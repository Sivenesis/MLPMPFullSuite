"""
REST API Request Dispatchers & Route Handlers for MLPMP Full Suite.
Coordinates state polling, mechanic execution, and system management.
"""

from typing import Dict, Any, Optional
from core.memory import mem
from core.version_check import check_game_version
from core.offsets import SUITE_VERSION, TARGET_GAME_VERSION
from mechanics import (
    level_mechanic,
    currency_mechanic,
    profile_mechanic,
    costumes_mechanic,
    group_quests_mechanic,
    boosters_mechanic,
    find_a_pair_mechanic,
    ferris_wheel_mechanic,
    fortune_shop_mechanic,
    store_mechanic,
    MECHANICS,
)


def handle_get_status() -> Dict[str, Any]:
    """Returns top-level process attachment, version validation, and PID status."""
    is_attached = mem.is_attached()
    ver_info = check_game_version()
    return {
        "suite_version": SUITE_VERSION,
        "target_game_version": f"v{TARGET_GAME_VERSION}",
        "attached": is_attached,
        "pid": mem.pid,
        "module_base": f"0x{mem.module_base:X}" if mem.module_base else None,
        "version_info": ver_info,
    }


def handle_post_attach() -> Dict[str, Any]:
    """Explicit user-requested attachment to game process."""
    ok, msg = mem.attach()
    ver_info = check_game_version()
    return {
        "success": ok,
        "message": msg,
        "status": handle_get_status(),
        "version_info": ver_info,
    }


def handle_post_detach() -> Dict[str, Any]:
    """Explicit user-requested detachment."""
    ok = mem.detach()
    return {
        "success": ok,
        "message": "Detached from game process and reverted session patches.",
        "status": handle_get_status(),
    }


def handle_get_full_state() -> Dict[str, Any]:
    """Aggregated full state snapshot for all Suite mechanics."""
    status = handle_get_status()
    if not status["attached"]:
        return {
            "status": status,
            "attached": False,
        }

    return {
        "status": status,
        "attached": True,
        "level": level_mechanic.get_state(),
        "currency": currency_mechanic.get_state(),
        "profile": profile_mechanic.get_state(),
        "costumes": costumes_mechanic.get_state(),
        "group_quests": group_quests_mechanic.get_state(),
        "boosters": boosters_mechanic.get_state(),
        "find_a_pair": find_a_pair_mechanic.get_state(),
        "ferris_wheel": ferris_wheel_mechanic.get_state(),
        "fortune_shop": fortune_shop_mechanic.get_state(),
        "store": store_mechanic.get_state(),
    }


def handle_mechanic_action(mechanic_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatches an action payload to the specified mechanic."""
    mech = MECHANICS.get(mechanic_name)
    if not mech:
        return {
            "success": False,
            "message": f"Unknown mechanic '{mechanic_name}'.",
        }

    if not mem.is_attached():
        return {
            "success": False,
            "message": "Suite is not attached to the game process. Please click 'Attach' first.",
        }

    ok, msg = mech.apply(payload)
    return {
        "success": ok,
        "message": msg,
        "state": mech.get_state(),
    }


def handle_get_catalog(refresh: bool = False) -> Dict[str, Any]:
    """Fetches the 2,381-character catalog with live RAM b125 states."""
    return store_mechanic.get_shop_catalog(refresh_from_ram=refresh)


def handle_catalog_apply(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Applies custom pony selection in live game RAM."""
    selected_ids = payload.get("selected_ids", None)
    return store_mechanic.apply_pony_selection(selected_ids)


def handle_catalog_rescan() -> Dict[str, Any]:
    """Re-scans catalog directly from live RAM."""
    return store_mechanic.rescan_catalog_from_ram()


def handle_store_hooks(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Applies or reverts store patches."""
    action = payload.get("action", "apply")
    if action == "apply":
        ok, msg = store_mechanic.apply_store_patches()
    else:
        ok, msg = store_mechanic.revert_store_patches()
    return {
        "success": ok,
        "message": msg,
        "patches": store_mechanic.get_patch_status(),
    }


def handle_get_level_table(refresh: bool = False) -> Dict[str, Any]:
    """Returns the full 200-level progression and required XP table."""
    table = level_mechanic.get_level_table(force_refresh=refresh)
    return {
        "success": True,
        "total_levels": len(table),
        "table": table,
    }

