"""
Centralized Memory Map, RVAs, Struct Offsets, and Patch Signatures.
MLPMP Full Suite - Target Build: MyLittlePony_x64.exe (v11.5.0)

All memory references are centralized here to allow trivial updates when game patches release.

Re-offset for 11.5.0 (package 11.5.0.0): every RVA below was re-derived against the live
process. Struct offsets, Container20 cipher (ROR32-5), and all orig/patch byte signatures are
UNCHANGED from 11.4.2a - only module RVAs moved. See OFFSETS_1150_WIP.md for the evidence.
"""

from typing import Dict, Tuple, List, Any

# Target Binary Definition
TARGET_EXE_NAME = "MyLittlePony_x64.exe"
TARGET_GAME_VERSION = "11.5.0"
SUITE_VERSION = "2.2.2"

# =============================================================================
# SINGLETON RVAs (Relative Virtual Addresses from Main Module Base)
# =============================================================================
RVA_PLAYER_MANAGER   = 0x1A7E660   # PlayerManager* / ResourceManager*  (11.4.2a: 0x1A86EE0)
RVA_LEVEL_MANAGER    = 0x1A6F3C8   # PlayerLevelManager*                (11.4.2a: 0x1A77CA8)
RVA_PONY_PARTS_MGR   = 0x1A70FD8   # PonyPartsManager*                  (11.4.2a: 0x1A798B8)
RVA_STATE_MANAGER    = 0x1A6CA58   # StateManager* (Minigames, FSM)     (11.4.2a: 0x1A75338)
RVA_FSM_POINTER      = 0x1A7CA98   # FortuneShopManager** (Double ptr)  (11.4.2a: 0x1A85318)
RVA_GAME_STATE       = 0x1AD3630   # GameState*                         (11.4.2a: 0x1AD79F0)
RVA_UI_INVALIDATE    = 0x1A83F20   # UI Cache invalidation flag         (11.4.2a: 0x1A8C7A0)
RVA_SHOP_CONTROLLER  = 0x1A7FEC0   # ShopManager*                       (11.4.2a: 0x1A88740)
RVA_TOWN_CONTROLLER  = 0x1A7F568   # TownManager*                       (11.4.2a: 0x1A87DE8)
RVA_ARENA_MANAGER    = 0x1A89BC0   # ArenaManager* (Event/Siege TLS)

# =============================================================================
# ARENA / SIEGE TIME-LIMITED STORY (TLS) (at [base + RVA_ARENA_MANAGER])
# =============================================================================
OFF_ARENA_ACTIVE_TLS      = 0x240    # Pointer to ActiveTLS / Arena object
OFF_ARENA_CURRENCY        = 0xC4     # 20-byte encrypted container (Event Coins / Magic Coins)
OFF_ARENA_CURRENCY_SHADOW = 0xD4     # 4-byte plaintext live value
OFF_ARENA_BASKET          = 0xD8     # 20-byte encrypted container (CurrencyBasket)
OFF_ARENA_BASKET_SHADOW   = 0xE8     # 4-byte plaintext live value

# =============================================================================
# PLAYER LEVEL MANAGER (at [base + RVA_LEVEL_MANAGER])
# =============================================================================
OFF_LEVEL_CURRENT_XP    = 0x00     # 20-byte encrypted container
OFF_LEVEL_REQUIRED_XP   = 0x14     # 20-byte encrypted container
OFF_LEVEL_PLAYER_LEVEL  = 0x28     # 20-byte encrypted container
OFF_LEVEL_MAX_LEVEL     = 0x3C     # 20-byte encrypted container
OFF_LEVEL_IS_MAX_FLAG   = 0x50     # 1-byte uint8 flag (1 if level >= max)
OFF_LEVEL_XP_TABLE_PTR  = 0x58     # 8-byte uint64 pointer to XP/Reward array
OFF_LEVEL_XP_TABLE_COUNT = 0x60    # 4-byte uint32 count of entries in table

# =============================================================================
# PLAYER MANAGER (at [base + RVA_PLAYER_MANAGER])
# =============================================================================
# Main Currencies (20-byte encrypted containers: ROL32 cipher)
OFF_CURRENCY_BITS     = 0x444
OFF_CURRENCY_GEMS     = 0x458
OFF_CURRENCY_HEARTS   = 0x4BC

# Element Shards (20-byte encrypted containers)
SHARD_OFFSETS: Dict[str, int] = {
    "loyalty":    0x4E4,
    "kindness":   0x4F8,
    "honesty":    0x50C,
    "generosity": 0x520,
    "laughter":   0x534,
    "magic":      0x548,
}

