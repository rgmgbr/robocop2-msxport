# The acceptance harness (`tools/bstest/`)

The scripts that accepted Brainstorm, the bonus stage after level 1, on the night of 2026-10-27
(`docs/BRAINSTORM.md` section 4). They were written in a session's scratch folder, which macOS
clears, and live here so that the next milestones (the stage's sound, the second visit) run the
same checks. Every check below ran that night; section 9 lists what was verified again when the
scripts moved, without an emulator.

The final checks' scripts (`np.tcl`, `ft.tcl`, `run8f.tcl`, `titlecmp.py`, `titlecmp2.py`,
`partialcheck.py`; `docs/BRAINSTORM.md` 4.6) ran later that morning, before the test candidates
went out, and followed the others here: their checks are 5.17, and section 10 says what changed
and what was verified when they moved.

The shooting range, the second bonus stage, adds its display's checks (`rgview.tcl`, `rgview.py`,
`rgview.sh`): section 5.18. Its milestone's whole regression (the flows through the range, its
screens, its logic after a played level 1 and Brainstorm, its sound, the product from the keyboard,
and every Brainstorm check run again through the new flow) is section 5.19: `regress.sh`,
`regress.tcl`, `rgflow.tcl`, `frsound.tcl`, `rgcheck.py`, `cmpcheck.py` and `frsnd/`. They were
written in the range chain's scratch folder and moved here at its step 10 (section 11).

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
| `c8.tcl`, `run8.tcl` | Tcl | `c8_job` (a PZ_TEST ROM from power-on, cursor keys from the keyboard), `c8_chain` (the test candidates; `c8_jobs`: its job list) |
| `np.tcl` | Tcl | the final checks' flows (5.17): `np_job`, `np_keys_arm` (a drive's moves from the keyboard), `np_solved_setup`, `np_title_setup` / `np_title0_setup` (the title's exact record), `np_fire_setup`, `np_two_setup` / `np_two_title_setup`, `np_wp_job` |
| `ft.tcl` | Tcl | VRAM writes lost at another Z80 clock (5.17 g): `ft_job`, `ft_flow_job`, `ft_boot_job`, `ft_l1_job` |
| `run8f.tcl` | Tcl | `c8f_chain`: `c8_chain`'s jobs and the solved ending from the keyboard (5.17 h) |
| `check_all.sh OUT TAG...` | shell | for every drive job: `tools/puzlcmp.py`, `stepcheck.py still`, `stepcheck.py rec` |
| `stepcheck.py still` / `rec` | python | the stage's pictures against `tools/msxpuzl.py`'s render (5.5) |
| `bonuscheck.py DIR TAG` | python | the bonus text screens against `tools/msxtext.py`'s render, the HUD split at every VBLANK, the title, the new game (5.9); `--range time\|C,D,M`: the range's screens recorded in the same flow (5.19); `--no-game` |
| `restorecheck.py DIR AFTER FRESH [--known]` | python | what the stage leaves: page 2, the atlas, the SATs; the next game against a fresh start (5.10) |
| `hudcheck.py NEW_DIR REF_DIR` | python | the HUD during the stage against a reference build's at the same passes (5.6) |
| `shots.py OUT SNAP...` | python | whole-screen PNGs of snapshots (play area, blank lines, HUD; 2x) |
| `fixblank.py FILE` | python | the HUD's blank at the turbo R's CPU switch (5.12) |
| `frozen.py SNAP OUT.png` | python | what the VDP shows while the CPU is held (5.12) |
| `romdiff.py A B` | python | the 8 KiB banks that differ |
| `relocheck.py OLD NEW OLD.labels NEW.labels BANK...` | python | a code bank's differences are only relocated label words (5.15) |
| `variants.sh OUT` | shell | the night review's 41 option sets, built (5.15) |
| `titlecmp.py DIR A B` | python | two title records taken apart: the picture as the VDP shows it, the VRAM it does not show, the registers, the palette; an `hz_fresh` record's music, PSG writes and game too (5.17 b) |
| `titlecmp2.py DIR A B [--unheard]` | python | two exact title records: the music per music tick (the SCC's and PSG's registers, named; the PSG writes), the game at its tick 300 (5.17 b) |
| `partialcheck.py SNAP LABEL [--tag N]` | python | a text screen cut short by fire against the render of its script as far as it got (5.17 d) |
| `rgview.tcl` | Tcl | the shooting range's display checks (5.18): `rgv_job` (snapshots at passes, a record at every VBLANK, the camera's pokes, the HUD's register probe), `rgv_tjob` (a trace), `rgv_guard_job`, `rgv_fast_job`, `rgv_rate_job`, `rgv_after_setup` (the restore), `rgv_suite W` (all 81 jobs) |
| `rgview.py still` / `rec` / `rate` / `probe` / `want` | python | the range's pictures against `tools/msxrange.py`'s render and the bench's states at the camera; the cut; the picture rates; the pass rate; the register probe (5.18); the wanted state at every pass (5.19) |
| `rgview.sh builds W` / `check W` | shell | the range's four test builds; every verdict of 5.18, then "rgview: PASS" |
| `regress.sh base B` / `basecheck B` / `builds W` / `check W B [FAMILY ...]` | shell | the range milestone's whole regression (5.19): the base 4a8a61d rebuilt from a worktree, the builds, every verdict against the base, then "regress: PASS" |
| `regress.tcl` | Tcl | `rgr_chain W ?FAMILY? ?MARK?` (flows, final, drives, range, display, sound; 207 jobs with all), `rgr_jobs`, `rgr_base_chain B` (the base's records) |
| `rgflow.tcl` | Tcl | the range's flows (5.19): `rgx_job` (PZ_TEST=2), `rgx_arm_job` (after level 1 and Brainstorm), `rgx_tarm_job` (the range traced there), `rgx_want_job` (the wanted state), `rgk_job` (the product from the keyboard), `rgh_arm` (the range's screens inside Brainstorm's flows), `rgx_timeout_if` |
| `frsound.tcl` | Tcl | the range's sound logs (5.19): `frs_drive`, `frs_alone`, `frs_suite W ?REC?` |
| `rgcheck.py DIR TAG (--counts C,D,M \| --time) [--tag N] [--no-game]` | python | the range's text screens against `tools/msxtext.py`'s render, the HUD split, the result at `fr_done`, the rating at `fr_rated`, SHARP and the lost counters at the new game (5.19); `bonuscheck.py --range` calls it |
| `cmpcheck.py BASE.log NEW.log [OUT]` | python | two `check_all.sh` logs job by job; a torn cell accepted only under a black palette (5.19) |
| `frsnd/frregcmp.py ROOT LOG...` | python (venv) | FRM's registers per tick in an `frsound.tcl` log against `frm.bin`'s streams decoded apart; `--selftest` (5.19) |
| `frsnd/frsim.py ROOT ROM LABELS` | python (venv) | the range's sound on a ROM image in a Z80 interpreter (`frsnd/z80.py`, `frsnd/pzsim.py`: Brainstorm's), offline (5.19) |
| `frsnd/frwavcmp.py`, `frsnd/fxalone.py` | python (venv) | recordings judged by pitch against the converter's previews (`frsnd/int_wavcmp.py`'s measures; 5.19) |

The Tcl reads these labels from a ROM's label file:

- the stage: `pz_tick`, `pz_frame`, `pz_done`, `pz_boards`, `ext_joy`, `iv_late`;
- the bonus texts and the interrupts: `txt_bs_*`, `isr_split`, `isr_vblank`, `INPUT_SCRIPT`;
- the title's music: `BANK_MUSIC`, `mus_adv`;
- the game tick: `tick_start`, `game_tick`;
- the CPU switch: `cs_go`, `display_on`, `front_bonus`;
- the final checks: `new_game` (`np_two_setup`), `init` (`ft_boot_job`: its first byte must be DI,
  F3h);
