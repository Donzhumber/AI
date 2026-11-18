"""Agrupación operativa documentada de posición ocupacional GEIH/ECV 2022–2025.

No modifica matching ni respuestas originales. El grupo sin remuneración es una
aproximación amplia: ECV distingue trabajadores y ayudantes, GEIH dice familiar.
Los consumidores restringen a ocupados y a pesos válidos antes de evaluar.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
import pandas as pd

GRUPOS = {1:'Empleado particular',2:'Empleado del gobierno',3:'Empleado doméstico',
          4:'Independiente o cuenta propia',5:'Patrón o empleador',
          6:'Sin remuneración (agrupación amplia)',7:'Jornalero o peón'}
MAPA_GEIH = {1:1,2:2,3:3,4:4,5:5,6:6,7:7}
MAPA_ECV = {1:1,2:2,3:3,4:4,5:4,6:5,7:4,8:6,9:6,10:7}


def _armonizar(values, mapping, year):
    if year is not None and int(year) not in (2022,2023,2024,2025):
        raise ValueError('Armonización documentada únicamente para 2022–2025')
    source=values if isinstance(values,pd.Series) else pd.Series(values)
    return pd.to_numeric(source,errors='coerce').map(mapping).astype(float)


def armonizar_posicion_geih(values, year=None):
    """P6430: 7=jornalero; 8=otro queda NaN por ausencia de equivalencia ECV."""
    return _armonizar(values,MAPA_GEIH,year)


def armonizar_posicion_ecv(values, year=None):
    """P6435: finca propia7 no contrata remunerados según DDI; se integra a4."""
    return _armonizar(values,MAPA_ECV,year)
