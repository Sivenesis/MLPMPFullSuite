"""
Game Executable & Build Version Detection for MLPMP Full Suite.
Inspects live game process memory and package metadata to verify client version compatibility.
"""

from typing import Dict, Any, Optional
from core.memory import mem
from core.offsets import TARGET_GAME_VERSION

RVA_VERSION_STRING = 0x1548D90  # 11.4.2a: 0x154DC30


def check_game_version() -> Dict[str, Any]:
    """
    Validates whether the attached or running game process matches the expected version.
    Target: Client v11.5.0 (Package build 11.5.0.0 or version string 11.5.0).
    """
    if not mem.is_attached():
        return {
            "attached": False,
            "detected_version": "Not Attached",
            "expected_version": f"v{TARGET_GAME_VERSION}",
            "is_match": True,  # Neutral before attach
            "warning": None,
        }

    detected = mem.read_string(mem.module_base + RVA_VERSION_STRING, 16).strip()
    if not detected:
        detected = "Unknown Build"

    # In Gameloft's Windows PC package, string '11.5.0' corresponds to client 'v11.5.0'
    is_compatible = detected.startswith("11.5") or detected == TARGET_GAME_VERSION

    display_version = "v11.5.0" if is_compatible else detected

    return {
        "attached": True,
        "raw_string": detected,
        "detected_version": display_version,
        "expected_version": f"v{TARGET_GAME_VERSION}",
        "is_match": is_compatible,
        "warning": None if is_compatible else (
            f"Game version mismatch detected! Found '{detected}', expected 'v{TARGET_GAME_VERSION}'. "
            "Offsets and memory layouts may be shifted or altered. Using this Suite on an untested game version may cause instability or unexpected behavior."
        ),
    }
