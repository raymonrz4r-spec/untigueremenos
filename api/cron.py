"""
Endpoint Vercel Cron: /api/cron
Ejecutado automáticamente por Vercel cada 5 minutos mediante vercel.json.
Comprueba si hay titulares nuevos de noticias en RD:
- Si hay titulares nuevos: los analiza con Groq y los guarda en SQLite.
- Si no hay titulares nuevos: NO hace nada (0 llamadas a Groq).
"""

from http.server import BaseHTTPRequestHandler
import json
import sys
from pathlib import Path

# Añadir raíz del proyecto al path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.background_monitor import check_and_update_news, get_monitor_status


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Ejecutar revisión de 5 minutos
            new_inserted = check_and_update_news()
            status = get_monitor_status()

            response_data = {
                "success": True,
                "new_incidents_inserted": new_inserted,
                "groq_called": bool(new_inserted > 0),
                "monitor_status": status,
                "message": (
                    f"Se procesaron e insertaron {new_inserted} incidentes nuevos con Groq."
                    if new_inserted > 0
                    else "No hay titulares nuevos. 0 llamadas a Groq realizadas."
                )
            }
            status_code = 200
        except Exception as e:
            response_data = {
                "success": False,
                "error": str(e)
            }
            status_code = 500

        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
