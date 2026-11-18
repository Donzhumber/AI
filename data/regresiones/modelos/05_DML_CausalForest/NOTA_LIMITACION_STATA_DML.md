# Alcance de la réplica y de los diagnósticos ML

Actualización26-09-2026. Se replica en Stata la referencia WLS con FEX_C, exposición basal y efectos categóricos de departamento, año, ocupación2d y educación. No se ha implementado una réplica Stata del boosting ni del R-learner.

El problema principal es de identificación: D=I×Post queda determinado por las covariables I/año, de modo que el PLR no tiene variación residual poblacional de tratamiento. El residuo del learner representa error predictivo. Los coeficientes e intervalos conservados son diagnósticos exploratorios y no estimaciones causales identificadas.

Los nuisance learners usan GroupKFold por ocupación4d. El R-learner recibe residuos de cross-fitting interno entrenado sin las ocupaciones del fold externo; BLP evalúa las predicciones externas. Este cambio evita reutilizar outcomes de evaluación, pero no subsana la falta de identificación PLR. La diferencia WLS−DML no es una medición del sesgo de WLS.
