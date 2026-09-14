# Reverse-Engineering & Research Documentation
## Target Build: *My Little Pony: Magic Princess* (Windows x64 / v11.4.1a)
### MLPMP Full Suite Architecture & Technical Reference

---

## 1. Executive Summary & Mission Statement

This document serves as the permanent, exhaustive technical specification and reverse-engineering reference for the Windows x64 PC client of *My Little Pony: Magic Princess* (Gameloft / Hasbro), with primary focus on build **`v11.4.1a`** and forward compatibility with future updates.

Its purpose is to provide researchers, software engineers, modders, and autonomous AI agents with a comprehensive, mathematically rigorous guide to:
1. The internal runtime memory layout of the game engine.
2. Gameloft's proprietary in-memory container encryption schemes (`Container20` and `Token16`).
3. Singleton manager resolution and dynamic pointer paths.
4. Scaleform GFx UI integration and live ownership verification gates.
5. Store rotation, shelf population, and direct purchase bypasses.
6. Real-time minigame state machine traversal and timer manipulation.
7. Step-by-step methodologies for maintaining and updating RVAs across future game revisions.

All techniques documented herein operate strictly via non-invasive virtual memory introspection (`ReadProcessMemory` / `WriteProcessMemory`) without altering saved data, disk assets, or game executables.

---

## 2. Target Binary & Execution Environment

### 2.1 Process Specifications
- **Target Executable**: `MyLittlePony_x64.exe`
- **Architecture**: PE32+ (64-bit AMD64 / x86_64)
- **Engine**: Proprietary Gameloft C++ Cross-Platform Framework
- **UI Subsystem**: Autodesk Scaleform GFx (ActionScript 2 / 3 vector UI rendered into 3D viewport)
- **Host OS**: Windows 10 / 11 64-bit
- **Security & Mitigations**:
  - **ASLR (Address Space Layout Randomization)**: Enabled. Base address is dynamically randomized on every process spawn (e.g., `0x7FF6A2A50000`).
  - **DEP (Data Execution Prevention)**: Enabled. Memory patches targeting code segments require explicit permission modifications (`VirtualProtectEx` to `PAGE_EXECUTE_READWRITE`, followed by restoring `PAGE_EXECUTE_READ`).
  - **Privilege Model**: Standard Win32 user-mode permissions. The process does not employ kernel-mode anti-tamper drivers (e.g. EasyAntiCheat, BattlEye), permitting standard `OpenProcess` handle acquisition with `PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION`.

### 2.2 Dynamic Base & Pointer Arithmetic
Because ASLR is active, static absolute memory addresses cannot be hardcoded. Every memory location is defined as a **Relative Virtual Address (RVA)** from the executable's module base:

$$\text{Effective Address} = \text{ModuleBase} + \text{RVA}$$

In Python, the module base is dynamically resolved via the Toolhelp32 API (`CreateToolhelp32Snapshot` with `TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32`).

---

## 3. Gameloft In-Memory Cryptographic Enclaves

To prevent trivial memory modification via naive integer scanning (e.g., Cheat Engine four-byte scans), Gameloft wraps all critical gameplay variables in proprietary obfuscated container structures.

### 3.1 The 20-Byte Encrypted Container (`Container20`)

The 20-byte container is used for core currencies, element shards, player levels, experience points, and boutique crafting materials.

#### Struct Definition (C++ / Memory Layout):
```cpp
#pragma pack(push, 1)
struct Container20 {
    uint32_t v1;      // +0x00: Obfuscated value 1
    uint32_t v2;      // +0x04: Obfuscated value 2
    uint32_t k1;      // +0x08: Entropy key 1
    uint32_t k2;      // +0x0C: Entropy key 2
    uint32_t shadow;  // +0x10: Plaintext shadow / mirror copy
};
#pragma pack(pop)
static_assert(sizeof(Container20) == 20, "Container20 size mismatch");
```

#### Cipher Algorithm:
The encryption mechanism utilizes 32-bit bitwise circular rotation combined with dual XOR keys. The rotation constant is fixed at **5 bits**:

$$\text{Decrypt}(v, k) = \text{ROR32}(v \oplus k, 5)$$

$$\text{Encrypt}(val, k) = \text{ROL32}(val, 5) \oplus k$$

