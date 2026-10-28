# Level 2: the Tokugawa brewery, the whole level

Written on 2026-10-27 as the plan for the phase after the shooting range. The workflow that asked
for it relayed the user's orders:
- the next phase is **level 2, complete**: the way in after the range, the level itself, and the
  way out through the statistics and both bonus stages' second visits;
- level 3 is not ported now;
- no release until level 2 is whole and working. The user cannot test on hardware before the
  delivery, so **everything must be shown to work in openMSX first**.

The rules that bind the port (`docs/MSX_ARCHITECTURE.md` "Decisions", `CLAUDE.md`; the decision
numbers are those of the phase's task):
- SCREEN 5 for everything, and pixel-exact 1:1 art.
- The characters are hardware sprites in full OR colour, cut into 16-line bands. No sprite ever
  flickers, loses a piece or has one rewritten.
- Big objects are drawn into the play field by the VDP: the hostage, the lift, the vehicle, the
  gunners that stay put, explosions and smoke (decisions 11-16). Left = right mirrored (14).
- `ENEMY_CAP` 1, and the hostage does not count (18, 25).
- The game logic runs at 25 Hz, ported routine by routine, trace-identical to the Amiga bench (10).
- Damage to RoboCop × 3 (`DAMAGE_X`), the missiles × 2 at most (17, 19).
- The colour grade applies to game play only (24).
- The PSG always; an SCC in any slot and MSX-MUSIC or an FM-PAC when present; the in-game effects
  on the SCC (21, 23).
- The digitised photos are dropped but the title and the game over (5). Between-level scenes are
  text screens in the game's font.
- The MSX2 (V9938) is the baseline, V9958 features when detected, the turbo R (the R800 for the
  game) must work, generic hardware only.
- Level 1's mechanics, Brainstorm, the range and the title do not change.
- The ROM stays within 2 MiB (256 banks), with room left for level 3.

Base: five area reports of the same day (flow, map, logic, sprites, bench: section 9) on the
repository at `3c3a735` (branch `range`), read only. The method follows `docs/BRAINSTORM.md` and
the range's plan (`RANGE.md`). No emulator ran for any of it. The reports disagree in a few places;
section 10 lists each and what this plan takes.

Tags:
- **V**: verified, by REA (Ghidra 12.1.4 provider, raw-binary m68k, entry 0x0, seeds
  `analysis/ghidra_seeds.tsv`, plus the four `+entry` seeds of 2.11) on `build/ram/level2_full.bin`
  (sha256 `a039a158…0a88b09`); by a byte read or a script on the game's data; by a bench run of the
  original (Unicorn: the bench report's `l2bench.py`, built on `tools/amigaemu.py`); or by the MSX
  source at `3c3a735`;
- **I**: inferred, not confirmed by a run;
- **D**: a design decision for the port;
- **E**: estimated.

The main code `$8000-$125FF` is byte-identical in `level1_full.bin` and `level2_full.bin` [V: byte
compare, first difference at `$28089`]. REA names and seeds from either image apply to both, and
level 2's tables can be copied from either.

## 1. Summary

- **What level 2 is [V].**
  - RoboCop starts at (352, 784), bottom left, with 7:30 on the timer. He climbs a brewery 2,560 ×
    800 pixels: five lifts, four trolleys that carry him over vats of bubbling liquid, falling
    drips, rolling tyres, homing drones, walking gunmen, a grenadier, the marker spawns and ten
    hostages.
  - **The level ends when RoboCop touches type 2**, the armed suspect on the roof that the briefing
    calls Cain ("ARREST CAIN"). The arrest tail `$C91A` queues "ARREST SUCESSFUL." (the original's
    spelling) and sets `$16D0`. There is no boss fight: the suspect's hit points are set back to 4
    every frame.
  - The level's lists live in the main code: header `$868C`, spawn list `$97B0` (40 entries), object
    list `$A828` (44), markers `$C5EC`, 7 vats `$95B2`, 9 special objects `$8FE0` (5 lifts, 4
    trolleys). DATAL2 holds the 512-tile sheet, the 160 × 50 map and level 2's own BOB graphics.
    **MADEX is DATAL1's last 25,340 bytes, byte for byte.**
  - Each enemy's hit points come from the range's rating (`$8060`).
- **The way in and out [V].**
  - After the range, `load_level1` `$8582` shows the briefing `$110F0` ("TOKUGAWA BREWERY" / "ARREST
    CAIN"), PIC4, then loads MU1, MADEX and DATAL2. `level_init` `$871A` then reads level 2's
    40-byte header.
  - After the arrest: the statistics, Brainstorm (D0 = 4), the range (D0 = 5), the level-3 briefing
    `$110B4`, PIC7, DATAL3.
  - A death restarts level 2 with nothing reloaded: the map keeps its changes. A game over offers a
    continue when Brainstorm has given a credit.
- **The port [D].**
  - **One level start for both levels** (`lv_go`) reads a per-level descriptor. It replaces about
    twenty build-time equates. Level 1 runs the same steps with the same values, and its traces
    stay at 0 differences.
  - **A logic bank `BANK_L2`** holds level 2's lists, its seven new object types, the vats' logic
    and copies of the level-1 handlers it shares. The trolley goes into LC3 and the blinking mine
    (`act_0c`) into LC2.
  - **The map** converts with the existing tools. The palette is **C**: level 1's index layout with
    level 2's own values at entries 9, 11 and 13. RoboCop's data and every shared frame stay
    byte-identical.
  - **The vats leave the map patches.** The logic keeps their phases exactly. The display redraws
    whole vat columns at the newest look the VDP can afford, never torn and never older.
  - **The sprites**: one global sprite pool (+4 banks). Type 1 becomes joint compositions (3 sprites
    a line). Types 2 and 14, type 16's body and the trolley go into the play field. In level 2 the
    atlas grows to 112 lines, and the dynamic slot moves to page 2.
  - **The flow**: the briefings are text screens in the game's font (`fe_text`). The continue offer
    (`$11FD2`) is ported. After level 2 come the stages' second visits, the level-3 briefing and the
    title (level 3 is missing).
  - **The rating**: `ac_diff` (the port's `$8060`) is set to SHARP by a new game only, so level 2
    gets the range's rating, as on the Amiga.
  - **The sound needs no new data**: level 2 requests MU1's effects, all converted for level 1.
- **ROM [E].** The pool +4 banks (built in place: the later banks shift by 4 once), Brainstorm's
  visit-2 pictures +4, level 2 +15: **about 127 banks**. That just fits 1 MiB; every candidate also
  gets its `ROM_2M=1` twin. The whole game then comes to about **152-164 of 256 banks**.
- **Verification [D]: all in openMSX.**
  - The logic: 12 bench references and 4 new drives, 1,022 fields, 0 differ.
  - The picture: the start check, the field check, the objects against the bench, frame-to-frame
    coherence, the lost counters, stills against the converters' renders, the vats' and the cut's
    own checks.
  - The sound per tick on every chip set.
  - The regression: level 1, Brainstorm, the range and the title unchanged; the product from a fresh
    machine; `tools/msxmatrix.py`; the 2 MiB product.
- **The plan [D]**: 25 steps in three milestones (section 5).
  1. Level 2 playable, its logic trace-identical (steps 0-11).
  2. The complete picture (steps 12-16).
  3. The sound and the flow with both stages' second visits (steps 17-24).
- **Test builds [D]**: `LV_TEST=2` starts in level 2 once at power-on, with `LV_CARRY` for the
  score, lives, credits and rating. `CHEAT=1` maps the original's level-end and energy keys. The
  product's flow does not depend on either (section 6).
- **Defaults (section 7)**: 50 choices, each with its alternative. The ones the user should look at
  first:
  - the briefing's title typed in the 8 × 8 font (1);
  - the ending after level 2 while level 3 is missing (5);
  - palette C, with the vats' red-brown liquid (16);
  - the vats' animation rate (18);
  - `ENEMY_CAP` in level 2 (25);
  - the arrest scene's view (31);
  - type 1 as joint compositions (33).

## 2. The original

### 2.1 The way into level 2 [V]

`load_level1` `$8582` (REA `procedure_assembly`; the bench ran it for real):

| Address | What |
|---|---|
| `$8582` | `clr.b $8580` (`datal1_resident`: DATAL2 overwrites DATAL1) |
| `$8588`-`$8592` | the statistics `$85D8`, Brainstorm `$8382` (D0 = 2), the range `$8420` (D0 = 1): ported (`front_stats`, `front_bonus`, `front_range`) |
| `$8596` | `moveq #2,D0` and 3 `nop`s: a removed 6-byte call (**I**: the disk-2 prompt) |
| `$859E` | `lea $110F0,A0` / `jsr $10762`: **the level-2 briefing**, then `$FE14` (music stopped, palette black, `clear_game_vars`) |
| `$85AA` | `moveq #3,D0` / `jsr $11E06`: PIC4, 251 VBLs or fire. **Dropped** (decision 5) |
| `$85B2` | `move #$2700,SR`: no interrupts while loading |
| `$85B6` | `bsr $8614` `load_level_music`: MU1 to `$18000`, init only. **No tune** |
| `$85B8` | MADEX (`$8579`), A1 = 0: the name table's destination `$45250`, PP20 |
| `$85C4` | DATAL2 (`$1012F`), A1 = 0: `$28000`, PP20; a tail `jmp` into the loader, which returns into `level_init` at `$8764` |

The loader's name table (`$14E`, decoded): MU1 id 9, plain, `$18000`; PIC4 id 16 plain `$6FFA0`;
MADEX id 17, PP20, `$45250`, 25,340 B; DATAL2 id 18, PP20, `$28000`, 105,816 B (to `$41D57`).

- **MADEX** (`MADEX_17.bin`) equals `DATAL1_10.bin[1D250h:]`: 25,340 bytes, 0 differ [V: data].
  - DATAL1 spans `$28000-$4B54B`, so MADEX is its tail `$45250-$4B54B`: the explosions, the smoke,
    the hostage and the nuke that levels 1 and 2 share.
  - It is reloaded because FRNG's decrunch (`$1EA00-$485D9`, both visits) overwrote that range [I:
    the reason; the ranges are V].
  - The port has nothing new to convert for it.
- **The briefing `$110F0`** (393 calls, 394 VBLs without fire; `build/front/scripts.json`):
  1. `FF 04 30`: the particle writer's set-up 4, "TOKUGAWA BREWERY", colour set A (head 7, middle 8,
     final 4), origin (16, −24): bitplane (32 + 16i, 40-53). 1 call;
  2. `FF 03`: the particle writer until its 24 particles are idle. 124 calls;
  3. `00 0C 04` "ARREST CAIN" (column 12, row 4): 1 + 11 calls;
  4. `FF 02 40`: a wait of 256 calls;
  5. `FF 07`: the end. With fire the screen ends at its first call from the 50th on. The panel
     stays below, and its messages tick on.

### 2.2 `level_init` and the header [V]

`level_init` `$871A`, in order:
1. The player's init and stop all; the VBL music tick off.
2. `seq $16CF` when `$8050` = `$8052` (the level already loaded).
3. The load table `$86FA`: entry `$8050` for a restart, entry `$8050` + 4 for a load (then `$8052`
   = `$8050`).
4. `clear_game_vars` `$FE96`: `$B00-$16EB`, `$802D`, `$802E` and `$804D` cleared, `$B02B` = 7Fh.
5. The header at `$8664` + 40 × `$8050` into the code and the variables.
6. The fixed values: `$B2D8` = 108h, `$B2FC` = −70h, energy `$169A` = 100h, the can `$169C` = F0h;
   the music tick on.
7. `set_weapon(0)` `$FD30`: weapon and ammo reset at every level start.
8. Every object-list entry but type 58h back to look 0 and 4 hits; the map objects' pass.
9. `$F89D` = Ah (the start pose: the gun's opening), the level-3 test `$88AC`, `setup_ciab_timer`.

**The headers** (`read_bytes $8664`, 3 × 40):

| Offset | Goes to | Level 1 | **Level 2 (`$868C`)** | Level 3 |
|---|---|---|---|---|
| +0 | `$9C18` object list | `$A562` | **`$A828`** | `$AA3A` |
| +4 | `$915E` hazard list | `$9538` | **`$95B2`** | `$95EC` |
| +8 | `$8B54` special objects | `$8FC0` | **`$8FE0`** | `$9008` |
| +12 | `$B0E` spawn list | `$9626` | **`$97B0`** | `$99E2` |
| +16, +18 | `$15D0`/`$B04`, `$15D4`/`$B06`: **the start** (RoboCop and the camera) | (144, 800) | **(352, 784)** | (1184, 784) |
| +20, +22 | `$15D6`, `$15D8` (`$87A4`/`$87A8`): `obj_relocate`'s target | (996, 640) | **(192, 112)** | (224, 544) |
| +24 | `$C598`, `$C692` marker table | `$C59C` | **`$C5EC`** | `$C624` |
| +28 | `$B08` the camera's lowest y | 640 | **624** (50 rows × 16 − 176) | 624 |
| +30 | `$804A` timer (BCD) | 10:00 | **7:30** | 7:30 |
| +32 | `$16B8` spawn delay | 5Ah | **2Eh** | 3Ch |
| +34 | `$C53D` marker mask (byte) | 7 | **7** | 3 |
| +36 | `$F8C6`, `$F8BC` palette (the fade's source) | `$FFF6` | **`$10036`** | `$10036` |

- **The tests of `$8050` in the main code** (REA `xrefs $8050`): `$81B8` (+ 1 at a level's end),
  `$873A`/`$876C` (`level_init`), `$FFC4` (new game), `$0122` (the loader's PUZL switch), `$83B8`
  (Brainstorm's decrunch, visit 1), `$88AC` (level 3's extras), `$8EB0` (`cmpi.w #2`: level 3's
  lift look) and **`$91A4`, the hazard dispatch `$91B0` + 4 × level: level 2 runs `level_tick_1`
  `$91BC`**. No object handler reads the level number. `$8052` is used only at `$873E`/`$8748`.
- So **what differs per level is short**: the header, the data files, and the hazard dispatch.
  Everything else that is level 2's own lives in routines only its lists reach (2.4, 2.5).
- **What carries over from level 1** [V: the bench's flow start against its direct start]:

| Kept (nothing between the levels writes it) | Reset by `level_init` / `clear_game_vars` |
|---|---|
| the score `$8046-$8049` (with the stages' points) | `$B00-$16EB` (energy, statistics counters, the random word `$B32`, the objects' and the player's state) |
| lives `$8034` (an extra life from 10 hostages included) | `$802D`, `$802E`, `$804D` (inputs); `$B02B` = 7Fh |
| credits `$805E` (+ 1 per solved Brainstorm) | the header's 12 fields (table above) |
| `$8060`, the range's hit-point table | energy 100h, the can F0h, camera offsets 108h / −70h |
| `$804F` (the cheat), the high scores, `$8052` | weapon 0 and its ammo, the timer, the object list but type 58h, the fade-in |
| the code-area variables `level_init` does not patch: the marker step `$C44A`, the flash countdown `$F826`, the explosions' divider `$F07E`, the vehicle state `$8C98` | |
| HUD message state `$8054-$805B` (display only) | |

  The code-area carry matters: without `$C44A` = 13 and `$F07E` = 1 (what `drive_end` leaves), 26
  addresses differ from the flow's first row, because the marker step changes which enemies spawn.
  The port keeps the same split: `AC_VARS` is cleared only at power-on, AG at a new game, the AM
  mirror at every level start.

### 2.3 The map and its animations [V]

**DATAL2** (105,816 B at `$28000-$41D57`):

| What | Where | Size |
|---|---|---|
| tile sheet | `$28000-$37FFF` | 512 tiles × 128 B: 16 × 16 px, 4 planes interleaved per line |
| map | `$38000-$3BE7F` | 160 × 50 words: DATAL offset `& ~$7F` \| attributes |
| level 2's own BOBs | `$3BE80-$41D57` | 24,280 B: type 5 at `$3BFC0`, type 6 at `$3C920`, type 2 at `$3D280`, type 14 at `$3DFA0`, type 1's legs at `$3E810`, type 16's body at `$40818`, type 49 at `$41358` |
| MADEX | `$45250-$4B54B` | 25,340 B: DATAL1's tail (2.1) |
| SPERMA (shared) | from `$4B68A` | the lift's `$4B68A` (48 × 24), the trolley's `$4B95A` (32 × 47) |

- `draw_background` `$BCCA` is the same for every level: the map at `$38000`, tiles at `$B1E` (set
  to `$28000` at `$87E8`) plus `word & $FF80`, 19 × 12 tiles.
- **50 rows**: 624 + 176 = 800 = 50 × 16. Camera x runs 0-2272 (the immediate at `$B2F0`, the same
  for every level); camera y up to 624.
- The map uses 461 tile offsets (460 graphics after the MSX remap) and 8 attribute values: 0, 1, 2,
  3, 8, 9, Bh, Dh. The writers use 113 offsets, 37 of them not in the map at the start: 498 in all.
  All 512 offsets hold distinct graphics; 511 stay distinct after the remap.
- **Only two kinds of routine write level 2's map** (REA sweep of every caller of `$EF8E` writing
  through A0 and every `(140h,A0)` / `(280h,A0)` user): the map objects' looks, and the vats.
  `$933A`/`$9436` are levels 1 and 3's hazards; `$EAA6`, `$EA50`, `$EBB8` belong to types 40-42,
  which level 2 never spawns; `$AF08`'s `add.w (A0)` writes an enemy slot, not the map.

**The map objects** (`$A828`, 44 entries of 12 bytes; activators through the BRA table at `$9EC4`):

| Entries | Map type (offset) | Activator | Look | What they do |
|---|---|---|---|---|
| 0-3 | 12 (30h) at y 144, x 1184, 1312, 1472, 1776 | **`act_0c` `$9EE8`**, new | 5 × 2: `$A4A2`, `$A4B6`, gone | a mine: one cell blinks; stepping on it explodes it |
| 4 | 13 (34h) at (672, 96) | `act_10` `$9FC4` `obj_relocate`: ported | 2 × 4 | 80 ticks of "up" → (192, 112) |
| 5-9 | 0 (00h) at (1056, 224), (1136, 336), (1120, 579), (1872, 624), (2368, 256) | `$9C76` look with a collision slot: ported | 3 × 3, 4 looks + gone | shootable blockers (4 hits); pickups 4, 8, 12, 16, 24 |
| 10, 11 | 1 (04h) | `$9C76` | 2 × 1 | shootable; pickups 28, 28 |
| 12-27 | 3 (0Ch) | `act_04` `$9F84` floor switch: ported | 4 × 2, 4 looks | trapdoors |
| 28-43 | 2, 4-8, 10, 11 | `act_08` `$9EA4`: ported | 2 × 2: `$A3AE`, `$A3B6`, gone | crates that explode at look 4; pickups 4-32 |

- They can change **289 cells** (146 in even rows, 143 in odd rows) and write only attribute values
  0, 1 and 2, all among the map's 8. The port's two patch pools hold 255 each.
- No conveyor, barrier or beam: activators 14h, 18h and 1Ch do not appear.
-  **`act_0c` `$9EE8`** rewrites the look word `$A4A6` (row 0, column 2 of look `$A4A2`:
  `A280 A280 [E680] A280 A280 / A901 CA81 FF81 CA81 A901`) every frame: `$E680`, or `$9700` when
  game-frame bit 2 is clear. So one cell per mine blinks every 4 frames. Both words have attributes
  0.

**The vats** (`level_tick_1` `$91BC`; records at `$95B2`: x left, y, x right, rows):

| Vat | x | y | Cells (columns × rows) | First cell (row, column) | Trolley |
|---|---|---|---|---|---|
| 0 | 848-1024 | 640 | 12 × 9 = 108 | (40, 45) | 0 |
| 1 | 1296-1440 | 640 | 10 × 9 = 90 | (40, 73) | 1 |
| 2 | 1568-1712 | 640 | 10 × 9 = 90 | (40, 90) | 2 |
| 3 | 2016-2256 | 688 | 16 × 6 = 96 | (43, 118) | 3 |
| 4 | 1904-2240 | 288 | 22 × 4 = 88 | (18, 111) | — |
| 5 | 1264-1568 | 288 | 20 × 4 = 80 | (18, 71) | — |
| 6 | 608-800 | 288 | 13 × 4 = 52 | (18, 30) | — |

- **604 cells in all**, at map rows 18-21 and 40-48, none shared with a map object.
- **Every vat word and every vat cell of the map has attributes 0.** Each static column matches one
  phase of the tables. **The vats change only tiles, never anything the logic reads.**
- The animation: each column cycles through 8 looks, bubbles rising. It is drawn frames, not a
  texture scroll: after the best vertical shift, 67-80 of a column pair's 512 pixels still differ.
  The columns start at scrambled phases.
- One step every 2 ticks (80 ms) changes up to 107 cells of vat 0.
- Only vats 0 + 1 (camera x 881-909) and 1 + 2 (1153-1325) can be in the window together. The first
  of each pair is the wider or equal, so every vat's columns advance when it is written (2.5).

**The special objects** (`$8FE0`, records `$9088-$911D`; dispatch `$8B8C` `jmp ($8B92,PC,D2)`:
handler 0 lift `$8DE6`, 4 trolley `$8F02`, 8 vehicle):

| Record | Kind | x | y | Path |
|---|---|---|---|---|
| `$9088` | lift L0 | 174 | 789 | 709, 789 (waits at a stop) |
| `$9098` | lift L1 | 542 | 789 | 629, 709, 789 (waits) |
| `$90AA` | lift L2 | 2542 | 789 | 469, 709, 789 (ping-pongs, period 320) |
| `$90BC` | lift L3 | 239 | 468 | 308, 468 (period 160) |
| `$90CC` | lift L4 | 2543 | 181 | 165, 309, 389 (period 224) |
| `$90DE` | trolley 0 | 832 | 592 | x 848-1008, over vat 0 |
| `$90EE` | trolley 1 | 1296 | 592 | x 1304-1408, over vat 1 |
| `$90FE` | trolley 2 | 1576 | 592 | x 1576-1712, over vat 2 |
| `$910E` | trolley 3 | 2016 | 640 | x 2016-2224, over vat 3 |

- The records live in the code area: they keep moving across deaths. The lifts take level 1's BOB
  path (`$8EB0` tests for level 3 only).
- The trolleys shuttle 2 px a frame whatever RoboCop does [V: bench]. Trolley k reaches its left end
  at 168 + 160n, 108 + 104n, 136 + 136n and 208 + 208n.

**The trap of `$EF8E`** [V]. `$EF8E` adds `map_row_offsets[row]` only for rows < 51 (`$EFA4`
`cmpi.w #$66`), a constant for every level. Level 2's row 50 is DATAL2's BOB data after the map: 35
of its 160 words have a nonzero low nibble, so `$EF8E` answers "solid" there.

**The palette** (REA `read_bytes $FFF6`, `$10036`). COLOR16-31 (RoboCop's sprites) are identical in
levels 1 and 2. Five background colours differ:

| Colour | Level 1 | Level 2 | 3-bit, level 1 → level 2 | Share of level 2's map |
|---|---|---|---|---:|
| c5 | 024 | 03A | 012 → 015 | 0.05 % |
| c6 | 012 | 025 | 001 → 012 | 0.19 % |
| c10 | B00 | A00 | 500 → 500 | 0.07 % |
| c11 | 800 | 700 | 400 → 300 | 0.11 % |
| c15 | CCC | BBB | 666 → 555 | 0.69 % |

### 2.4 The objects [V]

**The spawn list** `$97B0` (40 entries of 14 bytes: x, y, type +4, flags +7, reload +8, count +10,
spawned +12; end word at `$99E0`):

| Entries | Type | Where | Flags, reload |
|---|---|---|---|
| 0-9 | 45 hostage | ids (y & 15) 0-9 | 40h (once), 999 |
| 10, 11 | 1 walking gunman | (384, 664), (672, 424) | C0h (once, at the screen's edge), 300 |
| 12-17 | 49 homing drone | y 16, x 1504-2416 | 0, 60-190 |
| 18-26 | 5 drip | y 368, x 772-2196 | 0, 45-64 |
| 27 | 6 rolling tyre | (416, 448) | 0, 40 |
| 28 | **2 the armed suspect** | (384, 56): the roof | 40h, 32767 |
| 29 | 14 grenadier | (320, 77) | 40h |
| 30-39 | 4, 12, 13 (×10) | y 12-59, x 272-2476: the top corridor | 40h / 60h, 32767 |

- Flag bit 5 (60h) is read by nothing in `update_objects` [I: no other reader found].
- **The markers** `$C5EC` [bands, type, y offset]: (2, 3, 53), (7, 4, 69), (1, 12, 62), (1, 13, 65),
  (6, 14, 50), (7, 15, 56), (7, 16, 56), (7, 30, 51), (7, 31, 67). They spawn at floor cells
  (attribute bit 3) at the view's edges every 8 frames (mask 7), once the delay (2Eh, + 5Ah per
  enemy's death) has run out.
- No level-2 type spawns another type. Type 38's launch mailbox `$E67A-$E67E` is written only by
  level-3 types (REA xrefs `$E67C`).

**The types** (`update_objects` reads P(t) = `$BEA6` + 16t: width +4, height +6, score +8, handler
+10, death +12, hit-point class +14). Hit points at spawn = byte [`$8060` + class]; a hit takes one
point while the count is 0 or more, so h points take h + 1 hits:

| Type | What | Handler | Death | w × h | Score | Class | SHARP / GOOD / FAIR / POOR |
|---|---|---|---|---|---|---|---|
| 1 | walking gunman, legs and torso | `$C736` **new** | `$C31E` | 24 × 46 | 250 | 3 | 2 / 3 / 3 / 4 |
| 2 | **the armed suspect** (the level's end) | `$C868` + `$C91A` **new** | `$C2D8` | 24 × 48 | 1500 | 7 | 99, then 4 every frame |
| 3 | kneeling walker | `$CB6E` | `$C2EE` | 32 × 50 | 350 | 2 | 1 / 2 / 3 / 3 |
| 4 | gunner | `$CFB0` | `$C31E` | 32 × 50 | 200 | 0 | 0 / 1 / 2 / 3 |
| 5 | drip (falling debris) | `$D0E2` **new** | `$C1FA` (`rts`) | 15 × 15 | 125 | 7 | 99 |
| 6 | rolling tyre (barrel) | `$D1E2` **new** | `$C33E` **new** | 21 × 21 | 250 | 1 | 1 / 2 / 3 / 3 |
| 12 | | `$CEF8` | `$C31E` | 31 × 48 | 200 | 0 | 0 / 1 / 2 / 3 |
| 13 | | `$CE72` | `$C31E` | 31 × 48 | 200 | 1 | 1 / 2 / 3 / 3 |
| 14 | grenadier that stays put | `$CE0A` **new** | `$C2EE` | 40 × 48 | 250 | 2 | 1 / 2 / 3 / 3 |
| 15 | gunman | `$CA78` | `$C31E` | 31 × 50 | 225 | 0 | 0 / 1 / 2 / 3 |
| 16 | walker with a big gun | `$CD7A` **new** | `$C31E` | 31 × 50 | 225 | 0 | 0 / 1 / 2 / 3 |
| 30, 31 | walkers | `$CA14`, `$CA3E` | `$C31E` | 25 × 48 | 225 | 1 | 1 / 2 / 3 / 3 |
| 45 | hostage | `$ED1E` | `$C1FC` | 26 × 35 | 0 | 2 | 1 / 2 / 3 / 3 |
| 49 | homing drone (missile) | `$E6C0` + `$E728-$E7B1` **new** | `$C35A` | 15 × 15 | 345 | 1 | 1 / 2 / 3 / 3 |

- The tables (`$C716-$C735`): SHARP 00 01 01 02 03 03 04 63, GOOD 01 02 02 03 03 04 04 63, FAIR 02
  03 03 03 04 04 04 63, POOR 03 03 03 04 04 04 05 63. Both reads (`$C512`, `$C706`) are PC-relative
  to `$8060`.
- A POOR rating makes types 4, 12, 15 and 16 take four hits instead of one.
- **New**: types 1, 2, 5, 6, 14, 16, 49 and the death `$C33E`. **Ported in level 1**: types 3, 4,
  12, 13, 15, 30, 31, 45 and the deaths `$C1FA`, `$C1FC`, `$C2D8`, `$C2EE`, `$C31E`, `$C35A`. Their
  tables (`t3_gfx`, `t4_*`, `t12_*`, `t30_dy`, `t45_*`) are main-code tables. Their BOB addresses
  inside `$28000-$4B54B` read DATAL2 or MADEX in level 2: the hostage's (`$4B31C`, `$498DC`) are
  MADEX's, so the same bytes.
- Coverage [V: bench]: all 15 types seen. 16 procedures run only in level 2: the trolley, the vats,
  `act_0c`, the deaths `$C33E` and `$C35A`, types 1, 2, 5, 6, 14, 16, 38's body and 49, and pieces
  of `$8064`, `$871A`, `$9C06`. 431 blocks (4,136 bytes) never run in level 1's coverage.

### 2.5 The logic, routine by routine [V]

REA listings of every routine below (590 instructions; the logic report's `level2_new.lst`).
Conventions: `x`/`y` are world words (map pixel x = world x − 128); a slot byte at Amiga offset d is
the port's `IX + (d ^ 1)`; `update_objects` leaves D7 = type × 16 (`$C3F6`) and frees a slot whose
handler returns D0 < 0. Drawing: `$AB08` plain (`bob_draw`), `$AC44` first part (`bob_part`),
`$AC56` last part (`bob_part2`), `$AC6E` white silhouette (`bob_flashd`).

**The trolley `$8F02`** (special handler 4). Inputs: the record A3, D0 = its x, D1 = its y, the lift
entry A0 = `$B4C` + (6 & `$168C`), the flag A4 = `$167A` + n.

```
idx = rec.idx                                   ; +8: 0 or 2
if D0 == rec.path[idx]: rec.idx = (rec.idx + 2) & 2
idx = rec.idx
if D0 != rec.path[idx]:
    if D0 < rec.path[idx]: rec.x += 2; entry.dx = +2
    else:                  rec.x -= 2; entry.dx = -2
if not (cam_x < D0 <= cam_x + 1B0h and cam_y < D1 <= cam_y + 118h):
    return                                      ; the lift's rts $8ED0: D7 stays 6 & $168C
if flag:                                        ; RoboCop on it (lift_check)
    if (p_state & ~1) == 14: p_x = D0           ; $15D0: the x before this frame's step
    p_pend = 14 + (p_state & 1)                 ; $1696: hang (states 14/15)
flag = 0
entry.flagidx = $168A; entry.left = D0; entry.right = D0 + 10h
$168C += 2
entry.top = D1 + 14h
if (game_frame & 1) == 0: snd_b2d = 0Ch
draw_bob($4B95A, $BC3, D0 + 10h, D1 + 14h - 68h)   ; 32 x 47
```

- After this `draw_bob`, **D7 = 47 × 4 = BCh** (computed at `$AB26`, before any clipping exit).
  `update_player`'s up + fire punch box (`$AD52-$AD78`) then starts with direction BCh when the last
  record, trolley `$910E`, was seen. In level 1 every special BOB left D7 & 14 = 0.
- `lift_check` `$BD72` stands RoboCop on the entry when his x is in [x, x + 16) and his new y in
  (top − 15, top]. The trolley then asks for states 14/15 (hanging). `player_move` lets only "up"
  through there (`$B07C-$B082`).

**The hazards `$9150` and the vats `$91BC`** (`level_tick_1`):

```
$9150, every tick:
    $15F0 = 0                                   ; vats_first_done
    $10356 = CAh                                ; the copper's sprite-off line (the default)
    for each vat record r:
        if y in [cam_y - 64h, cam_y + ACh) and x1 >= cam_x + 73h and x0 < cam_x + 1A0h:
            jmp ($91B0 + 4 * level)             ; level 2: $91BC

$91BC:
if (random_b32 & 0Fh) == 0: snd_b2e = 1Ah
if p_x + 10h >= x0 and p_x - 10h < x1:
    d = cam_y + 98h - y
    if 0 <= d < 4Dh:
        $10356 = CBh - d                        ; his sprites cut from the liquid's surface down
        if CBh - d < 90h:                       ; d >= 3Ch: under
            st $169A; st $16CC; snd_b2e = 10h   ; the energy target negative, dying
if (game_frame & 1) == 0: return                ; odd frames only
c0, r0 = the map cell of (x0, y)
for k = 0 .. (x1 - x0) >> 4:
    if vats_first_done == 0: low byte of phase[k] += 2      ; phase table $92DA
    d = (phase[k] & 0Eh) + (10h if high byte of phase[k + 1] != 0 else 0)
    cell(c0 + k, r0) = T0[d / 2]                              ; $927A
    for j = 1 .. rows + 1:
        cell(c0 + k, r0 + j) = (T1 if j odd else T2)[d / 2]   ; $929A, $92BA
vats_first_done = FF00h
```

- `$10356` is a copper WAIT followed by `DMACON = 0020h` (sprite DMA off) and the eight sprites'
  control words cleared [V: copper bytes `$10332-$103CE`]. RoboCop sinks into the liquid.
- **The death depends on the camera's y**, not on RoboCop's: it is exact as long as the camera
  (`$B06`) is.
- T0, T1, T2: 16 words each, 37 distinct tiles, all attributes 0. The phases are words at
  `$92DA-$9305`, written only at `$923C` (REA xrefs of `$92DC`) and **never reset**. The last column
  of vat 4 reads one more word (`$9306`): 46 bytes are read.

**`act_0c` `$9EE8`** (activator offset 0Ch; A1 = the entry, D0/D1 = its x/y):

```
word = E680h
if (game_frame & 4) == 0:
    word = 9700h
    if (game_frame & 3) == 0: snd_b2d = 28h     ; every 8th frame, per entry in the window
if y == ((p_y + 8) & ~15) - 10h and x == (p_x & ~15) - 20h:   ; RoboCop at x + 32..47, y + 8..23
    st 4(A1)                                    ; animate the look
    4 x explosion type 0 at x + 10h, + 24h, + 38h, + 4Ch
look = looks[12][entry.look]                    ; $A4A2, $A4B6, -1
if look < 0: st 2(A1); next                     ; off; no pickup on this path
if hits_hi bit 7 and game_frame odd: entry.look += 4
copy the 5 x 2 look into the map, its word 2 = word when the look is $A4A2
```

The explosions do not hurt RoboCop (`$FA7C` tests bullets, enemies and pickups only).

**Type 1 `$C736`**, the walking gunman:

```
(A3).w += 1; D2 = (A3) & 0Eh; if FACE == 0: D2 += 10h
D1 = obj_fall(x, y + 2Ch) - 2Ch                 ; $EF72
D6 = walk($EF42, 4 px)                          ; D6 as $EF42 leaves it
if (game_frame & 2Dh) == 0:                     ; 4 frames in 64
    A2 = $6CDA0; bx = D0 - 18h                  ; facing left: D7 = 10h, D6 = walk's
    if FACE == 0: bx = D0 + 28h; A2 = $6CEE0; D7 = 4; D6 = 6
    ebullet_add(type D6, dir D7, bx, D1 + 12h)
    bob_draw(A2, $403, bx, D1 + 8)              ; muzzle flash 32 x 16
bob_part($3E810 + legs[D2 / 2], $5C3, D0, D1 + 15h)          ; legs 32 x 23
torso: $404D0 at D0 - 2 (left), $40674 at D0 + 2 (right), y + dy[step]
return bob_part2(torso, $543, ...)                            ; 32 x 21
```

**Facing left, it fires bullet type D6 with D7 = 10h** [V: listing; to confirm on the bench]: after
a step D6 = 0, so the slot is written but stays free (no bullet); after a turn at a wall D6 = 2, an
upward missile. Level 2's attribute codes never give D6 = 10h or 18h.

**Type 2 `$C868`** and its tail `$C91A`, the armed suspect:

```
if (game_frame & 3Fh) == 0: game_msg("ARREST ARMED EMEMY.")        ; $DC76
(-40h).w += 1; c = (-40h).w
x = 180h; D0 = 180h
$B2D8 = 500h                                    ; player_move's immediate: the camera pinned at x 0
A2 = $3D280
if c >= 46h:
    if (c & 33h) == 0:                          ; bursts at 4-frame steps, every 64
        bob_draw($6CDA0, $403, D0 - 14h, D1 + 6)
        if ebullet_add(type 5, dir 0Ch, D0, D1 + 10h):
            ax = -2000h; ay = -1000h (+3000h when c & 40h)
    A2 = $3D910                                 ; the shooting pose
if game_frame & 8: bob_flashd(A2, $E04, D0, D1) ; 48 x 56, white
else:              bob_part2(A2, $E04, D0, D1)
; $C91A, always (pea at $C90A):
hp = 4                                          ; +21h
if touch:                                       ; +23h, set by $FA7C
    game_msg("ARREST SUCESSFUL.")               ; $DC8A
    snd_b2c = 21h; st $16D0 (at $C936); $16C4 = 40h
    return -1
return 0                                        ; never freed by clipping
```

- 5 hits in one frame would still kill it: death `$C2D8` (energy − 30h, "SUSPECT DESTROYED.", the
  big explosion), no level end; its entry spawns it again when its window is left and entered again
  [I].
- `$C91A` is reached only through the pushed return address, so Ghidra makes no function there and
  REA's xrefs of `$16D0` miss `$C936` [V: a bench write hook found it]. "CAIN DESTROYED." (`$C24B`)
  belongs to type 22's death `$C25C`, level 3; it never runs in level 2.

**Type 5 `$D0E2`**, a drip (byte 0 state, byte 1 counter n):

```
switch state:
  0: n += 1; if n >= 5: state = 1               ; grows, then falls
  1: solid = map_cell(x, D1 + 18h)
     if touch: energy -= 0Ah; solid = true      ; its own damage
     if solid: state = 2; snd_b2e = 12h; (-60h).w = 1; (-80h).w += 2
     else: vy += 8000h; y += vy
  2: n += 1; if n >= 0Ch: return -1             ; the splash
f = (n & 3Fh) - 1
return bob_draw($3BFC0 + gfx[f], size[f], D0 + dx[f] - 0Ah, D1)   ; freed off screen
```

**Type 6 `$D1E2`** (+ `$D1CA`, `$D1D0`, `$D1DE`), the rolling tyre:

```
if not launched:
    if p_y < 1A0h or p_y >= 1D1h or killed($15F2) >= 10h: return -1
    if gap($D1DC) != 0: gap -= 1; x = y = 0; return 0
    if (game_frame & 13h) != 0: x = y = 0; return 0
    gap = 2; launched = FFh; x = 78h; y = 160h
    bounce = -7.0 (-4.5 when game_frame & 4); vy = 1.0
D5 = a & 0Eh; if D5 == 10h or D5 == 6: a = 0; D5 = 0
a += 2; vy += 8000h; D0 = x; x += 3; y += vy; D1 = y
if D0 >= A0h and map_cell(D0, D1 + 18h) is solid:
    D1 = ((D1 + 18h) & ~0Fh) - 18h              ; the draw's y only
    if notdrawn == 0: snd_b2e = 19h
    vy = bounce; D5 = 6; a = 8
if D0 >= cam_x + 1E8h: return -1
notdrawn = bob_part2($3C920 + gfx[D5 / 2], $603, D0, D1)            ; 32 x 24
return 0
```

`$D1DC` is a code-area word: it persists across lives, levels and games (0 at power-on).

**Death `$C33E`** (type 6): `$15F2` + 1 (cleared every life); every 4th kill drops a pickup: 1Ch
(energy) at the 16th, else 24h (a nuke); then an explosion of type 0 (falls into `$C35A`).

**Type 14 `$CE0A`**, the grenadier:

```
FACE = (x >= p_x) ? FFh : 0
D6 = 0; D7 = 20h; A2 = $3DFA0
if FACE == 0: A2 = $3E3D8; D6 = 2Ch; D7 = 14h
if (game_frame & 2Fh) == 0:                     ; 2 frames in 64
    explosion type 1 at (D0 + D6 - 4, D1 - 4)   ; the muzzle smoke
    if ebullet_add(type 4, dir D7, D0 + D6 - 4, D1 + 2): ay = 4000h   ; lobbed
return bob_part2(A2, $904, D0, D1)              ; 48 x 36
```

**Type 16 `$CD7A`**, the walker with a big gun: `walker1` `$C948` (ported: legs, fall, walk); its
count `(-3Eh).w` from 1Eh fires at 20h and 28h (bullet 5 facing left, 6 facing right, a muzzle
flash) and wraps at 2Eh. Body `$40818` (+ 5A0h aiming from 14h, + 2D0h facing right) through
`bob_part2`, 48 × 24, at x − 9 (+ 4 aiming, + 12h right).

**Type 49 `$E6C0`** and the flight `$E728-$E7B1` (shared with type 38):

```
if B3 == 0: B3 = FFh; dir = 10h                 ; down
D2 = dir & 1Eh
x += dx[D2 / 2] / 2; y += dy[D2 / 2] / 2        ; 16.16, $E680 / $E6A0
if D2 == target: target = 2 * aim_at(D0, D1 + 34h)   ; $D0A6, ported
elif D2 < target: dir += 1
else: dir -= 1
bob_part2($41358 + gfx[D2 / 2], $402, D0, D1)   ; 16 x 16; result ignored
if touch: energy -= 18h; goto boom
life -= 1; if life == 0: goto boom              ; from 0: 65,536 frames
return 0
boom: explosion type 0 at (x - 8, y - 8); return -1
```

The first target is 0, so a drone first turns from down through right to up (16 frames), then homes.

**Enemy bullets** (`ebullet_add` `$F5BC`; damage `$FA63`):

| Bullet type | Fired by in level 2 | Damage | Port (`DAMAGE_X` 3, types 1-2 × 2) |
|---|---|---|---|
| 1, 2 missile | type 3; type 1's leftover D6 = 2 | 40h | 80h |
| 3 | types 4, 12, 13, 15, 30, 31 | 6 | 18 |
| 4 grenade | type 14 (ay 4000h) | 0Ch | 36 |
| 5 | type 2 (ax −2000h, ay −1000h / +3000h); type 16 facing left | 0Ch | 36 |
| 6 | type 1 and type 16 facing right | 6 | 18 |
| 0 | type 1 facing left after a step (no bullet) | — | — |

**Other damage to RoboCop**: touching any enemy-slot object (`$FA7C`) 1 a frame; a falling drip 0Ah
more; a drone 18h more; killing the suspect 30h, a hostage 20h; a vat: death.

**RoboCop's interactions**: 5 lifts (as level 1's); 4 trolleys (hanging, states 14/15, which level 1
never used); the vats (sinking, the death); 16 trapdoors; 4 mines (stepping on the blinking cell);
the relocation at (672, 96); 22 shootable crates and blockers with pickups; drips from y 368;
drones from the ceiling; tyres launched from x 120 while he is at y 416-464. No conveyor, beam,
barrier or ladder.

### 2.6 The frames [V]

Level 2 draws **229 distinct frames** (address, blit size; the sprites report's catalogue from the
REA-read tables). **60 are not in level 1's MSX data**:

| Object | Frames | Where they are drawn |
|---|---|---|
| type 1 | legs `$3E810 + $C7E0[k]`: 16 × 32 × 23 (8 left, 8 exact mirrors); torso `$404D0`, mirror `$40674`: 32 × 21 | legs at (x, y + 21) via `$AC44`; torso at (x ∓ 2, y + `$C800[step]`) via `$AC56`; flash `$6CDA0`/`$6CEE0` (PERMA) |
| type 2 | `$3D280` for the first 70 ticks, then `$3D910`: 48 × 56 | x fixed at 180h; white every other 8 frames through `$AC6E` |
| type 5 | `$3BFC0 + $D19A[k]`, BLTSIZE `$D17C[k]`: 9 distinct (5 of 16 × 16, 4 of 32 × 16) | |
| type 6 | `$3C920 + $D2DA[k]`: 5 distinct of 32 × 24 | moves right only |
| type 14 | `$3DFA0`, mirror `$3E3D8`: 48 × 36 | |
| type 16 | body `$40818`, `$40DB8`, mirrors `$40AE8`, `$41088`: 48 × 24; legs: `walker1` (SPERMA, shared) | |
| type 49 | `$41358 + $E7B2[dir]`: 16 directions of 16 × 16 | |
| type 4 (shared) | torso aims 0 (`$58312`, 32 × 38), 4 (`$57912`), 7 (`$58092`) and muzzle flash 4 (`$6C8A0`) | **level 1's MSX data lacks them too**: the MSX hides type 4's torso at those aims today |

- **169 frames are level 1's**: MADEX, SPERMA and PERMA frames, the lift `$4B68A` (48 × 24), the
  hostage, explosions (`$0408` from `$C2EE`; type 4's smoke from `$C31E`; types 0-3 from type 6's
  death; 1 from type 14's shot; 0 from type 49's end) and bullets 1-6.
- **The trolley** `$4B95A` (SPERMA, 32 × 47) is drawn at (x + 10h, y − 54h).
- **The white flash**: `$AC44` and `$AC56` draw the silhouette (minterm `$BFA` patched at `$AC16`)
  while the hit flag +22h is set; `$AC56` clears it. `$AC6E` always draws it.
- **RoboCop's states 14 and 15** (hanging under a trolley) come into use. They are in RoboCop's
  shared data, but level 1 never shows them.
- `tools/bobcatalog.py`'s catalogue misses type 2's first frame, type 6's `$3D0A0`, and types 5 and
  49 entirely; it lists type 4's torso and `$4ED26` at a wrong 16 × 16 (scan errors, never drawn).

### 2.7 The level's end and the way out [V]

- **The arrest** (2.5): `$16D0` set at `$C936`, `$16C4` = 40h, effect 21h.
- **Then as in level 1** (`main_loop` `$8188`; the port's `frame.asm` `frame_end`): 65 frames of
  +100 points with effect 26h every 4th frame, the fade-out, `$8050` + 1 = 2 (`$81B8`), `level_init`
  → load-table entry 6. A time out during the count still costs a life.
- **`load_level2` `$8524`**, in order:
  1. the statistics `$85D8`;
  2. `moveq #2,D0` and 3 `nop`s;
  3. `clr.b $857F` (`sperma_resident`: DATAL3 overwrites SPERMA);
  4. Brainstorm `$8382` with D0 = 4 (visit 2);
  5. the range `$8420` with D0 = 5 (visit 2);
  6. the level-3 briefing `$110B4` through `$10762`: 411 calls. Particles 5 "CIVIC CENTRUM" at
     origin (48, −48) for 1 + 108 calls; then "BATTLE YOUR WAY TO THE ROOF TO" (column 4, row 1) and
     "CONFRONT CAIN." (column 12, row 3); then a wait of 256;
  7. PIC7 (D0 = 6);
  8. MU1, then DATAL3 (a tail call).
- **The load table `$86FA`** (8 × `bra.w`): 0 `$8352` `restart_level0`; **1, 2 `$86DC`: `rts`**
  (levels 2 and 3 again: nothing); 3, 7 `$86DE` (the game completed); 4, 5, 6 `$82EC`, `$8582`,
  `$8524` (load levels 1, 2, 3).

### 2.8 Deaths, game over and continues [V]

- **A death with lives left** (`$82A0`): lives − 1, then `level_init` with the same level: entry 1,
  nothing reloaded. RoboCop and the camera back at (352, 784), energy full, **the timer 7:30
  again**, weapon 0, every object-list entry but type 58h reset. **The map keeps its changes.** The
  score, credits and `$8060` are kept. [V: bench `vat`: deaths at 54 and 470, restarts at 109 and
  525.]
- **Game over** (`$82A8`): PIC9 (251 VBLs or fire), 128 VBLs, `high_score_entry` `$12082`, then
  `$11FD2`:
  - `$805E` − 1; while still ≥ 0: `load_level_music` and script `$11590` ("YOU HAVE A GAME CREDIT."
    / "PRESS FIRE TO CONTINUE.", 304 calls) through `$10768`;
  - fire (`$802E` bit 4) then leads to `$FFD8` (2 lives, both heads) and `level_init`: level 2
    again, score kept. No fire leads to `$8098`, the title. The credit is used either way.
- **`$805E`'s only writers**: `$83FA` (+ 1, Brainstorm solved), `$FFCC` (a new game), `$11FD2`,
  `$11FEE`. Level 1 always has 0, so **the offer can first appear in level 2**. [V: bench `cont`:
  level 2 again at row 109 with 2 lives and `$805E` = 0.]
- **`$8060`'s writers**: `$8314` (`load_level0`: SHARP), `$8482` (a time out: POOR), `$84FC` (the
  rating). `$FFC4` never writes `$8052` or `$8060`; the file holds FFFFh at `$8052`. **So every new
  game plays level 1 with SHARP, and level 2 with the range's table across deaths and continues.**
  [V: bench `trolley` at the four ratings: type 1 spawns at row 4 with 2, 3, 3 or 4 hit points.]

### 2.9 The sound [V]

- **No music plays in levels 1 or 2.** MU1 (62,800 B; the player `$18000-$18B35`) holds **42
  effects**, each a pattern on one channel, 2-57 ticks long. It is reloaded before every level;
  `level_init` calls init and stop all and turns the tick on, but starts no tune.
- Requests go through `frame_keys` `$F76C` (`$B31` … `$B2C`) once a game frame, under `$1822C`'s
  priority rule.
- **Request sites in level-2-only routines** (REA `search_bytes 11 fc 00 ?? 0b ??`):

| Site | Routine | Effect | Heard in level 1? |
|---|---|---|---|
| `$8FAC` | the trolley | 0Ch, every 2nd frame while seen | yes (a conveyor) |
| `$91C4` | the vats | 1Ah, when random & 15 = 0 | **no** |
| `$9208` | the vats | 10h, the death | yes (pickups) |
| `$9F08` | `act_0c` | 28h, every 8th frame per mine in the window | **no** |
| `$C930` | the arrest | 21h | through a pickup only [I] |
| `$D124` | type 5 | 12h, the splash | **no** |
| `$D298` | type 6 | 19h, a bounce | yes |

- Between the levels: the statistics, briefings and pictures are silent (`$FE14` stops all); PZM
  tune 1 in Brainstorm, FRM in the range; the continue screen is silent (MU1 init only).

### 2.10 The bonus stages' second visits [V]

- **Brainstorm** reads `$8050` ≥ 2 (`$17156`) and then uses: boards `$175C0` (start (5, 3); 23 / 21
  / 24 / 28 red chips; 1:00 each); palette `$17DAA` (COLOR16-31 differ); **Ellen's face `$25160`**
  instead of Murphy's `$244E0`. Quirk 5: at the end of every fade-out the palette pointer returns to
  visit 1's, so boards 1-3 fade in with visit 1's colours on Ellen's face (`docs/BRAINSTORM.md` 2.2,
  2.6, 2.8).
- **The range** reads `$8050` only at `$1FBBE`: palette `$1FC2A` instead of `$1FBEA`. FRNG is
  decrunched again, so every state starts from the file.

### 2.11 Quirks a faithful port keeps [V unless marked]

| # | Quirk | Port |
|---|---|---|
| Q1 | The suspect's hit points are 4 again every frame: only 5 hits in one frame kill it, and then the level does not end until its entry spawns it again [I: the respawn] | kept |
| Q2 | Type 1 facing left fires bullet type D6 with D7 = 10h: no bullet after a step, an upward missile after a wall turn [V: listing; bench pending] | kept (default 24) |
| Q3 | The trolley's draw leaves D7 = BCh for the up + fire punch box | `sp_d7` = BCh |
| Q4 | The vat phases are never reset, and only the first in-window vat's columns advance | the phases exact; re-initialised at a fresh level-2 start (default 22: display only) |
| Q5 | Type 6's launch gap `$D1DC` persists across lives, levels and games | in `AC_VARS` (cleared at power-on only) |
| Q6 | Types 2, 6 and 49 ignore `draw_bob`'s result: never freed by clipping. Type 49 lives 65,536 frames unless it touches RoboCop or is shot | kept |
| Q7 | A shot drone reaches `$C35A` with D5 = 0198h, its descriptor offset: `spawn_explosion` then reads frames E6h (`$F454`) to 41h (`$F45D`), garbage on the Amiga [I: listing, not run] | the logic kept (traced); the explosion's draw ignores frame numbers it has no frame for, so nothing is drawn |
| Q8 | Type 2 writes the camera immediate `$B2D8` = 500h every frame: the camera pinned at x 0 | `ac_camdx` = 500h; the view: default 31 |
| Q9 | The vat's death is decided by the camera's y, even in god mode (the energy target becomes FF00h) | kept |
| Q10 | `$EF8E` reads rows < 51 in every level: level 2's row 50 is data after the map, 35 words "solid" | `cp 51` (3.1) |
| Q11 | The mines' explosions do not hurt; a mine drops no pickup | kept |
| Q12 | The original's spellings "ARREST ARMED EMEMY.", "ARREST SUCESSFUL." | kept (`HUD_MSG_DC76`, `HUD_MSG_DC8A` exist) |
| Q13 | Explosion types 5 and 6 would draw DATAL addresses that hold type 2's frames in level 2; level 2 never spawns them | nothing to do |

REA needs four `+entry` seeds to list or cross-reference the code Ghidra misses: `c91a` (the arrest
tail), `d1ca`, `d1d0`, `d1de` (type 6's waiting paths).

## 3. The MSX design

### 3.1 What becomes level-parametric, and how [D]

The rule: **level 1's bytes change only where a level parameter needs it, and its behaviour does not
change**. Its logic traces stay at 0 differences after every step, and its pictures stay
pixel-identical (4.4).

**One level start.** `ng_go` keeps the new game's part: AG cleared (moved before `tiles_init` and
`atr_load`, which do not read it), two lives, **`ac_diff` = `diff_tab` (SHARP)**. Then `xor a` and
it falls into **`lv_go`** (A = the level: 0 or 1):
1. `lv_select` (FRONT, `cold.asm`) copies `lv_desc[A]` into `lv_cur` (RAM). It copies the level's
   palette and `view_offy` into RAM, uploads the level's tiles 0-255 into page 2 (`tiles_upload`, E
   = 4) and its atlas into page 3, and points the fade at the level's palette.
2. Today's sequence, reading `lv_cur`: `tiles_init`, `atr_load`, `pl_init`, `lvl_bank`, `lv_fresh` =
   FFh, `obj_start`, `ao_start`, `engines_init`.
3. The HUD: `hud_init` for a new game; **`hud_lvl`** for the next level (3.7).
4. `display_on`, then the main loop (the test hooks of section 6 first).

**The descriptor** (one per level, `gen/levels.inc` from `tools/mkrom.py`, assembled into FRONT;
about 33 bytes; copied to `lv_cur` at every level start, and at power-on before `vdp_setup`):

| Field | Level 1 | Level 2 | Replaces |
|---|---|---|---|
| `LV_LOGIC` | `BANK_L1` | `BANK_L2` | `lvl_bank`'s immediate (`rc2.asm:147`) |
| `LV_TILES` | its first tile bank | level 2's | `BANK_TILES` (`tc_upload`, `tiles_upload`) |
| `LV_MAPB`, `LV_ROWS` | its first map bank, 51 | level 2's, 50 | `BANK_MAP`; `MAP_ROWS` in the display and loader uses and in `atr_rc` (`tiles.asm:94`, `:147`: rows from `LV_ROWS` on read ATR2) |
| `LV_ATR`, `LV_ATRN` | `ATR_BANK`, `ATR_PACKED` | level 2's | `atr_load` (`cold.asm:1028`, `:1035`) |
| `LV_TAB` | `LEVEL_BANK` | level 2's | OTILE, ATR2, BOBHASH, the field tables (`tiles.asm:161`, `:197`, `field.asm`) |
| `LV_FIMG`, `LV_FLINES` | `FIELD_IMG_BANK`, 88 | level 2's, 112 | the atlas and its size |
| `LV_DYN` | page 3 line 88 | **page 2 line 224** | the dynamic slot's place (3.6) |
| `LV_TCN` | 256 | **224** | `TC_SLOTS` (the tile cache's slots) |
| `LV_X`, `LV_Y`, `LV_YMAX` | 144, 800, 640 | **352, 784, 624** | `LVL_X/Y/YMAX` (`cold.asm:265-271`) |
| `LV_CAMY` | level 1's `CAM_Y_MAX` | 638 (800 − 162) | `CAM_Y_MAX` (`player.asm:647`) |
| `LV_KY`, `LV_VOFFY` | 1434, its `view_offy` | 1471 [E: mkrom's formula], its own (42 entries) | `VIEW_KY`, `view_offy` |
| `LV_PAL` | the fixed area's `palette` (`rc2.asm:480`, `level1_grade.pal`) | `level2_grade.pal` (palette C graded) in its tables bank | the source `pal_fade` and the flashes read (`logic.asm:385`, `:420`) |
| `LV_SIDX`, `LV_SBOBS`, `LV_SPARK` (from step 12) | `SPR_BASE_BANK` and 8372h, 198, 194 | level 2's (3.6) | `SPR_BOB_INDEX`, `SPR_BOBS`, `SPR_SPARK`: build-time equates of `gen/robocop.inc` today, read by `bob.asm` and `player.asm:576` (fixed area); per level in the global pool |

Bank numbers are whatever `tools/mkrom.py` assigns. **`lv_cur` is filled with level 1's descriptor at
power-on, before `vdp_setup`**: its `tiles_upload` (E = 8) and `field_upload`, and `title`'s
`tiles_upload`, run before any `lv_select` and would otherwise read RAM as the machine left it. `lv_select` copies the level's palette into
`lv_pal` and its `view_offy` into `lv_voffy` (RAM); `pal_fade`, the flashes and `pv_add` read the
copies. Level 1's `palette` stays in the fixed area, where `vdp_setup` (`cold.asm:484`) still loads
it at power-on. Shared, unchanged: `CAM_X_MAX` (2304 on the MSX; 2272 on the Amiga for both levels),
`VIEW_KX`, `view_offx`, `FADE_STATE`, `atr_rows`, the `ATR_RAM0`/`ATR_RAM1` split at row 48,
RoboCop's flashes (entries 2, 3, 7, which no background colour uses under palette C), the dynamic
frames' banks.

**`rowtab`** stays one shared table in the fixed area (153 B), with **bank bytes relative to the
level's first map bank**: both levels keep 25 rows a bank at A000h + 320r. Each of its five uses
adds `LV_MAPB`. Level 2 never reads row 50 for display (its view ends at y 800).

**The logic constants** that are assembler constants today:

| Today | Where | Becomes |
|---|---|---|
| `ac_diff` = SHARP | `objects.asm:44-45` (`obj_start`) | moved to `ng_go`, the port of `$8314` (3.8) |
| `SW_N` (28) | `objects.asm:376-378`, `level1.asm` `sw_init` | read from the level bank's header (40 in level 2) |
| the spawn masks as longs (32 entries): `cp 32`, 4-byte `sw_dirty`, 33-byte `sw_list` | `level1.asm` `sw_prep`, `sw_init`, `sw_dbit`; `msx.inc` | 5-byte masks (40 entries; level 3 has 39); `tools/cellmasks.py` `SW_MAX` 40 |
| the `sw_ptr` label | `objects.asm:234` | a fixed place in every level bank's header |
| `HZ_XN`, `HZ_YN` | `special.asm:651`, `:663` | the level bank's header |
| `not_enemy` (32, 44, 45) | `objects.asm:180` | `jp lv_noten` in the level bank (3.3) |
| `ao_acts` entry 3 (`ao_look`) | `mapobj.asm:144` | `act_0c` (no level-1 entry uses offset 0Ch) |
| `sp_update`'s 0 / 8 dispatch | `special.asm:114-117` | + 4: `sp_trolley`; the rest shortcut tests handler 0 only |
| the `$EF8E` ports' `cp MAP_ROWS` | `logic.asm:110` `map_cell`, `logic.asm:163` `map_atr`, `hits.asm:607` `cell_solid` | **`cp 51`** in every level (Q10): the same bytes for level 1. `atr_rc` (`tiles.asm:94`, `:147`) is not one of them: it compares with `LV_ROWS`, so level 2's row 50 is read from ATR2 (the words after the map), not from `ATR_RAM1`'s third row, which `atr_load` fills for level 1 only |
| `FIELD_ID0` C8h | `tools/msxsprites.py` | D0h for both levels (3.6) |

**What level 1 keeps.** Its descriptor holds today's values; its uploads write the bytes VRAM holds
already; its header gains the new fields with level 1's values. Its shared handlers move into
`msx/lvshared.asm`, which `BANK_L1` includes. The bytes that change in level 1's image: the fixed
area (the descriptor reads, the relative `rowtab`, the SHARP set), LC1 (−11 B net), LC2 and LC3 (the
new entries), `BANK_L1` (its header fields, the code moved), the sprite ids from C8h on, and the
banks after the sprite pool (shifted by 4, 3.12).

### 3.2 Modules, banks and code room [D, E]

| Piece | Where | Bytes [E] | Content |
|---|---|---:|---|
| `ng_go` → `lv_go`, `lv_next`, `lv_cont`, `ml_ev`, the descriptor reads, the relative `rowtab` | fixed area (188 B free at `0e1d6ab`; 160 in `PZ_TEST` builds) | +65 to +100 | the level start and the flow; the whole fixed-area budget is below the table |
| `lv_test`, `CHEAT` | fixed area, test builds only | ~30 + ~25 | section 6 |
| `lv_select`, `hud_lvl`, `front_brief`, `front_cont`, `front_l2test`, `front_bonus`'s extra call | FRONT (about 2,300 B free after the range) | ~240 | |
| `lv_desc` × 2 | FRONT (`gen/levels.inc`) | ~56 | |
| `txt_l2_brief`, `txt_l3_brief`, `txt_cont` | FRONT (`text.inc`) | ~181 | 3.7 |
| `obj_start` without SHARP, `not_enemy` → `lv_noten`, `SW_N` read | LC1 (39 B free) | −11 | |
| `act_0c` | LC2 (5,087 B free) | 200-320 | |
| `sp_trolley`, its dispatch, the cut line's reset | LC3 (5,105 B free) | ~265 | |
| the header fields; the shared handlers moved to `lvshared.asm` | `BANK_L1` (984 B free) | ~+30 | |
| **`BANK_L2`**: `lv_htab`, the header, `l2_init`, the new types, `lt1`, `death_c33e`, `walk_d6`, `lv_noten`, the shared copies (`gen/lvshared_l2.asm`), the tables, `cells_l2.inc` | a bank at A000h | **~6.5 KiB (6.0-7.2)** | 3.3 |
| the vat refresher (the column queue and its commands) | `msx/field.asm` in `BANK_FIELD` at A000h (1,529 B free: `field_end` BA07h in the last build), run through `field_call` from the frame's idle work, as `fb_work` is | ~500-800 | 3.5 |
| `get_tile`'s vat rule; the refresher's hooks | **fixed area**: `tiles.asm`, `scroll9938.asm` and `scroll9958.asm` are fixed code (`rc2.asm`'s org 4000h section), not `BANK_FIELD` | ~60-100 | 3.5 |
| the cut; the arrest's view | **fixed area** (`sprites.asm`, `player.asm`) | ~80 + ~40, less what moves out (below) | 3.6 |
| `rd_at`'s base, `pz_pal2`, the cursor's colours | `BANK_PUZL` (4,590 B free) | ~45 | 3.9 |

- **The fixed area is the scarce part, and the plan needs more than it has** [V: `code_end` =
  7F42h in the last build, 190 B free, 188 after the range's `fr_done` and `fr_rated`; `bank.asm`
  to `player.inc`, the scroll engines and `sprites.asm` included, assemble at 4000h-7FFFh]. Its
  additions: the level start and the flow with the descriptor reads (+65 to +100), `get_tile`'s
  vat rule and the refresher's hooks (+60 to +100), the cut (~80) and the arrest's view (~40):
  **about 245-320 B against 188** (160 in `PZ_TEST` builds; `LV_TEST` and `CHEAT` add ~55 in
  their builds). So **step 4 makes room first**, and steps 14 and 15 start only when the fixed area
  has their bytes free in every option set:
  - the power-on init's tail (`rc2.asm` from `snd_init` to `front_mode`: it calls only fixed or
    A000h code) and `title` (`front_title`, `front_done`, `tiles_upload`: all FRONT) move to FRONT;
  - the arrest's view target is computed by `t2` in `BANK_L2` into a RAM byte that `player.asm`
    only adds;
  - the cut's per-band work goes to `BANK_FIELD` behind a hook in `sprites.asm`.

  `lv_go`'s body cannot move to FRONT whole: it calls `obj_start` (LC1) and `ao_start` (LC2),
  which need the 8000h window FRONT takes; only `lv_select` and `hud_lvl` live there.
- `BANK_L2`'s ratio: 1,446 B of new 68000 code × 1.43 (level 1's measured Z80 / 68000 for its
  types) = about 2.35 KiB; the copied shared handlers 1,194 B and the spawn-walk shortcuts with init
  664 B (measured in `BANK_L1`); the tables and cells about 2.3 KiB.
- If `BANK_L2` passes 8 KiB: the tables and cells move to the level's tables bank, read at 8000h
  (the `sw_*` code already maps `LV_TAB`); then a second logic bank (level 3 needs one anyway).

### 3.3 The new logic [D]

The logic stays the original's, routine by routine, in the AM mirror's layout, traced against the
bench (4.1). What each new routine becomes:

| Amiga | Port | Bank | Notes |
|---|---|---|---|
| `$871A` (level 2's part) | `l2_init` | `BANK_L2` | copies the lists (`lv_fresh`), the vat phases and `vat_shown`'s start (the static map's look of each of the 103 columns, a table `tools/mapcells.py` derives: fresh starts only), reads the header fields into AM and `AC_VARS` (timer 7:30, delay 2Eh, mask 7, the start, the relocation target, `$F89D` = Ah) as `l1_init` does |
| `$8F02` | `sp_trolley` | LC3 | its own window (1B0h, 118h) beside `sp_seen` (1A0h, C4h); never at rest; **`sp_d7` = BCh** after its BOB (Q3); its BOB in the field's `fb_late` group, as the lift's |
| `$9150` | `hz_update` + one line | LC3 | `vat_cut_line` = CAh every tick |
| `$91BC` | **`lt1`** | `BANK_L2` | the phases exact (46 B, Q4); per column it stores the row-table index d / 2 (`vat_shown`, 103 B) and marks the vat changed; **no `map_write` for the 604 cells**; the cut line; the death |
| `$9EE8` | `act_0c` | LC2 | after `ao_copy`, when the look is `$A4A2`, writes cell (c0 + 2, r0) with the word from the game frame (`map_write_lin`: one patch per mine, 4 cells in all, among the 289 the pools count) |
| `$C736` | `t1` + `walk_d6` | `BANK_L2` | `walk_d6`: `obj_walk` returning `$EF42`'s D6 (0 after a step; on a turn `attr & 18h` unless 8, else 2) for Q2 |
| `$C868`, `$C91A` | `t2` | `BANK_L2` | `ac_camdx` = 500h; the arrest: `HUD_MSG_DC8A`, effect 21h, AM `$16D0`, `$16C4` = 40h |
| `$D0E2` | `t5` | `BANK_L2` | its own damage 0Ah × `DAMAGE_X` (default 26) |
| `$D1E2` + `$D1CA-$D1E1` | `t6` | `BANK_L2` | `barrel_gap` in `AC_VARS` (Q5) |
| `$C33E` | `death_c33e` | `BANK_L2` | LC1 has no room |
| `$CE0A` | `t14` | `BANK_L2` | |
| `$CD7A` | `t16` | `BANK_L2` | `walker1` ported |
| `$E6C0`, `$E728-$E7B1` | `t49` | `BANK_L2` | `aim_at` ported; its own damage 18h × 2 at most, as a missile (default 26) |
| types 3, 4, 12, 13, 15, 30, 31, 45 | the level-1 handlers | `BANK_L2` copies | z80asm labels are global: `tools/mkrom.py` writes `gen/lvshared_l2.asm` from `msx/lvshared.asm` with every label it defines suffixed `_l2` (default 28) |

**The bank's header** (`BANK_L2` at A000h, the contract `obj_start` and `update_objects` already
use): `lv_htab` (the handler table, 53 × 4), `lv_init` (`jp l2_init`), `lv_tick` (`jp lt1`), `lv_hz`
(the vat records), then the new fields: `lv_swn`, `lv_swlast`, `sw_ptr`, `lv_hzxn`, `lv_hzyn`,
`lv_noten`.

**`ENEMY_CAP` in level 2** (`uo_cap` counts the slots whose type `lv_noten` does not reject):

| Counted (enemies) | Not counted |
|---|---|
| 1, **2**, 3, 4, 5, 6, 12, 13, 14, 15, 16, 30, 31, 49 | **45**, the hostage (decisions 18, 25) |

- Decision 18 counts every enemy; it exempts only the hostage and the types that draw nothing (32,
  44). Type 2 draws and shoots (bullet 5), so it counts. Once spawned it holds the slot until the
  arrest (never freed by clipping, Q6), but it also pins the camera at x 0 (Q8): the rest of the
  level is that scene, one on one, as `ENEMY_CAP` 1 means. An enemy that holds the slot when the
  suspect's entry comes into the window delays it until that enemy is gone (decision 25's rule).
- Types 5, 6 and 49 are sprites beside RoboCop: counting them keeps every line within RoboCop's 5
  and one enemy's 3, by construction (default 25). The cost: in the drips corridor, a drip and a
  walker take turns at the one slot.
- Counted, type 2's silhouette (its white blink, 3 a line) meets only RoboCop's 5 on a line, and
  18 + 2 + 8 = 28 sprites in all. Not counted (the alternative), it would meet another enemy's 3
  on RoboCop's lines (11 > 8) and its bands would give way: a partly white suspect (decision 13).

**Damage**: the port's rule needs no change (`hits.asm` `phb_en`: bullet types below 3 doubled, the
rest × `DAMAGE_X`; the 23-entry tables suffice). The own damages of types 5 and 49 (energy − 0Ah
and − 18h in their handlers when they touch RoboCop) are an enemy's touch, which decision 17
multiplies; it keeps × 1 only for the beams (a hazard) and the penalties for killing a suspect or a
hostage. So type 5's 0Ah × `DAMAGE_X`, and type 49's 18h × 2 at most, a missile's rule (decision
19). Level 1 has no such damage (its only direct ones are the beams and the penalties). Trace
builds (`DAMAGE_X=1`) keep × 1 (default 26).

**CPU [E]**: a busy level-2 tick about 45,000-55,000 Z80 T-states (the vat corridors with a trolley
ride and drips; the top corridor with drones, gunners and the suspect), against level 1's measured
74,000. That holds only because the vats write no map patches: 108 cells through `map_write_lin`
would add about 24,000 T a tick and overflow both pools. The R800 runs the same code 4-5 times
faster.

### 3.4 RAM [D]

| Range | Use | Why it is free |
|---|---|---|
| DD0Ch (`ac_diff`) | the rating's table | exists; written by `ng_go`, `front_range`, `lv_test` only |
| DD1Ah-DD1Bh | `barrel_gap` (`$D1DC`) | free in `AC_VARS` (DD1Ah-DD1Fh); `AC_VARS` is cleared at power-on only, as the Amiga's word persists |
| DD20h-DD5Dh | the shortcuts repacked: `sw_list` 41, `sw_dirty` 5, `sw_key` 7, then `sw_lp` … `sw_px` | `AC_VARS`' tail; `sp_rest` stays at DD60h (`SP_REST_N` 12 ≥ 9 + 1) |
| DD80h-DFB1h | level 2's spawn list (562 B: 40 × 14 + the end word) | `spawn_ram` (640 B) |
| **DFB2h-DFDFh** | **`vat_phase`** (46 B: `$92DA-$9307`) | `spawn_ram`'s tail; inside the harness's DD00h dump, so the trace needs no new block |
| EE00h-F011h | level 2's object list (530 B) | `objl_ram` (768 B) |
| F012h-F0E6h | `vat_shown` (103 B), `vat_disp` (the step each page shows: a nibble per page, 103 B), 7 changed flags | `objl_ram`'s tail; the stages use `objl_ram` only between levels (the range's display: EE40h-EFD7h and F080h-F0F9h at `0e1d6ab`), and a fresh level-2 start sets `vat_shown` again (3.3) |
| E900h-E995h | the special records (150 B) | `SP_RAM` |
| CE42h | `vat_cut_line` | free in `G_VARS` (CE42h-CE43h); `act_0c`'s word is computed from the game frame, not stored |
| F1A0h-F1C2h | `lv_cur` (≤ 35 B: the descriptor with its sprite fields) | free (`msx.inc`: "F1A0h-F1C2h: free since the alternation went"; not in the range's list) |
| C6AAh | `pz_tvb`, `rd_at`'s bank base for Brainstorm's visit-2 pictures (3.9, step 20) | Brainstorm's scratch after `rd_cmd` (C69Bh-C6A9h), used only while Brainstorm runs; allocated at step 5 with the other homes |
| C68Ah-C6D4h | `lv_pal` (32 B), `lv_voffy` (43 B) | the stages' scratch while they run; rebuilt by `lv_select` at every level start and by `lv_cont` |
| AG `$805E` | the credits | exists (`front.asm:380` counts it) |
| C6F0h (`fo_cont`) | `front_cont`'s answer (1 B; cleared by `front_over` at its start, 3.7) | C68Ah-C6FEh's tail: read by `ml_ev` right after `front_over`, before `lv_cont` rebuilds the copies; the text screens use only `fs_buf` and `txt_pal` (`pz_first` stays at C6FFh) |

- Other agents are editing `msx/msx.inc` on the branch: every home above is checked against the
  file as it is at step 5 and step 7.
- The bench report proposed `vat_phase` at DFB0h: that is the spawn list's end word. DFB2h is the
  first free byte after it.
- `$15F0`, `$15F2`, `$167B-$1683` (the 9 special flags) and `$16DB-$16E4` (10 hostages) are in AM
  already.

### 3.5 The play field: tiles, map, palette, vats [D]

**Tiles and map.** `tools/msxconv.py` converts level 2 unchanged:
`level DATAL2_18.bin --rows 50 --joint build/msx/level2` [V: the map report's run]: `.map` 16,000 B,
`.atrp` 4,016, `.otile` 1,024, `.atr2` 320 (rows 50-51, the words after the map), `.til` 65,408 (511
tiles). Its docstring still says 432 VRAM slots; `TC_SLOTS` is 256.

**The tile cache** [V: `tilecache.py` on the map]: at most 107 distinct map tiles in the V9958's 19
× 14 kept window, **148 with every tile the writers can put there** (V9938 17 × 14: 103 and 144;
level 1: 125/133 and 118/128). 224 slots (3.6) hold that with 76 to spare. A miss costs a 128-B
`tc_upload`, about 4,500 T [E]; the vats' 37 tiles stay resident once seen.

**Palette C** (default 16; `scripts/l2pal.py`: ΔE76 per pixel over the whole map against the
Amiga's 12-bit colours):

| Option | Palette | Mean ΔE | Notes |
|---|---|---:|---|
| A: level 1's as it is | `000 432 455 344 333 000 111 234 222 666 210 012 100 001 500 630` | 2.50 | the sky's two blues merge (c5 ΔE 52.9) |
| B: level 2's own k-means | `000 432 355 344 234 123 111 000 112 677 100 210 222 630 333 555` | 2.46 | RoboCop's 1-7 change (his data stored again); the reds turn orange (c10 ΔE 35.4) |
| **C: level 1's layout, level 2's values** | `000 432 455 344 333 000 111 234 222 555 210 015 100 012 500 630` | **2.42** | c5 16.6, c6 11.0, c15 1.8 |
| D: 0-7 kept, 8-15 refitted (reference) | `… 012 100 210 222 300 543 555 630` | 2.40 | every shared frame's 8-15 change meaning |

- C is the Amiga's own scheme: the same index map (level 1's remap unchanged), five background
  values changed. Entries 0-7 stay, so RoboCop's data and every shared frame stay byte-identical;
  the shared frames show level 2's values, as the Amiga's BOBs do.
- It costs no ROM: a 32-B palette graded by `tools/mkrom.py` (`level2_grade.pal`).
- Type 1's #03A shirt lands on entry 11 = 015 (a blue) instead of level 1's 012 (a dark navy).
- c7 (310, 8.4 % of level 2: the vats' liquid) has ΔE 11.5 in every option, rounding to 100 as in
  level 1: the liquid looks redder than the Amiga's brown. The user approved this colour in level 1;
  the vats make it prominent (`png/crop_vat0.png` for the user's eye).

**The vats as a display layer** (defaults 17, 18):
1. **The logic is exact** (3.3): `lt1` updates `vat_phase` and `vat_shown` and never writes the map
   patches. The logic's map reads see the original's attributes; the vat cells hold attribute 0
   anyway.
2. **A vat cell's word is T0/T1/T2 at `vat_shown`** (a per-row byte says which vats cover the row;
   T0/T1/T2[d] through `.otile`). That is the word the Amiga's map holds, including vats that left
   the window and froze. `tools/mapcmp.py` compares whole maps with that rule.
   - **The display draws a vat cell at its column's shown step on the page being drawn**
     (`vat_disp`), not at `vat_shown`: the scroll engines' `get_tile` takes that column's
     `vat_disp`, and only a column with no vat cell on that page yet takes `vat_shown` and
     records it. Otherwise a row or column the scroll uncovers would show a newer look than the
     rest of its column, which is a torn column.
   - `vat_disp` is cleared at every full redraw (`engines_init`: level start, restart, continue;
     `engines_jump`) and for a column that leaves the drawn window.
   - The rule's tables (the per-row byte, the 7 vats' column ranges, the 48 T words' tiles) go into
     level 2's tables bank (step 13), read at 8000h as `map_write` reads OTILE.
3. **The display redraws whole columns, never single cells.**
   - A column is 4 VDP commands from the tile cache: T0, T1, T2, then one overlapping HMMM 32 lines
     below its source that repeats the T1/T2 pair down the column (split at the ring's line 255).
   - Each column keeps the step it shows (`vat_disp`, per page on the V9938). The oldest visible
     column whose shown step differs from `vat_shown` goes first, straight to the newest look.
   - **Never tear**: a column starts between the HUD split and the VBLANK, or while the beam is
     below its lines.
   - **Never go back**: on the V9938 the page shown comes first and the other page catches up with
     the VDP time left; a flip waits for the back page's stale vat columns.
   - **BOBs first**: a column that meets a play-field BOB goes through `fb_meetq`, as changed cells
     do. Nothing goes through `rd_queue` (64 entries cannot take a step's 100 cells).
4. **Why not the original's rate [V, E]**: vat 0's step is 13,696 B as whole tiles, 10,888 B as
   per-tile boxes, 5,240 B exactly. At the original's rate that is 101-129 % of a V9958's HMMM
   throughput and 202-257 % of a V9938's (which draws changed cells on both pages). Exact CPU writes
   cost about 220,000 T a step. No method keeps 12.5 steps a second on the V9938, nor reliably on
   the V9958.
5. **Expected [E, to measure]**: each picture shows one of the original's looks per column; about
   4-8 steps a second of the original's 12.5 with the camera still, 2-3 on a scrolling V9938. About
   2,500 T a column, 5 % of a 3.58 MHz Z80 at 75 columns a second.
6. Fresh level-2 starts copy the original's phases from `BANK_L2` (default 22) and set `vat_shown`
   to the static map's looks (each static column is one look: a 103-B table from
   `tools/mapcells.py`). Without that, a vat not yet written would show look 0 instead of the map's,
   and `mapcmp` would differ from the bench. Deaths and continues keep both, as the Amiga does.
7. **Where the code goes**: the refresher in `msx/field.asm` (`BANK_FIELD`, through `field_call`
   from the frame's idle work), beside `fb_meetq` and the field's command path (`fb_cmd`,
   `cmd_lock`); only `get_tile`'s rule and the hooks are fixed code (3.2).

**The map patches**: the 289 object cells (146 even, 143 odd rows) fit the 2 × 255 pools; the build
fails otherwise (`tools/mapcells.py`, 3.11).

**VRAM in level 2** [D]:

| Area | Level 1 (unchanged) | Level 2 |
|---|---|---|
| pages 0-1 | the play field (V9958 ring; V9938 two pages) | the same |
| page 2 | the tile cache, 256 slots | slots 0-223; **lines 224-247 the dynamic slot** (explosions, smoke); 248-255 unused |
| page 3 lines 0-87 / 0-111 | the atlas (88 lines) | **the atlas, 112 lines** (108 used) |
| page 3 lines 88-111 | the dynamic slot | (the atlas) |
| page 3 lines 112-255 | caches and scratch, sprites, HUD | the same |

`lv_select` uploads page 2 and the atlas at every level start (default 14), so the next level 1
after level 2 gets its own bytes back. The stages' exits keep restoring page 2 from level 1's tiles
(unchanged code); `lv_go` uploads the right level after them.

### 3.6 Sprites and play-field BOBs [D]

**Where each frame goes** (the sprites report, measured with the project's converter run from a
scratch copy that reproduces level 1's `robocop.bin` and `robocop_field.bin` byte for byte):

| Object | MSX | Per line (most) | Sprites |
|---|---|---:|---:|
| type 1 | **16 joint compositions** of legs and torso, 48 × 44 (8 steps + 8 mirrors) | 3 | 7-8 |
| type 2 | play field (48 × 56) + a one-layer silhouette for its blink | 3 (silhouette) | 8 |
| type 14 | play field (48 × 36) + its hit-flash silhouette | 3 | 7 |
| type 16 | body in the play field (48 × 24); `walker1`'s legs as sprites | 3 | 5-6 |
| types 5, 6, 49 | sprites | 2-3, 3, 2 | 2-3, 6, 2 |
| trolley | play field (32 × 47), `FIELD_RIDDEN` like the lift | — | — |
| lift, hostage, explosions, smoke, shared enemies, RoboCop | as level 1 | | |

- Drawn as two parts like level 1's walkers, type 1 reaches 5-6 sprites a line (8-9 with its gun
  flash): beside RoboCop's 5 the VDP would hide some. As joint compositions it stays at 3 by
  construction, for +1.0 KiB (default 33). The cost: on wide strides the dithered trousers show
  solid grey wedges (the parts show them too).
- RoboCop 18 + spark 2 + type 1 joint 8 = 28 ≤ 30 sprites in all.
- **Muzzle flashes, bullets and silhouettes are effects**: they give way when a line would pass 8,
  for that picture only. No character piece is ever touched (default 39).
- `FIELD_FLASH` = types 2, 14, 16; `FIELD_PROCS` = 45, 2, 14, 16, the lift, the trolley.

**The pool** (default 37): one global pool. Level 1's patterns, colour rows and records are reused;
each level has its own BOB index, ids, BOBHASH, atlas and field tables; the dynamic frames are
shared.

| Variant | New patterns | New colour rows | New records | Index | Total | Banks |
|---|---:|---:|---:|---:|---:|---|
| **type 1 joint (default)** | 347 | 245 | 4,372 B | 612 B | **19.5 KiB** | **+4** (patterns 13 → 15, rows 4 → 5, area 6 → 7) |
| type 1 as parts | 333 | 235 | 3,908 B | 618 B | 18.5 KiB | +3 |
| every frame from level 2's Amiga colours | 440 | 336 | 6,744 B | 618 B | 26.2 KiB | +4/+5 |
| a level-2 blob of its own | | | | | 184 KiB | 23 |

- RoboCop converts byte-identical (294 of 294 entries); 146 of level 2's 204 BOB frames are
  identical to level-1 records.
- **Under palette C**, level 2's own frames are converted against C (level 1's remap, level 2's
  values) and the shared frames are not converted again (default 32). The sprites report measured
  them against level 1's palette: the sizes above are within a few patterns of C's [I].
- A shared frame whose OR row reaches 9, 11 or 13 shows level 2's value in level 2: the Amiga's own
  change for its BOBs. The converter reports every such row with its ΔE to level 2's colour; large
  ones go to the user (4.2 check 12).
- The pool's sub-pools are addressed by id from `SPR_PAT_BANK`/`SPR_COL_BANK` and must stay
  contiguous: the pool is rebuilt in place and the banks after it shift by 4, once (3.12).

**Frame ids** (default 36): level 2 needs 204 sprite frame ids (the hit spark's 4 included) and 35
play-field frames; only 200 fit below `FIELD_ID0` = C8h. `FIELD_ID0` becomes **D0h for both levels**
(level 1: 198 + 40 still fit), with `SPR_SPARK` and the BOB index per level.

**The atlas** (default 35): level 2's static frames need 108 lines with the converter's shelf
packing (104 cropped to their pixels), against 88 above the dynamic slot. In level 2 the dynamic
slot moves to page 2 lines 224-247, the atlas takes page 3 lines 0-111, and the tile cache keeps 224
slots (3.5). The atlas is 9,722 B of ROM, 2 banks; the dynamic frames add 0 bytes (byte-identical to
level 1's).

**Type 4's gaps** (default 40): its torso aims 0, 4, 7 and flash 4 go into the pool (≈1 KiB) and
into **level 2's index only**. Level 1's index keeps its gap until the user decides, so level 1's
pictures do not change.

**RoboCop's hanging poses** (states 14/15) are in the shared data but were never shown: they go into
the frame chooser and the records (4.2).

**The sprite cut at the vat's surface** (default 30): while `vat_cut_line` < CAh, the sprite engine
drops RoboCop's bands wholly below the line (through the view's y mapping) and writes colour 0 into
the rows of the band that straddles it. Enemies are not cut (they are BOBs on the Amiga). Level 1
never sets the line: one compare per picture.

**The arrest's view** (default 31): `ac_camdx` = 500h pins the camera at x 0, so the MSX's 256-px
view shows map x 0-255 and the suspect (map x 256-303) stands outside it; the Amiga's 288-px view
shows his left 32 px. While `ac_camdx` = 500h, the view's target moves right by up to 48 px (map x
48-303: the suspect whole) at 2 px a tick, and `pv_keep` still keeps RoboCop within `AX_MIN`..
`AX_MAX` of the screen. Display only: the logic's camera is untouched.

**The frame chooser.** `build/review/quadros.html` has no generator in `tools/`. A new
`tools/msxchooser.py` writes it from the converter's outputs, with a level-2 section: type 1
(joint), types 2, 5, 6, 14, 16 (body and legs), 49, the trolley, type 4's new aims, RoboCop's states
14/15. Every new level-2 frame is kept until the user chooses (`msx/level2_frames.json`, empty by
default).

### 3.7 The flow, the briefings and the continue [D]

| # | Original | Port |
|---|---|---|
| 1 | level 1 ends, `$8050` = 1 | as today (`frame_end`, `FE_NEXT`) |
| 2 | statistics | `front_stats`, unchanged |
| 3 | Brainstorm (D0 = 2), the range (D0 = 1) | `front_bonus`, unchanged up to `front_range` |
| 4 | briefing `$110F0` | **`front_brief`**: `front_bonus`'s tail, before `jp cpu_title` |
| 5 | PIC4, MU1, MADEX, DATAL2 | nothing: PIC4 dropped (decision 5), the rest is ROM data |
| 6 | `level_init` | **`lv_next`**: display and VDP interrupts off (as `new_game`), then `lv_go` with A = 1 |
| 7 | level 2; deaths: entry 1 (`rts`) | the main loop; `level_restart` as today, reading `lv_cur` |
| 8 | game over: PIC9, high score, `$11FD2` | `front_over`, then **`front_cont`** when AG `$805E` > 0; fire leads to **`lv_cont`** |
| 9 | the arrest, `$8050` = 2 | as today (`frame_end`) |
| 10 | statistics, Brainstorm (D0 = 4), the range (D0 = 5) | `front_stats`, `front_bonus`: both stages read AG `$8050` = 2 |
| 11 | briefing `$110B4`, PIC7, DATAL3, level 3 | `front_brief` (level 3's), then **the title and a new game** (default 5) |

`ml_ev` (fixed area):

```z80
ml_ev:  ld a,(g_event)
        or a
        jp z,mainloop
        cp FE_RESTART
        jr z,ml_rst
        cp FE_OVER
        jr z,ml_ov
        ld hl,front_stats           ; the level done ($81B8: $8050 + 1 already): $85D8
        call front_call
        ld hl,front_bonus           ; Brainstorm, the range, the next level's briefing
        call front_call             ;  (load_level1 $8588-$85A4 / load_level2 $8524-$8548)
        ld a,(AG + 0x8050)          ; (the word's low byte: the mirror keeps words little-endian)
        dec a
        jp z,lv_next                ; ($8050 = 1: level 2, load_level1's tail and level_init)
        jr ml_ttl                   ; (after level 2: level 3 is not ported, the title)
ml_ov:  ld hl,front_over            ; PIC9, then the continue offer ($82A8-$82D8)
        call front_call
        ld a,(fo_cont)
        or a
        jp nz,lv_cont               ; (fire with a credit: the same level, two lives)
        jr ml_ttl
ml_fe:  call front_call             ; (pz_test, unchanged)
ml_ttl: call title
        jp new_game
```

**The briefings** are text screens through `fe_text`, typed in the game's 8 × 8 font (default 1).
`tools/msxtext.py` gets `BRIEF = (("txt_l2_brief", 0x110F0, 393), ("txt_l3_brief", 0x110B4, 411))`
and `CONT = (("txt_cont", 0x11590, 304),)`, read from the RAM image as the stages' scripts are. The
particle part becomes its text typed where the stroke text is centred, then a wait, so that each
screen lasts the original's calls (`fs_run` checks them):
-  level 2: `00 0A FD` (column 10, row −3: x 64-191, lines 43-50) + "TOKUGAWA BREWERY" (16) +
  `FF 02 1B` (108) = 125 calls; then the original's `00 0C 04` "ARREST CAIN" `FF 02 40` `FF 07`. 393
  calls, 41 bytes;
- level 3: `00 0C FA` (column 12, row −6) + "CIVIC CENTRUM" (13) + `FF 02 17` (92) + 3 × `00 0C FA`
  = 109 calls; then "BATTLE YOUR WAY TO THE ROOF TO" (column 4, row 1) and "CONFRONT CAIN." (column
  12, row 3), `FF 02 40`, `FF 07`. 411 calls, about 83 bytes;
- the continue `$11590`: unchanged, 57 bytes, 304 calls.

`fs_char` computes the line as 67 + 8r in 8 bits, so rows −8 to 10 stay inside the play area. The
colours are the font's (default 2). `front_brief` (FRONT, ~20 B): AG `$8050` = 1 shows
`txt_l2_brief`, 2 shows `txt_l3_brief`, else `ret`. The briefings are silent, the HUD's messages
tick on below, `TAG` shows "TEST n" at row 10, and fire ends a screen from tick 50 on.

**`hud_lvl`** (FRONT, `cold.asm` beside `hud_init`): the level start's HUD without a new game's
reset. It redraws the score, the lives' heads and weapon 0's icon from AG and the game state, sets
the energy display full, and clears the message queue and ticker. It is right after every path: the
product, `LV_TEST` and the continue.

**The continue** (default 6: ported now, without the high-score entry):
- `front_over` (PIC9, 30 s or fire: the user's timing; the 128 VBLs are covered by it, default 7)
  **clears `fo_cont` first** (else a continue taken earlier in the power-on would leave it set, and
  a later game over without a credit would continue), then **`front_cont`** (FRONT, ~70 B): AG
  `$805E` − 1 (a word; below 0 its high byte cleared, as `$11FEE` does); while still ≥ 0 it
  rebuilds the game's display and shows `fe_text(txt_cont)`:
  - `front_done` (SCREEN 5; it leaves the display and the line interrupt off), `fb_prep`, and
    **`display_on` on the machines where `fb_prep` does not call it** (all but the turbo R: after
    the stages they still have the game's display on). After PIC9 they do not: without the line
    interrupt there is no HUD split, and lines 162-211 show the bytes PIC9's G7 left in page 0
    (`fs_clear` clears 162 lines);
  - `fo_cont` set when the screen ended by fire or fire is held at its end (as `$82D0` tests
    `$802E` right after `$10768`). Then `jp cpu_title`.
- **`lv_cont`** (fixed area, ~20 B; the rest in FRONT): AG `$8034` = 2 and both heads (`$FFD8`);
  `lv_select` again (page 2, the atlas, `lv_cur`: default 50); the tile cache reset (`tiles_init`'s
  cache part only), **without** the map patches' reset or `atr_load`, so the map keeps its changes;
  `cpu_game`; `level_restart`; the main loop.
- Level 1's game over never shows the offer (`$805E` = 0) and does not change.

**The default ending** while level 3 is missing (default 5): after the range's second visit, the
level-3 briefing, then the title and a new game: level 1, SHARP, score 0, 2 lives, level 1's tiles
and atlas uploaded again by `lv_go`. The candidates' notes say that level 3 is not in the ROM.

### 3.8 The rating: `$8060` and `ac_diff` [D]

- The port keeps `$8060` as **`ac_diff`** (DD0Ch, `AC_VARS`): a pointer into `diff_tab`
  (`$C716-$C735`, `gen/at_c1.inc`, `BANK_LC1`). `slot_place` (`objects.asm:568`) reads it for every
  enemy's hit points.
- **The 6 bytes `ld hl,diff_tab` / `ld (ac_diff),hl` move from `obj_start` (`objects.asm:44-45`) to
  `ng_go`**, the port of `load_level0`'s `$8314`. The range's plan (3.10) asked for exactly this.
  - A new game sets SHARP: level 1 plays with SHARP, as today.
  - `front_range` sets the rating after level 1; `lv_go` for level 2, deaths (`level_restart`) and
    continues (`lv_cont`) keep it, as `$86FE`'s `rts` and `$11FD2` do.
- The trace reads `ac_diff` − `diff_tab` (0 SHARP, 8 GOOD, 16 FAIR, 24 POOR) against `$8060` −
  `$C716`: the field `diff_table` with `ptr=c716:diff_tab`.
- **Check**: the `trolley` drive at the four ratings, where type 1 spawns at row 4 with 2, 3, 3 or 4
  hit points. A port that resets SHARP at level 2 fails GOOD's at row 4.

### 3.9 The second visits [D]

**Brainstorm's visit 2** (its milestone 3; default 12):
- Already ported: visit 2's boards and rules (`puzl.asm:58-69`, `PZ_RECS_V2`), `solve2` and `fuzz2`
  at 0 differences, the visit's pointer `pz_tv`. It still shows Murphy (`PZ_GFX_TV2` =
  `PZ_GFX_TV1`), visit 1's palette (`puzl.asm:72-73`) and visit 1's cursor colours (`PZ_CUR_COL_2` =
  15/14).
- `tools/msxpuzl.py --visits 1,2` (ready) writes visit 2's 9 TV pictures (28,800 B) and
  `puzl_2.pal`. The face colour pair (655, 644) is provisional: the user's eye.
- **`rd_at` addresses only 8 banks from `PUZL_GFX_BANK`** (`puzl.asm:855-867`: the offset's top 3
  bits), and visit 2's pictures sit at offset 56,704 + n. They go into **a separate blob
  `puzl_tv2.bin`, 4 banks, after the last block**: no bank moves. `pz_tv` becomes a bank base plus
  an offset (`rd_at` with the base in a variable, about 10 B in `BANK_PUZL`).
- `pz_pal` = `pz_pal2` on visit 2 (`gen/puzl_2_grade.pal`, +32 B); the cursor's colours from the
  converter's `PZ_CUR_COL_2`/`PZ_CUR_COL2_2`; the Makefile's `msxpuzl.py` line with `--visits 1,2`.
- Quirk 5 (visit 1's palette back at each fade-out's end) reproduced (Brainstorm's default 14): the
  user's call.
- Visit 1 stays byte-identical in VRAM and pictures.

**The range's visit 2** is built on the branch [V: `frng.asm:97-104` picks `rg_pal2`,
`range_2_grade.pal`, when AG `$8050` ≥ 2]. The flow only has to reach it with `$8050` = 2, which
`frame_end` does after level 2. Its palette (the range's default 21) waits for the user's eye.

### 3.10 Sound [D; V]

- **Level 2 needs no new sound data: 0 bytes on every chip** [V]. Its routines request MU1's own
  numbers, all converted for level 1: the PSG streams (`sound.inc`, 1,415 B), the SCC tones with the
  noise on the PSG (`sccfx.bin` 4,471 B), the gun's opening (`gun_scc.bin` 603 B, `gun_psg.bin` 329
  B), effects 2, 4 and 11 attenuated. No OPLL in play (decision 23).
- `tools/msxtune.py`, `msx/tune.asm` and `tools/msxsccfx.py` need no change. The second visits reuse
  PZM tune 1 and FRM unchanged.
- The gun's opening plays at level 2's start too: `$F89D` = Ah, so `player_move` asks for it as in
  level 1.
- **Heard in play for the first time**: 12h (the drip's splash), 1Ah (the vats' bubbles), 28h (the
  mines' blink), 21h (the arrest); 10h from a new place (a vat's death); 0Ch every 2nd frame while a
  trolley is seen. 4.3 checks them by register and gives the user previews by ear.
- Not added: music during level 2. The original has none.

### 3.11 Tools [D]

| Tool | Level 2 |
|---|---|
| `tools/msxconv.py` | as is (`--rows 50 --joint` palette C); the docstring's 432 slots → 256 |
| `tools/msxlvpal.py` (new, stdlib) | palette C from level 1's joint `.pal`/`.remap` and the two Amiga palettes; checks: entries 0-7 equal level 1's, entries 2, 3, 7 free of background colours, colour 0 black, mean ΔE ≤ option A's |
| `tools/mapcells.py` | `--level`: level 2's object list, `act_0c`'s second word, the pools (146/143 of 255), the codes; the vats' own checks: attributes 0 in every vat word and vat cell, no object cell in a vat, every vat word's tile in the sheet. It leaves the vats out of the pools |
| `tools/cellmasks.py` | `SW_MAX` 40, 5-byte masks; `cells_l2.inc` |
| `tools/amitab.py` | as is; `analysis/amiga_tables.tsv` gets bank `l2` (below) |
| `tools/bobcatalog.py` | level 2's REA-verified frames; the table walk that stopped at the first repeated offset; BLTSIZE from a table; the type 4 / `$4ED26` scan errors dropped |
| `tools/msxsprites.py` | one run for several levels: the global pool, per level the BOB index, ids, `FIELD_ID0`, `SPR_SPARK`, atlas, field tables, the `FIELD_*` sets; joint compositions; level 2's frames against palette C |
| `tools/msxframe.py`, `tools/recframes.py` | the same layouts per level; RoboCop's states 14/15 |
| `tools/msxreal.py`, `tools/mapcmp.py` | `--level` exists; the vat cells from `vat_shown` in RAM |
| `tools/msxtext.py` | the `BRIEF` and `CONT` groups and their renders |
| `tools/msxchooser.py` (new) | the frame chooser page (3.6) |
| `tools/mkrom.py` | the descriptors, level 2's blocks, the pool in place, `lvshared_l2.asm`, the options of section 6 |

`analysis/amiga_tables.tsv`, bank `l2` (about 1,970 B):

| Label | Address | Count | Kind | What |
|---|---|---|---|---|
| `l2_hdr` | 868c | 20 | w | the header |
| `spawn_l2` | 97b0 | 562 | x | spawn list (40 × 14 + end) |
| `objl_l2` | a828 | 530 | x | object list (44 × 12 + end) |
| `sp_l2` | 9088 | 150 | x | special records |
| `spl_l2` | 8fe0 | 10 | l | their list |
| `mk_tab2` | c5ec | 28 | w | the marker table (the trace's pointer field) |
| `hz_l2` | 95b2 | 29 | w | the vats |
| `vat_top`, `vat_odd`, `vat_even` | 927a, 929a, 92ba | 16 each | w | the row words |
| `vat_ph0` | 92da | 23 | w | the phases' initial words |
| `t1_gfx`, `t1_dy` | c7e0, c800 | 16, 8 | w | type 1 |
| `t5_size`, `t5_gfx`, `t5_dx` | d17c, d19a, d1b0 | 11 each | w | type 5 |
| `t6_gfx` | d2da | 8 | w | type 6 |
| `fly_dx`, `fly_dy`, `fly_gfx` | e680, e6a0, e7b2 | 16 each | w | type 49 |
| copies of `t3_gfx`, `t3_size`, `t4_*`, `t12_*`, `t30_dy`, `t45_gfx`, `t45_dy` | as level 1 | | | for the shared handlers |

### 3.12 `tools/mkrom.py` and the bank count [D, E]

- **The level blocks.** A second set of level blocks, each starting a bank: `BANK_L2` (a late code
  section, as `STAGES`: adding it to `LOGIC` would shift every data bank), tiles, map, attributes,
  tables, atlas. `banks.inc` gets `BANK_L2`, `L2_TILES`, `L2_MAP`, `L2_ATR`, `L2_TAB`, `L2_FIMG`;
  `gen/levels.inc` gets both descriptors; `level2_grade.pal` is graded like level 1's.
- **The pool in place** (step 12): the global pool replaces `robocop.bin` at `SPR_BASE_BANK`, and
  every later block shifts by 4 banks, once. `tools/bstest/romdiff.py` learns a block map from
  `banks.inc`, so the regression compares every block at its new bank.
- **Before step 12** (milestone 1), level 2's BOBHASH holds only the frames level 2 shares with
  level 1 (MADEX, SPERMA, PERMA addresses): DATAL1's own addresses hold other bytes in level 2. Its
  descriptor points at level 1's atlas and field tables (the lifts, the hostage). Level 2's own
  frames draw nothing until then. Step 12 adds its sprite frames; step 13 its atlas, field tables
  and the BOBHASH's play-field entries, together with the engine that shows them.

| Item | Banks | Total |
|---|---:|---:|
| The branch with the range (banks 0-103) | 104 | 104 |
| The global sprite pool's growth (in place; later blocks +4) | 4 | 108 |
| `BANK_L2` (≤ 8 KiB) | 1 | 109 |
| level 2's tiles (65,536 B) | 8 | 117 |
| level 2's map (16,000 B, 25 rows a bank) | 2 | 119 |
| level 2's packed attributes (4,016 B) | 1 | 120 |
| level 2's tables: OTILE 1,024, ATR2 320, BOBHASH 4,224, the field tables, the palette, `view_offy`, the vat tables (about 6.2-7 KiB) | 1 | 121 |
| level 2's atlas (9,722 B) | 2 | 123 |
| Brainstorm's visit-2 pictures (`puzl_tv2.bin`, 28,800 B) | 4 | **127** |
| dynamic frames, sound | 0 | 127 |

- **127 banks (0-126): a 1 MiB image holds it, one bank to spare** [E]. Any growth (`BANK_L2` over 8
  KiB, a fifth pool bank, padding for the 3Fh rule) makes it 2 MiB. mkrom picks the size (1 MiB up
  to 128 banks); every candidate also gets its `ROM_2M=1` twin (default 47). Over 1 MiB the boot
  guard is on, with its tag in bank 255.
- **The 3Fh rule**: banks 63, 127 and 191 may hold only data never mapped at 8000h. The map banks
  and the logic banks are read at A000h: `mkrom.py`'s `a000_only` set (`mkrom.py:660`) learns them.
- **The SCC test values** at a bank's 1800h: banks 36, 63, 90 and 9's B800h in a 1 MiB image; 36,
  63, 90, 137 and 191 in 2 MiB. The shift by 4 changes what sits there: data-dependent, checked on
  every build; if one fails, reorder or pad.
- **The whole game** [E]: 127 + level 3 (17 / 19 / 22, `docs/ROM_BUDGET.md` 3.3) + its pool share (4
  / 5 / 6) + the ending's CMP tune (4) + front-end and overflow code (0 / 2 / 3) = **about 152 / 157
  / 162 banks**, 164 with padding: 92 or more of the 256 spare.
- **The Pico+'s speed target** (`docs/PICO_CACHE.md`: at most 53 banks selected a level) [E]: level
  2's set is level 1's with its own tiles, map, tables, atlas and logic instead of level 1's, plus
  up to 4 pool banks. `PICO_CACHE.md` 5.2 put level 2 at 45-48 under the budget's layout; the global
  pool may add 1-2. Level 2's new data sits at each sub-pool's end, so level 1's set does not grow.
  A device quirk sets only a speed target: it never costs content. 4.4 measures it.

### 3.13 Turbo R and generic hardware [D]

- The text screens run on the Z80 in `front_bonus`'s state (`fb_prep` on entry, `cpu_title` at the
  end). No new 0.1 s blank appears: the briefing follows the range's result inside `front_bonus`
  (default 3).
- `lv_go` → `tiles_init` → `cpu_game` puts the R800 back, as `ng_go` does. `front_cont` uses
  `front_done`, `fb_prep` and `display_on` (`fb_prep`'s on a turbo R, its own on the others: 3.7),
  then `cpu_title`; `lv_cont` calls `cpu_game`.
- Level 2's logic runs on the R800 like level 1's. The vat refresher waits for the VDP by its status
  and starts columns by the interrupts' windows, never by polling S#1 for a line
  (`docs/BRAINSTORM.md`: the Hotbit's FH misses).
- Nothing depends on one device: plain mapper writes through `bank_8000`/`bank_a000`, the VDP as
  today, the SCC and the OPLL only through the existing players.

## 4. Verification (all in openMSX)

The user cannot test on hardware before the delivery, so every check runs in headless openMSX
through the MSX-AI MCP (`msx_local_*`), on the machines already in the MCP's home, at most two
instances, with the harness's ground rules (`docs/HARNESS.md` 1: no `vwait`, `exit`, `max` or `min`
in Tcl, files opened once). Offline checks (converters, the bench, a Z80 interpreter) come first
where they are cheaper; they never replace the openMSX run of the same thing.

Machines:
- C-BIOS_MSX2 (V9938, 60 Hz), the Panasonic FS-A1FX (V9958) and the FS-A1GT (turbo R: the R800 for
  the game) for everything;
- C-BIOS_MSX2_EU (50 Hz) for the trolley drive and the records;
- the Gradiente Expert 2.0 (MSX2) and the Sony HB-F1XDJ (V9958) for the flows and the fresh-machine
  runs;
- C-BIOS_MSX2+ for the 5.37 MHz VRAM speed.

### 4.1 Logic: the bench against the MSX trace

**The bench** (`tools/amigaemu.py game --level 2`, from the bench report's `l2bench.py`):
- `--carry SCORE:LIVES:CREDITS:TABLE` (default `10050:2:0:good`: what `drive_end` + `pz_fail` +
  `fr_good` give); `--pre-poke ADDR:VALUE:SIZE` (the code-area carry); `--flow L1:PZ:FR` (level 1,
  Brainstorm and the range played, then `load_level1` for real); `--stop-at-end`.
- **The direct start**: `level2_full.bin`, `$FEDA`, `$FFC4`, then `$8050` = `$8052` = 1, the score,
  lives, credits and `$8060` poked. `level_init` takes entry 1 (an `rts`): nothing loads. The code
  area keeps its power-on values, which the port's `AC_VARS` init also sets.
- **The flow start equals the direct start** in every byte of `$B00-$16EB`, `$8000-$80FF` and the
  level-2 code blocks over `l2_end`'s 259 rows, except `$8054-$805B` (HUD message state), once
  `$C44A` = 13 and `$F07E` = 1 are poked [V].
- `CODE_BLOCKS` per level: `$97B0-$99E1` (spawn list), `$A828-$AA39` (object list), `$9088-$911D`
  (special records), `$92DA-$9305` (vat phases), `$D1DC-$D1DD` (type 6's gap), `$A4A6` (recorded,
  not compared), and level 1's shared blocks.
- `--level 1` stays byte-identical: `--gframes 600` reproduces the first 601 rows of
  `trace_cov1_ram.jsonl` (`docs/HARNESS.md` 5.2). The puzl and frng modes stay unchanged.

**The fields**: `analysis/amiga_ram_l2.tsv`, 1,022 fields: `amiga_ram.tsv`'s with level 1's
code-area records replaced, plus `spawn` (DD80h), `objl` (EE00h), `special` (E900h), `marker_ptr`
(DD08h, `ptr=c5ec:mk_tab2`), `vat_phase` (DFB2h), `obj06_countdown` (DD1Ah), `diff_table` (DD0Ch,
`ptr=c716:diff_tab`), `continues` (AG). `tools/tracecmp.py --fields FILE` (the default stays
`amiga_ram.tsv`). Its self-test without an emulator [V]: a mock MSX trace from the references gives
0 differ (`end`, `vat`, `trolley_poor`, `tour`); SHARP forced makes 641 of 641 frames differ; one
vat phase changed from row 700 makes 1,954 frames of `tour` differ.

**The drives** (`build/emu/l2_<name>.drive`, `l2_<name>_ram.jsonl`; direct start, carry
`10050:2:0:good` unless marked):

| Drive | Rows | What it covers |
|---|---:|---|
| `end` | 259 | teleport onto the roof at frame 20, fire right every 4th frame: the suspect shot, then touched; `$16D0` at frame 164 (`$C936`), the level's end at row 258 |
| `tour` | 2,654 | the play-through: L1, trolleys 0-3 (state 14 in rows 499-565, 739-781, 963-1017, 1260-1349), the blockers 7 and 8 broken, L2 and L4, the roof: the arrest at row 2,559. 14 types (all but 6); energy and lives poked every 25 frames |
| `lift` | 801 | L0 and L1 ridden up and down |
| `trolley` | 641 | trolley 0 ridden over vat 0 (rows 499-565), off at (1087, 624) |
| `trolley_sharp`, `_fair`, `_poor` | 641 each | the same at the other ratings: type 1 with 2, 3 or 4 hit points from row 4 |
| `vat` | 701 | a fall into vat 0: the death at 54, restart at 109; a death by the enemies at 470, restart at 525 |
| `cont` (carry `0:0:1:good`) | 301 | the game over and a continue: level 2 again at row 109, lives 2, `$805E` = 0 |
| `over` (carry `0:0:0:good`) | 109 | the game over without a credit |
| `fuzz` (god) | 2,501 | `drivejoy.py --fuzz 2 --frames 2500` |
| `flow_l2_end` (the flow start) | 259 | `end` reached through level 1, Brainstorm and the range |
| **`barrel`** (new, step 2) | made at step 2 | RoboCop on the left stairs (y 416-464): type 6's launches, bounces, `$D1DC`, 16 kills (pickups 24h × 3, then 1Ch) |
| **`mine`** (new) | made at step 2 | the mine at x 1184 stepped on: 4 explosions, the look advancing, then off |
| **`t1left`** (new) | made at step 2 | a left-facing type 1 on a fire frame (bullet slot written, type 0) and on a wall turn (an upward missile); the bench lists those frames |
| **`drone`** (new) | made at step 2 | the top floor: drones homing, one touching RoboCop, one shot down (Q7's D5 = 0198h) |

Every reference reproduces byte for byte on a rerun [V for the 12 made]; sha256 prefixes (all 12
recomputed by the review from `$L2/bench/ref/`): `end` e0ecb97c30288d6d, `tour` d0ef114623da05c8,
`lift` 978d9cc7dec76d65, `trolley` 8b93c3bd428166f4, `trolley_sharp` 3c810e16ee4d22eb,
`trolley_fair` 9e608b5a5255c74f, `trolley_poor` ba9dbf04d18c70e0, `vat` 05a3aacea265b2c4, `cont`
02692c53cc6458c7, `over` 3d3f211d54e83db7, `fuzz` 8bdc1c303d6c7742, `flow_l2_end`
e65540af1e959526.

**The MSX side.**
- **Builds**: `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2` with `LV_CARRY` `10050:2:0:1` (`l2`),
  `:0`, `:2`, `:3` (`l2s`, `l2f`, `l2p`), `0:0:0:1` (`l2o`), `0:0:1:1` (`l2c`).
- **`rc2_drive_rom` needs no change** [I: read, not run]: `tick_n` counts from power-on and no
  level-1 tick runs in an `LV_TEST` build, so its index is level 2's game frame. It already dumps
  D000h, DC00h, DD00h-DFFFh, EE00h-F0FFh and E900h-E9FFh, which hold every new home (3.4), and maps
  the pokes of `$169A` and `$8034` to DB9Ah and DC34h.
- **`hz_l2`** (new, `tools/bstest/hz.tcl`): the jobs of the table on C-BIOS_MSX2; `tour` and `vat`
  also on the FS-A1FX and, with `tr`, the FS-A1GT; `trolley` on C-BIOS_MSX2_EU.
-  **`rc2_l2_arm`** (new, `tools/openmsx_rc2.tcl`): in an `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1` product
  build, after `drive_end`, `rc2_pz_arm` with `pz_fail` and `rc2_fr_arm` with `fr_good`, it breaks
  once at **`lv_next`**, takes `tick0` at the next `tick_start`, and indexes the drive by
  `tick_n − tick0` (`tick_n` rewritten around `rc2_drive_hit`, before the tick runs). Compared with
  `flow_l2_end`.
- **`cont` and `over`** cross PIC9 and the continue screen, where no game tick runs: `ext_joy` keeps
  the drive's last byte, so `cont`'s fire held from row 100 ends PIC9 and the continue screen (at
  their 50th tick) and continues. `front_over` and `fe_text` must read the joystick through
  `ext_joy` in `EXTJOY` builds [I: to confirm at step 19]. `over` stops at row 109, before the new
  game's ticks.
- **Expected**: "N game frames compared (N Amiga, N MSX), 1022 fields: 0 differ" for every job, with
  the table's N.

### 4.2 Visual checks

1. **The start check.** From level 2's `display_on`, 40 s of play (`tour`'s first 1,000 ticks, and
   the product's start untouched) under `rc2_guard`: reg, pal, cmd, cpu, vbl and tear 0;
   `rc2_satcheck` and `rc2_patcheck` 0 bad. At the first picture: page 2's tile slots equal level
   2's tile image, page 3's atlas lines level 2's atlas (from step 13), the VDP's palette graded C,
   RoboCop at (352, 784). On the MSX2, the MSX2+ and the turbo R, through `LV_TEST=2` and through
   the product's flow.
2. **The field check** (`fieldcheck.py`, level 1's scratch tool: copies survive in
   `build/perf_2026-10-23/` and `$L2/../../perf/field_agent/`; into `tools/bstest/` at step 0,
   adapted at step 13). Every play-area pixel no sprite covers equals the tiles and the BOB list of the list on
   screen, with level 2's vat rule (a vat column shows one of its looks, never older than the one
   shown before). Windows of `tour`: the start, each trolley ride over vats 0-3, the drips corridor,
   the top corridor with types 14 and 16, the roof with the suspect blinking; `barrel`'s stairs. 0
   differ on the three machines.
3. **Objects against the bench**: `rc2_objs_rom` + `tools/objcmp.py` (sprite objects against the
   bench's `draw_bob` calls, tick by tick) and `rc2_bobs_rom` + `tools/bobcmp.py` (play-field BOBs)
   on `tour`, `end`, `vat`, `trolley`, `barrel`, `drone`. Every frame drawn is the bench's at its
   place, but where a default gives way (effects on a full line).
4. **Frame-to-frame coherence** (`rc2_jumprec` + `tools/recframes.py`): "pixels changed on screen
   where the original stays still: 0" over type 1's walk (joint compositions), RoboCop's hanging
   poses, the suspect's blink, a trolley ride, type 6's bounces, type 49's turns and the start
   poses; in scene coordinates, so that a scroll is not a change.
5. **The lost counters**: `mp_lost`, `atr_lost`, `rd_lost`, `fb_lost` 0 after every drive; the patch
   pools at most 146/143; the vat refresher's columns behind logged.
6. **Stills against the converters' renders**: snapshots (VRAM, RAM, registers) at chosen frames of
   `tour` (the start, each vat with its trolley, the drips, the top corridor, the arrest) equal
   `tools/msxframe.py`/`msxreal.py`'s render of the snapshot's state: 0 pixels differ, on both VDPs.
7. **Sprites a line**: `rc2_sprlines`/`rc2_overlines` over `tour`: no line above 8 but where an
   effect gave way; RoboCop and the enemy whole on every line.
8. **The vats**: records near vats 0-3 with the camera still and scrolling: no picture with a
   half-drawn or an older vat column; the steps a second per vat, the CPU share and the V9938's flip
   delay logged, on the three machines (the user's eye decides between default 18 and its
   alternatives). **The same windows under `rc2_guard` with tear counting: tear 0.** A record is
   the VRAM at the split, so it cannot show a column drawn while the beam passed it, and check 1's
   guard covers only `tour`'s first 1,000 ticks (vat 0).
9. **The cut**: in `vat`, from the frame `vat_cut_line` < CAh to the death, no RoboCop pixel below
   the line in the snapshots; enemies uncut.
10. **The arrest scene**: in `end` and `tour`, the suspect whole in the view once the view has
    moved; RoboCop within `AX_MIN`..`AX_MAX`; the view moving at most 2 px a tick.
11. **The text screens**: page 0's play area equals `tools/msxtext.py`'s render, pixel for pixel:
    the level-2 briefing, the level-3 briefing, the continue; 393, 411 and 304 ticks without fire;
    with "TEST 7" at row 10 in a `TAG=7` build. **And the screen is on**: R#1's display bit, R#0's
    line interrupt and a HUD split at every VBLANK while each screen shows, on the MSX2 and the
    MSX2+ too (page 0's VRAM alone passes with the display or the split off: the continue after
    PIC9, 3.7).
12. **The palette**: the VDP's play-field palette equals graded C; every fade step equals it limited
    by `fade_cap`; the shared frames' rows on 9, 11, 13 listed by the converter, with previews.
13. **The HUD**: at level 2's start the score, lives and credits kept, the energy full, the timer
    7:30, weapon 0's icon; the HUD's VRAM otherwise equal to level 1's.

### 4.3 Sound checks

- **The effects by register**: `sess_fxlog.tcl` (level 1's scratch tool: the only copy is
  `$L2/../../sess_fxlog.tcl`, a temporary folder; into `tools/bstest/` at step 0) and `fxcheck.py`
  (**lost**: no copy is left in the repository, the build folder or any scratch folder; step 21
  writes it again: the engine's model replays every request and compares each tick's SCC and PSG
  writes) on `tour`, `vat`, `mine` and `end`, with an SCC in the cartridge,
  an SCC in another slot, and the PSG alone. Every request starts its stream; every tick of the
  SCC's channels and the PSG voices equals the engine's model, write for write; the priority rule
  (`$1822C`) unchanged.
- **The new numbers**: 12h, 1Ah, 28h and 21h started and played whole at least once each; 0Ch every
  2nd frame of a trolley ride; the gun's opening at level 2's start.
- **By ear**: the previews `build/music/preview/sfx_all_*` of those effects, in the notes for the
  user.
- **Silence**: the briefings and the continue screen write no sound register after their `snd_stop`.
- **The second visits**: Brainstorm's PZM and the range's FRM per tick equal their visit-1 logs.
- **The title's music** after the new flow equals the base (registers per tick).

### 4.4 Regression

| Check | How | Expected |
|---|---|---|
| Level 1's logic | `drive_cov1`, `drive_cov0`, the death-and-restart and relocation drives on `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1`; `tools/tracecmp.py --ram` | 4,401 frames on C-BIOS_MSX2, 1,400 on the FS-A1FX and the FS-A1GT: 0 differ, after every step |
| Level 1's picture | its start check, field check, stills and LOCKSTEP records against step 0's | 0 pixels differ (the ids and banks may differ) |
| Level 1's effects | `LOCKSTEP` builds, the effect starts | write for write as before |
| Brainstorm | its 20 traces, stills, records and text screens | as the base; visit 1 byte-identical in VRAM |
| The range | its 15 drives, stills, records, the rating | as the base |
| The title | a fresh Gradiente Expert 2.0 from power-on: VRAM, registers, palette, music, the game at tick 300 | identical to the base, but `$B32` (R-seeded) |
| The image | each step's ROM against the previous step's (`romdiff.py` with the block map, `relocheck.py`) | every block byte-identical at its bank, but the blocks the step changes |
| The flows | the product from power-on: the title, level 1 ended by `drive_end`, the statistics, Brainstorm, the range, the level-2 briefing, level 2 ended by `end`, the statistics, Brainstorm v2 (Ellen), the range v2, the level-3 briefing, the title, a new game; on the Expert, the HB-F1XDJ and the FS-A1GT | the text screens pixel-exact; a HUD split at every VBLANK; level 1 after the new game equal to the base's (tiles, atlas, SHARP) |
| The game over | level 2 with lives 0: with a credit the continue, without the title; level 1's game over without an offer; a second game over after a continue, with no credit left, goes to the title | as 4.1 `cont`, `over`; the map patches, the attribute RAM, the level's lists (`spawn_ram`, `objl_ram`, `SP_RAM`) and the vat state equal before PIC9 and at `lv_cont`'s entry (after it, `level_restart`'s `ao_start` resets the object list's entries but type 58h's, as `level_init` does: `cont` checks that part) |
| The 2 MiB product | the same flow on the `ROM_2M=1` image (and the default image when it passes 128 banks) | PASS |
| Fresh machine | the product with its title on a power-on 64K machine (Expert, HB-F1XDJ, FS-A1GT) | the title, its music, level 1's start as the base |
| Set-ups | `make matrix` (`tools/msxmatrix.py`: MSX2, MSX2+, turbo R, 50 Hz, a disk interface first, a slot expander, an FM-PAC, a 2 MiB MegaRAM with an SCC, an SCC+, none) on the product; `--no-title` on `LV_TEST` builds | 10 of 10 PASS each |
| Turbo R writes | a write watchpoint on 4000h-7FFFh from `front_bonus`' entry to level 2's tick 100 | 0 writes |
| The Pico+ target | the bank-select log over `tour` | at most 53 distinct banks at 8000h/A000h (a speed target, logged) |
| The bench | the game mode over 600 frames of `drive_cov1`; the puzl and frng modes | byte-identical |
| Option sets | `tools/bstest/variants.sh` plus `LV_TEST`, `CHEAT` | build and pass mkrom's checks |
| Unit tests | `make test` | the known failures only |

- Brainstorm's and the range's flow checks expect the title after the range: they now see the
  level-2 briefing in between (`bonuscheck.py` learns it). `PZ_TEST=1` shows the next level's
  briefing after the range, then the title.
- Product flows cross level 1 and level 2 by drives; `CHEAT=1` builds by F5 (section 6).

### 4.5 Running the checks

```sh
sh tools/bstest/hz.sh builds W/R             # then the six l2 builds of 4.1
sh tools/bstest/build.sh W/R/l2/rc2_l2.rom EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2
sh tools/bstest/build.sh W/R/l2p/rc2_l2p.rom EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2 LV_CARRY=10050:2:0:3
```

```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_l2 {W/O/l2} {W/R} tr
msx_local_cmd: list $::hz_state $::hz_msgs          (poll until done)
```

```sh
F="--ram --fields analysis/amiga_ram_l2.tsv"
python3 -I tools/tracecmp.py $F --labels W/R/l2/rc2_l2.labels build/emu/l2_end_ram.jsonl W/O/l2/l2_end.txt
# 259 game frames compared (259 Amiga, 259 MSX), 1022 fields: 0 differ
```

The references, after the bench's merge:

```sh
$PY -I tools/amigaemu.py game --level 2 --carry 10050:2:0:good --gframes 3000 --stop-at-end \
    --drive build/emu/l2_tour.drive --trace build/emu/l2_tour_ram.jsonl --trace-ram       # 2654 rows
```

`docs/HARNESS.md` gains a level-2 part: the `LV_TEST` builds, `hz_l2`, `rc2_l2_arm`,
`hz.sh compare --fields`, and the visual checks of 4.2.

## 5. Implementation plan

One step at a time, in order, each small enough for one agent. Each ends with its acceptance test
and one review (lean process: no multi-agent audits by default). Work goes on a branch `level2` from
main once the range is merged there, one commit per step (source and docs only). No tag, no release,
no push without the user. **∥** marks steps that can run beside the ones named, because they touch
no common file.

**Milestone 1: level 2 playable, its logic trace-identical.**

| # | Step | Files | Acceptance |
|---|---|---|---|
| 0 | Baseline | records outside the repository; `tools/bstest/fieldcheck.py` and `tools/bstest/sess_fxlog.tcl` copied in from their temporary scratch copies (4.2, 4.3; `fxcheck.py` is lost) | the branch's product and harness builds rebuilt byte-identical; base records: level 1's traces, start check, field check, stills and LOCKSTEP records; the title on a fresh Expert; Brainstorm's 20 traces; the range's 15 drives; the product flow; the bank map; the free bytes of every code bank |
| 1 | Names and the ledger (∥ 2, 3, 6, 17) | `analysis/main_8000.sym` (the five reports' names, merged in its own convention: its level numbers count from 0 as `$8050` does, so `spawnlist_level1` `$97B0` is level 2's list and `special_l1` `$8F02` the trolley; the 36 addresses the reports name differently settled once; `+entry` `c91a`, `d1ca`, `d1d0`, `d1de`), `analysis/ghidra_seeds.tsv` (`tools/ghidra_seeds.py`), `docs/AMIGA_ANALYSIS.md` (level 2: the header, the lists, the arrest, MADEX = DATAL1's tail, the load table, `$8060`'s and `$805E`'s writers, the vats, `$EF8E`) | REA applies the seeds, 0 failed; REA xrefs of `$16D0` list `$C936`; `batch_decompile` `$C91A` works |
| 2 | The bench in the repository (∥ 1, 3, 6, 17) | `tools/amigaemu.py` (`game --level 2`: `--carry`, `--pre-poke`, `--flow`, `--stop-at-end`; `CODE_BLOCKS` per level), `tools/amigacov.py` (`--level 2`, scenario `level2`), `tools/tracecmp.py` (`--fields`), `analysis/amiga_ram_l2.tsv`, `tools/l2drives.py` (the drives), `tools/l2mock.py` (the mock MSX trace), `tests/test_level2_bench.py` | the 12 references reproduce the sha256 prefixes of 4.1; `barrel`, `mine`, `t1left`, `drone` made, their events listed; the suspect's 5-hit kill tried (risk 8); level 1's game mode byte-identical over 601 rows; puzl and frng modes unchanged; the mock 0 differ, its two mutations caught |
| 3 | The SHARP set into `ng_go` (∥ 1, 2, 6) | `msx/objects.asm`, `msx/rc2.asm` | level 1's traces 0 differ; `ac_diff` = `diff_tab` at every new game; a poked `ac_diff` survives a level-1 death |
| 4 | One level start, level 1 only | `tools/mkrom.py` (`lv_desc[0]`, `gen/levels.inc`, the relative `rowtab`), `msx/rc2.asm` (`ng_go` → `lv_go`; `lv_cur` filled at power-on before `vdp_setup`; **the fixed area's room first** (3.2): the init's tail and `title` into FRONT), `msx/cold.asm` (`lv_select`; `pl_init`, `atr_load`, the uploads from `lv_cur`), `msx/front.asm`, `msx/tiles.asm` (`atr_rc` with `LV_ROWS`), `msx/scroll9938.asm`, `msx/scroll9958.asm`, `msx/field.asm` (banks, rows, slots, the atlas and dynamic slot from `lv_cur`), `msx/player.asm` (`CAM_Y_MAX`, `view_offy` from RAM), `msx/logic.asm`, `msx/hits.asm` (`cp 51`), `msx/msx.inc` (`lv_cur`, `lv_pal`, `lv_voffy`) | level 1's traces 0 differ; its start check, field check and stills as step 0's; the title, Brainstorm and the range as the base; the title and level 1's start from a fresh Expert as the base; the data banks unchanged; the fixed area's free bytes logged in every option set: at least the 3.2 budget for steps 14-15 (+60-100 and +80-120), else more moves out before step 7 |
| 5 | The logic's level constants, level 1 only | `msx/lvshared.asm` (new: `t3`-`t45`, `t_xy` … `t_word`, the `sw_*` code, out of `level1.asm`), `msx/level1.asm` (its header fields), `msx/objects.asm` (`SW_N`, `sw_ptr`, `lv_noten`), `msx/special.asm` (`HZ_XN/YN`; offset 4 to a stub; the cut line's reset), `msx/mapobj.asm` (`ao_acts` entry 3 to a stub), `msx/msx.inc` (the `AC_VARS` repack and every level-2 home of 3.4: `barrel_gap`, `vat_phase`, `vat_shown`, `vat_disp`, `vat_cut_line`, `fo_cont`, `pz_tvb`; no later step edits `msx.inc` before step 18), `tools/cellmasks.py` (`SW_MAX` 40, 5-byte masks; it reads `spawn_l2`/`hz_l2` from `analysis/amiga_tables.tsv`, so `cells_l2.inc` comes at step 7, after step 6), `tools/mkrom.py` (`gen/lvshared_l2.asm`) | level 1's traces 0 differ, the death-and-restart and relocation drives too, the product configuration's as the base; LOCKSTEP records 0 differ; LC1 −11 B |
| 6 | Level 2's map data (∥ 1-5) | `tools/msxlvpal.py` (new), `tools/mapcells.py` (`--level`), `analysis/amiga_tables.tsv` (bank `l2`), `tools/msxconv.py` (its docstring), `Makefile` (level 2's conversions, outside `mkrom.py`), `tests/test_level2_data.py` | the checks of 3.11 pass; `.map` 16,000, `.atrp` 4,016, `.otile` 1,024, `.atr2` 320, `.til` 65,408 (511 tiles); palette C's 0-7 equal level 1's |
| 7 | Level 2 in the ROM, a stub logic bank, the test build | `tools/mkrom.py` (level 2's blocks after the range, its atlas still level 1's (3.12); `lv_desc[1]`; `level2_grade.pal`; `LV_TEST`, `LV_CARRY`; `LV_TEST` refused with `PZ_TEST`; the shared-only BOBHASH; `cells_l2.inc` from step 6's bank `l2`), `msx/rc2.asm` (the L2 section, `lv_test`, `lv_next`), `msx/level2.asm` (new: `lv_htab`, the header, `l2_init`, the lists; the new types as stubs that free their slot), `msx/level2obj.asm` (new: the stubs), `msx/front.asm` (`front_l2test`, a stub `front_brief`), `tools/bstest/hz.tcl` (`hz_l2`), `tools/openmsx_rc2.tcl` (`rc2_l2_arm`), `tools/bstest/hz.sh` (`compare --fields`), `docs/HARNESS.md` | mkrom's checks for every option set; the data banks of 0-103 unchanged (the code banks change: this step adds code to the fixed area and FRONT); `LV_TEST=2` reaches level 2 on the three machines with RoboCop at (352, 784) and a start picture equal to `msxreal.py`'s render; `lift` 0 differ up to the first frame an unported routine runs (the bench's coverage names it) |
| 8 | The level code (∥ 9, 10) | `msx/special.asm` (`sp_trolley`, `sp_d7`), `msx/mapobj.asm` (`act_0c`), `msx/level2.asm` (`lt1`) | `lift`, `trolley` (4 ratings), `vat`, `mine` 0 differ up to the first frame of an unported type; states 14/15 ridden; `mp_lost` 0 |
| 9 | The new types (∥ 8, 10) | `msx/level2obj.asm` (types 1 + `walk_d6`, 2 + `$C91A`, 5, 6 + `$D1CA-$D1E1`, 14, 16, 49 + the flight, `death_c33e`, `lv_noten`) | `end` 0 differ (259 rows); `barrel`, `t1left`, `drone` 0 differ |
| 10 | The sprite tools for level 2 (∥ 7-9) | `tools/bobcatalog.py`, `tools/msxsprites.py`, `tools/msxframe.py`, `tools/recframes.py`, `tools/msxchooser.py` (new), `msx/level2_frames.json` (new, empty), `tests/test_msxsprites.py`; the global pool and `FIELD_ID0` D0h only behind a new option and into new output files, so that the Makefile's run, `build/msx`'s level-1 outputs and every ROM of steps 7-9 stay byte-identical until step 12 takes them | level 1's frames render pixel-identical from the new outputs (ids aside); the Makefile's outputs byte-identical to step 0's; level 2's 229 frames converted; the pool +4 banks; type 1 joint ≤ 3 a line; the atlas 108 lines; the chooser page lists level 2's new frames |
| 11 | **Milestone 1 accepted** | none, or fixes | 4.1: every drive 0 differ in all 1,022 fields on every listed machine, but `cont` only up to its game over (rows 0-108: the continue is step 19) and not `flow_l2_end` (the product's flow into `lv_next` is step 18); 4.4's level-1 rows; 4.2 checks 1 and 5 (start check, lost counters) on the three machines; `BANK_L2`'s size logged |

**Milestone 2: the complete picture.**

| # | Step | Files | Acceptance |
|---|---|---|---|
| 12 | The global pool in the ROM | `tools/mkrom.py` (the pool from step 10; later blocks +4; level 2's atlas placed; its BOBHASH with its sprite frames, the play-field ones still off), `tools/bstest/romdiff.py` (the block map), `tools/bstest/relocheck.py` (one-byte bank operands: today it accepts only moved 16-bit label words, and the shift by 4 changes every `ld a,BANK_...` of a later block) | every data block byte-identical at its new bank but the pool and the sprite tables; the code banks differ only in bank operands and moved labels (`relocheck.py`); mkrom's checks; level 1's traces 0 differ; level 1's stills and records 0 pixels differ from step 0's; Brainstorm, the range and the title as the base; level 2's types 1, 5, 6, 49 drawn (4.2 check 3 on their objects) |
| 13 | Level 2's play field | `msx/field.asm` (the atlas's lines and the dynamic slot per level, the trolley in `fb_late`, the suspect's blink, `FIELD_FLASH`), `msx/tiles.asm` (224 slots in level 2), `msx/cold.asm` (`lv_select`'s atlas size), `tools/mkrom.py` (level 2's descriptor: its atlas, 112 lines, the dynamic slot, 224 slots; the BOBHASH's play-field entries; the vats' display tables of 3.5 in level 2's tables bank, so that step 14 needs no `mkrom.py` change beside step 20), `tools/mapcells.py` (those tables and `vat_shown`'s start), `tools/bstest/fieldcheck.py` (from step 0) | 4.2 checks 2, 3, 6 and 7 on `tour`'s windows on the three machines; level 1's field check as the base |
| 14 | The vats' display | `msx/tiles.asm` (`get_tile`'s vat rule: `vat_disp` per page, else `vat_shown`), `msx/scroll9938.asm`, `msx/scroll9958.asm` (hooks only: fixed area), `msx/field.asm` (the column refresher, `BANK_FIELD`; `vat_disp` cleared by `engines_init` and `engines_jump`), `tools/mapcmp.py`, `tools/msxreal.py` (the vat rule) | 4.2 check 8 (tear 0 under `rc2_guard`); 4.2 check 2 on the vat windows while scrolling up and down (no column of two looks); the fixed area's bytes within 3.2's budget; the map against the bench, with the vat rule, equal at chosen frames of `tour`; level 1's records as the base |
| 15 | The cut and the arrest's view (after 14: both edit `field.asm`) | `msx/sprites.asm` (the cut's hook), `msx/player.asm` (the view's add), `msx/level2obj.asm` (`t2`: the view's target), `msx/field.asm` (the cut's per-band work) | 4.2 checks 9 and 10; level 1's records as the base; the fixed area's bytes within 3.2's budget |
| 16 | **Milestone 2 accepted** | none, or fixes; the chooser page refreshed | 4.2 whole on the three machines; 4.1 and 4.4 again |

**Milestone 3: the sound and the flow with both stages' second visits.**

| # | Step | Files | Acceptance |
|---|---|---|---|
| 17 | The texts (∥ any step from 1) | `tools/msxtext.py` (`BRIEF`, `CONT`, their renders), `tests/test_bonus_text.py` | calls 393, 411, 304; 41, ~83 and 57 bytes; level 1's, PUZL's and FRNG's scripts byte-identical |
| 18 | The flow into and out of level 2 | `msx/rc2.asm` (`ml_ev`, `lv_next` for real), `msx/front.asm` (`front_brief`, `front_bonus`'s tail), `msx/cold.asm` (`hud_lvl`), `tools/bstest/bonuscheck.py` and the flows, `docs/HARNESS.md` | 4.2 checks 11 and 13; 4.4's flows; `flow_l2_end` through `rc2_l2_arm` 0 differ |
| 19 | The continue | `msx/front.asm` (`front_cont` with `display_on` off the turbo R; `front_over` clears `fo_cont`), `msx/rc2.asm` (`lv_cont`), `msx/cold.asm` (the cache's reset apart from the patches) | `cont` 0 differ (301 rows); the map patches, the attribute RAM, the level's lists and the vat state equal before PIC9 and at `lv_cont`'s entry; the continue screen with its HUD split on the MSX2 and the MSX2+ (4.2 check 11); `over` 0 differ, then the title; a second game over after a continue, without a credit, goes to the title; level 1's game over unchanged |
| 20 | Brainstorm's visit 2 (∥ 14-19, after 13) | `tools/msxpuzl.py` (`--visits 1,2`), `tools/mkrom.py` (`puzl_tv2.bin` after the last block), `msx/puzl.asm` (`rd_at`'s base in `pz_tvb`, step 5's byte; `pz_tv`, `pz_pal2`, the cursor's colours), `Makefile` | `PZ_TEST=1 PZ_LEVEL=2` stills equal `msxpuzl.py render --visit 2`; `solve2`, `fuzz2` 0 differ; visit 1 byte-identical in VRAM; mkrom's checks |
| 21 | The sound checks and the cheat | `tools/mkrom.py` (`CHEAT`), `msx/player.asm` (`key_scan`: F5, F4), `msx/rc2.asm` (`$804F` at a new game in `CHEAT` builds), `tools/bstest/sess_fxlog.tcl` (from step 0), `tools/bstest/fxcheck.py` (**new**: the 2026-10-22 scratch copy is lost) and its self-test (a mutated write caught) | 4.3 |
| 22 | **Milestone 3 accepted** | none, or fixes | 4.1-4.4 whole: the matrix, the fresh machines, the 2 MiB product, the option sets, `make test` |
| 23 | The test candidates | outside the repository (section 6) | each built twice to the same bytes; the matrix 10/10 each; the fresh-machine runs; the notes with each file's SHA-256; only the files sent go to `build/msx` |
| 24 | Documentation | `docs/LEVEL2.md` (as built), `docs/MSX_ARCHITECTURE.md` (the level descriptor, level 2, the flow), `docs/AMIGA_ANALYSIS.md`, `docs/ROM_BUDGET.md`, `README.md` (the flow; the 2 MiB requirement for the complete game), `docs/HARNESS.md` | `make test` with the known failures only; REA seeds 0 failed |

- Order of the files' owners: 3 before 4 (`rc2.asm`); 4 before 5 (`msx.inc`); 4, 5 and 6 before 7;
  7 before 8 and 9; 10 and 11 before 12; 12 → 13 (`mkrom.py`) → 14 (`tiles.asm`, `field.asm`) → 15
  (`field.asm`); 11 and 17 before 18 → 19 (`rc2.asm`, `front.asm`, `cold.asm`); 13 before 20
  (`mkrom.py`); 15, 19 and 20 before 21 (`player.asm`, `rc2.asm`, `mkrom.py`).
- Step 20 runs beside 14-19 only because step 5 allocates its `pz_tvb` byte and step 13 places the
  vats' tables: neither 14 nor 20 then touches a file of the other.
- Milestone 3's steps 17 and 20 may start while milestone 2 runs; the milestones are accepted in
  order.
- If step 14's rates disappoint, step 16 stops for the user's choice among default 18's alternatives
  (the candidates go out with the measured default and a note).
- If `BANK_L2` passes 8 KiB at step 9: the tables and cells move to the tables bank first (3.2).
- If milestone 3's sound checks cannot pass in time, the candidates go out with milestone 2's level
  and the notes say so.

## 6. Test builds and candidates

| Option | Default | Effect |
|---|---|---|
| `LV_TEST=2` | 0 | **new**: power-on without the title → `ng_go` (level 1's set-up) → once, instead of the main loop (`lv_test`): the carry into AG and `ac_diff`, AG `$8050` = 1, `cpu_title`, `front_l2test` (`fb_prep`, `front_brief`, `jp cpu_title`), then `lv_next`. One-shot through `pz_first`, so later games are the product's. mkrom refuses it with `PZ_TEST` |
| `LV_CARRY=S:L:C:R` | `10050:2:0:1` | `LV_TEST`'s carry: the score (BCD digits, into AG's little-endian words), lives, credits (`$805E`), the rating 0-3 (`ac_diff` = `diff_tab` + 8R) |
| `CHEAT=1` | 0 | **new**: AG `$804F` set at each new game; `key_scan` maps F5 to key code 59h (the level's end) and F4 to 58h (energy), which `frame_end` already handles: the original's F10/F9 |
| `PZ_TEST=1/2`, `PZ_LEVEL` | as today | `PZ_TEST=1` now shows the next level's briefing after the range, then the title |
| `EXTJOY`, `JOY`, `TAG`, `TELE`, `GOD`, `ENEMY_CAP`, `DAMAGE_X`, `ROM_2M`, `DIAG` | as today | |

- `LV_TEST` and `CHEAT` code exists only in builds that ask for it (`if` blocks, as `PZ_TEST`):
  **the product's bytes and flow do not depend on them**.
- In milestone 1, `front_brief` is a stub: `LV_TEST` goes straight into level 2. From step 18 it
  shows the briefing first (default 9), which tests the product's path. Ticks count only in the main
  loop, so the drives' indices do not move.
-  **Harness builds**: `l2`, `l2s`, `l2f`, `l2p`, `l2o`, `l2c` (4.1), all
  `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2`; the product `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1` for
  `rc2_l2_arm`.
- **The candidates** (step 23), all with `TAG=7`, built outside `build/msx`:

| File | Options | What it is |
|---|---|---|
| `ROBOCOP2_v0.1.3-test7.ROM` | `TAG=7` | the product: the title, level 1, the statistics, Brainstorm, the range, **level 2**, the statistics, both second visits, the level-3 briefing, the title |
| `ROBOCOP2_v0.1.3-test7-cheat.ROM` | `TAG=7 CHEAT=1` | the same, F5 ends a level and F4 fills the energy: every transition in seconds |
| `ROBOCOP2_v0.1.3-test7-l2.ROM` | `TAG=7 LV_TEST=2 CHEAT=1` | level 2 right after the BIOS (GOOD), then the product |
| the `-2M` twin of each | `ROM_2M=1` | when the default image is 1 MiB; the product is 2 MiB anyway once it passes 128 banks |
| optional: `-test7-l2-poor.ROM` | `LV_TEST=2 LV_CARRY=10050:2:0:3 CHEAT=1` | the hardest table |
| optional: `-test7-bs2.ROM` | `PZ_TEST=1 PZ_LEVEL=2` | Brainstorm's second visit (Ellen) at power-on |

- The notes go with the files, not into the repository. They give each file's SHA-256; what is new;
  F5/F4 in cheat builds; the default ending (level 3 is not in the ROM); the open choices for the
  user's eye (section 7's first list); **the minimum hardware: a 2 MiB Konami SCC device for the
  complete game**, and the image's own size.
- The user's SX-2 runs ROMs from slot 1 (slot 2 froze earlier tests): the notes repeat it.

## 7. Defaults chosen while the user is away

| # | Question | Default | Alternative | Why |
|---|---|---|---|---|
| 1 | The briefing's particle title | typed in the 8 × 8 font, the original's calls | port the particle writer and its stroke font (about 2.5 KiB of code, 2 KiB of RAM); or a 2× bitmap title (GAME OVER's look) | decision 5: text screens in the game's font; no new engine. **The user's eye** |
| 2 | The title's colours | the font's (green, colour-4 shadow) | the particles' final blue | the same font everywhere |
| 3 | Where the briefing runs | `front_bonus`'s tail, before `jp cpu_title` | a separate FRONT entry (one more 0.1 s blank on a turbo R) | no extra blank; the range set the precedent |
| 4 | PIC4 / PIC7 | nothing in their place | a black pause of 251 ticks | decision 5 |
| 5 | The ending while level 3 is missing | the level-3 briefing, then the title | the title right after the range's second visit | the original's next screen; it tells the player what follows. **The user's call** |
| 6 | The continue | ported now, without the high-score entry | left out (credits unused, as today) | Brainstorm promises "A GAME CREDIT"; level 2 is the first place to use it |
| 7 | The 128 VBLs after PIC9 | covered by PIC9's 30 s / fire | added | the user chose PIC9's timing |
| 8 | Level 2's set-up | the display off, as `new_game` | the uploads during the briefing | the proven path |
| 9 | `LV_TEST` | shows the briefing first (from step 18) | straight into level 2 | it tests the product's path |
| 10 | `LV_CARRY`'s rating | GOOD (1), the bench's references | SHARP | SHARP equals level 1's table and would not catch a lost rating |
| 11 | `CHEAT` | built, F5 / F4 | no cheat | the user crosses the transitions in seconds. **The user's keyboards** |
| 12 | Brainstorm's visit-2 pictures | a separate 4-bank blob after the last block | grow `puzl_gfx.bin` (the range's banks move) | no bank moves; `rd_at` reaches 8 banks only |
| 13 | Per-level values | a descriptor copied to RAM at each level start | a pointer into FRONT (every reader maps FRONT) | banked readers stay simple |
| 14 | VRAM at a level start | page 2 and the atlas uploaded at every start | only when the level changes | simpler; the same bytes for level 1 |
| 15 | Script builds | the briefing runs, as the stages' texts do | skipped, as `title` is | one path |
| 16 | Palette | C: level 1's layout, level 2's values at 9, 11, 13 | A (level 1's as it is: the blues merge); D (8-15 refitted: every shared frame converted again) | best ΔE of the options that keep 0-7; no ROM. **The user's eye** on `png/level2_compare_half.png`, `crop_vat0.png` |
| 17 | The vats' cells | a display layer outside the map patches | 604 more patches (pools of 3 × 255 or more; `rd_queue` overflows; ~24,000 T a tick) | the attributes never change; the logic stays exact |
| 18 | The vats' rate | whole columns, the newest look, never torn, never older, within the VDP time left | a fixed half rate; tearing allowed (about twice the rate on the V9958); only the surface row while a V9938 scrolls; the logic report's surface row at full rate and the body round-robin | the zero-glitch rule first. **The user's eye** on the records |
| 19 | `$EF8E`'s ports | `cp 51` in every level | per-level rows (wrong for level 2's row 50) | the original's constant |
| 20 | Per-level tables in RAM | `rowtab` shared with relative banks; the palette and `view_offy` copied to RAM | everything through the tables bank (a bank switch per `get_tile`) | `get_tile` stays fast; 75 B of RAM |
| 21 | The tile sheet | raw, 8 banks | per-tile ZX0 (−4 banks, 14-27k T a miss) | 2 MiB has room |
| 22 | `vat_phase` | re-initialised at each fresh level-2 start | kept from power-on in persistent RAM | display only; the first visit is exact either way |
| 23 | The mine's blinking cell | `map_write_lin` after the look copy | the look block in RAM with the word patched | the existing path |
| 24 | Type 1 facing left | its leftover D6/D7 reproduced (Q2) | always fire type 6 | the original, trace-exact |
| 25 | `ENEMY_CAP` in level 2 | only 45 not counted; 2, 5, 6, 49 counted | 2 not counted too (the suspect beside one more enemy, as the original's crowd; its silhouette's bands then give way on RoboCop's lines); the logic report's: 5 and 6 not counted too (the line budget then needs another way: drips as effects that may vanish, or drawn in the play field) | decision 18 counts every enemy but the hostage and the types that draw nothing; no sprite piece lost. **The user's feel** in the drips corridor and at the arrest |
| 26 | The own touch damages of types 5 and 49 | type 5's 0Ah × `DAMAGE_X`; type 49's 18h × 2 (a missile) | × 1 (the drip as a hazard, like the beams); type 49 × `DAMAGE_X` (decision 19's letter: only bullet types 1-2 are × 2) | decision 17: touching an enemy is a weapon's damage, × 3; only the beams and the penalties stay × 1; decision 19: missiles × 2 |
| 27 | The SHARP set | moved to `ng_go` | `obj_start` guarded by `$8050` = 0 | the original's place (`$8314`) |
| 28 | Shared handlers | `msx/lvshared.asm` and a generated, label-suffixed copy | trampolines into one shared bank (no: A000h is the level bank's only window) | z80asm's global labels |
| 29 | `sp_d7` after the trolley | BCh | — | needed for trace identity (Q3) |
| 30 | The cut at the vat's surface | in the sprite engine: RoboCop's bands below dropped, the straddling rows zeroed | none (he shows whole until the death); a line interrupt clearing R#8's sprite bit (enemies cut too) | the original's sinking, exact per line |
| 31 | The arrest's view | eased 48 px to the right while `ac_camdx` = 500h | the proportional view (he shoots from off screen); 32 px (the Amiga's own right edge, the suspect cut) | the suspect whole; RoboCop kept on screen. **The user's eye** |
| 32 | The sprites' palette | level 2's frames converted against C; the shared frames kept | every frame from level 2's colours (26.2 KiB) | C keeps the indices |
| 33 | Type 1 | 16 joint compositions | parts like level 1's walkers (−1.0 KiB, 5-6 a line) | 3 a line by construction. **The user's eye** on `type1_joint.png` |
| 34 | Big frames | types 2, 14 and 16's body in the play field; the trolley ridden | type 16 as one sprite composition (one layer: the look the user rejected for the gunners) | decisions 13 and 16 |
| 35 | The atlas | the dynamic slot on page 2 lines 224-247 in level 2; 224 tile slots | cropped frames and type 16's bodies streamed (82 lines; the slot shared with explosions) | the measured working set is 148 tiles |
| 36 | Frame ids | `FIELD_ID0` D0h for both levels | drop the 8 silhouettes (198 ids; the suspect's blink lost) | the blink is a cue: arrest, don't shoot |
| 37 | The pool | one global pool, rebuilt in place (later blocks +4, once) | a 23-bank level-2 blob after the range (no shift, +19 banks) | the budget's plan; 19 banks saved for level 3 |
| 38 | Frames removed | level 1's choices for the shared data; every new frame kept until the chooser | — | the user chooses |
| 39 | Muzzle flashes, bullets, silhouettes | effects that give way on a full line | — | no character piece ever lost |
| 40 | Type 4's missing aims | in the pool and in level 2's index only | in level 1's index too (a visual fix of level 1) | level 1's pictures unchanged. **The user's call** |
| 41 | The references' start | the direct start, plus one flow reference | every reference through the flow | each level-2 test independent of level 1 and the stages |
| 42 | Test aids in `tour` | teleports after vat 3; energy and lives poked every 25 frames | a teleport-free route (L2 boarded in passing; the top floor's gap) | god mode would hold `$16C4` |
| 43 | The new trace homes | inside the five dumped blocks (`vat_phase` DFB2h, `barrel_gap` DD1Ah, `mk_tab2`) | a sixth dump block | the Tcl unchanged |
| 44 | The flow's Tcl | one new proc, `rc2_l2_arm`, breaking at `lv_next` | an index offset in `rc2_drive_trace` | the existing procs unchanged |
| 45 | Not compared | `$8054-$805B`, `$A4A6` | compare them once the port mirrors the ticker | display only |
| 46 | New drives | `barrel`, `mine`, `t1left`, `drone` | — | type 6, the mines, Q2 and Q7 are in no reference yet |
| 47 | The image's size | mkrom picks (1 MiB up to 128 banks), with `ROM_2M=1` twins | always 2 MiB | 1 MiB devices can still run level 2 while it fits |
| 48 | The descriptors | in FRONT (`gen/levels.inc`) | in each level's tables bank | `lv_select` runs in FRONT |
| 49 | The pool's order | level 2's new data at each sub-pool's end | sorted [shared][level 1][level 2] | level 1's bank set unchanged |
| 50 | `lv_cont` | uploads page 2 and the atlas again (`lv_select`) | rely on PIC9 leaving page 3 untouched [I] | no inference to trust |

**The user's first list** (for the candidates' notes): 1, 5, 16, 18, 25, 31, 33, 40, Brainstorm's
face colours and quirk 5, the range's visit-2 palette.

Inferences the defaults rest on:
- the suspect respawns from its entry after a kill (Q1);
- type 1's leftover registers (Q2) and the shot drone's D5 (Q7) from the listings only (the new
  drives check them);
- `rc2_drive_rom` working unchanged for `LV_TEST` builds (read, not run);
- the global pool's sizes under palette C within a few patterns of the measured ones;
- the vats' expected rates (to measure at step 14);
- the CPU per tick (to measure with `rc2_prof`);
- PIC9 leaving page 3 untouched (default 50 does not rely on it).

## 8. Risks and open issues

| # | Item | Mitigation or status |
|---|---|---|
| 1 | **The vats' animation rate** on the V9938 while it scrolls (2-3 steps a second [E]) | measured at step 14; default 18's alternatives for the user's choice |
| 2 | **`BANK_L2` overflow** (6.0-7.2 KiB [E] of 8) | the tables and cells to the tables bank; then a second logic bank |
| 3 | **The fixed area** (188 B; 160 in `PZ_TEST` builds) needs about 245-320 B: the flow and the descriptor reads, `get_tile`'s vat rule and the refresher's hooks, the cut, the view (3.2) | step 4 makes room first and logs it in every option set: the init's tail and `title` into FRONT, the view's target from `t2`, the cut's work and the refresher in `BANK_FIELD`. `lv_go`'s body cannot move whole: it calls `obj_start` (LC1) and `ao_start` (LC2) in the 8000h window FRONT needs |
| 4 | **The image at 127 banks**: one bank from 1 MiB | the `ROM_2M=1` twins; the product is 2 MiB as soon as it passes 128 |
| 5 | **The shift by 4** moves the SCC test values and the 3Fh rule's banks | mkrom's checks on every build; reorder or pad |
| 6 | **Level 1 regressions** from the descriptor, the relative `rowtab`, `FIELD_ID0`, the moved handlers, the pool | 4.4 after every step: traces, stills, records, LOCKSTEP |
| 7 | **Trolley rides run port code no trace has checked** (states 14/15 in `plmove.asm`; what "up" does there) | `trolley` and `tour` 0 differ; the hanging poses in the records |
| 8 | **The suspect killed by 5 hits in one frame**: no level end until its respawn [I] | step 2 tries it on the bench with the three-way and scatter guns at the roof; if it happens, a `kill2` drive joins the references |
| 9 | **Shared frames' OR rows on entries 9, 11, 13** look different under palette C | the converter's report and previews (4.2 check 12) |
| 10 | **`ENEMY_CAP` with drips and tyres counted** changes the drips corridor's feel | default 25, the user's feel |
| 11 | **A homing drone** holds the only enemy slot until it hits or is shot (it lives 65,536 frames) | `tour` and `drone` records; if it strays, the user's call (exempt it as an effect) |
| 12 | **The Pico+'s 53 banks** with the global pool (level 2 at 46-50 [E]) | the bank-select log (4.4); the pool's order (default 49); the set reducers of `docs/PICO_CACHE.md` 6 only if over |
| 13 | **RAM homes** while other agents edit `msx.inc` | checked again at steps 5 and 7 |
| 14 | **Brainstorm's and the range's flow checks** expect the title after the range | step 18 updates `bonuscheck.py` and the flows |
| 15 | **The continue's VRAM after PIC9** | `lv_cont` uploads again (default 50); 4.4's game-over row compares the map state |
| 16 | **The arrest scene's view** moves the picture 48 px | eased at 2 px a tick; the user's eye (default 31) |
| 17 | **Type 1's leftover registers**, the shot drone's garbage explosion | the new drives `t1left`, `drone` before step 9 relies on them |
| 18 | **The 2 MiB product through both levels** was not run before | 4.4 runs it, and the fresh-machine runs |
| 19 | **Real hardware is unverified** until the user is back: openMSX's VDP and command timing against a real V9938, V9958 or an FPGA | everything that can run in openMSX does; waits by interrupt, never by polling S#1 |
| 20 | **Level 1 at 5.37 MHz** loses VRAM writes (known, the user's call) | unchanged; level 2 checked on C-BIOS_MSX2+ for the same |
| 21 | **Headless runs**: at most 2 openMSX, no `exit` or `vwait` in callbacks, files opened once | kept |

## 9. Sources

`$L2` = this workflow's scratch folder,
`/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space/l2`
(not in the repository, and temporary):

| Report | Spec | What it holds |
|---|---|---|
| flow | `$L2/flow/FLOW2.md` | `load_level1`'s tail, `level_init` and the headers, `$8060` and `$805E`'s writers, the end and `load_level2`, deaths and the continue, the sound, the second visits; the descriptor, `lv_go`, the briefings, the continue, the test options; `flow_level2.sym`, `rea/listings.txt`, `rea/seeds_flow.tsv` |
| map | `$L2/map/MAP2.md` | DATAL2, the header, the map objects and their writers, the vats and their costs, the specials, the `$EF8E` trap, the palette options, the tile cache, the converter plan; `l2map.sym`, `scripts/` (`vats.py`, `l2objects.py`, `l2pal.py`, `tilecache.py`, `vatlooks.py`), `out/`, `png/` (`level2_compare_half.png`, `crop_vat0.png`, `vat0_looks.png`, `level2_C.pal`, `level2_C.remap`) |
| logic | `$L2/logic/LOGIC2.md` | every new routine's pseudo-code, the lists, hit points, bullets and damage, `ENEMY_CAP`, the per-level constants, RAM, the amitab rows, sizes and CPU; `level2.sym`, `level2_new.lst`, `tables/`, `rea/l2seeds.tsv` |
| sprites | `$L2/sprites/SPRITES2.md` | the 229 frames, sprites or play field, per-line counts, the pool measured, the atlas, the ids, the previews; `level2_sprites.sym`, `out/l2_frames.json`, `out/pool_*.txt`, `out/compose_l2.txt`, `previews/`, `previews_joint/type1_joint.png`, the scripts |
| bench | `$L2/bench/BENCH2.md` | the two starts, the 12 references, the coverage, the field set, the MSX side (`hz_l2`, `rc2_l2_arm`); `tools/l2bench.py`, `l2cov.py`, `tracecmp.py` (`--fields`), `mockmsx.py`, `seek.py`, `analysis/amiga_ram_l2.tsv`, `analysis/level2_bench.sym`, `ref/`, `out/`, `scripts/make_drives.py`, `make_refs.sh` |

All Amiga facts in section 2 come from REA (Ghidra provider) listings and byte reads in those
reports, on `build/ram/level2_full.bin` with the project's seeds and the four `+entry` seeds, from
bench runs of the original code, and from data compares of the game's files. MSX facts cite the
source at `3c3a735`. This plan ran no new REA query: it reconciles the reports.

**The review (2026-10-27)** re-checked the main Amiga facts with REA (Ghidra 12.1.4, raw-binary
m68k, entry 0x0, the repository's seeds: 111 functions, 176 labels, 0 failed) on
`level2_full.bin` (sha256 `a039a158…0a88b09`): the three headers at `$8664` (`read_bytes`, every
field of 2.2's table); `load_level1` `$8582-$85CE` and `load_level2` `$8524-$8568`; the load table
`$86FA`; the xrefs of `$8050`, `$8060` and `$805E`; type 2 `$C868` and the tail's bytes
`$C91A-$C947`; `draw_bob` `$AB08` (D7 = height × 2(w − 1) at `$AB26`, BCh for `$BC3`); `$EF8E`
(`cmpi.w #$66` at `$EFA4`); `$91BC`; `act_0c` `$9EE8`; type 1's head `$C736`; `$D1C8-$D1DF`; the
tables `$C716`; `$11FD2`; `$82A0-$82E8`. All as section 2 says. It also re-did two data checks:
`MADEX_17.bin` = `DATAL1_10.bin[1D250h:]`, and the 12 references' sha256 prefixes (4.1). The MSX
facts were re-read at `0e1d6ab`, where the branch has moved on. `frngview.asm` (in `BANK_FRNG`) adds
the range's display RAM at C691h-C6D5h and EE40h-EFD7h, which the homes of 3.4 share in time. The
fixed area, LC1-LC3, `BANK_L1` and `BANK_FIELD` match the last build (`build/msx/rc2.labels`:
`code_end` 7F42h, `lc1_end` 9FD9h, `field_end` BA07h), but for the range's `fr_done` and
`fr_rated` (2 B of the fixed area: 188 B free in the product) and its `PZ_TEST=2` path. FRONT had 2,733 B free there (`front_end` 9553h), about 2,300 after
the range's `front.asm` code.

## 10. Where the area reports disagreed, and what this plan takes

| Item | Reports | This plan, and why |
|---|---|---|
| Type 2's name | flow, bench: "Cain"; logic, sprites: "the armed enemy / suspect", Cain's messages are level 3's | **the armed suspect the briefing calls Cain**: the code says "ARREST ARMED EMEMY." and "SUSPECT DESTROYED.", the briefing "ARREST CAIN" [V both]; level 3's boss (type 22) is "CAIN" |
| `ENEMY_CAP` | logic: 2, 5, 6, 45 not counted, 49 counted; sprites: 5 and 49 counted (the line budget) | **45 not counted; 2, 5, 6, 49 counted** (the review's change: the plan first left 2 out): decision 18 exempts only the hostage and the types that draw nothing, and type 2 shoots; types 5, 6, 49 are sprites beside RoboCop (the binding sprite rule) (default 25) |
| The vats' display | map: whole columns at the newest look; logic: the surface row at full rate, the body round-robin through the changed-cell queue | **the map report's column refresher**: `rd_queue`'s 64 entries cannot take a step, and a column is 4 commands; the logic report's way stays an alternative (default 18) |
| `vat_phase`'s home | logic: `objl_ram`'s tail; bench: DFB0h | **DFB2h**: DFB0h-DFB1h is the spawn list's end word; DFB2h stays inside the DD00h dump |
| Type 6's gap | logic: DD74h-DD7Fh; bench: DD1Ah | **DD1Ah** (the bench's homes are inside the dumps; both are free) |
| The test option | flow: `LV_TEST=2`, `LV_DIFF`; bench: `L2_TEST=1`, `L2_CARRY` | **`LV_TEST=2` with `LV_CARRY`**: the level's number, and the whole carry the references need (score, lives, credits, rating) |
| The test build's rating | flow: SHARP; bench: GOOD | **GOOD** (default 10): SHARP would not catch a lost rating |
| The Tcl's break label | bench: `l2_go`; flow: `lv_go` is shared by both levels | **`lv_next`**: fixed code reached only for the next level |
| The palette | map: C; sprites: level 1's palette, level 2's frames read with level 2's colours (type 1's shirt navy) | **C for the map and the sprites**: level 1's remap kept, so no shared frame is converted again, and the shirt lands on 015 (default 32) |
| The cut | map: colour rows to 0 below the line; logic: no cut at first | **the sprite engine's cut** in milestone 2 (default 30); "no cut" stays the fallback |
| Bank moves | flow: no existing bank moves; sprites: the contiguous pool moves the later banks | **one shift by 4 at step 12**, with a block-aware `romdiff`; Brainstorm's pictures after the last block |
| The atlas | map: 80 lines by hand, type 14 not placed; ROM_BUDGET: 84 of 88 with streaming | **108 lines measured** by the converter: the dynamic slot moves to page 2 in level 2 (default 35) |
| Tiles in view | sprites: "107, not re-measured" | the map report measured it: **148 with the writers**, so 224 slots hold it |
| The spawn list's length | sprites: "39 entries up to `$99E0`" (its own table sums to 40) | **40 entries**, the end word at `$99E0` [V: logic, bench coverage writes up to `$99DE`] |
| Explode-look-4 crates | logic: "15" (its range 28-43 is 16 entries) | **16**: 7 + 16 + 16 + 4 + 1 = 44 entries (the map report) |
| Vat numbers | logic: trolleys over vats 1-4 | **vats 0-6** in the records' order: trolleys 0-3 run over vats 0-3 |
| The blockers' handler | bench: probably `$9EA4` | **`$9C76`** (activator offset 0, decoded from `$9EC4` by the logic report): entries 5-9, 4 hits, pickups |
| Header +32/+34 | map: open | spawn delay `$16B8` and marker mask `$C53D` [V: logic, flow] |
| An `obj_relocate` entry in level 2 | flow: open | **yes**: entry 4 at (672, 96) → (192, 112) [V: map, logic] |
| Names | the five sym files name 36 addresses differently; the logic report renames 4 of `main_8000.sym`'s (`spawnlist_level1` → `spawnlist_level2`, …) and the bench 1 (`msg_arrest`) | **`main_8000.sym`'s names and its 0-based level numbers stay** (`level_tick_1`, `special_l1`); step 1 merges the rest once |
