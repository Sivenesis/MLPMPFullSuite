"""
Pony Editor: Costumes, Sets & Crafting Materials Mechanic for MLPMP Full Suite.
Incorporates the verified logic from pony_costume_unlocker_materials:
- In-place piece ownership hook (PonyPartsManager::IsPartOwned 0x65CAA0)
- In-place costume set completion hook (CostumeSet::IsComplete 0x956C90)
- FashionPage boutique visibility checks (0x2F9860)
- Store rotation visibility hooks
- Crafting materials (pins, buttons, twine, ribbons, bows) in PlayerManager & token synchronization.
"""

from typing import Dict, Any, Optional, Tuple, List
from core.memory import mem
from core.offsets import (
    RVA_PART_OWNED,
    ORIG_PART_OWNED,
    PATCH_PART_OWNED,
    RVA_SET_COMPLETE,
    ORIG_SET_COMPLETE,
    PATCH_SET_COMPLETE,
    COSTUME_VIS_RVAS,
    ORIG_COSTUME_VIS,
    PATCH_COSTUME_VIS,
    STORE_PATCHES,
    MATERIAL_OFFSETS,
    MATERIAL_TOKENS,
)
from core.crypto import decode_container_20, encode_container_20
from mechanics.base import BaseMechanic


class CostumesMechanic(BaseMechanic):
    name = "CostumesMechanic"
    description = "Pony Editor: Costumes/Sets Unlocker & Crafting Materials Manager"

    ROT_KEYS = ["HOOK_ROT_SETTER", "HOOK_ROT_BUILDER", "HOOK_ROT_RENDER", "HOOK_BUYABILITY_ALL"]

    def get_unlock_state(self) -> Dict[str, Any]:
        """Inspects whether costume hooks and rotation patches are applied."""
        if not mem.is_attached() or not mem.module_base:
            return {
                "all_unlocked": False,
                "parts_owned_hook": False,
                "set_complete_hook": False,
                "vis_checks_hook": False,
                "rotation_hooks": False,
            }

        addr_parts = mem.module_base + RVA_PART_OWNED
        parts_hook = (mem.read_bytes(addr_parts, len(PATCH_PART_OWNED)) == PATCH_PART_OWNED)

        addr_set = mem.module_base + RVA_SET_COMPLETE
        set_hook = (mem.read_bytes(addr_set, len(PATCH_SET_COMPLETE)) == PATCH_SET_COMPLETE)

        vis_hook = True
        for rva in COSTUME_VIS_RVAS:
            addr = mem.module_base + rva
            cur = mem.read_bytes(addr, len(PATCH_COSTUME_VIS))
            if cur != PATCH_COSTUME_VIS:
                vis_hook = False
                break

        rot_hook = True
        for key in self.ROT_KEYS:
            info = STORE_PATCHES[key]
            addr = mem.module_base + info["rva"]
            cur = mem.read_bytes(addr, len(info["patch"]))
            if cur != info["patch"]:
                rot_hook = False
                break

        all_unlocked = (parts_hook and set_hook and vis_hook and rot_hook)
        return {
            "all_unlocked": all_unlocked,
            "parts_owned_hook": parts_hook,
            "set_complete_hook": set_hook,
            "vis_checks_hook": vis_hook,
            "rotation_hooks": rot_hook,
        }

    def get_materials(self) -> Dict[str, int]:
        pm_addr = self.get_player_manager_addr()
        if not pm_addr:
            return {k: 0 for k in MATERIAL_OFFSETS}

        res = {}
        for name, off in MATERIAL_OFFSETS.items():
            raw = mem.read_bytes(pm_addr + off, 20)
            if raw and len(raw) == 20:
                dec = decode_container_20(raw)
                res[name] = dec["value"] if dec else 0
            else:
                res[name] = 0
        return res

    def get_state(self) -> Dict[str, Any]:
        return {
            "available": mem.is_attached(),
            "unlock_state": self.get_unlock_state(),
            "materials": self.get_materials(),
        }

    def set_unlock_costumes(self, enable: bool) -> bool:
        if not mem.is_attached() or not mem.module_base:
            return False

        ok = True

        # 1. Piece Ownership Hook (0x65CAA0)
        addr_parts = mem.module_base + RVA_PART_OWNED
        if enable:
            ok &= mem.apply_patch("HOOK_PART_OWNED", addr_parts, PATCH_PART_OWNED, ORIG_PART_OWNED)
        else:
            ok &= mem.restore_patch("HOOK_PART_OWNED", addr_parts, ORIG_PART_OWNED)

        # 2. Set Completion Hook (0x956C90)
        addr_set = mem.module_base + RVA_SET_COMPLETE
        if enable:
            ok &= mem.apply_patch("HOOK_SET_COMPLETE", addr_set, PATCH_SET_COMPLETE, ORIG_SET_COMPLETE)
        else:
            ok &= mem.restore_patch("HOOK_SET_COMPLETE", addr_set, ORIG_SET_COMPLETE)

        # 3. Boutique Visibility Checks (0x2F9860)
        for i, rva in enumerate(COSTUME_VIS_RVAS):
            addr = mem.module_base + rva
            patch_name = f"COSTUME_VIS_{i}"
            if enable:
                ok &= mem.apply_patch(patch_name, addr, PATCH_COSTUME_VIS, ORIG_COSTUME_VIS)
            else:
                ok &= mem.restore_patch(patch_name, addr, ORIG_COSTUME_VIS)

        # 4. Master Store Rotation Hooks
        for key in self.ROT_KEYS:
            info = STORE_PATCHES[key]
            addr = mem.module_base + info["rva"]
            if enable:
                ok &= mem.apply_patch(key, addr, info["patch"], info["orig"])
            else:
                ok &= mem.restore_patch(key, addr, info["orig"])

        return ok

    def set_materials(self, materials: Dict[str, int]) -> Tuple[bool, List[str]]:
        pm_addr = self.get_player_manager_addr()
        if not pm_addr:
            return False, []

        ok = True
        updated = []

        for name, off in MATERIAL_OFFSETS.items():
            if name in materials and materials[name] is not None:
                val = max(0, min(int(materials[name]), 999999))
                raw = mem.read_bytes(pm_addr + off, 20)
                k1, k2 = None, None
                if raw and len(raw) == 20:
                    dec = decode_container_20(raw)
                    if dec:
                        k1, k2 = dec["k1"], dec["k2"]

                encoded = encode_container_20(val, k1, k2)
                res = mem.write_bytes(pm_addr + off, encoded)
                ok &= res

                # Also synchronize token tree node
                tok_name = MATERIAL_TOKENS.get(name)
                if tok_name:
                    self.write_token_value(tok_name, val)

                if res:
                    updated.append(f"{name.capitalize()} -> {val:,}")

        return ok, updated

    def apply(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        if not mem.is_attached():
            return False, "Not attached to game process."

        actions = []
        overall_ok = True

        # Handle costume unlock toggle
        if "unlock_costumes" in payload:
            target_unlock = bool(payload["unlock_costumes"])
            ok_costumes = self.set_unlock_costumes(target_unlock)
            overall_ok &= ok_costumes
            if ok_costumes:
                state_str = "Unlocked all costumes & sets" if target_unlock else "Restored costume locks"
                actions.append(state_str)
                mem.log("SUCCESS", f"[Costumes] {state_str}.")

        # Handle crafting materials
        mats_payload = payload.get("materials")
        if mats_payload is None:
            # Check if materials were passed at the top level
            mats_payload = {k: payload[k] for k in MATERIAL_OFFSETS if k in payload}

        if mats_payload:
            ok_mats, updated_mats = self.set_materials(mats_payload)
            overall_ok &= ok_mats
            if updated_mats:
                actions.append(f"Materials: {', '.join(updated_mats)}")
                mem.log("SUCCESS", f"[Costumes] Materials updated: {', '.join(updated_mats)}.")

        if overall_ok and actions:
            return True, "; ".join(actions)
        elif not actions:
            return False, "No valid costume or material fields provided."
        return False, "Failed applying pony editor modifications."


costumes_mechanic = CostumesMechanic()
