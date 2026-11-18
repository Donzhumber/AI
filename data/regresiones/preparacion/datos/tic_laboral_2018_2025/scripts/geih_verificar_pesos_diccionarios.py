"""Conserva factores CNPV2018 como tabla separada y audita enlace, sin sustituir pesos."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from geih_reconstruir_historicas import DEST, sha, leer_csv
import json
import subprocess
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd

CAT = {2018: 547, 2019: 599, 2020: 780, 2021: 701}
RES = {2018: 20918, 2019: 20915, 2020: 22570}
records = []
for y, cat in CAT.items():
    folder = DEST / str(y)
    folder.mkdir(parents=True, exist_ok=True)
    ddi = folder / "ddi.xml"
    url = f"https://microdatos.dane.gov.co/index.php/metadata/export/{cat}/ddi"
    if not ddi.exists():
        subprocess.run(["curl", "-fL", url, "-o", str(ddi)], check=True)
    record = {"anio": y, "ddi_url": url, "ddi_sha256": sha(ddi)}
    root = ET.parse(ddi).getroot()
    ns = {"d": root.tag.split("}")[0].strip("{")}
    cats = {}
    for v in root.findall(".//d:var", ns):
        name = v.attrib.get("name", "").upper()
        if name in ["P6210", "P6220", "P3042"] and name not in cats:
            cats[name] = {c.findtext("d:catValu", namespaces=ns).strip():
                          c.findtext("d:labl", namespaces=ns).strip()
                          for c in v.findall("d:catgry", ns)}
    record["categorias_educacion_ddi"] = cats
    if y in RES:
        zpath = folder / f"Factores_CNPV2018_{y}.zip"
        url = f"https://microdatos.dane.gov.co/index.php/catalog/{cat}/download/{RES[y]}"
        if not zpath.exists():
            subprocess.run(["curl", "-fL", url, "-o", str(zpath)], check=True)
        with zipfile.ZipFile(zpath) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
            f = leer_csv(z, name)
        f = f.loc[f.MES.isin([9, 10, 11])].copy()
        key = ["DIRECTORIO", "SECUENCIA_P", "ORDEN", "MES"]
        if f.duplicated(key).any() or f[key].isna().any().any():
            raise ValueError(f"Factor llave inválida {y}")
        f.to_parquet(folder / f"factores_CNPV2018_son_{y}.parquet", index=False)
        record.update(factor_url=url, factor_sha256=sha(zpath), filas_factores_son=len(f))
        source = folder / f"geih_son_original_ensamblada_{y}.parquet"
        if source.exists():
            d = pd.read_parquet(source, columns=key)
            joined = d.merge(f[key + ["FEX_C18"]], on=key, how="left", validate="one_to_one")
            record["receptores_factor_no_encontrado"] = int(joined.FEX_C18.isna().sum())
            record["pesos_sustituidos"] = False
    records.append(record)
(DEST / "diagnostico_pesos_diccionarios.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf8")
print(json.dumps([{k: v for k, v in r.items() if k != "categorias_educacion_ddi"} for r in records], ensure_ascii=False, indent=2))
