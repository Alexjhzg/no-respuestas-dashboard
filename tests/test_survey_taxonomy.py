import unittest
from src.survey_taxonomy import detect_survey_metadata, enrich_record_taxonomy


class TestSurveyTaxonomy(unittest.TestCase):

    def test_detect_ehm_ampliada_v3(self):
        asset_name = "EHM Ampliada V3_aZ6qCkgxXpzM6ZYeJRtWhF.json"
        fam, ver, var = detect_survey_metadata(asset_name)
        self.assertEqual(fam, "EHM")
        self.assertEqual(ver, "V3")
        self.assertEqual(var, "Ampliada")

    def test_detect_esca_v2(self):
        asset_name = "ENCUESTA ESCA V2_aXW6LTx4SQvfGWp6wCu2SK.json"
        fam, ver, var = detect_survey_metadata(asset_name)
        self.assertEqual(fam, "ESCA")
        self.assertEqual(ver, "V2")
        self.assertEqual(var, "Estándar")

    def test_detect_esca_ampliada_v4(self):
        asset_name = "ESCA  AMPLIADA V4_aeTBRbtCffTkU2sDuu6FKK.json"
        fam, ver, var = detect_survey_metadata(asset_name)
        self.assertEqual(fam, "ESCA")
        self.assertEqual(ver, "V4")
        self.assertEqual(var, "Ampliada")

    def test_enrich_record_taxonomy(self):
        raw_rec = {"control": "16040051", "group_sh53u78/control": "16040051"}
        enriched = enrich_record_taxonomy(raw_rec, asset_name="EHM AMPLIADA V4")
        self.assertEqual(enriched["Familia_Encuesta"], "EHM")
        self.assertEqual(enriched["Version_Encuesta"], "V4")
        self.assertEqual(enriched["Variante_Encuesta"], "Ampliada")
        self.assertEqual(enriched["Tipo_Encuesta"], "EHM")


if __name__ == "__main__":
    unittest.main()
