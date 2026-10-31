# FLOW2: into and out of level 2

The "flow" area of the level-2 phase ("level 2, complete"), written on 2026-10-27. It covers how
the game gets from the shooting range into level 2 and out of it again, deaths, the game over and
the continue inside level 2, the sound, and the bonus stages' second visits. Level 2's own logic,
map, sprites and bench belong to the other areas of the phase (`space/l2/logic`, `map`,
`sprites`, `bench`); this file gives them the interface the flow needs.

Base:
- the repository at `781005e` (branch `range`), read only;
- `docs/MSX_ARCHITECTURE.md`, `docs/AMIGA_ANALYSIS.md`, `docs/ROM_BUDGET.md` (3.2, 4.1),
  `docs/BRAINSTORM.md`;
- the range's design `space/range/RANGE.md`.

No emulator ran (the phase's rule). Every Amiga fact below comes from REA (Ghidra provider,
raw-binary m68k, entry 0x0) on `build/ram/level2_full.bin` with `analysis/ghidra_seeds.tsv`,
through the MCP tools or the REA CLI 6.7.0. The listings are in `rea/listings.txt` and the new names
in `flow_level2.sym`. `$C91A` needed one extra function seed (`rea/seeds_flow.tsv`).

Tags:
- **V**: verified, by REA, by data, or by the port's source at `781005e`;
- **I**: inferred, not confirmed by a run;
- **D**: a design decision for the port;
- **E**: an estimate.

## 1. Summary

- **Into level 2 [V].** `load_level1` `$8582` runs, in order:
  1. the statistics and Brainstorm (D0 = 2);
  2. the range (D0 = 1);
  3. three `nop`s (a removed call);
  4. the level-2 briefing `$110F0`;
  5. PIC4, then MU1 (load and init, no tune);
  6. MADEX, then DATAL2, both PP20.

  Then `level_init` `$871A` reads level 2's 40-byte header at `$868C`.
- **MADEX is DATAL1's last 25,340 bytes, byte for byte [V: data].** The common BOBs at
  `$45250-$4B54B` are reloaded because FRNG's decrunch (`$1EA00-$485D9`) overwrote them [I].
  The port has nothing new to convert for MADEX.
- **What differs per level [V]** is short: the 40-byte header, the data files, and three tests of
  `$8050` in the main code. These are the hazard dispatch (level 2: `level_tick_1` `$91BC`), level
  3's lift look, and level 3's extras in `level_init`.
- **The start position is (352, 784), not (192, 112) [V].** `$87A4`/`$87A8` store header +20/+22
  = (192, 112) into `$15D6`/`$15D8`, which is `obj_relocate`'s destination. The start comes from
  +16/+18.
