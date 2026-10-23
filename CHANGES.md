# Changes in v2.2.2

## Event Currency Editor Support (Arena / Time-Limited Story)
- Added full support for Time-Limited Story (TLS) / Arena event currency ("Magic Coins" / Event Coins) and Event Basket accumulator.
- **Cheat Engine Table (`MLPMPFullSuite_v11.5.0a.CT`)**:
  - Added Cheat Entries `ID 3205` ("Event Currency / Magic Coins") and `ID 3206` ("Event Currency Basket") with dynamic pointer paths (`[ [ MyLittlePony_x64.exe + 0x1A89BC0 ] + 0x240 ] + 0xD4` / `+ 0xE8`).
  - Added Lua helper functions `SetEventCurrency` and `SetEventCurrencyBasket` with real-time `Container20` encryption (`ROL32-5`), automatically hooked into `LIVE_HANDLERS`.
- **WebGUI Suite**:
  - Added Event Coins and Event Basket input fields to the Currency Editor panel in `index.html`.
  - Added real-time live synchronization, dirty-state preservation, and max-value preset population in `app.js`.
  - Integrated `event_currency` and `event_currency_basket` into `CurrencyMechanic` backend (`currency.py` and `base.py`).

# Changes in v2.2.0

Updated for game build **11.5.0** (package 11.5.0.0).

## Game-version re-offset (11.4.2a → 11.5.0)
- Re-derived every module RVA against the live 11.5.0 client. Struct offsets and the
  `Container20` cipher (ROR32-5) are unchanged from 11.4.2a — only module RVAs moved.
- Updated singletons (PlayerManager, LevelManager, FortuneShop, ShopController, etc.),
  the version-string check, profile/costume/store code-patch sites, and fortune checks.
- Verified live: attach + version check, currency, level/XP, shards, materials, boosters,
  royal club, ferris, tokens, store catalog, profile unlock, store rotation + purchase.

## Catalog
- Catalog regenerated from live RAM: **2,418 ponies** (was 2,381), including **38 new**
  11.5.0 characters (the Edgy set, Derby set, Mane-iac Henchponies, Ringmaster Pony, etc.).
- New portrait icons bundled in `web/assets_part4.zip`.

## Fortune Shop — rewritten
- Replaced the legacy one-shot refresh (which force-activated Royal Club and only worked
  once or twice) with a **Continuous 50-gem Refresh** toggle: keeps the in-game paid refresh
  button permanently available for unlimited re-rolls, **without ever touching Royal Club**.
  Implemented as a single in-place code patch (neutralizes the daily paid-refresh counter).

## Costume unlock
- **Unlock All Costumes & Sets** re-ported to 11.5.0 — 9 hooks forced true:
  PonyPartsManager::IsPartOwned (`0x65B360`), CostumeSet::IsComplete (`0x9573B0`), and 7
  FashionPage visibility gates (`0x2FBD05`…`0x2FC173`). Reveals hidden/event costume sets and
  lets them be put on. (The earlier port mis-identified IsPartOwned; corrected here.)

## WebUI Input Safeguards
- Fixed currency editor input overwriting: background memory polling (every 2.5s) no longer overwrites user input while editing or after staging max safe values.
- Staged/dirty input values are preserved until user clicks Apply or Reset.
- Added visual modified indicator badge (`[N] MODIFIED`), field highlight borders, a "Reset to Live" action button, and Enter key application support.
- Extended the same dirty-state protection to Player Level/XP, Crafting Materials, Boosters, and Group Quests keys.

## Known follow-ups
- A few niche store hooks (ACTION_POSSIBLE detour, BUYABILITY/BUY_HOUSE best-guesses) are
  disabled; store rotation + purchase work without them.
