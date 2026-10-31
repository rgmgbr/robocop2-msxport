# BENCH2: proving level 2 against the original

The bench area of the level-2 plan (2026-10-27). It covers how to prove that the port's level 2 is
frame-exact against the Amiga, the way level 1 was proved (`docs/HARNESS.md` 5.2):

- the start state the original has when it enters level 2;
- the bench changes and the drives, prototyped and run;
- the trace field set;
- the MSX side: a test build that starts at level 2, and what the Tcl dumps.

No repository file was changed, and no emulator ran. Everything below lives in this folder:

`B=/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space/l2/bench`

| Path under `$B` | What it is |
|---|---|
| `tools/l2bench.py` | **new**: level 2 on the bench. `--start direct` (the level-2 RAM image and the carried state poked) or `--start flow` (level 1 played, then `load_level1` for real, Brainstorm and the range played). Imports the copies below |
| `tools/l2cov.py` | **new**: level-2 coverage, `tools/amigacov.py` plus types, messages and vats; scenario `level2` |
| `tools/tracecmp.py` | a copy of the repository's, plus `--fields FILE` (4 lines changed) |
| `tools/mockmsx.py` | **new**: writes a bench trace as the MSX trace a perfect port would give, to self-test a field file |
| `tools/seek.py` | **new**: tries drive variants in one process (it was used to time the trolleys) |
| `tools/amigaemu.py`, `amigahw.py`, `amigacov.py`, `drivejoy.py`, `bytekiller.py`, `planar.py` | copies of the repository's at 781005e, unchanged |
| `analysis/amiga_ram_l2.tsv` | **new**: level 2's field set (1,022 fields) |
| `analysis/level2_bench.sym` | **new**: the names this area found |
| `ref/l2_<name>.drive`, `ref/l2_<name>_ram.jsonl`, `.log` | the level-2 drives and their bench references (section 4) |
| `ref/flow_l2_end_ram.jsonl`, `flow_l2_end.json` | the same end drive reached through level 1, Brainstorm and the range |
| `out/cov2_run1.json`, `cov2_run2.json`, `cov2_top.json`, `cov_small.json`, `cov2_summary.json`, `routines_l2.txt` | the coverage (section 5) |
| `scripts/make_drives.py`, `scripts/make_refs.sh` | the commands that made `ref/`: the drives, then their references |
| `scripts/l2scan.py`, `jdiff.py`, `routines.py`, `mapnote.py` | readers: a trace's slots and events, two traces byte by byte, routines reached, the annotated map |
| `out/map2_a.png`, `map2_b.png` | level 2's map with the spawn list, object list, lifts and trolleys marked |
| `build/` | copies of `build/extracted`, `build/ram/level{1,2}_full.bin` and the level-1, Brainstorm and range drives used |

`PY=~/.venvs/msxports/bin/python` (Unicorn). The copies keep the repository's `ROOT` rule, so `$B/build/...` stands
in for the repository's `build/`.

**[V]** marks a fact verified with REA or a bench run, with its evidence. **[I]** marks an inference.
**[D]** marks a decision this area took while the user is away; section 8 gives each alternative.

## 1. How level 1 was proved, and what level 2 reuses

- **The Amiga side.** `tools/amigaemu.py game` (Unicorn) loads `level1_full.bin` and runs `$FEDA`, `$FFC4` and
  `level_init $871A`, then `main_loop`.
  - At each game frame's start (`$80CC`) it applies a `tools/drivejoy.py` drive: the joystick byte,
    teleports, god mode and pokes.
  - With `--trace-ram` it records `$B00-$16EB`, `$8000-$80FF` and the code-area blocks (`CODE_BLOCKS`).
- **The MSX side.** An `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1` build, driven by `tools/openmsx_rc2.tcl`
  `rc2_drive_rom`.
  - At each `tick_start` (`call game_tick`) it dumps D000h (AM), DC00h (AG), DD00h-DFFFh (AC_VARS and the
    spawn list), EE00h-F0FFh (the object list) and E900h-E9FFh (the special records).
  - Then it puts the drive's byte in `ext_joy` (CE5Ah), indexed by `tick_n` (CEE0h), and applies the drive's
    teleports, god mode and pokes.
- **The verdict.** `tools/tracecmp.py --ram` compares `analysis/amiga_ram.tsv`'s 948 fields, game frame by game
  frame: `drive_cov1` (4,401 rows) and `drive_cov0` (1,400) give 0 differ on C-BIOS_MSX2, the FS-A1FX and the
  FS-A1GT.

Level 2 reuses all of this. Five things are new:

1. a level-2 start on both sides;
2. level 2's code-area blocks;
3. a field file for level 2 (`tracecmp --fields`);
4. level 2's drives;
5. one Tcl proc for the flow through the bonus stages.

## 2. The start state of level 2

### 2.1 What the original does [V: REA on `build/ram/level2_full.bin`]

1. **Level 1 ends.** `main_loop` (`$80C2`) counts `$16C4` down after `$16D0`; then `$8050 + 1`, and `level_init`
   is called again at `$80AE`.
2. **`level_init` takes the load table.** `$873A-$8760`: D0 = `$8050`. When it differs from `level_loaded`
   (`$8052`), `$8052 = D0` and D0 + 4.
   - Then `jsr ($86FA,PC,D0*4)`. Bytes at `$86FA`: `6000fc56 6000ffdc 6000ffd8 6000ffd6 6000fbe0 6000fe72
     6000fe10 6000ffc6`.
   - Entry [5] is `bra $8582`, `load_level1`.
   - Entries [1] and [2] (levels 2 and 3 after a death or a continue) are `bra $86DC`, an `rts`: nothing is
     reloaded. Entry [7] is `$86DE`, the end after level 3.
