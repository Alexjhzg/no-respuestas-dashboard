"""
tables.py
Módulo de interfaz UI para renderizado de tablas interactivas y exportación en Streamlit.
"""

import streamlit as st
import pandas as pd
from src.reports import get_planned_vs_executed_report, get_control_no_response_report
from src.formatters import format_control_short
from src.config import COLS_TO_SHOW
from src.ui.exporters import export_to_csv, export_to_excel


def render_planned_vs_executed_section(df_filtered: pd.DataFrame):
    """Renderiza la sección de Cobertura de Controles Planificados vs Levantados."""
    st.markdown("---")
    st.subheader("Cobertura de Controles Planificados (Planificados vs Levantados)")

    col_group_mode, _ = st.columns([1.5, 1])
    with col_group_mode:
        group_view = st.radio(
            "Modo de Vista de Controles:",
            options=["Juntos (Consolidado)", "Separados por Semestre"],
            index=0,
            horizontal=True,
        )

    by_sem = (group_view == "Separados por Semestre")
    df_planned_report = get_planned_vs_executed_report(df_filtered, by_semester=by_sem)

    if not df_planned_report.empty:
        total_plan = len(df_planned_report)
        levantados = len(df_planned_report[df_planned_report["Estatus"] == "Levantado"])
        pendientes = len(df_planned_report[df_planned_report["Estatus"] == "Pendiente"])
        multi_sem = (
            len(
                df_planned_report[
                    df_planned_report["Semestres Levantados"].astype(str).str.contains("Multi-Semestre", na=False)
                ]
            )
            if "Semestres Levantados" in df_planned_report.columns
            else 0
        )
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            st.metric("Planificados", total_plan)
        with col_p2:
            st.metric("Levantados", levantados)
        with col_p3:
            st.metric("Pendientes", pendientes)
        with col_p4:
            st.metric("Multi-Semestre", multi_sem)

        col_plan_filter, col_plan_search = st.columns([1, 2])
        filter_options = ["Todos", "Levantado", "Pendiente"]
        if not by_sem:
            filter_options.append("Solo Multi-Semestre")

        with col_plan_filter:
            status_opt = st.selectbox(
                "Filtrar por Estatus de Levantamiento:",
                options=filter_options,
                index=0,
            )
        with col_plan_search:
            plan_query = st.text_input(
                "Buscar por Código de Control o Municipio:",
                value="",
                placeholder="Ej: 51 o Maturín...",
            )

        df_plan_filtered = df_planned_report.copy()
        if status_opt == "Solo Multi-Semestre" and "Semestres Levantados" in df_plan_filtered.columns:
            df_plan_filtered = df_plan_filtered[
                df_plan_filtered["Semestres Levantados"].astype(str).str.contains("Multi-Semestre", na=False)
            ]
        elif status_opt != "Todos":
            df_plan_filtered = df_plan_filtered[df_plan_filtered["Estatus"] == status_opt]

        if plan_query:
            query_clean = plan_query.strip().lower()
            df_plan_filtered = df_plan_filtered[
                df_plan_filtered["Control"].astype(str).str.lower().str.contains(query_clean)
                | df_plan_filtered["Municipio"].astype(str).str.lower().str.contains(query_clean)
            ]

        col_configs = {
            "Control": st.column_config.TextColumn("Código Control"),
            "Estatus": st.column_config.TextColumn("Estado"),
            "% No Respuesta": st.column_config.NumberColumn(format="%.1f %%"),
        }
        if "Semestres Levantados" in df_plan_filtered.columns:
            col_configs["Semestres Levantados"] = st.column_config.TextColumn("Periodos Levantados")
        if "Semestre" in df_plan_filtered.columns:
            col_configs["Semestre"] = st.column_config.TextColumn("Semestre")

        st.dataframe(
            df_plan_filtered,
            width="stretch",
            hide_index=True,
            column_config=col_configs,
        )

        col_plan_exp1, col_plan_exp2 = st.columns(2)
        with col_plan_exp1:
            plan_csv = export_to_csv(df_plan_filtered)
            st.download_button(
                label="Descargar Cobertura (CSV)",
                icon=":material/download:",
                data=plan_csv,
                file_name="cobertura_controles_planificados.csv",
                mime="text/csv",
            )
        with col_plan_exp2:
            plan_excel = export_to_excel(
                df_plan_filtered, sheet_name="Cobertura_Controles"
            )
            st.download_button(
                label="Descargar Cobertura (Excel)",
                icon=":material/table_chart:",
                data=plan_excel,
                file_name="cobertura_controles_planificados.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


def render_control_no_response_section(df_filtered: pd.DataFrame):
    """Renderiza la sección de Reporte de Porcentaje de No Respuesta por Control y Semestre."""
    st.markdown("---")
    st.subheader("Reporte de Porcentaje de No Respuesta por Control y Semestre")

    df_control_report = get_control_no_response_report(df_filtered)
    if not df_control_report.empty:
        col_ctrl_search, col_ctrl_kpi = st.columns([2, 1])

        with col_ctrl_search:
            ctrl_query = st.text_input(
                "Buscar por Código de Control:", value="", placeholder="Ej: 51..."
            )
            if ctrl_query:
                df_control_report = df_control_report[
                    df_control_report["Control"].str.contains(
                        ctrl_query.strip(), case=False, na=False
                    )
                ]

        with col_ctrl_kpi:
            st.metric("Controles Evaluados", len(df_control_report))

        st.dataframe(
            df_control_report,
            width="stretch",
            hide_index=True,
            column_config={
                "% No Respuesta": st.column_config.NumberColumn(format="%.2f %%"),
            },
        )

        col_ctrl_exp1, col_ctrl_exp2 = st.columns(2)
        with col_ctrl_exp1:
            ctrl_csv = export_to_csv(df_control_report)
            st.download_button(
                label="Descargar Reporte (CSV)",
                icon=":material/download:",
                data=ctrl_csv,
                file_name="reporte_controles_no_respuesta.csv",
                mime="text/csv",
            )
        with col_ctrl_exp2:
            ctrl_excel = export_to_excel(
                df_control_report, sheet_name="Reporte_Controles"
            )
            st.download_button(
                label="Descargar Reporte (Excel)",
                icon=":material/table_chart:",
                data=ctrl_excel,
                file_name="reporte_controles_no_respuesta.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    else:
        st.info("No hay información suficiente para generar el reporte por control.")


def render_detailed_table_section(df_filtered: pd.DataFrame):
    """Renderiza la tabla de datos consolidados detallada y botones de exportación."""
    st.markdown("---")
    st.subheader("Consolidado Detallado y Exportación")

    cols_present = [
        c
        for c in (
            COLS_TO_SHOW
            + ["Semestre", "anio", "nodo", "municipio", "tipologia_vivienda"]
        )
        if c in df_filtered.columns
    ]
    df_detailed_display = df_filtered[cols_present].copy()
    if "control" in df_detailed_display.columns:
        df_detailed_display["control"] = df_detailed_display["control"].apply(format_control_short)

    st.dataframe(df_detailed_display, width="stretch", hide_index=True)

    col_exp1, col_exp2 = st.columns(2)
    with col_exp1:
        csv_data = export_to_csv(df_filtered)
        st.download_button(
            label="Descargar Consolidado (CSV)",
            icon=":material/download:",
            data=csv_data,
            file_name="consolidado_encuestas_2025_2026.csv",
            mime="text/csv",
        )

    with col_exp2:
        excel_data = export_to_excel(df_filtered, sheet_name="Consolidado")
        st.download_button(
            label="Descargar Consolidado (Excel)",
            icon=":material/table_chart:",
            data=excel_data,
            file_name="consolidado_encuestas_2025_2026.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
