# ROM budget for the whole game

Measured on 2026-10-26 against release v0.1.2 (`build/msx/ROBOCOP2_v0.1.2.ROM`: level 1, the
title, the game over and the statistics screen).

Sources:
- eight area reports of the same day (level 2, level 3, sprites, bonus stages, pictures, music,
  code, hardware);
- a review of those reports that removed double counts and alternatives counted as additions;
- three measurements made for this budget: per-tile and per-row compression of the tile sheets
  and maps, the slack inside the banks already used, and the cost of mirrored frames streamed
  into the play field.

No emulator was run for any of it, so no number here comes from a frame the MSX drew.

Conventions:
- KiB = 1,024 bytes. A bank is 8 KiB, and 1 MiB is 128 banks.
- Banks are counted the way `tools/mkrom.py` places data: each block starts a bank of its own.
  The sprite pools are the exception and are rounded per pool.
- Basis column:
  - **M**: measured, by running the project's converters or counting bytes on the game's data.
  - **M\***: measured through a proxy (zlib -9 × 1.15 for a Z80 LZ such as ZX0).
  - **E**: estimated, scaled from a measured analogue (for example Amiga code size × the port's
    measured Z80/68000 ratio).
  - **D**: design assumption.
- Low, likely and high give the range of the same content in the same formats. Optional content
  (section 3.9) and savings (section 6) are kept out of these three columns.

## 1. Summary

| | Banks | KiB |
|---|---:|---:|
| Used today (banks 0-77) | 78 | 624 |
| Free today (banks 78-127) | 50 | 400 |
| Rest of the game with today's pipeline (one palette per level) | about 102 | about 816 |
| Rest of the game with the plan of section 3 (one palette, one sprite pool), low / likely / high | 58 / 63 / 73 | 464 / 504 / 584 |

- **With today's pipeline, the whole game does not fit 1 MiB.** It is about 52 banks (416 KiB)
  over.
- **With one palette for all levels, it still does not fit.** That palette stores RoboCop's
  sprite data and the frames the levels share once. Even so, the game is **8 / 13 / 23 banks
  over** (low / likely / high). Before any bank rounding the content alone is 411 / 442 / 522
  KiB, which is more than the 400 KiB free in every case.
- **1 MiB needs at least 13 more banks of savings (23 in the high case).** The two largest
  savings that keep all the content are these:
  - Compress each tile of the tile sheets separately: −11 banks, sizes measured.
  - Flip sprite patterns horizontally at run time: −6 banks, estimated.

  Together they bring the likely case to 46 banks, 4 to spare. The high case is still 6 over.
  The CPU cost of both changes has not been measured.
- **A 2 MiB Konami SCC image holds every scenario measured here.** It has 256 banks, 178 of them
  free, enough even for today's pipeline plus all the photos. It needs a few tool changes, and
  devices that hold only 1 MiB cannot run it (section 6.1).

## 2. What the ROM holds today