Where:
- $\text{ROL32}(x, r) = ((x \ll r) \mid (x \gg (32 - r))) \ \& \ \text{0xFFFFFFFF}$
- $\text{ROR32}(x, r) = ((x \gg r) \mid (x \ll (32 - r))) \ \& \ \text{0xFFFFFFFF}$

#### Validation & Integrity Rules:
The engine validates container integrity by decrypting both copies independently and comparing them to the shadow field:

$$\text{Valid} \iff \left(\text{ROR32}(v_1 \oplus k_1, 5) == \text{ROR32}(v_2 \oplus k_2, 5) == shadow\right)$$

If any mismatch occurs, the game engine flags memory corruption and either resets the value to zero or forces a desynchronization crash.

#### Python Implementation:
```python
def rol32(val: int, r: int) -> int:
    return ((val << r) | (val >> (32 - r))) & 0xFFFFFFFF

def ror32(val: int, r: int) -> int:
    return ((val >> r) | ((val << (32 - r)) & 0xFFFFFFFF)) & 0xFFFFFFFF

def decode_container_20(raw: bytes, offset: int = 0) -> Optional[dict]:
    if len(raw) < offset + 20:
        return None
    v1, v2, k1, k2, shadow = struct.unpack_from("<IIIII", raw, offset)
    dec1 = ror32(v1 ^ k1, 5)
    dec2 = ror32(v2 ^ k2, 5)
    is_valid = (dec1 == dec2 == shadow)
    return {
        "value": shadow if is_valid else dec1,
        "k1": k1, "k2": k2, "v1": v1, "v2": v2,
        "valid": is_valid
    }

def encode_container_20(val: int, k1: Optional[int] = None, k2: Optional[int] = None) -> bytes:
    val = int(val) & 0xFFFFFFFF
    if k1 is None: k1 = random.randint(0x1000, 0xFFFF)
    if k2 is None: k2 = random.randint(0x1000, 0xFFFF)
    rot = rol32(val, 5)
    v1 = rot ^ k1
    v2 = rot ^ k2
    shadow = val
    return struct.pack("<IIIII", v1, v2, k1, k2, shadow)
```

> [!TIP]
> **Entropy Preservation**: When writing new values to an existing container, reading the existing `k1` and `k2` and reusing them ensures that memory monitors do not detect anomalous key changes.

---

### 3.2 The 16-Byte Token Container (`Token16`)

Tokens (Group Quest keys, Friendship chest tokens, minigame currency tokens) use a 16-byte structure without a dedicated shadow field:

```cpp
#pragma pack(push, 1)
struct Token16 {
    uint32_t v1;  // +0x00: Obfuscated value 1
    uint32_t v2;  // +0x04: Obfuscated value 2
    uint32_t k1;  // +0x08: Key 1 (0 if plaintext)
    uint32_t k2;  // +0x0C: Key 2 (0 if plaintext)
};
#pragma pack(pop)
```

If $k_1 == 0$ and $k_2 == 0$, the container is treated as raw plaintext with value $= v_1$. Otherwise, it follows the identical ROR32-5 cipher:

$$\text{Value} = \text{ROR32}(v_1 \oplus k_1, 5)$$

---

## 4. Master Singleton RVAs & Memory Map

All gameplay systems are anchored to global singleton manager pointers located in the `.data` and `.bss` sections of `MyLittlePony_x64.exe`.

### Singleton Pointers Table (v11.4.1a)

| Symbol / Manager Name | RVA | Type | Description |
| :--- | :--- | :--- | :--- |
| `RVA_PLAYER_MANAGER` | `0x1A85EE0` | `PlayerManager*` | Root inventory, currencies, crafting, tokens, boosters, Royal Club |
| `RVA_LEVEL_MANAGER` | `0x1A76CA8` | `PlayerLevelManager*` | Progression level, XP, required milestone XP, table pointer |
| `RVA_PONY_PARTS_MGR` | `0x1A788B8` | `PonyPartsManager*` | Costume pieces, boutique outfits, fashion ownership |
| `RVA_STATE_MANAGER` | `0x1A74338` | `StateManager*` | Game state machine linked list (Find a Pair, minigames) |
| `RVA_FSM_POINTER` | `0x1A84318` | `FortuneShopManager**` | Double pointer to Fortune Shop controller |
| `RVA_SHOP_CONTROLLER` | `0x1A87740` | `ShopManager*` | Master character catalog array (2,381 ponies), rotation shelves |
| `RVA_GAME_STATE` | `0x1AD69F0` | `GameState*` | Global game frame counters, engine state flags |
| `RVA_UI_INVALIDATE` | `0x1A8B7A0` | `uint8_t*` | Global UI cache invalidation flag (forces Scaleform repaint) |
| `RVA_TOWN_CONTROLLER` | `0x1A86DE8` | `TownManager*` | Zone metadata, town boundaries, placement restrictions |

