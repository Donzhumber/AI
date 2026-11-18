"""Genera evidencia de referencia fija, cobertura individual y exposición por cohorte."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[4]))
from pathlib import Path
import json
import numpy as np
import pandas as pd
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import *

BASE=ROOT.parents[1]

def main():
    ref=cargar_indices()
    ref.to_csv(ROOT/'indices_normalizados_referencia.csv',index=False)
    meta=metadatos()
    meta['metodo_correspondencia']=ref.metodo_isco.value_counts().to_dict()
    meta['fuentes_primarias']={
        'llm':'https://github.com/openai/GPTs-are-GPTs/blob/main/README.md',
        'geih_no_ocupados2022':'https://microdatos.dane.gov.co/index.php/catalog/771/data-dictionary/F58'}
    meta['reconstruccion_origen']='Catálogo recibido conservado; archivos originales de crosswalk y puntuaciones no presentes en este checkout. Se verifica asignación/normalización, no se afirma réplica independiente del crosswalk original.'
    (ROOT/'metadatos_indices.json').write_text(json.dumps(meta,indent=2,ensure_ascii=False))
    ref[COLUMNAS].describe().T.rename_axis('indice').reset_index().to_csv(ROOT/'distribucion_indices_referencia.csv',index=False)
    ref[[f'{k}_pct' for k in INDICADORES]].corr().rename_axis('indice').reset_index().to_csv(ROOT/'correlaciones_indices_referencia.csv',index=False)
    ref[[f'{k}_pct' for k in INDICADORES]].dropna().corr().rename_axis('indice').reset_index().to_csv(ROOT/'correlaciones_indices_muestra_comun.csv',index=False)
    coverage=[]; assignments=[]; cells=[]; differences=[]; sensitivity=[]
    cols=['OFICIO_C8_geih','OFICIO1_C8_geih','OFICIO2_C8_geih','P6040','P6020','P1_DEPARTAMENTO','FEX_C','OCI_geih','DSI_geih','P6920_geih','INGLABO_geih','id_donante_geih','exp_aioe','exp_webb_ia','exp_gpt4_beta']
    for year in range(2022,2026):
        d=pd.read_parquet(BASE/f'datos/imputados/ecv_geih_imputada_{year}.parquet',columns=cols)
        d['ciuo08']=ocupacion_analitica(d)
        d=agregar_indices(d,'ciuo08')
        pet=d.P6040.ge(15)&d.FEX_C.gt(0)&np.isfinite(d.FEX_C)
        oc=pet & d.OCI_geih.eq(1); ds=pet&d.DSI_geih.eq(1)
        groups={'PET':pet,'ocupados':oc,'desocupados':ds,'fuerza_laboral':oc|ds,
            'no_cotizacion_respuesta12':oc&d.P6920_geih.isin([1,2]),'ingreso_positivo':oc&d.INGLABO_geih.gt(0)}
        current=codigo_ocupacion(d.OFICIO_C8_geih)
        prev=codigo_ocupacion(d.OFICIO2_C8_geih)
        for name,mask in groups.items():
            sub=d.loc[mask]; total=sub.FEX_C.sum()
            for k in [*INDICADORES,'envolvente','comun_cinco']:
                valid=sub[[f'{x}_pct' for x in INDICADORES]].notna().all(axis=1) if k=='comun_cinco' else sub[f'{k}_pct'].notna()
                coverage.append(dict(anio=year,universo=name,indice=k,n_total=len(sub),n_con_indice=int(valid.sum()),cobertura_pct=100*valid.mean(),cobertura_ponderada_pct=100*sub.loc[valid,'FEX_C'].sum()/total))
            assignments.append(dict(anio=year,universo=name,n=len(sub),ocupacion_actual=int((mask&current.notna()).sum()),solo_ocupacion_anterior=int((mask&current.isna()&prev.notna()).sum()),sin_ocupacion=int((mask&d.ciuo08.isna()).sum())))
        # Compare previous vs sought occupation only for unemployment, fixed scales.
        buscada=agregar_indices(pd.DataFrame({'ciuo08':ocupacion_analitica(d,'buscada')}),'ciuo08')
        for k in INDICADORES:
            actual=d[f'{k}_pct']; alt=buscada[f'{k}_pct']; both=ds&actual.notna()&alt.notna()
            sensitivity.append(dict(anio=year,indice=k,n_desocupados=int(ds.sum()),n_anterior=int((ds&actual.notna()).sum()),n_buscada=int((ds&alt.notna()).sum()),n_ambas=int(both.sum()),n_exposicion_distinta=int((both&~np.isclose(actual,alt,equal_nan=True)).sum())))
        # Raw micro exposure was assigned to current occupation only; assess that operation separately.
        lookup=ref.set_index('ciuo08')
        for raw,col in [('AIOE','exp_aioe'),('ai_score','exp_webb_ia'),('dv_rating_beta','exp_gpt4_beta')]:
            expected=current.map(lookup[raw]).astype(float); actual=pd.to_numeric(d[col],errors='coerce')
            mismatch=~np.isclose(expected,actual,equal_nan=True,atol=1e-10,rtol=1e-9)
            differences.append(dict(anio=year,indice=raw,filas=len(d),discrepancias_vs_ocupacion_actual=int(mismatch.sum())))
        p=d.loc[pet].copy(); born=year-p.P6040
        p['generacion']=np.select([born.le(1964),born.le(1974),born.le(1984),born.le(1994)],[1,2,3,4],default=5)
        p['id_cohorte']=p.P1_DEPARTAMENTO.astype(int).astype(str)+'_'+p.P6020.astype(int).astype(str)+'_'+p.generacion.astype(str)
        # Cohort exposure uses current employed occupations, fixed2022 when used as baseline.
        for ident,g in p.groupby('id_cohorte'):
            occupied=g.OCI_geih.eq(1); mass=g.loc[occupied,'FEX_C'].sum()
            row=dict(anio=year,id_cohorte=ident,n_pet=len(g),n_ocupados=int(occupied.sum()))
            for k in COLUMNAS:
                v=occupied&g[k].notna(); w=g.loc[v,'FEX_C']
                row[k]=float(np.average(g.loc[v,k],weights=w)) if len(w) else np.nan
                if k.endswith('_pct'):
                    row[k+'_n']=int(v.sum());row[k+'_cobertura']=float(w.sum()/mass) if mass else np.nan
            cells.append(row)
    pd.DataFrame(sensitivity).to_csv(ROOT/'sensibilidad_ocupacion_desempleo.csv',index=False)
    pd.DataFrame(coverage).to_csv(ROOT/'cobertura_indices_micro.csv',index=False)
    pd.DataFrame(assignments).to_csv(ROOT/'asignacion_ocupacion_micro.csv',index=False)
    pd.DataFrame(differences).to_csv(ROOT/'verificacion_indices_imputados.csv',index=False)
    pd.DataFrame(cells).to_csv(ROOT/'exposicion_cohortes_2022_2025.csv',index=False)
    assert ref.ciuo08.is_unique
    assert ref[COLUMNAS].stack().between(0,1).all()
    assert pd.DataFrame(cells).groupby('id_cohorte').size().eq(4).all()
    # Reordered/subset recipients cannot change reference-normalized values.
    test=pd.DataFrame({'codigo':[ref.ciuo08.iloc[30],ref.ciuo08.iloc[10],None,ref.ciuo08.iloc[30]]})
    out=agregar_indices(test,'codigo')
    assert out.loc[0,COLUMNAS].equals(out.loc[3,COLUMNAS])
    assert out.loc[2,COLUMNAS].isna().all()
    print(json.dumps({'ocupaciones':len(ref),'cohortes':len(cells)//4,'cobertura_filas':len(coverage),'verificaciones':'aprobadas'},ensure_ascii=False))

if __name__=='__main__':main()
