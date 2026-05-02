"""
Wildfire Routing MVP — Backend entrypoint.

Runs:
    OWM_API_KEY=your_key uvicorn main:app --reload --port 8000

Endpoints:
    GET  /              -> health
    POST /simulate      -> run fire simulation (CA real engine, mock fallback)
    GET  /simulate/demo -> hardcoded Serra da Estrela scenario for live demo
"""

import json
import math
import os
import urllib.request
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from mock_engine import generate_fire_timesteps as mock_fire
from fire_engine import simulate as ca_fire, compute_bbox_polygon
from fire_engine import (
    _estimate_dfmc,
    _compute_no_wind_ros,
    _wind_factor as ca_wind_factor,
    _moisture_damping as ca_moisture_damping,
    FUEL_MODELS,
    DEFAULT_FUEL_MODEL,
)
from weather_client import get_weather, WeatherSnapshot


app = FastAPI(title="Wildfire Routing MVP", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# GEE provider — lazy singleton, only active when GEE_CREDENTIALS_PATH is set #
# --------------------------------------------------------------------------- #

_gee_provider = None

def _get_gee_provider():
    global _gee_provider
    if _gee_provider is not None:
        return _gee_provider
    # Requires GEE_API_KEY (JSON string) set in environment
    if not os.environ.get("GEE_API_KEY", "").strip():
        return None
    try:
        from infrasctuture.fuel.EarthEngineCLCProvider import EarthEngineCLCProvider
        _gee_provider = EarthEngineCLCProvider()
        print("[main] GEE provider initialised via GEEAuthSingleton")
        return _gee_provider
    except Exception as exc:
        print(f"[main] GEE provider init failed: {exc!r}")
        return None


# --------------------------------------------------------------------------- #
# Schemas                                                                     #
# --------------------------------------------------------------------------- #

class EngineChoice(str, Enum):
    auto = "auto"   # CA if OWM key exists, else mock
    ca = "ca"       # force real CA
    mock = "mock"   # force mock


class SimulationRequest(BaseModel):
    ignition_lon: float = Field(..., description="Ignition longitude (WGS84)")
    ignition_lat: float = Field(..., description="Ignition latitude (WGS84)")
    n_steps: int = Field(6, ge=1, le=24)
    minutes_per_step: int = Field(10, ge=1, le=60)
    engine: EngineChoice = Field(EngineChoice.auto)
    use_topo: bool = Field(True, description="Fetch real elevation from SRTM")

    # Optional weather overrides
    wind_speed_ms: Optional[float] = Field(None, ge=0.0, le=50.0)
    wind_direction_deg: Optional[float] = Field(
        None, ge=0.0, lt=360.0,
        description="Meteorological: degrees clockwise from North, FROM where wind blows",
    )
    humidity_pct: Optional[float] = Field(None, ge=0.0, le=100.0)

    # Fire origin — forwarded into the response for the frontend to display
    source: Optional[str] = Field(
        "manual",
        description="Origin of the fire report: 'nasa_firms', 'prociv', or 'manual'",
    )


class TimestepFeature(BaseModel):
    t: int
    minutes_elapsed: int
    burned_area: Dict[str, Any]
    burning_front: Optional[Dict[str, Any]] = None  # individual cell squares of active fire front


class VectorsPayload(BaseModel):
    primary_spread_angle: float = Field(
        description="Geographic bearing (0=N, 90=E, CW) of dominant fire spread"
    )
    wind_angle: float = Field(
        description="Meteorological wind FROM direction (0=N, CW)"
    )
    speed_m_per_min: float = Field(
        description="Estimated fire spread speed in m/min"
    )


class EnvironmentalData(BaseModel):
    temperature_c: float
    humidity_pct: float
    wind_speed_kmh: float
    fuel_load_mean: float = Field(description="Mean fuel load from GEE (0–1.5+); 0.42 if no GEE")
    ndvi_mean: float = Field(description="Mean NDVI from GEE (0–1); 0.5 if no GEE")


class SimulationResponse(BaseModel):
    ignition: List[float]
    source: str
    vectors: VectorsPayload
    environmental_data: EnvironmentalData
    metadata: Dict[str, Any]
    timesteps: List[TimestepFeature]


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #

def _resolve_engine(choice: EngineChoice) -> str:
    if choice == EngineChoice.mock:
        return "mock"
    # "auto" and "ca" always run the real CA engine.
    # Weather comes from Open-Meteo (no key needed); mock only as inner fallback.
    return "ca"


def _meteo_to_math_rad(wind_from_deg: float) -> float:
    """Convert meteorological wind FROM direction to math angle (CCW from East)."""
    return math.radians((270.0 - wind_from_deg) % 360.0)


def _compute_spread_angle(
    wind_speed_ms: float,
    wind_direction_deg: float,
    temperature_c: float,
    humidity_pct: float,
    elev_ignition: Optional[float],
    elev_n: Optional[float],
    elev_s: Optional[float],
    elev_e: Optional[float],
    elev_w: Optional[float],
    cell_size_m: float = 120.0,
) -> Tuple[float, float]:
    """
    Compute the dominant fire spread bearing using Rothermel-inspired physics.

    Fire spread direction is the resultant vector of:
      - Wind (pushes fire downwind)
      - Slope (pushes fire uphill, weighted at 0.3×)

    Rate of spread uses full fuel + wind + slope + moisture model:
      ROS = ROS_0 × Φ_W × Φ_S × η_M

    Returns (primary_spread_angle_deg, speed_m_per_min).
    """
    wind_rad = _meteo_to_math_rad(wind_direction_deg)

    # ── Wind vector in math coords (CCW from East) ──
    wx = wind_speed_ms * math.cos(wind_rad)
    wy = wind_speed_ms * math.sin(wind_rad)

    # ── Slope vector: steepest uphill from 4 cardinal neighbours ──
    sx, sy = 0.0, 0.0
    best_slope = 0.0
    if elev_ignition is not None:
        best_dx, best_dy = 0.0, 0.0

        directions = [
            (-1, 0, elev_n),  # North
            ( 1, 0, elev_s),  # South
            ( 0, 1, elev_e),  # East
            ( 0,-1, elev_w),  # West
        ]
        for dr, dc, elev_nbr in directions:
            if elev_nbr is not None:
                rise = elev_nbr - elev_ignition
                if rise > 0:
                    dist_m = math.sqrt(dr * dr + dc * dc) * cell_size_m
                    slope_pct = rise / dist_m
                    if slope_pct > best_slope:
                        best_slope = slope_pct
                        dx = float(dc)
                        dy = float(-dr)
                        best_dx, best_dy = dx, dy

        if best_slope > 0:
            angle_rad = math.atan2(best_dy, best_dx)
            slope_mag = min(best_slope * 200.0, wind_speed_ms)
            sx = slope_mag * math.cos(angle_rad)
            sy = slope_mag * math.sin(angle_rad)

    # ── Combine: wind dominates, slope nudges ──
    cx = wx + 0.3 * sx
    cy = wy + 0.3 * sy

    # Math angle (CCW from E) → geographic bearing (CW from N)
    primary_angle = (90.0 - math.degrees(math.atan2(cy, cx))) % 360.0

    # ── Rothermel Rate of Spread ──
    fuel = FUEL_MODELS[DEFAULT_FUEL_MODEL]
    dfmc = _estimate_dfmc(humidity_pct, temperature_c)
    ros_base = _compute_no_wind_ros(
        fuel["load"], fuel["savr"], fuel["heat"],
        fuel["depth"], dfmc, fuel["m_ext"],
    )

    # Wind factor in primary spread direction
    phi_w = ca_wind_factor(wind_speed_ms, wind_rad, wind_rad)

    # Slope factor
    phi_s = 1.0
    if best_slope > 0:
        phi_s = min(5.0, 1.0 + 2.0 * best_slope)

    # Moisture damping
    eta_m = ca_moisture_damping(humidity_pct, temperature_c)

    # Combined ROS: R = R_0 × Φ_W × Φ_S × η_M
    ros_m_per_s = ros_base * phi_w * phi_s * eta_m
    speed_m_per_min = max(0.5, ros_m_per_s * 60.0)

    return primary_angle, speed_m_per_min


def _run_simulation(
    ignition_lon: float,
    ignition_lat: float,
    n_steps: int,
    minutes_per_step: int,
    engine: str,
    use_topo: bool,
    wind_speed_ms: Optional[float],
    wind_direction_deg: Optional[float],
    humidity_pct: Optional[float],
    source: str = "manual",
) -> SimulationResponse:

    # ── 1. FETCH WEATHER REAL (sempre — independente do motor) ─────────
    if wind_speed_ms is not None and wind_direction_deg is not None and humidity_pct is not None:
        weather = WeatherSnapshot(
            wind_speed_ms=wind_speed_ms,
            wind_direction_deg=wind_direction_deg,
            humidity_pct=humidity_pct,
            temperature_c=25.0,
            source="override",
        )
    else:
        weather = get_weather(ignition_lat, ignition_lon)
        if wind_speed_ms is not None:
            weather.wind_speed_ms = wind_speed_ms
        if wind_direction_deg is not None:
            weather.wind_direction_deg = wind_direction_deg
        if humidity_pct is not None:
            weather.humidity_pct = humidity_pct

    # ── 2. FETCH ELEVATION + COMPUTE SPREAD ANGLE (sempre) ─────────────
    elev_ignition: Optional[float] = None
    elev_n: Optional[float] = None
    elev_s: Optional[float] = None
    elev_e: Optional[float] = None
    elev_w: Optional[float] = None

    if use_topo:
        from topo_client import fetch_elevations as _fetch_topo
        dlat = 120.0 / 111_320.0
        dlon = 120.0 / (111_320.0 * math.cos(math.radians(ignition_lat)))
        points = [
            (ignition_lat, ignition_lon),                # ignition
            (ignition_lat + dlat, ignition_lon),         # N
            (ignition_lat - dlat, ignition_lon),         # S
            (ignition_lat, ignition_lon + dlon),         # E
            (ignition_lat, ignition_lon - dlon),         # W
        ]
        elevs = _fetch_topo(points)
        elev_ignition = elevs[0] if elevs[0] is not None else None
        elev_n = elevs[1] if elevs[1] is not None else None
        elev_s = elevs[2] if elevs[2] is not None else None
        elev_e = elevs[3] if elevs[3] is not None else None
        elev_w = elevs[4] if elevs[4] is not None else None

        if elev_ignition is not None:
            max_slope = 0.0
            for nbr in [elev_n, elev_s, elev_e, elev_w]:
                if nbr is not None:
                    s = abs(nbr - elev_ignition) / 120.0
                    max_slope = max(max_slope, s)
            weather.temperature_c += max_slope * 2
            print(f"[main] Elevation: {elev_ignition:.0f}m, max_slope: {max_slope:.3f}")

    # Compute spread angle using wind + slope (Rothermel-inspired)
    spread_angle, spread_speed = _compute_spread_angle(
        weather.wind_speed_ms,
        weather.wind_direction_deg,
        weather.temperature_c,
        weather.humidity_pct,
        elev_ignition, elev_n, elev_s, elev_e, elev_w,
    )

    # Determine engine tag
    has_real_elevation = elev_ignition is not None
    topo_tag = "" if has_real_elevation else "(no topo)"

    if engine == "ca":
        # ── Fetch GEE satellite data (optional) ──────────────────────────
        gee_layers = None
        gee_provider = _get_gee_provider()
        if gee_provider is not None:
            bbox = compute_bbox_polygon(ignition_lon, ignition_lat, 40, 120.0)
            fire_month = datetime.now().month
            try:
                gee_layers = gee_provider.get_fuel_grid(bbox, fire_month=fire_month)
                print(f"[main] GEE data fetched for month={fire_month}")
            except Exception as exc:
                print(f"[main] GEE fetch failed: {exc!r} — proceeding without satellite data")

        # ── Run CA engine ─────────────────────────────────────────────────
        try:
            result = ca_fire(
                ignition_lon=ignition_lon,
                ignition_lat=ignition_lat,
                weather=weather,
                n_steps=n_steps,
                minutes_per_step=minutes_per_step,
                use_topo=use_topo,
                gee_layers=gee_layers,
            )
            actual_engine = "ca" + ("+gee" if gee_layers is not None else "") + topo_tag

        except Exception as exc:
            print(f"[main] CA engine failed: {exc!r} — falling back to mock")
            raw_timesteps = mock_fire(
                ignition_lon=ignition_lon,
                ignition_lat=ignition_lat,
                wind_speed_ms=weather.wind_speed_ms,
                wind_direction_deg=weather.wind_direction_deg,
                humidity_pct=weather.humidity_pct,
                n_steps=n_steps,
                minutes_per_step=minutes_per_step,
            )
            result = {
                "timesteps": raw_timesteps,
                "primary_spread_angle": spread_angle,
                "wind_angle": weather.wind_direction_deg,
                "speed_m_per_min": spread_speed,
                "fuel_load_mean": 0.42,
                "ndvi_mean": 0.5,
                "bbox_polygon": compute_bbox_polygon(ignition_lon, ignition_lat, 40, 120.0),
            }
            actual_engine = "mock(fallback from ca)"

    else:
        raw_timesteps = mock_fire(
            ignition_lon=ignition_lon,
            ignition_lat=ignition_lat,
            wind_speed_ms=weather.wind_speed_ms,
            wind_direction_deg=weather.wind_direction_deg,
            humidity_pct=weather.humidity_pct,
            n_steps=n_steps,
            minutes_per_step=minutes_per_step,
        )
        result = {
            "timesteps": raw_timesteps,
            "primary_spread_angle": spread_angle,
            "wind_angle": weather.wind_direction_deg,
            "speed_m_per_min": spread_speed,
            "fuel_load_mean": 0.42,
            "ndvi_mean": 0.5,
            "bbox_polygon": compute_bbox_polygon(ignition_lon, ignition_lat, 40, 120.0),
        }
        actual_engine = "mock" + topo_tag

    return SimulationResponse(
        ignition=[ignition_lon, ignition_lat],
        source=source,
        vectors=VectorsPayload(
            primary_spread_angle=result["primary_spread_angle"],
            wind_angle=result["wind_angle"],
            speed_m_per_min=result["speed_m_per_min"],
        ),
        environmental_data=EnvironmentalData(
            temperature_c=weather.temperature_c,
            humidity_pct=weather.humidity_pct,
            wind_speed_kmh=round(weather.wind_speed_ms * 3.6, 1),
            fuel_load_mean=result["fuel_load_mean"],
            ndvi_mean=result["ndvi_mean"],
        ),
        metadata={
            "engine": actual_engine,
            "wind_speed_ms": weather.wind_speed_ms,
            "wind_direction_deg": weather.wind_direction_deg,
            "humidity_pct": weather.humidity_pct,
            "temperature_c": weather.temperature_c,
            "weather_source": weather.source,
            "location_name": weather.location_name,
            "n_steps": n_steps,
            "minutes_per_step": minutes_per_step,
            "use_topo": use_topo,
            "bbox_polygon": result["bbox_polygon"],
        },
        timesteps=[TimestepFeature(**ts) for ts in result["timesteps"]],
    )


# --------------------------------------------------------------------------- #
# Routes                                                                      #
# --------------------------------------------------------------------------- #

@app.get("/")
def root() -> Dict[str, str]:
    has_owm = bool(os.environ.get("OWM_API_KEY", "").strip())
    has_gee = bool(os.environ.get("GEE_API_KEY", "").strip())
    return {
        "status": "ok",
        "service": "wildfire-routing-mvp",
        "owm_configured": str(has_owm),
        "gee_configured": str(has_gee),
        "default_engine": "ca",
    }


@app.post("/simulate", response_model=SimulationResponse)
def simulate(req: SimulationRequest) -> SimulationResponse:
    engine = _resolve_engine(req.engine)
    return _run_simulation(
        ignition_lon=req.ignition_lon,
        ignition_lat=req.ignition_lat,
        n_steps=req.n_steps,
        minutes_per_step=req.minutes_per_step,
        engine=engine,
        use_topo=req.use_topo,
        wind_speed_ms=req.wind_speed_ms,
        wind_direction_deg=req.wind_direction_deg,
        humidity_pct=req.humidity_pct,
        source=req.source or "manual",
    )


@app.get("/active-fires")
def active_fires() -> Dict[str, Any]:
    """
    Tenta ir buscar fogos reais. Se a rede falhar, 
    usa um FALLBACK para a demo nunca crachar!
    """
    try:
        # Usamos o endpoint web mais estável
        url = "https://api.fogos.pt/new/fires"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        fires = data.get("data", [])
        features = []
        for fire in fires:
            # Filtra apenas se tiver coordenadas válidas
            if not fire.get("lng") or not fire.get("lat"):
                continue
                
            features.append({
                "type": "Feature",
                "geometry": { "type": "Point", "coordinates": [fire["lng"], fire["lat"]] },
                "properties": {
                    "id": fire.get("id"),
                    "town": fire.get("town"),
                    "status": fire.get("status"),
                    "man": fire.get("man"), # Bombeiros
                    "terrain": fire.get("terrain")
                }
            })
            
        # Se a API estiver vazia de momento, forçamos o fallback para termos o que mostrar
        if not features:
            raise ValueError("Sem fogos ativos na API real no momento.")

        return {
            "source": "fogos_pt",
            "type": "FeatureCollection",
            "features": features
        }

    except Exception as exc:
        print(f"[main] Fogos.pt fetch failed: {exc!r}. ATIVANDO FALLBACK DE EMERGÊNCIA!")
        
        # O NOSSO SEGURO DE VIDA PARA A DEMO
        return {
            "source": "mock_fallback",
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": { "type": "Point", "coordinates": [-8.4750, 40.8330] }, 
                    "properties": { "id": "mock1", "town": "Oliveira de Azeméis", "status": "Em Curso", "man": 150 }
                },
                {
                    "type": "Feature",
                    "geometry": { "type": "Point", "coordinates": [-7.6167, 40.3217] }, 
                    "properties": { "id": "mock2", "town": "Serra da Estrela", "status": "Em Curso", "man": 85 }
                },
                {
                    "type": "Feature",
                    "geometry": { "type": "Point", "coordinates": [-8.5530, 37.3140] }, 
                    "properties": { "id": "mock3", "town": "Monchique", "status": "Em Curso", "man": 45 }
                }
            ]
        }