---

## 5. Reverse-Engineering Game Mechanics

### 5.1 Player Progression: Level & Experience Points

#### Struct Layout: `PlayerLevelManager` (at `[ModuleBase + 0x1A76CA8]`)
```
+0x00: Container20 CurrentXP      (Current total cumulative XP)
+0x14: Container20 RequiredXP     (Threshold XP needed for next level up)
+0x28: Container20 PlayerLevel    (Current level: 1 to 200)
+0x3C: Container20 MaxLevel       (Engine cap: 200)
+0x50: uint8_t     IsMaxLevelFlag (1 if PlayerLevel >= MaxLevel, else 0)
+0x58: uint64_t    XpTablePtr     (Pointer to native progression threshold array)
+0x60: uint32_t    XpTableCount   (200 entries)
```

#### Milestone Mathematics & Desynchronization Prevention:
In `v11.4.1a`, the game tracks two XP numbers:
1. **Cumulative Experience Points (`CurrentXP`)**: Monotonically increasing counter.
2. **Next Level Milestone Threshold (`RequiredXP`)**: Target number where the level-up sequence triggers.

```
Level 1: Base XP = 0,         Required XP = 5
Level 2: Base XP = 5,         Required XP = 45
Level 3: Base XP = 45,        Required XP = 135
Level 4: Base XP = 135,       Required XP = 270
...
Level 55: Base XP = 89,150,   Required XP = 93,240
...
Level 200: Base XP = 60,107,610, Required XP = 60,107,610 (Maxed)
```

> [!IMPORTANT]
> **Decoupled Synchronization Rule**:
> - When **Level** is set: The Suite looks up the exact base milestone XP for that level ($XP_{base}$) and next threshold ($XP_{req}$), and writes Level, $XP_{base}$, and $XP_{req}$ simultaneously.
> - When **Custom XP** is set: The Suite traverses the threshold intervals, calculates the matching canonical level $L$ where $XP_{base}(L) \le XP_{custom} < XP_{req}(L)$, and writes both Level and XP simultaneously.
> This guarantees that the player is never left in an illegal state where the UI badge reports a different level than the progress bar.

---

### 5.2 Currencies, Shards & Token Linked Lists

#### Primary Currency Containers (in `PlayerManager` at `[ModuleBase + 0x1A85EE0]`):
- **Bits**: Offset `+0x444` (`Container20`)
- **Gems**: Offset `+0x458` (`Container20`)
- **Hearts**: Offset `+0x4BC` (`Container20`)

#### Element Shards:
- **Loyalty**: `+0x4E4`
- **Kindness**: `+0x4F8`
- **Honesty**: `+0x50C`
- **Generosity**: `+0x520`
- **Laughter**: `+0x534`
- **Magic**: `+0x548`

#### Boutique Crafting Materials:
- **Pins**: `+0x3B4`
- **Buttons**: `+0x3C8`
- **Twine**: `+0x3DC`
- **Ribbons**: `+0x3F0`
- **Bows**: `+0x404`

#### Dual-Write Requirement (The Token Linked List):
Inside `PlayerManager`, certain currencies are also mirrored in an internal `std::list`-style token map. The primary head pointer in `v11.4.1a` resides at:
$$\text{HeadPointer} = [\text{PlayerManager} + 0x818]$$
Fallback head pointer:
$$\text{HeadPointer}_{alt} = [\text{PlayerManager} + 0x858]$$

Each node contains a pointer to a null-terminated identifier string (e.g. `"Token_GQ_bonus"`, `"Token_Social_Chest"`, `"Token_Pop_Pin"`) and a 16-byte `Token16` container. When modifying Group Quest bonus keys or boutique materials, both the direct offset container AND the token list entry must be synchronized to ensure UI elements across disparate Scaleform dialogs stay consistent.

---

### 5.3 Profile Customizations: Scaleform Ownership Gates

