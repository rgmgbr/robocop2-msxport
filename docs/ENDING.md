# The game completed and the high scores

The end of the game (WELL DONE, the CMP tune) and the high-score table with its name entry, after
every game over and after the ending. [V] marks what was read in the original's code or measured;
[D] the port's design as built. The checks, with their commands: `docs/level3/HANDOFF.md`, "Step 3".

## 1. The original [V: REA (Ghidra 12.1.4, raw-binary m68k, entry `0x0`, `analysis/ghidra_seeds.tsv`) on `build/ram/level3_full.bin`; the main code `$8000-$17FFF` is the same bytes in the three level images]

**The way in.** `level_load_3` `$86DE` (load-table entries 3 and 7: `level_init` with `$8050` = 3
after level 3; no statistics, no bonus stage): `lea $112C5,A0` / `jsr $10762` / `jsr $11C54` /
`jsr $12082` / `bra $8090` (the stack reset, then `$8098`: the title).

**The text screen `$112C5`** (through `$10762`: the music stopped at its start, the palette black
at its end): particle set-up 7, "  WELL DONE" (colour set A, origin (32, -24): 1 + 106 calls), then
"YOU HAVE DEFEATED ROBOCOP 2," (column 4, row 1), "AND THE SUPPLY OF NUKE HAS BEEN" (2, 3),
"STAMPED OUT." (12, 5), a wait of 160 calls, the end: 341 calls; fire ends it from VBL 50.

**`$11C54`, the tune.** PICF loaded at `$6FFA0` and shown (copper `$123EA`); CMP loaded at `$18000`,
its init, stop all and tune 1; then a loop of 1801h passes, one a frame (raster line `$C0`), which
ends at once on fire (`read_joystick` bit 4, no release needed). The tune is ticked on 4 of every 5
passes (`$11C52` from 0: `subq` / `beq` skip / `bpl` tick / else 4 and tick): **4,916 ticks in the
6,145 passes** (102.4 s at 60 Hz). CMP tune 1 is 4,800 ticks long and its audible loop starts at
tick 192 (`tools/rc2music.py`): the original plays it once and the loop's first 116 ticks. Its
instrument 16 (sample 1, 6 key-ons) measures as speech (`docs/ROM_BUDGET.md` 3.9).

**The game over** (`main_loop` `$82A8-$82E0`): PIC9 (`show_picture` D0 = 8: 251 VBLs or fire), 128
VBLs, `high_score_entry`, `$11FD2` (the continue offer); fire then `$FFD8` (two lives) and
`level_init` (the same level, the score kept), else `$8098`.

**`high_score_entry` `$12082`.** `st.b` `$15EF` (the key latch), `$8032` (the key byte: FFh, no
key), `$15EA`; the score `$8046` (a BCD long) as 8 characters '[' + digit at `$1207A`; its low 7
digits against entry 6's (`$12070`) digit by digit: **only a greater score enters**. Entry 6 = those
digits and 9 spaces; `$12300` (copper `$10356`, HI1 loaded at `$18000`, its tune 1 started);
`$1215C` (the name); the fade out (one VBL: the palette is black already); then 24 bubble passes
of 5 comparisons, 18 bytes swapped when the upper score is the lower: **ties keep the older entry
above**. Then `rts`: nothing shows the table here; the title's attract cycle writes it with the
particle writer (particles 0 and 1, 1 + 373 calls each) every 1,094 frames.

**The table** `$11FF6`, in the code (RAM only: from the power-on until the power goes): "   TODAYS
BEST " CR, 6 entries of 19 bytes (' ', a name of 9, ' ', 7 digits '[' + digit, CR), FF 00. Defaults:
IAN 100000, KAREN 90000, COLIN 50000, KEITH 45000, ANDY 9000, PAUL 7500.

