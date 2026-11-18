# Datos locales y de publicación

Las bases originales, reconstrucciones históricas, microdatos imputados, indicadores y paneles se concentran físicamente aquí. El registro de la rama oficial es `../rutas.py` y su implementación está en `../regresiones/preparacion/datos/armonizados_2018_2025/rutas.py`.

- `armonizados_2018_2025` expone los anuales y paneles oficiales mediante accesos a sus fuentes físicas.
- `derivados_modelos` contiene matrices de entrada para modelos y diagnósticos.
- `GEIH`, `ECV`, `POBREZA_MONETARIA`, `tic_laboral_2018_2025` y `extensiones_historicas` conservan fuentes, diccionarios y ramas reconstruidas; no todas son la rama principal seleccionada.
- `complementarios_RLM` reúne los datos adicionales del antiguo RLM. No se fusionan con los resultados del Anexo.
- `publicacion/dashboard` contiene únicamente los agregados y la cartografía de la web.

La exclusión de Git no significa que una base pueda borrarse. Las fuentes necesarias para reconstruir y las versiones históricas tienen funciones distintas. La lista de candidatos a eliminación requiere aprobación y está en `../plan_reorganizacion/ARCHIVOS_PARA_APROBAR.md`.
