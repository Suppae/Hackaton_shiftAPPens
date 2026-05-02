# infrasctuture/IFireDetectionProvider.py
from abc import ABC, abstractmethod

class IFireDetectionProvider(ABC):

    @abstractmethod
    def get_active_fires(self, polygon: list, hours_back: int = 24) -> dict:
        """Retorna ignições ativas com FRP e coordenadas."""
        pass

    @abstractmethod
    def get_fire_extent(self, polygon: list, date_str: str) -> dict:
        """Retorna área estimada do fogo numa data."""
        pass