3. **`load_level1` (`$8582`)** runs: `clr.b $8580`; `bsr $85D8` (statistics); `moveq #2,D0`, `bsr $8382`
   (Brainstorm); `moveq #1,D0`, `bsr $8420` (the range); three `nop`.
   - Then `lea $110F0,A0`, `jsr $10762` (the briefing) and `moveq #3,D0`, `jsr $11E06` (PIC4).
   - Then `move #$2700,SR` and `bsr $8614` (MU1).
   - Then the loader: MADEX (`lea -$41(PC)`), and DATAL2 through `jmp (A2)`, which returns into `level_init`.
4. **`level_init` goes on** at `$8764`:
   - `move #$2000,SR`, then `clear_game_vars` (`$FE96`: `$B00-$16EB`, `$802D`, `$802E` and `$804D` cleared,
     `$B02B` = 7Fh).
   - Header 1 at `$868C` (read at `$8664`+40):
     - lists: objects `$A828`, hazards `$95B2`, specials `$8FE0`, spawns `$97B0`;
     - RoboCop and the camera at (352, 784); relocation (192, 112); markers `$C5EC`;
     - camera_y_max `$270`; timer `$0730`; spawn delay `$2E`; marker mask 7; palette `$10036`.
   - `$B2D8` = 108h, `$B2FC` = -70h, `set_weapon` with D0 = 0 (`$8842`: weapon and ammo reset at every level
     start), the object-list pass and the activation sweep.
   - Only level 3 has a special case (`$88AC`). The random word `$B32` starts at 0: `clear_game_vars` clears it
     after `$FEDA` seeded it.
5. **`$FFC4`** (a new game only): `move.w #0,$8050`, `clr.w $805E`, `clr.l $8046`, then `$FFD8` (lives = 2).

### 2.2 What carries into level 2 [V: the bench, `ref/flow_l2_end` against the direct start]

| State | Where | Notes |
|---|---|---|
| level | `$8050` = 1, `$8052` = 1 | |
| score | `$8046`, a long, BCD | level 1's, plus the range's points |
| lives | `$8034` | |
| continues | `$805E` | + 1 by a solved Brainstorm |
| the range's hit-point table | `$8060`, a long | `$C716` SHARP, `$C71E` GOOD, `$C726` FAIR, `$C72E` POOR or time out |
| code-area state left by level 1 | `$C44A` marker step; `$F07E` explosion divider | power-on values 0 and FFh; after `drive_end`: 13 and 1 |
| HUD message state | `$8054-$805B`; slots `$FD92` | display only, not compared |

Nothing else differs.

### 2.3 The two starts

- **Direct** (`l2bench.py --start direct`, the reference for every level-2 drive):
  1. load `level2_full.bin` (RB1 MU1 DATAL2 MADEX SPERMA PERMA) and run `$FEDA` and `$FFC4`;
  2. poke `$8050` = 1, `$8052` = 1, the score, lives, continues and `$8060`;
  3. run `level_init`, which takes entry [1], the `rts`, so nothing loads and no text screen runs;
  4. go to `main_loop`. The code area keeps its power-on (image) values.
- **Flow** (`l2bench.py --start flow`):
  1. `level1_full.bin`, level 1 played with `drive_end.txt` until `main_loop` calls `load_level1`;
  2. then `load_level1` for real: the statistics, Brainstorm with `pz_fail.drive`, the range with
     `fr_good.drive`, the briefing, PIC4, MU1, MADEX and DATAL2 by the bench's loader, and `level_init`'s rest;
  3. then `main_loop`.
- **[V] The flow reproduces the known results.** Level 1 ends at game frame 517 with score 00009600.
  Brainstorm returns 1 after 182 passes. The range gives 14 correct, 0 dummy, timer 2:00, GOOD, `$8060` =
  `$C71E`. The loads are PIC4, MU1, MADEX and DATAL2. Level 2 then starts with score 00010050, 2 lives and 0
  continues.
- **[V] The flow equals the direct start** (`ref/flow_l2_end_ram.jsonl` against a direct start with carry
  `10050:2:0:good` and `--pre-poke 0xC44A:13:2 --pre-poke 0xF07E:1:1`):
  - in all 259 rows of `l2_end`, every byte of `$B00-$16EB`, `$8000-$80FF` and the level-2 code blocks is equal,
    except `$8054-$805B` (`scripts/jdiff.py`: 5 addresses);
  - so the RAM the level-2 image leaves at 0, where the real flow has FRNG's and DATAL1's leftovers
    (`$41D58-$45250`, `$27550-$28000`, ...), is never read by those 259 frames.
- **[V] The code-area carry matters.** Without those two pokes, 26 addresses differ from row 0: `$C44B`, `$F07E`,
  `$C59B`, then enemy slots 3-4, `$16B9` and `$802C`. The marker step changes which enemies spawn.
- **[V] `L2Bench` changes nothing in level 1's game phases.** It is a `FrngBench`, run with `fix_sr` off and
  MU1's player skipped, as `GameBench` runs. On level 1 with `drive_cov1` it gives the same 400 rows with RAM as
  `GameBench` (equal sha256).
- **[V] Runs are deterministic.** `l2_end` run twice gives equal hashes.

### 2.4 The carry used by the references [D]

