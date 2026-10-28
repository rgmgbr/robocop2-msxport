# The shooting range: the second bonus stage after level 1

The shooting range's design, as built on the branch `range` (2026-10-27/28, from main `4a8a61d`).
This file was written on 2026-10-27 as the plan for the phase. The implementation followed it step
by step (section 5); section 11 lists where the build departs from it, and the sizes and results
it measured. The plan's text is kept: what a section says is what was built, unless section 11
says otherwise.

The user's orders, relayed by the workflow that asked for this plan:
- **no new release until level 2 is whole and working**: Brainstorm is not published; commit the
  source and the docs only, with no official release;
- **the shooting range**: its reverse engineering, its port, and a test ROM left for the user, who
  cannot test it before the delivery. So **everything must be shown to work in openMSX first**;
- then level 2, whole.

The rules that bind the port (`docs/MSX_ARCHITECTURE.md` "Decisions", `CLAUDE.md`):
- SCREEN 5, and pixel-exact 1:1 art: only spacing or decoration may move;
- hardware sprites never flicker and never lose a piece; big objects are drawn by the VDP;
- the colour grade applies to game play, not to pictures;
- the digitised photos are dropped (decision 5): no PIC2 or PIC6;
- the original's logic, routine by routine, trace-identical to the bench;
- the PSG always, an SCC (in any slot) and MSX-MUSIC or an FM-PAC when present, the effects on the
  SCC when there is one;
- no dependence on one device; the MSX2 (V9938) is the baseline;
- level 1's mechanics, Brainstorm and the title do not change;
- the ROM stays within 2 MiB (256 banks).

Base: five area reports of the same day (flow, logic, gfx, sound, bench: section 9; scratch files,
not in the repository) on the repository at `4a8a61d` (main, clean). They disagree in a few places; section 10 lists each and how
this plan settles it.

Tags:
- **V**: verified, by REA (Ghidra provider) on the level-1 RAM image with FRNG decrunched at
  `$1EA00` (sha256 `9470791f…5f3d91a`), by a byte read, by a bench run of the original, by the
  logic report's executable model (equal to the bench), or by the MSX source at `4a8a61d`;
- **I**: inferred, not confirmed by a run;
- **D**: a design decision for the port;
- **E**: estimated.

## 1. Summary

- **What it is [V].** After Brainstorm, `load_level1` calls the shooting range `$8420` (D0 = 1).
  It shows an intro text and PIC2, then decrunches FRNG into `$1EA00` and calls it. The player moves
  a crosshair over a 320 × 172 street and has **25 shots** and **2:00** on the panel's timer.
  - Targets slide out of 9 windows (pop-ups), rise from the street (the riser) or walk out of a
    door (the walkers). Some are armed, some are dummies, and some pictures hold both.
  - An armed hit counts a correct target and pays 25 points. A dummy hit counts a dummy target.
  - The stage ends 130 passes after the last shot ("NO AMMO.") or at once when the time runs out
    ("TIME OUT.").
  - `$8420` then rates the counts: rating = max(0, min(3, (6 × correct − dummy − 50 − 12 ×
    [timer minutes = 0]) div 14)), POOR to SHARP. The rating selects **the next level's enemy
    hit-point table (`$8060`)**. A time out gives POOR and "OUT OF TIME.".
  - The target sequence comes from the pass counter: no random number is read. The second visit
    (after level 2) differs only by its palette.
- **The port [D].**
  - `front_bonus` (FRONT) calls a new `front_range` after Brainstorm's result, before
    `jp cpu_title`.
  - `front_range` ports `$8420` without PIC2. Its intro, result and time-out texts go through
    Brainstorm's text engine (`fe_text`). Its rating sets `ac_diff`, the port's `$8060`.
  - The stage `rg_stage` (`msx/frng.asm`) runs in its own code bank, **`BANK_FRNG` = 88**, at
    A000h. It is FRNG ported routine by routine, one pass per 50 Hz tick, its variables in the
    mirror (`AM + $B00-$BC5`), traced against the bench pass by pass.
  - **The screen.**
    - The street stays 320 pixels wide in VRAM, and a 256-pixel view follows the crosshair (a
      camera, as in level 1): every picture is 1:1 and nothing is cut.
    - Amiga rows 10-171 fill the play area; the HUD stays below.
    - Pages 0 and 1 are double-buffered display pages, built with VDP copies from a clean copy of
      the scene in page 2.
    - Only the crosshair's vertical line and the fire box's sides are hardware sprites: at most 30,
      3 to a line.
  - **The sound** is FRNG's own tune and its three effects, on the chips the machine has, through
    Brainstorm's player (`msx/tune.asm`) with two small additions.
  - **Level 1 does not change.** `obj_start` still sets SHARP at every level start, and today a new
    game follows the range. When level 2 is ported, that set moves to `ng_go`, so that level 2
    gets the rating.
- **ROM [D, E].** 1 code bank, 8 banks of raw graphics, 2 banks of hit masks for the logic, and 5
  banks of music: **104 of 128 banks**, still a 1 MiB image for the test ROMs. No Brainstorm bank
  moves. With the rest of the game's budget, the whole game comes to about **196 of the mandatory
  256 banks (201 high)**: section 3.12.
- **Verification [D]: all in openMSX**, because the user cannot test on hardware before the
  delivery:
  - the bench's `frng` mode against the MSX trace (15 drives, every rating and both endings, quirk
    T1 and visit 2);
  - the text screens, stills and per-VBLANK records against the converter's renders;
  - the HUD unshifted under the camera, on the V9938 and the V9958;
  - the sound per tick on every chip set;
  - level 1's regression, Brainstorm's checks and the title untouched;
  - the product from a fresh machine, and the generic set-ups of `tools/msxmatrix.py`
    (section 4).
- **The plan [D]**: 15 steps in order (section 5).
  - Steps 1-10: the range playable after Brainstorm with the original's logic and graphics.
  - Steps 11-12: its sound.
  - Steps 13-14: the test ROMs (`TAG=4`) and the documentation, with no release. As built, all
    15 steps ran on the branch `range`, which is merged into main after step 14 (section 11).
- **Test builds (section 6).** `PZ_TEST=2` starts in the range at power-on, once; `PZ_LEVEL` picks
  the visit. The product's flow does not depend on it.
- **Defaults (section 7)**: 38 choices made while the user is away, each with its alternative. The
  ones the user should look at first: the camera over the 320-pixel street (13), the crosshair line
  through the hit column (17), visit 2's dark palette (21), and the music at 50 ticks a second (25).

## 2. The original

### 2.1 The flow around the stage [V]

| Step | Address | What |
|---|---|---|
| 1 | `$8588` | statistics `$85D8`: ported, `front_stats` |
| 2 | `$858A` | Brainstorm `$8382`, D0 = 2: ported, `front_bonus` |
| 3 | `$8590` | **the range `$8420`, D0 = 1** (`moveq #1,D0` / `bsr.w`) |
| 4 | `$8596` | 3 `nop`s where a 6-byte call was. **I**: the disk-2 prompt, removed by the crack |
| 5 | `$859E`-`$85C4` | the level-2 briefing `$110F0`, PIC4, MU1, MADEX, DATAL2: later |

- `load_level2` `$8524` runs: the statistics, 3 `nop`s, `clr.b $857F`, Brainstorm (D0 = 4), then
  **the range (D0 = 5) at `$853C`**, the level-3 briefing `$110B4`, PIC7, MU1, DATAL3.
- `$8420` has no other caller (REA xrefs: `$8592`, `$853E`). It runs whatever Brainstorm's result.

`$8420` (REA listing `$8420-$851E`):

| Address | What |
|---|---|
| `$8422` | the intro `$1142D` through `$10762` (the text loop, then `$FE14`) |
| `$842E` | `show_picture` `$11E06`: PIC('1' + D0) = **PIC2 / PIC6**: dropped (decision 5). D0 only picks the picture |
| `$8436` | `$10320` = `$1032E`: the VBL's music call becomes an `rts` |
| `$8440`-`$8458` | the loader with "FRNG" (`$841B`) at `$1E980`; `$124A6` decrunches it into `$1EA00-$485D9` (170,970 bytes), on both visits |
| `$845E` | `clr.b $804C` |
| `$8464`, `$846C` | `$1FB34` = `$1880`, `$1FB38` = `$3FF0`: the **values** of the DIWSTRT and DIWSTOP moves in FRNG's copper list `$1FA9E`. The file holds `$0090` and `$3FF0`, so only DIWSTRT changes. Display only: ignored by the port |
| `$8474` | **`jsr $1EA00`** → D0 = `$B06` (dummy targets), D1 = `$B04` (correct targets) |
| `$847A`-`$848C` | `$804C` set: `$8060` = `$C72E` (POOR) and `$11698` ("OUT OF TIME." / "ATTEMPT TERMINATED.") through `$10762`; the counts are not shown |
| `$8498`-`$84BC` | the dummy count into the field `$113E4` and the correct count into `$113CA` (`$11DC6`: 8 characters, `[` + digit, leading zeros as spaces) |
| `$84C2`-`$84F0` | s = 6c − d − 50, − 12 more when `$804A` (the minutes) is 0, in 16-bit words; s < 0 → 0, else min(3, s `divs` 14) |
| `$84F6` | **`$8060` = `$C716` + 24 − 8 × rating** |
| `$8502`-`$8514` | the rating's 8-byte name from `$1140D` + 8 × rating into `$11400` |
| `$8518` | `$113A5` ("GUN CALIBRATION.") through `$10762` |

- The flow report ran the original `$8498-$8516` in Unicorn for correct 0-40, dummy 0-40 and
  minutes 0-2: 5,043 cases, 0 differences from the formula, in `$8060` and in the three fields.
- **Least correct counts**, with no dummy hit:

| Timer at FRNG's return | FAIR | GOOD | SHARP |
|---|---:|---:|---:|
| 1:00 or more | 11 | 13 | 16 |
| below 1:00 | 13 | 15 | 18 |

  SHARP needs 6c − d ≥ 92, GOOD 78, FAIR 64, and 12 more below a minute. Each dummy costs 1/6 of a
  correct target. The minutes are read at FRNG's return, 130 passes after the last shot.

The text screens (bytes from REA `read_bytes` `$113A5-$114AC`; `build/front/scripts.json` agrees):

