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


# ── Mediterranean fuel model parameters (Scott & Burgan 2005, adapted) ───────
# Each model: (fuel_load_kg_m2, savr_cm_1, heat_content_kJ_kg, bed_depth_m, moisture_extinction)
# fuel_load  = dry biomass per unit area
# savr       = surface-area-to-volume ratio (higher = finer fuel, faster ignition)
# heat_content = energy released per kg of fuel burned
# bed_depth  = depth of the fuel bed
# M_ext      = moisture content at which fuel becomes non-combustible

FUEL_MODELS = {
    "grass_short":  {"load": 0.30, "savr": 82.0, "heat": 18600, "depth": 0.15, "m_ext": 0.30},
    "grass_tall":   {"load": 0.60, "savr": 65.0, "heat": 18600, "depth": 0.30, "m_ext": 0.30},
    "shrub_low":    {"load": 1.20, "savr": 55.0, "heat": 20000, "depth": 0.45, "m_ext": 0.35},
    "shrub_high":   {"load": 2.50, "savr": 45.0, "heat": 20000, "depth": 0.90, "m_ext": 0.35},
    "forest_lite":  {"load": 0.90, "savr": 40.0, "heat": 19000, "depth": 0.35, "m_ext": 0.32},
    "forest_heavy": {"load": 3.00, "savr": 30.0, "heat": 19000, "depth": 0.60, "m_ext": 0.32},
}

# Default for Portugal (Mediterranean shrubland / eucalyptus understorey)
DEFAULT_FUEL_MODEL = "shrub_high"


def _estimate_dfmc(humidity_pct: float, temperature_c: float) -> float:
    """
    Estimate Dead Fuel Moisture Content (DFMC) as a fraction (0–1).

    Uses a simplified equilibrium moisture content (EMC) model based on
    Simard (1968), calibrated for 1-hour timelag fuels (the ones that matter
    for fire spread).

    At 10% RH, 35°C → DFMC ≈ 0.04 (bone-dry, tinder)
    At 50% RH, 25°C → DFMC ≈ 0.10 (typical fire conditions)
    At 90% RH, 15°C → DFMC ≈ 0.25 (very wet, hard to ignite)
    """
    # Simard-style EMC: EMC = a * RH^b / (1 + c * T + d * RH)
    RH = humidity_pct / 100.0
    T = temperature_c

    # Coefficients calibrated for 1-hour dead fuels
    emc = (0.34 * (RH ** 0.55)) / (1.0 + 0.012 * T + 0.65 * RH)
    return max(0.03, min(0.40, emc))


def _compute_no_wind_ros(
    fuel_load: float,
    savr: float,
    heat_content: float,
    bed_depth: float,
    moisture_fraction: float,
    moisture_extinction: float,
) -> float:
    """
    Compute the no-wind, no-slope rate of spread (ROS) in m/s.

    Simplified Rothermel:
        ROS_0 = (propagating_flux * reaction_efficiency) / (bulk_density * heat_of_ignition)

    Where:
    - propagating_flux ∝ fuel_load × savr × heat_content
    - reaction_efficiency decreases with moisture
    - bulk_density = fuel_load / bed_depth
    - heat_of_ignition ≈ 1800 kJ/kg (energy to raise fuel to pyrolysis)

    Returns ROS in m/s (typically 0.001–0.05 for no-wind conditions).
    """
    if fuel_load <= 0 or bed_depth <= 0:
        return 0.001  # minimum creep

    bulk_density = fuel_load / bed_depth  # kg/m³

    # Moisture damping: exponential decay when moisture exceeds threshold
    if moisture_fraction >= moisture_extinction:
        return 0.0005  # nearly non-combustible

    moisture_factor = 1.0 - (moisture_fraction / moisture_extinction)
    moisture_factor = max(0.05, moisture_factor)

    # Reaction intensity (simplified)
    reaction_intensity = fuel_load * savr * heat_content * 1e-6  # kW/m², scaled

    # Propagating flux fraction (empirical, ~0.01–0.1 of reaction intensity reaches unburned fuel)
    propagating_fraction = 0.04 * moisture_factor

    # Heat of ignition (energy to raise fuel to pyrolysis temp ~300°C)
    heat_of_ignition = 1800.0  # kJ/kg

    # ROS = (propagating_flux) / (bulk_density * heat_of_ignition)
    ros = (reaction_intensity * propagating_fraction) / (bulk_density * heat_of_ignition)

    # Clamp to realistic range for no-wind spread
    return max(0.0005, min(0.05, ros))


