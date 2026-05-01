import mockData from './mockData.json'

const BASE = 'http://localhost:8000'

export async function fetchDemo() {
  try {
    const res = await fetch(`${BASE}/simulate/demo`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } catch (e) {
    console.warn('Backend unavailable, using mock data:', e.message)
    return mockData
  }
}

export async function fetchSimulation(params) {
  try {
    const res = await fetch(`${BASE}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return await res.json()
  } catch (e) {
    console.warn('Backend unavailable, using mock data:', e.message)
    // Return mock data adjusted to the requested ignition point
    return {
      ...mockData,
      ignition: [params.ignition_lon, params.ignition_lat],
      metadata: {
        ...mockData.metadata,
        wind_speed_ms: params.wind_speed_ms ?? mockData.metadata.wind_speed_ms,
        wind_direction_deg: params.wind_direction_deg ?? mockData.metadata.wind_direction_deg,
        humidity_pct: params.humidity_pct ?? mockData.metadata.humidity_pct,
      },
    }
  }
}
