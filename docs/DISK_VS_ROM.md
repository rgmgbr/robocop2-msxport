# Disk or ROM for the whole game

Written on 2026-10-26 to answer the user's question: "Didn't you consider migrating to DSK? Then
we would have no limitations, or would we still?"

Measured against release v0.1.2 (`build/msx/ROBOCOP2_v0.1.2.ROM`: level 1, the title, the game
over and the statistics screen) and `docs/ROM_BUDGET.md`, the whole-game budget of the same day.

Sources:
- three area reports of the same day: the RAM and disk space a disk version needs, the hardware
  it would run on, and the engine rework it implies;
- the MSX2 Technical Handbook, manuals, wikis and forum reports (URLs in section 9);
- the MSX Pico+ firmware v2.12, read with REA and Ghidra.

No emulator was run and nothing was tried on hardware for this document.

Conventions:
- KiB = 1,024 B. A ROM bank is 8 KiB (1 MiB = 128 banks). A memory-mapper segment is 16 KiB
  (1 MiB = 64 segments).
- Basis:
  - **M**: measured on the game's data or code;
  - **S**: from a cited source;
  - **E**: estimated;
  - **I**: inferred from code or sources, not tested.
- Sizes are those of the budget's plan, likely case, unless stated. The plan is one palette for
  every level, one sprite pool, both bonus stages and no photos.
- Read speeds (S):
  - 5 kB/s on a Brazilian port-based floppy interface;
  - 10 kB/s on a typical MSX disk ROM;
  - 17 kB/s on an optimised disk ROM;
  - 130 kB/s on an SD/MMC interface at 3.58 MHz.
- ZX0 decoding costs about 96.5 T-states a byte, about 36 KiB/s at 3.58 MHz (E: cost model). A
  published benchmark gives 58-124 T-states a byte (S).

## 1. The short answer

**A disk version was considered: decision 6 kept the door open for it. It would still have
limits, only different ones.**

