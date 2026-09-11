"""
kobo_client.py
Cliente para la API v2 de KoboToolbox con soporte de paginación,
elevación de esquemas (Upcasting V1->V4) y conversión a DataFrames clasificados.
"""

import logging
from typing import Dict, List, Optional, Any
import requests
import pandas as pd

from .config import DEFAULT_KOBO_BASE_URL, DEFAULT_KOBO_API_TOKEN
from .no_respuesta_classifier import (
    upcast_record_to_v4,
    apply_housing_classification_df,
)

logger = logging.getLogger(__name__)


class KoboAPIClient:
    """Cliente para interactuar con los endpoints v2 de KoboToolbox."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = False,
    ):
        self.base_url = (base_url or DEFAULT_KOBO_BASE_URL).rstrip("/")
        self.token = token or DEFAULT_KOBO_API_TOKEN
        self.timeout = timeout
        self.verify_ssl = verify_ssl

    @property
    def headers(self) -> Dict[str, str]:
        """Cabeceras HTTP necesarias para autenticación en la API de Kobo."""
        return {
            "Authorization": f"Token {self.token}",
            "Accept": "application/json",
        }

    def get_assets(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de activos/formularios de KoboToolbox.

        Returns:
            List[Dict[str, Any]]: Lista de diccionarios con la información de los activos.
        """
        url = f"{self.base_url}/assets/?format=json"
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify_ssl,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", [])
        except requests.RequestException as e:
            logger.error(f"Error al obtener assets de Kobo ({url}): {e}")
            raise RuntimeError("Error al comunicarse con el servidor") from e

    def get_asset_data(
        self, asset_uid: str, page_size: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Descarga todos los registros (submissions) de un activo/formulario Kobo,
        manejando automáticamente la paginación de la API v2.

        Args:
            asset_uid (str): UID del formulario en Kobo.
            page_size (int): Tamaño de página para la solicitud.

        Returns:
            List[Dict[str, Any]]: Lista de todos los registros raw descargados.
        """
        all_results: List[Dict[str, Any]] = []
        next_url: Optional[str] = (
            f"{self.base_url}/assets/{asset_uid}/data/?format=json&page_size={page_size}"
        )

        while next_url:
            try:
                response = requests.get(
                    next_url,
                    headers=self.headers,
                    timeout=self.timeout,
                    verify=self.verify_ssl,
                )
                response.raise_for_status()
                payload = response.json()

                results = payload.get("results", [])
                all_results.extend(results)

                # Pasar a la siguiente página
                next_url = payload.get("next")
            except requests.RequestException as e:
                logger.error(
                    f"Error al descargar página de data para asset {asset_uid}: {e}"
                )
                raise RuntimeError("Error al comunicarse con el servidor") from e

        return all_results

    def fetch_and_process_kobo_dataframe(self, asset_uid: str) -> pd.DataFrame:
        """
        Descarga los registros de Kobo, los normaliza al esquema canónico V4
        y los devuelve como un DataFrame de Pandas clasificado con 'tipologia_vivienda'.

        Args:
            asset_uid (str): UID del formulario Kobo.

        Returns:
            pd.DataFrame: DataFrame procesado y enriquecido con clasificaciones.
        """
        raw_records = self.get_asset_data(asset_uid)
        if not raw_records:
            return pd.DataFrame()

        # Elevar cada registro al esquema V4 e inferir su periodo temporal
        from .kobo_consolidator import infer_period_from_record
        upcasted_records = []
        for r in raw_records:
            v4_rec = upcast_record_to_v4(r)
            period = infer_period_from_record(v4_rec)
            v4_rec["anio"] = period["anio"]
            v4_rec["Semestre"] = period["Semestre"]
            upcasted_records.append(v4_rec)

        # Crear DataFrame inicial
        df = pd.DataFrame(upcasted_records)

        # Mapear nombres estándar para el Dashboard sin duplicar nombres de columna
        col_renames = {}

        # Unificar columnas clave coalesciendo todas las posibles variantes
        target_mappings = [
            ("encuestador", ["s0/cedula_encuestador", "v4_encuestador", "cedula_encuestador", "encuestador"]),
            ("estatusentrevista", ["ubicacion_final/nota", "estatus_entrevista", "estatusentrevista", "nota"]),
            ("control", ["datos_mm111/control", "group_sh53u78/control", "v4_control", "control", "id_vivienda", "vivienda_id"]),
            ("nodo", ["S1/nodo", "S1/S2/nodo", "v4_nodo", "nodo"]),
            ("municipio", ["S1/mun", "S1/S2/mun", "S1/Ymun", "v4_municipio", "municipio", "mun"]),
        ]

        def coalesce_series(dframe, target_col, candidates):
            s = pd.Series([None] * len(dframe), index=dframe.index, dtype=object)
            cols = ([target_col] if target_col in dframe.columns else []) + [c for c in candidates if c in dframe.columns]
            for c in cols:
                s = s.fillna(dframe[c])
            return s

        for target_col, candidates in target_mappings:
            df[target_col] = coalesce_series(df, target_col, candidates)

        # Aplicar clasificación jerárquica de No Respuesta y derivar es_efectiva y entrevista
        df_classified = apply_housing_classification_df(df)
        return df_classified
