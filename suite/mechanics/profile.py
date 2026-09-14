"""
Profile Customizations Engine for MLPMP Full Suite.
Unlocks all 743 profile customization items (507 Avatars, 95 Avatar Frames,
50 Backgrounds, 48 Background Frames, 43 Cutie Marks) via live ownership gate hooks.
"""

from typing import Dict, Any, Tuple
from core.memory import mem
from core.offsets import PROFILE_HOOKS
from mechanics.base import BaseMechanic


class ProfileMechanic(BaseMechanic):
    name = "ProfileMechanic"
    description = "Profile Customizations Unlocker (743 Items)"

    def get_state(self) -> Dict[str, Any]:
        state = {
            "available": False,
            "unlocked": False,
            "hooks_active": 0,
            "hooks_total": len(PROFILE_HOOKS),
            "hooks": {},
            "total_items": 743,
            "categories": {
                "avatars": 507,
                "avatar_frames": 95,
                "backgrounds": 50,
                "background_frames": 48,
                "cutie_marks": 43,
            },
        }

        if not mem.is_attached() or not mem.module_base:
            return state

        state["available"] = True
        active_count = 0

        for key, info in PROFILE_HOOKS.items():
            addr = mem.module_base + info["rva"]
            patch_len = len(info["patch"])
            cur_bytes = mem.read_bytes(addr, patch_len)
            is_patched = (cur_bytes == info["patch"])
            if is_patched:
                active_count += 1

            state["hooks"][key] = {
                "name": info["name"],
                "active": is_patched,
            }

        state["hooks_active"] = active_count
        state["unlocked"] = (active_count == len(PROFILE_HOOKS))
        return state

    def apply(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        if not mem.is_attached() or not mem.module_base:
            return False, "Not attached to game process."

        unlock = payload.get("unlock", True)
        ok = True

        for key, info in PROFILE_HOOKS.items():
            addr = mem.module_base + info["rva"]
            if unlock:
                res = mem.apply_patch(key, addr, info["patch"], info["orig"])
            else:
                res = mem.restore_patch(key, addr, info["orig"])
            ok &= res

        action_str = "Unlocked" if unlock else "Restored to vanilla"
        if ok:
            msg = f"{action_str} all 743 profile customization items."
            mem.log("SUCCESS", f"[Profile] {msg}")
            return True, msg
        return False, f"Failed while applying profile customization hooks."


profile_mechanic = ProfileMechanic()
