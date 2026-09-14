"""
Ferris Wheel Cooldown Mechanic for MLPMP Full Suite.
Resets the in-game spin timer to make free spins immediately available without waiting.
"""

from typing import Dict, Any, Tuple
from core.memory import mem
from core.offsets import OFF_FERRIS_WHEEL_ELAPSED
from mechanics.base import BaseMechanic


class FerrisWheelMechanic(BaseMechanic):
    name = "FerrisWheelMechanic"
    description = "Ferris Wheel Instant Free Spin & Cooldown Reset"

    def get_state(self) -> Dict[str, Any]:
        pm_addr = self.get_player_manager_addr()
        if not pm_addr:
            return {
                "available": False,
                "elapsed": 0.0,
                "remaining": 0.0,
                "ready": False,
            }

        elapsed = mem.read_float(pm_addr + OFF_FERRIS_WHEEL_ELAPSED) or 0.0
        remaining = max(0.0, 3600.0 - elapsed)
        ready = (elapsed >= 3600.0)

        return {
            "available": True,
            "elapsed": round(elapsed, 1),
            "remaining": round(remaining, 1),
            "ready": ready,
        }

    def apply(self, payload: Dict[str, Any] = None) -> Tuple[bool, str]:
        pm_addr = self.get_player_manager_addr()
        if not pm_addr:
            return False, "PlayerManager singleton not found in memory."

        # Writing 86400.0f (24 hours) ensures elapsed >= 3600.0, enabling the free spin immediately
        ok = mem.write_float(pm_addr + OFF_FERRIS_WHEEL_ELAPSED, 86400.0)
        if ok:
            msg = "Ferris Wheel cooldown reset. Free spin is now ready."
            mem.log("SUCCESS", f"[FerrisWheel] {msg}")
            return True, msg
        return False, "Failed writing Ferris Wheel timer to memory."


ferris_wheel_mechanic = FerrisWheelMechanic()
