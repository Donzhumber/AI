# Estimaciones de aprendizaje automático

Principal y Anexo A utilizan las siguientes estimaciones de la colección armonizada GEIH–ECV.

| Modelo | Código vigente | Salidas de publicación |
| --- | --- | --- |
| DML-DiD continuo | [Estimación con el panel de cohortes](estimar_dml_did_continuo.py) | [Contrastes y diagnósticos](../../resultados/dml_did/) |
| DML-IV para uso reportado de IA en 2025 | [Estimación y diagnósticos de identificación](revision_53_20261030/ejecutar_revision.py) | [Resultados de AIOE y sensibilidades](../../resultados/iv/) |
| Heterogeneidad exploratoria | [Preparación de microdatos](preparar_microdatos_2021_2025.py) y [estimación con R-learner](estimar_cate_armonizado.py) | [Calibración y perfiles](../../resultados/cate/) |

Las tablas de ambos documentos leen las salidas guardadas mediante el [código de publicación](../../validacion/auditoria_qmd_20260926/publicacion_anexo.py). El [manifiesto de modelos](../../resultados/certificacion_modelos.json) registra las huellas de los scripts y de las bases empleadas.

El [ejecutor de modelos armonizados](../ejecutar_modelos_armonizados.py) coordina la reproducción de las estimaciones y sus comprobaciones.