`10050:2:0:good`: score 00010050, 2 lives, 0 continues, GOOD. This is exactly what the flow `drive_end` +
`pz_fail` + `fr_good` gives. The code area keeps its power-on values, which the port's `init` also sets in
AC_VARS: `ac_mkstep` 0, `ac_ediv` FFh, `ac_flash` FFFFh, `ac_ridest` 2. The level-2 image holds the same:
`$C44A` 0000, `$F07E` FF, `$F826` FFFF, `$8C98` 0002. The rating is GOOD, not SHARP, on purpose: a port that
resets SHARP at level 2 (RANGE.md 3.10) fails `l2_trolley` at row 4.

## 3. The bench changes (for `tools/`, when level 2 is merged)

The prototype is `tools/l2bench.py` and `tools/l2cov.py`. In the repository they become:

- **`tools/amigaemu.py game --level 2`**:
  - `--carry SCORE:LIVES:CONTINUES:TABLE`: SCORE as BCD hex digits; TABLE `sharp`, `good`, `fair`, `poor` or a
    hex address; default `10050:2:0:good`.
  - `--pre-poke ADDR:VALUE:SIZE`: the code-area carry, before `level_init`.
  - `--flow L1:PZ:FR`: the flow start, with three drives.
  - `--stop-at-end`: stops at `level_init` once `$8050` is no longer 1, that is at the level's end, or at a game
    over without a continue (0).
  - `--level 1`, the default, must stay byte-identical. The check is HARNESS 5.2's: `--gframes 600` reproduces
    the first 601 rows of `trace_cov1_ram.jsonl`.
- **`CODE_BLOCKS` per level.** Level 2's, from the coverage's code-area writes (section 5):

| Block | What |
|---|---|
| `$97B0-$99E1` | spawn list, 40 × 14 bytes and the end word |
| `$A828-$AA39` | object list, 44 × 12 |
| `$9088-$911D` | the special records (5 lifts, 4 trolleys) |
| `$92DA-$9305` | the vats' bubble phases, written at `$923C` |
| `$D1DC-$D1DD` | type 6's countdown, written at `$D1CA` and `$D20E` |
| `$A4A6-$A4A7` | act_0c's look word (display, recorded but not compared) |
| shared blocks | `$B2D6`, `$B2FA`, `$C44A`, `$C53C`, `$C598`, `$8C98`, `$B02A`, `$F07E`, `$F826`, as level 1's |

