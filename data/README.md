# Document · estructura en 4 carpetas

`Document/` organiza el proyecto en cuatro carpetas de primer nivel:

- `Principal/`: artículo científico (`principal.qmd`, `principal.html`, `principal.pdf`).
- `Anexo_a/`: anexo metodológico y econométrico (`anexo_a.qmd`, `anexo_a.html`, `figuras/`).
- `Dashboard/`: tablero interactivo local y edición web (`dashboard.qmd`, `dashboard_publico.qmd`, servidor HTTP).
- `data/`: datos (`datos/`), códigos y resultados econométricos (`regresiones/`), bibliografía compartida (`references.bib`, `apa.csl`) y coordinadores (`rutas.py`, `actualizar_todo.py`, `compilar_todo.py`, `reproducir.py`, `preparar_web.py`).

Ejecutar desde `Document/data/`: `python3 reproducir.py verificar`, `python3 reproducir.py documentos` o `python3 compilar_todo.py`.
