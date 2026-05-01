import { Marker } from 'react-map-gl'
import useStore from '@/store'

function Pin({ color, label }) {
  return (
    <div style={{ position: 'relative', cursor: 'grab' }}>
      <svg width="28" height="36" viewBox="0 0 28 36" fill="none">
        <path
          d="M14 0C6.268 0 0 6.268 0 14c0 9.333 14 22 14 22S28 23.333 28 14C28 6.268 21.732 0 14 0z"
          fill={color}
        />
        <circle cx="14" cy="14" r="5" fill="white" fillOpacity="0.9" />
      </svg>
      <span style={{
        position: 'absolute',
        top: '-20px',
        left: '50%',
        transform: 'translateX(-50%)',
        color,
        fontSize: '10px',
        fontFamily: 'monospace',
        fontWeight: 700,
        whiteSpace: 'nowrap',
        textShadow: '0 1px 3px #000',
      }}>
        {label}
      </span>
    </div>
  )
}

function IgnitionPin() {
  return (
    <div style={{
      width: 20,
      height: 20,
      borderRadius: '50%',
      background: '#ff4500',
      border: '2px solid #ff8c1a',
      boxShadow: '0 0 10px #ff4500, 0 0 20px #ff4500',
      animation: 'pulse 1s ease-in-out infinite alternate',
    }} />
  )
}

export default function MarkersLayer() {
  const origin = useStore((s) => s.origin)
  const destination = useStore((s) => s.destination)
  const ignition = useStore((s) => s.ignition)
  const setOrigin = useStore((s) => s.setOrigin)
  const setDestination = useStore((s) => s.setDestination)

  return (
    <>
      {ignition && (
        <Marker longitude={ignition[0]} latitude={ignition[1]} anchor="center">
          <IgnitionPin />
        </Marker>
      )}
      <Marker
        longitude={origin[0]}
        latitude={origin[1]}
        anchor="bottom"
        draggable
        onDragEnd={(e) => setOrigin([e.lngLat.lng, e.lngLat.lat])}
      >
        <Pin color="#39ff14" label="ORIGEM" />
      </Marker>
      <Marker
        longitude={destination[0]}
        latitude={destination[1]}
        anchor="bottom"
        draggable
        onDragEnd={(e) => setDestination([e.lngLat.lng, e.lngLat.lat])}
      >
        <Pin color="#22d3ee" label="DESTINO" />
      </Marker>
    </>
  )
}
