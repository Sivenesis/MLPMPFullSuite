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

## Known follow-ups
- Costume "unlock all / hidden costumes" is disabled for 11.5.0 — the costume subsystem
  changed substantially and needs re-derivation (safely no-ops in the meantime).
- A few niche store hooks (ACTION_POSSIBLE detour, BUYABILITY/BUY_HOUSE best-guesses) are
  disabled; store rotation + purchase work without them.
