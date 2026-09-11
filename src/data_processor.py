"""
data_processor.py
Módulo principal para la carga, sincronización API/Parquet y gestión de fallbacks de datasets.
"""

import os
import json
import pandas as pd
import streamlit as st
from typing import Optional, List, Any
from .config import DEFAULT_KOBO_BASE_URL, DEFAULT_KOBO_API_TOKEN
from .no_respuesta_classifier import apply_housing_classification_df
from .kobo_client import KoboAPIClient
from .kobo_consolidator import fetch_consolidated_kobo_dataset, infer_period_from_record

# Re-exportaciones de compatibilidad desde submódulos especializados
from .formatters import format_control_short, extract_control_series
from .reports import (
    get_kpis,
    get_control_no_response_report,
    load_planned_controls_catalog,
    get_planned_vs_executed_report,
)


def load_data_from_kobo_asset(
    asset_uid: str,
    token: Optional[str] = None,
    base_url: Optional[str] = None,
) -> pd.DataFrame:
    """
    Descarga y procesa datos directamente desde la API v2 de KoboToolbox para un asset específico.

    Args:
        asset_uid (str): UID del formulario Kobo.
        token (str, optional): Token API.
        base_url (str, optional): URL base de Kobo.

    Returns:
        pd.DataFrame: DataFrame procesado y clasificado.
    """
    client = KoboAPIClient(base_url=base_url, token=token)
    df = client.fetch_and_process_kobo_dataframe(asset_uid)

    if not df.empty:
        if "Tipo_Encuesta" not in df.columns:
            df["Tipo_Encuesta"] = "API_KOBO"
        if "Semestre" not in df.columns:
            periods = [infer_period_from_record(row)["Semestre"] for row in df.to_dict("records")]
            df["Semestre"] = periods

        if "entrevista" in df.columns:
            df["entrevista"] = pd.to_numeric(
                df["entrevista"], errors="coerce"
            ).fillna(0)

    return df


def load_consolidated_dataset(
    source_type: str = "kobo",
    kobo_asset_uids: Optional[List[str]] = None,
    kobo_token: Optional[str] = None,
    kobo_base_url: Optional[str] = None,
    auto_detect_all: bool = True,
    survey_family: Optional[str] = "ALL",
) -> pd.DataFrame:
    """
    Descarga y consolida masivamente los envíos de múltiples formularios Kobo
    para los periodos 2025 y 2026 S1 con normalización por encuesta (EHM / ESCA).

    Args:
        source_type (str): Origen de datos ('kobo').
        kobo_asset_uids (List[str], optional): UIDs específicos a consolidar.
        kobo_token (str, optional): Token API.
        kobo_base_url (str, optional): URL base de Kobo API.
        auto_detect_all (bool): Si es True, detecta e integra todos los formularios activos.
        survey_family (str, optional): 'ALL', 'EHM' o 'ESCA'.

    Returns:
        pd.DataFrame: DataFrame consolidado y normalizado.
    """
    client = KoboAPIClient(base_url=kobo_base_url, token=kobo_token)
    try:
        df = fetch_consolidated_kobo_dataset(
            client=client,
            asset_uids=kobo_asset_uids,
            auto_detect_all=auto_detect_all,
            survey_family=survey_family,
        )
        if not df.empty:
            return df
    except Exception as e:
        st.warning("Error al comunicarse con el servidor. Cargando datos locales en caché...")

    # Fallback a dataset local con caché Parquet ultra-rápida y validación mtime
    return load_local_fallback_dataset(survey_family=survey_family)


