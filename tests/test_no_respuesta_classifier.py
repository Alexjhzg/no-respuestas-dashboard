import sys
import os
import unittest
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.no_respuesta_classifier import (
    normalize_text,
    is_truthy_raw,
    upcast_record_to_v4,
    classify_housing_state,
    process_kobo_record,
    apply_housing_classification_df,
)


class TestNoRespuestaClassifier(unittest.TestCase):

    def test_normalize_text(self):
        self.assertEqual(normalize_text("Totalmente Encuestada!"), "totalmenteencuestada")
        self.assertEqual(normalize_text("Condición de Ocupación #1"), "condiciondeocupacion1")
        self.assertEqual(normalize_text("¿Rehusó entrevista?"), "rehusoentrevista")
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text(None), "")

    def test_is_truthy_raw(self):
        self.assertTrue(is_truthy_raw("Totalmente Encuestada"))
        self.assertTrue(is_truthy_raw("Si"))
        self.assertTrue(is_truthy_raw("1"))
        self.assertFalse(is_truthy_raw("No"))
        self.assertFalse(is_truthy_raw("no_1"))
        self.assertFalse(is_truthy_raw("0"))
        self.assertFalse(is_truthy_raw("false"))
        self.assertFalse(is_truthy_raw(""))
        self.assertFalse(is_truthy_raw(None))

    def test_upcast_record_to_v4(self):
        v1_payload = {
            "cedula_encuestador": "V12345678",
            "segmento": "SEG001",
            "control": "CTRL99",
            "condicion_de_ocupacion": "ocupadaconocupantespresentes",
            "situacion_vivienda": "ocupadaconocupantespresentes",
            "nota": "Totalmente Encuestada",
        }
        v4_from_v1 = upcast_record_to_v4(v1_payload)
        self.assertEqual(
            v4_from_v1["Condici_n_de_ocupaci_n/condicion_de_ocupacion"],
            "ocupadaconocupantespresentes",
        )
        self.assertEqual(
            v4_from_v1["Condici_n_de_ocupaci_n/situacion_vivienda"],
            "ocupadaconocupantespresentes",
        )
        self.assertEqual(v4_from_v1["ubicacion_final/nota"], "Totalmente Encuestada")

        v2_payload = {
            "S0/cedula_encuestador": "V87654321",
            "S1/segmento": "SEG002",
            "v4_condicion_ocupacion": "desocupada",
            "situacion": "demolida",
        }
        v4_from_v2 = upcast_record_to_v4(v2_payload)
        self.assertEqual(
            v4_from_v2["Condici_n_de_ocupaci_n/condicion_de_ocupacion"],
            "desocupada",
        )
        self.assertEqual(
            v4_from_v2["Condici_n_de_ocupaci_n/situacion_vivienda"],
            "demolida",
        )

    def test_classify_housing_state(self):
        self.assertEqual(
            classify_housing_state("totalmenteencuestada", "ocupadaconocupantespresentes"),
            "TIPO E",
        )
        self.assertEqual(classify_housing_state("TE"), "TIPO E")
        self.assertEqual(classify_housing_state("", "ocupadaconocupantespresentes"), "TIPO E")

        self.assertEqual(
            classify_housing_state("nadieenvivienda", "ocupadasconocupantesausentes"),
            "TIPO A",
        )
        self.assertEqual(classify_housing_state("rehusoentrevista"), "TIPO A")
        self.assertEqual(classify_housing_state("informantenocalificado"), "TIPO A")
        self.assertEqual(classify_housing_state("OA"), "TIPO A")
        self.assertEqual(classify_housing_state("RZ"), "TIPO A")

        self.assertEqual(classify_housing_state("usovacacional", "desocupada"), "TIPO B")
        self.assertEqual(classify_housing_state("construyendose"), "TIPO B")
        self.assertEqual(classify_housing_state("VO"), "TIPO B")

        self.assertEqual(classify_housing_state("demolida"), "TIPO C")
        self.assertEqual(classify_housing_state("negocioalmacenpermanente"), "TIPO C")
        self.assertEqual(classify_housing_state("DE"), "TIPO C")

        self.assertEqual(classify_housing_state("", ""), "NO DEFINIDO")

    def test_process_kobo_record(self):
        raw = {
            "condicion_de_ocupacion": "ocupadaconocupantespresentes",
            "nota": "Totalmente Encuestada",
        }
        processed = process_kobo_record(raw)
        self.assertTrue(processed["no_respuesta"])
        self.assertEqual(processed["tipologia_vivienda"], "TIPO E")
        self.assertTrue(processed["es_efectiva"])

    def test_apply_housing_classification_df(self):
        df = pd.DataFrame(
            [
                {"estatusentrevista": "TE", "entrevista": 1},
                {"estatusentrevista": "OA", "entrevista": 0},
                {"estatusentrevista": "DE", "entrevista": 0},
                {"estatusentrevista": "VO", "entrevista": 0},
            ]
        )

        df_res = apply_housing_classification_df(df)
        self.assertIn("tipologia_vivienda", df_res.columns)
        self.assertIn("es_efectiva", df_res.columns)
        self.assertEqual(
            list(df_res["tipologia_vivienda"]),
            ["TIPO E", "TIPO A", "TIPO C", "TIPO B"],
        )
        self.assertEqual(list(df_res["es_efectiva"]), [True, False, False, False])


if __name__ == "__main__":
    unittest.main()

