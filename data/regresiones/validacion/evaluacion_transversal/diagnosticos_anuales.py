"""Diagnósticos anuales sobre bases existentes; nunca ejecuta ni altera el matching."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import argparse
import json
import os
import sys

BASE = (Path(__file__).resolve().parents[3])
OUT = (Path(__file__).resolve().parents[3] / 'regresiones/validacion/evaluacion_transversal/salidas')
os.environ.setdefault('MPLCONFIGDIR', '/tmp/anexo_evaluacion_matplotlib')
sys.path.insert(0, str(BASE))
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from regresiones.validacion.correcciones.educacion import armonizar_educacion_ecv, COLUMNAS_EDUCACION_ECV, ESCOLARIDAD_GEIH
from regresiones.validacion.correcciones.depurar_panel import IPC, ocupacion_ciuo_valida


def guardar(nombre, registros):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{nombre}.json').write_text(json.dumps(registros, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def leer(path, columnas):
    disponibles = pq.read_schema(path).names
    return pd.read_parquet(path, columns=[c for c in dict.fromkeys(columnas) if c in disponibles])


def distribucion(x, w):
    ok = x.notna() & np.isfinite(w) & w.gt(0)
    if not ok.any():
        raise ValueError('Distribución sin observaciones válidas')
    f = w[ok].groupby(x[ok], observed=True).sum()
    return f / f.sum()


def covariables(df, geih):
    edad = df.P6040
    jefe = df['P6050' if geih else 'P6051']
    return {
        'Zona': df.CLASE,
        'Sexo': df['P3271' if geih else 'P6020'],
        'Tramos de edad': pd.cut(edad, [-np.inf, 18, 30, 45, 60, np.inf], labels=False),
        'Educación': df.P3042.map(ESCOLARIDAD_GEIH) if geih else armonizar_educacion_ecv(df),
        'Jefatura': jefe.eq(1).astype(float).where(jefe.notna()),
        'Población de 15 años o más': edad.ge(15).astype(float).where(edad.notna()),
    }


def coherencia(df, year):
    pet, trabaja, ocupado = df.P6040.ge(15), df.P6240.eq(1), df.OCI_geih.eq(1)
    pares = df.loc[df.PERCAPITA.gt(0), ['ingpcug_pm_geih', 'PERCAPITA']].dropna() if 'PERCAPITA' in df else pd.DataFrame()
    r = pares.corr().iloc[0, 1] if len(pares) > 1 else np.nan
    return dict(anio=year, n_integrados=len(df), n_pet=int(pet.sum()),
                sensibilidad_actividad_pct=float(ocupado[pet & trabaja].mean()*100),
                acuerdo_actividad_pct=float((ocupado[pet] == trabaja[pet]).mean()*100),
                menores_ingreso_positivo=int((df.P6040.lt(15) & df.INGLABO_geih.gt(0)).sum()),
                menores_ocupados=int((df.P6040.lt(15) & ocupado).sum()),
                desocupados_ingreso_positivo=int((df.DSI_geih.eq(1) & df.INGLABO_geih.gt(0)).sum()),
                ocupados_codigo_invalido=int((ocupado & ~ocupacion_ciuo_valida(df.OFICIO_C8_geih)).sum()),
                correlacion_ingreso_percapita=float(r) if np.isfinite(r) else None,
                n_pares_ingreso=len(pares), ponderacion='Sin factores de expansión, igual que el diagnóstico original')


def ejecutar(years):
    coherencias, afinidades, resumen, insumos = [], [], [], []
    fig, axes = plt.subplots(2, 2, figsize=(11, 7), squeeze=False)
    gcols = ['CLASE', 'P3271', 'P6040', 'P3042', 'P6050', 'FEX_C18', 'OCI', 'INGLABO']
    ecols = ['CLASE', 'P6020', 'P6051', 'FEX_C'] + COLUMNAS_EDUCACION_ECV
    icols = ecols + ['P6240', 'OCI_geih', 'DSI_geih', 'INGLABO_geih', 'OFICIO_C8_geih', 'PERCAPITA', 'ingpcug_pm_geih', 'inglabo_real_geih']
    for ax, year in zip(axes.flat, years):
        paths = [BASE/f'datos/GEIH/{year}/total_son_full_{year}.parquet', BASE/f'datos/ECV/{year}/total_ecv_{year}.parquet', BASE/f'datos/imputados/ecv_geih_imputada_{year}.parquet']
        g, e, d = [leer(p, cs) for p, cs in zip(paths, [gcols, ecols, icols])]
        for p in paths:
            st = p.stat()
            insumos.append(dict(anio=year, archivo=str(p.relative_to(BASE)), bytes=st.st_size, mtime_ns=st.st_mtime_ns))
        coherencias.append(coherencia(d, year))
        cg = covariables(g, True)
        for dominio, receptor in [('ECV original', e), ('ECV integrada', d)]:
            for nombre, x in covariables(receptor, False).items():
                fg, fe = distribucion(cg[nombre], g.FEX_C18).align(distribucion(x, receptor.FEX_C), join='outer', fill_value=0)
                rho = float(np.sqrt(fg*fe).sum())
                afinidades.append(dict(anio=year, comparacion=dominio, variable=nombre, afinidad=rho))
        for fuente, df, ocupado, ingreso, peso, color in [
            ('GEIH', g, 'OCI', 'INGLABO', 'FEX_C18', '#1f77b4'),
            ('ECV integrada', d, 'OCI_geih', 'inglabo_real_geih', 'FEX_C', '#d62728')]:
            x = df[ingreso] * (IPC[2025]/IPC[year] if fuente == 'GEIH' else 1)
            ok = df[ocupado].eq(1) & x.gt(0) & np.isfinite(x) & df[peso].gt(0) & np.isfinite(df[peso])
            sns.kdeplot(x=np.log(x[ok]), weights=df.loc[ok, peso], ax=ax, label=fuente, color=color, lw=1.7)
            resumen.append(dict(anio=year, fuente=fuente, n_ingresos_positivos=int(ok.sum()), media_log_ponderada=float(np.average(np.log(x[ok]), weights=df.loc[ok,peso])), factor_ipc=IPC[2025]/IPC[year]))
        ax.set(title=str(year), xlabel='Logaritmo del ingreso laboral positivo', ylabel='Densidad')
        ax.legend(fontsize=8)
        print(json.dumps(coherencias[-1], ensure_ascii=False), flush=True)
    for ax in list(axes.flat)[len(years):]:
        ax.set_visible(False)
    fig.suptitle('Ingresos observados en GEIH e imputados en ECV\nPrecios de octubre de 2025')
    fig.tight_layout()
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig((Path(__file__).resolve().parents[3] / 'regresiones/validacion/evaluacion_transversal/salidas/densidad_ingresos_2022_2025.png'), dpi=170)
    plt.close(fig)
    guardar('coherencia_anual', coherencias)
    guardar('hellinger_anual', afinidades)
    guardar('densidad_resumen', resumen)
    guardar('insumos_diagnosticos', insumos)
    if 2023 in years:
        original = json.loads(((Path(__file__).resolve().parents[3] / 'datos/imputados/diagnosticos/publicacion/consistencia.json')).read_text())
        c = next(c for c in coherencias if c['anio']==2023)
        valores = [f"{c['sensibilidad_actividad_pct']:.2f}%", f"{c['acuerdo_actividad_pct']:.2f}%"] + [f"{c[k]} registros" for k in ['menores_ingreso_positivo','menores_ocupados','desocupados_ingreso_positivo','ocupados_codigo_invalido']] + [f"{c['correlacion_ingreso_percapita']:.3f} (Pearson)"]
        checks = [dict(diagnostico='coherencia', prueba=o['Prueba de Calibración'], original=o['Métrica Observada'], recalculado=v, coincide=o['Métrica Observada']==v) for o,v in zip(original,valores)]
        original_h = json.loads(((Path(__file__).resolve().parents[3] / 'datos/imputados/diagnosticos/publicacion/hellinger.json')).read_text())
        actual_h = [h for h in afinidades if h['anio']==2023 and h['comparacion']=='ECV original']
        checks += [dict(diagnostico='Hellinger ECV original', prueba=o['Variable Común'], original=o['Afinidad de Hellinger (ρ)'], recalculado=round(h['afinidad'],4), coincide=o['Afinidad de Hellinger (ρ)']==round(h['afinidad'],4)) for o,h in zip(original_h,actual_h)]
        guardar('reproduccion_2023', checks)
        if not all(c['coincide'] for c in checks):
            raise AssertionError('Hay diferencias respecto de la publicación original de 2023; revisar reproduccion_2023.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--years', nargs='+', type=int, choices=range(2022,2026), default=[2022,2023,2024,2025])
    args = parser.parse_args()
    ejecutar(sorted(set(args.years)))
