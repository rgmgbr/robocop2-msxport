# The MSX Pico+ page cache and the 2 MiB ROM

Written on 2026-10-26, after the 2 MiB bank test passed on the user's MSX Pico+. It goes with
`docs/ROM_BUDGET.md` 6.1 (the 2 MiB ROM), which links here.

The question: the Pico+ runs our ROM from flash through a cache of 8 KiB pages in its SRAM. Does
that cache limit the 2 MiB plan, and what must the layout and the engine respect?

Measured against:
- release v0.1.2 (`build/msx/ROBOCOP2_v0.1.2.ROM`, SHA1 973dc14b…): level 1, the title, the game
  over;
- the bank test cartridge `build/msx/ROBOCOP2_banktest-1.ROM` (ID BT2M-1, 2 MiB, SHA1 4fc883fb…),
  built by `tools/msxbanktest.py` from `msx/banktest.asm`.

Sources:
- the user's bank-test results of the same day, on the SX-2 and on the Hotbit;
- three area reports of the same day:
  - **firmware**: the Pico+ firmware v2.12, decompiled with REA and Ghidra;
  - **trace**: every bank v0.1.2 selects and reads in openMSX, over 12 runs;
  - **levels**: the engine's bank readers from the source, and a scene model of levels 1-3;
- checks made for this draft with those reports' own scripts and recordings (section 9):
  - the bank-test replay fitted to the Hotbit's counts, and a finer fit next to 55 slots on both
    machines;
  - v0.1.2's recorded bank selects replayed through the decompiled cache;
- a review of this draft against the same files, which corrected it (scripts in section 9).

Nothing was run on hardware or in an emulator for this draft.

Conventions:
- A bank is 8 KiB of the ROM image. The Pico+ holds a bank as a page, in an 8 KiB slot of its SRAM.
- T = one Z80 T-state at 3.579545 MHz. A 60 Hz frame is 59,736 T.
- A **select** is a write of a bank number to 9000h (the 8000h window) or B000h (the A000h window).
  A phase's **set** is the banks it selects. A **miss** is a select of a bank the cache does not
  hold; a **hold** is the time the Z80 then waits.
- Images A and B are the two firmware builds inside v2.12 (section 3.1).
- K is the number of banks the bank test's timed loop takes in turn.
- Basis:
  - **M**: measured on the user's hardware, or in openMSX where marked "M, openMSX";
  - **D**: decompiled from the Pico+ firmware v2.12. (In `ROM_BUDGET.md`, D means a design
    assumption; here it does not.)
  - **S**: from a source: the project's code or a cited text;
  - **E**: estimated;
  - **I**: inferred. This includes replays of the decompiled algorithm on measured data.

## 1. The short answer

**The cache does not limit the size of the ROM. It limits how many different banks one level
selects: 53 on the user's Pico+.**

- **ROM size plays no part (D).** When a ROM starts, the Pico+ gives the cache all its free SRAM.
  A 1 MiB and a 2 MiB image get the same cache. Only ROMs that fit the free SRAM (at most
  451,584 B or 490,496 B) run without one.
- **The user's Pico+ has 55 slots (I, from M and D).**
  - Banks 0 and 1 hold 2 of them for good. 53 remain for the banks at 8000h and A000h (D).
  - 55 is the only slot count that reproduces all nine bank-test counts exactly, on the SX-2 and
    on the Hotbit (section 2.4).
  - In the firmware, 55 slots means image B, the build with FM-PAC emulation. The user reported
    every option disabled, so this is still open (section 8).
  - The budget of 53 holds only if the Pico+ menu shows FM-PAC enabled (check 7.1). If it shows
    FM-PAC disabled, the decompile missed an allocation of 31-39 KiB. If image B makes it too,
    FM-PAC on leaves 50-51 slots, 48-49 for the banks at 8000h and A000h (I).
- **A miss holds the Z80 for about 246 µs** (I, fitted to M: 877-885 T, about 1.5 % of a 60 Hz
  frame).
  - The page is copied when its number is written, even if the window is never read (D).
  - A select of a cached bank costs nothing measurable (M).
- **Level 1 fits.**
  - In play it selects 47 banks, 49 with a restart after a death. Its start adds 4 more: 53 in
    all (M, openMSX).
  - Replayed through the decompiled cache, 20-26 minutes of play cost 13 misses, all first loads
    in the first 41 s, at most 1 in a frame. A level start costs 21-23 loads after a title and
    37-42 from a cold start, at most 4 in a frame (I).
  - The user saw no slowdown and no glitch with v0.1.2 on the Pico+. This agrees.
- **Levels 2 and 3 come close to the limit (E).**
  - The levels model puts their busiest 5 s at 45 and 49 banks, banks 0-1 included, against 55
    slots.
  - That model undercounts level 1's set in play by 4-6 banks. Over a whole level, levels 2-3 may
    therefore reach 50-54: from 3 under the limit of 53 to 1 over it.
  - The bonus stages (9-18 banks) and the ending (8-11) are far below.
- **The rules** (section 6):
  1. At most 53 banks selected per level in play, with 3Fh and the sound banks, once check 7.1
     confirms image B. `tools/mkrom.py` should count them and stop the build above that.
  2. No speculative selects. Putting back a bank that is still cached is free.
  3. Select a level's set before its play field shows (two passes), and the speech's three banks
     before its PCM loop.
  4. Only if a level goes over the budget: the set reducers (SFX, LC23, S1, L3, FLASH, STREAM).
- **The record, corrected the same day.**
  - `docs/ROM_BUDGET.md` 6.1 and decision 6 in `docs/MSX_ARCHITECTURE.md` used to say "the banks
    the game reads within a short stretch must stay well under 32"; 6.1 also asked to check
    "more banks per frame than it holds". Both now say: at most 53 banks selected per level.
  - A reload costs 877-885 T (about 246 µs), not 860 T.
  - The cache counts selects, not reads.

### 1.1 Where the reports disagree