The game features 743 profile cosmetic items:
- **507 Avatars**
- **95 Avatar Frames**
- **50 Backgrounds**
- **48 Background Frames**
- **43 Cutie Marks**

Rather than modifying 743 individual database entries in RAM, the game evaluates ownership dynamically through virtual gate functions whenever the Profile UI opens. Each gate function concludes with a conditional byte test:

```x86asm
; Vanilla Ownership Gate Evaluation
test    al, al
setne   al          ; Opcode: 0F 95 C0 (3 bytes)
ret
```

By patching the `setne al` instruction to force `al = 1`, all 743 items unlock immediately:

```x86asm
; Patched Ownership Gate
mov     al, 1       ; Opcode: B0 01
nop                 ; Opcode: 90
ret
```

#### Master Profile Customization Gate RVAs:
| Cosmetic Type | RVA | Vanilla Bytes | Patched Bytes | ASM Translation |
| :--- | :--- | :--- | :--- | :--- |
| **Avatar Gate 1** | `0x5B00A0` | `0F 95 C0` | `B0 01 90` | `mov al, 1; nop` |
| **Avatar Gate 2** | `0x5B037F` | `0F 95 C0` | `B0 01 90` | `mov al, 1; nop` |
| **Avatar Frames** | `0x5B030F` | `0F 95 C0` | `B0 01 90` | `mov al, 1; nop` |
| **Backgrounds** | `0x5B01EF` | `0F 95 C0` | `B0 01 90` | `mov al, 1; nop` |
| **Background Frames** | `0x5B017F` | `0F 95 C0` | `B0 01 90` | `mov al, 1; nop` |
| **Cutie Marks** | `0x5B025F` | `0F 95 C0` | `B0 01 90` | `mov al, 1; nop` |

---

### 5.4 Pony Boutique: Costumes & Sets Unlocker

Unlocking pony costume sets and pieces requires hooking two discrete layers:

#### 1. Piece Ownership Hook (`PonyPartsManager::IsPartOwned`):
- **RVA**: `0x65CAA0`
- **Vanilla**: `48 89 5C 24 08` (`mov [rsp+8], rbx`)
- **Patch**: `B0 01 C3 90 90` (`mov al, 1; ret; nop; nop`)
- **Result**: Every individual costume piece reports owned to the boutique wardrobe.

#### 2. Costume Set Completion Hook (`CostumeSet::IsComplete`):
- **RVA**: `0x956C90`
- **Vanilla**: `48 89 5C 24 10` (`mov [rsp+16], rbx`)
- **Patch**: `B0 01 C3 90 90` (`mov al, 1; ret; nop; nop`)
- **Result**: Set bonuses and set completion rewards activate immediately.

#### 3. Boutique FashionPage Visibility Checks:
Inside the FashionPage rendering method (`0x2F9860`), 7 inline visibility gates test whether craftable outfits should appear in the crafting catalog:
- **RVAs**: `0x2F99F5`, `0x2F9A52`, `0x2F9BBE`, `0x2F9C2C`, `0x2F9C9A`, `0x2F9DF2`, `0x2F9E63`
- **Vanilla**: `0F B6 46 48` (`movzx eax, byte ptr [rsi+0x48]`)
- **Patch**: `B0 01 90 90` (`mov al, 1; nop; nop`)

---

### 5.5 Store Architecture & 2,381 Character Catalog

The in-game store holds an array of 2,381 character records at `[ModuleBase + RVA_SHOP_CONTROLLER]`.

#### In-Memory Store Array Layout:
- **Header**:
  - `+0x438`: Pointer to start of item records array ($Ptr_{start}$)
  - `+0x440`: Pointer to end of item records array ($Ptr_{end}$)
- **Stride**: `0x158` (344 bytes) per item record.
- **Record Structure**:
  ```
  +0x08: uint32_t CategoryId    -> 0x39 for playable character records
  +0x18: uint64_t InternItemPtr -> +0x08 -> null-terminated item ID string
  +0x38: uint64_t ZoneArrayStart-> Pointer to valid town zone IDs array
  +0x40: uint64_t ZoneArrayEnd  -> Pointer to end of town zone IDs array
  +0x90: uint32_t ObfuscatedPrice[4] -> 16-byte encrypted price container (ROR32-5)
  +0x108: uint32_t CurrencyType -> Type: 0 = Bits, 1 = Gems, 2 = Hearts
  +0x110: float   SortPrice     -> Must be >= 1.0f for Scaleform category sorting
  +0x124: uint8_t b124          -> Base availability flag
  +0x125: uint8_t b125          -> Active-on-shelf flag (1 = visible on store shelves)
  +0x126: uint8_t b126          -> Rotation-eligible flag
  ```

