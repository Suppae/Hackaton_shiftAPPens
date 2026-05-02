import React, { useEffect, useState, useMemo } from 'react'
import { Source, Layer, useMap } from 'react-map-gl'
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

function buildFrontArrows(fireFeature, fireDirection) {
  const ring = fireFeature.geometry.coordinates[0]
  const cx = ring.reduce((s, c) => s + c[0], 0) / ring.length
  const cy = ring.reduce((s, c) => s + c[1], 0) / ring.length

  const rad = (fireDirection * Math.PI) / 180
  const dirLon = Math.sin(rad)
  const dirLat = Math.cos(rad)

  const front = ring.slice(0, -1).filter((pt) => {
    const dot = (pt[0] - cx) * dirLon + (pt[1] - cy) * dirLat
    return dot > 0
  })

  if (!front.length) return { type: 'FeatureCollection', features: [] }

  const targetArrows = 18
  const step = Math.max(1, Math.floor(front.length / targetArrows))
  const features = []

  for (let i = 0; i < front.length; i += step) {
    const pt = front[i]
    const dx = pt[0] - cx
    const dy = pt[1] - cy
    const len = Math.sqrt(dx * dx + dy * dy) || 0.001

    const offsetOuter = 0.008
    const offsetInner = 0.0045
    const offsetMid = 0.006

    features.push({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [pt[0] + (dx / len) * offsetOuter, pt[1] + (dy / len) * offsetOuter],
      },
      properties: { size: 'lg' },
    })

    features.push({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [pt[0] + (dx / len) * offsetInner, pt[1] + (dy / len) * offsetInner],
      },
      properties: { size: 'sm' },
    })

    features.push({
      type: 'Feature',
      geometry: {
        type: 'Point',
        coordinates: [pt[0] + (dx / len) * offsetMid, pt[1] + (dy / len) * offsetMid],
      },
      properties: { size: 'md' },
    })
  }

  return { type: 'FeatureCollection', features }
}

