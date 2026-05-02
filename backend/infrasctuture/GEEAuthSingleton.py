import ee
import os
import json
from google.oauth2 import service_account


class GEEAuthSingleton:
    _instance = None
    _initialized = False
    credentials = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GEEAuthSingleton, cls).__new__(cls)
        return cls._instance

    def initialize(self):
        if self._initialized:
            return self.credentials

        raw = os.environ.get("GEE_API_KEY", "").strip()
        credentials = None

        if raw:
            # Accept either a file path or an inline JSON string
            if os.path.isfile(os.path.expanduser(raw)):
                path = os.path.expanduser(raw)
                with open(path, "r") as f:
                    info = json.load(f)
                print(f"[GEEAuthSingleton] Loaded service account from file: {path}")
            else:
                info = json.loads(raw)
                print("[GEEAuthSingleton] Loaded service account from inline JSON")

            credentials = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/earthengine"],
            )

        ee.Initialize(credentials=credentials)
        self.credentials = credentials
        self._initialized = True
        return credentials
