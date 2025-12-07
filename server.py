import http.server
import json
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

APP_ROOT = Path("/app")
STATIC_DIR = APP_ROOT / "static"
TEMPLATE_CONTENT = APP_ROOT / "content" / "content.json"
RUNTIME_BASE = Path("/var/caddy")
RUNTIME_CONTENT = RUNTIME_BASE / "content.json"
CONFIG_BASE = Path("/config")
CADDYFILE_PATH = CONFIG_BASE / "Caddyfile"
BACKUP_DIR = CONFIG_BASE / "backup"


def bootstrap_content() -> None:
    RUNTIME_BASE.mkdir(parents=True, exist_ok=True)
    if not RUNTIME_CONTENT.exists():
        shutil.copyfile(TEMPLATE_CONTENT, RUNTIME_CONTENT)


def read_body(request_handler: http.server.BaseHTTPRequestHandler) -> bytes:
    length = int(request_handler.headers.get("Content-Length", "0"))
    return request_handler.rfile.read(length)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        super().log_message(format, *args)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self._serve_file(STATIC_DIR / "index.html", "text/html")
        if parsed.path == "/admin":
            return self._serve_file(STATIC_DIR / "admin.html", "text/html")
        if parsed.path == "/api/content":
            return self._serve_file(RUNTIME_CONTENT, "application/json")
        if parsed.path == "/admin/caddyfile":
            return self._serve_caddyfile()
        if parsed.path.startswith("/static/"):
            target = STATIC_DIR / parsed.path.removeprefix("/static/")
            if target.is_file() and target.resolve().is_relative_to(STATIC_DIR.resolve()):
                return self._serve_file(target, self._guess_type(target))
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload":
            return self._handle_content_upload()
        if parsed.path == "/admin/caddyfile":
            return self._handle_caddyfile_update()

        self.send_error(404)

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _guess_type(self, path: Path) -> str:
        if path.suffix == ".html":
            return "text/html"
        if path.suffix == ".css":
            return "text/css"
        if path.suffix == ".js":
            return "application/javascript"
        return "application/octet-stream"

    def _serve_caddyfile(self):
        content = ""
        if CADDYFILE_PATH.exists():
            existing = CADDYFILE_PATH.read_text(encoding="utf-8")
            if existing:
                content = existing

        data = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_content_upload(self):
        raw_body = read_body(self)
        data = parse_qs(raw_body.decode())
        new_content = data.get("content", [None])[0]
        if new_content is None:
            self.send_error(400, "Missing content")
            return

        try:
            parsed_json = json.loads(new_content)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON payload")
            return

        with open(RUNTIME_CONTENT, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, ensure_ascii=False, indent=2)

        response = json.dumps({"status": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _handle_caddyfile_update(self):
        raw_body = read_body(self)
        new_content = raw_body.decode("utf-8")

        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        CADDYFILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        previous_content = ""
        if CADDYFILE_PATH.exists():
            previous_content = CADDYFILE_PATH.read_text(encoding="utf-8")

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = BACKUP_DIR / f"Caddyfile.old.{timestamp}"
        backup_path.write_text(previous_content, encoding="utf-8")

        CADDYFILE_PATH.write_text(new_content, encoding="utf-8")

        backups = sorted(
            BACKUP_DIR.glob("Caddyfile.old.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old_backup in backups[10:]:
            old_backup.unlink(missing_ok=True)

        response = json.dumps({"status": "ok", "restart_required": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


if __name__ == "__main__":
    bootstrap_content()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    print("caddylander running on port 8080")
    server.serve_forever()
