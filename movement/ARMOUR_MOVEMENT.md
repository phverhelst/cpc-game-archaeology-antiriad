# Tal in the armour

This document describes Tal's movement inside the sacred armour, getting in and out, the armour's parts, its energy and the recharge cell. The model is in `armure.py`, which builds on `tal.py`. The harness `verif_armure.py` confronts it with the original code running in the emulator. Over nine scenarios (392 turns: take-off, drift, walls, ceiling, landing, turns, armour without energy, cell carried, inert armour), the model reproduces the game's state at every turn, field by field. The comparison is made step by step and continuously. Only leaving the armour, which is an event, remains outside the model and is reported as such.

To put the emulator inside the armour, the harness makes the game run its own entry routine (&60D3), called from the main loop with a return to &54FA, after setting the desired part flags and energy.

## What changes inside the armour

The variable &B4F1 is 0 when Tal is in the armour. The main loop then calls &5744 instead of the on-foot logic (&5787). Tal remains object 0, with the same record fields; his animation states are &16 to &1B.

| State | Role | Sprite | Main transitions |
|---|---|---|---|
| &16 | facing front, flying | &16 | right → &1A, left → &18 |
| &17 | resting on the ground | &17 | up → &16; left or right: leave the armour |
| &18 / &1A | turning left / right | &15 / &95 | to &19 / &1B, or back to &16 |
| &19 / &1B | facing left / right | &14 / &94 | the only states in which the armour can fire |

A complete turn therefore goes through two intermediate poses (&19 → &18 → &16 → &1A → &1B). State changes are accepted only when the armour is no longer sliding horizontally.

## The throttle

Vertical movement does not depend on a speed but on a fifteen-notch throttle (&B51D, 0 to 14, neutral at 7). Each turn, up moves it down one notch and down moves it up one notch. With no vertical command, it moves one notch back towards neutral. The table at &8EF3 gives the direction and speed for each notch:

| Notch | 0 | 1-2 | 3-4 | 5-6 | 7 | 8-9 | 10-11 | 12-13 | 14 |
|---|---|---|---|---|---|---|---|---|---|
| Speed (lines/turn) | up 4 | up 3 | up 2 | up 1 | 0 | down 1 | down 2 | down 3 | down 4 |

Acceleration and deceleration are thus gradual. Going from neutral to full speed takes 7 turns, and as many to come back to neutral on release. At neutral, in flight, the armour hovers (&627B): the table at &8ED3 moves it up one line, waits, then down again, over a 16-turn cycle.

## Horizontal momentum

Horizontal speed is always 1 byte per turn. What changes is how long the push lasts. The counter &B51E rises by 1 per turn, up to 6, as long as the player pushes in the direction the armour faces. On release, or as soon as the command changes direction, it falls by 1 per turn, and the armour keeps moving as long as it is not zero. The armour therefore slides up to 6 turns (6 bytes, 12 pixels) after being let go.

## Collisions and bounces

The ground is looked for under the armour over the turn's distance (speed + 1), with the same routine as for Tal on foot (&68B4). The ceiling is looked for from Y + 3 upwards, with &6714. Unlike Tal on foot, the armour tests the ceiling at every height.

On contact, the armour bounces: the throttle is "reflected", taking the value 15 minus its value (&6390), and the vertical direction is reversed. An armour that hits the ground at full downward speed (notch 14) therefore sets off upwards at notch 1. If the armour comes down facing front or resting (&16 or &17), it does not bounce: it lands and goes to state &17.

The wall test covers 38 lines instead of 35 for Tal on foot. On contact, the horizontal direction is reversed (&68A3) and the armour moves back for the rest of its momentum. When the armour is at the very top of the screen (Y < &33), the test changes nature: it covers the first four lines of the screen (&8C57), and any non-black pixel counts as a wall.

## Getting in, getting out, parts, energy

To get in (&6094), Tal on foot must touch the armour while facing front (state 01), with life energy, and with no re-entry delay running. The game then removes the armour object, recreates Tal in its place in state &17, puts the throttle at neutral and the momentum at 0. To get out (&6150), the armour must be resting (&17) and the player pushes left or right. Tal reappears facing front, the armour stays where it is, and a 40-turn delay (&B517, decremented every turn by &6217) prevents him from getting straight back in. Leaving is refused if radiation is too high (&B538 ≥ 5), with the message HIGH RADIATION SAFETY INTERLOCK OPERATIVE.

The four parts are objects to collect (states &1D to &20, table &8F14). Each one clears its flag (&B519 to &B51C) and shows its message:

