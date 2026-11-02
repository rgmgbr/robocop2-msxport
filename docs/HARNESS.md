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
| `build.sh OUT.rom [NAME=VALUE ...]` | shell | `tools/mkrom.py` into `OUT.rom`, then checks: mkrom's exit status, no "error" in `OUT.log`, a ROM written by this build, and no z80asm message in `OUT.labels` other than the 12 known "expression fully enclosed in parenthesis" warnings. `LEVEL=` another conversion; `SRC=` another source tree (5.3); `KNOWN_WARNINGS=` another count. Refuses `build/msx`, also the folder it resolves to (a tree whose `build/` or `build/msx` links to another checkout's), and any OUT not ending in `.rom`/`.ROM` |
| `hz.sh` | shell | `trace DIR` (the regression's build), `compare DIR [LABELS]` (the regression's verdict), `product DIR` (a product build), `fresh DIR A B` (two title records), `builds R` (the suite's six builds); level 2 (5.22): `l2builds R` (its six trace builds), `compare --fields FIELDS DIR R [--refs REFS] [JOB[:ROWS] ...]` (its drives' traces) |
| `load.tcl` | Tcl | sources the Tcl files below in order (`hz.tcl` first) |
| `hz.tcl` | Tcl | `hz_chain` (the job runner), `hz_regress`, `hz_fresh`, `hz_bonus`; level 2 (5.22): `hz_l2` / `hz_l2_jobs` (its 20 drive jobs), `hz_l2_still_jobs` (its start on the three machines) |
| `hz6.tcl` | Tcl | `hz6_arm` (the stage after a played level 1), `hz6_prod` (the product's whole flow), `hz6_time` (the real timer) |
| `hz7.tcl` | Tcl | `hz7_snap`, `hz7_arm` (snapshots at passes, a record at every VBLANK), `hz7_job`, `hz7_guard_arm`, `hz7_after_setup` / `hz7_fresh_setup` (the restore) |
| `fixchk.tcl` | Tcl | `hzp_setup` (the turbo R's PAUSE), `hzb_setup` (the turbo R's HUD blank), `hzg_job` (the display guard), `hzf_job` (VRAM access speed) |
| `suite.tcl` | Tcl | `suite_drives R O` (25 jobs), `suite_flows R O FDIR FTAG` (13 jobs): the acceptance suite |
| `c8.tcl`, `run8.tcl` | Tcl | `c8_job` (a PZ_TEST ROM from power-on, cursor keys from the keyboard), `c8_chain` (the test candidates; `c8_jobs`: its job list) |
| `np.tcl` | Tcl | the final checks' flows (5.17): `np_job`, `np_keys_arm` (a drive's moves from the keyboard), `np_solved_setup`, `np_title_setup` / `np_title0_setup` (the title's exact record), `np_fire_setup`, `np_two_setup` / `np_two_title_setup`, `np_wp_job` |
| `ft.tcl` | Tcl | VRAM writes lost at another Z80 clock (5.17 g): `ft_job`, `ft_flow_job`, `ft_boot_job`, `ft_l1_job` |
| `run8f.tcl` | Tcl | `c8f_chain`: `c8_chain`'s jobs and the solved ending from the keyboard (5.17 h) |
| `check_all.sh OUT TAG...` | shell | for every drive job: `tools/puzlcmp.py`, `stepcheck.py still`, `stepcheck.py rec` (`solve2` and `fuzz2` with `--visit 2`) |
| `stepcheck.py still` / `rec` | python | the stage's pictures against `tools/msxpuzl.py`'s render (5.5); `--visit 2`: visit 2's (Ellen's pictures and cursor colours; a snapshot's AG `$8050` must be 2 or more) |
| `bonuscheck.py DIR TAG` | python | the bonus text screens against `tools/msxtext.py`'s render, the HUD split at every VBLANK, the title, the new game (5.9); `--range time\|C,D,M`: the range's screens recorded in the same flow (5.19); `--no-game`; `--brief l2\|l3`: the next level's briefing after the range, `--level2`: level 2 after it instead of a new game (level 2's step 18, 5.22), its first picture checked (`first_picture`: `tools/msxframe.py ... --field --no-sprites` exits 0, the notes' HUD record holds the game's values; step 22) |
| `restorecheck.py DIR AFTER FRESH [--known]` | python | what the stage leaves: page 2, the atlas, the SATs; the next game against a fresh start (5.10) |
| `hudcheck.py NEW_DIR REF_DIR` | python | the HUD during the stage against a reference build's at the same passes (5.6) |
| `shots.py OUT SNAP...` | python | whole-screen PNGs of snapshots (play area, blank lines, HUD; 2x) |
| `fixblank.py FILE` | python | the HUD's blank at the turbo R's CPU switch (5.12) |
| `frozen.py SNAP OUT.png` | python | what the VDP shows while the CPU is held (5.12) |
| `romdiff.py [--blocks] A B [--allow NAME,...]` | python | the 8 KiB banks that differ; `--blocks`: each block of `gen/banks.inc` at its own bank in each image (5.15) |
| `relocheck.py OLD NEW OLD.labels NEW.labels BANK...` | python | a code bank's differences are only relocated label words and one-byte operands of changed names (`NAME + k`: bank numbers); `OLD:NEW` or a name for a code bank that moved (5.15) |
| `variants.sh OUT` | shell | the night review's 41 option sets, level 2's 7 `LV_TEST=2` sets, the candidates' 5 `CHEAT=1` sets and 2 `VAT_ANIM=1 VAT_TICK=1` sets (55), built (5.15, 5.22, 5.24) |
| `titlecmp.py DIR A B` | python | two title records taken apart: the picture as the VDP shows it, the VRAM it does not show, the registers, the palette; an `hz_fresh` record's music, PSG writes and game too (5.17 b) |
| `titlecmp2.py DIR A B [--unheard]` | python | two exact title records: the music per music tick (the SCC's and PSG's registers, named; the PSG writes), the game at its tick 300 (5.17 b) |
| `partialcheck.py SNAP LABEL [--tag N]` | python | a text screen cut short by fire against the render of its script as far as it got (5.17 d) |
| `rgview.tcl` | Tcl | the shooting range's display checks (5.18): `rgv_job` (snapshots at passes, a record at every VBLANK, the camera's pokes, the HUD's register probe), `rgv_tjob` (a trace), `rgv_guard_job`, `rgv_fast_job`, `rgv_rate_job`, `rgv_after_setup` (the restore), `rgv_suite W` (all 81 jobs) |
| `rgview.py still` / `rec` / `rate` / `probe` / `want` | python | the range's pictures against `tools/msxrange.py`'s render and the bench's states at the camera; the cut; the picture rates; the pass rate; the register probe (5.18); the wanted state at every pass (5.19) |
| `rgview.sh builds W` / `check W` | shell | the range's four test builds; every verdict of 5.18, then "rgview: PASS" |
| `regress.sh base B` / `basecheck B` / `builds W` / `check W B [FAMILY ...]` / `cand W B NAME CB` | shell | the range milestone's whole regression (5.19): the base cb7c9ef rebuilt from a worktree, the builds, every verdict against the base, then "regress: PASS"; `cand`: the range's test candidates' verdicts (5.20) |
| `regress.tcl` | Tcl | `rgr_chain W ?FAMILY? ?MARK?` (flows, final, drives, range, display, sound; 208 jobs with all), `rgr_jobs`, `rgr_base_chain B` (the base's records) |
| `rgflow.tcl` | Tcl | the range's flows (5.19): `rgx_job` (PZ_TEST=2), `rgx_arm_job` (after level 1 and Brainstorm), `rgx_tarm_job` (the range traced there), `rgx_want_job` (the wanted state), `rgk_job` (the product from the keyboard), `rgh_arm` (the range's screens inside Brainstorm's flows), `rgx_timeout_if`; `rgc_job` and `rgc_chain` (the range's test candidates from the keyboard, 5.20) |
| `frsound.tcl` | Tcl | the range's sound logs (5.19): `frs_drive`, `frs_alone`, `frs_suite W ?REC?` |
| `contcheck.py DIR TAG (--fire \| --again \| --no-fire \| --none) [--tag N] [--gen GEN]` | python | level 2's continue (its step 19, 5.22): the offer's screen against `tools/msxtext.py`'s render of `txt_cont`, R#0/R#1, the HUD split, its length, the continue or the new game, AG `$805E`; with the continue the map patches, attribute RAM, level's lists, vat state and tile cache equal before PIC9 and at `lv_cont`'s entry, and level 2's first picture after it checked as `bonuscheck.py --level2`'s (step 22) |
| `rgcheck.py DIR TAG (--counts C,D,M \| --time) [--tag N] [--no-game] [--level2 \| --new-game]` | python | the range's text screens against `tools/msxtext.py`'s render, the HUD split, the result at `fr_done`, the rating at `fr_rated`, SHARP and the lost counters at the new game, or (the product's flow since level 2's step 18) level 2 with the range's rating kept (5.19, 5.22); `bonuscheck.py --range` calls it |
| `cmpcheck.py BASE.log NEW.log [OUT]` | python | two `check_all.sh` logs job by job; a torn cell accepted only under a black palette (5.19) |
| `frsnd/frregcmp.py ROOT LOG...` | python (venv) | FRM's registers per tick in an `frsound.tcl` log against `frm.bin`'s streams decoded apart; `--selftest` (5.19) |
| `frsnd/frsim.py ROOT ROM LABELS` | python (venv) | the range's sound on a ROM image in a Z80 interpreter (`frsnd/z80.py`, `frsnd/pzsim.py`: Brainstorm's), offline (5.19) |
| `frsnd/frwavcmp.py`, `frsnd/fxalone.py` | python (venv) | recordings judged by pitch against the converter's previews (`frsnd/int_wavcmp.py`'s measures; 5.19) |
| `l2base.sh builds W` / `check W BASE [RB]` / `base W` | shell | level 2's base and the comparison of any later build against it (5.21): `regress.sh`'s builds, the `LOCKSTEP=24` builds and the code banks' free bytes; every verdict of `regress.sh check` and of level 1's records below, then "l2base: PASS" |
| `l2base.tcl` | Tcl | `l2b_chain W ?MARK?` (`rgr_jobs W all` and `l2b_jobs W`: 227 jobs), `l2b_jobs W` (level 1's death-and-restart and end traces, the start check, the field records, the stills, the `LOCKSTEP` records, the effects: 19 jobs; the PSG-write jobs also log the effects by their starts, `l2b_sn_arm`) (5.21) |
| `l2base.py banks` / `start` / `field` / `stills` / `tears` / `fresh` / `ram` | python | the code banks' free bytes (`msx/rc2.asm`'s padded windows) and the product's bank map; the verdicts of 5.21 against the base's; the field check's known hostage tear (`TEARS`, `tears` derives it); the exact title from power-on and the game's RAM by variable (5.21, the gate's timing-blind verdicts) |
| `fieldcheck.py RECDIR LEVEL_PREFIX OUT.png [--level 2]` | python (venv) | every play-area pixel no sprite covers against the tiles (map and patches) and the play-field BOBs of the list on screen (level 1's scratch tool of 2026-10-21, 5.21); a `CLASS` line per kind of difference in a picture (the hostage tear with its BOBs, a torn explosion, other); `--level 2`: level 2's frames as its ROM uploads them (`tools/msxframe.py` `FieldLooks`) and its hostage-like BOBs torn per object (5.22, step 13) |
| `fxcmp.py BASE_sn.txt NEW_sn.txt`, `--starts A B` | python | the effects of two builds by their starts: the same starts in the same order and `LOCKSTEP` frames, each effect's own sound from its start (5.21, the gate's timing-blind verdicts) |
| `sess_fxlog.tcl` | Tcl | the in-game effects per tick: every `fx_start`, and at every `fx_tick` the SCC's channels and the PSG's registers (level 1's scratch tool of 2026-10-22, 5.21); sourced with its `::fl_*` set, not by `load.tcl` |
| `fxlog.tcl` | Tcl | every PSG (R0-R13), SCC (9800h-98FFh, where it went) and OPLL write with the sound engine's events: requests queued and taken, ticks, stops, text screens, the stages' tune ticks; `fxl_jobs W/fx R` (26 jobs: level 2's drives on three chip sets, the continue, the briefings, both stages' visits), `fxl_drive_job`, `fxl_text_job` (5.23) |
| `fxcheck.py check LOG ROM LABELS [--bench REF] [--expect K]`, `visits A B`, `selftest LOG ROM LABELS` | python | the sound engine's model (`sndplay.asm`, `music.asm`'s in-game effects) replays an `fxlog.tcl` log: every segment's writes, the queue, the tick divider, the end state, the effects' starts and plays to the end, the bench's requests, the text screens' silence; the stages' tunes of two visits tick for tick; mutations a log must fail (5.23) |
| `cheat.tcl` | Tcl | `ch_job DIR ROM LABELS`: a `CHEAT=1` build by the keyboard from the power-on, F5 ending level 1 and level 2, F4 filling the energy, snapshots and notes (5.23); since the ending's step through the game completed (RETURN at the name entry: `ending.tcl` `ge_ret_arm`) to the title |
| `ending.tcl` | Tcl | the game completed and the high scores (5.25): `ge_job DIR TAG ROM LABELS KEYS ?MACHINE? ?FIRE?` (an `END_TEST` build's screens, the keys typed one a wait of the name entry, the tune's ticks, the table in RAM), `ge_ret_arm ROM LABELS` (RETURN at a flow's name entry: `np.tcl` `np_title_setup`'s jobs, `cheat.tcl`) |
| `endcheck.py DIR TAG KEYS [--tag N] [--score S] [--over [--no-offer]] [--gen GEN]` | python | `ge_job`'s records (5.25): WELL DONE, every wait of the name entry and the table screen against `tools/msxtext.py`'s renders and models of `$1215C` and `$1211C`, R#0/R#1 and the palette at each, the tune's 4,917 ticks, the continue offer after an entry, the table in RAM |
| `frsnd/endsim.py ROOT ROM LABELS` | python | the ending's sound (5.25): `end.bin`'s tune and HI1's effects as `msx/ending.asm` starts them, register-exact against the streams in the Z80 interpreter (four chip sets, 50 and 60 Hz, the R800) |
| `l2stub.py OUT [--drop NAME ...] [REF ...]`, `--list` | python | level 2's bench references with the routines the port has not ported yet stubbed as the port stubs them (5.22), so that its traces compare whole |
| `l2frame.py SNAP LEVEL HUD OUT.png [SPRITE_PAL]` | python (venv) | `tools/msxframe.py` on a level-2 snapshot, the sprites' expected pixels from the palette they were converted with (level 1's, until level 2's step 12) (5.22) |
| `vatlog.tcl` | Tcl | level 2's vats (5.22, step 14; sourced after `load.tcl`): `vl_jobs` (the guard with tears and every vat column drawn: its parts' beam lines, R#23, the time in `vat_run` and `vat_prep`), `vl_speed_jobs` (game frames, ticks and pictures in SECS), `vl_snap_jobs` (`rc2_snap` at chosen game frames for `tools/mapcmp.py`) |
| `l3field.tcl` | Tcl | level 3's play field (5.27, its step C; sourced after `load.tcl` and `l2base.tcl`): `lf_jobs DIR R POSES ?FROM? ?N? ?MACHINES? ?DRIVE?` (scripted enemies of level 3's frames appended to the tick's play-field list after `bob_flush`, the field check's records, the frame cache's copies counted), `lf_start_jobs DIR R ?SECS? ?POSES?` (level 3's start check under the guard, `hz_l2_start_jobs`' lines) |
| `pooldiff.py OLD_PREFIX NEW_PREFIX` | python | the global sprite pool grown in place: RoboCop's, level 1's and level 2's index entries resolve to the same records, patterns and colour rows (5.27) |
| `l3poses.py OUT.tcl [POOL]` | python | `lf_jobs`' script from level 3's play-field frames: Cain, type 21, the truck, type 51, type 35 with the rocket, Cain's legs beside type 21's, each part cycling its frames, a hit flash every 16th tick (5.27) |
| `vatcheck.py DIR` | python | `vl_jobs`' logs per machine: columns a second, each column's draws a second, the CPU's share, the least margin from the beam to a column; exit 1 when the beam drew into a vat column (5.22) |
| `cutview.tcl` | Tcl | level 2's arrest scene (5.22, step 15; sourced after `load.tcl`): `cv_view_jobs` (at every tick the view, `v_addx`, RoboCop and the camera; at each list's split its camera, RoboCop's record and the play-field BOBs) |
| `cutview.py cut SNAPROOT REF.jsonl`, `view DIR [--add 48]` | python (venv) | the cut at a vat's surface (stills against `tools/msxframe.py --cut LINE` at the original's copper line) and the arrest's view (`v_addx`'s steps, the view's pace, RoboCop's range, the suspect whole) (5.22) |
| `l2neg.sh REPO BASE W OUT` | shell | the level-2 gate's negative controls on copies of a passing run's records: each mutated copy must FAIL its verdict, each unmutated one PASS (5.24) |
| `mcpd.py DIR`, `mx.sh NAME 'TCL' [TIMEOUT_S]` | python, shell | a private MSX-AI MCP session (its own headless openMSX, the same `msx_local_*` tools) when the in-process target is another agent's: `mcpd.py` in the background serves `DIR/req/*.tcl`, `mx.sh` (`MCPD_DIR=DIR`) sends one command and prints the reply (5.24) |

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
  `snd_stop`, `BANK_MUSIC`;
- level 2 (5.22): `lv_next`, `dsp_off` (`rc2_l2_arm`), `BANK_L2`, `BANK_L1` (`hz_l2_still_setup`);
  `tracecmp.py --fields analysis/amiga_ram_l2.tsv` reads `mk_tab2` and `diff_tab`;
