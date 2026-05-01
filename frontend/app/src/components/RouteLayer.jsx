import { Source, Layer } from 'react-map-gl'
import useStore from '@/store'

export default function RouteLayer() {
  const currentRoute = useStore((s) => s.currentRoute)
  const previousRoute = useStore((s) => s.previousRoute)

  return (
    <>
      {previousRoute && (
        <Source id="route-old" type="geojson" data={previousRoute}>
          <Layer
            id="route-old-line"
            type="line"
            layout={{ 'line-cap': 'round', 'line-join': 'round' }}
            paint={{
              'line-color': '#ff2e2e',
              'line-width': 4,
              'line-opacity': 0.8,
              'line-dasharray': [2, 2],
            }}
          />
        </Source>
      )}
      {currentRoute && (
        <Source id="route-current" type="geojson" data={currentRoute}>
          <Layer
            id="route-current-line"
            type="line"
            layout={{ 'line-cap': 'round', 'line-join': 'round' }}
            paint={{
              'line-color': '#39ff14',
              'line-width': 5,
              'line-opacity': 0.95,
            }}
          />
          <Layer
            id="route-current-glow"
            type="line"
            layout={{ 'line-cap': 'round', 'line-join': 'round' }}
            paint={{
              'line-color': '#39ff14',
              'line-width': 10,
              'line-opacity': 0.15,
              'line-blur': 4,
            }}
          />
        </Source>
      )}
    </>
  )
}
