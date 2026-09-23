import sys
import json
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.database import get_dashboard_payload_single_request
from src.background_monitor import check_and_update_news

class LocalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/incidents':
            try:
                data = get_dashboard_payload_single_request()
                payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        elif self.path == '/api/cron':
            try:
                inserted = check_and_update_news()
                payload = json.dumps({"success": True, "inserted": inserted}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(payload)
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == '__main__':
    print("Starting local API server on port 3000...")
    server = HTTPServer(('localhost', 3000), LocalHandler)
    server.serve_forever()
