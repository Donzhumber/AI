# -*- coding: utf-8 -*-
"""Reproduce la colección común, los modelos y las publicaciones vigentes.
Uso: python3 actualizar_todo.py [todo|datos|indices|modelos|ml|dashboard|verificar|documentos]
No reconstruye descargas DANE ni inventa equivalencias históricas.
"""

# Raíz portable de data para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[0]))
from pathlib import Path
import argparse, os, subprocess, sys

BASE = Path(__file__).resolve().parents[0]
DOC_ROOT = BASE.parent
CANON = BASE / 'datos/armonizados_2018_2025'
ML = BASE / 'regresiones/modelos/05_DML_CausalForest'
DASH = DOC_ROOT / 'Dashboard'
ENV = dict(os.environ, OMP_NUM_THREADS='4', OPENBLAS_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1', MPLCONFIGDIR='/tmp/anexo_armonizado_mpl', PYTHONDONTWRITEBYTECODE='1')


def py(path, *args):
    subprocess.run([sys.executable, str(path), *args], cwd=BASE, env=ENV, check=True)


def datos():
    py(BASE / 'regresiones/preparacion/datos/armonizados_2018_2025/scripts/construir_coleccion.py')


def indices():
    py(BASE / 'regresiones/preparacion/datos/exposicion_ia/verificar_indices.py')


def modelos():
    py(BASE / 'regresiones/modelos/ejecutar_modelos_armonizados.py', '--todo')


def ml():
    for p in ['estimar_dml_did_continuo.py', 'preparar_microdatos_2021_2025.py', 'estimar_cate_armonizado.py', 'revision_53_20261030/ejecutar_revision.py', 'revision_53_20261030/verificar_revision.py']:
        py(ML / p)


def dashboard():
    for name in ['generar_cuadrantes_anexo.py', 'generar_perfiles_uso_ia_2025.py', 'generar_catalogo_multianual.py']:
        py(DASH / name)


def verificar():
    py(BASE / 'regresiones/preparacion/datos/armonizados_2018_2025/scripts/verificar_coleccion.py')
    py(BASE / 'regresiones/validacion/armonizacion_2018_2025/evaluar_integracion.py')
    py(BASE / 'regresiones/validacion/armonizacion_2018_2025/evaluar_panel.py')
    py(BASE / 'regresiones/validacion/armonizacion_2018_2025/verificar_soporte_panel.py')
    py(BASE / 'regresiones/modelos/ejecutar_modelos_armonizados.py', '--certificar')


def documentos():
    py(BASE / 'regresiones/validacion/armonizacion_2018_2025/evaluar_panel.py')
    for directory, name, fmt in [
        (DOC_ROOT / 'Principal', 'principal.qmd', ['--to', 'all']),
        (DOC_ROOT / 'Anexo_a', 'anexo_a.qmd', ['--to', 'html']),
        (DASH, 'dashboard.qmd', []),
    ]:
        subprocess.run(['quarto', 'render', name, *fmt], cwd=directory, env=ENV, check=True)


if __name__ == '__main__':
    steps = {'datos': datos, 'indices': indices, 'modelos': modelos, 'ml': ml, 'dashboard': dashboard, 'verificar': verificar, 'documentos': documentos}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('etapa', nargs='?', default='todo', choices=['todo', *steps])
    args = parser.parse_args()
    if args.etapa == 'todo':
        for f in [datos, indices, modelos, dashboard, verificar, documentos]:
            f()
    else:
        steps[args.etapa]()
