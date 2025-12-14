import base64
import http.server
import json
import os
import shutil
import subprocess
import logging
import socket
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
RUNTIME_STATIC = RUNTIME_BASE / "static"
TEMP_CADDYFILE = Path("/tmp/caddyfile.upload")
CADDY_BIN = Path("/app/vendor/caddy/caddy")

DEFAULT_ADMIN_PASSWORD = "caddyLander"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD)

LOGO = "\n".join(
    [
        "                       █████     █████            █████                                █████",
        "                       ░░███     ░░███            ░░███                                ░░███",
        "  ██████   ██████    ███████   ███████  █████ ████ ░███         ██████   ████████    ███████   ██████  ████████",
        " ███░░███ ░░░░░███  ███░░███  ███░░███ ░░███ ░███  ░███        ░░░░░███ ░░███░░███  ███░░███  ███░░███░░███░░███",
        "░███ ░░░   ███████ ░███ ░███ ░███ ░███  ░███ ░███  ░███         ███████  ░███ ░███ ░███ ░███ ░███████  ░███ ░░░",
        "░███  ███ ███░░███ ░███ ░███ ░███ ░███  ░███ ░███  ░███      █ ███░░███  ░███ ░███ ░███ ░███ ░███░░░   ░███",
        "░░██████ ░░████████░░████████░░████████ ░░███████  ███████████░░████████ ████ █████░░████████░░██████  █████",
        " ░░░░░░   ░░░░░░░░  ░░░░░░░░  ░░░░░░░░   ░░░░░███ ░░░░░░░░░░░  ░░░░░░░░ ░░░░ ░░░░░  ░░░░░░░░  ░░░░░░  ░░░░░",
        "                                         ███ ░███",
        "                                        ░░██████",
        "                                         ░░░░░░",
    ]
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
LOGGER = logging.getLogger("caddylander")
BUILD_VERSION = datetime.now().strftime("%y%m%d")


def bootstrap_content() -> None:
    RUNTIME_BASE.mkdir(parents=True, exist_ok=True)
    RUNTIME_STATIC.mkdir(parents=True, exist_ok=True)
    if not RUNTIME_CONTENT.exists():
        shutil.copyfile(TEMPLATE_CONTENT, RUNTIME_CONTENT)
        LOGGER.info("Bootstrapped runtime content from template")


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
        if parsed.path == "/api/admin/content/generate":
            if not self._require_auth():
                return
            return self._serve_generated_content()
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
        if parsed.path == "/favicon.png":
            return self._serve_file(STATIC_DIR / "favicon.png", "image/png")
        if parsed.path == "/favicon.svg":
            return self._serve_favicon("favicon.svg", "image/svg+xml")
        if parsed.path == "/favicon.ico":
            return self._serve_favicon("favicon.ico", "image/x-icon")
        if parsed.path == "/static/favicon.svg":
            return self._serve_favicon("favicon.svg", "image/svg+xml")
        if parsed.path == "/static/favicon.ico":
            return self._serve_favicon("favicon.ico", "image/x-icon")
        # Allow direct access to static assets without the /static prefix (e.g. /favicon.ico)
        static_target = (STATIC_DIR / parsed.path.lstrip("/")).resolve()
        if static_target.is_file() and static_target.is_relative_to(STATIC_DIR.resolve()):
            return self._serve_file(static_target, self._guess_type(static_target))
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
        if parsed.path == "/api/admin/favicon":
            if not self._require_auth():
                return
            return self._handle_favicon_upload(parsed)
        if parsed.path == "/api/admin/favicon/restore":
            if not self._require_auth():
                return
            return self._handle_favicon_restore(parsed)
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
        if path.suffix == ".png":
            return "image/png"
        if path.suffix == ".svg":
            return "image/svg+xml"
        return "application/octet-stream"

    def _serve_favicon(self, name: str, mime: str):
        runtime_candidate = RUNTIME_STATIC / name
        target = runtime_candidate if runtime_candidate.exists() else STATIC_DIR / name
        return self._serve_file(target, mime)

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
        info = {
            "defaultPassword": ADMIN_PASSWORD == DEFAULT_ADMIN_PASSWORD,
            "buildVersion": BUILD_VERSION,
            "status": self._collect_status(),
            "links": {
                "github": "https://github.com/mythosaz/caddyLander"
            },
        }
        data = json.dumps(info).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _collect_status(self) -> dict:
        forwarded_for = self.headers.get("X-Forwarded-For")
        client_ip = self.client_address[0] if self.client_address else None
        internal_ips = self._get_internal_ips()

        return {
            "clientIp": forwarded_for.split(",")[0].strip() if forwarded_for else client_ip,
            "clientChain": forwarded_for,
            "serverIps": internal_ips,
            "docker": self._get_docker_info(),
        }

    def _get_internal_ips(self) -> list[str]:
        try:
            result = subprocess.run([
                "hostname",
                "-I",
            ], capture_output=True, text=True, check=False)
            output = result.stdout.strip()
            if output:
                return [ip for ip in output.split() if ip]
        except Exception:
            pass

        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip:
                return [ip]
        except Exception:
            pass

        return []

    def _get_docker_info(self) -> dict:
        is_docker = Path("/.dockerenv").exists()
        container_id = None

        try:
            cgroup_path = Path("/proc/self/cgroup")
            if cgroup_path.exists():
                for line in cgroup_path.read_text().splitlines():
                    parts = line.split("/")
                    if parts:
                        candidate = parts[-1]
                        if len(candidate) >= 12:
                            container_id = candidate[-12:]
                            break
        except Exception:
            pass

        return {
            "detected": is_docker,
            "containerId": container_id,
        }

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

        LOGGER.info("Saved landing content (%s bytes)", len(raw_body))

        response = json.dumps({"status": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _serve_generated_content(self):
        if not CADDYFILE_PATH.exists():
            self.send_error(404, "Caddyfile not found")
            return

        caddy_text = CADDYFILE_PATH.read_text(encoding="utf-8")
        hosts = self._parse_caddy_hosts(caddy_text)

        if not hosts:
            self.send_error(400, "No hostnames discovered in Caddyfile")
            return

        template = {}
        try:
            template = json.loads(TEMPLATE_CONTENT.read_text(encoding="utf-8"))
        except Exception:
            LOGGER.warning("Failed to load template content")

        defaults = {k: v for k, v in template.items() if k != "items"}
        generated_items = [
            {
                "name": display,
                "url": url,
                "desc": "Discovered from Caddyfile",
            }
            for display, url in hosts
        ]

        fallback_items = [
            item
            for item in template.get("items", [])
            if "caddyLander" in item.get("url", "") or "caddyserver" in item.get("url", "")
        ]

        payload = {**defaults, "items": generated_items + fallback_items}

        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _handle_caddyfile_update(self):
        raw_body = read_body(self)
        new_content = raw_body.decode("utf-8")

        LOGGER.info("Received Caddyfile update (%s bytes)", len(raw_body))

        # Step 1: Write to temp file
        TEMP_CADDYFILE.write_text(new_content, encoding="utf-8")

        # Step 2: Format
        result = subprocess.run(
            [str(CADDY_BIN), "fmt", "--overwrite", str(TEMP_CADDYFILE)],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            LOGGER.warning("Caddyfile fmt failed: %s", result.stderr.strip())
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
            LOGGER.warning("Caddyfile validation failed: %s", result.stderr.strip())
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

        LOGGER.info("Caddyfile validation succeeded")

        # Step 4: Backup previous version if exists
        CADDYFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        previous_content = ""
        if CADDYFILE_PATH.exists():
            previous_content = CADDYFILE_PATH.read_text(encoding="utf-8")

        if previous_content:
            self._backup_caddyfile(previous_content)

        # Step 5: Promote temp to real file
        shutil.move(str(TEMP_CADDYFILE), str(CADDYFILE_PATH))

        LOGGER.info("Saved validated Caddyfile to %s", CADDYFILE_PATH)

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

        LOGGER.info("Created content backup %s", backup_path)

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

        LOGGER.info("Restored landing content from backup %s", name)

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
            )[:10]
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

    def _handle_favicon_upload(self, parsed_url):
        params = parse_qs(parsed_url.query)
        target_type = params.get("type", [None])[0]
        if target_type not in {"svg", "ico"}:
            self.send_error(400, "Specify type=svg or type=ico")
            return

        raw_body = read_body(self)
        if not raw_body:
            self.send_error(400, "Missing favicon payload")
            return

        if target_type == "svg":
            if b"<svg" not in raw_body.lower():
                self.send_error(400, "Only SVG content is allowed")
                return
        if target_type == "ico":
            if len(raw_body) < 4 or raw_body[:4] != b"\x00\x00\x01\x00":
                self.send_error(400, "Only ICO content is allowed")
                return

        RUNTIME_STATIC.mkdir(parents=True, exist_ok=True)
        target_path = RUNTIME_STATIC / f"favicon.{target_type}"
        target_path.write_bytes(raw_body)

        LOGGER.info("Uploaded custom favicon: %s", target_path)

        response = json.dumps({"status": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _handle_favicon_restore(self, parsed_url):
        params = parse_qs(parsed_url.query)
        target_type = params.get("type", [None])[0]

        targets = []
        if target_type in {"svg", "ico"}:
            targets.append(RUNTIME_STATIC / f"favicon.{target_type}")
        else:
            targets.extend([RUNTIME_STATIC / "favicon.svg", RUNTIME_STATIC / "favicon.ico"])

        removed_any = False
        for path in targets:
            if path.exists():
                path.unlink(missing_ok=True)
                removed_any = True

        if removed_any:
            LOGGER.info("Restored bundled favicon assets")

        response = json.dumps({"status": "ok"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _backup_caddyfile(self, previous_content: str):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = BACKUP_DIR / f"Caddyfile.old.{timestamp}"
        backup_path.write_text(previous_content, encoding="utf-8")

        LOGGER.info("Created Caddyfile backup %s", backup_path)

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
            )[:10]
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

        LOGGER.info("Restored Caddyfile from backup %s", name)

        response = json.dumps({"status": "ok", "restart_required": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def _parse_caddy_hosts(self, text: str) -> list[tuple[str, str]]:
        hosts: list[str] = []
        tokens: list[str] = []
        brace_depth = 0

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "#" in line:
                line = line.split("#", 1)[0].strip()
            if not line:
                continue

            if brace_depth == 0:
                if "{" in line:
                    before, after = line.split("{", 1)
                    tokens.extend(before.replace(",", " ").split())
                    brace_depth += 1 + after.count("{")
                    brace_depth -= after.count("}")
                    hosts.extend(tokens)
                    tokens = []
                    continue

                tokens.extend(line.replace(",", " ").split())
            brace_depth += line.count("{")
            brace_depth -= line.count("}")
            if brace_depth < 0:
                brace_depth = 0

        cleaned: list[tuple[str, str]] = []
        seen = set()

        for token in hosts:
            candidate = token.strip().strip(",")
            if not candidate or candidate in {"import", "handle", "route"}:
                continue
            if candidate.startswith(("(", "@", ":", "/")):
                continue
            if candidate.startswith("unix/"):
                continue

            url = candidate
            if "://" in candidate:
                parsed = urlparse(candidate)
                display = parsed.hostname or candidate
                url = candidate
            else:
                display = candidate
                if candidate.startswith("*."):
                    display = candidate.removeprefix("*.")
                display = display.lstrip("*")
                port = None
                if ":" in display:
                    host_only, port = display.split(":", 1)
                    display = host_only
                scheme = "https"
                if candidate.startswith("http") or port == "80":
                    scheme = "http"
                url = f"{scheme}://{display}"

            key = (display, url)
            if display and key not in seen:
                cleaned.append(key)
                seen.add(key)

        return cleaned


if __name__ == "__main__":
    safe_logo = "\n".join(
        line for line in LOGO.splitlines() if all(ord(ch) >= 32 or ch in {"\n", "\t", " "} for ch in line)
    )
    LOGGER.info("\n%s", safe_logo)
    LOGGER.info("Starting caddyLander")
    bootstrap_content()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    LOGGER.info("caddylander running on port 8080")
    server.serve_forever()
