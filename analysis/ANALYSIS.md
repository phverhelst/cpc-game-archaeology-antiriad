# First pass: from the disk image to a map of the game

The release studied is `The_Sacred_Armour_of_Antiriad__2013-10-17__ENGLISH__CNGSOFT.dsk`, a tape-to-disk conversion made by CNGSoft in 2013 (see `checksums.sha256`). There is no BASIC in the game: it is written entirely in Z80 assembly, and the first task was to get it out of its compression.

## The CNGSoft loader

The disk holds a single file, `ANTIRIDE.BAS` (30 647 bytes). It is a one-line dummy BASIC program, `47195 CALL &190 ' "CNG LZ5 20131017"`, followed by machine code compressed with CNGSoft's LZ5 compressor. Run in the Z80 simulator with firmware calls intercepted (`extract.py`, using `cpcarch.loader`), the loader works in six steps:

1. It sets 10 inks and the border, then selects mode 0. Its colour table is written in ASCII letters (`@@`, `AA`, `ZZ`…), which the firmware brings back to 0-26 with an AND &1F.
2. It programs the CRTC for an enlarged screen (R1=48, R2=50, R6=34, R7=35, i.e. 96 bytes by 272 lines). It fills the screen with a maze, lays the CNGSoft logo over it and shows it for three seconds.
3. It blanks the screen, loads 16 inks, decompresses the loading screen (mode 2) and returns the CRTC to the standard format. The picture is revealed by a falling, bouncing curtain, obtained by changing colours during the frame, synchronised with VSYNC on port &F5, bit 0.
4. It waits for the space bar (`KM WAIT KEY`).
5. With the screen blanked (R6=0), it decompresses two blocks (down to &ACFF, then &FFFF), then restores R6=25.
6. It writes an `LDIR / RET` routine at &0030 and replaces the return address on the stack with **&5400**. It then copies 41 KB (&A300 bytes) down to &0200. This copy overwrites the loader itself, hence the execution from &0030. The `RET` starts the game.

Steps 2 and 3 are modelled, verified and rendered in `intro/INTRO.md`. None of this loader is Palace Software's work.

## Game start-up (&5400)

The game first writes 0 to port &FAFE, stopping the tape or disk motor. It then puts the screen at &C000, selects mode 0 with both ROMs disabled, and installs `JP &6EF2` at &0038. From that point the firmware is abandoned. Last, it sets the stack at &C000 and loads 16 hardware colours from the table at &8DF3.

`python3 analysis/disassemble.py` writes a recursive disassembly to `build/antiriad.asm`, starting from &5400, the interrupt handler &6EF2 and the keyboard routine &7923. It reaches about 8.3 KB of code and 124 called routines. `python3 analysis/screens.py` renders the title screen and the first room, each display line with the palette and mode of its interrupt slot.

## Hardware tricks

**A screen in two modes.** The interrupt handler runs six times per frame, and its counter at &B49A is resynchronised on VSYNC. At interrupt 0 it loads inks 1-3 of the play area (&8DF4) and selects mode 0 (16 colours). At interrupt 4 it loads inks 1-3 of the panel (&8E09) and selects mode 1 (4 colours, double horizontal resolution). The jungle and the armour's panel therefore have neither the same palette nor the same resolution.

**A minimal keyboard.** Only two lines of the keyboard matrix are read (&7923). Line 9 (joystick) is stored inverted at &7A4C, and line 8 at &7A4D, where the Q key (bit 3) returns to the title screen.

**Sound.** The sound driver sends 11 AY-3-8912 registers from a copy at &7A50, through the routine at &78F2. A table of note periods starts at &7974. See `sound/SOUND.md`.

## Memory map

| Area | Contents |
|---|---|
| &0000-&003F | vectors (&0030 the loader's LDIR, &0038 JP &6EF2) |
| &0200-&53FF | data (about 20 KB: graphics and rooms) |
| &5400-&7973 | code (about 8.3 KB reached by the disassembly, 124 called routines) |
| &7974-&7A4F | note table; keyboard buffer &7A4C-&7A4D |
| &7A50-… | AY registers, then data |
| &8DF3-&8E1F | palettes (full, play area, panel) |
| &A0CB-&A4A0 | messages and credits (a second copy at &A8CB, left over by the copy) |
| &B400-&B5FF | game variables (object records, counters, energy, radiation…) |
| &C000-&FFFF | screen |

The messages shown in the panel run from status reports (GRAVITY PREVENTS TAKEOFF, DANGER SUIT ENERGY LOW) to the final countdown and the victory message. They can be read in `build/antiriad_5400.bin` from &A0CB.
