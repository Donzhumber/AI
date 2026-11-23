# -*- coding: utf-8 -*-
"""Lectura y presentación del Anexo reorganizado; no estima ni altera insumos."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import json
import numpy as np
import pandas as pd
from IPython.display import display, Markdown

BASE=(Path(__file__).resolve().parents[3])
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import CARPETA as CANON, PANEL_2022_2025, PANEL_CERRADO_2022_2025
PROY=BASE/'regresiones/historico/proyecciones/Proyeccion_IA_2026_2030'
LABEL={'aioe_pct':'AIOE','webb_ia_pct':'Webb–IA','llm_pct':'LLM','software_pct':'Software','robots_pct':'Robots','envolvente_pct':'Envolvente','aioe_mm':'AIOE MM','webb_ia_mm':'Webb–IA MM','llm_mm':'LLM MM','software_mm':'Software MM','robots_mm':'Robots MM','envolvente_mm':'Envolvente MM'}
OUTCOME={'desempleo':'Desempleo','no_cotiza':'No cotización','informal':'No cotización','informalidad':'No cotización','salario':'Ingreso laboral'}

def leer(path):
    return json.loads((BASE/path).read_text(encoding='utf-8'))

def datos(nombre):
    return pd.DataFrame(leer('datos/imputados/diagnosticos/'+nombre+'.json'))

def evaluacion_anual(nombre):
    d=pd.DataFrame(leer('datos/armonizados_2018_2025/diagnosticos/evaluacion_transversal_2022_2025/'+nombre+'.json'))
    if set(d.anio.unique()) != {2022, 2023, 2024, 2025}:
        raise ValueError('Evaluación incompleta: ejecutar auditoria/evaluacion_transversal/ejecutar.py para los cuatro años')
    return d

def evaluacion_historica(nombre):
    d=pd.read_json((Path(__file__).resolve().parents[3] / 'datos/armonizados_2018_2025/diagnosticos/integracion')/f'{nombre}.json')
    if set(d.anio.unique()) != set(range(2018,2026)):
        raise ValueError('Evaluación histórica incompleta')
    return d


def formato_evaluacion(frame, enteros=(), decimales=None):
    """Separadores españoles solo para las tablas de evaluación transversal."""
    t=frame.copy()
    decimales=decimales or {}
    for c in t:
        if c == 'Año':
            t[c]=t[c].map(lambda v: str(int(v)))
        elif c in enteros:
            t[c]=t[c].map(lambda v: '—' if pd.isna(v) else f'{int(v):,}'.replace(',', '.'))
        elif pd.api.types.is_numeric_dtype(t[c]):
            n=decimales.get(c, 2)
            t[c]=t[c].map(lambda v: '—' if pd.isna(v) else f'{v:.{n}f}'.replace('.', ','))
    return t

def mostrar(frame):
    t=pd.DataFrame(frame).copy()
    for c in t:
        if pd.api.types.is_numeric_dtype(t[c]):
            def fmt(v):
                if pd.isna(v):return '—'
                if c in ['Año','N','G','Filas','Columnas','Cohortes','Receptores','Donantes','Ocupaciones','Personas GEIH','Personas ECV','Excluidos'] or str(c).startswith('N '):return f'{int(v):,}'.replace(',','.') if c!='Año' else str(int(v))
                if str(c).endswith('%'):return f'{v:.2f}'
                if c=='Afinidad':return f'{v:.4f}'
                return f'{v:.5g}'
            t[c]=t[c].map(fmt)
        else:t[c]=t[c].fillna('—').astype(str).str.replace('|','/',regex=False).str.replace('\n',' ',regex=False).str.replace('≥',r'$\geq$',regex=False).str.replace('≤',r'$\leq$',regex=False)
    display(Markdown(t.to_markdown(index=False, disable_numparse=True)))

def fuentes():
    d=evaluacion_historica('fuentes_reproducidas')
    d=d[['anio','geih','geih_admisibles','ecv','excluidos','receptores','donantes_unicos']].rename(columns={'anio':'Año','geih':'GEIH original','geih_admisibles':'GEIH admisible','ecv':'ECV original','excluidos':'Excluidos ECV','receptores':'Receptores','donantes_unicos':'Donantes utilizados'})
    return formato_evaluacion(d, enteros=list(d.columns[1:]))

def matching():
    d=evaluacion_historica('matching_reproducido')
    d=d[['anio','desempleo_imputado','no_cotizacion','fallback_ponderado_pct','usos_medios','usos_maximos']].rename(columns={'anio':'Año','desempleo_imputado':'Desempleo %','no_cotizacion':'No cotiza %','fallback_ponderado_pct':'Ampliación %','usos_medios':'Usos medios','usos_maximos':'Usos máximos'})
    return formato_evaluacion(d, enteros=['Usos máximos'])


def soporte():
    d=datos('publicacion/soporte')
    return d.iloc[:,:6].rename(columns={'Estratos Observados en ECV':'Bloques ECV','Estratos Observados en GEIH':'Bloques GEIH','Estratos en Intersección Común':'Comunes','Estratos en Fallback Rural':'Sin donante local','% Cobertura de Estratos':'Cobertura %'})

def validacion_laboral():
    d=evaluacion_anual('metricas');d=d.loc[d.dominio.eq('total')&d.ponderacion.eq('FEX_C')]
    d=d[['anio','variante','sensibilidad','especificidad','concordancia','recuperacion_no_principal']].copy()
    d.variante=d.variante.replace({'actual_6D':'6D','sin_P6240_5D':'5D'})
    return formato_evaluacion(d.rename(columns={'anio':'Año','variante':'Distancia','sensibilidad':'Sensibilidad %','especificidad':'Especificidad %','concordancia':'Acuerdo %','recuperacion_no_principal':'Recuperación de ocupados con otra actividad principal %'}))

def reservadas():
    d=evaluacion_anual('variables_reservadas')
    d=d.loc[d.dominio.eq('reserva_hogares')&d.variante.eq('actual_6D')].copy()
    d['variable']=d.variable.replace({'pension':'Afiliación pensional','posicion_grupos':'Posición ocupacional','horas':'Horas trabajadas'})
    d=d[['anio','variable','n_comparables','cobertura_pct','acuerdo_pct','mae_horas','sesgo_horas']].rename(columns={'anio':'Año','variable':'Variable','n_comparables':'N','cobertura_pct':'Cobertura %','acuerdo_pct':'Acuerdo %','mae_horas':'Error absoluto medio en horas','sesgo_horas':'Sesgo en horas'})
    return formato_evaluacion(d, enteros=['N'])

def empates():
    d=evaluacion_anual('empates')
    d['Cambio ocupación (pp)']=d.tasa_ocupacion_alternativa-d.tasa_ocupacion_actual
    for c in ['receptores_sin_dimension_educativa', 'cambios_ocupacion']:
        d[c]=d[c].map(lambda v: f'{int(v):,}'.replace(',', '.'))
    for c in ['empates_pct', 'empates_ponderados_pct', 'Cambio ocupación (pp)']:
        d[c]=d[c].map(lambda v: f'{v:.2f}'.replace('.', ','))
    return d[['anio','empates_pct','empates_ponderados_pct','receptores_sin_dimension_educativa','cambios_ocupacion','Cambio ocupación (pp)']].rename(columns={'anio':'Año','empates_pct':'Empates %','empates_ponderados_pct':'Empates ponderados %','receptores_sin_dimension_educativa':'Sin educación en métrica','cambios_ocupacion':'Cambios individuales'})

def tasas():
    d=evaluacion_historica('matching_reproducido')
    d['Diferencia pp']=d.desempleo_imputado-d.desempleo_geih
    d=d[['anio','desempleo_geih','desempleo_imputado','Diferencia pp']].rename(columns={'anio':'Año','desempleo_geih':'GEIH %','desempleo_imputado':'ECV imputada %'})
    return formato_evaluacion(d)

def coherencia():
    d=evaluacion_historica('coherencia_anual').set_index('anio')
    criterios=[('sensibilidad_actividad_pct','Sensibilidad respecto de actividad principal %',2),
               ('acuerdo_actividad_pct','Acuerdo respecto de actividad principal %',2),
               ('menores_ingreso_positivo','Menores de 15 años con ingreso laboral positivo',0),
               ('menores_ocupados','Menores de 15 años clasificados como ocupados',0),
               ('desocupados_ingreso_positivo','Desocupados con ingreso laboral positivo',0),
               ('ocupados_codigo_invalido','Ocupados con código ocupacional ausente o inválido',0),
               ('correlacion_ingreso_percapita','Correlación de ingreso per cápita',3),
               ('n_pares_ingreso','Personas con ambos ingresos para la correlación',0)]
    filas=[]
    for campo,label,n in criterios:
        fila={'Comprobación':label}
        for year,row in d.iterrows():
            value=row[campo]
            fila[str(year)]=('—' if pd.isna(value) else f'{int(value):,}'.replace(',', '.') if n==0 else f'{value:.{n}f}'.replace('.', ','))
        filas.append(fila)
    return pd.DataFrame(filas)

def hellinger():
    d=evaluacion_anual('hellinger_anual')
    d=d.loc[d.comparacion.eq('ECV original')]
    t=d.pivot(index='variable',columns='anio',values='afinidad').reindex(d.variable.drop_duplicates()).reset_index()
    t.columns=['Variable']+[str(c) for c in t.columns[1:]]
    return formato_evaluacion(t, decimales={str(y):4 for y in d.anio.unique()})

def diagnostico_panel():
    path=(Path(__file__).resolve().parents[3] / 'datos/armonizados_2018_2025/diagnosticos/panel_2018_2025/evaluacion_panel.json')
    d=json.loads(path.read_text(encoding='utf-8'))
    if {r['anio'] for r in d['estructura_anual']} != set(range(2018,2026)):
        raise ValueError('Diagnósticos de panel incompletos: ejecutar auditoria/armonizacion_2018_2025/evaluar_panel.py')
    return d


def paneles():
    d=pd.DataFrame(diagnostico_panel()['estructura_anual'])
    cols={'anio':'Año','cohortes':'Cohortes','filas':'Celdas','columnas':'Columnas',
          'pet_min':'Mín. PET','pet_mediana':'Mediana PET','pet_max':'Máx. PET'}
    return formato_evaluacion(d[list(cols)].rename(columns=cols),
        enteros=['Cohortes','Celdas','Columnas','Mín. PET','Máx. PET'],decimales={'Mediana PET':1})


def calidad_panel():
    d=pd.DataFrame(diagnostico_panel()['calidad_anual'])
    cols={'anio':'Año','resultado':'Resultado','celdas_observadas':'Celdas válidas',
          'receptores_min':'Receptores mín.','donantes_min':'Donantes mín.',
          'donantes_mediana':'Donantes mediana','cobertura_min_pct':'Cobertura mín. %'}
    return formato_evaluacion(d[list(cols)].rename(columns=cols),
        enteros=['Celdas válidas','Receptores mín.','Donantes mín.'],decimales={'Donantes mediana':1})


def analisis_matching():
    d=datos('validacion_laboral/metricas');d=d.loc[d.dominio.eq('total')&d.ponderacion.eq('FEX_C')&d.variante.eq('actual_6D')]
    r=datos('validacion_laboral/variables_reservadas');r=r.loc[r.anio.eq(2023)&r.dominio.eq('reserva_hogares')&r.variante.eq('actual_6D')].set_index('variable')
    display(Markdown(f"La reconstrucción laboral más amplia arroja acuerdos ponderados entre **{d.concordancia.min():.2f}% y {d.concordancia.max():.2f}%**. La recuperación de ocupados cuya actividad principal no era trabajar se sitúa entre {d.recuperacion_no_principal.min():.2f}% y {d.recuperacion_no_principal.max():.2f}%; esta limitación impide equiparar concordancia con cobertura completa de las rutas laborales. En los hogares reservados de 2023, el acuerdo pensional alcanza {r.loc['pension','acuerdo_pct']:.2f}% y el de posición ocupacional {r.loc['posicion_grupos','acuerdo_pct']:.2f}%; el error absoluto medio de horas es {r.loc['horas','mae_horas']:.2f} horas. La coherencia contable y el acuerdo agregado, por tanto, coexisten con discrepancias individuales relevantes."))

def referencia_indices():
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'datos/exposicion_ia/distribucion_indices_referencia.csv'))
    d=d.loc[d.indice.isin(['aioe_pct','webb_ia_pct','llm_pct','software_pct','robots_pct'])].copy()
    d['indice']=d.indice.map(LABEL)
    return d[['indice','count','mean','std','min','max']].rename(columns={'indice':'Índice','count':'Ocupaciones','mean':'Media','std':'DE','min':'Mínimo','max':'Máximo'})

def correlaciones_indices():
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'datos/exposicion_ia/correlaciones_indices_muestra_comun.csv'));d['indice']=d.indice.map(LABEL)
    return d.rename(columns={'indice':'Índice',**LABEL})

def cobertura_indices():
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'datos/exposicion_ia/cobertura_indices_micro.csv'))
    d=d.loc[d.universo.isin(['ocupados','desocupados'])&d.indice.eq('comun_cinco')]
    return d[['anio','universo','n_total','n_con_indice','cobertura_pct','cobertura_ponderada_pct']].rename(columns={'anio':'Año','universo':'Universo','n_total':'N universo','n_con_indice':'N común','cobertura_pct':'Cobertura %','cobertura_ponderada_pct':'Cobertura ponderada %'})

def muestras():
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/cobertura_muestras_comparables.csv'));d['resultado']=d.resultado.map(OUTCOME)
    d['Retención %']=100*d.comun/d.disponible
    return d.rename(columns={'resultado':'Resultado','disponible':'N universo','comun':'N común'})

def coeficientes(familia,modelo,parametro='exposicion_post',indices='pct'):
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/resultados_indices_comparables.csv'))
    mask=d.familia.eq(familia)&d.modelo.eq(modelo)
    if parametro is not None:mask &= d.parametro.eq(parametro)
    if indices=='principal':mask &= d.indice.eq('aioe_pct')
    elif indices=='pct':mask &= d.indice.isin(['aioe_pct','webb_ia_pct','llm_pct','software_pct','robots_pct'])
    elif indices=='sensibilidad':mask &= d.indice.str.endswith('_mm')|d.indice.eq('envolvente_pct')
    elif isinstance(indices,list):mask &= d.indice.isin(indices)
    d=d.loc[mask].copy()
    order={k:i for i,k in enumerate(LABEL)}
    d['_orden']=d.indice.map(order)
    return d.sort_values(['resultado','_orden','parametro']).drop(columns='_orden')

def tabla_coef(d,descriptor='indice'):
    d=d.copy()
    r=pd.DataFrame({'Resultado':d.resultado.map(OUTCOME),
       'Índice' if descriptor=='indice' else 'Término':d[descriptor].replace(LABEL).replace({'exposicion_2021':'2021','exposicion_2023':'2023','exposicion_2024':'2024','exposicion_2025':'2025','exposicion_post':'H=0','triple':'Interacción triple','exposicion_post_H1':'H=1'}),
       'Coef. (EE)':[f'{b:.4f} ({s:.4f})' for b,s in zip(d.coef,d.se)],
       'IC 95%':[f'[{lo:.4f}; {hi:.4f}]' for lo,hi in zip(d.ci_lower,d.ci_upper)],
       'p':[f'{x:.4g}' for x in d.p],'N':d.nobs,'G':d.clusters})
    return r

def regresiones(familia,modelo,indices='pct'):
    return tabla_coef(coeficientes(familia,modelo,indices=indices))

def dinamica(familia='did'):
    d=coeficientes(familia,'dinamico',parametro=None,indices='principal');d=d.loc[d.parametro.str.match('exposicion_202[1345]')]
    return tabla_coef(d,descriptor='parametro').rename(columns={'Término':'Año de contraste'})

def triples(h):
    d=coeficientes('ddd',h,parametro=None,indices='principal')
    return tabla_coef(d.loc[d.parametro.isin(['exposicion_post','triple','exposicion_post_H1'])],descriptor='parametro')

def triple_alternativas():
    rows=[]
    for h,label in [('H_tic','TIC'),('H_edu','Educación')]:
        d=coeficientes('ddd',h,parametro='triple',indices=['webb_ia_pct','llm_pct','software_pct','robots_pct'])
        t=tabla_coef(d);t['Índice']=label+' / '+t['Índice'];rows.append(t)
    return pd.concat(rows,ignore_index=True)

def contrastes():
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/contrastes_indices_comparables.csv'));d=d.loc[d.indice.eq('aioe_pct')].copy();d.resultado=d.resultado.map(OUTCOME)
    return d[['resultado','F_conjunto','p_conjunto','cambio_2025_2023','se_cambio','p_cambio']].rename(columns={'resultado':'Resultado','F_conjunto':'F conjunto','p_conjunto':'p conjunto','cambio_2025_2023':'Beta2025−Beta2023','se_cambio':'EE diferencia','p_cambio':'p diferencia'})

def interpretar(familia,modelo):
    d=coeficientes(familia,modelo,indices='principal')
    for _,r in d.iterrows():
        wage=r.resultado=='salario'
        fn=(lambda v:100*np.expm1(.1*v)) if wage else (lambda v:10*v)
        unit='%' if wage else 'puntos porcentuales'
        finding='el intervalo excluye cero al 5%' if r.p<.05 else 'el intervalo incluye cero y no permite establecer un signo con el criterio del 5%'
        meaning=('ingreso geométrico condicional entre perceptores positivos' if familia=='did' else 'ingreso laboral medio positivo de cohorte') if wage else ('probabilidad de desempleo dentro de la muestra con ocupación identificable' if r.resultado=='desempleo' and familia=='did' else ('tasa de desempleo de cohorte' if r.resultado=='desempleo' else 'no cotización pensional'))
        display(Markdown(f"**{OUTCOME[r.resultado]}.** Un contraste de 0,1 unidades de AIOE se asocia con un cambio diferencial de **{fn(r.coef):+.3f} {unit}** en {meaning}, con intervalo [{fn(r.ci_lower):+.3f}; {fn(r.ci_upper):+.3f}] y p={r.p:.4g}. Econométricamente, {finding}. Esta magnitud corresponde a la especificación y población de la tabla; no se interpreta como respuesta a un aumento observado de adopción de IA."))

def interpretar_ddd():
    for h,label in [('H_tic','habilitación TIC'),('H_edu','educación universitaria')]:
        d=coeficientes('ddd',h,parametro='triple',indices='principal')
        parts=[]
        for _,r in d.iterrows():
            val=10*r.coef
            parts.append(f"{OUTCOME[r.resultado].lower()}: {val:+.3f} {'puntos logarítmicos ×100' if r.resultado=='salario' else 'pp'}, p={r.p:.3g}")
        display(Markdown(f"Para **{label}**, la diferencia adicional entre grupos asociada a 0,1 unidades de AIOE es: "+'; '.join(parts)+'. En el resultado salarial, la interacción es una diferencia de cambios logarítmicos, no una suma de porcentajes de ingreso. El contraste neto del grupo habilitado debe leerse en la fila H=1.'))

def ml():
    return pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_indices_ml.csv'))

def tabla_ml(indices=None):
    d=ml();indices=indices or ['aioe_pct','webb_ia_pct','llm_pct','software_pct','robots_pct'];d=d[d.indice.isin(indices)]
    return pd.DataFrame({'Resultado':d.resultado.map(OUTCOME),'Índice':d.indice.map(LABEL),'PLR (EE)':[f'{b:.4f} ({s:.4f})' for b,s in zip(d.theta_diagnostico,d.se)],'IC 95%':[f'[{a:.3f}; {b:.3f}]' for a,b in zip(d.ci_lower,d.ci_upper)],'p diagnóstico':d.p,'N':d.nobs,'G':d.clusters})

def diagnostico_ml():
    d=ml();d=d[d.indice.isin(['aioe_pct','webb_ia_pct','llm_pct'])]
    return pd.DataFrame({'Resultado':d.resultado.map(OUTCOME),'Índice':d.indice.map(LABEL),'Media D residual²':d.var_D_residual,'Var D':d.var_D,'BLP (EE)':[f'{v:.4f} ({e:.4f})' for v,e in zip(d.blp,d.blp_se)],'p BLP':d.blp_p})

def interpretar_ml():
    d=ml();d=d[d.indice.eq('aioe_pct')]
    for _,r in d.iterrows():
        judgement='presenta pendiente distinta de cero al 5%' if r.blp_p<.05 else 'no presenta pendiente distinta de cero al 5%'
        display(Markdown(f"**{OUTCOME[r.resultado]}.** El coeficiente PLR diagnóstico es {r.theta_diagnostico:+.4f}, p={r.p:.4g}. La calibración externa BLP {judgement} (pendiente {r.blp:+.4f}, p={r.blp_p:.4g}). El segundo momento ponderado del tratamiento residual equivale a {100*r.var_D_residual/r.var_D:.3f}% de la varianza total de D. Estos resultados describen el comportamiento del aprendizaje y de su residualización; no permiten calcular creación de empleo, formalización o ganancias salariales causadas por IA."))

def tabla_dml_did(indice='aioe_pct'):
    p_did = (Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_dml_did_rc.csv')
    if not p_did.exists():
        return pd.DataFrame()
    d = pd.read_csv(p_did)
    d = d[d.tipo.eq('principal')].copy()
    return pd.DataFrame({
        'Resultado': d.resultado.map(OUTCOME),
        'Contraste': [f'{a}–{b}' for a,b in zip(d.pre,d.post)],
        'ATT DML-DiD (EE)': [f'{b:+.4f} ({s:.4f})' for b, s in zip(d.att, d.se_cluster_ocupacion)],
        'IC 95%': [f'[{a:+.4f}; {b:+.4f}]' for a,b in zip(d.ci_lower,d.ci_upper)],
        'p-valor': d.p.map(lambda x: f'{x:.4f}'),
        'Observaciones': d.nobs.map(lambda x: f'{x:,}')
    })

def tabla_dml_did_placebo():
    p = (Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_dml_did_rc.csv')
    if not p.exists():
        return pd.DataFrame()
    d = pd.read_csv(p)
    d = d[d.tipo.eq('placebo')].copy()
    return pd.DataFrame({
        'Resultado': d.resultado.map(OUTCOME),
        'ATT placebo (EE)': [f'{b:+.4f} ({s:.4f})' for b,s in zip(d.att,d.se_cluster_ocupacion)],
        'IC 95%': [f'[{a:+.4f}; {b:+.4f}]' for a,b in zip(d.ci_lower,d.ci_upper)],
        'p-valor': d.p.map(lambda x: f'{x:.4f}'),
        'Observaciones': d.nobs.map(lambda x: f'{x:,}')
    })

def tabla_dml_aioe():
    p = (Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_dml_aioe.csv')
    if not p.exists():
        return pd.DataFrame()
    d = pd.read_csv(p)
    return pd.DataFrame({
        'Resultado': d.resultado.map(OUTCOME),
        'Coeficiente DML (EE)': [f'{b:+.4f} ({s:.4f})' for b,s in zip(d.theta,d.se)],
        'IC 95%': [f'[{a:+.4f}; {b:+.4f}]' for a,b in zip(d.ci_lower,d.ci_upper)],
        'p-valor': d.p.map(lambda x: f'{x:.4f}'),
        'Observaciones': d.nobs.map(lambda x: f'{x:,}'),
        'Ocupaciones': d.clusters.map(lambda x: f'{x:,}')
    })

def tabla_dml_did_continuo(principal=True):
    p = (Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_dml_did_continuo.csv')
    if not p.exists():
        return pd.DataFrame()
    d = pd.read_csv(p)
    main = 'Pre 2021–2022 / Post 2023–2025'
    d = d[d.contraste.eq(main) if principal else ~d.contraste.eq(main)].copy()
    return pd.DataFrame({
        'Resultado': d.resultado.map(OUTCOME),
        'Contraste': d.contraste,
        'Coeficiente (EE)': [f'{b:+.4f} ({s:.4f})' for b,s in zip(d.theta,d.se)],
        'IC 95%': [f'[{a:+.4f}; {b:+.4f}]' for a,b in zip(d.ci_lower,d.ci_upper)],
        'p-valor': d.p.map(lambda x: f'{x:.4f}'),
        'Cohortes': d.nobs.map(lambda x: f'{x:,}')
    })

def tabla_dml_iv(indice=None):
    p_iv = (Path(__file__).resolve().parents[3] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/salidas/resultados_dml_iv_aioe.csv')
    if not p_iv.exists():
        raise FileNotFoundError('Ejecutar revision_53_20261030/ejecutar_revision.py antes de publicar la sección 5.3')
    d = pd.read_csv(p_iv)
    if indice is not None:
        d = d.loc[d.instrumento.eq(indice)].copy()
    return pd.DataFrame({
        'Resultado': d.resultado.map(OUTCOME),
        'Instrumento (Z)': d.instrumento.map(LABEL),
        'Coeficiente IV (EE)': [f'{b:+.4f} ({s:.4f})'.replace('.', ',') for b, s in zip(d.theta_iv, d.se)],
        'p convencional': d.p.map(lambda x: f'{x:.4f}'.replace('.', ',')),
        'F primera etapa': d.f_stat_primer_paso.map(lambda x: f'{x:.4f}'.replace('.', ',')),
        'Personas': d.nobs.map(lambda x: f'{x:,}'.replace(',', '.')),
        'Ocupaciones': d.clusters.map(str)
    })

def tabla_dml_iv_identificacion():
    carpeta = (Path(__file__).resolve().parents[3] / 'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/salidas')
    d = pd.read_csv(carpeta/'resultados_dml_iv_aioe.csv')
    variantes = pd.read_csv(carpeta/'resultados_todas_variantes.csv')
    variantes = variantes.loc[variantes.variante.isin(['principal','particion_alternativa'])]
    rangos = variantes.groupby('resultado').theta_iv.agg(['min','max'])
    return pd.DataFrame({
        'Resultado': d.resultado.map(OUTCOME),
        'Conjunto por inversión con umbral del 5 %': d.ar_conjunto,
        'Rango del coeficiente entre particiones': [f'[{rangos.loc[k,"min"]:+.4f}; {rangos.loc[k,"max"]:+.4f}]'.replace('.', ',') for k in d.resultado]
    })

def tabla_cate():
    p_cate = (Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/05_DML_CausalForest/resultados_cate.json')
    if not p_cate.exists():
        return pd.DataFrame()
    with open(p_cate, 'r', encoding='utf-8') as f:
        data = json.load(f)
    rows = []
    for item in data:
        cl = item.get('clan_subgrupos', {})
        rows.append({
            'Resultado': OUTCOME.get(item['resultado'], item['resultado']),
            'BLP β (p)': f"{item['blp_beta_hetero']:+.4f} ({item['blp_p']:.3f})",
            'Con TIC': f"{cl.get('con_tic', np.nan):+.3f}",
            'Sin TIC': f"{cl.get('sin_tic', np.nan):+.3f}",
            'Universitaria o posgrado': f"{cl.get('universitarios', np.nan):+.3f}",
            'Resto de niveles': f"{cl.get('no_universitarios', np.nan):+.3f}",
            'Mujeres': f"{cl.get('mujeres', np.nan):+.3f}",
            'Hombres': f"{cl.get('hombres', np.nan):+.3f}",
            'Jóvenes ≤29': f"{cl.get('jovenes_le29', np.nan):+.3f}",
            'Adultos 30-49': f"{cl.get('adultos_30_49', np.nan):+.3f}"
        })
    return pd.DataFrame(rows)

def interpretar_causal_ml():
    display(Markdown(
        "> **Dictamen Econométrico Causal ML (2021–2025):**\n"
        "> 1. **DML-DiD y Tendencias Paralelas:** Al incorporar 2021 y evaluar el test de placebo pre-choque (2021 vs. 2022), se demuestra que los índices libres de tendencias seculares pre-existentes (*Webb-IA* y *LLM*) arrojan efectos nulos e insignificantes sobre salario ($p=0,48$ y $p=0,19$), informalidad ($p=0,44$ y $p=0,34$) y desempleo ($p=0,90$ y $p=0,77$). El coeficiente negativo de AIOE en salario refleja una violación de tendencias paralelas ya presente en 2021–2022 ($p=0,0014$), no un impacto causal de la IA generativa.\n"
        "> 2. **DML-IV del uso reportado de IA (2025):** La revisión con AIOE armonizado encuentra una primera etapa débil, coeficientes sensibles a las particiones y conjuntos de identificación no acotados. El ejercicio no permite establecer con precisión el efecto causal del uso de IA ni concluir que sea nulo.\n"
        "> 3. **Heterogeneidad Condicional:** La calibración BLP no rechaza la homogeneidad del efecto en ninguno de los tres resultados, confirmando que la IA aún no genera brechas estructurales sistemáticas entre trabajadores con o sin dotación digital en Colombia."
    ))

def parametros_proyeccion():
    d=json.loads((PROY/'parametros_calibracion_2030.json').read_text())
    return pd.DataFrame(d['escenarios_difusion_ia']).T[['nombre','A_max','lambda_vel','t0']].rename(columns={'nombre':'Escenario','lambda_vel':'Velocidad','t0':'Punto medio'})

def salarios_proyectados(todos=False,escenario='Acelerado'):
    d=pd.read_csv(PROY/'resumen_proyecciones_anuales_escenarios.csv')
    d=d[d.escenario_nombre.eq(escenario)]
    if not todos:d=d[d.anio.isin([2025,2026,2028,2030])]
    r=d[['anio','salario_medio_real','salario_medio_ic95_inferior','salario_medio_ic95_superior','salario_medio_beta_cero']].copy()
    for c in r.columns[1:]:r[c]=r[c].map(lambda x:f'{x:,.0f}'.replace(',','.'))
    return r.rename(columns={'anio':'Año','salario_medio_real':'Ingreso COP','salario_medio_ic95_inferior':'IC inferior','salario_medio_ic95_superior':'IC superior','salario_medio_beta_cero':'Beta=0'})

def escenarios(indice='aioe_pct'):
    d=pd.read_csv(PROY/'resumen_escenarios_indices_comparables.csv');d=d.loc[d.indice.eq(indice)&d.anio.eq(2030)].copy()
    d['Unidad']=np.where(d.variable.eq('salario'),'%','pp');d.variable=d.variable.map(OUTCOME)
    return d[['variable','escenario','delta','delta_ic95_inferior','delta_ic95_superior','Unidad']].rename(columns={'variable':'Resultado','escenario':'Escenario','delta':'Cambio','delta_ic95_inferior':'IC inferior','delta_ic95_superior':'IC superior'})

def escenarios_alternativos():
    d=pd.read_csv(PROY/'resumen_escenarios_indices_comparables.csv');d=d.loc[d.anio.eq(2030)&d.escenario.eq('base')].copy()
    d['Unidad']=np.where(d.variable.eq('salario'),'%','pp');d.variable=d.variable.map(OUTCOME);d.indice=d.indice.map(LABEL)
    return d[['variable','indice','delta','delta_ic95_inferior','delta_ic95_superior','Unidad']].rename(columns={'variable':'Resultado','indice':'Índice','delta':'Cambio','delta_ic95_inferior':'IC inferior','delta_ic95_superior':'IC superior'})

def interpretar_escenarios(escenario='rapido'):
    d=pd.read_csv(PROY/'resumen_escenarios_indices_comparables.csv');d=d.loc[d.indice.eq('aioe_pct')&d.anio.eq(2030)&d.escenario.eq(escenario)]
    nombre={'lento':'lento','base':'base','rapido':'rápido'}[escenario]
    partes=[]
    for _,r in d.iterrows():
        unidad='%' if r.variable=='salario' else 'pp'
        partes.append(f"{r.delta:+.3f} {unidad} en {OUTCOME[r.variable].lower()} (IC [{r.delta_ic95_inferior:+.3f}; {r.delta_ic95_superior:+.3f}])")
    todos_incluyen_cero=all(r.delta_ic95_inferior<=0<=r.delta_ic95_superior for _,r in d.iterrows())
    lista=', '.join(partes[:-1])+' y '+partes[-1] if len(partes)>1 else partes[0]
    texto=(f"Bajo el escenario {nombre} se promedia el cambio proyectado en 2030 entre los 33 departamentos, dándole el mismo peso a cada uno sin importar su tamaño: el promedio es "
           f"{lista}. "
           f"{'En los tres casos' if todos_incluyen_cero else 'En al menos uno de los casos'} el intervalo cruza el cero, es decir, incluye valores positivos y negativos a la vez, lo que significa que "
           f"{'ninguno de los tres resultados puede distinguirse' if todos_incluyen_cero else 'ese resultado no puede distinguirse'}, con la evidencia disponible, de no tener ningún efecto. Esa magnitud depende, además, de dos supuestos ajenos a los datos: la trayectoria de habilitación tecnológica que se decidió simular, y la extrapolación hacia un promedio departamental de un coeficiente individual que, en el Capítulo 3, tampoco era significativo por sí mismo.")
    display(Markdown(texto))

def indice_ilustrativo():
    d=pd.read_csv(PROY/'resumen_proyecciones_anuales_escenarios.csv');d=d[d.anio.eq(2030)]
    return d[['escenario_nombre','indice_reasignacion_ilustrativo_100','indice_reasignacion_maximo_100','proporcion_indice_superior_25_pct','labor_share_pct']].rename(columns={'escenario_nombre':'Escenario','indice_reasignacion_ilustrativo_100':'Índice medio /100','indice_reasignacion_maximo_100':'Máximo /100','proporcion_indice_superior_25_pct':'Proporción >25 (%)','labor_share_pct':'Participación salarial %'})

def interpretar_complementos(familia,modelo,parametro='exposicion_post'):
    d=coeficientes(familia,modelo,parametro=parametro,indices=['webb_ia_pct','llm_pct','software_pct','robots_pct'])
    for outcome,group in d.groupby('resultado',sort=False):
        parts=[]
        for _,r in group.iterrows():
            if outcome=='salario' and parametro=='triple':v,u=10*r.coef,'puntos logarítmicos ×100'
            elif outcome=='salario':v,u=100*np.expm1(.1*r.coef),'%'
            else:v,u=10*r.coef,'pp'
            parts.append(f"{LABEL[r.indice]}: {v:+.3f} {u} (p={r.p:.3g})")
        display(Markdown(f"**{OUTCOME[outcome]}, comparación de indicadores.** Para un contraste de 0,1 unidades, "+'; '.join(parts)+'. Los intervalos de la tabla determinan la precisión de cada asociación; los valores p son nominales y estas comparaciones no se seleccionan como efectos causales.'))

VARLABEL={'y_sal':'Salario','y_des':'Desempleo','y_inf':'Informalidad','d_tic':'TIC','d_int':'Internet','d_comp':'Computador'}
PVAR=(Path(__file__).resolve().parents[3] / 'regresiones/modelos')

def panel_var_estabilidad():
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/panel_var_estabilidad.csv'))
    d['Sistema']=d.sistema.str.replace('_',' ').str.title()
    d['Estabilidad']=np.where(d.estable,'Estable','Inestable')
    return d[['Sistema','modulo_max','Estabilidad']].rename(columns={'modulo_max':'Módulo propio máximo'})

def panel_var_coef(sistema):
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/panel_var_coeficientes.csv'));d=d.loc[d.sistema.eq(sistema)].copy()
    d['Ecuación']=d.ecuacion.map(VARLABEL);d['Término']=d.termino.str.replace('L.','',regex=False).map(VARLABEL)
    return pd.DataFrame({'Ecuación':d['Ecuación'],'Término (rezago 1)':d['Término'],
        'Coef. (EE)':[f'{b:.4f} ({s:.4f})' for b,s in zip(d.coef,d.se)],
        'IC 95%':[f'[{lo:.4f}; {hi:.4f}]' for lo,hi in zip(d.ci_lo,d.ci_hi)],'p':[f'{x:.4g}' for x in d.p]})

def panel_var_granger(sistema):
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/panel_var_granger.csv'));d=d.loc[d.sistema.eq(sistema)].copy()
    return pd.DataFrame({'Ecuación':d.ecuacion.map(VARLABEL),'Variable excluida':d.excluida.map(VARLABEL),
        'chi2':d.chi2.round(3),'g.l.':d.df.astype(int),'p':d.p.map(lambda x:f'{x:.4g}')})

RESULTADO_TIC={'salario':'Salario','desempleo':'Desempleo','informalidad':'Informalidad'}
DIGITAL_TIC={'internet':'Internet','computador':'Computador','tic_hogar':'TIC combinado (hogar)'}

def panel_tic_resumen_fe():
    fe=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/panel_tic_inferencia_departamento.csv')).set_index('resultado')
    rows=[]
    for resultado,r in fe.iterrows():
        rows.append({'Resultado':RESULTADO_TIC[resultado],
            'Coef. FE (EE dept.)':f'{r.coef:.4f} ({r.se_departamento:.4f})',
            'p agrupado':f'{r.p_departamento:.3g}',
            'p bootstrap':f'{r.p_wild_cluster:.3g}'})
    return pd.DataFrame(rows)

def panel_tic_resumen_dml():
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/dml_panel_tic_resultados.csv'))
    metodo={'fd_exacto':'Primeras diferencias exactas',
            'within_aproximado':'Within aproximado'}
    resultado={'salario':'Salario','desempleo':'Desempleo',
               'no_cotizacion':'No cotización'}
    return pd.DataFrame({
        'Método':d.metodo.map(metodo),
        'Resultado':d.resultado.map(resultado),
        'Coef. (EE dept.)':[f'{b:.4f} ({s:.4f})' for b,s in zip(d.coef,d.se_departamento)],
        'IC 95% agrupado':[f'[{lo:.4f}; {hi:.4f}]' for lo,hi in zip(d.ci95_inferior,d.ci95_superior)],
        'p bootstrap':[f'{p:.4f}' for p in d.p_wild_cluster],
        'N':d.n.astype(int)})

def panel_tic_fe(resultado,digital='tic_hogar'):
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/panel_tic_consolidado.csv'))
    r=d[(d.resultado.eq(resultado))&(d.digital.eq(digital))&(d.modelo.eq('fe'))].iloc[0]
    crit=1.96
    return pd.DataFrame({'Resultado':[RESULTADO_TIC[resultado]],'Variable':[DIGITAL_TIC[digital]],
        'Coef. (EE)':[f'{r.coef:.4f} ({r.se:.4f})'],
        'IC 95%':[f'[{r.coef-crit*r.se:.4f}; {r.coef+crit*r.se:.4f}]'],
        'p':[f'{r.p:.4g}'],'N':[int(r.N)],'G':[330]})

def panel_tic_dinamico(resultado,digital='tic_hogar'):
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/panel_tic_consolidado.csv'))
    r=d[(d.resultado.eq(resultado))&(d.digital.eq(digital))&(d.modelo.eq('dinamico'))].iloc[0]
    crit=1.96
    return pd.DataFrame({'Resultado':[RESULTADO_TIC[resultado]],'Variable':[DIGITAL_TIC[digital]],
        'Coef. (EE)':[f'{r.coef:.4f} ({r.se:.4f})'],
        'IC 95%':[f'[{r.coef-crit*r.se:.4f}; {r.coef+crit*r.se:.4f}]'],
        'p':[f'{r.p:.4g}'],'N':[int(r.N)],'G':[330]})

def panel_var_fevd(sistema,horizontes=(1,4,8)):
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/panel_var_fevd.csv'));d=d.loc[d.sistema.eq(sistema)&d.horizonte.isin(horizontes)].copy()
    d['Respuesta']=d.respuesta.map(VARLABEL);d['Impulso']=d.impulso.map(VARLABEL)
    return d.pivot_table(index=['Respuesta','Impulso'],columns='horizonte',values='participacion').reset_index().rename(columns={h:f'Año {h}' for h in horizontes})

def curva_adopcion_nacional():
    """Serie observada 2022-2025 + proyectada 2026-2030 de uso de TIC en el trabajo, nacional."""
    o=pd.read_csv((Path(__file__).resolve().parents[3] / 'datos/exposicion_ia/indice_tic_trabajo_colombia.csv'),dtype={'ciuo08':str}).dropna(subset=['uso_internet_trabajo_prop'])
    w=o.sort_values('anio').groupby('ciuo08').n_ponderado.last().rename('n_ponderado')
    p=pd.read_csv((Path(__file__).resolve().parents[3] / 'datos/exposicion_ia/proyecciones/adopcion_tic_proyectada_2026_2030.csv'),dtype={'ciuo08':str}).merge(w,on='ciuo08',how='left').dropna(subset=['n_ponderado'])
    def agregar(d,col):
        g=d.assign(_w=d[col]*d.n_ponderado).groupby('anio')[['_w','n_ponderado']].sum()
        return (100*g._w/g.n_ponderado).rename('Uso TIC en el trabajo %').reset_index()
    obs=agregar(o,'uso_internet_trabajo_prop');obs['Tipo']='Observado'
    proy=agregar(p,'uso_internet_trabajo_prop_proyectado');proy['Tipo']='Proyectado'
    return pd.concat([obs,proy],ignore_index=True).rename(columns={'anio':'Año'})

def escenario_continuidad_nacional():
    """Agregado nacional ponderado por participacion_empleo del escenario de continuidad 2026-2030."""
    d=pd.read_csv((Path(__file__).resolve().parents[3] / 'regresiones/resultados/legacy_modelos/06_Robustez_No_Lineal/escenario_continuidad_2026_2030.csv'))
    def wavg(vals,weights):
        m=vals.notna()&weights.notna()
        return np.average(vals[m],weights=weights[m]) if m.any() else np.nan
    rows=[]
    for anio,g in d.groupby('año'):
        w=g.participacion_empleo_proyectada
        rows.append({'Año':int(anio),
            'Participación de empleo':w.sum(),
            'Salario medio (log)':wavg(g.salario_medio_proyectado,w),
            'No cotización %':100*wavg(g.no_cotiza_tasa_proyectada,w)})
    return pd.DataFrame(rows)

def bandas_incertidumbre_nacional(resultado):
    """Agregado nacional (media simple departamental) de las bandas de incertidumbre, escenario de difusión TIC 'base', para un resultado dado ('desempleo','no_cotiza','salario')."""
    d=pd.read_csv(PROY/'escenarios_banda_incertidumbre_2026_2030.csv')
    d=d.loc[d.escenario_difusion_tic.eq('base')&d.resultado.eq(resultado)]
    g=d.groupby(['anio','escenario']).valor_proyectado.mean().unstack('escenario')
    return pd.DataFrame({'Año':g.index,'Inferior':g['inferior'].values,'Central':g['central'].values,'Superior':g['superior'].values,'Unidad':d.unidad.iloc[0]})

def comparacion_ilo_wb():
    """Comparación de la proyección de uso de IA contra el rango regional ILO/WB 2024."""
    path=(Path(__file__).resolve().parents[3] / 'datos/exposicion_ia/proyecciones/comparacion_ilo_wb_2026_2030.csv')
    cols=['Año','Uso de IA proyectado %','Uso de TIC proyectado %','Límite inferior ILO/WB %','Límite superior ILO/WB %']
    if not path.exists():
        return pd.DataFrame(columns=cols)
    d=pd.read_csv(path)
    def pct(s):
        s=pd.to_numeric(s)
        return 100*s if s.abs().max()<=1 else s
    return pd.DataFrame({'Año':d.anio,'Uso de IA proyectado %':pct(d.uso_ia_prop_nacional_proyectado),'Uso de TIC proyectado %':pct(d.uso_tic_trabajo_prop_nacional_proyectado),'Límite inferior ILO/WB %':pct(d.limite_inferior_ilo_wb),'Límite superior ILO/WB %':pct(d.limite_superior_ilo_wb)})
