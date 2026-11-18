"""Registro central de rutas portables del proyecto."""

# Raíz portable de data para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[0]))
from pathlib import Path
DATA_ROOT = Path(__file__).resolve().parent
DOCUMENT = DATA_ROOT.parent
DATOS = DATA_ROOT / 'datos'
REGRESIONES = DATA_ROOT / 'regresiones'
RESULTADOS = REGRESIONES / 'resultados'
DASHBOARD = DOCUMENT / 'Dashboard'
PRINCIPAL = DOCUMENT / 'Principal'
ANEXO_A = DOCUMENT / 'Anexo_a'
RECURSOS = ANEXO_A / 'figuras'
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS, INDICADORES, PANEL_2018_2025, PANEL_2021_2025, PANEL_2022_2025, INDICES, FUENTES_GEIH, FUENTES_ECV
