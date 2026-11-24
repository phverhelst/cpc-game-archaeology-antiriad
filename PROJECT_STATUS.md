# Project status

This document summarises what has been established about the CPC version of *The Sacred Armour of Antiriad*, for whoever resumes or reviews the work. It is dated November 2026. Details and verification figures are in each folder's document.

## From the disk to the game

The disk image holds one file, `ANTIRIDE.BAS`, a one-line dummy BASIC program hiding a compressed loader (CNGSoft's LZ5). Run in the Z80 simulator with the firmware intercepted, the loader decompresses the game, copies 41 KB down to &0200 from a routine it writes at &0030, and jumps to &5400. The memory at that moment is the starting point of everything else (`build/antiriad_5400.bin`). The game abandons the firmware at once: it installs its own interrupt handler, reads only two lines of the keyboard matrix and drives the AY-3-8912 directly (`analysis/ANALYSIS.md`).

## Notable findings

**A screen in two modes.** The interrupt handler, called six times per frame and resynchronised on vertical sync, puts the play area in mode 0 (16 colours) and the armour's panel in mode 1 (4 colours, double horizontal resolution), each with its own palette.

**Data-driven movement.** Tal is object 0 of a table of eight 19-byte records at &B400. The joystick is reduced to six classes, a transition table gives the next state, and animation scripts complete the whole. A single speed table serves the jump, read one way to rise and the other to fall. The logic only sets direction bits and speeds; the animator shared by all objects does the moving. Several gaps between likely intent and code explain the stiffness of the movement: the last rising step is applied downwards, a jump launched against a wall is cancelled, landing locks Tal for 7 turns, turning round must go through a front-facing pose, and the rate varies from 14 to 19 turns per second with the number of objects on screen (`movement/TAL_MOVEMENT.md`).

**The armour.** Vertical movement goes through a fifteen-notch throttle that returns to neutral by itself. Horizontal speed is fixed, with at most a 6-turn slide. The armour bounces on contact (throttle reflected, direction reversed against a wall). A bug in the code makes the throttle's sound overwrite IX, losing a speed update (`movement/ARMOUR_MOVEMENT.md`).

**Enemies without scenery.** Each object follows a script of 4-byte steps. No collision with the scenery is ever tested for enemies. Of 244 objects placed:

- 51 do not move;
- 125 follow closed patrols that return exactly to their starting point;
- 57 chase Tal in a straight line, with the target recomputed every turn;
- 11 are falling drops.

An enemy dies when it touches Tal and costs him 4 to 12 points out of 31. It takes 1 to 4 stones depending on the creature. Obstacles are invulnerable and wound at every contact. Nothing can be collected before the first entry into the armour, and rooms &00 and &01 kill Tal on entry without the particle negator (`enemies/ENEMIES.md`).

**The panel is screen memory.** Gauges catch up with the real values one notch per turn. The central screen's "noise" is the game's own code copied onto the screen, 230 bytes per turn. Some logic runs in real time rather than in game turns: every two seconds, life regenerates in the armour and radiation wears Tal down on foot (`enemies/PANEL_AND_ENDING.md`).

**The starting room is random.** The game reads bit 0 of the Z80's R register (&58DF), which depends on the exact moment the player pressed fire. Tal starts in room &38, at the far left of the bottom of the map, or in &44, at the far right. A deterministic emulator always drew &44, and the other branch was found only by reading the code.

**Sound in software.** The driver, called 100 times per second, interprets sounds coded as bytes, with software envelopes for volume, pitch and noise. Fewer than 2 KB hold nearly two minutes of three-part title music. The driver has three oddities: a tempo truncation (155 played as 187.5), a "channel 3" that does not exist and silently erases three instruments, and an end of channel obtained by starting a sound beyond the table (`sound/SOUND.md`).

**The ending shakes the monitor.** CRTC register 8 is set to 1 (interlace) while 16 384 random draws erase the play area over about ten seconds. The opening of the studied copy, a bouncing curtain timed to the microsecond, is the work of the 2013 conversion, not of Palace (`intro/INTRO.md`).

## Verification at a glance

| Model | Against | Coverage |
|---|---|---|
| `movement/tal.py` | the game | 11 scenarios, 592 turns |
| `movement/armure.py` | the game | 9 scenarios, 392 turns |
| `enemies/monde.py` | the game | 24 scenarios, 5 262 turns, death, firing, complete ending |
| `sound/pilote.py` | the game | 14 000 title music calls, 5 760 sound effect calls |
| `intro/rideau.py` | the loader | 5 787 Gate Array writes, 175 frames |
| `sandbox/*.js` | the Python models | 80 000, 48 000 and 4 477 cases |

Each comparison is made step by step (the model restarts from the game's state at every call) and, where it makes sense, continuously (the model runs alone).

## What remains

- **Graphics data.** Decode the room and sprite formats in &0200-&53FF directly, rather than capturing what the drawing routine produces.
- **The armour's reach.** Measure which rooms the armour can reach (on foot, 44 rooms are reachable from &44).
- **The original release.** Study an original tape release, compare its game code with this one byte for byte, and document its own loader.
- **The authors.** Research the rights holders and contact the authors (`CONTACTS.md`).
- **Translation.** Translate the code's identifiers and comments, and the sandboxes' texts, into English.
- **Development history.** Document from sources how the game was developed in 1986. A reconstruction from the code is in `cpc-game-archaeology/DEVELOPMENT_PLAN.md`.
