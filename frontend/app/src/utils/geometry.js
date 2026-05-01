import booleanIntersects from '@turf/boolean-intersects'

export function routeIntersectsFire(routeGeometry, fireFeature) {
  if (!routeGeometry || !fireFeature) return false
  try {
    return booleanIntersects(
      { type: 'Feature', geometry: routeGeometry },
      fireFeature
    )
  } catch {
    return false
  }
}

export function polygonCentroid(fireFeature) {
  const coords = fireFeature.geometry.coordinates[0]
  const cx = coords.reduce((s, c) => s + c[0], 0) / coords.length
  const cy = coords.reduce((s, c) => s + c[1], 0) / coords.length
  return [cx, cy]
}
