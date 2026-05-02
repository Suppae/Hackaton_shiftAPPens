"""
Cellular Automaton fire propagation engine (Rothermel-inspired).

Grid-based model where each cell can be:
    0 = unburned
    1 = burning
    2 = burned out

At each timestep, every burning cell tries to ignite its 8 neighbours.
The probability of ignition depends on:

    P_spread = P_base × Φ_W(θ) × Φ_S × η_M

Where:
    P_base  = fuel[nr][nc] × ndvi[nr][nc] × (1 − ndmi[nr][nc])
              when GEE satellite data is available; falls back to 0.42
    Φ_W(θ)  = wind factor, elliptical, based on cos(θ) between wind
              vector and the direction from cell to neighbour
    Φ_S     = slope factor from topo_client (fire accelerates uphill)
    η_M     = moisture damping factor, exponential decay with humidity

The grid is geo-referenced: each cell maps to real lat/lon coordinates.
Output is a dict containing a sequence of GeoJSON Polygon Features plus
directional vector metadata for the frontend.
"""

import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from weather_client import WeatherSnapshot, get_weather, _fallback_snapshot
from topo_client import fetch_elevations, compute_slope_factor


# ── Cell states ──────────────────────────────────────────────────────────────
UNBURNED = 0
BURNING = 1
BURNED = 2

# ── 8-connected neighbourhood (row_offset, col_offset) ──────────────────────
NEIGHBOURS = [
    (-1, -1), (-1, 0), (-1, 1),
    ( 0, -1),          ( 0, 1),
    ( 1, -1), ( 1, 0), ( 1, 1),
]

# Meters per degree latitude (approx)
_M_PER_DEG_LAT = 111_320.0


def _m_per_deg_lon(lat: float) -> float:
    return _M_PER_DEG_LAT * math.cos(math.radians(lat))


def _meteo_to_math_rad(wind_from_deg: float) -> float:
    """
    Convert meteo wind direction (FROM, clockwise from N)
    to math angle (radians, CCW from East) of where fire spreads TO.
    """
    math_deg = (270.0 - wind_from_deg) % 360.0
    return math.radians(math_deg)


def _direction_angle(dr: int, dc: int) -> float:
    """
    Math angle (radians, CCW from East) from center cell to neighbour
    at grid offset (dr, dc). dr>0 = South in our grid (row increases
    southward), dc>0 = East.
    """
    dx = float(dc)
    dy = float(-dr)  # row↑ = north in math coords
    return math.atan2(dy, dx)


def _wind_factor(
    wind_speed_ms: float,
    wind_math_rad: float,
    neighbour_angle_rad: float,
) -> float:
    """
    Elliptical wind factor Φ_W.

    When the neighbour is in the direction the fire wants to go (downwind),
    cos(θ) ≈ 1 → big boost. When upwind, cos(θ) ≈ -1 → strong penalty.

    Φ_W = 1 + C × wind_speed × cos(θ)

    Where C is a tuning constant. Clamped so Φ_W ≥ 0.05 (fire can still
    creep upwind very slowly).
    """
    theta = neighbour_angle_rad - wind_math_rad
    cos_theta = math.cos(theta)

    C = 0.12  # tuned for visual spread at 5-15 m/s
    factor = 1.0 + C * wind_speed_ms * cos_theta
    return max(0.05, factor)


def _moisture_damping(humidity_pct: float) -> float:
    """
    Exponential moisture damping η_M.

    At 30% RH → η_M ≈ 1.0 (neutral)
    At 80% RH → η_M ≈ 0.29 (hard to spread)
    At 15% RH → η_M ≈ 1.45 (tinder-dry, faster spread)

    η_M = exp(-0.025 × (H - 30))
    Clamped to [0.15, 1.6].
    """
    eta = math.exp(-0.025 * (humidity_pct - 30.0))
    return max(0.15, min(1.6, eta))


