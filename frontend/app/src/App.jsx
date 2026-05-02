import { useEffect, useRef, useCallback } from 'react'
import MapView from '@/components/MapView'
import RoutePanel, { SCENARIOS } from '@/components/RoutePanel'
import TimeSlider from '@/components/TimeSlider'
import WindHUD from '@/components/WindHUD'
import Legend from '@/components/Legend'
import CompassHUD from '@/components/CompassHUD'
import useStore from '@/store'
import { fetchDemo, fetchSimulation } from '@/api/backend'
import { fetchRoute } from '@/api/mapbox'
import { routeIntersectsFire } from '@/utils/geometry'

export default function App() {
  const mapRef = useRef()

  const setSimulation   = useStore((s) => s.setSimulation)
  const setCurrentRoute = useStore((s) => s.setCurrentRoute)
  const setRerouted     = useStore((s) => s.setRerouted)
  const setStatus       = useStore((s) => s.setStatus)
  const setMode         = useStore((s) => s.setMode)
  const setOrigin       = useStore((s) => s.setOrigin)
  const setDestination  = useStore((s) => s.setDestination)
  const resetReroute    = useStore((s) => s.resetReroute)

  const origin       = useStore((s) => s.origin)
  const destination  = useStore((s) => s.destination)
  const currentRoute = useStore((s) => s.currentRoute)
  const timesteps    = useStore((s) => s.timesteps)
  const currentStep  = useStore((s) => s.currentStep)
  const isRerouted   = useStore((s) => s.isRerouted)

  // Load Serra da Estrela demo + auto-calculate initial route on mount
  useEffect(() => {
    loadScenario(SCENARIOS.find((s) => s.id === 'demo'))
  }, []) // eslint-disable-line

  async function loadScenario(sc) {
    setStatus('loading')
    let data

    if (!sc || sc.id === 'demo') {
      data = await fetchDemo()
    } else if (sc.id === 'pedrogao') {
      data = await fetchSimulation(sc.ignition)
    } else {
      // custom mode — user clicks map to ignite
      setStatus('idle')
      return
    }

    setSimulation(data)

    const orig = sc?.origin ?? origin
    const dest = sc?.destination ?? destination
    setOrigin(orig)
    setDestination(dest)

    // Auto-calculate route for the new scenario
    const route = await fetchRoute(orig, dest)
    if (route) {
      resetReroute()
      setCurrentRoute(route)
    }

    setStatus('idle')

    const center = sc?.center ?? data.ignition
    if (center) mapRef.current?.flyTo({ center, zoom: 11, pitch: 45, duration: 2000 })
  }

  // Auto-reroute when fire intersects the current route
  useEffect(() => {
    if (!currentRoute || !timesteps.length || currentStep === 0 || isRerouted) return

    const visibleFire = timesteps.slice(0, currentStep).map((s) => s.burned_area)
    const hasIntersection = visibleFire.some((fp) =>
      routeIntersectsFire(currentRoute.geometry, fp)
    )
    if (!hasIntersection) return

    // Pass all visible fire polygons as exclusions to Mapbox Directions
    const excludePolygons = visibleFire.map((fp) => fp.geometry.coordinates)

    fetchRoute(origin, destination, excludePolygons).then((newRoute) => {
      if (newRoute) {
        setCurrentRoute(newRoute) // saves old route to previousRoute automatically
        setRerouted(true)
      }
    })
  }, [currentStep]) // eslint-disable-line

  const handleScenarioSelect = useCallback((sc) => {
    setMode(sc.id)
    if (sc.id !== 'custom') loadScenario(sc)
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
      <RoutePanel onScenarioSelect={handleScenarioSelect} />
      <WindHUD />
      <CompassHUD mapRef={mapRef} />
      <TimeSlider />
      <Legend />
    </div>
  )
}
