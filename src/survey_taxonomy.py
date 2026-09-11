"""
survey_taxonomy.py
Módulo de clasificación y etiquetado taxonómico de encuestas Kobo (EHM / ESCA, V1-V4, Estándar/Ampliada).
"""

import re
from typing import Dict, Any, Tuple


def detect_survey_metadata(asset_name_or_record: Any) -> Tuple[str, str, str]:
    """
    Analiza un registro, nombre de archivo o nombre de activo Kobo y determina:
    - familia_encuesta: 'EHM' o 'ESCA'
    - version_encuesta: 'V1', 'V2', 'V3', 'V4'
    - variante_encuesta: 'Ampliada' o 'Estándar'

    Args:
        asset_name_or_record: Cadena de texto o diccionario del registro/asset.

    Returns:
        Tuple[str, str, str]: (familia_encuesta, version_encuesta, variante_encuesta)
    """
    text = str(asset_name_or_record).upper()

    # 1. Deducir Familia
    if "ESCA" in text:
        familia = "ESCA"
    elif "EHM" in text:
        familia = "EHM"
    else:
        # Fallback por campos específicos en el registro
        if any(k in text for k in ["ESCA", "ACTIVIDAD_ECONOMICA", "ESTABLECIMIENTO"]):
            familia = "ESCA"
        else:
            familia = "EHM"

    # 2. Deducir Versión
    if "V4" in text or "GROUP_SH53U78" in text or "DATOS_MM111" in text:
        version = "V4"
    elif "V3" in text or "GROUP_SEGMETO_SECTOR" in text:
        version = "V3"
    elif "V2" in text or "S0/CEDULA_ENCUESTADOR" in text:
        version = "V2"
    elif "V1" in text:
        version = "V1"
    else:
        version = "V4"  # Default canonical fallback

    # 3. Deducir Variante
    if "AMPLIADA" in text:
        variante = "Ampliada"
    else:
        variante = "Estándar"

    return familia, version, variante


def enrich_record_taxonomy(record: Dict[str, Any], asset_name: str = "") -> Dict[str, Any]:
    """
    Enriquece un registro individual inyectando las claves taxonómicas:
    - 'Tipo_Encuesta' (compatibilidad): 'EHM' / 'ESCA'
    - 'Familia_Encuesta': 'EHM' / 'ESCA'
    - 'Version_Encuesta': 'V1' - 'V4'
    - 'Variante_Encuesta': 'Estándar' / 'Ampliada'

    Args:
        record (Dict[str, Any]): Registro original.
        asset_name (str): Nombre opcional del formulario de origen.

    Returns:
        Dict[str, Any]: Registro enriquecido con metadatos de taxonomía.
    """
    rec_copy = dict(record)
    sample_text = f"{asset_name} {str(rec_copy)}"
    familia, version, variante = detect_survey_metadata(sample_text)

    rec_copy["Tipo_Encuesta"] = familia
    rec_copy["Familia_Encuesta"] = familia
    rec_copy["Version_Encuesta"] = version
    rec_copy["Variante_Encuesta"] = variante

    return rec_copy
