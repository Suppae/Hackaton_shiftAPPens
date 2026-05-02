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

  const calculateArea = (ring) => {
    if (!ring || ring.length < 3) return 0
    let area = 0
    for (let i = 0; i < ring.length - 1; i++) {
      const [lon1, lat1] = ring[i]
      const [lon2, lat2] = ring[i + 1]
      area += (lon2 - lon1) * (lat2 + lat1) / 2
    }
    return Math.abs(area) * 111 * 111
  }

  let totalArea = 0
  if (currentTs?.burned_area?.geometry?.coordinates) {
    totalArea = calculateArea(currentTs.burned_area.geometry.coordinates[0])
  }

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
      <div className="h-full bg-black/95 backdrop-blur-md border-l border-orange-400/20 flex flex-col">

        {/* Header */}
        <div className="px-5 py-4 border-b border-orange-400/20 flex-shrink-0">
          <div className="flex justify-between items-start">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                <h2 className="text-base font-bold text-orange-400 tracking-wide">
                  {activeFireInfo?.town || 'Localização'}
                </h2>
              </div>
              {activeFireInfo?.status && (
                <span className="text-xs font-mono text-white/50 uppercase tracking-wider">
                  {activeFireInfo.status}
                </span>
              )}
            </div>
            <button
              onClick={resetSimulation}
              className="text-white/40 hover:text-white text-lg w-7 h-7 flex items-center justify-center rounded hover:bg-white/10 transition"
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
              <p className="text-[10px] uppercase tracking-[0.3em] text-white/40 mb-2">Recursos no Terreno</p>
              <div className="bg-white/[0.03] rounded-lg p-3 border border-white/5">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-white/60">Bombeiros</span>
                  <span className="font-mono text-xl font-bold text-orange-300">
                    {activeFireInfo.man || '—'}
                  </span>
                </div>
                {activeFireInfo.terrain && (
                  <div className="mt-2 pt-2 border-t border-white/5 flex items-center justify-between">
                    <span className="text-xs text-white/40">Terreno</span>
                    <span className="font-mono text-xs text-white/60">{activeFireInfo.terrain}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Dados Ambientais (GEE + OWM) */}
          {environmental_data && (
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-white/40 mb-2">Dados Ambientais</p>
              <div className="grid grid-cols-2 gap-2">
                <EnvCard label="Temperatura" value={`${environmental_data.temperature_c?.toFixed(1) || '—'}°C`} color="text-red-400" />
                <EnvCard label="Humidade" value={`${environmental_data.humidity_pct?.toFixed(0) || '—'}%`} color="text-cyan-400" />
                <EnvCard label="Vento" value={`${environmental_data.wind_speed_kmh?.toFixed(1) || '—'} km/h`} color="text-orange-400" />
                <EnvCard label="Combustível" value={(environmental_data.fuel_load_mean?.toFixed(2)) || '—'} color="text-green-400" />
              </div>
              {environmental_data.ndvi_mean !== undefined && (
                <div className="mt-2 bg-white/[0.03] rounded p-2 border border-white/5 flex items-center justify-between">
                  <span className="text-xs text-white/40">NDVI (vegetação)</span>
                  <span className="font-mono text-xs text-green-400">{environmental_data.ndvi_mean.toFixed(3)}</span>
                </div>
              )}
            </div>
          )}

          {/* Vetores de Propagação */}
          {vectors && (
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-white/40 mb-2">Propagação</p>
              <div className="bg-white/[0.03] rounded-lg p-3 border border-white/5 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-white/50">Direção do Fogo</span>
                  <span className="font-mono text-sm text-orange-300 font-bold">
                    {spreadAngle?.toFixed(1)}° {spreadCompass && <span className="text-orange-400/60">({spreadCompass})</span>}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-white/50">Dir. do Vento (FROM)</span>
                  <span className="font-mono text-sm text-white/60">
                    {windAngle?.toFixed(1)}° {windCompass && <span className="text-white/40">({windCompass})</span>}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-white/50">Vel. Propagação</span>
                  <span className="font-mono text-sm text-red-400 font-bold">
                    {vectors.speed_m_per_min?.toFixed(1)} m/min
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Divisor */}
          <div className="border-t border-white/5" />

          {/* Info da Simulação */}
          {metadata && (
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-white/40 mb-2">Motor</p>
              <div className="bg-white/[0.03] rounded p-2 border border-white/5 flex items-center justify-between">
                <span className="text-xs text-white/40">Engine</span>
                <span className="font-mono text-xs text-white/60">{metadata.engine || source}</span>
              </div>
            </div>
          )}

          {/* Área Queimada (último timestep visível) */}
          {currentTs && totalArea > 0 && (
            <div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-white/40 mb-2">Área Queimada (T+{currentTs.minutes_elapsed}min)</p>
              <div className="bg-orange-400/5 rounded-lg p-4 border border-orange-400/20 text-center">
                <div className="font-mono text-3xl font-bold text-orange-300">
                  {totalArea.toFixed(2)}
                </div>
                <div className="text-xs text-white/40 mt-1">km²</div>
              </div>
            </div>
          )}

          {/* Coordenadas */}
          <div>
            <p className="text-[10px] uppercase tracking-[0.3em] text-white/40 mb-2">Coordenadas</p>
            <div className="bg-white/[0.03] rounded p-2 border border-white/5 font-mono text-xs text-cyan-300/70 space-y-0.5">
              <div>Lat: {centerLat.toFixed(5)}°</div>
              <div>Lon: {centerLon.toFixed(5)}°</div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-white/5 flex-shrink-0">
          <p className="text-[10px] text-white/30 text-center font-mono tracking-wider">
            FIRELYTICS · ROTEAMENTO TÁTICO
          </p>
        </div>
      </div>
    </div>
  )
}

function EnvCard({ label, value, color }) {
  return (
    <div className="bg-white/[0.03] rounded p-2.5 border border-white/5">
      <div className="text-[10px] text-white/40 mb-0.5">{label}</div>
      <div className={`font-mono text-sm font-bold ${color}`}>{value}</div>
    </div>
  )
}
