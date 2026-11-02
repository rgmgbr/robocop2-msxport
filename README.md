# Robocop 2 — Amiga 500 to MSX2/MSX2+/turbo R port

Goal: port ROBOCOP 2 (Ocean/Special FX, 1990) from the Amiga 500 to MSX2, MSX2+ and MSX turbo R,
reusing as much of the original logic and graphics as the target machine allows. The MSX2
(V9938) is the mandatory baseline; the MSX2+ (V9958) is detected at run time and used when
present, and on a turbo R the game runs on the R800 (the title on the Z80; see
[docs/TURBO_R.md](docs/TURBO_R.md)).

- Amiga reverse engineering: tools in `tools/` + REA (Ghidra).
- MSX development and testing: headless openMSX through the MSX-AI MCP.

The ADFs live in `amiga/` and **must not be committed or distributed**, and neither must
anything generated in `build/`.

## Requirements

- An MSX2, MSX2+ or MSX turbo R with 128 KiB of VRAM and 64 KiB of RAM.
- A cartridge device that runs a **Konami SCC MegaROM** (the Konami5 mapper) of the game's size:
  - releases 0.1.x, with level 1 only: **1 MiB**;
  - **the complete game: 2 MiB**, the minimum device for it (the user's decision, 2026-10-26:
    [docs/DISK_VS_ROM.md](docs/DISK_VS_ROM.md)). The complete game (the three levels, both bonus
    stages and the ending; in development, not released yet) is a 2 MiB image (163 of its 256
    banks). A 2 MiB image checks the device at power-on: on one that holds less, the game shows
    "ROBOCOP 2 needs a 2 MB Konami SCC cartridge or MegaRAM." and stops.

  No original cartridge is that large, so the game needs one of these: a flash or multi-ROM
  cartridge, a MegaRAM, an FPGA MSX, or an emulator.

| Device | 2 MiB Konami SCC ROM |
|---|---|
| MSX Pico+ (firmware v2.12) | works: tested on an SX-2 (MSX2+) and an MSX2 Hotbit, 2026-10-26 |
| openMSX (`-romtype KonamiSCC`) | works |
| OCM-PLD machines (SX-2 and others) | internal ESE-MegaSCC+ of 2048 KB, loaded by a ROM loader; not tested |
| MegaFlashROM SCC+ SD, Yamanooto, Popolon Flash-ROM SCC, Konami Ultimate Collection | 2 MB supported, by their documentation and users; not tested |
| 2 MiB MegaRAM (CIEL 2 MB and similar) | supported, loaded from disk; not tested |
| Carnivore2 | one forum report of a 2 MB Konami SCC game running; not tested |
| MSX PicoVerse | has the Konami SCC mapper, with a reported 2 MB limit; not tested |
| 1 MiB devices (1 MiB MegaRAM, the original MegaFlashROM SCC+) | releases 0.1.x only |

