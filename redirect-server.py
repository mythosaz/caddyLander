import http.server
import json
import os
from urllib.parse import parse_qs

BASE = "/var/caddy"
CONTENT = os.path.join(BASE, "content.json")

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.path = "/index.html"
        elif self.path == "/admin":
            self.path = "/admin.html"
        elif self.path == "/api/content":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            with open(CONTENT, "rb") as f:
                self.wfile.write(f.read())
            return
        
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        if self.path != "/api/upload":
            self.send_error(404)
            return

        length = int(self.headers["Content-Length"])
        body = self.rfile.read(length).decode()
        data = parse_qs(body)
        new_content = data.get("content", [""])[0]

        with open(CONTENT, "w") as f:
            f.write(new_content)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')


if __name__ == "__main__":
    os.chdir(BASE)
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    print("redirect-portal running on port 8080")
    server.serve_forever()
