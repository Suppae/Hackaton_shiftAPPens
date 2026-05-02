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
  
  const selectedFire = useStore((s) => s.selectedFire)
  const activeFireInfo = useStore((s) => s.activeFireInfo)
  const showCompass = useStore((s) => s.showCompass)
  const showWindHUD = useStore((s) => s.showWindHUD)
  const showLegend = useStore((s) => s.showLegend)
  const showTimeSlider = useStore((s) => s.showTimeSlider)
  const showRoutePanel = useStore((s) => s.showRoutePanel)
  const showFireDetailsPanel = useStore((s) => s.showFireDetailsPanel)
  const status = useStore((s) => s.status)
  const timesteps = useStore((s) => s.timesteps)
  
  const setSimulation   = useStore((s) => s.setSimulation)
  const setActiveFireInfo = useStore((s) => s.setActiveFireInfo)
  const setStatus       = useStore((s) => s.setStatus)
  const setMode         = useStore((s) => s.setMode)
  const mode            = useStore((s) => s.mode)

  const [activeFiresGeoJSON, setActiveFiresGeoJSON] = useState(null)

  useEffect(() => {
    setMode('custom')
    setStatus('loading')
    
    fetchActiveFires(24).then(geojson => {
      if (geojson && geojson.features && geojson.features.length > 0) {
        setActiveFiresGeoJSON(geojson)
      }
      setStatus('idle')
      
      if (mapRef.current) {
        mapRef.current.flyTo({
          center: [-8.2245, 39.3999],
          zoom: 5.5,
          pitch: 30,
          duration: 3000
        })
      }
    })
  }, [setStatus, setMode])

  const handleMapClick = useCallback(async ([lon, lat], fireProps) => {
    if (fireProps) {
      setActiveFireInfo(fireProps)
    }

    setStatus('loading')
    
    const data = await fetchSimulation({ 
        ignition_lon: lon, 
        ignition_lat: lat,
        n_steps: 6,
        minutes_per_step: 10,
        engine: "auto",
        source: fireProps?.fireId ? "fogos_pt" : "manual",
    })
    
    setSimulation(data)
    
    if (mapRef.current) {
        mapRef.current.flyTo({
            center: [lon, lat],
            zoom: 12,
            pitch: 50,
            duration: 2500
        })
    }
  }, [setSimulation, setStatus, setActiveFireInfo])

  const panelWidth = (timesteps.length > 0 || activeFireInfo) ? 380 : 0

  return (
    <div style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden', background: '#000' }}>
      
      <div style={{ width: panelWidth, minWidth: panelWidth, transition: 'width 220ms ease', background: '#050505' }}>
        {showFireDetailsPanel && <FireDetailsPanel />}
      </div>
      
      <div style={{ flex: 1, position: 'relative', minWidth: 0 }}>
        
        <MapView 
          mapRef={mapRef} 
          onMapClick={handleMapClick} 
          activeFires={activeFiresGeoJSON} 
        />
        
        {status === 'loading' && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20">
            <div className="bg-black/80 backdrop-blur-md rounded-xl px-6 py-3 border border-orange-400/40 flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-orange-400 border-t-transparent rounded-full animate-spin" />
              <span className="font-mono text-sm text-orange-400 tracking-wide">A CALCULAR PROPAGAÇÃO...</span>
            </div>
          </div>
        )}

        {showWindHUD && <WindHUD />}
        {showCompass && <CompassHUD mapRef={mapRef} />}
        {showTimeSlider && timesteps.length > 0 && <TimeSlider />}
        {showLegend && timesteps.length > 0 && <Legend />}
        <LayersToggle />
        
      </div>
    </div>
  )
}
