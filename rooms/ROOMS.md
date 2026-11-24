# The rooms

`capturer.py` makes the game's own routine (&7051) draw each of the 69 rooms in the emulator, and reads the play area before the objects are created. The result is written to `salles.bin` (69 × 136 lines × 80 bytes). The script also writes `salles.json`, which gives each room's palette, colour scheme and links. Both files are generated locally and not committed.

The links (&9632, four bytes per room) are read in the order used by the room-change routine (&69A7): byte 0 for an exit to the right, 1 to the left, 2 downwards, 3 upwards. A first version read them in the order left, right, up, down. The reconstructed map was then rotated by half a turn, and looked consistent because the error was symmetric. The exact order was confirmed in the emulator: leaving the starting room (&44) by the left, Tal arrives in &43 with X = &44.

The room changes when Tal (or the armour) has:

| Condition | Exit | New position |
|---|---|---|
| X < 5 | left | X = &44 |
| X ≥ &45 | right | X = 6 |
| Y ≥ &9B | down | Y = &1B |
| Y < &19 | up | Y = &99 |

A link &FF means there is no neighbour: the game redraws the same room with Tal put back on the opposite side.

The map layout follows the C64 map of the C64-Wiki: a grid of 15 columns by 14 rows, with the same room numbers. Of 193 links, 185 join two neighbouring cells of this grid. The only correction comes from the Amstrad links: room &06 is to the left of &07 and above &0A, not to the right of &09 as on the wiki's numbered grid. Rooms &27 and &28, missing from that grid, appear on its illustrated map, above &36 and &37. The remaining 8 links lead from one end of a row to the other (&06/&09, &0D/&12, &1A/&23, &29/&37): these four rows close on themselves. The wiki's images do not show links, so they do not tell whether the C64 version has the same wrap-arounds.

A first layout, computed by walking from &44, placed some rooms at the opposite end of their row by following these wrap-arounds, producing a "cylinder" and "jumps" that did not exist. The exit through the bottom of room &32 names a room &45 that does not exist: the table has only 69 entries, and the game would read beyond them into unrelated data. Room &40 leads to &32 through the top, however, which makes this link the only non-reciprocal one.

`accessibilite.js` (Node.js) exhaustively explores, with the verified model `sandbox/tal.js`, the states that Tal on foot can reach. The `carre` mode is limited to the four rooms of sandbox 2, with closed edges; the `monde` mode covers the whole map, with the game's rules. Options: `depart=XX` for a starting room, `complet` to list the rooms reached, `diagonale` to enable the diagonal jump. Results: see `movement/ARMOUR_MOVEMENT.md`.

## A continuous world, and the cameras of sandbox 3

The position in the world is computed per axis, column and row being the room's cell on the 15 × 14 grid described above:

- horizontal: column × 64 + X, in bytes;
- vertical: row × 128 + (Y − &32), in lines.

With the room-change thresholds of &69A7, Tal keeps the same world position when he crosses a horizontal or vertical border (to within one line when rising).

Sandbox 3 uses this to draw the neighbouring rooms around the current one, without their bottom strip (lines &B3-&B9). A neighbour is drawn only if the game's link leads to it and it occupies the expected cell. A non-planar link or an &FF exit therefore never shows a room that is not really adjacent.