| Point | Firmware report | Trace report | Levels report | Stronger evidence |
|---|---|---|---|---|
| Cache size | 55 slots (image B) or 59 (A); 53 or 57 for 8000h/A000h (D) | unknown; simulated at 32-63 pages | unknown; checked against 64 | The firmware, fitted exactly on both machines (2.4) |
| Replacement | CLOCK, mapped slots skipped (D) | LRU or FIFO | LRU or FIFO | The firmware. The replay of 4.3 runs its CLOCK itself: in play it matches LRU (13 misses; LRU 13-14), and at the first eviction after the slots fill it acts like FIFO (3.3) |
| When a page loads | at the select (D) | at a read (model A) or a select (model B) | at a select ("mapped") | The firmware: model B and the levels model apply |
| Banks 0 and 1 | 2 of the slots, never evicted (D) | outside the cache, or cached | inside the count | The firmware |
| Bank 3Fh | loaded, and pinned while selected (D) | counted in model B | counted | The firmware |
| Miss cost | 880-885 T (fit, SX-2) | 860 T | 860 T | The fit, which reproduces all nine counts: 877-885 T on the two machines. 860 T assumes that every pair misses from K = 64 on. The two differ by 2-3 %, which changes no conclusion |
| The drop at K = 32 (784 against 807) | 15 first loads at a constant 74.0 T a hit | a hit cost growing with occupancy? | eviction in the background? | The firmware replay, which is exact |
| Level 1's set | about 48 (an earlier estimate, not checked) | 46 read in a whole level; its recordings give 47-49 selected in play, 53 with the start (M, openMSX) | busy: 44 over 5 s, banks 0-1 included | The trace |
| The Hotbit | expected to match the SX-2 | — | — | Recorded in `docs/ROM_BUDGET.md` 6.1 (commit 71ffdb3). 55 slots fit it exactly too (2.4) |
| Which image | B, from the fit | — | — | Open: the user reported every option disabled. If the menu shows image A, the budget of 53 is not safe (section 8, question 1) |

## 2. The measurement

### 2.1 What ran

- **Cartridge**: BT2M-1, a 2 MiB Konami SCC image in which every byte names its bank
  (`docs/ROM_BUDGET.md` 6.1).
- **SX-2**: OCM-PLD MSX2+, 60 Hz, Z80 at 3.58 MHz. The Pico+ ran firmware v2.12 in primary slot 1,
  not expanded. Every option was disabled, turbo included (the user, 2026-10-26).
- **Hotbit**: MSX2 with a V9938 (Ademir Carchano's kit 2.0), 60 Hz, the Pico+ in slot 1. Its
  Pico+ settings were not stated (`docs/ROM_BUDGET.md` 6.1).
- **The timed loop** (`msx/banktest.asm` rc_spd, lines 704-722; S):
  - it runs from RAM at C480h with interrupts off;
  - each pair is a select at B000h and a read of A020h:
    `ld a,(de) / inc e / ld (B000h),a / ld a,(A020h) / inc bc / in a,(99h) / rlca / jr nc`;
  - it counts pairs over 8 frames from a VBLANK, then divides by 8 (`speed`, lines 332-372);
  - the list holds 256 entries: entry i = 2 + i × (256 / K), with an 8-bit add (lines 341-344).

### 2.2 Results (M)

- **PASS on both machines.**
  - All 256 bank numbers showed the right bank at 8000h (written at 9000h) and at A000h (written
    at B000h).
  - Every byte of banks 1-255 was right through A000h.
- **The SCC answers at 9800h for exactly 3Fh**: 4 of 4 values with 3Fh at 9000h; 0 of 4 with 7Fh,
  BFh and FFh.
- **Pairs a frame**, with the replays of section 2.4:

| K | SX-2 (M) | Hotbit (M) | openMSX (M) | 55 slots (I) | Misses in the 8 frames, 55 slots, SX-2 (I) | 59 slots, SX-2 timing (I) | 59 slots, Hotbit timing (I) |
|---:|---:|---:|---:|---|---:|---:|---:|
| 1 | 807 | 817 | 829 | = measured | 0 | 807 | 817 |
| 2 | 805 | 816 | 829 | = measured | 1 | 805 | 816 |
| 4 | 804 | 814 | 829 | = measured | 2 | 804 | 814 |
| 8 | 802 | 813 | 829 | = measured | 3 | 802 | 813 |
| 16 | 796 | 807 | 829 | = measured | 7 | 796 | 807 |
| 32 | 784 | 795 | 829 | = measured | 15 | 786 | 796 |
| 64 | 68 | 69 | 829 | = measured | 495 | 95 | 96 |
| 128 | 65 | 65 | 829 | = measured | 497 | 63 | 64 |
| 256 | 64 | 64 | 829 | = measured | 498 | 63 | 63 |

### 2.3 What the counts show by themselves (M)

- A hit pair costs about 74 T on the SX-2 and about 73 T on the Hotbit (K = 1). openMSX, without
  the Pico+, takes 72 T.
- From K = 1 to K = 32 the count falls by 1-23 pairs a frame: a few misses in the 8 frames.
- From K = 64 on, 64-69 pairs a frame are left: nearly every pair misses.
- So the cache holds at least 32 and fewer than 64 pages for banks taken in turn. If every pair
  missed at K = 256, a miss would cost 59,736 / 64 − 74 ≈ 860 T.

### 2.4 What the decompiled cache makes of them (I)

The firmware report replays the whole bank test, from the ROM start, through the decompiled
algorithm (`firmware/scripts/picocache_sim.py`). This draft ran the same replay against the
Hotbit's counts, and a finer search next to 55 on both machines (`draft/hotbit_fit.py`,
`draft/fit_fine.py`).

| | SX-2 | Hotbit |
|---|---|---|
| Slot counts tried | 40-64 | 46-60 |
| Exact fit of all nine counts | 55 only | 55 only |
| At 55 slots: a hit pair, the extra time a miss | 74.00-74.03 T, 880-885 T | 73.04-73.08 T, 877-880 T |
| 53-54 slots: the smallest sum of the nine errors | 1 | 2 |
| 49-52 slots | 2-3 | 3-5 |
| 48 slots (image B with music at the start) | 3 | 5 |
| 56-60 slots, 59 (image A) among them | 26-32 | 25-30 |
| 59 slots at K = 64 | 95 pairs a frame, against 68 | 96, against 69 |

- **The counts alone** allow anything from the mid-40s to 55 slots within a few pairs (45-54: 1-3
  on the SX-2, `firmware/fit_grid.txt`; 46-54: 2-5 on the Hotbit), and rule out 56 and more. At
  55 slots a replay with extra early bank writes moves a count by 1 at most; at 59 it moves
  K = 64 by up to 4 (`firmware/perturb.txt`).
