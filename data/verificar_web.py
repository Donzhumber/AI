"""Comprueba la publicación estática sin microdatos ni paquetes externos."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urlparse
import base64
import json
import re

SITE = Path(__file__).resolve().parent / '_site'
PAGES = ['index.html', 'Principal/principal.html', 'Anexo_a/anexo_a.html', 'Dashboard/dashboard.html']


class Resources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.resources = []

    def handle_starttag(self, tag, attrs):
        self.resources.extend(value for name, value in attrs if name in {'src', 'href'} and value)


def local_target(page, value):
    if value.startswith(('#', '${')) or urlparse(value).scheme or value.startswith('//'):
        return None
    name = unquote(value.split('?', 1)[0].split('#', 1)[0])
    if not name:
        return None
    target = (page.parent / name).resolve()
    assert target.is_relative_to(SITE.resolve()), f'Enlace fuera del sitio: {value}'
    assert target.is_file(), f'Recurso ausente en {page.relative_to(SITE)}: {value}'
    return target


def main():
    assert SITE.is_dir(), 'Ejecutar primero python data/preparar_web.py'
    forbidden = []
    for p in SITE.rglob('*'):
        if p.is_symlink() or (p.is_file() and p.suffix.lower() in {'.parquet', '.dta', '.sav', '.dbf', '.zip'}):
            forbidden.append(str(p.relative_to(SITE)))
    assert not forbidden, f'Archivos no admitidos en Pages: {forbidden}'
    checked = set()
    cell_count = 0
    for name in PAGES:
        page = SITE / name
        text = page.read_text(encoding='utf-8')
        checked.add(name)
        parser = Resources()
        parser.feed(text)
        for value in parser.resources:
            target = local_target(page, value)
            if target:
                checked.add(str(target.relative_to(SITE.resolve())))
        for module in re.findall(r'<script type="ojs-module-contents">\s*([^<]+)</script>', text):
            cells = json.loads(base64.b64decode(module))['contents']
            cell_count += len(cells)
            for cell in cells:
                assert '.parquet' not in cell['source'], 'El dashboard público requiere microdatos'
                for value in re.findall(r'FileAttachment\(["\']([^"\']+)', cell['source']):
                    target = local_target(page, value)
                    assert target
                    json.loads(target.read_text())
                    checked.add(str(target.relative_to(SITE.resolve())))
    assert cell_count >= 20, 'Faltan las celdas interactivas del dashboard'
    report = {'paginas': PAGES, 'paginas_y_recursos': len(checked), 'celdas_interactivas': cell_count,
              'enlaces_rotos': [], 'microdatos_publicados': False, 'enlaces_simbolicos': False}
    (SITE / 'verificacion_web.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
