"""Replica todos los donantes de2021 con el kernel moderno del Anexo."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from pathlib import Path
import json
import sys
import time
import numpy as np
import pandas as pd
ROOT=(Path(__file__).resolve().parents[5])
sys.path.insert(0,str(ROOT))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import FUENTES_GEIH,FUENTES_ECV,MICRODATOS,CARPETA
from regresiones.validacion.evaluacion_transversal.reproducir_integracion import preparar
from regresiones.validacion.correcciones.educacion import COLUMNAS_EDUCACION_ECV


def main():
 start=time.monotonic()
 gcols=['P6040','P3271','P6050','DIRECTORIO','SECUENCIA_P','DPTO','CLASE','P3042','P6240']
 ecols=list(dict.fromkeys(['P6040','P6020','P6051','CANT_PERSONAS_HOGAR','P1_DEPARTAMENTO','CLASE','P6240']+COLUMNAS_EDUCACION_ECV))
 g=pd.read_parquet((Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/reconstruccion/fuentes/GEIH/2021/geih_son_original_ensamblada_2021.parquet'),columns=gcols).reset_index(drop=True)
 e=pd.read_parquet((Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/reconstruccion/fuentes/ECV/2021/total_ecv_2021.parquet'),columns=ecols).dropna(subset=['CLASE','P1_DEPARTAMENTO']).reset_index(drop=True)
 # Activity missingness is structural only below15 in GEIH marco2018.
 assert not (g.P6040.ge(15)&g.P6240.isna()).any()
 *_,matched,fallback=preparar(g,e)
 old=pd.read_parquet((Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/microdatos/ecv_geih_imputada_2021.parquet'),columns=['id_donante_geih','en_fallback'])
 result={'anio':2021,'donantes_fuente':len(g),'receptores':len(e),
  'diferencias_donante':int(np.sum(matched!=old.id_donante_geih.to_numpy())),
  'diferencias_ampliacion':int(np.sum(fallback!=old.en_fallback.to_numpy())),
  'segundos':time.monotonic()-start,
  'metodo':'Réplica completa del vector6D, educación moderna, bloqueo y buscar_vecinos compartidos; no muestreo'}
 assert result['diferencias_donante']==0 and result['diferencias_ampliacion']==0,result
 ((Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/diagnosticos/replica_completa_2021.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
