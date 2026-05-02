import { useEffect, useState } from 'react'

function normalizeBearing(value) {
  return ((value % 360) + 360) % 360
}

export default function CompassHUD({ mapRef }) {
  const [bearing, setBearing] = useState(0)

  useEffect(() => {
    let cleanup = () => {}

    const bindMap = () => {
      const map = mapRef.current?.getMap?.() ?? mapRef.current
      if (!map?.on || !map?.off || !map?.getBearing) return false

      const updateBearing = () => setBearing(normalizeBearing(map.getBearing()))
      updateBearing()

      map.on('move', updateBearing)
      map.on('rotate', updateBearing)

      cleanup = () => {
        map.off('move', updateBearing)
        map.off('rotate', updateBearing)
      }

      return true
    }

    if (bindMap()) return cleanup

    const id = setInterval(() => {
      if (bindMap()) clearInterval(id)
    }, 150)

    return () => {
      clearInterval(id)
      cleanup()
    }
  }, [mapRef])

  const dialRotation = `rotate(${-bearing}deg)`

  return (
    <div className="absolute bottom-6 left-4 z-10 pointer-events-none select-none">
      <div
        className="rounded-2xl border border-white/10 bg-slate-950/80 backdrop-blur-xl shadow-[0_18px_45px_rgba(0,0,0,0.45)] px-4 py-4 flex flex-col items-center gap-3"
        style={{ width: 140 }}
      >
        <div className="text-sm font-mono font-bold text-white">{Math.round(bearing)}°</div>

        <div className="relative flex h-20 w-20 items-center justify-center">
          <div className="absolute inset-0 rounded-full border border-white/10 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.10),rgba(0,0,0,0.85)_72%)]" />
          <div className="absolute inset-2 rounded-full border border-white/5" />
          
          {/* Pontos cardinais fixos */}
          <div className="absolute left-1/2 top-0 -translate-x-1/2 text-[11px] font-bold text-emerald-300">N</div>
          <div className="absolute right-0 top-1/2 -translate-y-1/2 text-[11px] font-bold text-white/70">E</div>
          <div className="absolute bottom-0 left-1/2 -translate-x-1/2 text-[11px] font-bold text-white/70">S</div>
          <div className="absolute left-0 top-1/2 -translate-y-1/2 text-[11px] font-bold text-white/70">O</div>

          <div
            className="absolute inset-0 transition-transform duration-300 ease-out"
            style={{ transform: dialRotation }}
          >
            <div className="absolute left-1/2 top-1/2 h-8 w-0.5 -translate-x-1/2 -translate-y-full rounded-full bg-gradient-to-b from-emerald-300 to-transparent shadow-[0_0_8px_rgba(57,255,20,0.75)]" />
            <div className="absolute left-1/2 top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow-[0_0_8px_rgba(255,255,255,0.3)]" />
          </div>

          <div className="absolute inset-0 rounded-full border border-white/5" />
        </div>
      </div>
    </div>
  )
}