#!/usr/bin/env python3
"""Decodes the map objects of level 2 (object list $A828, 12-byte entries; per-type tables at $9D0C:
looks long +0, flags word +$88, activator offset word +$8A (from $9EC4), width-1 / height-1 words
+$110 / +$112, all with a 4-byte stride; REA listing of activate_objects $9C06 / map_object_look
$9C76). Writes tables/objlist_l2.txt and tables/objtypes.txt."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from img import hx, l, sw, w  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tables")
ACT = {0: "(none: map_object_look $9C76)", 0x14: "act_conveyor_left $A038"}
NAMES = {0x9EA4: "act_explode_look4", 0x9EE8: "act_0c (level 2)", 0x9F74: "act_20", 0x9F84: "act_floor_switch",
         0x9FC4: "obj_relocate", 0xA038: "act_conveyor_left", 0xA03E: "act_conveyor_right", 0xA0D4: "act_barrier",
         0x9EC4: "(offset 0: map_object_look)"}


def looks(tab, maxn=12):
    out = []
    for i in range(maxn):
        p = l(tab + 4 * i)
        out.append(p)
        if p & 0x80000000:
            break
    return out


# the activators: a table of BRA instructions at $9EC4 + offset (jmp (0,A5,D7) at $9C72)
BR = {}
for off in range(0, 36, 4):
    op = w(0x9EC4 + off)
    if op == 0x6000:
        BR[off] = (0x9EC4 + off + 2 + sw(0x9EC4 + off + 2)) & 0xFFFFF
    elif op >> 8 == 0x60:
        d = op & 0xFF
        BR[off] = 0x9EC4 + off + 2 + (d - 256 if d > 127 else d)
NAMES[0x9C76] = "map_object_look"
types = []
for t in range(34):
    a = 0x9D0C + 4 * t
    lt, fl, act, wm1, hm1 = l(a), w(a + 0x88), w(a + 0x8A), sw(a + 0x110), sw(a + 0x112)
    types.append((t, lt, fl, act, wm1, hm1))
lines = ["# map object types: t (= entry +0 / 4), looks table, flags (+$88: byte to the slot +$40), activator "
         "($9EC4 + offset), width-1, height-1 (cells); looks: map-word blocks, -1 = gone"]
for t, lt, fl, act, wm1, hm1 in types:
    tgt = BR.get(act, 0x9EC4 + act)
    lk = looks(lt) if 0x8000 <= lt < 0x80000 else []
    lines.append(f"t {t:2d} (+0 = {4 * t:3d}) looks ${lt:05X} flags {fl:04X} act {act:3d} -> ${tgt:05X} "
                 f"{NAMES.get(tgt, '?')} size {wm1 + 1}x{hm1 + 1}  looks: " + " ".join(
                     ('-1' if p & 0x80000000 else f'${p:05X}') for p in lk))
open(os.path.join(OUT, "objtypes.txt"), "w").write("\n".join(lines) + "\n")

ol = ["# level 2 object list $A828: 12-byte entries: type*4 +0, look index +2 (negative = gone), hits/flags +4 "
      "(high byte bit 7: animating), pickup +6, x +8, y +10; end: negative word",
      "#  k  addr    t  look  +4    pick   x     y    col row  activator"]
a, k, used = 0xA828, 0, {}
while sw(a) >= 0:
    t = w(a) // 4
    used.setdefault(t, 0)
    used[t] += 1
    tt = types[t]
    ol.append(f"{k:3d} ${a:05X} {t:2d} {sw(a + 2):5d} {w(a + 4):04X} {w(a + 6):5d} {w(a + 8):5d} {w(a + 10):5d}  "
              f"{w(a + 8) // 16 - 8:3d} {w(a + 10) // 16:3d}  {NAMES.get(BR.get(tt[3], 0), '?')}")
    a += 12
    k += 1
ol.append(f"# end at ${a:05X}: {hx(a, 2)}; {k} entries; types used: " +
          ", ".join(f"{t}x{n}" for t, n in sorted(used.items())))
open(os.path.join(OUT, "objlist_l2.txt"), "w").write("\n".join(ol) + "\n")
print("\n".join(ol[-1:]))
for t in sorted(used):
    print(lines[t + 1])
