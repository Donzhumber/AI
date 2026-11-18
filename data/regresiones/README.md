# Código y resultados

`preparacion` contiene imputación, armonización, índices y agregación del panel. `modelos` reúne los estimadores Python/Stata. `resultados` contiene coeficientes y diagnósticos y accesos a matrices centralizadas en datos. `validacion` comprueba resultados y presenta las tablas del Anexo. `historico` conserva escenarios y procedimientos que no forman parte de los modelos principales actuales.

El punto de entrada es `../reproducir.py`. La comprobación independiente está en `validacion/verificar_reorganizacion.py`. No se ha vuelto a entrenar cada modelo durante el traslado; se comprueban los resultados conservados y las fórmulas con los datos de entrada.
