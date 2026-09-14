"""
Player Level & XP Progression Mechanic for MLPMP Full Suite.
Manages live reading and writing of PlayerLevelManager fields and level reward tables.
"""

import struct
from typing import Dict, Any, Optional, Tuple, List
from core.memory import mem
from core.offsets import (
    RVA_LEVEL_MANAGER,
    OFF_LEVEL_CURRENT_XP,
    OFF_LEVEL_REQUIRED_XP,
    OFF_LEVEL_PLAYER_LEVEL,
    OFF_LEVEL_MAX_LEVEL,
    OFF_LEVEL_IS_MAX_FLAG,
    OFF_LEVEL_XP_TABLE_PTR,
    OFF_LEVEL_XP_TABLE_COUNT,
)
from core.crypto import decode_container_20, encode_container_20
from mechanics.base import BaseMechanic


class LevelMechanic(BaseMechanic):
    name = "LevelMechanic"
    description = "Live Player Level & XP Progression Editor"

    def __init__(self):
        super().__init__()
        self._cached_table: Optional[List[Dict[str, Any]]] = None
        self._load_table_fallback()

    def _load_table_fallback(self):
        import os, json
        table_path = os.path.join(os.path.dirname(__file__), "..", "data", "levels_table.json")
        try:
            if os.path.exists(table_path):
                with open(table_path, "r", encoding="utf-8") as f:
                    self._cached_table = json.load(f)
        except Exception:
            pass

    def _get_mgr_addr(self) -> Optional[int]:
        if not mem.is_attached() or not mem.module_base:
            return None
        ptr = mem.read_ptr(mem.module_base + RVA_LEVEL_MANAGER)
        return ptr if mem.is_valid_user_ptr(ptr) else None

    def get_level_table(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Parses the level progression table from game memory or cached database."""
        if self._cached_table and not force_refresh:
            return self._cached_table

        mgr = self._get_mgr_addr()
        if not mgr:
            if not self._cached_table:
                self._load_table_fallback()
            return self._cached_table or []

        raw_header = mem.read_bytes(mgr, 0x80)
        if not raw_header:
            return self._cached_table or []

        tbl_ptr = struct.unpack_from("<Q", raw_header, OFF_LEVEL_XP_TABLE_PTR)[0]
        tbl_cnt = struct.unpack_from("<I", raw_header, OFF_LEVEL_XP_TABLE_COUNT)[0]

        if not mem.is_valid_user_ptr(tbl_ptr) or tbl_cnt == 0:
            return self._cached_table or []

        raw_tbl = mem.read_bytes(tbl_ptr, tbl_cnt * 20)
        if not raw_tbl:
            return self._cached_table or []

        records = []
        total_levels = tbl_cnt // 5
        for i in range(total_levels):
            off = i * 5 * 20
            f0 = decode_container_20(raw_tbl, off)
            f1 = decode_container_20(raw_tbl, off + 20)
            f2 = decode_container_20(raw_tbl, off + 40)
            f3 = decode_container_20(raw_tbl, off + 60)
            records.append({
                "level": f0["value"] if f0 else (i + 1),
                "req_xp": f1["value"] if f1 else 0,
                "reward_bits": f2["value"] if f2 else 0,
                "reward_gems": f3["value"] if f3 else 0,
            })

        self._cached_table = records
        return records

    def get_base_xp_for_level(self, target_level: int) -> int:
        """Returns exact starting XP for a player at target_level."""
        if target_level <= 1:
            return 0
        if target_level >= 200:
            return 60107610
        table = self.get_level_table()
        if table and len(table) >= target_level:
            return table[target_level - 2]["req_xp"]
        return max(0, (target_level - 1) * 300000)

    def get_next_req_xp_for_level(self, target_level: int) -> int:
        """Returns total cumulative XP required to advance to next level."""
        if target_level >= 200:
            return 60107610
        table = self.get_level_table()
        if table and len(table) >= target_level:
            return table[target_level - 1]["req_xp"]
        return max(5, target_level * 300000)

    def get_level_for_xp(self, xp: int) -> Tuple[int, int]:
        """Calculates matching level and next threshold for a given XP amount."""
        if xp >= 60107610:
            return 200, 60107610
        if xp <= 0:
            return 1, 5

        table = self.get_level_table()
        if table and len(table) >= 200:
            for lvl in range(1, 200):
                base_xp = self.get_base_xp_for_level(lvl)
                next_req = self.get_next_req_xp_for_level(lvl)
                if base_xp <= xp < next_req:
                    return lvl, next_req
        return 200, 60107610

    def get_xp_threshold(self, target_level: int) -> int:
        return self.get_next_req_xp_for_level(target_level)

    def get_state(self) -> Dict[str, Any]:
        state = {
            "available": False,
            "level": 0,
            "xp": 0,
            "required_xp": 0,
            "max_level": 200,
            "is_max_level": False,
            "xp_percentage": 0.0,
            "level_valid": False,
            "xp_valid": False,
        }

        mgr = self._get_mgr_addr()
        if not mgr:
            return state

        raw = mem.read_bytes(mgr, 0x80)
        if not raw:
            return state

        lvl_info = decode_container_20(raw, OFF_LEVEL_PLAYER_LEVEL)
        xp_info = decode_container_20(raw, OFF_LEVEL_CURRENT_XP)
        req_info = decode_container_20(raw, OFF_LEVEL_REQUIRED_XP)
        max_info = decode_container_20(raw, OFF_LEVEL_MAX_LEVEL)
        is_max = bool(raw[OFF_LEVEL_IS_MAX_FLAG])

        curr_lvl = lvl_info["value"] if lvl_info else 0
        curr_xp = xp_info["value"] if xp_info else 0
        req_xp = req_info["value"] if req_info else 0
        max_lvl = max_info["value"] if max_info else 200

        state.update({
            "available": True,
            "level": curr_lvl,
            "xp": curr_xp,
            "required_xp": req_xp,
            "max_level": max_lvl,
            "is_max_level": is_max,
            "level_valid": lvl_info["valid"] if lvl_info else False,
            "xp_valid": xp_info["valid"] if xp_info else False,
        })

        if is_max or curr_lvl >= max_lvl:
            state["xp_percentage"] = 100.0
        else:
            prev_th = self.get_base_xp_for_level(curr_lvl)
            next_th = self.get_next_req_xp_for_level(curr_lvl)
            span = next_th - prev_th
            if span > 0:
                prog = max(0, curr_xp - prev_th)
                state["xp_percentage"] = round(min(100.0, (prog / span) * 100.0), 2)

        return state

    def apply(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        mgr = self._get_mgr_addr()
        if not mgr:
            return False, "PlayerLevelManager not found in memory."

        raw = mem.read_bytes(mgr, 0x80)
        if not raw:
            return False, "Failed to read PlayerLevelManager."

        action = payload.get("action")
        target_level = payload.get("level")
        custom_xp = payload.get("xp")

        max_info = decode_container_20(raw, OFF_LEVEL_MAX_LEVEL)
        max_lvl = max_info["value"] if max_info else 200

        lvl_curr = decode_container_20(raw, OFF_LEVEL_PLAYER_LEVEL)
        xp_curr = decode_container_20(raw, OFF_LEVEL_CURRENT_XP)
        req_curr = decode_container_20(raw, OFF_LEVEL_REQUIRED_XP)

        ok = True
        modified_fields = []

        # Case 1: Apply Level (Decoupled: sets level and synchronizes exact matching XP)
        if action == "set_level" or (target_level is not None and custom_xp is None):
            new_lvl = max(1, min(int(target_level), 200))
            base_xp = self.get_base_xp_for_level(new_lvl)
            next_req = self.get_next_req_xp_for_level(new_lvl)

            enc_lvl = encode_container_20(new_lvl, lvl_curr["k1"] if lvl_curr else None, lvl_curr["k2"] if lvl_curr else None)
            enc_xp = encode_container_20(base_xp, xp_curr["k1"] if xp_curr else None, xp_curr["k2"] if xp_curr else None)
            enc_req = encode_container_20(next_req, req_curr["k1"] if req_curr else None, req_curr["k2"] if req_curr else None)

            ok &= mem.write_bytes(mgr + OFF_LEVEL_PLAYER_LEVEL, enc_lvl)
            ok &= mem.write_bytes(mgr + OFF_LEVEL_CURRENT_XP, enc_xp)
            ok &= mem.write_bytes(mgr + OFF_LEVEL_REQUIRED_XP, enc_req)

            is_max = 1 if new_lvl >= max_lvl else 0
            mem.write_u8(mgr + OFF_LEVEL_IS_MAX_FLAG, is_max)

            modified_fields.append(f"Level -> {new_lvl}")
            modified_fields.append(f"XP synchronized -> {base_xp:,} (Req: {next_req:,})")

        # Case 2: Apply XP (Decoupled: sets XP and synchronizes matching level)
        elif action == "set_xp" or (custom_xp is not None and target_level is None):
            new_xp = max(0, int(custom_xp))
            matched_lvl, next_req = self.get_level_for_xp(new_xp)

            enc_xp = encode_container_20(new_xp, xp_curr["k1"] if xp_curr else None, xp_curr["k2"] if xp_curr else None)
            enc_lvl = encode_container_20(matched_lvl, lvl_curr["k1"] if lvl_curr else None, lvl_curr["k2"] if lvl_curr else None)
            enc_req = encode_container_20(next_req, req_curr["k1"] if req_curr else None, req_curr["k2"] if req_curr else None)

            ok &= mem.write_bytes(mgr + OFF_LEVEL_CURRENT_XP, enc_xp)
            ok &= mem.write_bytes(mgr + OFF_LEVEL_PLAYER_LEVEL, enc_lvl)
            ok &= mem.write_bytes(mgr + OFF_LEVEL_REQUIRED_XP, enc_req)

            is_max = 1 if matched_lvl >= max_lvl else 0
            mem.write_u8(mgr + OFF_LEVEL_IS_MAX_FLAG, is_max)

            modified_fields.append(f"XP -> {new_xp:,}")
            modified_fields.append(f"Level synchronized -> {matched_lvl} (Req: {next_req:,})")

        # Case 3: Both level and custom XP provided simultaneously
        elif target_level is not None and custom_xp is not None:
            new_lvl = max(1, min(int(target_level), 200))
            new_xp = max(0, int(custom_xp))
            next_req = self.get_next_req_xp_for_level(new_lvl)

            enc_lvl = encode_container_20(new_lvl, lvl_curr["k1"] if lvl_curr else None, lvl_curr["k2"] if lvl_curr else None)
            enc_xp = encode_container_20(new_xp, xp_curr["k1"] if xp_curr else None, xp_curr["k2"] if xp_curr else None)
            enc_req = encode_container_20(next_req, req_curr["k1"] if req_curr else None, req_curr["k2"] if req_curr else None)

            ok &= mem.write_bytes(mgr + OFF_LEVEL_PLAYER_LEVEL, enc_lvl)
            ok &= mem.write_bytes(mgr + OFF_LEVEL_CURRENT_XP, enc_xp)
            ok &= mem.write_bytes(mgr + OFF_LEVEL_REQUIRED_XP, enc_req)

            is_max = 1 if new_lvl >= max_lvl else 0
            mem.write_u8(mgr + OFF_LEVEL_IS_MAX_FLAG, is_max)

            modified_fields.append(f"Level -> {new_lvl}")
            modified_fields.append(f"XP -> {new_xp:,}")

        if ok:
            msg = f"Updated: {', '.join(modified_fields)}"
            mem.log("SUCCESS", f"[Level] {msg}")
            return True, msg
        return False, "Failed writing level/XP containers to memory."


level_mechanic = LevelMechanic()
