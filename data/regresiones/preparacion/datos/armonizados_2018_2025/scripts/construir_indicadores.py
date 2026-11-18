"""Materializa indicadores oficiales ligeros, sin los percentiles legados raw."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from pathlib import Path
import sys,json,hashlib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
ROOT=(Path(__file__).resolve().parents[5]);sys.path.insert(0,str(ROOT))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS,INDICADORES,CARPETA,BASE,IPC
from regresiones.preparacion.datos.armonizados_2018_2025.indicadores import tic_combinado,uso_ia_validado,exposicion_personal
from regresiones.validacion.correcciones.educacion import armonizar_educacion_ecv,COLUMNAS_EDUCACION_ECV
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import COLUMNAS


def main():
 records=[]
 for year,source in MICRODATOS.items():
  schema=set(pq.read_schema(source).names)
  columns=list(dict.fromkeys(['DIRECTORIO','SECUENCIA_P','ORDEN','P6040','P6020','P1_DEPARTAMENTO','CLASE','P6051','FEX_C','OCI_geih','DSI_geih','P6920_geih','INGLABO_geih','inglabo_real_geih','P1910','P1911','P1075','id_donante_geih']+COLUMNAS_EDUCACION_ECV))
  if year>=2021:columns+=['OFICIO_C8_geih','OFICIO2_C8_geih','OFICIO1_C8_geih']
  if year==2025:columns+=['P1084']+[f'P1083S{i}' for i in range(1,22)]
  missing=set(columns)-schema
  if missing:raise ValueError(f'{year}: campos requeridos no disponibles {missing}')
  d=pd.read_parquet(source,columns=list(dict.fromkeys(columns)))
  output=d[['DIRECTORIO','SECUENCIA_P','ORDEN','P1_DEPARTAMENTO','CLASE','P6020','FEX_C','id_donante_geih']].copy()
  assert not output.duplicated(['DIRECTORIO','SECUENCIA_P','ORDEN']).any()
  output['anio']=year;output['edad']=d.P6040
  pet=d.P6040.ge(15);oc=d.OCI_geih.eq(1)&pet;ds=d.DSI_geih.eq(1)&pet
  assert not (oc&ds).any()
  output['pet']=pet.astype('int8');output['ocupado']=oc.astype('int8');output['desocupado']=ds.astype('int8')
  output['desempleo']=ds.astype(float).where(oc|ds)
  output['no_cotiza']=d.P6920_geih.eq(2).astype(float).where(oc&d.P6920_geih.isin([1,2]))
  output['ingreso_laboral_real']=d.inglabo_real_geih.where(oc)
  positive=oc&d.inglabo_real_geih.gt(0)
  output['log_ingreso_laboral_real']=np.log(d.inglabo_real_geih.where(positive))
  # Confirm the commonOctober2025basis against observed nominal labor income.
  ok=oc&d.INGLABO_geih.notna()
  np.testing.assert_allclose(d.loc[ok,'inglabo_real_geih'],d.loc[ok,'INGLABO_geih']*IPC[2025]/IPC[year],rtol=1e-6,atol=1e-6,equal_nan=True)
  output['educacion_ecv']=armonizar_educacion_ecv(d)
  output['tic_combinado']=tic_combinado(d)
  output['tic_respuesta_valida']=output.tic_combinado.notna()
  if year==2025:
   output['uso_ia'],report=uso_ia_validado(d)
   output['ruta_ia_valida']=output.uso_ia.notna()
  else:
   output['uso_ia']=np.nan;output['ruta_ia_valida']=False;report={'nota':'ÍtemIA2025 no disponible; no inferir no uso en otros años.'}
  if year>=2021:
   exposures=exposicion_personal(d)
   pd.testing.assert_index_equal(output.index,exposures.index)
   output=pd.concat([output,exposures],axis=1)
  else:
   output['ciuo08']=pd.Series(pd.NA,index=output.index,dtype='string')
   for col in COLUMNAS:output[col]=np.nan
  output['cobertura_comun_cinco']=output[['aioe_pct','webb_ia_pct','llm_pct','software_pct','robots_pct']].notna().all(axis=1)
  target=INDICADORES[year];target.parent.mkdir(exist_ok=True)
  output.to_parquet(target,index=False,compression='zstd')
  records.append({'anio':year,'filas':len(output),'columnas':len(output.columns),'archivo':str(target.relative_to(BASE)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'ocupados':int(oc.sum()),'desocupados':int(ds.sum()),'poblacion_pet':int(pet.sum()),'tic_validos':int(output.tic_respuesta_valida.sum()),'educacion_ausente':int(output.educacion_ecv.isna().sum()),'exposicion_comun_observada':int(output.cobertura_comun_cinco.sum()),'ia':report})
  print(f'{year}: tabla oficial {output.shape}',flush=True)
 ((Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/diagnosticos/manifest_indicadores.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
