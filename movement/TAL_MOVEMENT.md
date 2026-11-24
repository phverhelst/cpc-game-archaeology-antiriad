# Tal's movement on foot

This folder isolates and documents Tal's movement without the armour: walking, turning, crouching, throwing a stone, jumping, falling, stopping against a wall. It contains a dependency-free Python model (`tal.py`), the game's tables extracted from memory (`tables.py`, exported as `tal_tables.json`), a harness that checks the model against the real code (`verif.py`) and a trajectory calculation (`trajectoires.py`).

The model was checked against the original Z80 code running in the emulator. Over eleven scenarios, 592 game turns covering states 01 to 13, it reproduces Tal's object record exactly, field by field, at every turn. The comparison was made step by step (the model restarts from the real state at each turn) and continuously (the model keeps its own state from start to finish). Only two events are deliberately outside the model and reported as such: changing room and Tal's death.

## Where Tal lives in memory

The game manages eight animated objects in a table of 19-byte (&13) records starting at &B400. Tal is object 0. His record holds, among other things:

- **+3**: column X, in screen bytes (in mode 0 one byte holds two pixels);
- **+4**: line Y (line &32 is the first of the play area);
- **+7**: the direction bits;
- **+8 and +9**: horizontal speed (always 1 for Tal) and vertical speed;
- **+A**: the animation state;
- **+D**: the sprite shown;
- **+F and +10**: the sprite's half-width and height.

Two global variables complete the record: &B498, the index into the vertical speed table, and &B554, the result of the last wall test.

The four direction bits at +7 are the key to everything. Bit 0 moves up, bit 1 down, bit 2 left, bit 3 right. The game logic never moves Tal itself: it sets these bits and the speeds, and the animator shared by all objects (&6B0E, part &6C23) applies the movement. Bit 1 (down) stays set permanently while Tal is on foot. Gravity is always active, with a speed equal to the distance to the ground, so it is zero when he stands on a platform.

## A game turn

The main loop (&54FA) is not synchronised to a fixed rate. Each object is redrawn only at a precise moment of the frame, according to its height on screen (&6D19 waits for the right interrupt slot). The number of turns per second therefore depends on the number of moving objects. Measured in the emulator on the verification scenarios, it ranges from about 14 to 19 turns per second in the first room, an average close to 17; a room change makes it drop. The emulator counts raw Z80 cycles, without the CPC's memory-access rounding, which makes it slightly optimistic. Waiting for the beam, however, dominates computing time, which limits the error.

At each turn, when Tal is on foot (&B4F1 non-zero), the game runs three steps. Routine &65A2 handles the rising part of a jump, or looks for the ground and handles the fall, then reads the joystick if Tal is on the ground. Routine &67B6 tests for a wall ahead; if there is one, &6876 stops Tal. Later in the turn, the animator moves to the next frame of Tal's animation, then applies the movement. The model follows this order: `pied_tour()` then `animer()`.

## The state machine

Movement is data-driven. The joystick is first reduced to six classes by the table at &8F3B: nothing, up, right, down, left, fire. Diagonals fold onto the horizontal, and fire overrides everything. For each state, the table at &8F4B then gives the next state for each class, and a mask saying which joystick directions are copied into the movement bits. Bit 4 of the mask makes the state uninterruptible: no transition is accepted until its animation has finished. Animations (&9021) are small scripts: a delay, then a sequence of sprites, ended by FC (loop), FD (end; bit 7 marks the state as finished) or FE n (go to state n).

States 01 to 0A are Tal facing left, 0B to 13 their mirror facing right; bit 7 of the sprite number flips the sprite.

