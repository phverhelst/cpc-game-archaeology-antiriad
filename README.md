# The Sacred Armour of Antiriad (Palace Software, 1986), Amstrad CPC: verified reverse engineering

*The Sacred Armour of Antiriad* is an action and exploration game published by Palace Software in 1986 for the Amstrad CPC, the Commodore 64 and the ZX Spectrum, among others. It was programmed by Andrew Fitter, with plot and graphics by Daniel Malone and sound design by Richard Joseph. In North America, Epyx published it as *Rad Warrior*.

This repository explains how the Amstrad CPC version works, subsystem by subsystem, and proves each explanation by checking a model against the original code running in an emulator. It is the first study made with the protocol and tools of [`cpc-game-archaeology`](../cpc-game-archaeology), which you need alongside it.

**No game material is distributed here.** You need your own copy of the game. `extract.py` builds everything else from it, and `make_all.py` regenerates every product and runs every verification.

## Release studied

| File | SHA-256 |
|---|---|
| `The_Sacred_Armour_of_Antiriad__2013-10-17__ENGLISH__CNGSOFT.dsk` | `a186d22294ee2b9b5139f2e25b02584f41fc4302c5cc288fcc4f8dddad03f963` |

This is a tape-to-disk conversion made by CNGSoft in 2013. The game code proper (from &5400) is Palace's. The loader, the opening logo and the curtain that reveals the loading screen are CNGSoft's (see `intro/INTRO.md`). With another release, `extract.py` will report different hashes, and the addresses and figures in the documentation may not apply.

## Getting started

You need Python 3.9 or later and the toolkit. Install it from the `cpc-game-archaeology` folder, which also installs SkoolKit 10.2, NumPy, Pillow and SciPy:

    pip install -e ../cpc-game-archaeology

Then, in this repository:

    python3 extract.py path/to/your/copy.dsk   # build/: the game file and two memory images, hashes checked
    python3 make_all.py                         # generate everything (about 1 min), then verify everything (about 3 min)

Optional tools:

- `ffmpeg`, for the audio recordings and videos;
- `rsvg-convert`, for the engraved score;
- Node.js, for the checks of the JavaScript ports and for `rooms/accessibilite.js`.

## Findings

| Subject | Document | Verification against the game |
|---|---|---|
| Loader, start-up, memory map, hardware tricks | `analysis/ANALYSIS.md` | loader output identical to the reference image (SHA-256) |
| Tal on foot: state machine, jump, collisions | `movement/TAL_MOVEMENT.md` | 11 scenarios, 592 turns, step by step and continuous |
| Tal in the armour: throttle, momentum, bounces, parts, energy | `movement/ARMOUR_MOVEMENT.md` | 9 scenarios, 392 turns |
| The 69 rooms, their links and the map | `rooms/ROOMS.md` | captured with the game's own drawing routine |
| Enemies, obstacles, stone, damage, lives | `enemies/ENEMIES.md` | 24 scenarios, 5 262 turns, plus death, firing and the ending |
| The armour's panel, the two-second task, pulsar beam, end of the game | `enemies/PANEL_AND_ENDING.md` | panel compared byte by byte in screen memory |
| Sound driver, title music, sound effects, comparison with the C64 | `sound/SOUND.md` | 14 000 + 5 760 driver calls |
| Opening (CNGSoft loader) and the final implosion | `intro/INTRO.md` | 5 787 Gate Array writes of the curtain |
| Interactive sandboxes (JavaScript) | `sandbox/SANDBOX.md` | JavaScript against Python: 80 000, 48 000 and 4 477 cases |

`PROJECT_STATUS.md` summarises the findings and what remains. `CONTACTS.md` records the search for the authors and rights holders.

## About the code

The study was carried out in French, and the code keeps its French file names, identifiers and comments; the documentation is in English. Each model function carries the address of the Z80 routine it reproduces, which is the most reliable guide. The main file names translate as follows:

| French | English |
|---|---|
| `verif*.py` | verification harness |
| `monde` | world (all objects other than Tal) |
| `armure` | armour |
| `salle(s)` | room(s) |
| `ennemis` | enemies |
| `pilote` | (sound) driver |
| `partition`, `musique`, `gravure` | score, music, engraving |
| `ecouter` | listen (audio rendering) |
| `chargeur` | loader |
| `rideau` | curtain |
| `fin` | end |
| `construire*`, `gabarit*` | build, template (sandboxes) |
| `capturer` | capture |
| `extraire` | extract |
| `trajectoires` | trajectories |
| `accessibilite` | reachability |

Translating the code is a welcome contribution, provided `make_all.py verify` still passes.

## How this was made

The study was carried out in 2026 by Philippe Verhelst, directing an AI assistant (Claude, by Anthropic), which wrote most of the code and documentation. No claim was accepted without an automated comparison with the original code; the protocol is described in `cpc-game-archaeology/PROTOCOL.md`.

## Licence and credits

Game © Palace Software, 1986, and its current rights holders. Programming: Andrew Fitter. Plot and graphics: Daniel Malone. Sound design: Richard Joseph. Disk conversion: CNGSoft, 2013.

This study: code under the MIT licence (`LICENSE`), documentation under CC BY 4.0 (`LICENSE-docs.md`). Nothing here licenses any part of the game.
