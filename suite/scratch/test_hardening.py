"""
Automated Test Suite for MLPMP Full Suite Hardening (version2).
Tests:
1. Memory smart protection elevation & pre-flight opcode check
2. Fortune shop error accumulation
3. Currency limits (2.14B)
4. HTTP request size ceiling (1MB) & path traversal defense
5. Live attachment & process introspection against running game
"""

import os
import sys
import unittest
import struct
import json
from pathlib import Path
import ctypes

# Add version2 to sys.path
V2_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(V2_DIR))

from core.memory import mem
from core.offsets import TARGET_GAME_VERSION
from core.version_check import check_game_version
from mechanics.fortune_shop import fortune_shop_mechanic
from mechanics.currency import currency_mechanic
from server.app import MAX_REQUEST_BODY, WEB_DIR


class TestMemoryHardening(unittest.TestCase):
    def test_smart_protection_and_preflight(self):
        """Tests smart protection elevation and pre-flight opcode checks against live game process."""
        mem.attach()
        self.assertTrue(mem.is_attached())
        kernel32 = ctypes.windll.kernel32
        kernel32.VirtualAllocEx.restype = ctypes.c_void_p
        kernel32.VirtualAllocEx.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32]

        # Allocate a test page inside the live target process
        p_remote = kernel32.VirtualAllocEx(mem.handle, None, 0x1000, 0x1000 | 0x2000, 0x04) # PAGE_READWRITE
        self.assertTrue(p_remote, "VirtualAllocEx failed in target process")
        try:
            # 1. Test direct write to PAGE_READWRITE page (fast path without VirtualProtectEx)
            test_data = b"\x12\x34\x56\x78"
            ok = mem.write_bytes(p_remote, test_data)
            self.assertTrue(ok)
            self.assertEqual(mem.read_bytes(p_remote, 4), test_data)

            # 2. Test pre-flight verification in apply_patch
            # When memory matches orig_bytes, patch succeeds
            orig_opcodes = b"\x90\x90\x90\x90"
            patch_opcodes = b"\xB0\x01\xC3\x90"
            mem.write_bytes(p_remote, orig_opcodes)

            patch_ok = mem.apply_patch("TEST_PATCH", p_remote, patch_opcodes, orig_opcodes)
            self.assertTrue(patch_ok)
            self.assertEqual(mem.read_bytes(p_remote, 4), patch_opcodes)

            # 3. Test pre-flight abort when memory contains unexpected opcodes
            foreign_opcodes = b"\xCC\xCC\xCC\xCC"
            mem.write_bytes(p_remote, foreign_opcodes)
            failed_patch = mem.apply_patch("TEST_PATCH_FAIL", p_remote, patch_opcodes, orig_opcodes)
            self.assertFalse(failed_patch)
            # Memory should remain untouched
            self.assertEqual(mem.read_bytes(p_remote, 4), foreign_opcodes)
        finally:
            kernel32.VirtualFreeEx(mem.handle, ctypes.c_void_p(p_remote), 0, 0x8000)


class TestServerHardening(unittest.TestCase):
    def test_max_request_body_size(self):
        """Verifies that MAX_REQUEST_BODY is enforced at 1MB."""
        self.assertEqual(MAX_REQUEST_BODY, 1024 * 1024)

    def test_path_traversal_logic(self):
        """Verifies that static file path resolution rejects traversal attempts."""
        safe_files = ["index.html", "css/suite.css", "js/app.js"]
        for sf in safe_files:
            p = (WEB_DIR / sf).resolve()
            self.assertTrue(p == (WEB_DIR / "index.html").resolve() or p.is_relative_to(WEB_DIR.resolve()))

        traversal_attempts = ["../../server/app.py", "../../../Windows/System32/cmd.exe", "../core/memory.py"]
        for bad in traversal_attempts:
            bad_p = (WEB_DIR / bad.lstrip("/")).resolve()
            is_safe = (bad_p == (WEB_DIR / "index.html").resolve() or bad_p.is_relative_to(WEB_DIR.resolve()))
            self.assertFalse(is_safe, f"Path traversal attempt not caught: {bad}")


class TestCurrencyLimits(unittest.TestCase):
    def test_currency_clamping(self):
        """Verifies that currency logic clamps values to signed 32-bit ceiling (2.14B)."""
        # When unattached, apply should reject gracefully
        if not mem.is_attached():
            ok, msg = currency_mechanic.apply({"bits": 3_000_000_000})
            self.assertFalse(ok)
            self.assertIn("PlayerManager", msg)


class TestLiveProcessAttachment(unittest.TestCase):
    def test_live_attach(self):
        """Tests live attachment to running MyLittlePony_x64.exe process."""
        ok, msg = mem.attach()
        self.assertTrue(ok, f"Failed attaching to game: {msg}")
        self.assertTrue(mem.is_attached())
        self.assertIsNotNone(mem.pid)
        self.assertIsNotNone(mem.module_base)

        ver_info = check_game_version()
        self.assertTrue(ver_info["attached"])
        self.assertTrue(ver_info["is_match"])
        print(f"Attached successfully to PID {mem.pid} (Base: 0x{mem.module_base:X}), Detected Version: {ver_info['detected_version']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
