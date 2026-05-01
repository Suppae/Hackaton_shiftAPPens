# Wildfire Routing MVP — Backend

## Run

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/docs for the auto-generated Swagger UI.

## Endpoints

| Method | Path              | Purpose                                                    |
|--------|-------------------|------------------------------------------------------------|
| GET    | `/`               | Health check                                               |
| POST   | `/simulate`       | Run simulation with custom ignition + (optional) weather   |
| GET    | `/simulate/demo`  | Hardcoded Serra da Estrela scenario for the live demo      |

## Response contract (this is what the frontend consumes)

```jsonc
{
  "ignition": [-7.6167, 40.3217],            // [lon, lat]
  "metadata": {
    "engine": "mock",                         // "mock" | "ca" later
    "wind_speed_ms": 8.0,
    "wind_direction_deg": 225.0,              // FROM direction, clockwise from N
    "humidity_pct": 25.0,
    "n_steps": 6,
    "minutes_per_step": 10
  },
  "timesteps": [
    {
      "t": 1,
      "minutes_elapsed": 10,
      "burned_area": {
        "type": "Feature",
        "properties": { "timestep": 1, "minutes": 10, "intensity": 0.166, ... },
        "geometry": { "type": "Polygon", "coordinates": [[[lon, lat], ...]] }
      }
    },
    // ... t=2 ... t=N
  ]
}
```

Each `burned_area` is a valid GeoJSON `Feature` and can be dropped straight
into a Mapbox source without transformation.

## Architecture notes

- `main.py` — FastAPI app, schemas, routes. **The route is engine-agnostic.**
- `mock_engine.py` — fast elliptical fire shape generator. Same I/O shape
  as the real Cellular Automaton, so swap is one import line.
- The eventual real engine will live in `fire_engine.py` and will call
  `weather_client.py` (OpenWeatherMap v2.5, NOT v3.0 — avoids 401s) and
  `topo_client.py` (Open Topo Data SRTM30m).
