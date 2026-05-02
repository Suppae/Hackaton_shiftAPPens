import { Marker } from 'react-map-gl'
import useStore from '@/store'

function IgnitionPin() {
  return (
    <div style={{
      width: 18,
      height: 18,
      borderRadius: '50%',
      background: '#ff4500',
      border: '2px solid #ff8c1a',
      boxShadow: '0 0 8px #ff4500, 0 0 16px #ff4500',
    }} />
  )
}

export default function MarkersLayer() {
  const ignition = useStore((s) => s.ignition)

  if (!ignition) return null

  return (
    <Marker longitude={ignition[0]} latitude={ignition[1]} anchor="center">
      <IgnitionPin />
    </Marker>
  )
}
