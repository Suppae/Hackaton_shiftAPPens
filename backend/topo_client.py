"""
Open Topo Data client — SRTM30m dataset (NASA Shuttle Radar Topography Mission).

Endpoint: https://api.opentopodata.org/v1/srtm30m
Free, no key needed, rate limit ~1 req/sec.

Provides:
- Batch elevation lookups (up to 100 points per request)
- Slope calculation via numerical finite differences (∂z/∂x, ∂z/∂y)

The slope factor (Φ_S) for the fire model is computed here so fire_engine.py
stays clean: it just asks "what's the slope factor from cell A to cell B?"
"""

import json
import math
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


TOPO_BASE_URL = "https://api.opentopodata.org/v1/srtm30m"
HTTP_TIMEOUT_SECONDS = 6
MAX_POINTS_PER_REQUEST = 100

# Module-level elevation cache: { (lat_r, lon_r): elevation_m }
_elev_cache: Dict[Tuple[float, float], float] = {}


def _cache_key(lat: float, lon: float) -> Tuple[float, float]:
    return (round(lat, 5), round(lon, 5))


def fetch_elevations(
    points: List[Tuple[float, float]],
) -> List[Optional[float]]:
    """
    Fetch elevations for a list of (lat, lon) tuples.

    Returns list of elevations in meters (same order as input).
    Uses cache aggressively — SRTM data is static, no TTL needed.
    On failure, returns None for each point (engine handles gracefully).
    """
    results: List[Optional[float]] = [None] * len(points)
    to_fetch: List[Tuple[int, float, float]] = []  # (original_idx, lat, lon)

    # Check cache first
    for i, (lat, lon) in enumerate(points):
        ck = _cache_key(lat, lon)
        if ck in _elev_cache:
            results[i] = _elev_cache[ck]
        else:
            to_fetch.append((i, lat, lon))

    if not to_fetch:
        return results

    # Batch into chunks of MAX_POINTS_PER_REQUEST
    for chunk_start in range(0, len(to_fetch), MAX_POINTS_PER_REQUEST):
        chunk = to_fetch[chunk_start:chunk_start + MAX_POINTS_PER_REQUEST]
        locations_str = "|".join(f"{lat},{lon}" for _, lat, lon in chunk)
        url = f"{TOPO_BASE_URL}?locations={locations_str}"

        try:
            with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            api_results = data.get("results", [])
            for j, entry in enumerate(api_results):
                elev = entry.get("elevation")
                if elev is not None:
                    orig_idx = chunk[j][0]
                    lat, lon = chunk[j][1], chunk[j][2]
                    results[orig_idx] = float(elev)
                    _elev_cache[_cache_key(lat, lon)] = float(elev)

        except Exception as exc:
            print(f"[topo_client] Elevation fetch failed: {exc!r} — affected {len(chunk)} points")

    return results


def compute_slope_factor(
    elev_from: Optional[float],
    elev_to: Optional[float],
    distance_m: float,
) -> float:
    """
    Compute the slope factor (Φ_S) between two cells using finite differences.

    Slope angle θ via: tan(θ) = Δz / Δx  (numerical derivative)

    The Rothermel-inspired slope factor:
        Φ_S = 5.275 * β^{-0.3} * (tan θ)^2   (simplified)

    For the hackathon we use a simpler but visually equivalent formula:
        - Uphill  (Δz > 0): Φ_S = 1 + 2.0 * tan(θ)   (fire accelerates)
        - Flat    (Δz ≈ 0): Φ_S = 1.0
        - Downhill(Δz < 0): Φ_S = max(0.3, 1 - 0.5 * |tan(θ)|)  (fire slows)

    This is simplified but preserves the critical behavior: fire charges
    uphill and crawls downhill. Good enough for a hackathon demo.

    Args:
        elev_from: elevation of source cell (meters), or None if unknown
        elev_to: elevation of destination cell (meters), or None if unknown
        distance_m: horizontal distance between cells (meters)

    Returns:
        Slope factor multiplier (>0). 1.0 = flat, >1 = uphill boost, <1 = downhill drag.
    """
    if elev_from is None or elev_to is None or distance_m <= 0:
        return 1.0  # no data → assume flat

    dz = elev_to - elev_from                    # Δz (finite difference numerator)
    tan_theta = dz / distance_m                 # Δz/Δx (finite difference derivative)

    if tan_theta > 0:
        # Uphill: fire accelerates. Cap at 3x to avoid absurd values on cliffs.
        return min(3.0, 1.0 + 2.0 * tan_theta)
    elif tan_theta < 0:
        # Downhill: fire decelerates. Floor at 0.3 (fire never fully stops from slope alone).
        return max(0.3, 1.0 - 0.5 * abs(tan_theta))
    else:
        return 1.0


def get_slope_between(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """
    Convenience: fetch elevations for two points and return the slope factor.
    Caches aggressively, so repeated calls for the same grid are cheap.
    """
    elevs = fetch_elevations([(lat1, lon1), (lat2, lon2)])

    # Haversine-lite distance (good enough at short range)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    avg_lat = math.radians((lat1 + lat2) / 2.0)
    dx = dlon * math.cos(avg_lat) * 6_371_000
    dy = dlat * 6_371_000
    dist_m = math.sqrt(dx * dx + dy * dy)

    return compute_slope_factor(elevs[0], elevs[1], dist_m)
