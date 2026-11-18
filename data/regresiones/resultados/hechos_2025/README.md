# Hechos estilizados de exposición ocupacional en 2025

Ejecutar desde la raíz del proyecto

```sh
MPLCONFIGDIR=/tmp/mpl_hechos_2025 python3 neurona/quarto/Hechos_estilizados_2025/generar_hechos.py
```

Requiere Python, pandas, NumPy, PyArrow y Matplotlib. El script sobrescribe únicamente sus resultados en esta carpeta, no las bases de origen.

## Definiciones

Se utilizan AIOE percentil y exposición a robots de Webb percentil tal como están guardados en `indices_normalizados_referencia.csv`. No se recalculan rangos. Los cortes son las medianas no ponderadas del catálogo común de 426 ocupaciones, ambas iguales a 0,5. Un valor igual al corte pertenece al grupo alto. No se interpretan los cuadrantes como sustitución o complementariedad ni como probabilidades causales.

Se usan factores ECV `FEX_C` finitos y positivos de la base integrada de 2025. La ocupación es la actual imputada para ocupados y la última imputada para desocupados, mediante `ocupacion_analitica`. Los desocupados sin historia ocupacional identificable no se imputan por promedio ni por ocupación buscada. Las coberturas se calculan por separado sobre todos los ocupados o desocupados con peso válido, antes de exigir ambos índices.

Los porcentajes de cuadrantes y de ocupación usan exclusivamente personas con ambos índices, por lo que suman cien dentro de cada condición laboral cubierta. La tasa descriptiva de desempleo por cuadrante es la masa de desocupados dividida entre ocupados más desocupados. No equivale a una probabilidad de perder el empleo ni representa toda la fuerza laboral excluida por falta de exposición.

La no cotización se calcula entre ocupados con respuesta pensional uno o dos, tomando como numerador quienes responden dos. No es una medida oficial de informalidad. El ingreso es la mediana ponderada del ingreso laboral positivo entre ocupados, en pesos de octubre de 2025. Los denominadores válidos de pensiones e ingreso se conservan en la tabla de cuadrantes.

## Archivos

Los porcentajes rojos de la figura distribuyen a los ocupados clasificables que no cotizan entre los cuatro cuadrantes y suman cien. Se rotulan como informalidad aproximada por no cotización pensional, no como medición oficial. Su denominador es el total expandido de no cotizantes clasificables, no los ocupados de cada cuadrante. La tasa interna `no_cotizacion_pct` de la tabla se conserva sin cambios. La nueva columna `participacion_no_cotizantes_pct` contiene la distribución roja. En la figura se aplica redondeo por restos mayores a dos decimales para que cada serie visible sume exactamente 100,00; los archivos conservan la precisión completa.

* `cobertura_2025.csv` contiene conteos, masas y coberturas por condición laboral.
* `cuadrantes_2025.csv` contiene composiciones, tasas y mediana de ingreso.
* `ocupaciones_2025.csv` contiene todas las ocupaciones observadas y sus participaciones dentro del universo y del cuadrante.
* `principales_ocupaciones_2025.csv` contiene las cinco ocupaciones de mayor peso de cada cuadrante y condición laboral más el resto. Los empates se ordenan por código.
* `sensibilidad_cortes_2025.csv` compara cortes simultáneos de 0,4 y 0,6 con el corte principal. El porcentaje de cambio se refiere a personas ponderadas que cambian de cuadrante.
* `exposicion_cuadrantes_2025.png` muestra una burbuja por ocupación en cada condición laboral. Su área, no su radio, representa la participación ponderada dentro del universo cubierto de ese panel. Los porcentajes indican la composición por cuadrante, no tasas de desempleo.
* `metadatos.json` registra definiciones, cortes, hashes de fuentes y equivalencia con la clasificación por medianas de mínimo y máximo.

Los cortes alternativos son decisiones descriptivas. Cambiar la normalización a mínimo y máximo usando sus propias medianas produce la misma clasificación de las 426 ocupaciones. Esto no implica que usar 0,5 en ambas escalas produzca los mismos grupos.

Las comprobaciones automáticas exigen masas conciliadas, composiciones que suman cien y equivalencia de clasificación por medianas. No incorporan diseño muestral complejo ni incertidumbre de imputación; los resultados son descriptivos de una base sintética.
