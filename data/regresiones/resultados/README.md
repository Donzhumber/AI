# Estimaciones sobre bases armonizadas

Colección oficial actualizada el 4 de noviembre de 2026. Las entradas se resuelven mediante `../../rutas.py`. Los resultados de las rutas tradicionales del proyecto son enlaces relativos a los archivos de esta carpeta, evitando copias divergentes.

## Reproducción

Desde `Document`, ejecutar `python3 regresiones/preparacion/datos/armonizados_2018_2025/scripts/reproducir_modelos.py --todo` para reconstruir las muestras y estimar las familias clásicas, su réplica Stata, DML-DiD, panel de TIC con 9.999 réplicas, R-learner y revisiónDML-IV. Requiere Python con numpy,pandas,pyarrow,scipy,scikit-learn,statsmodels y una instalación funcional de Stata para las réplicas y selecciónFE/RE.

`--certificar` verifica las salidas existentes sin volver a estimar. La colección de bases canónicas debe construirse primero mediante el procedimiento del directorio superior.

## Productos

- `clasicos`:982 coeficientes e índices basales;54 estimaciones principales replicadas con Stata.
- `dml_did`:15 contrastes sobre 330 cohortes y 33 departamentos.
- `panel_tic`:efectos fijos, F de cohorte, Hausman, inferencia agrupada, bootstrap y residuos.
- `cate`:R-learner de pendientes exploratorias, BLPy promedios de perfiles. La muestra usa el catálogo fijo y última ocupación de desocupados. No es CLAN formal ni CATE causal identificado.
- `iv`:revisión DML-IV 2025. La armonización conserva los resultados por identidad exacta del hash del anual 2025 y del estimador; el ejecutor permite reconstruir todas las variantes.
- `revision_20261104`:versiones contrastadas y comparaciones antes/después. Son material de auditoría, no entradas alternativas de estimación.
- `logs`:registros de las ejecuciones efectivamente realizadas.

`certificacion_modelos.json` contiene huellas de entradas y código, cifras ycomprobaciones. `resumen_resultados_armonizados.json` reúne los números para la narrativa. Los manifiestos no acreditan exogeneidad, independencia condicional delmatching ni efectos causales.

Las convenciones no cambiaron las ecuaciones: el cambio principal afecta el TIC de 2021 en el panel ampliado y la preparación del input del R-learner. Las diferencias numéricas deben interpretarse junto con los supuestos y límites del Anexo.