export default function FireLayer() {
  const timesteps = useStore((s) => s.timesteps)
  const currentStep = useStore((s) => s.currentStep)
  const metadata   = useStore((s) => s.metadata)
  const vectors    = useStore((s) => s.vectors)
  const setSelectedFire = useStore((s) => s.setSelectedFire)
  const [glowOpacity, setGlowOpacity] = useState(0.7)
  const { current: map } = useMap()

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

  useEffect(() => {
    if (!map) return

    const handleFireClick = (e) => {
      if (e.features && e.features.length > 0) {
        const layerId = e.features[0].layer.id
        const match = layerId.match(/fire-\w+-(\d+)/)
        if (match) {
          const fireIndex = parseInt(match[1], 10)
          const timestep = timesteps[fireIndex]
          if (timestep) {
            setSelectedFire({ timestep, fireIndex })
          }
        }
      }
    }

    timesteps.forEach((_, i) => {
      const fillLayerId = `fire-fill-${i}`
      const glowLayerId = `fire-glow-${i}`

      if (map.getLayer(fillLayerId)) {
        map.on('click', fillLayerId, handleFireClick)
        map.on('mouseenter', fillLayerId, () => { map.getCanvas().style.cursor = 'pointer' })
        map.on('mouseleave', fillLayerId, () => { map.getCanvas().style.cursor = 'auto' })
      }

      if (map.getLayer(glowLayerId)) {
        map.on('click', glowLayerId, handleFireClick)
        map.on('mouseenter', glowLayerId, () => { map.getCanvas().style.cursor = 'pointer' })
        map.on('mouseleave', glowLayerId, () => { map.getCanvas().style.cursor = 'auto' })
      }
    })

    return () => {
      timesteps.forEach((_, i) => {
        const fillLayerId = `fire-fill-${i}`
        const glowLayerId = `fire-glow-${i}`
        if (map.getLayer(fillLayerId)) map.off('click', fillLayerId, handleFireClick)
        if (map.getLayer(glowLayerId)) map.off('click', glowLayerId, handleFireClick)
      })
    }
  }, [map, timesteps, setSelectedFire])

  const fireDirection = vectors
    ? vectors.primary_spread_angle
    : metadata
      ? (metadata.wind_direction_deg + 180) % 360
      : 0

  const arrowRotation = (fireDirection - 90 + 360) % 360

  const activeTs = currentStep > 0
    ? timesteps[currentStep - 1]
    : timesteps.length > 0
      ? timesteps[0]
      : null

  const arrowGeoJSON = useMemo(() => {
    if (!activeTs) return null
    return buildFrontArrows(activeTs.burned_area, fireDirection)
  }, [activeTs, fireDirection])

  if (!timesteps.length) return null

  // Steps to render: all up to currentStep (or all if paused at 0)
  const visibleSteps = currentStep === 0
    ? timesteps
    : timesteps.slice(0, currentStep)

  const latestIdx = visibleSteps.length - 1

  return (
    <>
      {visibleSteps.map((step, i) => {
        const isLatest = i === latestIdx

        return (
          <React.Fragment key={`fire-src-${i}`}>
            {/* ── Burned zone (charcoal/black) ───────────────────────── */}
            <Source id={`burned-src-${i}`} type="geojson" data={step.burned_area}>
              <Layer
                id={`fire-fill-${i}`}
                type="fill"
                paint={{
                  'fill-color': '#1a0a00',
                  'fill-opacity': isLatest ? 0.82 : 0.70,
                }}
              />
              <Layer
                id={`fire-glow-${i}`}
                type="line"
                paint={{
                  'line-color': '#3d1500',
                  'line-width': 1,
                  'line-opacity': 0.5,
                }}
              />
            </Source>

            {/* ── Active fire front (red/orange jagged cells) ─────────── */}
            {step.burning_front && isLatest && (
              <Source id={`front-src-${i}`} type="geojson" data={step.burning_front}>
                <Layer
                  id={`fire-front-fill-${i}`}
                  type="fill"
                  paint={{
                    'fill-color': '#ff4500',
                    'fill-opacity': 0.90,
                  }}
                />
                <Layer
                  id={`fire-front-glow-${i}`}
                  type="line"
                  paint={{
                    'line-color': '#ffcc00',
                    'line-width': 2.5,
                    'line-blur': 4,
                    'line-opacity': glowOpacity,
                  }}
                />
              </Source>
            )}

            {/* ── Ember glow on older fronts (faint orange outline) ───── */}
            {step.burning_front && !isLatest && (
              <Source id={`front-src-${i}`} type="geojson" data={step.burning_front}>
                <Layer
                  id={`fire-front-fill-${i}`}
                  type="fill"
                  paint={{
                    'fill-color': '#cc2200',
                    'fill-opacity': 0.45,
                  }}
                />
              </Source>
            )}
          </React.Fragment>
        )
      })}

      {arrowGeoJSON && arrowGeoJSON.features.length > 0 && (
        <Source id="fire-arrows-outer" type="geojson" data={arrowGeoJSON}>
          <Layer
            id="fire-arrows-outer-layer"
            type="symbol"
            filter={['==', ['get', 'size'], 'lg']}
            layout={{
              'text-field': '➤',
              'text-size': 26,
              'text-rotate': arrowRotation,
              'text-rotation-alignment': 'map',
              'text-allow-overlap': true,
              'text-ignore-placement': true,
              'text-pitch-alignment': 'map',
            }}
            paint={{
              'text-color': '#ef4444',
              'text-halo-color': '#0a0000',
              'text-halo-width': 4,
              'text-opacity': glowOpacity,
            }}
          />
          <Layer
            id="fire-arrows-mid-layer"
            type="symbol"
            filter={['==', ['get', 'size'], 'md']}
            layout={{
              'text-field': '➤',
              'text-size': 20,
              'text-rotate': arrowRotation,
              'text-rotation-alignment': 'map',
              'text-allow-overlap': true,
              'text-ignore-placement': true,
              'text-pitch-alignment': 'map',
            }}
            paint={{
              'text-color': '#dc2626',
              'text-halo-color': '#0a0000',
              'text-halo-width': 3,
              'text-opacity': glowOpacity * 0.9,
            }}
          />
          <Layer
            id="fire-arrows-inner-layer"
            type="symbol"
            filter={['==', ['get', 'size'], 'sm']}
            layout={{
              'text-field': '▸',
              'text-size': 16,
              'text-rotate': arrowRotation,
              'text-rotation-alignment': 'map',
              'text-allow-overlap': true,
              'text-ignore-placement': true,
              'text-pitch-alignment': 'map',
            }}
            paint={{
              'text-color': '#b91c1c',
              'text-halo-color': '#0a0000',
              'text-halo-width': 2,
              'text-opacity': glowOpacity * 0.75,
            }}
          />
        </Source>
      )}
    </>
  )
}
