"""Hechos descriptivos 2025; usa percentiles existentes, nunca los recalcula."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import sys, json, hashlib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = (Path(__file__).resolve().parents[3] / 'regresiones/resultados/hechos_2025')
BASE = (Path(__file__).resolve().parents[3])
sys.path.insert(0, str(BASE))
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import ocupacion_analitica

QUADRANTS = ['AIOE bajo · robots bajo', 'AIOE alto · robots bajo',
             'AIOE bajo · robots alto', 'AIOE alto · robots alto']

def classify(a, r, ca, cr):
    return np.select([(a < ca) & (r < cr), (a >= ca) & (r < cr),
                      (a < ca) & (r >= cr)], QUADRANTS[:3], default=QUADRANTS[3])

def weighted_median(values, weights):
    ix = np.argsort(values.to_numpy())
    vals, w = values.to_numpy()[ix], weights.to_numpy()[ix]
    return float(vals[np.searchsorted(np.cumsum(w), w.sum() / 2)]) if len(vals) else None

def main():
    source = (Path(__file__).resolve().parents[3] / 'datos/imputados/ecv_geih_imputada_2025.parquet')
    index_source = (Path(__file__).resolve().parents[3] / 'datos/exposicion_ia/indices_normalizados_referencia.csv')
    idx = pd.read_csv(index_source, dtype={'ciuo08':'string'})
    assert not idx.ciuo08.duplicated().any()
    common = idx.dropna(subset=['aioe_pct','robots_pct']).copy()
    ca, cr = common[['aioe_pct','robots_pct']].median()
    d = pd.read_parquet(source, columns=['OCI_geih','DSI_geih','OFICIO_C8_geih',
         'OFICIO2_C8_geih','FEX_C','P6920_geih','INGLABO_geih'])
    d = d.loc[np.isfinite(d.FEX_C) & d.FEX_C.gt(0)].copy()
    d = d.loc[d.OCI_geih.eq(1) | d.DSI_geih.eq(1)].copy()
    d['ciuo08'] = ocupacion_analitica(d)
    d['universo'] = np.where(d.OCI_geih.eq(1),'Ocupados','Desocupados')
    d = d.merge(idx[['ciuo08','ciuo08_desc','aioe_pct','robots_pct']], on='ciuo08',how='left',validate='m:1')
    d['cubierto'] = d[['aioe_pct','robots_pct']].notna().all(axis=1)
    coverage = []
    for u, g in d.groupby('universo'):
        covered = g.loc[g.cubierto]
        coverage.append(dict(universo=u,n_universo=len(g),n_cubierto=len(covered),
            masa_universo=g.FEX_C.sum(),masa_cubierta=covered.FEX_C.sum(),
            cobertura_pct=100*len(covered)/len(g),
            cobertura_ponderada_pct=100*covered.FEX_C.sum()/g.FEX_C.sum()))
    pd.DataFrame(coverage).to_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/hechos_2025/cobertura_2025.csv'),index=False)
    d=d.loc[d.cubierto].copy()
    d['cuadrante']=classify(d.aioe_pct,d.robots_pct,ca,cr)
    rows=[]
    for q in QUADRANTS:
        g=d.loc[d.cuadrante.eq(q)]
        o=g.loc[g.universo.eq('Ocupados')]; un=g.loc[g.universo.eq('Desocupados')]
        pen=o.loc[o.P6920_geih.isin([1,2])]
        income=o.loc[np.isfinite(o.INGLABO_geih)&o.INGLABO_geih.gt(0)]
        rows.append(dict(cuadrante=q,n_ocupados=len(o),n_desocupados=len(un),
            ocupados_ponderados=o.FEX_C.sum(),desocupados_ponderados=un.FEX_C.sum(),
            porcentaje_ocupados=100*o.FEX_C.sum()/d.loc[d.universo.eq('Ocupados'),'FEX_C'].sum(),
            porcentaje_desocupados=100*un.FEX_C.sum()/d.loc[d.universo.eq('Desocupados'),'FEX_C'].sum(),
            tasa_desempleo_pct=100*un.FEX_C.sum()/g.FEX_C.sum(),
            no_cotizacion_pct=100*pen.loc[pen.P6920_geih.eq(2),'FEX_C'].sum()/pen.FEX_C.sum(),
            no_cotizantes_ponderados=pen.loc[pen.P6920_geih.eq(2),'FEX_C'].sum(),
            n_pension_valida=len(pen),masa_pension_valida=pen.FEX_C.sum(),
            n_ingreso_positivo=len(income),masa_ingreso_positivo=income.FEX_C.sum(),
            ingreso_mediano_positivo=weighted_median(income.INGLABO_geih,income.FEX_C)))
    summary=pd.DataFrame(rows)
    summary['participacion_no_cotizantes_pct']=100*summary.no_cotizantes_ponderados/summary.no_cotizantes_ponderados.sum()
    for c in ['porcentaje_ocupados','porcentaje_desocupados','participacion_no_cotizantes_pct']:
        assert np.isclose(summary[c].sum(),100)
    assert np.isclose(summary.ocupados_ponderados.sum()+summary.desocupados_ponderados.sum(),d.FEX_C.sum())
    summary.to_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/hechos_2025/cuadrantes_2025.csv'),index=False)
    occupation=d.groupby(['universo','cuadrante','ciuo08','ciuo08_desc','aioe_pct','robots_pct'],dropna=False).agg(n=('FEX_C','size'),masa=('FEX_C','sum')).reset_index()
    occupation['participacion_universo_pct']=100*occupation.masa/occupation.groupby('universo').masa.transform('sum')
    occupation['participacion_cuadrante_pct']=100*occupation.masa/occupation.groupby(['universo','cuadrante']).masa.transform('sum')
    occupation.to_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/hechos_2025/ocupaciones_2025.csv'),index=False)
    top=[]
    for (u,q),g in occupation.groupby(['universo','cuadrante']):
        g=g.sort_values(['masa','ciuo08'],ascending=[False,True])
        for _,r in g.head(5).iterrows():
            top.append(dict(universo=u,cuadrante=q,ciuo08=r.ciuo08,ocupacion=r.ciuo08_desc,
                            masa=r.masa,participacion_cuadrante_pct=r.participacion_cuadrante_pct))
        remaining=g.iloc[5:]
        top.append(dict(universo=u,cuadrante=q,ciuo08='',ocupacion='Otras ocupaciones',masa=remaining.masa.sum(),participacion_cuadrante_pct=remaining.participacion_cuadrante_pct.sum()))
    top=pd.DataFrame(top)
    assert np.allclose(top.groupby(['universo','cuadrante']).participacion_cuadrante_pct.sum(),100)
    top.to_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/hechos_2025/principales_ocupaciones_2025.csv'),index=False)
    sensitivity=[]
    for cut in [0.4,0.6]:
        labels=classify(d.aioe_pct,d.robots_pct,cut,cut)
        for u,g in d.assign(alternativa=labels).groupby('universo'):
            for q in QUADRANTS:
                sensitivity.append(dict(corte=cut,universo=u,cuadrante=q,porcentaje=100*g.loc[g.alternativa.eq(q),'FEX_C'].sum()/g.FEX_C.sum(),cambio_clasificacion_pct=100*g.loc[g.alternativa.ne(g.cuadrante),'FEX_C'].sum()/g.FEX_C.sum()))
    pd.DataFrame(sensitivity).to_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/hechos_2025/sensibilidad_cortes_2025.csv'),index=False)
    equivalence=None
    if {'aioe_mm','robots_mm'}.issubset(common.columns):
        mm=common[['aioe_mm','robots_mm']].median()
        pct_labels=classify(common.aioe_pct,common.robots_pct,ca,cr)
        mm_labels=classify(common.aioe_mm,common.robots_mm,*mm)
        equivalence=dict(cortes_minmax=mm.to_dict(),ocupaciones=len(common),discrepancias=int(np.sum(pct_labels!=mm_labels)))
        assert equivalence['discrepancias']==0
    # Matplotlib usaba 10 pt para ejes, ticks y leyenda; se elevan a 12 pt.
    fig,axes=plt.subplots(1,2,figsize=(12.5,7),sharex=True,sharey=True)
    palette=dict(zip(QUADRANTS,['#7a9698','#3a8ba4','#d3a264','#9b7aab']))
    # Redondeo por restos mayores para sumar exactamente 100,00 en cada serie visible.
    def display_shares(column):
        values=summary.set_index('cuadrante').loc[QUADRANTS,column].to_numpy()*100
        units=np.floor(values).astype(int)
        order=np.argsort(-(values-units),kind='stable')
        units[order[:10000-units.sum()]]+=1
        assert units.sum()==10000
        return dict(zip(QUADRANTS,units/100))
    red_shares=display_shares('participacion_no_cotizantes_pct')
    for ax,u in zip(axes,['Ocupados','Desocupados']):
        g=occupation.loc[occupation.universo.eq(u)]
        black_shares=display_shares('porcentaje_ocupados' if u=='Ocupados' else 'porcentaje_desocupados')
        ax.scatter(g.robots_pct,g.aioe_pct,s=g.participacion_universo_pct*65,
                   alpha=.55,c=g.cuadrante.map(palette),edgecolor='white',linewidth=.3)
        ax.axvline(cr,color='gray',ls='--',lw=1);ax.axhline(ca,color='gray',ls='--',lw=1)
        for numeral,x,y in [('I',.25,.73),('II',.75,.73),('III',.25,.27),('IV',.75,.27)]:
            ax.text(x,y,numeral,transform=ax.transAxes,ha='center',va='center',
                    fontsize=14,fontweight='bold',color='#183c54',
                    bbox=dict(facecolor='white',alpha=.85,edgecolor='none',pad=3),zorder=10)
        for q,(x,y) in zip(QUADRANTS,[(.02,.03),(.02,.96),(.98,.03),(.98,.96)]):
            share=black_shares[q]
            ax.text(x,y,f'{share:.2f} %'.replace('.',','),transform=ax.transAxes,ha='left' if x<.5 else 'right',va='top' if y>.5 else 'bottom',bbox=dict(facecolor='white',alpha=.85,edgecolor='none'))
            if u=='Ocupados':
                label=f'Informalidad aproximada\n{red_shares[q]:.2f} %'.replace('.',',')
                ax.text(x,y-.065 if y>.5 else y+.065,label,transform=ax.transAxes,
                        ha='left' if x<.5 else 'right',va='top' if y>.5 else 'bottom',
                        fontsize=10,color='#b22222',
                        bbox=dict(facecolor='white',alpha=.9,edgecolor='none',pad=2))
        ax.set(title=u,xlabel='Exposición a robots de Webb · percentil',xlim=(-.02,1.02),ylim=(-.02,1.02))
        ax.grid(alpha=.12)
        ax.xaxis.label.set_size(12)
        ax.tick_params(axis='both',labelsize=12)
    axes[0].set_ylabel('Exposición AIOE · percentil',fontsize=12)
    handles=[axes[1].scatter([],[],s=p*65,color='#247b91',alpha=.45,label=f'{p} %') for p in [1,3,5]]
    fig.legend(handles=handles,title='Participación ponderada de la ocupación dentro de cada panel',
               loc='lower center',bbox_to_anchor=(.5,.035),ncol=3,frameon=False,
               fontsize=12,title_fontsize=12)
    fig.text(.5,.012,'Rojo · Distribución de ocupados que no cotizan a pensión, suma 100 %. No es la medición oficial de informalidad.',
             ha='center',fontsize=10,color='#b22222')
    fig.suptitle('Exposición ocupacional entre ocupados y desocupados con ambos índices · 2025')
    fig.tight_layout(rect=[0,.18,1,.95])
    fig.savefig((Path(__file__).resolve().parents[3] / 'regresiones/resultados/hechos_2025/exposicion_cuadrantes_2025.png'),dpi=180)
    plt.close(fig)
    meta=dict(anio=2025,indicadores=['aioe_pct','robots_pct'],normalizacion='Se leen percentiles existentes sin recalcular rangos',
        cortes=dict(aioe_pct=float(ca),robots_pct=float(cr)),regla='Alto si valor >= mediana no ponderada del catálogo común',
        ocupaciones_catalogo_comun=len(common),ponderacion='FEX_C positivo y finito',
        ocupacion='Actual para ocupados; última para desocupados. Ausentes no se rellenan.',
        ingresos='Mediana ponderada de ingreso laboral positivo, COP de octubre 2025',
        porcentajes_rojos='Distribución entre cuadrantes de ocupados clasificables que no cotizan; denominador total de no cotizantes clasificables',
        redondeo_figura='Restos mayores a dos decimales para que cada distribución visible sume 100,00; CSV conserva precisión completa',
        equivalencia_minmax=equivalence,validaciones='Participaciones suman100, masas concilian, top5+otras suman100, equivalencia de clasificación con medianas minmax',
        fuentes={str(p.relative_to(BASE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,index_source,(Path(__file__).resolve().parents[3] / 'regresiones/preparacion/datos/exposicion_ia/indices_comunes.py')]})
    ((Path(__file__).resolve().parents[3] / 'regresiones/resultados/hechos_2025/metadatos.json')).write_text(json.dumps(meta,ensure_ascii=False,indent=2))
    print(summary.to_string(index=False));print(json.dumps(meta,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
