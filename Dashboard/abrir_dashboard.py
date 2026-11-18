#!/usr/bin/env python3
"""
abrir_dashboard.py
==================
Inicia un servidor HTTP local para servir el Tablero Interactivo Quarto / OJS
y lo abre automáticamente en Google Chrome (o el navegador predeterminado).

Motivo técnico:
Los navegadores modernos bloquean por seguridad (CORS / Same-Origin Policy)
los módulos de JavaScript (type="module") y las llamadas fetch() / FileAttachment()
a archivos JSON cuando se abren páginas directamente desde rutas locales (file:///).
Servir la carpeta mediante HTTP local resuelve esto completamente.
"""

# Raíz portable de Document para ejecución directa.
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parents[1] / 'data'))

import sys
import time
import socket
import urllib.request
import subprocess
from pathlib import Path

PORT = 8008
BASE_DIR = Path(__file__).resolve().parent
URL = f"http://localhost:{PORT}/dashboard.html"

def esta_puerto_activo(puerto):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", puerto)) == 0

def abrir_en_navegador():
    # `open -a "Google Chrome" URL` reutiliza la pestaña existente sin recargarla
    # si esa URL ya está abierta. Se agrega un parámetro de caché única para que
    # macOS/Chrome lo trate como una navegación nueva y siempre cargue el HTML
    # recién renderizado, no una pestaña vieja ya abierta.
    url_fresca = f"{URL}?v={int(time.time())}"
    print(f"-> Abriendo {url_fresca} en Google Chrome...")
    try:
        subprocess.run(["open", "-a", "Google Chrome", url_fresca], check=True)
    except subprocess.CalledProcessError:
        subprocess.run(["open", url_fresca])

# Servidor propio en vez de `python -m http.server` plano: ese no manda ningún
# encabezado de caché, así que Chrome puede seguir sirviendo una copia vieja de
# un archivo (p. ej. data/cuadrantes_anexo.json) aunque la página HTML sí se
# recargue fresca — justo lo que pasó cuando ese archivo creció de 1,9 a 21 MB
# al agregar el filtro de departamento/sexo: el título y los ejes del gráfico
# se veían bien (no dependen de ese archivo) pero los puntos quedaban vacíos,
# porque la copia cacheada no tenía los campos nuevos. Cache-Control: no-store
# obliga a recargar todo (HTML, JSON, parquet) en cada visita.
SERVIDOR_SIN_CACHE = '''
import http.server, sys
class SinCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()
http.server.test(HandlerClass=SinCache, port=int(sys.argv[1]))
'''

def main():
    if esta_puerto_activo(PORT):
        print(f"[OK] El servidor local ya está activo en el puerto {PORT}.")
        abrir_en_navegador()
        return

    print(f"-> Iniciando servidor HTTP local (sin caché) en el puerto {PORT}...")
    proc = subprocess.Popen(
        [sys.executable, str(BASE_DIR / 'servidor_dashboard.py')],
        cwd=str(BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Esperar hasta que responda
    for _ in range(20):
        time.sleep(0.2)
        if esta_puerto_activo(PORT):
            break
            
    print(f"[OK] Servidor activo (PID {proc.pid}).")
    abrir_en_navegador()
    print(f"\nTablero disponible en: {URL}")
    print("Presiona Ctrl+C para detener el servidor si lo ejecutaste en primer plano.")
    
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nDeteniendo servidor...")
        proc.terminate()

if __name__ == "__main__":
    main()
