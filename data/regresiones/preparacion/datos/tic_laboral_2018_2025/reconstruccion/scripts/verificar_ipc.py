"""Extrae IPC de octubre del anexo DANE local, sin valores históricos manuales."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[6]))
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion')
SOURCE = (Path(__file__).resolve().parents[6] / 'datos/anex-IPC-Indices.xlsx')


def main():
    d = pd.read_excel(SOURCE, sheet_name="IndicesIPC", header=8)
    oct_rows = d[d.iloc[:, 0].astype(str).str.strip().str.lower().eq("octubre")]
    assert len(oct_rows) == 1
    values = {str(year): float(oct_rows[year].iloc[0]) for year in range(2018, 2026)}
    assert all(value > 0 for value in values.values())
    report = {
        "fuente": str(SOURCE),
        "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "hoja": "IndicesIPC", "mes": "Octubre",
        "base": "Diciembre de 2018 = 100",
        "ipc": values,
        "factor_a_octubre_2025": {year: values["2025"] / v for year, v in values.items()},
        "correccion": "Los valores 2018–2020 del script histórico no coinciden "
                      "con octubre de este anexo. Se extraen de la fuente, no se reutilizan.",
    }
    out = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/diagnosticos')
    out.mkdir(parents=True, exist_ok=True)
    (out / "ipc_verificado.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
