"""Datos del dashboard alineados con Hechos_estilizados_2025, sin alterar fuentes."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'data'))
from pathlib import Path
import sys
import json
import hashlib
from itertools import combinations
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
BASE = Path(__file__).resolve().parents[1] / 'data'
sys.path.insert(0, str(BASE))
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import ocupacion_analitica
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS, INDICES as REFERENCIA, INDICADORES as INDICADORES_OFICIALES
INDICES = ['aioe_pct', 'webb_ia_pct', 'llm_pct', 'software_pct', 'robots_pct']

def main():
    reference = REFERENCIA
    idx = pd.read_csv(reference, dtype={'ciuo08': 'string'})
    assert not idx.ciuo08.duplicated().any()
    output = {'metadata': {'indices': ['aioe_pct', 'robots_pct'], 'cortes': [0.5, 0.5],
        'nota': 'Percentiles fijos del catálogo, sin renormalización anual. No cotización no equivale a informalidad oficial.',
        'indices_disponibles': INDICES,
        'cortes_indices': {k: 0.5 for k in INDICES},
        'cobertura_parejas': 'Filtrar ambas puntuaciones no nulas y dividir masa incluida por denominadores_universo. Alto >= 0,5 en percentiles fijos.',
        'fuentes': {str(reference.relative_to(BASE)): hashlib.sha256(reference.read_bytes()).hexdigest()}}, 'anios': {}}
    validations = []
    for year in range(2022, 2026):
        source = MICRODATOS[year]
        output['metadata']['fuentes'][str(source.relative_to(BASE))] = hashlib.sha256(source.read_bytes()).hexdigest()
        d = pd.read_parquet(source, columns=['OCI_geih', 'DSI_geih', 'OFICIO_C8_geih', 'OFICIO2_C8_geih', 'FEX_C', 'P6920_geih', 'INGLABO_geih', 'P1_DEPARTAMENTO', 'P6020'])
        d = d.loc[np.isfinite(d.FEX_C) & d.FEX_C.gt(0) & (d.OCI_geih.eq(1) | d.DSI_geih.eq(1))].copy()
        d['ciuo08'] = ocupacion_analitica(d)
        d['universo'] = np.where(d.OCI_geih.eq(1), 'Ocupados', 'Desocupados')
        # Departamento (código DPTO_CCDGO, igual al de co_departamentos.geojson) y sexo,
        # para el filtro opcional del explorador de cuadrantes. Son campos nuevos,
        # aditivos: no tocan 'cuadrantes'/'ocupaciones'/'ocupaciones_indices' ni las
        # validaciones contra el Anexo A que dependen de esos campos ya existentes.
        d['departamento'] = d.P1_DEPARTAMENTO.astype('Int64')
        d['sexo'] = np.where(d.P6020.eq(1), 'Hombre', 'Mujer')
        d = d.merge(idx[['ciuo08', 'ciuo08_desc'] + INDICES], how='left', on='ciuo08', validate='m:1')
        d['pension_valida'] = np.where(d.OCI_geih.eq(1) & d.P6920_geih.isin([1, 2]), d.FEX_C, 0)
        d['no_cotiza'] = np.where(d.OCI_geih.eq(1) & d.P6920_geih.eq(2), d.FEX_C, 0)
        denominators = d.groupby('universo').agg(n=('FEX_C','size'),poblacion=('FEX_C','sum')).reset_index()
        denominators_detalle = d.groupby(['universo','departamento','sexo'],dropna=False).agg(n=('FEX_C','size'),poblacion=('FEX_C','sum')).reset_index()
        income_valid = d.OCI_geih.eq(1) & np.isfinite(d.INGLABO_geih) & d.INGLABO_geih.gt(0)
        d['masa_ingreso'] = np.where(income_valid, d.FEX_C, 0)
        d['suma_ingreso'] = np.where(income_valid, d.INGLABO_geih * d.FEX_C, 0)
        available = d.loc[d[INDICES].notna().any(axis=1)]
        free = available.groupby(['universo','ciuo08','ciuo08_desc']+INDICES,dropna=False).agg(
            poblacion=('FEX_C','sum'),n=('FEX_C','size'),pension_valida=('pension_valida','sum'),no_cotiza=('no_cotiza','sum'),masa_ingreso=('masa_ingreso','sum'),suma_ingreso=('suma_ingreso','sum')).reset_index()
        # Misma tabla que 'free', con departamento y sexo como dimensiones adicionales
        # para el filtro del explorador de cuadrantes. No sustituye a 'free' (que sigue
        # siendo la fuente de 'ocupaciones_indices' y de las validaciones de abajo).
        free_detalle = available.groupby(['universo','ciuo08','ciuo08_desc','departamento','sexo']+INDICES,dropna=False).agg(
            poblacion=('FEX_C','sum'),n=('FEX_C','size'),pension_valida=('pension_valida','sum'),no_cotiza=('no_cotiza','sum'),masa_ingreso=('masa_ingreso','sum'),suma_ingreso=('suma_ingreso','sum')).reset_index()
        if year == 2025:
            # Uso observado, distinto de los cinco índices internacionales.
            # Se calcula entre ocupados con ruta válida y después se ordenan
            # sus prevalencias ocupacionales una sola vez para 2025.
            official = pd.read_parquet((BASE / 'datos/armonizados_2018_2025/indicadores/indicadores_oficiales_2025.parquet'), columns=['ciuo08','ocupado','uso_ia','FEX_C'])
            official['ciuo08'] = official.ciuo08.astype('string')
            valid = official.ocupado.eq(1) & official.uso_ia.notna() & official.ciuo08.notna() & official.FEX_C.gt(0)
            official = official.loc[valid].copy()
            official['masa_ia'] = official.uso_ia*official.FEX_C
            ia_df = official.groupby('ciuo08').agg(n=('uso_ia','size'),numerador=('masa_ia','sum'),denominador=('FEX_C','sum')).reset_index()
            ia_df['uso_ia_prop'] = (ia_df.numerador/ia_df.denominador).where(ia_df.n.ge(30))
            count = int(ia_df.uso_ia_prop.notna().sum())
            ia_df['uso_ia_pct'] = (ia_df.uso_ia_prop.rank(method='average')-1)/(count-1) if count>1 else np.nan
            free = free.merge(ia_df[['ciuo08','uso_ia_pct','uso_ia_prop']], on='ciuo08', how='left',validate='m:1')
            free_detalle = free_detalle.merge(ia_df[['ciuo08','uso_ia_pct','uso_ia_prop']], on='ciuo08', how='left',validate='m:1')
            output['metadata']['fuentes'][str((BASE / 'datos/armonizados_2018_2025/indicadores/indicadores_oficiales_2025.parquet').relative_to(BASE))] = hashlib.sha256((BASE / 'datos/armonizados_2018_2025/indicadores/indicadores_oficiales_2025.parquet').read_bytes()).hexdigest()
            output['metadata']['uso_ia_2025'] = {'definicion':'Prevalencia ponderada de uso de IA por internet entre ocupados con ruta válida, agrupada por ocupación actual; mínimo 30 respuestas válidas. No identifica lugar de uso.', 'escala_eje':'Posición percentil entre ocupaciones con prevalencia observada en 2025; no es índice internacional ni porcentaje de uso.', 'ocupaciones_observadas':count}
        # Cotejo de las diez parejas y ambos universos con los microdatos.
        for left,right in combinations(INDICES,2):
            pair = free.dropna(subset=[left,right]).copy()
            direct = d.dropna(subset=[left,right]).copy()
            for frame in [pair,direct]:
                frame['q'] = frame[left].ge(.5).astype(int)*2 + frame[right].ge(.5).astype(int)
            for universe in ['Ocupados','Desocupados']:
                a=pair.loc[pair.universo.eq(universe)]
                b=direct.loc[direct.universo.eq(universe)]
                for q in range(4):
                    aa=a.loc[a.q.eq(q)];bb=b.loc[b.q.eq(q)]
                    np.testing.assert_allclose([aa.poblacion.sum(),aa.pension_valida.sum(),aa.no_cotiza.sum()],
                                               [bb.FEX_C.sum(),bb.pension_valida.sum(),bb.no_cotiza.sum()],rtol=1e-12,atol=1e-7)
                    assert aa.n.sum()==len(bb)
                assert np.isclose((100*a.groupby('q').poblacion.sum()/a.poblacion.sum()).sum(),100)
                assert a.no_cotiza.sum() <= a.pension_valida.sum()+1e-7
                total=denominators.set_index('universo').loc[universe,'poblacion']
                assert 0 <= a.poblacion.sum()/total <= 1+1e-12
                validations.append(dict(anio=year,indices=[left,right],universo=universe,
                    n=int(a.n.sum()),poblacion=float(a.poblacion.sum()),
                    cobertura_pct=float(100*a.poblacion.sum()/total),
                    pension_valida=float(a.pension_valida.sum()),no_cotiza=float(a.no_cotiza.sum())))
        valid = d.aioe_pct.notna() & d.robots_pct.notna()
        coverage = []
        for u, g in d.groupby('universo'):
            gvalid = g.loc[valid]
            coverage.append({'universo': u, 'n': len(g), 'n_clasificados': len(gvalid),
                'poblacion': float(g.FEX_C.sum()), 'clasificados': float(gvalid.FEX_C.sum()),
                'cobertura_pct': float(100*gvalid.FEX_C.sum()/g.FEX_C.sum())})
        d = d.loc[valid].copy()
        d['cuadrante'] = np.select([(d.aioe_pct >= .5) & (d.robots_pct < .5), (d.aioe_pct >= .5) & (d.robots_pct >= .5),
            (d.aioe_pct < .5) & (d.robots_pct < .5)], ['I', 'II', 'III'], default='IV')
        d['pension_valida'] = np.where(d.OCI_geih.eq(1) & d.P6920_geih.isin([1, 2]), d.FEX_C, 0)
        d['no_cotiza'] = np.where(d.OCI_geih.eq(1) & d.P6920_geih.eq(2), d.FEX_C, 0)
        occ = d.groupby(['universo', 'cuadrante', 'ciuo08', 'ciuo08_desc', 'aioe_pct', 'robots_pct']).agg(
            poblacion=('FEX_C', 'sum'), n=('FEX_C', 'size'), pension_valida=('pension_valida', 'sum'), no_cotiza=('no_cotiza', 'sum')).reset_index()
        occ['participacion'] = 100*occ.poblacion/occ.groupby('universo').poblacion.transform('sum')
        rows = []
        for q in ['I', 'II', 'III', 'IV']:
            g = occ.loc[occ.cuadrante.eq(q)]
            o = g.loc[g.universo.eq('Ocupados')]; un = g.loc[g.universo.eq('Desocupados')]
            rows.append({'cuadrante': q, 'ocupados_pct': float(o.participacion.sum()), 'desocupados_pct': float(un.participacion.sum()),
                'ocupados': float(o.poblacion.sum()), 'desocupados': float(un.poblacion.sum()),
                'no_cotizantes_pct': float(100*o.no_cotiza.sum()/occ.no_cotiza.sum()),
                'tasa_no_cotizacion': float(100*o.no_cotiza.sum()/o.pension_valida.sum()),
                'tasa_desempleo': float(100*un.poblacion.sum()/g.poblacion.sum())})
        for k in ['ocupados_pct', 'desocupados_pct', 'no_cotizantes_pct']:
            assert np.isclose(sum(r[k] for r in rows), 100)
        if year == 2025:
            expected = pd.read_csv((BASE / 'regresiones/resultados/hechos_2025/cuadrantes_2025.csv')).iloc[[1, 3, 0, 2]]
            for key, col in [('ocupados_pct','porcentaje_ocupados'),('desocupados_pct','porcentaje_desocupados'),
                ('tasa_no_cotizacion','no_cotizacion_pct'),('tasa_desempleo','tasa_desempleo_pct'),('no_cotizantes_pct','participacion_no_cotizantes_pct')]:
                np.testing.assert_allclose([r[key] for r in rows], expected[col], atol=1e-9, rtol=1e-10)
        output['anios'][str(year)] = {'cobertura': coverage, 'cuadrantes': rows, 'ocupaciones': occ.to_dict('records'),
            'denominadores_universo': denominators.to_dict('records'),
            'ocupaciones_indices': free.astype(object).where(pd.notna(free),None).to_dict('records'),
            'denominadores_universo_detalle': denominators_detalle.astype(object).where(pd.notna(denominators_detalle),None).to_dict('records'),
            'ocupaciones_indices_detalle': free_detalle.astype(object).where(pd.notna(free_detalle),None).to_dict('records')}
    target = (BASE / 'datos/publicacion/dashboard/cuadrantes_anexo.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, allow_nan=False), encoding='utf-8')
    ((BASE / 'datos/publicacion/dashboard/validacion_parejas_indices.json')).write_text(json.dumps(validations,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf-8')
    print('Generados cuatro años. Cinco series de 2025 verificadas contra el Anexo A.')

if __name__ == '__main__':
    main()
