# Project rules (Robocop 2 Amiga → MSX2/MSX2+ port)

## Language
- Everything related to code is written in **English**: source code, comments, docstrings,
  tool output messages, generated files and documentation (`.md`).
- Only the chat with the user is in Brazilian Portuguese.

## Mandatory tools
- **Amiga code reverse engineering: REA MCP with the Ghidra provider.** Every question about
  code (what a routine does, who calls it, who writes an address, which data format the code
  reads) must be answered with REA calls (`open_binary` in `raw-binary`/`m68k` mode,
  `procedure_pseudo_code`, `batch_decompile`, `xrefs`, `analyze_function`, `get_call_graph`,
  `read_bytes`, ...). Bulk exports may use the REA CLI (same Ghidra engine and seeds).
  Own scripts only for data formats (ADF, PP20, bitplanes, copper, MSX conversion) or to
  complement what REA does not cover — never as a silent substitute.
- **MSX side: MSX-AI MCP with headless openMSX** (`msx_local_*`) to load, run, inspect
  memory/VRAM and capture screens.

## Hardware reference
- MSX2 Technical Handbook (ASCII 1987, Konamiman's transcription), cloned by `make reference`
  into `reference/MSX2-Technical-Handbook` (git-ignored: third-party text, never commit it):
  `md/Chapter4a.md` / `md/Chapter4b.md` (VDP: registers, sprites, commands and their register
  settings), `md/Appendix3.md` (bit block transfer), `md/Appendix5.md` (VRAM map),
  `md/Appendix6.md` (I/O map). Consult it for VDP and hardware details before guessing.

## Target
- MSX2 (V9938) is the mandatory baseline; detect a V9958 at runtime and use MSX2+ features
  when present. Never MSX2+-only.
- Medium: a Konami SCC MegaROM. The complete game requires a device that runs a **2 MiB**
  Konami SCC image (the user's decision, 2026-10-26); the 0.1.x releases (level 1) are 1 MiB.
  Keep this minimum in `README.md` (Requirements) and in every release's notes. Images over
  1 MiB carry the boot guard (`msx/frontx.asm` `rom_guard`, run by `cold.asm` through `ci_hook`).
- Generic hardware support. The game relies only on what README.md lists as requirements: the
  standard Konami SCC mapper, the PSG, and the optional SCC/SCC+ (in any slot) and
  MSX-MUSIC/FM-PAC. Never tie the design to one device, such as the user's MSX Pico+.
  - A device's quirk (its page cache, how it decodes the SCC) may set a speed target or a
    safety rule that is harmless on every other device.
  - It never becomes a requirement, and never costs content or features.

## Conventions
- `tools/` in Python (stdlib whenever possible), `Makefile`, `docs/`, `tests/`; `build/` is ignored.
- Never commit ADFs, ROMs or data extracted from the game.
- Discovered names and comments live in `analysis/*.sym` (source of truth, because the Ghidra
  session inside REA is ephemeral) and seed Ghidra through `analysis/ghidra_seeds.tsv`.
- For cross-references into data, open the composite RAM image in REA
  (`build/ram/level1_full.bin`, entry point `0x0`), not only the main code.
- Findings ledger: `docs/AMIGA_ANALYSIS.md` (keep verified facts apart from inferences).