- Sound: always the PSG. An SCC or SCC+ (in the game's cartridge or in another slot) and
  MSX-MUSIC / FM-PAC are used when present, by the title music, the in-game effects, the bonus
  stages' music and effects and the ending's tune.

Details: [docs/ROM_BUDGET.md](docs/ROM_BUDGET.md) 6.1 (the devices, the bank test) and
[docs/MSX_ARCHITECTURE.md](docs/MSX_ARCHITECTURE.md) (decision 2, "2 MiB").

## Playing

The complete game, in order:

1. The title (fire starts a game).
2. Level 1, the River Rouge complex, then its statistics.
3. The bonus stages: Brainstorm (the chip puzzle; solving it gives a game credit), then the shooting
   range (its rating sets the next level's enemy hit points).
4. The level-2 briefing and level 2, the Tokugawa brewery, then its statistics.
5. Both bonus stages again (Brainstorm's second set of boards, the range's darker street).
6. The level-3 briefing and level 3, the Civic Centrum: up through the building to the roof, where
   Cain, now RoboCop 2, appears; the chase down through the car park ends with his death.
7. The game completed: WELL DONE, with the ending's tune (no statistics after level 3, as in the
   original).
8. The high-score entry, when the score enters TODAYS BEST (six names and scores, kept from the
   power-on), then the table.
9. The title again.

A game over shows the game-over picture, then the high-score entry when the score enters the
table; when Brainstorm has given a credit, a continue screen follows, and fire restarts the same
level with two lives and the score kept, the map as it was left (the first offer can come in level
2).

**Controls.**
- RoboCop: joystick port 1 (button A fires, button B jumps, also while walking or firing and from a
  crouch, up aims) or the keyboard as on the Amiga (cursor keys, up jumps; SPACE or RETURN fire). The
  bonus stages take the same joystick or keys.
- The text screens (statistics, briefings, the stages' intros and results, WELL DONE, the table) end
  with fire after their first second; the game-over picture after 30 s or with fire; the ending's
  tune with fire (pressed once released); the continue screen continues with fire.
- The name entry is typed on the MSX keyboard, as the original's on the Amiga's: the letters A-Z,
  the digits (the main row or the keypad) and SPACE, up to nine characters; BACKSPACE deletes the
  last one, RETURN ends the name. No joystick and no time limit, as the original.

**Sound.** The title music, the bonus stages' tunes and the ending's tune play on the chips the
machine has: with an SCC the melody there and the drums on the PSG, or on MSX-MUSIC / FM-PAC's
rhythm when there is one; MSX-MUSIC / FM-PAC alone; or the PSG alone. The in-game effects use the
SCC when there is one, else the PSG.

## Quick start

```sh
make extract    # extracts and decrunches the 27 files of both disks
make list       # file table, classification and disk coverage
make pics       # renders the static screens into build/png/
make test
```

For the Capstone listing (optional, complements Ghidra):

```sh
make setup      # creates the venv in ~/.venvs/msxports (outside iCloud)
make disasm     # build/dis/main_8000.s
```

## Code reverse engineering (REA + Ghidra)

Project rule (see [CLAUDE.md](CLAUDE.md)): all Amiga code analysis goes through REA with
the Ghidra provider; the MSX side uses MSX-AI with headless openMSX.

| Item | Location |
|---|---|
| Ghidra 12.1.4 (`mac_arm_64` natives built) | `~/Applications/ghidra_12.1.4_PUBLIC` |
| JDK 21 (Homebrew, keg-only) | `/opt/homebrew/opt/openjdk@21` |
| `rea` MCP registration | user scope: `GHIDRA_INSTALL_DIR`, `JAVA_HOME`, `REA_GHIDRA_SEED_FILE` |

```sh
make ram      # per-level RAM images in build/ram/ (files at their real addresses)
make seeds    # analysis/ghidra_seeds.tsv: entries reached only through jump tables
make sprites  # Ghidra assembly via the REA CLI -> BOB catalogue and RoboCop frames
```

In REA, open the whole RAM of a level (entry at `$0`, which holds `JMP $8000`):

```text
open_binary(path=".../build/ram/level1_full.bin",
            format="raw-binary", architecture="m68k", entry_point="0x0")
```

The seeds are re-read on every `open_binary`; changing the server registration requires
reconnecting `rea` (`/mcp`). Names and comments live in `analysis/main_8000.sym`, the
source of truth, because the Ghidra session inside REA is ephemeral.

Brainstorm's code (PUZL, loaded at `$17100`) has an image and a seed file of its own; never
seed a level image with them (those addresses hold other files there):

```sh
python3 -I tools/ramimage.py build/extracted build/ram/puzl RB1 MU1 DATAL1 SPERMA PERMA PUZL_25
python3 -I tools/ghidra_seeds.py build/extracted/boot/main_8000.bin analysis/main_8000.sym \
    analysis/ghidra_seeds_puzl.tsv analysis/puzl_17100.sym
```

Open `build/ram/puzl_full.bin` as above with `REA_GHIDRA_SEED_FILE` set to
`analysis/ghidra_seeds_puzl.tsv`; PUZL's names live in `analysis/puzl_17100.sym`.

The shooting range's code (FRNG, ByteKiller-crunched, decrunched to `$1EA00`) likewise:

```sh
python3 -I tools/ramimage.py build/extracted build/ram/frng RB1 MU1 DATAL1 SPERMA PERMA FRNG@1ea00
python3 -I tools/ghidra_seeds.py build/extracted/boot/main_8000.bin analysis/main_8000.sym \
    analysis/ghidra_seeds_frng.tsv analysis/frng_1ea00.sym
```

Open `build/ram/frng_full.bin` with `REA_GHIDRA_SEED_FILE` set to `analysis/ghidra_seeds_frng.tsv`
(through the REA CLI, as the MCP server names the main seed file: `docs/AMIGA_ANALYSIS.md`, *The
shooting range*); FRNG's names live in `analysis/frng_1ea00.sym`.

## MSX build

```sh
make msx      # the conversions: joint palette, the sprite pool (RoboCop and the three levels' BOBs), the three levels' tiles, maps, attributes and palettes, level 3's frame cache, HUD and its run-time data, RoboCop's logic tables, both stages' graphics (Brainstorm's two visits), tables, texts, music and effects, the ending's tune (build/msx/)
make rom      # MegaROM (KonamiSCC/MegaRAM mapper) in build/msx/rc2.rom
make rom ROMOPTS="DEMO_ACTORS=2"    # build options (tools/mkrom.py OPTIONS: DEMO_ACTORS, FORCE_V9938, PZ_TEST, PZ_LEVEL, TAG, ...)
make rom ROMOPTS="JOY=70:30:r,105:10:d"   # test ROM playing a joystick script instead of the controls
make rom ROMOPTS="PZ_TEST=1"        # test ROM: at power-on straight into Brainstorm, then the shooting range, then the title
make rom ROMOPTS="PZ_TEST=1 PZ_LEVEL=2 TAG=2"   # its second visit's boards; TEST 2 on the bonus text screens
make rom ROMOPTS="PZ_TEST=2"        # test ROM: at power-on straight into the shooting range, then the title
make rom ROMOPTS="LV_TEST=2"        # test ROM: at power-on the level-2 briefing and level 2 (LV_CARRY's score, lives, credits, rating)
make rom ROMOPTS="LV_TEST=3"        # test ROM: at power-on the level-3 briefing and level 3, the same way
make rom ROMOPTS="END_TEST=1"       # test ROM: at power-on the game completed (WELL DONE, the ending's tune, the high-score entry)
make rom ROMOPTS="END_TEST=2 LV_CARRY=10050:0:1:1"   # test ROM: at power-on a game over, the entry, the continue offer
make rom ROMOPTS="CHEAT=1"          # F5 ends the level (level 3: the game completed), F4 fills the energy (the original's F10/F9)
make rom ROMOPTS="CHEAT=1 INVULN=1" # the same, and no hit or time out kills RoboCop (the play tests' builds)
```

The game's flow is under "Playing" above. Levels 2 and 3 and the ending are in development on the
branch `level2` and not released yet: they go out only complete and tested
([docs/LEVEL2.md](docs/LEVEL2.md): level 2's plan, as built; [docs/LEVEL3.md](docs/LEVEL3.md): level 3's plan
and, in its sections 3.9-3.11, what was built; [docs/ENDING.md](docs/ENDING.md): the ending and the high
scores).
- Brainstorm (its intro, the chip puzzle, its result): [docs/BRAINSTORM.md](docs/BRAINSTORM.md).
  Solving it gives a credit. Its second visit, after level 2, has its own boards and Ellen's face.
- The shooting range (its intro; a crosshair over a street of targets, 25 shots and 2:00; its
  result and rating, or OUT OF TIME.): [docs/RANGE.md](docs/RANGE.md). The 320-pixel street is
  kept 1:1 and a 256-pixel view follows the crosshair. The rating sets the next level's enemy hit
  points; the second visit has a darker palette.

Their music and sound effects (each stage's own tune and effects, by the original's rules) play
on the chips the machine has, as the title music does: with an SCC the melody there and the drums
on the PSG, or on MSX-MUSIC / FM-PAC's rhythm when there is one; MSX-MUSIC / FM-PAC alone; or the
PSG alone (`tools/msxtune.py` converts them, `msx/tune.asm` plays them). Build options
(`tools/mkrom.py`):

| Option | Effect |
|---|---|
| `PZ_TEST=1` | power-on without the title: level 1's set-up, then Brainstorm and the shooting range once, then the title and a new game |
| `PZ_TEST=2` | the same with the shooting range alone |
| `PZ_LEVEL=1` or `2` | `PZ_TEST`'s visit: after level 1 (default) or after level 2 (Brainstorm's second set of boards and Ellen's face, the range's darker palette) |
| `LV_TEST=2` or `3` | power-on without the title: level 1's set-up, then that level's briefing and the level once, as the product reaches them after the range; later games as the product's |
| `END_TEST=1` | power-on without the title: level 1's set-up, then the game completed (WELL DONE, the ending's tune, the high-score entry and the table) with `LV_CARRY`'s score, then the title and a new game |
| `END_TEST=2` | the same with a game over instead: the game-over picture, the high-score entry, the continue offer with `LV_CARRY`'s credits (a continue restarts level 1) |
| `LV_CARRY=S:L:C:R` | `LV_TEST`'s or `END_TEST`'s carry: score, lives, credits and the rating 0-3 (SHARP to POOR; default `10050:2:0:1`) |
| `CHEAT=1` | F5 ends the level, F4 fills the energy (the original's F10/F9 cheat keys) |
| `INVULN=1` | with `CHEAT=1`, for play tests: no hit or time out kills RoboCop (the energy full again at every tick, the timer stops at 0:00), and a death that still comes (level 2's vats) takes no life (refused without `CHEAT=1`) |
| `VAT_ANIM=1` | level 2's vats redrawn as they bubble, as built for test7 (a comparison only: the product shows them as static images, the map's own look, the user's choice for the game's speed; `docs/LEVEL2.md` 3.5) |
| `VAT_TICK=1` | with `VAT_ANIM=1`: the vats redrawn more often, for a little of the game's speed (the other comparison; refused without `VAT_ANIM=1`) |
| `DAMAGE_X=n` | the enemies' damage to RoboCop times n, 1-3 (default 2, the user's choice; 1 = the original, for the trace tests): their bullets, touching them, level 2's drips; the missiles (enemy bullet types 1 and 2, level 2's drone, level 3's rocket and Cain's bombs and missiles) keep the original's damage in every build |
| `FLASH_LOOK=6` or `7` | the look of an enemy's hit flash, for comparison (nothing decided: every build without it shows one white picture for each hit): `6` at most one white picture in 4 per enemy, `7` the enemy white in the game tick of a hit and the 3 ticks after it, every hit starting the 4 ticks again, so hits at most 4 ticks apart keep it white (with `CAD_MAX` and `CAD_HOLD` at most 4) ([docs/MSX_ARCHITECTURE.md](docs/MSX_ARCHITECTURE.md), "The hit flash's look") |
| `TAG=n` | a test candidate (1-99): the text screens (the stages', the briefings, the ending's and the high scores') show TEST n below their text |
| `RG_ADJ=0` | the range's camera in 16-pixel steps without R#18 (the VDP's horizontal adjust), for a VDP that ignores R#18 |
| `EXTJOY=1` | the trace harness's input (`tools/openmsx_rc2.tcl`); the stages' timers stand still |

