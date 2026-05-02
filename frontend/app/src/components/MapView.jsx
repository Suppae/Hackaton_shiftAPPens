import { useCallback } from 'react'
import Map, { Source, Layer } from 'react-map-gl'
import mapboxgl from 'mapbox-gl'
import FireLayer from './FireLayer'
import MarkersLayer from './MarkersLayer'
import useStore from '@/store'

const INITIAL_VIEW = {
  longitude: -7.6167,
  latitude: 40.3217,
  zoom: 11,
  pitch: 45,
  bearing: 0,
}

const MAP_STYLE = 'mapbox://styles/mapbox/satellite-streets-v12'
const TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || "pk.eyJ1IjoidGlhZ29tYW5pbmhhIiwiYSI6ImNtb213emZqYTBpdjcyc3M0bHlldWZnc2gifQ.KogqOP6C00qQ8VNtk847Ng"

// Portugal + Azores + Madeira bounding box [swLon, swLat, neLon, neLat]
const PORTUGAL_BOUNDS = [-32.5, 31.5, -5.5, 43.0]
const MIN_ZOOM = 4

const activeFiresStyle = {
    id: 'active-fires-layer',
    type: 'circle',
    paint: {
      'circle-radius': 7,
      'circle-color': '#ff1a1a',
      'circle-stroke-width': 2,
      'circle-stroke-color': '#ffcc00',
      'circle-opacity': 0.9,
      'circle-blur': 0.2,
    }
}

const activeFiresGlowStyle = {
    id: 'active-fires-glow',
    type: 'circle',
    paint: {
      'circle-radius': 14,
      'circle-color': '#ff4400',
      'circle-opacity': 0.25,
      'circle-blur': 1,
    }
}

export default function MapView({ mapRef, onMapClick, activeFires }) {
  const timesteps = useStore((s) => s.timesteps)
  const currentStep = useStore((s) => s.currentStep)

  const handleLoad = useCallback(({ target: map }) => {
    if (map.getSource('mapbox-dem')) return
    map.addSource('mapbox-dem', {
      type: 'raster-dem',
      url: 'mapbox://mapbox.mapbox-terrain-dem-v1',
      tileSize: 512,
      maxzoom: 14,
    })
    map.setTerrain({ source: 'mapbox-dem', exaggeration: 1.5 })
    map.addLayer({
      id: 'sky',
      type: 'sky',
      paint: {
        'sky-type': 'atmosphere',
        'sky-atmosphere-sun': [0.0, 90.0],
        'sky-atmosphere-sun-intensity': 15,
      },
    })
  }, [])

  const handleClick = useCallback((e) => {
    if (!onMapClick) return

    // Check if user clicked an active-fire marker
    const features = e.features || []
    const fireFeature = features.find(
      (f) => f.layer.id === 'active-fires-layer' || f.layer.id === 'active-fires-glow'
    )

    if (fireFeature) {
      const [lon, lat] = fireFeature.geometry.coordinates
      const props = fireFeature.properties || {}
      onMapClick([lon, lat], {
        town: props.town || 'Desconhecido',
        status: props.status || 'N/A',
        man: props.man || 0,
        terrain: props.terrain || '',
        fireId: props.id,
      })
    } else {
      // Free-map click → custom ignition point, no fire metadata
      const { lng, lat } = e.lngLat
      onMapClick([lng, lat], null)
    }
  }, [onMapClick])

  const interactiveLayers = ['active-fires-layer', 'active-fires-glow']
  const visibleCount = currentStep > 0 ? currentStep : timesteps.length
  for (let i = 0; i < visibleCount; i++) {
    interactiveLayers.push(`fire-fill-${i}`, `fire-front-fill-${i}`)
  }

  return (
    <Map
      ref={mapRef}
      mapLib={mapboxgl}
      mapboxAccessToken={TOKEN}
      initialViewState={INITIAL_VIEW}
      style={{ width: '100%', height: '100%' }}
      mapStyle={MAP_STYLE}
      onLoad={handleLoad}
      onClick={handleClick}
      interactiveLayerIds={interactiveLayers}
      cursor="pointer"
      maxBounds={PORTUGAL_BOUNDS}
      minZoom={MIN_ZOOM}
    >
      {activeFires && (
          <Source id="active-fires-data" type="geojson" data={activeFires}>
            <Layer {...activeFiresGlowStyle} />
            <Layer {...activeFiresStyle} />
          </Source>
      )}

      <FireLayer />
      <MarkersLayer />
    </Map>
  )
}
