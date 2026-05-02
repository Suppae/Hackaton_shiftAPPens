"""
Wildfire Routing MVP — Backend entrypoint.

Runs:
    OWM_API_KEY=your_key uvicorn main:app --reload --port 8000

Endpoints:
    GET  /              -> health
    POST /simulate      -> run fire simulation (CA real engine, mock fallback)
    GET  /simulate/demo -> hardcoded Serra da Estrela scenario for live demo
"""

import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from mock_engine import generate_fire_timesteps as mock_fire
from fire_engine import simulate as ca_fire, compute_bbox_polygon
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
    if choice == EngineChoice.ca:
        return "ca"
    if os.environ.get("OWM_API_KEY", "").strip():
        return "ca"
    return "mock"


def _wind_spread_bearing(wind_direction_deg: float) -> float:
    """Geographic bearing (CW from N) where fire spreads due to wind alone."""
    # wind_direction_deg is FROM direction; fire goes downwind = +180°
    return (wind_direction_deg + 180.0) % 360.0


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

    if engine == "ca":
        # ── Build weather snapshot ────────────────────────────────────────
        weather: Optional[WeatherSnapshot] = None
        if wind_speed_ms is not None and wind_direction_deg is not None and humidity_pct is not None:
            weather = WeatherSnapshot(
                wind_speed_ms=wind_speed_ms,
                wind_direction_deg=wind_direction_deg,
                humidity_pct=humidity_pct,
                temperature_c=25.0,
                source="override",
            )
        elif any(v is not None for v in [wind_speed_ms, wind_direction_deg, humidity_pct]):
            weather = get_weather(ignition_lat, ignition_lon)
            if wind_speed_ms is not None:
                weather.wind_speed_ms = wind_speed_ms
            if wind_direction_deg is not None:
                weather.wind_direction_deg = wind_direction_deg
            if humidity_pct is not None:
                weather.humidity_pct = humidity_pct

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
            actual_engine = "ca" + ("+gee" if gee_layers is not None else "")
            if weather is None:
                weather = get_weather(ignition_lat, ignition_lon)

        except Exception as exc:
            print(f"[main] CA engine failed: {exc!r} — falling back to mock")
            weather = weather or get_weather(ignition_lat, ignition_lon)
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
                "primary_spread_angle": round(_wind_spread_bearing(weather.wind_direction_deg), 1),
                "wind_angle": round(weather.wind_direction_deg, 1),
                "speed_m_per_min": round(max(1.0, weather.wind_speed_ms * 0.03 * 60.0), 2),
                "fuel_load_mean": 0.42,
                "ndvi_mean": 0.5,
                "bbox_polygon": compute_bbox_polygon(ignition_lon, ignition_lat, 40, 120.0),
            }
            actual_engine = "mock(fallback)"

    else:
        ws = wind_speed_ms if wind_speed_ms is not None else 5.0
        wd = wind_direction_deg if wind_direction_deg is not None else 270.0
        hm = humidity_pct if humidity_pct is not None else 35.0
        weather = WeatherSnapshot(
            wind_speed_ms=ws, wind_direction_deg=wd, humidity_pct=hm,
            temperature_c=25.0, source="mock-default",
        )
        raw_timesteps = mock_fire(
            ignition_lon=ignition_lon,
            ignition_lat=ignition_lat,
            wind_speed_ms=ws,
            wind_direction_deg=wd,
            humidity_pct=hm,
            n_steps=n_steps,
            minutes_per_step=minutes_per_step,
        )
        result = {
            "timesteps": raw_timesteps,
            "primary_spread_angle": round(_wind_spread_bearing(wd), 1),
            "wind_angle": round(wd, 1),
            "speed_m_per_min": round(max(1.0, ws * 0.03 * 60.0), 2),
            "fuel_load_mean": 0.42,
            "ndvi_mean": 0.5,
            "bbox_polygon": compute_bbox_polygon(ignition_lon, ignition_lat, 40, 120.0),
        }
        actual_engine = "mock"

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
    has_gee = bool(os.environ.get("GEE_CREDENTIALS_PATH", "").strip())
    return {
        "status": "ok",
        "service": "wildfire-routing-mvp",
        "owm_configured": str(has_owm),
        "gee_configured": str(has_gee),
        "default_engine": "ca" if has_owm else "mock",
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


# Portugal mainland bounding box (lon_min, lat_min, lon_max, lat_max)
_PORTUGAL_BBOX = [[-9.5, 36.8], [-6.2, 36.8], [-6.2, 42.2], [-9.5, 42.2]]


@app.get("/active-fires")
def active_fires(
    hours_back: int = Query(24, ge=1, le=168, description="Temporal window in hours"),
) -> Dict[str, Any]:
    """
    Returns active fire points in Portugal from NASA VIIRS (GEE).
    Each point includes lon, lat, FRP (Fire Radiative Power in MW) and confidence.
    Requires GEE_API_KEY to be set; returns empty list otherwise.
    """
    if not os.environ.get("GEE_API_KEY", "").strip():
        return {
            "source": "nasa_viirs",
            "gee_available": False,
            "fire_points": [],
            "hours_back": hours_back,
            "message": "GEE_API_KEY not configured — set it to enable live fire detection",
        }

    try:
        from infrasctuture.fire_recognition.VIIRSFireDetectionProvider import VIIRSFireDetectionProvider
        provider = VIIRSFireDetectionProvider()
        result = provider.get_active_fires(_PORTUGAL_BBOX, hours_back=hours_back)
        return {
            "source": "nasa_viirs",
            "gee_available": True,
            "bbox": _PORTUGAL_BBOX,
            **result,
        }
    except Exception as exc:
        print(f"[main] VIIRS fetch failed: {exc!r}")
        return {
            "source": "nasa_viirs",
            "gee_available": True,
            "fire_points": [],
            "hours_back": hours_back,
            "error": str(exc),
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
