"""Reproduce diagnósticos sin modificar fuentes ni bases integradas.

Ejecutar con Python desde cualquier directorio. --anios acepta uno o varios años.
Replica el vector y bloqueo de preparar_integracion.py y reutiliza sus módulos
de educación, vecinos y evaluación, sin importar su bloque ejecutable.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import argparse
import sys
import time

import numpy as np
import pandas as pd

BASE = (Path(__file__).resolve().parents[3])
sys.path.insert(0, str(BASE))
from regresiones.validacion.correcciones.educacion import armonizar_educacion_ecv
from regresiones.validacion.correcciones.empates import buscar_vecinos, diagnosticar_empates
from regresiones.validacion.validacion_laboral.validacion import evaluar

EDUCACION_GEIH = {1: 0, 2: 0, 3: 1, 4: 2, 5: 2, 6: 2, 7: 2,
                  8: 3, 9: 3, 10: 4, 11: 4, 12: 4, 13: 4, 99: np.nan}
SALIDAS = (Path(__file__).resolve().parents[3] / 'regresiones/validacion/evaluacion_transversal/salidas')


def preparar(g, e):
    """Orden original, exclusiones, métrica y pools idénticos a producción."""
    for frame, cols in [(g, ['P6040', 'P3271', 'P6050', 'DIRECTORIO', 'SECUENCIA_P']),
                        (e, ['P6040', 'P6020', 'P6051', 'CANT_PERSONAS_HOGAR'])]:
        if frame[cols].isna().any().any():
            raise ValueError('Covariable no educativa ausente')
    gs = g.DPTO.astype(int).astype(str) + '_' + g.CLASE.astype(int).astype(str) + '_' + g.P3271.astype(int).astype(str)
    es = e.P1_DEPARTAMENTO.astype(int).astype(str) + '_' + e.CLASE.astype(int).astype(str) + '_' + e.P6020.astype(int).astype(str)
    gt = g.groupby(['DIRECTORIO', 'SECUENCIA_P']).P6040.transform('count').clip(1, 15)
    gf = np.column_stack([g.P6040 / 100, g.P3042.map(EDUCACION_GEIH) / 4,
                          2 * g.P6050.eq(1), gt / 10, 5 * g.P6040.ge(15), 3 * g.P6240.eq(1)])
    ef = np.column_stack([e.P6040 / 100, armonizar_educacion_ecv(e) / 4,
                          2 * e.P6051.eq(1), e.CANT_PERSONAS_HOGAR.clip(1, 15) / 10,
                          5 * e.P6040.ge(15), 3 * e.P6240.eq(1)])
    matched = np.zeros(len(e), dtype=int)
    fallback = np.zeros(len(e), dtype=bool)
    for s, group in e.groupby(es):
        pos = group.index.to_numpy()
        pool = g.index[gs.eq(s)].to_numpy()
        if not len(pool):
            fallback[pos] = True
            _, zone, sex = s.split('_')
            pool = g.index[g.CLASE.eq(int(zone)) & g.P3271.eq(int(sex))].to_numpy()
        _, matched[pos] = buscar_vecinos(gf, ef, pool, pos)
    return gf, ef, gs, es, matched, fallback


def comprobar(tabla, referencia, year, pruebas):
    """Compara todos los campos, tolerando únicamente redondeo JSON."""
    actual = pd.DataFrame(tabla)
    expected = pd.read_json(referencia)
    expected = expected.loc[expected.anio.eq(year)].reset_index(drop=True)
    actual = actual.reset_index(drop=True)[expected.columns]
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False, atol=1e-8, rtol=1e-9)
    pruebas.append(dict(anio=year, prueba=referencia.name, filas=len(actual), coincide=True))


def ejecutar(anios):
    SALIDAS.mkdir(parents=True, exist_ok=True)
    datos = (Path(__file__).resolve().parents[3] / 'datos')
    diagnosticos = datos / 'imputados/diagnosticos'
    resultados = {k: [] for k in ['fuentes_reproducidas', 'matching_reproducido', 'metricas',
                   'matrices_confusion', 'variables_reservadas', 'rutas_ocupacion', 'empates',
                   'comprobacion_reproduccion']}
    pruebas = resultados['comprobacion_reproduccion']
    for year in anios:
        start = time.monotonic()
        print(f'{year}: lectura y reconstrucción de donantes', flush=True)
        g = pd.read_parquet(datos / f'GEIH/{year}/total_son_full_{year}.parquet').reset_index(drop=True)
        bruto = pd.read_parquet(datos / f'ECV/{year}/total_ecv_{year}.parquet').reset_index(drop=True)
        excluidos = bruto[['CLASE', 'P1_DEPARTAMENTO']].isna().any(axis=1)
        e = bruto.loc[~excluidos].reset_index(drop=True)
        gf, ef, gs, es, matched, fallback = preparar(g, e)
        guardada = pd.read_parquet(datos / f'imputados/ecv_geih_imputada_{year}.parquet',
                                   columns=['id_donante_geih', 'en_fallback'])
        assert np.array_equal(matched, guardada.id_donante_geih.to_numpy()), 'Donantes distintos de base publicada'
        assert np.array_equal(fallback, guardada.en_fallback.to_numpy()), 'Fallback distinto'
        pruebas.append(dict(anio=year, prueba='punteros_y_fallback_parquet', filas=len(e), coincide=True))
        resultados['fuentes_reproducidas'].append(dict(anio=year, geih=len(g), ecv=len(bruto),
            variables_geih=len(g.columns), variables_ecv=len(bruto.columns), receptores=len(e),
            excluidos=int(excluidos.sum()), excluidos_ponderados_pct=100*bruto.loc[excluidos, 'FEX_C'].sum()/bruto.FEX_C.sum(),
            donantes_unicos=len(np.unique(matched))))
        donor = g.iloc[matched]
        w = e.FEX_C.to_numpy(float)
        if not (np.isfinite(w) & (w > 0)).all():
            raise ValueError('Pesos ECV no válidos')
        pet = e.P6040.ge(15).to_numpy()
        oc = donor.OCI.eq(1).to_numpy() & pet
        ds = donor.DSI.eq(1).to_numpy() & pet
        pension = donor.P6920.to_numpy()
        wg = g.FEX_C18.to_numpy(float) / 3
        uses = pd.Series(matched).value_counts()
        matching = dict(anio=year, desempleo_geih=100*wg[g.DSI.eq(1)].sum()/wg[g.OCI.eq(1) | g.DSI.eq(1)].sum(),
            desempleo_imputado=100*w[ds].sum()/w[oc | ds].sum(),
            no_cotizacion=100*w[oc & (pension == 2)].sum()/w[oc & np.isin(pension, [1, 2])].sum(),
            fallback_pct=100*fallback.mean(), fallback_ponderado_pct=100*np.average(fallback, weights=w),
            usos_medios=float(uses.mean()), usos_maximos=int(uses.max()))
        resultados['matching_reproducido'].append(matching)
        publicado = pd.read_json(diagnosticos / 'publicacion/matching.json').set_index('Año').loc[year]
        for key, column, decimals in [('desempleo_imputado', 'Desempleo imputado (%)', 2),
            ('no_cotizacion', 'No cotiza / ocupados con respuesta 1/2 (%)', 2),
            ('fallback_ponderado_pct', '% Fallback (Pob.)', 2), ('usos_medios', 'Réplica Media', 1),
            ('usos_maximos', 'Réplica Max', 0)]:
            assert np.isclose(round(matching[key], decimals), publicado[column]), (year, key)
        pruebas.append(dict(anio=year, prueba='matching_publicado_redondeado', filas=len(e), coincide=True))
        print(f'{year}: validación 6D/5D y empates', flush=True)
        rows, matrices, details, flow = evaluar(year, g, e, gf, ef, gs, es, matched, fallback)
        for name, table in [('metricas', rows), ('matrices_confusion', matrices),
                            ('variables_reservadas', details), ('rutas_ocupacion', [flow])]:
            resultados[name].extend(table)
            comprobar(table, diagnosticos / f'validacion_laboral/{name}.json', year, pruebas)
        ties = diagnosticar_empates(year, g, e, gf, ef, gs, es, matched)
        resultados['empates'].append(ties)
        comprobar([ties], diagnosticos / 'correcciones/empates.json', year, pruebas)
        for name, records in resultados.items():
            pd.DataFrame(records).to_json(SALIDAS / f'{name}.json', orient='records', indent=2, force_ascii=False, double_precision=12)
        print(f'{year}: todas las pruebas coinciden; {time.monotonic()-start:.1f} segundos', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--anios', nargs='+', type=int, choices=[2022, 2023, 2024, 2025], default=[2022, 2023, 2024, 2025])
    ejecutar(parser.parse_args().anios)
