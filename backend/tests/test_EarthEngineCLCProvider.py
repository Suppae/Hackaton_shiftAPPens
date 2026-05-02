import unittest
from unittest.mock import patch
import numpy as np

from infrasctuture.fuel.EarthEngineCLCProvider import EarthEngineCLCProvider


class TestEarthEngineCLCProvider(unittest.TestCase):
    json_credentials = '/home/junkeira/hackaton/hackathon_sh1fthappens/backend/infrasctuture/fuel/civil-glyph-495022-k3-689473ae18be.json'

    def setUp(self):
        # Patch do ee.Initialize para não tentar conectar ao Google durante o init
        with patch('ee.Initialize'):
            self.provider = EarthEngineCLCProvider(self.json_credentials)

    def test_polygon_key_consistency(self):
        """Garante que o mesmo polígono gera a mesma chave de cache."""
        poly = [[0, 0], [1, 1], [1, 0], [0, 0]]
        key1 = self.provider._polygon_key(poly)
        key2 = self.provider._polygon_key(poly)
        self.assertEqual(key1, key2)

    @patch.object(EarthEngineCLCProvider, '_extract_multi_band')
    def test_fetch_from_ee_logic(self, mock_extract):
        """Testa se o processamento Numpy (normalização/map) está correto."""

        # Configuramos um retorno falso que simula o que o GEE enviaria
        mock_extract.return_value = {
            "landcover": np.array([[311, 512]]),  # Floresta e Água
            "NDVI": np.array([[5000, 10000]]),  # 0.5 e 1.0 após normalização
            "NDMI_proxy": np.array([[2000, 0]]),  # 0.2 e 0.0
            "Lai": np.array([[12, 5]])  # 12 deve virar 10 após o clip
        }

        poly = [[0, 0], [1, 1], [1, 0], [0, 0]]
        result = self.provider.get_fuel_grid(poly)

        # Verificação do Fuel Map (311 -> 1.3, 512 -> 0.0)
        np.testing.assert_array_equal(result['fuel'], [1.3, 0.0])

        # Verificação do NDVI (5000 / 10000 = 0.5)
        self.assertEqual(result['ndvi'][0, 0], 0.5)

        # Verificação do Clip do LAI (máximo 10)
        self.assertEqual(result['lai'][0, 0], 10)

    def test_cache_mechanism(self):
        """Verifica se o cache evita chamadas repetidas ao fetch."""
        poly = [[0, 0], [1, 1], [1, 0], [0, 0]]
        self.provider.cache = {"some_hash": {"data": "cached"}}

        with patch.object(self.provider, '_polygon_key', return_value="some_hash"):
            # Este método não deve disparar o _fetch_from_ee porque a chave já existe
            with patch.object(self.provider, '_fetch_from_ee') as mock_fetch:
                result = self.provider.get_fuel_grid(poly)
                mock_fetch.assert_not_called()
                self.assertEqual(result["data"], "cached")

    def test_run(self):
        test_poly = [
            [-8.64, 40.15],
            [-8.60, 40.15],
            [-8.60, 40.18],
            [-8.64, 40.18],
            [-8.64, 40.15]
        ]

        try:
            print("--- A inicializar Google Earth Engine ---")

            print("--- A instanciar o Provider ---")
            provider = EarthEngineCLCProvider(self.json_credentials)

            print("--- A efetuar chamada única (Single Fetch) ao GEE ---")
            layers = provider.get_fuel_grid(test_poly)

            print("\n✅ Sucesso! Resultados obtidos:")
            for name, data in layers.items():
                print(f"Layer: {name:8} | Formato: {data.shape} | Médio: {np.mean(data):.4f}")

        except Exception as e:
            print(f"\n❌ Erro durante o teste: {e}")

if __name__ == '__main__':
    unittest.main()