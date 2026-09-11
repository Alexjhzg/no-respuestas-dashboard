import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from src.config import COLOR_MAP


def create_temporal_chart(df: pd.DataFrame) -> go.Figure:
    """
    Genera el gráfico de líneas de evolución temporal del Porcentaje de No Respuesta entre semestres.

    Args:
        df (pd.DataFrame): DataFrame filtrado de encuestas.

    Returns:
        go.Figure: Figura de Plotly con gráfico de línea y marcadores.
    """
    if df.empty or "Semestre" not in df.columns or "entrevista" not in df.columns:
        fig = go.Figure()
        fig.update_layout(title="Sin datos suficientes para evolución temporal")
        return fig

    sem_df = df.copy()

    sem_agg = sem_df.groupby(["Semestre"]).agg(
        Total=("entrevista", "count"),
        Diligenciadas=("entrevista", lambda x: (x == 1).sum()),
        No_Diligenciadas=("entrevista", lambda x: (x == 0).sum())
    ).reset_index()

    if sem_agg.empty:
        fig = go.Figure()
        fig.update_layout(title="Sin datos suficientes para evolución temporal")
        return fig

    sem_agg["Pct_No_Respuesta"] = (sem_agg["No_Diligenciadas"] / sem_agg["Total"] * 100).round(1)

    # Orden cronológico estandarizado por semestre
    sem_order = ["Segundo Semestre 2025", "Primer Semestre 2026", "Segundo Semestre 2026"]
    present_order = [s for s in sem_order if s in sem_agg["Semestre"].values]
    for s in sem_agg["Semestre"].values:
        if s not in present_order:
            present_order.append(s)

    sem_agg["Semestre"] = pd.Categorical(sem_agg["Semestre"], categories=present_order, ordered=True)
    sem_agg = sem_agg.sort_values("Semestre")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=sem_agg["Semestre"],
            y=sem_agg["Pct_No_Respuesta"],
            mode="lines+markers+text",
            name="% No Respuesta",
            line=dict(color="#e74c3c", width=4),
            marker=dict(size=12, color="#c0392b", symbol="circle"),
            text=[f"{v}%" for v in sem_agg["Pct_No_Respuesta"]],
            textposition="top center",
            textfont=dict(size=13),
            hovertemplate="<b>%{x}</b><br>Porcentaje No Respuesta: <b>%{y}%</b><extra></extra>",
        )
    )

    fig.update_layout(
        title="Evolución del Porcentaje de No Respuesta por Semestre",
        xaxis_title="Semestre / Periodo",
        yaxis_title="% de No Respuesta",
        yaxis=dict(range=[0, min(100, max(80, sem_agg["Pct_No_Respuesta"].max() + 15))]),
        hovermode="x unified",
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig


def create_typology_chart(tipologia_counts: pd.DataFrame) -> go.Figure:
    """
    Genera el gráfico de barras por Tipología Censal (TIPO E, A, B, C).

    Args:
        tipologia_counts (pd.DataFrame): Conteo por tipología de vivienda.

    Returns:
        go.Figure: Figura de Plotly.
    """
    if tipologia_counts.empty:
        fig = go.Figure()
        fig.update_layout(title="Sin datos de tipología de vivienda")
        return fig

    fig_tipo = px.bar(
        tipologia_counts,
        x="Tipología",
        y="Cantidad",
        color="Tipología",
        title="Distribución por Tipología Censal (TIPO E, A, B, C)",
        text_auto=True,
        color_discrete_sequence=px.colors.qualitative.Safe,
    )
    return fig_tipo
