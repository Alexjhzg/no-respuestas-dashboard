import sys
import os
import unittest
import pandas as pd
import numpy as np

# Ensure root dir is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.data_processor import (
    get_kpis,
    extract_control_series,
    get_control_no_response_report,
)
from src.no_respuesta_classifier import (
    classify_housing_state,
    apply_housing_classification_df,
)
from src.config import STATUS_MAPPING


class TestDashboardKPIs(unittest.TestCase):
    """Pruebas TDD para la función get_kpis."""

    def test_get_kpis_empty_dataframe(self):
        df_empty = pd.DataFrame()
        kpis = get_kpis(df_empty)
        self.assertEqual(kpis["controles_evaluados"], 0)
        self.assertEqual(kpis["porcentaje_no_respuesta"], 0)
        self.assertEqual(kpis["no_respuestas"], 0)

    def test_get_kpis_100_percent_effective(self):
        df = pd.DataFrame({
            "entrevista": [1, 1, 1, 1],
            "control": ["C001", "C002", "C003", "C004"]
        })
        kpis = get_kpis(df)
        self.assertEqual(kpis["no_respuestas"], 0)
        self.assertEqual(kpis["controles_evaluados"], 4)
        self.assertEqual(kpis["porcentaje_no_respuesta"], 0.0)

    def test_get_kpis_100_percent_no_response(self):
        df = pd.DataFrame({
            "entrevista": [0, 0, 0],
            "control": ["C001", "C001", "C002"]
        })
        kpis = get_kpis(df)
        self.assertEqual(kpis["no_respuestas"], 3)
        self.assertEqual(kpis["controles_evaluados"], 2)
        self.assertEqual(kpis["porcentaje_no_respuesta"], 100.0)

    def test_get_kpis_mixed(self):
        df = pd.DataFrame({
            "entrevista": [1, 0, 0, 1, 0],
            "control": ["C001", "C001", "C002", "C003", "SIN_CONTROL"]
        })
        kpis = get_kpis(df)
        self.assertEqual(kpis["no_respuestas"], 3)
        # "SIN_CONTROL" must be excluded from distinct controls count
        self.assertEqual(kpis["controles_evaluados"], 3)
        self.assertAlmostEqual(kpis["porcentaje_no_respuesta"], 60.0, places=2)

    def test_get_kpis_invalid_controls_filtered(self):
        df = pd.DataFrame({
            "entrevista": [1, 0, 0, 1],
            "control": ["nan", "None", "", "C001"]
        })
        kpis = get_kpis(df)
        self.assertEqual(kpis["controles_evaluados"], 1)


class TestExtractControlSeries(unittest.TestCase):
    """Pruebas TDD para la unificación de códigos de control."""

    def test_extract_control_series_priority(self):
        df = pd.DataFrame({
            "control": ["CTRL_MAIN", None, None, None],
            "v4_control": ["CTRL_V4_ALT", "CTRL_V4", None, None],
            "datos_mm111/control": [None, None, "CTRL_MM111", None],
            "group_sh53u78/control": [None, None, None, "CTRL_GROUP"],
        })
        res = extract_control_series(df)
        self.assertEqual(res.tolist(), ["CTRL_MAIN", "CTRL_V4", "CTRL_MM111", "CTRL_GROUP"])

    def test_extract_control_series_empty_df(self):
        df = pd.DataFrame()
        res = extract_control_series(df)
        self.assertTrue(res.empty)

    def test_extract_control_series_trim_and_fallback(self):
        df = pd.DataFrame({
            "control": ["  CTRL_SPACES  ", None]
        })
        res = extract_control_series(df)
        self.assertEqual(res.tolist(), ["CTRL_SPACES", "SIN_CONTROL"])

    def test_extract_control_series_remapping(self):
        df = pd.DataFrame({
            "control": ["06160010", "16060037"]
        })
        res = extract_control_series(df)
        self.assertEqual(res.tolist(), ["16060037", "16060037"])


class TestControlNoResponseReport(unittest.TestCase):
    """Pruebas TDD para la generación del reporte por control y semestre."""

    def test_report_empty_df(self):
        report = get_control_no_response_report(pd.DataFrame())
        self.assertTrue(report.empty)

    def test_report_calculation_and_sorting(self):
        df = pd.DataFrame({
            "control": ["C1", "C1", "C1", "C2", "C2"],
            "Semestre": ["Primer Semestre 2025", "Primer Semestre 2025", "Primer Semestre 2025", "Primer Semestre 2025", "Primer Semestre 2025"],
            "entrevista": [1, 0, 0, 1, 1], # C1: 2/3 no resp (66.67%), C2: 0/2 no resp (0.0%)
        })
        report = get_control_no_response_report(df)

        self.assertEqual(list(report.columns), ["Control", "Semestre", "Total Registros", "No Diligenciadas", "% No Respuesta"])
        self.assertEqual(len(report), 2)
        
        # Check top row (sorted descending by % No Respuesta)
        top_row = report.iloc[0]
        self.assertEqual(top_row["Control"], "C1")
        self.assertEqual(top_row["Total Registros"], 3)
        self.assertEqual(top_row["No Diligenciadas"], 2)
        self.assertEqual(top_row["% No Respuesta"], 66.67)

        bottom_row = report.iloc[1]
        self.assertEqual(bottom_row["Control"], "C2")
        self.assertEqual(bottom_row["Total Registros"], 2)
        self.assertEqual(bottom_row["No Diligenciadas"], 0)
        self.assertEqual(bottom_row["% No Respuesta"], 0.0)

    def test_report_fallback_es_efectiva(self):
        # When 'entrevista' column is missing, verify fallback to 'es_efectiva'
        df = pd.DataFrame({
            "control": ["C1", "C1"],
            "Semestre": ["Primer Semestre 2026", "Primer Semestre 2026"],
            "es_efectiva": [True, False],
        })
        report = get_control_no_response_report(df)
        self.assertEqual(report.iloc[0]["No Diligenciadas"], 1)
        self.assertEqual(report.iloc[0]["Total Registros"], 2)
        self.assertEqual(report.iloc[0]["% No Respuesta"], 50.0)


