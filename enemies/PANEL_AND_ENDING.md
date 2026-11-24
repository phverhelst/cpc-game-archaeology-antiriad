# The armour's panel, the pulsar beam and the end of the game

This document complements `ENEMIES.md`. The routines described here are transcribed in `monde.py` (and `sandbox/monde.js`) and checked against the game by `verif.py`.

## A screen in two modes

Screen lines 0 to 135 form the play area, in mode 0 (16 colours, 160 pixels wide). Lines 136 to 199 form the panel, in mode 1 (4 colours, 320 pixels). The interrupt handler, called six times per frame, changes mode and palette at the fourth interrupt, then returns to the play area at the first. The panel's three pens come from the table at &8E09. Everything the panel shows is written directly into screen memory by the routines described below. Sandbox 3 does not imitate the panel: it reads it from its model's screen memory, as the video circuit would.

## What the panel shows

| Element | Routine | How it works |
|---|---|---|
| Tal's life gauge | &5DE9, &5DFC | The displayed value (&B4FA) catches up with the real value (&B4FB) by one notch per turn, and only one byte of the gauge is redrawn each time, over 4 lines. The first 16 notches are red, the next ones cyan |
| Armour energy gauge | same | Same mechanism, &B4FC towards &B4FD |
| Score | &568D, &56A8, &6FBE | The displayed score (&B534) catches up with the real one (&B536) by one unit per turn; at each step the five digits are rewritten |
| Central screen | &5E56 | Every turn, 230 bytes of program memory, read from an advancing pointer (&B4F7), are copied onto 23 lines: the screen's "noise" is the game's own code |
| Picture of a part | &5F83, &5F99, &5FC8 | When a part's message is shown, the central screen is cleared and the part's picture (16 lines of 6 bytes, at &21D8) is copied there; the noise stops until the next message |
| Messages | &5EA0, &5F12, &5F55, &5FFC | A queue of 8 messages (&B521). The text advances by one byte (two pixels) per turn, at the left of a 21-byte window; a letter is 2 bytes wide and so enters in two turns. Between two messages a blank (message 0) scrolls by |
| Radiation dial | &72C5, &72FE, &7319 | Level 0 to 6 according to the room number (thresholds at &8B37); drawn in segments, as special characters of the font, with an exclamation mark from 5 |
| Part lights | &5A43, &5A67, &5A8B, &5AB3 | A lit character at four fixed positions |

All texts go through the same routine (&6FBE), which reads codes:

- `$` ends the text;
- &0D starts a new line;
- a byte from &80 to &83 selects one of four colour masks (&8BEF);
- the other codes designate characters.

Digits and letters are computed; the other characters go through a correspondence table (&8B3D, &8B50). Each character is 8 lines of 2 bytes, taken from &0400. The segments of the radiation dial are simply characters of this font.

A programming detail shows in the code: when the message queue empties, routine &5FFC returns the pointer left by the sound routine it has just called (&7A5B). The "next letter" is therefore read from the sound registers. It has no effect, since the scrolling stops.

## Before and after start-up

Until Tal has entered the armour once, &B512 is FF and the panel stays frozen: no gauges, score, messages or radiation. The first entry (&6112) writes "00000" to the score, starts the start-up sequence and computes the radiation. For about 63 turns, each turn reads one bit of a nine-byte pattern (&8E12). According to that bit, the panel's colours are taken from &8E0C or from &8E0F (&61E9, &61F8), and the panel flashes. At the first zero byte, &B512 becomes 0 and the "suit active" message scrolls. Entering or leaving the armour also changes three colours of the play area, pens 13 to 15 (&61BB, &61D2): those of Tal and the armour.

## Every two seconds

Part of the logic depends not on game turns but on real time. The interrupt counts frames (&B541), and every 100 frames, two seconds at 50 Hz, it acts (&6F18):

