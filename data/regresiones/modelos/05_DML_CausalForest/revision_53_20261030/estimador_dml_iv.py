"""Weighted, occupation-cross-fitted partially linear IV (PLIV).

Model: Y = theta D + g(X) + error; E[error | X,Z] = 0.
The partialling-out score is (Z-E[Z|X]) *
    (Y-E[Y|X] - theta*(D-E[D|X])).
This is the PLIV score in Chernozhukov et al. (2018), section 4.2,
equation (4.8), DOI:10.1111/ectj.12097. A continuous instrument does
not by itself identify the binary-instrument LATE estimand.

estimar assumes the caller already selected the intended outcome population.
Missing/nonfinite required numeric values and nonpositive weights are excluded.
Categorical X columns must be passed through categorical_cols or have category,
object or string dtype. Numeric category codes should be declared explicitly.
Survey expansion weights define weighted moments; these are occupation-cluster
standard errors, not full complex-survey design standard errors.

The inverted orthogonal-score set uses the same frozen OOF residuals at every
theta and a t(G-1) cutoff. It is an AR-style weak-identification diagnostic;
coverage still requires valid IV assumptions, independent clusters, sufficiently
many clusters and valid nuisance estimation. It does not establish exclusion,
exogeneity, or causal validity. No first-stage F cutoff certifies strength.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))

import os

os.environ.setdefault("OMP_NUM_THREADS", "4")

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import HistGradientBoostingRegressor


def _quadratic_set(a, b, c):
    """Solve a*t²+b*t+c <= 0, including linear, disjoint and unbounded sets."""
    # Scale the polynomial against overflow. Only exact zero removes a degree:
    # a tiny quadratic coefficient may encode a substantively distant endpoint.
    scale = max(abs(a), abs(b), abs(c))
    if scale == 0:
        return {"kind": "all_real", "intervals": [[-np.inf, np.inf]]}
    a, b, c = a / scale, b / scale, c / scale
    tol = 64 * np.finfo(float).eps
    if a == 0:
        if b == 0:
            intervals = [[-np.inf, np.inf]] if c <= 0 else []
        else:
            root = -c / b
            intervals = [[-np.inf, root]] if b > 0 else [[root, np.inf]]
    else:
        disc = b*b - 4*a*c
        dtol = tol * max(b*b, abs(4*a*c), np.finfo(float).tiny)
        if disc < -dtol:
            intervals = [[-np.inf, np.inf]] if a < 0 else []
        elif abs(disc) <= dtol:
            intervals = [[-np.inf, np.inf]] if a < 0 else [[-b/(2*a), -b/(2*a)]]
        else:
            q = -.5 * (b + np.copysign(np.sqrt(disc), b))
            roots = sorted([q/a, c/q])
            intervals = [roots] if a > 0 else [[-np.inf, roots[0]], [roots[1], np.inf]]
    kind = ("empty" if not intervals else "all_real" if intervals == [[-np.inf, np.inf]]
            else "disjoint" if len(intervals) == 2 else
            "unbounded" if not np.isfinite(intervals[0]).all() else "bounded")
    return {"kind": kind, "intervals": intervals}


def estimar(df, y_col, x_cols, group_col="ciuo08", weight="FEX_C",
            treatment="uso_ia", instrument="aioe_pct", folds=5,
            seed=20261030, alpha=.05, categorical_cols=None):
    """Return estimate, cluster inference, first stage and AR-style score set.

    Fold assignment randomly permutes clusters then balances observation counts;
    all members of an occupation remain together. Repeating with different seeds
    changes the partition. Returned row_index and fold_id permit leakage audits.
    """
    if not 0 < alpha < 1 or folds < 2:
        raise ValueError("Require 0 < alpha < 1 and folds >= 2")
    x_cols = list(x_cols)
    if not x_cols or set(x_cols) & {y_col, treatment, instrument, weight, group_col}:
        raise ValueError("X must be nonempty and exclude Y, D, Z, weights and cluster")
    required = list(dict.fromkeys([y_col, treatment, instrument, weight, group_col, *x_cols]))
    s = df.loc[:, required].copy()
    numeric = list(dict.fromkeys([y_col, treatment, instrument, weight]))
    for col in numeric:
        s[col] = pd.to_numeric(s[col], errors="coerce")
    s = s.replace([np.inf, -np.inf], np.nan).dropna()
    s = s.loc[s[weight] > 0]
    if not len(s):
        raise ValueError("No complete observations with positive weights")
    categories = categorical_cols if categorical_cols is not None else [
        col for col in x_cols if not pd.api.types.is_numeric_dtype(s[col])]
    X = pd.get_dummies(s[x_cols], columns=list(categories), dtype=float).to_numpy(float)
    if not np.isfinite(X).all():
        raise ValueError("X must be finite after encoding")
    y, d, z = (s[col].to_numpy(float) for col in [y_col, treatment, instrument])
    w = s[weight].to_numpy(float)
    w = w / w.mean()
    group, labels = pd.factorize(s[group_col], sort=False)
    G = len(labels)
    if G < folds:
        raise ValueError("Fewer occupations than cross-fitting folds")
    rng = np.random.default_rng(seed)
    counts = np.bincount(group)
    assignment = np.empty(G, dtype=int)
    loads = np.zeros(folds, dtype=int)
    for g in rng.permutation(G):
        f = int(np.argmin(loads))
        assignment[g] = f
        loads[f] += counts[g]
    fold_id = assignment[group]
    residual = np.empty((len(s), 3))
    metrics = {}
    for j, target in enumerate([y, d, z]):
        pred = np.empty(len(s))
        for f in range(folds):
            test = fold_id == f
            model = HistGradientBoostingRegressor(
                max_iter=60, min_samples_leaf=30, max_leaf_nodes=15,
                learning_rate=.06, l2_regularization=1., early_stopping=False,
                random_state=seed + 100*j + f)
            model.fit(X[~test], target[~test], sample_weight=w[~test])
            pred[test] = model.predict(X[test])
        residual[:, j] = target - pred
        mse = float(np.average((target-pred)**2, weights=w))
        variance = float(np.average((target-np.average(target, weights=w))**2, weights=w))
        metrics[["Y", "D", "Z"][j]] = {"oof_mse": mse,
            "oof_r2": 1-mse/variance if variance > 0 else np.nan,
            "raw_variance": variance, "residual_second_moment": mse}
    yr, dr, zr = residual.T
    A = np.bincount(group, weights=w*zr*yr, minlength=G)
    B = np.bincount(group, weights=w*zr*dr, minlength=G)
    sy, sd = A.sum(), B.sum()
    correction = G/(G-1)
    critical = float(stats.t.ppf(1-alpha/2, G-1))
    # Acceptance: (sum A-theta sum B)^2 <= tcrit² V_cluster(theta).
    poly = [sd*sd-critical**2*correction*np.dot(B, B),
            -2*sy*sd+2*critical**2*correction*np.dot(A, B),
            sy*sy-critical**2*correction*np.dot(A, A)]
    weak_set = _quadratic_set(*poly)
    weak_set.update({"alpha": alpha, "critical_t": critical,
                     "polynomial": [float(v) for v in poly],
                     "method": "inversion of cross-fitted orthogonal score; raw occupation cluster sums"})
    theta = float(sy/sd) if sd != 0 else np.nan
    se = float(np.sqrt(correction*np.sum((A-theta*B)**2))/abs(sd)) if sd != 0 else np.nan
    tstat = theta/se if se > 0 else np.nan
    zz = np.sum(w*zr*zr)
    pi = float(sd/zz) if zz > 0 else np.nan
    fs_sums = np.bincount(group, weights=w*zr*(dr-pi*zr), minlength=G)
    fs_se = float(np.sqrt(correction*np.dot(fs_sums, fs_sums))/zz) if zz > 0 else np.nan
    fs_t = pi/fs_se if fs_se > 0 else np.nan
    return {"theta": theta, "se": se, "t": float(tstat),
            "p": float(2*stats.t.sf(abs(tstat), G-1)),
            "ci_lower": theta-critical*se, "ci_upper": theta+critical*se,
            "nobs": len(s), "n_excluded": len(df)-len(s), "clusters": G,
            "folds": folds, "seed": seed, "df_cluster": G-1,
            "first_stage_pi": pi, "first_stage_se": fs_se,
            "first_stage_t": float(fs_t), "first_stage_F": float(fs_t**2),
            "first_stage_p": float(2*stats.t.sf(abs(fs_t), G-1)),
            "jacobian": float(sd/w.sum()), "weak_iv_set": weak_set,
            "oof_metrics": metrics, "row_index": s.index.tolist(),
            "fold_id": fold_id.tolist(),
            "fold_observations": np.bincount(fold_id, minlength=folds).tolist(),
            "fold_clusters": np.bincount(assignment, minlength=folds).tolist()}
