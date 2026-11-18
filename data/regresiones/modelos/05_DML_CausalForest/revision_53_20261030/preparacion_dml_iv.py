"""Preparación ECV–GEIH 2025, sin alterar insumos ni imponer tratamiento.

Educación del receptor: nivel alcanzado P8587 si no estudia y nivel actual
P1088 si estudia (se controla también asistencia). No es años completados.
H_tic indica uso personal de computador en cualquier lugar más internet
en el hogar; es contemporáneo, no tenencia ni dotación previa.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

QUARTO = (Path(__file__).resolve().parents[4])
sys.path.insert(0,str(QUARTO))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS
sys.path.insert(0, str((Path(__file__).resolve().parents[4] / 'datos/exposicion_ia')))
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import cargar_indices, ocupacion_analitica

CONTINUAS = ['edad', 'edad2', 'mujer', 'rural', 'jefe', 'H_tic', 'asiste']
CATEGORICAS = ['edu_cat', 'dpto', 'oficio_2d']
CONTROLES = CONTINUAS + CATEGORICAS
RESULTADOS = ['ln_salario_real', 'no_cotiza', 'desempleo']

def binaria(s, positivo=1, validos=(1, 2)):
    return s.eq(positivo).astype(float).where(s.isin(validos))

def cargar_2025(path=None, variante_ocupacion='anterior'):
    """Devuelve (datos, diagnóstico). Conserva filas; universos vía outcomes NaN."""
    path = Path(path or (Path(__file__).resolve().parents[4] / 'datos/armonizados_2018_2025/microdatos/ecv_geih_imputada_2025.parquet'))
    schema = pq.ParquetFile(path).schema.names
    cols = ['P6040','P6020','CLASE','P1_DEPARTAMENTO','P6051','P8586',
            'P8587','P1088','P3042_geih','P1910','P1911','P1075',
            'OCI_geih','DSI_geih','P6920_geih','INGLABO_geih',
            'OFICIO_C8_geih','OFICIO1_C8_geih','OFICIO2_C8_geih','FEX_C',
            'id_persona','id_hogar','id_donante_geih','P1084','P1083']
    cols += [c for c in schema if c.startswith('P1083S')]
    missing = sorted(set(cols) - set(schema))
    if missing:
        raise ValueError(f'Columnas requeridas ausentes: {missing}')
    d = pd.read_parquet(path, columns=list(dict.fromkeys(cols)))
    d['edad'] = d.P6040.where(d.P6040.between(15, 110))
    d['edad2'] = (d.edad / 10) ** 2
    d['mujer'] = binaria(d.P6020, 2)
    d['rural'] = binaria(d.CLASE, 2)
    d['jefe'] = binaria(d.P6051, 1, tuple(range(1, 15)))
    d['dpto'] = pd.to_numeric(d.P1_DEPARTAMENTO, errors='coerce')
    d['asiste'] = binaria(d.P8586)
    alcanzado = d.P8587.map({1:0,2:0,3:1,4:2,5:3,6:4,7:4,8:4,9:4,10:5,11:5,12:6,13:6})
    actual = d.P1088.map({1:0,2:1,3:2,4:3,5:4,6:4,7:5,8:6})
    d['edu_cat'] = alcanzado.where(d.P8586.eq(2), actual.where(d.P8586.eq(1)))
    d['H_edu'] = d.edu_cat.ge(5).astype(float).where(d.edu_cat.notna())
    d['edu_cat_geih'] = d.P3042_geih.map({1:0,2:0,3:1,4:2,5:3,6:4,7:4,8:4,9:4,10:5,11:6,12:6,13:6})
    desktop = binaria(d.P1910, 1, (1,2,3,4,5))
    desktop = d.P1910.isin([1,2,3,4]).astype(float).where(desktop.notna())
    laptop = d.P1911.isin([1,2,3,4]).astype(float).where(d.P1911.isin([1,2,3,4,5]))
    computer = pd.concat([desktop,laptop],axis=1).max(axis=1,skipna=False)
    internet = binaria(d.P1075)
    d['H_tic'] = (computer.eq(1) & internet.eq(1)).astype(float).where(computer.notna() & internet.notna())
    d['ciuo08'] = ocupacion_analitica(d, variante=variante_ocupacion)
    d['oficio_2d'] = pd.to_numeric(d.ciuo08, errors='coerce').astype(float) // 100
    tabla = cargar_indices().set_index('ciuo08')
    d['aioe_pct'] = d.ciuo08.map(tabla.aioe_pct).astype(float)
    occupied = d.OCI_geih.eq(1)
    pea = occupied | d.DSI_geih.eq(1)
    income = pd.to_numeric(d.INGLABO_geih, errors='coerce')
    d['ln_salario_real'] = np.log(income.where(occupied & income.gt(0) & np.isfinite(income)))
    d['no_cotiza'] = binaria(d.P6920_geih, 2).where(occupied)
    d['desempleo'] = d.DSI_geih.eq(1).astype(float).where(pea)
    d['anio'] = 2025
    diagnostico = {'filas':len(d),'ocupados':int(occupied.sum()),'pea':int(pea.sum()),
        'desocupados':int(d.DSI_geih.eq(1).sum()),
        'desocupados_sin_ocupacion_previa':int((d.DSI_geih.eq(1)&d.ciuo08.isna()).sum()),
        'edad_menor15':int(d.P6040.lt(15).sum()),
        'faltantes_controles':{c:int(d[c].isna().sum()) for c in CONTROLES},
        'donantes_unicos':int(d.id_donante_geih.nunique()),
        'hogares_unicos':int(d.id_hogar.nunique()),
        'clase':d.CLASE.value_counts(dropna=False).to_dict(),
        'outcomes_validos':{c:int(d[c].notna().sum()) for c in RESULTADOS}}
    diagnostico['muestras_base'] = {c:len(muestra_resultado(d,c)) for c in RESULTADOS}
    return d, diagnostico

def muestra_resultado(d, resultado, required=()):
    """Edad>=15, peso positivo, AIOE, outcome y controles observados."""
    if resultado not in RESULTADOS:
        raise ValueError(f'Resultado desconocido: {resultado}')
    cols = [resultado,'aioe_pct','FEX_C'] + CONTROLES + list(required)
    mask = d[cols].notna().all(axis=1) & d.FEX_C.gt(0) & np.isfinite(d.FEX_C)
    mask &= np.isfinite(d[cols].select_dtypes(include='number')).all(axis=1)
    return d.loc[mask].copy()

def matriz_controles(d):
    """X numérica, categorías explícitas: nunca departamento como orden continuo."""
    return pd.get_dummies(d[CONTROLES],columns=CATEGORICAS,drop_first=True,dtype=float).astype(float)

if __name__ == '__main__':
    import json
    _, diagnostic = cargar_2025()
    print(json.dumps(diagnostic,ensure_ascii=False,indent=2))
