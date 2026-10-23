# Reverse-Engineering & Research Documentation
## Target Build: *My Little Pony: Magic Princess* (Windows x64 / **v11.5.0**)

> **Read this first.** This document is the durable RE reference for the MLPMP Full Suite.
> It is written for the next engineer or AI agent who has to re-offset the tool for a new game
> build. The **single source of truth for live addresses is [`core/offsets.py`](core/offsets.py)** —
> every RVA and byte signature actually used by the running tool lives there. This file explains
> *what those addresses mean, how they were found, and the mistakes that cost the most time* so
> you do not repeat them. The full re-offset evidence trail for 11.5.0 (per-address verification,
> the costume investigation history, and the asset-extraction findings) is in **Appendix A** below.

---

## 0. Orientation for a Future Update (start here)

The memory **structures, cipher, and patch byte-patterns have been stable across 11.4.2a → 11.5.0.**
Only the module RVAs move between builds. So a version bump is mostly a **relocation** job, not a
re-derivation job. The fast path:

1. Attach to the new build, read the version string, confirm it mismatches.
2. For every RVA in `offsets.py`, relocate it by its **AOB signature** (Section 6), not by copying
   a number. Singletons relocate by their xref/registration string.
3. Keep the `orig` bytes in `offsets.py` as a **pre-flight check**: the tool refuses to patch unless
   the bytes at the new RVA match `orig`. If they don't match, the signature moved *or you found the
   wrong site*. Trust the pre-flight; do not force it.
4. Co-test risky code patches with the game open, one at a time.

**Hard-won pitfalls — read before touching code patches (details in Section 5):**
- **`IsPartOwned` is `0x65B360`, found via the `call` inside the set-build loop — NOT a generic
  `48 89 5C 24 08` prologue match.** Matching prologues blindly picked `0x668A90` (a setter) and
  shipped broken "still shows as craft" costumes for days. Anchor function identity by a *call site
  you can see in context*, then verify live.
- **Never copy a patch whose bytes contain a relative `jmp`/`call` (`E9`/`E8 …`).** The old
  `HOOK_ACTION_POSSIBLE` patch ended in `E9 36 A6 89 00`, a rel32 computed for the *old* address.
  Relocated verbatim it jumps into the wrong function and **crashes the game**. Rel operands must be
  recomputed for the new site, or the hook left disabled. It is currently sentinel-disabled.
- **Never patch the zone-check function (`RVA_ZONE_CHECK`).** Patching it corrupts the Scaleform
  dispatcher and causes an instant crash the moment the Store button is clicked. It must stay vanilla.
- **Store rotation needs only 3 hooks** (`ROT_SETTER`, `ROT_BUILDER`, `ROT_RENDER`). The extra
  buyability/action/housing hooks are sentinel-disabled — they were never needed and were crash risks.
- **Fortune Shop continuous refresh does NOT use the Royal Club free-refresh hack anymore.** The
  modern approach NOPs one instruction so the paid-refresh counter never increments (Section 5.6).

---

## 1. Mission & Scope

Permanent technical specification and RE reference for the Windows x64 PC client of *My Little Pony:
Magic Princess* (Gameloft / Hasbro), current build **v11.5.0** (package `11.5.0.0`). It documents:

1. The runtime memory layout of the engine.
2. Gameloft's in-memory container ciphers (`Container20`, `Token16`).
3. Singleton manager resolution.
4. Scaleform GFx UI ownership gates.
5. Store rotation / shelf population / purchase bypasses.
6. Fortune Shop continuous paid refresh.
7. Pony-editor costume unlock.
8. A deterministic playbook for re-offsetting future builds.

All techniques are **non-invasive virtual-memory introspection** (`ReadProcessMemory` /
`WriteProcessMemory`). Nothing on disk, no saved data, and no executable file is altered.

---

## 2. Target Binary & Execution Environment

- **Executable**: `MyLittlePony_x64.exe` (PE32+, AMD64)
- **Engine**: proprietary Gameloft C++ cross-platform framework
- **UI**: Autodesk Scaleform GFx (ActionScript vector UI composited into the 3D viewport)
- **Packaging**: MSIX/UWP app package; host OS Windows 10/11 x64
- **Mitigations**: ASLR on (base randomized per launch), DEP on (code patches need
  `VirtualProtectEx → PAGE_EXECUTE_READWRITE`, restore after). **No kernel anti-cheat** (no EAC/
  BattlEye) — a standard `OpenProcess` with `VM_READ | VM_WRITE | VM_OPERATION | QUERY_INFORMATION`
  handle is sufficient.

### Dynamic base & RVAs
Because ASLR is active, nothing is hardcoded as an absolute address. Every location is an **RVA**
from the module base:

```
Effective Address = ModuleBase + RVA
```

