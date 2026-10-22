# MLPMP Full Suite — 11.5.0 Re-offset Working Notes

Target: `MyLittlePony_x64.exe`, MSIX package **11.5.0.0**
(`A278AB0D.MyLittlePonynew_11.5.0.0_x64__h6adky7gbf63m`).
Method: live user-mode `ReadProcessMemory` dump of the loaded module image
(file-offset == RVA), capstone disassembly + structural/value fingerprinting.
Dump base at capture: `0x7FF62D330000`, SizeOfImage `0x1C51000`.

Legend: ✅ verified (evidence noted) · ⏳ pending · ⚠️ needs live apply/revert crash-test.

---

## ⏸️ SESSION PAUSED (PC restart) — RESUME CHECKLIST
All findings below are **base-independent** (module RVAs / struct offsets) and stay valid
across the reboot — the game's live heap addresses change but nothing here depends on them.
The module dump `scratchpad/bin_1150/module_dump.bin` + analysis scripts persist on disk.

**On resume:**
1. Relaunch game (11.5.0). Re-attach: scripts auto-find PID + base via `scripts/rpm.py`.
2. (Optional) re-dump is NOT needed — same exe version = same RVAs; existing dump is valid.
3. Continue with: remaining code-hook RVAs → write `offsets.py` → live patch co-test →
   secondary find-a-pair offsets (needs minigame active) → docs. Portraits parked (user/antigravity).

### ✅ READY TO WRITE into `suite/core/offsets.py` (all verified):
```
TARGET_GAME_VERSION = "11.5.0"          # was "11.4.2a"
# SUITE_VERSION: decide (repo inconsistent: offsets=2.1.1, catalog=v4.0.0, git tag v2.1.1)
RVA_VERSION_STRING   = 0x1548D90        # version_check.py (was 0x154DC30); match "11.5.0"
RVA_PLAYER_MANAGER   = 0x1A7E660        # was 0x1A86EE0  ✅ value-verified
RVA_LEVEL_MANAGER    = 0x1A6F3C8        # was 0x1A77CA8  ✅ value-verified
RVA_FSM_POINTER      = 0x1A7CA98        # was 0x1A85318  ✅ struct-verified
RVA_SHOP_CONTROLLER  = 0x1A7FEC0        # was 0x1A88740  ✅ live-verified (2419 ponies)
RVA_UI_INVALIDATE    = 0x1A83F20        # was 0x1A8C7A0  ✅ code-verified
RVA_PONY_PARTS_MGR   = 0x1A70FD8        # was 0x1A798B8  ◐ confirm at IsPartOwned patch test
RVA_TOWN_CONTROLLER  = 0x1A7F568        # was 0x1A87DE8  ◐ confirm live (town)
RVA_STATE_MANAGER    = 0x1A6CA58        # was 0x1A75338  ◐ confirm live (Find-a-Pair)
RVA_GAME_STATE       = 0x1AD79F0        # ⏳ STILL TO FIND (prediction 0x1ACF170 was wrong)
# --- code-patch sites (.text) already found ---
HOOK_ACTION_POSSIBLE  rva 0x368810      # was 0x366600  ✅ (orig/patch bytes unchanged)
HOOK_GET_CURRENCY     rva 0x6C88D0      # was 0x6C9760  ✅ (orig/patch unchanged)
RVA_ZONE_CHECK        = 0x6C88A0        # was 0x6C9730  ✅ do-NOT-patch; vanilla 4C 8B 41 40 48
RVA_FORTUNE_VIS_CHECK = 0x81DA7C        # was 0x81D90C  ✅
RVA_FORTUNE_FREE_CHECK= 0x81DA8B        # was 0x81D91B  ✅
HOOK_BUY_FRAME_CHECK  rva 0x67C9F9      # was 0x67E129  ✅
RVA_SORT_PRICE_STUB   = 0x68B931        # was 0x68CEC1  ✅
```
**ALL struct offsets UNCHANGED** (verified live): PlayerManager currencies/shards/materials/
royalclub/boosters/ferris/tokenlist; LevelManager level/XP; FSM fields; Store record (stride
0x158, all fields). Cipher ROR32-5 unchanged. PAIR_STATE_ID=102.

### ✅ CODE HOOKS RESOLVED + co-tested:
- Profile gates ×6 (0x5AE6E0/7BF/82F/89F/94F/9BF): APPLIED + confirmed live (all customizations unlocked).
- Currency edit (bits/gems/hearts): confirmed live, persisted across a crash+relaunch.
- **Store rotation + PURCHASE: CONFIRMED WORKING** with only 3 hooks — ROT_SETTER 0x12FFD1C,
  ROT_BUILDER 0x69F163, ROT_RENDER 0x67B21F (all orig-matched, surfaced all 38 new event ponies;
  bought Derby Princess Luna successfully, no crash). Selection (b125/b126) alone hides/shows;
  these 3 hooks bypass the rotation filter for event/non-rotated ponies.
