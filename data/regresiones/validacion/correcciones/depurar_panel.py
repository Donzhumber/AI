"""Panel analítico con indicadores definidos; diagnósticos en archivo separado."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import shutil, json
import numpy as np
import pandas as pd

try:
    from .educacion import armonizar_educacion_ecv, COLUMNAS_EDUCACION_ECV
    from .exposicion_panel import incorporar_exposicion_basal, entradas_diccionario
except ImportError:  # Ejecución directa desde la raíz del proyecto.
    from educacion import armonizar_educacion_ecv, COLUMNAS_EDUCACION_ECV
    from exposicion_panel import incorporar_exposicion_basal, entradas_diccionario

BASE=(Path(__file__).resolve().parents[3])
OUT=(Path(__file__).resolve().parents[3] / 'datos/imputados/panel')
IPM=['alfabetismo','logro_educativo','inasistencia_escolar','rezago_escolar','trabajo_infantil','atencion_integral','desempleo_larga_duracion','empleo_formal','aseguramiento_salud','barreras_acceso_salud','acueducto','alcantarillado','pisos','paredes','hacinamiento']
IPC={2022:123.51,2023:136.45,2024:143.83,2025:151.76}
FUENTE='https://microdatos.dane.gov.co/index.php/catalog/827/data-dictionary'


def ocupacion_ciuo_valida(codigos):
    """Filtro de formato: excluye 0/desconocido, no certifica cada código del catálogo."""
    numeric=pd.to_numeric(codigos,errors='coerce')
    return numeric.between(110,9998)&numeric.mod(1).eq(0)


def informe_econometrico(tables,audit,indicadores):
    """Diagnósticos de disponibilidad e identidades; no pruebas de exogeneidad."""
    def finite(value):
        return float(value) if pd.notna(value) and np.isfinite(value) else None
    result={'advertencias':[
        'Las filas balanceadas no implican datos completos para toda especificación.',
        'Los recuentos y tamaños Kish son descriptivos; no incorporan diseño complejo ni incertidumbre del matching.',
        'Los donantes distintos se refieren al donante individual; los atributos sincronizados por jefe requieren su propia trazabilidad.',
        'No incluir simultáneamente IPM y sus 15 componentes: identidad lineal exacta cuando comparten soporte.',
        'Efectos fijos de cohorte absorben departamento, sexo y generación; revisar variación temporal de cada regresor.',
        'Los indicadores no se eliminan automáticamente por escasez; justificar la muestra y sensibilidad de cada modelo.',
        'El ingreso logarítmico es log de media positiva, no media de logaritmos; las unidades monetarias son COP de octubre de 2025.',
    ],'paneles':{}}
    ipm_weights=np.array([.1,.1,.05,.05,.05,.05,.1,.1,.1,.1,.04,.04,.04,.04,.04])
    for closed,t in tables.items():
        variant='cerrada' if closed else 'principal'
        a=audit.loc[audit.variante.eq(variant)]
        complete=t[indicadores].notna().all(axis=1)
        stats={}
        for name in indicadores:
            z=a.loc[a.variable.eq(name)]
            observed=z.loc[z.n_observados.gt(0)]
            stats[name]={
                'celdas_observadas':int(t[name].notna().sum()),
                'celdas_faltantes':int(t[name].isna().sum()),
                'valores_distintos':int(t[name].nunique()),
                'constante_o_vacia':bool(t[name].nunique()<=1),
                'cohortes_con_variacion_temporal':int(t.groupby('id_cohorte')[name].nunique().gt(1).sum()),
                'n_receptores_min_entre_observados':finite(observed.n_observados.min()),
                'n_receptores_mediana_entre_observados':finite(observed.n_observados.median()),
                'cobertura_ponderada_min':finite(z.cobertura.min()),
                'cobertura_ponderada_mediana':finite(z.cobertura.median()),
                'donantes_individuales_min_entre_observados':finite(observed.n_donantes_individuales.min()),
                'donantes_individuales_mediana_entre_observados':finite(observed.n_donantes_individuales.median()),
            }
        ipm_cols=['priv_'+x for x in IPM]
        joint=t[['ipm_medio']+ipm_cols].dropna()
        residual=joint.ipm_medio-(joint[ipm_cols].to_numpy()*ipm_weights).sum(axis=1)
        labor=t.tasa_ocupacion-t.tasa_participacion*(1-t.tasa_desempleo)
        result['paneles'][variant]={
            'filas':len(t),'cohortes':int(t.id_cohorte.nunique()),
            'casos_completos_todos_indicadores':int(complete.sum()),
            'casos_completos_por_anio':{str(k):int(v) for k,v in complete.groupby(t.anio).sum().items()},
            'identidad_ipm_error_maximo':finite(residual.abs().max()),
            'identidad_laboral_error_maximo':finite(labor.abs().max()),
            'indicadores':stats,
        }
    return result


def depurar(base=None, datos=None, out=None, years=range(2022,2026), ipc=None):
    """Agrega microdatos; no elimina indicadores por criterios de una regresión.

    ``datos`` apunta al directorio que contiene ``imputados``; el panel se guarda dentro de este último.
    Todas las rutas de lectura y escritura derivan de esa misma configuración.
    """
    base=Path(base).resolve() if base is not None else BASE
    datos=Path(datos).resolve() if datos is not None else base/'datos'
    out=Path(out).resolve() if out is not None else datos/'imputados/panel'
    out.mkdir(parents=True,exist_ok=True)
    years=tuple(years)
    ipc=IPC if ipc is None else ipc
    if not years or not set(years).issubset(ipc) or 2025 not in ipc:
        raise ValueError('Se requieren años y factores IPC, con base 2025.')
    backup=out/'respaldo_exploratorio_9423';backup.mkdir(exist_ok=True)
    for filename in ['panel_cohortes_2022_2025','panel_cohortes_nacimiento_hasta_2007']:
        for ext in ['parquet','dta']:
            p=out/f'{filename}.{ext}'
            # Nunca sustituir respaldo con una versión ya depurada o intermedia.
            if p.exists() and not (backup/p.name).exists():
                import pyarrow.parquet as pq
                if len(pq.read_schema(out/f'{filename}.parquet').names)>1000:shutil.copy2(p,backup/p.name)
    catalog={}; audits=[]; panels={False:[],True:[]}
    cols=['P6040','P1_DEPARTAMENTO','P6020','FEX_C','CLASE','P6051','CANT_PERSONAS_HOGAR','P8587','OCI_geih','DSI_geih','P6920_geih','P6800_geih','P6430_geih','OFICIO_C8_geih','inglabo_real_geih','PERCAPITA','I_UGASTO','ingpcug_pm_real_geih','pobre_pm_geih','ipm','pobre','P1075','P1910','P1911','P1912','P1084','P1082','P6090','P5095']+IPM
    cols=list(dict.fromkeys(cols+list(COLUMNAS_EDUCACION_ECV)+['id_donante_geih']))
    for year in years:
        d=pd.read_parquet(datos/f'imputados/ecv_geih_imputada_{year}.parquet',columns=cols)
        d=d.loc[d.P6040.ge(15)&np.isfinite(d.FEX_C)&d.FEX_C.gt(0)].reset_index(drop=True)
        born=year-d.P6040
        gen=np.select([born.le(1964),born.le(1974),born.le(1984),born.le(1994)],[1,2,3,4],default=5)
        ids=d.P1_DEPARTAMENTO.astype(int).astype(str)+'_'+d.P6020.astype(int).astype(str)+'_'+pd.Series(gen).astype(str)
        oc=d.OCI_geih.eq(1);ds=d.DSI_geih.eq(1);pet=np.ones(len(d),bool)
        if (oc&ds).any():
            raise ValueError(f'OCI y DSI simultáneos en {year}: revisar clasificación laboral.')
        features={}
        def add(name,tema,label,x,valid=None,domain=None,source='',reference='',log=False):
            arr=np.asarray(x,dtype=float)
            eligible=np.asarray(domain if domain is not None else pet,bool)
            ok=np.isfinite(arr)&eligible
            if valid is not None:ok &= np.asarray(valid,bool)
            features[name]=(arr,ok,eligible,log)
            catalog[name]=dict(variable=name,tema=tema,descripcion=label,fuente=source,referencia_omitida=reference,tipo='continua agregada',regla='Logaritmo de media ponderada positiva' if log else 'Media o proporción ponderada',denominador='Dominio indicado en descripción, con respuesta válida; pesos ECV FEX_C',unidad='log(COP de octubre 2025)' if log else ('proporcion 0-1' if name.startswith(('prop_','tasa_','priv_')) else 'ver descripcion'),documentacion=FUENTE)
        add('edad_media','Demografía','Edad media de personas PET (años)',d.P6040,source='ECV P6040')
        add('tam_hogar_medio','Demografía','Tamaño del hogar de la persona PET (personas)',d.CANT_PERSONAS_HOGAR,valid=d.CANT_PERSONAS_HOGAR.gt(0),source='ECV CANT_PERSONAS_HOGAR')
        add('prop_rural','Demografía','Personas PET residentes en centros poblados/rural disperso',d.CLASE.eq(2),valid=d.CLASE.isin([1,2]),source='ECV CLASE',reference='Cabecera')
        add('prop_jefes','Demografía','Jefes de hogar entre PET',d.P6051.eq(1),valid=d.P6051.notna(),source='ECV P6051',reference='Otros parentescos')
        ed=armonizar_educacion_ecv(d)
        for code,label in [(1,'primaria'),(2,'secundaria'),(3,'tecnica'),(4,'universitaria')]:
            add('prop_edu_'+label,'Educación',f'PET con educación {label}; escala armonizada ECV',ed.eq(code),valid=ed.notna(),source='ECV P8586/P8587/P1088/P1088S1/P6216; rutas armonizadas',reference='Sin educación/preescolar (escala0)')
        add('tasa_ocupacion','Mercado laboral','Ocupados imputados / PET',oc,source='GEIH OCI, PET receptor')
        add('tasa_participacion','Mercado laboral','Fuerza laboral imputada / PET',oc|ds,source='GEIH OCI y DSI, PET receptor')
        add('tasa_desempleo','Mercado laboral','Desocupados imputados / fuerza laboral imputada',ds,domain=oc|ds,source='GEIH OCI y DSI')
        for value,name in [(1,'cotizante'),(3,'pensionado')]:
            add('prop_'+name+'_ocup','Mercado laboral',f'{name} entre ocupados con condición pensional informada',d.P6920_geih.eq(value),valid=d.P6920_geih.isin([1,2,3]),domain=oc,source='GEIH P6920',reference='No cotizante')
        add('prop_no_cotiza_respuesta12','Mercado laboral','No cotizantes entre ocupados con respuesta pensional 1 o 2; pensionados y faltantes excluidos',d.P6920_geih.eq(2),valid=d.P6920_geih.isin([1,2]),domain=oc,source='GEIH P6920',reference='Cotizante (1)')
        add('horas_semanales_medias','Mercado laboral','Horas habituales entre ocupados (0–168)',d.P6800_geih,valid=d.P6800_geih.between(0,168),domain=oc,source='GEIH P6800')
        for val,label in [(1,'privado'),(2,'publico'),(3,'domestico'),(5,'empleador'),(6,'familiar_sin_pago'),(7,'jornalero'),(8,'otro')]:
            add('prop_pos_'+label,'Posición ocupacional',f'Posición {label} entre ocupados con posición1–8',d.P6430_geih.eq(val),valid=d.P6430_geih.isin(range(1,9)),domain=oc,source='GEIH P6430',reference='Cuenta propia (4); otros códigos excluidos')
        major=np.floor(d.OFICIO_C8_geih/1000)
        for val,label in [(0,'fuerzas_armadas'),(1,'directivos'),(2,'profesionales'),(3,'tecnicos'),(4,'administrativos'),(5,'servicios_ventas'),(6,'agropecuarios'),(7,'oficiales_artesanos'),(8,'operadores')]:
            valid=ocupacion_ciuo_valida(d.OFICIO_C8_geih)
            add('prop_ocu_'+label,'Ocupaciones',f'Gran grupo CIUO {val}: {label}; entre ocupados con código válido',major.eq(val),valid=valid,domain=oc,source='GEIH OFICIO_C8',reference='Ocupaciones elementales (9)')
        for name,dom,label in [('log_sal_real_medio',oc,'ocupados'),('log_sal_real_cotizante',oc&d.P6920_geih.eq(1),'cotizantes'),('log_sal_real_no_cotizante',oc&d.P6920_geih.eq(2),'no cotizantes'),('log_sal_real_pensionado',oc&d.P6920_geih.eq(3),'pensionados')]:
            add(name,'Ingresos',f'Log de ingreso laboral medio real entre {label} con ingreso positivo',d.inglabo_real_geih,valid=d.inglabo_real_geih.gt(0),domain=dom,source='GEIH INGLABO imputado y deflactado',log=True)
        for name,col in [('log_ingpc_ecv_real','PERCAPITA'),('log_ingug_ecv_real','I_UGASTO')]:
            x=d[col]*ipc[2025]/ipc[year]
            add(name,'Ingresos',f'Log media real {col} entre PET con ingreso positivo; atributo de unidad de gasto',x,valid=x.gt(0),source='ECV '+col+'; IPC octubre',log=True)
        add('log_ingpc_geih_real','Ingresos','Log media ingreso per cápita real sincronizado por jefe, entre PET con ingreso positivo',d.ingpcug_pm_real_geih,valid=d.ingpcug_pm_real_geih.gt(0),source='GEIH ingpcug_pm, donante del jefe',log=True)
        add('prop_pobreza_monetaria','Pobreza y bienestar','PET con pobreza monetaria imputada entre informados',d.pobre_pm_geih,valid=d.pobre_pm_geih.isin([0,1]),source='GEIH pobre_pm, donante del jefe')
        add('prop_pobreza_multidim','Pobreza y bienestar','PET en hogares pobres multidimensionales entre informados',d.pobre,valid=d.pobre.isin([0,1]),source='ECV pobre')
        add('ipm_medio','Pobreza y bienestar','Media del puntaje de privaciones IPM (0–1), entre informados',d.ipm,valid=d.ipm.between(0,1),source='ECV ipm')
        for c in IPM:
            add('priv_'+c,'Privaciones del IPM',f'PET en hogares con privación IPM: {c}; entre informados',d[c],valid=d[c].isin([0,1]),source='ECV indicador IPM '+c)
        add('prop_afiliacion_salud','Salud','Afiliados a salud entre PET con respuesta sí/no',d.P6090.eq(1),valid=d.P6090.isin([1,2]),source='ECV P6090')
        for value,label in [(1,'propia_pagada'),(2,'propia_pagando'),(4,'usufructo'),(5,'posesion'),(6,'colectiva')]:
            add('prop_viv_'+label,'Vivienda',f'PET en vivienda {label}, entre respuestas válidas',d.P5095.eq(value),valid=d.P5095.isin(range(1,7)),source='ECV P5095',reference='Arriendo/subarriendo (3)')
        for c,label in [('P1910','escritorio'),('P1911','portatil'),('P1912','tableta'),('P1084','internet')]:
            for vals,usage in [([1,2,3,4],'uso'),([1],'diario')]:
                add(f'prop_{usage}_{label}','Tecnologías digitales',f'PET: {usage} de {label}, entre respuestas1–5',d[c].isin(vals),valid=d[c].isin(range(1,6)),source='ECV '+c,reference='No uso para uso; uso no diario/no uso para diario')
        for c,name,label in [('P1075','prop_internet_hogar','PET en hogar con conexión a internet'),('P1082','prop_tiene_celular','PET con teléfono celular')]:
            add(name,'Tecnologías digitales',label,d[c].eq(1),valid=d[c].isin([1,2]),source='ECV '+c,reference='No')
        for closed in [False,True]:
            sample=born.le(2007).to_numpy() if closed else pet
            labels,g=np.unique(ids[sample],return_inverse=True);w=d.FEX_C.to_numpy()[sample];ng=len(labels)
            donor=d.id_donante_geih.to_numpy()[sample]
            if not np.isfinite(donor).all() or (donor<0).any() or (donor%1!=0).any():
                raise ValueError('Se requieren identificadores de donante enteros no negativos.')
            donor=donor.astype(np.int64);stride=int(donor.max())+1
            cells={'id_cohorte':labels,'anio':np.full(ng,year),'n_obs_pet':np.bincount(g,minlength=ng)}
            parts=pd.Series(labels).str.split('_',expand=True)
            cells.update(departamento=parts[0].astype(int).to_numpy(),sexo=parts[1].astype(int).to_numpy(),generacion=parts[2].astype(int).to_numpy())
            for name,(x,ok,dom,log) in features.items():
                x=x[sample];ok=ok[sample];dom=dom[sample]
                mass=np.bincount(g[ok],weights=w[ok],minlength=ng);den=np.bincount(g[dom],weights=w[dom],minlength=ng)
                nums=np.bincount(g[ok],weights=w[ok]*x[ok],minlength=ng)
                means=np.divide(nums,mass,out=np.full(ng,np.nan),where=mass>0)
                if log:means=np.log(means)
                cells[name]=means
                counts=np.bincount(g[ok],minlength=ng)
                coverage=np.divide(mass,den,out=np.full(ng,np.nan),where=den>0)
                domain_counts=np.bincount(g[dom],minlength=ng)
                sum_w2=np.bincount(g[ok],weights=w[ok]**2,minlength=ng)
                kish=np.divide(mass**2,sum_w2,out=np.full(ng,np.nan),where=sum_w2>0)
                keys,inverse=np.unique(g[ok]*stride+donor[ok],return_inverse=True)
                donor_groups=keys//stride
                donor_counts=np.bincount(donor_groups,minlength=ng)
                donor_mass=np.bincount(inverse,weights=w[ok],minlength=len(keys))
                donor_sum_w2=np.bincount(donor_groups,weights=donor_mass**2,minlength=ng)
                donor_kish=np.divide(mass**2,donor_sum_w2,out=np.full(ng,np.nan),where=donor_sum_w2>0)
                audits.extend(dict(variante='cerrada' if closed else 'principal',anio=year,id_cohorte=k,variable=name,
                    n_observados=int(counts[j]),n_dominio=int(domain_counts[j]),cobertura=float(coverage[j]),
                    masa_observada=float(mass[j]),masa_dominio=float(den[j]),n_kish_receptores=float(kish[j]),
                    n_donantes_individuales=int(donor_counts[j]),n_kish_donantes_individuales=float(donor_kish[j]))
                    for j,k in enumerate(labels))
            panels[closed].append(pd.DataFrame(cells))
    tables={k:pd.concat(v,ignore_index=True) for k,v in panels.items()}
    tables[False] = incorporar_exposicion_basal(tables[False], base)
    # La selección de regresores corresponde al modelo; informar, no borrar.
    drop=[]
    removed={}
    for closed,t in tables.items():
        t=t.drop(columns=drop)
        assert not t.duplicated(['id_cohorte','anio']).any()
        filename='panel_cohortes_nacimiento_hasta_2007' if closed else 'panel_cohortes_2022_2025'
        t.to_parquet(out/(filename+'.parquet'),index=False)
        t.to_stata(out/(filename+'.dta'),write_index=False,version=118)
    audit=pd.DataFrame(audits);audit.to_parquet(out/'diagnosticos_panel_regresion.parquet',index=False)
    dictionary=[]
    for c,entry in catalog.items():
        if c in drop:continue
        t=tables[False];entry['celdas_observadas']=int(t[c].notna().sum());entry['cohortes_con_variacion_temporal']=int((t.groupby('id_cohorte')[c].nunique()>1).sum())
        dictionary.append(entry)
    dictionary += entradas_diccionario(tables[False])
    pd.DataFrame(dictionary).to_json(out/'diccionario_panel_regresion.json',orient='records',indent=2,force_ascii=False)
    summary=dict(filas=len(tables[False]),columnas=len(tables[False].columns)-len(drop),indicadores=len(dictionary),columnas_estructura=6,por_tema=pd.DataFrame(dictionary).tema.value_counts().to_dict(),exclusiones_adicionales=removed)
    summary.update(indicadores_agregados=72, exposiciones_basales=2,
                   exposicion_basal_solo_panel_principal=['aioe_pct_c','aioe_pct_d'])
    (out/'resumen_panel_regresion.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
    informe=informe_econometrico(tables,audit,list(catalog))
    (out/'diagnostico_econometrico.json').write_text(json.dumps(informe,indent=2,ensure_ascii=False,allow_nan=False))
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    return tables[False].drop(columns=drop)

if __name__=='__main__':depurar()