The module base is resolved at runtime via Toolhelp32 (`CreateToolhelp32Snapshot` with
`TH32CS_SNAPMODULE | TH32CS_SNAPMODULE32`). Note a memory dump of the module has **file-offset == RVA**,
which is what makes the dump-based disassembly workflow (Section 6) line up directly with `offsets.py`.

---

## 3. In-Memory Cryptographic Containers

Critical gameplay values are wrapped in obfuscated containers so a naive 4-byte scanner can't find
or safely write them. **The cipher has not changed across builds** — verify, don't re-derive.

### 3.1 `Container20` (20 bytes) — currencies, shards, level, XP, crafting materials

```cpp
#pragma pack(push, 1)
struct Container20 {
    uint32_t v1;      // +0x00 obfuscated value 1
    uint32_t v2;      // +0x04 obfuscated value 2
    uint32_t k1;      // +0x08 entropy key 1
    uint32_t k2;      // +0x0C entropy key 2
    uint32_t shadow;  // +0x10 plaintext mirror
};
#pragma pack(pop)   // sizeof == 20
```

**Cipher: dual XOR + 32-bit circular rotate, rotation constant = 5.**

```
Decrypt(v, k) = ROR32(v XOR k, 5)
Encrypt(x, k) = ROL32(x, 5) XOR k
Valid  <=>  ROR32(v1^k1,5) == ROR32(v2^k2,5) == shadow
```

If validation fails the engine treats the value as corrupt and resets to zero or desyncs. **When
writing, reuse the existing `k1`/`k2`** so key bytes don't change anomalously — read the container,
keep the keys, re-encode the new value. Reference implementation: `core/crypto.py`
(`rol32`/`ror32`/`decode_container_20`/`encode_container_20`).

### 3.2 `Token16` (16 bytes) — token linked-list entries

Same ROR32-5 cipher, no shadow field. If `k1 == 0 && k2 == 0` the value is plaintext `= v1`;
otherwise `Value = ROR32(v1 ^ k1, 5)`.

---

## 4. Singleton Managers (11.5.0)

All gameplay systems anchor to global singleton pointers in `.data`/`.bss`. **Current RVAs are in
`offsets.py`; the table below is a map of meaning, not a source of truth** (relocate by xref string
on each build, see Section 6).

| Symbol | 11.5.0 RVA | 11.4.2a RVA | Purpose |
| :-- | :-- | :-- | :-- |
| `RVA_PLAYER_MANAGER` | `0x1A7E660` | `0x1A86EE0` | currencies, shards, crafting, tokens, boosters, Royal Club |
| `RVA_LEVEL_MANAGER` | `0x1A6F3C8` | `0x1A77CA8` | level, XP, milestone table |
| `RVA_PONY_PARTS_MGR` | `0x1A70FD8` | `0x1A798B8` | costume pieces / fashion ownership |
| `RVA_STATE_MANAGER` | `0x1A6CA58` | `0x1A75338` | FSM linked list (minigames) |
| `RVA_FSM_POINTER` | `0x1A7CA98` | `0x1A85318` | FortuneShopManager** (double ptr) |
| `RVA_SHOP_CONTROLLER` | `0x1A7FEC0` | `0x1A88740` | character catalog array + shelves |
| `RVA_GAME_STATE` | `0x1AD3630` | `0x1AD79F0` | global frame counters / engine flags |
| `RVA_UI_INVALIDATE` | `0x1A83F20` | `0x1A8C7A0` | UI repaint invalidation flag |
| `RVA_TOWN_CONTROLLER` | `0x1A7F568` | `0x1A87DE8` | zone metadata / placement |
| `RVA_VERSION_STRING` | `0x1548D90` | `0x154DC30` | ASCII build string (`"11.5.0"`) |

---

## 5. Game Mechanics

### 5.1 Level & XP — `PlayerLevelManager` (`[base + RVA_LEVEL_MANAGER]`)

```
+0x00 Container20 CurrentXP
+0x14 Container20 RequiredXP   (threshold for next level)
+0x28 Container20 PlayerLevel  (1..200)
+0x3C Container20 MaxLevel     (cap 200)
+0x50 uint8       IsMaxLevelFlag
+0x58 uint64      XpTablePtr
+0x60 uint32      XpTableCount (200)
```

**Decoupled write rule** — never leave the badge level and the progress bar in disagreement:
- Setting **level L** → look up canonical `XP_base(L)` and `XP_req(L)`; write Level, base XP, required
  XP together.
- Setting **custom XP** → find the interval where `XP_base(L) ≤ XP < XP_req(L)`; write that Level and
  the XP together.

(Co-tested live on 11.5.0: set to 194, read back 194 in-game, restored to 200 — confirmed.)

