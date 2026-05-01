import useStore from '@/store'

const SCENARIOS = [
  {
    id: 'pedrogao',
    label: 'Pedrógão Grande',
    icon: '🔥',
    ignition: { ignition_lon: -8.140, ignition_lat: 40.045, wind_speed_ms: 12, wind_direction_deg: 225, humidity_pct: 20 },
    center: [-8.140, 40.045],
    origin: [-8.25, 40.00],
    destination: [-7.98, 40.12],
  },
  {
    id: 'demo',
    label: 'Serra da Estrela',
    icon: '⛰️',
    center: [-7.6167, 40.3217],
    origin: [-7.70, 40.28],
    destination: [-7.53, 40.37],
  },
  {
    id: 'custom',
    label: 'Custom',
    icon: '📍',
    center: null,
  },
]

export default function ScenarioPicker({ onSelect }) {
  const mode = useStore((s) => s.mode)

  return (
    <div className="absolute top-4 left-4 z-10">
      <div className="bg-black/70 backdrop-blur-md rounded-xl p-3 border border-white/10">
        <div className="text-xs font-mono text-white/50 mb-2 tracking-widest uppercase">Cenário</div>
        <div className="flex flex-col gap-1.5">
          {SCENARIOS.map((sc) => (
            <button
              key={sc.id}
              onClick={() => onSelect(sc)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-sans transition-all duration-200 text-left"
              style={{
                background: mode === sc.id ? 'rgba(255,140,26,0.25)' : 'rgba(255,255,255,0.05)',
                border: mode === sc.id ? '1px solid #ff8c1a' : '1px solid transparent',
                color: mode === sc.id ? '#ff8c1a' : 'rgba(255,255,255,0.75)',
              }}
            >
              <span>{sc.icon}</span>
              <span>{sc.label}</span>
              {sc.id === 'custom' && mode === 'custom' && (
                <span className="text-xs text-white/40 ml-1">(click no mapa)</span>
              )}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

export { SCENARIOS }
