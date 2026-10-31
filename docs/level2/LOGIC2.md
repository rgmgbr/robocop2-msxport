# Level 2's objects and game logic: a routine-by-routine spec for the Z80 port

Area "logic" of the level-2 plan, 2026-10-27. Base: the repository at `781005e` (branch `range`), read
only. Nothing here was run in an emulator.

Tags:
- **V**: verified by REA (6.7.0, Ghidra provider 12.1.4, raw-binary m68k, entry 0x0) on
  `build/ram/level2_full.bin` (sha256 `a039a158…0a88b09`), seeds `analysis/ghidra_seeds.tsv`; or by the
  MSX source at `781005e`; or by the image's bytes decoded by the scripts below (data only).
- **I**: inferred, not confirmed by a run.
- **D**: a design decision proposed for the port (section 13 lists each with its alternative).
- **E**: an estimate.

Files in this folder (`$L2 = …/scratchpad/space/l2/logic`):

| File | What |
|---|---|
| `LOGIC2.md` | this spec |
| `level2.sym` | the names (routines, variables, data ranges), in `analysis/*.sym` format |
| `level2_new.lst` | REA instruction listings of every new routine (590 instructions) |
| `rea/asm/*.json`, `rea/asmx*/*.json` | the REA CLI dumps (69 procedures); `rea/dump.sh`, `rea/compact.py`; `rea/l2seeds.tsv` (the project seeds + `$C91A`, `$D1CA`, `$D1D0`, `$D1DE`) |
| `tables/*.txt` | the level-2 data decoded: headers, spawn list, object list, markers, hazards, specials, descriptors, hit points, enemy bullets, the new types' tables |
| `scripts/img.py`, `lists.py`, `objlist.py` | the decoders (read the image only; `python3 -I scripts/lists.py`) |

## 1. Summary

- **Where the level lives [V].** Level 2's lists are in the main code (identical in every level image),
  not in DATAL2: header `$868C`, spawn list `$97B0` (40 entries), object list `$A828` (44), marker table
  `$C5EC` (9), hazards `$95B2` (7), special objects `$8FE0` (9 records `$9088-$911D`). DATAL2 holds the
  tiles, the map (`$38000`, 160 × 50) and level 2's BOB graphics (`$3BE80-$41D57`); MADEX (`$45250`) holds
  more BOB graphics (the hostage's and the explosions' addresses fall there: section 6).
- **Object types [V].** Spawn list: 1, 2, 4, 5, 6, 12, 13, 14, 45, 49. Markers: 3, 4, 12, 13, 14, 15,
  16, 30, 31. No level-2 type spawns another type (type 38's launches come only from level-3 types).
  New handlers: **1, 2 (+ its tail `$C91A`), 5, 6 (+ `$D1CA-$D1E1`), 14, 16, 49 (+ obj38's flight
  `$E728-$E7B1`)** and the death `$C33E`. Already ported (level 1): 3, 4, 12, 13, 15, 30, 31, 45 and the
  deaths `$C1FA`, `$C1FC`, `$C2D8`, `$C2EE`, `$C31E`, `$C35A`.
- **Level code [V].** New: the trolley `$8F02` (4 records), the vats `$91BC` (7 records), `act_0c`
  `$9EE8` (4 map objects). Shared and ported: the lifts `$8DE6` (5 records; level 2 takes the level-1 BOB
  path), the floor switch `$9F84` (16), explode-look-4 `$9EA4` (15), the relocation `$9FC4` (1, to
  (192, 112)), plain looks `$9C76` (7).
- **The level's end [V].** Touching type 2 (the armed enemy, ROM_BUDGET's "Cain") runs its tail
  `$C91A`: "ARREST SUCESSFUL.", sound 21h, `$16D0` set, `$16C4` = 40h; `main_loop` then counts 65 frames of
  100 points and fades out, `$8050` + 1, `load_level2` `$8524`. The messages naming Cain are level 3's
  (`$C25C`, `$D49C`). REA's xrefs of `$16D0` miss `$C936`: `$C91A` is reached only through `pea` at `$C90A`.
- **Size [E].** About 1,450 bytes of new 68000 code in the level bank (× 1.43, level 1's measured ratio:
  ~2.1 KiB of Z80), 190 in `special.asm` (~0.25 KiB), 140 in `mapobj.asm` (~0.2-0.3 KiB); the level-1
  handlers level 2 shares (1,194 Z80 bytes measured) and the spawn-walk shortcuts (664) copied into the
  level-2 bank; ~2.0 KiB of tables. **BANK_L2: ~6.6 KiB of 8.** LC1 has 39 bytes free: nothing new goes
  there (net −11 bytes).
- **CPU [E].** A busy level-2 tick ~45,000-55,000 Z80 T-states, below level 1's measured 74,000, **if**
  the vats do not rewrite their 604 cells through the map patches (that alone would add ~24,000 T a tick
  on average and overflow both patch pools). Section 11.
- **What the logic asks of the display [V/D].** The vats' animated cells (up to 108 visible cells change
  every odd tick), RoboCop's sprite cut at the vat's surface line, the armed enemy outside the MSX's
  256-px view when the camera is pinned at x 0, and four more play-field BOBs that move every tick
  (the trolleys). Section 12.

## 2. Level 2's data [V]

### 2.1 The header (`level_init` `$871A` reads `$8664` + 40 × level)

