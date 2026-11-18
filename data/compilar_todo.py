#!/usr/bin/env python3
"""Compila los documentos vigentes, sin reestimar modelos externos.
Uso: python3 compilar_todo.py [principal | anexo_a | dashboard | todo]
"""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[0]))
import os
import shutil
import subprocess
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[0]
DOC_ROOT = DATA_DIR.parent
DOCUMENTOS = {
    'principal': (DOC_ROOT / 'Principal/principal.qmd', ('--to', 'all'), ('.html', '.pdf')),
    'anexo_a': (DOC_ROOT / 'Anexo_a/anexo_a.qmd', ('--to', 'html'), ('.html',)),
    'dashboard': (DOC_ROOT / 'Dashboard/dashboard.qmd', (), ('.html',)),
}


def compilar_documento(nombre, ruta_qmd, flags, exts):
    quarto = os.environ.get('QUARTO_BIN') or shutil.which('quarto')
    if not quarto:
        raise RuntimeError('Quarto no está en PATH; configure QUARTO_BIN con su ejecutable.')
    env = dict(os.environ, MPLBACKEND='Agg', QUARTO_PYTHON=sys.executable)
    print(f'Compilando {nombre}: {ruta_qmd.name}', flush=True)
    res = subprocess.run([quarto, 'render', ruta_qmd.name, *flags], cwd=ruta_qmd.parent, env=env)
    salidas = [ruta_qmd.with_suffix(ext) for ext in exts]
    correcto = res.returncode == 0 and all(p.exists() and p.stat().st_size > 0 for p in salidas)
    print('Compilación completa' if correcto else f'ERROR de compilación: {nombre}', flush=True)
    return correcto


def main():
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else 'todo'
    if arg not in (*DOCUMENTOS, 'todo'):
        print('Opciones: principal | anexo_a | dashboard | todo', file=sys.stderr)
        return 2
    nombres = DOCUMENTOS if arg == 'todo' else [arg]
    for nombre in nombres:
        ruta_qmd, flags, exts = DOCUMENTOS[nombre]
        if not compilar_documento(nombre, ruta_qmd, flags, exts):
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
