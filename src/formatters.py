"""
formatters.py
Módulo de utilidades de formateo y unificación de series (Controles, Encuestadores, Textos).
"""

from typing import Any
import pandas as pd
from .config import CONTROL_REMAPS, MUNICIPIOS_MAP


def format_municipio_name(val: Any) -> str:
    """
    Mapea y formate el código de municipio (ej. 1601, 1608) a su nombre correspondiente
    con código (ej. '1601 - Acosta', '1608 - Maturín').

    Args:
        val: Código de municipio.

    Returns:
        str: Nombre y código formateado de municipio.
    """
    if val is None or pd.isna(val):
        return ""
    m_str = str(val).strip()
    if m_str.endswith(".0"):
        m_str = m_str[:-2]
    if m_str in MUNICIPIOS_MAP:
        return MUNICIPIOS_MAP[m_str]
    if len(m_str) == 6 and m_str.startswith("16"):
        sub_code = m_str[:4]
        if sub_code in MUNICIPIOS_MAP:
            return MUNICIPIOS_MAP[sub_code]
    return m_str


def format_control_short(val: Any) -> str:
    """
    Convierte un código de control completo (ej. 16010004, 16012050, 16040051)
    a su representación en dígitos resumidos (ej. 4, 2050, 51) correspondiente
    al formato utilizado en los marcos muestrales Excel.

    Args:
        val: Valor raw del código de control.

    Returns:
        str: Código de control en formato resumido.
    """
    if val is None or pd.isna(val):
        return ""
    c_str = str(val).strip()
    if not c_str or c_str in ("nan", "None", "SIN_CONTROL"):
        return c_str
    if len(c_str) == 8 and c_str.isdigit() and c_str.startswith("16"):
        try:
            return str(int(c_str[-4:]))
        except ValueError:
            pass
    elif len(c_str) > 4 and c_str.isdigit():
        try:
            return str(int(c_str[-4:]))
        except ValueError:
            pass
    return c_str


def extract_control_series(dframe: pd.DataFrame) -> pd.Series:
    """
    Extrae y unifica la serie de códigos de control a partir de todas las posibles variantes de nombres de columna.

    Args:
        dframe (pd.DataFrame): DataFrame de encuestas.

    Returns:
        pd.Series: Serie de códigos de control unificados.
    """
    if dframe.empty:
        return pd.Series(dtype=str)

    def get_col_or_empty(df_in, col_name):
        if col_name in df_in.columns:
            return df_in[col_name]
        return pd.Series([None] * len(df_in), index=df_in.index)

    c1 = get_col_or_empty(dframe, "control")
    c2 = get_col_or_empty(dframe, "v4_control")
    c3 = get_col_or_empty(dframe, "datos_mm111/control")
    c4 = get_col_or_empty(dframe, "group_sh53u78/control")

    series = (
        c1.fillna(c2)
        .fillna(c3)
        .fillna(c4)
        .fillna("SIN_CONTROL")
        .astype(str)
        .str.strip()
    )
    return series.replace(CONTROL_REMAPS)
