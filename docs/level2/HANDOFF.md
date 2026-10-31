# Level 2 implementation: handoff log

Plan: ../LEVEL2.md (sections 5-7). Branch `level2`, created on 2026-10-28 from main a969fc8
(level 1, Brainstorm and the shooting range; the range's candidates test4 were delivered from it).
`make test` at a969fc8: only the 4 known failures (test_line_counts_and_rank_list,
test_joystick_script_entries, test_compositions_fit_their_bank_and_the_limits,
test_records_bits_ids_and_sat_order). The whole regression: tools/bstest/regress.sh and
regress.tcl (docs/HARNESS.md 5.19-5.20).

Each agent appends one section: what it did, the files, the commits, every check with its exact
command and result, the open issues.

## Step 0: the baseline (2026-10-28)

**Done.** The base is a969fc8 (no msx/ or mkrom.py change since; 26c9dd9 and 3b6487e add only harness
files and docs, so every ROM at 3b6487e equals a969fc8's). Records in `$IMPL/base`, with
`IMPL=/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space/l2/impl`
(this folder); the range's base (4a8a61d) is `$IMPL/../../range/impl/base`. Commits **26c9dd9**
(and **3b6487e**: the job counts in HARNESS.md and l2base.sh's header): `tools/bstest/fieldcheck.py`,
`sess_fxlog.tcl` (copied in), `l2base.sh`, `l2base.tcl`, `l2base.py` (new), `docs/HARNESS.md` 5.21
(+ the file table and the labels list).

### THE ONE CHECK: any later build against this base

```sh
W=$IMPL/sNN/W            # a fresh folder per run (outside build/msx)
sh tools/bstest/l2base.sh builds $W
# MCP (msx_local_boot headless, then one msx_local_cmd):
#   source {<repo>/tools/bstest/load.tcl}; source {<repo>/tools/bstest/l2base.tcl}; l2b_chain {W} {W/all.done}
until [ -f $W/all.done ]; do sleep 20; done      # 227 jobs, about 8 minutes
sh tools/bstest/l2base.sh check $W $IMPL/base     # "l2base: PASS", exit 0
```

**Since the harness step (2026-10-28, section "The gate made timing-blind" below): pass it
literally.** A change of level 1's CPU time no longer fails it: the title from power-on is judged
on an exact record (job `xfresh`, the game at exactly tick 300; its RAM by variable, relocated
pointers and moved variables followed), the titles after the flows on the registers that show,
the field check with the known hostage tear classified and bounded (`l2base.py TEARS`), the
effects by their starts (`fxcmp.py`). No manual method (xfresh.tcl, fxcmp by hand, unseen_regs by
hand, the tear by eye) is needed any more; a FAIL is a real difference: read its lines.
Two practical rules: (1) build HEAD (or your step's commit) from a `git worktree` with the build
data copied when other agents have uncommitted edits in the shared tree (they enter a plain
`l2base.sh builds`); (2) the in-process MCP holds ONE local openMSX target, shared by the agents
of this process: if `msx_local_boot` says "already connected" and another agent's chain lives in
it (`list $::hz_state $::hz_mark`), do not use it; start a private MSX-AI MCP session instead
(`$IMPL/sg/mcpd.py` + `mx.sh`, below).

`check` = `regress.sh check W BASE` (the range's 45 verdicts: level 1's cov traces, the title from
power-on, the product's and PZ_TEST flows, the keyboard flows, 2 MiB, turbo R writes, Brainstorm's
20 traces + stills + records + guard + HUD, the range's 41 screens + 79 drive traces + wanted
state + display + 20 sound logs) and level 1's records of `l2base.tcl` against the base's
(HARNESS.md 5.21 table). A run writes ~1.9 GB (V/O 1.1 GB): delete W's subfolders after its verdict,
keep its logs. One family of the range: `rgr_chain {W} FAMILY {W/f.done}` + `regress.sh check W
$IMPL/base FAMILY`. When a step changes level 1's flow on purpose (step 18: the briefing after the
range), regress.sh's flow checks must learn it first (bonuscheck.py, plan 4.4).

### What the base holds (`$IMPL/base`)
- builds: R (prod pzt pz1 pz2 trace ext), X, V, S (regress.sh builds), L/lock24, L/lock24p, T4 (TAG=4,
  1 MiB and 2 MiB), variants/ (the 41 option sets), drives/.
- level 1's traces: O/trace/cov1.txt (4,401), cov0.txt and cov0_tr.txt (1,400), l1/trace/{die,over,end}.txt;
  O/rg/l1cov* (after the range).
- the start check: l1/start/st_{m2,fx,tr}.txt; the field records: l1/field/{430,860,1490}_{m2,fx}/
  (+ .check.txt, .png sheets); the stills: l1/still/{m2,fx}/gNNNN (+ msxframe PNG/txt);
  the LOCKSTEP records: l1/lock/disp_{m2,fx}.txt; the effects: l1/fx/{fx_scc,pw_scc,pw_psg}.txt.
- the title on a fresh Expert: fresh/base_* (= fresh/new_*, a969fc8's; identical to 4a8a61d's in
  every record); after the flows: O/np/tx_{ex,f1,tr}_*.
- Brainstorm: O/st, O/tr, check_all.log; the range: O/rg, O/lt, O/snd, V/O; the product flow:
  O/flow (prod_*, pzt_*, after_*, guard_*), O/kb (kb_ex, kb_tr), O/np (p2m_ex, solved_*, two_*).
- banks.txt (every build's code-bank free bytes), banks_variants.txt (the 41 option sets).
- recovered/: fxcheck.py (see open issue 1), sess_fxlog.tcl as recovered.

### Checks (exact commands, results)
- `sh tools/bstest/regress.sh builds $IMPL/base`: builds PASS (21). `sh tools/bstest/build.sh
  $IMPL/base/T4/rc2.rom TAG=4`: sha256 3f49a34c0435a069… = build/msx/ROBOCOP2_v0.1.3-test4.ROM (cmp
  identical); `TAG=4 ROM_2M=1` = ROBOCOP2_v0.1.3-test4-2M.ROM (cmp identical).
- Rebuilt byte-identical: `regress.sh builds $IMPL/rebuild` + the two L builds: 25 ROMs, 0 differ;
  the 23 regress builds equal the range's step-13 builds (`space/range/impl/s13/W`, 4650771): 0 differ.
- `sh tools/bstest/variants.sh $IMPL/base/variants`: 38 of 41 OK; DEMO_ACTORS=2, =5 and DEMO_HUD=1
  overflow the fixed area (rc2.asm:487 ds −0xdb / −0x22), as at the range's base.
- MCP: `l2b_chain {$IMPL/base} {$IMPL/base/all.done}`: 225 jobs (the first l2base.tcl), 0 time outs;
  st_* and pw_* redone with the final l2base.tcl (5 jobs, `redo.done`).
- `sh tools/bstest/l2base.sh check $IMPL/base $IMPL/base $IMPL/../../range/impl/base` (the range's
  base 4a8a61d): **l2base: PASS** (`base/l2base_check.log`): regress: PASS, 45 verdicts, 0 FAIL;
  die/over/end 901/1,249/517 rows, 948 fields, 0 differ; start check m2/fx/tr: reg pal cmd cpu vbl
  tear 0, 26,690/26,445/31,505 sprite entries 0 bad, 0 frames above 8 a line, SATs 0 bad, lost 0;
  field check 0 differ in every window but 860_m2 (3 pictures, 177 px: see issue 3); stills
  identical (msxframe's own counts 0/77/37/462 (fx 543)/57); LOCKSTEP 3,000 lists, 0 late, both
  VDPs; effects 800 starts, 7,435 SCC ticks, PSG 19,846 / 22,217 writes. Then `l2base.sh base
  $IMPL/base`: "base: ready".
- Dry run of the one check (a second whole run, 226 jobs, on the rebuild): `sh tools/bstest/l2base.sh
  check $IMPL/rebuild $IMPL/base`: **l2base: PASS**, every record identical to the base's
  (`rebuild/l2base_check.log`; its big record folders deleted).
- Negative controls (`$IMPL/neg.sh $IMPL/base $IMPL/neg`, `neg.log`): a trace field, tear 0→2, cpu
  0→1, 50 zeroed lines in a field record (10,987 px), a zeroed still page (42,348 px), a LOCKSTEP SAT
  byte, a PSG write, an SCC tick: all 8 FAIL as they must.
- `make test`: 224 tests, only the 4 known failures (failures=3, errors=1); `python3 -I -m unittest
  discover -s tests -p test_bstest.py`: 34 OK with the new files.
- Pictures looked at: a field-record contact sheet (level 1's corridor, RoboCop firing), the still
  fx_g1490 (the vehicle, RoboCop, the HUD), the 860_m2 hostage crop.

### The bank map and free bytes (product, 1 MiB, 128 banks)
0-1 fixed; 2 LC1; 3 LC2; 4 L1; 5 LC3; 6 INPUT; 7 FRONT; 8 FIELD; 9 MUSIC; 10-17 tiles; 18-20 map;
21-43 sprites; 44-45 HUD; 46 attributes; 47 HUD image; 48 level tables; 49 field images; 50-51
field dynamic; 52-58 title picture; 59-64 game-over picture; 65-67 voice; 68-70 voice mix; 71-74
SCC music; 75-76 FM; 77 SCC effects; 78 PUZL; 79-85 PUZL gfx; 86-87 PZM; 88 FRNG; 89-96 range gfx;
97-98 range hits; 99-103 FRM; **104-127 free (24 banks)**.
Free bytes (product): fixed 188, LC1 39, LC2 5,087, L1 984, LC3 5,105, INPUT 11, FRONT 2,309, FIELD
1,529, MUSIC 1,331 (music_end BACDh; Pico+: only the 256 B below B800h hold what the player reads
with the SCC mapped), PUZL 4,590, FRNG 700. The fixed area per option set (banks_variants.txt):
DIAG=1/2 + PZ_TEST=1 **14 B**, DIAG=1/2 44, EXTJOY+LOCKSTEP+PZ_TEST 88, LOCKSTEP 118, PZ_TEST+EXTJOY
134, PZ_TEST 158, EXTJOY 164, product 188; DEMO_* already overflow.

### Open issues
1. fxcheck.py is not lost: its 2026-10-22 text (heredoc + the 12:37:39 edit) came back from the
   session log: `$IMPL/base/recovered/fxcheck.py` (not committed; it replays sess_fxlog logs against
   build/msx/sccfx.bin). Step 21 may start from it. sess_fxlog.tcl sees only the SCC path:
   pw_* (every PSG write) covers the PSG alone in the base.
2. The relocation drive of plan 4.4 (`drive_reloc_up`) is lost (it lived in the scratch folder
   agentC); the base has cov1, cov0, die, over and end. Its args are in the session log if wanted.
3. Pre-existing, not a regression: fieldcheck 860_m2, pictures j008_f0021-23: the hostage half
   old, half new (336 old, 59 new px) for 3 pictures on the V9938; 0 on the V9958 (v0.1.1 had
   "3/6"). The gate allows at most the base's count.
4. fieldcheck.py needed more than a copy: at the base the old copy skipped every record silently (the
   record grew by MP_B in 46fa12c); now it reads the two pools and reports skipped files. Step 13
   adapts it for level 2 (atlas, vats).
5. rc2_guard flags writes it cannot place: started inside an upload it reported 81 false "cpu" on
   the FS-A1GT. Level 2's start check (4.2 check 1) should start the guard at tick_start, as
   l2base.tcl l2b_st_go does.
6. The fixed area: 14 B left in DIAG + PZ_TEST builds; step 4's "free bytes in every option set"
   starts from banks_variants.txt.
7. regress.sh's own `base` command still makes the range's base (4a8a61d); level 2's base is made by
   l2base.sh (builds, the chain, `check W W RB`, `base W`). macOS cleans the scratchpad after days
   without access: if $IMPL/base goes, remake it from a worktree of a969fc8 the same way (RB = the
   range's base, or `regress.sh base B`).

## Step 17: the texts (2026-10-28)

**Done, offline (no openMSX).** Commit **8b1ca1e**: `tools/msxtext.py`, `tests/test_bonus_text.py`.
Scratch: `S=$IMPL/s17`.

### What it does
- `BRIEF = (("txt_l2_brief", 0x110F0, 393), ("txt_l3_brief", 0x110B4, 411))`,
  `CONT = (("txt_cont", 0x11590, 304),)`, read from build/ram/level1_full.bin (the same bytes in
  level2/3_full.bin). The particle part (`FF 04 p` `FF 03`) runs through rc2front.py's model. Its
  text is typed in the 8 × 8 font at the column and row whose cells are centred nearest the stroke
  text's box (computed, not hard-coded). Then a wait and repeated positions make up its calls, and
  the original's lines follow unchanged. The continue is the original's bytes.
  - `txt_l2_brief`, 41 B, 29 elements, 393 calls: `00 0A FD` "TOKUGAWA BREWERY" `FF 02 1B` |
    `00 0C 04` "ARREST CAIN" `FF 02 40` `FF 07`. Stroke box x 0-253, lines 40-53 → title x
    64-191, lines 43-50.
  - `txt_l3_brief`, 83 B, 63 elements, 411 calls: `00 0C FA` "CIVIC CENTRUM" `FF 02 17` + 3 ×
    `00 0C FA` | `00 04 01` "BATTLE YOUR WAY TO THE ROOF TO" `00 0C 03` "CONFRONT CAIN." `FF 02 40`
    `FF 07`. Stroke box x 32-237, lines 16-29 → title x 80-183, lines 19-26.
  - `txt_cont`, 57 B, 48 elements, 304 calls: $11590 as is.
- text.inc = the old part, byte-identical, + `brief_inc` (3 labels, no equates). Renders next to
  OUT.inc: `text_l2_brief`, `text_l3_brief`, `text_cont` (.sc5 + .png).
- For steps 18/19 and their checks:
  - `msxtext.brief_scripts(ram)` and `msxtext.cont_scripts(ram)` return [(label, address,
    bytes)];
  - a TAG build's reference is `fs_render(glyphs, tag_line(5) + script)`, as rgcheck.py does;
  - `check_text(label, script, calls)` takes any order of elements (rows −8..8 signed, the TAG
    row free, no cell twice); `particle_title`, `s8`.
- **build/msx/text.inc was not regenerated** (another agent builds from it). The labels arrive at
  the next `make msx`, or with the Makefile's line `python3 -I tools/msxtext.py
  build/ram/level1_full.bin build/msx/text.inc build/msx/title.sc8 build/msx/title_credit.sc8
  build/msx/gameover.sc8 build/msx/gameover_text.sc8`. Every ROM's FRONT then grows by 181 B at its
  end, and nothing else changes (below).

### Checks (exact commands, results)
- Before (HEAD's tool, = `git show HEAD:tools/msxtext.py`): `python3 -I tools/msxtext.py
  build/ram/level1_full.bin $S/before/text.inc build/msx/title.sc8 $S/before/title_credit.sc8
  build/msx/gameover.sc8 $S/before/gameover_text.sc8` gives 27 files, each cmp-identical to
  build/msx's (text.inc sha256 3d5a464e…).
- After: the same into `$S/after`:
  - the 26 old .sc5/.png/.sc8 files are cmp-identical, the title and game-over pictures included;
  - text.inc's first 16,117 bytes equal the old file's, and 1,728 bytes are appended;
  - output: 41 B (393 calls), 83 B (411), 57 B (304).
- Pictures looked at: `$S/sheet_brief.png` (3×, the three screens). They match the original's
  layout in build/front/screens/briefing_level2.png and briefing_level3.png. The title is in the
  font's green, not the particles' blue (default 2).
- `python3 -I -m unittest discover -s tests -p test_bonus_text.py`: 40 OK. The 7 new tests:
  - the bytes as the plan;
  - the calls equal rc2front's model, and the title takes 125 / 109 calls;
  - the titles' boxes, and centring within half a cell;
  - the play areas against an independent model with signed rows, plus TEST 5;
  - text.inc's prefix pinned to a969fc8's sha256 (`TEXT_INC_A969FC8`; update the pin only if a
    later step changes the old texts on purpose);
  - negative rows in 8 bits;
  - check_text's 9 refusals.
- Mutations (`python3 -I $S/mut/run.py <repo> $S/mut/m_{row,rg,extra}.py`): all 3 are caught:
  - the title one row up;
  - one character changed in the range's comment (only the sha pin catches it);
  - one call too many.
- `make test`: 231 tests, failures=3 errors=1. These are the 4 known failures only (the 7 new
  tests ran and passed).
- Assembly, offline:
  - set-up: a worktree of 3b6487e (removed after) and a cpio copy of build/msx (regress.sh's
    pattern) in `$S/msx`;
  - `SRC=$S/wt LEVEL=$S/msx/level1 sh tools/bstest/build.sh $S/rom/{old,new}/{prod,tag5,diag1}/rc2.rom
    [TAG=5 | DIAG=1]`, old with the current text.inc and new with `$S/after/text.inc`: 6 × build
    OK, the 12 known warnings, 0 other messages;
  - old prod = the base's R/prod (sha256 31e09590d52dee35);
  - `python3 -I $S/romcmp.py <repo> $S prod tag5 diag1`: **PASS**. 173 bytes differ in each
    (181 − 8 that are FFh in both). All of them lie in FRONT between the old and the new
    `front_end`, they are exactly the 3 scripts (FFh before), and every other label is unchanged
    (the fixed area and every other bank: 0 bytes differ).
  - Product labels: txt_l2_brief 96FBh, txt_l3_brief 9724h, txt_cont 9777h, front_end 97B0h.
  - **FRONT free**: product 2,309 → 2,128 B; TAG=5 2,277 → 2,096 B; DIAG=1 (the tightest set)
    1,950 → 1,769 B. The fixed area's free bytes are unchanged (188 in the product).

### Open issues
1. None blocking for step 18.
2. 4.2 check 11 (the screens in openMSX against these renders, with the display, R#0's line
   interrupt and the HUD split on) belongs to steps 18/19.
3. For the user's eye: the title's colour (defaults 1-2: the font's green, colour-4 shadow).
4. Level 3's second line keeps the original's column 4 (x 16-255: the original's 8 px right of
   centre).

## Step 1: the names and the ledger (2026-10-28)

**Done, offline (no openMSX).** Commit **223fd46**: `analysis/main_8000.sym`,
`analysis/ghidra_seeds.tsv`, `docs/AMIGA_ANALYSIS.md`. Scratch: `S=$IMPL/s01` (`names.py`: the
reports' names and their conflicts; `merge_sym.py`, `ledger.py`: the exact edits;
`main_8000.sym.orig`, `seeds_before.tsv`, `make_test.log`, `gaps_{orig,new}.s`).

### What it does
- `main_8000.sym`: +4 `+entry` (c91a, d1ca, d1d0, d1de), +13 `+data` ranges (level 2's lists and
  tables), +135 names, 12 old comments completed (load_level1/2, the load table, spawnlist_level1,
  objlist_level1, special_l1, act_0c, objtype_act_base, special_handlers, walker_legs, msg_arrest,
  level_done). Its convention: level numbers from 0 (`_level1`, `_l1`, `level_tick_1`,
  `level_header_1`, `restart_level12`, `sp1_*` are level 2's); type handlers keep `objNN_update`;
  deaths `death_*`; frame tables `tN_*`, `*_offs`, `*_bltsize`, `*_dx`, `*_dy`. Siblings added from
  the headers: `speclist_level0/2`, `hazlist_level0`, `markers_level0/2`, `level_header_2`.
- **The 36 settled** (final name, then the reports' others): 15f0 vats_first_done
  (vat_phases_done); 868c level_header_1 (level2_header); 86dc restart_level12
  (level_restart_rts; the seeds' level_load_1); 8fe0 speclist_level1 (speciallist_level1/2);
  9088-910e sp1_lift0-4, sp1_trolley0-3 (sp2_*); 91b0 level_tick_table (hazard_handlers,
  hazard_tick_table); 927a vat_surface_words (vat_tiles, vat_top_words); 929a vat_odd_words
  (vat_body_words_a); 92ba vat_even_words (vat_body_words_b); 92da vat_column_phases (vat_phase,
  vat_phases); 95b2 hazlist_level1 (hazards_level1/2, vat_list); 9ee8 act_0c (act_blink_mine);
  a4a6 act_0c_blink_word (act0c_blink_word, act_0c_look, type30_blink_word); c25c death_cain
  (kill_case_c25c, obj22_death); c33e death_barrel (death_t6); c5ec markers_level1
  (markers_level2); c7e0 t1_legs_offs (t1_legs_gfx); c91a obj02_arrest (obj02_arrest_tail); d17c
  t5_bltsize (t5_size); d19a t5_gfx_offs (t5_gfx); d1ca obj06_gap_count (obj06_wait); d1dc
  barrel_gap (obj06_countdown, t6_busy); d2da t6_gfx_offs (t6_gfx); e680/e6a0 homing_dx/dy
  (fly_dx/dy); e728 homing_body (obj38_fly); e7b2 homing_gfx_offs (fly_gfx); 10356
  copper_sprite_cut (vat_cut_line).
- Kept against the reports (plan section 10): special_l1, level_tick_1, spawnlist_level1,
  objlist_level1, objtype_act_base, act_0c, msg_arrest and the generated `obj01/02/05/06/14/16/49_update`.
  Renamed single-report names for the convention: sprites' walker1_* → walker_legs_* (c9a4-c9f4),
  walker2 → walker2_legs (cc4a).
- Left out of main_8000.sym on purpose: `$3BE80` (row 50 after the map) and `$4B95A` (the
  trolley's BOB): level data, and this file seeds every level image; the ledger names them.
- `docs/AMIGA_ANALYSIS.md`: new section 4 "Level 2: the Tokugawa brewery" (before "Music and sound
  effects": the image and seeds, MADEX = DATAL1's tail, the way in and out, the load table, the
  headers table, the lists, the arrest, `$8060`'s and `$805E`'s writers, the vats, `$EF8E`, type
  6's death; items re-read marked *REA 10-28*) and the Files table's MADEX row (was "level-2 BOBs
  [inferred]").

### Checks (exact commands, results)
- Seeds: `python3 -I tools/ghidra_seeds.py build/extracted/boot/main_8000.bin analysis/main_8000.sym
  analysis/ghidra_seeds.tsv` → "116 functions, 285 labels" (the old sym reproduces the committed
  file byte-identical: 112/176).
- REA MCP (its REA_GHIDRA_SEED_FILE is the repository's `analysis/ghidra_seeds.tsv`):
  `open_binary build/ram/level2_full.bin` raw-binary, m68k, entry 0x0, provider ghidra (sha256
  a039a158…0a88b09): **"Seed outcome: 115 functions created, 1 already present, 0 failed; 0 code
  seeds decoded, 0 failed; 285 labels applied, 0 failed; 0 seeds outside initialized memory."**
  (REA's seed sha256 edd527e3… = the file's entries).
- REA `xrefs 0x16d0`: 0x8158, 0x8188, 0xc29a, **0xc936**, 0xdfda, 0xdfe6.
- REA `batch_decompile [0xc91a, 0xd1ca, 0xc33e]`: 3 ok, 0 failed. `obj02_arrest`: `+21h = 4; if
  (+23h) { message_queue(); sound_requests = 0x21; level_done = 0xff; end_count = 0x40; return -1;
  } return 0`.
- REA reads for the ledger: `read_bytes` 8664 (152 B: the 3 headers, 86DC rts, 86DE), 86FA (the
  load table: 8352 86DC 86DC 86DE 82EC 8582 8524 86DE), 95B2 (the 7 vats), 9230 + 9318 (the
  column loop, T0-T2, 48 phase words up to 933A), 914C, EF9E, 10350, 11FD2, FFC4, D1C4; `xrefs`
  8060 (8314 8482 84FC C512 C706), 805E (83FA FFCC 11FD2 11FEE), 15F0 (9150 9236 9272), C948 (CA78
  CD7A D87E DC9C); `procedure_assembly` C33E. REA closed after.
- Data (python3 -I): MADEX_17.bin == DATAL1_10.bin[1D250h:] True; level2_full.bin holds MADEX at
  45250 and DATAL2 at 28000; row 50 (3BE80) has 35 of 160 words with a nonzero low nibble.
- The sym's other reader: `~/.venvs/msxports/bin/python -I tools/m68kdis.py
  build/extracted/boot/main_8000.bin --base 0x8000 --sym analysis/main_8000.sym --a6 0xdff002
  --scan-gaps -o $S/gaps_new.s` parses it: 7553 instructions (old sym 7560); the 8 lost are gap-scan
  garbage (6 inside the new data ranges, C918 and D1CC mid-instruction), the 2 new are D1CA and
  933A.
- `make test`: Ran 231 tests, FAILED (failures=3, errors=1, skipped=34): the 4 known only.

### Open issues
1. **For step 9 (`death_c33e`)**: `$C33E` is `addq.w #1,$15F2; moveq #3,D5; and.w $15F2,D5; bne
   $C35A; (pickup 24h, or 1Ch at the 16th) bsr $F98C` and falls into `$C35A`: the explosion type
   is `$15F2` & 3 (0 with the pickup, else 1-3), not always 0 as the plan's 2.5 says (its 2.6 and
   the sprites report have it right).
2. **For steps 2 and 19 (`over`, `cont`)**: `$11FEE` is `clr.b $805E`: after a game over without a
   credit the word reads 00FFh (FFFFh with its high byte cleared) until `$FFCC`'s `clr.w` at the
   next new game. Nothing reads it in between; only a trace that compares `$805E` after `$11FD2`
   sees it.
3. The phase table runs to `$9339` (48 words); the vats read the first 23 (`$92DA-$9307`), as the
   plan says.

## Step 6: level 2's map data (2026-10-28)

**Done**, offline (no openMSX). Commit **e074b06** (6 files, explicit paths): `tools/msxlvpal.py`
(new), `tools/mapcells.py` (`--level`), `analysis/amiga_tables.tsv` (bank `l2`), `tools/msxconv.py`
(docstring only), `Makefile` (level 2's conversions in `msx`, after level 1's msxconv), and
`tests/test_level2_data.py` (15 tests). Scratch: `$IMPL/s6` (logs, hashes, crops, negative controls).

What it does:
- `msxlvpal.py palette`: palette C = level 1's joint `.pal`/`.remap` (robocop) with an entry 8-15 set
  to level 2's 3-bit colour when every Amiga colour the remap puts there agrees on it (9 = 555 c15,
  11 = 015 c5, 13 = 012 c6; 14 kept 500: c10 → 500 and c11 → 300 disagree). Applied to level 1's own
  colours it gives level 1's palette back (tested). Writes `level2.pal`, `level2.remap` (= level 1's
  remap). Checks: 0-7 = level 1's, remap free of 2/3/7, colour 0 black, mean ΔE76 ≤ option A's.
  Pure stdlib Lab; reproduces the map report's numpy figures exactly.
- `msxlvpal.py preview`: the whole map, the original (12-bit) above the conversion (`.til`/`.map`,
  graded with BRIGHT), 2560 × 1608; fails unless every cell's tile is the original's through the remap.
- `mapcells.py --level 2` (default 1, CLI unchanged for mkrom.py): objl_l2's 44 objects; activator
  0Ch adds act_0c's words (`MINE_WORDS` E680h, 9700h, checked against the image's code at $9EE8/$9EF8
  in the tests); `map_cell` uses $EF8E's row limit 51 in every level (`EF8E_ROWS`, the same for level
  1); level 1's beams only for `l1`, an unmodelled hazard list stops; the vats (`hz_l2`) stay out of
  the pools: `vats()`, `column_look()`, `vat_problems()`: attributes 0 in T0/T1/T2 and in every vat
  cell (map at $38000 of level2_full.bin), no object cell in a vat, every vat word's tile in `.otile`/
  `.til` (siblings of the `.atrp` argument), every column one look. Misread records stop at once.
- TSV bank `l2`: `l2_hdr`, `objl_l2`, `sp_l2`, `spl_l2`, `mk_tab2`, `hz_l2`, `vat_top/odd/even`,
  `vat_ph0` (23), `t1_*`, `t5_*`, `t6_gfx`, `fly_*`, and 15 copies of level 1's shared tables named
  **`<label>_l2`** (`t3_gfx_l2` … `t45_dy_l2`, same address and count as level 1's rows, tested).
  **`spawn_l2` is a commented row**: today's cellmasks.py (SW_MAX 32) makes masks for every level that
  lists both `spawn_` and `hz_`, and would fail mkrom.py on level 2's 40 entries.

### Checks (exact commands, results)
- `make -n msx` parses; the four level-2 commands it prints, run from the repo root
  (`$IMPL/s6/l2_recipe.sh`, log `l2_recipe.log`): rc 0. Palette C `000 432 455 344 333 000 111 234 222
  555 210 015 100 012 500 630`, mean ΔE C 2.417 ≤ A 2.501; `build/msx/level2`: 50 × 160, 461 offsets
  (460 tiles), 511 tiles; `.map` 16,000, `.atrp` 4,016, `.otile` 1,024, `.atr2` 320, `.til` 65,408;
  mapcells: "level 2: 289 cells … (146 in even rows, 143 in odd ones; 255 a pool), 8 attribute values
  (0 not in the map; 16 codes, 8 free)", "vats: 7 vats, 604 cells in 103 columns (outside the pools),
  37 tile offsets, attributes 0, every column one look"; preview "0 cells differ from the remap".
  Every output equals the map report's `out/conv` run byte for byte.
- Vat geometry against the data: the map holds vat words in exactly the 604 modelled cells, none
  outside, none in any vat's surrounding ring.
- build/msx and build/ram hashed before and after (`$IMPL/s6/hash_before.txt`, `hash_after.txt`, 241
  → 252 files): only 11 new files (`level2.{atr,atr2,atrp,map,otile,pal,png,remap,til,vram}`,
  `level2_amiga_vs_msx.png`), no existing file changed.
- Level 1: `python3 -I tools/mapcells.py build/ram/level1_full.bin analysis/amiga_tables.tsv
  build/msx/level1.atrp 160 51` prints the same bytes as HEAD's tool (438 cells, 213/225, rc 0).
- ROM unchanged: a worktree of HEAD 8b1ca1e (build/ram copied, since removed), `SRC=$WT sh
  tools/bstest/build.sh $IMPL/s6/romA/rc2.rom` and again with my TSV + mapcells.py (`romB`): both
  "build OK", 12 known warnings; A = B = `$IMPL/base/R/prod/rc2.rom` (sha256 31e09590d52dee35…); gen/
  differs only in `at_l2.inc`, which nothing includes (grep).
- Negative controls (`$IMPL/s6/neg`): T0 address +2 → "no look of the tables" rc 1; hz_l2 +2 → stops
  ("a vat of 4057 x 1298 cells") rc 1; a vat cell with attribute 1 → rc 1; a short `.otile` → rc 1.
- `python3 -I -m unittest discover -s tests -p test_level2_data.py`: 15 OK (synthetic rule, checks,
  Lab, vat geometry; the TSV rows against the image's lists; the conversion in a temp dir).
  `test_tools.py`: the 4 known failures only. `make test` (shared tree, `$IMPL/s6/make_test.log`): 246
  tests, the 4 known + **1 not mine**: `test_msxtune …test_nothing_of_the_tunes_in_the_fixed_area_but_
  fx_tk_operand` fails on step 4's uncommitted `msx/rc2.asm` (a comment now follows `include
  "rowtab.inc"`; HEAD's rc2.asm passes the test's pattern).
- Pictures looked at: the whole preview and 2× crops (`$IMPL/s6/crops`: sky, vat0, top): the skyline's
  two blues stay apart; vats, mines, crates and lifts match the original; the differences are the
  grade and the vats' liquid / bricks 310 → 100 (redder, default 16, for the user's eye).

### Open issues
1. **`spawn_l2`**: uncomment its row in `analysis/amiga_tables.tsv` in the same commit that makes
   cellmasks.py take 40 entries (step 5, else step 7). `test_level2_data.py` fails if it is listed
   while `cellmasks.SW_MAX` < 40.
2. **The `_l2` copies**: step 5's `gen/lvshared_l2.asm` must also rename lvshared.asm's references to
   the 15 shared tables (`t3_gfx` → `t3_gfx_l2`, …), not only the labels it defines.
3. mapcells' level-2 check runs in the Makefile (`make msx`); step 7 may also run it from mkrom.py
   (`build/ram/level2_full.bin`, `level2.atrp`, 160, 50, `--level 2`).
4. Step 13: `mapcells.vats()` + `column_look()` give each of the 103 vat columns' static look (the
   `vat_shown` start table).
5. msxconv.py's print still says "432 VRAM slots" (the step owned its docstring only).
6. `make test`'s fifth failure belongs to step 4 (its test pattern or its comment).

## Step 2: the bench in the repository (2026-10-28)

**Done.** Commit **d36f6c4** (7 files, explicit paths): `tools/amigaemu.py` (`game --level 2`:
`Level2Bench`, `--carry`, `--pre-poke`, `--flow`, `--stop-at-end`, `--report`; `GameBench.code_blocks`,
`CODE_BLOCKS_L2`), `tools/amigacov.py` (`--level 2`, `--carry`, scenario `level2`; run parts `poke=`,
`frames=`), `tools/tracecmp.py` (`--fields`), `analysis/amiga_ram_l2.tsv` (1,022 fields), `tools/l2drives.py`
(new), `tools/l2mock.py` (new), `tests/test_level2_bench.py` (new, 15 tests). Not committed: `build/emu/l2_*`
(16 references, 12 drives). Scratch: `$IMPL/s2` (event lists `ev_*.txt`, the risk-8 probe `kill2.py`).

### Bench: what the MSX agents need (no need to read BENCH2.md)

`PY=~/.venvs/msxports/bin/python` (Unicorn). All from the repository's root.

**The references** (already made in `build/emu`; remake or check them any time):

```sh
python3 -I tools/l2drives.py make            # the 12 drives build/emu/l2_<drive>.drive (+ .args), stdlib
python3 -I tools/l2drives.py refs --jobs 4    # the 16 references (runs $PY), ~2 min; ends "references: 16 of 16 as expected"
python3 -I tools/l2drives.py check           # rows and sha256 prefixes of what is in build/emu
python3 -I tools/l2drives.py list            # the table below
$PY -I tools/l2drives.py events end [--every 25]   # a reference's events frame by frame (spawns, kills, shots, ...)
```

`refs` runs, for each reference (a direct start; the carry decides lives, credits and the rating):

```sh
$PY -I tools/amigaemu.py game --level 2 --carry 10050:2:0:good --gframes 300 --drive build/emu/l2_end.drive \
    --stop-at-end --trace build/emu/l2_end_ram.jsonl --trace-ram
# the flow reference: level 1 (drive_end), Brainstorm (pz_fail) and the range (fr_good) played first
$PY -I tools/amigaemu.py game --level 2 --flow build/emu/drive_end.txt:build/emu/pz_fail.drive:build/emu/fr_good.drive \
    --gframes 300 --drive build/emu/l2_end.drive --stop-at-end --trace build/emu/l2_flow_l2_end_ram.jsonl --trace-ram \
    --report build/emu/l2_flow_l2_end.json
```

| Reference (`build/emu/l2_<ref>_ram.jsonl`) | Drive | `--carry` | `--gframes` | Rows = the MSX job's n | sha256 (16) | MSX build |
|---|---|---|---:|---:|---|---|
| `end` | `l2_end` | 10050:2:0:good | 300 | 259 | e0ecb97c30288d6d | `l2` |
| `tour` | `l2_tour` | 10050:2:0:good | 3000 | 2654 | d0ef114623da05c8 | `l2` |
| `lift` | `l2_lift` | 10050:2:0:good | 800 | 801 | 978d9cc7dec76d65 | `l2` |
| `trolley` | `l2_trolley` | 10050:2:0:good | 640 | 641 | 8b93c3bd428166f4 | `l2` |
| `trolley_sharp` | `l2_trolley` | 10050:2:0:sharp | 640 | 641 | 3c810e16ee4d22eb | `l2s` |
| `trolley_fair` | `l2_trolley` | 10050:2:0:fair | 640 | 641 | 9e608b5a5255c74f | `l2f` |
| `trolley_poor` | `l2_trolley` | 10050:2:0:poor | 640 | 641 | ba9dbf04d18c70e0 | `l2p` |
| `vat` | `l2_vat` | 10050:2:0:good | 700 | 701 | 05a3aacea265b2c4 | `l2` |
| `cont` | `l2_cont` | 0:0:1:good | 300 | 301 | 02692c53cc6458c7 | `l2c` |
| `over` | `l2_over` | 0:0:0:good | 300 | 109 | 3d3f211d54e83db7 | `l2o` |
| `fuzz` | `l2_fuzz` | 10050:2:0:good | 2500 | 2501 | 8bdc1c303d6c7742 | `l2` |
| `flow_l2_end` | `l2_end` | (`--flow`) | 300 | 259 | e65540af1e959526 | product, `rc2_l2_arm` |
| **`barrel`** (new) | `l2_barrel` | 10050:2:0:good | 900 | 901 | 2c4aebed5e969225 | `l2` |
| **`mine`** (new) | `l2_mine` | 10050:2:0:good | 160 | 161 | 3cab181fb43ca28b | `l2` |
| **`t1left`** (new) | `l2_t1left` | 10050:2:0:good | 340 | 341 | 1f00278095ce9e64 | `l2` |
| **`drone`** (new) | `l2_drone` | 10050:2:0:good | 400 | 401 | 533db1ac622378fa | `l2` |

The flow reference's file is `build/emu/l2_flow_l2_end_ram.jsonl` (the plan's `flow_l2_end`; new build/emu
files start with `l2_`), not BENCH2's `flow_l2_end_ram.jsonl`.

**The MSX side** (step 7 makes `LV_TEST`, `LV_CARRY`, `hz_l2`, `rc2_l2_arm`; nothing of it exists yet):
- builds (plan 4.1, rating 0-3 = SHARP-POOR): `sh tools/bstest/build.sh W/R/l2/rc2_l2.rom EXTJOY=1 ENEMY_CAP=0
  DAMAGE_X=1 LV_TEST=2` (`LV_CARRY` default `10050:2:0:1`); `l2s` `LV_CARRY=10050:2:0:0`, `l2f` `:2`, `l2p` `:3`,
  `l2o` `LV_CARRY=0:0:0:1`, `l2c` `LV_CARRY=0:0:1:1` (each `W/R/<b>/rc2_<b>.rom`, its `.labels` beside it).
- one job (unchanged Tcl, `tools/openmsx_rc2.tcl`): `rc2_drive_rom ROM LABELS OUT N 0 build/emu/l2_<drive>.drive`
  with N = the table's rows; the trace lands in OUT (`W/O/l2/l2_<job>.txt`): one line a tick, five hex blocks
  (D000h AM 0BECh bytes, DC00h AG, DD00h-DFFFh, EE00h-F0FFh, E900h-E9FFh). `hz_l2` (step 7) chains the jobs
  as BENCH2 7.2 lists them; add `barrel`, `mine`, `t1left`, `drone` (build `l2`, C-BIOS_MSX2).
- the homes the port must keep (they are in the dumps; `analysis/amiga_ram_l2.tsv`): spawn list DD80h-DFAFh
  (+ end word DFB0h), `vat_phase` **DFB2h** (22 words compared; the port keeps 23, DFB2h-DFDFh), object list
  EE00h-F00Fh, special records E900h-E995h, `marker_ptr` DD08h (pointer field `c5ec:mk_tab2`),
  `obj06_countdown` = `barrel_gap` DD1Ah, `diff_table` = `ac_diff` DD0Ch (pointer field `c716:diff_tab`),
  `continues` AG `$805E`. The ROM's labels must hold `mk_tab2` and `diff_tab`.

**The compare** (`--fields` selects level 2's set; without it tracecmp uses level 1's 948 fields):

```sh
python3 -I tools/tracecmp.py --ram --fields analysis/amiga_ram_l2.tsv --labels W/R/l2/rc2_l2.labels \
    build/emu/l2_end_ram.jsonl W/O/l2/l2_end.txt
# 259 game frames compared (259 Amiga, 259 MSX), 1022 fields: 0 differ        (exit 0)
```

A difference prints up to `--show` (10) lines `game frame N (keys): field amiga/msx, ...` before the count
line `... 1022 fields: K differ` (exit 1). A trace shorter than its reference compares its own rows only:
check that the counts in brackets are equal.

**The mock** (a self-test without an emulator: the MSX trace a perfect port would give):

```sh
python3 -I tools/l2mock.py build/emu/l2_end_ram.jsonl W/mock/end.txt          # + W/mock/end.txt.labels
python3 -I tools/tracecmp.py --ram --fields analysis/amiga_ram_l2.tsv --labels W/mock/end.txt.labels \
    build/emu/l2_end_ram.jsonl W/mock/end.txt                                  # 0 differ
python3 -I tools/l2mock.py build/emu/l2_trolley_poor_ram.jsonl W/mock/s.txt --mutate diff_table:0:0x9000   # 641 differ
python3 -I tools/l2mock.py build/emu/l2_tour_ram.jsonl W/mock/v.txt --mutate 'vat_phase[3].0:700:0x4242'   # 1954 differ
```

### The new drives and their events (`$PY -I tools/l2drives.py events <ref>`)
- `barrel` (tele (300, 440) at 10: the left stairs, y 464; fire every 4th frame, facing right; energy poked):
  type 6 launches at 12, 64, 108 ...; 84 bounces; `$D1DC` 2 -> 1 -> 0 waits (34); **17 kills** at 99 ... 835
  (`$15F2` 1-17); pickups 24h at kills 4, 8, 12 (frames 247, 419, 607) and 1Ch at 16 (795); no launch after
  the 16th (the 17th was in flight).
- `mine` (tele (1190, 130) at 10, right 66-79): object 0 (the mine at x 1184) stepped on at 76, 77, 78, 79, 80
  (RoboCop in its cell 5 frames: 4 explosions each, x 1200/1220/1240/1260, y 144); its words +4 -> FF04 (77),
  +2 look 0 -> 4 (78) -> 8 (80) -> FF08 off (81); RoboCop falls through (y 160 -> 240).
- `t1left` (tele 1:(620, 430) spawns entry 11 at the screen's edge, then 8 teleports follow it): type 1 fires
  facing left with D6 = 0, D7 = 10h at 2, 16, 18, 64, 66, 80, 82, 192, 194, 208, 210, 272, 274, 320, 322;
  turns at x 319 (118, D6 0) and **at x 931 to the left on a fire frame (272, D6 0)**.
- `drone` (tele (1600, 150) at 10, fire every 4th frame from 66): drones from (1664, 16) and (1504, 16) at 11;
  touch at 65 and 225 (energy - 18h, explosion via `$E7AA`); **shot down at 84 and 272: `$C35A` entered with
  D5 = 0198h** (Q7), then `spawn_explosion` (`$F366`) called from `$C436` with D5 = 0, at (1667, 118) and
  (1675, 118).

### Findings for later steps [V: bench]
1. **Q2: the upward missile (D6 = 2) does not occur in level 2.** `$EF42` leaves D6 = 2 only on a turn at a
   wall above the walkway; both type-1 walkways end at edges (entry 10: x 271-531; entry 11: x 319-931), where
   it leaves D6 = 0; no other source of type 1. Every left-facing fire is bullet type 0 (slot written, no
   bullet). `walk_d6` stays the faithful port (step 9), but its 2 branch has no trace.
2. **Q7**: D5 = 0198h at `$C35A` confirmed; the explosion it spawns is a normal type 0 (D5 = 0 at `$F366`),
   so the garbage frames E6h-41h are not read in these kills.
3. **Risk 8 tried: no kill.** `$IMPL/s2/kill2.py` (scratch): weapons 2 (three-way) and 3 (scatter) poked
   with ammo, on the roof at x 296-347 firing every 2, 3 or 4 frames (108 runs, 300 frames), and weapons 1-3
   walking in from x 200, 260, 300 while firing (18 runs): at most **3 hits in one frame** (one shot's three
   bullets), `$C2D8` never reached; walking in ends in the arrest. No `kill2` drive (Q1 kept as a quirk).
4. A type-6 kill that drops a pickup (`$F98C`) spawns its explosion **at y 0** (D1 clobbered): frames 247,
   419, 607, 795 of `barrel` (`death_c33e`, step 9).
5. act_0c triggers on every frame RoboCop is in the cell (5 x 4 explosion requests in `mine`).
6. Inputs are ignored for ~65 frames after a level-2 start (the start sequence locks the controls).

### Checks (exact commands, results)
- Level 1 unchanged: `$PY -I tools/amigaemu.py game --gframes 600 --drive build/emu/drive_cov1.txt --trace
  O/l1_600.jsonl --trace-ram` before and after the patch: 601 rows, `head -601 build/emu/trace_cov1_ram.jsonl |
  cmp - O/l1_600.jsonl` identical both times (`$IMPL/s2/modes.sh before|after`, stdout identical too).
- puzl and frng unchanged: `puzl --pframes 2000 --drive build/emu/pz_fail.drive`, `frng --fframes 3000 --drive
  build/emu/fr_good.drive`, `frng --level 2 --ram build/ram/level2_full.bin --fframes 3000 --drive
  build/emu/fr_armed2.drive` (all `--trace X --trace-ram`): identical before/after and to build/emu's
  `pz_fail_ram`, `fr_good_ram`, `fr_armed2_ram.jsonl`; `amigacov.py` level 1 (`--gframes 300`, two runs):
  JSON identical before/after.
- `python3 -I tools/l2drives.py make --out $IMPL/s2/refs`: the 8 old drives and `.args` byte-identical to the
  bench report's `ref/`. `l2drives.py refs` (scratch, then build/emu): **references: 16 of 16 as expected**
  both times (the 12 of plan 4.1 and the 4 new, equal on the rerun).
- Mock: all 16 references `... 1022 fields: 0 differ`; `--mutate diff_table:0:0x9000` on `trolley_poor`:
  `641 differ` (`diff_table 0x18/0x0`); `--mutate 'vat_phase[3].0:700:0x4242'` on `tour`: `1954 differ`.
- tracecmp's level-1 default on the base's MSX traces: `tracecmp.py --ram build/emu/trace_cov1_ram.jsonl
  $IMPL/base/O/trace/cov1.txt --labels $IMPL/base/R/trace/rc2_ext5.labels`: 4401, 948 fields, 0 differ;
  cov0_tr: 1400, 0 differ.
- `$PY -I tools/amigacov.py --level 2 --carry 0:2:0:good --scenario level2 $IMPL/s2/cov2_scen.json` (12 min):
  1,480 blocks, 290 code-area addresses, 214 BOB frames, the 15 types with the same highest hit points and the
  14 messages, all equal to the bench report's three runs; the 7 vats run.
- `python3 -I -m unittest discover -s tests -p test_level2_bench.py`: 15 OK (4 skipped without Unicorn);
  with `$PY`: 15 OK. `make test`: 261 tests, only the 4 known failures.

### Open issues
1. `hz_l2` and `rc2_l2_arm` (step 7) are BENCH2's untested proposals; `hz_l2` should gain the 4 new jobs.
2. `cont` and `over` need the port's continue and game-over flows reading `ext_joy` (steps 19).
3. amigacov `--level 2` defaults to the carry `10050:2:0:good`; the bench report's coverage used `0:2:0:good`
   (pass `--carry 0:2:0:good` to compare with it).
4. The findings above belong in `docs/AMIGA_ANALYSIS.md` (step 1's file: not edited here).

## Steps 3 and 4: the SHARP set into ng_go, one level start (level 1 only) (2026-10-28)

**Done.** Commits **d3ddbeb** (step 3) and **c726025** (step 4). Records in `$IMPL/s3` and `$IMPL/s4`
(`s4/W`: step 4's whole l2base run, kept; the other runs keep only their logs).

### What was built
- Step 3 (`msx/objects.asm`, `msx/rc2.asm`): `ld hl,diff_tab / ld (ac_diff),hl` left `obj_start`; a new
  game sets SHARP; `level_restart` (and later `lv_go` for level 2, `lv_cont`) keeps `ac_diff`.
- Step 4 (`msx/{bob,cold,diag,field,front,hits,logic,msx,music,objects,player,rc2,scroll9938,scroll9958,sound,tiles}.asm|inc`, `tools/mkrom.py`):
  - `gen/levels.inc` (mkrom, in FRONT): `lv_desc` = level 1's descriptor (symbolic: `db BANK_L1, BANK_TILES,
    BANK_MAP, MAP_ROWS, ATR_BANK / dw ATR_PACKED-3840 / db LEVEL_BANK, FIELD_IMG_BANK, DYN_Y / dw LVL_X,
    LVL_Y, LVL_YMAX, CAM_Y_MAX, MAP_ROWS*16, lv_pal1, lv_voffy1`), then `lv_pal1` (level1_grade.pal) and
    `lv_voffy1` (43 B). `ds LV_SIZE - ($ - lv_desc)` errors when the fields outgrow LV_SIZE.
  - `msx.inc`: `lv_cur` F1A0h, LV_SIZE 24 (34 at most): `lv_logic +0, lv_tiles +1, lv_mapb +2, lv_rows +3,
    lv_atr +4, lv_atrn +5 (w), lv_tab +7, lv_fimg +8, lv_dyn +9, lv_x +10, lv_y +12, lv_ymax +14,
    lv_camy +16, lv_maph +18, lv_palp +20, lv_voffp +22`; `lv_vram` F1C2h; `lv_pal` C68Ah (32),
    `lv_voffy` C6AAh (LV_VOFFN 43). A level-2 descriptor = the same fields in the same order after
    level 1's (lv_copy indexes `lv_desc + LV_SIZE * C`); its palette/view_offy pointers may point into
    FRONT or into its `lv_tab` bank (lv_copy maps lv_tab at A000h while it copies).
  - `rowtab.inc`: bank bytes relative (0-2); `get_tile` adds `(lv_mapb)`. `view_offy` left rowtab.inc
    (now in levels.inc); `view_offx`, `atr_rows`, `rowtab` stay in the fixed area.
  - `cold.asm`: `cold_init` (the whole power-on init after the slot set-up, DIAG probes included;
    `lv_copy` with C = 0 before `vdp_setup`; `lv_vram` = 0 after it), `ng_init` (R800PING's ping, AG,
    two lives, SHARP, C = 0, falls into `lv_select`), `lv_select` (C = level: lv_copy; tiles_upload E=4 +
    field_upload only when `lv_vram` != C; tiles_init, atr_load, pl_init, lvl_bank = lv_logic,
    lv_fresh = FFh), `lv_copy`; pl_init/atr_load/tiles_upload/vdp_setup read lv_cur/lv_pal.
  - `rc2.asm`: `init` ends `ld hl,cold_init / jp front_call`; `new_game: call dsp_off`; `ng_go: ld hl,ng_init /
    jr lv_gs`; **`lv_go: ld c,a / ld hl,lv_select / lv_gs: call front_call`**, then obj_start, ao_start,
    engines_init, hud_init, display_on as before (step 18: `lv_next` = dsp_off, `ld a,(AG+8050h)`,
    `jp lv_go`; hud_lvl instead of hud_init for level 2 is still to add); `title` = `ld hl,fr_title /
    jp front_call` (front.asm `fr_title`: front_title, front_done, tiles_upload E=4); `dsp_off` shared
    with level_restart; `palette` gone from the fixed area.
  - Readers: atr_rc/ar_after/atr_new/ttp_prep/dt_prep `lv_rows`; map_write/ar_after/bf_fid `lv_tab`;
    tc_upload/tiles_upload `lv_tiles`; field_upload `lv_fimg`; field.asm dyn slot `lv_dyn` (page 3:
    step 13 must add the page for level 2's page-2 slot: `fbb_sy` writes SY's high byte 3, `fdy_ln`
    computes 18000h + line*128), `FB_MAPH` -> `lv_maph`; pl_view `lv_voffy`, `lv_camy`; pal_fade and
    pal_robo `lv_pal`; map_cell/map_atr/cell_solid `cp 51`. `TC_SLOTS` untouched (step 13's).
- **Deviations** (recorded choices):
  1. Default 14's alternative: page 2 and the atlas are uploaded only when VRAM holds another level's
     (`lv_vram`). Measured: the upload at every start adds 0.37 s of black screen to every level-1
     start and shifted more of the base's records (`s4/W_upl/l2base_check.log`). Step 19's `lv_cont`
     must set `lv_vram` = FFh before `lv_go` (PIC9 overwrote page 2); `lv_next` and a new game after
     level 2 upload by themselves (the level changes).
  2. Level 1's palette left the fixed area (plan 3.1 kept it there): FRONT `lv_pal1`, vdp_setup loads
     `lv_pal` (lv_copy runs before it). 32 B of the fixed area.
  3. The whole init after the slot set-up moved to FRONT (3.2 named only its tail): every callee
     leaves act_8000 (FRONT) mapped; `jp c,no_ram` keeps the same stack depth (cold_init is jumped to).
- A bug caught by step 3's own check during step 4 (fixed before the commit): atr_rc took the
  ar_after0 path with A = rows - 1 instead of the row (the rows after the map read 0): the marker scan
  diverged at frame 57 of `over`. Now `cp d / ld a,d / jr c,ar_after0`.

### Checks (exact commands, results)
- Builds: `sh tools/bstest/l2base.sh builds $IMPL/s3/W` and `... $IMPL/s4/W`: builds PASS (21 + 2 L).
  `python3 -I tools/bstest/romdiff.py $IMPL/base/R/prod/rc2.rom $IMPL/s4/W/R/prod/rc2.rom`: only banks
  0-9, 78, 88 (code) differ; the same for ROM_2M=1 and PZ_TEST=1 (variants): **the data banks unchanged**.
- `sh tools/bstest/variants.sh $IMPL/s4/variants`; `python3 -I tools/bstest/l2base.py banks
  $IMPL/s4/variants > $IMPL/s4/banks_variants.txt`: **39 of 41 build** (DEMO_HUD=1 fits again;
  DEMO_ACTORS=2/5 overflow by 18 B, 219 at the base). Fixed area free (base -> step 4): product 188 -> 389,
  PZ_TEST 158 -> 361, EXTJOY/trace 164 -> 354, LOCKSTEP 118 -> 308, EXTJOY+LOCKSTEP+PZ_TEST 88 -> 280,
  DIAG 44 -> 282, DIAG+PZ_TEST 14 -> **254 (the lowest)**, DEMO_HUD 167; every set that built at the
  base has >= 254 B: 3.2's 60-100 + 80-120 B for steps 14-15 fit everywhere. FRONT product 2,309 ->
  1,968 (text.inc as in build/msx), FIELD 1,529 -> 1,522, LC1 39 -> 45.
- `make test`: 261 tests, the 4 known failures only (one more had failed on my comment after
  `include "rowtab.inc"`: test_msxtune pins that line; fixed).
- Step 3's own checks (`$IMPL/s3/poke.tcl`, an hz_chain job: rc2_drive_rom on drive_over with
  breakpoints at new_game, level_restart, display_on; `s3p_setup ROM LABELS TRACE LOG`, done
  `[s3p_done]` or, with a game over and a new game after the trace, `[s3n_done]` with `::s3n_lab` set):
  - step 3 (`s3/poke.log`, `s3/pokeng.log`) and step 4 (`s4/pokeng.log`): power-on SHARP ok; ac_diff
    poked to +8 at both deaths' level_restart -> display_on sees 8 (survives); poked to +16 at the
    new game after the game over -> SHARP. The trace (poke undone at display_on) 0 differ:
    `python3 -I tools/tracecmp.py --ram --labels $IMPL/s4/W/R/trace/rc2_ext5.labels
    build/emu/trace_over_ram.jsonl $IMPL/s4/pokeng_trace.txt` -> 1,249 frames, 0 differ.
  - negative control: a969fc8's trace build (`s3/poke_base.log`): both deaths WRONG (0, obj_start reset it).
  - the flows after the range (regress): every new game `ac_diff - diff_tab 0` after the range's 24.
- The gate: MCP `source load.tcl; source l2base.tcl; hz_chain [concat [rgr_jobs W all] [l2b_jobs W]] W/all.done`
  then `sh tools/bstest/l2base.sh check W $IMPL/base`:
  - **step 3** (`s3/W/l2base_check.log`): everything PASS but the fresh title's `game_ram.bin` (3 bytes):
    `python3 -I $IMPL/s3/ramreloc.py base_game_ram.bin new_game_ram.bin BASE.labels NEW.labels` ->
    DD08h, DD0Ah, DD0Ch = pointers into LC1 moved by -6 with obj_start (mk_tab+6, mk_tab, diff_tab).
  - **step 4** (`s4/W/l2base_check.log`): PASS: level 1's traces (cov1 4,401, cov0 / cov0_tr 1,400;
    die 901, over 1,249, end 517: 0 differ), Brainstorm's 20 traces and records, the range's drives,
    screens, sound, the 2 MiB product, turbo R writes, the start check on m2/fx/tr (reg pal cmd cpu vbl
    tear 0, 0 bad, lost 0), the stills (10 pictures identical), LOCKSTEP (2,998 lists 0 differ both
    VDPs). FAIL, each a timing effect (below): the fresh title's polled game record (tick 302 instead
    of 300), the titles after the f1 and kb_tr flows (R#5 CF/C7), field 860_fx (6 pictures, 183 px;
    860_m2 now 0, base 3), the effects (write for write).
- **Timing-only control** (`$IMPL/s4/nc`: a worktree of d3ddbeb + pure delays: 13 T in get_tile, 14 T
  in atr_rc, 10 T in ttp_prep/dt_prep; `SRC=.../nc/wt LEVEL=<repo>/build/msx/level1 sh
  tools/bstest/l2base.sh builds $IMPL/s4/nc/W`, the same chain, check): the **same four verdicts fail**
  (plus the tr title's R#5), field 860_fx with the **same 6 pictures, 183 px** (`diff` of the two
  860_fx.check.txt: identical), effects shifted alike. So these verdicts fail on any change of level
  1's CPU time; step 4's results are of that kind:
  - fresh, exact (`$IMPL/s4/xfresh.tcl`: hz_fresh_setup + np_hf_step, the game at exactly tick 300;
    job `s4x_fresh_setup DIR TAG ROM LABELS` on Gradiente_Expert20_64K; records in `s4/xfresh`):
    title VRAM, registers, palette identical; `titlecmp2.py s4/xfresh base s4`: the music identical
    at every tick; game VRAM identical; game RAM: DD08h/DD0Ah/DD0Ch (relocated, ramreloc) and
    **D032h-D033h, $B32 (R-seeded): the plan's 4.4 exception**. The control: the same.
  - titles after the flows: R#8 = 0Ah on both (sprites off): `registers that show: identical`
    (regress.sh's unseen_regs rule); picture, palette, PSG writes identical (titlecmp2 PASS).
  - effects: `python3 -I $IMPL/s4/fxcmp.py $IMPL/base/l1/fx/fx_scc.txt $IMPL/s4/W/l1/fx/fx_scc.txt`:
    800 starts, the types identical in order, their effect-player ticks shifted by 0-3 (frames that
    redraw the whole view, engines_jump, take another VBLANK; LOCKSTEP pins frames, not the ticks
    inside them).
  - field 860_fx: the known hostage tear ("336 old, 59 new pixels", issue 3 of step 0) on other
    pictures; looked at `s4/tear/tear.png` (j007_f0043-45: the hostage on the bar beside RoboCop on
    the lift).

### Open issues
1. **The gate is timing-sensitive**: l2base's fresh (a polled record), the flows' titles (R#5),
   field-check counts per window and the effects (VBLANK keys) fail on any change of level 1's CPU
   time; steps 5, 7, 12-15 will all change it. Use the method above (a timing control, the exact
   fresh record, unseen_regs, fxcmp) or teach the harness: hz_fresh exact (np_hf_step), titles with
   unseen_regs, effects by starts, the field check on m2+fx together with the known tear classified.
2. **The hostage tear is a real pre-existing glitch** that moves between the V9938 and the V9958 with
   timing (v0.1.1: 3/6; base 3/0; step 4: 0/6). Milestone 2's field work should fix it (zero glitches).
3. A level start now costs ~5 ms more (lv_copy, front_call); level 1's VRAM uploads only at power-on,
   the title and the stages' exits, as before.
4. The fixed area: 254 B in DIAG+PZ_TEST builds. 3.2's steps 14-15 (<= 220 B) fit; with the flow's
   ~60 B (steps 18-19) the DIAG+PZ_TEST set would run out first if every estimate hits its top: the
   DIAG builds' dg_probe/dg_rec (fixed, ~45 B) could move to BANK_MUSIC then (mus_call keeps B).
5. Descriptor fields still missing for level 2: LV_TCN (TC_SLOTS, step 13), LV_FLINES, the sprite
   fields (step 12); `hud_lvl` (step 18). `level1.asm` keeps its own `cp MAP_ROWS` (t23c, level 1's code).
6. Scratch tools (not committed): `s3/poke.tcl`, `s3/ramreloc.py`, `s4/xfresh.tcl`, `s4/fxcmp.py`.

## Step 5: the logic's level constants, level 1 only (2026-10-28)

**Done.** Commit **e0399d4**. Records in `$IMPL/s5`: `W` (the whole l2base run, kept: 1.9 GB), `logic` (the
logic traces), `xfresh` (the exact fresh record), the scripts `s5logic.tcl` (the logic jobs),
`msxcmp.py` (two MSX traces of two builds, field by field), `l2dry.py` (the level-2 dry run), and
`variants.log`, `banks_variants.txt`, `make_test2.log`.

### What was built
- **The level header** (`msx/objects.asm` equates, `msx/level1.asm` values): after `lv_htab` (53 x 4),
  `lv_init` (jp), `lv_tick` (jp), `lv_hz` (dw) come `lv_swn1` (db SW_N - 1), `lv_swlast` (dw
  spawn_ram + 14 (SW_N - 1)), `lv_hzxn`, `lv_hzyn` (db), `lv_hzxm`, `lv_hzym`, `lv_hzall` (dw: the
  hazards' masks, which `special.asm` used to name directly), then `lv_noten` (code, 9 bytes at most:
  level 1's `cp 32 / ret z / cp 44 / ret z / cp 45 / ret`), `LV_HDR_END` = A0F0h. `ds FIELD - $`
  lines in `level1.asm` stop the build when the header drifts from the equates.
- **`msx/lvshared.asm`** (new; `level1.asm` includes it right after the header, at A0F0h): `sw_ptr`
  (now SW_MAX = 40 entries, level-independent, moved out of `cells_l1.inc`), the shortcuts `sw_prep`
  ... `sw_bits` (5-byte masks: one more key byte, `ld bc,SW_MB`, a cell x 5, `cp SW_MAX`, 5 bytes
  cleared, `and 7`), `t3`, `t_xy`, `t_face`, `t_col`, `t_word`, `t12`, `t13`, `t45`, `t4`, `t15`,
  `t30`, `t31` moved verbatim (`level1.asm` keeps `l1_init`, `lt0`, `t23-t29`, `t32`, `t44`).
- **Design choice (recorded): the shared code at fixed addresses.** `objects.asm` (LC1) calls
  `sw_prep`, `sw_dset`, `sw_dclr` and reads `sw_ptr`; `special.asm` (LC3) calls `sw_cell`. These
  calls are assembled once, so level 2's copies must sit at the same addresses: every level bank
  has the same header and includes its lvshared copy right after it; the copy assembles to the same
  bytes but its level-data operands. `tools/mkrom.py lvshared_check` fails the build when a copy's
  label differs from level 1's. No jump vectors: 0 T more per call.
- **`tools/mkrom.py`**: `gen/lvshared_l2.asm` (`lvshared_copy`: every label `lvshared.asm` defines,
  plus every name of the level's own data it uses, i.e. defined in `gen/at_l1.inc` or
  `gen/cells_l1.inc`, gets `_l2`; comments kept; quotes refused), `lvshared_check` after z80asm.
- **`tools/cellmasks.py`**: SW_MAX 40, SW_MB 5 (masks 5 bytes), `sw_ptr` no longer written, level 1's
  names plain and other levels' suffixed (`SW_N_l2`, `sw_xm_l2`, `hz_all_l2`, ...), two `ds` lines
  that stop the build unless `msx.inc`'s SW_MB is the table's. Level 1's masks: the old 4 bytes + a
  0 byte (checked).
- **`msx/objects.asm`**: `uf_last` reads `lv_swlast`/`lv_swn1`; `uo_cap` and `uo_free` call
  `lv_noten` directly (`not_enemy` removed).
- **`msx/special.asm`**: `hz_update` sets `vat_cut_line` = CAh first (`$9150`'s `move.b
  #$CA,$10356`), reads `lv_hzxn/yn/xm/ym/all`; `sp_update` dispatches handler 4 to `sp_trolley`
  (a `ret` stub until step 8); the rest shortcut needs no handler test (only `sp_lift` sets
  `sp_rest`).
- **`msx/mapobj.asm`**: `ao_acts` entry 3 = `act_0c`, a label on `ao_look` (LC2's bytes unchanged).
- **`msx/msx.inc`**: `barrel_gap` DD1Ah; `SW_MAX` 40, `SW_MB` 5; repack `sw_list` DD20h (41),
  `sw_dirty` DD49h (5), `sw_key` DD4Eh (7), `sw_lp` DD55h, `sw_k` DD57h, `sw_ci` DD58h, `sw_bc`
  DD59h, `sw_tchg` DD5Bh, `sw_px` DD5Ch (sp_rest stays DD60h); `vat_phase` DFB2h (46);
  `vat_shown` F012h (103), `vat_disp` F079h (103), `vat_chg` F0E0h (7); `vat_cut_line` CE42h;
  `pz_tvb` C6AAh (Brainstorm's, over `lv_voffy`, as the plan says); `fo_cont` C6F0h; the free-RAM
  audit comment updated (also `lv_cur`'s F1A0h, which step 4 left listed as free).
- Also: `tools/msxprof.py` names BANK_L1 PCs from `lvshared.asm` too; `tests/test_tools.py` (5-byte
  masks, the suffixed names, SW_MAX/SW_MB = msx.inc's; `lvshared_copy`/`lvshared_check`);
  `docs/MSX_ARCHITECTURE.md` (the shortcuts' paragraph, the level bank); `docs/HARNESS.md` 3 (the
  relocation drive).
- **For step 7** (level 2's bank): `level2.asm` = `lv_htab_l2`, `jp l2_init`, `jp lt1`, `dw hz_l2`,
  `ds lv_swn1 - $`, `db SW_N_l2 - 1`, `dw spawn_ram + 14 * (SW_N_l2 - 1)`, `db HZ_XN_l2, HZ_YN_l2`,
  `dw hz_xm_l2, hz_ym_l2, hz_all_l2`, `ds lv_noten - $`, `cp 45 / ret` (default 25), `ds LV_HDR_END
  - $`, `include "lvshared_l2.asm"`, then its own code, `at_l2.inc`, `cells_l2.inc`.
  `analysis/amiga_tables.tsv` needs bank-`l2` rows for the shared handlers' tables under `_l2` names
  (the copy references 15: `t3_gfx_l2 t3_size_l2 t4_gx_l2 t4_gy_l2 t4_tgfx_l2 t4_tsize_l2 t4_tx_l2
  t4_ty_l2 t12_dx_l2 t12_gfx_l2 t12_mx_l2 t12_my_l2 t30_dy_l2 t45_dy_l2 t45_gfx_l2`, the same Amiga
  addresses as level 1's rows) and `spawn_l2` uncommented (cellmasks then writes `cells_l2.inc`).
  The dry run `$S/l2dry/dry.py` shows it works: a dummy level-2 bank (level 1's data suffixed)
  after BANK_L1 assembles, its 44 lvshared labels at level 1's addresses, the only differing bytes
  19 operand words, each a level-1 data name -> its `_l2` copy.

### Checks (exact commands, results)
- Builds: `sh tools/bstest/l2base.sh builds $IMPL/s5/W`: builds PASS (21 + 2 L). The final tree rebuilt
  (`build.sh` into `<scratch>/s5/b3`): product 06774c62cd5d86cd, trace d19578163af1f537, ext
  d08cee4760d0e45d, byte-identical to the gate's. 12 known z80asm warnings, 0 other.
- `python3 -I tools/bstest/romdiff.py $IMPL/s4/W/R/prod/rc2.rom $IMPL/s5/W/R/prod/rc2.rom`: banks 0, 1,
  2 (LC1), 4 (L1), 5 (LC3), 7 (FRONT), 88 (FRNG) differ; `relocheck.py ... 0 1`: PASS (12 relocated
  words); banks 7 and 88: relocated words, FRONT's one "not a label word" is `diff_tab + 24`
  (front_range's rating 3) moved by -8 with LC1; LC2 (3) and every data bank unchanged.
- Free bytes (`l2base.py banks`; product): fixed 389 (= step 4), **LC1 53** (step 4 45, base 39: -14 B
  against the base, -8 at this step; the plan's -11 assumed `not_enemy: jp lv_noten`, the callers now
  call `lv_noten` directly), L1 874 (984), LC3 5,086 (5,105), LC2 5,087, FRONT 1,968. Trace builds
  (ENEMY_CAP=0): LC1 153 (154). `sh tools/bstest/variants.sh <scratch>/s5/variants` +
  `l2base.py banks`: 39 of 41 build (DEMO_ACTORS=2/5 overflow by 18 B, as at step 4); the fixed
  area's free bytes equal step 4's in every set (lowest DIAG+PZ_TEST 254, product 389).
- Level 1 against the bench, MCP chain `hz_chain [s5_jobs O T X XB]` (`s5logic.tcl`), then
  `python3 -I tools/tracecmp.py --ram --labels .../trace/rc2_ext5.labels build/emu/trace_<d>_ram.jsonl
  O/<d>.txt`: cov1 4,401, cov0 1,400 (FS-A1FX), cov0_tr 1,400 (FS-A1GT), die 901, over 1,249, end 517:
  **0 differ** (948 fields). reloc 401: 7 differ (`player_hot_x/_y`, frames 193-199), the **same 7 on
  the base** a969fc8 (`reloc_base`) and step 5 = base field for field (`msxcmp.py`: 0 rows differ):
  a deliberate port deviation (`player.asm` `pl_frame` keeps the state's last frame record where the
  Amiga reads on), not this step's.
- The relocation drive is new (the old `drive_reloc_up` was lost): `python3 -I tools/drivejoy.py --joy
  110:300:u --tele 100:2072:320 --god build/emu/drive_reloc.txt` and `$PY -I tools/amigaemu.py game
  --gframes 400 --drive build/emu/drive_reloc.txt --trace build/emu/trace_reloc_ram.jsonl --trace-ram`
  (RoboCop relocated to (996, 640) at game frame 192); `docs/HARNESS.md` 3 lists it.
- The product configuration (EXTJOY=1: ENEMY_CAP 1, DAMAGE_X 3, the only builds that run `lv_noten`),
  this step's ext build against the base's (`$IMPL/base/R/ext`), C-BIOS_MSX2, `python3 -I msxcmp.py
  O/xb_<d>.txt BASE.labels O/x_<d>.txt NEW.labels <repo>`: cov1 4,401, cov0 1,400, over 1,249, reloc
  401: **0 rows differ** in the 948 fields; raw dumps differ only at DD08h/DD0Ah/DD0Ch (LC1 pointers
  relocated) and DD42h-DD5Dh (the repacked caches).
- The gate: MCP `source load.tcl; source l2base.tcl; l2b_chain W W/all.done` (226 jobs, 0 time outs,
  about 33 minutes), `sh tools/bstest/l2base.sh check $IMPL/s5/W $IMPL/base` (`s5/W/l2base_check_out.txt`):
  - PASS: the traces (regress's cov1/cov0/cov0_tr; die/over/end 0 differ), Brainstorm's 20 traces and
    records, the range's drives, screens, wanted state, display and sound, the 2 MiB product, turbo R
    writes 0, the flows' logic and text screens (`bonus check: PASS` everywhere), the start check
    m2/fx/tr (reg pal cmd cpu vbl tear 0, 26,649 / 26,127 / 31,505 sprite entries, 0 bad, lost 0),
    the stills (10 identical), LOCKSTEP (2,998 lists, 0 differ, both VDPs), the field check in 5 of 6
    windows (860_m2 = the base's 3 pictures).
  - FAIL, timing only (regress: 40 PASS, 5 FAIL), the families step 4 found:
    - the fresh title (`hz_fresh` polls: the game record at tick 302). Exact record
      (`$IMPL/s4/xfresh.tcl`, job `s4x_fresh_setup $IMPL/s5/xfresh s5 ROM LABELS`): title VRAM, registers,
      palette identical, `titlecmp2.py xfresh base s5` PASS (the music at every tick), game VRAM at tick 300
      identical, game RAM (`$IMPL/s3/ramreloc.py`): DD08h/DD0Ah/DD0Ch relocated, D032h-D033h ($B32,
      R-seeded: plan 4.4's exception), DD47h-DD5Dh the repacked caches holding the same values (sw_key's
      cells, sw_lp DD20h, sw_ci 1Bh, sw_bc, sw_px = sw_xm + cell 0 in both).
    - the titles after the flows ex, f1, tr and kb_ex: only R#5 CF/C7 (the SAT's parity), R#8 0Ah on
      both: `unseen_regs` "registers that show: identical (sprites off)"; picture, palette, PSG writes
      identical (step 4: f1 and kb_tr).
    - field 860_fx: 5 pictures, 124 px, every one "hostage torn" (336 old / 59 new, 287 / 2: the
      known pre-existing tear of step 0's issue 3), base 0, step 4 6 / 183.
    - effects: `python3 -I $IMPL/s4/fxcmp.py $IMPL/base/l1/fx/fx_scc.txt $IMPL/s5/W/l1/fx/fx_scc.txt`: 800
      starts, types identical in order, ticks shifted 0-4; the PSG writes as (register, value) sequences
      equal but 5 local reorderings of 3-5 writes (psg build; step 4: 7).
  - No timing-only control chain was run for this step (35 minutes): step 4's control showed that
    any change of level 1's CPU time fails exactly these verdicts; this step adds about 100-200 T a
    tick (sw_prep's fifth key byte, the hazards' header reads, vat_cut_line, the dispatch).
- `make test`: 262 tests, the 4 known failures only (`make_test2.log`); the new
  `test_lvshared_copy_renames_labels_and_level_data` and the cell-mask test (5 bytes, suffixed names,
  SW_MAX/SW_MB = msx.inc's) pass.
- The level-2 dry run (`python3 -I $IMPL/s5/l2dry.py <repo> <build>/gen <out>`): a dummy level-2 bank
  after BANK_L1 in a scratch rc2.asm: z80asm 0 errors, 44 of 44 lvshared labels at level 1's
  addresses, 19 differing operand words, each a level-1 data name -> its `_l2` copy.

### Open issues
1. **regress.sh cannot PASS literally while a step changes level 1's CPU time** (steps 7, 12-15 will):
   the four timing families above. A harness step should make them timing-blind before step 7's gate:
   the fresh record exact at tick 300 (np_hf_step) with ramreloc-like rules (relocated pointers, $B32,
   the port's caches), the titles' registers by `unseen_regs`, the effects by starts and write
   sequences, the field check with the known hostage tear classified (or fixed: zero glitches).
2. The hostage tear is real (step 0's issue 3, step 4's issue 2): it moved again (m2 3 = base, fx 5).
3. Step 7 must give level 2's header exactly level 1's layout (above) or `lvshared_check` stops the build;
   `lv_noten` fits 9 bytes (a longer one jumps out).
4. `pz_tvb` shares C6AAh with `lv_voffy` (the plan's choice): Brainstorm must set it at its start (step
   20), never before a level start; `vat_disp` and `vat_chg` overlap level 1's object list tail and the
   range's display (F080h-F0F9h): level 2's start must set them, `engines_init` clear `vat_disp` (step 14).
5. Scratch tools (not committed): `s5logic.tcl`, `msxcmp.py`, `l2dry.py` in `$IMPL/s5`.

## The gate made timing-blind (harness step, 2026-10-28)

**Done.** Commit **cdf5bb4** (`tools/bstest/fieldcheck.py`, `l2base.py`, `l2base.sh`, `l2base.tcl`,
`regress.sh`, `regress.tcl`, new `fxcmp.py`; `docs/HARNESS.md` 5.21 "The gate's timing-blind
verdicts", the file table, 5.19's counts). Records and scripts in `$IMPL/sg`. **The gate is used as
before** (THE ONE CHECK at the top, now 227 jobs) **and must pass literally**; the four families
that steps 3-5 passed by hand now pass by themselves on a change of level 1's CPU time:

| Family | Now |
|---|---|
| the title from power-on | new flows job `xfresh` (`regress.tcl rgr_xfresh_setup`) writes `W/fresh/xnew_*` with the game at exactly tick 300; `regress.sh` judges it with `l2base.py fresh` against `BASE/fresh/xbase_*` (title VRAM/registers/palette and game VRAM identical, music identical per tick, game RAM by variable: `l2base.py ram`). The polled `new_*` record is still made and only reported ("game_ram.bin: DIFFERENT (24 bytes)" is normal now) |
| the titles after the flows | `unseen_regs` (R#5/6/10/11 apart while both have the sprites off): "registers that show: identical (sprites off: R#5 CF/C7 apart)" |
| the field check | `fieldcheck.py` prints `CLASS picture kind [key] px=N`; `l2base.py field` accepts only `TEARS`' classes: the hostage at (785, 680), A `shown=4@785,680 newest=2@785,680+11@961,760` (59 px) and B `shown=2@785,680+11@961,760 newest=0@785,680` (2 px), window 860 only, at most 3 pictures a class and 6 pictures / 183 pixels a window and machine (the most of base, step 4, step 5) |
| the effects | `l2base.tcl`'s `pw_*` jobs also write `W/l1/fx/pw_K_sn.txt` (frames, starts, every sound tick's state); `fxcmp.py BASE NEW`: the same starts in the same order and LOCKSTEP frames, each effect's own sound exact from its start; `fxcmp.py --starts` on `fx_scc.txt`; the write logs reported ("not write for write the base's" is normal now) |

### What the next agents need
- **A FAIL is real now.** Read its lines: `l2base.py field` names a new class; `fxcmp.py` prints
  `DIFFER start K (effect E, frame F): SCC|PSG channel C, N sound ticks after the start: base X /
  new Y`; `l2base.py fresh` prints `DIFFER ADDR base / new` for the game's RAM.
- **RAM layout changes** (step 18 edits `msx.inc`): the by-name comparison follows moved and grown
  variables and relocated pointers (into code or RAM labels); a renamed or removed RAM variable in
  D000h-DFFFh fails ("its variable's name is gone"), and a new variable written during level 1 in
  what was free RAM fails in place. Judge such a FAIL, never widen the rule silently.
- **The hostage tear** is still a real level-1 glitch: when milestone 2's field work fixes it, empty
  `TEARS` (then any tear fails). If a later step tears it on a third frame change or for a 4th
  picture, that is above the bound: look at the pictures (`W/l1/field/860_*.png`), do not raise it.
- **The effects' tolerance** is the LOCKSTEP frame (24 VBLANKs): a start that leaves its frame fails.
  Step 21's `fxcheck.py` can read `pw_scc_sn.txt` (VBLANK-stamped starts and states) instead of
  `fx_scc.txt`.
- **Build HEAD from a worktree** when the shared tree holds another agent's uncommitted edits (it
  did: step 7's msx/ and mkrom.py changes enter a plain `l2base.sh builds`): `git worktree add
  --detach DIR <commit>`, `cp -R build/ram build/emu DIR/build/`, `build/msx` copied without
  ROMs/labels/PNGs/gen (`regress.sh base`'s cpio line), `ln -s <repo>/build/extracted DIR/build/`,
  then `cd DIR && sh tools/bstest/l2base.sh builds W`, the chain with `DIR/tools/bstest/load.tcl`,
  `cd DIR && sh tools/bstest/l2base.sh check W $IMPL/base`. `git worktree remove --force DIR` after.
- **The in-process MCP has ONE local target** for all agents of this process. At this step the
  step-7 agent held it (its chain in it, `$IMPL/s7/W/O/chain1.done`), so I ran a private MSX-AI MCP
  session: `$IMPL/sg/mcpd.py DIR` (background: spawns `/opt/homebrew/bin/msx-ai-mcp`, JSON-RPC over
  stdio, `msx_local_boot` cbios headless, then serves `DIR/req/*.tcl` through `msx_local_cmd`;
  `quit.tcl` shuts it down) and `$IMPL/sg/mx.sh NAME 'TCL'` (one command, prints the reply; its DIR is
  `$IMPL/sg/mcp`). Same tools, a second openMSX (2 in all). Deviation recorded: no shared target used.

### Checks (exact commands, results)
- HEAD's build: worktree `$IMPL/sg/wt` of e0399d4 + my 7 files; `cd $IMPL/sg/wt && sh
  tools/bstest/l2base.sh builds $IMPL/sg/W`: builds PASS; the 25 ROMs byte-identical to `$IMPL/s5/W`'s
  (step 5's gate builds); fixed area 389 B free in the product (= step 5: harness-only step).
- Chain (private MCP): `source {$IMPL/sg/wt/tools/bstest/load.tcl}; source {.../l2base.tcl}; l2b_chain
  {$IMPL/sg/W} {$IMPL/sg/W/all.done}`: 227 jobs, 0 time outs, 04:03-04:11 (8 minutes).
- `cd $IMPL/sg/wt && sh tools/bstest/l2base.sh check $IMPL/sg/W $IMPL/base`: **l2base: PASS**, exit 0
  (`$IMPL/sg/W/l2base_check.log`, `regress_check.log`): regress 45 PASS / 0 FAIL (fresh exact PASS:
  RAM 3,996 equal at their place, 19 moved, 5 bytes of relocated pointers DD08h/DD0Ah/DD0Ch/DD54h->DD5Ch,
  84 in place, 9 not compared DD53h DD58h-DD5Fh, 0 differ; titles ex/f1/tr/kb_ex R#5 CF/C7 apart,
  kb_tr identical); die/over/end 0 differ; start m2/fx/tr 0; field 860_m2 A 3 (177 px), 860_fx A 2 B 3
  (124 px), others 0; stills 10 identical; LOCKSTEP 2,998 lists 0 differ; effects: sess_fxlog's 800
  starts the same; scc build 803 starts in their frames (moves -1..+1), SCC 57,475 / PSG 33,390 sound
  ticks 0 differ; psg build 802 starts, PSG 33,393 ticks 0 differ.
- The timing-control set through the new verdicts (records in `$IMPL/sg`): field (`fc/`, the new
  fieldcheck on 860 of base/step 4/step 5) all PASS; exact fresh step 4, the delays build and step 5
  PASS (`l2base.py fresh $IMPL/s4/xfresh base s4 ...`, `... base nc ...`, `$IMPL/s5/xfresh base s5 ...`);
  effects (`fx_s4`, `fx_nc`, `fx_s5`: the `pw_*` jobs on their LOCKSTEP builds) all PASS, 0 differ.
- The base's new records: `xfresh` on the base product = `$IMPL/s5/xfresh/base_*` byte for byte ->
  `$IMPL/base/fresh/xbase_*`; the `pw_*` jobs on the base's builds reproduced `pw_*.txt` byte for byte
  -> `$IMPL/base/l1/fx/pw_{scc,psg}_sn.txt`. Every rerun of a `pw_*` job (base, step 4, step 5)
  reproduced its gate's `pw_*.txt` byte for byte (the logger changes nothing).
- Negative controls: `bash $IMPL/sg/neg2.sh $IMPL/sg/wt` (`$IMPL/sg/neg2.log`): **33 as expected, 0
  wrong**: 25 FAIL (exact title: title VRAM byte, R#7, game VRAM byte, RAM D100h, pointer DD08h moved,
  moved variable `sw_ci`, free RAM DFC0h, tick 302, a music tick; unseen_regs: R#7, R#2, R#5 with the
  sprites on; field: a new class, above the bound, an unexplained pixel, the tear in window 430, 50
  zeroed page lines re-checked by fieldcheck (8,431 px); effects: real ROMs with effect 4's first
  record changed run in openMSX (`$IMPL/sg/negfx`: SCC 383, PSG 363 starts differ), a start one frame
  late, another effect, a missing start (both builds), another `sess_fxlog` start), 8 PASS (the
  unmutated copies).
- `make test` in the worktree (HEAD + my files): 262 tests, the 4 known failures only (failures=3,
  errors=1; 44 skipped: 6 more than in the main tree, the ADF-based `Robocop2DiskTests`, which pass in
  the main tree: `python3 -I -m unittest discover -s tests -p test_tools.py -k Robocop2DiskTests` 6 OK);
  `test_bstest.py` 34 OK in both trees.
- Pictures looked at: the class-A tear (`$IMPL/s4/tear/tear.png`) and class B
  (`$IMPL/sg/tearB.png`: j008_f0004-08 of step 5's 860_fx): the hostage on the bar above RoboCop's lift.

### Open issues
1. The hostage tear (classes A, B) is a real pre-existing glitch, now classified and bounded, not
   fixed (milestone 2).
2. `fx_scc.txt` (sess_fxlog) is judged only by its starts; its ticks move with the CPU time. Its full
   check is step 21's fxcheck.
3. `$IMPL/base` has the exact title record and the effects' sound logs (added at this step); a new
   base made by `l2base.sh base W` gets both from its run (`xnew_*` copied to `xbase_*`); the range's
   base `4a8a61d` has neither, so `regress.sh check W <range base>` keeps the old polled title
   comparison.
4. The worktree `$IMPL/sg/wt` was removed after the commit; `$IMPL/sg/W` keeps its logs only.

## Step 10: the sprite tools for level 2 (2026-10-28)

**Done**, offline (no openMSX). Commit **3b91acf** (7 files, explicit paths): `tools/bobcatalog.py`,
`tools/msxsprites.py`, `tools/msxframe.py`, `tools/recframes.py`, `tools/msxchooser.py` (new),
`msx/level2_frames.json` (new, empty), `tests/test_msxsprites.py` (new). Scratch: `$IMPL/s10` (logs,
outputs, check scripts, pictures). The Makefile, mkrom.py and build/ are untouched: **build/msx and
build/sprites hashed before and after: 300 files, 0 changed, 0 added** (`s10/hash_{before,after}.txt`).

### What step 12 takes (commands, files, layout)
```sh
python3 -I tools/bobcatalog.py level2 [--drawn COV2.json] [-o build/sprites/catalog_l2.json]
$VPY -I tools/msxsprites.py <the Makefile's level-1 arguments, unchanged> \
    --pool build/msx/sprites --l2-datal build/extracted/files/DATAL2_18.bin --l2-rows 50 \
    --l2-bobs build/sprites/catalog_l2.json --l2-ram build/ram/level2_full.bin \
    --l2-pal build/msx/level2.pal --l2-remove msx/level2_frames.json build/msx/robocop
$VPY -I tools/msxchooser.py build/msx/sprites build/review/quadros.html [--sheet OUT.png]
```
- `bobcatalog.py level2` reads `build/emu/cov_level1.json` (default `--shared`): level 1's coverage
  frames whose bytes level 2's image holds. `--drawn` = level 2's coverage (`amigacov.py --level 2
  --carry 0:2:0:good --scenario level2`, only in `$IMPL/s2/cov2_scen.json` today): it fails if the
  catalogue lacks a drawn frame (today: 0 of 214 missing). The `catalog` command is unchanged.
- `--pool P` writes, beside OUT's unchanged level-1 files: `P.bin` (27 banks: compositions 7, patterns
  15 (3,604 of 3,840), colour rows 5 (2,067 of 2,560); robocop.bin: 6 + 13 + 4 = 23), `P.inc`
  (robocop.inc's names = level 1's, plus `SPR_{BOBS,SPARK,SIL_FLASH,SIL_BLACK,BOB_INDEX}_L1/_L2`:
  L1 198 / 194 / 1818 / 1122 / 8372h, L2 204 / 200 / 1818 / 1122 / **85C4h**), `P_l1.json`,
  `P_l2.json` (robocop.json's structure: "bobs" with ids, "reuse" = level 1's id, "new"; "field" with
  fid; L2 also "hidden", "frames", "palette"), `P_l1_field.{bin,inc}` (= robocop_field.* but
  FIELD_ID0 D0h), `P_l2_field.{bin,inc}`, `P_l{1,2}_field_vram.bin`, `P_fdyn.bin` (= robocop_fdyn.bin),
  `P_flash.inc` (= robocop_flash.inc; level 2's flashes are the same: no `P_l2_flash.inc`),
  `P_l2_bobs.png`, `P_l2_or.txt`.
- The index: [RoboCop 294][level 1's 198][level 2's 204] in bank 0 (SPR_BOB_INDEX per level, the bank
  SPR_BASE_BANK for both). Level 1's records are byte-identical, at other offsets (the index grew).
- Level 2's play field: 35 frames, ids FIELD_ID0 D0h + fid (hostage 0-8, type 2 9-10, type 14 11-12,
  type 16 13-16, dynamic 17-32, lift 33, trolley 34 = FIELD_LATE 33), atlas **108 lines**, ROM
  **9,722 B (two banks)**, `DYN_Y equ 224` = page 2 (field_tab's y of a dynamic frame is not read).
- mkrom's `bob_hash` with `FIELD_ID0 = 0xD0` builds both tables (L1 230 slots, L2 227; with C8h it
  refuses level 2: 204 ids > 200).

### Checks (exact commands, results)
- `catalog` unchanged: `bobcatalog.cmd_catalog()` with `OUT` = `$S10/cat` (python driver,
  `s10/cat/catalog.log`): `cmp` = build/sprites/catalog.json.
- `python3 -I tools/bobcatalog.py level2 -o $S10/cat/catalog_l2.json --drawn $IMPL/s2/cov2_scen.json`:
  "61 references, **229 distinct frames** (56 in DATAL2, 173 shared)", rc 0; against the sprites
  report's `l2_frames.json`: 229 = 229, 0 extra, 0 missing.
- The Makefile's msxsprites command into `$S10/l1ref` (old tools) and `$S10/l1new` (new tools), and
  the `--pool` run's OUT (`$S10/pool/robocop.*`): all 12 files `cmp` = build/msx's.
- The pool run (command above, OUT and P in `$S10/pool`, 16 s, `s10/pool/log.txt`): "27 banks (level
  1's 23: +4)"; "level 2: **229 Amiga frames**: field 27, joint 18, sprite 176, sprite+field 8"; "204
  BOB ids (58 new records, 142 level 1's, the spark's 4), 35 play-field frames (ids from 0xD0), atlas
  **108 lines**, 9722 B; type 1 joint: 16 frames, **at most 3 a line**"; flashes = level 1's.
- Level 1 from the new outputs: `$VPY -I $S10/check_l1.py $REPO build/msx/robocop $S10/pool/sprites`:
  492 index entries (294 RoboCop's, 198 BOBs'), 1,927,008 px (full and one layer): **0 differ**, every
  record's bytes identical. `$VPY -I $S10/check_msxframe.py $REPO $S10/pool/sprites`: msxframe's 492
  layouts converted again = the pool's decoded, 0 differ, silhouettes [0, 9, 5, 0] both. msxframe on
  the base stills g0430 and g1490 with and without `--sprites ... --level 1`: PNGs and reports
  identical, and identical to `$IMPL/base/l1/still/m2_g*.png`. recframes `--sprites` with and without
  `--pool ... --level 1` on 30 records (`base/l1/field/430_m2` cut to rc2_jumprec's size): identical.
- `$VPY -I $S10/check_pool.py $REPO $S10/pool/sprites`: both levels' records 0 bad (in their bank,
  pattern and row ids in range, BOB_CAP / RC_CAP a line); BOBHASH (mkrom.bob_hash, FIELD_ID0 0xD0):
  L1 230 slots, L2 227.
- Chooser: `$VPY -I tools/msxchooser.py $S10/pool/sprites $S10/review/quadros.html --sheet
  $S10/review/level2_new.png`: RoboCop 35 cards, level 1 169, **level 2 56** (type 1 8, type 2 2,
  type 5 9, type 6 5, type 14 1, type 16 2, its walker1 legs 8, type 49 15, trolley 1, type 4's new
  aims 4, RoboCop hanging 1); `node --check` of its script OK; the script run on its data in a DOM stub
  (`s10/review/dom_test.js`): 260 cards, level 1's 8 removals pre-ticked, the result JSON
  `{"rc2_frames":3,"level1":[...],"level2":[]}`.
- `~/.venvs/msxports/bin/python -I -m unittest discover -s tests -p test_msxsprites.py`: **13 OK**
  (17 s; the pool test converts both levels in a temp dir and checks the acceptance); with python3:
  3 OK, 10 skipped (numpy). `make test`: 283 tests, **only the 4 known failures**.
- Pictures looked at: `s10/review/level2_new.png` (every level-2 card, Amiga | MSX at 3x, graded),
  `zoom_types.png`, `zoom_t4.png`, `reconv_cmp.png`, `pool/sprites_l2_bobs.png`. Type 1 joint, types
  2/14/16 (play field), 5, 49, the trolley and RoboCop's hanging pose look right; type 6's tyre loses
  its inner ring and type 1's strides show solid grey wedges (both known from the report); type 4's
  new aims keep their face (aim 7) but show one box per band as a solid block (gun, jacket).

### Decisions taken here (defaults kept; for the user's eye)
- Default 32 kept: the shared frames keep level 1's records under palette C. `P_l2_or.txt` (check
  12): 128 shared frames show entries 9/11/13; about 30 get clearly worse than in level 1 (walker1 and
  walker2 legs, the gunman's torso, types 4, 12, 13: largest dE76 94 against level 1's 30-44, means
  21-31 against 9-14: OR lines whose p|q = 11 is now 015). Looked at (`reconv_cmp.png`): the
  difference is modest. `--l2-reconvert` (default 32's alternative, not used) converts their 8
  animations again for level 2 only: 36 frames, still 27 banks (patterns 3,749), largest left +8.1.
- Type 4's torso aims are poses (`L2_POSES`): each new aim keeps the OR layer on its own best boxes
  (as an animation group, aim 7 lost its face to the gun).
- The chooser and the generated files are in English (CLAUDE.md); the old pt-BR
  build/review/quadros.html is untouched; the MSX views use the game's graded colours.

### Open issues
1. **Joint frames and the view's bottom edge** (step 12): type 1's record is placed from the legs'
   call, so its torso's bands have dy down to about -25; sprites.asm's park test (`sbo`: the object's
   origin at or below VIEW_LINES = parked) then hides the whole joint while its torso is still in view
   (up to 21 lines early). Test the record's top (its top band's dy) instead: level 1's BOBs have no
   pixel above their origin, so that is neutral for level 1.
2. **Type 1's torso calls** (`P_l2.json` "hidden": $404D0 and $40674, 32 x 21) must draw nothing and
   take no object: check bob_flush's path for a sprite frame missing from BOBHASH, or give them an
   explicit skip entry.
3. Step 13: level 2's dynamic slot is page 2 line 224 (field.asm's `fbb_sy` and the slot's writes use
   page 3 today), its atlas ROM spans two banks (field_upload reads one), and msxframe's TILE_AREA check
   (page 2, page 3 lines 0-175) is level 1's VRAM layout.
4. The Makefile/mkrom wiring is step 12's: `bobcatalog.py level2` in `make sprites`, the pool run in
   `make msx`, mkrom's FIELD_ID0 D0h and BOBHASH per level, LV_SIDX/LV_SBOBS/LV_SPARK from `P.inc`.
5. PoolTests/FormatTests/JointTests need numpy: `make test` (system python3) skips them; run them with
   the venv after any change to these tools.
6. recframes reads rc2_jumprec's records; the field records (l2base's, +440h EXTRA) need cutting first
   (fieldcheck.py reads them whole).

## Step 7: level 2 in the ROM, a stub logic bank, the test build (2026-10-28)

**Done.** Commit **5f6cade**. Records in `$IMPL/s7` (`W`: the builds `W/R`, the level-2 traces `W/O/l2`,
the stills `W/O/still`, the stubbed references `W/stub`; `G`: the gate's run; `variants`,
`banks_variants.txt`, the logs).

### What was built
- **`tools/mkrom.py`**: level 2's blocks after the range's, each from a bank: `BANK_L2` 104 (a late
  code section: `STAGES` gained `"L2"`, rc2.asm's last section), its tiles 105-112 (`level2.vram`'s
  pages 2-3), map 113-114 (50 rows), packed attributes 115, tables 116 (OTILE, ATR2, its BOBHASH at
  8600h, `level2_grade.pal` at B680h and its view_offy at B6A0h in the A000h window): **117 banks,
  1 MiB**; banks 0-103 keep their places (the data banks byte-identical). `banks.inc`: `BANK_L2`,
  `L2_TILES`, `L2_MAP`, `L2_ROWS`, `L2_ATR`, `L2_ATRN` (160), `L2_TAB`, `L2_FIMG` (= `FIELD_IMG_BANK`:
  level 1's atlas, 3.12), `L2_X/Y/YMAX` (read from the header at `$868C`: 352, 784, 624),
  `L2_PALP`, `L2_VOFFP`, `L2_KY` (1471). `levels.inc`: `lv_desc2` (level 2's descriptor, `lv_desc` +
  `LV_SIZE`, `ds` lines hold it there; `lv_camy` 638, `lv_maph` 800, `lv_dyn` level 1's `DYN_Y`).
  The BOBHASH keeps level 1's frames outside DATAL1's own part `[$28000, $45250)` (`DATAL_OWN`,
  `shared_frame`: MADEX, SPERMA, PERMA; 153 sprite and 26 play-field frames, level 1's ids); the build
  fails when one of them holds other bytes in `level2_full.bin` (the rule matched the byte compare
  exactly: the 41 + 14 dropped all differ). Level 2's colour 0 must be the HUD's. mapcells' level-2
  check runs from mkrom (`--level 2`). `LV_TEST` (0/2) and `LV_CARRY=S:L:C:R` (default `10050:2:0:1`;
  `options.inc`: `LV_SCORE_H/L` BCD, `LV_LIVES`, `LV_CREDITS`, `LV_RATING`); refused: `LV_TEST` with
  `PZ_TEST`, `LV_TEST` other than 0/2, `LV_CARRY` without `LV_TEST`, a bad carry.
- **`analysis/amiga_tables.tsv`**: `spawn_l2` listed (`cells_l2.inc`: 40 entries, 7 hazards). The 15
  `_l2` tables the shared handlers read were already there (step 6).
- **`msx/level2.asm`** (new, `BANK_L2` at A000h): `lv_htab_l2` (the types from the original's
  `obj_desc`: 1 `t1`/`death_c31e`, 2 `t2`/`death_c2d8`, 5 `t5`/`death_none` ($C1FA is an rts), 6
  `t6`/`death_c33e`, 14 `t14`/`death_c2ee`, 16 `t16`/`death_c31e`, 49 `t49`/`death_c35a`; 3, 4, 12, 13,
  15, 18, 30, 31, 45 the `_l2` copies with level 1's deaths), the header exactly as level 1's
  (`lv_noten` `cp 45 / ret`, default 25), `lvshared_l2.asm` at A0F0h (mkrom's label check passes),
  `l2_init` (a fresh start: spawn list, object list, `vat_ph0` -> `vat_phase`, the specials and their
  pointers from `SP_RAM - 9088h`; always: `ac_objlA`, `$B0E`, `$15D6/8`, `ac_mkptr`/`ac_mktab` from
  `mk_tab2`, `$16B8`, `ac_mkmask`, the timer, `$804C`; then `sw_init_l2`), `lt1` (a `ret` stub).
- **`msx/level2obj.asm`** (new): `t1 t2 t5 t6 t14 t16 t49`: `ld a,0FFh / ret` (the slot freed at
  once); `death_c33e`: `ret`.
- **`msx/rc2.asm`**: `lv_next` (fixed, 9 B: `dsp_off`, AG `$8050`, `jp lv_go`); `lv_test` (`LV_TEST`:
  `pz_first` = 0, `front_l2test`, falls into `lv_next`) and its test after `display_on` beside
  `PZ_TEST`'s; the L2 section. **`msx/front.asm`**: `front_l2test` (`LV_TEST`: the carry, AG `$8050` = 1,
  `cpu_title`, `fb_prep`, `front_brief`, `jp cpu_title`), `front_brief` (a `ret` for step 18).
  **`msx/cold.asm`** (one line, needed): `if PZ_TEST + LV_TEST` sets `pz_first` and skips the title
  (the product's bytes unchanged: rebuilt identical).
- Harness: `hz.tcl` (`hz_l2_jobs`/`hz_l2`: BENCH2's 16 jobs + `barrel`, `mine`, `t1left`, `drone`;
  `hz_l2_still_jobs`/`_setup`/`_hit`), `openmsx_rc2.tcl` (`rc2_l2_arm` at `lv_next` (its first
  instruction checked), `rc2_l2_drive`), `hz.sh` (`l2builds R`; `compare --fields FIELDS DIR R
  [--refs REFS] [JOB[:ROWS] ...]`), `variants.sh` (+7 `LV_TEST=2` sets: 48), **`l2stub.py`** (new),
  **`l2frame.py`** (new), `tests/test_bstest.py` (48 sets), `tests/test_level2_rom.py` (new, 8 tests),
  `docs/HARNESS.md` 5.22 (+ the file table, the labels).

### THE level-2 check from now on (HARNESS.md 5.22)
```sh
sh tools/bstest/hz.sh l2builds W/R
# MCP: source {<repo>/tools/bstest/load.tcl}; hz_l2 {W/O/l2} {W/R} tr            (20 jobs, ~1 min)
python3 -I tools/bstest/l2stub.py W/stub [--drop trolley --drop vats --drop mine]  (~2 min, 4 cores)
sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv W/O/l2 W/R --refs W/stub   # level 2: PASS (20 traces)
```
`l2stub.py` makes the 15 direct references again with the routines the port lacks stubbed on the
bench exactly as the port stubs them (`--pre-poke` before `level_init`: trolley `rts`, vats `bra.w
$919E`, `act_0c` `bra.w $9C76` = `ao_look`, the 7 types `moveq #-1,D0 / rts`). **Steps 8 and 9: drop
your routine's stub (`--drop NAME` or the `STUBS` table) when you port it; then every drive compares
whole, not only "up to the first unported frame"** (which is row 0 for every reference: see below).

### Checks (exact commands, results)
All from the repository root; `S7=$IMPL/s7`, `W=$S7/W`.
- Builds: `sh tools/bstest/build.sh $S7/b3/prod/rc2.rom` (product, **77432348263399da**, 1 MiB: 117 of
  128 banks used), `sh tools/bstest/hz.sh l2builds $W/R`: l2builds PASS (l2 **25d98a685d63a8c4**, l2s, l2f,
  l2p, l2o, l2c), `build.sh $W/R/l2t/rc2.rom LV_TEST=2` (**0e46ab3d16de601b**); rebuilt on top of
  cdf5bb4 + 3b91acf: the same three hashes. 12 known z80asm warnings, 0 errors.
- Refusals: `python3 -I tools/mkrom.py build/msx/level1 $S7/neg.rom <opts>` with `LV_TEST=2 PZ_TEST=1`,
  `LV_TEST=2 PZ_TEST=2`, `LV_TEST=1`, `LV_CARRY=1:2:3:1`, and the carries `1:2:3:4`,
  `123456789:2:0:1`, `1:2:3`, `1:x:3:1` with `LV_TEST=2`: exit 2 each, no ROM written.
- Data banks: `python3 -I tools/bstest/romdiff.py $IMPL/s5/W/R/prod/rc2.rom $S7/G/R/prod/rc2.rom`: banks
  0-9, 78, 88 (code) and 104-116 (new) differ; **10-77, 79-87, 89-103 identical**. `relocheck.py ... 2 3 4
  5 6 8 9 78 88`: relocated words only, but one byte operand in FIELD (B9C1h: `add a,atr_rows & 0FFh`,
  84h -> 8Dh, `atr_rows` moved +9 with `lv_next`); banks 0-1 and 7 hold inserted code (not checkable).
- Option sets: `sh tools/bstest/variants.sh $S7/variants` + `python3 -I tools/bstest/l2base.py banks
  $S7/variants > $S7/banks_variants.txt`: **46 of 48 build** (DEMO_ACTORS=2/5 overflow the fixed area by
  27 B, 18 at step 5: +9 `lv_next`). The fixed area's free bytes (step 5 -> step 7): product 389 -> 380,
  PZ_TEST 361 -> 352, EXTJOY/trace 354 -> 345, LOCKSTEP 308 -> 299, DIAG 282 -> 273, DIAG+PZ_TEST 254 ->
  **245 (the lowest)**, DEMO_HUD 167 -> 158; the LV_TEST sets: `l2_test` 363, `l2_carry` 363, `l2_tag` 363,
  `l2_2m` 363, `l2_trace` 328, `l2_lock` 282, `l2_diag` 256. FRONT: product 1,968 -> 1,943 (lowest
  `l2_diag` 1,497). **BANK_L2: 3,744 B free** (4,448 used) in every set. The other banks as step 5's.
- Level 2's logic: MCP `hz_l2 {$W/O/l2} {$W/R} tr` (20 jobs), then `python3 -I tools/bstest/l2stub.py
  $W/stub` (15 of 15) and `sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv $W/O/l2 $W/R
  --refs $W/stub`: **level 2: PASS (20 traces), 0 differ in all 1,022 fields over every row** (end 259,
  tour 2,654 on C-BIOS_MSX2, the FS-A1FX and the FS-A1GT, lift 801, trolley 641 at 4 ratings and 50 Hz,
  vat 701 x 3 machines, fuzz 2,501, over 109, cont 301, barrel 901, mine 161, t1left 341, drone 401).
- Against the plain references (the plan's literal check): the bench's first runs of what step 7 does
  not port (`$S7/firstrun.py`, `$S7/initrun.py`: Unicorn hooks on the entries): **`act_0c` in
  `level_init`'s map-object pass, before row 0, in every reference** (5 calls; `$B2D` = 28h), then
  `special_l1` at game frame 0, type 1 at 4 (also: t1left vats at 1, type 5 at 2; mine `act_0c` at 10;
  drone type 49 at 11; barrel type 6 at 11; vat/over/cont vats at 30; the rest later). `hz.sh compare
  --fields ... lift:1`: row 0 differs in **`snd_b2d` 0x28/0x0 alone** (act_0c's sound); rows 1-4 only in
  the trolleys' words (`special[44]`-`[71]`); from row 5 type 1's slot. So "0 differ up to the first
  frame an unported routine runs" holds vacuously (there is no such row), and the stubbed references
  carry the real proof.
- `rc2_l2_arm`: `rc2_l2_drive` on the l2 build with `lift` (`$W/O/l2/arm_lift.txt`) = `rc2_drive_rom`'s
  trace byte for byte (`cmp`).
- The start (MCP `hz_l2_still_jobs {$W/O/still} {$W/R} {0 50 70 100}`; the plain `l2t` on the same jobs
  with frames 0, 100, `$W/O/l2t`), on C-BIOS_MSX2, the FS-A1FX and the FS-A1GT: RoboCop at **(352, 784)**,
  `lv_cur`'s logic bank 104 (`BANK_L2`), `$PY -I tools/bstest/l2frame.py SNAP build/msx/level2
  build/msx/hud OUT.png`: every sprite pixel exact (RoboCop 861/812/816 at frame 50, 808 at 70, 1,612
  with a type-4 gunman at 100); the play area equal to level 2's map but the lift drawn into the play
  field (233-617 px at y 139-161, which msxframe does not model) and, in the first picture only, the
  HUD's timer (20 px: `hud_init`'s 09:58 before 7:30; level 1's first picture has the same 27 px with
  its 10:00); `l2t` at frame 100: 0 differ on all three. Looked at: the first pictures (the view at
  (173, 638), the HUD), frames 50/70 (RoboCop in his start pose, 7:30, 0010050), 100 (on lift L0 in its
  shaft, a gunman), on each machine. (An early still job took two snapshots while the display was off
  during level 2's set-up, level 1's view still in VRAM: `hz_l2_still_hit` now waits for R#1's display
  bit.)
- The gate: `sh tools/bstest/l2base.sh builds $S7/G`, MCP `l2b_chain` (227 jobs, 0 time outs), `sh
  tools/bstest/l2base.sh check $S7/G $IMPL/base`: **l2base: PASS** (`$S7/G/l2base_check.log`): regress 45
  verdicts PASS (cov1 4,401, cov0/cov0_tr 1,400: 0 differ; the title exact: PASS, its polled record
  reported; Brainstorm's and the range's verdicts), die/over/end 0 differ, the start check 0 on the
  three machines, the field check within the known tear's bound (860_m2 3 = the base's, 860_fx 5),
  the stills identical to the base's, LOCKSTEP 2,998 lists 0 differ, the effects by their starts PASS.
  Run again on the gate's committed harness (cdf5bb4: the Tcl of the first run was sourced 7 minutes
  before that commit): `l2base.sh builds $S7/G2`, `l2b_chain` (227 jobs, 0 time outs), `l2base.sh check
  $S7/G2 $IMPL/base`: **l2base: PASS** again (`$S7/G2/l2base_check.log`; the same counts). Both runs' big
  record folders deleted, the logs kept.
- `make test` (`$S7/make_test2.log`): 283 tests, the 4 known failures only. `tests/test_level2_rom.py`: 8
  OK; `test_bstest.py`: 34 OK (48 option sets).

### Open issues
1. **The HUD at level 2's start is `hud_init`'s** (a new game's: 09:58, score 0 until `hud_frame`
   catches up in a frame or two; lives drawn as 2 whatever the carry). Step 18's `hud_lvl` should draw
   the level's timer, the score and the lives from AG at once.
2. **The weapon at the next level**: `lv_go` does not call `set_weapon(0)` (`level_init` does, at every
   level start). Right for `LV_TEST` (AG cleared: weapon 0, ammo 0 = `set_weapon(0)`'s), wrong for step
   18's real `lv_next` after a level 1 played with a weapon: call it there (LC1, `logic_map` first).
3. **`l2_init` does not set `vat_shown`, `vat_disp`, `vat_chg`** (their start table is step 13's
   `mapcells.py` output; the plan's 3.3 lists `vat_shown`'s start in `l2_init`): steps 13-14 add it.
4. **Use `tools/bstest/l2frame.py`, not `msxframe.py`, on level-2 stills until step 12** (msxframe
   re-converts sprites with the level's palette; step 10's `--sprites POOL --level 2` is for the pool).
5. On a turbo R an `LV_TEST` build shows level 1's start view while `fb_prep` measures the split (a
   fraction of a second) before level 2; on the MSX2/2+ the display is on for microseconds only. Test
   builds only; step 18 may clear the play area first when `front_brief` gets its text screen.
6. `msx/msx.inc`'s `pz_first` comment still says PZ_TEST only (`LV_TEST` uses it too); msx.inc is left
   to step 18 (the plan's rule).
7. With `ENEMY_CAP=0` (the l2 trace build) the frame-100 still has more than 8 sprites on lines 115-119
   (RoboCop and a type-4 gunman), which msxframe reports as a transient: for the sprite steps (10-12).
8. `BANK_L2` has 3,744 B left for `lt1`, the 7 types, `walk_d6`, `death_c33e` (~2.4 KiB [E]); the plan's
   fallback if it overflows: its tables and cells to `L2_TAB`.
9. Scratch tools (not committed): `$S7/firstrun.py`, `$S7/initrun.py` (the first frames of the routines
   step 7 lacks, per reference), `$S7/sprpix.py`, `$S7/diffbox.py`.

## Step 8: the level code (2026-10-28)

**Done.** Commit **76b53e2** (explicit paths: `msx/special.asm`, `msx/mapobj.asm`, `msx/level2.asm`,
`tools/bstest/l2stub.py`, `tools/bstest/hz.tcl`, `tools/bstest/hz.sh`, `docs/HARNESS.md`). Records in
`$IMPL/s8` (`S8`): `W/R` (the six l2 builds), `W/stub` (the stubbed references), `W/O/mst`, `W/O/tst`
(stills and their PNGs), `drv/` (the scratch drives `l2_h0`, `l2_h1` and their bench references), `G` (the
gate's logs), `compare1.log`, `compare_plain5.log`, `variants`, `banks_variants.txt`, `make_test.log`,
`tools/` (the scratch scripts below); the traces themselves deleted (1.9 GB with the gate's records).
Built from a worktree (`$S8/wt`: HEAD 5f6cade + my files; the step-9 agent's `level2obj.asm` edits were in
the shared tree), removed after the commit.

### What was built
- **`sp_trolley`** (`msx/special.asm`, LC3, `$8F02`): the index toggles at the path point it names (+8,
  0/2), the record's x steps 2 towards the other point and the entry's dx (`(8,A0)`) gets +-2, seen or
  not; its own window (x in (cam_x, +1B0h], y in (cam_y, +118h], unsigned as `sp_seen`); seen: with
  RoboCop on it (its flag) and his state & ~1 = 14 (the word) his x = D0 (the x before the step), `p_pend`
  = 14 + (state & 1); the flag cleared; `sp_entry` with top = D1 + 14h, right = x + 10h; sound 0Ch on even
  frames; its BOB `$4B95A`/`BC3h` at (x + 10h, y + 14h - 68h); then **`sp_d7` = BCh** (default 29). Not
  seen: `ret` (D7 stays 6 & `$168C`). `spt_pt` = `cmp.w (0Ah,A3,D2.w),D0`. +220 B in LC3.
- **`act_0c`** (`msx/mapobj.asm`, LC2, `$9EE8`), placed after `act_1c` (level 1's LC2 code keeps its
  addresses: only the data operands of `at_c2.inc` move +F5h and `ao_acts`' entry 3): sound 28h when game
  frame & 7 = 0; RoboCop's cell test ((y + 8) & F0h low byte) - 10h = its y, (x & ~15) - 20h = its x) sets
  hits' high byte FFh and starts 4 explosions (type 0) at x + 10h, + 24h, + 38h, + 4Ch; then `$9FAE`
  (`ao_lookp`; negative: look index high byte FFh, no pickup). Any look but `$A4A2` goes to `ao_copy`;
  `$A4A2` runs `ao_copy`'s steps itself (the animated step, `lk_cache`, the 5 x 2 block) and then writes the
  blinking word into cell (row, column + 2) with `map_write_lin`: E680h, or 9700h while frame bit 2 is
  clear (default 23: the look data is ROM; the word is written after the look so that a first copy of the
  block cannot put E680h back over 9700h). One patch per mine, among the 289 cells mapcells counts. +245 B.
- **`lt1`** (`msx/level2.asm`, BANK_L2, `$91BC`): every frame sound 1Ah when ($B32 & 0Fh) = 0; RoboCop in
  x0 - 10h .. x1 + 10h and d = cam_y + 98h - y in 0..4Ch: `vat_cut_line` = CBh - d, below 90h `st $169A`,
  `st $16CC`, sound 10h; odd frames: per column k (vat_phase, one table for every vat from column 0) the
  first vat in the window (`$15F0`'s byte clear) adds 2 to phase k's low byte, `vat_shown[base + k]` = (phase
  k & 0Eh) / 2 + 8 when phase k + 1's high byte is not 0 (= the original's d / 2), `vat_chg[v]` = FFh when a
  column's value changed; then `st $15F0`. base = the columns of the hz_l2 records before this one (0, 12,
  22, 32, 48, 70, 90; 103 in all). No map write (default 17); `vat_shown`/`vat_disp`/`vat_chg` are not
  initialised yet (steps 13-14: their start table from mapcells). IX is not kept (hz_update does not need
  it). +239 B in BANK_L2.
- **Harness**: `l2stub.py`'s table without `trolley`, `vats`, `mine` (the 7 types remain; its default
  output is byte-identical to `--drop trolley --drop vats --drop mine`); **`cont`**: RoboCop now dies in
  the vat, so until the continue (step 19) the port's game over ends `cont`'s trace at row 108 and the job
  would wait 1,800 s: `hz.tcl hz_l2_jobs` gives `cont` a 60-s timeout, and `hz.sh compare --fields` without
  job names compares it as `cont:109` (the plan's milestone-1 rule; **step 19 removes both**: `upto=109`
  in hz.sh, the `tmo` line in hz.tcl). `HARNESS.md` 5.22: a step-8 paragraph.

### For step 9 (and the next agents)
- **Stubbed references now**: `python3 -I tools/bstest/l2stub.py OUT` (no `--drop` for my three: they are
  gone from the table; `--drop trolley` is now an error). When you port a type, drop it with `--drop tN` or
  from the table. A worktree made before 76b53e2 (the step-9 agent's `$IMPL/s9/wt` is at 5f6cade) still
  stubs the trolley, the vats and `act_0c` in the port and in its l2stub.py: its traces and references agree
  with each other, but the final check of step 9 belongs on a tree with 76b53e2 (both stub sets dropped).
- Against the **plain** references every job equals the bench in rows 0-4 (row 0's `snd_b2d` 28h included:
  `act_0c` runs in `ao_start`'s pass); from row 5 type 1's slot (`obj0_type 1/0`).
- BANK_L2 has **3,505 B** free after `lt1` (the types' room); LC2 4,842, LC3 4,866; the fixed area unchanged.
- The trolley's BOB (`$4B95A`, BC3h) is in the shared BOBHASH as a **sprite** frame (id 0; level 1's sprite
  set has `$8F02`'s frame, `build/sprites/common_FUN_00008f02.png`): the stills show it drawn as sprites with
  its OR layers dropped (`drop 0x07`) while RoboCop hangs under it. The plan puts it into the play field
  (`fb_late`, step 13).

### Checks (exact commands, results)
All from the repository root unless `cd $S8/wt`; the MSX runs in a private MSX-AI MCP session
(`$S8/tools/mcpd.py $S8/mcp` + `$S8/tools/mx.sh NAME 'TCL'`, copies of the harness step's; the in-process
target is shared with the step-9 agent, which held the second openMSX: 2 in all).
- Builds: `cd $S8/wt && sh tools/bstest/hz.sh l2builds $S8/W/R`: l2builds PASS (12 known z80asm warnings);
  product `sh tools/bstest/build.sh $S8/b/prod/rc2.rom`: **cc8a6524c30da27c** (1 MiB, 117 banks used).
- Banks against step 7's product (`python3 -I tools/bstest/romdiff.py $IMPL/s7/b3/prod/rc2.rom
  $S8/b/prod/rc2.rom`): banks 1, 3, 5, 104 differ. `relocheck.py ... 1`: PASS (3 relocated words);
  LC3 and LC2 hold inserted code, so `$S8/tools/segcheck.py OLD NEW OLD.labels NEW.labels 5
  8000:80AB:8000 80AC:8C22:8188`: 3,105 bytes, 73 relocated words, **0 other bytes**; LC2 (`3
  8000:86B1:8000 86B1:8C21:87A6`): 12 other bytes = 6 operand words `obj_types/obj_looks + const` (+F5h,
  the data's move) and `ao_acts`' entry 3 (8125h -> 86B1h, act_0c); every other byte equal.
- Level 2's logic: `hz_l2 {$S8/W/O/l2} {$S8/W/R} tr` (20 jobs; cont TIMEOUT by design, see above),
  `python3 -I tools/bstest/l2stub.py $S8/W/stub --drop trolley --drop vats --drop mine` (15 of 15), `sh
  tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv $S8/W/O/l2 $S8/W/R --refs $S8/W/stub`:
  **level 2: PASS (20 traces), 0 differ in all 1,022 fields over every row** (end 259, tour 2,654 on
  C-BIOS_MSX2, FS-A1FX, FS-A1GT, lift 801, trolley/sharp/fair/poor 641, trolley_eu 641 (50 Hz), vat 701 x 3
  machines, fuzz 2,501, over 109, cont 109 (its game over), barrel 901, mine 161, t1left 341, drone 401).
- The plan's literal check (plain references, up to type 1's first frame): `sh tools/bstest/hz.sh compare
  --fields analysis/amiga_ram_l2.tsv $S8/W/O/l2 $S8/W/R lift:5 trolley:5 sharp:5 fair:5 poor:5 vat:5
  mine:5`: **level 2: PASS (7 traces)**; with `--show` the first difference of each is game frame 5,
  `obj0_type 0x1/0x0` (type 1).
- **States 14/15**: state 14 ridden in `trolley` (67 rows, frames 499-565) and `tour` (255). No reference
  hangs facing left, so two scratch drives (`$S8/tools/t15.sh NAME JOY GFRAMES`: drivejoy + the bench with
  the 7 type stubs): `h0` = trolley's joy + `640:6:l,710:12:u` (RoboCop back on the right floor, turned
  left, jumps up-left onto trolley 0 at its right end: **state 15 for 171 rows**), `h1` = h0 +
  `770:8:u` (up while hanging: he lets go, falls into vat 0 and dies, the level restarts at row 862: state
  15 for 42 rows). Played by `rc2_drive_rom` (901 rows) and compared with `tracecmp.py --ram --fields
  analysis/amiga_ram_l2.tsv`: h0 C-BIOS_MSX2, h1 C-BIOS_MSX2, FS-A1FX, FS-A1GT: **0 differ** (901 rows each).
- **Lost counters** (`$S8/tools/s8.tcl s8_lostrun`: peeks at each trace's end): tour (m2, fx, tr), mine,
  vat, trolley, fuzz, h0, h1: **mp 0, atr 0, rd 0, fb 0** in all.
- `vat_shown` against the phases (`python3 -I $S8/tools/vatchk.py TRACE...`): every change of a vat's
  columns equals the formula from that row's `vat_phase`, `vat_chg` set, a vat showing the phases on every
  `$15F0` = FF00h row: tour (vats 0-5 updated 180/152/161/236/4/17 rows; 3 machines), vat, trolley,
  fuzz, h0: 0 errors; h1: one row (862) where the phases moved with `$15F0` 0: the death's restart in the
  same tick (`clear_game_vars` clears `$15F0`), equal to the bench (not an error).
- Pictures looked at (`$PY -I tools/bstest/l2frame.py SNAP build/msx/level2 build/msx/hud OUT.png`): the
  mine drive's stills (`hz_l2_still_setup` frames 40-82, m2 and fx): the mine's cell alternates (a box with
  a blue / a red light, the static map's word 9700h at mine 0 shows as the only diff at E680h frames), RoboCop
  sets it off at 76, the floor turns to the broken look and he falls; all sprite pixels exact. The trolley
  rides (h1's drive, frames 496-830, m2/fx/tr): RoboCop hanging under the trolley in states 14 and 15,
  jumping off, in vat 0 at 830 (whole: the cut is step 15); sprite pixels exact, 0 pixels differ but 155
  at frame 496 on each machine, all in the HUD's energy can (the drive pokes the energy every 25 frames:
  the can's redraw in progress). tr 830: 2 sprite pixels of the level-1 type-4 gunman (ENEMY_CAP
  0 trace build, another walking frame than m2/fx) differ from msxframe's model: not this step's code.
- Option sets: `cd $S8/wt && sh tools/bstest/variants.sh $S8/variants` + `python3 -I tools/bstest/l2base.py
  banks $S8/variants`: **46 of 48 build** (DEMO_ACTORS=2/5 overflow the fixed area by 27 B, as at step 7);
  the fixed area's free bytes equal step 7's in every set (product 380, lowest DIAG+PZ_TEST 245); LC2
  4,842, LC3 4,866, BANK_L2 3,505 in every set.
- `cd $S8/wt && make test`: 283 tests, the 4 known failures only (`$S8/make_test.log`); in the main tree
  `test_level2_rom.py` 8 OK, `test_bstest.py` 34 OK.
- **The gate**: `cd $S8/wt && sh tools/bstest/l2base.sh builds $S8/G` (builds PASS), private MCP `source
  {$S8/wt/tools/bstest/load.tcl}; source {$S8/wt/tools/bstest/l2base.tcl}; l2b_chain {$S8/G}
  {$S8/G/all.done}` (227 jobs, 0 time outs, about 35 minutes beside the step-9 agent's emulator), `cd
  $S8/wt && sh tools/bstest/l2base.sh check $S8/G $IMPL/base`: **l2base: PASS** (`$S8/G/l2base_check.log`):
  regress 45 PASS / 0 FAIL (cov1 4,401, cov0/cov0_tr 1,400: 0 differ; the title exact: PASS, its RAM by
  variable, the music identical at every tick; Brainstorm's and the range's verdicts), die/over/end 0
  differ, the start check 0 on the three machines, the field check within the known tear's bound (860_m2
  A 3 / 177 px = the base's, 860_fx A 2 B 3 / 124 px), the 10 stills identical to the base's, LOCKSTEP
  2,998 lists 0 differ (m2, fx), the effects by their starts PASS (SCC 57,475 and PSG 33,390/33,393 sound
  ticks 0 differ). The gate's ROMs were built before a comment-only edit of level2.asm: rebuilt after it,
  the l2 build (de6ddb0f0e9eba39) and the product (cc8a6524c30da27c) are byte-identical.

### Open issues
1. `vat_shown`, `vat_disp`, `vat_chg` hold level 1's object-list leftovers until a vat runs: steps 13-14
   set their start (the static map's looks, mapcells) in `l2_init` (step 7's issue 3 stands).
2. The trolley is drawn as sprites with dropped OR layers until step 13 moves it into the play field; the
   vat cut (`vat_cut_line` is computed, nothing reads it) is step 15: RoboCop shows whole in the liquid.
3. State 15 and the "up" release are proven only on the scratch drives `h0`/`h1` (`$S8/drv`, recreate
   with `t15.sh`); step 11 may add them to `tools/l2drives.py` as references (21+ jobs: the job tables
   and their tests change together).
4. `cont` 60-s timeout and `cont:109` default: step 19 removes them (hz.tcl, hz.sh).
5. Scratch tools (not committed): `$S8/tools/` `mcpd.py`, `mx.sh`, `s8.tcl` (lost counters), `t15.sh`,
   `vatchk.py`, `segcheck.py` (LC banks with inserted code against an older build, label-relocation aware).

## Step 9: the new object types (2026-10-28)

**Done.** Commit **eca54d9** (on top of step 8's 76b53e2; 5 files, explicit paths): `msx/level2obj.asm`,
`tools/bstest/l2stub.py`, `tests/test_level2_rom.py`, `docs/HARNESS.md` 5.22, `docs/AMIGA_ANALYSIS.md`.
Records in `$IMPL/s9` (`G/l2base_check.log` and the gate's logs, `W2/R` the six l2 builds of eca54d9,
`banks_variants.txt`, `variants.log`, `make_test2.log`, `extra.tsv`, `tools/` = my private MCP (`mcpd.py`,
`mx.sh`), `amdiff.py`, the still/product Tcl). Big run folders deleted; the worktree removed.

### What was built (`msx/level2obj.asm`, BANK_L2; every routine from the REA listing `logic/level2_new.lst`)
- **t1** ($C736) + **walk_d6** (obj_walk's code returning $EF42's D6: 0 after a step, attr & 18h or 2
  on a turn). D2 uses the facing before the step; the fire, the bullet and the torso the facing after
  it. Facing left: bullet type D6, direction 10h (the leftover; Q2). The D6 = 2 path has no trace
  (bench finding 1: it never occurs in level 2).
- **t2** ($C868 + $C91A): message every 64 frames, x = 180h, `ac_camdx` = 500h (step 15 adds the eased
  view), bursts with the accelerations, the white blink, hp = 4 every frame, the arrest (`$16D0`,
  `$16C4` = 40h, sound 21h, freed).
- **t5** ($D0E2), **l2_fall8** (vy + 8000h, y + vy), **t6** ($D1E2, $D1CA/$D1D0/$D1DE, `barrel_gap`),
  **death_c33e**, **t14** ($CE0A), **t16** ($CD7A, `walker1`), **t49** ($E6C0 + flight $E728,
  **fly_half**).
- Damage (decisions 17/19, default 26): t5's touch `0 - 0Ah * DAMAGE_X` (FFE2h in the product, FFF6h
  in trace builds); t49's touch 30h when DAMAGE_X > 1, else 18h (FFD0h / FFE8h: checked in the ROMs).
- `lv_noten` untouched: level2.asm's `cp 45 / ret` since step 7 is default 25 (2, 5, 6, 49 counted).
- Harness: `l2stub.py`'s STUBS is **empty** (every level-2 routine ported); with it the script remakes
  the plain references byte for byte (`end`, `drone` cmp-identical to build/emu). `test_level2_rom.py`
  StubTests now asserts the empty table and checks the 7 handler addresses from the type records.

### Findings [V]
1. **Step 1's note on `$C33E` was wrong**: `$C35A` is `moveq #0,D5; bra $F366` (REA bytes), so the
   explosion is always type 0 (the plan's 2.5 was right). After a pickup `$F98C` leaves D1's low word
   0 (`swap D1; clr.w D1`): the explosion comes at y 0. Ledger corrected.
2. **The flight's half step** (`$E728`: `ext.l`, `swap`, `asr.l #1`): a negative step carries FFFFh
   into the low word before the shift (-9 gives FFFB.FFFFh, not FFFB.8000h). With a plain half step
   the `drone` trace differed in 380 of 401 rows; `fly_half` reproduces it: 0. Ledger added.
3. Type 6's byte 2 is the draw's D0 low byte: when not drawn it is `$16BA`'s low byte (port
   `AM + 16BAh`), not FFh.
4. **The 1,022 fields leave out the enemy bullets ($C34-$D33) and explosions ($D34-$D73)**; my scratch
   `$IMPL/s9/extra.tsv` (112 fields) compares them with `tracecmp.py --ram --fields extra.tsv`: 0 differ
   (end, tour, tour_tr, fuzz, barrel, drone, t1left, vat, mine, lift, trolley). The whole AM block
   differs only in the port's own pointers/display words ($B0A-$B20, $B22-$B2B, $1690), as before.
   Worth adding to `amiga_ram_l2.tsv` at step 11 (the field count 1,022 is quoted in tests and docs).
5. Product options (LV_TEST=2, EXTJOY, ENEMY_CAP 1, DAMAGE_X 3) on `end`: the grenadier (type 14) waits
   for the suspect's slot and spawns only after the arrest (row 165), then its grenades can kill
   RoboCop during the level-end countdown (row 220; the level end still wins). The original's rule
   with the port's cap: for the user's feel (default 25), not a bug of this step. The `drone` drive:
   the touch costs 51 (30h + 3), as designed.

### Checks (exact commands, results)
- Builds from a worktree (5f6cade + level2obj.asm, then 76b53e2 + it): `sh tools/bstest/hz.sh l2builds
  W/R`: PASS (12 known warnings). eca54d9's l2 build 11d325dd76f7a693, product 66e294ce1f26139c.
- On top of step 7, MCP (private session, `$IMPL/s9/tools/mx.sh`): `hz_chain [hz_l2_jobs {W/O/l2} {W/R}
  tr] {W/O/chain2.done}`; `python3 -I tools/bstest/l2stub.py W/stub --drop t1 --drop t2 --drop t5
  --drop t6 --drop t14 --drop t16 --drop t49`; `sh tools/bstest/hz.sh compare --fields
  analysis/amiga_ram_l2.tsv W/O/l2 W/R --refs W/stub`: **level 2: PASS (20 traces)**, 0 differ.
- **On top of step 8 (eca54d9's code), against the plain references**: the same `hz_l2_jobs` chain on
  `W2`, `sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv W2/O/l2 W2/R`: **level 2:
  PASS (20 traces)**: end 259, tour 2,654 (MSX2, FS-A1FX, FS-A1GT), lift 801, trolley 641 (4 ratings,
  50 Hz), vat 701 x 3, fuzz 2,501, over 109, cont 109 (step 8's game over), **barrel 901, mine 161,
  t1left 341, drone 401**: 0 differ in all 1,022 fields.
- The gate (on 5f6cade + level2obj.asm): `sh tools/bstest/l2base.sh builds $IMPL/s9/G` (25 builds OK),
  MCP `l2b_chain {G} {G/all.done}` (227 jobs, 0 time outs), `sh tools/bstest/l2base.sh check G
  $IMPL/base`: **l2base: PASS** (regress 45 PASS, die/over/end, start 0 on three machines, field
  860_m2 3 = base, stills identical, LOCKSTEP 2,998 lists 0 differ, effects PASS). `romdiff.py`: the
  gate's prod/ext/pzt/pz1/pz2/trace differ from step 7's (`s7/G2/R`) in bank 104 only, and eca54d9's
  prod/ext/pzt from step 8's (`s8/G/R`) in bank 104 only: the gate's runs never map BANK_L2.
- Stills (`end` drive, frames 12/30/100/150, MSX2 and turbo R) through `l2frame.py`: play area 0
  differ everywhere; sprites exact but tr g0100 (21 px where a type-5 bullet overlaps another BOB at
  x 184; m2 0); lost counters 0. The new types are **invisible**: their frames are not in level 2's
  BOBHASH until step 12 (bf_fid hides them); looked at: the roof with "ARREST ARMED EMEMY.", the
  suspect's bullets, the brewery floor, no garbage.
- Option sets: `sh tools/bstest/variants.sh $IMPL/s9/variants` (on step 7 + this): 46 of 48 (DEMO_ACTORS
  2/5 overflow by 27 B as before). **BANK_L2: 1,826 B free on top of step 7, 1,587 B on top of step 8
  (6,605 B used)**; the fixed area unchanged (product 380, lowest 245 DIAG+PZ_TEST); other banks as step 8.
- `make test`: 283 tests, the 4 known failures only (`make_test2.log`); `test_level2_rom.py` 8 OK.

### Open issues
1. Paths without a trace: type 1's D6 = 2 missile, type 5's touch damage, type 2's 5-hit kill (risk 8),
   type 49's life running out (65,536 frames). Read against the listing only.
2. The arrest's eased view (default 31) is step 15's: `t2` sets `ac_camdx` = 500h exactly as the original.
3. The enemy bullet/explosion fields are not in the official field set (finding 4).

## Step 11: milestone 1 accepted, but for 4.2 check 1's guard (2026-10-28)

**Done, with one acceptance item not met literally (below).** The review's findings: none (`[]`). No
msx/ or mkrom.py change: every ROM is eca54d9's. Commit **5d41020**: the harness only (`tools/bstest/hz.tcl`,
`tools/bstest/hz.sh`, `tools/openmsx_rc2.tcl`, `docs/HARNESS.md` 5.22 "At step 11"). Records in `$IMPL/s11`
(`S11`): `W/R` (the six l2 builds, `l2x` = `EXTJOY=1 LV_TEST=2` with the product's caps), `b/prod`, `G` (the
gate's logs), `W/O/l2/lost.txt`, `W/O/st2_l2`, `W/O/st2_l2x` (the start checks), `W/O/g2` (level 1 under
the same guard), `W/O/still` (stills, PNGs, `sheet_{m2,fx,tr}.png`), `W/O/mapend` (map comparisons),
`drv/` (h0/h1 plain references, bench map dumps), `tools/` (`mcpd.py`, `mx.sh`, `g1.tcl`, `tcchk.py`,
`mapcmp50.py`), `banks.txt`, `banks_variants.txt`, the logs. Big traces and the gate's records deleted.

### What the next agents need
- **`hz_l2` now records the lost counters** (`W/O/l2/lost.txt`, via `hz_l2_drive`) and `hz.sh compare
  --fields` fails on a lost counter that is not 0 (pools printed). **`cont` ends once its 109 rows are
  written** (no more 60-s wait); **step 19**: give `cont` the others' done condition (`hz.tcl hz_l2_jobs`,
  the `if {$name eq "cont"}` block) and drop `upto=109` in `hz.sh`.
- **Level 2's start check**: `hz_chain [hz_l2_start_jobs DIR ROM LABELS ?SECS?]` (HARNESS.md 5.22). Its
  expected entries at step 11 are listed there: anything outside those classes is new.
- **The guard** no longer takes the play-field BOBs' scratch/caches on page 3 (commands started with the
  HUD's R#2 page 3) for tears; Brainstorm's and the range's guard counts and level 1's start check are
  unchanged (rerun of `st_m2/fx/tr`: all 0).
- **4.2 check 1 is not met yet (cmd, tear; reg 1 once; satcheck at frame 0)**: every entry is a class
  level 1 shows too under an active drive (table below). Milestone 2 (steps 13-16; check 8 asks tear 0
  under rc2_guard) must take them: the redraw fallback's 16 x 16 copies into the page on screen during
  the play area (the only real tears: 1-4 per 42 s, when a map object's look block changes for several
  frames, `tour` 638-644), the play-field copies still running at the picture's start (by `fb_fits` ahead
  of the beam, unprovable by the guard), `fb_qstart`'s R#46 for a staged piece in the play area.
- Tools for the start's picture items: `$S11/tools/tcchk.py VRAMIMAGE SNAP...` (every tile-cache slot
  against the level's sheet; msxframe's "tile VRAM changed" line predates the cache and the atlas and
  means nothing now); `tools/mapcmp.py` hard-codes 51 rows (level 1): `$S11/tools/mapcmp50.py` is it with
  50 (step 14 owns mapcmp.py: take the rows from the map's size, add the vat rule).

### Checks (exact commands, results)
All from the repository root; MSX runs in the in-process MCP (one openMSX) and, for the gate, a private
session (`$S11/tools/mcpd.py $S11/mcp` + `mx.sh`): 2 openMSX at most.
- Builds: `sh tools/bstest/hz.sh l2builds $S11/W/R`: PASS (12 known warnings), the six ROMs = step 9's
  `s9/W2/R` (l2 **11d325dd76f7a693**, l2c 2c3df626, l2f f8dec583, l2o faee77a6, l2p 10c389a8, l2s b1fc4966);
  `sh tools/bstest/build.sh $S11/b/prod/rc2.rom`: **66e294ce1f26139c** (= step 9's product; 1 MiB, 117
  banks used); `build.sh $S11/W/R/l2x/rc2_l2x.rom EXTJOY=1 LV_TEST=2`: 62cabfa1e5462343.
- **4.1**: MCP `source {<repo>/tools/bstest/load.tcl}; hz_l2 {$S11/W/O/l2} {$S11/W/R} tr`, then `sh
  tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv $S11/W/O/l2 $S11/W/R`: **level 2: PASS (20
  traces), 0 differ in all 1,022 fields over every row** (end 259, tour 2,654 on C-BIOS_MSX2, FS-A1FX,
  FS-A1GT, lift 801, trolley 641 at 4 ratings and on C-BIOS_MSX2_EU, vat 701 x 3 machines, fuzz 2,501,
  over 109, cont 109 = rows 0-108, barrel 901, mine 161, t1left 341, drone 401). `flow_l2_end` not run
  (step 18). Also `hz.sh compare --fields $IMPL/s9/extra.tsv ...` (the 112 bullet/explosion fields):
  PASS, 0 differ in all 20.
- States 14/15 on the full port: plain bench references of step 8's scratch drives (`~/.venvs/msxports/
  bin/python -I tools/amigaemu.py game --level 2 --carry 10050:2:0:good --gframes 900 --drive
  $S11/drv/l2_h0.drive --stop-at-end --trace $S11/drv/l2_h0_ram.jsonl --trace-ram`, h1 the same; 901 rows,
  state 14 67 rows, state 15 171 / 42), played with `hz_l2_drive` (h0 MSX2, h1 MSX2/FS-A1FX/FS-A1GT) and
  `python3 -I tools/tracecmp.py --ram --fields analysis/amiga_ram_l2.tsv --labels .../rc2_l2.labels REF
  TRACE`: **0 differ** x 4, lost 0.
- The map against the bench: `amigaemu.py ... --gframes 2653 --drive build/emu/l2_tour.drive
  --stop-at-end --dump $S11/drv/tour_2653.bin` (mine: `--gframes 160`), the port's `rc2_snap` at the trace's
  end (tour on MSX2 and FS-A1GT, mine on MSX2), `PYTHONPATH=tools python3 $S11/tools/mapcmp50.py DUMP SNAP
  build/msx/level2`: 540 (tour) and 79 (mine) cells differ, **every one a vat cell** (the vats leave the
  map, default 17: 604 cells, the records' x - 128); every other cell's tile and attributes equal; patches
  19/23 and 4/8, lost 0.
- **4.2 check 5**: the lost counters 0 after every drive (`lost.txt`: the 20 jobs, the four hanging
  drives, the start checks, the map runs); the pools at most 19/23 (bounds 146/143). No vat refresher yet.
- **4.2 check 1** (`hz_chain [concat [hz_l2_start_jobs $S11/W/O/st2_l2 W/R/l2/rc2_l2.rom ...]
  [hz_l2_start_jobs $S11/W/O/st2_l2x W/R/l2x/rc2_l2x.rom ...]]`, 42 s from level 2's first tick):
  RoboCop at (352, 784), logic bank 104, R#1 62h, `lv_pal` = `gen/level2_grade.pal` byte for byte, the
  VDP's palette at the end = `lv_pal` on the three machines (at the first tick black, or the HUD's
  `hud_grade.pal` on the FS-A1GT where the tick came after the split: the fade from black); pal 0, cpu 0,
  vbl 0, patcheck 0 bad (11,363-54,984 entries), lost 0; the guarded traces = tour's first 713 / 781 /
  1,049 rows, 0 differ (`hz.sh compare --fields ... $S11/W/O/st2_l2 $S11/W/R tour:713 tour_fx:781
  tour_tr:1049`). **Not met**:

  | run (42 s) | reg | cmd | tear | satcheck |
  |---|---|---|---|---|
  | l2 m2 / fx / tr | 0 / 1 / 0 | 18 / 23 / 17 | 2 / 4 / 1 | 1 / 1 / 0 |
  | l2x m2 / fx / tr | 0 / 0 / 0 | 19 / 15 / 15 | 3 / 3 / 3 | 1 / 1 / 0 |
  | level 1, `drive_cov0` on the gate's ext build, 62 s (`$S11/tools/g1.tcl`) | 6 / 6 / 12 | 47 / 59 / 523 | 5 / 10 / 102 (vbl 0 / 1 / 0) | 1 / 1 / 0 |

  Level 2's entries, all of them: late play-field copies (HMMM 48-50 x 28-32 at the lifts, frames
  155-305 and 606-662, still running at line 0), 16 x 16 HMMMs into the page on screen in the play area
  (frames 638-644, `vdp_cmd` from the scroll engines' redraw; the tears are among them), `R#46` from
  `fqs_go` (fx, frame 617); satcheck at game frame 0 (VRAM's SAT ends at sprite 0, the first list's
  buffer unpublished; level 1 identical at its frame 0). Before the guard fix, 69 more "tears" were the
  BOBs' scratch writes (LMMM TIMP to page 3 line 112: (193, 880)) misread through the HUD's R#2/R#23.
- Tile cache at the stills: `python3 -I $S11/tools/tcchk.py build/msx/level2.vram $S11/W/O/still/*/g*`:
  256 slots each, **0 differ** from level 2's sheet, links right (21 stills, 3 machines); against
  `level1.vram` 256 of 256 differ (the control).
- **4.4's level-1 rows / the gate**: `sh tools/bstest/l2base.sh builds $S11/G` (PASS), private MCP
  `source load.tcl; source l2base.tcl; l2b_chain {$S11/G} {$S11/G/all.done}` (227 jobs, 0 time outs),
  `sh tools/bstest/l2base.sh check $S11/G $IMPL/base`: **l2base: PASS** (`$S11/G/l2base_check.log`: regress
  45 PASS; die/over/end 901/1,249/517 rows 0 differ; start m2/fx/tr all 0; field 860_m2 A 3 / 177 px =
  base, 860_fx A 2 B 3 / 124 px, others 0; 10 stills identical; LOCKSTEP 2,998 lists 0 differ; effects
  800 starts, SCC 57,475 and PSG 33,390/33,393 sound ticks 0 differ). Run on HEAD's harness; after the
  guard change `l2b_jobs`' `st_m2/fx/tr` rerun: reg pal cmd cpu vbl tear 0, SATs 0, lost 0 (the change
  only removes reports: Brainstorm's guard tears are all 16 x 16 copies into the play page, the range's 0).
- **BANK_L2: 1,587 B free (6,605 used)** in every option set: `sh tools/bstest/variants.sh $S11/variants`
  + `python3 -I tools/bstest/l2base.py banks $S11/variants > $S11/banks_variants.txt`: 46 of 48 build
  (DEMO_ACTORS 2/5: -27 B as before); the fixed area as step 8's in every set (product 380, lowest 245
  `p_pzdiag`); LC2 4,842, LC3 4,866, FRONT 1,943.
- `make test` (`$S11/make_test2.log`): 283 tests, the 4 known failures only (failures=3, errors=1).
- Pictures looked at (`$PY -I tools/bstest/l2frame.py SNAP build/msx/level2 build/msx/hud OUT.png`, tour's
  frames 0, 60, 530, 660, 1300, 2000, 2565 on each machine; sheets `$S11/W/O/still/sheet_*.png`): the
  start by L0's shaft, the trolley ride over vat 0 (state 14), the hostage beside a type-4 gunman, trolley
  3, a lift ride up the grey shaft, the roof with "ARREST ARMED EMEMY." / "ARREST SUC..."; HUD 07:30 (08:30
  later: the timer the bench's), 0010050, two heads, weapon 000. Every sprite pixel exact but 26-34 at the
  roof (two BOBs overlapping, step 9 saw the same; the frames change at step 12); the play area equal to
  msxframe's map but the play-field lifts and hostage and the map patches (msxframe models neither:
  305-1,501 px, every region looked at: the lift, the hostage, a broken floor, a map object's look at
  rows 39-40) and the first picture's HUD timer (20 px). The new types stay invisible until step 12.

### Open issues
1. 4.2 check 1's guard classes (above): milestone 2's, with level 1's same classes. `ok` is false for this
   item only.
2. `tools/mapcmp.py` (51 rows) and msxframe's tile-area line: see "What the next agents need".
3. Level 2 runs under 25 ticks a second in busy parts (42 s: 713 ticks on the MSX2 with ENEMY_CAP 0, 957
   with the product's caps, 1,050 on the turbo R); level 1's `drive_cov0` the same (995 in 62 s on the MSX2).
   For the rates of milestone 2, not a logic issue.
4. Optional, not done: step 8's h0/h1 as `l2drives.py` references (re-proven on the full port above);
   step 9's bullet/explosion fields in `amiga_ram_l2.tsv` (the 1,022 is quoted in tests and docs; the
   scratch set passes).

## Step 12: the global sprite pool in the ROM (2026-10-28)

**Done.** Commit **db4f720** (18 files, explicit paths): `Makefile`, `tools/mkrom.py`, `msx/{msx.inc, rc2.asm,
field.asm, sprites.asm, bob.asm, player.asm, level2obj.asm}`, `tools/objcmp.py`, `tools/bstest/{romdiff.py,
relocheck.py, l2base.py, hz.tcl}`, `tests/{test_level2_rom.py, test_bstest.py}`, `docs/{HARNESS.md,
MSX_ARCHITECTURE.md}`. Records in `$IMPL/s12` (`S12`): `A` (the relocation layer's builds), `B` and `H`
(the commit's prod/ext/l2: product **6cb5693e59e9ff59**, l2 **51c58e227195cf68**), `X/l2` (`EXTJOY=1
LV_TEST=2`, product caps: 379316419a91e261), `W/R` (the six l2 builds), `G` (the gate's logs), `bench`
(the bench's draw_bob records), `objs2` (4.2 check 3), `still`, `stillx` (stills, PNGs, `sheet.png`),
`tools/` (scratch: `recext.py`, `pixext.py`, `desccheck.py`, `hashcmp.py`, `relo.sh`, `ovl.py`, `zoom.py`,
`objs.tcl`, `cut.py`, `mcpd.py`/`mx.sh`). build/msx now holds the pool (`sprites.*`, from the Makefile's
command; robocop.* unchanged, hashed before/after) and build/sprites/catalog_l2.json (= step 10's).

### What was built
- **The pool in place**: `sprites.bin` at `SPR_BASE_BANK` (27 banks; every later block +4, once). Bank map
  (1 MiB, **123 of 128 banks**): 0-1 fixed; 2-9 code; 10-17 tiles; 18-20 map; **21-47 pool**; 48-49 HUD;
  50 attributes; 51 HUD image; 52 level tables; 53 atlas; 54-55 dynamic frames; 56-62 title; 63-68 game
  over; 69-74 voice; 75-80 SCC/FM music; 81 SCC effects; 82 PUZL; 83-91 its gfx/music; 92 FRNG; 93-107 its
  data; **108 BANK_L2; 109-116 L2 tiles; 117-118 map; 119 attributes; 120 tables; 121-122 L2_ATLAS**;
  123-127 free. The SCC test values and the 3Fh rule pass (mkrom's checks).
- mkrom: `FIELD_ID0` D0h; `hash_table`/`level_frames`/`l2_hash`/`pool_above`; level 1's BOBHASH from
  `sprites_l1.json` (190 sprite entries identical, its 40 play-field ids +8); **level 2's**: its own sprite
  frames with level 2's ids, `BOB_HIDDEN` (FEh) for type 1's torso frames ($404D0, $40674), level 1's 26
  play-field frames it shares (level 1's atlas, ids D0h + level-1 fid), its own play-field frames off.
  `L2_ATLAS`/`L2_ATLAS_BANKS` in banks.inc (placed, unused: lv_desc2's `lv_fimg` is still `L2_FIMG` =
  level 1's atlas). Descriptor fields **`lv_sidx`** (2: `SPR_BOB_INDEX_Ln`) and **`lv_spark`**
  (`SPR_SPARK_Ln - 1`), `LV_SIZE` 27. `LV_SBOBS` not added: no code reads `SPR_BOBS`.
- **Step 10's notes, fixed** (pixel extents from the records' patterns: level 1 has no pixel outside its
  place's box, level 2 only the 16 joints: 20-21 lines above, 2 px beside): the BOBHASH slot's last byte =
  those lines; `bf_vis` keeps a record while that picture (2 px wider) is in the play area (the legs' call
  below the view no longer drops the joint); `O_TOPU`/`V_TOPU` and `sb_object`'s park test use the first
  line with pixels; `BOB_HIDDEN` frames take no object. Neutral for level 1 (all 0; verified by the gate).
- **Found and fixed**: types 1, 2 and 16 draw their muzzle flash first, so the parts after it changed
  identity on every shot (the legs' object showed the flash's frame for a picture, objcmp "late, other
  size"): `level2obj.asm` `l2_flash` draws it under owner + 1, as RoboCop's flash has its own owner.
- Fixed area +65 B (product 380 -> **315**; lowest DIAG+PZ_TEST 245 -> **180**), FRONT -6, BANK_L2 -18
  (**1,569 free**). 46 of 48 option sets (DEMO_ACTORS 2/5 overflow as before).

### Checks (exact commands, results)
- Relocation layer (`$S12/A`: this commit's mkrom + msx.inc + include names, no readers): `romdiff.py
  --blocks BASE.rom A.rom --allow SPR_BASE_BANK,LEVEL_BANK,L2_TAB` (base = `$IMPL/s11/b/prod`,
  `s11/G/R/ext`, `s11/W/R/l2`): **PASS** x3, every other data block identical at its new bank;
  `$S12/tools/hashcmp.py`: LEVEL_BANK's BOBHASH 190 entries identical, 40 ids +8, the rest of the bank
  identical. `relocheck.py BASE A BASE.labels A.labels 0 1 2 3 4 5 6 7 8 9 BANK_PUZL BANK_FRNG BANK_L2`:
  only relocated words and one-byte bank operands (FIELD_ID0, HUD_BANK + 1, the music tables'...) except
  FRONT's descriptor region (102 bytes: lv_desc2/lv_pal1/lv_voffy1 moved 3/6 bytes) and `ld hl,lv_desc -
  LV_SIZE` (1 byte); `$S12/tools/desccheck.py`: every old field equal (banks +4), new fields 8372h/193 and
  85C4h/199, lv_pal1/lv_voffy1 equal: PASS (prod, ext, l2). Commit vs A: data blocks all identical, banks
  2-9/PUZL/FRNG relocated words only (`relocheck: PASS`); the fixed area and BANK_L2 hold the edits.
- Level 2's logic: `sh tools/bstest/hz.sh l2builds $S12/W/R`; MCP `hz_l2 {$S12/W/O/l2} {$S12/W/R} tr`;
  `sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv $S12/W/O/l2 $S12/W/R`: **level 2:
  PASS (20 traces)**, lost 0, pools <= 19/23; with `$IMPL/s9/extra.tsv`: PASS.
- **4.2 check 3**: bench `~/.venvs/msxports/bin/python -I tools/amigaemu.py game --level 2 --carry
  10050:2:0:good --gframes G --drive build/emu/l2_NAME.drive --stop-at-end --bobs $S12/bench/NAME_bobs.jsonl`
  (end, t1left, barrel, drone, tour: every drawn frame is in level 2's table); MCP `hz_chain
  [hz_l2_objs_jobs DIR $S12/W/R {end t1left barrel drone tour}]` (15 jobs); `python3 -I tools/objcmp.py
  BOBS DIR/NAME_M.txt --sprites build/msx/sprites_l2.json --rows N [--procs ...]`. Types 1 (obj01_joint,
  obj01_update), 5, 6, 49 on the three machines: exact 24-1,896 per run; **no extra, no "no frame"**; the
  rest: "missing, left out" (budget, ENEMY_CAP=0), "missing, loading"/"late" (same BOB, a picture), type
  5's growing drip as "late, other size" (16x16 -> 32x16, same routine), and "missing" only in ticks held
  while the view moves (t1left frames 80/181/301 after teleports; drone/tour 1-2 at an edge). Before
  `l2_flash`: one type-1 "late, other size" (flash -> joint) on the MSX2.
- **Pictures** (`hz_l2_still_setup` via `$S12/tools/objs.tcl s12_still_jobs`, then `$VPY -I tools/msxframe.py
  SNAP build/msx/level2 build/msx/hud OUT.png --sprites build/msx/sprites --level 2`): l2 build (t1left
  150-260, barrel 76-662, drone 50-300) and X build (product caps, + tour 1700-2300), three machines: sprite
  pixels exact in most; every not-exact still becomes exact with the SAT's real order (`$S12/tools/ovl.py`),
  but drone m2 g0050 (10 px behind the V9938's right border, counted not checked). Looked at, beside the
  bench's play field (`--screenshot`): type 1 joint (striped vest, grey trousers, rifle), the drips under
  the pipe, type 6's tyre, type 49's red drone; no garbage. In the l2 build t1left's crowd (3 enemies +
  RoboCop on one line) shows OR drops and VDP-hidden sprites: ENEMY_CAP=0's, not the product's.
- **Step 10's question** (21-34 sprite px "not exact" at steps 9/11): **the check's limit**: msxframe puts
  objects in front by number, the VDP by SAT run; s11's roof stills (3 machines) give 1397/1397 and
  1522/1522 with the SAT's order (which there also matches the original's draw order).
- **The gate**: `sh tools/bstest/l2base.sh builds $S12/G`; private MCP (`$S12/tools/mcpd.py $S12/mcp` +
  `mx.sh`) `l2b_chain {$S12/G} {$S12/G/all.done}` (227 jobs); `sh tools/bstest/l2base.sh check $S12/G
  $IMPL/base`: first run **FAIL in one verdict**, the exact title record: game VRAM at tick 300 108 bytes =
  SAT entries 28-31 of both sprite sets in another order (two 16x16 boxes at 85/140 that the base itself
  swaps between its two sets; this build reached tick 300 one VBLANK later: 123.040 s / 123.023 s; RAM,
  title, music identical). Judged: the BOB runs' order moves with CPU time (LOCKSTEP records, timing fixed:
  2,998 lists **0 differ**). `l2base.py fresh` now accepts only that (`sat_order`: every differing byte in
  the two sprite sets, each set the same entries; unit test with negative cases; HARNESS.md 5.21). Rerun
  `check`: **l2base: PASS** (`$S12/G/l2base_check2.log`): regress 45/45; die/over/end 0 differ; start check
  all 0 (m2/fx/tr); field check 0 differ in every window (860_m2: base 3); 10 stills identical to the
  base; LOCKSTEP 0 differ; effects PASS.
- `sh tools/bstest/variants.sh $S12/variants` + `l2base.py banks`: 46/48 (`$S12/banks_variants.txt`).
- `make test`: 289 tests, the 4 known failures only (`$S12/make_test.log`).

### For step 13 (and later)
- Level 2's play field: set `lv_desc2`'s `lv_fimg` to `L2_ATLAS` (2 banks: field_upload reads one), the
  field tables from `sprites_l2_field.inc` (fids differ from level 1's), and in `mkrom.l2_hash` replace
  the shared level-1 field entries by `level_frames({"field": spool[2]["field"]})` (silhouettes:
  sprite frames with a "field" key, already level 2's ids).
- **Until step 13 the trolley shows nothing** (milestone 1 drew it as level 1's sprite record 0; in level 2
  it is play-field frame 34), nor types 2, 14, 16's bodies and silhouettes.
- 4.2 check 6 (stills) must order objects by SAT run (msxframe orders by number): see `ovl.py`.
- The fixed area: 180 B in the lowest set (3.2's budget for steps 14-15: 140-220).

### Open issues (engine, pre-existing, level 1 the same; for milestone 2)
1. **BOB runs leapfrog**: two BOBs that both change take each other's SAT entries list by list, so their
   overlap alternates every picture (level 1, tick 300 of a new game: 67 px at 140/85, both builds).
2. **SAT order vs the original's draw order**: tour g2100, type 13's 56F12h in front of 56A12h, the
   original the opposite (30 px).
3. `bf_vis` decides per tick: a BOB entering while the view moves between ticks shows a picture late.
4. Shared types 4/12/15: a slot reused by another routine's frame shows the old frame for a picture
   (objcmp "late, other size" of other routines, tour/t1left on the turbo R).

## Step 13: level 2's play field (2026-10-28)

**Done** (the gate's verdict at the end of this section). Commit **1b10b8a** (17 files, explicit paths):
`tools/mkrom.py`, `tools/mapcells.py`, `msx/{field.asm, isr.asm, tiles.asm, cold.asm, level2.asm, msx.inc,
rc2.asm}`, `tools/msxframe.py`, `tools/bstest/{fieldcheck.py, hz.tcl}`, `tests/{test_level2_rom.py,
test_bstest.py, test_msxsprites.py}`, `docs/{HARNESS.md, MSX_ARCHITECTURE.md}`. Records in `$IMPL/s13`
(`S13`): `W/R` (the six l2 builds), `X/l2` (`EXTJOY=1 LV_TEST=2`, product caps), `G` (the gate), `fd`, `fdb`
(field checks, l2 build: `*.check.txt` and contact sheets; the records deleted), `fdx`, `fdxb` (the same on
X), `still` (36 snapshots + msxframe PNG/txt), `objs`, `start` (the whole tour under the guard, X), `ol`
(lines above 8: this build and step 12's), `gd` (VDP command traces), `tools/` (scratch: `s13.tcl`,
`fdall.sh`, `fdsum.py`, `fdbobs.py`, `fdlines.py`, `fdpic.py`, `fdbench.py`, `ring.py`, `crop.py`,
`sheetpic.py`).

### What was built
- **Level 2's own play field.** mkrom: level 2's BOBHASH takes its own play-field frames (`sprites_l2.json`
  "field": ids D0h + index; types 2, 14, 16 with their silhouette's sprite id, the suspect's blink and
  the hit flashes) instead of level 1's shared ones; its atlas at `L2_ATLAS` cut by `atlas_banks` into
  two banks with a table each (count's bit 7 = another bank follows; a one-bank atlas, level 1's, is kept
  byte for byte); `gen/field_l2.inc` (`field_tab_l2`, `field_look_l2`, `FIELD_LATE_l2` ...: level 2's
  tables with suffixed names; its `field_dyn`/`dyn_tab` are checked equal to level 1's and left out).
- **The descriptor** (`LV_SIZE` 32): `lv_dynp` (+27, the dynamic slot's VRAM page: 3; level 2: 2, with
  `lv_dyn` 224), `lv_tcn` (+28, 2 bytes: the tile cache's slots negated: -256, -224), `lv_fld` (+30: the
  level's field block in BANK_FIELD, `fld_l1`/`fld_l2`). `lv_fimg` of level 2 = `L2_ATLAS`. mkrom checks
  that each level's atlas, dynamic slot and tile slots do not overlap in VRAM (`TC_SLOTS`, `DYN_PAGE`).
- **field.asm**: `fb_init` copies the level's block (FIELD_LATE, FIELD_DYN0, FIELD_DYN1, field_tab,
  field_look) to `fb_flate` ... `fb_flook` (0x064F-0x0655, free per msx.inc) and the engine reads them there
  (the trolley, frame 34 >= FIELD_LATE_l2 33, is copied late as the lift); the dynamic slot's copies use
  (`lv_dyn`, `lv_dynp`); `field_upload` walks the atlas bank by bank. `tiles.asm tc_load` wraps at
  `lv_tcn` (same 3 bytes), `cold.asm tiles_init` fills the level's slots (TC_TILE of absent slots FFFFh).
  "lv_select's atlas size": nothing else needed (`field_upload` takes the banks; no LV_FLINES field).
- **The vats' tables (for step 14)**: `L2_VATS` = 9700h in L2_TAB at 8000h (`mapcells.vat_tables`): +0 64
  bytes per map row (bit v: vat v covers it); +40h 8 bytes per vat [first column, columns, first row, rows
  (record rows + 2), its first index in vat_shown, FFh x3]; +80h the 48 tiles (words, LE) of T0[0..15],
  T1[0..15], T2[0..15] (sheet tiles: `.otile` at word >> 7). `vat_sh0` (103 bytes, `gen/vats_l2.inc` in
  BANK_L2, `VAT_COLS_l2`): each column's static look; `l2_init`'s fresh path copies it to `vat_shown` and
  zeroes `vat_disp` + `vat_chg` (110 bytes). Step 14 defines vat_disp's encoding (and clears it in
  `engines_init`/`engines_jump`): nothing reads vat_disp yet.
- **Two engine faults found by the new field check and fixed** (both also in level 1's code paths):
  1. A piece across the V9958 ring's x 256 AND y 256 needs 4 HMMMs; the pair mechanism copied 2 per blank,
     so the trolleys (y 508-554, across ring line 256) showed their top 4 lines 4 px ahead for one picture
     at every step while crossing x 256 (9-23 pictures a ride, MSX2+/turbo R). Now `fcp_wait` prepares
     every part (fb_cmd + up to 3 in `fb_cmd2` = EDC0h-EDECh, `fb_cn` EDEDh, `fb_cp` EDEEh; F1EFh-F1FDh
     freed) and `isr_fbgo`/`ifg_fin` start each when the one before is done (`ifg_nxt`); `fb_wait`'s
     fallback starts what is left in a row.
  2. `do_publish` counted the picture (`fb_tick`) after `publish`: when the split's uploads readied the
     list and the VBLANK took it before that, `fb_pend` took the list's own items for the next picture's
     and the list went on screen without them (the barrel lift missing for 6 pictures, MSX2). `publish`
     (isr.asm) now counts it before `pk_state` is set.
- Fixed area: product 298 B free (step 12: 315), lowest real set DIAG+PZ_TEST 163 (180), DEMO_HUD 76; FRONT
  1,897; FIELD 1,183 (EXTJOY builds 1,142); BANK_L2 1,445. 46 of 48 option sets (DEMO_ACTORS 2/5 as before).

### Checks (exact commands, results)
- Builds: `sh tools/bstest/hz.sh l2builds $S13/W/R`; `sh tools/bstest/build.sh $S13/X/l2/rc2_l2.rom EXTJOY=1
  LV_TEST=2`. `python3 -I tools/bstest/romdiff.py --blocks <s12 prod> <s13 prod> --allow L2_TAB,L2_ATLAS`:
  PASS (every data block identical but L2_TAB and L2_ATLAS); relocheck on PUZL/FRNG: relocated words only.
- **Level 2's logic**: MCP `hz_l2 {$S13/W/O/l2} {$S13/W/R} tr`; `sh tools/bstest/hz.sh compare --fields
  analysis/amiga_ram_l2.tsv $S13/W/O/l2 $S13/W/R`: **level 2: PASS (20 traces)**, 0 differ, lost 0.
- **4.2 check 2 (field check)**: MCP `hz_chain [hz_l2_field_jobs {DIR} {ROM} {LABELS} {<repo>/build/emu/l2_tour.drive}
  {0 300 150 300 495 300 735 200 960 250 1150 300 1255 350 2385 400 2420 400 2500 300}]` (+ barrel's
  drive {70 300 300 300}), then `sh $S13/tools/fdall.sh DIR` (= `$PY -I tools/bstest/fieldcheck.py DIR/W
  build/msx/level2 DIR/W.png --level 2` per window). Coverage (`fdsum.py`): types 14/16 (frames 11-16),
  the lift (33), the trolley on all four rides (34), the hostages (0-8), the suspect (9, 10). Results:
  - product caps (X): **0 differ in every window on the MSX2, MSX2+ and turbo R** but `2385_fx`;
  - trace build (l2, ENEMY_CAP=0): 0 differ but `2385_fx`, `150_tr` (1 picture) and `735_tr` (1 picture, 5 px);
  - `2385_fx` (85/87 pictures, both builds): all at tick 2412, the view sweeping x 1008 -> 176 after the
    drive's teleport at 2410 (1,400 px in one tick), empty field lists: the V9958 scroll's catch-up, a test
    artifact (no teleport in play);
  - `150_tr`: a 2-piece staged item (type 16's body merged with the lift) whose 2nd piece the main loop
    starts during the picture (the guard's class (3) of step 11, `fst_more`); `735_tr`: a trolley entering
    at the right edge drawn one picture before its list, which waits for the other trolley's copy (two
    late items take two blanks). Both pre-existing engine classes, turbo R, trace build only.
  - Negative controls: a BOB shifted 3 px in both recorded lists -> 29 of 30 pictures flagged; a hostage
    spliced half old/half new -> flagged (37 px) while two hostages one picture apart are not.
- **4.2 check 3**: MCP `hz_chain [hz_l2_objs_jobs {$S13/objs} {$S13/W/R} {tour end barrel}]`; `python3 -I
  tools/objcmp.py $IMPL/s12/bench/NAME_bobs.jsonl $S13/objs/NAME_M.txt --sprites build/msx/sprites_l2.json
  --rows N`: no "extra", no "no frame" (tour m2: exact 5,325, left out 2,133, missing 409, loading 35, late 12;
  more "left out" than step 12 in `end`: the suspect's blink silhouette now takes sprites in the
  ENEMY_CAP=0 crowd). Field BOBs: `python3 -I $S13/tools/fdbench.py BENCH.jsonl RECDIRS` (the list on
  screen vs the bench's calls of field frames): tour 3,579 + barrel 1,888 exact; missing only in the
  teleport sweep (26, fx), 3 extra at the view's edges.
- **4.2 check 6 (stills)**: MCP `hz_chain [hz_l2_still_jobs DIR {$S13/W/R} {10 200 520 760 1000 1230 1300 2395 2456
  2464 2472 2555} l2_tour]`; `$PY -I tools/msxframe.py SNAP build/msx/level2 build/msx/hud OUT.png --sprites
  build/msx/sprites --level 2 --field`: 36 stills, **the play area exact in all**, tile area clean in all,
  sprite pixels exact but msxframe's object order (m2 g1000 25 px, m2 g2555 37, tr g2395 18: exact with the
  SAT's order, `$IMPL/s12/tools/ovl.py`; m2 g0760 8 px on lines above 8, ENEMY_CAP=0) and, at the arrest
  frame g2555, the HUD's can (171 px on the three machines: msxframe's HUD model at the level's end).
- **Looked at** (zoomed against the bench's `--screenshot`): type 14 and type 16's body (g0200), the trolley
  with RoboCop hanging (g0520), the suspect whole in the V9958 ring across its x 256 (`ring.py`, g2456,
  g2464) and its white blink silhouette over it (g2555); type 16's frames against the Amiga's
  (`t16frames.png`). (The bench's screenshot is its front buffer, two frames behind the draw calls.)
- **4.2 check 7 / 1 / 5** (product caps, the whole tour under the guard: MCP `hz_chain [hz_l2_start_jobs
  {$S13/start} {$S13/X/l2/rc2_l2.rom} {$S13/X/l2/rc2_l2.labels} 110]`): patcheck 0 bad, lost 0, pools
  <= 19/23, satcheck 0-1 (frame 0); guard reg 0/7/5, cmd 68/102/62, tear 2/8/11 (the known classes);
  **sprlines 1,125 / 834 / 769 frames with a line above 8 — NOT 0**: `rc2_overlines` (`$S13/ol`) shows
  every one is RoboCop (4) beside a level-1 walker drawn as legs + torso (types 3, 4, 15: 3 + 3 where the
  parts meet), no silhouette or play-field change among them; step 12's X build on the same route: 827
  (MSX2). Pre-existing, the sprite budget's (see open issue 1).
- The gate: see the last paragraph.
- `make test`: 295 + 3 new tests, the 4 known failures only; `test_msxsprites.py` (venv) 14 OK;
  `test_bstest.py` 38 OK. `sh tools/bstest/variants.sh` + `l2base.py banks`: 46/48 (`$S13/banks_variants.txt`).

### For step 14 (the vats' display)
- Tables: `L2_VATS` (above) + `vat_sh0`; `vat_shown` (F012h) holds looks 0-15; `vat_disp` (F079h, 103 B) and
  `vat_chg` (F0E0h, 7 B) are zeroed at a fresh level 2 only.
- `fieldcheck.py --level 2` still compares vat cells with the static ROM map (right until the vats are
  drawn); step 14 adds the vat rule (one look per column, never older). The records' RAM (0600h-09FFh,
  F240h-F27Fh) does not hold vat_shown/vat_disp: extend l2b_fd_setup's record or read them elsewhere.
- Field windows for the vats: tour's 495/735/960/1255 windows (the four rides) and `hz_l2_field_jobs`.
- The chain (`fb_cmd2`.., `ifg_nxt`) is the place to keep a vat column's 4 commands in one blank.

### Open issues (for step 16, milestone 2's acceptance)
1. **Lines above 8 sprites** (4.2 check 7 fails, pre-existing at step 12): RoboCop + a level-1 walker (legs
   + torso, 3 + 3) on one line = 10 in level 2's corridors (MSX2 1,125 of ~6,600 frames over tour). A
   design choice for the user/step 16: walkers as joint compositions (type 1's way) or another budget rule;
   decision 13 forbids cutting pieces, so the VDP now hides the walker's last sprites on those lines.
2. The staged multi-piece item (150_tr) and two late items in one picture (735_tr): pre-existing engine
   classes, trace build on the turbo R only; the product build shows neither in the same windows.
3. The fixed area: 163 B at the lowest set (3.2's budget for steps 14-15: 140-220 B) — tight; the chain
   took 18 B (isr.asm).
4. `hz_l2_start_jobs` with a time past the drive's end hangs (rc2_drive_rom pauses at its end): use <= 105 s
   on the turbo R or `set ::pause off`.
5. The HUD's can at the arrest frame differs from msxframe's model (171 px, three machines): look at it with
   step 18/19's HUD check (4.2 check 13).

## Step 14: the vats' display (2026-10-31)

**Done, but the rates disappoint on the Z80 machines** (the plan's 5: step 16 stops for the user's choice
among default 18's alternatives; the numbers below). Branch `l2-s14` (worktree `scratchpad/l2/wt14`),
commits (cherry-picked onto level2 a7c465d, steps 18 and 19) **d7d3d3e, 5e729a4, 4cd547c, abde258, 3b00f26,
bb23717**, this section's and its end's, all committed locally, not pushed (the user's order), integrated
into `level2` by fast-forward (before the cherry-pick on 7aecb40: 0d4471f, ed9c119, 9a7e0e2, 659742e,
51cca83, e074a78, 0a190f3). Files: `msx/{tiles.asm,
scroll9938.asm, scroll9958.asm, field.asm, vats.asm (new), level2.asm, msx.inc}`, `tools/{mapcmp.py,
msxreal.py, msxframe.py}`, `tools/bstest/{fieldcheck.py, l2base.tcl, vatlog.tcl (new), vatcheck.py (new)}`,
`tests/test_bstest.py`, `docs/HARNESS.md` (5.22), this file. Records in `scratchpad/l2/s14` (`S14`): `W/R`
(the six l2 builds), `X/l2` (`EXTJOY=1 LV_TEST=2`, product caps), `P` (the product), `V` (the option
sets), `G` (the gate), `vl/<window>` (the vats' logs and the guard), `hR`, `hg` (the same windows' guard
on level2 7aecb40's code), `sp*`, `spf` (speeds), `snap` + `map` (the map against the bench), `st`, `stp`
(stills and their renders), `fd`, `fdx` (field records and checks), `dbg` (the scratch tracers).

### What was built
- **The rule (tiles.asm `get_tile`)**: in level 2 (`lv_logic` = BANK_L2) every cell without a map patch
  goes to `field.asm` `vat_tile` (BANK_FIELD): a vat cell (`L2_VATS`' row bits and records) is drawn at
  its column's look on the page drawn (`vat_pg`: `vat_disp`'s nibble of that page, `8 | look & 7`, the
  look's half from `vat_shown`'s bit 3; no nibble yet: `vat_shown`'s look, which the page then holds),
  T0 on the vat's first row, T1/T2 alternating below; any other cell gets the map's tile, which
  `vat_tile` reads itself through the 8000h window (gt_map's way), so that the fixed area keeps only
  the jump. `vat_pg` is set by the V9938's `ttp_prep` (the page it draws on) and `fb_tiles` (the BOBs'
  restores); on the V9958 `vt_page` takes page 0 (its ring) whatever page a BOB item names.
- **The column refresher (msx/vats.asm, new, BANK_L2; field.asm's vat section)**: the map report's way
  (whole columns at the newest look). `vat_prep`, at the scroll engines' idle points (once a VBLANK on
  the R800, every `VAT_KZ` = 4 on the Z80; only when a vat changed, `vat_chg`), looks from `vat_rr`
  round robin for the first column in the view whose look on the page shown is not `vat_shown`'s,
  that meets no play-field BOB nor their work (the boxes of `fb_cur`, the queue, the page list,
  `fb_wbx`, and on the V9938 the page being built) and may be drawn in time; it prepares it in `vat_fr`
  (0860h, 41 bytes): its three tiles in the tile cache, the destinations, the parts. `vat_run`, when
  the beam is outside the play area (between the HUD split and the VBLANK, or in the blank after the
  VBLANK: S#2 VR), checks again that the column is still the newest, its tiles still in their slots,
  no BOB came over it, and that it ends before the beam reaches its first line with R#23 now
  (`vat_fits`: `VAT_LB` lines a row, `VAT_LP` a part's start, `VAT_LM` for the VBLANK interrupt,
  `VAT_LV`/`VAT_LB0` the blank's lines), then draws it with `cmd_lock` held: T0, T1, T2 (HMMM from
  the cache) and an overlapping HMMM that copies the T1/T2 pair down the column, cut at the page's
  line 255 (the ring); the nibble of the frame's page (`VF_EP`, never `vat_pg`) takes the look. On the V9938 the column is then copied onto
  the other page (`vat_mirror`, HMMM page to page; the flip waits for it: `s38u_step` `vat_bk`), and
  `vat_mmark` re-marks the BOBs over it there. `vat_init` (every level's `engines_init` and
  `engines_jump`) clears the state and, in level 2, `vat_disp`; `vat_bbinit` (`fb_bbinit`) gives the
  page being built the shown page's nibbles where both views hold the column. A play-field BOB piece
  with a vat cell restores its background by tiles (`fb_piece` -> `fp_tiles`, `vat_inbox`).
- **The hooks (fixed area, 75 B in the product)**: `vat_win` at `scroll_work`'s and `s38_work`'s entry
  (the VDP idle; no bank switched unless a column is ready), `vat_idle` at `sw_idle` and `s38w_idle`
  (level 2 only: `vat_on`, set by `vat_init`), one tail `vat_l2` (BANK_L2 at A000h, the routine's flags
  kept); `s38_copy_chunk` makes 1-slot chunks while a column is ready. The vats never keep `iw_more`:
  their work waits for `wait_frame`'s loop or the engines' own work (see "the cost" below).
- RAM (msx.inc): `vat_pg` F0E7h, `vat_wtk` F0E8h, `vat_rr` F0E9h, `vat_bk` F0EAh, `vat_bkc` F0EBh,
  `vat_bky` F0ECh, `vat_cmd` F0EDh (15 B; F0FCh-F0FFh free), `vat_fr` 0860h (41 B), `vat_on` 088Fh
  (page-0 RAM that TC_REF leaves free with 256 slots at most).
- **Tools**: `tools/mapcmp.py` (the map's rows from its size; vat cells at their column's look in the
  snapshot: `vat_layout`, `vat_tile`, `vat_look`), `tools/msxreal.py` (the same rule, the page from R#2
  on the V9938), `tools/bstest/fieldcheck.py` (the vats' RAM in the record, vat cells at the recorded
  page's look: class `vat-look`; never older than the look shown a picture before: `vat-older`; the four
  record lengths), `tools/bstest/l2base.tcl` (`l2b_fd_setup` records F012h-F0E6h),
  `tools/bstest/vatlog.tcl` (new: `vl_jobs`, `vl_speed_jobs`, `vl_snap_jobs`), `tools/bstest/vatcheck.py`
  (new), `tests/test_bstest.py` (`test_vatcheck_flags_a_vat_column_the_beam_drew`), docs/HARNESS.md 5.22.

### The cost, and the choices made for it
- **The game's speed** (`vl_speed_jobs`: game ticks in 25 s of `tour` from game frame 450, the l2 trace
  build, vats 0-2 in view; level2 7aecb40's code: MSX2+ 424, MSX2 351, turbo R 621). The first design
  (the vats kept `iw_more` while a column waited, so that every `feed_vdp` in the game's logic took its
  full path; "the BOBs first" in `vat_run`) cost the MSX2+ 13 % and the MSX2 4 %. Isolated: the hooks off
  with `get_tile`'s rule on 416 / 353, both off 427 / 348 (the noise is about 3 ticks), so the rule costs
  the MSX2+ about 2 % and the rest was the waiting column's `feed_vdp` path. Now the vats never keep
  `iw_more` (their work runs from `wait_frame`'s loop and the engines' own work); "the BOBs first" went
  too (it cut the MSX2+'s columns from 137 to 38 for 1 % of speed). Final: see the checks.
- **Zero glitches first**: a column is drawn whole, at the look prepared (the newest when prepared; a
  column's look cannot move on while its frame waits, so never older), started only where the beam is
  outside the play area and ended before the beam reaches its first line (`vat_fits` with R#23 now);
  later parts of its chain start while the beam is above the column (the guard's "cmd" lines, no tear).
- **The fixed area**: 75 B in the product (3.2's budget for step 14: 60-100 B): `get_tile`'s level-2 path
  is a jump into BANK_FIELD (`vat_tile` reads the map's tile itself), the two hooks share one tail. Over
  7aecb40: 298 -> 223 free, the lowest real set (DIAG+PZ_TEST) 163 -> 88, `DEMO_HUD=1` 1 B. **Integrated
  (over a7c465d, steps 18-19: 267 free): the product 192 B, DIAG+PZ_TEST 57 B** (builds: the agreed
  fallback, DIAG's `dg_probe`/`dg_rec` into BANK_MUSIC, was not needed), **`DEMO_HUD=1` -30 B: it does not
  build any more** (45 B at a7c465d; its HUD demo, about 220 B, lives in the fixed area: moving `hud_demo`
  into a bank is the fix if the set is still wanted; it overflowed before step 12 too). BANK_FIELD 143 B
  free (1,183 at step 13), BANK_L2 41 B (1,441 at a7c465d), FRONT 1,506 as a7c465d: tight for step 15. No
  new bank: still 127 of 128 banks, the 1 MiB image (the vats need no block of their own).

### Checks (exact commands, results; `S14` = scratchpad/l2/s14, `W` = wt14)
- Builds: `sh tools/bstest/hz.sh l2builds $S14/W/R` (PASS), `sh tools/bstest/build.sh $S14/X/l2/rc2_l2.rom
  EXTJOY=1 LV_TEST=2`, `sh tools/bstest/build.sh $S14/P/rc2.rom`: build OK, z80asm 12 known warnings only.
  `sh tools/bstest/variants.sh $S14/V` + `python3 -I tools/bstest/l2base.py banks $S14/V`: 46 of 48 (DEMO_ACTORS
  2/5 as before); integrated (`$S14/IV`, `$S14/i_banks_variants.txt`): **45 of 48** (DEMO_ACTORS 2/5 -D7h,
  DEMO_HUD -1Eh); free bytes above. The integrated tree's `build/msx/text.inc` made again with the
  Makefile's `msxtext.py` line (equal to the main tree's).
- **Level 2's logic**: MCP `hz_chain [hz_l2_jobs {$S14/W/O/l2} {$S14/W/R} tr]`; `sh tools/bstest/hz.sh compare
  --fields analysis/amiga_ram_l2.tsv $S14/W/O/l2 $S14/W/R`: **level 2: PASS (20 traces)**, 0 differ, lost 0.
- **The map against the bench, with the vat rule**: the bench's maps `$S14/map/tour_F.bin` (`python3 -I
  tools/amigaemu.py game --level 2 --carry 10050:2:0:good --gframes F --drive build/emu/l2_tour.drive
  --stop-at-end --dump ...`), MCP `hz_chain [vl_snap_jobs {$S14/snap} ROM LABELS {600 1000 1400 2300} {m2
  C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT}]`, `python3 -I tools/mapcmp.py $S14/map/tour_F.bin
  $S14/snap/<m>_gF build/msx/level2`: **0 differ in all 12** (8,000 cells, 604 vat cells by the vat rule).
- **4.2 check 8 (tear 0 under rc2_guard) and the rates**: MCP `source {W/tools/bstest/vatlog.tcl}; hz_chain
  [vl_jobs {$S14/vl/F} ROM LABELS SECS F ?MACHINES? ?DRIVE?]` for tour from frames 450, 850, 1250 (25 s),
  2130 (20 s) and standing still (`tour` cut at frame 520 or 2200, then no input: `$S14/still520.drive`,
  `still2200.drive`; 20 s from 540, 15 s from 2220), on C-BIOS_MSX2, the FS-A1FX and the FS-A1GT;
  `python3 -I tools/bstest/vatcheck.py $S14/vl/F`: **exit 0 in all 18: no vat column's tear, no column the
  beam drew into** (the least margin to a column's first line 10-90 lines). The guard's other tears are
  the classes level2 7aecb40's code shows over the same windows (`hg`: a guard-only job on its l2 build):
  the engines' changed-cell redraws (16 x 16, `sw_redraw` and `s38_redraw`), play-field pieces (the turbo
  R's staged item, the MSX2+'s piece across the ring's x 256 started late in the blank); 23 there, 26
  here over the 450/850/1250 windows.

  | columns drawn a second (each column's redraws a second) | MSX2 | MSX2+ | turbo R |
  |---|---|---|---|
  | tour 450 (vats 0-2, scrolling) | 1.3 (0.04-0.08) | 2.7 (0.04-0.13) | 12.8 (0.31-0.47) |
  | tour 850 (vats 1-3, the lift rides) | 1.3 (0.04-0.08) | 2.2 (0.04-0.09) | 16.4 (0.31-0.66) |
  | tour 1250 (vat 3) | 1.0 (0.11) | 1.0 (0.10) | 10.5 (0.65) |
  | standing at vat 0 (frame 540) | 0.8 (0.08) | 2.9 (0.24) | 8.0 (0.67) |

  (vats 4-6: seen for a second in tour 2130, none changed standing at 2200.) The original steps every
  odd tick (12.5 steps a second, LOGIC2.md 4.2): a column of a vat in view is redrawn every 4-25 s on
  the Z80 machines and every 1.5-3 s on the turbo R; the plan's expectation (2-3 steps a second on a
  scrolling V9938) is not met. CPU: vat_run + vat_prep 2-4 % (Z80), 6-17 % (R800, its idle time).
- **The game's speed**: MCP `hz_chain [vl_speed_jobs {DIR} ROM LABELS 25 450 ...]` on the l2 builds: MSX2+
  843 frames / 393 ticks (level2 7aecb40's code, `$S14/hR`: 874 / 424: **-7 %**; the same design one
  commit before measured 403, -5 %), MSX2 791 / 341 (801 / 351: **-3 %**), turbo R 1068 / 618 (1071 / 621).
- **4.2 check 2 on the vat windows, scrolling up and down** (the four lift rides and vats 4-5): MCP `hz_chain
  [hz_l2_field_jobs {$S14/fd} {$S14/W/R/l2/rc2_l2.rom} {...labels} {W/build/emu/l2_tour.drive} {495 300 735
  200 960 250 1255 350 2140 260}]` and the same on X (`$S14/fdx`); `$PY -I tools/bstest/fieldcheck.py DIR/W
  build/msx/level2 DIR/W.png --level 2`: **0 differences in all 30 windows** (both builds, three machines,
  9,180 pictures; every vat cell at its column's look on the page shown, no "vat-look", no "vat-older").
  On the way it caught a real fault: on the MSX2 the page shown kept an older nibble than its column
  (13-22 pictures a window: `vat_run` wrote the nibble of `vat_pg`, which the V9938's tile draws had
  meanwhile set to the page being built), fixed in bb23717 (e074a78 before the cherry-pick); and its first "vat-older" rule took the
  looks' recurrence for steps back (fixed: only a change of a column's look is dated).
- **Stills, looked at** (MCP `hz_chain [hz_l2_still_jobs {$S14/st} {$S14/W/R} {520 900 1000 1300 2200 2380}
  l2_tour]`; `$PY -I tools/msxframe.py SNAP build/msx/level2 build/msx/hud OUT.png --sprites build/msx/sprites
  --level 2 --field`, now with the vat rule): the play area exact in all 18 (sprite pixels exact but
  msxframe's object order on the MSX2 at g0900, g1000: 44 and 25 px, step 13's note). Looked at, zoomed
  (`$S14/stp/crop_*.png`): vat 0 on the MSX2 (g0520), vat 3 on the MSX2+ (g1300), vats 1-2 on the turbo R
  (g1000): whole columns, each at one look, the surface's bubbles at a different phase column by column.
- `make test`: 299 tests, the 4 known failures only (failures=3, errors=1), before and after the integration.
- **The gate** (`l2base.sh builds $S14/G`; MCP `source {W/tools/bstest/load.tcl}; source
  {W/tools/bstest/l2base.tcl}; l2b_chain {$S14/G} {$S14/G/all.done}`; `sh tools/bstest/l2base.sh check
  $S14/G scratchpad/l2/base`), on step 14 over level2 7aecb40 before the integration: **l2base: FAIL on one
  level-1 still, all else PASS**: regress 45 verdicts PASS; level 1's traces, the start check, the field
  check (the known hostage tear only), the LOCKSTEP records (3,000 lists, 0 differ) and the effects PASS;
  the stills 9 of 10 identical, `m2_g1490` 24 px apart (the conveyor's gear one animation frame later) and
  msxframe 468 against the base's 462. That snapshot (the HUD split of game frame 1490's first new list)
  came one VBLANK later (304.2872 s against 304.2705 s): the hooks' few T-states in level 1's V9938 engine
  pushed that frame's list past a VBLANK, so the picture is the display one step on. No level-1 logic or
  list differs (the traces, LOCKSTEP's 3,000 lists); the stills are the one verdict of the gate that is not
  blind to CPU time (a level-1 still taken a fixed VBLANK count after its frame's start would be).
  **The integrated tree** (step 14 cherry-picked onto level2 a7c465d; `l2base.sh builds $S14/IG`, `hz.sh
  l2builds $S14/IG/L2R`; MCP `hz_chain [concat [hz_l2_jobs {$S14/IG/O/l2} {$S14/IG/L2R} tr] [rgr_jobs {$S14/IG}
  all] [l2b_jobs {$S14/IG}]] {$S14/IG/all.done}`, 252 jobs, as step 19's): `hz.sh compare --fields
  analysis/amiga_ram_l2.tsv $S14/IG/O/l2 $S14/IG/L2R`: **level 2: PASS (23 traces)**, `cont` 301 rows on the
  three machines, `over`, `flow_l2_end` 259; `contcheck.py` cont, cont_fx, cont_tr (`--fire`), cont2
  (`--again`), cont_nf (`--no-fire`), over (`--none`): **PASS** (the vat state equal before PIC9 and at
  `lv_cont`'s entry); `sh tools/bstest/l2base.sh check $S14/IG scratchpad/l2/base`: **regress 45 verdicts
  PASS** (the fresh title's exact record too), everything else PASS, **the same one still `m2_g1490`
  FAILs** (24 px, msxframe 468 against 462: the timing above). Against level2 a7c465d's records
  (`scratchpad/l2/s18/I`) the same still, and the fresh title's exact RAM reads as 17 bytes apart: I's
  `fresh/xbase_*` is the main base's record (its level-table pointers 14 B away) judged with a7c465d's
  labels; our record equals I's own `xnew` there (`ac_mkptr` 9959h, `ac_mktab` 9953h, `ac_diff` 9933h).
  The vat checks again on the integrated l2 build (`$S14/ivl`, `$S14/ifd`, `$S14/ispf`): `vl_jobs` 450 and
  850 on the three machines: **no vat column's tear** (MSX2 1.6 / 1.4, MSX2+ 2.6 / 2.7, turbo R 12.5 / 16.6
  columns a second); the field windows 495, 735, 1255 on the three machines: **0 differences, 0 older**;
  the speed (25 s from frame 450): MSX2+ 401 ticks (-5 %), MSX2 344 (-2 %), turbo R 620.

### Open issues (for step 16 and the user)
1. **The rates disappoint on the Z80 machines** (the table above): the plan's 5 applies, step 16 stops
   for the user's choice among default 18's alternatives (a fixed half rate; tearing allowed, about twice
   the rate on the V9958; only the surface row while a V9938 scrolls; the logic report's surface row at full
   rate and the body round robin). What limits them: one column a window, made ready only at the engines'
   idle points (the vats never keep `iw_more`), each 40-120 lines of VDP time (T0, T1, T2 and the overlap
   copy) with the CPU waiting part by part. Measured and left: keeping `iw_more` while a column waits
   (MSX2+ about 2.5 x the columns, -13 % speed).
2. **The game's speed** in the vats' stretch: MSX2+ -5 to -7 %, MSX2 -3 %, turbo R 0 (the checks). About
   2 % of the MSX2+'s is `get_tile`'s rule (every level-2 cell without a patch goes through BANK_FIELD);
   a RAM row filter in the fixed area (about 10 B) would take the cells off the vats' rows out of it.
3. **Room**: BANK_L2 45 B and BANK_FIELD 143 B free (step 15 is field.asm's), the fixed area 223 B in the
   product, 88 B at the lowest real set, `DEMO_HUD=1` 1 B.
4. The guard's other tears are older than this step (the same classes on level2 7aecb40's code over the
   same windows): the engines' changed-cell redraws (16 x 16: `sw_redraw`, `s38_redraw`) and play-field
   pieces started late (the MSX2+'s piece across the ring's x 256 at the picture's top line; the turbo R's
   staged item). Not from code this step touched: left to step 16.
5. On the turbo R with no vat changing in view, `vat_prep`'s calls take 8-12 % of the time in
   `wait_frame`'s loop (idle time: the game's speed unchanged); a `vat_chg` test before the bank switch
   would cost fixed-area bytes.
6. Vat 6 never comes into `tour`'s view, vats 4-5 for about a second (tour 2130): checked only there.

## Step 20: Brainstorm's second visit (2026-10-31)

**Done.** One commit (10 files, explicit paths: its hash is in `git log`): `tools/msxpuzl.py`, `tools/mkrom.py`,
`msx/puzl.asm`, `Makefile`, `tools/bstest/stepcheck.py`, `tools/bstest/check_all.sh`, `tests/test_msxpuzl.py`,
`tests/test_bstest.py`, `docs/HARNESS.md` (5.5's rows, 7's milestone-3 note), this file. Records in `$S20` =
`/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/l2/s20`:
`A` (20 option-set builds of HEAD 7c8635a) and `A2` (its `regress.sh builds` and `rgr_chain all` records, made
this step's base: no new l2base path was written when it started), `C`, `C2` (the same of this commit), `B`, `B2`
(the plan's mechanism, rejected: below), `look` (extra visit-2 runs), `png`, logs, and the scratch scripts
`builds.sh`, `snapcmp.py`, `seqcmp.py`, `palcheck.py`, `puzldiff.py`. The worktrees `wt0`/`wt1` are removed.

### What was built
- **Converter** (`tools/msxpuzl.py --visits 1,2`, now the Makefile's line): visit 2's 9 TV pictures are a blob
  of their own, `puzl_tv2.bin` (28,800 B); `puzl_gfx.bin` stays visit 1's (56,704 B, byte-identical);
  `puzl_2.pal`; `puzl.inc`: `PZ_GFX_TV2` 0 (in `puzl_tv2.bin`), `PZ_VISITS` 2, `PZ_CUR_COL_2` 14
  (`PZ_CUR_COL2_2` 14: visit 2's COLOR19 and COLOR18 both land on its entry 14, 655). Without `--visits`
  every output is byte-identical to before.
- **mkrom**: `puzl_tv2.bin` after the last block (level 2's atlas): `PUZL_TV2_BANK` 123-126,
  `PUZL_TV2_BANKS` 4 (banks.inc; the summary line names it); it refuses a conversion without visit 2
  (`puzl.inc` `PZ_VISITS`, the file, its size, `PZ_GFX_TV2` 0, `puzl_gfx.bin`'s size); `gen/puzl_2_grade.pal`.
  **127 of 128 banks: 1 MiB** (one left: the next block makes the product 2 MiB, default 47).
- **`msx/puzl.asm`: visit 2 out of line; visit 1 runs its old code instruction for instruction.**
  `bs_stage`'s visit-2 fall-through keeps its 9 bytes (`ld de,PZ_GFX_TV2` became `jp bs_v2`). `bs_v2`, after
  `puzl_tab.inc` (so every old label keeps its address): the boards, `pz_pal` = `pz_pal2` (the graded visit-2
  palette), `bs_show2` (`bs_show`'s 13-instruction head, keep the two equal; then Ellen's pictures from
  `PUZL_TV2_BANK` through `rd_atb`, A = a blob's first bank, which joins `rd_at` at `rd_at1`; then `jp bsw_tv`:
  `bs_show`'s own TV loop and the rest, the cursor's colours by its own visit test), back at `bs_vr`. Visit 2's
  entry does the same work as visit 1's (no second upload). Quirk 5 as it was: `bfd_out` puts `pz_pal1` back
  at every fade-out's end, so boards 1-3 fade in with visit 1's colours on Ellen's face.
- BANK_PUZL against HEAD: all 1,490 labels at their addresses; before the old end only 4 bytes differ
  (A03Ch-A03Eh `jp bs_v2`, A4D5h `PZ_CUR_COL_2` 0Fh -> 0Eh), neither run by visit 1; 107 B appended
  (`puzl_end` AE12h -> AE7Dh): **4,483 B free** (4,590). Every other bank is HEAD's.
- **`pz_tvb` (C6AAh) is not used.** The plan's mechanism (`rd_at` reading its base from `pz_tvb`, set in
  `bs_stage`) was built first (`B`, `B2`): it adds about 113 T to visit 1's entry, and the asynchronous renderer
  turns that into other pictures. Its uploads and every picture stayed valid (20 traces 0 differ, every still
  equal to its render, `regress.sh check B2 A2` PASS, 45 verdicts), but 18 of 53 visit-1 snapshots differed
  from HEAD's (a TV copy in flight a few bytes further on; at passes 300 and 450 a page flipped a VBLANK
  earlier) and the picture sequences of `solve1_m2`, `_tr`, `_fx` and `quirk2_tr` differed (the TV duty rule's
  choices). The out-of-line design makes "visit 1 byte-identical in VRAM" hold by construction, and leaves
  C6AAh to `lv_voffy` and the range's `rgr_nx`.
- Harness (add only): `stepcheck.py --visit 2` (still and rec: `Puzl(data, (1, 2))`, `render(state, cursor, 2)`;
  a snapshot's AG $8050 must be 2 or more), `check_all.sh` passes it for `solve2` and `fuzz2`.
- Tests: `test_msxpuzl.py` (`test_visit_2`: the blobs, the equates, the render's Ellen; the command line with
  `--visits 1,2` and `render --visit 2`), `test_bstest.py` (`test_stepcheck_visit_2`).

### Checks (exact commands, results)
- Converter: `python3 -I tools/msxpuzl.py build/extracted/files/PUZL_25.bin OUT/puzl` (no `--visits`): its 14
  outputs byte-identical to HEAD's; with `--visits 1,2`: `puzl_gfx.bin` = visit 1's, `puzl_tv2.bin` = the old
  one-blob output's last 28,800 B, `puzl.inc` = visit 1's but `PZ_GFX_TV2` 27904 -> 0, `PZ_VISITS` 1 -> 2,
  `PZ_CUR_COL_2` 15 -> 14; its checks pass (the renders against the Amiga's composition, 11 states a visit).
- Builds: `sh $S20/builds.sh WT OUT` (`hz.sh builds`, `hz.sh l2builds`, and `ROM_2M=1`, `PZ_TEST=2`, `PZ_TEST=2
  PZ_LEVEL=2`, `PZ_TEST=1 PZ_LEVEL=2` (+ `ROM_2M=1`), `EXTJOY=1 LV_TEST=2`, `TAG=7`, `DIAG=1`) from a worktree
  of 7c8635a into `A` and of this tree into `C`: 20 + 20 build OK, 12 known z80asm warnings each. The shared
  tree's product, rebuilt after the copy and `make msx`'s converter line: byte-identical to `C`'s (sha256
  2cd25893b28f0a32; HEAD's 4194792d6a7d1585).
- **Only Brainstorm's bank and the new blob differ**: `python3 -I tools/bstest/romdiff.py --blocks A/<b> C/<b>`
  on all 20: romdiff PASS, BANK_PUZL (111 bytes) and `PUZL_TV2_BANK` (new: 123-126; 116-119 in `DIAG=1`, which
  has no music banks); FIXED, every code bank and every data block identical, so level 1, the title, the range,
  level 2 and FRONT are HEAD's byte for byte. mkrom's checks (3Fh rule, SCC test values, "OPLL", guard) pass in
  all.
- Free bytes (`python3 -I tools/bstest/l2base.py banks C A`): only PUZL moves (4,590 -> 4,483); fixed area
  298 (product), lowest DIAG+PZ_TEST 163, DEMO_HUD 76, as before. `sh tools/bstest/variants.sh C/variants`: 46
  of 48 (`DEMO_ACTORS=2`/`5`: the fixed area 6Dh over, as at HEAD).
- Emulator: one openMSX (the in-process MCP; the step-14 agent used its private session). `sh
  tools/bstest/regress.sh builds A2` (worktree of 7c8635a) and `... C2`; MCP `source {wt1/tools/bstest/load.tcl};
  rgr_chain {A2} all {A2/all.done}`, the same on C2: 208 jobs each, 0 time outs. A2 made a base:
  `check_all.sh A2/O m2 tr fx eu > A2/check_all.log` (7c8635a's scripts), `fresh/new_*`, `xnew_*` copied to
  `base_*`, `xbase_*`. **`sh tools/bstest/regress.sh check C2 A2`: regress: PASS, 20 steps, 45 verdicts, 0
  FAIL** (level 1's cov traces; the title from power-on, exact and polled; the product's and `PZ_TEST=1` flows;
  the restore; the turbo R's blank and writes; the titles after the flows; 2 MiB; the keyboard product; the
  final checks' flows; Brainstorm's 20 traces, stills and records; the guard and VRAM speed; the HUD; the
  range's screens, ratings, traces after level 1 and Brainstorm, wanted state, display and sound).
- **Brainstorm's 20 traces 0 differ** (`sh tools/bstest/check_all.sh C2/O m2 tr fx eu`), `solve2` 728 and
  `fuzz2` 606 frames with results 0 and 1 on C-BIOS_MSX2 and the FS-A1GT; `python3 -I tools/bstest/cmpcheck.py
  A2/check_all.log C2/check_all.log C2/O`: PASS (its one torn cell is the base's own: `solve2_m2` record 592,
  $B00 470, a set-up, palette black).
- **Visit 1 byte-identical**: `python3 -I $S20/snapcmp.py A2/O/st C2/O/st solve1_m2 solve1_tr solve1_fx
  solve1_eu fail_m2 fail_tr timeout_m2 timeout_tr quirk2_m2 quirk2_tr`: PASS, all 53 snapshots identical in VRAM,
  the VDP registers, the palette and RAM C000h-FFFFh; all 10 records (4,331 VBLANKs) identical in every part.
- **Visit 2's stills equal `msxpuzl.py render --visit 2`**: `python3 -I tools/bstest/stepcheck.py still --visit
  2 ...` on 66 snapshots, 0 with differences: the suite's (C-BIOS_MSX2, FS-A1GT: passes 100, 400, 700) and 60
  more (`hz7_job solve2_{fx,eu,m2x}` on the FS-A1FX, C-BIOS_MSX2_EU and C-BIOS_MSX2: every 8 passes of board 0,
  boards 1 and 3, the ending; their traces 0 differ); `stepcheck.py rec --visit 2 --ref
  build/emu/pz_solve2_ram.jsonl` on the FS-A1FX and 50 Hz records: 0 torn, 0 outside, 0 cursor errors, the
  face in 260 and 257 of 424 pictures. `$S20/palcheck.py`: board 0 shows `puzl_2_grade.pal`, boards 1-3 and
  the ending `puzl_1_grade.pal` (quirk 5), on every machine.
- Visit 2's flow from power-on (`PZ_TEST=1 PZ_LEVEL=2`, the optional `-test7-bs2` option set): MCP
  `hz_bonus_setup` on `C/X/bs2` on the Expert and the FS-A1GT, `python3 -I tools/bstest/bonuscheck.py DIR
  bs2_m2 --result time --gen C/X/bs2/gen --range time`: bonus check PASS on both (the intro and OUT OF TIME.
  equal to their renders, 4,075 HUD splits in 4,075 VBLANKs, the range's intro and result equal, the range
  PASS, the title, the new game, lost counters 0).
- Pictures looked at (`tools/bstest/shots.py`): Ellen under static in visit 2's palette (board 0, FS-A1GT),
  darker in visit 1's (board 2, quirk 5), clean at the ending (C-BIOS_MSX2), board 3 on the FS-A1FX; HEAD's
  Murphy at the same pass.
- `make test`: 298 tests, the 4 known failures only (failures=3, errors=1).

### Open issues
1. For the user's eye (the candidates' notes): Ellen's face pair 655/644 (provisional, the face looks pale)
   and quirk 5 (reproduced: boards 1-3 show her in visit 1's 433/322). Under quirk 5 the cursor keeps visit 2's
   indices (14/14), so on boards 1-3 it shows `pz_pal1`'s 433 where the Amiga shows visit 1's COLOR19 ($754, MSX
   322); if the user fixes quirk 5 the cursor is 655 throughout.
2. **`build/msx/puzl.inc` now holds visit 2's equates.** An older commit built with today's `build/msx` reads
   visit 2's pictures from `puzl_gfx.bin`'s start (and `PZ_CUR_COL_2` 14): for an exact older build regenerate
   in its worktree with its own converter, `python3 -I tools/msxpuzl.py build/extracted/files/PUZL_25.bin
   build/msx/puzl`. The step-14 base (`l2/base`, built 03:25 from `l2/wt0`) has its own earlier copy.
3. `check_all.sh` checks `solve2` and `fuzz2` as visit 2: records of a build before this commit (Murphy) fail
   those stills; check them with their own commit's `tools/bstest/`.
4. For step 24: `pz_tvb` (step 5's byte) is unused and `msx.inc`'s `pz_tv` comment ("in puzl_gfx.bin") is
   visit 1's only (`msx.inc` not edited here); `docs/BRAINSTORM.md`'s visit-2 statements are outdated (1's
   "Not yet", 3.1 step 3, 3.3, 3.9's `--visits 1,2`, 3.10's 92 banks and 85,504-byte blob, 5's step 13, 8's
   risks 8 and 9).
5. Visit 2's entry maps 8 data banks (`puzl_gfx.bin`'s first 4, `puzl_tv2.bin`'s 4), visit 1's 7.

## Level 2's base made again, from main 9be19aa (2026-10-31)

**Done.** macOS wiped the scratchpad on 2026-10-30: `$IMPL/base` (a969fc8) and the range's base are gone.
**The base is now `$L2/base`**, with `L2=/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/l2`:
main **9be19aa** (the range's two cameras: the V9958's rings, the V9938's 16-column steps), recorded
and checked by level2 7c8635a's harness. Keep it; other agents only read it. Every "as the base" check
from now on: `sh tools/bstest/l2base.sh check W $L2/base` (THE ONE CHECK at the top, with this path).

### How it was made (exact commands)
```sh
git worktree add --detach $L2/wt0 9be19aa
ln -s <repo>/build/extracted $L2/wt0/build/extracted; cp -Rc build/ram build/emu $L2/wt0/build/
(cd build/msx && find . -type f ! -name '*.rom' ! -name '*.ROM' ! -name '*.labels' ! -name '*.png' \
   ! -path './gen/*' ! -name '*.wav' -print | cpio -pdm $L2/wt0/build/msx)   # (copied 03:20, before step 20's puzl.inc)
git -C $L2/wt0 checkout 7c8635a -- tools/bstest tools/openmsx_rc2.tcl tools/tracecmp.py tools/msxframe.py \
   tools/recframes.py tools/objcmp.py tools/msxprof.py     # (the gate's harness; 9be19aa's sources and build tools)
cd $L2/wt0 && sh tools/bstest/l2base.sh builds $L2/base    # builds: PASS (25 ROMs)
# a private MSX-AI MCP session (this process's target may be another agent's): new tools/bstest/mcpd.py, mx.sh
python3 -I tools/bstest/mcpd.py $L2/sg/mcp &               # (background; MCPD_DIR=$L2/sg/mcp sh tools/bstest/mx.sh NAME 'TCL')
#   source {$L2/wt0/tools/bstest/load.tcl}; source {$L2/wt0/tools/bstest/l2base.tcl}; l2b_chain {$L2/base} {$L2/base/all.done}
sh tools/bstest/l2base.sh check $L2/base $L2/base          # one FAIL only: the title from power-on (no base_* yet)
sh tools/bstest/l2base.sh base $L2/base                     # "base: ready" (fresh/new_* -> base_*, xnew_* -> xbase_*)
sh tools/bstest/l2base.sh check $L2/base $L2/base          # l2base: PASS ($L2/base/l2base_check.log)
```

### Checks (results)
- The build data are 9be19aa's: `build.sh ... TAG=6` and `PZ_TEST=2 TAG=6` in `$L2/wt0` give test6's files
  byte for byte (SHA-256 6aea17e05c26dba0… and 8c8bf053d876a208…, `build/msx/ROBOCOP2_v0.1.3-test6*.ROM`);
  `TAG=4` against `ROBOCOP2_v0.1.3-test4.ROM` (a969fc8, the old base): only bank 88 (FRNG) differs, so level 1,
  the title, Brainstorm and the fixed area are the old base's byte for byte.
- The chain: 227 jobs, all done, no time out (`$L2/base/all.done`). `l2base.sh check $L2/base $L2/base`:
  **l2base: PASS** (regress 45 PASS; die/over/end 901/1,249/517 rows 0 differ; start m2/fx/tr all 0 (26,690 /
  26,445 / 31,505 entries); field 0 differ but `860_m2` 3 pictures / 177 px, the known hostage tear (A); stills
  10 pictures; LOCKSTEP 2,998 lists both VDPs; effects 800 starts, SCC 57,480 / PSG 33,395 sound ticks; code
  banks: fixed 188, FIELD 1,529, FRONT 2,309 ... as a969fc8's).
- **The base against itself, a rebuild**: `l2base.sh builds $L2/rebuild` (25 ROMs, 0 differ from the base's),
  the chain again, `l2base.sh check $L2/rebuild $L2/base`: **l2base: PASS**, every record identical
  (`$L2/rebuild/l2base_check.log`).
- **level2 7c8635a (level 1, Brainstorm, the range and the title as the base)**: worktree `$L2/wtH` (its own
  harness), `l2base.sh builds $L2/h13`, the chain with `$L2/wtH`'s Tcl, `cd $L2/wtH && sh
  tools/bstest/l2base.sh check $L2/h13 $L2/base`: **l2base: PASS** (`$L2/h13/l2base_check.log`): regress 45
  PASS, traces 0 differ, start checks all 0, field 0 differ in every window (860_m2's hostage tear did not come
  this time), stills identical, effects PASS (802/802 starts, 57,435 and 33,352/33,356 sound ticks 0 differ);
  LOCKSTEP fx 2,998 lists 0 differ, m2 906 lists 0 differ, then `dispcmp.py`'s rule stops at game frame 1812
  ("the displayed cameras differ (1567/654 vs 1551/654; scroll engine timing)": the V9938 engine's idle-time
  camera, which LOCKSTEP does not pin; reported, not a FAIL).
- **Negative controls** (new `tools/bstest/l2neg.sh`, on copies of the rebuild's records; `sh
  tools/bstest/l2neg.sh $L2/wt0 $L2/base $L2/rebuild $L2/neg/out`, `$L2/neg/neg.log`): **19 as expected, 0
  wrong**: 11 FAIL (die trace's camera_x in one row; start tear 0->1, cpu 0->1; a field record's page zeroed:
  1 picture, 34,712 px, "a new class: other"; a still's play pages zeroed; one LOCKSTEP SAT byte; an effect
  start 30 VBLANKs late; another effect at a start; the exact title's VRAM byte, the game's RAM D100h; the
  range's tarm_m2 row 40), 8 PASS (the same copies unmutated).

### Open issues
1. After step 20 (244ccb8) `check_all.sh` checks `solve2`/`fuzz2` as visit 2 (Ellen), while this base's
   `check_all.log` and records are visit 1's pictures (Murphy, 9be19aa): a later tree's run against this base
   shows those differences in Brainstorm's family (expected, step 20's change; see the step-14 section for how
   they were judged).
2. `$L2/base` holds 1.8 GB; `$L2/rebuild`'s and `$L2/h13`'s big record folders can go once read.

## Step 18: the flow into and out of level 2 (2026-10-31)

**Done; committed locally, not pushed (the user's order).** Branch `l2-s18` (worktree
`scratchpad/l2/wt18`, from level2 244ccb8). Records in `$S18` =
`/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/l2/s18`:
`B` (level2 head's records, below), `W` (this step's gate: `W/R`, `W/X`, `W/V`, `W/S`, `W/L`, `W/L2R` the
level-2 builds, `W/O`, `W/fresh`, `W/l1`), `T` (the first runs), `variants`, the logs.

### What was built
- **`msx/rc2.asm`**: `ml_ev` as the plan's 3.7 (step 19 adds the continue): after `front_stats` and
  `front_bonus`, AG `$8050` = 1 goes on into `lv_next` (moved right after it: `dsp_off`, `lv_go` with A =
  `$8050`), anything else to the title and a new game (`ml_ttl`: after level 2, default 5). `lv_test`
  jumps to `lv_next`. `lv_go` calls `hud_start` (FRONT) where it called `hud_init`.
- **`msx/front.asm`**: `front_brief` (AG `$8050` 1: `fe_text(txt_l2_brief)`, 2: `txt_l3_brief`, else
  nothing) at `front_bonus`' tail before `jp cpu_title`: silent, the HUD's messages ticking below, TEST n
  at row 10, fire from tick 50 (all `fe_text`'s). `PZ_TEST=1` thus shows the briefing after the range, then
  the title; `LV_TEST`'s `front_l2test` shows it too (default 9).
- **`msx/cold.asm`**: `hud_start` (AG `$8050` 0: `hud_init`, a new game; else `hud_lvl`) and **`hud_lvl`**:
  `hud_init`'s empty panel and state, then with the display off the game's own HUD work (`hud_keep`, 24
  calls, `g_tick` 0 meanwhile) draws AG's timer, ammo and score and the heads (slot k keeps head 0 while
  lives > k, else graphic 5, the lost life's last look: `hud_request`), then the message queue and ticker
  cleared. The first picture of level 2 shows 07:30, the score, the lives, weapon 0's 000 and icon, the
  full can (below).
- **`msx/level2.asm`**: `l2_init`'s fresh path calls `set_weapon(0)` (`$8844`, level_init's: step 7's open
  issue 2: a level 1 played with a weapon left it set). **Deviation (recorded)**: the plan put it in
  `lv_next`; here it costs no byte of the fixed area (4 B of `BANK_L2`), runs for `LV_TEST` too (AG
  already weapon 0 / ammo 0: `wpn_ammo[0]` = 0, the traces unchanged), and a death keeps
  `level_restart`'s own call.
- `msx/msx.inc`: `pz_first`'s comment (`LV_TEST` too; step 7's open issue 6). `build/msx/text.inc`
  regenerated with the Makefile's `msxtext.py` line (step 17's labels; its first 16,117 bytes unchanged,
  1,728 appended): **the integrated tree's build/msx needs the same** (any build of this commit does).
- Harness (docs/HARNESS.md 5.9, 5.17 b and f, 5.22 "At step 18", the file table): `hz.tcl` (`hb_step`'s
  briefing and level 2: `hb_brief_arm`, `hb_l2_go`, `hb_l2_snap`, `hb_l2_100`; `flow_l2_end`:
  `hz_l2_flow_setup`), `hz.sh` (`l2builds` adds `R/flow`; `compare --fields` lists `flow_l2_end`),
  `rgflow.tcl` (`rgx_l2`: the `ar_*` jobs into level 2; the keyboard flow to level 2), `np.tcl` (the title
  job through level 2 and the second visits: `np_t_l2`, `np_t_end`, the snapshots; `np_wp_done`'s line),
  `regress.sh` (the verdicts above), `bonuscheck.py` (`--brief`, `--level2`), `rgcheck.py` (`--level2`,
  `--new-game`), `tools/msxframe.py` (a product snapshot without sprite records renders instead of
  failing), `tests/test_bstest.py`, `tests/test_level2_rom.py` (the new job and wording).

### Checks (exact commands, results)
All from the worktree's root; `S18` as above; one openMSX (the in-process MCP).
- **Level2 head's records** (`B`): `sh tools/bstest/regress.sh builds $S18/B` at 244ccb8 (before any
  edit): every hash equal to step 20's C2 builds (prod 2cd25893b28f0a32, pzt ff490d845bf806c2, pz1
  16f7a1307ca63cd8, pz2 514e5fb00c302af9, trace c7d7a04389d6f130, ext 3631e1af717b6739, fr2 cf6dac2f807aee71,
  ... all 22); MCP `source {wt18/tools/bstest/load.tcl}; rgr_chain {$S18/B} all {$S18/B/all.done}`: 208 jobs,
  0 time outs; made a base (fresh `new_*` -> `base_*`, `xnew_*` -> `xbase_*`; `check_all.sh $S18/B/O m2 tr fx
  eu > $S18/B/check_all.log`: its one torn cell, solve2_m2's set-up, as at step 20).
- Builds: `sh tools/bstest/l2base.sh builds $S18/W` (PASS: prod cd7ee1199de2b82b, pzt 278958fc28a5540b,
  trace 7613737a7cca2c8d, ext 038237e7a47e3fe9), `sh tools/bstest/hz.sh l2builds $S18/W/L2R` (PASS, flow =
  the trace build's bytes), 12 known z80asm warnings each, nothing else in the logs. `sh
  tools/bstest/variants.sh $S18/variants`: 46 of 48 (DEMO_ACTORS 2/5: the fixed area -76h, -6Dh before: +9 B).
- **Free bytes** (`python3 -I tools/bstest/l2base.py banks $S18/variants`, against level2 head): fixed area
  product 298 -> **289**, PZ_TEST 270 -> 261, lowest DIAG+PZ_TEST 163 -> **154**, DEMO_HUD 76 -> 67; FRONT
  product 1,897 -> **1,622** (text.inc's three scripts 181 B, `front_brief`, `hud_start`/`hud_lvl` 94 B), lowest
  `l2_diag` 1,176; BANK_L2 1,445 -> 1,441; every other bank as before.
- **The gate**: MCP `source {load.tcl}; source {l2base.tcl}; hz_chain [concat [rgr_jobs W all] [l2b_jobs W]
  [hz_l2_jobs W/O/l2 W/L2R tr]] W/all.done` (248 jobs, 0 time outs). Then:
  - `sh tools/bstest/regress.sh check $S18/W $S18/B` (**against level2 head's records**): **regress: PASS,
    45 verdicts, 0 FAIL** (`$S18/regress_check_B.log`);
  - `sh tools/bstest/l2base.sh check $S18/W ../base` (**main 9be19aa's base**): **l2base: PASS** (regress 45
    PASS; level 1's die/over/end 901/1,249/517 rows 0 differ; the start check; the field check; the stills
    identical; LOCKSTEP 0 differ; the effects by their starts);
  - `sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv $S18/W/O/l2 $S18/W/L2R`: **level 2:
    PASS (21 traces)**, 0 differ in all 1,022 fields, lost 0; **`flow_l2_end` 259 rows, 0 differ**
    (`rc2_l2_arm` after level 1 by `drive_end`, Brainstorm `pz_fail`, the range `fr_good`); `cont` 109
    (step 19).
- **4.2 check 11, the briefings** (bonuscheck in regress.sh): the level-2 briefing equal to
  `msxtext.py`'s render in every flow (prod_m2/tr, pzt_m2/tr, p2m_ex, tx_ex/f1/tr, kb_ex/tr, solved_*,
  two_*; with TEST 4 in `solved_cand_ex`, `two_title_ex`), the level-3 briefing in tx_ex2/f12/tr2; R#0 16h
  R#1 62h; **394 and 412 ticks** without fire (the scripts' 393 and 411 calls and the call that reads the
  end: the original's 394 VBLs, docs/LEVEL2.md 2.1); a HUD split at every VBLANK (e.g. 267/267, 289/289).
- **4.2 check 13, the HUD at level 2's start**: `$PY -I tools/msxframe.py W/O/.../TAG_l2g0 build/msx/level2
  build/msx/hud OUT.png --sprites build/msx/sprites --level 2 --field` on the first picture of the 11 flows
  into level 2: **0 pixels differ** (play area and HUD) on the Expert, the HB-F1XDJ, the FS-A1GT, the 2 MiB
  product, wp_tr, kb_tr, two_title_ex; kb_ex 25 (the timer had ticked once before the picture: the HUD's
  one-cell-a-frame catch-up, below), two_m2 1,212 (all sprite pixels msxframe expects from the EXTJOY
  records at frame 0, where the SAT is not published yet: the screen shows none). The notes: timer 0730,
  score and lives as level 1 left them, `$805E` kept, weapon 0, ammo 0000, heads 0 0, icon 3, can 0100, no
  HUD job.
- **4.4's flows, on the Expert (MSX2), the HB-F1XDJ (MSX2+) and the FS-A1GT (turbo R)**: `tx_*`, the
  product's whole flow from the power-on: level 1 (`drive_end`), the statistics, Brainstorm and the range
  left to time out, the level-2 briefing, level 2 (the range's rating kept: POOR 24), its end at game frame
  100 as F5 ends it, the statistics, **Brainstorm's second visit** (`stepcheck.py still --visit 2` on passes
  100 and 400 of the three machines: 6 snapshots equal to the render), **the range's second visit**, the
  level-3 briefing, **the title** (exact record against the base's title after Brainstorm: picture, palette,
  registers that show identical, the music identical per tick) and **a new game** at its tick 300 (level
  1: `lv_logic` BANK_L1, SHARP, lost 0).
- Turbo R writes: `wp_tr` 0 writes from `front_bonus`' entry to level 2's game frame 100.
- `make test`: 298 tests, the 4 known failures only.
- Pictures looked at: the level-2 briefing (prod_m2), the level-3 briefing (tx_ex2), level 2's first picture
  (prod_m2, two_m2: the brewery's start, 07:30, the score), Brainstorm's second visit (tx_ex2 p0400, tx_f12
  p0100: visit 2's board 0), the range's second visit (tx_tr2 pass 1500: its visit-2 colours).

### Open issues
1. The timer's first second at a level start can be short (`sec_tick` adds the VBLANKs since the last
   main-loop frame, `wf_n`, which spans the set-up): level 1's start does the same; the original re-arms its
   CIA-B timer at each start (`setup_ciab_timer`). With the HUD's one cell a frame, a picture can show the
   timer half updated (07:20 between 07:30 and 07:29), as at every ten seconds in play. Not changed here.
2. The flows' text records count VBLANKs and splits from the record (fs_n 170) to the screen's end, not
   from its first tick.
3. For integration: `build/msx/text.inc` of every tree that builds this code must be regenerated (the
   Makefile's `msxtext.py` line) or the build fails on `txt_l2_brief`.

## Step 19: the continue (2026-10-31)

**Done; committed locally, not pushed (the user's order).** Branch `l2-s18` (on step 18's 038ddbf: the
history was rewritten to the author rgmgbr meanwhile). Records in `$S18/W19` (the gate) and `$S18/W19/T*`
(the first runs).

### What was built
- **`msx/front.asm`**: `front_over` clears `fo_cont` first, and after PIC9 sets the key byte as
  `high_score_entry` `$12082`'s start does (`st.b $8032`: AG `$8032` = FFh, not ported otherwise: default
  6), then calls **`front_cont`** and returns `fo_cont` as the flags (NZ: continue). `front_cont`
  (`$11FD2`): AG `$805E` - 1 as a word; below 0 its high byte cleared (`$11FEE`: 00FFh) and no offer
  (`jp cpu_title`); else `cpu_title` (a turbo R on the Z80, as after `front_stats`), `front_done`,
  `fb_prep`, `display_on` where `fb_prep` does not call it, `fe_text(txt_cont)` (silent, the HUD's split
  on), `fo_cont` = 1 when the screen ended by fire or fire is held at its end, `jp cpu_title`.
- **`msx/rc2.asm`** (fixed area): `ml_ev`'s game over goes to `ml_ov` (`front_over` through
  `front_call`, `jr z,ml_ttl`), falling into **`lv_cont`**: `lv_cfront` (FRONT), `level_restart`,
  `hud_lvl` (which now ends with `logic_map`), then `lr_on`, the death restart's own tail (`display_on`,
  `g_tick` 0, the main loop). `level_restart` no longer calls `display_on` itself: `ml_rst` does (the same
  order). A script build's `title` runs `front_done` when `front_mode` is set (after a game over: PIC9
  left it set and the new game hung waiting for lists; a test-build fault that only the continue's
  harness reached); at the power-on and after the stages it does nothing, as before. **The product's
  bytes for `title` are unchanged.**
- **`msx/cold.asm`**: `lv_cfront` (two lives, `lv_vram` = FFh, `lvs_vram`: `lv_select`'s copy and uploads,
  page 2 and the atlas again after PIC9: default 50; `tc_reset`: the tile cache alone, with `cpu_game`);
  `lv_select` and `tiles_init` split into those parts (the same work for every level start). The map
  patches, the attribute RAM, the level's lists and the vats' state are not touched: the map keeps its
  changes (level_init's entry 1 for level 2).
- Harness: `hz.tcl` (`hz_l2_cont_arm` and its procs: the 64 KiB at `front_over`'s entry and at `lv_cont`'s,
  the offer's record at `iv_late` from `fs_n` 50, SPACE from its tick 60, the first picture after the
  continue, the new game; `hz_l2_jobs`: `cont` whole again (301 rows), `cont_fx`, `cont_tr`, `over` then
  its new game; `hz_l2_cont_jobs`: `cont_nf`, `cont2` with `hz_l2_cont2_drive`; `hb_step`'s intro and result
  records at `iv_late` within `fs_n` windows, below), `hz.sh` (no `cont:109`; `cont_fx`, `cont_tr`),
  `rgflow.tcl` (the keyboard flow's notes stay its own), **`tools/bstest/contcheck.py`** (new),
  `tests/test_level2_rom.py` (22 jobs), `docs/HARNESS.md` (5.22 "At step 19", the file table).
- **A harness fault found and fixed**: `hb_step` recorded Brainstorm's intro and result by an `after time`
  poll: twice in one gate it took the previous screen's end for the intro (`fe_text` sets `fs_ptr` before
  it clears `fs_n`: `kb_tr` then removed its stage's breakpoints and lost the trace and the keys), and three
  times it read R#1 inside the split's blank lines (22h: `prod_m2`, `tx_ex`, `kb_ex`). Both records now
  come at the next `iv_late` with `fs_n` windows (intro 150-280, result 80-125, briefing 170-300).

### Checks (exact commands, results)
All from the worktree's root; one openMSX (the in-process MCP); `B` = level2 head's records (step 18).
- Builds: `sh tools/bstest/l2base.sh builds $S18/W19` (PASS: prod 01ab7ffa2794be0a, pzt 8f1f9288f11037dd, trace
  57b40762725a694a, ext bd14a3ed6e895e93), `sh tools/bstest/hz.sh l2builds $S18/W19/L2R` (PASS: l2 c7d59acca481f0b8,
  l2c d691c89e8b9a9c03, l2o 9d16b2789ddac7df, flow = trace), 12 known z80asm warnings, nothing else in the logs.
  `sh tools/bstest/variants.sh $S18/variants19`: 46 of 48 (DEMO_ACTORS 2/5: the fixed area -8Ch, -76h at step 18).
- **Free bytes** (`python3 -I tools/bstest/l2base.py banks $S18/variants19`): fixed area product 289 -> **267**,
  lowest DIAG+PZ_TEST 154 -> **132**, DEMO_HUD 67 -> 45 (step 19: 22 B: `lv_cont` 17, `ml_ov` 5 net; a script
  build's `title` 10 more in script builds only); FRONT product 1,622 -> **1,506**, lowest `l2_diag` 1,176 ->
  1,060; BANK_L2 1,441; every other bank as before.
- **The gate** (the final code): MCP `hz_chain [concat [hz_l2_jobs W19/O/l2 W19/L2R tr] [rgr_jobs W19 all]
  [l2b_jobs W19]] W19/all.done` (252 jobs, 0 time outs), then:
  - `sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv $S18/W19/O/l2 $S18/W19/L2R`: **level 2:
    PASS (23 traces)**, 0 differ in all 1,022 fields, lost 0: **`cont` 301 rows on C-BIOS_MSX2, the FS-A1FX and
    the FS-A1GT** (the game over at row 108, PIC9, the offer, fire, level 2 again from row 109 with two lives and
    `$805E` 0, `$8032`/`$8033` FFh as the bench's), **`over` 109 rows**, `flow_l2_end` 259, the others whole;
  - `python3 -I tools/bstest/contcheck.py $S18/W19/O/l2 TAG MODE --gen $S18/W19/L2R/l2c/gen`: **cont, cont_fx,
    cont_tr `--fire`: PASS** (the offer equal to `msxtext.py`'s render of `txt_cont`, R#0 16h R#1 62h, 12 VBLANKs
    and 12 HUD splits to its end, ended by fire at its tick 61-62, `lv_cont` with `$805E` 0000h and `fo_cont` 1;
    **the map patches, the attribute RAM, the level's lists, the vat state and the tile cache equal before PIC9
    and at `lv_cont`'s entry**); **cont_nf `--no-fire`: PASS** (305 ticks, the whole length: 304 calls; 304
    VBLANKs, 304 HUD splits; the new game with the credit used); **cont2 `--again`: PASS** (the continue, then at
    tick 229 a second game over without a credit: no offer, `$805E` 00FFh, the title's new game); **over
    `--none`: PASS** (no offer, `$805E` 00FFh as `$11FEE` leaves it, the new game 30 s after: PIC9's time);
  - `sh tools/bstest/regress.sh check $S18/W19 $S18/B`: **regress: PASS, 45 verdicts, 0 FAIL**;
  - `sh tools/bstest/l2base.sh check $S18/W19 ../base` (main 9be19aa): **l2base: PASS** (level 1's die 901, over
    1,249, end 517 rows 0 differ: level 1's game over unchanged; the start and field checks, the stills, LOCKSTEP,
    the effects).
- **The first picture after the continue** (`TAG_l2g0`, `$PY -I tools/msxframe.py ... --level 2 --field`): the HUD
  07:30, two heads, score and ammo, the can full (shown digits 0730, heads 0 0, icon 3, no job), the play area
  equal to the map; msxframe's sprite pixels at that frame 0 come from the records before the SAT is published
  (as level 2's frame 0 in two_m2: the screen shows none): a still at game frame 50 after the continue, MSX2 and
  turbo R (a scratch job, `$S18/W19/T3`): **0 pixels differ, every sprite pixel exact**.
- Found and fixed on the way: `hud_lvl` left `hud_last` (the values every digit cell was last right for) as it
  was, so after a continue whose values equalled it the digits stayed the panel's 09:58 (the first such run);
  `hud_lvl` now clears it (the next level's start redraws the same as before).
- `make test`: 298 tests, the 4 known failures only (`test_bstest`'s mocked sessions fire `iv_late` now).
- Pictures looked at: the offer on the FS-A1FX (the lost lives' heads, 07:30), the first picture after the
  continue on the turbo R (07:30, two heads, the brewery's start), the MSX2 one before the `hud_last` fix (09:58).

### Open issues
1. The fixed area is down to 132 B in the lowest set (DIAG+PZ_TEST) and 267 in the product; the plan's 3.2
   budget for steps 14-15 is 140-220 B: the DIAG builds' `dg_probe`/`dg_rec` (~45 B) may have to move to
   BANK_MUSIC (risk 3).
2. The high-score entry (`$12082`) stays unported (default 6); only its `st.b $8032` is kept, for the trace.
3. In one gate run the lost counters of `cont_fx`/`cont_tr` stopped at tick 30 (a chain artifact: run alone, and
   in the final gate, both reach tick 300 with 0); `hz_clean` does not remove probe breakpoints, which jobs
   remove themselves.
4. The title after a game over is seen only in the product (script builds skip it); no regress record covers it
   (the plan's 4.4 game-over row: checked here on EXTJOY builds through the new game).

## Step 15: the cut and the arrest's view (2026-10-31)

**Done; committed locally, not pushed (the user's order).** Branch `l2-s15` (worktree `scratchpad/l2/wt15`, from
level2 0b63ec2), commits **b8b7490** (the code and the harness), **c456d4c** (the view's 48 px), this section's;
cherry-picked onto level2 9fd16e9 (step 21's head) as **93f89f1, 5b2f260, 20a575b** and this note's commit
(below). Files: `msx/{cold.asm, sprites.asm, player.asm, level2obj.asm, msx.inc}`, `tools/msxframe.py`,
`tools/bstest/{cutview.py, cutview.tcl}` (new), `tests/test_bstest.py`, `docs/HARNESS.md` (5.22), this file. Records
in `S15` = `scratchpad/l2/s15`: `W/R` (the six l2 builds), `X/l2` (`EXTJOY=1 LV_TEST=2`, product caps), `B0`/`B1` (the
product before/after), `V` (the option sets), `G` (the gate), `IGB` (a clone of step 14's `s14/IG`, made a base there:
IG itself untouched), `st`/`stb` (vat stills, new/base), `se`, `se2`, `se2b`, `se2x` (the arrest scene's stills),
`cv`, `cvt` (view records), `fd` (field records), `vl/*` (guards), `copper.py`, `cutscan.py`, `crop.py` (scratch),
`crop_*.png` (the pictures looked at).

### What was built
- **The cut** (plan 3.6, default 30): `sprites.asm` `sprites_frame`, after `sat_build` and before `q_sat`: while
  `vat_cut_line` < CAh (level 2's vats only; CAh in every other level: one compare per rebuilt SAT) the 8000h window's
  bank goes on the stack and `front_call` runs **`cold.asm` `spr_cut`**, which puts the bank back at its end.
  `spr_cut`: the original's copper line (`$10356`: from that beam line the sprite DMA is off) through the view's y
  mapping (map y = the line - 1Eh + the game camera's y; screen line = that - `cam_y`; the 9th bit kept: above the
  play area every entry parked, below it nothing done); over SAT entries 0 to `RC_RUN` + RoboCop's shown entries - 1
  (RoboCop's run and the hit spark's two: on the Amiga the spark is drawn into his sprites; a BOB is never in that
  range while his version is shown): an entry whose top is on or below the line is parked (`sb_parky`), one the line
  crosses gets colour 0 (transparent, CC 0) in its colour rows from the line down in the set being prepared
  (`rs_colhi`) and its row is marked unknown in that set (`col_held` FFFFh), so that the set's next list writes it
  whole again. The enemies are not cut (BOBs on the Amiga). A life's first lists before its first tick (`vat_cut_line`
  0, `G_VARS` cleared) call it and it leaves at once (level 1 too: a FRONT call of about 150 T-states, until the first
  tick sets CAh).
- **The arrest's view** (plan 3.6, default 31): `level2obj.asm` `t2` eases **`v_addx`** (CE43h, `G_VARS`: 0 at every
  life) by 2 a tick up to `VU_ADD` = 48 while it runs (type 2 writes `ac_camdx` = 500h every tick); `player.asm`
  `pl_view` adds it to the view's x right after `pv_add` (`pva_a`, `pv_add`'s tail), before `pv_keep`, which still
  keeps RoboCop within `AX_MIN`..`AX_MAX`. Display only: the logic's camera is untouched.
- **Two deviations, recorded**: (1) the cut's work is in FRONT (`cold.asm`), not `BANK_FIELD` (plan 3.2/3.6): the
  routine takes 125 B (116 B in `BANK_FIELD`'s form) and `BANK_FIELD` has 143 B in the product but only 102 B in every EXTJOY build (`fb_visrec`):
  the trace and harness builds would not assemble; FRONT keeps 935 B or more in every set; the 8000h bank kept around it
  costs 6 more fixed bytes than a `field_call` would. (2) The hit spark is cut with RoboCop (his sprites on the
  Amiga). The view's 48 is the plan's: the suspect's play-field BOB lies at map x 241 (its pixels 242-285), so map x
  48-295 shows him whole on both VDPs (the plan's premise "map x 256-303, the Amiga shows his left 32 px" was off: the
  Amiga's 288 px at camera 0 show him whole, the MSX's 248 his first 6 columns). A first build took 56 from that
  premise; c456d4c set it back to 48.
- **Room** (`python3 -I tools/bstest/l2base.py banks S15/V`): the fixed area product 192 -> **169** (the cut's hook
  17, the view 6), the lowest set DIAG+PZ_TEST 57 -> **34** (no fallback needed), `l2_diag` 66 -> 43, EXTJOY builds
  105-124; FRONT 1,506 -> **1,381** (lowest `l2_diag` 1,060 -> 935); `BANK_L2` 41 -> **29**; `BANK_FIELD` unchanged
  (143, EXTJOY 102); every other bank as before. No new block: 127 of 128 banks, the 1 MiB image. Option sets: **45 of
  48** (DEMO_ACTORS 2/5 -EEh, DEMO_HUD -35h: the known overflows, 23 B further).
- **Harness**: `tools/msxframe.py --cut LINE`; `tools/bstest/cutview.py cut|view` and `cutview.tcl` `cv_view_jobs`
  (HARNESS.md 5.22, "At step 15");
  `test_cutview_takes_the_copper_rule_and_flags_a_view_that_jumps_or_hides_the_suspect`.

### Checks (exact commands, results; `S15` as above, `W` = wt15, one openMSX: the in-process MCP)
- **Builds**: `sh tools/bstest/build.sh S15/B1/rc2.rom` (the product), `sh tools/bstest/hz.sh l2builds S15/W/R`
  (PASS), `sh tools/bstest/build.sh S15/X/l2/rc2_l2.rom EXTJOY=1 LV_TEST=2`, `sh tools/bstest/l2base.sh builds S15/G`
  (PASS), `sh tools/bstest/hz.sh l2builds S15/G/L2R`: build OK, z80asm's 12 known warnings only, nothing else in the
  logs. `sh tools/bstest/variants.sh S15/V` + `python3 -I tools/bstest/l2base.py banks S15/V`: 45 of 48 (above).
- **Level 2's logic** (the gate's first 25 jobs): `sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv
  S15/G/O/l2 S15/G/L2R`: **level 2: PASS (23 traces)**, 0 differ in all 1,022 fields, lost 0 (`cont` 301 rows on the
  three machines, `over` 109, `flow_l2_end` 259, `tour`/`vat` on the three); `python3 -I tools/bstest/contcheck.py
  S15/G/O/l2 TAG MODE --gen S15/G/L2R/l2c/gen`: cont, cont_fx, cont_tr `--fire`, cont2 `--again`, cont_nf `--no-fire`,
  over `--none`: **PASS** all six.
- **4.2 check 9, the cut**: MCP `source {W/tools/bstest/load.tcl}; source {W/tools/bstest/cutview.tcl}; hz_chain
  [hz_l2_still_jobs {S15/st} {S15/W/R} {36 37 ... 62} l2_vat]` (a still at the first new list from each of those game
  frames: 9 lists of the sinking on the MSX2 and the MSX2+, 17 on the turbo R), then `$PY -I tools/bstest/cutview.py
  cut S15/st build/emu/l2_vat_ram.jsonl`: **cut: PASS**: 35 stills with the original's line below CAh (game frames
  39-55: the line from C9h down to 85h; RoboCop under it from frame 48), all exact (RoboCop's and the spark's pixels
  from the line down absent, every other pixel as msxframe's model, the play area exact), 7,329 of RoboCop's pixels
  left out in all (57 at frame 48, up to 822 at frame 55); the enemies on screen meanwhile (MSX2 BOBs 65 and 20, V9958
  BOB 166) whole. The 4 stills without a cut that are not exact are the base's classes: msxframe at the V9938's left
  edge (3 px, frames 58-61) and around the death's objects near the play area's bottom (53 px at frame 79: the base
  35-161 px at 67-71), and on the turbo R a tile upload caught half done by the snapshot (lines 0-11 of slot 95 new) —
  the same stills of the base build (`S15/stb`) show those classes, and none of the sinking frames differs there (the
  base shows him whole). The line's rule against the original: `$PY -I S15/copper.py build/emu/l2_vat.drive 120` (the
  bench's own `$10356` at each game frame's start): equal to `cutview.copper_line` on all 121 rows.
- **The cut forced through the enemies** (a control): `vat_cut_line` forced to 6Eh at every `sprites_frame` (a cut at
  screen line 80 through RoboCop and the two enemy sprites beside him in `end`; scratch `S15/ctl.tcl` `s15_ctl_jobs`,
  stills at frames 40-60 on the three machines), `$PY -I tools/msxframe.py STILL ... --field --cut 80`: RoboCop's
  423-506 pixels left out, the enemies (BOB 68 at y 57, BOB 20 at y 85: across and below the line) whole, 12 of 15
  stills exact; without `--cut` all 15 differ by 300-330 px (the check sees the cut). The 3 others (frame 40-41, 9 px
  on line 87) are the two enemies' overlap: the cut parked RoboCop's entries from line 87 down, so line 87 went from
  10 sprites (not checked: above 8) to 6 and msxframe now checks it, putting the enemies in front by object number
  while the VDP puts the lower SAT run (enemy 2, entries 21-23, before enemy 1's 29-31) in front: msxframe's known
  object-order limit (step 12).
- **4.2 check 10, the arrest's view**: MCP `hz_chain [concat [cv_view_jobs {S15/cvt} {S15/W/R/l2/rc2_l2.rom}
  {S15/W/R/l2/rc2_l2.labels} {tour 2654 2405 end 259 15}] [cv_view_jobs {S15/cv} {S15/X/l2/rc2_l2.rom}
  {S15/X/l2/rc2_l2.labels} {end 259 15}]]`, `$PY -I tools/bstest/cutview.py view S15/cvt` and `... view S15/cv`:
  **view: PASS** both: `v_addx` steps 0 and 2 only, at 48 from 24 ticks after the suspect's spawn (end tick 45, tour
  2435); the view at its target from tick 83 (end) / 2476 (tour), the suspect whole in every list from 76-77 (end) /
  2471-2472 (tour) to the arrest (164 / 2559), on the three machines; RoboCop within 48..160 on every tick but 25 of
  `tour`'s at the map's left edge (the view at 0, RoboCop at x 173 after the drive's teleport); the view's steps at
  most 3 px a tick, 11-12 (end) and 20-21 (tour) of them above 2, all where the view follows RoboCop at his range's
  edge (open issue 2). With the product's caps `tour` has no suspect (open issue 3), so it runs on the trace build.
- **Pictures looked at** (msxframe's renders, zoomed: `S15/crop_cut_m2.png`, `crop_cut_fx.png`, `crop_cut_tr.png`,
  `crop_after_m2.png`, `crop_arrest_m2.png`, `crop_arrest_v58.png`): RoboCop sinking into vat 0, cut at the original's
  line (6 lines below the liquid's top edge: the line is the vat's y + 21) down to his head, on the MSX2, the MSX2+
  and the turbo R; after the line is CAh again (frame 56) he stands whole in the vat while he dies (open issue 1); the
  roof at game frame 100 on the MSX2, base and new side by side: the base's view at 0 leaves the suspect beyond the
  right edge, the new shows him whole (his white blink); the MSX2+ and the turbo R with the suspect firing.
- **Frame to frame** (field records of every picture, the X build: MCP `hz_chain [concat [hz_l2_field_jobs {S15/fd}
  {S15/X/l2/rc2_l2.rom} {...labels} {W/build/emu/l2_end.drive} {15 220}] [hz_l2_field_jobs ... l2_vat.drive {30
  120}]]`, `$PY -I tools/bstest/fieldcheck.py S15/fd/W build/msx/level2 S15/fd/W.png --level 2`): **0 differences** in
  all six windows: the arrest scene from frame 15 (220 pictures a machine: the view easing and following RoboCop, the
  play field exact in every picture: no static pixel changes in scene coordinates) and the vat's window from frame 30
  (120 pictures a machine, the vats' columns at their looks, none older). With the sinking's stills exact (9 lists a
  machine on the Z80 machines, 17 on the turbo R), no picture checked shows a pixel of RoboCop below the line. The scene's stills every 5 frames
  from 95 to 160 (`S15/se2`, base `S15/se2b`, product caps `S15/se2x`): the same small differences on both builds at
  the same frames (explosion sprites with a dropped OR layer at the suspect, 1-37 px: msxframe's model), nothing else.
- **The tear guard on those windows** (MCP `hz_chain [vl_jobs DIR ROM LABELS SECS FROM MACHINES DRIVE]`: `vat` 6 s
  from frame 30 (MSX2+, turbo R) and 5 s from 33 (MSX2: the V9938 first catches up with the drive's teleport), `end` 9
  s from 15 (three machines), on this l2 build and on IG's (0b63ec2) `s14/IG/L2R/l2`; `S15/vl/*`): **no tear, CPU,
  VBLANK or palette event before the death's restart in either build**; the one extra line, `end` MSX2+ `reg R#46 = d0
  pc b8e9` (`field.asm` `fqs_go` starting a play-field BOB's copy), is in step 14's records of the same code
  (`s14/ivl/450`, `ivl/850`, `vl/s520`): not new. At and after the restart (the display off about 10,500 lines while
  the screen is redrawn) both builds show tears and register events at different phases (open issue 4).
- **The gate** (nothing else changes): `sh tools/bstest/l2base.sh builds S15/G`, `sh tools/bstest/hz.sh l2builds
  S15/G/L2R`; MCP `source {W/tools/bstest/load.tcl}; source {W/tools/bstest/l2base.tcl}; hz_chain [concat [hz_l2_jobs
  {S15/G/O/l2} {S15/G/L2R} tr] [rgr_jobs {S15/G} all] [l2b_jobs {S15/G}]] {S15/G/all.done}` (252 jobs, 0 time outs).
  The base: step 14's integrated records `s14/IG` (0b63ec2), cloned into `S15/IGB` (`cp -Rc`) and made a base there
  (`sh tools/bstest/l2base.sh base S15/IGB`: its own title records as `base_*`/`xbase_*`; IG untouched). `sh
  tools/bstest/l2base.sh check S15/G S15/IGB` (`S15/G/l2base_check_IG.log`, `regress_check_IG.log`): **regress: PASS,
  45 verdicts, 0 FAIL**; level 1's die/over/end 901/1,249/517 rows 0 differ; the start check m2/fx/tr all 0 (25,217 /
  24,861 / 31,505 patterns, 0 bad, no line above 8, SATs 0 bad, lost 0); the field check PASS (860_m2 the known
  hostage tear A, 3 pictures 177 px, 860_fx A/B 6 pictures 183 px: within `TEARS`' bound); **LOCKSTEP 2,998 lists 0
  differ on both VDPs**; the effects PASS (800 / 803 / 802 starts in their frames; SCC 57,473, PSG 33,395 / 33,401
  sound ticks 0 differ); **the stills 9 of 10 identical, `m2_g1490` 8 PNG pixels apart (msxframe 470 against IG's
  468): FAIL, judged CPU time**: the snapshot is the same instant and list as IG's (304.28722 s, seq 235: both a
  VBLANK after the main base's, step 14's shift), and the 2 screen pixels are one link of the conveyor's chain beside
  its gear one redraw step apart (the engines' idle-time cell redraws, moved by the hooks' few T-states in level 1:
  32 a rebuilt SAT, 49 a tick; `S15/crop_g1490.png`: IG, new, main base); level 1's traces and LOCKSTEP's lists
  0 differ, as step 14's evidence. Against the main base (`sh tools/bstest/l2base.sh check S15/G scratchpad/l2/base`,
  `S15/G/l2base_check_base.log`): regress: PASS (45 verdicts), every other verdict PASS, the same still `m2_g1490`
  FAILs (32 px; msxframe 470 against the main base's 462; IG's 468, 24 px: the VBLANK shift step 14 recorded, plus the
  2 pixels above).
- `make test`: 300 tests, the 4 known failures only (failures=3, errors=1); `test_bstest.py` 41 OK.
- **Integrated** (step 21 integrated first: level2 96e2172): the step's code commits applied onto 96e2172 without a
  conflict (`test_bstest.py` merged); from that tree (a detached worktree `S15/wti`, the build data copied: equal to
  the main tree's, 105 files) the product, the `EXTJOY=1 LV_TEST=2` build, the six l2 builds and the flow build
  (`S15/IR`) and every ROM of `l2base.sh builds S15/IG2` (32) are **byte-identical** to this branch's (step 21 changed
  only `CHEAT` builds), so every emulator check above holds for the integrated tree as it is; `sh
  tools/bstest/variants.sh S15/IV` + `l2base.py banks`: **50 of 53** (the 5 `CHEAT` sets build: fixed 150-169, LC3
  4,833; DEMO_ACTORS 2/5 and DEMO_HUD as before); `make test`: 318 tests, the 4 known failures only. Cherry-picked
  onto level2 9fd16e9 in the main tree (the HANDOFF.md conflict: both sections, step 15's before step 21's;
  HARNESS.md merged by git); the integrated tree rebuilt into `S15/IM` (`build.sh`, `hz.sh l2builds`, the X build):
  the product, the X build and the seven l2 builds byte-identical to this branch's; MCP `hz_chain [concat [hz_l2_jobs
  {S15/IM/O/l2} {S15/IM/L2R} tr] [hz_l2_still_jobs {S15/IM/st} {S15/IM/L2R} {36 ... 62} l2_vat] [cv_view_jobs
  {S15/IM/cv} ... {tour 2654 2405 end 259 15}]]`: **level 2: PASS (23 traces)**, contcheck's six PASS, **cut: PASS**
  (35 stills, 7,329 px), **view: PASS**; `sh tools/bstest/variants.sh S15/MV`: 50 of 53; `make test` (the main tree):
  318 tests, the 4 known failures only.

### Open issues
1. **After the death in a vat RoboCop shows whole inside it**: the original's line goes back to CAh once d = camera y
   + 98h - the vat's y reaches 4Dh (frame 56 of `vat`, the camera following him down: the bench's `$10356` is CAh from
   there), so from then to the restart he stands at the vat's bottom in front of the liquid, dying, as the original's
   copper rule gives. Faithful; for the user's eye (MSX2 crop `S15/crop_after_m2.png`).
2. **The view's steps above 2 px a tick**: its own easing is 2 px a tick, but where RoboCop's place reaches `AX_MIN`
   (the drives' teleports put him at x 173-200, left of the scene) the view follows his walk at his speed (3 px on
   some ticks), as `pv_keep` does everywhere in the game; check 10's "at most 2 px a tick" holds for the easing, not
   for that following (20-21 ticks in `tour`, 11-12 in `end`).
3. **`tour` with the product's `ENEMY_CAP` 1 never spawns the suspect**: after the drive's teleports an enemy keeps
   the one slot (decision 25, risk 11: e.g. a homing drone, never freed by clipping); in real play the slot must be
   free when Cain's entry comes. Pre-existing; the user's call if it shows in play.
4. The guard's view of a death's restart (the display off for about 10,500 lines while the screen is redrawn) counts
   tears, CPU writes, VBLANK and register events at different phases in both builds (`S15/vl/*`): it does not model
   the restart; no event before it in either build.
5. Room: `BANK_L2` 29 B, the fixed area's lowest set 34 B (DIAG+PZ_TEST).

## Step 21: the sound checks and the cheat (2026-10-31)

**Done; committed locally, not pushed (the user's order).** Branch `l2-s21` (worktree `scratchpad/l2/wt21`,
from level2 a7c465d), cherry-picked onto level2 0b63ec2 (step 14 integrated meanwhile). Records in `$S21` =
`/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/l2/s21`:
`R` (`hz.sh fxbuilds`, `R/cheat`), `fx` (the 26 sound logs and their `.check` verdicts), `neg` (the mutated
ROMs), `cheat` (the keyboard run, its snapshots and renders), `var0`/`var1` (a7c465d's and this step's option
sets), `W` (the gate), the logs. One openMSX: a private MSX-AI MCP session (`mcpd.py $S21/mcp`, `mx.sh`).

### What was built
- **`CHEAT=1`** (`tools/mkrom.py`; refused with `DIAG`, which plays no game): `msx/cold.asm` `ng_init` sets AG
  `$804F` to FFh at each new game (the title's cheat handler `$11F60` begins `st.b $804F`: REA on
  `level1_full.bin`), and `msx/frame.asm` `fe_keys`, called first by `frame_end`, maps F5 (keyboard row 7 bit 1)
  to key code 59h and F4 (bit 0) to 58h in `$8032` while held, the code + 80h once let go (the release the
  Amiga's keyboard interrupt leaves; another key's code is kept); `frame_end` already acts on 59h (`$16D0`
  set: the level's end) and 58h (energy 102h), the original's F10/F9. **Deviation (recorded): the mapping is
  at `frame_end`'s head in `BANK_LC3` and the `$804F` store in FRONT, not in `player.asm` `key_scan` and
  `rc2.asm` as the plan's row 21 says**: both are fixed code, and so the fixed area pays nothing (every
  set's `code_end` as its twin's; `LC3` −33 B, FRONT −5 B in CHEAT builds; operands of the code after them
  move). Since `frame_end` runs in script builds too, F5/F4 also work in an `EXTJOY` CHEAT build; nothing
  changes while the game is paused (no tick).
- **`tools/bstest/fxlog.tcl`** (new; `load.tcl` sources it; `sess_fxlog.tcl` stays as step 0 brought it:
  l2base's `fx_scc` job reads its log by its starts): every write to the PSG's R0-R13, to 9800h-98FFh with
  where it went (the cartridge's SCC, another slot's, none) and to the OPLL, with the engine's events
  (HARNESS.md 5.23); `msx/sound.asm` gained the label `sf_back` (no byte) for the VBLANK's sound work's end.
  `fxl_jobs` (26 jobs), `hz.sh fxbuilds R` (9 builds).
- **`tools/bstest/fxcheck.py`** (new; the 2026-10-22 scratch copy was lost): `check` replays a log on a model
  of `sndplay.asm` and `music.asm`'s in-game effects (their data read from the ROM) and compares every
  event's writes with the model's, the queue, the tick divider, the end state, the effects' starts and plays
  to the end, the bench's requests per frame and the text screens' silence; `visits` compares the stages'
  tunes of two runs tick for tick; `selftest` mutates a real log.
- **`tools/bstest/cheat.tcl`** (new): `ch_job DIR ROM LABELS`, a CHEAT=1 build by the keyboard from the
  power-on through both levels (HARNESS.md 5.23).
- `tools/bstest/variants.sh`: the candidates' five CHEAT sets (53 in all). Tests: `tests/test_fxcheck.py`
  (15: a synthetic ROM, logs made through the model, every mutation caught, both players' rules, the voice
  choice, the waveform skip, the divider, the queue, the bench's restart, the job tables), `test_level2_rom.py`
  `CheatTests` (the refusals, the `if CHEAT` blocks, a CHEAT build's code windows), `test_bstest.py` (53
  sets). `docs/HARNESS.md` 5.23, the file table, the labels list.

### Checks (exact commands, results)
All from the worktree's root; `S21` as above.
- **Builds**: `sh tools/bstest/hz.sh fxbuilds $S21/R`: PASS (l2 c7d59acca481f0b8 and l2c d691c89e8b9a9c03 =
  step 19's; l2x 32982a9c0bdab777, l2n 2529805774f7c3db, l2cn ca2ba682e101777d, pz1 8f1f9288f11037dd = step
  19's pzt, pz2 324adab4a16839a9, pz1n 696f566ac58674a9, pz2n bdbf4247434bce03); `sh tools/bstest/build.sh
  $S21/R/cheat/rc2.rom CHEAT=1`: dcaa839e9b2790da; 12 known z80asm warnings each, nothing else in the logs.
- **4.3 check 1, the effects by register**: `hz_chain [fxl_jobs {$S21/fx} {$S21/R}] {...}` (26 jobs, under a
  minute), then `sh $S21/fxall.sh $S21/fx $S21/R`, which runs for each drive (tour, vat, mine, end, t1left,
  trolley) and chip set k (scc: the cartridge's SCC, `l2`; ext: an SCC cartridge in slot B, `extb scc`,
  `l2x`; psg: the PSG alone, `l2n`; C-BIOS_MSX2) `python3 -I tools/bstest/fxcheck.py check $S21/fx/d_D_k.txt
  $S21/R/B/rc2.rom $S21/R/B/rc2.labels --bench build/emu/l2_D_ram.jsonl --expect k` and `tools/tracecmp.py
  --ram --fields analysis/amiga_ram_l2.tsv` on the run's trace: **18 of 18 fxcheck: PASS**, every trace 0
  differ in all 1,022 fields (2,654 / 701 / 161 / 259 / 341 / 641 rows). In all: 144,355 segments, 310,398
  writes (SCC 93,586 + 93,986, PSG 37,497 + 37,975 + 47,354) equal to the model write for write; every SCC
  write at the chip the run uses (`c` / `x`); every request taken by the next VBLANK in order, none dropped
  (tour: 1,829 queued, taken 1-2 VBLANKs after); a tick at exactly the divider's VBLANKs (tour 9,194 of
  11,033); the engine's 197 bytes equal at the end; every frame's requests equal the bench's (2,653 / 700 /
  160 / 258 / 340 / 640 frames run; the gun's opening once a life: frames 29, and 138 and 554 after `vat`'s
  two deaths). The priority rule: each player's own as before (refusals: tour 05h 8, 07h 2 on the SCC; the PSG
  player 79 of 593 0Ch), see open issue 1.
- **4.3 check 2, the new numbers** (started / played whole; the rest cut by a later start on the channel or
  voice): **12h** t1left 7/7 (scc, ext 7/6, psg 6/5); **1Ah** t1left 112/4 (scc, ext; psg 112/6), tour psg
  657/1; **28h** vat 3/2 (all three), tour psg 5/1; **21h** tour 2/1 (all three), end ext 1/1; **10h** (a vat's
  death) vat 2/1. **0Ch**: tour's longest ride 212 requests every 2nd frame (frames 643-1065), trolley's 79
  (483-639), t1left's 50: on the SCC (both slots) every request started (tour 593/593, 593 and 590 whole); on
  the PSG alone 514 of 593 (79 refused by `sndplay.asm`'s rule: open issue 1). **The gun's opening** at level
  2's start: G at game frame 29 in every drive (the bench's first effect 3), played whole in end, tour, vat
  (three starts) and trolley, cut by early effects in mine and t1left.
- **4.3 check 3, by ear** (for the user's notes): the effects in `build/music/preview/sfx_all_amiga.wav`,
  `sfx_all_scc.wav`, `sfx_all_psg.wav` (one layout, 42 effects, 33.92 s) at 0Ch 0:08.56 (0.08 s), 10h 0:11.40
  (0.98 s), 12h 0:13.42 (0.22 s), 1Ah 0:20.24 (0.52 s), 21h 0:25.62 (0.32 s), 28h 0:30.90 (0.68 s); alone:
  `build/music/preview/sfx/sfx_NN_amiga.wav` / `_psg.wav` with NN the decimal number (12, 16, 18, 26, 33, 40).
- **4.3 check 4, silence**: `fxcheck.py check` on `brief_scc`, `brief_psg` (LV_TEST's briefing),
  `cont_scc`, `cont_psg` (the continue offer), `pz1_*` (the level-2 briefing after the range) and `pz2_*` (the
  level-3 briefing after the range's second visit): **8 screens, 0 writes after their stop** each; the
  stop's own writes (mus_quiet, sq_mute, the VBLANK's sq_stop) as the model's; the model ends at the title's
  music (`mus_start`, `sq_title`) after `pz*`'s briefing.
- **4.3 check 5, the second visits**: `python3 -I tools/bstest/fxcheck.py visits $S21/fx/pz1_k.txt
  $S21/fx/pz2_k.txt` (PZ_TEST=1, PZ_LEVEL 1 / 2, the stages left alone from the power-on): **PASS on the SCC
  and on the PSG alone**: Brainstorm's PZM 3,001 ticks and the range's FRM 6,000 ticks, every chip register
  equal at every tick (the SCC's 00h-AFh, PSG R0-R13).
- **4.3 check 6, the title's music after the new flow**: regress.sh's flows in the gate below: the title after the product's whole flow (level 1, both
  stages, the level-2 briefing, level 2 ended at its frame 100 as F5 ends it, both stages' second visits, the
  level-3 briefing) on the Expert, the HB-F1XDJ and the FS-A1GT: **the picture identical, the music identical
  at every tick** (5,045 / 5,045 / 5,046 ticks; 150,864 / 150,864 / 130,435 PSG writes; SCC, PSG registers
  and PSG writes 0 differ: titlecmp2.py) against a7c465d's records; against main 9be19aa's base (the title after the old flow) the
  picture identical and every PSG write identical at every tick, the registers that differ only ones neither
  run can hear (`titlecmp2.py --unheard`: the SCC's at every tick, on the turbo R the PSG's too: leftovers of
  what played before the title, as at steps 18-19).
- **Self-test**: `python3 -I tools/bstest/fxcheck.py selftest $S21/fx/d_end_K.txt ...` on scc, ext and psg:
  **12 of 12, 12 of 12, 9 of 9 mutations caught** (a PSG write's value and register, a write missing, one
  more, two swapped, an SCC write's value, address and chip, a start, a tick and a request lost, the end
  state). Real ROMs run in openMSX (`$S21/neg`): the first record of effect 0Ah's SCC stream with its volume
  0 → 1: **FAIL, 5 differences** (every start of 0Ah), PASS against its own ROM (the model reads the data);
  `sound.asm` `spv_on`'s `ld a,0Fh` → 0Eh: **FAIL, 580**.
- **4.3 check 7, the cheat**: `hz_chain [list [ch_job {$S21/cheat} {$S21/R/cheat/rc2.rom}
  {$S21/R/cheat/rc2.labels}]]` (466 emulated s; `$S21/cheat/cheat.txt`): `$804F` FFh from the new game; level
  1 at frame 100, **F5: `$8032` 59h and `$16D0` FFh at the next tick**, the score counted, front_stats at frame
  132 (`$8032` D9h once let go); Brainstorm and the range left alone, the level-2 briefing; level 2 at frame
  100, the energy poked to 40h, **F4: 102h at the next tick** (`$8032` 58h, then D8h); **F5 ends level 2**,
  front_stats, both second visits, the level-3 briefing, the title (SCREEN 8, `front_mode` 1). **Pictures
  looked at** (`$PY -I tools/msxframe.py $S21/cheat/S build/msx/levelN build/msx/hud S.png --sprites
  build/msx/sprites --level N`, a contact sheet `$S21/cheat/sheet.png`): level 1 before F5 (score 0) and after
  it (the score counting, 2100), level 1's statistics, level 2 at frame 100 (07:26), the can drained (40h),
  full after F4, level 2's end (the score counting), its statistics, the title after it.
- **Option sets**: `sh tools/bstest/variants.sh $S21/var1`: **51 of 53** (DEMO_ACTORS 2/5 overflow as before,
  the fixed area −8Ch); **the 46 sets that built at a7c465d byte-identical to a7c465d's** (`$S21/var0`, built
  from this worktree before any edit; `cmp`), `python3 -I tools/bstest/romdiff.py --blocks` on the product,
  l2_test, lock, trace, p_pz: **romdiff: PASS** (39 blocks identical). Free bytes (`python3 -I
  tools/bstest/l2base.py banks $S21/var1`): the CHEAT sets' fixed area as their twins' (cheat, cheat_t7,
  cheat_2m 267; cheat_l2, cheat_l2p 248), LC3 4,866 → 4,833, FRONT −5 (cheat 1,501, cheat_l2 1,419); the
  lowest set (DIAG+PZ_TEST) 132 as at a7c465d.
- `make test`: 316 tests, the 4 known failures only.
- **The gate**: all from the worktree (a7c465d + this step: its ROMs are a7c465d's).
  - Builds: `sh tools/bstest/l2base.sh builds $S21/W` and `sh tools/bstest/hz.sh l2builds $S21/W/L2R`:
    PASS; **all 32 ROMs byte-identical to a7c465d's** (`s18/I`, cmp), 12 known warnings each.
  - The chain (the private MCP): `hz_chain [concat [hz_l2_jobs W/O/l2 W/L2R tr] [rgr_jobs W all] [l2b_jobs
    W]] W/all.done`: 252 jobs, 0 time outs.
  - `sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv $S21/W/O/l2 $S21/W/L2R`: **level 2:
    PASS (23 traces)**, lost 0; `contcheck.py` cont, cont_fx, cont_tr `--fire`, cont2 `--again`, cont_nf
    `--no-fire`, over `--none`: **PASS**.
  - `sh tools/bstest/regress.sh check $S21/W $S18/I`: one FAIL, the exact title from power-on's game RAM
    (pointers DD08h, DD0Ah, DD0Ch 14 bytes apart, the `sw_*` bytes): **`s18/I/fresh/xbase_*` are main
    9be19aa's** (its check against `../base` copied them there: `regress.sh check` copies the base's
    `xbase_*` into W's `fresh/`), while its labels are a7c465d's, so the relocated pointers cannot be
    followed; this step's record equals `s18/I`'s own `xnew_*` byte for byte. So **the base view `$S21/IB`**:
    `s18/I`'s folders linked, `fresh/` with `s18/I`'s own records as `base_*` and `xbase_*` (what
    `l2base.sh base` does; nothing written into s18). Against it: `sh tools/bstest/regress.sh check $S21/W
    $S21/IB`: **regress: PASS** (45 verdicts; the exact title identical in every part, RAM 4,094 bytes at
    their place, $B32 apart); `sh tools/bstest/l2base.sh check $S21/W $S21/IB`: **l2base: PASS** (level
    1's die, over, end 901 / 1,249 / 517 rows 0 differ; the start checks 0 on the MSX2, MSX2+, turbo R; the
    stills; LOCKSTEP 2,998 lists 0 differ; the effects identical: sess_fxlog's 800 starts, 803 / 802 starts
    each in the base's frame with 0 moves, SCC 57,480 and PSG 33,396 sound ticks 0 differ).
  - `sh tools/bstest/l2base.sh check $S21/W ../base` (main 9be19aa's base): **l2base: PASS** (45 verdicts).

### Open issues
1. **The priority rule's scope differs between the two players (pre-existing, level 1 too; not fixed: no
   default covers it and it changes level 1's accepted SCC sound).** The original's request entry `$18014`
   jumps to `$1822C` for every effect: while channel 3's flags (`$18126` = the channel records `$18024` +
   56h × 3) are set, an effect lower than the last one started (`$18023`) is not played, whatever its
   channel (REA on `level2_full.bin`: `tst.w $18126; beq; cmp.b $18023,D0; bcs rts`; xrefs: only `$18014`).
   `sndplay.asm` `sq_sfx` (the PSG alone) does that; `music.asm` `fxs_one` (with an SCC) applies it only to
   channel-3 requests (`cp 3; jr nz,fxs_ok`), against its own comment and docs/MSX_ARCHITECTURE.md. Evidence
   (fxcheck's "scope" line): requests on channels 0-2 played on the SCC that the original refuses: tour 105
   (cartridge) / 109 (slot B), end 15 / 14, trolley 13, t1left 9, vat 5; the PSG player refuses the same
   kind (tour 79 0Ch). The fix is 5 bytes less in BANK_MUSIC (the channel test dropped), the user's call: it
   changes which effects play on the SCC in level 1 and level 2 (l2base's effect verdicts would then differ
   from the base by design).
2. Not modelled by `fxcheck.py`: the title's music, the speech, the stages' tunes (their own checks:
   `titlecmp2.py`, `frregcmp.py`, and `visits` here). A log's check ends at the title's music.
3. `fxlog.tcl`'s drive jobs run `LV_TEST` builds; the product's way into level 2 (`flow_l2_end`) is not
   logged by it (its traces equal the bench: the same requests).

### Integrated (level2 0b63ec2, step 14's integration, + step 21: b6ad4d5, 96e2172)
- Cherry-picked without a conflict (git merged HARNESS.md and HANDOFF.md). From the main tree: `sh
  tools/bstest/l2base.sh builds $S21/X`, `sh tools/bstest/hz.sh l2builds $S21/X/L2R`: PASS, **all 32 ROMs
  byte-identical to step 14's integrated builds** (`scratchpad/l2/s14/IG`), 12 known warnings each; `hz.sh
  fxbuilds $S21/XR`: PASS; `CHEAT=1`: e0d28bf115ad94a9.
- Option sets: `sh tools/bstest/variants.sh $S21/var2`: **50 of 53** (DEMO_ACTORS 2/5 -D7h and DEMO_HUD -1Eh,
  as step 14's integration; the five CHEAT sets build). Free bytes (`python3 -I tools/bstest/l2base.py banks
  $S21/var2`): the fixed area 192 B in the product, 173 with LV_TEST, 57 in the lowest set (DIAG+PZ_TEST), each
  CHEAT set as its twin; LC3 4,833 and FRONT -5 B in the CHEAT sets.
- The chain (the private MCP, the main tree's Tcl): `hz_chain [concat [hz_l2_jobs X/O/l2 X/L2R tr] [rgr_jobs X
  all] [l2b_jobs X] [fxl_jobs xfx XR {d_tour_scc d_vat_ext d_t1left_psg cont_scc brief_psg}]] X/all.done`: 257
  jobs, 0 time outs. `hz.sh compare --fields analysis/amiga_ram_l2.tsv $S21/X/O/l2 $S21/X/L2R`: **level 2: PASS
  (23 traces)**; `contcheck.py`'s six: **PASS**; `fxcheck.py check` (with `--bench`) on tour (the cartridge's
  SCC), vat (an SCC in slot B), t1left (the PSG alone): **PASS**, their traces 0 differ; cont_scc and brief_psg:
  **PASS**, the offer and the briefing silent after their stop.
- `sh tools/bstest/l2base.sh check $S21/X scratchpad/l2/base` (main 9be19aa): regress **45 verdicts PASS**,
  everything else PASS but **the known still `m2_g1490`** (24 px, msxframe 468 against 462): step 14's open
  issue, its integration's same verdict (these ROMs are its own byte for byte).
- `make test` (the main tree): 317 tests, the 4 known failures only.
