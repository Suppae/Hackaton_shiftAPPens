import { useEffect, useState, useMemo } from 'react'
import { Source, Layer } from 'react-map-gl'
import useStore from '@/store'

const FIRE_COLORS = [
  [0.0,  '#ffe066'],
  [0.33, '#ff8c1a'],
  [0.66, '#e63946'],
  [1.0,  '#7a0e0e'],
]

const fillColor = [
  'interpolate', ['linear'], ['get', 'intensity'],
  ...FIRE_COLORS.flat(),
]

// Returns GeoJSON points only on the LEADING EDGE of the fire polygon
// (the side facing the fire spread direction), offset slightly outward.
function buildFrontArrows(fireFeature, fireDirection, maxArrows = 5) {
  const ring = fireFeature.geometry.coordinates[0]
  const cx = ring.reduce((s, c) => s + c[0], 0) / ring.length
  const cy = ring.reduce((s, c) => s + c[1], 0) / ring.length

  // Unit vector in fire spread direction (bearing → lon/lat components)
  const rad = (fireDirection * Math.PI) / 180
  const dirLon = Math.sin(rad)
  const dirLat = Math.cos(rad)

  // Keep only points whose (point - centroid) has positive dot product with spread dir
  const front = ring.slice(0, -1).filter((pt) => {
    const dot = (pt[0] - cx) * dirLon + (pt[1] - cy) * dirLat
    return dot > 0
  })

  if (!front.length) return { type: 'FeatureCollection', features: [] }

  const step = Math.max(1, Math.floor(front.length / maxArrows))
  const features = []

  for (let i = 0; i < front.length; i += step) {
    const pt = front[i]
    const dx = pt[0] - cx
    const dy = pt[1] - cy
    const len = Math.sqrt(dx * dx + dy * dy) || 0.001
    const offset = 0.004
    features.push({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [pt[0] + (dx / len) * offset, pt[1] + (dy / len) * offset],
      },
      properties: {},
    })
  }

  return { type: 'FeatureCollection', features }
}

export default function FireLayer() {
  const timesteps = useStore((s) => s.timesteps)
  const currentStep = useStore((s) => s.currentStep)
  const metadata   = useStore((s) => s.metadata)
  const [glowOpacity, setGlowOpacity] = useState(0.7)

  useEffect(() => {
    let dir = 1
    const id = setInterval(() => {
      setGlowOpacity((prev) => {
        const next = prev + dir * 0.015
        if (next >= 1.0) { dir = -1; return 1.0 }
        if (next <= 0.6) { dir = 1;  return 0.6 }
        return next
      })
    }, 30)
    return () => clearInterval(id)
  }, [])

  // wind_direction_deg is FROM — fire spreads in the OPPOSITE direction
  const fireDirection = metadata ? (metadata.wind_direction_deg + 180) % 360 : 0

  // ➤ naturally points East (90° from North in map space).
  // To point in fireDirection: rotate by (fireDirection - 90).
  const arrowRotation = (fireDirection - 90 + 360) % 360

  const arrowGeoJSON = useMemo(() => {
    if (!timesteps.length || currentStep === 0 || !metadata) return null
    return buildFrontArrows(timesteps[currentStep - 1].burned_area, fireDirection)
  }, [timesteps, currentStep, fireDirection]) // eslint-disable-line

  if (!timesteps.length) return null

  return (
    <>
      {timesteps.map((step, i) => {
        const visible = i < currentStep
        const ratio = visible ? (i + 1) / currentStep : 0
        const fillOpacity = visible ? 0.25 + 0.55 * ratio : 0
        const isLatest = visible && i === currentStep - 1

        return (
          <Source key={`fire-src-${i}`} id={`fire-src-${i}`} type="geojson" data={step.burned_area}>
            <Layer
              id={`fire-fill-${i}`}
              type="fill"
              paint={{
                'fill-color': fillColor,
                'fill-opacity': fillOpacity,
              }}
            />
            <Layer
              id={`fire-glow-${i}`}
              type="line"
              paint={{
                'line-color': '#ff8c1a',
                'line-width': isLatest ? 3 : 1.5,
                'line-blur': 3,
                'line-opacity': isLatest ? glowOpacity : (visible ? 0.3 : 0),
              }}
            />
          </Source>
        )
      })}

      {arrowGeoJSON && currentStep > 0 && (
        <Source id="fire-arrows" type="geojson" data={arrowGeoJSON}>
          <Layer
            id="fire-arrows-layer"
            type="symbol"
            layout={{
              'text-field': '➤',
              'text-size': 22,
              'text-rotate': arrowRotation,
              // 'map' = rotation is fixed to geographic North — never changes when panning
              'text-rotation-alignment': 'map',
              // 'viewport' = symbol face stays upright — no tilt with pitch 45°
              'text-allow-overlap': true,
              'text-ignore-placement': true,
              'text-pitch-alignment': 'map'
            }}
            paint={{
              'text-color': '#ff8c1a',
              'text-halo-color': '#1a0800',
              'text-halo-width': 2,
              'text-opacity': glowOpacity,
            }}
          />
        </Source>
      )}
    </>
  )
}