- **Storage stops being a limit.** The whole game under the plan packs into 410,305 B of ZX0
  (M for the blocks that exist, the budget's estimates for the rest). That is one 720 KiB disk,
  424 of its 713 clusters. Raw, it takes two disks. Even a palette per level fits one disk as ZX0
  (562 clusters).
- **RAM becomes the limit.** The engine reads its data every frame: tiles, sprites, play-field
  frames, music and speech. A floppy cannot feed it during play, so each phase must be in a
  memory mapper before it starts.
  - Level 3 needs 27 segments of data (431,226 B, E), plus 4 to 7 for DOS and the game's own
    pages.
  - That is a 512 KiB mapper at the very least, and 1 MiB under Nextor or MSX-DOS 2 (E).
  - Most stock MSX2 and MSX2+ machines have 64-256 KiB (S). The MSX Pico+ gives at most 432 KiB
    (S).
- **On the user's own hardware it is a step back.**
  - The SX-2 (2-4 MiB mapper) would run it.
  - The Hotbit with the Pico+ would not reach level 3. It has 27 segments at most, fewer with the
    SCC+ on, against 31 or more needed (E).
  - Both machines already load ROM images from SD.
- **The player waits** (E):
  - on a typical floppy: about 29 s at boot, 8-11 s before each level, 76 s over a whole game;
  - on a Brazilian port-based interface: 46 s at boot, 12-17 s before each level;
  - from SD: 1-5 s before each level, 3-13 s at boot.
- **The screen limits stay.** The VDP, the 128 KiB of VRAM, the Z80, the 25 Hz logic and every
  limit in section 7 of the budget stay. Extra RAM lifts only the map-patch limit.
- **The engine needs a rework** (E).
  - Its two independent 8 KiB windows become one 16 KiB mapper page, and five places read both
    windows at once.
  - About 15-16 assembly files and 400-700 lines change, and a 1.5-3 KiB loader is added.
  - The risk is high.

**Recommendation: B, a 2 MiB Konami SCC ROM** (section 7).
- It has 178 free banks. The plan needs 63, a palette per level about 102, and everything
  including the photos stored raw about 171.
- It keeps 64 KiB of RAM, no loading waits, the SCC in the cartridge and today's engine.
- It is expected to run on all three of the user's targets, once a 256-bank test image passes on
  the Pico+ and the SX-2.
- A disk edition stays possible later as option E: a loader that copies the same image into a
  2 MiB MegaRAM, with no change to the game.

## 2. Why a disk moves the limit instead of removing it

### 2.1 The engine reads its data during play

| Reader | What it reads | When |
|---|---|---|
| Tile cache (`tiles.asm`, tc_upload) | 16×16 tiles from the tile banks | each cache miss while scrolling |
| Sprite engine (`sprites.asm`, `bob.asm`) | compositions, band tables, patterns, colour rows | every frame |
| Play field (`field.asm`) | dynamic and streamed frames | while they are shown |
| HUD (`hud.asm`) | 16 KiB of run-time data | every frame |
| Sound (`music.asm`, `sndplay.asm`) | music streams, SCC effects, the gun's voices | every VBLANK |
| Speech (`music.asm`, vm_play) | PSG PCM | one sample every 322 T-states (11.1 kHz) |
| Game logic | LC1, LC2 or LC3 at 8000h with the level's logic at A000h | every tick |

A floppy cannot serve any of these readers:
- it delivers 5-20 kB/s (S);
- its transfers run with the interrupts off, so the music stops while it reads (S).

Everything a phase reads must therefore be in RAM before the phase starts.

### 2.2 Only one 16 KiB window

The Z80 sees 64 KiB at once, and the game fills three of the four pages (`msx/msx.inc`,
`msx/cold.asm`):
- **page 0**: RAM tables from 0000h to 1FFFh and the entity pages at 2000h-3FFFh;
- **page 1**: the fixed code, 16,149 of 16,384 B;
- **page 3**:
  - the variables from C000h;
  - the IM 2 table at C100h;
  - the stack at F280h-F37Fh;
  - so_x and so_n at F380h-F43Bh;
  - MP_B at F500h-F9FFh.

Only page 2 can change during play.
- A memory mapper switches page 2 as one 16 KiB segment through port FEh, and its registers are
  write-only (S).
- Today's engine uses page 2 as two independent 8 KiB Konami SCC windows. A write to 9000h selects
  8000h-9FFFh and a write to B000h selects A000h-BFFFh.

Five places read both windows at once (I):
1. LC1, LC2 or LC3 at 8000h and the level's logic at A000h call each other.
2. A sprite composition at 8000h is read while the pattern and colour pools are mapped at A000h.
   Any record bank can need any pool bank, so no fixed pairing covers this case.
3. FIELD's code at A000h reads its frames at 8000h.
4. MUSIC's code at A000h reads the streams, the speech and the SCC effects at 8000h. It also
   reaches the cartridge's SCC through bank 3Fh at 8000h.
5. INPUT's gun code at A000h reads gun_tab at 8000h.

### 2.3 The RAM each phase needs

Data segments per phase, packed into 16 KiB segments with the engine reorganised for one window
(E):

| Phase | Bytes, likely | Segments low / likely / high |
|---|---:|---|
| Title: SCC music, speech, picture streamed into VRAM | 312,060 | 19 / 20 / 20 |
| Level 1 | 360,899 | 23 / 23 / 24 |
| Level 2 | 366,302 | 22 / 23 / 24 |
| Level 3 | 431,226 | 26 / 27 / 30 |
| Brainstorm | 261,539 | 16 / 17 / 18 |
| Shooting range | 274,277 | 17 / 18 / 18 |
| Ending | 261,340 | 16 / 17 / 17 |

- Each figure includes the set that stays loaded across phases, so that RoboCop is never
  reloaded. That set is 248,921 B in 16 segments (M): code, HUD, effects, LC1-3, FIELD, RoboCop,
  the common BOBs and the dynamic frames.
- Level 1 and the sound are measured. Levels 2-3, the bonus stages and the new code come from the
  budget.

On top of the data, the mapper must hold (S/I):
- **+3 segments** when everything is loaded once and the disk is never used again: the game's
  page 0, the fixed code in page 1 and the game's page 3.
- **+4** when each phase is loaded through Disk BASIC or MSX-DOS 1. The system's page-3 segment,
  with the BIOS and disk work area, must be kept and swapped back for each load. The 64 KiB the
  machine booted with therefore stay taken.
- **+7** under MSX-DOS 2 or Nextor. They add their two kernel segments and a page-0 segment for
  0005h calls (+6 if F37Dh works there). Both need at least 128 KiB of mapped RAM.

| Loading | Level 3 likely | Level 3 high | Mapper needed |
|---|---|---|---|
| Per phase, Disk BASIC or MSX-DOS 1 | 31 segments, 496 KiB | 34, 544 KiB | 512 KiB (1 MiB high) |
| Per phase, Nextor or MSX-DOS 2 | 34, 544 KiB | 37, 592 KiB | 1 MiB |
| Per phase, today's 8 KiB code/data pairs kept, Disk BASIC | about 39, 624 KiB | — | 1 MiB |
| Everything once at boot | 68, 1,088 KiB | 73, 1,168 KiB | 2 MiB |
| Everything once, the two SCREEN 8 pictures streamed from disk | 62, 992 KiB | 67, 1,072 KiB | 1 MiB (2 MiB high) |
| v0.1.2's content only: per phase / once | 26, 416 KiB / 38, 608 KiB | — | 512 KiB / 1 MiB |

The row "8 KiB code/data pairs kept" copies each code bank next to every data bank it reads
through the other window. It counts 35 data segments for level 3 instead of 27, and it still does
not solve the sprite case without an engine change.

### 2.4 Disk space (M, with the budget's estimates for blocks not yet built)

| Content | ZX0 | Raw |
|---|---|---|
| The plan | 410,305 B, 424 clusters: 1 disk | 1,101,128 B, 1,098 clusters: 2 disks |
| A palette per level | 550,077 B, 562 clusters: 1 disk | 1,449,338 B, 1,442 clusters: 3 disks |
| The plan with the photos (PIC1-7, PICF) and the logos | 579,867 B, 592 clusters: 1 disk | 1,519,944 B, 1,507 clusters: 3 disks |
| A palette per level with the photos and the logos | 719,639 B, 730 clusters: 2 disks | 1,868,154 B, 1,851 clusters: 3 disks |

- **Format.** A 2DD MSX-DOS disk holds 713 clusters of 1 KiB and 112 root entries (S: Handbook
  table 3.1). The game is 57 files.
- **Compression.**
  - Each 16 KiB chunk is packed on its own, so it decodes into one segment. Every stream was
    decoded again and compared.
  - ZX0 comes to 1.023 × zlib -9 (M). The budget's "zlib × 1.15" proxy therefore overstates ZX0
    by about 12 % on this game's data.
- **Raw on two disks**, the split follows the Amiga's two disks:
  - disk 1: boot, code, RoboCop, title, level 1, game over and ending, 597 clusters;
  - disk 2: the bonus stages and levels 2-3, 501 clusters.

  Moving the ending to disk 2 saves the swap back at the end (about 528 clusters).
- **Single-sided 360 KiB disks** (354 clusters) were common on Brazilian 5.25-inch setups. They
  take 2 disks as ZX0 and 4 raw (E).

### 2.5 What RAM buys, and what it does not

RAM would lift these limits (I):
- **The map-patch pools.** With the map in RAM, cells are written in place, so level 2's 893
  changeable cells no longer meet the pools' 2 × 255 cells.
- **Compressing whole tile sheets, maps and pools.** The random-access argument against it
  (budget option 14) goes, since data is unpacked at load time.
- **The R800's data reads.** On the turbo R, the R800 would read data from internal RAM instead of
  the cartridge.

It changes nothing in these:
- the VDP: sprites per line, the speed of its commands;
- the 128 KiB of VRAM: the field atlas's 88 lines, the 256-px dynamic slot;
- the Z80 and the 25 Hz logic;
- the frame ids and the spawn masks;
- the VDP time of level 2's vats;
- the full fixed area.

These are the budget's section 7 limits, and they stay in every option.

## 3. The options side by side

### 3.1 What the player needs, and the user's machines

| | A. 1 MiB ROM | B. 2 MiB ROM | C. Disk + mapper | D. Hybrid ROM + disk | E. Disk into a 2 MiB MegaRAM |
|---|---|---|---|---|---|
| Machine | MSX2 or later, 128 KiB VRAM | same | same | same | same |
| RAM | 64 KiB | 64 KiB | a mapper: 512 KiB in the best case, 1 MiB otherwise | a mapper of 256 KiB or more | 64 KiB, plus a 2 MiB Konami-style RAM |
| Medium | a 1 MiB Konami SCC device | a 2 MiB Konami SCC device | a drive or SD | a ROM device, and a drive or SD | a drive or SD |
| SCC | in the cartridge, or another slot | same | another slot only | in the cartridge | in the device (ESE-SCC), or another slot |
| SX-2 | yes: v0.1.2 runs | expected | yes | plausible | possible with a loader |
| Hotbit with the Pico+ | yes | expected | no: level 3 does not fit | no | the Pico+ runs the ROM itself: that is B |
| openMSX | yes | yes | yes, with extensions | yes | yes |
| The user's targets | 3 of 3 | 3 of 3, untested | 2 of 3 | 2 of 3 at most | B in practice |

"Expected" for B rests on these:
- the Pico+ firmware v2.12's Konami SCC handler accepts any bank below the ROM's size (M: REA on
  the firmware);
- the SX-2's internal ESE-MegaSCC+ holds 2048 KB (S);
- openMSX's KonamiSCC mapper accepts any size (S).

Nothing has been run yet.

### 3.2 Waits, limits, work and risk

| | A | B | C | D | E |
|---|---|---|---|---|---|
| Waits | none | none | at 10 kB/s: boot 29 s, levels 8-11 s; from SD: levels 1-5 s | levels 8-11 s at 10 kB/s | once: 70-100 s at 10 kB/s, 8 s from SD |
| Storage | 50 banks free for 58 / 63 / 73 needed | 178 free for 63 (115 spare) | disks: no limit | ROM for the shared part, disk per level | 178 banks, as B |
| RAM | 64 KiB | 64 KiB | 23-27 data segments a phase | 130-220 KiB a level | the 2 MiB device |
| Engine work | savings: 2 to 4 changes, CPU cost not measured | `mkrom.py`, a 50 B boot guard | 15-16 files, 400-700 lines, a 1.5-3 KiB loader, 600-1,000 lines of Python | 10-12 files, 2-3.5 KiB | none in the game; a 0.3-1 KiB loader per device |
| Risk | medium (frame time) | low | high | high | low for the game |
| Content | one palette, no photos, cuts in the high case | everything in the budget | everything; a palette per level adds 11.6 s to each level load | as C for the levels | as B |

Waits, work and risk are estimates (E). Storage figures are measured or taken from the budget.

## 4. The options

### A. 1 MiB Konami SCC ROM (today's medium)

**Player needs.**
- An MSX2 or later with 128 KiB of VRAM and 64 KiB of RAM.
- A device that runs a 1 MiB Konami SCC MegaROM:
  - a flash cartridge;
  - an MSX Pico or Pico+;
  - a 1 MiB MegaRAM loaded from disk;
  - an OCM such as the SX-2.
- The SCC comes with the cartridge's mapper or from another slot. Without one, the title music
  plays on the OPLL or the PSG.

**The user's machines.** 3 of 3. v0.1.2 runs on the SX-2, on the Hotbit through the Pico+, and in
openMSX.

**Waits.** None.

**What stays limited.** ROM space (ROM_BUDGET sections 4-6):
- The plan needs 58 / 63 / 73 banks against 50 free: 8 / 13 / 23 banks over.
- Two savings bring the likely case to 46 banks, 4 to spare: per-tile tile compression (−11
  banks, M) and the run-time pattern flip (−6, E). The high case stays 6 over.
- Adding the VDP-drawn hit flash and the packing gives 39 likely and 49 high, 1 to spare.
- The other way is to cut content. The plan without the bonus stages takes 49 banks likely: 1 to
  spare, and 4 over in the high case. That changes the game:
  - continues come only from solved Brainstorms;
  - the range's rating sets the next level's enemy hit points ($8060).

**Engine work and risk.** The savings are engine changes whose CPU cost no test has measured (E):
- A tile-cache miss decodes 128 B: about 14-27k T-states, 10-19 % of a 25 Hz tick for each missed
  tile.
- The pattern flip about doubles the CPU per pattern upload. RoboCop's look must then be checked
  again on hardware.

The risk is medium, and it falls on the frame rate.

**Content that stays out.**
- A palette per level, about 102 banks. With one palette, level 3's blue $03A shows with an error
  of dE 52.9.
- The photos, the CMP speech, HI1 tune 1 and the cheat.
- In the high case, possibly the bonus stages.

### B. 2 MiB Konami SCC ROM

**Player needs.** As A, with a device that holds 2 MiB (ROM_BUDGET 6.1; S):
- the MSX Pico+ with firmware v2.12;
- the SX-2 or another OCM-PLD machine (ESE-MegaSCC+ 2048 KB);
- the MegaFlashROM SCC+ SD, Popolon, Yamanooto, Konami Ultimate Collection or Repro V1;
- a 2 MiB MegaRAM: the CIEL 2 MB, the 2014 anniversary MegaRAM;
- probably the Carnivore2: its Konami5 descriptor allows it, but no report was found.

1 MiB MegaRAMs and the original MegaFlashROM SCC+ (1 MiB) can no longer run the game. Decision 2
("MegaRAM is the minimum") becomes "a 2 MiB MegaRAM or flash cartridge".

**The user's machines.** 3 of 3 expected, none tested yet:
- The Pico+ firmware v2.12 accepts any bank number below the ROM's size (M: REA decompile). It
  runs ROMs up to 15 MB (S).
- The SX-2 has a 2048 KB ESE-MegaSCC+ per slot (DIP 4 for slot 1, DIP 5/6 for slot 2; S), and
  the Pico+ in its cartridge slot.
- openMSX's KonamiSCC accepts any size (S).

**Waits.** None.

**What stays limited.** 256 banks, 178 of them free after today's 78 (ROM_BUDGET section 4):

| Scenario | Banks needed, likely | Spare in 2 MiB |
|---|---:|---:|
| The plan | 63 | 115 |
| The plan with all the optional content (photos as ZX0, logos, CMP speech, HI1 tune, cheat) | 101 | 77 |
| Today's pipeline, with a palette per level | 102 | 76 |
| Today's pipeline with all the optional content, photos raw | about 171 | about 7 |

- Banks 63, 127, 191 and 255 may hold only data read at A000h. Writing a bank number with
  (b & 3Fh) = 3Fh to 9000h selects the SCC instead.
- RAM stays at 64 KiB, so the map-patch pools must still be fixed for level 2 (budget section 7).

**Engine work and risk.** Low (ROM_BUDGET 6.1):
- `tools/mkrom.py`: raise the 1 MiB limit, and extend the 8000h check to every bank with
  (b & 3Fh) = 3Fh.
- A boot guard of about 50 B in FRONT. A 1 MiB device wraps, masks or ignores banks 128 and up
  without any error.
- Two rules that already hold must keep holding:
  - BANK_MUSIC's SCC-time data stays below B800h, for the Pico+;
  - no write ever goes to BFFEh/BFFFh or 7FFEh/7FFFh.

Test first:
- Run a 256-bank DIAG image on the Pico+ in both machines and on the SX-2's ESE-MegaSCC+.
- Check that later levels do not touch more banks per frame than the Pico+'s SRAM page cache
  holds. Its 8 KiB page refills freeze the Z80.

**Content that stays out.** Nothing for lack of space. The section 7 limits stay, as in every
option.

### C. Disk version with a memory mapper (DSK or SD files, MSX-DOS or Nextor)

There are two ways to load:
- **C1, per phase.** The boot loads the shared set and the title. Each level, bonus stage and the
  game over then load their own data. This suits floppies, with ZX0.
- **C2, everything once.** The boot loads the whole game, which then plays like the ROM. This
  suits SD.

**Player needs.**
- An MSX2 or later with 128 KiB of VRAM.
- A memory mapper:
  - C1: 512 KiB, but only in the best case: the engine reorganised for one window, a Disk BASIC or
    MSX-DOS 1 loader, and the likely sizes. 1 MiB under Nextor or MSX-DOS 2, in level 3's high
    case, or with today's 8 KiB pairs kept.
  - C2: 1 MiB with the pictures streamed (992 KiB likely), 2 MiB otherwise.
- A 720 KiB drive (one disk as ZX0, two raw), or SD or CF with Nextor.
- An SCC cartridge in another slot, for the SCC music and effects. Without one, the title music
  plays on the OPLL or the PSG and the effects on the PSG.

Stock machines do not have that RAM (S):

| RAM | Machines |
|---|---|
| 64 KiB | most Japanese MSX2 (Panasonic FS-A1, FS-A1F, FS-A1mkII; Sony HB-F1, HB-F1II, HB-F1XD), every MSX2+, Philips VG-8230 and VG-8220 |
| 128 KiB | Philips NMS 8245, 8250 and 8280, VG-8235; Sony HB-F9 |
| 256 KiB | Sony HB-F700 and HB-F900, Panasonic FS-A1ST, the Brazilian ACVS and DDX MSX2+ kits |
| 512 KiB | Panasonic FS-A1GT, Sony HB-G900AP |

- None reaches 1 MiB.
- The FS-A1GT, under its MSX-DOS 2, would run levels 1-2 (30 segments) but not level 3 (34
  segments against its 32) (E).
- Nearly every player would need a 512 KiB-1 MiB expansion (section 5).

**The user's machines.** 2 of 3:
- **SX-2: yes.**
  - Its internal mapper is 2,048 or 4,096 KB (S), with MegaSD and Nextor.
  - For SCC music the game must find an ESE-SCC slot or the Pico+'s SCC+ in a subslot. Otherwise
    it uses the SX-2's own OPLL.
- **The Hotbit with the Pico+: no.**
  - The Pico+'s mapper is at most 432 KiB, 27 segments, and smaller with its SCC+ or FM-PAC on
    (S).
  - Level 3 needs 31 segments under Disk BASIC and 34 under Nextor.
  - Level 1 would need all 27 under Disk BASIC and 30 under Nextor.
  - The Hotbit's own RAM (Ademir Carchano's kit 2.0) is not documented. It may be 64 KiB without
    a mapper (I).