- **In the armour**, Tal regains one life point (up to 31).
- **In rooms &00 and &01**, the armour loses two energy points. A quirk of the code leaves it stuck at 2 if it lands exactly on that value.
- **On foot**, radiation wears Tal down in rooms of level 2 to 4 (&06 to &19): 1 point at levels 2 and 3, 2 points at level 4.
- **At levels 5 and 6** there is no wear, but the armour cannot be left (HIGH RADIATION SAFETY INTERLOCK OPERATIVE).

Since the game's rate varies, these two seconds amount to between 28 and 38 turns.

## The pulsar beam

Once the pulsar beam has been collected (&B51A = 0), fire shoots when the armour faces one side (states &19 and &1B) and no projectile is in flight (&64EF). The beam occupies slot 1, the stone's, 6 bytes towards the target side and 14 lines below the top of the armour. Its script (&03 to the right, &04 to the left) is modified in place when firing: the first step takes the armour's directions and speeds, so that the beam first follows the armour's movement for 3 turns. It then drops 6 lines, pauses, and shoots off at 4 bytes per turn. Against an enemy it removes two hits instead of one, but scores only half the points. Without the beam, fire in these two states shows PULSAR BEAM NOT FITTED.

## The end of the game

The target is the object of state &3D, at the bottom of room &00, under a decorative structure (&3E). Its contact reaction (&5C0E) requires three conditions: the mine collected (&B51B = 0), Tal in the armour facing front (state &16), and moving down. The armour must therefore land on it from above. It is then set down (state &17), the detonation countdown message enters the queue, and all objects are deactivated (&B4EE = 0), Tal included. The game keeps running, but only the panel remains.

The countdown has no timer: the scrolling of the text drives it. The message ends with a "y" character (&79), and it is the scrolling routine that, on meeting this character, calls the final sequence (&5C31). In the verified scenario this takes 209 turns, about twelve seconds.

The final sequence (&5C31) first sets CRTC register 8 to 1 (interlace mode), which makes the picture shake. It then draws 16 384 random addresses (&6584, a 16-bit congruential generator, &B4EF) and clears those that fall within the first 16 character rows of each screen block, i.e. within the play area: 10 240 distinct bytes. Each draw is followed by a wait, and the disintegration lasts several seconds. Register 8 is then reset to 0. A single object is created (slot 4, state &3F, script &2D): the armour, facing front, moving up and down by one line in the centre of the screen. The final loop (&5CA6) only animates this object and the panel, putting the victory message back in the queue every turn. Fire restarts the game. The visual effects of this sequence are analysed in `intro/INTRO.md`.

Conversely, the fifth death (&582C) shows YOU HAVE DIED YOUR RACE IS DOOMED. The main loop continues, enemies included, until the player presses fire. The game also waits for the displayed score to catch up with the real one.

## Verification

In addition to the records and variables, `verif.py` compares the 64 lines of the panel in screen memory. Only the central screen (lines 157 to 183, columns 36 to 45) is excluded. It shows the game's memory at the exact moment of drawing, and part of what it shows (stack, records, sound) changes during the turn. For this screen the pointer is checked, not the picture. Since the two-second interrupt falls at an arbitrary moment of the turn, the harness tries it before and after the modelled part, and keeps the order that matches.

The added scenarios cover:

- the panel on foot (gauge, score, stones);
- radiation in two rooms;
- the message queue (armour without displacer);
- the pulsar beam (shots checked separately, &64EF);
- the complete ending: the mine set down in room &00, 209 turns of countdown, the screen's disintegration (byte-by-byte comparison of the 16 KB) and 300 turns of the final loop.

In all, 24 scenarios and 5 262 turns, plus death, firing and the ending: everything matches. `sandbox/verif_monde_js.py` checks the JavaScript transcription by comparing a hash of the whole memory (64 KB) after every turn, over 26 starts of 320 turns. It also checks the creation of the objects of the 69 rooms in several configurations. Two errors deliberately introduced into `monde.js` were both caught.

## Outside the model

The sound driver is studied separately (`sound/SOUND.md`). Sandbox 3 does not reproduce the screen shake during the implosion, and its disintegration is accelerated.