- **The firmware can only produce 59, 55, 52 or 48 slots** (section 3.1). Of those, 55 fits both
  machines exactly, 52 and 48 miss by 3-5, and 59 by about 30. So the user's Pico+ ran with 55
  slots on both machines (I).
- **Why 59 fails.** With 59 slots, CLOCK keeps about 37 % hits at K = 64, from the state the
  K = 32 phase leaves (firmware report).
- **The K = 2-32 drops are first loads only:** 1, 2, 3, 7 and 15 misses at a constant hit cost.
  A hit costs no measurable time.
- **The miss cost.** 877-885 T is 245-247 µs: 1.47-1.48 % of a 60 Hz frame (1.24 % at 50 Hz,
  firmware report). 8 KiB in 247 µs or less is 33 MB/s or more from flash.
- **The naive 860 T is 2-3 % low.** At K = 256, 16 of the 514 pairs in the 8 frames still hit:
  banks 0-2, which stay mapped, sit in the list, and the previous phase leaves pages behind
  (`firmware/sim_N55_N59.txt`).

## 3. How the cache works (firmware v2.12)

### 3.1 Two firmware images, four cache sizes (D)

The v2.12 file holds a bootloader and two complete firmware images. The menu's \<INS\> key
("toggle sound source") switches between them and reboots.

| Pico+ state | Image | Menu's bottom line | \<HOME\> info ends | Free SRAM at a ROM start | Slots | For 8000h/A000h |
|---|---|---|---|---|---:|---:|
| FM-PAC off | A, `msxpico_scc` at 10008000h | "FM-PAC disabled \| \<INS\> enable FM-PAC" | 479kB | 490,496 B | 59 | 57 |
| FM-PAC on | B, `msxpico_opll_scc` at 10033000h | "FM-PAC enabled \| \<INS\> disable FM-PAC" | 441kB | 451,584 B | 55 | 53 |
| FM-PAC off, music or WaveGame still playing at the ROM start | A | | | 490,496 − 57,956 B | 52 | 50 |
| FM-PAC on, the same | B | | | 451,584 − 57,956 B | 48 | 46 |

- **Slots = free SRAM / 8 KiB, taken when a ROM starts** (image A: FUN_1000a6c0,
  1000CF8Eh-1000D084h; image B: FUN_100357b8). The arrays hold 64 slots, which no image reaches.
- **The SRAM is empty at a normal start.** Every menu list, and the start of an entry, reset the
  heap first.
- **Music or WaveGame** still playing at the start (01.wav or long.wav in the ROM's SD folder)
  takes 57,956 B first.
- **Not a factor:** the ROM's size, the turbo setting, Nextor or the SCC+ slot expander (another
  core-1 loop, no allocation). A RAM mapper is set up only for the Nextor and disk types.
- The last column is slots − 2, for banks 0 and 1 (section 3.3). Its 50 and 46 are that
  subtraction, made here.

### 3.2 When a page is loaded (D)

- **Only at a select.** Core 1 handles a write to its own slot at 5000h or above with
  (address & 1800h) = 1000h: 5000h, 7000h, 9000h, B000h and their mirrors. It calls the cache
  routine at once, before any read (image A: seed_200799e4 at 20079AE2h, calling FUN_20078558).
- **Reads never load.** They come from the window's page, or from the SCC's registers.
- **A select of a cached bank** only sets its reference bit. A routine that puts back the bank it
  found pays nothing while that bank is cached.
- **A select of a missing bank** costs the whole copy, even if the window is never read.
- **Bank numbers at or above the image's page count are ignored.** In a 1 MiB image, 128-255
  leave the window as it was. In a 2 MiB image every number maps.

### 3.3 Which page is evicted (D)

- At the ROM start, the windows at 4000h-BFFFh get banks 0-3, in slots 0-3.
- The game never selects at 5000h or 7000h (M, openMSX: none in 12 runs). Banks 0 and 1 stay
  mapped, so they are never evicted.
- The first misses fill the empty slots in order.
- After that the policy is CLOCK (second chance):
  - the hand skips every slot mapped in a window: banks 0 and 1, and the banks at 8000h and A000h
    at that moment;
  - it clears each reference bit it finds set;
  - it evicts the first unmapped slot whose bit is clear.
- A page enters with its bit set. Every select of it sets the bit again.
- **What that means (I).** CLOCK acts like LRU while most pages are idle. When every unmapped
  page has its bit set, the hand clears them all in one sweep and evicts in ring order, like
  FIFO. That is always so at the first eviction after the slots fill: each page entered with its
  bit set and the hand had not moved. In the replays the first eviction takes slot 2, which holds
  LC1 since the ROM start, though LC1 was selected a few hundredths of a second earlier; LC1's
  reload then takes slot 3, LC2 (section 4.3).

### 3.4 What a miss costs (D, M, I)

- **The copy (D).** Core 1 copies 8 KiB with its CPU, 1,024 LDRD/STRD pairs from the flash's
  cached XIP window into the slot (FUN_20078558, 20078718h-20078736h). There is no DMA. The
  system clock is 260 MHz. Neither firmware image sets the flash clock, so its divider is the boot
  default (the bootloader at 10000000h was not read).
- **The time (I, fitted to M).** 245-247 µs, 33 MB/s or more.
- **The Z80 waits for the whole copy (I).**
  - During the copy, GPIO20, the pin the PIO drives as /WAIT, is taken from the PIO. In turbo
    disabled and normal it is left undriven; in risky, SIO drives it high (D).
  - The bank test read A000h about 60 T after each select and always got the right byte (M).
    Core 1 answers no read while it copies (D), so /WAIT must hold the Z80 until the copy ends.
  - /WAIT acts on every bus cycle, so the Z80 waits whatever it runs. Code that runs only from RAM
    was not tested.
  - The architecture notes already say the Z80 is held in every mode while a page is copied
    (`docs/MSX_ARCHITECTURE.md`, the MSX Pico+ under Sound).
- **The author's own note (S):** the v1.54 / v2.12 release notes say "Disable cache for NEO
  mappers for now because it causes stuttering in the new MSX dev game "Trapped"".

