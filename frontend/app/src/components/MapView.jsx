import { useCallback } from 'react'
import Map, { Source, Layer } from 'react-map-gl'
import mapboxgl from 'mapbox-gl'
import FireLayer from './FireLayer'
import RouteLayer from './RouteLayer'
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

// Estilo dos focos reais
const activeFiresStyle = {
    id: 'active-fires-layer',
    type: 'circle',
    paint: {
      'circle-radius': 6,
      'circle-color': '#ff0000', 
      'circle-stroke-width': 2,
      'circle-stroke-color': '#ffff00', 
      'circle-opacity': 0.8
    }
};

export default function MapView({ mapRef, onMapClick, activeFires }) {
  const mode = useStore((s) => s.mode)

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
    // 1. Verificar se clicámos num fogo real primeiro
    const features = e.features;
    if (features && features.length > 0) {
        const fireFeature = features.find(f => f.layer.id === 'active-fires-layer');
        if (fireFeature && onMapClick) {
            onMapClick([fireFeature.geometry.coordinates[0], fireFeature.geometry.coordinates[1]]);
            return; // Sai cedo, já encontrou o fogo
        }
    }

    // 2. Se for modo custom e clicou no vazio, gera fogo ali mesmo (Fallback)
    if (mode === 'custom' && onMapClick) {
      onMapClick([e.lngLat.lng, e.lngLat.lat])
    }
  }, [mode, onMapClick])

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
      interactiveLayerIds={['active-fires-layer']} /* IMPORTANTE: Torna os pontos clicáveis */
      cursor={mode === 'custom' ? 'crosshair' : 'auto'}
    >
      {/* Desenha os pontos de ignição reais */}
      {activeFires && (
          <Source id="active-fires-data" type="geojson" data={activeFires}>
            <Layer {...activeFiresStyle} />
          </Source>
      )}

      <FireLayer />
      {/* <RouteLayer /> */}
      {/* <MarkersLayer /> */}
    </Map>
  )
}