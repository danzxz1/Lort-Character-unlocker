<div align="center">

[🇷🇺 Русский](README.ru.md) · **🇬🇧 English**

# 🗝️ LORT Character Unlocker

**Unlock every hero in LORT with a couple of clicks — no more hunting for them in the world.**

A window with hero portraits, an "Unlock" button right under each one.
Dependency-free Python: Windows · Linux (Steam/Proton) · macOS

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

</div>

---

## ✨ Features

- 🖼️ **GUI with portraits** — one card per hero: portrait, status (unlocked / locked) and an "Unlock" button right below it
- 🌐 **English / Русский interface** — switch with the 🌐 button (English by default, your choice is remembered)
- 🎯 **Pick your hero** — unlock only the ones you want, or everyone at once
- 🔒 **Re-lock** — an unlocked hero gets a "Lock" button that closes them again
- 🛡️ **Automatic backup** before every write, plus a "Restore" button
- 🚦 **Safety check** — refuses to write while the game is running (it would overwrite the save on exit)
- 🔁 **Idempotent** — clicking again never creates duplicates
- 🌍 **Finds your saves automatically** on Windows and Linux/Proton, with manual folder selection
- ⌨️ **Command-line mode** for terminal fans (`--dry-run`, `--list`, `--restore`)

## 🚀 Quick start

1. **Close the game** and wait until Steam finishes syncing.
2. Download the repository (`Code → Download ZIP`) and unpack it.
3. Start the window:

```bash
python lort_gui.py
```

4. Pick a profile (the one with progress is selected by default) and click **"Unlock"**
   under the hero you want, or **"Unlock all"**.

> On Linux the GUI needs `tkinter`: `sudo apt install python3-tk` (Debian/Ubuntu).

### 🖼️ Portraits

Game assets are **not** distributed with this repository. The tool extracts the portraits
from your own copy of the game and stores them in `portraits/`:

1. Download [retoc](https://github.com/trumank/retoc/releases) (an Unreal Engine container unpacker).
2. Click **"Load portraits"** in the window and point it to `retoc`, or run in a terminal:

```bash
python extract_portraits.py --retoc path/to/retoc [--game-dir "<LORT folder>"]
```

The GUI also works without portraits — it shows coloured placeholders with the class letter.

## 🧙 Heroes

| Hero | Class | How the game unlocks it | What the tool adds |
|---|---|---|---|
| Astrid Glitzgore | Warrior | available from the start | — |
| Cliff Bowman | Ranger | available from the start | — |
| Bernie Blazington | Wizard | `Challenge_MeetBoss_Ranger` | challenge |
| Croaks Malone | Rogue | `Challenge_FindTheRogue` | challenge + `Weapon_Blinkblades` |
| Xavier | Monk | `Challenge_FindTheMonk` | challenge + `Weapon_DragonFists` |
| Stacy of Chillendell | IceMage | `Challenge_Die` | challenge + `Weapon_IceStaff` |
| Marcus T. Fury | Paladin | `Challenge_Paladin` | challenge |

## ⌨️ Command-line mode

```bash
python lort_unlocker.py                         # interactive menu
python lort_unlocker.py --list                  # who is unlocked right now
python lort_unlocker.py -H monk -H paladin      # specific heroes
python lort_unlocker.py -H monk --lock          # lock a hero back
python lort_unlocker.py --all -p Profile1.sav   # everyone, in a chosen profile
python lort_unlocker.py --all --dry-run         # only show what would change
python lort_unlocker.py --restore               # roll back from the latest backup
python lort_unlocker.py -s /path/to/SaveGames   # custom save folder
```

| Option | Description |
|---|---|
| `-H`, `--hero` | `monk`, `rogue`, `paladin`, `wizard`, `icemage` (repeatable) |
| `-a`, `--all` | all heroes |
| `-p`, `--profile` | profile file, e.g. `Profile1.sav` |
| `-s`, `--save-dir` | `SaveGames` folder if auto-detection fails |
| `-L`, `--lock` | the opposite: lock the selected heroes |
| `-l`, `--list` | show status and exit |
| `-n`, `--dry-run` | write nothing |
| `--restore` | roll back from the latest backup |
| `--force` | skip the "game is closed" check |

## 📁 Save locations

| System | Path |
|---|---|
| Windows | `%LOCALAPPDATA%\LORT\Saved\SaveGames\<SteamID>\` |
| Linux (Proton) | `~/.local/share/Steam/steamapps/compatdata/<appid>/pfx/drive_c/users/steamuser/AppData/Local/LORT/Saved/SaveGames/` |

Only `Profile<N>.sav` files are edited. A copy named `Profile1.sav.bak-<date-time>`
is created next to the modified file.

## ⚙️ How it works

A save file is plain JSON. A hero counts as unlocked once the GUID of their "class"
challenge is present in `completedChallenges`. For some heroes the game also grants a
starter weapon in `unlocks.items`; the tool adds it with the same GUID. The rest of the
profile is left untouched and the file formatting is preserved.

## ⚠️ Important

- **Steam Cloud** may overwrite the edited save with the cloud copy. Disable sync for
  LORT while editing, or start the game only after Steam has finished syncing.
- The challenge → hero mapping was derived from the game data and verified on a copy of
  a save file, not inside the game itself. If something looks wrong, click "Restore"
  (or use `--restore`) and open an issue.
- **Steam achievements are not granted.** The tool only edits the save file, while the
  game sends achievements to Steam itself when a challenge is completed during a run,
  so unlocking via this tool most likely won't count (not verified in-game).
- Intended for **your own saves** only. The save format may change after game updates.
- Unofficial project, not affiliated with the LORT developers.

## 📄 License

[MIT](LICENSE) — covers the code of this tool. LORT and its assets belong to their respective owners.
