import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.kobo_consolidator import infer_period_from_record, fetch_consolidated_kobo_dataset
from src.kobo_client import KoboAPIClient


class TestKoboConsolidator(unittest.TestCase):

    def test_infer_period_from_record(self):
        rec_2025_s1 = {"_submission_time": "2025-03-15T10:00:00Z"}
        p1 = infer_period_from_record(rec_2025_s1)
        self.assertEqual(p1["anio"], "2025")
        self.assertEqual(p1["Semestre"], "Primer Semestre 2025")

        rec_2025_s2 = {"today": "2025-09-20"}
        p2 = infer_period_from_record(rec_2025_s2)
        self.assertEqual(p2["anio"], "2025")
        self.assertEqual(p2["Semestre"], "Segundo Semestre 2025")

        rec_2026_s1 = {"start": "2026-02-10T08:00:00Z"}
        p3 = infer_period_from_record(rec_2026_s1)
        self.assertEqual(p3["anio"], "2026")
        self.assertEqual(p3["Semestre"], "Primer Semestre 2026")

    def test_fetch_consolidated_kobo_dataset_mocked(self):
        mock_client = MagicMock(spec=KoboAPIClient)
        mock_client.get_assets.return_value = [
            {"uid": "u1", "name": "EHM V1"},
            {"uid": "u2", "name": "ESCA V4"},
        ]

        rec_u1 = [
            {
                "cedula_encuestador": "V111",
                "condicion_de_ocupacion": "ocupadaconocupantespresentes",
                "nota": "Totalmente Encuestada",
                "_submission_time": "2025-05-01T12:00:00",
            }
        ]

        rec_u2 = [
            {
                "v4_encuestador": "V222",
                "v4_condicion_ocupacion": "ocupadasconocupantesausentes",
                "ubicacion_final/nota": "Ausente",
                "start": "2026-01-15T09:00:00",
            }
        ]

        def get_asset_data_side_effect(uid, **kwargs):
            if uid == "u1":
                return rec_u1
            elif uid == "u2":
                return rec_u2
            return []

        mock_client.get_asset_data.side_effect = get_asset_data_side_effect

        df_res = fetch_consolidated_kobo_dataset(mock_client, auto_detect_all=True)

        self.assertFalse(df_res.empty)
        self.assertEqual(len(df_res), 2)
        self.assertIn("Semestre", df_res.columns)
        self.assertIn("tipologia_vivienda", df_res.columns)

        semestres = list(df_res["Semestre"])
        self.assertIn("Primer Semestre 2025", semestres)
        self.assertIn("Primer Semestre 2026", semestres)

        tipologias = list(df_res["tipologia_vivienda"])
        self.assertEqual(tipologias, ["TIPO E", "TIPO A"])

    def test_fetch_ehm_and_esca_datasets_mocked(self):
        from src.kobo_consolidator import fetch_ehm_dataset, fetch_esca_dataset

        mock_client = MagicMock(spec=KoboAPIClient)
        mock_client.get_assets.return_value = [
            {"uid": "u1", "name": "EHM V1"},
            {"uid": "u2", "name": "ESCA V4"},
        ]

        rec_u1 = [{"Tipo_Encuesta": "EHM", "Familia_Encuesta": "EHM", "_submission_time": "2025-05-01"}]
        rec_u2 = [{"Tipo_Encuesta": "ESCA", "Familia_Encuesta": "ESCA", "start": "2026-01-15"}]

        mock_client.get_asset_data.side_effect = lambda uid: rec_u1 if uid == "u1" else rec_u2

        df_ehm = fetch_ehm_dataset(mock_client, auto_detect_all=True)
        self.assertEqual(len(df_ehm), 1)
        self.assertEqual(df_ehm["Familia_Encuesta"].iloc[0], "EHM")

        df_esca = fetch_esca_dataset(mock_client, auto_detect_all=True)
        self.assertEqual(len(df_esca), 1)
        self.assertEqual(df_esca["Familia_Encuesta"].iloc[0], "ESCA")


if __name__ == "__main__":
    unittest.main()

