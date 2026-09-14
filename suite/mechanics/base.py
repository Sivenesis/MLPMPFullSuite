"""
Abstract Base Mechanic & Shared Memory Traversal Services for MLPMP Full Suite.
Provides common pointer resolution, token list traversal, and validation methods.
"""

from abc import ABC, abstractmethod
import struct
import threading
from typing import Dict, Any, Optional, Tuple, Set

from core.memory import mem
from core.offsets import (
    RVA_PLAYER_MANAGER,
    OFF_TOKEN_MAP_PRIMARY,
    OFF_TOKEN_MAP_SECONDARY,
)
from core.crypto import decode_token_16, encode_token_16


class BaseMechanic(ABC):
    """Abstract base class for all game mechanic handlers."""

    name: str = "BaseMechanic"
    description: str = ""

    def __init__(self):
        self._lock = threading.RLock()
        self._token_node_cache: Dict[str, int] = {}

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Returns the current live state of the mechanic."""
        pass

    @abstractmethod
    def apply(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        """Applies requested modifications to live RAM."""
        pass

    def get_player_manager_addr(self) -> Optional[int]:
        """Resolves the active PlayerManager instance address."""
        if not mem.is_attached() or not mem.module_base:
            return None
        ptr = mem.read_ptr(mem.module_base + RVA_PLAYER_MANAGER)
        return ptr if mem.is_valid_user_ptr(ptr) else None

    def find_token_node(self, token_name: str) -> Optional[int]:
        """
        Traverses the token linked list in PlayerManager to find the node for token_name.
        Caches resolved node pointers for rapid subsequent reads/writes.
        """
        pm_addr = self.get_player_manager_addr()
        if not pm_addr:
            return None

        # Verify cached node
        cached = self._token_node_cache.get(token_name)
        if cached and mem.is_valid_user_ptr(cached):
            node_raw = mem.read_bytes(cached, 0x30)
            if node_raw:
                hs_ptr = struct.unpack_from("<Q", node_raw, 0x10)[0]
                if mem.is_valid_user_ptr(hs_ptr):
                    hs_raw = mem.read_bytes(hs_ptr, 16)
                    if hs_raw:
                        s_len, _, s_ptr = struct.unpack("<IIQ", hs_raw)
                        if 0 < s_len < 100 and mem.is_valid_user_ptr(s_ptr):
                            name_b = mem.read_bytes(s_ptr, s_len)
                            if name_b and name_b.split(b"\x00")[0].decode("latin-1", errors="ignore") == token_name:
                                return cached
            del self._token_node_cache[token_name]

        for off in (OFF_TOKEN_MAP_PRIMARY, OFF_TOKEN_MAP_SECONDARY):
            sentinel = mem.read_ptr(pm_addr + off)
            if not mem.is_valid_user_ptr(sentinel):
                continue

            curr = mem.read_ptr(sentinel + 0x08)
            visited: Set[int] = set()
            while curr and curr != sentinel and curr not in visited and len(visited) < 400:
                visited.add(curr)
                node_raw = mem.read_bytes(curr, 0x30)
                if not node_raw:
                    break

                next_ptr = struct.unpack_from("<Q", node_raw, 0x08)[0]
                hs_ptr = struct.unpack_from("<Q", node_raw, 0x10)[0]
                if mem.is_valid_user_ptr(hs_ptr):
                    hs_raw = mem.read_bytes(hs_ptr, 16)
                    if hs_raw:
                        s_len, _, s_ptr = struct.unpack("<IIQ", hs_raw)
                        if 0 < s_len < 100 and mem.is_valid_user_ptr(s_ptr):
                            name_b = mem.read_bytes(s_ptr, s_len)
                            if name_b:
                                clean_name = name_b.split(b"\x00")[0].decode("latin-1", errors="ignore")
                                if clean_name:
                                    self._token_node_cache[clean_name] = curr
                                if clean_name == token_name:
                                    return curr
                curr = next_ptr

        return None

    def read_token_value(self, token_name: str) -> Optional[int]:
        """Reads and decodes the integer value of a named token container."""
        node = self.find_token_node(token_name)
        if not node:
            return None
        raw = mem.read_bytes(node + 0x18, 16)
        if raw and len(raw) == 16:
            decoded = decode_token_16(raw)
            return decoded["value"] if decoded else None
        return None

    def write_token_value(self, token_name: str, amount: int) -> bool:
        """Encodes and writes an integer value to a named token container."""
        node = self.find_token_node(token_name)
        if not node:
            return False
        raw = mem.read_bytes(node + 0x18, 16)
        k1, k2 = None, None
        if raw and len(raw) == 16:
            v1, v2, rk1, rk2 = struct.unpack("<IIII", raw)
            if rk1 != 0 or rk2 != 0:
                k1, k2 = rk1, rk2
        new_data = encode_token_16(amount, k1, k2)
        return mem.write_bytes(node + 0x18, new_data)
