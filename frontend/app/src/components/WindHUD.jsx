import { useEffect, useState } from 'react'
import useStore from '@/store'
import { degreesToCompass } from '@/utils/format'

export default function WindHUD() {
  const vectors = useStore((s) => s.vectors)
  const environmental_data = useStore((s) => s.environmental_data)
  const metadata = useStore((s) => s.metadata)
  const [pulse, setPulse] = useState(1)

  useEffect(() => {
    let dir = -1
    const id = setInterval(() => {
      setPulse((p) => {
        const next = p + dir * 0.04
        if (next <= 0.6) { dir = 1; return 0.6 }
        if (next >= 1.0) { dir = -1; return 1.0 }
        return next
      })
    }, 40)
    return () => clearInterval(id)
  }, [])

  const windSpeedMs = metadata?.wind_speed_ms
  const windDirDeg = vectors?.wind_angle ?? metadata?.wind_direction_deg
  const humidity = environmental_data?.humidity_pct ?? metadata?.humidity_pct

  if (windSpeedMs === undefined && windDirDeg === undefined) return null

  const compass = windDirDeg !== undefined ? degreesToCompass(windDirDeg) : 'N/A'
  const rotation = windDirDeg ?? 0

  return (
    <div className="absolute top-4 right-4 z-10">
      <div className="rounded-xl p-4 border border-white/5 bg-black/70 backdrop-blur-md flex flex-col items-center gap-2.5"
        style={{ minWidth: 120 }}>
        <div className="text-[11px] font-semibold text-white/40 tracking-[0.2em] uppercase">Vento</div>

        <div style={{ transform: `rotate(${rotation}deg)`, transition: 'transform 0.5s ease-out' }}>
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <line x1="24" y1="44" x2="24" y2="8" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round"/>
            <polygon
              points="24,4 19,14 29,14"
              fill="#ef4444"
              opacity={pulse}
              style={{ filter: `drop-shadow(0 0 4px #ef4444)` }}
            />
            <circle cx="24" cy="44" r="3" fill="#ef4444" opacity="0.5"/>
          </svg>
        </div>

        <div className="text-center">
          <div className="font-mono text-lg text-white font-bold leading-tight">
            {windSpeedMs?.toFixed(1) ?? '—'} <span className="text-xs text-white/50">m/s</span>
          </div>
          <div className="font-mono text-sm text-red-400 font-semibold">{compass}</div>
        </div>

        <div className="border-t border-white/5 w-full pt-2 text-center">
          <div className="text-[10px] text-white/35 font-medium">Humidade</div>
          <div className="font-mono text-sm text-cyan-400/80 font-semibold">
            {humidity !== undefined ? `${humidity}%` : '—'}
          </div>
        </div>

        {vectors && (
          <div className="border-t border-white/5 w-full pt-2 text-center">
            <div className="text-[10px] text-white/35 font-medium">Propagação</div>
            <div className="font-mono text-sm text-red-400/90 font-semibold">
              {vectors.speed_m_per_min?.toFixed(1)} m/min
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
