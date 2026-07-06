import http.server
import os

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'book_scanner', 'build', 'web')

class SPAHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB, **kwargs)

    def do_GET(self):
        path = self.path.split('?')[0]
        if os.path.isfile(os.path.join(WEB, path.lstrip('/'))):
            super().do_GET()
        else:
            self.path = '/index.html'
            super().do_GET()

    def log_message(self, fmt, *args):
        pass

if __name__ == '__main__':
    http.server.HTTPServer(('0.0.0.0', 8000), SPAHandler).serve_forever()
