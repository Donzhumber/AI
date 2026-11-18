"""Inventario GEIH sin modificar fuentes ni armonizar silenciosamente."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from pathlib import Path
import io
import json
import zipfile
import pandas as pd
import pyarrow.parquet as pq

BASE = (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025')
DATOS = (Path(__file__).resolve().parents[5] / 'datos')
EXTERNA = Path("/Users/zhumber/Library/CloudStorage/OneDrive-Personal/Documents/Investigación/Coronavirus/Paper_Coronavirus/Data/GEIH")
CANDIDATAS = {
    "ocupado": ["OCI"], "desocupado": ["DSI"],
    "ingreso_laboral_no_equivale_solo_salario": ["INGLABO"],
    "salario_monetario": ["P6500"],
    "posicion_ocupacional": ["P6430"],
    "cotizacion_pensional": ["P6920"],
    "horas_habituales": ["P6800"], "horas_efectivas": ["P7040"],
    "peso": ["FEX_C18", "FEX_C_2011", "FEX_C"],
    "departamento": ["DPTO"], "sexo": ["P3271", "P6020"],
    "edad": ["P6040"], "actividad_principal": ["P6240"],
}


def contenidos(zf, prefijo=""):
    salida = []
    for nombre in zf.namelist():
        if nombre.lower().endswith(".csv"):
            salida.append(prefijo + nombre)
        elif nombre.lower().endswith(".zip") and "csv" in nombre.lower():
            with zipfile.ZipFile(io.BytesIO(zf.read(nombre))) as interior:
                salida.extend(contenidos(interior, prefijo + nombre + "::"))
    return salida


def main():
    resultados = []
    for year in range(2018, 2026):
        registro = {"anio": year, "periodo_objetivo": "septiembre-octubre-noviembre",
                    "consolidado_disponible": False, "modulos": [], "advertencias": []}
        ruta = (Path(__file__).resolve().parents[5] / 'datos/GEIH') / str(year) / f"total_son_full_{year}.parquet"
        columnas = set()
        if ruta.exists():
            pf = pq.ParquetFile(ruta)
            nombres = pf.schema_arrow.names
            columnas.update(c.upper() for c in nombres)
            registro.update(consolidado_disponible=True, ruta=str(ruta),
                            filas=pf.metadata.num_rows, variables=len(nombres))
            registro["columnas"] = nombres
            for z in sorted(ruta.parent.glob("*.zip")):
                with zipfile.ZipFile(z) as archivo:
                    registro["modulos"].append({"archivo": str(z), "csv": contenidos(archivo)})
            seleccion = [c for c in nombres if c.upper() in sum(CANDIDATAS.values(), [])]
            df = pd.read_parquet(ruta, columns=seleccion)
            registro["no_ausentes"] = {c: int(df[c].notna().sum()) for c in seleccion}
            registro["departamentos_observados"] = sorted(df["DPTO"].dropna().unique().tolist())
        else:
            carpeta = EXTERNA / f"Append_{year}"
            for f in sorted(carpeta.glob("*.dta")):
                with pd.io.stata.StataReader(f, convert_categoricals=False) as r:
                    muestra = r.read(nrows=1)
                    nombres = muestra.columns.tolist()
                    columnas.update(c.upper() for c in nombres)
                    n_total = int(r._nobs)
                mes = next((c for c in nombres if c.upper() == "MES"), None)
                n_son = None
                if mes:
                    meses = pd.read_stata(f, columns=[mes], convert_categoricals=False)[mes]
                    n_son = int(pd.to_numeric(meses, errors="coerce").isin([9, 10, 11]).sum())
                registro["modulos"].append({"archivo": str(f), "filas_anuales": n_total,
                                            "filas_son": n_son, "variables": len(nombres),
                                            "columnas": nombres})
            registro["variables_distintas_union_modulos"] = len(columnas)
            registro["advertencias"].append(
                "No hay consolidado donante histórico en la ruta del proyecto. "
                "La unión de nombres de módulos no es un conteo de variables de una base ensamblada."
            )
            if not registro["modulos"]:
                registro["advertencias"].append(
                    "No se localizaron fuentes GEIH en las rutas declaradas por los pipelines históricos; "
                    "las bases imputadas no sustituyen estas fuentes para validación."
                )
            if year < 2021:
                registro["advertencias"].append(
                    "Marco y codificación históricos. No tratar FEX_C_2011 como FEX_C18 "
                    "sin verificar factores oficiales y correspondencia."
                )
        registro["variables_candidatas_presentes"] = {
            nombre: [c for c in opciones if c in columnas] for nombre, opciones in CANDIDATAS.items()
        }
        resultados.append(registro)
    out = (Path(__file__).resolve().parents[5] / 'datos/tic_laboral_2018_2025/diagnosticos')
    out.mkdir(parents=True, exist_ok=True)
    (out / "geih_inventario.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf8")
    texto = ["# Inventario GEIH 2018–2025", "",
             "Auditoría de disponibilidad, no certificación de equivalencia metodológica ni de informalidad oficial.",
             "", "| Año | Consolidado | Filas SON | Variables consolidadas | Módulos/ZIP encontrados |",
             "|---|---|---:|---:|---:|"]
    for r in resultados:
        texto.append(f"| {r['anio']} | {'Sí' if r['consolidado_disponible'] else 'No'} | "
                     f"{r.get('filas', 'No ensamblado')} | {r.get('variables', 'No ensamblado')} | {len(r['modulos'])} |")
    texto += ["", "## Precauciones", "",
              "En 2018 y 2019 los módulos externos son archivos anuales; el JSON incluye también sus filas de septiembre a noviembre.",
              "La presencia de P6920 permite estudiar cotización, pero no define por sí sola informalidad oficial.",
              "INGLABO incluye ingreso laboral y no debe etiquetarse automáticamente salario. La medida salarial exige seleccionar asalariados y conceptos comparables.",
              "No se han reconstruido fuentes históricas ni sustituido ponderadores. Los nombres técnicos son candidatos cuya semántica y universos deben contrastarse en los diccionarios.",
              "Los ZIP modernos contienen módulos de características generales, vivienda, fuerza laboral y ocupados/no ocupados; su detalle exacto queda en el JSON.",
              "La ausencia consignada es en las rutas inspeccionadas, no una afirmación de inexistencia en DANE."]
    (out / "geih_inventario.md").write_text("\n".join(texto) + "\n", encoding="utf8")
    for r in resultados:
        print(r["anio"], r.get("filas"), r.get("variables"), len(r["modulos"]))


if __name__ == "__main__":
    main()
