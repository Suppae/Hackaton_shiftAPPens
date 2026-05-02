"""
Weather client — Open-Meteo (primary, free, no key) + OpenWeatherMap (fallback).

Open-Meteo API: https://api.open-meteo.com/v1/forecast
- Completely free, no API key needed
- Returns real-time weather for any WGS84 coordinate
- Data: wind speed (m/s), wind direction (° FROM), humidity (%), temperature (°C)

OpenWeatherMap v2.5: kept as secondary if OWM_API_KEY is set.

Includes:
- 5-minute in-memory cache
- Graceful fallback to defaults only if ALL sources fail
- No external HTTP dependencies — uses urllib (stdlib)
"""

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Tuple


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OWM_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
CACHE_TTL_SECONDS = 300  # 5 min
HTTP_TIMEOUT_SECONDS = 6


@dataclass
class WeatherSnapshot:
    """Weather state at a given lat/lon at a given moment."""
    wind_speed_ms: float           # meters per second
    wind_direction_deg: float      # 0..360, FROM direction, clockwise from N
    humidity_pct: float            # 0..100
    temperature_c: float           # °C
    source: str                    # "open-meteo" | "owm" | "fallback"
    location_name: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


_cache: Dict[Tuple[float, float], Tuple[float, WeatherSnapshot]] = {}


def _cache_key(lat: float, lon: float) -> Tuple[float, float]:
    return (round(lat, 2), round(lon, 2))


def _fallback_snapshot(lat: float, lon: float) -> WeatherSnapshot:
    """
    Last-resort defaults — vary slightly by latitude so not every fire
    shows identical values. North of 40°N gets cooler/windier, south warmer.
    """
    base_wind = 4.0 + (abs(lat - 39.0) * 0.3)
    base_temp = 22.0 - (abs(lat - 37.0) * 0.8)
    base_hum = 30.0 + (abs(lat - 39.0) * 2.0)
    return WeatherSnapshot(
        wind_speed_ms=round(base_wind, 1),
        wind_direction_deg=round(200.0 + (lon % 60), 1),
        humidity_pct=round(min(80.0, base_hum), 1),
        temperature_c=round(base_temp, 1),
        source="fallback",
    )


def _fetch_open_meteo(lat: float, lon: float) -> Optional[WeatherSnapshot]:
    """Fetch real weather from Open-Meteo (free, no API key)."""
    params = urllib.parse.urlencode({
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "ms",
    })
    url = f"{OPEN_METEO_URL}?{params}"

    with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    current = data.get("current", {})
    if not current:
        return None

    return WeatherSnapshot(
        wind_speed_ms=float(current.get("wind_speed_10m", 5.0)),
        wind_direction_deg=float(current.get("wind_direction_10m", 270.0)) % 360.0,
        humidity_pct=float(current.get("relative_humidity_2m", 35.0)),
        temperature_c=float(current.get("temperature_2m", 25.0)),
        source="open-meteo",
        location_name=f"{lat:.2f}°N, {abs(lon):.2f}°W",
    )


def _fetch_owm(lat: float, lon: float, key: str) -> Optional[WeatherSnapshot]:
    """Fetch real weather from OpenWeatherMap v2.5."""
    params = urllib.parse.urlencode({
        "lat": f"{lat:.4f}",
        "lon": f"{lon:.4f}",
        "units": "metric",
        "appid": key,
    })
    url = f"{OWM_BASE_URL}?{params}"

    with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    wind = data.get("wind", {}) or {}
    main = data.get("main", {}) or {}

    return WeatherSnapshot(
        wind_speed_ms=float(wind.get("speed", 5.0)),
        wind_direction_deg=float(wind.get("deg", 270.0)) % 360.0,
        humidity_pct=float(main.get("humidity", 35.0)),
        temperature_c=float(main.get("temp", 25.0)),
        source="owm",
        location_name=data.get("name"),
    )


def get_weather(
    lat: float,
    lon: float,
    api_key: Optional[str] = None,
) -> WeatherSnapshot:
    """
    Fetch current weather at (lat, lon).

    Strategy:
      1. Check cache
      2. Try Open-Meteo (free, no key) — ALWAYS available
      3. Try OpenWeatherMap (if OWM_API_KEY set)
      4. Fallback to location-varying defaults

    Returns WeatherSnapshot — always succeeds.
    """
    ck = _cache_key(lat, lon)
    cached = _cache.get(ck)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]

    # Primary: Open-Meteo (free, real data, no key needed)
    try:
        snapshot = _fetch_open_meteo(lat, lon)
        if snapshot:
            _cache[ck] = (time.time(), snapshot)
            print(f"[weather_client] Open-Meteo OK: ws={snapshot.wind_speed_ms}m/s wd={snapshot.wind_direction_deg}° hum={snapshot.humidity_pct}%")
            return snapshot
    except Exception as exc:
        print(f"[weather_client] Open-Meteo failed: {exc!r}")

    # Secondary: OpenWeatherMap (if key available)
    key = api_key or os.environ.get("OWM_API_KEY", "").strip()
    if key:
        try:
            snapshot = _fetch_owm(lat, lon, key)
            if snapshot:
                _cache[ck] = (time.time(), snapshot)
                print(f"[weather_client] OWM OK: ws={snapshot.wind_speed_ms}m/s wd={snapshot.wind_direction_deg}° hum={snapshot.humidity_pct}%")
                return snapshot
        except Exception as exc:
            print(f"[weather_client] OWM failed: {exc!r}")

    # Last resort
    print(f"[weather_client] All sources failed — using fallback for ({lat:.2f}, {lon:.2f})")
    return _fallback_snapshot(lat, lon)
