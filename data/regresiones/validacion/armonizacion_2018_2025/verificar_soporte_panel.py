"""Verificación independiente del soporte del panel con indicadores individuales.

Recalcula los tres resultados laborales por cohorte en2018–2025 y contrasta
medias, receptores, donantes, cobertura y tamaños PET con sus tablas canónicas.
No reconstruye imputaciones ni modifica las bases.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import json
import sys
import numpy as np
import pandas as pd

BASE = (Path(__file__).resolve().parents[3])
sys.path.insert(0, str(BASE))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import CARPETA, INDICADORES, PANEL_2018_2025

OUT = (Path(__file__).resolve().parents[3] / 'datos/armonizados_2018_2025/diagnosticos/panel_2018_2025/comprobacion_microdatos.json')
VARIABLES = [
    ('tasa_desempleo', 'desempleo', False),
    ('prop_no_cotiza_respuesta12', 'no_cotiza', False),
    ('log_sal_real_medio', 'ingreso_laboral_real', True),
]


def ejecutar():
    panel = pd.read_parquet(PANEL_2018_2025).set_index(['anio', 'id_cohorte'])
    diagnosticos = pd.read_parquet((Path(__file__).resolve().parents[3] / 'datos/armonizados_2018_2025/construccion/paneles/diagnosticos_panel_regresion.parquet'))
    diagnosticos = diagnosticos.loc[diagnosticos.variante.eq('principal')].set_index(['anio', 'id_cohorte', 'variable'])
    registros = []
    for year, source in INDICADORES.items():
        print(f'Verificando soporte individual {year}', flush=True)
        d = pd.read_parquet(source, columns=['P1_DEPARTAMENTO', 'P6020', 'FEX_C', 'id_donante_geih', 'edad', 'pet', 'ocupado', 'desempleo', 'no_cotiza', 'ingreso_laboral_real'])
        w = pd.to_numeric(d.FEX_C, errors='coerce')
        d = d.loc[d.pet.eq(1) & np.isfinite(w) & w.gt(0)].copy()
        # Los factores heredados pueden estar almacenados en float32.
        # La agregación canónica calcula las sumas en doble precisión.
        d['FEX_C'] = d.FEX_C.astype('float64')
        born = year - d.edad
        generation = pd.Series(np.select([born.le(1964), born.le(1974), born.le(1984), born.le(1994)], [1, 2, 3, 4], default=5), index=d.index)
        d['id_cohorte'] = d.P1_DEPARTAMENTO.astype(int).astype(str) + '_' + d.P6020.astype(int).astype(str) + '_' + generation.astype(str)
        target = panel.xs(year, level='anio')
        pet = d.groupby('id_cohorte').size().reindex(target.index)
        np.testing.assert_array_equal(pet.to_numpy(), target.n_obs_pet.to_numpy())
        for variable, source_column, use_log in VARIABLES:
            valid = d[source_column].notna()
            if use_log:
                valid &= d[source_column].gt(0)
            z = d.loc[valid].copy()
            z['_numerador'] = z[source_column].astype(float) * z.FEX_C
            grouped = z.groupby('id_cohorte')
            calculated = grouped.agg(receptores=('id_cohorte', 'size'), donantes=('id_donante_geih', 'nunique'), masa=('FEX_C', 'sum'), numerador=('_numerador', 'sum')).reindex(target.index)
            mean = calculated.numerador / calculated.masa
            if use_log:
                mean = np.log(mean)
            domain = d.loc[d.desempleo.notna() if variable == 'tasa_desempleo' else d.ocupado.eq(1)].groupby('id_cohorte').FEX_C.sum().reindex(target.index)
            coverage = calculated.masa / domain
            expected = diagnosticos.xs((year, variable), level=('anio', 'variable')).reindex(target.index)
            np.testing.assert_array_equal(calculated.receptores.to_numpy(), expected.n_observados.to_numpy())
            np.testing.assert_array_equal(calculated.donantes.to_numpy(), expected.n_donantes_individuales.to_numpy())
            np.testing.assert_allclose(mean, target[variable], rtol=1e-12, atol=1e-12, equal_nan=True)
            np.testing.assert_allclose(coverage, expected.cobertura, rtol=1e-12, atol=1e-12, equal_nan=True)
            registros.append({'anio': year, 'resultado': variable, 'cohortes': len(target), 'diferencia_max_media': float((mean-target[variable]).abs().max()), 'diferencia_max_receptores': int((calculated.receptores-expected.n_observados).abs().max()), 'diferencia_max_donantes': int((calculated.donantes-expected.n_donantes_individuales).abs().max()), 'diferencia_max_cobertura': float((coverage-expected.cobertura).abs().max()), 'pet_exacta': True})
    report = {'verificacion': 'aprobada', 'periodo': [2018, 2025], 'fuente': 'indicadores individuales oficiales de la colección armonizada', 'panel': str(PANEL_2018_2025.relative_to(BASE)), 'comparaciones': registros, 'nota': 'Comprobación algebraica de agregación y soporte. No demuestra independencia condicional ni precisión individual de la imputación.'}
    (Path(__file__).resolve().parents[3] / 'datos/armonizados_2018_2025/diagnosticos/panel_2018_2025').mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f'Verificación aprobada. {OUT}', flush=True)
    return report


if __name__ == '__main__':
    ejecutar()
