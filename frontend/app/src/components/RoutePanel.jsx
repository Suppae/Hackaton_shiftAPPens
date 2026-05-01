import { useState } from 'react'
import useStore from '@/store'
import { fetchRoute } from '@/api/mapbox'

const LOCATIONS = [
  { name: 'Pedrógão Grande',   coords: [-8.140, 40.045] },
  { name: 'Hospital de Leiria', coords: [-8.807, 39.749] },
  { name: 'Manteigas',          coords: [-7.539, 40.402] },
  { name: 'Hospital da Covilhã', coords: [-7.508, 40.281] },
  { name: 'Vila de Rei',         coords: [-8.144, 39.674] },
  { name: 'Castelo Branco',      coords: [-7.491, 39.822] },
  { name: 'Coimbra',             coords: [-8.429, 40.211] },
  { name: 'Guarda',              coords: [-7.267, 40.537] },
]

const SCENARIOS = [
  { id: 'demo',     label: 'Serra da Estrela', center: [-7.6167, 40.3217], origin: [-7.70, 40.28], destination: [-7.53, 40.37] },
  { id: 'pedrogao', label: 'Pedrógão Grande',  center: [-8.140, 40.045],  origin: [-8.25, 40.00], destination: [-7.98, 40.12], ignition: { ignition_lon: -8.140, ignition_lat: 40.045, wind_speed_ms: 12, wind_direction_deg: 225, humidity_pct: 20 } },
  { id: 'custom',   label: 'Custom',            center: null },
]

function coordsMatch(a, b) {
  return a && b && a[0] === b[0] && a[1] === b[1]
}

