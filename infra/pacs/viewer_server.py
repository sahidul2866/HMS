#!/usr/bin/env python3
"""
DICOM Viewer Server - Serves viewer UI and handles image loading from Orthanc
"""
import os
import sys
import argparse
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import urllib.request
import urllib.error
import urllib.parse

class ViewerHandler(SimpleHTTPRequestHandler):
    """HTTP handler with CORS support for DICOM viewer"""
    
    def end_headers(self):
        """Add CORS and cache-busting headers to all responses"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.send_header('ETag', 'W/"cms-bust"')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight"""
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/orthanc/"):
            return self._proxy_orthanc()
        if self.path.startswith("/viewer"):
            query = ""
            if "?" in self.path:
                query = self.path[self.path.index("?") :]
            self.path = f"/index.html{query}"
        return super().do_GET()

    def _proxy_orthanc(self):
        try:
            target_base = self.server.orthanc_url.rstrip("/")
            proxied_path = self.path[len("/orthanc") :]
            target_url = f"{target_base}{proxied_path}"
            req = urllib.request.Request(target_url, method="GET")
            with urllib.request.urlopen(req, timeout=20) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "application/json")
                self.send_response(response.status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as error:
            body = error.read() if hasattr(error, "read") else b""
            self.send_response(error.code)
            self.send_header("Content-Type", error.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)
        except Exception as error:
            payload = json.dumps({"error": str(error)}).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
    
    def log_message(self, format, *args):
        """Custom logging"""
        print(f"[VIEWER] {format % args}")

def run_viewer_server(port=8080, orthanc_url="http://localhost:8042"):
    """Start DICOM viewer server"""
    os.chdir(Path(__file__).parent / "viewer")
    
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, ViewerHandler)
    httpd.orthanc_url = orthanc_url
    
    print(f"\n{'='*60}")
    print(f"🏥 HMS DICOM Viewer Server")
    print(f"{'='*60}")
    print(f"✓ Viewer running: http://localhost:{port}")
    print(f"✓ Orthanc API: {orthanc_url}")
    print(f"{'='*60}\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n✓ Viewer server stopped")
        httpd.shutdown()
        sys.exit(0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HMS DICOM Viewer Server')
    parser.add_argument('--port', type=int, default=8080, help='Port to run on (default: 8080)')
    parser.add_argument('--orthanc', type=str, default='http://localhost:8042', 
                       help='Orthanc URL (default: http://localhost:8042)')
    
    args = parser.parse_args()
    run_viewer_server(args.port, args.orthanc)
