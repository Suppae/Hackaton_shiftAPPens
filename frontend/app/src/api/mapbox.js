const TOKEN = "pk.eyJ1IjoidGlhZ29tYW5pbmhhIiwiYSI6ImNtb213emZqYTBpdjcyc3M0bHlldWZnc2gifQ.KogqOP6C00qQ8VNtk847Ng"
const BASE = 'https://api.mapbox.com/directions/v5/mapbox/driving'

function buildExclude(excludePolygons) {
  if (!excludePolygons.length) return null
  const polyStrings = excludePolygons.map((coords) => {
    const ring = coords[0]
    const points = ring.map(([lon, lat]) => `${lon} ${lat}`).join(',')
    return `polygon((${points}))`
  })
  return polyStrings.join(',')
}

async function callDirections(origin, destination, excludeStr) {
  const coordStr = `${origin[0]},${origin[1]};${destination[0]},${destination[1]}`
  const params = new URLSearchParams({
    geometries: 'geojson',
    overview: 'full',
    steps: 'false',
    access_token: TOKEN,
  })
  if (excludeStr) params.append('exclude', excludeStr)

  const res = await fetch(`${BASE}/${coordStr}?${params}`)
  if (!res.ok) {
    const err = new Error(`Mapbox Directions HTTP ${res.status}`)
    err.status = res.status
    throw err
  }
  const data = await res.json()
  if (!data.routes?.length) throw new Error('Sem rota possível')

  return {
    geometry: data.routes[0].geometry,
    distance_km: data.routes[0].distance / 1000,
    duration_min: data.routes[0].duration / 60,
  }
}

export async function fetchRoute(origin, destination, excludePolygons = []) {
  // Try with fire polygon exclusions first
  if (excludePolygons.length) {
    try {
      return await callDirections(origin, destination, buildExclude(excludePolygons))
    } catch (e) {
      // 422 = exclude not supported by this plan; fall through to route without exclusions
      if (e.status !== 422) console.warn('Reroute with exclude failed:', e.message)
    }
  }

  // Fetch normal route (no exclusions)
  try {
    return await callDirections(origin, destination, null)
  } catch (e) {
    console.error('Route calculation failed:', e.message)
    return null
  }
}
