"""
kobo_consolidator.py
Módulo de consolidación masiva multi-formulario (V1 -> V4)
para encuestas KoboToolbox (EHM y ESCA).
Extrae registros de múltiples activos, aplica Upcasting, determina
el periodo temporal (2025 / 2026 S1) y genera DataFrames unificados.
"""

import logging
import re
from typing import Dict, List, Optional, Any
import pandas as pd

from .kobo_client import KoboAPIClient
from .no_respuesta_classifier import (
    upcast_record_to_v4,
    apply_housing_classification_df,
)

from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


def infer_period_from_record(record: Dict[str, Any]) -> Dict[str, str]:
    """
    Deduce el año y semestre de un registro basándose en campos de fecha Kobo
    (_submission_time, start, today, fecha, etc.) o sufijos del formulario.

    Args:
        record (Dict[str, Any]): Registro individual de encuesta.

    Returns:
        Dict[str, str]: Diccionario con 'anio' y 'semestre'.
    """
    raw_date = (
        record.get("_submission_time")
        or record.get("today")
        or record.get("start")
        or record.get("fecha")
        or ""
    )

    year = "2025"
    semester = "Primer Semestre 2025"

    match = re.search(r"202[4-6]", str(raw_date))
    if match:
        year = match.group(0)
    else:
        # Si no hay año en la fecha, revisar otros campos de texto
        str_rec = str(record).lower()
        if "2026" in str_rec:
            year = "2026"
        elif "2025" in str_rec:
            year = "2025"

    # Determinar mes si existe formato YYYY-MM-DD
    month = None
    month_match = re.search(r"202[4-6]-(\d{2})", str(raw_date))
    if month_match:
        try:
            month = int(month_match.group(1))
        except ValueError:
            pass

    if year == "2025":
        if month and month > 6:
            semester = "Segundo Semestre 2025"
        else:
            semester = "Primer Semestre 2025"
    elif year == "2026":
        if month and month > 6:
            semester = "Segundo Semestre 2026"
        else:
            semester = "Primer Semestre 2026"
    else:
        semester = "Primer Semestre 2025"

    return {"anio": year, "Semestre": semester}


def fetch_consolidated_kobo_dataset(
    client: KoboAPIClient,
    asset_uids: Optional[List[str]] = None,
    auto_detect_all: bool = True,
    survey_family: Optional[str] = "ALL",
) -> pd.DataFrame:
    """
    Descarga y consolida los envíos de múltiples formularios KoboToolbox,
    aplicando upcasting de esquema (V1-V4), resolución de periodos (2025 / 2026 S1),
    enriquecimiento de taxonomía por encuesta (EHM / ESCA) y clasificación de No Respuesta.

    Args:
        client (KoboAPIClient): Instancia del cliente API Kobo.
        asset_uids (List[str], optional): Lista de UIDs a descargar.
        auto_detect_all (bool): Si es True, detecta automáticamente todos los activos de la cuenta.
        survey_family (str, optional): 'ALL', 'EHM' o 'ESCA'.

    Returns:
        pd.DataFrame: DataFrame consolidado y unificado.
    """
    asset_name_map = {}
    if auto_detect_all or not asset_uids:
        try:
            assets = client.get_assets()
            asset_uids = [a.get("uid") for a in assets if a.get("uid")]
            asset_name_map = {a.get("uid"): a.get("name", "") for a in assets if a.get("uid")}
            logger.info(f"Se detectaron {len(asset_uids)} formularios Kobo.")
        except Exception as e:
            logger.error(f"Error al listar activos para consolidación: {e}")
            raise

    if not asset_uids:
        return pd.DataFrame()

    def fetch_asset_records(uid: str) -> List[Dict[str, Any]]:
        aname = asset_name_map.get(uid, "")
        records = []
        try:
            raw_records = client.get_asset_data(uid)
            for r in raw_records:
                v4_rec = upcast_record_to_v4(r, asset_name=aname)
                period_info = infer_period_from_record(v4_rec)
                v4_rec["anio"] = period_info["anio"]
                v4_rec["Semestre"] = period_info["Semestre"]
                v4_rec["kobo_asset_uid"] = uid

                fam = v4_rec.get("Familia_Encuesta", v4_rec.get("Tipo_Encuesta", "EHM"))
                if survey_family and survey_family.upper() != "ALL":
                    if fam.upper() != survey_family.upper():
                        continue

                records.append(v4_rec)
        except Exception as e:
            logger.warning(f"No se pudieron obtener registros del asset {uid}: {e}")
        return records

    combined_records: List[Dict[str, Any]] = []
    max_workers = min(10, max(1, len(asset_uids)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(fetch_asset_records, asset_uids)
        for res in results:
            combined_records.extend(res)

    if not combined_records:
        return pd.DataFrame()

    # Crear DataFrame unificado
    df = pd.DataFrame(combined_records)

    # Unificar columnas clave coalesciendo todas las posibles variantes
    def coalesce_series(dframe, target_col, candidates):
        s = pd.Series([None] * len(dframe), index=dframe.index, dtype=object)
        cols = ([target_col] if target_col in dframe.columns else []) + [c for c in candidates if c in dframe.columns]
        for c in cols:
            s = s.fillna(dframe[c])
        return s

    target_mappings = [
        ("nodo", ["S1/S2/nodo", "S1/nodo", "v4_nodo"]),
        ("municipio", ["S1/S2/mun", "S1/mun", "S1/Ymun", "v4_municipio", "mun"]),
        ("control", ["v4_control", "datos_mm111/control", "group_sh53u78/control", "id_vivienda"]),
        ("encuestador", ["S0/cedula_encuestador", "cedula_encuestador", "v4_encuestador"]),
    ]

    for target_col, candidates in target_mappings:
        df[target_col] = coalesce_series(df, target_col, candidates)

    from .formatters import format_municipio_name
    if "municipio" in df.columns:
        df["municipio"] = df["municipio"].apply(format_municipio_name)

    # Normalizar encuestadores
    if "encuestador" in df.columns:
        df["encuestador"] = df["encuestador"].astype(str).str.strip().str.upper()

    # Aplicar clasificación jerárquica de No Respuesta y derivar es_efectiva y entrevista
    df_classified = apply_housing_classification_df(df)
    return df_classified


def fetch_ehm_dataset(
    client: KoboAPIClient,
    asset_uids: Optional[List[str]] = None,
    auto_detect_all: bool = True,
) -> pd.DataFrame:
    """Descarga y normaliza específicamente las encuestas de la familia EHM."""
    return fetch_consolidated_kobo_dataset(
        client=client,
        asset_uids=asset_uids,
        auto_detect_all=auto_detect_all,
        survey_family="EHM",
    )


def fetch_esca_dataset(
    client: KoboAPIClient,
    asset_uids: Optional[List[str]] = None,
    auto_detect_all: bool = True,
) -> pd.DataFrame:
    """Descarga y normaliza específicamente las encuestas de la familia ESCA."""
    return fetch_consolidated_kobo_dataset(
        client=client,
        asset_uids=asset_uids,
        auto_detect_all=auto_detect_all,
        survey_family="ESCA",
    )

