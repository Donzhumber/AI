# Evaluación transversal reproducible

## Ejecución completa de ambas secciones

Desde la raíz del proyecto ejecutar con las bases locales disponibles

```sh
python3 Document/regresiones/validacion/evaluacion_transversal/ejecutar.py
```

Para recalcular y regenerar también el documento

```sh
python3 Document/regresiones/validacion/evaluacion_transversal/ejecutar.py --render
```

Se requieren Python y los paquetes de `requirements.txt`; la opción `--render` requiere además Quarto y su kernel Python configurado. El comando completo ejecuta ambos scripts para 2022–2025, verifica la reproducción y registra versiones y hashes de los scripts en `salidas/ejecucion.json`. No usa Internet ni modifica microdatos. Los JSON y la figura de `salidas` alimentan directamente las tablas de ambas secciones del QMD. Renderizar el QMD por separado solo lee esas salidas y no repite la imputación.

Mantener la estructura del proyecto, los módulos estadísticos importados y los diagnósticos originales usados como referencia. Los insumos son `datos/GEIH/AÑO/total_son_full_AÑO.parquet`, `datos/ECV/AÑO/total_ecv_AÑO.parquet`, `datos/imputados/ecv_geih_imputada_AÑO.parquet` y los JSON originales de `datos/imputados/diagnosticos`. No se incluyen copias de microdatos en esta carpeta.

## Solo coherencia, Hellinger y densidades

Desde la raíz del proyecto ejecutar

```sh
python3 Document/regresiones/validacion/evaluacion_transversal/diagnosticos_anuales.py
```

Puede limitarse la ejecución con `--years 2023`. Requiere Python 3, pandas, numpy, pyarrow, scipy, matplotlib y seaborn. Las funciones de armonización educativa, validación de formato ocupacional e IPC se importan de los scripts locales de `auditoria/correcciones` para no duplicar sus reglas.

El script lee exclusivamente las bases originales GEIH SON, ECV y las bases integradas de `datos/imputados`. No vuelve a ejecutar el emparejamiento ni modifica esas bases. Escribe resultados y figura en `salidas`. La reproducción del emparejamiento completo sigue siendo responsabilidad de `auditoria/correcciones/preparar_integracion.py`, que no se ejecuta aquí porque altera bases y otros productos.

## Salidas y criterios

- `coherencia_anual.json` aplica a cada año las siete comprobaciones originalmente limitadas a 2023. Sensibilidad respecto de actividad principal, acuerdo y correlación son no ponderados para conservar exactamente el procedimiento original. La correlación compara ingreso per cápita imputado con el nativo ECV positivo, excluye pares ausentes y cuenta personas, no hogares únicos. No mide acierto individual ni ingreso laboral.
- `hellinger_anual.json` distingue GEIH frente a ECV original y frente a ECV integrada. El script original usaba ECV original pese a que el texto describía la base integrada. Se conservan ambas comparaciones para trazabilidad. Cada distribución se normaliza sobre categorías observadas y factores finitos positivos, con armonización educativa idéntica. Las covariables pertenecen al receptor, no son atributos laborales transferidos.
- `densidad_ingresos_2022_2025.png` aplica KDE ponderado al logaritmo natural del ingreso laboral positivo de ocupados, en precios de octubre de 2025. Usa IPC y reglas originales, con factores GEIH o ECV según corresponda. `densidad_resumen.json` documenta tamaños, factores y medias logarítmicas; no es una validación del ingreso individual. Los ceros y ausentes quedan fuera de las curvas.
- `reproduccion_2023.json` compara las cifras publicadas de coherencia y Hellinger con el recálculo a la misma precisión. El script falla si no coinciden. La figura se regenera con los mismos datos y método, no se exige igualdad binaria de la imagen por diferencias de tamaño y diseño.
- `insumos_diagnosticos.json` registra rutas relativas, tamaños y marcas temporales de los archivos efectivamente leídos.

Los cuatro años utilizan las mismas reglas. Ningún diagnóstico prueba independencia condicional, precisión individual o validez causal. No se calculan errores estándar que incorporen incertidumbre del emparejamiento. La afinidad agregada no valida relaciones entre variables nunca observadas conjuntamente.

## Reproducción de selección de donantes y evaluaciones laborales

```sh
python3 Document/regresiones/validacion/evaluacion_transversal/reproducir_integracion.py
```

El script complementario vuelve a calcular la selección de donantes, la sensibilidad laboral y los diagnósticos de empates, compara los donantes con las bases integradas existentes y guarda sus resultados en la misma carpeta `salidas`, sin sobrescribir las bases. Admite `--anios` para seleccionar años. Las funciones estadísticas se reutilizan desde `auditoria/validacion_laboral` y `auditoria/correcciones`; esas carpetas deben mantenerse junto a esta carpeta reproducible.

Sus salidas `fuentes_reproducidas.json` y `matching_reproducido.json` contienen tamaños, exclusiones, reutilización de donantes, ampliación territorial y tasas recalculadas. `metricas.json`, `matrices_confusion.json`, `variables_reservadas.json` y `rutas_ocupacion.json` conservan los esquemas originales de la validación 6D/5D para cada año. `empates.json` reproduce la alternativa de donante a igual distancia. `comprobacion_reproduccion.json` registra las pruebas de igualdad con los punteros de las bases y los diagnósticos publicados, con tolerancia exclusivamente al redondeo JSON. Una divergencia detiene la ejecución y no modifica ningún archivo original. Una ejecución parcial guarda únicamente los años solicitados en estas salidas, por lo que antes de publicar deben ejecutarse ambos scripts para los cuatro años.
