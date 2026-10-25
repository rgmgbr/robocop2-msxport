#!/usr/bin/env python3
"""Compares the MSX port's map, as the game changed it, with the original's after the same game frames.

The original's map is in a chip RAM dump of the bench (tools/amigaemu.py game --dump, after the
same driven input as the port: --drive): 51 rows of 160 map words from $38000 (tile offset in
bits 7-15, attributes in bits 0-6). The port's is in an rc2_snap directory (tools/openmsx_rc2.tcl,
taken when the driven trace pauses: rc2_drive_trace with n rows from game frame 0 stops at the
start of game frame n - 1, the bench at the start of game frame --gframes, so --gframes n - 1):
ram0.bin (page-0 RAM) and ramf.bin (F000h-FFFFh). Each cell's tile is its map patch's (msx/msx.inc MP_ROW, the even rows'
pool MP_A, the odd rows' MP_B: column, next, tile low, tile high) or the ROM map's (LEVEL.map),
its attributes the packed map's code (ATR_RAM0 / ATR_RAM1, even column in the high nibble) in
atr_lut; the original's tile is LEVEL.otile's for its word's offset (msx/tiles.asm map_write).
Prints the patches in use and the lost counters, how many cells differ in tile or attributes
and the first 40 of them; exit code 1 if any.

usage: mapcmp.py BENCH_DUMP.bin SNAP_DIR LEVEL_PREFIX     (e.g. ... build/snap/end build/msx/level1)
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

COLS, ROWS = 160, 51
AMIGA_MAP = 0x38000
MP_ROW = 0x0A00
MP_POOL = (0x0B00, 0xF500)                  # even rows, odd rows
MPF_COL, MPF_NEXT, MPF_TILEL, MPF_TILEH = 0x000, 0x100, 0x200, 0x300
ATR_RAM0, ATR_RAM1, ATR_LUT = 0x108C, 0x0910, 0x1F8C
ATR_LOST, MP_LOST = 0x1082, 0x1084


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    bench = Path(argv[1]).read_bytes()
    snap = Path(argv[2])
    p0, pf = (snap / "ram0.bin").read_bytes(), (snap / "ramf.bin").read_bytes()
    level = Path(argv[3])
    rom_map, otile = level.with_suffix(".map").read_bytes(), level.with_suffix(".otile").read_bytes()

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
        return struct.unpack_from("<H", rom_map, 2 * (row * COLS + col))[0], atr

    bad = []
    for row in range(ROWS):
        for col in range(COLS):
            w = struct.unpack_from(">H", bench, AMIGA_MAP + 2 * (row * COLS + col))[0]
            want = (struct.unpack_from("<H", otile, 2 * (w >> 7))[0], w & 0x7F)
            got = cell(row, col)
            if got != want:
                bad.append((row, col, got, want))
    print(f"patches in use: {ram(MP_POOL[0] + MPF_COL + 0xFF)} (even rows) + {ram(MP_POOL[1] + MPF_COL + 0xFF)} "
          f"(odd rows); tiles lost {ram(MP_LOST)}, attribute values lost {ram(ATR_LOST)}")
    print(f"{ROWS * COLS} cells compared: {len(bad)} differ")
    for row, col, (t, a), (wt, wa) in bad[:40]:
        print(f"  row {row} column {col}: tile {t} attributes {a:02X}h, the original's {wt} / {wa:02X}h")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
