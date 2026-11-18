"""Audita el panel amplio usado por la sección 4.6 sin modificar sus valores."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

BASE = (Path(__file__).resolve().parents[5] / 'datos')
PANEL = (Path(__file__).resolve().parents[5] / 'datos/imputados/panel/panel_cohortes_2018_2025.parquet')
OUT = (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/diagnosticos/panel_amplio_2018_2025.json')
CORE = [
    "prop_H_tic", "tasa_desempleo", "prop_no_cotiza_respuesta12",
    "log_sal_real_medio", "edad_media", "prop_rural",
    "prop_edu_universitaria", "tam_hogar_medio", "prop_jefes",
]
PROPORTIONS = [
    "prop_H_tic", "prop_uso_internet", "prop_uso_computador",
    "tasa_desempleo", "prop_no_cotiza_respuesta12", "prop_rural",
    "prop_edu_universitaria", "prop_jefes",
]


def main():
    d = pd.read_parquet(PANEL)
    key = ["id_cohorte", "anio"]
    assert set(CORE).issubset(d)
    invalid_ranges = {
        c: int((d[c].notna() & ~d[c].between(0, 1)).sum()) for c in PROPORTIONS
    }
    missing_core = d.loc[d[CORE].isna().any(axis=1),
                         ["anio", "id_cohorte", "departamento", "sexo",
                          "generacion"] + CORE]
    report = {
        "archivo": str(PANEL),
        "sha256": hashlib.sha256(PANEL.read_bytes()).hexdigest(),
        "filas": len(d), "columnas": len(d.columns),
        "cohortes": int(d.id_cohorte.nunique()),
        "anios": sorted(int(x) for x in d.anio.unique()),
        "filas_por_anio": {str(k): int(v) for k, v in d.groupby("anio").size().items()},
        "duplicados_cohorte_anio": int(d.duplicated(key).sum()),
        "rangos_invalidos": invalid_ranges,
        "ausentes_core": {c: int(d[c].isna().sum()) for c in CORE},
        "filas_core_incompletas": missing_core.replace({np.nan: None}).to_dict("records"),
        "cohortes_con_variacion_temporal": {
            c: int(d.groupby("id_cohorte")[c].nunique(dropna=True).gt(1).sum())
            for c in CORE
        },
        "muestras_modelo": {
            outcome: {
                "niveles_FE": int(d[[outcome, "prop_H_tic"] + CORE[4:]].notna().all(axis=1).sum()),
                "cohortes_FE": int(d.loc[d[[outcome, "prop_H_tic"] + CORE[4:]].notna().all(axis=1), "id_cohorte"].nunique()),
            }
            for outcome in ["tasa_desempleo", "prop_no_cotiza_respuesta12", "log_sal_real_medio"]
        },
        "estado": "estructura_valida; panel_2018_2025_reconstruido",
        "advertencias": [
            "Los valores 2018–2021 proceden de las integraciones reconstruidas desde las fuentes originales.",
            "No cotización pensional no equivale a informalidad oficial.",
            "No se reemplazaron ausentes por cero.",
            "La muestra DML-FD debe recalcularse por pares consecutivos y conservar cohortes completas en los folds.",
        ],
    }
    (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/diagnosticos').mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ["filas", "columnas", "cohortes",
          "duplicados_cohorte_anio", "ausentes_core", "muestras_modelo", "estado"]},
          ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
