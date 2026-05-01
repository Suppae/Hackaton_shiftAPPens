"""
External API service for geospatial and environmental data.

In production, replace these mocks with actual API calls to:
- Open-Elevation (https://open-elevation.com) for elevation
- USGS for land cover / fuel types
- OpenWeatherMap for temperature
"""

from typing import Dict, Any
import math


def get_elevation_and_slope(lon: float, lat: float) -> Dict[str, float]:
    """
    Mock: Get elevation (m) and slope (degrees) at a location.
    
    In production, call Open-Elevation API:
        https://api.open-elevation.com/api/v1/lookup?locations=40.3217,-7.6167
    """
    # Simplified mock: return plausible values for Serra da Estrela
    # In reality, you'd integrate with a real DEM (Digital Elevation Model)
    base_elevation = 500.0
    elevation = base_elevation + 300.0 * math.sin(lat * 0.1) * math.cos(lon * 0.1)
    
    # Slope: mock as 15-25 degrees in mountainous region
    slope_deg = 15.0 + 10.0 * abs(math.sin(lon * 0.2))
    
    return {
        "elevation_m": round(elevation, 1),
        "slope_deg": round(slope_deg, 1),
    }


def get_fuel_type(lon: float, lat: float) -> Dict[str, Any]:
    """
    Mock: Get fuel type classification and properties.
    
    Fuel models (simplified, based on NFFL - National Fire-Fuel Laboratory):
    - "grassland": light, fast-burning
    - "shrubland": moderate, typical wildfire
    - "forest": heavy, slow-burning but intense
    """
    # Simplified mock: use lat/lon to pick fuel type
    fuel_idx = int((lat + lon) * 10) % 3
    
    fuel_types = {
        0: {
            "model": "grassland",
            "dead_fuel_load_tn_ha": 2.0,      # tons/hectare of dead fuel
            "live_fuel_load_tn_ha": 3.0,      # tons/hectare of live fuel
            "fuel_bed_depth_m": 0.3,           # meters
            "surface_area_to_volume": 4000.0,  # ft²/ft³ (Rothermel input)
            "fuel_moisture_dead_pct": 8.0,     # dead fuel moisture
            "fuel_moisture_live_pct": 80.0,    # live fuel moisture
        },
        1: {
            "model": "shrubland",
            "dead_fuel_load_tn_ha": 4.5,
            "live_fuel_load_tn_ha": 5.0,
            "fuel_bed_depth_m": 0.6,
            "surface_area_to_volume": 2500.0,
            "fuel_moisture_dead_pct": 10.0,
            "fuel_moisture_live_pct": 75.0,
        },
        2: {
            "model": "forest",
            "dead_fuel_load_tn_ha": 8.0,
            "live_fuel_load_tn_ha": 15.0,
            "fuel_bed_depth_m": 1.0,
            "surface_area_to_volume": 1500.0,
            "fuel_moisture_dead_pct": 12.0,
            "fuel_moisture_live_pct": 90.0,
        },
    }
    
    return fuel_types[fuel_idx]


def get_weather_at_location(lon: float, lat: float) -> Dict[str, float]:
    """
    Mock: Get weather data (temperature, humidity, wind).
    
    In production, call OpenWeatherMap or similar:
        https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid=...
    """
    # Simplified mock: base conditions for Serra da Estrela
    temperature_c = 18.0 + 5.0 * math.sin(lat * 0.1)
    relative_humidity_pct = 45.0 + 20.0 * math.cos(lon * 0.1)
    wind_speed_ms = 6.0 + 3.0 * abs(math.sin(lon * 0.15))
    wind_direction_deg = (225.0 + 30.0 * math.sin(lat * 0.1)) % 360.0
    
    return {
        "temperature_c": round(temperature_c, 1),
        "relative_humidity_pct": round(relative_humidity_pct, 1),
        "wind_speed_ms": round(wind_speed_ms, 1),
        "wind_direction_deg": round(wind_direction_deg, 1),
    }


def fetch_environmental_data(
    ignition_lon: float,
    ignition_lat: float,
) -> Dict[str, Any]:
    """
    Fetch all environmental data for a location.
    
    Returns a dict with elevation, slope, fuel type, and weather.
    This is the "one-stop shop" to call before running a simulation.
    """
    elevation_data = get_elevation_and_slope(ignition_lon, ignition_lat)
    fuel_data = get_fuel_type(ignition_lon, ignition_lat)
    weather_data = get_weather_at_location(ignition_lon, ignition_lat)
    
    return {
        "elevation_m": elevation_data["elevation_m"],
        "slope_deg": elevation_data["slope_deg"],
        "fuel_type": fuel_data["model"],
        "fuel": fuel_data,
        "weather": weather_data,
    }
