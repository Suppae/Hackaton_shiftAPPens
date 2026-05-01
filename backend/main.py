"""
Wildfire Routing MVP — Backend entrypoint.

Runs:
    uvicorn main:app --reload --port 8000

Endpoints:
    GET  /              -> health
    POST /simulate      -> run mock fire spread, returns timestep GeoJSONs
    GET  /simulate/demo -> hardcoded Serra da Estrela scenario for the live demo
"""

from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from mock_engine import generate_fire_timesteps


app = FastAPI(title="Wildfire Routing MVP", version="0.1.0")

# Hackathon: allow everything. Tighten before any real deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Schemas — this IS the contract with the frontend. Treat as load-bearing.    #
# --------------------------------------------------------------------------- #

class SimulationRequest(BaseModel):
    ignition_lon: float = Field(..., description="Ignition longitude (WGS84)")
    ignition_lat: float = Field(..., description="Ignition latitude (WGS84)")
    n_steps: int = Field(6, ge=1, le=24, description="Number of timesteps to simulate")
    minutes_per_step: int = Field(10, ge=1, le=60, description="Minutes per timestep")

    # Optional weather override. If None, the real engine would call OpenWeatherMap.
    # In mock mode, sensible defaults are used.
    wind_speed_ms: Optional[float] = Field(None, ge=0.0, le=50.0)
    wind_direction_deg: Optional[float] = Field(
        None, ge=0.0, lt=360.0,
        description="Meteorological: degrees clockwise from North, FROM where wind blows",
    )
    humidity_pct: Optional[float] = Field(None, ge=0.0, le=100.0)


class TimestepFeature(BaseModel):
    t: int
    minutes_elapsed: int
    burned_area: Dict[str, Any]  # GeoJSON Feature (Polygon)


class SimulationResponse(BaseModel):
    ignition: List[float]                # [lon, lat]
    metadata: Dict[str, Any]
    timesteps: List[TimestepFeature]


# --------------------------------------------------------------------------- #
# Routes                                                                      #
# --------------------------------------------------------------------------- #

@app.get("/")
def root() -> Dict[str, str]:
    return {"status": "ok", "service": "wildfire-routing-mvp"}


@app.post("/simulate", response_model=SimulationResponse)
def simulate(req: SimulationRequest) -> SimulationResponse:
    # Mock mode. When the real engine lands, this block reads weather from
    # OpenWeatherMap v2.5 and elevation from Open Topo Data, then calls the CA.
    wind_speed = req.wind_speed_ms if req.wind_speed_ms is not None else 5.0
    wind_dir = req.wind_direction_deg if req.wind_direction_deg is not None else 270.0
    humidity = req.humidity_pct if req.humidity_pct is not None else 35.0

    timesteps_raw = generate_fire_timesteps(
        ignition_lon=req.ignition_lon,
        ignition_lat=req.ignition_lat,
        wind_speed_ms=wind_speed,
        wind_direction_deg=wind_dir,
        humidity_pct=humidity,
        n_steps=req.n_steps,
        minutes_per_step=req.minutes_per_step,
    )

    return SimulationResponse(
        ignition=[req.ignition_lon, req.ignition_lat],
        metadata={
            "engine": "mock",
            "wind_speed_ms": wind_speed,
            "wind_direction_deg": wind_dir,
            "humidity_pct": humidity,
            "n_steps": req.n_steps,
            "minutes_per_step": req.minutes_per_step,
        },
        timesteps=[TimestepFeature(**ts) for ts in timesteps_raw],
    )


@app.get("/simulate/demo")
def simulate_demo() -> Dict[str, Any]:
    """One-shot scenario for the live demo: ignition near Serra da Estrela, PT."""
    ignition_lon, ignition_lat = -7.6167, 40.3217
    timesteps_raw = generate_fire_timesteps(
        ignition_lon=ignition_lon,
        ignition_lat=ignition_lat,
        wind_speed_ms=8.0,
        wind_direction_deg=225.0,  # blowing FROM SW -> fire spreads NE
        humidity_pct=25.0,
        n_steps=6,
        minutes_per_step=10,
    )
    return {
        "ignition": [ignition_lon, ignition_lat],
        "metadata": {
            "engine": "mock",
            "location": "Serra da Estrela, Portugal",
            "wind_speed_ms": 8.0,
            "wind_direction_deg": 225.0,
            "humidity_pct": 25.0,
            "n_steps": 6,
            "minutes_per_step": 10,
        },
        "timesteps": timesteps_raw,
    }
