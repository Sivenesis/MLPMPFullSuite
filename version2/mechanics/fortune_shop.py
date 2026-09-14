"""
Fortune Shop Refresh & Royal Club Synchronization Mechanic for MLPMP Full Suite.
Provides a concise, one-click Fortune Shop roster refresh:
- Clears the 24-hour cooldown
- Re-rolls the character roster immediately
- Sets refresh cost (0 vs 50 Gems)
- Configures 100% Rare character drop weights
- Synchronizes active Royal Club status (required by game engine for refresh functionality)
"""

import time
import struct
from typing import Dict, Any, Optional, Tuple, List
from core.memory import mem
from core.offsets import (
    RVA_FSM_POINTER,
    RVA_PLAYER_MANAGER,
    RVA_GAME_STATE,
    RVA_UI_INVALIDATE,
    RVA_FORTUNE_VIS_CHECK,
    RVA_FORTUNE_FREE_CHECK,
    ORIG_FORTUNE_VIS,
    ORIG_FORTUNE_FREE,
    OFF_FSM_AVAILABLE,
    OFF_FSM_RARITY_TREE,
    OFF_FSM_TOTAL_WEIGHT,
    OFF_FSM_DAY_NUMBER,
    OFF_FSM_REFRESH_COST,
    OFF_FSM_REQUIRED_LVL,
    OFF_FSM_LAST_REFRESH,
    OFF_FSM_FREE_AVAILABLE,
    OFF_ROYAL_CLUB_BASE,
    OFF_RC_IS_ACTIVE,
    OFF_RC_EXPIRATION,
    OFF_RC_TIER,
    OFF_RC_TIER_ACTIVE,
)
from mechanics.base import BaseMechanic