- **openMSX: yes**, with extensions already installed: ram512k, ram1mb, ram2mb,
  SunriseIDE_Nextor, Carnivore2, MegaFlashROM_SCC+_SD.

**Waits** (C1, likely case, seconds; E):

| Load | 5 kB/s, ZX0 / raw | 10 kB/s, ZX0 / raw | 17 kB/s, ZX0 / raw | SD 130 kB/s, ZX0 / raw |
|---|---|---|---|---|
| Boot: code, HUD, effects, RoboCop, common BOBs, title | 45.7 / 75.6 | 28.7 / 38.0 | 21.8 / 22.5 | 13.1 / 3.3 |
| Level 1 | 13.1 / 24.2 | 8.4 / 12.1 | 6.4 / 7.1 | 4.0 / 1.0 |
| Level 2 | 12.5 / 25.1 | 8.0 / 12.6 | 6.2 / 7.4 | 3.9 / 1.0 |
| Level 3 | 17.1 / 36.4 | 11.0 / 18.2 | 8.5 / 10.7 | 5.3 / 1.4 |
| Level 3, high case | 20.6 / 43.2 | 13.2 / 21.6 | 10.2 / 12.7 | 6.4 / 1.7 |
| Brainstorm | 5.9 / 12.4 | 4.0 / 6.4 | 3.2 / 3.9 | 2.3 / 0.8 |
| Shooting range | 8.3 / 19.9 | 5.7 / 10.2 | 4.7 / 6.2 | 3.4 / 1.2 |
| Game-over picture | 7.5 / 9.9 | 4.9 / 5.1 | 3.8 / 3.1 | 2.5 / 0.7 |
| Back to the title after a game over | 13.7 / 22.7 | 8.9 / 11.5 | 6.9 / 6.9 | 4.4 / 1.2 |
| A whole game: boot, 3 levels, each bonus stage twice, ending | 117 / 228 | 76 / 115 | 59 / 69 | 38 / 11 |

