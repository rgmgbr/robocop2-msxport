# Performance campaign 2: the plan (levels 2-3, Cain, the hit flash)

Agent "plan", 2026-11-01. Base: `level2` at 3b11042 (HEAD 4f8fcb4 differs only in `docs/LEVEL3.md`).

- **`C`**: the campaign's working folder, kept locally as `build/archive/perf_2026-11-01.tar.gz`
  (git-ignored; the run dumps are left out and listed in its `EXCLUDED.txt`).
- **`P`**: the repository.

**Sources.**
- `C/CONTEXT.md`.
- The measurement reports `C/m_l3/REPORT.md` and `C/m_l2/REPORT.md`.
- The analysts' proposals and the verifiers' verdicts (v_rules, v_gain). They are kept in the archive (`plan/agents_journal.jsonl`).
- v_gain's records: `C/v_gain/checks.txt`, `C/v_gain/combined.txt`.
- Section 4's numbers come from `C/plan/combine_plan.py` (output `C/plan/combined_plan.txt`): v_gain's model restricted to the items this plan keeps.

**Measured and estimated.**
- "Measured" means openMSX 21 headless, emulated time, EXTJOY drive builds, with 60 Hz machines:
  - "MSX2" is C-BIOS_MSX2 (V9938);
  - "MSX2+" is Panasonic_FS-A1FX (V9958, Z80);
  - "turbo R" is Panasonic_FS-A1GT (R800).
- The product is a little faster than these builds: 0.3-1 % in level 3, 2-4 % in level 2. The test-only costs are fb_visrec, pub_spr and sb_want.
- Anything estimated says so.

**Kept.** `C` is archived (above), with every prototype, ROM and record named below; this plan is
`docs/PERF2_PLAN.md`.

## 0. Summary

