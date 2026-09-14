"""
Core Win32 Memory Management & Process Manipulation Subsystem for MLPMP Full Suite.
Provides safe, isolated, and deterministic process attachment, memory reading/writing,
page protection management, and thread-safe internal logging.
"""

import ctypes
from ctypes import wintypes
import os
import struct
import threading
import time
from typing import Optional, Dict, Any, List, Tuple
from core.offsets import TARGET_EXE_NAME

# Win32 Process Security Flags
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ           = 0x0010
PROCESS_VM_WRITE          = 0x0020
PROCESS_VM_OPERATION      = 0x0008
PROCESS_SAFE_RIGHTS       = (
    PROCESS_QUERY_INFORMATION | PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION
)  # 0x0438

PAGE_EXECUTE_READWRITE    = 0x40
TH32CS_SNAPPROCESS        = 0x00000002

class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]

# Win32 API Bindings
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

OpenProcess = kernel32.OpenProcess
OpenProcess.restype = wintypes.HANDLE
OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

CloseHandle = kernel32.CloseHandle
CloseHandle.restype = wintypes.BOOL
CloseHandle.argtypes = [wintypes.HANDLE]

CreateToolhelp32Snapshot = kernel32.CreateToolhelp32Snapshot
CreateToolhelp32Snapshot.restype = wintypes.HANDLE
CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]

Process32First = kernel32.Process32First
Process32First.restype = wintypes.BOOL
Process32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]

Process32Next = kernel32.Process32Next
Process32Next.restype = wintypes.BOOL
Process32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32)]

VirtualProtectEx = kernel32.VirtualProtectEx
VirtualProtectEx.restype = wintypes.BOOL
VirtualProtectEx.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_size_t,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]

ReadProcessMemory = kernel32.ReadProcessMemory
ReadProcessMemory.restype = wintypes.BOOL
ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]

WriteProcessMemory = kernel32.WriteProcessMemory
WriteProcessMemory.restype = wintypes.BOOL
WriteProcessMemory.argtypes = [
    wintypes.HANDLE,
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]