- **What a load costs.** Each figure is the read time, plus ZX0 decoding at 3.58 MHz, plus an
  OTIR for what goes into VRAM.
- **ZX0 or raw.**
  - From 17 kB/s up, ZX0 and raw take about the same time.
  - On SD, decoding dominates, and ZX0 loads are 3-4 times slower than raw files.
- **A game over** costs about 22 s at 10 kB/s before level 1 starts again: the picture 4.9 s,
  the title 8.9 s and level 1 8.4 s. A mapper of 1 MiB or more could keep the title and level 1
  instead.
- **The frozen title screen** would first appear after the boot load, and again after each game
  over.
- **C2** loads 1,046,351 B once:
  - about 69 s at 10 kB/s with ZX0, and 102 s raw;
  - about 8 s raw from SD;
  - no waits after that.

**What stays limited.**
- **RAM per phase** (section 2.3). Level 3's high case or Nextor push the mapper to 1 MiB.
- **Disks and swaps** (section 2.4). As ZX0 on 2DD there are none. Raw, there is a swap after
  level 1 and one back to disk 1 after a game over.
- **The SCC.** It is never on the game's medium.
  - Three devices put their SCC in a subslot (S): the MSX Pico+ with its mapper on, the
    Carnivore2 in its default set-up and the MegaFlashROM SCC+ SD.
  - Today's scc_scan skips expanded slots (M: `msx/sound.asm`), so new subslot code is needed.
  - An external SCC in a primary slot, such as a Yamanooto with its flash turned off by a jumper
    (S), should be found by today's code (I).
  - An original Konami cartridge's SCC needs a modification that turns its ROM off (S).
