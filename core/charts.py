"""
charts.py

Genera los gráficos de Plotly. El gráfico de "gasto total por período"
siempre muestra TODOS los períodos cargados (2 a 12). Los demás
gráficos (top categorías, aumentos, disminuciones, distribución por
estado) se calculan para el PAR de períodos que el usuario eligió en
el selector del dashboard.
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

COLOR_FONDO = "#ffffff"
COLOR_TEXTO = "#1f2430"
COLOR_GRILLA = "#e7e9ee"
COLOR_POSITIVO = "#1f9d55"
COLOR_NEGATIVO = "#e0322c"
COLOR_ACENTO = "#e0322c"
COLOR_SECUNDARIO = "#5b6472"
COLOR_AZUL = "#1c8fd6"


def _layout_base(titulo: str) -> dict:
    return dict(
        title=dict(text=titulo, font=dict(size=15, color=COLOR_TEXTO), x=0.02),
        paper_bgcolor=COLOR_FONDO,
        plot_bgcolor=COLOR_FONDO,
        font=dict(color=COLOR_TEXTO, family="Segoe UI, sans-serif", size=12),
        margin=dict(l=50, r=30, t=50, b=40),
        xaxis=dict(gridcolor=COLOR_GRILLA, zerolinecolor=COLOR_GRILLA),
        yaxis=dict(gridcolor=COLOR_GRILLA, zerolinecolor=COLOR_GRILLA),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=COLOR_TEXTO)),
        height=340,
    )


PALETA_LINEAS = ["#e0322c", "#1c8fd6", "#1f9d55", "#f5b942", "#7c4dff", "#00b8a9", "#e0668f", "#8d99ae"]


def grafico_gasto_total(
    labels: list[str], gastos_por_periodo: dict[str, float], label_base: str, label_comparado: str
) -> go.Figure:
    """
    Gasto total de TODOS los períodos cargados (2 a 12 barras). Las dos
    barras del par elegido en el selector se resaltan con color (azul
    la base, verde/rojo la comparada según suba o baje); el resto queda
    en gris neutro como contexto.
    """
    valores = [gastos_por_periodo[label] for label in labels]

    valor_base = gastos_por_periodo[label_base]
    valor_comparado = gastos_por_periodo[label_comparado]
    color_comparado = COLOR_POSITIVO if valor_comparado >= valor_base else COLOR_NEGATIVO

    colores = []
    for label in labels:
        if label == label_comparado:
            colores.append(color_comparado)
        elif label == label_base:
            colores.append(COLOR_AZUL)
        else:
            colores.append(COLOR_SECUNDARIO)

    # Con muchos períodos las etiquetas se ponen en vertical (con el monto
    # completo) para que no se encimen.
    muchos = len(labels) > 4
    textos = [f"${v:,.0f}" for v in valores]
    estilo_txt = dict(textangle=-90, constraintext="none", textfont=dict(size=9, color=COLOR_TEXTO)) if muchos else {}
    techo = max(valores + [0]) * (1.42 if muchos else 1.1)

    fig = go.Figure(
        data=[
            go.Bar(
                x=labels,
                y=valores,
                marker_color=colores,
                text=textos,
                textposition="outside",
                **estilo_txt,
            )
        ]
    )
    fig.update_layout(**_layout_base("Gasto total por período"))
    fig.update_layout(yaxis=dict(gridcolor=COLOR_GRILLA, zerolinecolor=COLOR_GRILLA, rangemode="tozero", range=[0, techo]))
    return fig


def grafico_top_categorias(tabla_vista: pd.DataFrame, label_comparado: str, n: int = 10) -> go.Figure:
    """Top N categorías por gasto en el período COMPARADO elegido por el usuario."""
    col = f"TOTAL_{label_comparado}"
    top = tabla_vista.nlargest(n, col).sort_values(col)

    fig = go.Figure(
        data=[
            go.Bar(
                x=top[col],
                y=top["DENO"],
                orientation="h",
                marker_color=COLOR_AZUL,
                text=[f"${v:,.0f}" for v in top[col]],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(**_layout_base(f"Top {n} categorías por gasto ({label_comparado})"))
    fig.update_layout(height=max(340, n * 34))
    return fig


def grafico_top_aumentos(tabla_vista: pd.DataFrame, label_base: str, label_comparado: str, n: int = 10) -> go.Figure:
    subset = tabla_vista[tabla_vista["ESTADO"] == "EXISTENTE"].nlargest(n, "VARIACION_PCT")
    subset = subset.sort_values("VARIACION_PCT")

    fig = go.Figure(
        data=[
            go.Bar(
                x=subset["VARIACION_PCT"],
                y=subset["DENO"],
                orientation="h",
                marker_color=COLOR_NEGATIVO,
                text=[f"+{v:.1f}%" for v in subset["VARIACION_PCT"]],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(**_layout_base(f"Top {n} aumentos: {label_base} → {label_comparado}"))
    fig.update_layout(height=max(340, n * 34))
    return fig


def grafico_top_disminuciones(tabla_vista: pd.DataFrame, label_base: str, label_comparado: str, n: int = 10) -> go.Figure:
    subset = tabla_vista[tabla_vista["ESTADO"] == "EXISTENTE"].nsmallest(n, "VARIACION_PCT")
    subset = subset.sort_values("VARIACION_PCT", ascending=False)

    fig = go.Figure(
        data=[
            go.Bar(
                x=subset["VARIACION_PCT"],
                y=subset["DENO"],
                orientation="h",
                marker_color=COLOR_POSITIVO,
                text=[f"{v:.1f}%" for v in subset["VARIACION_PCT"]],
                textposition="outside",
            )
        ]
    )
    fig.update_layout(**_layout_base(f"Top {n} disminuciones: {label_base} → {label_comparado}"))
    fig.update_layout(height=max(340, n * 34))
    return fig


def grafico_distribucion_estado(tabla_vista: pd.DataFrame) -> go.Figure:
    conteo = tabla_vista["ESTADO"].value_counts()

    etiquetas = {"EXISTENTE": "Existentes", "NUEVO": "Nuevas", "DISCONTINUADO": "Discontinuadas"}
    colores = {"EXISTENTE": COLOR_AZUL, "NUEVO": COLOR_POSITIVO, "DISCONTINUADO": COLOR_NEGATIVO}

    labels = [etiquetas.get(k, k) for k in conteo.index]
    values = list(conteo.values)
    colors = [colores.get(k, COLOR_SECUNDARIO) for k in conteo.index]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=colors),
                hole=0.55,
                textinfo="label+value",
                textfont=dict(color=COLOR_TEXTO),
            )
        ]
    )
    fig.update_layout(**_layout_base("Categorías por estado (par seleccionado)"))
    fig.update_layout(showlegend=False)
    return fig


def generar_todos_los_graficos(
    labels: list[str],
    gastos_por_periodo: dict[str, float],
    tabla_vista: pd.DataFrame,
    label_base: str,
    label_comparado: str,
) -> dict[str, go.Figure]:
    return {
        "gasto_total": grafico_gasto_total(labels, gastos_por_periodo, label_base, label_comparado),
        "top_categorias": grafico_top_categorias(tabla_vista, label_comparado),
        "top_aumentos": grafico_top_aumentos(tabla_vista, label_base, label_comparado),
        "top_disminuciones": grafico_top_disminuciones(tabla_vista, label_base, label_comparado),
        "distribucion_estado": grafico_distribucion_estado(tabla_vista),
    }
