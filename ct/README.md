# MLPMP Full Suite - Cheat Engine Table (.CT)
**Target Game Client**: *My Little Pony: Magic Princess* (Windows 64-bit / Build `v11.5.0a`)  
**Target Executable**: `MyLittlePony_x64.exe`  
**Compatibility**: Cheat Engine 7.4+ (CheatEngineTableVersion 45)

---

## Overview

Updated Cheat Engine table for game client build **v11.5.0a** (Windows Store package `11.5.0.0`).
All values using Gameloft's encrypted 20-byte container and 16-byte token ciphers (`rol32`, `ror32`, dual-key XOR, and shadow verification) are seamlessly handled by an embedded Lua synchronization engine.

---

## Verified Offsets Summary (v11.5.0a)

### 1. Singletons
- **PlayerManager**: `MyLittlePony_x64.exe + 0x1A7E660`
- **LevelManager**: `MyLittlePony_x64.exe + 0x1A6F3C8`
- **StateManager**: `MyLittlePony_x64.exe + 0x1A6CA58`
- **FortuneShopManager**: `MyLittlePony_x64.exe + 0x1A7CA98` (Double Pointer)
- **ShopManager / Store Controller**: `MyLittlePony_x64.exe + 0x1A7FEC0`
- **UI Invalidate Cache**: `MyLittlePony_x64.exe + 0x1A83F20`

### 2. Profile Customization Hooks (Section 3)
- **Avatar Gate 1**: `0x5AE6E0`
- **Avatar Gate 2**: `0x5AE9BF`
- **Avatar Frame Gate**: `0x5AE94F`
- **Background Gate**: `0x5AE82F`
- **Background Frame Gate**: `0x5AE7BF`
- **Cutie Mark Gate**: `0x5AE89F`

### 3. Pony Editor & Costumes Hooks (Section 4)
- **IsPartOwned**: `0x65B360`
- **IsComplete**: `0x9573B0`
- **FashionPage Visibility Gates 1-7**: `0x2FBD05`, `0x2FBD62`, `0x2FBECE`, `0x2FBF3C`, `0x2FBFAA`, `0x2FC102`, `0x2FC173`

### 4. Store Rotation & Purchasing Hooks (Section 8)
- **Rotation Setter**: `0x12FDAD7`
- **Category Deque Builder**: `0x69F163`
- **Shelf Render Iterator**: `0x67B21F`
- **Buyability Enabler**: `0x680010`
- **Scaleform Flash Action Gate**: `0x368810` (Jump displacement to `0xC06500`: `E6 DC 89 00`)
- **Currency Type Resolver**: `0x6C88D0`
- **Dispatcher Frame Debounce**: `0x67C9F9`
- **Housing Space Allowance**: `0x67E076`
- **Town Store Isolation**: `0x6C88A0`

---

## How to Use

1. Launch *My Little Pony: Magic Princess*.
2. Open [`MLPMPFullSuite_v11.5.0a.CT`](file:///f:/Progs/VIBECODE/Google/Projects/MLPMP/ct/1150/MLPMPFullSuite_v11.5.0a.CT) in Cheat Engine.
3. Attach Cheat Engine to the running `MyLittlePony_x64.exe` process (`File -> Select Process -> MyLittlePony_x64.exe`).
4. Edit any live value directly by double-clicking its **Value** column, or activate toggles/scripts.
