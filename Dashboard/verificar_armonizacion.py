"""Comprueba fuentes comunes, rutas, universos y exportaciones del dashboard.

No estima modelos ni modifica microdatos. Ejecutar después de los generadores.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'data'))
from pathlib import Path
import hashlib
import json
import re
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = Path(__file__).resolve().parents[1] / 'data'
DOC_ROOT = Path(__file__).resolve().parents[1]
PUB_DASH = BASE / 'datos/publicacion/dashboard'
sys.path.insert(0, str(BASE))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS, INDICES
from regresiones.preparacion.datos.armonizados_2018_2025.indicadores import uso_ia_validado


def main():
    report = {"coleccion": "data/datos/armonizados_2018_2025", "pruebas": []}
    tests = report["pruebas"]
    profile = json.loads((PUB_DASH / 'perfiles_uso_ia_2025.json').read_text())
    columns = ["P6040", "FEX_C", "OCI_geih", "DSI_geih", "P1084"]
    columns += [f"P1083S{i}" for i in range(1, 22)]
    data = pd.read_parquet((BASE / 'datos/armonizados_2018_2025/microdatos/ecv_geih_imputada_2025.parquet'), columns=columns)
    data = data.loc[data.P6040.ge(5) & np.isfinite(data.FEX_C) & data.FEX_C.gt(0)].copy()
    data["uso_ia"], routing = uso_ia_validado(data)
    assert routing == profile["diagnostico_ruta"]
    for universe in ["Población de 5 años o más", "Ocupados", "Desempleados", "Fuerza laboral"]:
        mask = np.ones(len(data), dtype=bool)
        if universe == "Ocupados":
            mask = data.OCI_geih.eq(1)
        elif universe == "Desempleados":
            mask = data.DSI_geih.eq(1)
        elif universe == "Fuerza laboral":
            mask = data.OCI_geih.eq(1) | data.DSI_geih.eq(1)
        direct = data.loc[mask]
        rows = [r for r in profile["filas"] if r["universo"] == universe and r["dimension"] == "Sexo"]
        assert sum(r["n"] for r in rows) == len(direct)
        valid = direct.uso_ia.notna()
        numerator = sum(r["poblacion_ia_valida"] * r["uso_ia"] for r in rows)
        denominator = sum(r["poblacion_ia_valida"] for r in rows)
        expected = np.average(direct.loc[valid, "uso_ia"], weights=direct.loc[valid, "FEX_C"])
        np.testing.assert_allclose(numerator / denominator, expected, rtol=1e-12)
        tests.append({"prueba": "IA por sexo versus cálculo directo", "universo": universe,
                      "n": len(direct), "prevalencia": float(expected), "coincide": True})
    pairs = json.loads((PUB_DASH / 'validacion_parejas_indices.json').read_text())
    assert len(pairs) == 80
    tests.append({"prueba": "diez parejas, cuatro años y dos universos", "combinaciones": len(pairs), "coincide": True})
    catalog = json.loads((PUB_DASH / 'catalogo_ocupaciones_multianual.json').read_text())
    reference = pd.read_csv(INDICES).set_index("ciuo08")
    aliases = {"exp_aioe_pct": "aioe_pct", "exp_webb_robot_pct": "robots_pct",
               "exp_webb_software_pct": "software_pct", "exp_webb_ia_pct": "webb_ia_pct",
               "exp_gpt4_beta_pct": "llm_pct"}
    for year, result in catalog["datos_por_anio"].items():
        for row in result["profesiones"]:
            code = row["ciuo"]
            for alias, original in aliases.items():
                if row[alias] is not None:
                    np.testing.assert_allclose(row[alias] / 100, reference.loc[code, original], atol=1e-12)
        tests.append({"prueba": "catálogo fijo sin rangos anuales", "anio": int(year), "coincide": True})
    qmd = (ROOT / 'dashboard.qmd').read_text()
    attachments = sorted(set(re.findall(r'FileAttachment\("([^\"]+)"\)', qmd)))
    missing = [p for p in attachments if not (ROOT / p).resolve().exists()]
    assert not missing, missing
    tests.append({"prueba": "FileAttachment con destino existente", "archivos": len(attachments), "coincide": True})
    report["archivos_sha256"] = {str(p.relative_to(DOC_ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [PUB_DASH / 'perfiles_uso_ia_2025.json', PUB_DASH / 'cuadrantes_anexo.json',
                                           PUB_DASH / 'catalogo_ocupaciones_multianual.json', ROOT / 'dashboard.qmd']}
    (PUB_DASH / 'verificacion_armonizacion.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print("OK IA validada, universos, parejas, catálogo y rutas del dashboard.")


if __name__ == "__main__":
    main()
