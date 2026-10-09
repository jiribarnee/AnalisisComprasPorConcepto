"""
alerts.py

Detecta automáticamente situaciones relevantes ENTRE DOS PERÍODOS
ESPECÍFICOS, elegidos por el usuario en el selector del dashboard (no
necesariamente el primero/último de toda la serie cargada).

Recibe la tabla ya recalculada por core.comparator.calcular_metricas_par
para ese par, así que toda la lógica acá es simple: mirar ESTADO,
DIFERENCIA y VARIACION_PCT ya calculados para ese par puntual.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from core.comparator import ESTADO_DISCONTINUADO, ESTADO_NUEVO

NIVEL_ALTO = "alto"
NIVEL_MEDIO = "medio"
NIVEL_POSITIVO = "positivo"


@dataclass
class Alerta:
    icono: str
    titulo: str
    detalle: str
    nivel: str


@dataclass
class UmbralesAlertas:
    variacion_alta_pct: float = 30.0
    variacion_disminucion_pct: float = -30.0
    monto_relevante_nueva: float = 500_000.0
    monto_relevante_discontinuada: float = 500_000.0
    top_n: int = 5


def generar_alertas(
    tabla_vista: pd.DataFrame,
    label_base: str,
    label_comparado: str,
    umbrales: UmbralesAlertas | None = None,
) -> list[Alerta]:
    """
    tabla_vista: tabla ya recalculada (ver comparator.calcular_metricas_par)
    para el par (label_base, label_comparado) que el usuario eligió.
    """
    umbrales = umbrales or UmbralesAlertas()
    col_base = f"TOTAL_{label_base}"
    col_comparado = f"TOTAL_{label_comparado}"

    alertas: list[Alerta] = []
    alertas += _alertas_aumentos(tabla_vista, umbrales, label_base, label_comparado)
    alertas += _alertas_disminuciones(tabla_vista, umbrales, label_base, label_comparado)
    alertas += _alertas_nuevas(tabla_vista, col_comparado, umbrales)
    alertas += _alertas_discontinuadas(tabla_vista, col_base, umbrales)

    return alertas


def _alertas_aumentos(tabla, umbrales, label_base, label_comparado) -> list[Alerta]:
    filtro = (tabla["ESTADO"] == "EXISTENTE") & (tabla["VARIACION_PCT"] >= umbrales.variacion_alta_pct)
    subset = tabla[filtro].sort_values("VARIACION_PCT", ascending=False).head(umbrales.top_n)

    return [
        Alerta(
            icono="🔴",
            titulo=f"Aumento fuerte: {row['DENO']}",
            detalle=f"+{row['VARIACION_PCT']:.1f}% de {label_base} a {label_comparado}",
            nivel=NIVEL_ALTO,
        )
        for _, row in subset.iterrows()
    ]


def _alertas_disminuciones(tabla, umbrales, label_base, label_comparado) -> list[Alerta]:
    filtro = (tabla["ESTADO"] == "EXISTENTE") & (tabla["VARIACION_PCT"] <= umbrales.variacion_disminucion_pct)
    subset = tabla[filtro].sort_values("VARIACION_PCT", ascending=True).head(umbrales.top_n)

    return [
        Alerta(
            icono="🟢",
            titulo=f"Disminución importante: {row['DENO']}",
            detalle=f"{row['VARIACION_PCT']:.1f}% de {label_base} a {label_comparado}",
            nivel=NIVEL_POSITIVO,
        )
        for _, row in subset.iterrows()
    ]


def _alertas_nuevas(tabla, col_comparado, umbrales) -> list[Alerta]:
    filtro = (tabla["ESTADO"] == ESTADO_NUEVO) & (tabla[col_comparado] >= umbrales.monto_relevante_nueva)
    subset = tabla[filtro].sort_values(col_comparado, ascending=False).head(umbrales.top_n)

    return [
        Alerta(
            icono="📦",
            titulo=f"Categoría nueva: {row['DENO']}",
            detalle=f"Sin gasto en el período base, ${row[col_comparado]:,.0f} en el período comparado",
            nivel=NIVEL_MEDIO,
        )
        for _, row in subset.iterrows()
    ]


def _alertas_discontinuadas(tabla, col_base, umbrales) -> list[Alerta]:
    filtro = (tabla["ESTADO"] == ESTADO_DISCONTINUADO) & (tabla[col_base] >= umbrales.monto_relevante_discontinuada)
    subset = tabla[filtro].sort_values(col_base, ascending=False).head(umbrales.top_n)

    return [
        Alerta(
            icono="📉",
            titulo=f"Categoría discontinuada: {row['DENO']}",
            detalle=f"Tenía ${row[col_base]:,.0f} en el período base, sin gasto en el período comparado",
            nivel=NIVEL_ALTO,
        )
        for _, row in subset.iterrows()
    ]
