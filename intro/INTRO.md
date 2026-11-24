# The opening and the ending: two display effects

This folder documents what the player sees before the first game and after the last: the opening sequence of the studied copy, the game's title screen, then the final implosion. Both effects are real, but they do not have the same author, and that is the first thing to say.

## Who made the opening

The only source is CNGSoft's disk image, a conversion of the tape made in 2013. The program that runs before the game, `ANTIRIDE.BAS`, is CNGSoft's loader; its BASIC line carries the signature "CNG LZ5 20131017". It displays the logo, then the loading screen with the curtain effect. None of this code is by Palace Software or Andrew Fitter. The original tape loader, with any turbo loading and its own way of revealing the picture, is not on the disk and could not be examined.

The picture itself raises a related question. The loading screen is in mode 2, two colours, 640 pixels wide; its drawing shows regular vertical stripes that suggest a picture of another resolution stretched horizontally. Our files cannot tell whether it is the tape's screen as it was, or an adaptation made for the conversion. A comparison with a capture of the tape version would settle it, and so would a study of the tape's own loader (contributions welcome).

The title screen and the end of the game, on the other hand, are in the game's code (&5400 onwards) and date from 1986.

## The sequence

Measured in the emulator (`chargeur.py`, "loader"), the loader runs six stages:

1. It decompresses and displays the CNGSoft logo in 0.2 seconds, then keeps it on screen for three seconds.
2. It blanks the screen while it decompresses the loading screen (0.6 seconds).
3. It reveals the loading screen with the curtain (3.52 seconds).
4. It waits for the space bar.
5. It blanks the screen again to decompress the game (3.4 seconds).
6. It jumps to &5400.

The decompression times are counted in raw Z80 time. On the real machine, where the Gate Array stretches every instruction to a multiple of 4 T-states, they are a little longer. The logo's three seconds are exact: 225 rounds of four `HALT`s, at 300 interrupts per second.

`video.py` assembles `intro.mp4`: the whole sequence, up to the title screen and its music (40 seconds of title, out of the 115.6 of the complete loop).

## The CNGSoft logo, in overscan

`images.py` renders it as `logo_cngsoft.png`.

The loader programs the CRTC beyond the standard values:

- R1=48: 48 words, i.e. 96 bytes per line instead of 80;
- R2=50;
- R6=34: 34 rows of 8 lines, i.e. 272 lines instead of 200;
- R7=35.

The picture covers the whole border: this is "overscan", a well-known technique of CPC demos. It usually has a cost, since 96 × 272 bytes make 26 112 bytes, more than the 16 KB of a screen. The loader avoids it. From the 22nd row, the CRTC's address counter (MA) exceeds 1024 words, but the Gate Array ignores bits 10 and 11 of that counter. The bottom of the screen therefore rereads the top of the same 16 KB block. To hide the repetition, the background is a repetitive pattern.

That background is generated, not stored. The loop at &01AB fills the 16 KB with two small 8-line patterns (at &BE80 and &BE90), chosen cell by cell according to the parity of a counter. This gives a maze in the manner of the famous Commodore 64 one-liner `10 PRINT`. The logo is then laid over it (&01D2) from a small source picture, each pixel enlarged into a block; colour-0 pixels are skipped and let the maze show through. Ten inks, set through the firmware, and a blue border complete the screen.

## The falling, bouncing curtain (&0251-&02B7)

This is the most interesting effect, and it does not touch a single byte of the screen. The picture is entirely in memory from the start; everything happens in the palette, in step with the electron beam.

The screen is in mode 2, so there are only two pens. Each frame, the loader proceeds as follows:

1. It waits for the end of vertical sync by reading port B of the PPI (&F5xx, bit 0), with interrupts disabled so that nothing upsets the timing.
2. It gives the pens the picture's colours (dark blue background, white drawing).
3. It waits, doing nothing, for a time proportional to a variable D: 73 µs per unit, a little more than one scan line. During this wait the beam moves down and displays the picture normally.
4. It draws three bands. Pen 0, pen 1 and the border all receive the same colour: grey (&40), then bright white (&4B), then grey again. Each band lasts 127 µs, about two lines.
5. Finally, all three receive the dark blue of the background.

When background, drawing and border have the same colour, the picture vanishes, and the bottom of the screen stays plain until the next frame. The picture is thus visible above a bright line, and nothing below.

The whole animation lies in how D changes from one frame to the next. A second variable, IXl, is incremented every frame and added to D: it is a speed that grows steadily, in other words gravity, and the line falls faster and faster. When D overflows (the "floor"), the code sets D to 255 and replaces the speed v with 3 − v (a `CPL` followed by `ADD A,4`). The speed changes sign and loses three units. The line rises again, slowing down, stops and falls again. The successive peaks are 65, 119, 164, 200, 227, 245 and 254: seven ever shorter bounces. When the remaining speed is no more than 3, the loop exits through its other branch, the one that has just restored the picture's colours. The picture then stays fully visible while waiting for the space bar. The effect lasts 176 frames, 3.52 seconds. It is a bouncing ball, applied to a blind being unrolled.

