# Spyro's Adventure difficulty mod

Adds difficulty settings to **Skylanders: Spyro's Adventure** (Wii, PAL, `SSPP52`
Rev 3) running in Dolphin. A Gecko code scales the damage your Skylander takes, and
a small Windows app lets you pick the difficulty while you play.

The presets copy the enemy damage scale of **Skylanders Imaginators**' own
difficulties, read from its game files (`CGlobalTuningData`):

| Preset     | Damage taken | Chompy bite (normally 11) |
|------------|--------------|---------------------------|
| Invincible | 0×           | 0                         |
| Easy       | 0.4×         | 4                         |
| Medium     | 1×           | 11                        |
| Hard       | 1.8×         | 19                        |
| Nightmare  | 3.5×         | 38                        |
| One-shot   | 1024×        | all HP                    |

The app also has a custom slider (0–8×), a live HP bar, **Refill HP**, a
**Regeneration** option (1% of max HP per second), hit statistics and "always on
top". It remembers your last settings.

## Install

1. In Dolphin, right-click the game → **Properties** → **Gecko Codes** → **Add New
   Code**, name it `Damage multiplier`, paste the code below and enable it. Make sure
   cheats are enabled (**Config → General → Enable Cheats**).

   ```
   C2034784 0000000F
   7D4802A6 48000015
   53534132 00000100
   12FC5B28 03400003
   7D6802A6 7D4803A6
   81830008 814B0008
   7C0C5000 40820044
   81830004 814B000C
   7C0C5000 40820034
   81830020 7C006000
   40800028 814B0004
   7D606050 7D6B51D6
   7D6B4670 7C0B6050
   7C006040 4081000C
   38000000 60000000
   90030020 00000000
   ```

   On its own the code plays at 1× (normal). The app changes the multiplier.

2. Install Python 3 and the requirements, then start the app while the game runs:

   ```
   pip install -r requirements.txt
   python ssa_difficulty.py
   ```

Start the game fresh after enabling or updating the code. Dolphin save states
contain the code that was loaded when they were made, so loading an older state
brings an older code back (the app then shows "Old Gecko code loaded").

## Known limits

- **The white damage numbers show the normal damage.** The game reads both the
  number and the HP loss straight from the attacking enemy's own damage value, and
  those values have different IDs for every enemy type.
- **Only damage taken is scaled.** Enemy health, food healing and rewards are not:
  the variable slot that holds enemy HP is shared with counters and timers, so
  touching it breaks the game.
- Only tested on the PAL Rev 3 disc.

## How it works

The game runs its gameplay through level scripts. Every script integer is an object
(vtable `0x80485f0c`, ID at `+8`, value at `+0x20`), and all of them are written
through one setter at `0x80034780`. The Gecko code hooks the store at `0x80034784`.

The Skylander's HP lives in three script integers. Only ID `0x12fc5b28` is the real
one; `0x12fcc7dc` (HUD) and `0x12fc5244` (stats, reloaded after the pause menu) copy
it. The same ID is also used by around 38 other slots per level (enemy HP, counters,
timers), so the code also checks the variable's flag word. Its low bits count
references: the player's HP reads `0x03400002` at rest and `0x03400003` while a
script writes it, while the other slots read `0x03400001`. When the flag and ID
match and the new value is lower, the loss is multiplied by `multiplier / 256`.

The multiplier sits inside the code, right after the marker `SSA2`, so the app can
find and change it in Dolphin's memory while the game runs.

## Files

| File | What it is |
|------|------------|
| `ssa_difficulty.py` | The difficulty app (tkinter). `python ssa_difficulty.py test` runs its self-check. |
| `make_gecko.py` | Builds the Gecko code and prints its disassembly (needs `capstone`). |
| `dolmem.py` | Reads, writes and scans Dolphin's emulated Wii memory. |
| `iga.py` | Extracts files from Imaginators' IGA v11 `.pak` archives. |
| `ppcdis.py` | Disassembles the game's `main.dol` (extract it yourself into `sys/`). |
| `kbinput.py`, `boot.ps1`, `dismiss.ps1`, `snap.sh`, `shot.ps1`, `addbp.py`, `hittest.py`, `shottest.py`, `trydmg.py` | Test helpers used during development: keyboard control of Dolphin, screenshots, debugger breakpoints and damage measurements. |