| State | Role | Sprites | Directions | Blocking | Nothing | Up | Right | Down | Left | Fire |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | facing front (turning) | 09, delay 2 | — | yes | · | · | 0B | · | 02 | · |
| 02 / 0B | standing | 08 / 88 | L / R | no | · | jump | 01 / 0C | 04 / 0D | 03 / 01 | 0A / 13 |
| 03 / 0C | walking | 8 looping frames | L / R | no | 02 / 0B | 02 / 0B | 02 / · | 04 / 0D | · / 0B | running jump |
| 04 / 0D | crouching down | 2 frames | — | yes | 05 / 0E | 06 / 0F | 06 / 0F | 05 / 0E | 06 / 0F | · |
| 05 / 0E | crouched | 2 frames, delay &18 | — | no | 06 / 0F | 06 / 0F | · | · | · | · |
| 06 / 0F | getting up | 2 frames | — | yes | 02 / 0B | 02 / 0B | 02 / 0B | 05 / 0E | 02 / 0B | · |
| 07 / 10 | jump | 0F / 8F | (set at take-off) | — | | | | | | |
| 08 / 11 | fall | 10 / 90 | (unchanged) | — | | | | | | |
| 09 / 12 | landing | 2 frames | — | yes | 06 / 0F | 06 / 0F | 06 / 0F | 05 / 0E | 06 / 0F | 06 / 0F |
| 0A / 13 | stone throw | 9 frames, then back to standing | — | no | | | | | | |

A dot (·) means the state does not change. States 0A and 13 were first taken for a kick. Watching them in the emulator showed a throw: at the third frame, the game creates object 1, the stone, with script &01 or &02 (see `enemies/ENEMIES.md`). States 14 and 15 are Tal's death; 16 to 1B concern the armour (see `ARMOUR_MOVEMENT.md`).

## Jumping and falling

The jump has a single table, &8EC2, in lines per turn: 01 01 02 02 03 03 04 04 05 06 07 08 08 09 09 0A 0A. At take-off the index &B498 is set to &0B. While rising, Tal goes up by the value read, then the index decreases (8, 7, 6, 5, 4, 4, 3, 3, 2, 2, 1). While falling, the index increases from 0 up to &10, and speed caps at 10 lines per turn. Deceleration on the way up and acceleration on the way down are thus two readings of the same table, in opposite directions. The ground is only looked for over the distance Tal will travel in the turn: if it is found, the speed becomes that exact distance, and Tal lands precisely.

There are three ways to jump (&6659):

- **Vertical jump**: up, while Tal is standing.
- **Standing jump**: fire, up and the direction Tal is facing.
- **Running jump**: fire while walking.

In the last two cases, the horizontal direction is fixed at take-off. In the air, the joystick is not read at all: there is no air control.

Computed by the model on flat ground (`trajectoires.py`), the three trajectories have the same height, 44 lines, and the same duration, 23 turns. The two horizontal jumps reach 22 bytes, or 44 mode 0 pixels: a little more than a quarter of the screen width. The standing jump and the running jump are strictly identical once in the air. After landing, it takes 7 turns before Tal is standing and responsive again, because landing (09) must be followed by getting up (06), two blocking states.

`trajectoires.py` also draws `trajectoires.png`: one point per turn, in the original screen proportions (one byte wide is about four lines high). The vertical jump is yellow, the standing jump green, and the running jump, launched after six steps, blue.

## No diagonal from the joystick, and what an obstacle costs

The joystick alone never produces a diagonal jump. The table at &8F3B folds up + right onto the class "right" (likewise to the left), and only the up bit is then examined by &6659. Standing, up + direction therefore gives a vertical jump: the horizontal bits of +7 are still empty at take-off. Walking, up + direction does nothing but keep walking, since the jump on "up" is accepted only in the standing states (02, 0B). A diagonal jump always goes through fire: fire while walking, or fire + up + the direction Tal faces. If Tal faces the other way, the same combination throws a stone.

The jump cancelled against a wall has a practical consequence. To clear an obstacle, Tal must take off from far enough away; otherwise the wall test cuts the rise before his feet are above the obstacle. This was measured with the model on a block standing on the ground. The gap counted is the number of free bytes between Tal's front (X+5) and the block at take-off. The standing and running jumps give exactly the same ranges, since they are identical in the air.

| Block height | Gaps that reach or clear the block |
|---|---|
| 8 lines | 3 to 19 bytes |
| 16 lines | 4 to 18 bytes |
| 24 lines | 5 to 16 bytes, and 18 |
| 32 lines | 7 to 14 bytes, and 16 |