### 3.5 The SCC and bank 3Fh (D, M)

- 3Fh at 9000h first loads page 3Fh like any bank, a miss if it is absent. Then the SCC is on only
  if the byte is exactly 3Fh (D; M: 7Fh, BFh and FFh do not turn it on).
- **Page 3Fh is part of a level's set whenever the SCC plays.** In v0.1.2 it is bank 63, one of
  the game-over picture's banks (59-64), read only at A000h.
- **While the SCC is on**, reads with (address & D800h) = 9800h return its registers. That is
  9800h-9FFFh, and B800h-BFFFh in the A000h window too. Reads of 8000h-97FFh come from page 3Fh.
- **Writes** with (address & D800h) = 9800h go to the SCC whatever bank is at 9000h. They never
  touch the cache.

### 3.6 ROMs that run from SRAM (D)

- If max(size, 64 KiB) fits the free SRAM, the Pico+ copies the ROM there and needs no cache. The
  limit is 490,496 B (image A) or 451,584 B (image B). 256 and 384 KiB ROMs run that way.
- Our 1 and 2 MiB images run from flash, through the cache.

## 4. Level 1 today

### 4.1 The trace (M, openMSX)

The trace report logged every select, with its PC, and the first read of each bank between two
selects. It ran openMSX 21.0 on a rebuild byte-identical to v0.1.2 and on its EXTJOY test build:
- machines: C-BIOS_MSX2+ (V9958, MSX-MUSIC) and Gradiente_Expert20_64K (V9938, SCC only), both
  60 Hz;
- the title with 62 s of music and its speech, the level start, and 140 s standing in the level;
- a whole cycle: the title, the level, a death with no lives left, the 30 s game-over picture, the
  title again and a second level;
- drives: normal play (57.7 s); the death spot, the busiest place (9-14 game ticks a second), in
  two drives; and a coverage drive with a teleport every 150 game frames (1,209 s on the MSX2+,
  1,583 s on the MSX2).

Checks: the sparse log of reads gives the same simulated misses as a full log of every read, at
every capacity from 16 pages up (24 with banks 0-1 cached). Every select is logged, so the replay
of section 4.3, which uses the selects only, needs no such check. The tracer does not change the
emulation.

### 4.2 The sets (M, openMSX)

| Set | Banks | Running total |
|---|---|---:|
| Level 1 in play (coverage drive) | 2-6, 8-33, 35-45, 48, 50, 51, 63 (3Fh), 77 | 47 |
| A restart after a death adds | 7 (FRONT), 34 (a pattern bank) | 49 |
| The level start alone adds | 46 (attributes), 47 (HUD image), 49 (field atlas), 67 (speech, from the cold start's calibration) | 53 |
| A whole cycle, in its own runs: title, level, game over, title, level | 46 level banks (2-22, 24-28, 31-32, 34-37, 39-49, 63, 67, 77), plus the title picture 52-58, the game over 59-62 and 64, the speech 65-66, the title music 71, 72 and 76 (MSX2: 73) | 63 (its own total, not a running one) |

- Bank 63 (3Fh) is selected for the SCC and never read in play.
- The level makes 18-26 selects a frame on average (18 standing still), 33-45 at the death spot,
  104 at most.

The most banks selected within a window (banks 2 and up):

| Window | Coverage drive | Death spot | Normal play |
|---|---:|---:|---:|
| One 60 Hz frame | 15-16 | 13-14 | 15 |
| One second | 33-34 | 22-26 | 26 |
| Ten seconds | 41-42 | 30-37 | 28 |
| The whole segment | 47 | 36-38 | 29 |

### 4.3 Misses at 55 slots (I: replay)

`draft/clock_replay.py` replays every recorded select, from power-on, through the firmware
report's model of the cache (the decompiled FUN_20078558, unchanged). It drops the EXTJOY build's
extra VBLANK selects, as the trace report did, since the product ROM does not make them.

Limits of the replay:
- openMSX has no holds, so frames and seconds are those of a machine without the cache. The
  order of the selects in a game tick does not depend on time, and at these miss counts the
  shift is small (trace report).
- C-BIOS and the Gradiente stand in for the SX-2 and the Hotbit. Their BIOS selects before the
  game differ; the game's own selects do not.

| Run, segment | Length | Misses at 55 slots: first loads + reloads | Most in a frame | Most in a second | At 48 slots | At 59 slots |
|---|---|---|---:|---:|---|---|
| Coverage, level start | 4.9 s | 37-38 + 0 | 4 | 12-13 | same | same |
| Coverage, play | 1,209 s / 1,583 s | 13 + 0 | 1 | 4 | 13 + 10-12 | same |
| Normal play | 57.7 s | 2 + 0 | 1 | 1 | same | same |
| Death spot | 36.7 s / 54.8 s | 5 + 0 | 1 | 2-3 | same | same |
| Title: from the game's start to the music | 1.2 s | 23-24 + 0 | 2 | 15-16 | same | same |
| Title: 62 s of music | 62 s | 6-7 + 0 | 3 | 3 | same | same |
| Level start after the title | 7.3 s | 21 + 2 | 4 | 11 | 21 + 2 | 21 + 0 |
| Standing in the level | 139.6 s | 0 | 0 | 0 | 0 | 0 |
| Cycle: death spot | 33.6 s / 50.7 s | 4-5 + 3-4 | 1-2 | 2-3 | 4-5 + 8 | 4-5 + 0 |
| Cycle: game-over picture | 30.5 s | 5 + 0 | 1 | 5 | 5 + 1 | 5 + 0 |
| Cycle: the title again, picture | 0.46 s | 0 + 7 | 1 | 4-5 | 0 + 7 | 0 |
| Cycle: the title again, music | 20 s | 0 + 3 | 3 | 3 | 0 + 3 | 0 |
| Cycle: the speech again | 3.1 s | 0 + 2 | 1 | 2 | 0 + 2 | 0 |
| Cycle: the second level start | 4.3 s | 0-1 + 21-23 | 4 | 12 | 0-1 + 22-23 | 0-1 + 7-20 |
| Cycle: the second level, 22.6 s | 22.6 s | 1 + 3 | 1 | 3 | 1 + 3 | 1 + 3 |

Where a cell holds a range or two figures, they come from the MSX2+ and the MSX2 runs.

- **The coverage drive never evicts.** Its 53 banks fill the 53 free slots exactly.
- **Its 13 first loads of play all come in the first 41 s**: sprite banks and the explosion
  frames, the first time each is drawn. The remaining 19-25 minutes have none.
- **The first eviction costs two hot code banks** (`review/first_evictions.txt`). When the 53
  free slots first fill, every page still has the bit it entered with. The hand clears all 51
  unmapped ones and takes slot 2, where the ROM start put LC1 (bank 2). LC1's reload then takes
  slot 3, LC2 (bank 3).
  - Title runs: the slots fill at the level start after the title. LC1 and LC2 had been selected
    0.01-0.05 s before and come back within 0.03 s: the 2 reloads of "Level start after the
    title".
  - Cycle runs: the slots fill at the death spot, 0.1 s after the teleport, 0.02 s after LC1's
    last select. No game-logic bank is selected for the next 3.7 s (MSX2+) or 21 s (MSX2); then
    LC1 comes back, its reload evicts LC2, and LC2 comes back 0.03 s later.
- **The cycle does evict.** Its 63 banks exceed 53, so the title and the game over push level
  pages out. The second level start reloads 21-23 pages, as many as the first start loads.
- **With 48 slots** (46 free), level 1's 47 banks no longer fit. The coverage drive then reloads
  10-12 pages in 20-26 minutes.

### 4.4 The speech (S, I)

- `vm_play` reads the PCM through 8000h with interrupts off. Every 0.74 s it selects the next
  speech bank inside its loop (`msx/music.asm` vm_pg, line 1583; S).
- At 55 slots, holds fall inside that loop (I: replay):
  - after power-on, the speech in the music loads banks 69 and 70 there, and the speech alone
    loads bank 66 there (67 stays cached from the cold start);
  - after a game over, the speech alone reloads 66 and 67 there.
- Each hold stops the stream for about 246 µs. The sample being played lasts about 2.7 sample
  times longer (11,117 samples a second): a stretch, not a gap (I).
- The first title after every power-on has these holds, and the user reported nothing. Whether
  they can be heard was never tested.

### 4.5 The earlier simulations

- The trace report simulated LRU and FIFO caches of 32-63 pages. At 32 pages the coverage drive
  cost 392 misses (LRU, reads only, banks 0-1 pinned) to 2,118 (FIFO, every select, banks 0-1
  cached), up to 9 in a frame. Those capacities do not apply: the cache has 53 free slots.
- Its LRU curve for every select, with banks 0-1 pinned, agrees with the replay. The coverage
  drive's play costs 14 misses at 52 pages and 13 at 56, with 13 first uses (M, openMSX, and
  simulation).