#### The 8 Master Code Hooks:
To make unlisted, event-exclusive, and limited-time ponies purchasable directly:

1. **`HOOK_ROT_SETTER` (RVA `0x1301A47`)**:
   - Bypasses rotation XML flag parsing: `0F 94 C0` $\rightarrow$ `B0 01 90` (`mov al, 1; nop`).
2. **`HOOK_ROT_BUILDER` (RVA `0x69FFC3`)**:
   - Bypasses category deque builder restrictions: `74 43` $\rightarrow$ `90 90` (`nop; nop`).
3. **`HOOK_ROT_RENDER` (RVA `0x67C81F`)**:
   - Bypasses shelf render iteration caps: `0F 84 FD 00 00 00` $\rightarrow$ 6x `90`.
4. **`HOOK_BUYABILITY_ALL` (RVA `0x681610`)**:
   - Forces item buyability validation to true: `48 89 5C 24 08` $\rightarrow$ `B0 01 C3 90 90` (`mov al, 1; ret; nop; nop`).
5. **`HOOK_ACTION_POSSIBLE` (RVA `0x3665A0`)**:
   - Scaleform action gate bypass: `40 57 48 83 EC 50 83 79 20 01` $\rightarrow$ `48 8B 09 B2 01 E9 C6 99 89 00`.
6. **`HOOK_GET_CURRENCY` (RVA `0x6C9630`)**:
   - Runtime currency resolver: `48 83 EC 28 48 8B D1 8B 49 68 33 4A 60 8B 42 6C` $\rightarrow$ `8B 81 08 01 00 00 85 C0 75 05 B8 02 00 00 00 C3`.
7. **`HOOK_BUY_FRAME_CHECK` (RVA `0x67DFF9`)**:
   - Dispatcher frame debounce bypass: `0F 8E AC 01 00 00` $\rightarrow$ 6x `90`.
8. **`HOOK_BUY_HOUSE_CHECK` (RVA `0x67F676`)**:
   - Housing space allowance override: `0F 94 C3` $\rightarrow$ `31 DB 90` (`xor ebx, ebx; nop`).

> [!CAUTION]
> **CRITICAL CRASH PITFALL: Zone Check at RVA `0x6C9600`**:
> Legacy tools attempted to patch the town zone validation function at RVA `0x6C9600`. In `v11.4.1a`, modifying `0x6C9600` corrupts the Scaleform category dispatcher, causing an instant CTD (Crash to Desktop) the exact moment the player clicks on the Store button!
> **Rule**: Never patch RVA `0x6C9600`. It must retain its pure vanilla bytes: `4C 8B 41 40 48` (`mov r8, [rcx+0x40]; rex.W`).

---

### 5.6 Fortune Shop & Royal Club Engine Coupling

The Fortune Shop is controlled by `FortuneShopManager` via a double pointer:
$$\text{FSM} = [[\text{ModuleBase} + 0x1A84318]]$$

#### Internal FSM Offsets:
- `+0x08`: Availability flag (`uint8_t`)
- `+0x18`: Red-Black Tree of rarity weights (`sentinel -> root -> nodes`)
- `+0x28`: Total weight sum (`uint32_t = 100`)
- `+0x78`: Day sequence number (`uint64_t`)
- `+0x84`: Refresh cost (`uint32_t`: 0 vs 50 Gems)
- `+0x90`: Timestamp of last refresh (`uint64_t`)

#### Engine Coupling with Royal Club:
The game engine contains an intentional hard lock: free roster refreshes and certain refresh intervals are gated behind **Royal Club Membership** status. If a refresh is forced without active Royal Club credentials in memory, the engine suppresses the refresh or reverts the roster.

The Suite overcomes this by synchronizing the Royal Club enclave in `PlayerManager` at `+0xDA0`:
- `+0xDA0 + 0x48`: `IsActive` = `1` (`uint8_t`)
- `+0xDA0 + 0x70`: `ExpirationTimestamp` = `Now + 31,536,000` (1 year in the future)
- `+0xDA0 + 0x80`: `Tier` = `2` (Gold tier)
- `+0xDA0 + 0x81`: `TierActive` = `1`

