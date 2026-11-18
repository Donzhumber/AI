"""Construye el panel definitivo 2018–2025 con una sola regla de agregación."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[6]))
from pathlib import Path
import json
import shutil
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = (Path(__file__).resolve().parents[6])
RECON = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion')
STAGE = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/panel_final/stage')
FINAL = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/panel_final')
sys.path.insert(0, str(ROOT))

from regresiones.validacion.correcciones.depurar_panel import depurar, IPM
from regresiones.validacion.correcciones.educacion import COLUMNAS_EDUCACION_ECV

YEARS = range(2018, 2026)
IPC = {2018: 99.59, 2019: 103.43, 2020: 105.23, 2021: 110.06,
       2022: 123.51, 2023: 136.45, 2024: 143.83, 2025: 151.76}
BASE_COLUMNS = [
    "P6040", "P1_DEPARTAMENTO", "P6020", "FEX_C", "CLASE", "P6051",
    "CANT_PERSONAS_HOGAR", "P8587", "OCI_geih", "DSI_geih", "P6920_geih",
    "P6800_geih", "P6430_geih", "OFICIO_C8_geih", "inglabo_real_geih",
    "PERCAPITA", "I_UGASTO", "ingpcug_pm_real_geih", "pobre_pm_geih",
    "ipm", "pobre", "P1075", "P1910", "P1911", "P1912", "P1084",
    "P1082", "P6090", "P5095", "id_donante_geih"
] + IPM + list(COLUMNAS_EDUCACION_ECV)
BASE_COLUMNS = list(dict.fromkeys(BASE_COLUMNS))


def source(year):
    if year <= 2021:
        return (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/microdatos') / f"ecv_geih_imputada_{year}.parquet"
    return (Path(__file__).resolve().parents[6] / 'datos/imputados') / f"ecv_geih_imputada_{year}.parquet"


def prepare_inputs():
    target = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/panel_final/stage/datos/imputados')
    target.mkdir(parents=True, exist_ok=True)
    availability = {}
    for year in YEARS:
        src = source(year)
        if not src.exists():
            raise FileNotFoundError(src)
        schema = set(pq.read_schema(src).names)
        present = [c for c in BASE_COLUMNS if c in schema]
        frame = pd.read_parquet(src, columns=present)
        missing = [c for c in BASE_COLUMNS if c not in frame]
        for column in missing:
            frame[column] = np.nan
        frame[BASE_COLUMNS].to_parquet(
            target / f"ecv_geih_imputada_{year}.parquet", index=False,
            compression="zstd")
        availability[str(year)] = {
            "fuente": str(src), "filas": len(frame),
            "variables_requeridas_observadas": len(present),
            "variables_no_disponibles": missing,
        }
    return availability


def add_tic(panel, closed=False):
    rows = []
    for year in YEARS:
        path = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/panel_final/stage/datos/imputados') / f"ecv_geih_imputada_{year}.parquet"
        d = pd.read_parquet(path, columns=["P6040", "P1_DEPARTAMENTO", "P6020",
                                               "FEX_C", "P1910", "P1911", "P1075"])
        valid_person = d.P6040.ge(15) & np.isfinite(d.FEX_C) & d.FEX_C.gt(0)
        born = year - d.P6040
        if closed:
            valid_person &= born.le(2007)
        d = d.loc[valid_person].reset_index(drop=True)
        born = year - d.P6040
        generation = np.select(
            [born.le(1964), born.le(1974), born.le(1984), born.le(1994)],
            [1, 2, 3, 4], default=5)
        ids = (d.P1_DEPARTAMENTO.astype(int).astype(str) + "_" +
               d.P6020.astype(int).astype(str) + "_" +
               pd.Series(generation).astype(str))
        weights = d.FEX_C.to_numpy(float)
        computer = d.P1910.isin(range(1, 5)) | d.P1911.isin(range(1, 5))
        valid_computer = d.P1910.isin(range(1, 6)) & d.P1911.isin(range(1, 6))
        combined = computer & d.P1075.eq(1)
        valid_combined = valid_computer & d.P1075.isin([1, 2])
        labels, groups = np.unique(ids, return_inverse=True)

        def weighted_mean(values, valid):
            valid = valid.to_numpy(bool)
            den = np.bincount(groups[valid], weights=weights[valid], minlength=len(labels))
            num = np.bincount(groups[valid], weights=weights[valid] * values[valid], minlength=len(labels))
            return np.divide(num, den, out=np.full(len(labels), np.nan), where=den > 0)

        rows.append(pd.DataFrame({
            "id_cohorte": labels, "anio": year,
            "prop_uso_computador": weighted_mean(computer.to_numpy(float), valid_computer),
            "prop_H_tic": weighted_mean(combined.to_numpy(float), valid_combined),
        }))
    tic = pd.concat(rows, ignore_index=True)
    result = panel.merge(tic, on=["id_cohorte", "anio"], how="left", validate="one_to_one")
    return result


def main():
    FINAL.mkdir(parents=True, exist_ok=True)
    availability = prepare_inputs()
    out = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/panel_final/stage/datos/imputados/panel')
    panel = depurar(base=ROOT, datos=(Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/panel_final/stage/datos'), out=out,
                    years=YEARS, ipc=IPC)
    panel = add_tic(panel, closed=False)
    closed = pd.read_parquet(out / "panel_cohortes_nacimiento_hasta_2007.parquet")
    closed = add_tic(closed, closed=True)
    for frame, stem in [(panel, "panel_cohortes_2018_2025"),
                        (closed, "panel_cohortes_2018_2025_cerrado")]:
        frame = frame.sort_values(["id_cohorte", "anio"]).reset_index(drop=True)
        if frame.duplicated(["id_cohorte", "anio"]).any():
            raise ValueError("Llaves repetidas en el panel final")
        frame.to_parquet(FINAL / f"{stem}.parquet", index=False, compression="zstd")
        frame.to_stata(FINAL / f"{stem}.dta", write_index=False, version=118)
    report = {
        "periodo": [2018, 2025], "filas": len(panel), "columnas": len(panel.columns),
        "cohortes": int(panel.id_cohorte.nunique()),
        "balanceado": bool(panel.groupby("id_cohorte").anio.nunique().eq(8).all()),
        "duplicados_llave": int(panel.duplicated(["id_cohorte", "anio"]).sum()),
        "disponibilidad_fuentes": availability,
        "regla_faltantes": "La ausencia de una variable permanece NaN; nunca se reemplaza por cero.",
    }
    ((Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/panel_final/diagnostico_construccion.json')).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
