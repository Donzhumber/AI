"""R-learner de pendientes exploratorias y calibración BLP; tratamiento continuo.
Este módulo no estima IV ni atribuye causalidad a las pendientes predichas.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold


def fit_nuisance_continuous(X_tr, y_tr, w_tr, X_te, seed=42):
    mod = HistGradientBoostingRegressor(max_iter=60, min_samples_leaf=30, random_state=seed)
    mod.fit(X_tr, y_tr, sample_weight=w_tr)
    return mod.predict(X_te)

def estimar_cate_rlearner(df, y_var, exp_var="aioe_pct", n_splits=5, seed=42):
    """
    R-Learner y análisis de heterogeneidad CATE (Nie & Wager 2021) + BLP y CLAN.
    """
    sample = df.dropna(subset=[y_var, exp_var, "post", "FEX_C", "ciuo08", "edad", "edad2", "mujer", "rural", "jefe", "edu_cat", "H_tic", "dpto", "oficio_2d"]).copy().reset_index(drop=True)
    features = ["edad", "edad2", "mujer", "rural", "jefe", "edu_cat", "H_tic", "dpto", "oficio_2d"]
    X = pd.get_dummies(sample[features], columns=["edu_cat", "dpto", "oficio_2d"], drop_first=True, dtype=float).to_numpy()

    y = sample[y_var].to_numpy(dtype=float)
    d = (sample[exp_var] * sample["post"]).to_numpy(dtype=float)
    w = sample["FEX_C"].to_numpy(dtype=float)
    w = w / w.mean()
    groups = sample["ciuo08"].to_numpy()

    n = len(sample)
    G = sample["ciuo08"].nunique()
    gkf = GroupKFold(n_splits=n_splits)

    y_res = np.empty(n)
    d_res = np.empty(n)
    tau_hat = np.empty(n)

    for fold, (tr, te) in enumerate(gkf.split(X, groups=groups)):
        # Nuisance functions
        y_hat = fit_nuisance_continuous(X[tr], y[tr], w[tr], X[te], seed=seed + fold)
        d_hat = fit_nuisance_continuous(X[tr], d[tr], w[tr], X[te], seed=seed + 10 + fold)
        y_res[te] = y[te] - y_hat
        d_res[te] = d[te] - d_hat

        # Ajuste de R-learner dentro del split
        # Cross-fitting interno para tau
        inner_gkf = GroupKFold(n_splits=3)
        y_in, d_in = np.empty(len(tr)), np.empty(len(tr))
        for itr, ite in inner_gkf.split(X[tr], groups=groups[tr]):
            y_in[ite] = y[tr[ite]] - fit_nuisance_continuous(X[tr[itr]], y[tr[itr]], w[tr[itr]], X[tr[ite]], seed=seed + fold + 100)
            d_in[ite] = d[tr[ite]] - fit_nuisance_continuous(X[tr[itr]], d[tr[itr]], w[tr[itr]], X[tr[ite]], seed=seed + fold + 200)

        keep = np.abs(d_in) > 1e-4
        r_mod = HistGradientBoostingRegressor(max_iter=40, min_samples_leaf=40, random_state=seed + fold)
        weights_r = w[tr[keep]] * (d_in[keep] ** 2)
        target_r = y_in[keep] / d_in[keep]
        r_mod.fit(X[tr[keep]], target_r, sample_weight=weights_r)
        tau_hat[te] = r_mod.predict(X[te])

    # Best Linear Predictor (BLP) of CATE
    tau_mean = np.average(tau_hat, weights=w)
    tau_centered = tau_hat - tau_mean
    blp_X = np.column_stack([tau_mean * d_res, tau_centered * d_res])
    blp_mod = sm.WLS(y_res, blp_X, weights=w).fit(cov_type="cluster", cov_kwds={"groups": groups})

    beta_hetero = float(blp_mod.params[1])
    se_hetero = float(blp_mod.bse[1])
    p_hetero = float(blp_mod.pvalues[1])

    # CLAN (Classification Analysis por subgrupos)
    subgrupos = {
        "con_tic": sample["H_tic"] == 1,
        "sin_tic": sample["H_tic"] == 0,
        "universitarios": sample["H_edu"] == 1,
        "no_universitarios": sample["H_edu"] == 0,
        "mujeres": sample["mujer"] == 1,
        "hombres": sample["mujer"] == 0,
        "jovenes_le29": sample["edad_cat"] == 1,
        "adultos_30_49": sample["edad_cat"] == 2,
        "mayores_ge50": sample["edad_cat"] == 3,
        "urbano": sample["rural"] == 0,
        "rural": sample["rural"] == 1
    }

    clan = {}
    for sg_name, mask in subgrupos.items():
        if mask.sum() > 0:
            clan[sg_name] = float(np.average(tau_hat[mask], weights=w[mask]))

    return {
        "tau_mean": float(tau_mean),
        "blp_beta_hetero": beta_hetero,
        "blp_se": se_hetero,
        "blp_p": p_hetero,
        "rechaza_homogeneidad": bool(p_hetero < 0.05),
        "clan_subgrupos": clan
    }
