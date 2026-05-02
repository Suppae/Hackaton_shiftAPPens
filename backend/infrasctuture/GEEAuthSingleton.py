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

        creds_json = os.environ.get("GEE_API_KEY")

        credentials = ''

        if creds_json:
            credentials = service_account.Credentials.from_service_account_info(
                json.loads(creds_json),
                scopes=["https://www.googleapis.com/auth/earthengine"]
            )

        self.credentials = credentials

        ee.Initialize(credentials=credentials)
        self._initialized = True

        return credentials
