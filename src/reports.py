"""
reports.py
Módulo dedicado al cálculo de KPIs, agregaciones y generación de reportes de negocio.
"""

import os
from typing import Optional, Dict, Any
import pandas as pd
from .formatters import extract_control_series, format_control_short


def get_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula los KPIs principales enfocados en Controles Evaluados y Porcentaje de No Respuesta.

    Args:
        df (pd.DataFrame): DataFrame filtrado.

    Returns:
        Dict[str, Any]: Diccionario con controles evaluados y porcentaje de no respuesta.
    """
    if df.empty:
        return {
            "controles_evaluados": 0,
            "porcentaje_no_respuesta": 0.0,
            "no_respuestas": 0,
        }

    total_asignadas = len(df)

    if "entrevista" in df.columns and df["entrevista"].notnull().any():
        entrevista_series = pd.to_numeric(df["entrevista"], errors="coerce").fillna(0)
    elif "es_efectiva" in df.columns:
        entrevista_series = df["es_efectiva"].astype(int)
    elif "tipologia_vivienda" in df.columns:
        entrevista_series = (df["tipologia_vivienda"] == "TIPO E").astype(int)
    else:
        entrevista_series = pd.Series([0] * total_asignadas, index=df.index)

    no_respuestas = int((entrevista_series == 0).sum())
    porcentaje_no_respuesta = (
        (no_respuestas / total_asignadas * 100)
        if total_asignadas > 0
        else 0.0
    )

    c_series = extract_control_series(df)
    c_clean = c_series[~c_series.isin(["nan", "None", "", "SIN_CONTROL"])]
    controles_evaluados = c_clean.nunique()

    return {
        "controles_evaluados": controles_evaluados,
        "porcentaje_no_respuesta": porcentaje_no_respuesta,
        "no_respuestas": no_respuestas,
    }


def get_control_no_response_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera un informe detallado agrupado por Control y Semestre,
    enfocado en el Código de Control y la No Respuesta.

    Args:
        df (pd.DataFrame): DataFrame de encuestas procesado.

    Returns:
        pd.DataFrame: Resumen por control y semestre ordenado por % de No Respuesta descendente.
    """
    if df.empty:
        return pd.DataFrame()

    df_calc = df.copy()
    df_calc["control_unificado"] = extract_control_series(df_calc)

    if "Semestre" not in df_calc.columns:
        df_calc["Semestre"] = "General"

    if "entrevista" not in df_calc.columns:
        if "es_efectiva" in df_calc.columns:
            df_calc["entrevista"] = df_calc["es_efectiva"].astype(int)
        else:
            df_calc["entrevista"] = 0

    grouped = (
        df_calc.groupby(["control_unificado", "Semestre"])
        .agg(
            Total_Asignadas=("entrevista", "count"),
            No_Respuestas=("entrevista", lambda x: (x == 0).sum()),
        )
        .reset_index()
    )

    grouped["Porcentaje_No_Respuesta"] = (
        grouped["No_Respuestas"] / grouped["Total_Asignadas"] * 100
    ).round(2)

    grouped = grouped.rename(
        columns={
            "control_unificado": "Control",
            "Total_Asignadas": "Total Registros",
            "No_Respuestas": "No Diligenciadas",
            "Porcentaje_No_Respuesta": "% No Respuesta",
        }
    )

    grouped["Control"] = grouped["Control"].apply(format_control_short)

    grouped = grouped[["Control", "Semestre", "Total Registros", "No Diligenciadas", "% No Respuesta"]]

    grouped = grouped.sort_values(
        by=["Semestre", "% No Respuesta"], ascending=[True, False]
    )
    return grouped


def load_planned_controls_catalog(
    parquet_path: Optional[str] = None,
    csv_path: Optional[str] = None,
) -> pd.DataFrame:
    """
    Carga la lista maestra de controles planificados desde Parquet o CSV.
    Si los archivos no existen, invoca la generación automática desde los marcos muestrales.
    """
    if parquet_path is None:
        parquet_path = os.path.join("data", "controles_planificados.parquet")
    if csv_path is None:
        csv_path = os.path.join("data", "controles_planificados.csv")

    if os.path.exists(parquet_path):
        try:
            return pd.read_parquet(parquet_path)
        except Exception:
            pass

    if os.path.exists(csv_path):
        try:
            return pd.read_csv(csv_path, dtype=str)
        except Exception:
            pass

    from .catalog_builder import build_planned_controls_catalog
    return build_planned_controls_catalog()


