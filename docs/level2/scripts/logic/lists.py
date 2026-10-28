#!/usr/bin/env python3
"""Decodes level 2's lists from the level-2 RAM image (formats from REA listings of $C3E4, $9C06,
$9150, $8B32): spawn list $97B0, object list $A828, marker table $C5EC, hazards $95B2, specials
$8FE0, type descriptors ($BEA6 + 16 t), hit-point tables $C716. Writes tables/*.txt (stdout: summary)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from img import RAM, b, hx, l, sw, w  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tables")
os.makedirs(OUT, exist_ok=True)


def save(name, lines):
    with open(os.path.join(OUT, name), "w") as f:
        f.write("\n".join(lines) + "\n")


# level header (level_init reads $8664 + 40 * level)
hdr = []
for lv in range(3):
    a = 0x8664 + 40 * lv
    f = [l(a), l(a + 4), l(a + 8), l(a + 12), w(a + 16), w(a + 18), w(a + 20), w(a + 22), l(a + 24),
         w(a + 28), w(a + 30), w(a + 32), w(a + 34), l(a + 36)]
    hdr.append(f"level {lv + 1} @${a:05X}: objlist ${f[0]:05X} hazards ${f[1]:05X} specials ${f[2]:05X} "
               f"spawn ${f[3]:05X} +16 ${f[4]:04X} +18 ${f[5]:04X} reloc ({f[6]}, {f[7]}) markers ${f[8]:05X} "
               f"camymax ${f[9]:04X} timer ${f[10]:04X} delay ${f[11]:04X} mkmask ${f[12]:04X} pal ${f[13]:05X}")
save("level_headers.txt", hdr)
print("\n".join(hdr))

# spawn list: 14-byte entries, end = negative x word
sp = ["# level 2 spawn list $97B0 (14-byte entries: x.w +0, y.w +2, type.b +4, +5, +6, flags.b +7 "
      "(bit 7 at the screen edge, bit 6 once), reload.w +8, count.w +10, spawned.b +12 (bit 7), +13)",
      "# k  addr    x     y   type b5 b6 flags reload count b12 b13  raw"]
a, k = 0x97B0, 0
types = {}
while sw(a) >= 0:
    t = b(a + 4)
    types.setdefault(t, []).append(k)
    sp.append(f"{k:2d} ${a:05X} {w(a):5d} {w(a + 2):5d} {t:4d} {b(a + 5):02X} {b(a + 6):02X}  {b(a + 7):02X}  "
              f"{w(a + 8):5d} {sw(a + 10):5d}  {b(a + 12):02X}  {b(a + 13):02X}  {hx(a, 14)}")
    a += 14
    k += 1
sp.append(f"# end marker at ${a:05X}: {hx(a, 2)}; {k} entries")
save("spawn_l2.txt", sp)
print(f"spawn list: {k} entries, end ${a:05X}; types " + ", ".join(f"{t}:{len(v)}" for t, v in sorted(types.items())))

# marker table: 6-byte entries, +0 bands (bit 15 = end), +2 type, +4 y offset
mk = ["# level 2 marker table $C5EC (6-byte entries: bands.w +0 (1 high, 2 middle, 4 low; negative = end, "
      "back to the start), type.w +2, y offset.w +4); $C598 holds the walk pointer (level 1: $C59C)"]
a = 0xC5EC
mtypes = []
while True:
    if sw(a) < 0:
        mk.append(f"${a:05X} end {hx(a, 2)}")
        break
    mk.append(f"${a:05X} bands {w(a):04X} type {w(a + 2):3d} yoff {sw(a + 4):5d}  {hx(a, 6)}")
    mtypes.append(w(a + 2))
    a += 6
save("markers_l2.txt", mk)
print("markers:", mtypes)

# hazards: 8-byte records x0, y, x1, n; end negative
hz = ["# level 2 hazard list $95B2 (8-byte records: x0.w, y.w, x1.w, rows.w; negative x0 = end); "
      "level_tick_1 $91BC runs for each record in the window"]
a = 0x95B2
while sw(a) >= 0:
    hz.append(f"${a:05X} x0 {w(a):5d} y {w(a + 2):4d} x1 {w(a + 4):5d} rows {w(a + 6):3d}  "
              f"cols {(w(a + 4) - w(a)) // 16 + 1}  {hx(a, 8)}")
    a += 8
hz.append(f"${a:05X} end {hx(a, 2)}")
save("hazards_l2.txt", hz)
print("\n".join(hz))

# specials: list of longs at $8FE0 (negative = end), records: handler.w, x.w, y.l, idx.w, path words
spc = ["# level 2 special objects: list $8FE0 (record pointers, negative = end); record: handler offset.w "
       "(0 lift $8DE6, 4 $8F02, 8 vehicle $8B9E), x.w +2, y.l +4, path index.w +8, path words from +10 "
       "(negative = end)"]
a = 0x8FE0
while not (l(a) & 0x80000000):
    r = l(a)
    path = []
    p = r + 10
    while sw(p) >= 0 and len(path) < 40:
        path.append(w(p))
        p += 2
    spc.append(f"${r:05X}: handler {w(r)} x {w(r + 2)} y {w(r + 4)}.{w(r + 6):04X} idx {w(r + 8)} path {path} "
               f"(end {hx(p, 2)} at ${p:05X})")
    a += 4
spc.append(f"list end at ${a:05X}: {hx(a, 4)}")
save("specials_l2.txt", spc)
print("\n".join(spc))

# type descriptors P(t) = $BEA6 + 16 t
ds = ["# type descriptors P(t) = $BEA6 + 16 t: +0, +2, width +4, height +6, score (BCD) +8, handler offset +10 "
      "(from P+10), death offset +12 (from P+12), hit-point class +14 (index into the $8060 table)",
      "# t   P       +0   +2   w    h   score  handler death  class"]
for t in range(1, 53):
    p = 0xBEA6 + 16 * t
    ds.append(f"{t:2d} ${p:05X} {w(p):04X} {w(p + 2):04X} {sw(p + 4):4d} {sw(p + 6):4d}  {w(p + 8):04X}  "
              f"${(p + 10 + sw(p + 10)) & 0xFFFFF:05X} ${(p + 12 + sw(p + 12)) & 0xFFFFF:05X}  {w(p + 14)}")
save("descriptors.txt", ds)

hp = ["# hit points by class 0-7 ($8060 points at one of these; REA: $C512, $C706 read it)"]
for i, name in enumerate(("SHARP", "GOOD", "FAIR", "POOR")):
    a = 0xC716 + 8 * i
    hp.append(f"${a:05X} {name:5s} " + " ".join(f"{b(a + j):02X}" for j in range(8)))
save("hp_tables.txt", hp)
print("\n".join(hp))
