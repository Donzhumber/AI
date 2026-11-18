"""Wild cluster bootstrap-t por departamento para el coeficiente TIC."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from scipy import stats

ROOT = (Path(__file__).resolve().parents[2] / 'regresiones/modelos')
sys.path.insert(0,str((Path(__file__).resolve().parents[2])))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import PANEL_TIC_DTA
DATA = PANEL_TIC_DTA
OUT = (Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/panel_tic_inferencia_departamento.csv')
OUTCOMES = {"salario": "y_sal", "desempleo": "y_des", "informalidad": "y_inf"}
XCOLS = ["x_tic", "c_edad", "c_rural", "c_edu", "c_hogar", "c_jefe"]
REPS = 9999
SEED = 20261024


def demean(frame, columns):
    z = frame[columns].astype(float)
    return (z - z.groupby(frame.coh).transform("mean")
            - z.groupby(frame.anio).transform("mean") + z.mean()).to_numpy()


def fit_cluster(y, x, cluster):
    # lstsq y pinv evitan amplificar errores de redondeo en las réplicas
    # bootstrap cuando los regresores transformados están muy correlacionados.
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    inv = np.linalg.pinv(x.T @ x)
    residual = y - np.sum(x * beta, axis=1)
    groups = np.unique(cluster)
    meat = np.zeros((x.shape[1], x.shape[1]))
    for group in groups:
        score = x[cluster == group].T @ residual[cluster == group]
        meat += np.outer(score, score)
    correction = len(groups) / (len(groups) - 1) * (len(y) - 1) / (len(y) - x.shape[1])
    covariance = correction * inv @ meat @ inv
    return beta, np.sqrt(np.diag(covariance))


def main():
    frame = pd.read_stata(DATA).sort_values(["coh", "anio"]).reset_index(drop=True)
    frame["departamento"] = frame.id_cohorte.str.split("_").str[0].astype(int)
    cluster = frame.departamento.to_numpy()
    groups = np.unique(cluster)
    group_index = pd.Categorical(cluster, categories=groups).codes
    x = demean(frame, XCOLS)
    controls = x[:, 1:]
    rng = np.random.default_rng(SEED)
    weights = rng.choice([-1.0, 1.0], size=(REPS, len(groups)))
    rows = []
    for label, outcome in OUTCOMES.items():
        y = demean(frame, [outcome]).ravel()
        beta, se = fit_cluster(y, x, cluster)
        observed_t = beta[0] / se[0]
        restricted_beta = np.linalg.lstsq(controls, y, rcond=None)[0]
        fitted_null = np.sum(controls * restricted_beta, axis=1)
        residual_null = y - fitted_null
        exceed = 0
        for draw in weights:
            y_star = fitted_null + residual_null * draw[group_index]
            beta_star, se_star = fit_cluster(y_star, x, cluster)
            exceed += abs(beta_star[0] / se_star[0]) >= abs(observed_t)
        p_wild = (exceed + 1) / (REPS + 1)
        p_cluster = 2 * stats.t.sf(abs(observed_t), len(groups) - 1)
        rows.append({"resultado": label, "coef": beta[0], "se_departamento": se[0],
                     "t_departamento": observed_t, "p_departamento": p_cluster,
                     "p_wild_cluster": p_wild, "clusters": len(groups),
                     "repeticiones": REPS, "semilla": SEED})
    result = pd.DataFrame(rows)
    result.to_csv(OUT, index=False)
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