- the shooting range (5.18): `fr_tick`, `fr_frame`, `fr_done`, `fr_rated`, `fr_code`, `ac_diff`,
  `diff_tab`, `rg_loop`, `tick`, `iv_late`, `txt_rg_intro`, `txt_bs_time` and the other `txt_`
  labels (a text's span ends at the next one); the camera's checks: `rg_want`, `RG_ST_S` (the
  pokes), `sp_r19`, `split_list`, `hud_msk` (the probe); the flows (5.19): `fs_buf`, `new_game`,
  `display_on`, `txt_rg_res`, `rg_blost`; the sound: `tns_go`, `tn_tick`, `tn_left`, `snd_rfx`,
  `snd_stop`, `BANK_MUSIC`.

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
| C2A6h | `cpu_tr` | C623h | `msg_wr` |
| EE40h | `rgs0` (the range) | EE68h | `rgs1` (the range) |

The Amiga mirror is read at D000h (`$B00` + n) and DC00h (`$8000` + n). The BIOS's RG9SAV (FFE8h)
and CASPRV (FCB1h) are read too. If `msx.inc` moves one of these, update the scripts.

## 3. Reference files

None of these is committed (`build/` is git-ignored; data from the game is never committed).

| Reference | Used by | How it is made |
|---|---|---|
| `build/msx/*` (conversions: `level1.*`, `hud*`, `text_bs_*.sc5`, `puzl*`, `pzm.bin`) | every build; `bonuscheck.py` (`text_bs_*.sc5`); `restorecheck.py` (`level1.vram`) | `make msx` |
| `build/ram/level1_full.bin`, `build/extracted/files/PUZL_25.bin` | `bonuscheck.py`, `stepcheck.py`, `shots.py` (`stepcheck`'s renders) | `make ram`, `make extract` |
| `build/emu/drive_cov1.txt`, `drive_cov0.txt` and `trace_cov1_ram.jsonl` (4,401 rows), `trace_cov0_ram.jsonl` (20,541 rows) | the level-1 regression (5.2); `drive_cov1.txt`: `ft_l1_job` (5.17 g) | made in earlier sessions. The drives are `tools/drivejoy.py` files, their bench arguments in their `.args` files (`drivejoy.py --scenario level1` makes such drives from `tools/amigacov.py`'s coverage scenario). A trace is `$PY -I tools/amigaemu.py game --gframes N --drive build/emu/drive_covK.txt --trace build/emu/trace_covK_ram.jsonl --trace-ram` (N + 1 rows); `--gframes 600` reproduced the first 601 rows of `trace_cov1_ram.jsonl` byte for byte when the harness moved. Keep them: the regression compares against them as they are |
| `build/emu/drive_end.txt` | `hz_bonus ... end`, `hz6_arm`, `hz6_prod`, `hzb_setup`, `np.tcl`'s flows (5.17) | four lines: no joystick, the teleport `100:0x900:0x2d0`, no god mode, the poke `150:5826:80:2` (`tools/drivejoy.py`'s format). Level 1 ends by game frame 517 |
| `build/emu/pz_<name>.drive` and `pz_<name>_ram.jsonl` for `solve1`, `solve2`, `fail`, `timeout`, `fuzz1`, `fuzz2`, `quirk2`, `quirk1` | the drives (5.4), stills and records (5.5); `pz_solve1.drive` and `pz_fail.drive`: the final checks' runs and keyboard moves (5.17) | `docs/BRAINSTORM.md` 4.5 (`tools/puzlsolve.py`, `tools/drivejoy.py`, then `$PY -I tools/amigaemu.py puzl --pframes 2000 --drive build/emu/pz_<name>.drive --trace build/emu/pz_<name>_ram.jsonl --trace-ram`; `--pframes 3000` for the fuzz drives, `--level 2 --ram build/ram/level2_full.bin` for visit 2) |
| `build/emu/pz_opp.drive`, `pz_opp_ram.jsonl` | the `opp` drive | written by hand in `tools/drivejoy.py`'s four-line format: lines 1-2 empty (no joystick, no teleport), line 3 `0` (no god mode), line 4 the 19 pokes `40:32814:2:1 44:32814:12:1 48:32814:3:1 52:32814:15:1 56:32814:140:1 60:32814:2:1 64:32814:12:1 68:32814:8:1 72:32814:12:1 76:32814:8:1 80:32814:3:1 84:32814:12:1 88:32814:3:1 92:32814:15:1 96:32814:5:1 100:32814:10:1 104:32814:6:1 108:32814:9:1 160:32844:255:1`; then `$PY -I tools/amigaemu.py puzl --pframes 2000 --drive build/emu/pz_opp.drive --trace build/emu/pz_opp_ram.jsonl --trace-ram` (203 passes, result 1) |
| `build/emu/pz_kbd.drive`, `pz_kbd_ram.jsonl` | the candidates' keyboard moves (5.14) | `python3 -I tools/drivejoy.py --joy 100:5:d,110:5:r,120:5:d,130:5:l,140:5:d build/emu/pz_kbd.drive`, then `$PY -I tools/amigaemu.py puzl --pframes 1000 --drive build/emu/pz_kbd.drive --trace build/emu/pz_kbd_ram.jsonl --trace-ram` (1,001 rows, still playing; both equal the night's `cand/bench/kbd*` byte for byte) |
| **The title reference**: `FDIR/BASE_*` | the title check (5.3) | `hz_fresh` on the product ROM of the commit before the change (5.3) |
| A reference build's snapshots | the HUD check (5.6) | the same `hz7_job` on the commit before the change |
| **The approved title flow**: `W/O/np/t0x_<m>_*` | the title after Brainstorm (5.17 b) | `np_title0_setup` (a base without Brainstorm) or `np_title_setup` (a base with it) with EXACT 1 on the product of the commit before the change (5.3's base build), on each machine |
| `build/emu/fr_<name>.drive` and `fr_<name>_ram.jsonl` for the range's 15 drives (`armed`, `mixed`, `dummy`, `poor`, `fair`, `good`, `good_min0`, `timeout`, `late_timeout`, `hold`, `opp`, `edge`, `fuzz`, `quirk4`, `armed2`) | the range's traces (5.18, 5.19), its keyboard flow (`fr_armed`), its sound logs (`fr_mixed`) | `docs/RANGE.md` 4.5: `$PY -I tools/frngbot.py` for the bot drives, the hand-made ones a poke line added (`tools/drivejoy.py`), then `$PY -I tools/amigaemu.py frng --fframes 3000 --drive build/emu/fr_<name>.drive --trace build/emu/fr_<name>_ram.jsonl --trace-ram` (`--level 2 --ram build/ram/level2_full.bin` for `armed2`, `--fframes 80` for `opp`) |
| **The range milestone's base**: `B` (`B/R`, `B/O`, `B/fresh`, `B/check_all.log`) | `regress.sh check W B` (5.19) | `regress.sh base B`, `rgr_base_chain`, `regress.sh basecheck B` (5.19) |

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
- Gradiente_Expert20_64K (the user's Hotbit's twin) and Sony_HB-F1XDJ_128K_Lite (V9958);
- C-BIOS_MSX2+ (V9958; the speed jobs at 5.37 MHz, 5.17 g).

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

`hzf_job` (in `suite_drives`, `W/O/flow/fast_{m2,tr}.txt`) counts with `rc2_count_too_fast`
(`tools/openmsx_rc2.tcl`, `too_fast_vram_access real`). It covers `solve1` with the entry's
uploads and the exit's restore, on C-BIOS_MSX2 and the FS-A1GT at 3.58 MHz. Expected: "too fast
VRAM accesses: 0 ...; result 0, passes 732".

**The counter counts since `b59a338`.**

- openMSX runs a callback setting's value as a command, with the event's arguments appended: it
  must name a proc. openMSX's own `share/scripts/callbackprocs.tcl` does `set
  VDP.too_fast_vram_access_callback warn_too_fast_vram_access`.
- Before `b59a338`, `rc2_count_too_fast` set an inline script there, which failed silently: it
  never counted, and the zeros of the night's runs before `b59a338` were not measurements. Since
  `b59a338` it names a proc, `rc2_too_fast_cb`.
- It has been seen to move. With it, `solve1` from the power-on to `pz_done` (`ft_job`, 5.17 g):
  - at 5.37 MHz with the code before `rs_one`'s fix (`14bc5ef`'s): 5 lost writes on the Panasonic
    FS-A1FX and 43 on C-BIOS_MSX2+, all at `rs_one`'s two 17 T writes (C-BIOS_MSX2+ adds 1 in
    its own boot code, before the cartridge starts);
  - at 5.37 MHz with the fix (`b59a338`): 0 in the cartridge on both;
  - at 3.58 MHz: 0 measured, before and after the fix (C-BIOS_MSX2, the FS-A1FX, the FS-A1GT).
- **Another clock.** `hz_cfg` sets `z80_freq` to 3,579,545 Hz and `z80_freq_locked on` on every
  new machine, and openMSX ignores `z80_freq` while it is locked. For another clock, set
  `z80_freq_locked off` after `hz_cfg`, then `z80_freq`: in the job's setup, as `ft.tcl`'s jobs do
  (`ft_clock`). `hz_cfg` locks it again for the next job.

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
script). `tests/test_bstest.py` checks this harness without an emulator (sections 9 and 10).

### 5.17 The final checks (`np.tcl`, `ft.tcl`, `run8f.tcl`)

The final checks of 2026-10-27 (`docs/BRAINSTORM.md` 4.6) ran the paths no earlier check had run,
and measured the VRAM speed at 5.37 MHz with the counter that counts (5.8). They run in the
session of section 4: `load.tcl` sources `np.tcl`, `ft.tcl` and `run8f.tcl` too. Start a chain only
after the one before reads `done`. The builds:

- `W/R` (5.1): `pz1` (`EXTJOY=1 PZ_TEST=1`, a script build), `prod` (the product) and `trace`;
- the candidates `CDIR/BASE*.ROM` (5.14), built in `W/cb/{prod,bonus,prod2m,bonus2m}`.
  `BASE-bonus.ROM` (`PZ_TEST=1 TAG=N`) has no script: its stage takes the keyboard;
- for b, the product of the commit before the change (5.3's base build, `W/base/rc2.rom`).

Output goes to `W/O/np` and `W/O/fast`. The numbers below are the night's, at `b59a338` with
`TAG=2` candidates: the expected results (with another tag, `--tag N` and "TEST N").

**Jobs.** `np_job NAME MACHINE SETUP DIR ROM LABELS [ARG ...]` makes an `hz_chain` job of a setup:
`SETUP DIR NAME ROM LABELS ARG ...` on a new machine until `::hz_done`, 900 s at most. NAME is
also the records' tag. `np_wp_job` and `ft.tcl`'s jobs have done conditions of their own.

**The keyboard as a drive.** A build without `EXTJOY` ignores a drive's script, so `np_keys_arm
LABELS DRIVE` presses the drive's joystick bytes on the keyboard (row 8). At each `pz_tick` the
byte of PUZL frame `$B00` becomes keys: up 1 UP (20h), down 2 DOWN (40h), left 4 LEFT (10h), right
8 RIGHT (80h), fire 10h SPACE (01h). Every key is let go past the drive's end and at `pz_done`.
The keyboard sets bit 7 of the joystick byte (`$802E`, `$B1E`), and a build without a script
counts real seconds: such traces compare with `--skip joy,last_joy,timer_min,timer_sec` (395
fields).

#### a. The solved ending

```
msx_local_cmd: hz_chain [list [np_job solved_m2 C-BIOS_MSX2 np_solved_setup {W/O/np} {W/R/pz1/rc2_pz1.rom} {W/R/pz1/rc2_pz1.labels}] [np_job solved_tr Panasonic_FS-A1GT np_solved_setup {W/O/np} {W/R/pz1/rc2_pz1.rom} {W/R/pz1/rc2_pz1.labels}] [np_job solved_cand_ex Gradiente_Expert20_64K np_solved_setup {W/O/np} {CDIR/BASE-bonus.ROM} {CDIR/BASE-bonus.labels} 1]]
```

The last argument, 1, also presses `solve1`'s moves on the keyboard, for the build without a
script; a script build reads them from `ext_joy`, which `rc2_pz_drive` feeds in both cases. Poll
until done (section 4), then:

```sh
python3 -I tools/puzlcmp.py build/emu/pz_solve1_ram.jsonl W/O/np/solved_m2_pz.txt
python3 -I tools/bstest/bonuscheck.py W/O/np solved_m2 --result ok --gen W/R/pz1/gen
python3 -I tools/puzlcmp.py --skip joy,last_joy,timer_min,timer_sec build/emu/pz_solve1_ram.jsonl W/O/np/solved_cand_ex_pz.txt
python3 -I tools/bstest/bonuscheck.py W/O/np solved_cand_ex --tag N --result ok --gen W/cb/bonus/gen
```

and the first two lines for `solved_tr`. Expected:

- "732 PUZL frames compared (732 Amiga, 732 MSX), 399 fields: 0 differ" (`solved_cand_ex`: 395
  fields) and "result: Amiga 0, MSX 0";
- "bonus check: PASS". WELL DONE MEMORY RESTORED. / GAME CREDIT AWARDED equals its render; the
  result line reads `805Eh 1` (the game credit); 1,237 VBLANKs and 1,238 HUD splits between the
  records (`solved_cand_ex`: 1,238 and 1,238); then the new game. A script build has no title, so
  its new game follows the result; `solved_cand_ex` shows the title and takes fire first.

#### b. The title after Brainstorm, against the approved title

The title that follows a flow is recorded as `hz_fresh` records a fresh machine's (5.3), but in a
form that compares two runs whose titles start at different emulated times (EXACT = 1):

- `TAG_title_vram.bin`, `TAG_title_regs.bin` and `TAG_title_pal.bin`, once the title shows plus
  1 s;
- `TAG_music2.txt`: a line per music tick, keyed by `mus_tick`: the SCC's registers, the PSG's,
  and the count and hash of the PSG writes since the tick before;
- `TAG_game2_vram.bin`, `TAG_game2_ram.bin` (D000h-DFFFh) and `TAG_game2.txt`: the game the title
  starts by itself, at exactly its tick 300 (a breakpoint at `tick_start`).

`np_title_setup` runs the product's flow (`hz6_prod_setup`: the title, fire, level 1 ended by
`drive_end`, the statistics, Brainstorm left to its time out, OUT OF TIME.) and records the title
that follows the result. `np_title0_setup` records the title that follows level 1's statistics in
a build without Brainstorm: the approved flow. The night's reference was the product of the
commit before Brainstorm (the night's step 0: `msx/` as at `90ca7b3`). A later milestone, whose
base has Brainstorm, records its base build with `np_title_setup` instead.

```
msx_local_cmd: hz_chain [list [np_job t0x_ex Gradiente_Expert20_64K np_title0_setup {W/O/np} {W/base/rc2.rom} {W/base/rc2.labels} 1] [np_job tx_ex Gradiente_Expert20_64K np_title_setup {W/O/np} {W/R/prod/rc2.rom} {W/R/prod/rc2.labels} 1]]
```

Add the same two jobs on `Sony_HB-F1XDJ_128K_Lite` (`t0x_f1`, `tx_f1`) and `Panasonic_FS-A1GT`
(`t0x_tr`, `tx_tr`); all six may go in one chain. Then, for each machine:

```sh
python3 -I tools/bstest/titlecmp.py W/O/np t0x_ex tx_ex
python3 -I tools/bstest/titlecmp2.py W/O/np t0x_ex tx_ex --unheard
```

Expected, after Brainstorm against without it:

- `titlecmp.py`: "the title's picture (G7, 256 x 212): identical", "palette: identical" and
  "registers: identical", except `['R#5 C7/CF', 'R#19 9C/9D']` on the FS-A1GT (the title has its
  sprites and its line interrupt off). "VRAM not shown by the title" differs (the stage's pages
  and tables). The exact records have no `music.txt`, `psg.txt` or `game_*`: it says so for each.
- `titlecmp2.py`:
  - the Expert: "5044 common ticks compared (150851 PSG writes in them): differ {'SCC': 0, 'PSG
    regs': 0, 'PSG writes': 0}";
  - the HB-F1XDJ: the same ticks and writes. The SCC differs at every tick in A6h, A7h and their
    mirror B6h, B7h (`freq3`): channel 3's frequency, with the channel off at every tick ("heard
    at 0");
  - the FS-A1GT: 5,045 ticks and 130,432 writes. The same SCC registers differ, and the PSG's R6
    (the noise period) with the noise off on all three channels;
  - "titlecmp2: PASS" on all three with `--unheard`. Without it, it exits 1 on the HB-F1XDJ and
    the FS-A1GT, as the night's copy did: "titlecmp2: FAIL (only registers neither run can hear
    differ: --unheard passes them)";
  - the game at tick 300 is reported, not judged. Its RAM differs in D032h-D033h (the random word
    `$B32`, seeded from R) and, on the Expert, in DC4Ah, the level timer's seconds:
    `'DC4A 44/45'`, the BCD word DC4Ah-DC4Bh reading 9:44 without Brainstorm and 9:45 after it.
    Its VRAM differs in 9,615 bytes on the Expert, 29 of them in the HUD (its rows 5-18, x
    240-251); 23,963 on the HB-F1XDJ and 26,795 on the FS-A1GT, none in the HUD.
- The night's reading of these, that nothing that differs is seen or heard, is in
  `docs/BRAINSTORM.md` 4.6 b.

The night first recorded with EXACT = 0 (`hz_fresh`'s files: `titlecmp.py` reads their music by
line and their PSG count). Those windows start at 0.1 s polls: on the Expert they read 151,212
against 151,182 PSG writes, and on the other two their music lines were a tick or two apart. Use
EXACT = 1.

#### c. The 2 MiB product's level end into Brainstorm

```
msx_local_cmd: hz_chain [list [np_job prod2m_ex Gradiente_Expert20_64K hz6_prod_setup {W/O/np} {CDIR/BASE-2M.ROM} {CDIR/BASE-2M.labels}]]
```

```sh
python3 -I tools/bstest/bonuscheck.py W/O/np prod2m_ex --tag N --result time --gen W/cb/prod2m/gen
```

Expected: "bonus check: PASS", 4,075 VBLANKs and 4,075 HUD splits, then the title, fire and a new
game.

#### d. Text screens ended by fire

`np_fire_setup` runs the bonus candidate from the power-on. SPACE is held 0.15 s once the intro's
`fs_n` reaches 60; the stage is stuck by the `fail` drive's moves from the keyboard; SPACE again
once the result's `fs_n` reaches 60; then the title and fire. `TAG_intro60.bin` and
`TAG_result60.bin` are snapshots taken just before each press.

```
msx_local_cmd: hz_chain [list [np_job fire_ex Gradiente_Expert20_64K np_fire_setup {W/O/np} {CDIR/BASE-bonus.ROM} {CDIR/BASE-bonus.labels}] [np_job fire_tr Panasonic_FS-A1GT np_fire_setup {W/O/np} {CDIR/BASE-bonus.ROM} {CDIR/BASE-bonus.labels}]]
```

```sh
cat W/O/np/fire_ex_fire.txt
python3 -I tools/bstest/partialcheck.py W/O/np/fire_ex_intro60.bin txt_bs_intro --tag N
python3 -I tools/bstest/partialcheck.py W/O/np/fire_ex_result60.bin txt_bs_fail --tag N
python3 -I tools/bstest/stepcheck.py still W/O/np/st_fire_ex/p*.bin
```

and the same for `fire_tr`. Expected:

- `fire.txt`: the intro ended at `fs_n` 61 and the stage's first pass came 0.724 s after the press
  (the FS-A1GT: 0.749 s); the result screen (fail) after 182 passes; its SPACE at `fs_n` 61 (the
  FS-A1GT: 60), the screen ended at the next call, and the title came 0.020 s after the press;
  fire on the title; the new game, "lost: mp 0 atr 0 rd 0 fb 0". The title ignores the SPACE still
  held: the new game comes from the later fire.
- `partialcheck.py`: "fire_ex_intro60.bin: fs_n 60: page 0 = the render of txt_bs_intro after 60
  fs_step calls (56 of its 95 characters, TEST 2 first), pixel for pixel"; the result "after 61
  fs_step calls (38 of its 38 characters, TEST 2 first)" (the FS-A1GT: 60 calls). Exit 0.
- `stepcheck.py still`: "7 snapshot(s), 0 with differences".

#### e. Two Brainstorms in one session

`np_two_setup` takes a script build through the first stage (the `fail` drive), its result and
the new game; then level 1, ended by `drive_end`, the statistics and the intro; then the second
stage, armed by `rc2_pz_arm` with `solve1`, its screens' records, and the new game.
`rc2_drive_hit` counts a drive's frames by `tick_n`, the ticks since the power-on, so the second
level 1 takes a copy of `drive_end.txt` moved by the new game's `tick_n` (`W/O/np/TAG_drive_end.txt`).

```
msx_local_cmd: hz_chain [list [np_job two_m2 C-BIOS_MSX2 np_two_setup {W/O/np} {W/R/pz1/rc2_pz1.rom} {W/R/pz1/rc2_pz1.labels}] [np_job two_tr Panasonic_FS-A1GT np_two_setup {W/O/np} {W/R/pz1/rc2_pz1.rom} {W/R/pz1/rc2_pz1.labels}]]
```

```sh
python3 -I tools/puzlcmp.py build/emu/pz_fail_ram.jsonl W/O/np/two_m2_pz1.txt
python3 -I tools/puzlcmp.py --skip score build/emu/pz_solve1_ram.jsonl W/O/np/two_m2_pz2.txt
python3 -I tools/bstest/bonuscheck.py W/O/np two_m2 --result ok --gen W/R/pz1/gen
```

Expected: 182 frames, 399 fields, 0 differ, result 1; 732 frames, 398 fields (the score carries
level 1's), 0 differ, result 0; "bonus check: PASS" with `805Eh 1`. The night's `two_tr` printed
FAIL on one item: its intro record read R#1 22h, with R#2 7Fh and R#23 29h, the HUD split's state
between its interrupt and the HUD (`docs/BRAINSTORM.md` 8.17). A sampling artefact: its text and
its splits (1,237 in 1,238 VBLANKs) pass.

`np_two_title_setup` does the same with the candidates' options: the moves from the keyboard and
the title, then fire, before each new game.

```
msx_local_cmd: hz_chain [list [np_job two_title_ex Gradiente_Expert20_64K np_two_title_setup {W/O/np} {CDIR/BASE-bonus.ROM} {CDIR/BASE-bonus.labels}] [np_job two_title_f1 Sony_HB-F1XDJ_128K_Lite np_two_title_setup {W/O/np} {CDIR/BASE-bonus.ROM} {CDIR/BASE-bonus.labels}] [np_job two_title_tr Panasonic_FS-A1GT np_two_title_setup {W/O/np} {CDIR/BASE-bonus.ROM} {CDIR/BASE-bonus.labels}]]
```

```sh
python3 -I tools/puzlcmp.py --skip joy,last_joy,timer_min,timer_sec build/emu/pz_fail_ram.jsonl W/O/np/two_title_ex_pz1.txt
python3 -I tools/puzlcmp.py --skip joy,last_joy,timer_min,timer_sec,score build/emu/pz_solve1_ram.jsonl W/O/np/two_title_ex_pz2.txt
python3 -I tools/bstest/bonuscheck.py W/O/np two_title_ex --tag N --result ok --gen W/cb/bonus/gen
```

Expected on all three machines: 182 frames, 395 fields, 0 differ, result 1; 732 frames, 394
fields, 0 differ, result 0; "bonus check: PASS".

#### f. Turbo R: no write to 4000h-7FFFh

On a turbo R the fixed area runs from a RAM copy in page 1, and nothing may write 4000h-7FFFh
after the copy (`docs/TURBO_R.md` 6). `np_wp_job` runs the product's flow with a write watchpoint
on 4000h-7FFFh from `front_bonus`' entry (its breakpoint needs `act_8000` = 7) to the new game's
tick 100.

```
msx_local_cmd: hz_chain [list [np_wp_job wp_tr Panasonic_FS-A1GT {W/O/np} {W/R/prod/rc2.rom} {W/R/prod/rc2.labels}]]
```

```sh
cat W/O/np/wp_tr_wp.txt
python3 -I tools/bstest/bonuscheck.py W/O/np wp_tr --result time --gen W/R/prod/gen
```

Expected: "watch from 43.208 s (front_bonus) to 124.708 s (the new game's tick 100, g_frame 100,
cpu_tr 1): 0 writes" (`cpu_tr` 1: the game found the R800, so it made the copy) and "bonus check:
PASS". Without that line the job did not reach the new game.

#### g. VRAM writes lost at another clock

Each `ft.tcl` job unlocks the Z80's clock after `hz_cfg` and sets FREQ (5.8), then
`too_fast_vram_access real` and the counter. `ft_job`, `ft_flow_job` and `ft_l1_job` place each hit
by its PC: the BIOS's code below 4000h, the cartridge's above, the first 8 of each with their
emulated times. FREQ is 5369318 (the Panasonic MSX2+ turbo) or 3579545.

- `ft_job NAME MACHINE ROM LABELS OUT FREQ [DRIVE]`: `build/emu/pz_DRIVE.drive` (`solve1`) on a
  script build, from the power-on to `pz_done`. `OUT/flow/NAME.txt`, and the trace
  `OUT/tr/NAME.txt`.
- `ft_flow_job NAME MACHINE ROM LABELS OUT FREQ`: a build without a script, the stage solved from
  the keyboard, to the title's start (a watchpoint on `front_mode`).
- `ft_boot_job NAME MACHINE ROM LABELS OUT FREQ`: the first 6 emulated seconds. Each BIOS hit with
  SP and the four words on the stack, and the time the cartridge's `init` starts.
- `ft_l1_job NAME MACHINE ROM LABELS OUT FREQ N`: level 1 by `drive_cov1` for N ticks on the trace
  build.

```
msx_local_cmd: hz_chain [list [ft_job fx537 Panasonic_FS-A1FX {W/R/pz1/rc2_pz1.rom} {W/R/pz1/rc2_pz1.labels} {W/O/fast} 5369318] [ft_job cb537 C-BIOS_MSX2+ {W/R/pz1/rc2_pz1.rom} {W/R/pz1/rc2_pz1.labels} {W/O/fast} 5369318] [ft_job m2358 C-BIOS_MSX2 {W/R/pz1/rc2_pz1.rom} {W/R/pz1/rc2_pz1.labels} {W/O/fast} 3579545] [ft_job fx358 Panasonic_FS-A1FX {W/R/pz1/rc2_pz1.rom} {W/R/pz1/rc2_pz1.labels} {W/O/fast} 3579545] [ft_job tr358 Panasonic_FS-A1GT {W/R/pz1/rc2_pz1.rom} {W/R/pz1/rc2_pz1.labels} {W/O/fast} 3579545]]
msx_local_cmd: hz_chain [list [ft_flow_job flow537_fx Panasonic_FS-A1FX {CDIR/BASE-bonus.ROM} {CDIR/BASE-bonus.labels} {W/O/fast} 5369318] [ft_flow_job flow537_cb C-BIOS_MSX2+ {CDIR/BASE-bonus.ROM} {CDIR/BASE-bonus.labels} {W/O/fast} 5369318] [ft_boot_job boot537_cb C-BIOS_MSX2+ {CDIR/BASE-bonus.ROM} {CDIR/BASE-bonus.labels} {W/O/fast} 5369318] [ft_boot_job boot358_cb C-BIOS_MSX2+ {CDIR/BASE-bonus.ROM} {CDIR/BASE-bonus.labels} {W/O/fast} 3579545]]
msx_local_cmd: hz_chain [list [ft_l1_job l1_537_fx Panasonic_FS-A1FX {W/R/trace/rc2_ext5.rom} {W/R/trace/rc2_ext5.labels} {W/O/fast} 5369318 1400] [ft_l1_job l1_358_fx Panasonic_FS-A1FX {W/R/trace/rc2_ext5.rom} {W/R/trace/rc2_ext5.labels} {W/O/fast} 3579545 1400]]
```

Each line is a chain: poll it until done before the next. Then:

```sh
cat W/O/fast/flow/*.txt
python3 -I tools/puzlcmp.py build/emu/pz_solve1_ram.jsonl W/O/fast/tr/fx537.txt     # and cb537, m2358, fx358, tr358
python3 -I tools/tracecmp.py --ram build/emu/trace_cov1_ram.jsonl W/O/fast/tr/l1_537_fx.txt --labels W/R/trace/rc2_ext5.labels
```

Expected at `b59a338`:

- `ft_job`: "too fast VRAM accesses 0: cartridge 0 {}, BIOS 0 {}" on every machine but C-BIOS_MSX2+
  at 5.37 MHz, "too fast VRAM accesses 1: cartridge 0 {}, BIOS 1 {05b3@3.491}". Every trace: 732
  frames, 0 differ, result 0. The code before `rs_one`'s fix lost 5 (the FS-A1FX) and 43
  (C-BIOS_MSX2+) in the cartridge, all at A8A5h and A8ADh (5.8).
- `ft_flow_job`, the power-on to the title's start with WELL DONE on the way: the FS-A1FX "too fast
  VRAM accesses 0: cartridge 0 {}, BIOS 0 {}"; C-BIOS_MSX2+ "too fast VRAM accesses 2: cartridge 0
  {}, BIOS 2 {05b0@3.491 05b3@3.491}"; both "AG 805Eh 1, passes 732". Step 8's candidate, before
  the fix, lost 8 and 55 in the cartridge.
- `ft_boot_job`: at 5.37 MHz "too fast VRAM accesses 2; the cartridge's init at 3.5286 s; BIOS
  hits: {pc 05b0 at 3.4907 s, sp f2e2: 065a f392 f040 247a} {pc 05b3 at 3.4909 s, ...}". C-BIOS's
  own code makes them, with C-BIOS's return address 065Ah on the stack, 0.04 s before the
  cartridge's init. At 3.58 MHz: 0 (the init at 3.7596 s). The FS-A1FX's own BIOS loses none at
  5.37 MHz.
- `ft_l1_job`: level 1 at 5.37 MHz loses 790 writes, all in the cartridge; the first 8 at
  6AA6h-6AD4h are `outi32`/`outi16`, the sprite engine's 18 T OUTIs. At 3.58 MHz: 0. Both traces:
  "1400 game frames compared ..., 948 fields: 0 differ". Level 1's code, which Brainstorm did not
  change: the user's call (`docs/BRAINSTORM.md` 8.16).

#### h. The candidates with the solved ending

`c8f_chain` is `c8_chain` (5.14) plus `solved_m2`: the bonus candidate on the Expert, solved by
`solve1`'s moves from the keyboard, with snapshots at passes 100, 300, 450, 600, 650 and 700, and
the intro's and the result's for screenshots.

```
msx_local_cmd: c8f_chain {CDIR} BASE {W/fresh} cand      (8 jobs; poll until done)
```

5.14's checks, then:

```sh
python3 -I tools/bstest/bonuscheck.py CDIR/run solved_m2 --tag N --result ok --gen W/cb/bonus/gen
python3 -I tools/bstest/stepcheck.py still CDIR/run/st_solved_m2/p*.bin
python3 -I tools/bstest/shots.py CDIR/shots CDIR/run/solved_m2_result.bin
```

Expected: "bonus check: PASS" (WELL DONE with TEST N, then the title, fire and the new game) and "6
snapshot(s), 0 with differences". The last line draws the WELL DONE screen.

### 5.18 The shooting range's display and its camera (steps 8 and 9 of its plan)

The second bonus stage (`msx/frng.asm`, its display `msx/frngview.asm`; the plan's 3.3 and 4.2 are
in the range chain's scratch notes until `docs/RANGE.md` lands) draws what the original draws in each
pass: the wanted state `rg_want` (EE00h, `range.inc`'s `RG_ST_` layout), taken whole when a build of
the page not on screen starts, so that each display page shows one pass. Each page's shown state is
kept in RAM with the pass it was taken at (`rgs0` EE40h, `rgs1` EE68h: `RG_ST_LEN` bytes, then the
pass, `$B00`, as a word). Every check compares what the VDP shows with `tools/msxrange.py`'s render
of that state (`Range.shown`: the page as built, its SAT, R#18), and that state with the one the
bench's trace gives for its pass.

The camera (`frng.asm` `rg_cam`, once a pass after the crosshair's move) keeps the crosshair's line
in the view's middle band: s = clamp(clamp(s, cx - 191, cx - 64), 0, 64), cx = `$B9A` - 111, from
s = 32 (`msxrange.py camera`). A page is built at the multiple of 16 c with c - s in -7..8 and shown
at s by its list's R#18 = (s - c) & 15 (level 1's sign); when s leaves the back page's window, that
page is built again whole while the page on screen holds. On a V9958 the HUD split's last write is
R#18 = 0 instead of R#27 = 0 while the stage runs (`split_list` + 8 = 92h, written by `rg_show`, 9Bh
again in `rg_hide` once a list with R#18 = 0 is on screen under the black palette). The `RG_ADJ=0`
build keeps R#18 at 0: s moves in steps of 16 only to keep cx - s in 5..240 (`camera_steps`). The
bench's drives never reach R#18's ends (the crosshair moves 4 pixels a pass from x 129, so s is 0,
32, 64 or 1-2 modulo 4): the camera jobs poke s (`rgv_poke_arm`, after the pass that makes `$B00` =
P, before that pass's builds) on the `hold` drive, whose crosshair never leaves the band.

```sh
sh tools/bstest/rgview.sh builds W          # W/fr2, W/fr2v2, W/fr2n, W/ext; prints the Tcl line
```
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_chain [rgv_suite {W}]   (81 jobs; poll)
```
```sh
sh tools/bstest/rgview.sh check W           # last line "rgview: PASS"; exit 0
```

`rgv_suite` (`rgview.tcl`) runs, each job on a new machine from the power-on through
`rc2_fr_drive` (the drive's trace into `W/O/tr/`):

- `armed`, `mixed`, `edge`, `timeout` and `armed2` (visit 2: the `fr2v2` build) on C-BIOS_MSX2
  (`_m2`), the Panasonic FS-A1FX (`_fx`, a V9958) and the FS-A1GT (`_tr`, the turbo R; the stage
  runs on its Z80), each with snapshots at chosen passes (`W/O/st/NAME/pNNNN.bin`, `hz7_snap`'s
  layout) and a record of every VBLANK from the first pass to 150 VBLANKs past the stage's end
  (`W/O/st/NAME/rec.bin`: 22,272 bytes a VBLANK, taken at `iv_late`, once the list is applied:
  the registers, the page R#2 shows, the SAT R#5 shows, `pf_pal`, the list, RAM C000h-C0FFh,
  C600h-C6FFh, D000h-D0FFh and EE00h-EFFFh), and the HUD's register probe;
- the camera: `hold7_*` and `hold8_*` (s poked to 7 and to 8 after pass 1: shifts -7 and +8, R#18
  07h and 08h) and `sweep_*` (s = k from pass 10 + 10k on, k = 0-64: every s, every shift, every
  c) on the three machines, with snapshots, records and the probe; the probe alone on `armed`,
  `hold7` and `hold8` on the Gradiente Expert 2.0 (`_ex`) and the Sony HB-F1XDJ (`_xd`, its 128K
  Lite set-up: the plain one needs a Kanji ROM the MCP's home lacks); the negative control `neg8_*`
  (`hold8` with `split_list` + 8 put back to 9Bh at the first pass) on the FS-A1FX, the HB-F1XDJ and
  the FS-A1GT;
- the `RG_ADJ=0` build (`fr2n`): `armed`, `mixed`, `edge` and `timeout` with snapshots and records
  on C-BIOS_MSX2 (`_m2n`) and the FS-A1GT (`_trn`);
- the display guard (`rc2_guard`, tears counted) over `armed`'s passes 5 to about 1,130 on the three
  machines (`guard_*`), and over the sweep's passes 5-655 on the HB-F1XDJ (`guard_sweep_xd`); the
  entry's uploads and builds and `rg_hide`'s SAT writes fall outside it by design (the palette black
  there);
- the VRAM speed over `armed` from the power-on to `fr_rated` at 3.58 MHz (C-BIOS_MSX2, FS-A1GT)
  and 5.37 MHz (FS-A1FX, C-BIOS_MSX2+): `fast_*`;
- the pass rate of `armed`, `mixed` and `edge` at 60 Hz (C-BIOS_MSX2) and 50 Hz (C-BIOS_MSX2_EU),
  `armed` on the FS-A1GT: `rate_*`, a line a pass (`tick`, the times at the loop's work, `fr_tick`,
  after `fr_frame` and after the pass's `rg_feed`, the active CPU);
- the other ten drives' traces on C-BIOS_MSX2 and the FS-A1GT, `opp` on the Gradiente Expert 2.0;
- the restore (`rgv_after_setup`): `timeout`'s stage (it times out at pass 301 with the palette lit),
  OUT OF TIME., the new game's frame 50 and six pictures (`W/O/flow/after_rg_*`), against
  `hz7_fresh_setup`'s fresh start of the `ext` build (`fresh_rg_*`), on C-BIOS_MSX2 and the
  FS-A1GT.

`rgview.sh check` gives one verdict for each:

- **the traces**: `tools/frngcmp.py` against `build/emu/fr_DRIVE_ram.jsonl` (the camera's jobs:
  `hold`'s; the guard's and the VRAM speed's: `armed`'s): 0 differ with equal results and ratings
  (the display does not change the logic);
- **the stills** (`rgview.py still ... --ref --gen`): the page the applied list shows (lines 0-161)
  equals the render of its shown state, index 1 (the sheets' black, which a front layer puts where
  the scene is 0) counting as 0; its set's SAT equals the state's; the colour rows of its sprites are
  all 15; the picture as shown (the sprites drawn from VRAM's patterns and colour rows, R#18's
  shift) equals the render's; the list's R#18 is (s - c) & 15; the view equals the converter's model
  of the Amiga's own composition (`compare`: 0 pixels, quirk 4's apart); the state is the bench's
  for its pass (pass 0: `rg_show`'s, nothing drawn), its c and s included (the camera from the
  bench's `$B9A`, the build's `RG_ADJ` from `gen/options.inc`, the job's pokes from its
  `campoke.txt`: `--campoke`); snapshots at s = 7 (R#18 07h) and s = 8 (08h) must be among them;
- **the records** (`rgview.py rec`): at every VBLANK showing a stage page, the page equals its
  state's render (no torn element), R#18 and the SAT are the state's (at most 31 entries, at most 3
  sprites on a line, every sprite whole in lines 0-157), no pixel outside both states' elements
  changes between two pictures shown in a row (compared in scene coordinates, screen x + s, over the
  page's 256 columns only: never the border R#18 uncovers), every picture's state is the bench's
  for its pass, and the crosshair's line is in the view. The cut: no list but a stage page's with
  its own R#18 while the palette is lit, the first other list after the stage's with the palette
  black, and on a V9958 `split_list` + 8 92h whenever a list has R#18 != 0 and 9Bh under every
  other lit list. VBLANKs with the SATs empty and the palette black are `rg_hide`'s (counted,
  accepted: `RG_ADJ=0` builds; the others show `fe_text`'s list by then);
- **the picture rates** (C-BIOS_MSX2, reported): pictures a second over the VBLANKs of the spans of
  passes whose camera moves (pans) and of those whose riser frame changes (every other pass: spans
  join gaps of 3 passes at most), and over the whole stage;
- **the probe** (`rgview.py probe`): at every split's end of the stage R#18 = 0, at every VBLANK the
  applied list's value; on each V9958 machine shifts -7 and +8 among the frames; the three negative
  controls report the shifted HUD (the check sees the fault it is for);
- **the guard**: reg, pal, cmd, cpu, vbl and tear 0 on all four runs;
- **the VRAM speed**: 0 lost writes in the cartridge (C-BIOS_MSX2+ loses 1 in its own BIOS, at
  05B3h, before the cartridge starts);
- **the pass rate** (`rgview.py rate`): no late pass (50 Hz: every step 1 VBLANK; 60 Hz: four 1s and
  a 2 in every 5, `fs_div`'s skip), the worst pass's T-states against a VBLANK's;
- **the restore** (`restorecheck.py ... --known --range`, then `tools/checkrun.py` with the venv's
  Python): after the stage page 2 equals `level1.vram`, page 3 lines 0-87 the intro's, both SATs
  start with Y = 216; at the new game's frame 50, page 2, the atlas, the HUD and the mirror equal a
  fresh start's, the sprite tables apart from the known items (`--range`: the colour rows of the
  line sprites 0-29, which the engine rewrites before use: cold.asm `spr_init`); the lost counters
  0; every checkrun picture 0 pixels differ and every sprite pixel exact (its "tile VRAM changed"
  item adds, after the range, page 3 lines 88-161: sheet S3, which `fb_init` freed, as `fe_text`
  runs it first and `engines_init` before any field use).

The run of 2026-10-27 (the commit after `3c3a735`): every verdict PASS.

- 45 traces 0 differ (`armed` 1,163 passes, `mixed` 1,869, `edge` 344, `timeout` 301, `armed2`
  1,163, the other ten as at step 7).
- 282 stills equal to the render; the records 0 torn, 0 SAT errors, 0 coherence errors, every
  state the bench's: `armed` 613 pictures in 1,158 passes on C-BIOS_MSX2 (606 FS-A1FX, 611
  FS-A1GT), `mixed` 1,163 in 1,868 (about 27 pictures a second).
- The guard: 1,348 frames, about 3,100 commands, all 0. VRAM speed 0 in the cartridge.
- The pass rate: 0 late passes; the worst pass 37,131 T-states at 60 Hz (a VBLANK: 59,659),
  38,603 at 50 Hz.
- The restore PASS; the HUD at `armed`'s 39 passes equal to step 7's build (`hudcheck.py
  W/O/st/armed_m2 REF/st/armed_m2`: a build of `3c3a735` in a worktree, the same `rgv_job`).

The run of 2026-10-27 with the camera (the commit after `26a2076`): every verdict PASS.

- 79 traces 0 differ, with equal results and ratings.
- 695 stills equal to the render, every R#18 value 00h-0Fh among them (30 at s = 7, 30 at s = 8, 3
  at s = 0, 63 at s = 64); the records 0 torn, 0 SAT errors, 0 coherence errors, every state the
  bench's at its camera, the crosshair's line always in the view; the sweeps show all 16 shifts;
  the cut: `timeout`'s last stage list has R#18 0Ah (s = 10, c = 16), the next list comes with the
  palette black, `split_list` + 8 9Bh again one VBLANK later (V9958).
- The probe: 33 runs, R#18 0 at every split's end (C-BIOS_MSX2, Expert, FS-A1FX, HB-F1XDJ,
  FS-A1GT; shifts -7 and +8 held 866-867 frames each); the negative controls report 866-867
  shifted HUD frames.
- Picture rates on C-BIOS_MSX2: pans 10-13 a second (`armed`, `mixed`, `timeout`), the riser 5-13
  (12.7 `armed`, 7.7 `mixed`, 5.0 over `timeout`'s 10 riser passes), the whole stage 20-29; 23-30
  pictures a drive at another c. (FS-A1FX: pans 11.0 and 10.5, the riser 15.9 and 10.2.)
- The guard: all 0 (1,348 frames of `armed` on three machines, 779 of the sweep on the HB-F1XDJ).
  VRAM speed 0 in the cartridge.
- The pass rate: 0 late passes; the worst pass 37,973 T-states at 60 Hz, 38,633 at 50 Hz.
- The restore PASS; the HUD at `armed`'s 39 passes equal to step 8's build.

### 5.19 The shooting range's milestone: the whole regression (step 10 of its plan)

`docs/RANGE.md` section 4 (the range chain's scratch notes until it lands) asks for every check of
the range, logic, display, camera and sound, and for every check of what existed before it (level
1, the title, `front_stats`, Brainstorm), against the base `4a8a61d`, the commit before the range.
`regress.sh` (shell) and `regress.tcl` (Tcl) run them all; `rgflow.tcl` holds the range's flows,
`frsound.tcl` its sound logs, `rgcheck.py` its text screens' check, `cmpcheck.py` the comparison of
Brainstorm's check logs, and `frsnd/` the sound's Python checkers (the venv's Python: numpy).

```sh
sh tools/bstest/regress.sh base B          # once a milestone: B/wt (4a8a61d), B/R; the product's SHA-256
```
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; rgr_base_chain {B} {B/base.done}   (41 jobs)
```
```sh
sh tools/bstest/regress.sh basecheck B     # B/check_all.log (Brainstorm's checks on the base)
sh tools/bstest/regress.sh builds W        # 21 builds through build.sh, W/drives; prints the Tcl line
```
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; rgr_chain {W} all {W/all.done}     (207 jobs)
```
```sh
until [ -f W/all.done ]; do sleep 20; done  # (or poll as in section 4); the file lists the messages
sh tools/bstest/regress.sh check W B       # every verdict, then "regress: PASS"; exit 0
```

One family at a time: `rgr_chain {W} FAMILY {W/FAMILY.done}`, then `regress.sh check W B FAMILY`
(several families may follow `check W B`). `hz_chain JOBS MARK` writes MARK when the chain ends,
done or stopped by an error: a shell waits for the file instead of polling the emulator.

**The base.** `regress.sh base B` adds a worktree of `4a8a61d` in `B/wt` (`git worktree add
--detach`), copies `build/ram` and `build/msx` into it (without ROMs, labels, pictures and `gen/`;
`build/extracted` is linked, read only), rebuilds the two conversions the range changed
(`msxhudrt.py`, `msxtext.py`) with the base's own tools, and builds `B/R` with the base's `hz.sh
builds`. The product must be `29d29e99e24731c8…`. On 2026-10-27 the six builds were byte-identical to
the range chain's step-0 base. `rgr_base_chain` records the base: `suite_flows` (the title from
power-on as `base`), the title after Brainstorm, exact, on the three machines (`B/O/np/tx_*`), and
`suite_drives`. The check reads `B/fresh/base_*`, `B/O/np/tx_*`, `B/O/flow/guard_*`,
`B/O/st/solve1_m2` and `B/check_all.log`. When the milestone is over: `git worktree remove --force
B/wt`.

**The builds** (`regress.sh builds W`): `W/R` (`hz.sh builds`: prod, pzt, pz1, pz2, trace, ext);
`W/X`: `fr2` (`EXTJOY=1 PZ_TEST=2`), `fr2t` (+ `ENEMY_CAP=0 DAMAGE_X=1`), `fr2tag` (+ `TAG=4`), `ext`
(`EXTJOY=1`), `pzt2` (`PZ_TEST=2`), `p2m` (`ROM_2M=1`), `cand` (`PZ_TEST=1 TAG=4`, the candidates'
options); `W/V` (`rgview.sh builds`); `W/S`: `fr2`, `fr2_noscc` (+ `NO_SCC=1`), `fr2_nosccint`
(+ `NO_SCC_INT=1`), `fr2_psg` (+ `NO_SCC=1 NO_FM=1`), `pz2`, `pz2_noscc`; `W/drives`: the poke
drives (`rg_cC_dD_mM.drive`: the counts and the ammo poked at pass 5; `rg_time.drive`: `$804C` =
FFh; `rg_none.drive`). About 8 s in all.

**The families** (`rgr_jobs`) and what `check` says of each:

| Family | Jobs | Verdicts |
|---|---|---|
| `flows` (21) | `suite_flows` (as `new`); `tx_ex`, `tx_f1`, `tx_tr` (`np_title_setup` EXACT 1); `wp_tr`; `p2m_ex` (the 2 MiB product, `hz6_prod_setup`); `kb_ex`, `kb_tr` (`rgk_job`) | level 1's coverage traces 0 differ; the title from power-on identical to the base's; `bonuscheck.py --range time` on `prod_*` and `pzt_*` (Brainstorm's screens, then the range's intro and OUT OF TIME. after its real 2:00, the rating 24 at `fr_rated`, SHARP and lost 0 at the new game); the restore; the turbo R's blank (reported); 0 writes to 4000h-7FFFh; the title after the flows against the base's (`titlecmp.py`, `titlecmp2.py --unheard`); the 2 MiB product through both stages; the keyboard flows (below) |
| `final` (7) | `solved_m2`, `solved_tr` (`pz1`), `solved_cand_ex` (`cand`, the moves from the keyboard), `fire_ex`, `two_m2`, `two_title_ex` (`cand`), `ftflow_fx` (`cand` at 5.37 MHz) | 5.17's verdicts, every one through the range (`--range time`): the script builds time it out at its first pass, the candidate plays its real 2:00; `ftflow_fx` 0 VRAM writes lost in the cartridge from the power-on through Brainstorm and the range's 6,050 passes to the title |
| `drives` (25) | `suite_drives` | `check_all.sh`, then `cmpcheck.py` against the base's log (a torn cell accepted only under a black palette); the guard and the VRAM speed; the HUD during Brainstorm against the base's snapshots |
| `range` (54) | `rgx_job` / `rgx_arm_job` for 5 poked results and the time out on C-BIOS_MSX2, the FS-A1FX and the FS-A1GT (36); TAG=4 (2); level 1 traced after the range (3); the real timer (3, `pzt2` on the Expert, C-BIOS_MSX2_EU, the FS-A1GT); `tarm_m2`, `tarm_tr` (`rgx_tarm_job`); `want_*` (8 drives) | `rgcheck.py` on 41 records; the real timer's time out at 6,050 passes; level 1's traces after the range 0 differ; `tools/frngcmp.py --skip score` of `fr_mixed` after a played level 1 and Brainstorm; `rgview.py want` on 8 drives and their traces |
| `display` (81) | `rgv_suite W/V` | `rgview.sh check W/V` (5.18) |
| `sound` (20) | `frs_suite W` | `frsnd/frregcmp.py` on the 20 register logs (FRM's registers per tick against `frm.bin`'s streams, the modes, tick 0 after the first pass, the refusals, the tune's end and the silence, the stage's own stop at most one tick after its last pass (the Q line: `msx/frng.asm` `rg_end`), no tick after it, the result's stop); the 15 drives' traces 0 differ |

**The range inside Brainstorm's flows.** Brainstorm's flow checks expected the title right after its
result; the range now comes in between (`front_range`). `hz.tcl hb_step`, after Brainstorm's result,
calls `rgflow.tcl rgh_arm`: in a build with the range (`fr_tick` in its labels) whose job does not
drive the range itself (`::hb_range`, set to 1 by `hb_init_range` in every set-up that runs
`hb_step`; `rgx_arm_setup` and `rgk_setup` set 0), it records the range's intro and its result or
OUT OF TIME. into the flow's own `DIR/TAG` (`TAG_rgintro.sc5`, `TAG_rgres.sc5`, `TAG_rg.txt`: the
result at `fr_done`, the rating at `fr_rated`, then `hb_step`'s new game with `ac_diff` and the lost
counters), then `hb_step` goes on to the title or the new game as before (its state 7). A build with
a script (`INPUT_SCRIPT` 1: `EXTJOY` or `JOY`), whose timer stands still, gets `rc2_fr_timeout`
(OUT OF TIME. at the range's first pass); the others play its real 2:00. `hz7_after_setup` (the
restore jobs) and `np.tcl np_2_w1` (the first of two stages) arm `rc2_fr_timeout` through
`rgx_timeout_if`; `ft_flow_job` allows 600 s. A build without the range takes the old path, so the
base's records are made by the same code. `bonuscheck.py --range time|C,D,M` checks the range's
records (`rgcheck.check`), and `--no-game` drops Brainstorm's own new-game line (the keyboard flow
ends at the title's game, which the range's notes give).

**The product from the keyboard** (`rgk_job`, docs/RANGE.md 4.4's fresh-machine run as far as the
harness allows; a new machine from the power-on, the product's own input, never `ext_joy`): the
title, SPACE, a new game; level 1 ended by `drive_end.txt`'s teleport and poke (pokes, as in every
product flow: no keyboard drive of level 1 exists); the statistics; Brainstorm played from keymatrix
row 8 with `pz_solve1.drive`'s moves (`np_keys_arm`), traced by `rc2_pz_arm`; the range played from
row 8 with `fr_armed.drive`'s moves (`rgk_keys_arm`: at each `fr_tick` the byte of FRNG frame `$B00`;
fire is SPACE), traced by `rc2_fr_arm`; its result (25 correct, 0 dummy, the timer at 1:37: SHARP);
the title, recorded exactly (`np_hf_step`) to its game at tick 300. The checks: `tools/puzlcmp.py
--skip joy,last_joy,timer_min,timer_sec,score` (394 fields) and `tools/frngcmp.py --skip
joy,timer_min,timer_sec,score` (139 fields; the keyboard sets the joystick byte's bit 7, the product's
timers count real seconds, the score carries level 1's): 0 differ; `bonuscheck.py --result ok
--no-game --range 25,0,1`; the title against the base's title after Brainstorm: picture, registers and
palette identical, `titlecmp2.py --unheard` PASS with every PSG write identical. The SCC's fourth
channel (its waveform 60h-9Fh in the debuggable, its period A6h-A7h and the mirror B6h-B7h) differs at
every title tick and is never heard: the range's effects play on that channel and the title never
writes it (docs/RANGE.md 4.3: "only unheard registers differing").

**Polling.** With throttle off the emulator runs 20 to 130 times faster than real time, so half a
real second is a minute of the game or more. Poll a running machine's condition with `after time`
(emulated); keep `after realtime` for the points where a trace paused the machine (`rc2_trace_done`).
The first keyboard flow polled `hb_st` in real time and armed the range's keys 80 emulated seconds
late: the range timed out with no shot (`rgk_tp` polls in emulated time).

**The run of 2026-10-27** (branch `range` at `43569f6` plus the moved harness; `W` =
`impl/s10/W`): 207 jobs in about 7 minutes, no time out, then `regress.sh check W B` for every
family: **regress: PASS**.

- flows: level 1's traces 0 differ (4,401 / 1,400 / 1,400 rows); the title from power-on identical
  to the base (5,046 music ticks); the product's and PZ_TEST=1 flows 4,075 / 4,078 VBLANKs and HUD
  splits in Brainstorm, then the range's intro and OUT OF TIME. equal to the renders, 7,629 VBLANKs
  and splits between them, the rating 24, SHARP and lost 0 at the new game, on the Expert and the
  FS-A1GT; the restore PASS (m2, tr); the turbo R's blank 6 frames as at the base; 0 writes to
  4000h-7FFFh from `front_bonus` (43.3 s) to the new game's tick 100 (255.8 s); the title after the
  flows identical to the base's on the Expert, the HB-F1XDJ and the FS-A1GT (5,044-5,045 ticks: 0 SCC,
  PSG register and PSG write differences); the 2 MiB product PASS; the keyboard flows PASS on the
  Expert and the FS-A1GT.
- final: `solved_m2`, `solved_tr`, `solved_cand_ex` (732 passes, 399 / 395 fields), `fire_ex` (both
  partial screens exact, the title 131 s after the press: the range's 2:00 between), `two_m2` and
  `two_title_ex` (182 and 732 passes), every range record PASS; `ftflow_fx`: 0 lost in the cartridge.
- drives: Brainstorm's 20 traces 0 differ, stills 0, records 0 outside, 0 cursor errors, the one
  known torn cell under a black palette (`solve1_tr` record 407: a board's set-up; the base has one
  in `solve1_tr` too); guard reg/pal/cpu/vbl 0 (cmd 171/165/175 and tear 31/29/32 on C-BIOS_MSX2,
  the FS-A1FX and the FS-A1GT, all at the set-ups), VRAM speed 0; the HUD equal to the base's.
- range: 41 screen records PASS; the real timer 6,050 passes on the three machines; level 1 after the
  range 0 differ; `tarm_m2`, `tarm_tr` 1,869 passes, 142 fields 0 differ, result (8, 17, 0), SHARP;
  the wanted state 0 differ at every pass of `armed` (1,162 passes: 1,382 pop-ups, 788 big targets,
  353 dissolves, 200 boxes), `mixed`, `dummy`, `edge`, `fuzz`, `quirk4`, `hold`, `armed2`.
- display: `rgview: PASS` (79 traces, 695 stills, every R#18 00h-0Fh; records 0 torn, 0 SAT and 0
  coherence errors; the probe and its 3 negative controls; the guard; VRAM speed; 0 late passes; the
  restore), as at the sound's step.
- sound: the 20 logs 0 differences (1,880-1,881 ticks of the drive, 5,999 of the stages left alone;
  modes 1, 5, 6, 0 as the set-up gives; tick 0 after the first pass; 39 effects started, 9-10
  refused; the tune's end then silence; the stop); the 15 drives' traces 0 differ.

Outside the chain, the same day: `tools/msxmatrix.py` 10 of 10 PASS on the product (its lines equal
the base product's), the 2 MiB product, and with `--no-title` the PZ_TEST=1 and PZ_TEST=2 builds (the
range's 50 passes a second: `tick_n` +350 in 7 s); its two negative cases FAIL as they must (the
product with `--no-title`, the PZ_TEST=2 build without it). `variants.sh`: the same 38 of 41 sets
build as at the base (`DEMO_ACTORS=2/5` and `DEMO_HUD=1` overflow the fixed area at both, now by 2
bytes more: `fr_done`, `fr_rated`). `make test`: the 4 known failures only.

**Negative controls** (on copies of the records; each gate must fail):

| Gate | Known-bad input | Result |
|---|---|---|
| `bonuscheck.py --range` | one byte of `prod_m2`'s OUT OF TIME. record inverted | FAIL: 1 byte DIFFER, line 60 |
| `bonuscheck.py --range` | the base's product flow (no range records) | FAIL: no record |
| `bonuscheck.py --range 24,0,1` | the keyboard flow's result (25 correct) | FAIL: 26 bytes DIFFER, lines 91-98 |
| `rgcheck.py` | `lost: mp 1` in the notes; the new game's `ac_diff - diff_tab 24` | FAIL: lost counters not 0; not SHARP |
| `frngcmp.py` (keyboard flow) | no skip list | FAIL: 1,163 passes differ (the score) |
| `titlecmp2.py` (keyboard flow) | without `--unheard`; one PSG write's hash changed with it | FAIL; FAIL (`PSG writes: 1`) |
| `rgview.py want` | step 7's log (before the camera: s 32 throughout); one pop-up's X + 1 | FAIL: 1,144 differ; 1 differ (pass 2) |
| `frngcmp.py --skip score` (`tarm`) | `fr_armed`'s reference instead of `fr_mixed`'s | FAIL: 1,096 differ |
| `cmpcheck.py` | one trace's "0 differ" made "3 differ" in a copy of the check log | FAIL |
| `frsnd/frregcmp.py` | channel A's volume changed at one T line of `d_scc` | FAIL: 1 difference |
| `rgview.py probe` | `neg8_*` (5.18) | the shifted HUD reported |
| `tools/msxmatrix.py` | the product with `--no-title`; `pzt2` without it | FAIL; FAIL |

The scratch script that ran them is in the step's notes (impl/s10/neg.sh); `tests/test_bstest.py
test_bonuscheck_range_command_line` keeps four of them as a unit test.

**Not in the chain**: the recordings judged by pitch (`frs_suite W 1`, then `frsnd/frwavcmp.py` and
`frsnd/fxalone.py` against the converter's previews, `tools/msxtune.py --frm --wav DIR`: the sound's
step ran them; they need the ear's judgment more than a gate's), the Z80 interpreter's offline runs
(`frsnd/frsim.py ROOT ROM LABELS`), `hz6_time`, `hzp_setup`, `ft_job` / `ft_boot_job` / `ft_l1_job`
and the candidates' `c8f_chain` (5.17 g, h: with the candidates of a delivery).

## 6. The whole suite in order

1. `sh tools/bstest/regress.sh builds W`; once a milestone the base: `regress.sh base B`, its
   records (`rgr_base_chain {B} {B/base.done}` in the MCP's openMSX), `regress.sh basecheck B`.
2. `msx_local_boot`; `source {<repo>/tools/bstest/load.tcl}`.
3. `rgr_chain {W} all {W/all.done}`: every emulator check of 5.2-5.10, 5.12's blank, 5.17 a-g's
   flows, 5.18 and 5.19 (207 jobs; about 7 minutes on 2026-10-27). Wait for `W/all.done`.
4. `sh tools/bstest/regress.sh check W B`: every verdict, "regress: PASS".
5. `msx_local_shutdown`; the matrix (5.13) on `W/R/prod`, `W/X/p2m` and, with `--no-title`, `W/R/pzt`
   and `W/X/pzt2`; `sh tools/bstest/variants.sh` (5.15) against the base's; `make test`.
6. The checks the chain does not run: `hz6_time` (5.11), `hzp_setup` (5.12's PAUSE), `hudcheck.py`
   against the commit before a change (5.6), 5.17 g's other speed jobs, `c8f_chain` for test
   candidates (5.17 h), the range's recordings (5.19).

One family: `rgr_chain {W} FAMILY {W/FAMILY.done}` with FAMILY `flows`, `final`, `drives`, `range`,
`display` or `sound`, then `sh tools/bstest/regress.sh check W B FAMILY`. The older entry points
still work alone: `hz_chain [suite_drives {W/R} {W/O}]` and `check_all.sh` (5.4-5.8),
`hz_chain [suite_flows {W/R} {W/O} {W/fresh} TAG]` (5.9-5.10), `hz_chain [rgv_suite {W}]` and
`rgview.sh check W` (5.18).

## 7. For the next milestones

- **Sound (milestone 2).**
  - The title's music must stay register-exact: 5.3's `music.txt` and `psg.txt` cover it.
  - So must the title that follows the stage: 5.17 b against the base build, where the stage's
    sound may leave values only in registers nobody hears (`titlecmp2.py --unheard`), and every
    PSG write must stay identical.
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
breakpoints in banked code, `rc2_guard`, `rc2_count_too_fast` (5.8: it did not count then; it
counts since `b59a338`, and the final checks saw it move), `turborpause` (`hzp_*`),
the timings `hzb_*` measures, `hz6_*`, `hz7_after_setup` / `hz7_fresh_setup`, `c8_step`'s
snapshots, and `suite_drives`, `suite_flows` and `c8_chain` end to end. These are the night's
procs with the changes of section 8 only; their first real run is the next milestone's suite.
`variants.sh` ran only against the stub; `build.sh` ran with the real `mkrom.py`.

## 10. When the final checks' scripts moved

The final checks' scripts (5.17) were in the night's scratch folder (`impl/final`: `np.tcl`,
`ft.tcl`, `cand/run8f.tcl`, `titlecmp.py`, `titlecmp2.py`, `partialcheck.py`). They moved to
`tools/bstest/` with their checks kept. These are the only changes:

- **Paths.** None from the scratch folder remains.
  - The Tcl reads the repository's drives through `::hz_root`, and `partialcheck.py` finds the
    repository from its own place.
  - `run8f.tcl`'s `c8f_chain` takes the candidates' folder, their base name, the title
    references' folder and a tag, as `c8_chain` does. It builds on `c8_jobs`: `c8_chain`'s job
    list, split out of `c8_chain`, which runs it as before.
- **New.**
  - `np_job`. `np_title_setup` and `np_title0_setup` take EXACT as an argument (the night set
    `::np_exact 1`); `np_solved_setup`'s KEYS defaults to 0.
  - `titlecmp2.py` names every register that differs, with the ticks it differs at and those where
    it can be heard; it prints the game's VRAM count and the HUD's share, ends with a verdict line,
    and has `--unheard`. Without `--unheard` its verdict is the night's: exit 0 only when the music
    is identical at every compared tick.
  - `titlecmp.py` leaves out the parts whose files a record lacks (the night's copy stopped at an
    exact record's missing `music.txt`) and reads a music log without an SCC column.
  - `partialcheck.py` exits 2 on an unknown label.
  - The setups of `ft.tcl`'s jobs (`ft_setup`, `ft_flow_setup`, `ft_boot_setup`, `ft_l1_setup`)
    and `c8f_solved_setup` are procs instead of scripts in strings, so a path needs no quoting.
    Their commands and their order are the night's; `ft_clock` sets the clock.
- **Safety.**
  - Every note and record writer closes its file when a write fails. `np_keys_arm` and
    `np_shift_drive` close the files they read on every path.
  - `np_keys_arm` lets go of a key an earlier arm left held and removes that arm's breakpoints
    (`np_keys_disarm`).
  - `np_job`, `np_wp_job`, `np_title_setup` and `np_title0_setup` create the output folder.
- `load.tcl` sources `np.tcl`, `ft.tcl` and `run8f.tcl` after the others.

**Checked without an emulator.** No openMSX was run.

- On the night's records, before the scratch folder was cleared:
  - `titlecmp.py` printed its night copy's output line for line on the three machines' first
    records (`t0_*` against `title_*`);
  - `partialcheck.py` printed the night's lines on the four fire snapshots (exit 0);
  - `titlecmp2.py` printed the night's music line and game lines on the three exact pairs, with
    the night's exit status: 0 on the Expert, 1 on the HB-F1XDJ and the FS-A1GT. It named A6h,
    A7h, B6h and B7h (and R6 on the FS-A1GT) "heard at 0", and with `--unheard` all three pass;
  - the harness's other tools gave 5.17's numbers: `puzlcmp.py` on 20 of the traces (a's three,
    e's ten, g's five after the fix and two before it), `bonuscheck.py` on the flows of a, c, e, f
    and h (PASS, but `two_tr`'s one item), `stepcheck.py still` on the fire and solved snapshots
    (7 and 6, 0 with differences), `tracecmp.py` on g's two level-1 traces (0 differ).
- `tests/test_bstest.py`, 33 tests (10 new):
  - every Python tool compiles and imports;
  - `titlecmp2.py`'s verdicts on made-up records: identical records; the window's edges left out;
    a silent SCC channel's registers, and the PSG's tone, noise and envelope registers, passed by
    `--unheard` only where nobody hears them; the mixer, the enable bits and the PSG writes always
    counted; the game reported, not judged; a missing file;
  - `titlecmp.py`'s parts on made-up records; `partialcheck.py`'s offsets against
    `msxtext.fs_run`, and its command line on a made-up snapshot (with
    `build/ram/level1_full.bin`);
  - every Tcl file complete, with no `exit`, `vwait`, `max` or `min`;
  - in tclsh with openMSX mocked and `::hz_root` on a folder of made-up drives: the keyboard
    drive's keys, the shifted drive, `np_job`, each flow of 5.17 a, b, d, e and f driven through
    its states, both exact title records read back by `titlecmp.py` and `titlecmp2.py`, the four
    speed jobs' setups (the clock unlocked) and files, `c8f_chain`'s eight jobs and its refusal of
    a missing file, and no channel left open;
  - three mutations each failed a test: `np_keys_end` not letting go, `ft_clock` not unlocking,
    `--unheard` passing R6 with the noise on.
- `make test`: 119 tests, the 4 known failures only (5.16).

**Not tested without an emulator.** The moved Tcl against a real openMSX. The night's copies ran
(`docs/BRAINSTORM.md` 4.6); the moved procs differ from them only as listed above.

## 11. When the range's harness moved (its step 10)

The range chain's agents wrote their checks in the session's scratch folder; step 10 moved them
here so that the repository alone reruns every gate:

- `impl/harness/regress.sh`, `regress.tcl`, `rgflow.tcl`, `rgcheck.py`, `cmpcheck.py` became
  `regress.sh`, `regress.tcl`, `rgflow.tcl`, `rgcheck.py`, `cmpcheck.py`: paths from the scripts'
  own place; the base's folder an argument (`check W B`), and its recipe a command (`base B`,
  `basecheck B`, `rgr_base_chain`); every family in one chain, with the display (`rgv_suite`) and
  the sound (`frs_suite`) added; `rgx_flows`' wrapper dropped (`hz7_after_setup` arms the time out
  itself); `rgcheck.py` importable (`check()`), with the lost counters checked.
- Step 7's scripts: `s7_arm_job` became `rgx_tarm_job`, `s7_want_job` `rgx_want_job`, `wantcheck.py`
  `rgview.py want` (on `rgview.py Bench`, with the camera: the old check expected s = 32); `s7_all`,
  `cmp.sh`, `s7_rate_job` and `rate.py` were already `rgview.tcl`'s `rgv_tjob`, `rgview.sh check`'s
  trace verdict, `rgv_rate_job` and `rgview.py rate`; the option-set scripts (`b3.sh`, `bset.sh`,
  `b8.sh`, `b9.sh`, `b11.sh`) are `regress.sh builds` and `variants.sh`.
- Steps 8 and 9's still and record checks were in the repository already (`rgview.*`, 5.18).
- The sound's step: `frs.tcl` became `frsound.tcl` (+ `frs_suite`); `py/frsim.py`, `frregcmp.py`,
  `frwavcmp.py`, `fxalone.py` and the Brainstorm night's `z80.py`, `pzsim.py`, `int_wavcmp.py` are in
  `frsnd/`, unchanged but for their import path.
- New: `hb_step`'s range part (`rgh_arm`), `rgk_job`, `hz_chain`'s MARK file, `bonuscheck.py --range`
  and `--no-game`, `rgview.py want`.

