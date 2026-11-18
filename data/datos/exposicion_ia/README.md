# Índices comunes para la estrategia econométrica vigente

## Estado y ubicación vigentes

Revisión documental del 14 de octubre de 2026.

Catálogo ocupacional vigente. AIOE percentil es el indicador principal; los demás índices y escalas se utilizan como alternativas o sensibilidad. Los promedios basales de 2022 por cohorte y departamento ya están incorporados al panel principal. Se mantienen las limitaciones documentadas sobre los archivos internacionales originales.

[Guía general de datos](../README.md).


`indices_comunes.py` es la única definición de las escalas utilizadas por la nueva estrategia.
`cargar_indices()` lee el catálogo fijo de455 códigos y agrega AIOE, Webb–IA, LLM beta GPT-4,
software y robots por separado. `*_pct` usa `(rango_promedio−1)/(N−1)` sobre los valores
observados del catálogo; `*_mm` usa Min–Max sobre ese mismo catálogo. Los cinco indicadores
no se normalizan de nuevo por año, resultado ni muestra. La envolvente máxima exige los tres
componentes IA observados y es exclusivamente una sensibilidad.

`ocupacion_analitica(df)` asigna OFICIO_C8 a ocupados y OFICIO2_C8 (último trabajo) a desocupados.
La variante `buscada` usa OFICIO1_C8 solo para desocupados. La distinción está comprobada en
el diccionario DANE2023 guardado en esta carpeta; no son variables intercambiables.
Los inactivos y los códigos faltantes permanecen sin exposición analítica.

Ejecute `python auditar_indices.py` para regenerar catálogo normalizado, metadatos, cobertura,
comparación de ocupación anterior/buscada y exposición por cohorte. No modifica los microdatos.
Las columnas históricas `exp_*_pct` de los microdatos no representan esta normalización fija
ocupacional y no deben usarse como sustitutos de las nuevas columnas `*_pct`.

La tabla original de puntuaciones se conserva intacta. Los archivos de origen del crosswalk
no están disponibles en este checkout: la auditoría reproduce la asignación y las
normalizaciones, pero no certifica una reconstrucción independiente desde los archivos originales.
El script `build_exposicion_ia.py` comprueba esa disponibilidad y falla explícitamente si faltan.

## Documentación histórica del catálogo original

# Exposición ocupacional a IA por CIUO-08 A.C.

Tabla de puntuaciones de exposición a IA por ocupación (código CIUO-08 A.C. a 4 dígitos, la
variable `OFICIO_C8` de la GEIH), construida a partir de tres índices publicados en la literatura
económica internacional. Generada por `build_exposicion_ia.py`. Reemplaza el mapeo anterior por
gran grupo (1 dígito, ~10 valores posibles, sin calibración empírica documentada).

## Salida

`ciuo08_exposicion_ia_scores.csv` — 455 filas (una por código CIUO-08 A.C. de 4 dígitos), columnas:

- `ciuo08`, `ciuo08_desc`: código y descripción; el grupo de tres dígitos se deriva del código.
- `metodo_isco`: `identidad_4d` (436 códigos, coincidencia exacta con ISCO-08), `fallback_3d`
  (4 códigos, se usó el promedio de los códigos ISCO-08 que comparten los mismos 3 primeros
  dígitos) o `sin_match` (15 códigos, sin ninguna correspondencia — quedan con valores nulos).
- `es_fuerzas_militares`: booleano, `True` para los 3 códigos del gran grupo 0 (Oficiales,
  Suboficiales y Otros miembros de las Fuerzas Militares).
- `motivo_sin_dato`: para los 28 códigos sin ningún índice, distingue explícitamente por qué:
  `fuerzas_militares_fuera_de_onet` (3 códigos — ninguno de los tres papers cubre ocupaciones
  militares, porque ninguno usa datos de O*NET para ellas: es un vacío estructural de la fuente,
  no del crosswalk), `sin_correspondencia_isco08` (15 códigos exclusivos de Colombia sin ningún
  ISCO-08 hermano) o `sin_indice_disponible_para_este_isco08` (10 códigos que sí tienen un
  ISCO-08 válido, pero ese ISCO-08 no aparece en ninguno de los tres datasets). Nulo cuando el
  código sí tiene al menos un dato.
- `AIOE`: índice de Felten, Raj & Seamans (2021).
- `ai_score`, `software_score`, `robot_score`: índice de Webb (2020), versión O*NET-SOC (v0.1,
  valores crudos, no percentiles).
- `dv_rating_alpha/beta/gamma`: exposición a LLM según GPT-4, Eloundou et al. (2023). `gamma` es
  la variante que el paper llama "zeta" en el texto (mismo cálculo: E1+E2).
