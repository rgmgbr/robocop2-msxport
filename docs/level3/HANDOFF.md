# The log of the rest of the game: the user's last changes, level 3 and the ending

Plans: `../LEVEL3.md` (level 3) and the steps' briefs. Branch `level2` (it carries the rest of the game
too), from 2b44ca5 (level 2 complete, the test7 candidates); level 2's log, whose checks and commands
these steps reuse, is `../level2/HANDOFF.md`. Each step appends one section, in step order: what it
did, the files, the commits, every check with its exact command and result, the open issues. `make
test` has 4 known failures (test_line_counts_and_rank_list, test_joystick_script_entries,
test_compositions_fit_their_bank_and_the_limits, test_records_bits_ids_and_sat_order).

## Step 1: the user's last changes (2026-10-31)

**Done.** Branch `g-s01` (worktree `scratchpad/g/wt01`, from level2 2b44ca5), commits **07b2436** (the
three changes and level 1's piece cache), **51abc24** (the V9958 ring's queues) and this section's.
Records in `S1` = `scratchpad/g/s01` (`W` = the worktree): `G` (the gate: builds, verdicts), `X` (the
extra builds), `B` (level 2's chain), `V55` (the option sets), `run1` (the first run's summaries, before
51abc24), `tools/` (scratch: `mkb.sh`, `chainB2.tcl`, `fpc.tcl`, `slot2.tcl`, `fdall.py`, `pngcat.py`,
`want.py`, `whichtile.py`); the big records deleted after their verdicts, the summaries (`keep`: the
field checks, vatcheck, the speeds, the stills, the start check, the piece counts), the logs, `run1`,
the scratch tools and the pictures looked at archived in `build/archive/rest_step1_records_2026-11-01.tar.gz`. One openMSX: a private MSX-AI MCP session
(`tools/bstest/mcpd.py S1/mcp`, `mx.sh`), shut down.

