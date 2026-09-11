import streamlit as st
import pandas as pd
from typing import Optional, Dict, Any, Tuple
from src.kobo_client import KoboAPIClient


@st.cache_data(ttl=600)
def fetch_cached_assets(token: str, base_url: str):
    c = KoboAPIClient(base_url=base_url, token=token)
    return c.get_assets()


def render_data_source_sidebar(client: KoboAPIClient) -> Dict[str, Any]:
    """
    Renderiza la sección del Sidebar para la selección del origen de datos Kobo.

    Args:
        client (KoboAPIClient): Cliente de la API de Kobo.

    Returns:
        Dict[str, Any]: Selección con claves 'data_source', 'survey_family', 'single_asset_uid', 'selected_asset_uids'.
    """
    st.sidebar.header("Fuente de Datos")
    data_source = st.sidebar.radio(
        "Seleccionar Origen:",
        options=[
            "Consolidado General (EHM + ESCA)",
            "Encuestas EHM (Todas las Versiones)",
            "Encuestas ESCA (Todas las Versiones)",
            "Formulario Individual",
        ],
        index=0,
    )

    selected_asset_uids = None
    single_asset_uid = None
    survey_family = "ALL"

    if data_source == "Encuestas EHM (Todas las Versiones)":
        survey_family = "EHM"
    elif data_source == "Encuestas ESCA (Todas las Versiones)":
        survey_family = "ESCA"

    try:
        assets = fetch_cached_assets(client.token, client.base_url)
        asset_options = {
            f"{a.get('name', 'Formulario')} ({a.get('uid')})": a.get("uid")
            for a in assets
        }

        if data_source == "Formulario Individual":
            if asset_options:
                selected_asset_name = st.sidebar.selectbox(
                    "Seleccionar Formulario / Asset:", list(asset_options.keys())
                )
                single_asset_uid = asset_options[selected_asset_name]
        else:
            consolidate_all = st.sidebar.checkbox(
                "Consolidar Todos los Formularios", value=True
            )
            if not consolidate_all and asset_options:
                selected_names = st.sidebar.multiselect(
                    "Seleccionar Formularios Específicos:",
                    options=list(asset_options.keys()),
                    default=list(asset_options.keys())[:2],
                )
                selected_asset_uids = [
                    asset_options[name] for name in selected_names
                ]
    except Exception as e:
        st.sidebar.error("Error al comunicarse con el servidor")

    return {
        "data_source": data_source,
        "survey_family": survey_family,
        "single_asset_uid": single_asset_uid,
        "selected_asset_uids": selected_asset_uids,
    }


