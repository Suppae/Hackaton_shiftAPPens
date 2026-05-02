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
const TOKEN = "pk.eyJ1IjoidGlhZ29tYW5pbmhhIiwiYSI6ImNtb213emZqYTBpdjcyc3M0bHlldWZnc2gifQ.KogqOP6C00qQ8VNtk847Ng"

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
    const features = e.features
    if (!features || features.length === 0) return

    const fireFeature = features.find(f => f.layer.id === 'active-fires-layer' || f.layer.id === 'active-fires-glow')
    if (!fireFeature || !onMapClick) return

    const [lon, lat] = fireFeature.geometry.coordinates
    const props = fireFeature.properties || {}
    onMapClick([lon, lat], {
        town: props.town || 'Desconhecido',
        status: props.status || 'N/A',
        man: props.man || 0,
        terrain: props.terrain || '',
        fireId: props.id,
    })
  }, [onMapClick])

  const interactiveLayers = ['active-fires-layer', 'active-fires-glow']
  if (timesteps.length > 0 && currentStep > 0) {
    for (let i = 0; i < currentStep; i++) {
      interactiveLayers.push(`fire-fill-${i}`, `fire-glow-${i}`)
    }
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