### 5.2 Currencies, Shards, Materials — `PlayerManager` (`[base + RVA_PLAYER_MANAGER]`)

`Container20` fields (offsets in `offsets.py`): Bits `+0x444`, Gems `+0x458`, Hearts `+0x4BC`;
shards `SHARD_OFFSETS` (loyalty/kindness/honesty/generosity/laughter/magic, `+0x4E4..+0x548`);
crafting materials `MATERIAL_OFFSETS` (pins/buttons/twine/ribbons/bows, `+0x3B4..+0x404`).

**Token dual-write.** Some values are mirrored in an internal `std::list` token map; head pointer
`[PlayerManager + 0x818]` (fallback `+0x858`). Each node → identifier string (e.g. `"Token_GQ_bonus"`,
`"Token_Social_Chest"`, `"Token_Pop_Pin"`) + a `Token16`. When editing Group-Quest keys, friendship
hearts, or crafting materials, write **both** the direct container and the matching token node so every
Scaleform dialog agrees. See `MATERIAL_TOKENS` / `TOKEN_*` in `offsets.py`.

### 5.3 Profile Cosmetics — Scaleform ownership gates (743 items)

Ownership is evaluated by per-category gate functions that end in `setne al`. Force them to return 1:

```
vanilla:  0F 95 C0         setne al
patch:    B0 01 90         mov al, 1 ; nop
```

Six gates (`PROFILE_HOOKS` in `offsets.py`): avatars ×2, avatar frames, backgrounds, background
frames, cutie marks. Unlocks all 743 items (507 avatars / 95 frames / 50 BGs / 48 BG frames /
43 cutie marks) without touching per-item DB records.

### 5.4 Pony Editor — Costumes & Sets (the one that cost the most time)

Costume unlock = **9 code patches**, all forcing a return of true. **This is the authoritative,
CT-verified set** (ported from the working reference Cheat Engine table in `ct/`):

| Hook | 11.5.0 RVA | vanilla | patch |
| :-- | :-- | :-- | :-- |
| `IsPartOwned` (`PonyPartsManager`) | `0x65B360` | `48 89 5C 24 08` | `B0 01 C3 90 90` (`mov al,1;ret;nop;nop`) |
| `IsComplete` (`CostumeSet`) | `0x9573B0` | `48 89 5C 24 10` | `B0 01 C3 90 90` |
| FashionPage visibility ×7 | `0x2FBD05, 0x2FBD62, 0x2FBECE, 0x2FBF3C, 0x2FBFAA, 0x2FC102, 0x2FC173` | `0F B6 46 48` | `B0 01 90 90` (`mov al,1;nop;nop`) |

> **Why this was hard, so you don't repeat it:** `IsPartOwned` was first mis-identified as `0x668A90`
> by matching the generic `48 89 5C 24 08` prologue — that site is a *setter*, not the ownership
> query, and costumes kept "appearing as craft, not buyable." The real function is `0x65B360`, which
> is the target of the `call` inside the costume-set build loop at `0x2FEAEB`. Lesson: **identify a
> function by a call site you can see in context (or by a reference CT), then verify live — never by
> prologue shape alone.** Likewise `IsComplete` was mis-picked as `0x958270` (a string processor); the
> real one is `0x9573B0`.

The 7 FashionPage gates live inside the FashionPage render fn at `0x2FBAF0`. Implementation:
`mechanics/costumes.py` applies exactly these 9 hooks (no bundled store-rotation anymore).

### 5.5 Store — character catalog & rotation

Catalog array at `[base + RVA_SHOP_CONTROLLER]`. Header: `+0x438` start ptr, `+0x440` end ptr;
stride `0x158` per record. Record fields: `+0x08` CategoryId (`0x39` = playable character),
`+0x18→+0x08` item-ID string, `+0x38/+0x40` zone-array start/end, `+0x90` 16-byte encrypted price,
`+0x108` currency type (0 Bits / 1 Gems / 2 Hearts), `+0x110` SortPrice float (must be ≥ 1.0 for
category sorting), `+0x124/125/126` availability / on-shelf / rotation-eligible bytes.

**Rotation uses only 3 hooks** (`STORE_PATCHES` in `offsets.py`), co-tested live:

| Hook | 11.5.0 RVA | vanilla → patch | effect |
| :-- | :-- | :-- | :-- |
| `HOOK_ROT_SETTER` | `0x12FFD1C` | `0F 94 C0` → `B0 01 90` | bypass rotation XML flag |
| `HOOK_ROT_BUILDER` | `0x69F163` | `74 43` → `90 90` | bypass category-deque restriction |
| `HOOK_ROT_RENDER` | `0x67B21F` | `0F 84 FD 00 00 00` → 6×`90` | bypass shelf-render cap |

