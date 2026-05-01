import React, { useState } from 'react';
import Map, { Source, Layer } from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

const MAPBOX_TOKEN = "pk.eyJ1IjoidGlhZ29tYW5pbmhhIiwiYSI6ImNtb213emZqYTBpdjcyc3M0bHlldWZnc2gifQ.KogqOP6C00qQ8VNtk847Ng";

export default function MapView({ scenario = null, onBack = () => {} }) {
  const [viewState, setViewState] = useState({
    longitude: -8.2520,
    latitude: 40.0935,
    zoom: 12,
    pitch: 45,
    bearing: 0
  });

  // MOCK DATA: arrows
  const predictionArrowsData = {
    type: 'FeatureCollection',
    features: [
      { type: 'Feature', geometry: { type: 'Point', coordinates: [-8.2400, 40.1020] }, properties: { rotation: 20, risk: 'high' } },
      { type: 'Feature', geometry: { type: 'Point', coordinates: [-8.2370, 40.098] }, properties: { rotation: 20, risk: 'high' } },
      { type: 'Feature', geometry: { type: 'Point', coordinates: [-8.2350, 40.0950] }, properties: { rotation: 20, risk: 'medium' } }
    ]
  };

  const arrowsLayerStyle = {
    id: 'prediction-arrows-layer',
    type: 'symbol',
    layout: {
      'text-field': '➤',
      'text-size': 60,
      'text-rotate': ['get', 'rotation'],
      'text-allow-overlap': true,
      'text-ignore-placement': true,
      'text-anchor': 'center',
      'text-offset': [0, -0.2],
      'text-rotation-alignment': 'map',
      'text-pitch-alignment': 'map'
    },
    paint: {
      'text-color': '#ffe066',
      'text-halo-color': '#7a0e0e',
      'text-halo-width': 2
    }
  };

  const firePolygonData = {
    type: 'Feature',
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [-8.2600, 40.0900],
        [-8.2400, 40.0900],
        [-8.2400, 40.1000],
        [-8.2600, 40.1000],
        [-8.2600, 40.0900]
      ]]
    }
  };

  const fireLayerStyle = {
    id: 'fire-layer',
    type: 'fill',
    paint: {
      'fill-color': '#ff8c1a',
      'fill-opacity': 0.55,
      'fill-outline-color': '#e63946'
    }
  };

  return (
    <div style={{ width: '100%', height: '100vh', position: 'relative' }}>
      <div style={{ position: 'absolute', top: 12, left: 12, zIndex: 10 }}>
        <button onClick={onBack} style={{ padding: '8px 10px', background: 'rgba(0,0,0,0.6)', color: '#fff', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 6 }}>← Voltar</button>
      </div>

      <div style={{ position: 'absolute', top: 12, right: 12, zIndex: 10, color: '#fff', fontFamily: 'monospace', background: 'rgba(0,0,0,0.45)', padding: '8px 10px', borderRadius: 6 }}>
        <div style={{ fontSize: 12 }}>Cenário: {scenario ?? 'Padrão'}</div>
      </div>

      <Map
        {...viewState}
        onMove={evt => setViewState(evt.viewState)}
        style={{ position: 'absolute', width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/mapbox/satellite-streets-v12"
        mapboxAccessToken={MAPBOX_TOKEN}
      >
        <Source id="fire-data" type="geojson" data={firePolygonData}>
          <Layer {...fireLayerStyle} />
        </Source>

        <Source id="arrows-data" type="geojson" data={predictionArrowsData}>
          <Layer {...arrowsLayerStyle} />
        </Source>
      </Map>
    </div>
  );
}
