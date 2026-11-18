"""Diagnósticos de residuos para el panel TIC con FE de cohorte y año."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from pathlib import Path
import sys
import json

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import het_breuschpagan, het_white
from statsmodels.stats.sandwich_covariance import cov_cluster

ROOT = (Path(__file__).resolve().parents[2] / 'regresiones/modelos')
sys.path.insert(0,str((Path(__file__).resolve().parents[2])))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import PANEL_TIC_DTA
DATA = PANEL_TIC_DTA
OUT = (Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/diagnosticos_residuos_panel_tic.csv')
DETAIL = (Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/diagnosticos_residuos_panel_tic.json')
OUTCOMES = {"salario": "y_sal", "desempleo": "y_des", "no_cotizacion": "y_inf"}
X = ["x_tic", "c_edad", "c_rural", "c_edu", "c_hogar", "c_jefe"]


def two_way_demean(frame, columns):
    z = frame[columns].astype(float)
    return (z - z.groupby(frame.coh).transform("mean")
            - z.groupby(frame.anio).transform("mean") + z.mean())


def pesaran_cd(frame, residual):
    wide = pd.DataFrame({"coh": frame.coh, "anio": frame.anio,
                         "resid": residual}).pivot(index="coh", columns="anio", values="resid")
    correlation = np.corrcoef(wide.to_numpy())
    upper = correlation[np.triu_indices_from(correlation, 1)]
    n, t = wide.shape
    statistic = np.sqrt(2 * t / (n * (n - 1))) * np.nansum(upper)
    return statistic, 2 * stats.norm.sf(abs(statistic)), float(np.nanmean(upper))


def wooldridge(frame, outcome):
    years = pd.get_dummies(frame.anio, prefix="year", drop_first=True, dtype=float)
    levels = pd.concat([frame[["coh", "anio", outcome] + X].reset_index(drop=True), years], axis=1)
    levels = levels.sort_values(["coh", "anio"])
    difference_columns = [outcome] + X + list(years.columns)
    diff = levels.groupby("coh")[difference_columns].diff()
    valid = diff.notna().all(axis=1)
    first = sm.OLS(diff.loc[valid, outcome], diff.loc[valid, difference_columns[1:]]).fit()
    errors = pd.Series(np.nan, index=levels.index)
    errors.loc[valid] = first.resid
    lag = errors.groupby(levels.coh).shift(1)
    valid_second = errors.notna() & lag.notna()
    second = sm.OLS(errors[valid_second], lag[valid_second].to_frame("lag"), hasconst=False).fit()
    covariance = cov_cluster(second, levels.loc[valid_second, "coh"], use_correction=True)
    se = float(np.sqrt(covariance[0, 0]))
    coefficient = float(second.params.iloc[0])
    statistic = (coefficient + 0.5) / se
    pvalue = 2 * stats.t.sf(abs(statistic), frame.coh.nunique() - 1)
    return coefficient, se, statistic, pvalue


def leave_one_cluster(frame, outcome, full_beta):
    estimates = []
    for cohort in frame.coh.unique():
        sample = frame.loc[frame.coh.ne(cohort)]
        transformed = two_way_demean(sample, [outcome] + X)
        beta = np.linalg.lstsq(transformed[X].to_numpy(),
                               transformed[outcome].to_numpy(), rcond=None)[0][0]
        estimates.append((int(cohort), float(beta), float(beta - full_beta)))
    return estimates


def main():
    frame = pd.read_stata(DATA).sort_values(["coh", "anio"]).reset_index(drop=True)
    rows, detail = [], {}
    for label, outcome in OUTCOMES.items():
        transformed = two_way_demean(frame, [outcome] + X)
        model = sm.OLS(transformed[outcome], transformed[X]).fit()
        residual = model.resid.to_numpy()
        exog = sm.add_constant(transformed[X], has_constant="add")
        bp_lm, bp_p, _, _ = het_breuschpagan(residual, exog)
        white_lm, white_p, _, _ = het_white(residual, exog)
        jb, jb_p, skew, kurtosis = sm.stats.jarque_bera(residual)
        cd, cd_p, mean_corr = pesaran_cd(frame, residual)
        w_coef, w_se, w_stat, w_p = wooldridge(frame, outcome)
        influence = leave_one_cluster(frame, outcome, float(model.params.x_tic))
        most = max(influence, key=lambda x: abs(x[2]))
        values = {
            "resultado": label, "N": len(frame), "cohortes": frame.coh.nunique(),
            "beta_tic": float(model.params.x_tic),
            "wooldridge_coef": w_coef, "wooldridge_t": w_stat,
            "wooldridge_p": w_p,
            "breusch_pagan_lm": float(bp_lm), "breusch_pagan_p": float(bp_p),
            "white_lm": float(white_lm), "white_p": float(white_p),
            "pesaran_cd": float(cd), "pesaran_p": float(cd_p),
            "correlacion_residual_media": mean_corr,
            "jarque_bera": float(jb), "jarque_bera_p": float(jb_p),
            "asimetria": float(skew), "curtosis": float(kurtosis),
            "cohorte_mas_influyente": most[0],
            "cambio_beta_max_leave_one_out": abs(most[2]),
        }
        rows.append(values)
        detail[label] = {"pruebas": values,
                         "leave_one_cohort_out": [
                             {"coh": c, "beta": b, "cambio": delta}
                             for c, b, delta in influence]}
    pd.DataFrame(rows).to_csv(OUT, index=False)
    DETAIL.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf8")
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
