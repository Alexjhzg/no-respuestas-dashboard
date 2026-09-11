"""
no_respuesta_classifier.py
Módulo independiente y reutilizable para clasificación de condición de ocupación,
detección de No Respuesta y soporte de Upcasting Multi-Versión (V1 -> V4)
basado en la especificación técnica logica_clasificacion_no_respuesta.md.
"""

import unicodedata
import re
from typing import Dict, List, Optional, Any
import pandas as pd
from .config import CONTROL_REMAPS


def normalize_text(text: Optional[str]) -> str:
    """
    Normaliza texto convirtiendo a minúsculas, descomponiendo caracteres Unicode NFD
    (eliminando acentos y diacríticos) y removiendo todo carácter que no sea a-z o 0-9.

    Args:
        text (str | None): Cadena de texto a normalizar.

    Returns:
        str: Texto normalizado alfanumérico limpio.
    """
    if not text:
        return ""
    text = str(text).lower()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"[^a-z0-9]", "", text)


def is_truthy_raw(v: Any) -> bool:
    """
    Evalúa si un valor raw representa una afirmación/valor verdadero.
    Previene errores por cadenas vacías o representaciones como 'no', '0', 'false', etc.

    Args:
        v (Any): Valor a evaluar.

    Returns:
        bool: True si el valor se considera afirmativo, False en caso contrario.
    """
    if v is None:
        return False
    vs = str(v).strip().lower()
    return vs not in ("", "no", "no_2", "no_1", "0", "false", "none")


class V1ToV2Upcaster:
    source_version = 1
    target_version = 2

    def upcast(self, record: dict) -> dict:
        res = dict(record)
        if "cedula_encuestador" in res and "S0/cedula_encuestador" not in res:
            res["S0/cedula_encuestador"] = res["cedula_encuestador"]
        if "segmento" in res and "S1/segmento" not in res:
            res["S1/segmento"] = res["segmento"]
        if "control" in res and "group_sh53u78/control" not in res:
            res["group_sh53u78/control"] = res["control"]
        return res


class V2ToV3Upcaster:
    source_version = 2
    target_version = 3

    def upcast(self, record: dict) -> dict:
        res = dict(record)
        if "S1/segmento" in res and "group_segmeto_sector/segmento" not in res:
            res["group_segmeto_sector/segmento"] = res["S1/segmento"]
        return res


class V3ToV4Upcaster:
    source_version = 3
    target_version = 4

    def upcast(self, record: dict) -> dict:
        res = dict(record)
        # Standardize main fields into V4 canonical aliases
        cond = (
            res.get("Condici_n_de_ocupaci_n/condicion_de_ocupacion")
            or res.get("condicion_de_ocupacion")
            or res.get("condicion_ocupacion")
            or res.get("v4_condicion_ocupacion")
        )
        sit = (
            res.get("Condici_n_de_ocupaci_n/situacion_vivienda")
            or res.get("situacion_vivienda")
            or res.get("situacion")
            or res.get("v4_situacion_vivienda")
        )
        nota = (
            res.get("ubicacion_final/nota")
            or res.get("no_respuesta_raw")
            or res.get("nota")
            or res.get("estatus_entrevista")
            or res.get("estatusentrevista")
        )
        ingresada = (
            res.get("Condici_n_de_ocupaci_n/ingresada")
            or res.get("ingresada")
            or res.get("v4_ingresada")
        )
        control = (
            res.get("datos_mm111/control")
            or res.get("group_sh53u78/control")
            or res.get("control")
            or res.get("v4_control")
        )
        if control and str(control).strip() in CONTROL_REMAPS:
            control = CONTROL_REMAPS[str(control).strip()]

        nodo = (
            res.get("S1/S2/nodo")
            or res.get("S1/nodo")
            or res.get("v4_nodo")
            or res.get("nodo")
        )
        municipio = (
            res.get("S1/S2/mun")
            or res.get("S1/mun")
            or res.get("S1/Ymun")
            or res.get("v4_municipio")
            or res.get("municipio")
            or res.get("mun")
        )

        res["Condici_n_de_ocupaci_n/condicion_de_ocupacion"] = cond
        res["Condici_n_de_ocupaci_n/situacion_vivienda"] = sit
        res["ubicacion_final/nota"] = nota
        res["Condici_n_de_ocupaci_n/ingresada"] = ingresada
        res["group_sh53u78/control"] = control
        res["control"] = control
        res["nodo"] = nodo
        res["municipio"] = municipio
        return res


