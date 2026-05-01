import { useCallback } from 'react'
import Map, { NavigationControl } from 'react-map-gl'
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

export default function MapView({ mapRef, onMapClick }) {
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
      cursor={mode === 'custom' ? 'crosshair' : 'auto'}
    >
      <NavigationControl position="bottom-right" />
      <FireLayer />
      <RouteLayer />
      <MarkersLayer />
    </Map>
  )
}
