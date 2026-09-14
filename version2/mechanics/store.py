"""
Store Editor, Rotation Hooks & Character Catalog Mechanic for MLPMP Full Suite.
Ported from MLPStoreSuite2 architecture.

Features:
- In-memory character catalog of 2,381 ponies across all zones
- Live RAM synchronization (b125 active-on-shelf, b126 rotation, SortPrice >= 1.0f)
- Purchase pipeline security: runtime currency container fix (Bits/Gems) and non-zero price encryption
- 8 Master in-place code hooks for rotation bypass, buyability, Scaleform action gate, and debounce
- Pure vanilla town store section isolation at RVA 0x6C9600
- Offline catalog loading with dynamic live RAM enrichment
"""

import json
import os
import struct
import time
from typing import Dict, Any, Optional, Tuple, List, Set

from core.memory import mem
from core.offsets import (
    TARGET_GAME_VERSION,
    SUITE_VERSION,
    RVA_SHOP_CONTROLLER,
    STORE_PATCHES,
    RVA_ZONE_CHECK,
    VANILLA_ZONE_BYTES,
    RVA_SORT_PRICE_STUB,
    VANILLA_SORT_PRICE_BYTES,
    RVA_CAN_PLACE_STUB,
    VANILLA_CAN_PLACE_BYTES,
)
from core.crypto import rol32, ror32
from mechanics.base import BaseMechanic