- **The VDP, the VRAM and the CPU.** Unchanged (section 2.5).

**Engine work and risk** (E unless marked):
- **The one-window restructure.**
  - Code must sit next to the data it reads from the other window, or the readers must move into
    the fixed area or get RAM buffers.
  - The sprite records must be copied to RAM before the pools are mapped.
  - One segment variable replaces act_8000 and act_a000, and every routine that maps page 2 must
    restore the whole segment.
- **The sites that know today's medium** (M, `bank_sites.tsv`), outside `bank.asm`:
  - 64 calls or jumps to bank_8000, bank_a000 or logic_map;
  - 31 direct writes to 9000h/B000h in shipped code: music 18, sound 11, sprites 2;
  - 40 calls to the wrappers;
  - 48 calls from the logic to fixed helpers that switch a window.
- **A loader with a DOS/BIOS context switch.** The game overwrites page 0 and the BIOS and disk
  work areas. Each load must therefore:
  - give them back;
  - go from IM 2 to IM 1 and back;
  - mask the VDP interrupts and move the stack;
  - keep MSX-DOS 2's segment images consistent.
- **Stray writes.** In RAM, a stray write into 8000h-BFFFh corrupts level data. The ROM ignored
  such writes.
- **Size.**
  - About 15-16 assembly files and 400-700 lines change.
  - A 1.5-3 KiB loader goes in a load-time segment.
  - The fixed area needs 0.3-0.6 KiB more and has 235 B free, so code must move out first.
  - 600-1,000 lines of Python: a segment packer and a DSK writer.
  - The test harness needs disk machines.
- **A second product** to build and validate on both real machines for every candidate.

The risk is **high**.

**Content that stays out.** Nothing for lack of space:
- **A palette per level** costs no RAM: only one level is in RAM at a time, and each level's
  conversion is within about 3 KiB of the shared one (M). It does cost 69,886 B more of ZX0 per
  level load, about +11.6 s at 10 kB/s, because RoboCop, the common BOBs and the dynamic frames
  are reloaded with each level.
- **The photos** can be streamed from disk into VRAM, with a pause for each.
- **The section 7 limits** stay, except the map-patch pools.

### D. Hybrid: a 1 MiB ROM plus per-level data from disk

**Player needs.** All of these at the same time:
- the ROM cartridge, holding the engine and the shared data (code, RoboCop, HUD, pictures,
  sound);
- a mapper of at least 256 KiB;
- a disk or SD interface.

Each level's own data comes from disk: tiles, map, tables, BOBs, logic and play-field frames,
about 130-220 KiB (E).

