#!/usr/bin/env python3
"""Genera agregados reproducibles para el explorador de uso reportado de IA."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'data'))

from pathlib import Path
import json
import sys
import hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = Path(__file__).resolve().parents[1] / 'data'
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030'))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS, INDICES
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import ocupacion_analitica
from regresiones.preparacion.datos.armonizados_2018_2025.indicadores import uso_ia_validado, tic_combinado
DATA = (BASE / 'datos/armonizados_2018_2025/microdatos/ecv_geih_imputada_2025.parquet')
OUT = (BASE / 'datos/publicacion/dashboard/perfiles_uso_ia_2025.json')
DIGITAL_LABEL = "Uso de computador y acceso a internet"
EDUCATION_LABELS = {0: "Sin escolaridad o preescolar", 1: "Primaria", 2: "Secundaria", 3: "Media", 4: "Técnica o tecnológica", 5: "Universitaria", 6: "Posgrado"}

INDEX_COLS = ["aioe_pct", "webb_ia_pct", "llm_pct", "software_pct", "robots_pct"]


def weighted_mean(x, w):
    ok = x.notna() & w.notna() & (w > 0)
    return float(np.average(x[ok], weights=w[ok])) if ok.any() else None


def main():
    cols = [
        "P1084", "P6040", "P6020", "CLASE", "P8586", "P8587", "P1088", "P1910", "P1911",
        "P1075", "OFICIO_C8_geih", "OFICIO2_C8_geih", "OCI_geih", "DSI_geih", "FEX_C",
    ]
    cols += [f"P1083S{i}" for i in range(1, 22)]
    d = pd.read_parquet(DATA, columns=cols)
    d = d.loc[np.isfinite(d["FEX_C"]) & d["FEX_C"].gt(0) & (d["P6040"] >= 5)].copy()
    d["universo"] = np.select(
        [d["OCI_geih"].eq(1), d["DSI_geih"].eq(1)], ["Ocupados", "Desempleados"], default=None
    )
    d["uso_ia"], routing = uso_ia_validado(d)
    d["ciuo08"] = ocupacion_analitica(d)

    idx = pd.read_csv(INDICES, dtype={"ciuo08": str})
    idx["ciuo08"] = idx["ciuo08"].str.zfill(4)
    d = d.merge(idx[["ciuo08", "ciuo08_desc", *INDEX_COLS]], on="ciuo08", how="left")

    d["Sexo"] = d["P6020"].map({1: "Hombres", 2: "Mujeres"})
    d["Rango de edad"] = pd.cut(
        d["P6040"], [4, 14, 24, 34, 44, 54, 64, 74, 84, np.inf],
        labels=["5 a 14 años", "15 a 24 años", "25 a 34 años", "35 a 44 años", "45 a 54 años", "55 a 64 años", "65 a 74 años", "75 a 84 años", "85 años o más"],
    ).astype("string")
    # Mismas categorías receptoras que la preparación de DML-IV 2025.
    reached = d.P8587.map({1:0,2:0,3:1,4:2,5:3,6:4,7:4,8:4,9:4,10:5,11:5,12:6,13:6})
    current = d.P1088.map({1:0,2:1,3:2,4:3,5:4,6:4,7:5,8:6})
    education = reached.where(d.P8586.eq(2), current.where(d.P8586.eq(1)))
    d["Educación"] = education.map(EDUCATION_LABELS).fillna("Sin información")
    d["Zona"] = d["CLASE"].map({1: "Cabecera", 2: "Centros poblados y rural disperso"})
    digital = tic_combinado(d)
    d[DIGITAL_LABEL] = digital.map({1.0: "Con uso de computador e internet", 0.0: "Sin condición conjunta"}).fillna("Sin información")
    d["Ocupación"] = d["ciuo08_desc"]

    dimensions = ["Sexo", "Rango de edad", "Educación", "Zona", DIGITAL_LABEL, "Ocupación"]
    rows = []
    pair_rows = []
    for universe in ["Población de 5 años o más", "Ocupados", "Desempleados", "Fuerza laboral"]:
        if universe == "Población de 5 años o más":
            z = d
        elif universe == "Fuerza laboral":
            z = d.loc[d["universo"].notna()]
        else:
            z = d.loc[d["universo"].eq(universe)]
        for dim in dimensions:
            for category, g in z.loc[z[dim].notna()].groupby(dim, observed=True):
                w = g["FEX_C"]
                row = {
                    "universo": universe, "dimension": dim, "categoria": str(category),
                    "n": int(len(g)), "poblacion": float(w.sum()),
                    "n_ia_valido": int(g.uso_ia.notna().sum()),
                    "poblacion_ia_valida": float(w[g.uso_ia.notna()].sum()),
                    "uso_ia": weighted_mean(g["uso_ia"], w),
                }
                row.update({col: weighted_mean(g[col], w) for col in INDEX_COLS})
                rows.append(row)

        for dim1 in dimensions:
            for dim2 in dimensions:
                if dim1 == dim2:
                    continue
                valid = z.loc[z[dim1].notna() & z[dim2].notna()]
                for (cat1, cat2), g in valid.groupby([dim1, dim2], observed=True):
                    if (dim1 == "Ocupación" or dim2 == "Ocupación") and len(g) < 30:
                        continue
                    w = g["FEX_C"]
                    pair_rows.append({
                        "universo": universe, "dimension1": dim1, "categoria1": str(cat1),
                        "dimension2": dim2, "categoria2": str(cat2), "n": int(len(g)),
                        "poblacion": float(w.sum()), "uso_ia": weighted_mean(g["uso_ia"], w),
                    })

    # Las ocupaciones con muy poca muestra se excluyen para evitar porcentajes inestables.
    rows = [r for r in rows if r["dimension"] != "Ocupación" or r["n"] >= 30]
    payload = {
        "titulo": "Uso reportado de herramientas de IA por características de la población, 2025",
        "definicion": "Uso de IA por internet con ruta válida P1084/P1083S1–S21. Ausencias e inconsistencias permanecen sin clasificar; no identifica si ocurrió en el trabajo, el hogar u otro lugar.",
        "diagnostico_ruta": routing,
        "fuentes_sha256": {str(DATA.relative_to(BASE)): hashlib.sha256(DATA.read_bytes()).hexdigest(), str(INDICES.relative_to(BASE)): hashlib.sha256(INDICES.read_bytes()).hexdigest()},
        "educacion": "Nivel alcanzado o actual de ECV según asistencia; no educación del donante.",
        "denominador": "El porcentaje de uso de IA incluye únicamente rutas válidas dentro de cada categoría.",
        "universo": "Población de 5 años o más; los universos laborales se presentan por separado.",
        "minimo_ocupacion": 30,
        "filas": rows,
        "cruces": pair_rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{OUT}: {len(rows)} agregados")


if __name__ == "__main__":
    main()
