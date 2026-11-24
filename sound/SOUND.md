# Sound and music

*The Sacred Armour of Antiriad* uses neither BASIC's SOUND command nor the Amstrad firmware's sound routines. The game discards the firmware at start-up and drives the sound chip itself, an AY-3-8912 clocked at 1 MHz. It does so with its own program, which has three parts:

- a small interpreter of "scores" coded as bytes;
- instruments defined in software;
- a routine that writes directly to the chip.

This folder contains the verified transcription of that driver (`pilote.py`, "driver") and an audio rendering (`ecouter.py`, "listen", using `cpcarch.ay`). It also produces a score of the title music (`partition.py`, `musique.py`, `gravure.py` "engraving", `export.py`). All of these outputs are generated locally from your copy and never committed. The music is by Richard Joseph.

## Where the driver fits

The interrupt handler is called 300 times per second, six times per frame. At the second and fifth interrupts it calls the driver (&755E), 100 times per second. This rate does not depend on the game loop, whose rate varies from 14 to 19 turns per second: the music stays regular whatever happens on screen. The rest of the game only starts sounds, through a single routine (&752A), which receives a channel (A) and a sound number (L).

At each call, the driver computes for each of the three channels a period (the pitch), a volume and the mixer state (tone, noise, or both). It also computes the noise period, shared by the three channels. It stores these 11 values at &7A50, then sends them to the chip (&78F2).

On the Amstrad, the AY is not wired directly to the processor: it is reached through the 8255 I/O chip. Each register takes four steps:

1. put the register number on port A (&F4xx);
2. give the "select register" order with two bits of port C (&F6xx);
3. put the value on port A;
4. give the "write" order.

The same routine then reads the keyboard, because the Amstrad's keyboard is read precisely through the AY's input port (register 14). Keyboard lines 9 (joystick) and 8 end up at &7A4C and &7A4D, where the rest of the game reads the joystick.

## A sound is a small program

Each sound is a sequence of bytes (table &8AEF, 31 sounds). Each channel has a 46-byte record (&7A5B, &7A89, &7AB7) with its position in the sound, the time remaining, the current instrument and the state of its envelopes. When the current note's time has run out, the driver mutes the channel, then reads the following bytes up to the next note.

| Byte | Effect |
|---|---|
| &00 to &7F | A note: index into the period table (&7974), 96 semitones from C0 (16.35 Hz) to B7; it lasts the current duration |
| &80 v | Base volume (0 to 15) |
| &81 m | Tone only (1), noise only (8) or both (9) |
| &82 | Back to the start of the sound (loop) |
| &83 d | Current duration: d units |
| &84 | Rest of the current duration (the channel stays muted) |
| &85 t | Tempo: one unit lasts 6000 / (8 t) hundredths of a second, as an integer; t is in crotchets per minute, the unit is a demisemiquaver |
| &86 n d₁…dₙ | Compound duration (sum); never used, and wrong: it only adds the first n − 1 values |
| &87 i | Instrument i (15 bytes, table &7AF2, 40 instruments) |
| &88 b | Noise period; if bit 7 is clear, strikes a note at once at the current pitch (percussion) |
| &89 e | Noise period envelope (table &7E49) |
| &8A r | Automatic restart of the envelopes (bit 0 volume, bit 1 pitch, bit 2 noise): tremolo, vibrato |
| &8B | End: the channel is restarted on a non-existent sound and falls silent (see below) |

The chip has a hardware envelope (registers 11 to 13), but the game does not use it. All envelopes are computed by the program, a hundred times per second. An instrument describes two phases for volume and three for pitch. For each phase it gives a number of steps, the value of a step (positive or negative) and the number of calls between two steps.

Two instruments show what this allows. Melody instrument 4 raises the volume by 7 at once (attack), then lowers it by one step every two calls, eleven times. Meanwhile, the pitch drops and comes back up by 3 at the first call, a small "glottal stop" on the attack. Instrument 12 falls back one step every 50 calls; its pitch oscillates by one step every 6 calls and, with automatic restart, this gives a vibrato.

