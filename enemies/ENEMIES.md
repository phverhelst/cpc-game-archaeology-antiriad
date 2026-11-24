# Enemies and obstacles: creation, movement, contacts, damage

This folder documents everything in *The Sacred Armour of Antiriad* that is not Tal himself: enemies, obstacles, the thrown stone, collectable objects, and the way they act on Tal. Four scripts cover it:

- `extraire.py` reads the 45 movement scripts and the object lists of the 69 rooms from memory, and writes `ennemis.json` (generated locally, not committed);
- `monde.py` ("world") models this whole part of the game, transcribed from the Z80 code routine by routine;
- `verif.py` confronts the model with the real game running in the emulator;
- `trace.py` provides the traces.

Sandbox 3 (`sandbox/carte.html`) uses the JavaScript transcription, `sandbox/monde.js`, checked against `monde.py` by `sandbox/verif_monde_js.py`.

## Eight object slots

The game manages eight objects, in a table of 19-byte records starting at &B400. Slot 0 is Tal, slot 1 the stone he throws, slots 2 to 7 the room's objects. A flag byte (&B4EE) says which slots are active. The resting armour, a part or a recharge cell also occupy slots 6 and 7: a room with five enemies and a part would lose its fifth enemy, replaced by the part.

| Byte | Role |
|---|---|
| +0, +1, +2 | movement script: number, current step, turns left in the step |
| +3, +4 | position X (bytes) and Y (lines) |
| +5, +6, +E | position and sprite at the last drawing |
| +7, +8, +9 | directions, horizontal speed, vertical speed |
| +A, +B, +C | animation state (bit 7: animation finished), current frame, wait |
| +D | sprite shown (bit 7: flipped) |
| +F, +10 | sprite half-width (bytes) and height (lines), for collisions |
| +11, +12 | fade: +12 is 1 while appearing and FF while disappearing, +11 counts the turns |

Each state has four property bytes at &922A:

- **byte 0**, flags: bit 7 invulnerable, bit 6 fade-in on appearance, bit 5 reaction to contact with Tal, bits 0 to 4 the number of the reaction routine (table &9216);
- **byte 1**: the damage (bits 0 to 4) and the number of stone hits to withstand (bits 5 to 7);
- **byte 2**: the points scored.

## The game loop, seen from the objects

At each turn, after Tal's own logic (on foot or in the armour), the main loop runs the following routines. This is the part reproduced by `monde.fin_de_tour`.

| Routine | Role |
|---|---|
| &5704 | fades: 12 turns to appear, 13 turns to disappear, then the slot is freed |
| &6B0E | shared animator, from object 7 down to object 0: next frame, script step, movement, drawing |
| &68EF | stone throw, at the fifth frame of the gesture |
| &5DDA, &568D | gauges and score shown, catching up with the real values by one unit per turn |
| &5933 | collisions of Tal and of the stone with objects 2 to 7 |
| &5CD7 | effect of the stone on the object hit |
| &59B5 | reaction of each object Tal touches |
| &6932 | the stone disappears at the edge of the screen |
| &6217 | timers (respite, armour delay, generator) |
| &604F | armour start-up, after the first entry |
| &5642, &55F5, &5598 | room-specific behaviours: cannon, drop, flying creature |

## Creating a room's objects

On entering a room, everything is destroyed (&6A1F), the room is drawn and its objects are created (&7051), in this order:

1. the armour, if it rests there (slot 7);
2. the room's list (table &9BC7), from slot 2;
3. the first uncollected part of the room (slot 6);
4. the first unused cell of the room (slot 6, or 7 if 6 is taken).

Each list entry gives the position, the script and the state. The number of hits to withstand comes from the state's properties. There are 2 to 5 objects per room, 244 in all. An "FF" exit (no neighbour) recreates the room like an ordinary room change.

An object of state &29 in a list is a materialisation. Its creation interrupts the list's. Forty turns later (&6217) it disappears, and the rest of the list appears in its place. Five rooms have one: &20, &31, &36, &3D, &40.

In rooms &00 and &01, if Tal does not have the particle negator, his life energy drops to zero on entry (&7113). On foot, he dies at once. The message is EXTREME RADIATION SHIELD FAILURE IMMINENT.

## Movement: one script per object, no collision with the scenery

A script (table &97F8) is a sequence of 4-byte steps:

1. directions, copied into +7;
2. duration, into +2 (the step lasts duration + 1 turns);
3. horizontal speed, into +8, in bytes per turn;
4. vertical speed, into +9, in lines per turn.

