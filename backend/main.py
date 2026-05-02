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
from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from mock_engine import generate_fire_timesteps as mock_fire
from fire_engine import simulate as ca_fire
from weather_client import get_weather, WeatherSnapshot


app = FastAPI(title="Wildfire Routing MVP", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    # Optional weather overrides. If None the engine fetches from OpenWeatherMap.
    wind_speed_ms: Optional[float] = Field(None, ge=0.0, le=50.0)
    wind_direction_deg: Optional[float] = Field(
        None, ge=0.0, lt=360.0,
        description="Meteorological: degrees clockwise from North, FROM where wind blows",
    )
    humidity_pct: Optional[float] = Field(None, ge=0.0, le=100.0)


class TimestepFeature(BaseModel):
    t: int
    minutes_elapsed: int
    burned_area: Dict[str, Any]


class SimulationResponse(BaseModel):
    ignition: List[float]
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
    # auto: CA if OWM key available
    if os.environ.get("OWM_API_KEY", "").strip():
        return "ca"
    return "mock"


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
) -> SimulationResponse:

    if engine == "ca":
        # Build weather: full override, partial override + OWM, or pure OWM
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

        try:
            timesteps_raw = ca_fire(
                ignition_lon=ignition_lon,
                ignition_lat=ignition_lat,
                weather=weather,
                n_steps=n_steps,
                minutes_per_step=minutes_per_step,
                use_topo=use_topo,
            )
            actual_engine = "ca"
            if weather is None:
                weather = get_weather(ignition_lat, ignition_lon)

        except Exception as exc:
            print(f"[main] CA engine failed: {exc!r} — falling back to mock")
            weather = weather or get_weather(ignition_lat, ignition_lon)
            timesteps_raw = mock_fire(
                ignition_lon=ignition_lon,
                ignition_lat=ignition_lat,
                wind_speed_ms=weather.wind_speed_ms,
                wind_direction_deg=weather.wind_direction_deg,
                humidity_pct=weather.humidity_pct,
                n_steps=n_steps,
                minutes_per_step=minutes_per_step,
            )
            actual_engine = "mock(fallback)"
    else:
        ws = wind_speed_ms if wind_speed_ms is not None else 5.0
        wd = wind_direction_deg if wind_direction_deg is not None else 270.0
        hm = humidity_pct if humidity_pct is not None else 35.0
        weather = WeatherSnapshot(
            wind_speed_ms=ws, wind_direction_deg=wd, humidity_pct=hm,
            temperature_c=25.0, source="mock-default",
        )
        timesteps_raw = mock_fire(
            ignition_lon=ignition_lon,
            ignition_lat=ignition_lat,
            wind_speed_ms=ws,
            wind_direction_deg=wd,
            humidity_pct=hm,
            n_steps=n_steps,
            minutes_per_step=minutes_per_step,
        )
        actual_engine = "mock"

    return SimulationResponse(
        ignition=[ignition_lon, ignition_lat],
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
        },
        timesteps=[TimestepFeature(**ts) for ts in timesteps_raw],
    )


# --------------------------------------------------------------------------- #
# Routes                                                                      #
# --------------------------------------------------------------------------- #

@app.get("/")
def root() -> Dict[str, str]:
    has_owm = bool(os.environ.get("OWM_API_KEY", "").strip())
    return {
        "status": "ok",
        "service": "wildfire-routing-mvp",
        "owm_configured": str(has_owm),
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
    )


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
