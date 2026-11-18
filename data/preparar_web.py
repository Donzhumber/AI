"""Crea un sitio estático solo con HTML, recursos y agregados explícitos.
No realiza push ni publica en GitHub. Usar --render para regenerar el dashboard
público. Los artículos deben estar compilados previamente con datos locales.
"""

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[0]))
from pathlib import Path
import argparse, shutil, json, re, base64
from urllib.parse import unquote

DATA_DIR = Path(__file__).resolve().parent
DOC_ROOT = DATA_DIR.parent
DASH = DOC_ROOT / 'Dashboard'
OUT = DATA_DIR / '_site'


def derivar_publico():
    source = (DASH / 'dashboard.qmd').read_text()
    assert '\n# Pirámide poblacional ' in source
    content = source.split('\n# Pirámide poblacional ', 1)[0]
    content, n = re.subn(r'```\{ojs\}\n//\| output: false\n// Motor DuckDB-WASM.*?\n```\n', '', content, flags=re.S)
    assert n == 1, 'Revisar la celda de consulta de microdatos antes de generar la edición pública'
    assert '.parquet' not in content
    content += '\n# Metodología {#metodologia icon="info-circle"}\n\nEsta edición web utiliza agregados de exposición ocupacional y uso reportado de IA. Las puntuaciones, los universos y los factores de expansión corresponden a los documentados en el [Anexo A](../Anexo_a/anexo_a.html). La no cotización no equivale a la informalidad oficial. El inspector de microdatos y los mapas detallados se conservan en el dashboard local y requieren las bases completas, que no se publican automáticamente.\n'
    (DASH / 'dashboard_publico.qmd').write_text(content)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--render', action='store_true')
    a = p.parse_args()
    if a.render:
        import subprocess
        derivar_publico()
        subprocess.run(['quarto', 'render', 'dashboard_publico.qmd'], cwd=DASH, check=True)
    OUT.mkdir(exist_ok=True)
    (OUT / 'Dashboard').mkdir(exist_ok=True)
    (OUT / 'Principal').mkdir(exist_ok=True)
    (OUT / 'Anexo_a').mkdir(exist_ok=True)
    for folder, name in [('Principal', 'principal.html'), ('Anexo_a', 'anexo_a.html')]:
        src = DOC_ROOT / folder / name
        assert src.is_file(), f'Compilar {folder}/{name}'
        shutil.copy2(src, OUT / folder / name)
    source = DASH / 'dashboard_publico.html'
    assert source.is_file(), 'Generar dashboard_publico.html'
    shutil.copy2(source, OUT / 'Dashboard/dashboard.html')
    for folder in ['dashboard_publico_files', 'dashboard_files']:
        if (DASH / folder).exists():
            shutil.copytree(DASH / folder, OUT / 'Dashboard' / folder, dirs_exist_ok=True)
    for name in ['ocupaciones_cortas.js', 'cajas_uniformes.css', 'ajustes_version_web.html']:
        if (DASH / name).exists():
            shutil.copy2(DASH / name, OUT / 'Dashboard' / name)
    public = OUT / 'data/datos/publicacion/dashboard'
    public.mkdir(parents=True, exist_ok=True)
    allow = ['co_departamentos.geojson', 'catalogo_ocupaciones_multianual.json', 'cuadrantes_anexo.json', 'perfiles_uso_ia_2025.json']
    for name in allow:
        shutil.copy2(DATA_DIR / 'datos/publicacion/dashboard' / name, public / name)
    linked_sources = []
    for folder, name in [('Principal', 'principal.html'), ('Anexo_a', 'anexo_a.html')]:
        html_file = DOC_ROOT / folder / name
        for value in re.findall(r'(?:src|href)=["\']([^"\']+)["\']', html_file.read_text()):
            if value.startswith(('http:', 'https:', 'data:', '#', 'javascript:', '${', 'mailto:')):
                continue
            relative = unquote(value.split('?')[0].split('#')[0])
            if not relative:
                continue
            src = (html_file.parent / relative).resolve()
            if src.suffix.lower() not in {'.py', '.md', '.do'}:
                assert src.is_relative_to(DOC_ROOT) and src.exists(), f'Revisar recurso de artículo: {relative}'
                continue
            assert src.is_relative_to(DOC_ROOT) and src.is_file(), relative
            rel_out = src.relative_to(DOC_ROOT)
            target = OUT / rel_out
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
            linked_sources.append(str(rel_out))
    (OUT / '.nojekyll').touch()
    (OUT / 'index.html').write_text('''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>IA y mercado laboral en Colombia</title><style>body{font:17px/1.6 system-ui;max-width:760px;margin:8vh auto;padding:0 20px;color:#183c54}a{display:block;padding:16px;margin:14px 0;border:1px solid #cbd5e1;border-radius:10px;color:#164d70;text-decoration:none}a:hover{background:#eef5fa}</style><h1>IA y mercado laboral en Colombia</h1><p>Documentos y exploración de resultados.</p><a href="Principal/principal.html">Artículo principal</a><a href="Anexo_a/anexo_a.html">Anexo A · métodos y validación</a><a href="Dashboard/dashboard.html">Dashboard · exposición y uso de IA</a></html>''')
    forbidden = [str(f.relative_to(OUT)) for f in OUT.rglob('*') if f.is_file() and (f.suffix.lower() in {'.parquet', '.dta', '.zip', '.dbf', '.sav'} or f.stat().st_size > 100 * 2**20)]
    assert not forbidden, forbidden
    text = (OUT / 'Dashboard/dashboard.html').read_text()
    assert '.parquet' not in text, 'Quedó un adjunto de microdatos'
    assert 'quarto-dashboard' in text, 'Compilar con el formato dashboard nativo, sin --to html'
    modules = [json.loads(base64.b64decode(value)) for value in re.findall(r'<script type="ojs-module-contents">\s*([^<]+)</script>', text)]
    cells = [cell for module in modules for cell in module['contents']]
    assert len(cells) >= 20, 'Faltan celdas interactivas del dashboard'
    code = '\n'.join(cell['source'] for cell in cells)
    assert '.parquet' not in code, 'Una celda interactiva requiere microdatos no públicos'
    attachments = re.findall(r'FileAttachment\(["\']([^"\']+)', code)
    for name in attachments:
        assert (OUT / 'Dashboard' / name).resolve().is_file(), name
    resources = []
    for match in re.finditer(r'(?:src|href)=["\']([^"\']+)["\']', text):
        value = match.group(1)
        if value.startswith(('http:', 'https:', 'data:', '#', 'javascript:', '${')):
            continue
        target = (OUT / 'Dashboard' / unquote(value.split('?')[0].split('#')[0])).resolve()
        if value and not target.exists():
            resources.append(value)
    assert not resources, resources
    report = {'archivos': len([f for f in OUT.rglob('*') if f.is_file()]), 'bytes': sum(f.stat().st_size for f in OUT.rglob('*') if f.is_file()), 'datos_publicados': allow, 'microdatos_publicados': False, 'publicado_en_github': False, 'recursos_html_comprobados': True, 'celdas_ojs': len(cells), 'adjuntos_interactivos': attachments, 'formato_dashboard': True, 'fuentes_enlazadas': linked_sources}
    (OUT / 'manifest_publicacion.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
