## Introduction
This project was developed as part of the ShiftAPPens competition, organized by
NEI (Núcleo de Estudantes de Informática) and JeK (junior enterprise). Over 48 hours,
together with 3 friends, we had the opportunity to develop a project of our choice.

## Project description
The application our group chose to develop predicts where a wildfire is likely to
spread, based on weather data and terrain conditions. To do this, we used the
**Rothermel model**, a mathematical model commonly used in forecasting wildfire
spread, which calculates the rate at which fire advances based on vegetation type,
wind, terrain slope, and humidity.

The application integrates APIs providing real-world environmental data, such as:

Wind, humidity, and temperature, obtained through Open-Meteo.

Elevation and slope, obtained through Open Topo Data.

Vegetation, obtained through Google Earth Engine.

Map, built using Mapbox.

Using this data, the backend calculates, for each time instant, the area expected
to be burning, returning this information in GeoJSON format, ready to be drawn
directly on the map through the frontend, built with React, Vite, and Mapbox GL.

## How to run the project
To run the backend, you need to enter the `backend` folder, install the dependencies
listed in `requirements.txt`, and start the server with `uvicorn`:

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Interactive API documentation is available at `http://localhost:8000/docs`.

To run the frontend, you need to enter the `frontend/app` folder, install the
dependencies with `npm install`, and then run the development server:

```bash
cd frontend/app
npm install
npm run dev
```
