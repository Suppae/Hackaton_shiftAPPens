export function formatArea(polygon) {
  if (!polygon) return '0.0'
  const coords = polygon.geometry.coordinates[0]
  let area = 0
  for (let i = 0; i < coords.length - 1; i++) {
    area += coords[i][0] * coords[i + 1][1] - coords[i + 1][0] * coords[i][1]
  }
  area = Math.abs(area) / 2
  const avgLat = coords.reduce((s, c) => s + c[1], 0) / coords.length
  const latKm = 111.32
  const lonKm = 111.32 * Math.cos(avgLat * Math.PI / 180)
  return (area * latKm * lonKm).toFixed(1)
}

export function formatDistance(meters) {
  if (!meters) return '0.0'
  return (meters / 1000).toFixed(1)
}

export function formatDuration(seconds) {
  if (!seconds) return '0'
  const mins = Math.round(seconds / 60)
  if (mins < 60) return `${mins}min`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return `${h}h${String(m).padStart(2, '0')}`
}

export function degreesToCompass(deg) {
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO']
  return dirs[Math.round(((deg % 360) + 360) % 360 / 45) % 8]
}
