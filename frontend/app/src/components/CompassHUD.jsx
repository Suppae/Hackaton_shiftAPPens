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
        className="rounded-2xl border border-white/10 bg-slate-950/80 backdrop-blur-xl shadow-[0_18px_45px_rgba(0,0,0,0.45)] px-4 py-3"
        style={{ width: 190 }}
        aria-label={`Bússola com bearing de ${Math.round(bearing)} graus`}
      >
        <div className="flex items-center gap-2 mb-3">
          <div className="relative flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 via-cyan-400 to-orange-400 shadow-[0_0_20px_rgba(255,140,26,0.35)]">
            <div className="h-5 w-5 rounded-full bg-slate-950/95 border border-white/10" />
            <div className="absolute inset-0 rounded-full border border-white/10" />
          </div>

          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-[0.35em] text-white/45">Bússola</div>
            <div className="text-sm font-semibold text-white leading-tight">Norte em tempo real</div>
          </div>
        </div>

        <div className="relative mx-auto flex h-24 w-24 items-center justify-center">
          <div className="absolute inset-0 rounded-full border border-white/10 bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.10),rgba(0,0,0,0.85)_72%)] shadow-[inset_0_0_18px_rgba(255,255,255,0.05)]" />
          <div className="absolute inset-2 rounded-full border border-white/5" />
          <div className="absolute inset-5 rounded-full border border-white/5" />
          <div className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2 rounded-full border border-emerald-300/40 bg-emerald-300 px-2 py-0.5 text-[9px] font-black tracking-[0.3em] text-slate-950 shadow-[0_0_12px_rgba(57,255,20,0.45)]">
            N
          </div>

          <div
            className="absolute inset-0 transition-transform duration-300 ease-out"
            style={{ transform: dialRotation }}
          >
            <div className="absolute left-1/2 top-2 -translate-x-1/2 rounded-full px-1.5 py-0.5 text-[10px] font-black text-emerald-300 drop-shadow-[0_0_8px_rgba(57,255,20,0.75)]">
              N
            </div>
            <div className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-full px-1.5 py-0.5 text-[10px] font-black text-white/70">
              E
            </div>
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 rounded-full px-1.5 py-0.5 text-[10px] font-black text-white/70">
              S
            </div>
            <div className="absolute left-1.5 top-1/2 -translate-y-1/2 rounded-full px-1.5 py-0.5 text-[10px] font-black text-white/70">
              W
            </div>

            <div className="absolute left-1/2 top-1/2 h-11 w-0.5 -translate-x-1/2 -translate-y-full rounded-full bg-gradient-to-b from-emerald-300 via-orange-300 to-transparent shadow-[0_0_10px_rgba(255,140,26,0.55)]" />
            <div className="absolute left-1/2 top-1/2 h-0.5 w-11 -translate-x-full -translate-y-1/2 rounded-full bg-gradient-to-r from-emerald-300 via-orange-300 to-transparent shadow-[0_0_10px_rgba(255,140,26,0.4)]" />
            <div className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/15 bg-white/90 shadow-[0_0_12px_rgba(255,255,255,0.25)]" />
            <div className="absolute left-1/2 top-3 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-emerald-300 shadow-[0_0_10px_rgba(57,255,20,0.8)]" />
          </div>

          <div className="absolute left-1/2 top-0 h-3 w-3 -translate-x-1/2 -translate-y-1 rounded-sm border-t border-l border-white/35 bg-slate-950/90 rotate-45 shadow-[0_0_10px_rgba(255,255,255,0.08)]" />
          <div className="absolute inset-0 rounded-full border border-white/5" />
        </div>

        <div className="mt-3 flex items-end justify-between border-t border-white/8 pt-2">
          <div>
            <div className="text-[10px] uppercase tracking-[0.28em] text-white/45">Direção</div>
            <div className="font-mono text-lg font-bold text-white leading-none">{Math.round(bearing)}°</div>
          </div>
          <div className="text-right">
            <div className="text-[10px] uppercase tracking-[0.28em] text-white/45">Norte</div>
            <div className="font-semibold text-emerald-300 leading-none">↑</div>
          </div>
        </div>
      </div>
    </div>
  )
}