| Part | Flag | Effect |
|---|---|---|
| &1D, gravity displacer | &B519 | without it the armour is inert (GRAVITY PREVENTS TAKEOFF) |
| &1E, pulsar beam | &B51A | allows firing, in states &19 and &1B |
| &1F, implosion mine | &B51B | needed for the ending (see `enemies/PANEL_AND_ENDING.md`) |
| &20, particle negator | &B51C | halves damage taken (&5BB2), and protects in rooms &00 and &01 |

Firing creates object 1 with script &03 or &04. Before that, the game copies the armour's current directions and speeds into the script: the shot inherits the armour's movement through modification of the script data.

The armour's energy (&B4FD, 31 at most) is not used up in flight. It drops when an enemy touches the armour (&5BC3, the same routine as for Tal's life energy). It also drops by 2 points every 100 interrupts (a third of a second) in rooms 0 and 1. Below 7, the game shows DANGER SUIT ENERGY LOW. At 0, it shows SUIT INOPERATIVE RECHARGE CELL DEPLETED, and the command is forced downwards: the armour descends and can no longer climb.

The recharge cell (state &1C, fifteen of them listed at &A066) is collected by touching it. Tal can carry only one (&B518 = 0 while he carries one). In the armour, it is used at once and restores energy to 31. Collected on foot, it is used as soon as Tal is in the armour.

## Gaps and oddities in the code

**The throttle sound loses an update.** When the throttle leaves notch 6 upwards, or notch 8 downwards, &6437 plays a sound through &752A. That routine overwrites register IX. The direction and speed update of that turn (&64DC) is then written elsewhere in memory (&7A89 + 7 and + 9 in our traces), and the armour keeps the previous turn's values. The defect is almost always invisible: the table gives exactly the same values at notches 5 and 6, and at 8 and 9. It only shows if something else changed the direction in the meantime, for example the resting armour resetting its direction to 0. The harness exposed it; the model reproduces it.

**The throttle can leave its table.** The code's guard stops the throttle only at exactly 14. A bounce off the ceiling at full throttle (notch 0) sets it to 15; if the player then pushes down, it goes to 16, 17 and so on. The game then reads the bytes following the table as directions and speeds. The model reads the same bytes from memory.

**A room with no neighbour can plant the armour in the ground.** Leaving by an edge that leads to no room (neighbour &FF) puts the object back on the other side of the same room. Through the top, this gives Y = &99, which puts the armour inside the ground. It then stays stuck, because its wall test meets the ground pixels.

**Collisions can read game variables instead of scenery.** In the line address table, all lines above the screen (below &32) point to a buffer at &B49B, where the game keeps the saved palette and some of its variables. A collision probe looking above the screen therefore reads game variables. The sandboxes read 0 at those heights.

## Reaching the armour

The script `rooms/accessibilite.js` explores every state that Tal on foot can reach with the verified model. From a starting point, it tries twelve key combinations at each turn and looks for a state where Tal touches the armour while facing front.

The armour's room (&3F) has &31 above, &3E to the left and &40 to the right; it has none below. In the square of sandbox 2 (&31 | &32 above &3F | &40), the armour can be reached in two ways:

- **From above, the simplest.** From a platform in room &31, Tal jumps to the right and drops through the bottom of the room: he lands on the armour's ledge (51 turns).
- **From the floor of &3F.** Tal climbs back to the small step on the far left of the room, then makes a standing jump to the right (92 turns). Measured position by position, this jump succeeds from only three positions (X &05 to &07). At X &04 Tal would change room, and a running jump is impossible for lack of run-up.

From the floor of &40 the route goes through &3F (156 turns); from &32, through &31 (131 turns). The diagonal jump option does not change these figures, since it is the same jump; it only spares the fire + up + direction combination.

Over the whole map, from the game's starting room &44, Tal on foot reaches 44 rooms: the armour's room, and those of the gravity displacer (&2B) and the pulsar beam (&21). The 25 rooms &00 to &18 remain out of his reach, among them those of the mine (&14) and the negator (&06). The flying armour is therefore needed to explore the rest of the world. Accessibility inside the armour has not yet been measured.

Collecting obeys a precise rule (&5D85). In the armour, contact is enough. On foot, Tal must be crouching down (states &04 or &0D) when he touches the cell or the part.

## Sandbox

`sandbox/armure.html` flies the armour in four real rooms of the game (&31 and &32 above, &3F and &40 below), captured by `rooms/capturer.py`. The JavaScript model `sandbox/armure.js` is checked against `armure.py` by `sandbox/verif_armure_js.py`: 160 games of 300 turns in these rooms, on foot and in the armour, compared turn by turn.