- **`tools/amigacov.py --level 2 --scenario level2`**, plus `l2cov.py`'s outputs:
  - the types seen, with their first frame and highest hit points;
  - the messages queued (`$FD76` A0's text);
  - the vats run (`level_tick_1` A3).
- **`tools/tracecmp.py --fields FILE`**. The default stays `analysis/amiga_ram.tsv`.
- **`tools/drivejoy.py`** needs no change. Its pokes into `$B00-$16EB` and `$8000-$80FF` cover the test aids
  used here: energy `$169A` and lives `$8034`.

## 4. The drives and their references [V: bench runs, `scripts/make_refs.sh`]

All drives use the direct start. The carry is `10050:2:0:good` unless the table says otherwise. Run with
`--stop-at-end --trace-ram`. File: `ref/l2_<name>_ram.jsonl`.

| Drive | Carry | Rows | What it covers | Outcome (last row) |
|---|---|---:|---|---|
| `end` | std | 259 | teleport onto the roof (200, 100) at 20, fire right every 4th frame. Cain (type 2, spawn entry 28) is shot, then touched: **"ARREST SUCESSFUL." and `$16D0` at frame 164** (written at `$C936`), the level's end at row 258 | level 2 → `$8050` = 2; types 1 2 4 14 |
| `tour` | std | 2,654 | **the play-through to the end**, described below | `$16D0` set, `$8050` = 2, no death; types 1 2 3 4 5 12 13 14 15 16 30 31 45 49 |
| `lift` | std | 801 | onto L0 (teleport (200, 784)): up to 709, down to 789; onto L1 (566, 784): up through 709 to 629, down to 789; energy poked | RoboCop (566, 785) on L1, state 10 |
| `trolley` | std | 641 | start, walk right onto L1, up, walk to x 826, jump at 482, **hang on trolley 0 (state 14) in rows 499-565**, carried to the right end, jump off right at 564: (1087, 624) past vat 0, no teleport; energy poked | (1087, 624) |
| `trolley_sharp`, `_fair`, `_poor` | the table changed | 641 each | the same, for the hit-point tables: type 1 spawns at row 4 with 2, 3, 3 or 4 hit points | as `trolley`; `$B00-$16EB` differs from GOOD's from row 4 (SHARP, POOR) or row 49 (FAIR) |
| `vat` | std | 701 | teleport over vat 0 (936, 600): falls in, **the vat's death at frame 54** (`$16CC`; energy_target FF00h by `level_tick_1`), restart at 109; then no input: **a death by the enemies at 470**, restart at 525 | lives 2 → 1 → 0 |
| `cont` | `0:0:1:good` | 301 | the vat's death with lives 0 and a continue, fire held 100-119: PIC9, the high-score check (score 0: no name), `$11FD2`; **fire continues: `$8034` = 2, `$805E` = 0, level 2 again at row 109** | lives 2, `$8050` = 1 |
| `over` | `0:0:0:good` | 109 | the same without a continue: the game ends; the bench stops at `$FFC4`'s `level_init` (`$8050` = 0) | 109 rows, then the title |
| `fuzz` | std, god | 2,501 | `drivejoy.py --fuzz 2 --frames 2500` from the start | types 1 3 4 14 15 16 30 31 |
| `flow_l2_end` | (flow) | 259 | `end` reached through level 1 (`drive_end`), Brainstorm (`pz_fail`) and the range (`fr_good`) | as `end`; see 2.3 |

How `tour` plays through the level:

1. **No teleport up to vat 3.** Walk right from the start onto L1 and ride it up. Walk to the vat-0 platform and
   wait for trolley 0. Hang on it and ride it over vat 0. Jump off right, at (1087, 624).
2. **The first blocker.** Object list entry 7 (type 0 at (1120, 579)) stops RoboCop at x 1090. Right-fire pulses
   (615-641) break it at row 640: its hits word goes 4 → -2, its look to FF10h. Then walk to x 1276.
3. **Trolleys 1 and 2.** Trolley 1 over vat 1 (up at 722, up-right at 780), landing at (1487, 624). Trolley 2 over
   vat 2, landing at (1797, 672).
4. **The second blocker and trolley 3.** Entry 8 (1872, 624) breaks the same way at row 1088. Walk to x 1989.
   Trolley 3 over vat 3, landing at (2303, 704).
5. **The lifts, with teleports.** Onto L2 at its bottom stop (1598), ride it to 465. Onto L4 (1910), ride it to
   161.
6. **The top floor and the roof.** Walk left on the top floor, firing (2080-2400). A teleport to the roof at
   2410, then fire right: Cain is arrested at row 2,559 (`$16D0` set), and the level ends at row 2,653.
7. **Test aids.** Energy (`$169A` = 100h) and lives (`$8034` = 2) are poked every 25 frames, instead of god mode,
   so that the level's end still comes. God mode holds `$16C4` at 100h.

The four trolleys are ridden in rows 499-565, 739-781, 963-1017 and 1260-1349 (state 14). There are no deaths.
Fourteen types are seen: all but 6.

**The trolley timing [V].** A trolley shuttles between its path's two x values at 2 px a frame, whatever RoboCop
does: trolley 0 reaches its left end at 168 + 160k, trolley 1 at 108 + 104k, trolley 2 at 136 + 136k, trolley 3
at 208 + 208k. The working recipe:

- stand about 21 px left of the left end;
- press up for 12 frames, starting 6 frames before the left end;
- press up-right 4-6 frames before the right end.

Lifts L2, L3 and L4 ping-pong while nobody rides them, with periods 320, 160 and 224. L0 and L1 wait at a stop.

| Reference | Rows | sha256 (first 16) |
|---|---:|---|
| `l2_end_ram.jsonl` | 259 | e0ecb97c30288d6d |
| `l2_tour_ram.jsonl` | 2,654 | d0ef114623da05c8 |
| `l2_lift_ram.jsonl` | 801 | 978d9cc7dec76d65 |
| `l2_trolley_ram.jsonl` | 641 | 8b93c3bd428166f4 |
| `l2_trolley_sharp_ram.jsonl` | 641 | 3c810e16ee4d22eb |
| `l2_trolley_fair_ram.jsonl` | 641 | 9e608b5a5255c74f |
| `l2_trolley_poor_ram.jsonl` | 641 | ba9dbf04d18c70e0 |
| `l2_vat_ram.jsonl` | 701 | 05a3aacea265b2c4 |
| `l2_cont_ram.jsonl` | 301 | 02692c53cc6458c7 |
| `l2_over_ram.jsonl` | 109 | 3d3f211d54e83db7 |
| `l2_fuzz_ram.jsonl` | 2,501 | 8bdc1c303d6c7742 |
| `flow_l2_end_ram.jsonl` | 259 | e65540af1e959526 |

## 5. Coverage [V: `l2cov.py` runs]

- **The runs.**
  - `cov2_run1`: the level-1 grid loop on level 2's map, x 150-2550 step 150, rows y 784 700 624 560 480 400
    300 220 112, 150 frames a point, god; 23,251 frames in 9 min 27 s.
  - `cov2_run2`: right 2,000, up 200, left 2,000, firing, god; 4,401 frames.
  - `cov2_top`: the top floor, 8 teleports at y 150 and 60, god; 1,701 frames.
  - `cov_small`: the `end` and `vat` drives.
- **Enemy types seen: all 15.** 1 2 3 4 5 6 12 13 14 15 16 30 31 45 49. These are the spawn list's ten types (1,
  2, 4, 5, 6, 12, 13, 14, 45, 49) and 3, 15, 16, 30, 31, which other objects spawn.
  - Type 49 appears only near the top (spawn entries 12-17 at y 16; `cov2_top`, frame 61).
  - Types 2 (Cain) and 5 spawn with 99 hit points (class 7: 99 in every table). Cain's are then pinned at 4
    every frame by `$C91A`.