- **Level 2 ends when RoboCop touches Cain (type 2) [V].** The arrest tail `$C91A` then:
  - queues "ARREST SUCESSFUL." (the original's spelling);
  - requests effect 21h;
  - sets `$16D0` and `$16C4` = 40h.

  The rest is shared with level 1: 65 frames of +100 points, the fade, `$8050` = 2, then
  `load_level2` `$8524`. That runs the statistics, Brainstorm (D0 = 4), the range (D0 = 5), the
  level-3 briefing `$110B4`, PIC7, MU1 and DATAL3.
- **`$8060` [V].** Only the range writes it after a game has started. `level_init`, deaths and
  continues keep it. A new game always plays level 1 with SHARP. This confirms the range's plan:
  the SHARP set moves from `obj_start` to `ng_go`.
- **Deaths and continues in level 2 [V].** The restart entry of level 2 is an `rts`: no briefing
  and no reload, so the map keeps its changes. A continue needs a game credit, which only a
  solved Brainstorm awards, and the first Brainstorm comes after level 1. So the continue offer
  can first appear in level 2.
- **Sound [V].** The original plays no music during levels 1 and 2: MU1 holds the 42 in-game
  effects only. Level 2 needs no new sound data. A few effect numbers sound in play for the first
  time (5).
- **The port [D].**
  - After the range's result, `front_bonus` shows the next level's briefing as a text screen
    (`fe_text`; PIC4 dropped). Level 2's title "TOKUGAWA BREWERY" is typed in the game's font
    where the original's particle writer draws it.
  - Then `lv_next` starts level 2 through a level start shared with level 1 (`lv_go`, a
    per-level descriptor), keeping the score, lives, credits and the rating.
  - After level 2 come the statistics, both stages' second visits, the level-3 briefing, then the
    title (the default ending while level 3 is missing).
  - Game over in level 2: PIC9, then the continue offer when a credit exists (section 4.5).
- **The second visits (6).**
  - Brainstorm still shows Murphy and visit 1's palette. Milestone 3 adds Ellen's 9 TV pictures
    (+4 banks), visit 2's palette and the cursor's colours.
  - The range's visit 2 (its palette) is already built on the branch.
- **Test builds (7).**
  - `LV_TEST=2` starts in level 2 at power-on, once, and `LV_DIFF=0-3` picks its rating.
  - `CHEAT=1` maps the original's F10/F9 cheat keys to F5/F4, to cross the transitions quickly.
  - The product's flow does not depend on either option.
- **ROM [E].** About 127-131 banks with level 2, right at 1 MiB's 128. So the product most likely
  becomes a 2 MiB image, as decided for the whole game (section 4.8).

## 2. The original

### 2.1 From the range to level 2: `load_level1`'s tail [V]

| Address | What |
|---|---|
| `$8582` | `clr.b $8580` (`datal1_resident`: DATAL2 will overwrite DATAL1) |
| `$8588`-`$8592` | statistics `$85D8`, Brainstorm `$8382` (D0 = 2), the range `$8420` (D0 = 1): ported (`front_stats`, `front_bonus`, `front_range`) |
| `$8596` | `moveq #2,D0` and 3 `nop`s: a removed 6-byte call with D0 = 2 (**I**: the disk-2 prompt) |
| `$859E` | `lea $110F0,A0` / `jsr $10762`: the level-2 briefing, then `$FE14` (music stopped, palette black, `clear_game_vars`) |
| `$85AA` | `moveq #3,D0` / `jsr $11E06`: PIC4, 251 VBLs or fire. **Dropped** (decision 5) |
| `$85B2` | `move #$2700,SR` (no interrupts while loading) |
| `$85B6` | `bsr $8614` `load_level_music`: "MU1" (`$8656`) to `$18000` (the file cache `$11932` is off in this crack), then `jmp $18000` = init `$18180`. **No tune** |
| `$85B8` | "MADEX" (`$8579`), A1 = 0: the name table's destination `$45250`, PP20 |
| `$85C4` | "DATAL2" (`$1012F`), A1 = 0: `$28000`, PP20; `jmp` into the loader (tail call) |

The loader's name table (`$14E`, REA `read_bytes`, decoded):

| File | Id | PP20 | Destination | Size (decrunched) |
|---|---:|---|---|---:|
| MU1 | 9 | no | `$18000` | 62,800 |
| PIC4 | 16 | no | `$6FFA0` | 42,366 |
| MADEX | 17 | yes | `$45250` | 25,340 |
| DATAL2 | 18 | yes | `$28000` | 105,816 (to `$41D57`) |
| PIC7 | 21 | no | `$6FFA0` | 42,366 |
| DATAL3 | 22 | yes | `$28000` | 185,356 |

- **MADEX** (`build/extracted/files/MADEX_17.bin`) equals `DATAL1_10.bin[1D250h:]`: 25,340
  bytes, 0 differ [V: data]. DATAL1 spans `$28000-$4B54B`, so MADEX is DATAL1's tail
  `$45250-$4B54B`.
  - Level 2's BOB research found 20 frames there, all "L1 coverage, same bytes in L2"
    (`space/sprites/drawn_level2.json`).
  - FRNG's decrunch (`$1EA00-$485D9`, both visits) overwrites `$45250-$485D9`, which is why
    `load_level1` reloads it [I: the reason; the ranges are V].
  - The ledger's "MADEX: level-2 BOBs **[inferred]**" can become "DATAL1's tail, the BOBs levels
    1 and 2 share" [V].
- **Level 3** loads DATAL3 alone (`load_level2` `$855E`). DATAL3 (`$28000-$5540B`) overwrites
  MADEX and SPERMA. That is why `load_level2` clears `$857F` (`sperma_resident`), and
  `load_level0` reloads SPERMA at the next new game.
- **The briefing** `$110F0` (393 calls, 394 VBLs without fire; `build/front/scripts.json` from
  `tools/rc2front.py`, the ledger's table):
  1. `FF 04 30`: particle set-up 4, "TOKUGAWA BREWERY", colour set A (head 7, middle 8, final
     4), origin (16, −24): bitplane (32 + 16i, 40..53) — 1 call;
  2. `FF 03`: the particle writer until its 24 particles are idle — 124 calls;
  3. `00 0C 04` "ARREST CAIN" (column 12, row 4) — 1 + 11 calls;
  4. `FF 02 40`: a wait — 256 calls;
  5. `FF 07`: the end.

  With fire it ends at its first call from the 50th on. The panel stays below, and its messages
  tick on.

### 2.2 `level_init` for level 2, and every per-level difference [V]

`level_init` `$871A` (REA listing in `rea/listings.txt`) does the following, in order:
1. The player init and stop all; the VBL music tick off.
2. `seq $16CF` when `$8050` = `$8052` (the level already loaded).
3. Either the load-table entry `$8050` (a restart) or `$8050` + 4 (a load, `$8052` = `$8050`).
4. `clear_game_vars` `$FE96`.
5. The header at `$8664` + 40 × `$8050` copied into the code and the variables.
6. The fixed values; the music tick on (`$10320` = `$18018`).
7. `set_weapon(0)` `$FD30`.
8. Every object-list entry but type 58h back to look 0 and 4 hits; the map objects' pass over the
   whole map.
9. `$F89D` = Ah (the start pose), then the level-3 test (`$88AC`), then `setup_ciab_timer`.

**The headers** (`read_bytes $8664`, 3 × 40):

| Offset | Goes to | Level 1 | **Level 2** | Level 3 |
|---|---|---|---|---|
| +0 | `$9C18` object list | `$A562` | **`$A828`** | `$AA3A` |
| +4 | `$915E` hazard list | `$9538` | **`$95B2`** | `$95EC` |
| +8 | `$8B54` special objects | `$8FC0` | **`$8FE0`** | `$9008` |
| +12 | `$B0E` spawn list | `$9626` | **`$97B0`** | `$99E2` |
| +16, +18 | `$15D0`, `$15D4` (RoboCop) and `$B04`, `$B06` (camera): **the start** | (144, 800) | **(352, 784)** | (1184, 784) |
| +20, +22 | `$15D6`, `$15D8` (at `$87A4`/`$87A8`): `obj_relocate`'s destination | (996, 640) | **(192, 112)** | (224, 544) |
| +24 | `$C598`, `$C692` marker table | `$C59C` | **`$C5EC`** | `$C624` |
| +28 | `$B08` lowest camera y | 640 | **624** (50 rows × 16 − 176) | 624 |
| +30 | `$804A` timer (BCD) | 10:00 | **7:30** | 7:30 |
| +32 | `$16B8` spawn delay | 5Ah | **2Eh** | 3Ch |
| +34 | `$C53D` marker mask (byte) | 7 | **7** | 3 |
| +36 | `$F8C6`, `$F8BC` palette (the fade's source) | `$FFF6` | **`$10036`** | `$10036` |

- **Correction to the task's note**: (192, 112) at `$87A4`/`$87A8` is the relocation target, which
  level 1 uses for its cracked wall (`mapobj.asm` `act_10`). Level 2's start is (352, 784):
  `tools/player.py` turns header +16/+18/+28 into `LVL_X`/`LVL_Y`/`LVL_YMAX`. Whether level 2 has an
  `obj_relocate` entry is the logic area's question [I: `$9FC4` is in level 2's routine list of
  the ROM-budget research, `space/code/levels.json`].
- **The tests of `$8050` in the main code** (REA `xrefs $8050`):
  - `$81B8` (+1) and `$873A`/`$876C` (`level_init`);
  - `$FFC4` (new game);
  - `$0122` (the loader's PUZL disk switch) and `$83B8` (Brainstorm's decrunch on visit 1);
  - `$88AC`: level 3's extras (`$15CA`, `$15DA`/`$15DE`/`$15E2`, `$F89D` = Bh);
  - `$8EB0`: `cmpi.w #2` / `beq`, level 3's lift look;
  - `$91A4`: the hazard dispatch `$91B0` + 4 × level, so level 2 runs `level_tick_1` `$91BC`.

  `$8052` is read and written only by `level_init` (`$873E`, `$8748`).
- **Level 2's other differences live in its data**: DATAL2 (tiles, map, BOBs), the tables its
  pointers name, and the routines only its lists reach (types 1, 2, 5, 6, 14, 16, 49, the
  trolley `$8F02`, `level_tick_1`). These are the logic area's.
- **Music: none.** `level_init` calls init and stop all and turns the tick on, but starts no
  tune (5).
- **The main code is byte-identical in `level1_full.bin` and `level2_full.bin`** [V: data, first
  difference at `$28089`]. A bench run of level 2 therefore starts with the code area's power-on
  values, not with what level 1 left there (2.3).

### 2.3 What carries over from level 1 [V]

| Kept (nothing between the levels writes it) | Reset by `level_init` / `clear_game_vars` |
|---|---|
| score `$8046-$8049` (with the stages' points) | `$B00-$16EB` (energy, the statistics counters, the random word `$B32`, the objects' and the player's state) |
| lives `$8034` (an extra life from 10 hostages included) | `$802D`, `$802E`, `$804D` (inputs), `$B02B` = 7Fh |
| credits `$805E` (+1 per solved Brainstorm) | the header's 11 fields (table above) |
| `$8060`, the range's hit-point table | energy `$169A` = 100h, the can `$169C` = F0h |
| cheat flag `$804F`, the high-score table, `$8052` | camera offsets `$B2D8` = 108h, `$B2FC` = −70h |
| the code area's own variables that `level_init` does not patch: the marker scan's step `$C44A`, the flash countdown `$F826`, the explosions' divider `$F07E`, the vehicle's state `$8C98` (`ac_mkstep`, `ac_flash`, `ac_ediv`, `ac_ridest` in the port) | weapon 0 and its ammo (`set_weapon(0)`), the timer from the header, the object list but type 58h, the fade-in |

The port keeps the same split. `AC_VARS` is cleared only at power-on, AG only at a new game, and
the AM mirror at every level start.

### 2.4 `$8060` at level 2's start [V]

- Writers: `$8314` (`load_level0`: SHARP `$C716`), `$8482` (a time out: POOR `$C72E`), `$84FC`
  (`$C716` + 24 − 8 × rating). Readers: `update_objects` `$C512`, `$C706` (the ledger;
  RANGE.md 2.1).
- `$FFC4` (new game) clears `$8050`, `$805E` and the score, but never `$8052` or `$8060`. The
  file holds FFFFh at `$8052` (REA `read_bytes $802C`).
  - After a game that reached level 2 or 3, a new game takes the load path (`$8050` ≠ `$8052`):
    `load_level0` sets SHARP.
  - After a game over in level 1, it takes the restart path (`restart_level0`: the briefing and
    PIC1 again, no load). `$8060` is then still SHARP, since the range never ran in that game.
  - **So every new game plays level 1 with SHARP, and level 2 with the range's table.**
- Level 2's enemy hit points by rating. n + 1 hits kill; the class is the word at `$BEB4` + 16 ×
  type (`read_bytes $BEA6`):

| Type | Class | SHARP | GOOD | FAIR | POOR / time out |
|---|---:|---:|---:|---:|---:|
| 1 | 3 | 2 | 3 | 3 | 4 |
| 4, 12, 16 | 0 | 0 | 1 | 2 | 3 |
| 6, 13, 49 | 1 | 1 | 2 | 3 | 3 |
| 14, 45 (hostage) | 2 | 1 | 2 | 3 | 3 |
| 2 (Cain), 5 | 7 | 99 | 99 | 99 | 99 |

  A POOR rating makes types 4, 12 and 16 take four hits instead of one.

### 2.5 Level 2's end and `load_level2` [V]

- **Who ends it.** Type 2's handler `obj02_update` `$C868`:
  - queues "ARREST ARMED EMEMY." (`$DC76`) every 64 frames;
  - draws Cain and fires;
  - ends with `pea (0Eh,PC)`, so after the draw it returns into `$C91A`, `obj02_arrest_tail` (REA
    CLI listing).

  ```
  C91A move.b #4,$21(A3)      ; hit points back to 4 every frame
  C920 tst.b $23(A3)          ; RoboCop touched him ($FA7C)?
  C924 beq $C944              ;   no: D0 = 0, keep running
  C928 lea ($1360,PC),A0      ; $DC8A "ARREST SUCESSFUL."
  C92C bsr $FD76              ; queue the message
  C930 move.b #$21,$B2C       ; effect 21h
  C936 st $16D0               ; the level done
  C93A move.w #$40,$16C4      ; the end count
  C940 moveq #-1,D0 / rts     ; the slot is freed
  ```

  Type 32 (level 1's end) is not in level 2's lists, and type 22's death `$C25C` ("CAIN
  DESTROYED.") ends level 3. Ghidra's MCP session has no function at `$C91A`, so its `xrefs
  $16D0` miss `$C936`. Seeding `c91a` in `analysis/main_8000.sym` fixes that (8).
- **Then, as in level 1** (`main_loop` `$8188`, the port's `frame.asm` `frame_end`):
  - for 65 frames: +100 points a frame, and effect 26h every 4th frame;
  - the fade out;
  - `$8050` + 1 = 2 (`$81B8`);
  - `level_init` → load-table entry 6 → `load_level2` `$8524`.

  A time out during the count still costs a life, as in level 1.
- **`load_level2` `$8524`**, in order:
  1. statistics `$85D8`;
  2. `moveq #2,D0` and 3 `nop`s;
  3. `clr.b $857F`;
  4. Brainstorm `$8382` with D0 = 4;
  5. the range `$8420` with D0 = 5;
  6. the level-3 briefing `$110B4` through `$10762` (411 calls: particles 5 "CIVIC CENTRUM" at
     origin (48, −48), 109 calls, then "BATTLE YOUR WAY TO THE ROOF TO" at column 4, row 1 and
     "CONFRONT CAIN." at column 12, row 3, then a wait of 256);
  7. PIC7 (D0 = 6);
  8. MU1, then DATAL3 (a tail call).
- **The load table `$86FA`** (8 × `bra.w`, decoded from `read_bytes`):

| Entry | Target | Use |
|---|---|---|
| 0 | `$8352` `restart_level0` | level 1 again; with 2 lives (a new game or a continue) the briefing and PIC1 again |
| 1, 2 | `$86DC`: `rts` | **level 2 or 3 again: nothing** (no briefing, no picture, no load) |
| 3, 7 | `$86DE` `level_load_3` | the game completed: script `$112C5`, `$11C54` (PICF, CMP), `high_score_entry`, the title |
| 4, 5, 6 | `$82EC`, `$8582`, `$8524` | load levels 1, 2, 3 |

### 2.6 Deaths, game over and continues in level 2 [V]

- **A death with lives left** (`main_loop` `$82A0`):
  - `$8034` − 1, then `level_init` with the same level (entry 1: nothing);
  - RoboCop and the camera back at (352, 784), energy full, **the timer 7:30 again**, weapon 0;
  - every object-list entry but type 58h reset, the map objects' pass;
  - the map keeps its changes, since DATAL2 is not reloaded;
  - the score, credits and `$8060` are kept.
- **Game over** (`$82A8`), in order:
  1. PIC9, 251 VBLs or fire;
  2. 128 VBLs;
  3. `high_score_entry` `$12082`;
  4. `$11FD2`: `$805E` − 1. While still ≥ 0: `load_level_music` and script `$11590` ("YOU HAVE A
     GAME CREDIT." / "PRESS FIRE TO CONTINUE.", 304 calls) through `$10768`. Else the joystick
     byte is cleared;
  5. back at `$82D0`, fire (`$802E` bit 4) leads to `$FFD8` `init_lives` (2 lives, both heads)
     and `level_init` (level 2's restart). No fire leads to `$8098`, the title.

  The credit is used up either way.
- **`$805E`'s only writers** (REA `xrefs $805E`): `$83FA` (+1, Brainstorm solved), `$FFCC` (cleared
  by a new game), `$11FD2`/`$11FEE`. Level 1 always has `$805E` = 0, so a continue offer can only
  appear from level 2 on. A continue always returns to the level where the game ended.

### 2.7 Sound in levels 1 and 2 [V]

- MU1 (62,800 bytes; the player `$18000-$18B35` that TITM, CH1, CMP and HI1 share) holds **42
  effects and no music**. Each is a pattern on one Amiga channel (42 on channels 2 and 3), 2-57
  ticks long (`build/music/MU1.json`, `tools/rc2music.py --verify`).
- `load_level_music` reloads it before every level, because PZM/FRM overwrote `$18000`.
  `level_init` calls init and stop all and turns the tick on. No tune ever starts in a level.
- Requests: `frame_keys` `$F76C` passes `$B31` … `$B2C` to the effect entry `$18014`, once a game
  frame, under `$1822C`'s priority rule (the ledger).
- **Request sites in level-2-only routines** (REA `search_bytes 11 fc 00 ?? 0b ??`; numbers from
  the ledger's list, `$C930` from the arrest's listing):

| Site | Routine | Effect | Also in level 1? |
|---|---|---|---|
| `$8FAC` | `special_l1` (the trolley) | 0Ch | yes (`$A06E`, a conveyor) |
| `$91C4` | `level_tick_1` | 1Ah | **no** |
| `$9208` | `level_tick_1` | 10h | yes (pickups) |
| `$9F08` | `act_0c` | 28h | **no** (also level 3's types) |
| `$C930` | the arrest | 21h | via a pickup only (I) |
| `$D124` | type 5 | 12h | **no** |
| `$D298` | type 6 | 19h | yes (`act_barrier`, deaths) |

- Between the levels:
  - silent: the statistics, the briefings and the pictures (`$FE14` stops all);
  - PZM tune 1 in Brainstorm, FRM in the range;
  - silent: the continue screen (MU1 init only).

### 2.8 The bonus stages' second visits [V]

- **Brainstorm** reads `$8050` ≥ 2 (`$17156`) and then uses:
  - boards `$175C0` (start (5, 3); 23 / 21 / 24 / 28 red chips; 1:00 each);
  - palette `$17DAA` (COLOR16-31 differ: 111 DCC EBA DAA D99 333 532 444 555 A9A 756 666 B87 878
    965 CAA);
  - Ellen's face `$25160` instead of Murphy's `$244E0`.

  Quirk 5: at the end of every fade-out the palette pointer returns to visit 1's, so boards 1-3
  fade in with visit 1's colours on Ellen's face (docs/BRAINSTORM.md 2.2, 2.6, 2.8).
- **The range** reads `$8050` only at `$1FBBE`: palette `$1FC2A` instead of `$1FBEA`. FRNG is
  decrunched again, so every state starts from the file (RANGE.md 2.10).

## 3. The port today [V: source at `781005e`]

### 3.1 How level 1 starts

- `init` (`rc2.asm:20`), at power-on: `title`, then `jr ng_go` (`rc2.asm:118-120`).
- `new_game` (`rc2.asm:124`): display and VDP interrupts off. `ng_go` (`rc2.asm:131`) then runs,
  in order:
  1. `tiles_init` (`cold.asm:146`: `cpu_game`, the R800 on a turbo R; the tile cache; the map
     patches);
  2. `atr_load`;
  3. **AG cleared**, 2 lives (`rc2.asm:139-144`);
  4. `pl_init` (`cold.asm:227`: `clear_game_vars`; RoboCop and the camera at the build-time
     `LVL_X`, `LVL_Y`, `LVL_YMAX`, `cold.asm:265-271`);
  5. `lvl_bank` = `BANK_L1`, `lv_fresh` = FFh;
  6. `obj_start` (`objects.asm:39`: **`ac_diff` = `diff_tab`, SHARP, `objects.asm:44-45`**;
     camera offsets, energy; `jp lv_init`, so level 1's bank `l1_init` copies its lists and reads
     its header, `level1.asm:66-103`);
  7. `ao_start` (LC2), `engines_init` (FIELD);
  8. `hud_init` (`cold.asm:8`: score 0, ammo 0, 2 lives, weapon 0's icon, the panel uploaded);
  9. `display_on`, then the main loop.
- A death: `FE_RESTART` → `level_restart` (`rc2.asm:337`: `pl_init`, `obj_start`, `ao_start`,
  `set_weapon(0)`, `engines_init`, `display_on`; the HUD as it is).
- The level's end: `frame.asm:42-66`. `$16D0`, then the count and the fade, then AG `$8050` + 1,
  then `FE_NEXT`.
- `ml_ev` (`rc2.asm:232-249`), in order:
  1. `FE_NEXT`: `front_stats`, then `front_bonus` (Brainstorm, then `front_range`,
     `front.asm:368-395`), then **`title` and `new_game`**;
  2. `FE_OVER`: `front_over` (PIC9 30 s or fire, `front.asm:62-85`), then the title and a new
     game. There is no high-score entry and no continue. `$805E` is counted (`front.asm:380`) and
     never used (Brainstorm's default 15).
- `PZ_TEST` (`rc2.asm:257-270`): after level 1's set-up, once:
  1. AG `$8050` = `PZ_LEVEL`;
  2. `cpu_title`;
  3. `front_bonus` (or `front_rgtest` with `PZ_TEST=2`);
  4. `ml_fe`: the title and a new game.

### 3.2 What is level 1's by build (mkrom's layout)

`tools/mkrom.py` builds one level. `LOGIC` (`mkrom.py:80`) holds banks 2-9: LC1, LC2, L1, LC3,
INPUT, FRONT, FIELD and MUSIC. `STAGES` (`mkrom.py:82`) holds the stages' code banks after their
music. The current `gen/banks.inc` (Brainstorm's layout) has:

| Banks | Content |
|---|---|
| 10-17 | `BANK_TILES`: the 64 KiB VRAM image of the tiles (pages 2-3): tiles 0-255 uploaded, 256-511 read on demand |
| 18-20 | `BANK_MAP`: 51 rows, 25 a bank, read at A000h (`rowtab.inc`) |
| 21-43 | `SPR_BASE_BANK`: `robocop.bin` (RoboCop and the BOB sprites) |
| 44-45, 46, 47, 48 | HUD data, `ATR_BANK`, HUD image, `LEVEL_BANK` (OTILE, ATR2, BOBHASH) |
| 49, 50-51 | `FIELD_IMG_BANK` (play-field atlas), `FIELD_DYN_BANK` |
| 52-77 | pictures, speech, title music (SCC, FM), `SCCFX_BANK` 77 |
| 78-87 | Brainstorm: code 78, graphics 79-85, PZM 86-87 |
| 88-103 | the range (RANGE.md 3.12): code 88, graphics 89-96, hit data 97-98, FRM 99-103 |

The build-time values a second level must turn into per-level values (uses in `msx/*.asm` at
`781005e`):
- `MAP_ROWS` (11 uses: cold, field, hits, level1, both scroll engines, tiles, logic);
- `rowtab` (5) and `atr_rows` (5);
- `BANK_TILES` (3), `LEVEL_BANK` (4), `ATR_BANK` (2), `FIELD_IMG_BANK` (2), `FIELD_DYN_BANK` (2);
- `LVL_X`, `LVL_Y`, `LVL_YMAX` (`pl_init`);
- `VIEW_KX`, `VIEW_KY`, `view_offx`, `view_offy` (`player.asm`);
- `BANK_L1` (3);
- the palette `palette` (`rc2.asm:480`, `incbin "level1_grade.pal"`).

`CAM_XMAX` (2272) and `FADE_STATE` (Ah) are the same for levels 1 and 2 [V: `$B2F0` in both
images; `level_init` `$88A4`].

**VRAM per level [V].**
- Page 2 holds tiles 0-255. They are uploaded at power-on (`vdp_setup` `tiles_upload` E = 8,
  `cold.asm:487`), again by `title` (E = 4, after the SCREEN 8 pictures) and by both stages' exits
  (E = 4), always from `BANK_TILES`.
- Page 3 lines 0-87 hold the play-field atlas, **uploaded only at power-on** (`cold.asm:490`;
  BRAINSTORM.md 3.3).
- The HUD (page 3 lines 208-252) is uploaded by `hud_init`.
- So a level-2 start must upload its own tiles and atlas, and so must the next level-1 start after
  it.

### 3.3 The front end after the range

`front_bonus` ends with `call front_range` / `jp cpu_title` (`front.asm:394-395`). On a turbo R
that is the Z80 with its hardware pause on and the display off, the state `title` expects.
`fe_text` (`front.asm:516`) runs any script of positions, characters, `FF 02 n` and `FF 07`, with
`hud_keep` each tick and the `TAG` line. `fs_char` takes signed rows: the line is 67 + 8r in 8
bits, so rows −8 to 10 stay inside the play area.

## 4. The design for the port [D]

### 4.1 The sequence

| # | Original | Port |
|---|---|---|
| 1 | level 1 ends, `$8050` = 1 | as today (`frame_end`, `FE_NEXT`) |
| 2 | statistics `$85D8` | `front_stats`, unchanged |
| 3 | Brainstorm (D0 = 2), the range (D0 = 1) | `front_bonus`, unchanged up to `front_range` |
| 4 | briefing `$110F0` | **`front_brief`**, new in `front_bonus`'s tail, before `jp cpu_title`: `fe_text(txt_l2_brief)` |
| 5 | PIC4, MU1, MADEX, DATAL2 | nothing: PIC4 is dropped (decision 5) and the rest is ROM data |
| 6 | `level_init` (`$8050` = 1) | **`lv_next`**: display off, then **`lv_go`** with level 2's descriptor |
| 7 | level 2; deaths: entry 1 (`rts`) | the main loop; `level_restart` as today, made level-generic by the descriptor |
| 8 | game over: PIC9, high score, `$11FD2` | `front_over`, then **`front_cont`** when AG `$805E` > 0: fire leads to **`lv_cont`** (level 2 again, 2 lives), else the title |
| 9 | Cain arrested, `$8050` = 2 | as today (`frame_end`), with the logic area's `$C91A` |
| 10 | statistics, Brainstorm (D0 = 4), the range (D0 = 5) | `front_stats`, `front_bonus`: both stages read AG `$8050` = 2 (visit 2) |
| 11 | briefing `$110B4`, PIC7, DATAL3, level 3 | `front_brief` (`txt_l3_brief`), then **the title and a new game** (default ending, 4.6) |

`ml_ev` (fixed area). The `FE_NEXT` branch tests AG `$8050` after `front_bonus`. The `FE_OVER`
branch reads `front_over`'s answer. `ml_fe` stays `pz_test`'s path, unchanged:

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

### 4.2 One level start for both levels: `lv_go` and the level descriptor

- **`ng_go` becomes the new game's part.** It clears AG, sets 2 lives and SHARP (4.4), then
  `xor a` and falls into `lv_go`. The AG clear moves before `tiles_init` and `atr_load`, neither
  of which reads AG.
- **`lv_next`** (fixed area, ~14 B) turns the display and the VDP's interrupts off, as `new_game`
  does, then does `ld a,(AG + 0x8050)` (the word's low byte) and `jr lv_go`.
- **`lv_go`** (A = the level: 0 or 1) does the following:
  1. `lv_select` (FRONT, cold code) copies `lv_desc[A]` into `lv_cur`. It uploads the level's
     tiles 0-255 into page 2 (`tiles_upload` from the level's first tile bank, E = 4) and its
     play-field atlas into page 3 lines 0-87 (the power-on's field upload, from the level's
     `FIELD_IMG_BANK`). It points the fade at the level's palette.
  2. Then today's sequence: `tiles_init`, `atr_load`, `pl_init`, `lvl_bank` from `lv_cur`,
     `lv_fresh` = FFh, `obj_start`, `ao_start`, `engines_init`.
  3. The HUD:
     - `hud_init` for level 1 (a new game);
     - for level 2: `set_weapon(0)` (`level_init` `$8844`, as `level_restart` does) and
       **`hud_lvl`**. That is `hud_init` without the reset of the score, ammo, lives, heads and
       weapon. It clears the message queue and ticker and sets the energy display to full.
  4. `display_on`, then the main loop (the test hooks of section 7 first).
- **The descriptor** (one per level, in FRONT; ~22 bytes; copied to `lv_cur` in RAM). A candidate
  block is `F1A0h-F1C2h`: free per `msx.inc:818` and `:878` at `781005e` (35 B), and absent from
  RANGE.md 3.2's list of the range's RAM. Other agents are editing `msx.inc` on the branch, so
  check again before taking it.

| Field | Level 1 | Level 2 | Replaces |
|---|---|---|---|
| `LV_LOGIC` | `BANK_L1` | `BANK_L2` | `BANK_L1` |
| `LV_TILES` | 10 | the level's first tile bank | `BANK_TILES` |
| `LV_MAP`, `LV_ROWS` | 18, 51 | its first map bank, 50 | `BANK_MAP`, `MAP_ROWS`, `rowtab`, `atr_rows` (bank = `LV_MAP` + r / 25, address A000h + 320 (r % 25); the `ATR_RAM0`/`ATR_RAM1` split at row 48 unchanged) |
| `LV_ATR`, `LV_ATRN` | 46, `ATR_PACKED` | its own | `ATR_BANK`, `ATR_PACKED` |
| `LV_TAB` | 48 | its own (OTILE, ATR2, its BOBHASH) | `LEVEL_BANK` |
| `LV_FIMG`, `LV_FDYN` | 49, 50 | its own | `FIELD_IMG_BANK`, `FIELD_DYN_BANK` |
| `LV_X`, `LV_Y`, `LV_YMAX` | 144, 800, 640 | **352, 784, 624** | `LVL_X`, `LVL_Y`, `LVL_YMAX` |
| `LV_KY`, `LV_VOFFY` | 1434, `view_offy` | 1471 (E: mkrom's formula with 50 rows and 624), its `view_offy` | `VIEW_KY`, `view_offy` (`VIEW_KX` = 924 and `view_offx` are the same for both) |
| `LV_PAL` | `palette` | level 1's under the plan's one palette (ROM_BUDGET 3.1), else level 2's graded `$10036` | `palette` |

  `mkrom.py` writes the descriptors from each level's conversion. The level-2 data and engine
  areas own these fields' users. The flow owns `lv_select`, `lv_go` and the order.
- **The level's own code** keeps today's contract. Its bank starts with `lv_htab`, `lv_init`
  (`jp l2_init`), `lv_tick` (`jp lt1`, i.e. `level_tick_1` `$91BC`) and `lv_hz`, so
  `obj_start` and `update_objects` need no level test.
- **Level 1 does not change.** Its start runs the same steps with the same values. The only
  differences are the order of the AG clear, the SHARP set's place, the descriptor reads and the
  uploads of page 2 and the atlas, which write the bytes they hold already. Its logic traces must
  stay equal to the branch's (8, check 1).

### 4.3 The briefings as text screens

`tools/msxtext.py` gets a third group beside `BONUS` and `RANGE`: `BRIEF = (("txt_l2_brief",
0x110F0, 393), ("txt_l3_brief", 0x110B4, 411))` and `CONT = (("txt_cont", 0x11590, 304),)`. It
reads them from the RAM image, as it reads the stages' scripts.
- **The particle part** (`FF 04 p` / `FF 03`: 1 + 124 calls for level 2, 1 + 108 for level 3)
  becomes the particle text **typed in the game's 8 × 8 font**. It sits where the stroke text is
  centred, followed by a wait and, when 4n cannot make up the calls, repeated (no-op) positions.
  Each screen then lasts the original's calls, and `fs_run` checks them:
  - level 2: `00 0A FD` (column 10, row −3: x 64-191, lines 43-50, centred on the stroke text's
    x 0-253 and lines 40-53) + "TOKUGAWA BREWERY" (16) + `FF 02 1B` (108) = 125 calls. Then the
    original's `00 0C 04` "ARREST CAIN" `FF 02 40` `FF 07`. In all 393 calls and 41 bytes;
  - level 3: `00 0C FA` (column 12, row −6: x 80-183, lines 19-26; the stroke text at x 32-237,
    lines 16-29) + "CIVIC CENTRUM" (13) + `FF 02 17` (92) + 3 × `00 0C FA` = 109 calls. Then
    "BATTLE YOUR WAY TO THE ROOF TO" (column 4, row 1, ends at x 255) and "CONFRONT CAIN." (column
    12, row 3), `FF 02 40`, `FF 07`. In all 411 calls and about 83 bytes;
  - the continue `$11590` needs no change: 57 bytes, 304 calls.
- Colours: the font's own (strokes colour 1, shadow colour 4 of `$109A8`). The original's
  particles end in colour 4 (head 7, middle 8). Default 2 keeps the font as it is.
- `front_brief` (FRONT, ~20 B): AG `$8050` = 1 shows `txt_l2_brief`, 2 shows `txt_l3_brief`, else
  `ret`, all through `fe_text`. So the briefings are silent, the HUD's messages tick on below, `TAG`
  shows "TEST n" at row 10, and fire ends a screen from tick 50 on.
- PIC4 and PIC7: nothing in their place (decision 5; the stages' PIC2, PIC3, PIC5 and PIC6 set the
  precedent).

### 4.4 `ac_diff` (`$8060`)

- The 6 bytes `ld hl,diff_tab` / `ld (ac_diff),hl` move from `obj_start` (`objects.asm:44-45`) to
  `ng_go`, the port of `$8314`. RANGE.md 3.10 asked for exactly this.
- Then a new game sets SHARP (2.4). Deaths, continues and the next level's start keep the range's
  table, as the original does.
- Check: level 2's spawns take the range's table, and level 1's traces stay equal (in level 1 it
  is SHARP either way).

### 4.5 Deaths, game over and the continue

- **Deaths**: `level_restart`, unchanged, once `pl_init`, `obj_start` and the rest read
  `lv_cur`. Level 2's restart point is (352, 784) with the timer 7:30 again; level 2's `l2_init`
  rereads the header fields, as `l1_init` does.
- **The continue** (default 6: ported in this phase; the high-score entry is not). In the port the
  sequence becomes: PIC9 (30 s or fire, the user's choice), then **`front_cont`**, then the
  continue or the title.
  - `front_cont` (FRONT, ~60 B) runs only when AG `$805E` > 0, and takes one credit first.
  - It first rebuilds the game's display: `front_done` (SCREEN 5 mode, `front_mode` = 0), the
    level's page 2 again (SCREEN 8's interleaved picture overwrote it [I, from the port's own note
    in `title`; page 3, the HUD and the atlas are untouched]), `display_on` (`fb_prep` on a turbo
    R).
  - It then shows `fe_text(txt_cont)` and continues when the screen ended by fire (`fs_done` = 0)
    or fire is held at its end (`ff_bits`), as `$82D0` tests `$802E` right after `$10768`. Then
    `jp cpu_title`.
  - No credit: the title, as today.
- **`lv_cont`** (fixed area, ~20 B; the rest in FRONT):
  - AG `$8034` = 2 and both heads in the HUD (`$FFD8`);
  - the tile cache reset (`tiles_init`'s TC part only), **without** the map patches' reset or
    `atr_load`, so that the map keeps its changes as on the Amiga;
  - `cpu_game`, then `level_restart`, then the main loop.
  - Check: the map-patch pools and the attribute RAM equal before PIC9 and after the continue (8,
    check 6).
- In level 1 the offer never shows (`$805E` = 0, 2.6), so level 1's game over does not change.

### 4.6 The default ending while level 3 is missing

After the range's second visit, the level-3 briefing (`front_brief`, 411 calls) and then the
title and a new game: level 1, SHARP, score 0, 2 lives, level 1's tiles and atlas uploaded again by
`lv_go`. The test notes must say that level 3 is not in the ROM. Default 5 lists the
alternatives.

### 4.7 Where the code goes, and its size [E]

| Piece | Where | Bytes |
|---|---|---:|
| `ml_ev` changes, `lv_next`, `lv_cont`, `ng_go` → `lv_go` (incl. the SHARP set) | fixed area (190 B free; 160 in `PZ_TEST` builds) | +45 to +60 |
| `obj_start` without SHARP | LC1 (39 B free) | −6 |
| `front_brief`, `front_cont`, `lv_select`, `hud_lvl`, `front_bonus`'s extra call | FRONT (2,733 B before the range; about 2,300 after) | ~200 |
| `txt_l2_brief`, `txt_l3_brief`, `txt_cont` | FRONT (`text.inc`) | ~181 |
| `lv_desc` × 2 | FRONT | ~44 |
| `lv_cur`, `fo_cont` | RAM (audit's free list) | ~24 |
| `LV_TEST`, `CHEAT` (test builds only) | fixed area | ~30 + ~25 |

The fixed area is the scarce part. `lv_go`'s set-up can live in FRONT behind `front_call` if the
level areas also need room there.

### 4.8 ROM layout (mkrom) [D, E]

- **No existing bank moves.** New blocks go after the range's FRM (bank 103), in the range's
  manner:
  - Brainstorm's visit-2 TV pictures, 4 banks (6.1);
  - then level 2: its logic bank `L2` as a late code section (like `STAGES`: adding it to
    `LOGIC` would shift every data bank and its SCC test values), tables, attributes, atlas,
    dynamic frames, the 8 tile banks, the 2 map banks, and the sprite pool's growth for level 2.
- **Level 2 adds about 15 banks** (ROM_BUDGET 3.2) **plus its sprite share** (about 4-6 of the 8-10
  that 3.4 counts for levels 2 and 3) **and Brainstorm's 4**. With the range's 104 banks that is
  about **127-131 banks**, right at a 1 MiB image's 128. So expect **the product to become a 2 MiB
  image**. `rom_banks` pads to 256 as soon as bank 128 is used:
  - the boot guard `rom_guard` turns on, with its tag in bank 255;
  - every candidate of this phase is then 2 MiB;
  - README's requirement (a 2 MiB Konami SCC device for the complete game) goes into the notes.

  If it lands at 128 or fewer, mkrom still writes 1 MiB. Both images are within the requirement.
- **The 3Fh rule.** Bank 127 (and 191) may hold only data never mapped at 8000h: a map bank or a
  level logic bank (both read at A000h), else padding. `mkrom.py`'s `a000_only` set
  (`mkrom.py:660`) holds only the pictures today and must learn these (ROM_BUDGET 4).
- **The SCC test values** at 1800h of banks 36, 63, 90, 137 (89h) and 191 are checked on every
  build. Bank 137 will hold level-2 or later data. If the check fails, reorder or pad.
- The Pico+'s speed target: at most 53 banks selected in level 2's play, start included
  (PICO_CACHE.md; its line 456 simulates level 2 under the plan's layout). The flow's own screens
  are separate phases: the statistics, the stages, the briefings and the continue.

### 4.9 Turbo R and generic hardware

- The text screens run on the Z80 in `front_bonus`'s state (`fb_prep` on entry, `cpu_title` at
  the end).
- `lv_go` → `tiles_init` → `cpu_game` puts the R800 back, as `ng_go` does.
- `front_cont` uses `fb_prep`, then `cpu_title`. `lv_cont` calls `cpu_game`.
- No new blank appears on the turbo R: the briefing follows the range's result inside
  `front_bonus` (default 3). The PAUSE rule is `cpu_title`'s (a pending press holds the picture).
- Nothing in the flow depends on a device: plain mapper writes through `bank_8000`/`bank_a000`, the
  VDP as today, and the SCC/OPLL untouched outside the existing players.

## 5. Sound

- **Original (2.7).** Levels 1 and 2 play the 42 MU1 effects only.
- **The port in level 1 [V].** It plays:
  - the 42 effects as PSG streams (`sound.inc`, 1,415 B of effect streams in `BANK_INPUT`);
  - with an SCC, their tones on SCC channel = Amiga channel and their noise on the PSG
    (`sccfx.bin` 4,471 B in bank 77, 49 waveforms in `BANK_MUSIC`);
  - the gun's opening in place of effect 3 (`gun_scc.bin` 603 B, `gun_psg.bin` 329 B);
  - effects 2, 4 and 11 attenuated (`FX_ATTEN_DB`).

  No OPLL in play (decision 23).
- **Level 2 needs no new sound data: 0 bytes on every chip [V].**
  - Its routines request MU1's own numbers, all already converted. MU1's role stays "the in-game
    effects".
  - `tools/msxtune.py`, `msx/tune.asm` and `tools/msxsccfx.py` need no change for level 2. The
    second visits reuse PZM tune 1 and FRM unchanged.
  - The gun's opening plays at level 2's start too: `$F89D` = Ah for level 2, so player_move asks
    for it as in level 1.
- **To check**: effects 12h, 1Ah, 28h and 21h (and 10h from `level_tick_1`) are heard in play for
  the first time.
  - By ear: the previews `build/music/preview/sfx_all_*`.
  - By registers: `sess_fxlog.tcl` and `fxcheck.py` on a level-2 drive (SCC in the cartridge, in
    another slot, PSG only).
  - The `$1822C` rule is unchanged.
- **Not added**: music during level 2. The original has none, so it would be an invention, not a
  port.

## 6. The bonus stages' second visits

### 6.1 Brainstorm's visit 2 (milestone 3): what is left [V: source; D]

- **Already ported:**
  - visit 2's boards and rules (`puzl.asm:58-69`, `PZ_RECS_V2`);
  - `solve2` and `fuzz2` with 0 differences (BRAINSTORM.md 4.1);
  - the visit's pointer `pz_tv`.

  Visit 2 shows Murphy (`PZ_GFX_TV2` = `PZ_GFX_TV1`), visit 1's palette (`puzl.asm:72-73`) and
  visit 1's cursor colours (`PZ_CUR_COL_2` = 15/14, `puzl.inc:109-110`).
- **Left:**
  1. `tools/msxpuzl.py --visits 1,2` (ready) writes visit 2's 9 TV pictures (28,800 B) and
     `puzl_2.pal`. The face pair (655, 644) is provisional, the user's eye.
  2. **`rd_at` addresses only 8 banks (64 KiB) from `PUZL_GFX_BANK`** (`puzl.asm:855-867`: the
     offset's top 3 bits). Visit 2's pictures at offset 56,704 + n do not fit.
     - Default 12: a separate blob `puzl_tv2.bin` after the range's FRM, banks 104-107 (no bank
       moves). `pz_tv` becomes a bank base plus an offset (`rd_at` with the base in a variable,
       about 10 B in `BANK_PUZL`, 4,590 B free).
     - The alternative (growing `puzl_gfx.bin`) moves every range bank by 4 and still needs a wider
       `rd_at`.
  3. `pz_pal` = `pz_pal2` on visit 2 (`gen/puzl_2_grade.pal`, +32 B). The cursor's colours from
     the converter's `PZ_CUR_COL_2`/`PZ_CUR_COL2_2`. The Makefile's `msxpuzl.py` line with
     `--visits 1,2`.
  4. Quirk 5 (visit 1's palette back at each fade-out's end): reproduced (Brainstorm's default
     14), the user's call.
- **Checks:**
  - `PZ_TEST=1 PZ_LEVEL=2` stills equal `msxpuzl.py render --visit 2`;
  - `solve2` and `fuzz2` still at 0 differences;
  - visit 1 byte-identical in VRAM and pictures;
  - mkrom's SCC and 3Fh checks on the new banks.

### 6.2 The range's visit 2 [V]

It is built on the branch: `frng.asm:97-104` picks `rg_pal2` (`range_2_grade.pal`,
`frng.asm:1557-1558`) when AG `$8050` ≥ 2. The range's default 21 (the plain rounding, several
colours black) waits for the user's eye on the `range_2` previews. The flow only has to reach it
with `$8050` = 2, which `frame_end` does after level 2.

## 7. Test builds

| Option | Default | Effect |
|---|---|---|
| `LV_TEST=2` | 0 | **new**: power-on without the title, then level 1's set-up (`ng_go`), then once, instead of the main loop (`lv_test`, fixed area, test builds only). `lv_test` sets AG `$8050` = 1 and `ac_diff` = `diff_tab` + 8 × `LV_DIFF`, runs `cpu_title` and `front_l2test` (FRONT: `fb_prep`, `front_brief`, `jp cpu_title`), then `lv_next`. One-shot through `pz_first`, which mkrom refuses to share by refusing `LV_TEST` with `PZ_TEST`. Later games are the product's |
| `LV_DIFF=n` | 0 | `LV_TEST`'s rating: 0 SHARP (a new game's table, the bench's default), 1 GOOD, 2 FAIR, 3 POOR |
| `CHEAT=1` | 0 | **new**: AG `$804F` set at each new game and `key_scan` mapping F5 to key code 59h and F4 to 58h. `frame_end` already acts on them: 59h ends the level, 58h fills the energy, the original's F10/F9 after "SERIAL INTERFACE". For crossing the transitions in seconds |
| `PZ_TEST=1/2`, `PZ_LEVEL`, `TAG`, `EXTJOY`, `JOY`, `TELE`, `GOD` | as today | `PZ_TEST=1` now shows the next level's briefing after the range (front_bonus's tail), then the title, as before |

- The product's bytes and flow do not depend on `LV_TEST` or `CHEAT` (`if` blocks, as
  `PZ_TEST`).
- **Harness builds**: `EXTJOY=1 LV_TEST=2 LV_DIFF=n`, against the bench's level-2 start. The bench
  area adds `tools/amigaemu.py game --level 2 --rating n`: after `$FFC4`, `$8050` = `$8052` = 1, so
  `level_init` takes entry 1, an `rts`, and loads nothing (`level2_full.bin` holds DATAL2, MADEX
  and MU1). It also needs **`$8060` = `$C716` + 8 × n**, since the image holds 0 there.

  The image's code area has power-on values, as an `LV_TEST` build's `AC_VARS` have.
- **Candidates** (after the range's `test4`, so `TAG=5`), 2 MiB images once the product passes
  128 banks (4.8; otherwise each with a `ROM_2M=1` twin, as before), built outside `build/msx`:
  - `-test5`: the product;
  - `-test5-cheat`: `CHEAT=1`;
  - `-test5-l2`: `LV_TEST=2 CHEAT=1`;
  - optional: `-test5-l2-poor` (`LV_DIFF=3`), `-test5-bs2` (`PZ_TEST=1 PZ_LEVEL=2`, Ellen).

  Only the files sent go to `build/msx`. Each one's notes give:
  - its SHA-256;
  - the 2 MiB requirement;
  - F5/F4 in cheat builds;
  - the default ending (level 3 missing);
  - the second visits' open palette choices.

## 8. Verification (openMSX, headless, when the emulator is free)

1. **Level 1's regression**: the coverage drive's traces equal the branch's, as do the title's
   picture and music, Brainstorm's and the range's suites (their drives, stills, records), and
   `make matrix`. The SHARP move and `lv_go` must not change a single traced value.
2. **The way into level 2**:
   - in the product with `CHEAT=1`, F5 in level 1, then the statistics, Brainstorm v1 and the
     range v1;
   - the level-2 briefing: stills equal `msxtext.py`'s render, and 393 ticks without fire;
   - at level 2's first tick: AG keeps the score, lives, `$805E` and `$8050` = 1; `ac_diff` holds
     the range's rating; AM holds the header's fields;
   - page 2 equals level 2's tile image, and page 3 lines 0-87 equal its atlas.
3. **Level 2's logic** against the bench, from `LV_TEST=2` (the logic area's drives, with
   `LV_DIFF` 0 and 3): 0 differences.
4. **The way out**:
   - the arrest: message 9 (`HUD_MSG_DC8A`), effect 21h, then `$16D0`, 65 counted frames, the fade,
     `$8050` = 2;
   - the statistics, Brainstorm v2 (Ellen and visit 2's palette after milestone 3) and the range
     v2 (`rg_pal2`);
   - the level-3 briefing (411 ticks), the title, then a new game whose level 1 starts equal to
     main's record (tiles, atlas, SHARP).
5. **Deaths in level 2**: the restart at (352, 784), the timer 7:30, the map patches kept,
   `ac_diff` kept.
6. **The continue**, with a credit (from a solved Brainstorm, or a `TELE`/poke in the harness):
   - the PIC9, the continue screen (304 ticks), fire, then level 2 with 2 lives and the score
     kept;
   - the map patch pools and the attribute RAM equal to before PIC9, and `$805E` − 1;
   - without fire: the title.
   - Level 1's game over shows no offer.
7. **Sound**: section 5's register logs on level-2 drives (SCC in the cartridge and in another
   slot, PSG only); the title's registers after the new flow equal main's.
8. **Machines**: the MSX2 (V9938), an MSX2+ (V9958) and the turbo R FS-A1GT (the Z80 and R800
   changes at each transition, the PAUSE rule); a fresh machine's power-on; `tools/msxmatrix.py`'s
   10 set-ups on the product, and on `LV_TEST` builds with `--no-title`.
9. **ROM**: mkrom's checks on every option set (`ROM_2M` implied, `DIAG=1/2`, `PZ_TEST` 0-2,
   `LV_TEST`, `CHEAT`). The Pico cache's bank count for level 2 must be at most 53.

## 9. Implementation plan

| # | Step | Area | Acceptance |
|---|---|---|---|
| F1 | The SHARP set into `ng_go` | flow | check 1; `ac_diff` = SHARP at every new game |
| F2 | The descriptor and `lv_go` with level 1 only (mkrom writes `lv_desc[0]`; the engine reads `lv_cur`) | flow + engine | check 1 (level 1 equal); the image's data banks unchanged |
| F3 | Level 2's data and logic banks, `lv_desc[1]`, `LV_TEST`/`LV_DIFF` | level-2 areas + flow | check 3; level 2 plays from `LV_TEST=2` |
| F4 | `front_brief`, the three scripts (`msxtext.py`), `front_bonus`'s tail, `ml_ev`, `lv_next`, `hud_lvl` | flow | checks 2, 4, 5 |
| F5 | The continue (`front_cont`, `lv_cont`, the tile cache's reset apart from the map patches) | flow | check 6 |
| F6 | Brainstorm's milestone 3 (6.1) | flow (bonus) | 6.1's checks |
| F7 | `CHEAT`, the sound checks, the matrix, the candidates and their notes | flow | checks 7-9 |
| F8 | Documentation: `MSX_ARCHITECTURE.md` (the flow, the descriptor), `AMIGA_ANALYSIS.md` (level 2's end, MADEX, the load table, `$8060`'s paths), `ROM_BUDGET.md`, `README.md` (2 MiB), `analysis/main_8000.sym` (this area's names, the `c91a` seed) | flow | REA accepts the new seeds |

F1 and F2 can land before level 2's data exists: each leaves level 1 identical. F5 and F6 are
independent of each other.

## 10. Defaults chosen while the user is away

| # | Question | Default | Alternative | Why |
|---|---|---|---|---|
| 1 | The briefing's particle title | typed in the 8 × 8 font, same calls | port the particle writer and its stroke font (about 2.5 KiB of code, 2 KiB of RAM for 24 particles); or a 2× bitmap title (GAME OVER's look) | decision 5: text screens in the game's font; no new engine |
| 2 | The title's colours | the font's (green, colour-4 shadow) | the particles' final blue (strokes 7, shadow 4) | the same font everywhere |
| 3 | Where the briefing runs | `front_bonus`'s tail, before `jp cpu_title` | a separate FRONT entry after `front_bonus` (`front_bonus` byte-identical; one more 0.1 s blank on a turbo R) | no extra blank on the turbo R; the range's own step set the precedent |
| 4 | PIC4 / PIC7 | nothing in their place | a black pause of the picture's 251 ticks | decision 5 and the stages' precedent |
| 5 | The ending while level 3 is missing | the level-3 briefing, then the title | the title at once after the range | the original's next screen, and it tells the player what follows |
| 6 | The continue | ported now, without the high-score entry | left out (credits unused, as today) | Brainstorm promises "A GAME CREDIT"; level 2 is the first place one can be used; level 1 unchanged |
| 7 | The 128 VBLs after PIC9 | covered by PIC9's 30 s / fire | added after PIC9 | the user chose PIC9's timing |
| 8 | Level 2's set-up | display off, as `new_game` (the HUD blank for the set-up) | upload during the briefing, the HUD kept | the proven path |
| 9 | `LV_TEST` | shows the briefing first | straight into level 2 | it tests the product's path |
| 10 | `LV_DIFF` | 0 (SHARP) | 3 (POOR, the hardest) | a new game's table, the bench's start |
| 11 | `CHEAT` test option | built, F5 = end of level, F4 = energy | no cheat (drives only) | the user can cross the transitions on hardware in seconds |
| 12 | Brainstorm's visit-2 pictures | a separate blob after the range | grow `puzl_gfx.bin` (the range's banks move by 4) | no bank moves |
| 13 | Per-level values | a descriptor copied to RAM at each level start | a pointer into FRONT (every reader maps FRONT) | readers in banked code stay simple |
| 14 | VRAM at a level start | page 2 and the atlas uploaded at every level start | only when the level changes | simpler, and the same bytes for level 1 |
| 15 | Script builds (`INPUT_SCRIPT`) | the briefing runs, as the stages' texts do | skipped, as `title` is | one path; the harness presses fire |

## 11. Risks and open questions

| # | Item | Status |
|---|---|---|
| 1 | **Cain killed by shots.** His hit points are 4 again every frame; five hits in one frame would set bit 7 and run his death routine (`$C2D8`) instead, so the level would not end (I) | the logic area: bench or code check |
| 2 | **The fixed area** (190 B; 160 in `PZ_TEST` builds) | the flow needs about 50 B; move set-up code into FRONT if the level areas need room |
| 3 | **The continue's VRAM state after PIC9** (page 2 only, inferred from the G7 interleave and `title`'s comment) | check 6 dumps pages 2-3 and the map state |
| 4 | **`PZ_TEST` flows** now show a briefing after the range; the stages' flow checks expect the title next | accept the briefing in `bonuscheck.py`'s flow test |
| 5 | **Level 1 has no briefing** in the port while level 2 gets one | the user's call: adding `$11108` before level 1 changes a new game's start |
| 6 | **Level 2's palette** (level 1's under the plan, or `$10036`) | the graphics area; the descriptor carries it |
| 7 | **The 2 MiB product** | expected (decision 6); the notes and README state it |
| 8 | **`$C91A` in the seeds** | add `c91a function obj02_arrest_tail` to `analysis/main_8000.sym`, so that REA's xrefs show `$C936` |
| 9 | **Bank 127 and 137** (3Fh rule, SCC test value) inside level 2's blocks | mkrom's checks; padding costs at most a bank |

Open questions for the user (defaults stand meanwhile):
- Brainstorm visit 2: the face pair and quirk 5.
- The range's visit-2 palette.
- The briefing's title look (default 1).
- The ending (default 5).
- The continue (default 6).

## 12. Sources

- REA (Ghidra 12.1.4) on `build/ram/level2_full.bin` (SHA-256 `a039a158…`):
  - `procedure_assembly` `$8582`, `$8524`, `$8614`, `$871A`, `$80C2`, `$82EC`, `$C25C`, `$C868`;
  - `batch_decompile` `$FFC4`, `$8352`, `$11FD2`; `procedure_pseudo_code` `$FD30`;
  - `read_bytes` `$8560`, `$10120`, `$8664`, `$86FA`, `$802C`, `$14E`, `$8EA6`, `$DC8A`, `$FFC4`,
    `$BEA6`;
  - `xrefs` `$8050`, `$8052`, `$805E`, `$16D0`;
  - `search_bytes` (sound request sites, `lea $4xxxx,A2`);
  - REA CLI `instructions` `$C91A` (seed), `$8F02`, `$C736`, `$CD7A`, `$E6C0`, `$E6D6`, `$D0E2`,
    `$D1E2`, `$CE0A`.

  Listings: `rea/listings.txt`; CLI outputs: `rea/*.json`.
- Data: `build/extracted/files` (MADEX against DATAL1), `build/front/scripts.json`,
  `build/music/MU1.json`, `build/msx/sound.inc`, `build/msx/gen/banks.inc`.
- The port at `781005e`: `msx/rc2.asm`, `objects.asm`, `level1.asm`, `cold.asm`, `front.asm`,
  `frame.asm`, `puzl.asm`, `frng.asm`, `player.asm`, `msx.inc`, `tools/mkrom.py`,
  `tools/msxtext.py`, `tools/player.py`, `tools/amigaemu.py`.
- Docs: `docs/AMIGA_ANALYSIS.md` (sections 3, 4, 5), `docs/BRAINSTORM.md`, `docs/ROM_BUDGET.md`,
  `docs/MSX_ARCHITECTURE.md`, `docs/PICO_CACHE.md`, `space/range/RANGE.md`.
