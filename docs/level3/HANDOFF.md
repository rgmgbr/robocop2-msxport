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

## Step 4 (plan step A): level 3 in the ROM, the flow and the bench (2026-11-01)

**Done.** Worktree `g/wt04`, branch `g-s04`, rebased onto `level2` `d0985a4` (steps 1 and 3 in);
scratch `S=$SCRATCH/g/s04`. The plan: `docs/LEVEL3.md` step A; as built: its new section 3.9.

### What it did
- **The ROM** (`tools/mkrom.py`): `L3` and `L3B` in `STAGES` after `FRONT2`; level 3's tiles, map,
  attributes and tables after the ending's sound, laid out by `place_banks` (a bank with `(b & 3Fh) =
  3Fh` takes `BANK_L3` or `BANK_L3B`, both read at A000h only, else padding): the product is **146 of
  256 banks** (2 MiB, the boot guard): tiles 132-139, map 140-141, attributes 142, tables 143,
  `BANK_L3` 144, `BANK_L3B` 145. Its tables bank holds OTILE, ATR2, a BOBHASH of level 2's frames whose
  bytes level 3's memory holds too (`l3_stub_hash`), the graded palette (`level3_grade.pal`, the same
  bytes as level 2's) and its `view_offy`. `lv_desc3` and `lv_fid0` (`LV_SIZE` 33) in `gen/levels.inc`;
  `gen/lvshared_l3.asm`; `mapcells.py --level 3` in every build; `LV_TEST=3`.
- **The level's banks**: `msx/level3.asm` (`BANK_L3`: the header, `lvshared_l3`, `l3_init` with
  `level_init`'s level-3 part, `lt2` (the beams, `level_tick_2` `$9436`), `l3_noten`, the three deaths
  with `debris_add`, 19 stubs into `BANK_L3B`, the tables) and `msx/level3obj.asm` (`BANK_L3B`: the 19
  types, each a stub that frees its slot), through `rc2.asm` `l3b_call`.
- **The flow**: `ml_ev` sends AG `$8050` = 3 into step 3's ending (`ml_end`: `frontx.asm` `fr_ending`,
  then the title), 1 and 2 through the statistics, the stages and the briefing into `lv_next`; step 3's
  interim `fb_brief2` is removed (`front_bonus` calls `front_brief` again; `docs/ENDING.md` and
  `docs/MSX_ARCHITECTURE.md` say so). `front_l2test` (= `front_l3test`) sets AG `$8050` = `LV_TEST` - 1.
- **The fade's state** (`$F89D`): `fade_st` (DD1Ch), 10 from `ng_init`, 11 from `l3_init`; `pl_fade`
  reads it (the same bytes in the fixed area).
- **RAM** (`msx/msx.inc`): `fade_st` DD1Ch; level 3's code-area words DD74h-DD7Fh (`obj22_x`, `obj37_last`,
  `l3_mail` (6), `obj22_step`, `obj40_flag`); `lv_fid0` F1C0h; `fc_tab` ECF0h-ED0Fh (32 B) for step C's
  frame cache. Level 3's lists: spawn DD80h-DFA3h, objects EE00h-EEB5h, lifts E900h-E92Fh.
- **The bench and the harness**: `tools/l3drives.py` (`tour3`, `beam`; `cont3`'s drive only),
  `tools/bstest/l3stub.py` (the stubbed references), `analysis/amiga_ram_l3.tsv` (778 fields),
  `analysis/amiga_tables.tsv` banks `l3` and `l3b` (`tools/amitab.py`: `at_l3b.inc` always written),
  `tools/mapcells.py --level 3` (the beams' 80 cells, the turrets' 36 from the spawn list, the map
  objects': 216 of 2 x 255), `hz.tcl` `hz_l3`, `hz_l3_still_jobs`, `hz.sh l3builds` and `compare
  --fields analysis/amiga_ram_l3.tsv`, `openmsx_rc2.tcl` unchanged (`rc2_l2_arm` arms at the next
  `lv_next`: armed in level 2 it traces level 3), `cheat.tcl` through level 3 to the ending, `np.tcl`
  `np_t_l2` ends level 3 at its first tick (the gate's `tx` flows reach the ending as before),
  `romdiff.py` (the `L3_` blocks), `tools/msxframe.py` (level 3: 160 slots, level 2's pool frames),
  `variants.sh` (six `LV_TEST=3` sets), the Makefile's level-3 conversions; `docs/HARNESS.md` 5.26.

### Commits
- On `g-s04` (rebased onto `d0985a4`): `acfe7d2` (level 3 in the ROM: the banks, the flow, `msx.inc`,
  `mkrom.py`, `mapcells.py`, the tables) and `7145596` (the deaths, the bench, the harness, the docs).
- Integrated into `level2` (clean tree, from `d0985a4`) by cherry-pick as **`69c9081`, `74c4554`**. In
  the main tree then: level 3's conversions made (`build/msx/level3.*`, byte-identical to the
  worktree's); the product (`e1fa3562861d8fc1`) and the `l3` trace build (`75fb186fa03b8c93`)
  byte-identical to the worktree's; `l3drives.py refs` (both references at their sha256), `l3stub.py`
  (byte-identical to the worktree's), `hz_l3 ... tr` and `hz.sh compare --fields
  analysis/amiga_ram_l3.tsv`: "level 3: PASS (4 traces)"; `make test`: 339 tests, the 4 known failures
  only. The level-1 and level-2 traces above ran on builds made before the deaths were added: those
  differ from the final ones in `BANK_L3` alone (`romdiff.py`: bank 144, 1,808 bytes), which levels 1
  and 2 never map. The small records in `build/archive/level3_stepA_records_2026-11-01.tar.gz`.

### Checks (each with its command and result)
- The conversions: `python3 -I tools/msxlvpal.py palette build/extracted/files/DATAL3_22.bin --pal-file
  build/extracted/boot/main_8000.bin --base-addr 0xfff6 --pal-addr 0x10036 --base build/msx/robocop
  --rows 50 -o build/msx/level3` (mean dE76 C 2.179, A 2.675; `level3.pal` = `level2.pal`) and
  `python3 -I tools/msxconv.py level ... --rows 50 --joint build/msx/level3 -o build/msx/level3` (505
  tiles); `python3 -I tools/mapcells.py build/ram/level3_full.bin analysis/amiga_tables.tsv
  build/msx/level3.atrp 160 50 --level 3` -> 216 cells (121 even rows, 95 odd; 255 a pool), 6 attribute
  values, 10 codes free; levels 1 and 2 unchanged (438 and 289 cells).
- The builds: `sh tools/bstest/build.sh $S/R/prod/rc2.rom` -> 2048 KiB, 146 banks, mkrom's checks (the
  3Fh rule, the SCC test values, the guard's tag, the late sections at their banks, lvshared's copies at
  level 1's addresses) passed; 12 known z80asm warnings. `sh tools/bstest/variants.sh $S/var` -> 58 of
  61 sets build, the three known fixed-area overflows (`demoact`, `demoact5`, `demohud`, as at the base);
  the `DIAG` sets pad banks 126-127 (no tunes: level 3 from bank 120).
- Free bytes (`python3 -I tools/bstest/l2base.py banks $S`, against `d0985a4` built by `SRC=` from a
  detached worktree): fixed area 156 (base 174: `ml_ev` +1, `ml_end` 3, `l3b_call` 14), 21 in the lowest
  set `DIAG=1 PZ_TEST=1` (base 39); LC1 54, LC2 4,842, `BANK_L1` 874, LC3 4,866, INPUT 11 (all as the
  base); FRONT 1,143 (base 1,173: `lv_desc3`, `lv_fid0` x 2, `ng_init`'s 6 B, `fb_brief2` gone); FIELD
  150, MUSIC 1,251, PUZL 4,483, FRNG 264, `BANK_L2` 28, `BANK_FRONT2` 7,041 (as the base); **`BANK_L3`
  3,913**, **`BANK_L3B` 8,045**.
- The data blocks: `python3 -I tools/bstest/romdiff.py --blocks $S/base/R/prod/rc2.rom
  $S/R/prod/rc2.rom` -> 28 blocks identical at their banks, the six `L3_`/`BANK_L3*` blocks new, "romdiff:
  PASS"; `python3 -I tools/bstest/relocheck.py ... 2 3 4 5 6 8 9 BANK_PUZL BANK_FRNG BANK_L2
  BANK_FRONT2` -> every differing byte a relocated label word ("relocheck: PASS"; banks 0-1 and FRONT
  hold the step's code).
- Level 1: `sh tools/bstest/hz.sh trace $S/R/trace`, `hz_regress` (cov1 4,401 rows on C-BIOS_MSX2,
  cov0 1,400 on the FS-A1FX and the FS-A1GT), `sh tools/bstest/hz.sh compare $S/R/trace` -> 948 fields,
  0 differ in all three, "regression: PASS".
- Level 2: `sh tools/bstest/hz.sh l2builds $S/R`, `hz_l2 {$S/O/l2} {$S/R} tr`, `sh tools/bstest/hz.sh
  compare --fields analysis/amiga_ram_l2.tsv $S/O/l2 $S/R` -> the 23 traces 0 differ in 1,022 fields
  (`flow_l2_end`, the continues on three machines included), the lost counters 0: "level 2: PASS (23
  traces)".
- Level 3's references: `python3 -I tools/l3drives.py make`, `refs` (`tour3` 1,401 rows sha256
  `27fc3e0241c53f5a`, `beam` 501 rows `9c293cd6431fb211`; `check`: 2 of 2); `python3 -I
  tools/bstest/l3stub.py $S/stub` (the stubbed ones; with or without the deaths' stubs byte-identical:
  no such death in them).
- Level 3's traces: `sh tools/bstest/hz.sh l3builds $S/R`, `hz_l3 {$S/O/l3} {$S/R} tr`, `sh
  tools/bstest/hz.sh compare --fields analysis/amiga_ram_l3.tsv $S/O/l3 $S/R --refs $S/stub` -> `tour3`
  (C-BIOS_MSX2, FS-A1FX, FS-A1GT) 1,401 rows and `beam` 501 rows, **0 differ in 778 fields**, lost
  counters 0, the pools 58/54 of 255: "level 3: PASS (4 traces)". Against the plain reference
  (`tracecmp.py --ram --fields analysis/amiga_ram_l3.tsv ... build/emu/l3_tour3_ram.jsonl`) every row
  differs from row 0: `act_20` (unported) runs in `level_init`'s map-object pass before row 0 (the map
  objects' collision slot 1: `mslot1_x` B7h/617h), the stubbed types from row 2 (type 39's slot, type
  47's `cam_mode`): the first frame of an unported routine is row 0, as level 2's step 7 found.
- Level 3's start: `hz_l3_still_jobs {$S/O/st} {$S/R} {0 50 230 400 600 1110}` -> on the three machines
  RoboCop at (1184, 784), `lv_cur`'s logic bank `BANK_L3` (144), game frame 0; `$PY -I tools/msxframe.py
  $S/O/st/M/g0000 build/msx/level3 build/msx/hud OUT.png --sprites build/msx/sprites --level 3 --field`
  -> **the first picture 0 differ** (52,126-52,936 pixels) on C-BIOS_MSX2, the FS-A1FX and the FS-A1GT
  (looked at: the street, the fence and the skyline, the HUD at 07:30); game frames 50 and 1,110 (the
  roof) 0 differ with RoboCop's sprite pixels exact; 230, 400 (the beams) and 600 (lift L0) differ at
  the beams' cells only (their looks change every tick, the RAM's patches a tick ahead of the picture:
  step C's field check judges them). msxreal.py needs a rendered screenshot, which the headless MCP
  cannot make: msxframe's render stands for it, as for level 2's start.
- The flow: `hz_chain [list [ch_job {$S/O/cheat} {$S/R/cheat/rc2.rom} {$S/R/cheat/rc2.labels}
  Gradiente_Expert20_64K]]` (`CHEAT=1 TAG=7`, a fresh Expert): the title, level 1, F5, the stages, the
  level-2 briefing, level 2, F5, the statistics, both second visits, the level-3 briefing, **level 3**
  (frame 100 at emulated 469.0 s), F5, **the game completed** (`front_ending` at 470.3 s), the name
  entry (RETURN), the table, the title (593.5 s): "end: the title after level 3"; level 3's frame-100
  snapshot rendered (msxframe, the product: 0 differ, looked at).
- `make test` (the worktree, rebased): 339 tests, the 4 known failures only (failures=3, errors=1).

### For step B (the logic) first
- Fill `msx/level3obj.asm`: replace the shared stub (`t21` ... `t52`: `ld a,0xFF` / `ret`) by each type's
  port; its tables go into `analysis/amiga_tables.tsv` bank `l3b` (`at_l3b.inc`, already included; the
  turrets' looks `tur_panel`, `tur40_look`, `tur41_look` are there). While a handler runs, BANK_L3 is not
  mapped: `lvshared_l3`'s `t_xy`, `t_face`, `t_col`, `t_word` need copies in `BANK_L3B` (as needed); the
  fixed code and LC1 are reachable. Level 2's type-49 flight (`level2obj.asm` `t49`, `fly_dx`, `fly_dy`,
  `fly_gfx` in bank `l2`) is not in `BANK_L3B`: type 38 needs its own copy.
- Drop each ported type's stub from `tools/bstest/l3stub.py`'s `STUBS` (and `act_20` once `mapobj.asm`
  has it at `ao_acts` entry 8); the deaths need no stub (ported here, untested: the kill drives check
  them). Enable `$D583` and `$E9F5` in `analysis/amiga_ram_l3.tsv` once `obj22_step` and `obj40_flag`
  hold the Amiga's bytes (the image's 3 and 42h: AC_VARS is 0 at power-on) or the comparison learns
  their encoding.
- `msx/hits.asm` `phb_en`: bullet 11h (the rocket of types 40 and 42, 40h) x 1 (default 11); the touches
  of 38, 39 and 52 (18h) x 1 in their own code (default 12).
- The drives the plan asks (`park`, `boss`, `kill`, `cont3`'s reference) into `tools/l3drives.py`
  (`cont3`: the bench faults after its game over, PC `$FDB8`, A1 800000h, bench frame 735), the jobs
  into `hz_l3_jobs` and `hz.sh`'s level-3 `JOBS`.
- The two-part lift (`special.asm`, `$8ED2`) and `act_20` (`mapobj.asm`).

### For step C (the sprites and the play field) first
- Level 3's descriptor (`tools/mkrom.py`, the `lv_desc3` lines of `gen/levels.inc`) takes level 2's BOB
  index (`SPR_BOB_INDEX_L2`), spark, play-field tables (`fld_l2`), ids (`FIELD_ID0_l2`, `lv_fid0`) and
  atlas (`L3_ATLAS` = `L2_ATLAS`, no bank of its own); its BOBHASH is `l3_stub_hash`'s. Replace them with
  the pool's level-3 values (`SPR_BOB_INDEX_L3`, `fld_l3`, the per-level `lv_fid0`), level 3's own atlas
  block (a new entry in `place_banks`' data list: it lays out the banks), and the BOBHASH from the pool;
  `L3_DYN_Y` (232) and `TC_SLOTS[3]` (160) are the plan's.
- `bob.asm` reads `lv_fid0` (F1C0h, `LV_SIZE` 33: the field is in every descriptor, D0h today); the
  frame cache's RAM `fc_tab` (ECF0h, 32 B) is reserved in `msx.inc`; `tools/msxframe.py`'s
  `POOL_LEVEL = {3: 2}` goes once the pool has level 3.

### Open issues
- `cont3`'s reference: the bench faults after level 3's game over (above): step D (`contcheck.py
  --level 3`).
- The `flow_l3` reference (the bench through level 2's end into level 3) is not built: the flow is
  checked by `cheat.tcl` (above); `amigaemu.py --flow` through `load_level2` is step D's if needed.
- Only `tour3` and `beam` exist; the plan's `park`, `boss` and `kill` need the car park's and Cain's
  logic (step B).

## Step 5 (plan step C): the sprites and the play field (2026-11-01)

**Done, with one open issue for step D** (big moving play-field enemies tear: below). Worktree `g/wt05`,
branch `g-s05` from `level2` `d0985a4`, rebased onto `bc3ad83` (step 4 in); scratch `S5` =
`$SCRATCH/g/s05`. One openMSX: a private MSX-AI MCP session (`tools/bstest/mcpd.py S5/mcp`, `mx.sh`).
The plan: `docs/LEVEL3.md` step C; as built: its new section 3.10.

### What it did
- **Default 9**: `vats.asm` (in `level2.asm`), `field.asm`'s vat section past `vat_init` and `tiles.asm`'s
  `vat_win` / `vat_idle` only in `VAT_ANIM=1` builds (the product: stubs; `vatlog.tcl` logs the clock and
  the guard alone on a build without `vat_run`). Product: the fixed area +31 B, `BANK_FIELD` +958 B,
  `BANK_L2` +1,401 B.
- **The catalogue** (`tools/bobcatalog.py level3`, REA on `level3_full.bin`): 212 frames, the bench's
  202 (`build/emu/cov_level3.json` and `l3_frames_drawn.json`, copied from step 2's scratch; all in it,
  only `$6BB80` not explained by the tables) and 10 from the draw code's tables (`L3_HARD`, Cain's
  `$D7EE`/`$D80E`/`$D79A`/`$D7CA`, type 21's `$D44C`, the truck's, types 34-39's, 50-52's, the lift's,
  types 4 and 12's), the bullets level 3 fires (`L3_BULLETS`), its explosions (`L3_EXPL`), its pickups.
- **The pool** (`tools/msxsprites.py --l3-bobs --l3-ram --l3-pal --l3-remove`, the Makefile): level 3's
  150 ids after level 2's (82 new records, level 1's 60 and level 2's 4 where those memories hold the same
  bytes, the spark's 4), the pool 28 banks (27); its play field: 66 frames from `lv_fid0` 98h, 18 in
  its atlas (109 lines, two banks), 42 big ones and 55 white copies (colour 9) in the frame cache's ROM
  (14 banks, the header in the first), the smoke in level 1's dynamic frames; `msx/level3_frames.json`
  (empty: default 14); `tools/msxchooser.py` a level-3 section (120 cards).
- **The engine**: `field.asm` per-level tables (`fld_l1/2/3`: `field_dyn`, the white mark, the cache's
  bank; `fb_init` copies 11 bytes to 064Fh-0659h and empties the cache), `fb_wants` (the white mark kept
  in level 3), `fbb_fc`, `fc_find`, `fc_get` (the frame cache, `fc_res` ECF0h, seven fixed places on page
  2 lines 160-231); `bob.asm` (`lv_fid0`, level 3's bullets with a play-field frame to the play field,
  `fb_add`'s BM_FLASH mark). `mkrom.py`: level 3's BOBHASH (`l3_hash`), atlas, frame cache and
  descriptor (its index, spark, `fld_l3`, ids); every late block by `place_banks` (163 of 256 banks:
  `BANK_FRONT2` stays on 127). `cold.asm` needed nothing: `lv_select` uploads `lv_fimg`'s atlas, now
  level 3's own.
- **The harness**: `tools/bstest/l3field.tcl` (`lf_jobs`: scripted enemies of level 3's frames appended to
  each tick's play-field list, the field check's records, the cache's copies counted; `lf_start_jobs`),
  `l3poses.py`, `fieldcheck.py --level 3`, `msxframe.py` (`FieldLooks(3)`, `POOL_LEVEL` dropped),
  `romdiff.py` (`L3_FC`), harness marks `ml_fbn`, `fcg_ld`, `fcg_dn` (no bytes); `docs/HARNESS.md` 5.27;
  `tests/test_level3_field.py` (8 tests).

### Commits
`a2fbaab` (default 9), `b87d778` (the catalogue), `6e796df` (the pool, the engine, mkrom, the Makefile),
`a2ec1e4` (the harness, fieldcheck, msxframe, the chooser), `37952b4` (the tests, `lf_start_jobs`), and
this section's (with `docs/LEVEL3.md` 3.10 and `docs/HARNESS.md` 5.27).

### Checks (each with its command and result; `W` = the worktree, `PY` the venv's Python)
- **Builds**: `sh S5/tools/mkb.sh W S5/fin "prod" "l3 EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=3" "low
  DIAG=1 PZ_TEST=1" "anim VAT_ANIM=1"`: all build, the 12 known z80asm warnings only; the product
  `3f9e446fac3bb45a` (2 MiB, 163 of 256 banks, the guard), l3 `72686ab18a50937c`. `sh
  tools/bstest/variants.sh S5/V`: **58 of 61** (the three known fixed-area overflows: `DEMO_ACTORS` 2 and
  5 -F3h, `DEMO_HUD` -3Ah). Free bytes (`l2base.py banks`): the fixed area **164** (product), **29**
  (`DIAG=1 PZ_TEST=1`, the lowest), `BANK_FIELD` **300**, `BANK_L2` 1,429, FRONT 1,143, `BANK_L3` 3,913,
  `BANK_L3B` 8,045; `VAT_ANIM=1`: fixed 118, FIELD 99 (level 3's play field left out there).
- **The pool**: `python3 -I tools/bstest/pooldiff.py OLD/sprites build/msx/sprites` (OLD: step 4's pool): every
  index entry of RoboCop (294), level 1 (198) and level 2 (204) resolves to the same record bytes,
  patterns and colour rows: **PASS**; level 1's and level 2's `sprites_l*` files byte-identical.
- **romdiff** against step 4's product (`bc3ad83`, built from the main tree): `python3 -I
  tools/bstest/romdiff.py --blocks BASE.rom S5/b2/prod/rc2.rom`: **31 data blocks identical** at their
  new banks; differ as meant: the pool (`SPR_BASE_BANK`, 27 -> 28 banks: pooldiff above) and `L3_TAB`
  (level 3's own BOBHASH); new `L3_ATLAS`, `L3_FC`. `relocheck.py ... BANK_LC1 BANK_LC2 BANK_L1 BANK_LC3
  BANK_INPUT BANK_MUSIC BANK_PUZL BANK_FRNG BANK_FRONT2 BANK_L3`: relocated label words and bank
  operands only; FRONT besides them level 3's descriptor (`lv_sidx`, `lv_spark`, `lv_fld`, `lv_fid0`: 6
  bytes); `BANK_L2` besides them the removed `vats.asm` and 16 label-plus-constant operands of `l2_hdr`
  and `mk_tab2` (moved by it); FIXED and FIELD: this step's code.
- **Levels 1 and 2 unchanged** (step 4's builds against these, `S5/tools/ab.tcl`, 14 jobs): the
  `LOCKSTEP=24` records, `python3 -I tools/dispcmp.py BASE/disp_M.txt NEW/disp_M.txt`: **2,998 lists, 0
  differ** on C-BIOS_MSX2 and the FS-A1FX; level 1's stills (`l2b_sl_setup`, game frames 100, 430,
  860, 1490, 2400, two machines): `tools/msxframe.py --level 1 --field` the same verdicts on base and new
  in all 10 (the known classes: 18, 31, 260, 6 px), 9 of them with VRAM and registers byte-identical;
  level 2's stills (`hz_l2_still_jobs`, `l2_tour`, frames 0 to 2000, three machines): `msxframe.py
  --level 2 --field` 0 play-field pixels differ in 23 of 24 on both, the FS-A1FX's g1600 8 px on both,
  every sprite pixel exact.
- **Check 2** (`hz_l3_still_jobs S5/st S5/R {0 50 300 700}`; `$PY -I tools/msxframe.py SNAP
  build/msx/level3 build/msx/hud OUT.png --sprites build/msx/sprites --level 3 --field`): the start
  picture (g0000, RoboCop at (1184, 784)) **exact on the three machines**; 11 of 12 stills exact, the
  MSX2's g0300 796 px at the beams (step 4's known class); level 3's sprite BOBs (type 4's) exact.
- **Check 3** on the windows step 4's stubs reach (`lf_jobs` with `poses_none.tcl`, `tour3` from frame 2,
  700 pictures, and from 600, 500 pictures; `$PY -I tools/bstest/fieldcheck.py DIR build/msx/level3 OUT
  --level 3`): **0 differ on the three machines** (the beams' cells not checked).
- **Checks 4 and 5** (`lf_start_jobs S5/sc/plain S5/R 42`): guard reg 0, pal 0, cmd 2 / 0 / 0, cpu 0,
  vbl 0, tear 0; patcheck 0 bad; satcheck the first frame only; lost 0; **sprlines 395 / 317 / 299
  frames, all the known class** (RoboCop beside type 4 drawn as legs and torso, level 1's records: no new
  class).
- **The frame cache** (no level-3 enemy draws yet: `lf_jobs` injects them; `python3 -I
  tools/bstest/l3poses.py`; `set ::lf_mul 8; set ::lf_dx 0`, `l3_still`'s idle drive, 1,100 pictures a
  machine, the six phases in 360 ticks): its frames and places are right in every picture checked on
  both VDPs (looked at: Cain's legs, his 64 x 32 part, type 21's legs and torso, the white copies of
  Cain, the truck and type 51 on the MSX2, the MSX2+ and the turbo R; `S5/lf3/m2_four.png`). Copies
  (`fc.txt`): 49 / 60 / 71 in 350-400 ticks, 13-21 ms each (the turbo R's as slow: the VDP's access).
  The field check's differences (`fieldcheck.py ... --level 3`, per phase `S5/tools/phases.py`):
  MSX2 32 of 1,100 pictures, MSX2+ 59, turbo R 51, all of the "hostage tear" class (part of the
  enemy a picture ahead) but 18 on the MSX2; per phase (MSX2+): Cain 37 of 268 pictures, type 21 10 of
  170, the truck 2 of 172, type 51 0 of 148, type 35 with the rocket 0 of 157, the two legs side by side
  10 of 185. The same counts with `FB_HOLD` 60 (a test build): not the hold. With the enemy walking 2 px
  a tick and animating every tick (`lf_mul` 1): 92 / 51 / 57 of 450. Under the guard (`lf_start_jobs ...
  poses60.tcl`): reg 184-289, cmd 332-679, tear 6 / 10 / 43, vbl 0 / 20 / 1 (lists applied late: the
  split interrupt waits for long copy chains).
- **make test** (the worktree): 347 tests, **the 4 known failures only**.

### What step D must know about the frame cache and the play field
- A big enemy's frames reach the screen right: the cache loads a frame into its place when a piece is
  composed with it (13-21 ms of CPU, the main loop stopped meanwhile: Cain's walk loads a legs frame
  every other tick); a white copy for each hit flash of a play-field frame. Frames shown together never
  share a place, so they are loaded once; two different leg frames on screen at once (a type 21's debris
  beside a new type 21) share place 0 and are loaded again for each piece (right, slow).
- **The tear**: an item of more than one 64 x 64 piece on the page shown is copied in pieces of about
  13 ms each (`fb_mayq`'s 6.3 us a byte), which no blank holds; the V9958 has one page, so Cain (64 x
  ~80, three play-field parts) and type 21 show partly old, partly new frames in about 5-14 % of the
  pictures while they move or animate (the stress test above; the real logic will tell). Options:
  copies racing the beam top-down only when they keep ahead (`fb_fits` for chains), smaller items (the
  changed rectangle only), or on the V9938 composing big items on the hidden page and flipping. The
  user's choice may be needed (decision 13's play field against sprites).
- `fb_add` marks every BM_FLASH record (bit 7); levels 1-2 drop the mark in `fb_wants`. A play-field
  frame without a white copy (the lift, the rocket, the smoke, a debris part) shows its normal look.
- Level 3's enemy bullets whose frame is a play-field frame are drawn into the play field (the debris
  of `death_cain`, `death_truck`, `death_w21`; the rocket, bullet 11h, 48 x 16).

### Open issues
1. The tear above (step D: the boss fight's look; possibly the user's choice).
2. `VAT_ANIM=1` builds leave level 3's play field out (no room in `BANK_FIELD`): they serve level 2's
   comparison only.
3. The lowest option set has 29 B of the fixed area.
4. The `park`, `boss` and `kill` windows (checks 3-5 there) wait for step B's logic: `lf_jobs` and
   `fieldcheck.py --level 3` take them as they are.

### Integrated
Cherry-picked onto `level2` `bc3ad83` (the main tree clean) as **`cc67408`** (default 9), **`69c5bbe`** (the
catalogue), **`416bb42`** (the pool, the engine, mkrom), **`0acd381`** (the harness), **`618f2f4`** (the
tests), **`9f51b90`** (the docs) and this note's. In the main tree then: `build/emu/cov_level3.json` and
`l3_frames_drawn.json` (step 2's coverage), `build/sprites/catalog_l3.json` (`bobcatalog.py level3`) and
the pool (the Makefile's `msxsprites.py` line) made with the integrated tools, byte-identical to the
worktree's; the product, the l3 trace build, the lowest set and `VAT_ANIM=1` built from the main tree
(`tools/bstest/build.sh`) byte-identical to the worktree's (the product `3f9e446fac3bb45a`), so every
result above holds; `make test`: 347 tests, the 4 known failures only. The summaries, the scratch tools
and the pictures looked at: `build/archive/rest_step5_records_2026-11-01.tar.gz`; the big records deleted.

## Step 6 (plan step B): the logic (2026-11-01)

**Done.** Worktree `g/wt06`, branch `g-s06`, rebased onto `level2` `a80288d` (step 5 in); scratch
`S=$SCRATCH/g/s06`. The plan: `docs/LEVEL3.md` step B; as built: its new section 3.11.

### What it did
- **The types** (`msx/level3obj.asm`, `BANK_L3B`): 21, 22 (Cain), 33-43, 46, 47, 48, 50, 51 and 52 ported
  from step 2's REA exports (`S2/asm`, the Ghidra provider) instruction by instruction, with `obj_push`
  (`$EF18`), the turrets' map writes (`$EAA6`, `$EA50`, `$EBB8`), type 38's flight (level 2's `t49` copied),
  the bank's own helpers; their tables in bank `l3b` of `analysis/amiga_tables.tsv` (19 rows).
- **The patched bytes**: `obj22_step` = `$D583` XOR 3, `obj40_flag` = `$E9F5` XOR 42h; `tools/tracecmp.py`'s
  field option `xor=`, both fields enabled in `analysis/amiga_ram_l3.tsv` (780 fields).
- **The D1 Cain reads** (found here): `update_objects` hands each handler the slot before's D1 and type 22
  tests it (`$D53A`: sound 0Eh). The port keeps it in `uo_d1`: every level-3 handler leaves its last D1
  there (`l3_tail` after a last BOB: draw_bob's shift ror 4 | 0FCAh, or y - camera y when out; `$B0A`'s
  nibble is ~camera x & 15, so the shift is (x + 1) & 15), types 4 and 12 and the deaths through
  `level3.asm`'s `t4_w`, `t12_w`, `d3_c31e`, `d3_c35a` (the deaths' last explosion's y too); slot 0's is
  `read_joystick`'s (negative).
- `msx/mapobj.asm` `act_20` (`ao_acts` entry 8), `msx/special.asm` `spl_two` (the lift's two parts when AG
  `$8050` = 2), `msx/hits.asm` the rocket (bullet 11h) x 1 (default 11); types 38, 39, 52's 18h x 1 (12).
- **The drives** (`tools/l3drives.py`): `park`, `boss`, `kill` (a natural kill: Cain followed down through
  act_20's three floor pieces, shot on the ground floor; energy and lives poked, no god mode) and `cont3`'s
  reference; `hz.tcl` `hz_l3_jobs` (16 jobs), `hz.sh` (the `l3c` build, the level-3 `JOBS`).
- **cont3's bench fault**: its drive's fire came after the game frames stop at the death's end (row 149):
  the offer went unanswered, the title came, and the title's text plot (`$11062` through `$725A2`) wrote
  80h into chip RAM's mirror of the message slots (`$10FD9F` = `$FD9F`), whose ticker then read a string at
  `$800000`, unmapped on the bench (open bus on an A500). Fire now at 140-159. Then the continue's one
  difference, the palette flash's countdown (`$F826`, 2 against 4 after the continue): the original takes
  two `pl_fade` steps between the death's end and the continued game (`$82A8`'s `$FEDA`, `$FEFC`; the
  continue's text `$10768`, `$1080C`), the port none: `msx/front.asm` `fo_flash` at `front_over`'s start and
  at `front_cont`'s text (both levels; level 2's countdown is idle there, its traces unchanged).
- `tools/mapcells.py --level 3`: type 36's shafts (the 22 cells of 2D00h that `t36_w` holds as constants)
  checked against the map and every writer. `analysis/main_8000.sym` (`text_plot` `$11062`, `$D53A`, `$B0A`)
  and the seeds. `tests/test_level2_rom.py`: the damage rule with the rocket and the touches.

### Commits
- On `g-s06` (rebased onto `a80288d`): `163d065` (the types, act_20, the lift, the rocket, xor=), `bedd287`
  (park, boss, kill and their jobs), `df6b7ab` (cont3: the drive, `fo_flash`, the l3c build and jobs),
  `09e4fd3` (the findings, mapcells' shafts), `92a6106` (LEVEL3.md 3.11, HARNESS.md 5.28, the test), and
  this note's.

### Checks (each with its command and result; `R` = `$S/R2`, `PY` the venv's Python)
- The builds: `sh tools/bstest/hz.sh l3builds $S/R2` (l3 `e5841d12d0689e79`, l3c `89ba0ac2d0384657`), the
  product `sh tools/bstest/build.sh $S/R2/prod/rc2.rom` (`fb06ae0faab13802`: 2 MiB, level 3's code in bank
  161, its types in 162), the lowest set `DIAG=1 PZ_TEST=1` (`ca449cce9180c21e`): mkrom's checks passed, the
  12 known z80asm warnings only.
- Free bytes (`python3 -I tools/bstest/l2base.py banks $S/R2`): fixed area 164 in the product, 29 in the
  lowest set (as step 5 left them: this step adds nothing there); LC1 50 (- 4: the rocket), LC2 4,827 (- 15:
  `act_20`), LC3 4,794 (- 72: the lift), FRONT 1,119 (- 24: `fo_flash`; the lowest set 721), `BANK_L3` 3,867
  (- 46: the wrappers), **`BANK_L3B` 2,383** (5,662 used).
- The references: `python3 -I tools/l3drives.py refs park boss kill cont3` then `check`: "references: 6 of
  6 as expected" (`park` 1,201 rows `6614e02d98a2f6b5`, `boss` 1,401 `6454a63800dea384`, `kill` 1,861
  `83ff8fd40281d2af`, `cont3` 401 `094defd80670fc84`; `tour3`, `beam` as at step A). `l3stub.py` has no stub
  left: the plain references are compared.
- **Level 3's traces** (private MCP session `tools/bstest/mcpd.py $S/mcp`, `mx.sh`): `hz_chain [hz_l3_jobs
  {$S/O5} {$S/R2} tr] MARK`, then `sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l3.tsv $S/O5
  $S/R2` -> **"level 3: PASS (16 traces)"**: `tour3`, `park`, `boss`, `kill`, `cont3` each on C-BIOS_MSX2, the
  FS-A1FX and the FS-A1GT, and `beam`, every row 0 differ in 780 fields (kill to the level's end, row 1860;
  cont3 through the continue at row 150), lost counters 0 (pools at most 66/60 of 255).
- Level 1: `sh tools/bstest/hz.sh trace $S/R2/trace`, `hz_regress ... tr`, `sh tools/bstest/hz.sh compare
  $S/R2/trace` -> cov1 4,401 rows, cov0 and cov0_tr 1,400, 948 fields 0 differ: "regression: PASS".
- Level 2: `sh tools/bstest/hz.sh l2builds $S/R2`, `hz_chain [hz_l2_jobs {$S/O5/l2} {$S/R2} tr] MARK`, `sh
  tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv $S/O5/l2 $S/R2` -> **"level 2: PASS (23
  traces)"** (1,022 fields, the continues on three machines and `flow_l2_end` included).
- ENEMY_CAP with level 3's types: `build.sh $S/R2/cap/rc2_cap.rom EXTJOY=1 LV_TEST=3` (ENEMY_CAP 1,
  DAMAGE_X 2) on `kill`'s drive, 2,600 ticks: Cain in slot 0 from tick 150, his bombs and missiles (38, 39,
  52: not counted) beside him, his falls through the three pieces (y 56, 255, 416, 578, 719), his death at
  about 1780, the ending and the title; lost counters 0.
- The frames: the bench's `--bobs` log of `tour3`, `park`, `boss` and `kill` draws 178 distinct frames
  (address, BLTSIZE), **all in step 5's catalogue** (`build/sprites/catalog_l3.json`, 212).
- `python3 -I tools/mapcells.py build/ram/level3_full.bin analysis/amiga_tables.tsv build/msx/level3.atrp
  160 50 --level 3` -> 216 cells, "type 36's shafts: 22 cells of 2D00h, as SHAFTS_L3, no writer's".
- `make test`: 347 tests, the 4 known failures only.

### For step D
- **The windows** of the new drives (`build/emu/l3_<drive>.drive`, ticks = rows): `park` 0-1200 (the street
  and the trucks 40-240, floor 35 under the turrets 250-600: rockets from 330, the car park's ground floor
  600-1100); `boss` 0-1400 (the roof 50-260 with Cain from about 125 and his bursts until 425, floor 20
  300-600, act_20's pieces open at about 600, 1000 and 1400, floor 30 625-1000 with the homing missiles,
  floor 40 1025-1400); `kill` 0-1860 (boss's route, the ground floor 1500-1770: Cain hurt from about 1600,
  dead at about 1765, the end count to 1860); `cont3` (the beam's death, the game over at 149, the
  continue, level 3 again from 150). Checks 3-5 (`fieldcheck.py --level 3`, `l3field.tcl`) can run there now.
- The sound (check 6): Cain's 0Eh depends on the D1 above; the traces' `snd_b2c`-`snd_b31` already match
  the bench on all 16 traces.
- The continue: `fo_flash` covers a game over with a credit; the original's high-score entry (`$12082`)
  calls `pl_fade` too (`$12112`, `$121E0`), which a flash running at the death's end of a qualifying score
  would also count down (not traced: no drive reaches it).
- The two-part lift's frames (`$5397C` 743h, `$53BC0` 403h) and the rocket's are drawn by the logic now:
  step 5's catalogue holds them.

### Open issues
- The D1 that Cain reads is emulated where it can come from in level 3; with the joystick locked (`$804D`)
  slot 0's D1 would be `eb_update`'s leftover, which the port takes as negative (no drive reaches it).
- A marker spawn into the slot before Cain's on the frame he runs leaves the original's D1 at the marker's
  y, the port's at 20h + 8 x step (`objects.asm` `uf_mk`): it changes nothing while type 43 (markers off,
  the roof) has run, as in every drive here.

### Integrated
Cherry-picked onto `level2` `a80288d` (the main tree clean) as **`4d742b3`** (the types, act_20, the lift, the
rocket, xor=), **`da4a1e7`** (park, boss, kill), **`bbbf802`** (cont3, `fo_flash`), **`13a155a`** (the
findings, mapcells' shafts), **`ef672f0`** (the docs, the test), **`9bd2de8`** (this section) and this note's.
In the main tree then: `python3 -I tools/l3drives.py refs park boss kill cont3` and `check` ("references: 6
of 6 as expected"); the l3 and l3c trace builds, the product, the lowest set, the level-1 trace build and
the level-2 builds made from the main tree (`tools/bstest/build.sh`, `hz.sh l3builds`, `hz.sh trace`, `hz.sh
l2builds`) byte-identical to the worktree's (the product `fb06ae0faab13802`); `hz_l3_jobs` from the main
tree's harness: "level 3: PASS (16 traces)", lost counters 0; `make test`: 347 tests, the 4 known failures
only. The scratch tools, the BOB logs and the lost counters: `build/archive/level3_stepB_records_2026-11-01.tar.gz`.

## Step 9 (plan step E, its documentation): the docs at 56e8f56 and the option sets (2026-11-01)

**Done.** Worktree `g/wt09`, branch `g-s09` from `level2` 56e8f56; scratch `S9` = `$SCRATCH/g/s09`. No
emulator (steps 7 and 8 held both openMSX instances); REA with the Ghidra provider for the ledger's
evidence. The numbers below are of 56e8f56's builds: steps 7 and 8 change some of them.

### What it did
- **`docs/MSX_ARCHITECTURE.md`**, the engine as it is: the VRAM map and the per-level tables with level
  3 (`fld_l3`, `lv_fid0`); the play field's level-3 part (the frame cache's seven places, `fc_res`,
  `fbb_fc` / `fc_find` / `fc_get`, the white copies and `fb_fwm`, the bullets routed into the play field,
  the known tear); `DAMAGE_X`'s x1 rule with the rocket and the 18h touches; ENEMY_CAP's level-3 types;
  the descriptor (`LV_SIZE` 33, `lv_fid0`, `lv_desc3`); level 2's bank table at 56e8f56 and a new "Level
  3's modules and banks" (`BANK_L3`, `BANK_L3B`, `l3b_call`, the D1 in `uo_d1`, the code-area words,
  `fade_st`, `act_20`, `spl_two`, `place_banks`); the flow into `ml_end`; `fo_flash`; the vats' display code
  only with `VAT_ANIM=1`; the ending's banks; `LV_TEST=3`; the 2 MiB image (163 banks, the 3Fh blocks,
  `rom_guard` in `frontx.asm` through `ci_hook`). The V9958 `draw_kept` fix was already described.
- **`docs/ROM_BUDGET.md`**: a 2026-11-01 update line and summary rows; **2.4** (the bank map from
  mkrom's output, the free bytes of every code bank in the product, `DIAG=1 PZ_TEST=1` and the least of
  the 58 sets, level 3's real cost against 3.3-3.4 and `docs/LEVEL3.md` 3.2, the ending's against
  3.5-3.6), as-built lines in 3.3, 3.5, 3.6; section 7: a table of what became of each limit level 3
  was expected to break.
- **`docs/AMIGA_ANALYSIS.md`**, level 3's section: step 6's three findings (Cain's read of the slot
  before's D1, the `cont3` bench fault with `text_plot`'s code, the palette flash's two countdown steps)
  and what steps 4 and 5 had left out of the ledger (`act_20` before row 0, level 3's explosions and
  bullet frames, the frames the code can draw beyond the bench's, the flash's colour 15), each tagged
  verified or inferred with its evidence.
- **`README.md`** (public): a "Playing" section (the complete game's order, the game over and the
  continue, the controls with the name entry on the keyboard, the sound with the ending's tune), the
  Requirements' 2 MiB line (163 of 256 banks; the rest of the requirements as they were), the sound
  line, `make msx`, `LV_TEST=3`, `DAMAGE_X`'s missiles, `docs/LEVEL3.md` in the list.
- **`docs/LEVEL3.md`**: italic as-built notes where the build changed a design or estimate of sections
  1 and 3.1-3.8 (pointing at 3.9-3.11 and `docs/ROM_BUDGET.md` 2.4); section 6's defaults marked **In**
  (6 as white copies in the ROM, 13's rule in with bank 127 the ending's, 15 superseded); section 7's
  risks marked as they turned out (1: the cache held, the big items tear; 4: happened, `place_banks`; 5
  averted; 6 solved).
- **The `DIAG=2` sets** (found by this step's builds): `diag2` and `p_pzdiag2` stopped at z80asm since
  step 6 (`level3obj.asm:128` and `:134` "relative jump out of range", `:140` "duplicate definition of
  label lt_h"): `level3obj.asm`'s `l3_tail` and the VDP lab (`msx/lab.asm`, `DIAG=2` builds only) both
  define `lt_h`. `lab.asm`'s label is now `lab_lth` (two lines): the safest fix, in a test build's file no
  other step edits; no other build includes `lab.asm`, so every other ROM keeps its bytes (below).

### Commits
`46c4172` (`lab.asm`), `a178d0b` (`MSX_ARCHITECTURE.md`), `c7d4b28` (`ROM_BUDGET.md`), `b50936c`
(`AMIGA_ANALYSIS.md`), `b9b0666` (`README.md`, `LEVEL3.md`) and this section's.

### Checks (each with its command and result; `W` = the worktree)
- **The option sets** on 56e8f56: `sh tools/bstest/variants.sh S9/V` -> 56 of 61: the three known
  fixed-area overflows (`demoact`, `demoact5` -F3h, `demohud` -3Ah, as at step 5) and `diag2`, `p_pzdiag2`
  (above). With the fix: `sh tools/bstest/variants.sh S9/V2` -> **58 of 61** (the three known only); the
  56 ROMs built both times byte-identical (`cmp`, 0 differ); `diag2` `f0a3535bd730f5da`, `p_pzdiag2`
  `9bea38e5ebb2e48b`. Every log: build.sh's checks (mkrom's exit, no error, the 12 known z80asm warnings
  only); mkrom's checks (the 3Fh rule, the SCC test values, the guard's tag) in all 58. The product
  `fb06ae0faab13802` (2 MiB, 163 of 256 banks), the same bytes as step 6's.
- **The free bytes**: `python3 -I tools/bstest/l2base.py banks S9/V2` (all 58 sets) -> the product: fixed
  area 164, LC1 50, LC2 4,827, `BANK_L1` 874, LC3 4,794, INPUT 11, FRONT 1,119, FIELD 300, MUSIC 1,251,
  PUZL 4,483, FRNG 264, `BANK_L2` 1,429, `BANK_FRONT2` 7,041, `BANK_L3` 3,867, `BANK_L3B` 2,383; the lowest
  set (`DIAG=1 PZ_TEST=1`) fixed area 29, FRONT 721, MUSIC 1,280; the least per bank in
  `docs/ROM_BUDGET.md` 2.4. The bank map: the product's `rc2.log` and `gen/banks.inc`.
- **REA** (MCP, Ghidra 12.1.4, `build/ram/level3_full.bin` sha256 `700df44d…3515ca`, the seeds: 125
  functions created, 1 present, 317 labels, 0 failed): `read_function_instructions` `0xd49c`
  (`obj22_update`: `$D53A` `cmpi.w #$30,D1`, no D1 write before it, the fire counter's test at `$D526`),
  `0xc3e4` (`update_objects`: the handler's `jsr` at `$C432`, D1 loaded only on the dying path `$C40A`),
  `0x11062` (`text_plot`, 22 instructions); `xrefs 0xf878` -> `$80F8`, `$FEFC`, `$1080C`, `$10902`, `$12112`,
  `$121E0`.
- **`make test`** (the worktree, with the fix): 347 tests, **the 4 known failures only** (failures=3,
  errors=1, skipped=56).

### Numbers the later steps must refresh
- `docs/ROM_BUDGET.md` 2.4 (the product's hash, the free bytes, the bank map if a block grows, the 58
  of 61), the summary rows and section 7's "(new)" row; `docs/MSX_ARCHITECTURE.md`'s bank tables (`BANK_L2`
  1,429, `BANK_L3` 3,867, `BANK_L3B` 2,383), its "163 of 256 banks" and the "Known at 56e8f56" tear
  paragraph; `README.md`'s 163 banks; `docs/LEVEL3.md` risk 1 and the tear's "open at 56e8f56".

### Open issues
1. The tear of big play-field items (step 7) and checks 3-8 (step 8) are described as open at 56e8f56.
2. The `DIAG=2` sets count MUSIC's free bytes as 0 (`music_end` at C000h in that build): not looked into
   (a test build that plays no game; it builds and its other banks are as the product's).
3. The ledger records that the address arithmetic by which `text_plot`'s write reached `$10FD9F` was
   not traced (no emulator here).
4. Not run here (no emulator): checks 9-12 of `docs/LEVEL3.md` 4 (the fresh machines, the matrix, the
   bank-select log) belong to the candidates' builds.

### Integrated
Cherry-picked onto `level2` 56e8f56 (the main tree clean) as **`e5ec4b8`** (`lab.asm`), **`ac1fe6b`**
(`MSX_ARCHITECTURE.md`), **`31678f0`** (`ROM_BUDGET.md`), **`e5db439`** (`AMIGA_ANALYSIS.md`), **`af05f35`**
(`README.md`, `LEVEL3.md`), **`c1a25d8`** (this section), **`0f81c37`** (a table row's indentation) and this
note's. In the main tree then: the product, `DIAG=2` and `DIAG=1 PZ_TEST=1` built with
`tools/bstest/build.sh` byte-identical to the worktree's (the product `fb06ae0faab13802`), so the results
above hold; `make test`: 347 tests, the 4 known failures only. The summaries (the two option-set runs,
the free bytes of the 58 sets, the logs) in `build/archive/rest_step9_records_2026-11-01.tar.gz`; the
option sets' ROMs deleted.

## Step 7: the tear of big moving play-field items (2026-11-01)

**Done, one open issue** (the beam crossing a chain's last band on the V9958: below). Worktree `g/wt07`, branch
`g-s07` from `level2` `a80288d`, moved to `56e8f56` (step 6's logic: the real Cain) and rebased onto
`001787b` (step 9); scratch `S7` = `$SCRATCH/g/s07`. One openMSX: a private MSX-AI MCP session
(`tools/bstest/mcpd.py S7/mcp`, `mx.sh`). Step 5's open issue 1.

### What it did
- **The cause** (the records' field state at each split, `S7/tools/fbstate.py`: `fb_stg`, `fb_spk`,
  `fb_scp`, the queue): the torn pictures were a staged item's pieces after the first. `fst_more` let the
  main loop start each of them "right away" when it found the VDP idle, 2-15 ms after the one before and
  often while the beam drew it, so the item showed between two pieces for 1-10 pictures (runs of up to 10
  in the records). A first try, every piece in `fb_cmd` and `fb_cmd2` for the split interrupt, fell back to
  the old path whenever a 2 x 2 item crossed the ring (more than four commands: Cain at map y 768).
- **`msx/field.asm`** (`13924de`): `fb_stage` composes a staged item's pieces side by side in page 3
  (piece k at x 64k: the three caches lent, piece 3 in the scratch; `fb_scol` its pieces across);
  `fst_chain` prepares the item's copies as one chain for the split interrupt (`fb_scp` 2): one HMMM a band
  of pieces, cut where the V9958's ring is crossed, the last band's first and of a band's parts the larger
  last (`fb_sord`, `fch_hf`), so that the split's wait (`isr_fbgo`, 110 polls) covers only the small ones;
  `fb_cq` 3, `fb_vok` 0 (never the VBLANK's start; a one-command chain may start in the blank by
  `fb_mayq`); more than four commands or a piece out of its window: piece by piece as before. `fcp_sp`:
  `fb_copy`'s cut points as a routine (`fst_chain` and `fb_copy`). `fst_more` counts `fb_scp` 1 only.
  `VAT_ANIM=1` builds keep the old staging (no room in `BANK_FIELD`; they serve level 2's comparison).
  `msx/msx.inc`: `fb_scol` 065Ah, `fb_sord` 065Bh (065Ch-065Fh free). `tests/test_level3_field.py`:
  `test_staged_pieces_one_chain`.
- **Not taken**: option (a), a fit test for chains: from the split a big item high on the screen cannot
  stay ahead of the beam at 6.3 us a byte in any order (Cain's top at shown line 46: the beam catches a
  64-wide copy after about 44 of its lines), so the test would only hold the item; option (c), the
  V9938's page flip: the V9938 shows no torn item with the chain in the real windows.

### Commits
`13924de` (the chain, the test) and this section's (with `docs/LEVEL3.md` 3.10 and
`docs/MSX_ARCHITECTURE.md`'s play-field rules).

### Checks (`W` = the worktree, `PY` the venv's Python, base = `level2` without `13924de`)
- **Builds** (`sh S7/tools/mkb.sh W S7/bv4 "prod" "low DIAG=1 PZ_TEST=1" "anim VAT_ANIM=1" "diag2
  DIAG=2"`; `sh tools/bstest/hz.sh l3builds S7/R4`): all build, the 12 known warnings only; the product
  `fde75be5865bfb72`, l3 `7d5eb71e82a31bb5`, the lowest set `b941de7001cd6c49`, `VAT_ANIM=1`
  `ac52b05753a61100` (byte-identical before and after the rebase onto `001787b`, so every result below
  holds). `sh tools/bstest/variants.sh S7/V` on `56e8f56` + the chain: 56 of 61 (the three known fixed-area
  overflows; `DIAG=2` and `PZ_TEST=1 DIAG=2` failed at `level3obj.asm:128` on the base too: step 9's
  `001787b` fixed it, `DIAG=2` builds here). **Free bytes** (`python3 -I tools/bstest/l2base.py banks
  S7/bv4`): the fixed area 164 (the same), the lowest set 29 (the same); **`BANK_FIELD` 300 -> 49** (the
  product and the lowest set), `VAT_ANIM=1` 99 -> 93, the l3 trace build (`EXTJOY=1`) 259 -> **8**.
- **The field check's torn pictures** (`CLASS ... hostage-tear`: a big item partly a picture ahead or
  behind at the split; `$PY -I tools/bstest/fieldcheck.py DIR build/msx/level3 OUT.png --level 3`, counted
  by `S7/tools/tears.py DIR FC.txt LEN`), base -> new, the same jobs on both builds (`lf_jobs DIR R POSES
  FROM N MACHINES DRIVE`; the real logic with `poses_none.tcl`, nothing injected):

  | window | V9938 (C-BIOS_MSX2) | V9958 (FS-A1FX) | turbo R (FS-A1GT) |
  |---|---|---|---|
  | `boss` from tick 125, 1,000 pictures (Cain on the roof) | 10 -> **0** | 84 -> **0** | 114 -> **21** |
  | `kill` from tick 1500, 700 pictures (Cain on the ground floor, his death) | 61 -> **0** | 65 -> **1** | - |
  | stress (`poses60`, `lf_mul 8`, `lf_dx 0`, idle drive, 1,100 pictures) | 106 -> 49 | 194 -> 106 | 188 -> 83 |
  | stress: Cain's phase | 8/271 -> 0/273 | 48/299 -> 4/254 | 44/203 -> 7/193 |
  | stress: type 21's phase | 59/299 -> 30/272 | 65/256 -> 27/251 | 52/208 -> 37/199 |
  | stress: the truck's phase | 20/279 -> 17/252 | 59/275 -> 51/256 | 48/218 -> 12/174 |

  The stress test's remaining ones are runs of 2-24 pictures while the scripted enemy and a real one
  (`D0E4h`) are composed at once (four pieces each: the hold, `FB_HOLD` 8, runs out), a load the real
  game does not make (ENEMY_CAP 1); `poses60.tcl` is step 5's, the idle drive `build/emu/l3_still.drive`
  (no input; made from `l3_tour3.drive`'s pokes). Looked at (the field check's sheets, `S7/kb0/fx.png`,
  `S7/kb3/fx.png`): the base's torn boss pictures show Cain on the roof with pieces of his white hit-flash
  copy left beside his normal look; the new build's pictures there show him and the smoke whole.
- **The guard** (42 s from level 3's first tick, `boss`'s drive; `S7/tools/gd.tcl` `gd_jobs`, as
  `lf_start_jobs` with another drive), base -> new: **tear** (a copy the beam crossed) m2 3 -> 0, fx 8 ->
  **15**, tr 10 -> **22**; reg (R#46 written in the play area) 58 / 183 / 182 -> 0 / 5 / 2; cmd 95 / 279 /
  405 -> 53 / 130 / 274; vbl 0 / 10 / 1 -> 0 / 11 / 6; pal and cpu 0; lost 0. The stress test (fx): tear 5
  -> 69, reg 103 -> 1, cmd 351 -> 252, vbl 127 -> 18. The new tears are the chains' last bands (50-124 x
  59-64) started at lines 228-260: the blank begins during the split's wait (the HUD's 45 lines) and the
  VBLANK interrupt goes on with them only after its list (`isr.asm` `ifg_fin`), too late for a band high
  on the screen; one picture is torn each time (about 1 in 170 on the V9958 in the boss window, against
  84 in 1,000 at the split before).
- **Speed** (ticks reached in the same pictures, 60 Hz): the stress test fx 246 -> 265, m2 212 -> 238, tr
  320 -> 350; **Cain's phase** fx 11.6 -> 13.7 ticks a second, m2 12.8 -> 12.7, tr 17.1 -> 18.0; **type 21's**
  fx 14.1 -> 14.3, m2 12.0 -> 13.2, tr 17.3 -> 18.1; `boss` fx 248 -> 254, m2 232 -> 235, tr 350 -> 366;
  `kill` fx 1624 -> 1634, m2 1629 -> 1636. Not slower anywhere but Cain's phase on the MSX2 (-1 %).
- **Levels 1 and 2** (`S7/tools/ab.tcl`: step 5's comparison, base `SRC=S7/bwt` builds of `56e8f56` and
  new): the `LOCKSTEP=24` records, `python3 -I tools/dispcmp.py BASE/disp_M.txt NEW/disp_M.txt`: **2,998
  lists, 0 differ** on C-BIOS_MSX2 and the FS-A1FX; level 1's 10 stills (`tools/msxframe.py --level 1
  --field`): 4 byte-identical, 6 the same verdicts (the known 31, 260, 6 px); level 2's 24 stills (`--level
  2 --field`): 6 byte-identical, 16 the same (0 differ), the MSX2's g0900 44 -> 0 px, its g1600 0 -> 8 px
  (8 sprite pixels on a line of 9 sprites, step 5's known class; the new build reached frame 1600 2.4 s
  earlier, so the still is another moment).
- **`make test`** (the worktree): 348 tests, the 4 known failures only.

### Open issues
1. **The beam crosses a chain's last band** on the V9958 and the turbo R (above: 15 and 22 copies in 42 s
   of the boss window, each one torn picture). In `field.asm` alone no order holds both ends: the largest
   band first starts it at the split but leaves the rest to the main loop (step 5's tear); last, it waits
   for the VBLANK's list. Next levers, outside the copy path: in `isr.asm`, the VBLANK interrupt going on
   with a pair's parts (`ifg_fin`) before its list, or the split's wait not stopping at the blank for a
   chain; or a copy started right after the beam leaves the item's top (a line interrupt: each line gets a
   whole frame). The user's choice may be needed (decision 13's play field against sprites for Cain).
2. `BANK_FIELD` has 49 bytes left in the product and **8 in the trace builds**: the next change of
   `field.asm` needs room first (`VAT_ANIM=1` builds keep the old staging for that reason).
3. The stress test's runs while two big enemies change at once (the hold runs out); not reached with
   ENEMY_CAP 1.
