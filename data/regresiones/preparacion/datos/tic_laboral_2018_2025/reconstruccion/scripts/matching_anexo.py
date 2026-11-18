"""Matching 6D del Anexo, parametrizado y sin modificar sus fuentes.

Educación GEIH debe venir armonizada como EDUCACION_ARM_GEIH por un proceso
documentado. Este módulo deliberadamente no decide equivalencias históricas.
No estima exposiciones ni recalcula percentiles ocupacionales.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[6]))
from pathlib import Path
import argparse
import json
import sys
import numpy as np
import pandas as pd

QUARTO = (Path(__file__).resolve().parents[6])
sys.path.insert(0, str(QUARTO))
from regresiones.validacion.correcciones.educacion import armonizar_educacion_ecv
from regresiones.validacion.correcciones.empates import buscar_vecinos
from regresiones.validacion.correcciones.trazabilidad import sha256, sincronizar_hogar


def numeric(df, columns, source, allow_missing=False):
    missing = sorted(set(columns) - set(df.columns))
    if missing:
        raise ValueError(f"{source}: faltan {missing}")
    values = df[columns].apply(pd.to_numeric, errors="coerce")
    if not allow_missing and not np.isfinite(values.to_numpy(float)).all():
        counts = values.isna().sum()
        raise ValueError(f"{source}: covariables no educativas ausentes {counts[counts.gt(0)].to_dict()}")
    return values


def select_donors(g, e, activity_structural_under=None):
    """Mismos pesos, bloqueo y desempate cKDTree; nunca rellena adultos ausentes."""
    g = g.reset_index(drop=True)
    e = e.reset_index(drop=True)
    sex = "P3271" if "P3271" in g else "P6020"
    ng = numeric(g, ["DPTO", "CLASE", sex, "P6040", "P6050"], "GEIH")
    ne = numeric(e, ["P1_DEPARTAMENTO", "CLASE", "P6020", "P6040", "P6051", "CANT_PERSONAS_HOGAR"], "ECV")
    if not ng[sex].isin([1, 2]).all() or not ne.P6020.isin([1, 2]).all():
        raise ValueError("Sexo fuera de categorías 1/2")
    if not ng.CLASE.isin([1, 2]).all() or not ne.CLASE.isin([1, 2]).all():
        raise ValueError("Zona no armonizada a categorías 1/2")
    gedu = numeric(g, ["EDUCACION_ARM_GEIH"], "GEIH", True).iloc[:, 0]
    if not gedu.dropna().isin(range(5)).all():
        raise ValueError("Educación GEIH fuera de escala 0–4")
    eedu = armonizar_educacion_ecv(e)
    activity = []
    for name, frame in [("GEIH", g), ("ECV", e)]:
        a = numeric(frame, ["P6240"], name, True).iloc[:, 0]
        absent = a.isna()
        if absent.any():
            cutoff = activity_structural_under.get(name) if isinstance(activity_structural_under, dict) else activity_structural_under
            if isinstance(cutoff, dict):
                age_limit = pd.to_numeric(frame.CLASE, errors="coerce").map(cutoff)
                structural = frame.P6040.lt(age_limit)
            else:
                structural = frame.P6040.lt(cutoff) if cutoff is not None else pd.Series(False, index=frame.index)
            if (absent & ~structural).any():
                raise ValueError(f"{name}: actividad ausente no estructural o no autorizada")
        # Tras verificar que todos los ausentes son estructurales, su
        # indicador trabajar=0; no modifica la respuesta cruda.
        activity.append(a.eq(1).fillna(False).astype(float))
    sizeg = g.groupby(["DIRECTORIO", "SECUENCIA_P"], sort=False).P6040.transform("count").clip(1, 15)
    gf = np.column_stack([ng.P6040/100, gedu/4, 2*ng.P6050.eq(1), sizeg/10, 5*ng.P6040.ge(15), 3*activity[0]])
    ef = np.column_stack([ne.P6040/100, eedu/4, 2*ne.P6051.eq(1), ne.CANT_PERSONAS_HOGAR.clip(1, 15)/10, 5*ne.P6040.ge(15), 3*activity[1]])
    gs = ng.DPTO.astype(int).astype(str)+"_"+ng.CLASE.astype(int).astype(str)+"_"+ng[sex].astype(int).astype(str)
    es = ne.P1_DEPARTAMENTO.astype(int).astype(str)+"_"+ne.CLASE.astype(int).astype(str)+"_"+ne.P6020.astype(int).astype(str)
    matched = np.full(len(e), -1, dtype=int)
    fallback = np.zeros(len(e), dtype=bool)
    for stratum, positions in es.groupby(es).groups.items():
        pos = np.asarray(list(positions), dtype=int)
        pool = np.flatnonzero(gs.eq(stratum))
        if not len(pool):
            _, zone, sx = stratum.split("_")
            pool = np.flatnonzero(ng.CLASE.eq(int(zone)) & ng[sex].eq(int(sx)))
            fallback[pos] = True
        if not len(pool):
            raise ValueError(f"No hay donantes misma zona/sexo para {stratum}")
        _, matched[pos] = buscar_vecinos(gf, ef, pool, pos)
    return matched, fallback


def run(args):
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(f"No sobrescribir salida existente: {output}")
    g = pd.read_parquet(args.geih).reset_index(drop=True)
    e = pd.read_parquet(args.ecv).reset_index(drop=True)
    source_g_columns = len(g.columns)
    # La celda de donación exige parentesco válido para identificar la
    # jefatura. Algunos archivos históricos incluyen registros auxiliares sin
    # esa respuesta; no son donantes admisibles y se excluyen, no se rellenan.
    source_g_rows = len(g)
    g = g.loc[pd.to_numeric(g["P6050"], errors="coerce").notna()].reset_index(drop=True)
    excluded_invalid_donors = source_g_rows - len(g)
    if "EDUCACION_ARM_GEIH" not in g:
        from matching_educacion_geih import armonizar
        g["EDUCACION_ARM_GEIH"] = armonizar(g)
    original_n = len(e)
    # Exclusión territorial explícita, idéntica a Anexo.
    e = e.dropna(subset=["CLASE", "P1_DEPARTAMENTO"]).reset_index(drop=True)
    weights = numeric(e, ["FEX_C"], "ECV").FEX_C
    if not weights.gt(0).all():
        raise ValueError("Factores ECV no positivos")
    gcut = args.activity_structural_under_geih
    if args.activity_geih_historic_12_10:
        if gcut is not None:
            raise ValueError("No combinar umbral GEIH uniforme e histórico por zona")
        gcut = {1: 12, 2: 10}
    activity = pd.to_numeric(g["P6240"], errors="coerce")
    if isinstance(gcut, dict):
        age_limit = pd.to_numeric(g["CLASE"], errors="coerce").map(gcut)
        structural = pd.to_numeric(g["P6040"], errors="coerce").lt(age_limit)
    elif gcut is not None:
        structural = pd.to_numeric(g["P6040"], errors="coerce").lt(gcut)
    else:
        structural = pd.Series(False, index=g.index)
    invalid_activity = activity.isna() & ~structural
    excluded_invalid_activity = int(invalid_activity.sum())
    g = g.loc[~invalid_activity].reset_index(drop=True)
    cutoffs = {"GEIH": gcut, "ECV": args.activity_structural_under_ecv}
    matched, fallback = select_donors(g, e, cutoffs)
    donor = g.iloc[matched].reset_index(drop=True)
    labor = numeric(donor, ["OCI", "DSI", "P6920", "INGLABO"], "GEIH laboral", True)
    pet = e.P6040.ge(15)
    occupied = labor.OCI.eq(1) & pet
    unemployed = labor.DSI.eq(1) & pet
    if (occupied & unemployed).any():
        raise ValueError("Clasificación laboral simultánea")
    # Ausente dentro de ocupados sigue ausente; cero fuera de ocupado es
    # restricción lógica del Anexo, no imputación de salario ausente.
    income = labor.INGLABO.where(occupied, 0.0)
    factor = 151.76 / args.ipc_origen
    frame = pd.concat([e, donor.add_suffix("_geih")], axis=1)
    if not frame.columns.is_unique:
        raise ValueError("Colisión de columnas receptor/donante")
    for key, value in {"OCI_geih": occupied.astype(int), "DSI_geih": unemployed.astype(int),
                       "inglabo_real_geih": income*factor}.items():
        if key in frame:
            frame.rename(columns={key: key+"_donante_original"}, inplace=True)
        frame[key] = value
    for source, target in [("pobre_pm", "pobre_pm_hogar"), ("ingpcug_pm", "ingpcug_pm_hogar_nom")]:
        if source in donor:
            hh = e.DIRECTORIO.astype(str)+"_"+e.SECUENCIA_P.astype(str)
            frame[target] = sincronizar_hogar(hh, e.P6051.eq(1), pd.to_numeric(donor[source], errors="coerce"))
    if "ingpcug_pm_hogar_nom" in frame:
        frame["ingpcug_pm_hogar_real"] = frame.ingpcug_pm_hogar_nom*factor
    frame["id_donante_geih"] = matched
    frame["en_fallback"] = fallback
    frame["anio_fusion"] = args.year
    frame["factor_ipc_geih"] = factor
    frame["fexp"] = weights
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output, index=False)
    manifest = dict(anio=args.year, filas=len(frame), columnas=len(frame.columns),
                    variables_ecv=len(e.columns), variables_geih=source_g_columns,
                    donantes_fuente=source_g_rows,
                    donantes_excluidos_sin_parentesco=excluded_invalid_donors,
                    donantes_excluidos_sin_actividad=excluded_invalid_activity,
                    columnas_geih_con_armonizacion=len(g.columns),
                    receptores_originales=original_n, excluidos_territoriales=original_n-len(e),
                    donantes_distintos=len(np.unique(matched)), fallback=int(fallback.sum()),
                    educacion_geih_ausente=int(g.EDUCACION_ARM_GEIH.isna().sum()),
                    actividad_estructural_menores_de=cutoffs,
                    ipc_origen=args.ipc_origen, ipc_referencia=151.76,
                    fuentes=[dict(ruta=p, sha256=sha256(p)) for p in [args.geih, args.ecv]],
                    sha256_salida=sha256(output), exposiciones_recalculadas=False)
    output.with_suffix(".json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--geih", required=True)
    parser.add_argument("--ecv", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--ipc-origen", type=float, required=True)
    parser.add_argument("--activity-structural-under-geih", type=int, default=None)
    parser.add_argument("--activity-structural-under-ecv", type=int, default=None)
    parser.add_argument("--activity-geih-historic-12-10", action="store_true")
    args = parser.parse_args()
    if not np.isfinite(args.ipc_origen) or args.ipc_origen <= 0:
        parser.error("IPC debe ser positivo")
    run(args)
