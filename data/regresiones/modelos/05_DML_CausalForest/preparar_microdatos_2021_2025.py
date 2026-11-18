#!/usr/bin/env python3
"""Muestra ML armonizada: percentiles fijos y ocupación actual/última del Anexo.
No estima DML-IV ni convierte ausencias en categorías negativas.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import sys,json,hashlib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
BASE_DIR=(Path(__file__).resolve().parents[3])
sys.path.insert(0,str(BASE_DIR))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS,IPC,INDICES,CARPETA
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import cargar_indices,ocupacion_analitica
OUTPUT=(Path(__file__).resolve().parents[3] / 'datos/derivados_modelos/oficiales/microdatos_causal_ml_2021_2025.parquet')
EXP=["aioe_pct","webb_ia_pct","llm_pct","software_pct","robots_pct","envolvente_pct"]
EDU={1:0,2:0,3:1,4:2,5:2,6:2,7:2,8:3,9:3,10:4,11:4,12:4,13:4}

def main():
    frames=[];sources={};by_year=[]
    cols=['P6040','P6020','CLASE','P1_DEPARTAMENTO','P6051','OCI_geih','DSI_geih',
          'P6920_geih','INGLABO_geih','OFICIO_C8_geih','OFICIO1_C8_geih','OFICIO2_C8_geih',
          'FEX_C','P1910','P1911','P1075','P3042_geih','id_donante_geih']
    for year in range(2021,2026):
        path=MICRODATOS[year];schema=set(pq.read_schema(path).names)
        missing=set(cols)-schema
        if missing: raise ValueError(f'{year}: faltan {missing}')
        d=pd.read_parquet(path,columns=cols)
        for col in cols: d[col]=pd.to_numeric(d[col],errors='coerce')
        d=d.loc[d.P6040.ge(15)&d.FEX_C.gt(0)&np.isfinite(d.FEX_C)].copy()
        d['anio']=year
        frames.append(d);by_year.append({'anio':year,'personas_pet':len(d)})
        sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    d=pd.concat(frames,ignore_index=True)
    d['ciuo08']=ocupacion_analitica(d,variante='anterior')
    d=d.merge(cargar_indices()[['ciuo08']+EXP],on='ciuo08',how='left',validate='m:1')
    d['post']=d.anio.ge(2023).astype(float)
    d['pre22']=d.anio.eq(2022).astype(float);d['t_cat']=d.anio-2021
    d['edad']=d.P6040.clip(15,95);d['edad2']=(d.edad/10)**2
    d['mujer']=d.P6020.eq(2).astype(float).where(d.P6020.isin([1,2]))
    d['rural']=d.CLASE.eq(2).astype(float).where(d.CLASE.isin([1,2]))
    d['jefe']=d.P6051.eq(1).astype(float).where(d.P6051.notna())
    d['dpto']=pd.to_numeric(d.P1_DEPARTAMENTO,errors='coerce')
    d['edu_cat']=d.P3042_geih.map(EDU)
    d['H_edu']=d.edu_cat.eq(4).astype(float).where(d.edu_cat.notna())
    d['edad_cat']=np.select([d.edad.lt(30),d.edad.lt(50)],[1,2],default=3)
    valid_tic=d.P1910.isin([1,2,3,4,5])&d.P1911.isin([1,2,3,4,5])&d.P1075.isin([1,2])
    comp=d.P1910.isin([1,2,3,4])|d.P1911.isin([1,2,3,4])
    d['H_tic']=(comp&d.P1075.eq(1)).astype(float).where(valid_tic)
    d['oficio_2d']=pd.to_numeric(d.ciuo08,errors='coerce')//100
    oc=d.OCI_geih.eq(1);pea=oc|d.DSI_geih.eq(1)
    d['inglabo_real']=d.INGLABO_geih*d.anio.map({y:IPC[2025]/IPC[y] for y in range(2021,2026)})
    d['ln_salario_real']=np.log(d.inglabo_real.where(oc&d.inglabo_real.gt(0)))
    d['no_cotiza']=d.P6920_geih.eq(2).astype(float).where(oc&d.P6920_geih.isin([1,2]))
    d['desempleo']=d.DSI_geih.eq(1).astype(float).where(pea)
    (Path(__file__).resolve().parents[3] / 'regresiones/resultados').mkdir(parents=True,exist_ok=True)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUTPUT,index=False)
    manifest={'fuentes_sha256':sources,'indices_sha256':hashlib.sha256(INDICES.read_bytes()).hexdigest(),
      'salida':str(OUTPUT),'sha256_salida':hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
      'filas':len(d),'por_anio':by_year,'ocupacion':'actual ocupados; última desocupados; sin completar buscada',
      'percentil':'(rango promedio-1)/(N observado-1), catálogo fijo',
      'faltantes':'educación, TIC, ocupación y resultados inválidos permanecen ausentes'}
    (BASE_DIR/'regresiones/resultados/microdatos_causal_ml_2021_2025.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