- **Routines reached** (`out/routines_l2.txt`, executed blocks attributed to the nearest REA procedure entry).
  - Level 2 reaches 90 procedures; `cov_level1.json` reaches 90.
  - Level 2 only (16): `special_l1 $8F02` (trolleys), `level_tick_1 $91BC` (vats), `act_0c $9EE8`, the kill
    cases `$C33E` and `$C35A`, the updates of types 1 (`$C736`), 2 (`$C868`), 16 (`$CD7A`), 14 (`$CE0A`), 5
    (`$D0E2`), 6 (`$D1E2`), 49 (`$E6C0`) and 38 (`$E6D6`, type 49's body), and pieces attributed to `$8064`,
    `$871A` and `$9C06`.
  - Level 1 only (16): the vehicle, `level_tick_0`, `act_conveyor_right` and the updates of types 23, 24, 26,
    27, 28, 29, 32, 43 and 44.
- **Code executed.** 1,490 blocks, 10,782 bytes in 116 ranges. Of these, 431 blocks (4,136 bytes in 138 ranges)
  are never run by level 1's coverage.
- **Not reached.** `$C25C` ("CAIN DESTROYED.", the kill switch's case that also sets `$16D0`) never ran: level 2
  ends by the arrest.
- **Code Ghidra did not decode, but the bench ran it:**
  - `$D1CA-$D1DB` (`subq.w #1,$D1DC`; `+code d1ca`);
  - `$C91A-$C947`, Cain's arrest tail after the computed `jmp` at `$C90E` (`+entry c91a`).
  - That is why REA's xrefs of `$16D0` miss `$C936`. A mem-write hook on the bench found it.
- **Code-area writes in level 2.** These must live in the port's RAM and appear in the trace:
  - the spawn counters (`$97BA-$99DE`, by `$C4A4`-`$C526`);
  - the objects' look and hits (`$A82A-$AA30`);
  - the specials (lifts `+4` and `+8`, trolleys `+2` and `+8`);
  - `$92DB-$9305` (vats), `$D1DC` (type 6), `$B2D8` (also by `$C88E`: Cain's camera offset 500h),
    `$C44A`, `$C598`, `$F07E`, `$F826`.
  - Display only: `$A4A6`, `$10356` (the vat's glow line), `$104A4-$1051C` (copper palette),
    `$F846-$F852` (the "NUKE n HOST n" text's digits) and `$FD92-$FD9E` (message slots).
- **Messages queued:** TIME LOST, PROTECT THE INNOCENT, TIME GAIN, ENERGY, THREE WAY GUN, RAPID FIRE, MAN
  RESCUED, "NUKE n HOST n", REVERSE CONTROL, NUKE RETRIEVED, SCATTER GUN, ARREST ARMED EMEMY, ARREST
  SUCESSFUL.
- **The vats.** All 7 vat records ran (`$95B2-$95E2`). A vat kills by the camera's depth over it:
  `level_tick_1` sets `$16CC`, and energy_target becomes FF00h even in god mode.
- **BOB frames drawn.** 214 distinct (A2, D4): 19 in MADEX, 53 in DATAL2, the rest in SPERMA and PERMA. They are
  the input for `msxsprites.py --drawn`, as `cov_level1.json` is for level 1.

## 6. The trace fields (`analysis/amiga_ram_l2.tsv`)

`amiga_ram.tsv`'s fields with level 1's code-area records replaced, and these added. 1,022 fields:

| Field | Amiga | MSX home | Status |
|---|---|---|---|
| `spawn` | `97b0 rec:wwbbbbwwbb:40` | DD80h | as level 1's copy (40 records end at DFAFh) |
| `objl` | `a828 rec:wwwwww:44` | EE00h | to F00Fh |
| `special` | `9088 rec:w:75` | E900h | the 9 records as one block, to E995h |
| `marker_ptr` | `c598 4`, `ptr=c5ec:mk_tab2` | DD08h | **proposed**: `mk_tab2` is the port's label of level 2's marker table |
| `vat_phase` | `92da rec:w:22` | DFB0h | **proposed**: free after the spawn copy, inside the DD00h dump |
| `obj06_countdown` | `d1dc 2` | DD1Ah | **proposed**: free in AC_VARS (DD1Ah-DD1Fh) |
| `diff_table` | `8060 4`, `ptr=c716:diff_tab` | DD0Ch | the port's `ac_diff` |
| `continues` | `805e 2` | AG | |

**[V] Self-test without an emulator.** `tools/mockmsx.py` writes a reference as the trace a perfect port would
give, through this field file.

- `tracecmp --ram --fields analysis/amiga_ram_l2.tsv` then reports **0 differ** for `l2_end` (259 rows), `l2_vat`
  (701), `l2_trolley_poor` (641) and `l2_tour` (2,654).
- With `diff_table` forced to SHARP (`--mutate diff_table:0:0x9000`), all 641 frames differ, with
  `diff_table 0x18/0x0`.
- With one vat phase changed from row 700 (`--mutate 'vat_phase[3].0:700:0x4242'`), 1,954 of `l2_tour`'s frames
  differ from row 700 on.

## 7. The MSX side

### 7.1 The test build [D]

`tools/mkrom.py L2_TEST=1 L2_CARRY=SCORE:LIVES:CONTINUES:RATING`, with RATING 0-3 for SHARP-POOR and the default
`10050:2:0:1`. With `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1` for traces. It is the `PZ_TEST` pattern.

- **At power-on, without the title** (INPUT_SCRIPT already skips it):
  - `init`, as now: AC_VARS at their power-on values, `tick_n` = 0.
  - Then `ng_go`'s set-up: AG cleared, then the carry:
    - AG `$8050` = 1;
    - `$8046` (the score as AG's little-endian words);
    - `$8034` lives;
    - `$805E`;
    - `ac_diff` = `diff_tab` + 8 × RATING.
  - Then the port's level-2 start, **the same routine the product runs after the range**: level_init for level 2
    (BANK_L2, its lists into RAM, `obj_start`, `ao_start`, `engines_init`, `hud_init`), then `mainloop`.
- **Only the logic must match**, so the briefing and the display path may run or not: ticks only count in
  `mainloop`. One-shot, as `pz_first`: later games are the product's.
- **`ac_diff` moves to `ng_go` with level 2** (RANGE.md 3.10). `L2_TEST` sets it after `ng_go`.
- **Labels the Tcl reads.** `tick_start` and `game_tick`: level 2's tick must go through the same
  `tick_start: call game_tick`. Then `ext_joy`, and `l2_go`: fixed code, the level-2 start's first instruction,
  for 7.3. Also `mk_tab2` and `diff_tab` for `tracecmp`'s pointer fields.
- **RAM homes** (section 6): spawn copy DD80h, object list EE00h, special records E900h, vat phases DFB0h, type
  6's countdown DD1Ah, `ac_diff` DD0Ch. `tick_n` CEE0h and `ext_joy` CE5Ah stay where they are.

### 7.2 One drive (unchanged Tcl)

`rc2_drive_rom` works as it is. `tick_n` counts from power-on, and no level-1 tick runs in an `L2_TEST` build, so
the drive's index is level 2's game frame. It already dumps the five blocks, applies teleports, god mode and
pokes (`$169A` → DB9Ah, `$8034` → DC34h), and pauses after n rows.

```sh
sh tools/bstest/build.sh W/R/l2/rc2_l2.rom   EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 L2_TEST=1                       # 10050:2:0:1
sh tools/bstest/build.sh W/R/l2s/rc2_l2s.rom EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 L2_TEST=1 L2_CARRY=10050:2:0:0  # SHARP
sh tools/bstest/build.sh W/R/l2f/rc2_l2f.rom EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 L2_TEST=1 L2_CARRY=10050:2:0:2  # FAIR
sh tools/bstest/build.sh W/R/l2p/rc2_l2p.rom EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 L2_TEST=1 L2_CARRY=10050:2:0:3  # POOR
sh tools/bstest/build.sh W/R/l2o/rc2_l2o.rom EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 L2_TEST=1 L2_CARRY=0:0:0:1      # over
sh tools/bstest/build.sh W/R/l2c/rc2_l2c.rom EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 L2_TEST=1 L2_CARRY=0:0:1:1      # cont
```

The jobs run through the harness's `hz_chain`. Each job is a fresh machine, at 3.58 MHz, throttle off, as
`hz_regress` runs them. A new `hz_l2` in `tools/bstest/hz.tcl`:

```tcl
proc hz_l2 {dir R {tr ""}} {
	file mkdir $dir
	set e "$::hz_root/build/emu"
	set jobs {}
	foreach {name rom drive n m} [list \
			end     l2  l2_end     259  C-BIOS_MSX2       tour  l2  l2_tour  2654 C-BIOS_MSX2 \
			lift    l2  l2_lift    801  C-BIOS_MSX2       trolley l2 l2_trolley 641 C-BIOS_MSX2 \
			vat     l2  l2_vat     701  C-BIOS_MSX2       fuzz  l2  l2_fuzz  2501 C-BIOS_MSX2 \
			sharp   l2s l2_trolley 641  C-BIOS_MSX2       fair  l2f l2_trolley 641  C-BIOS_MSX2 \
			poor    l2p l2_trolley 641  C-BIOS_MSX2       over  l2o l2_over   109  C-BIOS_MSX2 \
			cont    l2c l2_cont    301  C-BIOS_MSX2       tour_fx l2 l2_tour 2654 Panasonic_FS-A1FX \
			vat_fx  l2  l2_vat     701  Panasonic_FS-A1FX trolley_eu l2 l2_trolley 641 C-BIOS_MSX2_EU] {
		lappend jobs [list l2_$name $m [list rc2_drive_rom "$R/$rom/rc2_$rom.rom" "$R/$rom/rc2_$rom.labels" \
			"$dir/l2_$name.txt" $n 0 "$e/$drive.drive"] {$::rc2_trace_done} 1800]
	}
	if {$tr eq "tr"} {
		foreach {name drive n} {tour_tr l2_tour 2654 vat_tr l2_vat 701} {
			lappend jobs [list l2_$name Panasonic_FS-A1GT [list rc2_drive_rom "$R/l2/rc2_l2.rom" \
				"$R/l2/rc2_l2.labels" "$dir/l2_$name.txt" $n 0 "$e/$drive.drive"] {$::rc2_trace_done} 1800]
		}
	}
	hz_chain $jobs
}
```

The builds behind it: `l2` (the default carry), `l2s`, `l2f` and `l2p` (`L2_CARRY=10050:2:0:0`, `:2` and
`:3`), `l2o` (`0:0:0:1`) and `l2c` (`0:0:1:1`), all with `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 L2_TEST=1`.

```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_l2 {W/O/l2} {W/R} tr
msx_local_cmd: list $::hz_state $::hz_msgs          (poll until done)
```

```sh
F="--ram --fields analysis/amiga_ram_l2.tsv"
for j in end:l2:l2_end tour:l2:l2_tour lift:l2:l2_lift trolley:l2:l2_trolley vat:l2:l2_vat fuzz:l2:l2_fuzz \
         sharp:l2s:l2_trolley_sharp fair:l2f:l2_trolley_fair poor:l2p:l2_trolley_poor over:l2o:l2_over \
         cont:l2c:l2_cont tour_fx:l2:l2_tour vat_fx:l2:l2_vat trolley_eu:l2:l2_trolley tour_tr:l2:l2_tour vat_tr:l2:l2_vat; do
  IFS=: read name rom ref <<< "$j"
  echo "== $name"; python3 -I tools/tracecmp.py $F --labels W/R/$rom/rc2_$rom.labels build/emu/${ref}_ram.jsonl W/O/l2/l2_$name.txt
done
```

Expected for each job: "N game frames compared (N Amiga, N MSX), 1022 fields: 0 differ", with section 4's N.
For example `end`: "259 game frames compared (259 Amiga, 259 MSX), 1022 fields: 0 differ".

The n of each drive is its row count in section 4: end 259, tour 2654, lift 801, trolley 641 (also with
L2_CARRY tables 0, 2, 3), vat 701, fuzz 2501, cont 301, over 109.

- **Machines.** As 5.2: C-BIOS_MSX2 (V9938, 60 Hz), the FS-A1FX (V9958) and the FS-A1GT (turbo R).
  - All drives on C-BIOS_MSX2.
  - `tour` and `vat` also on the FS-A1FX and FS-A1GT.
  - `trolley` also on C-BIOS_MSX2_EU.
- **`over`.** The port's game over (PIC9, then the title, then a new game) produces ticks of a new game after the
  109 rows. n = 109 stops the recording at the game over.
- **`cont`** needs the continue offer: section 8, D4.

### 7.3 Through the product's flow: `rc2_l2_arm`, the one new proc

- **The build.** An `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1` product build plays level 1 with `drive_end.txt`
  (`rc2_drive_rom`). The proc's flow then plays Brainstorm with `pz_fail` and the range with `fr_good`, as
  `rc2_pz_arm` / `rc2_fr_arm` do. Then it arms level 2.
- **The proc.** `rc2_l2_arm {labels file n script}` breaks at `l2_go` once and takes `tick0 = tick_n` at the first
  `tick_start` after it. Then, as `rc2_drive_hit`, with index `tick_n - tick0`, it dumps the same five blocks
  and applies the same inputs.
- **The check.** It compares with `ref/flow_l2_end_ram.jsonl`, 259 rows; the bench's flow counts level 2's frames
  from 0. The port's AC_VARS then come from its own level 1: `$C44A` 13, `$F07E` 1, as on the bench.
- **The proc in full** (for `tools/openmsx_rc2.tcl`):

```tcl
proc rc2_l2_arm {labels file n script} {
	set ts [rc2_label $labels tick_start]
	set gt [rc2_label $labels game_tick]
	rc2_drive_trace $file $n $ts $gt 0 $script     ;# opens the file, reads the drive, sets ::rd_bp
	debug remove_bp $::rd_bp
	set ::rl2_tick0 -1                             ;# -1: level 2 not started, -2: started, else its first tick_n
	set ::rl2_go [debug set_bp [rc2_label $labels l2_go] {} rc2_l2_go]
	set cond "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt && \$::rl2_tick0 != -1"
	set ::rd_bp [debug set_bp $ts $cond rc2_l2_hit]  ;# (rc2_drive_hit removes it after n rows)
	return "armed for level 2"
}
proc rc2_l2_go {} { debug remove_bp $::rl2_go; set ::rl2_tick0 -2 }
proc rc2_l2_hit {} {
	set real [rc2_w 0xCEE0]
	if {$::rl2_tick0 == -2} { set ::rl2_tick0 $real }
	rc2_wset 0xCEE0 [expr {$real - $::rl2_tick0}]   ;# the drive's index for rc2_drive_hit ...
	rc2_drive_hit
	rc2_wset 0xCEE0 $real                          ;# ... and tick_n back before the tick runs
}
```

- **Why the rewrite.** `rc2_drive_hit` reads `tick_n` for both the drive's index and `from`. Rewriting it around
  the call keeps that proc unchanged. The breakpoint fires at `tick_start`, before `call game_tick` runs, so the
  game never sees the rewritten value.
- **Alternative.** An index offset argument to `rc2_drive_hit` (D6). The proc is untested: no emulator ran in
  this phase.

### 7.4 The display, later

The play-field objects are compared with `tools/objcmp.py`, `bobcmp.py` and `rc2_bobs_rom`, as in level 1.
`l2bench.py game ... --bobs` already works for level 2, because draw_bob's hook is level-independent. Their
references come from the same drives.

## 8. Decisions taken [D] and their alternatives

| # | Decision | Alternative |
|---|---|---|
| D1 | The level-2 references use the **direct start** with carry `10050:2:0:good` and the code area at power-on values. One flow reference (`flow_l2_end`) checks the real path | every reference through the flow: slower, and every level-2 test then depends on level 1, Brainstorm and the range staying exact |
| D2 | The **rating in the default carry is GOOD**, plus `trolley_sharp`, `_fair` and `_poor` | SHARP: equal to level 1's table, so it would not catch a lost rating |
| D3 | **Test aids in `tour`**: no teleport up to vat 3. Three teleports after that: onto L2, onto L4, onto the roof. Energy and lives are poked every 25 frames. God mode is used only in `fuzz` and the coverage runs, because it holds `$16C4` and the level would never end | a fully teleport-free route: L2 must be boarded while it passes y 709, and the top floor has a gap near x 2400 |
| D4 | **`cont` is specified**: the original offers a continue after a game over when `$805E` ≥ 1 (`$11FD2`). The port's `front_over` goes to the title, so level 2's plan should port `$11FD2` (script `$11590`, fire continues: `$FFD8` and `level_init`, same level, score kept) | keep the port's PIC9-then-title and drop `cont`. Brainstorm's solve would then give a continue nobody can use |
| D5 | **The MSX homes** of the three new fields (`vat_phase` DFB0h, `obj06_countdown` DD1Ah, `mk_tab2`) are inside the five dumped blocks, so the Tcl does not change | a sixth dump block in `rc2_drive_hit`, and `tracecmp.MSX_DUMPS` extended |
| D6 | **One new Tcl proc** (`rc2_l2_arm`) for the flow | a `from` and index offset added to `rc2_drive_trace`, used by both |
| D7 | `$8054-$805B` (HUD message state) and `$A4A6` (a look word) are **not compared** | compare them once the port mirrors the message ticker |

## 9. Open questions

1. **The type-0 blockers [V: breakable; I: by which handler].** Object list entries 5-9 are type 0 at
   (1056, 224), (1136, 336), (1120, 579), (1872, 624) and (2368, 256).
   - Right-fire pulses break entries 7 and 8: hits 4 → ≤ 0, look FF10h.
   - Plain fire from x 1087 did not. Range or facing are inferred causes.
   - `$9EA4` (in level 2's activator set: a test of `+2` = 4, then an explosion, then `map_object_look $9C76`) is
     probably their handler. Confirm it from the activator table in REA.
2. **How a continue restarts level 2 on the MSX** (D4): through `level_restart` or a new path. It must give
   `l2_cont`'s rows 109-300: RoboCop at (352, 784), lives 2, `$805E` 0, `game_frame` 0.
3. **`$C25C` ("CAIN DESTROYED.")** is not reached in level 2: by level 3, or dead code? Not needed for level 2's
   traces.
4. **Type 6** (`$D1E2`, spawn entry 27 at (416, 448)) appears in `cov2_run1` but in no reference drive. A short
   drive on the left stairs (RoboCop's y in `$1A0-$1D0`) would cover its countdown `$D1DC`.
5. **The repository's `ROM_BUDGET.md` and plans call level 2's end a fight.** The bench shows an arrest: Cain's
   hit points are pinned at 4, and touching him ends the level. The level-2 plan's logic bank should port
   `$C91A`.

## 10. The commands

The prototype, now. All writes stay under `$B`.

```sh
B=/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space/l2/bench
PY=~/.venvs/msxports/bin/python
cd $B
# the drives (section 4), then their references: 11 runs, about 100 s on 2 cores
python3 -I scripts/make_drives.py $B
sh scripts/make_refs.sh $B
# the flow reference and the equivalence (section 2.3)
$PY -I tools/l2bench.py game --start flow --l1 build/emu/drive_end.txt --pz build/emu/pz_fail.drive \
    --fr build/emu/fr_good.drive --gframes 300 --drive ref/l2_end.drive --stop-at-end \
    --trace ref/flow_l2_end_ram.jsonl --trace-ram --report ref/flow_l2_end.json
$PY -I tools/l2bench.py game --start direct --carry 10050:2:0:good --pre-poke 0xC44A:13:2 --pre-poke 0xF07E:1:1 \
    --gframes 300 --drive ref/l2_end.drive --stop-at-end --trace out/direct_carry_end_ram.jsonl --trace-ram
python3 -I scripts/jdiff.py ref/flow_l2_end_ram.jsonl out/direct_carry_end_ram.jsonl   # 5 addresses: $8054-$805B
# coverage (section 5): the two scenario runs in parallel, then the top floor and the routines
$PY -I -c "import sys; sys.path.insert(0,'tools'); import l2cov; f,m=l2cov.SCENARIOS['level2']; r=m(f); open('drives/cov2_run1.spec','w').write(r[0]); open('drives/cov2_run2.spec','w').write(r[1])"
$PY -I tools/l2cov.py --carry 0:2:0:good --gframes 23250 --run "$(cat drives/cov2_run1.spec)" out/cov2_run1.json &
$PY -I tools/l2cov.py --carry 0:2:0:good --gframes 4400 --run "$(cat drives/cov2_run2.spec)" out/cov2_run2.json &
wait
$PY -I tools/l2cov.py --carry 0:2:0:good --gframes 1700 --run "$(cat drives/cov2_top.spec)" out/cov2_top.json
python3 -I scripts/routines.py rea/procs_l2.txt build/emu/cov_level1.json out/cov2_run1.json out/cov2_run2.json out/cov2_top.json
# (rea/procs_l2.txt: REA list_procedures on build/ram/level2_full.bin, "address name" lines;
#  build/emu/cov_level1.json: a copy of the repository's)
# the field file's self-test (section 6)
printf 'diff_tab:\tequ $9000\nmk_tab2:\tequ $A123\n' > out/mock.labels
python3 -I tools/mockmsx.py analysis/amiga_ram_l2.tsv out/mock.labels ref/l2_end_ram.jsonl out/mock_l2_end.txt
python3 -I tools/tracecmp.py --ram --fields analysis/amiga_ram_l2.tsv --labels out/mock.labels \
    ref/l2_end_ram.jsonl out/mock_l2_end.txt                                             # 0 differ
```

After the merge into `tools/`, the references go to `build/emu/`:

```sh
$PY -I tools/amigaemu.py game --level 2 --carry 10050:2:0:good --gframes 3000 --stop-at-end \
    --drive build/emu/l2_tour.drive --trace build/emu/l2_tour_ram.jsonl --trace-ram       # 2654 rows
```

`docs/HARNESS.md` 5.2 gains a level-2 part: the `L2_TEST` build, `hz_regress`'s job list with the drives of 7.2,
and `hz.sh compare` with `--fields analysis/amiga_ram_l2.tsv`. The level-1 regression stays as it is, and must
still give 0 differ once `ac_diff` moves to `ng_go`.
