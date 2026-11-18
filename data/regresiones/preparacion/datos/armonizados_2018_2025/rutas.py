"""Registro único de insumos certificados; ninguna estimación selecciona otra rama."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))
from pathlib import Path

CARPETA = Path(__file__).resolve().parents[4] / 'datos/armonizados_2018_2025'
BASE = Path(__file__).resolve().parents[4]
MICRODATOS = {y: (Path(__file__).resolve().parents[4] / 'datos/armonizados_2018_2025/microdatos') / f'ecv_geih_imputada_{y}.parquet' for y in range(2018, 2026)}
INDICADORES = {y: (Path(__file__).resolve().parents[4] / 'datos/armonizados_2018_2025/indicadores') / f'indicadores_oficiales_{y}.parquet' for y in range(2018, 2026)}
PANEL_2018_2025 = (Path(__file__).resolve().parents[4] / 'datos/armonizados_2018_2025/paneles/panel_cohortes_2018_2025.parquet')
PANEL_2021_2025 = (Path(__file__).resolve().parents[4] / 'datos/armonizados_2018_2025/paneles/panel_cohortes_2021_2025.parquet')
PANEL_2022_2025 = (Path(__file__).resolve().parents[4] / 'datos/armonizados_2018_2025/paneles/panel_cohortes_2022_2025.parquet')
PANEL_CERRADO_2022_2025 = (Path(__file__).resolve().parents[4] / 'datos/armonizados_2018_2025/paneles/panel_cohortes_nacimiento_hasta_2007.parquet')
PANEL_TIC_DTA = (Path(__file__).resolve().parents[4] / 'datos/armonizados_2018_2025/paneles/panel_tic_2018_2025.dta')
INDICES = (Path(__file__).resolve().parents[4] / 'datos/exposicion_ia/indices_normalizados_referencia.csv')
_RECON = (Path(__file__).resolve().parents[4] / 'datos/tic_laboral_2018_2025/reconstruccion')
FUENTES_GEIH = {
    **{y: _RECON / f'fuentes/GEIH/{y}/geih_son_original_ensamblada_{y}.parquet' for y in range(2018, 2021)},
    2021: (Path(__file__).resolve().parents[4] / 'datos/tic_laboral_2018_2025/reconstruccion/fuentes/GEIH/2021/geih_son_original_ensamblada_2021.parquet'),
    **{y: BASE / f'datos/GEIH/{y}/total_son_full_{y}.parquet' for y in range(2022, 2026)},
}
FUENTES_ECV = {
    **{y: _RECON / f'fuentes/ECV/{y}/total_ecv_{y}.parquet' for y in range(2018, 2021)},
    2021: (Path(__file__).resolve().parents[4] / 'datos/tic_laboral_2018_2025/reconstruccion/fuentes/ECV/2021/total_ecv_2021.parquet'),
    **{y: BASE / f'datos/ECV/{y}/total_ecv_{y}.parquet' for y in range(2022, 2026)},
}
PESOS_GEIH = {2018: 'FEX_C_2011', 2019: 'FEX_C_2011', 2020: 'FEX_C', **{y: 'FEX_C18' for y in range(2021, 2026)}}
IPC = {2018: 99.59, 2019: 103.43, 2020: 105.23, 2021: 110.06, 2022: 123.51, 2023: 136.45, 2024: 143.83, 2025: 151.76}
