import sys
import os
import unittest
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.catalog_builder import build_planned_controls_catalog
from src.data_processor import load_planned_controls_catalog, get_planned_vs_executed_report


class TestCatalogBuilder(unittest.TestCase):

    def test_build_planned_controls_catalog(self):
        df_cat = build_planned_controls_catalog()
        self.assertFalse(df_cat.empty)
        self.assertIn("control", df_cat.columns)
        self.assertIn("operativo", df_cat.columns)
        self.assertIn("viviendas_planificadas", df_cat.columns)
        self.assertGreater(len(df_cat), 0)

    def test_load_planned_controls_catalog(self):
        df_cat = load_planned_controls_catalog()
        self.assertFalse(df_cat.empty)
        self.assertTrue("control" in df_cat.columns)

    def test_get_planned_vs_executed_report(self):
        df_planned = pd.DataFrame([
            {
                "control": "16010001",
                "operativo": "EHM",
                "semana": 1,
                "municipio": "Maturín",
                "viviendas_planificadas": 10,
            },
            {
                "control": "16010002",
                "operativo": "ESCA",
                "semana": 1,
                "municipio": "Maturín",
                "viviendas_planificadas": 15,
            },
        ])

        # Actual data: 16010001 has 8 surveys (6 effective, 2 no response)
        df_actual = pd.DataFrame([
            {"control": "16010001", "entrevista": 1},
            {"control": "16010001", "entrevista": 1},
            {"control": "16010001", "entrevista": 1},
            {"control": "16010001", "entrevista": 1},
            {"control": "16010001", "entrevista": 1},
            {"control": "16010001", "entrevista": 1},
            {"control": "16010001", "entrevista": 0},
            {"control": "16010001", "entrevista": 0},
        ])

        report = get_planned_vs_executed_report(df_actual, df_planned)

        self.assertEqual(len(report), 2)
        row_c1 = report[report["Control"] == "1"].iloc[0]
        self.assertEqual(row_c1["Estatus"], "Levantado")
        self.assertEqual(row_c1["Viviendas Capturadas"], 8)
        self.assertEqual(row_c1["Diligenciadas"], 6)
        self.assertEqual(row_c1["No Diligenciadas"], 2)

        row_c2 = report[report["Control"] == "2"].iloc[0]
        self.assertEqual(row_c2["Estatus"], "Pendiente")
        self.assertEqual(row_c2["Viviendas Capturadas"], 0)


if __name__ == "__main__":
    unittest.main()
