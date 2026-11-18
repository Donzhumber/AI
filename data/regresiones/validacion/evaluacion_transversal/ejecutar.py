"""Reproduce las secciones 2.1.4 y 2.1.5 sin modificar los microdatos."""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[3]))
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys

CARPETA = (Path(__file__).resolve().parents[3] / 'regresiones/validacion/evaluacion_transversal')
BASE = (Path(__file__).resolve().parents[3])
PAQUETES = ['numpy', 'pandas', 'pyarrow', 'scipy', 'matplotlib', 'seaborn', 'ipython', 'tabulate']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--render', action='store_true', help='Regenerar también Anexo_A.html con Quarto')
    args = parser.parse_args()
    for script in ['reproducir_integracion.py', 'diagnosticos_anuales.py']:
        subprocess.run([sys.executable, str(CARPETA / script)], check=True, cwd=BASE)
    out = (Path(__file__).resolve().parents[3] / 'regresiones/validacion/evaluacion_transversal/salidas')
    pruebas = json.loads((out / 'comprobacion_reproduccion.json').read_text())
    originales = json.loads((out / 'reproduccion_2023.json').read_text())
    scripts = list(CARPETA.glob('*.py')) + [
        (Path(__file__).resolve().parents[3] / 'regresiones/validacion/correcciones/educacion.py'),
        (Path(__file__).resolve().parents[3] / 'regresiones/validacion/correcciones/empates.py'),
        (Path(__file__).resolve().parents[3] / 'regresiones/validacion/correcciones/depurar_panel.py'),
        (Path(__file__).resolve().parents[3] / 'regresiones/validacion/validacion_laboral/validacion.py'),
        (Path(__file__).resolve().parents[3] / 'regresiones/validacion/validacion_laboral/armonizacion_posicion.py'),
        (Path(__file__).resolve().parents[3] / 'regresiones/validacion/auditoria_qmd_20260926/publicacion_anexo.py'),
    ]
    manifest = {
        'ejecucion_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(),
        'paquetes': {p: importlib.metadata.version(p) for p in PAQUETES},
        'anios': [2022, 2023, 2024, 2025],
        'comprobaciones_integracion': len(pruebas),
        'comprobaciones_2023': len(originales),
        'scripts_sha256': {str(p.relative_to(BASE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in scripts},
        'microdatos_modificados': False,
    }
    (out / 'ejecucion.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.render:
        subprocess.run(['quarto', 'render', 'Anexo_A.qmd', '--to', 'html'], check=True, cwd=BASE)
    print('Evaluación 2022–2025 completada. Resultados y comprobaciones en', out)


if __name__ == '__main__':
    main()