### 4.6 Against the user's experience

The user validated v0.1.2 on the Pico+ on both machines, in every turbo mode, and reported no
glitch and no slowdown. At 55 slots (I):
- play has almost no misses: 13 in the coverage drive's 20-26 minutes, 2 in a minute of normal
  play;
- a level start loads 21-23 pages after a title, 37-42 from a cold start, over 4-8 s. At most 4
  fall in one frame, about 6 % of that frame;
- the HUD split goes late, about 15.7 lines for one frame, when a hold covers its interrupt
  (`msx/isr.asm` lines 58 and 87-91, `sp_late` at line 149; S). The levels report puts that at
  about 1 % of holds (E). That is about 0.2-0.4 late HUD frames per level start and 0.1 in the
  coverage drive's play;
- each speech has 1-2 holds, as above.

This agrees with what the user saw. A slowdown would need many misses a second, and only a set
far above 53 makes them.

## 5. Levels 2-3, the bonus stages and the ending (E)

### 5.1 The model, checked against level 1

- The levels report scripted 40-s scenes from the code's bank readers and the real sprite and
  tile data (`levels/scripts/scenes.py`). Each select counts as a load, as in the firmware.
- It counts banks 0-1 and includes them in its cache size C, so its C compares with 55 slots.
- Its steady-state misses come after a warm-up.
- Levels 2-3 rest on proxies: their sprite blobs converted with level 1's palette, scripted
  scenes and assumed boss animation rates. No coverage run exists for them yet.

Level 1, model against trace, banks 0-1 included in both:

| | Model, level 1 busy | Trace, death spot | Trace, coverage drive |
|---|---|---|---|
| Banks in one second | 33.9 on average, 39 at most | 24-28 at most | 35-36 at most |
| Banks in 5 s (model) or 10 s (trace) | 44 at most | 32-39 at most | 43-44 at most |
| Banks over the scene (40 s) or the segment | 45 | 38-40 | 49 |

- Over seconds the model is conservative. Its busy scene matches the coverage drive's worst
  windows and is above the busy spot.
- Over a whole level it undercounts: 45 against 49. A 40-s scene does not visit every tile, map
  and sprite bank.

### 5.2 The estimates

| Scene, layout | Banks a picture: mean (max) | Banks a second: mean (max) | 5 s max | 40-s total | Misses a second, LRU / FIFO, C = 48 | The same, C = 56 |
|---|---|---|---:|---:|---|---|
| Level 1 walking, today | 22.7 (27) | 25.9 (30) | 32 | 33 | 0.1 / 0.1 | 0.1 / 0.1 |
| Level 1 busy, today | 28.3 (33) | 33.9 (39) | 44 | 45 | 0.1 / 0.1 | 0.1 / 0.1 |
| Level 2 busy, the plan's layout | 29.1 (35) | 34.7 (42) | 45 | 48 | 0.1 / 0.1 | 0.1 / 0.1 |
| Level 3 boss, the plan's layout | 30.1 (36) | 39.9 (46) | 49 | 50 | 0.2 / 1.5 | 0.1 / 0.1 |
| Level 1 busy, all rules | 20.8 (29) | 29.8 (36) | 40 | 41 | 0.1 / 0.1 | 0.1 / 0.1 |
| Level 2 busy, all rules | 21.5 (29) | 30.2 (41) | 43 | 45 | 0.1 / 0.1 | 0.1 / 0.1 |
| Level 3 boss, all rules | 20.1 (26) | 28.0 (33) | 39 | 40 | 0.1 / 0.1 | 0.1 / 0.1 |

