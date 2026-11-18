# Vista de exposición alineada con el Anexo A

## Interfaz

La vista principal muestra el gráfico correspondiente a la población seleccionada. El explorador permite elegir la combinación de índices mediante un desplegable, seleccionar los ejes y distinguir ocupados de desocupados. Los colores de los cuadrantes son I verde, II ámbar, III gris y IV rojo. Las tarjetas muestran población, participación, número de ocupaciones y tasas con universos definidos. El detalle de las ocupaciones principales complementa las tarjetas. La pirámide demográfica histórica de las tarjetas no se reproduce con el nuevo agregado ocupacional, que no contiene edades ni sexo; la pestaña demográfica independiente se mantiene.

La pestaña Exposición tecnológica y empleo utiliza AIOE y robots en percentiles del catálogo fijo, cortes 0,50 y las bases integradas de 2022 a 2025. No usa el índice compuesto histórico ni recalcula rangos por año. I es superior izquierdo, II superior derecho, III inferior izquierdo y IV inferior derecho.

Los paneles separan ocupados y desocupados, usando ocupación actual y anterior respectivamente. Los ponderadores son FEX_C. La respuesta pensional procede de P6920_geih. La distribución roja divide los no cotizantes de cada cuadrante por el total de no cotizantes clasificables. La tabla distingue esa distribución de la tasa de no cotización entre ocupados con respuesta 1 o 2. No es informalidad oficial. Personas sin ambos índices se reportan en cobertura y se excluyen de los cuadrantes.

Desde esta carpeta ejecutar

```sh
python3 generar_cuadrantes_anexo.py
python3 generar_catalogo_multianual.py
python3 generar_perfiles_uso_ia_2025.py
python3 verificar_armonizacion.py
quarto render dashboard.qmd --to dashboard
python3 -m http.server 8008 --bind 127.0.0.1
```

Abrir http://127.0.0.1:8008/dashboard.html en Chrome. No abrir como archivo local, porque los módulos y datos interactivos requieren HTTP. No hace falta ejecutar el último comando si el servidor ya está activo.

El generador comprueba las sumas de las distribuciones y contrasta cinco series de 2025 contra Hechos_estilizados_2025/cuadrantes_2025.csv con tolerancia numérica. Registra hashes de las fuentes en data/cuadrantes_anexo.json. Los datos no contienen identificadores individuales. La búsqueda resalta puntos y filtra el detalle sin cambiar los denominadores.

La pestaña histórica se conserva en referencia/ia_impacto_antes_alineacion.qmd, sin utilizarse en el HTML vigente. Sus interpretaciones antiguas no son una referencia metodológica validada. Las fuentes de 2021 y los paneles del inspector se seleccionan mediante la colección armonizada. Las vistas mantienen universos propios que deben distinguirse de las muestras econométricas.

## Exploración de parejas entre cinco indicadores

El mismo JSON añade `ocupaciones_indices` para cada año, sin reemplazar las series originales de AIOE y robots. Contiene una fila por ocupación y condición laboral que tenga al menos uno de los cinco indicadores observados. Sus columnas son `aioe_pct`, `webb_ia_pct`, `llm_pct`, `software_pct` y `robots_pct`, junto con código, descripción, universo, número muestral, población ponderada, masa de ocupados con respuesta pensional válida y masa de no cotizantes. Los índices ausentes se conservan como `null`, nunca como cero. Los denominadores `denominadores_universo` incluyen todos los ocupados o desocupados con peso positivo y finito, antes de exigir exposición.

Para cada pareja seleccionada se filtran exclusivamente las ocupaciones con ambos índices observados. Las participaciones se recalculan sobre ese universo cubierto, mientras que su cobertura divide por el denominador total de la condición laboral. Los cortes son 0,5 en la escala percentil fija y los empates se asignan al grupo alto. No se estiman percentiles sobre la muestra seleccionada. Cambiar de pareja puede cambiar cobertura y composición, especialmente cuando interviene LLM.

La lista antigua `ocupaciones` y los campos `cobertura` y `cuadrantes` conservan la definición original AIOE y robots para compatibilidad. `metadata.indices_disponibles` documenta las cinco alternativas. La respuesta pensional es pertinente solo para ocupados, aunque los desocupados mantienen masas pensionales iguales a cero para facilitar la suma, sin interpretar cero como una tasa de cotización.

El generador contrasta las diez parejas en cuatro años y ambos universos con los microdatos, para 80 combinaciones. Verifica los cuatro cuadrantes, los conteos, masas poblacionales y pensionales, los porcentajes que suman cien y la cobertura dentro de cero y cien. Guarda el informe en `data/validacion_parejas_indices.json`. Además conserva la comprobación de cinco series AIOE y robots de 2025 frente al anexo. Ninguna validación convierte estos indicadores descriptivos en efectos causales ni probabilidades de automatización.


## Colección oficial armonizada

Los tres generadores leen `datos.armonizados_2018_2025.rutas`. Los anuales conservan las columnas de origen; las puntuaciones publicadas se vuelven a asignar desde el catálogo fijo, nunca desde percentiles históricos incorporados en esos archivos. El panel del inspector se deriva de las mismas versiones anuales que las estimaciones. El enlace `dashboard/datos` apunta a `../datos` y es una dependencia de publicación que debe conservarse.

La vista de IA aplica `uso_ia_validado` del módulo compartido, que respeta las rutas del cuestionario ECV 2025. Educación procede del receptor ECV, combinando nivel alcanzado y actual según asistencia. TIC combinado identifica uso personal de computador y acceso del hogar a internet, preservando respuestas desconocidas. La población del módulo comienza en cinco años; las vistas laborales tienen su propio universo y no deben confundirse con la muestra del DML-IV.

El eje opcional de uso reportado de IA se construye entre ocupados por ocupación actual con al menos 30 rutas válidas. Su posición percentil es un ordenamiento descriptivo de prevalencias en 2025, distinto de los cinco índices internacionales. La diagonal solo compara posiciones relativas; no mide adopción óptima, subadopción causal ni uso necesariamente laboral. La prevalencia original aparece separada en el globo.

El catálogo de compatibilidad utiliza los mismos cinco percentiles fijos, multiplicados por cien únicamente para las vistas históricas que esperan una escala de 0 a 100. Esa conversión no recalcula rangos. Las medidas pensionales usan la respuesta transferida `P6920_geih` y los ingresos medios incluyen únicamente valores laborales reales positivos. El explorador principal mantiene la escala 0 a 1.

`data/verificacion_armonizacion.json` registra los contrastes de universos, IA, catálogo y destinos de FileAttachment. `data/validacion_parejas_indices.json` contiene las 80 combinaciones comprobadas. Las verificaciones no acreditan identificación causal ni la independencia condicional del matching.
