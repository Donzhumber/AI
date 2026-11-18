# Revisión reproducible de la sección 5.3

Revisión del 30 de octubre de 2026. Sustituye exclusivamente la presentación DML-IV de la sección 5.3 por estimaciones armonizadas de AIOE. No modifica las bases originales, DML-DiD ni R-learner. La carpeta `antes` conserva la versión anterior del QMD, los scripts y los resultados de DML-IV.

## Ejecutar

Desde esta carpeta:

```sh
python3 ejecutar_revision.py
python3 verificar_revision.py
```

La primera orden estima los tres resultados principales, repite las cinco particiones con otras dos semillas y evalúa ocupación buscada únicamente como sensibilidad del desempleo. `--solo-principal` permite estimar sólo los tres modelos principales, pero el informe completo requiere la ejecución sin esa opción.

Se necesita la estructura original del proyecto. `preparacion_dml_iv.py` resuelve las rutas desde su ubicación y utiliza `datos/imputados/ecv_geih_imputada_2025.parquet`, el catálogo ocupacional y `datos/exposicion_ia/indices_comunes.py`. Las versiones de Python y paquetes, las semillas y las huellas SHA-256 se registran en `salidas/manifest.json`. No se requiere Stata.

`requirements.txt` conserva las versiones utilizadas. La verificación completa finalizó correctamente, incluyendo reconstrucción de D, normalización, ocupación anterior, universos, separación de donantes y ocupaciones entre particiones, fórmulas de inferencia y recuperación de un efecto conocido en datos sintéticos.

## Qué se corrigió

- Uso declarado de IA como actividad por internet, respetando la selección múltiple y los saltos de ECV. No identifica exclusivamente adopción en el empleo ni IA fuera de internet. Los campos vacíos no se convierten indiscriminadamente en cero. En los universos laborales adultos de 2025 la regla revisada no cambia el indicador anterior.
- AIOE fijo con `(rango promedio - 1)/(N - 1)`. La exposición principal usa ocupación actual para ocupados y anterior para desocupados. La ocupación buscada se conserva sólo como sensibilidad.
- Edad original válida y controles del receptor ECV. Educación combina nivel alcanzado de no asistentes y nivel actual de asistentes, con control adicional de asistencia. El indicador digital mide uso personal de computador en cualquier lugar más internet del hogar, no tenencia ni dotación previa. No se completan departamentos ni respuestas desconocidas con valores inventados.
- El modelo es PLIV, con parámetro `theta_IV`. No se etiqueta automáticamente LATE, pues AIOE es continuo y no se estima el modelo interactivo de instrumento binario.
- Cinco particiones por ocupación, comprobando también separación por donante. Los ponderadores entran en aprendizaje y momentos. Los errores estándar agrupan ocupaciones, sin pretender incorporar todo el diseño de encuesta o toda la incertidumbre del matching.

## Archivos

| Archivo | Contenido |
| --- | --- |
| `tratamiento_ia.py` | Construcción de D y diagnóstico de rutas |
| `diagnostico_tratamiento.md` | Evidencia oficial y conteos de respuesta |
| `preparacion_dml_iv.py` | Reglas de universos, exposición y controles |
| `estimador_dml_iv.py` | PLIV ponderado, cross-fitting e inferencia |
| `ejecutar_revision.py` | Ejecución completa y trazabilidad |
| `verificar_revision.py` | Verificaciones numéricas y de muestras |
| `salidas/base_analitica_2025.parquet` | Base preparada con ítems originales e indicadores |
| `salidas/resultados_dml_iv_aioe.csv` | Tres modelos principales, leídos por Anexo A |
| `salidas/resultados_todas_variantes.csv` | Modelos principales y sensibilidades |
| `salidas/diagnosticos_modelos.json` | Métricas fuera de muestra e inversión del momento |
| `salidas/particiones_*.parquet` | Muestras efectivas e identificadores de partición |
| `salidas/comparacion_antes_despues.csv` | Comparación con resultados previos |
| `salidas/diagnostico_preparacion.json` | Cobertura y filtros |

## Identificación e interpretación

El estimador sigue Chernozhukov et al. (2018), sección 4.2, ecuación 4.8, mediante medias condicionales del resultado, tratamiento e instrumento. Las funciones se aproximan con HistGradientBoostingRegressor, 60 iteraciones, 30 observaciones mínimas por hoja, máximo 15 hojas, aprendizaje 0,06, regularización 1 y sin parada temprana. Esta configuración queda fijada, sin escogerla por significancia.

Los conjuntos adicionales invierten la prueba del momento ortogonal con residuos fuera de muestra y sumas por ocupación, con corte t de G−1 grados de libertad. Siguen la lógica de Anderson–Rubin, pero no son una implementación exacta del test clásico ni garantizan cobertura uniforme bajo cualquier aprendizaje. Evitan interpretar un intervalo Wald convencional como evidencia concluyente ante una primera etapa casi nula. Pueden abarcar toda la recta real o ser disjuntos y no acotados. No validan la exclusión ni convierten un instrumento inválido en válido.

En la corrida principal los tres instrumentos de primera etapa son débiles. Los grandes coeficientes y sus cambios entre particiones no constituyen estimaciones estables de magnitudes causales. Para resultados binarios, valores absolutos superiores a uno no son diferencias plausibles de probabilidad bajo una interpretación de efecto constante; el conjunto disjunto de desempleo tampoco respalda esa interpretación. El diagnóstico es identificación insuficiente y posible incompatibilidad de supuestos, no ausencia demostrada de impacto.

## Fuentes

- Chernozhukov et al. (2018), DOI [10.1111/ectj.12097](https://doi.org/10.1111/ectj.12097), [texto del artículo](https://arxiv.org/html/1608.00060).
- DANE, [formulario ECV 2025](https://microdatos.dane.gov.co/index.php/catalog/905/download/24644), páginas 53–54; copia local en `datos/ECV/2025/diccionarios/Formulario_ECV2025.pdf`.
- DANE, [diccionario del módulo TIC](https://microdatos.dane.gov.co/index.php/catalog/905/data-dictionary/F15).
- Anderson y Rubin (1949), DOI [10.1214/aoms/1177730090](https://doi.org/10.1214/aoms/1177730090).