When all volume phases are over, the volume offset returns to zero: the note goes back to its base volume. A long melody note therefore rises to 15, falls to 4, then jumps back to 8 and stays there. Such a fall followed by a jump back sounds like a swell after the attack. The code does not tell whether it was intended.

Percussion is a particular use of the same mechanism. A channel switches to noise only (&81 8). Each strike is an &88 followed by the noise period: 31 for a low drum, 11 for a snare, 1 for a hi-hat, each with its own instrument (17, 15 and 16). There are no samples.

## The title music

The title screen starts sounds 1, 2 and 3 on channels A, B and C (&546D). The loop lasts 11 560 calls, 115.6 seconds, and restarts on all three channels at once. The three sounds together take 1 875 bytes: less than 2 KB for nearly two minutes of three-part music. The piece has three parts, marked by three tempo commands in channel A.

| Part | Length | Tempo commanded | Unit | Tempo heard | Bars as read |
|---|---|---|---|---|---|
| 1 | 47.6 s | 107 | 7 hundredths | 107.1 crotchets per minute | 28 bars of 3/4, plus one beat |
| 2 | 15.6 s | 155 | 4 hundredths | 187.5 crotchets per minute | an upbeat of 3 semiquavers, then 12 bars of 4/4 |
| 3 | 52.4 s | 150 | 5 hundredths | 150 crotchets per minute | 32 bars of 4/4, plus one bar of 3/4 |

The unit is computed with integers. "155" gives 6000 / 1240 = 4.8, truncated to 4: the second part is played at 187.5 crotchets per minute, noticeably faster than the data say. This may be intended, but it may also be an unintended effect of the truncation.

The first part is the theme. Channel A plays the melody. Channel B doubles it, then harmonises it, before switching to percussion from bar 14. Channel C plays the bass, in held notes then repeated quavers. The second part is a fast fanfare, with demisemiquaver arpeggios that imitate chords: since a channel can play only one note, the chord is spelled out very fast. It ends with a scale rising over three octaves. The third part is rhythmic: a low pattern of mixed tone and noise on channel A, the percussion, then held notes.

The division into bars is a reading: the code knows only durations. The first part reads naturally in 3/4, with four-bar phrases. In the other two, the bass changes note every 96 then every 64 units, which leads to 4/4.

## Comparison with the C64 version

A published transcription of the C64 title music (by Stephan Pabst, not included here) and the CPC code give the same piece. The CPC plays it a whole tone higher: G minor (two flats) instead of F minor (four flats). Every note corresponds a tone apart, in the melody as in the semiquaver runs. The tempo is almost the same: 104 to the crotchet on the C64 and 107.1 on the CPC, a value imposed by the 7-hundredths unit. The three-part organisation is the same: melody, a second voice that doubles then harmonises, and a bass in held notes then repeated quavers.

One difference shows in the durations. On the C64, the first bar is a minim tied to a quaver, followed by a quaver. On the CPC, the first note lasts one semiquaver less (18 units instead of 20). The phrase then arrives a semiquaver early up to the long note, which takes back the lost semiquaver (50 instead of 48). This makes syncopations, on all three channels at once. Whether it is a choice of the CPC adaptation or a simplification of the C64 transcription, made by ear, cannot be told from the code.

On the C64 the music is played by the SID, with its own waveforms, filters and hardware envelopes. On the CPC, the AY produces only square waves and noise, and all the colour comes from the software envelopes. The score is the same; the timbre is necessarily different.

## Sound effects

Sound effects go through the same start routine as the music. The driver makes no difference between a musical note and a sound effect.

