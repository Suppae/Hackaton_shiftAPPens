import useStore from '@/store'
import { degreesToCompass } from '@/utils/format'

export default function FireDetailsPanel() {
  const activeFireInfo = useStore((s) => s.activeFireInfo)
  const vectors = useStore((s) => s.vectors)
  const environmental_data = useStore((s) => s.environmental_data)
  const metadata = useStore((s) => s.metadata)
  const timesteps = useStore((s) => s.timesteps)
  const currentStep = useStore((s) => s.currentStep)
  const source = useStore((s) => s.source)
  const ignition = useStore((s) => s.ignition)
  const resetSimulation = useStore((s) => s.resetSimulation)

  const hasSimulation = timesteps.length > 0

  if (!activeFireInfo && !hasSimulation) return null

  const currentTs = currentStep > 0 ? timesteps[currentStep - 1] : null

  // Use area computed by the backend (already accounts for cell count × cell_size²)
  const totalArea = currentTs?.burned_area?.properties?.area_km2 ?? 0

  const spreadAngle = vectors?.primary_spread_angle
  const spreadCompass = spreadAngle !== undefined ? degreesToCompass(spreadAngle) : null
  const windAngle = vectors?.wind_angle
  const windCompass = windAngle !== undefined ? degreesToCompass(windAngle) : null

  const getCentroid = (ring) => {
    if (!ring || ring.length < 3) return [0, 0]
    let x = 0, y = 0
    for (const [lon, lat] of ring) {
      x += lon
      y += lat
    }
    return [x / ring.length, y / ring.length]
  }

  const [centerLon, centerLat] = currentTs?.burned_area?.geometry?.coordinates
    ? getCentroid(currentTs.burned_area.geometry.coordinates[0])
    : ignition || [0, 0]

  return (
    <div className="h-full overflow-y-auto panel-scroll">
      <div className="h-full bg-gradient-to-b from-gray-950 via-gray-950 to-[#080204] flex flex-col">

        {/* Header */}
        <div className="px-5 py-4 border-b border-red-900/30 flex-shrink-0">
          <div className="flex justify-between items-start">
            <div>
              <div className="flex items-center gap-2.5 mb-1.5">
                <div className="relative">
                  <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
                  <div className="absolute inset-0 w-3 h-3 rounded-full bg-red-500 animate-ping opacity-40" />
                </div>
                <h2 className="text-lg font-bold text-red-400 tracking-tight">
                  {activeFireInfo?.town || 'Localização'}
                </h2>
              </div>
              {activeFireInfo?.status && (
                <span className="text-[11px] font-semibold text-red-400/60 uppercase tracking-widest">
                  {activeFireInfo.status}
                </span>
              )}
            </div>
            <button
              onClick={resetSimulation}
              className="text-white/30 hover:text-white text-sm w-8 h-8 flex items-center justify-center rounded-lg hover:bg-white/5 transition"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">

          {/* Recursos */}
          {activeFireInfo && (
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/30 mb-3">Recursos no Terreno</p>
              <div className="rounded-xl p-4 border border-white/5 bg-gradient-to-br from-white/[0.02] to-transparent">
                <div className="flex items-baseline justify-between">
                  <span className="text-sm font-medium text-white/50">Bombeiros</span>
                  <span className="font-mono text-2xl font-bold text-red-400">
                    {activeFireInfo.man || '—'}
                  </span>
                </div>
                {activeFireInfo.terrain && (
                  <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between">
                    <span className="text-xs text-white/30">Terreno</span>
                    <span className="font-mono text-xs text-white/50">{activeFireInfo.terrain}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Dados Ambientais */}
          {environmental_data && (
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/30 mb-3">Dados Ambientais</p>
              <div className="grid grid-cols-2 gap-2.5">
                <EnvCard label="Temperatura" value={`${environmental_data.temperature_c?.toFixed(1) || '—'}°C`} icon="🌡" accent="red" />
                <EnvCard label="Humidade" value={`${environmental_data.humidity_pct?.toFixed(0) || '—'}%`} icon="💧" accent="cyan" />
                <EnvCard label="Vento" value={`${environmental_data.wind_speed_kmh?.toFixed(1) || '—'}`} unit="km/h" icon="💨" accent="amber" />
                <EnvCard label="Combustível" value={environmental_data.fuel_load_mean?.toFixed(2) || '—'} icon="🌿" accent="green" />
              </div>
              {environmental_data.ndvi_mean !== undefined && (
                <div className="mt-2.5 rounded-lg p-2.5 border border-white/5 bg-white/[0.01] flex items-center justify-between">
                  <span className="text-xs text-white/30">NDVI (vegetação)</span>
                  <span className="font-mono text-xs text-green-400/80">{environmental_data.ndvi_mean.toFixed(3)}</span>
                </div>
              )}
            </div>
          )}

          {/* Vetores de Propagação */}
          {vectors && (
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/30 mb-3">Propagação</p>
              <div className="rounded-xl p-4 border border-red-500/10 bg-gradient-to-br from-red-500/[0.03] to-transparent space-y-3">
                <VectorRow label="Direção do Fogo" value={`${spreadAngle?.toFixed(1)}°`} sub={spreadCompass} color="text-red-400" />
                <div className="h-px bg-gradient-to-r from-red-500/10 via-white/5 to-transparent" />
                <VectorRow label="Dir. do Vento (FROM)" value={`${windAngle?.toFixed(1)}°`} sub={windCompass} color="text-white/60" />
                <div className="h-px bg-gradient-to-r from-red-500/10 via-white/5 to-transparent" />
                <VectorRow label="Vel. Propagação" value={`${vectors.speed_m_per_min?.toFixed(1)}`} sub="m/min" color="text-red-300" bold />
              </div>
            </div>
          )}

          {/* Divisor */}
          <div className="h-px bg-gradient-to-r from-transparent via-white/5 to-transparent" />

          {/* Info da Simulação */}
          {metadata && (
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/30 mb-3">Motor</p>
              <div className="rounded-lg p-2.5 border border-white/5 bg-white/[0.01] flex items-center justify-between">
                <span className="text-xs text-white/30">Engine</span>
                <span className="font-mono text-xs text-white/40">{metadata.engine || source}</span>
              </div>
            </div>
          )}

          {/* Área Queimada */}
          {currentTs && totalArea > 0 && (
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/30 mb-3">Área Queimada</p>
              <div className="rounded-xl p-5 border border-red-500/15 bg-gradient-to-br from-red-500/[0.04] to-transparent text-center">
                <div className="font-mono text-4xl font-bold text-red-400 leading-none">
                  {totalArea.toFixed(2)}
                </div>
                <div className="text-xs text-white/30 mt-2 font-medium">km² · T+{currentTs.minutes_elapsed}min</div>
              </div>
            </div>
          )}

          {/* Coordenadas */}
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-white/30 mb-3">Coordenadas</p>
            <div className="rounded-lg p-3 border border-white/5 bg-white/[0.01] font-mono text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-white/25">Lat</span>
                <span className="text-cyan-300/60">{centerLat.toFixed(5)}°</span>
              </div>
              <div className="flex justify-between">
                <span className="text-white/25">Lon</span>
                <span className="text-cyan-300/60">{centerLon.toFixed(5)}°</span>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-white/5 flex-shrink-0">
          <p className="text-[10px] text-white/20 text-center font-semibold tracking-[0.25em]">
            FIRELYTICS · ROTEAMENTO TÁTICO
          </p>
        </div>
      </div>
    </div>
  )
}

function EnvCard({ label, value, unit, icon, accent }) {
  const accentMap = {
    red: 'text-red-400',
    cyan: 'text-cyan-400',
    amber: 'text-amber-400',
    green: 'text-green-400',
  }
  return (
    <div className="rounded-xl p-3 border border-white/5 bg-gradient-to-br from-white/[0.02] to-transparent">
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-xs opacity-40">{icon}</span>
        <span className="text-[10px] text-white/35 font-medium">{label}</span>
      </div>
      <div className={`font-mono text-base font-bold leading-none ${accentMap[accent] || 'text-white/70'}`}>
        {value}{unit && <span className="text-xs opacity-50 ml-0.5 font-normal">{unit}</span>}
      </div>
    </div>
  )
}

function VectorRow({ label, value, sub, color, bold }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-white/40">{label}</span>
      <span className={`font-mono text-sm ${bold ? 'font-bold' : 'font-medium'} ${color}`}>
        {value}{sub && <span className="text-xs opacity-40 ml-1">({sub})</span>}
      </span>
    </div>
  )
}
