import numpy as np
import ee
from google.oauth2 import service_account
import hashlib
import json
import os
from datetime import datetime, timedelta

from infrasctuture.GEEAuthSingleton import GEEAuthSingleton
from infrasctuture.fuel.IVegetationDataProvider import IVegetationDataProvider

CACHE_DIR = "infrasctuture/fuel/.gee_cache"

class EarthEngineCLCProvider(IVegetationDataProvider):

    fuel_map = {
        # Urban / artificial
        111: 0.1,  # continuous urban fabric
        112: 0.15,  # discontinuous urban fabric
        121: 0.1,  # industrial/commercial
        122: 0.0,  # road/rail networks
        131: 0.0,  # mineral extraction
        141: 0.3,  # green urban areas
        142: 0.2,  # sport/leisure

        # Agriculture (lower fuel load)
        211: 0.4,  # non-irrigated arable land
        212: 0.2,  # permanently irrigated
        221: 0.5,  # vineyards
        222: 0.4,  # fruit trees
        231: 0.8,  # pastures
        242: 0.6,  # complex cultivation
        243: 0.7,  # agriculture + natural vegetation

        # Forest (high fuel) — critical for Portugal
        311: 1.3,  # broad-leaved forest
        312: 1.5,  # coniferous forest (eucalyptus/pine — most dangerous)
        313: 1.2,  # mixed forest
        321: 1.4,  # natural grassland
        322: 1.3,  # moors/heathland (mato — very common in PT fires)
        323: 1.1,  # sclerophyllous vegetation
        324: 1.2,  # transitional woodland/shrub (post-fire regrowth)

        # Water / bare (non-flammable)
        331: 0.0,  # beaches/dunes
        332: 0.0,  # bare rock
        511: 0.0,  # water courses
        512: 0.0,  # water bodies
        521: 0.0,  # coastal lagoons
    }

    def __init__(self):
        self.credentials = None
        self._initialized = False  # lazy init — GEE not called until first use
        self.cache = {}

    # ------------------------------------------------------------------
    # Core fetch
    # ------------------------------------------------------------------

    def _extract_multi_band(self, image, region, bands, scale=250):
        """Extracts multiple bands in a single server call."""
        img = image.select(bands).clip(region)        # FIX 2: removed broken URL syntax
        img = img.reproject(crs='EPSG:4326', scale=scale)
        data_dict = img.sampleRectangle(region).getInfo()

        return {band: np.array(data_dict["properties"][band]) for band in bands}

    def _get_seasonal_filter(self, month: int, window_days: int = 7, years_back: int = 5, datetimeObjectDI: datetime = None):
        """
        Returns an ee.Filter that captures the same seasonal window
        across multiple years — e.g., all images from July 15–Aug 15
        for the past 5 years.

        This is better than a single year because:
        - MODIS has cloud gaps — more years = more valid pixels
        - Averages out anomalous years (e.g., drought year vs wet year)
        - Still represents the correct seasonal fuel state
        """
        if datetimeObjectDI is None:
            datetimeObjectDI = datetime.now()
        current_year = datetimeObjectDI.year

        filters = []
        for year in range(current_year - years_back, current_year + 1):
            # Build start/end for this year's window
            center = datetime(year, month, datetimeObjectDI.day)
            start = (center - timedelta(days=window_days)).strftime("%Y-%m-%d")
            end = (center + timedelta(days=window_days)).strftime("%Y-%m-%d")
            filters.append(ee.Filter.date(start, end))

        # OR all the per-year windows together
        return ee.Filter.Or(*filters)


    def _fetch_from_ee(self, polygon, fire_month: int = 7):
        """
        fire_month: month of the simulated fire (1–12).
                    Defaults to July — peak fire season in Portugal.
        """
        region = ee.Geometry.Polygon([polygon])
        seasonal_filter = self._get_seasonal_filter(month=fire_month)

        self.clc_source = ee.Image("COPERNICUS/CORINE/V20/100m/2018")
        clc_img = self.clc_source.select(["landcover"])

        ndvi_img = (
            ee.ImageCollection("MODIS/061/MOD13A1")
            .filter(seasonal_filter)
            .median()
            .select(["NDVI"])
        )

        ndmi_img = (
            ee.ImageCollection("MODIS/061/MOD09A1")
            .filter(seasonal_filter)
            .median()
            .normalizedDifference(["sur_refl_b02", "sur_refl_b06"])
            .rename("NDMI")
        )

        lai_img = (
            ee.ImageCollection("MODIS/061/MCD15A3H")
            .filter(seasonal_filter)
            .median()
            .select(["Lai"])
        )

        combined_image = ee.Image.cat([clc_img, ndvi_img, ndmi_img, lai_img])
        band_names = ["landcover", "NDVI", "NDMI", "Lai"]

        raw_data = self._extract_multi_band(combined_image, region, band_names)

        fuel = np.vectorize(
            lambda x: self.fuel_map.get(int(x), 0.2)
        )(raw_data["landcover"]).astype(float)

        ndvi = np.clip(raw_data["NDVI"] / 10000.0, 0, 1)
        ndmi = np.clip(raw_data["NDMI"], -1, 1)  # already [-1,1] from normalizedDifference
        lai = np.clip(raw_data["Lai"] * 0.1, 0, 10)  # apply MODIS scale factor

        return {"fuel": fuel, "ndvi": ndvi, "ndmi": ndmi, "lai": lai}


    # ------------------------------------------------------------------
    # Disk cache management
    # ------------------------------------------------------------------

    def _polygon_key(self, polygon, fire_month: int):
        rounded = [(round(x, 4), round(y, 4)) for x, y in polygon]
        key_str = f"month={fire_month}|{rounded}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _disk_cache_path(self, key: str) -> str:
        os.makedirs(CACHE_DIR, exist_ok=True)
        return os.path.join(CACHE_DIR, f"{key}.json")

    def _save_to_disk(self, key: str, layers: dict):
        path = self._disk_cache_path(key)
        serializable = {k: v.tolist() for k, v in layers.items()}
        with open(path, "w") as f:
            json.dump(serializable, f)

    def _load_from_disk(self, key: str) -> dict | None:
        path = self._disk_cache_path(key)
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            raw = json.load(f)
        return {k: np.array(v) for k, v in raw.items()}


    # ------------------------------------------------------------------
    # Public API  (satisfies IVegetationDataProvider + test expectations)
    # ------------------------------------------------------------------

    def get_fuel_grid(self, polygon, fire_month: int = 7):
        self.credentials = GEEAuthSingleton().initialize()

        key = self._polygon_key(polygon, fire_month)

        if key in self.cache:
            return self.cache[key]

        disk_data = self._load_from_disk(key)
        if disk_data is not None:
            self.cache[key] = disk_data
            return disk_data

        layers = self._fetch_from_ee(polygon, fire_month)
        self.cache[key] = layers
        self._save_to_disk(key, layers)
        return layers