The plan's layout is that of `docs/ROM_BUDGET.md` 3.2-3.4: level 2 adds about 2.6 banks of sprite
data and shares RoboCop and the SPERMA frames; level 3 has 2 logic banks, 61 big frames streamed
from 4-5 banks, about 6 banks of sprite data and an overflow code bank used every tick.

Other phases (E, from the budget's sizes, since their code does not exist yet):

| Phase | Banks |
|---|---:|
| Brainstorm | 9-12 |
| Shooting range | 12-18 |
| Ending | 8-11 |
| The title today | 12-16; the trace measured 9-13 selected during its music (M, openMSX) |

### 5.3 What follows (E, I)

- **Over seconds, every scene fits 55 slots.** In steady state the model gives 0.1-0.2 misses a
  second with LRU at 48 pages and 0.1-1.5 with FIFO; at 56 pages, 0.1 for every scene. CLOCK
  usually lies between LRU and FIFO.
- **Over a whole level, levels 2-3 come close to 53.** Without banks 0-1 their 40-s totals are 46
  and 48. Level 1's set in play is 4-6 banks more than its busy scene's (47-49 against 43). The
  same gap would put levels 2-3 at about 50-54. The levels report also puts level 3 at about 50-55
  banks.
- **A level a few banks over the limit** reloads its rarely used banks when they come back. For
  scale: level 1's 47 banks in 46 slots reload 10-12 pages in 20-26 minutes (section 4.3).
- **A new area** (the boss room, new enemies) loads 6-10 new pages over a few pictures (levels
  report). A warm-up at the level start removes most of them.
- **With music or WaveGame at the ROM start** (48 slots), level 3's boss scene (49 over 5 s) no
  longer fits. With all the rules it falls to 39.
- **The bonus stages and the ending** are far below any limit.

## 6. Rules for the layout and the engine

| # | Rule | Cost | Gain | When |
|---|---|---|---|---|
| R1 | A per-level budget in `tools/mkrom.py`: at most 53 banks selected in play | 0 banks; a count per level | Over-budget levels are caught at build time | With the 2 MiB layout |
| R2 | No speculative selects | 0 | No hold for a bank nobody reads | Always |
| R3 | Warm-up: select the level's set before its play field shows | 0 banks; about 10-12 ms once a level | No first loads in play | With the 2 MiB work |
| R4 | Select the speech's three banks before its PCM loop | 0 banks; a few bytes in BANK_MUSIC | No hold inside the PCM loop | Any time |
| R5 | Bank 3Fh and the SCC (below) | 0 banks | Correct on the Pico+ and in openMSX | Its build checks are done (commit 5583758); keep them |
| R6 | Set reducers: SFX, LC23, S1, L3, FLASH, STREAM | see the table below | 1-4 banks fewer each | Only if R1 fails |
| R7 | Split margin: the split's first interrupt 3-4 lines earlier | 684-912 T a frame, 1.1-1.5 % of the CPU | A hold can no longer make the HUD late | Only if play still has misses |

**R1. The budget (D for the limit, I for the rule).**
- Count, per level, every bank its code can select in play:
  - the code and logic banks, the level tables, the map, the tiles;
  - the sprite banks its frames use, the HUD, FIELD, the dynamic and streamed frames;
  - the sound code and data, and 3Fh with an SCC.
- Stop the build above 53, and print the margin. Also print the margin against 46, the music or
  WaveGame case.
- 53 assumes image B with an empty heap, as the fit says. Fix the number only after check 7.1. If
  the menu shows FM-PAC disabled, the limit stays unknown until BT2M-2 runs with FM-PAC on
  (section 8, question 1).
- Level 1 measures 47 in play, 49 with a restart. A static count will be somewhat larger.
- The levels report proposed the same check ("each level's static hot set").

**R2. No speculative selects (D).** A select of a bank that is not cached costs a full hold, even
if the code never reads the window. Restoring a cached bank, as the far calls do, is free.

**R3. A warm-up at the level start (I).**
- With the display off, select every bank of the level's set, then do it again. The second pass
  costs nothing where the first stuck, and reloads what CLOCK evicted meanwhile.
- About 40-50 holds of about 246 µs each: 10-12 ms, once a level.
- R1's count can write the list.
- Gain: the loads of the level's first seconds (21-23 after a title, 37-42 from a cold start,
  21-23 again after a game over) happen before play.

**R4. The speech (I).**
- In `vm_play` (`msx/music.asm` lines 1532-1535), before the loop, select the speech's second and
  third banks, then its first.
- Interrupts are already off there, so nothing can evict them during the 1.68 s of speech.
- Two holds then come before the speech starts, instead of inside it.

**R5. Bank 3Fh and the SCC (S, D).**
- Done at HEAD (commit 5583758): `tools/mkrom.py`'s 8000h check (lines 497-504) covers every bank
  with (b & 3Fh) = 3Fh, so 63, 127, 191 and 255 may hold only data read at A000h (today only the
  pictures). Keep it.
  - On the Pico+ only 3Fh selects the SCC (M).
  - openMSX's KonamiSCC tests (b & 3Fh) = 3Fh, and so do its Yamanooto, Repro V1 and MegaFlashROM
    SCC+ models: there all four select it (S).
- Whatever runs or is read at A000h while 3Fh is at 9000h must sit below B800h. The Pico+ shows
  the SCC's registers at B800h-BFFFh too (D). This rule is already in `docs/ROM_BUDGET.md` 6.1 and
  section 7, and `tools/mkrom.py` checks BANK_MUSIC's part (`scc_time_end`, lines 556-560).
- Never write to 9800h-9FFFh or B800h-BFFFh unless 3Fh is selected. The Pico+ takes those writes
  as SCC writes whatever bank is at 9000h (D).
- Count 3Fh in every level's set (D).

**R6. Set reducers, from the levels report (S, E).** Use them only when R1 fails, cheapest first.