- GET_CURRENCY 0x6C88D0, BUY_FRAME 0x67C9F9: correct locations (safe patches), active, not separately needed.
- GAME_STATE 0x1AD3630 (medium).

### ⚠️ STORE HOOKS DISABLED (sentinel 0x0FFFFFFF) — not needed, were risky:
- HOOK_ACTION_POSSIBLE (real site 0x368810): CAUSED THE CTD. Patch ends in a rel jmp (E9 36 A6 89 00)
  computed for old 0x366600; at 0x368810 it lands in the wrong function. Patch BYTES need rebuilding
  (recompute detour target) — needs the 11.4.2a binary to reconstruct. RVA itself is correct.
- HOOK_BUYABILITY_ALL (best-guess 0x680D60): never verified; purchase works without it.
- HOOK_BUY_HOUSE_CHECK (best-guess 0x67E2E3/0x67E076): never verified; niche housing feature.
- RVA_CAN_PLACE_STUB 0x62EE40 (best-guess): remediation-only (acts only if it sees B0 01 C3), low risk.

### ✅ COSTUMES — RESOLVED (via reference CT table ct/MLPMPFullSuite_v11.5.0a.CT):
The working unlock is 9 hooks forced true: **IsPartOwned = 0x65B360** (the `call 0x65b360` in the
set loop at 0x2FEAEB — my earlier 0x668A90 was WRONG), **IsComplete = 0x9573B0** (= CHECK_B),
and the 7 FashionPage VIS gates 0x2FBD05/0x2FBD62/0x2FBECE/0x2FBF3C/0x2FBFAA/0x2FC102/0x2FC173
(movzx[rsi+0x48] 0F B6 46 48 -> B0 01 90 90; the two checks -> B0 01 C3 90 90). Baked into
offsets.py + costumes.py; UI re-enabled; co-tested working (matches the CT). History below.

### ◐ (earlier dead-ends, kept for reference) hidden sets APPEAR but not obtainable:
System = Pony Editor / Collection Book. Sets have states crafted/locked/notCrafted, prices
(SetPrice), Buy/Craft actions (Native_BuyPonySet). StateFashion state id = 0x4C (ctor 0x812880);
pony editor active state observed as id 0x40.

RESOLVED — make hidden sets APPEAR (co-tested working):
- Set-visibility filter is in the population loop at 0x2FE9A0: a set shows iff
  CostumeSet CHECK_A(0x957200, owned flag set+0x79) OR CHECK_B(0x9573B0, avail flag set+0x8a).
  Hidden sets fail both and are skipped (je).
- **Patch CHECK_B (0x9573B0, orig 48 89 5C 24 10 -> B0 01 C3 90 90 = mov al,1;ret) makes ALL
  hidden sets APPEAR.** Confirmed live for Sunburst. ⚠️ feeds a set-count tally; watch progress math.

BLOCKED — obtaining them:
- Appeared sets are EVENT sets: show "craft" + "Check events every day..." (pieces not available;
  no buy path by design). Goal was "buyable" but these have no buy flow.
- CHECK_A (0x957200, owned fn) patch = no visible effect (display reads data, not the fn).
- Set-button display fn 0x2FA4F0 reads owned flag DIRECTLY at 0x2FA5F6 (movzx [rsi+0x79]) +
  prices at set+0x98/+0x9c; forcing that read to 1 did NOT change "craft" -> Scaleform keys the
  crafted/locked/notCrafted frame off a different field. The label strings sit at 0x1589368/70/78
  (crafted/locked/notCrafted); state-label selection refs at 0x844B18, 0x6A9A63 (needs tracing).
- NEEDS NEXT: trace the actual frame-label selection (how set-state -> crafted/notCrafted),
  OR force piece ownership so craft works, OR find a real buy-enable for event sets. Live experiment
  patches (0x9573B0, 0x2FA5F6, 0x957200) were reverted; NONE baked into offsets.py yet.
- offsets.py costume hooks remain sentinel'd (safe no-op).

RUNTIME INSTRUMENTATION findings (code-cave at CHECK_B 0x9573B0 logging rcx=set):
- CostumeSet object layout: id char* at +0x08 (e.g. "SET_Sunburst_00" default, "SET_Sunburst_DDD_TLS_MAIN/SUB_1..3"
  = hidden event set); +0x79 = collection-owned byte (across 279 live sets: 212 owned / 67 not);
  +0x8a = available byte; float "prices" at +0x98/+0x9c; pieces vector at +0xd0/+0xd8.
