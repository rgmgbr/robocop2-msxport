"""eqtiles.py (tools/bstest/perf2; agent a_field's check of 2026-11-01, no arguments): the equivalence of
docs/PERF2_PLAN.md item 2's (field-2's) fb_tiles (ftl_ax: 8-bit arithmetic on the piece's corner) with the old one
(fb_rpiece's 16-bit clip, fb_dscr, SX/SY from the clipped cell's low nibble): for every piece position on an
axis (0..2559, x even as fb_clip makes them; y any) and extent (x: 2..64 even, y: 1..64), every cell the piece
spans: the same (offset in the scratch, first pixel in the cell, pixels)."""
def old(p0, ext, c):
    p1 = p0 + ext
    x0, x1 = 16 * c, 16 * c + 16
    if x0 < p0: x0 = p0                     # fb_rpiece
    if x1 > p1: x1 = p1
    return (x0 - p0) & 0xFF, x0 & 15, x1 - x0   # fb_dscr's D - base; SX's added nibble; NX
def new(p0, ext, c):
    a = ((16 * c) & 0xFF) - (p0 & 0xFF)
    a &= 0xFF                               # sub (hl): 8 bits
    b = a
    a = (a + 16) & 0xFF
    cc = ext
    if not (a >= cc): cc = a                # cp c / jr nc
    s = b - 256 if b & 0x80 else b
    if s >= 0:
        return b, 0, (cc - b) & 0xFF
    return 0, (-s) & 0xFF, cc
bad = n = 0
for axis, step, exts in (("x", 2, range(2, 65, 2)), ("y", 1, range(1, 65))):
    for p0 in range(0, 2560, step):
        for ext in exts:
            for c in range(p0 >> 4, ((p0 + ext - 1) >> 4) + 1):
                n += 1
                if old(p0, ext, c) != new(p0, ext, c):
                    bad += 1
                    if bad < 5: print(axis, p0, ext, c, old(p0, ext, c), new(p0, ext, c))
print(f"{n} cells checked, {bad} differ")
