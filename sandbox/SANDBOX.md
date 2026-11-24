# The sandboxes

Three self-contained web pages, built locally from templates because they embed game data (palette, sprites, rooms, memory image). They are never committed: run `make_all.py generate`, or the three `construire*.py` scripts, then open the HTML files in a browser.

| Page | Built by | Contents |
|---|---|---|
| `index.html` | `construire.py` | Sandbox 1: Tal on foot in a test room. His object record and collision probes are shown at every turn, and the movement settings can be changed live. |
| `armure.html` | `construire_armure.py` | Sandbox 2: Tal, the armour and a recharge cell in four real rooms of the game (&31 and &32 above, &3F and &40 below). |
| `carte.html` | `construire_carte.py` | Sandbox 3: the complete map of 69 rooms, starting from the game's memory at the beginning of its main loop (`build/antiriad_54FA.bin`). It has enemies, obstacles, the armour's panel drawn in screen memory, and five camera modes. A whole game can be played, up to victory or the fifth death. |

The page texts are still in French; translating them is a welcome contribution.

## The verification chain

Each JavaScript model is a function-by-function transcription of a Python model, which is itself verified against the Z80 code:

| JavaScript | Python model | Check of the JavaScript against Python |
|---|---|---|
| `tal.js` | `movement/tal.py` (592 turns, eleven scenarios, against the game) | `verif_js.py`: 200 games of 400 random turns in the test room, all states 01 to 13 reached, complete state compared at every turn. The check was itself tested by introducing two one-byte errors, both caught. |
| `armure.js` | `movement/armure.py` (392 turns, nine scenarios) | `verif_armure_js.py`: 160 games of 300 turns in the four real rooms, on foot and in the armour |
| `monde.js` | `enemies/monde.py` (24 scenarios, 5 262 turns, plus death, firing and the ending) | `verif_monde_js.py` (and `verif_monde_js.js`): MD5 of the whole 64 KB memory after every turn, from 26 starting points taken from the game, plus the creation of the objects of all 69 rooms |

The sprites are the game's own, decoded as the drawing routine &6D3C does it. Each byte goes through the tables at &0200 and &0300, then the sprite's tint (&9332) is ORed in; a zero byte is transparent. The data face left, and the game flips them in place for the right (&73F0). The decoding was compared byte by byte with what the game writes to the screen.

The test room of sandbox 1 (`salle.py`) is not a room of the game: it is built with the same collision rules. Platforms have a top line in the pattern recognised as ground, placed on the 8-line grid. Blocks are made of bytes recognised as wall, and also as ground on their top line. The rate is fixed and adjustable (17 turns per second by default), whereas the game's rate varies with the number of objects on screen.
