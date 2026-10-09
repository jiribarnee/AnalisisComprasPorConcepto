"""
excel_processor.py

Se encarga de leer un Excel de RESUMEN DE GASTOS POR CATEGORÍA y
devolverlo como un DataFrame de pandas limpio y normalizado.

Estructura esperada del Excel (detectada analizando Res__06-2026.xlsx
y Res__07-2026.xlsx):

    CODIGO, DENO, NETO10, IVA10, NETO, IVA, NETO27, IVA27, OTNETO,
    OTIVA, NOGRA, IMPUE, PERCE, RETEIB, RETGAN, IMPUE2, ITC, TOTAL

Cada FILA representa el total de UNA CATEGORÍA de gasto en el mes
(ej: "COMBUSTIBLE", "REPUESTOS", "HONORARIOS JURÍDICOS"). TOTAL es la
suma de todas las columnas de impuestos/componentes (verificado
numéricamente: la diferencia es de punto flotante, no de datos).

DENO es la unidad principal de análisis de esta aplicación (equivalente
al "Producto"/"RAZÓN" de otras versiones). CODIGO se usa como clave
interna estable, ya que es 1:1 con DENO.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

import pandas as pd

# ----------------------------------------------------------------------
# Configuración: columnas requeridas y componentes de impuestos
# ----------------------------------------------------------------------

REQUIRED_COLUMNS = {
    "CODIGO": True,
    "DENO": True,
    "TOTAL": True,
}

# Columnas de desglose de impuestos/componentes (opcionales, se usan
# para el detalle de cada categoría, pero no son obligatorias para que
# la comparación básica funcione).
COLUMNAS_COMPONENTES = [
    "NETO10", "IVA10", "NETO", "IVA", "NETO27", "IVA27",
    "OTNETO", "OTIVA", "NOGRA", "IMPUE", "PERCE", "RETEIB",
    "RETGAN", "IMPUE2", "ITC",
]

# Nombres legibles para mostrar en la UI (detalle por categoría)
NOMBRES_COMPONENTES = {
    "NETO10": "Neto (IVA 10,5%)",
    "IVA10": "IVA 10,5%",
    "NETO": "Neto (IVA 21%)",
    "IVA": "IVA 21%",
    "NETO27": "Neto (IVA 27%)",
    "IVA27": "IVA 27%",
    "OTNETO": "Otros conceptos - Neto",
    "OTIVA": "Otros conceptos - IVA",
    "NOGRA": "No gravado",
    "IMPUE": "Impuestos internos",
    "PERCE": "Percepciones",
    "RETEIB": "Retención Ingresos Brutos",
    "RETGAN": "Retención Ganancias",
    "IMPUE2": "Impuestos (otros)",
    "ITC": "Impuesto a los Créditos y Débitos",
}


class ExcelProcessingError(Exception):
    """
    Error controlado durante la lectura/validación de un Excel.
    El mensaje ya viene listo para mostrarse al usuario (en español,
    sin detalles técnicos internos).
    """

    pass


@dataclass
class LoadedPeriod:
    """Resultado de cargar un archivo de gastos: datos + metadatos."""

    label: str
    filepath: str
    dataframe: pd.DataFrame
    row_count: int = field(init=False)

    def __post_init__(self):
        self.row_count = len(self.dataframe)


# ----------------------------------------------------------------------
# Detección del nombre de período a partir del archivo
# ----------------------------------------------------------------------

def detect_period_label(filepath: str) -> str:
    """
    Genera un nombre de período legible a partir del nombre del archivo.

    Ejemplos:
        Res__06-2026.xlsx  -> "RES 06-2026"
        JUNIO.xlsx         -> "JUNIO"
        compras-agosto.xlsx -> "COMPRAS AGOSTO"

    Es solo una sugerencia inicial: la UI permite que el usuario la
    edite si lo desea.
    """
    filename = os.path.basename(filepath)
    name_without_ext = os.path.splitext(filename)[0]
    cleaned = re.sub(r"[_\-]+", " ", name_without_ext).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)  # colapsar espacios múltiples
    return cleaned.upper() if cleaned else "PERIODO"


# ----------------------------------------------------------------------
# Carga y validación
# ----------------------------------------------------------------------

def load_expense_file(filepath: str, period_label: str | None = None) -> LoadedPeriod:
    """
    Lee un archivo Excel de resumen de gastos por categoría y devuelve
    un LoadedPeriod con el DataFrame ya limpio.

    Lanza ExcelProcessingError con un mensaje claro si algo no es válido.
    """
    _validate_file_exists_and_extension(filepath)

    df = _read_excel_safely(filepath)
    df = _normalize_columns(df, filepath)
    _validate_required_columns(df, filepath)
    df = _clean_data(df)

    if len(df) == 0:
        raise ExcelProcessingError(
            f'El archivo "{os.path.basename(filepath)}" no contiene filas de datos '
            f"válidas después de limpiarlo. Verifique que no esté vacío."
        )

    label = period_label or detect_period_label(filepath)
    return LoadedPeriod(label=label, filepath=filepath, dataframe=df)


def _validate_file_exists_and_extension(filepath: str) -> None:
    if not os.path.isfile(filepath):
        raise ExcelProcessingError(f"No se encontró el archivo:\n{filepath}")

    ext = os.path.splitext(filepath)[1].lower()
    if ext not in (".xlsx", ".xlsm"):
        raise ExcelProcessingError(
            f'El archivo "{os.path.basename(filepath)}" no es un Excel válido (.xlsx).\n'
            f"Formato detectado: {ext or 'desconocido'}"
        )


def _read_excel_safely(filepath: str) -> pd.DataFrame:
    try:
        return pd.read_excel(filepath, sheet_name=0)
    except Exception as exc:  # noqa: BLE001
        raise ExcelProcessingError(
            f'No se pudo abrir "{os.path.basename(filepath)}".\n'
            f"El archivo podría estar corrupto, dañado o no ser un Excel real.\n\n"
            f"Detalle técnico: {exc}"
        ) from exc


def _normalize_columns(df: pd.DataFrame, filepath: str) -> pd.DataFrame:
    if df.empty and len(df.columns) == 0:
        raise ExcelProcessingError(
            f'El archivo "{os.path.basename(filepath)}" está vacío (sin columnas).'
        )
    df = df.copy()
    # Los headers reales vienen con espacios de relleno, ej: "CODIGO         "
    df.columns = [str(c).strip() for c in df.columns]
    return df


def _validate_required_columns(df: pd.DataFrame, filepath: str) -> None:
    missing = [
        col for col, required in REQUIRED_COLUMNS.items()
        if required and col not in df.columns
    ]
    if missing:
        cols_txt = ", ".join(f'"{c}"' for c in missing)
        raise ExcelProcessingError(
            f'El archivo "{os.path.basename(filepath)}" no tiene la estructura esperada.\n\n'
            f"Faltan las columnas: {cols_txt}\n\n"
            f'Verifique que el Excel sea un "resumen por categoría" con al menos '
            f"las columnas CODIGO, DENO y TOTAL."
        )


def _clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # DENO: quitar espacios de relleno, descartar filas sin categoría
    if "DENO" in df.columns:
        df["DENO"] = df["DENO"].astype(str).str.strip()
        df = df[df["DENO"].str.len() > 0]

    # CODIGO: usarlo como clave estable de categoría
    if "CODIGO" in df.columns:
        df["CODIGO"] = pd.to_numeric(df["CODIGO"], errors="coerce")
        df = df[df["CODIGO"].notna()]
        df["CODIGO"] = df["CODIGO"].astype("int64")

    # TOTAL: forzar numérico, descartar filas sin importe válido
    if "TOTAL" in df.columns:
        df["TOTAL"] = pd.to_numeric(df["TOTAL"], errors="coerce")
        df = df[df["TOTAL"].notna()]

    # Columnas de componentes: forzar numérico, NaN -> 0 (no todas las
    # categorías usan todos los conceptos impositivos)
    for col in COLUMNAS_COMPONENTES:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df = df.reset_index(drop=True)
    return df


def columnas_componentes_presentes(df: pd.DataFrame) -> list[str]:
    """Devuelve qué columnas de componentes de impuestos existen en este DataFrame."""
    return [c for c in COLUMNAS_COMPONENTES if c in df.columns]