`$868C`: object list `$A828`, hazards `$95B2`, specials `$8FE0`, spawn list `$97B0`, start x/y and camera
(160h, 310h) = (352, 784), relocation (C0h, 70h) = (192, 112), marker table `$C5EC`, lowest camera 270h,
timer `$0730` (07:30), spawn delay 2Eh, marker mask 7, palette `$10036` (level 3's too).
`tables/level_headers.txt`. `level_init` has no other level-2 case (the `$8050` = 2 tests at `$88AC`
and `$8EB0` are level 3's); REA xrefs of `$8050`: `$122`, `$81B8`, `$83B8`, `$873A`, `$876C`, `$88AC`,
`$8EB0`, `$91A4`, `$FFC4` — no object handler reads the level number.

### 2.2 Spawn list `$97B0` (`tables/spawn_l2.txt`)

40 entries of 14 bytes (x, y, type byte +4, flags +7, reload +8, count +10, spawned +12), end `$99E0`.

| Entries | Type | Where | Flags, reload |
|---|---|---|---|
| 0-9 | 45 hostage | ids (y & 15) 0-9 | 40h (once), 999 |
| 10, 11 | 1 walker | (384, 664), (672, 424) | C0h (once, at the screen's edge), 300 |
| 12-17 | 49 drone | y 16, x 1504-2416 | 0, 60-190 |
| 18-26 | 5 drip | y 368, x 772-2196 | 0, 45-64 |
| 27 | 6 barrel | (416, 448) | 0, 40 |
| 28 | 2 armed enemy | (384, 56) | 40h, 32767 |
| 29 | 14 grenadier | (320, 77) | 40h |
| 30-39 | 4, 12, 13 ×10 | y 12-59, x 272-2476 (the top corridor) | 40h / 60h, 32767 |

Flag bit 5 (60h) is read by nothing in `update_objects` (I: no other reader).

### 2.3 Marker table `$C5EC` (`tables/markers_l2.txt`)

[bands, type, y offset]: (2, 3, 53), (7, 4, 69), (1, 12, 62), (1, 13, 65), (6, 14, 50), (7, 15, 56),
(7, 16, 56), (7, 30, 51), (7, 31, 67). Spawns at floor cells (attribute bit 3) at the view's edges,
every 8 frames (mask 7) once the delay (2Eh, + 5Ah per death of an enemy) has run out.

### 2.4 Object list `$A828` (`tables/objlist_l2.txt`, `tables/objtypes.txt`)

44 entries of 12 bytes. Activators through the BRA table at `$9EC4` (offset → target): 0 `$9C76`,
4 `$9F84`, 8 `$9EA4`, 0Ch `$9EE8`, 10h `$9FC4`, 14h `$A038`, 18h `$A03E`, 1Ch `$A0D4`, 20h `$9F74`.

| Map type | Entries | Activator | Size | Looks | Pickups |
|---|---|---|---|---|---|
| 0 | 5-9 | `$9C76` (a shootable slot) | 3×3 | 4 + gone | 4, 8, 12, 16, 24 |
| 1 | 10, 11 | `$9C76` | 2×1 | 2 + gone | 28, 28 |
| 2, 4-8, 10, 11 | 28-43 (15) | `$9EA4` | 2×2 | `$A3AE`, `$A3B6`, gone | 4-32 |
| 3 | 12-27 (16) | `$9F84` floor switch | 4×2 | 4 looks | — |
| 12 (0Ch × 4 = 30h) | 0-3 at y 144, x 1184, 1312, 1472, 1776 | **`$9EE8` act_0c** | 5×2 | `$A4A2`, `$A4B6`, gone | (4: not dropped on this path) |
| 13 | 4 at (672, 96) | `$9FC4` relocation | 2×4 | `$A4CA`, `$A4DA` | — |

No conveyor or barrier in level 2. All looks are inside the port's `obj_looks` copy (`$A1AA`, 476 words).

### 2.5 Hazards `$95B2` (`tables/hazards_l2.txt`)

7 vats [x0, y, x1, rows]: (848, 640, 1024, 7), (1296, 640, 1440, 7), (1568, 640, 1712, 7),
(2016, 688, 2256, 4), (1904, 288, 2240, 2), (1264, 288, 1568, 2), (608, 288, 800, 2). Each covers
(x1 − x0)/16 + 1 columns × rows + 2 rows: 12×9, 10×9, 10×9, 16×6, 22×4, 20×4, 13×4 = **604 cells**.
Every one of those cells holds attribute 0 in the map, every row-table word has attribute 0 (37
distinct tiles), and each static column matches exactly one phase of the tables: **the vats' cell writes
never change an attribute, so they change nothing the logic reads.**

### 2.6 Special objects `$8FE0` (`tables/specials_l2.txt`)

Records: handler offset (0 lift, 4 trolley, 8 vehicle; dispatch `$8B8C`: `jmp ($8B92,PC,D2)`), x, y
(long), index, path (negative ends):

| Record | Kind | x | y | Path |
|---|---|---|---|---|
| `$9088` | lift | 174 | 789 | 709, 789 (idx 2) |
| `$9098` | lift | 542 | 789 | 629, 709, 789 (idx 2) |
| `$90AA` | lift | 2542 | 789 | 469, 709, 789 |
| `$90BC` | lift | 239 | 468 | 308, 468 |
| `$90CC` | lift | 2543 | 181 | 165, 309, 389 |
| `$90DE` | trolley | 832 | 592 | x 848, 1008 (over vat 1) |
| `$90EE` | trolley | 1296 | 592 | x 1304, 1408 (vat 2) |
| `$90FE` | trolley | 1576 | 592 | x 1576, 1712 (vat 3) |
| `$910E` | trolley | 2016 | 640 | x 2016, 2224 (vat 4) |

The records live in the code area: they keep moving across deaths, as level 1's (the port: copied only
at a fresh level start, `lv_fresh`).

### 2.7 Type descriptors and hit points (`tables/descriptors.txt`, `tables/hp_tables.txt`)

`update_objects` reads the record P(t) = `$BEA6` + 16 t: width +4, height +6, score +8 (`$C414`, BCD),
handler offset +10 (`$C3FE`, from P+10), death offset +12 (`$C40E`, from P+12), hit-point class +14
(`$C510`, `$C700`). Hit points = byte [`$8060`] + class (`movea.l (-$44B4,PC),A2` at `$C512` and
`(-$46A8,PC)` at `$C706`, both `$8060`).

| Type | Handler | Death | w × h | Score | Class | SHARP / GOOD / FAIR / POOR |
|---|---|---|---|---|---|---|
| 1 walker | `$C736` new | `$C31E` | 24 × 46 | 250 | 3 | 2 / 3 / 3 / 4 |
| 2 armed enemy | `$C868` new | `$C2D8` | 24 × 48 | 1500 | 7 | 99 (then 4 every frame) |
| 3 kneeling walker | `$CB6E` | `$C2EE` | 32 × 50 | 350 | 2 | 1 / 2 / 3 / 3 |
| 4 | `$CFB0` | `$C31E` | 32 × 50 | 200 | 0 | 0 / 1 / 2 / 3 |
| 5 drip | `$D0E2` new | `$C1FA` (rts) | 15 × 15 | 125 | 7 | 99 |
| 6 barrel | `$D1E2` new | `$C33E` new | 21 × 21 | 250 | 1 | 1 / 2 / 3 / 3 |
| 12 | `$CEF8` | `$C31E` | 31 × 48 | 200 | 0 | 0 / 1 / 2 / 3 |
| 13 | `$CE72` | `$C31E` | 31 × 48 | 200 | 1 | 1 / 2 / 3 / 3 |
| 14 grenadier | `$CE0A` new | `$C2EE` | 40 × 48 | 250 | 2 | 1 / 2 / 3 / 3 |
| 15 gunman | `$CA78` | `$C31E` | 31 × 50 | 225 | 0 | 0 / 1 / 2 / 3 |
| 16 walker-gun | `$CD7A` new | `$C31E` | 31 × 50 | 225 | 0 | 0 / 1 / 2 / 3 |
| 30 | `$CA14` | `$C31E` | 25 × 48 | 225 | 1 | 1 / 2 / 3 / 3 |
| 31 | `$CA3E` | `$C31E` | 25 × 48 | 225 | 1 | 1 / 2 / 3 / 3 |
| 45 hostage | `$ED1E` | `$C1FC` | 26 × 35 | 0 | 2 | 1 / 2 / 3 / 3 |
| 49 drone | `$E6C0` new | `$C35A` | 15 × 15 | 345 | 1 | 1 / 2 / 3 / 3 |

Tables `$C716` (SHARP 00 01 01 02 03 03 04 63), `$C71E` GOOD, `$C726` FAIR, `$C72E` POOR. A hit takes one
point while the count is 0 or more; going below 0 kills (h points = h + 1 hits).

## 3. The port today, routine by routine [V: `msx_refs.json` and the source at `781005e`]

| Amiga | What | Port | Level 2 needs |
|---|---|---|---|
| `$80C2` main_loop, `$8144-$82E8` | the tick, the frame's end | `player.asm` `game_tick`, `frame.asm` | nothing (the level end is generic) |
| `$871A` level_init | the level's start | `objects.asm` `obj_start`, `level1.asm` `l1_init`, `mapobj.asm` `ao_start` | `l2_init`; the SHARP set out of `obj_start` (section 8) |
| `$8B32`, `$8B8C` | special objects | `special.asm` `sp_update` (0 lift, 8 vehicle) | **offset 4: `sp_trolley`** (4.1); `sp_ptrs`/`SP_RAM` from level 2's list |
| `$8DE6` lift | | `special.asm` `sp_lift` | as is (level 2 is `$8050` = 1: the level-1 BOB) |
| `$9150` hazards | | `special.asm` `hz_update` (+ `lv_tick`, `lv_hz`) | `vat_cut_line` = CAh each tick; `HZ_XN`/`HZ_YN` per level |
| `$91BC` level_tick_1 | vats | — | **new `lt1`** (4.2) |
| `$9C06`, `$9C76` | map objects | `mapobj.asm` `activate_objects`, `ao_look` | `ao_acts` entry 3 (offset 0Ch): **`act_0c`** (4.3) |
| `$9F84`, `$9EA4`, `$9FC4` | activators | `act_04`, `act_08`, `act_10` | as is |
| `$C3E4` update_objects | spawns, slots | `objects.asm` | `not_enemy` per level (9); `SW_N` per level (10.2) |
| death `$C1FA/$C1FC/$C2D8/$C2EE/$C31E/$C35A` | | `death_none`, `death_c1fc`, `death_c2d8`, `death_c2ee`, `death_c31e`, `death_c35a` | as is |
| death `$C33E` | type 6's | — | **new `death_c33e`** (5.5) |
| types 3, 4, 12, 13, 15, 30, 31, 45 | | `level1.asm` `t3`, `t4`, `t12`, `t13`, `t15`, `t30`, `t31`, `t45` (BANK_L1) | **the same code in BANK_L2** (10.1) |
| types 1, 2, 5, 6, 14, 16, 49 | | — | **new** (5.1-5.7) |
| `$C948` walker_legs, `$CC4A`, `$CA7C` gunman, `$D0A6` | helpers | `objects.asm` `walker1`, `walker2`, `gunman`, `aim_at` | as is |
| `$EF42`, `$EF72`, `$EF8E` | walk, fall, map cell | `obj_walk`, `obj_fall`, `logic.asm` `map_cell` | type 1 needs `$EF42`'s D6: a level-bank copy `walk_d6` (5.1) |
| `$F5BC`, `$F3CE` | enemy bullets | `ebullet_add`, `eb_update` (accelerations +C0h/+E0h included) | as is |
| `$F366`, `$F080`, `$F266` | explosions | `logic.asm` `expl_add`, `objects.asm` `expl_update` | as is |
| `$F98C`, `$F900`, `$FA7C` | pickups, hits | `logic.asm` `pickup_drop`, `hits.asm` | as is |
| `$FD76` | messages | `game_msg` (`HUD_MSG_DC76`, `HUD_MSG_DC8A`, `HUD_MSG_C238` exist) | as is |
| `$AB08`, `$AC44`, `$AC56`, `$AC6E` | BOBs | `bob.asm` `bob_draw`, `bob_part`, `bob_part2`, `bob_flashd` | as is |
| `$AFF8` player_move, `$BD72` lift_check | | `plmove.asm`, `player.asm` | as is; **states 14/15 (the trolley) never ran in level 1** (verification, 14) |

## 4. Level code: pseudo-code

Conventions: Amiga names in brackets; `x`/`y` are world words (map pixel x = world x − 128); `AM` the
mirror. "Port:" lines are the D decisions for the Z80.

### 4.1 `special_trolley` `$8F02` (record handler 4; `special.asm`, BANK_LC3) [V]

Inputs from `sp_update` [`$8B32`]: record IX (A3), D0 = its x, D1 = its y (both read before the call),
the lift-table entry IY (A0 = `$B4C` + (6 & `$168C`)), the flag byte `sp_flag` (A4 = `$167A` + n).

```
idx = rec.idx                                   ; +8: 0 or 2
if D0 == rec.path[idx]:                          ; +10 + idx (x values)
    rec.idx = (rec.idx + 2) & 2                  ; addq #2 / andi #2
idx = rec.idx
if D0 != rec.path[idx]:
    if D0 < rec.path[idx]:  rec.x += 2;  entry.dx = +2      ; (8,A0)
    else:                   rec.x -= 2;  entry.dx = -2
; seen: x in (cam_x, cam_x + 1B0h], y in (cam_y, cam_y + 118h] (signed compares, as the lift's)
if not (cam_x < D0 <= cam_x + 0x1B0 and cam_y < D1 <= cam_y + 0x118):
    return                                      ; the lift's rts $8ED0: D7 stays 6 & $168C
if flag:                                        ; RoboCop on it (lift_check set it)
    if (p_state & ~1) == 14:  p_x = D0           ; $15D0 = the x before this frame's step
    p_pend = 14 + (p_state & 1)                  ; $1696: hang (states 14/15)
flag = 0
entry.flagidx = $168A                            ; (10h,A0)
entry.left    = D0                               ; (-10h,A0)
entry.right   = D0 + 10h                         ; (-8,A0)
$168C += 2
entry.top     = D1 + 14h                         ; (A0)
if (game_frame & 1) == 0:  snd_b2d = 0Ch
draw_bob(A2 = $4B95A, D4 = $BC3, x = D0 + 10h, y = D1 + 14h - 68h)   ; 32 x 47, plain $AB08
```

- D7 left for `update_player` [`$AD78`, `sp_d7`]: after this `draw_bob`, D7 = lines × 2 × (words − 1) =
  47 × 4 = **BCh** (draw_bob computes it at `$AB26`, before any clipping exit); unseen: 6 & `$168C`. In
  level 1 every special BOB left a multiple of 16 (`& 14` = 0). Level 2's last record is trolley
  `$910E`, so when it is seen the up+fire punch box (`spawn_effect` D3 = 8) starts with direction BCh
  (`& 14` = 0Ch: it tests nothing, `fx_punch` stops from 6). **Port: `sp_d7` = BCh after the trolley's
  BOB.**
- Port: `sp_update`'s dispatch gets `cp 4 / jr z,sp_trolley`; its own window test (`1B0h`, `118h`)
  beside `sp_seen` (`1A0h`, `C4h`). It never sets `sp_rest` (trolleys never rest). The rest shortcut must
  test the handler (0 only), as it reads `sp_rest[n]` for every record. E: ~250 Z80 bytes.
- The trolley's BOB is a play-field BOB carrying RoboCop: in the field's `fb_late` group, as the lift's
  and the vehicle's.

### 4.2 `level_tick_vats` `$91BC` and its dispatcher `$9150` [V]

`$9150`, every tick (ported as `hz_update`, plus one line):

```
$15F0 = 0                                        ; vats_first_done (ported)
vat_cut_line = CAh                               ; move.b #$CA,$10356 (port: new, 5 bytes)
for each record r of lv_hz (8 bytes; x0 negative ends):
    if y in [cam_y - 64h, cam_y + ACh) and x1 >= cam_x + 73h and x0 < cam_x + 1A0h:
        D0 = p_x, D1 = p_y, D2 = x0, D3 = y, D4 = x1, A3 = r
        jmp ($91B0 + 4 * level)                   ; level 2: $91BC
```

`$91BC` (port `lt1`, BANK_L2):

```
if (random_b32 & 0Fh) == 0:  snd_b2e = 1Ah                 ; $B32: the random word
if p_x + 10h >= x0 and p_x - 10h < x1:
    d = cam_y + 98h - y
    if 0 <= d < 4Dh:
        line = CBh - d                                     ; >= 7Eh here
        vat_cut_line = line                                ; the copper's sprite-off line
        if line < 90h:                                     ; d >= 3Ch: RoboCop is under
            byte AM[$169A ^ 1] = FFh                       ; st $169A: energy target negative
            byte AM[$16CC ^ 1] = FFh                       ; st $16CC: dying
            snd_b2e = 10h
if (game_frame & 1) == 0:  return                          ; btst #0,$B01: odd frames only
c0, r0 = map_cell(x0, y)                                   ; $EF8E: column (x0 >> 4) - 8, row y >> 4
ncol = (x1 - x0) >> 4                                      ; dbf count: ncol + 1 columns
for k = 0 .. ncol:
    if vats_first_done == 0:  low byte of vat_phase[k] += 2  ; only the first in-window record's columns
    D3 = (vat_phase[k] & 0Eh) + (10h if high byte of vat_phase[k + 1] != 0 else 0)
    cell(c0 + k, r0)     = vat_top [D3 / 2]                  ; $927A
    for j = 1 .. rows + 1:                                   ; rows + 2 cells a column
        cell(c0 + k, r0 + j) = (vat_odd if j odd else vat_even)[D3 / 2]   ; $929A / $92BA
vats_first_done = FF00h                                    ; st $15F0 (high byte)
```

- Data (`tables/type_tables_l2.txt`): `vat_top`, `vat_odd`, `vat_even` (16 words each), `vat_phase`
  (words at `$92DA`; 22 columns + 1 byte read at most: `$92DA-$9307`; only `$923C` writes them; REA
  xrefs of `$92DC`: `$9242`, `$9244` only).
- The copper [V: bytes `$10332-$103CE`]: `$10356` is the line of a WAIT followed by `DMACON = 0020h`
  (sprite DMA off) and the eight sprites' control words cleared: **RoboCop's sprites are cut from that
  screen line down** (CAh by default, near the play field's bottom `CEh`). With a vat in view the line is
  the vat's surface (33h + y − cam_y), so he sinks into it; once that line is above 90h he dies.
- The death test depends on the camera, not on RoboCop's y: the camera (`$B06`) is kept exactly by the
  port, so this is trace-exact as written.
- **Port (D):** `lt1` updates `vat_phase` exactly and stores, per vat and column, the row-table index it
  would write (`vat_shown[v][k]` = D3 / 2) with a changed bit; it does **not** call `map_write_lin` for
  the 604 cells (2.5: no attribute changes; ~450 T a cell; the two patch pools of 255 would overflow and
  `tools/mapcells.py` would fail the build). The display draws vat cells from `vat_shown` (12.1).
  `vat_phase` (46 bytes) is re-initialised from the original's table at each fresh level-2 start
  (the Amiga never resets it; the difference is cosmetic only: no logic reads the vat cells).
- `vat_cut_line` is computed every tick for the display (12.2). E: `lt1` ~250 Z80 bytes.

### 4.3 `act_0c` `$9EE8` (activator offset 0Ch; `mapobj.asm`, BANK_LC2) [V]

Called by `activate_objects` for an in-window entry of map type 12 with D0 = x, D1 = y, A1 = the entry,
A2 = its type table, D3 = its look index (already ≥ 0).

```
act0c_word = E680h                               ; $A4A6: look $A4A2's word 2 (third cell of row 0)
if (game_frame & 4) == 0:
    act0c_word = 9700h
    if (game_frame & 3) == 0:  snd_b2d = 28h     ; every 8th frame, per entry in the window
if y == ((p_y + 8) & ~15) - 10h and x == (p_x & ~15) - 20h:   ; RoboCop at x + 32..47, y + 8..23
    entry.hits_hi = FFh                          ; st 4(A1): animate the look
    expl_add(type 0, x + 10h, y); expl_add(type 0, x + 24h, y)
    expl_add(type 0, x + 38h, y); expl_add(type 0, x + 4Ch, y)   ; D0 back to x
; $9FAE: no collision slot
look = looks[type 12][entry.look]                ; $A1F2: $A4A2, $A4B6, -1
if look < 0:  entry.look_hi = FFh; next entry    ; st 2(A1): off (no pickup on this path)
if entry.hits_hi bit 7 and game_frame odd:  entry.look += 4   ; for the next frame ($9CD2)
copy look block (5 x 2 map words) into the map at (c0, r0)    ; with word 2 = act0c_word for $A4A2
```

- Port (D): `act0c_word` is a tick variable (each frame's value is written before any use). After
  `ao_copy` (which may skip an unchanged look through `lk_cache`), when the look copied is `$A4A2`, write
  cell (c0 + 2, r0) = `act0c_word` with `map_write_lin` (one patch per entry, 4 cells in all; a redraw
  every 4 ticks per visible entry). ~200-320 Z80 bytes (E).
- The 4 explosions do not hurt RoboCop (`$FA7C` tests bullets, enemies and pickups only).

## 5. The new object types: pseudo-code

Slot fields (Amiga offset from A3 → port `OS_*`): word/bytes 0, 1 (`OS_L0`), byte 2 facing (`OS_FACE`:
FFh = right of RoboCop, moving left), byte 3 (`OS_B3`), x −20h/−1Eh, y −80h/−7Eh (16.16), long −60h,
long −40h, type +20h, hit points +21h, flash +22h, touch +23h. A Amiga byte at offset d is at
IX + (d ^ 1). `update_objects` sets `$16BA`'s high byte (`st`) before each handler and leaves
D7 = type × 16 (`$C3F6`). A handler returns D0 < 0 to free its slot. Drawing calls: `$AB08` plain
(`bob_draw`), `$AC44` first part (`bob_part`, result to `$16BA`), `$AC56` last part (`bob_part2`, result:
its own, or `$16BA`'s when not drawn), `$AC6E` flash (`bob_flashd`).

### 5.1 Type 1 `$C736`: a walker with a torso [V]

```
(A3).w += 1
D2 = (A3) & 0Eh;  if FACE == 0: D2 += 10h                ; facing right
D0 = x; D1 = y
D1 = obj_fall(x, y + 2Ch) - 2Ch                          ; $EF72: vy += 2800h unless solid; D1 snapped
D6 = walk_d6(4)                                          ; $EF42: turn or x += +-4; D6 as it leaves it
save D2, D1, D0                                          ; D0 = the x before the step
if (game_frame & 2Dh) == 0:                              ; 4 frames in 64
    A2 = $6CDA0;  bx = D0 - 18h
    if FACE == 0:  bx = D0 + 28h;  A2 = $6CEE0;  D7 = 4;  D6 = 6
    ; FACE != 0: D7 = 10h (type 1 x 16 from update_objects), D6 = walk_d6's
    ebullet_add(type D6, dir D7, bx, D1 + 12h)           ; type 0: the slot is written but stays free
    bob_draw(A2, $403, bx, D1 + 8)                       ; muzzle flash 32 x 16
D0, D1, D2 = saved
bob_part($3E810 + t1_legs_gfx[D2/2], $5C3, D0, D1 + 15h)            ; legs 32 x 23
D2 &= 0Eh
tx = D0 - 2;  A2 = $404D0;  if FACE == 0: tx = D0 + 2;  A2 = $40674
return bob_part2(A2, $543, tx, D1 + t1_torso_dy[D2/2])              ; torso 32 x 21
```

- `walk_d6` (port, BANK_L2, ~70 bytes): `obj_walk` returning `$EF42`'s D6: 0 after a step; on a turn,
  `attr & 18h` when that is not 8, else 2 (a wall above-beside). Level 2's map and looks have no
  attribute bit 4 (codes 00, 01, 02, 03, 08, 09, 0B, 0D), so D6 is 0 or 2.
- **Quirk kept [V: listing; to confirm on the bench]:** a type 1 facing left fires bullet type D6 with
  D7 = 10h: normally type 0 (no bullet: `ebullet_add` writes x, y, vx = 0, vy = −4, +A0h, +C0h, +E0h of
  the first free slot and leaves its type 0; sound `eb_snd[0]` = 0); on a frame it turned left at a wall,
  type 2 (the missile, 40h damage) flying up. Its muzzle flash is drawn either way.

### 5.2 Type 2 `$C868` and its tail `$C91A`: the armed enemy, the level's end [V]

```
if (game_frame & 3Fh) == 0:  game_msg("ARREST ARMED EMEMY.")       ; $DC76
(-40h).w += 1;  c = (-40h).w                                       ; OS_L40's high word
x = 180h;  D0 = 180h;  D1 = y
ac_camdx = 500h                                                    ; the immediate at $B2D8 (108h)
A2 = $3D280
if c >= 46h:
    if (c & 33h) == 0:                                             ; bursts at 4-frame steps, every 64
        bob_draw($6CDA0, $403, D0 - 14h, D1 + 6)                   ; muzzle flash
        if ebullet_add(type 5, dir 0Ch, D0, D1 + 10h):             ; vx -9, vy 0
            slot.ay = -1000h;  slot.ax = -2000h                    ; longs +E0h, +C0h
            if c & 40h:  slot.ay = +3000h
    A2 = $3D910                                                    ; the shooting pose
if game_frame & 8:  bob_flashd(A2, $E04, D0, D1)                   ; 48 x 56, white
else:               bob_part2(A2, $E04, D0, D1)
; $C91A (always: pea): 
hp = 4                                                             ; +21h: needs 5 hits in one frame
if touch:                                                          ; +23h, set by $FA7C
    game_msg("ARREST SUCESSFUL.");  snd_b2c = 21h                  ; $DC8A
    level_done = FFh;  end_count = 40h                             ; $16D0, $16C4
    return -1
return 0                                                           ; never freed by clipping
```

- Killed anyway (5 hits in a frame): death `$C2D8` (ported): energy − 30h, "SUSPECT DESTROYED.", the big
  explosion; no level end; the entry (once, 40h) spawns it again when its window is left and re-entered.
- `ac_camdx` = 500h pins the camera at x 0 (target `p_x` − 500h, clamped): the view shows map x 0-287, the
  enemy at map x 256-303 on the right, RoboCop arriving from the left lift (`$90BC`, x 239). `level_init`
  (`obj_start` in the port) writes 108h again at every level start or restart.

### 5.3 Type 5 `$D0E2`: a drip [V]

Bytes 0 = state, 1 = frame counter (n); −60h vy; y 16.16.

```
D0 = x;  D1 = y
switch state:
  0: n += 1;  if n >= 5: state = 1                       ; grows (frames 0-3), then falls
  1: solid = map_cell(x, D1 + 18h)                       ; $EF8E
     if touch:  energy -= 0Ah;  solid = true             ; $169A: own damage (touch: 5.10)
     if solid:  state = 2;  snd_b2e = 12h;  (-60h).w = 1;  (-80h).w += 2
     else:      vy += 8000h;  y += vy
  2: n += 1;  if n >= 0Ch: return -1                     ; splash frames 5-10
f = (n & 3Fh) - 1
return bob_draw($3BFC0 + t5_gfx[f], t5_size[f], D0 + t5_dx[f] - 0Ah, D1)   ; freed off screen
```

(D0, D1 are the values read at entry, before this frame's fall.)

### 5.4 Type 6 `$D1E2` (+ `$D1CA`, `$D1D0`, `$D1DE`): a barrel [V]

Bytes 0 = launched, 1 = animation counter (a), 2 = "not drawn" (the last draw's D0 byte); −40h bounce
speed (long); −60h vy; −80h y (16.16); −20h x.

```
if not launched:
    if p_y < 1A0h or p_y >= 1D1h or barrels_killed >= 10h:  return -1     ; $D1DE
    if barrel_gap != 0:  barrel_gap -= 1;  x = y = 0;  return 0           ; $D1CA, $D1D0
    if (game_frame & 13h) != 0:  x = y = 0;  return 0                     ; $D1D0
    barrel_gap = 2;  launched = FFh;  x = 78h;  y = 160h
    bounce = -7.0;  if game_frame & 4:  bounce = -4.5                     ; -70000h / -48000h
    (-60h).w = 1                                                          ; vy 1.0
D5 = a & 0Eh;  if D5 == 10h or D5 == 6:  a = 0;  D5 = 0                   ; (& 0Eh: 10h never matches)
a += 2;  vy += 8000h
D0 = x;  x += 3
y += vy;  D1 = y
if D0 >= A0h and map_cell(D0, D1 + 18h) is solid:     ; $EF8E; solid also snaps D1:
    D1 = ((D1 + 18h) & ~0Fh) - 18h                     ;   the draw's y only
    if notdrawn == 0:  snd_b2e = 19h
    vy = bounce;  D5 = 6;  a = 8
if D0 >= cam_x + 1E8h:  return -1
notdrawn = bob_part2($3C920 + t6_gfx[D5/2], $603, D0, D1)    ; 32 x 24; its D0 low byte
return 0
```

### 5.5 Death `$C33E` (type 6) [V]

```
barrels_killed += 1                                  ; $15F2 (cleared every life)
if (barrels_killed & 3) == 0:
    pickup_drop(barrels_killed == 10h ? 1Ch : 24h, x, y)   ; energy at the 16th, else a nuke
expl_add(type 0, x, y)                               ; falls into $C35A
```

### 5.6 Type 14 `$CE0A`: a grenadier that stays put [V]

```
D0 = x;  D1 = y;  FACE = (x >= p_x) ? FFh : 0          ; spl every frame
D6 = 0;  D7 = 20h;  A2 = $3DFA0
if FACE == 0:  A2 = $3E3D8;  D6 = 2Ch;  D7 = 14h
if (game_frame & 2Fh) == 0:                            ; 2 frames in 64
    expl_add(type 1, D0 + D6 - 4, D1 - 4)              ; (D7 saved around it: $F366 uses D7)
    if ebullet_add(type 4, dir D7, D0 + D6 - 4, D1 + 2):   ; (-5, -2) or (5, -2)
        slot.ay = 4000h                                ; lobbed
return bob_part2(A2, $904, D0, D1)                     ; 48 x 36
```

### 5.7 Type 16 `$CD7A`: a walker with a big gun [V]

```
D0, D1, D2 = walker1()                                 ; $C948 (ported): legs, fall, walk; D1 with its bob
D1 += 2;  save D1, D0
c = (-3Eh).w += 1                                      ; OS_L40's low word
if c >= 1Eh:
    if c >= 2Eh:  (-3Eh).w = 0
    if (c & 7) == 0:                                   ; c = 20h, 28h
        bx = D0 - 20h;  A2 = $6CDA0;  D7 = 1Eh;  D6 = 5
        if FACE == 0:  bx = D0 + 32h;  A2 = $6CEE0;  D7 = 16h;  D6 = 6
        ebullet_add(type D6, dir D7, bx, D1 + 0Ah)
        bob_draw(A2, $403, bx, D1 + 6)
restore D0, D1
A2 = $40818;  D0 -= 9
if (-3Eh).w >= 14h:  A2 += 5A0h;  D0 += 4;  D1 += 2   ; aiming
if FACE == 0:  D0 += 12h;  A2 += 2D0h
return bob_part2(A2, $604, D0, D1)                     ; 48 x 24
```

### 5.8 Type 49 `$E6C0` and the flight `$E728-$E7B1`: a drone [V]

Word 0 = direction counter (dir); byte 3 = started; −60h.w = target (×2); −40h.w = life; x, y 16.16.

```
A2 = $41358
if B3 == 0:  B3 = FFh;  dir = 10h                      ; down
; $E728
D2 = dir & 1Eh
x += (fly_dx[D2/2] << 16) >> 1;  D0 = x                ; 16.16 adds: half a step a frame
y += (fly_dy[D2/2] << 16) >> 1;  D1 = y
if D2 == target:
    target = 2 * aim_at(D0, D1 + 34h)                  ; $D0A6: 0 up ... 0Eh up left
elif D2 < target:  dir += 1
else:              dir -= 1
bob_part2(A2 + fly_gfx[D2/2], $402, D0, D1)            ; 16 x 16; result ignored
if touch:  energy -= 18h;  goto boom                   ; own damage (touch: 5.10)
life -= 1;  if life == 0:  goto boom                   ; from 0: 65536 frames
return 0
boom: expl_add(type 0, x - 8, y - 8);  return -1
```

The first target is 0 (cleared slot), so a drone first turns from down through right to up (16
frames), then homes. It is never freed off screen. Type 38's part `$E6D6-$E727` (the mailbox
`$E67A-$E67E`, written only by level-3 types: REA xrefs `$D72C`, `$E7D8`, `$E80E`, `$E82A`, `$E8A8`,
`$E8DE`, `$E8FA`) is not needed.

### 5.9 Enemy bullets in level 2 and their damage [V: `$FA35`/`$FA4C`/`$FA63`, `$F5D2`, `$F658`/`$F67C`; `tables/ebullets.txt`]

| Bullet type | Fired by (level 2) | Damage | Port (DAMAGE_X 3; types 1-2 at most ×2) |
|---|---|---|---|
| 1, 2 missile | type 3 (`$CC4A` kneeling; markers band 2); type 1's leftover D6 = 2 | 40h | 80h |
| 3 | types 4, 12, 13, 15, 30, 31 (gunman) | 6 | 18 |
| 4 grenade | type 14 (ay 4000h) | 0Ch | 36 |
| 5 | type 2 (ax −2000h, ay −1000h / +3000h), type 16 left | 0Ch | 36 |
| 6 | type 1 right, type 16 right | 6 | 18 |
| 0 | type 1 facing left (no bullet) | — | — |

Directions used: 4 (9, 0), 0Ch (−9, 0), 10h (0, −4), 14h (5, −2), 16h (9, 0), 1Eh (−9, 0), 20h
(−5, −2) (pixels a frame, integer words of 16.16). The port's rule (`hits.asm` `phb_en`: type < 3
doubled, else ×DAMAGE_X) needs no change; the 23-entry tables suffice (D6 is 0 or 2 in level 2).

### 5.10 Other damage to RoboCop in level 2 [V]

| Source | Amount | Port today | Proposed (D) |
|---|---|---|---|
| touching an enemy-slot object (`$FA7C`, every frame of contact) | 1 | ×DAMAGE_X | as is (drips, barrels, drones, the hostage included, as on the Amiga) |
| a drip touching him (type 5, falling) | 0Ah more | — | ×1 (like level 1's beams `lt0`) |
| a drone touching him (type 49) | 18h more | — | ×1 |
| a vat | death | — | as is |
| killing the armed enemy (`$C2D8`) / a hostage (`$C1FC`) | 30h / 20h | ×1 | as is |

## 6. Shared level-1 handlers in level 2 [V]

Types 3, 4, 12, 13, 15, 30, 31, 45 run the same code with the same tables (`t3_gfx`, `t4_*`, `t12_*`,
`t30_dy`, `t45_gfx`, `t45_dy` are main-code tables). Their BOB addresses that fall in `$28000-$4B54B`
(DATAL1 in level 1) read DATAL2 or MADEX in level 2: the hostage's `$4B31C` (legs) and `$498DC` (body),
for instance, are MADEX's bytes in level 2. The logic is unchanged; the graphics area converts them per
level. Hostage ids (y & 15) are 0-9: the 10th rescued is an extra life (`$ECD8`).

## 7. RoboCop's interactions [V unless marked]

- **Lifts** (5): `$8DE6`, as level 1's.
- **Trolleys** (4, 4.1): `lift_check` `$BD72` stands him on the entry when his x is in [x, x + 16) and
  his new y in (top − 15, top] (top = trolley y + 14h; not while rising in the air): y = top − 4, x + dx,
  the flag set. The trolley then asks state 14/15 (hanging; `player_move` lets only "up" through there)
  and holds his x at its own; it shuttles 2 px a frame between its two x values over a vat (I: what "up"
  does there comes from the ported state table; to see on the bench).
- **Vats** (7, 4.2): falling in kills (camera test), the sprite cut shows him sinking.
- **Floor switches** (16, `$9F84`): trapdoors (as level 1's). **The trap `act_0c`** (4): stepping on the
  blinking cell explodes it (no damage) and leaves the destroyed look.
- **The relocation** (1, `$9FC4` at (672, 96)): "up" 80 frames there → (192, 112), as level 1's wall.
- **Shootable crates and cans** (22): pickups 4-32 (all ported); type 6's deaths drop nukes and energy.
- **Falling things**: drips (type 5, from y 368), drones (type 49, from the ceiling y 16, homing),
  barrels (type 6, launched from x 120 while he is in y 416-464), pickups falling ($F900).
- **No conveyors, beams, barriers or ladders** in level 2 (none in its lists; `player_move` has no
  climbing state).

## 8. Hit points, `$8060` and the SHARP set [V; D]

- Every enemy takes its hit points from `[$8060] + class` at its spawn (2.7). The port keeps `$8060` as
  `ac_diff` (DD0Ch), set by `front_range` after level 1 (RANGE.md 3.10).
- `obj_start` (`objects.asm:44`) sets `ac_diff = diff_tab` at every level start and restart: level 2
  would lose the range's rating. **Move those 6 bytes to `ng_go` (`rc2.asm`)**, the port of
  `load_level0`'s `$8314` (a new game). Deaths and continues keep `ac_diff` as on the Amiga: a level-2
  restart is `$86FE` → `rts` (nothing reloaded); a new game after level 2 is `$870A` → `$82EC`.
- Check: a level-2 spawn's +21h equals the range's table (POOR: types 4/12/15/16 get 3, not 0).

## 9. ENEMY_CAP in level 2 [D]

`uo_cap` counts the slots whose type `not_enemy` rejects. Level 1: 32, 44, 45. Level 2 proposal:

| Counted (enemies) | Not counted |
|---|---|
| 1, 3, 4, 12, 13, 14, 15, 16, 30, 31, 49 | 45 hostage (decision 25); 5 drips and 6 barrels (hazards: 9 + 1 respawning entries would hold the only slot); 2 the armed enemy (the level's end, like 32: it spawns as on the Amiga and never blocks the rest; it is never freed by clipping, so counted it would stop every enemy for the rest of the level if RoboCop went back) |

Port: `not_enemy` becomes `jp lv_noten` (the level bank's header), −6 bytes in LC1.

## 10. Port design

### 10.1 Banks and sources (D)

- **BANK_L2** (one 8 KiB bank at A000h, mapped while the game ticks like BANK_L1): `lv_htab` (53 × 4),
  `lv_init` / `lv_tick` (= `lt1`) / `lv_hz`, the new per-level header fields (10.2), `l2_init`, the new
  handlers (5.1-5.8, `death_c33e`, `walk_d6`), `lt1`, the shared level-1 handlers, the spawn-walk
  shortcuts (`sw_prep` … `sw_bits`), its tables (10.4) and `cells_l2.inc`.
- **Shared handlers**: z80asm labels are global, so the same source cannot be included twice. Move `t3`,
  `t_xy`, `t_face`, `t_col`, `t_word`, `t4`, `t12`, `t13`, `t15`, `t30`, `t31`, `t45`, the `sw_*` code and
  `l1_init`'s generic part to `msx/lvshared.asm`; BANK_L1 includes it; `tools/mkrom.py` writes
  `gen/lvshared_l2.asm` with every label defined there suffixed `_l2` (references to other files kept)
  for BANK_L2. Measured today in BANK_L1: handlers 1,194 bytes, shortcuts and init 664.
- `special.asm` (LC3, 5,105 bytes free): `sp_trolley`, its dispatch, `vat_cut_line` = CAh in `hz_update`.
- `mapobj.asm` (LC2, 5,087 free): `act_0c` in `ao_acts`' entry 3.
- `objects.asm` (LC1, 39 free): only the three per-level edits of 10.2 (net −11 bytes).
- Fixed code (190 free): `ng_go` sets `ac_diff` (+6) and maps the level bank by `$8050` (`lvl_bank`).

### 10.2 Per-level parameters that are assembler constants today (D)

| Today | Where | Level 2 |
|---|---|---|
| `SW_N` (28) | `objects.asm:376-378` (`uf_last`), `level1.asm` `sw_init` | 40: read from the level bank (`lv_swlast`, `lv_swn1`) |
| masks are longs (32 entries): `cp 32`, 4-byte `sw_dirty` | `level1.asm` `sw_prep`, `sw_init`, `sw_dbit`; `msx.inc` | 5 bytes (40 entries; level 3 has 39) |
| `sw_ptr` (a label in BANK_L1) | `objects.asm:234` | at a fixed address in every level bank (after the header), or computed |
| `HZ_XN`, `HZ_YN` | `special.asm:651, 663` | from the level bank's header |
| `not_enemy` 32/44/45 | `objects.asm:180` | `jp lv_noten` |
| `ac_diff` = SHARP | `objects.asm:44` | moved to `ng_go` |
| `ao_acts` entry 3 = `ao_look` | `mapobj.asm:144` | `act_0c` |
| `sp_update` dispatch 0 / 8 | `special.asm:114-117` | + 4 |
| `BANK_L1` | `rc2.asm:147` | by level |

### 10.3 RAM (D)

- `AC_VARS` (DD20-DD5F, the shortcuts): `sw_list` 33 → 41, `sw_dirty` 4 → 5, `sw_key` 6 → 7; repacked they
  end at DD5D (2 bytes spare). `barrel_gap` (`$D1DC`, persists across lives, levels and games, 0 at
  power-on) in DD74-DD7F (free).
- Tick variables: `vat_cut_line` and `act0c_word` (G_VARS: CE42h-CE43h are free).
- Level-2-only (objl_ram's tail F012h-F0FFh, 238 bytes free behind level 2's 530-byte list; the range
  uses it only between levels): `vat_phase` 46 bytes (copied from at_l2 at a fresh level-2 start),
  `vat_shown` 103 bytes + changed bits 13 bytes.
- `$15F0`, `$15F2`, `$167B-$1683` (9 special flags), `$16DB-$16E4` (10 hostages) are in AM already.
- `spawn_ram` (640) holds 562 bytes, `objl_ram` (768) 530, `SP_RAM` (256) 150, `sp_ptrs` 9 + 1,
  `SP_REST_N` 12 ≥ 9 + 1.

### 10.4 Tables for `tools/amitab.py` (`analysis/amiga_tables.tsv`, bank `l2`) (D)

| Label | Address | Count | Kind | What |
|---|---|---|---|---|
| `l2_hdr` | 868c | 20 | w | header |
| `spawn_l2` | 97b0 | 562 | x | spawn list (40 × 14 + end) |
| `objl_l2` | a828 | 530 | x | object list (44 × 12 + end) |
| `sp_l2` | 9088 | 150 | x | special records (5 lifts, 4 trolleys) |
| `spl_l2` | 8fe0 | 10 | l | their list |
| `hz_l2` | 95b2 | 29 | w | vats |
| `vat_top`, `vat_odd`, `vat_even` | 927a, 929a, 92ba | 16 each | w | row words |
| `vat_ph0` | 92da | 24 | w | the phases' initial words |
| `t1_gfx`, `t1_dy` | c7e0, c800 | 16, 8 | w | type 1 |
| `t5_size`, `t5_gfx`, `t5_dx` | d17c, d19a, d1b0 | 11 each | w | type 5 |
| `t6_gfx` | d2da | 8 | w | type 6 |
| `fly_dx`, `fly_dy`, `fly_gfx` | e680, e6a0, e7b2 | 16 each | w | type 49 |
| (copies of `t3_gfx`, `t3_size`, `t4_*`, `t12_*`, `t30_dy`, `t45_gfx`, `t45_dy`) | as level 1 | | | for the shared handlers in BANK_L2 |

About 1,970 bytes. `cells_l2.inc` from `tools/cellmasks.py` with level 2's lists (its `SW_MAX` 32 → 40).

## 11. Size and CPU estimates [E]

### 11.1 Z80 bytes (level 1's measured ratio: Z80 / 68000 = 1.43 for its types, 1.31 specials, 2.31 map objects)

| Routine | 68000 B | Z80 B | Bank |
|---|---:|---:|---|
| type 1 + `walk_d6` | 170 | 245 + 70 | L2 |
| type 2 + `$C91A` | 224 | 320 | L2 |
| type 5 | 154 | 220 | L2 |
| type 6 + `$D1CA-$D1E1` | 272 | 390 | L2 |
| death `$C33E` | 28 | 40 | L2 |
| type 14 | 104 | 150 | L2 |
| type 16 | 144 | 205 | L2 |
| type 49 + `$E728-$E7B1` | 160 | 230-270 | L2 |
| `lt1` (no cell writes; `vat_shown`) | 190 | 250 | L2 |
| `l2_init`, header fields, `lv_noten` | — | 200 | L2 |
| **new in L2** | **1,446** | **~2,350** | |
| shared handlers + shortcuts (copies) | — | 1,860 | L2 |
| tables + cells | — | ~2,300 | L2 |
| **BANK_L2** | | **~6.5 KiB** (6.0-7.2) | |
| `sp_trolley` + dispatch | 190 | ~260 | LC3 |
| `act_0c` | 140 | 200-320 | LC2 |

### 11.2 CPU per tick (Z80 3.58 MHz)

Level 1's busiest tick was measured at ~74,000 T (2026-10-20, five enemies; less since ENEMY_CAP 1
and the shortcuts). Level-2 costs on top of the shared core (~25,000 T: player_move, collisions with 8
bullets, update_player, draw_player's logic, activate_objects, the spawn walk, explosions, pickups):

| Part | T a tick |
|---|---:|
| specials: 5 lifts (rest shortcut) + 4 trolleys (never at rest; one seen) | ~2,300 |
| `lt1`, one vat in the window (odd ticks ~2,000, even ~400) | ~1,400 |
| (the same writing 108 cells with `map_write_lin`, ~450 T each) | (~24,000) |
| `act_0c`, 2 entries in the window | ~800 |
| one enemy (type 16 or 1, with its BOBs) | ~4,500 |
| 2 drips, a barrel, a hostage | ~9,000 |
| a drone | ~2,000 |
| 8 enemy bullets (the armed enemy's bursts) | ~4,800 |

Busy scenes (the vat corridors with a trolley ride and drips; the drips corridor at y 368-470; the top
corridor with drones, once-only gunners and the armed enemy): **~45,000-55,000 T a tick**, about two
thirds of level 1's measured worst. To measure with `rc2_prof` once built. The R800 runs the same code
4-5 times faster.

## 12. What the logic asks of the display (for the graphics and flow areas)

1. **Vat animation** (4.2): up to 108 visible cells change every odd tick (12.5 Hz); at ~0.75 ms of VDP a
   16×16 cell that is 81 ms per 80 ms: not possible beside the scroll. The logic gives `vat_shown` and
   changed bits; the display picks a rate. Default (D): the surface row (12-22 cells) at full rate through
   the changed-cell queue, the body columns round-robin as VDP time allows; alternatives: all cells best
   effort (slower, uneven), or static vats.
2. **The sprite cut** (`vat_cut_line`, Amiga copper lines; CAh = no cut): RoboCop's sprites hidden from
   the vat's surface down while he sinks (a few ticks before the death). Default (D): no cut in the first
   build (he shows whole until the death sequence); alternative: a line interrupt at that line clearing
   R#8's sprite enable until the HUD split (it would also hide enemies' sprites and bullets below the
   line), or dropping his bands below it in the sprite engine.
3. **The armed enemy's scene** (5.2): with `ac_camdx` = 500h the camera sits at x 0; the MSX view (256 of
   288) at view x 0 leaves the enemy (map x 256-303) just outside. Default (D): while type 2 lives the view
   is the camera's + 48 (map x 48-303: the enemy whole, RoboCop from map x 48, the left lift at map x 111);
   alternative: the proportional view as today (he shoots from off screen until RoboCop walks right).
4. **More play-field BOBs**: the 4 trolleys (32 × 47, every tick, carrying RoboCop: `fb_late`), the armed
   enemy (48 × 56, white every 8 frames), types 14 (48 × 36) and 16 (48 × 24 body) — as ROM_BUDGET 3.2.

## 13. Defaults chosen (the user is away), each with its alternative

| # | Default | Alternative |
|---|---|---|
| 1 | The vats update their phases exactly but never write map patches; the display draws them from `vat_shown` | `map_write_lin` per cell (needs pools for 604 cells and ~24,000 T a tick) |
| 2 | `vat_phase` re-initialised at each fresh level-2 start | kept from power-on in persistent RAM (exact across games; cosmetic only) |
| 3 | `act_0c`'s blinking cell written with `map_write_lin` after the look copy | the look block in RAM with the patched word |
| 4 | Type 1's leftover D6/D7 reproduced (left-facing: no bullet, rarely an upward missile) | always fire type 6 left (a fix, not the original) |
| 5 | ENEMY_CAP: 2, 5, 6, 45 not counted | type 2 counted (one-on-one at the end; risks blocking enemies) |
| 6 | Own damages of types 5 (0Ah) and 49 (18h) ×1, as level 1's beams | ×DAMAGE_X (type 49 ×2 as a missile) |
| 7 | The SHARP set moved from `obj_start` to `ng_go` | `obj_start` guarded by `$8050` = 0 (RANGE.md 7, #6) |
| 8 | Shared handlers through a generated, label-suffixed copy | one shared bank with trampolines (no: the level bank is A000h's only window) |
| 9 | `sp_d7` = BCh after the trolley's BOB | — (needed for trace identity) |
| 10 | No sprite cut at the vat line at first | a line interrupt (12.2) |
| 11 | The armed enemy's view right-aligned | the proportional view |

## 14. Verification (for the bench and the build)

- Bench drives (the bench area): a trolley ride over vat 1 (states 14/15, `$15D0` held, `$1696`), a fall
  into a vat (`$169A`, `$16CC`, `$10356`), the trap at x 1184 (explosions, look 1, off), barrels until the
  16th kill (`$15F2`, pickups 36/28, `$D1DC`), drips touching him, a drone homing and exploding, the top
  corridor, the arrest (`$16D0`, `$16C4`, the score count, `$8050` = 2), each at SHARP and POOR (`$8060`).
  A left-facing type 1 on a fire frame (bullet slot written, type 0) and one turning at a wall.
- Fields to add to `analysis/amiga_ram.tsv` for level 2: `$97B0` (rec, 40), `$9088-$911D` (specials),
  `$15F2`, `$16E2-$16E4` (hostages 7-9), `$D1DC`, `$B2D8` (exists), `$10356` (`vat_cut_line`), and the
  enemy bullets' +C0h/+E0h longs; `$92DA-$9307` only for a visual check.
- The build: `tools/mapcells.py` for level 2 must leave the vats out (4.2); `tools/cellmasks.py` with
  40 entries; LC1 must not grow.

## 15. Open questions and risks

- [I] What "up" does in states 14/15 on the trolley (the ported `player_move` decides; never exercised).
- [I] Whether a death while hanging over a vat leaves the trolley's flag set (it is cleared only when
  seen; harmless on the Amiga).
- The vats' display (12.1) is the largest unknown of level 2's speed; the logic itself is lighter than
  level 1's.
- Type 1's leftover registers are verified from the listing only; the bench should show a frame of each
  case before the port relies on it.
- `$C91A`, `$D1CA`, `$D1D0`, `$D1DE` need `+entry` seeds (`level2.sym`) for REA to list or cross-reference
  them.
