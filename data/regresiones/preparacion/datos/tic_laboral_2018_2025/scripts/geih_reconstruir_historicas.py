"""Ensambla fuentes GEIH originales SON; no imputa ni armoniza educación."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile
import pandas as pd

BASE = (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025')
DEST = (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/reconstruccion/fuentes/GEIH')
LOCAL = Path("/Users/zhumber/Library/CloudStorage/OneDrive-Personal/Documents/Investigación/Coronavirus/Paper_Coronavirus/Data/GEIH")
URLS = {
    (2020, "Septiembre_2020.zip"): "https://microdatos.dane.gov.co/index.php/catalog/780/download/22294",
    (2020, "Octubre_2020.zip"): "https://microdatos.dane.gov.co/index.php/catalog/780/download/22295",
    (2020, "Noviembre_2020.zip"): "https://microdatos.dane.gov.co/index.php/catalog/780/download/22296",
    (2020, "Factores_CNPV2018_2020.zip"): "https://microdatos.dane.gov.co/index.php/catalog/780/download/22570",
    (2021, "GEIH_marco2018_II_semestre.zip"): "https://microdatos.dane.gov.co/index.php/catalog/701/download/22661",
}
KEY = ["MES", "DIRECTORIO", "SECUENCIA_P", "HOGAR", "ORDEN"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(2**20), b""):
            h.update(b)
    return h.hexdigest()


def normalizar(d):
    d.columns = d.columns.str.strip().str.upper()
    if d.columns.duplicated().any():
        raise ValueError("Columnas repetidas")
    for c in d.columns:
        if d[c].dtype == object:
            s = d[c].astype("string").str.strip()
            n = pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce")
            valid = s.notna() & s.ne("")
            if n[valid].notna().all():
                d[c] = n.astype(float)
            else:
                d[c] = s
    return d


def leer_csv(z, n):
    with z.open(n) as f:
        header = f.readline()
    sep = ";" if header.count(b";") > header.count(b",") else ","
    with z.open(n) as f:
        d = pd.read_csv(f, encoding="latin1", sep=sep, dtype=str)
    return normalizar(d)


def unir(mods, audit):
    base_name = next(n for n in mods if "persona" in n.lower() or "caracter" in n.lower())
    d = mods.pop(base_name)
    if d[KEY].isna().any().any() or d.duplicated(KEY).any():
        raise ValueError("Personas con llave ausente o duplicada")
    audit["modulos"] = [{"nombre": base_name, "filas": len(d), "variables": len(d.columns)}]
    for ix, (name, m) in enumerate(mods.items(), 1):
        keys = KEY[:-1] if "vivienda" in name.lower() else KEY
        if m[keys].isna().any().any() or m.duplicated(keys).any():
            raise ValueError(f"Llave ausente o duplicada en {name}")
        hu = m[keys].merge(d[keys].drop_duplicates(), on=keys, how="left", indicator=True)
        n_huerfanos = int(hu["_merge"].eq("left_only").sum())
        if n_huerfanos:
            if not name.lower().startswith(("otras ", "otros ")):
                raise ValueError(f"{name}: {n_huerfanos} llaves fuera de personas")
            ruta_huerfanos = DEST / str(audit["anio"]) / f"huerfanos_{audit.get('mes')}_modulo_{ix}.parquet"
            seleccion = m.merge(hu.loc[hu["_merge"].eq("left_only"), keys], on=keys, how="inner")
            seleccion.to_parquet(ruta_huerfanos, index=False)
            audit.setdefault("auxiliares_sin_persona", []).append({"modulo": name, "filas": n_huerfanos, "archivo": str(ruta_huerfanos)})
        overlap = [c for c in m if c in d and c not in keys]
        m = m.rename(columns={c: f"{c}__M{ix}" for c in overlap})
        audit["modulos"].append({"nombre": name, "filas": len(m),
                                 "variables": len(m.columns), "llaves": keys,
                                 "huerfanos": n_huerfanos, "repetidas_preservadas": overlap})
        d = d.merge(m, on=keys, how="left", validate="many_to_one", sort=False)
    return d


def main():
    manifest = []
    for (y, name), url in URLS.items():
        p = DEST / str(y) / name
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            subprocess.run(["curl", "-fL", url, "-o", str(p)], check=True)
        with zipfile.ZipFile(p) as z:
            bad = z.testzip()
            if bad:
                raise ValueError(bad)
        manifest.append({"archivo": str(p), "url": url, "sha256": sha(p)})
    ((Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/reconstruccion/fuentes/GEIH/manifest_descargas.json')).write_text(json.dumps(manifest, indent=2), encoding="utf8")
    for year in ([int(v) for v in sys.argv[1:]] or range(2018, 2022)):
        audits, frames = [], []
        if year < 2020:
            mods = {}
            for p in sorted((LOCAL / f"Append_{year}").glob("*.dta")):
                d = normalizar(pd.read_stata(p, convert_categoricals=False))
                mods[p.stem] = d.loc[d.MES.isin([9, 10, 11])].copy()
                manifest.append({"archivo": str(p), "sha256": sha(p), "origen": "archivo local preexistente"})
            audit = {"periodo": "SON", "anio": year}
            frames.append(unir(mods, audit))
            audits.append(audit)
        else:
            for month, spanish in [(9, "Septiembre"), (10, "Octubre"), (11, "Noviembre")]:
                p = DEST / str(year) / (f"{spanish}_2020.zip" if year == 2020 else "GEIH_marco2018_II_semestre.zip")
                with zipfile.ZipFile(p) as z:
                    names = [n for n in z.namelist() if n.lower().endswith(".csv")
                             and (year == 2020 or spanish.lower() in n.lower())]
                    mods = {Path(n).stem: leer_csv(z, n) for n in names}
                    for name, d in mods.items():
                        if not pd.to_numeric(d.MES, errors="coerce").eq(month).all():
                            raise ValueError(f"Mes inconsistente {name}")
                    audit = {"mes": month, "anio": year}
                    frames.append(unir(mods, audit))
                    audits.append(audit)
        # Los CSV de 2021 codifican algunas llaves como número y otras como
        # texto según el mes. Se normalizan como texto antes de concatenar para
        # conservar exactamente el identificador y evitar tipos mixtos.
        for frame in frames:
            for key in KEY:
                frame[key] = frame[key].astype("string")
        d = normalizar(pd.concat(frames, ignore_index=True, sort=False))
        if d.duplicated(KEY).any():
            raise ValueError("Duplicados entre meses")
        outdir = DEST / str(year)
        outdir.mkdir(parents=True, exist_ok=True)
        p = outdir / f"geih_son_original_ensamblada_{year}.parquet"
        d.to_parquet(p, index=False)
        report = {"anio": year, "filas": len(d), "variables": len(d.columns),
                  "archivo": str(p), "sha256": sha(p), "ensambles": audits,
                  "departamentos": sorted(d.DPTO.dropna().unique().tolist()),
                  "politica": "Sin relleno de ausentes. Columnas repetidas preservadas con sufijo. Educación original. Pesos originales sin sustitución.",
                  "no_ausentes": {c: int(d[c].notna().sum()) for c in
                                  ["P6240", "P6210", "P6220", "P3042", "OCI", "DSI", "INGLABO",
                                   "P6920", "FEX_C", "FEX_C_2011", "FEX_C18"] if c in d}}
        (outdir / "diagnostico_ensamble.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
        print(year, len(d), len(d.columns), flush=True)
    ((Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/reconstruccion/fuentes/GEIH/manifest_descargas.json')).write_text(json.dumps(manifest, indent=2), encoding="utf8")


if __name__ == "__main__":
    main()