- Set objects are REBUILT on every editor/book open (owned resets to 0) -> direct data writes don't persist.
- The Pony Editor costume selector does NOT read set+0x79 (no 0F B6 ?? 79 anywhere in 0x790000-0x7B0000):
  it uses a SEPARATE wardrobe/owned-costume system, distinct from the Collection Book's set+0x79.
- So "buyable in pony editor" needs the pony-editor wardrobe ownership + buy path cracked (deeper layer).
  Confirmed achievable: CHECK_B patch makes hidden sets APPEAR (browse). Buy/wear = separate deep subsystem.
- Capture tooling: scratchpad/scripts/inject.py (install/read/remove), examine_sets.py, own_sunburst.py.

### ✅ DONE deliverables:
- `suite/data/ponies_catalog.json` → 2418 ponies, v11.5.0 (38 new, regenerated from live RAM).

---

## Confirmed constants / cipher
- ✅ `Container20` cipher unchanged: ROR32 rotation = **5** (currencies decrypt with
  `dec1==dec2==shadow`).
- ✅ `PAIR_STATE_ID = 102` (0x66) — state ctor at `0x87FB60` loads `r8d, 0x66`
  immediately before the `"StateMinigameFindPair"` string.
- ✅ Version string `"11.5.0"` at **RVA `0x1548D90`** (was `0x154DC30`/"11.4.2").

## Singletons (RVA from module base)
| Symbol | 11.4.2a | 11.5.0 | Status / evidence |
| :-- | :-- | :-- | :-- |
| `RVA_PLAYER_MANAGER` | 0x1A86EE0 | **0x1A7E660** | ✅ decrypts real bits=777,893,899 gems=744,754 hearts=9,639 + 6 shards, all 9 containers encrypted |
| `RVA_LEVEL_MANAGER` | 0x1A77CA8 | **0x1A6F3C8** | ✅ curXP=reqXP=60,107,610 level=200 max=200 (canonical maxed) |
| `RVA_FSM_POINTER` | 0x1A85318 | **0x1A7CA98** | ✅ [[slot]]→FSM totalW=100 avail=1 cost=50 reqlvl=35, valid rarity tree |
| `RVA_SHOP_CONTROLLER` | 0x1A88740 | **0x1A7FEC0** | ✅ VERIFIED LIVE (Store open): +0x438/+0x440 → 4470 recs, 2419 ponies (cat==0x39), all fields match old |
| `RVA_UI_INVALIDATE` | 0x1A8C7A0 | **0x1A83F20** | ✅ flag slot (held=0) written −1 by fortune code; matches −0x8880 delta |
| `RVA_PONY_PARTS_MGR` | 0x1A798B8 | **0x1A70FD8** | ◐ med-high: hot in FashionPage code (−0x88E0); verify live (Pony Editor) |
| `RVA_TOWN_CONTROLLER` | 0x1A87DE8 | **0x1A7F568** | ◐ med-high: hot vtable slot (−0x8880); verify live (enter town) |
| `RVA_STATE_MANAGER` | 0x1A75338 | **0x1A6CA58** | ◐ med: vt_in_mod, matches −0x88E0; verify live (start Find-a-Pair → state id 102) |
| `RVA_GAME_STATE` | 0x1AD79F0 | ⏳ | predicted 0x1ACF170 WRONG (held=15); find separately (only fortune refresh-seen flag) |

Note: `.data` singleton block shifted ≈ −0x888x but NOT uniformly (Player −0x8880,
Level −0x88E0), so each must be individually verified.

