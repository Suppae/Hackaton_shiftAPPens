import { useEffect, useRef, useCallback } from 'react'
import MapView from '@/components/MapView'
import TimeSlider from '@/components/TimeSlider'
import WindHUD from '@/components/WindHUD'
import StatsPanel from '@/components/StatsPanel'
import ScenarioPicker from '@/components/ScenarioPicker'
import Legend from '@/components/Legend'
import useStore from '@/store'
import { fetchDemo, fetchSimulation } from '@/api/backend'
import { fetchRoute } from '@/api/mapbox'
import { routeIntersectsFire, polygonCentroid, computeDetourWaypoint } from '@/utils/geometry'

export default function App() {
  const mapRef = useRef()

  const setSimulation = useStore((s) => s.setSimulation)
  const setCurrentRoute = useStore((s) => s.setCurrentRoute)
  const setRerouted = useStore((s) => s.setRerouted)
  const setStatus = useStore((s) => s.setStatus)
  const setMode = useStore((s) => s.setMode)
  const setOrigin = useStore((s) => s.setOrigin)
  const setDestination = useStore((s) => s.setDestination)
  const resetReroute = useStore((s) => s.resetReroute)

  const origin = useStore((s) => s.origin)
  const destination = useStore((s) => s.destination)
  const currentRoute = useStore((s) => s.currentRoute)
  const timesteps = useStore((s) => s.timesteps)
  const currentStep = useStore((s) => s.currentStep)
  const isRerouted = useStore((s) => s.isRerouted)

  // Load Serra da Estrela demo on mount
  useEffect(() => {
    loadScenario(null)
  }, []) // eslint-disable-line

  async function loadScenario(sc) {
    setStatus('loading')
    let data

    if (!sc || sc.id === 'demo') {
      data = await fetchDemo()
    } else if (sc.id === 'pedrogao') {
      data = await fetchSimulation(sc.ignition)
    } else {
      setStatus('idle')
      return
    }

    setSimulation(data)
    setStatus('idle')

    if (sc?.origin) {
      setOrigin(sc.origin)
      setDestination(sc.destination)
    }

    const center = sc?.center ?? data.ignition
    if (center) {
      mapRef.current?.flyTo({ center, zoom: 11, pitch: 45, duration: 2000 })
    }
  }

  // Re-fetch route when origin/destination changes
  useEffect(() => {
    if (!origin || !destination) return
    let cancelled = false
    fetchRoute(origin, destination).then((route) => {
      if (!cancelled) {
        resetReroute()
        setCurrentRoute(route)
      }
    })
    return () => { cancelled = true }
  }, [origin[0], origin[1], destination[0], destination[1]]) // eslint-disable-line

  // Auto-reroute when fire intersects current route
  useEffect(() => {
    if (!currentRoute || !timesteps.length || currentStep === 0 || isRerouted) return

    const hasIntersection = timesteps
      .slice(0, currentStep)
      .some((step) => routeIntersectsFire(currentRoute, step.burned_area))

    if (!hasIntersection) return

    const latestFire = timesteps[currentStep - 1].burned_area
    const centroid = polygonCentroid(latestFire)
    const waypoint = computeDetourWaypoint(origin, destination, centroid)

    fetchRoute(origin, destination, waypoint).then((newRoute) => {
      if (newRoute) {
        setCurrentRoute(newRoute)
        setRerouted(true)
      }
    })
  }, [currentStep]) // eslint-disable-line

  const handleScenarioSelect = useCallback((sc) => {
    setMode(sc.id)
    if (sc.id !== 'custom') {
      loadScenario(sc)
    }
  }, []) // eslint-disable-line

  const handleMapClick = useCallback(async ([lon, lat]) => {
    setStatus('loading')
    const data = await fetchSimulation({ ignition_lon: lon, ignition_lat: lat })
    setSimulation(data)
    setStatus('idle')
  }, [setSimulation, setStatus])

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative', background: '#000' }}>
      <MapView mapRef={mapRef} onMapClick={handleMapClick} />
      <ScenarioPicker onSelect={handleScenarioSelect} />
      <WindHUD />
      <StatsPanel />
      <TimeSlider />
      <Legend />
    </div>
  )
}
