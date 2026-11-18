"""Incorpora AIOE percentil basal sin alterar las variables originales del panel.

Los CSV son agregados validados de ocupados de 2022 con cobertura común en
cinco indicadores y FEX_C positivo. Se conservan como insumos intermedios;
estimar_indices_comparables.py reconstruye y contrasta estos agregados.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import hashlib
import json
import shutil
import pandas as pd
import numpy as np

BASE = (Path(__file__).resolve().parents[3])
VARIABLES = ('aioe_pct_c', 'aioe_pct_d')


def incorporar_exposicion_basal(panel, base=BASE):
    """Enlace único por cohorte/departamento, sin modificar orden ni filas."""
    original = panel.copy()
    result = panel.copy()
    for variable, filename, key, source_key in [
        ('aioe_pct_c', 'exposicion_cohortes_indices_2022.csv', 'id_cohorte', 'id_cohorte'),
        ('aioe_pct_d', 'exposicion_departamental_indices_2022.csv', 'departamento', 'dpto'),
    ]:
        source = pd.read_csv(Path(base) / 'DiD_estimaciones' / filename)
        if source[source_key].duplicated().any():
            raise ValueError(f'Claves duplicadas en {filename}')
        expected = result[key].map(source.set_index(source_key).aioe_pct)
        if not expected.dropna().between(0, 1).all():
            raise ValueError(f'Exposición fuera de escala en {filename}')
        if variable in result:
            np.testing.assert_allclose(result[variable], expected, rtol=1e-12, atol=1e-12, equal_nan=True)
        result[variable] = expected
        if result.groupby(key)[variable].nunique().gt(1).any():
            raise ValueError(f'Exposición basal no constante para {key}')
    pd.testing.assert_frame_equal(original.drop(columns=list(VARIABLES), errors='ignore'),
                                  result[original.columns].drop(columns=list(VARIABLES), errors='ignore'))
    return result


def entradas_diccionario(panel):
    return [dict(variable=v, tema='Exposición tecnológica basal',
        descripcion=f'AIOE percentil de {nivel}, fijo desde 2022',
        fuente='Agregados de ocupados GEIH–ECV de 2022 con cobertura común en cinco indicadores',
        referencia_omitida='', tipo='continua agregada',
        regla='Media ponderada por FEX_C de AIOE percentil, constante en 2022–2025',
        denominador='Suma FEX_C positivo de ocupados con cinco indicadores observados en 2022',
        unidad='escala 0–1', documentacion='regresiones/validacion/correcciones/exposicion_panel.py',
        celdas_observadas=int(panel[v].notna().sum()), cohortes_con_variacion_temporal=0)
        for v, nivel in zip(VARIABLES, ('cohorte', 'departamento'))]


def actualizar_panel_guardado(base=BASE):
    base = Path(base)
    folder = base / 'datos/imputados/panel'
    backup = folder / 'respaldo_antes_exposicion_basal_20261014'
    stem = 'panel_cohortes_2022_2025'
    panel = pd.read_parquet(folder / f'{stem}.parquet')
    updated = incorporar_exposicion_basal(panel, base)
    assert len(updated) == 1320 and not updated.duplicated(['id_cohorte', 'anio']).any()
    analytic = pd.read_stata(base / 'datos/derivados_modelos/oficiales/clasicos/indices_comparables_panel.dta')
    aligned = analytic.set_index(['id_cohorte', 'anio']).reindex(pd.MultiIndex.from_frame(updated[['id_cohorte', 'anio']]))
    for variable in VARIABLES:
        np.testing.assert_allclose(updated[variable], aligned[variable], rtol=1e-12, atol=1e-12, equal_nan=True)
    backup.mkdir(exist_ok=True)
    for name in [f'{stem}.parquet', f'{stem}.dta', 'diccionario_panel_regresion.json', 'resumen_panel_regresion.json']:
        if not (backup / name).exists():
            shutil.copy2(folder / name, backup / name)
    updated.to_parquet(folder / f'{stem}.parquet', index=False)
    updated.to_stata(folder / f'{stem}.dta', write_index=False, version=118)
    dictionary_path = folder / 'diccionario_panel_regresion.json'
    dictionary = [x for x in json.loads(dictionary_path.read_text()) if x['variable'] not in VARIABLES]
    dictionary += entradas_diccionario(updated)
    dictionary_path.write_text(json.dumps(dictionary, ensure_ascii=False, indent=2))
    summary_path = folder / 'resumen_panel_regresion.json'
    summary = json.loads(summary_path.read_text())
    summary.update(columnas=len(updated.columns), indicadores=len(dictionary))
    summary.update(indicadores_agregados=72, exposiciones_basales=2)
    summary['por_tema']['Exposición tecnológica basal'] = 2
    summary['exposicion_basal_solo_panel_principal'] = list(VARIABLES)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    sources = [base / 'DiD_estimaciones' / f'exposicion_{level}_indices_2022.csv' for level in ('cohortes', 'departamental')]
    metadata = dict(indicador='AIOE', escala='percentil', anio_base=2022,
        variables=list(VARIABLES), panel='principal; el cerrado no se modifica',
        metodo='Media FEX_C de ocupados 2022 con cobertura común en los cinco indicadores y peso positivo',
        ausentes='Se preservan como ausentes; no se sustituyen por cero',
        reproduccion='python3 neurona/quarto/auditoria/correcciones/exposicion_panel.py',
        respaldo=str(backup.relative_to(base)), filas=len(updated), columnas=len(updated.columns),
        fuentes={str(p.relative_to(base)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        verificacion='Columnas originales intactas; valores coinciden con base econométrica a tolerancia 1e-12')
    (folder / 'metadatos_exposicion_basal.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2))
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    actualizar_panel_guardado()
