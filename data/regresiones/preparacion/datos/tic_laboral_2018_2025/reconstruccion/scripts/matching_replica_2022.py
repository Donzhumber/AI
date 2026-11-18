"""Replica punteros de 2022, solo lectura de fuentes y producción existente."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[6]))
import json
import pandas as pd
from matching_anexo import QUARTO, select_donors
from regresiones.validacion.correcciones.educacion import ESCOLARIDAD_GEIH
from pathlib import Path

datos = QUARTO/"datos"
gc = ["DPTO", "CLASE", "P3271", "P6040", "P6050", "DIRECTORIO", "SECUENCIA_P", "P6240", "P3042"]
ec = ["P1_DEPARTAMENTO", "CLASE", "P6020", "P6040", "P6051", "CANT_PERSONAS_HOGAR", "P6240",
      "P8586", "P8587", "P1088", "P1088S1", "P6216"]
g = pd.read_parquet(datos/"GEIH/2022/total_son_full_2022.parquet", columns=gc)
e = pd.read_parquet(datos/"ECV/2022/total_ecv_2022.parquet", columns=ec).dropna(subset=["P1_DEPARTAMENTO", "CLASE"]).reset_index(drop=True)
g["EDUCACION_ARM_GEIH"] = g.P3042.map(ESCOLARIDAD_GEIH)
idx, fallback = select_donors(g, e, {"GEIH": 15, "ECV": 12})
old = pd.read_parquet(datos/"imputados/ecv_geih_imputada_2022.parquet", columns=["id_donante_geih", "en_fallback"])
result = dict(anio=2022, receptores=len(e), diferencias_donante=int((idx != old.id_donante_geih.to_numpy()).sum()),
              diferencias_fallback=int((fallback != old.en_fallback.to_numpy()).sum()),
              nota="Umbrales estructurales 15/12 usados únicamente para réplica moderna; no habilitan años históricos.")
out = (Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/diagnosticos/matching_replica_2022.json')
(Path(__file__).resolve().parents[6] / 'datos/tic_laboral_2018_2025/reconstruccion/diagnosticos').mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False, indent=2))
