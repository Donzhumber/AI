# Revisión independiente del Anexo reorganizado, secciones 3 y 4

Se contrastaron las ecuaciones, universos, controles y extracción de tablas de `Anexo_A.qmd` y `publicacion_anexo.py` con los códigos y las salidas vigentes.

- DiD y DDD: educación categórica, exposición basal, efectos año/departamento/ocupación2, controles individuales, peso FEX_C y agrupación CIUO4 coherentes. DDD de educación omite su columna de nivel porque está absorbida, manteniendo las interacciones inferiores.
- Shift-share: 1.320 cohortes-año, exposición departamental 2022, efectos cohorte/año, controles del panel, peso PET y 33 clusters; no IV.
- Within: exposición de la propia cohorte en 2022 y especificación coincidente. FD: 330 diferencias 2025−2022, peso medio PET de extremos. No confundir diferencias largas con primeras diferencias anuales consecutivas.
- Las cinco tablas estáticas/comparativas contienen cinco índices separados por tres resultados (15 filas). Las dinámicas AIOE contienen nueve filas. La sensibilidad DiD contiene siete índices por tres resultados (21 filas). No hay duplicación ni extracción de resultados históricos.
- AIOE salarial DiD 2023 sí es positivo con p=0,02491, pero el test conjunto p=0,1190 y la diferencia 2025−2023 p=0,06865 no sustentan persistencia o aceleración. El texto reconoce esta distinción.
- Ninguna triple AIOE es significativa al 5%. FD de desempleo es negativo significativo y Within no lo es. El texto no convierte estas diferencias en evidencia causal.
- DML: fórmula residualizada ponderada coincide con el helper. Particiones externas5/internas3 y categorización coinciden. La advertencia de determinismo D dado I/año es correcta.

Precisiones remitidas al integrador:

1. En interpretaciones salariales del panel/territorio, sustituir “ingreso laboral positivo” por “ingreso laboral medio de cohorte”. En DiD, exp(0,1β) expresa una razón de ingresos geométricos condicionales; no garantiza el mismo porcentaje para la media aritmética sin supuestos sobre retransfomación.
2. La salida ML denominada `var_D_residual` calcula la media ponderada de D residual al cuadrado, no su varianza centrada. La tabla/texto deben identificarla como segundo momento residual; no requiere reestimación.
3. Explicitar el umbral R-learner: valor absoluto del residuo de tratamiento mayor que 10⁻⁴.
4. Las dinámicas de índices complementarios y Min–Max de DDD/panel permanecen en el CSV completo, conforme informa el texto. Es una decisión de presentación, no ausencia de estimación. Si se desea autosuficiencia impresa completa, pueden añadirse tablas de detalle al material técnico, pero no deben mezclarse con las tablas AIOE principales.

La comprobación Stata cubre 48 contrastes principales AIOE; no atribuir esa réplica independiente a los 910 parámetros ni a ML. Las extensiones comparten el estimador validado y controles programáticos de finitud, intervalos, cobertura y muestra común.
