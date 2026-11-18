"""Exporta la muestra amplia con nombres utilizados por las regresiones TIC."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[6]))
from pathlib import Path
import pandas as pd

ROOT = (Path(__file__).resolve().parents[6])
SOURCE = (Path(__file__).resolve().parents[6] / 'datos/imputados/panel/panel_cohortes_2018_2025.parquet')
OUTPUT = (Path(__file__).resolve().parents[6] / 'datos/derivados_modelos/legacy/panel_tic_2018_2025.dta')

RENAME = {
    "tasa_desempleo": "y_des",
    "prop_no_cotiza_respuesta12": "y_inf",
    "log_sal_real_medio": "y_sal",
    "prop_uso_internet": "x_int",
    "prop_uso_computador": "x_comp",
    "prop_H_tic": "x_tic",
    "edad_media": "c_edad",
    "prop_rural": "c_rural",
    "prop_edu_universitaria": "c_edu",
    "tam_hogar_medio": "c_hogar",
    "prop_jefes": "c_jefe",
}


def main():
    panel = pd.read_parquet(SOURCE)
    panel = panel.sort_values(["id_cohorte", "anio"]).reset_index(drop=True)
    panel["coh"] = pd.factorize(panel.id_cohorte, sort=True)[0] + 1
    columns = ["coh", "id_cohorte", "anio"] + list(RENAME)
    result = panel[columns].rename(columns=RENAME)
    if result.duplicated(["id_cohorte", "anio"]).any():
        raise ValueError("Llaves repetidas")
    result.to_stata(OUTPUT, write_index=False, version=118)
    print(result.shape)


if __name__ == "__main__":
    main()
