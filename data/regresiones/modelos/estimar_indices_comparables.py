#!/usr/bin/env python3
"""Estimaciones vigentes: índices separados, normalización fija y muestra común.
FWL ponderado conserva todos los controles y el ajuste CR1; inferencia t(G−1).
Los archivos anteriores son la auditoría de la estrategia de envolvente previa.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
import os
for v in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','VECLIB_MAXIMUM_THREADS']:os.environ.setdefault(v,'1')
import sys,json,hashlib,time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats,linalg
ROOT=(Path(__file__).resolve().parents[2] / 'regresiones/modelos'); BASE=(Path(__file__).resolve().parents[2])
sys.path.insert(0,str(BASE))
from regresiones.preparacion.datos.exposicion_ia.indices_comunes import cargar_indices,ocupacion_analitica
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import MICRODATOS, PANEL_2021_2025
IND=[f'{i}_{s}' for s in ['pct','mm'] for i in ['aioe','webb_ia','llm','software','robots','envolvente']]
COMMON=['aioe_pct','webb_ia_pct','llm_pct','software_pct','robots_pct']
CONT=['edad','edad2','mujer','rural','jefe']
PCONT=['edad_media','prop_rural','prop_edu_universitaria']
ROWS=[]; TESTS=[]

def incorporar_indices_panel(panel, dep, coh):
 """Conserva AIOE basal del constructor y verifica que coincide con los microdatos."""
 for ind in IND:
  for suffix,key,reference in [('_d','departamento',dep),('_c','id_cohorte',coh)]:
   column=ind+suffix
   expected=panel[key].map(reference[ind])
   if ind=='aioe_pct':
    if column not in panel:
     raise ValueError(f'Falta {column} en el panel principal; reconstruya el panel con exposición basal.')
    if not np.allclose(panel[column].to_numpy(float),expected.to_numpy(float),
                       rtol=1e-12,atol=1e-12,equal_nan=True):
     raise ValueError(f'{column} del panel no coincide con la agregación basal 2022; revise los insumos.')
   else:
    panel[column]=expected
 return panel

def cargar_micro():
 cols=['P6040','P6020','CLASE','P1_DEPARTAMENTO','P6051','OCI_geih','DSI_geih','P6920_geih','INGLABO_geih','OFICIO_C8_geih','OFICIO1_C8_geih','OFICIO2_C8_geih','FEX_C','P1910','P1911','P1075','P3042_geih']
 dfs=[]
 for year in range(2021,2026):
  d=pd.read_parquet(MICRODATOS[year],columns=cols);d['anio']=year;dfs.append(d)
 d=pd.concat(dfs,ignore_index=True)
 d['ciuo08_buscada']=ocupacion_analitica(d,variante='buscada')
 d['ciuo08']=ocupacion_analitica(d,variante='anterior')
 indices=cargar_indices()[['ciuo08']+IND]
 d=d.merge(indices,on='ciuo08',how='left',validate='m:1')
 for c in COMMON:d[c+'_buscada']=d.ciuo08_buscada.map(indices.set_index('ciuo08')[c])
 d['oficio_2d']=d.ciuo08.str[:2];d['dpto']=d.P1_DEPARTAMENTO
 d['post']=(d.anio>=2023).astype(float)
 d['edad']=d.P6040.clip(15,95);d['edad2']=(d.edad/10)**2
 d['mujer']=(d.P6020==2).astype(float);d['rural']=(d.CLASE==2).astype(float);d['jefe']=(d.P6051==1).astype(float)
 valid_tic=d.P1910.isin([1,2,3,4,5])&d.P1911.isin([1,2,3,4,5])&d.P1075.isin([1,2])
 d['H_tic']=((d.P1910.isin([1,2,3,4])|d.P1911.isin([1,2,3,4]))&(d.P1075==1)).astype(float).where(valid_tic)
 d['H_edu']=d.P3042_geih.isin([10,11,12,13]).astype(float)
 d['edu_cat']=d.P3042_geih.map({1:0,2:0,3:1,4:2,5:2,6:2,7:2,8:3,9:3,10:4,11:4,12:4,13:4})
 d['desempleo']=np.where((d.OCI_geih==1)|(d.DSI_geih==1),(d.DSI_geih==1).astype(float),np.nan)
 d['no_cotiza']=np.where((d.OCI_geih==1)&d.P6920_geih.isin([1,2]),(d.P6920_geih==2).astype(float),np.nan)
 income=d.INGLABO_geih*d.anio.map({2021:151.76/110.06,2022:151.76/123.51,2023:151.76/136.45,2024:151.76/143.83,2025:1})
 d['salario']=np.log(income.where((d.OCI_geih==1)&(income>0)))
 d['generacion']=np.searchsorted([1964,1974,1984,1994],d.anio-d.P6040,side='left')+1
 d['id_cohorte']=d.dpto.astype('Int64').astype(str)+'_'+d.P6020.astype('Int64').astype(str)+'_'+d.generacion.astype(str)
 return d

def diseno(d,controls,fe):
 z=[pd.DataFrame({'const':np.ones(len(d))},index=d.index),d[controls].astype(float)]
 z.extend(pd.get_dummies(d[c],prefix=c,drop_first=True,dtype=float) for c in fe)
 return pd.concat(z,axis=1).to_numpy(float)

class FWL:
 def __init__(self,d,y,controls,fe,w,cluster):
  self.d=d;self.y=d[y].to_numpy(float);self.w=d[w].to_numpy(float)
  self.Z=diseno(d,controls,fe); self.n=len(d)
  self.codes,self.groups=pd.factorize(d[cluster],sort=True); self.G=len(self.groups)
  # QR selects a full-rank basis without changing the span of the controls.
  _,r,piv=linalg.qr(self.Z*np.sqrt(self.w[:,None]),mode='economic',pivoting=True)
  rank=int(np.sum(np.abs(np.diag(r))>np.abs(r[0,0])*max(self.Z.shape)*np.finfo(float).eps))
  self.Z=self.Z[:,piv[:rank]];self.rank=rank
  self.inv=np.linalg.inv(self.Z.T@(self.w[:,None]*self.Z))
  self.yr=self.y-self.Z@(self.inv@(self.Z.T@(self.w*self.y)))
 def fit(self,B,names):
  B=np.asarray(B,float);B=B[:,None] if B.ndim==1 else B
  R=B-self.Z@(self.inv@(self.Z.T@(self.w[:,None]*B)))
  bread=np.linalg.inv(R.T@(self.w[:,None]*R));b=bread@(R.T@(self.w*self.yr));e=self.yr-R@b
  sums=np.zeros((self.G,len(names)));np.add.at(sums,self.codes,R*(self.w*e)[:,None])
  k=self.rank+len(names);cov=bread@(sums.T@sums)@bread*(self.G/(self.G-1))*((self.n-1)/(self.n-k))
  tss=np.sum(self.w*(self.y-np.average(self.y,weights=self.w))**2)
  diag={'nobs':self.n,'clusters':self.G,'r2_total':1-np.sum(self.w*e*e)/tss,'rango_diseno':k}
  return b,cov,diag

def guardar(family,model,outcome,ind,b,cov,diag,names,weight,cluster,base):
 for j,name in enumerate(names):
  se=float(np.sqrt(max(0,cov[j,j])));t=float(b[j]/se);crit=stats.t.ppf(.975,diag['clusters']-1)
  ROWS.append(dict(familia=family,modelo=model,resultado=outcome,indice=ind,escala='percentil' if ind.endswith('_pct') else 'minmax',parametro=name,coef=float(b[j]),se=se,p=float(2*stats.t.sf(abs(t),diag['clusters']-1)),ci_lower=float(b[j]-crit*se),ci_upper=float(b[j]+crit*se),**diag,ponderador=weight,cluster=cluster,base=base,muestra='comun_cinco_indices',papel='principal' if ind=='aioe_pct' else ('sensibilidad' if ind.endswith('_mm') or ind.startswith('envolvente') else ('automatizacion' if ind.startswith(('software','robots')) else 'complementaria_IA'))))

def main():
 started=time.time();d=cargar_micro();print('Microdatos',len(d),flush=True)
 common=d.dropna(subset=COMMON+CONT+['FEX_C','dpto','anio','ciuo08','oficio_2d','edu_cat','H_tic']);common=common[common.FEX_C>0].copy()
 coverage=[]
 for outcome in ['desempleo','no_cotiza','salario']:
  coverage.append({'resultado':outcome,'disponible':int(d[outcome].notna().sum()),'comun':int(common[outcome].notna().sum())})
 pd.DataFrame(coverage).to_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/cobertura_muestras_comparables.csv'),index=False)
 # Analytic export is small enough to permit independent Stata replication.
 exports=common[['anio','dpto','ciuo08','oficio_2d','FEX_C','post','H_tic','H_edu','edu_cat']+CONT+['desempleo','no_cotiza','salario']+IND].copy()
 exports['ciuo08']=exports.ciuo08.astype(int);exports['oficio_2d']=exports.oficio_2d.astype(int)
 exports.to_stata((Path(__file__).resolve().parents[2] / 'datos/derivados_modelos/oficiales/clasicos/indices_comparables_micro.dta'),write_index=False,version=118)
 for outcome in ['desempleo','no_cotiza','salario']:
  q=common.dropna(subset=[outcome]);print(outcome,len(q),flush=True)
  fit=FWL(q,outcome,CONT,['dpto','anio','oficio_2d','edu_cat'],'FEX_C','ciuo08')
  for ind in IND:
   v=q[ind].to_numpy();post=q.post.to_numpy()
   for model,ts in [('estatico',[post]),('dinamico',[(q.anio==2021).to_numpy()]+[(q.anio==year).to_numpy() for year in [2023,2024,2025]])]:
    names=['exposicion_basal']+(['exposicion_post'] if model=='estatico' else ['exposicion_2021','exposicion_2023','exposicion_2024','exposicion_2025'])
    b,cov,diag=fit.fit(np.column_stack([v]+[v*t for t in ts]),names)
    guardar('did',model,outcome,ind,b,cov,diag,names,'FEX_C','ciuo08','microdatos GEIH–ECV 2021–2025')
    if model=='dinamico':
     # Post-conjunto (2023-2025) igual que antes; exposicion_2021 (posición 1) es el contraste de
     # pre-tendencia frente a la base 2022 y se reporta por su propio coeficiente/p en resultados,
     # no se mezcla en este F conjunto.
     z=b[2:];C=cov[2:,2:];F=float(z@np.linalg.inv(C)@z/3);a=np.array([0,0,-1,0,1]);bd=float(a@b);se=float(np.sqrt(a@cov@a))
     TESTS.append(dict(familia='did',resultado=outcome,indice=ind,F_conjunto=F,p_conjunto=float(stats.f.sf(F,3,diag['clusters']-1)),cambio_2025_2023=bd,se_cambio=se,p_cambio=float(2*stats.t.sf(abs(bd/se),diag['clusters']-1))))
  del fit
  for h in ['H_tic','H_edu']:
   fit=FWL(q,outcome,CONT,['dpto','anio','oficio_2d','edu_cat'],'FEX_C','ciuo08')
   for ind in IND:
    v=q[ind].to_numpy();p=q.post.to_numpy();H=q[h].to_numpy();names=['exposicion_basal','exposicion_post','exposicion_H','post_H','triple','H']
    B=np.column_stack([v,v*p,v*H,p*H,v*p*H,H])
    if h=='H_edu':names=names[:-1];B=B[:,:-1]
    b,cov,diag=fit.fit(B,names)
    guardar('ddd',h,outcome,ind,b,cov,diag,names,'FEX_C','ciuo08','microdatos GEIH–ECV 2021–2025')
    a=np.array([0,1,0,0,1]+([0] if h=='H_tic' else []));guardar('ddd',h,outcome,ind,np.array([a@b]),np.array([[a@cov@a]]),diag,['exposicion_post_H1'],'FEX_C','ciuo08','microdatos GEIH–ECV 2021–2025')
   del fit
  # Save progressively so projections need not wait for panel fits.
  pd.DataFrame(ROWS).to_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/resultados_indices_comparables.csv'),index=False)
 del exports,common
 # Alternative assignment is diagnostic: occupation sought among unemployed.
 alt=d.copy()
 alt['ciuo08']=alt.ciuo08_buscada;alt['oficio_2d']=alt.ciuo08.str[:2]
 for ind in COMMON:alt[ind]=alt[ind+'_buscada']
 alt=alt.dropna(subset=COMMON+CONT+['FEX_C','dpto','anio','ciuo08','oficio_2d','edu_cat','desempleo']);alt=alt[alt.FEX_C>0]
 f=FWL(alt,'desempleo',CONT,['dpto','anio','oficio_2d','edu_cat'],'FEX_C','ciuo08')
 for ind in COMMON:
  v=alt[ind].to_numpy();names=['exposicion_basal','exposicion_post']
  beta,cov,diag=f.fit(np.column_stack([v,v*alt.post.to_numpy()]),names)
  guardar('did','sensibilidad_buscada','desempleo',ind,beta,cov,diag,names,'FEX_C','ciuo08','ocupación actual ocupados 2021–2025; buscada desempleados')
 del alt,f
 # Base occupation shares use current occupation only, employed 2022 and common coverage.
 b=d[(d.anio==2022)&(d.OCI_geih==1)].dropna(subset=COMMON+['FEX_C','dpto','id_cohorte']).copy();b=b[b.FEX_C>0]
 def aggregate(key):
  vals=b[IND].multiply(b.FEX_C,axis=0).groupby(b[key]).sum().div(b.groupby(key).FEX_C.sum(),axis=0)
  vals['n_ocupados']=b.groupby(key).size();vals['suma_pesos']=b.groupby(key).FEX_C.sum();return vals
 dep=aggregate('dpto');coh=aggregate('id_cohorte')
 dep.to_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/exposicion_departamental_indices_2022.csv'));coh.to_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/exposicion_cohortes_indices_2022.csv'))
 panel=pd.read_parquet(PANEL_2021_2025)
 panel['desempleo']=panel.tasa_desempleo;panel['no_cotiza']=panel.prop_no_cotiza_respuesta12;panel['salario']=panel.log_sal_real_medio
 panel['post']=(panel.anio>=2023).astype(float)
 panel=incorporar_indices_panel(panel,dep,coh)
 panel.to_stata((Path(__file__).resolve().parents[2] / 'datos/derivados_modelos/oficiales/clasicos/indices_comparables_panel.dta'),write_index=False,version=118)
 for outcome in ['desempleo','no_cotiza','salario']:
  q=panel.dropna(subset=[outcome]+PCONT+['n_obs_pet']+[i+'_c' for i in IND]+[i+'_d' for i in IND]);q=q[q.n_obs_pet>0]
  fit=FWL(q,outcome,PCONT,['id_cohorte','anio'],'n_obs_pet','departamento')
  for ind in IND:
   for family,suffix,models in [('shiftshare','_d',['estatico','dinamico']),('panel','_c',['within'])]:
    v=q[ind+suffix].to_numpy()
    for model in models:
     names=['exposicion_post'] if model!='dinamico' else ['exposicion_2021','exposicion_2023','exposicion_2024','exposicion_2025']
     times=[q.post.to_numpy()] if model!='dinamico' else [(q.anio==2021).to_numpy()]+[(q.anio==yr).to_numpy() for yr in [2023,2024,2025]]
     beta,cov,diag=fit.fit(np.column_stack([v*t for t in times]),names)
     guardar(family,model,outcome,ind,beta,cov,diag,names,'n_obs_pet','departamento','pseudo-panel 330 cohortes × 5 años')
  a=q[q.anio==2022].set_index('id_cohorte');z=q[q.anio==2025].set_index('id_cohorte');ids=a.index.intersection(z.index);a=a.loc[ids];z=z.loc[ids]
  fd=z.copy();fd[outcome]=z[outcome]-a[outcome];fd[PCONT]=z[PCONT]-a[PCONT];fd['peso_fd']=(a.n_obs_pet+z.n_obs_pet)/2
  f=FWL(fd,outcome,PCONT,[],'peso_fd','departamento')
  for ind in IND:
   beta,cov,diag=f.fit(fd[ind+'_c'].to_numpy(),['exposicion_post'])
   guardar('panel','fd',outcome,ind,beta,cov,diag,['exposicion_post'],'media n_obs_pet 2022/2025','departamento','330 diferencias de cohorte 2025−2022')
  print('Panel',outcome,'finalizado',flush=True)
 assert np.isfinite(pd.DataFrame(ROWS)[['coef','se','p','ci_lower','ci_upper']].to_numpy()).all(), 'Resultado no finito'
 pd.DataFrame(ROWS).to_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/resultados_indices_comparables.csv'),index=False)
 pd.DataFrame(TESTS).to_csv((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/contrastes_indices_comparables.csv'),index=False)
 metadata={'estrategia':'AIOE percentil principal; indicadores separados; envolvente y MinMax sensibilidad','muestra':'común cinco indicadores en cada resultado; educación válida para comparabilidad DiD/DDD','normalizacion':'tabla ocupacional fija índices_comunes; percentil (rango promedio−1)/(N−1)','inferencia':'CR1 agrupado; t(G−1); efectos fijos incluidos en rango y corrección','identificacion':'Asociaciones condicionales; dos años previos a la base (2021 y 2022); prueba de tendencias paralelas con un contraste pre-periodo (exposicion_2021) además del F conjunto post-periodo','ocupacion':'Ocupados: actual OFICIO_C8; desempleados: anterior OFICIO2. Sensibilidad: buscada OFICIO1. No imputar ocupación a primer empleo.','r2':'Total, no within','sha_tabla_scores':hashlib.sha256(((Path(__file__).resolve().parents[2] / 'datos/exposicion_ia/ciuo08_exposicion_ia_scores.csv')).read_bytes()).hexdigest(),'duracion_segundos':time.time()-started,'fuentes_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*MICRODATOS.values(),PANEL_2021_2025] if p.exists()}}
 ((Path(__file__).resolve().parents[2] / 'regresiones/resultados/legacy_modelos/resultados_indices_comparables.json')).write_text(json.dumps({'metadata':metadata,'resultados':ROWS,'contrastes':TESTS},ensure_ascii=False,indent=2))
 print('OK',len(ROWS),'coeficientes',time.time()-started,flush=True)
if __name__=='__main__':main()