The link between D and the position on screen can be calculated. Vertical sync starts 72 lines before the first line of the picture and lasts 8 lines, and the delay is 73 µs per unit. The first line of the picture therefore corresponds to D ≈ 56. The floor, D = 255, falls about thirty lines below the picture, in the bottom border. Since the border changes colour with the pens, the line stays visible in the border, above as well as below the picture. Colour changes do not fall at the start of a line: each one generally cuts a line in two, which shows at the ends of the line.

Two details of the code are worth noting. Each band sends &8E to the Gate Array (mode 2, ROMs off), which is redundant but guarantees the mode every frame. At the top of the picture, the code uses the alternate registers (`EXX`) to execute `OUT (C),C'`. It relies on a convention of the CPC firmware, which keeps the Gate Array port and the last mode value in BC'. The loader thus restores the state the firmware believes to be current. A last write, `OUT (C),H` with H=&C0, is a standard memory configuration with no effect: the routine seems generic, intended for a third colour this picture does not use.

`rideau.py` ("curtain") transcribes the loop with CPC timings (in µs). It renders each frame line by line, to the microsecond, borders included. The verification compares the model with the emulator: the 5 787 writes to the Gate Array (same order, same values) and the 175 positions of D are identical. Timestamps cannot be compared directly, because the emulator counts raw Z80 T-states. The vertical position of the line in the rendering is therefore accurate to within one or two lines, which changes nothing in the movement. The `OUT (C),C'` is left out of the comparison: in the emulator the firmware has not really run, BC' is zero, and the write goes to another port.

`rideau.gif` shows the effect alone, and `rideau_*.png` a few frames.

## The game's title screen (&542C)

Once started, the game displays its own title screen, and it is static. The credits (programming Andrew Fitter, plot and graphics Daniel Malone, sound design Richard Joseph, © Palace Software MCMLXXXVI) are written by the panel's text routine (&6FBE), above the drawing of the armour's panel.

The only trick is the mode. In play, the interrupt switches the screen from mode 0 (play area) to mode 1 (panel) at the right height. For the title, the game patches the byte at &6F87 (&8D instead of &8C) so that the whole height is in mode 1, and restores it when the game starts. On the game's side, the opening's animation is therefore the music: sounds 1, 2 and 3 on the three channels, a 115.6-second loop, described in `sound/SOUND.md`. Fire starts the game. `analysis/screens.py` renders the title screen.

## The end of the game: shaking and disintegration (&5C31)

The trigger is described in `enemies/PANEL_AND_ENDING.md`: the mine set down on the target in room &00 displays a countdown, and it is the scrolling of this text that, on meeting a "y", calls the final sequence. The sequence combines two effects.

The first is a hardware effect. The game writes 1 to CRTC register 8, which controls interlace. With the value 1, the CRTC shifts vertical sync by half a line every other frame, without changing what it displays. The monitor therefore draws the same picture alternately in its place and half a line lower, twenty-five times per second. On a cathode-ray screen the whole picture trembles vertically: an earthquake made with a single register write.

The effect depends on the hardware. The different CRTC models fitted to CPCs do not all handle interlace the same way, and an emulator or a modern screen may attenuate or ignore it. In `fin.mp4` it is simulated by shifting the picture by half a CPC line (one line of the video) every other frame.

The second is a software effect. The game starts sounds &17, &18 and &19 on the three channels (the rumble of the implosion). It then draws 16 384 numbers at random with the game's generator (&6584, 16-bit congruential). Each number whose high byte, modulo 8, is below 5 designates a byte of the first 16 character rows, that is, of the play area, and that byte is cleared. In all, 10 240 distinct bytes are erased: the room crumbles pixel by pixel, Tal in his armour included. Between two draws, a delay loop (`LD A,&78` then `DEC A / JP NZ`, 480 µs) sets the pace. The game's main loop is suspended meanwhile: nothing moves any more, only the interrupts continue (sound, the two-second task). Measured in the emulator, the disintegration lasts 9.87 seconds, about 600 µs per draw. Register 8 is then reset to 0.

Then comes the final scene (&5CA6). A single object, the armour facing front, moves up and down by one line in the centre of the empty screen, while the panel scrolls the victory message. Fire returns to the title screen.

`fin.py` ("end") replays all this in the emulator from the ending's verification scenario (`enemies/verif.py`). It reads the screen at every frame, with the palette and mode of each interrupt slot, and assembles `fin.mp4` with the sound of the implosion computed by the transcribed driver (`sound/pilote.py`). `fin_*.png` are key frames. The logic of the implosion itself (bytes erased, final scene) was already verified against the game in `enemies/verif.py`.

## What the two effects show

Both effects rest on the same idea: acting on how the picture is displayed rather than on the picture. The curtain draws nothing: it changes three colours at the right moment of the scan. The final shaking moves nothing: it shifts the monitor's synchronisation. This is the culture of the CPC in 1986 and after: the Gate Array and the CRTC, programmable at any moment, offered effects that cost no memory to whoever could count microseconds.

The difference in nature between the two is worth remembering. Palace's effect is a one-line trick laid over a very simple disintegration. CNGSoft's, twenty-seven years later, is a small piece of demo code, timed to the microsecond, with bouncing physics in a few instructions.
