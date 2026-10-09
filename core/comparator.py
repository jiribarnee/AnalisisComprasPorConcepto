"""
comparator.py

Compara ENTRE 2 Y 12 períodos de gastos, agrupando por categoría
(DENO/CODIGO). La variación principal (DIFERENCIA/VARIACION_PCT) se
calcula entre el PRIMER y el ÚLTIMO período de la lista, en el orden
en que el usuario los cargó — pensado para usarse con hasta 12 meses
consecutivos, pero funciona igual con solo 2.

"Categoría nueva" = no tenía gasto en el primer período, sí en el
último. "Discontinuada" = tenía gasto en el primer período, no en el
último. Categorías con actividad intermitente en el medio se
consideran "EXISTENTE" (están presentes en las puntas).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce

import pandas as pd

from core.calculations import variacion_absoluta, variacion_porcentual
from core.excel_processor import COLUMNAS_COMPONENTES, LoadedPeriod

ESTADO_NUEVO = "NUEVO"
ESTADO_DISCONTINUADO = "DISCONTINUADO"
ESTADO_EXISTENTE = "EXISTENTE"

MIN_PERIODOS = 2
MAX_PERIODOS = 12


@dataclass
class ComparisonResult:
    """Resultado completo de comparar entre 2 y 12 períodos."""

    labels: list[str]            # en el orden cronológico dado por el usuario
    tabla: pd.DataFrame          # una fila por categoría, con una columna TOTAL_<label> por período
    resumen: dict
    columnas_componentes: list[str]  # columnas de impuestos presentes en TODOS los períodos

    @property
    def label_primero(self) -> str:
        return self.labels[0]

    @property
    def label_ultimo(self) -> str:
        return self.labels[-1]

    @property
    def label_penultimo(self) -> str | None:
        return self.labels[-2] if len(self.labels) >= 2 else None


def comparar_periodos(periodos: list[LoadedPeriod]) -> ComparisonResult:
    """Punto de entrada principal: compara entre 2 y 12 períodos por categoría de gasto."""
    if len(periodos) < MIN_PERIODOS:
        raise ValueError(f"Se necesitan al menos {MIN_PERIODOS} períodos para comparar.")
    if len(periodos) > MAX_PERIODOS:
        raise ValueError(f"No se pueden comparar más de {MAX_PERIODOS} períodos a la vez.")

    labels = [p.label for p in periodos]

    componentes_por_periodo = [
        set(c for c in COLUMNAS_COMPONENTES if c in p.dataframe.columns) for p in periodos
    ]
    componentes_comunes = [
        c for c in COLUMNAS_COMPONENTES if all(c in s for s in componentes_por_periodo)
    ]

    aggs = [_agrupar_por_categoria(p.dataframe, componentes_comunes) for p in periodos]
    tabla = _combinar(aggs, labels, componentes_comunes)
    resumen = _calcular_resumen(tabla, labels)

    return ComparisonResult(
        labels=labels, tabla=tabla, resumen=resumen, columnas_componentes=componentes_comunes
    )


def _agrupar_por_categoria(df: pd.DataFrame, componentes: list[str]) -> pd.DataFrame:
    agg_dict = {"DENO": ("DENO", lambda s: s.value_counts().idxmax()), "TOTAL": ("TOTAL", "sum")}
    for comp in componentes:
        agg_dict[comp] = (comp, "sum")
    return df.groupby("CODIGO").agg(**agg_dict).reset_index()


def _combinar(aggs: list[pd.DataFrame], labels: list[str], componentes: list[str]) -> pd.DataFrame:
    """Combina N períodos en una sola tabla ancha (outer join sucesivo por CODIGO)."""
    renamed = []
    for df, label in zip(aggs, labels):
        rename_map = {"DENO": f"DENO_{label}", "TOTAL": f"TOTAL_{label}"}
        for comp in componentes:
            rename_map[comp] = f"{comp}_{label}"
        renamed.append(df.rename(columns=rename_map))

    merged = reduce(lambda left, right: pd.merge(left, right, on="CODIGO", how="outer"), renamed)

    for label in labels:
        col_total = f"TOTAL_{label}"
        merged[col_total] = merged[col_total].fillna(0.0)
        for comp in componentes:
            col = f"{comp}_{label}"
            if col in merged.columns:
                merged[col] = merged[col].fillna(0.0)

    # Nombre de categoría a mostrar: el más reciente disponible (recorre de atrás hacia adelante)
    deno_cols = [f"DENO_{label}" for label in labels]

    def _pick_deno(row):
        for col in reversed(deno_cols):
            if pd.notna(row[col]):
                return row[col]
        return "(sin nombre)"

    merged["DENO"] = merged.apply(_pick_deno, axis=1)
    merged = merged.drop(columns=deno_cols)

    col_total_primero = f"TOTAL_{labels[0]}"
    col_total_ultimo = f"TOTAL_{labels[-1]}"

    def _estado(row):
        tiene_primero = row[col_total_primero] != 0
        tiene_ultimo = row[col_total_ultimo] != 0
        if tiene_primero and not tiene_ultimo:
            return ESTADO_DISCONTINUADO
        if tiene_ultimo and not tiene_primero:
            return ESTADO_NUEVO
        return ESTADO_EXISTENTE

    merged["ESTADO"] = merged.apply(_estado, axis=1)
    merged["DIFERENCIA"] = merged.apply(
        lambda r: variacion_absoluta(r[col_total_primero], r[col_total_ultimo]), axis=1
    )
    merged["VARIACION_PCT"] = merged.apply(
        lambda r: variacion_porcentual(r[col_total_primero], r[col_total_ultimo]), axis=1
    )

    columnas_totales = [f"TOTAL_{label}" for label in labels]
    columnas_componentes_final = [
        f"{comp}_{label}"
        for label in labels
        for comp in componentes
        if f"{comp}_{label}" in merged.columns
    ]

    columnas_base = ["CODIGO", "DENO"] + columnas_totales + ["DIFERENCIA", "VARIACION_PCT", "ESTADO"]
    merged = merged[columnas_base + columnas_componentes_final]
    merged = merged.sort_values(by=col_total_ultimo, ascending=False).reset_index(drop=True)
    return merged


def _calcular_resumen(tabla: pd.DataFrame, labels: list[str]) -> dict:
    gastos_por_periodo = {label: float(tabla[f"TOTAL_{label}"].sum()) for label in labels}
    gasto_primero = gastos_por_periodo[labels[0]]
    gasto_ultimo = gastos_por_periodo[labels[-1]]

    return {
        "labels": labels,
        "cant_periodos": len(labels),
        "gastos_por_periodo": gastos_por_periodo,
        "periodo_primero": labels[0],
        "periodo_ultimo": labels[-1],
        "gasto_primero": gasto_primero,
        "gasto_ultimo": gasto_ultimo,
        "variacion_gasto_pct": variacion_porcentual(gasto_primero, gasto_ultimo),
        "cant_categorias_nuevas": int((tabla["ESTADO"] == ESTADO_NUEVO).sum()),
        "cant_categorias_discontinuadas": int((tabla["ESTADO"] == ESTADO_DISCONTINUADO).sum()),
    }


# ----------------------------------------------------------------------
# Recalculo para un PAR de períodos elegido libremente por el usuario
# (no necesariamente el primero y el último de toda la serie cargada).
# ----------------------------------------------------------------------

def calcular_metricas_par(tabla: pd.DataFrame, label_base: str, label_comparado: str) -> pd.DataFrame:
    """
    Devuelve una copia de la tabla ancha con ESTADO, DIFERENCIA y
    VARIACION_PCT recalculados para el par (label_base, label_comparado)
    elegido por el usuario, en vez del primero/último de toda la serie.

    La tabla ancha ya tiene una columna TOTAL_<label> por cada período
    cargado (ver comparar_periodos), así que no hace falta volver a leer
    los Excel: alcanza con mirar las dos columnas correspondientes.
    """
    tabla = tabla.copy()
    col_base = f"TOTAL_{label_base}"
    col_comparado = f"TOTAL_{label_comparado}"

    def _estado(row):
        tiene_base = row[col_base] != 0
        tiene_comparado = row[col_comparado] != 0
        if tiene_base and not tiene_comparado:
            return ESTADO_DISCONTINUADO
        if tiene_comparado and not tiene_base:
            return ESTADO_NUEVO
        return ESTADO_EXISTENTE

    tabla["ESTADO"] = tabla.apply(_estado, axis=1)
    tabla["DIFERENCIA"] = tabla.apply(
        lambda r: variacion_absoluta(r[col_base], r[col_comparado]), axis=1
    )
    tabla["VARIACION_PCT"] = tabla.apply(
        lambda r: variacion_porcentual(r[col_base], r[col_comparado]), axis=1
    )
    return tabla


def resumen_par(tabla_vista: pd.DataFrame, label_base: str, label_comparado: str) -> dict:
    """
    Resumen (tarjetas del dashboard) para el par de períodos elegido.
    Recibe la tabla YA recalculada por calcular_metricas_par.
    """
    col_base = f"TOTAL_{label_base}"
    col_comparado = f"TOTAL_{label_comparado}"

    gasto_base = float(tabla_vista[col_base].sum())
    gasto_comparado = float(tabla_vista[col_comparado].sum())

    return {
        "periodo_base": label_base,
        "periodo_comparado": label_comparado,
        "gasto_base": gasto_base,
        "gasto_comparado": gasto_comparado,
        "variacion_gasto_pct": variacion_porcentual(gasto_base, gasto_comparado),
        "cant_categorias_nuevas": int((tabla_vista["ESTADO"] == ESTADO_NUEVO).sum()),
        "cant_categorias_discontinuadas": int((tabla_vista["ESTADO"] == ESTADO_DISCONTINUADO).sum()),
    }