# Crafting Materials in PlayerManager (20-byte containers)
MATERIAL_OFFSETS: Dict[str, int] = {
    "pins":    0x3B4,
    "buttons": 0x3C8,
    "twine":   0x3DC,
    "ribbons": 0x3F0,
    "bows":    0x404,
}

# Active Boosters
OFF_BOOSTER_XP_TIME    = 0x1178    # double (seconds remaining)
OFF_BOOSTER_BITS_TIME  = 0x1180    # double (seconds remaining)
OFF_BOOSTER_XP_MULT    = 0x1188    # float (multiplier e.g. 2.0)
OFF_BOOSTER_BITS_MULT  = 0x118C    # float (multiplier e.g. 2.0)

# Ferris Wheel Spin Cooldown
OFF_FERRIS_WHEEL_ELAPSED = 0x898   # float (counts up to 3600.0s)

# Token Linked List Map inside PlayerManager
OFF_TOKEN_MAP_PRIMARY   = 0x818    # Primary head pointer in v11.4.2a (std::list)
OFF_TOKEN_MAP_SECONDARY = 0x858    # Fallback head pointer

# Token Identifiers for Red-Black Tree lookup
TOKEN_SOCIAL_CHEST  = "Token_Social_Chest"    # Friendship Hearts
TOKEN_GQ_KEYS       = "Token_GQ_bonus"        # Group Quest Keys
TOKEN_PAIR_APPLE    = "Token_Pair_Apple"      # Find a Pair Apples

MATERIAL_TOKENS: Dict[str, str] = {
    "pins":    "Token_Pop_Pin",
    "buttons": "Token_Pop_Button",
    "twine":   "Token_Pop_Twine",
    "ribbons": "Token_Pop_Ribbon",
    "bows":    "Token_Pop_Bow",
}

# =============================================================================
# PROFILE CUSTOMIZATIONS (743 Items: 507 Avatars, 95 Frames, 50 BGs, 48 BG Frames, 43 Cutie Marks)
# =============================================================================
PROFILE_HOOKS: Dict[str, Dict[str, Any]] = {
    "HOOK_AVATARS_1": {
        "name": "Avatar Ownership Gate 1",
        "rva": 0x5AE6E0,                     # 11.4.2a: 0x5B01F0
        "orig": b"\x0f\x95\xc0",             # setne al (3 bytes)
        "patch": b"\xb0\x01\x90",            # mov al, 1; nop (3 bytes)
    },
    "HOOK_AVATARS_2": {
        "name": "Avatar Ownership Gate 2",
        "rva": 0x5AE9BF,                     # 11.4.2a: 0x5B04CF
        "orig": b"\x0f\x95\xc0",
        "patch": b"\xb0\x01\x90",
    },
    "HOOK_AVATAR_FRAMES": {
        "name": "Avatar Frame Ownership Gate",
        "rva": 0x5AE94F,                     # 11.4.2a: 0x5B045F
        "orig": b"\x0f\x95\xc0",
        "patch": b"\xb0\x01\x90",
    },
    "HOOK_BACKGROUNDS": {
        "name": "Background Ownership Gate",
        "rva": 0x5AE82F,                     # 11.4.2a: 0x5B033F
        "orig": b"\x0f\x95\xc0",
        "patch": b"\xb0\x01\x90",
    },
    "HOOK_BG_FRAMES": {
        "name": "Background Frame Ownership Gate",
        "rva": 0x5AE7BF,                     # 11.4.2a: 0x5B02CF
        "orig": b"\x0f\x95\xc0",
        "patch": b"\xb0\x01\x90",
    },
    "HOOK_CUTIE_MARKS": {
        "name": "Cutie Mark Ownership Gate",
        "rva": 0x5AE89F,                     # 11.4.2a: 0x5B03AF
        "orig": b"\x0f\x95\xc0",
        "patch": b"\xb0\x01\x90",
    },
}

# =============================================================================
# PONY EDITOR: COSTUMES & SETS HOOKS
# =============================================================================
# 11.5.0 costume unlock = 9 hooks (PonyPartsManager::IsPartOwned + CostumeSet::IsComplete +
# 7 FashionPage visibility gates), all forced to return true. Addresses verified against the
# working CT table. Note: the correct IsPartOwned is 0x65B360 (the call in the set loop at
# 0x2FEAEB) - NOT 0x668A90, which earlier generic-prologue matching wrongly picked.
RVA_PART_OWNED    = 0x65B360  # bool PonyPartsManager::IsPartOwned(HashedString&)  (11.4.2a: 0x65CBD0)
ORIG_PART_OWNED   = b"\x48\x89\x5c\x24\x08"
PATCH_PART_OWNED  = b"\xb0\x01\xc3\x90\x90"  # mov al, 1; ret; nop; nop