## Code-patch sites (.text; deltas are non-uniform — .text was reordered)
| Hook | 11.4.2a | 11.5.0 | Status |
| :-- | :-- | :-- | :-- |
| `HOOK_ACTION_POSSIBLE` | 0x366600 | **0x368810** | ✅ unique AOB `40 57 48 83 EC 50 83 79 20 01` |
| `HOOK_GET_CURRENCY` | 0x6C9760 | **0x6C88D0** | ✅ disasm = ROR32-5 currency-type resolver; orig/patch unchanged |
| `RVA_ZONE_CHECK` (do NOT patch) | 0x6C9730 | **0x6C88A0** | ✅ vanilla `4C 8B 41 40 48`, 0x30 before currency resolver |
| `RVA_FORTUNE_VIS_CHECK` | 0x81D90C | **0x81DA7C** | ✅ `je` (74 04), 0xF before free-check |
| `RVA_FORTUNE_FREE_CHECK` | 0x81D91B | **0x81DA8B** | ✅ `cmp r8d,2; sete al` |
| `HOOK_BUY_FRAME_CHECK` | 0x67E129 | **0x67C9F9** | ✅ unique AOB `0F 8E AC 01 00 00` |
| `RVA_SORT_PRICE_STUB` | 0x68CEC1 | **0x68B931** | ✅ unique AOB `F3 41 0F 11 74 24 50` |
| Profile gates ×6 | 0x5B01F0… | ⏳⚠️ | epilogue sig changed; cluster-locate + live test |
| `RVA_PART_OWNED` | 0x65CBD0 | ⏳ | generic prologue (30 hits); disambiguate by caller |
| `RVA_SET_COMPLETE` | 0x956F60 | ⏳ | generic prologue (14 hits) |
| `COSTUME_VIS_RVAS` ×7 | 0x2F9… | ⏳⚠️ | relocate in FashionPage fn |
| `HOOK_ROT_SETTER` | 0x1301CD7 | ⏳⚠️ | `0F 94 C0` common |
| `HOOK_ROT_BUILDER` | 0x6A00F3 | ⏳⚠️ | `74 43` common |
| `HOOK_ROT_RENDER` | 0x67C94F | ⏳⚠️ | `0F 84 FD 00 00 00` 30 hits |
| `HOOK_BUYABILITY_ALL` | 0x681740 | ⏳ | generic prologue |
| `HOOK_BUY_HOUSE_CHECK` | 0x67F7A6 | ⏳⚠️ | `0F 94 C3` common |
| `RVA_CAN_PLACE_STUB` | 0x6303C0 | ⏳ | remediation stub |

## Struct offsets
- ✅ PlayerManager currency/shard/material offsets unchanged (value-verified via cipher).
- ✅ LevelManager level/XP offsets unchanged (+0x00/+0x14/+0x28/+0x3C). Note: u32 at
  +0x60 read 1000 (old doc said table count 200) — re-check XpTable offsets.
- ✅ FSM field offsets appear stable (+0x08 avail, +0x18 tree, +0x28 weight, +0x84 cost, +0x88 lvl).
- ⏳ Store record re-laid-out: stride 0x158 → **0x130**; cat/id/zone/SortPrice/currency/
  price/b125/b126 offsets must be re-mapped against live records.
- ✅ Royal Club (+0xDA0: active+0x48, exp+0x70, tier+0x80, tieractive+0x81), boosters
  (+0x1178/+0x1180 doubles, +0x1188/+0x118C float mults = 1.0 default), ferris (+0x898),
  token-list heads (+0x818 primary, +0x858 secondary) — ALL verified live & UNCHANGED.
- ✅ Materials (pins+0x3B4=678, buttons+0x3C8=677, twine+0x3DC=681, ribbons+0x3F0=678,
  bows+0x404=681) all valid Container20. **Entire PlayerManager struct layout is stable;
  only RVA_PLAYER_MANAGER moved.**
- ⏳ find-a-pair state offsets (+0x3A4/+0x3A8/+0x3B8/+0x3D0): verify when minigame active.

## Catalog (user request)
- ✅ Store record layout UNCHANGED from 11.4.2a: stride 0x158, cat@+0x08==0x39, id@+0x18→+8,
  SortPrice@+0x50, currency@+0x60, price@+0x90, xml_curr@+0x108, b125@+0x125, b126@+0x126,
  zones@+0x38/+0x40. Only RVA_SHOP_CONTROLLER moved. store.py needs no layout change.
- ✅ Catalog regenerated from live RAM: **2418 ponies** (2419 cat==0x39, 1 empty id).
  Written to `suite/data/ponies_catalog.json` (game_version 11.5.0).
- ✅ 38 NEW ponies vs old 2381 (match screenshot): Ringmaster/First Folio/Phony Pharaoh/
  Sweetcream Scoops/Ordinary Mane-iac/Hum Drum Spike/Sneaky Pete/Steel Buns/5x Mane-iac
  Henchpony/E.W.E. Referee/Derby set/Edgy set. 1 removed: Queen_Cleopatrot.
- ⏳ Images: 38 new portraits needed. Existing 2380 are square icons in assets_part*.zip.
  Game `.ark` extraction investigated (user chose this for style match):
    - Format: 16-byte header + zstd frames (each = one PVR texture) + ENCRYPTED/hashed TOC.
    - PVR frames decode cleanly (e.g. 256×256 RGBA8888 → PNG trivially). Decode half works.
    - BLOCKER: TOC has no plaintext filenames (hashed); 6 archives (up to 1.4GB), portrait
      icons not found by name in any; inline strings are material defs, not portrait names.
    - Full game extraction = crack hashed-TOC naming (needs exe loader code) + locate portrait
      archive + decode + match 38 by hash. Large/uncertain. Disproportionate for 38 thumbnails.
    - Options: (A) deep TOC-crack via exe code; (B) all-the-ponies.com renders; (C) placeholders
      now + revisit. Portraits block nothing else — core offset work proceeds regardless.
