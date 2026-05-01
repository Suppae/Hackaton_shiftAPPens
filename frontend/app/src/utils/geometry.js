function pointInPolygon(point, ring) {
  const [x, y] = point
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) {
      inside = !inside
    }
  }
  return inside
}

export function routeIntersectsFire(routeFeature, fireFeature) {
  if (!routeFeature || !fireFeature) return false
  const routeCoords = routeFeature.geometry.coordinates
  const fireRing = fireFeature.geometry.coordinates[0]
  return routeCoords.some(pt => pointInPolygon(pt, fireRing))
}

export function polygonCentroid(fireFeature) {
  const coords = fireFeature.geometry.coordinates[0]
  const cx = coords.reduce((s, c) => s + c[0], 0) / coords.length
  const cy = coords.reduce((s, c) => s + c[1], 0) / coords.length
  return [cx, cy]
}

export function computeDetourWaypoint(origin, destination, fireCentroid) {
  const mx = (origin[0] + destination[0]) / 2
  const my = (origin[1] + destination[1]) / 2

  const routeDx = destination[0] - origin[0]
  const routeDy = destination[1] - origin[1]
  const len = Math.sqrt(routeDx * routeDx + routeDy * routeDy) || 0.01

  const perpDx = -routeDy / len
  const perpDy = routeDx / len

  const toFireDx = fireCentroid[0] - mx
  const toFireDy = fireCentroid[1] - my
  const dot = toFireDx * perpDx + toFireDy * perpDy
  const sign = dot > 0 ? -1 : 1

  return [mx + sign * perpDx * 0.06, my + sign * perpDy * 0.06]
}
