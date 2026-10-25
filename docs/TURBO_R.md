# MSX turbo R support (R800): design

Status: implemented and verified in openMSX, 2026-10-25 (section 12: what was built and
measured; where it differs from the design below). Written from a research and code-inventory
pass (three web research agents, two code readers, a design draft and a completeness critic),
then revised with the user's decisions. Numbers marked *est.* were estimates before the
measurements of section 12.

Notation: `L:t` is display line L at VDP tick t (0-1367) after that line's sync, as in the
measured table of `docs/MSX_ARCHITECTURE.md`; the FH match of line L is at `L:1282`. One line =
1368 ticks = 228 Z80 T-states = 456 R800 cycles; 1 T = 6 ticks; 1 R800 cycle = 3 ticks. A
"turn" is one taken `djnz` of a delay loop.

## 1. Decisions (the user, 2026-10-25)

1. **The HUD split on the R800: one play-field line less.** On a turbo R running the R800 the
   play field shows display lines 0-160 (161 lines) and six blank lines (161-166) hold the
   split's writes; the HUD still starts at line 167. Nothing is written to the VDP while the
   HUD is drawn, as on every other machine. (The alternative, writing colours 12-15 during the
   HUD's first line, which uses only colours 0, 7, 8 and 9, was declined.)
2. **The R800 is always used for the game on a turbo R**, with no key to stay on the Z80. The
   title (music and speech) stays on the Z80.
3. **The fixed area (banks 0-1) is copied into the turbo R's internal RAM** before any release
   with R800 support (phase B), for speed.
4. **Validation in openMSX only** (its Panasonic FS-A1GT; the user has no turbo R). Release
   notes will say "verified in openMSX".
5. Kept by default (no question asked): the game ticks at 25 Hz on the turbo R as everywhere;
   no MULUB/MULUW.

The test6 crashes on the SX-2 with the MSX Pico+'s turbo normal or risky are treated as that
combination's limit (the user: "esse SX-2 com o Pico+ é bastante instável"); turbo R work goes
ahead.

## 2. Hardware facts

| # | Fact | Status |
|---|---|---|
| H1 | R800 clock 7.15909 MHz: 1 cycle = ½ T = 3 ticks; a line = 456 cycles; a 262-line frame = 119,472 cycles | several sources |
| H2 | R800 code in internal RAM (slot 3-0): 1 cycle per opcode byte, +1 when the fetch changes 256-byte page; a data access forces a page break on the next fetch. `djnz`/`jr` 3 taken, 2 not; `jp` 5; `push` 6; `pop` 5; `ld a,(nn)` 6. A taken `djnz` at xxFEh costs 4, at xxFFh 5 | openMSX's model, measured on a real FS-A1GT |
| H3 | DRAM refresh stalls ≈26 cycles every ≈210 (0.876 of the time usable), not synchronised with the program: ±78 ticks of jitter | several sources; openMSX uses a fixed grid |
| H4 | R800 accesses to the cartridge slots go through the S1990 at the 3.58 MHz bus timing: ≈+2 cycles per data access (`ld a,(hl)` 6 against 4); opcode fetches ≈4-5 cycles per byte (openMSX charges 4; never measured exactly). ROM-resident R800 code ran ≈2.5x slower than from RAM on a real turbo R | data cost measured; fetch cost inferred |
| H5 | **S1990 in R800 mode: any two accesses to ports 98h-9Bh (IN or OUT, any instruction, OUTI/OTIR included) are held at least 62 cycles (186 ticks, 8.66 µs) apart, start to start.** A lone access costs nothing extra; up to ≈52 cycles of other code between two accesses are free. It cannot be switched off | measured on an FS-A1GT; openMSX models one timer for all four ports (mixed-port sequences unmeasured) |
| H6 | Z80 mode on a turbo R: no S1990 hold, +1 T per VDP access (T9769C); the FS-A1GT (Z80) row of the measured table includes it | verified |
| H7 | Other I/O on the R800 (PSG, OPLL, PPI, mapper, E4h-E7h): 9-10 cycles, no hold | several sources |
| H8 | The YM2413 needs ≥ 12 clocks after the address write and ≥ 84 after the data write; the turbo R's MSX-MUSIC BIOS waits 3 and 13 E6h ticks. Too-fast writes are lost on hardware; openMSX does not emulate this | several sources |
| H9 | SCC and Konami mapper registers are ordinary cartridge writes on the R800 (≈+2 cycles), no known rate limit | inferred; hardware only |
| H10 | E6h/E7h: a 16-bit up-counter at 3,579,545 / 14 Hz (3.911 µs = 28 R800 cycles = 14 Z80 T = 84 ticks a count), the same in both CPU modes; a write to E6h resets it; turbo R only | several sources |
| H11 | CHGCPU (0180h): A bits 1-0 = 0 Z80, 1 R800 ROM mode, 2 R800 DRAM mode; bit 7 also sets the turbo LED. It does DI, pushes 11 words (22 bytes), keeps SP at FFFDh-FFFEh, updates CASPRV (FCB1h) and port A7h (bit 1 = 1 for the Z80: hardware pause enabled), OTIRs S1990 register 6 through E4h/E5h; the CPU that writes parks inside that OTIR, the other resumes at its own parking point in the same ROM code, pops everything, `LD I,A`, **EI**, RET. I is carried across, **the interrupt mode is not** (the R800 got IM 1 at cold boot). **Page 0 must show the main ROM (slot 0-0) at both ends** | BIOS 4.1 source, several sources |
| H12 | A ROM cartridge's INIT runs in Z80 ROM mode (the logo's R800 use is undone first), unless a cartridge in an earlier slot switched CPU and returned | several sources |
| H13 | Detection: 002Dh = 3; a JP (C3h) at 0180h; GETCPU (0183h) returns A = 0/1/2. Some Z80 turbo kits also implement CHGCPU, so a measurement must confirm the R800 (8.1) | several sources |
| H14 | DRAM mode copies the BIOS, BASIC, SUB-ROM and Kanji driver into the top four mapper segments (12-15 on the FS-A1ST, 28-31 on the FS-A1GT) and write-protects them; only BIOS code gets faster. Not used here | several sources |
| H15 | V99x8 CPU access slots: the worst safe spacing is ≈86 ticks with sprites on; the S1990's 186 exceed it, so R800 code cannot overrun VRAM | verified + inferred |
| H16 | R800 instruction set: SLL acts as SLA, flag bits 3/5 differ, IXH/IXL/IYH/IYL official, MULUB/MULUW added, R also counts refreshes. The port uses no SLL and no `OUT (C),0` | several sources |
| H17 | R800 interrupt acceptance: IM 2 ≈7-8 cycles in openMSX (marked TODO there); no hardware figure. Match-to-caller latency of the "pop hl / ret" waits ≈18-21 cycles + 0-26 of refresh | model only |
| H18 | PAUSE: port A7h read bit 0 = the pause flip-flop (the key toggles it); write bit 0 = pause LED, bit 1 = Z80 hardware pause enable, bit 7 = R800 LED. In Z80 mode the flip-flop holds the Z80 in WAIT; in R800 mode only the BIOS ISR's busy-wait honours it (the game's IM 2 handler does not) | several sources |
| H19 | openMSX bench: the FS-A1GT config and firmware are installed; the FS-A1ST firmware is not (no downloads). Tools: `get_active_cpu`, the "S1990 regs" debuggable (register 6: 60h Z80, 40h R800 ROM, 00h DRAM), `r800_freq_locked`. No console command performs a proper CPU switch | verified locally |
| H20 | openMSX's limits: cartridge timing errs fast; refresh deterministic; IRQ/HALT/OTIR costs marked TODO; OPLL overrun not emulated; the S1990 rule a flat 62 cycles shared by all four ports | several sources |