- level 2's base (5.21): `spr_plan`, `SPR_BASE_BANK`, `SPR_PAT_BANK`, `SPR_COL_BANK`, `VIEW_LINES`,
  `fx_start`, `fx_tick`; its field records copy RAM 0600h-09FFh (the play-field engine's lists:
  `fb_dn0` 06D9h, `fb_dn1` 0712h, `fb_lost`, `fb_qn`), F240h-F27Fh (`fb_vis` F248h) and MP_B
  F500h-F8FFh, which `fieldcheck.py` reads at those offsets;
- level 2's sound logs (5.23, `fxlog.tcl`): `snd_frame`, `sf_back`, `sq_put`, `sq_mute`, `sq_sfx`,
  `sq_gun`, `sq_stop`, `sq_title`, `sqf_t`, `mus_stop`, `mus_start`, `fe_text`, `tns_go`, `tn_tick`,
  `tn_left`, `tick_n`, `scc_pg2`, `mus_mode`, `BANK_INPUT`, `BANK_MUSIC`, `BANK_FRONT`, the scripts
  `txt_l2_brief`, `txt_l3_brief`, `txt_cont`; `fxcheck.py` the engine's equates and RAM homes
  (`SCCFX_BANK`, `GUN_FX`, `GUN_TAB`, `SND_SFX_N`, `snd_sfx`, `fx_waves`, `TN_MARK`, `SCC_*`, `mus_v`,
  `fx_pv`, `fx_wc`, `snd_v`, ... its `LABELS_NEEDED`); the cheat (`cheat.tcl`): `front_stats`,
  `fr_title`, `front_mode`;
- level 2's vats (`vatlog.tcl`): `vat_prep`, `vat_run`, `vat_pass`, `vat_mirror`, `vat_fr`, `vat_bk`,
  the harness's marks `vr_try`, `vr_drop`, `vr_nt`, `vr_lt`, `vr_ok`, `vp_scan`, `vw_ret`, the parts'
  starts `ve_go1`, `ve_go2`, `vmg_c`, `vmg_d`, `vmg_end`, and `fb_meetq`, `act_a000`, `BANK_L2`,
  `iv_late`; the arrest's view (`cutview.tcl`): `tick_start`, `game_tick`, and RAM CE43h (`v_addx`).

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
| `build/emu/drive_reloc.txt` (`.args`) and `trace_reloc_ram.jsonl` (401 rows) | the relocation drive (the cracked wall, `obj_relocate` `$9FC4`: RoboCop sent to (996, 640) at game frame 192), with `rc2_drive_rom` on the trace build, as `drive_die` | level 2's step 5 (the old `drive_reloc_up` was lost): `python3 -I tools/drivejoy.py --joy 110:300:u --tele 100:2072:320 --god build/emu/drive_reloc.txt`, then `$PY -I tools/amigaemu.py game --gframes 400 --drive build/emu/drive_reloc.txt --trace build/emu/trace_reloc_ram.jsonl --trace-ram`. At `8507734` and since, 7 rows differ: `player_hot_x`/`_y` at game frames 193-199, right after the relocation, where the port's `draw_player` keeps the state's last frame record and the Amiga reads on past them (`msx/player.asm` `pl_frame`, on purpose); every other field 0 differ |
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
  `8b89e4e`; take the addresses from the build's label file). Any entry elsewhere is a glitch.
  Since level 2's step 16 the guard counts nothing under an all-black palette or with the display
  off, and a tear only when a picture shows a command's lines half old, half new (5.22, "At step
  16"): those copies no longer count.

### 5.8 VRAM access speed

`hzf_job` (in `suite_drives`, `W/O/flow/fast_{m2,tr}.txt`) counts with `rc2_count_too_fast`
(`tools/openmsx_rc2.tcl`, `too_fast_vram_access real`). It covers `solve1` with the entry's
uploads and the exit's restore, on C-BIOS_MSX2 and the FS-A1GT at 3.58 MHz. Expected: "too fast
VRAM accesses: 0 ...; result 0, passes 732".

**The counter counts since `ff249f6`.**

- openMSX runs a callback setting's value as a command, with the event's arguments appended: it
  must name a proc. openMSX's own `share/scripts/callbackprocs.tcl` does `set
  VDP.too_fast_vram_access_callback warn_too_fast_vram_access`.
- Before `ff249f6`, `rc2_count_too_fast` set an inline script there, which failed silently: it
  never counted, and the zeros of the night's runs before `ff249f6` were not measurements. Since
  `ff249f6` it names a proc, `rc2_too_fast_cb`.
- It has been seen to move. With it, `solve1` from the power-on to `pz_done` (`ft_job`, 5.17 g):
  - at 5.37 MHz with the code before `rs_one`'s fix (`8b89e4e`'s): 5 lost writes on the Panasonic
    FS-A1FX and 43 on C-BIOS_MSX2+, all at `rs_one`'s two 17 T writes (C-BIOS_MSX2+ adds 1 in
    its own boot code, before the cartridge starts);
  - at 5.37 MHz with the fix (`ff249f6`): 0 in the cartridge on both;
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
  its real time-out, OUT OF TIME., the range (its real 2:00), the level-2 briefing and level 2 to
  its game frame 100 (level 2's step 18: before it, the title, fire and a new game);
- `pzt_m2` and `pzt_tr` (`hz_bonus_setup`): the `PZ_TEST=1` build from power-on;
- the restore jobs (5.10);
- the turbo R's blank (5.12).

The checks:

```sh
sh tools/bstest/hz.sh compare W/O/trace W/R/trace/rc2_ext5.labels
sh tools/bstest/hz.sh fresh W/fresh base suite
python3 -I tools/bstest/bonuscheck.py W/O/flow prod_m2 --result time --gen W/R/prod/gen --range time --brief l2 --level2
python3 -I tools/bstest/bonuscheck.py W/O/flow prod_tr --result time --gen W/R/prod/gen --range time --brief l2 --level2
python3 -I tools/bstest/bonuscheck.py W/O/flow pzt_m2 --result time --gen W/R/pzt/gen --range time --brief l2
python3 -I tools/bstest/bonuscheck.py W/O/flow pzt_tr --result time --gen W/R/pzt/gen --range time --brief l2
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
# a layout that moves blocks (level 2's step 12: the sprite pool 4 banks larger, every later block
# 4 banks on): the blocks by name, wherever each build put them, and the code banks that moved
python3 -I tools/bstest/romdiff.py --blocks W/old/rc2.rom W/new/rc2.rom --allow SPR_BASE_BANK,LEVEL_BANK,L2_TAB
python3 -I tools/bstest/relocheck.py W/old/rc2.rom W/new/rc2.rom W/old/rc2.labels W/new/rc2.labels \
    0 1 2 3 4 5 6 7 8 9 BANK_PUZL BANK_FRNG BANK_L2
```

- `romdiff.py` names the banks that differ. Expected: only the banks the change touched. The
  data banks 10-77 never changed during Brainstorm's milestone 1.
- `relocheck.py` passes when a code bank's other differences are only operands of labels that
  moved ("relocheck: PASS", exit 0). For example, a `TAG` build against the `TAG=0` one in banks
  0 and 78, or the review fix's FRONT change. A one-byte operand passes when it is a changed byte
  equate plus 0-63 that moved by as much (`NAME + k`: `ld a,HUD_BANK + 1`, `add a,SPR_BASE_BANK +
  SPR_COL_BANK`, the bank numbers mkrom writes into `gen/music.inc`; the summary names the nearest
  such equate), or a moved label's low or high byte after an instruction that takes a byte. Bytes
  inserted into a bank (new code, a descriptor that grew) cannot pass: check them apart.
- `romdiff.py --blocks` reads each image's `gen/banks.inc` (next to the ROM, as `build.sh` leaves
  it): a block starts at a bank equate (`BANK_*`, `*_BANK`, `L2_TILES` ... `L2_ATLAS`; FIXED = banks
  0-1) and runs to the next, the last to the first bank of 0FFh bytes; every data block is compared
  with the other image's of the same name: "identical", a byte count, another size, or only in one
  image. Exit 1 when a data block not named in `--allow` differs or is missing in the new image.
- `variants.sh` builds the night review's 41 option sets ("NAME OK" or "NAME FAIL: the first
  error"). At `8b89e4e` all built except `DEMO_ACTORS=2`/`5` and `DEMO_HUD=1`, which overflow the
  fixed area at `1818985` too.

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

Output goes to `W/O/np` and `W/O/fast`. The numbers below are the night's, at `ff249f6` with
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
that follows the result. Since level 2's step 18 the product goes on from the range into the
level-2 briefing and level 2, and the title follows level 2's stages instead: the job records the
briefing and level 2's start under TAG (`hb_step`, 5.22), ends level 2 at its game frame 100 as a
`CHEAT` build's F5 would (`np_t_l2`: `$16D0` FFh, `$16C4` 40h), records the second visits' screens
and the level-3 briefing under TAG2 (`bonuscheck.py W/O/np TAG2 --result time --range time --brief
l3 --no-game`; Brainstorm's passes 100 and 400 and the range's pass 1500 in `W/O/np/st_TAG2/`:
`stepcheck.py still --visit 2`, `shots.py`), and the title after the level-3 briefing as above
(TAG's files); its game at tick 300 is level 1 again (SHARP, `lv_logic` `BANK_L1` in TAG2_rg.txt). `np_title0_setup` records the title that follows level 1's statistics in
a build without Brainstorm: the approved flow. The night's reference was the product of the
commit before Brainstorm (the night's step 0: `msx/` as at `1148ea5`). A later milestone, whose
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
tick 100 (since level 2's step 18: to level 2's game frame 100, the plan's 4.4).

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

Expected at `ff249f6`:

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

(2026-10-28) On a V9958 the range scrolls its pages as rings by R#26/R#27 instead of R#18
(`docs/RANGE.md` 11.1). `rgview.py` recognises a ring list by R#25's MSK: it un-rotates the page by
its c before the compare, builds the picture as shown (screen x = Amiga column s - 8 + x, x 0-7
hidden), places the sprites at their screen x, takes the bench's camera from
`msxrange.camera_ring` and leaves c out of the bench's state (a ring page keeps its own c while it
holds s's columns; the registers' check holds c <= s <= c + 8). The HUD probe counts R#18, R#27 or
MSK left at the split's end; its negative control holds s at 7 and, on a ring, turns the split's
R#27 = 0 into R#18 = 0.
The bench's camera for every other page is `msxrange.camera_steps` (`docs/RANGE.md` 11.2: the
V9938 steps 16 columns at run time, as RG_ADJ=0 builds do on every VDP).

The second bonus stage (`msx/frng.asm`, its display `msx/frngview.asm`; `docs/RANGE.md` 3.3 and
4.2) draws what the original draws in each
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

The run of 2026-10-27 (the commit after `781005e`): every verdict PASS.

- 45 traces 0 differ (`armed` 1,163 passes, `mixed` 1,869, `edge` 344, `timeout` 301, `armed2`
  1,163, the other ten as at step 7).
- 282 stills equal to the render; the records 0 torn, 0 SAT errors, 0 coherence errors, every
  state the bench's: `armed` 613 pictures in 1,158 passes on C-BIOS_MSX2 (606 FS-A1FX, 611
  FS-A1GT), `mixed` 1,163 in 1,868 (about 27 pictures a second).
- The guard: 1,348 frames, about 3,100 commands, all 0. VRAM speed 0 in the cartridge.
- The pass rate: 0 late passes; the worst pass 37,131 T-states at 60 Hz (a VBLANK: 59,659),
  38,603 at 50 Hz.
- The restore PASS; the HUD at `armed`'s 39 passes equal to step 7's build (`hudcheck.py
  W/O/st/armed_m2 REF/st/armed_m2`: a build of `781005e` in a worktree, the same `rgv_job`).

The run of 2026-10-27 with the camera (the commit after `8c08187`): every verdict PASS.

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

`docs/RANGE.md` section 4 asks for every check of
the range, logic, display, camera and sound, and for every check of what existed before it (level
1, the title, `front_stats`, Brainstorm), against the base `cb7c9ef`, the commit before the range.
`regress.sh` (shell) and `regress.tcl` (Tcl) run them all; `rgflow.tcl` holds the range's flows,
`frsound.tcl` its sound logs, `rgcheck.py` its text screens' check, `cmpcheck.py` the comparison of
Brainstorm's check logs, and `frsnd/` the sound's Python checkers (the venv's Python: numpy).

```sh
sh tools/bstest/regress.sh base B          # once a milestone: B/wt (cb7c9ef), B/R; the product's SHA-256
```
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; rgr_base_chain {B} {B/base.done}   (41 jobs)
```
```sh
sh tools/bstest/regress.sh basecheck B     # B/check_all.log (Brainstorm's checks on the base)
sh tools/bstest/regress.sh builds W        # 21 builds through build.sh, W/drives; prints the Tcl line
```
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; rgr_chain {W} all {W/all.done}     (208 jobs)
```
```sh
until [ -f W/all.done ]; do sleep 20; done  # (or poll as in section 4); the file lists the messages
sh tools/bstest/regress.sh check W B       # every verdict, then "regress: PASS"; exit 0
```

One family at a time: `rgr_chain {W} FAMILY {W/FAMILY.done}`, then `regress.sh check W B FAMILY`
(several families may follow `check W B`). `hz_chain JOBS MARK` writes MARK when the chain ends,
done or stopped by an error: a shell waits for the file instead of polling the emulator.

**The base.** `regress.sh base B` adds a worktree of `cb7c9ef` in `B/wt` (`git worktree add
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
| `flows` (22) | `suite_flows` (as `new`); `xfresh` (the title from power-on again, exact: 5.21); `tx_ex`, `tx_f1`, `tx_tr` (`np_title_setup` EXACT 1); `wp_tr`; `p2m_ex` (the 2 MiB product, `hz6_prod_setup`); `kb_ex`, `kb_tr` (`rgk_job`) | level 1's coverage traces 0 differ; the title from power-on identical to the base's (on the exact record when the base has one: `l2base.py fresh`, 5.21); `bonuscheck.py --range time` on `prod_*` and `pzt_*` (Brainstorm's screens, then the range's intro and OUT OF TIME. after its real 2:00, the rating 24 at `fr_rated`, SHARP and lost 0 at the new game); the restore; the turbo R's blank (reported); 0 writes to 4000h-7FFFh; the title after the flows against the base's (`titlecmp.py` with `unseen_regs`, `titlecmp2.py --unheard`); the 2 MiB product through both stages; the keyboard flows (below) |
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

