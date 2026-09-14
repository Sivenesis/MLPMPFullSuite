"""
Local WebGUI Server & HTTP Application Layer for MLPMP Full Suite.
Serves static assets, manages CSRF token security, and provides REST API routing.
"""

import json
import mimetypes
import os
from pathlib import Path
import secrets
import sys
import threading
import time
from urllib.parse import urlparse, parse_qs
import zipfile
from typing import Any

try:
    from http.server import ThreadingHTTPServer as DefaultHTTPServer
except ImportError:
    from http.server import HTTPServer as DefaultHTTPServer
from http.server import BaseHTTPRequestHandler

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from core.memory import mem
from server.handlers import (
    handle_get_status,
    handle_post_attach,
    handle_post_detach,
    handle_get_full_state,
    handle_mechanic_action,
    handle_get_catalog,
    handle_catalog_apply,
    handle_catalog_rescan,
    handle_store_hooks,
    handle_get_level_table,
)
from mechanics.store import store_mechanic

WEB_DIR = PROJECT_DIR / "web"
SESSION_TOKEN = secrets.token_hex(16)
_CURRENT_SERVER = None


def ensure_assets(project_dir: Path = PROJECT_DIR) -> bool:
    """Extracts portrait icons from assets_part*.zip with ZipSlip validation if directory is missing."""
    web_dir = project_dir / "web"
    portraits_dir = web_dir / "assets" / "portraits"

    if portraits_dir.is_dir():
        png_count = sum(1 for _ in portraits_dir.glob("*.png"))
        if png_count >= 100:
            return True

    zip_files = sorted(web_dir.glob("assets_part*.zip"))
    if not zip_files:
        for candidate in [web_dir / "assets.zip", project_dir / "data" / "assets.zip"]:
            if candidate.is_file():
                zip_files.append(candidate)
                break

    if not zip_files:
        return False

    names_str = ", ".join(z.name for z in zip_files)
    mem.log("ASSETS", f"Extracting character portraits from {names_str}...")
    try:
        portraits_dir.mkdir(parents=True, exist_ok=True)
        for z_path in zip_files:
            with zipfile.ZipFile(z_path, "r") as zf:
                for member in zf.infolist():
                    norm_name = os.path.normpath(member.filename)
                    if (
                        norm_name.startswith("..")
                        or os.path.isabs(norm_name)
                        or member.filename.startswith("/")
                        or member.filename.startswith("\\")
                    ):
                        raise RuntimeError(f"Zip Slip blocked: {member.filename}")

                    if not member.filename.lower().endswith(".png"):
                        continue

                    if member.filename.startswith("portraits/"):
                        dest_dir = web_dir / "assets"
                    elif member.filename.startswith("assets/"):
                        dest_dir = web_dir
                    else:
                        dest_dir = portraits_dir

                    target_path = (dest_dir / member.filename).resolve()
                    dest_resolved = dest_dir.resolve()
                    if not str(target_path).startswith(str(dest_resolved) + os.sep):
                        raise RuntimeError(f"Zip Slip blocked: {member.filename}")

                    zf.extract(member, dest_dir)
        count = sum(1 for _ in portraits_dir.glob("*.png"))
        mem.log("ASSETS", f"Extraction complete: {count} portraits unpacked to assets/portraits/.")
        return True
    except Exception as e:
        mem.log("ERROR", f"Error extracting portrait assets: {e}")
        return False


