"""Verificaciones de muestras, ausencia de filtración y fórmulas de la revisión."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy import stats
from preparacion_dml_iv import cargar_indices
from tratamiento_ia import construir_tratamiento
from estimador_dml_iv import _quadratic_set, estimar

HERE = (Path(__file__).resolve().parents[4] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030')
OUT = (Path(__file__).resolve().parents[4] / 'datos/derivados_modelos/oficiales/iv')


def main():
    d = pd.read_parquet((Path(__file__).resolve().parents[4] / 'datos/derivados_modelos/oficiales/iv/base_analitica_2025.parquet'))
    reconstructed, treatment = construir_tratamiento(d)
    assert np.allclose(d.uso_ia, reconstructed, equal_nan=True)
    assert treatment['ruta_inconsistente'] == 0
    assert d.loc[d.edad.notna(),'uso_ia'].notna().all()
    table = cargar_indices().set_index('ciuo08')
    assert np.allclose(d.aioe_pct, d.ciuo08.map(table.aioe_pct).astype(float), equal_nan=True)
    unemployed = d.DSI_geih.eq(1)
    previous = pd.to_numeric(d.OFICIO2_C8_geih,errors='coerce')
    observed = pd.to_numeric(d.ciuo08,errors='coerce')
    assert np.allclose(observed[unemployed].astype(float),previous[unemployed],equal_nan=True)
    r = pd.read_csv((Path(__file__).resolve().parents[4] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/salidas/resultados_dml_iv_aioe.csv'))
    assert set(r.resultado) == {'salario','informalidad','desempleo'}
    assert set(r.instrumento) == {'aioe_pct'}
    assert np.allclose(r.p,2*stats.t.sf(abs(r.theta_iv/r.se),r.clusters-1))
    assert np.allclose(r.first_stage_F,r.first_stage_t**2)
    for f in OUT.glob('particiones_*.parquet'):
        a=pd.read_parquet(f)
        assert a.fold.nunique() == 5
        assert a.groupby('ciuo08').fold.nunique().max()==1
        assert a.groupby('id_donante_geih').fold.nunique().max()==1
    diagnostics=json.loads(((Path(__file__).resolve().parents[4] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/salidas/diagnosticos_modelos.json')).read_text())
    for model in diagnostics:
        a,b,c=model['weak_iv_set']['polynomial']
        solution=_quadratic_set(a,b,c)
        candidates=np.linspace(-300,300,10001)
        included=np.zeros(len(candidates),dtype=bool)
        for lo,hi in solution['intervals']:
            included |= (candidates>=lo)&(candidates<=hi)
        polynomial=(a*candidates+b)*candidates+c
        away=np.abs(polynomial)>1e-10*max(1,abs(a),abs(b),abs(c))
        assert np.array_equal(included[away],(polynomial<=0)[away])
    rng=np.random.default_rng(537)
    n=3000
    x=rng.normal(size=n);z=rng.normal(size=n);v=rng.normal(size=n)
    treatment=z+.4*x+v
    y=2*treatment+.5*x+.4*v+rng.normal(size=n)
    toy=pd.DataFrame({'y':y,'uso_ia':treatment,'aioe_pct':z,'x':x,
                      'FEX_C':np.ones(n),'ciuo08':np.repeat(np.arange(100),30)})
    check=estimar(toy,'y',['x'],seed=537)
    assert abs(check['theta']-2)<.15
    assert check['weak_iv_set']['kind']=='bounded'
    assert check['weak_iv_set']['intervals'][0][0]<2<check['weak_iv_set']['intervals'][0][1]
    print('OK tratamiento, normalización, ocupación anterior, resultados, particiones, conjuntos y recuperación sintética.')


if __name__=='__main__':
    main()
