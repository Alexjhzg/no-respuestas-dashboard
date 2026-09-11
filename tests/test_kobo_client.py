import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.kobo_client import KoboAPIClient


class TestKoboAPIClient(unittest.TestCase):

    def test_get_assets_mocked(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "results": [
                {"uid": "aAsset123", "name": "Encuesta EHM 2025"},
                {"uid": "aAsset456", "name": "Encuesta ESCA 2025"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response) as mock_get:
            client = KoboAPIClient(
                base_url="https://test.kobo.org/api/v2", token="test_token"
            )
            assets = client.get_assets()

            self.assertEqual(len(assets), 2)
            self.assertEqual(assets[0]["uid"], "aAsset123")
            mock_get.assert_called_once_with(
                "https://test.kobo.org/api/v2/assets/?format=json",
                headers={"Authorization": "Token test_token", "Accept": "application/json"},
                timeout=30,
                verify=False,
            )

    def test_get_asset_data_pagination_mocked(self):
        page1_resp = MagicMock()
        page1_resp.json.return_value = {
            "count": 3,
            "next": "https://test.kobo.org/api/v2/assets/a123/data/?format=json&page_size=2&page=2",
            "results": [{"_id": 1, "nota": "TE"}, {"_id": 2, "nota": "OA"}],
        }
        page1_resp.raise_for_status = MagicMock()

        page2_resp = MagicMock()
        page2_resp.json.return_value = {
            "count": 3,
            "next": None,
            "results": [{"_id": 3, "nota": "DE"}],
        }
        page2_resp.raise_for_status = MagicMock()

        with patch("requests.get", side_effect=[page1_resp, page2_resp]) as mock_get:
            client = KoboAPIClient(
                base_url="https://test.kobo.org/api/v2", token="test_token"
            )
            records = client.get_asset_data("a123", page_size=2)

            self.assertEqual(len(records), 3)
            self.assertEqual(records[0]["_id"], 1)
            self.assertEqual(records[2]["_id"], 3)
            self.assertEqual(mock_get.call_count, 2)

    def test_fetch_and_process_kobo_dataframe_mocked(self):
        raw_records = [
            {
                "cedula_encuestador": "V100",
                "condicion_de_ocupacion": "ocupadaconocupantespresentes",
                "nota": "Totalmente Encuestada",
            },
            {
                "cedula_encuestador": "V200",
                "condicion_de_ocupacion": "ocupadasconocupantesausentes",
                "nota": "No Atiende",
            },
        ]

        with patch.object(
            KoboAPIClient, "get_asset_data", return_value=raw_records
        ):
            client = KoboAPIClient(
                base_url="https://test.kobo.org/api/v2", token="test_token"
            )
            df = client.fetch_and_process_kobo_dataframe("a999")

            self.assertFalse(df.empty)
            self.assertIn("tipologia_vivienda", df.columns)
            self.assertIn("encuestador", df.columns)
            self.assertEqual(list(df["tipologia_vivienda"]), ["TIPO E", "TIPO A"])


if __name__ == "__main__":
    unittest.main()

