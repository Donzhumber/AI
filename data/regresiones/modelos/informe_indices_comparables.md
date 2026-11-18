# Reestimación con indicadores separados


El flujo vigente produjo 910 parámetros: cinco indicadores separados percentiles, cinco Min–Max y dos envolventes. AIOE percentil es la especificación principal. Todas las comparaciones de índices de un modelo y resultado mantienen la misma muestra. Los coeficientes son asociaciones condicionales.


## Construcción y muestra


La ocupación de los ocupados es OFICIO_C8; para desempleados se utiliza OFICIO2 (última ocupación). OFICIO1 es ocupación buscada y se utiliza únicamente en sensibilidad de desempleo. Esta corrección excluye del análisis principal a desempleados sin experiencia/ocupación anterior identificable. La clasificación de cohortes usa año de nacimiento estimado y las exposiciones agregadas usan ocupados 2022 con los cinco indicadores válidos.


| resultado   |   disponible |   comun |
|:------------|-------------:|--------:|
| desempleo   |       455614 |  431601 |
| no_cotiza   |       412939 |  396064 |
| salario     |       394119 |  377991 |


DiD y DDD incluyen efectos de departamento, año, ocupación a dos dígitos y educación categórica; controles edad, edad², mujer, rural y jefe. H_edu es absorbido por los efectos educativos. TIC: uso de computador e internet del hogar; no equivale a propiedad ni adopción de IA. Los faltantes no satisfacen H=1.


## Resultados principales AIOE


