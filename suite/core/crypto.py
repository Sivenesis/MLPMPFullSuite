"""
Cryptographic routines and Gameloft container codec utilities for MLPMP Full Suite.
Handles 32-bit bitwise rotation (ROL32/ROR32) and in-memory container ciphering.
"""

import random
import struct
from typing import Optional, Dict, Any, Tuple


def rol32(val: int, r: int) -> int:
    """32-bit bitwise left rotation."""
    return ((val << r) | (val >> (32 - r))) & 0xFFFFFFFF


def ror32(val: int, r: int) -> int:
    """32-bit bitwise right rotation."""
    return ((val >> r) | ((val << (32 - r)) & 0xFFFFFFFF)) & 0xFFFFFFFF


def decode_container_20(raw_data: bytes, offset: int = 0) -> Optional[Dict[str, Any]]:
    """
    Decodes a 20-byte Gameloft encrypted container:
    [uint32 v1, uint32 v2, uint32 k1, uint32 k2, uint32 shadow]
    Cipher: ROR32(v ^ k, 5)
    """
    if not raw_data or len(raw_data) < offset + 20:
        return None

    v1, v2, k1, k2, shadow = struct.unpack_from("<IIIII", raw_data, offset)
    dec1 = ror32(v1 ^ k1, 5)
    dec2 = ror32(v2 ^ k2, 5)
    is_valid = (dec1 == dec2 == shadow)

    return {
        "value": shadow if is_valid else dec1,
        "shadow": shadow,
        "dec1": dec1,
        "dec2": dec2,
        "k1": k1,
        "k2": k2,
        "v1": v1,
        "v2": v2,
        "valid": is_valid,
    }


def encode_container_20(val: int, k1: Optional[int] = None, k2: Optional[int] = None) -> bytes:
    """
    Encodes a 32-bit integer into a 20-byte Gameloft encrypted container.
    Preserves key entropy or generates random 16-bit keys.
    """
    val = int(val) & 0xFFFFFFFF
    if k1 is None:
        k1 = random.randint(0x1000, 0xFFFF)
    if k2 is None:
        k2 = random.randint(0x1000, 0xFFFF)

    rot = rol32(val, 5)
    v1 = rot ^ k1
    v2 = rot ^ k2
    shadow = val

    return struct.pack("<IIIII", v1, v2, k1, k2, shadow)


def decode_token_16(raw_data: bytes, offset: int = 0) -> Optional[Dict[str, Any]]:
    """
    Decodes a 16-byte token node value container:
    [uint32 v1, uint32 v2, uint32 k1, uint32 k2]
    """
    if not raw_data or len(raw_data) < offset + 16:
        return None

    v1, v2, k1, k2 = struct.unpack_from("<IIII", raw_data, offset)
    if k1 != 0 or k2 != 0:
        dec1 = ror32(v1 ^ k1, 5)
        dec2 = ror32(v2 ^ k2, 5)
        valid = (dec1 == dec2)
        val = dec1
    else:
        valid = True
        val = v1

    return {
        "value": val,
        "dec1": dec1 if (k1 or k2) else v1,
        "dec2": dec2 if (k1 or k2) else v1,
        "k1": k1,
        "k2": k2,
        "valid": valid,
    }


def encode_token_16(val: int, k1: Optional[int] = None, k2: Optional[int] = None) -> bytes:
    """
    Encodes a 32-bit integer into a 16-byte token node value container.
    """
    val = max(0, min(int(val), 2000000000))
    if k1 is None or k1 == 0:
        k1 = 0x1A2B3C4D
    if k2 is None or k2 == 0:
        k2 = 0x5E6F7A8B

    rol_val = rol32(val, 5)
    new_v1 = rol_val ^ k1
    new_v2 = rol_val ^ k2
    return struct.pack("<IIII", new_v1, new_v2, k1, k2)