def load_local_fallback_dataset(
    json_path: Optional[str] = None,
    parquet_path: Optional[str] = None,
    survey_family: Optional[str] = "ALL",
) -> pd.DataFrame:
    """
    Carga el dataset local de fallback usando caché binario Parquet con validación de timestamps.
    Normaliza esquemas por tipo de encuesta (EHM / ESCA) y aplica filtrado por familia.
    """
    if json_path is None:
        json_path = os.path.join("data", "consolidado_completo_ehm_esca_2025_2026.json")
    if parquet_path is None:
        parquet_path = os.path.join("data", "consolidado_completo_ehm_esca_2025_2026.parquet")

    if not os.path.exists(json_path):
        return pd.DataFrame()

    df_result = pd.DataFrame()

    # 1. Comprobar si existe el Parquet y si su timestamp es más reciente o igual al del JSON
    if os.path.exists(parquet_path):
        try:
            if os.path.getmtime(parquet_path) >= os.path.getmtime(json_path):
                df_result = pd.read_parquet(parquet_path)
        except Exception:
            pass  # Fallback a parsear JSON si hubiera algún problema al leer el Parquet

    if df_result.empty:
        # 2. Parsear JSON, normalizar esquemas y aplicar clasificación
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                records = content.get("records", [])
                for r in records:
                    period = infer_period_from_record(r)
                    r["Semestre"] = period["Semestre"]
                    r["anio"] = period["anio"]

                df_json = pd.DataFrame(records)

                def coalesce_series(dframe, target_col, candidates):
                    s = pd.Series([None] * len(dframe), index=dframe.index, dtype=object)
                    cols = ([target_col] if target_col in dframe.columns else []) + [c for c in candidates if c in dframe.columns]
                    for c in cols:
                        s = s.fillna(dframe[c])
                    return s

                from .formatters import format_municipio_name

                df_json["nodo"] = coalesce_series(df_json, "nodo", ["S1/S2/nodo", "S1/nodo", "v4_nodo"])
                df_json["municipio"] = coalesce_series(df_json, "municipio", ["S1/S2/mun", "S1/mun", "S1/Ymun", "v4_municipio", "mun"]).apply(format_municipio_name)
                df_json["control"] = coalesce_series(df_json, "control", ["v4_control", "datos_mm111/control", "group_sh53u78/control", "id_vivienda"])

                df_result = apply_housing_classification_df(df_json)

                # 3. Guardar en caché Parquet para futuras lecturas ultra-rápidas
                try:
                    parent_dir = os.path.dirname(parquet_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    df_result.to_parquet(parquet_path, index=False)
                except Exception as e:
                    st.warning(f"No se pudo escribir la caché Parquet: {e}")
        except Exception as e:
            st.error(f"Error al leer dataset JSON local: {e}")
            return pd.DataFrame()

    if not df_result.empty and survey_family and survey_family.upper() != "ALL":
        if "Familia_Encuesta" in df_result.columns:
            df_result = df_result[df_result["Familia_Encuesta"].astype(str).str.upper() == survey_family.upper()]
        elif "Tipo_Encuesta" in df_result.columns:
            df_result = df_result[df_result["Tipo_Encuesta"].astype(str).str.upper() == survey_family.upper()]

    return df_result


def load_and_clean_data(
    source_type: str = "kobo",
    kobo_asset_uid: Optional[str] = None,
    kobo_token: Optional[str] = None,
    kobo_base_url: Optional[str] = None,
) -> pd.DataFrame:
    """
    Carga los datos directamente desde la API de KoboToolbox.

    Args:
        source_type (str): Origen de datos ('kobo').
        kobo_asset_uid (str, optional): UID del activo en Kobo.
        kobo_token (str, optional): Token de API Kobo.
        kobo_base_url (str, optional): URL base de Kobo.

    Returns:
        pd.DataFrame: DataFrame combinado y limpio con clasificaciones jerárquicas.
    """
    if kobo_asset_uid:
        try:
            return load_data_from_kobo_asset(
                asset_uid=kobo_asset_uid,
                token=kobo_token,
                base_url=kobo_base_url,
            )
        except Exception as e:
            st.warning("Error al comunicarse con el servidor. Cargando datos locales en caché...")
            return load_local_fallback_dataset()

    return load_consolidated_dataset(
        source_type="kobo",
        kobo_token=kobo_token,
        kobo_base_url=kobo_base_url,
        auto_detect_all=True,
    )