def _wind_factor(
    wind_speed_ms: float,
    wind_math_rad: float,
    neighbour_angle_rad: float,
) -> float:
    """
    Elliptical wind factor Φ_W(θ) — Rothermel/Albini formulation.

    The wind effect on fire spread is modelled as an elliptical deformation
    of the fire perimeter. The factor depends on:
      - Wind speed (U)
      - Direction alignment (cos θ between wind and neighbour direction)

    Φ_W = exp[C × U^B × (1 + cos θ)]

    Where C and B are empirical constants. When cos(θ) = 1 (downwind),
    the factor is maximised. When cos(θ) = -1 (upwind), it minimises.

    Clamped to [0.02, 8.0] for numerical stability.
    """
    theta = neighbour_angle_rad - wind_math_rad
    cos_theta = math.cos(theta)

    # Albini-style wind coefficient (calibrated for Mediterranean fuels)
    # These values produce realistic head-fire/back-fire ratios at typical wind speeds
    A = 0.085
    B = 0.52

    if wind_speed_ms < 0.5:
        return 1.0  # negligible wind

    factor = math.exp(A * (wind_speed_ms ** B) * (1.0 + cos_theta))
    return max(0.02, min(8.0, factor))


def _moisture_damping(humidity_pct: float, temperature_c: float = 25.0) -> float:
    """
    Moisture damping factor η_M based on estimated Dead Fuel Moisture Content.

    Uses a physically-informed DFMC estimate from RH + temperature,
    then applies exponential damping when moisture exceeds optimal levels.

    At 10% RH, 35°C → η_M ≈ 1.5 (tinder-dry, fire spreads faster)
    At 30% RH, 25°C → η_M ≈ 1.0 (neutral baseline)
    At 70% RH, 20°C → η_M ≈ 0.25 (very damp, fire suppressed)
    """
    dfmc = _estimate_dfmc(humidity_pct, temperature_c)

    # Optimal DFMC for spread is ~0.06–0.08 (very dry 1-hour fuels)
    # Damping increases as DFMC rises above this range
    if dfmc <= 0.08:
        eta = 1.0 + (0.08 - dfmc) * 8.0  # dry boost
    else:
        eta = math.exp(-3.5 * (dfmc - 0.08))  # exponential decay

    return max(0.08, min(1.8, eta))


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
    gee_layers: Optional[Dict[str, Any]] = None,
) -> Tuple[float, float]:
    """
    Returns (primary_spread_angle_deg, speed_m_per_min).

    primary_spread_angle: geographic bearing (0=N, 90=E, CW) of the dominant
    fire spread direction — resultant of wind vector and steepest uphill
    slope at the ignition point.

    speed_m_per_min: computed from full Rothermel ROS incorporating
    fuel properties, wind, slope, and dead fuel moisture content.
    """
    ws = weather.wind_speed_ms

    # ── Wind vector in math coords (CCW from East) ──
    wx = ws * math.cos(wind_math_rad)
    wy = ws * math.sin(wind_math_rad)

    # ── Slope vector: steepest uphill neighbour at ignition ──
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

    # ── Combine: wind dominates, slope nudges ──
    cx = wx + 0.3 * sx
    cy = wy + 0.3 * sy

    # Math angle (CCW from E) → geographic bearing (CW from N)
    primary_angle = (90.0 - math.degrees(math.atan2(cy, cx))) % 360.0

    # ── Rothermel Rate of Spread ──
    # Base ROS from fuel model (no-wind, no-slope)
    fuel = FUEL_MODELS[DEFAULT_FUEL_MODEL]
    dfmc = _estimate_dfmc(weather.humidity_pct, weather.temperature_c)
    ros_base = _compute_no_wind_ros(
        fuel["load"], fuel["savr"], fuel["heat"],
        fuel["depth"], dfmc, fuel["m_ext"],
    )

    # Wind factor in primary spread direction (maximum forward spread)
    phi_w = _wind_factor(ws, wind_math_rad, wind_math_rad)  # cos(θ)=1 for downwind

    # Slope factor using max slope at ignition
    phi_s = 1.0
    if ign_elev is not None and best_slope > 0:
        tan_theta = best_slope
        phi_s = min(5.0, 1.0 + 2.0 * tan_theta)  # Rothermel Φ_S

    # Moisture damping
    eta_m = _moisture_damping(weather.humidity_pct, weather.temperature_c)

    # Combined ROS: R = R_0 × Φ_W × Φ_S × η_M
    ros_m_per_s = ros_base * phi_w * phi_s * eta_m

    # Convert to m/min for frontend
    speed_m_per_min = max(0.5, ros_m_per_s * 60.0)

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
    eta_m = _moisture_damping(weather.humidity_pct, weather.temperature_c)

    # ── Bounding box ─────────────────────────────────────────────────────
    bbox_polygon = compute_bbox_polygon(ignition_lon, ignition_lat, grid_size, cell_size_m)

    # ── Resize GEE layers to grid_size × grid_size ───────────────────────
    gee_fuel: Optional[np.ndarray] = None
    gee_ndvi: Optional[np.ndarray] = None
    gee_ndmi: Optional[np.ndarray] = None
    fuel = FUEL_MODELS[DEFAULT_FUEL_MODEL]
    fuel_load_mean = fuel["load"]
    ndvi_mean = 0.55  # typical Mediterranean shrubland NDVI

    if gee_layers is not None:
        try:
            gee_fuel = _resize_array(np.asarray(gee_layers["fuel"], dtype=float), grid_size)
            gee_ndvi = _resize_array(np.asarray(gee_layers["ndvi"], dtype=float), grid_size)
            gee_ndmi = _resize_array(np.asarray(gee_layers["ndmi"], dtype=float), grid_size)
            fuel_load_mean = float(np.mean(gee_fuel))
            ndvi_mean = float(np.mean(gee_ndvi))
            print(f"[fire_engine] GEE layers active — fuel_mean={fuel_load_mean:.3f} ndvi_mean={ndvi_mean:.3f}")
        except Exception as exc:
            print(f"[fire_engine] GEE resize failed: {exc!r} — falling back to Mediterranean fuel model")
            gee_fuel = gee_ndvi = gee_ndmi = None
            fuel_load_mean = fuel["load"]
            ndvi_mean = 0.55

    # ── Build geo-referenced grid ──
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
        # Sample a coarse 10×10 sub-grid (100 pts = 1 API call, fits rate limit).
        # SRTM30m resolution is 30m; our cells are 120m — coarse sampling is plenty.
        topo_n = 10  # coarse grid side length
        stride = max(1, grid_size // topo_n)
        sample_rows = list(range(0, grid_size, stride))[:topo_n]
        sample_cols = list(range(0, grid_size, stride))[:topo_n]

        sample_points = []
        for r in sample_rows:
            for c in sample_cols:
                lon, lat = cell_to_lonlat(r, c)
                sample_points.append((lat, lon))

        t0 = time.time()
        elev_flat = fetch_elevations(sample_points)
        print(f"[fire_engine] Elevation fetch: {len(sample_points)} pts in {time.time()-t0:.1f}s")

        # Build coarse elevation array and upscale to full grid_size
        coarse = np.full((topo_n, topo_n), np.nan)
        idx = 0
        for ri, r in enumerate(sample_rows):
            for ci, c in enumerate(sample_cols):
                if elev_flat[idx] is not None:
                    coarse[ri, ci] = elev_flat[idx]
                idx += 1

        # Fill NaN with column/row means so resize doesn't propagate NaN
        col_means = np.nanmean(coarse, axis=0)
        row_means = np.nanmean(coarse, axis=1)
        for ri in range(topo_n):
            for ci in range(topo_n):
                if np.isnan(coarse[ri, ci]):
                    coarse[ri, ci] = col_means[ci] if not np.isnan(col_means[ci]) else 300.0

        full_elev = _resize_array(coarse, grid_size)

        for r in range(grid_size):
            for c in range(grid_size):
                v = full_elev[r, c]
                elevations[r][c] = float(v) if not np.isnan(v) else None

    # ── Precompute neighbour direction angles ────────────────────────────
    neighbour_angles = {}
    neighbour_distances = {}
    for dr, dc in NEIGHBOURS:
        neighbour_angles[(dr, dc)] = _direction_angle(dr, dc)
        dist_factor = math.sqrt(dr * dr + dc * dc)
        neighbour_distances[(dr, dc)] = cell_size_m * dist_factor

    # ── Primary spread direction (computed once, before the CA loop) ─────
    primary_spread_angle, speed_m_per_min = _compute_spread_vector(
        weather, wind_math_rad, half, half, grid_size, elevations, cell_size_m, gee_layers
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

                    # ── Ignition probability P_base ──
                    if gee_fuel is not None:
                        fuel_v = float(gee_fuel[nr, nc])
                        ndvi_v = float(gee_ndvi[nr, nc])
                        ndmi_v = float(gee_ndmi[nr, nc])
                        # NDMI ∈ [-1,1]: negative = dry vegetation = higher fire risk.
                        # Normalize to [0,1] then invert so dry→high p_base.
                        ndmi_norm = (ndmi_v + 1.0) / 2.0  # maps [-1,1] → [0,1]
                        p_base = fuel_v * ndvi_v * (1.0 - ndmi_norm)
                        p_base = max(0.05, min(0.95, p_base))
                    else:
                        # Mediterranean fuel model (no GEE)
                        fuel = FUEL_MODELS[DEFAULT_FUEL_MODEL]
                        dfmc = _estimate_dfmc(weather.humidity_pct, weather.temperature_c)
                        ros_0 = _compute_no_wind_ros(
                            fuel["load"], fuel["savr"], fuel["heat"],
                            fuel["depth"], dfmc, fuel["m_ext"],
                        )
                        # Normalise ROS into a probability (0.01–0.70 range)
                        p_base = max(0.05, min(0.70, ros_0 * 50.0))

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

        # ── Collect burning and burned cells ─────────────────────────────
        burning_cells: List[Tuple[float, float]] = []
        burned_cells: List[Tuple[float, float]] = []
        for r in range(grid_size):
            for c in range(grid_size):
                state = grid[r][c]
                if state == BURNING:
                    burning_cells.append(cell_to_lonlat(r, c))
                elif state == BURNED:
                    burned_cells.append(cell_to_lonlat(r, c))

        all_fire_cells = burned_cells + burning_cells
        if not all_fire_cells:
            continue

        n_burning = len(burning_cells)
        n_burned = len(burned_cells)
        area_km2 = len(all_fire_cells) * cell_size_m * cell_size_m / 1_000_000.0

        # Burned zone → convex hull (smooth interior, near-black in UI)
        burned_hull = _convex_hull(burned_cells) if burned_cells else _convex_hull(burning_cells)

        # Burning front → individual cell squares (jagged real shape, red in UI)
        half_dlon = dlon_per_cell / 2.0
        half_dlat = dlat_per_cell / 2.0

        def _cell_square(lon: float, lat: float) -> List[List[float]]:
            return [
                [lon - half_dlon, lat - half_dlat],
                [lon + half_dlon, lat - half_dlat],
                [lon + half_dlon, lat + half_dlat],
                [lon - half_dlon, lat + half_dlat],
                [lon - half_dlon, lat - half_dlat],
            ]

        burning_squares = [[_cell_square(lon, lat)] for lon, lat in burning_cells]

        props = {
            "timestep": t,
            "minutes": int(t * minutes_per_step),
            "intensity": round(min(1.0, t / n_steps), 3),
            "area_km2": round(area_km2, 3),
            "n_cells_burning": n_burning,
            "n_cells_burned": n_burned,
        }

        burned_area_feature = {
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [burned_hull]},
        }

        burning_front_feature = {
            "type": "Feature",
            "properties": props,
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": burning_squares if burning_squares else [[[burned_hull[0]]]],
            },
        }

        timesteps.append({
            "t": t,
            "minutes_elapsed": int(t * minutes_per_step),
            "burned_area": burned_area_feature,
            "burning_front": burning_front_feature,
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