**The user's machines.** 2 of 3 at most:
- **SX-2: plausible**, not tested: the Pico+ as the ROM, the internal mapper and MegaSD.
- **The Hotbit with the Pico+: no.** The Pico+ documents a ROM mode and a Nextor/DSK mode, not
  both at once (S). No other drive or mapper is known on the Hotbit.
- **openMSX: yes.**

**Waits.** No boot load. Each level loads about as in C1: 8-11 s at 10 kB/s with ZX0.

**What stays limited.** RAM per level, and the 1 MiB ROM for the shared part (enough with one
palette). The SCC comes from the cartridge.

**Engine work and risk** (E):
- The ROM modules keep their two windows, because the cartridge keeps its bank registers while
  page 2 shows the mapper.
- RAM data is reachable only from fixed code, with page 2 switched to the RAM's slot. This affects
  tc_upload, get_tile, map_write, ar_after, bf_fid, the sprite pools and compositions, and FIELD's
  frames.
- The VBLANK interrupt must save, reselect and restore page 2's slot before any sound-bank write.
- The cartridge must start through H.STKE, so that the disk system is set up before the game takes
  over (S: Handbook chapter 2).
- About 10-12 assembly files and 2-3.5 KiB of new code.

The risk is **high**.

**Content that stays out.** As C for the levels, with one palette.

### E. A disk that loads the 2 MiB image into a MegaRAM or flash cartridge

**Player needs.**
- A drive or SD.
- A Konami-SCC-compatible RAM or writable flash of 2 MiB that the loader knows, either:
  - a 2 MiB Brazilian MegaRAM, made writable through port 8Eh (S);
  - or an OCM ESE-SCC, made writable through its SCC+ mode register (S).
- The SCC comes from the device (the ESE-SCC has an SCC+) or from another slot (Brazilian
  MegaRAMs have none).

This is how decision 2's MegaRAM owners already run the ROM. The same loader would put A's 1 MiB
image into a 1 MiB MegaRAM.

**The user's machines.** It adds almost nothing:
- **The Pico+** loads `.ROM` files itself, so on both machines E is simply B.
- **The SX-2** could take the image into its ESE-SCC through a loader from its own SD card,
  without the Pico+; which loader is still open.
- **openMSX: yes**, with the MegaRAM_2MB and ESE_SCC extensions.

**Waits.** Once at boot (E): about 70 s as ZX0 to 100 s raw at 10 kB/s, about 8 s from SD. No
waits after that.

**What stays limited.** As B, plus the size of the device. One disk as ZX0, two raw.

**Engine work and risk.** None in the game. The loader is 0.3-1 KiB per device class, or an
existing one is used (E). The risk to the game is low.

**Content that stays out.** As B.

### F. Other options the reports raise

| Option | What it would take | Verdict |
|---|---|---|
| F1. Per-level loading into a 512-768 KiB MegaRAM | The engine keeps its 8 KiB windows, and the working set is about 0.5-0.6 MiB (E). C's loader, context switch and per-level bank descriptors are still needed. | It would serve owners of smaller MegaRAMs with a drive. Medium-high work; not now. |
| F2. Two 1 MiB ROMs, as episodes | The shared part, about 61 banks, is stored twice (ROM_BUDGET 6.2). | Changes the game's flow; not recommended. |
| F3. Other mappers: ASCII16 (4 MiB), NEO8/NEO16, Konami SCC with a cartridge's offset register | See ROM_BUDGET 6.2. | Most devices lose the cartridge SCC, or the image runs on one model only; not recommended. |
| F4. A Konami Sound Cartridge as the RAM | An SCC+ with 64-128 KB of RAM (S). | Far below a level's working set; not an option. |

## 5. Hardware that gives a disk version its RAM

| Device | Mapper | SCC | 2 MiB Konami SCC ROM | Price (S) |
|---|---|---|---|---|
| MSX Pico+ | up to 432 KiB with Nextor, less with SCC+ or FM-PAC on | SCC+, in subslot 0 when the mapper is on | expected (firmware v2.12) | 125 EUR |
| SX-2 (OCM-PLD) | 2,048 or 4,096 KB internal | ESE-SCC slots (SCC+) | yes (ESE-MegaSCC+ 2048 KB) | 170-250 EUR |
| Carnivore2 | 1,024 KB, plus 720 KB used like a MegaRAM | SCC/SCC+, in a subslot by default | allowed by its descriptor, no report | 70-115 EUR |
| MegaFlashROM SCC+ SD | 512 KB, optional | SCC/SCC-I | yes | about 90-120 EUR |
| GR8NET | 1,024 KB (or 512 KB) | SCC/SCC+ emulation | not checked | — |
| 8bits4ever SD-512 | 512 KB, as a mapper or a MegaRAM | none | no | about 60 EUR |

- Of these devices, the SX-2 and the MegaFlashROM SCC+ SD also run a 2 MiB Konami SCC ROM, and
  the Carnivore2 probably does (I).
- A disk version would add the players who have a large mapper and no such device:
  - a turbo R FS-A1GT;
  - an SD-512;
  - perhaps a GR8NET;
  - a Brazilian Mega-Mapper or ACVS board with 1-4 MB.
- No survey says how many MSX users have 512 KiB or more. Forum opinions range from "256 kB is
  large enough for most software" to "512kB is the amount that everybody can accept" (S).

## 6. Would we still have limitations?

Yes. A disk changes which limit we meet, not whether we meet one:

| Limit | A. 1 MiB ROM | B. 2 MiB ROM | C. Disk + mapper |
|---|---|---|---|
| Storage for the whole game | 8-23 banks short: savings or cuts | 115 banks spare for the plan, about 7 with everything raw | none: 1 disk as ZX0, 2-3 raw |
| RAM the player needs | 64 KiB | 64 KiB | a 512 KiB-1 MiB mapper, which almost no stock machine has |
| The user's machines | 3 of 3 | 3 of 3 expected | 2 of 3: not the Hotbit with the Pico+ |
| Waits | none | none | at 10 kB/s: about 29 s at boot, 8-11 s a level, 76 s a game |
| SCC | in the cartridge | in the cartridge | another slot only, often a subslot (new code) |
| VDP, VRAM, CPU, 25 Hz | unchanged | unchanged | unchanged |
| Budget section 7 limits | stay | stay | stay, except the map-patch pools |
| Engine change | savings with unmeasured CPU cost | small | large, high risk |

