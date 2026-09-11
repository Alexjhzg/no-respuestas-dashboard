import sys
import os
import unittest
import tempfile
import time
import json
import pandas as pd

# Add root directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.data_processor import load_local_fallback_dataset


class TestParquetCache(unittest.TestCase):
    """Pruebas unitarias para el mecanismo de caché binario Parquet con validación mtime."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.json_path = os.path.join(self.temp_dir.name, "test_dataset.json")
        self.parquet_path = os.path.join(self.temp_dir.name, "test_dataset.parquet")

        # Create sample JSON dataset
        sample_data = {
            "records": [
                {
                    "control": "C001",
                    "estatusentrevista": "TE",
                    "entrevista": 1,
                    "_submission_time": "2025-04-10T10:00:00Z",
                },
                {
                    "control": "C002",
                    "estatusentrevista": "OA",
                    "entrevista": 0,
                    "_submission_time": "2025-09-15T12:00:00Z",
                },
            ]
        }
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(sample_data, f)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parquet_cache_creation_and_reading(self):
        # 1. First load: Parquet doesn't exist yet, must build and save Parquet
        self.assertFalse(os.path.exists(self.parquet_path))
        df_first = load_local_fallback_dataset(
            json_path=self.json_path, parquet_path=self.parquet_path
        )
        self.assertFalse(df_first.empty)
        self.assertTrue(os.path.exists(self.parquet_path))

        # 2. Second load: Parquet exists and is valid -> reads from Parquet
        df_second = load_local_fallback_dataset(
            json_path=self.json_path, parquet_path=self.parquet_path
        )
        self.assertEqual(len(df_first), len(df_second))

    def test_parquet_cache_invalidation_on_json_update(self):
        # Initial load to generate Parquet
        df_initial = load_local_fallback_dataset(
            json_path=self.json_path, parquet_path=self.parquet_path
        )
        self.assertEqual(len(df_initial), 2)

        # Wait briefly to ensure mtime timestamp difference
        time.sleep(0.1)

        # Update JSON dataset with a 3rd record
        updated_data = {
            "records": [
                {"control": "C001", "estatusentrevista": "TE", "entrevista": 1},
                {"control": "C002", "estatusentrevista": "OA", "entrevista": 0},
                {"control": "C003", "estatusentrevista": "DE", "entrevista": 0},
            ]
        }
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(updated_data, f)

        # Explicitly update JSON mtime to be in the future of parquet mtime
        future_mtime = os.path.getmtime(self.parquet_path) + 10.0
        os.utime(self.json_path, (future_mtime, future_mtime))

        # Re-run load: invalidation triggers, re-parses JSON and returns 3 rows
        df_invalidated = load_local_fallback_dataset(
            json_path=self.json_path, parquet_path=self.parquet_path
        )
        self.assertEqual(len(df_invalidated), 3)


if __name__ == "__main__":
    unittest.main()