Too close, the rise is cut; too far, Tal lands before the block. The isolated values come from the 8-line grid of the ground. A 32-line wall thus needs at least 7 bytes (14 pixels) of run-up. A narrower nook between a wall and the edge of the screen is a trap with no way out, except, in the game, by changing room. These figures hold to the right; to the left one byte less is needed, because the left wall test (see below) looks one byte less far. The sandbox had such a nook: its right-hand block left at most 5 bytes to the edge, while 6 are needed to escape to the left. The block was moved one cell, and the nook can now be left with 6 to 9 bytes of run-up.

## Option: the diagonal jump

The model offers an option absent from the game, off by default: `OPTIONS['saut_diagonal']` in `tal.py`, `{sautDiagonal: true}` in `sandbox/tal.js`. With it, up + the direction Tal faces launches a jump in that direction, standing or walking, without fire. The jump launched is exactly the game's (&66B1): only the key combination differs. If Tal faces the other way, the command keeps its original behaviour. With the option off, `verif.py` still matches the game; with it on, `sandbox/verif_js.py --diagonale` checks that the Python and JavaScript versions stay identical (80 000 turns).

## Collisions

Collisions are read from the screen itself, by pixel colour, as often at the time. There is no separate collision map.

The ground (&68B4) is recognised only on lines of rank 2 within their block of eight lines. Platforms therefore sit on a vertical grid of 8 lines. The test compares the six bytes under Tal's feet with a colour pattern (&8E1C); a single matching pixel is enough for Tal to stand.

The ceiling (&6714) is tested during the rise only above line &3A, that is, in the first eight lines of the screen. In practice only the top edge stops a jump: Tal passes through platforms from below.

The wall (&67B6) is tested over 35 lines in one column: X−1 to the left, X+7 to the right. Tal occupies six bytes, from X to X+5. The right-hand test therefore looks one byte further than the left-hand one, and Tal stops two pixels earlier against a wall on the right than against a wall on the left.

## Gaps between probable intent and code

Several behaviours found in the code look unintended, or at least debatable. They partly explain the stiffness of Tal's movements.

At the top of the jump, the last rising step is applied downwards. The index reaches zero and the direction switches to down before the animator applies the turn's speed. The real height is therefore 44 lines instead of the 45 the table gives. The verification harness confirms this on the real code.

A jump launched against a wall is cancelled in its first turn. The wall test follows the joystick reading in the same turn; it finds Tal blocked and resets the direction to "down". The code has an exception, but for index &0A, that is, the following turn. This branch was not reached in the scenarios.

Landing cuts horizontal momentum dead, then locks Tal for 7 turns (landing, then getting up).

Turning round must go through state 01, facing front, uninterruptible, with a delay of 2. From walking, Tal must first stop (a push the other way brings him back to standing), then push again to face front, then again to set off.

Speed depends on screen load. Since the rate is not fixed, Tal walks and jumps more slowly when enemies move: one byte per turn, i.e. between 28 and 38 mode 0 pixels per second according to the measurements above.

Finally, walking has no inertia: one byte per turn from the first frame, instant stop.

## What the model does not cover

The model does not cover room changes (when Tal leaves the screen, the game puts him back on the other side: X goes for instance from 4 to &44), death (state 14, triggered when energy &B4FB reaches zero), entering the armour, or sprite drawing. Collisions assume a screen in the CPC's format: `EcranMemoire` reads a memory image of the game. A modern reconstruction will replace this reading with a collision map, which means translating the rules above (8-line grid, colour pattern) into room data.

## Usage

```
python3 tables.py               # rewrites tal_tables.json from build/antiriad_5400.bin
python3 verif.py                # all scenarios against the real code
python3 verif.py saut_droit -v  # one scenario, with Tal's state at every turn
python3 trajectoires.py         # jump figures and trajectoires.png
```

To rework the movement, start from `tal.py`: each function carries the address of the routine it reproduces. The settings are data (`tal_tables.json`): the speed table sets the shape of the jump, the transition table sets the sequences and what is blocking. Any change can be confronted with the original behaviour by `verif.py`, which then shows exactly where, and by how much, it departs from it.