**The name entry `$1215C`.** Script `$115C9` through `$10768` (its `$FE14` stops the music before
HI1's first tick: tune 1 is never heard): "YOU HAVE A HIGH SCORE." (column 9, row -1), "ENTER NAME
ON THE KEYBOARD" (7, 5), "USE BACKSPACE TO DELETE" (8, 7), "RETURN TO FINISH." (12, 9), 92 calls,
fire from VBL 50. The name is entry 6's (`$12066`): 9 spaces, and the mark 'g' (glyph '?') under its
**second** position; `$12218` draws it through `$118CE` at column 16 + i, row 10 with the front buffer
as the text origin: bitplane x 128 + 8i, lines 80-87 (off the text grid's rows). Then a key at a
time (`$1225C`): Return (0Dh) ends; Backspace (7Fh), past the start, puts the mark on the last
character and a space after it; any other is ignored once 9 are typed, else goes at the next
position with the mark after it (none after the ninth). Return: the marks cleared, `$16CD` = 1 and
one fade step (the palette black at once), both buffers cleared (`$BCA8`), effect 4.

**`$1225C`, a key.** One a press: `$8032` (the keyboard interrupt's last raw code; bit 7: none or a
release) negative clears the latch `$15EF`; with the latch set the loop waits; else the latch is set
and the code looked up in `$122C8` (A-Z, the main row's 0-9, the keypad's 0-9, space, Backspace
`$41`, Return `$44`, `$2B`), its character from `$12296` (A-Z, '['-'d' for both rows of digits, ' ',
7Fh, 0Dh, 0Dh) into `$15EA`, and effect 3; a code not there waits too. **No joystick, no timeout.**
HI1's effects 3 (6 ticks) and 4 (14 ticks) sound on channel 3 (the VBL ticks HI1: `$10320` =
`$18018`).

## 2. The port [D]

**Flow.**
- The ending: `msx/ending.asm` `front_ending`, reached only through `frontx.asm` `fr_ending`
  (`ld hl,fr_ending` / `call front_call`, then the title: `rc2.asm` `ml_ttl`), **the one way in that
  level 3's end calls** (`rc2.asm` `ml_ev`'s `ml_end`, AG `$8050` = 3, since level 3's step A; the
  interim call after the level-3 briefing, `frontx.asm` `fb_brief2`, is gone: `front_bonus` calls
  `front_brief` again and level 3 follows the briefing).
- The game over: `front_over` (PIC9, 30 s or fire), then `frontx.asm` `fo_hsc`: `hs_entry`, then
  `front_cont` (after an entry, its display set-up left out: the display is on and the HUD stays).
