"""Agrega integración reconstruida; no acepta silenciosamente el piloto histórico.

Indicadores TIC verificados en diccionarios 2018–2021. No estima regresiones.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[6]))
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd

ROOT = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion')


def weighted(values, weights):
    ok = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    x, w = values[ok], weights[ok]
    mass = float(w.sum())
    return (float(np.average(x, weights=w)) if mass else np.nan,
            int(ok.sum()), mass,
            float(mass * mass / np.square(w).sum()) if mass else np.nan)


def build(year):
    source = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/microdatos') / f"ecv_geih_imputada_{year}.parquet"
    required = ["P6040", "P6020", "P1_DEPARTAMENTO", "FEX_C",
                "id_donante_geih", "OCI_geih", "DSI_geih", "P6920_geih",
                "inglabo_real_geih", "P1075", "P1077S21", "P1077S22", "P1084"]
    d = pd.read_parquet(source, columns=required)
    for c in required:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    keep = (d.P6040.ge(15) & d.P6020.isin([1, 2]) &
            d.P1_DEPARTAMENTO.notna() & np.isfinite(d.FEX_C) & d.FEX_C.gt(0))
    excluded = int((~keep).sum())
    d = d.loc[keep].copy()
    born = year - d.P6040
    d["generacion"] = np.select(
        [born.le(1964), born.le(1974), born.le(1984), born.le(1994)],
        [1, 2, 3, 4], default=5)
    d["nacimiento_estimado"] = born
    occupied, unemployed = d.OCI_geih.eq(1), d.DSI_geih.eq(1)
    if (occupied & unemployed).any():
        raise ValueError("Clasificación laboral contradictoria")
    d["desempleo"] = unemployed.astype(float).where(occupied | unemployed)
    d["no_cotizacion"] = d.P6920_geih.eq(2).astype(float).where(
        occupied & d.P6920_geih.isin([1, 2]))
    d["ingreso_laboral_real"] = d.inglabo_real_geih.where(
        occupied & d.inglabo_real_geih.gt(0))
    d["internet_hogar"] = d.P1075.eq(1).astype(float).where(d.P1075.isin([1, 2]))
    d["computador_hogar"] = np.nan
    d.loc[d.P1077S21.eq(1) | d.P1077S22.eq(1), "computador_hogar"] = 1.
    d.loc[d.P1077S21.eq(2) & d.P1077S22.eq(2), "computador_hogar"] = 0.
    d["uso_internet"] = d.P1084.isin([1, 2, 3, 4]).astype(float).where(
        d.P1084.isin([1, 2, 3, 4, 5]))
    rows, support = [], []
    for variant in ["abierto", "cerrado_2003"]:
        sample = d if variant == "abierto" else d[d.nacimiento_estimado.le(2003)]
        for (department, sex, generation), g in sample.groupby(
                ["P1_DEPARTAMENTO", "P6020", "generacion"]):
            key = dict(variante=variant, anio=year, departamento=int(department),
                       sexo=int(sex), generacion=int(generation))
            key["id_cohorte"] = f"{int(department)}_{int(sex)}_{int(generation)}"
            row = dict(key, n_receptores=len(g), masa_pet=float(g.FEX_C.sum()),
                       n_donantes=int(g.id_donante_geih.nunique()))
            for variable in ["desempleo", "no_cotizacion", "ingreso_laboral_real",
                             "internet_hogar", "computador_hogar", "uso_internet"]:
                mean, n, mass, kish = weighted(g[variable], g.FEX_C)
                row[variable] = mean
                valid = np.isfinite(g[variable])
                donor_weights = g.loc[valid].groupby("id_donante_geih").FEX_C.sum()
                support.append(dict(key, variable=variable, n_observados=n,
                                    masa=mass, n_efectivo_receptores=kish,
                                    n_donantes=int(len(donor_weights)),
                                    n_efectivo_donantes=float(
                                        mass**2 / np.square(donor_weights).sum())
                                    if mass and len(donor_weights) else np.nan))
            row["log_ingreso_real_medio"] = (
                np.log(row["ingreso_laboral_real"])
                if row["ingreso_laboral_real"] > 0 else np.nan)
            rows.append(row)
    frame = pd.DataFrame(rows)
    assert not frame.duplicated(["variante", "anio", "id_cohorte"]).any()
    out = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/paneles_parciales')
    out.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(out / f"cohortes_{year}.parquet", index=False)
    pd.DataFrame(support).to_parquet(out / f"soporte_{year}.parquet", index=False)
    report = dict(anio=year, fuente=str(source), filas=len(frame),
                  columnas=len(frame.columns), excluidos_pet_o_llaves_o_peso=excluded,
                  estado="parcial_anual_no_regresiones",
                  advertencia="Ingreso laboral no equivale a salario; no cotización "
                              "no equivale a informalidad oficial.")
    (out / f"cohortes_{year}.json").write_text(json.dumps(
        report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", required=True, type=int, choices=range(2018, 2026))
    build(parser.parse_args().year)
