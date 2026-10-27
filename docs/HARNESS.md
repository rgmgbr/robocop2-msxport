# The acceptance harness (`tools/bstest/`)

The scripts that accepted Brainstorm, the bonus stage after level 1, on the night of 2026-10-27
(`docs/BRAINSTORM.md` section 4). They were written in a session's scratch folder, which macOS
clears, and live here so that the next milestones (the stage's sound, the second visit) run the
same checks. Every check below ran that night; section 9 lists what was verified again when the
scripts moved, without an emulator.

The harness has two sides:

- **The emulator side** is Tcl, sourced into the MSX-AI MCP's openMSX with `msx_local_cmd`. It
  builds on `tools/openmsx_rc2.tcl`: `rc2_drive_rom`, `rc2_pz_drive`, `rc2_pz_arm`, `rc2_guard`,
  `rc2_snaps` and `rc2_count_too_fast`.
- **The shell side** builds ROMs and compares the records with tools that need only `python3`.

## 1. Ground rules

- **The MSX side runs only in the MSX-AI MCP's openMSX** (`msx_local_boot`, headless;
  `msx_local_cmd`). Run at most two openMSX at a time (`pgrep -x openmsx`). One of them may
  belong to another agent: leave it alone.
- **Never `vwait`, `exit` or block inside `msx_local_cmd`.** Start a chain, which returns at
  once, then poll with short calls. The harness's Tcl uses no `exit`, `vwait`, `max` or `min`.
  It closes every file it opens on every path, including when a job times out (`hz_clean`).
- **Work folder.** The examples write to `W`, any folder outside `build/msx`.
  - The user picks ROMs from `build/msx`. `build.sh` refuses it.
  - The repository is in iCloud Drive, and one suite run writes about 200 MB of records. A
    session scratch folder or `$TMPDIR` is the better place.
  - Copy a test candidate to `build/msx` only when it is the exact file sent to the user.
- **Paths.** In Tcl, put braces around every path: the repository's path holds spaces. Pass
  absolute paths to Tcl, because openMSX's working directory is another. `hz.sh` prints its
  lines with absolute paths.
- **Build options.** In zsh, pass them as separate words, not through one `$opts` variable.
- **Python.** The harness's tools run with `python3 -I` (stdlib only). The Amiga bench
  (`tools/amigaemu.py`: Unicorn) and `tools/checkrun.py` (numpy) need
  `PY=~/.venvs/msxports/bin/python`.
- **Locations.** Every script finds the repository from its own place (`tools/bstest/`). Tcl
  sets `::hz_root` when `hz.tcl` is sourced.

## 2. The files

