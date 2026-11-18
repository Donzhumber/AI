"""Ejecuta Stata y contrasta las 48 estimaciones principales AIOE."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import sys
from pathlib import Path
import pandas as pd
ROOT=(Path(__file__).resolve().parents[2] / 'regresiones/modelos')
sys.path.append('/Applications/Stata/utilities')
from pystata import config
config.init('be')
from pystata import stata
from sfi import Scalar
stata.run(f'cd "{ROOT}"\ncapture noisily do "replicar_indices_comparables.do"\nscalar replica_rc=_rc')
if Scalar.getValue('replica_rc')!=0:raise RuntimeError('Error Stata; consultar log')
a=pd.read_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/resultados_indices_comparables.csv'));b=pd.read_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/replica_indices_aioe_stata.csv'))
a=a[a.indice.eq('aioe_pct')]
keys=['familia','modelo','resultado','parametro'];q=a.merge(b,on=keys,suffixes=('_python','_stata'),validate='1:1')
assert len(q)==len(b)==54  # 48 originales + 6 por el contraste exposicion_2021 (did y shiftshare dinámico, 3 resultados cada uno)
for v in ['coef','se','p','nobs','clusters']:q['error_'+v]=(q[v+'_python']-q[v+'_stata']).abs()
q.to_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/validacion_indices_aioe_stata.csv'),index=False)
print(q.filter(like='error_').max().to_string())
assert (q.filter(like='error_')<1e-7).all().all()
print('54 coeficientes e inferencia principales verificados con Stata.')
