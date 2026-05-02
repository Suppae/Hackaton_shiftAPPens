import ee
from datetime import datetime, timedelta

from infrasctuture.fire_recognition.IFireDetectionProvider import IFireDetectionProvider
from infrasctuture.GEEAuthSingleton import GEEAuthSingleton


class VIIRSFireDetectionProvider(IFireDetectionProvider):

    def get_active_fires(
        self,
        polygon: list,
        hours_back: int = 24,
        datetime_object_di: datetime = None,
    ) -> dict:
        """
        Returns active ignition points with FRP and confidence.
        hours_back: temporal window — 24h realtime, 72h for MVP demo.
        """
        if datetime_object_di is None:
            datetime_object_di = datetime.utcnow()

        GEEAuthSingleton().initialize()
        region = ee.Geometry.Polygon([polygon])
        start = datetime_object_di - timedelta(hours=hours_back)

        fire_collection = (
            ee.ImageCollection("NOAA/VIIRS/001/VNP14IMGT")
            .filterDate(
                start.strftime("%Y-%m-%dT%H:%M:%S"),
                datetime_object_di.strftime("%Y-%m-%dT%H:%M:%S"),
            )
            .filterBounds(region)
        )

        def mask_fires(img):
            qa = img.select("QF")
            fire_mask = qa.eq(7).Or(qa.eq(8)).Or(qa.eq(9))
            return img.updateMask(fire_mask)

        masked = fire_collection.map(mask_fires)
        frp_image = masked.select("FRP").max()

        try:
            result = frp_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=375,
                maxPixels=1e8,
            ).getInfo()

            fire_pixels = self._extract_fire_points(masked, region)

            return {
                "mean_frp": result.get("FRP"),
                "fire_points": fire_pixels,
                "hours_back": hours_back,
                "timestamp": datetime_object_di.isoformat(),
            }

        except ee.EEException as e:
            raise RuntimeError(f"VIIRS fetch failed: {e}") from e

    def _extract_fire_points(self, collection, region) -> list:
        """Extract individual ignition points with coordinates for Mapbox GeoJSON."""
        frp_img = collection.select("FRP").max()
        qa_img = collection.select("QF").max()
        combined = ee.Image.cat([frp_img, qa_img])

        try:
            points = combined.sample(
                region=region,
                scale=375,
                geometries=True,
            ).getInfo()
        except ee.EEException:
            return []

        result = []
        for feature in points.get("features", []):
            props = feature.get("properties", {})
            coords = feature["geometry"]["coordinates"]
            frp = props.get("FRP")
            if frp and frp > 0:
                result.append({
                    "lon": coords[0],
                    "lat": coords[1],
                    "frp_mw": round(frp, 2),
                    "confidence": self._qa_to_confidence(props.get("QF", 0)),
                })

        return result

    def _qa_to_confidence(self, qa_value: int) -> str:
        return {7: "high", 8: "medium", 9: "low"}.get(qa_value, "unknown")

    def get_fire_extent(self, polygon: list, date_str: str) -> dict:
        """Estimates burned area using VIIRS I4 band (SWIR 3.7µm)."""
        GEEAuthSingleton().initialize()
        region = ee.Geometry.Polygon([polygon])

        end = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")

        surface = (
            ee.ImageCollection("NOAA/VIIRS/001/VNP09GA")
            .filterDate(date_str, end)
            .filterBounds(region)
            .median()
        )

        fire_mask = surface.select("I4").gt(0.5)

        fire_area_result = fire_mask.multiply(ee.Image.pixelArea()).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=region,
            scale=375,
            maxPixels=1e8,
        ).getInfo()

        area_m2 = fire_area_result.get("I4", 0) or 0

        return {
            "area_m2": area_m2,
            "area_ha": round(area_m2 / 10_000, 2),
            "area_km2": round(area_m2 / 1_000_000, 4),
            "date": date_str,
        }

    @staticmethod
    def to_geojson(fire_result: dict) -> dict:
        return {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
                    "properties": {"frp_mw": p["frp_mw"], "confidence": p["confidence"]},
                }
                for p in fire_result.get("fire_points", [])
            ],
        }