On disk the game no longer runs out of storage. But:
- it runs out of RAM on most machines, including the user's Hotbit;
- it makes the player wait;
- it loses the SCC from its medium;
- it needs the largest engine change of all the options;
- and the screen looks the same.

The 2 MiB ROM removes the storage limit without any of these costs.

## 7. Recommendation

1. **Target B, a 2 MiB Konami SCC ROM, for the whole game.**
   - It holds every scenario in the budget: the plan with 115 banks to spare, a palette per level
     with 76, everything raw with about 7.
   - It keeps 64 KiB of RAM, no waits, the SCC in the cartridge and today's engine.
   - The cost is the 1 MiB devices.
2. **Gate it on the test of ROM_BUDGET 6.1**, before any level-2 data goes in:
   - a 256-bank DIAG image, each bank tagged, with `dg_bnks` extended with 80h, BFh, C0h and FFh;
   - run on the Pico+ in both machines and on the SX-2's ESE-MegaSCC+;
   - the `mkrom.py` changes and the 50 B boot guard;
   - find out which OCM-PLD version the SX-2 runs.

   If the Pico+ fails, fall back to A with the savings, measuring their CPU cost first.
3. **Let the user decide again what only 1 MiB forced:**
   - a palette per level, or the middle way with a palette per level for the background only;
   - the photos (decision 5);
   - the CMP speech and HI1 tune 1.

   These are the user's decisions. The title screen stays as it is.
4. **Do not start a disk version now, and correct the record.**
   - `msx/bank.asm` says a mapper version "only needs to replace these routines", and decision 6
     says bank switching "goes through a single routine". Both are wrong:
     - a mapper switches 16 KiB at a time;
     - outside `bank.asm`, 64 calls, 31 direct register writes and 40 wrapper calls know today's
       medium;
     - five places need both 8 KiB windows at once.
   - Decision 6 in `docs/MSX_ARCHITECTURE.md` and the header of `msx/bank.asm` were corrected
     with this document: "A disk edition loads the ROM image into a 2 MiB MegaRAM or flash
     cartridge (option E). A memory-mapper edition needs the engine reorganised for one 16 KiB
     window."
5. **If a disk edition is wanted once the game is complete:**
   - first E, which changes nothing in the game and serves MegaRAM owners with a drive;
   - C only as a separate project:
     - its stated minimum is Nextor or MSX-DOS 2 with a 1 MiB mapper;
     - SD is its main medium (C2, about 8 s at boot);
     - one ZX0 floppy is the second medium.

## 8. Open questions

| # | Question | Why it matters | Next step |
|---:|---|---|---|
| 1 | Does the user want more storage, or a disk edition for its own sake? | B answers the first; only C or E give a disk | Ask the user |
| 2 | Does a 2 MiB Konami SCC image run on the Pico+ in both machines and on the SX-2's ESE-MegaSCC+? Which OCM-PLD version does the SX-2 run? | It gates B | The 256-bank test image |
| 3 | How much RAM does the Hotbit's kit 2.0 add, and is it a memory mapper? Does the Hotbit have a floppy drive, and which interface? | It decides whether C or D could ever run there | The user checks; a mapper test, or Nextor's largest RAM disk on the Hotbit |
| 4 | How large is the Pico+'s mapper with SCC+ and FM-PAC on, in Nextor and in DSK mode? How fast does it read DSK files? Does its RAM have the ROM's wait states? Can it serve a ROM and Nextor at once? | C and D on the Hotbit | Measure from the MSX side. The firmware's help screen shows a constant 479 kB, not the mapper (M) |
| 5 | For a disk edition: Disk BASIC or MSX-DOS 1 through F37Dh, or Nextor/MSX-DOS 2? Per phase or once? ZX0 floppies or raw SD files? 2DD only, or 1DD too? | 512 KiB against 1-2 MiB, the waits, the disk count | Only if a disk edition is wanted |
| 6 | Which loader puts a 2 MiB Konami SCC image into an ESE-SCC or a 2 MiB MegaRAM? | E | Look for existing loaders |
| 7 | How many MSX users have 512 KiB or more of mapper RAM? | The audience of C | No survey exists |
| 8 | How is level 2's map patched under a ROM: 893 changeable cells against 2 × 255? | It stays open in A and B | Budget section 7 |

## 9. Evidence and sources

**Repository** (as of commit a4ec419):