`make matrix` runs the ROM headless on a fixed set of generic set-ups (`tools/msxmatrix.py`):
MSX2, MSX2+, turbo R, 50 Hz, a disk interface before the cartridge, a slot expander, an FM-PAC,
and a 2 MiB MegaRAM with an SCC, with an SCC+ or alone. `make matrix OMHOME=DIR` uses an openMSX
home that has those machines, such as the MSX-AI MCP's (a leading `~/` is expanded; default:
`$OPENMSX_HOME`, else `~/.openMSX`).

The tool waits for the title on every set-up, so a `PZ_TEST` (or `LV_TEST`, `END_TEST`) build, which starts without the
title, FAILs under `make matrix`. Check such a build with the tool itself (add `--home DIR` for
another openMSX home):

```sh
python3 -I tools/msxmatrix.py build/msx/rc2.rom --labels build/msx/rc2.labels --no-title
```

With `--no-title` it waits for no title and presses no key: the game's tick counter (`tick_n`,
which the stage's passes advance) must go up between samples at 20 s and 27 s from the power-on,
with the display on and no DI; HALT.

The engine is Z80 assembly in `msx/` (z80asm 1.8). Run it in openMSX with
`carta insert build/msx/rc2.rom -romtype KonamiSCC`. The game runs at the PAL original's 25 game
frames per second on 50 and 60 Hz machines (`msx/player.asm`); the controls are under "Playing".

