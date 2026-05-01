import React, { useState } from 'react';
import Map from 'react-map-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

const MAPBOX_TOKEN = "pk.eyJ1IjoidGlhZ29tYW5pbmhhIiwiYSI6ImNtb213emZqYTBpdjcyc3M0bHlldWZnc2gifQ.KogqOP6C00qQ8VNtk847Ng";

function App() {
  const [viewState, setViewState] = useState({
    longitude: -8.2520,
    latitude: 40.0935,
    zoom: 12,
    pitch: 45, 
    bearing: 0
  });

  if (!MAPBOX_TOKEN) {
    return <div style={{color: 'red', padding: '20px'}}>⚠️ Erro: Token do Mapbox não encontrada.</div>;
  }

  return (
    // O container principal
    <div style={{ width: '99%', height: '100%', position: 'absolute', backgroundColor: '#222' }}>
      
      {/* HUD de Comando */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        zIndex: 2, // Garante que fica por cima do mapa
        backgroundColor: 'rgba(0, 0, 0, 0.85)',
        padding: '0px',
        borderRadius: '8px',
        color: '#00FF00',
        fontFamily: 'monospace',
        border: '1px solid #00FF00',
        boxShadow: '0 0 10px rgba(0, 255, 0, 0.2)'
      }}>
        <h2 style={{ margin: '0 0 10px 0', fontSize: '1.2rem' }}>🔥 TACTICAL ROUTING</h2>
        <p style={{ margin: '5px 0', fontSize: '0.9rem' }}>Status: Aguardando Ignição...</p>
        <p style={{ margin: '5px 0', fontSize: '0.9rem' }}>Vento: -- km/h</p>
      </div>

      {/* COMPONENTE DO MAPA CORRIGIDO */}
      <Map
        {...viewState}
        onMove={evt => setViewState(evt.viewState)}
        style={{ position: "absolute", width: '100%', height: '100%' }} /* <-- ESTA LINHA É A MAGIA QUE FALTAVA */
        mapStyle="mapbox://styles/mapbox/satellite-v9"
        mapboxAccessToken={MAPBOX_TOKEN}
      />
      
    </div>
  );
}

export default App;