| Banks | Content | Bytes used | Fill or free | Shared by levels 2-3 under one palette |
|---|---|---:|---:|---|
| 0-1 | Fixed code | 16,149 | 235 | yes |
| 2-9 | Banked code: LC1, LC2, L1, LC3, INPUT, FRONT, FIELD, MUSIC | 47,274 | 18,262 | yes, except L1 (level 1's logic) |
| 10-17 | Level 1 tile sheet (512 tiles, 431 used by the map) | 65,536 | 0 | no |
| 18-20 | Level 1 map, 160 × 51 words | 16,320 | 8,256 | no |
| 21-43 | Sprite blob: RoboCop 112,734 B, level-1 BOB frames 64,702 B | 177,436 | 10,980 | RoboCop, PERMA frames, level 1's SPERMA/MADEX frames, hit spark |
| 44-45 | HUD run-time data | 16,384 | — | yes |
| 46 | Level 1 packed attributes | 4,096 | 4,096 | no |
| 47 | HUD image | 5,760 | 2,432 | yes |
| 48 | Level 1 tables (.otile, .atr2, BOBHASH) | 5,760 | 2,432 | no |
| 49 | Play-field atlas (hostage, gunners 26/28, lift, vehicle) | 7,373 | 819 | no (each level uploads its own) |
| 50-51 | Play-field dynamic frames (explosion, smoke) | 13,824 | 2,560 | yes |
| 52-58 | Title picture, SCREEN 8, 200 lines | 51,200 | 6,144 | yes |
| 59-64 | Game-over picture, 192 lines | 49,152 | 0 | yes |
| 65-70 | RoboCop's speech as PSG PCM, alone and in the music | 49,152 | 5,908 B of fill at the end of each half | yes |
| 71-74 | Title music, SCC | 25,803 | 6,965 | yes |
| 75-76 | Title music, OPLL | 13,238 | 3,146 | yes |
| 77 | SCC effects (MU1's 42) and the gun's opening | 5,405 | 2,787 | yes |
| 78-127 | Free | 0 | 409,600 | |

By kind:

| Kind | Banks |
|---|---:|
| Code | 10 |
| Level-1-only data (tiles 8, map 3, attributes 1, tables 1, atlas 1) | 14 |
| Sprite blob | 23 |
| HUD | 3 |
| Play-field dynamic frames | 2 |
| Pictures | 13 |
| Sound | 13 |

The sprite blob holds RoboCop 110.1 KiB, level-1 BOBs 63.2 KiB and pool padding 10.7 KiB.

Free bytes in the code banks (M, from a rebuild byte-identical to v0.1.2):

| Bank | Free bytes |
|---|---:|
| Fixed | 235 |
| LC1 | 39 |
| LC2 | 5,087 |
| L1 | 985 |
| LC3 | 5,105 |
| INPUT | 11 |
| FRONT | 3,202 |
| FIELD | 1,529 |
| MUSIC | 2,304 |

MUSIC's `music_end` is B700h. On the MSX Pico+ only the 256 B below B800h can hold what the
player reads while the SCC is mapped.

Slack inside the 78 used banks (M):
- 18,497 B free in the code banks.
- 63,238 B (61.8 KiB) of fill at the end of data banks, counting runs of 256 B or more.

Only one of these is a whole bank. Bank 20 holds row 50 of the level-1 map (320 B) and 7,872 B
of fill. `rowtab.inc` stores a bank and an address for each row, so that row can move into bank
46's free 4 KiB, and bank 20 then becomes free.

## 3. What the rest of the game needs

### 3.1 The plan behind the numbers

Decision numbers are those of the port's decision list.

1. **One 16-colour palette for every level: level 1's (`build/msx/robocop.pal`).** With it,
   levels 2 and 3 store none of these again:
   - RoboCop's sprite data, which converts byte-identical (checked with `cmp` in both levels'
     conversions);
   - the play-field dynamic frames;
   - the BOB frames the levels have in common.

   The cost is in section 6, option 1.
2. **One global sprite pool.** Level 1's patterns, colour rows and records are extended with
   those of levels 2 and 3. Each level's tables bank gets its own BOB index and BOBHASH.
3. **Decision 13 applies to levels 2 and 3:** no sprite piece is ever cut, and big objects go
   into the play field. Every frame 48 px wide or more is drawn by the VDP. Its sprite version
   stays for the hit flash, as level 1's gunners kept theirs (decision 16).
4. **Decision 5 stands.** There are no movie photos (PIC1-7, PICF) and no boot logos, as today.
5. **Both bonus stages are ported, with both visits each.**
   - Their one-time graphics are stored compressed with a Z80 LZ (ZX0).
   - Their two tunes come in SCC, OPLL and PSG versions, as the title's do (decision 21).
6. **The ending** has the CMP tune in three chip versions, the WELL DONE text screen and the
   high-score entry. PICF is not shown.
7. **Left out of the plan:**
   - HI1 tune 1. The original stops it before its first tick at the name entry, and the frozen
     title always plays TITM.
   - The cheat and its CH1 jingle.
   - The CMP speech, until the user has listened to it.
8. **Everything else stays in today's formats:** tiles and maps raw, music streams as today.

### 3.2 Level 2

| Block | Low KiB | Likely KiB | High KiB | Banks L/l/H | Basis | Source |
|---|---:|---:|---:|---|---|---|
| Tile sheet: 498 tiles needed of 511, stored as the 64 KiB VRAM image | 62.3 | 64.0 | 64.0 | 8/8/8 | M | level 2 |
| Map, 160 × 50 words | 15.6 | 15.6 | 15.6 | 2/2/2 | M | level 2 |
| Packed attributes (.atrp) | 3.9 | 3.9 | 3.9 | 1/1/1 | M | level 2 |
| Level tables (.otile, .atr2, BOBHASH) | 5.6 | 5.6 | 5.6 | 1/1/1 | M | level 2 |
| Logic bank L2 | 6.0 | 6.6 | 7.5 | 1/1/1 | E | level 2, code |
| Play field: atlas and streamed big frames | 8.9 | 8.9 | 10.9 | 2/2/2 | M | level 2, review |
| **Level 2** | **102.3** | **104.6** | **107.5** | **15/15/15** | | |

- **Tiles.** The map uses 460 MSX tiles and the run-time writers 37 more: 498 of the 511
  distinct DATAL2 tiles, so 14 of the 512 tile numbers stay free.
  - Only 1 tile equals a level-1 tile, so the sheets cannot be shared.
  - At most 107 distinct tiles are in view at once (level 1: 121-125), so the 256-slot tile
    cache is enough.
- **Map.** The level header (REA `read_bytes` at $868C, +28: lowest camera $270) gives 50 rows,
  which is exactly 2 banks of 25 rows.
- **Attributes.** The map uses 8 of the 16 codes, and the writers write only values 0-2.
- **Logic.**
  - 1,510 B of new Amiga code × 1.43 (level 1's measured ratio) = about 2.2 KiB of Z80. The new
    code is: types 1, 2 (with its arrest tail $C91A), 5, 6, 14, 16 and 49 (with obj38's body),
    level_tick_1 $91BC and death $C33E.
  - About 1.2 KiB of level-1 handlers copied into the bank (types 3, 4, 12, 13, 15, 30, 31, 45).
  - 2,014 B of tables (amitab on level2_full.bin), plus the cell masks and the init code.
- **Play field.**
  - The atlas holds the hostage, the 5 lifts, the trolley $8F02 (32 × 47) and Cain (type 2,
    2 × 48 × 56): 7,088 B, using 84 of its 88 lines.
  - Types 14 (48 × 36) and 16 (48 × 24 body) follow the gunners' precedent but do not fit the
    atlas. They are streamed: 2,016 B, or 4,032 B if their mirrors are stored (the high case).
  - The explosion and the smoke come from level 1's banks 50-51.
- **Nothing new** for in-game sounds, the HUD or RoboCop's tables: all 42 MU1 effects are
  already in the ROM.

### 3.3 Level 3

| Block | Low KiB | Likely KiB | High KiB | Banks L/l/H | Basis | Source |
|---|---:|---:|---:|---|---|---|
| Tile sheet: 504 tiles | 63.0 | 64.0 | 64.0 | 8/8/8 | M | level 3 |
| Map, 160 × 50 words | 15.6 | 15.6 | 15.6 | 2/2/2 | M | level 3 |
| Packed attributes (.atrp) | 3.9 | 3.9 | 3.9 | 1/1/1 | M | level 3 |
| Level tables | 5.4 | 5.4 | 5.4 | 1/1/1 | M | level 3 |
| Logic | 8.0 | 10.0 | 13.4 | 1/2/2 | E | level 3, code |
| Play field: 61 frames 48 px wide or more, streamed, plus the lift's 2 parts | 30.3 | 33.6 | 59.4 | 4/5/8 | M | review, this budget |
| **Level 3** | **126.2** | **132.5** | **161.7** | **17/19/22** | | |

- **Tiles.** The map uses 480 tiles and the sheet holds 504; the 16 tiles only the writers write
  are among them. At most 95 tiles are in view at once.
- **Logic.**
  - 4,230 B of level-3-only Amiga code × about 1.55 = about 6.4 KiB. Cain / RoboCop 2 (obj22)
    alone is 764 B of that Amiga code.
  - The rest brings it to about 10 KiB, more than one bank: the framework, the copied level-1
    types 4 and 12, the lists (header, 39 spawn entries, 15 objects, lifts, barriers), the
    handler tables and the masks.
  - LC1 is full, so the new deaths ($C25C, $C360, $C3A8) and the debris helper $C398 must live
    here.
  - Low: 1 bank with heavy sharing. High: Amiga code × 2.31, the ratio of the port's map-object
    code.
- **Play field.** Under decision 13 every frame 48 px wide or more leaves the sprites; level 3
  has 61:

  | Object | Frames |
  |---|---|
  | Boss | 48 × 44 × 18, 64 × 40 × 16, 64 × 32 × 6, 64 × 34 × 2 |
  | Vehicle | 80 × 48 |
  | Others | 48 × 49 × 2, 48 × 24 × 6, 48 × 16 × 6, 48 × 28 × 3, 48 × 12 |

  - As 4-bit pixels they take 33,648 B if the 26 exact mirrors are flipped while streaming, and
    60,144 B if the mirrors are stored (the high case).
  - The static atlas cannot hold them, so they stream into the dynamic slot. That slot must grow
    from 256 to 336 px for the boss.
  - The lift's two parts ($5397C 32 × 29, $53BC0 32 × 16) take 720-735 B.
  - The smoke frames are level 1's (banks 50-51).
  - Low: 10 % of the frames are never drawn. No coverage run exists for level 3.

### 3.4 Sprite pool growth (levels 2 and 3, one palette)

| Block | Low KiB | Likely KiB | High KiB | Banks L/l/H | Basis | Source |
|---|---:|---:|---:|---|---|---|
| Level 2 data not already in level 1's pools | 17.1 | 20.8 | 22.9 | — | M | sprites, level 2 |
| Level 3 data not already in level 1's pools | 44.5 | 49.4 | 54.3 | — | M | sprites |
| **Pool growth, rounded per pool** | **61.6** | **70.2** | **77.2** | **8/9/10** | M | sprites, review |

- **What is shared.** Converted with level 1's joint palette, RoboCop's data for levels 2 and 3 is
  byte-identical to level 1's. So are the PERMA frames, and for level 2 every SPERMA or MADEX
  frame level 1 already holds.
- **Level 2's new data** is 21,337 B:

  | Part | Size |
  |---|---:|
  | New patterns | 402 × 32 B |
  | New colour rows | 301 × 16 B |
  | Records and index | 3,657 B |

  - The 55 DATAL2 frames alone take 17,516 B (the low case).
  - 106 of the new patterns are SPERMA frames that the converter grouped into animations
    differently. One joint conversion avoids that.
- **Level 3's new data** is 50,593 B for 151 frames:

  | Part | Size |
  |---|---:|
  | New patterns | 922 × 32 B |
  | New colour rows | 557 × 16 B |
  | Records and index | 12,177 B |

  - The 151 frames were found by segmenting the level's BOB data by its format. The same check
    on level 1 found 70 of the 74 known frames exactly and missed none.
  - 27,345 B of this are the sprite versions of the 61 big frames, kept for the hit flash.
- **One global pool** grows from 23 to 32 banks, +9:

  | Pool | Today | With levels 2-3 | Banks |
  |---|---:|---:|---|
  | Patterns | 3,257 | 4,581 | 13 → 18 |
  | Colour rows | 1,819 | 2,677 | 4 → 6 |
  | Index and records | | | 6 → 8 |

  - Per-level pools, each padded to banks, would take 4 + 8 = 12 banks instead.
  - The format allows a global pool: pattern numbers are 16-bit, the colour pool stays under 64
    banks and frame ids are per level.
- **High:** +10 % for frames that no coverage run has drawn.

### 3.5 Front end and shared code

| Block | Low KiB | Likely KiB | High KiB | Banks L/l/H | Basis | Source |
|---|---:|---:|---:|---|---|---|
| FRONT2 bank | 2.8 | 5.8 | 7.0 | 1/1/1 | E | code, pictures |
| Additions to FRONT | 1.4 | 1.9 | 2.7 | 0/0/0 | E | code, bonus, pictures |
| Additions to LC2, LC3, FIELD | 0.6 | 1.1 | 2.4 | 0/0/0 | E | code, level 2, level 3 |
| Overflow code bank | 0 | 3 | 8 | 0/1/2 | D | review |
| **Front end and code** | **4.8** | **11.8** | **20.1** | **1/2/3** | | |

- **FRONT2** is a new bank at A000h, beside FRONT at 8000h. It holds:
  - the script interpreter with all 8 commands, the curtain and the wipe;
  - the particle writer and its stroke font (1,152 B);
  - the high scores: compare, insert, the table, and name entry with an MSX keyboard reader;
  - the scripts not yet ported, 1,053 B in all: the briefings of levels 1-3, the bonus stages'
    intros and results, WELL DONE, the continue screen and the high-score screen.

  Low drops the particle writer and draws the titles in the existing bitmap font. Even then FRONT
  cannot take everything.
- **FRONT** (3,202 B free) gets:
  - the game flow (load_level0/1/2, continue, ending): about 0.9 KiB;
  - the bonus-stage glue ($8382/$8420: rating, $8060, continue credit): about 0.8 KiB;
  - a ZX0 decoder, 68-121 B (assembled, not run).
- **LC2, LC3 and FIELD** get:
  - LC2 (5,087 B free): act_0c (level 2, 140 B of 68000 code) and act_20 (level 3).
  - LC3 (5,105 B free): the trolley $8F02 and the 2-part lift.
  - FIELD (1,529 B free): the wider dynamic slot and the multi-part frames.
- **The overflow bank** takes code that would otherwise have to go into full banks: the fixed
  area (235 B free), LC1 (39 B), INPUT (11 B) and MUSIC (256 B usable below B800h). That code
  is:
  - level switching (a per-level descriptor instead of build-time equates);
  - spawn masks for 40 and 39 entries (32 today);
  - frame ids past C8h;
  - level 3's bullet, debris and explosion types;
  - the vat sprite cut;
  - far calls into a level whose logic takes 2 banks;
  - the music player's tune directory, loop points and 48 ticks/s.

### 3.6 Sound

| Block | Low KiB | Likely KiB | High KiB | Banks L/l/H | Basis | Source |
|---|---:|---:|---:|---|---|---|
| CMP, the ending tune: SCC 12,419 + OPLL 8,511 + PSG 5,144 B | 25.5 | 25.5 | 28.0 | 4/4/4 | M | music |
| Brainstorm tune (PZM 1): 6,884 + 3,580 + 1,878 B | 12.1 | 12.1 | 13.3 | 2/2/2 | M | music |
| Shooting-range tune (FRM 1): 16,652 + 16,544 + 5,882 B | 38.2 | 38.2 | 42.0 | 5/5/6 | M | music |
| New effects (HI1 3-4, PZM 3-6, FRM 2-4), PSG and SCC: 877 B | 0.9 | 0.9 | 1.0 | 0/0/0 | M | music |
| **Sound** | **76.7** | **76.7** | **84.3** | **11/11/12** | | |

- **How they were converted.** The project's own encoders ran at the title's quality. The routing
  wrapper used reproduces the title's bytes exactly: scc.bin 25,803 B, fm.bin 13,238 B and the
  PSG title 5,990 B. High adds 10 % for routing changes.
- **Lengths.** Every tune that is started is needed whole:

  | Tune | Ticks | Notes |
  |---|---:|---|
  | CMP | 4,800 | loops at tick 192; plays at 48 ticks/s |
  | PZM | 3,000 | 60 s, restarted for every board |
  | FRM | 5,999 | about 125 s for a 2:00 stage |

- **Bank placement.**
  - One blob per tune, which the bank-crossing reader allows: 11 banks (the likely case).
  - All three packed back to back: 10 banks.
  - Each chip's stream starting a bank, as scc.bin and fm.bin do today: 15 banks.
- **Effects.** The new effects fit in bank 77, which has 2,787 B free. Levels 2 and 3 use MU1's
  42 effects (load_level_music $8614 loads MU1 for every level), so they need nothing new.

### 3.7 Bonus stages: Brainstorm and the shooting range, two visits each

| Block | Low KiB | Likely KiB | High KiB | Banks L/l/H | Basis | Source |
|---|---:|---:|---:|---|---|---|
| Brainstorm code and tables | 4.4 | 5.6 | 7.2 | 1/1/1 | E | bonus |
| Shooting-range code and tables | 7.0 | 8.5 | 10.4 | 1/1/2 | E | bonus |
| Brainstorm graphics, ZX0 | 12.4 | 14.5 | 16.4 | 2/2/3 | M* | bonus |
| Shooting-range graphics, ZX0 | 15.4 | 17.8 | 36.8 | 2/3/5 | M* | bonus |
| **Bonus stages** | **39.2** | **46.4** | **70.8** | **6/7/11** | | |

- **Code.** The Amiga code is 1,930 B (Brainstorm) and 2,970 B (range), measured as REA function
  bodies. It is scaled by 1.42-2.28, the ratios measured on player_move and hits. Added to it:
  - the tables: Brainstorm's boards (752 B); the range's 41 target scripts and 23 descriptors
    (1.4 KiB, which can sit in the range's graphics bank);
  - the MSX glue.
- **Graphics**, as SCREEN 5 nibbles, raw / zlib -9 in bytes:

  | Stage | Part | Raw | zlib -9 |
  |---|---|---:|---:|
  | Brainstorm | Frame (the board is redrawn from the chip tiles) | 22,528 | 1,508 |
  | Brainstorm | Chips | 4,096 | 1,699 |
  | Brainstorm | Two faces | 6,400 | 4,617 |
  | Brainstorm | TV static | 12,800 | 4,538 |
  | Range | Background | 22,016 | 5,244 |
  | Range | Priority plane | 5,504 | 495 |
  | Range | Targets | 20,864 | 4,779 |
  | Range | Hit dissolves | 25,600 | 5,202 |

  - The low, likely and high columns use the zlib size × 1.0, × 1.15 and × 1.3.
  - For the range, high instead stores the dissolves raw for streaming. Its 39 target and
    dissolve frames take 92,928 px against about 110,592 px of free VRAM.
  - Stored raw like today's pictures, the graphics would take about 120 KiB (16 banks).
- **The second visits cost almost nothing.**
  - PUZL on disk 1, once decrunched, is byte-identical to disk 2's.
  - The second Brainstorm differs only by 4 boards (376 B), Ellen's face instead of Murphy's
    (about 2.4 KiB compressed) and some palette entries.
  - The second range differs only by its palette.
  - Leaving the second visits out saves less than half a bank.
- **Music.** The stages' tunes are counted once, in 3.6.

### 3.8 Total of the plan

| Area | Low KiB | Likely KiB | High KiB | Banks L/l/H |
|---|---:|---:|---:|---|
| Level 2 | 102.3 | 104.6 | 107.5 | 15/15/15 |
| Level 3 | 126.2 | 132.5 | 161.7 | 17/19/22 |
| Sprite pool growth | 61.6 | 70.2 | 77.2 | 8/9/10 |
| Front end and code | 4.8 | 11.8 | 20.1 | 1/2/3 |
| Sound | 76.7 | 76.7 | 84.3 | 11/11/12 |
| Bonus stages | 39.2 | 46.4 | 70.8 | 6/7/11 |
| **Total** | **410.8** | **442.2** | **521.6** | **58/63/73** |

Of the 63 likely banks:
- 56 rest on measured data: tiles, maps, attributes, tables, play field, sprites, music and bonus
  graphics.
- 7 rest on code-size estimates: logic L2 1 and L3 2, FRONT2 1, overflow 1, bonus code 2.

### 3.9 Optional content, not in the plan

| Item | KiB | Banks | Basis | Note |
|---|---:|---|---|---|
| PIC1, PIC4, PIC7 (before levels 1-3) and PICF (the ending, 212 of its 224 visible lines): SCREEN 8, ZX0 with a 4 KiB window | 93.0 | 12 packed, 14 one picture per bank; 25 raw | M | decision 5 dropped them |
| PIC2, PIC3, PIC5, PIC6 (before the bonus stages) | 67.3 | 9; 24 raw | M | only with the bonus stages |
| Boot logos DATAE and OAS, SCREEN 5, ZX0 | 5.3 | 1; 6 raw | M | decision 4 plans logos in SCREEN 5; none are shown today |
| CMP speech: one PSG PCM / all five different mixes | 16 / 80 | 2 / 10 | E | CMP sample 1 measures as speech; needs the user's ear (`build/music/cand_CMP_s1.wav`) |
| HI1 tune 1 (high-score music) | 17.5 | 3 | M | the original stops it before its first tick at the name entry |
| Cheat (SERIAL INTERFACE) and the CH1 jingle | 3.8 | 1 | M/E | the in-game F9/F10 keys are already ported; the title matcher is not |
| **All of them** | **266.9** | **38**, one picture per bank | | |

### 3.10 The same game with today's pipeline (one palette per level)

| Area | Banks |
|---|---:|
| Level 2: tiles 8, map 2, attributes 1, tables 1, logic 1, sprite blob 23, play field 2, dynamic frames 2 | 40 |
| Level 3: tiles 8, map 2, attributes 1, tables 1, logic 2, sprite blob 23, play field and smoke 5 | 42 |
| Front end and code, sound, bonus stages (as in 3.5-3.7) | 20 |
| **Total** | **about 102 (97-112)** |

- **Why per-level palettes cost so much.** Each level's own k-means palette changes RoboCop's
  sprite data:
  - Levels 2 and 3 share only 383 of 2,134 and 597 of 2,044 patterns with level 1.
  - RoboCop's 110 KiB is therefore stored again for each level, and the common frames are
    converted again.
  - Pinning only RoboCop's 7 OR colours is not enough: 0 of his 294 records stay identical.
- **A middle way:** a palette per level for the background only, with RoboCop converted on
  entries shared by every level (a converter change). It would come to about 10 banks more than
  the plan:
  - 20-22 sprite banks for levels 2-3 instead of 10-12 (sprites report);
  - 2-3 more banks of play-field dynamic frames.

## 4. Totals against 1 MiB and 2 MiB

| Scenario | Banks needed L / l / H | 1 MiB (50 free) | 2 MiB (178 free) |
|---|---|---|---|
| A. Today's pipeline | 97 / 102 / 112 | 47 / 52 / 62 over | 81 / 76 / 66 spare |
| A'. Background palette per level, RoboCop on shared entries | about 75 likely | about 25 over | about 103 spare |
| B. The plan (section 3) | 58 / 63 / 73 | 8 / 13 / 23 over | 120 / 115 / 105 spare |
| B without the bonus stages and their tunes | 45 / 49 / 54 | 5 spare / 1 spare / 4 over | 133 / 129 / 124 spare |
| B with the bonus tunes on the PSG only | 52 / 57 / 66 | 2 / 7 / 16 over | 126 / 121 / 112 spare |
| B with all the optional content of 3.9 | 96 / 101 / 111 | 46 / 51 / 61 over | 82 / 77 / 67 spare |
| A with all the optional content, photos raw | about 171 likely | — | about 7 spare |

In a 1 MiB image, bank 127 (like bank 63 today) may only hold data that is never mapped at
8000h. The plan has such data: the level logic banks and the map banks are read at A000h. But
`mkrom.py` today treats every data bank up to the dynamic frames as mapped at 8000h, so it must
learn that maps are A000h-only.

## 5. Verdict

**The whole game does not fit 1 MiB as the project builds it today, and the user's fear is
justified.**

| Case | Banks needed | Banks free | Result |
|---|---:|---:|---|
| Today's pipeline | about 102 | 50 | 52 over |
| The plan, which shares RoboCop and the common frames through one palette, low / likely / high | 58 / 63 / 73 | 50 | 8 / 13 / 23 over |

Before any bank rounding, the plan's content is 442 KiB likely and 411 KiB low. Both already
exceed the 400 KiB free.

What would fit 1 MiB:
- **Keeping all the content: the plan plus at least 13 banks of savings from section 6.**
  - The minimum is per-tile tile compression plus the run-time pattern flip: 46 banks likely,
    4 to spare, but 6 over in the high case.
  - Adding the VDP-drawn hit flash and the packing brings it to 39 likely and 49 high, which is
    1 bank to spare.
  - That takes four engine changes whose CPU cost no test has measured. Option 1 (one palette)
    is a fifth, and the user still has to accept its level-3 colours.
- **Giving up content:** the plan without the bonus stages, at 49 banks likely, 1 to spare and 4
  over in the high case. That changes the game's structure (section 6, option 12).

A 2 MiB Konami SCC image holds every scenario in section 4, with 7 to 133 banks to spare. It
costs the devices that hold only 1 MiB (section 6.1).

## 6. Options that change the answer

Savings are counted against the plan (B), likely case.

| # | Option | Saving | Basis | Cost and risk |
|---|---|---|---|---|
| 1 | One palette for all levels and one sprite pool (already in B) | about 39 banks against A (102 → 63) | M | See below the table. |
| 2 | Compress each 128-B tile on its own with ZX0 | −11 banks: level 1 −3 (65,536 → 33,476 B), level 2 −4 (65,408 → 28,809 B), level 3 −4 (64,512 → 24,738 B), each with a 3-B index per tile | M (sizes, round trip checked) | Each tile-cache miss decodes 128 B: about 14-27k T-states (E, from the picture decoders' cost model), several times today's plain copy and 10-19 % of a 25 Hz tick per missed tile. The start of a level decodes the first uploads. The decoder (68 B) must be reachable from the tile-cache code. |
| 3 | Flip sprite patterns horizontally at upload | −6 banks: RoboCop 937 mirror pairs (29.3 KiB) and level 1's BOBs 393 pairs (12.3 KiB), measured; levels 2-3 about 10 KiB, estimated; patterns 4,581 → about 2,930 (18 → 12 banks) | M/E | About twice the CPU per pattern upload. Decision 14 deferred it until ROM space was needed. Needs a 256-B bit-reverse table, and RoboCop's look must be checked again on hardware. |
| 4 | Bonus tunes on the PSG only | −6 banks (50.2 → 7.6 KiB) | M | The bonus stages would sound like the old PSG title, against the user's wish for music close to the Amiga (decision 21). |
| 5 | Music in a "repeat earlier records" format | −5 banks on the new tunes (75.7 → 40.5 KiB); −3 on the title (44.0 → 21.9 KiB: SCC 4 → 2, OPLL 2 → 1) plus 2.1 KiB freed in BANK_INPUT | E (sizes from a model of the format, not built) | A new stream reader in BANK_MUSIC (256 B usable on the Pico+), and every stream checked again tick for tick. Changing the title music needs the user's agreement. |
| 6 | Hit flash of play-field objects drawn by the VDP, so their sprite versions are dropped | −4 banks: level 3 26.7 KiB, level 2 about 3.8 KiB, level 1's gunners and hostage 2.7-5.5 KiB | M (sizes) / E (bank effect) | Work in field.asm and VDP time per flash. It also eases the frame-id limit. |
| 7 | No OPLL version of the new tunes | −3 banks (28.0 KiB) | M | OPLL-only machines (an MSX2+ with built-in FM and no SCC) play those tunes on the PSG. |
| 8 | Pack small blocks into the slack of used banks and into each other | −2 to −4 banks | M (sizes) | See below the table. |
| 9 | Compress each map row with ZX0 and decode the visible rows into a RAM window | −4 banks: level 1 −2 (16,320 → 6,666 B), levels 2 and 3 −1 each (5,076 B and 4,643 B) | M (sizes) / E (cost) | About 4.5 KiB of RAM on a 64 KiB machine, a decode for each new row, and the map patches applied over decoded rows. Risky. |
| 10 | Game-over picture in ZX0 | −2 banks (49,152 → 26,386 B) | M | About 2-3 s of black screen while it decodes (E); the 121-B ring decoder (assembled, not run). |
| 11 | Title picture in ZX0 | −4 banks (51,200 → 18,875 B) | M | The title screen is frozen by the user's rule, and it would add about 1.5-2 s of black screen. Only if the user asks. |
| 12 | Leave out the bonus stages | −14 banks (7, plus 7 of music) and part of FRONT2 | M/E | Changes the original's structure: continues come only from solved Brainstorms, and the range's rating sets the next level's enemy hit points ($8060). |
| 13 | Leave out only the second visits | less than half a bank | M | See 3.7. |
| 14 | Compress whole tile sheets, maps or sprite pools | not usable | M | See below the table. |
| 15 | A 2 MiB Konami SCC image | +128 banks of capacity | M (hardware sources) | See 6.1. |

Option 1's cost is in level 3's colours:

| Colour (level 3) | Pixels | Error under level 1's palette |
|---|---:|---|
| Blue $03A | 1.07 % | dE 52.9, shown as dark blue 012 |
| $B97 | 1.15 % | 17.0 |
| $BBB | 1.14 % | 11.4 |
| Mean, every pixel | | 2.28 → 2.68 |

- Level 2 barely changes: the mean goes from 2.46 to 2.50.
- The joint conversion must keep level 1's bytes, whose look the user validated.

Option 8 frees these banks:
- bank 20, which holds a single map row;
- the 4,016-B attribute blocks of levels 2 and 3, which are read once at level start and can sit
  in any bank;
- the last 1.6 KiB of level 3's streamed frames.

The cost is `mkrom.py` layout work and bank equates per block, and the A000h-only banks (63, 127)
must be respected.

Option 14 does not work. zlib leaves 25-34 % of a tile sheet, 18-25 % of a map and 41 % of the
sprite blob, but:
- the tile cache, the scroll and the sprite uploads need random access;
- a 64 KiB machine has no RAM to unpack a whole level.

Combinations, starting from B (58 / 63 / 73 banks):

| Options | Saving | Banks L / l / H | 1 MiB margin L / l / H |
|---|---:|---|---|
| 2 + 3 | −17 | 41 / 46 / 56 | 9 / 4 / −6 |
| 2 + 3 + 8 | −20 | 38 / 43 / 53 | 12 / 7 / −3 |
| 2 + 3 + 6 + 8 | −24 | 34 / 39 / 49 | 16 / 11 / 1 |
| 3 + 5 + 6 + 8 (no tile compression, all content and music kept) | −18 | 40 / 45 / 55 | 10 / 5 / −5 |
| 3 + 4 + 8 + 10 | −17 | 41 / 46 / 56 | 9 / 4 / −6 |
| 12 alone | −14 | 45 / 49 / 54 | 5 / 1 / −4 |

### 6.1 A 2 MiB ROM

**Capacity.** Every mapper that decodes the bank registers fully has 8-bit registers, so a plain
Konami SCC image can address 256 banks of 8 KiB. 178 of them would be free after today's 78.

**Where it should run.** This comes from sources, manuals and decompiled firmware. None of it has
been tested on hardware.

| Device | Status |
|---|---|
| openMSX | KonamiSCC accepts any size; the project's harness forces the type. |
| MSX Pico+ firmware v2.12 | Its Konami SCC handler accepts any bank number below the ROM's size. The SCC appears only for exactly 3Fh. |
| SX-2 with OCM-PLD v3.9.x | Internal ESE-MegaSCC+ 2048 KB: DIP 4 on for slot 1, DIP 5/6 for slot 2. |
| MegaFlashROM SCC+ SD | 2 MiB Konami5 games ship for it (Dim X, Pampas & Selene). |
| Popolon Flash-ROM SCC, Yamanooto, Konami Ultimate Collection, Repro V1 | 2 MiB supported. |
| 2 MiB MegaRAMs | CIEL 2 MB, the 2014 anniversary MegaRAM. |
| Carnivore2 | Its Konami5 descriptor allows it; no report found. |

**What is lost.**
- 1 MiB MegaRAMs and the original MegaFlashROM SCC+ (1 MiB, mask 7Fh). The 512 KiB devices are
  already excluded by today's 1 MiB ROM.
- Decision 2 ("MegaRAM is the minimum") becomes "a 2 MiB MegaRAM or flash cartridge".

**Changes needed** (the first three done on 2026-10-26: `docs/MSX_ARCHITECTURE.md`, "2 MiB").
- Done: `tools/mkrom.py` takes up to 256 banks and writes `ROM_BANKS`.
- Done: the 8000h check now covers every bank with (b & 3Fh) = 3Fh (63, 127, 191, 255).
  Written at 9000h, such a bank selects the SCC at 9800h-9FFFh, so those banks may only hold data
  read at A000h: level logic, maps, pictures.
- Done: a boot guard in FRONT, only in images over 1 MiB: `cold.asm` `rom_guard` (37 B of code,
  an 8 B tag, a 57 B message) and 6 B in `rc2.asm` init. A 1 MiB device wraps, masks or ignores banks 128 and up without any error:
  the guard reads a tag in the last bank and stops with a message when it is missing.
- Keep BANK_MUSIC's SCC-time data below B800h: the Pico+ decodes the SCC at
  (address & D800h) = 9800h.
- Never write BFFEh/BFFFh or 7FFEh/7FFFh, which switch SCC+ and ESE modes.
- The bank numbers in `msx/*.asm` are already 8-bit and need no change.

**Test first.**
- The user chose the 2 MiB ROM on 2026-10-26 (`docs/DISK_VS_ROM.md`), on the condition that the
  bank test below passes on their devices.
- The bank test: `tools/msxbanktest.py` (`make banktest`) builds a 2 MiB cartridge from
  `msx/banktest.asm`, with no game. Bank b holds b × 3Bh + (o >> 8) × 1Dh + (o & FFh) at its offset
  o (low 8 bits), so one byte names the bank a window shows. The screen shows:
  - for each bank number, written at 9000h and at B000h, whether the window showed that bank
    (a grid of 256 cells and the first wrong ones, such as `80>00` when a device wraps at 1 MiB);
  - every byte of banks 1-255, checked through A000h;
  - how many of 4 values stored at 9800h come back with 3Fh, 7Fh, BFh and FFh at 9000h;
  - the bank switches and reads at A000h a frame allows with 1, 2, 4 ... 256 banks taken in
    turn. The timed loops run from RAM. The Pico+'s page cache shows as a drop.

  In openMSX it passes on the MSX2, MSX2+, turbo R and 50 Hz machines, with the cartridge in a
  primary slot and in subslot 1-0. A 1 MiB image fails with `80>00`; a changed byte shows as `D`.
- **Result on the user's hardware (2026-10-26, `ROBOCOP2_banktest-1.ROM`, ID BT2M-1): PASS on
  both machines**, each with the MSX Pico+ in slot 1, at 60 Hz:
  - the SX-2 (MSX2+), every Pico+ option disabled;
  - the Hotbit (MSX2); its Pico+ settings were not stated.

  On both, 256 of 256 bank numbers are right in each window and every byte of banks 1-255 is
  right. The SCC answers at 9800h for 3Fh only (4 of 4), not for 7Fh, BFh or FFh.

  Bank switches and reads at A000h a frame, with N banks in turn (M):

  | N | SX-2 | Hotbit | openMSX |
  |---:|---:|---:|---:|
  | 1 | 807 | 817 | 829 |
  | 2 | 805 | 816 | 829 |
  | 4 | 804 | 814 | 829 |
  | 8 | 802 | 813 | 829 |
  | 16 | 796 | 807 | 829 |
  | 32 | 784 | 795 | 829 |
  | 64 | 68 | 69 | 829 |
  | 128 | 65 | 65 | 829 |
  | 256 | 64 | 64 | 829 |

  - **The Pico+'s page cache** holds at least 32 and fewer than 64 pages of 8 KiB for banks taken
    in turn. Beyond that, nearly every switch reloads a page.
  - **What a miss costs.** A hit costs about 73-74 T. A reload costs about 860 T: about 240 µs at
    3.58 MHz, or 1.4 % of a 60 Hz frame.
  - **The rule for the layout.** The banks the game reads within a short stretch must stay well
    under 32.
- Run it on the Pico+ and on the SX-2's internal ESE-MegaSCC+.
- Find out which OCM-PLD version the SX-2 runs, and which loader accepts a 2 MiB Konami SCC
  image.
- The Pico+ SRAM page cache refills freeze the Z80. Check that later levels do not touch more
  banks per frame than it holds.

### 6.2 Other mappers and media (not recommended)

- **ASCII16** (256 banks of 16 KiB, 4 MiB): most devices then have no cartridge SCC, and the
  engine, which maps 8000h and A000h independently, would need a rework.
- **Konami SCC with a cartridge's own offset register** (MFR SCC+ SD, Yamanooto, KUC, Popolon
  16 MiB): the image would run on one cartridge model only.
- **NEO8 / NEO16:** the Pico+ and openMSX only, and no SCC.
- **Two 1 MiB ROMs (episodes), or disk plus memory mapper** (decision 6 keeps that door open):
  the common part would be stored twice. That part is about 61 banks: code 10, HUD 3, RoboCop and
  the common frames about 22, pictures 13, sound 13. Not measured.

## 7. Limits that are not ROM space

These must be solved before levels 2 and 3 run. Most cost little ROM, but they land in full
banks.

**Lists and ids**
- **Spawn-walk masks hold 32 entries.** Level 2 has 40 and level 3 has 39.
  - `tools/cellmasks.py` refuses them, and `sw_xm`/`sw_ym` are longs.
  - `uo_free` is in LC1, which has 39 B free.
- **Frame ids stop at 200 sprite frames** (FIELD_ID0 = C8h).
  - Level 2 has 210 sprite frames plus 26-29 field frames.
  - Level 3 has 202 plus 63, more than 255.
  - Fix: the VDP draws the hit flash (option 6), or ids grow to 16 bits.

**Map and play field**
- **Map patch pools** hold 2 × 255 cells and never give them back.
  - Level 2's writers can change 893 cells, 604 of them in the vats.
  - Level 3, at about 216 cells, fits.
- **The field atlas has 88 lines.** Level 2 uses 84 with Cain and the trolley.
- **The dynamic slot is 256 × 24.** Level 3's boss needs 336 px of strips at once.
- **Level 3 has 17 frames that need 4-5 sprites a line** even on one layer, beside RoboCop's 5.
  They must leave the sprites (counted in 3.3).
- **Level 2's tile sheet** uses 498 of the 512 tile numbers.

**Per-level data in code**
- **The fixed area** has 235 B free and holds about 0.5 KiB of level-1 tables:

  | Table | Bytes |
  |---|---:|
  | rowtab | 153 |
  | atr_rows | 102 |
  | view_offx | 145 |
  | view_offy | 43 |
  | flashes | 39 |
  | palette | 32 |

  Each level's set must move to its tables bank.
- **Build-time equates** become a per-level descriptor: MAP_ROWS, SPR_BASE_BANK, BANK_TILES,
  ATR_BANK, FIELD_IMG_BANK, FIELD_DYN_BANK, LVL_YMAX and CAM_*.

**Music and pictures**
- **SCC/OPLL streams loop only to their start.** CMP loops at tick 192 and HI1 at tick 48. CMP
  and the range run at 48 ticks/s.
- **PIC_*_LINES is 8-bit**, so a 256-line picture would wrap. PICF must be cut to 212 lines in
  any case.
- **On the MSX Pico+**, BANK_MUSIC's code and data used while the SCC is mapped must stay below
  B800h. 256 B are left.

**VDP time**
- **One visible vat in level 2** changes about 108 cells every 2 ticks: about 54 tile copies a
  tick, against about 18 a frame.
- **The vat's sprite cut** needs a second line interrupt next to the HUD split, which is a timing
  risk on the V9938.

**Tooling**
- **`build/ram/level3_full.bin` is built without SPERMA** (Makefile line 33), so the frames of
  types 4 and 12 read as zeros. Build it with `RB1 MU1 SPERMA DATAL3 PERMA`.
- **`tools/bobcatalog.py`** does not follow `lea (d,PC)` + `adda.w` tables. It finds about 30 %
  of level 3's BOB bytes and 69 % of level 2's.
- **No coverage run exists for levels 2 and 3.**

**Level 1 correctness (not space)**
- The catalogue reads obj04's frames at $57192 as 16 × 16.
  - The ROM therefore holds 8 junk frames.
  - 3 real frames are missing: $57912 and $58092 at 32 × 32, $58312 at 32 × 38.
- Fix this before the pools become shared. The net change is −0.6 KiB.

## 8. Open questions, by how much they move the total

| # | Question | Moves | Next step |
|---:|---|---|---|
| 1 | 1 MiB or 2 MiB? | the limit, by 128 banks | The 256-bank test image on the Pico+ and the SX-2; revisit decision 2. |
| 2 | Bring the photos back? | +12 to +49 banks: PIC1/4/7 and PICF take 12-14 in ZX0 (25 raw); all eight take 21-23 in ZX0 (49 raw) | The user's decision; it only makes sense with 2 MiB. |
| 3 | One palette for all levels? | about 39 banks (102 → 63) | Show a level-3 preview under level 1's palette beside its own. The alternatives are a palette fitted over all three levels (which converts level 1 again) or the middle way of 3.10 (about +10 banks). |
| 4 | Port the bonus stages? | 14 banks (8 with PSG-only tunes) | The user's decision. Their effects on the game: continues, the $8060 hit points. |
| 5 | Per-tile tile compression? | −11 banks | Count tile-cache misses per tick on the coverage drive (both scroll engines) and time a 128-B decode. |
| 6 | The CMP speech? | +2 or +10 banks | The user listens to `build/music/cand_CMP_s1.wav`. |
| 7 | Music formats and chips? | −3 to −11 banks (options 4, 5, 7) | Build the repeat-record reader on one tune; decide on OPLL for the new tunes. |
| 8 | Run-time pattern flip? | −6 banks | Time a flipped pattern upload against today's. |
| 9 | Compress the game-over and title pictures? | −2 and −4 banks | The title needs the user's explicit request. |
| 10 | VDP-drawn hit flash for play-field objects? | −4 banks | A prototype on level 1's gunners. |
| 11 | Packing small blocks? | −2 to −4 banks | `mkrom.py` layout work; no risk to the picture. |
| 12 | Mirrors in streamed frames: flip while streaming, or store them? | +3 banks if stored | Time a flipped strip upload. |
| 13 | HI1 tune, cheat and CH1, boot logos? | +3, +1, +1 banks | The user's decision. |
| 14 | Level 3's logic and the overflow code | 0 to +3 banks | Known only after porting. |
| 15 | Which frames levels 2 and 3 really draw | about ±1 bank | Fix the level-3 RAM image and bobcatalog, then run coverage drives (tools/amigacov.py). |

## 9. Corrections applied to the area reports

- **Units.** The review's "21.3 KiB" and "50.6 KiB" for the sprite increments are kB. In KiB
  they are 20.8 and 49.4.
- **MUSIC bank.** It has 2,304 B free (`music_end` = B700h), not 2,322.
- **Photos.** They count 0 under decision 5. The pictures report had PIC1-7 and PICF in its
  likely total. Recompressing the title and the game over is listed only as an option.
- **Music.** HI1 tune 1, CH1 and the CMP speech are out of the likely total, which goes from
  115 KiB to 76.7 KiB.
- **Level 3's play field.** The frames 48 px wide or more are added (+33.6 KiB, 5 banks). Two
  reports had them only as an option.
- **Level 2's play field** takes 2 banks (trolley, Cain, types 14 and 16), not 0.
- **Sprite increments** are measured against level 1's pools (20.8 and 49.4 KiB), not against
  RoboCop-only conversions (61.7 and 63.2 KiB). They are rounded as one global pool (+9 banks),
  not as padded per-level pools.
- **The level-3 report's ending item** (110 KiB) is dropped:
  - the CMP tune is counted in sound;
  - PICF is optional;
  - HI1 tune 1 is never heard.
- **Bonus music and bonus effects** are counted once, in sound.
- **Code** beyond the level logic banks (L2 1, L3 2) is FRONT2 plus one overflow bank, not 4 new
  banks.
- **New in this budget:**
  - per-tile and per-row compression, measured;
  - the ROM's slack, measured (bank 20 holds one map row);
  - the mirror cost of streamed play-field frames: +25.8 KiB if the mirrors are stored.

## 10. Evidence

Scratch files of 2026-10-26 (a session's scratch directory, not kept in the repository), under
`/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space/`:

| Path | What it holds |
|---|---|
| `sprites/out/l2_l1pal.*`, `sprites/out/l3_l1pal.*` | The level-2/3 conversions with level 1's palette |
| `sprites/perframe.py` | Per-frame sprite and field sizes |
| `level2/conv/level2_joint_l1pal.*`, `level3/conv/level3j.*` | Tile sheets and maps |
| `music/music/summary.json`, `music/music/reuse.json` | Stream sizes, measured and modelled |
| `pictures/summary_pictures.json` | Picture compression |
| `bonus/msx_sizes.json`, `bonus/summary.json` | Bonus-stage graphics and code |
| `code/mirror/out/rc2.labels` | The rebuild byte-identical to v0.1.2 |
| `hardware/pico_re/`, `hardware/ocm/` | Mapper evidence |
| `budget/tilecomp.py`, `budget/tilecheck.py` | Per-tile and per-row compression with a round-trip check |
| `budget/totals.py` | The sums of this document |
