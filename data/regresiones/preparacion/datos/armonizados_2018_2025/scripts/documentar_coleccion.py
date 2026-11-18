"""Diccionario de los productos oficiales; no cambia datos ni estimaciones."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[5]))
from pathlib import Path
import sys,json
import pandas as pd
ROOT=(Path(__file__).resolve().parents[5]);sys.path.insert(0,str(ROOT))
from regresiones.preparacion.datos.armonizados_2018_2025.rutas import CARPETA,PANEL_2018_2025


def main():
 old=json.loads(((Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/construccion/paneles/diccionario_panel_regresion.json')).read_text())
 dictionary={x['variable']:x for x in old}
 structure={'id_cohorte':'Departamento de residencia, sexo y generación','anio':'Año de encuesta','n_obs_pet':'Personas receptoras de15+ con factor positivo en la celda','departamento':'Código DANE de departamento de residencia','sexo':'Sexo del receptor ECV','generacion':'Hasta1964,1965–74,1975–84,1985–94,desde1995'}
 panel=pd.read_parquet(PANEL_2018_2025)
 for name,label in structure.items():dictionary[name]={'variable':name,'tema':'Estructura','descripcion':label,'regla':'Identificador o conteo, no media expandida'}
 for name in panel:
  if name in dictionary:continue
  if name in ['prop_H_tic','prop_uso_computador','prop_uso_ia']:
   label={'prop_H_tic':'Uso de computador escritorio o portátil y conexión del hogar','prop_uso_computador':'Uso de escritorio o portátil','prop_uso_ia':'Uso de IA por internet, ruta válida; disponible solo2025'}[name]
   dictionary[name]={'variable':name,'tema':'Tecnologías digitales','descripcion':label,'regla':'Media ponderada FEX_C entre receptoresPET con respuestas válidas; fuera de dominio o año sin pregunta permanece ausente','unidad':'proporción0–1'}
  else:
   level='cohorte' if name.endswith('_c') else 'departamento'
   scale='percentil fijo (rango promedio−1)/(N observado−1)' if '_pct_' in name else 'mínimo–máximo fijo, sensibilidad'
   dictionary[name]={'variable':name,'tema':'Exposición tecnológica basal','descripcion':f'{name}, basal2022 de {level}','regla':f'Media FEX_C de ocupados2022 con cobertura común de cinco; {scale}; constante por grupo a través de años','unidad':'escala0–1','advertencia':'No es exposición observada en las ocupaciones históricas2018–2020; es caracterización basal2022 mantenida fija'}
 for name,value in dictionary.items():
  value['celdas_observadas']=int(panel[name].notna().sum())
  value['cohortes_con_variacion_temporal']=int(panel.groupby('id_cohorte')[name].nunique().gt(1).sum())
 assert set(dictionary)==set(panel.columns)
 ((Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/diagnosticos/diccionario_panel_oficial.json')).write_text(json.dumps(list(dictionary.values()),ensure_ascii=False,indent=2))
 fields={
  'llaves':'DIRECTORIO,SECUENCIA_P,ORDEN identifican receptores; anio identifica corte',
  'pet':'Edad observada15+; no recorte superior',
  'ocupado/desocupado':'Estado laboral transferido a receptoresPET; no simultáneos',
  'desempleo':'1desocupado,0ocupado; ausente fuera de fuerza laboral',
  'no_cotiza':'1respuesta2,0respuesta1 entre ocupados; otras respuestas ausentes',
  'ingreso_laboral_real':'Valor GEIH transferido a ocupado, COPoctubre2025; ausente fuera de ocupado',
  'log_ingreso_laboral_real':'Log del ingreso individual positivo; en panel el resultado es log de media ponderada, no media de logs',
  'educacion_ecv':'Armonización nativa ECV0–4 mediante rutas documentadas',
  'tic_combinado':'Uso escritorio/portátil categorías1–4 y hogarP1075=1; observación válida requiere respuestas1–5enambosequipos y1–2eninternet',
  'uso_ia':'Misma construcción validada del DML-IV; solo2025, sin ceros para blancos desconocidos',
  'ruta_ia_valida':'uso_ia observado; no supone edad laboral, población5+disponible en fuente',
  'ciuo08':'Actualocupados,últimadesocupados; no usa buscada principal;2018–20ausente sin correspondencia',
  'indices':'Cinco percentiles y escalasMM del catálogo fijo; envolvente sensibilidad exige los tres índicesIA observados',
  'cobertura_comun_cinco':'Observación deAIOE,WebbIA,LLM,softwareyrobots; no incluye por sí sola controles de regresión'}
 ((Path(__file__).resolve().parents[5] / 'datos/armonizados_2018_2025/diagnosticos/diccionario_indicadores_oficiales.json')).write_text(json.dumps(fields,ensure_ascii=False,indent=2))
 print('Diccionario oficial de101columnas y definiciones individuales guardados.')

if __name__=='__main__':main()
