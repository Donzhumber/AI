"""Comprobaciones independientes de escala, asignación laboral y agregación."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import *

ref=cargar_indices()
for k,original in INDICADORES.items():
    s=ref[original]; valid=s.notna(); x=s[valid].to_numpy()
    np.testing.assert_allclose(ref.loc[valid,f'{k}_pct'],(rankdata(x,method='average')-1)/(len(x)-1))
    np.testing.assert_allclose(ref.loc[valid,f'{k}_mm'],(x-x.min())/(x.max()-x.min()))
    assert ref.loc[~valid,[f'{k}_pct',f'{k}_mm']].isna().all().all()
assert ref.envolvente_pct.notna().equals(ref[['aioe_pct','webb_ia_pct','llm_pct']].notna().all(axis=1))
# Distinguish unemployment history from sought occupation and refuse fallback for missing employed codes.
d=pd.DataFrame({'OCI_geih':[1,1,0,0,0],'DSI_geih':[0,0,1,1,0],
    'OFICIO_C8_geih':[1111,None,None,None,None],'OFICIO1_C8_geih':[2222,2222,2222,2222,2222],
    'OFICIO2_C8_geih':[3333,3333,3333,None,3333]})
assert ocupacion_analitica(d).tolist()==['1111',pd.NA,'3333',pd.NA,pd.NA]
assert ocupacion_analitica(d,'buscada').tolist()==['1111',pd.NA,'2222','2222',pd.NA]
# Independent reconstruction of one cohort in2022 from raw data (not exported aggregate).
p=ROOT.parents[1]/'datos/imputados/ecv_geih_imputada_2022.parquet'
d=pd.read_parquet(p,columns=['P1_DEPARTAMENTO','P6020','P6040','FEX_C','OCI_geih','OFICIO_C8_geih'])
born=2022-d.P6040;gen=np.select([born.le(1964),born.le(1974),born.le(1984),born.le(1994)],[1,2,3,4],default=5)
d['id_cohorte']=d.P1_DEPARTAMENTO.astype(int).astype(str)+'_'+d.P6020.astype(int).astype(str)+'_'+pd.Series(gen).astype(str)
a=pd.read_csv(ROOT/'exposicion_cohortes_2022_2025.csv');row=a[a.anio.eq(2022)].iloc[0]
sub=d[d.id_cohorte.eq(row.id_cohorte)&d.P6040.ge(15)&d.OCI_geih.eq(1)&d.FEX_C.gt(0)&np.isfinite(d.FEX_C)]
x=codigo_ocupacion(sub.OFICIO_C8_geih).map(ref.set_index('ciuo08').aioe_pct)
valid=x.notna();expected=(x[valid]*sub.loc[valid,'FEX_C']).sum()/sub.loc[valid,'FEX_C'].sum()
np.testing.assert_allclose(expected,row.aioe_pct,atol=1e-14)
print('APROBADO: 5 percentiles, 5 MinMax, faltantes, envolvente completa, asignación actual/anterior/buscada y agregación independiente cohorte2022.')