| familia    | modelo               | resultado   | parametro          |      coef |       se |        p |   ci_lower |   ci_upper |   nobs |   clusters |
|:-----------|:---------------------|:------------|:-------------------|----------:|---------:|---------:|-----------:|-----------:|-------:|-----------:|
| did        | estatico             | desempleo   | exposicion_post    | -0.003413 | 0.010630 | 0.748345 |  -0.024312 |   0.017487 | 431601 |        385 |
| ddd        | H_tic                | desempleo   | exposicion_post    |  0.011762 | 0.013484 | 0.383603 |  -0.014750 |   0.038273 | 431601 |        385 |
| ddd        | H_tic                | desempleo   | triple             | -0.025844 | 0.017145 | 0.132541 |  -0.059555 |   0.007866 | 431601 |        385 |
| ddd        | H_tic                | desempleo   | exposicion_post_H1 | -0.014083 | 0.014325 | 0.326179 |  -0.042247 |   0.014082 | 431601 |        385 |
| ddd        | H_edu                | desempleo   | exposicion_post    |  0.005459 | 0.013738 | 0.691325 |  -0.021552 |   0.032470 | 431601 |        385 |
| ddd        | H_edu                | desempleo   | triple             | -0.037285 | 0.029746 | 0.210800 |  -0.095770 |   0.021200 | 431601 |        385 |
| ddd        | H_edu                | desempleo   | exposicion_post_H1 | -0.031826 | 0.025996 | 0.221607 |  -0.082939 |   0.019287 | 431601 |        385 |
| did        | estatico             | no_cotiza   | exposicion_post    |  0.016292 | 0.017876 | 0.362651 |  -0.018855 |   0.051440 | 396064 |        384 |
| ddd        | H_tic                | no_cotiza   | exposicion_post    |  0.033081 | 0.020611 | 0.109314 |  -0.007444 |   0.073607 | 396064 |        384 |
| ddd        | H_tic                | no_cotiza   | triple             | -0.028469 | 0.027974 | 0.309465 |  -0.083472 |   0.026533 | 396064 |        384 |
| ddd        | H_tic                | no_cotiza   | exposicion_post_H1 |  0.004612 | 0.029130 | 0.874283 |  -0.052662 |   0.061886 | 396064 |        384 |
| ddd        | H_edu                | no_cotiza   | exposicion_post    |  0.032034 | 0.023970 | 0.182206 |  -0.015095 |   0.079162 | 396064 |        384 |
| ddd        | H_edu                | no_cotiza   | triple             |  0.002446 | 0.050291 | 0.961241 |  -0.096436 |   0.101327 | 396064 |        384 |
| ddd        | H_edu                | no_cotiza   | exposicion_post_H1 |  0.034479 | 0.047674 | 0.469978 |  -0.059256 |   0.128214 | 396064 |        384 |
| did        | estatico             | salario     | exposicion_post    |  0.050405 | 0.032785 | 0.125015 |  -0.014057 |   0.114866 | 377991 |        383 |
| ddd        | H_tic                | salario     | exposicion_post    |  0.034355 | 0.032424 | 0.290025 |  -0.029398 |   0.098107 | 377991 |        383 |
| ddd        | H_tic                | salario     | triple             |  0.025501 | 0.042536 | 0.549186 |  -0.058134 |   0.109136 | 377991 |        383 |
| ddd        | H_tic                | salario     | exposicion_post_H1 |  0.059856 | 0.049604 | 0.228306 |  -0.037675 |   0.157387 | 377991 |        383 |
| ddd        | H_edu                | salario     | exposicion_post    |  0.052246 | 0.036945 | 0.158127 |  -0.020394 |   0.124886 | 377991 |        383 |
| ddd        | H_edu                | salario     | triple             | -0.038390 | 0.092347 | 0.677853 |  -0.219961 |   0.143182 | 377991 |        383 |
| ddd        | H_edu                | salario     | exposicion_post_H1 |  0.013856 | 0.094025 | 0.882920 |  -0.171015 |   0.198727 | 377991 |        383 |
| did        | sensibilidad_buscada | desempleo   | exposicion_post    |  0.002420 | 0.012134 | 0.842040 |  -0.021437 |   0.026276 | 437020 |        385 |
| shiftshare | estatico             | desempleo   | exposicion_post    |  0.069103 | 0.078031 | 0.382454 |  -0.089842 |   0.228048 |   1320 |         33 |
| panel      | within               | desempleo   | exposicion_post    | -0.050664 | 0.038357 | 0.195928 |  -0.128795 |   0.027468 |   1320 |         33 |
| panel      | fd                   | desempleo   | exposicion_post    | -0.084888 | 0.033529 | 0.016458 |  -0.153185 |  -0.016591 |    330 |         33 |
| shiftshare | estatico             | no_cotiza   | exposicion_post    | -0.055247 | 0.091804 | 0.551557 |  -0.242246 |   0.131753 |   1320 |         33 |
| panel      | within               | no_cotiza   | exposicion_post    |  0.019207 | 0.055800 | 0.732942 |  -0.094454 |   0.132867 |   1320 |         33 |
| panel      | fd                   | no_cotiza   | exposicion_post    |  0.018783 | 0.053855 | 0.729554 |  -0.090917 |   0.128483 |    330 |         33 |
| shiftshare | estatico             | salario     | exposicion_post    |  0.271340 | 0.183127 | 0.148199 |  -0.101677 |   0.644357 |   1320 |         33 |
| panel      | within               | salario     | exposicion_post    | -0.064876 | 0.131133 | 0.624168 |  -0.331985 |   0.202233 |   1320 |         33 |
| panel      | fd                   | salario     | exposicion_post    | -0.136238 | 0.117480 | 0.254762 |  -0.375536 |   0.103060 |    330 |         33 |


## Interpretación


En DiD estático, AIOE no muestra asociaciones distintas de cero al 5% para los tres resultados. Un contraste de 0,1 unidades equivale a −0,0341 puntos porcentuales de desempleo, +0,1629 puntos de no cotización y +0,5053% de ingreso individual (transformación exponencial); los intervalos incluyen cero. No es evidencia de ausencia de asociación, sino incertidumbre compatible con ambos signos.


Ninguna triple interacción AIOE con TIC o educación superior resulta significativa al 5%. No puede afirmarse que esos habilitadores mitiguen efectos de IA. Deben interpretarse conjuntamente la asociación sin H, el diferencial triple y la suma para H=1; la significancia de una suma requiere la covarianza entre términos.


Los modelos territoriales AIOE estáticos tampoco rechazan cero al 5%. En Within las tres asociaciones AIOE son imprecisas. La diferencia larga de desempleo sí es negativa (−0,084888; p=0,01646): por 0,1 unidades de exposición basal, −0,8489 puntos porcentuales en el cambio de tasa 2025–2022. La discrepancia con Within impide presentarla como resultado uniforme del panel. No cotización e ingreso medio no rechazan cero en diferencias largas.


