#!/usr/bin/env python3
"""Compares the MSX port's map, as the game changed it, with the original's after the same game frames.

The original's map is in a chip RAM dump of the bench (tools/amigaemu.py game --dump, after the
same driven input as the port: --drive): the level's rows (the size of LEVEL.map: 51 in level 1, 50
in level 2) of 160 map words from $38000 (tile offset in bits 7-15, attributes in bits 0-6). The port's is in an rc2_snap directory (tools/openmsx_rc2.tcl,
taken when the driven trace pauses: rc2_drive_trace with n rows from game frame 0 stops at the
start of game frame n - 1, the bench at the start of game frame --gframes, so --gframes n - 1):
ram0.bin (page-0 RAM) and ramf.bin (F000h-FFFFh). Each cell's tile is its map patch's (msx/msx.inc MP_ROW, the even rows'
pool MP_A, the odd rows' MP_B: column, next, tile low, tile high) or the ROM map's (LEVEL.map),
its attributes the packed map's code (ATR_RAM0 / ATR_RAM1, even column in the high nibble) in
atr_lut; the original's tile is LEVEL.otile's for its word's offset (msx/tiles.asm map_write).
Level 2's vat cells (docs/LEVEL2.md 3.5, the vat rule) are no patches: their tile is T0, T1 or T2 at
the look the logic last gave their column (vat_shown, F012h), the word the original's map holds there
(vat_layout: tools/mapcells.py vat_tables, as tools/mkrom.py builds them).
Prints the patches in use and the lost counters, how many cells differ in tile or attributes
and the first 40 of them; exit code 1 if any.

usage: mapcmp.py BENCH_DUMP.bin SNAP_DIR LEVEL_PREFIX     (e.g. ... build/snap/end build/msx/level1)
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COLS = 160
AMIGA_MAP = 0x38000
MP_ROW = 0x0A00
MP_POOL = (0x0B00, 0xF500)                  # even rows, odd rows
MPF_COL, MPF_NEXT, MPF_TILEL, MPF_TILEH = 0x000, 0x100, 0x200, 0x300
ATR_RAM0, ATR_RAM1, ATR_LUT = 0x108C, 0x0910, 0x1F8C
ATR_LOST, MP_LOST = 0x1082, 0x1084
VAT_SHOWN, VAT_DISP = 0xF012, 0xF079        # msx/msx.inc: per vat column its look, the looks drawn


def vat_layout(level: Path) -> dict | None:
    """The level's vats (level 2: tools/mapcells.py vat_tables, as tools/mkrom.py builds them) for
    LEVEL_PREFIX: None for a level without; else {"cells": {(row, column): (index in vat_shown, row in
    the vat)}, "tiles": [T0[16], T1[16], T2[16]]} (the tiles: the sheet's, LEVEL.otile's)."""
    m = re.fullmatch(r"level(\d+)", level.name)
    if not m or m.group(1) != "2":
        return None
    sys.path.insert(0, str(ROOT / "tools"))
    import mapcells
    from amitab import parse
    img = (ROOT / "build/ram/level2_full.bin").read_bytes()
    rows = len(level.with_suffix(".map").read_bytes()) // (COLS * 2)
    tab, _ = mapcells.vat_tables(img, {r["label"]: r for r in parse(ROOT / "analysis" / "amiga_tables.tsv")},
                                 "l2", COLS, rows, level.with_suffix(".otile").read_bytes())
    cells = {}
    for v in range(8):
        c0, n, r0, nr, first = tab[0x40 + 8 * v:0x45 + 8 * v]
        if c0 == 0xFF:
            continue
        for k in range(n):
            for j in range(nr):
                cells[(r0 + j, c0 + k)] = (first + k, j)
    tiles = [[struct.unpack_from("<H", tab, 0x80 + 32 * t + 2 * d)[0] for d in range(16)] for t in range(3)]
    return {"cells": cells, "tiles": tiles}


def vat_tile(layout: dict, cell: tuple[int, int], look: int) -> int:
    """The tile of a vat cell ((index, row in the vat): vat_layout's) at a look: T0 in its first row, then
    T1 and T2 alternating."""
    j = cell[1]
    return layout["tiles"][0 if j == 0 else 1 if j % 2 else 2][look]


def vat_look(ramf: bytes, idx: int, page: int | None) -> int:
    """A vat column's look from RAM F000h-FFFFh: vat_shown's (page None), or what that page shows
    (vat_disp's nibble: 8 + (look & 7), the half vat_shown's; none drawn: vat_shown's)."""
    shown = ramf[VAT_SHOWN - 0xF000 + idx]
    if page is None:
        return shown
    nib = (ramf[VAT_DISP - 0xF000 + idx] >> (4 * page)) & 15
    return (nib & 7) | (shown & 8) if nib & 8 else shown


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    bench = Path(argv[1]).read_bytes()
    snap = Path(argv[2])
    p0, pf = (snap / "ram0.bin").read_bytes(), (snap / "ramf.bin").read_bytes()
    level = Path(argv[3])
    rom_map, otile = level.with_suffix(".map").read_bytes(), level.with_suffix(".otile").read_bytes()
    rows = len(rom_map) // (COLS * 2)
    vats = vat_layout(level)

    def ram(a: int) -> int:
        return p0[a] if a < 0x4000 else pf[a - 0xF000]

    def cell(row: int, col: int) -> tuple[int, int]:
        """-> (tile, attributes)"""
        base = ATR_RAM0 + row * 80 if row < 48 else ATR_RAM1 + (row - 48) * 80
        b = ram(base + col // 2)
        atr = ram(ATR_LUT + ((b >> 4) if col % 2 == 0 else b & 15))
        pool, p = MP_POOL[row & 1], ram(MP_ROW + row)
        while p != 0xFF:
            if ram(pool + MPF_COL + p) == col:
                return ram(pool + MPF_TILEL + p) | ram(pool + MPF_TILEH + p) << 8, atr
            p = ram(pool + MPF_NEXT + p)
        if vats and (row, col) in vats["cells"]:
            v = vats["cells"][(row, col)]
            return vat_tile(vats, v, vat_look(pf, v[0], None)), atr
        return struct.unpack_from("<H", rom_map, 2 * (row * COLS + col))[0], atr

    bad = []
    for row in range(rows):
        for col in range(COLS):
            w = struct.unpack_from(">H", bench, AMIGA_MAP + 2 * (row * COLS + col))[0]
            want = (struct.unpack_from("<H", otile, 2 * (w >> 7))[0], w & 0x7F)
            got = cell(row, col)
            if got != want:
                bad.append((row, col, got, want))
    print(f"patches in use: {ram(MP_POOL[0] + MPF_COL + 0xFF)} (even rows) + {ram(MP_POOL[1] + MPF_COL + 0xFF)} "
          f"(odd rows); tiles lost {ram(MP_LOST)}, attribute values lost {ram(ATR_LOST)}")
    note = f" ({len(vats['cells'])} vat cells by the vat rule)" if vats else ""
    print(f"{rows * COLS} cells compared{note}: {len(bad)} differ")
    for row, col, (t, a), (wt, wa) in bad[:40]:
        print(f"  row {row} column {col}: tile {t} attributes {a:02X}h, the original's {wt} / {wa:02X}h")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
