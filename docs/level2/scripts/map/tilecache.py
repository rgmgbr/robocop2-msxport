#!/usr/bin/env python3
"""Tile-cache pressure in level 2 (and level 1 for scale): the most distinct tiles (after the
palette remap) in the windows the scroll engines keep drawn, with the vats' and the map objects'
run-time tiles added where their cells meet the window.

Windows (cells): V9958 ring 19 x 14 (msx/scroll9958.asm: columns cx-1..cx+17, rows cy-1..cy+12);
V9938 two pages 17 x 14 (16 columns a page, the back page one column over); a 40 x 24 window
(msx/tiles.asm's own margin figure). TC_SLOTS = 256 (msx/tiles.asm).
usage: tilecache.py REPO REMAP_FILE   (venv python -I -B)
"""
import struct
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
REPO = Path(sys.argv[1])
remap = list(Path(sys.argv[2]).read_bytes())
sys.path.insert(0, str(REPO / "tools"))
import mapcells  # noqa: E402
from amitab import parse  # noqa: E402

COLS = 160


def tiles_of(datal, lut):
    out = {}
    for off in range(0, 0x10000, 0x80):
        t = np.zeros((16, 16), np.uint8)
        for y in range(16):
            for p in range(4):
                v = (datal[off + (y * 4 + p) * 2] << 8) | datal[off + (y * 4 + p) * 2 + 1]
                for x in range(16):
                    if v & (0x8000 >> x):
                        t[y, x] |= 1 << p
        out[off] = lut[t].tobytes()
    return out


def run(level, datal_name, rows, img_name, objl, vats_addr):
    datal = (REPO / "build/extracted/files" / datal_name).read_bytes()
    img = (REPO / "build/ram" / img_name).read_bytes()
    lut = np.array(remap, np.uint8)
    gfx = tiles_of(datal, lut)
    words = [struct.unpack_from(">H", datal, 0x10000 + 2 * i)[0] for i in range(rows * COLS)]
    cell = [[gfx[words[r * COLS + c] & ~0x7F] for c in range(COLS)] for r in range(rows)]
    extra = {}          # (row, col) -> set of graphics the writers can put there
    tabs = {r["label"]: r for r in parse(REPO / "analysis" / "amiga_tables.tsv")}
    tabs[f"objl_{level}"] = {"label": f"objl_{level}", "addr": objl[0], "count": objl[1], "kind": "x", "bank": level, "comment": ""}
    cells, words_of = mapcells.writers(img, tabs, level, COLS, rows)
    for name, cs in cells.items():
        g = {gfx[w & ~0x7F] for w in words_of[name]}
        for rc in cs:
            extra.setdefault(rc, set()).update(g)
    if vats_addr:
        vat_g = [gfx[w & ~0x7F] for w in struct.unpack_from(">48H", img, 0x927A)]
        a = vats_addr
        while struct.unpack_from(">h", img, a)[0] >= 0:
            xl, y, xr, nr = struct.unpack_from(">4H", img, a)
            row, col = mapcells.map_cell(xl, y, rows)
            for c in range((xr - xl) // 16 + 1):
                for r in range(nr + 2):
                    extra.setdefault((row + r, col + c), set()).update(
                        set(vat_g[0:16]) if r == 0 else set(vat_g[16:48]))
            a += 8
    print(f"{level}: {len({g for row in cell for g in row})} distinct tiles in the map")
    for wname, ww, wh in (("V9958 19x14", 19, 14), ("V9938 17x14", 17, 14), ("40x24", 40, 24)):
        best = (0, 0, 0, 0)
        best_static = (0, 0, 0)
        for r0 in range(0, max(1, rows - wh + 1)):
            for c0 in range(0, COLS - ww + 1):
                s = set()
                for r in range(r0, min(rows, r0 + wh)):
                    s.update(cell[r][c0:c0 + ww])
                st = len(s)
                for r in range(r0, min(rows, r0 + wh)):
                    for c in range(c0, c0 + ww):
                        if (r, c) in extra:
                            s |= extra[(r, c)]
                if len(s) > best[0]:
                    best = (len(s), c0, r0, st)
                if st > best_static[0]:
                    best_static = (st, c0, r0)
        print(f"  {wname}: at most {best_static[0]} distinct tiles from the map alone (cell {best_static[1]},{best_static[2]});"
              f" with the writers' tiles {best[0]} (cell {best[1]},{best[2]}; {best[3]} from the map there)")


def main():
    run("l2", "DATAL2_18.bin", 50, "level2_full.bin", (0xA828, 530), 0x95B2)
    run("l1", "DATAL1_10.bin", 51, "level1_full.bin", (0xA562, 710), None)


if __name__ == "__main__":
    main()
