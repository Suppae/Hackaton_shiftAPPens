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
    P_base  = base spread probability per step (~0.4)
    Φ_W(θ)  = wind factor, elliptical, based on cos(θ) between wind
              vector and the direction from cell to neighbour
    Φ_S     = slope factor from topo_client (fire accelerates uphill)
    η_M     = moisture damping factor, exponential decay with humidity

The grid is geo-referenced: each cell maps to real lat/lon coordinates.
Output is a sequence of GeoJSON Polygon Features (convex hull of all
burning + burned cells at each timestep).
"""

import math
import random
import time
from typing import Any, Dict, List, Optional, Tuple

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
    # Grid: row increases = latitude decreases (south)
    # So dy in "math" coords = -dr (north is positive y)
    dx = float(dc)
    dy = float(-dr)
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
        # Degenerate: return a tiny triangle around the points
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

    # Graham scan
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
    # Close the ring and convert to [lon, lat] lists
    ring = [[p[0], p[1]] for p in hull]
    ring.append(ring[0])  # close
    return ring


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
) -> List[Dict[str, Any]]:
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

    Returns:
        List of timestep dicts, same shape as mock_engine output.
    """
    if seed is not None:
        random.seed(seed)

    # ── Fetch weather if needed ──────────────────────────────────────────
    if weather is None:
        weather = get_weather(ignition_lat, ignition_lon)

    wind_math_rad = _meteo_to_math_rad(weather.wind_direction_deg)
    eta_m = _moisture_damping(weather.humidity_pct)

    # Base probability tuned so fire visibly grows but doesn't explode
    P_base = 0.42

    # ── Build geo-referenced grid ────────────────────────────────────────
    # Grid center = ignition point. Row 0 = northernmost.
    half = grid_size // 2
    dlat_per_cell = cell_size_m / _M_PER_DEG_LAT
    dlon_per_cell = cell_size_m / _m_per_deg_lon(ignition_lat)

    def cell_to_lonlat(r: int, c: int) -> Tuple[float, float]:
        lon = ignition_lon + (c - half) * dlon_per_cell
        lat = ignition_lat - (r - half) * dlat_per_cell  # row↑ = north
        return (lon, lat)

    # ── Initialise grid ──────────────────────────────────────────────────
    grid = [[UNBURNED] * grid_size for _ in range(grid_size)]
    grid[half][half] = BURNING  # ignition at center

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
        # Diagonal distance is √2 × cell_size
        dist_factor = math.sqrt(dr * dr + dc * dc)
        neighbour_distances[(dr, dc)] = cell_size_m * dist_factor

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
                    if 0 <= nr < grid_size and 0 <= nc < grid_size:
                        if grid[nr][nc] != UNBURNED:
                            continue

                        # Wind factor
                        phi_w = _wind_factor(
                            weather.wind_speed_ms,
                            wind_math_rad,
                            neighbour_angles[(dr, dc)],
                        )

                        # Slope factor (finite differences)
                        phi_s = compute_slope_factor(
                            elevations[r][c],
                            elevations[nr][nc],
                            neighbour_distances[(dr, dc)],
                        )

                        # Spread probability
                        p_spread = P_base * phi_w * phi_s * eta_m

                        # Diagonal penalty (fire has to travel further)
                        if abs(dr) + abs(dc) == 2:
                            p_spread *= 0.707  # 1/√2

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
        # Collect all burning + burned cell centers for the convex hull
        fire_points: List[Tuple[float, float]] = []
        for r in range(grid_size):
            for c in range(grid_size):
                if grid[r][c] in (BURNING, BURNED):
                    fire_points.append(cell_to_lonlat(r, c))

        if not fire_points:
            # Fire died — unlikely with reasonable params, but handle it
            continue

        hull = _convex_hull(fire_points)

        # Area estimate: count of burned/burning cells × cell area
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

    return timesteps
