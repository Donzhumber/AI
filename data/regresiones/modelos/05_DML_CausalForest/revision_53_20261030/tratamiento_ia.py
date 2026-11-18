"""ECV 2025 internet-mediated AI use, respecting questionnaire routing."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))
import numpy as np
import pandas as pd


def construir_tratamiento(df):
    """Return (D, diagnostics); unknown module/response stays missing.

    P1083 is an empty parent field. Its selected-response subitems carry
    the multiple-choice answer. P1084=5 skips I6 and explicitly reports
    no internet use, hence no internet-mediated AI use.
    """
    required = ['P1084'] + [f'P1083S{i}' for i in range(1, 22)]
    absent = [c for c in required if c not in df.columns]
    if absent:
        raise ValueError(f'Missing treatment inputs: {absent}')
    freq = pd.to_numeric(df['P1084'], errors='coerce')
    acts = df[required[1:]].apply(pd.to_numeric, errors='coerce')
    any_activity = acts.eq(1).any(axis=1)
    ai = acts['P1083S21'].eq(1)
    user = freq.isin([1, 2, 3, 4])
    nonuser = freq.eq(5)
    conflict = (nonuser & any_activity) | (ai & ~user)
    d = pd.Series(np.nan, index=df.index, name='uso_ia', dtype=float)
    d.loc[nonuser & ~conflict] = 0.0
    d.loc[user & any_activity & ~conflict] = ai.loc[user & any_activity & ~conflict].astype(float)
    # The item exists only in 2025; never turn other years into controls.
    if 'anio' in df.columns:
        d.loc[pd.to_numeric(df['anio'], errors='coerce').ne(2025)] = np.nan
    diagnostics = {
        'n': int(len(df)), 'tratados': int(d.eq(1).sum()),
        'controles': int(d.eq(0).sum()), 'sin_clasificar': int(d.isna().sum()),
        'usuarios_sin_actividad': int((user & ~any_activity).sum()),
        'ruta_inconsistente': int(conflict.sum()),
        'sin_ruta_valida': int((~user & ~nonuser).sum()),
    }
    return d, diagnostics
