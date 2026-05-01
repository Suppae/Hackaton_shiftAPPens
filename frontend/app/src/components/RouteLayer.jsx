import { Source, Layer } from 'react-map-gl'
import useStore from '@/store'

function toGeoJSON(route) {
  if (!route) return null
  return { type: 'Feature', geometry: route.geometry, properties: {} }
}

export default function RouteLayer() {
  const currentRoute = useStore((s) => s.currentRoute)
  const previousRoute = useStore((s) => s.previousRoute)

  const current = toGeoJSON(currentRoute)
  const previous = toGeoJSON(previousRoute)

  return (
    <>
      {previous && (
        <Source id="route-old" type="geojson" data={previous}>
          <Layer
            id="route-old-line"
            type="line"
            layout={{ 'line-cap': 'round', 'line-join': 'round' }}
            paint={{
              'line-color': '#ff2e2e',
              'line-width': 4,
              'line-opacity': 0.7,
              'line-dasharray': [2, 2],
            }}
          />
        </Source>
      )}
      {current && (
        <Source id="route-current" type="geojson" data={current}>
          <Layer
            id="route-current-line"
            type="line"
            layout={{ 'line-cap': 'round', 'line-join': 'round' }}
            paint={{
              'line-color': '#39ff14',
              'line-width': 5,
              'line-blur': 1,
              'line-opacity': 0.95,
            }}
          />
          <Layer
            id="route-current-glow"
            type="line"
            layout={{ 'line-cap': 'round', 'line-join': 'round' }}
            paint={{
              'line-color': '#39ff14',
              'line-width': 12,
              'line-opacity': 0.12,
              'line-blur': 5,
            }}
          />
        </Source>
      )}
    </>
  )
}
