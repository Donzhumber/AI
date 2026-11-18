"""Comprueba soporte y resultados, sin reestimar ni eliminar archivos."""

# Raíz portable de data para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[2]))
from pathlib import Path
import sys, json, runpy, inspect, os, builtins, re

D = Path(__file__).resolve().parents[2]
DOC_ROOT = D.parent
sys.path.insert(0, str(D))
READS = set()


def record(value):
    try:
        p = Path(value).resolve()
        if p.is_relative_to(D) and p.is_file():
            READS.add(str(p.relative_to(D)))
    except (TypeError, ValueError, OSError):
        pass


origopen = builtins.open


def traced_open(file, mode='r', *args, **kwargs):
    if 'r' in str(mode) or mode == '':
        record(file)
    return origopen(file, mode, *args, **kwargs)


def main():
    import pandas as pd
    for name in ['read_csv', 'read_json', 'read_parquet', 'read_stata', 'read_excel']:
        original = getattr(pd, name)
        def wrapper(path, *a, _original=original, **kw):
            record(path)
            return _original(path, *a, **kw)
        setattr(pd, name, wrapper)
    builtins.open = traced_open
    for p in D.rglob('*.py'):
        if not p.is_symlink():
            compile(p.read_text(), str(p), 'exec')
    from regresiones.validacion.auditoria_qmd_20260926 import publicacion_anexo as pub
    tables = []
    for name in sorted(set(re.findall(r'pub\.(\w+)\(', (DOC_ROOT / 'Anexo_a/anexo_a.qmd').read_text()))):
        func = getattr(pub, name)
        try:
            inspect.signature(func).bind()
        except TypeError:
            continue
        func()
        tables.append(name)
    steps = [
        'regresiones/preparacion/datos/armonizados_2018_2025/scripts/verificar_coleccion.py',
        'regresiones/validacion/armonizacion_2018_2025/evaluar_panel.py',
        'regresiones/validacion/armonizacion_2018_2025/verificar_soporte_panel.py',
        'regresiones/validacion/armonizacion_2018_2025/evaluar_integracion.py',
        'regresiones/preparacion/datos/exposicion_ia/verificar_indices.py',
        'regresiones/modelos/ejecutar_modelos_armonizados.py',
        'regresiones/modelos/05_DML_CausalForest/revision_53_20261030/verificar_revision.py',
    ]
    reports, failures = [], []
    prev = os.getcwd()
    os.chdir(D)
    try:
        for relative in steps:
            sys.argv = [relative] + (['--certificar'] if relative.endswith('ejecutar_modelos_armonizados.py') else [])
            print('VERIFICANDO', relative, flush=True)
            try:
                sys.path.insert(0, str((D / relative).parent))
                runpy.run_path(str(D / relative), run_name='__main__')
                reports.append(relative)
            except Exception as e:
                failures.append({'procedimiento': relative, 'error': repr(e)})
                print('ERROR', repr(e), flush=True)
    finally:
        os.chdir(prev)
        builtins.open = origopen
    result = {
        'tablas_recalculadas': tables,
        'procedimientos_aprobados': reports,
        'fallos': failures,
        'lecturas': sorted(READS),
        'sin_reestimacion': True,
    }
    (D / 'regresiones/validacion/verificacion_reorganizacion.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print('VERIFICACION', json.dumps({k: v for k, v in result.items() if k not in ['lecturas', 'tablas_recalculadas']}, ensure_ascii=False), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