Supporting (verified): `HOOK_GET_CURRENCY` `0x6C88D0`, `HOOK_BUY_FRAME_CHECK` `0x67C9F9`,
`SORT_PRICE` stub `0x68B931`, `CAN_PLACE` `0x62EE40`.

> **Disabled on purpose (sentinel `0x0FFFFFFF`), do not blindly re-enable:**
> - `HOOK_ACTION_POSSIBLE` (real site `0x368810`) — patch bytes end in rel32 `E9 36 A6 89 00`
>   computed for the *old* address; relocating verbatim **crashed the game**. Rebuild the detour
>   target before enabling.
> - `HOOK_BUYABILITY_ALL`, `HOOK_BUY_HOUSE_CHECK` — best-guess RVAs never live-verified; not needed
>   for rotation or purchase. Verify the function identity before enabling.

> **CRASH — never patch `RVA_ZONE_CHECK` (`0x6C88A0`, vanilla `4C 8B 41 40 48`).** Patching the town
> zone-validation function corrupts the Scaleform category dispatcher → instant crash on opening the
> Store. Keep it vanilla.

(Live-confirmed on 11.5.0: all 38 new 11.5.0 characters appeared in-store, no crash, and a pony —
"Derby Princess Luna" — was purchased successfully.)

### 5.6 Fortune Shop — continuous paid refresh (modern approach)

`FSM = [[base + RVA_FSM_POINTER]]`. Offsets: `+0x08` available, `+0x18` rarity red-black tree,
`+0x28` total weight (100), `+0x78` day number, `+0x84` refresh cost, `+0x88` required level,
`+0x90` last-refresh timestamp, **`+0x99` paid-refresh count** (`>=1` hides the 50-gem button),
`+0x9A` free-available.

**The user's requirement: always able to pay 50 gems to re-roll, no forced Royal Club, no free hack.**
The engine marks a paid refresh "used" by writing `FSM[+0x99] = 1`, which hides the button. A
poll-and-reset race fails because hide+increment is atomic. The fix is a **single code patch**:

```
RVA_FORTUNE_REFRESH_USED = 0x4F98A9
vanilla:  C6 81 99 00 00 00 01   mov byte [rcx+0x99], 1
patch:    90 90 90 90 90 90 90   7× nop
```

NOP that write → the counter never increments → the 50-gem button is **always** available, cooldown
untouched, Royal Club untouched. (Live-confirmed: "works as requested, never hides, no royal club.")

The old Royal-Club coupling (`[PlayerManager + 0xDA0]`: IsActive/Expiration/Tier/TierActive) and the
`RVA_FORTUNE_VIS_CHECK` / `RVA_FORTUNE_FREE_CHECK` patches remain documented in `offsets.py` for
reference, but the continuous-refresh feature no longer depends on them. `set_force_rare` still walks
the rarity tree at `[FSM + 0x18]` to bias the pool to rare when the user opts in.

### 5.7 Minigames — Find a Pair (State ID 102)

`StateManager` holds a circular doubly-linked list of states; head `[[base + RVA_STATE_MANAGER] + 0x08]`.
Walk nodes, read `state_ptr = [node + 0x10]`, match `state_id = [state_ptr + 0x28] == 102`. Inside the
state: `+0x3A4` timer (uint32 display), `+0x3A8` countdown (float), `+0x3B8→+0x08` multiplier,
`+0x3D0→+0x08` score. Multiplier lock uses a 20 Hz "deny-decrease" sampler: raise target to live when
live climbs, raise live to target when live drops (ignores penalty dips, allows natural growth).

---

## 6. Playbook: Re-Offsetting a Future Build

### Step 1 — Attach & confirm version
Launch the new build, attach, read `[base + RVA_VERSION_STRING]`. `core/version_check.py` gates
writes on a version match; update `TARGET_GAME_VERSION` and the detection prefix there.

### Step 2 — Relocate singletons by xref string
Search `.rdata` for registration strings and trace to the pointer: `"PlayerManager"`/`"ResourceManager"`
→ `RVA_PLAYER_MANAGER`, `"PlayerLevelManager"` → `RVA_LEVEL_MANAGER`, `"PonyPartsManager"` →
`RVA_PONY_PARTS_MGR`, `"FortuneShopManager"` → `RVA_FSM_POINTER`, `"StateMinigameFindPair"` → State 102.

### Step 3 — Relocate code hooks by AOB signature
Relocate every hook by pattern, then **let the tool's pre-flight `orig`-byte check confirm the site**.

