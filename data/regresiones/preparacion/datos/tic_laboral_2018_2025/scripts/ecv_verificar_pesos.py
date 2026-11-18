"""Contrasta FEX_C local con personas oficiales DANE sin modificar bases."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
import json
import zipfile
import pandas as pd
import numpy as np
from ecv_reconstruir import DEST, CAT, download, csv_bytes, PERSON

IDS = {2018:10977, 2019:13707, 2020:20599, 2021:21121}
results = []
for year, rid in IDS.items():
    p = DEST / str(year) / "composicion_verificacion_oficial.zip"
    meta = download(f"https://microdatos.dane.gov.co/index.php/catalog/{CAT[year]}/download/{rid}", p)
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        member = next(n for n in z.namelist() if n.lower().endswith((".csv", ".txt")))
        official = csv_bytes(z.read(member))
    official.columns = [c.upper() for c in official]
    official = official[PERSON+["FEX_C"]].copy()
    local = pd.read_parquet(DEST / str(year) / f"total_ecv_{year}.parquet", columns=PERSON+["FEX_C"])
    for d in [local, official]:
        for c in d:
            d[c] = pd.to_numeric(d[c].astype("string").str.replace(",", ".", regex=False), errors="raise")
    comp = local.merge(official, on=PERSON, how="outer", validate="one_to_one",
                       suffixes=("_local","_oficial"), indicator=True)
    valid = comp["_merge"].eq("both")
    dif = (comp.loc[valid,"FEX_C_local"]-comp.loc[valid,"FEX_C_oficial"]).abs()
    result = {"anio": year, **meta, "miembro": member, "n_local":len(local),
              "n_oficial":len(official), "coinciden_llaves":bool(valid.all()),
              "max_diferencia_peso":float(dif.max()),
              "diferencias_mayores_1e_6":int(dif.gt(1e-6).sum())}
    results.append(result)
    print(result, flush=True)
(DEST / "verificacion_pesos_oficiales.json").write_text(json.dumps(results,ensure_ascii=False,indent=2))
