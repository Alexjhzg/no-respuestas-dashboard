import sys
import os
import unittest
import pandas as pd

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.data_processor import get_kpis


class TestGetKPIsLegacy(unittest.TestCase):
    """Prueba de regresión para la función get_kpis con datos sintéticos."""

    def test_get_kpis(self):
        data = {
            "entrevista": [1, 1, 0, 1, 0],
            "control": ["CTRL1", "CTRL1", "CTRL2", "CTRL3", "CTRL3"],
        }
        df = pd.DataFrame(data)

        kpis = get_kpis(df)

        self.assertEqual(kpis["no_respuestas"], 2)
        self.assertEqual(kpis["controles_evaluados"], 3)
        self.assertAlmostEqual(kpis["porcentaje_no_respuesta"], 40.0, places=2)


if __name__ == "__main__":
    unittest.main()

