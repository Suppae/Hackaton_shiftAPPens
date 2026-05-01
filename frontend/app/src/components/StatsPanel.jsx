import useStore from '@/store'
import { formatArea, formatDistance, formatDuration } from '@/utils/format'

export default function StatsPanel() {
  const timesteps = useStore((s) => s.timesteps)
  const currentStep = useStore((s) => s.currentStep)
  const currentRoute = useStore((s) => s.currentRoute)
  const isRerouted = useStore((s) => s.isRerouted)
  const status = useStore((s) => s.status)

  const currentFire = currentStep > 0 ? timesteps[currentStep - 1] : null
  const area = formatArea(currentFire?.burned_area)
  const distance = formatDistance(currentRoute?.properties?.distance)
  const eta = formatDuration(currentRoute?.properties?.duration)

  return (
    <div className="absolute bottom-24 left-4 z-10">
      <div className="bg-black/70 backdrop-blur-md rounded-xl p-4 border border-white/10"
        style={{ minWidth: 220 }}>

        {status === 'loading' && (
          <div className="font-mono text-xs text-orange-400 mb-2 animate-pulse">
            A carregar simulação...
          </div>
        )}

        {isRerouted && (
          <div className="mb-3 px-2 py-1 rounded text-xs font-mono font-bold text-center animate-pulse"
            style={{ background: '#ff2e2e22', border: '1px solid #ff2e2e', color: '#ff2e2e' }}>
            REROUTED
          </div>
        )}

        <div className="flex flex-col gap-2">
          <StatRow label="Área ardida" value={`${area} km²`} color="text-orange-400" />
          <StatRow label="Distância"   value={`${distance} km`} color="text-green-400" />
          <StatRow label="ETA"         value={eta}              color="text-cyan-400" />
          {currentStep > 0 && (
            <StatRow
              label="Timestep"
              value={`T+${currentFire?.minutes_elapsed ?? 0}min`}
              color="text-white/60"
            />
          )}
        </div>
      </div>
    </div>
  )
}

function StatRow({ label, value, color }) {
  return (
    <div className="flex justify-between items-baseline gap-4">
      <span className="text-xs text-white/50 font-sans">{label}</span>
      <span className={`font-mono text-sm font-semibold ${color}`}>{value}</span>
    </div>
  )
}
