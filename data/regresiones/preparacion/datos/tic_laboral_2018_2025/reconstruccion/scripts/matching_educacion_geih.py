"""Escala común 0–4; conserva como desconocido el nivel no identificable."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[6]))
import numpy as np
import pandas as pd
from matching_anexo import QUARTO
from regresiones.validacion.correcciones.educacion import ESCOLARIDAD_GEIH


def armonizar(df):
    if "P3042" in df:
        return pd.to_numeric(df.P3042, errors="coerce").map(ESCOLARIDAD_GEIH)
    if not {"P6210", "P6220"}.issubset(df.columns):
        raise ValueError("Faltan variables de educación GEIH histórica")
    level = pd.to_numeric(df.P6210, errors="coerce")
    degree = pd.to_numeric(df.P6220, errors="coerce")
    out = pd.Series(np.nan, index=df.index, name="EDUCACION_ARM_GEIH")
    out.loc[level.isin([1, 2])] = 0.
    out.loc[level.eq(3)] = 1.
    out.loc[level.isin([4, 5])] = 2.
    out.loc[level.eq(6) & degree.eq(3)] = 3.
    out.loc[level.eq(6) & degree.isin([4, 5])] = 4.
    # Superior sin título identificable no prueba nivel técnico ni universitario.
    return out