The game logic is checked against the original: `tools/amigaemu.py game --ram
build/ram/level1_full.bin --gframes N --joy F:C:KEYS ... --trace A.jsonl` runs the Amiga code
with a joystick script and traces its variables per game frame; a ROM built with the same
script (`JOY=...`) traced with `rc2_trace FILE N ADDR TARGET` (`tools/openmsx_rc2.tcl`, the
`tick_start` and `game_tick` addresses from `build/msx/rc2.labels`) is compared with
`tools/tracecmp.py A.jsonl FILE`.

Brainstorm's logic is checked the same way, pass by pass (the commands, the drives and their
results: [docs/BRAINSTORM.md](docs/BRAINSTORM.md) 4.5). The bench plays a drive and traces
PUZL's state (`PY=~/.venvs/msxports/bin/python`):

```sh
$PY -I tools/puzlsolve.py build/emu/pz_solve1          # the four boards solved: pz_solve1.drive
$PY -I tools/amigaemu.py puzl --pframes 2000 --drive build/emu/pz_solve1.drive \
    --trace build/emu/pz_solve1_ram.jsonl --trace-ram
python3 -I tools/mkrom.py build/msx/level1 OUT/rc2_pz1.rom EXTJOY=1 PZ_TEST=1   # OUT outside build/msx
```

