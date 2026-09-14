"""
Test HTTP endpoints of the local server:
1. Rejects request without CSRF token (403)
2. Rejects request with payload > 1MB (413)
3. Accepts valid request with CSRF token (200)
4. Version override endpoint (/api/version/override)
"""

import sys
import os
import threading
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

V2_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2_DIR))

from server.app import RobustHTTPServer, SuiteRequestHandler, SESSION_TOKEN

PORT = 8998
server = None


def start_server():
    global server
    server = RobustHTTPServer(("127.0.0.1", PORT), SuiteRequestHandler)
    server.serve_forever()


def test_http():
    t = threading.Thread(target=start_server, daemon=True)
    t.start()
    time.sleep(0.3)

    base_url = f"http://127.0.0.1:{PORT}"

    # 1. Test GET csrf-token
    req = urllib.request.Request(f"{base_url}/api/csrf-token")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        csrf_token = data.get("csrf_token")
        assert csrf_token == SESSION_TOKEN, f"CSRF token mismatch: {csrf_token}"
        print("PASS: /api/csrf-token returned valid session token.")

    # 2. Test POST without CSRF token -> 403 Forbidden
    req = urllib.request.Request(
        f"{base_url}/api/attach",
        data=b"{}",
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 403
    except urllib.error.HTTPError as e:
        assert e.code == 403, f"Expected 403, got {e.code}"
        print("PASS: POST without CSRF token was rejected with 403.")

    # 3. Test POST with payload > 1MB -> 413 Payload Too Large
    big_payload = b"X" * (1024 * 1024 + 100) # > 1MB
    req = urllib.request.Request(
        f"{base_url}/api/mechanic/currency",
        data=big_payload,
        headers={
            "Content-Type": "application/json",
            "X-Suite-Token": csrf_token,
            "Content-Length": str(len(big_payload))
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            assert resp.status == 413
    except urllib.error.HTTPError as e:
        assert e.code == 413, f"Expected 413, got {e.code}"
        print("PASS: POST exceeding 1MB was rejected with 413 Payload Too Large.")

    # 4. Test POST /api/version/override -> 200 OK
    req = urllib.request.Request(
        f"{base_url}/api/version/override",
        data=json.dumps({"override_version": True}).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Suite-Token": csrf_token
        }
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        assert data.get("success") is True
        print("PASS: /api/version/override succeeded and confirmed override.")

    # 5. Test Path Traversal on static file -> 403 Forbidden
    req = urllib.request.Request(f"{base_url}/../../core/memory.py")
    try:
        with urllib.request.urlopen(req) as resp:
            assert False, "Should have returned 403"
    except urllib.error.HTTPError as e:
        assert e.code == 403, f"Expected 403, got {e.code}"
        print("PASS: Path traversal attempt was rejected with 403 Forbidden.")

    print("\nALL HTTP ENDPOINT HARDENING TESTS PASSED!")
    server.shutdown()


if __name__ == "__main__":
    test_http()