#### One-Click Refresh Execution:
1. Walk the rarity red-black tree at `[FSM + 0x18]` and set the **Rare** node weight to 100, and Common/Uncommon to 0.
2. Write `0` to `[FSM + 0x90]` (`LastRefreshTimestamp`).
3. Increment `[FSM + 0x78]` (`DayNumber`).
4. Write `0` to `[FSM + 0x84]` (`RefreshCost`).
5. Write `1` to `[ModuleBase + RVA_UI_INVALIDATE]`.
Result: Instant roster re-roll guaranteed to pull from the rare character pool with zero gem cost.

---

### 5.7 Minigames: State Machine Traversal & Freeze Loops

#### Traversal Algorithm for `StateMinigameFindPair` (State ID 102):
The `StateManager` maintains a circular doubly linked list of active game states at:
$$\text{StateHead} = [[\text{ModuleBase} + 0x1A74338] + 0x08]$$

To find the active minigame instance without hardcoded pointers:
```python
def find_pair_state():
    sm = mem.read_ptr(mem.module_base + RVA_STATE_MANAGER)
    head = mem.read_ptr(sm + 8)
    curr = mem.read_ptr(head)
    visited = set()
    while curr and curr != head and curr not in visited and len(visited) < 60:
        visited.add(curr)
        state_ptr = mem.read_ptr(curr + 0x10)
        if state_ptr:
            state_id = mem.read_u32(state_ptr + 0x28)
            if state_id == 102: # StateMinigameFindPair
                return state_ptr
        curr = mem.read_ptr(curr)
    return None
```

#### Offsets inside `StateMinigameFindPair`:
- `+0x3A4`: Timer display (`uint32_t`)
- `+0x3A8`: Active countdown timer (`float`)
- `+0x3B8`: Pointer to Multiplier Object $\rightarrow `+0x08` \rightarrow `uint32_t` current multiplier
- `+0x3D0`: Pointer to Score Object $\rightarrow `+0x08` \rightarrow `uint32_t` current score

#### Natural Growth Multiplier Lock (`deny_decrease` mode):
Rather than forcing a static integer, the background worker thread samples the multiplier at 20 Hz:
$$\text{If } Mult_{live} > Mult_{target} \implies Mult_{target} \leftarrow Mult_{live}$$
$$\text{If } Mult_{live} < Mult_{target} \implies Mult_{live} \leftarrow Mult_{target}$$
This allows the player's multiplier to climb naturally on successful matches while completely ignoring penalty drops from mistakes.

---

## 6. Playbook: Adapting the Suite for Future Game Updates

When Gameloft releases a new game update (e.g. `v11.4.2a` or `v11.5.0`), memory addresses will shift. Follow this deterministic playbook to update the Suite.

### Step 1: Locate the Target Process & Module Base
Launch the updated game and attach x64dbg / Cheat Engine. Confirm the new executable name and version string in the main window title.

### Step 2: Update Singleton RVAs via Cross-Referenced Strings
Search memory / string references in the `.rdata` section for known singleton registration strings:
- `"PlayerManager"` or `"ResourceManager"` $\rightarrow$ Traces directly to `RVA_PLAYER_MANAGER`.
- `"PlayerLevelManager"` $\rightarrow$ Traces to `RVA_LEVEL_MANAGER`.
- `"PonyPartsManager"` $\rightarrow$ Traces to `RVA_PONY_PARTS_MGR`.
- `"FortuneShopManager"` $\rightarrow$ Traces to `RVA_FSM_POINTER`.
- `"StateMinigameFindPair"` $\rightarrow$ Traces to State ID 102 registration in `StateManager`.

### Step 3: Array of Bytes (AOB) Pattern Signatures
Use these unique byte signatures to relocate core hooks:

| Target Function | Signature (AOB) | Mask | Description |
| :--- | :--- | :--- | :--- |
| `PonyPartsManager::IsPartOwned` | `48 89 5C 24 08 57 48 83 EC 20 48 8B D9 48 8B FA` | `xxxxxxxxxxxxxxx` | Wardrobe piece ownership prologue |
| `CostumeSet::IsComplete` | `48 89 5C 24 10 48 89 74 24 18 57 48 83 EC 20 48 8B F9` | `xxxxxxxxxxxxxxxxx` | Costume set completion prologue |
| Profile Ownership Gates | `0F 95 C0 48 83 C4 20 5B C3` | `xxxxxxxxx` | `setne al; add rsp, 0x20; pop rbx; ret` |
| Store Action Gate | `40 57 48 83 EC 50 83 79 20 01` | `xxxxxxxxxx` | Scaleform purchase validator |
| Store Buyability All | `48 89 5C 24 08 57 48 83 EC 30 48 8B D9 0F B6` | `xxxxxxxxxxxxxxx` | Universal store buyability check |