class UpcasterChain:
    """Cadena de elevación progresiva de esquemas (Upcasting Chain V1 -> V4)."""
    CANONICAL_VERSION = 4

    def __init__(self):
        self.upcasters = [
            V1ToV2Upcaster(),
            V2ToV3Upcaster(),
            V3ToV4Upcaster()
        ]

    def upcast_record(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return payload
        record = dict(payload)
        for upcaster in self.upcasters:
            record = upcaster.upcast(record)
        return record


from .survey_taxonomy import enrich_record_taxonomy


def upcast_record_to_v4(payload: Dict[str, Any], asset_name: str = "") -> Dict[str, Any]:
    """
    Eleva cualquier registro de encuestas (V1, V2, V3) a la estructura canónica V4 y enriquece la taxonomía.

    Args:
        payload (Dict[str, Any]): Registro en formato diccionario.
        asset_name (str): Nombre del formulario o archivo de origen.

    Returns:
        Dict[str, Any]: Registro normalizado a esquema V4 con metadatos taxonómicos.
    """
    chain = UpcasterChain()
    upcasted = chain.upcast_record(payload)
    return enrich_record_taxonomy(upcasted, asset_name=asset_name)


def classify_housing_state(situacion: str, condicion: str = "") -> str:
    """
    Clasifica la vivienda en una de las 4 tipologías censales según su condición y situación:
    - TIPO E: Totalmente Encuestada (Efectiva)
    - TIPO A: Ocupada sin Entrevista (No Respuesta por ausencia, rechazo, etc.)
    - TIPO B: Desocupada Habitable / Uso Ocasional / En Construcción
    - TIPO C: No Residencial / Demolida / Comercial u Otros Usos
    - NO DEFINIDO: Cuando no se puede determinar la clasificación.

    Args:
        situacion (str): Situación detallada de la vivienda o estatus.
        condicion (str): Condición general de ocupación.

    Returns:
        str: Código de tipología ('TIPO E', 'TIPO A', 'TIPO B', 'TIPO C', 'NO DEFINIDO').
    """
    sit = normalize_text(situacion)
    cond = normalize_text(condicion)
    norm = sit or cond

    if not norm:
        return "NO DEFINIDO"

    # 1. TOTALMENTE ENCUESTADA (TIPO E) - Respuesta Efectiva Completa
    if (
        cond == "ocupadaconocupantespresentes"
        or sit == "ocupadaconocupantespresentes"
        or "totalmenteencuestad" in sit
        or sit in ["te", "totalmenteencuestada"]
    ):
        return "TIPO E"

    # 2. TIPO A - Vivienda Ocupada Sin Entrevista (No Respuesta)
    if cond == "ocupadasconocupantesausentes" or sit in [
        "nadieenvivienda",
        "ausentetemporalmente",
        "rehusoentrevista",
        "otroausentes",
        "oa",
        "at",
        "rz",
        "ic",
        "no",
        "nt",
        "in",
        "se",
    ]:
        return "TIPO A"

    if any(
        k in sit
        for k in [
            "nocalificad",
            "menor",
            "nino",
            "ebriedad",
            "enferm",
            "discapacidad",
            "incapacitad",
            "noatiende",
            "incompleta",
            "sinentrevista",
            "rehuso",
            "rechaz",
            "ocupanteausente",
            "ausentetemporal",
        ]
    ):
        return "TIPO A"

    # 3. TIPO B - Vivienda Desocupada Habitable / Uso Ocasional / En Construcción
    if cond == "desocupada" or norm:
        if sit in [
            "desocupadaestadoregular",
            "inadecuadaeluso",
            "construyendose",
            "temporalmenteennegocio",
            "usovacacional",
            "usovacasional",
            "co",
            "vo",
            "vd",
            "uv",
            "iu",
            "tn",
        ]:
            return "TIPO B"
        if any(
            k in sit
            for k in [
                "desocupad",
                "inadecuada",
                "construc",
                "temporalmenteennegocio",
                "usovacacional",
                "usoocacional",
            ]
        ):
            return "TIPO B"

    # 4. TIPO C - Vivienda Desocupada No Residencial / Demolida / Comercio u Otros Usos
    if sit in [
        "demolida",
        "negocioalmacenpermanente",
        "consolidada",
        "otrodesocupada",
        "otro",
        "de",
        "ml",
        "np",
        "ne",
        "sl",
        "ot",
        "os",
    ]:
        return "TIPO C"

    if any(
        k in sit
        for k in [
            "demolid",
            "negocio",
            "almacen",
            "consolidada",
            "ferreteria",
            "autolavado",
            "comercio",
            "taller",
            "iglesia",
            "otro",
            "mal-listado",
            "mallistado",
            "noexiste",
        ]
    ):
        return "TIPO C"

    return "TIPO C" if cond == "desocupada" else "NO DEFINIDO"


def process_kobo_record(raw_record: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa un registro individual de cualquier versión de Kobo y devuelve su estado y tipología.

    Args:
        raw_record (Dict[str, Any]): Registro en bruto.

    Returns:
        Dict[str, Any]: Diccionario con 'no_respuesta_raw', 'no_respuesta', 'tipologia_vivienda', 'es_efectiva'.
    """
    record = upcast_record_to_v4(raw_record)

    nota_raw = record.get("ubicacion_final/nota")
    sit_raw = record.get("Condici_n_de_ocupaci_n/situacion_vivienda")
    cond_raw = record.get("Condici_n_de_ocupaci_n/condicion_de_ocupacion")

    no_respuesta = is_truthy_raw(nota_raw) if nota_raw is not None else False
    tipologia = classify_housing_state(
        situacion=sit_raw or nota_raw or "", condicion=cond_raw or ""
    )

    return {
        "no_respuesta_raw": nota_raw,
        "no_respuesta": no_respuesta,
        "tipologia_vivienda": tipologia,
        "es_efectiva": tipologia == "TIPO E",
    }


def extract_encuestador_name_series(dframe: pd.DataFrame) -> pd.Series:
    """
    Coalesce todas las posibles variantes de campos de encuestador (nombre, apellido, cédula)
    en una representación legible: 'Nombre Apellido (Cédula)' o 'Nombre Apellido' o 'Cédula'.
    """
    if dframe.empty:
        return pd.Series(dtype=str)

    def get_col(c):
        if c in dframe.columns:
            return dframe[c]
        return pd.Series([None] * len(dframe), index=dframe.index)

    n1 = get_col("S0/s0_nombreapellido")
    n2 = get_col("S0/_xm_s0_nombreapellido")
    n3 = get_col("nombre_encuestador")
    n4 = get_col("v4_encuestador_nombre")
    n5 = get_col("encuestador_nombre")

    c1 = get_col("encuestador")
    c2 = get_col("S0/cedula_encuestador")
    c3 = get_col("cedula_encuestador")
    c4 = get_col("v4_encuestador")

    nombres = n1.fillna(n2).fillna(n3).fillna(n4).fillna(n5)
    cedulas = c1.fillna(c2).fillna(c3).fillna(c4)

    results = []
    for nom, ced in zip(nombres, cedulas):
        nom_str = str(nom).strip() if pd.notnull(nom) and str(nom).strip() not in ("nan", "None", "") else ""
        ced_str = str(ced).strip() if pd.notnull(ced) and str(ced).strip() not in ("nan", "None", "") else ""

        if nom_str:
            results.append(nom_str.title())
        elif ced_str:
            results.append(f"Cédula {ced_str}")
        else:
            results.append("NO ESPECIFICADO")

    return pd.Series(results, index=dframe.index)


def apply_housing_classification_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica la clasificación jerárquica de vivienda a todo un DataFrame de Pandas.

    Añade las columnas:
    - `tipologia_vivienda`
    - `es_efectiva`
    - `encuestador` (con Nombre Completo y Cédula)

    Args:
        df (pd.DataFrame): DataFrame de encuestas.

    Returns:
        pd.DataFrame: DataFrame enriquecido con las columnas de clasificación.
    """
    if df.empty:
        return df

    df_out = df.copy()

    def row_classifier(row):
        sit = str(
            row.get("Condici_n_de_ocupaci_n/situacion_vivienda")
            or row.get("estatusentrevista")
            or row.get("ubicacion_final/nota")
            or ""
        )
        cond = str(
            row.get("Condici_n_de_ocupaci_n/condicion_de_ocupacion")
            or row.get("condicion_de_ocupacion")
            or ""
        )

        # Si se dispone de 'entrevista' numérica (1=Efectiva, 0=No Respuesta)
        if "entrevista" in row and pd.notnull(row["entrevista"]):
            if row["entrevista"] == 1 and not sit:
                sit = "TE"

        tipologia = classify_housing_state(sit, cond)
        return pd.Series(
            {
                "tipologia_vivienda": tipologia,
                "es_efectiva": tipologia == "TIPO E",
            }
        )

    classification_results = df_out.apply(row_classifier, axis=1)
    df_out["tipologia_vivienda"] = classification_results["tipologia_vivienda"]
    df_out["es_efectiva"] = classification_results["es_efectiva"]
    df_out["entrevista"] = df_out["es_efectiva"].astype(int)
    df_out["encuestador"] = extract_encuestador_name_series(df_out)

    # Asegurar metadatos taxonómicos por encuesta (Familia, Versión, Variante)
    from .survey_taxonomy import detect_survey_metadata
    if "Familia_Encuesta" not in df_out.columns or df_out["Familia_Encuesta"].isnull().any():
        def infer_tax(row):
            asset_name = str(row.get("_asset_name") or row.get("_xform_id_string") or "")
            if not asset_name.strip():
                asset_name = str(row.to_dict())
            fam, ver, var = detect_survey_metadata(asset_name)
            return pd.Series({"Familia_Encuesta": fam, "Version_Encuesta": ver, "Variante_Encuesta": var, "Tipo_Encuesta": fam})

        tax_df = df_out.apply(infer_tax, axis=1)
        for col in ["Familia_Encuesta", "Version_Encuesta", "Variante_Encuesta", "Tipo_Encuesta"]:
            if col not in df_out.columns:
                df_out[col] = tax_df[col]
            else:
                df_out[col] = df_out[col].fillna(tax_df[col])

    return df_out
