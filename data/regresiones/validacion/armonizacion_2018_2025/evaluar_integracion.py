"""Diagnósticos comparables de la colección oficial; no altera fuentes ni imputaciones."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import json, sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
BASE=(Path(__file__).resolve().parents[3])
sys.path.insert(0,str(BASE))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS,FUENTES_GEIH,FUENTES_ECV,PESOS_GEIH,IPC,CARPETA
from regresiones.validacion.correcciones.educacion import armonizar_educacion_ecv,COLUMNAS_EDUCACION_ECV,ESCOLARIDAD_GEIH
from regresiones.validacion.correcciones.empates import buscar_vecinos
OUT=(Path(__file__).resolve().parents[3] / 'datos/armonizados_2018_2025/diagnosticos/integracion')


def leer(p, cols):
    names=set(pq.read_schema(p).names)
    return pd.read_parquet(p,columns=[c for c in dict.fromkeys(cols) if c in names])


def num(d,c):
    return pd.to_numeric(d[c],errors='coerce').astype(float) if c in d else pd.Series(np.nan,index=d.index)


def educacion_g(g):
    if 'P3042' in g:return num(g,'P3042').map(ESCOLARIDAD_GEIH)
    level,degree=num(g,'P6210'),num(g,'P6220');out=pd.Series(np.nan,index=g.index)
    for mask,v in [(level.isin([1,2]),0),(level.eq(3),1),(level.isin([4,5]),2),(level.eq(6)&degree.eq(3),3),(level.eq(6)&degree.isin([4,5]),4)]:out.loc[mask]=v
    return out


def tasa(x,w,valid):
    valid=valid & np.isfinite(w) & w.gt(0)
    return float(np.average(x[valid],weights=w[valid])) if valid.any() else None


def run():
    fuentes,matching,coherencias,checks=[],[],[],[]
    for year,path in MICRODATOS.items():
        print(year,flush=True)
        g=leer(FUENTES_GEIH[year],['DIRECTORIO','SECUENCIA_P','P6040','P6050','P6240','P3042','P6210','P6220','DPTO','CLASE','P3271','P6020','OCI','DSI','P6920',PESOS_GEIH[year]])
        raw_n=len(g);invalid_head=invalid_activity=0
        if year<=2020:
            good=num(g,'P6050').notna();invalid_head=int((~good).sum());g=g.loc[good].copy()
            structural=num(g,'P6040').lt(num(g,'CLASE').map({1:12,2:10}))
            bad=num(g,'P6240').isna()&~structural;invalid_activity=int(bad.sum());g=g.loc[~bad].copy()
        g=g.reset_index(drop=True)
        d=leer(path,['DIRECTORIO','SECUENCIA_P','ORDEN','P1_DEPARTAMENTO','CLASE','P6020','P6051','CANT_PERSONAS_HOGAR','P6240','OCI_geih','DSI_geih','INGLABO_geih','inglabo_real_geih','P6920_geih','id_donante_geih','en_fallback','FEX_C','OFICIO_C8_geih','ingpcug_pm_geih','ingpcug_pm_hogar_nom','PERCAPITA']+COLUMNAS_EDUCACION_ECV)
        e_original_n=pq.ParquetFile(FUENTES_ECV[year]).metadata.num_rows
        idx=num(d,'id_donante_geih').to_numpy(int);assert idx.min()>=0 and idx.max()<len(g)
        pet=num(d,'P6040').ge(15);oc=num(d,'OCI_geih').eq(1);ds=num(d,'DSI_geih').eq(1);w=num(d,'FEX_C')
        donor=g.iloc[idx].reset_index(drop=True)
        assert np.array_equal((num(donor,'OCI').eq(1)&pet).to_numpy(),oc.to_numpy())
        assert np.array_equal((num(donor,'DSI').eq(1)&pet).to_numpy(),ds.to_numpy())
        uses=pd.Series(idx).value_counts();fall=d.en_fallback.astype(bool)
        fuentes.append(dict(anio=year,geih=raw_n,geih_admisibles=len(g),excluidos_donantes_parentesco=invalid_head,excluidos_donantes_actividad=invalid_activity,ecv=e_original_n,excluidos=e_original_n-len(d),receptores=len(d),donantes_unicos=len(uses)))
        wg=num(g,PESOS_GEIH[year]);gpet=num(g,'P6040').ge(15);goc=num(g,'OCI').eq(1)&gpet;gds=num(g,'DSI').eq(1)&gpet
        matching.append(dict(anio=year,desempleo_geih=100*tasa(gds.astype(float),wg,goc|gds),desempleo_imputado=100*tasa(ds.astype(float),w,oc|ds),no_cotizacion=100*tasa(num(d,'P6920_geih').eq(2).astype(float),w,oc&num(d,'P6920_geih').isin([1,2])),fallback_ponderado_pct=100*tasa(fall.astype(float),w,w.notna()),usos_medios=float(uses.mean()),usos_maximos=int(uses.max())))
        income=num(d,'inglabo_real_geih');works=num(d,'P6240').eq(1)
        percap_col=next((c for c in ['ingpcug_pm_geih','ingpcug_pm_hogar_nom'] if c in d),None)
        pairs=pd.DataFrame() if percap_col is None else d.loc[num(d,'PERCAPITA').gt(0),[percap_col,'PERCAPITA']].dropna()
        corr=pairs.corr().iloc[0,1] if len(pairs)>1 else np.nan
        invalid_code=None
        if 'OFICIO_C8_geih' in d:
            from regresiones.validacion.correcciones.depurar_panel import ocupacion_ciuo_valida
            invalid_code=int((oc&~ocupacion_ciuo_valida(d.OFICIO_C8_geih)).sum())
        coherencias.append(dict(anio=year,n_integrados=len(d),n_pet=int(pet.sum()),sensibilidad_actividad_pct=float(100*oc[pet&works].mean()),acuerdo_actividad_pct=float(100*(oc[pet]==works[pet]).mean()),menores_ingreso_positivo=int((~pet&income.gt(0)).sum()),menores_ocupados=int((~pet&oc).sum()),desocupados_ingreso_positivo=int((ds&income.gt(0)).sum()),ocupados_codigo_invalido=invalid_code,correlacion_ingreso_percapita=float(corr) if np.isfinite(corr) else None,n_pares_ingreso=len(pairs) if percap_col else None))
        # Comprobación independiente de la selección 6D en una muestra reproducible.
        sx='P3271' if 'P3271' in g else 'P6020'
        gs=num(g,'DPTO').astype(int).astype(str)+'_'+num(g,'CLASE').astype(int).astype(str)+'_'+num(g,sx).astype(int).astype(str)
        es=num(d,'P1_DEPARTAMENTO').astype(int).astype(str)+'_'+num(d,'CLASE').astype(int).astype(str)+'_'+num(d,'P6020').astype(int).astype(str)
        size=g.groupby(['DIRECTORIO','SECUENCIA_P'],sort=False).P6040.transform('count').clip(1,15)
        gf=np.column_stack([num(g,'P6040')/100,educacion_g(g)/4,2*num(g,'P6050').eq(1),size/10,5*gpet,3*num(g,'P6240').eq(1)])
        ef=np.column_stack([num(d,'P6040')/100,armonizar_educacion_ecv(d)/4,2*num(d,'P6051').eq(1),num(d,'CANT_PERSONAS_HOGAR').clip(1,15)/10,5*pet,3*works])
        print("faltantes vectores",np.isnan(gf).sum(axis=0).tolist(),np.isnan(ef).sum(axis=0).tolist(),flush=True)
        selected=np.random.default_rng(20261104+year).choice(len(d),size=min(256,len(d)),replace=False);different=0
        for key in es.iloc[selected].unique():
            pos=selected[es.iloc[selected].eq(key).to_numpy()];pool=np.flatnonzero(gs.eq(key))
            if not len(pool):
                _,zone,sex=key.split('_');pool=np.flatnonzero(num(g,'CLASE').eq(int(zone))&num(g,sx).eq(int(sex)))
            _,actual=buscar_vecinos(gf,ef,pool,pos)
            different+=int(np.sum(actual!=idx[pos]))
        checks.append(dict(anio=year,receptores_comprobados=len(selected),diferencias_vecino=different,condicion_laboral_donante_coincide=True))
        OUT.mkdir(parents=True,exist_ok=True)
        for name,rows in [('fuentes_reproducidas',fuentes),('matching_reproducido',matching),('coherencia_anual',coherencias),('comprobacion_vecinos',checks)]:
            (OUT/f'{name}.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2,allow_nan=False))
        if different: raise AssertionError(f'{year}: selección 6D difiere en {different} casos; revisar armonización')
    OUT.mkdir(parents=True,exist_ok=True)
    for name,rows in [('fuentes_reproducidas',fuentes),('matching_reproducido',matching),('coherencia_anual',coherencias),('comprobacion_vecinos',checks)]:
        (OUT/f'{name}.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2,allow_nan=False))
    print('OK ocho años, punteros y muestra de vecinos 6D.')

if __name__=='__main__':run()
