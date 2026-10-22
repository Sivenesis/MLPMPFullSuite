"""
Fortune Shop Continuous Refresh Mechanic for MLPMP Full Suite.

Clean, Royal-Club-free approach (11.5.0):
- Each paid refresh, the game's "mark refresh used" routine (0x4F98A0) writes FSM[+0x99]=1,
  which hides the in-game 50-gem refresh button (daily paid-refresh limit). NOP'ing that single
  7-byte write (RVA_FORTUNE_REFRESH_USED) means the counter never increments, so the green
  50-gem button is ALWAYS available - the player re-rolls the roster for 50 gems as many times
  as they like via the normal in-game button.
- Royal Club is NEVER touched (unlike the legacy build, which force-flipped VIP status).
- A single in-place code patch (not a background worker) - race-free and reverts cleanly.
- Optional: force rare drop odds; one-shot immediate re-roll.
"""

import struct
from typing import Dict, Any, Optional, Tuple
from core.memory import mem
from core.offsets import (
    RVA_FSM_POINTER,
    RVA_UI_INVALIDATE,
    RVA_FORTUNE_REFRESH_USED,
    ORIG_FORTUNE_REFRESH_USED,
    PATCH_FORTUNE_REFRESH_USED,
    OFF_FSM_RARITY_TREE,
    OFF_FSM_TOTAL_WEIGHT,
    OFF_FSM_REFRESH_COST,
    OFF_FSM_DAY_NUMBER,
    OFF_FSM_PAID_REFRESH_COUNT,
)
from mechanics.base import BaseMechanic


class FortuneShopMechanic(BaseMechanic):
    name = "FortuneShopMechanic"
    description = "Fortune Shop Continuous 50-Gem Refresh (no Royal Club)"

    def _resolve_fsm(self) -> Optional[int]:
        """Double-dereference the FortuneShopManager singleton."""
        if not mem.is_attached() or not mem.module_base:
            return None
        p1 = mem.read_ptr(mem.module_base + RVA_FSM_POINTER)
        if not p1 or not mem.is_valid_user_ptr(p1):
            return None
        p2 = mem.read_ptr(p1)
        if not p2 or not mem.is_valid_user_ptr(p2):
            return None
        return p2

    def _is_continuous_applied(self) -> bool:
        if not mem.is_attached() or not mem.module_base:
            return False
        cur = mem.read_bytes(mem.module_base + RVA_FORTUNE_REFRESH_USED, len(PATCH_FORTUNE_REFRESH_USED))
        return cur == PATCH_FORTUNE_REFRESH_USED

    def get_state(self) -> Dict[str, Any]:
        state = {
            "available": False,
            "fsm_address": None,
            "cost": 50,
            "continuous_refresh": self._is_continuous_applied(),
            "paid_refreshes_used": None,
        }
        fsm = self._resolve_fsm()
        if not fsm:
            return state
        state["available"] = True
        state["fsm_address"] = f"0x{fsm:X}"
        state["cost"] = mem.read_u32(fsm + OFF_FSM_REFRESH_COST) or 50
        state["paid_refreshes_used"] = mem.read_u8(fsm + OFF_FSM_PAID_REFRESH_COUNT)
        return state

    def set_continuous_refresh(self, enable: bool) -> bool:
        """Install/remove the NOP patch that stops the paid-refresh counter from incrementing."""
        if not mem.is_attached() or not mem.module_base:
            return False
        addr = mem.module_base + RVA_FORTUNE_REFRESH_USED
        if enable:
            ok = mem.apply_patch(
                "FORTUNE_REFRESH_USED", addr, PATCH_FORTUNE_REFRESH_USED, ORIG_FORTUNE_REFRESH_USED
            )
            # Clear the counter now so the button is immediately available.
            fsm = self._resolve_fsm()
            if fsm:
                mem.write_u8(fsm + OFF_FSM_PAID_REFRESH_COUNT, 0)
            return ok
        return mem.restore_patch("FORTUNE_REFRESH_USED", addr, ORIG_FORTUNE_REFRESH_USED)

    def set_force_rare(self, enable: bool) -> bool:
        """Patch the rarity red-black tree weights (Rare=100 when enabled)."""
        fsm = self._resolve_fsm()
        if not fsm:
            return False
        sentinel = mem.read_ptr(fsm + OFF_FSM_RARITY_TREE)
        if not sentinel or not mem.is_valid_user_ptr(sentinel):
            return False
        root = mem.read_ptr(sentinel + 8)

        def walk(node):
            if not node or node == sentinel or not mem.is_valid_user_ptr(node):
                return []
            if mem.read_u8(node + 0x19):  # nil sentinel
                return []
            res = []
            res.extend(walk(mem.read_ptr(node)))
            raw = mem.read_bytes(node, 0x30)
            if raw:
                res.append((node, raw))
            res.extend(walk(mem.read_ptr(node + 0x10)))
            return res

        ok = True
        for n_addr, raw in walk(root):
            r_id = struct.unpack_from("<I", raw, 0x1C)[0]
            if enable:
                target_w = 100 if r_id == 2 else 0            # Rare only
            else:
                target_w = 50 if r_id == 0 else 35 if r_id == 1 else 15
            ok &= mem.write_u32(n_addr + 0x20, target_w)
        mem.write_u32(fsm + OFF_FSM_TOTAL_WEIGHT, 100)
        return ok

    def refresh_now(self) -> bool:
        """One-shot immediate re-roll via the 'new day' trick (no Royal Club)."""
        fsm = self._resolve_fsm()
        if not fsm:
            return False
        ok = True
        ok &= mem.write_u8(fsm + OFF_FSM_PAID_REFRESH_COUNT, 0)
        ok &= mem.write_u64(fsm + OFF_FSM_DAY_NUMBER, 0)
        mem.write_bytes(mem.module_base + RVA_UI_INVALIDATE, struct.pack("<i", -1))
        return ok

    def apply(self, payload: Dict[str, Any] = None) -> Tuple[bool, str]:
        if payload is None:
            payload = {}
        if not mem.is_attached():
            return False, "Not attached to game process."

        actions = []

        if payload.get("continuous_refresh") is not None:
            want = bool(payload["continuous_refresh"])
            if self.set_continuous_refresh(want):
                actions.append(f"Continuous 50-gem refresh -> {'ON' if want else 'OFF'}")

        if payload.get("force_rare") is not None:
            if self.set_force_rare(bool(payload["force_rare"])):
                actions.append(f"Rare odds -> {'ON' if payload['force_rare'] else 'OFF'}")

        if payload.get("refresh_now"):
            if self.refresh_now():
                actions.append("Immediate re-roll triggered")

        if actions:
            msg = "; ".join(actions)
            mem.log("SUCCESS", f"[Fortune] {msg}")
            return True, msg
        return False, "No fortune shop parameters provided."


fortune_shop_mechanic = FortuneShopMechanic()