# --------------------------------------------------------------------------- #
# Diagnostic endpoints — test APIs in isolation                               #
# --------------------------------------------------------------------------- #

@app.get("/weather")
def weather(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
) -> Dict[str, Any]:
    snapshot = get_weather(lat, lon)
    return snapshot.to_dict()


@app.get("/elevation")
def elevation(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
) -> Dict[str, Any]:
    from topo_client import fetch_elevations, compute_slope_factor

    dlat = 120.0 / 111_320.0
    points = [(lat, lon), (lat + dlat, lon)]
    elevs = fetch_elevations(points)

    slope = compute_slope_factor(elevs[0], elevs[1], 120.0)

    return {
        "location": {"lat": lat, "lon": lon},
        "elevation_m": elevs[0],
        "nearby_point": {
            "lat": round(lat + dlat, 6),
            "lon": lon,
            "elevation_m": elevs[1],
        },
        "slope_factor": round(slope, 4),
        "slope_explanation": (
            "1.0 = flat | >1.0 = uphill (fire accelerates) | <1.0 = downhill (fire slows)"
        ),
        "source": "opentopodata.org/srtm30m",
    }


@app.get("/simulate/demo")
def simulate_demo(
    engine: EngineChoice = Query(EngineChoice.auto),
) -> Dict[str, Any]:
    """Serra da Estrela scenario for the live demo."""
    resp = _run_simulation(
        ignition_lon=-7.6167,
        ignition_lat=40.3217,
        n_steps=6,
        minutes_per_step=10,
        engine=_resolve_engine(engine),
        use_topo=True,
        wind_speed_ms=8.0,
        wind_direction_deg=225.0,
        humidity_pct=25.0,
    )
    resp_dict = resp.model_dump()
    resp_dict["metadata"]["location"] = "Serra da Estrela, Portugal"
    return resp_dict
