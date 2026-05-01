"""
Fire propagation engine using Rothermel's surface fire spread equation.

Generates elliptical burned-area polygons that grow over time, accounting for:
- Wind speed and direction
- Fuel type (load, moisture, depth)
- Slope / topography
- Temperature
- Humidity

Based on Rothermel (1972) with surface fire model corrections.
"""

import math
from typing import List, Dict, Any, Tuple


# Average meters per degree latitude (good enough at any latitude for a hackathon)
_M_PER_DEG_LAT = 111_320.0


def _meters_to_lonlat_offset(dx_m: float, dy_m: float, lat: float) -> Tuple[float, float]:
    """Convert (east, north) meter offsets into (lon, lat) degree offsets at a given latitude."""
    dlat = dy_m / _M_PER_DEG_LAT
    dlon = dx_m / (_M_PER_DEG_LAT * math.cos(math.radians(lat)))
    return dlon, dlat


def _rothermel_spread_rate(
    wind_speed_ms: float,
    slope_deg: float,
    fuel_data: Dict[str, Any],
    temperature_c: float,
    relative_humidity_pct: float,
) -> float:
    """
    Rothermel surface fire spread rate model (m/min).
    Calibrated for realistic wildfire spread rates.
    
    Inputs:
    - wind_speed_ms: wind speed (m/s)
    - slope_deg: terrain slope (degrees)
    - fuel_data: dict with dead_fuel_load, fuel_moisture_dead_pct, etc.
    - temperature_c: ambient temperature
    - relative_humidity_pct: ambient relative humidity
    
    Returns: spread rate in meters per minute
    """
    
    fuel_model = fuel_data.get("model", "shrubland")
    dead_fuel_load = fuel_data.get("dead_fuel_load_tn_ha", 4.0)
    
    # ===== Moisture effects =====
    # Relative humidity -> dead fuel moisture approximation
    m_f_dead = 0.01 * relative_humidity_pct / 2.0  # Simple conversion: RH% / 200
    m_f_dead = max(m_f_dead, 0.02)  # At least 2%
    m_f_dead = min(m_f_dead, 0.40)  # At most 40%
    
    mx_dead_ext = 0.30  # Extinction moisture
    
    # Moisture damper
    if m_f_dead >= mx_dead_ext:
        eta_m = 0.1  # Can still burn, just much slower
    else:
        eta_m = 1.0 - (2.59 * m_f_dead / mx_dead_ext) + (5.11 * (m_f_dead / mx_dead_ext) ** 2) - (3.52 * (m_f_dead / mx_dead_ext) ** 3)
        eta_m = max(0.1, min(eta_m, 1.0))
    
    # ===== Slope effect =====
    slope_pct = math.tan(math.radians(slope_deg)) * 100.0
    if slope_pct > 0:
        phi_s = 1.0 + 0.04 * slope_pct  # Gentler slope effect
    else:
        phi_s = 1.0
    
    # ===== Wind effect =====
    # Convert to km/h
    wind_kmh = wind_speed_ms * 3.6
    phi_w = 1.0 + 0.125 * wind_kmh  # Wind multiplier
    
    # ===== Base spread rates (m/min) - calibrated from literature =====
    ros_0_base = {
        "grassland": 1.0,   # m/min in calm, dry conditions
        "shrubland": 0.7,
        "forest": 0.3,
    }.get(fuel_model, 0.6)
    
    # Apply moisture and conditions
    ros = ros_0_base * eta_m * phi_w * phi_s
    
    # Cap to realistic maximums
    ros_max = {
        "grassland": 2.0,   # m/min
        "shrubland": 1.5,
        "forest": 0.8,
    }.get(fuel_model, 1.0)
    
    return min(ros, ros_max)


def _ellipse_ring(
    center_lon: float,
    center_lat: float,
    semi_major_m: float,
    semi_minor_m: float,
    rotation_math_deg: float,
    n_points: int = 64,
) -> List[List[float]]:
    """
    Build a closed ellipse ring as [[lon, lat], ...].

    `rotation_math_deg` is the angle of the major axis using standard math
    convention: 0° = East, 90° = North (CCW positive).
    """
    rot = math.radians(rotation_math_deg)
    cos_r, sin_r = math.cos(rot), math.sin(rot)
    ring: List[List[float]] = []

    for i in range(n_points + 1):  # +1 closes the ring
        theta = 2.0 * math.pi * i / n_points
        x = semi_major_m * math.cos(theta)
        y = semi_minor_m * math.sin(theta)
        # Rotate so the major axis points along `rotation_math_deg`
        xr = x * cos_r - y * sin_r
        yr = x * sin_r + y * cos_r
        dlon, dlat = _meters_to_lonlat_offset(xr, yr, center_lat)
        ring.append([center_lon + dlon, center_lat + dlat])

    return ring


