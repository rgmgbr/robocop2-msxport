# Level 2's play field on the MSX: the map, the vats, the palette

Area "map" of the level-2 plan, written on 2026-10-27 against the repository at `781005e` (branch
`range`), read only. No emulator was run and nothing was written into the repository.

Tags:
- **V**: verified, by REA (Ghidra provider, raw-binary m68k, entry 0x0, on `build/ram/level2_full.bin`,
  sha256 `a039a158…0a88b09`, seeded with `analysis/ghidra_seeds.tsv`), or by a script of this folder on
  the game's data (named in each case);
- **I**: inferred, not run;
- **D**: a design proposal for the port;
- **E**: an estimate, scaled from a measurement.

Names found here are in `l2map.sym` (this folder), in the format of `analysis/*.sym`.

## 1. Summary

- **The data [V].** DATAL2 is the tile sheet (512 tiles), the map (160 × 50 words) and level 2's own
  BOB graphics. Level 2 has:
  - 44 map objects: 16 trapdoors, 16 breakable objects, 5 static looks, 4 blinking mines and 1 teleport;
  - 7 vats of bubbling liquid, the level's only hazard (no beams, no conveyors, no barriers);
  - 5 lifts and 4 trolleys that run over the vats. These are play-field BOBs, not map cells.
- **The writers [V].** Only two kinds of routine change level 2's map:
  - the map objects' looks (`activate_objects` `$9C06`, with `act_0c` `$9EE8` new): 289 cells;
  - the vats (`level_tick_1` `$91BC`): 604 cells.

  Every vat word has attributes 0, and so has every vat cell of the map. **The vats change only
  tiles, never what the logic reads.**
- **The pipeline.**
  - Reused as it is: `tools/msxconv.py`, `tools/amitab.py` and the tile cache.
  - Given a level parameter: `tools/mapcells.py`, `tools/mkrom.py` and about 20 build-time equates
    in the asm. These become a per-level descriptor (3.3).
  - New: the vats, `act_0c`, the trolley and the level-2 palette step.
  - A level-2 trap: the port's ports of `$EF8E` stop at `MAP_ROWS` rows. The original stops at the
    constant 51 for every level (`$EFA4` `cmpi.w #$66`). Level 2's row 50 is read there, and 35 of
    its 160 words are "solid" (2.9).
- **The palette [V, D].** RoboCop's Amiga colours (COLOR16-31) are the same in levels 1 and 2. Only
  background colours 5, 6, 10, 11 and 15 differ.
  - Recommended: option **C**, level 1's joint palette with level 2's values at indices 9, 11 and 13.
    - Indices 0-7 are unchanged, so RoboCop's data and every shared frame stay byte-identical.
    - Mean ΔE is 2.42, against 2.50 for level 1's palette as it is (A) and 2.46 for level 2's own
      k-means palette (B).
    - The sky's two blues stay apart, which A loses.
    - B turns the reds orange and changes RoboCop's colours.
  - Previews: `png/level2_compare_half.png` and `png/crop_*.png`.
- **The vats against the VDP [V, E].**
  - A visible vat changes up to 107 cells every 2 ticks: 13.7 KB as tiles, 10.9 KB as per-tile
    bounding boxes, 5.2 KB exactly (scattered bytes).
  - At the original rate, that is 101-129 % of the command engine on a V9958, and twice that on a
    V9938, whose scroll draws changed cells on both pages.
  - **No faithful method keeps 25 Hz on the V9938, nor reliably on the V9958.**
  - Proposed (5.1) as the cheapest that is still exact in every picture: the vats leave the map
    patches, and a column refresher redraws whole vat columns at the newest step the VDP can afford.
    It never tears and never goes back to an older look.
  - Expected: about half the original step rate with the camera still, less on a scrolling V9938.
    This must be measured in openMSX.
- **Tile cache and VRAM [V].**
  - At most 107 distinct tiles are in the V9958's 19 × 14 window (148 with every tile the writers
    can put there), against 256 slots.
  - The vats need no VRAM of their own.
- **ROM [V].** The map area takes 12 banks: tiles 8, map 2, attributes 1, tables 1.
  - With the logic bank and the play field, the total comes to the 15 of `docs/ROM_BUDGET.md` 3.2.
  - The `.atrp` is 4,016 B and the `.otile` 1,024 B. The tile sheet holds 511 tiles (65,408 B).

## 2. DATAL2 and the level's data [V]

### 2.1 Files and memory

| What | Where | Size |
|---|---|---|
| DATAL2 (`DATAL2_18.bin`) | `$28000-$41D57` (manifest load address) | 105,816 B |
| tile sheet | `$28000-$37FFF` | 512 × 128 B: 16 × 16 px, 4 planes interleaved per line |
| map | `$38000-$3BE7F` | 160 × 50 words: DATAL offset `& ~$7F` \| attributes |
| level 2's own BOBs | `$3BE80-$41D57` | 24,280 B (type 5 at `$3BFC0`, type 6 at `$3C920`, type 1's legs at `$3E810`) |
| MADEX | `$45250-$4B54B` | 25,340 B, level 2's other BOBs |
| SPERMA (shared) | from `$4B68A` | holds the lift's `$4B68A` (48 × 24) and the trolley's `$4B95A` (32 × 47) |