| Target | AOB signature |
| :-- | :-- |
| `PonyPartsManager::IsPartOwned` | `48 89 5C 24 08 57 48 83 EC 20 48 8B D9 48 8B FA` — but confirm via the `call` in the set-build loop (`~0x2FEAEB`), not the prologue alone |
| `CostumeSet::IsComplete` | `48 89 5C 24 10 48 89 74 24 18 57 48 83 EC 20 48 8B F9` |
| Profile ownership gates | `0F 95 C0 48 83 C4 20 5B C3` (`setne al; add rsp,0x20; pop rbx; ret`) |
| FashionPage visibility | `0F B6 46 48` inside the FashionPage render fn |
| Fortune refresh-used write | `C6 81 99 00 00 00 01` (`mov byte [rcx+0x99], 1`) |
| Store rotation setter | `0F 94 C0` at the rotation XML flag site |

**Rule for any patch containing `E8`/`E9` (rel32 call/jmp): recompute the operand for the new address.
Never relocate such a patch verbatim.** (This is what crashed `HOOK_ACTION_POSSIBLE`.)

### Step 4 — Verify the cipher constant
Search disassembly for `ror eax, 5` / `rol eax, 5`. If Gameloft changed the constant from 5 to N,
update `ror32`/`rol32` in `core/crypto.py`. (Unchanged through 11.5.0.)

### Step 5 — Update `offsets.py` only
Edit `core/offsets.py` (`TARGET_GAME_VERSION`, `SUITE_VERSION`, the RVAs). The backend, API
server, and web frontend are fully decoupled from offsets — updating this one file updates the whole
Suite. Keep the `11.4.2a: 0x…` trailing comments as a relocation audit trail, and add an
`11.x.x: 0x…` column as you go.

### Step 6 — Co-test live, one patch at a time
Risky code patches (store, fortune, costume) are applied and verified with the game running, singly,
watching for crashes. Pre-flight mismatches mean *stop and re-find the site*, not *force the write*.

### Tooling note
The scratchpad RE workflow used for 11.5.0: dump the module (`dump_module.py`), disassemble with
capstone against the dump (file-offset == RVA), index RIP-relative xrefs, value/structural
fingerprint singletons, and — when static analysis is ambiguous — a VirtualAllocEx RWX **code cave**
with a detour `jmp` at a candidate hook to log live register state (`inject.py`). This runtime
confirmation is how function identity was finally nailed down where prologue matching failed.

---

## 7. Catalog & Assets (11.5.0)

`data/ponies_catalog.json` was regenerated from live RAM: **2,418 ponies**, `game_version`
`11.5.0`. The 38 new 11.5.0 characters have portrait PNGs (`portraits/Pony_<id>.png`) shipped in
`web/assets_part4.zip`, sourced from all-the-ponies.com per-pony icons.

---

## 8. Web UI — input preservation (polling vs. user typing)

The web UI (`web/js/app.js`) polls the local server and re-renders live state. **The render must
not overwrite an input the user is actively editing**, or currency/level fields get clobbered mid-type.
Guard every poll-driven `input.value = …` with the active-element check already used for the fortune
toggle:

```js
const el = document.getElementById('input-bits');
if (el && document.activeElement !== el) el.value = newValue;
```

Applies to currencies, shards, materials, level/XP, and booster inputs. Staged user input is preserved
across polls as of Suite 2.2.0.

---

## 9. Security Architecture & Trust Boundaries

1. **Loopback only** — HTTP server bound to `127.0.0.1`; never `0.0.0.0`; zero outbound telemetry.
2. **Host/Origin validation** — requests outside `127.0.0.1`/`localhost` rejected with 403.
3. **CSRF** — all `POST` mutations require the ephemeral 128-bit `X-Suite-Token`.
4. **Minimal protection elevation** — direct `WriteProcessMemory` first; `PAGE_EXECUTE_READWRITE`
   reserved only for read-only code segments, restored after.
5. **Pre-flight byte verification** — code hooks confirm bytes match expected vanilla/patched before
   writing; a mismatch aborts the write (this is your re-offset safety net — never bypass it).
6. **Version gating** — unexpected version string blocks writes at both WebGUI and API until the user
   explicitly overrides.
7. **Path safety** — static delivery validates `is_relative_to(WEB_DIR)`; archive extraction normalizes
   entry paths (ZipSlip defense).

---

## 10. Glossary

| Symbol | Type | Notes |
| :-- | :-- | :-- |
| `Container20` | 20-byte struct | dual XOR + ROR32-5, shadow-validated |
| `Token16` | 16-byte struct | ROR32-5, no shadow; plaintext if keys == 0 |
| `PlayerManager` | singleton | currencies, shards, materials, boosters, Royal Club, token list |
| `PlayerLevelManager` | singleton | level, XP, milestone table |
| `PonyPartsManager` | singleton | costume pieces / fashion ownership (`IsPartOwned` 0x65B360) |
| `ShopManager` | singleton | character catalog array + shelf rendering |
| `FortuneShopManager` | double ptr | daily rotation; `+0x99` paid-refresh count is the refresh lever |
| `StateMinigameFindPair` | State 102 | timer / multiplier / score |
| `RVA_ZONE_CHECK` | code | **do not patch** — crashes Store |
| Scaleform GFx | engine | ActionScript vector UI; most ownership gates live here |