| Script | Text (row: column) | Bytes | Calls | Frames without fire |
|---|---|---:|---:|---:|
| `$1142D` intro | 0: 11 "SHOOTING RANGE." / 3: 5 "YOU MUST SHOOT ARMED TARGETS" / 5: 1 "YOUR GUN CALIBRATION WILL BE TESTED" / 7: 4 "WARNING ACCURACY IS ESSENTIAL." / `FF 02 30` / `FF 07` | 125 | 304 | 305 |
| `$113A5` result | 0: 9 "GUN CALIBRATION." / 3: 5 "CORRECT TARGETS" + field `$113CA` / 5: 5 "DUMMY TARGETS" + 2 spaces + field `$113E4` / 7: 5 "YOU ARE RATED AS " + name `$11400` / `FF 02 40` / `FF 07` | 104 | 347 | 348 |
| `$11698` time out | 0: 12 "OUT OF TIME." / 2: 9 "ATTEMPT TERMINATED." / `FF 02 18` / `FF 07` (Brainstorm's result 2) | 42 | 129 | 130 |

- They use only positions, characters, `FF 02 n` and `FF 07`: what `fe_text` runs. With fire a
  screen ends at its first call from the 50th on.
- The panel stays below each text screen, and its messages tick on.
- Names at `$1140D`: "POORe   FAIRe   GOODe   SHARPe  " (8 bytes each; `e` is the font's '.').

**What the rest of the game reads afterwards [V]:**
- `$8060`, read only by `update_objects` (`$C3E4`) at `$C512` and `$C706`. Every enemy spawned
  takes its hit points (slot + `$21`) from that table, indexed by its class, so the rating counts in
  levels 2 and 3.
  - Writers of `$8060`: `$8314` (`load_level0`: SHARP at a new game), `$8482` and `$84FC`.
  - `restart_level0` `$8352` and `level_init` never write it.
- The score (+ 25 BCD per paid correct hit).

Weapon, ammo, timer and `$804C` are set again by the next `level_init`, and `$B00-$16EB` by the
next text screen's `$FE14`.

| Table | Rating | Hit points by class 0-7 |
|---|---|---|
| `$C716` | SHARP (and every new game) | 00 01 01 02 03 03 04 63 |
| `$C71E` | GOOD | 01 02 02 03 03 04 04 63 |
| `$C726` | FAIR | 02 03 03 03 04 04 04 63 |
| `$C72E` | POOR and every time out | 03 03 03 04 04 04 05 63 |

### 2.2 The rules [V: REA, bench, executable model]

- **The gun.**
  - `set_weapon(0)` runs, then `$8030` = `$0025`: 25 shots, 3-digit BCD. Each shot calls `$8010`
    (`$AC9A`: ammo − 1).
  - With fire held, one shot every 25 passes: `$1EB48` counts down from `$18`. Releasing fire, or
    running out of ammo, sets its high byte to FF, so the next press shoots at once (taps every 2
    passes).
- **The crosshair.**
  - X (`$B9A`) starts at 240 and moves 4 a pass within `$7C-$198`; Y (`$B9E`) starts at 72 and moves
    4 a pass within `$10-$9E`. Signed clamps.
  - Right beats left and down beats up: the opposite of Brainstorm's rule. No acceleration, no
    mouse.
  - The hit pixel is BOB x X + 17, row Y: bitplane x **X − 111**.
- **Targets: two slots** (`$B2E`, `$B32`).
  - An empty slot spawns script (`$B00` & `$3F`) + 1, less 32 from 40 on: 1-39. Scripts 1-7 and
    33-39 have weight 1 in 64, scripts 8-32 weight 2.
  - The random word `$B0C` is computed every pass and **never read**.
  - A refused script (its position or the big target's lock taken) costs two passes.
- **Kinds.**
  - **Pop-ups**: 27 scripts (1-13 and 26-39) through 23 stubs to 22 descriptors. A pop-up rises (or
    slides), holds and goes back, one at a time per position (9 positions, locks `$1F502`).
  - **The riser** (scripts 23-25): one big target rising at x `$82` + (`$B00` & `$FF`). Always
    armed.
  - **The walkers** (scripts 14-22): one big target sliding in from the right, 16 kinds by
    `$B00` & `$1E`.
  - One big target at a time (`$BA6`).
- **The hit test** (`$1EDBC`, section 2.3): a shot in pass n is tested by every draw of pass n + 1
  against the target's own mask. For pop-ups the mask is less the scenery's priority plane, so only
  pixels seen in the opening can be hit. The target's handler scores it in pass n + 2.
- **Armed or dummy**, by the hit column measured from the BOB's word-aligned left edge:
  - pop-ups: armed when the column < the threshold (`+$14`: 0 always dummy, 99 always armed, 24 the
    left part);
  - walkers: armed when the column ≤ the kind's threshold (0, 99 or 32);
  - the riser: always armed.
- **Scoring.**
  - Correct: `$B04` + 1 and `$BBC` = 10; 10 passes later, effect 3 and add_score(`$25`).
  - Dummy: `$B06` + 1 and `$BBE` = 10; 10 passes later, effect 4.
  - A hit starts a hit effect (a dissolve), unless one runs.
- **The ends.**
  - The 25th shot queues "NO AMMO." and starts `$B08`. At 99 the fade-out starts, and FRNG returns
    when it reaches 0: 130 passes after the last shot.
  - `$804C` (the CIA-B timer below 0:00) is tested only while `$B08` = 0 and ammo is left. Then FRNG
    queues "TIME OUT." through `jmp $8008`, whose `rts` returns to `$847A` **in that pass, without a
    fade-out**.
- **The timer**: `setup_ciab_timer($0200)`, 2:00. The CIA-B handler `$1015E` counts real seconds
  while `$804E` is clear and sets `$804C` below 0:00: the 121st second after the set-up.
- **Visits**: only `$8050` ≥ 2 changes anything: the palette (`$1FC2A` instead of `$1FBEA`).

### 2.3 Entry and the pass loop [V]

```
frng_main $1EA00:
    jsr $20000                         ; FRM, FRNG's own copy of the music player: init
    set_weapon(0) ($8014 -> $FD30)     ; $805C = 0, $8030 = weapon 0's ammo, the panel's icon
    word $8030 = $0025                 ; 25 shots
    frng_init_hw $1FB52:
        $FE14 (through $8028)          ; stop all, palette black, the game's vectors, clear_game_vars
        copy $3E062 -> $769B0          ; the clean street into the shown buffer (3,439 x 10 bytes:
                                       ;  10 short of 5 planes, display quirk 2)
        $B00-$BC4 = 0; $7F330 = $2B0 words of $0001 (sprite data)
        vector $6C = $1F9EA; COP1LC = $1FA9E
        $BC1 = 0; $BC0 = FF (fade in); $802C = 0
        $1F9B0 = $1FBEA; $8050 >= 2 (cmpi.w #2 / bmi): $1FC2A    ; the visit: the palette only
        setup_ciab_timer($0200)        ; 2:00, $804C = 0
    $804C = 0; $B9E = $48; $B9A = $F0  ; the crosshair at (240, 72)
    jsr $20010 with D0 = 1             ; tune 1, once
    st $BBE; st $BBC                   ; the delays idle ($FF00)
loop $1EA40: wait until VHPOSR's line byte = $C0     ; one pass a frame
pass $1EA4A:                                         ; <- the trace's sampling point
    COLOR00 = 0
    frng_fade $1F980; frng_big_erase $1F44A; frng_fx_erase $1F808; frng_random $1EF6A
    frng_targets $1F0DA (both slots, then frng_big_draw $1F3F6); frng_fx_draw $1F83A
    frng_crosshair $1EB5C              ; restore, recoil box, the shot (effect 2), the move
    $B00 += 1; $B02 += 3
    $1EB30 -= 1: 0 -> no tick; < 0 -> 4 and tick; > 0 -> tick      ; 4 passes of 5 (starts at 1)
    read_joystick $801C                ; $802E for the NEXT pass's crosshair
    panel_update_digits $8004; message_ticker $8020
    frng_sound_delays $1EB00           ; effects 3 and 4, the + 25
end checks $1EAA6:
    D0 = $B08
    if D0: $B08 += 1; if (signed)(D0 - 99) < 0: loop
           $BC0 = 0 (fade out); if $BC1: loop
           return D0 = $B06 (dummy), D1 = $B04 (correct)
    if word $8030 == 0: $B08 += 1; message_queue("NO AMMO."); loop
    if $804C == 0: loop
    $B08 += 1; jmp message_queue("TIME OUT.")       ; returns to $847A at once
```

- In pass n, `$B00` = n for everything before `$1EA6E`; the spawn reads it.
- The crosshair uses `$802E` as read in the previous pass. A shot in pass n is tested in pass n + 1
  and scored in pass n + 2.
- One pass per frame (the raster wait): 50 passes a second on PAL. **I**: that a pass always fits a
  frame; the bench counts 807-2,796 instructions and 552-8,928 blitter words a pass.

### 2.4 The routines [V]

Names: the logic report's `frng_1ea00.sym` (to become `analysis/frng_1ea00.sym`). Bytes from FRNG's
memory map.

| Address | Name | Role | 68000 bytes | Port (`msx/frng.asm`) |
|---|---|---|---:|---|
| `$1EA00` | `frng_main` | entry, pass loop, end checks | 256 | `rg_stage`, `rg_loop`, `fr_frame`, `rg_end` |
| `$1EB00` | `frng_sound_delays` | `$BBC`: effect 3 and + 25; `$BBE`: effect 4 | 48 | `rg_delays` |
| `$1EB5C` | `frng_crosshair` | restore, recoil box, shot, move, clamp, the row | 506 | `rg_cross` (+ the wanted crosshair and box) |
| `$1ED5A` | `frng_hline` | a line of `$FFFF` words in 5 planes (display), rows 0-`$9D` only | 64 | the renderer (the box's edges) |
| `$1EDBC` | `frng_draw_bob` | right clip, blit 1 into `$7FC50`, the hit test, blit 2 | 430 | `rg_bob`: the clip, the bounds and the hit test (3.4); the drawing is the renderer's |
| `$1EF6A` | `frng_random` | `$B0C`: never read | 30 | none |
| `$1F0DA` | `frng_targets` | the slots, the spawn, the handlers, then `frng_big_draw` | 116 | `rg_targets` |
| `$1F14E` | `frng_h_rise` | scripts 23-25 | 164 | `rg_rise` |
| `$1F32A` | `frng_h_move` | scripts 14-22 | 204 | `rg_move` |
| `$1F3F6`, `$1F44A` | `frng_big_draw`, `frng_big_erase` | the big target drawn after the slots, erased at the next pass's start | 118 | `rg_bigdraw`, `rg_bigerase` |
| `$1F46E` | `frng_h_reject` | `moveq #-1,D0; rts` | 4 | — |
| `$1F472-$1F501` | 23 stubs | `lea descriptor,A0; bra $1F50C` | 144 | a table: script → descriptor |
| `$1F50C` | `frng_h_popup` | lock, rise, hold, lower, the hit, the erase | 258 | `rg_popup` |
| `$1F808`, `$1F83A` | `frng_fx_erase`, `frng_fx_draw` | the hit effect | 162 | `rg_fxerase`, `rg_fxdraw` |
| `$1F940` | `frng_fx_start` | one effect at a time | 52 | `rg_fxstart` |
| `$1F980` | `frng_fade` | `$BC1` ± 1; COLOR01-31 limited; the palette pointer reset | 108 | `rg_fade` |
| `$1F9EA` | `frng_irq_copper` | bitplanes; sprite pairs 0-3 (display) | 162 | the renderer's SAT |
| `$1FB52` | `frng_init_hw` | the set-up | 150 | `rg_stage`'s entry |

FRNG's calls into the main code (`$8004-$8028` table) and their port:

| Entry | Routine | Port |
|---|---|---|
| `$8004`, `$8020` | `$F6B8` panel digits, `$FDA2` message ticker | `hud_keep` (fixed) each pass |
| `$8008` | `$FD76` message_queue | `game_msg` (177 "NO AMMO.", 178 "TIME OUT.") |
| `$800C` | `$F6A0` add_score | `add_score`, DE = `$0025` |
| `$8010` | `$AC9A` ammo − 1 | `rg_ammo`: a copy of LC1's 12-byte `ammo_dec` |
| `$8014` | `$FD30` set_weapon | LC1's `set_weapon`, with LC1 mapped at 8000h for the call |
| `$8018` | `$F9DC` setup_ciab_timer | `rg_timer` (AG `$804A` = `$0200`, `$804C` = 0, `sec_n` = 0, the stage's last-tick base) |
| `$801C` | `$BDEC` read_joystick | `joy_read` (fixed) |
| `$8028` | `$FE14` | `rg_stage`'s entry |

### 2.5 State [V]

`$B00-$BC5` (cleared by `$FE14` and again by `frng_init_hw`; the port's mirror D000h-D0C5h):

| Address | Size | Name | Meaning |
|---|---|---|---|
| `$B00` | w | pass | passes so far (+ 1 after the crosshair) |
| `$B02` | w | pass3 | + 3 a pass; nothing reads it |
| `$B04` / `$B06` | w | correct / dummy | the counts (D1 / D0 at the return) |
| `$B08` | w | end_count | 0 in play; 1 at "NO AMMO." (+ 1 a pass) or at a time out |
| `$B0B` | b | hit | `frng_draw_bob`'s test, per call |
| `$B0C` | w | random | never read |
| `$B0E`/`$B12` | w | slot leftovers | D1's leftover at a spawn; never read |
| `$B10`/`$B14` | w | slot offset | a pop-up's rise or slide offset |
| `$B26`/`$B2A` | w | slot x | a big target's x; D0's leftover until the first call |
| `$B28`/`$B2C` | w | slot hold | the riser's hold count |
| `$B2E`/`$B32` | l | slot state | pop-up: byte 0 countdown, byte 3 first-call flag; big: byte 0 flag, word 2 counter |
| `$B36`/`$B3A` | b | slot script | 1-39, 0 empty |
| `$B3E`, `$B46`, `$B4E` | b | fx_step, fx_frame, fx_end | the hit effect |
| `$B56`, `$B66` | w | fx_x, fx_y | (y = the start's D1 − 8) |
| `$B9A`, `$B9E` | w | cross_x, cross_y | the crosshair |
| `$BA2`, `$BA4` | w | hit_x, hit_row | the test's column (or high byte FF: outside) and row, per call |
| `$BA6` | b | big_busy | FF while a big target is out |
| `$BA8`, `$BAA`, `$BAE`, `$BB0` | w, l, w, w | big size, graphic, x, y | the big target to draw this pass |
| `$BB2`, `$BB5` | b | big_hit, its column | `frng_big_draw`'s test, seen by the handler a pass later |
| `$BB6` | b | fx_delay | − 1 every pass, even with no effect |
| `$BB8` | l | script_entry | the running slot's entry `$1EF88` + 8 n |
| `$BBC`, `$BBE` | w | correct_delay, dummy_delay | 10 at a hit; `$FF00` idle |
| `$BC0`, `$BC1` | b | fade_in, fade_level | FF in, 0 out; 0-`$1F` |

Globals: `$802E` joystick byte (up 1, down 2, left 4, right 8, fire `$10`; the keyboard byte
`$802D` when 0), `$8030` ammo (BCD), `$8046-$8049` score, `$804A`/`$804B` timer, `$804C` time out,
`$804E` pause (never set by FRNG), `$8050` levels done, `$805C` weapon.

**State inside FRNG's code, loaded from the file at every visit** (FRNG is decrunched again each
time):

| Address | Meaning | In the file |
|---|---|---|
| `$1EB30` | music divider | `$0001` |
| `$1EB46` | shot flag (set for the next pass's draws) | 0 |
| `$1EB48` | fire repeat counter | `$FF18` |
| `$1EB4A` | recoil box n (8 → 0), −1 idle | `$FFFF` |
| `$1EE42` | `frng_draw_bob`'s right clip (an immediate): `$1F4`, `$258` for pop-ups, `$1F46C`'s for big targets | `$01F4` |
| `$1EE76` | its C source (an immediate): `$3E062` or the screen | `$0003E062` |
| `$1EEC6` | its first blit's mode (an immediate): `$9F0` mask, `$B50` mask & ~priority, `$100` erase | `$09F0` |
| `$1F246` | the walker's kind × 2 | `$0014` |
| `$1F46C` | the big target's clip | `$01C0` |
| `$1F502` | 10 position locks | `00 00 00 00 00 00 FF 00 00 00` (position 6 locked: quirk T2) |
| `$1F60E` + 22k | 23 descriptors; their run-time bytes `+1` phase, `+$12` hit, `+$13` hit column | stale values, set before use |
| `$1F9B0` | the fade's palette (an immediate) | set by the init |

### 2.6 Tables [V: REA read of `$1EA00-$1FFFF`, equal to the image]

- **Scripts** `$1EF88`: 42 entries of 8 bytes (`$1EF88-$1F0D7`): the handler (entry + word 0), an
  unused offset to the `rts` at `$1F0D8`, the hit effect's type 1-4, and 0. Entry 0 is empty;
  entries 40 and 41 are never spawned.
- **Descriptors** `$1F60E-$1F807`, 23 × 22 bytes:
  - `+0` position, `+1` phase (FF rise, 1 hold, 2 lower);
  - `+2` coordinate A, `+4` coordinate B's base, `+7` rise/lower passes, `+8` signed speed, `+$A`
    hold passes, `+$B` horizontal flag;
  - `+$C` BLTSIZE, `+$E` graphic;
  - `+$12` hit, `+$13` hit column, `+$14` threshold.

  `$1F666` has no stub. A pop-up lives 2 × duration + hold calls; the last one erases it.
- **The riser**: frames 0-9 every 2 calls, frame 4 for 54 calls: 72 drawn calls. Graphics
  `$1F1C2`, sizes `$1F1EA` (64 wide; 16, 32, 48, 70 and 88 rows), rows `$1F200` (bottom row 171).
- **The walkers**: tables `$1F248-$1F2EA` by kind k = (`$B00` & `$1E`) / 2 at the first call:
  - row, clip (`$1A0` or `$1C0`), threshold (`$1F288`: 0 0 99 0 32 0 0 0 99 99 0 32 0 99 99 99),
    x offset (0 or 34), size, graphic;
  - x from `$198` (+ offset): 63 passes left (1 px a pass), 64 back, so 127 drawn calls.
- **Effects** (`$1F8AA` sizes, `$1F8E8` graphics, `$1F974`/`$1F979` first and end frames):

| Type | Used by | Frames | Size |
|---|---|---|---|
| 1 | walkers | 0-3 | 32 × 64 |
| 2 | pop-ups | 4-7 | 32 × 40 |
| 3 | pop-ups | 8-11 | 32 × 32 |
| 4 | the riser | 16-21 | 64 × 88 |

  The first frame shows 3 passes, the next 4 each.
- **Palettes** COLOR01-31 (COLOR00 = 0):
  - visit 1 `$1FBEA`: 777 666 555 444 333 222 111 654 543 432 321 601 501 400 300 211 40A 309 208
    107 105 200 310 000 120 741 631 520 410 111 3F3;
  - visit 2 `$1FC2A`: 555 444 333 222 111 000 000 431 321 322 210 401 301 200 100 211 105 107 208
    309 40A 100 100 000 120 641 522 420 400 000 3F3.
- **Messages**: `$1EB32` "NO AMMOe" FF, `$1EB3B` "TIME OUTe" FF. The second is not the game's
  "TIMEOUTe" (`$865A`, HUD message 6).

The full script list (weights, descriptors, motions, sizes, thresholds) is in the logic report's
section 8.1. The descriptors and big tables are decoded in its `tables/`.

### 2.7 Timelines [V: bench traces]

| Event | When |
|---|---|
| Fade-in | `$BC1` 1 at pass 1's start … 31 at pass 31's |
| First targets | pass 0: both slots spawn script 1. Pass 1: slot 0 draws it, slot 1 is refused (position 8 taken). Pass 2: slot 1 spawns script 3 |
| A shot | fired in pass n (effect 2, ammo − 1); tested by the draws of n + 1; scored in n + 2; + 25 and effect 3 (or effect 4) at the end of n + 12 |
| A big target | the riser: 72 draws; a walker: 127 draws; then the slot spawns again the next pass |
| The last shot, in pass s | "NO AMMO." at the end of s; `$BC0` = 0 at the end of s + 99; FRNG returns at the end of s + 130 (2.6 s at 50 passes a second) |
| Time out | the 121st CIA-B second; the pass that sees `$804C` queues "TIME OUT." and returns |
| A scripted hit (bench) | `--joy 0:11:dr --joy 11:18:r --joy 32:1:f`: type 1 hit, tested in frame 34, counted in 35, + 25 in 45 |

### 2.8 The screen [V unless marked]

- **The picture.**
  - 320 × 172 in 5 planes at `$769B0`, one buffer, restored from the clean copy at `$3E062` (5
    planes of `$1AE0`).
  - A 6th plane at `$466C2` (6,880 bytes) marks the scenery in front of the pop-ups: 48,077 of
    55,040 pixels set.
  - FRNG's copper list ends with `COPJMP2` to the game's `$10356`, so **the status panel shows
    below the stage**.
  - Sprites run from line `$22` to `$C9` (rows 0-167).
  - **I**: all 320 columns are seen.
- **Drawing** (`$1EDBC`). A picture is a mask plane, then 5 planes, each (w − 1) words × h.
  - Blit 1 writes the shifted mask into `$7FC50`: mode `$B50` (mask & ~priority) for pop-ups, `$9F0`
    for big targets and effects, `$100` (zeros) for erases.
  - Blit 2 cookie-cuts the picture over the clean copy, or over the screen for the big target and
    the effect.
- **The elements** (bitplane coordinates):

| Element | Where | Rule |
|---|---|---|
| Pop-ups | 9 openings; each position's rectangle holds every pixel its pop-ups can show: 0 (4,29,25×28), 1 (58,24,29×34), 2 (56,99,31×33), 3 (126,99,27×29), 4 (194,47,20×46), 5 (236,44,19×51), 6 (274,46,22×21), 7 (194,104,20×29), 8 (234,100,20×23) | 8 pictures (16 or 32 wide, 30 or 40 tall); masked by the 6th plane |
| The riser | x 2-257, bottom at row 171 | 5 pictures, 64 wide, 16-88 tall; drawn over everything |
| Walkers | lane 1: x 217-280, rows 87-104, clipped at 288; lane 2: x 251-314, rows 105-122, clipped at 320 | 6 pictures; drawn over everything |
| Dissolves | (x, y − 8) of the target hit (the riser's at (x, 84)) | 4 types (32 × 64, 32 × 40, 32 × 32, 64 × 88) |
| Crosshair, horizontal | row `$B9E`, all 320 px, colour 31 (`$3F3`, green) | the old row restored first |
| Crosshair, vertical | attached sprite pair 0, data `$0001`: a 1-px column at H = `$B9A` + 15, rows 0-167 | **I**: its bitplane x (section 3.3) |
| Fire box | 32n × 32n, n = 8 → 0 over 9 passes, centred on c = (`$B9A` + 4) & ~15 at the position before the pass's move | sides: sprites 2+3 and 4+5 (attached pairs 1 and 2, H = c ± 16n); top and bottom: bitmap lines, restored the next pass |

- **Palette fade**: one step a pass, each component limited to (`$BC1` >> 1) & `$1E`. At the end of
  a fade-out the pointer goes back to visit 1's palette (invisible: FRNG returns in that pass).
- **Display quirks**:
  1. Restoring the old crosshair row wipes that row from targets drawn the same pass (a 1-row gap
     for one frame).
  2. The set-up copies 10 bytes short: row 171, x 240-319, plane 4 shows stale RAM.
  3. A hit big target is drawn once more under its dissolve in its scoring pass.
  4. A pop-up wipes columns of another position's pop-up drawn earlier in the same pass [V: REA,
     found by the converter's model at step 3]. Blit 2 (`$1EF1C`: BLTCON0 `$FCA`, D = A·B + ¬A·C
     over the whole BLTSIZE) writes its **whole word-aligned box** from the clean copy, so where
     that box meets another position's rectangle, the earlier pop-up's pixels there go back to the
     scenery for that frame. Seven descriptors do it: `$1F6A8` and `$1F6D4` steps 0-5 over position
     3 (x 126-127), `$1F6EA` steps 0-4 over 1 (x 58-63), `$1F716` and `$1F72C` every step over 5
     (x 236-239), `$1F7C6` step 0 over 5 (x 240-254; position 6, locked, never shows it), `$1F7F2`
     step 0 over 3 (x 144-152). The port keeps the pop-up whole (zero-glitch rule, as quirk 1).
- **Unused [I]**: `$1FC6A-$1FFFF` (an earlier build's code, a copper list, "MUSRNG", "RNGBAK") and
  `$481A2-$485D9` (FFh): nothing references them.

### 2.9 The sound [V: REA, model]

- **The player.** FRNG carries its own copy of the music player at `$20000` (FRM). Its 448
  REA-listed instructions equal MU1's at `$18000` but for 6 per-file operands. Entries: `$20180`
  init, `$20194` stop all, `$2024E` music, `$2022C` effect, `$20316` tick. `rc2music.py --verify`
  on the extracted copy: 12,600 ticks, 0 differences.
- **What plays.**
  - **Tune 1** starts once (`$1EA32`), before the first pass. It is channels 0-2, 5,999 ticks, no
    loop: 119.98 s at 50 ticks a second, the stage's 2:00.
  - Nothing in FRNG stops it. The result text's `$FE14` does (PZM's resident stop all writes
    AUDxVOL = 0 for all four channels). On a time out the music stops at the OUT OF TIME. screen.
    Either way the stop comes within microseconds of FRNG's return (`$8474` returns to the rating,
    `$847A-$8518`, which has no wait; then `$10762`, whose `$10768` begins with `$FE14`), and FRM
    ticks only from the pass loop: the last tick heard is the last pass's.
- **The tick**: on 4 passes of 5 (`$1EB30` starts at 1: the first pass has no tick). 40 ticks a
  second on PAL, 48 on the NTSC machines the dumped release targets. **I**: the composer's tempo
  is 50 a second, which makes the tune last exactly the stage's 2:00.
- **Effects**, all on channel 3, so they never cut the music:

| Effect | When | Heard |
|---|---|---|
| 2 | a shot (`$1ECB4`, before the pass's tick) | a 6-tick noise burst, as loud as the music's loudest (+1.4 dB) |
| 3 | a correct hit, 10 passes later, with the + 25 (`$1EB0E`, after the tick) | a 16-tick rising sine "ding", −9.5 dB |
| 4 | a dummy hit, 10 passes later (`$1EB2A`) | a 12-tick falling sine "dud", −9.5 dB |
| 5 | never requested | — |

- **`$1822C`'s rule** (`$2022C` is identical): a request lower than the last effect started is
  refused while channel 3 is busy. So a shot is silent while a hit sound plays, 3 is refused during
  4, and 4 cuts 3.
- The text screens and PIC2 are silent. The visit does not change the sound.

### 2.10 The second visit [V]

- `load_level2` calls `$8420` with D0 = 5 (PIC6, dropped); `$8050` = 2.
- FRNG is decrunched again: every static variable, the locks included, starts from the file.
- FRNG reads `$8050` only at `$1FBBE`: the palette `$1FC2A`. The bench's `armed` drive at visit 2
  equals visit 1's in every traced field of every frame but `$8051` and the palette pointer.

### 2.11 Quirks a faithful port keeps [V]

| # | Quirk | Seen on the bench |
|---|---|---|
| T1 | The hit test accepts one row below a BOB (row offset = h). It then reads bytes past this blit's output, left there by earlier blits. With a clipped BOB, the unclipped x bound can also read into the next row's bytes | 28 such reads in 8 traces, all on clear bits |
| T2 | Position 6 is locked in the file and nothing clears it: scripts 5 and 27 are always refused | every trace |
| T3 | A split target's armed border is measured from x & `$FFF0`, so it jumps with x & 15 while a pop-up slides. Pop-ups use `<`, walkers `≤` | the bots' left and right hits |
| T4 | A second armed hit scored within 10 passes of another restarts `$BBC`: one + 25 is lost | by code |
| T5 | A time out during the NO AMMO end sequence still gives OUT OF TIME. and POOR | `bot_late_timeout` |
| T6 | The time out returns at once without a fade-out; "TIME OUT." stays queued | `idle_timeout` |
| T7 | `$BB6` counts down every pass; `$B0C` changes every pass; spawns leave register leftovers | every trace |
| T8 | Y's lattice shifts when the clamp to row 158 lands off it (154, 150 … follow) | `bot_edge`, `fuzz1` |
| T9 | Both slots spawn script 1 in pass 0 | every trace |
| T10 | A hit big target is drawn once more in its scoring pass. A hit on a pop-up in the pass it is lowered away is never scored | by code |

## 3. The MSX design

### 3.1 Modules, banks, entry and exit [D]

| Piece | Where | Bytes [E] | Content |
|---|---|---:|---|
| `ml_ev` | fixed area (`rc2.asm`) | 0 | unchanged: FE_NEXT runs `front_stats`, then `front_bonus` |
| `fr_done`, `fr_rated` | fixed area (`rc2.asm`) | 2 | two `ret`s: the trace harness's breakpoints |
| `pz_test`'s `PZ_TEST=2` branch | fixed area, test builds only | ~6 | section 6 |
| `fb_prep`, `front_range` | FRONT (`front.asm`) | ~170 | the turbo R's set-up factored out of `front_bonus`; the port of `$8420` |
| `front_rgtest` | FRONT, `PZ_TEST=2` builds only | 9 | `fb_prep`, `front_range`, `jp cpu_title` |
| `txt_rg_intro`, `txt_rg_res`, `txt_rg_rate` | FRONT (`text.inc`, `tools/msxtext.py`) | 263 | the scripts (3.8) |
| `rg_stage`: the logic, the renderer, the tables, the graded palettes, `snd_rfx` | **`BANK_FRNG` = 88 at A000h** (`msx/frng.asm`) | ≤ 7,500 | FRNG and its display |
| graphics | banks 89-96 (`RANGE_GFX_BANK`) | 63,616 | `range_gfx.bin`: the scene and the sheets (3.11) |
| hit data | banks 97-98 (`RANGE_HIT_BANK`) | 11,776 | `range_hit.bin`: the priority plane, then the masks the hit test reads (3.4) |
| the sound's player additions | `BANK_MUSIC` (`tune.asm`, `tune.inc`) | ~123 | `tn_frm`, the PSG-B effect path, the second descriptor (3.7) |
| music and effects | banks 99-103 (`FRM_BANK`) | 39,341 | `frm.bin` (`tools/msxtune.py`) |
| messages | `HUD_BANK` + 1 (`tools/msxhudrt.py`) | 23 | "NO AMMO." 177, "TIME OUT." 178 |

Free before the range [V: the flow report's scratch build of `4a8a61d`]:

| Area | Free |
|---|---:|
| fixed area | 190 B (160 in `PZ_TEST` builds) |
| FRONT | 2,733 B |
| LC1 | 39 B (no new code goes there) |
| `BANK_PUZL` | 4,590 B (too small for the range) |
| `BANK_MUSIC` | 1,480 B, all past B800h |
| `HUD_BANK` + 1 | 447 B |

**`front_bonus`** (FRONT, `front.asm:373`) changes in two places: the turbo R block and
`g_tick` = 0 move into `fb_prep` (the same code, called), and `call front_range` comes between
Brainstorm's result and `jp cpu_title`:

```z80
front_bonus:
        call fb_prep                ; (a turbo R: the Z80's hardware pause off, display_on; g_tick = 0)
        ld hl,txt_bs_intro
        call fe_text                ; ($8384) ... Brainstorm unchanged, up to its result:
        ...
        call fe_text                ; ($8400: Brainstorm's result)
        call front_range            ; ($8590: moveq #1,D0 / bsr $8420; visit 2: the same code)
        jp cpu_title                ; (a turbo R: the hardware pause on again, the display off)
```

Brainstorm's calls keep their order and behaviour. After level 2 is ported, `ml_ev`'s `call
title` / `jp new_game` become the level-2 briefing and level 2's start; the same `front_bonus`
then runs visit 2 (both stages read AG `$8050`).

**`front_range`** (FRONT): the flow report's sketch. It assembles with z80asm (148 B before the
two `call fr_rated`). Its rating, transliterated instruction by instruction, equals the bench's
model in all 5,043 cases:

```z80
front_range:
        ld hl,txt_rg_intro
        call fe_text                ; ($8422: $1142D through $10762)
        ld a,BANK_FRNG
        call bank_a000
        xor a
        ld (AG + (0x804C ^ 1)),a    ; ($845E: clr.b $804C)
        call rg_stage               ; ($8474: jsr $1EA00; the counts stay in AM $B04, $B06)
        ld a,(AG + (0x804C ^ 1))
        or a
        jr z,frg_rate               ; ($847A)
        ld hl,diff_tab + 24
        ld (ac_diff),hl             ; ($8482: $8060 = $C72E, POOR)
        call fr_rated
        ld hl,txt_bs_time
        jp fe_text                  ; ($848C: $11698, Brainstorm's own copy)
frg_rate:
        ld hl,txt_rg_res
        ld de,fs_buf
        ld bc,TXT_RG_LEN
        ldir
        ld hl,(AM + 0x0B06)         ; ($849C: the dummy count into $113E4)
        ld de,fs_buf + TXT_RG_F2
        call fs_num
        ld hl,(AM + 0x0B04)         ; ($84AE: the correct count into $113CA)
        ld de,fs_buf + TXT_RG_F1
        call fs_num
        ld hl,(AM + 0x0B04)         ; ($84C0-$84DC: 6 correct - dummy - 50, in 16 bits)
        ld d,h
        ld e,l
        add hl,hl
        add hl,de
        add hl,hl
        ld de,(AM + 0x0B06)
        or a
        sbc hl,de
        ld de,50
        or a
        sbc hl,de
        ld a,(AG + (0x804A ^ 1))    ; ($84CE: tst.b $804A, the timer's minutes)
        or a
        jr nz,frg_s
        ld de,12
        sbc hl,de                   ; (carry clear: or a)
frg_s:  xor a                       ; ($84DE: below 0 -> 0, else (s div 14) up to 3)
        bit 7,h
        jr nz,frg_r
        ld de,14
frg_d:  or a
        sbc hl,de
        jr c,frg_r
        inc a
        cp 3
        jr nz,frg_d
frg_r:  add a,a
        add a,a
        add a,a                     ; ($84F0: lsl.w #3)
        ld c,a
        ld b,0
        ld hl,diff_tab + 24
        or a
        sbc hl,bc
        ld (ac_diff),hl             ; ($84FC: $8060 = $C716 + 24 - 8 x rating)
        call fr_rated
        ld hl,txt_rg_rate
        add hl,bc
        ld de,fs_buf + TXT_RG_F3
        ld bc,8
        ldir                        ; ($8502: the rating's name into $11400)
        ld hl,fs_buf
        jp fe_text                  ; ($8518: $113A5 through $10762)
```

- The counts come from the mirror, where the stage leaves them, as `$1EAC4` reads them: no
  register convention.
- `diff_tab` is LC1's label. FRONT only computes the address; it never reads LC1.
- `fs_buf` (CF40h) has 120 bytes before `fs_ptr`. A build check keeps `TXT_RG_LEN` (104) within it.
- No `snd_stop` in `front_range`: the stage stops its sound itself at its end (`rg_end`, below),
  and `fe_text` stops it again. (The plan had only `fe_text`'s stop; section 11.)

**`rg_stage`'s rules** (Brainstorm's `bs_stage` rules):
- FRONT is at 8000h and `BANK_FRNG` at A000h while it runs. It calls fixed code and FRONT.
- It maps data banks only at 8000h, through `bank_8000`, and puts `BANK_FRONT` back. These are the
  entry's uploads, the hit test's reads (3.4) and the call of LC1's `set_weapon`.
- `hud_frame` only through `hud_keep`.

**`rg_stage`, in order** (`$1EA00-$1EA3C`, `$1FB52`):
1. `snd_stop` (FRM's init; `$FE14`'s stop all); `pf_pal` black.
2. `set_weapon(0)`: LC1 at 8000h, `call set_weapon`, `BANK_FRONT` back. It posts `JOB_ICON`
   through the fixed `hud_request`. Then AG `$8030` = `$0025`.
3. `AM_START..AM_END` cleared; AG `$802D`, `$802E`, `$804D` cleared (`clear_game_vars`); `g_keys`,
   `g_joy`, `g_lock` cleared; AG `$804E` = 0 (FRNG relies on Brainstorm's clear: the same result).
4. `fr_code` loaded from the ROM (3.2): the file's locks (position 6 locked), descriptors and gun
   variables. The code-state variables take the file's values: clip `$1F4`, mode `$9F0`, the
   walker kind `$14`, the big clip `$1C0`.
5. The visit by AG `$8050` (`cmpi.w #2` / `bmi`): the graded palette `rg_pal1` or `rg_pal2`.
6. `rg_show`: VRAM and the renderer's state (3.3, "Entry").
7. `rg_timer($0200)`; AG `$804C` = 0; `$B9E` = `$48`, `$B9A` = `$F0`; `$BC1` = 0, `$BC0` = FF;
   `$BBE` = `$BBC` = `$FF00`.
8. The tune (step 11: `ld hl,tn_frm` / `call mus_call`).
9. The pass loop (3.5) until the end checks return.

**Exit** (`rg_end`: `snd_stop`, `rg_hide`, then `jp fr_done`):
- the sound stopped first, before any wait: `rg_hide`'s waits and its page-2 restore take about
  0.25 s, and the VBLANK would tick the tune meanwhile (about 13 ticks over the black screen);
  `$10768`'s `$FE14` stops it right after the last pass;
- the VDP idle;
- on the time-out path, `pf_pal` black first, then a last list with R#18 = 0, so that no shifted
  picture is ever seen in colour (the NO AMMO path is black already);
- that list on screen, then the V9958 split byte back (3.3);
- Y = 216 at entry 0 of both SATs;
- page 2 back (`tiles_upload` E = 4).

The counts stay in AM `$B04`/`$B06` and the time out in AG `$804C`. Nothing after `fr_done` changes
them before `front_range` reads them.

### 3.2 RAM [D]

| Range | Use during the stage | Why it is free |
|---|---|---|
| `AM + $B00-$BC5` (D000h-D0C5h) | FRNG's variables (`frv_...`), in the mirror's layout (words little-endian, a byte at A ^ 1, a long's high word first) | cleared at the entry as `$FE14` does; `pl_init` clears it again at a new game |
| AG (DC00h-DCFFh) | `$802D`, `$802E`, `$804D`, `$804E` cleared; ammo, weapon, score, timer, `$804C`; `$8050` read | the game's globals |
| F500h-F70Dh (`MP_B`) | **`fr_code`**: FRNG's code-area state as the bench traces it, 526 bytes in the mirror rule: `$1EB46-$1EB4B`, `$1F246-$1F247`, `$1F46C-$1F46D`, `$1F502-$1F50B`, `$1F60E-$1F807`, one after another. Copied from `BANK_FRNG` at every entry | `tiles_init` rebuilds `MP_B` at the next level; Brainstorm's `pz_boards` uses the same bytes, never at the same time |
| F70Eh-F7FFh (`MP_B`) | the hit test's list of recent blits (3.4) | the same |
| EE00h-F0FFh (`objl_ram`) | the renderer: the wanted state, both pages' shown states, the dirty rectangles | copied again at a level's start (`lv_fresh`) |
| C68Ah-C6FEh | the stage's scalars, a union with Brainstorm's: the clip `$1EE42`, the mode `$1EEC6`, the palette pointer, the last tick, the renderer's page, camera and 15-byte command buffer | Brainstorm's while it runs; the two stages never run together |
| C6FFh | `pz_first` (`PZ_TEST` builds) | kept apart |
| DD0Ch (`ac_diff`, `AC_VARS`) | written by `front_range` | survives levels and games |

- Never touched: 0600h-09FFh, CF40h-CFC2h (`fs_buf` and the text engine), DD00h-DD7Fh, the
  addresses `docs/HARNESS.md` 2 lists.
- Everything the stage reads is set at its entry: nothing relies on the power-on RAM.
- `fr_code` is a fixed label, so the trace harness dumps it by name.
- Not kept:
  - the music divider `$1EB30`: the VBLANK ticks the music (3.7);
  - the restore list `$1EB4C`, the sprite table `$1FA8C` and the masks `$1ED96`: the renderer keeps
    its own;
  - `$B0C`: left 0.

### 3.3 Screen, VRAM, palette and sprites [D]

#### Layout: a camera over the 320-pixel street

A 256-pixel MSX line cannot show the 320-pixel street 1:1 at once. The targets span bitplane x
2-319, and the hit pixel 13-297.
- **A crop** to 256 (e.g. x 32-287) loses position 0 (scripts 31 and 34, 3/64 of the spawns) and
  8 of position 6's 22 columns. Rejected.
- **A relayout** of the buildings (Brainstorm's method) puts seams that the 64-pixel riser (random
  x 2-257) nearly always straddles. Its part beyond a seam would then show up to 24 pixels away
  from where the logic tests the hit, unless the stage's x runs in MSX coordinates, which is not
  trace-identical. Rejected while the logic must stay trace-identical (alternative of default 13).
- **The camera (the default).**
  - The street stays 320 wide in VRAM. The view shows scene x s to s + 255, s ∈ [0, 64].
  - MSX x = Amiga x − s and MSX y = Amiga y − 10: Amiga rows 10-171 fill lines 0-161. Rows 0-9 are
    sky and roof tops; nothing functional is there.
  - The 5 blank lines and the HUD (lines 167-211) follow through the existing split, as in
    Brainstorm.
  - **The rule**: once a pass, s ← clamp(clamp(s, cx − 191, cx − 64), 0, 64), with cx = the
    crosshair line's x (`$B9A` − 111). The camera moves only while the line is in the view's outer
    quarters. It starts at s = 32.
  - The line always stays on screen (cx − s ∈ [13, 233]).
  - Every target position can be shown whole: positions 0-8 each for some s; the riser for every
    x; the far walker lane from s = 32, the near one at s = 64.
- **The engine, on every VDP: level 1's V9938 method** (`msx/scroll9938.asm`):
  - Each display page is built at a coarse offset c ∈ {0, 16, 32, 48, 64}.
  - R#18 (set adjust) shows it at s: the image moves right by c − s, and R#18 can only move it by
    −7 to +8 (level 1's shift 8 − f, `msx/scroll9938.asm`: nibble 8 is +8, 7 is −7). So c − s ∈
    [−7, 8] (s − c ∈ [−8, 7]): c is the multiple of 16 in [s − 7, s + 8], and s = 8 takes c = 16 at
    +8, never c = 0 at −8, which R#18 cannot show. The shift goes into the page's published
    register list. R#18 moves the sprites with the bitmap, so the line sprites stay aligned.
  - When s leaves the back page's window, that page is rebuilt at the next c: about 121 ms of HMMM
    from the clean scene, plus the elements [E].
  - Up to 8 pixels of border show at one edge, as in level 1.
- **The HUD under R#18 on a V9958.** The HUD split resets R#18 only in its V9938 list
  (`isr.asm:606` `split_init`: "V9938: R#18 = 0 (the V9958 engine keeps R#18 at 0)"). On a V9958
  the list is `[8, R2_PAGE3, 82h, HUD_R23, 97h, R26_PAGE3, 9Ah, 0, 9Bh]`, so the HUD would shift
  with the range's R#18.
  - **The fix [D]**: while the range runs on a V9958 (`hud_msk` ≠ 0), the list's last register
    byte (`split_list` + 8) is 92h instead of 9Bh. The split then writes R#18 = 0 where it wrote
    R#27 = 0.
  - The range's lists keep R#25, R#26 and R#27 at 0 every frame, as `fs_list` and `bs_list` do, so
    the HUD needs no R#27 reset.
  - The list keeps its length (8), so the split's timed writes keep the timing `split_cal`
    measured. No split code changes.
  - `rg_stage` writes the byte after its first list. `rg_hide` writes it back after its last list
    (R#18 = 0) is on screen.
  - **V**: the list's layout and `sp_regs`' 6/8-byte paths (`split.asm`). **I**: that the split's
    timing holds with R#18 ≠ 0 on a V9958 (level 1's V9938 engine proves it on the V9938 only).
    Checked by 4.2 check 4 and the display guard.

#### VRAM

| Area | During the stage | After the stage |
|---|---|---|
| Page 0, lines 0-161 | display page A (with sprite set A) | `fe_text` clears it |
| Page 0, lines 162-249 | sheet S0 (the riser's 88-line frame, three type-4 dissolves, a walker) | free |
| Page 1, lines 0-161 | display page B (with set B) | free |
| Page 1, lines 162-250 | sheet S1 | free |
| Page 2, lines 0-161 | the clean scene, Amiga columns 64-319 | **restored**: `tiles_upload` E = 4 |
| Page 2, lines 162-242, x 0-127 | the clean scene, Amiga columns 0-63, as two 64 × 81 blocks | the same |
| Page 2, lines 162-248, x 128-255 | sheet S2 | the same |
| Page 3, lines 0-87 | **kept**: the play-field atlas | unchanged |
| Page 3, lines 88-161 | sheet S3, over the field engine's dynamic slot and caches | `fb_init` frees them: `fe_text` (`front.asm:423`) and `engines_init` run it before any field use (`msx/field.asm:293-323`) |
| Page 3, lines 176-179 | the 16 line patterns (1D800h) | a level's start forgets them (`spr_init`) |
| Page 3, lines 192-207 | sets A and B: colour rows of sprites 0-29 (all 15), the SATs | Y = 216 at entry 0 of both SATs; the colour rows stay until the sprite engine rewrites them |
| Page 3, lines 208-252 | **kept**: the HUD | unchanged |

The sheets hold 37 trimmed pictures (8 pop-ups, 6 walkers, 5 riser frames, 18 dissolve frames) and
9 front layers: 65,969 pixels. The block coordinates are in the gfx report's section 8 and its
`out/sizes.json`.

#### Palette and grade

- One index map for both visits; each Amiga colour is its 9-bit rounding (`tools/msxhud.py`
  `to_msx`). A joint k-means over CIELAB converged to the same map: mean error 3.93 (visit 1) and
  3.26 (visit 2).

```
index:   0   1   2   3   4   5   6   7   8   9   10  11  12  13  14  15
visit 1: 000 000 333 222 111 211 110 300 200 100 205 104 104 003 --- 171
visit 2: 000 000 222 111 000 111 100 200 100 000 002 003 104 104 --- 171
```

- Index 0 is the scene's black; **index 1 the sheets' black** (LMMM with TIMP treats 0 as
  transparent); 15 the crosshair's green; 14 free.
- **Graded as game play** (decision 8): `tools/mkrom.py` writes `gen/range_1_grade.pal` and
  `gen/range_2_grade.pal`, which `msx/frng.asm` includes as `rg_pal1`/`rg_pal2`. The `.pal` files
  and the previews stay plain.
- The fade (`rg_fade`, `logic.asm` `pal_fade`'s rule): `pf_pal` = the graded palette limited by
  `fade_cap[$BC1 >> 2]`. The VBLANK loads it; the HUD keeps its own palette through the split. At
  the end of a fade-out the palette goes back to visit 1's (the original's reset; invisible).

#### What is a VDP block and what is a sprite

- **Sprites: only the vertical lines**, mode 2, 16 × 16.
  - The patterns: column 0 set on rows 0..k (patterns 0-15, 512 B at 1D800h); colour rows all 15;
    SAT Y = line − 1.
  - **The crosshair's vertical line**: 10 sprites stacked from line 0 to 157 (Amiga rows 10-167;
    the tenth uses pattern 13). **[D] It passes through the hit column**, bitplane x `$B9A` − 111
    (default 17).
  - **The fire box's sides**: up to 10 sprites each, at the gfx model's x (c ± 16n − 113, the H −
    128 inference), only while n ≥ 1 and row `$B9E` − 16n ≥ −2 (default 18). Clipped to lines
    0-157 and to the page.
  - At most 30 sprites and the terminator; at most 3 on a line. Never flickering, never cut.
  - The SAT is written with OTIR from RAM: 23 T-states a byte.
- **Everything else is drawn by the VDP** into the page being built, in the original's z-order:
  1. **Restore**: HMMM from the clean scene in page 2. The rectangle is widened to whole bytes and
     split at Amiga column 64 and at the strip's row 81.
  2. **Pop-ups**: LMMM/TIMP of the trimmed picture, clipped to its position's rectangle, then
     LMMM/TIMP of **that position's front layer** (the scene's pixels where the 6th plane is set).
     Without the front layers, 10-379 pixels per slide step would be wrong [V: model].
  3. **The big target**: LMMM/TIMP, clipped at the walker's clip x.
  4. **The dissolve**: LMMM/TIMP.
  5. **Lines**: the crosshair's row (HMMV, 256 px, colour 15) and the box's top and bottom edges
     (LMMV).
- **Equality with the original [V: model].** The gfx report's sweep composes, through a model of
  VRAM, the stored sheets and these rules, then compares with a model of `$1EDBC`'s blits. The
  cases: 347 pop-up slide steps, 240 riser cases, 160 walker cases, 54 dissolve frames, 39 mixed
  moments, plus 3 full moments with lines and sprites. Result: 0 differing pixels.
- Display quirks 1, 2 and 4 (2.8) are not reproduced: zero-glitch rule and the stored pixels. Quirk 3
  is: the renderer draws what the ported routines draw in each pass.
- **Costs per page** [E: `docs/MSX_FEASIBILITY.md`'s rates with sprites on]:

| Change | VDP time |
|---|---|
| a pop-up's slide step (restore, picture, front layer) | ~13 ms |
| a walker's step | 18-28 ms |
| the riser's step or a type-4 dissolve frame | ~51 ms |
| a type 1-3 dissolve frame | 5-15 ms |
| the crosshair moving | ~2.5 ms |
| a camera rebuild | ~121 ms + the elements |

  Expected: about 25-30 pictures a second in typical play, 17-20 with a walker, about 12 during the
  riser's 20 animated passes, and about 7 while the camera pans. The renderer never waits for the
  VDP, so the logic keeps its 50 passes a second whatever the pictures do, as long as the CPU's own
  work per pass (the logic, the hit test, `rg_feed`'s bookkeeping, the SAT, `hud_keep`, the music
  tick in the VBLANK) fits a 50 Hz tick [E: not measured yet; 4.2 check 10 measures it].

#### The renderer: wanted state, shown state, double buffer, camera

This is Brainstorm's `bs_feed` model (`docs/BRAINSTORM.md` 3.3), with a page's coarse offset added.
- **The wanted state** (`rgw_...`, `objl_ram`) is written by `fr_frame` where the original draws,
  and never read by the logic:
  - per slot, the pop-up drawn this pass (position, picture, x, y) or none (`$1F5F8`);
  - the big target drawn by `$1F3F6` (picture, x, y, clip) or none;
  - the dissolve frame drawn by `$1F83A` (frame, x, y) or none;
  - the crosshair at the pass's end (`$B9A`, `$B9E`);
  - the fire box (n, and its centre and row from before the move) or none;
  - the camera s.
- **The shown state** of each page (`rgs0`, `rgs1`): its c, and the same fields as last drawn into
  it.
- **`rg_feed`**, a state machine called while `rg_wait` waits and once after each pass. It never
  waits for the VDP:

| State | Moves on when | What it does |
|---|---|---|
| idle | a new pass, the VDP idle | target = the page not shown. If its c does not cover s, c = the multiple of 16 in [s − 7, s + 8] (the engine bullet above), and the whole page is dirty |
| building | the VDP idle | one command for the next dirty rectangle (the old box ∪ the new box of each element that differs), then the elements that meet it in z-order; when none is left: the target set's SAT, then the list (`rg_list`: `bs_list`'s with R#18 = the page's shift, R#25-R#27 = 0 on a V9958) |
| published | `app_seq` = `pub_seq` | that page is shown (`rgv_shown`); back to idle |

- Each page shows the state of one recent pass, element by element, never a half-drawn block.
- While a camera rebuild runs (~150 ms), the shown page keeps its picture: the targets and the
  crosshair hold still meanwhile (default 15).
- **Entry** (`rg_show`; the play area black and the intro's list on screen):
  - `range_gfx.bin` into page 2 and the four sheet areas through the 8000h window (63,616 B, about
    0.5 s [E]);
  - both pages built at c = 32;
  - the line patterns; the colour rows of sprites 0-29 in both sets; both SATs empty;
  - the shown states unset;
  - on a V9958, the split byte (above).
- **Exit**: `rg_hide` (3.1).
- **Engine rules** (Brainstorm's, `docs/BRAINSTORM.md` 3.3):
  - every command goes through `vdp_cmd` from the renderer's own 15-byte buffer, never `cmdbuf`;
  - `fe_text`'s `fb_init` leaves no play-field copy pending, so nothing new runs in the interrupts;
  - every VRAM stream uses `vram_write` / `vram_done`;
  - no OTIR runs past 9FFFh (streams split at the 8 KiB boundaries);
  - `BANK_FRONT` is back before any FRONT routine;
  - every write to the VDP's data port comes at least 22 T-states after the one before (the 5.37
    MHz rule of `docs/BRAINSTORM.md` 4.6 g).

### 3.4 The hit test on the Z80 [D; V for the rule it reproduces]

`$1EDBC`'s first blit writes the shifted mask into `$7FC50`, and the CPU tests one bit of it (2.2).
A full shadow of that buffer (up to about 2,000 words a pass) is too slow for a Z80. The port
computes the one byte the test reads instead (the logic report's section 11):

- **Every draw call** (`rg_bob`, erases and effects included) computes, as `$1EDBC`, in 16-bit
  words:
  - the right clip from the clip variable;
  - k (words dropped) and w' = w − k;
  - the bounds of `$BA2` (column) and `$BA4` (row), where row h passes (T1).

  Then it pushes an entry {mode, mask, w', h, shift, x, y} on the **recent-blit list** and drops
  every older entry whose output size 2w'h is ≤ the new one's. A call clipped to nothing (the C
  modulo reaching 40: `$1EE64`, exit `$1ED56`) returns before its blit: no entry, no test, D0
  unchanged (the logic report's 7.6).
  - The list's sizes strictly fall from the oldest entry to the newest, so its length is at most the
    number of distinct output sizes the tables allow (pop-ups, walkers at every clip, the riser's
    five heights, the four effect sizes, the erases). `tools/msxrange.py` computes that bound from
    the tables, and a build check keeps bound × entry size within F70Eh-F7FFh (242 bytes); in
    practice the list stays a few entries long.
- **The test** (only when `$1EB46` is set and `$BA2` ≥ 0, i.e. at most 3 calls in a pass after a
  shot):
  - i = (2w' × `$BA4` + (`$BA2` >> 3)) & `$FFFF`, bit 7 − (`$BA2` & 7);
  - the newest entry whose output covers i gives the byte: mode `$100` → 0; `$9F0` → S; `$B50` →
    S & ~C;
  - S is the mask word shifted by x & 15 (the first word masked by FFFF, the last by 0000: the
    clipped BOB's last 16 pixels are never hit), and C the priority plane's word at the blit's
    position;
  - no entry → 0 (the bench's buffer starts at 0; the real Amiga's initial bytes are unknown [I]).
- **The data**: `range_hit.bin`, read through the 8000h window, one byte at a time, then
  `BANK_FRONT` back.
  - Bank 97: the priority plane (6,880 B, rows of 40 bytes as at `$466C2`).
  - Bank 98: the masks of the 8 pop-up, 6 walker and 5 riser pictures (920 + 1,944 + 2,032 = 4,896
    B, each as in FRNG: (w − 1) words × h).
  - Neither plane crosses a bank. `range_tab.inc` gives each mask's address, keyed by the graphic's
    Amiga address (the descriptors and the big tables hold Amiga addresses).
- **The dissolves' masks are not stored.**
  - **V on the traces**: the logic report's model (equal to the bench) was instrumented for this
    plan (`$RS/design/fxmask_check.py`, output `fxmask_check.txt`). It records which blit last
    wrote each byte a test reads, over all 22 bench traces.
  - The tests whose result is used (the pop-ups' and the big target's) read 252 bytes, 6 of them
    past their own blit's output (T1). None was last written by an effect: those 6 hold the big
    target's erase (zeros).
  - **I in general**: each effect's output is zeroed by the next pass's `frng_fx_erase` before any
    target draws. The erase has the same frame, x, y and clip: nothing between them changes the
    clip, and the big erase runs before the targets.
  - Step 2 runs the same check on the new drives. If it ever fails, `range_hit.bin` grows by their
    6,400 B (still 2 banks).
- `$B0B`, `$BA2-$BA5` and `$BB8` are per-call results only the caller reads. The port computes
  them where the original's callers read them (the pop-ups' `+$12`/`+$13`, `$BB2`/`$BB5`); the
  trace leaves them out.

### 3.5 Timing [D]

- **One pass per 50 Hz tick, on 50 and 60 Hz machines** (default 1).
  - FRNG's loop waits for one raster line a frame, so its PAL design speed is 50 passes a second.
    That is the rate Brainstorm and the text screens use.
  - At 60 Hz every sixth VBLANK is skipped (`fs_tick`'s `fs_div`). `TICK_HZ` does not apply.
- **The timer** is the CIA-B's: `sec_tick` (fixed code, real seconds by VBLANKs) after each wait.
  `rg_timer` resets `sec_n` and the stage's last-tick base.
  - The time out comes about 121 s after the set-up, real time, as on the Amiga.
  - In script builds (`EXTJOY=1`, `JOY=`), `sec_tick` is a `ret`: the timer stands still at 2:00,
    as on the bench. A drive ends by 25 shots or by a poke of `$804C`.
- **The loop** (`msx/frng.asm`):

```
rg_loop:  rg_wait                  ; the next 50 Hz tick ($1EA40); rg_feed meanwhile; wf_n
          hud_keep                 ; ($8004, $8020: the panel), before the beam reaches the HUD
          sec_tick                 ; ($1015E: the CIA-B second; still in script builds)
fr_tick:  call fr_frame            ; one pass: the trace's sampling point ($1EA4A)
          rg_feed
          rg_end                   ; the end checks ($1EAA6-$1EAFA) -> rg_loop, or rg_hide / jp fr_done
fr_frame: rg_fade; rg_bigerase; rg_fxerase; rg_targets (+ rg_bigdraw); rg_fxdraw; rg_cross;
          $B00 + 1; $B02 + 3; joy_read; rg_delays; tick_n + 1; the wanted state
```

- No music tick in the pass: the VBLANK ticks it (3.7).
- `tick_n` + 1 each pass lets a `JOY=` script go on through the stage.
- The end sequences keep their PAL lengths: 2.6 s after the last shot.
- Turbo R: the range runs on the Z80 at 3.58 MHz, after `front_bonus`' `fb_prep` (the hardware
  pause off, the split measured for the Z80). The OPLL can be written there (3.7).

### 3.6 Input [D]

- `joy_read` as in the game (`player.asm`): joystick port 1 (trigger A is fire), else the keyboard
  byte (cursor keys, SPACE or RETURN fire). The whole byte goes to `$802E`. Trigger B does nothing.
- It is called at the original's point (after the crosshair), so the crosshair uses the previous
  pass's byte.
- **Opposite directions**: `read_joystick`'s table reads up + down or left + right on the joystick
  as no direction, but the keyboard byte can hold both bits. FRNG then takes right over left and
  down over up; the port follows (the `fr_opp` drive).
- Holding fire shoots every 25 passes (0.5 s); each new press shoots at once.
- `EXTJOY=1` builds: `ext_joy` (CE5Ah), taken as is, poked by the Tcl at `fr_tick`. `JOY=` builds:
  the script by `tick_n`.
- No pause: FRNG never sets `$804E`. On a turbo R, PAUSE does nothing during the bonus screens, as
  in Brainstorm.

### 3.7 Sound [D; V: the sound report's interpreter runs]

- **Data** (`tools/msxtune.py` `convert_frm` → `build/msx/frm.bin`, 39,341 B, banks 99-103 from
  `FRM_BANK`):
  - **The extraction.** FRNG_15 is decrunched (`tools/bytekiller.py`), and `$20000-$485D9` is
    moved to `$18000` as `frm_extract.py` does: the code's absolute operands, the per-file table
    operands, **and record 0's start and loop** (`$20B96`).
    - The ROM-budget day's extraction missed record 0. Its model played effects 3-5 with the wrong
      bytes, and its effect sizes were wrong; tune 1 was unaffected.
    - The cache: `build/music/FRM_00.bin` + `FRM.json`, like PZM's.
  - **Tune 1** in three versions, through the routing step and the title's converters unchanged.
    The routing steals no note and needs at most 3 melodic voices.

| Version | Content | Bytes |
|---|---|---:|
| SCC | SCC voices 0-2 with each sample's waveform; the drums on PSG C | 16,652 |
| OPLL | channels 0-2 (#1 custom patch, PIZZICATO piano, #4 acoustic bass, WARM organ) and the rhythm (SNAZ as SD, TOM1 as tom) | 16,544 |
| PSG | A-C at the title's λ; #1 an octave up | 5,882 |

  - **Effects 2-4** are converted at the tune's reference, so the Amiga's balance holds (effect 2
    as loud as the music's loudest, 3 and 4 about 9.5 dB under it). Effect 5 is not converted:
    FRNG never requests it.
    - Effect 2 is pure noise: msxsccfx gives it no SCC part. With an SCC, its PSG noise part at
      the SCC music's scale (levels 12/11) becomes its SCC-mode stream, flagged by bit 7 of its
      "SCC ticks" byte. `pzm.bin`'s entries never reach 128 ticks, so `pzm.bin` keeps its bytes.
    - Sizes, SCC-mode + PSG-alone streams: effect 2 18 + 4 B, effect 3 22 + 21 B, effect 4 50 +
      49 B: 90 + 74 B in all.
  - **`tools/msxscc.py`**: a note whose period would pass 4095 plays an octave up instead of
    clamping (FRM's bass "#1": 10 key-ons at 25.1 Hz, 147 cents sharp if clamped). TITM's and
    PZM's streams never pass N 3,329, so `scc.bin` and `pzm.bin` keep their bytes.
- **Player** (`msx/tune.asm`, in `BANK_MUSIC` past B800h, which has 1,480 B free):
  - `tn_frm`: `ld hl,fr_desc` / `jr tn_start` (5 B), with `tn_pzm`'s layout guard;
  - effect 2 with an SCC: in `tn_go`, the flag selects MVK_PSG for the effect voice, and `tn_tick`
    plays it on **PSG voice B**, idle in both SCC modes (about 22 B);
  - a kind switch while sounding (2 cut by 3 or 4) silences PSG B first (about 14 B). Brainstorm's
    effects, all SCC-kind, write exactly what they write today;
  - `tune.inc` gets `fr_desc` (56 B) and `fr_fx` (27 B) after PZM's, which keep their bytes;
  - no fixed-area byte; no RAM (C2D9h-C2FFh stays free).
- **Unchanged and enough** [V: the sound report ran the repository's unchanged `tune.asm` with FRM
  as `pzm.bin` in its Z80 interpreter]: tune 1 and effects 3-4, register-exact for 6,100 ticks on
  the SCC with the PSG drums, the SCC with the OPLL's rhythm, the OPLL alone and the PSG alone, at
  50 and 60 Hz.
- **The stage's calls** (in `BANK_FRNG`, where the 68000 makes them):
  - after the set-up, before the first pass: `ld hl,tn_frm` / `call mus_call` (`$1EA32`). No
    `snd_stop` right before it: `tn_start`'s stop all is the stop;
  - effect 2 in `rg_cross` at the shot (`$1ECB4`); effects 3 and 4 in `rg_delays` (`$1EB0E`,
    `$1EB2A`): `ld a,n` / `call snd_rfx`;
  - `snd_rfx` is `snd_bfx`'s 12 bytes copied into `BANK_FRNG` (both banks sit at A000h). It writes
    only RAM (`tn_req`, `fx_act`), so the traces are the silent stage's.
- **Ticks**: the VBLANK's 50 Hz ticks (`sq_frame`; at 60 Hz the sixth VBLANK skipped), **50 ticks
  a second** (default 25).
  - `tn_hold` keeps tick 0 until the pass counter moves. FRNG's pass counter is `$B00` at AM +
    `$B00`, the same address as Brainstorm's `pzv_frame`, so tick 0 comes after the first pass.
  - The tune then lasts the stage's 2:00.
- **A shot and a due hit sound in one pass**: the higher request stays (`snd_bfx`'s rule). The
  Amiga sounds the shot for one tick first; the port loses that tick (default 28).
- **At the stage's end**: `rg_end`'s `snd_stop` silences every chip set right after the last pass,
  before `rg_hide` (as built; the plan had `fe_text`'s stop, which came about 13 ticks later), and
  `fe_text` stops it again. The title after the range must write its chips as the title after
  Brainstorm does, but for registers nobody hears (SCC channel 3's waveform, PSG B's period).
- **Cost** [E: the sound report's interpreter with MSX timings]:
  - per tick, a mean of 2,766-4,237 T-states (3.9-5.9 % of the Z80);
  - about 10 % of a pass in the worst 1 % of ticks;
  - 14-19 % once, at the tune's tick 0 (3.9 ms at most inside the VBLANK interrupt, well before
    the HUD split's line).

### 3.8 The intro, result and time-out texts [D; V: the flow report's prototype]

- `tools/msxtext.py` appends three scripts to `text.inc` after Brainstorm's. It checks that only
  commands 2 and 7 occur, every glyph is in the font, every line fits the 256 × 162 play area
  (x = 8c − 16, y = 67 + 8r), and the original's call counts.

| Label | Source | Bytes | Elements / calls |
|---|---|---:|---|
| `txt_rg_intro` | `$1142D`, the long line split | 127 | 112 / 304 (the original's) |
| `txt_rg_res` | `$113A5` up to `FF 07` | 104 | 91 / 347 |
| `txt_rg_rate` | `$1140D`, the four names | 32 | — |
| `txt_bs_time` | `$11698`: Brainstorm's, reused | 42 | 33 / 129 |

- `txt_rg_res`' fields are stored as 8 spaces. Equates: `TXT_RG_LEN` 104; `TXT_RG_F1` 37
  (`$113CA`, correct), `TXT_RG_F2` 63 (`$113E4`, dummy), `TXT_RG_F3` 91 (`$11400`, the name).
  `fs_num` writes the digits from the field's end, `$11DC6`'s format.
- **The intro's long line** "YOUR GUN CALIBRATION WILL BE TESTED" (35 characters at column 1: x −8
  to 271) cannot fit 256 pixels; `fs_char` has no bounds check. The port's copy splits it after
  "CALIBRATION" (default 4):

```
00 0B 00 "SHOOTING RANGE."                  row 0, x 72-191   (as the original)
00 05 03 "YOU MUST SHOOT ARMED TARGETS"     row 3, x 24-247   (as the original)
00 09 05 "YOUR GUN CALIBRATION"             row 5, x 56-215
00 0C 06 "WILL BE TESTED"                   row 6, x 80-191
00 04 08 "WARNING ACCURACY IS ESSENTIAL."   row 8, x 16-255   (was row 7)
FF 02 30 FF 07
```

  Five positions and 107 characters: 112 elements, as the original's 4 + 108. The screen still
  lasts 304 calls (305 ticks without fire). Rows 0-8 leave row 10 to the `TAG` line.
- The result and the time out fit as they are. The widest result line is "YOU ARE RATED AS SHARP."
  at x 24-223.
- The tool writes each script's finished play area (`build/msx/text_rg_*.sc5` and `.png`). It also
  gains `render-result CORRECT DUMMY MINUTES`, the reference of the result screen for any counts.
- `fe_text` runs `hud_keep` each tick, so "NO AMMO." or "TIME OUT." ticks on during the result, as
  on the Amiga.

### 3.9 The HUD [D]

- It stays shown and updated as in the game:
  - the weapon icon (weapon 0, from `set_weapon`);
  - the ammo 025 counting down (AG `$8030`, which `hud_frame` reads already);
  - the timer from 2:00;
  - the score (+ 25 per paid correct hit);
  - the message line.
- The lives stay; the can never moves (`g_tick` = 0, set by `fb_prep`).
- **Messages.** `tools/msxhudrt.py` appends FRNG's two strings to the bonus table after PUZL's three:
  - "NO AMMO." `$1EB32` is **177** (`HUD_MSG_1EB32`), "TIME OUT." `$1EB3B` **178**
    (`HUD_MSG_1EB3B`);
  - the table grows to 5 pointers: PUZL's strings move 4 bytes and keep their numbers (174-176);
  - 23 B of the 447 free;
  - level 1's 21 messages, `HUD_NMSGS` and every earlier byte keep their values;
  - the tool reads FRNG decrunched (`tools/bytekiller.py`; a fifth argument, `FRNG_15.bin`).

### 3.10 The rating and `$8060` [D]

- The port keeps `$8060` as **`ac_diff`** (DD0Ch, `AC_VARS`, cleared only at power-on): a pointer
  into `diff_tab` (`$C716-$C735`, `gen/at_c1.inc`, in `BANK_LC1`). `slot_place`
  (`objects.asm:568`) reads it for every enemy's hit points (`OS_HP`, + `$21`).
- `front_range` sets `ac_diff` = `diff_tab` + 24 − 8 × rating, or `diff_tab` + 24 (POOR) on a
  time out (3.1). AG `$8060` is not written: no port code reads it.
- **Level 1 does not change** [V: the source]. `obj_start` (`objects.asm:39`) sets `ac_diff` =
  `diff_tab` (SHARP) at every level start, from `ng_go` (`rc2.asm:131`) and `level_restart`
  (`rc2.asm:332`). Today the title and a new game follow the range, so level 1 always gets SHARP,
  as the original's `$8314`.
- **When level 2 is ported**, the 6 bytes `ld hl,diff_tab` / `ld (ac_diff),hl` move from
  `obj_start` to `ng_go`, the port of `load_level0`'s `$8314`. A new game then sets SHARP, and
  deaths and the next level's start keep the range's value, as on the Amiga (`$8314` is inside
  `load_level0` `$82EC`; REA finds no direct caller of `$82EC`, so whether a continue runs it again
  is **I**, for level 2's plan to trace). Otherwise
  level 2 loses the rating. **This belongs in level 2's plan**, with a check that level 2's spawns
  use the range's table.
- The trace reads the rating as the word at `ac_diff` − `diff_tab`: 0 SHARP, 8 GOOD, 16 FAIR, 24
  POOR or a time out (default 9). The Amiga's is `$8060` − `$C716`.

### 3.11 The converter `tools/msxrange.py` [D; prototype: the gfx report's `scripts/msxrange.py`]

- Stdlib only. It imports `tools/msxhud.py` (`to_msx`), `tools/msxbright.py`, `tools/planar.py` and
  `tools/bytekiller.py`.
- Input `build/extracted/files/FRNG_15.bin`, decrunched (93,224 → 170,970 B, checksum 0).
- The `msx` target's line: `$(PYTHON) -I tools/msxrange.py $(X)/files/FRNG_15.bin
  $(BUILD)/msx/range`.

| Output | Format | Bytes |
|---|---|---:|
| `range_1.pal`, `range_2.pal` | 16 colours, V9938 pairs (R << 4 \| B, G), plain | 32 each |
| `range_gfx.bin` | one stream of raw nibbles (left pixel high): the scene's columns 64-319 (162 lines × 128 B, into page 2 line 0); the strip (81 lines × 64 B: both 64 × 81 blocks side by side, page 2 line 162); then S0, S1 (88 / 89 lines × 128 B), S2 (87 lines × 64 B at x 128), S3 (74 lines × 128 B at page 3 line 88) | 20,736 + 5,184 + 37,696 = 63,616 |
| `range_hit.bin` | **new**: from a bank boundary, the priority plane `$466C2` (6,880 B), padded to 8 KiB; then the 19 masks (4,896 B) | 11,776 used, 2 banks |
| `range_line.spr` | 16 patterns × 32 B (mode 2: left 8 columns, then right 8) | 512 |
| `range.inc` | equates only: TOP, VIEW_H, CAM_MAX, the blob's streams (offset, length, VDP x/y, bytes a line), each position's Amiga rectangle and its front layer's VDP x/y, the colour indices | — |
| `range_tab.inc` | data for `BANK_FRNG`, keyed by the Amiga graphic address: each picture's sheet x, y, w, h and trim, its mask's address in `range_hit.bin`; the 9 position rectangles; the 9 front layers; FRNG's tables in the 68000's layout (scripts `$1EF88`, the stubs' descriptors, the riser's and walkers' tables, the effect tables); `fr_code`'s initial 526 bytes in the mirror rule | ~2,000 |
| `range_*.png` | previews: the stored scene and sheets; moments at s = 0, 32 and 64, plain and graded with the HUD; visit 2; the Amiga against the MSX | — |

- **Checks on every run** (any failure stops the tool):
  - the decrunch length and checksum;
  - the tables and both palettes equal section 2.6 and the logic report's `tables/`;
  - every colour the stage shows maps by rounding; the scene uses no index 1 or 15; no sheet pixel
    inside a mask is 0;
  - every pop-up's visible pixels lie in its position's rectangle, and the rectangles do not
    overlap;
  - the blocks fit their areas without overlap and never meet the scene;
  - the sweep of 3.3 equals the Amiga composition pixel for pixel;
  - the SAT stays within 31 entries and 3 sprites a line;
  - `range_hit.bin`'s bytes equal the decrunched file's.
- **`render` mode**, as `msxpuzl.py render`: a page's shown state (from a RAM dump) plus the SAT
  and R#18 → `.sc5` and `.png`. These are the references of the stills (4.2).
- Tests: `tests/test_msxrange.py`.

### 3.12 `tools/mkrom.py` and the banks [D, E]

- **The layout.** `STAGES = ("PUZL", "FRNG")`: the stage code stays `rc2.asm`'s last sections,
  assembled as before.
  - mkrom slices it: PUZL's bank after the sound effects (78, as today), then `puzl_gfx.bin` and
    `pzm.bin`, then FRNG's bank, `range_gfx.bin`, `range_hit.bin` and `frm.bin`.
  - **No Brainstorm bank moves** (default 7); the code-size check counts both stages.
- `banks.inc` gets `BANK_FRNG`, `RANGE_GFX_BANK`, `RANGE_GFX_BANKS`, `RANGE_HIT_BANK` and
  `FRM_BANK`; the summary line names them.
- `gen/range_1_grade.pal`, `gen/range_2_grade.pal` are written like `puzl_1_grade.pal`;
  `range.inc`, `range_tab.inc` and `range_line.spr` are copied to `gen`.
- `PZ_TEST` accepts 0-2 (section 6).

| Item | Banks | Total |
|---|---:|---:|
| Today (`4a8a61d`) | 88 | 88 |
| `BANK_FRNG`: code and tables (≤ 7,500 B [E]) | 1 | 89 (bank 88) |
| `range_gfx.bin`, raw (63,616 B; 1,920 B free in the last) | 8 | 97 (89-96) |
| `range_hit.bin` (11,776 B) | 2 | 99 (97-98) |
| `frm.bin` (39,341 B; 1,619 B free in the last) | 5 | **104** (99-103) |

- **The image stays 1 MiB** for the test ROMs: 128 banks, 104 used, 24 free. The 2 MiB twins
  (`ROM_2M=1`) have 256 banks with the boot guard's tag in bank 255.
- **mkrom's checks** must pass on every build (`ROM_2M=1`, `DIAG=1` and `2`, `PZ_TEST` 0-2):
  - the 3Fh rule: banks 88-103 are 24-39 mod 64;
  - no "OPLL";
  - ≤ 256 banks;
  - the **SCC test values** at a bank's 1800h. In a 1 MiB image this means bank 90 (5Ah: now
    `range_gfx.bin` data), bank 36 (24h), bank 63 (BFh and every value) and **bank 9 (89h:
    `BANK_MUSIC`'s B800h, where `tune.asm`'s bytes move at step 11)**. In 2 MiB it means banks 36,
    63, 90, 137 and 191.
  - The check is data-dependent. If it fails, reorder or pad a blob (or move `tune.inc`'s new
    descriptor past `tune.asm`).
- **Banks the stage maps** [E]: 0-1, `BANK_FRONT`, `BANK_FRNG`, `BANK_LC1` (once), the 2 HUD
  banks, `BANK_INPUT`, `BANK_MUSIC`, `SCCFX_BANK`, `BANK_FIELD` (the text screens), the 8 graphics
  banks (entry only), the 2 hit banks, the 5 music banks, the 4 tile banks (exit only): about 29.
  That is far under the MSX Pico+'s 53-bank speed target (`docs/PICO_CACHE.md`).
- **The whole game against the mandatory 2 MiB** [E: `docs/ROM_BUDGET.md` 4.1, scenario A with the
  range's graphics raw]:
  - That scenario counts 192 / 196 / 203 banks (low, likely, high) for the whole game. It counted
    the range at 16 / 16 / 18 banks (code 1/1/2, graphics raw 10, tune 5/5/6).
  - This design's range is 16 banks, so the whole game stays at about **192 / 196 / 201 of 256**:
    55 or more spare.
  - ZX0 for the bonus graphics stays a fallback (about −5 banks for the range, −8 for Brainstorm).

### 3.13 What the stage leaves [D]

| Item | After the stage |
|---|---|
| `ac_diff` | the rating's table; `obj_start` resets SHARP at the next level start (level 2 will change that: 3.10) |
| AG `$8046-$8049` | the score with the paid hits |
| AG `$8030`, `$805C`, `$804A`, `$804C` | as the stage left them; `new_game` clears AG, and the next level's start sets them |
| AM, `fr_code` (`MP_B`), `objl_ram`, C68Ah-C6FEh | dead; `new_game` rebuilds them |
| HUD queue | may hold "NO AMMO." / "TIME OUT."; they tick on in the result; `hud_init` clears it |
| VRAM | page 2 and both SATs back; pages 0-1 and page 3 lines 88-161 overwritten (`fb_init` frees the caches); the line patterns and the colour rows of sprites 0-29 until the sprite engine rewrites them |
| `split_list` | the V9958 list back as `split_init` wrote it |
| CPU | the Z80 on a turbo R; `jp cpu_title` turns its hardware pause on again |

## 4. Verification (all in openMSX)

The user cannot test on hardware before the delivery, so every check below runs in headless
openMSX through the MSX-AI MCP (`msx_local_*`), on the machines already in the MCP's home, at most
two instances, with the harness's ground rules (`docs/HARNESS.md` 1: no `vwait`, `exit`, `max` or
`min` in Tcl, files opened once). Offline checks (the converters' tests, a Z80 interpreter) come
first where they are cheaper; they never replace the openMSX run of the same thing.

Machines:
- C-BIOS_MSX2 (V9938, 60 Hz) and the Panasonic FS-A1GT (turbo R, the stage on its Z80, V9958) for
  everything;
- the Panasonic FS-A1FX (MSX2+, V9958) and C-BIOS_MSX2_EU (50 Hz) for the main drive;
- the Gradiente Expert 2.0 (MSX2) and the Sony HB-F1XDJ (V9958) for the flows and the fresh-machine
  runs;
- C-BIOS_MSX2+ for the 5.37 MHz VRAM speed.

### 4.1 Logic: the bench against the MSX trace

- **The bench's `frng` mode** (`tools/amigaemu.py frng`, Unicorn; the bench report's patch).
  - It runs FRNG along the game's own path: the loader, `$124A6`, `$8420` entered at `$845E`, which
    applies its patches, calls `$1EA00` and rates. `--via-8420` runs the whole `$8420`.
  - It applies a drive file's joystick byte and pokes at each FRNG frame's start (`$1EA4A`), records
    `--trace` / `--trace-ram` there, and stops once `$8420` has chosen `$8060` and the text.
  - `--sec N` raises the CIA-B second every N frames. `--level 2` (with `build/ram/level2_full.bin`)
    runs visit 2.
  - The puzl mode's Unicorn fixes carry over (`FrngBench` is a `PuzlBench`). The game and puzl
    modes stay byte-identical.
- **The executable model** (the logic report's `frngmodel.py`, scratch) equals the original in
  every field of 22 traces, 14,949 passes. It is the spec's check and the place to try a port
  rule before writing Z80.
- **The labels the port provides** (`tools/openmsx_rc2.tcl` looks them up in the label file):

| Label | What |
|---|---|
| `fr_tick` | the `call fr_frame` at the start of every pass, after the wait, `hud_keep` and `sec_tick` (the Amiga's `$1EA4A`). The breakpoint checks its bytes (CD lo hi), so it fires only where `BANK_FRNG` is mapped |
| `fr_frame` | its target |
| `fr_done` | fixed code, a `ret`, reached once when the stage returns, before anything changes the mirror (the Amiga's `$847A`) |
| `fr_rated` | fixed code, a `ret`, reached once after `ac_diff` is set, on both paths |
| `fr_code` | F500h: the 526 bytes of 3.2 |
| `ac_diff`, `diff_tab` | the rating's readout |
| `ext_joy` | CE5Ah |

- **`rc2_fr_drive`** resets the machine with an `EXTJOY=1 PZ_TEST=2` ROM (`PZ_LEVEL=2` for visit
  2).
  - At each `fr_tick` it records D000h-D0C5h, DC00h-DCFFh and `fr_code`'s 526 bytes. Then it pokes
    the pass's joystick byte (index `$B00`) into `ext_joy`, then that pass's pokes.
  - At `fr_done` it writes `# result DUMMY CORRECT TIMEOUT`; at `fr_rated` `# rating`, the word at
    `ac_diff` − `diff_tab` (the bench report's procs, with DC62h and `hp_sharp` replaced by these
    two labels).
- **`rc2_fr_arm`** does the same in the running machine, after a played level 1 and Brainstorm.
- **`tools/frngcmp.py`** compares 143 fields (`analysis/frng_ram.tsv`) pass by pass, then the
  result and the rating.
  - Left out: display state, the music divider, the per-call results (`$B0B`, `$BA2-$BA5`, `$BB8`),
    and dead state (`$B0C`, the spawn's D1 leftovers).
  - Two fields are conditional: a slot's x only while its slot runs, a hit column only while its
    hit flag is set.
- **The drives** (`build/emu/fr_<name>.drive` and `fr_<name>_ram.jsonl`):

| Drive | Visit | FRNG passes | Dummy, correct, `$804C` | Rating | What it covers |
|---|---|---:|---|---|---|
| `armed` | 1 | 1,163 | 0, 25, 0 | SHARP | 25 aimed at armed targets: pop-ups, a walker, the riser |
| `mixed` | 1 | 1,869 | 8, 17, 0 | SHARP | **dummies hit** (every third shot) |
| `dummy` | 1 | made at step 2 | dummies only | POOR | `frngbot.py --mode dummy`: split targets' right parts, dummy walkers |
| `poor`, `fair`, `good` | 1 | 386, 659, 730 | 0, 5 / 11 / 14, 0 | POOR / FAIR / GOOD | **good shooting** at each rating, the rest missed |
| `good_min0` | 1 | 730 | 0, 14, 0 | FAIR | the minutes-0 penalty (AG `$804A` poked to 0 at 700) |
| `timeout` | 1 | about 301 | —, —, FF | POOR | **a time out**: `$804C` poked at a pass near 300 where the camera's s (a function of `$B9A`'s history: 3.3's rule) is not a multiple of 16, so that R#18 ≠ 0 when it cuts (risk 14); the immediate return. The bench report's poke at a fixed pass of `armed` lands wherever s happens to be, R#18 = 0 included (s a multiple of 16, as at the start's 32), and then the cut goes untested |
| `late_timeout` | 1 | 1,163 | 0, 25, FF | POOR | T5: a time out in the end count |
| `hold` | 1 | ~755 [E] | 0, 0, 0 | POOR | fire held from the start: 25 misses 25 passes apart (the bench report's `fireall` run) |
| `opp` | 1 | 81 (cap) | — | — | 10 pokes of `$802E` with opposite bits (right over left, down over up) |
| `edge` | 1 | made at step 2 | — | — | T1: aiming one row below the targets (the logic report's `bot_edge`: 344 passes, 28 T1 reads among 8 traces) |
| `fuzz` | 1 | made at step 2 | — | — | random keys, diagonals, fire toggles (the logic report's `fuzz1`) |
| `quirk4` | 1 | made at step 2 | — | — | T4: two armed hits scored within 10 passes (a double hit the bot finds, else a poke of `$BBC` = 10 five passes after a scored hit) |
| `armed2` | **2** | 1,163 | 0, 25, 0 | SHARP | **visit 2** (`PZ_LEVEL=2`): only the palette differs |

- **Expected**: every drive "0 differ" in all 143 fields of every pass, with the same result and
  rating, on C-BIOS_MSX2 and the FS-A1GT; `armed` also on the FS-A1FX and C-BIOS_MSX2_EU; `armed`
  and `opp` on the Gradiente Expert 2.0.
- **After a played level 1 and Brainstorm** (`EXTJOY=1` build): `rc2_drive_rom` with `drive_end`,
  then `rc2_pz_arm` with `pz_fail`, then `rc2_fr_arm` with `fr_mixed`. Expected: `frngcmp.py --skip
  score`, 0 differ, on C-BIOS_MSX2 and the FS-A1GT.
- **The rating, exhaustively.** The built `front_range`'s rating code runs offline in a Z80
  interpreter on the ROM's FRONT bank for the 5,043 cases of the flow report's `ratebench.py`: 0
  differences. In openMSX, the drives cover every rating and both paths.
- Headless runs never press fire, so every text screen runs its full length: the intro 305 ticks,
  the result 348, OUT OF TIME. 130.

### 4.2 Visual checks

1. **The text screens.** Page 0's play area equals `tools/msxtext.py`'s render, pixel for pixel:
   the intro, the result for each drive's counts (`render-result`) and OUT OF TIME. On the MSX2, the
   MSX2+ and the turbo R; with "TEST 4" at row 10 in a `TAG=4` build.
2. **Stills.** Snapshots (VRAM, RAM, registers) at chosen passes of `armed`, `mixed`, `edge`,
   `timeout` and `armed2`: the fade-in, two pop-ups mid-slide, the riser at frame 4, a walker
   clipped at the door, a dissolve, the fire box at n = 8 and n = 3, the camera at s = 0, 32 and
   64, the end's fade-out, visit 2.
   - s = 0, 32 and 64 are pages at c = s: R#18 is 0 there. Stills at s = 7 and s = 8 (shifts −7
     and +8, the ends of R#18's range) and at one s inside a 16-px step are needed too, or no still
     checks R#18's value or sign.
   - The page R#2 shows, with its set's SAT and the published R#18, must equal `tools/msxrange.py
     render` of that page's shown state (in the snapshot's RAM): 0 pixels differ. The render applies
     R#18 with level 1's sign (nibble 8 moves the picture 8 px right, 7 moves it 7 px left).
   - The view of the same moment must equal the converter's model of the Amiga's own composition.
3. **Records** at every VBLANK of whole drives (`armed`, `mixed`, `edge`, `timeout`, `armed2`):
   - no torn element: every element rectangle shows one of its states;
   - **frame-to-frame coherence**: no pixel outside the elements changes, compared in scene
     coordinates (screen x + s) so that a camera move is not a change; only the page's 256 columns
     are compared, never the set-adjust border (up to 8 columns at one edge while R#18 ≠ 0), which
     shows no scene pixel;
   - the SAT is valid: at most 31 entries, at most 3 sprites a line, the crosshair at the bench's
     position of the pass the list was published after;
   - the crosshair always inside the view;
   - **the time-out cut** (`timeout`'s record runs on to OUT OF TIME.'s first lit picture): from the
     time-out pass on, no VBLANK applies a list whose R#18 differs from the shown page's own while
     the play area's palette is lit; the first R#18 = 0 list comes with the palette black, and
     `split_list` + 8 is 9Bh again before the text's first list (V9958).
4. **The HUD.**
   - In an `EXTJOY=1 PZ_TEST=2` build (the timer stands still), the HUD at each still equals a
     stub-stage build's (step 6) at the same pass but in the ammo, the score and the message.
   - **The HUD's rows are not shifted while R#18 ≠ 0**, on the V9938 (C-BIOS_MSX2, Expert) and the
     V9958 (FS-A1FX, HB-F1XDJ, FS-A1GT). A shift is a register's effect, which no VRAM still shows,
     and at s = 0 and 64 R#18 is 0 anyway (c = s). So the check reads the register:
     - a breakpoint at the split's end (`sp_r19`, after its timed writes) reads `debug read "VDP
       regs" 18` in every frame of the `armed` record and of a hold at s = 7 and at s = 8 (shifts −7
       and +8): 0 every time; at the next VBLANK (`iv_late`) the list's value again;
     - the same run with `split_list` + 8 poked back to 9Bh (R#27) by the Tcl must report the shift
       on the three V9958 machines: the check sees the fault it is for.
5. **The display guard** (`rc2_guard`) over the passes, from the first to the last: a HUD split at
   every VBLANK; reg, pal, cmd, cpu, tear and vbl 0.
   - Outside that window by design: `rg_show`'s uploads and builds (the sheets into pages 0-1 and
     the sprite tables are CPU writes the guard counts as cpu wherever they fall, the builds cmd and
     tear into the page on screen) and `rg_hide`'s SAT writes, all with the palette black. Checks 6
     and 7 cover them. (Brainstorm's guard ran over passes 10-633 for the same reason.)
   - Run on the MSX2, the MSX2+ and the turbo R.
6. **VRAM access speed**: `rc2_count_too_fast` (with `z80_freq_locked off`) 0 lost writes in the
   cartridge over `armed` from the power-on to `fr_done`: at 3.58 MHz on C-BIOS_MSX2 and the FS-A1GT,
   at 5.37 MHz on the FS-A1FX and C-BIOS_MSX2+ (C-BIOS_MSX2+'s own init loses 1-2 writes before the
   cartridge starts: `docs/BRAINSTORM.md` 4.6 g).
7. **The restore and the next game** (`timeout`, then the result and a new game, on C-BIOS_MSX2
   and the FS-A1GT):
   - VRAM 10000h-17FFFh equals `build/msx/level1.vram`, page 3 lines 0-87 are the intro's, both
     SATs start with Y = 216;
   - at the new game's frame 50, against a fresh start: page 2, the atlas, the HUD and the mirror
     equal, the sprite tables differing only in colour rows the engine rewrites before use
     (`restorecheck.py --known`);
   - lost counters 0.
8. **50 and 60 Hz, the real timer.** A `PZ_TEST=2` build without a script, the range left alone:
   the time out about 121 s after the set-up (±1 s), then OUT OF TIME. On the Expert (60 Hz),
   C-BIOS_MSX2_EU (50 Hz) and the FS-A1GT.
9. **Previews for the user**: `build/msx/range_*.png`, plain and graded, the Amiga against the
   MSX, both visits.
10. **The pass rate.** The traces compare pass by pass, so a stage that falls behind its 50 Hz
    ticks still passes them while it runs slower than the original against its 2:00. The Tcl reads
    `tick` (the VBLANK count) at every `fr_tick`: over `armed`, `mixed` and `edge`, on C-BIOS_MSX2
    and C-BIOS_MSX2_EU at 3.58 MHz, the steps between passes follow `fs_div`'s pattern exactly
    (50 Hz: every step 1; 60 Hz: four steps of 1 and one of 2 in every 5 passes). A longer step is a
    late pass: logged with its pass number, what the renderer did meanwhile and the pass's T-states.
    Expected: none.

### 4.3 Sound checks

**Offline** (cheaper first):
- the converters' tests: TITM's three outputs and `pzm.bin` byte-identical; FRM's streams last
  5,999 ticks and read back; record 0 is the sine; effect 2's flag; the octave rule;
- `rc2music.py --verify` on FRM: 0 differences;
- mkrom's `pzm_check` on both blobs;
- the Z80 interpreter on the built images: FRM's registers per tick against the streams decoded
  apart, on the four chip sets at 50 and 60 Hz;
- effect 2 on PSG B in both SCC modes, its cut by 3 and 4, a shot refused during 3 and 4, the drums'
  R6;
- `$1822C`'s rule at its edges (every pair, the lower one 1, L − 1, L and L + 1 ticks after);
- the title's and Brainstorm's chip writes as before, write for write.

**In openMSX** (`docs/BRAINSTORM.md` 4.3's method):
- FRM's registers per tick against the streams: the cartridge's SCC, an SCC and an SCC+ in another
  slot, SCC + OPLL, the OPLL alone, the PSG alone, at 50 and 60 Hz, on an MSX2, an MSX2+ and a turbo
  R;
- the tune's 5,999 ticks, then silence;
- tick 0 after the first pass;
- the refusals as `$1822C`'s rule gives them;
- the drives still 0 differ;
- the title after the range against the title after Brainstorm (`titlecmp2.py --unheard`): every
  PSG write identical, only unheard registers differing;
- recordings by pitch against the converters' renders. The bass's 10 low notes play an octave up
  on the SCC.

### 4.4 Regression

| Check | How | Expected |
|---|---|---|
| Level 1's logic | `drive_cov1` and `drive_cov0` on an `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1` build, `tools/tracecmp.py --ram` against `build/emu/trace_cov*_ram.jsonl` | 4,401 frames on C-BIOS_MSX2, 1,400 on the FS-A1FX and the FS-A1GT: 0 differ, after every step |
| Level 1's effects | `LOCKSTEP` builds, the effect starts | write for write as before |
| Brainstorm | the suite's 20 traces (`suite_drives`), its stills and records, its text screens | as at `4a8a61d`: 0 differ, 0 torn, pixel-exact |
| The title | a fresh Gradiente Expert 2.0 from power-on: the title's VRAM, registers and palette, its music (SCC and PSG registers per tick), the game at tick 300 | identical to the base (step 0), but `$B32` (R-seeded) |
| The image | each step's ROM against the previous step's, bank by bank (`romdiff.py`, `relocheck.py`) | data banks 10-87 never change, but bank 45 (`HUD_BANK` + 1, `hud_rt.bin`: the two new messages and PUZL's strings 4 bytes on) at step 4 only; code banks only where the step adds code |
| The flows | the product from power-on (the title, level 1 ended by `drive_end`, the statistics, Brainstorm left to its time out, **the range left to its time out**, OUT OF TIME., the title, fire, a new game), `PZ_TEST=1` and `PZ_TEST=2`, on the Expert, the HB-F1XDJ and the FS-A1GT | the text screens pixel-exact; a HUD split at every VBLANK; the title; a new game |
| The 2 MiB product | the same flow on the `ROM_2M=1` image (Brainstorm's checks stopped at tick 300) | PASS |
| Fresh machine | the product with its title on a power-on 64K machine | the title, its music and level 1's start as the base |
| Set-ups | `make matrix` (`tools/msxmatrix.py`: MSX2, MSX2+, turbo R, 50 Hz, a disk interface first, a slot expander, an FM-PAC, a 2 MiB MegaRAM with an SCC, an SCC+, none) on the product; `--no-title` on the `PZ_TEST` builds | 10 of 10 PASS each |
| Turbo R writes | a write watchpoint on 4000h-7FFFh from `front_bonus`' entry to the new game's tick 100 | 0 writes |
| Bench | the game mode over 600 frames of `drive_cov1`; the puzl mode's `pz_solve1` | byte-identical |
| Option sets | `tools/bstest/variants.sh` (41 sets) | as at `4a8a61d` |
| Losses | `mp_lost`, `atr_lost`, `rd_lost`, `fb_lost` | 0 |
| Unit tests | `make test` | the known 4 failures only |

- **Brainstorm's flow checks change with the flow.**
  - `tools/bstest`'s `suite_flows`, `bonuscheck.py`, `hz6_prod` and the final checks' `np.tcl`,
    `ft.tcl` and `run8f.tcl` expect the title right after Brainstorm's result. The range now comes
    in between.
  - Product flows let the range time out by itself: about 121 s more, fast with `throttle off`.
    `bonuscheck.py` gains the range's intro and OUT OF TIME.
  - Script builds have no time out: a new proc `rc2_fr_timeout` pokes AG `$804C` (DC4Dh) = FFh at
    the range's first `fr_tick`. The range then returns at once with POOR and OUT OF TIME.
  - The title comparison's reference becomes the title after Brainstorm at `4a8a61d` (step 0).

### 4.5 Running the checks

From the repository root; `PY=~/.venvs/msxports/bin/python` (Unicorn) runs the bench. Build
harness and candidate ROMs outside `build/msx`.

**The references** (`build/emu/`, git-ignored):

```sh
$PY -I tools/frngbot.py build/emu/fr_armed --mode armed           # .drive, .joy, .jsonl, .log
$PY -I tools/frngbot.py build/emu/fr_mixed --mode mixed --every-dummy 3
$PY -I tools/frngbot.py build/emu/fr_dummy --mode dummy
$PY -I tools/frngbot.py build/emu/fr_poor --shots 5                # (fair: 11, good: 14)
$PY -I tools/amigaemu.py frng --fframes 3000 --drive build/emu/fr_armed.drive \
    --trace build/emu/fr_armed_ram.jsonl --trace-ram                # (each drive)
$PY -I tools/amigaemu.py frng --level 2 --ram build/ram/level2_full.bin --fframes 3000 \
    --drive build/emu/fr_armed.drive --trace build/emu/fr_armed2_ram.jsonl --trace-ram
```

The hand-made drives (`good_min0`, `timeout`, `late_timeout`, `opp`) add a poke line to a bot drive
(`tools/drivejoy.py` format: line 4), as the bench report's `run_all.sh` does.

**The MSX trace**:

```sh
python3 -I tools/mkrom.py build/msx/level1 OUT/rc2_fr2.rom EXTJOY=1 PZ_TEST=2
```

Then in openMSX (`msx_local_cmd`; braces around paths), at 3.58 MHz:

```
set ::z80_freq 3579545; set throttle off; set ::pause off;
source {<repo>/tools/openmsx_rc2.tcl};
rc2_fr_drive {OUT/rc2_fr2.rom} {OUT/rc2_fr2.labels} {OUT/fr_armed_msx.txt} 3000 0 {<repo>/build/emu/fr_armed.drive}
```

Poll `set ::rc2_trace_done` with short calls until 1, then `set ::rc2_fr_result` and `set
::rc2_fr_rating`. Compare:

```sh
python3 -I tools/frngcmp.py build/emu/fr_armed_ram.jsonl OUT/fr_armed_msx.txt
# 1163 FRNG frames compared (1163 Amiga, 1163 MSX), 143 fields: 0 differ
# result: Amiga (0, 25, 0), MSX (0, 25, 0)
# rating: Amiga 0, MSX 0
```

**Stills**: `save_debuggable VRAM FILE` and RAM C000h-FFFFh, then `python3 -I tools/msxrange.py
render build/extracted/files/FRNG_15.bin RAM.bin OUT --page P --sat SAT.bin --r18 N`, compared with
the page's lines 0-161 and its sprites. The record, still, HUD, restore and flow checks extend
`tools/bstest/` (step 10), and `docs/HARNESS.md` gets their section.

**As built**: `docs/HARNESS.md` 5.18 (the display and the camera: `rgview.tcl`, `rgview.py`,
`rgview.sh`), 5.19 (the whole regression: `regress.sh builds W`, `rgr_chain {W} all {W/all.done}`,
`regress.sh check W B`, the sound's `frsound.tcl` and `frsnd/`) and 5.20 (the test candidates:
`rgc_chain`, `regress.sh cand`).

## 5. Implementation plan

One step at a time, in order, each small enough for one agent. Each ends with its acceptance test
and one review (lean process: no multi-agent audits by default). Work goes on a branch `range`
from `4a8a61d`, one commit per step (source and docs only), merged into main after step 12; steps
13-14 then work on main. No tag, no release, no push: the user's order.

| # | Step | Files | Acceptance |
|---|---|---|---|
| 0 | Baseline | none (records outside the repository) | the product and harness builds of `4a8a61d` rebuilt byte-identical; base records of the title on a fresh Expert, level 1's coverage traces, Brainstorm's 20 traces and the product flow |
| 1 | ByteKiller and FRNG's symbols | `tools/bytekiller.py` (from the reports' `bkdec.py`: `$124A6` transcribed), `tests/test_bytekiller.py`, `analysis/frng_1ea00.sym`, `analysis/ghidra_seeds_frng.tsv` (`tools/ghidra_seeds.py`), `tools/ramimage.py` (a file decrunched by `tools/bytekiller.py` placed at its address: `ramimage.py` copies files as they are, and `FRNG_15` is crunched; the reports built the image with scratch `bkdec.py` and `overlay.py`), `docs/AMIGA_ANALYSIS.md` (the range's ledger entry and its REA image recipe) | FRNG_15 → 170,970 B, checksum 0, sha256 `2ec1d6a4…`; equal to the bench's `$124A6` output; REA applies the seeds on the image `9470791f…` with 0 failed |
| 2 | The bench in the repository | `tools/amigaemu.py` (`frng` mode: the bench report's patch), `tools/frngbot.py` (+ `edge` and `quirk4` modes from the logic report's `scenarios.py`), `tools/frngcmp.py`, `analysis/frng_ram.tsv`, `tools/frngmock.py`, `tools/openmsx_rc2.tcl` (`rc2_fr_*`, the rating via `ac_diff` − `diff_tab`, `rc2_fr_timeout`), `tests/test_frng.py` | the 15 references of 4.1 made, with the tabulated results; replays byte-identical; `--via-8420` equal; `armed2` differs only in `$8051` and the palette pointer; `edge` holds T1 reads; `fxmask_check.py`'s rule on the new drives: no used test reads a byte an effect wrote (3.4); the mock 0 differ; the game and puzl modes byte-identical; the tests pass |
| 3 | The converter | `tools/msxrange.py`, `tests/test_msxrange.py`, `Makefile` | the outputs of 3.11, byte-identical to the gfx prototype's where they overlap; every check passes (the sweep: 0 pixels); `range_hit.bin` equal to the image's bytes |
| 4 | Texts and HUD messages | `tools/msxtext.py` (`txt_rg_*`, `TXT_RG_*`, the renders, `render-result`), `tools/msxhudrt.py` (177, 178), `tests/test_bonus_text.py`, `Makefile` | the call counts 304, 347, 129; `check_bonus` passes; the renders equal the flow report's; level 1's and PUZL's message numbers and bytes unchanged |
| 5 | ROM layout, a stub stage | `tools/mkrom.py` (`STAGES`, the slicing, the blobs, `banks.inc`, `PZ_TEST` 0-2), `msx/rc2.asm` (the FRNG section), `msx/frng.asm` (a stub) | banks 0-87 identical to step 4's build; banks 88-98 as 3.12; mkrom's checks pass for `PZ_TEST` 0-2, `ROM_2M=1`, `DIAG=1` and `2` |
| 6 | The flow, with a stub stage | `msx/front.asm` (`fb_prep`, `front_range`, `front_rgtest`), `msx/rc2.asm` (`fr_done`, `fr_rated`, `pz_test`'s branch), `msx/msx.inc` (`frv_...`, `fr_code`, `rg_...`), `msx/frng.asm` (the entry and exit contract: set-up, HUD, timer, the end checks, no targets) | through the product's flow (an `EXTJOY` build, Brainstorm by `pz_fail`) and `PZ_TEST=2`: the intro, the result for poked counts at each rating, and OUT OF TIME. pixel-exact on the MSX2, the MSX2+ and the turbo R; `ac_diff` right at `fr_rated`; level 1's traces after the new game 0 differ; Brainstorm's 20 traces 0 differ |
| 7 | The stage's logic (display black) | `msx/frng.asm` (every routine of 2.4, `fr_code`, the hit test of 3.4 reading `range_hit.bin`, `snd_rfx` stubbed), `msx/msx.inc` | the 15 drives 0 differ with equal results and ratings on C-BIOS_MSX2 and the FS-A1GT, `armed` also on the FS-A1FX and at 50 Hz; after level 1 and Brainstorm `--skip score` 0 differ; `BANK_FRNG`'s size logged |
| 8 | The display at a fixed camera (s = 32) | `msx/frng.asm` (`rg_show`, `rg_feed`, the composition, the sprites, the fade, `rg_hide`), `msx/msx.inc`, `tools/bstest/` (still and record checks for the range), `docs/HARNESS.md` | 4.2 checks 1-3, 5-7 and 10 at s = 32; the traces still 0 differ |
| 9 | The camera | `msx/frng.asm` (the rule, R#18 in the lists, page rebuilds, the V9958 split byte), `tools/mkrom.py` (`RG_ADJ`, section 6) | 4.2 checks 2-5 and 10 with the camera at s = 0-64, shifts −7 to +8 included, on the V9938 and the V9958 (the HUD unshifted by check 4's register probe, which fails with the split byte poked back); records coherent in scene coordinates; `timeout`'s cut at R#18 ≠ 0; picture rates logged; the traces still 0 differ |
| 10 | Milestone 1 accepted: the harness's flows and the whole suite | `tools/bstest/` (flows through the range, `rc2_fr_timeout`, `bonuscheck.py` for the range's screens), `docs/HARNESS.md` | 4.1, 4.2 and 4.4 PASS on the silent range |
| 11 | Sound | `tools/msxtune.py` (`convert_frm`, effect 2's flag), `tools/msxscc.py` (the octave rule), `tests/test_msxtune.py`, `msx/tune.asm` (`tn_frm`, the PSG-B path), `tools/mkrom.py` (`frm.bin` from `FRM_BANK`, `tune_inc`, `pzm_check` for both), `msx/frng.asm` (the tune's start, `snd_rfx`), `Makefile` | 4.3's offline checks; 104 banks; mkrom's SCC test values pass (bank 9's B800h) |
| 12 | Milestone 2 accepted: the sound in openMSX and the suite again | none, or fixes | 4.3's openMSX checks PASS; 4.1, 4.2 and 4.4 PASS again; merge into main |
| 13 | The test ROMs | outside the repository: the candidates of section 6 and their notes | each built twice to the same bytes; the matrix 10/10 each; the fresh-machine runs; the range ROMs' stills and records from the keyboard; the notes give each file's SHA-256; only the sent files go to `build/msx` |
| 14 | Documentation | this file (as built), `docs/MSX_ARCHITECTURE.md` (the range under Front end and Sound), `docs/AMIGA_ANALYSIS.md`, `docs/ROM_BUDGET.md` (2.x as built), `README.md` (the flow, `PZ_TEST=2`), `docs/HARNESS.md` | `make test` with the known failures only; REA seeds 0 failed; the commit on main |

**As built** (branch `range`, one commit per step; steps 0 and 12 left records outside the
repository and no commit):

| # | Commit |
|---|---|
| 1 | `c241299` (ByteKiller), `b1b355c` (FRNG's symbols, its seed file and REA image, the ledger) |
| 2 | `6de52e8` |
| 3 | `b1008cf` |
| 4 | `073a0ad` |
| 5 | `7451db5` |
| 6 | `4aed67b` |
| 7 | `3c3a735` |
| 8 | `26a2076` |
| 9 | `abe80d9`, `0e1d6ab` (the rates' check) |
| 10 | `4b46bb7` (the harness in the repository, after step 11) |
| 11 | `131797e` (the converter, before step 3), `43569f6` (the ROM) |
| 12 | no fix needed; the milestone's review then found the sound's late stop: `4650771` |
| 13 | `92a7dd4` (the candidates' harness: `rgflow.tcl` `rgc_chain`, `regress.sh cand`, `docs/HARNESS.md` 5.20); the candidates and their notes stay outside the repository |
| 14 | the commit that adds this file, with `docs/MSX_ARCHITECTURE.md`, `docs/AMIGA_ANALYSIS.md`, `docs/ROM_BUDGET.md` and `README.md` |

- If step 11 cannot pass its checks in time, step 13 delivers milestone 1's silent range, and the
  notes say so.
- If `BANK_FRNG` passes 7,500 B at step 7 or 8:
  1. the entry-only data (`fr_code`'s initial image, the line patterns) move to the free space of
     banks 97-98;
  2. if needed, the renderer moves to a second code bank mapped at 8000h while the stage runs
     (the stage then calls no FRONT routine between its entry and its exit: its wait becomes its
     own copy of `fs_tick`; the hit test's reads and `set_weapon`'s call put that bank back at
     8000h instead of `BANK_FRONT`), +1 bank.

## 6. Test builds and candidates

| Option | Default | Effect |
|---|---|---|
| `PZ_TEST=2` | 0 | **new**: power-on without the title → level 1's set-up (`ng_go`) → once, instead of the main loop (`pz_test`): AG `$8050` = `PZ_LEVEL`, `cpu_title`, then `front_rgtest` (`fb_prep`, `front_range`, `jp cpu_title`), the title and a new game. One-shot (`pz_first`), so later games are normal (Brainstorm, then the range) |
| `PZ_TEST=1` | 0 | as before, now Brainstorm **then the range** at power-on |
| `PZ_LEVEL=n` | 1 | the visit for `PZ_TEST`: 1 or 2 |
| `EXTJOY=1` | 0 | the stage reads `ext_joy` (the trace harness); the timer stands still |
| `JOY=...` | none | a script by `tick_n`: the stage's passes continue it |
| `TAG=n` | 0 | "TEST n" at row 10 of every bonus text screen (the range's three too, through `fe_text`); harness builds keep 0 |
| `RG_ADJ=0` | 1 | **new**, the fallback of risks 2 and 3: the range's lists keep R#18 = 0 and the camera moves in 16-pixel steps (the view starts at the page's c; the crosshair stays in view: cx − c ∈ [5, 240]); for a VDP that ignores R#18 or applies it once a frame |

- `PZ_TEST` code exists only in builds that ask for it. The product's flow and bytes do not depend
  on it.
- AG is cleared by `ng_go`: score 0, `$8050` = `PZ_LEVEL`, the bench's starting globals.
- **Harness builds**:
  - `EXTJOY=1 PZ_TEST=2` (`PZ_LEVEL=2` for `armed2`);
  - `EXTJOY=1` (after level 1 and Brainstorm);
  - `EXTJOY=1 PZ_TEST=1` (Brainstorm's drives);
  - the product and `PZ_TEST=2` without a script (the real timer).
- **The candidates (step 13)**, all with `TAG=4`, built outside `build/msx`. Only the files
  actually sent go there.

| File | Options | What it is |
|---|---|---|
| `ROBOCOP2_v0.1.3-test4.ROM` | `TAG=4` | the product, 1 MiB: the title, level 1, the statistics, Brainstorm, **the range**, the title |
| `ROBOCOP2_v0.1.3-test4-range.ROM` | `PZ_TEST=2 TAG=4` | 1 MiB: the range right after the BIOS, then the title and a normal game |
| `ROBOCOP2_v0.1.3-test4-2M.ROM` | `TAG=4 ROM_2M=1` | the product as a 2 MiB image, through the boot guard |
| `ROBOCOP2_v0.1.3-test4-range-2M.ROM` | `PZ_TEST=2 TAG=4 ROM_2M=1` | the range ROM as a 2 MiB image |
| optional: `-test4-range-v2.ROM` | `PZ_TEST=2 PZ_LEVEL=2 TAG=4` | visit 2's palette |
| optional: `-test4-range-noSCC.ROM`, `-PSG.ROM` | `NO_SCC=1` / `NO_SCC=1 NO_FM=1` | the sound versions the user's machines never pick (they find the Pico+'s SCC) |
| optional: `-test4-range-noadj.ROM` | `PZ_TEST=2 TAG=4 RG_ADJ=0` | the camera without R#18 (16-px steps), checked like the others; for the SX-2 if its HUD moves with the camera or the picture does not follow the crosshair smoothly (risk 3) |

- The notes go with the files, not into the repository. They give:
  - each file's SHA-256;
  - what is new;
  - how to reach each ending: shoot 25 times, or wait 2:00;
  - the known limits: the camera hides 64 px; the original's display details are inferred;
  - the minimum hardware: a 2 MiB Konami SCC device for the complete game; these test images are
    1 MiB, or 2 MiB twins.
- **As built** (step 13, 2026-10-28, from `4650771`): the four, `-range-noadj` and `-range-v2`, each
  built twice to the same bytes; the `noSCC` and `PSG` variants were not built (the regression's
  sound family runs those chip sets). Their checks: `docs/HARNESS.md` 5.20. The files, their notes
  (`ROBOCOP2_v0.1.3-test4-NOTES.txt`: the SHA-256s, what is new, the endings, the defaults to look
  at and listen to, the known limits, the SX-2's slot 1 and `-range-noadj`, the minimum hardware)
  and a few screenshots stay outside the repository until the user takes them.

## 7. Defaults chosen while the user is away

| # | Question | Default | Alternative | Why |
|---|---|---|---|---|
| 1 | Pass rate | 50 a second at 50 and 60 Hz | one per VBLANK (60 at 60 Hz) | decision 7's PAL design rule; Brainstorm and the texts do it |
| 2 | Where the range hooks in | inside `front_bonus`, after Brainstorm's result | a third `front_call` in `ml_ev` | no fixed-area bytes; Brainstorm unchanged |
| 3 | PIC2 / PIC6 | dropped | — | decision 5 (binding) |
| 4 | The intro's 35-character line | split after "CALIBRATION" over rows 5-6, the last line to row 8 | rows 5 and 7, the last line at row 9 | Brainstorm's rule; the same 304 calls |
| 5 | The time-out text | Brainstorm's `txt_bs_time` reused | a copy | the original shares `$11698` |
| 6 | `$8060` | `ac_diff` = `diff_tab` + 24 − 8r; level 1 unchanged; the SHARP set moves to `ng_go` with level 2 | a rating byte that `obj_start` turns into the pointer; or `obj_start` guarded by `$8050` = 0 | the existing pointer; 0 bytes in level 1 |
| 7 | Banks | `BANK_FRNG` after `pzm.bin` (88); no Brainstorm bank moves | the stage code contiguous (`BANK_FRNG` = 79, Brainstorm's data one bank up) | the bank-for-bank regression stays exact |
| 8 | Test option | `PZ_TEST=2`, one-shot | a separate `RG_TEST`/`FR_TEST` | one hook, one flag, one option check |
| 9 | The rating in the trace | the word at `ac_diff` − `diff_tab` | the port also writes AG `$8060` (~10 B) | no bytes; no port code reads AG `$8060` |
| 10 | The counts' handover | AM `$B04`/`$B06`, AG `$804C` | registers | as the original |
| 11 | End breakpoints | `fr_done`, `fr_rated` (fixed `ret`s, 2 B) | reuse `pz_done` | the harness tells the stages apart |
| 12 | Turbo R | the range on the Z80 | the R800 | the OPLL needs the Z80; Brainstorm's default 2 |
| 13 | 320 → 256 | a camera over the 1:1 street, the middle-band rule, s from 32 | a static relayout with the stage's x in MSX coordinates (whole street at once; not trace-identical); or a centred camera | 1:1 art, nothing cut, the logic untouched. **The user's eye**: 64 px are off-view at any time |
| 14 | Camera engine | R#18 + 16-pixel page rebuilds on every VDP, the V9958 split byte | an R#26/R#27 ring on the V9958 (smooth, 248-pixel view) as a second path | one code path; level 1's V9938 method |
| 15 | During a camera rebuild | the shown page holds (coherent) | move the shown page's R#18 and SAT within its window meanwhile | zero-glitch first; to judge on recordings |
| 16 | Rows | Amiga rows 0-9 dropped | — | sky and roof tops only |
| 17 | The crosshair's vertical line | through the hit column, bitplane x `$B9A` − 111 | the Amiga's inferred offset after an emulator check: 2 px left (the gfx report) or 10 px left (the logic report, with BPLCON1 `$FF`) | what you see is what you hit; the two inferences disagree |
| 18 | Fire-box sides above line `$20` | hidden, as inferred | always drawn | **I**: sprite DMA starts at line `$20` |
| 19 | The original's 1-frame row gaps | composed correctly | reproduced | zero-glitch rule |
| 20 | Palette | 9-bit rounding, one map, index 1 the sheets' black, 14 free | lift visit 2's darkest greys with index 14 | the k-means found nothing better |
| 21 | Visit 2's palette | the plain rounding (several colours become black) | lifted (20) | **the user's eye**, on `range_2` previews |
| 22 | Grade | graded (game play) | plain | decision 8 |
| 23 | Graphics storage | raw, 8 banks | ZX0, about 3 banks, once a decompressor exists | no decompressor to write; 1 MiB holds |
| 24 | Page 3 lines 88-161 | sheet space, freed by `fb_init` | keep them and lose the double buffer | the sheets need the room |
| 25 | Music tempo | 50 ticks a second (2:00 exactly) | 48, the NTSC release's 4-of-5 divider (~12 B) | the port's tempo for every tune |
| 26 | Effect 2 with an SCC | its noise on PSG voice B at the SCC music's scale | PSG C with the drums muted 6 ticks a shot; or the PSG-alone stream on B (6-9 dB too loud) | B is idle in both SCC modes. **The user's ear**: with the SCC alone, B shares R6 with the drums on C |
| 27 | Bass notes below the SCC's range | an octave up | clamped at 27.3 Hz, 147 cents sharp | the pitch class kept; TITM and PZM unchanged |
| 28 | A shot and a hit sound in one pass | the higher stays (`snd_bfx`'s rule) | a two-entry queue in `tn_go` (~15 B) | one tick of difference |
| 29 | Tick 0 | the first tick after the first pass (`tn_hold`) | two passes, as FRNG's skipped first tick | `tune.asm` unchanged |
| 30 | `frm.bin`'s size | 5 banks at the title's quality | 4 banks with a coarser OPLL | the 2 MiB budget has room |
| 31 | Drums | SNAZ as SD, TOM1 as tom | by ear | the converters' classes |
| 32 | Effect 5 | not converted | converted (~51 B) | never requested |
| 33 | The hit buffer | computed exactly from a recent-blit list and the masks in ROM | a full 896-byte shadow (too slow); or row h never hit (not exact) | trace identity at Z80 speed |
| 34 | The dissolves' masks | not stored: no used test reads them (3.4) | stored (+6,400 B) | V on the 22 bench traces; the pass order in general; step 2 checks the new drives |
| 35 | Random word `$B0C` | left out | a dummy | nothing reads it |
| 36 | Quirks T1-T10 | kept | — | the original's logic, trace-identical |
| 37 | Script builds | the timer still; drives end by 25 shots or a `$804C` poke | a harness poke of the ammo | the bench raises no CIA-B by default |
| 38 | `fr_code` | one 526-byte block in the mirror rule | a label per field | the bench's compare reads it as one block |

Inferences the defaults rest on:
- one pass per frame on a real Amiga;
- the vertical line's and the box sides' bitplane x;
- the fire-box sides hidden above line `$20`;
- the composer's tempo of 50 ticks a second;
- the drum classes;
- the dissolves' masks never read by a used test beyond the 22 traces checked (step 2 checks the
  new drives).

## 8. Risks and open issues

| # | Item | Mitigation or status |
|---|---|---|
| 1 | **The HUD under R#18 on a V9958**: the V9958 split list does not reset R#18 | the split byte (3.3); 4.2 check 4's register probe on three V9958 machines, with its negative control (the byte poked back must fail); the display guard |
| 2 | **The split's timing with R#18 ≠ 0 on a V9958** is proven on the V9938 only (level 1's V9938 engine) | the display guard and 4.2 check 4's probe at shifts −7 and +8 (not s = 0 or 64, where R#18 is 0) on the FS-A1FX, HB-F1XDJ and FS-A1GT. Fallback: `RG_ADJ=0`, rebuild-only camera steps of 16 px (R#18 = 0 always: section 6) |
| 3 | **A device that ignores R#18, or applies it only once a frame** (e.g. an FPGA VDP: the user's SX-2 has never run a split with R#18 ≠ 0, since level 1 scrolls with R#26/R#27 there) | ignored: the picture and the sprites still agree (both in page coordinates) and the camera steps 16 px at a time. Once a frame: the HUD would move with the camera by up to 8 px. Not checkable here; the optional `-range-noadj` candidate (`RG_ADJ=0`) goes with the others so that the user's SX-2 can compare |
| 4 | **VDP time**: the riser (~12 pictures a second) and camera pans (~7); **CPU time** per pass (logic, hit test, renderer bookkeeping, SAT, HUD, the music's VBLANK tick) not measured yet | VDP: measured at step 9. CPU: 4.2 check 10 (no late pass) from step 8 on. Later: the V9958 ring path (default 14) |
| 5 | **`BANK_FRNG` overflow** (the budget estimated 7.0-10.4 KiB) | the plan of section 5: entry-only data to banks 97-98, then a second code bank at 8000h |
| 6 | **The hit test's exactness** (T1, the recent-blit list) | the model first (step 2), then the 15 drives; `edge` holds T1 reads |
| 7 | **SCC test values**: bank 90 now holds graphics; bank 9's B800h moves with `tune.asm` | mkrom's check at every build; reorder or pad |
| 8 | **Brainstorm's flow checks** expect the title after its result | step 10 updates them (4.4) |
| 9 | **Script builds never time out** | `rc2_fr_timeout`, or drives that fire 25 shots |
| 10 | **Level 2 must move the SHARP set to `ng_go`**, or it loses the rating | in level 2's plan (3.10) |
| 11 | **The camera hides 64 px** that the Amiga shows (about 9 % of spawns at positions 0 and 6, the near walkers) | the user's eye (default 13); the relayout alternative needs a deviation from trace identity |
| 12 | **Visit 2's palette** is very dark after rounding | the user's eye (default 21) |
| 13 | **Effect 2 on PSG B** shares R6 with the PSG drums (SCC alone) | the user's ear (default 26) |
| 14 | **The time-out cut** with R#18 ≠ 0 | `rg_hide`: the palette black before the R#18 = 0 list; 4.2 check 3 on the `timeout` drive, whose poke lands where R#18 ≠ 0 (4.1) |
| 15 | **Page 3 lines 88-161** must be freed before any field use | `fe_text`'s and `engines_init`'s `fb_init`; 4.2 check 7 |
| 16 | **The fixed area** (190 B free; 160 in `PZ_TEST` builds) | +2 B (+~6 in `PZ_TEST=2` builds); the option sets build |
| 17 | **Turbo R**: no write to 4000h-7FFFh after the RAM copy | the watchpoint check (4.4) |
| 18 | **The 2 MiB product through the bonus stages** was not run before | 4.4 runs it |
| 19 | **Real hardware is unverified** until the user is back: openMSX's VDP and command timing against a real V9938, V9958 or an FPGA | everything that can run in openMSX does; waits by interrupt, never by polling S#1 (`docs/BRAINSTORM.md`, the Hotbit's FH misses) |
| 20 | **Level 1 at 5.37 MHz** loses VRAM writes (known, the user's call) | unchanged; the range itself must lose none (4.2 check 6) |
| 21 | **The turbo R's 0.1 s HUD blank** before Brainstorm's intro | unchanged (Brainstorm's default 2, the user's call) |
| 22 | **Headless runs**: at most 2 openMSX, no `exit` or `vwait` in callbacks, files opened once | kept |

## 9. Sources

`$RS` = this workflow's scratch folder (temporary: the reports are not in the repository; their
facts that the port uses are in sections 2 and 10, in `docs/AMIGA_ANALYSIS.md` and in the tools'
docstrings),
`/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space/range`
(not in the repository, and temporary):

| Report | Spec | What it holds |
|---|---|---|
| flow | `$RS/flow/FLOW.md` | the callers, `$8420`, the texts, the rating bench (5,043 cases), `front_range`'s sketch (`asm/front_range.asm`), the text prototype (`scripts/rgtext.py`, `text/`), `$8060` in the port, RAM and free space |
| logic | `$RS/logic/LOGIC.md` | FRNG routine by routine, the state, the tables, the timelines, the quirks, the hardware models, the trace fields; `frng_1ea00.sym`, `rea/frng_listing.txt`, `tables/`, the bench (`scripts/frngbench.py`) and the executable model (`scripts/frngmodel.py`: 22 traces, 0 differences) |
| gfx | `$RS/gfx/GFX.md` | the screen read from the code, the layout and camera, the palette, the VRAM map, the composition and its model checks, the converter prototype (`scripts/msxrange.py`), the previews |
| sound | `$RS/sound/SOUND.md` | FRM = MU1's player, the calls, what is heard, the corrected extraction, the sizes, the player additions, the interpreter runs and costs |
| bench | `$RS/bench/BENCH.md` | the `frng` mode (`amigaemu_frng.diff`), the bot and the nine drives, the Tcl procs, `frngcmp.py`, the field map, the mocked MSX pipeline |
| this plan | `$RS/design/fxmask_check.py`, `fxmask_check.txt` | the logic model instrumented to name the last writer of every byte a hit test reads (3.4): 22 traces, 0 rows differing from the bench, no used test reading an effect's bytes |

All Amiga facts in section 2 come from REA (Ghidra provider) listings and byte reads in those
reports, on the level-1 RAM image with FRNG decrunched at `$1EA00` (sha256 `9470791f…5f3d91a`), and
from bench runs of the original code. The divider and end checks of `$1EA40-$1EAFA` were read again
in the logic report's REA listing for this plan. MSX facts cite the source at `4a8a61d`.

## 10. Where the area reports disagreed, and what this plan takes

| Item | Report | This plan, and why |
|---|---|---|
| Music tick rate | gfx: 5 passes of 6 | **4 of 5** [V: REA listing `$1EA76-$1EA90`: `subq` / `beq` skip / `bpl` tick / else 4 and tick; `$1EB30` starts at 1; the logic, sound and bench reports] |
| After "TIME OUT." | gfx: the stage runs 99 more passes | **returns at once** [V: `$1EAF2-$1EAFA` `jmp $8008`; the bench's `timeout` returns at frame 301] |
| FRM's stop entry | gfx: "stop `$2022C`" | `$2022C` is the effect entry; stop all is `$20194` (`$20004`), which FRNG never calls [V: sound] |
| Script table | gfx: 41 entries, "26 pop-up stubs" | 42 entries (`$1EF88-$1F0D7`); 27 pop-up scripts through 23 stubs to 22 descriptors [V: logic] |
| The random word | gfx: "the bench must model it" | nothing reads `$B0C`; left out [V: REA xrefs] |
| The vertical line's x | gfx: `$B9A` − 113 (H − 128); logic: 10 px left with BPLCON1 `$FF` | through the hit column `$B9A` − 111 (D, default 17); both inferences kept for an emulator check |
| The HUD under R#18 | gfx: "the split resets R#18" | true of the V9938 list only (`isr.asm:606`); the split byte on a V9958 (3.3) |
| Code bank | flow: `STAGES` contiguous, `BANK_FRNG` = 79 | after `pzm.bin`, 88: no Brainstorm bank moves (sound's preference; default 7) |
| Test option | flow: `PZ_TEST=2`; bench: `FR_TEST=1` | `PZ_TEST=2` (default 8) |
| The rating in the trace | bench: AG `$8060`'s low word − `hp_sharp` | `ac_diff` − `diff_tab`, as flow's default; the Tcl reads the two labels (default 9) |
| Breakpoint names | flow: `rg_done`; bench: `fr_done`, `fr_rated` | `fr_done`, `fr_rated` (fixed); `rg_` for the stage's code (`rg_stage`) |
| The hit test's data | nobody sized it | `range_hit.bin`, 11,776 B, 2 banks (3.4); the effects' masks left out after an instrumented model run (V on 22 traces) |
| FRM's effect sizes | ROM budget 3.6: PSG 111, SCC 180 B | 74 + 90 B: the budget's model read the wrong record 0 [V: sound] |
| The music divider in the trace | logic: compared | left out: the port ticks the music from the VBLANK (bench) |
| Bank count | flow ~105, gfx 102-103 | 104: the graphics 8, the hit data 2, the music 5, the code 1 |

## 11. As built: where the build departs from the plan, and what it measured

Each departure below is the plan's default or the safest choice where the plan said nothing; the
implementation's handoff log (scratch) recorded them step by step.

**Flow and texts** (steps 4 and 6)
- The intro's split lines sit on rows 5-6, the last line on row 8 (default 4); the original's call
  counts are kept (304, 347 and 129 for the intro, the result and the time out).
- `fr_done` and `fr_rated` sit before the fixed tables, not at the code's end: no table moved, and
  every routine after them keeps its address.
- The HUD's messages 177 ("NO AMMO.") and 178 ("TIME OUT."): the HUD data grows by 23 B to 15,960
  B, 424 B free in its bank.

**Logic** (step 7)
- The dead tests are skipped: the original tests every draw after a shot; the port skips the
  erases' and the dissolves' own tests (their `$B0B` is never read, and the trace leaves `$B0B`
  out). The plan's "at most 3 calls in a pass after a shot" assumed it.
- `rg_init`, `rg_show` and the tune's start come before `rg_timer`: the real timer's time out falls
  at pass 6,050 (6,048 otherwise), and the entry's uploads (about 0.5 s) are not stage time.
- The bench's `dummy` drive uses `--shots 12` (in dummy mode the bot found only 19 dummy shots in
  3,000 passes); `fr_armed2.drive` is a copy of `fr_armed.drive`.

**Display** (steps 3, 8 and 9)
- Display quirk 4 (2.8) was found by the converter's model of the original; the port does not
  reproduce it (`tools/msxrange.py`'s model has a `quirk4` switch, and its sweep checks every pixel
  the quirk changes).
- Both pages' shown states are built at the entry and set to the scene at c = 32 (the plan: unset),
  so the first passes need no whole-page rebuild.
- The front layer is drawn over the pop-up's own part of its position; the converter's model draws
  it over the whole position: index 1 against 0, both black.
- The fade writes `pf_pal` in the pass, as Brainstorm's does: during the fades the palette leads the
  picture by the page's latency (1 to 5 passes).
- `rg_feed` works in bounded steps: a build's whole preparation in one call (up to 36k T-states)
  gave 20 late passes at 60 Hz.
- Pans and the riser: a whole-page rebuild (about 6 passes of VDP time) holds the page on screen,
  and the elements then jump several passes. Measured on the V9938: the riser 5-13 pictures a second
  over whole drives (16-17 in the candidates' records near the end), pans 10-13 (the plan estimated
  7). Default 15's alternative (moving the shown page's R#18 meanwhile) is not built.
- `rg_hide` publishes FRONT's `fs_list` (page 0, R#18 = 0, no sprites) under the black palette;
  `fe_text` publishes the same list next.
- The box's sides are hidden above row −2 (default 18) and the line drawn at `$B9A` − 111 (default
  17) in the converter's previews and model too (its prototype drew the line at − 113).

**Sound** (step 11 and the milestone's review)
- The octave rule is FRM's only (`scc_version(gt, octave_up=True)`, called by `convert_frm` alone):
  TITM and PZM keep the clamp's code path. FRM's 10 raised notes take N 2229 (−0.37 cents).
- `frm.bin` is 39,341 B, as planned; SCC voice 2 is 5,612 B (8 less: the raised notes share N 2229
  with the bass's own notes an octave up), and effect 4's SCC stream plays volume 3 (the sound
  report's measurement: 2; effects 3 and 4 have the same Amiga level).
- The tune starts after `rg_show`, before `rg_timer`, not at `$1EA32`'s place after the crosshair's
  set-up: `tn_start` waits for a VBLANK, which there would move the real timer's time out. Tick 0
  still comes after the first pass (default 29).
- **The stop.** The plan had no `snd_stop` in the stage (3.1, 3.7: `fe_text`'s). The milestone's
  review found that on the NO AMMO end `rg_hide`'s waits and its page-2 restore (`tiles_upload`,
  32 KiB) let the VBLANK tick the tune about 13 more times (0.25 s) over the black screen, where
  the original stops it within microseconds of FRNG's return (2.9). `rg_end` now calls `snd_stop`
  before `rg_hide` on both ends (`4650771`). `tools/bstest/frsound.tcl` logs that stop (its Q line),
  and `frsnd/frregcmp.py` checks it: at most one tick between the last pass and the stop (0 in all
  20 logs), none after it, the chips silent at `fr_done`; the logs of the build before the fix
  fail it.
- Open: with an OPLL (modes 5 and 6) the tune's last snare (tick 5,985) releases after the tune's
  end, and openMSX's YM2413 holds its envelope floor (a 98 Hz tone about 40 dB under the tune's
  loudest tick) until the stage's stop, about 1 s later on a time out. Not changed: a fix in
  `tune.asm` would add OPLL writes to Brainstorm's end too; an FRM-only rule or a converter change
  would do. For the user's ear.

**Harness and process** (steps 1, 10 and 13)
- REA applied FRNG's seeds (0 failed) through the REA CLI, with the same Ghidra and parameters: the
  MCP server pins the main seed file, and loading FRNG's needs a configuration change (the user's
  call).
- The reports disagreed on where FRNG's graphics end: `docs/AMIGA_ANALYSIS.md` takes `$2CC62-$3E061`
  (the last dissolve frame starts at `$3CFE2`).
- The whole regression lives in `tools/bstest/` (`regress.sh`, `regress.tcl`, `rgflow.tcl`,
  `frsound.tcl`, `frsnd/`, `rgcheck.py`, `cmpcheck.py`; `docs/HARNESS.md` 5.19), and Brainstorm's
  flows go through the range. The candidates' checks: `rgflow.tcl` `rgc_chain` and `regress.sh
  cand` (`docs/HARNESS.md` 5.20).
- All 15 steps ran on the branch `range` (the plan: steps 13-14 on main after a merge at step 12);
  the branch is merged after step 14.

**Sizes and results**
- `BANK_FRNG`: 7,492 B (`frng_end` BD44h; the soft budget 7,500 B, 700 B to the bank's end). The
  image: 104 of 128 banks (the range's code in 88, its graphics in 89-96, its hit data in 97-98, its
  music in 99-103); `ROM_2M=1` pads the same to 256.
- The whole regression after `4650771` (`regress.sh check`, 2026-10-28): 45 verdicts PASS. Level
  1's traces 0 differ, the title from power-on identical to `4a8a61d`'s, Brainstorm's 20 traces 0
  differ with its screens and records as at the base; the range's 15 drives 0 differ on C-BIOS_MSX2
  and the FS-A1GT (79 traces in all, also after a played level 1 and Brainstorm), the wanted state
  at every pass, 695 stills, the records (0 torn, 0 SAT and 0 coherence errors), the HUD's register
  probe on the V9958, 0 late passes, the sound's 20 register logs 0 differences; the lost counters 0
  in all 58 notes. `make test`: the 4 known failures only.
- The test candidates `ROBOCOP2_v0.1.3-test4*` (section 6): `regress.sh cand` PASS (the products'
  title from power-on, the product from the keyboard on an MSX2, an MSX2+ and a turbo R, the range
  candidates from the keyboard with stills and records, the real 2:00), and `tools/msxmatrix.py` 10
  of 10 on each of the six files.

### 11.1 The V9958's ring (2026-10-28, after the user's test of test4)

The user found the range laggy while the camera pans, even on a turbo R: on every VDP a page whose
c changed was built again whole (about 6 passes with the page on screen held, then a jump of up to
10 passes). On a V9958 (RG_ADJ builds, the V9958's split list: `hud_msk`) the display now uses the
chip's horizontal scroll instead (`msx/frngview.asm` `rgr_ring`):

- each page is a ring: Amiga column x at page column x & 255, holding the 256 columns c..c + 255
  (c even, 0-64); the list shows column s at screen x 8 by R#26/R#27 (X = s - 8, one page, level
  1's rule of `msx/scroll9958.asm`), MSK hides x 0-7, R#18 stays 0, and the split's own R#27 = 0
  (split_list + 8 keeps 9Bh) resets the scroll for the HUD;
- the view is the 248 columns s..s + 247, so `rg_cam`'s band ends 8 columns sooner and s goes up to
  72 (every column 0-319 still comes into view; `tools/msxrange.py` `camera_ring`);
- a page keeps its c while s stays in c..c + 8; else its build moves c by d and draws only the d
  columns that come in (`rvb_ring`): the elements keep their columns (their x relative to c moves
  by -d, cut to the page), every group is made again and compared with them, and a command that
  passes column 255 is sent in two parts (`rv_ring`, `rv_ring2`);
- the sprites (the crosshair's line, the box's sides) are placed at their screen x (x - (s - 8)):
  R#26/R#27 move the bitmap, not the sprites.

Measured in openMSX (`tools/bstest/rgview.sh`, all 11 sections PASS; `rgview.py` and `rgview.tcl`
model the ring: the page un-rotated by c, the picture as shown with MSK, the ring's camera, the
HUD probe on R#18, R#27 and MSK at the split's end, its negative control at s = 7):

| | Pictures a second while panning (armed, mixed, timeout) | Holds of 7-10 passes (armed) |
|---|---|---|
| V9938 (R#18, unchanged) | 12.2, 10.7, 12.9 | 35 |
| V9958 (the ring: FS-A1FX, FS-A1GT) | 17.2-17.3, 15.7-16.2, 16.3-18.0 | 3 |

The V9938 keeps R#18 and its whole-page builds: it has no horizontal scroll register. Only bank 88
(`BANK_FRNG`, now 7,899 B) differs from test4's product; the logic's traces are unchanged.

### 11.2 The V9938's camera in 16-column steps (2026-10-28)

The V9938 has no horizontal scroll register, so a page whose c changes must have its 20 KB moved
again: about 90 ms a page with the VDP's own commands, whether the page is built from the clean
scene (the plan's way), moved within itself, or copied from the page on screen with the elements'
changes on top (both tried: every check passed, the holds stayed at 8-10 passes; the experiment is
kept outside the repository, build/archive/range_v9938_copy_experiment_2026-10-28.patch). The user
tried test4's `-range-noadj` ROM on the MSX2 and chose its camera for the V9938: `rg_cam` now
applies the RG_ADJ=0 rule at run time whenever the pages are not a V9958's ring (`rgr_ring` 0):
s a multiple of 16 that moves only when the crosshair's line would leave cx - s in 5..240
(`msxrange.camera_steps`), so the view stands still and steps 16 columns near the edges. A V9958
keeps 11.1's ring. `RG_ADJ=0` builds still use the steps on every VDP.

Measured in openMSX (`tools/bstest/rgview.sh`: all 11 sections PASS): on C-BIOS_MSX2 the holds of
7-10 passes went from 35 to 13 (armed) and from about 35 to 9 (mixed), the camera moving in 9
spans of armed's 1,163 passes instead of 15. The V9958's numbers are 11.1's. Only bank 88 differs
from test5's product.
