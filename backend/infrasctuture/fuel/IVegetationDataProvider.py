from abc import ABC, abstractmethod
import numpy as np

class IVegetationDataProvider(ABC):
    """
    Interface abstrata (Protected Variation)
    O simulador NUNCA sabe de onde vêm os dados.
    """

    @abstractmethod
    def get_fuel_grid(self, bbox):
        """
        Returns:
            np.ndarray: grid de combustível normalizado
        """
        pass