class RobustHTTPServer(DefaultHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        exc_type, _, _ = sys.exc_info()
        if exc_type in (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            return
        mem.log("ERROR", f"Server exception: {sys.exc_info()[1]}")


class SuiteRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default noisy access logs

    def _is_allowed_origin(self) -> bool:
        host = self.headers.get("Host", "").split(":")[0]
        if host and host not in ("127.0.0.1", "localhost"):
            return False
        origin = self.headers.get("Origin")
        if origin:
            parsed = urlparse(origin)
            if parsed.hostname not in ("127.0.0.1", "localhost"):
                return False
        return True

    def _verify_token(self) -> bool:
        token = self.headers.get("X-Suite-Token")
        return bool(token and secrets.compare_digest(token, SESSION_TOKEN))

    def _send_json(self, data: Any, status: int = 200):
        try:
            body = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            origin = self.headers.get("Origin")
            if origin and self._is_allowed_origin():
                self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(body)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass
        except Exception as ex:
            mem.log("ERROR", f"_send_json error: {ex}")

    def _read_json_body(self) -> dict:
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                raw_body = self.rfile.read(content_length).decode("utf-8", errors="replace")
                return json.loads(raw_body)
        except Exception as ex:
            mem.log("WARN", f"Failed parsing JSON body: {ex}")
        return {}

    def do_OPTIONS(self):
        if not self._is_allowed_origin():
            self.send_error(403, "Forbidden Origin")
            return
        self.send_response(200)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Suite-Token")
        self.end_headers()

    def do_GET(self):
        if not self._is_allowed_origin():
            self.send_error(403, "Forbidden Origin")
            return

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Flat query param helper
        params = {k: v[0] for k, v in query.items() if v}

        if path == "/api/csrf-token":
            return self._send_json({"csrf_token": SESSION_TOKEN})

        elif path == "/api/status":
            return self._send_json(handle_get_status())

        elif path == "/api/state":
            return self._send_json(handle_get_full_state())

        elif path == "/api/logs":
            return self._send_json({"logs": mem.get_logs()})

        elif path in ("/api/catalog", "/api/store/catalog"):
            refresh = bool(params.get("refresh", False))
            return self._send_json(handle_get_catalog(refresh=refresh))

        elif path in ("/api/level/table", "/api/level/progression"):
            refresh = bool(params.get("refresh", False))
            return self._send_json(handle_get_level_table(refresh=refresh))

        # Static file delivery
        self._serve_static(path)

    def do_POST(self):
        if not self._is_allowed_origin():
            self.send_error(403, "Forbidden Origin")
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if not self._verify_token():
            mem.log("WARN", f"Blocked unauthorized POST to {path} (Invalid/Missing CSRF Token)")
            return self._send_json({"success": False, "error": "Unauthorized / Invalid CSRF Token"}, 403)

        body = self._read_json_body()

        if path == "/api/attach":
            return self._send_json(handle_post_attach())

        elif path == "/api/detach":
            return self._send_json(handle_post_detach())

        elif path == "/api/logs/clear":
            mem.clear_logs()
            return self._send_json({"success": True, "message": "Logs cleared."})

        elif path == "/api/shutdown":
            mem.log("INFO", "Safe shutdown requested from WebGUI. Detaching and stopping server...")
            mem.detach()
            self._send_json({
                "success": True,
                "message": "Suite has been detached and terminated safely. It is now safe to close this browser tab.",
            })

            def _delayed_exit():
                time.sleep(0.5)
                global _CURRENT_SERVER
                if _CURRENT_SERVER:
                    _CURRENT_SERVER.shutdown()
                os._exit(0)

            threading.Thread(target=_delayed_exit, daemon=True).start()
            return

        elif path.startswith("/api/mechanic/"):
            mechanic_name = path.replace("/api/mechanic/", "").strip()
            res = handle_mechanic_action(mechanic_name, body)
            return self._send_json(res)

        elif path == "/api/catalog/apply":
            res = handle_catalog_apply(body)
            return self._send_json(res)

        elif path == "/api/catalog/rescan":
            res = handle_catalog_rescan()
            return self._send_json(res)

        elif path in ("/api/store/hooks", "/api/store/action"):
            res = handle_store_hooks(body)
            return self._send_json(res)

        self.send_error(404, "Endpoint Not Found")

    def _serve_static(self, path: str):
        if path in ("/", ""):
            path = "/index.html"

        safe_path = path.lstrip("/")
        file_path = (WEB_DIR / safe_path).resolve()

        # Prevent Directory Traversal
        try:
            if not str(file_path).startswith(str(WEB_DIR.resolve()) + os.sep) and file_path != (WEB_DIR / "index.html").resolve():
                self.send_error(403, "Access Denied")
                return
        except Exception:
            self.send_error(403, "Access Denied")
            return

        if not file_path.is_file():
            self.send_error(404, "File Not Found")
            return

        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            content_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            if safe_path.endswith((".png", ".jpg", ".svg", ".woff2")):
                self.send_header("Cache-Control", "public, max-age=86400")
            else:
                self.send_header("Cache-Control", "no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(content)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
            pass
        except Exception as ex:
            mem.log("ERROR", f"Error serving static file {path}: {ex}")


def run_server(port: int = 8080):
    global _CURRENT_SERVER
    ensure_assets(PROJECT_DIR)
    server_address = ("127.0.0.1", port)
    _CURRENT_SERVER = RobustHTTPServer(server_address, SuiteRequestHandler)
    mem.log("SERVER", f"Suite WebGUI online at http://127.0.0.1:{port}/")
    try:
        _CURRENT_SERVER.serve_forever()
    except KeyboardInterrupt:
        mem.log("SERVER", "KeyboardInterrupt detected. Detaching and exiting cleanly...")
    finally:
        mem.detach()
        _CURRENT_SERVER.server_close()
