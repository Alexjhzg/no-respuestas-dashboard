"""
catalog_builder.py
Módulo para escanear, extraer y consolidar el Catálogo Maestro de Controles Planificados
a partir de archivos de marco muestral Excel (.xlsx) y CSV (EHM, ESCA, etc.).
"""

import os
import glob
import logging
from typing import List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


def build_planned_controls_catalog(
    root_dir: str = ".",
    output_csv: Optional[str] = None,
    output_parquet: Optional[str] = None,
) -> pd.DataFrame:
    """
    Escanea la carpeta en busca de marcos muestrales Excel/CSV,
    extrae la lista única de controles planificados y genera el dataset consolidado.

    Args:
        root_dir (str): Directorio raíz de búsqueda.
        output_csv (str, optional): Ruta donde guardar el CSV.
        output_parquet (str, optional): Ruta donde guardar el Parquet.

    Returns:
        pd.DataFrame: DataFrame de catálogo maestro de controles planificados.
    """
    if output_csv is None:
        output_csv = os.path.join("data", "controles_planificados.csv")
    if output_parquet is None:
        output_parquet = os.path.join("data", "controles_planificados.parquet")

    records = []

    # 1. Buscar archivos Excel de marco muestral (ej: 16_Monagas_EHM.xlsx)
    xlsx_files = glob.glob(os.path.join(root_dir, "*_*.xlsx")) + glob.glob(
        os.path.join(root_dir, "data", "*_*.xlsx")
    )

    for filepath in sorted(set(xlsx_files)):
        filename = os.path.basename(filepath)
        # Ignorar reportes o listas generadas por el sistema
        if (
            filename.startswith("reporte_")
            or filename.startswith("resumen_")
            or filename.startswith("lista_")
            or filename.startswith("~$")
        ):
            continue

        try:
            df_file = pd.read_excel(filepath)
            if df_file.empty:
                continue

            # Determinar operativo (EHM o ESCA) desde el nombre del archivo
            operativo = "EHM"
            if "esca" in filename.lower():
                operativo = "ESCA"
            elif "ehm" in filename.lower():
                operativo = "EHM"

            # Identificar columnas de semana y control
            col_semana = None
            for c in ["semana", "SEMANA", "Semana"]:
                if c in df_file.columns:
                    col_semana = c
                    break

            col_control = None
            for c in ["control", "CONTROL", "Control"]:
                if c in df_file.columns:
                    col_control = c
                    break

            col_entidad = None
            for c in ["COD_ENTIDAD", "COD_ ENT", "COD_ENT", "entidad"]:
                if c in df_file.columns:
                    col_entidad = c
                    break

            col_mun = None
            for c in ["municipio", "COD_MUN", "mun", "COD-MUN"]:
                if c in df_file.columns:
                    col_mun = c
                    break

            col_parr = None
            for c in ["parroquia", "COD-PARROQ", "COD_PARROQ", "parroquia"]:
                if c in df_file.columns:
                    col_parr = c
                    break

            if col_semana and col_control:
                grouped = df_file.groupby([col_semana, col_control])
                for (sem, ctrl), grp in grouped:
                    try:
                        sem_num = int(sem)
                        ctrl_num = int(ctrl)
                        entidad_num = int(grp[col_entidad].iloc[0]) if col_entidad else 16
                        ctrl_8 = f"{entidad_num:02d}{sem_num:02d}{ctrl_num:04d}"

                        mun_val = str(grp[col_mun].iloc[0]) if col_mun else ""
                        parr_val = str(grp[col_parr].iloc[0]) if col_parr else ""

                        records.append({
                            "control": ctrl_8,
                            "entidad": entidad_num,
                            "operativo": operativo,
                            "semana": sem_num,
                            "control_raw": ctrl_num,
                            "municipio": mun_val,
                            "parroquia": parr_val,
                            "viviendas_planificadas": len(grp),
                            "archivo_origen": filename,
                        })
                    except (ValueError, TypeError):
                        continue
        except Exception as e:
            logger.warning(f"Error procesando marco muestral {filename}: {e}")

    if not records:
        return pd.DataFrame()

    df_catalog = pd.DataFrame(records)

    # Eliminar duplicados manteniendo el primer registro si el mismo control aparece dos veces
    df_catalog = df_catalog.drop_duplicates(subset=["control", "operativo"]).reset_index(
        drop=True
    )

    # Guardar a disco en CSV y Parquet
    try:
        os.makedirs(os.path.dirname(output_csv), exist_ok=True)
        df_catalog.to_csv(output_csv, index=False, encoding="utf-8")
        df_catalog.to_parquet(output_parquet, index=False)
        logger.info(f"Catálogo maestro de controles guardado en {output_csv} ({len(df_catalog)} controles).")
    except Exception as e:
        logger.error(f"Error guardando catálogo maestro de controles: {e}")

    return df_catalog


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df_cat = build_planned_controls_catalog()
    print(f"Catálogo construido con {len(df_cat)} controles planificados.")
