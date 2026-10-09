# 📊 Análisis de Compras por Concepto

Aplicación de escritorio en Python que compara los **gastos por categoría**
entre **2 y 12 períodos** (por ejemplo, los 12 meses de un año), a partir
de archivos Excel de resumen mensual. Desarrollada para **Bailo Hnos.**

Es un proyecto hermano de **Analizador de Compras** (que compara por
proveedor/factura, siempre 2 períodos), pero pensado para un tipo de
reporte distinto: un resumen ya agrupado por categoría de gasto
(combustible, repuestos, neumáticos, honorarios, etc.), con desglose
impositivo, y ahora con la posibilidad de analizar un año completo de
una sola vez. Tiene una identidad visual propia (clara, corporativa, con
el rojo del logo de Bailo Hnos como color principal).

## Qué hace

- Cargás **entre 2 y 12** Excel de resumen (uno por período), agregando
  o quitando filas dinámicamente en la pantalla inicial.
- Compara el gasto total por **categoría** (columna `DENO`) a lo largo
  de todos los períodos cargados.
- La tabla principal muestra **una columna de gasto por cada período**
  cargado, más diferencia y variación entre el primer y el último.
- Categorías nuevas/discontinuadas: se determinan comparando el primer
  y el último período de toda la serie.
- Alertas automáticas: los aumentos/disminuciones fuertes comparan
  específicamente los **últimos dos períodos cargados** (el cambio más
  reciente); las categorías nuevas/discontinuadas comparan las puntas
  de toda la serie.
- Gráficos interactivos (Plotly): gasto total por período (una barra
  por mes), top categorías, mayores aumentos/disminuciones (primer vs
  último período), distribución por estado.
- **Detalle por categoría**: al hacer doble clic en una fila se ve el
  gasto de esa categoría en TODOS los períodos cargados, más el
  desglose impositivo completo comparando el primer y el último período.
- Empaquetable como ejecutable standalone (`.exe` en Windows, `.app`
  en macOS).

## Estructura real del Excel de origen

Cada fila del Excel es el resumen de UNA categoría de gasto en el mes:

```
CODIGO, DENO, NETO10, IVA10, NETO, IVA, NETO27, IVA27, OTNETO,
OTIVA, NOGRA, IMPUE, PERCE, RETEIB, RETGAN, IMPUE2, ITC, TOTAL
```

`TOTAL` es la suma de todas las columnas de componentes (verificado
numéricamente). `DENO` es el nombre de la categoría. `CODIGO` es una
clave numérica estable, 1:1 con `DENO`, usada internamente para agrupar.

El desglose impositivo del detalle solo muestra las columnas de
componentes que estén presentes en **todos** los períodos cargados —
si algún mes viene con una estructura distinta, la app sigue
funcionando con la comparación de totales igual.

## Instalación

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
python main.py
```

Podés probar con los archivos de ejemplo **ficticios** en
`data/sample/` (los reales de Bailo Hnos. nunca se suben a un
repositorio público).

## Generar el ejecutable

**Windows:**
```powershell
venv\Scripts\activate
pip install -r requirements-dev.txt
build_exe.bat
```

**macOS:**
```bash
source venv/bin/activate
pip install -r requirements-dev.txt
chmod +x build_exe_mac.sh
./build_exe_mac.sh
```

El resultado queda en `dist/`. Distribuir la carpeta completa (Windows)
o el archivo `.app` (Mac), no solo el ejecutable suelto.

## Estructura del proyecto

```
AnalisisComprasPorConcepto/
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── build_exe.bat / build_exe_mac.sh
│
├── core/
│   ├── excel_processor.py   # Lectura, validación y limpieza del Excel
│   ├── comparator.py        # Comparación entre dos períodos por categoría
│   ├── calculations.py      # Cálculos puros: %, formato moneda
│   ├── charts.py            # Gráficos Plotly
│   └── alerts.py            # Detección automática de alertas
│
├── ui/
│   ├── main_window.py       # Selección de archivos
│   ├── dashboard.py         # Pantalla de resultados
│   ├── charts_panel.py      # Gráficos embebidos (QtWebEngine)
│   ├── alerts_panel.py      # Panel de alertas
│   └── detail_dialog.py     # Detalle por categoría + desglose impositivo
│
├── assets/                  # Ícono, logo, hoja de estilos
├── data/sample/              # Datos ficticios para pruebas/portafolio
└── docs/screenshots/
```

## Privacidad

Todo el procesamiento es 100% local. Los Excel reales de la empresa no
se envían a ningún servidor ni se suben a este repositorio.

## Roadmap

- [x] Comparación entre 2 y 12 períodos por categoría, dashboard,
      alertas, gráficos, detalle con serie completa y desglose
      impositivo, manejo de errores.
- [x] Empaquetado como ejecutable standalone (Windows y macOS).
- [ ] Exportación de resultados a Excel/PDF.
- [ ] Interpretación con IA (OpenAI API) — en pausa a la espera de que
      la empresa confirme el uso de su propia cuenta.