class MemoryManager:
    """Singleton engine managing live RAM access to the target game process."""

    def __init__(self):
        self._lock = threading.RLock()
        self.pid: Optional[int] = None
        self.handle: Optional[wintypes.HANDLE] = None
        self.module_base: Optional[int] = None
        self._log_history: List[Dict[str, Any]] = []
        self._max_logs = 500
        self._applied_patches: Dict[str, Tuple[int, bytes]] = {}

        # Initialize logging directory
        proj_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.logs_dir = os.path.join(proj_dir, "logs")
        try:
            os.makedirs(self.logs_dir, exist_ok=True)
            self.log_file = os.path.join(self.logs_dir, "suite_debug.log")
        except Exception:
            self.log_file = None

        self.log("INIT", "Core Win32 Memory Engine initialized. Standing by for attach.")

    def log(self, level: str, message: str):
        """Records an internal debug log entry."""
        time_short = time.strftime("%H:%M:%S")
        time_full = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "timestamp": time_short,
            "level": level.upper(),
            "message": message,
        }
        with self._lock:
            self._log_history.append(entry)
            if len(self._log_history) > self._max_logs:
                self._log_history.pop(0)

            if self.log_file:
                try:
                    with open(self.log_file, "a", encoding="utf-8") as f:
                        f.write(f"[{time_full}] [{level.upper():7s}] {message}\n")
                except Exception:
                    pass
        print(f"[{entry['timestamp']}] [{entry['level']}] {entry['message']}")

    def get_logs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._log_history)

    def clear_logs(self):
        with self._lock:
            self._log_history.clear()
            self.log("INFO", "Log history cleared.")

    def find_process(self, exe_name: str = TARGET_EXE_NAME) -> Optional[int]:
        """Finds the Process ID for the target executable."""
        h_snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if not h_snap or h_snap == ctypes.c_void_p(-1).value:
            return None

        pe = PROCESSENTRY32()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
        target = exe_name.lower()

        try:
            if Process32First(h_snap, ctypes.byref(pe)):
                while True:
                    cur_name = pe.szExeFile.decode("latin-1", errors="ignore").rstrip("\x00").lower()
                    if cur_name == target:
                        return pe.th32ProcessID
                    if not Process32Next(h_snap, ctypes.byref(pe)):
                        break
        finally:
            CloseHandle(h_snap)
        return None

    def is_attached(self) -> bool:
        with self._lock:
            if not self.handle or not self.pid:
                return False
            # Verify process is still alive
            exit_code = wintypes.DWORD()
            if kernel32.GetExitCodeProcess(self.handle, ctypes.byref(exit_code)):
                return exit_code.value == 259  # STILL_ACTIVE
            return False

    def attach(self) -> Tuple[bool, str]:
        """
        Explicitly attaches to MyLittlePony_x64.exe.
        Never attaches automatically upon initialization.
        """
        with self._lock:
            if self.is_attached():
                return True, f"Already attached to PID {self.pid} (Base: 0x{self.module_base:X})"

            pid = self.find_process()
            if not pid:
                self.log("WARN", f"Target process '{TARGET_EXE_NAME}' not found running.")
                return False, f"Game process '{TARGET_EXE_NAME}' is not running."

            h_proc = OpenProcess(PROCESS_SAFE_RIGHTS, False, pid)
            if not h_proc:
                err = ctypes.get_last_error()
                self.log("ERROR", f"OpenProcess failed for PID {pid} (Win32 Error: {err}). Run as Administrator if needed.")
                return False, f"Failed to open process (Win32 Error {err})."

            base = self._resolve_main_module_base(h_proc)
            if not base:
                CloseHandle(h_proc)
                self.log("ERROR", f"Failed to resolve main module base for PID {pid}.")
                return False, "Failed to resolve executable module base address."

            self.pid = pid
            self.handle = h_proc
            self.module_base = base
            self.log("SUCCESS", f"Successfully attached to {TARGET_EXE_NAME} (PID: {pid}, Module Base: 0x{base:X}).")
            return True, f"Successfully attached to PID {pid}."

    def detach(self) -> bool:
        """Detaches from game process, reverting any temporary applied patches."""
        with self._lock:
            if not self.handle:
                return True

            # Revert any active registered patches
            if self._applied_patches:
                self.log("INFO", f"Reverting {len(self._applied_patches)} active memory patches upon detach...")
                for name, (addr, orig_bytes) in list(self._applied_patches.items()):
                    self.write_bytes(addr, orig_bytes)
                self._applied_patches.clear()

            CloseHandle(self.handle)
            self.log("INFO", f"Detached from PID {self.pid}.")
            self.handle = None
            self.pid = None
            self.module_base = None
            return True

    def _resolve_main_module_base(self, h_proc: wintypes.HANDLE) -> Optional[int]:
        hmods = (ctypes.c_void_p * 1024)()
        cb_needed = wintypes.DWORD()
        if psapi.EnumProcessModules(h_proc, hmods, ctypes.sizeof(hmods), ctypes.byref(cb_needed)):
            return hmods[0]
        return None

    @staticmethod
    def is_valid_user_ptr(ptr: Any) -> bool:
        """Validates that a 64-bit address resides within user-mode virtual memory."""
        return isinstance(ptr, int) and 0x10000 <= ptr <= 0x7FFFFFFFFFFF

    def read_bytes(self, address: int, length: int) -> Optional[bytes]:
        """Reads raw bytes from process memory."""
        with self._lock:
            if not self.is_attached() or not self.is_valid_user_ptr(address):
                return None

            buf = ctypes.create_string_buffer(length)
            read = ctypes.c_size_t()
            if ReadProcessMemory(self.handle, ctypes.c_void_p(address), buf, length, ctypes.byref(read)):
                return buf.raw[:read.value]
            return None

    def write_bytes(self, address: int, data: bytes) -> bool:
        """Safely writes bytes to process memory with VirtualProtectEx protection elevation."""
        with self._lock:
            if not self.is_attached() or not self.is_valid_user_ptr(address):
                return False

            old_protect = wintypes.DWORD()
            written = ctypes.c_size_t()
            length = len(data)

            if not VirtualProtectEx(self.handle, ctypes.c_void_p(address), length, PAGE_EXECUTE_READWRITE, ctypes.byref(old_protect)):
                return False

            ok = WriteProcessMemory(self.handle, ctypes.c_void_p(address), data, length, ctypes.byref(written))
            VirtualProtectEx(self.handle, ctypes.c_void_p(address), length, old_protect.value, ctypes.byref(old_protect))
            return bool(ok and written.value == length)

    def read_ptr(self, address: int) -> int:
        raw = self.read_bytes(address, 8)
        return struct.unpack("<Q", raw)[0] if raw and len(raw) == 8 else 0

    def read_u8(self, address: int) -> Optional[int]:
        raw = self.read_bytes(address, 1)
        return raw[0] if raw else None

    def read_u32(self, address: int) -> Optional[int]:
        raw = self.read_bytes(address, 4)
        return struct.unpack("<I", raw)[0] if raw and len(raw) == 4 else None

    def read_u64(self, address: int) -> Optional[int]:
        raw = self.read_bytes(address, 8)
        return struct.unpack("<Q", raw)[0] if raw and len(raw) == 8 else None

    def read_float(self, address: int) -> Optional[float]:
        raw = self.read_bytes(address, 4)
        return struct.unpack("<f", raw)[0] if raw and len(raw) == 4 else None

    def read_double(self, address: int) -> Optional[float]:
        raw = self.read_bytes(address, 8)
        return struct.unpack("<d", raw)[0] if raw and len(raw) == 8 else None

    def write_u8(self, address: int, val: int) -> bool:
        return self.write_bytes(address, bytes([val & 0xFF]))

    def write_u32(self, address: int, val: int) -> bool:
        return self.write_bytes(address, struct.pack("<I", int(val) & 0xFFFFFFFF))

    def write_u64(self, address: int, val: int) -> bool:
        return self.write_bytes(address, struct.pack("<Q", int(val) & 0xFFFFFFFFFFFFFFFF))

    def write_float(self, address: int, val: float) -> bool:
        return self.write_bytes(address, struct.pack("<f", float(val)))

    def write_double(self, address: int, val: float) -> bool:
        return self.write_bytes(address, struct.pack("<d", float(val)))

    def read_string(self, address: int, max_len: int = 64) -> str:
        raw = self.read_bytes(address, max_len)
        if not raw:
            return ""
        return raw.split(b"\x00")[0].decode("latin-1", errors="ignore")

    def apply_patch(self, name: str, address: int, patch_bytes: bytes, orig_bytes: Optional[bytes] = None) -> bool:
        """Applies a code/data patch and records original bytes for clean detachment."""
        with self._lock:
            if orig_bytes is None and name not in self._applied_patches:
                cur = self.read_bytes(address, len(patch_bytes))
                if cur and cur != patch_bytes:
                    orig_bytes = cur

            if orig_bytes and name not in self._applied_patches:
                self._applied_patches[name] = (address, orig_bytes)

            ok = self.write_bytes(address, patch_bytes)
            if ok:
                self.log("HOOK", f"Applied patch '{name}' at 0x{address:X} ({len(patch_bytes)} bytes).")
            else:
                self.log("ERROR", f"Failed to apply patch '{name}' at 0x{address:X}.")
            return ok

    def restore_patch(self, name: str, address: int, orig_bytes: bytes) -> bool:
        with self._lock:
            ok = self.write_bytes(address, orig_bytes)
            if name in self._applied_patches:
                del self._applied_patches[name]
            if ok:
                self.log("HOOK", f"Restored patch '{name}' at 0x{address:X} to vanilla bytes.")
            return ok


# Global memory manager instance
mem = MemoryManager()