Four command codes are added, through the table at &9BC1. FC restarts the script. FD freezes it: the object keeps its last directions forever. FE hands control back to Tal; it is used only by Tal's own scripted sequences, death and rebirth. FF is unused. The script does not advance during a fade.

No collision with the scenery is tested for objects. The three routines that read the scenery (ground &68B4, ceiling &6714, wall &67B6) are called only by Tal's logic. Enemies and stones therefore pass through platforms and walls; like every object, they are bounded only by the edges of the screen.

When a step's directions are &0F, the animator computes the direction at each turn (&6CDE). The target is the point (Tal's X − 3, Tal's Y + 12), at chest height. Horizontally, the object moves right or left until exactly level. Vertically, it moves up or down, unless the gap is under 4 lines. There is neither anticipation nor detour. Three scripts use this guidance:

- **&1F** chases Tal at 1 byte and 4 lines per turn;
- **&20** chases him only horizontally;
- **&21**, the most common, waits 62 turns (about 3.6 seconds at 17 turns per second), then chases like &1F.

A chaser moves exactly at Tal's walking speed: walking does not shake it off.

| Category | Scripts | Objects placed | Description |
|---|---|---|---|
| Closed patrol | &05 to &1E, &24 to &28, &2C, &2D | 125 | A loop of horizontal, vertical or diagonal segments that returns exactly to the starting point; cycle of 18 to 142 turns |
| Guided towards Tal | &1F, &20, &21 | 57 | Pursuit recomputed every turn |
| Falling | &22 | 11 | Waits 11 turns, then falls vertically at 4 lines per turn |
| Projectiles | &01, &02 (Tal's stone), &23 (dropped object), &29 (cannon shot) | — | Created during play |
| Tal's sequences | &03, &04, &2A (death), &2B (rebirth) | — | Short scripted sequences of Tal |
| No script | — | 51 | Motionless objects: obstacles, barriers, collectables |

The closed patrols are checked by calculation: over a complete cycle, the sum of the movements is zero on both axes. The slightest gap would make the object drift out of its area over the loops.

## Contacts and damage

The collision test (&5933) compares Tal, then the stone, with objects 2 to 7. Two objects touch if the horizontal gap is less than the width of the one on the left, and the vertical gap less than the height of the one above. Results are stored at &B502 (Tal) and &B508 (stone). They are not recomputed for an inactive object: when Tal fades out, his last contact remains valid. The game uses this for entering the armour and for the teleporter; the reaction happens when Tal has finished disappearing. When Tal is inactive, the stone's contacts are even written in place of Tal's.

A touched object whose state has reaction 5 (&5B19) wounds Tal. Nothing happens during a fade of the object or of Tal. On foot, the damage value is subtracted from life energy (&B4FB, 31 at most). In the armour, it is halved, and halved again with the particle negator, then subtracted from the armour's energy (&B4FD). An ordinary (vulnerable) enemy dies from the contact and scores its points; an invulnerable obstacle stays, and wounds again on the next turn. Traps &30, &31 and &3C then impose an 8-turn respite (&B552), during which only trap &3B still wounds; that one wounds every turn.

| State | Objects | Nature | Damage | Stone hits | Points |
|---|---|---|---|---|---|
| &22 | 38 | enemy | 8 | 3 | 35 |
| &23 | 31 | enemy | 6 | 1 | 30 |
| &24 | 25 | enemy | 8 | 2 | 30 |
| &25 | 25 | enemy | 6 | 2 | 30 |
| &26 | 12 | enemy | 4 | 1 | 20 |
| &27 | 12 | flying creature that drops a projectile | 12 | 4 | 60 |
| &28 | 20 | enemy | 6 | 1 | 30 |
| &29 | 5 | materialisation | 4 | 1 | 40 |
| &2E | — | projectile dropped by the flying creature | 12 | — | 30 |
| &33 | — | cannon shot | 12 | — | 0 |
| &2A, &39 | 11 | drop, invulnerable | 1 | — | — |
| &2B | 3 | cannon, invulnerable | 16 | — | — |
| &2F | 6 | plant, invulnerable | 4 | — | — |
| &30 | 19 | fixed trap, invulnerable, 8-turn respite | 6 | — | — |
| &31 | 10 | moving trap, invulnerable, 8-turn respite | 6 | — | — |
| &3B | 5 | fixed trap, invulnerable, no respite | 5 | — | — |
| &3C | 12 | moving trap, invulnerable, 8-turn respite | 5 | — | — |
| &37, &38 | 7 | barrier | — | — | — |

The plant &2F touches Tal only if he is to its right or at the same X, and spares him if he is crouching. The cannon shot also spares Tal crouching, if he is low enough (Y ≥ &78). Barriers &37 and &38 (reaction 8, &5BFF) let Tal on foot through and send the armour back: horizontal directions and stored facing reversed, by the same routine as the bounce off a wall (&68A3).

## The stone

Fire while standing still, with Tal facing one side, throws a stone (&68EF) at the fifth frame of the gesture, if no stone is already in flight. It starts 2 bytes to Tal's left or 6 bytes to his right, 6 lines below the top of his head. To the right (&01) it travels 68 bytes in 17 turns; to the left (&02), 60 bytes in 15 turns. It first rises in an arc, then falls. It disappears at the edge of the screen (&6932).

When it hits an object (&5CD7, only one per turn, starting from object 7), it stops: it rises 4 lines, loses its script and goes to state &2D, a small splash that fades. If the object is invulnerable, nothing else happens. Otherwise it loses one hit (two for a projectile of a state other than the stone, presumably the armour's shot, not yet studied). At zero, it disappears and scores its points, halved if the projectile is not the stone.

## Room-specific behaviours

The flying creature (&27, always the first object of its room) drops a projectile (&2E, script &23) into the slot following the room's objects, as soon as that slot is free (&5598). The projectile starts 5 bytes to its right and 21 lines lower. It is destroyed when it reaches line &A0.

The drop (&2A, always the first object) waits, switches to state &39 and falls. Reaching line &92, it is set at &95, splashes (&3A) then disappears, and is immediately recreated at its starting point (&55F5). A room has only one drop.

The cannon (&2B, first object, rooms &1E, &21 and &32) fires as soon as slot 5 is free and its animation allows (&5642). The shot is always born at the same point (X &1B, Y &7F), with script &29, and disappears when it reaches X &46.

The teleporter (&21, room &27, reaction 7) makes Tal disappear if he touches it while facing front, and carries him next to the armour, in the room where it rests. The message is BEAM ME UP SCOTTY. Object &3D in room &00 (reaction 9) is the target of the implosion mine: landing on it in the armour with the mine triggers the end of the game (see `PANEL_AND_ENDING.md`).

## Death and lives

Death is part of Tal's on-foot logic (&579C). When his life energy is zero and he is neither jumping nor falling, Tal moves down 6 lines and switches to state &14, with script &2A. The life counter (&B551) is shifted by one bit. At the end of the animation (&57D7), he is reborn on the spot: energy back to 31, 11 lines higher, state &15 and script &2B, then back to player control. The counter starts at &20: Tal therefore has five lives, and the fifth death ends the game (YOU HAVE DIED YOUR RACE IS DOOMED). During a script or a fade of Tal, his logic (&65A2) does not run.

## Before and after the armour's start-up

Until Tal has entered the armour once, the flag &B512 is FF. Gauges and score do not move, no object can be collected (&5D85), there are no rebirth messages, and radiation is not computed. On the first entry (&6112), a start-up sequence begins (&604F). Each turn reads one bit of a nine-byte pattern (&8E12), which makes the panel flash. At the first zero byte, about 63 turns later, &B512 becomes 0 and the panel shows a "suit active" message. From then on, each room's radiation level (&72C5) applies. It runs from 0 to 6, the higher the lower the room number, with thresholds at &8B37. From 5 upwards, it forbids leaving the armour (HIGH RADIATION SAFETY INTERLOCK OPERATIVE).

## Verification

`verif.py` makes Tal enter a room through the game's routines and plays a key plan. At every turn, it compares the model applied to the game's memory image with the game's result, over the eight records and the variables concerned. It also runs the model continuously, without resynchronising, taking only Tal himself from the game. Finally, it compares the creation of the objects on entering each room and, separately, Tal's death and rebirth.

The first 19 scenarios cover 10 rooms, on foot and in the armour, 3 948 turns. They include:

- chasers, the flying creature, drops, the materialisation, the cannon, plants, traps and barriers;
- the stone: targets hit, hits withstood, enemies killed;
- damage on foot and in the armour, with and without the negator;
- the armour's start-up.

Everything matches, step by step and continuously. Death and rebirth match over two scenarios of 260 and 283 turns, up to the end of the game. With the panel and ending (`PANEL_AND_ENDING.md`), there are now 24 scenarios and 5 262 turns. `sandbox/verif_monde_js.py` checks the JavaScript transcription on the same turns, plus the creation of the objects of the 69 rooms in six configurations: 4 477 cases, all identical.

For each inactive object slot, the animator calls &699C, a delay loop of 300 iterations (about 2 ms at 4 MHz). The game thus partly compensates the time freed when an enemy disappears, but only partly, hence a rate that varies from 14 to 19 turns per second.
