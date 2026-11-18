"""Reproduce la revisión de la sección 5.3 sin alterar las estimaciones anteriores."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))
import os
os.environ.setdefault('OMP_NUM_THREADS', '4')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '4')
from pathlib import Path
import argparse
import hashlib
import json
import platform
import sys
import time
import numpy as np
import pandas as pd
import scipy
import sklearn

from preparacion_dml_iv import cargar_2025, muestra_resultado, CONTROLES, CATEGORICAS, QUARTO
from tratamiento_ia import construir_tratamiento
from estimador_dml_iv import estimar

HERE = (Path(__file__).resolve().parents[4] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030')
SALIDAS = (Path(__file__).resolve().parents[4] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/salidas')
DATOS = QUARTO / 'datos/derivados_modelos/oficiales/iv'
OUTCOMES = {'salario':'ln_salario_real', 'informalidad':'no_cotiza', 'desempleo':'desempleo'}


def limpio(obj):
    if isinstance(obj, dict):
        return {str(k): limpio(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, np.ndarray)):
        return [limpio(v) for v in obj]
    if isinstance(obj, (float, np.floating)):
        return float(obj) if np.isfinite(obj) else None
    if isinstance(obj, np.integer):
        return int(obj)
    return obj


def guardar_json(path, datos):
    path.write_text(json.dumps(limpio(datos), ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def texto_conjunto(conjunto):
    if conjunto['kind'] == 'all_real':
        return 'Toda la recta real'
    if conjunto['kind'] == 'empty':
        return 'Vacío'
    def extremo(v):
        if v == -np.inf:
            return '−∞'
        if v == np.inf:
            return '+∞'
        return f'{v:.4f}'.replace('.', ',')
    return ' ∪ '.join(f'[{extremo(a)}; {extremo(b)}]' for a,b in conjunto['intervals'])


def corrida(df, resultado, variante, seed, filas, diagnos):
    y = OUTCOMES[resultado]
    s = muestra_resultado(df, y, required=['uso_ia'])
    print(f'Estimando {variante} / {resultado} / semilla {seed}: N={len(s):,}', flush=True)
    t0 = time.time()
    r = estimar(s, y, CONTROLES, categorical_cols=CATEGORICAS, seed=seed)
    indices = r.pop('row_index')
    fold_ids = r.pop('fold_id')
    audit = s.loc[indices, ['id_persona','id_hogar','id_donante_geih','ciuo08','FEX_C','uso_ia','aioe_pct', y]].copy()
    audit['fold'] = fold_ids
    for col in ['ciuo08', 'id_donante_geih']:
        if audit.groupby(col, dropna=False)['fold'].nunique().max() > 1:
            raise AssertionError(f'Filtración entre particiones por {col}')
    audit.to_parquet(DATOS / f'particiones_{variante}_{resultado}_{seed}.parquet', index=False)
    weak = r.pop('weak_iv_set')
    fila = {k:v for k,v in r.items() if not isinstance(v, (dict,list))}
    fila.update({'resultado': resultado, 'instrumento':'aioe_pct', 'variante':variante,
                 'theta_iv':r['theta'], 'f_stat_primer_paso':r['first_stage_F'],
                 'tratados':int(s.uso_ia.eq(1).sum()), 'controles':int(s.uso_ia.eq(0).sum()),
                 'poblacion_expandida':float(s.FEX_C.sum()),
                 'ar_tipo':weak['kind'], 'ar_conjunto':texto_conjunto(weak),
                 'segundos':round(time.time()-t0,2)})
    filas.append(fila)
    diagnos.append({'resultado':resultado,'variante':variante, **r, 'weak_iv_set':weak})
    pd.DataFrame(filas).to_csv((Path(__file__).resolve().parents[4] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/salidas/resultados_todas_variantes.csv'), index=False)
    guardar_json((Path(__file__).resolve().parents[4] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/salidas/diagnosticos_modelos.json'), diagnos)
    print(f"  theta={r['theta']:.6f}, F={r['first_stage_F']:.4f}, conjunto={fila['ar_conjunto']}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--solo-principal', action='store_true')
    args = parser.parse_args()
    SALIDAS.mkdir(parents=True, exist_ok=True)
    DATOS.mkdir(parents=True, exist_ok=True)
    df, datos_diag = cargar_2025()
    df['uso_ia'], tratamiento_diag = construir_tratamiento(df)
    assert df.loc[df.edad.notna(), 'uso_ia'].notna().all(), 'Tratamiento adulto incompleto'
    df.to_parquet((Path(__file__).resolve().parents[4] / 'datos/derivados_modelos/oficiales/iv/base_analitica_2025.parquet'), index=False)
    guardar_json((Path(__file__).resolve().parents[4] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/salidas/diagnostico_preparacion.json'), {'datos':datos_diag, 'tratamiento':tratamiento_diag})
    filas, diagnosticos = [], []
    for resultado in OUTCOMES:
        corrida(df, resultado, 'principal', 20261030, filas, diagnosticos)
    pd.DataFrame(filas).to_csv((Path(__file__).resolve().parents[4] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/salidas/resultados_dml_iv_aioe.csv'), index=False)
    if not args.solo_principal:
        for seed in [20261031, 20261101]:
            for resultado in OUTCOMES:
                corrida(df, resultado, 'particion_alternativa', seed, filas, diagnosticos)
        buscada, _ = cargar_2025(variante_ocupacion='buscada')
        buscada['uso_ia'], _ = construir_tratamiento(buscada)
        corrida(buscada, 'desempleo', 'ocupacion_buscada', 20261030, filas, diagnosticos)
    old = pd.read_csv((Path(__file__).resolve().parents[4] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_dml_iv.csv'))
    old = old.loc[old.instrumento.eq('aioe_pct'), ['resultado','theta_iv','se','p','nobs','clusters','f_stat_primer_paso']]
    new = pd.DataFrame(filas).loc[lambda d:d.variante.eq('principal')]
    old.merge(new[old.columns], on='resultado', suffixes=('_anterior','_revisado')).to_csv((Path(__file__).resolve().parents[4] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/salidas/comparacion_antes_despues.csv'), index=False)
    from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS
    entradas = [MICRODATOS[2025],
                QUARTO/'regresiones/preparacion/datos/exposicion_ia/indices_comunes.py', QUARTO/'datos/exposicion_ia/ciuo08_exposicion_ia_scores.csv']
    entradas += list(HERE.glob('*.py'))
    def sha(path):
        digest = hashlib.sha256()
        with path.open('rb') as file:
            for bloque in iter(lambda:file.read(1024*1024), b''):
                digest.update(bloque)
        return digest.hexdigest()
    guardar_json((Path(__file__).resolve().parents[4] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/salidas/manifest.json'), {'python':sys.version,'platform':platform.platform(),
        'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__,
        'entradas':{str(p.relative_to(QUARTO)):sha(p) for p in entradas}, 'controles':CONTROLES,
        'categoricas':CATEGORICAS,'semillas':[20261030] if args.solo_principal else [20261030,20261031,20261101],
        'referencia':'Chernozhukov et al. (2018), sección 4.2, ecuación 4.8',
        'limites':'Diagnóstico por inversión del momento ortogonal, con residuos estimados y conglomerados ocupacionales. No certifica exclusión, validez causal ni cobertura uniforme bajo cualquier aprendizaje.'})
    print('Revisión completada.', flush=True)


if __name__ == '__main__':
    main()
