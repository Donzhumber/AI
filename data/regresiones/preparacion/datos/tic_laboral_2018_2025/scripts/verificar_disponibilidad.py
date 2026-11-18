"""Inventario reproducible sin modificar fuentes ni estimar sobre series no aprobadas."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from pathlib import Path
import json
import pandas as pd
import pyarrow.parquet as pq

ROOT = (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025')
DATOS = (Path(__file__).resolve().parents[5] / 'datos')


def main():
    fuentes = []
    for year in range(2018, 2026):
        for encuesta, pattern in [
            ("GEIH", f"GEIH/{year}/total_son_full_{year}.parquet"),
            ("ECV", f"ECV/{year}/total_ecv_{year}.parquet"),
        ]:
            path = DATOS / pattern
            row = dict(anio=year, encuesta=encuesta, archivo=str(path),
                       disponible=path.exists())
            if path.exists():
                meta = pq.ParquetFile(path)
                row.update(filas=meta.metadata.num_rows,
                           columnas=len(meta.schema_arrow),
                           variables=meta.schema_arrow.names)
            fuentes.append(row)
    panels = []
    old = (Path(__file__).resolve().parents[5] / 'datos/extensiones_historicas/integrada_geih_ecv_2018_2025/panel')
    for path in sorted(old.glob("pseudopanel*.parquet")):
        d = pd.read_parquet(path)
        panels.append(dict(
            archivo=str(path), filas=len(d), columnas=len(d.columns),
            variables=list(d.columns), cohortes=int(d.id_cohorte.nunique()),
            filas_anio={str(k): int(v) for k, v in d.groupby("anio").size().items()},
            duplicados=int(d.duplicated(["id_cohorte", "anio"]).sum()),
            ausentes={c: int(d[c].isna().sum()) for c in d},
            estado="existente_no_certificado_como_panel_TIC_definitivo",
        ))
    report = dict(
        estado="auditoria_previa_requiere_decision_metodologica",
        nota="Ausencia en ruta canónica no prueba ausencia de módulos en otras rutas; "
             "consultar inventarios ECV y GEIH. No se reconstruyen ni estiman series.",
        fuentes_canonicas=fuentes, paneles_existentes=panels,
    )
    out = (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/diagnosticos')
    out.mkdir(parents=True, exist_ok=True)
    (out / "disponibilidad.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for row in fuentes:
        print(row["anio"], row["encuesta"], row.get("filas"), row.get("columnas"))
    for p in panels:
        print(Path(p["archivo"]).name, p["filas"], p["columnas"], p["cohortes"])


if __name__ == "__main__":
    main()
