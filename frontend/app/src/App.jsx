import React, { useState } from 'react';
import Map, { Source, Layer } from 'react-map-gl';
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

  // MOCK DATA: Setas de predição do vetor de propagação (Vento + Topografia)
  const predictionArrowsData = {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [-8.2400, 40.1020] }, // À frente do fogo
        properties: { 
          rotation: 20, // Aponta para Nordeste
          risk: 'high' 
        }
      },
          {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [-8.2370, 40.098] }, // À frente do fogo
        properties: { 
          rotation: 20, // Aponta para Nordeste
          risk: 'high' 
        }
      },
      {
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [-8.2350, 40.0950] }, // Lado direito do fogo
        properties: { 
          rotation: 20, // Aponta para Este-Nordeste
          risk: 'medium' 
        }
      }
    ]
  };

 // ESTILO DAS SETAS (CORRIGIDO PARA USAR ÍCONES NATIVOS DO MAPBOX)
  // ESTILO DAS SETAS (O Truque Final: Caractere Geométrico Unicode)
  const arrowsLayerStyle = {
    id: 'prediction-arrows-layer',
    type: 'symbol',
    layout: {
      'text-field': '➤', // Triângulo geométrico básico (funciona em 100% das fontes)
      'text-size': 60,
      'text-rotate': ['get', 'rotation'], // Continua a rodar perfeitamente
      'text-allow-overlap': true,
      'text-ignore-placement': true, // Força a renderização mesmo se houver ruas por baixo
      'text-anchor': 'center',
      // Forçamos o deslocamento ligeiro para o "bico" do triângulo ser o ponto central da coordenada
      'text-offset': [0, -0.2],
      'text-rotation-alignment': 'map', // Obriga a seta a rodar com o terreno (Norte é sempre Norte)
      'text-pitch-alignment': 'map'
    },
    paint: {
      'text-color': '#c42214',       // Amarelo Néon
      'text-halo-color': '#000000',  // Borda Preta
      'text-halo-width': 2
    }
  };

  // MOCK DATA: Um polígono a representar a mancha inicial do incêndio
  const firePolygonData = {
    type: 'Feature',
    geometry: {
      type: 'Polygon',
      // Um quadrado de coordenadas em redor da Serra da Lousã
      coordinates: [[
        [-8.2600, 40.0900],
        [-8.2400, 40.0900],
        [-8.2400, 40.1000],
        [-8.2600, 40.1000],
        [-8.2600, 40.0900] // Tem de fechar onde começou
      ]]
    }
  };

  // Estilo visual da mancha de fogo (Laranja transparente com borda vermelha viva)
  const fireLayerStyle = {
    id: 'fire-layer',
    type: 'fill',
    paint: {
      'fill-color': '#ff4500', // Laranja fogo
      'fill-opacity': 0.6,     // Semitransparente para ver as ruas por baixo
      'fill-outline-color': '#ff0000' // Borda vermelha
    }
  };

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
        style={{ position: "absolute", width: '100%', height: '100%' }}
        mapStyle="mapbox://styles/mapbox/satellite-streets-v12"
        mapboxAccessToken={MAPBOX_TOKEN}
      >
        
        {/* AQUI ESTÁ A MAGIA: Injetar o Polígono no Mapa */}
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

export default App;