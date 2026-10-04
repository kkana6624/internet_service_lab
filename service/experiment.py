#!/usr/bin/env python3
"""Private, dedicated endpoint: does not delay WordPress requests."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import time, sys
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/experiment':
            self.send_error(404); return
        delay = 2 if Path('/var/lib/lab/anomaly-delay').exists() else 0
        time.sleep(delay)
        self.send_response(200); self.end_headers(); self.wfile.write(b'experiment\n')
ThreadingHTTPServer((sys.argv[1],8081), Handler).serve_forever()
