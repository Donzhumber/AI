# Diagnósticos de aprendizaje automático

La fuente vigente para el Anexo reorganizado es `resultados_indices_ml.json` y su tabla `resultados_indices_ml.csv`, generadas por `estimar_indices_ml.py`. Los restantes JSON se conservan como ejercicios de la versión anterior y no deben mezclarse con la comparación actual.

La comparación contiene AIOE como principal, Webb–IA y LLM como alternativas de IA, software y robots como extensión, y la envolvente como sensibilidad; cada indicador se estima por separado en escala percentil ocupacional fija y Min–Max. La única fuente de normalización es `datos/exposicion_ia/indices_comunes.py`. La muestra por resultado exige los cinco indicadores y educación observados, así como pesos FEX_C positivos. Para ocupados se emplea exclusivamente su ocupación actual; para desempleados, la última ocupación declarada (OFICIO2_C8). Quienes carecen de historia ocupacional puntuable quedan excluidos: la tasa no representa toda la fuerza laboral.

Se aplican cinco particiones exteriores por ocupación, sin mezcla de ocupaciones entre entrenamiento y evaluación. El R-learner de AIOE, Webb–IA y LLM utiliza tres particiones interiores; la calibración BLP se evalúa únicamente con predicciones externas. La inferencia agrupa por ocupación y usa t(G−1). No incorpora incertidumbre completa del emparejamiento ni diseño complejo de encuesta.

El tratamiento D=I×Post es determinista una vez condicionados exposición y año. Por ello no se cumple la variación residual requerida para identificar el PLR. Los coeficientes y sus valores p son diagnósticos del procedimiento; no acreditan efectos causales ni heterogeneidad causal. La varianza residual estimada refleja aproximación predictiva, no una fuente de identificación. Los modelos usan HistGradientBoostingRegressor; no son generalized random forests.

Ejecución: `OMP_NUM_THREADS=4 /usr/bin/python3 estimar_indices_ml.py`. No se usa DML para calibrar proyecciones. El archivo `modelos_ml_comunes.py` concentra el estimador y sus controles de partición. Los scripts anteriores permanecen para trazabilidad, pero la ejecución actual se realiza con el comparador de índices.
