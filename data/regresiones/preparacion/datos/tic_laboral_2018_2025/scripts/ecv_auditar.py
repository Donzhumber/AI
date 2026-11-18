"""Inventario ECV de solo lectura. No armoniza ni imputa variables."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from pathlib import Path
import json
import unicodedata
import zipfile
import io
import xml.etree.ElementTree as ET
import pandas as pd
import pyarrow.parquet as pq

ROOT = (Path(__file__).resolve().parents[5])
OUT = (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/diagnosticos')
HIST = ROOT.parents[2] / "INSOR" / "ECV"
TARGET = ["P1075", "P1077S21", "P1077S22", "P1084"]
MODULES = {
    "composicion": "caracteristicas",
    "vivienda": "datos",
    "educacion": "educacion",
    "fuerza_trabajo": "fuerza",
    "bienes_internet": "condiciones",
    "tic_personal": "tecnologias",
    "servicios": "servicios",
}


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if not unicodedata.combining(c))


def inspect_csv(stream):
    raw = stream.read()
    try:
        txt = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        txt = raw.decode("latin1")
    first = txt.splitlines()[0]
    sep = max([";", "\t", ","], key=first.count)
    d = pd.read_csv(io.StringIO(txt), sep=sep, low_memory=False)
    cols = [str(c).upper() for c in d.columns]
    return {"filas": len(d), "columnas": len(cols), "variables": cols,
            "tic_presentes": [c for c in TARGET if c in cols]}


def inspect_module(p):
    result = {"ruta": str(p)}
    try:
        if p.is_dir():
            for q in sorted(p.glob("*.dta")):
                try:
                    d = pd.read_stata(q, convert_categoricals=False)
                    cols = [str(c).upper() for c in d.columns]
                    result.update(filas=len(d), columnas=len(cols), variables=cols,
                                  tic_presentes=[c for c in TARGET if c in cols],
                                  archivo_leido=str(q))
                    return result
                except Exception as e:
                    result["aviso_dta"] = str(e)
            candidates = sorted(p.glob("*.csv")) + sorted(p.glob("*.txt"))
            if candidates:
                with candidates[0].open("rb") as f:
                    result.update(inspect_csv(f))
                result["archivo_leido"] = str(candidates[0])
            else:
                q = next(p.glob("*.dta"))
                d = pd.read_stata(q, convert_categoricals=False)
                result.update(filas=len(d), columnas=len(d.columns),
                              variables=[str(c).upper() for c in d.columns])
                result["tic_presentes"] = [c for c in TARGET if c in result["variables"]]
        else:
            with zipfile.ZipFile(p) as z:
                q = next(n for n in z.namelist() if n.lower().endswith((".csv", ".txt")))
                with z.open(q) as f:
                    result.update(inspect_csv(f))
                result["archivo_leido"] = q
    except Exception as e:
        result["error_lectura"] = str(e)
    return result


def main():
    years = []
    for y in range(2018, 2026):
        base = HIST / str(y) if y < 2022 else (Path(__file__).resolve().parents[5] / 'datos/ECV') / str(y)
        row = {"anio": y, "directorio": str(base), "modulos": {}}
        entries = list(base.iterdir()) if base.exists() else []
        for key, fragment in MODULES.items():
            paths = [p for p in entries if fragment in norm(p.name)
                     and "programa" not in norm(p.name)
                     and "beneficiario" not in norm(p.name)
                     and "compra" not in norm(p.name)
                     and "adquisicion" not in norm(p.name)
                     and (p.is_dir() or p.suffix.lower() == ".zip")]
            row["modulos"][key] = [inspect_module(p) for p in paths]
        consolidated = (Path(__file__).resolve().parents[5] / 'datos/ECV') / str(y) / f"total_ecv_{y}.parquet"
        row["consolidado"] = None
        if consolidated.exists():
            f = pq.ParquetFile(consolidated)
            row["consolidado"] = {"ruta": str(consolidated),
                "filas": f.metadata.num_rows, "columnas": len(f.schema.names),
                "tic_presentes": [c for c in TARGET if c in f.schema.names]}
        labels = {}
        for xml in base.glob("diccionarios/*DDI*.xml"):
            for v in ET.parse(xml).getroot().iter():
                if v.tag.split("}")[-1] == "var" and v.attrib.get("name", "").upper() in TARGET:
                    label = next((x.text for x in v if x.tag.split("}")[-1] == "labl"), "")
                    labels[v.attrib["name"]] = " ".join((label or "").split())
        row["definiciones_DDI"] = labels
        years.append(row)
        print(y, row["consolidado"], flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    ((Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/diagnosticos/ecv_inventario.json')).write_text(json.dumps(years, ensure_ascii=False, indent=2))
    lines = ["# Auditoría ECV 2018–2025", "",
             "Los conteos de módulo incluyen identificadores y ponderadores. No deben sumarse como variables únicas.",
             "Los consolidados ECV no son bases GEIH–ECV imputadas. Ausencia de un módulo local no demuestra ausencia en DANE.", "",
             "| Año | Filas consolidado | Columnas consolidado | Módulos requeridos no localizados |",
             "| --- | --- | --- | --- |"]
    for r in years:
        c = r["consolidado"] or {}
        missing = ", ".join(k for k, v in r["modulos"].items() if not v) or "Ninguno"
        lines.append(f"| {r['anio']} | {c.get('filas','No disponible')} | {c.get('columnas','No disponible')} | {missing} |")
    lines += ["", "## Variables TIC verificadas en diccionarios recientes", "",
              "P1075 corresponde a conexión a internet del hogar. P1077S21 y P1077S22 son tenencia de computador de escritorio y portátil. P1084 es frecuencia de uso personal de internet.",
              "El hogar y la persona son universos diferentes. Antes de armonizar años históricos deben verificarse etiquetas, categorías, filtros y periodos de referencia de cada año.",
              "", "## Límites", "",
              "Las fuentes históricas están fuera de la carpeta del proyecto. No existe aquí un consolidado ECV 2018–2021 cuya procedencia completa pueda certificarse mediante los archivos total_ecv.",
              "ALERTA 2021: varios CSV locales son extractos, mientras sus DTA contienen más registros. TIC tiene 12.997 filas en CSV frente a 238.888 en DTA; fuerza de trabajo 36.986 frente a 209.349. El script prefiere DTA legible y documenta CSV como respaldo solo si Stata no es compatible. No se deben elegir formatos indistintamente sin comparar cobertura.",
              "No se sustituyeron ausentes por cero ni se ejecutó imputación o estimación. Se requiere resolver diferencias de preparación histórica antes de certificar comparabilidad."]
    ((Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/diagnosticos/ecv_inventario.md')).write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