- Builds with a script (`EXTJOY`, `JOY`) skip the ending and the entry as they skip the title (their
  drives type no name: every trace flow stays the base's); `PZ_TEST` builds skip the ending.

**Screens** (the text screens' engine: `front.asm` `fs_step`, `fs_char`, `fs_tick`, the HUD below,
`TAG`'s TEST n at row 10; `tools/msxtext.py`, its output `ending.inc`):
- WELL DONE: `txt_end`, its particle title typed at column 11, row -3 as the briefings' are, then the
  original's lines and wait: 341 calls, fire from tick 50.
- The tune: CMP tune 1 (`tune.asm` `tn_cmp`) while the WELL DONE screen stays on, until the tune's
  end (`tn_left` 0: 4,916 ticks and the end's, 98.3 s at the port's 50 ticks a second) or fire pressed
  once released; then the play area black and silence.
- The name entry: `txt_hisc` (the original's bytes, 92 calls), the name's 9 cells at x 96 + 8i, lines
  80-87 (`hs_draw`), the mark under the second position at the start, the original's rules for Return,
  Backspace and a full name; a key at a time from the MSX keyboard (`kb_char`: the matrix, MSX2
  Technical Handbook figure 5.17B; A-Z, the main rows' and the keypad's digits stored as '['-'d',
  SPACE, BS, RETURN), one a press (`hs_lat`: every key released before the next); effect 3 a key,
  effect 4 at Return, which blacks the play area. No joystick and no timeout, as the original.
- The table (`hs_best`): TODAYS BEST and the 6 entries typed at once in the 8 x 8 font, each line at
  column 11 (the stroke text's centre), rows -4 to 8 (the original's 16-line pitch), for the
  attract's 748 calls; fire from tick 50.

**The table** in RAM (`msx.inc`): 6 entries of 13 bytes (the name's 9 characters, the score's 7
digits as 4 BCD bytes), entries 0-2 at `hs_tab0` C5D0h, 3-5 at `hs_tab1` C2D9h, from `hs_def`
(`$12006`'s defaults) at the power-on (`ci_hook`). The entry takes the score's low 7 digits, enters
only above the last entry's, and moves up past every lower score (the bubble passes' result).

**Sound** (`tools/msxtune.py --end` -> `build/msx/end.bin`, 27,110 B, pzm.bin's layout): CMP tune 1
unrolled to the 4,916 ticks the original plays, in the three versions with the stages' converters
(SCC 12,797 B with the drums on PSG C; OPLL 8,793 B, its drums BDRM as BD, SNARE as SD, CLOSEDHAT
as HH, sample 7 as TCY; PSG 5,287 B); its speech instrument silent (it waits for the user); HI1's
effects 3 and 4 at CMP's reference as effects 3 and 4 of the same blob (`snd_ffx`). The name entry
starts the same descriptor with its tune cut to no tick (`tn_left` 1).

**Code, banks, RAM.**
- `BANK_FRONT2` (bank 127, A000h: a bank the 3Fh rule leaves to code and data read at A000h):
  `msx/ending.asm` and `ending.inc`, 1,151 B (7,041 free). `end.bin` in banks 128-131: **the image is
  2 MiB** (132 of 256 banks) with the boot guard (`rom_guard`, now in `frontx.asm`).
- FRONT: `msx/frontx.asm` after its code and tables (`front2_call`, `fr_ending`, `fo_hsc`,
  `ci_hook`, `rom_guard`); the calls that reach them replace calls of the same size (`front_over`,
  `cold_init`; `front_bonus`' until level 3's step A), so nothing in FRONT moves: 1,173 B free (as
  built by the ending's step).
- MUSIC: `tn_cmp` after `tune.asm`'s code, its descriptor `tune_cm.inc` after it (Brainstorm's and the
  range's keep their bytes): 1,251 B free. The fixed area: unchanged, 181 B free.
- Every other bank keeps its bytes (`tools/bstest/romdiff.py --blocks`: 37 blocks identical).
- RAM: the table (78 B: C2D9h-C2FFh, C5D0h-C5F6h), the entry's work in `fs_buf` (`hs_i`, `hs_lat`,
  `hs_sc`, `hs_ran`).

**Defaults** (where nothing covered the choice; the safest that changes nothing that works):
1. The tune's length: the 4,916 ticks the original plays, at the port's 50 ticks a second (every
   tune's: `docs/RANGE.md` default 25), the screen ending with them (98.3 s; the original 102.4 s at
   60 Hz). The PAL timing (6,145 ticks) would have repeated 27 s of the loop.
2. **While the tune plays the WELL DONE screen stays on**: PICF is dropped (decision 5), and a black
   play area for 98 s would look stopped; no new content.
3. **The table after an entry**: the original shows it only in the title's attract, which the port's
   title has not (the title is frozen); the port shows it once after each entry, as the attract's
   write and unwrite of it (748 calls, fire from 50). Without an entry nothing, as the original.
4. Fire on the tune: pressed once released (PIC9's rule): without the original's disk loads, fire
   held from the WELL DONE screen would skip the tune at once.
5. The keyboard by its matrix position, as the original reads the Amiga's raw codes by position.
6. Effect 4 is heard out (16 ticks) before the next screen's stop.
7. Builds with a script skip the ending and the entry (as the title).
8. The name entry's last line keeps the original's row 9; a `TAG` build's TEST n is right below it.
9. The OPLL's rhythm takes CMP's hat as HH and sample 7 as TCY (the stages use BD, SD and TOM only).

**Test options** (`tools/mkrom.py`): `END_TEST=1` starts at power-on with the ending (after level 1's
set-up, `LV_CARRY`'s score, lives and credits; then the title and a new game: the way level 3's end
will reach it); `END_TEST=2` with a game over (PIC9, the entry, the continue offer with `LV_CARRY`'s
credits: a continue restarts level 1).

## 3. Checks [V] (details and commands: `docs/level3/HANDOFF.md`, "Step 3")

- The screens pixel for pixel against `tools/msxtext.py`'s renders, R#0 16h, R#1 62h and the palette
  at each (`tools/bstest/ending.tcl` `ge_job`, `tools/bstest/endcheck.py`): WELL DONE, every wait of the
  name entry against a model of `$1215C`, the table against a model of `$1211C`, the continue offer
  after an entry, on five machines, with `TAG=8`; the table in RAM after each entry.
- The tune and the effects register-exact against `end.bin`'s streams in the Z80 interpreter, four
  chip sets at 50 and 60 Hz, and on the R800 without the OPLL (`tools/bstest/frsnd/endsim.py`); the
  tune's 4,917 ticks to its end in the emulator.
- The flows through the gate's records: the title from power-on, the product's whole flow and the
  title after the ending, level 2's continue checks, the cheat run; the 2 MiB guard; the matrix.