RVA_SET_COMPLETE  = 0x9573B0  # bool CostumeSet::IsComplete()  (11.4.2a: 0x956F60)
ORIG_SET_COMPLETE = b"\x48\x89\x5c\x24\x10"
PATCH_SET_COMPLETE = b"\xb0\x01\xc3\x90\x90" # mov al, 1; ret; nop; nop

# FashionPage Boutique Visibility Checks (7 gates in FashionPage fn 0x2FBAF0).
COSTUME_VIS_RVAS = [0x2FBD05, 0x2FBD62, 0x2FBECE, 0x2FBF3C, 0x2FBFAA, 0x2FC102, 0x2FC173]
ORIG_COSTUME_VIS  = b"\x0f\xb6\x46\x48"
PATCH_COSTUME_VIS = b"\xb0\x01\x90\x90"     # mov al, 1; nop; nop

# =============================================================================
# PETS & COMPANIONS (36 Items: Category 0xA1)
# =============================================================================
CATEGORY_PET       = 0xA1      # Shop & Storage Category ID for Pets
OFF_PLAYER_STORAGE = 0x40      # Storage hash map inside PlayerManager (+0x40)

# Pet Ownership Gate (PlayerManager::IsPetOwned)
RVA_PET_OWNED      = 0x5AE120  # bool PlayerManager::IsPetOwned(HashedString&) (11.5.0)
ORIG_PET_OWNED     = b"\x48\x89\x5c\x24\x08"
PATCH_PET_OWNED    = b"\xb0\x01\xc3\x90\x90"  # mov al, 1; ret; nop; nop

# =============================================================================
# STORE ROTATION & PURCHASE PATCHES
# =============================================================================
STORE_PATCHES: Dict[str, Dict[str, Any]] = {
    "HOOK_ROT_SETTER": {
        "name": "Store Rotation XML Setter",
        "rva": 0x12FFD1C,                    # 11.4.2a: 0x1301CD7
        "orig": b"\x0f\x94\xc0",
        "patch": b"\xb0\x01\x90",
    },
    "HOOK_ROT_BUILDER": {
        "name": "Category Deque Builder",
        "rva": 0x69F163,                     # 11.4.2a: 0x6A00F3
        "orig": b"\x74\x43",
        "patch": b"\x90\x90",
    },
    "HOOK_ROT_RENDER": {
        "name": "Shelf Render Iterator",
        "rva": 0x67B21F,                     # 11.4.2a: 0x67C94F
        "orig": b"\x0f\x84\xfd\x00\x00\x00",
        "patch": b"\x90\x90\x90\x90\x90\x90",
    },
    # DISABLED for 11.5.0 - best-guess RVA, never live-verified. Store rotation + purchase
    # both work with only the 3 rotation hooks (ROT_SETTER/BUILDER/RENDER), so this is not
    # needed; sentinel'd to avoid patching a possibly-wrong function. Verify before enabling.
    "HOOK_BUYABILITY_ALL": {
        "name": "Buyability Enabler",
        "rva": 0x0FFFFFFF,                   # DISABLED (best-guess 0x680D60); not needed for store rotation
        "orig": b"\x48\x89\x5c\x24\x08",
        "patch": b"\xb0\x01\xc3\x90\x90",
    },
    # !! DISABLED for 11.5.0 - caused CTD. The patch ends in a RELATIVE jmp (E9 36 A6 89 00)
    # whose target was computed for the old address 0x366600; at 0x368810 it lands in the wrong
    # function. The patch bytes must be rebuilt for 11.5.0 (recompute the detour target), not copied.
    # RVA relocated fine (0x366600 -> 0x368810) but is sentinel'd so the broken patch cannot apply.
    "HOOK_ACTION_POSSIBLE": {
        "name": "Scaleform Action Gate",
        "rva": 0x0FFFFFFF,                    # DISABLED (real site 0x368810); patch bytes need rebuild
        "orig": b"\x40\x57\x48\x83\xec\x50\x83\x79\x20\x01",
        "patch": b"\x48\x8b\x09\xb2\x01\xe9\x36\xa6\x89\x00",
    },
    "HOOK_GET_CURRENCY": {
        "name": "Currency Type Resolver",
        "rva": 0x6C88D0,                     # 11.4.2a: 0x6C9760
        "orig": b"\x48\x83\xec\x28\x48\x8b\xd1\x8b\x49\x68\x33\x4a\x60\x8b\x42\x6c",
        "patch": b"\x8b\x81\x08\x01\x00\x00\x85\xc0\x75\x05\xb8\x02\x00\x00\x00\xc3",
    },
    "HOOK_BUY_FRAME_CHECK": {
        "name": "Dispatcher Frame Debounce",
        "rva": 0x67C9F9,                     # 11.4.2a: 0x67E129
        "orig": b"\x0f\x8e\xac\x01\x00\x00",
        "patch": b"\x90\x90\x90\x90\x90\x90",
    },
    # DISABLED for 11.5.0 - best-guess RVA (alt 0x67E076), never verified. Not needed for store
    # rotation; sentinel'd for safety. Housing-space override is a separate niche feature.
    "HOOK_BUY_HOUSE_CHECK": {
        "name": "Housing Space Allowance",
        "rva": 0x0FFFFFFF,                   # DISABLED (best-guess 0x67E2E3 / 0x67E076); verify before enabling
        "orig": b"\x0f\x94\xc3",
        "patch": b"\x31\xdb\x90",
    },
}