class TestHousingTypologyAggregations(unittest.TestCase):
    """Pruebas TDD para clasificaciones y agregados de tipología de vivienda."""

    def test_housing_classification_distribution(self):
        df = pd.DataFrame({
            "estatusentrevista": ["TE", "OA", "DE", "VO", "UNKNOWN"],
            "entrevista": [1, 0, 0, 0, 0]
        })
        classified = apply_housing_classification_df(df)
        
        counts = classified["tipologia_vivienda"].value_counts().to_dict()
        self.assertEqual(counts.get("TIPO E"), 1)
        self.assertEqual(counts.get("TIPO A"), 1)
        self.assertEqual(counts.get("TIPO C"), 1)
        self.assertEqual(counts.get("TIPO B"), 1)
        self.assertEqual(counts.get("NO DEFINIDO"), 1)

    def test_effective_vs_no_response_flags(self):
        df = pd.DataFrame({
            "estatusentrevista": ["TE", "OA"],
            "entrevista": [1, 0]
        })
        classified = apply_housing_classification_df(df)
        self.assertTrue(classified.iloc[0]["es_efectiva"])
        self.assertFalse(classified.iloc[1]["es_efectiva"])


class TestEnumeratorAndStatusBreakdown(unittest.TestCase):
    """Pruebas TDD para desgloses por encuestador y motivos de no respuesta."""

    def test_enumerator_group_totals(self):
        df = pd.DataFrame({
            "encuestador": ["ANA", "ANA", "PEDRO", "PEDRO", "PEDRO"],
            "entrevista": [1, 0, 1, 1, 0]
        })
        df["Estatus_Resumen"] = df["entrevista"].map({1: "Diligenciadas", 0: "No Diligenciadas"}).fillna("No Diligenciadas")
        grouped = df.groupby(["encuestador", "Estatus_Resumen"]).size().reset_index(name="Cantidad")

        ana_efectiva = grouped[(grouped["encuestador"] == "ANA") & (grouped["Estatus_Resumen"] == "Diligenciadas")]["Cantidad"].values[0]
        ana_no_resp = grouped[(grouped["encuestador"] == "ANA") & (grouped["Estatus_Resumen"] == "No Diligenciadas")]["Cantidad"].values[0]
        pedro_efectiva = grouped[(grouped["encuestador"] == "PEDRO") & (grouped["Estatus_Resumen"] == "Diligenciadas")]["Cantidad"].values[0]
        pedro_no_resp = grouped[(grouped["encuestador"] == "PEDRO") & (grouped["Estatus_Resumen"] == "No Diligenciadas")]["Cantidad"].values[0]

        self.assertEqual(ana_efectiva, 1)
        self.assertEqual(ana_no_resp, 1)
        self.assertEqual(pedro_efectiva, 2)
        self.assertEqual(pedro_no_resp, 1)

    def test_status_mapping_and_totals(self):
        df = pd.DataFrame({
            "entrevista": [0, 0, 0, 1],
            "estatusentrevista": ["OA", "RZ", "UNKNOWN", "TE"]
        })
        df_no_resp = df[df["entrevista"] == 0].copy()
        df_no_resp["estatusentrevista"] = df_no_resp["estatusentrevista"].apply(
            lambda x: f"{x} - {STATUS_MAPPING[x]}" if x in STATUS_MAPPING else str(x)
        )

        total_no_resp = df_no_resp.shape[0]
        self.assertEqual(total_no_resp, 3)

        status_list = df_no_resp["estatusentrevista"].tolist()
        self.assertIn("OA - Ocupantes Ausentes", status_list)
        self.assertIn("RZ - Rechazada", status_list)
        self.assertIn("UNKNOWN", status_list)


class TestGlobalFilterIntegrity(unittest.TestCase):
    """Pruebas TDD para verificar la integridad de totales tras aplicar filtros."""

    def test_filter_subset_totals(self):
        df = pd.DataFrame({
            "Semestre": ["Primer Semestre 2025", "Primer Semestre 2025", "Segundo Semestre 2025"],
            "nodo": ["Nodo 1", "Nodo 2", "Nodo 1"],
            "municipio": ["Mun A", "Mun B", "Mun A"],
            "entrevista": [1, 0, 1],
            "control": ["C1", "C2", "C3"]
        })

        total_initial = len(df)
        
        # Apply filter by Semester
        filtered_sem = df[df["Semestre"] == "Primer Semestre 2025"]
        self.assertEqual(len(filtered_sem), 2)
        kpis_sem = get_kpis(filtered_sem)
        self.assertEqual(kpis_sem["controles_evaluados"], 2)
        self.assertEqual(kpis_sem["no_respuestas"], 1)

        # Apply filter by Node
        filtered_nodo = df[df["nodo"] == "Nodo 1"]
        self.assertEqual(len(filtered_nodo), 2)
        kpis_nodo = get_kpis(filtered_nodo)
        self.assertEqual(kpis_nodo["no_respuestas"], 0)


if __name__ == "__main__":
    unittest.main()
