import React, { useState } from 'react';
import MapView from './components/MapView';

function App() {
  const [view, setView] = useState('menu'); // 'menu' | 'map'
  const [scenario, setScenario] = useState(null);

  const openMapWith = (sc) => {
    setScenario(sc);
    setView('map');
  };

  if (view === 'map') {
    return (
      <MapView
        scenario={scenario}
        onBack={() => setView('menu')}
      />
    );
  }

  return (
    <div style={{ width: '100%', height: '100vh', backgroundColor: '#0b0b0b', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ width: 820, padding: 28, borderRadius: 12, background: 'linear-gradient(180deg, rgba(0,0,0,0.6), rgba(0,0,0,0.4))', border: '1px solid rgba(255,255,255,0.06)', boxShadow: '0 10px 40px rgba(0,0,0,0.6)', fontFamily: 'Inter, system-ui, sans-serif' }}>
        <h1 style={{ margin: 0, fontSize: 28, color: '#ffe066' }}>🔥 Tactical Routing — Demo</h1>
        <p style={{ marginTop: 8, color: '#cbd5e1' }}>Visual demo para rota dinâmica em presença de incêndio florestal. Escolha um cenário para começar.</p>

        <div style={{ display: 'flex', gap: 12, marginTop: 18 }}>
          <button onClick={() => openMapWith('serra') } style={{ flex: 1, padding: '12px 16px', background: '#111827', border: '1px solid #374151', color: '#fff', borderRadius: 8 }}>Demo: Serra da Estrela</button>
          <button onClick={() => openMapWith('pedrogao') } style={{ flex: 1, padding: '12px 16px', background: '#7c2d12', border: '1px solid #ff8c1a', color: '#fff', borderRadius: 8 }}>Pedrógão Grande</button>
          <button onClick={() => openMapWith('custom') } style={{ flex: 1, padding: '12px 16px', background: '#063b63', border: '1px solid #22d3ee', color: '#fff', borderRadius: 8 }}>Custom Ignite (click)</button>
        </div>

        <div style={{ marginTop: 18, display: 'flex', gap: 12 }}>
          <button onClick={() => openMapWith(null) } style={{ padding: '10px 14px', background: '#052e16', border: '1px solid #39ff14', color: '#d1fae5', borderRadius: 8 }}>Abrir Mapa</button>
          <a href="https://github.com/" target="_blank" rel="noreferrer" style={{ padding: '10px 14px', display: 'inline-block', textDecoration: 'none', background: '#0f172a', border: '1px solid #374151', color: '#9ca3af', borderRadius: 8 }}>README</a>
        </div>

        <div style={{ marginTop: 20, fontFamily: 'monospace', color: '#94a3b8', fontSize: 13 }}>
          <div>Backend: http://localhost:8000</div>
          <div style={{ marginTop: 6 }}>Mapbox token: env VITE_MAPBOX_TOKEN (fallback token embedded in map component)</div>
        </div>
      </div>
    </div>
  );
}

export default App;