RVA_ZONE_CHECK = 0x6C88A0                    # 11.4.2a: 0x6C9730  (do NOT patch; keep vanilla)
VANILLA_ZONE_BYTES = b"\x4c\x8b\x41\x40\x48"

# Remediation RVAs for stale legacy patches
RVA_SORT_PRICE_STUB = 0x68B931               # 11.4.2a: 0x68CEC1
VANILLA_SORT_PRICE_BYTES = b"\xf3\x41\x0f\x11\x74\x24\x50"
RVA_CAN_PLACE_STUB = 0x62EE40                # 11.4.2a: 0x6303C0  (co-test: 0x62EB10 is the alt candidate)
VANILLA_CAN_PLACE_BYTES = b"\x48\x89\x5c\x24\x08"

# =============================================================================
# FORTUNE SHOP & ROYAL CLUB
# =============================================================================
RVA_FORTUNE_VIS_CHECK  = 0x81DA7C  # 2 bytes: je (\x74\x04)                        (11.4.2a: 0x81D90C)
RVA_FORTUNE_FREE_CHECK = 0x81DA8B  # 7 bytes: cmp r8d, 2; sete al (\x41\x83\xF8\x02\x0F\x94\xC0)  (11.4.2a: 0x81D91B)

# Continuous paid refresh (11.5.0): the "mark refresh used" fn (0x4F98A0) sets FSM[+0x99]=1
# after each paid refresh, which hides the 50-gem button. NOP'ing that single write keeps the
# counter at 0 so the in-game 50-gem button is ALWAYS available - no Royal Club, no cooldown clear.
RVA_FORTUNE_REFRESH_USED   = 0x4F98A9
ORIG_FORTUNE_REFRESH_USED  = b"\xc6\x81\x99\x00\x00\x00\x01"  # mov byte [rcx+0x99], 1
PATCH_FORTUNE_REFRESH_USED = b"\x90\x90\x90\x90\x90\x90\x90"  # 7x nop
ORIG_FORTUNE_VIS       = b"\x74\x04"
ORIG_FORTUNE_FREE      = b"\x41\x83\xf8\x02\x0f\x94\xc0"

OFF_FSM_AVAILABLE      = 0x08      # uint8
OFF_FSM_RARITY_TREE    = 0x18      # Red-black tree of rarity weights
OFF_FSM_TOTAL_WEIGHT   = 0x28      # uint32 (100)
OFF_FSM_DAY_NUMBER     = 0x78      # uint64
OFF_FSM_REFRESH_COST   = 0x84      # uint32
OFF_FSM_REQUIRED_LVL   = 0x88      # uint32
OFF_FSM_LAST_REFRESH   = 0x90      # uint64 (timestamp)
OFF_FSM_PAID_REFRESH_COUNT = 0x99  # uint8: paid refreshes done today; >=1 hides the 50-gem button.
                                   # Keeping this at 0 keeps the paid refresh continuously available
                                   # WITHOUT touching Royal Club (11.5.0; verified by live FSM diff).
OFF_FSM_FREE_AVAILABLE = 0x9A      # uint8

# Royal Club at [ResourceManager + 0xDA0]
OFF_ROYAL_CLUB_BASE    = 0xDA0
OFF_RC_IS_ACTIVE       = 0x48      # uint8
OFF_RC_EXPIRATION      = 0x70      # uint64 timestamp
OFF_RC_TIER            = 0x80      # uint8 (Tier 2 enables free refreshes)
OFF_RC_TIER_ACTIVE     = 0x81      # uint8

# =============================================================================
# FIND A PAIR MINIGAME (StateManager -> State ID 102 / 0x66)
# =============================================================================
PAIR_STATE_ID          = 102       # 0x66 = StateMinigameFindPair
OFF_PAIR_TIMER_FLOAT   = 0x3A8     # float (active countdown)
OFF_PAIR_TIMER_INT     = 0x3A4     # uint32 (integer display)
OFF_PAIR_MULT_OBJ      = 0x3B8     # Pointer to Multiplier container
OFF_PAIR_SCORE_OBJ     = 0x3D0     # Pointer to Score container
