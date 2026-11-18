"""Reestima exclusivamente R-learner con insumos armonizados, sin tocar DML-IV."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
import os
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ.setdefault(key,'4')
from pathlib import Path
import json,hashlib,time
import pandas as pd
from rlearner_armonizado import estimar_cate_rlearner
import sys
BASE=(Path(__file__).resolve().parents[3])
sys.path.insert(0,str(BASE))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import CARPETA
DATA_PARQUET=(Path(__file__).resolve().parents[3] / 'datos/derivados_modelos/oficiales/microdatos_causal_ml_2021_2025.parquet')
HERE=(Path(__file__).resolve().parents[3] / 'regresiones/modelos/05_DML_CausalForest')

def main():
 d=pd.read_parquet(DATA_PARQUET);rows=[]
 for result,y in [('salario','ln_salario_real'),('informalidad','no_cotiza'),('desempleo','desempleo')]:
  sample=d[d[y].notna()].copy();t=time.time()
  print(f'R-learner {result}: {len(sample):,} candidatos',flush=True)
  r=estimar_cate_rlearner(sample,y,exp_var='aioe_pct')
  r.update(resultado=result,indice='aioe_pct');rows.append(r)
  ((Path(__file__).resolve().parents[3] / 'regresiones/modelos/05_DML_CausalForest/progreso_cate_armonizado.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2))
  print(result,r, 'segundos',round(time.time()-t,1),flush=True)
 tmp=(Path(__file__).resolve().parents[3] / 'regresiones/modelos/05_DML_CausalForest/resultados_cate.completo.tmp')
 tmp.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 target=(Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_cate.json')
 destination=target.resolve() if target.is_symlink() else target
 final_tmp=destination.with_suffix('.json.tmp')
 final_tmp.write_text(tmp.read_text());tmp.unlink()
 final_tmp.replace(destination)
 manifest={'base':str(DATA_PARQUET.relative_to(BASE)),'sha256_base':hashlib.sha256(DATA_PARQUET.read_bytes()).hexdigest(),
  'procedimiento':str((Path(__file__).resolve().parents[3] / 'regresiones/modelos/05_DML_CausalForest/estimar_cate_armonizado.py')),'sha256_procedimiento':hashlib.sha256((Path(__file__).resolve().parents[3] / 'regresiones/modelos/05_DML_CausalForest/estimar_cate_armonizado.py').read_bytes()).hexdigest(),
  'metodo':'R-learner de pendiente exploratoria, nested5/3 por ocupación; BLP sin intercepto agrupadoocupación',
  'parametros':{'n_splits':5,'inner_splits':3,'seed':42,'max_iter_tau':40,'min_samples_leaf_tau':40},
  'salida_sha256':hashlib.sha256(((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_cate.json')).read_bytes()).hexdigest()}
 ((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/manifest_cate_armonizado.json')).write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