La exposición de cohortes/territorios se basa en ocupados, mientras la tasa de desempleo usa toda la fuerza laboral de la cohorte; ese coeficiente no equivale al DiD individual restringido a ocupación identificable. El logaritmo del ingreso medio de cohorte tampoco es el promedio de logaritmos individuales.


## Indicadores complementarios y automatización


| familia    | modelo   | resultado   | indice       |      coef |       se |        p |
|:-----------|:---------|:------------|:-------------|----------:|---------:|---------:|
| did        | estatico | desempleo   | aioe_pct     | -0.003413 | 0.010630 | 0.748345 |
| did        | estatico | desempleo   | webb_ia_pct  |  0.002385 | 0.008811 | 0.786790 |
| did        | estatico | desempleo   | llm_pct      | -0.000522 | 0.011993 | 0.965318 |
| did        | estatico | desempleo   | software_pct |  0.008952 | 0.009033 | 0.322303 |
| did        | estatico | desempleo   | robots_pct   |  0.004572 | 0.010118 | 0.651617 |
| did        | estatico | no_cotiza   | aioe_pct     |  0.016292 | 0.017876 | 0.362651 |
| did        | estatico | no_cotiza   | webb_ia_pct  |  0.003839 | 0.018095 | 0.832078 |
| did        | estatico | no_cotiza   | llm_pct      |  0.019972 | 0.019228 | 0.299609 |
| did        | estatico | no_cotiza   | software_pct |  0.003489 | 0.020725 | 0.866392 |
| did        | estatico | no_cotiza   | robots_pct   | -0.010124 | 0.017973 | 0.573567 |
| did        | estatico | salario     | aioe_pct     |  0.050405 | 0.032785 | 0.125015 |
| did        | estatico | salario     | webb_ia_pct  | -0.057896 | 0.030188 | 0.055874 |
| did        | estatico | salario     | llm_pct      |  0.050305 | 0.035443 | 0.156615 |
| did        | estatico | salario     | software_pct | -0.085562 | 0.034935 | 0.014768 |
| did        | estatico | salario     | robots_pct   | -0.080857 | 0.036472 | 0.027213 |
| shiftshare | estatico | desempleo   | aioe_pct     |  0.069103 | 0.078031 | 0.382454 |
| panel      | within   | desempleo   | aioe_pct     | -0.050664 | 0.038357 | 0.195928 |
| shiftshare | estatico | desempleo   | webb_ia_pct  | -0.041405 | 0.089345 | 0.646192 |
| panel      | within   | desempleo   | webb_ia_pct  |  0.050433 | 0.018403 | 0.009950 |
| shiftshare | estatico | desempleo   | llm_pct      |  0.079194 | 0.077663 | 0.315513 |
| panel      | within   | desempleo   | llm_pct      | -0.027351 | 0.051656 | 0.600127 |
| shiftshare | estatico | desempleo   | software_pct | -0.056758 | 0.087136 | 0.519456 |
| panel      | within   | desempleo   | software_pct |  0.058520 | 0.017301 | 0.001911 |
| shiftshare | estatico | desempleo   | robots_pct   | -0.076649 | 0.073263 | 0.303300 |
| panel      | within   | desempleo   | robots_pct   |  0.063257 | 0.035589 | 0.085006 |
| panel      | fd       | desempleo   | aioe_pct     | -0.084888 | 0.033529 | 0.016458 |
| panel      | fd       | desempleo   | webb_ia_pct  |  0.074330 | 0.019841 | 0.000710 |
| panel      | fd       | desempleo   | llm_pct      | -0.073453 | 0.046130 | 0.121151 |
| panel      | fd       | desempleo   | software_pct |  0.084214 | 0.018166 | 0.000057 |
| panel      | fd       | desempleo   | robots_pct   |  0.097086 | 0.031518 | 0.004227 |
| shiftshare | estatico | no_cotiza   | aioe_pct     | -0.055247 | 0.091804 | 0.551557 |
| panel      | within   | no_cotiza   | aioe_pct     |  0.019207 | 0.055800 | 0.732942 |
| shiftshare | estatico | no_cotiza   | webb_ia_pct  |  0.209818 | 0.090063 | 0.026293 |
| panel      | within   | no_cotiza   | webb_ia_pct  |  0.072472 | 0.031383 | 0.027537 |
| shiftshare | estatico | no_cotiza   | llm_pct      |  0.004950 | 0.103984 | 0.962326 |
| panel      | within   | no_cotiza   | llm_pct      |  0.013457 | 0.073826 | 0.856513 |
| shiftshare | estatico | no_cotiza   | software_pct |  0.159557 | 0.080147 | 0.055101 |
| panel      | within   | no_cotiza   | software_pct |  0.053450 | 0.030450 | 0.088767 |
| shiftshare | estatico | no_cotiza   | robots_pct   |  0.041759 | 0.084629 | 0.625075 |
| panel      | within   | no_cotiza   | robots_pct   |  0.006653 | 0.046493 | 0.887119 |
| panel      | fd       | no_cotiza   | aioe_pct     |  0.018783 | 0.053855 | 0.729554 |
| panel      | fd       | no_cotiza   | webb_ia_pct  |  0.077011 | 0.031224 | 0.019193 |
| panel      | fd       | no_cotiza   | llm_pct      |  0.003493 | 0.079094 | 0.965053 |
| panel      | fd       | no_cotiza   | software_pct |  0.064794 | 0.028836 | 0.031668 |
| panel      | fd       | no_cotiza   | robots_pct   |  0.021781 | 0.042959 | 0.615617 |
| shiftshare | estatico | salario     | aioe_pct     |  0.271340 | 0.183127 | 0.148199 |
| panel      | within   | salario     | aioe_pct     | -0.064876 | 0.131133 | 0.624168 |
| shiftshare | estatico | salario     | webb_ia_pct  | -0.302489 | 0.183141 | 0.108382 |
| panel      | within   | salario     | webb_ia_pct  | -0.170514 | 0.080803 | 0.042746 |
| shiftshare | estatico | salario     | llm_pct      |  0.271843 | 0.217695 | 0.220820 |
| panel      | within   | salario     | llm_pct      | -0.084404 | 0.225571 | 0.710739 |
| shiftshare | estatico | salario     | software_pct | -0.297259 | 0.184941 | 0.117810 |
| panel      | within   | salario     | software_pct | -0.113563 | 0.082505 | 0.178241 |
| shiftshare | estatico | salario     | robots_pct   | -0.277531 | 0.188849 | 0.151436 |
| panel      | within   | salario     | robots_pct   | -0.003100 | 0.117674 | 0.979149 |
| panel      | fd       | salario     | aioe_pct     | -0.136238 | 0.117480 | 0.254762 |
| panel      | fd       | salario     | webb_ia_pct  | -0.198354 | 0.083061 | 0.023011 |
| panel      | fd       | salario     | llm_pct      | -0.201902 | 0.218325 | 0.362004 |
| panel      | fd       | salario     | software_pct | -0.146047 | 0.078391 | 0.071653 |
| panel      | fd       | salario     | robots_pct   |  0.011291 | 0.092562 | 0.903672 |


Las diferencias entre indicadores se reportan íntegramente; no se selecciona una medida por su valor p. Estas comparaciones son exploratorias y los valores p no corrigen multiplicidad. Los indicadores Min–Max y envolventes están en el CSV completo. No deben compararse magnitudes sin reconocer su escala.


## Verificación


Se replicaron con Stata 48 coeficientes principales AIOE: DiD estático/dinámico, DDD (asociación sin H, triple y suma), shift-share estático/dinámico, Within y FD. Diferencias máximas: coeficiente 2,39×10⁻¹²; error estándar 8,05×10⁻⁹; p 2,95×10⁻⁸; muestras y clusters idénticos. Las extensiones no se presentan como replicadas individualmente en Stata. `verificar_indices_comparables.py` comprueba finitud, rangos, intervalos, muestra común, 33 departamentos, 330 cohortes y la réplica.


Un solo año previo impide comprobar tendencias paralelas. WLS territorial no es IV. CR1 con t(G−1) no incorpora toda la incertidumbre por emparejamiento ni el diseño completo de encuesta. R² es total. Los scripts/resultados anteriores permanecen etiquetados como estrategia histórica y no son la fuente principal del Anexo reorganizado.