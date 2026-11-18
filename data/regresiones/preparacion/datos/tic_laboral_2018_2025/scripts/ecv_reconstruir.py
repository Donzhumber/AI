"""Reconstrucción conservadora ECV 2018–21; no imputación ni modelos.

Preserva todos los campos de siete módulos, renombra colisiones con el módulo
y valida cardinalidad de cada unión. Los únicos alias añadidos se documentan.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from pathlib import Path
import argparse
import hashlib
import io
import json
import subprocess
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
import pandas as pd

BASE = (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025')
QUARTO = (Path(__file__).resolve().parents[5])
LOCAL = QUARTO.parents[2] / "INSOR/ECV"
DEST = (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/reconstruccion/fuentes/ECV')
CAT = {2018: 607, 2019: 678, 2020: 718, 2021: 734}
DOWNLOADS = {
    2018: ("bienes", 10979),
    2020: ("servicios", 20605),
}
FRAG = {"composicion": "caracteristicas", "vivienda": "datos de la vivienda",
        "educacion": "educacion", "laboral": "fuerza de trabajo",
        "tic": "tecnologias", "bienes": "condiciones de vida", "servicios": "servicios del hogar"}
PERSON = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))


def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def download(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        subprocess.run(["curl", "-L", "--fail", "--retry", "2", url, "-o", str(target)], check=True)
    return {"url": url, "archivo": str(target), "sha256": digest(target)}


def csv_bytes(raw):
    try:
        txt = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        txt = raw.decode("latin1")
    sep = max([";", "\t", ","], key=txt.splitlines()[0].count)
    return pd.read_csv(io.StringIO(txt), sep=sep, dtype=str, low_memory=False)


def load(year, module):
    if year in DOWNLOADS and module == DOWNLOADS[year][0]:
        p = DEST / str(year) / f"original_{module}.zip"
        with zipfile.ZipFile(p) as z:
            assert z.testzip() is None
            name = next(n for n in z.namelist() if n.lower().endswith((".csv", ".txt")))
            d = csv_bytes(z.read(name))
        meta = {"archivo": str(p), "miembro": name, "sha256": digest(p)}
    else:
        dirs = [p for p in (LOCAL / str(year)).iterdir() if p.is_dir()
                and FRAG[module] in norm(p.name) and "programa" not in norm(p.name)]
        assert len(dirs) == 1, (year, module, dirs)
        directory = dirs[0]
        if year == 2021:
            p = next(directory.glob("*.dta"))
            d = pd.read_stata(p, convert_categoricals=False)
        else:
            p = next(directory.glob("*.csv"))
            d = csv_bytes(p.read_bytes())
        meta = {"archivo": str(p), "sha256": digest(p)}
    original = list(d.columns)
    names = [str(c).replace("\ufeff", "").replace("ï»¿", "").upper() for c in original]
    assert len(set(names)) == len(names), (year, module, "colisiones nombre", names)
    d.columns = names
    for c in d:
        if c in ["DIRECTORIO", "SECUENCIA_P", "SECUENCIA_ENCUESTA", "ORDEN"]:
            d[c] = pd.to_numeric(d[c], errors="raise").astype("Int64")
        elif d[c].dtype == "object":
            # Conservar valores textuales; no interpretar etiquetas como números.
            d[c] = d[c].astype("string")
            numeric = pd.to_numeric(d[c].str.replace(",", ".", regex=False), errors="coerce")
            if numeric.notna().sum() == d[c].notna().sum():
                d[c] = numeric
    meta.update(filas=len(d), columnas=len(d.columns), nombres_originales=original,
                nombres_normalizados=names)
    return d, meta


def ddi(year):
    p = DEST / str(year) / "diccionario.xml"
    facts = []
    for v in ET.parse(p).getroot().iter():
        if v.tag.split("}")[-1] == "var" and v.attrib.get("name", "").upper() in [
                "P1075", "P1077S21", "P1077S22", "P1084", "FEX_C", "P1_DEPARTAMENTO", "DPTO"]:
            fields = {}
            for x in v:
                tag = x.tag.split("}")[-1]
                if tag in ["labl", "universe", "qstn", "catgry"]:
                    fields.setdefault(tag, []).append(" ".join(" ".join(x.itertext()).split()))
            facts.append({"variable": v.attrib["name"], "archivo_DDI": v.attrib.get("files"), **fields})
    return facts


def build(year):
    out = DEST / str(year)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"total_ecv_{year}.parquet"
    if target.exists():
        print("Ya existe; no sobrescrito", target)
        return
    base, meta = load(year, "composicion")
    assert not base[PERSON].isna().any().any()
    assert not base.duplicated(PERSON).any()
    report = {"anio": year, "fuentes": {"composicion": meta}, "uniones": [], "aliases": {}}
    for module in ["vivienda", "educacion", "laboral", "tic", "bienes", "servicios"]:
        d, meta = load(year, module)
        report["fuentes"][module] = meta
        if module == "vivienda":
            left_keys = right_keys = ["DIRECTORIO"]
        elif module in ["bienes", "servicios"]:
            left_keys = ["DIRECTORIO", "SECUENCIA_P"]
            right_keys = ["DIRECTORIO", "SECUENCIA_ENCUESTA"]
        else:
            left_keys = right_keys = PERSON
        assert not d[right_keys].isna().any().any(), (year, module, "llave ausente")
        assert not d.duplicated(right_keys).any(), (year, module, "llave duplicada")
        rename = {c: f"{c}__{module}" for c in d if c in base.columns}
        d = d.rename(columns=rename)
        right_renamed = [rename.get(c, c) for c in right_keys]
        before = len(base)
        base = base.merge(d, how="left", left_on=left_keys, right_on=right_renamed,
                          validate="many_to_one", indicator="_union")
        unmatched = int(base["_union"].eq("left_only").sum())
        base = base.drop(columns="_union")
        assert len(base) == before
        report["uniones"].append({"modulo": module, "llave_receptor": left_keys,
                                  "llave_modulo": right_keys, "personas_sin_modulo": unmatched,
                                  "renombradas_para_preservar": rename})
    if "P1_DEPARTAMENTO" not in base and "DPTO" in base:
        base["P1_DEPARTAMENTO"] = pd.to_numeric(base["DPTO"], errors="coerce")
        report["aliases"]["P1_DEPARTAMENTO"] = "DPTO de vivienda; alias numérico sin imputación"
    report["TIC_diccionario_oficial"] = ddi(year)
    report.update(filas=len(base), columnas=len(base.columns),
                  departamentos=int(pd.to_numeric(base["P1_DEPARTAMENTO"], errors="coerce").nunique()),
                  departamento_ausente=int(base["P1_DEPARTAMENTO"].isna().sum()))
    base.to_parquet(target, index=False)
    report["sha256_salida"] = digest(target)
    (out / "reconstruccion.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(year, report["filas"], report["columnas"], report["departamentos"], flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--download", action="store_true")
    p.add_argument("--year", type=int, choices=CAT)
    args = p.parse_args()
    years = [args.year] if args.year else list(CAT)
    if args.download:
        records = []
        for year in years:
            records.append(download(f"https://microdatos.dane.gov.co/index.php/metadata/export/{CAT[year]}/ddi",
                                    DEST / str(year) / "diccionario.xml"))
            if year in DOWNLOADS:
                module, rid = DOWNLOADS[year]
                records.append(download(f"https://microdatos.dane.gov.co/index.php/catalog/{CAT[year]}/download/{rid}",
                                        DEST / str(year) / f"original_{module}.zip"))
            if year == 2019:
                records.append(download("https://microdatos.dane.gov.co/index.php/catalog/678/download/13702",
                                        DEST / str(year) / "cuestionario.pdf"))
        ((Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/reconstruccion/fuentes/ECV/descargas_manifest.json')).write_text(json.dumps(records, ensure_ascii=False, indent=2))
    else:
        for year in years:
            build(year)


if __name__ == "__main__":
    main()
