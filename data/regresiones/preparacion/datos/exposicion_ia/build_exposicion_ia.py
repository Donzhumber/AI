"""Construye la tabla CIUO-08 A.C. (4 dígitos) -> puntuaciones de exposición a IA
(AIOE, Webb, Eloundou et al.), vía SOC-2010 <-> ISCO-08 <-> CIUO-08 A.C.
Fase 2 del plan: solo construye la tabla de referencia, no modifica ningun .qmd.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))
import pandas as pd
import numpy as np
import openpyxl
import json
from pathlib import Path

DEST = (Path(__file__).resolve().parents[4] / 'datos/exposicion_ia')
REQUERIDOS = ['crosswalks/EstructuraCIUO_08_A_C.xlsx', 'crosswalks/isco_soc_crosswalk.xls',
              'felten_raj_seamans_2021/AIOE_DataAppendix.xlsx', 'webb_2020/final_df_out.dta',
              'eloundou_2023/occ_level.csv']
faltantes = [str(DEST / x) for x in REQUERIDOS if not (DEST / x).exists()]
if faltantes:
    raise FileNotFoundError('No se puede reconstruir el crosswalk original sin los archivos fuente: '
                            + ', '.join(faltantes)
                            + '. Para normalizar el catálogo recibido utilice auditar_indices.py.')


# ---------------------------------------------------------------------------
# 1. CIUO-08 A.C. (Colombia): lista de codigos de 4 digitos + jerarquia
# ---------------------------------------------------------------------------
wb = openpyxl.load_workbook(f"{DEST}/crosswalks/EstructuraCIUO_08_A_C.xlsx", data_only=True)
ws = wb["CIUO-08 A.C."]
filas = []
for row in ws.iter_rows(min_row=5, values_only=True):
    c, desc = row[0], row[1]
    if c is not None:
        s = str(c).strip()
        if s.isdigit():
            filas.append((s, desc))

ciuo_4d = pd.DataFrame([(c, d) for c, d in filas if len(c) == 4], columns=["ciuo08", "ciuo08_desc"])
ciuo_4d["ciuo08_3d"] = ciuo_4d["ciuo08"].str[:3]
print(f"CIUO-08 A.C. codigos de 4 digitos: {len(ciuo_4d)}")

# ---------------------------------------------------------------------------
# 2. Crosswalk BLS: ISCO-08 (4 dig, zero-padded) <-> SOC-2010 (6 dig)
# ---------------------------------------------------------------------------
cw = pd.read_excel(f"{DEST}/crosswalks/isco_soc_crosswalk.xls", header=6)
cw.columns = [c.strip() for c in cw.columns]
cw["isco08"] = cw["ISCO-08 Code"].astype(str).str.strip().str.zfill(4)
cw["soc2010"] = cw["2010 SOC Code"].astype(str).str.strip()
cw = cw[["isco08", "soc2010"]].dropna().drop_duplicates()
print(f"Pares ISCO-08 <-> SOC-2010 en crosswalk BLS: {len(cw)}")

isco_validos = set(cw["isco08"].unique())

# ---------------------------------------------------------------------------
# 3. Mapear CIUO-08 A.C. -> ISCO-08: identidad directa (436/455), y fallback
#    al grupo padre de 3 digitos para los 19 codigos exclusivos de Colombia.
# ---------------------------------------------------------------------------
ciuo_4d["isco08_directo"] = ciuo_4d["ciuo08"].where(ciuo_4d["ciuo08"].isin(isco_validos))
sin_match = ciuo_4d[ciuo_4d["isco08_directo"].isna()].copy()
print(f"CIUO-08 sin match directo a ISCO-08: {len(sin_match)} -> {sorted(sin_match['ciuo08'])}")

# Fallback: usar el ISCO-08 cuyo codigo empieza igual en los primeros 3 digitos
# (aproximacion documentada, no identidad).
isco_por_3d = {}
for code in isco_validos:
    isco_por_3d.setdefault(code[:3], []).append(code)

def fallback_3d(ciuo_code):
    candidatos = isco_por_3d.get(ciuo_code[:3], [])
    return candidatos  # lista de codigos ISCO-08 que comparten los 3 primeros digitos

ciuo_4d["isco08_fallback_3d"] = ciuo_4d["ciuo08"].apply(
    lambda c: fallback_3d(c) if c not in isco_validos else None
)
ciuo_4d["metodo_isco"] = np.where(ciuo_4d["isco08_directo"].notna(), "identidad_4d", "fallback_3d")
ciuo_4d.loc[ciuo_4d["isco08_fallback_3d"].apply(lambda x: x is not None and len(x) == 0), "metodo_isco"] = "sin_match"

n_sin_match_total = (ciuo_4d["metodo_isco"] == "sin_match").sum()
print(f"CIUO-08 sin ningun match (ni directo ni por grupo de 3 digitos): {n_sin_match_total}")

# ---------------------------------------------------------------------------
# 4. Indices por ocupacion (SOC / O*NET-SOC)
# ---------------------------------------------------------------------------
aioe = pd.read_excel(f"{DEST}/felten_raj_seamans_2021/AIOE_DataAppendix.xlsx", sheet_name="Appendix A")
aioe.columns = [c.strip() for c in aioe.columns]
aioe["soc2010"] = aioe["SOC Code"].astype(str).str.strip()
aioe = aioe[["soc2010", "AIOE"]].dropna()
print(f"AIOE: {len(aioe)} ocupaciones SOC")

webb = pd.read_stata(f"{DEST}/webb_2020/final_df_out.dta")
webb["soc2010"] = webb["onetsoccode"].astype(str).str.strip().str.split(".").str[0]
webb_agg = webb.groupby("soc2010")[["ai_score", "software_score", "robot_score"]].mean().reset_index()
print(f"Webb (agregado de O*NET-SOC a SOC-2010 por promedio): {len(webb_agg)} codigos SOC")

eloundou = pd.read_csv(f"{DEST}/eloundou_2023/occ_level.csv")
eloundou.columns = [c.strip() for c in eloundou.columns]
eloundou["soc2010"] = eloundou["O*NET-SOC Code"].astype(str).str.strip().str.split(".").str[0]
cols_elo = ["dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
            "human_rating_alpha", "human_rating_beta", "human_rating_gamma"]
eloundou_agg = eloundou.groupby("soc2010")[cols_elo].mean().reset_index()
print(f"Eloundou et al. (agregado a SOC-2010 por promedio): {len(eloundou_agg)} codigos SOC")

# ---------------------------------------------------------------------------
# 5. SOC-2010 -> ISCO-08 (muchos-a-muchos): promedio simple, igual que el
#    atajo metodologico documentado por el paper del FMI (IMF WP 2023/216).
# ---------------------------------------------------------------------------
def agregar_a_isco(tabla_soc, cols):
    merged = cw.merge(tabla_soc, on="soc2010", how="inner")
    return merged.groupby("isco08")[cols].mean().reset_index()

aioe_isco = agregar_a_isco(aioe, ["AIOE"])
webb_isco = agregar_a_isco(webb_agg, ["ai_score", "software_score", "robot_score"])
eloundou_isco = agregar_a_isco(eloundou_agg, cols_elo)

isco_scores = aioe_isco.merge(webb_isco, on="isco08", how="outer").merge(eloundou_isco, on="isco08", how="outer")
print(f"Codigos ISCO-08 con al menos un indice: {len(isco_scores)}")

# ---------------------------------------------------------------------------
# 6. CIUO-08 A.C. -> puntuaciones finales
# ---------------------------------------------------------------------------
directo = ciuo_4d[ciuo_4d["metodo_isco"] == "identidad_4d"][["ciuo08", "ciuo08_desc", "metodo_isco"]].copy()
directo["isco08_usado"] = directo["ciuo08"]

filas_fallback = []
for _, r in ciuo_4d[ciuo_4d["metodo_isco"] == "fallback_3d"].iterrows():
    for isco_code in r["isco08_fallback_3d"]:
        filas_fallback.append({"ciuo08": r["ciuo08"], "ciuo08_desc": r["ciuo08_desc"],
                                "metodo_isco": "fallback_3d", "isco08_usado": isco_code})
fallback_df = pd.DataFrame(filas_fallback)

base = pd.concat([directo, fallback_df], ignore_index=True)
base = base.merge(isco_scores, left_on="isco08_usado", right_on="isco08", how="left", suffixes=("", "_y"))

score_cols = ["AIOE", "ai_score", "software_score", "robot_score"] + cols_elo
final = base.groupby(["ciuo08", "ciuo08_desc", "metodo_isco"], as_index=False)[score_cols].mean()

sin_match_final = ciuo_4d[ciuo_4d["metodo_isco"] == "sin_match"][["ciuo08", "ciuo08_desc"]].copy()
sin_match_final["metodo_isco"] = "sin_match"
for c in score_cols:
    sin_match_final[c] = np.nan

final = pd.concat([final, sin_match_final], ignore_index=True).sort_values("ciuo08").reset_index(drop=True)

# ---------------------------------------------------------------------------
# 7. Identificar explicitamente por que un codigo queda sin ningun indice:
#    fuerzas militares (gran grupo 0, fuera del alcance de O*NET en las tres
#    fuentes), sin correspondencia ISCO-08, o con ISCO-08 pero sin indice.
# ---------------------------------------------------------------------------
tiene_dato = final[score_cols].notna().any(axis=1)
es_militar = final["ciuo08"].str[0] == "0"

motivo = pd.Series(pd.NA, index=final.index, dtype="object")
motivo[es_militar] = "fuerzas_militares_fuera_de_onet"
motivo[(~es_militar) & (~tiene_dato) & (final["metodo_isco"] == "sin_match")] = "sin_correspondencia_isco08"
motivo[(~es_militar) & (~tiene_dato) & (final["metodo_isco"] != "sin_match")] = "sin_indice_disponible_para_este_isco08"

final.insert(3, "es_fuerzas_militares", es_militar)
final.insert(4, "motivo_sin_dato", motivo)

out_path = f"{DEST}/ciuo08_exposicion_ia_scores.csv"
final.to_csv(out_path, index=False, encoding="utf-8")
print(f"\nGuardado: {out_path}")
print(f"Total filas CIUO-08: {len(final)}")
print("Cobertura por metodo:")
print(final["metodo_isco"].value_counts())
print("\nCobertura de al menos un indice no nulo (AIOE, Webb o Eloundou):")
print(tiene_dato.value_counts())
print("\nMotivo de los codigos sin ningun dato:")
print(motivo.value_counts(dropna=False))
print("\nEjemplo de filas:")
print(final.head(5).to_string())
