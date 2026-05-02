"""
Mock fire propagation engine.

Generates elliptical burned-area polygons that grow over time, biased
in the direction the wind is blowing. Same I/O contract as the real
Cellular Automaton engine, so swapping later is a one-line change in main.py.

Math (intentionally simplified, Rothermel-inspired):
- Forward spread rate scales with wind speed.
- Ellipse length-to-width ratio (LWR) grows with wind (head fire >> back fire).
- Humidity acts as an exponential damper.
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
    n_steps: int = 6,
    minutes_per_step: int = 10,
) -> List[Dict[str, Any]]:
    """
    Returns a list of timestep dicts; each contains a GeoJSON Feature
    (Polygon) representing the cumulative burned area at that time.
    """
    # Baseline rate of spread in still, dry air (m/s). Tuned for visible
    # growth on a city-scale map within ~1 hour of simulated time.
    base_rate = 0.08

    # Wind multiplier for forward spread. Head fire elongates with wind.
    wind_factor = 1.0 + 0.35 * max(0.0, wind_speed_ms)

    # Humidity damper: exponential, pivot at 30% RH.
    humidity_damp = math.exp(-0.025 * (humidity_pct - 30.0))
    humidity_damp = max(0.2, min(humidity_damp, 1.6))

    effective_rate = base_rate * humidity_damp
    fire_dir_math = _meteo_to_math_deg(wind_direction_deg)

    timesteps: List[Dict[str, Any]] = []

    for t in range(1, n_steps + 1):
        seconds = t * minutes_per_step * 60.0

        forward = effective_rate * wind_factor * seconds
        backward = effective_rate * seconds / wind_factor
        flank = effective_rate * seconds

        semi_major = (forward + backward) / 2.0
        semi_minor = flank

        # Shift ellipse center forward so ignition stays near the trailing edge
        center_offset_m = (forward - backward) / 2.0
        dx_m = center_offset_m * math.cos(math.radians(fire_dir_math))
        dy_m = center_offset_m * math.sin(math.radians(fire_dir_math))
        dlon, dlat = _meters_to_lonlat_offset(dx_m, dy_m, ignition_lat)

        center_lon = ignition_lon + dlon
        center_lat = ignition_lat + dlat

        # Outer ring = current burned area boundary
        outer_ring = _ellipse_ring(
            center_lon=center_lon,
            center_lat=center_lat,
            semi_major_m=semi_major,
            semi_minor_m=semi_minor,
            rotation_math_deg=fire_dir_math,
        )

        # Inner ring = previous step boundary (approximates burned zone interior)
        shrink = 0.85
        inner_ring = _ellipse_ring(
            center_lon=center_lon,
            center_lat=center_lat,
            semi_major_m=max(1.0, semi_major * shrink),
            semi_minor_m=max(1.0, semi_minor * shrink),
            rotation_math_deg=fire_dir_math,
        )
        # Reverse inner ring for GeoJSON hole convention
        inner_ring_rev = list(reversed(inner_ring))

        props = {
            "timestep": t,
            "minutes": int(t * minutes_per_step),
            "intensity": round(min(1.0, t / n_steps), 3),
            "semi_major_m": round(semi_major, 1),
            "semi_minor_m": round(semi_minor, 1),
            "area_km2": round(math.pi * semi_major * semi_minor / 1_000_000.0, 3),
        }

        burned_area_feature = {
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [inner_ring]},
        }

        burning_front_feature = {
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [outer_ring, inner_ring_rev]},
        }

        timesteps.append({
            "t": t,
            "minutes_elapsed": int(t * minutes_per_step),
            "burned_area": burned_area_feature,
            "burning_front": burning_front_feature,
        })

    return timesteps
