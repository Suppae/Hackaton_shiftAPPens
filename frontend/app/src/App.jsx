import { useEffect, useRef, useCallback, useState, useReducer } from 'react'
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

  const activeFireInfo = useStore((s) => s.activeFireInfo)
  const showCompass = useStore((s) => s.showCompass)
  const showWindHUD = useStore((s) => s.showWindHUD)
  const showLegend = useStore((s) => s.showLegend)
  const showTimeSlider = useStore((s) => s.showTimeSlider)
  const showFireDetailsPanel = useStore((s) => s.showFireDetailsPanel)
  const status = useStore((s) => s.status)
  const timesteps = useStore((s) => s.timesteps)

  const setSimulation = useStore((s) => s.setSimulation)
  const setActiveFireInfo = useStore((s) => s.setActiveFireInfo)
  const setStatus = useStore((s) => s.setStatus)
  const setMode = useStore((s) => s.setMode)

  const [activeFiresGeoJSON, setActiveFiresGeoJSON] = useState(null)
  const [simError, setSimError] = useState(false)

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
    }).catch(err => {
      console.error('Failed to load active fires:', err)
      setStatus('idle')
    })
  }, [setStatus, setMode])

  const handleMapClick = useCallback(async ([lon, lat], fireProps) => {
    // Always reset stale fire info; only set if we clicked an active fire marker
    setActiveFireInfo(fireProps || null)

    setStatus('loading')

    try {
      const data = await fetchSimulation({
        ignition_lon: lon,
        ignition_lat: lat,
        n_steps: 6,
        minutes_per_step: 10,
        engine: "ca",
        source: fireProps?.fireId ? "fogos_pt" : "manual",
      })

      setSimulation(data)

      if (mapRef.current) {
        mapRef.current.flyTo({
          center: [lon, lat],
          zoom: 12,
          pitch: 50,
          duration: 2500,
        })
      }
    } catch (err) {
      console.error('[App] Simulation failed:', err)
      setSimError(true)
      setStatus('idle')
      setTimeout(() => setSimError(false), 4000)
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
            <div className="bg-black/80 backdrop-blur-md rounded-xl px-6 py-3 border border-red-500/30 flex items-center gap-3">
              <div className="w-5 h-5 border-2 border-red-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm text-red-400 tracking-[0.1em] font-semibold" style={{ fontFamily: "'Manrope', sans-serif" }}>A CALCULAR PROPAGAÇÃO...</span>
            </div>
          </div>
        )}

        {simError && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20">
            <div className="bg-black/90 backdrop-blur-md rounded-xl px-6 py-3 border border-orange-500/40 flex items-center gap-3">
              <span className="text-orange-400 text-lg">⚠</span>
              <span className="text-sm text-orange-300 font-semibold tracking-wide">Backend indisponível — verifica se o servidor está a correr</span>
            </div>
          </div>
        )}

        {status === 'idle' && timesteps.length === 0 && !simError && (
          <div className="absolute bottom-24 left-1/2 -translate-x-1/2 z-10 pointer-events-none">
            <div className="bg-black/60 backdrop-blur-sm rounded-lg px-4 py-2 border border-white/10">
              <span className="text-xs text-white/40 font-mono tracking-[0.15em]">CLIQUE NO MAPA PARA SIMULAR IGNIÇÃO</span>
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