then, in headless openMSX, `source tools/openmsx_rc2.tcl` and `rc2_pz_drive ROM LABELS FILE 2000 0
build/emu/pz_solve1.drive` (poll `::rc2_trace_done`; `rc2_pz_arm` reaches the stage from a played
level 1), and `tools/puzlcmp.py build/emu/pz_solve1_ram.jsonl FILE` prints "0 differ" and both
results. `tools/msxpuzl.py render` draws a display page from its shown state in a RAM dump, to
compare with the screen.

The shooting range's logic is checked the same way: `tools/frngbot.py` makes a drive,
`tools/amigaemu.py frng` traces the original, an `EXTJOY=1 PZ_TEST=2` build traced with
`rc2_fr_drive` is compared with `tools/frngcmp.py`, and `tools/msxrange.py render` draws a page
(commands: [docs/RANGE.md](docs/RANGE.md) 4.5). The whole regression of both stages, level 1 and
the title runs from `tools/bstest/regress.sh` ([docs/HARNESS.md](docs/HARNESS.md) 5.19).

Checking a run in headless openMSX (MSX-AI `msx_local_cmd`): `source tools/openmsx_rc2.tcl`,
then `rc2_snaps DIR N SECS` (or `rc2_snaps_when` for a condition) saves VRAM, RAM and VDP
registers; `tools/checkrun.py DIR build/msx/level1 build/msx/hud` rebuilds every frame
(`tools/msxframe.py`) and compares it pixel by pixel with the map, the HUD and every sprite
object (RoboCop and the BOBs) as converted, reports lines where the SAT holds more than 8
sprites and checks that the tile area of VRAM is untouched. `rc2_prof SECS LOG LABELS` +
`tools/proflog.py LOG` profile the main loop (addresses from `build/msx/rc2.labels`);
`rc2_count_too_fast` counts lost VRAM writes.

## Documentation

- [Amiga reverse-engineering ledger](docs/AMIGA_ANALYSIS.md)
- [MSX2/MSX2+ feasibility measurements](docs/MSX_FEASIBILITY.md)
- [ROM budget for the whole game](docs/ROM_BUDGET.md)
- [Disk or ROM for the whole game](docs/DISK_VS_ROM.md)
- [The MSX Pico+ page cache and the 2 MiB ROM](docs/PICO_CACHE.md)
- [MSX port architecture and decisions](docs/MSX_ARCHITECTURE.md)
- [MSX turbo R support (R800)](docs/TURBO_R.md)
- [Brainstorm, the bonus stage after level 1](docs/BRAINSTORM.md)
- [The shooting range, the second bonus stage](docs/RANGE.md)
- [Level 2, the Tokugawa brewery: the plan, as built](docs/LEVEL2.md), and its steps' accounts
  ([docs/level2/HANDOFF.md](docs/level2/HANDOFF.md))
- [Level 3, the Civic Centrum: the plan, and what was built](docs/LEVEL3.md)
- [The rest of the game: the user's last changes, level 3 and the ending, step by step](docs/level3/HANDOFF.md)
- [The game completed and the high scores](docs/ENDING.md)
- [The bonus stages' acceptance harness (`tools/bstest/`)](docs/HARNESS.md)