class FortuneShopMechanic(BaseMechanic):
    name = "FortuneShopMechanic"
    description = "Fortune Shop Roster Refresh & Cooldown Bypass"

    ONE_YEAR_SECONDS = 365 * 86400

    def _resolve_fsm(self) -> Optional[int]:
        if not mem.is_attached() or not mem.module_base:
            return None
        p1 = mem.read_ptr(mem.module_base + RVA_FSM_POINTER)
        if not p1 or not mem.is_valid_user_ptr(p1):
            return None
        p2 = mem.read_ptr(p1)
        if not p2 or not mem.is_valid_user_ptr(p2):
            return None
        return p2

    def get_state(self) -> Dict[str, Any]:
        state = {
            "available": False,
            "fsm_address": None,
            "cost": 50,
            "is_free": False,
            "cooldown_cleared": False,
            "royal_club_active": False,
            "force_rare": False,
        }

        fsm = self._resolve_fsm()
        if not fsm:
            return state

        state["available"] = True
        state["fsm_address"] = f"0x{fsm:X}"

        cost = mem.read_u32(fsm + OFF_FSM_REFRESH_COST) or 50
        last_ts = mem.read_u64(fsm + OFF_FSM_LAST_REFRESH) or 0
        state["cost"] = cost
        state["is_free"] = (cost == 0)
        state["cooldown_cleared"] = (last_ts == 0)

        # Check Royal Club status
        pm_addr = self.get_player_manager_addr()
        if pm_addr:
            rc_active = mem.read_u8(pm_addr + OFF_ROYAL_CLUB_BASE + OFF_RC_IS_ACTIVE)
            state["royal_club_active"] = (rc_active == 1)

        # Inspect rare weight at [FSM + 0x18]
        sentinel = mem.read_ptr(fsm + OFF_FSM_RARITY_TREE)
        if sentinel and mem.is_valid_user_ptr(sentinel):
            root = mem.read_ptr(sentinel + 8)

            def walk(n):
                if not n or n == sentinel or not mem.is_valid_user_ptr(n):
                    return []
                is_nil = mem.read_u8(n + 0x19)
                if is_nil:
                    return []
                res = []
                res.extend(walk(mem.read_ptr(n)))
                raw = mem.read_bytes(n, 0x30)
                if raw:
                    res.append(raw)
                res.extend(walk(mem.read_ptr(n + 0x10)))
                return res

            for r in walk(root):
                rid = struct.unpack_from("<I", r, 0x1C)[0]
                w = struct.unpack_from("<I", r, 0x20)[0]
                if rid == 2:  # Rare
                    state["force_rare"] = (w >= 100)

        return state

    def apply(self, payload: Dict[str, Any] = None) -> Tuple[bool, str]:
        if payload is None:
            payload = {}

        fsm = self._resolve_fsm()
        if not fsm:
            return False, "FortuneShopManager singleton not found in memory."

        cost = payload.get("cost", 0)
        force_rare = payload.get("force_rare", True)
        target_cost = max(0, min(int(cost), 9999))

        base = mem.module_base

        # 1. Restore vanilla code bytes in FortuneShopDialog::Update to ensure native execution
        mem.write_bytes(base + RVA_FORTUNE_VIS_CHECK, ORIG_FORTUNE_VIS)
        mem.write_bytes(base + RVA_FORTUNE_FREE_CHECK, ORIG_FORTUNE_FREE)

        # 2. Activate Royal Club / VIP membership at [ResourceManager + 0xDA0]
        # Required because Fortune Shop refresh is natively an exclusive Royal Club perk.
        pm_addr = self.get_player_manager_addr()
        if pm_addr:
            rc_addr = pm_addr + OFF_ROYAL_CLUB_BASE
            safe_future_ts = int(time.time()) + self.ONE_YEAR_SECONDS
            mem.write_u8(rc_addr + OFF_RC_IS_ACTIVE, 1)
            mem.write_u64(rc_addr + OFF_RC_EXPIRATION, safe_future_ts)
            mem.write_u8(rc_addr + OFF_RC_TIER, 1)       # Tier 2
            mem.write_u8(rc_addr + OFF_RC_TIER_ACTIVE, 1)

        # 3. Patch FortuneShopManager fields
        mem.write_u8(fsm + OFF_FSM_AVAILABLE, 1)
        mem.write_u32(fsm + OFF_FSM_REFRESH_COST, target_cost)
        mem.write_u32(fsm + OFF_FSM_REQUIRED_LVL, 1)
        mem.write_u64(fsm + OFF_FSM_LAST_REFRESH, 0)     # Clear 24h cooldown
        mem.write_u8(fsm + OFF_FSM_FREE_AVAILABLE, 0)

        # 4. Reset GameState + 0x13DA (FortuneShopRefreshSeen)
        gs_ptr = mem.read_ptr(base + RVA_GAME_STATE)
        if gs_ptr and mem.is_valid_user_ptr(gs_ptr):
            mem.write_u8(gs_ptr + 0x13DA, 0)

        # 5. Invalidate UI cache at [base + RVA_UI_INVALIDATE] to show refresh button immediately
        mem.write_bytes(base + RVA_UI_INVALIDATE, struct.pack("<i", -1))

        # 6. Patch Rarity Weights at [FSM + 0x18]
        sentinel = mem.read_ptr(fsm + OFF_FSM_RARITY_TREE)
        if sentinel and mem.is_valid_user_ptr(sentinel):
            root = mem.read_ptr(sentinel + 8)

            def walk_nodes(node):
                if not node or node == sentinel or not mem.is_valid_user_ptr(node):
                    return []
                is_nil = mem.read_u8(node + 0x19)
                if is_nil:
                    return []
                res = []
                res.extend(walk_nodes(mem.read_ptr(node)))
                raw_node = mem.read_bytes(node, 0x30)
                if raw_node:
                    res.append((node, raw_node))
                res.extend(walk_nodes(mem.read_ptr(node + 0x10)))
                return res

            for n_addr, raw_node in walk_nodes(root):
                r_id = struct.unpack_from("<I", raw_node, 0x1C)[0]
                if force_rare:
                    target_w = 100 if r_id == 2 else 0
                else:
                    target_w = 50 if r_id == 0 else 35 if r_id == 1 else 15
                mem.write_u32(n_addr + 0x20, target_w)

            mem.write_u32(fsm + OFF_FSM_TOTAL_WEIGHT, 100)

        # 7. Crucial: Write 0 to [fsm + 0x78] (day_number)
        # Causes native Update (vfunc[4] at 0x4FC282) to detect day 0 != today,
        # immediately rolling a fresh roster and saving today's day number!
        mem.write_u64(fsm + OFF_FSM_DAY_NUMBER, 0)

        msg = "Fortune Shop refreshed (24-hour cooldown cleared, roster re-rolled, Royal Club synchronized)."
        mem.log("SUCCESS", f"[Fortune] {msg}")
        return True, msg


fortune_shop_mechanic = FortuneShopMechanic()
