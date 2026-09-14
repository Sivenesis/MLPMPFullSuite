"""
Live Currency & Element Shards Mechanic for MLPMP Full Suite.
Manages reading and writing of:
- Primary Currencies: Bits, Gems, Hearts
- Social Currency: Friendship Hearts (Token_Social_Chest)
- Element Shards: Loyalty, Kindness, Honesty, Generosity, Laughter, Magic
"""

import struct
from typing import Dict, Any, Optional, Tuple
from core.memory import mem
from core.offsets import (
    OFF_CURRENCY_BITS,
    OFF_CURRENCY_GEMS,
    OFF_CURRENCY_HEARTS,
    SHARD_OFFSETS,
    TOKEN_SOCIAL_CHEST,
)
from core.crypto import decode_container_20, encode_container_20
from mechanics.base import BaseMechanic


class CurrencyMechanic(BaseMechanic):
    name = "CurrencyMechanic"
    description = "Bits, Gems, Hearts, Friendship Hearts & Element Shards Manager"

    def get_state(self) -> Dict[str, Any]:
        state = {
            "available": False,
            "currencies": {
                "bits": 0,
                "gems": 0,
                "hearts": 0,
                "friendship_hearts": 0,
            },
            "shards": {
                "loyalty": 0,
                "kindness": 0,
                "honesty": 0,
                "generosity": 0,
                "laughter": 0,
                "magic": 0,
            },
            "valid": {
                "bits": False,
                "gems": False,
                "hearts": False,
                "friendship_hearts": False,
                "shards": True,
            },
        }

        pm_addr = self.get_player_manager_addr()
        if not pm_addr:
            return state

        # Read main currencies
        raw_bits = mem.read_bytes(pm_addr + OFF_CURRENCY_BITS, 20)
        raw_gems = mem.read_bytes(pm_addr + OFF_CURRENCY_GEMS, 20)
        raw_hearts = mem.read_bytes(pm_addr + OFF_CURRENCY_HEARTS, 20)

        dec_bits = decode_container_20(raw_bits) if raw_bits else None
        dec_gems = decode_container_20(raw_gems) if raw_gems else None
        dec_hearts = decode_container_20(raw_hearts) if raw_hearts else None

        # Read Friendship Hearts from token list
        fh_val = self.read_token_value(TOKEN_SOCIAL_CHEST)

        state["available"] = True
        state["currencies"]["bits"] = dec_bits["value"] if dec_bits else 0
        state["currencies"]["gems"] = dec_gems["value"] if dec_gems else 0
        state["currencies"]["hearts"] = dec_hearts["value"] if dec_hearts else 0
        state["currencies"]["friendship_hearts"] = fh_val if fh_val is not None else 0

        state["valid"]["bits"] = dec_bits["valid"] if dec_bits else False
        state["valid"]["gems"] = dec_gems["valid"] if dec_gems else False
        state["valid"]["hearts"] = dec_hearts["valid"] if dec_hearts else False
        state["valid"]["friendship_hearts"] = fh_val is not None

        # Read Element Shards
        for shard_name, shard_off in SHARD_OFFSETS.items():
            raw_shard = mem.read_bytes(pm_addr + shard_off, 20)
            if raw_shard:
                dec_shard = decode_container_20(raw_shard)
                state["shards"][shard_name] = dec_shard["value"] if dec_shard else 0
                if dec_shard and not dec_shard["valid"]:
                    state["valid"]["shards"] = False
            else:
                state["shards"][shard_name] = 0
                state["valid"]["shards"] = False

        return state

    def apply(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        pm_addr = self.get_player_manager_addr()
        if not pm_addr:
            return False, "PlayerManager singleton not found in memory."

        ok = True
        updated = []

        # 1. Main currencies
        main_offsets = {
            "bits": OFF_CURRENCY_BITS,
            "gems": OFF_CURRENCY_GEMS,
            "hearts": OFF_CURRENCY_HEARTS,
        }

        for cur_id, off in main_offsets.items():
            if cur_id in payload and payload[cur_id] is not None:
                val = max(0, min(int(payload[cur_id]), 2147483647))
                raw = mem.read_bytes(pm_addr + off, 20)
                k1, k2 = None, None
                if raw and len(raw) == 20:
                    dec = decode_container_20(raw)
                    if dec:
                        k1, k2 = dec["k1"], dec["k2"]
                encoded = encode_container_20(val, k1, k2)
                res = mem.write_bytes(pm_addr + off, encoded)
                ok &= res
                if res:
                    updated.append(f"{cur_id.capitalize()} -> {val:,}")

        # 2. Friendship Hearts
        if "friendship_hearts" in payload and payload["friendship_hearts"] is not None:
            val = max(0, min(int(payload["friendship_hearts"]), 9999999))
            res = self.write_token_value(TOKEN_SOCIAL_CHEST, val)
            ok &= res
            if res:
                updated.append(f"Friendship Hearts -> {val:,}")

        # 3. Element Shards
        shards_data = payload.get("shards", {})
        if not isinstance(shards_data, dict):
            shards_data = {}

        # Also check top-level shard keys
        for shard_name, off in SHARD_OFFSETS.items():
            target_val = shards_data.get(shard_name)
            if target_val is None and shard_name in payload:
                target_val = payload[shard_name]

            if target_val is not None:
                val = max(0, min(int(target_val), 999999))
                raw = mem.read_bytes(pm_addr + off, 20)
                k1, k2 = None, None
                if raw and len(raw) == 20:
                    dec = decode_container_20(raw)
                    if dec:
                        k1, k2 = dec["k1"], dec["k2"]
                encoded = encode_container_20(val, k1, k2)
                res = mem.write_bytes(pm_addr + off, encoded)
                ok &= res
                if res:
                    updated.append(f"{shard_name.capitalize()} -> {val:,}")

        if ok and updated:
            msg = f"Updated: {', '.join(updated)}"
            mem.log("SUCCESS", f"[Currency] {msg}")
            return True, msg
        elif not updated:
            return False, "No valid currency fields provided."
        return False, "Failed writing currency values to memory."


currency_mechanic = CurrencyMechanic()
