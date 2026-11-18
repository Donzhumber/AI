#!/usr/bin/env python3
"""DML-DiD con exposición AIOE continua sobre el pseudo-panel de cohortes."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import json, os, sys, hashlib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold

os.environ.setdefault("OMP_NUM_THREADS", "4")
HERE=(Path(__file__).resolve().parents[3] / 'regresiones/modelos/05_DML_CausalForest')
BASE=(Path(__file__).resolve().parents[3])
sys.path.insert(0,str(BASE))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import PANEL_2021_2025
DATA=PANEL_2021_2025
OUT=(Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_dml_did_continuo.csv')
DIAG=(Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/diagnostico_dml_did_continuo.json')
OUTCOMES={'salario':'log_sal_real_medio','no_cotiza':'prop_no_cotiza_respuesta12','desempleo':'tasa_desempleo'}
CONTROLS=['edad_media','prop_rural','prop_edu_universitaria','tam_hogar_medio','prop_jefes']

def weighted_period(g, col, years):
    z=g[g.anio.isin(years)]
    return np.average(z[col],weights=z.n_obs_pet)

def build_contrast(panel,outcome,pre,post,label):
    ycol=OUTCOMES[outcome]; rows=[]
    for cid,g in panel.groupby('id_cohorte',sort=True):
        if not set(pre+post).issubset(set(g.anio)) or g[[ycol,'n_obs_pet','aioe_pct_c',*CONTROLS]].isna().any().any():
            continue
        gb=g[g.anio.isin(pre)]
        rows.append({'id_cohorte':cid,'departamento':str(g.departamento.iloc[0]),
            'dy':weighted_period(g,ycol,post)-weighted_period(g,ycol,pre),
            'd':float(g.loc[g.anio.eq(2022),'aioe_pct_c'].iloc[0]),
            'w':float(g[g.anio.isin(pre+post)].n_obs_pet.mean()),
            **{c:float(np.average(gb[c],weights=gb.n_obs_pet)) for c in CONTROLS}})
    return pd.DataFrame(rows),label

def estimate(frame,label,outcome,folds=5,seed=20261024):
    X=frame[CONTROLS].to_numpy(float); y=frame.dy.to_numpy(float); d=frame.d.to_numpy(float)
    w=frame.w.to_numpy(float);w/=w.mean();groups=frame.departamento.to_numpy()
    yr=np.empty(len(frame));dr=np.empty(len(frame))
    splitter=GroupKFold(n_splits=folds)
    for k,(tr,te) in enumerate(splitter.split(X,groups=groups)):
        my=HistGradientBoostingRegressor(max_iter=80,max_leaf_nodes=3,min_samples_leaf=30,
            learning_rate=.04,l2_regularization=5,random_state=seed+k)
        md=HistGradientBoostingRegressor(max_iter=80,max_leaf_nodes=3,min_samples_leaf=30,
            learning_rate=.04,l2_regularization=5,random_state=seed+10+k)
        my.fit(X[tr],y[tr],sample_weight=w[tr]);md.fit(X[tr],d[tr],sample_weight=w[tr])
        yr[te]=y[te]-my.predict(X[te]);dr[te]=d[te]-md.predict(X[te])
    denom=np.sum(w*dr**2);theta=float(np.sum(w*dr*yr)/denom)
    psi=w*dr*(yr-theta*dr);sums=pd.Series(psi).groupby(groups).sum().to_numpy();G=len(sums)
    se=float(np.sqrt((G/(G-1))*np.sum(sums**2)/denom**2));t=theta/se
    p=float(2*stats.t.sf(abs(t),G-1));crit=float(stats.t.ppf(.975,G-1))
    return {'resultado':outcome,'contraste':label,'theta':theta,'se':se,'t':t,'p':p,
        'ci_lower':theta-crit*se,'ci_upper':theta+crit*se,'nobs':len(frame),'clusters':G,
        'var_d':float(np.average((d-np.average(d,weights=w))**2,weights=w)),
        'var_d_residual':float(np.average(dr**2,weights=w)),'folds':folds}

def main():
    panel=pd.read_parquet(DATA);rows=[]
    contrasts=[([2021,2022],[2023,2024,2025],'Pre 2021–2022 / Post 2023–2025'),
               ([2022],[2023],'2022–2023'),([2022],[2024],'2022–2024'),
               ([2022],[2025],'2022–2025'),([2021],[2022],'Placebo 2021–2022')]
    for outcome in OUTCOMES:
        for pre,post,label in contrasts:
            frame,_=build_contrast(panel,outcome,pre,post,label)
            rows.append(estimate(frame,label,outcome))
    result=pd.DataFrame(rows);result.to_csv(OUT,index=False)
    DIAG.write_text(json.dumps({'modelo':'DML-DiD continuo en cambios de cohorte','base':str(DATA),'sha256_base':hashlib.sha256(DATA.read_bytes()).hexdigest(),
        'tratamiento':'AIOE percentil continuo fijado en 2022','controles_pre':CONTROLS,
        'cross_fitting':'5 pliegues agrupados por departamento','resultados':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print(result.to_string(index=False))
if __name__=='__main__':main()
