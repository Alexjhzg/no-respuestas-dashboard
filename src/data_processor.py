import pandas as pd
import streamlit as st
from .config import DATA_FILES

def load_and_clean_data():
    """
    Carga los datos de los archivos Excel configurados, los combina y realiza la limpieza inicial.
    
    Returns:
        pd.DataFrame: DataFrame combinado y limpio.
    """
    combined_df = pd.DataFrame()
    
    for tipo, file_path in DATA_FILES.items():
        try:
            # Intentamos leer todas las hojas (Semestre 1 y 2 asumiendo que existen)
            xl = pd.ExcelFile(file_path)
            for sheet_name in xl.sheet_names:
                df = xl.parse(sheet_name)
                
                # Normalizar nombres de columnas (quitar espacios adicionales y homogeneizar a minúsculas temporalmente)
                col_mapping = {c: str(c).strip().lower() for c in df.columns}
                df = df.rename(columns=col_mapping)
                
                # Deshacer minúsculas solo para las columnas estructurales base que pueden usarse luego o unificarlas.
                # Como 'Tipo_Encuesta' se agrega manualmente, la pondremos después.
                
                # Unificar 'anio (año)' a 'anio'
                if 'anio (año)' in df.columns:
                    df = df.rename(columns={'anio (año)': 'anio'})
                
                df['Tipo_Encuesta'] = tipo
                
                # Mapeo descriptivo del semestre
                s_name = sheet_name.upper()
                
                anio_str = ""
                if "2025" in s_name:
                    anio_str = " 2025"
                elif "2026" in s_name:
                    anio_str = " 2026"
                
                if any(x in s_name for x in ["1", "S1", "PRIMER"]):
                    df['Semestre'] = f"Primer Semestre{anio_str}"
                elif any(x in s_name for x in ["2", "S2", "SEGUNDO"]):
                    df['Semestre'] = f"Segundo Semestre{anio_str}"
                else:
                    df['Semestre'] = f"Semestre: {sheet_name}"
                    
                combined_df = pd.concat([combined_df, df], ignore_index=True)
        except Exception as e:
            st.error(f"Error al cargar {file_path}: {e}")
            
    # Transformación y Limpieza
    if not combined_df.empty:
        # Normalizar nombres de encuestadores (Quitar espacios y pasar a mayúsculas)
        if 'encuestador' in combined_df.columns:
            combined_df['encuestador'] = combined_df['encuestador'].astype(str).str.strip().str.upper()
        
        # Asegurar que la columna 'entrevista' sea numérica
        if 'entrevista' in combined_df.columns:
            combined_df['entrevista'] = pd.to_numeric(combined_df['entrevista'], errors='coerce').fillna(0)
        
    return combined_df

def get_kpis(df):
    """
    Calcula los KPIs principales basados en el DataFrame filtrado.
    
    Args:
        df (pd.DataFrame): DataFrame filtrado.
        
    Returns:
        dict: Diccionario con los valores de los KPIs.
    """
    total_asignadas = len(df)
    encuestas_efectivas = df[df['entrevista'] == 1].shape[0]
    no_respuestas = df[df['entrevista'] == 0].shape[0]
    porcentaje_efectividad = (encuestas_efectivas / total_asignadas * 100) if total_asignadas > 0 else 0
    
    return {
        "total_asignadas": total_asignadas,
        "encuestas_efectivas": encuestas_efectivas,
        "no_respuestas": no_respuestas,
        "porcentaje_efectividad": porcentaje_efectividad
    }