---

## Appendix A: 11.5.0 Re-Offset Evidence Trail

This appendix is the working record of how the 11.5.0 addresses were derived and verified. It is kept
inside this document on purpose so the evidence travels with the repo. Status markers: `[verified]`
confirmed with evidence noted; `[probable]` strong static evidence, confirm live; `[history]` a
dead-end or intermediate finding kept so it is not re-attempted.

### A.1 Capture method and dump

- Target: `MyLittlePony_x64.exe`, MSIX package **11.5.0.0**
  (`A278AB0D.MyLittlePonynew_11.5.0.0_x64__h6adky7gbf63m`).
- Method: live user-mode `ReadProcessMemory` dump of the loaded module image, so **file-offset == RVA**.
  Capstone disassembly plus structural/value fingerprinting; where static analysis was ambiguous, a
  VirtualAllocEx RWX code cave with a detour `jmp` logged live register state.
- Dump at capture: base `0x7FF62D330000`, `SizeOfImage` `0x1C51000`. The module dump and analysis
  scripts live in the session scratchpad (`scripts/rpm.py`, `inject.py`, `examine_sets.py`,
  `own_sunburst.py`, `dump_module.py`); a re-dump is not needed for the same exe version.
- All findings here are base-independent (module RVAs / struct offsets); only live heap addresses
  change between launches.

### A.2 Singleton verification evidence

The `.data` singleton block shifted by roughly `-0x888x` from 11.4.2a but **not uniformly** (Player
`-0x8880`, Level `-0x88E0`), so each pointer was individually confirmed:

| Symbol | 11.4.2a | 11.5.0 | Evidence |
| :-- | :-- | :-- | :-- |
| `RVA_PLAYER_MANAGER` | 0x1A86EE0 | 0x1A7E660 | [verified] decrypts bits=777,893,899 gems=744,754 hearts=9,639 + 6 shards; all 9 containers validly encrypted |
| `RVA_LEVEL_MANAGER` | 0x1A77CA8 | 0x1A6F3C8 | [verified] curXP=reqXP=60,107,610 level=200 max=200 (canonical maxed) |
| `RVA_FSM_POINTER` | 0x1A85318 | 0x1A7CA98 | [verified] `[[slot]]` -> FSM totalWeight=100 avail=1 cost=50 reqLvl=35, valid rarity tree |
| `RVA_SHOP_CONTROLLER` | 0x1A88740 | 0x1A7FEC0 | [verified] Store open: `+0x438/+0x440` -> 4470 records, 2419 ponies (cat==0x39) |
| `RVA_UI_INVALIDATE` | 0x1A8C7A0 | 0x1A83F20 | [verified] flag slot written by fortune code; matches `-0x8880` delta |
| `RVA_PONY_PARTS_MGR` | 0x1A798B8 | 0x1A70FD8 | [verified] confirmed at the costume (Pony Editor) patch test |
| `RVA_TOWN_CONTROLLER` | 0x1A87DE8 | 0x1A7F568 | [probable] hot vtable slot (`-0x8880`); confirm on entering town |
| `RVA_STATE_MANAGER` | 0x1A75338 | 0x1A6CA58 | [probable] vtable-in-module, matches `-0x88E0`; confirm with Find-a-Pair (state 102) |
| `RVA_GAME_STATE` | 0x1AD79F0 | 0x1AD3630 | [verified] resolved (an early prediction `0x1ACF170` was wrong, held=15) |
| `RVA_VERSION_STRING` | 0x154DC30 | 0x1548D90 | [verified] ASCII `"11.5.0"` |

### A.3 Code-patch site evidence (.text was reordered; deltas non-uniform)

