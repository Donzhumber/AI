"""Sirve el dashboard local sin conservar copias anteriores en el navegador."""

# Raíz portable de data para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'data'))

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import posixpath
from urllib.parse import unquote, urlsplit

DASH_DIR = Path(__file__).resolve().parent
DOC_ROOT = DASH_DIR.parent


class SinCache(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self):
        if "If-Modified-Since" in self.headers:
            del self.headers["If-Modified-Since"]
        super().do_GET()

    def translate_path(self, path):
        clean = unquote(urlsplit(path).path)
        norm = posixpath.normpath(clean)
        if norm.startswith(("/data/", "/Anexo_a/", "/Principal/", "/Dashboard/")) or norm in ("/data", "/Anexo_a", "/Principal", "/Dashboard"):
            return str(DOC_ROOT / norm.lstrip("/"))
        if norm.startswith("/datos/") or norm == "/datos":
            return str(DOC_ROOT / "data" / norm.lstrip("/"))
        return super().translate_path(path)


if __name__ == "__main__":
    servidor = ThreadingHTTPServer(("127.0.0.1", 8008), partial(SinCache, directory=str(DASH_DIR)))
    print("Dashboard disponible en http://localhost:8008/dashboard.html", flush=True)
    servidor.serve_forever()
