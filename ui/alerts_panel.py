"""
alerts_panel.py

Panel que lista las alertas generadas automáticamente (ver
core/alerts.py), con color según nivel de importancia.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.alerts import Alerta, NIVEL_ALTO, NIVEL_MEDIO, NIVEL_POSITIVO


_COLOR_POR_NIVEL = {
    NIVEL_ALTO: "#e0322c",
    NIVEL_MEDIO: "#e08a1e",
    NIVEL_POSITIVO: "#1f9d55",
}


class AlertItem(QFrame):
    def __init__(self, alerta: Alerta, parent=None):
        super().__init__(parent)
        self.setObjectName("alertItem")
        color = _COLOR_POR_NIVEL.get(alerta.nivel, "#7a8294")
        self.setStyleSheet(
            f"#alertItem {{ border-left: 3px solid {color}; "
            f"background-color: #f7f8fa; border-radius: 8px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        titulo = QLabel(f"{alerta.icono} {alerta.titulo}")
        titulo.setStyleSheet("font-weight: 700; color: #1f2430; font-size: 12px;")
        titulo.setWordWrap(True)
        layout.addWidget(titulo)

        detalle = QLabel(alerta.detalle)
        detalle.setStyleSheet("color: #7a8294; font-size: 11px;")
        detalle.setWordWrap(True)
        layout.addWidget(detalle)


class AlertsPanel(QWidget):
    def __init__(self, alertas: list[Alerta], parent=None):
        super().__init__(parent)
        self._build_ui(alertas)

    def _build_ui(self, alertas: list[Alerta]):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(8)

        titulo = QLabel(f"⚠️ ALERTAS ({len(alertas)})")
        titulo.setStyleSheet("font-weight: 800; font-size: 13px; color: #35394a;")
        outer.addWidget(titulo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(6)
        container_layout.setContentsMargins(0, 0, 4, 0)

        if not alertas:
            vacio = QLabel("Sin alertas relevantes en este análisis.")
            vacio.setStyleSheet("color: #7a8294; font-size: 12px;")
            container_layout.addWidget(vacio)
        else:
            for alerta in alertas:
                container_layout.addWidget(AlertItem(alerta))

        container_layout.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll, stretch=1)