def apply_global_filters(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Renderiza la sección de Filtros Globales en la barra lateral (Sidebar).
    Implementa selección implícita ("Vacío = Todos"), cascada dinámica entre campos y botón de reset.

    Args:
        df_raw (pd.DataFrame): DataFrame completo de encuestas.

    Returns:
        pd.DataFrame: DataFrame filtrado dinámicamente.
    """
    if df_raw.empty:
        return df_raw

    # Manejo de reseteo mediante session_state
    if "reset_filters_flag" in st.session_state and st.session_state["reset_filters_flag"]:
        st.session_state["flt_semestre"] = []
        st.session_state["flt_nodo"] = []
        st.session_state["flt_municipio"] = []
        st.session_state["flt_control"] = []
        st.session_state["flt_tipo"] = []
        st.session_state["flt_encuestador"] = "Todos"
        st.session_state["reset_filters_flag"] = False

    data = df_raw.copy()

    def sanitize_key(key: str, valid_options: list):
        if key in st.session_state:
            val = st.session_state[key]
            if isinstance(val, list):
                st.session_state[key] = [x for x in val if x in valid_options]
            elif isinstance(val, str):
                if val not in valid_options:
                    st.session_state[key] = valid_options[0] if valid_options else "Todos"

    st.sidebar.markdown("---")
    st.sidebar.header("Filtros Globales")

    # 1. Semestre
    semestres_canonicos = [
        "Segundo Semestre 2025",
        "Primer Semestre 2026",
    ]
    semestres_presentes = set(df_raw["Semestre"].dropna().unique()) if "Semestre" in df_raw.columns else set()
    semestres_opciones = semestres_canonicos.copy()
    for s in sorted(semestres_presentes):
        if s not in semestres_opciones and s != "Primer Semestre 2025":
            semestres_opciones.append(s)

    sanitize_key("flt_semestre", semestres_opciones)
    semestres_selected = st.sidebar.multiselect(
        "Semestre / Periodo:",
        options=semestres_opciones,
        key="flt_semestre",
        placeholder="Todos los Periodos",
    )

    if semestres_selected:
        data = data[data["Semestre"].isin(semestres_selected)]

    # 2. Nodo (Cascada a partir de data filtrado por Semestre)
    nodos_disponibles = (
        sorted([
            n for n in data["nodo"].dropna().astype(str).unique()
            if n and n not in ["N/A", "nan", "None"]
        ])
        if "nodo" in data.columns else []
    )

    sanitize_key("flt_nodo", nodos_disponibles)
    nodos_selected = st.sidebar.multiselect(
        "Nodo:",
        options=nodos_disponibles,
        key="flt_nodo",
        placeholder="Todos los Nodos",
    )

    if nodos_selected:
        data = data[data["nodo"].astype(str).isin(nodos_selected)]

    # 3. Municipio (Cascada a partir de data filtrado por Semestre + Nodo)
    municipios_disponibles = (
        sorted([
            m for m in data["municipio"].dropna().astype(str).unique()
            if m and m not in ["N/A", "nan", "None"]
        ])
        if "municipio" in data.columns else []
    )

    sanitize_key("flt_municipio", municipios_disponibles)
    municipios_selected = st.sidebar.multiselect(
        "Municipio:",
        options=municipios_disponibles,
        key="flt_municipio",
        placeholder="Todos los Municipios",
    )

    if municipios_selected:
        data = data[data["municipio"].astype(str).isin(municipios_selected)]

    # 4. Código de Control (Cascada a partir de data filtrado por Semestre + Nodo + Municipio)
    from src.data_processor import extract_control_series, format_control_short
    control_series = extract_control_series(data)
    data["_control_temp"] = control_series
    data["_control_short_temp"] = data["_control_temp"].apply(format_control_short)

    raw_controles = [
        c for c in data["_control_short_temp"].dropna().astype(str).unique()
        if c and c not in ["N/A", "nan", "None", "", "SIN_CONTROL"]
    ]

    def sort_ctrl_key(c):
        try:
            return (0, int(c))
        except ValueError:
            return (1, c)

    controles_disponibles = sorted(raw_controles, key=sort_ctrl_key)

    sanitize_key("flt_control", controles_disponibles)
    controles_selected = st.sidebar.multiselect(
        "Código de Control:",
        options=controles_disponibles,
        key="flt_control",
        placeholder="Todos los Controles",
    )

    if controles_selected:
        data = data[
            data["_control_temp"].astype(str).isin(controles_selected)
            | data["_control_short_temp"].astype(str).isin(controles_selected)
        ]

    for col_to_drop in ["_control_temp", "_control_short_temp"]:
        if col_to_drop in data.columns:
            data = data.drop(columns=[col_to_drop])

    # 5. Tipo de Encuesta
    tipos_disponibles = (
        sorted(data["Tipo_Encuesta"].dropna().unique())
        if "Tipo_Encuesta" in data.columns else []
    )

    sanitize_key("flt_tipo", tipos_disponibles)
    tipos_selected = st.sidebar.multiselect(
        "Tipo de Encuesta:",
        options=tipos_disponibles,
        key="flt_tipo",
        placeholder="Todas las Encuestas",
    )

    if tipos_selected:
        data = data[data["Tipo_Encuesta"].isin(tipos_selected)]

    # 6. Encuestador
    encuestadores_list = (
        sorted(data["encuestador"].dropna().unique())
        if "encuestador" in data.columns else []
    )

    encuestador_options = ["Todos"] + encuestadores_list
    sanitize_key("flt_encuestador", encuestador_options)
    encuestador_selected = st.sidebar.selectbox(
        "Encuestador:",
        options=encuestador_options,
        key="flt_encuestador",
    )

    if encuestador_selected != "Todos":
        data = data[data["encuestador"] == encuestador_selected]

    st.sidebar.markdown("")
    col_f1, col_f2 = st.sidebar.columns(2)
    with col_f1:
        if st.button("Limpiar", icon=":material/cleaning_services:", use_container_width=True):
            st.session_state["reset_filters_flag"] = True
            st.rerun()
    with col_f2:
        if st.button("Recargar", icon=":material/refresh:", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    return data


