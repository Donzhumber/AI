"""Verifica indicadores desde microdatos, sin reestimar ni modificar fuentes."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from pathlib import Path
import sys,json
import numpy as np
import pandas as pd
ROOT=(Path(__file__).resolve().parents[5])
sys.path.insert(0,str(ROOT))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS,PANEL_2018_2025,PANEL_2021_2025,PANEL_TIC_DTA,CARPETA
from regresiones.preparacion.datos.armonizados_2018_2025.indicadores import tic_combinado


def main():
 p=pd.read_parquet(PANEL_2018_2025)
 assert p.shape==(2640,101)
 assert p.groupby('id_cohorte').anio.nunique().eq(8).all()
 assert not p.duplicated(['id_cohorte','anio']).any()
 assert p.id_cohorte.nunique()==330
 assert p.anio.min()==2018 and p.anio.max()==2025
 small=pd.read_parquet(PANEL_2021_2025)
 pd.testing.assert_frame_equal(small.reset_index(drop=True),p.loc[p.anio.ge(2021)].reset_index(drop=True))
 tests=[]
 for year,path in MICRODATOS.items():
  cols=['P6040','P1_DEPARTAMENTO','P6020','FEX_C','OCI_geih','DSI_geih','P6920_geih','inglabo_real_geih','P1910','P1911','P1075']
  d=pd.read_parquet(path,columns=cols)
  d=d.loc[d.P6040.ge(15)&np.isfinite(d.FEX_C)&d.FEX_C.gt(0)].copy()
  born=year-d.P6040
  gen=np.select([born.le(1964),born.le(1974),born.le(1984),born.le(1994)],[1,2,3,4],default=5)
  d['id_cohorte']=d.P1_DEPARTAMENTO.astype(int).astype(str)+'_'+d.P6020.astype(int).astype(str)+'_'+pd.Series(gen,index=d.index).astype(str)
  d['tic']=tic_combinado(d)
  d['FEX_C']=d.FEX_C.astype('float64')
  expected=p.loc[p.anio.eq(year)].set_index('id_cohorte')
  for key,g in d.groupby('id_cohorte'):
   oc=g.OCI_geih.eq(1);ds=g.DSI_geih.eq(1)
   assert not (oc&ds).any()
   pea=oc|ds;pension=oc&g.P6920_geih.isin([1,2]);positive=oc&g.inglabo_real_geih.gt(0);tic=g.tic.notna()
   row=expected.loc[key]
   values={'tasa_desempleo':g.loc[ds,'FEX_C'].sum()/g.loc[pea,'FEX_C'].sum() if pea.any() else np.nan,
    'prop_no_cotiza_respuesta12':g.loc[pension&g.P6920_geih.eq(2),'FEX_C'].sum()/g.loc[pension,'FEX_C'].sum() if pension.any() else np.nan,
    'log_sal_real_medio':np.log(np.average(g.loc[positive,'inglabo_real_geih'],weights=g.loc[positive,'FEX_C'])) if positive.any() else np.nan,
    'prop_H_tic':np.average(g.loc[tic,'tic'],weights=g.loc[tic,'FEX_C']) if tic.any() else np.nan}
   for name,value in values.items():
    np.testing.assert_allclose(row[name],value,rtol=1e-12,atol=1e-12,equal_nan=True)
   assert row.n_obs_pet==len(g)
  tests.append({'anio':year,'cohortes':len(expected),'receptores_pet':len(d),'indicadores_recalculados':['desempleo','no_cotizacion','log_media_ingreso_positivo','TIC_combinado'],'coincide':True})
  print(f'{year}: 330 cohortes y cuatro indicadores reproducidos desde personas',flush=True)
 for c in [x for x in p if x.endswith(('_pct_c','_pct_d','_mm_c','_mm_d'))]:
  assert p.groupby('id_cohorte')[c].nunique().le(1).all()
  assert p[c].dropna().between(0,1).all()
 export=pd.read_stata(PANEL_TIC_DTA)
 assert len(export)==2640
 aligned=export.set_index(['id_cohorte','anio']).reindex(pd.MultiIndex.from_frame(p[['id_cohorte','anio']]))
 for original,alias in [('tasa_desempleo','y_des'),('prop_no_cotiza_respuesta12','y_inf'),('log_sal_real_medio','y_sal'),('prop_H_tic','x_tic')]:
  np.testing.assert_allclose(p[original],aligned[alias],rtol=1e-12,atol=1e-12,equal_nan=True)
 report={'pruebas_anuales':tests,'filas_panel':len(p),'columnas_panel':len(p.columns),'llaves_unicas':True,'panel_2021_subconjunto_exacto':True,'basales_constantes':True,'exportacion_stata_identica':True,'causalidad_certificada':False}
 ((Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/diagnosticos/verificacion_coleccion.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print('OK colección anual, cohortes, fórmulas, basales y exportación Stata.')

if __name__=='__main__':main()
