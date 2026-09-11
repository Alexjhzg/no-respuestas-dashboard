import io
import pandas as pd


def export_to_csv(df: pd.DataFrame) -> bytes:
    """
    Convierte un DataFrame a bytes codificados en UTF-8 en formato CSV.

    Args:
        df (pd.DataFrame): DataFrame a exportar.

    Returns:
        bytes: Datos binarios CSV.
    """
    if df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")


def export_to_excel(df: pd.DataFrame, sheet_name: str = "Datos") -> bytes:
    """
    Convierte un DataFrame a bytes de libro Excel (.xlsx) usando openpyxl.

    Args:
        df (pd.DataFrame): DataFrame a exportar.
        sheet_name (str): Nombre de la hoja Excel.

    Returns:
        bytes: Contenido binario del archivo Excel.
    """
    if df.empty:
        return b""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()
