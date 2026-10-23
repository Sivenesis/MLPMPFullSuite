# MLPMP Full Suite

A lightweight trainer and memory editor for *My Little Pony: Magic Princess* on Windows (64-bit).

It changes values in the game while it is running. It does not touch your save files.

---

## What It Can Do

- **Level and XP** - Set your level and experience. The right numbers are worked out for you.
- **Currency** - Edit Bits, Gems, Hearts, and Friendship Hearts.
- **Element Shards** - Edit all six shards: Loyalty, Kindness, Honesty, Generosity, Laughter, and Magic.
- **Profile Unlocks** - Unlock all profile items in one click (avatars, frames, backgrounds, cutie marks, and more).
- **Ponies and Costumes** - Unlock all costume sets and pieces.
- **Crafting Materials** - Set how many Pins, Buttons, Twine, Ribbons, and Bows you have.
- **Group Quest Keys** - Set your bonus keys for Group Quest reward chests.
- **Boosters** - Change the timer and multiplier of active XP and Bits boosters.
- **Find a Pair Minigame** - Freeze the timer and the score multiplier. A "deny decrease" mode lets the multiplier go up but never down.
- **Ferris Wheel** - Skip the 6-hour wait and spin again right away.
- **Fortune Shop Refresh** - Keep the 50-gem refresh button always ready so you can re-roll as often as you like.
- **Store Catalog** - Search the full list of 2,418 characters, find the exact ponies you want, and switch on only those ones to buy in the in-game shop. Unlock a single pony or a hundred - it is completely up to you.

---

## How to Use

### To Start

1. Open the game first (*My Little Pony: Magic Princess*).
2. Double-click **`start.bat`**.
3. The Suite opens in your web browser at `http://127.0.0.1:8080/`.
4. Click the green **Attach to Process** button at the top. It connects to the running game.

That's it. You can now use any of the tools above.

### To Close

1. Click the red **close (X)** button in the top-right corner of the Suite.
2. The Suite disconnects from the game, undoes any temporary changes, and shuts itself down.
3. When you see the confirmation message, you can close the browser tab.

---

## Good to Know

- **Your save files are safe.** The Suite only reads and writes the game's live memory while it is running. It never opens, edits, or deletes any of your game files or save data.
- **Nothing happens on its own.** The Suite does not connect to the game by itself, and it never changes anything until you click a button. You are always in control.

---

## Technical Overview

*This section is for advanced users and developers. You do not need to read it to use the Suite.*

### Non-Invasive Live RAM Architecture

The Suite is strictly non-invasive. It works only on the running game's virtual process memory (`MyLittlePony_x64.exe`) using standard Windows memory APIs (`ReadProcessMemory` and `WriteProcessMemory`).

- **Zero file modification**: It never opens, edits, parses, or writes to local game files, save data, XML files, or application containers.
- **Strict user intent**: It never attaches automatically and never applies a memory patch without an explicit click.

### Tab 1: Profile Editor

- **Progression**: Edit level and XP. A built-in XP table parser calculates the exact thresholds for your target level.
- **Currency and Shards**: Edit Bits, Gems, Hearts, Friendship Hearts, and Element Shards. Containers are encrypted using Gameloft's 20-byte container cipher with preserved key entropy.
- **Ponies and Crafting**: Toggle ownership across all costume sets and pieces, and set crafting material quantities.
- **Group Quests and Boosters**: Set bonus keys for reward chests and extend or boost active multipliers.
- **Minigames**: Lock the Find a Pair timer or score multiplier (including "deny decrease" mode), and reset the Ferris Wheel timer.

### Tab 2: Fortune Shop and Store Tweaks

- **Continuous Refresh**: Neutralizes the daily paid-refresh counter so the in-game 50-gem refresh button stays available. Royal Club is never touched. Optional "Re-roll Roster Now" and "Force Rare odds" controls are included.
- **Store Editor and Catalog**: Browse an offline, searchable database of 2,418 characters across Ponyville, Canterlot, Sweet Apple Acres, Crystal Empire, and Klugetown. Apply store rotation patches to make unlisted and event-exclusive ponies buyable in the shop.

### Modularity and Maintainability

Core Win32 memory routines (`core/memory.py`), memory mappings (`core/offsets.py`), and mechanic handlers (`mechanics/`) are kept separate from the server and interface. When the game updates, maintainers can adapt the Suite by updating the centralized offset definitions without touching frontend or server code.

### Reverse-Engineering and Research Documentation

For full technical documentation - internal memory structures, Gameloft container ciphers (`Container20`, `Token16`), singleton RVAs, Scaleform ownership gates, store rotation patches, and update-adaptation guides - see [RESEARCH.md](RESEARCH.md).

---

## Legal Notice

The developer of this Suite claims no rights, ownership, or copyright over any game assets, character designs, names, logos, trademarks, or intellectual property belonging to Gameloft, Hasbro, or their respective right owners. *My Little Pony: Magic Princess* and all associated characters, titles, and media are trademarks and registered copyrights of Hasbro, Inc. and Gameloft S.E. This Suite is an independent, non-commercial open-source interoperability tool developed strictly for educational analysis, personal backup, and research purposes.

---

## Disclaimer ("AS IS")

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. USE AT YOUR OWN RISK.

---

## AI Disclaimer

Portions of the architecture, memory reverse-engineering analysis, cryptographic algorithms, REST handlers, and user interface for this Suite were designed, refactored, and implemented with the assistance of advanced Artificial Intelligence (AI) pair programming agents. All generated code has been validated against active process memory for correctness, portability, safety, and reliability.
