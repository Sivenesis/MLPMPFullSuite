"""
Centralized Memory Map, RVAs, Struct Offsets, and Patch Signatures.
MLPMP Full Suite - Target Build: MyLittlePony_x64.exe (v11.4.1a)

All memory references are centralized here to allow trivial updates when game patches release.
"""

from typing import Dict, Tuple, List, Any

# Target Binary Definition
TARGET_EXE_NAME = "MyLittlePony_x64.exe"
TARGET_GAME_VERSION = "11.4.1a"
SUITE_VERSION = "2.1.0"

# =============================================================================
# SINGLETON RVAs (Relative Virtual Addresses from Main Module Base)
# =============================================================================
RVA_PLAYER_MANAGER   = 0x1A85EE0   # PlayerManager* / ResourceManager*
RVA_LEVEL_MANAGER    = 0x1A76CA8   # PlayerLevelManager*
RVA_PONY_PARTS_MGR   = 0x1A788B8   # PonyPartsManager*
RVA_STATE_MANAGER    = 0x1A74338   # StateManager* (Minigames, FSM)
RVA_FSM_POINTER      = 0x1A84318   # FortuneShopManager** (Double pointer)
RVA_GAME_STATE       = 0x1AD69F0   # GameState*
RVA_UI_INVALIDATE    = 0x1A8B7A0   # UI Cache invalidation flag
RVA_SHOP_CONTROLLER  = 0x1A87740   # ShopManager*
RVA_TOWN_CONTROLLER  = 0x1A86DE8   # TownManager*

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
OFF_TOKEN_MAP_PRIMARY   = 0x818    # Primary head pointer in v11.4.1a (std::list)
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
        "rva": 0x5B00A0,
        "orig": b"\x0f\x95\xc0",             # setne al (3 bytes)
        "patch": b"\xb0\x01\x90",            # mov al, 1; nop (3 bytes)
    },
    "HOOK_AVATARS_2": {
        "name": "Avatar Ownership Gate 2",
        "rva": 0x5B037F,
        "orig": b"\x0f\x95\xc0",
        "patch": b"\xb0\x01\x90",
    },
    "HOOK_AVATAR_FRAMES": {
        "name": "Avatar Frame Ownership Gate",
        "rva": 0x5B030F,
        "orig": b"\x0f\x95\xc0",
        "patch": b"\xb0\x01\x90",
    },
    "HOOK_BACKGROUNDS": {
        "name": "Background Ownership Gate",
        "rva": 0x5B01EF,
        "orig": b"\x0f\x95\xc0",
        "patch": b"\xb0\x01\x90",
    },
    "HOOK_BG_FRAMES": {
        "name": "Background Frame Ownership Gate",
        "rva": 0x5B017F,
        "orig": b"\x0f\x95\xc0",
        "patch": b"\xb0\x01\x90",
    },
    "HOOK_CUTIE_MARKS": {
        "name": "Cutie Mark Ownership Gate",
        "rva": 0x5B025F,
        "orig": b"\x0f\x95\xc0",
        "patch": b"\xb0\x01\x90",
    },
}

# =============================================================================
# PONY EDITOR: COSTUMES & SETS HOOKS
# =============================================================================
RVA_PART_OWNED    = 0x65CAA0  # bool PonyPartsManager::IsPartOwned(HashedString&)
ORIG_PART_OWNED   = b"\x48\x89\x5c\x24\x08"
PATCH_PART_OWNED  = b"\xb0\x01\xc3\x90\x90"  # mov al, 1; ret; nop; nop

RVA_SET_COMPLETE  = 0x956C90  # bool CostumeSet::IsComplete()
ORIG_SET_COMPLETE = b"\x48\x89\x5c\x24\x10"
PATCH_SET_COMPLETE = b"\xb0\x01\xc3\x90\x90" # mov al, 1; ret; nop; nop

# FashionPage Boutique Visibility Checks (in FashionPage 0x2F9860)
COSTUME_VIS_RVAS = [0x2F99F5, 0x2F9A52, 0x2F9BBE, 0x2F9C2C, 0x2F9C9A, 0x2F9DF2, 0x2F9E63]
ORIG_COSTUME_VIS  = b"\x0f\xb6\x46\x48"
PATCH_COSTUME_VIS = b"\xb0\x01\x90\x90"     # mov al, 1; nop; nop

