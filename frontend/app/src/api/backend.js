import mockData from './mockData.json'

const BASE = 'http://localhost:8000'

const MOCK_ACTIVE_FIRES = {
  source: 'mock_fallback',
  type: 'FeatureCollection',
  features: [
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [-8.4750, 40.8330] },
      properties: { id: 'mock1', town: 'Oliveira de Azeméis', status: 'Em Curso', man: 150, terrain: 'Floresta' },
    },
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [-7.6167, 40.3217] },
      properties: { id: 'mock2', town: 'Serra da Estrela', status: 'Em Curso', man: 85, terrain: 'Serra' },
    },
    {
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [-8.5530, 37.3140] },
      properties: { id: 'mock3', town: 'Monchique', status: 'Em Curso', man: 45, terrain: 'Mato' },
    },
  ],
}

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
    return {
      ...mockData,
      ignition: [params.ignition_lon, params.ignition_lat],
      vectors: {
        primary_spread_angle: (mockData.metadata.wind_direction_deg + 180) % 360,
        wind_angle: mockData.metadata.wind_direction_deg,
        speed_m_per_min: Math.max(1.0, (params.wind_speed_ms ?? mockData.metadata.wind_speed_ms) * 0.03 * 60),
      },
      environmental_data: {
        temperature_c: 35.0,
        humidity_pct: params.humidity_pct ?? mockData.metadata.humidity_pct,
        wind_speed_kmh: (params.wind_speed_ms ?? mockData.metadata.wind_speed_ms) * 3.6,
        fuel_load_mean: 0.42,
        ndvi_mean: 0.5,
      },
      metadata: {
        ...mockData.metadata,
        wind_speed_ms: params.wind_speed_ms ?? mockData.metadata.wind_speed_ms,
        wind_direction_deg: params.wind_direction_deg ?? mockData.metadata.wind_direction_deg,
        humidity_pct: params.humidity_pct ?? mockData.metadata.humidity_pct,
      },
      source: params.source || 'manual',
      timesteps: mockData.timesteps,
    }
  }
}

export async function fetchActiveFires(hours_back = 24) {
  try {
    const res = await fetch(`${BASE}/active-fires?hours_back=${hours_back}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    return data
  } catch (e) {
    console.warn('Active fires fetch failed, using fallback:', e.message)
    return MOCK_ACTIVE_FIRES
  }
}
