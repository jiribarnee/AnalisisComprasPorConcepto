"""
detail_dialog.py

Diálogo que se abre al hacer doble clic sobre una fila de la tabla del
dashboard. Muestra:
    - El gasto de esa categoría en CADA período cargado (2 a 12), con
      los dos períodos elegidos para comparar resaltados.
    - Un selector propio de "Período base" / "Período comparado"
      (arranca con el mismo par activo en el dashboard, pero se puede
      cambiar acá sin afectar al dashboard).
    - Diferencia, variación y desglose impositivo, recalculados según
      el par elegido en ESTE diálogo.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from core.calculations import formato_moneda, formato_porcentaje, variacion_absoluta, variacion_porcentual
from core.comparator import ComparisonResult, ESTADO_DISCONTINUADO, ESTADO_NUEVO
from core.excel_processor import NOMBRES_COMPONENTES


class CategoryDetailDialog(QDialog):
    def __init__(self, row, resultado: ComparisonResult, label_base: str, label_comparado: str, parent=None):
        super().__init__(parent)
        self._row = row
        self._resultado = resultado
        self._label_base = label_base
        self._label_comparado = label_comparado

        self.setWindowTitle(f"Detalle — {row['DENO']}")
        self.setMinimumWidth(560)
        self.setMinimumHeight(500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self._layout = layout

        titulo = QLabel(f"🏷️ {self._row['DENO']}")
        titulo.setStyleSheet("font-size: 18px; font-weight: 800; color: #1f2430;")
        titulo.setWordWrap(True)
        layout.addWidget(titulo)

        layout.addLayout(self._build_selector_par())

        self._estado_label = QLabel()
        self._estado_label.setStyleSheet("font-weight: 700; font-size: 12px;")
        layout.addWidget(self._estado_label)

        self._serie_container_holder = QVBoxLayout()
        layout.addLayout(self._serie_container_holder)

        separador = QFrame()
        separador.setFrameShape(QFrame.HLine)
        separador.setStyleSheet("background-color: #e7e9ee; max-height: 1px; border: none;")
        layout.addWidget(separador)

        self._resumen_container_holder = QVBoxLayout()
        self._resumen_container_holder.setSpacing(8)
        layout.addLayout(self._resumen_container_holder)

        self._separador2 = QFrame()
        self._separador2.setFrameShape(QFrame.HLine)
        self._separador2.setStyleSheet("background-color: #e7e9ee; max-height: 1px; border: none;")
        layout.addWidget(self._separador2)

        self._desglose_titulo = QLabel()
        self._desglose_titulo.setStyleSheet("font-weight: 800; font-size: 13px; color: #35394a;")
        self._desglose_titulo.setWordWrap(True)
        layout.addWidget(self._desglose_titulo)

        self._desglose_container_holder = QVBoxLayout()
        layout.addLayout(self._desglose_container_holder)

        cerrar_btn = QPushButton("Cerrar")
        cerrar_btn.setCursor(Qt.PointingHandCursor)
        cerrar_btn.setStyleSheet(
            "background-color: #1f2430; border: none; border-radius: 9px; "
            "padding: 10px; color: #ffffff; font-weight: 700;"
        )
        cerrar_btn.clicked.connect(self.accept)
        layout.addWidget(cerrar_btn)

        self._refrescar_contenido()

    def _build_selector_par(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        icono = QLabel("🔀")
        row.addWidget(icono)

        label = QLabel("Comparar:")
        label.setStyleSheet("color: #7a8294; font-size: 12px;")
        row.addWidget(label)

        self.combo_base = QComboBox()
        self.combo_base.addItems(self._resultado.labels)
        self.combo_base.setCurrentText(self._label_base)
        self.combo_base.currentTextChanged.connect(self._on_par_changed)
        row.addWidget(self.combo_base)

        flecha = QLabel("→")
        flecha.setStyleSheet("color: #7a8294;")
        row.addWidget(flecha)

        self.combo_comparado = QComboBox()
        self.combo_comparado.addItems(self._resultado.labels)
        self.combo_comparado.setCurrentText(self._label_comparado)
        self.combo_comparado.currentTextChanged.connect(self._on_par_changed)
        row.addWidget(self.combo_comparado)

        row.addStretch()
        return row

    def _on_par_changed(self, *_args):
        self._label_base = self.combo_base.currentText()
        self._label_comparado = self.combo_comparado.currentText()
        self._refrescar_contenido()

    # ------------------------------------------------------------------
    # Recalcular todo el contenido para el par activo
    # ------------------------------------------------------------------

    def _refrescar_contenido(self):
        row = self._row
        label_base = self._label_base
        label_comparado = self._label_comparado

        col_base = f"TOTAL_{label_base}"
        col_comparado = f"TOTAL_{label_comparado}"
        valor_base = row.get(col_base, 0.0) or 0.0
        valor_comparado = row.get(col_comparado, 0.0) or 0.0

        estado = _estado_para_par(valor_base, valor_comparado)
        estado_txt, estado_color = _estado_visual(estado)
        self._estado_label.setText(estado_txt)
        self._estado_label.setStyleSheet(f"font-weight: 700; font-size: 12px; color: {estado_color};")

        _limpiar_layout(self._serie_container_holder)
        self._serie_container_holder.addWidget(self._build_serie_periodos(row, label_base, label_comparado))

        _limpiar_layout(self._resumen_container_holder)
        diferencia = variacion_absoluta(valor_base, valor_comparado)
        variacion = variacion_porcentual(valor_base, valor_comparado)
        signo_icono = "💰" if diferencia >= 0 else "💸"
        self._resumen_container_holder.addWidget(
            self._metric_line(signo_icono, f"Diferencia ({label_base} → {label_comparado})", formato_moneda(diferencia), diferencia)
        )
        self._resumen_container_holder.addWidget(
            self._metric_line("📈", "Variación", formato_porcentaje(variacion), variacion)
        )

        desglose = self._build_desglose(row, label_base, label_comparado)
        _limpiar_layout(self._desglose_container_holder)
        if desglose is not None:
            self._desglose_titulo.setText(f"🧾 Desglose impositivo ({label_base} vs {label_comparado})")
            self._desglose_titulo.setVisible(True)
            self._separador2.setVisible(True)
            self._desglose_container_holder.addWidget(desglose)
        else:
            self._desglose_titulo.setVisible(False)
            self._separador2.setVisible(False)

    def _build_serie_periodos(self, row, label_base, label_comparado):
        """Lista con el gasto de esta categoría en cada período cargado, resaltando el par elegido."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(150)

        container = QFrame()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(4)
        container_layout.setContentsMargins(0, 0, 4, 0)

        for label in self._resultado.labels:
            valor = row.get(f"TOTAL_{label}", 0.0)
            es_seleccionado = label in (label_base, label_comparado)

            fila = QFrame()
            fila.setObjectName("metricBlock" if es_seleccionado else "")
            fila_layout = QHBoxLayout(fila)
            fila_layout.setContentsMargins(10, 6, 10, 6)

            peso = "800" if es_seleccionado else "500"
            nombre_label = QLabel(label)
            nombre_label.setStyleSheet(f"color: #35394a; font-size: 12px; font-weight: {peso};")
            fila_layout.addWidget(nombre_label, stretch=1)

            color = "#1f2430" if es_seleccionado else "#5b6472"
            valor_label = QLabel(formato_moneda(valor))
            valor_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: {peso};")
            fila_layout.addWidget(valor_label)

            container_layout.addWidget(fila)

        container_layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _build_desglose(self, row, label_base, label_comparado):
        filas = []
        for comp in self._resultado.columnas_componentes:
            col1 = f"{comp}_{label_base}"
            col2 = f"{comp}_{label_comparado}"
            val1 = row.get(col1, 0.0) or 0.0
            val2 = row.get(col2, 0.0) or 0.0
            if val1 == 0 and val2 == 0:
                continue
            nombre = NOMBRES_COMPONENTES.get(comp, comp)
            filas.append((nombre, val1, val2))

        if not filas:
            return None

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(180)

        container = QFrame()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(6)
        container_layout.setContentsMargins(0, 0, 4, 0)

        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(10, 0, 10, 0)
        concepto_h = QLabel("Concepto")
        concepto_h.setStyleSheet("color: #7a8294; font-size: 10px; font-weight: 800;")
        header_layout.addWidget(concepto_h, stretch=1)
        p1_h = QLabel(label_base)
        p1_h.setStyleSheet("color: #7a8294; font-size: 10px; font-weight: 800;")
        p1_h.setFixedWidth(130)
        p1_h.setAlignment(Qt.AlignRight)
        header_layout.addWidget(p1_h)
        p2_h = QLabel(label_comparado)
        p2_h.setStyleSheet("color: #7a8294; font-size: 10px; font-weight: 800;")
        p2_h.setFixedWidth(130)
        p2_h.setAlignment(Qt.AlignRight)
        header_layout.addWidget(p2_h)
        container_layout.addWidget(header)

        for nombre, val1, val2 in filas:
            fila = QFrame()
            fila.setObjectName("componentRow")
            fila_layout = QHBoxLayout(fila)
            fila_layout.setContentsMargins(10, 6, 10, 6)

            nombre_label = QLabel(nombre)
            nombre_label.setStyleSheet("color: #1f2430; font-size: 12px;")
            fila_layout.addWidget(nombre_label, stretch=1)

            val1_label = QLabel(formato_moneda(val1))
            val1_label.setStyleSheet("color: #5b6472; font-size: 12px;")
            val1_label.setFixedWidth(130)
            val1_label.setAlignment(Qt.AlignRight)
            fila_layout.addWidget(val1_label)

            val2_label = QLabel(formato_moneda(val2))
            val2_label.setStyleSheet("color: #1f2430; font-size: 12px; font-weight: 700;")
            val2_label.setFixedWidth(130)
            val2_label.setAlignment(Qt.AlignRight)
            fila_layout.addWidget(val2_label)

            container_layout.addWidget(fila)

        container_layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _metric_line(self, icono, etiqueta, valor_txt, valor_num):
        row_widget = QFrame()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"{icono} {etiqueta}")
        label.setStyleSheet("color: #5b6472; font-size: 13px;")
        label.setWordWrap(True)
        row_layout.addWidget(label, stretch=1)

        color = "#1f9d55" if (valor_num is not None and valor_num >= 0) else "#e0322c"
        valor = QLabel(valor_txt)
        valor.setStyleSheet(f"color: {color}; font-weight: 800; font-size: 13px;")
        row_layout.addWidget(valor)

        return row_widget


def _limpiar_layout(layout):
    """Saca y elimina todos los widgets/sub-layouts de un QLayout, para poder repoblarlo."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()


def _estado_para_par(valor_base: float, valor_comparado: float) -> str:
    tiene_base = valor_base != 0
    tiene_comparado = valor_comparado != 0
    if tiene_base and not tiene_comparado:
        return ESTADO_DISCONTINUADO
    if tiene_comparado and not tiene_base:
        return ESTADO_NUEVO
    return "EXISTENTE"


def _estado_visual(estado: str) -> tuple[str, str]:
    if estado == ESTADO_NUEVO:
        return "🆕 Categoría nueva (sin gasto en el período base)", "#1f9d55"
    if estado == ESTADO_DISCONTINUADO:
        return "⛔ Categoría discontinuada (sin gasto en el período comparado)", "#e0322c"
    return "Categoría activa en ambos períodos del par elegido", "#7a8294"