**The run of 2026-10-27** (branch `range` at `56923f5` plus the moved harness; `W` =
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
- Again on 2026-10-28 after `b4fdcc3` (the stage's own stop, `rg_end`): every family PASS, 45
  verdicts; the sound's drives now 1,866-1,868 ticks (the 13-14 ticks after the last pass are gone),
  the Q line 0 ticks after the last pass in all 20 logs; the logs of the build before the fix FAIL
  the new rule ("no stop at the stage's end"), and `frregcmp.py --selftest` catches a missing and a
  late stop on every chip set.

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

### 5.20 The shooting range's test candidates (step 13 of its plan)

The candidates of `docs/RANGE.md` section 6 are built outside `build/msx` (`TAG=4`; each twice, to
the same bytes, through `build.sh`), copied under their final names into a folder `C`, and checked
from the power-on with the keyboard, never `ext_joy`:

```sh
sh tools/bstest/build.sh CB/prod/rc2.rom TAG=4               # and CB2/... for the second build; cmp
sh tools/bstest/build.sh CB/range/rc2.rom PZ_TEST=2 TAG=4
sh tools/bstest/build.sh CB/prod2m/rc2.rom TAG=4 ROM_2M=1
sh tools/bstest/build.sh CB/range2m/rc2.rom PZ_TEST=2 TAG=4 ROM_2M=1
sh tools/bstest/build.sh CB/noadj/rc2.rom PZ_TEST=2 TAG=4 RG_ADJ=0
sh tools/bstest/build.sh CB/v2/rc2.rom PZ_TEST=2 PZ_LEVEL=2 TAG=4
# then C/NAME.ROM, NAME-range.ROM, NAME-2M.ROM, NAME-range-2M.ROM, NAME-range-noadj.ROM,
# NAME-range-v2.ROM (NAME = ROBOCOP2_v0.1.3-test4)
```
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; rgc_chain {CB} {C} NAME {W}     (15 jobs)
```
```sh
sh tools/bstest/regress.sh cand W B NAME CB     # "cand: PASS"; pictures in W/png
```

`rgc_chain` (`rgflow.tcl`) runs, into `W/run` and `W/fresh`:
- the title from the power-on of `NAME.ROM` and `NAME-2M.ROM` on a fresh Expert (`hz_fresh_setup`:
  `cand`, `cand_2m`), checked against the base's `B/fresh/base_*` (`hz.sh fresh`; the 2 MiB image
  may differ only in `game_ram.bin`'s D032h-D033h, cmp's offsets 51 and 52);
- `rgk_job` on `NAME.ROM` on the Expert, the HB-F1XDJ and the FS-A1GT (`kb_m2`, `kb_f1`, `kb_tr`)
  and on `NAME-2M.ROM` on the Expert (`kb2m_m2`): level 1 ended, Brainstorm solved, the range's 25
  shots, the result, the title, checked as 5.19's keyboard flows with `--tag 4` against the base's
  title after Brainstorm (`B/O/np/tx_ex`, `tx_f1`, `tx_tr`). The title's registers may differ only in
  the sprite tables' (R#5, R#6, R#10, R#11) while both records have the sprites off (R#8 bit 1:
  the title's G7): `regress.sh`'s `unseen_regs` (2026-10-28: R#5 CFh/C7h on the 2 MiB image, the
  game's sprite set at level 1's end; nothing shows);
- `rgc_job` (a PZ_TEST=2 build from the power-on: `rc2_fr_drive`'s trace, `rgk_keys_arm`'s keys
  from `build/emu/fr_armed.drive` (`fr_armed2` for v2), `rgv_arm`'s snapshots at passes 60, 300,
  600, 900 and 1100 and a record of 600 VBLANKs from pass 1000 with 60 past `fr_rated`, the intro's
  and the result's records, then the title, fire 1.5 s after it and the new game's frame 100) on
  `NAME-range.ROM` (Expert, HB-F1XDJ, FS-A1GT), `-range-2M` (Expert), `-range-noadj` (Expert,
  HB-F1XDJ) and `-range-v2` (Expert): `frngcmp.py --skip joy,timer_min,timer_sec` against the bench,
  `rgcheck.py --counts 25,0,1 --tag 4`, `rgview.py still` and `rec` with `--ref` and `--gen` (PNGs);
- `rgc_job` with DRIVE `-` (no input; the trace from pass 5990 only) on `-range` (Expert) and
  `-range-noadj` (HB-F1XDJ): the real 2:00, `rgcheck.py --time --tag 4`, stills at passes 600, 3000
  and 6040.

Then, with the MCP's openMSX shut down, `tools/msxmatrix.py` on each file (`--labels CB/K/rc2.labels`;
`--no-title` for the four PZ_TEST ones): 10 of 10 each. The candidates' notes and screenshots go
with the files; only the files actually sent go to `build/msx`.

On 2026-10-28 (`b4fdcc3`, `impl/s13` of the range's scratch): the six built twice to the same
bytes; `rgc_chain` 15 jobs without a time out; `regress.sh cand`: PASS (the fresh titles; the
keyboard flows 732 and 1,163 passes 0 differ, every screen pixel-exact with TEST 4, the titles
identical; the range candidates 1,163 passes, 140 fields 0 differ, 5 stills and 600 records each
with 0 torn, 0 SAT errors and 0 pixels outside, R#18 shown 06h at s = 6 and 00h in the noadj
builds; the two left alone 6,050 passes, OUT OF TIME., POOR; every new game SHARP with the lost
counters 0); the matrix 10 of 10 on all six. Negative controls of `unseen_regs`: R#8's sprite bit
cleared, or R#2 changed, gives DIFFER.

### 5.21 Level 2's base (step 0 of its plan)

Level 2's plan asks every step to keep what exists unchanged: level 1's logic and picture, the title,
`front_stats`, Brainstorm and the range, against its step 0, the base `8507734` (branch `level2` =
main). `l2base.sh` runs the range's whole regression (5.19) and level 1's records that it does not
make (`l2base.tcl`), in one chain, and compares any later build with the base:

```sh
sh tools/bstest/l2base.sh builds W         # regress.sh builds W, W/L/lock24 (EXTJOY=1 LOCKSTEP=24) and lock24p (+ NO_SCC=1), W/banks.txt
```
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; source {<repo>/tools/bstest/l2base.tcl}; l2b_chain {W} {W/all.done}   (227 jobs)
```
```sh
until [ -f W/all.done ]; do sleep 20; done
sh tools/bstest/l2base.sh check W BASE     # every verdict below, then "l2base: PASS"; exit 0
```

`check W BASE [RB]` runs `regress.sh check W RB` (RB defaults to BASE: a base made by `l2base.sh base`
holds what `regress.sh check` reads of a base, its title from power-on as `fresh/base_*`), then:

| Job (`l2b_jobs`) | Records (`W/l1`) | Verdict |
|---|---|---|
| `tr_die`, `tr_over`, `tr_end` | `drive_die`, `drive_over`, `drive_end` (901, 1,249, 517 ticks) on the trace build, C-BIOS_MSX2 | `tools/tracecmp.py --ram` against the bench's `trace_*_ram.jsonl`: 0 differ |
| `st_m2`, `st_fx`, `st_tr` | the product from the power-on of C-BIOS_MSX2, the FS-A1FX, the FS-A1GT: the title, SPACE, 40 s of level 1 from its tick 20 under `rc2_guard` (tears counted), `rc2_patcheck`, `rc2_sprlines`, `rc2_satcheck`; the lost counters | reg, pal, cmd, cpu, vbl, bad patterns, bad SATs, lost 0; tears and lines above 8 at most the base's (`l2base.py start`) |
| `fd_FROM_M` | the field records: every picture of `drive_cov0` from game frame 430 (125), 860 (480), 1490 (360) on the `EXTJOY` build, C-BIOS_MSX2 and the FS-A1FX | `fieldcheck.py` (venv): every picture checked; every picture that differs of the known hostage tear's classes, within their bound (`l2base.py field`, `TEARS`: the timing-blind verdicts below) |
| `sl_m2`, `sl_fx` | the stills: `rc2_snap` at the HUD split of the first new list from game frames 100, 430, 860, 1490, 2400 of `drive_cov0` on `lock24` | `tools/msxframe.py` (venv) renders each; the picture identical to the base's, its own count at most the base's (`l2base.py stills`) |
| `lk_m2`, `lk_fx` | `rc2_disp_rom`, 3,000 lists of `drive_cov0` on `lock24` | `tools/dispcmp.py` against the base's: 0 differ |
| `fx_scc`, `pw_scc`, `pw_psg` | 300 s of `drive_cov0` on `lock24`: `sess_fxlog.tcl` (every effect start, the SCC's and the PSG's registers at every `fx_tick`); every PSG write ("VBLANK register value") on `lock24` and `lock24p` (the effects on the PSG alone, which `sess_fxlog.tcl` does not see), and in the same runs the effects by their starts (`pw_K_sn.txt`, `l2b_sn_arm`) | by their starts (`fxcmp.py`: the timing-blind verdicts below): the same starts in the same order and `LOCKSTEP` frames, each effect's own sound from its start; `sess_fxlog.tcl`'s starts the same; the logs themselves reported |

The code banks' free bytes (`l2base.py banks`: every `ds LIMIT - NAME_end` window of `msx/rc2.asm`)
are listed beside the base's for every build. `l2base.sh base W` turns a checked folder into a base.

Brought in from level 1's scratch folders at the base: `fieldcheck.py` (2026-10-21; the copy of
`build/perf_2026-10-23`) and `sess_fxlog.tcl` (2026-10-22; its scratch copy was gone, its last text
came from the session's log). Changed only where the harness's rules or the engine since required:
`fieldcheck.py` imports without numpy or the build's files, finds the repository from its place,
reads the map patches' two pools (`9eee4a3`, 2026-10-25: the record carries MP_B F500h since, as
`rc2_jumprec`'s), and counts a record of another length as skipped instead of passing it in
silence (at the base it had skipped every record); `sess_fxlog.tcl` sources
`tools/openmsx_rc2.tcl` from its place and sets `::fl_done` instead of quitting openMSX. Its
checker `fxcheck.py` is lost (level 2's step 21 writes one). The start check starts its guard at
`tick_start`: started inside a sprite upload (`outi32`), `rc2_guard` took the upload's writes for
VRAM 00000h (it cannot know an address set before it started): 81 false "cpu" on the FS-A1GT.

**The base of 2026-10-28** (`impl/base` of level 2's scratch folder): the 25 builds rebuilt byte for
byte, the 23 of `regress.sh builds` equal to the range's step-13 builds, the product with `TAG=4`
(and `ROM_2M=1`) equal to the delivered `ROBOCOP2_v0.1.3-test4.ROM` (`-2M`); the chain without a time out
(the start checks and the PSG logs run again once their jobs took their final form);
`regress.sh check` against the range's base `cb7c9ef`: 45 verdicts, **regress: PASS** (the title
from power-on identical to `cb7c9ef`'s in every record); the death, game-over and end traces 0 differ;
the start checks all 0 on the three machines (26,690 / 26,445 / 31,505 sprite entries checked); the
field check 0 differ in every window but 860 on the MSX2: 3 pictures (`j008_f0021`-`23`, 177 pixels:
the hostage half old, half new; 0 on the MSX2+), as level 1 had them (`0.1.1`: "3/6"); the stills'
`msxframe.py` counts 0, 77, 37, 462 / 543, 57 (its map has no play-field BOB, patch or tile cache);
3,000 lists, none late, on both VDPs; 800 effect starts and 7,435 SCC ticks, 19,846 and 22,217 PSG
writes. A second run of the whole chain on a rebuild (the same 25 ROMs, byte for byte) against the
base: **l2base: PASS**, every record identical. Negative controls (copies of the base's records, each
must fail): `camera_x` of one trace row changed (1 differ), tear 0 → 2 and cpu 0 → 1 in a start
check, 50 page lines zeroed in one field record (1 picture, 10,987 pixels), 16 KiB of a still's
page zeroed (42,348 pixels), one SAT byte of a `LOCKSTEP` list (1 differ), one PSG write, one SCC
tick: every one FAIL.

**The gate's timing-blind verdicts (2026-10-28, level 2's harness step).** Steps 3-5 changed level
1's CPU time on purpose, and four families of verdicts failed although nothing visible changed; a
build of steps 3's tree with pure delays added (13 T in `get_tile`, 14 T in `atr_rc`, 10 T in
`ttp_prep`/`dt_prep`) failed the same four. They now judge what a change of CPU time cannot move,
so that a step passes `l2base.sh check` literally:

| Verdict | Before | Now |
|---|---|---|
| The title from power-on (`regress.sh` flows) | `hz_fresh`'s record: `hf_step` polls every 0.1 s, so the game was recorded at tick 302 instead of 300 | job `xfresh` (`regress.tcl` `rgr_xfresh_setup`: `hz_fresh_setup` with `np.tcl` `np_hf_step`): `fresh/xnew_*`, the game at exactly its tick 300 (a breakpoint at `tick_start`); `l2base.py fresh` against the base's `xbase_*`: the title's VRAM, registers and palette identical, its music identical at every tick (`titlecmp2.py`), the game's VRAM identical but the order of each sprite set's entries (the same entries, the same number of times: `l2base.py sat_order`, level 2's step 12) and its RAM D000h-DFFFh by `l2base.py ram`. A base without `xbase_*` (the range's) keeps the polled comparison; the polled record is reported |
| The titles after the flows (`tx_ex`, `tx_f1`, `tx_tr`, `kb_ex`, `kb_tr`) | the registers identical | `unseen_regs` (as `regress.sh cand`): identical but the sprite tables' R#5, R#6, R#10 and R#11 while both records have the sprites off (R#8 bit 1). R#5 differed (CF/C7: the SAT's double buffer, whose parity the frames before the title set) |
| The field check (`fd_*`) | at most the base's pictures and pixels per window | `fieldcheck.py` prints a `CLASS` line per kind of difference in a picture (`hostage-tear` with the hostage BOBs of the shown and of the newest list, `smoke-tear`, `other`); `l2base.py field` accepts only the known classes (`TEARS`), within their bound |
| The effects (`fx_scc`, `pw_scc`, `pw_psg`) | the logs byte-identical, write for write by VBLANK | `fxcmp.py` on `pw_K_sn.txt` (below); `fxcmp.py --starts` on `sess_fxlog.tcl`'s log (the same effects in the same order); the logs themselves reported |

- **The game's RAM by variable** (`l2base.py ram`): a byte is compared at its variable's place in
  each build: the nearest RAM label at or below it, by the same name in the new build's label file,
  as far as the variable reaches there (up to the next label). A differing word that points at the
  same label and offset in both builds is a relocated pointer (code moved: `diff_tab`, `mk_tab`,
  `sw_xm`); `$B32` (D032h-D033h) is R-seeded (the plan's 4.4); a byte past its variable's room in
  the new layout is compared in place unless a moved variable's byte lies there (step 5's repack:
  DD53h, DD58h-DD5Fh); a variable whose name is gone fails. Step 5 against the base: 3,996 bytes
  equal at their place (19 moved with their variable), 5 bytes of relocated pointers, 84 compared in
  place, 9 not compared, 0 differ.
- **The known hostage tear** (level 1's, older than this work: the base has it, v0.1.1 had "3/6"):
  for a few pictures the hostage on the bar at (785, 680), above RoboCop's lift, shows half its old
  frame and half its new one. Class A `shown=4@785,680 newest=2@785,680+11@961,760` (59 pixels a
  picture), class B `shown=2@785,680+11@961,760 newest=0@785,680` (2 pixels). Which VDP and which
  pictures show it moves with the CPU time: window 860, base m2 3 (A) and fx 0; step 4 m2 0, fx 6
  (A 3, B 3; 183 pixels); step 5 m2 3 (A), fx 5 (A 2, B 3; 124 pixels); every other window 0. The
  bound, the most of that timing-control set on either machine (`l2base.py tears` on its check
  files): per class 3 pictures and its pixels a picture, per window and machine 6 pictures and 183
  pixels; no tear outside window 860. A new class, a pixel no list explains, a torn explosion or more
  than the bound fails. Milestone 2's field work should fix the tear (zero glitches), then `TEARS`
  empties.
- **The effects by their starts** (`l2base.tcl` `l2b_sn_arm`, in the PSG-write jobs' runs: no extra
  job): `pw_K_sn.txt` holds `F V` at every `LOCKSTEP` frame's start (`wfk_ok`), `S V EFFECT
  CHANNEL` at every start (`sq_sfx`), `G V` (the gun, `sq_gun`), `X V` (`sq_stop`, `mus_stop`) and
  `T V PSG VOICES [SCC]` at every sound tick (`sqf_t`: the PSG's R0-R10, each PSG voice's ticks left,
  noise period and Amiga channel, the SCC's registers; a bare `T V` repeats the state). The cadence
  gives the tolerance: under `LOCKSTEP=24` a frame of two game ticks starts every 24 VBLANKs whatever
  the CPU time; the logic asks for an effect, the next tick's `frame_keys` queues it and the VBLANK
  interrupt starts it, so a start moves only by whole VBLANKs inside its frame. `fxcmp.py`: the same
  starts in the same order, each in the base's frame (24 VBLANKs, 20 sound ticks); then each start's
  own sound tick by tick from its start, per Amiga channel it takes: the SCC channel (period,
  volume, waveform) and the PSG voice that channel owns, whichever voice it is (volume, the tone
  period when on, the voice's own noise period when on: the shared R6 and the voice a channel-3
  effect takes are interplay), until a later start may take it in either run (the next start on the
  channel; for a PSG voice also any channel-3 start; for channel 3's voice any start; a stop). Exact.
  Step 5 against the base: 803 / 802 starts the same, in the same frames, moved -1 to +1 VBLANKs
  inside them; SCC 57,475 and PSG 33,390 / 33,393 sound ticks compared, 0 differ (step 4 and the
  delays build alike: 0 differ, moves -1 to +2).

**The sprite sets' order (level 2's step 12).** Which SAT entries a BOB's run takes depends on the
CPU time: two runs that both change take each other's entries list by list (`sprites.asm` `pc_run`: a
BOB's run goes where it fits), so at exactly tick 300 a build whose sprite code runs a little longer can
catch the other order. Step 12's build reached tick 300 one VBLANK later than the base (123.040 s against
123.023 s): the game's VRAM differed in 108 bytes, SAT entries 28-31 of both sprite sets (two 16 x 16
boxes at the same place, 85/140, which the base itself swaps between its two sets), everything else
identical, the RAM by variable equal. `l2base.py fresh` takes such a record when every differing byte lies
in the two sprite sets (`SPRITE_SETS`: `msx.inc` `SPR_COL_A`, `SPR_COL_B`, colour tables and SATs) and each
set holds the same entries (SAT bytes and colour row) the same number of times; any other byte, or an
entry that is not the base's, still fails. The order itself is checked where the timing is fixed: the
LOCKSTEP records (`dispcmp.py`, 2,998 lists 0 differ at step 12).

**The base gained** (`impl/base`): `fresh/xbase_*` (the job `xfresh` on the base's product: byte for
byte step 4's and step 5's exact base records) and `l1/fx/pw_scc_sn.txt`, `pw_psg_sn.txt` (the
`pw_*` jobs again on the base's builds; their `pw_*.txt` came out byte-identical to the base's).

**HEAD's run** (f2d0cf0 built from a worktree, its 25 ROMs byte-identical to step 5's gate builds;
227 jobs, 0 time outs, about 8 minutes): `l2base.sh check W BASE`: **l2base: PASS**: regress 45
verdicts PASS (the exact title from power-on PASS while the polled one still differs in 24 bytes;
the titles after the flows "registers that show: identical (sprites off: R#5 CF/C7 apart)"), the
death, game-over and end traces 0 differ, the start checks 0, the field check PASS with the known
tear (860_m2 A 3 pictures, 860_fx A 2 and B 3), the stills identical, LOCKSTEP 0 differ, the
effects PASS.

**Negative controls** (on copies of real records, each FAIL; the unmutated copies PASS): the exact
title: one title VRAM byte, the title's R#7, one game VRAM byte, the RAM's D100h, the pointer DD08h
moved to another place, a moved variable's value (`sw_ci`), free RAM DFC0h written, the game
recorded at tick 302, one music tick's registers; `unseen_regs`: R#7, R#2, R#5 apart with the
sprites on; the field: a new tear class, the known tear above its bound, a picture's pixels no list
explains, the tear in another window, 50 page lines zeroed in a record (`fieldcheck.py` run again:
8,431 pixels); the effects: ROMs with effect 4's first record changed, run in openMSX (SCC volume
0 → 1: 383 starts differ; PSG volume 11 → 10: 363 differ), a start one frame late, another effect,
a missing start (both builds), another effect in `sess_fxlog.tcl`'s starts. 25 FAIL, 8 PASS, as
they must.

### 5.22 Level 2's drives and its test start (step 7 of its plan)

**The test start.** `tools/mkrom.py LV_TEST=2` builds a ROM that starts level 2 at power-on, once
(`pz_first`), without the title: level 1's set-up (`ng_go`), then `rc2.asm` `lv_test` instead of level
1's main loop: `front.asm` `front_l2test` writes `LV_CARRY`'s score, lives, credits and rating
(`LV_CARRY=SCORE:LIVES:CREDITS:RATING`, default `10050:2:0:1`: score 10050 as a BCD long in AG's two
words, `$8034`, `$805E`, `ac_diff` = `diff_tab` + 8 x the rating 0-3, SHARP to POOR) and AG `$8050` = 1,
then runs the screens the product will show between the range and level 2 (`cpu_title`, `fb_prep`,
`front_brief`, a stub until step 18, `cpu_title`), then `lv_next` (the display off, `lv_go` with AG
`$8050`): the product's way into the next level. Later games are the product's. mkrom refuses
`LV_TEST` with `PZ_TEST`, `LV_TEST` other than 0 or 2, and `LV_CARRY` without `LV_TEST`. No level-1
tick runs before level 2, so `tick_n` is level 2's game frame and `rc2_drive_rom` drives these builds
unchanged.

```sh
sh tools/bstest/hz.sh l2builds W/R      # R/l2 (the default carry), l2s, l2f, l2p (SHARP, FAIR, POOR), l2o (0:0:0:1), l2c (0:0:1:1)
```
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_l2 {W/O/l2} {W/R} tr      (20 jobs: with ONLY, a list of names, a subset)
```
```sh
sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv W/O/l2 W/R                 # the bench's references
python3 -I tools/bstest/l2stub.py W/stub                                                   # (about 2 minutes, 4 cores)
sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv W/O/l2 W/R --refs W/stub   # "level 2: PASS (20 traces)"
```

`hz_l2`'s jobs (`hz_l2_jobs`), each `rc2_drive_rom` with the reference's rows: `end` 259, `tour` 2,654,
`lift` 801, `trolley` 641, `vat` 701, `fuzz` 2,501, `sharp`/`fair`/`poor` (`l2_trolley` on `l2s`/`l2f`/
`l2p`) 641, `over` (`l2o`) 109, `cont` (`l2c`) 301, `barrel` 901, `mine` 161, `t1left` 341, `drone` 401 on
C-BIOS_MSX2; `tour_fx` and `vat_fx` on the FS-A1FX, `trolley_eu` on C-BIOS_MSX2_EU; with `tr`, `tour_tr`
and `vat_tr` on the FS-A1GT. `compare --fields` takes each trace with its build's labels against
`build/emu/l2_<ref>_ram.jsonl` (`tools/l2drives.py`), or with `--refs` against another folder's;
`JOB:ROWS` compares a job's first rows only.

**The stubbed references** (`l2stub.py`). While routines are missing, a level-2 trace differs from the
bench's reference from its first row: `act_0c` (`$9EE8`) runs in `level_init`'s map-object pass, before
row 0 (its sound request `$B2D` = 28h is row 0's only difference), the trolleys (`$8F02`) from game
frame 0, type 1 from frame 4 (the first frames each reference runs a routine not ported at step 7: all
16 references alike). `l2stub.py` makes every direct reference again with those routines stubbed on
the bench the way the port stubs them (`--pre-poke` patches written before `level_init`: the trolley
`rts`, the vats' handler `bra.w $919E`, `act_0c` `bra.w $9C76` (the default activator, the port's
`ao_look`), types 1, 2, 5, 6, 14, 16 and 49 `moveq #-1,D0 / rts`, the slot freed as the port's stubs
free it), so that everything the port has compares whole, every row and field. A step that ports a
routine removes its stub from the port and from `l2stub.py`'s table (or `--drop NAME`).

**`rc2_l2_arm`** (`tools/openmsx_rc2.tcl`; default 44 of the plan): `rc2_drive_trace`'s trace in the
running machine, indexed from the first `tick_start` after `lv_next` (its breakpoint checks the
instruction there, `call dsp_off`: openMSX breaks at an address in any slot); `tick_n` is rewritten
around `rc2_drive_hit` and put back before the tick runs. For the product's flow into level 2 (step
18). `rc2_l2_drive` starts an `LV_TEST=2` build from the power-on and arms it: its trace of `lift`
equals `rc2_drive_rom`'s byte for byte (a check of the proc).

**The start** (`hz_l2_still_jobs W/O/still W/R ?FRAMES?`, default game frames 0 and 50): the `l2` build
from the power-on of C-BIOS_MSX2, the FS-A1FX and the FS-A1GT on `lift`'s drive, `rc2_snap` at the HUD
split of the first new list from each frame with level 2's logic bank in `lv_cur` and the display on
(a level's set-up runs with the display off, and a line match still sets the VDP's flag:
`hz_l2_still_hit` skips those), `when.txt` and `pos.txt` (RoboCop's and the camera's place, the logic
bank) beside each snapshot. Check each with `$PY -I tools/bstest/l2frame.py SNAP build/msx/level2
build/msx/hud OUT.png`: `tools/msxframe.py` with the sprites' expected pixels taken from the palette
they were converted with. msxframe converts every sprite frame again with the palette it is given, and
under level 2's palette C it picks other OR rows than the ROM's level-1 data (30-40 of RoboCop's pixels
a picture "wrong" where the screen shows the ROM's data exactly); until step 12 converts level 2's
frames against C, `l2frame.py` passes `build/msx/level1.pal` for them. msxframe's map has no
play-field BOB: the lifts drawn into the play field remain as differences (5.21's stills have the
same kind).

At step 7 (2026-10-28): the 20 jobs against the stubbed references 0 differ in all 1,022 fields over
every row (`tour` 2,654 rows on the three machines, `fuzz` 2,501, the four ratings, 50 Hz); against the
plain references `lift`'s row 0 differs in `snd_b2d` alone (28h/0). The start on the three machines:
RoboCop at (352, 784), `lv_cur`'s logic bank `BANK_L2`; the first picture (the view at (173, 638))
equal to the render but for the HUD's timer, which shows `hud_init`'s 09:58 for a frame or two before
7:30, as level 1's first picture does with its 10:00; at game frames 50, 70 and 100 RoboCop's and the
enemy's sprite pixels all exact (861, 808, 1,612), the only differing pixels the lift's (233-617).

At step 8 (2026-10-28): the trolley (`special.asm` `sp_trolley`), the vats (`level2.asm` `lt1`) and
`act_0c` (`mapobj.asm`) are ported and gone from `l2stub.py`'s table (the 7 types remain). Against the
plain references every job's rows 0-4 equal the bench (row 0's `snd_b2d` included: `act_0c` runs in
`ao_start`'s pass as in `level_init`'s), type 1's slot from row 5 on; against the stubbed references
the 20 jobs 0 differ over every row. RoboCop now dies in the vat, so `cont`'s trace ends at its game
over (row 108) until the port has the continue (step 19): `hz_l2`'s `cont` job times out after 60 s
instead of 1,800, and `hz.sh compare` without job names takes it as `cont:109` (the plan's milestone 1;
step 19 removes both).

At step 9 (2026-10-28): types 1, 2, 5, 6, 14, 16 and 49 and type 6's death (`level2obj.asm`) are ported
and gone from `l2stub.py`'s table, which is now empty: the 20 jobs compare against the plain references
(`hz.sh compare --fields analysis/amiga_ram_l2.tsv W/O/l2 W/R`, no `--refs`), 0 differ in all 1,022
fields over every row (`cont` to row 108), on the three machines and at 50 Hz. The field set leaves the
enemy bullets (`$C34-$D33`) and the explosions (`$D34-$D73`) out; a scratch set of their 112 fields (each
slot's x, y, type, speeds, word +A0h and accelerations; the explosions' bytes and places) compared 0
differ over `end`, `tour`, `fuzz`, `barrel`, `drone`, `t1left`, `vat` and `mine` too.

At step 11 (2026-10-28, milestone 1's acceptance), three additions:

- **The lost counters with every drive** (the plan's 4.2 check 5). `hz_l2`'s jobs run `hz_l2_drive`
  (`rc2_drive_rom` and, at every `tick_start`, `mp_lost`, `atr_lost`, `rd_lost`, `fb_lost` and the map
  patches' pools in use, MP_A's and MP_B's entry FFh) and append them when they end to `W/O/l2/lost.txt`
  (`l2_<job> (<machine>): mp 0 atr 0 rd 0 fb 0 pools EVEN/ODD tick T`). `hz.sh compare --fields` takes
  each job's last line there and fails on a counter that is not 0 (the pools' use printed: level 2's
  bounds are 146/143, `mapcells.py`). `cont` now ends once its 109 rows are written (its counters
  those of row 108's tick) instead of waiting for its 60-s time out; step 19 gives it the others'
  condition (`$::rc2_trace_done`) again.
- **Level 2's start check** (4.2 check 1): `hz_l2_start_jobs DIR ROM LABELS ?SECS?`, an `EXTJOY=1
  LV_TEST=2` build from the power-on of C-BIOS_MSX2, the FS-A1FX and the FS-A1GT on `tour`'s drive;
  from level 2's first `tick_start` (`lv_cur`'s logic bank `BANK_L2`) 42 s under `rc2_guard` (tears
  counted), `rc2_patcheck`, `rc2_sprlines`, `rc2_satcheck`. `DIR/start_<m2|fx|tr>.txt`: at that tick
  and at the end the game frame, RoboCop's and the camera's place, the logic bank, R#1, the VDP's
  palette, `lv_pal` and `pf_pal`, the lost counters and the pools; the rows driven; the guard's counts
  and its whole log. The drive's trace (`DIR/l2_tour.txt`, `l2_tour_fx.txt`, `l2_tour_tr.txt`) compares
  with `hz.sh compare --fields analysis/amiga_ram_l2.tsv DIR R tour:N tour_fx:N tour_tr:N` on the `l2`
  build.
  ```
  msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_chain [hz_l2_start_jobs {W/O/start} {W/R/l2/rc2_l2.rom} {W/R/l2/rc2_l2.labels}]
  ```
  Expected at step 11: RoboCop at (352, 784), logic bank 104, `lv_pal` = `gen/level2_grade.pal` (the
  VDP's palette black or the HUD's at the first tick, the play field fading in, `lv_pal` at the end);
  reg, pal, cpu, vbl 0, patcheck 0 bad; the lost counters 0. **cmd and tear are not 0 yet**, and every
  entry falls in one of the play-field engine's classes that level 1 shows too when the same guard runs
  over an active drive (`drive_cov0` on the EXTJOY build: reg 6-12, cmd 47-523, vbl 0-1, tear 5-102 in
  62 s): (1) the play-field BOBs' copy onto the page shown still running when the picture starts (HMMM
  about 50 x 28 at the lifts; by `fb_fits`' rule it keeps ahead of the beam, which the guard cannot
  see); (2) 16 x 16 tile HMMMs into the page shown during the play area when many cells change at once
  (the redraw's fallback, `vdp_cmd` from the scroll engines' redraw: in `tour` frames 638-644, a map
  object's look; 1-4 of them tears); (3) `R#46` written during the play area by `fb_qstart` for a
  staged piece (pc in `fqs_go`). `rc2_satcheck` also differs once at game frame 0 (the SAT in VRAM ends
  at sprite 0 while the first list's buffer is not published; level 1 the same at its frame 0; the
  base's start check starts at tick 20). Milestone 2's field work (the plan's steps 13-16, 4.2 check 8:
  tear 0) takes them; any entry outside these classes is new.
- **The guard** (`tools/openmsx_rc2.tcl` `rc2_rg_cmd`): a command started below the play area while the
  HUD's registers are in (R#2 page 3, between the split and the VBLANK's list) is no tear candidate any
  more: those registers show only the HUD's lines of page 3, so the play-field BOBs' scratch and caches
  on page 3 lines 112-175 were taken for play-area lines (69 such "tears" in level 2's start check,
  two builds on the three machines); what the next picture shows is checked when its list goes in
  (`rc2_rg_vbl`), as before. It can only remove reports: Brainstorm's guard tears (16 x 16 copies into
  the play page) and the range's guard (0) are unchanged.

At step 12 (2026-10-28, the global sprite pool in the ROM), **level 2's objects against the bench**
(the plan's 4.2 check 3): `hz_l2_objs_jobs DIR R NAMES ?MACHINES?` (hz.tcl) runs `rc2_objs_rom` on
`R/l2/rc2_l2.rom` with each named drive until the game frame passes the drive's rows
(`hz_l2_objs_done`: the file closed, the probe gone), on C-BIOS_MSX2, the FS-A1FX and the FS-A1GT:
`DIR/<name>_<m2|fx|tr>.txt`. The bench's draw calls: `$PY -I tools/amigaemu.py game --level 2 --carry
10050:2:0:good --gframes G --drive build/emu/l2_<name>.drive --stop-at-end --bobs AMI.jsonl`. Then
`python3 -I tools/objcmp.py AMI.jsonl DIR/<name>_m2.txt --sprites build/msx/sprites_l2.json --rows N
[--procs obj01_joint,obj05_update,...] [-v]`: `--sprites` gives level 2's frame table (the pool's: type
1's joint compositions keyed and placed as the legs' call, their picture 20-21 lines higher and 2
pixels wider; the torso's calls, "hidden", are no object), `--rows` cuts the record to the drive's game
(it runs past the drive's end, sometimes into a new game), `--procs` counts only those routines'
frames.
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_chain [hz_l2_objs_jobs {W/O/objs} {W/R} {t1left barrel drone tour end}]
```
What the trace build shows besides "exact" (step 12, types 1, 5, 6, 49): "missing, left out" (the
sprite budget: the build has `ENEMY_CAP=0`, up to five enemies on a line), "missing, loading" and
"late" (an older frame of the same BOB for a picture; objcmp's size rule calls a growing drip, 16 x 16
to 32 x 16, and the walkers' legs, 32 x 28 to 48 x 28, "late, other size": the same routine's frames),
and "missing" only in lists that repeat a tick while the view moves (after `t1left`'s and `drone`'s
teleports, or a 16-pixel step at an edge: `bf_vis` decides per tick, level 1 the same). No "extra",
no "no frame". Two "late, other size" of other routines (type 4's 16 x 16 flash and a walker's torso,
`tour`, `t1left` on the turbo R) are slot reuses of shared types, level 1's code.

**msxframe's sprite pixels**: it puts the objects in front of each other by object number, the VDP by
their SAT runs (a BOB's run goes where it fits): where two objects overlap, the 2-34 pixels a still
counts as not exact (steps 9, 11, 12) all become exact with the SAT's order (every such still of
steps 11 and 12 checked: the roof g2565 on the three machines, `t1left` g0215/g0260, `barrel` g0076,
`drone` g0300); and on the V9938 a sprite in the right border's columns (set-adjust) is counted but
not checked (`drone` g0050: 10 pixels). The check's limits, not the picture's.

At step 13 (2026-10-28, level 2's play field: its own atlas, frames and field tables, the dynamic slot
on page 2, 224 tile slots), **level 2's field check** (the plan's 4.2 check 2): `hz_l2_field_jobs DIR
ROM LABELS DRIVE WINDOWS ?MACHINES?` (hz.tcl; `l2base.tcl` `l2b_fd_setup`'s records: every picture's
HUD split from game frame FROM, N of them) and `fieldcheck.py DIR/W build/msx/level2 DIR/W.png --level
2` (level 2's frames as its ROM uploads them, `tools/msxframe.py` `FieldLooks`: the atlas as VRAM holds
it, the dynamic frames from `sprites_fdyn.bin` with `dyn_tab`; its hostage-like BOBs, the hostage and
types 2, 14 and 16's bodies, torn per object: two hostages, one a picture ahead of the other, are each
whole, which level 1's rule took for a tear). The vats are checked against the static map until the
vats' display (step 14) draws them.
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_chain [hz_l2_field_jobs {W/fd} {W/R/l2/rc2_l2.rom} {W/R/l2/rc2_l2.labels} {<repo>/build/emu/l2_tour.drive} {0 300 150 300 495 300 735 200 960 250 1150 300 1255 350 2385 400 2420 400 2500 300}]
```
`tools/msxframe.py` (the plan's 4.2 check 6): the tile area of VRAM per level (each cache slot of page
2 against its `TC_TILE` entry, page-0 RAM: 256 slots, 224 in level 2; the atlas's static frames on page
3 against `POOL_lN_field_vram.bin`) instead of level 1's whole VRAM image (which every picture failed:
the cache and the atlas write there); `--field`: the map with its patches and the play-field BOBs of the
list on screen (`fb_vis`, test builds) in the expected picture, so that a level-2 still compares whole.
`hz_l2_still_jobs DIR R FRAMES DRIVE` takes a drive (default `l2_lift`).

At step 13: the field check on the `l2` build (`ENEMY_CAP=0`, the bench's enemies: types 2, 14, 16, the
trolleys, the lifts, the hostages) over `tour`'s windows (the start, types 14 and 16, the four trolley
rides, the drips, the arrest) and `barrel`'s stairs on the three machines: 0 differ in every window but
three cases, none of the play-field frames' own: `2385_fx` (the drive's teleport at 2410 sweeps the view
1,400 pixels in one tick: 85 pictures at tick 2412 with an empty list, the scroll's catch-up), `735_tr`
(5 pixels: a trolley entering at the screen's right edge one picture before its list, which waits for the
other trolley's copy: two late items take two blanks) and `150_tr` (one picture: a 2-piece staged item,
type 16's body with the lift, its second piece started by the main loop during the picture: the guard's
class (3) of step 11). On the product-caps build (`EXTJOY=1 LV_TEST=2`) the same windows: 0 differ on
the three machines. The play-field BOBs of the lists on screen against the bench's draw calls (a scratch
check over the records: 5,467 BOBs exact; missing only in the teleport's sweep, 3 more at the view's
edges, where the list's camera and the tick's differ by a few pixels). Two engine faults found
and fixed: a piece across both the V9958 ring's x 256 and y 256 (four parts) was copied two parts a blank
(the trolleys' top lines a picture ahead, 9-23 pictures a ride on the MSX2+ and the turbo R; `isr.asm`
`isr_fbgo` now chains every part, `fb_cmd2` at EDC0h for three); and a list could go on screen without its
BOBs when the split's uploads readied it and the VBLANK took it before `do_publish` counted the picture
(`fb_tick`, now counted in `publish`; a lift missing for 6 pictures in `barrel`, MSX2). Stills
(`hz_l2_still_jobs` on `tour`, 12 frames, three machines; `msxframe.py --sprites build/msx/sprites
--level 2 --field`): the play area exact in all 36, the tile area clean, sprite pixels exact but where
two objects overlap (msxframe's object order: exact with the SAT's, step 12's note) and at the arrest
(2555) the HUD's can 171 pixels (its model). `rc2_sprlines` over `tour` on the product caps
(`hz_l2_start_jobs ... 110`): 1,125 / 834 / 769 frames with a line above 8 (MSX2, MSX2+, turbo R), all
RoboCop beside a level-1 walker drawn as legs and torso (types 3, 4, 15: 3 + 3 on the lines where the
parts meet, no silhouette among them); step 12's build on the same route 827 (MSX2): not the play
field's, left to milestone 2. Note: `hz_l2_start_jobs` with a time past the drive's end pauses at the
drive's end (`rc2_drive_rom`): the guard's `after time` waits for `set ::pause off`.

At step 14 (2026-10-31, the vats' display: `msx/vats.asm`, `field.asm`'s vat section, `tiles.asm`'s
`get_tile` rule and hooks), **the vats' checks** (the plan's 4.2 check 8 and the rates):
`tools/bstest/vatlog.tcl` (sourced after `load.tcl`) `vl_jobs DIR ROM LABELS ?SECS? ?FROM? ?MACHINES?
?DRIVE?`: from the power-on on DRIVE (default `tour`'s), from level 2's first tick past game frame FROM
for SECS seconds, `rc2_guard` (tears counted) and every vat column `vats.asm` draws (its parts' beam
lines, R#23, its destinations), the time spent in `vat_run` and `vat_prep`, the window's tries and the
V9938's mirrors, into `DIR/vat_<m>.txt` and `DIR/guard_<m>.txt`; `tools/bstest/vatcheck.py DIR` sums
them per machine (columns a second, each column's look changes a second, the CPU's share, the least
margin from the beam to a column ending in the next picture's display, the guard's tears and play-area
commands that are a vat column's) and exits 1 when the beam drew into a vat column (a negative margin or
a guard tear whose command is a vat column's part). The guard's "cmd" lines of a vat column are its
later parts, started while the beam is above the column (each waits for the one before): not tears.
`vl_speed_jobs DIR ROM LABELS ?SECS? ?FROM? ?MACHINES?`: the game frames and ticks reached in SECS seconds
from FROM (`DIR/speed_<m>.txt`: the vats' cost against another build's). `vl_snap_jobs DIR ROM LABELS
FRAMES ?MACHINES?`: `rc2_snap` at the start of each game frame F of FRAMES (`DIR/<m>_gF`) for
`tools/mapcmp.py BENCH DIR/<m>_gF build/msx/level2`, which now takes a vat cell's tile from its column's
look in the snapshot (`vat_disp`'s nibble of the page shown, else `vat_shown`'s; "N vat cells by the vat
rule"), as `tools/msxreal.py` and `tools/msxframe.py` (a map patch first with `--field`) do.
`l2b_fd_setup`'s records hold the vats' RAM (F012h-F0E6h:
`vat_shown`, `vat_disp`, `vat_chg`) and `fieldcheck.py --level 2` checks every vat cell against its
column's look on the page recorded (`vat-look`: a column of two looks, half drawn, or a page whose
nibble is not its pixels') and, when a column's look changes, never to a look older than the one it
showed (`vat-older`; the looks recur every cycle, so only the changes are dated).
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; source {<repo>/tools/bstest/vatlog.tcl}; hz_chain [vl_jobs {W/vl} {W/R/l2/rc2_l2.rom} {W/R/l2/rc2_l2.labels} 25 450] {W/vl/all.done}
python3 -I tools/bstest/vatcheck.py W/vl
```

At step 15 (2026-10-31, the cut at a vat's surface and the arrest scene's view: `cold.asm` `spr_cut`
behind `sprites.asm`'s hook, `level2obj.asm` `t2`'s `v_addx`, `player.asm` `pl_view`), **the cut's and
the view's checks** (the plan's 4.2 checks 9 and 10). `tools/msxframe.py --cut LINE` expects RoboCop's
and the hit spark's sprites to end above screen line LINE (their pixels from it down left out of the
expected picture and counted: "cut at screen line N: K of RoboCop's ... left out"), every other object
whole. `tools/bstest/cutview.py cut SNAPROOT REF.jsonl` takes `hz_l2_still_jobs`' stills on `l2_vat`
(every list from the frames asked), the bench's row of each list's tick (its game frame near the still's
`tick_n`: the game frame starts again after a death), the original's copper line there (`lt1`'s rule:
equal to the bench's own `$10356` on every row of `vat`) and its screen line on the MSX (the line - 1Eh
+ the camera's y - the list's camera y), and runs msxframe with it: PASS when every still with a cut is
exact and the cut left out some of RoboCop's pixels; the stills without a cut are reported (msxframe's
own classes: compare them with the base's). `tools/bstest/cutview.tcl` (sourced after `load.tcl`)
`cv_view_jobs DIR ROM LABELS ?SPEC? ?MACHINES?`: per drive (default `end` from frame 15, `tour` from
2405) and machine, at every tick_start the view the game asks for, `v_addx`, RoboCop's x and the
camera, and at each new list's HUD split its camera, RoboCop's record and its play-field BOBs
(`DIR/view_<name>_<m>.txt`); `cutview.py view DIR [--add 48]` checks the suspect's scene: `v_addx`
steps 0 or 2 up to 48, the view at most 2 px a tick but where it follows RoboCop at his range's edge
(`pv_keep`) or stays at the map's edge, RoboCop within `AX_MIN`..`AX_MAX` but at the map's left edge,
and the suspect's pixels (their columns from the atlas) within the map x the screen shows from the
view's arrival at its target to the arrest. `tour` needs the trace build (`ENEMY_CAP=0`): with the
product's cap the drive's teleports leave an enemy in the one slot and the suspect never comes.
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; source {<repo>/tools/bstest/cutview.tcl}; hz_chain [concat [hz_l2_still_jobs {W/st} {W/R} {36 37 ... 62} l2_vat] [cv_view_jobs {W/cv} {W/R/l2/rc2_l2.rom} {W/R/l2/rc2_l2.labels}]] {W/cv.done}
$PY -I tools/bstest/cutview.py cut W/st build/emu/l2_vat_ram.jsonl
$PY -I tools/bstest/cutview.py view W/cv
```

At step 18 (2026-10-31, the flow into and out of level 2), **the product goes on from the range into
the level-2 briefing and level 2** (`front.asm` `front_brief` at `front_bonus`' end, `rc2.asm` `ml_ev`,
`lv_next`), and after level 2's stages into the level-3 briefing and the title (default 5); `PZ_TEST=1`
shows the briefing after the range, then the title. The flows learnt it:

- **`hz.tcl` `hb_step`** (every Brainstorm flow): after the range's records, `hb_brief_arm` (state 8)
  records the briefing at the next `iv_late` once `fs_n` reaches 170 (`TAG_brief.sc5` and hb_snap's other
  files; notes "brief l2|l3 at"), counts the VBLANKs and HUD splits to its `fe_end` ("brief ... end at":
  `fs_n` there, the screen's length in ticks, 394 and 412 without fire: the scripts' 393 and 411 calls
  and the call that reads the end, the original's VBLs; `fs_done`), then goes on to the title or the new
  game as before (states 2, 4), unless `lv_next` came (`hb_l2_go`): then `TAG_l2g0` (`rc2_snap` at the
  HUD split of level 2's first list with the display on: `tools/msxframe.py ... --sprites
  build/msx/sprites --level 2 --field`, which renders a product snapshot without its sprite records
  now) and, at level 2's game frame 100, "level 2 at tick_n" (the game's state, the HUD's shown digits,
  heads, icon and can, the lost counters) end the job, or run `::hb_l2next` (a job's next steps).
- **`bonuscheck.py --brief l2|l3`** (the record against `msxtext.py`'s render with TEST N, R#0 16h
  R#1 62h, the length, the split at every VBLANK) and **`--level2`** (level 2 instead of a new game, its
  first picture checked (step 22, below), its lost counters 0; with `--range` the range's rating kept:
  `rgcheck.py` `level2=True`). `rgcheck.py` takes the notes' "level 2 at tick_n" line (`--level2`, `--new-game`, or
  as the notes say).
- **`regress.sh check`**: `prod_m2`, `prod_tr`, `p2m_ex`, `two_m2`, `two_title_ex` (the second stage is
  the product's) with `--brief l2 --level2`; `pzt_*`, `solved_*` with `--brief l2`; the `ar_*` range
  records (`rgflow.tcl` `rgx_l2`: `lv_next` instead of `new_game`, level 2's frame 100) with
  `rgcheck.py --level2`, the PZ_TEST=2 ones with `--new-game`; `wp_tr` to level 2's game frame 100;
  `kb_*` (the keyboard product) through the briefing to level 2 (the title after the range no longer
  comes: the `tx_*` jobs compare the title); **`tx_ex`, `tx_f1`, `tx_tr` run the product's whole flow**
  (`np_title_setup`, 5.17 b): level 1, both stages, the level-2 briefing, level 2 to its game frame 100,
  where `np_t_l2` ends the level as F5 would, the statistics, both stages' second visits (Brainstorm's
  passes 100 and 400, the range's pass 1500 in `W/O/np/st_tx_M2/`), the level-3 briefing, then the title
  (exact, against the base's title after Brainstorm) and its game at tick 300 (level 1, SHARP).
- **`flow_l2_end`** (the plan's 4.1 flow reference): `hz.sh l2builds` adds `R/flow/rc2_flow.rom`
  (`EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1` without `LV_TEST`) and `hz_l2` the job `l2_flow_l2_end`
  (`hz_l2_flow_setup`: `drive_end`'s 200 rows, Brainstorm by `pz_fail`, the range by `fr_good`, then
  `rc2_l2_arm` with `l2_end` from level 2's first tick, 259 rows, the lost counters); `hz.sh compare
  --fields analysis/amiga_ram_l2.tsv DIR R flow_l2_end` against `build/emu/l2_flow_l2_end_ram.jsonl`.

At step 19 (2026-10-31, the continue: `front.asm` `front_over` (clears `fo_cont`, sets the key byte as
`high_score_entry`'s start), `front_cont`, `rc2.asm` `ml_ov`, `lv_cont`, `cold.asm` `lv_cfront`, `tc_reset`),
`hz_l2`'s `cont` job is whole again (301 rows, the others' done condition; `hz.sh compare` has no
`cont:109` any more) and, with `over`, runs `hz_l2_cont_arm` (hz.tcl): the 64 KiB at `front_over`'s entry
(`DIR/l2/TAG_over_ram.bin`), the offer's screen at `fs_n` 50 (`TAG_cont.sc5` and hb_snap's files), its
VBLANKs and HUD splits to `fe_end`, SPACE held from its tick 60 (`cont`), the 64 KiB at `lv_cont`'s entry
(`TAG_lvc_ram.bin`), level 2's first picture after it (`TAG_l2g0`), or the new game (notes
`TAG_cont.txt`). New jobs: `cont_fx` and `cont_tr` (the same on the FS-A1FX and the FS-A1GT, traced and
compared: `hz.sh compare` lists them), and `hz_l2_cont_jobs`' `cont_nf` (the offer left alone) and
`cont2` (`hz_l2_cont2_drive`: the lives poked to 0 and vat 0 again at frame 150 after the continue: a
second game over without a credit). A script build's `title` now ends the front end (`front_done`, as
the product's title does at its end) when `front_mode` is set, i.e. after a game over (PIC9 left it set
and the new game waited for lists the VBLANK no longer applied); at the power-on and after the stages it
still does nothing, so that level 1's start in those builds keeps its timing. `hb_step` takes the
intro's and the result's records at the next `iv_late` too, within `fs_n` windows (intro 150-280,
result 80-125, briefing 170-300): `fe_text` sets `fs_ptr` before it clears `fs_n`, and a poll in that
window took the screen before for this one (a keyboard flow on the turbo R lost its stage's trace and
keys that way), or read R#1 inside the split's blank lines (22h).
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_l2 {W/O/l2} {W/R} tr
python3 -I tools/bstest/contcheck.py W/O/l2 cont --fire --gen W/R/l2c/gen      # also cont_fx, cont_tr
python3 -I tools/bstest/contcheck.py W/O/l2 cont2 --again
python3 -I tools/bstest/contcheck.py W/O/l2 cont_nf --no-fire
python3 -I tools/bstest/contcheck.py W/O/l2 over --none
```

At step 22 (2026-10-31, the review's finding 2), **level 2's first picture is checked**, after the flow
(`bonuscheck.py --level2`) and after the continue (`contcheck.py --fire`, `--again`): `bonuscheck.py`
`first_picture` runs `tools/msxframe.py TAG_l2g0 build/msx/level2 build/msx/hud TAG_l2g0.png --sprites
build/msx/sprites --level 2 --field --no-sprites` (the venv's Python, or `--py PY`) and fails on its exit
status: the play area equal to the map with its patches, the vats and the play-field BOBs, every pixel
of it (`--no-sprites` renders it with the sprites off: a level's first list has no SAT published yet,
so its records name objects the screen does not show), the HUD equal to what `hud.asm` records as
shown, the tile cache's slots and the atlas equal to the level's. It also compares the notes' record
("level 2's first picture at": HUD shown, heads, icon, can, jobs) with the game's values: the score's 7
cells and the ammo's 3, the timer's 4 (its value or 07:30), the heads (slot k: 0 while the lives are more
than k, else 5), weapon 0's icon 3, the can full, no HUD job. `hz.tcl` `hb_l2_snap_arm` follows the main
program's HUD work (`hud_frame`'s entry to its return into `mainloop` or `hud_keep`) and `hb_l2_snap`
passes over a split that comes while it runs (a digit cell recorded as shown before its 16 lines are
written: the record ahead of the VRAM), taking the next one; the notes then end with "splits passed
over while the HUD was drawn: N" (kb_ex: 1). Known-bad cases caught (copies of real records): 16 KiB of
page 2's tile slots zeroed, 64 HUD bytes and 512 play-area bytes flipped, 40 atlas lines zeroed (msxframe
exit 1); a score cell, the heads, the lives or the timer (09:58) changed in the notes' line.

At step 16 (2026-10-31, milestone 2's acceptance: the display's remaining glitches, the vats'
variant), **the guard judges what the screen shows** (`tools/openmsx_rc2.tcl` `rc2_guard`):
- **The display off, the palette black.** While the game has the display off (R#1's BL bit as the game
  last wrote it, `::rg_r1`: not the HUD split's own blank) nothing is judged, and while the play field's
  palette is all black (the fades of a death, of a level's end, a start's fade in) no reg, cpu, cmd or
  tear is counted (pal and vbl still are). The writes that turn the display off and on (`dsp_off`,
  `display_on`: R#1's display and VBLANK interrupt bits, R#0's line interrupt bit alone) are logged as
  `display off at line L`, `display on`, `line interrupt off`, not counted; once on, the VBLANK and split
  bookkeeping starts again from the second VBLANK interrupt (the first comes at once: the VDP's F was set
  while the interrupt was off). A death's restart (the screen redrawn with the display off for about
  10,500 lines) read as tens of tears, commands, register, CPU (the SAT written by that first interrupt
  under the black palette) and VBLANK events; it now reads clean (`vat` from frame 30, three machines:
  reg, pal, cpu, vbl, tear 0; the cmd lines are a vat column's later parts).
- **A tear is a picture that shows a command's lines half old, half new.** `rc2_rg_cend` takes the
  command's lines as written at an even pace from its start to its end (line k of NY done at t0 + (k + 1)
  (t1 - t0) / NY) and, for each picture the beam drew while it ran, a line the beam drew before its write
  as old, after it as new: a tear when one picture has both ("(N lines old, M new)"). Until now any beam
  line between the start and the end over one of its lines counted: a copy that keeps ahead of the beam
  (the V9958's part started in the blank that ended as the beam reached its first line) or one the beam
  passed before it began read as a tear, while a copy across the beam's whole pass did not. The pace is an
  average (the VDP copies faster in the blank): a copy that ends a line or two from the beam may be judged
  either way.
- Effects on the gate's guards: Brainstorm's `guard_*` loses the tears of `bs_board`'s copies under the
  black palette (its verdict needs reg, pal, cpu, vbl 0 only, as before); the range's stay 0.

The engines' changed cells wait for the window between the HUD split and the VBLANK (`scroll9958.asm`
`swr_one`, `scroll9938.asm` `s38_redraw`: no 16 x 16 copy into the page shown during the play area), and
the HUD's timer cells change in one frame (`hud.asm` `hud_digits`). **The vats' variant** `VAT_TICK=1`
(`tools/mkrom.py`; `tiles.asm` `vat_tick` after each game tick, `sprites.asm` `feed_vdp` in the window
while a column is ready; off by default: the product's bytes as before) is measured with the step-14 jobs,
`vl_speed_jobs` now also counting the pictures (lists put on screen) and taking a drive: tour from 450 and
850, and standing at vat 0 (`build/emu/l2_still520.drive`: tour's joystick bytes to frame 520, none after,
no teleport, tour's pokes; `python3 -I -c "l=open('build/emu/l2_tour.drive').read().split('\n');
open('build/emu/l2_still520.drive','w').write('\n'.join([l[0][:1042]+'00'*(len(l[0])//2-521),'']+l[2:]))"`)
from 540.
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; source {<repo>/tools/bstest/vatlog.tcl}; hz_chain [concat [vl_jobs {W/t450} ROM LABELS 25 450] [vl_jobs {W/s540} ROM LABELS 20 540 {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT} <repo>/build/emu/l2_still520.drive] [vl_speed_jobs {W/sp450} ROM LABELS 25 450]] {W/v.done}
python3 -I tools/bstest/vatcheck.py W/t450          # columns a second, each column's draws a second, tear 0
```

### 5.23 Level 2's sound checks and the cheat (step 21 of its plan)

The plan's 4.3. **`fxlog.tcl`** logs, from an arming point on, every write the game makes to the sound
chips (the PSG's R0-R13 by its latch, R14/R15 left out; every store to 9800h-98FFh with where it went:
the cartridge's SCC when page 2 shows the cartridge with bank 3Fh there, another slot's SCC when page 2
shows another slot, else none; the OPLL's) and the engine's events around them: a request queued by
the main program (`sq_put`, Q), `snd_stop`'s parts (`mus_stop` Y, `sq_mute` Z), the VBLANK's sound work
(`snd_frame` V to `sf_back` W) with what it takes from the queue (`sq_sfx` S, `sq_gun` G, `sq_stop` X)
and its tick (`sqf_t` T), each game frame's start (F), the text screens (`fe_text` B to its return b),
the title's music (M: the model's end) and, from the job's start, every tick of the stages' tunes with
the chips' state (`tn_tick` U, `tns_go` N). Its first line (I) holds the engine's RAM C000h-CFFFh, its
last (E) the same at the end. **`fxcheck.py`** replays the log on a model of the engine (`sndplay.asm`,
the PSG player; `music.asm`'s effects on the SCC with their noise on the PSG: `fx_start`, `fx_tick`,
their readers and outputs, routine for routine; the data read from the ROM: `sccfx.bin`'s table and
streams in `SCCFX_BANK`, `fx_waves`, `snd_sfx` and its streams in `BANK_INPUT`, `GUN_TAB`) from the
I line's state, and wants: each event's writes exactly the model's, in order; every request taken by
the next VBLANK, in order, none dropped; a tick at exactly the VBLANKs the divider gives (60 Hz: five of
six); the engine's variables at the end equal (197 bytes); in a text screen no write after its own
stop. It reports per effect its starts, the refusals of the priority rule (`$1822C` as each player
implements it) and the starts played whole (every part to its stream's end, not cut by another start
or a stop); with `--bench`, the requests the main program queued in each game frame against the
reference's (`$B31` ... `$B2C`, frame_keys' order; the gun's opening once a life, at its first effect 3).

```sh
sh tools/bstest/hz.sh fxbuilds R          # l2, l2x (NO_SCC_INT=1), l2n (NO_SCC=1), l2c, l2cn, pz1, pz2, pz1n, pz2n
```
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_chain [fxl_jobs {W/fx} {R}] {W/fx/all.done}     (26 jobs, < 1 min)
```
```sh
python3 -I tools/bstest/fxcheck.py check W/fx/d_tour_scc.txt R/l2/rc2.rom R/l2/rc2.labels --bench build/emu/l2_tour_ram.jsonl --expect scc
python3 -I tools/bstest/fxcheck.py visits W/fx/pz1_scc.txt W/fx/pz2_scc.txt      # Brainstorm's PZM and the range's FRM, visit 2 against 1
python3 -I tools/bstest/fxcheck.py selftest W/fx/d_end_scc.txt R/l2/rc2.rom R/l2/rc2.labels
```

| Job (`fxl_jobs`) | Build, machine | Checks |
|---|---|---|
| `d_<drive>_<k>`: tour, vat, mine, end, t1left, trolley | `l2` (k scc: the cartridge's SCC), `l2x` (ext: `NO_SCC_INT=1`, an SCC cartridge in slot B), `l2n` (psg: `NO_SCC=1`), C-BIOS_MSX2 | `check --bench build/emu/l2_<drive>_ram.jsonl --expect k`; the drive's trace (`d_<drive>_<k>_trace.txt`) against the reference, `tracecmp.py --ram --fields analysis/amiga_ram_l2.tsv` |
| `cont_<k>` | `l2c`, `l2cn`: the cont drive (301 rows) | `check`: the offer `txt_cont` silent after its stop |
| `brief_<k>` | `l2`, `l2n` from the power-on: LV_TEST's briefing to 1 s after it | `check`: `txt_l2_brief` silent |
| `pz1_<k>`, `pz2_<k>` | `pz1`, `pz2` (scc), `pz1n`, `pz2n` (psg) from the power-on, no script: Brainstorm and the range of visit 1 or 2 left alone, then the next level's briefing to 1 s after it | `check` (the briefing silent; the model ends at the title's music); `visits pz1_k pz2_k` |

`cheat.tcl` (`ch_job DIR ROM LABELS`, a `CHEAT=1` build, no script, C-BIOS_MSX2): the title, SPACE,
level 1 to its game frame 100, F5 (row 7 bit 1) held 0.5 s, the statistics, the stages left alone, the
level-2 briefing, level 2 to its game frame 100, its energy poked to 40h, F4 (row 7 bit 0), F5, the
statistics, both second visits, the level-3 briefing and the title; `DIR/cheat.txt` notes each step with
`$804F`, `$8032`, `$16D0` and the energy; snapshots `l1_100`, `l1_end`, `l1_stats`, `l2_100`, `l2_low`,
`l2_full`, `l2_end`, `l2_stats` (`tools/msxframe.py ... --level N`) and `title` (SCREEN 8).

### 5.24 Level 2's acceptance in one place (the plan's 4.1-4.4, as it stands)

The checks of 5.21-5.23 in one run, as milestone 2's acceptance ran them (level 2's step 16) with
milestone 3's sound and set-ups added: what accepts level 2 as a whole (`docs/LEVEL2.md` 4; its last
results: 4.6). `W` is a fresh folder outside `build/msx`; `<repo>` the repository's root; `PY` =
`~/.venvs/msxports/bin/python`. Build from a worktree of the commit under test when the shared tree
holds another agent's uncommitted edits (5.21), with the build data copied, and regenerate
`build/msx/text.inc` and `puzl.inc` there with the commit's own converters when it is older than
their changes (`docs/level2/HANDOFF.md`, steps 18 and 20).

**The base.** `l2base.sh check` compares level 1, the title, Brainstorm and the range with a base
(5.21). The base in use is main `6082d3a`'s (the range's two cameras), recorded with level 2's harness
and made with `l2base.sh base` (the commands: `docs/level2/HANDOFF.md`, "Level 2's base made again");
`sh tools/bstest/l2neg.sh REPO BASE W OUT` runs the gate's negative controls on copies of a passing
run's records (19 controls at the base: 11 mutated copies FAIL, the 8 unmutated PASS). Against it two verdicts read as CPU time since steps
14-16 (the still `m2_g1490`, one PSG tick: `docs/LEVEL2.md` 8.1); a base made from an accepted level-2
tree ends that.

**1. The builds** (about 2 minutes; every log: "build OK", z80asm's 12 known warnings only):
```sh
sh tools/bstest/l2base.sh builds W                                   # the gate's 25 (regress.sh's, lock24, lock24p)
sh tools/bstest/hz.sh l2builds W/L2R                                 # l2 l2s l2f l2p l2o l2c flow (4.1)
sh tools/bstest/build.sh W/GX/l2/rc2_l2.rom EXTJOY=1 LV_TEST=2       # the product's caps: start, field, view
sh tools/bstest/build.sh W/GXA/l2/rc2_l2.rom EXTJOY=1 LV_TEST=2 VAT_ANIM=1                          # the same, the vats drawn
sh tools/bstest/build.sh W/L2A/l2/rc2_l2.rom EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2 VAT_ANIM=1    # the vats as built (check 8)
sh tools/bstest/build.sh W/GV/l2/rc2_l2.rom EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2 VAT_ANIM=1 VAT_TICK=1   # the vats' variant
sh tools/bstest/hz.sh fxbuilds W/FX                                  # 4.3's nine builds (5.23)
sh tools/bstest/build.sh W/cheat/rc2.rom CHEAT=1                     # 4.3's cheat run
sh tools/bstest/variants.sh W/V; python3 -I tools/bstest/l2base.py banks W/V > W/banks_variants.txt
```
`variants.sh` builds 55 option sets (the night review's 41, 7 `LV_TEST=2`, 5 `CHEAT=1`, 2
`VAT_ANIM=1 VAT_TICK=1`): 52 build, `DEMO_ACTORS=2`/`5` and `DEMO_HUD=1` overflow the fixed area. `l2base.py banks`
lists every set's free bytes (the fixed area's lowest: `p_pzdiag`, `DIAG=1 PZ_TEST=1`).

**2. The chain** (one openMSX: `msx_local_boot` headless; a private MSX-AI MCP session,
`python3 -I tools/bstest/mcpd.py DIR &` and `MCPD_DIR=DIR sh tools/bstest/mx.sh NAME 'TCL'`, when the
in-process target is another agent's; one `msx_local_cmd` a line, `L` = `W/L2R/l2/rc2_l2`, `LA` =
`W/L2A/l2/rc2_l2` (the vats drawn: `VAT_ANIM=1`), `X` = `W/GX/l2/rc2_l2`, `E` = `<repo>/build/emu`):
```
source {<repo>/tools/bstest/load.tcl}; source {<repo>/tools/bstest/l2base.tcl}; source {<repo>/tools/bstest/vatlog.tcl}; source {<repo>/tools/bstest/cutview.tcl}
set J [hz_l2_jobs {W/O/l2} {W/L2R} tr]                                                          ;# 4.1: 25 jobs
set J [concat $J [rgr_jobs {W} all] [l2b_jobs {W}]]                                             ;# 4.4: the gate, 227 jobs
set J [concat $J [hz_l2_start_jobs {W/start} {X.rom} {X.labels}]]                               ;# 4.2 check 1
set J [concat $J [hz_l2_field_jobs {W/fd} {X.rom} {X.labels} {E/l2_tour.drive} {1 300 150 300 495 300 735 200 960 250 1150 300 1255 350 2140 260 2385 400 2420 400 2500 300}]]
set J [concat $J [hz_l2_field_jobs {W/fdb} {X.rom} {X.labels} {E/l2_barrel.drive} {70 300 300 300}]]   ;# check 2
set J [concat $J [hz_l2_objs_jobs {W/objs} {W/L2R} {tour end vat trolley barrel drone}]]        ;# check 3
set J [concat $J [hz_l2_still_jobs {W/st} {W/L2R} {10 200 520 760 1000 1230 1300 2395 2456 2464 2472 2555} l2_tour]]   ;# check 6
set J [concat $J [hz_l2_still_jobs {W/cut} {W/L2R} FRAMES l2_vat]]                              ;# check 9: FRAMES every game frame 36-62
set J [concat $J [cv_view_jobs {W/cvt} {L.rom} {L.labels} {tour 2654 2405 end 259 15}] [cv_view_jobs {W/cv} {X.rom} {X.labels} {end 259 15}]]   ;# check 10
set J [concat $J [vl_jobs {W/vl/450} {LA.rom} {LA.labels} 25 450] [vl_jobs {W/vl/850} {LA.rom} {LA.labels} 25 850] [vl_jobs {W/vl/1250} {LA.rom} {LA.labels} 25 1250] [vl_jobs {W/vl/2130} {LA.rom} {LA.labels} 20 2130]]
set J [concat $J [vl_jobs {W/vl/s540} {LA.rom} {LA.labels} 20 540 {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT} {E/l2_still520.drive}] [vl_jobs {W/vl/vat} {LA.rom} {LA.labels} 20 30 {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT} {E/l2_vat.drive}]]   ;# check 8
set J [concat $J [fxl_jobs {W/fx} {W/FX}] [list [ch_job {W/cheat} {W/cheat/rc2.rom} {W/cheat/rc2.labels}]]]   ;# 4.3
hz_chain $J {W/all.done}
```
Step 16's chain (without 4.3's jobs) ran 345 jobs with 0 time outs; `build/emu/l2_still520.drive` is
made by 5.22's one-liner ("At step 16"). The vats' variant: the same `vl_jobs` and `vl_speed_jobs` on
`W/GV/l2` (5.22).

**The vats' checks since the rest of the game's step 1** (2026-10-31: the product's vats are static,
`VAT_ANIM=0`): check 8 (`vl_jobs`, `vatcheck.py`, the rates) and the field check's `vat-look` and
`vat-older` classes concern the display of `VAT_ANIM=1` builds (`LA` above, `W/GXA/l2` for the field
windows, `W/GV/l2` for the variant). On the product's builds (`W/L2R`, `W/GX`) `vatcheck.py` reports 0
columns drawn and the field check expects every vat cell at the map's own tile (`tools/mapcmp.py`
`vat_look` None for a column with no nibble on the page shown: the summary's "vat columns seen at the
map's own tile"), which proves the static image. The vats' cost: `vl_speed_jobs` on `L` against `LA`
(`docs/level3/HANDOFF.md`, step 1).

**3. The verdicts**, once `W/all.done` exists:
```sh
sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv W/O/l2 W/L2R      # 4.1: "level 2: PASS (23 traces)", lost 0
for t in cont cont_fx cont_tr; do python3 -I tools/bstest/contcheck.py W/O/l2 $t --fire --gen W/L2R/l2c/gen; done
python3 -I tools/bstest/contcheck.py W/O/l2 cont2 --again
python3 -I tools/bstest/contcheck.py W/O/l2 cont_nf --no-fire
python3 -I tools/bstest/contcheck.py W/O/l2 over --none
sh tools/bstest/l2base.sh check W BASE                                               # 4.4: "l2base: PASS" (regress's 45 verdicts, level 1's records)
for d in W/fd/* W/fdb/*; do [ -d "$d" ] && $PY -I tools/bstest/fieldcheck.py "$d" build/msx/level2 "$d.png" --level 2; done   # check 2
python3 -I tools/objcmp.py BENCH_NAME.jsonl W/objs/NAME_M.txt --sprites build/msx/sprites_l2.json --rows N   # check 3 (BENCH: 5.22, "At step 12")
$PY -I tools/msxframe.py W/st/M_gNNNN build/msx/level2 build/msx/hud OUT.png --sprites build/msx/sprites --level 2 --field   # check 6, each still
$PY -I tools/bstest/cutview.py cut W/cut build/emu/l2_vat_ram.jsonl                   # check 9: "cut: PASS"
$PY -I tools/bstest/cutview.py view W/cvt; $PY -I tools/bstest/cutview.py view W/cv  # check 10: "view: PASS"
for d in W/vl/*; do python3 -I tools/bstest/vatcheck.py "$d"; done                     # check 8: exit 0, the rates
```
- Check 1: `W/start/start_<m2|fx|tr>.txt` (the guard's counts: tear, pal, cpu, vbl 0; reg and cmd are
  the classes of 5.22 at steps 11 and 16; patcheck 0 bad; satcheck 1 at game frame 0 at most; the lost
  counters 0; the lines above 8, which 4.2 check 7 does not meet yet).
- Checks 11 and 13: the briefings' and the offer's records are regress's (`bonuscheck.py --brief`,
  `--level2`) and `contcheck.py`'s; level 2's first picture in each flow, `W/O/<flow>/<TAG>_l2g0`, which
  `bonuscheck.py --level2` and `contcheck.py --fire`/`--again` check themselves from level 2's step 22
  on: `tools/msxframe.py ... --level 2 --field --no-sprites` exits 0, and the notes' HUD record holds the
  game's values (5.22, "At step 22").
- 4.3: `fxcheck.py check` on every `fxl_jobs` log (the table of 5.23), `fxcheck.py visits`, `selftest`,
  and `W/cheat/cheat.txt` with its snapshots.
- 4.4's set-ups (`msx_local_shutdown` first: the tool runs its own openMSX):
  `python3 -I tools/msxmatrix.py W/R/prod/rc2.rom --labels W/R/prod/rc2.labels --home <msx-ai>/.openmsx-home --jobs 1`
  (10 of 10 PASS) and the same with `--no-title` on an `LV_TEST=2` build; `make test` (the 4 known
  failures only).
- Not in the chain yet: the Pico+'s bank-select log over `tour` (4.4: at most 53 distinct banks at
  8000h and A000h, a speed target) and level 2 on C-BIOS_MSX2+ at 5.37 MHz.

### 5.25 The game completed and the high scores (the ending's step)

`docs/ENDING.md`; the step's account: `docs/level3/HANDOFF.md`, "Step 3". `W` a fresh folder outside
`build/msx`, `PY` the venv's Python.

**The builds**: `sh tools/bstest/build.sh W/b/NAME/rc2.rom OPTIONS` for `e1` (`END_TEST=1
LV_CARRY=10050:2:0:1`), `e1t` (the same with `TAG=8`), `e2` (`END_TEST=2 LV_CARRY=10050:0:1:1`),
`e2n` (`END_TEST=2 LV_CARRY=10050:0:0:1`: no credit), `e2s` (`END_TEST=2 LV_CARRY=7500:0:1:1`: a tie
with the last entry, no entry), `cheat` (`CHEAT=1`) and the product.

**The sound** (no emulator): `$PY -I tools/bstest/frsnd/endsim.py <repo> W/b/prod/rc2.rom
W/b/prod/rc2.labels`: every tick of CMP's 4,916 and 60 after them (`tn_left` 0 at tick 4,916, no write
after), the name entry's effects against `$1822C`'s rule, on the four chip sets at 50 and 60 Hz, and on
the R800 without an OPLL write: "all: PASS". A one-bit change in a stream of the image fails it.

**The screens** (one chain, the MCP's openMSX or a private session):
```
source {<repo>/tools/bstest/load.tcl}
set J {}
lappend J [ge_job {W/E} e1 {W/b/e1/rc2.rom} {W/b/e1/rc2.labels} {R O B O C O P 2 X BS KP9 Z RET}]
lappend J [ge_job {W/E} e1t {W/b/e1t/rc2.rom} {W/b/e1t/rc2.labels} {RET} C-BIOS_MSX2]
lappend J [ge_job {W/E} e2 {W/b/e2/rc2.rom} {W/b/e2/rc2.labels} {BS SPACE M S X RET} Sony_HB-F1XDJ_128K_Lite 1]
lappend J [ge_job {W/E} e2n {W/b/e2n/rc2.rom} {W/b/e2n/rc2.labels} {A RET} Panasonic_FS-A1FX 1]
lappend J [ge_job {W/E} e2s {W/b/e2s/rc2.rom} {W/b/e2s/rc2.labels} {} Gradiente_Expert20_64K 1]
lappend J [ge_job {W/E} e1tr {W/b/e1/rc2.rom} {W/b/e1/rc2.labels} {A RET} Panasonic_FS-A1GT]
lappend J [ge_job {W/E} e2tr {W/b/e2/rc2.rom} {W/b/e2/rc2.labels} {K E Y P A D KP0 KP1 RET} Panasonic_FS-A1GT 1]
hz_chain $J {W/E/all.done}
```
then `endcheck.py W/E TAG "KEYS" [OPTIONS] --gen W/b/NAME/gen` for each: `e1` and `e1tr` without
options, `e1t --tag 8`, `e2` and `e2tr --over`, `e2n --over --no-offer`, `e2s "-" --over --score
7500`: "endcheck TAG: PASS" (the previews `W/E/TAG_*.png`: look at them).

**The flows**: the product's whole flow now reaches the ending after the level-3 briefing: `np.tcl`
`np_t_poll` arms `ge_ret_arm` once the stages' records are taken (they remove every breakpoint), so
the tx jobs' title is recorded after the ending; `regress.sh check W B flows` judges it against the
base's title after Brainstorm (the picture, the registers that show, the palette identical; the
music `titlecmp2.py --unheard`: the SCC's registers that differ are the ones neither run hears).
`cheat.tcl` goes through the ending to the title. Builds with a script skip the ending and the entry,
so every EXTJOY flow (level 2's traces, the continue checks) is the base's.

### 5.26 Level 3's drives, its test start and the flow into it (level 3's step A)

`docs/LEVEL3.md` (the plan: 3.8, 4, step A); the step's account: `docs/level3/HANDOFF.md`, "Step 4 (plan
step A)". `W` a fresh folder outside `build/msx`, `PY` the venv's Python.

**The test start.** `tools/mkrom.py LV_TEST=3` builds a ROM that starts level 3 at power-on, once, as
`LV_TEST=2` starts level 2 (5.22): level 1's set-up, then `front.asm` `front_l2test` (alias
`front_l3test`) writes `LV_CARRY`'s score, lives, credits and rating and AG `$8050` = `LV_TEST` - 1 (2),
shows the level-3 briefing (`txt_l3_brief`), then `lv_next` starts level 3 (`lv_go` with A = 2). No
level-1 tick runs before it: `tick_n` is level 3's game frame and `rc2_drive_rom` drives these builds
unchanged. `hz.sh l3builds W/R` builds `W/R/l3/rc2_l3.rom` (`EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=3`).

**The drives and references** (`tools/l3drives.py`, the bench's `game --level 3`: `Level3Bench`'s direct
start, carry `10050:2:0:good`): `tour3` (1,401 rows: the street from the start, the beams of floors 25,
35 and 20, the lifts L0, L1 and L2 up and down, the roof, by teleports, energy and lives poked every 25
frames) and `beam` (501 rows: a beam's death at frame 100, the restart). `python3 -I tools/l3drives.py
make`, `refs`, `check`, `path REF` (RoboCop's place and the slots' types every N rows). `cont3`'s drive
exists; its reference came with step B (5.28: the fault at PC `$FDB8` after its game over was the drive's).

**The stubbed references** (`tools/bstest/l3stub.py OUT [--drop NAME]`, `l2stub.py`'s twin): the
bench with the port's stubs written into the main code before `level_init` (`--pre-poke`): the 19 new
types `moveq #-1,D0 / rts` at their handlers, the three deaths of types 21, 22 and 33 `rts`, `act_20`
`bra.w $9C76` (the port's `ao_acts` entry 8 is `ao_look`). A step that ports a routine drops its stub
there and in the port. Against the plain references a level-3 trace differs from row 0: `act_20` runs
in `level_init`'s map-object pass (the map objects' collision slot 1, entry 12's), and the stubbed
types from frame 2 (type 39's bomb, type 47's camera mode), as level 2's step 7 found for its routines.

**The traces** (`hz.tcl` `hz_l3`, `hz_l2_drive`'s jobs with the lost counters): `tour3` on
C-BIOS_MSX2, `tour3_fx` on the FS-A1FX, `beam` on C-BIOS_MSX2, with `tr` `tour3_tr` on the FS-A1GT;
`analysis/amiga_ram_l3.tsv` (778 fields: level 2's set with level 3's code-area records, its code-area
words DD74h-DD7Fh and its flags `$15C4`, `$16A6-$16A9`, `$16B4`, `$16D4`, `$16D9`, `$16DA`; `$D583` and
`$E9F5` commented until step B chooses how the port keeps them):
```
sh tools/bstest/hz.sh l3builds W/R
python3 -I tools/l3drives.py refs                 # build/emu/l3_*_ram.jsonl (Unicorn: about 30 s)
python3 -I tools/bstest/l3stub.py W/stub          # the stubbed ones
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_l3 {W/O/l3} {W/R} tr
sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l3.tsv W/O/l3 W/R --refs W/stub   # "level 3: PASS (4 traces)"
```
`hz.sh compare --fields` picks level 3's jobs, traces (`l3_<job>.txt`) and lost-counter lines from the
field file's name (`*_l3.tsv`).

**The start and the stills** (`hz_l3_still_jobs W/O/st W/R ?FRAMES? ?DRIVE?`: `hz_l2_still_setup` with
`BANK_L3`, on the three machines): `pos.txt` (RoboCop at (1184, 784), `lv_cur`'s logic bank `BANK_L3`),
then `$PY -I tools/msxframe.py SNAP build/msx/level3 build/msx/hud OUT.png --sprites build/msx/sprites
--level 3 --field` (level 3's own pool frames since step C, 5.27; 160 tile-cache slots). The first picture (game frame 0) is exact on the three machines; stills on the beams
differ at the beams' cells only (their looks change every tick: the RAM's patches are a tick ahead of the
picture) and, at a lift, step B's two-part look is missing.

**The flow** (`cheat.tcl`, a `CHEAT=1` product build): the title, level 1, F5, the stages, the level-2
briefing, level 2, F5, the stages' second visits, the level-3 briefing, **level 3** to its game frame 100,
F5 (AG `$8050` = 3: `rc2.asm` `ml_ev`'s `ml_end`), the game completed (`front_ending`, the name entry by
RETURN, the table) and the title. The regress gate's `tx` flows (`np.tcl` `np_title_setup`) do not end
level 3: `np_t_l2`'s breakpoint, which takes `BANK_L3` too, is set at level 2's game frame 100 and gone
by level 3 (the stages' result record, `hz.tcl` `hb_result_rec`, removes every breakpoint), so level 3
plays without input until the game over; then PIC9, the name entry when the score enters the table
(`ending.tcl` `ge_ret_arm`'s RETURN), the offer left to time out and the title, whose record and
comparison hold either way. The flow that ends level 3 and reaches the game completed is step D's
`np_l3flow_setup` (5.29): it asks the end itself at level 3's game frame 100 (`np_t_l3`).

### 5.27 Level 3's sprites and play field (level 3's step C)

`docs/LEVEL3.md` 3.5-3.6 and 3.10 (as built); the step's account: `docs/level3/HANDOFF.md`, "Step 5 (plan
step C)". `W` a fresh folder outside `build/msx`, `PY` the venv's Python, `R` = `W/R` with `hz.sh
l3builds W/R`.

**The pool and the catalogue**: `python3 -I tools/bobcatalog.py level3 --drawn build/emu/cov_level3.json
--drawn build/emu/l3_frames_drawn.json` (212 frames; a coverage frame the REA tables do not explain is
listed), then the Makefile's `msxsprites.py ... --l3-bobs ... --l3-ram ... --l3-pal ... --l3-remove
msx/level3_frames.json`: `sprites_l3.json`, `sprites_l3_field.{bin,inc}`, `sprites_l3_field_vram.bin`,
`sprites_l3_fc.bin` (the frame cache), `sprites_l3_bobs.png`. `tools/msxchooser.py` has a level-3 section.
`python3 -I tools/bstest/pooldiff.py OLD/sprites build/msx/sprites`: levels 1-2's index entries against an
older pool resolve to the same records, patterns and colour rows (the pool grown in place).

**The field check** (`fieldcheck.py --level 3`: level 3's frames from `msxframe.py`'s `FieldLooks(3)`, its
frame cache's and the white copies, a list entry's bit 7; judged as the frame itself):
```
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; source {<repo>/tools/bstest/l2base.tcl}; source {<repo>/tools/bstest/l3field.tcl}
python3 -I tools/bstest/l3poses.py W/poses.tcl          # (set ::lf_len 60 in it: the six phases in 360 ticks)
msx_local_cmd: hz_chain [lf_jobs {W/lf} {W/R} {W/poses.tcl} 2 1100] {W/lf/all.done}
$PY -I tools/bstest/fieldcheck.py W/lf/m2 build/msx/level3 W/lf/m2.png --level 3   # and fx, tr
```
`set ::lf_mul N` slows the parts' frames down, `::lf_dx` is the walk's pixels a tick (0: the enemy stays
where the camera puts it); a POSES file with `set ::lf_phases {{none {}}}` injects nothing (the windows
the level reaches by itself: `tour3` from frames 2 and 600, 0 differ on the three machines at step C).
`W/lf/<m>/fc.txt`: the frame cache's copies (count, emulated microseconds, the longest) and the lost
counters. **The start check**: `hz_chain [lf_start_jobs {W/sc} {W/R} 42] {W/sc/all.done}` (with POSES
as its fourth argument the scripted enemies run under the guard).

### 5.28 Level 3's logic (level 3's step B)

`docs/LEVEL3.md` 3.3-3.4 and 3.11 (as built); the step's account: `docs/level3/HANDOFF.md`, "Step 6 (plan
step B)". Every routine of level 3 is ported: `tools/bstest/l3stub.py`'s table is empty and the plain
references are the ones to compare with (no `--refs`).

**The drives and references** (`tools/l3drives.py`, energy and lives poked every 25 frames, no god mode):
`park` (1,201 rows: the street from x 1000 firing, the trucks and type 21 shot, frames 40-240; floor 35
under the turrets 41 and 40 from x 600, 250-600; the car park's ground floor from x 1700, 600-1100),
`boss` (1,401 rows: the roof's left end for type 47's mode 1, the roof from x 900 firing; Cain comes at
about 125, falls into the car park at 260; floor 20 to its end, act_20's piece opens at 600; floor 30
leftwards in mode 2, the second piece at 1000; floor 40 rightwards until Cain falls onto the ground floor
at 1400), `kill` (1,861 rows: boss's route without fire, RoboCop on the ground floor from 1500 firing left:
Cain dies at about 1765, the end count, the level's end at row 1860) and `cont3` (401 rows, carry
`0:0:1:good`: the beam's death with no life left, fire held at the death's end, row 149; the continue,
level 3 again from row 150).

**The builds**: `hz.sh l3builds W/R` builds `W/R/l3/rc2_l3.rom` and `W/R/l3c/rc2_l3c.rom` (`LV_CARRY=0:0:1:1`:
cont3's game over with a credit).

**The traces** (`hz_l3`): `tour3`, `park`, `boss`, `kill` on C-BIOS_MSX2 and the FS-A1FX (`_fx`), `beam` on
C-BIOS_MSX2, `cont3` (and `_fx`) on the l3c build through `hz_l2_cont_setup` (the offer taken by SPACE as
level 2's `cont`); with `tr` all five on the FS-A1GT (`_tr`): 16 traces. `analysis/amiga_ram_l3.tsv` has
780 fields: `$D583` and `$E9F5` compared through `tools/tracecmp.py`'s field option `xor=` (the port keeps
those patched bytes XOR'ed with the image's 3 and 42h, so that AC_VARS' zero at the power-on reads as them).
```
sh tools/bstest/hz.sh l3builds W/R
python3 -I tools/l3drives.py refs                 # the six references (Unicorn: about 1.5 min)
msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_l3 {W/O/l3} {W/R} tr
sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l3.tsv W/O/l3 W/R   # "level 3: PASS (16 traces)"
```

### 5.29 Level 3's checks 3-8: Cain, the end, the sound and the continue (level 3's step D)

`docs/LEVEL3.md` 4 and 3.12 (as built); the step's account: `docs/level3/HANDOFF.md`, "Step 8 (plan step
D)". `W` a fresh folder outside `build/msx`, `PY` the venv's Python, `R` = `W/R` with `hz.sh l3builds W/R`
and `hz.sh l3fxbuilds W/R` (`l3x`, `l3n`, `l3cn`), `<repo>` the repository's root. One chain (one
`msx_local_cmd` a line, or a private session's `mx.sh`), after `source {<repo>/tools/bstest/load.tcl};
source {<repo>/tools/bstest/l2base.tcl}; source {<repo>/tools/bstest/l3field.tcl}`:
```
set J [hz_l3_jobs {W/O/l3} {W/R} tr]                                                   ;# check 1 and cont3's records (check 8)
foreach {nm drive from n} {parka l3_park 40 500 bossb l3_boss 625 400 killa l3_kill 1550 700 killb l3_kill 1745 600} {
    set J [concat $J [lf_jobs "W/lf/$nm" {W/R} {W/poses_none.tcl} $from $n {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT} $drive]] }   ;# check 3
set J [concat $J [lf_start_jobs {W/sc} {W/R} 400 {} kill 1861]]                       ;# checks 4-5: the guard over kill
set J [concat $J [hz_l3_still_jobs {W/st} {W/R} {1700 1760 1770 1779 1781 1783 1800 1855} l3_kill]]   ;# check 4's stills
set J [concat $J [fxl_l3_jobs {W/fx} {W/R}]]                                            ;# check 6
lappend J [np_job f3_ex Gradiente_Expert20_64K np_l3flow_setup {W/np} {W/prod/rc2.rom} {W/prod/rc2.labels}]   ;# check 7 (and _fx, _tr)
lappend J [ge_kill_job {W/ke} {W/R} C-BIOS_MSX2 {}]                                     ;# check 7 (and _fx, _tr: machine, suffix)
lappend J [ge_l3over_job {W/ov} ov_ex {W/l3o/rc2_l3o.rom} {W/l3o/rc2_l3o.labels} {C A I N RET} Gradiente_Expert20_64K]   ;# check 7
hz_chain $J {W/all.done}
```
`W/poses_none.tcl` is `set ::lf_len 60; set ::lf_phases {{none {}}}` (nothing injected: the real logic);
`W/prod` the product, `W/l3o` `build.sh W/l3o/rc2_l3o.rom LV_TEST=3 LV_CARRY=10050:0:1:1` (no script: no
life, a credit, a score that enters the table). `lf_start_jobs`' guard ends at its SECS, or wait: the drive
pauses the machine at its last row and the guard's emulated seconds stop there; a job that wants the guard
over the drive alone ends it then (`rc2_rg_end` after cancelling its `after time`; step D's chain did that
from an `after realtime` loop). The verdicts:
```sh
sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l3.tsv W/O/l3 W/R            # check 1: "level 3: PASS (16 traces)"
$PY -I tools/bstest/fieldcheck.py W/lf/NAME/M build/msx/level3 OUT.png --level 3          # check 3, each window and machine
$PY -I tools/msxframe.py W/st/M/gNNNN build/msx/level3 build/msx/hud OUT.png --sprites build/msx/sprites --level 3 --field
python3 -I tools/bstest/fxcheck.py check W/fx/d_kill_scc.txt W/R/l3/rc2_l3.rom W/R/l3/rc2_l3.labels --bench build/emu/l3_kill_ram.jsonl --expect scc
python3 -I tools/bstest/fxcheck.py check W/fx/cont3_scc.txt W/R/l3c/rc2_l3c.rom W/R/l3c/rc2_l3c.labels --bench build/emu/l3_cont3_ram.jsonl --expect scc
python3 -I tools/bstest/fxcheck.py check W/fx/brief3_scc.txt W/R/l3/rc2_l3.rom W/R/l3/rc2_l3.labels --expect scc
python3 -I tools/bstest/bonuscheck.py W/np f3_ex2 --result time --range time --brief l3 --level3 --gen W/prod/gen
python3 -I tools/bstest/endcheck.py W/np f3_ex2 RET --score S --gen W/prod/gen        # S: the score at the end (f3_ex2_end.txt)
python3 -I tools/bstest/endcheck.py W/ke kill - --script --score S
python3 -I tools/bstest/endcheck.py W/ov ov_ex "C A I N RET" --over --score 10050
sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l3.tsv W/ke W/R kill kill_fx kill_tr   # the won level's traces
for t in l3_cont3 l3_cont3_fx l3_cont3_tr; do python3 -I tools/bstest/contcheck.py W/O/l3 $t --fire --level 3 --gen W/R/l3c/gen; done   # check 8
```
- **`fxl_l3_jobs`** (`fxlog.tcl`): kill and park on the three chip sets (the cartridge's SCC, an SCC in slot B,
  the PSG), boss on the SCC, cont3 on the SCC and the PSG with the offer taken as `hz_l3_jobs`' cont3
  (`hz_l2_cont_setup`), the level-3 briefing on the SCC and the PSG.
- **`np_l3flow_setup`** (`np.tcl`): the product's whole flow as `np_title_setup` (EXACT 1), with level 3
  recorded after the level-3 briefing (`hz.tcl` `hb_l2_go` with `::hb_l3rec`: `TAG2_l3g0`, "level 3 at
  tick_n" at its game frame 100), its end asked there (`np_t_l3`: the stages' records remove `np_t_l2`'s
  breakpoint, so the other flows reach level 3 and play it until a game over), the game completed recorded
  under TAG2 by `ending.tcl` `ge_arm` (`::ge_nopause`: its end does not pause the flow), the name entry
  left blank by `ge_ret_arm`'s RETURN, the title recorded as `np_title_setup`'s.
- **`ge_kill_job`** (`ending.tcl`): kill's drive on the l3 build, its trace as `hz_l3`'s job `l3_kill`
  (`_fx`, `_tr`), then the game completed in a script build (no entry, no title: the job ends at the new
  game; `endcheck.py --script`). **`ge_l3over_job`**: a game over in level 3 (RoboCop put into floor 25's
  beam at its game frame 30), PIC9, the entry, the table, the offer taken (`endcheck.py --over`); its end
  notes `ac_flash` (`$F826`).
- **`contcheck.py --level 3`**: level 3's lists by their lengths, no vats, every frame-cache place empty at
  `lv_cont`'s entry (PIC9's G7 overwrote page 2, the cache's lines; the continue's `fe_text` emptied it), the
  first picture `TAG_l3g0` (`bonuscheck.py` `first_picture(level=3)`). `hz.tcl` `hz_l2c_poll` takes the
  offer's record only once the text pointer moved after `front_over` (an `LV_TEST=3` build's briefing ends
  where `txt_cont` starts).
- `tools/recframes.py` reads `rc2_jumprec`'s records only (the field check's carry 1,301 more bytes); the
  field check is the coherence check of the play field (a picture of a big item behind its list, or torn,
  differs), `msxframe.py`'s stills that of the sprites (every sprite pixel exact).

## 6. The whole suite in order

1. `sh tools/bstest/regress.sh builds W`; once a milestone the base: `regress.sh base B`, its
   records (`rgr_base_chain {B} {B/base.done}` in the MCP's openMSX), `regress.sh basecheck B`.
2. `msx_local_boot`; `source {<repo>/tools/bstest/load.tcl}`.
3. `rgr_chain {W} all {W/all.done}`: every emulator check of 5.2-5.10, 5.12's blank, 5.17 a-g's
   flows, 5.18 and 5.19 (207 jobs, about 7 minutes on 2026-10-27; 208 since the exact title of
   5.21). Wait for `W/all.done`.
4. `sh tools/bstest/regress.sh check W B`: every verdict, "regress: PASS".
5. `msx_local_shutdown`; the matrix (5.13) on `W/R/prod`, `W/X/p2m` and, with `--no-title`, `W/R/pzt`
   and `W/X/pzt2`; `sh tools/bstest/variants.sh` (5.15) against the base's; `make test`.
6. The checks the chain does not run: `hz6_time` (5.11), `hzp_setup` (5.12's PAUSE), `hudcheck.py`
   against the commit before a change (5.6), 5.17 g's other speed jobs, `c8f_chain` for
   Brainstorm's test candidates (5.17 h), `rgc_chain` and `regress.sh cand` for the range's
   (5.20), the range's recordings (5.19).
7. Level 2 as a whole: 5.24. Its chain holds 3's jobs (`rgr_jobs W all`) with level 1's records
   (`l2b_jobs`), and its `l2base.sh check` runs 4's verdicts.

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
  - Built at level 2's step 20 (`docs/LEVEL2.md` 3.9): visit 2 shows Ellen, and `check_all.sh`
    checks `solve2` and `fuzz2` with `stepcheck.py --visit 2` (`msxpuzl.Puzl(data, (1, 2))`,
    `render(state, cursor, 2)`). The records of a build before it (Murphy on visit 2) fail those
    stills: check them with their own commit's `tools/bstest/`.
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
- **`hz.sh builds`** with `SRC=` (an export of `6e62c74`) gave the six suite images of the night
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
counts since `ff249f6`, and the final checks saw it move), `turborpause` (`hzp_*`),
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


## 12. Performance campaign 2's kit (`tools/bstest/perf2/`)

The measurement and gate scripts of `docs/PERF2_PLAN.md` (5.4's gates), from the campaign's
analysts (m_l3, m_l2, a_field, a_flash, a_scroll, a_sprites, a_logic, a_loop, v_gain), with every
address taken from the build's own label file and ROM and every path an argument. `W` is a run
folder, `R` a builds folder, `BASE` the HEAD records every gate compares with (made once by the
campaign's measurement lane with these very scripts; HEAD here is `a75405c`).

**The session.** A private one (2, 5.24): `python3 -I tools/bstest/mcpd.py DIR &`, then
`MCPD_DIR=DIR sh tools/bstest/mx.sh NAME 'TCL'`; during the campaign under its semaphore (at most two
openMSX of the campaign at once). Load the kit with `source {<repo>/tools/bstest/perf2/load.tcl}`: it
sources `tools/bstest/load.tcl`, `l2base.tcl` and `l3field.tcl` first. From a git worktree (no
`build/`) set `::pf_repo` to the main checkout before sourcing it: the harness and the drives come
from there.

**The builds** (`gate.sh builds R [SRC]`, from SRC: a source tree whose `build/` links to the main
checkout's, 5.3): `R/l3/cap3.rom` (`EXTJOY=1 LV_TEST=3`, the product's options otherwise),
`R/l2/cap2.rom` (`EXTJOY=1 LV_TEST=2`), `R/l1/ext.rom` (`EXTJOY=1`), `R/L/l1|l2|l3/lock.rom`
(`LOCKSTEP=24`) and hz.sh's trace builds in `R/T` (`l3builds`, `l2builds`, `trace`).

**A gate run**: `hz_chain [pf_gate_jobs {W} {R}] {W/gates.done}` (149 jobs; `pf_gate_jobs W R
{speed lock}` for some), then `REPO=<main checkout> sh tools/bstest/perf2/gate.sh all BASE W R`:
each verdict's output in `W/gate_<name>.txt`, its last line `G-NAME: PASS` or `G-NAME: FAIL ...`.
Every verdict judges what BASE holds: a run, window, dump or record W lacks FAILs, as does one cut
short (a job that timed out, a chain that stopped) and a verdict that judged nothing; a deliberate
subset is judged with `--partial` (`PARTIAL=1` for `gate.sh`: the left-out records listed; G-LOGIC
always whole). A job removes its run's old records when it starts (`m3_setup`, `cnt_setup`,
`pf_guard_setup`; the field, lock and logic records are rewritten from their start, and a field check
older than its window's recording is checked again), so a W reused for a later commit never passes
on an earlier run's records.

| File | Side | Inputs -> outputs | Gate |
|---|---|---|---|
| `load.tcl` | Tcl | sources the harness and the kit's Tcl | |
| `m3.tcl` | Tcl | `m3_job NAME MACHINE DIR ROM LABELS DRIVE N ?MODE?`: a drive (N rows from tick 0, `rc2_drive_rom`'s inputs without its RAM dump) -> `DIR/NAME_ticks.txt` (per tick: tick_n, emulated time, counters), `_pics.txt` (per picture: time, tick, fb_hold, the list's game frame, VBLANK), `_pubs.txt`, `_frames.txt` (cadence: wf_n, ticks due, cap), `_fcs.txt` (frame-cache uploads); MODE `flash` adds to each ticks line the BOBs drawn as a colour-15 silhouette in the tick (`bd_mode` with BM_FLASH: shown, all); `cmds` adds `_cmds.txt` (every VDP command) and `_ce.txt`, `full` adds `_samp.txt` (a PC sample every 0.2 ms); `m3_job2`/`m3_job3` stack variants. Probes take no emulated time: a lean run's records equal a full one's | G-SPEED, G-HOLD |
| `win.py` | python | `T0-T1 PREFIX...`; `--table DIR [--json OUT]`; `--gate BASE NEW` -> ticks/s, pictures/s, pictures/s with game progress, held VBLANKs per window (each drive's windows: kill 130-1400, 300-1500, 1500-1765; boss 130-1400; tour3 40-210, 215-540, 545-1065, 1085-1400; park 40-1200; l2tour 20-1590, 2080-2350; l1play 40-1450). FAIL: a window slower than BASE by more than 1 % (400 ticks or more) or 5 % (shorter); for l1play (level 1's play "must stay at 25 ticks/s and 25 pictures/s", its ticks/s at the logic's cap) also its pictures/s or progress pictures/s below BASE's by more than that; a window not reached; a run BASE holds that NEW lacks (`--partial`: not judged) | G-SPEED |
| `holds.py` | python | `PREFIX [FROM TO]`; `--table DIR`; `--gate BASE NEW [--partial]` -> pictures shown after FB_HOLD (fb_hold 8 at `iv_take`: BOBs one picture behind the sprites) per minute over whole drives (kill, boss, tour3, l2tour judged). FAIL: more per minute than BASE; a run that does not span BASE's ticks; a run NEW lacks | G-HOLD |
| `gates.tcl` | Tcl | `pf_speed_jobs`, `pf_field_jobs`, `pf_guard_jobs`, `pf_lock_jobs`, `pf_map_jobs`, `pf_logic_jobs`, `pf_gate_jobs W R ?GATES?` (each `DIR R ?TAGS?`; TAGS `::pf_m4` = C-BIOS_MSX2 m2, Gradiente_Expert20_64K ex, FS-A1FX fx, FS-A1GT tr; `::pf_m3`, `::pf_vdp2` = m2 fx); `pf_fd_setup` (`l2b_fd_setup`'s records plus `holds.txt`: each record's fb_hold), `pf_guard_setup` (the guard from the level's first tick to the drive's end); `pf_logic_jobs`' level-1 jobs run through `hz_l2_drive` (the same trace, plus the lost counters in `DIR/l1/lost.txt`) | all |
| `fieldsum.py` | python (venv for fieldcheck) | `run DIR [--root REPO] [--jobs N] [--check FIELDCHECK]` -> `fieldcheck.py` on every window (`DIR/<win>_<tag>.fc.txt`, `.png`), `DIR/fieldsum.json`; `table DIR`; `gate BASE NEW [--partial]`. Windows: kill300, kill1025, kill1560, boss110, boss300, park40, tour545 (900 records each), l2_tour's 11 of 5.24, level 1's c430, c860, c1490. FAIL: a difference class BASE's window does not show, the pictures after FB_HOLD left out (G-HOLD's); or the window's other pictures with differences beyond 3 x BASE's + 30 (a gross regression a class BASE shows would hide); a window whose check did not cover its records (no summary line: fieldcheck stopped, e.g. a wrong `--root`; fewer checked than level.txt's n: skipped or cut short; a check older than the window's level.txt or holds.txt: recorded again since, which `run` checks again); a window NEW lacks; WARN: a class more than doubles | G-FIELD |
| `guardsum.py` | python | `table DIR`; `gate BASE NEW [--partial]` -> `rc2_guard`'s counts over whole kill and boss drives (cap3), patcheck, sprlines, satcheck. FAIL: more tears, a bad patcheck entry, a drive not driven to its end, a record NEW lacks | G-GUARD |
| `lockgate.py` | python | `BASE NEW [--partial]` -> `tools/dispcmp.py`'s comparison of every LOCKSTEP=24 record (l1cov0 3000 lists, l2tour 1300, kill 900, boss 680; m2 fx), judged up to the first late frame (`.over`) of either run. FAIL: a judged list differs, NEW has fewer lists, a record NEW lacks | G-LOCK |
| `cnt.tcl` | Tcl | `cnt_job NAME MACHINE DIR ROM LABELS DRIVE N ?NAMES? ?MAP?` -> `DIR/NAME_cnt.txt` (per tick, cumulative calls of NAMES: `label` or `label@BANK`), `DIR/NAME_map.txt` (every 100 ticks: 0910h-0FFFh, 1082h-1F9Bh, F500h-F9FFh) | G-MAP, counters |
| `mapdiff.py` | python | `A_map.txt B_map.txt`; `--gate BASE NEW [--ignore FROM-TO] [--partial]` (tour3, park; m2 fx). FAIL: a byte differs (1085h-108Bh never compared; `--ignore 0A33-0AFF` for item 10's row hints); a tick one dump has and the other lacks; a dump NEW lacks | G-MAP |
| `gate.sh` | shell | `builds R [SRC]`; `speed`, `hold`, `field`, `guard`, `lock`, `map` `BASE NEW`; `logic W R` (hz.sh compare: level 3's 16 traces and level 2's 23 named, so a missing one FAILs; level 1's cov1, cov0, cov0_tr; every job's lost counters 0, level 1's from `l1/lost.txt`); `all BASE NEW R`. Environment `REPO`: the checkout with `build/`; `PARTIAL=1`: the verdicts' `--partial` | all |
| `cen.tcl`, `vercmp.py` | Tcl, python | `cen_jobs DIR ROM LABELS DRIVE N ?TAGS?` -> the sprite budget's census per run (`R`, `E`, `C`, `F`, `O` records; labels at 8000h-BFFFh counted while the ROM's `romblocks` debuggable shows a level bank there: `msx/lvshared.asm`'s); `vercmp.py BASE NEW`: 0 differing records, the budget's T-states per run | items 12, 13, 16 |
| `sync3.py` | python | `PREFIX FROM TO` (an m3 run in `cmds` mode) -> the V9938 build's copy end -> sync -> flip timing | item 7 |
| `fl.tcl`, `flcmp.py` | Tcl, python | `fl_jobs DIR ROM LABELS DRIVE N TAG TAGS` -> level 3's flash probe (ticks, pictures with fb_hold, uploads, fb_wants with white entries); `flcmp.py T0-T1 LOG...` | items 3, 8, 14, 18 |
| `pgprobe.tcl` | Tcl | `pg_jobs DIR R ?TAGS? ?WINS?` on flash-1's builds -> `DIR/<win>_<tag>/pg.txt` (each page-path use, each diff's verdict) beside the field records | item 3 |
| `lp.tcl`, `lpan.py` | Tcl, python | `lp_job NAME MACHINE DIR ROM LABELS DRIVE N WINS ?DT?` -> the frame pipeline's events; `lpan.py EV LABELS BANKS_INC` | D2, D3 |
| `m2.tcl` | Tcl | `m2_jobs DIR ROM LABELS DRIVE N ?TAGS? ?DT? ?LIGHT?` -> level 2's ticks, pictures, commands, samples, phase marks and the flash probe (`_flash.txt`: OS_FLASH per slot, the silhouette BOBs drawn per tick) | the level-1/2 flash |
| `flash12.py` | python | `HEAD CONTROL [T0-T1]`: an m3 `flash` run and one of a build whose `bob.asm` draws BM_NORMAL for BM_FLASH -> the flash's whole cost (the time difference), the flash pictures, the cost per flash picture and its share of those pictures' time | the level-1/2 flash |
| `whitechk.py`, `vertrim.py`, `eqtiles.py` | python | `whitechk.py ROM FIELD_L3_INC FC_BANK ATLAS_BANK`; `vertrim.py OLD NEW` (conversions before and after item 1); `eqtiles.py` (no arguments): checks of items 1-3 (unit tests to be) | items 1, 2, 3 |

`tests/test_perf2.py` runs every verdict on made-up records (each passes on equal records and fails on a
mutated copy) and checks the kit's files as `test_bstest.py` checks the harness's.

Examples (`K` = `tools/bstest/perf2`, `B` = the baseline folder):
```
MCPD_DIR=D sh tools/bstest/mx.sh j "hz_chain [pf_speed_jobs {W/speed} {R}] {W/speed.done}"
python3 -I K/win.py --gate B/speed W/speed
python3 -I K/holds.py --gate B/speed W/speed
MCPD_DIR=D sh tools/bstest/mx.sh j "hz_chain [pf_field_jobs {W/field} {R}] {W/field.done}"; python3 -I K/fieldsum.py run W/field --root <main checkout>; python3 -I K/fieldsum.py gate B/field W/field
python3 -I K/lockgate.py B/lock W/lock
python3 -I K/guardsum.py gate B/guard W/guard
python3 -I K/mapdiff.py --gate B/map W/map
REPO=<main checkout> sh K/gate.sh logic W R
python3 -I K/vercmp.py B/cen/cen_l3_kill_m2.txt W/cen/cen_l3_kill_m2.txt
python3 -I K/sync3.py W/kill_m2 300 1500
```