| Hook | 11.4.2a | 11.5.0 | Evidence |
| :-- | :-- | :-- | :-- |
| `HOOK_ACTION_POSSIBLE` | 0x366600 | 0x368810 | [verified] unique AOB `40 57 48 83 EC 50 83 79 20 01`. RVA correct, but patch bytes end in rel jmp `E9 36 A6 89 00` computed for the old site; left disabled (see A.5) |
| `HOOK_GET_CURRENCY` | 0x6C9760 | 0x6C88D0 | [verified] disasm is the ROR32-5 currency-type resolver; orig/patch unchanged |
| `RVA_ZONE_CHECK` (do NOT patch) | 0x6C9730 | 0x6C88A0 | [verified] vanilla `4C 8B 41 40 48`, 0x30 before the currency resolver |
| `RVA_FORTUNE_VIS_CHECK` | 0x81D90C | 0x81DA7C | [verified] `je` (`74 04`), 0xF before free-check |
| `RVA_FORTUNE_FREE_CHECK` | 0x81D91B | 0x81DA8B | [verified] `cmp r8d,2; sete al` |
| `HOOK_BUY_FRAME_CHECK` | 0x67E129 | 0x67C9F9 | [verified] unique AOB `0F 8E AC 01 00 00` |
| `RVA_SORT_PRICE_STUB` | 0x68CEC1 | 0x68B931 | [verified] unique AOB `F3 41 0F 11 74 24 50` |
| Profile gates x6 | 0x5B01F0... | 0x5AE6E0/7BF/82F/89F/94F/9BF | [verified] applied + confirmed live (all customizations unlocked) |
| Store rotation x3 | 0x1301CD7 / 0x6A00F3 / 0x67C94F | 0x12FFD1C / 0x69F163 / 0x67B21F | [verified] all orig-matched; surfaced all 38 new event ponies; bought Derby Princess Luna, no crash |
| `RVA_PART_OWNED` | 0x65CBD0 | 0x65B360 | [verified] the `call 0x65B360` in the set loop at 0x2FEAEB (not a prologue match; see A.4) |
| `RVA_SET_COMPLETE` | 0x956F60 | 0x9573B0 | [verified] = CHECK_B; CT-confirmed |
| `COSTUME_VIS_RVAS` x7 | 0x2F9... | 0x2FBD05/0x2FBD62/0x2FBECE/0x2FBF3C/0x2FBFAA/0x2FC102/0x2FC173 | [verified] FashionPage render fn 0x2FBAF0 |

Confirmed-working features, co-tested live: profile customizations unlocked; currency edits persisted
across a crash+relaunch; store rotation + purchase with only the 3 rotation hooks; costume unlock
matching the reference CT.

### A.4 Costume investigation history (why this took the longest)

The shipping solution is the 9-hook set in Section 5.4. The path to it, kept so it is not repeated:

- **Mis-identification by prologue.** `IsPartOwned` was first guessed as `0x668A90` by matching the
  generic `48 89 5C 24 08` prologue (30 candidate hits); that site is a setter and costumes kept
  showing as "craft, not buyable." `IsComplete` was likewise mis-picked as `0x958270` (a string
  processor, 14 prologue hits). The correct functions are `0x65B360` (target of the `call` in the
  set-build loop at `0x2FEAEB`) and `0x9573B0`. Lesson: identify by a call site visible in context or
  by a reference table, then verify live.
- **Making hidden sets appear.** The set-visibility filter is in the population loop at `0x2FE9A0`: a
  set shows iff `CHECK_A(0x957200, owned flag set+0x79)` OR `CHECK_B(0x9573B0, avail flag set+0x8a)`.
  Hidden sets fail both and are skipped (`je`). Patching CHECK_B (`0x9573B0`, `48 89 5C 24 10` ->
  `B0 01 C3 90 90`) makes all hidden sets appear (confirmed live for Sunburst). It feeds a set-count
  tally, so watch progress math.
- **The old "appear but not obtainable" dead-end.** Appeared sets were event sets showing "craft" with
  "Check events every day..." and no buy path by design. CHECK_A (owned fn) patch had no visible effect
  (display reads data, not the fn). The set-button display fn `0x2FA4F0` reads the owned flag directly
  at `0x2FA5F6` (`movzx [rsi+0x79]`) plus prices at `set+0x98/+0x9c`; forcing that read to 1 did not
  change "craft" because Scaleform keys the crafted/locked/notCrafted frame off a different field. The
  label strings are at `0x1589368/70/78` (crafted/locked/notCrafted); state-label selection refs at
  `0x844B18`, `0x6A9A63`.
- **Runtime instrumentation (code cave at CHECK_B `0x9573B0`, logging rcx=set).** CostumeSet layout:
  id `char*` at `+0x08` (e.g. `"SET_Sunburst_00"` default, `"SET_Sunburst_DDD_TLS_MAIN/SUB_1..3"` for
  hidden event sets); `+0x79` collection-owned byte (across 279 live sets: 212 owned / 67 not); `+0x8a`
  available byte; float prices at `+0x98/+0x9c`; pieces vector at `+0xd0/+0xd8`. Set objects are rebuilt
  on every editor/book open (owned resets to 0), so direct data writes do not persist. The Pony Editor
  costume selector does not read `set+0x79` (no `0F B6 ?? 79` in `0x790000-0x7B0000`): it uses a
  separate wardrobe/owned-costume system distinct from the Collection Book's `set+0x79`.
