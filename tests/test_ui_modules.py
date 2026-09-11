import sys
import os
import unittest
import pandas as pd
import plotly.graph_objects as go

# Add root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.ui.exporters import export_to_csv, export_to_excel
from src.ui.charts import (
    create_temporal_chart,
    create_typology_chart,
)


class TestUIExporters(unittest.TestCase):
    """Pruebas unitarias para los exportadores CSV y Excel."""

    def test_export_to_csv(self):
        df = pd.DataFrame({"col1": [1, 2], "col2": ["A", "B"]})
        csv_bytes = export_to_csv(df)
        self.assertTrue(len(csv_bytes) > 0)
        self.assertIn(b"col1,col2", csv_bytes)

    def test_export_to_csv_empty(self):
        csv_bytes = export_to_csv(pd.DataFrame())
        self.assertEqual(csv_bytes, b"")

    def test_export_to_excel(self):
        df = pd.DataFrame({"Control": ["C1", "C2"], "Porcentaje": [10.5, 20.0]})
        excel_bytes = export_to_excel(df, sheet_name="Reporte")
        self.assertTrue(len(excel_bytes) > 0)
        # Excel zip signature (PK..)
        self.assertTrue(excel_bytes.startswith(b"PK"))

    def test_export_to_excel_empty(self):
        excel_bytes = export_to_excel(pd.DataFrame())
        self.assertEqual(excel_bytes, b"")


class TestUICharts(unittest.TestCase):
    """Pruebas unitarias para los generadores de gráficos Plotly."""

    def setUp(self):
        self.sample_df = pd.DataFrame({
            "Semestre": ["Primer Semestre 2025", "Primer Semestre 2025", "Primer Semestre 2026"],
            "entrevista": [1, 0, 0],
            "encuestador": ["V100", "V100", "V200"],
            "estatusentrevista": ["TE", "OA", "DE"],
            "tipologia_vivienda": ["TIPO E", "TIPO A", "TIPO C"],
        })

    def test_create_temporal_chart(self):
        fig = create_temporal_chart(self.sample_df)
        self.assertIsInstance(fig, go.Figure)
        self.assertTrue(len(fig.data) > 0)

    def test_create_temporal_chart_empty(self):
        fig = create_temporal_chart(pd.DataFrame())
        self.assertIsInstance(fig, go.Figure)

    def test_create_typology_chart(self):
        counts = self.sample_df["tipologia_vivienda"].value_counts().reset_index()
        counts.columns = ["Tipología", "Cantidad"]
        fig = create_typology_chart(counts)
        self.assertIsInstance(fig, go.Figure)
        self.assertTrue(len(fig.data) > 0)


if __name__ == "__main__":
    unittest.main()
