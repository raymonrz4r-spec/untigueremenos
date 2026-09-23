"""
Endpoint Vercel API: /api/incidents
Devuelve toda la información requerida para las cards y los contadores en un solo request SQL.
Incluye cabecera Cache-Control: s-maxage=900 (15 minutos en el Edge CDN de Vercel).
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.database import get_dashboard_payload_single_request


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Traer toda la información en un solo request
            data = get_dashboard_payload_single_request()
            status_code = 200
        except Exception as e:
            data = {"error": str(e)}
            status_code = 500

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        # Cache de 15 minutos en el CDN de Vercel
        self.send_header("Cache-Control", "public, s-maxage=900, stale-while-revalidate=60")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