export default function RoutePanel({ onScenarioSelect }) {
  const origin      = useStore((s) => s.origin)
  const destination = useStore((s) => s.destination)
  const currentRoute = useStore((s) => s.currentRoute)
  const isRerouted  = useStore((s) => s.isRerouted)
  const mode        = useStore((s) => s.mode)
  const setOrigin      = useStore((s) => s.setOrigin)
  const setDestination = useStore((s) => s.setDestination)
  const setCurrentRoute = useStore((s) => s.setCurrentRoute)
  const resetReroute   = useStore((s) => s.resetReroute)

  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const originName = LOCATIONS.find((l) => coordsMatch(l.coords, origin))?.name ?? 'Personalizado'
  const destName   = LOCATIONS.find((l) => coordsMatch(l.coords, destination))?.name ?? 'Personalizado'
  const samePlace  = coordsMatch(origin, destination)

  const handleCalculate = async () => {
    if (samePlace || loading) return
    setLoading(true)
    setError(null)
    const route = await fetchRoute(origin, destination)
    if (route) {
      resetReroute()
      setCurrentRoute(route)
    } else {
      setError('Rota não encontrada. Verifica o token Mapbox.')
    }
    setLoading(false)
  }

  return (
    <div className="absolute top-4 left-4 z-10" style={{ width: 360 }}>
      <div
        className="rounded-2xl shadow-2xl p-5"
        style={{
          background: 'rgba(15,15,15,0.88)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255,255,255,0.10)',
        }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 mb-4">
          <span style={{ fontSize: 20 }}>🔥</span>
          <span className="text-white font-semibold text-base" style={{ fontFamily: 'Inter, sans-serif' }}>
            Wildfire Routing
          </span>
        </div>

        {/* Scenario tabs */}
        <div className="flex gap-1.5 mb-5">
          {SCENARIOS.map((sc) => (
            <button
              key={sc.id}
              onClick={() => onScenarioSelect(sc)}
              style={{
                flex: 1,
                padding: '5px 4px',
                borderRadius: 8,
                fontSize: 11,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 500,
                transition: 'all 0.15s',
                background: mode === sc.id ? 'rgba(255,140,26,0.20)' : 'rgba(255,255,255,0.05)',
                border: mode === sc.id ? '1px solid #ff8c1a' : '1px solid rgba(255,255,255,0.08)',
                color: mode === sc.id ? '#ff8c1a' : 'rgba(255,255,255,0.55)',
                cursor: 'pointer',
              }}
            >
              {sc.label}
            </button>
          ))}
        </div>

        {/* Origin */}
        <div className="mb-3">
          <div className="flex items-center gap-2 mb-1.5">
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#39ff14', boxShadow: '0 0 6px #39ff14', flexShrink: 0 }} />
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', fontFamily: 'Inter, sans-serif', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Origem</span>
          </div>
          <select
            value={originName}
            onChange={(e) => {
              const loc = LOCATIONS.find((l) => l.name === e.target.value)
              if (loc) setOrigin(loc.coords)
            }}
            style={{
              width: '100%',
              background: 'rgba(255,255,255,0.07)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 8,
              padding: '8px 12px',
              color: '#fff',
              fontSize: 13,
              fontFamily: 'Inter, sans-serif',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            {LOCATIONS.map((l) => (
              <option key={l.name} value={l.name} style={{ background: '#1a1a1a' }}>{l.name}</option>
            ))}
          </select>
        </div>

        {/* Destination */}
        <div className="mb-5">
          <div className="flex items-center gap-2 mb-1.5">
            <div style={{ width: 10, height: 10, borderRadius: '50%', background: '#22d3ee', boxShadow: '0 0 6px #22d3ee', flexShrink: 0 }} />
            <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.45)', fontFamily: 'Inter, sans-serif', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Destino</span>
          </div>
          <select
            value={destName}
            onChange={(e) => {
              const loc = LOCATIONS.find((l) => l.name === e.target.value)
              if (loc) setDestination(loc.coords)
            }}
            style={{
              width: '100%',
              background: 'rgba(255,255,255,0.07)',
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 8,
              padding: '8px 12px',
              color: '#fff',
              fontSize: 13,
              fontFamily: 'Inter, sans-serif',
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            {LOCATIONS.map((l) => (
              <option key={l.name} value={l.name} style={{ background: '#1a1a1a' }}>{l.name}</option>
            ))}
          </select>
        </div>

        {/* Calculate button */}
        <button
          onClick={handleCalculate}
          disabled={samePlace || loading}
          style={{
            width: '100%',
            padding: '11px 0',
            borderRadius: 12,
            fontFamily: 'Inter, sans-serif',
            fontWeight: 700,
            fontSize: 13,
            letterSpacing: '0.05em',
            border: 'none',
            cursor: samePlace || loading ? 'not-allowed' : 'pointer',
            background: samePlace || loading ? 'rgba(57,255,20,0.25)' : '#39ff14',
            color: samePlace || loading ? 'rgba(0,0,0,0.35)' : '#000',
            transition: 'all 0.15s',
          }}
          onMouseEnter={(e) => { if (!samePlace && !loading) e.target.style.background = '#5aff30' }}
          onMouseLeave={(e) => { if (!samePlace && !loading) e.target.style.background = '#39ff14' }}
        >
          {loading ? 'A calcular...' : 'CALCULAR ROTA'}
        </button>

        {/* Error toast */}
        {error && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#f87171', fontFamily: 'Inter, sans-serif', textAlign: 'center' }}>
            {error}
          </div>
        )}

        {/* Route stats */}
        {currentRoute && !error && (
          <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="flex items-center justify-between">
              <div className="flex gap-5">
                <div>
                  <div className="font-mono" style={{ fontSize: 18, fontWeight: 600, color: '#fff', lineHeight: 1 }}>
                    {currentRoute.distance_km.toFixed(1)}
                  </div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2, fontFamily: 'Inter, sans-serif' }}>km</div>
                </div>
                <div>
                  <div className="font-mono" style={{ fontSize: 18, fontWeight: 600, color: '#fff', lineHeight: 1 }}>
                    {Math.round(currentRoute.duration_min)}
                  </div>
                  <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2, fontFamily: 'Inter, sans-serif' }}>min</div>
                </div>
              </div>
              {isRerouted && (
                <div
                  className="animate-pulse font-mono"
                  style={{
                    padding: '4px 10px',
                    borderRadius: 6,
                    fontSize: 11,
                    fontWeight: 700,
                    background: 'rgba(255,46,46,0.15)',
                    border: '1px solid #ff2e2e',
                    color: '#ff2e2e',
                  }}
                >
                  REROUTED
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export { SCENARIOS }
