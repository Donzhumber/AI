# Auditoría de tratamiento ECV 2025 — 30 octubre 2026

El tratamiento identificable es **uso declarado de herramientas de IA como actividad en internet**, no adopción laboral ni toda IA fuera de internet. La pregunta no establece intensidad, momento de adopción ni uso en el empleo.

## Evidencia primaria y ruta

- [Formulario oficial DANE ECV 2025](https://microdatos.dane.gov.co/index.php/catalog/905/download/24644), copia local `datos/ECV/2025/diccionarios/Formulario_ECV2025.pdf`, páginas impresas/PDF 53–54: capítulo I para personas de 5 años y más. En p53, después de habilidades, quien en pregunta 2 respondió opción 5 pasa a 7. En p54 las preguntas 4–6 se reservan a quienes en pregunta 2 respondieron opciones 1–4. I6 es selección múltiple de 21 servicios/actividades y la opción 20 es IA.
- [Diccionario oficial P1084](https://microdatos.dane.gov.co/index.php/catalog/905/variable/F15/V837?name=P1084): 1 diario, 2 semanal, 3 mensual, 4 anual, 5 no utiliza internet. Confirma salto hacia I7 para no usuarios.
- [Diccionario oficial P1083S21](https://microdatos.dane.gov.co/index.php/catalog/905/variable/F15/V889?name=P1083S21): 8.115 selecciones `1`, ningún `2`, 212.928 `Sysmiss` dentro de 221.043 registros TIC. El título identifica IA, pero el texto literal/instrucción está erróneamente copiado de tenencia de celular; se usa el formulario para verificar significado y ruta.

La ausencia de marca en una casilla de selección múltiple no equivale por sí sola a no respuesta. Se comprueba pertenencia a la ruta y existencia de alguna respuesta de actividades. No debe reemplazarse todo `Sysmiss` por cero.

## Regla ejecutable

`tratamiento_ia.py` implementa `construir_tratamiento(df) -> (serie, diagnosticos)`:

1. `D=1`: `P1084` en 1–4 y `P1083S21=1`.
2. `D=0`: `P1084=5`, sin actividad contradictoria; o `P1084` en 1–4, alguna `P1083S1`…`P1083S21=1`, sin selección de IA.
3. `D=NaN`: módulo/ruta desconocida, usuarios sin ninguna actividad marcada, rutas inconsistentes y años distintos de 2025.

Conservar las 21 columnas de actividades y `P1084`. El campo padre `P1083` está vacío en los 234.804 registros integrados y no sirve como indicador de respuesta. El sufijo S21 corresponde a opción 20 del formulario; S11 es la opción residual «otro».

## Conteos no ponderados observados

Fuente integrada: `datos/imputados/ecv_geih_imputada_2025.parquet`. Se leen datos originales de ECV conservados en ese archivo; las variables laborales con sufijo `_geih` provienen de la integración/imputación.

| Universo | N | D=1 | D=0 | D faltante |
|---|---:|---:|---:|---:|
| Todos | 234804 | 8095 | 212450 | 14259 |
| Edad ECV ≥15 | 183058 | 7379 | 175679 | 0 |
| OCI_geih=1 | 106915 | 4800 | 102115 | 0 |
| PEA: OCI_geih=1 o DSI_geih=1 | 114737 | 5232 | 109505 | 0 |
| OCI_geih=1 e INGLABO_geih>0 | 102644 | 4667 | 97977 | 0 |
| OCI_geih=1 y P6920_geih en 1,2 | 105520 | 4718 | 100802 | 0 |

Estos conteos preceden filtros de exposición/instrumento, covariables y ponderadores de la estimación.

Los 165.882 usuarios `P1084` en 1–4 tienen al menos una actividad seleccionada. Los 54.663 no usuarios no tienen ninguna actividad. Los 14.259 con P1084 ausente tampoco tienen actividades. No se observan usuarios sin actividades ni contradicciones. Así, la regla cuidadosa produce los mismos ceros que el indicador ingenuo **entre personas de 15 años o más**, pero conserva correctamente la falta de módulo fuera de ese universo.

Fuente original: `datos/ECV/2025/total_ecv_2025.parquet`, N=235.350, con 221.043 respuestas P1084 y 8.115 selecciones IA, coincidentes con DANE. Sus 14.307 P1084 ausentes son exclusivamente edades 0–4 (2.208, 2.477, 2.942, 3.212 y 3.468 respectivamente). Esto verifica ausencia estructural del módulo en ese archivo, no no respuesta generalizada.

## Verificación del helper

Caso sintético comprobó IA seleccionada→1, usuario con otra actividad→0, no usuario explícito→0, módulo ausente→NaN, usuario sin actividades→NaN y no usuario con IA contradictoria→NaN. La corrección conceptual evita inventar controles en años sin pregunta, aun cuando no cambie los conteos del universo laboral 2025 observado.
