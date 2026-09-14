"""
Active Boosters Mechanic for MLPMP Full Suite.
Manages reading and writing of XP and Bits active booster multipliers and durations.
"""

from typing import Dict, Any, Optional, Tuple
from core.memory import mem
from core.offsets import (
    OFF_BOOSTER_XP_TIME,
    OFF_BOOSTER_BITS_TIME,
    OFF_BOOSTER_XP_MULT,
    OFF_BOOSTER_BITS_MULT,
)
from mechanics.base import BaseMechanic


class BoostersMechanic(BaseMechanic):
    name = "BoostersMechanic"
    description = "Active XP & Bits Booster Multipliers & Time Remaining"

    def get_state(self) -> Dict[str, Any]:
        state = {
            "available": False,
            "xp_time": 0.0,
            "bits_time": 0.0,
            "xp_mult": 1.0,
            "bits_mult": 1.0,
        }

        pm_addr = self.get_player_manager_addr()
        if not pm_addr:
            return state

        xp_t = mem.read_double(pm_addr + OFF_BOOSTER_XP_TIME) or 0.0
        bits_t = mem.read_double(pm_addr + OFF_BOOSTER_BITS_TIME) or 0.0
        xp_m = mem.read_float(pm_addr + OFF_BOOSTER_XP_MULT) or 1.0
        bits_m = mem.read_float(pm_addr + OFF_BOOSTER_BITS_MULT) or 1.0

        state.update({
            "available": True,
            "xp_time": round(xp_t, 2),
            "bits_time": round(bits_t, 2),
            "xp_mult": round(xp_m, 2),
            "bits_mult": round(bits_m, 2),
        })
        return state

    def apply(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        pm_addr = self.get_player_manager_addr()
        if not pm_addr:
            return False, "PlayerManager singleton not found in memory."

        ok = True
        updated = []

        if "xp_time" in payload and payload["xp_time"] is not None:
            val_d = max(0.0, float(payload["xp_time"]))
            res = mem.write_double(pm_addr + OFF_BOOSTER_XP_TIME, val_d)
            ok &= res
            if res:
                updated.append(f"XP Time -> {val_d:,.1f}s")

        if "bits_time" in payload and payload["bits_time"] is not None:
            val_d = max(0.0, float(payload["bits_time"]))
            res = mem.write_double(pm_addr + OFF_BOOSTER_BITS_TIME, val_d)
            ok &= res
            if res:
                updated.append(f"Bits Time -> {val_d:,.1f}s")

        if "xp_mult" in payload and payload["xp_mult"] is not None:
            val_f = max(1.0, float(payload["xp_mult"]))
            res = mem.write_float(pm_addr + OFF_BOOSTER_XP_MULT, val_f)
            ok &= res
            if res:
                updated.append(f"XP Mult -> {val_f:.2f}x")

        if "bits_mult" in payload and payload["bits_mult"] is not None:
            val_f = max(1.0, float(payload["bits_mult"]))
            res = mem.write_float(pm_addr + OFF_BOOSTER_BITS_MULT, val_f)
            ok &= res
            if res:
                updated.append(f"Bits Mult -> {val_f:.2f}x")

        if ok and updated:
            msg = f"Updated boosters: {', '.join(updated)}"
            mem.log("SUCCESS", f"[Boosters] {msg}")
            return True, msg
        elif not updated:
            return False, "No booster fields provided."
        return False, "Failed writing booster values to memory."


boosters_mechanic = BoostersMechanic()
