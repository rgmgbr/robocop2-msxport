#!/usr/bin/env python3
"""whitechk.py (tools/bstest/perf2; agent a_flash's check of 2026-11-01) ROM FIELD_L3_INC L3_FC ATLAS_BANK
(the ROM, build/msx/sprites_l3_field.inc, the banks of the frame cache and of the atlas as the build's log
names them, e.g. 147 145): every white copy against its normal frame: the same
transparent nibbles (0) and every opaque nibble 9. Normal frames from the frame cache (cache frames) or
from the atlas (field_upload's banks: per bank its frames [atlas line, x/2, bytes a line, lines, mirrored,
offset])."""
import re, sys
rom = open(sys.argv[1], 'rb').read()
inc = open(sys.argv[2]).read()
FC = int(sys.argv[3], 0)
ATL = int(sys.argv[4], 0)
tab = []
for m in re.finditer(r'^\s+db (\d+), (\d+), (\d+), (\d+), (-?\d+), (-?\d+)\s+;', inc.split('field_look_l3')[0], re.M):
    tab.append(tuple(int(m.group(i)) for i in range(1, 5)))
def hb(a): return rom[FC * 8192 + a - 0x8000]
def ent(c):
    a = 0x8084 + 4 * c
    return hb(a), hb(a + 1) | hb(a + 2) << 8, hb(a + 3)
def cache_px(c, w, h):
    bank, addr, place = ent(c)
    off = (FC + bank) * 8192 + addr - 0x8000
    bpl = w // 2
    return [rom[off + y * bpl: off + (y + 1) * bpl] for y in range(h)]
# the atlas: page 3 lines from FIELD_Y0 (0 in level 3); build a 256 x 112 nibble image
atl = {}
b = ATL
while True:
    base = b * 8192
    n = rom[base] & 0x7F
    for i in range(n):
        e = rom[base + 1 + 7 * i: base + 8 + 7 * i]
        line, x2, bpl, lines, mir, off = e[0], e[1], e[2], e[3], e[4], e[5] | e[6] << 8
        p = base + off
        for y in range(lines):
            row = rom[p + y * bpl: p + (y + 1) * bpl]
            if mir:
                row = bytes(((v >> 4) | (v << 4)) & 0xFF for v in reversed(row))
            for k, v in enumerate(row):
                atl[(line + y, x2 + k)] = v
    if not rom[base] & 0x80:
        break
    b += 1
def atlas_px(f):
    x, y, w, h = tab[f]
    return [bytes(atl.get((y + r, x // 2 + k), 0) for k in range(w // 2)) for r in range(h)]
bad = 0
n = 0
for f in range(66):
    nc, wc = hb(0x8000 + 2 * f), hb(0x8001 + 2 * f)
    if wc == 0xFF:
        continue
    w, h = tab[f][2], tab[f][3]
    norm = cache_px(nc, w, h) if nc != 0xFF else atlas_px(f)
    white = cache_px(wc, w, h)
    n += 1
    for y in range(h):
        for k in range(w // 2):
            a, bb = norm[y][k], white[y][k]
            for s in (4, 0):
                na, nb = (a >> s) & 15, (bb >> s) & 15
                if (na == 0) != (nb == 0) or (nb not in (0, 9)):
                    bad += 1
print(f'{n} white copies checked against their normal frames: {bad} nibbles differ in mask or are not 0/9')