| Path | What it supports |
|---|---|
| `msx/bank.asm` | the two 8 KiB windows, logic_map, the header's claim about a mapper version |
| `msx/msx.inc` | BANK_8000 and BANK_A000; the page-0 and page-3 RAM maps |
| `msx/cold.asm` | ram_page0, tr_fixram (the turbo R's fixed area in RAM), cpu_set, tiles_upload |
| `msx/sound.asm` | scc_scan (expanded slots skipped), snd_frame |
| `msx/music.asm`, `msx/sndplay.asm` | streams, speech, the SCC through bank 3Fh |
| `msx/sprites.asm`, `msx/bob.asm` | records at 8000h, pools at A000h (pat_now, pc_rows) |
| `msx/field.asm`, `msx/tiles.asm` | FIELD at A000h reading 8000h; tc_upload leaves 8000h mapped |
| `msx/isr.asm` | the IM 2 table, the split's code in page-3 RAM |
| `tools/mkrom.py` | the bank layout, the 1 MiB limit, the 8000h check |
| `docs/ROM_BUDGET.md` | banks, the plan, savings, 2 MiB (6.1), other media (6.2), the limits of section 7 |
| `docs/MSX_ARCHITECTURE.md` | decisions 2 and 6 |
| `reference/MSX2-Technical-Handbook/md/Chapter2.md`, `Chapter3.md`, `Appendix6.md` | H.STKE, disk formats (table 3.1), the F37Dh entry, the memory-mapper ports |

**Scratch files** of 2026-10-26 (a session's scratch directory, not kept in the repository),
under
`/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space/`:

| Path | What it holds |
|---|---|
| `disk/ram/blobs/manifest.json`, `disk/ram/scripts/extract.py` | the bytes v0.1.2 reads from ROM |
| `disk/ram/ramset.txt`, `disk/ram/ramset.json`, `disk/ram/scripts/ramset.py` | RAM per phase |
| `disk/ram/mapper.txt`, `disk/ram/scripts/mapper.py` | the minimum mapper per scenario |
| `disk/ram/bankpair.txt`, `disk/ram/scripts/bankpair.py`, `disk/ram/segments_estimate.py` | today's 8 KiB pairs kept |
| `disk/ram/compress.json`, `disk/ram/scripts/compress.py` | ZX0 sizes, 53 blobs, round trip checked |
| `disk/ram/disks.txt`, `disk/ram/scripts/disks.py` | disk counts |
| `disk/ram/loadtime.json`, `disk/ram/scripts/loadtime.py` | load times |
| `disk/ram/bank_sites.tsv`, `disk/ram/bank_sites.py` | the bank-switching sites |
| `disk/hardware/web/` | the Pico manual and release notes, MSX FAQ pages, CPU magazine no. 27 |
| `disk/hardware/rea/`, `disk/hardware/fw212_strings.txt` | the Pico+ firmware v2.12, read with REA |
| `disk/hardware/scripts/disk_estimates.py` | the hardware report's working-set and disk estimates |
| `hardware/ocm/emsx_top.vhd`, `hardware/ocm/megaram.vhd` | the SX-2's mapper and ESE-SCC |
| `hardware/openmsx_src/MSXMegaRam.cc` | how a Brazilian MegaRAM behaves |
| `pictures/comp/lzpack.py`, `pictures/comp/zx0stats.py` | the ZX0 packer and the decode cost model |

**Web sources:**
- Memory mapper: https://www.msx.org/wiki/Memory_Mapper
- MSX-DOS 2 environment and mapper support: https://map.grauw.nl/resources/dos2_environment.php,
  https://www.msx.org/wiki/MSX-DOS_2
- Nextor 2.1 manual: https://github.com/Konamiman/Nextor/blob/v2.1/docs/Nextor%202.1%20User%20Manual.md
- MSX2 Technical Handbook: https://github.com/Konamiman/MSX2-Technical-Handbook
- Floppy speeds: https://www.msx.org/news/development/en/fastdiskrom-10
- Interrupts during floppy reads:
  https://msx.org/forum/msx-talk/hardware/read-disk-using-every-controller-low-level
- SD speeds: https://hansotten.file-hunter.com/special-msx-hardware/sd-mmc-drive/,
  https://www.msx.org/forum/msx-talk/software-and-gaming/msx-disk-benchmark-tool
- ZX0 decoders and their benchmark: https://github.com/uniabis/z80depacker
- Disk rotation (300 rpm): https://en.wikipedia.org/wiki/List_of_floppy_disk_formats
- MSX Pico and Pico+: https://www.msxpico.com/ (manual.txt, downloads.txt),
  https://msx.org/wiki/Jeroen_Taverne_MSX_Pico
- SX-2: https://www.msx.org/wiki/8bits4ever_SX-2,
  https://www.8bits4ever.net/product-page/sx2-msx2-fpga,
  https://github.com/gnogni/ocm-pld-dev/blob/master/docs/dip-sw%20user%20manual%20v3.9.2-type2.pdf
- Stock machines:
  - https://www.msx.org/wiki/Panasonic_FS-A1ST, https://www.msx.org/wiki/Panasonic_FS-A1GT
  - https://www.msx.org/wiki/Philips_NMS_8245, https://www.msx.org/wiki/Philips_NMS_8250,
    https://www.msx.org/wiki/Philips_NMS_8280, https://www.msx.org/wiki/Philips_VG-8235
  - https://www.msx.org/wiki/Panasonic_FS-A1, https://www.msx.org/wiki/Sony_HB-F1XD,
    https://www.msx.org/wiki/Sony_HB-F1XDJ
  - the MSX FAQ hardware list:
    https://web.archive.org/web/2024/https://www.faq.msxnet.org/hardware.html
- Brazilian hardware:
  - https://www.msx.org/wiki/Sharp_HB-8000, https://pt.wikipedia.org/wiki/HotBit_HB-8000
  - https://msx.org/wiki/Microsol_CDX-2
  - https://archive.org/details/CPU_Ano_3_No._27_199x_Bonus_Rio_Editora_BR_pt
- Devices:
  - https://www.msx.org/wiki/RBSC_Carnivore2
  - https://www.msx.org/wiki/MSX_Cartridge_Shop_MegaFlashROM_SCC+_SD
  - https://www.msx.org/wiki/AGE_Labs_GR8NET
  - https://msx.org/wiki/8bits4ever_SD-512
  - https://www.msx.org/news/hardware/en/yamanooto-a-new-flash-sound-cartridge-for-msx
- MegaRAM and SCC:
  - https://www.msx.org/wiki/MegaRAM, https://www.msx.org/wiki/MegaROM_Mappers
  - https://www.msx.org/wiki/Konami_SCC, https://www.msx.org/wiki/Konami_Sound_Cartridge
- Opinions on how much RAM players have: https://msx.org/ar/node/66079,
  https://www.msx.org/fr/node/67010?page=1