| Reducer | What | Cost | Gain |
|---|---|---|---|
| SFX | The in-game sound code in one bank: the PSG title streams (5,990 B) move from BANK_INPUT to bank 74 (6,965 B free); the SCC effect engine (about 770 B at A603h-A906h) and its 52 waves of 32 B move into BANK_INPUT, below B800h; fx_go and fx_tk map BANK_INPUT; snd_frame maps SCCFX only while a sound plays | 0 banks; every effect checked again | BANK_MUSIC leaves every level's set: −1 |
| LC23 | LC2 and LC3 in one bank (BANK_LC2 = BANK_LC3) | −1 bank; 2,000 B left for the levels' LC2/LC3 code (likely 0.6-1.1 KiB, high 2.4 KiB) | −1, and 1 select fewer a tick |
| S1 | Sprite home banks: `tools/msxsprites.py` puts each group's patterns and colour rows in its home bank; the Z80 code is unchanged | 0 to −1 bank (23 → 22 per blob); level 1's sprites validated again (ids change, pixels do not) | −1 per level; banks per composition: RoboCop 3.54 → 1.74, BOB frames 3.20 → 1.37 |
| L3 | Level 3's per-tick code in its A000h level bank; nothing per tick in the overflow bank | 0 | Keeps the overflow bank out of the set |
| FLASH | The VDP draws the play-field objects' hit flash (budget option 6) | −4 banks; work in field.asm; VDP time per flash. It also eases the frame-id limit | Level 3 loses 27 KiB of silhouettes |
| STREAM | Each streamed animation in one bank, mirrors flipped at upload | 0 to +1 bank | Fewer streamed-frame banks at once |
| HUD | hud_map only when the HUD has work | 0 | −2 banks on idle pictures, none in a level's set |

- S1's constraints: the sprite area stays within 64 banks (15-bit colour ids, 512 a bank), holds
  no bank with (b & 3Fh) = 3Fh, and keeps the silhouette rows (SPR_SIL_*) in the index bank.
- With all of them, the 40-s totals fall from 45 / 48 / 50 to 41 / 45 / 40 (levels 1, 2 and the
  level-3 boss; banks 0-1 included).
- Weighed and not recommended: re-ordering today's pools only, self-contained sprite groups (+14
  banks), tiles numbered by first use, the map stored by columns, the LEVEL tables merged into a
  hot bank, and the run-time pattern flip as a cache measure.

**R7. Split margin (E, levels report).** Only if a level still has holds in play. The R#19 write
comes about 310 T before line V-2's match, so a hold of about 880 T can push it past. Moving the
first interrupt 3-4 lines earlier costs 684-912 T a frame.

## 7. A follow-up hardware test

**Only check 1 is needed to plan the layout.** The decompiled code gives the measured 55 slots
only with FM-PAC on (image B), and the user reported every option disabled. If the menu shows
FM-PAC disabled, check 2 must also run once with FM-PAC on before the budget is fixed. The other
checks close what is open.

1. **The menu (no test ROM).** The Pico+ menu's bottom line shows "FM-PAC enabled" or "FM-PAC
   disabled". The \<HOME\> info line ends in "441kB" (image B) or "479kB" (image A).
2. **BT2M-2: banks taken in turn between 32 and 64.**
   - The list must repeat K banks: entry i = 2 + (i mod K) × (256 div K). Today's builder
     (`msx/banktest.asm` lines 341-344) adds 256 / K with an 8-bit wrap, which works only when K
     divides 256.
   - The firmware report predicts, for the SX-2's timing and the order 1, 2 … 32, 33, 40, 48, 56,
     63, 64, 128, 256:

     | K | 32 | 33 | 40 | 48 | 56 | 63 | 64 | 128 | 256 |
     |---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
     | Image B, 55 slots | 784 | 765 | 752 | 743 | 93 | 65 | 65 | 64 | 63 |
     | Image A, 59 slots | 786 | 767 | 756 | 740 | 732 | 71 | 63 | 63 | 63 |

   - K = 56 separates the two images by a factor of 8. Run it as the Pico+ is set, then once with
     FM-PAC toggled by \<INS\>.
   - The Hotbit's timing gives other counts. The same scripts can predict them.
3. **A RAM-only hold.** Select a bank that is not cached, then count a loop that runs only from
   RAM until the next VBLANK, against the same with a cached bank. A frozen Z80 counts about 880 T
   fewer. This tells whether the SX-2's FPGA honours /WAIT on its own RAM cycles.
4. **The turbo modes.** One run in normal and one in risky. The firmware predicts the same 55
   slots and the same hold. Risky drives /WAIT another way (section 3.4), so its hold could
   differ.

The trace report also proposed a test of LRU against FIFO with one hot bank. The decompiled CLOCK
answers it, so that test is not needed.

## 8. Open questions

| # | Question | Why it matters | Next step |
|---:|---|---|---|
| 1 | The user reported every option disabled, but only image B (FM-PAC on) gives 55 slots. Is FM-PAC on, or did the firmware report miss an allocation? The Hotbit's run, whose settings were not stated, fits 55 slots too | If FM-PAC is on: 53 free slots (57 with it off) and the budget stays at 53. If it is off, the decompile missed 31-39 KiB; if image B makes the same allocation, FM-PAC on leaves 48-49 free slots and the budget must drop to that | The menu check (7.1) first; if it shows FM-PAC disabled, BT2M-2 with FM-PAC on |
| 2 | Do the user or the players run WaveGame or music at the ROM start? | 46 free slots instead of 53. Level 1 then reloads a few pages; level 3's plan layout would not fit | Ask the user. R1 could also report the 46 margin |
| 3 | Does a hold freeze a Z80 that runs only from RAM, on the SX-2's FPGA? | Only the HUD-late estimate and R7 depend on it | Check 7.3 |
| 4 | Are the 1-2 holds inside the speech's PCM loop audible? | R4 removes them anyway | Apply R4, or listen to the first title after power-on |
| 5 | What are levels 2-3's real sets? | The model says close to 53; only real data can tell | R1 once their data exist; the trace report's tracer on their coverage drives |
| 6 | Will a later Pico+ firmware change the slot count or the policy? | Everything here is v2.12 | Re-run the bank test after a firmware update |
| 7 | How often does a hold make the HUD late on the real machines? | It is the visible symptom of a miss | Only if play keeps misses: a test build that selects a cold bank at random points |
| 8 | On a turbo R with the Pico+, is a hold still about 246 µs, so about twice as many R800 cycles? | The R800 split's margins differ (the levels report) | The user has no turbo R; only if a player reports trouble |

