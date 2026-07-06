import http.server
import urllib.request
import urllib.error
import os
import re

BACKEND = 'http://119.91.119.89:9000'
WEB_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'book_scanner', 'build', 'web')

STATIC_EXT = re.compile(r'\.(js|json|wasm|ttf|otf|woff2?|css|png|jpg|jpeg|gif|svg|ico|map|dart)$')

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_ROOT, **kwargs)

    def do_GET(self):
        if self.path.startswith('/api/') or self.path.startswith('/uploads/'):
            self._proxy('GET')
        elif STATIC_EXT.search(self.path):
            super().do_GET()
        elif self.path == '/' or self.path == '/index.html':
            super().do_GET()
        else:
            self.path = '/index.html'
            super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/'):
            self._proxy('POST')
        else:
            super().do_POST()

    def do_PUT(self):
        if self.path.startswith('/api/'):
            self._proxy('PUT')
        else:
            super().do_PUT()

    def do_DELETE(self):
        if self.path.startswith('/api/'):
            self._proxy('DELETE')
        else:
            super().do_DELETE()

    def do_PATCH(self):
        if self.path.startswith('/api/'):
            self._proxy('PATCH')
        else:
            super().do_PATCH()

    def _proxy(self, method):
        url = BACKEND + self.path
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len) if content_len > 0 else None
        req = urllib.request.Request(url, data=body, method=method)
        for k, v in self.headers.items():
            if k.lower() in ('host', 'content-length'):
                continue
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() == 'transfer-encoding':
                        continue
                    self.send_header(k, v)
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() == 'transfer-encoding':
                    continue
                self.send_header(k, v)
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(f'{{"detail":"Backend unreachable: {e}"}}'.encode())

    def log_message(self, fmt, *args):
        pass  # silent

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    print(f'[Server] Serving {WEB_ROOT} + proxy /api/* -> {BACKEND}')
    http.server.HTTPServer(('0.0.0.0', port), ProxyHandler).serve_forever()
