"""
OpenWeatherMap v2.5 client.

Endpoint: https://api.openweathermap.org/data/2.5/weather
NOT v3.0 (OneCall) — that requires a separate subscription and returns 401
on the standard free key.

Provides:
- Wind speed (m/s, since we use units=metric)
- Wind direction in METEOROLOGICAL convention: degrees clockwise from
  North, indicating where the wind blows FROM. (Same convention as
  the rest of the codebase.)
- Relative humidity (%)
- Temperature (°C) — bonus, used for drying factor

Includes:
- 5-minute in-memory cache (hackathon: weather doesn't change every second)
- Graceful fallback to sensible defaults if the API fails
- No external HTTP dependencies — uses urllib (stdlib)
"""

import json
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from typing import Dict, Optional, Tuple


OWM_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
CACHE_TTL_SECONDS = 300  # 5 min
HTTP_TIMEOUT_SECONDS = 4


@dataclass
class WeatherSnapshot:
    """Weather state at a given lat/lon at a given moment."""
    wind_speed_ms: float           # meters per second
    wind_direction_deg: float      # 0..360, FROM direction, clockwise from N
    humidity_pct: float            # 0..100
    temperature_c: float           # °C
    source: str                    # "owm" | "fallback"
    location_name: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


# Module-level cache: { (lat_rounded, lon_rounded): (timestamp, snapshot) }
_cache: Dict[Tuple[float, float], Tuple[float, WeatherSnapshot]] = {}


def _cache_key(lat: float, lon: float) -> Tuple[float, float]:
    # Round to 2 decimals (~1 km grid). Avoids cache misses for nearby cells.
    return (round(lat, 2), round(lon, 2))


def _fallback_snapshot() -> WeatherSnapshot:
    """Return reasonable defaults so the simulation never breaks."""
    return WeatherSnapshot(
        wind_speed_ms=5.0,
        wind_direction_deg=270.0,  # wind from W -> fire spreads E
        humidity_pct=35.0,
        temperature_c=25.0,
        source="fallback",
    )


def get_weather(
    lat: float,
    lon: float,
    api_key: Optional[str] = None,
) -> WeatherSnapshot:
    """
    Fetch current weather at (lat, lon).

    Args:
        lat, lon: WGS84 coordinates.
        api_key: OpenWeatherMap key. If None, reads OWM_API_KEY env var.

    Returns:
        WeatherSnapshot — always succeeds; falls back to defaults on error.
    """
    key = api_key or os.environ.get("OWM_API_KEY", "").strip()

    if not key:
        return _fallback_snapshot()

    # Cache hit?
    ck = _cache_key(lat, lon)
    cached = _cache.get(ck)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return cached[1]

    params = urllib.parse.urlencode({
        "lat": f"{lat:.4f}",
        "lon": f"{lon:.4f}",
        "units": "metric",
        "appid": key,
    })
    url = f"{OWM_BASE_URL}?{params}"

    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # Defensive parsing — if any field missing, fall back per-field
        wind = data.get("wind", {}) or {}
        main = data.get("main", {}) or {}

        snapshot = WeatherSnapshot(
            wind_speed_ms=float(wind.get("speed", 5.0)),
            wind_direction_deg=float(wind.get("deg", 270.0)) % 360.0,
            humidity_pct=float(main.get("humidity", 35.0)),
            temperature_c=float(main.get("temp", 25.0)),
            source="owm",
            location_name=data.get("name"),
        )

        _cache[ck] = (time.time(), snapshot)
        return snapshot

    except Exception as exc:
        # Log but never crash — the demo continues with fallback.
        print(f"[weather_client] OWM fetch failed: {exc!r} — using fallback")
        return _fallback_snapshot()
