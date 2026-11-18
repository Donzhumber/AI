"""Controles de resultados, muestra común y trazabilidad de índices vigentes."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from pathlib import Path
import json
import numpy as np
import pandas as pd
ROOT=(Path(__file__).resolve().parents[2] / 'regresiones/modelos')
r=pd.read_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/resultados_indices_comparables.csv'))
assert len(r)==982
assert np.isfinite(r[['coef','se','p','ci_lower','ci_upper']].to_numpy()).all()
assert (r.se>0).all() and r.p.between(0,1).all()
assert ((r.ci_lower<=r.coef)&(r.coef<=r.ci_upper)).all()
assert (r.groupby(['familia','modelo','resultado']).nobs.nunique()==1).all()
assert (r.groupby(['familia','modelo','resultado']).clusters.nunique()==1).all()
assert r[~r.modelo.eq('sensibilidad_buscada')].indice.nunique()==12
for path,n in [('exposicion_departamental_indices_2022.csv',33),('exposicion_cohortes_indices_2022.csv',330)]:
 d=pd.read_csv(ROOT/path);assert len(d)==n
 c=[k for k in d if k.endswith(('_pct','_mm'))];assert len(c)==12
 assert d[c].notna().all().all() and d[c].ge(0).all().all() and d[c].le(1).all().all()
 for scale in ['pct','mm']:assert (d['envolvente_'+scale]+1e-12>=d[['aioe_'+scale,'webb_ia_'+scale,'llm_'+scale]].max(axis=1)).all()
v=pd.read_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/validacion_indices_aioe_stata.csv'));assert len(v)==54;assert(v.filter(like='error_')<1e-7).all().all()
summary={'coeficientes_finitos':len(r),'indices_separados_y_sensibilidades':12,'estimaciones_replicadas_stata':len(v),'muestras_comunes_por_modelo':True,'departamentos':33,'cohortes':330,'max_diferencias_stata':v.filter(like='error_').max().to_dict()}
((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/verificacion_indices_comparables.json')).write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