| Sound | Channel | When |
|---|---|---|
| 1, 2, 3 | A, B, C | title music |
| 4 | C | first entry into the armour (&6147), start-up jingle |
| 5, 6 | C, "D" | end of the start-up (&6085) |
| 7 | A | a message arrives in the panel |
| 8, 9 | B | armour in flight (armour routine, &6446-&64B6) |
| &0A | B | when object 3 shows frame &6E (an animated enemy, &554B) |
| &15 | B | Tal's footsteps (frames 0 and 4 of the walk, &555B) and landing from a jump (&6646) |
| &0B | C | cannon shot (&5682) and pulsar beam (&656B) |
| &0C | C | cell or part collected |
| &0D | C | materialisation of enemies |
| &0E, &0F | B, C | entering and leaving the armour |
| &10, &11, &12 | A, B, C | Tal's rebirth (&5816) |
| &13 | C | contact with an enemy |
| &16 | B | barrier |
| &17, &18, &19 | A, B, C | final implosion |
| &1B to &1D | B | radiation wear, every two seconds: the sound depends on the level (&6F60) |
| &1E | C | stone hitting |

## Three peculiarities of the code

**A channel that does not exist.** At the end of the armour's start-up, the game starts sound 6 on a "channel 3" (&608C), which does not exist. The start routine computes the record's address without checking: record "3" falls at &7AE5, on the noise envelope and the start of the instrument table. Instruments 0, 1 and 2 are cleared for the rest of the game. The only audible effect concerns the title music when it is heard again after a game: channels B and C change from 64.4 seconds on. `antiriad_titre_cpc_apres_une_partie.mp3` gives the rendering.

**An end that is not one.** The end command (&8B) restarts the channel on sound &57, beyond the table (31 sounds). The pointer read falls into the radiation dial's data, but the record is cleared: mixer off, zero duration. The position stays on &8B, and the decremented zero duration becomes 65 535: the channel is silent for eleven minutes, then the &8B silences it again. It is not a real stop, but it has the effect of one.

**Letters read from the sound.** When the message queue empties, the message routine takes the pointer left by the sound routine (&7A5B) and reads its "next letter" from channel A's record (see `enemies/PANEL_AND_ENDING.md`).

## Verification

`verif.py` runs the real game in the emulator. At every driver call, it applies the model to the memory image taken at entry and compares the result with the game, just before the values are sent to the chip: the 11 registers, the three channel records and the noise envelope. It also runs the model continuously, without resynchronising. The tests cover 14 000 calls of the title music (140 seconds, more than one complete loop) and 2 × 2 880 calls of in-game sound effects (two rooms, stones, enemies, jumps). Everything matches. The static decoding used for the score (`partition.py`) was cross-checked with the verified driver: the 736 notes and strikes of the three channels are identical, in onset and pitch.

## Generated files

| File | Contents |
|---|---|
| `antiriad_titre_cpc.pdf` | The score of the title music, 75 bars, engraved by `gravure.py` |
| `antiriad_titre_cpc.musicxml` | The same, to open in MuseScore, Finale or Sibelius |
| `antiriad_titre_cpc.mid` | The same in MIDI (percussion on channel 10) |
| `antiriad_titre_cpc.mp3` | Audio rendering: registers computed by the verified driver, rendered by `cpcarch.ay` |
| `antiriad_titre_cpc_apres_une_partie.mp3` | The same, after the corruption of instruments 0 to 2 |
| `mise_en_route_armure.mp3` | The jingle of the first entry into the armour (sound 4) |

The audio rendering approximates the chip. It produces perfect square waves and uses a published AY volume table and a 17-bit noise generator, without the filtering of the Amstrad's output. Channels are spread as on the stereo socket: A left, B centre, C right. The registers, however, are exactly those the game sends.

The engraving is done by a small engraver written for the purpose. It draws beams per beat, ties, accidentals and cross noteheads for percussion. Notes too far from the staff are written an octave off (8va, 8vb). For careful layout, open the MusicXML file in MuseScore.
