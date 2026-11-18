"""Educación ECV comparable en escala 0..4; incertidumbre se conserva como NaN.

No equipara matrícula con aprobación en las fronteras entre categorías.
Ver educacion_notas.md para supuestos y fuentes. No modifica el DataFrame.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
import numpy as np
import pandas as pd

COLUMNAS_EDUCACION_ECV = ['P6040', 'P8586', 'P8587', 'P1088', 'P1088S1', 'P6216']
ESCOLARIDAD_ECV = {1:0, 2:0, 3:1, 4:2, 5:2, 6:3, 7:3, 8:3, 9:3, 10:4, 11:4, 12:4, 13:4}
ESCOLARIDAD_GEIH = {1:0, 2:0, 3:1, 4:2, 5:2, 6:2, 7:2, 8:3, 9:3, 10:4, 11:4, 12:4, 13:4}


def armonizar_educacion_ecv(df):
    """Devuelve Series float, índice original, categorías 0..4 o NaN.

    Escala: ninguno/preescolar, primaria, secundaria/media, técnico/tecnológico,
    universitario/posgrado. Casos de frontera sin nivel aprobado identificable
    se mantienen desconocidos. Requiere columnas originales ECV.
    """
    missing = set(COLUMNAS_EDUCACION_ECV) - set(df.columns)
    if missing:
        raise ValueError(f'Faltan columnas de educación ECV: {sorted(missing)}')
    age, attendance, attained, enrolled, grade, years = (
        pd.to_numeric(df[c], errors='coerce') for c in COLUMNAS_EDUCACION_ECV)
    out = pd.Series(np.nan, index=df.index, name='educacion_arm', dtype=float)
    nonstudent = attendance.eq(2)
    out.loc[nonstudent] = attained.loc[nonstudent].map(ESCOLARIDAD_ECV)
    student = attendance.eq(1)
    # Primaria desde grado 2; secundaria desde grado 7. En el primer grado
    # de cada nivel no podemos distinguir primera matrícula de repetición.
    out.loc[student & enrolled.eq(1) & grade.between(1,3)] = 0
    out.loc[student & enrolled.eq(2) & grade.between(2,5)] = 1
    out.loc[student & enrolled.eq(3) & grade.between(7,9)] = 2
    out.loc[student & enrolled.eq(4) & grade.between(10,13)] = 2
    # Años superiores son acumulados, no identifican el nivel previo en
    # estudiantes de primer año. Para años >=2 exigimos consistencia mínima.
    consistent = years.ge(grade - 1) & years.le(40)
    out.loc[student & enrolled.isin([5,6]) & grade.between(2,10) & consistent] = 3
    out.loc[student & enrolled.eq(7) & grade.between(2,10) & consistent] = 4
    # La matrícula de posgrado presupone nivel universitario: misma escala4.
    out.loc[student & enrolled.eq(8) & grade.between(1,10)] = 4
    # El capítulo no aplica a menores de 5; no los inventamos como secundaria.
    out.loc[age.lt(5) | age.isna()] = np.nan
    return out