Facts from this repository:
- P1. No BIOS call after `ram_page0`; `so_x`/`so_n` overwrite F380h-F43Bh at each level start,
  so CALSLT, RDSLT and the BIOS ISR cannot run any more. FFFDh-FFFEh and FCB1h are outside the
  game's map; C2A6h-C2C1h are free.
- P2. Page 0 is slot 3's RAM (mapper segment 3), page 3 segment 0; FCh-FFh are never written.
- P3. The only OPLL writes during the game are `mus_quiet`'s (through `snd_stop` from `pl_init`,
  `front_over`, `front_stats`).
- P4. No T-state budget is compared any more (`UP_TOTAL`, `COST_*` are accumulated only); the live
  per-frame limits are counts with beam deadlines.
- P5. The game already ran with a 10.74 MHz Z80 (3x): the state shared with the interrupts copes
  with a fast CPU. What is new on the R800 is slower VDP I/O and the timed code.

## 3. CPUs, detection and switching

### 3.1 What runs where

| Stage | CPU |
|---|---|
| Power-on: detection, the R800's IM 2 and presence check (3.2), `snd_detect`, `vdp_setup`, `ram_page0`, phase B's copy (6), `snd_init`, `mus_init`, `vm_cal` | Z80 |
| Title: pictures, SCC/OPLL/PSG music, speech, `front_done`, `tiles_upload` | Z80 (`vm_play` is calibrated for it; `opll_w`'s waits, `dc_set`, `scc_pat`) |
| From `ng_go`: level set-up, `display_on`/`split_cal`, the main loop, `level_restart` | R800 |
| `front_over`, `front_stats` | R800 (VBLANK waits, the split, `snd_stop` without its OPLL part) |

### 3.2 Detection and the power-on round trip (`cpu_detect`, `BANK_FRONT`)

Called from `rc2.asm` `init` while the BIOS is still in page 0 and its work area intact:
1. `cpu_tr` = 0 (no R800 use), `cpu_cur` = 0 (Z80).
2. If 002Dh < 3 or (0180h) ≠ C3h: done (no turbo R).
3. GETCPU; if not 0 (another cartridge left the R800 on): CHGCPU(80h). Always, whatever else.
4. Round trip: CHGCPU(81h); on the R800, `di`, `ld a,IM2_I`, `ld i,a`, `im 2` (so that the R800
   is never again in IM 1 once the BIOS work area is gone), then the presence check (8.1: the R800
   turn rate against E6h and the S1990's hold on an `in a,(98h)` sequence), then CHGCPU(80h). The
   R800 parks under DI (CHGCPU's own). `cpu_tr` = 1 only if the check passed.
5. On any failure the game stays on the Z80 everywhere.

### 3.3 Switching (`cpu_set`, `BANK_FRONT`)

Points: to the R800 at the first instruction of `ng_go` (both ways into a game pass there, the
display off); back to the Z80 after `front_over`/`front_stats` return, before `call title`.
`level_restart` stays on the R800. `cpu_set` (A = 81h or 80h; returns at once when `cpu_tr` = 0):
1. DI; no VDP interrupt source and none pending: R#1 = display off without IE0, R#0 with IE1 off,
   S#1 and S#0 read.
2. Switching back to the Z80 with the pause flip-flop set would freeze the Z80 at once (H18): wait
   while A7h bit 0 = 1 (the picture kept, the pause LED lit), see 3.4.
3. Page 0 = slot 0-0 for the call (A8h only: slot 0's secondary register still selects 0-0), the
   old A8h kept in a register (CHGCPU saves every register).
4. CHGCPU(A); on return (the other CPU, interrupts enabled but no source can fire): DI,
   `ld a,IM2_I / ld i,a / im 2` (a second guard after 3.2's), GETCPU, page 0 = RAM again,
   `cpu_cur` = the CPU now running.
5. Install that CPU's timed RAM block at `SR_RAM` (split.asm for the Z80, split8.asm for the R800)
   and set the split's line offset (4.1).
6. EI, return.
It touches 24 bytes of stack, FFFDh-FFFEh, FCB1h, ports A7h, E4h/E5h. The game never writes
E4h/E5h, F4h or A5h itself.

### 3.4 PAUSE on the R800

On the R800 `key_scan` reads A7h bit 0: each change becomes the game's own pause key (its P
code), and the pause LED (A7h bit 0 write, CASPRV kept in step) follows. `cpu_set`'s wait (3.3
step 2) covers a press on the screens that do not scan keys (`front_over`, `front_stats`).

## 4. The HUD split on the R800

### 4.1 Why a separate block, and the six blank lines

The Z80 split makes 44 VDP accesses from its blank to its display-on (R#8, the page/scroll
registers, R#16, 30 palette bytes, R#1): at 186 ticks each that is 8,184 ticks, more than the
8,164 the five blank lines allow (blank in [161:144, 162:100], display-on in [166:144, 167:100]),
so no calibration can make it fit (H5). With the user's choice the R800 path takes one play-field
line more for the blank: V' = 161 (the first blank line), the interrupt at the end of line V'-5 =
156, the timed match at the end of line V'-2 = 159, the blank effective from line 161, the
display-on from line 167 (HUD_R23 unchanged).

Run-time changes: `iv_list` (the VBLANK list) computes `split_r19` = R#23 + V - 2 - `sl_off` and,
when `sl_off` = 1 (the R800), writes R#19 = R#23 + SPLIT_LINE - 1 after the list's OTIR and before
its S#1 read (the read that drops a match the list's R#23 raised: 2026-10-24's phantom split). The
lists keep R#19 = R#23 + SPLIT_LINE; `front_stats`' list goes through `iv_list` too. `SPLIT_R19`
(written after the split, a match behind) is unchanged. The game still draws 162 lines; line 161
is just not shown on the R800.

### 4.2 The burst

After the match's interrupt (an R800 copy of `sp_irq` in the R800 block) and one calibrated delay
(`split_dly`), every access goes out back to back, paced by the S1990: the code between two
accesses is a few cycles, well under the ≈52 the hold leaves free, so each lands exactly 186 ticks
after the previous (even with a refresh in between). With the blank at B:

| Access k (after the blank) | Write | At (B = 160:830) | Constraint |
|---|---|---|---|
| 0 | R#1 = blank | 160:830 | [160:144, 161:100] |
| 2 | R#16 = 1 | 160:1202 | none (colours unchanged) |
| 4 | R#8 = sprites off | 161:206 | after line 160's last pixel (≈160:1282) |
| 6, 8, 10, 12 | R#2, R#23, R#26, R#27 (`split_list`) | 161:578 … 162:326 | after line 160's last pixel |
| 14 | R#25 = HUD (no border mask) | 162:698 | blank line |
| 15 … 44 | colours 1-15 (30 bytes to 9Ah) | 162:884 … 166:806 | blank lines |
| 46 | R#1 = display on | **166:1178** | [166:144, 167:100] |

Then `sp_r19` (shared with the Z80 path). B must lie in [160:538, 160:1120] (R#8 after line 160's
pixels; the display-on before line 167's latch); the target 160:830 leaves ≈290 ticks on both
sides, ≥ 206 with the 0-84 ticks of jitter (one turn, a refresh). The display-on stays inside its
window for an S1990 spacing of 55-64 cycles (hardware 61.8-62, openMSX 62); if port 99h and port
9Ah had separate timers (unmeasured, T1 in 9), the display-on would come up to ≈370 ticks earlier,
still inside. Fallback when the match never comes (`sp_irq8` timing out after ≈2.3 lines' worth of
turns, a limit worked out from the calibration; the longest legitimate wait is ≈2 lines): the
burst at once; timeouts are counted in RAM for the tests (`sp8_cnt`, off the normal path).

The lead before the match: the interrupt at line 156 leaves 3 lines (1,368 cycles); the path
from it to the R#19 write is ≈460-880 cycles from the cartridge (the worst case with a 5-access
DI window of the main program in progress), less with phase B: ≥ 1.07 lines of lead.

### 4.3 Calibration on the R800 (`split_cal8`)

`split_cal` dispatches on `cpu_cur`. On the R800 it measures N only (the turns of 32 lines, the
least of four, R800 copies of `sc_sync`/`sc_ack`/`sc_cnt`/`sc_turns` in the R800 block) and works
out the one delay: `split_dly` from n (≈133 turns a line in openMSX: ≈3.42 cycles a turn with
refresh) with constants fitted on openMSX's line:tick table (as the Z80's were), in 16-bit
arithmetic, clamped to 1..255; the timeout of 4.2 from n too. Default when N is missing: the
value measured on openMSX's FS-A1GT. No M run, no `split_dly1`/`split_dly2`.

### 4.4 Code layout

New `msx/split8.asm`: `org SR_RAM`, bytes stored in `BANK_FRONT` (`sr8_rom`, ≤ `SR_ROOM`), the
first routine `isr_split8` (so that `isr`'s `call nz,isr_split` lands on it), using A, B, C, HL
only (`isr` saves AF, BC, HL). Assembly-time checks: every timed `djnz` and taken `jr` and its
whole loop inside one 256-byte page and not at xxFEh/xxFFh (checked on the branch instruction's
address, after the labels: z80asm's forward-`if` gotcha). The Z80 block (split.asm) stays as it
is, byte for byte.

## 5. Other CPU-speed dependencies

| Item | On the R800 | Handling |
|---|---|---|
| `SP_GAP`, `SC_GAP` (8 turns ≈ 31 µs on the Z80) | ≈3.4 µs | `SP_GAP8`/`SC_GAP8` 32 turns ≈ 15 µs: ≈21 µs from the S#1 read to the first R#19 access, ≈29 µs to its register byte through the S1990's hold (the Hotbit's V9938 lost writes closer than that; the turbo R's V9958 never showed it) |
| `SC_WRAPS` (65,536 turns: 15 frames) | ≈1.9 frames | unchanged (≥ 1 frame) |
| `sc_cnt`'s 64 wraps, `sc_turns` | N ≈ 4,200 turns: 17 wraps | unchanged; R800 copies use the R800 block's addresses (`scn_inc`) |
| `split_cal`'s products (x74 fits ≈6.8x; `split_dly2` saturates ≈4.2x) | n32 ≈ 4,270 | the R800 path (4.3) |
| `pl_init` / `sc_dflt` defaults | Z80 values | R800 default from openMSX |
| DI windows (`vram_write`, `vdp_busy`, `fv_chk`, `spr_wr`) | 4-5 accesses ≈ 250-350 cycles | unchanged (inside the lead) |
| `vdp_cmd`, `vdp_cmd_q`, `ifg_send`, `fb_qstart` | a command start ≥ 139 µs (Z80 ≈112-125) | unchanged; slower VDP feeding |
| `ifg_wt`'s 110 polls | ≈75-80 lines | unchanged (exits on VR) |
| `iv_list` | ≈60 accesses (+17 with a command) ≈ 0.5-0.7 ms | unchanged (50 blank lines at 60 Hz) |
| `outi32`/`outi16`, `q_sat`, `pat_now`, `pcr_eb` | 186 ticks a byte: safe, ≈1.7x slower | unchanged |
| `hud_frame` | ≤ ≈230 accesses ≈ 32 lines | unchanged; a guard check for HUD VRAM writes while lines 167-211 are drawn (both CPUs) |
| tile/HUD/picture uploads (OTIR) | ≈1.35x slower, no deadline | unchanged |
| `fb_mayq`/`fb_fits` | models the VDP's speed | unchanged; `rc2_guard` re-checks |
| `FB_BURST`, `FB_STEPS`, `RD_BURST` | VDP-bound | not raised for the R800 |
| cost units (`COST_*`, `UP_TOTAL`) | unused | unchanged |
| `cadence`, `wait_frame`, `sec_tick` | count VBLANKs | unchanged |
| `vm_play`, `vm_cal`, `dc_set`, `scc_pat`, `mst_fm`, `snd_init` | Z80 timing | Z80 only (3.1) |
| `opll_w` via `mus_quiet` | too fast for the YM2413 | skipped when `cpu_cur` = 1 (the OPLL is silent since the title's `snd_stop` on the Z80); tests assert no OPLL write on the R800 |
| `psg_w`, joystick, SCC stores, bank switches | 9-10 cycles apart | unchanged |
| `rnd_step`'s `ld a,r` | the R800's R counts refreshes too | unchanged; Z80-against-R800 equality checks use INPUT_SCRIPT builds |
| `isr_init`'s IM 2 | Z80 only | 3.2 and 3.3 |
| SPLITDIAG, DIAG, the lab | Z80 units | SPLITDIAG builds keep `cpu_tr` = 0; DIAG builds never reach `ng_go` |

## 6. The fixed area in RAM (phase B)

On a turbo R only, at power-on after the detection (before `vm_cal`: the title then runs the
fixed area from RAM, which `vm_cal`'s self-contained loop in `BANK_MUSIC` does not depend on):
1. Set FCh = 3, FDh = 4, FFh = 0 explicitly (a loader may have left other values).
2. Copy the cartridge's 4000h-7FFFh into segment 4 (through page 0 or page 2), then show segment
   4 of slot 3-0 in page 1 (slot 3's secondary register for page 1 = 0, A8h page 1 = slot 3).
3. Nothing may write 4000h-7FFFh afterwards (the mapper registers 5000h/7000h are never
   written: the game switches only 9000h/B000h): a write watchpoint on 4000h-7FFFh in the
   keyboard plan and the long run, on every machine before phase B and on the FS-A1GT after it;
   an mkrom.py check for stores to 5000h/7000h.
Banked code (logic modules, the field engine, tiles, music) still comes from the cartridge.
Both CPUs then run the ISR's entry, the main loop and the sprite engine from RAM.

## 7. Performance expectations (*est.*)

| Kind of work | Z80 time ÷ R800 time |
|---|---|
| CPU work from internal RAM | 5-8 |
| CPU work from the cartridge | openMSX 2-3; hardware ≈1.5-2 |
| VDP streams (OUTI/OTIR to 98h-9Bh) | 0.58 against OUTI, 0.74 against OTIR |
| VDP register pairs | ≈0.4 |
| The VDP command engine | 1 |

The busiest window measured (`c860`, 6.3-7.7 pictures/s, ≈46-50 % game speed on the Z80):
≈10-23 pictures/s at 78-100 % speed with everything from the cartridge, ≈12-25 with the fixed
area in RAM (25 is the cadence's cap). Normal play already runs at 25-26 pictures/s. What stays
VDP-bound: the VBLANK list, the split, sprite uploads, HUD jobs, command starts and polls, and the
command engine itself (scroll tiles, BOB composition). Ticks/s and pictures/s are reported apart,
with the frames where the camera lag held ticks.

## 8. Test plan (headless openMSX through `msx_local_*`, Panasonic_FS-A1GT)

8.1 **The R800 presence check** (on the R800, at power-on): a `djnz` loop's turns over E6h counts
(≈8 a count on the R800 in RAM, ≈1 on a Z80) and 16 `in a,(98h)` against 16 `in a,(0A8h)` timed by
E6h (≈35 against ≈6 counts on the R800, equal on a Z80; no counter: not a turbo R).

8.2 **Bench settings**: `throttle off`, `r800_freq_locked` and `z80_freq_locked` on, `::z80_freq`
reset, `::pause` off, `::rg_notear` unset, turbo R pause off.

8.3 **Tools** (tools/openmsx_rc2.tcl): `rc2_cpu` (`get_active_cpu`, S1990 register 6),
`rc2_cpucheck` (the CPU at INIT, `front_title`, `display_on`, the main loop, the title after a
game), `rc2_opllwatch` (writes to 7Ch/7Dh while the R800 runs: 0), `rc2_vdpcount` (VDP accesses per
picture, the command engine's busy fraction); the guard's split line, play-area height and RAM
block key made CPU-aware; a probe time-base correction: watchpoint stamps are the instruction's
start on the Z80 (11-15 T before the port write) and the effective time for a held R800 access,
so the line:tick probe adds the instruction's I/O offset on the Z80 and treats a stamp exactly 62
cycles after the previous VDP access as held on the R800 (self-check: two back-to-back `out
(99h)` log 186 ticks apart); the Z80 rows, the window edges and the R800 row are restated on that
time base before the R800 constants are fitted.

8.4 **Functional**: the CPU at each point; 100 title-game round trips (registers, SP, I kept; IM 2
on both CPUs; page 0's checksum unchanged; never an execution at 0038h with page 0 on slot 0);
a fresh power-on through the title; death, restart, game over, statistics, a new game, x20; a
30-minute keyboard plan without a freeze; a cartridge of our own in slot 1 whose INIT leaves the
R800 on (ROM mode, and DRAM mode) with the game in slot 2; PAUSE pressed in play, on
`front_over`/`front_stats` and across both switches.

8.5 **Timing**: the R800 row of the line:tick table over 1,500 frames (blank 160:830 ± 84 ticks,
display-on 166:1178 ± 84 on the corrected time base), no `sp_irq8` timeout, the lead ≥ 0.9 line,
`rc2_guard` reg/pal/cmd/cpu/vbl 0 with the tears beside the Z80's.

8.6 **Sound**: no OPLL write on the R800; `dc_set` only on the Z80; `vm_dly` 7 on the FS-A1GT; SCC
and PSG effects consumed and written.

8.7 **Equivalence and performance**: the logic traces on the R800 (4,401 and 1,400 frames, 0
differ); LOCKSTEP display records Z80 = R800 on INPUT_SCRIPT builds; recordings clean and coherent
across pictures without a tick; rates and profiles over `drive_play` and `c860` for the Z80, the R800
from the cartridge, and the R800 with phase B.

8.8 **Regression**: the 14 other machines (keyboard plan, guard 0, their table rows unchanged: the
Z80 block is identical); the candidate sent to the user's Hotbit and SX-2 (Pico+ disabled on the
SX-2).

8.9 **Not verifiable without a turbo R**: cartridge fetch timing under the R800, the S1990's rule
for mixed ports, IM 2 latency and the refresh phase on hardware, too-fast OPLL writes, SCC/flash/
emulated cartridges under R800 bus cycles (the Pico+ included), the real V9958's latch points,
CHGCPU's duration.

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| T1 | The S1990's spacing between port-99h and port-9Ah accesses (separate timers?) | positions robust to it (4.2) |
| T2 | CHGCPU's round trip and the IM modes | 3.2's power-on round trip, Tcl assertions |
| T3 | INIT in Z80 mode | `rc2_cpucheck` at INIT; 3.2 step 3 anyway |
| T4 | IM 2 latency on hardware | inside the margins (±30 ticks) |
| R1 | The real V9958 latch or S1990 differing from openMSX | ≥ 206-tick margins; 55-64-cycle tolerance |
| R2 | Pending interrupt or IM 1 at a switch | sources masked, DI, `IM 2` at power-on and after every switch |
| R3 | Slot 0's page 0 not on 0-0 at a switch | checked in `cpu_set`: on failure stay on the current CPU, `cpu_tr` = 0 |
| R4 | Not enough lead before the match | 3 lines from the interrupt; fallback; phase B shortens the path |
| R5 | The VDP command engine saturated in scenes with many BOBs | measured (busy fraction) |
| R6 | FS-A1ST (256 KiB) untested | only segments 0, 3, 4 used, present on both models |
| R7 | Stray writes into the RAM copy of the fixed area (phase B) | watchpoint tests, mkrom.py check |
| R8 | PAUSE freezing the Z80 at the switch back | 3.3 step 2, 3.4 |

## 10. Phases

0. **Tools and baseline** (the ROM unchanged): the Tcl helpers and the probe correction of 8.3;
   the FS-A1GT (Z80) baseline: `drive_play` and `c860` rates, a profile per file, VDP accesses per
   picture, the command engine's busy fraction; the write watchpoint on 4000h-7FFFh on every
   machine.
1. **Detection and the power-on round trip** (3.2), the R800 parked in IM 2; nothing else
   changes: every machine's rows identical, `rc2_cpucheck` Z80 throughout.
2. **Switch round trip** (a test build: `ng_go` switches to the R800 and straight back): 8.4's
   round-trip invariants over 100 cycles, PAUSE across the switches.
3. **The game on the R800**: split8.asm, the run-time split line, `split_cal8`, the OPLL guard,
   PAUSE in `key_scan`, the `ng_go`/`ml_fe` hooks; 8.4-8.8.
4. **Phase B** (section 6), re-measured; `c860` toward 25 ticks/s.
5. **Docs and release** (`docs/MSX_ARCHITECTURE.md`'s turbo R section and table row; notes
   "verified in openMSX"); only the exact candidate sent goes to `build/msx`.

## 11. Sources

- openMSX source and its hardware measurements: `src/cpu/R800.hh`, `src/cpu/VDPIODelay.cc`,
  `src/cpu/CPUCore.cc`, `src/MSXS1990.cc`, `src/MSXE6Timer.cc`, `src/memory/PanasonicMemory.cc`,
  `doc/internal/r800test.txt`, `turbor-vdp-io.txt`, `turbor-vdp-io-timing.ods`,
  `r800-refresh.txt`, `r800-djnz.txt`, `r800-call.txt` (github.com/openMSX/openMSX); issues #935
  (OPLL timing), #961, #989.
- The turbo R BIOS 4.1 source (github.com/dinoboards/msxsrcsrc, base410/bios.mac, subrom.mac,
  optrom.mac) and the DOS 2.31 disk ROM source (github.com/gomwing/msxsyssrc, disk231).
- msx.org wiki: R800 Programming, ASCII R800, ASCII S1990, Main-ROM BIOS; msx.org forum threads on
  the turbo R's CPU switch, cartridge signals and VDP speed.
- Grauw's MSX Assembly Page: Z80/R800 instruction timings, I/O port list, BIOS calls
  (map.grauw.nl/resources).
- The R800 user's manual transcription (d4.princess.ne.jp/msx/datas/R800UM).

## 12. As built (2026-10-25)

What the code does, where it differs from the design above, and what openMSX measured
(Panasonic FS-A1GT; every other machine of the MCP's home unchanged).

**Code.**
- `cold.asm` `cpu_detect` (called first by `snd_detect`, at power-on with the BIOS): a turbo R
  (002Dh = 3, a JP at 0180h) gets the Z80 back first if a cartridge left the R800 on, then a round
  trip with the VDP's interrupt sources off (R#1/R#0 from RG1SAV/RG0SAV without IE0/IE1, S#1 and
  S#0 read): the R800 goes into IM 2 and measures itself from RAM (`cd_ram`), the Z80 comes back
  in IM 1 (the BIOS's mode until `isr_init`, even if CHGCPU came back on one same CPU) with R#0/R#1
  as the BIOS had them. `cpu_tr` = 1 when 512 turns took under 120 timer counts and port 98h was
  held (FS-A1GT: 64, 34 against 6-7 counts). SPLITDIAG and DEMO_HUD builds keep the Z80.
- `cold.asm` `cpu_set` / `cpu_game` / `cpu_title`: `tiles_init` (both ways into a game) switches
  to the R800; the exits of `front_over` and `front_stats` (front.asm) switch back before the
  title. The switch installs that CPU's block at SR_RAM (split.asm or split8.asm), sets `sl_off`,
  `scn_at` (sc_turns' wrap check), `key_tp` and `sp8_cnt` = 0.
- `cold.asm` `tr_fixram` (from `ram_page0`'s success exit): the fixed area into segment 4, page 1
  on it (A8h EFh with the game in slot 2: pages 0, 1, 3 the internal RAM).
- `split8.asm` (191 bytes of the 320): `isr_split8`, `sp_irq8`, the burst, `sc8_*`, `split_cal8`
  (n32 = N + `SC8_K` 80; `split_dly` = n x 117 / 256; `sp8_tmo` = n x 147 / 64). Assembly-time
  checks for each timed djnz (a label defined twice when it lands at xxFEh/xxFFh).
- `isr.asm`: `iv_list` (split_r19 = R#23 + V - 2 - `sl_off`; on the R800 R#19 = split_r19 - 3
  after the list, before the S#1 read), `split_cal` dispatching to `split_cal8`, `sc_turns`
  comparing DE with `scn_at`. These, `key_scan`'s R800 branch and the dispatch are left out of
  DEMO_HUD and SPLITDIAG builds (fixed-area room; those builds keep the Z80).
- `player.asm` `key_scan`: on the R800 a change of the PAUSE flip-flop is a press of P (fresh:
  g_keydone 99h first), its release sent once that press was handled and P itself is not held
  (so that the next P counts); the pause LED follows the flip-flop. PAUSE and P each toggle the
  game's pause, so mixing them can leave the flip-flop set while the game runs (the LED lit):
  `cpu_set` then waits at the next switch to the Z80 for PAUSE again, the picture kept and the
  LED lit, instead of the Z80 freezing in CHGCPU.
- `music.asm` `muq_f`: no OPLL write on the R800 (silent since the title's `snd_stop` anyway).

**Measured** (openMSX FS-A1GT, headless, through the MCP):
- The R800 split over 1,500 frames, the same with and without the fixed area in RAM: blank
  160:822-906, sprites off 161:198-282, display on 166:1170-1254 (window [166:144, 167:100]), R#19
  for line 159 written in lines 157-158; `split_dly` 60, n32 4,229-4,234, `sp8_tmo` 303; no wait
  timed out (`sp8_cnt` 0). Every other machine's row and delays of `docs/MSX_ARCHITECTURE.md`
  unchanged (the FS-A1FX at 5.37 MHz gave `split_dly2` 42 in one run, 43 in another).
- Speed, pictures/s and game ticks/s (25 = full speed):

| Window | Z80 | R800, code from the cartridge | R800, fixed area in RAM |
|---|---|---|---|
| `drive_play` | 26.0 / 25.0 | 47.9 / 25.0 | 58.5 / 25.0 |
| `c430` | 6.7 / 13.3 | 14.2 / 21.5 | 31.4 / 24.6 |
| `c860` | 7.0 / 13.9 | 15.6 / 23.2 | 25.4 / 24.5 |
| `c1490` | 7.3 / 13.8 | 18.2 / 23.3 | 38.8 / 24.7 |

  More pictures than ticks are the view catching up with the camera on frames without a tick
  (`ml_frame`), which the Z80 also does when it has time; the recordings check each against the
  map at its view.
- Logic traces on the R800: 4,401 and 1,400 game frames, 0 differ. Start check: guard 0,
  patcheck 0 bad, sprlines 0. Recordings: 0 background differences, RoboCop whole. The 14
  machines: no freeze, vbl 0, RoboCop never off the published camera.
- 100 round trips: page 0's sum unchanged, IM 2 and I = C1h on both CPUs at every resume, never
  the BIOS's 0038h after `isr_init`. Game over -> title -> new game x3: the title on the Z80, the
  game on the R800, no OPLL write on the R800 (386 on the Z80, the title's FM). A cartridge in
  slot 1 leaving the R800 on (ROM and DRAM modes): our INIT starts on the R800, the title runs on
  the Z80, the game on the R800. PAUSE during play and on `front_over`: handled; PAUSE then P,
  then PAUSE, then P: each toggles once. No write to 4000h-7FFFh after the copy.
- Not verified (no turbo R here): section 8.9.

**Seen on the way, not turbo R's** (also on C-BIOS_MSX2): the first list of a new game after a
game over shows RoboCop's sprites 12 px right and 4 px down of the camera's (tick 0,
`rc2_camcheck`); the field engine started a command (R#46, `fqs_go`) at line 57 of game frame 951
in some V9958 runs (`rc2_guard` reg 1, its destination not shown), as in earlier batches.
