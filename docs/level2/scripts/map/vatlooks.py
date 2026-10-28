#!/usr/bin/env python3
"""Vat 0's eight looks (level_tick_1's model, the columns' phases from $92DA as the image holds them,
every column advanced together): Amiga colours above, the MSX (palette C, graded) below.
usage: vatlooks.py REPO OUTDIR   (venv python -I -B)"""
import struct, sys
from pathlib import Path
import numpy as np
sys.dont_write_bytecode = True
REPO, OUT = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(REPO / "tools"))
from planar import write_png
from msxbright import BRIGHT
img = (REPO / "build/ram/level2_full.bin").read_bytes()
def tile(off):
    t = np.zeros((16, 16), np.uint8)
    for y in range(16):
        for p in range(4):
            v = (img[0x28000 + off + (y*4+p)*2] << 8) | img[0x28000 + off + (y*4+p)*2 + 1]
            for x in range(16):
                if v & (0x8000 >> x): t[y, x] |= 1 << p
    return t
T = [struct.unpack_from(">16H", img, a) for a in (0x927A, 0x929A, 0x92BA)]
ph = struct.unpack_from(">24H", img, 0x92DA)
cols, rows = 12, 9
l2 = [0] + list(struct.unpack_from(">15H", img, 0x10036))
am = np.array([[((c >> s) & 15) * 17 for s in (8, 4, 0)] for c in l2], np.uint8)
pd = (OUT / "level2_C.pal").read_bytes()
rem = list((OUT / "level2_C.remap").read_bytes())
msx = np.array([[BRIGHT[v] * 255 // 7 for v in ((pd[2*i] >> 4) & 7, pd[2*i+1] & 7, pd[2*i] & 7)] for i in range(16)], np.uint8)
lut = np.array(rem, np.uint8)
W = 8 * (cols * 16 + 8)
im = np.full((2 * rows * 16 + 8, W, 3), 255, np.uint8)
for s in range(8):
    for c in range(cols):
        d = (((ph[c] & 0xFF) + 2 * s) & 0xE) + (0x10 if ph[c + 1] >> 8 else 0)
        for r in range(rows):
            w = T[0][d // 2] if r == 0 else T[1 + (r - 1) % 2][d // 2]
            t = tile(w & ~0x7F)
            x0, y0 = s * (cols * 16 + 8) + c * 16, r * 16
            im[y0:y0+16, x0:x0+16] = am[t]
            im[rows*16 + 8 + y0:rows*16 + 8 + y0 + 16, x0:x0+16] = msx[lut[t]]
write_png(OUT / "vat0_looks.png", W, im.shape[0], [im[y].tobytes() for y in range(im.shape[0])])
print("wrote", OUT / "vat0_looks.png", W, im.shape[0])
