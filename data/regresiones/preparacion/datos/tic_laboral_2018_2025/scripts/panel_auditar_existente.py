"""Inventario no destructivo del piloto histórico y sus fuentes consolidadas."""

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
HIST = (Path(__file__).resolve().parents[5] / 'datos/extensiones_historicas/integrada_geih_ecv_2018_2025')


def describe(path):
    pf = pq.ParquetFile(path)
    names = pf.schema_arrow.names
    return dict(archivo=str(path.relative_to(DATOS)), filas=pf.metadata.num_rows,
                columnas=len(names), nombres=names)


def main():
    result = {"microdatos": [], "paneles": [], "fuentes": []}
    for year in range(2018, 2026):
        path = ((Path(__file__).resolve().parents[5] / 'datos/extensiones_historicas/integrada_geih_ecv_2018_2025/microdatos') if year < 2022 else (Path(__file__).resolve().parents[5] / 'datos/imputados')) / f"ecv_geih_imputada_{year}.parquet"
        item = describe(path)
        names = item["nombres"]
        item.update(anio=year, columnas_sufijo_geih=sum(n.endswith("_geih") for n in names),
                    columnas_sin_sufijo_geih=sum(not n.endswith("_geih") for n in names))
        cols = [c for c in ["P1075", "P1_DEPARTAMENTO", "id_donante_geih"] if c in names]
        d = pd.read_parquet(path, columns=cols)
        item["departamentos"] = int(d["P1_DEPARTAMENTO"].nunique())
        item["donantes_distintos"] = int(d.id_donante_geih.nunique())
        item["internet_valores"] = {str(k): int(v) for k, v in d.P1075.value_counts(dropna=False).items()} if "P1075" in d else {}
        result["microdatos"].append(item)
        for survey, filename in [("ECV", f"total_ecv_{year}.parquet"), ("GEIH", f"total_son_full_{year}.parquet")]:
            source = ((Path(__file__).resolve().parents[5] / 'datos/extensiones_historicas/integrada_geih_ecv_2018_2025/fuentes') if year < 2022 else DATOS) / survey / str(year) / filename
            item = dict(anio=year, encuesta=survey, disponible=source.exists(), archivo=str(source.relative_to(DATOS)))
            if source.exists():
                item.update(describe(source))
            result["fuentes"].append(item)
    for path in sorted(((Path(__file__).resolve().parents[5] / 'datos/extensiones_historicas/integrada_geih_ecv_2018_2025/panel')).glob("pseudopanel*.parquet")):
        item = describe(path)
        d = pd.read_parquet(path)
        item.update(anios=sorted(int(x) for x in d.anio.unique()), cohortes=int(d.id_cohorte.nunique()),
                    duplicados=int(d.duplicated(["id_cohorte", "anio"]).sum()),
                    filas_por_anio={str(k): int(v) for k, v in d.groupby("anio").size().items()},
                    ausentes_por_variable=d.isna().sum().astype(int).to_dict())
        result["paneles"].append(item)
    out = (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/diagnosticos/panel_inventario_existente.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k: [{a: b for a, b in x.items() if a != "nombres"} for x in v] for k, v in result.items()}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
