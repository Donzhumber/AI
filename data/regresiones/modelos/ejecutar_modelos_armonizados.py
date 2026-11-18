"""Ejecutor de modelos con registro único de bases.
Uso: python3 ejecutar_modelos_armonizados.py --todo
      python3 ejecutar_modelos_armonizados.py --certificar
La certificación verifica salidas existentes; --todo vuelve a estimar.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from pathlib import Path
import argparse,json,hashlib,subprocess,sys,os
ROOT=(Path(__file__).resolve().parents[2] / 'regresiones/modelos')
BASE=(Path(__file__).resolve().parents[2])
sys.path.insert(0,str(BASE))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import CARPETA,MICRODATOS,PANEL_2021_2025,PANEL_2018_2025,PANEL_TIC_DTA
OUT=(Path(__file__).resolve().parents[2] / 'regresiones/resultados')
ML=(Path(__file__).resolve().parents[2] / 'regresiones/modelos/05_DML_CausalForest')
STEPS=[(Path(__file__).resolve().parents[2] / 'regresiones/modelos/estimar_indices_comparables.py'),(Path(__file__).resolve().parents[2] / 'regresiones/modelos/replicar_indices_comparables.py'),
 (Path(__file__).resolve().parents[2] / 'regresiones/modelos/verificar_indices_comparables.py'),(Path(__file__).resolve().parents[2] / 'regresiones/modelos/05_DML_CausalForest/estimar_dml_did_continuo.py'),
 (Path(__file__).resolve().parents[2] / 'regresiones/modelos/estimar_panel_tic_principales.py'),(Path(__file__).resolve().parents[2] / 'regresiones/modelos/wild_cluster_bootstrap_panel_tic.py'),
 (Path(__file__).resolve().parents[2] / 'regresiones/modelos/diagnosticos_residuos_panel_tic.py'),(Path(__file__).resolve().parents[2] / 'regresiones/modelos/05_DML_CausalForest/preparar_microdatos_2021_2025.py'),
 (Path(__file__).resolve().parents[2] / 'regresiones/modelos/05_DML_CausalForest/estimar_cate_armonizado.py'),(Path(__file__).resolve().parents[2] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/ejecutar_revision.py'),
 (Path(__file__).resolve().parents[2] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/verificar_revision.py')]

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--todo',action='store_true');ap.add_argument('--certificar',action='store_true');args=ap.parse_args()
 OUT.mkdir(exist_ok=True);logs=(Path(__file__).resolve().parents[2] / 'regresiones/resultados/logs');logs.mkdir(exist_ok=True)
 if args.todo:
  env=dict(os.environ,OMP_NUM_THREADS='4',OPENBLAS_NUM_THREADS='1',VECLIB_MAXIMUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
  for script in STEPS:
   print('Ejecutando',script.name,flush=True)
   with (logs/(script.stem+'.log')).open('w') as f:
    subprocess.run([sys.executable,str(script)],cwd=script.parent,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 import pandas as pd,numpy as np
 classic=pd.read_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/resultados_indices_comparables.csv'))
 assert len(classic)==982 and np.isfinite(classic[['coef','se','p']].to_numpy()).all()
 assert (classic.groupby(['familia','modelo','resultado']).nobs.nunique()==1).all()
 replica=pd.read_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/validacion_indices_aioe_stata.csv'));assert len(replica)==54
 assert (replica.filter(like='error_')<1e-7).all().all()
 did=pd.read_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_dml_did_continuo.csv'));assert len(did)==15
 assert did.nobs.eq(330).all() and did.clusters.eq(33).all()
 cate=json.loads(((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_cate.json')).read_text());assert len(cate)==3
 cm=json.loads(((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/manifest_cate_armonizado.json')).read_text());assert sha(BASE/Path(cm['base']))==cm['sha256_base']
 for path,rows in [(PANEL_2018_2025,2640),(PANEL_2021_2025,1650)]:
  frame=pd.read_parquet(path);assert len(frame)==rows and not frame.duplicated(['id_cohorte','anio']).any()
 report={'fuentes_sha256':{str(p.relative_to(BASE)):sha(p) for p in [*MICRODATOS.values(),PANEL_2018_2025,PANEL_2021_2025,PANEL_TIC_DTA]},
  'coeficientes_clasicos':982,'replicas_stata':54,'contrastes_dml_did':15,'resultados_cate':cate,
  'panel_tic':pd.read_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/panel_tic_inferencia_departamento.csv')).to_dict('records'),
  'seleccion_panel_tic':pd.read_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/panel_tic_principales_reconstruido.csv')).to_dict('records'),
  'diagnosticos_tic':pd.read_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/diagnosticos_residuos_panel_tic.csv')).to_dict('records'),
  'scripts_sha256':{str(p.relative_to(BASE)):sha(p) for p in [*STEPS,(Path(__file__).resolve().parents[2] / 'regresiones/modelos/05_DML_CausalForest/rlearner_armonizado.py'),(Path(__file__).resolve().parents[2] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/estimador_dml_iv.py'),(Path(__file__).resolve().parents[2] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/preparacion_dml_iv.py'),(Path(__file__).resolve().parents[2] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/tratamiento_ia.py')]},'fuentes_canonicas':True,'limite':'Concordancia y reproducción numérica no certifican identificación causal.'}
 ((Path(__file__).resolve().parents[2] / 'regresiones/resultados/certificacion_modelos.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print('Certificados 982 coeficientes, 54 réplicas, 15 contrastes DML-DiD y tres calibraciones R-learner.')
if __name__=='__main__':main()
