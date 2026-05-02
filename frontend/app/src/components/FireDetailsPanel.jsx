import useStore from '@/store'

export default function FireDetailsPanel() {
  const selectedFire = useStore((s) => s.selectedFire)
  const setSelectedFire = useStore((s) => s.setSelectedFire)

  if (!selectedFire) return null

  const { timestep, fireIndex } = selectedFire
  const burnedArea = timestep.burned_area
  const geometry = burnedArea.geometry

  // Calculate polygon area (simples approximação)
  const coords = geometry.coordinates[0]
  const calculateArea = (ring) => {
    let area = 0
    for (let i = 0; i < ring.length - 1; i++) {
      const [lon1, lat1] = ring[i]
      const [lon2, lat2] = ring[i + 1]
      area += (lon2 - lon1) * (lat2 + lat1) / 2
    }
    return Math.abs(area) * 111 * 111 // Aproximação para km²
  }
  const polygonArea = calculateArea(coords)

  // Calculate perimeter
  const calculatePerimeter = (ring) => {
    let perimeter = 0
    for (let i = 0; i < ring.length - 1; i++) {
      const [lon1, lat1] = ring[i]
      const [lon2, lat2] = ring[i + 1]
      const dlat = (lat2 - lat1) * 111
      const dlon = (lon2 - lon1) * 111 * Math.cos((lat1 + lat2) / 2 * Math.PI / 180)
      perimeter += Math.sqrt(dlat * dlat + dlon * dlon)
    }
    return perimeter
  }
  const perimeter = calculatePerimeter(coords)

  // Get centroid
  const getCentroid = (ring) => {
    let x = 0, y = 0
    for (const [lon, lat] of ring) {
      x += lon
      y += lat
    }
    return [x / ring.length, y / ring.length]
  }
  const [centerLon, centerLat] = getCentroid(coords)

  const intensity = burnedArea.properties?.intensity ?? 'N/A'

  return (
    <div className="h-full overflow-y-auto p-4">
      <div className="h-full bg-black/90 backdrop-blur-md rounded-tr-3xl rounded-br-3xl border border-orange-400/30 p-5 shadow-2xl">
        <div className="flex justify-between items-center mb-4 border-b border-orange-400/20 pb-3">
          <h2 className="text-lg font-bold text-orange-400">🔥 Detalhes do Fogo</h2>
          <button
            onClick={() => setSelectedFire(null)}
            className="text-white/50 hover:text-white text-xl w-8 h-8 flex items-center justify-center rounded hover:bg-white/10 transition"
          >
            ✕
          </button>
        </div>

        {/* Conteúdo principal */}
        <div className="space-y-4">
          
          {/* Tempo */}
          <DetailRow 
            label="Tempo Decorrido"
            value={`${timestep.minutes_elapsed} min`}
            icon="⏱️"
          />

          {/* Índice do timestep */}
          <DetailRow 
            label="Timestep"
            value={`T+${fireIndex}`}
            icon="📍"
          />

          {/* Área queimada */}
          <DetailRow 
            label="Área Queimada"
            value={`${polygonArea.toFixed(2)} km²`}
            icon="📐"
            highlight
          />

          {/* Perímetro */}
          <DetailRow 
            label="Perímetro"
            value={`${perimeter.toFixed(2)} km`}
            icon="📏"
          />

          {/* Intensidade */}
          <DetailRow 
            label="Intensidade"
            value={typeof intensity === 'number' ? intensity.toFixed(2) : intensity}
            icon="🌡️"
          />

          {/* Divisor */}
          <div className="border-t border-orange-400/20 my-3"></div>

          {/* Coordenadas do centro */}
          <div>
            <p className="text-xs text-white/50 font-mono mb-2">📌 Centro do Fogo</p>
            <div className="bg-black/40 rounded p-2 font-mono text-xs text-cyan-300 space-y-1">
              <div>Latitude: {centerLat.toFixed(5)}°</div>
              <div>Longitude: {centerLon.toFixed(5)}°</div>
            </div>
          </div>

          {/* Número de pontos do polígono */}
          <DetailRow 
            label="Pontos do Perímetro"
            value={coords.length - 1}
            icon="◆"
          />

        </div>

        {/* Footer informativo */}
        <div className="mt-4 pt-3 border-t border-orange-400/20">
          <p className="text-xs text-white/40 text-center">
            Clique no mapa para fechar
          </p>
        </div>

      </div>
    </div>
  )
}

function DetailRow({ label, value, icon = '•', highlight = false }) {
  return (
    <div className={`flex justify-between items-baseline gap-2 ${highlight ? 'bg-orange-400/10 p-2 rounded' : ''}`}>
      <span className="text-xs text-white/50">{icon} {label}</span>
      <span className={`font-mono font-semibold ${highlight ? 'text-orange-300 text-sm' : 'text-white/70 text-xs'}`}>
        {value}
      </span>
    </div>
  )
}
