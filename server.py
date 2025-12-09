import base64
import http.server
import json
import os
import shutil
import subprocess
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
CONTENT_BACKUP_DIR = CONFIG_BASE / "content-backup"
TEMP_CADDYFILE = Path("/tmp/caddyfile.upload")
CADDY_BIN = Path("/app/vendor/caddy/caddy")

DEFAULT_ADMIN_PASSWORD = "caddyLander"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)


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
            if not self._require_auth():
                return
            return self._serve_file(STATIC_DIR / "admin.html", "text/html")
        if parsed.path == "/api/admin/info":
            if not self._require_auth():
                return
            return self._serve_admin_info()
        if parsed.path == "/api/content":
            return self._serve_file(RUNTIME_CONTENT, "application/json")
        if parsed.path == "/admin/caddyfile":
            if not self._require_auth():
                return
            return self._serve_caddyfile()
        if parsed.path == "/api/admin/content/backups":
            if not self._require_auth():
                return
            return self._serve_content_backups()
        if parsed.path == "/api/admin/content/backup":
            if not self._require_auth():
                return
            return self._serve_content_backup(parsed)
        if parsed.path == "/api/admin/caddyfile/backups":
            if not self._require_auth():
                return
            return self._serve_caddyfile_backups()
        if parsed.path == "/api/admin/caddyfile/backup":
            if not self._require_auth():
                return
            return self._serve_caddyfile_backup(parsed)
        if parsed.path.startswith("/static/"):
            target = STATIC_DIR / parsed.path.removeprefix("/static/")
            if target.is_file() and target.resolve().is_relative_to(STATIC_DIR.resolve()):
                return self._serve_file(target, self._guess_type(target))
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/upload":
            if not self._require_auth():
                return
            return self._handle_content_upload()
        if parsed.path == "/admin/caddyfile":
            if not self._require_auth():
                return
            return self._handle_caddyfile_update()
        if parsed.path == "/api/admin/content/restore":
            if not self._require_auth():
                return
            return self._handle_content_restore()
        if parsed.path == "/api/admin/caddyfile/restore":
            if not self._require_auth():
                return
            return self._handle_caddyfile_restore()

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

    def _require_auth(self) -> bool:
        if not ADMIN_PASSWORD:
            return True

        header = self.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                decoded = base64.b64decode(header.removeprefix("Basic ").strip()).decode()
                username, password = decoded.split(":", 1)
            except Exception:
                username, password = None, None

            if password == ADMIN_PASSWORD:
                return True

        self.send_response(401)
        self.send_header("WWW-Authenticate", 'Basic realm="caddyLander"')
        self.end_headers()
        return False

    def _serve_admin_info(self):
        info = {"defaultPassword": ADMIN_PASSWORD == DEFAULT_ADMIN_PASSWORD}
        data = json.dumps(info).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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

        previous_content = ""
        if RUNTIME_CONTENT.exists():
            previous_content = RUNTIME_CONTENT.read_text(encoding="utf-8")

        if previous_content:
            self._backup_content(previous_content)

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

        # Step 1: Write to temp file
        TEMP_CADDYFILE.write_text(new_content, encoding="utf-8")

        # Step 2: Format
        result = subprocess.run(
            [str(CADDY_BIN), "fmt", "--overwrite", str(TEMP_CADDYFILE)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            response = json.dumps({
                "success": False,
                "stage": "fmt",
                "output": result.stderr
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            return

        # Step 3: Validate (using adapt for syntax-only validation)
        result = subprocess.run(
            [str(CADDY_BIN), "adapt", "--adapter", "caddyfile", "--config", str(TEMP_CADDYFILE)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            response = json.dumps({
                "success": False,
                "stage": "validate",
                "output": result.stderr
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            return

        # Step 4: Backup previous version if exists
        CADDYFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        previous_content = ""
        if CADDYFILE_PATH.exists():
            previous_content = CADDYFILE_PATH.read_text(encoding="utf-8")

        if previous_content:
            self._backup_caddyfile(previous_content)

        # Step 5: Promote temp to real file
        shutil.move(str(TEMP_CADDYFILE), str(CADDYFILE_PATH))

        # Step 6: Success (Caddy reload must be done externally)
        response = json.dumps({
            "success": True,
            "stage": "complete",
            "message": "Caddyfile saved. Reload Caddy to apply changes."
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _backup_content(self, previous_content: str):
        CONTENT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = CONTENT_BACKUP_DIR / f"content.json.old.{timestamp}"
        backup_path.write_text(previous_content, encoding="utf-8")

        backups = sorted(
            CONTENT_BACKUP_DIR.glob("content.json.old.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old_backup in backups[10:]:
            old_backup.unlink(missing_ok=True)

    def _resolve_backup(self, name: str) -> Path | None:
        candidate = (CONTENT_BACKUP_DIR / name).resolve()
        if not candidate.is_file():
            return None
        if not candidate.is_relative_to(CONTENT_BACKUP_DIR.resolve()):
            return None
        if not candidate.name.startswith("content.json.old."):
            return None
        return candidate

    def _resolve_caddy_backup(self, name: str) -> Path | None:
        candidate = (BACKUP_DIR / name).resolve()
        if not candidate.is_file():
            return None
        if not candidate.is_relative_to(BACKUP_DIR.resolve()):
            return None
        if not candidate.name.startswith("Caddyfile.old."):
            return None
        return candidate

    def _handle_content_restore(self):
        raw_body = read_body(self)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON payload")
            return

        name = payload.get("name")
        if not name:
            self.send_error(400, "Missing backup name")
            return

        target = self._resolve_backup(name)
        if target is None:
            self.send_error(404, "Backup not found")
            return

        previous_content = ""
        if RUNTIME_CONTENT.exists():
            previous_content = RUNTIME_CONTENT.read_text(encoding="utf-8")

        backup_text = target.read_text(encoding="utf-8")

        try:
            parsed_json = json.loads(backup_text)
        except json.JSONDecodeError:
            self.send_error(500, "Selected backup is invalid JSON")
            return

        if previous_content:
            self._backup_content(previous_content)

        with open(RUNTIME_CONTENT, "w", encoding="utf-8") as f:
            json.dump(parsed_json, f, ensure_ascii=False, indent=2)

        response = json.dumps({"status": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _serve_content_backups(self):
        backups = [
            {
                "name": path.name,
                "timestamp": path.stat().st_mtime,
            }
            for path in sorted(
                CONTENT_BACKUP_DIR.glob("content.json.old.*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        ]

        data = json.dumps({"backups": backups}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_content_backup(self, parsed_url):
        params = parse_qs(parsed_url.query)
        name = params.get("name", [None])[0]
        if not name:
            self.send_error(400, "Missing backup name")
            return

        target = self._resolve_backup(name)
        if target is None:
            self.send_error(404, "Backup not found")
            return

        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _backup_caddyfile(self, previous_content: str):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = BACKUP_DIR / f"Caddyfile.old.{timestamp}"
        backup_path.write_text(previous_content, encoding="utf-8")

        backups = sorted(
            BACKUP_DIR.glob("Caddyfile.old.*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old_backup in backups[10:]:
            old_backup.unlink(missing_ok=True)

    def _serve_caddyfile_backups(self):
        backups = [
            {
                "name": path.name,
                "timestamp": path.stat().st_mtime,
            }
            for path in sorted(
                BACKUP_DIR.glob("Caddyfile.old.*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        ]

        data = json.dumps({"backups": backups}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_caddyfile_backup(self, parsed_url):
        params = parse_qs(parsed_url.query)
        name = params.get("name", [None])[0]
        if not name:
            self.send_error(400, "Missing backup name")
            return

        target = self._resolve_caddy_backup(name)
        if target is None:
            self.send_error(404, "Backup not found")
            return

        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_caddyfile_restore(self):
        raw_body = read_body(self)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON payload")
            return

        name = payload.get("name")
        if not name:
            self.send_error(400, "Missing backup name")
            return

        target = self._resolve_caddy_backup(name)
        if target is None:
            self.send_error(404, "Backup not found")
            return

        previous_content = ""
        if CADDYFILE_PATH.exists():
            previous_content = CADDYFILE_PATH.read_text(encoding="utf-8")

        backup_text = target.read_text(encoding="utf-8")

        if previous_content:
            self._backup_caddyfile(previous_content)

        CADDYFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CADDYFILE_PATH.write_text(backup_text, encoding="utf-8")

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