Other 2 MiB devices (the SX-2's ESE-MegaSCC+, MegaFlashROM SCC+ SD, 2 MiB MegaRAMs, openMSX) are
not known to have such a cache. The budget therefore costs them nothing (I). The MSX PicoVerse
(RP2040, RP2350; `docs/ROM_BUDGET.md` 6.1) also serves ROMs from a microcontroller's flash; how
it does so was not checked.

## 9. Evidence

**Repository** (as of commit d49294f; the Hotbit's counts were recorded in 71ffdb3):

| Path | What it supports |
|---|---|
| `docs/ROM_BUDGET.md` 6.1 (lines 530-615) | the bank test, both machines' counts, the rules this draft corrects (lines 608-609, 613-614), the 3Fh and B800h rules |
| `docs/MSX_ARCHITECTURE.md` decision 6 (lines 87-94); the MSX Pico+ notes (lines 879-924) | the rule this draft corrects; the turbo modes; the Z80 held during a copy |
| `msx/banktest.asm` lines 332-372, 341-344, 704-722 | the speed test, its list, the timed loop in RAM |
| `tools/msxbanktest.py` | the bank test's builder (`make banktest`) |
| `msx/bank.asm` lines 8-23 | bank_8000, bank_a000, logic_map |
| `msx/sound.asm` lines 160-166, 367-412 | scc_open (3Fh at 9000h), snd_frame, fx_go, fx_tk |
| `msx/music.asm` lines 1165-1170, 1532-1535, 1576-1583 | fx_tick (SCCFX at 8000h), vm_play's first select, vm_pg's select inside the PCM loop |
| `msx/hud.asm` lines 34-38, 109 | hud_map on every picture |
| `msx/sprites.asm` lines 2813-2819, 3296-3303 | pat_now and pc_rows select the pool banks |
| `msx/isr.asm` lines 58, 87-91, 149 | the split's interrupt, the late case, sp_late |
| `tools/mkrom.py` lines 73, 493-504, 556-560 | the 256-bank limit; the 8000h check for every bank with (b & 3Fh) = 3Fh (commit 5583758; before it, lines 470-476 checked 63 and 127 only); BANK_MUSIC's SCC-time data below B800h |

**Scratch files** of 2026-10-26 (a session's scratch directory, not kept in the repository),
under
`/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/`:

| Path | What it holds |
|---|---|
| `re_pico/fw212.bin` | the firmware v2.12, flattened from its UF2 (3 MiB at 10000000h) |
| `space/cache/firmware/notes.txt` | the firmware report's notes, with addresses |
| `space/cache/firmware/rea/dec_20078558.txt`, `ins_20078558.txt` | the cache routine (image A): hit path 2007857Ah-200785AAh, empty-slot fill 200785DCh-20078612h, CLOCK 200786A2h-200786F2h, copy 20078718h-20078736h |
| `space/cache/firmware/rea/dec_1000a6c0.txt`, `ins_1000a6c0.txt` | the ROM start: slot count (1000CF8Eh-1000D084h), banks 0-3 into slots 0-3 (1000D070h-1000D0E5h) |
| `space/cache/firmware/rea/dec_200799e4.txt` | core 1's Konami SCC loop: the select at 20079AE2h, the SCC decode |
| `space/cache/firmware/rea/dec_1000b088.txt`, `dec_1000b3e4.txt`, `dec_1000f4a0.txt`, `dec_1000e804.txt` | ROMs copied to SRAM; the heap at an entry's start; the music and WaveGame buffers |
| `space/cache/firmware/imgB/` | image B: `fwB.elf`, the ROM start (`decB_100357b8.txt`), the cache (`decB_2006f028.txt`), the menu (`decB_10036b60.txt`) |
| `space/cache/firmware/scripts/picocache_sim.py` | the cache model and the bank-test replay |
| `space/cache/firmware/sim_N55_N59.txt`, `fit2d_results.txt`, `fit_grid.txt`, `perturb.txt`, `predictions.txt` | the SX-2 fit and the predictions of section 7 |
| `space/cache/trace/bin/pagetrace.tcl`, `pagesim.py`, `analyze.sh` | the tracer and the LRU/FIFO simulator |
| `space/cache/trace/runs/*/trace.txt[.gz]`, `runs/*/sim.json` | the 12 recorded runs and their analyses |
| `space/cache/trace/key_table.txt`, `summary.tsv`, `results.txt`, `top_frames.txt` | the trace report's tables |
| `space/cache/trace/runs/valid_die_p/validation.txt`, `runs/valid_play/validation.txt` | the sparse log against the full log |
| `space/cache/levels/notes.txt`, `scenes.txt`, `scenes.json`, `breakdown.json` | the levels report's readers, model and estimates |
| `space/cache/levels/scripts/` | scenes.py, breakdown.py, sprlayouts.py, sprbanks.py, sprorder.py, sprhome.py, sprgroups.py, tilesim.py |
| `space/cache/draft/hotbit_fit.py`, `hotbit_fit_scan.txt` | this draft: the bank-test replay against the Hotbit, slot counts 46-60 |
| `space/cache/draft/hotbit_fit_n55.py`, `hotbit_fit_n55.txt` | this draft: the exact fit at 55 slots for the Hotbit, and the 59-slot replay |
| `space/cache/draft/fit_fine.py`, `fit_fine.txt` | this draft: 48-56 and 59 slots on both machines, H step 0.01 T, D step 1 T |
| `space/cache/draft/clock_replay.py`, `clock_replay_product.txt`, `clock_replay_drives.txt` | this draft: v0.1.2's recorded selects through the decompiled cache at 48, 55 and 59 slots |
| `space/cache/review/first_evictions.py`, `first_evictions.txt` | the review of this draft: the first CLOCK evictions of the 55-slot replay (slots 2 and 3, all bits set) |
| `space/cache/review/check_sets.py`, `sets.txt`, `check_restart.py`, `check_restart.txt` | the review: the banks selected per run and segment, the first loads of play and their times, the restart's banks |
| `space/disk/hardware/web/msxpico_downloads.txt` | the Pico+ release notes (v1.54 / v2.12: the cache and NEO mappers) |
| `space/hardware/openmsx_src/RomKonamiSCC.cc` (writeMem), `Yamanooto.cc`, `ReproCartridgeV1.cc`, `MegaFlashRomSCCPlus.cc` | openMSX selects the SCC when (b & 3Fh) = 3Fh |
