# MLPMP Full Suite

A lightweight, non-invasive, live RAM memory editor and trainer Suite for *My Little Pony: Magic Princess* on Windows x64.

---

## Features

- **Level & XP Editor**: Modify player level and experience points with automated threshold calculation and level-cap handling.
- **Currency Editor**: Real-time balance editing for Bits, Gems, Hearts, and Friendship Hearts.
- **Element Shards Editor**: Direct editing for all six Element Shards (Loyalty, Kindness, Honesty, Generosity, Laughter, Magic).
- **Profile Customizations**: One-click live unlock for all 743 customization items (507 Avatars, 95 Avatar Frames, 50 Backgrounds, 48 Background Frames, 43 Cutie Marks).
- **Pony Editor (Costumes & Sets)**: Unlock all pony costume sets and individual pieces.
- **Crafting Materials**: Set quantities for all materials (Pins, Buttons, Twine, Ribbons, Bows).
- **Group Quests Keys**: Modify available bonus keys for Group Quest rewards chests.
- **Active Boosters**: Adjust duration timers and multiplier ratios for active XP and Bits boosters.
- **Find a Pair Minigame**: Freeze game timer and score multiplier, including a 'deny decrease' mode allowing multipliers to grow naturally while ignoring drops.
- **Ferris Wheel Cooldown**: Instant bypass of the 6-hour wait timer for immediate free spin.
- **Fortune Shop Refresh**: Instant roster re-roll with zero gem cost, 24-hour cooldown bypass.
- **Store Editor & Catalog**: Searchable 2,381-character catalog, combined with store rotation patches for enabling purchases.

---

## How to Launch and Close the Suite

### Launching the Suite
1. Launch the game (*My Little Pony: Magic Princess*).
2. Double-click `start.bat` (or execute `python run.py` in your terminal).
3. The Suite interface will open automatically in your default web browser at `http://127.0.0.1:8080/`.
4. Click the green **"Attach to Process"** button in the header bar. The Suite will connect to the live game RAM.

### Closing the Suite
1. Click the red **[✕]** button in the top-right corner of the Suite interface.
2. The Suite will safely detach from the game RAM, revert any temporary memory patches, and terminate the background server process.
3. When the confirmation prompt appears, you may safely close your browser tab.

---

## Detailed Overview

### Non-Invasive Live RAM Architecture
The Suite is built from the ground up to be strictly non-invasive. It operates exclusively on live virtual process memory (`MyLittlePony_x64.exe`) using standard Windows memory management APIs (`ReadProcessMemory` and `WriteProcessMemory`). 
- **Zero File Modification**: The Suite **never** opens, edits, parses, or writes to your local game files, save data, XML files, or application containers.
- **Strict User Intent**: The Suite **never** attaches to the game automatically upon launch, nor does it apply any memory tweaks without explicit user interaction. Every patch, write, or toggle executes only when you click the corresponding control.

### Tab 1: Profile Editor
The Profile Editor provides comprehensive management over player progression and inventory:
- **Progression Management**: Edit your current player level and XP. The Suite includes an integrated XP table parser that automatically calculates and applies the exact XP thresholds required for your target level.
- **Currency & Shards**: Adjust your core economy (Bits, Gems, Hearts), social currency (Friendship Hearts), and Element Shards. All containers are encrypted using Gameloft's 20-byte container cipher with preserved key entropy.
- **Pony Editor & Crafting**: Toggle ownership hooks across all costume sets and pieces in the Fashion Page, while managing crafting materials (Pins, Buttons, Twine, Ribbons, Bows).
- **Group Quests & Boosters**: Set bonus keys for quest reward chests, and extend or increase active multiplier boosters.
- **Minigames**: Take control of the Find a Pair minigame by locking the timer or setting score multipliers. The unique 'Deny Decreasing' mode lets your multiplier climb naturally while preventing any decreases upon mismatches. Instantly reset the Ferris Wheel timer for back-to-back spins.

### Tab 2: Fortune Shop and Store Tweaks
The Fortune Shop and Store Tweaks tab is dedicated to character acquisition and catalog management:
- **Fortune Shop Roster Refresh**: A clean, singular refresh action that clears the 24-hour cooldown. This action will force apply Royal Club status in memory, as required by the game engine for refresh functionality.
- **Store Editor & Catalog**: Browse an offline, searchable database of 2,381 characters categorized across Ponyville, Canterlot, Sweet Apple Acres, Crystal Empire, and Klugetown. Filter by name, ID or town. Apply store rotation patches to make unlisted and event-exclusive ponies buyable directly in the in-game shop.

### Modularity & Maintainability
The Suite features a decoupled architecture where core Win32 memory routines (`core/memory.py`), memory mappings (`core/offsets.py`), and individual mechanic handlers (`mechanics/`) are isolated from the server and browser interface. When new game updates are released, maintainers and AI agents can adapt the Suite simply by updating centralized offset definitions without touching frontend or server code.

### Reverse-Engineering & Research Documentation
For comprehensive technical documentation detailing internal memory structures, Gameloft container ciphers (`Container20`, `Token16`), singleton RVAs, Scaleform ownership gates, store rotation patches, and adaptation guides for future game updates, please refer to [RESEARCH.md](RESEARCH.md).

---

## Legal Notice

The developer of this Suite claims no rights, ownership, or copyright over any game assets, character designs, names, logos, trademarks, or intellectual property belonging to Gameloft, Hasbro, or their respective right owners. *My Little Pony: Magic Princess* and all associated characters, titles, and media are trademarks and registered copyrights of Hasbro, Inc. and Gameloft S.E. This Suite is an independent, non-commercial open-source interoperability tool developed strictly for educational analysis, personal backup, and research purposes.

---

## Disclaimer ("AS IS")

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. USE AT YOUR OWN RISK.

---

## AI Disclaimer

Portions of the architecture, memory reverse-engineering analysis, cryptographic algorithms, REST handlers, and user interface for this Suite were designed, refactored, and implemented with the assistance of advanced Artificial Intelligence (AI) pair programming agents. All generated code has been validated against active process memory for correctness, portability, safety, and reliability.
