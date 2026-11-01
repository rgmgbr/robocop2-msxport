# Level 3: the Civic Centrum, the plan

Written on 2026-11-01 (the night's step 2) as the plan for porting level 3, the last level, whose
end hands over to the ending (the night's step 3). It follows `docs/LEVEL2.md` (the model: its
sections 3.1-3.13 and their **As built** notes describe the machinery reused here) and keeps to the
facts the implementing steps need. Each step appends its account to `docs/level3/HANDOFF.md`.

The rules that bind it are level 2's (`docs/LEVEL2.md` intro) with the user's orders of 2026-10-31:
`DAMAGE_X` 2, the missiles at the original's damage, ENEMY_CAP 1 (types that draw nothing and the
hostage not counted), decision 13 (every frame 48 px wide or more in the play field, no sprite piece
ever cut), left = right mirrored, 25 Hz logic trace-identical to the bench, zero glitches,
frame-to-frame coherence, the MSX2 baseline, generic hardware, the 2 MiB Konami SCC image with its
boot guard, nothing that works changes (levels 1 and 2 keep their traces at 0 differences, the
title is frozen).

Tags: **V** verified (REA with the Ghidra 12.1.4 provider, raw-binary m68k, entry 0x0, seeds
`analysis/ghidra_seeds.tsv`, on `build/ram/level3_full.bin` sha256 `700df44d…3515ca`; a byte read of
the game's data; or a run of the bench `tools/amigaemu.py game --level 3`); **I** inferred; **D** a
design decision; **E** estimated. The bench runs used here: the coverage `amigacov.py --level 3
--scenario level3` (three god-mode runs, 24,953 game frames, ten minutes) and four boss drives
(`build/archive/level3_research_2026-11-01.tar.gz`: `bossrun.py` and its JSON logs).

The main code `$8000-$125FF` is byte-identical in the three level images [V: byte compare], so every
name and seed of `analysis/main_8000.sym` holds in level 3, and the level-2 port's routines of the
main code (`update_objects`, the lifts, the bullets, the explosions, the pickups) are level 3's too.

## 1. Summary

- **What level 3 is [V].** RoboCop starts outside the Civic Centrum at (1184, 784), bottom left, with
  7:30 on the timer. He fights up through the building (seven electric beams, three lifts, crates,
  big walkers) to the roof, where Cain, now RoboCop 2 (type 22), appears ("CHASE CAIN"). Cain runs
  ahead of him to the right and down through a car park (wall turrets, a truck, flying machines,
  bombs and homing missiles that Cain launches). Cain cannot be hurt until he is low in the car
  park (his hit points are put back to 44 every frame while his y is above 290h); his death ("CAIN
  DESTROYED.") ends the level, and the game: `level_load_3` `$86DE` (the ending, step 3's).
- **The data [V].** Header `$86B4`; DATAL3 (185,356 B at `$28000-$5540B`): the tile sheet, the map
  160 × 50 at `$38000`, level 3's BOBs `$3BE80-$5540B`; SPERMA's tail `$5540C-$5884D` stays resident
  (types 4 and 12's frames); palette `$10036`, **level 2's**. Lists in the main code: spawn list
  `$99E2` (39 entries), object list `$AA3A` (15), special objects `$9008` (3 lifts, drawn in two
  parts), hazards `$95EC` (7 beams, `level_tick_2` `$9436`), markers `$C624`.
- **The objects [V].** 20 types seen on the bench: the new 21, 22, 33-43, 47, 48, 50, 51, 52 and
  level 1's 4 and 12. Level-3-only Amiga code: **4,222 bytes** (REA function bodies), the boss alone
  764. Three new deaths (`$C25C`, `$C360`, `$C3A8`) throw the dead enemy's parts as debris bullets.
- **The frames [V: bench].** 202 frames drawn: 136 in DATAL3 (**58 of them 48 px wide or more**:
  116,736 px, plus the lift's two parts), 12 in SPERMA's tail, 54 in PERMA (shared).
- **The port [D].**
  - Level 3 is the descriptor's third entry; `lv_go` with A = 2; `ml_ev` sends `$8050` = 2 to
    `lv_next` and `$8050` = 3 to step 3's ending; `LV_TEST=3`.
  - Two logic banks: **`BANK_L3`** (the header, the shared handlers' copy, `l3_init`, the beams,
    the deaths, the lists) and **`BANK_L3B`** (the 19 new types, 46 among them though nothing
    spawns it), reached through a small fixed-area trampoline like `field_call`.
  - The palette is **level 2's palette C, byte for byte** (mean ΔE76 2.18 against 2.68 for level 1's
    palette as it is).
  - The play field gets a **dynamic frame cache** in VRAM page 2 lines 160-231 for the big animated
    frames (Cain and type 21), filled on demand from ROM like today's explosion slot;
    their hit flash is a white copy uploaded into the cache (no sprite silhouettes); a **per-level
    `FIELD_ID0`** gives level 3 its ids (about 123 sprite + 83 play-field frames). *As built (3.10):
    seven fixed places, not filled least-recently-used; the white copies stored in the ROM (colour
    9); 150 sprite and 66 play-field ids, `lv_fid0` 98h.*
  - The sprite pool grows in place by about 1-2 banks (levels 1 and 2's records unchanged). *As
    built: one bank (3.10).*
- **ROM [E].** Level 3 about 22-25 banks (logic 2, tiles 8, map 2, attributes 1, tables 1, atlas 1-2,
  big frames 6-7, pool +1-2); with step 3's ending about **153-157 of 256 banks**. The image is 2 MiB
  from level 3's first block on (the boot guard). *As built: 31 banks (the frame cache 14, with its
  white copies), the whole game 163 of 256 at 56e8f56 (3.10; `docs/ROM_BUDGET.md` 2.4).*
- **The plan [D]**: five steps (section 5): A data, descriptor, flow and bench; B the logic ∥ C the
  sprites and the play field; D the boss, the end and the sound; E acceptance.

## 2. The original

### 2.1 The way in [V]

`load_level2` `$8524` (REA listing), after level 2's end (`$8050` = 2, load-table entry 6):

| Address | What | Port |
|---|---|---|
| `$8524` | the statistics `$85D8` | `front_stats` (as after level 2 today) |
| `$8528` | `moveq #2,D0` and three `nop`s (a removed call) | nothing |
| `$8530` | `clr.b $857F` (`sperma_resident`: DATAL3 overwrites SPERMA) | nothing (ROM data) |
| `$8536`-`$853E` | Brainstorm `$8382` (D0 = 4), the range `$8420` (D0 = 5): the second visits | `front_bonus` (built) |
| `$8542` | the level-3 briefing `$110B4` through `$10762` (411 calls) | `front_brief` `txt_l3_brief` (built, 412 VBLs) |
| `$854E` | PIC7 (`$11E06`, D0 = 6) | **dropped** (decision 5) |
| `$8556`-`$8568` | interrupts off, MU1 (`$8614`), DATAL3 (name `$8572`, PP20, A1 = 0: `$28000`) by a tail jump into the loader, which returns into `level_init` at `$8764` | nothing (ROM data); `lv_next` |

- **DATAL3** (`DATAL3_22.bin`, 185,356 B) covers `$28000-$5540B`: it overwrites SPERMA's first 40,322
  bytes; SPERMA's tail `$5540C-$5884D` (13,378 B) stays from level 1, with types 4 and 12's frames
  (`$56076-$5860A`, drawn in level 3). `make ram` builds the image so (Makefile, `934e2f1`).
- **`level_init` `$871A`** takes entry [`$8050` + 4] = 6 for the load (then `$8052` = 2), entry [2]
  `$86DC` (`rts`) after a death or a continue: nothing reloads, the map keeps its changes (as level 2).
- **The header `$86B4`** (`$8664` + 2 × 40; `read_bytes`):

| Offset | Goes to | Level 3 | (level 2) |
|---|---|---|---|
| +0 | `$9C18` object list | `$AA3A` | `$A828` |
| +4 | `$915E` hazard list | `$95EC` | `$95B2` |
| +8 | `$8B54` special objects | `$9008` | `$8FE0` |
| +12 | `$B0E` spawn list | `$99E2` | `$97B0` |
| +16, +18 | the start (RoboCop and the camera) | (1184, 784) | (352, 784) |
| +20, +22 | `obj_relocate`'s target | (224, 544) | (192, 112) |
| +24 | `$C598`, `$C692` marker table | `$C624` | `$C5EC` |
| +28 | `$B08` the camera's lowest y | 624 (50 rows) | 624 |
| +30 | `$804A` timer (BCD) | 7:30 | 7:30 |
| +32 | `$16B8` spawn delay | 3Ch | 2Eh |
| +34 | `$C53D` marker mask | **3** (every 4th frame) | 7 |
| +36 | the palette (the fade's source) | **`$10036`, level 2's** | `$10036` |

- **What changes per level in the code** (the tests of `$8050`, `docs/LEVEL2.md` 2.2):
  - `$88AC` (`level_init`, level 3 only): `$15CA` set (the level started: **no gun-opening sequence**),
    aim `$15DA` = 5, `$15DE` = 4, state `$15E2` = 6, and `$F89D` = 0Bh: the fade-in forces state
    11 instead of 10 [V: listing; the bench starts in state 6, then 11 during the fade];
  - `$8EB0` (the lift's look: two parts, 2.3);
  - `$91A4` (the hazard dispatch `$91B0` + 4 × 2: **`level_tick_2` `$9436`**).
- **What carries into level 3**: as into level 2 (`docs/LEVEL2.md` 2.2): the score, lives, credits,
  `$8060` (the second range's rating), the code-area variables `level_init` does not patch. Level
  3's own code-area state is in 3.4.

### 2.2 The map, the tiles and the palette [V]

| What | Where | Size |
|---|---|---|
| tile sheet | `$28000-$37FFF` | 512 slots; `msxconv.py` keeps 505 distinct MSX tiles (64,640 B) |
| map | `$38000-$3BE7F` | 160 × 50 words: 485 tile offsets (481 MSX tiles) |
| level 3's BOBs | `$3BE80-$5540B` | 88,460 B: the boss `$3BFC0-$45E30`, type 21 `$46970-$4D540`, type 38 `$4D680`, the others to `$552CC` |

- **Attributes** (a read of the map words): 0 (7,086 cells), 1 (87), 2 (185), 3 (14), 9 (622), 13
  (6). Floors (bit 3) on rows 7 (the roof, columns 4-87), 20, 25, 30, 35, 40 and 49 (the ground).
  RoboCop's y on a floor is the row × 16.
- **The route** [I: the map render `level3.png` and the boss drives]: the Civic Centrum's facade
  bottom left (the start), the building's floors with the beams (columns 1-76), the roof (row 7), a
  gap, the car park on the right (columns 89-159: rows 20-49, cars, "EXIT" barriers).
- **The tile cache's need**: at most **106 distinct map tiles in the V9958's 19 × 14 kept window,
  102 in the V9938's 17 × 14** (level 2: 107 and 103) [V: a scan of `level3.map`]; the writers' tiles
  (the beams' words, the turrets' and crates' looks) add at most about 40 [E].
- **The palette** [V: `tools/msxlvpal.py palette` on DATAL3]: level 3's header points at `$10036`,
  level 2's palette; `level_init` loads no other. **Palette C comes out byte-identical to level 2's**
  (`level3.pal` = `level2.pal`, the same remap): `000 432 455 344 333 000 111 234 222 555 210 015 100
  012 500 630`, entries 9, 11, 13 changed from level 1's. Mean ΔE76 over level 3's map: **C 2.179,
  A (level 1's as it is) 2.675**. The largest errors are the same colours as in level 2: c11 (0.20 %
  of the pixels) 27.7, c12 (1.74 %) 20.6, c14 (1.15 %) 17.0, c5 (1.07 %) 16.6 (52.9 under A).
- `tools/msxconv.py level DATAL3_22.bin --rows 50 --joint level3` gives `.map` 16,000 B, `.atrp`
  4,016, `.otile` 1,024, `.atr2` 320, `.til` 64,640 (505 tiles), as level 2's shapes.

### 2.3 The map writers, the hazards and the special objects [V]

**The map objects** (`$AA3A`, 15 entries of 12 bytes; activator = word `$9D96` + map type):

| Entries | Map type | Activator | Place (x, y) | What |
|---|---|---|---|---|
| 0, 1 | 60h, 64h | `act_10` `obj_relocate` (ported) | (272, 704), (240, 256) | two relocations to the header's (224, 544) |
| 2-11 | 6Ch-7Ch | `act_08` explode at look 4 (ported) | ten crates on the building's and the car park's floors | pickups 28 (energy) ×4, 16, 24, 8 ×3, 32 |
| 12-14 | 80h, 80h, 84h | **`act_20` `$9F74`** (16 B, new) | (1552, 480), (2480, 320), (2560, 640) | switched on once `$16A9` is set (type 22 sets it while RoboCop and Cain are both outside x 690h-9D7h); looks `$A292`, `$A2A6` |

- **The beams** (`level_tick_2` `$9436`, 178 B; records `$95EC`: x, y, window x, rows − 1): (416,
  496, 2), (416, 336, 2), (480, 336, 2), (544, 336, 2), (928, 192, 6), (992, 192, 6), (1056, 192, 6),
  each with window x 1472 (`$9150` runs a record while camera x + 73h ≤ 1472 and x < camera x +
  1A0h). They differ from level 1's (`$933A`):
  - **two cells wide**; on for 32 game frames, off for 32 (game frame bit 5; level 1's bit 4);
  - on: the top row from the longs `$94C0` by random & 6, every row below from `$94D0`/`$94F0` by
    (random + x) & 1Eh; off: 1900h/1880h on top, 1800h/1780h below;
  - RoboCop's x in x − 8 ... x + 15 and his y at most (r + 3) × 16 below the top (r = the record's
    rows − 1): the palette flash `$10074`, **energy − 0Ch** a frame (level 1's − 10h), effect 22h;
  - r + 2 rows written in all.
  - Cells: 4 × (4 × 2) + 3 × (8 × 2) = **80**, all map patches.
- **The turrets** (types 40, 41, 42) write two blocks of 2 × 3 map words every frame they run: a
  flashing panel at x − A0h (41: − 70h; `$EAA6`, looks `$EAE2`) and the turret one row lower and 10
  (41: 7) columns to the right (`$EA50`/`$EBB8`, looks `$EA6A`/`$EBD2`): 36 cells. Beside the beams
  and the map objects they are the only map writers [V: the coverage's writers into `$38000-$3BE7F`:
  `$9498`-`$952C` (beams), `$9CF0` (map objects), `$EA58`-`$EBC8` (turrets)].
- `tools/mapcells.py --level 3` must count the pools (the beams' 80 + the turrets' 36 + the objects'
  cells; level 3 has no vats) against 2 × 255.

**The special objects** (`$9008`: three records, handler 0, `special_lift` `$8DE6`): L0 (319, 484)
path 404-484 (`$911E`), L1 (1215, 404) path 324-404 (`$912E`), L2 (1215, 564) path 484-564
(`$913E`). With `$8050` = 2 the lift is drawn **in two parts** (`$8ED2`): `$5397C` 32 × 29 at (x +
20h, y − 52h), then `$53BC0` 32 × 16 at (x + 20h, y − 4). No vehicle, no trolley.

### 2.4 The objects [V]

**The spawn list** `$99E2` (39 entries of 14 bytes; end word at `$9C04`):

| Entries | Type | Where (x, y) | Flags, reload |
|---|---|---|---|
| 0, 1, 2 | 41, 40, 42 (turrets) | (576, 496), (832, 496), (1120, 496) | 0, 999 |
| 3-8 | 47 (camera modes) | (1234, 765), (208, 496), (241, 32), (2546, 432), (1569, 592), (2546, 752) | 0, 999 |
| 9, 10, 14 | 35 | (928, 765), (672, 765), (544, 765) | C0h, 999 |
| 11, 15, 19, 21 | 21 | (992, 736), (336, 736), (256, 272), (672, 272) | C0h, 900 |
| 20 | 21 | (352, 64) | 40h, 900 |
| 12, 13 | 33 (the truck) | (608, 736), (784, 736) | C0h, 200 |
| 16, 17, 18 | 36 | (1328, 257), (1328, 465), (160, 480) | 0 / 0 / 1, 256 |
| 22, 23, 24, 34 | 38 | (2224, 416), (1824, 416), (1856, 576), (2176, 720) | 0, 50 / 50 / 20 / 10 |
| 26, 27, 29, 33 | 39 | (2128, 240), (2336, 240), (1536, 752), (1984, 736) | 0, 50 / 40 / 20 / 10 |
| 25, 28 | 52 | (1840, 240), (2272, 576) | 0, 50 / 30 |
| 30, 31, 32 | 48 (Cain's burst timer) | (256, 32), (1152, 32), (1664, 736) | 0, 50 / 50 / 60 |
| 35 | 43 (markers off) | (768, 40) | 0, 30 |
| **36** | **22, Cain** | **(1280, 56)**: the roof | C0h, 900 |
| 37, 38 | 50 | (944, 408), (688, 408) | 40h, 999 |

**The markers** `$C624` (6-byte entries [bands, type, y offset]; every 4th frame, mask 3):
(7, 0, 0), (3, 34, 40), (7, 0, 0), (7, 4, 69), (7, 0, 0), (2, 37, 48), (1, 12, 62), (2, 37, 48),
(7, 0, 0), (2, 51, 49). **Type 0 spawns nothing** (`$C6F8` writes type 0: a free slot): the (7, 0,
0) entries thin the spawns. The scan wraps through the pointer `level_init` patches into the
`lea` at `$C690` (`$C692`), and **type 43 points both `$C598` and `$C692` at `$C662`**, a table of
two (7, 0, 0) entries: no more marker spawns from the roof on.

**The types** (descriptor `$BEA6` + 16t: width, height, score, handler, death, hit-point class;
hit points at GOOD; size = the REA function body; the coverage saw all but 46):

| Type | What | Handler | Size | Death | w × h | Score | Class (GOOD) | Frames (bench) |
|---|---|---|---:|---|---|---:|---|---|
| 21 | big walker: walks for 32 frames (a step every other frame), then stands facing RoboCop for 32; four shots every 128 frames (bullet 5 leftwards, 6 rightwards); pushes RoboCop 8 px (`obj_push` `$EF18`) | `$D2FA` | 290 | `$C3A8` | 50 × 52 | 1250 | 6 (4) | legs 64 × 40 × 8 per side (`$46970`, `$49FF8`), torso 48 × 28 × 2, head 32 × 16 × 2, muzzle flash (PERMA) |
| **22** | **Cain as RoboCop 2** (2.5) | `$D49C` | 764 | `$C25C` | 48 × 50 | 5000 | 7 (99) | legs 48 × 44 × 18, 64 × 34 × 2, 64 × 32 × 6, 48 × 16 × 4, 32 × 40 × 5, flash 16 × 16 |
| 33 | the truck: drives right 3 px a frame, fires bullet 16h once (24 frames after it comes, RoboCop to its right), effect 24h | `$E0A4` | 232 | `$C360` | 49 × 48 | 1500 | 4 (3) | body 80 × 48, cab 32 × 50, parts 48 × 24 × 2, wheels 32 × 24 × 4 |
| 34 | small walker aiming by `aim_cell` `$D0A6`, bullet 3; effect 23h | `$E1D6` | 182 | `$C35A` | 32 × 32 | 950 | 2 (2) | 32 × 8, 32 × 28, 32 × 24, 32 × 16 parts |
| 35 | gunner that rises and sinks, bullet 3; **hit points put back to 3 every frame** | `$E28C` | 190 | `$C31E` | 24 × 32 | 950 | 7 | 32 × 8, 48 × 18, 48 × 28 |
| 36 | robot on a 60-frame up-and-down cycle, its muzzle smoke (explosions 6/7) and bullet 3 twice a cycle, effect 25h; turns at map word 2D00h | `$E356` | 240 | `$C35A` | 30 × 32 | 500 | 6 (4) | 32 × 38 × 2, 16 × 16 legs |
| 37 | flying machine: follows RoboCop (speeds ±10/4), bursts of bullet 3; one a frame (`$E46E`) | `$E470` | 470 | `$C35A` | 31 × 32 | 650 | 2 (2) | body 32 × 32 × 3, rotors and guns 16 × 16 |
| 38 | homing missile from the mailbox (2.5): 96 frames, steers by `aim_cell`; touching RoboCop − 18h | `$E6D6` | 220 | `$C35A` | 16 × 16 | 350 | 2 | 16 × 16 × 16 directions (`$4D680`) |
| 39, 52 | bomb from the mailbox: thrown by the tables `$E7F8`/`$E8C8`, falls to the floor; 96 frames; − 18h; effect 25h | `$E7D2`, `$E8A2` | 186 each | `$C35A` | 16 × 16 | 350, 450 | 2 (2), 1 (2) | `$4D680` frames |
| 40, 41, 42 | wall turrets drawn into the map (2 × 3 cells); open when RoboCop comes within 32h (41: 28h) px (effect 28h), fire leftwards every 16 frames (40 and 42, which enters 40's code: bullet 11h, the 48 × 16 rocket, **40h**; 41: bullet 3); one of each at a time (`$16A6-$16A8`); destroyed: their wreck look, explosion 0, 40 and 42 drop energy (pickup 1Ch) | `$E98C`, `$EB0A`, `$E972` | 196, 178, 26 | `$C35A` | 32 × 40 | 1500 | 6 (4) | none (map words); bullet 11h 48 × 16 × 2 |
| 43 | trigger: markers off, `$16D7` = 0, camera y offset − 70h | `$EC02` | 32 | `$C1FA` | — | 0 | 0 | none |
| 46 | trigger: spawn delay and marker mask 0 (never spawned in level 3) | `$EE22` | 14 | `$C1FA` | — | 0 | 7 | none |
| 47 | trigger: camera mode x & 15 into `$15C4`, offsets from `$EE52`: 108h/− 70h, B0h, 130h | `$EE30` | 34 | `$C1FA` | — | 0 | 7 | none |
| 48 | trigger: `$16B4` = FAh (Cain's bursts) | `$EE5E` | 10 | `$C1FA` | — | 0 | 7 | none |
| 50 | gunner that stays put, bullet 3 every 64 frames | `$EEE2` | 54 | `$C35A` | 32 × 15 | 750 | 3 (3) | 32 × 38 |
| 51 | walker, bullet 3 at random times (random vy), effect 23h | `$EE68` | 122 | `$C35A` | 37 × 49 | 750 | 3 (3) | 48 × 49 × 2 |
| 4, 12 | level 1's gunners (markers) | shared | — | `$C31E` | | | | SPERMA's tail |

- **Level-3-only code**: the types above (3,724 B), the deaths (198), `debris_add` `$C398` (16),
  `obj_push` (42), the beams (178), `act_20` (16), the two-part lift (48): **4,222 B** [V: REA
  bodies]. Type 38's flight `$E722-$E7B1` is the code level 2's `t49` already ported (`homing_body`).
- **Seen on the bench**: every type but 46; type 38's flight only in the boss drives (the coverage
  scenario leaves the car park's missiles waiting: 66 of its 220 bytes ran there).

### 2.5 Cain (type 22) and the level's end [V]

- **Spawn**: entry 36 at (1280, 56) on the roof, once at the screen's edge (C0h); at its first frame
  "CHASE CAIN" (`$D46C`) and, once a life (`$16D4`), its x into the code-area word `$D798`; a second
  spawn in the same life frees itself (`$D478`). Seen on the bench at game frame 243 of the drive
  that walks the roof from x 900 (Cain at x 1237, RoboCop at 1176).
- **The chase** [V: bench; I: the reading of `$D4CE-$D586`]: its x follows a target ahead of RoboCop
  (x − BAh − RoboCop's x, through the camera mode `$15C4` of type 47), its step mask chosen by
  distance from `$D494` and **patched into the `moveq` at `$D582`** (FFh: it stands, `$16DA`); it falls
  through floors (`obj_fall` at y + 43h). In the drives it ran from x 1237 to 2440 and down from y 56
  to 255 (row 20) while RoboCop followed, and stayed there launching bombs (39) and homing missiles
  (38) when RoboCop was put on the ground floor.
- **Invulnerable high up**: while its y < 290h (656) its hit points are set to **2Ch every frame**
  (`$D6DE`); below, 45 hits kill it (the class-7 table gives 99 at spawn).
- **Its attacks**: while `$16B4` runs (250 frames from a type-48 trigger), every 64 frames a burst
  of 16 shots in 32 frames, bullet 9 (rightwards, direction 4) or 0Ah (leftwards, 0Ch) by its
  facing, with its muzzle flash; effects 27h (steps) and 0Eh; every frame **the launch mailbox**
  `$E67A` (direction: random & 15 + a table), `$E67C` (x + 18h), `$E67E` (y − 2): the waiting spawn
  entries of types 38, 39 and 52 take it (its only writer is `$D72C`: REA xrefs of `$E67C`).
- **Drawing**: four parts through `$AC44`/`$AC56` (all white on a hit) and the muzzle flash through
  `$AB08`: legs `$3BFC0` + `$D7EE`[step] (48 × 44, or 64 × 34 at `$3EE28`, the standing pose at
  `$3E900`), `$40278`+ (48 × 16, +1E0h in some frames), `$40638`+ (32 × 40; the hit look for 6
  frames, `$16D9`), `$3F378`+ (64 × 32 by its fire counter), the other side's set from `$41498`.
- **The death** `$C25C` [V: the kill drive, Cain put low with 1 hit point at game frame 820]: three
  debris bullets (types 12h, 13h, 14h: its parts thrown up), three explosions of type 0, **`$16D0`
  set, `$16C4` = 40h, "CAIN DESTROYED."** (`$C24B`). Then `main_loop`'s end as in levels 1 and 2:
  65 frames of the count, the fade, `$8050` = 3 (`$81B8`), `level_init` (the bench stopped there 94
  frames after the death).

### 2.6 Bullets, debris, explosions and damage [V]

| Bullet type | Fired by (level 3) | Graphics (`$F4A4` + 4t) | Damage (`$FA63`) | Box |
|---|---|---|---:|---|
| 3 | types 34-37, 41, 50, 51 | `$6D2A0` (PERMA) | 6 | 8 × 8 |
| 5, 6 | type 21 | `$6D3E0`, `$6D480` | 0Ch, 6 | 8 × 8 |
| 9, 0Ah | type 22 | `$413F8`, `$468D0` | **1**, 1 | 8 × 8 |
| 0Bh-0Dh | death `$C360` (the truck's body, wheel, cab) | `$4F00C`, `$4FD2C`, `$4E684` | 0 | never hits |
| 0Eh-10h | death `$C3A8` (type 21's legs, torso, head) | `$46970`, `$49B70`, `$49EB8` | 0 | never hits |
| **11h** | types 40, 42: the rocket | `$52FCC` (48 × 16) | **40h** | 8 × 8 |
| 12h-14h | death `$C25C` (Cain's parts) | `$40278`, `$40638`, `$3F378` | 0 | never hits |
| 16h | type 33 | `$54F0C` | 8 | 10 × 8 |

- **Debris draws big frames**: the debris bullets draw the dead enemy's 80 × 48, 64 × 40, 64 × 32
  ... frames through `ebullet_update`'s `$AB08`. Explosions: type 0 everywhere, 6 and 7 from type 36
  (`$F366` D5), the smoke of `$C31E` (types 4, 12, 35).
- **Damage to RoboCop in level 3**: bullets by the table; touching an enemy 1 a frame; the beams
  0Ch a frame; types 38, 39, 52 touching him − 18h (their own code, then they explode).
- **The port's rule** (`hits.asm` `phb_en`, after step 1): bullet types 1 and 2 × 1, the rest ×
  `DAMAGE_X`. Level 3 adds **bullet 11h, a rocket with the missiles' 40h** (default 11: × 1), and
  the 18h touches of 38, 39, 52 (default 12: × 1, as level 2's drone `t49_hit`). The beams: a
  hazard, × 1. **Cain's damage × 1** (default 16, 2026-11-01): his bullets 9 and 0Ah, touching him
  and touching his bombs and missiles (38, 39, 52) take the original's 1.

### 2.7 The frames [V: bench]

The coverage and the boss drives drew **202 distinct frames** (address and BLTSIZE;
`l3_frames_drawn.json` in the archive):

| Where | Play field (48 px or more) | Sprites |
|---|---|---|
| DATAL3 | **58**: 48 × 44 × 18 and 64 × 34 × 2 (Cain's legs), 64 × 40 × 16 (type 21's legs), 64 × 32 × 6 (Cain), 48 × 16 × 7 (Cain, the rocket), 48 × 28 × 3, 48 × 24 × 2, 48 × 49 × 2 (type 51), 48 × 18, 80 × 48 (the truck): 116,736 px, 58,368 B at 4 bits | 78, the lift's two parts among them (to the play field: 2.3) |
| SPERMA's tail | — | 12 (types 4, 12) |
| PERMA | 6 (the smoke, level 1's dynamic frames) | 48 (explosions, flashes, bullets, pickups: about 17 of them are explosion frames, which the port draws in the play field) |

- `tools/bobcatalog.py` finds few of them: its scan follows the image of level 1's REA exports, and
  most level-3 sites index PC-relative word tables (`lea (d,PC),A4` + `adda.w (0,A4,D2.w),A2`). The
  catalogue for level 3 is the bench's list (the coverage, `--drawn`) plus REA's tables for frames
  the drives did not reach (3.5, step C).
- Exact mirrors: the left and right sets of types 21, 22, 33's wheels and 51 are separate frames
  (the converter's `bob_mirrors` checks them).

### 2.8 The sound [V]

- No music in level 3 (MU1's effects only, as in levels 1 and 2). Requests in level-3 code (REA
  `search_bytes 11 fc 00 ?? 0b ??` over the main code): `$9474` 22h (beams), `$D540` 0Eh and `$D5A4`
  27h (Cain), `$E0AC` 24h (truck), `$E1DE` 23h (34), `$E400` 25h (36), `$E824`/`$E8F4` 25h (39,
  52), `$E9D0`/`$EB4E` 28h (turrets), `$EE70` 23h (51); the lift's 0Ah, the bullets' and explosions'
  own tables. All are MU1 effects 0-41, already converted (`sound.inc`, the SCC effects): **no new
  sound data**. 0Eh, 23h-25h and 27h have not been checked per tick before (step D).

### 2.9 The end of level 3 and the hand-over [V]

- `level_init` with `$8050` = 3 (`$8052` = 2) takes entry 7: **`level_load_3` `$86DE`**: the text
  screen `$112C5` ("YOU HAVE DEFEATED ROBOCOP 2, / AND THE SUPPLY OF NUKE HAS BEEN / STAMPED OUT.",
  341 calls) through `$10762`, `$11C54` (PICF and the CMP tune), `high_score_entry` `$12082`, `bra
  $8090` (the title). **No statistics and no bonus stage** after level 3.
- **What it hands over**: AG's score `$8046-$8049` (with the end count's +100 × 65), lives, credits;
  `$8050` = 3. The ending (WELL DONE, CMP, the high-score table and its entry) is **step 3's**; level
  3's steps own only the hook in `ml_ev` (3.1).

### 2.10 Quirks a faithful port keeps [V unless marked]

| # | Quirk | Port |
|---|---|---|
| Q1 | Cain's hit points are 2Ch again every frame while his y < 290h: shots high up never kill him | kept |
| Q2 | Type 35's hit points are 3 again every frame: only 4 hits in one frame kill it | kept (as level 2's suspect) |
| Q3 | Type 22 patches its own `moveq` immediate (`$D583`), type 40 its `addq` register (`$E9F5`), type 43 the markers' `lea` operand (`$C692`), `level_init` the same | variables (3.4) |
| Q4 | The launch mailbox is taken by the first waiting type 38, 39 or 52 in slot order; Cain writes it every frame, so waiting entries launch one a frame; entries that wait 96 frames free themselves and come back by their reload | kept |
| Q5 | The marker table's type-0 entries spawn nothing (a slot written with type 0) | the port's marker code must do the same (step B's traces) |
| Q6 | Turrets 40 and 42 share code (42 enters 40's at `$E9A0`); one of each at a time (`$16A6-$16A8`, cleared at each life) | kept |
| Q7 | `act_20`'s objects open only once `$16A9` is set by Cain [I: never set before Cain comes] | kept |
| Q8 | The beams hurt 0Ch a frame for 32 frames on, 32 off; level 1's 10h, 16/16 | kept |
| Q9 | Cain's debris and the truck's and type 21's parts are enemy bullets that never hit (box 9Dh) | kept |

### 2.11 Where Cain attacks [V: bench and the MSX traces, 2026-11-01]

A play-tester's report ("Cain randomly stops firing his missiles, and RoboCop can shoot him forever")
is the original's design (Q1, Q4, Q7).

- **His attacks are tied to places, not to Cain.**
  - He never fires a projectile himself: he only writes the mailbox (2.5).
  - Ten fixed spawn entries make the projectiles (22-29, 33, 34: x 1536-2336, one or two a floor).
    An entry counts down only while it is inside the window (x − camera x in (5Dh, 1AFh], y −
    camera y in (−28h, A8h], `$C454-$C492`); outside it is reset (`$C522`).
  - His bursts need `$16B4`, which only the type-48 entries set: 30 and 31 on the roof, 32 on the
    ground floor (`$EE5E`; at most one burst per 128 frames, `$D526-$D534`).
  - The random word feeds only his heading, bullet y and flash frame (`$D716`, `$D75A`, `$D782`),
    never a spawn, launch or burst decision.
- **Where**: with the camera settled, RoboCop's x (while walking the stretches shift by up to about
  30 px):

  | Floor (camera mode) | Attacks | Idle (Cain stands and never attacks) |
  |---|---|---|
  | Roof (1) | bursts at x ≤ 1234 (entry 31) or ≤ 338 (entry 30), and 250 frames after leaving | beyond 1234; no projectiles on the roof |
  | 20 (1) | bombs at 1585-2418 | 2419-2541 (the floor's end) |
  | 30 (2) | missiles at 1697-2034 and 2097-2434 | 2035-2096, 2435-2640 (the landing), below 1697 (the end) |
  | 40 (1) | 1601-1938 and 2017-2354 | below 1601, 1939-2016, 2355-2526 (the end) |
  | Ground (2) | projectiles at 1409-1746 and 1857-2386, bursts at 1537-1874 | 2387-2640 (the landing) |

- **Each floor's end is idle, and it is where the player must go**: a floor opens once RoboCop and
  Cain are both outside x 1680-2519 (`$16A9`, `act_20`, Q7): floors 20 and 40 at RoboCop's x ≥ 2520,
  floor 30 at x < 1680. Both then fall. A player who lingers in an idle stretch waits until the
  7:30 time out; `INVULN=1` skips the time out, so there it can last for ever.
- **He dies only on the ground floor** (Q1: y 56, 255, 416, 578 above; 719 there): 45 hits.
- **The port's check**: 11 drives (60 s lingering at chosen places, wandering, `drivejoy --fuzz`)
  give 0 differences against the bench on the trace build (`tracecmp --ram`, 780 fields a frame).
  With the product's options (`EXTJOY=1 LV_TEST=3 CHEAT=1 INVULN=1`) every spawn, launch, burst and
  `$16B4` reload has the bench's frame, slot and place:
  - 11 drives on the Expert, 3 each on the HB-F1XDJ and the FS-A1GT;
  - with the time-out flag set, as in the play-tester's state (timer 0:00).
  - The only difference is Cain's own entry 36: `ENEMY_CAP` skips it while he lives, so it keeps
    its count, where the Amiga resets it out of the window. It is harmless, since he spawns once a
    life.
  - The spawn walk's masks (`tools/cellmasks.py`) leave out no entry inside the window at 6,080,000
    camera places.
- **What the MSX shows differently** (display only):
  - At 7-8 ticks a second (Expert) the gaps between attacks last about 3 times longer.
  - In camera mode 2 the MSX shows 47-52 % of Cain's width (the Amiga 82-86 %): `pl_view` keeps
    RoboCop at screen x ≤ `AX_MAX` 160, and Cain stands 170-200 px behind him.
  - The 8-sprites-a-line budget leaves out 22-38 % of his burst bullets' pictures and 3-12 % of his
    projectiles' (RoboCop 5 + Cain's 32 × 40 part 3).
- **The user's decisions** (2026-11-01):
  - The logic stays the original's ("vamos manter a lógica", default 17).
  - Camera mode 2's view stays as it is ("a que for mais performaticamente economica", default
    18). The field engine composes only what its page keeps: `fn_rect` skips an item that
    `fb_clip` leaves empty, a V9938 page keeps 256 px and the V9958's ring 19 columns. A white
    copy is fetched (`fc_get`) only for a BOB it composes. So a view showing more of Cain could
    only add VDP work, in the game's slowest scene.
- Records, drives and tools: `build/archive/cain_2026-11-01.tar.gz` (local).

## 3. The MSX design

### 3.1 Level 3 in the engine [D]

- **The descriptor's third entry** (`gen/levels.inc` `lv_desc3` = `lv_desc` + 2 × `LV_SIZE`): `BANK_L3`,
  `L3_TILES`, `L3_MAP`, 50 rows, `L3_ATR`, `L3_ATRN`, `L3_TAB`, `L3_ATLAS`, its dynamic slot, (1184,
  784), 624, 638 (800 − 162), 800, `L3_PALP`/`L3_VOFFP` (in `L3_TAB` at A000h: level 2's graded palette
  bytes again, its own `view_offy`), `lv_sidx` (level 3's index in the pool), `lv_spark`, `lv_dynp`,
  `lv_tcn` −160, `fld_l3`, and **`lv_fid0`** (3.5): `LV_SIZE` 33 (F1A0h-F1C0h; F1C2h stays `lv_vram`).
- **The start**: `lv_go` with A = 2 (`lv_select` copies the third descriptor; uploads page 2 and the
  atlas since VRAM holds another level's); `l3_init` (the level bank) does `level_init`'s level-3
  part: the lists from the bank (fresh starts), the header's values (timer 7:30, delay 3Ch, mask 3,
  the relocation target), **`$15CA` set, aim 5, `$15DE` 4, state 6, the fade's forced state 0Bh**
  (the port's `$F89D`), `set_weapon(0)` on fresh starts (as `l2_init`). *As built: the fade's state is
  a variable, `fade_st` (3.9).*
- **The flow** (`rc2.asm` `ml_ev`, fixed area): `$8050` = 3 goes first to **step 3's ending** (no
  statistics, no stages: `level_load_3`), then the title; `$8050` = 1 or 2 runs `front_stats`,
  `front_bonus` (the stages and `front_brief`, built for both briefings) and `lv_next` (A =
  `$8050`). Today's `dec a` / `jr nz,ml_ttl` goes (−4 B), the test for 3 comes (+8 B). *As built:
  `ml_ev` +1 B and `ml_end` 3 B (3.9).*
- **Deaths and the continue**: as level 2 (`level_restart`, `lv_cont`: the level's VRAM again, the map
  kept). The continue offer can come in level 3 (credits from both Brainstorms).
- **Test builds**: `LV_TEST=3` (start in level 3 at power-on, after its briefing, with `LV_CARRY`);
  `CHEAT=1`'s F5 ends level 3 (the ending), F4 fills the energy.

### 3.2 Banks and code room [D, E]

**Free bytes now** [V: `tools/bstest/build.sh` and `l2base.py banks` at `2b44ca5`; step 1's `07b2436`
in its worktree]:

| Bank | Product | `LV_TEST=2 CHEAT=1` | Lowest set (`DIAG=1 PZ_TEST=1`) | After step 1 (product, lowest) |
|---|---:|---:|---:|---:|
| fixed area | 181 | 162 | 46 | 196, 89 |
| LC1 | 53 | 53 | 53 | 54 |
| LC2 | 4,842 | 4,842 | 4,842 | 4,842 |
| `BANK_L1` | 874 | 874 | 874 | 874 |
| LC3 | 4,866 | 4,833 | 4,866 | 4,866 |
| INPUT | 11 | 11 | 11 | 11 |
| FRONT | 1,381 | 1,326 | 983 | 1,381, 985 |
| `BANK_FIELD` | 143 | 143 | 143 | 150 |
| MUSIC | 1,331 | 1,331 | 1,280 | 1,331 |
| `BANK_L2` | 28 | 28 | 28 | 28 |

*As built: the banks in 3.9 (step A) and 3.10 (step C: 163 of 256 banks, `place_banks`); the free
bytes at 56e8f56 and level 3's real cost in `docs/ROM_BUDGET.md` 2.4.*

**What level 3 adds where:**

| Piece | Bank | Bytes [E] |
|---|---|---:|
| `ml_ev`'s two tests, `l3b_call` (a `field_call` for `BANK_L3B`: or `field_call` made `a000_call` with A = bank), `lv_fid0`'s two reads in `bob.asm`, the debris routing (3.5) | fixed area | +30 to +45 |
| `lv_desc3`, `front_l3test` (`LV_TEST`) | FRONT | +33, +25 (test builds) |
| `act_20` | LC2 | +30 |
| the two-part lift in `sp_lift` | LC3 | +60 |
| the dynamic frame cache, the white flash, `fld_l3` | `BANK_FIELD` | +400 to +700: **room first**: the vats' display section (`vat_init` ... `vat_dst`, at least 1,017 B from BB78h to `field_end` BF71h) assembled only with `VAT_ANIM=1` (default 9) |
| `BANK_L3`: the header (240 B), `lvshared_l3` (1,585 B at level 1's addresses), `l3_init`, `lt2` (beams), the deaths and `debris_add`, `lv_noten`, the stubs into `BANK_L3B` (19 × 6 B), the lists and tables, `cells_l3.inc`, `at_l3.inc` | new bank at A000h | about 5.5 KiB |
| `BANK_L3B`: the 19 new types, `obj_push`, the turrets' map writes, their tables | new bank at A000h | about 6.5-7.5 KiB (level 2's ratio 1.7 Z80 bytes per 68000 byte) |

- **Why two banks**: 4,222 B of new 68000 code at level 2's measured 1.7 is about 7.2 KiB, plus the
  header, the shared copy and the tables (about 4.4 KiB): 11.6 KiB. The new types call only fixed
  and LC1 code (`bob_part`, `bob_draw`, `ebullet_add`, `obj_walk`, `obj_fall`, `aim_at`, `map_cell`,
  `pal_flash`, `pickup_drop`, the explosion spawn), never `BANK_L3`'s, so they can live in a bank of
  their own: `lv_htab` points at 6-byte stubs in `BANK_L3` (`ld hl,tNN` / `jp l3b_call`) that map
  `BANK_L3B` at A000h around the handler and give `BANK_L3` back, as `field_call` does for
  `BANK_FIELD`. Calls cost about 100 T each, 5 slots × 25 a second.
- **The ROM** [E]:

| Block | Banks |
|---|---:|
| levels 1-2, the stages (today) | 127 (0-126) |
| `BANK_L3`, `BANK_L3B` | 2 |
| level 3's tiles (the 64 KiB VRAM image), map (2 banks of 25 rows), attributes, tables | 8 + 2 + 1 + 1 |
| level 3's atlas (static play-field frames) | 1-2 |
| level 3's big frames for the cache (48 KiB, both sides stored: no flip at run time) | 6-7 |
| the pool's growth in place (about 300 patterns: +1 pattern bank; records +1) | 1-2 |
| **level 3** | **22-25** |
| step 3's ending (CMP in three chip versions 4, its code and texts 0-1) | 4-5 |
| **the whole game** | **about 153-157 of 256** |

- **The 2 MiB image** from the first block past bank 127: `rom_banks` gives 256, the boot guard's
  tag goes into bank 255 (`GUARD_AT`), and every candidate is 2 MiB (the user's minimum device).
- **The 3Fh rule**: banks 127, 191 (and 255's tag) may hold only data never mapped at 8000h.
  `mkrom.py`'s `a000_only` today holds the pictures only; it must learn the blocks read at A000h only
  (`BANK_L3` and `BANK_L3B`, mapped by `lvl_bank` and `l3b_call`; the map banks only if every reader
  maps them at A000h) so that one of them can take bank 127 (default 13; else pad). Every build checks
  it (mkrom's error). *As built: the ending's `BANK_FRONT2` holds bank 127; `place_banks` would give
  191 to `BANK_L3` or `BANK_L3B` (3.9, 3.10).*
- **The SCC test values** (banks 36, 63, 90, 137, 191 at 1800h in a 2 MiB image): data-dependent,
  checked by mkrom on every build; the pool's shift moves what sits there: reorder or pad when one
  fails.
- **The pool in place**: the global pool (`sprites.bin`, banks 21-47) grows by its level-3 share and
  every later block shifts once, as level 2's step 12 did: `tools/bstest/romdiff.py --blocks` (every
  data block identical at its new bank) and `relocheck.py` (the code banks differ in bank operands
  and moved labels only).
- **The Pico+'s speed target** (`docs/PICO_CACHE.md`, at most 53 banks selected in a level) [E]:
  fixed 2, the code banks 8, level 3's map 2 and tables 1, logic 2, the pool's banks its frames use
  (up to about 25), the big frames 7-8, level 1's dynamic frames 2, the SCC effects 1, the HUD 3:
  about 52-54. Group each type's big frames in the fewest banks (the boss's in four); measure with
  the bank-select log (level 2's 4.4). A device quirk sets a speed target only.

### 3.3 The logic [D]

Routine by routine, in the AM mirror's layout, traced against the bench:

| Amiga | Port | Bank | Notes |
|---|---|---|---|
| `level_init` `$871A`'s level-3 part, `$88AC` | `l3_init` | `BANK_L3` | 3.1; the lists and the code-area state from the bank on fresh starts |
| `level_tick_2` `$9436` | `lt2` | `BANK_L3` | `lt0`'s pattern (`level1.asm`), two cells wide, 32/32 frames, − 0Ch × 1, `map_write_lin` per cell (80 cells counted in the pools) |
| `act_20` `$9F74` | `act_20` | LC2 | `ao_acts` entry 8 (today `ao_look`) |
| `$8ED2` (lift, `$8050` = 2) | `sp_lift`'s two parts | LC3 | two BOBs, both `FIELD_LATE` (RoboCop rides them) |
| types 21, 22, 33-43, 47, 48, 50, 51, 52 | `t21` ... `t52` | `BANK_L3B` | 39 and 52 one routine with their tables; 40 and 42 as the original (42 enters 40); 38's flight: level 2's `t49` code copied; `$EF18` `obj_push`, `$EA50`/`$EAA6`/`$EBB8` the turrets' map writes (`map_write_lin`) |
| `$C25C`, `$C360`, `$C3A8`, `$C398` | `death_cain`, `death_truck`, `death_w21`, `debris_add` | `BANK_L3` | `death_cain` sets AM `$16D0`, `$16C4` = 40h, `HUD_MSG_C24B` |
| types 4, 12 (markers) | the shared handlers | `BANK_L3` (`lvshared_l3`) | `tools/mkrom.py` writes `gen/lvshared_l3.asm` (`_l3` labels; `lvshared_check` already takes `l3`) |

- **ENEMY_CAP** (`lv_noten` in `BANK_L3`; default 10): counted (enemies): **4, 12, 21, 22, 33, 34, 35,
  36, 37, 50, 51**. Not counted: **38, 39, 52** (Cain's projectiles, which draw 16 × 16 sprites: counted,
  they would wait for Cain's own slot and he would never attack), **40, 41, 42** (drawn into the map,
  no sprite or BOB), **43, 46, 47, 48** (triggers that free their slot at once). Effect: from Cain's
  spawn to his death no other counted enemy comes (he holds the one slot; he is never freed by
  clipping [I: as type 2]): the chase is one on one, with his bombs and missiles.
- *As built (3.11): every routine above, 40 and 42 one routine; 10,134 B used in the two banks.*
- *Performance campaign 2 (2026-11-01): `lt2_off` and `tur_put` skip a write of the words their cells
  hold (the map-write caches: `docs/MSX_ARCHITECTURE.md`, "Map-write caches"; RAM 59 B at F170h-F190h,
  ECFBh-ED08h, EDF0h-EDFBh), and the beams and turrets write their looks with the tiles looked up at
  build time (`gen/tt_l3.inc`, `tt_l3b.inc` from `tools/mapcells.py` `look_tables`; `lt2_putt` and
  `tpu_w` call `tiles.asm` `map_write_t` instead of `map_write_lin`: their columns 18-63 never wrap);
  the logic and the map stay the original's tick for tick.*
- **CPU [E]**: a busy tick (type 21 or Cain with three projectiles) about 50,000-60,000 Z80
  T-states, below level 1's measured 74,000; the frame cache's uploads add about 15,000-30,000 T a
  tick while a big enemy animates (about 1 KiB a tick at most), the R800 four times faster.

### 3.4 RAM [D]

| Home | Use | Why free |
|---|---|---|
| DD80h-DFA3h | level 3's spawn list (548 B) | `spawn_ram` (640 B) |
| DD74h-DD7Fh | the code-area state (12 B): `obj22_step` (`$D583`, 1), `obj22_x` (`$D798`, 2), `obj37_last` (`$E46E`, 2), the mailbox (`$E67A-$E67F`, 6), `obj40_flag` (`$E9F5`, 1: 0 = the image's `addq.w #4,D2`) | the free tail of `AC_VARS` (after `ao_cahi`), cleared at power-on only, as the Amiga's code area keeps its words across lives, levels and games; zero is the image's value of each (`$D583` is written before it is read) |
| EE00h-EEB5h | level 3's object list (182 B) | `objl_ram` |
| E900h-E92Fh | the three lifts' records | `SP_RAM` |
| AM | `$15C4`, `$16A6-$16A9`, `$16B4`, `$16D4`, `$16D7`, `$16D9`, `$16DA` | the `$B00-$16EB` mirror (cleared at each life, as on the Amiga) |
| `ac_mkptr`, `ac_mktab` | type 43's two writes (`$C598`, `$C692`) | exist |
| `ac_camdx`, `ac_camdy` | types 43 and 47 (`$B2D8`, `$B2FC`) | exist |
| F1C0h | `lv_fid0` (the descriptor's 33rd byte) | free (F1C0h-F1C1h) |
| the frame cache's table | slot → (frame, white), age: about 24 B | `BANK_FIELD`'s RAM (step C finds the home; `msx.inc` is step A's to edit first) |

*As built: the code-area words in another order (words even) and the frame cache's `fc_tab` at
ECF0h (3.9); `fc_res` holds one byte a place (3.10).*

### 3.5 The play field and the sprites [D]

- **Where each frame goes** (decision 13): the 58 DATAL3 frames 48 px wide or more and the lift's
  two parts into the play field; the other 76 DATAL3 frames as sprites (type 1's joint-composition
  rule, 3 a line at most beside RoboCop's 5, for any 48 × n frame the user would rather keep as
  sprites: none by default). Cain is four play-field parts plus a sprite muzzle flash. *As built
  (3.10): three play-field parts; his 32 x 40 part and every frame under 48 px stay sprites.*
- **Static atlas** (page 3 lines 0-111, as level 2's): the frames that do not animate fast or are
  few: the lift's two parts, type 35's 48 × 18 and 48 × 28, the rocket's 48 × 16 × 2, Cain's 48 × 16
  × 4, type 51's 48 × 49 × 2, the truck's 80 × 48 and 48 × 24 × 2: about 19,100 px, 75-90 lines with
  the converter's shelves [E]. *As built: 18 frames in 109 lines, two banks (3.10).*
- **The dynamic frame cache** (new; page 2 lines 160-231, three rows of 24 lines: 768 px of strips;
  the tile cache keeps 160 slots, `lv_tcn` −160, against the 106 + ~40 tiles level 3 can show):
  Cain's legs (48 × 44 × 18, 64 × 34 × 2) and his 64 × 32 part (× 6), type 21's legs (64 × 40 × 16)
  and torso (48 × 28 × 2): 98,304 px (48 KiB at 4 bits, both sides) in ROM, at most 336 px of strips
  at once (Cain) or 224 (type 21). A frame not in VRAM when the field composes an item that needs
  it is copied from its ROM bank into a free (or the least recently used) place, in strips of 24
  lines side by side as `fb_dyn` does for the explosions today. A place in use by an item in
  flight, or by a page that has still to be composed with it (the V9938's two pages), is not reused.
  *As built (3.10): seven fixed places, one per kind of frame; the frames shown together never share
  one (ENEMY_CAP 1), so nothing is evicted while in use.*
- **The explosions' dynamic slot** stays the engine's (256 × 24), on page 2 lines 232-255 (level 2's
  is on page 2 too).
- **The hit flash**: on the Amiga `$AC44`/`$AC56` draw every part white for the frame of the hit.
  Level 3's play-field frames get it from the cache: the frame uploaded with every non-zero nibble
  turned to 15 (a flag on the upload), so **no sprite silhouettes** (default 6). Levels 1 and 2 keep
  theirs. *As built (3.10): white copies stored in the ROM, in colour 9 (the Amiga's flash is colour 15
  of its palette, (11, 11, 11)), uploaded as any cache frame.*
- **Frame ids**: level 3 needs about 123 sprite ids (76 DATAL3, 12 SPERMA, about 31 PERMA, the spark's
  4) and 83 play-field ids (60 DATAL3, about 17 explosion frames, 6 smoke): 206 of 254. No single
  `FIELD_ID0` serves the three levels (level 2 needs 204 sprite ids, level 3 83 play-field ids), so
  **`FIELD_ID0` becomes per level** (`lv_fid0`: D0h in levels 1 and 2; in level 3 between 7Bh and
  ABh, about 90h, from `msxsprites.py`'s counts; default 7). 16-bit ids (the alternative) would
  change the sprite engine's records and the fixed area far more. *As built: 150 sprite ids, 66
  play-field ids from 98h (3.10).*
- **Debris that draws big frames** (2.6): the bullet class goes to the sprite path today (`bob.asm`
  `bob_flush`: only enemies, specials and explosions reach the play field); a record whose frame id
  is a play-field id must go to the play field whatever its class (a few bytes in the fixed area).
- **The pool**: `tools/msxsprites.py`'s multi-level run gets level 3 (`--l3-datal`, `--l3-bobs`,
  `--l3-ram`, `--l3-pal` = level 2's palette, `--l3-remove msx/level3_frames.json`): level 3's
  index, BOBHASH, ids, atlas, big-frame banks and field tables; levels 1 and 2's records stay
  byte-identical; the frame chooser (`tools/msxchooser.py`) gets a level-3 section.
- **The catalogue**: `bobcatalog.py level3` (as `level2`): the coverage's frames (`--drawn`), REA's
  tables for the frames the drives did not reach (Cain's `$D7EE`/`$D80E`/`$D79A` tables, type 21's
  `$D44C`, the truck's, types 34-37's), the bullets 3-22; every coverage frame must be in it.

### 3.6 VRAM in level 3 [D]

| Area | Level 3 |
|---|---|
| pages 0-1 | the play field (as levels 1 and 2) |
| page 2 lines 0-159 | the tile cache, 160 slots |
| page 2 lines 160-231 | **the dynamic frame cache** (three rows of 24 lines) |
| page 2 lines 232-255 | the explosions' dynamic slot (`lv_dyn`, `lv_dynp` 2) |
| page 3 lines 0-111 | the atlas (static frames), as level 2's |
| page 3 lines 112-255 | caches and scratch, sprites, HUD (unchanged) |

`lv_select` uploads page 2's tiles and the atlas when VRAM holds another level's (`lv_vram`); the
cache starts empty at every level start, restart and continue. *As built: so (3.10); the atlas takes
page 3 lines 0-108.*

### 3.7 Sound [D]

Nothing to convert. Step D logs level 3's requests per tick on the three chip sets
(`tools/bstest/fxcheck.py`, level 2's step 21) and checks them against the bench's.

### 3.8 Tools and the bench [D]

| Tool | Level 3 |
|---|---|
| `Makefile` | `ram` builds `level3_full.bin` with SPERMA (`934e2f1`); `msx` gets level 3's conversions (`msxlvpal.py` palette C, `msxconv.py level`, `mapcells.py --level 3`) and the pool's level-3 arguments |
| `tools/amigaemu.py` | `game --level 3` (**built**, `d0afe4c`): the direct start, `CODE_BLOCKS_L3`; to add: `--flow` through level 2's end (level 2's flow + `load_level2` for real) for `flow_l3` (*not built: `cheat.tcl` checks the flow, `docs/level3/HANDOFF.md` step 4*) |
| `tools/amigacov.py` | `--level 3 --scenario level3` (**built**); to add: a car-park run that follows Cain down |
| `tools/l3drives.py` (new, from `l2drives.py`) | the drives and references: `tour3` (the building, the beams, the lifts, a relocation), `park` (the car park: the truck, the turrets, types 37, 51), `boss` (the roof, the chase, Cain's projectiles), `kill` (Cain down and dead; the level's end), `cont3` (a game over with a credit), `flow_l3` (level 2's end into level 3) |
| `analysis/amiga_ram_l3.tsv`, `tools/tracecmp.py --fields` | level 3's trace fields: `$B00-$16EB`, `$8000-$80FF` and `CODE_BLOCKS_L3` |
| `tools/bstest/hz.tcl` (`hz_l3`), `openmsx_rc2.tcl` (`rc2_l3_arm`) | the MSX trace of `LV_TEST=3` builds, as `hz_l2` (*as built: `hz_l3`, `hz_l3_jobs`; `openmsx_rc2.tcl` unchanged, `rc2_l2_arm` arms at the next `lv_next`*) |
| `tools/cellmasks.py` | `cells_l3.inc` (39 entries: `SW_MAX` 40 holds them) |
| `tools/amitab.py` | `analysis/amiga_tables.tsv` bank `l3`: `spawn_l3`, `objl_l3`, `sp_l3`, `mk_tab3` (with `markers_off`), `hz_l3`, `beam2_*`, the types' tables, copies of the shared tables |
| `tools/mapcells.py` | `--level 3`: the beams' and turrets' cells, `act_20`'s looks |
| `tools/bobcatalog.py`, `tools/msxsprites.py`, `tools/msxframe.py`, `tools/recframes.py`, `tools/msxchooser.py` | level 3 (3.5) |
| `tools/bstest/fieldcheck.py`, `msxreal.py`, `mapcmp.py` | `--level 3` (the cache's frames from the record) |

### 3.9 As built by step A (2026-11-01) [V]

What step A built and where it departs from 3.1-3.8 (the account and the checks: `docs/level3/HANDOFF.md`,
"Step 4 (plan step A)"):

- **The ROM** (on `level2` with steps 1 and 3 in): bank 127 holds `BANK_FRONT2` (the ending's code) and
  128-131 the CMP tune, so level 3's blocks follow from bank 132: tiles 132-139, map 140-141, attributes
  142, tables 143, `BANK_L3` 144, `BANK_L3B` 145; **146 of 256 banks**, 2 MiB with the boot guard.
  `tools/mkrom.py` `place_banks` lays them out: a bank with `(b & 3Fh) = 3Fh` takes `BANK_L3` or
  `BANK_L3B` (both read at A000h only), padding only when it must (the `DIAG` builds, without their
  tunes, pad 126-127). Default 13 thus takes no bank now; bank 191 would take an A000h-only block if
  the image reaches it. Levels 1-2's data blocks are identical at their banks (`romdiff.py --blocks`).
- **The descriptor**: `LV_SIZE` 33, `lv_fid0` +32 (D0h in every level for now). Level 3's (`lv_desc3`)
  takes **level 2's BOB index, spark, play-field tables (`fld_l2`), ids and atlas** (`L3_ATLAS` =
  `L2_ATLAS`) until step C; its BOBHASH holds level 2's frames whose bytes level 3's memory holds too
  (`l3_stub_hash`: PERMA's bullets, explosions, pickups, sparks), so level 3's own frames draw nothing
  yet. Its tile cache 160 slots, its dynamic slot page 2 line 232 (`L3_DYN_Y`), as 3.6.
- **The flow**: `ml_ev` sends AG `$8050` = 3 to `ml_end` (`frontx.asm` `fr_ending`, step 3's ending,
  then the title), 1 and 2 through `front_stats`, `front_bonus` and `lv_next`; step 3's interim
  `fb_brief2` (the ending right after the level-3 briefing) is gone: `front_bonus` calls `front_brief`
  again. `LV_TEST=3` (`front_l2test` = `front_l3test`: AG `$8050` = `LV_TEST` - 1).
- **The fade's forced state** (`$F89D`) is a variable, `fade_st` (DD1Ch): `cold.asm` `ng_init` sets 10
  at each new game, `l3_init` 11 at each level-3 start; `player.asm` `pl_fade` reads it (`ld hl,(fade_st)`:
  no fixed byte more).
- **RAM**: the code-area words at DD74h-DD7Fh in another order than 3.4's table (words even): `obj22_x`
  DD74h, `obj37_last` DD76h, `l3_mail` DD78h (6), `obj22_step` DD7Eh, `obj40_flag` DD7Fh; `fc_tab`
  ECF0h-ED0Fh (32) for step C's frame cache.
- **`BANK_L3`**: the header, `lvshared_l3`, `l3_init`, `lt2`, `l3_noten` (behind a `jp`: the rule takes 10
  bytes), the deaths `death_cain`, `death_truck`, `death_w21` and `debris_add` (ported from `$C25C`,
  `$C360`, `$C3A8`, `$C398`; not run yet: no stub dies, so step B's kill drives check them), the 19
  stubs (`tNN_s`: `ld hl,tNN` / `jp l3b_call`) and the tables: 3,913 B free. **`BANK_L3B`**: the 19 types as one stub (`ld a,FFh` / `ret`) and `at_l3b.inc`: 8,045 B free.
  `rc2.asm` `l3b_call` (14 B): `BANK_L3B` at A000h, the routine, then `logic_map`; A and the flags
  returned. While a `BANK_L3B` handler runs, `BANK_L3` (with `lvshared_l3`'s `t_xy`, `t_face`, `t_col`,
  `t_word`) is not mapped.
- **The fixed area** 18 B (`ml_ev` +1, `ml_end` 3, `l3b_call` 14): 156 B free in the product, 21 in the
  lowest set (`DIAG=1 PZ_TEST=1`).

### 3.10 As built by step C (2026-11-01) [V]

What step C built and where it departs from 3.5-3.6 (the account and the checks: `docs/level3/HANDOFF.md`,
"Step 5 (plan step C)"):

- **The catalogue** (`tools/bobcatalog.py level3`): **212 frames** (141 in DATAL3), the bench's 202 and
  10 from REA's reading of the draw code (`L3_HARD`: every table of types 21, 22, 33-39 and 50-52, the
  lift's two parts, the shared types 4 and 12): Cain's muzzle flash `$412B8` and `$46790`, type 38's
  directions 13-15, type 4's `$58312` and `$6C620`, and three PERMA frames of level 1's coverage. The
  bullets are the types level 3 fires (`L3_BULLETS`, `$F3CE`'s animation: offsets up to the first past
  the limit, so bullet 12h draws `$40638` as 48 x 16 and 13h `$40C78` as 32 x 40, as the bench saw);
  the explosions are the types the bench drew (`L3_EXPL` 0, 1, 4, 6, 7). **Level 3 has no MADEX
  explosion** (DATAL3 overwrites MADEX: explosion type 0 is PERMA's 32 x 32, sprites as in levels 1-2;
  type 6's first step draws whatever DATAL3 holds at `$3DF00`, as the Amiga does): only the smoke (48
  x 56) uses the explosions' slot.
- **The pool** (`tools/msxsprites.py --l3-*`): level 3's 150 ids (82 new records against palette C, 60
  level 1's and 4 level 2's records where those memories hold the same bytes, the spark's 4); patterns
  3,604 -> 3,944, **the pool 27 -> 28 banks** (every later block one bank on); levels 1-2's 696 index
  entries resolve to the same record bytes. The 32 x 40 part of Cain and every frame under 48 px stay
  sprites (decision 13; 3.5's "four play-field parts" counted that part).
- **The play field**: 66 frames from **98h** (`lv_fid0`: the first multiple of 8 after its sprite ids):
  18 static (the atlas, 109 lines, two banks: the lift's two parts, Cain's 48 x 16, type 21's torso, type
  35, the truck's body and part, type 51, the rocket, a debris part), **42 in the frame cache** (Cain's
  legs 48 x 44 x 18 and 64 x 34 x 2, his 64 x 32 x 6, type 21's legs 64 x 40 x 16), 6 smoke frames
  (level 1's dynamic frames: level 3's own `field_dyn`, `fb_fdyt`), the lift's two parts late.
- **The hit flash** (default 6): **white copies in the ROM**, not a conversion at the upload: 55 of
  them (every play-field frame an L3_FLASH enemy draws: Cain, types 21, 33, 35, 51), in **colour 9**
  (palette C's nearest to the Amiga's colour 15, (11, 11, 11): the flash is colour 15 of the Amiga's
  palette, which is not MSX colour 15), uploaded as any cache frame. `bob.asm` `fb_add` sets the list
  entry's bit 7 for a BM_FLASH record; `field.asm` `fb_wants` keeps it in level 3 only (`fb_fwm`, 80h),
  so levels 1-2's lists are as before (their silhouettes stay sprites).
- **The frame cache** (page 2 lines 160-231): **seven fixed places** (`L3_FC_PLACES`, not LRU): 0 the
  legs, 1 Cain's 64 x 32, 2 the legs' white copies, 3 the other white copies up to 64 x 48, 4 those up
  to 64 x 24, 5 the truck's body's white copy (80 x 48), 6 type 51's (48 x 49; places 5 and 6 overlap
  others); the frames shown together never share a place (ENEMY_CAP 1). `fc_res` (ECF0h) keeps the
  cache frame of each place; a copy makes the places it overlaps empty. `field.asm` `fbb_fc` /
  `fc_find` / `fc_get`: a frame not resident is copied from its ROM bank when a piece is composed with
  it, with the VDP idle and no command prepared (`fb_dyn`'s rule), 13-21 ms a copy (1-1.3 KiB: about 15
  us a byte while the screen shows, the R800 the same). Its ROM: 14 banks, the header in the first one
  (per id [normal, white], per cache frame [bank, address, place], per place [x, line, overlaps]).
- **ROM**: **163 of 256 banks**. `place_banks` now lays out every block after level 2's atlas (the pool's
  growth had put Brainstorm's visit-2 pictures on bank 127): level 3's map and attributes 124-126,
  `BANK_FRONT2` 127, the visit-2 pictures 128-131, the ending's sound 132-135, level 3's tiles 136-143,
  tables 144, atlas 145-146, frame cache 147-160, `BANK_L3` 161, `BANK_L3B` 162.
- **Default 9**: the vats' display only in `VAT_ANIM=1` builds; there `BANK_FIELD` has no room for level
  3's play field, so those builds leave it out (`fld_l3` empty, level 3's play-field frames out of its
  BOBHASH: not drawn; they serve level 2's comparison).
- **`bob.asm`**: `lv_fid0` in `bob_flush` and `bf_frame`; in level 3 (`fb_fwm`) the enemy bullets whose
  frame is a play-field frame (the deaths' debris, the rocket) go to the play field.
- **Free bytes** (the product): the fixed area 164 (156 + 31 from default 9 - 23), the lowest set 29;
  `BANK_FIELD` 300 (1,108 after default 9).
- **Big moving play-field enemies tear** (the step's stress test, `tools/bstest/l3field.tcl`): an item of
  more than one 64 x 64 piece on the page shown is copied in several HMMMs of about 13 ms each (6.3 us a
  byte), which no blank holds: with Cain-sized parts animating every tick, 10-14 % of the pictures show
  him partly old, partly new on the V9958 (fewer on the V9938), type 21 about 5 %, the truck 1 %, type 51
  none; the guard counts the copies running into shown lines. Not the cache's: its frames and places
  are right in every picture; the same with the picture held 60 VBLANKs. **Step 7** (`docs/level3/HANDOFF.md`)
  copies a staged item as one chain the split interrupt starts (`field.asm` `fst_chain`: one copy a band
  of pieces side by side in page 3, the largest last): with the real logic the field check's torn
  pictures went 84 -> 0 of 1,000 (boss, V9958), 10 -> 0 (V9938), 114 -> 21 (turbo R), kill 65 -> 1 of 700
  (V9958), 61 -> 0 (V9938). Left: the beam still crosses one copy of such an item now and then (one
  picture partly old each time): boss window 15 copies in 42 s on the V9958, 22 on the turbo R, none on
  the V9938; kill window (frames 1500-1634) 43-45 on all three. **Step 10** found the cause in the volume,
  not the order: HMMM moves 5.85 us a byte, and from the split the beam reaches an item at shown line 45
  after 139 lines, so at most ~2,200 bytes stay ahead of it there; Cain's moving bands are 2,600-5,250
  bytes. No order of the chain and no start from the split's or the VBLANK's interrupt avoids it (the
  beam's order was tried: no fewer crossings, the VBLANK's interrupt held into the picture); a chain
  started from a line interrupt right after the beam passes the item's top would hold up to 262 + the
  item's height lines of copy (Cain on the roof and in the kill window; not the turbo R's two-band
  poses). Open issue (`docs/level3/HANDOFF.md`, step 10).

### 3.11 As built by step B (2026-11-01) [V]

What step B built and where it departs from 3.3-3.4 (the account and the checks: `docs/level3/HANDOFF.md`,
"Step 6 (plan step B)"):

- **The types** (`msx/level3obj.asm`, `BANK_L3B`): the 19 new types as 3.3 lists them, the bank's own copies
  of the shared helpers (`l3_xy`, the muzzle flash as its own owner `l3_flash`, type 38's flight from
  level 2's `t49` with `fly_dx3`, `fly_dy3`, `fly_gfx3`), `obj_push` (`$EF18`) and the turrets' map writes
  (`tur_pnl`, `tur_put`: the panel's `map_cell` cell, the turret one row below and 10 or 7 columns right);
  39 and 52 one routine with their tables; 40 and 42 one routine (Q6). Their tables in bank `l3b` of
  `analysis/amiga_tables.tsv` (`t21_*`, `c22_*`, `t34_tab` ... `t47_cam`). Type 36's turn test reads map
  words of 2D00h: the port knows the 22 cells (its shafts, columns 2 and 75) as constants, which
  `tools/mapcells.py --level 3` checks against the map and every writer.
- **The patched bytes** (Q3): `obj22_step` holds `$D583` XOR 3 and `obj40_flag` `$E9F5` XOR 42h, so that
  AC_VARS' zero at the power-on reads as the image's bytes (`analysis/amiga_ram_l3.tsv`'s `xor=`).
- **The original's D1 that Cain reads** (found by this step): `update_objects` calls each handler with
  D1 as the slot before left it, and type 22 tests it (`cmpi.w #$30,D1` at `$D53A`: sound 0Eh while its
  fire counter is 0). The port keeps that D1 in `objects.asm`'s `uo_d1` (the free slot's own D1): every
  level-3 handler writes its last D1 there (after a last BOB, `l3_tail`: draw_bob's shift ror 4 | 0FCAh,
  or y - camera y when out), types 4 and 12 and the deaths through `level3.asm`'s wrappers (`t4_w`,
  `t12_w`, `d3_c31e`, `d3_c35a`); slot 0's is `read_joystick`'s FF00h/FF10h.
- **`act_20`** (`mapobj.asm`, `ao_acts` entry 8), **the two-part lift** (`special.asm` `spl_two`: AG `$8050`
  = 2) and **the rocket x 1** (`hits.asm`: bullet 11h beside types 1 and 2, default 11). The touches of
  38, 39 and 52 take 18h in their own code (default 12).
- **ENEMY_CAP**: `l3_noten` (step A) holds with the types: a product-option run of `kill` (ENEMY_CAP 1,
  DAMAGE_X 2) brings Cain, his bombs and missiles and his death as the trace builds do.
- **The continue** (`front.asm` `fo_flash`, both levels): the two countdown steps of the palette flash
  (`$F826`) the original takes between the death's end and the continued game (`$82A8`'s `$FEDA`, the
  continue's text `$10768`).
- **Bytes** (product): `BANK_L3B` 2,383 free (5,662 used), `BANK_L3` 3,867, LC1 50, LC2 4,827, LC3
  4,794, FRONT 1,119; the fixed area unchanged.
- **Known issues** (the D1 Cain reads, his sound 0Eh; no drive reaches any of them):
  1. With the joystick locked (`$804D`) slot 0's D1 would be `eb_update`'s leftover; the port takes it as
     negative (step B).
  2. A marker spawn into the slot before Cain's on the frame he runs leaves the original's D1 at the
     marker's y, the port's at 20h + 8 x step (`objects.asm` `uf_mk`); nothing changes while type 43
     (markers off, the roof) has run, as in every drive (step B).
  3. **Types 4 and 12** (review B's finding 1, recorded by step 11, not fixed): `level3.asm` `t4_w` /
     `t12_w` -> `tw_d1` calls `l3_tail` through `rc2.asm` `l3b_call`, which loads A = `BANK_L3B` first, so
     `l3_tail`'s `or a / jr nz,lt_out` never sees the BOB's result and always takes its "not drawn" branch
     (D1 = y - camera y, >= 30h); with A kept it would still test the handler's return value, not the last
     BOB's. The original's D1 there (`$D53A-$D540`; `draw_bob` `$ABDE-$AC18`) is the shift ror 4 | 0FCAh,
     negative when (x + 1) & 15 >= 8. So with a type 4 or 12 visible in the slot before Cain's and Cain's
     fire counter (-40h) 0, the port plays sound 0Eh where the original plays nothing. Sound only; with
     `ENEMY_CAP` 1 types 4, 12 and Cain are all counted and never coexist (`uo_cap`, `uf_any`, `uf_end`):
     only the `ENEMY_CAP=0` trace builds can reach it, and no drive does.

### 3.12 As built by step D (2026-11-01) [V]

Checks 3-8 of section 4, whole, on the MSX2, the MSX2+ and the turbo R, with step 7's chain in (the account,
the commands and every number: `docs/level3/HANDOFF.md`, "Step 8 (plan step D)"; the harness:
`docs/HARNESS.md` 5.29):

- **The one fix** (`msx/frontx.asm` `fo_hsc`): the high-score entry takes three steps of `pl_fade`'s
  countdown of the palette flash (`$F826`), as `$12082` does (REA: its text screen's `$10768`, `$1080C`;
  Return's `$121E0`; the fade loop's `$12112`, once, the fade level already 0). A flash running at the
  death's end of a qualifying score thus ends before the continued game: RoboCop's tint only (no logic
  reads `$F826`), and the trace field `$F826` (step B's open issue). FRONT 7 B.
- **Checks 3-4**: in Cain's windows (boss from 625, kill from 1550 and from 1745 to the level's end) the
  field check finds no picture behind its list or torn (one on the turbo R in 1,000), no wrong frame, no
  wrong cache place; type 21's death in park (ticks 49-85, the trace build's ENEMY_CAP 0) still shows its
  white flash and debris up to 8 pictures behind the list (37-53 pictures in 500). The guard counts
  124 / 250 / 234 copies the beam crossed over the whole kill drive (step 7's chain's last bands). The
  stills from Cain's last hits to the end count: every sprite pixel and play-field pixel as the lists say.
- **Check 5**: no line above 8 sprites over the whole kill drive (the guard's `sprlines` 0 on the three).
- **Check 6**: the requests per tick equal the bench's on the SCC, an SCC in slot B and the PSG (kill and
  park; boss on the SCC; cont3 through the continue), the briefing and the offer silent after their stop.
- **Check 7**: the product's whole flow (`np_l3flow_setup`) from level 1 through level 2's end, the
  statistics, both second visits, the level-3 briefing (412 VBLs), level 3 (its first picture and frame 100),
  its end, the end count, WELL DONE, the CMP tune (4,917 ticks), the name entry, the table and the title;
  Cain's own death in kill (trace 0 differ to row 1860) into WELL DONE and the tune; a game over in level
  3 into PIC9, the name entry, the table and the offer.
- **Check 8**: after the continue the map patches, the attribute RAM, the lists and the tile cache as
  before PIC9; the frame cache empty at `lv_cont` (PIC9 overwrote its lines: every frame copied again).
- **The speed** (not a check; the product's options, kill's drive): the boss route runs at 6-10.5 ticks a
  second on the MSX2, 9-10.6 on the MSX2+, 14-19 on the turbo R, the end count at 19-25; tour3's start at
  15-22. Cain's composition is the cost (an open issue, section 7's risk 1).

## 4. The checks

Every step: `make test` with the four known failures only; the build logs without errors or new
z80asm warnings; the free bytes of every code bank logged in the product and the lowest option set;
levels 1 and 2 unchanged (their bench traces at 0 differences, the title, Brainstorm and the range as
the base: `tools/bstest/l2base.sh`, the regress gate).

| # | Check | How |
|---|---|---|
| 1 | Level 3's logic: every reference of `l3drives.py` 0 differ in every field over every row, on the MSX2, the MSX2+ and the turbo R | `hz_l3`, `tracecmp.py --fields` (as `docs/level2/HANDOFF.md` step 11) |
| 2 | The start picture equal to `msxreal.py --level 3`'s render; the lost counters 0 | the start check |
| 3 | The field check 0 differ in the windows of `tour3`, `park`, `boss`, `kill` on the three machines; no picture shows a frame the list does not hold, none a wrong cache place | `fieldcheck.py --level 3` |
| 4 | Frame-to-frame coherence of Cain's and type 21's parts on recordings | the stills and `recframes.py` |
| 5 | Sprites a line: no new class of line above 8 beside the known one (`docs/LEVEL2.md` 8.1) | the start check's `sprlines` |
| 6 | The sound: level 3's requests per tick on the three chip sets equal the bench's | `fxcheck.py` |
| 7 | The flow: level 2's end, the statistics, both second visits, the level-3 briefing (412 VBLs), level 3, Cain's death, the end count, step 3's ending (or the title until it is in) | `flow_l3`, `bonuscheck.py --level3` |
| 8 | The continue in level 3: `cont3` 0 differ; the map, the lists and the cache state as before the game over | `contcheck.py --level 3` |
| 9 | The product from a fresh machine (Expert, HB-F1XDJ) through level 3; the 2 MiB image's guard on a 1 MiB device | as level 2's step 22 |
| 10 | The matrix 10 of 10 | `tools/msxmatrix.py --home ...` |
| 11 | mkrom's checks: the 3Fh rule, the SCC test values, the guard's tag, the bank map | every build |
| 12 | The ROM's bank-select log in level 3 (the Pico+'s target) | as level 2's 4.4, a measure only |

## 5. The steps

Each step works in its own worktree and branch, commits at every stable point, appends its section to
`docs/level3/HANDOFF.md` and integrates into `level2` by cherry-pick. B and C run side by side once A
is in; D after both; E last. Owners: **A edits `msx/msx.inc` first and allocates every level-3 home
and descriptor field (3.1, 3.4) so that B and C need not**; C owns `field.asm`, `bob.asm`, the pool and
`mkrom.py`'s pool and atlas parts; B owns `level3*.asm`, `objects.asm`, `special.asm`, `mapobj.asm`;
step 3 owns `front*.asm`'s ending and high scores.

| # | Step | Files | Depends on | Hours | Acceptance |
|---|---|---|---|---:|---|
| A | **Level 3 in the ROM, the flow and the bench** | `Makefile` (level 3's conversions), `tools/mkrom.py` (level 3's blocks after Brainstorm's pictures: `BANK_L3`, `BANK_L3B` as late code sections, tiles, map, attributes, tables, a stub atlas; `lv_desc3` with `lv_fid0`; `level3_grade.pal`; `gen/lvshared_l3.asm`; `a000_only`; `LV_TEST=3`), `msx/msx.inc` (3.4's homes, `LV_SIZE` 33), `msx/level3.asm` (new: header, `l3_init`, `lt2`, the deaths, `lv_noten`, stub types that free their slot), `msx/level3obj.asm` (new, `BANK_L3B`: stubs), `msx/rc2.asm` (`ml_ev`, `l3b_call`), `msx/front.asm` (`front_l3test`), `tools/l3drives.py`, `analysis/amiga_ram_l3.tsv`, `analysis/amiga_tables.tsv` (bank `l3`), `tools/cellmasks.py`, `tools/mapcells.py`, `tools/bstest/hz.tcl`, `tools/openmsx_rc2.tcl`, `docs/HARNESS.md` | step 1 (`DAMAGE_X`), this plan | 3 | mkrom's checks in every option set; the 2 MiB product with its guard; levels 1-2's data blocks identical at their banks (`romdiff.py`); levels 1 and 2's traces 0 differ; `LV_TEST=3` reaches level 3 with RoboCop at (1184, 784) and the start picture equal to `msxreal.py`'s; `tour3` 0 differ up to the first frame of an unported routine; the product's flow from level 2's end into level 3 (no ending yet: the title after `$8050` = 3) |
| B | **The logic** (∥ C) | `msx/level3.asm`, `msx/level3obj.asm` (every routine of 3.3), `msx/mapobj.asm` (`act_20`), `msx/special.asm` (the two-part lift), `msx/objects.asm` (only if the traces show a shared difference: LC1 has 53 B) | A | 3 | check 1 for `tour3`, `park`, `boss`, `kill`, `cont3`; `mp_lost` 0; levels 1 and 2's traces 0 differ |
| C | **The sprites and the play field** (∥ B) | `tools/bobcatalog.py` (`level3`), `tools/msxsprites.py` (level 3 in the pool, per-level `FIELD_ID0`, no silhouettes for its field frames), `tools/mkrom.py` (the pool in place, level 3's atlas, big-frame banks, BOBHASH), `msx/field.asm` (the vats' section under `VAT_ANIM`; the dynamic frame cache; the white flash; `fld_l3`), `msx/bob.asm` (`lv_fid0`, the debris routing), `msx/cold.asm` (`lv_select`'s atlas for level 3), `tools/msxframe.py`, `tools/recframes.py`, `tools/msxchooser.py`, `msx/level3_frames.json` (empty), `tools/bstest/fieldcheck.py` | A | 3 | levels 1 and 2's records and stills pixel-identical; `romdiff.py --blocks`, `relocheck.py`; level 3's frames all in the catalogue; checks 2-5 on the windows B's routines reach (with B's stubs: the frames drawn so far) |
| D | **Cain, the end, the sound and the continue** | fixes in `level3obj.asm` and `field.asm`; `rc2.asm`'s hook into step 3's ending (its entry's name from step 3); `tools/bstest/fxcheck.py` and `contcheck.py --level 3`, `bonuscheck.py --level3` | B, C, step 3's ending in `level2` (else the hook calls the title) | 2 | checks 1-8 whole on the three machines; Cain's death → the end count → the ending |
| E | **Acceptance and documentation** | none, or fixes; `docs/LEVEL3.md` (as built), `docs/MSX_ARCHITECTURE.md`, `docs/AMIGA_ANALYSIS.md`, `docs/ROM_BUDGET.md`, `README.md` (the flow) | D | 1-2 | checks 9-12; `make test`; the option sets; the candidates built twice to the same bytes |

## 6. Defaults taken for the user's choices

*Where each stands at 56e8f56 is marked **In** (or what replaced it) at its end.*

1. **The palette**: level 2's palette C as it is (identical bytes; ΔE76 2.18 against level 1's
   palette's 2.68). Alternative: refit entries 8-15 for level 3 (every shared frame changes meaning).
   **In** (3.9: `level3.pal` = `level2.pal`, the tables bank's graded palette level 2's bytes).
2. **PIC7 dropped** (decision 5), as PIC4 was. **In** (`front_brief`: the briefing alone).
3. **No statistics after level 3**: the original shows none (`level_load_3`). **In** (`ml_ev` → `ml_end`,
   3.9).
4. **Both sides of every big frame stored** in ROM (about 58 KiB): no flip while streaming.
   Alternative: flip at upload (half the ROM, more CPU). **In** (the frame cache's ROM, 3.10).
5. **The tile cache 160 slots in level 3**, page 2 lines 160-231 the frame cache, 232-255 the
   explosions' slot. **In** (3.9, 3.10).
6. **The hit flash of level 3's play-field frames drawn white by the play field** (an upload with the
   nibbles turned to 15), no sprite silhouettes; levels 1 and 2 unchanged. Alternative: silhouettes
   as level 2's (then the ids do not fit: 16-bit ids). **In, as white copies stored in the ROM** (colour
   9, 55 of them) instead of a conversion at the upload (3.10).
7. **`FIELD_ID0` per level** (D0h, D0h, about 98h). Alternative: 16-bit ids. **In** (`lv_fid0`: D0h,
   D0h, 98h; 3.9, 3.10).
8. **Two logic banks**, the new types in `BANK_L3B` behind stubs. **In** (`l3b_call`, 3.9, 3.11).
9. **The vats' display code assembled only with `VAT_ANIM=1`** (the user chose static vats): it frees
   `BANK_FIELD` for the frame cache. If a `VAT_ANIM=1` build then overflows `BANK_FIELD`, such builds
   stop at mkrom with level 3 in (they serve level 2's comparison only). **In** (3.10); the
   `VAT_ANIM=1` builds do build, without level 3's play field (`fld_l3` empty).
10. **ENEMY_CAP in level 3**: Cain's bombs and missiles (38, 39, 52), the turrets (40-42) and the
    triggers (43, 46, 47, 48) not counted (3.3). Alternative: count the projectiles (Cain would never
    attack). **In** (`l3_noten`, 3.9; checked with the product's options on `kill`, 3.11).
11. **The rocket (bullet 11h, 40h) × 1**, as the missiles (the user's order of 2026-10-31 covers
    missiles; this rocket is one). Alternative: × `DAMAGE_X`. **In** (`hits.asm` `phb_en`, 3.11).
12. **The touches of 38, 39 and 52 (18h) × 1**, as level 2's drone. **In** (their own code, 3.11).
13. **Bank 127**: an A000h-only block of level 3 (its logic or its map) takes it when the order puts
    one there; padding otherwise. **The rule is in** (`place_banks`), but bank 127 holds the ending's
    `BANK_FRONT2`; 191 would take `BANK_L3` or `BANK_L3B` (3.9, 3.10).
14. **Level 3's frames kept whole until the user's choices** (`msx/level3_frames.json` empty). **In**
    (3.10).
15. **The ending's hook**: until step 3's ending is in `level2`, `$8050` = 3 goes to the title.
    **Superseded**: the ending was in first; `ml_end` calls `fr_ending`, then the title (3.9).
16. **Cain's damage × 1** (the user's order of 2026-11-01: "o dano de Cain deve ser idêntico ao
    original do Amiga"): his shots (bullets 9 and 0Ah, damage 1; no other type fires them), touching
    him (type 22, 1 a frame) and touching his bombs and missiles (38, 39, 52: the touch's 1 a frame;
    their own 18h was × 1 already, default 12). Every other enemy keeps `DAMAGE_X`. **In** (`hits.asm`
    `phb_en` and the touch).
17. **Where Cain attacks and where he dies stay the original's** (the user's decision of
    2026-11-01, "vamos manter a lógica", after the play-test report of 2.11): the projectiles from
    their fixed spawn entries, the bursts from the type-48 triggers, the idle floor ends and Q1.
    Alternatives offered: attacks everywhere, or killable high up. **In** (no code change).
18. **Camera mode 2's view as it is** (the user's decision of 2026-11-01: the one that costs least,
    "a que for mais performaticamente economica"): RoboCop kept at screen x ≤ `AX_MAX` 160, so
    the MSX shows about half of Cain on floor 30 and the ground floor (2.11). Alternative: the view
    about 35 px further left in level 3's mode 2 (about 85 % of Cain, as on the Amiga), at the
    cost of more composition and more white copies. **In** (no code change).

## 7. Risks

*Which of them happened, at 56e8f56, is marked at each one's end.*

1. **The dynamic frame cache** is the one new engine piece (step C): VDP time and CPU while Cain and
   type 21 animate, and the V9938's two pages (a place reused while the other page still needs its
   frame). It can show wrong frames if its bookkeeping slips: check 3 must pass before D starts. If
   it cannot be made glitch-free tonight, the fallback is a static per-type upload at spawn (Cain's
   frames alone fit 128 lines) with a short pause when a big enemy spawns. **The cache's bookkeeping
   held** (its frames and places right in every picture checked on both VDPs; the fallback was not
   needed), but **a big item tears**: copied in several 64 x 64 pieces of about 13 ms each, which no
   blank holds, Cain and type 21 can show partly old, partly new frames while they move or animate
   (3.10; open at 56e8f56).
2. **`BANK_FIELD` room**: the cache needs the vats' section out of the product (default 9). **As
   foreseen**: default 9 gave 958 B, the cache and the flash took 808, 300 B are left.
3. **The fixed area**: about 30-45 B for level 3 against 181 (196 after step 1), 46 (89) in the
   lowest set: log after every change. **Within it**: level 3 took 41 B and default 9 gave 31 back:
   164 B free in the product, 29 in the lowest set.
4. **The pool's shift and the 3Fh / SCC rules**: data-dependent; mkrom stops the build, the step pads
   or reorders. **Happened**: the pool's growth put Brainstorm's visit-2 pictures on bank 127; step C
   made `place_banks` lay out every late block (3.10). mkrom's checks pass in all 58 option sets that
   build.
5. **Frames the bench did not draw** (rare states of Cain, types 36, 37): REA's tables must complete
   the catalogue, else a frame is missing on the MSX. **Averted**: the catalogue has 212 frames, 10 of
   them from REA's tables, and the 178 frames the new drives draw are all in it (3.10, 3.11).
6. **Cain's chase in the drives**: a drive must follow him down to y 290h and kill him without god
   mode for the `kill` reference; the bench's boss drives used god mode and a poke (coverage only).
   **Solved**: `kill` follows him down through `act_20`'s three floor pieces and shoots him on the
   ground floor (energy and lives poked, no god mode), 1,861 rows to the level's end (3.11).
7. **ENEMY_CAP with Cain**: no other enemy from his spawn to his death; the user may want more. **As
   foreseen** (the product's options on `kill`, 3.11); the user's choice stays open.
8. **Time**: A 3 h, B and C 3 h each side by side, D 2 h, E 1-2 h: about 9-10 hours of agents; if C
   slips, B's logic can still be accepted (traces) and the candidates carry level 3 with the
   static-upload fallback, said in their notes. **C did not slip**: the fallback was not needed.
