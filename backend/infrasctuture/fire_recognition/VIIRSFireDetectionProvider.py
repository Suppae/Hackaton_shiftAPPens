import ee
import numpy as np
from datetime import datetime, timedelta
from IFireDetectionProvider import IFireDetectionProvider
from infrasctuture.GEEAuthSingleton import GEEAuthSingleton


class VIIRSFireDetectionProvider(IFireDetectionProvider):

    def __init__(self):
        self.credentials = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Deteção de ignições ativas (últimas N horas)
    # ------------------------------------------------------------------

    def get_active_fires(self, polygon: list, hours_back: int = 24, datetime_object_di: datetime = datetime.now()) -> dict:
        """
        Retorna pontos de ignição ativos com FRP e confiança.

        hours_back: janela temporal — 24h para realtime, 72h para MVP demo
        """
        self.credentials = GEEAuthSingleton().initialize()
        region = ee.Geometry.Polygon([polygon])

        start = datetime_object_di - timedelta(hours=hours_back)

        fire_collection = (
            ee.ImageCollection("NOAA/VIIRS/001/VNP14IMGT")
            .filterDate(start.strftime("%Y-%m-%dT%H:%M:%S"),
                        datetime_object_di.strftime("%Y-%m-%dT%H:%M:%S"))
            .filterBounds(region)
        )

        # Máscara: só pixels com fogo confirmado ou provável
        # QA values: 7=fire high confidence, 8=fire medium, 9=fire low
        def mask_fires(img):
            qa = img.select("QF")
            fire_mask = qa.eq(7).Or(qa.eq(8)).Or(qa.eq(9))
            return img.updateMask(fire_mask)

        masked = fire_collection.map(mask_fires)

        # FRP máximo no período (pico de intensidade)
        frp_image = masked.select("FRP").max()

        try:
            result = frp_image.reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=375,  # resolução nativa VIIRS
                maxPixels=1e8
            ).getInfo()

            fire_pixels = self._extract_fire_points(masked, region)

            return {
                "mean_frp": result.get("FRP"),  # Fire Radiative Power médio (MW)
                "fire_points": fire_pixels,  # lista de {lat, lon, frp, confidence}
                "hours_back": hours_back,
                "timestamp": datetime_object_di.isoformat()
            }

        except ee.EEException as e:
            raise RuntimeError(f"VIIRS fetch failed: {e}") from e

    def _extract_fire_points(self, collection, region) -> list:
        """
        Extrai pontos individuais de ignição com coordenadas.
        Útil para passar ao Mapbox como GeoJSON.
        """
        frp_img = collection.select("FRP").max()
        qa_img = collection.select("QF").max()

        combined = ee.Image.cat([frp_img, qa_img])

        try:
            points = combined.sample(
                region=region,
                scale=375,
                geometries=True
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
                    "confidence": self._qa_to_confidence(props.get("QF", 0))
                })

        return result

    def _qa_to_confidence(self, qa_value: int) -> str:
        return {7: "high", 8: "medium", 9: "low"}.get(qa_value, "unknown")

    # ------------------------------------------------------------------
    # Estimativa de dimensão do fogo (área e perímetro)
    # ------------------------------------------------------------------

    def get_fire_extent(self, polygon: list, date_str: str) -> dict:
        """
        Estima a área ardida usando a banda termal I5 do VNP09GA.
        date_str: "YYYY-MM-DD" — data do fogo

        Usa threshold de brightness temperature para delimitar a chama.
        """
        self._ensure_initialized()
        region = ee.Geometry.Polygon([polygon])

        start = date_str
        end = (datetime.strptime(date_str, "%Y-%m-%d")
               + timedelta(days=1)).strftime("%Y-%m-%d")

        surface = (
            ee.ImageCollection("NOAA/VIIRS/001/VNP09GA")
            .filterDate(start, end)
            .filterBounds(region)
            .median()
        )

        # I4 (SWIR 3.7µm) — sensível a chamas ativas
        # I5 (TIR 11µm)   — sensível a área ardida e brasa
        i4 = surface.select("I4")
        i5 = surface.select("I5")

        # Threshold empírico: pixeis com I4 > 0.5 são chama ativa
        # Ajusta conforme os teus dados de validação
        fire_mask = i4.gt(0.5)

        fire_area_result = fire_mask.multiply(
            ee.Image.pixelArea()  # área real em m² por pixel
        ).reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=region,
            scale=375,
            maxPixels=1e8
        ).getInfo()

        area_m2 = fire_area_result.get("I4", 0)

        try:
            return {
                "area_m2": area_m2,
                "area_ha": round(area_m2 / 10_000, 2),
                "area_km2": round(area_m2 / 1_000_000, 4),
                "date": date_str
            }
        except ee.EEException as e:
            raise RuntimeError(f"VIIRS extent failed: {e}") from e


        def to_geojson(fire_result: dict) -> dict:
            return {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [p["lon"], p["lat"]]
                        },
                        "properties": {
                            "frp_mw": p["frp_mw"],
                            "confidence": p["confidence"]
                        }
                    }
                    for p in fire_result["fire_points"]
                ]
            }