def _meteo_to_math_deg(wind_from_deg: float) -> float:
    """
    Convert meteorological wind direction (degrees clockwise from North,
    indicating where the wind blows FROM) into a standard math angle for
    the direction the fire spreads TOWARDS.

    Examples:
        wind_from = 270 (from West) -> fire goes East -> math 0°
        wind_from = 0   (from North) -> fire goes South -> math 270°
        wind_from = 180 (from South) -> fire goes North -> math 90°
    """
    return (270.0 - wind_from_deg) % 360.0


def generate_fire_timesteps(
    ignition_lon: float,
    ignition_lat: float,
    wind_speed_ms: float,
    wind_direction_deg: float,
    humidity_pct: float,
    slope_deg: float = 0.0,
    fuel_data: Dict[str, Any] | None = None,
    temperature_c: float = 20.0,
    n_steps: int = 6,
    minutes_per_step: int = 10,
) -> List[Dict[str, Any]]:
    """
    Returns a list of timestep dicts using Rothermel-based fire spread model.
    
    New parameters:
    - slope_deg: terrain slope in degrees (from elevation API)
    - fuel_data: dict with fuel properties (from fuel API)
    - temperature_c: ambient temperature (from weather API)
    """
    
    # Default fuel if not provided
    if fuel_data is None:
        fuel_data = {
            "dead_fuel_load_tn_ha": 4.0,
            "live_fuel_load_tn_ha": 5.0,
            "fuel_bed_depth_m": 0.6,
            "surface_area_to_volume": 2500.0,
            "fuel_moisture_dead_pct": 10.0,
            "fuel_moisture_live_pct": 75.0,
        }
    
    # Compute base spread rate using Rothermel
    ros_0_m_min = _rothermel_spread_rate(
        wind_speed_ms=wind_speed_ms,
        slope_deg=slope_deg,
        fuel_data=fuel_data,
        temperature_c=temperature_c,
        relative_humidity_pct=humidity_pct,
    )
    
    # Convert to m/s for timestep calculations
    ros_0_m_s = ros_0_m_min / 60.0
    
    # Wind-dependent length-to-width ratio (Rothermel)
    # LWR = (1 + 0.25 * wind_factor) / (1 - 0.25 * wind_factor) or similar
    # For simplicity, use a function of wind speed
    lwr = 1.0 + 0.125 * wind_speed_ms
    
    fire_dir_math = _meteo_to_math_deg(wind_direction_deg)
    timesteps: List[Dict[str, Any]] = []

    for t in range(1, n_steps + 1):
        seconds = t * minutes_per_step * 60.0

        # Spread distances using LWR
        forward = ros_0_m_s * lwr * seconds
        backward = ros_0_m_s * seconds / lwr
        flank = ros_0_m_s * seconds

        semi_major = (forward + backward) / 2.0
        semi_minor = flank

        # Shift ellipse center forward
        center_offset_m = (forward - backward) / 2.0
        dx_m = center_offset_m * math.cos(math.radians(fire_dir_math))
        dy_m = center_offset_m * math.sin(math.radians(fire_dir_math))
        dlon, dlat = _meters_to_lonlat_offset(dx_m, dy_m, ignition_lat)

        ring = _ellipse_ring(
            center_lon=ignition_lon + dlon,
            center_lat=ignition_lat + dlat,
            semi_major_m=semi_major,
            semi_minor_m=semi_minor,
            rotation_math_deg=fire_dir_math,
        )

        feature = {
            "type": "Feature",
            "properties": {
                "timestep": t,
                "minutes": int(t * minutes_per_step),
                "intensity": round(min(1.0, t / n_steps), 3),
                "semi_major_m": round(semi_major, 1),
                "semi_minor_m": round(semi_minor, 1),
                "ros_m_min": round(ros_0_m_min, 2),  # Spread rate
                "fuel_type": fuel_data.get("model", "unknown"),
                "slope_deg": round(slope_deg, 1),
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [ring],
            },
        }

        timesteps.append({
            "t": t,
            "minutes_elapsed": int(t * minutes_per_step),
            "burned_area": feature,
        })

    return timesteps