### What was built
1. **The vats as static images** (the user's order: "the MSX cannot process so many frames, so we
   save performance"). `tools/mkrom.py` `VAT_ANIM` (default 0): the product shows the map's own look
   (every vat cell of the map has attributes 0 and each static column holds one look, so the map's
   cells are the level's start look). `tiles.asm` `get_tile`: `gt_rom`'s level-2 test and `gt_vat`
   only in `VAT_ANIM=1` builds (a tile costs in level 2 what it costs in level 1); `field.asm`
   `vat_init`: `vat_disp` cleared in level 2 as before, `vat_on` set only with `VAT_ANIM=1`; `vat_idle`
   and `vat_win` (tiles.asm) then do nothing and `VF_RDY` is never set. The logic is untouched
   (`level2.asm` `lt1`). `VAT_ANIM=1` = the display as built for test7; `VAT_TICK=1` is refused
   without it. `variants.sh`'s two vat sets carry `VAT_ANIM=1`. The models: `tools/mapcmp.py`
   `vat_look` returns None for a column with no nibble on the page shown (the map's own tile; the
   logic's comparison, page None, unchanged), followed by `msxframe.py`, `msxreal.py` and
   `bstest/fieldcheck.py` (such columns in neither vat class; its summary counts "vat columns seen at
   the map's own tile").
2. **`DAMAGE_X` 2 by default** (3 "made the game impossible"; 1-3 allowed, 1 for the trace builds).
3. **The missiles keep the original's damage in every build**: `hits.asm` `phb_en` skips the
   multiplication for enemy bullet types 1 and 2 (40h, from the enemies of types 3 and 27);
   `level2obj.asm` `t49_hit` takes the drone's 18h. ROM bytes read back: the product's `phb_en` is
   `ld a,c / cp 3 / jr c,+4 / ld l,e / ld h,d / add hl,de / ex de,hl`, the trace build's has no
   multiplication; in `BANK_L2` the drip's `ld de,FFECh` (FFF6h in the trace builds, FFE2h with
   `DAMAGE_X=3`) and the drone's `ld de,FFE8h` in every build (FFD0h before).
4. **Level 1's piece cache back** (the regression): `field.asm` `vat_inbox` began with `ld a,(lv_logic)
   / cp BANK_L2 / ret nz` and said "(Z: no vats)", but returned NZ in every level but 2, so from level
   2's step 14 (d7d3d3e) `fb_piece` sent every piece of level 1 to `fp_tiles`. `vat_inbox` and
   `vat_bbinit` now test `vat_on` (`ld a,(vat_on) / or a / ret z`): Z in every other level and in the
   product's level 2. Measured (`S1/tools/fpc.tcl`: `drive_cov1`'s 4,400 ticks on C-BIOS_MSX2, trace
   builds, breakpoints at `fb_piece`, `fp_cache`, `fp_tiles`; the emulated time the 4,400 ticks took):

   | build | pieces | from the cache | from the tiles | seconds |
   |---|---|---|---|---|
   | main 6082d3a (the base) | 95 | 55 | 40 | 337.4 |
   | level2 2b44ca5 | 96 | 0 | 96 | 338.8 |
   | this step (`VAT_ANIM=0`) | 95 | 55 | 40 | 334.2 |
   | this step, `VAT_ANIM=1` (`get_tile`'s test kept: the fix alone) | 91 | 53 | 38 | 334.1 |

   Level 1's pictures stay equal (the gate's field check, stills and LOCKSTEP records below). The
   gate's two verdicts judged CPU time at steps 16 and 22 **still fail with the same numbers**
   (`m2_g1490` 324 px, the PSG build's start 795): they do not come from the cache.
5. **The V9958 ring's queues** (51abc24; found by this step's field check): the product's faster
   pictures let the camera run 17 columns while a queued row waited behind the columns (the column
   first), and the row then drew columns 80-81 into the ring slots of 48-49, on the screen
   (`tour` from 2385, the product's caps, the FS-A1FX: 45 pictures, 2 cells showing the tiles 32
   columns to the right; reproduced twice, absent with `VAT_ANIM=1`; `S1/tools/slot2.tcl` logged the
   commands into that slot). `scroll9958.asm` `draw_kept`: the queues draw only the cells still in
   the kept area (as `swr_one` does for the changed cells); a skipped cell is queued again when it
   comes back. +22 B in the fixed area.

**Every write of `$169A` and every `DAMAGE_X` in `msx/`**, against the rule (weapons × `DAMAGE_X`,
the missiles × 1, the rest as the original):

| Place | Write | Rule |
|---|---|---|
| `hits.asm` `phb_en` | − the bullet type's damage (`$FA63`) | × `DAMAGE_X`, types 1-2 × 1 |
| `hits.asm` `pl_hits` (touching an enemy) | − `DAMAGE_X` (`ld de,0 - DAMAGE_X`) | × `DAMAGE_X` |
| `level2obj.asm` `t5` (the drip) | − 0Ah × `DAMAGE_X` | × `DAMAGE_X` |
| `level2obj.asm` `t49_hit` (the drone) | − 18h | × 1 (a missile) |
| `level1.asm` the beams (`lt0`) | − 10h | × 1 (a hazard) |
| `level2.asm` `lt1` (the sinking) | high byte FFh (a death) | as the original |
| `objects.asm` `death_c2d8`, `death_c1fc` | − 30h, − 20h (killing a suspect, a hostage) | × 1 (penalties) |
| `objects.asm` `en_update`, level start; `hits.asm` `pk_energy`, `pk_nuke`; `lvshared.asm` (a man rescued); `level1.asm` type 25, type 32 | 102h, 0, 100h, + 20h | not damage |
| `frame.asm` F4 (`CHEAT`), `player.asm` (`GOD`) | 102h, 100h | test builds |

Enemy bullet types 11h and 12h carry 40h in `$FA63` too (a byte read of `level1_full.bin`, `level2_full.bin`
and `level3_full.bin`, the same tables): 11h, the rocket of types 40 and 42, has an 8 × 8 box and hits, but
only level 3 has those types (`docs/LEVEL3.md` 2.6, its default 11: × 1, so `phb_en`'s test must take 11h
when level 3 is built); 12h's width is negative (it never hits). Levels 1 and 2 spawn no type 40 or 42,
so there the rule of types 1 and 2 is complete. (Type 25's second bullet, 17h, lies past the 23-entry
tables and never hits: its width byte is the height table's first, 9Dh.)

**The vats' code kept in every build** (for level 3's room): `vats.asm` 1,401 B in `BANK_L2`; `field.asm`'s
vat section (`vat_init` to its end) 1,010 B in `BANK_FIELD` (1,015 with `VAT_ANIM=1`); the fixed area
`vat_win`, `vat_idle`, `vat_l2` 33 B (+ 15 B of `gt_rom`'s test and `gt_vat` with `VAT_ANIM=1`, + `vat_tick`
with `VAT_TICK=1`); the hooks in the engines (`call vat_init`, `vat_bbinit`, `vat_inbox`, `vat_win`,
`vat_idle`) a few bytes each. Leaving `vats.asm` and the section out of `VAT_ANIM=0` builds would free
about 1.4 KiB in `BANK_L2` and 1 KiB in `BANK_FIELD`, once the harness no longer needs their labels.

**Free bytes** (`S1/G/banks.txt`, the product): the fixed area 174 (181 at 2b44ca5: −15 `get_tile`, +22
`draw_kept`), LC1 54 (+1: `phb_en`), FIELD 150 (+7), BANK_L2 28, the rest unchanged (LC2 4,842, L1 874,
LC3 4,866, INPUT 11, FRONT 1,381, MUSIC 1,331, PUZL 4,483, FRNG 264). The lowest option set
(`DIAG=1 PZ_TEST=1`) 39 B (46 at step 22).

### Checks (exact commands, results; `S1` and `W` as above; the second run, on 51abc24's code)
- **Builds**: `sh tools/bstest/l2base.sh builds S1/G`, `sh tools/bstest/hz.sh l2builds S1/G/L2R`, `sh
  S1/tools/mkb.sh W S1/X "GX EXTJOY=1 LV_TEST=2" "GXA EXTJOY=1 LV_TEST=2 VAT_ANIM=1" "L2A EXTJOY=1
  ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2 VAT_ANIM=1" "GV ... VAT_ANIM=1 VAT_TICK=1" "prod" "anim VAT_ANIM=1"
  "x3 DAMAGE_X=3" "trA EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 VAT_ANIM=1"`: all PASS; `VAT_TICK=1` alone refused
  (mkrom exit 2). **Every build log**: 94 label files, each the 12 known z80asm warnings, no error. The
  product bef7857425b227e0 (1 MiB, 127 of 128 banks), l2 16404f97538a719d, GX b55240fcbdf6bf8d, GXA
  05330a09602ab505.
- **romdiff**: `python3 -I tools/bstest/romdiff.py --blocks PRE.rom S1/G/R/prod/rc2.rom PRE_banks.inc
  S1/G/R/prod/gen/banks.inc` (PRE = 2b44ca5's product, eb8942c0…, = step 22's): **27 data blocks identical,
  romdiff: PASS**; the code blocks that differ: FIXED, LC1, FIELD, L2 (the changes) and LC2, L1, LC3,
  INPUT, FRONT, MUSIC, PUZL, FRNG. `python3 -I tools/bstest/relocheck.py ... BANK_LC2 BANK_L1 BANK_LC3
  BANK_INPUT BANK_FRONT BANK_MUSIC BANK_PUZL BANK_FRNG`: every differing byte a relocated label word but
  three label-plus-constant operands (`ld de,mk_tab - 0C59Ch` in L1, `ld hl,diff_tab + 18h` twice in FRONT),
  moved by −1 with LC1's labels after `phb_en`.
- **The gate**: `source W/tools/bstest/load.tcl; source W/tools/bstest/l2base.tcl; l2b_chain S1/G
  S1/G/all.done` (227 jobs, 0 time outs), `sh tools/bstest/l2base.sh check S1/G scratchpad/l2/base`
  (main 6082d3a's base): **regress: PASS, 45 verdicts** (the product's flows with `DAMAGE_X` 2 among them:
  every drive ends where it did, so no drive needed other options); level 1's die / over / end 0 differ;
  the start check PASS on the three machines; the field check PASS (860's known class, as step 22);
  LOCKSTEP 2,998 lists 0 differ on both machines; the SCC build's effects PASS. **The same two verdicts as
  steps 16 and 22 FAIL**: the still `m2_g1490` (324 px, msxframe 543 against 462) and the PSG build's start
  795 (effect 4: 10 against 11, one tick). `l2base: FAIL` on those two only. The first run (07b2436's
  code) gave the same verdicts.
- **Level 2's traces** (chain B2: `S1/tools/chainB2.tcl`, 126 jobs, 0 time outs): `sh tools/bstest/hz.sh
  compare --fields analysis/amiga_ram_l2.tsv S1/G/O/l2 S1/G/L2R`: **level 2: PASS (23 traces)**, lost 0;
  `python3 -I tools/bstest/contcheck.py S1/G/O/l2 TAG MODE --gen S1/G/L2R/l2c/gen`: cont, cont_fx, cont_tr
  `--fire`, cont2 `--again`, cont_nf `--no-fire`, over `--none`: **PASS all six** (their builds keep
  `DAMAGE_X=1`; the first pictures after `lv_cont` 0 pixels differ).
- **The field check** (`python3 -I S1/tools/fdall.py S1 W`: `fieldcheck.py DIR build/msx/level2 DIR.png
  --level 2` on each): `tour`'s 11 windows (1 300, 150 300, 495 300, 735 200, 960 250, 1150 300, 1255
  350, 2140 260, 2385 400, 2420 400, 2500 300) and `barrel`'s 2 (70 300, 300 300) on GX, and the vat
  windows (495, 735, 960, 1255) on GXA, three machines each: **51 windows, 15,180 pictures, 0
  differences**; GX: up to 33 vat columns a window at the map's own tile, none drawn; GXA: the vat
  columns drawn, none older. The first run had `tour` 2385 on the FS-A1FX at 45 pictures, 9,831 px
  (item 5); with 51abc24: 0 in 400 pictures on the three machines.
- **Looked at** (`S1/look_vat_sink.png`, `S1/look_vats_495_m2.png`): vat 0 from the trolley as the view
  scrolls over it (window 495, the MSX2) and RoboCop sinking into it (`cut` stills): the map's look, the
  same splashes and bubbles at the same places in every picture, no column of another look.
- **Stills** (check 6, `hz_l2_still_jobs` 12 frames × 3 machines, `msxframe.py ... --level 2 --field`): the
  play area exact in all 36; the known classes only: msxframe's object order (g2395 18 px on the MSX2 and
  the turbo R, g2555 37 on the MSX2+), the HUD's can at the arrest (g2555, 167-171 px), and one new
  instance of a HUD message's next letter (fx g1000: 27 px, the "U" of a message typed letter by letter,
  drawn in the next picture). **The cut** (check 9): `cutview.py cut S1/B/cut build/emu/l2_vat_ram.jsonl`:
  **cut: PASS** (35 stills with a cut, all exact). **The start check** (check 1, GX, 42 s): tear 0, pal,
  cpu, vbl 0; reg 0/6/1, cmd 1/11/3 (the play-field copies' known class; 44/62/335 at step 16 with the
  vat columns' parts); patcheck 0 bad; satcheck frame 0 only; lost 0.
- **The vats' records** (`vl_jobs`, `python3 -I tools/bstest/vatcheck.py DIR`): exit 0 in all 21 windows.
  The product (`tour` from 450 and 850, standing at vat 0): **0 vat columns drawn, `vat_run` and
  `vat_prep` 0 calls**; `VAT_ANIM=1` (L2A; 450, 850, 1250, standing): 0.7-1.2 columns a second on the MSX2,
  1.3-2.4 on the MSX2+, 4.5-15.6 on the turbo R, as at step 22; guard tears 0 of a vat column.
- **The speed** (`vl_speed_jobs` on `S1/G/L2R/l2` against `S1/X/L2A`: the same trace build, `VAT_ANIM` 0
  and 1; ticks and pictures a second; the turbo R holds 25 ticks in both):

| the product against `VAT_ANIM=1` | MSX2 ticks | MSX2 pictures | MSX2+ ticks | MSX2+ pictures | turbo R pictures |
|---|---|---|---|---|---|
| `tour` from 450 (25 s) | 14.08 / 13.68 (+2.9 %) | 11.16 / 10.84 (+3.0 %) | 17.00 / 15.60 (+9.0 %) | 9.08 / 7.88 (+15.2 %) | 31.64 / 29.04 (+9.0 %) |
| `tour` from 850 (25 s) | 18.32 / 17.76 (+3.2 %) | 17.88 / 16.36 (+9.3 %) | 21.64 / 21.12 (+2.5 %) | 15.08 / 13.64 (+10.6 %) | 41.20 / 38.76 (+6.3 %) |
| standing at vat 0 from 540 (20 s) | 16.85 / 16.25 (+3.7 %) | 9.95 / 9.85 (+1.0 %) | 20.00 / 19.20 (+4.2 %) | 10.75 / 10.10 (+6.4 %) | 28.80 / 26.20 (+9.9 %) |

- **The option sets**: `sh tools/bstest/variants.sh S1/V55` + `python3 -I tools/bstest/l2base.py banks
  S1/V55`: **52 of 55** (`DEMO_ACTORS` 2 and 5 −E9h, `DEMO_HUD` −30h: the same three as before, 7 B more
  over); the lowest set 39 B; BANK_L2 28 in every set.
- **make test** (the worktree, 51abc24 + this section): 329 tests, **the 4 known failures only** (failures 3,
  errors 1, 54 skipped).

### Open issues
1. The two CPU-time verdicts against main's base stay (`m2_g1490`, the PSG tick) until a base is made from
   the integrated tree (`l2base.sh base`).
2. `tour` from 450 with the product's caps: the guard counts one tear of a play-field copy on the FS-A1FX
   (f 605, 40 × 32 at the play area's last line) and one on the turbo R (f 618, 64 × 64): the staged
   pieces' class (`docs/LEVEL2.md` 8.1 item 4; step 22 saw the turbo R's).
3. The fixed area: 39 B in the lowest option set.
4. The matrix of generic set-ups was not run on this step's product (no start path changed); the
   candidates' builds should run it.

### Integrated
Cherry-picked onto level2 b7934b0 (step 2 integrated first) as **7779f02** (the three changes and level
1's piece cache), **a08e5c7** (the ring's queues) and **e723623** (the docs; this file resolved with both
sections in step order). From the main tree (`sh S1/tools/mkb.sh REPO S1/I "prod" "GX EXTJOY=1 LV_TEST=2"
"l2 EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2" "anim VAT_ANIM=1" "trace EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1"`):
the five ROMs **byte-identical** to the worktree's (the product bef7857425b227e0), so every result above
holds for the integrated tree; `make test`: 329 tests, the 4 known failures only.

## Step 2: level 3's research and plan (2026-11-01)

**Done, offline (REA and Python only, no openMSX).** Worktree `g/wt02`, branch `g-s02` from
`2b44ca5`; scratch `S=$SCRATCH/g/s02`; archive `build/archive/level3_research_2026-11-01.tar.gz`.

### What it did
- **The RAM image** (`Makefile`): `level3_full.bin` is built with SPERMA under DATAL3 (`RB1 MU1 SPERMA
  DATAL3 PERMA`), as the Amiga holds it: SPERMA's tail `$5540C-$5884D` (13,378 B, types 4 and 12's
  frames) was zeros before. sha256 `700df44da0688c8cd616f368aa6014535fcc3e33a312404f92ca35eda73515ca`.
- **The bench plays level 3**: `tools/amigaemu.py game --level 3` (`Level3Bench`: Level2Bench's direct
  start with `$8050` = `$8052` = 2, `--stop-at-end` at `$8050` = 3, `CODE_BLOCKS_L3` from the
  coverage's code-area writes) and `tools/amigacov.py --level 3 --scenario level3`.
- **The names**: `analysis/main_8000.sym` (level 3's block and ten `+entry` seeds),
  `analysis/ghidra_seeds.tsv` regenerated (126 functions, 303 labels).
- **The plan**: `docs/LEVEL3.md` (the original, the design, the checks, steps A-E, 15 defaults, the
  risks); `docs/AMIGA_ANALYSIS.md` (a level-3 section); `docs/ROM_BUDGET.md` 7 (two tooling items done).

### Commits
- `934e2f1` Makefile (level 3's RAM image).
- `d0afe4c` the bench, the coverage, the names and seeds.
- `5546686` the docs (this section, `docs/LEVEL3.md`, the ledger, `ROM_BUDGET.md` 7).
- Integrated into `level2` (clean tree, from `2b44ca5`) by cherry-pick as **`1a2edef`, `fe12770`,
  `9150383`**. In the main tree then: `build/ram/level3_full.bin` rebuilt with the Makefile's line
  (sha256 `700df44d…3515ca`); the product built from it (`sh tools/bstest/build.sh OUT.rom`) is
  byte-identical to `2b44ca5`'s (no ROM source changed); `amigaemu.py game --level 3 --gframes 200
  --god` runs (201 game frames, `$8050` 2).

### Checks (each with its command and result)
- The image: `python3 -I tools/ramimage.py build/extracted build/ram/level3 RB1 MU1 SPERMA DATAL3 PERMA`
  → SPERMA `$4b68a-$5884e`, DATAL3 `$28000-$5540c`; zeros in `$5540C-$5884D` 13,378 → 5,312 (the data's
  own zeros); `$8000-$125FF` equal to `level2_full.bin`'s (first difference `$28080`).
- REA seeds: `REA_GHIDRA_SEED_FILE=analysis/ghidra_seeds.tsv npx -y rea-agents@6.7.0 instructions
  build/ram/level3_full.bin 0xc398 --target-format raw-binary --architecture m68k --entry-point 0x0
  --provider ghidra --format json` → "125 functions created, 1 already present, 0 failed; 303 labels
  applied, 0 failed"; `$C398` named `debris_add`.
- The bench unchanged for levels 1 and 2: `tools/amigaemu.py game [--level 2] --gframes 300 --trace
  OUT --trace-ram --joy 70:200:rf` with the base's `amigaemu.py` (the main tree at `2b44ca5`) and this
  one: level 1 `02a902bf232125bd…`, level 2 `b3f75b3e8b7b3a42…`, both byte-identical.
- `python3 -I -m unittest discover -s tests -p 'test_level2_bench.py'` with the venv's Python: 15 OK.
- The coverage: `~/.venvs/msxports/bin/python -I tools/amigacov.py --level 3 --scenario level3
  $S/cov_level3.json` → 1,150 blocks, 11,176 bytes of code run, 173 code-area addresses written, 183
  BOB frames, types 4, 12, 21, 22, 33-43, 47, 48, 50, 51, 52 (every spawned type), 610 s.
- Cain: `$S/py/bossrun.py <tree> OUT FRAMES loop|fight2200|kill2050` (Level3Bench, god mode): "CHASE
  CAIN" at game frame 243 (at 250 RoboCop at (1176, 91), Cain at (1237, 56)); Cain at y 255 with 44 hit points
  from then on; killed after the poke at frame 820: "CAIN DESTROYED." at 868, `$16D0` set, the bench
  at `level_init` with `$8050` = 3 at 962; 19 frames more than the coverage (202 in all).
- The palette: `python3 -I tools/msxlvpal.py palette build/extracted/files/DATAL3_22.bin --pal-file
  build/extracted/boot/main_8000.bin --base-addr 0xfff6 --pal-addr 0x10036 --base build/msx/robocop
  --rows 50 -o $S/l3conv/level3` → mean ΔE76 C 2.179, A 2.675; `cmp level3.pal build/msx/level2.pal`
  and the remaps: identical.
- The map: `python3 -I tools/msxconv.py level build/extracted/files/DATAL3_22.bin --pal-file
  build/extracted/boot/main_8000.bin --pal-addr 0x10036 --rows 50 --joint $S/l3conv/level3 -o
  $S/l3conv/level3` → 485 offsets (481 tiles), 505 tiles, 64,640 B; a scan of `level3.map`: at most 106
  distinct tiles in 19 × 14 cells, 102 in 17 × 14 (the same scan gives level 2's 107 and 103).
- The free bytes: `sh tools/bstest/build.sh $S/R/prod/rc2.rom` (and `DIAG=1 PZ_TEST=1`, `LV_TEST=2
  CHEAT=1`), `python3 -I tools/bstest/l2base.py banks $S` → `docs/LEVEL3.md` 3.2's table (fixed area
  181 / 162 / 46, FRONT 1,381 / 1,326 / 983, `BANK_FIELD` 143, `BANK_L2` 28). Builds OK, 12 known
  z80asm warnings.
- `make test` → 321 tests, the 4 known failures only (failures=3, errors=1, skipped=54).

### Open issues
- Cain's chase in a drive without god mode (the `kill` reference of `docs/LEVEL3.md` 3.8) is step A's
  or D's: the drives here put RoboCop on the ground floor and Cain stayed on row 20.
- The frames the bench did not draw (rare states of Cain, types 36, 37) come from REA's tables in step C.
- The ending's hook needs step 3's entry name (until then `$8050` = 3 goes to the title).

## Step 3: the game completed and the high scores (2026-11-01)

**Done.** Worktree `g/wt03`, branch `g-s03` from `2b44ca5`, rebased onto `level2` `d44821d` (steps 1 and 2
integrated); scratch `S3` = `$SCRATCH/g/s03`. One openMSX: a private MSX-AI MCP session
(`tools/bstest/mcpd.py S3/mcp`, `mx.sh`), shut down. The design and the facts: `../ENDING.md`.

### What was built
- **The facts** (REA, Ghidra 12.1.4, raw-binary m68k, entry `0x0`, the project's seeds, on
  `build/ram/level3_full.bin`; `$8000-$17FFF` the same bytes in the three images): `level_load_3`
  `$86DE`, the text `$112C5`, `$11C54` (PICF, CMP, 1801h passes, the tune on 4 of 5: 4,916 ticks, fire
  at once), `high_score_entry` `$12082` (only a greater score, ties keep the older above), the name
  entry `$1215C` and its keys `$1225C` (keyboard only, no timeout), the table `$11FF6`; named in
  `analysis/main_8000.sym` (seeds regenerated), `docs/AMIGA_ANALYSIS.md` extended.
- **The code** (`msx/ending.asm` in **`BANK_FRONT2`, bank 127** at A000h; `msx/frontx.asm` appended to
  FRONT): `front_ending` (WELL DONE typed as the briefings, then CMP while that screen stays on, 4,916
  ticks or fire pressed once released), `hs_entry` (the entry after every game over and after the
  ending; the MSX keyboard's matrix; the table screen after an entry), the table in RAM from the
  power-on (C2D9h, C5D0h), `fr_ending` **the ending's one way in** (`ld hl,fr_ending` / `call
  front_call`, then `ml_ttl`), `fb_brief2` (front_bonus calls it after the level-3 briefing until level
  3 is in), `fo_hsc` (front_over), `ci_hook` (cold_init: `rom_guard`, moved from `cold.asm`, and the
  table). FRONT's own code keeps its place: three call operands of the same size change. `tune.asm`
  `tn_cmp` and `tune_cm.inc` after the player.
- **The sound**: `tools/msxtune.py --end` → `build/msx/end.bin` (27,110 B, banks 128-131): CMP tune 1
  unrolled to 4,916 ticks (SCC 12,797 B, OPLL 8,793 B with HH and TCY, PSG 5,287 B), its speech silent,
  HI1's effects 3 and 4.
- **The texts**: `tools/msxtext.py` → `build/msx/ending.inc` (`txt_end` 111 B, `txt_hisc` 102 B,
  `txt_best` 5 B, `hs_head`, `hs_def`) and `text_end.sc5`, `text_hisc.sc5`, `text_best.sc5`; `text.inc`
  unchanged.
- **The options**: `END_TEST=1` (the ending at power-on, `LV_CARRY`'s score) and `END_TEST=2` (a game
  over: PIC9, the entry, the offer with `LV_CARRY`'s credits); refused with `PZ_TEST`, `LV_TEST`, `DIAG`.
- **The harness**: `tools/bstest/ending.tcl` (`ge_job`, `ge_ret_arm`), `endcheck.py`,
  `frsnd/endsim.py`; `np.tcl` (`np_t_poll` arms RETURN at the entry after the stages' records) and
  `cheat.tcl` go through the ending; `docs/HARNESS.md` 5.25. `tests/test_ending.py` (10 tests).
- **The image**: 2 MiB, **132 of 256 banks** (127 `BANK_FRONT2`, 128-131 `END_BANK`); the boot guard on.
  Free bytes (`l2base.py banks`, the product on `d44821d`): fixed area **174** (unchanged by this step),
  FRONT **1,173** (1,381 before: `rom_guard` 143 B, `frontx.asm` 65 B), MUSIC **1,251** (1,331),
  FRONT2 **7,041**, FIELD 150, `BANK_L2` 28.

### Commits
- `90ac5a7` the ending and the high scores (code, tools, harness, tests); `8998d60` the docs, the
  harness's flows, the names; this section's (all three rebased onto `d44821d`; before the rebase
  `d37b8fd`, `99bff05` on `2b44ca5`).

### Checks (each with its command and result; `W` = the worktree, `PY` the venv's Python)
- **Builds**: `sh tools/bstest/build.sh S3/b2/NAME/rc2.rom OPTIONS` for the product, `e1`
  (`END_TEST=1 LV_CARRY=10050:2:0:1`), `e1t` (+ `TAG=8`), `e2` (`END_TEST=2 LV_CARRY=10050:0:1:1`),
  `e2n` (`...:0:0:1`), `e2s` (`END_TEST=2 LV_CARRY=7500:0:1:1`), `cheat`, `ext`, `diag` (`DIAG=1`);
  `sh tools/bstest/hz.sh builds S3/G/R`, `... l2builds S3/G/L2R`, `X/p2m` (`ROM_2M=1`): every log
  "build OK", the 12 known z80asm warnings only. The product `460553ba86166756` on `2b44ca5`,
  `4ffbd9695dff6907` on `d44821d`; `ROM_2M=1` the same bytes as the product.
- **The banks**: `python3 -I tools/bstest/romdiff.py --blocks BASE.rom NEW.rom` against the product of
  `2b44ca5` and of `d44821d` (built from the main tree): **37 blocks identical; code blocks that differ:
  BANK_FRONT, BANK_MUSIC**; FRONT differs at `807Eh`, `82D1h`, `8A3Ah` (the three calls) and from its old
  end `9A9Bh`, MUSIC from its old end `BACDh`; `BANK_FRONT2` and `END_BANK` new: every other code bank's
  checks stand.
- **The sound** (no emulator): `$PY -I tools/bstest/frsnd/endsim.py W S3/b3/prod/rc2.rom
  S3/b3/prod/rc2.labels` → **all: PASS** (the tune's 4,916 ticks and 60 after on SCC + PSG drums, SCC +
  OPLL rhythm, OPLL alone, PSG alone at 50 and 60 Hz, `tn_left` 0 at tick 4,916, no write after; the
  entry's effects, 14 started, 2 refused by `$1822C`'s rule; the R800 without an OPLL write). A one-bit
  change in the image's SCC, OPLL or PSG stream fails it (3 of 3 caught).
- **The screens** (`docs/HARNESS.md` 5.25's chain, 7 jobs on the Expert, C-BIOS_MSX2, the HB-F1XDJ,
  the FS-A1FX and the FS-A1GT; `bash S3/tools/endchecks.sh S3/E2 S3/b2`): **endcheck PASS on all 7**:
  WELL DONE, 33 waits of the name entry (R O B O C O P 2 X BS KP9 Z RET; RET alone with `TAG=8`; BS SPACE
  M S X RET; A RET; K E Y P A D KP0 KP1 RET), the table screens and the continue offer after an entry,
  each equal to the render pixel for pixel with R#0 16h, R#1 62h and txt_pal; the tune 4,917 ticks to
  `tn_left` 0 in 98.5 emulated s; no entry for a tie (7500), no offer without a credit; the table in RAM
  as the model. Looked at: `e1_end`, `e1_hs10`, `e1t_hs0` (TEST 8), `e2_best` (" MSX" under KEITH),
  `e2_cont`, `e1tr_end`.
- **The gate's flows** (`rgr_jobs S3/G flows`, `hz_l2_jobs S3/G/O/l2 S3/G/L2R tr {end over cont cont_fx
  cont_tr cont_nf cont2 flow_l2_end}`, `ch_job`: 30 jobs, `S3/tools/gate.tcl`): `sh tools/bstest/regress.sh
  check S3/G scratchpad/l2/base flows` → **regress: PASS**: level 1's coverage traces, the title from
  power-on (exact: the picture, registers, palette and the music at every tick identical), the
  product's and `PZ_TEST=1` flows, the restore, the turbo R's blank (6 frames, as the base), the turbo
  R's writes, **the product's whole flow through the ending and the title after it** (ex, f1, tr: the
  picture, the registers that show and the palette identical; the music `titlecmp2.py --unheard` PASS:
  the SCC registers that differ are channel 3's, which the title never sounds), the 2 MiB product, the
  keyboard flows. `sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv S3/G/O/l2 S3/G/L2R
  end over cont cont_fx cont_tr flow_l2_end` → **level 2: PASS (6 traces)**, 0 differ; `contcheck.py`
  cont, cont_fx, cont_tr `--fire`, cont2 `--again`, cont_nf `--no-fire`, over `--none` → **PASS all six**.
  The cheat run: level 1, level 2 (F5), both second visits, the level-3 briefing, the game completed
  (463 s), the title (568.6 s; the score under the table: no entry). tx_ex's first run waited at the
  entry (the stages' records had removed `ge_ret_arm`'s breakpoint) until RETURN was pressed by hand;
  `np_t_poll` arms it after them since, and tx_f1, tx_tr and the re-run below went through alone.
- **After the rebase** (S3/b3, on `d44821d`): `e1`, `e2` (endcheck PASS), `tx_ex` (the title after the
  ending against the base's: the picture, registers, palette identical, titlecmp2 PASS), `cont` (0
  differ, contcheck PASS), endsim PASS (`S3/tools/g3.tcl`).
- **The guard**: the product's first 1 MiB alone (`head -c 1048576`) on a fresh Expert: "ROBOCOP 2 needs
  a 2 MB Konami SCC cartridge or MegaRAM. If yours is one, reset the MSX." (VRAM's name table).
- **The matrix**: `python3 -I tools/msxmatrix.py S3/G/R/prod/rc2.rom --labels S3/G/R/prod/rc2.labels
  --home <msx-ai>/.openmsx-home --jobs 1` → **10 of 10 PASS**.
- **make test** → 331 tests, the 4 known failures only (failures=3, errors=1, skipped=56).

### Open issues
1. **Level 3's agents**: take `fb_brief2`'s call of `fr_ending` out (`frontx.asm`: the `$8050` = 2 test)
   when level 3 follows the level-3 briefing, and call `fr_ending` from level 3's end (`$8050` = 3: no
   statistics, no stages), then `ml_ttl`. `docs/LEVEL3.md` default 13 (an A000h-only block in bank 127)
   now meets `BANK_FRONT2` there: the next such bank is 191.
2. The user's choices: the WELL DONE screen kept on while CMP plays and the table screen after an entry
   (`../ENDING.md` defaults 2 and 3), the OPLL's HH and TCY drums (default 9), the CMP speech left silent.
3. Not run (their code banks byte-identical to the base's): the regress families final, drives,
   range, display and sound, the stills and field checks, the 55 option sets. The tx jobs take about
   120 s more emulated time (the ending).

### Integrated
Cherry-picked onto `level2` `d44821d` (the main tree clean) as **`af87f56`** (the code), **`5ca5870`** (the
docs) and **`b7ad1d3`** (this section); the tree equal to `g-s03`'s. In the main tree then:
`build/msx/end.bin` (`$PY -I tools/msxtune.py --end --out build/msx --cache build/music`) and
`ending.inc` with `text_end`, `text_hisc`, `text_best` (`tools/msxtext.py`, the Makefile's line) made with
the integrated tools, both byte-identical to the worktree's; the product, `e1`, `e2` and the `l2c` build
(`tools/bstest/build.sh`) byte-identical to the worktree's (the product `4ffbd9695dff6907`), so every
result above holds; `make test`: 339 tests, the 4 known failures only. The summaries, notes, pictures
looked at and the scratch scripts in `build/archive/rest_step3_records_2026-11-01.tar.gz`; the ending's
tune previews (`end_amiga.wav`, `end_scc.wav`, `end_fm.wav`, `end_psg.wav`, `end_sccfm.wav`,
`end_fx_*.wav`) in `build/music/preview`; the big records deleted.