class StoreMechanic(BaseMechanic):
    name = "StoreMechanic"
    description = "Store Rotation Patcher & 2,381-Character Catalog Manager"

    STRIDE = 0x158

    def __init__(self):
        super().__init__()
        self.catalog_data: Dict[str, Any] = {}
        self.custom_selection: Optional[Set[str]] = None
        self._item_id_cache: Dict[int, str] = {}
        self._load_catalog()

    def _get_catalog_file_path(self) -> str:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        return os.path.join(base_dir, "data", "ponies_catalog.json")

    def _load_catalog(self):
        cat_file = self._get_catalog_file_path()
        try:
            if os.path.exists(cat_file):
                with open(cat_file, "r", encoding="utf-8") as f:
                    self.catalog_data = json.load(f)
                    ponies = self.catalog_data.get("ponies", [])
                    mem.log("CATALOG", f"Loaded {len(ponies)} ponies from local catalog database.")
        except Exception as ex:
            mem.log("ERROR", f"Failed to load catalog database: {ex}")

    def _get_item_id(self, arr_buf: bytes, off: int, index: int) -> str:
        if index in self._item_id_cache:
            return self._item_id_cache[index]

        intern_ptr = struct.unpack_from("<Q", arr_buf, off + 0x18)[0]
        if mem.is_valid_user_ptr(intern_ptr):
            s_ptr = mem.read_ptr(intern_ptr + 8)
            if mem.is_valid_user_ptr(s_ptr):
                clean_id = mem.read_string(s_ptr, 64)
                if clean_id:
                    self._item_id_cache[index] = clean_id
                    return clean_id
        return ""

    def get_shop_catalog(self, refresh_from_ram: bool = False) -> Dict[str, Any]:
        """
        Returns complete 2,381-pony catalog for game version 11.4.1a.
        Enriches with live b125 visibility and active states from RAM if attached.
        Operates 100% offline from data/ponies_catalog.json.
        """
        cat_file = self._get_catalog_file_path()
        if not os.path.exists(cat_file) or refresh_from_ram:
            self.rescan_catalog_from_ram()

        if not self.catalog_data or not self.catalog_data.get("ponies"):
            self._load_catalog()

        # Deep copy structure so live state updates don't corrupt cached JSON
        catalog_copy = {
            "success": True,
            "game_version": TARGET_GAME_VERSION,
            "suite_version": SUITE_VERSION,
            "total_ponies": self.catalog_data.get("total_ponies", len(self.catalog_data.get("ponies", []))),
            "zones_summary": self.catalog_data.get("zones_summary", {}),
            "custom_selection_active": (self.custom_selection is not None),
            "custom_selection_count": len(self.custom_selection) if self.custom_selection is not None else len(self.catalog_data.get("ponies", [])),
            "ponies": [dict(p) for p in self.catalog_data.get("ponies", [])],
        }

        # If connected to live game, enrich with live b125 states from RAM
        if mem.is_attached() and mem.module_base:
            try:
                shop_ptr = mem.read_ptr(mem.module_base + RVA_SHOP_CONTROLLER)
                if shop_ptr and mem.is_valid_user_ptr(shop_ptr):
                    hdr_buf = mem.read_bytes(shop_ptr, 0x500)
                    if hdr_buf:
                        start_ptr = struct.unpack("<Q", hdr_buf[0x438:0x440])[0]
                        end_ptr = struct.unpack("<Q", hdr_buf[0x440:0x448])[0]
                        if mem.is_valid_user_ptr(start_ptr) and mem.is_valid_user_ptr(end_ptr) and end_ptr > start_ptr:
                            total_items = (end_ptr - start_ptr) // self.STRIDE
                            if 0 < total_items <= 20000:
                                arr_buf = mem.read_bytes(start_ptr, total_items * self.STRIDE)
                                if arr_buf:
                                    live_states: Dict[str, int] = {}
                                    for i in range(total_items):
                                        off = i * self.STRIDE
                                        cat = struct.unpack("<I", arr_buf[off + 8:off + 12])[0]
                                        if cat == 0x39:
                                            pony_id = self._get_item_id(arr_buf, off, i)
                                            if pony_id:
                                                b125 = arr_buf[off + 0x125]
                                                live_states[pony_id] = b125

                                    for pony in catalog_copy["ponies"]:
                                        pid_val = pony.get("id")
                                        if pid_val in live_states:
                                            pony["b125"] = live_states[pid_val]
                                            pony["active_in_store"] = bool(live_states[pid_val] == 1)
            except Exception as ex:
                mem.log("WARN", f"Failed reading live shop b125 states: {ex}")

        return catalog_copy

    def apply_pony_selection(self, selected_ids: Optional[List[str]]) -> Dict[str, Any]:
        """
        Applies custom pony selection directly into live game RAM:
        - Sets b125=1, b126=1 for selected ponies; b125=0, b126=0 for unselected ponies.
        - Elevates SortPrice to 1.0f if <= 0.0f.
        - Maintains currency and price normalization so any active pony can be purchased.
        """
        if selected_ids is None:
            self.custom_selection = None
            mem.log("CATALOG", "Selection set to ALL 2,381 ponies.")
        else:
            self.custom_selection = set(selected_ids)
            mem.log("CATALOG", f"Applying custom selection: {len(self.custom_selection)} ponies selected.")

        if not mem.is_attached() or not mem.module_base:
            return {
                "success": False,
                "error": "Game is not attached. Please click Attach first.",
                "selected_count": len(self.custom_selection) if self.custom_selection is not None else 2381,
            }

        shop_ptr = mem.read_ptr(mem.module_base + RVA_SHOP_CONTROLLER)
        if not shop_ptr or not mem.is_valid_user_ptr(shop_ptr):
            return {"success": False, "error": "ShopManager pointer invalid in memory."}

        hdr_buf = mem.read_bytes(shop_ptr, 0x500)
        if not hdr_buf:
            return {"success": False, "error": "Failed to read ShopManager header."}

        start_ptr = struct.unpack("<Q", hdr_buf[0x438:0x440])[0]
        end_ptr = struct.unpack("<Q", hdr_buf[0x440:0x448])[0]

        if not mem.is_valid_user_ptr(start_ptr) or not mem.is_valid_user_ptr(end_ptr) or end_ptr <= start_ptr:
            return {"success": False, "error": "ShopManager item array pointers invalid."}

        total_items = (end_ptr - start_ptr) // self.STRIDE
        if total_items <= 0 or total_items > 20000:
            return {"success": False, "error": f"Invalid item count: {total_items}"}

        arr_buf = mem.read_bytes(start_ptr, total_items * self.STRIDE)
        if not arr_buf:
            return {"success": False, "error": "Failed to read shop array buffer."}

        one_byte = b"\x01"
        zero_byte = b"\x00"
        one_float = struct.pack("<f", 1.0)
        updated = 0
        currencies_fixed = 0
        prices_fixed = 0

        for i in range(total_items):
            off = i * self.STRIDE
            item_addr = start_ptr + off
            cat = struct.unpack("<I", arr_buf[off + 8:off + 12])[0]

            if cat == 0x39:
                pony_id = self._get_item_id(arr_buf, off, i)
                should_be_active = True
                if self.custom_selection is not None:
                    should_be_active = (pony_id in self.custom_selection)

                if should_be_active:
                    # 1. Force b125 = 1 (active in store)
                    if arr_buf[off + 0x125] == 0:
                        if mem.write_bytes(item_addr + 0x125, one_byte):
                            updated += 1

                    # 2. Force b126 = 1 (rotation active)
                    if arr_buf[off + 0x126] == 0:
                        mem.write_bytes(item_addr + 0x126, one_byte)

                    # 3. Elevate SortPrice to 1.0f if <= 0.0f
                    sp = struct.unpack("<f", arr_buf[off + 0x50:off + 0x54])[0]
                    if sp <= 0.0:
                        if mem.write_bytes(item_addr + 0x50, one_float):
                            updated += 1
                else:
                    # Hide from store shelf
                    if arr_buf[off + 0x125] != 0:
                        if mem.write_bytes(item_addr + 0x125, zero_byte):
                            updated += 1
                    if arr_buf[off + 0x126] != 0:
                        mem.write_bytes(item_addr + 0x126, zero_byte)
            else:
                # Non-pony items (shops, decor)
                if arr_buf[off + 0x125] == 0:
                    if mem.write_bytes(item_addr + 0x125, one_byte):
                        updated += 1
                if arr_buf[off + 0x126] == 0:
                    mem.write_bytes(item_addr + 0x126, one_byte)
                sp = struct.unpack("<f", arr_buf[off + 0x50:off + 0x54])[0]
                if sp <= 0.0:
                    if mem.write_bytes(item_addr + 0x50, one_float):
                        updated += 1

            # 4. Normalize and encrypt runtime currency for purchase execution
            c60, c64, c68, c6c = struct.unpack("<4I", arr_buf[off + 0x60:off + 0x70])
            curr = ror32(c68 ^ c60, 5)
            xml_curr = struct.unpack("<I", arr_buf[off + 0x108:off + 0x10C])[0]
            if curr == 16 or curr not in (1, 2, 3, 12):
                target_curr = xml_curr if xml_curr in (1, 2, 3, 12) else 2
                val = rol32(target_curr, 5)
                new_c68 = c60 ^ val
                new_c6c = c64 ^ val
                curr_bytes = struct.pack("<2I", new_c68, new_c6c)
                if mem.write_bytes(item_addr + 0x68, curr_bytes):
                    currencies_fixed += 1

            # 5. Ensure non-zero price for ponies so purchase checks never abort on zero
            if cat == 0x39:
                p90, p94, p98, p9c = struct.unpack("<4I", arr_buf[off + 0x90:off + 0xA0])
                price = ror32(p98 ^ p90, 5)
                if price == 0:
                    target_price = 100 if xml_curr == 1 else 50
                    pval = rol32(target_price, 5)
                    new_p98 = p90 ^ pval
                    new_p9c = p94 ^ pval
                    price_bytes = struct.pack("<2I", new_p98, new_p9c)
                    if mem.write_bytes(item_addr + 0x98, price_bytes):
                        prices_fixed += 1

        selected_cnt = len(self.custom_selection) if self.custom_selection is not None else 2381
        msg = f"Store Selection Applied in RAM: {selected_cnt} ponies active on shelf ({updated} flags synced)."
        mem.log("SUCCESS", f"[Store] {msg}")

        return {
            "success": True,
            "selected_count": selected_cnt,
            "updated_items": updated,
            "currencies_fixed": currencies_fixed,
            "prices_fixed": prices_fixed,
        }

    def rescan_catalog_from_ram(self) -> Dict[str, Any]:
        """
        Scans all 2,381 ponies directly from live game RAM and regenerates local JSON database.
        Strictly offline; requires zero network access.
        """
        if not mem.is_attached() or not mem.module_base:
            return {"success": False, "error": "Game is not attached. Please click Attach first."}

        shop_ptr = mem.read_ptr(mem.module_base + RVA_SHOP_CONTROLLER)
        if not shop_ptr or not mem.is_valid_user_ptr(shop_ptr):
            return {"success": False, "error": "ShopManager pointer invalid in memory."}

        hdr_buf = mem.read_bytes(shop_ptr, 0x500)
        if not hdr_buf:
            return {"success": False, "error": "Failed to read ShopManager header."}

        start_ptr = struct.unpack("<Q", hdr_buf[0x438:0x440])[0]
        end_ptr = struct.unpack("<Q", hdr_buf[0x440:0x448])[0]
        total_items = (end_ptr - start_ptr) // self.STRIDE

        zone_map = {
            0: "Ponyville",
            1: "Canterlot",
            2: "Sweet Apple Acres",
            3: "Everfree Forest",
            4: "Crystal Empire",
            5: "Changeling Kingdom",
            6: "Klugetown",
        }

        ponies = []
        for i in range(total_items):
            off = i * self.STRIDE
            item_addr = start_ptr + off
            data = mem.read_bytes(item_addr, self.STRIDE)
            if not data or len(data) < self.STRIDE:
                continue

            cat_id = struct.unpack("<I", data[8:12])[0]
            if cat_id != 0x39:
                continue

            internal_id = self._get_item_id(data, 0, i)
            if not internal_id:
                continue

            z_start = struct.unpack("<Q", data[0x38:0x40])[0]
            z_end = struct.unpack("<Q", data[0x40:0x48])[0]
            zones = []
            if z_start and z_end and z_end >= z_start:
                z_cnt = (z_end - z_start) // 4
                if 0 < z_cnt < 20:
                    z_raw = mem.read_bytes(z_start, z_cnt * 4)
                    if z_raw:
                        zones = list(struct.unpack(f"<{z_cnt}i", z_raw))

            display_name = internal_id
            if display_name.startswith("Pony_"):
                display_name = display_name[5:].replace("_", " ")

            p90, p94, p98, p9c = struct.unpack("<4I", data[0x90:0xA0])
            price = ror32(p98 ^ p90, 5)
            xml_curr = struct.unpack("<I", data[0x108:0x10C])[0]
            b125 = data[0x125]
            b126 = data[0x126]

            primary_zone = zones[0] if zones else 0
            zone_name = zone_map.get(primary_zone, f"Zone {primary_zone}")

            ponies.append({
                "index": i,
                "id": internal_id,
                "name": display_name,
                "zones": zones,
                "primary_zone": primary_zone,
                "zone_name": zone_name,
                "currency": "Bits" if xml_curr == 1 else "Gems",
                "currency_id": xml_curr,
                "price": price,
                "b125": b125,
                "b126": b126,
                "local_portrait": f"/assets/portraits/{internal_id}.png",
            })

        catalog_data = {
            "game_version": TARGET_GAME_VERSION,
            "suite_version": SUITE_VERSION,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": "Live RAM",
            "total_ponies": len(ponies),
            "zones_summary": {
                "Ponyville": sum(1 for p in ponies if p["primary_zone"] == 0),
                "Canterlot": sum(1 for p in ponies if p["primary_zone"] == 1),
                "Sweet Apple Acres": sum(1 for p in ponies if p["primary_zone"] == 2),
                "Crystal Empire": sum(1 for p in ponies if p["primary_zone"] == 4),
                "Klugetown": sum(1 for p in ponies if p["primary_zone"] == 6),
                "Everfree Forest": sum(1 for p in ponies if p["primary_zone"] == 3),
            },
            "ponies": ponies,
        }

        cat_file = self._get_catalog_file_path()
        os.makedirs(os.path.dirname(cat_file), exist_ok=True)
        with open(cat_file, "w", encoding="utf-8") as f:
            json.dump(catalog_data, f, indent=2)

        self.catalog_data = catalog_data
        mem.log("CATALOG", f"Re-scanned {len(ponies)} ponies directly from live game RAM and saved local database.")
        return {"success": True, "total": len(ponies), "catalog": catalog_data}

    def apply_store_patches(self) -> Tuple[bool, str]:
        """Applies all 8 store hooks, remediates legacy stubs, enforces town isolation, and syncs live items."""
        if not mem.is_attached() or not mem.module_base:
            return False, "Not attached to game process."

        base = mem.module_base

        # 1. Remediate legacy detours or corrupt stubs if present
        sp_bytes = mem.read_bytes(base + RVA_SORT_PRICE_STUB, len(VANILLA_SORT_PRICE_BYTES))
        if sp_bytes and sp_bytes[0] == 0xE9:
            mem.write_bytes(base + RVA_SORT_PRICE_STUB, VANILLA_SORT_PRICE_BYTES)
            mem.log("HOOK", "Remediated legacy detour stub at 0x68CD91 back to pristine vanilla movss.")

        cp_bytes = mem.read_bytes(base + RVA_CAN_PLACE_STUB, len(VANILLA_CAN_PLACE_BYTES))
        if cp_bytes and cp_bytes[:3] == b"\xb0\x01\xc3":
            mem.write_bytes(base + RVA_CAN_PLACE_STUB, VANILLA_CAN_PLACE_BYTES)
            mem.log("HOOK", "Remediated legacy stub at 0x630290 back to pristine vanilla mov.")

        # 2. Enforce pure vanilla IsAllowedInZone at 0x6C9600 (4C 8B 41 40 48)
        cur_zone = mem.read_bytes(base + RVA_ZONE_CHECK, len(VANILLA_ZONE_BYTES))
        if cur_zone != VANILLA_ZONE_BYTES:
            mem.write_bytes(base + RVA_ZONE_CHECK, VANILLA_ZONE_BYTES)
            mem.log("HOOK", "Restored 0x6C9600 to pristine vanilla IsAllowedInZone.")

        # 3. Apply all 8 master hooks with readback verification
        applied = 0
        for key, info in STORE_PATCHES.items():
            addr = base + info["rva"]
            cur = mem.read_bytes(addr, len(info["patch"]))
            if cur == info["patch"]:
                applied += 1
                continue
            if mem.write_bytes(addr, info["patch"]):
                applied += 1
                mem.log("HOOK", f"Installed {info['name']} at 0x{info['rva']:X} (OK).")

        # 4. Synchronize live ShopManager array (SortPrice, runtime currency, non-zero prices)
        # Matches MLPStoreSuite2 patch_memory behavior to prevent shelf iterator crashes on invalid items
        sync_res = self.apply_pony_selection(list(self.custom_selection) if self.custom_selection is not None else None)
        mem.log("SYNC", f"Live shop array synchronized: {sync_res.get('updated', 0)} items updated.")

        all_ok = (applied == len(STORE_PATCHES))
        msg = f"Store patches active: {applied}/{len(STORE_PATCHES)} hooks verified. Town isolation enforced."
        mem.log("SUCCESS" if all_ok else "WARN", f"[Store] {msg}")
        return all_ok, msg

    def revert_store_patches(self) -> Tuple[bool, str]:
        """Restores all 8 store patches to vanilla bytes and reverts forced live shop items."""
        if not mem.is_attached() or not mem.module_base:
            return False, "Not attached to game process."

        base = mem.module_base
        reverted = 0
        for key, info in STORE_PATCHES.items():
            addr = base + info["rva"]
            cur = mem.read_bytes(addr, len(info["orig"]))
            if cur == info["orig"]:
                reverted += 1
                continue
            if mem.write_bytes(addr, info["orig"]):
                reverted += 1
                mem.log("RESTORE", f"Restored vanilla bytes for {info['name']} at 0x{info['rva']:X}.")

        # Restore 0x6C9600 to pure vanilla bytes
        cur_zone = mem.read_bytes(base + RVA_ZONE_CHECK, len(VANILLA_ZONE_BYTES))
        if cur_zone != VANILLA_ZONE_BYTES:
            mem.write_bytes(base + RVA_ZONE_CHECK, VANILLA_ZONE_BYTES)
            mem.log("RESTORE", "Restored 0x6C9600 to pure vanilla IsAllowedInZone.")

        # Revert live shop items
        reverted_items = self._revert_live_shop_items()

        msg = f"Restored vanilla store state: {reverted}/{len(STORE_PATCHES)} hooks restored. {reverted_items} shop items reset."
        mem.log("SUCCESS", f"[Store] {msg}")
        return True, msg

    def _revert_live_shop_items(self) -> int:
        if not mem.is_attached() or not mem.module_base:
            return 0

        shop_ptr = mem.read_ptr(mem.module_base + RVA_SHOP_CONTROLLER)
        if not shop_ptr or not mem.is_valid_user_ptr(shop_ptr):
            return 0

        hdr_buf = mem.read_bytes(shop_ptr, 0x500)
        if not hdr_buf:
            return 0

        start_ptr = struct.unpack("<Q", hdr_buf[0x438:0x440])[0]
        end_ptr = struct.unpack("<Q", hdr_buf[0x440:0x448])[0]
        if not mem.is_valid_user_ptr(start_ptr) or not mem.is_valid_user_ptr(end_ptr) or end_ptr <= start_ptr:
            return 0

        total_items = (end_ptr - start_ptr) // self.STRIDE
        if total_items <= 0 or total_items > 20000:
            return 0

        arr_buf = mem.read_bytes(start_ptr, total_items * self.STRIDE)
        if not arr_buf:
            return 0

        zero_byte = b"\x00"
        reverted = 0

        for i in range(total_items):
            off = i * self.STRIDE
            item_addr = start_ptr + off
            if arr_buf[off + 0x125] != 0:
                if mem.write_bytes(item_addr + 0x125, zero_byte):
                    reverted += 1
            if arr_buf[off + 0x126] != 0:
                mem.write_bytes(item_addr + 0x126, zero_byte)

        return reverted

    def get_patch_status(self) -> Dict[str, Any]:
        if not mem.is_attached() or not mem.module_base:
            return {
                "active_count": 0,
                "total_count": len(STORE_PATCHES),
                "all_applied": False,
                "patches": {},
            }

        active = 0
        status = {}
        for key, info in STORE_PATCHES.items():
            addr = mem.module_base + info["rva"]
            cur = mem.read_bytes(addr, len(info["patch"]))
            is_patched = (cur == info["patch"])
            if is_patched:
                active += 1
            status[key] = {
                "name": info["name"],
                "active": is_patched,
            }

        return {
            "active_count": active,
            "total_count": len(STORE_PATCHES),
            "all_applied": (active == len(STORE_PATCHES)),
            "patches": status,
        }

    def get_state(self) -> Dict[str, Any]:
        total_p = len(self.catalog_data.get("ponies", []))
        sel_c = len(self.custom_selection) if self.custom_selection is not None else total_p
        return {
            "available": mem.is_attached(),
            "total_catalog": total_p,
            "selected_count": sel_c,
            "custom_selection_active": (self.custom_selection is not None),
            "patches": self.get_patch_status(),
        }

    def apply(self, payload: Dict[str, Any]) -> Tuple[bool, str]:
        action = payload.get("action", "apply_patches")
        if action == "apply_patches":
            return self.apply_store_patches()
        elif action == "revert_patches":
            return self.revert_store_patches()
        elif action == "apply_selection":
            selected_ids = payload.get("selected_ids")
            res = self.apply_pony_selection(selected_ids)
            return res.get("success", False), res.get("error") or f"Applied {res.get('selected_count')} ponies to RAM."
        return False, f"Unknown store action '{action}'."


store_mechanic = StoreMechanic()
