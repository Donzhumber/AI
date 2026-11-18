# Inteligencia artificial y mercado laboral en Colombia

Artículo, anexo metodológico, dashboard y procedimientos de estimación del proyecto.

## Organización

| Carpeta | Contenido |
| --- | --- |
| `Principal/` | Artículo científico en Quarto, HTML y PDF. |
| `Anexo_a/` | Anexo metodológico y econométrico, HTML y figuras. |
| `Dashboard/` | Dashboard completo local, edición pública con agregados y generadores. |
| `data/` | Coordinadores, bibliografía, código de preparación, modelos y resultados. |
| `data/datos/` | Bases locales e insumos públicos seleccionados. |

## Consulta local

Desde la raíz del repositorio

```sh
python3 -m http.server 8008 --bind 127.0.0.1
```

Abrir `http://127.0.0.1:8008/Principal/principal.html`,
`http://127.0.0.1:8008/Anexo_a/anexo_a.html` o
`http://127.0.0.1:8008/Dashboard/dashboard_publico.html`.
Los módulos del dashboard requieren HTTP y conexión para algunas bibliotecas externas.

El dashboard completo `Dashboard/dashboard.html` incluye consultas a microdatos locales. La edición pública utiliza los agregados incluidos en el repositorio. Las dos ediciones tienen distinto alcance.

## Reproducción

Instalar las dependencias de `requirements.txt`, Quarto y, para los procedimientos correspondientes, una instalación funcional de Stata. Desde `data/`

```sh
python3 reproducir.py verificar
python3 reproducir.py documentos
python3 preparar_web.py --render
```

Las bases completas, archivos Stata, Parquet y descargas DANE no se incluyen en Git. Deben colocarse en `data/datos/` siguiendo el registro `data/rutas.py` y los procedimientos de preparación. Los agregados públicos y el catálogo ocupacional seleccionado sí están incluidos. La ausencia de microdatos en Git no implica que hayan sido borrados del equipo.

`verificar` comprueba productos existentes y no vuelve a entrenar todos los modelos. Las hipótesis y límites de interpretación se documentan en el anexo. Preparar el sitio con `preparar_web.py` no lo publica automáticamente.

## Lectura en línea

La publicación web utiliza GitHub Pages y ofrece estos accesos:

- [Inicio](https://donzhumber.github.io/AI/).
- [Artículo principal](https://donzhumber.github.io/AI/Principal/principal.html).
- [Anexo metodológico](https://donzhumber.github.io/AI/Anexo_a/anexo_a.html).
- [Dashboard público](https://donzhumber.github.io/AI/Dashboard/dashboard.html).

El flujo `.github/workflows/pages.yml` publica los HTML compilados y los agregados seleccionados cuando se actualizan en `main`. La preparación del sitio no reestima los modelos ni ejecuta Quarto en GitHub. La compilación de los documentos se realiza con los datos locales antes de subir sus versiones actualizadas. El dashboard en línea corresponde a la edición pública basada en agregados.

## Anotaciones durante la lectura

El botón **Anotaciones** permite guardar comentarios generales o sobre un texto seleccionado en el artículo, el anexo y el dashboard. Las notas y los borradores se conservan en el navegador del dispositivo y no se envían al repositorio ni se sincronizan automáticamente.

Para trasladarlas a otro equipo, usar **Exportar JSON** y guardar el archivo en Archivos, iCloud u otro medio personal. En el otro equipo, abrir el mismo sitio y elegir **Importar notas**. Las importaciones se combinan por identificador y conservan las versiones más recientes. **Descargar texto** genera un archivo Markdown con el fragmento, la sección y el comentario para revisar e incorporar las observaciones posteriormente al QMD. Las anotaciones no modifican por sí solas el documento original.

La prueba de las anotaciones se reproduce con `node data/web/verificar_anotaciones.mjs` después de preparar el sitio. Requiere Node 22 o superior y Chrome; `CHROME_BIN` permite indicar su ruta. Utiliza un perfil temporal aislado.
