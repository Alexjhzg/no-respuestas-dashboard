import streamlit as st
import pandas as pd
from src.config import (
    PAGE_TITLE,
    LAYOUT,
    DEFAULT_KOBO_BASE_URL,
    DEFAULT_KOBO_API_TOKEN,
)
from src.data_processor import (
    load_and_clean_data,
    load_consolidated_dataset,
)
from src.reports import get_kpis
from src.kobo_client import KoboAPIClient
from src.ui.charts import (
    create_temporal_chart,
    create_typology_chart,
)
from src.ui.filters import (
    render_data_source_sidebar,
    apply_global_filters,
)
from src.ui.tables import (
    render_planned_vs_executed_section,
    render_control_no_response_section,
    render_detailed_table_section,
)

# Configuración de la página
st.set_page_config(page_title=PAGE_TITLE, layout=LAYOUT)

st.title(PAGE_TITLE)
st.caption("Consolidación Anual (2025) y Primer Semestre (2026) con Soporte Multi-Versión Kobo (V1 → V4)")

# --- Sidebar: Selección de Origen de Datos ---
kobo_token = DEFAULT_KOBO_API_TOKEN
kobo_url = DEFAULT_KOBO_BASE_URL
client = KoboAPIClient(base_url=kobo_url, token=kobo_token)

source_config = render_data_source_sidebar(client)
data_source = source_config["data_source"]
survey_family = source_config.get("survey_family", "ALL")
single_asset_uid = source_config["single_asset_uid"]
selected_asset_uids = source_config["selected_asset_uids"]


# --- Carga de datos con Caché ---
@st.cache_data(ttl=600)
def fetch_dashboard_data(mode, family, single_uid, multi_uids, token, url):
    if mode == "Formulario Individual":
        return load_and_clean_data(
            source_type="kobo",
            kobo_asset_uid=single_uid,
            kobo_token=token,
            kobo_base_url=url,
        )
    else:
        return load_consolidated_dataset(
            source_type="kobo",
            kobo_asset_uids=multi_uids,
            kobo_token=token,
            kobo_base_url=url,
            auto_detect_all=(multi_uids is None),
            survey_family=family,
        )


data = fetch_dashboard_data(
    data_source, survey_family, single_asset_uid, selected_asset_uids, kobo_token, kobo_url
)

if data.empty:
    st.warning(
        "No se obtuvieron registros. Verifique la selección de fuente o los parámetros de conexión."
    )
else:
    # --- Sidebar - Filtros Globales ---
    df_filtered = apply_global_filters(data)

    st.markdown("---")

    # --- KPIs Principales ---
    kpis = get_kpis(df_filtered)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Controles Evaluados", f"{kpis['controles_evaluados']:,}")
    with col2:
        st.metric(
            "Porcentaje de No Respuesta",
            f"{kpis['porcentaje_no_respuesta']:.2f} %",
            delta_color="inverse",
        )

    st.markdown("---")

    # --- Comparativa Temporal por Semestre ---
    if "Semestre" in df_filtered.columns and "entrevista" in df_filtered.columns:
        st.subheader("Evolución y Comparativa Temporal (2025 - 2026)")
        fig_sem = create_temporal_chart(df_filtered)
        st.plotly_chart(fig_sem, use_container_width=True)
        st.markdown("---")

    # --- Clasificación por Tipología de Vivienda ---
    if "tipologia_vivienda" in df_filtered.columns:
        st.subheader("Clasificación por Tipología de Vivienda (Esquema V1 → V4)")
        col_tipo_chart, col_tipo_summary = st.columns([1.5, 1])

        tipologia_counts = df_filtered["tipologia_vivienda"].value_counts().reset_index()
        tipologia_counts.columns = ["Tipología", "Cantidad"]

        with col_tipo_chart:
            fig_tipo = create_typology_chart(tipologia_counts)
            st.plotly_chart(fig_tipo, use_container_width=True)

        with col_tipo_summary:
            st.markdown("##### Desglose de Tipologías:")
            st.dataframe(tipologia_counts, hide_index=True)

        st.markdown("---")

    # --- Cobertura de Controles Planificados vs Levantados ---
    render_planned_vs_executed_section(df_filtered)

    # --- Reporte por Control y Semestre ---
    render_control_no_response_section(df_filtered)

    # --- Exportación y Tabla Detallada ---
    render_detailed_table_section(df_filtered)

# Información en el Sidebar
st.sidebar.markdown("---")
st.sidebar.info("""
**Normalización por Encuesta:**
- **Encuestas EHM**: Filtra y normaliza únicamente encuestas EHM (V1 a V4, Estándar y Ampliada).
- **Encuestas ESCA**: Filtra y normaliza únicamente encuestas ESCA (V1 a V4, Estándar y Ampliada).
- **Consolidado General (EHM + ESCA)**: Combina y normaliza todas las encuestas de 2025 y 2026.
- **Formulario Individual**: Analiza un formulario específico en tiempo real.
""")
