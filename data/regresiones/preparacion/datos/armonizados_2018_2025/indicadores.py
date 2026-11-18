"""Definiciones compartidas de indicadores, preservando dominios y ausencias."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))
import importlib.util
import numpy as np
import pandas as pd
from .rutas import BASE
from regresiones.validacion.correcciones.educacion import armonizar_educacion_ecv
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import cargar_indices, ocupacion_analitica, COLUMNAS


def tic_combinado(d):
    """Uso personal de escritorio/portátil Y conexión del hogar; no propiedad."""
    valid = d.P1910.isin(range(1, 6)) & d.P1911.isin(range(1, 6)) & d.P1075.isin([1, 2])
    result = pd.Series(np.nan, index=d.index, name='H_tic')
    value = (d.P1910.isin(range(1, 5)) | d.P1911.isin(range(1, 5))) & d.P1075.eq(1)
    result.loc[valid] = value.loc[valid].astype(float)
    return result


def uso_ia_validado(d):
    """Misma ruta del cuestionario que DML-IV, sin transformar blancos en ceros."""
    path = BASE/'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/tratamiento_ia.py'
    spec = importlib.util.spec_from_file_location('tratamiento_ia_validado', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.construir_tratamiento(d)


def exposicion_personal(d, variante='anterior'):
    """Cinco índices percentiles/MM del catálogo fijo, sin normalización anual."""
    idx = cargar_indices().set_index('ciuo08')
    codes = ocupacion_analitica(d, variante=variante)
    result = pd.DataFrame({'ciuo08': codes}, index=d.index)
    for name in COLUMNAS:
        result[name] = codes.map(idx[name]).astype(float)
    return result