def _convex_hull(points: List[Tuple[float, float]]) -> List[List[float]]:
    """
    Compute convex hull of 2D points using Graham scan.
    Returns closed ring as [[lon, lat], ...] suitable for GeoJSON Polygon.
    """
    if len(points) < 3:
        if not points:
            return []
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        eps = 0.0005
        return [
            [cx - eps, cy - eps],
            [cx + eps, cy - eps],
            [cx + eps, cy + eps],
            [cx - eps, cy + eps],
            [cx - eps, cy - eps],
        ]

    pts = sorted(set(points))

    def cross(O, A, B):
        return (A[0] - O[0]) * (B[1] - O[1]) - (A[1] - O[1]) * (B[0] - O[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    hull = lower[:-1] + upper[:-1]
    ring = [[p[0], p[1]] for p in hull]
    ring.append(ring[0])
    return ring


def _resize_array(arr: np.ndarray, target_size: int) -> np.ndarray:
    """Resize a 2D array to target_size × target_size."""
    h, w = arr.shape
    try:
        from scipy.ndimage import zoom
        return zoom(arr, (target_size / h, target_size / w))
    except ImportError:
        yi = np.round(np.linspace(0, h - 1, target_size)).astype(int).clip(0, h - 1)
        xi = np.round(np.linspace(0, w - 1, target_size)).astype(int).clip(0, w - 1)
        return arr[np.ix_(yi, xi)]


def compute_bbox_polygon(
    ignition_lon: float,
    ignition_lat: float,
    grid_size: int,
    cell_size_m: float,
) -> List[List[float]]:
    """
    Returns the bounding-box polygon of the simulation grid as a closed
    ring of [lon, lat] pairs (GeoJSON-ready, without closing duplicate).
    """
    half = grid_size // 2
    dlat = (half * cell_size_m) / _M_PER_DEG_LAT
    dlon = (half * cell_size_m) / _m_per_deg_lon(ignition_lat)
    min_lon, max_lon = ignition_lon - dlon, ignition_lon + dlon
    min_lat, max_lat = ignition_lat - dlat, ignition_lat + dlat
    return [
        [min_lon, min_lat],
        [max_lon, min_lat],
        [max_lon, max_lat],
        [min_lon, max_lat],
    ]


def _compute_spread_vector(
    weather: WeatherSnapshot,
    wind_math_rad: float,
    ignition_r: int,
    ignition_c: int,
    grid_size: int,
    elevations: List[List[Optional[float]]],
    cell_size_m: float,
) -> Tuple[float, float]:
    """
    Returns (primary_spread_angle_deg, speed_m_per_min).

    primary_spread_angle: geographic bearing (0=N, 90=E, CW) of the dominant
    fire spread direction — resultant of wind vector and steepest uphill
    slope at the ignition point.
    """
    ws = weather.wind_speed_ms

    # Wind vector in math coords (CCW from East)
    wx = ws * math.cos(wind_math_rad)
    wy = ws * math.sin(wind_math_rad)

    # Slope vector: steepest uphill neighbour at ignition
    sx, sy = 0.0, 0.0
    ign_elev = elevations[ignition_r][ignition_c]
    if ign_elev is not None:
        best_slope = 0.0
        for dr, dc in NEIGHBOURS:
            nr, nc = ignition_r + dr, ignition_c + dc
            if 0 <= nr < grid_size and 0 <= nc < grid_size:
                nbr_elev = elevations[nr][nc]
                if nbr_elev is not None:
                    rise = nbr_elev - ign_elev
                    if rise > 0:
                        dist_m = math.sqrt(dr * dr + dc * dc) * cell_size_m
                        slope_pct = rise / dist_m
                        if slope_pct > best_slope:
                            best_slope = slope_pct
                            angle_rad = _direction_angle(dr, dc)
                            slope_mag = min(slope_pct * 200.0, ws)
                            sx = slope_mag * math.cos(angle_rad)
                            sy = slope_mag * math.sin(angle_rad)

    # Combine: wind dominates, slope nudges
    cx = wx + 0.3 * sx
    cy = wy + 0.3 * sy

    # Math angle (CCW from E) → geographic bearing (CW from N)
    primary_angle = (90.0 - math.degrees(math.atan2(cy, cx))) % 360.0

    # Rough fire spread speed: ~3 % of wind speed (m/s) → m/min
    speed_m_per_min = max(1.0, ws * 0.03 * 60.0)

    return primary_angle, speed_m_per_min


def simulate(
    ignition_lon: float,
    ignition_lat: float,
    weather: Optional[WeatherSnapshot] = None,
    n_steps: int = 6,
    minutes_per_step: int = 10,
    grid_size: int = 40,
    cell_size_m: float = 120.0,
    use_topo: bool = True,
    seed: Optional[int] = None,
    gee_layers: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Run the Cellular Automaton fire simulation.

    Args:
        ignition_lon, ignition_lat: ignition point (WGS84)
        weather: WeatherSnapshot. If None, fetches from OWM for the ignition point.
        n_steps: number of timesteps to simulate
        minutes_per_step: simulated minutes per step
        grid_size: NxN grid (40 → 1600 cells, fast enough)
        cell_size_m: side length of each cell in meters
        use_topo: whether to fetch real elevation data (False = assume flat)
        seed: random seed for reproducibility (None = random)
        gee_layers: dict with numpy arrays {"fuel", "ndvi", "ndmi", "lai"}.
                    If provided, replaces the static P_base = 0.42 with a
                    per-cell dynamic value.  Falls back to 0.42 if absent
                    or malformed.

    Returns:
        Dict with keys:
            timesteps         – list of GeoJSON-bearing dicts (existing shape)
            primary_spread_angle – dominant spread bearing (°, 0=N CW)
            wind_angle           – met wind direction (FROM, °)
            speed_m_per_min      – estimated fire speed
            fuel_load_mean       – mean fuel load from GEE (or 0.42 fallback)
            ndvi_mean            – mean NDVI from GEE (or 0.5 fallback)
            bbox_polygon         – grid bounding-box [[lon,lat], …]
    """
    if seed is not None:
        random.seed(seed)

    # ── Fetch weather if needed ──────────────────────────────────────────
    if weather is None:
        weather = get_weather(ignition_lat, ignition_lon)

    wind_math_rad = _meteo_to_math_rad(weather.wind_direction_deg)
    eta_m = _moisture_damping(weather.humidity_pct)

    # ── Bounding box ─────────────────────────────────────────────────────
    bbox_polygon = compute_bbox_polygon(ignition_lon, ignition_lat, grid_size, cell_size_m)

    # ── Resize GEE layers to grid_size × grid_size ───────────────────────
    gee_fuel: Optional[np.ndarray] = None
    gee_ndvi: Optional[np.ndarray] = None
    gee_ndmi: Optional[np.ndarray] = None
    fuel_load_mean = 0.42
    ndvi_mean = 0.5

    if gee_layers is not None:
        try:
            gee_fuel = _resize_array(np.asarray(gee_layers["fuel"], dtype=float), grid_size)
            gee_ndvi = _resize_array(np.asarray(gee_layers["ndvi"], dtype=float), grid_size)
            gee_ndmi = _resize_array(np.asarray(gee_layers["ndmi"], dtype=float), grid_size)
            fuel_load_mean = float(np.mean(gee_fuel))
            ndvi_mean = float(np.mean(gee_ndvi))
            print(f"[fire_engine] GEE layers active — fuel_mean={fuel_load_mean:.3f} ndvi_mean={ndvi_mean:.3f}")
        except Exception as exc:
            print(f"[fire_engine] GEE resize failed: {exc!r} — falling back to static P_base=0.42")
            gee_fuel = gee_ndvi = gee_ndmi = None

    P_base_static = 0.42

    # ── Build geo-referenced grid ────────────────────────────────────────
    half = grid_size // 2
    dlat_per_cell = cell_size_m / _M_PER_DEG_LAT
    dlon_per_cell = cell_size_m / _m_per_deg_lon(ignition_lat)

    def cell_to_lonlat(r: int, c: int) -> Tuple[float, float]:
        lon = ignition_lon + (c - half) * dlon_per_cell
        lat = ignition_lat - (r - half) * dlat_per_cell
        return (lon, lat)

    # ── Initialise grid ──────────────────────────────────────────────────
    grid = [[UNBURNED] * grid_size for _ in range(grid_size)]
    grid[half][half] = BURNING

    # ── Pre-fetch elevations for entire grid (1 batched HTTP call) ───────
    elevations: List[List[Optional[float]]] = [
        [None] * grid_size for _ in range(grid_size)
    ]

    if use_topo:
        all_points = []
        for r in range(grid_size):
            for c in range(grid_size):
                lon, lat = cell_to_lonlat(r, c)
                all_points.append((lat, lon))

        t0 = time.time()
        elev_flat = fetch_elevations(all_points)
        print(f"[fire_engine] Elevation fetch: {len(all_points)} pts in {time.time()-t0:.1f}s")

        idx = 0
        for r in range(grid_size):
            for c in range(grid_size):
                elevations[r][c] = elev_flat[idx]
                idx += 1

    # ── Precompute neighbour direction angles ────────────────────────────
    neighbour_angles = {}
    neighbour_distances = {}
    for dr, dc in NEIGHBOURS:
        neighbour_angles[(dr, dc)] = _direction_angle(dr, dc)
        dist_factor = math.sqrt(dr * dr + dc * dc)
        neighbour_distances[(dr, dc)] = cell_size_m * dist_factor

    # ── Primary spread direction (computed once, before the CA loop) ─────
    primary_spread_angle, speed_m_per_min = _compute_spread_vector(
        weather, wind_math_rad, half, half, grid_size, elevations, cell_size_m
    )

    # ── Run simulation ───────────────────────────────────────────────────
    timesteps: List[Dict[str, Any]] = []

    for t in range(1, n_steps + 1):
        new_burning: List[Tuple[int, int]] = []

        for r in range(grid_size):
            for c in range(grid_size):
                if grid[r][c] != BURNING:
                    continue

                for dr, dc in NEIGHBOURS:
                    nr, nc = r + dr, c + dc
                    if not (0 <= nr < grid_size and 0 <= nc < grid_size):
                        continue
                    if grid[nr][nc] != UNBURNED:
                        continue

                    # ── Dynamic P_base from GEE, or static fallback ──
                    if gee_fuel is not None:
                        fuel_v = float(gee_fuel[nr, nc])
                        ndvi_v = float(gee_ndvi[nr, nc])
                        ndmi_v = float(gee_ndmi[nr, nc])
                        p_base = fuel_v * ndvi_v * (1.0 - max(0.0, ndmi_v))
                        p_base = max(0.05, min(0.95, p_base))
                    else:
                        p_base = P_base_static

                    phi_w = _wind_factor(
                        weather.wind_speed_ms,
                        wind_math_rad,
                        neighbour_angles[(dr, dc)],
                    )

                    phi_s = compute_slope_factor(
                        elevations[r][c],
                        elevations[nr][nc],
                        neighbour_distances[(dr, dc)],
                    )

                    p_spread = p_base * phi_w * phi_s * eta_m

                    if abs(dr) + abs(dc) == 2:
                        p_spread *= 0.707  # diagonal penalty

                    p_spread = min(1.0, max(0.0, p_spread))

                    if random.random() < p_spread:
                        new_burning.append((nr, nc))

        # Transition: current burning → burned out, new → burning
        for r in range(grid_size):
            for c in range(grid_size):
                if grid[r][c] == BURNING:
                    grid[r][c] = BURNED

        for nr, nc in new_burning:
            grid[nr][nc] = BURNING

        # ── Build GeoJSON for this timestep ──────────────────────────────
        fire_points: List[Tuple[float, float]] = []
        for r in range(grid_size):
            for c in range(grid_size):
                if grid[r][c] in (BURNING, BURNED):
                    fire_points.append(cell_to_lonlat(r, c))

        if not fire_points:
            continue

        hull = _convex_hull(fire_points)

        n_fire_cells = len(fire_points)
        area_m2 = n_fire_cells * cell_size_m * cell_size_m
        area_km2 = area_m2 / 1_000_000.0

        feature = {
            "type": "Feature",
            "properties": {
                "timestep": t,
                "minutes": int(t * minutes_per_step),
                "intensity": round(min(1.0, t / n_steps), 3),
                "area_km2": round(area_km2, 3),
                "n_cells_burning": sum(
                    1 for r in range(grid_size)
                    for c in range(grid_size)
                    if grid[r][c] == BURNING
                ),
                "n_cells_burned": sum(
                    1 for r in range(grid_size)
                    for c in range(grid_size)
                    if grid[r][c] == BURNED
                ),
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [hull],
            },
        }

        timesteps.append({
            "t": t,
            "minutes_elapsed": int(t * minutes_per_step),
            "burned_area": feature,
        })

    return {
        "timesteps": timesteps,
        "primary_spread_angle": round(primary_spread_angle, 1),
        "wind_angle": round(weather.wind_direction_deg, 1),
        "speed_m_per_min": round(speed_m_per_min, 2),
        "fuel_load_mean": round(fuel_load_mean, 3),
        "ndvi_mean": round(ndvi_mean, 3),
        "bbox_polygon": bbox_polygon,
    }
