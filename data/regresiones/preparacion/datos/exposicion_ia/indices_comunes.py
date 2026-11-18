"""Referencia ocupacional fija de índices: nunca normaliza sobre una muestra laboral.

Percentil = (rango promedio - 1)/(N no faltantes - 1); no ponderado por empleo.
El máximo requiere los tres componentes observados; faltantes no equivalen a cero.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))
from pathlib import Path
import hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4] / 'datos/exposicion_ia'
FUENTE = Path(__file__).resolve().parents[4] / 'datos/exposicion_ia/ciuo08_exposicion_ia_scores.csv'
INDICADORES = {
    'aioe': 'AIOE', 'webb_ia': 'ai_score', 'llm': 'dv_rating_beta',
    'software': 'software_score', 'robots': 'robot_score',
}
ETIQUETAS = {'aioe':'AIOE', 'webb_ia':'Webb–IA', 'llm':'LLM beta GPT-4',
             'software':'Webb–software', 'robots':'Webb–robots', 'envolvente':'Máximo de tres IA'}
COLUMNAS = [f'{k}_{s}' for s in ('pct','mm') for k in (*INDICADORES, 'envolvente')]

def codigo_ocupacion(valores):
    """Normaliza códigos numéricos válidos a texto4; preserva faltantes."""
    x = pd.to_numeric(valores, errors='coerce')
    valido = x.notna() & x.between(0,9999) & x.eq(np.floor(x))
    return x.where(valido).astype('Int64').astype('string').str.zfill(4)

def cargar_indices():
    """Devuelve catálogo fijo455; mantiene originales y agrega12 columnas normalizadas."""
    d = pd.read_csv(FUENTE, dtype={'ciuo08':'string'})
    d['ciuo08'] = codigo_ocupacion(d.ciuo08)
    if d.ciuo08.isna().any() or d.ciuo08.duplicated().any():
        raise ValueError('Referencia ocupacional con códigos faltantes o duplicados')
    for nombre, original in INDICADORES.items():
        s = pd.to_numeric(d[original], errors='coerce')
        n = s.notna().sum()
        if n < 2 or s.max() <= s.min():
            raise ValueError(f'Índice sin variación: {original}')
        d[f'{nombre}_pct'] = (s.rank(method='average')-1)/(n-1)
        d[f'{nombre}_mm'] = (s-s.min())/(s.max()-s.min())
    for escala in ('pct','mm'):
        d[f'envolvente_{escala}'] = d[[f'{k}_{escala}' for k in ('aioe','webb_ia','llm')]].max(axis=1,skipna=False)
    return d

def agregar_indices(df, col_ocupacion='OFICIO_C8'):
    """Asigna por código, conserva número/orden/índice de filas, sobrescribe columnas comunes."""
    d = df.copy()
    codigos = codigo_ocupacion(d[col_ocupacion])
    tabla = cargar_indices().set_index('ciuo08')
    for c in COLUMNAS:
        d[c] = codigos.map(tabla[c]).astype(float)
    return d

def ocupacion_analitica(df, variante='anterior'):
    """Actual para OCI=1; última ocupación OFICIO2 para DSI=1.

    Sensibilidad variante='buscada' usa OFICIO1 para DSI=1. No rellena
    ocupados sin código ni inactivos. Desempleo principal excluye personas
    sin experiencia/código previo disponible; no representa toda la fuerza laboral.
    """
    if variante not in ('anterior','buscada'):
        raise ValueError('variante debe ser anterior o buscada')
    col = 'OFICIO2_C8_geih' if variante == 'anterior' else 'OFICIO1_C8_geih'
    resultado = pd.Series(pd.NA, index=df.index, dtype='string')
    oc = df['OCI_geih'].eq(1); ds = df['DSI_geih'].eq(1)
    if (oc & ds).any():
        raise ValueError('Ocupados y desocupados simultáneos')
    resultado.loc[oc] = codigo_ocupacion(df.loc[oc,'OFICIO_C8_geih'])
    resultado.loc[ds] = codigo_ocupacion(df.loc[ds,col])
    return resultado

def metadatos():
    d = cargar_indices()
    return {'fuente':str(FUENTE.name),'sha256':hashlib.sha256(FUENTE.read_bytes()).hexdigest(),
        'universo_referencia':'catálogo CIUO-08 A.C. fijo; una fila por ocupación, sin pesos de empleo',
        'filas':len(d),'percentil':'(rank_average(S)-1)/(N_no_faltantes-1)',
        'minmax':'(S-min(S))/(max(S)-min(S))',
        'empates':'rango promedio; extremos empatados pueden no alcanzar exactamente0 y1',
        'envolvente':'max(AIOE,WebbIA,LLM), solo con los tres valores observados',
        'indicadores':{k:{'columna_original':v,'n_referencia':int(d[v].notna().sum()),
                         'min_original':float(d[v].min()),'max_original':float(d[v].max())}
                       for k,v in INDICADORES.items()},
        'llm':'dv_rating_beta: calificación GPT-4, E1+0.5 E2; no probabilidad de desempleo',
        'faltantes':'Se preservan NaN; no se imputan cero ni ocupación promedio.'}
