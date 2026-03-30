import streamlit as st
import plotly.express as px
import pandas as pd
from src.config import PAGE_TITLE, LAYOUT, COLS_TO_SHOW, COLOR_MAP, COLOR_SEQUENCE, STATUS_MAPPING
from src.data_processor import load_and_clean_data, get_kpis

# Configuración de la página
st.set_page_config(page_title=PAGE_TITLE, layout=LAYOUT)

# --- Carga de datos ---
@st.cache_data
def get_cached_data():
    return load_and_clean_data()

data = get_cached_data()

if data.empty:
    st.warning("No se pudieron cargar datos. Asegúrese de que los archivos .xlsx estén en la carpeta /data.")
else:
    # --- Sidebar - Filtros Globales ---
    st.sidebar.header("Filtros Globales")
    
    tipos_selected = st.sidebar.multiselect(
        "Tipo de Encuesta", 
        options=data['Tipo_Encuesta'].unique(), 
        default=list(data['Tipo_Encuesta'].unique())
    )
    
    semestres_selected = st.sidebar.multiselect(
        "Semestre", 
        options=data['Semestre'].unique(), 
        default=list(data['Semestre'].unique())
    )
    
    encuestadores_list = sorted(data['encuestador'].dropna().unique())
    encuestador_selected = st.sidebar.selectbox("Seleccionar Encuestador", options=["Todos"] + encuestadores_list)

    df_filtered = data[
        (data['Tipo_Encuesta'].isin(tipos_selected)) &
        (data['Semestre'].isin(semestres_selected))
    ]
    
    if encuestador_selected != "Todos":
        df_filtered = df_filtered[df_filtered['encuestador'] == encuestador_selected]

    st.title(PAGE_TITLE)
    st.markdown("---")

    # --- KPIs ---
    kpis = get_kpis(df_filtered)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Asignadas", f"{kpis['total_asignadas']:,}")
    with col2:
        st.metric("Encuestas Efectivas", f"{kpis['encuestas_efectivas']:,}")
    with col3:
        st.metric("No Respuestas", f"{kpis['no_respuestas']:,}", delta_color="inverse")
    with col4:
        st.metric("Porcentaje Efectividad", f"{kpis['porcentaje_efectividad']:.2f} %")

    st.markdown("---")

    # --- Visualizaciones ---
    st.subheader("Rendimiento por Encuestador")
    bar_data = df_filtered.copy()
    bar_data['Estatus_Resumen'] = bar_data['entrevista'].map({1: 'Efectivas', 0: 'No Respuestas'})
    
    # Agrupar datos para que las etiquetas de texto muestren el total correcto
    bar_data_grouped = bar_data.groupby(['encuestador', 'Estatus_Resumen']).size().reset_index(name='Cantidad')
    
    fig_bar = px.bar(
        bar_data_grouped, 
        y='encuestador', 
        x='Cantidad',
        color='Estatus_Resumen',
        orientation='h',
        title="Efectivas vs No Respuestas",
        labels={'encuestador': 'Nombre del Encuestador', 'Cantidad': 'Cantidad de Encuestas'},
        color_discrete_map=COLOR_MAP,
        height=min(400 + len(bar_data_grouped['encuestador'].unique()) * 20, 1000), # Altura dinámica
        text_auto=True
    )
    fig_bar.update_layout(
        barmode='stack', 
        yaxis={'categoryorder':'total ascending'},
        uniformtext_minsize=8, 
        uniformtext_mode='hide'
    )
    fig_bar.update_traces(textposition='inside', textangle=0)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("Análisis de No Respuestas")
    df_no_resp = df_filtered[df_filtered['entrevista'] == 0].copy()
    
    if not df_no_resp.empty and 'estatusentrevista' in df_no_resp.columns:
        # Apply mapping to show both code and full name (e.g. "OA - Ocupante Ausente")
        df_no_resp['estatusentrevista'] = df_no_resp['estatusentrevista'].apply(
            lambda x: f"{x} - {STATUS_MAPPING[x]}" if x in STATUS_MAPPING else x
        )
        
        col_chart, col_totals = st.columns([1.5, 1])
        
        with col_chart:
            fig_donut = px.pie(
                df_no_resp, 
                names='estatusentrevista', 
                hole=0.6,
                title="Distribución de Motivos",
                color_discrete_sequence=COLOR_SEQUENCE,
                height=450
            )
            fig_donut.update_layout(
                margin=dict(t=40, b=90, l=120, r=30),
                legend=dict(
                    orientation="v", 
                    yanchor="middle", 
                    y=0.5, 
                    xanchor="right", 
                    x=-0.1,
                    valign="middle"
                )
            )
            st.plotly_chart(fig_donut, use_container_width=True)
        
        with col_totals:
            st.markdown("<br>", unsafe_allow_html=True) # Align with chart title
            # Gran Total de No Respuestas
            total_no_resp = df_no_resp.shape[0]
            st.markdown(
                f"""
                <div style="
                    background-color: #34495e;
                    padding: 8px;
                    border-radius: 6px;
                    text-align: center;
                    color: white;
                    margin-bottom: 15px;
                    box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
                ">
                    <div style="font-size: 0.7rem; font-weight: bold; text-transform: uppercase; opacity: 0.9;">
                        Total General de No Respuestas
                    </div>
                    <div style="font-size: 1.6rem; font-weight: bold;">
                        {total_no_resp}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            st.markdown("##### Desglose por Motivo:")
            status_counts = df_no_resp['estatusentrevista'].value_counts()
            
            # Use 3 columns inside the totals container
            sub_cols = st.columns(3)
            for i, (status, count) in enumerate(status_counts.items()):
                color = COLOR_SEQUENCE[i % len(COLOR_SEQUENCE)]
                with sub_cols[i % 3]:
                    st.markdown(
                        f"""
                        <div style="
                            background-color: {color};
                            padding: 4px 6px;
                            border-radius: 4px;
                            text-align: center;
                            color: white;
                            margin-bottom: 6px;
                            box-shadow: 1px 1px 2px rgba(0,0,0,0.1);
                        ">
                            <div style="font-size: 0.55rem; font-weight: bold; text-transform: uppercase; margin-bottom: 1px; opacity: 0.9; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{status}">
                                {status}
                            </div>
                            <div style="font-size: 1.0rem; font-weight: bold;">
                                {count}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
    else:
        st.info("No hay datos de 'No Respuesta' para mostrar.")

    # --- Tabla Detallada ---
    st.markdown("---")
    st.subheader("Detalle de Registros Filtrados")
    cols_present = [c for c in COLS_TO_SHOW if c in df_filtered.columns]
    st.dataframe(df_filtered[cols_present], width='stretch', hide_index=True) # Fixed deprecation warning

# Instrucciones en el Sidebar
st.sidebar.markdown("---")
st.sidebar.info("""
**Instrucciones de ejecución:**
1. Instale las librerías: `pip install -r requirements.txt`
2. Ejecute: `streamlit run dashboard.py`
""")