def get_planned_vs_executed_report(
    df_actual: pd.DataFrame,
    df_planned: Optional[pd.DataFrame] = None,
    by_semester: bool = False,
) -> pd.DataFrame:
    """
    Cruza el Catálogo Maestro de Controles Planificados con las encuestas realmente capturadas.
    Calcula el estado de ejecución por control ('Levantado' vs 'Pendiente') y desglosa viviendas planificadas vs capturadas.

    Args:
        df_actual (pd.DataFrame): Encuestas capturadas.
        df_planned (pd.DataFrame, optional): Catálogo maestro de controles planificados.
        by_semester (bool): Si es True, desglosa las filas por [Control, Semestre]. Si es False, consolida por Control.
    """
    if df_planned is None or df_planned.empty:
        df_planned = load_planned_controls_catalog()

    if df_planned.empty:
        return pd.DataFrame()

    df_plan = df_planned.copy()
    df_plan["control"] = df_plan["control"].astype(str).str.strip()

    if df_actual.empty:
        df_plan["Viviendas Capturadas"] = 0
        df_plan["Diligenciadas"] = 0
        df_plan["No Diligenciadas"] = 0
        df_plan["Estatus"] = "Pendiente"
        df_plan["% No Respuesta"] = 0.0
        if by_semester:
            df_plan["Semestre"] = "Sin Envíos"
        else:
            df_plan["Semestres Levantados"] = "Sin Envíos"
        return df_plan

    df_act = df_actual.copy()
    df_act["control_unificado"] = extract_control_series(df_act)

    if "Semestre" not in df_act.columns:
        df_act["Semestre"] = "General"

    if "entrevista" not in df_act.columns:
        if "es_efectiva" in df_act.columns:
            df_act["entrevista"] = df_act["es_efectiva"].astype(int)
        else:
            df_act["entrevista"] = 0

    if by_semester:
        agg_actual = (
            df_act.groupby(["control_unificado", "Semestre"])
            .agg(
                Viviendas_Capturadas=("entrevista", "count"),
                Diligenciadas=("entrevista", lambda x: (x == 1).sum()),
                No_Diligenciadas=("entrevista", lambda x: (x == 0).sum()),
            )
            .reset_index()
        )

        merged = pd.merge(
            df_plan,
            agg_actual,
            left_on="control",
            right_on="control_unificado",
            how="left",
        )
        merged["Semestre"] = merged["Semestre"].fillna("Sin Envíos")
    else:
        def fmt_semestres(series):
            sems = sorted(set(series.dropna().astype(str).unique()))
            if not sems:
                return "Sin Envíos"
            elif len(sems) == 1:
                return sems[0]
            else:
                def sem_key(s):
                    year = "9999"
                    for y in ["2024", "2025", "2026", "2027"]:
                        if y in s:
                            year = y
                            break
                    sem_num = "1" if "Primer" in s else ("2" if "Segundo" in s else "9")
                    return f"{year}_{sem_num}"

                sorted_sems = sorted(sems, key=sem_key)
                short_sems = [
                    s.replace("Primer Semestre ", "").replace("Segundo Semestre ", "") + (" S1" if "Primer" in s else (" S2" if "Segundo" in s else ""))
                    for s in sorted_sems
                ]
                return f"Multi-Semestre ({', '.join(short_sems)})"

        agg_actual = (
            df_act.groupby("control_unificado")
            .agg(
                Viviendas_Capturadas=("entrevista", "count"),
                Diligenciadas=("entrevista", lambda x: (x == 1).sum()),
                No_Diligenciadas=("entrevista", lambda x: (x == 0).sum()),
                Semestres_Levantados=("Semestre", fmt_semestres),
            )
            .reset_index()
        )

        merged = pd.merge(
            df_plan,
            agg_actual,
            left_on="control",
            right_on="control_unificado",
            how="left",
        )
        merged["Semestres Levantados"] = merged["Semestres_Levantados"].fillna("Sin Envíos")

    merged["Viviendas Capturadas"] = merged["Viviendas_Capturadas"].fillna(0).astype(int)
    merged["Diligenciadas"] = merged["Diligenciadas"].fillna(0).astype(int)
    merged["No Diligenciadas"] = merged["No_Diligenciadas"].fillna(0).astype(int)

    merged["Estatus"] = merged["Viviendas Capturadas"].apply(
        lambda x: "Levantado" if x > 0 else "Pendiente"
    )

    merged["% No Respuesta"] = (
        merged.apply(
            lambda r: (r["No Diligenciadas"] / r["Viviendas Capturadas"] * 100)
            if r["Viviendas Capturadas"] > 0
            else 0.0,
            axis=1,
        )
    ).round(1)

    res = merged.rename(
        columns={
            "control": "Control",
            "operativo": "Operativo",
            "semana": "Semana",
            "municipio": "Municipio",
            "parroquia": "Parroquia",
            "viviendas_planificadas": "Viviendas Planificadas",
        }
    )

    if by_semester:
        cols = [
            "Control",
            "Operativo",
            "Semestre",
            "Semana",
            "Municipio",
            "Estatus",
            "Viviendas Planificadas",
            "Viviendas Capturadas",
            "Diligenciadas",
            "No Diligenciadas",
            "% No Respuesta",
        ]
    else:
        cols = [
            "Control",
            "Operativo",
            "Semana",
            "Municipio",
            "Estatus",
            "Semestres Levantados",
            "Viviendas Planificadas",
            "Viviendas Capturadas",
            "Diligenciadas",
            "No Diligenciadas",
            "% No Respuesta",
        ]

    if "Control" in res.columns:
        res["Control"] = res["Control"].apply(format_control_short)

    present_cols = [c for c in cols if c in res.columns]
    sort_cols = ["Estatus", "Semestre", "Control"] if by_semester else ["Estatus", "Semana", "Control"]
    present_sort_cols = [c for c in sort_cols if c in res.columns]
    res = res[present_cols].sort_values(
        by=present_sort_cols, ascending=[True] * len(present_sort_cols)
    )

    return res