- `draw_background` `$BCCA` is the same for every level: the map at `$38000`, tiles at `$B1E` (set to
  `$28000` by `level_init` at `$87E8`) plus `word & $FF80`, 19 × 12 tiles.
- All 512 offsets of the sheet hold distinct graphics. After any of the MSX remaps of section 4,
  511 are distinct (`out/l2pal.txt`).

### 2.2 The header at `$868C` (`level_init` `$871A-$87D6`, bytes by REA `read_bytes`)

| Offset | Value (level 2) | Goes to | Meaning |
|---|---|---|---|
| +0 | `$A828` | `$9C18` | object list (44 entries) |
| +4 | `$95B2` | `$915E` | hazard list: the 7 vats |
| +8 | `$8FE0` | `$8B54` | special objects (9: 5 lifts, 4 trolleys) |
| +12 | `$97B0` | `$B0E` | spawn list (40 entries, 14 B each) |
| +16, +18 | 352, 784 | `$15D0`/`$B04`, `$15D4`/`$B06` | start: RoboCop and the camera |
| +20, +22 | 192, 112 | `$15D6`, `$15D8` | the teleport's target (`obj_relocate` `$9FC4`, type 34h) |
| +24 | `$C5EC` | `$C598`, `$C692` | marker table (types 3, 4, 12-16, 30, 31) |
| +28 | 624 (`$270`) | `$B08` | the camera's lowest y |
| +30 | `$0730` | `$804A` | timer 7:30 |
| +32 | `$2E` | `$16B8` | (not this area's) |
| +34 | 7 | `$C53D` (byte) | (not this area's) |
| +36 | `$10036` | `$F8C6`, `$F8BC` | palette |

### 2.3 Map, tiles and attributes

- 50 rows: the camera's lowest y is 624, and 624 + 176 = 800 = 50 × 16.
- The map uses 461 tile offsets (460 graphics after the MSX remap) and 8 attribute values: 0, 1, 2,
  3, 8, 9, Bh and Dh (`out/l2objects.txt`).
- The writers use 113 offsets, 37 of them not in the map at the start. That gives 498 offsets in
  all, with 14 of the 512 never used.
- **Scroll limits.**
  - Camera x runs 0-2272. This is the immediate at `$B2F0` in `player_move`, the same for every level
    (`tools/player.py` `CAM_XMAX`). `level_init` patches `$B2D8` and `$B2FC` identically for every level.
  - Camera y runs up to 624 (header +28).
  - On the MSX, `CAM_X_MAX` = 2304 is shared by both levels. `CAM_Y_MAX` is 800 − 162 = 638 for
    level 2.
- **Start.** RoboCop and the camera start at (352, 784): map x 224, the bottom-left. The camera
  eases up to its limit.

### 2.4 The map objects (`$A828`; `out/l2objects.txt`, through `tools/mapcells.py`'s model)

| Types | Activator (offset) | Entries | Look | What they do to the map |
|---|---|---|---|---|
| 00h, 04h | none (look only) | 5 + 2 | 3 × 3, 2 × 1 | their look, written at the level's start |
| 0Ch | `act_04` `$9F84` (trapdoor) | 16 | 4 × 2 | the trapdoor's looks |
| 08h, 10h, 14h, 18h, 1Ch, 20h, 28h, 2Ch | `act_08` `$9EA4` (explodes at look 4) | 16 | 2 × 2 | destroyed look |
| 30h | **`act_0c` `$9EE8`** (new) | 4 (row 9, x 1184-1776) | 5 × 2 | one cell blinks |
| 34h | `act_10` `$9FC4` (`obj_relocate`) | 1 (x 672, y 96) | 2 × 4 | looks; the teleport to (192, 112) |

- **`act_0c` [V].**
  - Every frame it rewrites the look word `$A4A6`, row 0 column 2 of look `$A4A2` (`A280 A280 [E680]
    A280 A280 / A901 CA81 FF81 CA81 A901`). The value is `$E680`, or `$9700` when game-frame bit 2
    is clear.
  - The 4 mines therefore blink one cell every 4 frames. Sound `$28` comes every 8th frame.
  - With RoboCop's cell on the mine, it sets the entry's (4,A1) = FFh and starts 4 explosions of
    type 0.
  - Both words have attributes 0.
- **Pool counts.**
  - The 44 entries can change 289 cells, 146 in even rows and 143 in odd rows. The pools hold 255
    each.
  - They write the attribute values 0, 1 and 2, all among the map's 8. No free code is needed.
- **No conveyor, barrier or beam [V].** Activators 14h, 18h and 1Ch do not appear in level 2's list,
  and its hazards are vats.

### 2.5 The vats (`level_tick_1` `$91BC`; REA `procedure_assembly`, `read_bytes`)

- **Dispatch.** `$9150` walks the list from header +4. A record whose x right ≥ cam x + 73h, x left <
  cam x + 1A0h and y − (cam y − 64h) in [0, 110h) runs `$91B0 + 4 × level`.
  - `$91B0` holds three `bra.w`: `$933A` (level 1), `$91BC` (level 2), `$9436` (level 3).
- **Records at `$95B2`** (x left, y, x right, rows):

  | Vat | x | y | Cells (columns × rows) | First map cell (row, column) |
  |---|---|---|---|---|
  | 0 | 848-1024 | 640 | 12 × 9 = 108 | (40, 45) |
  | 1 | 1296-1440 | 640 | 10 × 9 = 90 | (40, 73) |
  | 2 | 1568-1712 | 640 | 10 × 9 = 90 | (40, 90) |
  | 3 | 2016-2256 | 688 | 16 × 6 = 96 | (43, 118) |
  | 4 | 1904-2240 | 288 | 22 × 4 = 88 | (18, 111) |
  | 5 | 1264-1568 | 288 | 20 × 4 = 80 | (18, 71) |
  | 6 | 608-800 | 288 | 13 × 4 = 52 | (18, 30) |

  That is 604 cells in all, none shared with a map object.
- **The routine.**
  1. With RoboCop's x within the vat's x − 16 … x right + 16 and (cam y + 152 − y) in [0, 77), it
     writes 203 − that into the copper's line `$10356`. This is the WAIT before "sprite DMA off" at
     `$1035A`: his sprites end at the liquid's surface.
  2. If that line is below 144, RoboCop dies: `st $169A`, `st $16CC`, sound `$10`.
  3. Sound `$1A` plays when random & 15 = 0.
  4. **On odd game frames** (`$B01` bit 0), every column k of the vat gets T0[d] in its first row,
     then rows + 1 more cells alternating T1[d] and T2[d], with d = (phase_k & 0Eh) + 10h when the
     high byte of entry k + 1 is not 0.
  5. phase_k is the low byte of entry k at `$92DA`. It grows by 2 only for the columns of the
     *first* vat of the frame (`$15F0`, cleared by `$9150`).
- **Tables.** T0 `$927A`, T1 `$929A` and T2 `$92BA` hold 16 words each: 37 distinct tiles, all
  attributes 0. The phase table needs 23 words, because vat 4 has 22 columns.
- **The animation.** Each column cycles through 8 looks, bubbles rising (`png/vat0_looks.png`,
  `png/vat_tiles_amiga.png`).
  - It is not a plain scroll of a texture: after the best vertical shift, 67-80 of a column pair's
    512 pixels still differ.
  - The columns start at scrambled phases.
- **Pairs in the window.** Only vats 0 + 1 (camera x 881-909) and 1 + 2 (1153-1325) can be in the
  window together, and the first of each pair is the wider or equal. So every vat's columns advance
  when it is written.
- **Death zone and sprite cut** are game logic and sprites (not this area). Section 5.2 has a note
  on the cut.

### 2.6 The special objects (`$8FE0`, records `$9088-$911D`)

| Record | Handler | Place | Path |
|---|---|---|---|
| `$9088`, `$9098`, `$90AA`, `$90BC`, `$90CC` | 0, lift `$8DE6` | x 174, 542, 2542, 239, 2543 | y paths 709/789, 629-789, 469-789, 308/468, 165-389 |
| `$90DE`, `$90EE`, `$90FE`, `$910E` | 4, trolley `$8F02` | y 592, 592, 592, 640 | x 848-1008, 1304-1408, 1576-1712, 2016-2224: over vats 0-3 |

- **The trolley `$8F02` [V]** moves 2 px a frame. It is a lift-table entry for RoboCop, who hangs on
  it in states 14/15, and a BOB `$4B95A` of 32 × 47 (BLTSIZE `$BC3`) at (x + 16, y − 84). It writes
  no map cell.
- **The lift** uses the 48 × 24 BOB `$4B68A` in level 2. Its level test at `$8EB0` is for level 3's
  two-part lift only.

### 2.7 The per-level tables (as `tools/mkrom.py` lays out level 1's `LEVEL_BANK`)

| Table | Level 2 | Content |
|---|---|---|
| `.otile` (OTILE = 8000h) | 1,024 B | tile number per DATAL offset >> 7, all 512 (`map_write` resolves any word a writer writes) |
| `.atr2` (8400h) | 320 B | attributes of rows 50-51: the words after the map, DATAL2 `$13E80` (RAM `$3BE80`); 58 nonzero per row |
| BOBHASH (8600h) | 4,224 B | (512 + 16) × 8: level 2's BOB frames by (A2, D4), from level 2's sprite conversion |

The bank holds 5,760 B, with 2,432 B free for the per-level tables that leave the fixed area (3.3).

### 2.8 Engine routines that treat level 2 apart

| Where | How |
|---|---|
| `$91A4`-`$91B0` | the hazard dispatch: level 2 → `level_tick_1` `$91BC` (the only branch on `$8050` that concerns level 2's play field; REA xrefs to `$8050`: `$81B8`, `$83B8`, `$873A`, `$876C`, `$88AC`, `$8EB0`, `$91A4`, `$FFC4`) |
| `$871A` `level_init` | patches `$9C18`, `$915E`, `$8B54`, `$B0E`, `$C598`/`$C692`, `$B08`, `$F8C6`/`$F8BC` from the header |
| `$8B32` → `$8B92` | handler 4 = trolley `$8F02`; only level 2's list uses it |
| `$9C06` → activator offset 0Ch | `act_0c` `$9EE8`; only level 2's type 30h uses it among the levels ported so far |
| `$9C76` `map_object_look` | the looks (all levels) |
| `$EF8E` | rows < 51 for every level; for level 2, row 50 is past its map (2.9) |
| not level 2's | `$88AC` (level 3's start), `$8EB0` (level 3's lift), `$EA50`/`$EAA6`/`$EBB8` (2 × 3 writers of types 40-42, not spawned in level 2: spawn list types 1, 2, 4, 5, 6, 12, 13, 14, 45, 49; markers 3, 4, 12-16, 30, 31) |

Writers, swept with REA: every caller of `$EF8E` that writes through A0, plus the routines with `(140h,A0)`
or `(280h,A0)`.
- `$91BC`, `$933A` and `$9436` (vats, beams, level 3);
- `$EAA6` (obj40/41);
- `$AF08`'s `add.w D2,(A0)`, which pushes the enemy hit (its A0 comes from `$BE48`), not the map;
- the activators, through `$9C76`.

### 2.9 Trap: `$EF8E`'s rows

- `$EF8E` adds `map_row_offsets[row]` only for rows < 51 (`$EFA4` `cmpi.w #$66`). Past that it
  returns 0, and above the map it returns −1. This is a constant of the code.
- Level 2's row 50 is DATAL2's BOB data after the map: 35 of its words have a nonzero low nibble,
  so `$EF8E` answers "solid" there.
- The port's `$EF8E` ports stop at `MAP_ROWS` instead, which is the same in level 1 (51):
  - `msx/logic.asm:110` `map_cell`;
  - `msx/logic.asm:163` `map_atr`;
  - `msx/hits.asm:607` `cell_solid`.
- **For level 2 they must compare with 51 [D].** `tiles.asm` `atr_rc` then serves row 50 from `.atr2`
  (`ar_after`, which already starts at `MAP_ROWS`).
- Level 1's behaviour is unchanged.

## 3. The port's level-1 pipeline against level 2

### 3.1 Tools

| Tool | Level 1 role | Level 2 |
|---|---|---|
| `tools/msxconv.py` | tiles, map, `.atr`, `.otile`, `.atr2`, `.atrp`, `.vram`, preview | **as is**: `--rows 50 --joint <level-2 .pal/.remap>`. Ran here (`out/conv/`): 511 tiles, 65,408 B; `.map` 16,000; `.atrp` 4,016; `.otile` 1,024; `.atr2` 320. Its docstring and print still say 432 VRAM slots (256 now) |
| `tools/msxsprites.py` (joint palette) | k-means joint palette and remap | **new step**: level 2's palette is level 1's layout with level 2's values (section 4). Either a flag of `msxsprites.py` or a small stdlib tool; its level-2 frames must be converted with it (sprites area) |
| `tools/mapcells.py` | patch pools and attribute codes, level 1 | **parameter**: `main` hard-codes `"l1"`, and the level-1 tables `hz_l1`, `lt0_*`, `t32_map`. Add: the level, `objl_l2`, `act_0c`'s second word for type 30h, and the vats' own checks (attributes 0 in words and cells, no object overlap) instead of counting them in the pools |
| `tools/cellmasks.py` | spawn and hazard masks per camera cell | already loops over `l1`-`l3`; `SW_MAX` 32 < level 2's 40 entries (logic area). The vats use `$9150`'s window, the formula it has |
| `tools/amitab.py` | table copies | **as is**; level 2's rows in `analysis/amiga_tables.tsv` (bank `l2`: header, lists, `lt1_*` tables). The main code is identical in every image, so `level1_full.bin` gives the same bytes |
| `tools/msxreal.py`, `msxframe.py`, `mapcmp.py` | real-render and map checks | `--level` exists; **new**: vat cells from the vat state in RAM, not from map patches |
| `tools/mkrom.py` | lays out level 1 | **parameter**: a second set of level blocks, the per-level descriptor, level 2's graded palette |

### 3.2 The MSX code

| File (sites) | Level 2 |
|---|---|
| `msx/tiles.asm` `tile_src`, `tc_load`, `TC_SLOTS` | as is (256 slots are enough: 5.3) |
| `tiles.asm:723` `tc_upload` `BANK_TILES`; `cold.asm:1055` `tiles_upload` | variable (the level's tile bank); at level 2's start `tiles_upload` with E = 4 (page 2), as Brainstorm and the range do |
| `tiles.asm:59` `get_tile` `rowtab` | rowtab per level, in RAM (153 B, filled at the level's start). **New**: a vat cell (rows 18-21, 40-48, a per-row byte) returns the vat's word from its phase snapshot (5.1), before the patches |
| `tiles.asm:94`, `:147` `atr_rc`; `:161`, `:197` `LEVEL_BANK` | `MAP_ROWS` and the tables bank as variables |
| `tiles.asm` `map_write`, `atr_put`, `rd_queue` | as is (the pools hold the 289 object cells) |
| `scroll9938.asm:35`, `scroll9958.asm:23` | `MAP_ROWS` as a variable; **new**: the vat column refresher (5.1). `scroll9938.asm:226` `CAM_X_MAX` is shared |
| `msx/field.asm:9`, `:17`, `:279`, `:921`, `:2499`, `:3405` | `field_tab` (`robocop_field.inc`), `FIELD_IMG_BANK`, `FB_MAPH`, `FIELD_DYN_BANK`, `atr_new`'s `MAP_ROWS`: per level; the atlas uploaded at level 2's start (it is uploaded only at power-on today) |
| `msx/mapobj.asm` `ao_acts` | offset 0Ch is `ao_look` today: **new** `act_0c`; the rest as is (`act_10` and `engines_jump` serve level 2's teleport) |
| `logic.asm:110`, `:163`, `hits.asm:607` | `cp 51`, not `MAP_ROWS` (2.9) |
| `cold.asm:265-271` `pl_init`; `cold.asm:1028`, `:1035` `atr_load` | start, `LVL_YMAX`, `ATR_BANK` and the row count from the level (level 2: 50 rows, 2 of them in `ATR_RAM1`); `atr_rows` is the same table for both levels |
| `player.asm:647` `CAM_Y_MAX`; `msx.inc:41` | per level (638); `view_offy` per level (42 entries for level 2), `view_offx` shared (same `CAM_XMAX`, same width) |
| `rc2.asm:147`, `:480`, `:483`, `:505-511` | `lvl_bank`, the palette (`level1_grade.pal`), rowtab, level 1's bank: the level's descriptor; a new `level2.asm` bank (`BANK_L2`: `lv_init`, `level_tick_1`, the vat state, `cells_l2.inc`) |
| `msx/special.asm` | lifts as they are; **new** trolley `$8F02` (LC3) |

### 3.3 The per-level descriptor [D]

- **In ROM**, one per level in its tables bank: tile bank, map bank, rows, attribute bank, tables
  bank, atlas bank, dynamic-frame bank, start x and y, `LVL_YMAX`, `CAM_Y_MAX`, and a pointer to the
  graded palette, rowtab and `view_offy`. That is about 20 B.
- **In RAM**, copied at the level's start: rowtab (153 B), `view_offy` (43 B) and the graded
  palette (32 B).
- **Shared**: `atr_rows`, `view_offx` and RoboCop's flashes. The flashes still use entries 2, 3 and 7,
  which no background colour uses under palette C.
- **Constraint**: the fixed area has 235 B free. The changes there are mostly an immediate becoming a
  load from RAM.

## 4. The palette

### 4.1 Facts [V]

- The Amiga palettes (COLOR01-31) are at `$FFF6` (level 1) and `$10036` (levels 2-3), read with REA.
- COLOR16-31 (RoboCop's sprites) are identical in both.
- The background differs in five colours:

  | Colour | Level 1 | Level 2 | 3-bit, level 1 → level 2 |
  |---|---|---|---|
  | c5 | 024 | 03A | 012 → 015 |
  | c6 | 012 | 025 | 001 → 012 |
  | c10 | B00 | A00 | 500 → 500 |
  | c11 | 800 | 700 | 400 → 300 |
  | c15 | CCC | BBB | 666 → 555 |

- Level 2's pixel shares over the map: c0 31.2 %, c2 31.5 %, c1 12.9 %, c7 8.4 %, c8 5.9 %, c3 4.9 %,
  c9 2.4 %, c13 1.1 %, c15 0.69 %, c6 0.19 %, c5 0.05 %, c11 0.11 %, c10 0.07 %.
- Level 1's product palette is `000 432 455 344 333 000 111 234 222 666 210 012 100 001 500 630`, with
  background remap `0 6 12 10 15 11 13 12 8 4 14 14 12 1 1 9`.
  - RoboCop is at 1-7 (OR-closed); 5 is sprite black.
  - The background uses neither 2, 3 nor 7, which take his flashes.

### 4.2 Options, measured on the whole map (`scripts/l2pal.py`, `out/l2pal.txt`; ΔE76 per pixel against the Amiga's 12-bit colours, plain MSX colours)

| Option | Palette | Mean ΔE | Notable | RoboCop's data |
|---|---|---:|---|---|
| A: level 1's as it is (`level2_joint_l1pal`) | level 1's | 2.50 | c5 52.9 (both blues → 012), c15 11.4 | shared |
| B: level 2's own k-means (`level2_joint_own`) | `000 432 355 344 234 123 111 000 112 677 100 210 222 630 333 555` | 2.46 | c10 35.4 (reds turn orange), c5 51.3 | **changes** (1-7 differ: stored again) |
| **C: level 1's layout, level 2's values** | `000 432 455 344 333 000 111 234 222 555 210 015 100 012 500 630` | **2.42** | c5 16.6, c6 11.0, c15 1.8; c11 27.7 as A | **shared** |
| D: reference only, 0-7 fixed and 8-15 refitted | `… 012 100 210 222 300 543 555 630` | 2.40 | c11 4.7, c14 3.3, c5 52.9 | shared, but 8-15 change meaning for every shared frame |

- Under C the remap is level 1's remap unchanged. c11's nearest among 8-15 is still 14.
- c7 (310, 8.4 % of level 2: the vats' liquid among others) has ΔE 11.5 in every option, from the
  3-bit rounding to 100, as in level 1. The liquid looks redder than the Amiga's brown in every
  option.
- **Tiles**: 511 distinct after the remap in every option. The map and the vats use 460.

### 4.3 Recommendation: C [D]

- It is the Amiga's own scheme: level 2 changes the values of five background colours, and so does C.
  - The indices keep their meaning.
  - The frames level 1 already holds (enemies of PERMA/SPERMA, the hostage, the lift) show level 2's
    values in level 2, as the Amiga's BOBs do with its background palette.
  - RoboCop's indices 1-7 and his data stay byte-identical, as the one-pool plan needs.
- It is the best of the options that keep 0-7. Within 0.02 of a free refit of 8-15 (D), which would
  redefine 8-15 for every shared frame.
- It costs no ROM: a 32-B palette, graded by `tools/mkrom.py` as level 1's.
- Previews, graded (`tools/msxbright.py` `BRIGHT`):
  - `png/level2_amiga.png` and `png/level2_C.png`: the whole level, 2560 × 800;
  - `png/level2_A.png` and `png/level2_B.png`, and `_plain` versions of each;
  - `png/level2_compare_half.png`: Amiga, C, A and B stacked at half size;
  - `png/crop_blue.png` (the skyline: A merges its two blues, B makes them purple);
  - `png/crop_top.png` (B's orange valves);
  - `png/crop_vat0.png`;
  - `png/vat0_looks.png` (vat 0's 8 looks, Amiga above and C below).
- The palette files are `png/level2_C.pal` and `png/level2_C.remap`.

### 4.4 For the sprites area [I]

- Under C, any level-2 sprite colour row whose p, q or p|q is 9, 11 or 13 shows level 2's value.
- For the shared frames that is the Amiga's own change. OR pairs chosen for level 1's values may land
  a little differently: check them in the level-2 sprite conversion.

## 5. Performance and VRAM

### 5.1 The vats

**The cost [V, E].** Measured on the tiles (`scripts/vats.py`, `out/vats.txt`). The step rate is the
original's: one step every 2 ticks, 80 ms.

| Vat | Cells | Changed a step (max) | As tiles | As bounding boxes | Exact | VDP at the original rate, V9958 / V9938 [E] |
|---|---:|---:|---:|---:|---:|---|
| 0 | 108 | 107 | 13,696 B | 10,888 B | 5,240 B | 101-129 % / 202-257 % |
| 1, 2 | 90 | 89 | 11,392 B | 9,133 B | 4,387 B | 84-107 % / 168-214 % |
| 3 | 96 | 94 | 12,032 B | 9,226 B | 4,432 B | 90-114 % / 179-229 % |
| 4, 5 (17 columns seen) | 88, 80 | 85, 77 | 10,880, 9,856 B | 7,894, 7,195 B | 3,779, 3,435 B | 63-81 % / 127-162 % |
| 6 | 52 | 51 | 6,528 B | 4,730 B | 2,249 B | 49-62 % / 97-124 % |

- The VDP figures come from `docs/MSX_FEASIBILITY.md`'s HMMM rates with sprites on: 171 B/ms for
  large copies, 134 B/ms for 16 × 16 tiles. That is 13,711 and 10,752 B in 80 ms. Whole columns are
  1,152 B each for vats 0-2.
- The V9938 draws a changed cell on both pages (`scroll9938.asm` `s38_redraw`).
- T1 and T2 change in 7 of their 8 bytes on most lines, so bounding boxes save only 20 %.
- Exact bytes would need CPU writes:
  - 5,240 B and about 1,700 line addresses a step is about 220,000 T-states;
  - that is 110,000 a tick, 77 % of a 3.58 MHz Z80's tick. Not viable.

**Answer: no.** The V9938 cannot keep the vats at the original rate with any copy method, and the
V9958 only barely, with the VDP doing nothing else. The ROM budget's "54 tile copies a tick" holds.

**Proposed: vats as a display layer with a column refresher [D]**

1. **Logic, exact.**
   - `level_tick_1` is ported routine by routine. The phase table becomes RAM (23 words: code-area
     data the original changes).
   - At each vat write, the vat's column phases go into its snapshot: 12 + 10 + 10 + 16 + 22 + 20 + 13
     = 103 B in all, plus a written flag per vat.
   - The vats write nothing into the map patches. The 604 cells would overflow the 2 × 255 pools,
     with 318 in even rows, and they never change an attribute (2.5).
   - The logic's map reads see exactly the original's attributes. Its traces need no vat cell.
2. **`get_tile` reads a vat cell from the snapshot**: T0/T1/T2[d] through `.otile`. This is the word
   the Amiga's map holds, including vats that left the window and froze. `mapcmp` can compare whole
   maps with that rule.
3. **The display redraws whole columns, never single cells.**
   - A column is 4 VDP commands, all from the tile cache: T0, T1 and T2, then one overlapping HMMM
     that copies the T1/T2 pair down the column. A downward HMMM 32 lines below its source repeats
     the pair. Split it at the ring's line 255.
   - Each column keeps the step it shows, per page on the V9938. The oldest visible column whose shown
     step differs from its snapshot goes first, jumping to the newest look.
   - Rules:
     - **never tear**: start a column in the window between the HUD split and the VBLANK, or while the
       beam is below its lines;
     - **never go back**: on the V9938 the page shown comes first, and the other page catches up with
       the VDP time left; a flip waits for the back page's stale vat columns;
     - **BOBs first**: a column that meets a play-field BOB goes through `fb_meetq` as changed cells
       do;
     - **nothing through `rd_queue`**: its 64 entries cannot take a step's 100 cells.
4. **CPU [E].** About 2,500 T-states a column, 4 commands with the bookkeeping. At about 75 columns a
   second that is about 5 % of a 3.58 MHz Z80.
5. **Expected rate [E, to be measured].**
   - Each picture still shows one of the original's looks per column.
   - V9958 and V9938 with the camera still: the tear-free window allows about 1-2 vat-0 columns a
     frame. That is about 4-8 steps a second of the original's 12.5.
   - V9938 walking: the page builds take about 74 % of the VDP (27 KB per 16 px at 75 px/s), leaving
     about 2-3 steps a second.

**Alternatives** (section 7, default 3):
- a fixed half rate (one step every 4 ticks, every other look): predictable, but it still needs more
  than the V9938's free VDP time while it scrolls;
- tearing allowed: about twice the rate on the V9958, against the user's no-glitch rule;
- only the surface row animated on the V9938 while it scrolls: not faithful.

### 5.2 The vat's sprite cut (sprites area) [I]

- The copper hides RoboCop's sprites below the surface line (`$10356`).
- Sprite mode 2 has a colour per line per sprite, and colour 0 is transparent.
- Writing 0 into the colour rows of his A and B sprites below the cut line reproduces the cut per
  line without the second line interrupt `docs/ROM_BUDGET.md` 7 feared. Enemies (sprites on the MSX,
  BOBs on the Amiga) must not be cut.
- The line is 203 − (cam y + 152 − y), against the copper's play area starting at line 30. It needs
  the MSX view's mapping, `view_offy` included.

### 5.3 The tile cache [V]

From `scripts/tilecache.py` and `out/tilecache.txt`: the most distinct tiles in the windows the engines
keep drawn, with every tile the writers can put in them.

| Window | Level 2, map | + writers (vats' 37, looks) | Level 1, map / + writers |
|---|---:|---:|---:|
| V9958 ring 19 × 14 | 107 | 148 | 125 / 133 |
| V9938 two pages 17 × 14 | 103 | 144 | 118 / 128 |
| 40 × 24 (the margin of `tiles.asm`'s note) | 255 (the skyline corner) | 277 | 209 / 222 |

- 256 slots hold the working set with more than 100 to spare. The vats' 37 tiles stay resident once
  seen.
- A miss is a 128-B `tc_upload`, about 4,500 T-states [E]. The first visit to a vat area loads up to
  37 tiles over a few steps.
- The 40 × 24 figure only says that the clock replacement will evict in the skyline area. It is not a
  limit.

### 5.4 VRAM [V for the layout, I for the atlas]

- The layout stays level 1's. Page 2 is the tile cache.
- Page 3:
  - lines 0-87: the atlas;
  - lines 88-111: the dynamic slot;
  - lines 112-175: caches and scratch;
  - lines 176-207: sprites;
  - lines 208-252: the HUD;
  - lines 253-255: 3 lines free.
- The map needs nothing new: the vats draw from the tile cache.
- The atlas is uploaded at power-on only (`docs/BRAINSTORM.md` 3.3). Level 2 must upload its own at
  its start (`field_upload` with level 2's bank).
- The budget's estimate is 84 of 88 lines for the hostage, lift, trolley and Cain. A shelf packing by
  hand gives 80 lines:
  - Cain 2 × 48 × 56;
  - the trolley, 32 × 47;
  - the hostage, 4 × 48 × 28 plus legs 32 × 20;
  - the lift, 48 × 24;
  - this leaves x 80-255 on lines 56-87, enough for 48 × 24 bodies of type 16.
- Type 14's 48 × 36 frames fit neither that nor the 24-line dynamic slot (sprites area).

## 6. The converter plan [D]

### 6.1 Outputs, sizes, banks

| Block | File | Size | Banks | Mapped |
|---|---|---:|---:|---|
| tile sheet (pages 2-3 image, tile n in bank + n/64) | `level2.vram` [0x10000:0x20000] | 65,536 (511 tiles) | 8 | 8000h (`tc_upload`), A000h (`tiles_upload`) |
| map, 25 rows a bank | `level2.map` | 16,000 | 2 | A000h (`get_tile`) |
| packed attributes | `level2.atrp` | 4,016 | 1 | A000h, at the start only |
| level tables: OTILE, ATR2, BOBHASH, descriptor, rowtab, `view_offy`, palette, vat display table | `.otile`, `.atr2`, BOBHASH, new | about 6,200 | 1 | 8000h |
| **map area** | | | **12** | |
| logic `BANK_L2` and the play field (other areas) | | | 3 | |

- **Banks mapped at 8000h** must avoid bank numbers whose low 6 bits are 3Fh (63, 127, 191, 255).
  `tools/mkrom.py` checks this.
- **The Pico+ target** is 53 banks per level (decision 6). The tile sheet's 8 and the map's 2 are in
  use all through the level. Count them with the sprite pool's banks (sprites area).

### 6.2 Steps

1. `msxlvpal`, or a flag of `tools/msxsprites.py`:
   - in: level 1's joint `.pal` and `.remap` and the two Amiga palettes;
   - out: `level2.pal` and `level2.remap`, option C. Level 2's sprite conversion takes these too.
2. `tools/msxconv.py level DATAL2_18.bin --rows 50 --joint build/msx/level2 -o build/msx/level2`.
   This is unchanged and was run here (`out/conv/`).
3. `tools/mapcells.py` with a level argument. It checks level 2's pools and codes and the vats'
   properties.
4. A vat table for the port (in `tools/mapcells.py`, or a `vats_l2.inc` writer):
   - per vat: first row, first column, columns, rows + 2, snapshot offset;
   - per row: its vats;
   - the 48 vat words as tile numbers.
5. `tools/cellmasks.py` and `tools/amitab.py` with level 2's rows (logic area).
6. `tools/mkrom.py` lays out the level-2 blocks after the range's. It writes the descriptor and
   `level2_grade.pal` (and `view_offy` and rowtab per level). `MAP_ROWS` and the other level equates
   become per-level names.

### 6.3 Checks

**At build time** (fail the build):
- **Tiles**: at most 512; every offset the map and the writers use is in `.otile`.
- **Pools**: the object cells fit, 146/143 of 255.
- **Codes**: at most 16. The written values 0, 1 and 2 are among the map's.
- **Vats**:
  - every vat word and every vat cell of the map has attributes 0;
  - no object cell lies in a vat;
  - every vat word's tile is in the sheet.
- **Palette**:
  - entries 0-7 equal level 1's;
  - entries 2, 3 and 7 are free of background colours;
  - colour 0 is black (the HUD split);
  - mean ΔE ≤ A's.
- **Tile cache**: the largest window plus writers fits 256 with a margin, today 148.

**In openMSX, later:**
- **VDP palette**: it equals graded C.
- **Map against the bench**: the map equals the original's cell by cell at a game frame of a level-2
  drive. Use `tools/mapcmp.py` with the vat rule, against `tools/amigaemu.py game --dump`.
- **The refresher**, on both VDPs and the turbo R:
  - no picture with a half-drawn or older vat column;
  - its rate and CPU time;
  - the flip delay on the V9938.
- **Level 1 regression**: its traces must stay identical (the `cp 51` and the descriptor change code
  it runs).

## 7. Defaults chosen (the user is away), each with its alternative

| # | Default | Alternative |
|---:|---|---|
| 1 | Palette C (level 1's layout, level 2's values at 9, 11, 13) | A (level 1's as it is: blues merged), or a refit of 8-15 (D), which reconverts every shared frame |
| 2 | The vats as a display layer (snapshot per vat), outside the map patches | 604 more patches: pools of 3 × 255 or more, and `rd_queue` overflowing |
| 3 | The vat refresher: whole columns, newest look, never tearing, never going back, within the VDP time left | fixed half rate; tearing allowed for twice the rate on the V9958; surface-only animation while a V9938 scrolls |
| 4 | `$EF8E`'s ports compare with 51 in every level | per-level rows: wrong for level 2's row 50 |
| 5 | rowtab, `view_offy` and the palette per level in RAM; `atr_rows` and `view_offx` shared | everything through the tables bank (a bank switch per `get_tile`) |
| 6 | The tile sheet stored raw (8 banks) | per-tile ZX0, −4 banks but about 14-27k T-states a miss (`docs/ROM_BUDGET.md` 6) |

## 8. Open questions and risks

- The refresher's real rate and the V9938 flip delay near vats 0-3, measured in openMSX. If the
  look disappoints, the user chooses between defaults 3's alternatives.
- The liquid's colour: c7 310 → 100 for 8.4 % of level 2, ΔE 11.5. The user approved this colour in
  level 1. Level 2's vats make it prominent: a preview for the user (`png/crop_vat0.png`).
- Sprites area:
  - type 14's 36-line frames against the atlas and the dynamic slot;
  - the 200 frame-id limit (210 sprite frames in level 2);
  - the cut through colour rows (5.2);
  - the Pico+ bank count with the global pool.
- Logic area: `SW_MAX` 32 < 40 spawn entries. The meaning of header +32 (`$16B8`) and +34 (`$C53D`).

## 9. Files of this area

All under
`/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space/l2/map/`:

| Path | What |
|---|---|
| `MAP2.md` | this document |
| `l2map.sym` | the names found (REA) |
| `scripts/vats.py`, `out/vats.txt` | the vat model, tables, step costs |
| `scripts/l2objects.py`, `out/l2objects.txt` | the object list, writers, pools, codes, tile counts |
| `scripts/l2pal.py`, `out/l2pal.txt` | the palette options, errors, previews |
| `scripts/tilecache.py`, `out/tilecache.txt` | tile-cache windows |
| `scripts/vatlooks.py` | vat 0's looks |
| `out/conv/level2.*` | `tools/msxconv.py` run with palette C (scratch) |
| `out/all_asm_l1img.txt` | the earlier REA CLI dumps flattened (main code; used for the writer sweep) |
| `png/level2_{amiga,A,B,C}{,_plain}.png`, `png/level2_compare_half.png`, `png/crop_{blue,top,vat0}.png`, `png/vat0_looks.png`, `png/vat_tiles_amiga.png`, `png/level2_C.pal`, `png/level2_C.remap` | previews and the palette |

The scripts read the repository and write only here. Run them with the project's venv python,
`-I -B`, so that no bytecode lands in `tools/__pycache__`.
