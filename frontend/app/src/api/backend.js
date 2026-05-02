const BASE = 'http://localhost:8000'

export async function fetchSimulation(params) {
  const res = await fetch(`${BASE}/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!res.ok) throw new Error(`fetchSimulation: HTTP ${res.status}`)
  return await res.json()
}

export async function fetchActiveFires(hours_back = 24) {
  const res = await fetch(`${BASE}/active-fires?hours_back=${hours_back}`)
  if (!res.ok) throw new Error(`fetchActiveFires: HTTP ${res.status}`)
  return await res.json()
}
