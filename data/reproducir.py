"""Punto de entrada portable. Ver --help para etapas."""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[0]))
from pathlib import Path
import argparse, subprocess, sys

DATA_DIR = Path(__file__).resolve().parent
DOC_ROOT = DATA_DIR.parent


def python(path, *args):
    subprocess.run([sys.executable, str(path), *args], cwd=DATA_DIR, check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('etapa', choices=['verificar', 'documentos', 'dashboard', 'modelos', 'datos', 'web', 'todo'])
    a = p.parse_args()
    if a.etapa in ['datos', 'todo']:
        python(DATA_DIR / 'regresiones/preparacion/datos/armonizados_2018_2025/scripts/construir_coleccion.py')
    if a.etapa in ['modelos', 'todo']:
        python(DATA_DIR / 'regresiones/modelos/ejecutar_modelos_armonizados.py', '--todo')
    if a.etapa in ['verificar', 'todo']:
        python(DATA_DIR / 'regresiones/validacion/verificar_reorganizacion.py')
    if a.etapa in ['dashboard', 'todo']:
        for f in ['generar_cuadrantes_anexo.py', 'generar_perfiles_uso_ia_2025.py', 'generar_catalogo_multianual.py']:
            python(DOC_ROOT / 'Dashboard' / f)
    if a.etapa in ['documentos', 'todo']:
        for folder, f, flags in [
            ('Principal', 'principal.qmd', ['--to', 'all']),
            ('Anexo_a', 'anexo_a.qmd', ['--to', 'html']),
            ('Dashboard', 'dashboard.qmd', []),
        ]:
            subprocess.run(['quarto', 'render', f, *flags], cwd=DOC_ROOT / folder, check=True)
    if a.etapa in ['web', 'todo']:
        python(DATA_DIR / 'preparar_web.py', '--render')


if __name__ == '__main__':
    main()