# =============================================================================
# STORE ROTATION & PURCHASE PATCHES
# =============================================================================
STORE_PATCHES: Dict[str, Dict[str, Any]] = {
    "HOOK_ROT_SETTER": {
        "name": "Store Rotation XML Setter",
        "rva": 0x1301A47,
        "orig": b"\x0f\x94\xc0",
        "patch": b"\xb0\x01\x90",
    },
    "HOOK_ROT_BUILDER": {
        "name": "Category Deque Builder",
        "rva": 0x69FFC3,
        "orig": b"\x74\x43",
        "patch": b"\x90\x90",
    },
    "HOOK_ROT_RENDER": {
        "name": "Shelf Render Iterator",
        "rva": 0x67C81F,
        "orig": b"\x0f\x84\xfd\x00\x00\x00",
        "patch": b"\x90\x90\x90\x90\x90\x90",
    },
    "HOOK_BUYABILITY_ALL": {
        "name": "Buyability Enabler",
        "rva": 0x681610,
        "orig": b"\x48\x89\x5c\x24\x08",
        "patch": b"\xb0\x01\xc3\x90\x90",
    },
    "HOOK_ACTION_POSSIBLE": {
        "name": "Scaleform Action Gate",
        "rva": 0x3665A0,
        "orig": b"\x40\x57\x48\x83\xec\x50\x83\x79\x20\x01",
        "patch": b"\x48\x8b\x09\xb2\x01\xe9\xc6\x99\x89\x00",
    },
    "HOOK_GET_CURRENCY": {
        "name": "Currency Type Resolver",
        "rva": 0x6C9630,
        "orig": b"\x48\x83\xec\x28\x48\x8b\xd1\x8b\x49\x68\x33\x4a\x60\x8b\x42\x6c",
        "patch": b"\x8b\x81\x08\x01\x00\x00\x85\xc0\x75\x05\xb8\x02\x00\x00\x00\xc3",
    },
    "HOOK_BUY_FRAME_CHECK": {
        "name": "Dispatcher Frame Debounce",
        "rva": 0x67DFF9,
        "orig": b"\x0f\x8e\xac\x01\x00\x00",
        "patch": b"\x90\x90\x90\x90\x90\x90",
    },
    "HOOK_BUY_HOUSE_CHECK": {
        "name": "Housing Space Allowance",
        "rva": 0x67F676,
        "orig": b"\x0f\x94\xc3",
        "patch": b"\x31\xdb\x90",
    },
}

RVA_ZONE_CHECK = 0x6C9600
VANILLA_ZONE_BYTES = b"\x4c\x8b\x41\x40\x48"

# Remediation RVAs for stale legacy patches
RVA_SORT_PRICE_STUB = 0x68CD91
VANILLA_SORT_PRICE_BYTES = b"\xf3\x41\x0f\x11\x74\x24\x50"
RVA_CAN_PLACE_STUB = 0x630290
VANILLA_CAN_PLACE_BYTES = b"\x48\x89\x5c\x24\x08"

# =============================================================================
# FORTUNE SHOP & ROYAL CLUB
# =============================================================================
RVA_FORTUNE_VIS_CHECK  = 0x81D7DC  # 2 bytes: je 0x81D7E2 (\x74\x04)
RVA_FORTUNE_FREE_CHECK = 0x81D7EB  # 7 bytes: cmp r8d, 2; sete al (\x41\x83\xF8\x02\x0F\x94\xC0)
ORIG_FORTUNE_VIS       = b"\x74\x04"
ORIG_FORTUNE_FREE      = b"\x41\x83\xf8\x02\x0f\x94\xc0"

OFF_FSM_AVAILABLE      = 0x08      # uint8
OFF_FSM_RARITY_TREE    = 0x18      # Red-black tree of rarity weights
OFF_FSM_TOTAL_WEIGHT   = 0x28      # uint32 (100)
OFF_FSM_DAY_NUMBER     = 0x78      # uint64
OFF_FSM_REFRESH_COST   = 0x84      # uint32
OFF_FSM_REQUIRED_LVL   = 0x88      # uint32
OFF_FSM_LAST_REFRESH   = 0x90      # uint64 (timestamp)
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