- **Today.**
  - With Cain, the Z80 machines run 6-10 ticks/s: MSX2 6.1-10.2, MSX2+ 8.1-10.3. The turbo R runs 13.9-19.5.
  - The MSX2+ is CPU-bound. The MSX2 has the same CPU load, plus the V9938 scroll's view lag. The turbo R is bound by the VDP and the picture pipeline.
  - The two big CPU blocks are the play-field composition (34-42 % of the Z80's time; `fb_tiles` alone is 19-23 %) and the sprite engine (19-32 %).
- **The hit flash** is expensive only where the hit enemy stands still: Cain on kill's ground floor.
  - There it costs 38 % of the time on the Z80 machines.
  - It takes the turbo R from 37 to 14 pictures a second.
  - On Cain's route it costs only 2-4 %.
  - Levels 1-2 (sprite silhouettes) were not measured. Batch 0 does that.
- **The decision-identical set** (sections 2 and 5, three batches) takes Cain's scenes about x1.3-1.5 on every machine (ticks a second):

  | Scene | MSX2 | MSX2+ | turbo R |
  |---|---|---|---|
  | Cain's route | 7.3 -> 10.4-11.1 | 10.0 -> 14.1-14.6 | 15.0 -> 19.6 |
  | The ground floor, Cain shot | 10.2 -> 13.8-14.4 | 10.1 -> 13.9-14.3 | 19.5 -> 24.0, at about 20 pictures/s |

  The prototyped, measured items (all of batch 1, plus flash-1 and scroll-1 from batch 2), chained, give for Cain's route MSX2 9.4, MSX2+ 13.3, turbo R 19.4.
- **It does not reach 25 ticks/s with Cain on a Z80.**
  - With CAD_MAX 2 that needs an 80-ms frame. The MSX2+'s frame is 250 ms today.
  - The set makes the frame 1.4-1.5x shorter, where 3.1x is needed.
- **The rest is the user's decision** (section 3; measured on batch 1, previews test10-test15):
  - **The cadence cap** (loop-3 or loop-1): MSX2+ Cain's route 12.89 -> 15.77 or 15.76 ticks/s, the boss route 9.73 ->
    12.77 or 12.98, at fewer pictures with progress; loop-1 also the turbo R's Cain's route 18.35 -> 20.41.
  - **The flash's look.** flash-7, counted in game ticks, gives a steady white during a burst on every machine: the
    ground floor MSX2 12.52 -> 18.26 ticks/s, MSX2+ 12.50 -> 16.71, turbo R 22.77 -> 23.88 at 38.4 pictures/s (17.5).
    flash-6: 14.58 / 13.93 / 23.39.
  - **The V9938 lag tolerance** (LAG_X 64): MSX2 Cain's route 8.81 -> 10.44 ticks/s (+18.4 %), the boss route +17.1 %;
    the MSX2+ and turbo R unchanged.

## 1. Where the time goes (measured)

### 1.1 Speed today

Each cell is ticks/s / pictures/s / pictures with game progress per second.

| Scene (drive, ticks) | MSX2 | MSX2+ | turbo R |
|---|---|---|---|
| Cain's route, no fire (l3_kill 130-1400) | 7.26 / 15.9 / 4.9 | 10.04 / 5.8 / 5.2 | 15.00 / 12.2 / 8.5 |
| Cain's route firing, many flashes (l3_boss 130-1400) | 6.12 / 9.7 / 3.8 | 8.07 / 4.3 / 4.1 | 13.87 / 10.4 / 7.6 |
| Ground floor, Cain shot (l3_kill 1500-1765) | 10.18 / 5.5 / 5.3 | 10.06 / 5.4 / 5.2 | 19.54 / 14.0 / 11.0 |
| Level 3's start (l3_tour3 0-1400) | 9.07 / 26.5 / 5.3 | 12.87 / 13.2 / 7.1 | 21.37 / 40.4 / 18.4 |
| Level 2 (l2_tour, teleports excluded) | 19.6 / 19.8 / 13.2 | 23.1 / 16.9 / 15.2 | 24.9 / 45.0 / 24.4 |

Level 2's worst windows:
- MSX2: the trolley rides at 13.3-15.6 ticks/s, the fall to the roof at 13.2.
- MSX2+: the busy windows at 20.5-21.9 ticks/s, with 11.6-12.4 pictures/s.

### 1.2 What limits each machine

**MSX2+: the Z80.**
- The Z80 idles only 0.9-2.7 % of the time, while the VDP is busy 28-35 %.
- A 250-ms frame on Cain's route splits into about 86 ms of composition, 80 ms of sprites, 33 ms of logic (2 ticks) and 33 ms of interrupts.
- Ticks lost on the boss route: 2,662 in all.
  - 812 to CAD_MAX 2.
  - 1,786 because frames are longer than 8 VBLANKs (the `wf_n` clamp).
  - 63 to view lag.

**MSX2: the same CPU load, plus the V9938 scroll.**
- The page builds take 14.6-16.1 % of the time in Cain's scenes. A page build is an HMMM of the shown page shifted by 16 px.
- In level 2 they take 21.9 % of the tour, and 40-46 % of its horizontal windows.
- When a build is late, the view lags and the cadence withholds ticks. This loses:
  - 1,731 of the kill floors' 2,747 lost ticks;
  - 1,738 of the boss route's 3,920;
  - in level 2, the game stops 64 times for 150-495 ms.

**turbo R: the VDP and the picture pipeline.**
- On the boss route the VDP is busy 51.7 % of the time.
- The R800 idles 12 % and polls the VDP another 11.7 %.
- `fb_pend` holds the pictures 45 % of the time.

### 1.3 CPU by block (boss route, % of time; MSX2 / MSX2+ / turbo R)

| Block | Share |
|---|---|
| Field composition (`fb_work`) | 33.6 / 34.4 / 44.4 |
| - `fb_tiles` with its VDP polls | 21.6 / 21.8 / 29.1 |
| - frame cache (`fbb_fc`, `fc_get`, uploads) | 4.5 / 5.7 / 8.7 |
| Sprite engine | 28.7 / 32.0 / 16.9 |
| - `sprites_frame` | 12.9 / 12.9 / 10.0 |
| - `sprites_tick` (the budget) | 11.1 / 12.8 / 4.6 |
| - `bob_flush` | 4.5 / 6.0 / 2.1 |
| Interrupts (VBLANK 4.2, split 3.0-3.5, sound 2.4-4.3, copy starts 0.7-1.9) | 12.1 / 13.3 / 12.2 |
| Game logic (`game_tick` without the field work it feeds) | 9.7 / 13.2 / 8.1 |
| `fb_frame` bookkeeping | 4.4 / 3.3 / 2.7 |
| Scroll engine's idle steps | 3.8 / 0.8 / 0.3 |
| Idle and its polls | 4.6 / 0.9 / 12.0 |

Elsewhere:
- **The ground floor**: the budget takes 15.5-15.7 % and the logic 16 %.
- **tour3**: the beams' and turrets' map-write chain takes 27 % of the MSX2+'s samples in the beams window, and 34 % of the MSX2's on the roof.
- **Level 2 on the MSX2+**:
  - the sprite engine 34.7 %;
  - the logic 25.8 % (17-18 ms a tick);
  - the interrupts 14.2 %;
  - the field 11.3 %.

### 1.4 The VDP

- An `fb_tiles` HMMM needs 0.38-0.40 ms of VDP time but 1.15-1.19 ms of Z80 time: three times as much.
- VDP time by purpose on Cain's route (MSX2 / MSX2+ / turbo R, % of the window):
  - LMMMs of BOB frames: 10.4 / 10.3 / 20.7.
  - Tile HMMMs: 7.3 / 7.1 / 13.0.
  - Copies of composed pieces onto the pages: 6.5 / 6.3 / 11.8.
  - V9938 page builds: 14.6 (MSX2 only).
- Frame-cache uploads take 13-14 ms each, with the VDP idle. There is about one per picture: 4.2 / 5.4 / 9.0 % of the time.

### 1.5 The hit flash (level 3: Cain's white copies)

**kill's ground floor.** Hits come every 4 ticks, so every picture toggles the look.
- A flash picture costs 49 tile HMMMs, 5.6 LMMMs and 3 copies: 61-64 ms of VDP time.
- A picture without a flash costs 14-24 tile HMMMs, 1.3-1.9 LMMMs and 0.9-1.5 copies.
- The no-flash control build (nofl3b) against HEAD, in ticks/s:

  | Machine | No flash | HEAD |
  |---|---|---|
  | MSX2 | 16.43 | 10.18 |
  | MSX2+ | 16.10 | 10.06 |
  | turbo R | 22.38 | 19.54 |

  On the turbo R the pictures go from 37.4 a second without flashes to 14.0 with them.
- A hit costs about 220 ms on the Z80 machines.

**The boss route.** Cain moves, so the flash costs only 1.8 % (MSX2+), 4.2 % (MSX2) and 3.6 % (turbo R). m_l3's longer flash ticks there are a correlation, not the flash's cost.

**Levels 1-2** flash as colour-15 sprite silhouettes. This was not measured. Level 2's worst frames fall in a fire stretch: on the MSX2+, 238 ms, of which `sprites_frame` is 93.6 ms.

## 2. Decision-identical items, ranked

Each item keeps the logic tick for tick and the same pictures; only the timing changes. Gains are in ticks/s, as corrected by v_gain:
- (M) means measured on a prototype.
- (E) means an estimate.

The gate names (G-...) are defined in 5.4. Effort: S = small, M = medium, L = large.

1. **field-1: trim every play-field frame to its opaque pixels.** A converter-only change. Effort S. Prototype: `C/a_field/tools/mktrim.py`, `C/a_field/R/trim.rom`.
   - **Status (batch 1, 2026-11-01).** Level 3: **done**, `e998eb6` (lane W1F; merged into `perf2/batch1` by
     `54da0e0`): 55 of level 3's 66 frames cut, the frame cache 14 -> 11 banks (`BANK_L3`/`BANK_L3B` at 158/159).
     Levels 1-2: **dropped** in the lane: their commit made one turbo R picture of `l2t495` differ (32 px at the
     trolley's top edge, where the ring draws its new column) that HEAD and the lane's other builds do not show,
     for a measured gain of +0.1-0.5 % on `l2_tour` (the patch: `C/w1f/dropped/`). Whoever revives it finds that
     picture's cause first.
   - **Gain (M) on Cain's route.** MSX2 7.26->8.26 (+13.7 %), MSX2+ 10.04->11.69 (+16.5 %), turbo R 15.00->17.87 (+19.2 %).
   - **Gain (E) elsewhere.**
     - The boss route: about +12-14 % on the Z80 machines, +18-20 % on the turbo R.
     - The ground floor: +10 / +16 / +10 % alone, but only +3-4 % on top of flash-1.
     - Levels 1-2: 0-1 % on the Z80 machines; +3-5 % pictures in the turbo R's trolley windows.
   - **Where.** `tools/msxsprites.py` cuts each field frame (`l3_field`, then levels 1-2's) to its non-zero pixels, with even x edges.
     - `field_tab` becomes (x+x0, y+y0, w', h', dx+x0, dy+y0).
     - The frame cache's ROM stores the trimmed pixels.
     - A white copy shares its frame's bounds.
     - `field_look`/`FIELD_HALF` frames add the trim of the frame they show.
     - Levels 1-2's mirrored gunner frames are trimmed on the mirrored pixels.
     - The pool JSON carries the trimmed sw/sh for `tools/bstest/fieldcheck.py` and `tools/msxframe.py`.
     - No engine code changes. `field_tab`'s 7 readers are all in `field.asm` and all take the box. The place table stays as it is.
   - **Conditions.** Level 3 comes in the first commit. Levels 1-2 come in a second commit, merged only after level 1's regression and level 2's field check pass: that part was not prototyped.
   - **Gate.** `vertrim.py` as a unit test: 66/66 frames, normal and white, pixel-identical at their places. romdiff limited to `field_tab` and the cache's banks (and the atlas tables for levels 1-2). Then G-LOGIC, G-FIELD (levels 1-3), G-HOLD and G-SPEED.

2. **field-2: `fb_tiles` by byte arithmetic on the piece's corner, plus R1 (`field_upload` moved to FRONT2).** Effort S. Prototype: `C/a_field/patches/field_proto_full.diff` (it also holds item 8's OTIR loop), `C/a_field/tools/eqtiles.py`, `C/a_field/R/trimtiles.rom`.
   - **Status (batch 1).** **Done**, `5e59ae3` (W1F): BANK_FIELD 8 -> 120 B free in the drive builds before
     item 8; FRONT2 7,026 -> 6,894 in the product. The level-1 power-on, level-2 start, level-3 start and
     continue upload the atlas through `front2_call` (0 frames differ on three machines).
   - **Gain (M).** On top of field-1, Cain's route gains +4.7 / +5.5 / +1.1 %. The two together against HEAD:

     | Window | MSX2 | MSX2+ | turbo R |
     |---|---|---|---|
     | Cain's route | 8.65 (+19 %) | 12.33 (+23 %) | 18.07 (+20 %) |
     | Boss route | not measured | 9.58 (+19 %) | 16.95 (+22 %) |

   - **Where.**
     - `field.asm` `fb_tiles` with a new helper, `ftl_ax`. It issues the same HMMMs in the same order, and writes `fb_cmd`'s constant bytes once per call.
     - `field_upload` (132 B) moves to BANK_FRONT2 (`ending.asm`). Its two call sites in `cold.asm` go through `front2_call`.
   - **Conditions.**
     - Run a level-1 start, a level-2 start and a continue: only level 3 was run.
     - `vat_pg` (F0E7h) is no longer written in VAT_ANIM=0 builds. Exclude it from MSX-against-MSX trace compares.
     - The 132 freed bytes are counted once (5.2).
   - **Gate.** `eqtiles.py` as a unit test, then G-LOGIC, G-FIELD, G-HOLD and G-SPEED.

3. **flash-1: a look-only change (white on or off) takes each piece's background from the page itself.** Effort M.
   - **Prototype.** `C/a_flash/src_p12b/`; `C/v_rules/p12b_field.diff` (`field.asm` against HEAD); `C/a_flash/tools/mkproto.py`, `whitechk.py`, `pgprobe.tcl`, `fl.tcl`, `flcmp.py`.
   - **Gain (M, on HEAD), on the ground floor.**

     | Machine | ticks/s | pictures/s |
     |---|---|---|
     | MSX2 | 10.19 -> 11.80 (+16 %) | 5.56 -> 6.40 |
     | MSX2+ | 10.05 -> 11.84 (+18 %) | 5.45 -> 6.47 |
     | turbo R | 19.47 -> 20.50 (+5 %) | 14.1 -> 15.6 |

   - **Gain (E) on top of field-1/2.**
     - +8-10 % on the Z80 machines.
     - On the turbo R, +3 % ticks and +6 % pictures.
     - 0 on the boss route and park.
     - It applies to any level-3 enemy that stands while shot: type 21's stand, the turrets.
   - **Where (`field.asm`).**
     - `fb_diff` calls a new `fd_lkchk`. It checks that the page's list equals `fb_want` except for bit 7 of the frames.
     - Three flags: `fb_lkf0`, `fb_lkf1` and `fb_lkq`.
       - `fq_go` clears them unless the change is look-only.
       - `fb_step`'s idle point sets them.
       - `fb_init` clears them.
     - `fb_piece` calls a new `fp_lkok`. It requires that the piece is not a marker, that the page's flag is set, that nothing is pending and that `fb_inwin` holds. It then takes the new phase FP_PAGE (7).
     - FP_PAGE runs `fb_pgbg`: page-to-scratch HMMMs per part (`fcp_sp`, `fb_part`), then FP_BOB.
     - The `fwk_ph` dispatch gets the new phase.
   - **Conditions (v_rules).**
     - Add the V9938's pending row (`s38_rq` = FFh) to the pending-draw rule. Today the rule covers only `q_col`/`q_row` and the redraw queue.
     - Find the room by relocation R2, never by aliasing level 2's tables: that aliasing broke the prototype's level 2.
     - Put the RAM where 5.2 says: not at ECFBh, which is logic-1's.
     - Check scrolling windows on both VDPs, with the page-path uses counted. Every MSX2 check so far was on the static ground floor.
   - **Conflicts.**
     - `field.asm` is serial with the rest of the field lane.
     - scroll-1 changes when the queues drain: run an integration gate after both merge.
     - field-6(a) must keep the flag rule.
     - flash-3 and flash-4 build on this item.
   - **Gate.**
     - G-FIELD over 900-record windows, with `pgprobe.tcl` uses above 0 in each window: kill 1560+, boss 110+ and 300+, park, tour3 lifts, kill floors.
     - Then G-LOGIC, G-HOLD (the prototype's 0 -> 7 on boss 110+ lies inside the control builds' 3-5: judge on whole drives), G-GUARD, G-LOCK and G-SPEED (ground floor and boss).

4. **logic-1: skip the beam and turret map writes that would rewrite a cell's own word.** Uses a map-change counter. Effort S. Prototype: `C/a_logic/diffs/p1_logic1.diff`.
   - **Status (batch 1).** **Done**, `1c0a789` (W1L; merged by `b8c538d`), with `mw_gen` bumped in `tiles_init`,
     both masks cleared in `l3_init` and the skip also requiring `atr_lost` 0. The map at every tick's start equals
     HEAD's (review: 4,463 ticks of tour3, park and kill, 0 differ).
   - **Gain (M).**
     - The whole tour3: +3.9 % on the MSX2, +5.9 % on the MSX2+.
     - tour3's roof: +9.3 % / +10.0 %.
     - park: +1.8 % / +2.7 %.
     - The turbo R and Cain: 0.
   - **Where.**
     - `tiles.asm`: `mw_gen` is bumped in `atr_put`'s change path and in `fb_invf`. `cam_cells` is rewritten as `add hl,hl` four times: exact for all values, and the campaign's only `cam_cells` version.
     - `special.asm` `hz_update` ages the masks `mc_prev`/`mc_cur`.
     - `level3.asm` `lt2_off`.
     - `level3obj.asm` `tur_put`; its two callers pass the block in C.
     - `l3_init` clears `mc_cur`.
   - **Conditions.** Bump `mw_gen` in `tiles_init` as well. RAM per 5.2 (59 B).
   - **Gate.**
     - G-LOGIC (hz_l3's 16 traces, hz_l2's 23, level 1's cov0 and cov1).
     - G-MAP (tour3 and park, on the MSX2 and the MSX2+).
     - G-FIELD and G-GUARD on tour3 and park.
     - G-SPEED.

5. **logic-2: the beams' and turrets' tiles looked up at build time (`map_write_t`), and `rd_bit` without loops.** Effort M. Prototype: `C/a_logic/diffs/p2_logic2_on_p1.diff`, `C/a_logic/diffs/mktt.py`.
   - **Status (batch 1).** **Done**, `042965e` (+ `8cabb89`, docs) (W1L): `tools/mapcells.py look_tables` writes
     `gen/tt_l3.inc` and `tt_l3b.inc` at every build; `tests/test_level3_logic.py`.
   - **Gain (M, logic-1 and logic-2 together against HEAD).**
     - tour3: MSX2 9.07->9.66 (+6.5 %), MSX2+ 12.87->14.17 (+10.1 %).
     - The roof: +15.4 / +16.3 %.
     - park: +2.1 / +4.6 %.
     - The turbo R: 0 in ticks, +2 % in pictures.
   - **Where.**
     - The tools emit the beam looks (`lt2_top`, `lt2_left`, `lt2_right` and the off words) and the turret looks as 3-byte entries: the tile from OTILE, plus the attributes. They are generated at build time, not kept as static includes.
     - `tiles.asm` gets the entry `map_write_t` (+6 B) and the new `rd_bit`.
     - `level3.asm` `lt2_putt`.
     - `level3obj.asm` `tpu_w`.
   - **Gate.** As logic-1, plus a unit test that the generated tables equal OTILE's lookup of the original words.

6. **scroll-1: the scroll engines' queued tiles go out in bursts that yield to the field engine.** Effort S.
   - **Prototype.** `C/a_scroll/B/pQ2.diff`. Drop its `cam_cells` part: logic-1's version is the campaign's.
   - **Gain (M, on HEAD).**
     - MSX2: Cain's route +5.4 %, boss +6.3 %, tour3 +5.4 %, level 2 +5.8 % (horizontal windows +5-20 %).
     - MSX2+: kill +2.7 %.
     - turbo R: kill +5.8 %.
   - **Pictures.**
     - All pictures/s fall 9-28 %: the removed pictures repeat a game state.
     - Progress pictures fall 2-3.5 % on the MSX2's boss route and the turbo R's kill route.
   - **Where.**
     - `scroll9938.asm` `s38_work`: the column phase and the pending row in loops. A new `sc_stop38` stops them when `fb_busy` is set, when a field copy waits for the blank (`fb_cq` 1 or 3), or when `fb_pend` is set.
     - `scroll9958.asm` `scroll_work`: `sw_cq`/`sw_row` loop through a new `sw_next` while `sc_stop` allows.
     - `tiles.asm` `fm38_bb`: a hook.
     - +48 B of the fixed area. This needs spr-6 first.
   - **Conditions (v_rules).**
     - On the MSX2 the stale-BOB class rose: FB_HOLD reached went from 0.31/s to 0.60/s on the kill floors, and was 0.49/s on boss.
     - G-HOLD is measured against HEAD with this item on top of batch 1. If it fails, park the branch and either merge it with item 7, or add the rule "no flip while a published picture's items are pending", then measure again.
     - Look at the turbo R's scroll on a recording. If the catch-up looks worse, keep the bursts on the V9938 only; the turbo R's gain then drops to about 0.
   - **Gate.**
     - G-LOGIC.
     - G-HOLD on the MSX2, the Expert, the MSX2+ and the turbo R.
     - G-LOCK on both VDPs.
     - G-FIELD (levels 1-3) and G-GUARD.
     - The 15-machine matrix.
     - G-SPEED, the Expert included.

7. **V9938-SYNC (field-5, the same as scroll-3): the page being built takes its BOB rectangles from the page shown, with one HMMM each.** Effort L. Not prototyped. The priority-only experiment pS gave +3.5 % on boss, but with FB_HOLD at 1.82/s: not acceptable as it was.
   - **Gain (E).** MSX2 only:
     - Cain's route and the boss route: +8-15 % on top of scroll-1.
     - Level 2: +3-5 %.
     - tour3: +2-4 %.
     - The V9958 machines: 0.
   - **Where (`field.asm` `fb_sync`, `fb_step` and the marker `fb_bsync`).**
     - Queue the sync as soon as a build's copy is done.
     - For each `fb_bb` rectangle whose items are complete on the page shown, issue one HMMM from the page shown to the page being built, with the copy's 16-px shift: SX = x - vis_c0*16, DX = x - back_c0*16. "Complete" means: the queue is empty, no redraw is pending inside the rectangle, and no copy of the page's own is waiting or running.
     - Record the built page's list as the list that was copied.
     - Compose only the rest (the new column) as items.
   - **Conditions.**
     - It needs about 100 B of BANK_FIELD. Relocation R3 moves the V9938-only sync code to FRONT2 (or to a new bank) behind a `field_call`-like stub. That adds a bank to the V9938's per-frame bank set: a speed target on page-cache devices only.
     - Never combine it with scroll-4.
   - **Gate.**
     - G-FIELD on the V9938 machines (C-BIOS_MSX2 and the Expert) over scrolling windows: kill floors, the boss route, l2_tour's walks and trolleys. No new difference class.
     - G-HOLD.
     - The flip timing (`sync3.py`: copy end -> next build).
     - G-LOGIC.
     - G-SPEED, with m_l3 B's lost-tick table on the MSX2 and the Expert.

8. **FC-UPLOAD (field-3 merged with flash-2): frame-cache uploads with a tight per-line loop.** Effort S. Prototypes: `field_proto_full.diff` (OTIR) and `C/a_flash/src_p1/` (OUTI).
   - **Status (batch 1).** **Done**, `ffe75d7` (W1F): 49 B of BANK_FIELD (estimated 35), so 71 B stay free in the
     drive builds (112 in the product); 9.1-9.3 us a byte on the Z80 machines, 11.1-11.4 on the turbo R.
   - **Gain (M).**
     - field-3 on top of field-1/2: MSX2+ kill +3.3 % (v_gain puts the real effect at +1.5-2 %); turbo R boss +1.1 %.
     - flash-2 alone on the boss route: +1.3 / +1.9 / +2.5 %. Per byte: 12.6 -> 8.5 us (MSX2), 13.4 -> 9.2 us (MSX2+), 12.4 -> 11.0 us (turbo R).
   - **Where (`field.asm` `fc_get`, at `fcg_ln`).**
     - Set R#14 = 5 once. An assembly-time check proves every `L3_FC_PLACES` entry lies in page 2 lines 128-255.
     - Per line: the address with two OUTs between DI and EI; the next line's address is +128.
     - The bytes go out through the fixed area's `outi32` chain, called twice a line. Split an odd byte count B as n1 = B>>1 and n2 = B-n1, with the offsets 64-2*n1 and 64-2*n2 computed once per upload. field-1's even-x trims produce odd counts, and an odd offset jumps into the middle of an OUTI.
     - Optional: the same loop for `fb_dyn`'s smoke uploads (`fdy_ln`).
   - **Gate.**
     - G-VRAM: `rc2_count_too_fast` is 0 on the three machines and the Expert, and the cache places' VRAM after uploads equals the ROM's frames.
     - G-FIELD with flashes (boss).
     - G-LOGIC.
     - G-SPEED (boss).

9. **field-7: stage a band of pieces as one piece, up to 128 px wide.** Effort M.
   - **Gain (E).** +2-3 % on the Z80 machines and +1-2 % on the turbo R, after field-1/2. Per composition: 3 to 4 fewer tile commands and 1.5 fewer LMMMs.
   - **Where.** `field.asm` `fb_piece`, `fb_stage`, `fst_done`, `fst_place` and `fst_slot`.
     - Find every place that assumes 64-px pieces: `fb_piece`'s clamp, `fb_lastp`, `fcp_next`, the staged pieces' records.
     - A band stays within 128 px (`ftl_ax`'s signed byte).
     - The scratch's single-piece path stays 64 px wide.
     - VAT_ANIM=1 builds keep the old staging.
   - **Order.** Before flash-4. field-9 is deferred.
   - **Gate.** G-FIELD (the torn and old classes) on boss and kill on the three machines, then G-GUARD (beam crossings), G-HOLD and G-SPEED.

10. **scroll-2, parts (b) and (c) only: a window filter for changed cells, and a per-row patch hint.** Effort M. Parts (a), (d) and (e) are logic-1/2's.
    - **Gain (E), on top of logic-1/2.**
      - tour3 on the MSX2+: +3-6 % (the whole drive +3.5 %).
      - The MSX2: +1-3 %.
      - The turbo R and Cain: 0.
    - **Where (`tiles.asm`).**
      - `fb_invf` tests the cell against the three field caches' windows (`fb_cache`) and calls `fb_inval` only for a cell inside one. logic-1's `mw_gen` bump stays outside this filter.
      - A "last patch found" hint per row lives in MP_ROW's tail at 0A33h-0AFFh. First verify that no level's map uses row 51 or above. The hint is checked before walking the row's chain in `map_write` and `get_tile`, and cleared in `tiles_init`.
      - It needs 60-90 B of the fixed area, so it comes after spr-6.
    - **Gate.**
      - G-LOGIC (levels 1-3) and G-MAP.
      - G-FIELD on the beams' cells: a changed cell is shown at most one picture later, as today.
      - G-SPEED on tour3's windows, and the counters (`cnt.tcl`).

11. **TILE-LOOKUP (field-4 together with scroll-6): one cell lookup per row, and an inline command write in the tile burst.** Effort M.
    - **Gain (E).** +1.5-2 % on the MSX2 and the MSX2+; about 0 on the turbo R. scroll-6's remainder (`fb_fill`, `draw_tile`) adds +0.3-0.5 % in level 2.
    - **Where.**
      - `field.asm` `fb_tiles`: for each row of cells, map the map row's bank at 8000h once, with `act_8000` saved and restored as `fc_get` does. Read each cell's tile there, falling back to `get_tile` when the row has patches (MP_ROW).
      - Write R#32-R#46 inline under `cmd_lock`: one poll, DI, R#17, EI, OTIR.
      - `tiles.asm` gets a row variant of `get_tile`/`tile_src` in the fixed area.
    - **Fix (v_rules).**
      - A tile-cache miss inside the burst (`tc_load` -> `tc_upload`) maps the tile sheet at 8000h and does not put the map back. Map the row bank again after every `tc_load`, or compare `act_8000` per cell.
      - `rowtab` addresses are A000h-based: subtract 2000h at 8000h.
      - The inline read must equal `get_tile` exactly: the patch chain, and VAT_ANIM's vat rule.
    - **Gate.**
      - A unit test: the cell tiles equal `get_tile`'s over every level's map.
      - G-FIELD, G-LOGIC and G-SPEED.

12. **spr-6 (an enabler): the give-way moves into `lvshared.asm`.** It covers `ft_total`..`ftg_end`, `ft_live` and `ft_map`: about 550 B. Effort M.
    - **Status (batch 1).** **Done in a revised form**, `630452d` and `90ee7b7` (W1S; merged by `b79bac3`). With
      the whole give-way in the level banks the turbo R ran its ground floor 4 % slower (the fixed area runs from
      its internal RAM, the level banks from the cartridge), so the per-candidate walks stay in the fixed area
      and the level banks hold 496 B (the per-give and per-run code, `bu_order`, the cut). The lowest option set
      gains 322 B (29 -> 351; 348 at the merged tip with logic-1/2's -3), not about 530; all 61 sets build.
    - **Gain.** None (about 100-150 T-states more per budget run). It frees about 530 B of the fixed area. The lowest option set (p_pzdiag: 29 B free) needs that room for every fixed-area item. It adds no bank to the per-frame set.
    - **Where.**
      - `msx/lvshared.asm` is assembled into every level bank at the same address. Free bytes: L1 874, L2 1,429, L3 3,867.
      - A fixed-area trampoline of about 20 B maps `lvl_bank` at A000h explicitly: the sprite pools sit at A000h during `sprites_frame`.
    - **Gate.**
      - G-BUILD.
      - The census (`vercmp.py`) identical.
      - G-LOGIC and G-LOCK.
      - The product started from the title on the three machines.

13. **spr-1 and spr-4: object walks bounded by `fl_last`, and budget micro-changes.** Effort S. Prototype: `C/a_sprites/patches/spr_bundle_loops_budget.diff`.
    - **Status (batch 1).** **Done**, spr-1 `33a8a62`, spr-4 `58d0ecf` (W1S). `ft_orn` at EDFCh-EDFEh (the
      fallback, no RAM watch needed); the band test in `tests/test_sprite_pool.py` (144 compositions). At the
      merged tip: census 0 differing records on the FS-A1FX (kill 878 runs, l2_tour 906) and on C-BIOS_MSX2's
      l2_tour; budget T-states a run -8.1 % on kill, -12.1 to -12.9 % on l2_tour.
    - **Gain (M).**
      - Level-2 pictures: +3.4 % on the MSX2, +5.1 % on the MSX2+.
      - Cain's ticks: +0.5-1.5 %, at the noise level.
      - Budget T-states per run: -2.7 to -3.6 %.
      - The turbo R: 0.
    - **Where (`sprites.asm`).**
      - spr-1: `fl_last` bounds `rows_sync`, `sat_build` (through `sb_end`), `bg_r`, `ln_fill`'s BOB walk, `obj_ecs` and `cam_follow`. `obj_want` is removed.
      - spr-4: `ln_fill` clears three lines a turn; RoboCop's first counted version is stored, not compared; `ln_add` gives way from `ft_line` down; a new counter `ft_orn` of droppable layers.
    - **Conditions.**
      - +42 B and +97 B of the fixed area: after spr-6.
      - RAM per 5.2. `sb_end` is not at F170h. E553h-E555h is used only after a RAM watch proves it free.
      - A unit test in `tests/` that RoboCop's bands never overlap (all 250 compositions). Keep it out of the converter, which batch 1 changes for field-1.
      - A product-mode SAT check (`rc2_satcheck` from the title), because the drive builds keep `sat_build`'s full walk.
    - **Gate.**
      - The census (`vercmp.py`): 0 differing records (kill 878 runs, l2_tour 906).
      - G-LOCK with `rc2_satcheck`, `rc2_patcheck`, `rc2_sprlines`, `rc2_sprvram` and `rc2_overlines`.
      - G-LOGIC.
      - G-SPEED on l2_tour and kill.

14. **flash-3: flash-1's pending-draw rule per piece, not global.** Effort S. Check first.
    - **Gain (E).**
      - The MSX2's ground floor: about +3 % after field-1/2. p12 measured the upper bound without any rule, which is unsafe.
      - The MSX2+: 0.
      - The turbo R: up to +1.5 %.
    - **Where.** In `fp_lkok`, a cell blocks the page path only if it is:
      - waiting in RD_Q (`rd_bits`, in the 16x20 view window, with aliasing);
      - in the V9958's pending column or row (`q_col` with rows `q_col_row`..`q_col_end`, `q_row`);
      - in the V9938's `s38_rq`.
    - **Check first.** An offline checker over recorded queues must prove that the per-piece test equals "no pending draw meets the piece". p12, without any rule, produced stale ring cells, so an off-by-one shows as a glitch.
    - **Gate.**
      - G-FIELD over windows with scrolling and with animated cells under BOBs: kill floors 300-1500, tour3 lifts, boss 110+. Count the page-path uses.
      - G-SPEED on the MSX2's ground floor.
      - +30-40 B of BANK_FIELD.

15. **field-6: bookkeeping.** Effort M.
    - **Gain (E).** After field-2: +1-2 % on the Z80 machines with Cain, +0.5-1 % in level 2, about +0.5 % on the turbo R.
    - **Where (`field.asm`).**
      - (a) `fb_diff` queues one rectangle per owner. The union still meets `fq_fits`' four-piece rule against other owners, and keeps flash-1's `fq_go` flag rule.
      - (b) `fb_rpiece`, `fb_part`, `fq_go`, `fq_fits`, `fb_clip` and `fb_inwin` stop calling `fb_cmp`. Use an inline `sbc` only on map coordinates, never on the ±4000h sentinels.
      - (c) `fb_frame` skips `fb_wants` when `bob_flush` has not refilled `fb_new`. The flag is set at `fb_init` and at the level start; 1 B of RAM.
    - **Gate.** G-FIELD (the hold and order classes), then G-LOCK, G-LOGIC and G-SPEED (kill and l2_tour).

16. **spr-7, spr-2, spr-3 and spr-8: small sprite-engine items.** Effort M each.
    - **Gains (E).**
      - spr-7 (the plan): +1-1.4 % on the MSX2+.
      - spr-2 (`bob_flush`'s loops): +1 % in level 2, +0.3-0.5 % in level 3.
      - spr-3 (SAT and colour rows): +1 % pictures in level 2.
      - spr-8 (band masks in the composition headers): +0.4-0.7 % on the Z80 machines.
    - **Where.**
      - `sprites.asm`: `pend_build`'s fast loop, the `pc_r` skip, commits and releases; `sat_park`, `sbo_lp`, `pc_rows`.
      - `bob.asm`: `bf_claim` as a bit set, a kept identity count, `bf_hide`, `bob_begin`'s clear.
      - spr-8 changes the ROM format: `tools/msxsprites.py`, `tools/msxframe.py` and the pool checks.
    - **Conditions.**
      - spr-7 must keep the slot choices identical; otherwise use campaign 1's gated LOCKSTEP compare.
      - spr-3 must park exactly the entries no run takes, and keep the y rule (216 -> 215).
      - spr-7 needs 110-170 B of the fixed area: after spr-6.
    - **Gate.**
      - G-LOCK, `objcmp.py` and the rc2 sprite checks.
      - G-LOGIC and `make test`.
      - pooldiff/romdiff: spr-8 is expected to differ.
      - G-SPEED.

17. **logic-4 and logic-6: level 2's per-tick overheads.** Effort M + S.
    - **Gain (E).** Level 2 on the MSX2+: +1.2 % from logic-4 and +0.9-1.4 % from logic-6. Level 3: +0.2-0.3 %.
    - **Where.**
      - `mapobj.asm` `ao_lp` uses y-cell masks made by `tools/cellmasks.py`: L1 104 B, L2 78 B and L3 26 B in their banks.
        - Take the mask again after `act_10` moves the camera.
        - Restore `ao_x`, `ao_y` and IY when the last candidate is skipped.
      - `plmove.asm` `pl_lift`: return NC at once when $168C is 0.
      - `special.asm` `sp_update`: the trolley test first.
      - `hits.asm` `pl_hits`: the test order, byte-neutral (LC1 has 24 B free).
    - **Gate.**
      - Unit tests: the masks are supersets of the exact window.
      - A RAM watch on `objl_ram`'s y (+10/+11) over the drives.
      - G-LOGIC (levels 1-3), G-MAP and G-SPEED (l2_tour).

18. **flash-4: successive look toggles of the same item reuse its staged pieces.** Effort M. Check first. It comes after flash-1 and field-7.
    - **Gain (E).** The turbo R's ground floor: +8-12 % pictures, about +2 % ticks. The Z80 machines: +0.5-1.5 %.
    - **Where.**
      - A "last staged item" record holds the page, the rectangle and a valid flag. Any other composition, cell item, `fb_cfind` or `fb_stage` clears the flag.
      - `fp_lkok` checks the record, and a hit skips the page-to-scratch HMMMs.
      - About 50 B of BANK_FIELD and 10 B of RAM.
    - **Gate.** G-FIELD on kill 1560+ (900 records) on the three machines, with a reuse counter, and G-SPEED (the turbo R first).

19. **field-10: `fb_fill` skips the per-cell tests when the cache holds every cell of the piece.** Levels 1-2. Effort S.
    - **Gain (E).** +0.5-1 % in level 2's item windows.
    - **Room.** About 20 B of BANK_FIELD: the last claim on that bank.
    - **Gate.** Level 2's field check, G-LOGIC and l2_tour's speed.

20. **loop-7(a), optional: inline the hottest `bank_8000`/`bank_a000` calls.** Under 1 %. Only if fixed-area bytes remain at the end.

### Deferred

These are not in section 4's numbers. Reopen one only with its check.

- **field-8: dedicated places for the legs frames (FC_MAX 16).** +1.5-2.5 % on the Z80 machines, +3-4 % on the turbo R.
  - The VRAM does not add up. Page 2 lines 160-231 give 72 lines, and lines 232-255 are the explosion slot. The white copies shown together with Cain's other parts need places too.
  - Reopen it only with a place layout that includes every white copy, and a proof that frames shown together never share a place.
- **field-9: a kept band background.** +4-6 % on the Z80 machines. It halves the staging area, `fb_inval` must reach the window, it needs 150 B of BANK_FIELD, and it conflicts with field-7.
- **field-11 (the same as flash-5): uploads that overlap commands.** turbo R +1.5-2.5 %. It needs bookkeeping of which places each queued or running command reads.
- **scroll-4: lazy V9938 margin rows.** MSX2 level 2 +5-8 %. `fb_inwin` would then treat stale margin rows as valid, and item 3 and item 7 read those rows. Reopen only with per-page valid bits in `fb_inwin`.
- **logic-3: per-row change counters.** tour3 +1-2 %. It needs a page-aligned RAM table that does not exist. Make it exact with logic-1's 16-bit guard.
- **spr-5 and spr-9.** +0.5-2 % on boss. Two related variants measured slower, they overlap spr-4, and spr-9 needs a replay checker.
- **scroll-5: the scroll engines to FRONT2.** Only if the fixed area runs out after spr-6. It adds FRONT2 to every frame's bank set, and level 3 already uses 57 banks against the Pico+ page cache's 53.

### Dropped

- **spr-10.** It diffs against the set on screen, not against the target set's last SAT, which gives a wrong SAT. `q_sat` is not on the turbo R's critical path anyway.
- **flash-8.** The budget runs again at every hit anyway, because the spark appears in the same tick.
- **logic-5.** +0.2 %, within the noise.
- **logic-7.** A tiny gain, and LC1 has 24 B free.
- **loop-6: a third picture buffer.** It adds one picture of input latency, which would be the user's decision. No VRAM is free for a third sprite set, the effort is XL, and it gives 0-2 % on the Z80 machines.
- **loop-7 (b) and (c).** They move the HUD split's calibrated timing, or risk tears.
- **spr-11 and scroll-8.** They break standing rules: sprite pieces vanish, or 2-3x more stale-BOB pictures. They are not offered to the user.

## 3. Options for the user's decision (what the player would see)

D4-D6's numbers are ticks/s / progress pictures/s, on top of the full decision-identical set (realized estimate;
`C/plan/combined_plan.txt`). D1-D3 are measured on batch 1, and the user's previews built (below).

**Measured on batch 1** (D1-D3; lane dprev, 2026-11-01): openMSX headless, emulated time, the `EXTJOY` drive builds
with the product's options plus the option (`C/dprev/R`), one m3 lean run per drive and machine (`C/dprev/N/<set>/speed`)
against batch 1's (`C/integ/N/speed`); MSX2 = C-BIOS_MSX2, Expert = Gradiente_Expert20_64K, MSX2+ = Panasonic_FS-A1FX,
turbo R = Panasonic_FS-A1GT. Each cell: ticks/s / pictures/s / progress pictures/s, batch 1 -> **option** (the change in
ticks/s). The user's previews: test10-test15 (`C/dprev/preview/NOTES.txt`).

**D1. The hit flash's look: the complaint.** Batch 1 shows one white picture for each hit. With hits every 4 ticks, the
shot enemy alternates white and normal every picture. The Amiga shows white 1 frame in 4 at 25 Hz.
- **Keep it** (`FLASH_LOOK` 0, test12).
- **flash-7: a steady white during a burst** (`FLASH_LOOK=7`, test11). An enemy is white in the game tick of a hit and
  the 3 ticks after it, and every hit starts the 4 ticks again: hits at most 4 ticks apart keep it white (Cain's on the
  ground floor come every 4). Counted in game ticks, so it looks the same at every frame rate: a single hit shows 2
  white pictures at 2 ticks a picture, 4 at 1 tick a picture (the turbo R often). A hit in a skipped tick is still
  inside its 4 ticks at the tick shown, for frames of up to 4 ticks (`tools/mkrom.py` refuses more).
  - Cost: none in the fixed area, which has 22 B more free than without the option (no held hit, no frame-end
    loop); LC1 5 B.
  - The first flash-7 (`82c94a5`, measured on HEAD) counted pictures: white in the hit's picture and the next one. On
    the turbo R, at about 1.5 ticks a picture, Cain's hits came 3-4 pictures apart and the hold lapsed (58 look changes
    on the ground floor, 23.5 pictures/s); the tick-counted hold (Wd1's experiment `C/wd1/exp`, now flash-7) is steady.
- **flash-6: at most one white picture in 4 per enemy** (`FLASH_LOOK=6`, test10, unchanged). At today's hit rate the
  pictures go white, normal, normal, normal, white: half the hits show no white picture. Cost: the fixed area 6 B, LC1 5 B.

  | Scene | Look | MSX2 | MSX2+ | turbo R |
  |---|---|---|---|---|
  | Ground floor, Cain shot (kill 1500-1765) | 6 | 12.52 / 7.0 / 6.47 -> **14.58** / 8.4 / 7.70 (+16.4 %) | 12.50 / 6.8 / 6.51 -> **13.93** / 7.6 / 7.25 (+11.4 %) | 22.77 / 17.5 / 13.06 -> **23.39** / 28.2 / 17.12 (+2.7 %) |
  | | 7 | -> **18.26** / 9.9 / 9.65 (+45.8 %) | -> **16.71** / 9.5 / 8.89 (+33.7 %) | -> **23.88** / 38.4 / 21.35 (+4.9 %) |
  | Cain's route firing (boss 130-1400) | 6 | 7.29 / 10.8 / 4.49 -> **7.41** / 10.9 / 4.50 (+1.7 %) | 9.73 / 5.0 / 4.88 -> **9.76** / 5.1 / 4.92 (+0.3 %) | 17.02 / 13.2 / 9.41 -> **17.02** / 13.4 / 9.49 (0.0 %) |
  | | 7 | -> **7.57** / 10.9 / 4.64 (+3.8 %) | -> **10.12** / 5.3 / 5.10 (+4.0 %) | -> **17.42** / 13.7 / 9.82 (+2.3 %) |

  - Elsewhere (Cain's route without fire, tour3, l2_tour: no hits) both looks run within -1.5 to +0.7 % of batch 1, the
    timing scatter of a few T-states moved (flash-7's kill 130-1400 on the MSX2+, -1.0 %, is the one window of either look
    outside G-SPEED's 1 %).
  - The longest gap between two pictures on the ground floor: MSX2 250 -> 234 ms (6 and 7), MSX2+ 234 -> 250, turbo R
    117 -> 117.
  - The look (Wd1's `lk.tcl` records, `C/dprev/lkan2.py`; kill, boss and l2_barrel on the MSX2, MSX2+ and turbo R, 27
    runs): the rule holds in every run (flash-7: at every tick, shown and skipped). On the ground floor Cain's look
    changes 87 times with 0, 44 with 6 and once with 7 on all three machines (white from the first hit on). With 7 each
    single hit is white exactly 4 ticks (boss 27 hits, l2_barrel 9, each machine). No enemy shows two looks in a picture
    on the ground floor or l2_barrel. On the boss route the only mixed pictures are the kinds batch 1's look shows too:
    Cain's muzzle flash (`$41358`, which `c22_fl` draws with `bob_draw`, draw_bob `$AB08`: its own colours in every
    look; 0: 3 / 15 / 12 pictures on the MSX2 / MSX2+ / turbo R, 7: 31 / 16 / 26) and the first picture of a white
    stretch while his 32 x 40 sprite part's white version still loads (0: 49 / 0 / 7, 7: 32 / 0 / 4); plus, with 7
    only, one end-of-stretch picture on the MSX2 and one on the turbo R (the play-field parts normal, the sprite part
    still white).
  - The contact sheets of a burst on the ground floor (16 pictures from tick 1600, looks 0, 6, 7, three machines):
    `C/dprev/sheets/burst_*.png`.

**D2. Ticks per picture when pictures are slow.** Today CAD_MAX is 2. On 2026-10-21 the user rejected 3-4 ticks a
picture in level 1, when the walk's next step also loaded late.
- **Keep 2** (test12).
- **loop-3: 3 ticks a picture, only when a picture takes 8 VBLANKs or more** (below 7.5 pictures/s at 60 Hz;
  `CAD_MAX=3 CAD_HOLD=3 CAD_ADAPT=8`, test13). Faster scenes look exactly as today.
  - Where it acts: RoboCop's walk advances 1 and 2 drawings alternately; Cain's legs step unevenly; hits closer
    together than one picture merge into one flash picture. A scene near 7.5 pictures/s switches between 2-tick and
    3-tick pictures.
  - The pictures with 3 ticks (of those with ticks): MSX2 23.5 % on Cain's route, 69.6 % on the ground floor, 42.3 % on
    the boss route, 3.7 % in level 2; MSX2+ 81.1 %, 74.5 %, 92.7 %, 3.1 %; turbo R 3.5 %, 0, 8.9 %, 0.1 %.
  - Cost: 14 B (fixed area). A threshold of 6 VBLANKs (`CAD_ADAPT=6`) would also reach most of the turbo R's frames
    (not built).
- **loop-1: CAD_MAX 3 everywhere** (`CAD_MAX=3 CAD_HOLD=3`, test14; the CAD_HOLD a_loop's analyst measured loop-1 with,
  its `c3` and `T_c3` builds). The same look as loop-3, whenever a picture is late: 3-tick pictures MSX2 28.9 / 88.4 /
  44.1 / 13.3 %, MSX2+ 86.4 / 88.3 / 95.4 / 11.6 %, turbo R 31.9 / 14.4 / 49.2 / 0.3 % (the same four scenes). Cost: 0 B.

  | Scene | Option | MSX2 | MSX2+ | turbo R |
  |---|---|---|---|---|
  | Cain's route (kill 130-1400) | loop-3 | 8.81 / 18.0 / 5.99 -> **9.68** / 18.6 / 5.89 (+9.8 %) | 12.89 / 7.4 / 6.73 -> **15.77** / 6.6 / 5.78 (+22.4 %) | 18.35 / 15.6 / 10.49 -> **18.58** / 16.0 / 10.56 (+1.3 %) |
  | | loop-1 | -> **9.73** / 19.2 / 5.75 (+10.4 %) | -> **15.76** / 6.6 / 5.67 (+22.3 %) | -> **20.41** / 16.2 / 10.21 (+11.3 %) |
  | Ground floor (kill 1500-1765) | loop-3 | 12.52 / 7.0 / 6.47 -> **17.59** / 7.3 / 6.70 (+40.4 %) | 12.50 / 6.8 / 6.51 -> **17.80** / 6.9 / 6.58 (+42.4 %) | 22.77 / 17.5 / 13.06 -> **22.93** / 16.8 / 13.15 (+0.7 %) |
  | | loop-1 | -> **18.44** / 7.0 / 6.61 (+47.3 %) | -> **18.46** / 6.9 / 6.55 (+47.7 %) | -> **24.30** / 18.6 / 13.30 (+6.7 %) |
  | Boss route (boss 130-1400) | loop-3 | 7.29 / 10.8 / 4.49 -> **8.02** / 12.3 / 4.14 (+10.0 %) | 9.73 / 5.0 / 4.88 -> **12.77** / 4.7 / 4.40 (+31.2 %) | 17.02 / 13.2 / 9.41 -> **17.50** / 13.5 / 9.30 (+2.8 %) |
  | | loop-1 | -> **8.02** / 12.6 / 4.16 (+10.0 %) | -> **12.98** / 4.7 / 4.42 (+33.4 %) | -> **19.95** / 13.5 / 8.88 (+17.2 %) |
  | tour3 (street, beams, lifts, roof) | loop-3 | +2.5, -1.3, +9.5, +3.3 % | +7.3, +5.9, +7.6, +9.3 % | +0.5, -1.7, -0.1, -0.4 % |
  | | loop-1 | +4.4, -1.1, +11.9, +3.8 % | +15.2, +8.9, +13.1, +11.3 % | +0.9, +0.7, 0.0, 0.0 % |
  | Level 2 (l2_tour 20-1590) | loop-3 | 19.03 / 19.6 / 12.47 -> **19.33** / 19.8 / 12.55 (+1.6 %) | 23.05 / 17.4 / 15.53 -> **23.39** / 17.2 / 15.39 (+1.5 %) | 24.87 / 42.3 / 24.28 -> **24.92** / 42.1 / 24.32 (+0.2 %) |
  | | loop-1 | -> **19.86** / 20.1 / 12.23 (+4.4 %) | -> **24.39** / 17.0 / 15.16 (+5.8 %) | -> **24.93** / 42.1 / 24.27 (+0.3 %) |

  - Both trade pictures with progress for game speed where they act (MSX2+ Cain's route 6.73 -> 5.78 / 5.67 progress
    pictures/s).
  - The longest gap between two pictures grows by up to about 85 ms where they act: loop-3 MSX2 Cain's route 250 ->
    334 ms, boss 367 -> 417, the roof 267 -> 334; MSX2+ Cain's route 250 -> 300, boss 367 -> 401, the beams 334 -> 384;
    loop-1 MSX2 boss 367 -> 417, the lifts 234 -> 317, the roof 267 -> 350; MSX2+ the beams 334 -> 400; turbo R at most
    +34 ms.
- **loop-4: even caps up to 6 (not recommended; estimated on HEAD, not built).** MSX2+ Cain's route 21.1 / 5.7, boss
  17.1 / 4.1.
  - Cain's legs strobe at 4 ticks a picture and look as if they walk backwards at 6.
  - Progress pictures drop 15-22 %.
  - The longest gaps reach 417-484 ms.

**D3. MSX2 only: how far the view may lag behind the camera** (`LAG_X=64`, test15). With the V9938 engine (`fb_eng` 1:
an MSX2, or `FORCE_V9938`) x may lag 64 px instead of 32 before the ticks are held; y stays at 32. The V9958's ring keeps
32 (`fb_eng` 0: the MSX2+ and the turbo R take the default's return, so their cadence decides as without the option).
C/a_loop's prototype relaxed x on every machine; on the MSX2+ the x lag reaches 32-37 px in 10-12 frames of Cain's route.
- What the player sees: while the V9938 scroll is late, RoboCop may run ahead of the scrolled view, the view catches up
  in page steps, and enemies may act near the edge. Measured (`C/dprev/lx.tcl`, from tick 130, kill and boss): the
  view lags at most 37 px with batch 1 (held at 32-39 px in about 53 % of the MSX2's frames on Cain's route) and at most
  70 px with 64 (held at 64-71 px in about 45 %); RoboCop's sprites come within 39 px of the left side (64 with batch 1)
  and 12 px of the right side (13 with batch 1): `rc_safe`, unchanged, holds the ticks within 16 px of a side. The
  frames without a tick on the MSX2: Cain's route 1,723 -> 1,385, boss 1,101 -> 856.
- Cost: 12 B (fixed area).

  | Scene | MSX2 | Expert | MSX2+ |
  |---|---|---|---|
  | Cain's route (kill 130-1400) | 8.81 / 18.0 / 5.99 -> **10.44** / 18.4 / 7.03 (+18.4 %) | 8.87 / 18.1 / 6.02 -> **10.46** / 18.5 / 7.11 (+17.9 %) | 12.89 / 7.4 / 6.73 -> **12.89** / 7.3 / 6.73 (0.0 %) |
  | Ground floor (kill 1500-1765) | 12.52 / 7.0 / 6.47 -> **12.54** / 6.9 / 6.63 (+0.2 %) | 12.52 / 6.9 / 6.62 -> **12.47** / 7.1 / 6.59 (-0.4 %) | 12.50 / 6.8 / 6.51 -> **12.03** / 6.6 / 6.27 (-3.8 %) |
  | Boss route (boss 130-1400) | 7.29 / 10.8 / 4.49 -> **8.53** / 10.9 / 5.11 (+17.1 %) | 7.34 / 10.7 / 4.49 -> **8.53** / 10.8 / 5.14 (+16.2 %) | 9.73 / 5.0 / 4.88 -> **9.76** / 5.1 / 4.93 (+0.3 %) |
  | tour3 (street, beams, lifts, roof) | +7.7, +2.0, +1.4, +0.2 % | +6.7, +1.4, +1.6, +0.6 % | 0.0, +0.6, +0.2, -0.5 % |
  | Level 2 (l2_tour 20-1590) | 19.03 / 19.6 / 12.47 -> **19.27** / 19.4 / 12.65 (+1.2 %) | 19.02 / 20.0 / 12.66 -> **19.38** / 19.4 / 12.62 (+1.9 %) | 23.05 / 17.4 / 15.53 -> **23.08** / 17.2 / 15.42 (+0.1 %) |

  - The MSX2+ is unchanged by construction; its windows move within the timing scatter (the ground floor's -3.8 %: a
    265-tick window, G-SPEED's 5 % tolerance; the decisions the same, 7 to 24 T-states more a frame).
  - The longest gap between two pictures: MSX2 within -50..+33 ms of batch 1's, the Expert's Cain's route 234 -> 334 ms.
- scroll-7's AX_MAX 144 is not offered: it moves RoboCop's framing on every machine.

**D4. field-12: Cain's and type 21's legs at half their animation steps.** Each legs drawing is shown for two steps, as FIELD_HALF already does for the explosions and the smoke.
- Gain: +1.5-2 % on the Z80 machines, +3.5 % on the turbo R.
- Cost: 0 code bytes.
- The user rejected a similar half-step look for RoboCop's walk.

**D5. logic-8: level 3's beams change their looks only in the ticks that are shown.**
- Once the redraw has caught up, nothing differs. But on the V9938, a page built between the two ticks of a picture can show a beam look one random step older. The logic traces stay identical.
- Gain: MSX2+ tour3 15.6 -> 15.8 (+2.3-2.5 % in the beams and lifts windows); MSX2 +0.5 %.
- Cost: about 10 B.

**D6. loop-5: the 5.37 MHz turbo during play, on Panasonic MSX2+ machines** (FS-A1FX, WX, WSX).
- This is a hardware and sound decision, not a look.
- Gain: x1.3-1.4 there (MSX2+ Cain's route 19.7 / 9.9, ground floor 19.5 / 10.1); 0 everywhere else.
- Risks:
  - the PCM speech is paced in T-states;
  - the OPLL needs write delays;
  - VRAM writes need pacing: `outi32`'s 18 T are 3.35 us, against a slot of about 3.26 us;
  - the HUD split must be recalibrated;
  - the claimed x1.5 PSG pitch is unverified;
  - OCM-based machines and the SX-2 may run other clocks.
- It can only be an optional speed-up, never a requirement, and it needs tests on real hardware.
- Cost: 40-80 B, plus the speech and PSG compensation.

**Not offered.** spr-11 and scroll-8 break rules; loop-6 changes the input latency.

## 4. Expected speed per scene and machine

Each cell is ticks/s / progress pictures/s. The columns:
- **Today**: measured.
- **Measured set**: the prototyped items of batches 1-2 (field-1/2, FC-UPLOAD, flash-1, logic-1/2, scroll-1, spr-1/4), chained by v_gain's model.
- **Full DI set**: all three batches. The range runs from 60 % to 100 % of each unmeasured item's corrected gain.
- **Options**: each option alone, on top of the full set (realized). Estimates; D1-D3 measured on batch 1 alone: section 3.

Ticks/s are capped at 25.

| Scene | Machine | Today | Measured set | Full DI set | Options on top |
|---|---|---|---|---|---|
| Cain's route (kill 130-1400) | MSX2 | 7.26 / 4.91 | 9.4 / 6.0 | 10.4-11.1 / 6.6-7.1 | loop-1 12.3/6.3; loop-3 10.8/6.6; loop-4 13.3/5.6; lag-x 11.4/7.2; field-12 10.6/6.7 |
| | MSX2+ | 10.04 / 5.22 | 13.3 / 6.7 | 14.1-14.6 / 7.1-7.3 | loop-1 17.8/6.6; loop-3 15.7/6.9; loop-4 21.1/5.7; field-12 14.3/7.2; loop-5 19.7/9.9 |
| | turbo R | 15.00 / 8.46 | 19.4 / 10.2 | 19.6-19.7 / 10.3-10.4 | loop-1 23.5/10.0; loop-3 20.2/10.3; loop-4 24.5/9.8; field-12 20.3/10.7 |
| Boss route (130-1400) | MSX2 | 6.12 / 3.76 | 7.8 / 4.3 | 8.7-9.3 / 4.8-5.1 | loop-1 9.7/4.5; loop-3 9.0/4.7; lag-x 9.5/5.2; flash-7 9.0/5.0; flash-6 8.8/4.9 |
| | MSX2+ | 8.07 / 4.07 | 10.1 / 5.0 | 10.7-11.1 / 5.2-5.4 | loop-1 13.9/4.9; loop-3 13.0/5.0; loop-4 17.1/4.1; flash-7 10.9/5.3; loop-5 15.0/7.3 |
| | turbo R | 13.87 / 7.63 | 18.1 / 9.3 | 18.3-18.4 / 9.3-9.4 | loop-1 22.8/9.1; loop-3 19.2/9.3; flash-7 18.9/9.7 |
| Ground floor, Cain shot (1500-1765) | MSX2 | 10.18 / 5.34 | 13.0 / 6.8 | 13.8-14.4 / 7.3-7.6 | flash-7 16.8/9.2; flash-6 15.4/8.2; loop-1 18.7/7.3; loop-3 15.5/7.1 |
| | MSX2+ | 10.06 / 5.20 | 13.3 / 6.9 | 13.9-14.3 / 7.2-7.4 | flash-7 16.7/9.1; flash-6 15.4/8.1; loop-1 18.8/7.2; loop-3 15.6/7.0; loop-5 19.5/10.1 |
| | turbo R | 19.54 / 10.99 (14.0 all) | 23.6 / 13.9 | 24.0-24.3 / 14.1-14.3 (about 20 all) | flash-7 24.7/21.2 (about 38 all); flash-6 24.2/16.9; loop-1 25/14.1 (flash-7: estimated; see D1's measured note) |
| Level 3's start (tour3 0-1400) | MSX2 | 9.07 / 5.33 | 10.4 / 6.2 | 10.9-11.2 / 6.4-6.6 | loop-1 11.4/6.2; lag-x 11.5/6.8; logic-8 10.9/6.5 |
| | MSX2+ | 12.87 / 7.14 | 15.0 / 8.7 | 15.6-16.0 / 9.0-9.3 | loop-1 17.1/8.6; loop-3 16.2/8.9; logic-8 15.8/9.1; loop-5 20.3/11.7 |
| | turbo R | 21.37 / 18.42 | 22.3 / 19.0 | 22.3 / 19.0 | loop-1 23.1/19.0 |
| Level 2 (l2_tour) | MSX2 | 19.6 / 13.2 | 21.1 / 14.4 | 22.2-23.0 / 15.1-15.6 | loop-1 23.1/14.6; lag-x 22.5/15.3 |
| | MSX2+ | 23.1 / 15.2 | 23.7 / 16.2 | 24.9-25 / 17.0-17.5 | loop-1 25/16.1; loop-5 25/22.1 |
| | turbo R | 24.9 / 24.4 | 25 / 24.5 | 25 / 24.5 | none |

How to read the table:
- The MSX2's numbers are the least certain. They depend on item 7 (estimated), and they cannot pass about 0.95x the MSX2+'s.
- The MSX2's boss route with field-1/2 was never measured; batch 0 measures it.
- The options are alternatives inside each group: loop-1/3/4, and flash-6/7. Options from different groups (for example flash-7 with loop-3) compound roughly.

## 5. Implementation

### 5.1 Rules for every implementation agent

- **Git.**
  - One worktree per lane, from the current `level2` tip, on a branch `perf2/<lane>`.
  - One commit per finished item, with the docs it changes (`docs/MSX_ARCHITECTURE.md`, `docs/level3/HANDOFF.md`).
  - Lanes merge one at a time, and `docs/ROM_BUDGET.md`'s free bytes are updated after each merge. That keeps the lanes from conflicting there.
  - Never build into, or touch, `build/msx`.
- **Emulators.**
  - Use private headless sessions through `mcpd.py`/`mx.sh`, under `C/omsem.sh`: at most two instances of ours at once, across all lanes.
  - Throttle off, sound muted, `z80_freq` 3579545.
  - Follow CONTEXT.md 5's Tcl rules.
  - Emulator time is the shared bottleneck: run the gates of the item that is about to merge first.
- **Game rules.** Follow CONTEXT.md 3: the logic tick for tick, the display rules, the MSX2 baseline, generic hardware, the z80asm traps, and interrupt code that may clobber only AF, BC and HL.
- **Prototypes.** A prototype is a starting point only. Re-derive each change on the current tip, and never carry over a prototype's aliasing or its test-only shortcuts.
- **Gates.** Run them once per worktree, on its final commit. Measure speed per item only where the item's gain must be confirmed; below 2 %, use counters (T-states, census) instead.

### 5.2 Resources (assigned now, so that parallel lanes do not collide)

**Fixed area.** The binding set is p_pzdiag/p_pzdiag2, with 29 B free. The product has 164 B and the drive builds 100-119 B. Running ledger, in merge order (approximate):

| Step | Change (B) |
|---|---|
| W1L: logic-1 (net -4), logic-2 (+7) | +3 |
| W1S: spr-6 | -530 |
| W1S: spr-1 | +42 |
| W1S: spr-4 | +97 |
| W2C: scroll-1 | +48 |
| W2F: R2's trampoline | +10 |
| W2L: scroll-2 (b, c) | +65 |
| W2S: spr-2, spr-3, spr-7 | +35, +30, +140 |
| W3F: TILE-LOOKUP's row helper | +30 |

That leaves about 60 B in the lowest set for the user's options (loop-3 14, lag-x 9, flash-7 30). Rule: spr-6 merges before any fixed-area growth beyond W1L's.

**BANK_FIELD.** 8 B are free in the drive, trace and lock sets; 49 B in the product.
- **W1F.** R1 frees 132 B; `ftl_ax` takes 20 and FC-UPLOAD about 35. About 85 B are left.
- **W2F.**
  - R2 moves `engines_init`, `engines_jump`, `scroll_init` and `s38_init` (306 B) to FRONT2. A fixed-area trampoline saves and restores `act_a000`.
  - Verify that none of them runs every frame.
  - flash-1 takes about 185 B. About 210 B are left.
- **Batch 3** needs about 335 B:

  | Item | B |
  |---|---|
  | V9938-SYNC | 100 |
  | field-7 | 40 |
  | TILE-LOOKUP | 40 |
  | field-6 | 50 |
  | flash-3 | 35 |
  | flash-4 | 50 |
  | field-10 | 20 |

  So R3 must free at least 150 B. R3 moves the V9938-only sync code to FRONT2 (or to a new bank: 93 banks are free) behind a stub. Otherwise flash-4 and field-10 wait.

**RAM.** Free per msx.inc's audit: F170h-F190h (33 B), ECFBh-ED0Fh (21 B), EDF0h-EDFFh (16 B), plus crumbs.

| Owner | Bytes | Addresses |
|---|---:|---|
| logic-1 (`mw_gen`, `mc_prev`/`mc_cur`, beam and turret entries) | 59 | F170h-F190h, ECFBh-ED08h, EDF0h-EDFBh (as in P1) |
| flash-1 (`fb_lkf0`, `fb_lkf1`, `fb_lkq`) | 3 | ED09h-ED0Bh (p12b used ECFBh-ECFDh: move) |
| spr-1 (`sb_end`) | 1 | ED0Ch (the prototype used F170h: move) |
| field-6(c) (the refill flag) | 1 | ED0Dh |
| spr-4 (`ft_orn`...) | 3 | E553h-E555h only after a RAM watch over every drive proves it unwritten; otherwise EDFCh-EDFEh |
| flash-4 (the last staged item) | about 10 | C5F7h-C5FFh (9 B) plus EDFFh, or shrink it |
| scroll-2(c) (row hints) | 51 | MP_ROW's tail, 0A33h-0AFFh (check the largest map's rows; cleared in `tiles_init`) |

ED0Eh-ED0Fh stay spare.

**Elsewhere.**
- VRAM does not change in the planned set.
- LC1 has 24 B free: logic-6's `pl_hits` change stays byte-neutral.
- Per-frame banks: R1 and R2 add none. R3 adds one bank on the V9938: a speed target on page-cache devices, not a rule.

### 5.3 Batches

Lanes that run in the same batch work in parallel. They touch different files, except that each adds its own rows to msx.inc, and W2C and W2L edit different `tiles.asm` routines: whichever merges second rebases.

Serial chains:
- `field.asm`: W1F -> W2F -> W3V and W3F-a -> W3F-b.
- `sprites.asm`: W1S -> W2S.
- `tools/msxsprites.py`: W1F -> W2S's spr-8.
- `special.asm`: W1L -> W2L.

| Batch | Lane | Items, in order | Files | Starts after |
|---|---|---|---|---|
| 0 | W0 measure | 1. Commit the measurement kit into `P/tools/bstest/perf2/`, with fixed paths. 2. HEAD baselines for the gates. 3. The level-1/2 flash probe (`C/m_l2/m2.tcl` `m2_flash`, l2_tour on 3 machines). 4. lag-x builds on kill and l2_tour (MSX2, Expert). 5. The MSX2 boss route with `C/a_field/R/trimtiles.rom`. | `tools/bstest/perf2/*` only | now |
| 1 | W1F field | field-1 (level 3); field-2 with R1; FC-UPLOAD; field-1 (levels 1-2) | `tools/msxsprites.py`, `tools/bstest/fieldcheck.py`, `tools/msxframe.py`, `msx/field.asm`, `msx/ending.asm`, `msx/cold.asm`, `tests/` | W0 step 1 |
| 1 | W1L logic | logic-1; logic-2 | `msx/tiles.asm`, `special.asm`, `level3.asm`, `level3obj.asm`, `msx.inc` (its rows), `tools/mkrom.py` with the table generator, `tests/` | W0 step 1 |
| 1 | W1S sprites | spr-6; spr-1; spr-4 | `msx/sprites.asm`, `lvshared.asm`, `msx.inc` (its rows), the trampoline, `tests/` | W0 step 1 |
| 2 | W2F flash | R2; flash-1 | `msx/field.asm`, `ending.asm`, the engines' callers, `msx.inc` | W1F |
| 2 | W2C scroll | scroll-1 | `msx/scroll9938.asm`, `scroll9958.asm`, `tiles.asm` (the `fm38_bb` hook) | W1L, W1S |
| 2 | W2L logic | logic-6; logic-4; scroll-2 (b, c) | `mapobj.asm`, `special.asm`, `plmove.asm`, `hits.asm`, `tiles.asm` (`fb_invf`, `map_write`, `get_tile`), `tools/cellmasks.py`, `tests/` | W1L, W1S |
| 2 | W2S sprites | spr-7; spr-2; spr-3; spr-8 | `sprites.asm`, `bob.asm`, `tools/msxsprites.py`, `tools/msxframe.py`, the pool checks | W1S, W1F |
| 3 | W3V field | R3; V9938-SYNC (item 7) | `msx/field.asm` (`fb_sync`, `fb_step`, the marker), the new bank | W2F, W2C |
| 3 | W3F-a field | field-7; TILE-LOOKUP; field-10 (100 B budget) | `msx/field.asm` (`fb_piece`/staging, `fb_tiles`, `fb_fill`), `tiles.asm` (the row helper) | W2F, W2L |
| 3 | W3F-b field | field-6; flash-3; flash-4 | `msx/field.asm` | W3V, W3F-a |

**Batches 0 and 1: done (2026-11-01).** W0's kit `1c5791c` (with its review's fixes `2d58639`, `fdc3469`,
`47323db`, `c3732a9`, `c734c0b`) and the lanes W1L, W1S, W1F and Wd1 were merged in that order into
`perf2/batch1` (merge commits `7a3e845`, `b8c538d`, `b79bac3`, `54da0e0`, `44e7cf6`); no lane was dropped,
field-1's levels 1-2 commit was dropped inside W1F. The gates on the merged tip, the speed table (HEAD
against batch 1 per scene and machine) and the open issues: `docs/level3/HANDOFF.md`, "Performance campaign
2, batch 1"; the free bytes: `docs/ROM_BUDGET.md` 2.5.

**Integration gates.**
- When W2F and W2C have both merged: G-FIELD with page-path counts on scrolling windows, on both VDPs, and G-HOLD.
- After every merge: G-BUILD and G-LOGIC on the merged tip.
- If W2C fails G-HOLD, it waits for W3V and merges together with it.

**The user's decisions.**
- D1's look can be previewed at once on HEAD: it touches only `bob.asm`.
- D2 and D3 are previewed after batch 1 merges, so that the user judges them at the new speed.
- TAG ROMs for the user's preview: the DI tip; the tip with flash-7; with flash-6; with loop-3; with loop-1; and, for the MSX2, with lag-x 64.
  *Done on batch 1 (lane dprev, `perf2/dprev`):* test10 (flash-6), test11 (flash-7 in game ticks), test12 (batch 1
  itself, the reference), test13 (loop-3), test14 (loop-1), test15 (lag-x 64), as `-l2`/`-l3` play-test files
  (`C/dprev/preview`, `NOTES.txt`); the options `FLASH_LOOK`, `CAD_ADAPT` (with `CAD_MAX`, `CAD_HOLD`) and `LAG_X`, every
  build without them byte-identical; section 3 has the measured numbers.
- The options the user adopts go into a W-opt worktree (`player.asm`, `bob.asm`) after W2S merges.
- If W0 finds a flash spike in levels 1-2 above about 20 % of those pictures' time, W2S gets an item for the silhouette toggle's cost (the budget rerun, the plan, the colour rows, the uploads).

### 5.4 Gates

**Baseline.** Every gate compares with HEAD (3b11042), built with the same options and run on the same drive, machine and emulator (openMSX 21 headless). W0 records the baselines once. m_l3's, m_l2's and the analysts' base runs count where their options match.

- **G-BUILD.**
  - `tools/bstest/variants.sh`: every option set that builds at HEAD still builds. That is 58 of 61; the three DEMO sets already fail at HEAD (`rc2.asm:488`), outside this campaign.
  - Free bytes per bank (`l2base.py banks`) go in the commit message.
  - `make test` passes.
- **G-LOGIC.**
  - The `hz.sh l3builds`/`l2builds` trace builds compared with the Amiga bench: 0 differ. That covers tour3, beam, park, boss, kill and cont3; level 2's 23 traces; level 1's cov0 and cov1.
  - The lost counters (`mp_lost`, `atr_lost`, `rd_lost`, `fb_lost`) are 0.
  - The cadence options use their own trace builds (`C/a_loop/T_c3`).
- **G-MAP.** Map dumps every 100 ticks (`mapdiff.py` with `cnt.tcl`; `tools/mapcmp.py` against the bench) equal HEAD's.
- **G-FIELD.** The field check: `l2base.tcl` `l2b_fd_setup` with `tools/bstest/fieldcheck.py --level 3` or `--level 2`, `l3field.tcl` `lf_jobs`, and level 1's.
  - Windows of 900 records (15 s): two kill-floor windows, kill 1560+, boss 110+ and 300+, park, tour3's lifts, and l2_tour's fd windows.
  - Machines: C-BIOS_MSX2, FS-A1FX and FS-A1GT.
  - It passes when no difference class appears that HEAD's same window does not show. The FB_HOLD class is judged by G-HOLD instead.
- **G-HOLD.** Pictures that reach FB_HOLD (BOBs one picture behind the sprites), counted with `holds.py` per minute of play over whole drives (kill, boss, tour3, l2_tour), on the MSX2, the Expert, the MSX2+ and the turbo R. The count must stay at or below HEAD's. Short windows are noise: the control builds scatter between 3 and 7.
- **G-GUARD.** `rc2_guard` on kill and boss: tears not above HEAD's.
- **G-LOCK.**
  - LOCKSTEP=24 display records with `tools/dispcmp.py`, on both VDPs: 0 differences.
  - Sprite items also run the census (`vercmp.py`), `rc2_satcheck`, `rc2_patcheck`, `rc2_sprlines`, `rc2_sprvram` and `rc2_overlines`.
- **G-VRAM.** `rc2_count_too_fast` is 0, the Expert included. The frame-cache places equal the ROM's frames after uploads.
- **G-SPEED.** `m3.tcl` with `win.py`, on C-BIOS_MSX2, FS-A1FX and FS-A1GT (plus the Expert for V9938 items). Report ticks/s, pictures/s and progress pictures/s.
  - Windows:
    - kill 130-1400, 300-1500 and 1500-1765;
    - boss 130-1400;
    - tour3 40-210, 215-540, 545-1065 and 1085-1400;
    - park;
    - l2_tour 20-1590 and 2080-2350;
    - level 1's `drive_play`, which must stay at 25 ticks/s and 25 pictures/s.
  - The item's gain must reproduce on its target windows within the noise.
  - No window may be slower than HEAD by more than 1 % (long windows) or 5 % (the ground floor).
- **G-PROD, at each batch's merge.**
  - The product build, started from the title on a fresh machine (power-on RAM), on the three machines.
  - The 15-machine matrix (`make matrix`).
  - A look at Cain's fight on screen (`rc2_snap` and `msxframe`) on each machine.
- **At the end of the campaign.**
  - A TAG candidate for the user's hardware: the SX-2 in slot 1, the Pico+ at normal speed, the Hotbit.
  - The speed table in `docs/level3/HANDOFF.md` updated.

## 6. Open points

- **The flash in levels 1-2 is unmeasured.** The user's complaint covers all enemies (W0). *Measured by W0:* on
  `l2_end`, where flashes are dense, the silhouettes cost 9.0 % of the flash pictures' time on the MSX2 (+6.8 ms
  each), 4.3 % on the MSX2+ and 0 on the turbo R: below 5.3's ~20 %, so W2S gets no item for it.
- **The MSX2's boss route with field-1/2 was never measured** (W0). *Measured:* `trimtiles.rom` 6.12 -> 7.21
  ticks/s (W0); the merged batch 1 7.29.
- **The x-only lag build was never run** (W0). *Measured by W0* on HEAD, C-BIOS_MSX2, kill 130-1400: lagx64
  7.26 -> 8.91 ticks/s (+22.7 %), c3lagx64 9.89 (+36.2 %); l2_tour 20-1590 +0.7 % / +5.2 % (the Expert the same
  within 0.5 %).
- **scroll-1's picture count.** It removes catch-up pictures. Look at the turbo R's scroll on a recording before merging.
- **A study, not analysed for tears.** After the set, the flash still costs the turbo R about half its picture rate on the ground floor, and only flash-7 removes that. A possible decision-identical step: when no other BOB overlaps a look-only item, draw the new look with LMMM straight onto the page, in the copy's beam slot. That saves both copies, about 30 ms of VDP time per toggle.