- **Resolution.** The user's Gemini-updated reference CT (`../ct/MLPMPFullSuite_v11.5.0a.CT`) achieved the
  desired behavior with the 9 hooks now in `offsets.py`: `IsPartOwned` and `IsComplete` forced to
  `mov al,1; ret`, and the 7 FashionPage `movzx [rsi+0x48]` (`0F B6 46 48`) gates forced to
  `mov al,1`. StateFashion state id = `0x4C` (ctor `0x812880`); the pony-editor active state was
  observed as id `0x40`.

### A.5 Store hooks left disabled on purpose

Sentinel `0x0FFFFFFF` in `offsets.py`; do not re-enable without the stated work:

- `HOOK_ACTION_POSSIBLE` (real site `0x368810`): caused the crash-to-desktop. Its patch ends in a rel
  `jmp` (`E9 36 A6 89 00`) computed for the old `0x366600`; at `0x368810` it lands in the wrong
  function. The RVA is correct; the patch bytes must be rebuilt (recompute the detour target).
- `HOOK_BUYABILITY_ALL` (best-guess `0x680D60`): never verified; purchase works without it.
- `HOOK_BUY_HOUSE_CHECK` (best-guess `0x67E2E3`/`0x67E076`): never verified; niche housing feature.
- `RVA_CAN_PLACE_STUB` (`0x62EE40`, best-guess): remediation-only (acts only if it sees `B0 01 C3`),
  low risk, not a feature.

### A.6 Struct-offset confirmations

- PlayerManager currency/shard/material offsets unchanged, value-verified via the cipher. Materials
  read as valid Container20 (pins `+0x3B4`, buttons `+0x3C8`, twine `+0x3DC`, ribbons `+0x3F0`, bows
  `+0x404`). The entire PlayerManager layout is stable; only the RVA moved.
- LevelManager level/XP offsets unchanged (`+0x00/+0x14/+0x28/+0x3C`). Caution: a u32 at `+0x60` read
  1000 where the old doc said table-count 200, so re-check the XpTable offsets if you touch them.
- FSM field offsets stable (`+0x08` avail, `+0x18` tree, `+0x28` weight, `+0x84` cost, `+0x88` level).
- Royal Club (`+0xDA0`: active `+0x48`, expiration `+0x70`, tier `+0x80`, tier-active `+0x81`),
  boosters (`+0x1178/+0x1180` doubles, `+0x1188/+0x118C` float mults, default 1.0), ferris wheel
  (`+0x898`), token-list heads (`+0x818` primary, `+0x858` secondary): all verified live and unchanged.
- Store record layout unchanged from 11.4.2a: stride `0x158`, cat `@+0x08`==0x39, id `@+0x18`->`+8`,
  zones `@+0x38/+0x40`, SortPrice, currency, price `@+0x90`, xml-currency `@+0x108`, `b125 @+0x125`,
  `b126 @+0x126`. (An early note mis-read the stride as `0x130`; the live records confirm `0x158`.)
- Find-a-Pair state offsets (`+0x3A4/+0x3A8/+0x3B8/+0x3D0`): verify with the minigame active.
- Cipher `Container20` ROR32 rotation = 5, unchanged (currencies decrypt with `dec1==dec2==shadow`).
  `PAIR_STATE_ID = 102` (0x66): the state ctor at `0x87FB60` loads `r8d, 0x66` immediately before the
  `"StateMinigameFindPair"` string.

### A.7 Catalog and portrait assets

- Catalog regenerated from live RAM: **2,418 ponies** (2,419 records with cat==0x39, one empty id),
  written to `data/ponies_catalog.json` (game_version 11.5.0). The Store record layout is
  unchanged, so `store.py` needed no layout change.
- 38 new ponies vs the old 2,381 (matches the in-game screenshot): Ringmaster, First Folio, Phony
  Pharaoh, Sweetcream Scoops, Ordinary Mane-iac, Hum Drum Spike, Sneaky Pete, Steel Buns, 5x Mane-iac
  Henchpony, E.W.E. Referee, the Derby set, and the Edgy set. One removed: Queen_Cleopatrot.
- Portraits for the 38 new ponies ship in `web/assets_part4.zip` as `portraits/Pony_<id>.png`,
  sourced from all-the-ponies.com per-pony icons. The game `.ark` route was investigated and parked:
  the format is a 16-byte header + zstd frames (each a PVR texture) + an encrypted/hashed TOC. PVR
  frames decode cleanly to PNG, but the TOC has no plaintext filenames, portrait icons could not be
  matched by name across the 6 archives (up to 1.4 GB), and cracking the hashed-TOC naming (needs the
  exe loader code) was disproportionate for 38 thumbnails.

---

*Source of truth for all live addresses and byte patterns: [`core/offsets.py`](core/offsets.py).
The evidence behind those numbers, and the dead-ends not to repeat, are in Appendix A above. This
document explains the meaning and the pitfalls; the code holds the numbers.*
