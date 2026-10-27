# Brainstorm: the first bonus stage after level 1

Written on 2026-10-27 as the plan for the night the user asked for the next phase ("prossiga com a
implementação da próxima fase"), and updated the same day to what was built: milestone 1, the stage
playable after level 1 with the original's logic and graphics (commits `ac31d65` to `b59a338`), and
milestone 2, its music and effects (the branch `bs-sound-int`: section 5). Milestone 3 (the second
visit's face) is still a plan.

The user's orders for that night:
- **the ROM must stay within 2 MiB** (mandatory);
- **nothing that works in level 1 changes**: its mechanics, the title screen and its music;
- a **test ROM ready in the morning**.

Base: five area reports of the same night (flow, logic, graphics, sound, bench: section 9) on the
repository at `52149b0`, whose ROM is byte-identical to `build/msx/ROBOCOP2_v0.1.3-test1.ROM`.

Tags:
- **V**: verified: by REA (Ghidra provider) on the RAM image with PUZL at `$17100`, by data, by a
  bench run of the original, by the MSX source, or by an openMSX run of the port (section 4);
- **I**: inferred, not confirmed by a run;
- **D**: a design decision for the port;
- **E**: estimated.

## 1. Summary

- **What it is [V].** After level 1's statistics the original runs Brainstorm (`$8382`): an
  intro text, PIC3, then PUZL (`$17100`), a chip puzzle on an 11 × 8 board. The cursor moves one
  cell per joystick change and burns every cell it enters; entering a red chip destroys it
  (+100 points). Four boards of 1:00 each. Solved: a game credit (`$805E` + 1). Stuck with red
  chips left: "MEMORY MALFUNCTION". Time out: "OUT OF TIME". Then a result text.
- **The port, as built [D, V].**
  - `msx/rc2.asm` `ml_ev` (FE_NEXT only) runs `front_stats`, then `front_bonus` (FRONT), then the
    title and a new game, as before. `front_stats`, the title and level 1 keep their code (only
    addresses moved) and their behaviour: level 1's traces, the title's picture and music, and a
    new game are checked equal to `52149b0`'s (4.4).
  - `front_bonus` is `$8382` without PIC3 (decision 5): the intro and result texts through
    `front_stats`' engine (`fe_text`), and the stage `bs_stage` (`msx/puzl.asm`) in a code bank of
    its own, **`BANK_PUZL` = 78**, mapped at A000h. Its graphics are in banks 79-85.
  - The stage is PUZL ported routine by routine, one pass per 50 Hz tick. Its variables live in
    the mirror (`AM + $B00-$B21`), and the MSX traces equal the original's in all 399 compared
    values of every pass of nine drives on an MSX2 and a turbo R (its Z80), and of the full solve
    also on an MSX2+ and at 50 Hz (4.1).
  - The screen is the original's art 1:1, re-laid out in 8 pieces into the 256 × 162 play area,
    with the HUD below it as on the Amiga. It is double-buffered on VRAM pages 0 and 1: no block
    is seen half drawn (a board's set-up draws with the palette black), and no pixel outside the
    elements changes (4.2). The cursor is 1-2 hardware sprites; everything else is VDP HMMM
    copies. About 30 pictures a second at 60 Hz and 28 at 50 Hz.
  - The sound is the original's (3.6): PZM tune 1 at every board and effects 3-6 under `$1822C`'s
    rule, converted by `tools/msxtune.py` and played by `msx/tune.asm` on the chips the machine
    has, as the title music: the SCC (the melody; the drums on the PSG, or on the OPLL's rhythm),
    the OPLL alone (MSX-MUSIC, FM-PAC) or the PSG alone. A board's set-up ends with the tune, whose
    first tick waits for the next pass, so the jingle of boards 1-3 starts with it as on the
    Amiga. The fixed area did not grow (`fx_tk`'s operand only), and the title's and level 1's
    sound are unchanged, write for write [V: offline, in a Z80 interpreter on the images, and in
    openMSX on every chip set (4.3)].
  - Graphics are stored raw (no decompressor). The ROM uses **88 of its 128 banks: 1 MiB** (the
    music and effects in banks 86-87), far within the mandatory 2 MiB (3.10).
- **Not yet.** A second visit (`PZ_LEVEL=2`) plays visit 2's boards with visit 1's face and
  palette (milestone 3). The shooting range and level 2 come later. The sound waits for the
  user's ears on real hardware (the test3 candidates; 3.6, 4.3).
- **Test builds (section 6).** `PZ_TEST=1` starts in Brainstorm at power-on, for the user's quick
  test and for the trace harness; `TAG=n` marks a test candidate. The product's flow does not
  depend on them. The morning's four candidates (step 8) are the product and the `PZ_TEST=1` ROM,
  each as a 1 MiB image and as a 2 MiB one (`ROM_2M=1`), all with `TAG=2`, all silent (built before
  milestone 2).
- **Defaults for the user to review (section 7).** Section 7 lists the 16 choices made while the
  user slept, each with its alternative. By number:
  - still the user's call: 2 (on a turbo R the screen, HUD included, goes black for about 0.1 s
    between the statistics and the intro) and 14 (visit 2's palette reset, milestone 3);
  - built, and visible in play: 1 (50 passes a second on 60 Hz machines too), 3 (the intro's long
    line split over two rows), 4 (the HUD's messages tick on during the bonus texts), 5 (the
    stage graded like game play), 7 (the end sequence's junk cursor hidden) and 8 (the TV face's
    duty rule at about 30 pictures a second);
  - built, and heard in play: 12 (effect 6 designed as the buzz its restarts make) and 13 (effect
    3 kept, refused by the rule as on the Amiga);
  - inside the port, or for the later milestones: 6, 9-11, 15 and 16.

## 2. The original

### 2.1 The flow around the stage [V]

| Step | Address | What |
|---|---|---|
| 1 | `$81B8` | `main_loop`: the level done, `$8050` + 1, then `level_init` `$871A` |
| 2 | `$86FA` entry 5 | `level_init` jumps to `load_level1` `$8582` |
| 3 | `$8588` | statistics `$85D8` (script `$1132F`): ported, `front_stats` |
| 4 | `$858A` | **Brainstorm `$8382`, D0 = 2** |
| 5 | `$8590` | shooting range `$8420` (D0 = 1): later |
| 6 | `$8596` | 3 `nop`s where a 6-byte call was. **I**: the disk-2 prompt `$11BD2` (the crack) |
| 7 | `$859E`-`$85C4` | level-2 briefing `$110F0`, PIC4, MU1, MADEX, DATAL2: later |

`$8382` (136 bytes):

| Address | What |
|---|---|
| `$8384` | intro text `$114AA` through `$10762` (the text loop, then `$FE14`) |
| `$8392` | PIC3 (`show_picture` `$11E06` with D0 = 2, 251 frames or fire): **dropped** (decision 5) |
| `$8398` | `$10320` = `$1032E`: the VBL's music tick becomes an `rts` |
| `$83AC`-`$83CE` | loads "PUZL" (`$8416`) through the loader `($C0)`; on visit 1 (`$8050` < 2) `$124A6` decrunches `$17080` → `$17100` |
| `$83DE` | **`jsr $17100`** → D0 = 0 solved, 1 failed, 2 out of time |
| `$83E4` | PUZL's player: init `$18000`, stop all `$18004` |
| `$83FA` | D0 = 0 → `$805E` + 1 (a continue) |
| `$8400` | result text: `$840A`[D0] = `$1162F` / `$11667` / `$11698`, through `$10762` |

What the rest of the game reads afterwards: only `$805E` and the score `$8046-$8049` [V]. Every
other value is reset by the result screen's `$FE14` (`clear_game_vars`), by `level_init` or by
`$8420`.

The text screens [V] (bytes read from `build/ram/level1_full.bin`):

| Script | Text (row: column) | Bytes | Calls | Frames without fire |
|---|---|---:|---:|---:|
| `$114AA` intro | 0: 13 "BRAINSTORM." / 3: 2 "DESTROY ALL RED CHIPS ON THE BOARD" / 5: 5 "COMPLETE 4 TO REGAIN MEMORY." / 7: 7 "AND EARN A GAME CREDIT." / `FF 02 30` / `FF 07` | 113 | 292 | 293 |
| `$1162F` solved | 0: 6 "WELL DONE MEMORY RESTORED." / 3: 9 "GAME CREDIT AWARDED" / `FF 02 18` / `FF 07` | 56 | 143 | 144 |
| `$11667` failed | 0: 9 "MEMORY MALFUNCTION." / 2: 9 "ATTEMPT TERMINATED." / `FF 02 18` / `FF 07` | 49 | 136 | 137 |
| `$11698` out of time | 0: 12 "OUT OF TIME." / 2: 9 "ATTEMPT TERMINATED." / `FF 02 18` / `FF 07` | 42 | 129 | 130 |

- They use only positions, characters, `FF 02 n` and `FF 07`: what `front_stats`' engine handles.
- With fire, a screen ends at its first call from the 50th on.
- The status panel stays shown below every text screen, and the VBL handler `$10266` keeps
  ticking the panel's messages there.

### 2.2 The rules [V: REA, bench, executable model]

- **Board.** 11 columns × 8 rows. The low nibble of a cell is its type: 0 a red chip, 1 an IC (a
  wall), 2-14 tracks, 15 unused. A cell the cursor has been on gets + `$10` and is blocked.
- **Moves.** One move per change of the joystick byte `$802E` against `$B1E` (the whole byte, fire
  included). The lowest direction bit wins: up 1, down 2, left 4, right 8. A move onto a wall, a
  visited cell or past the edge is refused, and that pass makes no stuck check. Holding a
  direction moves once; toggling fire while holding it moves again.
- **Red chip.** Checked one pass after the move that entered the cell: +100 BCD (`$F6A0`, D2 =
  `$100`), effect 3, `$B10` − 1, and `$B17` set when no red chip is left.
- **Stuck.** A pass without a move attempt checks the four neighbours. None free and `$B17`
  clear: "MALFUNCTION.", `$B16` set: result 1.
- **Time.** Each board sets 1:00 (`$F9DC`). The CIA-B handler `$1015E` counts down in BCD and sets
  `$804C` below 0:00: "TIMEOUT." every pass, result 2. The time out comes on the 61st tick after
  the set-up.
- **Visits.** Only `$8050` ≥ 2 picks the second set: boards `$175C0` instead of `$17448`, palette
  `$17DAA` instead of `$17D6A`, Ellen's face `$25160` instead of Murphy's `$244E0`. No other
  difficulty parameter. No random numbers.
- **End.** After the 4th board: "MEMORY RESTORED.", the face shown clean, result 0.

### 2.3 Entry and loops [V]

```
puzl_main $17100:
    music_init ($18000); init_hw $17D1A ($FE14, $B00-$B21 = 0, own level-3 handler, copper $17BFC,
        $B19 = 0, $B20 = FF: fade in)
    setup_timer($0059) ($8018; board 0 replaces it); $804E = 0
    plane 5 set over the face window ($313BC: display only)
    visit by $8050 >= 2: patches $173D4 (boards), $17B20 (palette), $1729A (face)
    $B0A = -2
next_board $17184:
    D0 = $B0A + 2; D0 >= 9 -> return 0
    board_setup(D0 / 2) $173D2
loop $171BA: wait for $802C (one pass per frame)
    $171C2: COLOR00 = 0; $B12 = $17DE8 + word[$17194 + ($B00 & $1E)]   (cursor frame)
    fade $17AF0; draw_face $17298; draw_led $17944; draw_timer $1797C
    step $17760                                                       (the game)
    $B02 += 3; $B00 += 1
    music tick $18018 on 5 passes in 6 ($17282)
    draw_decor $179FC; message_ticker ($8020); read_joystick ($801C); panel digits ($8004)
    end checks $17230:
        $B1A not 0 and below 99 (cmpi.w #$63; bmi: signed): loop
        $B17 or $B16 ($17264): $B04 = 6, $B20 = 0; fade not 0: loop; $B17: next_board; else return 1
        $804C clear: loop
        $17254: $B20 = 0; fade not 0: loop; return 2
```

- The pass rate is one per frame: the game's copper part `$10356` raises SOFT at line `$CE`, and
  `$101CC` adds 1 to `$802C`.
- The step uses the joystick byte read at the end of the previous pass.
- In pass n, `$B00` = n and `$B02` = 3n up to the step; the decor and the panel see n + 1.

The game itself, as the logic report's spec gives it (the Z80 port follows it literally: signed
word compares where the 68000 uses `bmi`/`bpl`, 16-bit wrap of `$B00`, `$B02`, `$B1A`):

```
board_setup(n) $173D2:
    A4 = boards + 94 n; if n != 0: $B04 = 5
    $B0A = 2 n; $B0D, $B0F, $B11 = header bytes 0-2 (high bytes stay 0)
    setup_timer(header bytes 3-4: BCD MM SS); tune = header byte 5; $B06 = A4 + 6
    each of the 88 cells &= $0F, drawn                ; ($B1A, $B16, $B1E, $B19 are NOT reset)
    $B20 = FF; $B17 = 0; stop all; start the tune as music

step $17760:
    if $804C: message_queue("TIMEOUT."); $B1A += 1
    if $B1A: $B12 = $17FE8; $B1A += 1; return             ; the end sequence
    if $B04: start effect $B04; $B04 = 0
    D0 = $B0C; D1 = $B0E; A4 = cell(D0, D1)
    if (A4) == 0: add_score($100); $B04 = 3; $B10 -= 1; $B17 = ($B10 == 0) ? FF : 0
    (A4) |= $10; draw it
    if $B17 and $B0A == 6: $B0A = 8; $B1A += 1; D0 = message_queue("MEMORY RESTORED.")  ; quirk 1
    if $802E != $B1E:
        $B1E = $802E
        up    (bit 0): if D1 == 0: return; D1 -= 1; if blocked: return; $B0E = D1; $B04 = 4; return
        down  (bit 1): if D1 == 7: return; D1 += 1; ...; $B0E = D1 ...
        left  (bit 2): if D0 == 0: return; D0 -= 1; ...; $B0C = D0 ...
        right (bit 3): if D0 == 10: return; D0 += 1; ...; $B0C = D0 ...
        (a change without a direction bit falls through)
    if stuck(D0, D1) and $B17 == 0: message_queue("MALFUNCTION."); $B1A += 1; $B16 = FF

cell(D0, D1) $178E8:  A4 = $B06 + 11 D1 + D0 (no bounds check)
                      blocked = (signed byte)(cell - $10) >= 0 or cell == 1
stuck(D0, D1) $178A4: no neighbour (left, right, up, down, inside the board) that is not blocked
fade $17AF0:          $B20 ? (up to $1F) : (down to 0, and at 0 the palette pointer = $17D6A)
                      COLOR01-31 = palette with each component limited to ($B19 >> 1) & $1E
CIA-B $1015E:         unless $804E: seconds - 1 (BCD); below 0 minutes - 1 and seconds $59;
                      below 0:00 $804C = FF, the timer stays 0:00
```

### 2.4 The routines [V]

| Address | Name (`analysis/puzl_17100.sym`) | Role | 68000 bytes | Port (`msx/puzl.asm`) |
|---|---|---|---:|---|
| `$17100` | `puzl_main` | entry, visit, board loop, frame loop, end checks | 354 | `bs_stage`, `bs_next`, `bs_loop`, `pz_frame` |
| `$17D1A` | `puzl_init_hw` | `$FE14`, variables cleared, vectors, copper | 78 | `bs_stage`'s entry |
| `$173D2` | `puzl_board_setup` | header → cursor, red chips, timer, tune; 88 chips drawn; stop all; tune | 118 | `bs_setup` (+ `bs_board`) |
| `$17760` | `puzl_step` | time out, end count, effect, red chip, burn, moves, stuck | 316 | `bs_step` |
| `$178E8` | `puzl_cell` | cell address (no bounds check); blocked = visited or type 1 | 38 | `bs_cell`, `bs_blk` |
| `$178A4` | `puzl_stuck` | no free neighbour | 76 | `bs_stuck` |
| `$17AF0` | `puzl_fade` | `$B19` ± 1; COLOR01-31 limited; palette pointer reset | 108 | `bs_fade` |
| `$17298` | `puzl_draw_face` | TV: face or black, then a static frame | 226 | `bs_tv` (the wanted TV) |
| `$1737A` | `puzl_draw_chip` | 16 × 16 chip at (16 + 16c, 16 + 16r) | 88 | the renderer's cell copies |
| `$1790E` | `puzl_draw_glyph8` | 8 × 16 digit (CPU) | 54 | the renderer's digit copies |
| `$17944` | `puzl_draw_led` | one LED digit a pass | 46 | `bs_led` (the wanted LED row) |
| `$1797C` | `puzl_draw_timer` | the board's timer digits | 58 | `bs_tmr` (the wanted timer) |
| `$179FC` | `puzl_draw_decor` | button, scanning light, board bar | 226 | `bs_decor` (the wanted decor) |
| `$17B5A` | `puzl_irq_copper` | bitplane pointers, sprite 0 = the cursor | 144 | the renderer's SAT (`rd_sat`) |

Two pieces of code inside the data ranges the logic report proposed for the symbol file, found
with REA on 2026-10-27 [V]:
`$17AEE` is the `rts` the fade branches to at either end of its range (from `$17AFE` and
`$17B0A`), and `$17D04-$17D19` is an RTE handler that acknowledges EXTER (INTREQ `$2000`) and that
nothing references (no xref, and its address is in no byte of the image).

Main-code services PUZL calls (`$8004-$8028` table) and the port's equivalents:

| Entry | Routine | Port |
|---|---|---|
| `$8004` | `$F6B8` panel_update_digits | `hud_frame` (through `hud_keep`) |
| `$8008` | `$FD76` message_queue | `game_msg` → `hud_message` |
| `$800C` | `$F6A0` add_score | `add_score` (`logic.asm`), DE = `$0100` |
| `$8018` | `$F9DC` setup_ciab_timer | `bs_timer` (AG `$804A`, `$804C` = 0, `sec_n` = 0, `pz_last`) |
| `$801C` | `$BDEC` read_joystick | `joy_read` (`player.asm`) |
| `$8020` | `$FDA2` message_ticker | `hud_frame` (through `hud_keep`) |
| `$8028` | `$FE14` | `bs_stage`'s entry (palette black, variables cleared) |

### 2.5 State [V]

| Address | Size | Name | Meaning | Port (`msx/msx.inc`) |
|---|---|---|---|---|
| `$B00` | w | frame | passes so far | `pzv_frame` |
| `$B02` | w | frame3 | + 3 a pass (LED digit, bar blink) | `pzv_frame3` |
| `$B04` | b | sfx | effect request, played by the next pass's step | `pzv_sfx` |
| `$B06` | l | cells | the board's 88 cells | `pzv_cells` (low word: `pz_boards` + 6 + 94 × board) |
| `$B0A` | w | board2 | 2 × board; −2 at first, 8 once the 4th is done | `pzv_board2` |
| `$B0C` / `$B0E` | w | col / row | the cursor | `pzv_col`, `pzv_row` |
| `$B10` | w | reds | red chips left | `pzv_reds` |
| `$B12` | l | cursor_img | `$17DE8` + frame; `$17FE8` during the end sequences | `pzv_curimg` (low word: the offset from `$17DE8`) |
| `$B16` / `$B17` | b | failed / done | | `pzv_failed`, `pzv_done` |
| `$B19` | b | fade | 0-31 | `pzv_fade` |
| `$B1A` | w | end_count | 0 in play; counts the end sequence to 99 | `pzv_endc` |
| `$B1E` | b | prev_joy | the joystick byte of the last change | `pzv_prevjoy` |
| `$B20` | b | fade_in | FF fade in, 0 fade out | `pzv_fadein` |
| `$802E` | b | joystick | up 1, down 2, left 4, right 8, fire `$10` (keyboard byte when 0) | `g_joy` |
| `$8046-$8049` | 4 b | score | BCD | AG |
| `$804A` / `$804B` | b | timer | minutes, seconds (BCD) | AG |
| `$804C` | b | time_out | FF below 0:00 | AG |
| code | | patched immediates | boards `$173D4`, palette `$17B20`, face `$1729A`, tune `$17441` | `pz_boards`' copy, `pz_pal`, `pz_tv`, `pz_tune` |

### 2.6 Boards and tables [V: REA read_bytes, decoded]

Eight records of 94 bytes at `$17448-$17737`: start column, start row, red chips, timer (BCD
word), tune, then the 88 cells row by row. The three messages follow (`$17738-$1775E`), then a pad
byte (`$1775F` = `$08`).

| Visit | Records | Start | Red chips | Timer | Tune |
|---|---|---|---|---|---|
| 1 (after level 1) | 0-3, `$17448` | (0, 0) | 22 / 21 / 24 / 28 | 1:00 each | 1 |
| 2 (after level 2) | 4-7, `$175C0` | (5, 3) | 23 / 21 / 24 / 28 | 1:00 each | 1 |

Each red-chip count equals the number of type-0 cells. A full solve scores 9,500 (visit 1).

| Address | Table |
|---|---|
| `$17194` | cursor frame offsets × `$40`: 0 1 2 3 4 5 6 7 6 5 4 3 2 1 0 0 |
| `$17284` | face masks by board: 7 3 1 0 0 |
| `$1728E` | static shifts by board: 1 1 1 2 0 |
| `$17972` | LED thresholds by board: 0 3 6 8 10 |
| `$179B6` | LED values: 0 1 8 6 4 5 4 7 2 4 8 5 3 0 2 6 |
| `$17ADE` | light/bar rows × 320: 0 1 2 3 3 2 1 0 |
| `$17D6A` | COLOR01-31, visit 1: 222 444 666 888 AAA EEE 400 800 E20 020 040 480 620 A60 CA4 000 876 865 754 543 432 321 210 444 644 533 322 443 332 112 010 |
| `$17DAA` | COLOR01-31, visit 2: 222 444 666 888 AAA EEE 400 800 E20 020 040 480 620 A60 CA4 111 DCC EBA DAA D99 333 532 444 555 A9A 756 666 B87 878 965 CAA |
| `$17738` / `$17741` / `$1774E` | "TIMEOUT." / "MALFUNCTION." / "MEMORY RESTORED." (`FF`-ended; the font's '.' is `e`) |

`tools/msxpuzl.py` checks the tables and both palettes against this section on every conversion.

### 2.7 End sequences [V: bench]

| Event in pass j | Then |
|---|---|
| boards 0-2: last red chip | effect 6 started in each pass j+1 … j+31 (the fade-out); the next set-up at the end of pass j+31; pass j+32 starts effect 5 and fades in |
| board 3: last red chip | `$B1A` 1 → 99 by pass j+98; fade-out; **result 0** at the end of pass j+129 |
| stuck | the same: **result 1** at the end of pass j+129 |
| time out before pass j | `$B1A` + 2 a pass; **result 2** at the end of pass j+80 |

At 50 passes a second, 129 passes are 2.6 s.

### 2.8 The screen [V unless marked]

- 320 × 176 in 5 planes at `$2A320`, one buffer. Plane 5 is set only over the face's window, so
  the face and the static use COLOR16-31 and the rest COLOR00-15.
- PUZL's copper list `$17BFC` ends with `COPJMP2` to the game's `$10356`: **the status panel shows
  below the stage**. PUZL updates its digits and messages every pass. The energy can never moves
  (`$89BE` is not called).
- The elements:

| Element | Where (Amiga) | Rule (F = `$B00`) |
|---|---|---|
| Board cell (c, r) | (16 + 16c, 16 + 16r), 16 × 16, 32 tiles | all 88 at a set-up (palette black); the cursor's cell every pass |
| TV | (224, 16), 80 × 80 | face when (F & mask) = 0, else black; then static frame (F >> shift) & 3 when shift ≠ 0 |
| LED row | (64 + 8p, 152), 8 × 16 | one digit a pass: p = T[F & 15] when p ≥ the board's threshold, digit T[(`$B02` >> 1) & 15] |
| Timer | x 280 / 296 / 304, y 144 | `$804A` & 15, `$804B` >> 4, `$804B` & 15 |
| Button | (0, 148), 32 × 24 | image (F >> 3) & 1 |
| Scanning light | (216, 104 + 8 row), 8 × 8 | row (0,1,2,3,3,2,1,0)[(F >> 3) & 7], image (F >> 1) & 1 |
| Board bar | (224, 104 + 8 row), 24 × 8 | row = board (3 after the last), image (`$B02` >> 3) & 1 |
| Cursor | sprite 0 over the cursor's cell | image (0..7..0, 0)[(F >> 1) & 15], 2 passes each |

- The face shows 1 pass in 8, 4, 2 on boards 0-2, always under static on board 3, and clean once
  the memory is restored.
- Lights and bars draw only where they are; a row left behind keeps its last image.
- During the end sequences the cursor points at `$17FE8`. **I**: the sprite DMA then shows 10
  lines of PZM's jump table as a junk sprite on the last cell.
- **I**: the Amiga shows bitplane x 16-319 (DDFSTRT `$34` with BPLCON1 `$FF` left by the panel).
- Palette fade: 8 steps of 4 passes; each component limited to (level >> 1) & `$1E`. **V**: at the
  end of every fade-out `$17B14` resets the palette pointer to `$17D6A`, so visit 2's boards 1-3
  fade in with visit 1's colours (Murphy's on Ellen's face). Invisible in visit 1.

### 2.9 The sound [V: REA, model]

- PZM (PUZL's copy of the player at `$18000`) has MU1's and TITM's code. The model
  (`tools/rc2music.py --verify`) matches the 68000 code on 9,744 ticks of its 6 tunes.
- At every board set-up: stop all, then **tune 1** from its start (3,000 ticks = 60 s, no loop).
  Tune 2 is never started.
- Effects, all on Amiga channel 3, so they never cut the music:

| Effect | When | Heard |
|---|---|---|
| 4 | every cursor move | a short blip, −11 dB |
| 3 | the red chip, a pass after the move | in practice never: effect 4 still holds channel 3 and 3 < 4 (`$1822C`'s rule) |
| 5 | the start of boards 1-3 (the 2nd to the 4th) | a jingle, as loud as the music's loudest |
| 6 | every pass of the 31-pass fade-out after boards 0-2 | restarted each pass: a buzz at the pass rate (50 Hz with 24 % duty at 50 passes a second), −3.7 dB |
| none | after board 3 (the last), a failure or the time out | the music goes on |

Boards are numbered 0-3 here, as `$B0A` / 2 counts them.

- The text screens are silent (`$FE14` stops all).
- The music ticks inside PUZL's loop on 5 passes of 6: 50 ticks a second on the NTSC machines the
  dumped release targets, 41.7 on PAL. The VBL hook is patched to an `rts` meanwhile (`$8398`).

### 2.10 Quirks a faithful port keeps [V]

| # | Quirk | Traced on the MSX by (4.1) |
|---|---|---|
| 1 | D0 clobbered: in the pass that destroys the 4th board's last red chip, `message_queue` returns D0 = old `$8056` & `$C`, and a direction change in that pass moves from that column. `cell` has no bounds check: it reads up to index 90, 3 bytes past the 88 cells, into the next record's header (visit 1) or "TIM" of "TIMEOUT" (visit 2) | `pz_quirk1` (pass 602: the down move tests (0, 1), free, instead of the cursor's (4, 1), a black chip, and the cursor goes onto (4, 1)) |
| 2 | A time out during the fade-out after boards 0-2 starts the next board with `$B1A` ≥ 99: input ignored until that board's own time out, then result 2 | `pz_quirk2` |
| 3 | "TIMEOUT." is queued every pass while `$804C` is set; the queue (4 slots) fills, and the rest ticks on during the result screen | `pz_timeout`, `pz_quirk2` |
| 4 | Effect 6 requested on 31 passes in a row | every solve (the `sfx` field) |
| 5 | The palette pointer reset (2.8), visible only in visit 2 | display only: `pz_pal` back to visit 1's at every fade-out's end |

## 3. The MSX design, as built

### 3.1 Modules, banks, entry and exit [D, V]

| Piece | Where | Bytes [V] | Content |
|---|---|---:|---|
| `ml_ev` hook | fixed area (`rc2.asm`) | +6 | FE_NEXT: `front_stats`, then `front_bonus` |
| `hud_keep` | fixed area (`hud.asm`) | 16 | `hud_frame` for banked callers: both windows put back |
| `pz_done` | fixed area (`rc2.asm`) | 1 | a `ret`: the trace harness's end breakpoint |
| `pz_test` and its hooks | fixed area (`rc2.asm`), `PZ_TEST` builds only | +30 | power-on straight into Brainstorm (section 6) |
| `front_bonus`, `fe_text` | FRONT (`front.asm`) | 207 (+32 with a `TAG`) | `$8382` and the text screens |
| the four scripts | FRONT (`text.inc`) | 262 | `tools/msxtext.py` |
| `bs_stage`, the renderer, the tables | **`BANK_PUZL` = 78 at A000h** (`msx/puzl.asm`) | 3,582 | PUZL, the display, the boards, the cursor's patterns, the graded palette |
| graphics | banks 79-85 (`PUZL_GFX_BANK`, 7 banks) | 56,704 | screen, sheet, TV pictures (`puzl_gfx.bin`) |
| the sound's entries | `BANK_PUZL` (`msx/puzl.asm`: the set-up's tail `bsu_t`, `snd_bfx`) | +20 | milestone 2 (3.6) |
| the sound's player | `BANK_MUSIC` after `voice.inc` (`msx/tune.asm`, `tune.inc`) | 824 | milestone 2: tune 1 and the effect voice (3.6) |
| music and effects | banks 86-87 (`PZM_BANK`) | 12,734 | `pzm.bin` (`tools/msxtune.py`) |

Free afterwards [V: the label files of the product build at `b59a338`]: the fixed area 190 B (213
before; 160 in `PZ_TEST` builds), FRONT 2,733 B (3,202 before), `BANK_PUZL` 4,610 B,
`HUD_BANK` + 1 447 B (493 before). With milestone 2 [V: the product of `bs-sound-int` at
`3f2330d`, whose stage is `cae5193`'s]: the fixed area the same 190 B (its `fx_tk` reads `ld
hl,fx_tkd`, the same instruction), `BANK_PUZL` 20 B fewer (4,592 B there; 4,590 with `b59a338`'s
stage, as built after the merge of main `a90e77a`: `puzl_end` AE12h), `BANK_MUSIC` 1,480 B
(`music_end` BA38h; none left below B800h: 3.6).

The hook (`rc2.asm` `ml_ev`; `FE_OVER`, `FE_RESTART` and `front_stats` unchanged):

```z80
        ld hl,front_stats           ; the next level: its statistics ($85D8; a turbo R: the Z80
        call front_call             ;  again, front.asm), then load_level1's bonus stage
        ld hl,front_bonus           ;  (Brainstorm $8382; the range $8420 and level 2 later),
ml_fe:  call front_call             ;  then (for now) the title and a new game
        call title
        jp new_game
```

`front_bonus` (FRONT, the port of `$8382`):

1. On a turbo R (`cpu_tr` = 1): the Z80's hardware pause off (`CASPRV` & FDh to A7h; CHGCPU(80h)
   at `front_stats`' end had turned it on), then `display_on`. `front_stats` ends with
   `jp cpu_title`, which leaves the Z80 running with the interrupts, the display and the line
   interrupt off; `display_on` measures the HUD split for the Z80 (`split_cal`) and turns them on
   again. Other machines keep their display: `display_on` there would blank the HUD for a few
   frames, which the Amiga never does.
2. `g_tick` = 0: `hud_energy` then never moves the can.
3. `fe_text`(`txt_bs_intro`).
4. `ld a,BANK_PUZL` / `call bank_a000` / `call bs_stage` → A = 0, 1 or 2.
5. `snd_stop` (`$83E4`).
6. A = 0: AG `$805E` + 1 (a word).
7. `fe_text`(`txt_bs_ok`, `txt_bs_fail` or `txt_bs_time`, the table `fb_texts` as `$840A`).
8. `jp cpu_title`. On a turbo R it waits for a PAUSE press left pending (the picture kept, the
   pause LED lit), then CHGCPU(80h) turns the hardware pause on again and the display off: the
   title starts in the state it had after `front_stats` before Brainstorm existed. Elsewhere
   `cpu_set` returns at once.

The stage stays on the Z80 of a turbo R, where the OPLL can be written: milestone 2 plays the
OPLL there (`docs/TURBO_R.md` 3.1, 3.4). `front_bonus` leaves `BANK_PUZL` mapped at A000h: every
later path maps what it needs.

`fe_text` (FRONT) is `front_stats`' screen and loop with these changes:
- the script is read in place (`fs_ptr` = HL);
- `snd_stop` first (`$10768`: `$FE14`) and last;
- `hud_keep` runs every tick (the Amiga's VBL handler ticks the panel's messages);
- with `TAG` > 0 it draws "TEST n" at row 10 before the palette goes on (section 6).

It calls `field_call fb_init` first (no play-field copy may be pending), clears page 0's play area
(`fs_clear`), publishes `fs_list` and waits until that list is on screen, and reuses `fs_step`,
`fs_char`, `fs_tick`, `fs_vbl` and `ff_bits` unchanged. The play area goes black at its end.

`hud_keep` (fixed; `hud_frame` maps `HUD_BANK` at 8000h and `HUD_BANK` + 1 at A000h and does not
put them back). 16 bytes, because `act_8000` and `act_a000` are adjacent and `bank_a000` keeps HL:

```z80
hud_keep:
        ld hl,(act_8000)            ; L: the 8000h window's bank, H: the A000h window's
        push hl
        call hud_frame
        pop hl
        ld a,h
        call bank_a000              ; (keeps HL)
        ld a,l
        jp bank_8000
```

`bs_stage`'s rules [V: the source]:
- FRONT at 8000h and `BANK_PUZL` at A000h while it runs. It calls fixed code and FRONT.
- It maps data banks only at 8000h, through `bank_8000`, in its upload routines (`rd_at`,
  `rd_line`), and puts `BANK_FRONT` back. It never writes 9000h/B000h or 5000h/7000h directly.
- `hud_frame` only through `hud_keep`. `game_msg`, `snd_stop`, `field_call`, `joy_read` and
  `tiles_upload` put back what they map.
- Exit: `bs_hide` (the VDP idle, the last published list on screen, both SATs empty, page 2 put
  back: 3.3), then `jp pz_done` with A = the result. Nothing after `pz_done` changes the mirror.

`bs_stage`, in order (`$17100`-`$17192` and `$17D1A`):

1. `snd_stop` (`$18000`, `$FE14`'s stop all); `pf_pal` black.
2. `AM_START..AM_END` cleared; AG `$802D`, `$802E`, `$804D` cleared (`clear_game_vars`).
3. The visit by AG `$8050` (`$17156`: `cmpi.w #2,$8050` / `bmi`): `pzt_recs` + `PZ_RECS_V1`
   (`$17448-$1775F`, 792 bytes) or + `PZ_RECS_V2` (`$175C0-$1775F`, 416 bytes) copied to
   `pz_boards`; `pz_tv` = the visit's TV pictures (`PZ_GFX_TV1` / `PZ_GFX_TV2`: the same pictures
   until milestone 3); `pz_pal` = `pz_pal1`.
4. `bs_show`: VRAM and the renderer's state (3.3, "Entry").
5. `$B20` = FF; `bs_timer($0059)`; `$804E` = 0; `$B0A` = −2 (FFFEh).
6. `bs_next` (`$17184`), `bs_setup` (`$173D2`) and the pass loop (3.4) until a result.

### 3.2 RAM [D, V]

| Range | Use during the stage | Why it is free |
|---|---|---|
| `AM + $B00-$B21` (D000h-D021h) | PUZL's variables (`pzv_...`), in the mirror's layout (words little-endian, a byte at A ^ 1, a long's high word first) | the stage clears `AM_START..AM_END` as `$FE14` → `clear_game_vars` does; `pl_init` clears it again at a new game |
| AG (DC00h-DCFFh) | `$802D`, `$802E`, `$804D` cleared; score, timer, `$804C`, `$804E`; `$8050` read; `$805E` (`front_bonus`) | the game's globals |
| F500h-F817h (`MP_B`) | `pz_boards`: the visit's records and what follows them up to `$1775F` (visit 1: 792 bytes, to F817h; visit 2: 416 bytes, to F69Fh), copied at the entry; build checks (`ds` with a negative count otherwise) keep both inside `MP_B` | `tiles_init` rebuilds `MP_B` at the next level |
| EE00h-EEFDh (`objl_ram`) | `pz_want` EE00h-EE1Ah (the wanted state, 27 bytes), `rd_st0` EE20h-EE8Dh and `rd_st1` EE90h-EEFDh (each page's shown state, 110 bytes) | copied again at a level's start (`lv_fresh`) |
| C68Ah-C6A9h | the stage's scalars: `pz_last`, `pz_pal`, `pz_tv`, `pz_tune`, `pz_sfx`; the renderer's `rd_state`, `rd_shown`, `rd_page`, `rd_elem`, `rd_tvw`, `rd_acc`, `rd_face`, `rd_fr`, `rd_bank` and `rd_cmd` (the HMMM being sent, 15 bytes); C6AAh-C6FEh are still free | free since the 2026-10-24 audit |
| C6FFh | `pz_first` (`PZ_TEST` builds) | the same |

- `pz_boards` is a fixed label, so the trace harness finds it in the label file and dumps 376 bytes
  from it, and `tools/puzlcmp.py` reads `$B06` relative to it. Copying from the visit's first
  record up to `$1775F` keeps quirk 1 exact on both visits: reads past the 4th board's cells see
  the next record's header (visit 1) or "TIM" of "TIMEOUT" (visit 2), as on the Amiga.
- The patched immediates became variables: the copy's source, `pz_pal` (the graded palette in
  `BANK_PUZL`), `pz_tv` (the visit's TV pictures in `puzl_gfx.bin`), `pz_tune`.
- `$B06`'s low word holds `pz_boards` + 6 + 94 × board, its high word 0. `$B12`'s low word holds
  the frame's offset from `$17DE8` (0, `$40` … `$1C0`; `$200` in the end sequences), its high word
  0. These are the bench's encodings.
- Everything the stage reads is set at its entry: nothing relies on the power-on RAM.
- Not kept: the `$313BC` table (plane 5 over the face window) and the music divider `$17282`.
  Both are display or sound only.

### 3.3 Screen, VRAM, palette and sprites [D, V]

#### Layout

The play area is display lines 0-161, then the 5 blank lines and the HUD (lines 167-211) through
the existing split, as `front_stats` shows it. MSX y = Amiga y − 14. Eight rectangles of the
original are copied 1:1 (`tools/msxpuzl.py` `PIECES`); every functional element lies whole inside
one of them, and only decoration is dropped (the top 14 lines, the gold pins, the ribbon cable,
the TV casing, three bits of panel art). The converter checks this on every run.

| Element | MSX position |
|---|---|
| Cell (c, r) | (16c, 2 + 16r) |
| TV | (176, 2) |
| Light / bar of row k | (176 / 184, 90 + 8k) |
| LED position p | (64 + 8p, 138) |
| Timer digits | x 218 / 234 / 242, y 130 (the dash at 226 is in the picture) |
| Button | (0, 134) |
| Cursor | SAT Y = 1 + 16r, X = 16c (shown a line lower: from line 2 + 16r) |

This replaces the relayout behind `docs/ROM_BUDGET.md` 3.7's 256 × 176 frame (columns 0-15,
192-223 and 304-319 dropped): it cut the button, the four lights and the timer's seconds digit, and
it ignored the HUD below.

#### VRAM

| Area | During the stage | After the stage |
|---|---|---|
| Page 0 lines 0-161 | display page A (with sprite set A) | `fe_text` clears it |
| Page 0 lines 162-217 | the sheet, 256 × 56: chip t at (16 (t % 16), 162 + 16 (t // 16)); digit g at (8g, 194); light k at (80 + 8k, 194); bar k at (96 + 24k, 194); button k at (144 + 32k, 194) | free |
| Page 1 lines 0-161 | display page B (with set B): a copy of page 0's play area at the entry | free |
| Page 2 (10000h-17FFFh) | the visit's 9 TV pictures: picture n at (80 (n % 3), 512 + 80 (n // 3)) | **restored**: `tiles_upload` with E = 4 (banks 10-13, the bytes `vdp_setup` wrote) |
| Page 3 lines 0-87 | **kept**: the play-field atlas (uploaded only at power-on) | unchanged |
| Page 3 lines 176-191 | the cursor's 9 patterns in slots 0-8 (1D800h) | a level's start forgets them (`spr_init`) |
| Page 3 lines 192-207 | sets A and B: the colour rows of sprites 0-1 (1E000h, 1E400h), the SATs (1E200h, 1E600h) | Y = 216 at entry 0 of both SATs; the colour rows stay (4.2 check 5: harmless) |
| Page 3 lines 208-252 | **kept**: the HUD, shown by the split | unchanged |

- Why page 2: double buffering takes both display pages. The 9 pictures (3 rows of 80 lines) and
  the sheet's 32 chips do not fit the free parts of pages 0, 1 and 3 together. Page 2 holds tile
  slots 0-255, which only `title` uploads again, and `title` is a `ret` in script builds. So the
  stage puts page 2 back itself, about 0.2 s with the play area black [E]. The product's title
  uploads it once more: harmless.
- The atlas (page 3 lines 0-87) is never touched.

#### Palette and grade

- 16 colours a visit (`tools/msxpuzl.py`). Visit 1: `000 111 222 333 444 555 200 400 710 010 020 240
  310 530 433 322`. The frame keeps 14 of its 16 colours (`$EEE` → 555, `$CA4` → 530); the face and
  the static get 433 and 322, the best pair by an exhaustive CIELAB search (mean error 9.8). Face
  colours never map to a green or a bright red [V: the converter's checks]. Visit 2's pair (655,
  644) is provisional: milestone 3, the user's choice.
- **Graded as game play** (decision 8), like the HUD below it: `tools/mkrom.py` writes
  `gen/puzl_1_grade.pal`, which `msx/puzl.asm` includes as `pz_pal1`; the `.pal` and the previews
  stay plain.
- Colour 0 is black: the VBLANK and the split never write it.
- The fade (`bs_fade`, `logic.asm` `pal_fade`'s rule with `(pz_pal)` as its source): `pf_pal` =
  the graded palette limited by `fade_cap[$B19 >> 2]`. The VBLANK loads it every frame; the HUD
  keeps its own palette through the split. At the end of every fade-out `pz_pal` goes back to
  `pz_pal1` (quirk 5).

#### What is a VDP block and what is a sprite; the cursor rule

- **The cursor: hardware sprites, mode 2, 16 × 16.** Sprite 0 carries the image's colour-3 pixels
  (colour 15) on every line; sprite 1 only image 2's two colour-2 pixels (colour 14). Images 0-7
  use sprite 0's patterns 0, 1, 2, 4, 5, 6, 7, 8 and image 2 also sprite 1's pattern 3
  (`puzl.inc` `PZ_CURA_i`, `PZ_CURB_i`, `PZ_CUR_COL_v`). At most 2 sprites on a line, 3 SAT
  entries with the terminator. It never flickers and never loses a piece.
- **The cursor rule [D].** Each picture shows the cursor the original's copper interrupt shows
  after the pass its build saw: at (`$B0C`, `$B0E`) with image (`$B12` − `$17DE8`) / 40h
  (`pw_ccol`, `pw_crow`, `pw_cimg`). It is hidden (SAT entry 0 at Y = 216) exactly where the Amiga
  shows its junk sprite, `$B12` = `$17FE8` (`pw_cimg` = 8): from the pass after a 4th-board solve or
  a stuck, and from the time-out pass on. The pass that ends a board still shows it, as on the
  Amiga (the plan's "hidden while `$B1A` ≠ 0" differed by that pass). A set-up moves it to the
  board's start before the fade-in. Quirk 1's off-board column (11 or 13, only after a played
  level 1) is shown where the cell grid puts it (SAT X 176 or 208, over the TV) for its one pass,
  as the Amiga does; no drive reaches it.
- **Everything else: HMMM copies** (whole bytes, all x even) from the sheet or the TV pictures.

| Block | Size | HMMM, sprites on [E] | Changes |
|---|---|---|---|
| Cell | 16 × 16 | ~0.95 ms | 88 at a set-up; 1 when the cursor burns a cell |
| TV picture | 80 × 80 | ~18.7 ms | up to every pass (boards 0-2) |
| LED digit | 8 × 16 | ~0.5 ms | about every pass |
| Timer digit | 8 × 16 | ~0.5 ms | once a second |
| Light | 8 × 8 | ~0.3 ms | every 2 passes |
| Bar | 24 × 8 | ~0.7 ms | about 1 pass in 2.7 |
| Button | 32 × 24 | ~2.4 ms | every 8 passes |

#### The renderer: wanted state, shown state, double buffer

- An 80 × 80 copy takes about 18.7 ms, longer than a 60 Hz frame, and the beam leaves the TV's
  lines for only 11.7 ms (60 Hz) or 14.9 ms (50 Hz) [E]. On one page it would tear. So the picture
  is built on the page not shown and flipped at a VBLANK by a register list, the way `fs_list`
  and the V9938 scroll engine publish theirs (`next_list`, `list_tail`).
- The list (`bs_list`, after `fs_list`): R#23 = 0 first, R#19 = `SPLIT_LINE`, R#1 = `R1_ON`,
  R#8 = `R8_SPR_ON`, R#2 = `R2_PAGE0` / `R2_PAGE1`, R#18 = 0, R#5 = `R5_SET_A` / `R5_SET_B`; on the
  V9958 R#25-R#27 = 0. Page 0 goes with sprite set A, page 1 with set B.
- **The wanted state** (`pz_want`, `msx.inc`): what the original has drawn as of the last pass,
  written by `pz_frame` at the points where the original draws, never read by the logic. Its first
  22 bytes have the shown state's layout (checked at build time against `puzl.inc`), so the
  renderer compares them byte for byte:

| Address | Name | Content | Written |
|---|---|---|---|
| EE00h | `pz_want` | the TV picture of the last pass: `PZ_TV_FACE` + static frame (0-3, the face shown), `PZ_TV_BLACK` + static frame (4-7), or `PZ_TV_CLEAN` (8: the memory restored) | every pass (`bs_tv`, `$17298`) |
| EE01h-EE09h | `pw_led` | per LED position the digit last drawn there (FFh: never) | when the position reaches the board's threshold (`bs_led`, `$17944`) |
| EE0Ah-EE0Ch | `pw_timer` | minutes & 15, seconds >> 4, seconds & 15 | every pass (`bs_tmr`, `$1797C`) |
| EE0Dh | `pw_button` | (`$B00` >> 3) & 1 | every pass (`bs_decor`) |
| EE0Eh-EE11h | `pw_light` | per row the light's image last drawn there (FFh: never) | every pass, on row `pzt_rows[($B00 >> 3) & 7]` |
| EE12h-EE15h | `pw_bar` | per row the bar's image last drawn there (FFh: never) | every pass, on the board's row (3 after the last) |
| EE16h | `pw_tvk` | passes since the renderer last took the TV (at most FFh) | + 1 every pass; the renderer clears it |
| EE17h | `pw_tvf` | of those, the passes with the face (picture 0-3 or 8) | + 1 with the face; the renderer clears it |
| EE18h-EE1Ah | `pw_ccol`, `pw_crow`, `pw_cimg` | the cursor at the pass's end: `$B0C`, `$B0E`, `$B12`'s offset / 40h (8: none) | every pass (after `joy_read`); `bs_board` sets the board's start |

  The 88 cells are the board itself (`(pzv_cells + 2)`): the step burns the cursor's cell where
  the original redraws it; a set-up masks all 88 where the original draws them.
- **The shown state** (`rd_st0`, `rd_st1`: `puzl.inc` `PZ_ST_*`, 110 bytes a page): TV picture
  (0), 9 LED digits (1), 3 timer digits (10), button (13), 4 lights (14), 4 bars (18), 88 cells
  (22). Values: a TV picture 0-8, a digit 0-9, an image 0-1, a tile 0-31; FFh means the screen's
  own pixels. Elements the original has not drawn yet (FFh in the wanted state) keep the static
  screen's pixels, as on the Amiga.
- **`bs_feed`**, a state machine called while `bs_wait` waits and once after each pass. It never
  waits for the VDP:

| State | When it moves on | What it does |
|---|---|---|
| idle | a new pass (`$B00` ≠ `rd_fr`) and the VDP idle | decides the build's TV picture (the duty rule); target = the page not shown |
| building | the VDP idle | issues one HMMM (`rd_mk` into `rd_cmd`, through `vdp_cmd`) for the next element (`rd_next`: the TV, the 21 decor bytes, the 88 cells) whose wanted value differs from the target page's, and marks it in that page's state; when none is left: writes the target set's SAT (`rd_sat`: the cursor) and publishes the list (`bs_list`) |
| published | `app_seq` = `pub_seq` | that page is now the one shown (`rd_shown`); back to idle |

- Every change thus reaches each page once, at its next build, and a build starts only after a
  new pass. Each page always shows the state of a recent pass, element by element, never a
  half-drawn block.
- **The TV duty rule.** Pictures come about every 2 passes on boards 0-2 (one TV copy per build).
  A picture that covers k passes, f of them with the face, shows the face when acc + f/k ≥ 1/2,
  then acc += f/k − shown (`rd_acc`, signed, in 1/256). The static frame is always the newest
  pass's. When pictures keep up (k = 1) this is exactly the original's sequence; without the rule
  board 2's face (every other pass) would alias to always on or always off. Measured share of the
  pictures with the face on boards 0-3 and after: 0.13, 0.25, 0.48-0.50, 0.99, 1.00 (the original:
  1/8, 1/4, 1/2, always, clean) [V: the `solve1` records on four machines].
- **Board set-up** (`bs_board`, at the end of `bs_setup`; the palette black: the fade-out reached 0,
  or the entry). The cursor's place first (`pw_ccol`, `pw_crow` = the board's start), then the 88
  cells into both pages at once (176 HMMMs through `vdp_cmd`) and into both pages' states. The
  fade-in therefore never shows the previous board. The passes wait meanwhile.
- **Entry** (`bs_show`, with the play area black and the intro's list on screen): the screen and
  the sheet into page 0 (27,904 bytes from the ROM through the 8000h window), page 0's play area
  copied to page 1 (one HMMM 256 × 162), the TV pictures into page 2 (9 × 80 lines of 40 bytes,
  `vram_write` / `vram_done` a line), `BANK_FRONT` back at 8000h, the 9 cursor patterns, the colour
  rows of sprites 0-1 in both sets (the visit's `PZ_CUR_COL_v`, `PZ_CUR_COL2_v`), both SATs empty,
  `pz_want` and both shown states FFh.
- **Exit** (`bs_hide`): the VDP idle and the last published list on screen; Y = 216 at entry 0 of
  both SATs; page 2 back (`tiles_upload` E = 4). The result text's `fe_text` then publishes page
  0 with sprites off.
- **Engine rules the renderer follows** [V: `vdp.asm`, `isr.asm`, `cold.asm`, `field.asm`]:
  - Every HMMM goes through `vdp_cmd`: it sets `cmd_lock`, which keeps the interrupts' `isr_fbgo`
    / `ifg_rdy` off the command registers. The 15 bytes come from the renderer's own buffer
    (`rd_cmd`), never `cmdbuf`, whose NX, NY, ARG and command `vdp_setup` sets once for the tile
    engine.
  - `fe_text`'s `fb_init` leaves `fb_cq`, `fb_rdy` and `fb_busy` at 0, so the interrupts start no
    play-field copy during the stage. Nothing new runs in the interrupts: the VBLANK applies the
    published list (registers, colours 1-15 of `pf_pal`) as for the text screens.
  - Every VRAM stream sets its address with `vram_write` and ends with `vram_done`.
  - The graphics are packed across banks and read through the 8000h window while `BANK_PUZL`
    holds A000h: no OTIR may run past 9FFFh, so `rd_line` splits every stream at the 8 KiB
    boundaries, also inside a TV picture's 40-byte line.
  - `BANK_FRONT` is mapped back before any FRONT routine (`fs_tick`, `fs_list`, `tiles_upload`).

### 3.4 Timing [D, V]

- **One pass per 50 Hz tick, on 50 and 60 Hz machines.** Decision 7 runs the game logic at the
  original's PAL design speed; PUZL's loop waits for 1 VBL, so its PAL design speed is 50 passes a
  second, the rate the front end's text screens already use (`fs_tick`). At 60 Hz every sixth
  VBLANK is skipped. `TICK_HZ` does not apply to the stage, as it does not to the text screens.
- `bs_wait` is `fs_tick`'s rule (the same `fs_div`), with `bs_feed` called while it waits. It also
  sets `wf_n` = the VBLANKs since the last pass or the timer's set-up (`pz_last`).
- **The timer** is the CIA-B's: `sec_tick` (fixed code, real seconds by VBLANKs, 50 or 60 by
  `RG9SAV`) after each wait. `bs_timer` (`$F9DC`) resets `sec_n` and `pz_last`. In script builds
  (`JOY=`, `EXTJOY=1`) `sec_tick` is a `ret`, so the timer stands still, as on the bench.
  Measured [V: openMSX, `PZ_TEST=1`, board 0 left alone]: the time out 60.96 s after the first
  pass on a Gradiente Expert 2.0 (60 Hz), 60.65 s on C-BIOS_MSX2_EU (50 Hz: openMSX's 50.16 Hz),
  60.93 s on the FS-A1GT, then the result 80 passes later. `bs_board`'s 176 copies run after
  `bs_timer` started the board's count, so the time out comes about 61 s after the set-up: real
  time, as on the Amiga.
- **Pictures** [V: records of every VBLANK of `solve1`]: about 30 a second at 60 Hz (470 pictures
  in 922 VBLANKs on the MSX2, 466 on the turbo R, 463 on the MSX2+) and 28 at 50 Hz (429 in 766).
- The end sequences keep their PAL lengths: 2.6 s after the last red chip or a failure.
- Turbo R: the stage runs on the Z80 at 3.58 MHz.

The loop (`msx/puzl.asm`):

```
bs_loop:  bs_wait                  ; the next 50 Hz tick ($171BA); bs_feed meanwhile; wf_n
          hud_keep                 ; $8004 digits, $8020 ticker: before the beam reaches the HUD
          sec_tick                 ; the CIA-B ($1015E): real seconds; still in script builds
pz_tick:  call pz_frame            ; one pass ($171C2-$1722F): the trace's sampling point
          bs_feed
          end checks ($17230-$17280) -> bs_loop, bs_next, or bs_exit (bs_hide, jp pz_done)
pz_frame: $B12; bs_fade; bs_tv; bs_led; bs_tmr; bs_step; $B02 += 3; $B00 + 1;
          bs_decor; joy_read; tick_n + 1; the cursor's wanted state
```

`tick_n` + 1 each pass lets a `JOY=` script go on through the stage: pass k reads the script at
`tick_n` = (the ticks before the stage) + k.

### 3.5 Input [D, V]

- `joy_read` as in the game (`player.asm`): joystick port 1 (trigger A is fire), else the keyboard
  byte (cursor keys, SPACE/RETURN fire, bit 7 once a key was used). The whole byte goes to `$802E`,
  as on the Amiga, so fire toggles repeat a held move. Trigger B does nothing here (as F1 on the
  Amiga).
- Called at the original's point (after the decor), so the step uses the previous pass's byte.
- `JOY=` builds: the script by `tick_n`. `EXTJOY=1` builds: `ext_joy` (CE5Ah), poked by the Tcl
  driver at each `pz_tick`.
- Opposite directions: `read_joystick`'s table (`$BE26`) reads up + down or left + right on the
  joystick as no direction [V: REA], but the keyboard path (`$802D` → `$802E`) can deliver both
  bits of a pair, on the Amiga and on the MSX. The step takes the lowest bit first; the `pz_opp`
  drive pokes such bytes into `$802E` and matches the original.
- The stage has no pause (the original clears `$804E` and never sets it); on a turbo R the PAUSE
  key does nothing during the bonus screens (3.1).

### 3.6 Sound [D; V: in a Z80 interpreter on the images and in openMSX]

What the original plays is in 2.9. Milestone 2 plays it on the MSX (the branch `bs-sound-int`:
section 5's steps 10-12 and the integration review's fixes). The stage still calls `snd_stop` at
its entry and `front_bonus` after it, and the text screens stay silent, as on the Amiga. The
checks ran offline, in a Z80 interpreter on the ROM images, then in openMSX on every chip set
(4.3); the user's ears on real hardware are still to come (the test3 candidates).

- **Data** (`tools/msxtune.py` → `build/msx/pzm.bin`, 12,734 B, banks 86-87 from `PZM_BANK`; `make
  msx` runs it with the project's venv: numpy).
  - The routing step turns a tune into the title's shape, three melodic voices and the drum-only
    channels, so `tools/msxscc.py`, `tools/msxfm.py` and `tools/msxsound.py` convert it unchanged.
    Through it TITM tune 1 gives today's `scc.bin` (25,803 B), `fm.bin` (13,238 B) and PSG title
    (5,990 B) byte for byte (`tests/test_msxtune.py`).
  - PZM tune 1 in three versions: the SCC's 6,884 B (three SCC voices, the drums on PSG C), the
    OPLL's 3,580 B (three channels and the rhythm), the PSG's 1,878 B (A-C at the title's λ). Tune
    2 is not converted: PUZL never starts it.
  - Effects 3-5 through the effect converters at the tune's reference, so the Amiga's balance holds
    (3 and 4 about 11 dB under the music's loudest, 5 as loud). Effect 6 is designed as the buzz
    its restarts make (SCC: a 24 % pulse at 50.00 Hz, volume 8; PSG: a 50.00 Hz square at level
    13): converted from its data, whose first tick is silent, it would be silent when restarted
    every pass.
  - `tools/mkrom.py` checks the blob (every stream lasts the tune, every effect its ticks, at most
    254; each waveform within a bank) and writes `tune.inc`, the descriptor the player reads.
- **Player** (`msx/tune.asm`, in `BANK_MUSIC` after `voice.inc`). Not the generalised `music.asm`
  of the plan: a player of its own that drives `music.asm`'s voices, readers and outputs (`mus_v`,
  `mv_rec`, `mo_fm3`, `mo_rhy`, `mo_pv`) with `mus_on` 0, so the title's code and tables keep their
  bytes.
  - `tn_start` (HL = a descriptor, through `mus_call`) waits for a VBLANK, so that a stop the PSG
    player still has queued lands first (H7) and its work comes far from the HUD split. Then, with
    the interrupts off for up to about 2 ms: the stop all (`mus_quiet`; PSG A-C silent; the effect
    voice idle and `$1822C`'s memory cleared, as stop all clears `$18023`), the voices on the
    descriptor's streams for this machine's chips, the OPLL's patch, the SCC's channels 0-3 on.
  - The chips: with an SCC the melody on its channels 0-2 and the drums on PSG C, or on the OPLL's
    rhythm when there is one; the OPLL alone: its channels 0-2 and the rhythm; neither: the PSG
    version on A-C. On a turbo R the stage runs on the Z80, so the OPLL is written there too (on
    the R800 `tn_start` would leave it out).
  - The SCC's waveforms go from the tune's table in the data banks to the chip through RAM
    (`scc_wb`, `sound.asm` `scc_wv`). Nothing of the player runs or is read with 3Fh at 9000h, so it
    may lie past B800h, where the MSX Pico+ shows the SCC then.
- **The effect voice** (`tn_v`, a fifth voice): SCC channel 3 with an SCC (the music uses 0-2), else
  PSG voice C, where the PSG version's voice 2 is muted while an effect sounds and then written
  back whole (`mo_pw`): never lost. `$1822C`'s rule as the 68000 runs it [V: REA on `$1822C`,
  `$18316` and `$1839A`, the model]: a request lower than the last effect started is refused while
  that effect holds channel 3. Its flags (`$18126`) stay set until the tick that reads its end, its
  length L after its first, and PUZL's request comes before that pass's tick, so a lower request is
  refused 1 to L ticks after the effect's first (`tn_go`: busy for L + 1 ticks from its own). So
  effect 3 is refused in play, as on the Amiga (4 still plays). Of two requests between two ticks
  the higher one stays (`snd_bfx`), the one the Amiga lets sound.
- **Ticks.** The VBLANK interrupt runs `sndplay.asm` `sq_frame`'s 50 Hz ticks (at 60 Hz every sixth
  VBLANK skipped) while `fx_act` is set: `sound.asm` `fx_tk` → `tune.asm` `fx_tkd` (in `BANK_MUSIC`,
  behind `fx_bk`) → `tn_tick` while sndplay's voice A holds the tune's mark (`TN_MARK` in its
  `SV_CH`), else `fx_tick` as before (level 1's effects). A tick starts the pending request first,
  then reads the tune's records and the effect voice's. It runs while the tune or an effect plays:
  after the tune's 3,000 ticks (60 s) its voices fall silent, as the Amiga's channels stop, and an
  effect asked for later still sounds (H6). `snd_stop` ends it all: `mus_quiet` with an SCC or an
  OPLL, the PSG player's stop (the mark gone) with the PSG alone.
- **A board's first tick.** The 68000 ticks PZM inside PUZL's pass, after that pass's request
  (`$17794`, then `$17212`: 2.3), and a board's set-up ends with stop all and tune 1 (`$1743A`,
  `$17442`). The next pass asks for effect 5 at boards 1-3 (`$173DC` wrote it), and its tick plays
  that jingle with tune 1's tick 0.
  - The port ticks from the VBLANK while the stage's passes wait for their own 50 Hz ticks (3.4).
    So `tn_start` keeps the pass counter's low byte (`$B00`, which `pz_frame` raises after the step)
    and `fx_tkd` holds the tune until it moved (`tn_hold`: no tick, no write). Tick 0 is the first
    tick after the next pass, with that pass's request; board 0's too, as the 68000's first tick
    after its set-up.
  - This holds at 50 and 60 Hz whichever VBLANKs the passes' divider (`fs_div`) and the ticks'
    (`snd_div`) skip. An idle first tick would not: at 60 Hz, when the passes skip the first VBLANK
    after the set-up, tick 0 would still come before the request.
  - The integration's first build started effect 5 a tick after tick 0, a 20 ms flam (the
    integration review's finding 2).
- **The stage's calls** (`msx/puzl.asm`, in `BANK_PUZL`, where the 68000 makes them):
  - `bs_setup` ends with tune 1: its tail `bsu_t` is `ld hl,tn_pzm` / `jp mus_call`. The record's
    tune byte (`pz_tune`) is 1 in all eight records, so only tune 1 is converted.
  - `bst_go` records the pass's request (`pz_sfx`) and sends it with `snd_bfx`, after `bst_e`'s
    early return as `$1778A` comes after `$17776`'s. `snd_bfx` writes only RAM (`tn_req`, `fx_act`).
  - Never `snd_stop` right before the tune (H7): `tn_start`'s stop all is the stop.
  - Neither call writes the mirror, so the traces are the silent stage's (4.1).
- **Room.** No byte in the fixed area: `fx_tk` reads `ld hl,fx_tkd` where it read `ld
  hl,fx_tick`, so every build option set that assembled still assembles, with the same `code_end`
  (1,771 sets built from both trees). The integration's first build had put its 49 B there, and
  `SPLITDIAG=1 EXTJOY=1 LOCKSTEP=24` no longer assembled (the integration review's finding 1).
  `BANK_MUSIC`: `tune.inc` (92 B) and `tune.asm` (732 B) from B700h to `music_end` BA38h, 1,480 B
  left past B800h and none below it (`docs/ROM_BUDGET.md` 2.1). `BANK_PUZL`: 20 B. RAM: `tn_...` at
  C2B6h-C2C1h and C2C5h-C2D8h (`msx.inc`). DIAG builds, which never play the game, get no byte of
  it (`tn_pzm` is `mus_stop` there, `fx_tkd` is `fx_tick`).
- **Interrupt rule.** Everything that runs from the VBLANK keeps DE, IX, IY and the alternate
  registers: the interrupt saves AF, BC and HL, `snd_bk` adds DE and IX, and the player uses
  neither IY nor the alternate registers.
- **Cost** [E]: a tick about the title's (2,300 T-states for four voices) plus the effect voice's;
  a board's tick 0 loads three SCC waveforms, up to about 3.7 ms in the VBLANK interrupt, well
  before the HUD split's line (about 13 ms on).
- **After the stage.** `front_bonus`' `snd_stop` silences every chip set. The title after it writes
  its chips as the title after main's silent stage does, write for write: as at power-on when the
  stage comes first (a `PZ_TEST` build). After a played level 1, with the PSG alone, both write
  while silent the tone periods that level 1's last effects left in the PSG player's voices
  (`sndplay.asm` `sq_stop` keeps `SV_PER`; `sq_init` runs at power-on only), never heard. The
  registers the stage wrote keep its values only until the title's own records reach them, but
  for SCC channel 3's waveform and period, which the title never writes (its music uses channels
  0-2, with 3 off): they keep what the stage's effects left. Level 1's effects after the stage are
  a fresh machine's.
- **Level 1's random choices** [V: openMSX]. With an SCC, level 1's effects now tick through
  `fx_tkd`'s dispatch, about 54 T-states more per tick in the VBLANK interrupt. Builds without an
  input script (the product) mix the Z80's R register into the random word `$B32` every frame
  (`logic.asm` `rnd_step`), so for the same input it takes other values than in main's build (from
  row 31 of the product's drive; the objects differ from row 153), and the random choices follow
  another sequence. The logic and the effects are unchanged (the `EXTJOY` traces and the
  `LOCKSTEP` writes are main's), and builds without an SCC are identical. The same class as the
  2 MiB guard's timing; a human's input already varies R.
- **Open, for the user's ears** [I]: the effects' balance on the SCC (3 and 4 come out at SCC
  volume 3, the tune's scale). Measured in openMSX against the same music without the effect: a
  blip's loudest tick 3.6-6.7 dB under the music's median (the Amiga 6.1), the jingle 8.2-9.8 dB
  over it (the Amiga 5.1), the buzz 2.4-3.7 dB over it (the Amiga 1.4). The OPLL's custom patch on
  instrument #4, chosen on the converters' approximate OPLL model: it sounds only with the OPLL
  alone (mode 06, no SCC); with an SCC and an OPLL (mode 05) the OPLL plays the rhythm only. The
  user's machines find the Pico+'s SCC, so they play mode 01 or 05; `NO_SCC=1` test builds play the
  OPLL-alone and PSG-alone versions there. Their OPLLs are an FPGA core (the SX-2's MSX-MUSIC) and
  the Pico+'s firmware, not YM2413 chips. Effect 6's buzz design; PERCUSH1/2 classified as toms.

### 3.7 The intro and result texts [D, V]

- `tools/msxtext.py` appends `txt_bs_intro` (`$114AA`), `txt_bs_ok` (`$1162F`), `txt_bs_fail`
  (`$11667`) and `txt_bs_time` (`$11698`) to `text.inc` after `txt_glyphs`: each script's bytes
  up to its `FF 07`, read from the RAM image, 262 bytes in all. It asserts that only commands 2 and
  7 occur, that every glyph is in the font, that every line lies inside the 256 × 162 play area
  (x = 8c − 16, y = 67 + 8r) and the original's call counts (292, 143, 136, 129).
- **The intro's long line** "DESTROY ALL RED CHIPS ON THE BOARD" (34 characters at column 2: x
  0-271) cannot fit 256 pixels; `fs_char` has no bounds check and would write its last two glyphs
  into a VRAM line's left edge. The port's copy splits it, a spacing change:

```
00 0D 00 "BRAINSTORM."                    row 0, x 88-175   (as the original)
00 08 03 "DESTROY ALL RED CHIPS"          row 3, x 48-215
00 0D 04 "ON THE BOARD"                   row 4, x 88-183
00 05 06 "COMPLETE 4 TO REGAIN MEMORY."   row 6, x 24-247   (was row 5)
00 07 08 "AND EARN A GAME CREDIT."        row 8, x 40-223   (was row 7; lines 131-138)
FF 02 30 FF 07
```

  Five positions and 95 characters: 100 elements, as the original's 4 + 96, so the screen still
  lasts 292 calls (293 ticks without fire).
- The three result scripts fit as they are.
- The tool also writes each script's finished play area (`build/msx/text_bs_*.sc5`, SCREEN 5
  bytes, and `.png`), the reference of the MSX screen checks (4.2 check 1).
- `fe_text` runs `hud_keep` each tick, so messages left by the stage (several "TIMEOUT.") tick on
  during the result screen, as on the Amiga.

### 3.8 The HUD [D, V]

- It stays shown and updated as in the game: timer (the board's 1:00), score (+100 a red chip),
  the message line. The ammo, the lives and the can stay as level 1 left them; the can never moves
  (`g_tick` = 0). Measured (4.2 check 4) on `solve1` in an `EXTJOY=1` build, where the timer
  stands still: the HUD equals step 6's at the same 12 passes, and its first and last snapshots
  differ only in the score's box.
- **Messages.** `tools/msxhudrt.py` takes PUZL's three strings from `PUZL_25.bin` (offsets `$638`,
  `$641`, `$64E`: `$17738`, `$17741`, `$1774E`) and appends them as a second table after
  `HUD_WEAPONS`, at `HUD_PZ_MSGS` (BE14h: one FFh pad byte for an even distance from `HUD_MSGS`,
  3 pointers, the strings). `game_msg` computes `HUD_MSGS` + 2n, so it reaches them as numbers
  **174, 175, 176** (`HUD_MSG_17738`, `HUD_MSG_17741`, `HUD_MSG_1774E`); the stage uses only the
  equates. Level 1's 21 messages, their numbers, `HUD_NMSGS` (21) and every earlier byte keep
  their values. Every glyph is in the HUD font.
- Quirk 1 needs `message_queue`'s returned D0: the stage takes `(msg_wr & 6) × 2` before the
  "MEMORY RESTORED." call (the port's `msg_wr` counts as `$8056` does, in steps of 2 instead of 4).

### 3.9 The converter `tools/msxpuzl.py` [D, V]

From the graphics report's prototype (stdlib only; it imports `tools/planar.py`,
`tools/msxhud.py`, `tools/msxbright.py`). Input `build/extracted/files/PUZL_25.bin` (loaded at
`$17100`; the same bytes as disk 1's decrunched `PUZL_13`). Output prefix `build/msx/puzl` (the
`msx` target's line: `$(PYTHON) -I tools/msxpuzl.py $(X)/files/PUZL_25.bin $(BUILD)/msx/puzl`):

| Output | Format | Bytes |
|---|---|---:|
| `puzl_1.pal` (`puzl_2.pal` with `--visits 1,2`) | 16 colours, V9938 pairs (R << 4 \| B, G), plain | 32 each |
| `puzl_gfx.bin` | the screen (256 × 162, TV rectangle black) and the sheet (256 × 56), 128 bytes a line: one stream into page 0 from line 0; then visit 1's 9 TV pictures (80 × 80, 40 bytes a line, `TV_STATES` order: face + static 0-3, black + static 0-3, the face alone); with `--visits 1,2` visit 2's 9 after them | 27,904 + 28,800 (+ 28,800) |
| `puzl_cursor.spr` | 9 patterns × 32 bytes (mode 2: left 8 columns, then right 8) | 288 |
| `puzl.inc` | equates only (include it anywhere): the elements' places, the sheet's and the TV pictures' VDP coordinates, the blob's layout, the cursor's patterns and colours per visit, the 110-byte shown state, the boards' layout | — |
| `puzl_tab.inc` | data (included once, in `BANK_PUZL`): `$17448-$1775F` (`pzt_recs`, 792 bytes) and the small tables of 2.6 as the 68000 indexes them (`pzt_curofs`, `pzt_masks`, `pzt_shifts`, `pzt_ledthr`, `pzt_ledval`, `pzt_rows`) | 902 |
| `puzl_*.png` | previews: the stored screen, sheet, TV pictures, cursor; the stage plain and graded with the HUD; the Amiga against the MSX | — |

- The screen and the sheet are the same bytes in both visits; only the 2 face colours and the TV
  pictures differ [V: graphics report].
- Checks on every run (any failure stops the tool): the tables equal 2.6, the palettes too; every
  board's start, red-chip count (= its type-0 cells), timer and tune; visit 1's full solve = 9,500;
  the pieces neither overlap nor leave a hole, on even x; every functional element lies whole in
  one piece at its 3.3 place; the colour rules; and renders of 11 shown states a visit through a
  VRAM model equal the Amiga's own composition of the same states, pixel for pixel.
- **Render mode** (the still checks of 4.2): `msxpuzl.py render PUZL_25.bin STATE OUT [--offset N |
  --hex] [--cursor C,R,I] [--visit 1|2] [--grade] [--scale N]` builds a display page's picture from
  its 110-byte shown state (e.g. in a RAM dump) and the cursor, as the stage builds it, into
  `OUT.sc5` and `OUT.png`. Until milestone 3 check `PZ_LEVEL=2` snapshots with `--visit 1`: the
  ROM shows visit 1's face there.
- Tests: `tests/test_msxpuzl.py` (17).

### 3.10 `tools/mkrom.py` and the banks [D, V]

- **`BANK_PUZL` = 78, not 10 as planned.** With `"PUZL"` after `"MUSIC"` in `LOGIC` every data bank
  moved up by one, and bank 24h's byte at 1800h then held 24h, an SCC test value (`msx/sound.asm`
  `scc_pat`): mkrom refused the image ("the SCC test would find an SCC in a cartridge without
  one"). The plan's review had checked the 3Fh rule after the shift but not those values. Now
  `STAGES = ("PUZL",)`: the bonus stages' code banks are `msx/rc2.asm`'s last sections (`org
  0xA000`, `include "puzl.asm"`, `puzl_end`, the pad to C000h), assembled as before but placed
  **after the sound effects**, so that no bank before them moves. At step 4 (the layout with a
  stub stage) banks 0-77 were byte-identical to `52149b0`'s [V]; since then only the code banks
  changed where code was added (the fixed area and FRONT, and the calls into them in banks 2-9),
  and bank 45's padding (PUZL's HUD messages): the data banks 10-77 are as they were [V: the image
  against `ROBOCOP2_v0.1.3-test1.ROM`]. The code-size check counts `len(LOGIC) + len(STAGES)`. A
  later stage (the range) can be appended to `STAGES` the same way.
- `puzl_gfx.bin` follows the stage's code, packed across banks from `PUZL_GFX_BANK` = 79
  (`PUZL_GFX_BANKS` = 7: 79-85; bank 85 holds its last 7,552 bytes). `banks.inc` gets `BANK_PUZL`,
  `PUZL_GFX_BANK`, `PUZL_GFX_BANKS`; the summary line names them.
- `gen/puzl_1_grade.pal` is written like `level1_grade.pal`; `puzl.inc`, `puzl_tab.inc` and
  `puzl_cursor.spr` are copied to `gen`.
- Options `PZ_TEST` (0), `PZ_LEVEL` (1) and `TAG` (0), refused outside 0-1, 1-2 and 0-99 (section 6).
- mkrom's checks run as before and pass: the 3Fh rule, the SCC test values at 1800h, no "OPLL",
  `scc_time_end` below B800h, 256 banks at most; also with `ROM_2M=1`, `DIAG=1` and `DIAG=2`.

| Item | Banks | Total |
|---|---:|---:|
| Before Brainstorm (`52149b0`) | 78 | 78 |
| `BANK_PUZL` (code and tables, 3,582 B) | 1 | 79 |
| Graphics, visit 1, raw (56,704 B) | 7 | **86 (built)** |
| PZM tune 1 (SCC, OPLL, PSG) and effects (`pzm.bin`, 12,734 B, one blob from bank 86) [V: built] | 2 | **88 (built)** |
| Visit 2's TV pictures (28,800 B: the blob grows to 85,504 B, 11 banks) [V: `--visits 1,2`] | 4 | 92 |

- The image stays **1 MiB** (128 banks; 88 used, 40 free); the 2 MiB limit is 256. At 92 banks,
  bank 90 (5Ah) holds data: if mkrom finds 5Ah at its 1800h, move a block.
- ZX0 would bring the graphics to about 3 banks, but the project has no decompressor.
- **The whole game against the mandatory 2 MiB** [E: `docs/ROM_BUDGET.md` 4.1]. From 86 banks
  (88 with the sound, whose 2 banks the rest of the game counted already: the same totals), with
  today's pipeline, the rest of the game takes about 103 banks likely and 112 high
  (the range's graphics in ZX0): about 189 and 198 of 256. Stored raw like Brainstorm's, the
  range's graphics add about 7 and 5 more: about 196 likely and 203 high. The mandate holds with
  about 50 banks to spare. Only the content decision 5 dropped (`docs/ROM_BUDGET.md` 3.9, the
  photos raw) would then no longer fit; ZX0 for the bonus graphics stays the fallback (−8 to −9
  banks for Brainstorm).
- Banks the stage maps [E: read from the code]: 0-1, `BANK_FRONT`, `BANK_PUZL`, the 2 HUD banks,
  `BANK_INPUT` and `BANK_MUSIC` (the sound's calls and ticks), the 2 music banks (the tune's
  streams, at 8000h in the VBLANK), the 7 graphics banks (entry only), the 4 tile banks (exit
  only), and `BANK_FIELD` in the text screens: about 22, far under the MSX Pico+'s 53-bank speed
  target (`docs/PICO_CACHE.md`).

### 3.11 What the stage leaves [D, V]

| Item | After the stage |
|---|---|
| AG `$805E` | + 1 when solved. `new_game` clears AG, as the original's `$FFC4`; it becomes useful when the game-over continue (`$11FD2`) is ported |
| AG `$8046-$8049` | the score with the red chips, shown on the HUD |
| AG `$804A`, `$804C`, `$804E` | as the stage left them; the next level's start sets them (the future `$8420` clears `$804C` first) |
| AM, `pz_boards` (`MP_B`), `objl_ram` | dead; `new_game` rebuilds them |
| HUD queue | may hold PUZL's messages; they tick on in the result screen; `hud_init` clears it |
| VRAM | page 2 and the SATs back; pages 0-1 overwritten (the title and the next level draw them); the colour rows of sprites 0-1 hold the cursor's colours until the sprite engine rewrites them |
| CPU | the Z80 on a turbo R, with its hardware pause on again: what `title` expects |

## 4. Verification

Every result below comes from the implementation's own runs on 2026-10-27: headless openMSX
through the MSX-AI MCP, at most two instances, on the local machine set. While this document was
written, the trace compares, the display guard's logs, the time-out logs, the HUD blank's events,
the picture counts, the TV duty shares, three still pictures (rendered again from their RAM with
4.5's command: equal to their VRAM page byte for byte), `make matrix`'s log and the image sizes
were re-checked from those runs' files and from scratch builds; no emulator was run for it.

### 4.1 Logic: the bench against the MSX trace

- **The bench's `puzl` mode** (`tools/amigaemu.py puzl`, Unicorn). It runs PUZL along the game's
  own path (a new game's set-up, `$8050` = the level done, the loader, the decruncher `$124A6`,
  `jsr $17100`; or the whole of `$8382` with `--via-8382`), applies a `tools/drivejoy.py` file's
  joystick byte and pokes at the start of every pass (`$171C2`), records PUZL's state there
  (`--trace`; `--trace-ram` adds `$B00-$B21`, `$8000-$80FF`, the board table and the patched
  immediates) and stops when `$17100` returns D0. `--sec N` raises the CIA-B second every N passes.
  - Two Unicorn defects are handled in this mode only: the stale flags of `reg_read(SR)` (the
    interrupts push a live SR from a `move.w sr` stub) and SBCD's N flag (the countdown's `BPL`s at
    `$10198` and `$101A6`). The game mode stays byte-identical (`--trace-ram` over 600 frames of
    `drive_cov1`, before and after).
- **The executable model** (the logic report's `puzlmodel.py`, scratch) equals the original in
  every field of 17 scenarios, 20,280 passes, 0 differences [V]. It is the spec's check.
- **The labels the port provides** (`tools/openmsx_rc2.tcl` looks them up in the ROM's label
  file):

| Label | What |
|---|---|
| `pz_tick` | the `call pz_frame` at the start of every pass, after the wait, `hud_keep` and `sec_tick` (the Amiga's `$171C2`); the breakpoint checks its bytes (CD lo hi), so it fires only where `BANK_PUZL` is mapped |
| `pz_frame` | its target |
| `pz_done` | fixed code (`rc2.asm`), reached once with A = the result, before anything changes the mirror |
| `pz_boards` | F500h: the visit's 4 records in RAM (376 bytes, Amiga order, + `$10` on visited cells) on either visit |
| `ext_joy` | CE5Ah: the byte `joy_read` takes in `EXTJOY=1` builds |

- `rc2_pz_drive` resets the machine with an `EXTJOY=1 PZ_TEST=1` ROM; at each `pz_tick` it records
  the mirror's D000h-D021h, DC00h-DCFFh and the 376 bytes at `pz_boards`, then pokes the pass's
  joystick byte (index `$B00`) into `ext_joy` and that pass's pokes; it stops at `pz_done`.
  `rc2_pz_arm` does the same in the running machine, without a reset: after a level-1 drive the
  game runs on through the statistics and the intro into the stage. `tools/puzlcmp.py` compares 23
  fields (`analysis/puzl_ram.tsv`) plus the 376 board bytes, pass by pass, and the result.
  Display-only state is not compared: the palette, the bitplanes, the message ticker, the music
  divider.
- **The drives** (`build/emu/pz_<name>.drive` and their references `pz_<name>_ram.jsonl`, 4.5):

| Drive | Visit | Passes | Result | What it covers |
|---|---|---:|---:|---|
| `solve1` | 1 | 732 | 0 | the four boards solved (`tools/puzlsolve.py`); score 9,500 |
| `solve2` | 2 (`PZ_LEVEL=2`) | 728 | 0 | visit 2's boards (`$175C0`) solved |
| `fail` | 1 | 182 | 1 | a dead end at (1, 1): stuck at pass 52, MALFUNCTION |
| `timeout` | 1 | 181 | 2 | no keys; `$804C` = FFh poked at pass 100 |
| `fuzz1` | 1 | 619 | 1 | random keys, seed 34: diagonals and fire-toggle repeats, then stuck |
| `fuzz2` | 2 | 606 | 1 | random keys, seed 36 |
| `quirk2` | 1 | 282 | 2 | `solve1`'s keys with `$804C` poked inside board 0's fade-out (pass 140) and at 250: board 1 starts with `$B1A` = 100, its input ignored (quirk 2) |
| `quirk1` | 1 | 732 | 0 | a solve whose 4th board keeps (0, 1) free; pass 602 destroys the last red chip and moves from `message_queue`'s D0 = 0 onto (4, 1), a black chip (quirk 1) |
| `opp` | 1 | 203 | 1 | 19 pokes of `$802E` with opposite directions (02, 0C, 03, 0F, 8C, 05, 0A, 06, 09) at passes 40-108, then a time out; a port with the wrong priority gives 241 passes and result 2 |

- **Results [V]**: every drive gives "0 differ" in all 399 values of every pass and the right
  result, on C-BIOS_MSX2 (V9938, 60 Hz) and the Panasonic FS-A1GT (turbo R, the stage on its Z80);
  `solve1` also on the Panasonic FS-A1FX (MSX2+, V9958) and C-BIOS_MSX2_EU (50 Hz), `solve1` and
  `opp` on the Gradiente Expert 2.0. The 20 traces of the review fixes' run (`14bc5ef`) were
  compared again for this document: 0 differ. The final checks ran the same 20 on `b59a338`'s
  builds: 0 differ (4.6 h).
- **After a played level 1** (`rc2_pz_arm`: `drive_end` on an `EXTJOY=1` build, then `fail`):
  `puzlcmp.py --skip score` (the score starts from level 1's): 182 passes, 398 fields, 0 differ,
  result 1, on C-BIOS_MSX2 and the FS-A1GT. Quirk 1's D0 there follows level 1's messages (8.7).
  A solve after a played level 1, as the second Brainstorm of a session, is in 4.6 e.
- Headless runs never press fire, so every text screen runs its full length: the statistics 362
  ticks, the intro 293, a result 130-144.

### 4.2 Visual checks [V: openMSX runs]

All headless (`set renderer none`); Tcl callbacks never call `exit`, `vwait`, `max` or `min`, and
open files once.

1. **The text screens.** Page 0's play area equals `tools/msxtext.py`'s render of the port's
   script (`text_bs_*.sc5`), pixel for pixel: the intro and OUT OF TIME. on the Gradiente Expert
   2.0, the FS-A1FX, the FS-A1GT and C-BIOS_MSX2 (with TEST 2 at row 10 in a `TAG=2` build on the
   Expert), MEMORY MALFUNCTION. on C-BIOS_MSX2 and the FS-A1GT. The solved text (WELL DONE MEMORY
   RESTORED. / GAME CREDIT AWARDED) first ran in the final checks: equal to its render on
   C-BIOS_MSX2 and the FS-A1GT, and with TEST 2 on the Expert, the HB-F1XDJ and the FS-A1GT (4.6 a
   and e). Screens ended early by fire: 4.6 d.
2. **The stage, still pictures.** Snapshots (VRAM, RAM, registers) at chosen passes: board 0's
   start, the fade-in, mid-solve, each board, the fade-outs with the palette black, the end with
   no cursor and the clean face (12 in `solve1`, 3 in `fail`, `timeout` and `solve2`, on each
   machine). The page R#2 shows, with its sprite set's SAT, equals `tools/msxpuzl.py`'s render of
   that page's shown state (its 110 bytes in the snapshot's RAM) and of the cursor the SAT holds:
   every one equal.
3. **The stage, moving.** A record at every VBLANK of the whole stage (`solve1`, `fail`, `timeout`,
   `quirk2`, `solve2`): every element rectangle of every picture is one of its states (0 torn or
   unknown blocks), no pixel outside the elements differs from the screen's (frame-to-frame
   coherence), and the SAT is valid, holds the bench's cursor of the pass the list was published
   after, and is empty in the end sequences (0 cursor errors). On the MSX2 and the turbo R, and
   `solve1` also on the MSX2+ and at 50 Hz.
4. **The HUD.** Measured on the `solve1` drive in an `EXTJOY=1 PZ_TEST=1` build, where the timer
   stands still at 1:00 (`sec_tick` is a `ret` in script builds: 3.4):
   - at each of its 12 snapshots (passes 5 to 700) the HUD's VRAM (1E800h-1FE7Fh) and its colours
     (`SR_PAL`) equal those of step 6's build (whose stage drew nothing) at the same pass of the
     same drive. Step 7 compared C-BIOS_MSX2's snapshots; for this document the FS-A1FX's and the
     FS-A1GT's (12 passes each) and C-BIOS_MSX2_EU's (its 5) were compared from their files too:
     all equal;
   - the first and the last snapshot (passes 5 and 700) differ only in the score's box (x 200-231,
     y 24-47 of the HUD).

   This check does not cover the HUD's timer while it counts: that was seen, not compared (the
   bonus candidate's still at pass 155, with the real timer, shows 0:59 in the stage's timer and in
   the HUD's). A HUD split at every VBLANK: the display guard (`rc2_guard`, passes 10-633 of
   `solve1`) counts reg 0, pal 0, cpu 0 and vbl 0 on the MSX2, the MSX2+ and the turbo R. Its only
   other entries (cmd 166 / 158 / 165, tear 28) are `bs_board`'s copies into the page on screen at
   the three set-ups, with the palette black: the design (8.1), invisible.
5. **The restore and the next game.** After the stage (`fail`, then the result and a new game, on
   C-BIOS_MSX2 and the FS-A1GT): VRAM 10000h-17FFFh equals `build/msx/level1.vram`, page 3 lines
   0-87 are the intro's, both SATs start with Y = 216. At the new game's frame 50, against a fresh
   start: page 2, the atlas, the HUD and the mirror D000h-DFFFh are equal; the sprite tables
   differ in 72 bytes, both harmless: the colour rows of SAT entries 0-1 (the hit spark's, parked:
   the engine rewrites them before use) hold the cursor's colours, and entries 30-31 the same two
   states in the other set (the engine's set phase is one flip apart; those sprites sit at Y
   193-197, under the split). `tools/checkrun.py` on the pictures: 0 pixels differ, every sprite
   pixel exact. Lost counters 0.
6. **50 and 60 Hz.** The same pictures (3 above, at 50 Hz too), and the timer counting real seconds
   in a `PZ_TEST` build: board 0 left alone times out about 61 s after its set-up (3.4).
7. Previews for the user: plain and graded, Amiga against MSX (`build/msx/puzl_1_*.png`).

VRAM access speed: the "0 too fast" that step 7, the review fixes' suite and step 8's suite reported
over `solve1` (`rc2_count_too_fast`, with the entry's uploads and the exit's restore) was not a
measurement: the counter did not count before `b59a338`. The measurements, at 3.58 and 5.37 MHz,
and the fix they led to are in 4.6 g.

### 4.3 Sound checks (milestone 2)

**Offline** [V, 2026-10-27: scratch tools on the branch's images; no emulator]. A Z80 interpreter
runs the images' own code, with the mapper, the PSG, the SCC and the OPLL modelled and every chip
write logged; the expected registers come from `pzm.bin` decoded apart with the converters' own
decoders, the effects' schedule from `$1822C`'s rule modelled apart.
- Tools: TITM tune 1 through the routing gives today's three outputs byte for byte;
  `rc2music.py --verify` on PZM 0 differences; every PZM stream lasts 3,000 ticks
  (`tests/test_msxtune.py`, 16 tests).
- The images of 23 build option sets against main's, built with the same options, bank by bank:
  bank 1 only in `fx_tk`'s operand, `BANK_MUSIC` only past main's `music_end`, `BANK_PUZL` only by
  the stage's three edits (undone, main's listing exactly), banks 86-87 `pzm.bin`. 1,771 option
  sets build as on main, each with main's `code_end`.
- The title (four chip sets, 50 and 60 Hz) and level 1's 42 effects, the gun and a burst (SCC and
  PSG): main's chip writes, write for write; the title's executed instructions the same.
- PZM's registers per tick against the streams, on the SCC with the PSG drums, the SCC with the
  OPLL's rhythm, the OPLL alone and the PSG alone, at 50 and 60 Hz: the whole tune and its end;
  effects (moves, a red chip refused, moves during 5 refused, the 31 restarts of 6, two requests
  before one tick, effects after the tune's end); a board's restart with its jingle; `snd_stop`
  with the PSG alone; a stop queued right before the tune (H7); the R800 (no OPLL write); the
  interrupt rule; the SCC store rule.
- `$1822C`'s rule at its edge against `tools/rc2music.py`'s 68000 model: every pair of effects, the
  lower one 1, L - 1, L and L + 1 ticks after, on four chip sets: 256 cases, 0 differences.
- A board's start: 608 cases at 50 Hz and, at 60 Hz, for every phase of the passes' and the ticks'
  dividers (3.6). The build before the fix fails them.
- The title after the stage: as the title after main's silent stage, write for write, in the
  product's flow (the power-on title, level 1's effects, the stage left alone to its time out, the
  result) and a `PZ_TEST` build's, on four chip sets; as on a fresh machine when the stage comes
  first. After a played level 1 the power-on title is no reference, on main either: with the PSG
  alone the title's first records write, while silent, the tone periods level 1's effects left in
  the PSG player's voices (3.6). Level 1's effects after the stage: as on a fresh machine, write
  for write.

**In openMSX** [V, 2026-10-27, at `74b9901`, the merge of main `a90e77a`: the sound's emulator
plan, with scratch scripts outside the repository; one openMSX at a time, headless]. Every image
was rebuilt and compared bank by bank with main's twin (main's sources, the same options): only
banks 1, 9, 78 and 86-87 differ, and main's tree rebuilds the user's four test2 ROMs byte for byte.
- The title, register-exact: `TAG=3` and its 2 MiB twin on a power-on Gradiente Expert 2.0 against
  the night's step-0 reference: VRAM, registers, palette, the 5,046 music ticks and every PSG write
  identical; at game tick 300 the RAM differs only in `$B32` (3.6, level 1's random choices). On 11
  chip sets the title's chips, logged tick by tick, equal main's twin's.
- Level 1: the coverage drives (4,401, 1,400 and 1,400 frames on an MSX2, an MSX2+ and a turbo R)
  0 differ; its effects (`LOCKSTEP` builds) equal main's write for write (423 effect starts), also
  after a fully played stage, on 7 chip paths.
- The stage: the nine drives (20 traces) 0 differ, as the silent stage's; the stills, records and
  display guard as in 4.2 (one torn cell: board 1's set-up while the VDP's palette is black,
  invisible); VRAM speed 0 lost writes at 3.58 and 5.37 MHz; the tenth drive, after a played
  level 1, 0 differ; the real timer times out 60.6-60.9 s after the first pass at 50 and 60 Hz.
- PZM's registers per tick against the streams decoded apart, 20 runs: the cartridge's SCC, an SCC
  and an SCC+ in another slot, SCC + OPLL, the OPLL alone, the PSG alone, at 50 and 60 Hz, on an
  MSX2, an MSX2+ and a turbo R: 0 differences. The jingle with tick 0 (3 of 3); the refusals and
  the buzz's restarts as `$1822C`'s rule gives them; the tune's 3,001 ticks, then no chip write to
  the time out (14 runs).
- The title after the stage against the title after main's silent stage: 28 pairs PASS, among them
  the SCC+, an FM-PAC, the OPLL alone and the turbo R's OPLL. Only stages left to their time out
  were logged; an exit mid-tune (WELL DONE, MALFUNCTION) is checked offline only (above).
- The candidates: `tools/msxmatrix.py` 10 of 10 set-ups for each; power-on machines through the
  product's flow, the bonus ROMs' keyboard moves, OUT OF TIME. and WELL DONE: every lost counter 0.
- Audio, nine recordings by pitch against the converters' renders, each read at its own tick rate
  (49.936 Hz on a 60 Hz VDP, 50.159 Hz on a 50 Hz one): 96.8 % (the SCC), 96.3 % (the OPLL alone)
  and 99.5 % (the PSG) the same note; SCC + OPLL 93.9-94.9 % on ticks without drums (its drums are
  the OPLL's rhythm); the tune's end 54-125 dB under its peak; the buzz 49.2-50.0 Hz. Read at
  50.000 ticks a second, a 60 Hz recording drifts 77 ms by the tune's end, and the OPLL alone first
  measured 87.7 %: a defect of the measuring script, found by the evidence audit, not of the sound.
- Limits: the MCP home's HB-F1XDJ has no MSX-MUSIC, so the MSX2+ ran the SCC alone and the PSG
  alone; SCC + OPLL ran on the Expert with an FM-PAC and on the FS-A1GT. The 2 MiB product was
  checked to game tick 300 and in the matrix, not through the stage (its 1 MiB twin was).

### 4.4 Regression [V]

| Check | How | Result |
|---|---|---|
| Level 1's logic | the EXTJOY coverage drives (`rc2_drive_rom`, `drive_cov1` and `drive_cov0`) on an `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1` build, `tools/tracecmp.py --ram` against `build/emu/trace_cov*_ram.jsonl` with that build's `--labels` | 4,401 frames on C-BIOS_MSX2, 1,400 on the FS-A1FX and the FS-A1GT: 0 differ, after every step |
| The image | each step's ROMs against the previous step's, bank by bank | step 3: 296 bytes of former padding (FRONT, bank 45); step 4: banks 0-77 identical to `52149b0`'s; step 5: the code banks (the flow); steps 6 and 7: only bank 78 differs; the review fix: FRONT, and in banks 0 and 78 only the words of FRONT's labels that moved; the final checks' fix (`b59a338`): only bank 78. The data banks 10-77 never changed |
| The title | on a fresh Gradiente Expert 2.0 from power-on: the title's VRAM, registers and palette 1 s after it shows, the music (5,046 ticks of SCC and PSG registers), the PSG writes of the speech (their hash), the game's VRAM and RAM at tick 300 | identical to `52149b0`'s after every step |
| The flows | the product (the title, level 1 ended by `drive_end`'s teleport and poke, the statistics, the intro, the stage left alone to its time out, OUT OF TIME., the title, fire, a new game) and `PZ_TEST=1` from power-on, on the Gradiente Expert 2.0 and the FS-A1GT | the intro and the result pixel-exact, a HUD split at every VBLANK (4,075 / 4,075 and 4,078 / 4,077-4,078), the title, a new game |
| Bench game mode | 600 frames of `drive_cov1` before and after the bench patch | byte-identical |
| Set-ups | `make matrix` (`tools/msxmatrix.py`: MSX2, MSX2+, turbo R, 50 Hz, a disk interface before the cartridge, a slot expander, an FM-PAC, a 2 MiB MegaRAM with an SCC, an SCC+, none) on the product | all 10 PASS, the same lines as at `52149b0` |
| Option sets | the review's 41 option sets built | all but `DEMO_ACTORS=2`/`5` and `DEMO_HUD=1`, which fail with the same fixed-area overflow at `52149b0` |
| Losses | `mp_lost`, `atr_lost`, `rd_lost`, `fb_lost` | 0 |
| Unit tests | `make test` | 78 tests at `14bc5ef`, 86 with step 8's, 109 at `b59a338` (with `tests/test_bstest.py`'s 23, `70e775b`): the same 4 failures as before tonight (`test_tools`: the sprite data and the joystick script) |

A `PZ_TEST` ROM shows no title, which `make matrix` would report as FAIL: `tools/msxmatrix.py
--no-title` (`cae5193`, step 8) checks it instead, without the title wait: `tick_n` must advance
between samples at 20 s and 27 s from the power-on (the stage's passes), with the display on and
no DI; HALT. `make matrix` has no option for it: run the tool (`--home DIR` where `make matrix`
takes `OMHOME=DIR`):

```sh
python3 -I tools/msxmatrix.py build/msx/rc2.rom --labels build/msx/rc2.labels --no-title
```

### 4.5 Running the checks

Everything runs from the repository root. `PY=~/.venvs/msxports/bin/python` (Unicorn) runs the
bench; the other tools need only `python3`. Build harness and candidate ROMs outside `build/msx`
(the user picks ROMs from there; `make rom` writes only `build/msx/rc2.rom`); `gen/` lands next to
the ROM and the label file is the ROM's name with `.labels`.

**The references** (`build/emu/`, git-ignored; each command prints the PUZL frames and D0):

```sh
$PY -I tools/puzlsolve.py build/emu/pz_solve1          # the solution, its drive and the bot's trace
$PY -I tools/amigaemu.py puzl --pframes 2000 --drive build/emu/pz_solve1.drive \
    --trace build/emu/pz_solve1_ram.jsonl --trace-ram
$PY -I tools/puzlsolve.py --level 2 --ram build/ram/level2_full.bin build/emu/pz_solve2
$PY -I tools/amigaemu.py puzl --level 2 --ram build/ram/level2_full.bin --pframes 2000 \
    --drive build/emu/pz_solve2.drive --trace build/emu/pz_solve2_ram.jsonl --trace-ram
python3 -I tools/drivejoy.py --joy 40:1:d,42:1:d,44:1:r,46:1:r,48:1:u,50:1:l build/emu/pz_fail.drive
python3 -I tools/drivejoy.py --poke 100:0x804c:0xff:1 build/emu/pz_timeout.drive
python3 -I tools/drivejoy.py --fuzz 34 build/emu/pz_fuzz1.drive      # (36: pz_fuzz2, visit 2)
python3 -I tools/drivejoy.py --joy "$(paste -sd, build/emu/pz_solve1.joy)" \
    --poke 140:0x804c:0xff:1,250:0x804c:0xff:1 build/emu/pz_quirk2.drive
$PY -I tools/puzlsolve.py --quirk1 build/emu/pz_quirk1
```

Each drive's reference is `amigaemu.py puzl --pframes 2000 --drive build/emu/pz_<name>.drive
--trace build/emu/pz_<name>_ram.jsonl --trace-ram` (3000 for the fuzz drives, `--level 2 --ram
build/ram/level2_full.bin` for visit 2). `pz_opp.drive` holds the 19 `$802E` pokes of 4.1.

**The MSX trace.** Build `EXTJOY=1 PZ_TEST=1` (add `PZ_LEVEL=2` for `solve2` and `fuzz2`; harness
builds keep `TAG=0`):

```sh
python3 -I tools/mkrom.py build/msx/level1 OUT/rc2_pz1.rom EXTJOY=1 PZ_TEST=1
```

Then in openMSX (MSX-AI MCP `msx_local_cmd`; braces around paths with spaces), on a machine of
the local set at 3.58 MHz:

```
set ::z80_freq 3579545; set throttle off; set ::pause off;
source {<repo>/tools/openmsx_rc2.tcl};
rc2_pz_drive {OUT/rc2_pz1.rom} {OUT/rc2_pz1.labels} {OUT/pz_solve1_msx.txt} 2000 0 {<repo>/build/emu/pz_solve1.drive}
```

It answers "driving PUZL into ...; poll ::rc2_trace_done" (a missing label is an error). Poll
`set ::rc2_trace_done` with short calls (never `vwait`) until 1, then `set ::rc2_pz_result`
(0/1/2; −1 if the stage did not return); the machine is then paused. The arguments `n` (2000:
lines at most) and `from` (0: the first pass recorded) match a reference made with
`amigaemu.py puzl --trace-from F --pframes F+N-1`. Compare:

```sh
python3 -I tools/puzlcmp.py build/emu/pz_solve1_ram.jsonl OUT/pz_solve1_msx.txt
# 732 PUZL frames compared (732 Amiga, 732 MSX), 399 fields: 0 differ
# result: Amiga 0, MSX 0
```

On a difference it prints up to `--show N` lines "PUZL frame F (keys): name amiga/msx" and exits
1; different row counts or results exit 1 too.

**After a played level 1.** An `EXTJOY=1` build: `rc2_drive_rom {ROM} {LABELS} {OUT/end.txt} 200 0
{<repo>/build/emu/drive_end.txt}`, poll `::rc2_trace_done`, then `rc2_pz_arm {LABELS}
{OUT/pz_fail_arm.txt} 2000 0 {<repo>/build/emu/pz_fail.drive}` (it resumes the machine: level 1
ends, the statistics run 362 ticks and the intro 293, then the stage), poll again, and compare with
`puzlcmp.py --skip score`.

**Still pictures.** At a pass, save VRAM (`save_debuggable VRAM FILE`) and RAM C000h-FFFFh
(`debug read_block memory 0xC000 0x4000`; `rc2_snap` leaves out EE00h-EFFFh), then `python3 -I
tools/msxpuzl.py render build/extracted/files/PUZL_25.bin RAM.bin OUT --offset 0x2E20 --cursor
C,R,I` (`rd_st0`, EE20h, when R#2 shows page 0; `0x2E90`, `rd_st1`, for page 1; the cursor as
that set's SAT holds it) and compare `OUT.sc5` with the page's lines 0-161 and its sprites (SAT Y
= 1 + 16r shows from line 2 + 16r). The record, still, HUD, restore and flow checks of 4.2 and 4.4
first ran on the night's scratch scripts (`impl/` of its scratch folder: section 9).

**The harness.** Those scripts are now in `tools/bstest/` (`70e775b`), and `docs/HARNESS.md` is
their manual: the files, the reference files each check needs, a session in the MCP's openMSX, the
checks of 4.1, 4.2 and 4.4 with their commands and expected results, the whole suite in order, and
what milestones 2 and 3 must add (4.3's sound checks are not in it yet). When they moved they were
checked without an emulator only (`docs/HARNESS.md` 9): the Tcl's first real run is the next
milestone's suite. Their VRAM-speed count, `rc2_count_too_fast` (`tools/openmsx_rc2.tcl`), counts
from `b59a338` on (4.6 g). The final checks' own scripts (4.6) are not in `tools/bstest/`.

**Unit tests**: `tests/test_puzl.py` (11: the solver, the compare, the fuzz keys, the Tcl procs in
`tclsh` with openMSX mocked; the bench case needs Unicorn), `tests/test_msxpuzl.py` (17),
`tests/test_bonus_text.py` (16), `tests/test_bstest.py` (23: the harness, without an emulator), all
in `make test`.

### 4.6 The final checks (`b59a338`)

The final checks (2026-10-27, 06:10-06:55) ran the paths a completeness critic found no check had
run, and measured the VRAM access speed again with a counter that counts; that led to `b59a338`
(g). They ran on headless openMSX through the MSX-AI MCP, one instance at a time. Their own scripts
stayed in the night's scratch folder (`impl/final`: `np.tcl`, `ft.tcl`, `titlecmp.py`,
`titlecmp2.py`, `partialcheck.py`; section 9). For this document the trace compares, the text
screens against `tools/msxtext.py`'s renders, the fire snapshots, the title's per-tick music logs,
the game's RAM and VRAM at tick 300, the speed and watchpoint logs, the matrix logs and the ROM
images were checked again from that run's files, without an emulator. Everything below is
[V: openMSX] unless marked **I**.

**a. The solved ending.**
- `solve1` from the power-on (`EXTJOY=1 PZ_TEST=1`) on C-BIOS_MSX2 and the FS-A1GT: 732 passes, 399
  fields, 0 differ, result 0. WELL DONE MEMORY RESTORED. / GAME CREDIT AWARDED equals
  `build/msx/text_bs_ok.sc5` byte for byte; AG `$805E` = 1 after it; 1,237 VBLANKs and 1,238 HUD
  splits between the intro's and the result's records; then a new game (an `EXTJOY` build has no
  title).
- With the candidates' options (`PZ_TEST=1 TAG=2`, no script) on the Gradiente Expert 2.0, the
  drive's bytes pressed as the cursor keys and SPACE (keyboard row 8) at each `pz_tick`: 732
  passes, 0 differ in 395 fields (`puzlcmp.py --skip joy,last_joy,timer_min,timer_sec`: the keyboard
  sets bit 7 of `$802E` and `$B1E`, and a build without a script counts real seconds), result 0.
  WELL DONE with TEST 2 equals its render; then the title, fire and a new game.

**b. The title after Brainstorm, against the approved title.**
- The product's flow (the title, level 1 ended by `drive_end`, the statistics, Brainstorm left to
  its time out, OUT OF TIME.) and a record of the title that follows, on the Expert, the Sony
  HB-F1XDJ (V9958) and the FS-A1GT. The reference is the approved flow: step 0's ROM (no
  Brainstorm) through the same drive, recorded at the title that follows level 1's statistics. Each
  record logs the music by music tick (the SCC's and the PSG's registers, the count and hash of the
  PSG writes since the tick before) and takes the game the title starts by itself at exactly its
  tick 300.
- After Brainstorm against without it:
  - the title's picture (G7, 256 × 212) and palette are identical on all three. So are the VDP
    registers, but for R#5 (C7h/CFh) and R#19 (9Ch/9Dh) on the FS-A1GT; R#8 has the sprites off and
    R#0 the line interrupt off in both. Against a fresh start R#19 and the palette differ in both
    flows (and R#5 on the HB-F1XDJ, also in both);
  - every PSG write is identical at all common ticks: 5,044 ticks and 150,851 writes (5,045 and
    130,432 on the FS-A1GT). The PSG registers are identical but R6, the noise period, on the
    FS-A1GT, where R7 keeps the noise off on all three channels at every tick. The SCC's registers
    are identical on the Expert; on the HB-F1XDJ and the FS-A1GT only A6h/A7h (channel 3's
    frequency) and their mirror B6h/B7h differ, and channel 3 stays disabled (AFh = 07h) at volume
    0 at every tick;
  - VRAM outside the title's picture differs;
  - the game at tick 300: RAM D000h-DFFFh differs only in the random word `$B32` (D032h-D033h,
    seeded from R) and, on the Expert, in the level timer's seconds (DC4Ah: 9:45 after Brainstorm,
    9:44 without it, 9:47 on a fresh machine). VRAM differs in 9,615 bytes on the Expert (29 of
    them in the HUD: rows 5-18, x 240-251), 23,963 on the HB-F1XDJ and 26,795 on the FS-A1GT (none
    in the HUD); a fresh start and the approved flow already differ in 32,780-35,296 bytes there.
- The timer's seconds at tick 300 depend on what ran before the game: the approved flow already
  differs from a fresh machine there (9:44 against 9:47).
- **I**: nothing that differs is seen or heard. R#5 and R#19 do nothing with the sprites and the
  line interrupt off; channel 3 is silent; the noise period does nothing with the noise off. The
  Expert's 29 HUD bytes are that timer's seconds digit. The game's other differences are of the
  kind a fresh start already has.
- Records polled every 0.1 s had first suggested a PSG difference (151,182 against 151,212
  writes): their windows started a tick or two apart. The per-tick logs above settle it.

**c. The 2 MiB product's level end into Brainstorm.** `test2-2M` (`TAG=2 ROM_2M=1`) on the
Expert, through the product's flow: the intro and OUT OF TIME. with TEST 2 equal their renders,
4,075 VBLANKs and 4,075 HUD splits between them, then the title, fire and a new game. The 1 MiB
product had run the same flow (4.4, section 6).

**d. Text screens ended by fire.** `test2-bonus` (`PZ_TEST=1 TAG=2`) on the Expert and the
FS-A1GT, SPACE held for 0.15 s:
- at the intro's `fs_n` 60: the snapshot just before the press equals the render of 60 `fs_step`
  calls (TEST 2, then 56 of the intro's 95 characters); the intro ends at `fs_n` 61, and the stage's
  first pass comes 0.72 s (the FS-A1GT: 0.75 s) after the press;
- the stage that follows, stuck from the keyboard (the `fail` drive's moves: 182 passes, result 1),
  equals the render in its 7 snapshots;
- at the result's `fs_n` 61 (the FS-A1GT: 60): MEMORY MALFUNCTION. is complete (its 38 characters
  after TEST 2) and equals its render; the screen ends at the next call, and the title starts 0.02
  s after the press;
- the title ignores the SPACE still held: the new game comes from the later fire. Lost counters 0.

**e. A second Brainstorm in one session.**
- A script build (`EXTJOY=1 PZ_TEST=1`) on C-BIOS_MSX2 and the FS-A1GT: the first stage (`fail`:
  182 passes, 399 fields, 0 differ, result 1), its result, a new game; level 1 ended by `drive_end`
  (its frames moved by the new game's `tick_n`), the statistics, the intro; the second stage by
  `rc2_pz_arm` with `solve1`: 732 passes, 398 fields (`--skip score`), 0 differ, result 0; WELL DONE
  equal to `text_bs_ok.sc5`, AG `$805E` = 1, a new game.
- With the candidates' options and the keyboard, on the Expert, the HB-F1XDJ and the FS-A1GT: the
  first stage (182 passes, 395 fields, 0 differ, result 1), the title, fire, a new game, level 1
  ended, the statistics; the second stage (732 passes, 394 fields, 0 differ, result 0); WELL DONE
  with TEST 2 equal to its render; the title, fire and a new game.
- In the FS-A1GT's script run, `bonuscheck.py` (the night's copy; `tools/bstest/`'s has the same
  test) reported FAIL: its intro record read R#1 = 22h (`R1_BLANK`, the display off) with R#2 = 7Fh
  and R#23 = 29h (`R2_PAGE3`, `HUD_R23`: the HUD split's state, `msx/msx.inc`). **I**: a sampling
  artefact, not a display off: the record fell in the split's blank lines, between its interrupt
  and the HUD. The intro equals its render, and 1,237 HUD splits came in 1,238 VBLANKs between the
  records (8.17).
- Quirk 1 (8.7) did not show. In pass 602, which destroys the 4th board's last red chip, `solve1`'s
  joystick byte goes from 8 to 0 [V: the bench's trace]: a change without a direction bit, so the
  clobbered D0 moves nothing.

**f. Turbo R: no write to 4000h-7FFFh.** On a turbo R the fixed area runs from a RAM copy in page
1, and nothing may write 4000h-7FFFh after the copy (`docs/TURBO_R.md` 6). The product on the
FS-A1GT, through its whole flow (the title, level 1, the statistics, Brainstorm to its time out,
the title, a new game), with a write watchpoint on 4000h-7FFFh from `front_bonus`' entry (43.2 s)
to the new game's tick 100 (124.7 s): 0 writes.

**g. VRAM access speed at 5.37 MHz, and `rs_one`'s fix.**
- **The counter.** `rc2_count_too_fast` (`tools/openmsx_rc2.tcl`) set
  `VDP.too_fast_vram_access_callback` to an inline script. openMSX runs a callback setting's value
  as a command (its own `callbackprocs.tcl` puts a proc's name there), so the script failed
  silently and nothing was counted. The run showed it with an OTIR loop at 10.74 MHz: 0 with that
  form, 725-729 lost writes with a proc's name (no file kept). So every "0 too fast" before
  `b59a338` was not a measurement (4.2). `b59a338` names a proc, `rc2_too_fast_cb`. A run at
  another Z80 speed must also set `z80_freq_locked off`: `hz_cfg` (`tools/bstest/hz.tcl`) locks it,
  and openMSX ignores `z80_freq` while it is locked.
- **The fix.** `rs_one` (`msx/puzl.asm`) writes the cursor's SAT entry: Y, X, the pattern, 0. Its X
  write and its last write came 17 T after the write before (`ld a,e` / `xor a`, then `out`). A
  `nop` before each makes the gaps 22, 27 and 22 T: two bytes in `BANK_PUZL`. The stage's other
  VRAM streams [V: the source, timed per instruction with the MSX's M1 wait]: the uploads' OTIRs
  (`rd_line`, `rd_rom`) and `fs_char`'s for the TEST line 23 T a byte, the cursor patterns 57 T,
  the colour rows 30 T, `rd_hide` one write.
- **Measured** with the working counter (`too_fast_vram_access real`): `solve1` on an `EXTJOY=1
  PZ_TEST=1` build from the power-on to `pz_done` (the intro, the entry's uploads, 732 passes, the
  exit's restore):

| Machine, Z80 | Before (`14bc5ef`'s code) | After (`b59a338`) |
|---|---|---|
| Panasonic FS-A1FX, 5.37 MHz | 5 lost writes, all at `rs_one`'s two 17 T writes (A8A5h, A8ADh) | 0 |
| C-BIOS_MSX2+, 5.37 MHz | 43 at `rs_one`, 1 in C-BIOS | 0 in the cartridge, the same 1 in C-BIOS |
| C-BIOS_MSX2, the FS-A1FX, the FS-A1GT, 3.58 MHz | 0 | 0 |

  All these traces compare with the bench's with 0 differences.
- The whole bonus flow at 5.37 MHz, `test2-bonus` from the power-on (the intro with TEST 2, the
  stage solved from the keyboard, WELL DONE with TEST 2) to the title's start: step 8's candidate
  lost 8 writes on the FS-A1FX and 55 on C-BIOS_MSX2+, all in `rs_one`; the final candidate 0 in the
  cartridge on both.
- C-BIOS_MSX2+'s own 1-2 lost writes (05B0h, 05B3h) come at 3.49 s, before the cartridge's init
  (3.53 s), with C-BIOS's return address 065Ah on the stack; at 3.58 MHz it loses none. The
  FS-A1FX's own BIOS loses none at 5.37 MHz.
- **I: the model.** openMSX's V99x8 serves a CPU access at the first access slot at least 16 VDP
  cycles after the request, and in a bitmap mode with sprites on its slots are up to 70 cycles
  apart (`VDPAccessSlots.cc`), so a gap of 86 cycles or more is always safe. One T state is 4 VDP
  cycles at 5.37 MHz (22 T: 88 cycles; 17 T: 68) and 6 at 3.58 MHz (17 T: 102). That a real V9938
  or V9958 behaves the same is not verified here.
- **Level 1 at 5.37 MHz**, for the record (not tonight's code, unchanged): `drive_cov1`'s first
  1,399 ticks on the FS-A1FX lose 790 writes, and the eight PCs the run logged (6AA6h-6AD4h) are
  all in `outi32`/`outi16`, the sprite engine's 18 T OUTIs (72 cycles); at 3.58 MHz none. **I**:
  the other 782 are there too, and by the model 22 T there would be safe. The user's call (8.16).
  (Brainstorm's own losses, by contrast, are all in `rs_one`: the fix changed nothing else and
  took the cartridge's count to 0.)

**h. The acceptance suite and the candidates, on `b59a338`.**
- The six harness builds again, with the fix (`pz1` is g's "after" build), and the suite of
  4.1-4.4, with the same results: the 20 traces 0 differ with their results; stills 0 differences;
  records with 0 torn blocks, 0 pixels outside the elements and 0 cursor errors (`solve1`: 470,
  465 and 460 pictures in 922, 921 and 922 VBLANKs on the MSX2, the turbo R and the MSX2+; 429 in
  766 at 50 Hz); the display guard's reg, pal, cpu and vbl 0, its cmd and tear entries only at
  `bs_board`'s three set-ups with the palette black; the speed count at 3.58 MHz, now counting, 0
  on C-BIOS_MSX2 and the FS-A1GT; the level-1 regression 0 differ; the title equal to step 0's
  record; the four flows PASS; the restore with only the known 72 sprite-table bytes; the turbo R's
  blank 6 frames. `make test`: 109 tests, the 4 known failures only.
- The four candidates of section 6, rebuilt at `b59a338` (a second rebuild gives the same images
  and label files): against step 8's only bank 78 differs, where `puzl_end` moves from ADFCh to
  ADFEh. The matrix: 10 set-ups each, all PASS, every log equal to step 8's line for line. Fresh
  machines, as in step 8: `test2`'s title, music and game start equal step 0's record (`test2-2M`:
  all but `$B32`); the products' whole flow PASS on the Expert and the HB-F1XDJ; the bonus ROMs
  with five keyboard moves (`test2-bonus` on the Expert and the HB-F1XDJ, `test2-bonus-2M` on the
  Expert): the text screens equal their renders, 56 stills each equal the render, 500 pictures
  each with 0 torn blocks, 0 changed pixels outside the elements and 0 cursor errors; and `solve1`
  from the keyboard on the Expert: WELL DONE with TEST 2, 6 stills equal.

## 5. Implementation record

| # | Step | Commit | Files | Result |
|---|---|---|---|---|
| 0 | Baseline | — | none | a scratch build of `52149b0` byte-identical to `ROBOCOP2_v0.1.3-test1.ROM`; the level-1 regression and the title's record taken |
| 1 | The bench in the repository | `91d9b85`, `d37ae56` | `tools/amigaemu.py` (`puzl`), `tools/puzlsolve.py`, `tools/puzlcmp.py`, `analysis/puzl_ram.tsv`, `tools/openmsx_rc2.tcl` (`rc2_pz_drive`, `rc2_pz_arm`), `tools/drivejoy.py` (`--fuzz`), `tests/test_puzl.py` | the references of 4.1; the game mode byte-identical |
| 2 | The converter | `f4e2462` | `tools/msxpuzl.py`, `tests/test_msxpuzl.py`, `Makefile` | byte-identical to the graphics report's prototype; its checks pass |
| 3 | Texts and HUD messages | `ac31d65` | `tools/msxtext.py`, `tools/msxhudrt.py`, `tests/test_bonus_text.py`, `Makefile` | the four scripts and their renders; messages 174-176; level 1's bytes unchanged |
| 4 | ROM layout | `7e44db5` | `tools/mkrom.py`, `msx/rc2.asm`, `msx/puzl.asm` (a stub) | `BANK_PUZL` = 78 (3.10), graphics 79-85, 86 banks, 1 MiB; banks 0-77 byte-identical to `52149b0`'s |
| 5 | The flow | `d6239ec` | `msx/rc2.asm` (hook, `pz_done`, `pz_test`), `msx/front.asm` (`front_bonus`, `fe_text`), `msx/hud.asm` (`hud_keep`), `msx/msx.inc` | the stub's intro and OUT OF TIME. pixel-exact through both paths, on the MSX2, MSX2+ and turbo R |
| 6 | The stage's logic | `9cc1512` | `msx/puzl.asm`, `msx/msx.inc` | the nine drives 0 differ (4.1); the display black for now |
| 7 | The stage's display | `2eefba4` | `msx/puzl.asm`, `msx/msx.inc` | 4.2 checks 2-6; traces still 0 differ |
| — | The review's fixes | `14bc5ef` | `msx/front.asm`, `msx/cold.asm` (a comment), `Makefile` | the turbo R's PAUSE during the bonus screens; `make matrix` with a home path holding spaces (section 10) |
| 8 | The morning ROMs | `cae5193` (the tool) | `tools/msxmatrix.py` (`--no-title`), `tests/test_msxmatrix.py`; outside the repository, four candidates with their notes (section 6): `ROBOCOP2_v0.1.3-test2` (`TAG=2`), `-test2-bonus` (`PZ_TEST=1 TAG=2`), `-test2-2M` (`TAG=2 ROM_2M=1`) and `-test2-bonus-2M` (`PZ_TEST=1 TAG=2 ROM_2M=1`) | all four built from `14bc5ef`'s sources (the PAUSE fix; a rebuild at `cae5193` gives the same four images); the products pass the ten set-ups in title mode and the bonus ROMs with `--no-title`; the fresh-machine runs pass (section 6); the notes give each file's SHA-256 and say that the stage is silent and that a `PZ_LEVEL=2` visit shows Murphy |
| 9 | Documentation | `b99784e`, `a050d0a`, then the completeness review's fixes (section 10) | `analysis/puzl_17100.sym`, `analysis/ghidra_seeds_puzl.tsv` (`tools/ghidra_seeds.py`, `tools/ramimage.py`: the image with PUZL at `$17100`); this file, `docs/MSX_ARCHITECTURE.md`, `docs/AMIGA_ANALYSIS.md`, `docs/ROM_BUDGET.md`, `docs/TURBO_R.md`, `README.md`, `tools/msxpuzl.py` (comments only); the review's fixes: this file, `README.md`, `Makefile` | REA accepts the new seeds (0 failed); `make -n matrix` with a `~/` home and with a spaced one |
| — | The harness in the repository | `70e775b` | `tools/bstest/` (the night's scratch scripts of 4.2 and 4.4), `docs/HARNESS.md`, `tests/test_bstest.py` | 23 tests; checked against the night's records without an emulator (`docs/HARNESS.md` 9) |
| — | The final checks | `b59a338` | `msx/puzl.asm` (`rs_one`: two `nop`s), `tools/openmsx_rc2.tcl` (`rc2_count_too_fast` names a proc) | the paths no check had run; the VRAM speed at 5.37 MHz; the suite again; the four candidates rebuilt (4.6) |

**Milestone 2: sound**, as built on the branch `bs-sound-int` (its offline and openMSX checks:
4.3).

| # | Step | Commit | Files | Result |
|---|---|---|---|---|
| 10 | The routing step; PZM tune 1 in three chip versions; effects 3-6, 6 designed | `05b0674` | `tools/msxtune.py`, `tests/test_msxtune.py`, `Makefile` | TITM's three outputs byte-identical through the routing; `pzm.bin` 12,734 B (SCC 6,884, OPLL 3,580, PSG 1,878, the effects) |
| 11 | The player and the effect voice, on the SCC, the OPLL and the PSG | `534b1a7`, `c29d614` (docs), `37eece0` (a comment), `4d6da96` (the sound review's fix: busy for L + 1 ticks, `$1822C`'s edge) | `msx/tune.asm`, `msx/sound.asm`, `msx/msx.inc`, `msx/rc2.asm`, `tools/mkrom.py` (`pzm.bin` from bank 86, `tune.inc`, `pzm_check`), `docs/MSX_ARCHITECTURE.md`, `docs/AMIGA_ANALYSIS.md` | PZM's registers per tick equal the streams on the four chip sets; the title's and level 1's chip writes as before; the refusals at `$1822C`'s edge the 68000's |
| 12 | The wiring, after merging main | `284e861` (main `14bc5ef`), `188e791`, `d16b730` (main `cae5193`) | `msx/puzl.asm` | the set-up's tail starts tune 1; `bst_go` sends the request; the mirror untouched |
| — | The integration review's fixes | `413561c`, `3f2330d` | `msx/sound.asm`, `msx/tune.asm`, `msx/puzl.asm`, `msx/rc2.asm` (`msx/sndtune.asm` removed), `msx/msx.inc`, `tests/test_msxtune.py` | the fixed area as before the sound, so every option set main assembles still assembles (1,771 built); the jingle with the tune's tick 0 (608 cases, 3.6) |
| — | Documentation | `9b2ba67` (main's texts as the base), then this file's commits | this file, `README.md`, `docs/MSX_ARCHITECTURE.md`, `docs/ROM_BUDGET.md` | — |
| — | The emulator checks | `74b9901` (the merge of main `a90e77a`); no code change | — | 4.3's openMSX checks PASS; the test3 candidates (section 6) |

**Milestone 3: the second visit** (the plan; before level 2 exists).

| # | Step | Files | Acceptance |
|---|---|---|---|
| 13 | Ellen: visit 2's palette and TV pictures; the cursor's colour | `tools/msxpuzl.py` (`--visits 1,2`, ready), `tools/mkrom.py`, `msx/puzl.asm` | `PZ_LEVEL=2` pictures equal the previews; 92 banks; the user's choice on the palette reset (section 7) |

## 6. Test builds

| Option | Default | Effect |
|---|---|---|
| `PZ_TEST=1` | 0 | power-on without the title → level 1's set-up (`ng_go`, unchanged) → once, instead of the main loop (`pz_test`): AG `$8050` = `PZ_LEVEL`, `cpu_title` (a turbo R: the Z80, as after `front_stats`), then `front_bonus`, the title and a new game. A one-shot flag (`pz_first`, C6FFh, set by `init`) keeps later new games normal. 30 bytes of fixed code, only in these builds |
| `PZ_LEVEL=n` | 1 | the visit for `PZ_TEST`: 1 (after level 1) or 2 (after level 2) |
| `EXTJOY=1` | 0 | the stage reads `ext_joy` (the trace harness); the timer stands still |
| `JOY=...` | none | a script by `tick_n`: the stage's passes continue it |
| `TAG=n` | 0 | test candidates (1-99): `fe_text` draws "TEST n" with `fs_char` at row 10 (lines 147-154, below every bonus text; column 15, 14 for two digits) before the palette goes on and outside the script, so each bonus text screen shows it for its whole length and the screens' lengths stay. Not a HUD message: the ticker shows one for about 1.5 s, and a queued message moves `msg_wr`, which quirk 1's D0 follows. 32 bytes in FRONT; the product holds no "TEST " bytes. Harness builds keep `TAG=0`; releases build without it |

- `PZ_TEST` code exists only in builds that ask for it (`if PZ_TEST`): the product's flow and bytes
  do not depend on it. AG is cleared by `ng_go`, so score 0, two lives and `$805E` 0: the bench's
  starting globals.
- The harness: `EXTJOY=1 PZ_TEST=1` (and `PZ_LEVEL=2` for `solve2`, `fuzz2`).
- Through `make`: `make rom ROMOPTS="PZ_TEST=1 TAG=2"` (it writes `build/msx/rc2.rom`). `make
  matrix` reports such a build as FAIL (it has no title): check it with `tools/msxmatrix.py
  --no-title` (4.4).

**The candidates** (step 8), four, all with `TAG=2`:

| File | Options | What it is |
|---|---|---|
| `ROBOCOP2_v0.1.3-test2.ROM` | `TAG=2` | the product, 1 MiB: the title, level 1, its statistics, Brainstorm (the intro, the stage, the result), then the title again |
| `ROBOCOP2_v0.1.3-test2-bonus.ROM` | `PZ_TEST=1 TAG=2` | 1 MiB: Brainstorm right after the BIOS, without the title or level 1 first; then the title and level 1 |
| `ROBOCOP2_v0.1.3-test2-2M.ROM` | `TAG=2 ROM_2M=1` | the product as a 2 MiB image: it starts as the complete game will, through the boot guard's 2 MiB check |
| `ROBOCOP2_v0.1.3-test2-bonus-2M.ROM` | `PZ_TEST=1 TAG=2 ROM_2M=1` | the bonus ROM as a 2 MiB image |

- Step 8 built them from `14bc5ef`'s sources with `tools/mkrom.py`, outside `build/msx/` (a
  rebuild at `cae5193` gives the same four images). The final checks rebuilt all four at
  `b59a338` (4.6 h): only bank 78 differs from step 8's (`rs_one`'s two `nop`s), and their notes
  say they replace step 8's. Each has a label file of the same name. Only the exact files sent to
  the user go to `build/msx/`.
- Banks 0-85 hold data in each (86 banks). The 1 MiB images have 128 banks; the 2 MiB twins have
  256, with the boot guard's tag in bank 255.
- Each file's SHA-256, what to test, how to reach each ending and the known limits are in the
  candidates' notes, delivered with them, not in the repository.
- Their checks (openMSX, headless):
  - `tools/msxmatrix.py`, 10 set-ups each: all PASS. The products ran in title mode, with the
    same lines as `14bc5ef`'s product; the bonus ROMs with `--no-title` (`tick_n` up by 349-351
    between 20 s and 27 s). A product with `--no-title` and a bonus ROM without it FAIL, as they
    should.
  - Fresh machines (power-on RAM). `test2` on a Gradiente Expert 2.0: the title, its music and
    level 1's start equal step 0's record (4.4); `test2-2M` the same, except the game's random
    word `$B32` (2 bytes: it is seeded from the Z80's R register every frame, and the guard's
    extra instructions shift R). `test2`'s whole flow on the Expert and on a Sony HB-F1XDJ
    (V9958): PASS (4.4's flow check).
  - The bonus ROMs (`test2-bonus` on both machines, `test2-bonus-2M` on the Expert), with five
    moves from the cursor keys: the cursor and the score as the bench gives for the same moves,
    then board 0's time out, OUT OF TIME. with TEST 2, the title and a new game. The text screens
    are pixel-exact; 56 stills each equal the render; 1,000 recorded VBLANKs each show 0 torn
    blocks, 0 changed pixels outside the elements and 0 cursor errors.
  - The acceptance suite of 4.1-4.4 ran again on `cae5193`'s harness builds (byte-identical to
    the review fixes'): the same results.
  - The rebuilt four (`b59a338`): the matrix and the fresh-machine runs again, with the same
    results, and `solve1` from the keyboard on the Expert (WELL DONE with TEST 2): 4.6 h.

**The sound's candidates** (milestone 2), with `TAG=3`: `ROBOCOP2_v0.1.3-test3.ROM`,
`-test3-bonus`, `-test3-2M` and `-test3-bonus-2M`, test2's four option sets, built at `74b9901`.
Banks 0-87 hold data (the sound in 86-87). Two optional 1 MiB bonus builds play the versions the
user's machines never pick, since they find the Pico+'s SCC: `-test3-bonus-noSCC` (`NO_SCC=1`: the
OPLL alone with MSX-MUSIC or an FM-PAC, else the PSG alone) and `-test3-bonus-PSG` (`NO_SCC=1
NO_FM=1`). Their checks are in 4.3 (the matrix and power-on machines for the four; the flows,
stills, records, chip modes and register logs for the two).

## 7. Defaults chosen while the user slept

| # | Question | Default | Alternative | Why | Status |
|---|---|---|---|---|---|
| 1 | Pass rate | 50 a second at 50 and 60 Hz | one per VBLANK (60 at 60 Hz) | decision 7's PAL design rule; the text screens already do it | built (`bs_wait`) |
| 2 | Turbo R | the stage on the Z80, `display_on` after `front_stats` | move `cpu_title` into `title` and run on the R800 | changes no working code; the OPLL needs the Z80 | built, with the PAUSE fix (section 10); the HUD's 0.1 s blank before the intro stays: below |
| 3 | The intro's 34-character line | split over rows 3-4, the later lines one row down | 4-pixel word spaces | `fs_char` stays as it is; the same 292 calls | built |
| 4 | Panel messages during the bonus texts | tick on (`hud_keep`) | frozen | the Amiga's VBL handler ticks them; `front_stats` stays without it | built |
| 5 | Colour grade on the stage | graded (game play) | plain | decision 8; the face looks a little pinker graded: both previews exist | built |
| 6 | Display | double buffer, TV pictures in page 2, put back at the exit | one page and a second line interrupt to time the TV copy | no change to the split; never tears | built |
| 7 | The end sequence's junk cursor | hidden | 3 sprites showing `$17FE8`'s bytes | zero-glitch rule; an inferred hardware artefact | built: hidden exactly while `$B12` = `$17FE8` (3.3) |
| 8 | TV face at ~25-30 pictures a second | the duty rule | the newest pass only | keeps the face's on/off share; equal to the original when pictures keep up | built; shares measured (3.3) |
| 9 | Graphics | raw, 7 banks | ZX0, ~3 banks | no decompressor to write; the ROM stays 1 MiB | built |
| 10 | Messages | in the HUD's data (`msxhudrt.py`) | RAM copies in C68Ah-C6FFh | the original's bytes, valid as long as the queue holds them | built: a second table, numbers 174-176 |
| 11 | Timer | `sec_tick`: real seconds; still in script builds | a pass counter | existing fixed code; the CIA-B is real time | built; ~61 s measured |
| 12 | Effect 6 | designed as the buzz | its converted data | the converted data is silent when restarted every pass | built (3.6); the user's ears decide |
| 13 | Effect 3 | kept, refused by the rule as on the Amiga | dropped | the logic ports the request; ~60 bytes | built: sent with every red chip, refused by `$1822C`'s rule while 4 plays (3.6) |
| 14 | Visit 2's palette reset | decided with the user (milestone 3) | reproduce or fix | the pointer is a variable: one line either way; invisible in visit 1 | reproduced for now (`pz_pal` back to `pz_pal1`); the user's call |
| 15 | Continue (`$805E`) | kept, unused until the game-over continue is ported | — | `new_game` clears it, as `$FFC4` does | built |
| 16 | The stage's code bank (found while building) | after the sound effects: `BANK_PUZL` = 78 | 10, after MUSIC (the plan) | at 10 every data bank moved and an SCC test value landed at bank 24h's 1800h | built (3.10) |

**Default 2 and the HUD blank [V: openMSX, FS-A1GT].** On a turbo R only, between the level
statistics and the Brainstorm intro, the whole screen (the HUD included) is black for about 0.1 s:
the last HUD split before the CPU switch at 37.827 s, `cpu_set`'s display-off 4.25 ms later,
`display_on` 6.6 ms after the split, the next split 116.9 ms (7.01 frames) after the last: 6
frames without the HUD. Every other machine keeps the HUD, as the Amiga does. The ways out, for the
user to choose:
- keep it (the default);
- run the bonus on the R800 (`cpu_title` moved from `front_stats`' end to `front_bonus`' end, a
  few bytes). The R800's split blanks one line earlier (the user's choice for the R800,
  `docs/TURBO_R.md` 4.1), which hides the stage screen's line 161 (the button panel's lower edge,
  44 non-zero bytes), and milestone 2 could not use the turbo R's OPLL from the R800 as the code
  stands (`opll_w` is too fast for the YM2413 there, and `muq_f` writes no OPLL on the R800);
- a new CPU switch that keeps the display on (the Z80's split measured earlier, while the screen is
  dark): a larger change to `cpu_set` and to the power-on and new-game path.

Inferences the defaults rest on: the Amiga shows x 16-319 (the layout does not depend on it); one
pass per frame on a real Amiga (no hardware timing seen); PZM's drum samples classified as toms
(PERCUSH1/2); the buzz's sound by ear.

## 8. Risks and open issues

| # | Item | Status |
|---|---|---|
| 1 | **The renderer** is new code: a build published before its last HMMM ended would show a torn block | retired: `bs_feed` publishes only with the VDP idle; 0 torn blocks in every record (4.2 check 3). The display guard still counts `bs_board`'s copies into the page on screen at a set-up, with the palette black: a stricter design would draw the shown page only after a flip |
| 2 | **Page 2.** A path that left the stage without `tiles_upload` would break the next level's tiles in script builds (no title) | retired: `bs_exit` is the only way out; the restore checked (4.2 check 5) |
| 3 | **Turbo R.** The Z80's split delays are measured only by `front_bonus`' `display_on`; a missing call would hang the first `fs_vbl` | retired: checked on the FS-A1GT in every flow |
| 4 | **Bank renumbering** | avoided: `STAGES` after the effects; no data bank moved or changed |
| 5 | **The fixed area** had 213 B | 23 taken (190 free; 160 in `PZ_TEST` builds); the sound took none (3.6) |
| 6 | **Sound** changes `music.asm`, which the title uses: the title must stay register-exact | `music.asm` unchanged: `tune.asm` is a player of its own after the title's code (3.6); the title's chip writes and executed instructions are main's in a Z80 interpreter, and in openMSX its registers equal main's on 11 chip sets at power-on and in 28 pairs after the stage (4.3). Open: an exit mid-tune is checked offline only |
| 7 | **Quirk 1 after level 1.** D0 comes from `msg_wr`, which counts the HUD's messages since the last `hud_init`; `$8056` on the Amiga may count differently across games | open: exact in `PZ_TEST` runs (the bench's start); after a played level 1 only that pass's move could differ. The final checks solved the 4th board there (4.6 e), but `solve1` changes no direction in that pass, so the case is still not exercised |
| 8 | **Visit 2** shows Murphy until step 13 (the boards and logic are already visit 2's) | open (milestone 3) |
| 9 | **SCC test bytes.** With 92 banks, bank 90 holds data; mkrom stops if its 1800h holds 5Ah | open (milestone 3) |
| 10 | **Headless runs**: at most 2 instances, no `exit` in callbacks, files opened once | kept in every run |
| 11 | **Quirk 1** was not observable in any drive | retired: `pz_quirk1` (4.1) |
| 12 | **The silent stage** and Murphy on visit 2 must be in the candidates' notes, or the user reports them as bugs | retired: the four candidates' notes say both (step 8), and also the turbo R's 0.1 s blank and its PAUSE rule |
| 13 | **The solved path on the MSX**: the WELL DONE screen and `$805E` + 1 | retired: seen in the final checks (4.6 a and e), from the power-on and after a played level 1, on the MSX2, the MSX2+ and the turbo R: WELL DONE equal to its render, AG `$805E` = 1 |
| 14 | **The turbo R's HUD blank** before the intro (0.1 s) | the user's call (section 7) |
| 15 | **PAUSE on a turbo R** after the result: a press left pending during the bonus holds the game (the HUD kept, the pause LED lit) until PAUSE is pressed again | by design: as at the end of `front_stats` and `front_over` |
| 16 | **Level 1 at 5.37 MHz** (the turbo of some MSX2+ and FPGA machines; the normal speed is 3.58 MHz): level 1 loses VRAM writes in openMSX, the ones logged in the sprite engine's 18 T OUTIs (`outi32`, `outi16`) | open, the user's call: 790 lost in 1,399 ticks of `drive_cov1` on the FS-A1FX, none at 3.58 MHz (4.6 g); real hardware not checked. A level-1 change, not made tonight. Brainstorm itself loses none since `b59a338` |
| 17 | **The harness's text-screen check** (`tools/bstest/bonuscheck.py`) reads R#1 once per record, so a record taken inside the HUD split's blank lines reads as a display off | open: one such FAIL in the final checks (4.6 e). Accept R#1 = 22h with R#2 = 7Fh and R#23 = 29h, or sample again a few ms later, as `tools/msxmatrix.py` does |

## 9. Sources

`$BS` = the night's scratch folder,
`/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space/brainstorm`
(not in the repository, and temporary):

| Report | Spec | What it holds |
|---|---|---|
| flow | `$BS/flow/FLOW.md` | `load_level1`, `$8382`, the text screens, the port's hook, `fe_text`, RAM and VRAM audits, free bytes |
| logic | `$BS/logic/LOGIC.md` | PUZL routine by routine, the state, the tables, the quirks, the executable model (17 scenarios, 0 differences), the names now in `analysis/puzl_17100.sym` |
| graphics | `$BS/gfx/GFX.md` | the screen read from the code, the 256 × 162 layout, the palette search, the VRAM map, the renderer, the converter prototype |
| sound | `$BS/sound/SOUND.md` | PZM = MU1's player, the calls, what is heard, the routing, sizes, the player plan, hazards H1-H12 |
| bench | `$BS/bench/BENCH.md` | `amigaemu.py puzl`, solutions, references, the Unicorn fixes, the Tcl procs, `puzlcmp.py` |
| implementation | `$BS/impl/HANDOFF.md` | each step's work, commands and measured results; the harness scripts of 4.2 and 4.4 (`impl/harness`, `impl/step7`, `impl/fix`; now in `tools/bstest/`: 4.5) and those of the final checks (`impl/final`: 4.6) |

All Amiga facts in section 2 come from REA (Ghidra provider) listings and byte reads in those
reports, on the level-1 RAM image with `PUZL_25.bin` at `$17100` (sha256 `9c76e13f…a9431a`:
`build/ram/puzl_full.bin`, `docs/AMIGA_ANALYSIS.md` "Brainstorm"), and from bench runs of the
original code; `$8382`, `$17100`, the PZM entries, `$17AEE` and `$17D04` were read again with REA
for this document. MSX facts cite the source at `14bc5ef`, which `b59a338` changed only in `rs_one`
(two `nop`s: 4.6 g); the sizes in 3.1 and 3.10 are `b59a338`'s.

## 10. Reviews

**The plan's review (2026-10-27, before the implementation).** Checked against the area reports,
the source at `52149b0` and REA: `$8382`, `$17100`, `$17760` and `$178E8`; the four text scripts;
the fixed area's free bytes; every file:line the plan cited; EXTJOY ⇒ `INPUT_SCRIPT` ⇒ `sec_tick`
and `title` return at once; `hud_init` clears `msg_wr`, so quirk 1's D0 is 0 in `PZ_TEST` runs, as
on the bench; `cpu_set` reinstalls the Z80's split block; `spr_upload` and `iv_sat` no longer
write VRAM; page 3 lines 0-87 hold the atlas. It made `pz_boards` a fixed label, `hud_keep` the
16-byte form, and added the renderer's engine rules, the interrupt rule for milestone 2, the whole
game against 2 MiB, the quirk and fuzz drives, `rc2_pz_arm`, the time-out check, the matrix's
title wait, the text renders and the `TAG` display. Its check of the SCC test banks after the
bank shift was wrong (3.10).

**During the implementation.**
- The lead added the `pz_opp` drive (4.1): no drive put opposite direction bits into `$802E` at
  the step.
- `tools/msxpuzl.py render --visit 2` draws milestone 3's Ellen, but a milestone-1 `PZ_LEVEL=2`
  ROM shows Murphy: check visit-2 snapshots with `--visit 1`.

**The implementation's review (after step 7), three findings:**
1. `make matrix OMHOME=...` broke on a home path with spaces (the MSX-AI MCP's): fixed in
   `14bc5ef` (the recipe quotes it); all 10 set-ups PASS with that home. The quotes also stopped
   the shell's tilde expansion: see the completeness review below.
2. **Turbo R: PAUSE during the Brainstorm screens** [V: openMSX, FS-A1GT]. CHGCPU(80h) had left the
   Z80's hardware pause on (A7h = 02h), and nothing wrote A7h during the bonus: a PAUSE press held
   the Z80, and with it the HUD split and the VBLANK list, at any line. For 9 emulated seconds the
   VDP kept the split's registers (R#2 7Fh, R#23 29h), so the whole screen showed page 3 from line
   41 in the HUD's palette. Fixed in `14bc5ef` (3.1 step 1 and step 8): A7h bit 1 off before
   `display_on`; PAUSE then has no effect during the bonus (the original stage has no pause, and
   `front_stats` on the R800 ignores the key too). After the fix: PAUSE at pass 324 for 5 s, the
   stage ran on (splits = VBLANKs); a press left pending at the end held the game with the HUD
   split running and the pause LED lit until PAUSE again, then the title; PAUSE during the title
   holds the CPU as before. FRONT grew by 15 bytes.
3. **Turbo R: the HUD blank between the statistics and the intro**: measured (6 frames) and left to
   the user (section 7, default 2).

**The completeness review (after `a050d0a`)** asked for these fixes, in the documentation and the
`Makefile` only:
- `make matrix OMHOME=~/...` typed in zsh gave the tool a literal `~/...`: zsh passes the `~` to
  make as typed, and the recipe's quotes stop the shell's tilde expansion. The `Makefile` now
  expands a leading `~/` with `$(HOME)` itself and passes a path without one as typed. Checked with
  `make -n matrix`: without `OMHOME`, with the MCP's home (spaces), with the same home typed as
  `~/...`, with `OMHOME=~/x` typed in zsh and in bash, and with a path holding a double space and a
  `~` inside. A stand-in `PYTHON` that prints its arguments receives one `--home` argument holding
  the whole path.
- `README.md`: the `--no-title` command next to `make matrix`, and `PZ_TEST`, `PZ_LEVEL` and `TAG`
  on the build options line.
- This file: the four candidates in step 8's row and section 6 (their hashes stay in their
  notes); the HUD check stated as measured (4.2 check 4, 3.8); the defaults to review, pointed at
  from the summary; where the harness lives (4.5).