- `human_rating_alpha/beta/gamma`: la misma exposición, pero calificada por anotadores humanos.

427 de 455 códigos (93.8%) tienen al menos un índice no nulo. De los 28 sin ningún dato: 3 son
fuerzas militares (gran grupo 0 — vacío estructural, ningún índice cubre ocupaciones militares
porque ninguno de los tres papers usa datos de O*NET para ellas), 15 son códigos exclusivos de
Colombia sin ninguna correspondencia ISCO-08, y 10 tienen un ISCO-08 válido pero ese código no
aparece en ninguno de los tres datasets. Ver la columna `motivo_sin_dato` para el detalle por
código.

## Método (resumen; ver `build_exposicion_ia.py` para el detalle exacto)

1. **CIUO-08 A.C. (Colombia) → ISCO-08 (internacional):** se comparó directamente el listado de
   455 códigos de 4 dígitos de `EstructuraCIUO_08_A_C.xlsx` (DANE) contra los códigos ISCO-08 que
   aparecen en el crosswalk oficial del BLS. **436 son idénticos** (tras corregir un problema de
   ceros a la izquierda en el propio crosswalk del BLS: varios códigos de fuerzas militares
   aparecían como `110` en vez de `0110`). Los **19 restantes son subdivisiones exclusivas de
   Colombia** (mayoritariamente oficios y artesanos, gran grupo 7): para 4 de ellos se usó el
   promedio de los códigos ISCO-08 que comparten el mismo grupo de 3 dígitos como aproximación
   (`fallback_3d`); los otros 15 no tienen ningún código ISCO-08 hermano disponible y quedan sin
   dato (`sin_match`). Dos códigos de ISCO-08 (`0211`, `0315`) no tienen contraparte en Colombia y
   simplemente no se usan.
2. **ISCO-08 ↔ SOC-2010:** crosswalk oficial del BLS (`isco_soc_crosswalk.xls`), relación
   muchos-a-muchos. Cuando varios códigos SOC mapean a un mismo ISCO-08 (o viceversa), se usa el
   **promedio simple** — el mismo atajo metodológico documentado por el FMI (IMF WP 2023/216) al
   hacer este mismo cruce para su propio estudio de exposición a IA.
3. **O*NET-SOC (8 dígitos) → SOC-2010 (6 dígitos):** Webb (2020, v0.1) y Eloundou et al. (2023)
   publican sus puntuaciones a nivel O*NET-SOC, más fino que SOC. Se truncan al código SOC de 6
   dígitos (se quita el sufijo `.NN`) y se promedian los sub-códigos que comparten el mismo SOC.
4. Los tres índices se agregan de forma independiente hasta el nivel ISCO-08 y luego se asignan a
   cada CIUO-08 A.C. según el método del punto 1. **No se combinan en un solo número**: miden
   constructos distintos (AIOE = exposición general a capacidades de IA; Webb = exposición a
   robots/software/IA vía patentes; Eloundou et al. = exposición específica a LLM, con variante
   humana y variante GPT-4).

## Limitaciones conocidas (documentadas, no resueltas)

- La versión de SOC del dataset AIOE no está confirmada con cita textual primaria de los autores
  (evidencia indirecta fuerte apunta a SOC 2010, ver hallazgos de la Fase 1 de investigación).
- El promedio simple ante relaciones muchos-a-muchos (ISCO↔SOC) no pondera por tamaño de empleo;
  es una aproximación, igual que la usada por el FMI.
- Los 19 códigos exclusivos de Colombia (y en particular los 15 sin ningún match) representan una
  pérdida de granularidad real: ocupaciones que el DANE distingue explícitamente quedan sin
  puntuación propia o aproximadas por un grupo más amplio.
- No se verificó aún si `OFICIO_C8` en los microdatos GEIH usa exactamente esta versión de
  CIUO-08 A.C. sin modificaciones adicionales — pendiente de contrastar contra el diccionario de
  variables de la GEIH.

## Fuentes originales (carpetas hermanas)

- `felten_raj_seamans_2021/` — AIOE, repositorio oficial `github.com/AIOE-Data/AIOE`.
- `webb_2020/` — página de datos del autor (Notion), incluye v0.1 (O*NET-SOC) y v0.2 (occ1990dd).
- `eloundou_2023/` — repositorio oficial de OpenAI `github.com/openai/GPTs-are-GPTs`, licencia MIT.
- `crosswalks/` — `EstructuraCIUO_08_A_C.xlsx` (DANE), `isco_soc_crosswalk.xls` y
  `soc_2010_to_2018_crosswalk.xlsx` (BLS).