### Step 4: Verify Container Cipher Constants
Check whether Gameloft modified the rotation constant:
1. Search disassembly for `ror eax, 5` or `rol eax, 5`.
2. If the constant changed from 5 to $N$, update `ror32(val, N)` and `rol32(val, N)` in `core/crypto.py`.

### Step 5: Update Centralized Configuration
Modify `suite/core/offsets.py` with the updated RVAs and version string:
```python
TARGET_GAME_VERSION = "11.x.x"
SUITE_VERSION = "2.x.x"
RVA_PLAYER_MANAGER = 0x...
RVA_LEVEL_MANAGER  = 0x...
```
Because the entire backend, API server, and web frontend are fully decoupled from offsets, updating `core/offsets.py` instantly updates the entire Suite without touching any other files.

---

## 7. Master Glossary & Symbol Map

| Symbol | Location | Data Type | Notes |
| :--- | :--- | :--- | :--- |
| `Container20` | Native | 20-byte struct | Dual XOR + ROR32-5 cipher with shadow check |
| `Token16` | Native | 16-byte struct | Dual XOR + ROR32-5 cipher for token linked list |
| `PlayerLevelManager` | Singleton | Native C++ Class | Holds Level, XP, MaxLevel, and milestone array |
| `PlayerManager` | Singleton | Native C++ Class | Holds currencies, shards, boutique supplies, boosters |
| `ShopManager` | Singleton | Native C++ Class | Manages 2,381-pony character array and shelf rendering |
| `FortuneShopManager` | Double Ptr | Native C++ Class | Controls Fortune Shop daily rotation and gem costs |
| `StateMinigameFindPair` | FSM Node | State ID 102 | Controls Find a Pair timer, multiplier, and score |
| `b124` | `Item + 0x124` | `uint8_t` | Base availability bit in store record |
| `b125` | `Item + 0x125` | `uint8_t` | Active-on-shelf visibility bit in store record |
| `b126` | `Item + 0x126` | `uint8_t` | Rotation-eligibility bit in store record |
| `SortPrice` | `Item + 0x110`| `float` | Sorting key for Scaleform store category view |
| `Scaleform GFx` | Engine Sub | Vector UI | UI framework executing ActionScript inside game |

---

## 8. Security Architecture & Trust Boundaries

The MLPMP Full Suite is designed under a local, user-supervised process memory modification model:

1. **Localhost Loopback Isolation**:
   - The HTTP server is strictly bound to `127.0.0.1`. It never listens on external network interfaces (`0.0.0.0`) and makes zero outbound telemetry or external HTTP requests.
2. **Origin & Host Header Validation**:
   - Requests with missing or untrusted `Host` or `Origin` headers outside `127.0.0.1` and `localhost` are rejected with HTTP 403.
3. **Cross-Site Request Forgery (CSRF) Mitigation**:
   - All state-mutating requests (`POST`) require an ephemeral, 128-bit cryptographically secure session token (`X-Suite-Token`), blocking unauthorized requests from other local browser tabs.
4. **Smart Memory Protection Elevation**:
   - Data writes attempt direct `WriteProcessMemory` first, preserving standard page protections on heap structures. Protection elevation (`PAGE_EXECUTE_READWRITE`) is dynamically reserved only for read-only executable code segments.
5. **Pre-flight Code Signature Verification**:
   - In-place code hooks verify that target opcodes match expected vanilla or previously patched bytes before writing, preventing patch corruption if game revisions shift code locations.
6. **Explicit Version Mismatch Gating**:
   - If the attached game process reports an unexpected version string, memory writes are blocked at both the WebGUI and API dispatcher levels until the user explicitly confirms the override.
7. **Strict Path Resolution & ZipSlip Defense**:
   - Static file delivery validates path resolution with `is_relative_to(WEB_DIR)`, and asset extraction verifies normalized archive entry paths against target directories.
