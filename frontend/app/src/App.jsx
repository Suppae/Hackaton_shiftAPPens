import { useEffect, useRef, useCallback, useState } from 'react'
import MapView from '@/components/MapView'
import TimeSlider from '@/components/TimeSlider'
import WindHUD from '@/components/WindHUD'
import Legend from '@/components/Legend'
import CompassHUD from '@/components/CompassHUD'
import FireDetailsPanel from '@/components/FireDetailsPanel'
import LayersToggle from '@/components/LayersToggle'
import useStore from '@/store'
import { fetchSimulation, fetchActiveFires } from '@/api/backend'

export default function App() {
  const mapRef = useRef()
  
  // Estado UI
  const selectedFire = useStore((s) => s.selectedFire)
  const showCompass = useStore((s) => s.showCompass)
  const showWindHUD = useStore((s) => s.showWindHUD)
  const showLegend = useStore((s) => s.showLegend)
  const showTimeSlider = useStore((s) => s.showTimeSlider)
<<<<<<< HEAD
  const showRoutePanel = useStore((s) => s.showRoutePanel)

=======
  const showFireDetailsPanel = useStore((s) => s.showFireDetailsPanel)
  
  // Estado Lógico
>>>>>>> 3c62b372765fa08f19e23efaf4952e5f5b946c6c
  const setSimulation   = useStore((s) => s.setSimulation)
  const setStatus       = useStore((s) => s.setStatus)
  const setMode         = useStore((s) => s.setMode)
  const mode            = useStore((s) => s.mode)

  // Estado Local para os Fogos da Proteção Civil
  const [activeFiresGeoJSON, setActiveFiresGeoJSON] = useState(null)

  // 1. CARREGAR OS FOGOS REAIS NO INÍCIO DA APP
  useEffect(() => {
    // Forçamos o modo para 'custom' para libertar o mapa
    setMode('custom');
    setStatus('loading');
    
    fetchActiveFires().then(geojson => {
      if (geojson && geojson.features && geojson.features.length > 0) {
        setActiveFiresGeoJSON(geojson);
      }
      setStatus('idle');
      
      // Anima a câmara para mostrar Portugal inteiro
      if (mapRef.current) {
        mapRef.current.flyTo({
          center: [-8.2245, 39.3999], // Centro aproximado de Portugal Continental
          zoom: 5.5,
          pitch: 30,
          duration: 3000
        });
      }
    });
  }, [setStatus, setMode]);

  // 2. CLIQUE NO MAPA / FOGO REAL
  const handleMapClick = useCallback(async ([lon, lat]) => {
    setStatus('loading')
    
    // Simula a partir do ponto clicado (Puxa GEE, OpenWeather, Rothermel)
    const data = await fetchSimulation({ 
        ignition_lon: lon, 
        ignition_lat: lat,
        n_steps: 6,
        minutes_per_step: 10,
        engine: "auto",
        source: "fogos_pt" 
    })
    
    setSimulation(data)
    
    // Voa suavemente para o ponto de ignição para ver a mancha crescer
    if (mapRef.current) {
        mapRef.current.flyTo({
            center: [lon, lat],
            zoom: 12,
            pitch: 50,
            duration: 2500
        });
    }
    
    setStatus('idle')
  }, [setSimulation, setStatus])

  // Largura do painel de detalhes
  const panelWidth = selectedFire ? 380 : 0

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden', background: '#000' }}>
      
      {/* Painel lateral (só abre quando se clica na mancha gerada) */}
      <div style={{ width: panelWidth, minWidth: panelWidth, transition: 'width 220ms ease', background: '#050505' }}>
        <FireDetailsPanel />
      </div>
      
      {/* Container principal do Mapa */}
      <div style={{ flex: 1, position: 'relative', minWidth: 0 }}>
        
        <MapView 
          mapRef={mapRef} 
          onMapClick={handleMapClick} 
          activeFires={activeFiresGeoJSON} 
        />
        
        {/* HUDs visíveis */}
        {showWindHUD && <WindHUD />}
        {showCompass && <CompassHUD mapRef={mapRef} />}
        {showTimeSlider && <TimeSlider />}
        {showLegend && <Legend />}
        <LayersToggle />
        
      </div>
    </div>
  )
}