| File | Side | What it does |
|---|---|---|
| `build.sh OUT.rom [NAME=VALUE ...]` | shell | `tools/mkrom.py` into `OUT.rom`, then checks: mkrom's exit status, no "error" in `OUT.log`, a ROM written by this build, and no z80asm message in `OUT.labels` other than the 12 known "expression fully enclosed in parenthesis" warnings. `LEVEL=` another conversion; `SRC=` another source tree (5.3); `KNOWN_WARNINGS=` another count. Refuses `build/msx` and any OUT not ending in `.rom`/`.ROM` |
| `hz.sh` | shell | `trace DIR` (the regression's build), `compare DIR [LABELS]` (the regression's verdict), `product DIR` (a product build), `fresh DIR A B` (two title records), `builds R` (the suite's six builds) |
| `load.tcl` | Tcl | sources the Tcl files below in order (`hz.tcl` first) |
| `hz.tcl` | Tcl | `hz_chain` (the job runner), `hz_regress`, `hz_fresh`, `hz_bonus` |
| `hz6.tcl` | Tcl | `hz6_arm` (the stage after a played level 1), `hz6_prod` (the product's whole flow), `hz6_time` (the real timer) |
| `hz7.tcl` | Tcl | `hz7_snap`, `hz7_arm` (snapshots at passes, a record at every VBLANK), `hz7_job`, `hz7_guard_arm`, `hz7_after_setup` / `hz7_fresh_setup` (the restore) |
| `fixchk.tcl` | Tcl | `hzp_setup` (the turbo R's PAUSE), `hzb_setup` (the turbo R's HUD blank), `hzg_job` (the display guard), `hzf_job` (VRAM access speed) |
| `suite.tcl` | Tcl | `suite_drives R O` (25 jobs), `suite_flows R O FDIR FTAG` (13 jobs): the acceptance suite |
| `c8.tcl`, `run8.tcl` | Tcl | `c8_job` (a PZ_TEST ROM from power-on, cursor keys from the keyboard), `c8_chain` (the test candidates) |
| `check_all.sh OUT TAG...` | shell | for every drive job: `tools/puzlcmp.py`, `stepcheck.py still`, `stepcheck.py rec` |
| `stepcheck.py still` / `rec` | python | the stage's pictures against `tools/msxpuzl.py`'s render (5.5) |
| `bonuscheck.py DIR TAG` | python | the bonus text screens against `tools/msxtext.py`'s render, the HUD split at every VBLANK, the title, the new game (5.9) |
| `restorecheck.py DIR AFTER FRESH [--known]` | python | what the stage leaves: page 2, the atlas, the SATs; the next game against a fresh start (5.10) |
| `hudcheck.py NEW_DIR REF_DIR` | python | the HUD during the stage against a reference build's at the same passes (5.6) |
| `shots.py OUT SNAP...` | python | whole-screen PNGs of snapshots (play area, blank lines, HUD; 2x) |
| `fixblank.py FILE` | python | the HUD's blank at the turbo R's CPU switch (5.12) |
| `frozen.py SNAP OUT.png` | python | what the VDP shows while the CPU is held (5.12) |
| `romdiff.py A B` | python | the 8 KiB banks that differ |
| `relocheck.py OLD NEW OLD.labels NEW.labels BANK...` | python | a code bank's differences are only relocated label words (5.15) |
| `variants.sh OUT` | shell | the night review's 41 option sets, built (5.15) |

The Tcl reads these labels from a ROM's label file:

- the stage: `pz_tick`, `pz_frame`, `pz_done`, `pz_boards`, `ext_joy`, `iv_late`;
- the bonus texts and the interrupts: `txt_bs_*`, `isr_split`, `isr_vblank`, `INPUT_SCRIPT`;
- the title's music: `BANK_MUSIC`, `mus_adv`;
- the game tick: `tick_start`, `game_tick`;
- the CPU switch: `cs_go`, `display_on`, `front_bonus`.

It also uses RAM addresses of `msx/msx.inc` directly:

| Address | Name | Address | Name |
|---|---|---|---|
| EC44h | `front_mode` | CFB8h | `fs_ptr` |
| C202h | `mus_on` | CFBEh | `fs_n` |
| C2B2h | `mus_end` | C2A7h | `cpu_cur` |
| C205h | `mus_tick` | C002h | `split_armed` |
| CEE0h | `tick_n` | C07Ch | `act_8000` |
| C003h | `vbl_ptr` | CE5Ah | `ext_joy` |
| EA40h | `pf_pal` | EA22h | `SR_PAL` |
| EE20h | `rd_st0` | EE90h | `rd_st1` |
| 1084h | `mp_lost` | 1082h | `atr_lost` |
| 1088h | `rd_lost` | 069Ch | `fb_lost` |

The Amiga mirror is read at D000h (`$B00` + n) and DC00h (`$8000` + n). The BIOS's RG9SAV (FFE8h)
and CASPRV (FCB1h) are read too. If `msx.inc` moves one of these, update the scripts.

## 3. Reference files

None of these is committed (`build/` is git-ignored; data from the game is never committed).

| Reference | Used by | How it is made |
|---|---|---|
| `build/msx/*` (conversions: `level1.*`, `hud*`, `text_bs_*.sc5`, `puzl*`) | every build; `bonuscheck.py` (`text_bs_*.sc5`); `restorecheck.py` (`level1.vram`) | `make msx` |
| `build/ram/level1_full.bin`, `build/extracted/files/PUZL_25.bin` | `bonuscheck.py`, `stepcheck.py`, `shots.py` (`stepcheck`'s renders) | `make ram`, `make extract` |
| `build/emu/drive_cov1.txt`, `drive_cov0.txt` and `trace_cov1_ram.jsonl` (4,401 rows), `trace_cov0_ram.jsonl` (20,541 rows) | the level-1 regression (5.2) | made in earlier sessions. The drives are `tools/drivejoy.py` files, their bench arguments in their `.args` files (`drivejoy.py --scenario level1` makes such drives from `tools/amigacov.py`'s coverage scenario). A trace is `$PY -I tools/amigaemu.py game --gframes N --drive build/emu/drive_covK.txt --trace build/emu/trace_covK_ram.jsonl --trace-ram` (N + 1 rows); `--gframes 600` reproduced the first 601 rows of `trace_cov1_ram.jsonl` byte for byte when the harness moved. Keep them: the regression compares against them as they are |
| `build/emu/drive_end.txt` | `hz_bonus ... end`, `hz6_arm`, `hz6_prod`, `hzb_setup` | four lines: no joystick, the teleport `100:0x900:0x2d0`, no god mode, the poke `150:5826:80:2` (`tools/drivejoy.py`'s format). Level 1 ends by game frame 517 |
| `build/emu/pz_<name>.drive` and `pz_<name>_ram.jsonl` for `solve1`, `solve2`, `fail`, `timeout`, `fuzz1`, `fuzz2`, `quirk2`, `quirk1` | the drives (5.4), stills and records (5.5) | `docs/BRAINSTORM.md` 4.5 (`tools/puzlsolve.py`, `tools/drivejoy.py`, then `$PY -I tools/amigaemu.py puzl --pframes 2000 --drive build/emu/pz_<name>.drive --trace build/emu/pz_<name>_ram.jsonl --trace-ram`; `--pframes 3000` for the fuzz drives, `--level 2 --ram build/ram/level2_full.bin` for visit 2) |
| `build/emu/pz_opp.drive`, `pz_opp_ram.jsonl` | the `opp` drive | written by hand in `tools/drivejoy.py`'s four-line format: lines 1-2 empty (no joystick, no teleport), line 3 `0` (no god mode), line 4 the 19 pokes `40:32814:2:1 44:32814:12:1 48:32814:3:1 52:32814:15:1 56:32814:140:1 60:32814:2:1 64:32814:12:1 68:32814:8:1 72:32814:12:1 76:32814:8:1 80:32814:3:1 84:32814:12:1 88:32814:3:1 92:32814:15:1 96:32814:5:1 100:32814:10:1 104:32814:6:1 108:32814:9:1 160:32844:255:1`; then `$PY -I tools/amigaemu.py puzl --pframes 2000 --drive build/emu/pz_opp.drive --trace build/emu/pz_opp_ram.jsonl --trace-ram` (203 passes, result 1) |
| `build/emu/pz_kbd.drive`, `pz_kbd_ram.jsonl` | the candidates' keyboard moves (5.14) | `python3 -I tools/drivejoy.py --joy 100:5:d,110:5:r,120:5:d,130:5:l,140:5:d build/emu/pz_kbd.drive`, then `$PY -I tools/amigaemu.py puzl --pframes 1000 --drive build/emu/pz_kbd.drive --trace build/emu/pz_kbd_ram.jsonl --trace-ram` (1,001 rows, still playing; both equal the night's `cand/bench/kbd*` byte for byte) |
| **The title reference**: `FDIR/BASE_*` | the title check (5.3) | `hz_fresh` on the product ROM of the commit before the change (5.3) |
| A reference build's snapshots | the HUD check (5.6) | the same `hz7_job` on the commit before the change |

The night's own records (`impl/step0/fresh`, `impl/cand/suite_out`, ...) were in the scratch
folder and are gone or going. A new milestone makes its own references from its base commit.

## 4. A session in the MCP's openMSX

1. `pgrep -x openmsx | wc -l`: at most one already running.
2. `msx_local_boot` (headless, renderer none).
3. `msx_local_cmd`: `source {<repo>/tools/bstest/load.tcl}`. It answers "bstest loaded from ...;
   repository ...".
4. `msx_local_cmd`: one chain, for example `hz_chain [suite_drives {W/R} {W/O}]`. It answers
   "started N job(s)". Each job switches to a new machine (power-on RAM; `machine` inside an
   `after realtime`), sets `z80_freq` back to 3.58 MHz, throttle off and mute, then runs.
5. Poll with `msx_local_cmd`: `list $::hz_state $::hz_msgs` until the state reads `done`. Each
   finished job adds one message: "NAME (MACHINE): done in N s, emulated M s", or "TIMEOUT
   after ...". An error stops the chain: the state reads `error: NAME` and the message says
   why. A label missing from a ROM's label file shows there as "setup failed: no label X in
   ...". Check the first poll right after the start.
6. When done: `msx_local_shutdown`, unless another chain follows.

If the MCP's openMSX dies between calls (a broken pipe), the files already written survive: boot
again, source `load.tcl` again and restart the chain from the job that was running.

The machines are those of the MCP's openMSX home:

- C-BIOS_MSX2 (V9938, 60 Hz) and C-BIOS_MSX2_EU (50 Hz);
- Panasonic_FS-A1FX (MSX2+, V9958) and Panasonic_FS-A1GT (turbo R; the stage runs on its Z80);
- Gradiente_Expert20_64K (the user's Hotbit's twin) and Sony_HB-F1XDJ_128K_Lite (V9958).

Never download others.

## 5. The acceptance checks

`W` is the work folder, `R=W/R` the builds and `O=W/O` the outputs. Commands run from the
repository root. Each check lists the night's result: its expected result unless a change says
otherwise.

### 5.1 The builds

```sh
sh tools/bstest/hz.sh builds W/R
```

It builds the six that `suite.tcl` expects, each with `build.sh`'s checks, and ends "builds:
PASS":

| Folder | Options |
|---|---|
| `prod/rc2.rom` | none |
| `pzt/rc2.rom` | `PZ_TEST=1` |
| `pz1/rc2_pz1.rom` | `EXTJOY=1 PZ_TEST=1` |
| `pz2/rc2_pz2.rom` | `EXTJOY=1 PZ_TEST=1 PZ_LEVEL=2` |
| `trace/rc2_ext5.rom` | `EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1` |
| `ext/rc2_ext.rom` | `EXTJOY=1` |

Harness builds keep `TAG=0`. A single build:
`sh tools/bstest/build.sh W/x/rc2.rom NAME=VALUE ...`. It writes `rc2.labels`, `rc2.log`,
`code.bin` and `gen/` next to the ROM and ends "build OK: PATH (sha256 prefix)".

### 5.2 The level-1 regression

Level 1's logic must stay frame-exact against the Amiga bench.

```sh
sh tools/bstest/hz.sh trace W/trace          # builds W/trace/rc2_ext5.rom, prints the next line
```

```
msx_local_cmd: source {<repo>/tools/bstest/hz.tcl}; hz_regress {W/trace} {W/trace/rc2_ext5.rom} {W/trace/rc2_ext5.labels} tr
msx_local_cmd: list $::hz_state $::hz_msgs          (poll until done; about 10 s)
```

```sh
sh tools/bstest/hz.sh compare W/trace
```

- The jobs: `drive_cov1` (4,401 ticks) on C-BIOS_MSX2, `drive_cov0` (1,400) on the FS-A1FX
  and, with `tr`, on the FS-A1GT.
- The verdict: `tools/tracecmp.py --ram` with the traced ROM's own labels. A trace recorded in
  another folder than its ROM (the suite's `O/trace`) takes them as the second argument:
  `sh tools/bstest/hz.sh compare W/O/trace W/R/trace/rc2_ext5.labels`.
- Expected: "cov1: 4401 rows; 4401 game frames compared ..., 948 fields: 0 differ", the same
  with 1,400 for cov0 and cov0_tr, and "regression: PASS".

### 5.3 The title on a fresh machine, against the base

The title (its picture, registers, palette and music) and the start of the game must stay
byte-identical to the build before the change. The title is frozen: the user forbade changing it.

**The base reference**, made once per milestone from the commit before the change:

- Before touching `msx/` or `tools/mkrom.py`: `sh tools/bstest/hz.sh product W/base`.
- When the change is already in the tree, export the base commit instead (read-only on the
  repository, safe while other agents commit):

  ```sh
  mkdir -p W/base_src
  git archive BASE_COMMIT msx tools analysis | tar -x -C W/base_src
  ln -s "$PWD/build" W/base_src/build
  SRC=W/base_src sh tools/bstest/build.sh W/base/rc2.rom
  ```

  When the harness moved, this method rebuilt the night's six suite images and two of its
  candidates byte for byte.
- Then record it:

  ```
  msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_fresh {W/fresh} base {W/base/rc2.rom} {W/base/rc2.labels}
  ```

  Poll until done. The default machine is Gradiente_Expert20_64K and the game is recorded at
  tick 300.

Both builds use the same `build/msx` conversions, so a difference comes from the code.

**Each new build**:

```sh
sh tools/bstest/hz.sh product W/new
```

```
msx_local_cmd: hz_fresh {W/fresh} new {W/new/rc2.rom} {W/new/rc2.labels}     (poll until done)
```

```sh
sh tools/bstest/hz.sh fresh W/fresh base new
```

**The records**, in `W/fresh/TAG_*`:

- once the title shows, plus 1 s: `title_vram.bin`, `title_regs.bin` and `title_pal.bin`;
- `music.txt`: every music tick to the end of the title's music, with the SCC's and the PSG's
  registers;
- `psg.txt`: the count and hash of all PSG writes, the speech's PCM included;
- at game tick 300 (the title starts the game by itself): `game_vram.bin`, `game_ram.bin`
  (D000h-DFFFh) and `game.txt`.

**Expected**: every file "identical" ("music.txt: identical (5046 ticks)") and "fresh: PASS".
A `ROM_2M=1` build differs in `game_ram.bin` by 2 bytes at D032h. That is the random word `$B32`,
seeded from R each frame, and the 2 MiB guard's instructions shift R.

### 5.4 The drives: the stage's logic, pass by pass

Each drive runs an `EXTJOY=1 PZ_TEST=1` build. `rc2_pz_drive` resets the machine and feeds the
drive's joystick byte and pokes at every `pz_tick`. It records the mirror and the boards, and
`tools/puzlcmp.py` compares 399 values a pass, and the result, with the bench's trace.

| Drive | Build | Passes | Result |
|---|---|---:|---:|
| `solve1` | `pz1` | 732 | 0 |
| `fail` | `pz1` | 182 | 1 |
| `timeout` | `pz1` | 181 | 2 |
| `quirk2` | `pz1` | 282 | 2 |
| `fuzz1` | `pz1` | 619 | 1 |
| `quirk1` | `pz1` | 732 | 0 |
| `opp` | `pz1` | 203 | 1 |
| `solve2` | `pz2` | 728 | 0 |
| `fuzz2` | `pz2` | 606 | 1 |

`suite_drives` (5.5) runs all nine on C-BIOS_MSX2 and the FS-A1GT, and `solve1` also on the
FS-A1FX and C-BIOS_MSX2_EU. One drive alone:

```
msx_local_cmd: file mkdir {W/O/tr}; hz_chain [list [hz7_job solve1_m2 C-BIOS_MSX2 {W/R/pz1/rc2_pz1.rom} {W/R/pz1/rc2_pz1.labels} solve1 {W/O}]]
```

```sh
python3 -I tools/puzlcmp.py build/emu/pz_solve1_ram.jsonl W/O/tr/solve1_m2.txt
```

Expected: "732 PUZL frames compared (732 Amiga, 732 MSX), 399 fields: 0 differ" and "result:
Amiga 0, MSX 0".

**After a played level 1** (`rc2_pz_arm`: the stage reached through the level's end, the
statistics and the intro):

```
msx_local_cmd: hz6_arm {W/O/flow} arm_m2 {W/R/trace/rc2_ext5.rom} {W/R/trace/rc2_ext5.labels} C-BIOS_MSX2
```

```sh
python3 -I tools/puzlcmp.py --skip score build/emu/pz_fail_ram.jsonl W/O/flow/arm_m2_pz.txt
python3 -I tools/bstest/bonuscheck.py W/O/flow arm_m2 --result fail --gen W/R/trace/gen
```

Expected: 182 frames, 398 fields, 0 differ, result 1 (the score starts from level 1's), then
"bonus check: PASS". The night ran it on C-BIOS_MSX2 and the FS-A1GT.

### 5.5 Stills and records: the stage's display

```
msx_local_cmd: hz_chain [suite_drives {W/R} {W/O}]          (25 jobs; poll until done)
```

```sh
sh tools/bstest/check_all.sh W/O m2 tr fx eu
```

`suite_drives` runs:

- the nine drives with `hz7_job` on C-BIOS_MSX2 (`_m2`) and the FS-A1GT (`_tr`), and `solve1`
  on the FS-A1FX (`_fx`) and C-BIOS_MSX2_EU (`_eu`);
- snapshots (`W/O/st/NAME/pNNNN.bin`) at chosen passes: 12 in `solve1` (5 at 50 Hz), three each
  in `fail`, `timeout` and `solve2`;
- a record of up to 3,000 VBLANKs (`W/O/st/NAME/rec.bin`) in `solve1`, `fail`, `timeout`,
  `quirk2` and `solve2`;
- then the guard (5.7) and the speed jobs (5.8).

`check_all.sh` runs three checks on each job:

- `tools/puzlcmp.py` (5.4);
- `stepcheck.py still`: the page the applied list shows, with its SAT's sprites, equals
  `tools/msxpuzl.py`'s render of that page's shown state and of the cursor the SAT holds;
- `stepcheck.py rec` (its report in `W/O/st/NAME/rec.txt`): every element rectangle of every
  picture is one of its states (no torn block), and no pixel outside the elements differs from
  the screen (frame-to-frame coherence). The SAT is valid and holds the bench's cursor of the
  pass the list was published after, and none in the end sequences.

Expected: "check_all: PASS", with these numbers in the night's run:

- 20 traces with 0 differ;
- every still "equal to the render";
- `solve1`'s record: 922 records = 470 pictures (MSX2), 466 (turbo R), 463 (MSX2+), and 766
  records = 429 pictures at 50 Hz;
- 0 torn or unknown blocks, 0 pictures with pixels outside the elements, 0 cursor errors.

Pictures: `python3 -I tools/bstest/shots.py W/png W/O/st/solve1_m2/p0450.bin ...` gives the whole
screen 2x. `stepcheck.py rec REC --png DIR` writes the play area of the first 400 pictures.

### 5.6 The HUD during the stage

```sh
python3 -I tools/bstest/hudcheck.py W/O/st/solve1_m2 W/O_base/st/solve1_m2
```

- `W/O_base` holds the same drive's snapshots from the base build (5.3's base commit, its `pz1`
  build, the same `hz7_job`).
- The HUD's VRAM (1E800h-1FE7Fh) and its colours (`SR_PAL`) must be equal at every pass.
- Across the stage, only the score's box changes in an `EXTJOY=1` build, whose timer stands
  still: "[(200, 24, 231, 47)]".

The night compared step 7's build with step 6's, whose stage drew nothing.

### 5.7 The display guard

`hzg_job` (in `suite_drives`, `W/O/flow/guard_{m2,fx,tr}.txt`) runs `rc2_guard` over passes
10-633 of `solve1`, with tear counting on.

```sh
grep -E '^(reg|pal|cmd|cpu|vbl|tear) ' W/O/flow/guard_*.txt
```

Expected:

- reg 0, pal 0, cpu 0, vbl 0 on all three machines;
- cmd 166 / 158 / 165 (C-BIOS_MSX2 / FS-A1FX / FS-A1GT) and tear 28. Every one of them comes
  from `bs_board`'s copies into the page on screen at the three set-ups (passes 162, 326 and
  470), with the palette black: by design, invisible. Their log lines show `f=162`, `f=326` or
  `f=470` with a return address between `bs_board` and `rd_go` on the stack (A5EEh or A5F3h at
  `14bc5ef`; take the addresses from the build's label file). Any entry elsewhere is a glitch.

### 5.8 VRAM access speed

`hzf_job` (in `suite_drives`, `W/O/flow/fast_{m2,tr}.txt`) counts with `rc2_count_too_fast`.
It covers `solve1` with the entry's uploads and the exit's restore, on C-BIOS_MSX2 and the
FS-A1GT. Expected: "too fast VRAM accesses: 0 ...; result 0, passes 732".

**Check the counter before trusting a 0.**

- openMSX's callback settings name a proc. openMSX's own `share/scripts/callbackprocs.tcl` does
  `set VDP.too_fast_vram_access_callback warn_too_fast_vram_access`.
- The night's runs set an inline script there (`tools/openmsx_rc2.tcl` at `16507dd`). At this
  writing, a change to a proc (`rc2_too_fast_cb`) was pending in the working tree.
- So the night's zeros are not evidence until the counter has been seen to move once: on a
  build or a CPU speed known to write too fast.

### 5.9 The flows: the product and PZ_TEST

```
msx_local_cmd: hz_chain [suite_flows {W/R} {W/O} {W/fresh} suite]      (13 jobs; poll until done)
```

`suite_flows` runs, in this order:

- the regression (`W/O/trace`, 5.2);
- the title record into `W/fresh` as `suite` (5.3);
- `prod_m2` and `prod_tr` (`hz6_prod_setup`): the product from power-on, the title, fire, level 1
  ended by `drive_end`'s teleport and poke, the statistics, the intro, the stage left alone to
  its real time-out, OUT OF TIME., the title, fire and a new game;
- `pzt_m2` and `pzt_tr` (`hz_bonus_setup`): the `PZ_TEST=1` build from power-on;
- the restore jobs (5.10);
- the turbo R's blank (5.12).

The checks:

```sh
sh tools/bstest/hz.sh compare W/O/trace W/R/trace/rc2_ext5.labels
sh tools/bstest/hz.sh fresh W/fresh base suite
python3 -I tools/bstest/bonuscheck.py W/O/flow prod_m2 --result time --gen W/R/prod/gen
python3 -I tools/bstest/bonuscheck.py W/O/flow prod_tr --result time --gen W/R/prod/gen
python3 -I tools/bstest/bonuscheck.py W/O/flow pzt_m2 --result time --gen W/R/pzt/gen
python3 -I tools/bstest/bonuscheck.py W/O/flow pzt_tr --result time --gen W/R/pzt/gen
```

`bonuscheck.py` checks:

- the intro and the result screen equal `tools/msxtext.py`'s render, pixel for pixel. Add
  `--tag N` for a `TAG=N` build: "TEST N" at row 10;
- the TAG = 0 renders equal `build/msx/text_bs_*.sc5`;
- R#0 16h and R#1 62h at both records;
- a HUD split at every VBLANK between them (one more or fewer at most);
- the result named, and the new game.

It also writes `TAG_intro.png` and `TAG_result.png`. Expected: "bonus check: PASS" for all four.
The night counted 4,075 / 4,075, 4,078 / 4,077 and 4,078 / 4,078 VBLANKs / splits.

### 5.10 The restore and the new game

`after_{m2,tr}` (`hz7_after_setup` with `fail` on the `pz1` build) and `fresh_{m2,tr}`
(`hz7_fresh_setup` on the `ext` build) are in `suite_flows`.

```sh
python3 -I tools/bstest/restorecheck.py W/O/flow after_m2 fresh_m2 --known
python3 -I tools/bstest/restorecheck.py W/O/flow after_tr fresh_tr --known
PY=~/.venvs/msxports/bin/python
$PY -I tools/checkrun.py W/O/flow/after_m2_snaps build/msx/level1 build/msx/hud
$PY -I tools/checkrun.py W/O/flow/fresh_m2_snaps build/msx/level1 build/msx/hud
grep lost W/O/flow/after_m2_after.txt
```

The checks:

- after the stage: page 2 equals `level1.vram`'s tiles, page 3 lines 0-87 (the atlas) are the
  intro's, and both SATs start with Y = 216;
- at the new game's frame 50, against a fresh start: page 2, the atlas, the sprite tables, the
  HUD and the mirror D000h-DFFFh;
- the checkrun commands run for the `_tr` snapshot sets too.

**The 72 known bytes.** The sprite tables differ in 72 bytes in every run of the night, all
harmless:

- the colour rows of sprites 0-1 of both sets (1E000h-1E01Fh, 1E400h-1E41Fh) hold the cursor's
  colours where a fresh machine holds power-on bytes; the engine rewrites them before use;
- SAT entries 30-31 of both sets (1E278h-1E27Fh, 1E678h-1E67Fh) hold the same two parked sprites
  in swapped sets: the engine's set phase is one flip apart.

Without `--known` that line FAILs (exit 1), as on the night. With `--known`, the colour rows are
left out and entries 30-31 must equal the fresh start's, in the same set or swapped: every line
PASSes.

`checkrun.py`: 0 pixels differ and every sprite pixel exact. Its "tile VRAM changed" item is the
tile cache, the same in the fresh start. Lost counters: mp 0, atr 0, rd 0, fb 0.

### 5.11 The real timer at 50 and 60 Hz

```
msx_local_cmd: hz6_time {W/O/flow} time_m2 {W/R/pzt/rc2.rom} {W/R/pzt/rc2.labels} Gradiente_Expert20_64K
```

Run it again with C-BIOS_MSX2_EU (50 Hz) and Panasonic_FS-A1GT, then read
`W/O/flow/time_*_time.txt`.

- In a `PZ_TEST=1` build without a script, board 0 left alone times out about 61 s after the
  stage's first pass.
- The night measured 60.959 s (pass 3044) on the Expert, 60.647 s (3043) at 50 Hz and 60.933 s
  (3043) on the FS-A1GT; `pz_done` with result 2 came 80 passes later.

### 5.12 Turbo R: PAUSE and the HUD blank

**PAUSE.**

```
msx_local_cmd: hz_chain [list [list pause_tr Panasonic_FS-A1GT [list hzp_setup {W/O/flow} pause_tr {W/R/pzt/rc2.rom} {W/R/pzt/rc2.labels} end] {$::hz_done} 900]]
```

Read `W/O/flow/pause_tr_pause.txt`. Expected:

- A7h <- 00h at `front_bonus`;
- PAUSE pressed during the stage changes nothing: passes, splits and VBLANKs go on;
- held through the end, the game waits after the result with the pause LED on (A7h <- 01h,
  splits = VBLANKs), and the title comes after PAUSE off;
- PAUSE on the title holds the CPU (VBLANKs +0), as before the bonus existed.

A hold during the stage leaves `pause_tr_held.bin`; `python3 -I tools/bstest/frozen.py
W/O/flow/pause_tr_held.bin W/held.png` shows what the screen showed then.

**The HUD blank** (`blank_tr` in `suite_flows`):

```sh
python3 -I tools/bstest/fixblank.py W/O/flow/blank_tr_blank.txt
```

Expected: "6 frame(s) without the HUD" (116.9 ms, 7.01 frame periods). Measured, not fixed: the
user's call (`docs/BRAINSTORM.md` section 7, default 2).

### 5.13 The matrix of generic set-ups

Shut the MCP's openMSX down first (`msx_local_shutdown`): the tool starts two of its own.

```sh
python3 -I tools/msxmatrix.py W/R/prod/rc2.rom --labels W/R/prod/rc2.labels --home "OMHOME"
python3 -I tools/msxmatrix.py W/R/pzt/rc2.rom --labels W/R/pzt/rc2.labels --home "OMHOME" --no-title
```

- `OMHOME` is the MSX-AI MCP's openMSX home: on this Mac, the msx-ai project's `.openmsx-home`
  next to this repository.
- `make matrix OMHOME=...` runs the first line on `build/msx/rc2.rom`.
- The set-ups: MSX2, MSX2+, turbo R, C-BIOS at 50 Hz, a disk interface before the cartridge, a
  slot expander, an FM-PAC, and a 2 MiB MegaRAM with an SCC, with an SCC+ or alone.
- Expected: all 10 PASS.
  - In title mode, the products' lines equal those of the build before.
  - With `--no-title`, `tick_n` rises by about 350 between 20 s and 27 s: the stage's 50 passes
    a second.
- Two negative checks FAIL, as they should: a product with `--no-title` (ticks 0->0) and a
  `PZ_TEST` build without it (no title).

### 5.14 Test candidates

Build each candidate in its own folder, then copy the ROM and its label file under the final
names: `CDIR/BASE.ROM`, `BASE-bonus.ROM`, `BASE-2M.ROM`, `BASE-bonus-2M.ROM`, each with its
`.labels`.

```sh
sh tools/bstest/build.sh W/cb/prod/rc2.rom TAG=3
sh tools/bstest/build.sh W/cb/bonus/rc2.rom PZ_TEST=1 TAG=3
sh tools/bstest/build.sh W/cb/prod2m/rc2.rom TAG=3 ROM_2M=1
sh tools/bstest/build.sh W/cb/bonus2m/rc2.rom PZ_TEST=1 TAG=3 ROM_2M=1
```

Then on fresh machines:

```
msx_local_cmd: c8_chain {CDIR} BASE {W/fresh} cand      (7 jobs; poll until done)
```

`c8_chain` runs:

- the title records of `BASE` and `BASE-2M` into `W/fresh` as `cand` and `cand_2m`;
- `c8_job` on `BASE-bonus.ROM` (Gradiente_Expert20_64K: `bonus_m2`; Sony_HB-F1XDJ_128K_Lite:
  `bonus_f1`) and on `BASE-bonus-2M.ROM` (`bonus2m_m2`). The cursor keys come from the keyboard
  (keymatrix row 8): down, right, down, left, down at passes 100-140, each held 5 passes. Then
  nothing, so that board 0 times out;
- 56 snapshots at passes 60-3000 and a record of 1,000 VBLANKs from pass 90;
- `prod_m2` and `prod_f1`: the product's whole flow.

Output goes to `CDIR/run`. The checks:

```sh
sh tools/bstest/hz.sh fresh W/fresh base cand
sh tools/bstest/hz.sh fresh W/fresh base cand_2m      # only game_ram.bin's 2 bytes at D032h may differ
python3 -I tools/bstest/bonuscheck.py CDIR/run prod_m2 --tag 3 --result time --gen W/cb/prod/gen
python3 -I tools/bstest/bonuscheck.py CDIR/run bonus_m2 --tag 3 --result time --gen W/cb/bonus/gen
python3 -I tools/bstest/stepcheck.py still CDIR/run/st_bonus_m2/p*.bin
python3 -I tools/bstest/stepcheck.py rec CDIR/run/st_bonus_m2/rec.bin --ref build/emu/pz_kbd_ram.jsonl
```

Run `bonuscheck.py` and both `stepcheck.py` lines again for `prod_f1`, `bonus_f1` and
`bonus2m_m2`. Expected:

- PASS everywhere;
- 56 snapshots with 0 differences;
- 1,000 records = 500 pictures with 0 torn blocks, 0 pixels outside the elements and 0 cursor
  errors; the face shows in 63 of the 500;
- `CDIR/run/*_c8.txt`: the cursor on (0, 3), 2 red chips gone, the score 0200.

Screenshots: `python3 -I tools/bstest/shots.py CDIR/shots CDIR/run/bonus_m2_intro.bin
CDIR/run/st_bonus_m2/p0155.bin CDIR/run/st_bonus_m2/p3000.bin CDIR/run/bonus_m2_result.bin`.

Then `tools/msxmatrix.py` on the four files (5.13), and the candidates' notes: hashes, what to
test, known limits and the minimum hardware (a 2 MiB Konami SCC device for the complete game).
Copy to `build/msx` only the exact files sent.

### 5.15 The image and the option sets

```sh
python3 -I tools/bstest/romdiff.py W/old/rc2.rom W/new/rc2.rom
python3 -I tools/bstest/relocheck.py W/old/rc2.rom W/new/rc2.rom W/old/rc2.labels W/new/rc2.labels 0 78
sh tools/bstest/variants.sh W/var
```

- `romdiff.py` names the banks that differ. Expected: only the banks the change touched. The
  data banks 10-77 never changed during Brainstorm's milestone 1.
- `relocheck.py` passes when a code bank's other differences are only operands of labels that
  moved ("relocheck: PASS", exit 0). For example, a `TAG` build against the `TAG=0` one in banks
  0 and 78, or the review fix's FRONT change.
- `variants.sh` builds the night review's 41 option sets ("NAME OK" or "NAME FAIL: the first
  error"). At `14bc5ef` all built except `DEMO_ACTORS=2`/`5` and `DEMO_HUD=1`, which overflow the
  fixed area at `52149b0` too.

### 5.16 Unit tests

```sh
perl -e 'alarm 1500; exec @ARGV' make test
```

The night ended with the 4 known failures only (`test_tools`: the sprite data and the joystick
script). `tests/test_bstest.py` checks this harness without an emulator (section 9).

## 6. The whole suite in order

1. `sh tools/bstest/hz.sh builds W/R`, and the base reference if the milestone has none yet
   (5.3).
2. `msx_local_boot`; `source {<repo>/tools/bstest/load.tcl}`.
3. `hz_chain [suite_drives {W/R} {W/O}]`, poll until done, then `sh tools/bstest/check_all.sh
   W/O m2 tr fx eu` and 5.7-5.8's greps.
4. `hz_chain [suite_flows {W/R} {W/O} {W/fresh} NEWTAG]`, poll until done, then 5.9's and 5.10's
   commands and `fixblank.py`.
5. The checks the suite does not run: `hz6_arm` (5.4), `hz6_time` (5.11), `hzp_setup` (5.12)
   and `hudcheck.py` against the base (5.6).
6. `msx_local_shutdown`; the matrix (5.13); `make test`.

## 7. For the next milestones

- **Sound (milestone 2).**
  - The title's music must stay register-exact: 5.3's `music.txt` and `psg.txt` cover it.
  - The stage's sound must not move its logic: the drives (5.4) still give 0 differ.
  - The PZM register logs per tick and the effect checks of `docs/BRAINSTORM.md` 4.3 are not in
    this harness yet.
  - A new bank or a larger `music.asm` shows in `romdiff.py`. Mind the SCC test values that
    `tools/mkrom.py` checks.
- **The second visit (milestone 3).**
  - `stepcheck.py` renders visit 1: `msxpuzl.Puzl`'s default, and `render(..., visit=1)`.
  - Once visit 2 has its own pictures (Ellen), give it the visit
    (`msxpuzl.Puzl(data, (1, 2))`, `render(state, cursor, 2)`) before checking `solve2` /
    `fuzz2` stills and records.
  - Until then, check visit-2 snapshots as visit 1, as the night did.
- **New warnings or labels.**
  - `KNOWN_WARNINGS=n` when a change adds z80asm's known warning on purpose.
  - The labels and addresses of section 2 must exist in every build the harness drives.
  - The `PZ_TEST` hooks (`pz_tick`: exactly `call pz_frame`; `pz_done` in fixed code) are the
    trace harness's contract (`docs/BRAINSTORM.md` 4.1).

## 8. What changed when the harness moved

The checks are the night's. These are the only changes:

- **Paths.** Every path is now repository-relative or an argument.
  - The scripts find the repository from their own place.
  - `hz.tcl` sets `::hz_root` from `[info script]`.
  - `run8.tcl`'s `c8_chain` takes the candidates' folder, their base name, the title
    references' folder and a tag. It refuses missing files.
  - `hz.sh` prints its `msx_local_cmd` lines with absolute paths; `hz.sh product`'s line names
    the reference folder and the tag as placeholders (`FDIR`, `TAG`).
- **New.**
  - `load.tcl`.
  - `hz.sh builds` and `hz.sh compare DIR [LABELS]`; the night copied the label file next to the
    suite's traces instead.
  - `build.sh`'s `SRC=` and `KNOWN_WARNINGS=`, and `.ROM` names (the label file is then the
    ROM's name with `.labels`, as `mkrom.py` writes it).
  - `restorecheck.py --known`.
- **Safety.**
  - `build.sh` makes OUT absolute and refuses `build/msx` before it creates any folder.
  - `hz_clean` also closes the channels a job keeps open (`rc2_pz_arm`'s trace, `hz7.tcl`'s
    record, `fixchk.tcl`'s event log): a job that timed out left them open before.
  - The note and dump writers close their file even if a write fails.
  - `relocheck.py` and `romdiff.py` have a `main()`, so they can be imported. `relocheck.py`
    exits 1 on FAIL (it printed FAIL with exit 0).

## 9. Checked without an emulator when the harness moved

No openMSX was run. The Python tools and the shell scripts ran against the night's records and
ROMs in the scratch folder, before it was cleared, next to the night's own versions of the same
scripts; their outputs were compared.

- **`check_all.sh`** (puzlcmp, `stepcheck.py still` and `rec` over all 20 drive jobs) printed
  the night's `check_all.txt` line for line: PASS.
- **`bonuscheck.py`** gave identical output and PNGs on 9 flows and candidate runs (all PASS).
  The PNGs equal the night's.
- **`restorecheck.py`, `hudcheck.py`, `fixblank.py`, `frozen.py`, `romdiff.py` and
  `relocheck.py`** gave identical output on the night's records and ROMs. `restorecheck.py
  --known` PASSes on all four restore records. `shots.py`'s PNGs equal the night's screenshots.
- **`hz.sh compare`** reproduced the night's regression verdict, and `hz.sh fresh` the seven
  title comparisons, including the 2 MiB twin's 2 bytes.
- **`hz.sh builds`** with `SRC=` (an export of `16507dd`) gave the six suite images of the night
  byte for byte (`97011aac`, `9c1f8196`, `b0346483`, `bb39c329`, `3b1c8786`, `3b868e3f`). `build.sh`
  rebuilt the candidates `test2` and `test2-bonus-2M` byte for byte.
- **`tests/test_bstest.py`** (23 tests):
  - every tool compiles and imports;
  - the helpers on made-up data;
  - `build.sh`, `hz.sh builds` and `variants.sh` against a stub `mkrom.py`, including the
    `build/msx` refusals;
  - every Tcl file is complete, with no `exit`, `vwait`, `max` or `min`;
  - a tclsh session with openMSX mocked: `hz_chain` (done, timeout, setup error, machine error),
    `hz_clean` (a mutation test confirmed it catches the old leak), `hz_fresh`'s and
    `hz_bonus`'s records as `hz.sh fresh` and `bonuscheck.py` read them, `hz7.tcl`'s snapshot
    and record sizes against `stepcheck.py`'s layout, the suite's job lists, `c8`'s key presses
    and `hzf_done`.

**Not tested without an emulator.** The Tcl procs against a real openMSX: machine switches,
breakpoints in banked code, `rc2_guard`, `rc2_count_too_fast` (5.8), `turborpause` (`hzp_*`),
the timings `hzb_*` measures, `hz6_*`, `hz7_after_setup` / `hz7_fresh_setup`, `c8_step`'s
snapshots, and `suite_drives`, `suite_flows` and `c8_chain` end to end. These are the night's
procs with the changes of section 8 only; their first real run is the next milestone's suite.
`variants.sh` ran only against the stub; `build.sh` ran with the real `mkrom.py`.
