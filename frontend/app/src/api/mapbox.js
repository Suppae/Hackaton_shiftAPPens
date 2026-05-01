const TOKEN = import.meta.env.VITE_MAPBOX_TOKEN

function straightLine(origin, destination, waypoint) {
  const coords = waypoint
    ? [origin, waypoint, destination]
    : [origin, destination]
  const dx = (destination[0] - origin[0]) * 111.32 * Math.cos(origin[1] * Math.PI / 180)
  const dy = (destination[1] - origin[1]) * 111.32
  const distKm = Math.sqrt(dx * dx + dy * dy)
  return {
    type: 'Feature',
    geometry: { type: 'LineString', coordinates: coords },
    properties: {
      distance: distKm * 1000,
      duration: (distKm / 0.05) * 60,
    },
  }
}

export async function fetchRoute(origin, destination, waypoint = null) {
  try {
    const coordStr = waypoint
      ? `${origin[0]},${origin[1]};${waypoint[0]},${waypoint[1]};${destination[0]},${destination[1]}`
      : `${origin[0]},${origin[1]};${destination[0]},${destination[1]}`

    const url = `https://api.mapbox.com/directions/v5/mapbox/driving/${coordStr}?geometries=geojson&overview=full&access_token=${TOKEN}`
    const res = await fetch(url)

    if (res.status === 401 || res.status === 429) {
      console.warn('Mapbox Directions rate limited, using fallback')
      return straightLine(origin, destination, waypoint)
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`)

    const data = await res.json()
    if (!data.routes?.[0]) throw new Error('No route found')

    return {
      type: 'Feature',
      geometry: data.routes[0].geometry,
      properties: {
        distance: data.routes[0].distance,
        duration: data.routes[0].duration,
      },
    }
  } catch (e) {
    console.warn('Mapbox Directions failed, using fallback:', e.message)
    return straightLine(origin, destination, waypoint)
  }
}
