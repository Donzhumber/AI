"""Certifica anuales y construye paneles desde una sola rama por año.

No modifica fuentes ni modelos. Las bases completas se exponen mediante enlaces
relativos; los insumos de agregación se materializan por columna con NA explícito.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from pathlib import Path
import hashlib
import json
import os
import sys
import subprocess
import importlib.util
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = (Path(__file__).resolve().parents[5])
sys.path.insert(0, str(ROOT))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import (
    CARPETA, BASE, MICRODATOS, FUENTES_GEIH, FUENTES_ECV, IPC, PANEL_TIC_DTA)
from regresiones.preparacion.datos.armonizados_2018_2025.indicadores import tic_combinado, uso_ia_validado
from regresiones.validacion.correcciones.depurar_panel import depurar, IPM
from regresiones.validacion.correcciones.educacion import COLUMNAS_EDUCACION_ECV
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import cargar_indices, codigo_ocupacion, COLUMNAS

WORK = (Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/construccion')
PANELES = (Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/paneles')
REQUIRED = list(dict.fromkeys([
    'P6040','P1_DEPARTAMENTO','P6020','FEX_C','CLASE','P6051',
    'CANT_PERSONAS_HOGAR','P8587','OCI_geih','DSI_geih','P6920_geih',
    'P6800_geih','P6430_geih','OFICIO_C8_geih','inglabo_real_geih',
    'PERCAPITA','I_UGASTO','ingpcug_pm_real_geih','pobre_pm_geih',
    'ipm','pobre','P1075','P1910','P1911','P1912','P1084','P1082',
    'P6090','P5095','id_donante_geih'] + IPM + list(COLUMNAS_EDUCACION_ECV)))


def sha(p):
    digest=hashlib.sha256()
    with open(p,'rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def preparar():
    folder=(Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/construccion/datos/imputados');folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    for year,path in MICRODATOS.items():
        for source in [path,FUENTES_GEIH[year],FUENTES_ECV[year]]:
            if not source.exists():raise FileNotFoundError(source)
        schema=set(pq.read_schema(path).names)
        present=[c for c in REQUIRED if c in schema]
        missing=sorted(set(REQUIRED)-schema)
        d=pd.read_parquet(path,columns=present)
        for c in missing:d[c]=np.nan
        if not d.id_donante_geih.notna().all():raise ValueError(f'Donante ausente {year}')
        d[REQUIRED].to_parquet(folder/f'ecv_geih_imputada_{year}.parquet',index=False,compression='zstd')
        rows.append({'anio':year,'archivo':str(path.relative_to(BASE)),
          'destino_real':str(path.resolve().relative_to(BASE)),'sha256':sha(path),
          'filas':len(d),'columnas_originales':len(schema),'columnas_panel_disponibles':len(present),
          'columnas_panel_no_disponibles':missing,
          'fuente_geih':str(FUENTES_GEIH[year].relative_to(BASE)),
          'sha256_fuente_geih':sha(FUENTES_GEIH[year]),
          'fuente_ecv':str(FUENTES_ECV[year].relative_to(BASE)),
          'sha256_fuente_ecv':sha(FUENTES_ECV[year])})
        print(f'{year}: fuente certificada {len(d):,}',flush=True)
    return rows


def basales():
    path=(Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/microdatos/ecv_geih_imputada_2022.parquet')
    cols=['P6040','P1_DEPARTAMENTO','P6020','FEX_C','OCI_geih','OFICIO_C8_geih']
    d=pd.read_parquet(path,columns=cols)
    d=d.loc[d.P6040.ge(15)&d.OCI_geih.eq(1)&np.isfinite(d.FEX_C)&d.FEX_C.gt(0)].copy()
    table=cargar_indices().set_index('ciuo08')
    codes=codigo_ocupacion(d.OFICIO_C8_geih)
    for c in COLUMNAS:d[c]=codes.map(table[c]).astype(float)
    common=['aioe_pct','webb_ia_pct','llm_pct','software_pct','robots_pct']
    d=d.loc[d[common].notna().all(axis=1)].copy()
    born=2022-d.P6040
    gen=np.select([born.le(1964),born.le(1974),born.le(1984),born.le(1994)],[1,2,3,4],default=5)
    d['id_cohorte']=d.P1_DEPARTAMENTO.astype(int).astype(str)+'_'+d.P6020.astype(int).astype(str)+'_'+pd.Series(gen,index=d.index).astype(str)
    d['dpto']=d.P1_DEPARTAMENTO
    folder=(Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/construccion/DiD_estimaciones');folder.mkdir(parents=True,exist_ok=True)
    result={}
    for level,key in [('cohortes','id_cohorte'),('departamental','dpto')]:
        rows=[]
        for value,g in d.groupby(key,sort=True):
            r={key:value,'n_ocupados':len(g),'suma_pesos':float(g.FEX_C.sum())}
            r.update({c:float(np.average(g[c],weights=g.FEX_C)) for c in COLUMNAS})
            rows.append(r)
        t=pd.DataFrame(rows)
        path=folder/f'exposicion_{level}_indices_2022.csv'
        t.to_csv(path,index=False)
        # Contrast against the published aggregate, never rely on it as input.
        old=pd.read_csv((Path(__file__).resolve().parents[5] / 'regresiones/modelos')/path.name).set_index(key)
        aligned=t.set_index(key).reindex(old.index)
        np.testing.assert_allclose(aligned[COLUMNAS],old[COLUMNAS],rtol=1e-12,atol=1e-12,equal_nan=True)
        result[level]=t
    return result


def agregar_tic(panel):
    rows=[]
    for year,path in MICRODATOS.items():
        cols=['P6040','P1_DEPARTAMENTO','P6020','FEX_C','P1910','P1911','P1075']
        if year==2025:cols+=['P1084']+[f'P1083S{i}' for i in range(1,22)]
        d=pd.read_parquet(path,columns=cols)
        d=d.loc[d.P6040.ge(15)&np.isfinite(d.FEX_C)&d.FEX_C.gt(0)].copy()
        born=year-d.P6040
        gen=np.select([born.le(1964),born.le(1974),born.le(1984),born.le(1994)],[1,2,3,4],default=5)
        d['id_cohorte']=d.P1_DEPARTAMENTO.astype(int).astype(str)+'_'+d.P6020.astype(int).astype(str)+'_'+pd.Series(gen,index=d.index).astype(str)
        d['prop_H_tic']=tic_combinado(d)
        valid=d.P1910.isin(range(1,6))&d.P1911.isin(range(1,6))
        computer=d.P1910.isin(range(1,5))|d.P1911.isin(range(1,5))
        d['prop_uso_computador']=computer.astype(float).where(valid)
        d['prop_uso_ia']=uso_ia_validado(d)[0] if year==2025 else np.nan
        for key,g in d.groupby('id_cohorte',sort=True):
            row={'id_cohorte':key,'anio':year}
            for name in ['prop_H_tic','prop_uso_computador','prop_uso_ia']:
                ok=g[name].notna()
                row[name]=float(np.average(g.loc[ok,name],weights=g.loc[ok,'FEX_C'])) if ok.any() else np.nan
            rows.append(row)
    return panel.merge(pd.DataFrame(rows),on=['id_cohorte','anio'],validate='one_to_one')


def exportar_tic(panel):
    rename={'tasa_desempleo':'y_des','prop_no_cotiza_respuesta12':'y_inf','log_sal_real_medio':'y_sal',
      'prop_uso_internet':'x_int','prop_uso_computador':'x_comp','prop_H_tic':'x_tic',
      'edad_media':'c_edad','prop_rural':'c_rural','prop_edu_universitaria':'c_edu',
      'tam_hogar_medio':'c_hogar','prop_jefes':'c_jefe'}
    t=panel.sort_values(['id_cohorte','anio']).copy()
    t['coh']=pd.factorize(t.id_cohorte,sort=True)[0]+1
    t=t[['coh','id_cohorte','anio']+list(rename)].rename(columns=rename)
    t.to_stata(PANEL_TIC_DTA,write_index=False,version=118)


def main():
    PANELES.mkdir(exist_ok=True)
    sources=preparar();expos=basales()
    stage=(Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/construccion/paneles')
    panel=depurar(base=WORK,datos=(Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/construccion/datos'),out=stage,years=range(2018,2026),ipc=IPC)
    panel=agregar_tic(panel)
    for level,key,suffix in [('cohortes','id_cohorte','c'),('departamental','departamento','d')]:
        t=expos[level].set_index('id_cohorte' if suffix=='c' else 'dpto')
        for c in COLUMNAS:
            if c.startswith('envolvente'):continue
            col=f'{c}_{suffix}'
            expected=panel[key].map(t[c])
            if col in panel:np.testing.assert_allclose(panel[col],expected,rtol=1e-12,atol=1e-12,equal_nan=True)
            panel[col]=expected
    panel=panel.sort_values(['id_cohorte','anio']).reset_index(drop=True)
    assert len(panel)==2640 and panel.id_cohorte.nunique()==330
    assert not panel.duplicated(['id_cohorte','anio']).any()
    for first in [2018,2021,2022]:
        out=panel.loc[panel.anio.ge(first)].copy()
        out.to_parquet(PANELES/f'panel_cohortes_{first}_2025.parquet',index=False,compression='zstd')
        out.to_stata(PANELES/f'panel_cohortes_{first}_2025.dta',write_index=False,version=118)
    # The closed2007 variant is valid as a modern2022 start, not as a2018closed cohort.
    closed=pd.read_parquet(stage/'panel_cohortes_nacimiento_hasta_2007.parquet')
    closed=closed.loc[closed.anio.ge(2022)].copy()
    closed.to_parquet((Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/paneles/panel_cohortes_nacimiento_hasta_2007.parquet'),index=False,compression='zstd')
    closed.to_stata((Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/paneles/panel_cohortes_nacimiento_hasta_2007.dta'),write_index=False,version=118)
    exportar_tic(panel)
    comparisons={}
    oldmain=pd.read_parquet((Path(__file__).resolve().parents[5] / 'datos/imputados/panel/panel_cohortes_2021_2025.parquet')).set_index(['id_cohorte','anio'])
    newmain=panel.loc[panel.anio.ge(2021)].set_index(['id_cohorte','anio']).reindex(oldmain.index)
    for c in ['tasa_desempleo','prop_no_cotiza_respuesta12','log_sal_real_medio','aioe_pct_c','aioe_pct_d']:
        delta=(newmain[c]-oldmain[c]).abs()
        comparisons[c]={'max_abs':float(delta.max()),'distintos_mas_1e_10':int(delta.gt(1e-10).sum())}
        np.testing.assert_allclose(newmain[c],oldmain[c],rtol=1e-12,atol=1e-12,equal_nan=True)
    result={'periodo':[2018,2025],'filas':len(panel),'columnas':len(panel.columns),'cohortes':330,
      'version2021':'Marco2018, ocupaciónCIUO08 y educaciónP3042; pool completo234054, actividad estructural GEIH antes15. Pobreza monetaria e ingreso percapita transferidos no observados2021.',
      'panel_cerrado':'Solo2022–25 hasta nacimiento2007; no se etiqueta como cerrado2018–25',
      'indices':'Catálogo fijo, sin renormalización anual; basales2022 sobre cobertura común de cinco',
      'catalogo':{'fuente':str(((Path(__file__).resolve().parents[5] / 'datos/exposicion_ia/ciuo08_exposicion_ia_scores.csv')).relative_to(BASE)),'sha256':sha((Path(__file__).resolve().parents[5] / 'datos/exposicion_ia/ciuo08_exposicion_ia_scores.csv'))},
      'scripts_sha256':{str(p.relative_to(BASE)):sha(p) for p in list(((Path(__file__).resolve().parents[5] / 'regresiones/preparacion/datos/armonizados_2018_2025/scripts')).glob('*.py'))+[(Path(__file__).resolve().parents[5] / 'regresiones/preparacion/datos/armonizados_2018_2025/rutas.py'),(Path(__file__).resolve().parents[5] / 'regresiones/preparacion/datos/armonizados_2018_2025/indicadores.py')]},
      'comparacion_rama_principal':comparisons,'fuentes':sources,
      'productos':{p.name:{'sha256':sha(p),'bytes':p.stat().st_size} for p in PANELES.glob('*') if p.is_file()}}
    ((Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/diagnosticos/manifest_coleccion.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ['fuentes','productos']},ensure_ascii=False,indent=2),flush=True)
    for script in ['construir_indicadores.py','documentar_coleccion.py','verificar_coleccion.py','verificar_matching_2021.py']:
        subprocess.run([sys.executable,str((Path(__file__).resolve().parents[5] / 'regresiones/preparacion/datos/armonizados_2018_2025/scripts')/script)],check=True,cwd=BASE)

if __name__=='__main__':main()
