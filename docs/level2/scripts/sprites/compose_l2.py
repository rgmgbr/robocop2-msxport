#!/usr/bin/env python3
"""Per-line sprite counts of level 2's characters as the MSX shows them: each part's converted
record (tools/msxsprites.py blob: every sprite's dy, A or B) placed where the original draws it (the
offsets REA read in each handler), summed per line, against the VDP's 8 a line beside RoboCop
(RC_CAP 5 a line) and the 32 in all (30 for the BOBs and RoboCop, the spark's two kept).
usage: compose_l2.py PREFIX"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

BANK = 0x2000
pre = Path(sys.argv[1])
data = pre.with_suffix(".bin").read_bytes()
js = json.loads(pre.with_suffix(".json").read_text())
n_rc = len(js["rc_index"])
ids = {(b["addr"], b["w"], b["h"]): i for i, b in enumerate(js["bobs"])}


def sprites(addr: int, w: int, h: int) -> list[tuple[int, int, bool]]:
    """(dy, dx, is_B) of each sprite of the frame's record."""
    k = n_rc + ids[(addr, w, h)]
    b, o = struct.unpack_from("<BH", data, 3 * k)
    at = b * BANK + o
    out = []
    for s in range(data[at]):
        dy, dx, pb, ab, p, c, p1, c1 = struct.unpack_from("<bbBBHHHH", data, at + 8 + 12 * s)
        out.append((dy, dx, p1 == 0xFFFF))
    return out


def lines(parts: list[tuple[int, int, int, int]], one_layer: bool = False) -> dict[int, int]:
    """parts: (addr, w, h, y offset); -> line -> sprites covering it."""
    cnt: dict[int, int] = {}
    for a, w, h, oy in parts:
        for dy, _dx, is_b in sprites(a, w, h):
            if one_layer and is_b:
                continue
            for y in range(oy + dy, oy + dy + 16):
                cnt[y] = cnt.get(y, 0) + 1
    return cnt


def total(parts, one_layer=False) -> int:
    return sum(1 for a, w, h, _ in parts for _dy, _dx, b in sprites(a, w, h) if not (one_layer and b))


L = lambda a: (a, 32, 23)  # noqa: E731  (type 1's legs)
T1 = [0x3E810 + o for o in (0, 0x1CC, 0x398, 0x564, 0x730, 0x8FC, 0xAC8, 0xC94)]
W1 = {0: (0x4BD06, 48, 28), 1: (0x4C396, 32, 28), 2: (0x4C5C6, 32, 28), 3: (0x4C7F6, 32, 28),
      4: (0x4C04E, 48, 28), 5: (0x4CA26, 32, 28), 6: (0x4CC56, 32, 28), 7: (0x4CE86, 32, 28)}
cases = {}
# type 1 ($C736): torso (x-2, y + 0/1), legs (x, y + 21), gun flash (x - 24, y + 8) when firing
for k, a in enumerate(T1):
    bob = (0, 0, 1, 1, 0, 0, 1, 1)[k] if False else (1 if k in (0, 1, 4, 5) else 0)
    cases[f"type 1 step {k}"] = [(0x404D0, 32, 21, bob), (a, 32, 23, 21)]
    cases[f"type 1 step {k} + gun flash"] = [(0x404D0, 32, 21, bob), (a, 32, 23, 21), (0x6CDA0, 32, 16, 8)]
# type 2 ($C868): play field; its white flash (8 frames in 16) = the body's sprite silhouette (one
# layer), its gun flash at (x - 20, y + 6)
for a in (0x3D280, 0x3D910):
    cases[f"type 2 {a:X} white flash (silhouette)"] = [(a, 48, 56, 0)]
cases["type 2 3D910 white flash + gun flash"] = [(0x3D910, 48, 56, 0), (0x6CDA0, 32, 16, 6)]
# type 14 ($CE0A): play field; the hit flash's silhouette
cases["type 14 hit flash (silhouette)"] = [(0x3DFA0, 48, 36, 0)]
# type 16 ($CD7A): walker1 legs (y + 25), body in the play field (y + bob + 2), gun flash (y + bob + 8)
for k in range(8):
    cases[f"type 16 step {k} (legs only as sprites)"] = [(*W1[k], 25)]
    cases[f"type 16 step {k} + gun flash"] = [(*W1[k], 25), (0x6CDA0, 32, 16, 8)]
    cases[f"type 16 step {k} + gun + hit flash"] = [(*W1[k], 25), (0x6CDA0, 32, 16, 8), (0x40818, 48, 24, 2)]
for k, a in enumerate((0x3C920, 0x3CB00, 0x3CCE0, 0x3CEC0, 0x3D0A0)):
    cases[f"type 6 frame {k}"] = [(a, 32, 24, 0)]
for a in (0x3BFC0, 0x3C060, 0x3C100, 0x3C1A0, 0x3C240, 0x3C2E0, 0x3C560, 0x3C6A0, 0x3C7E0):
    w = 16 if a < 0x3C2E0 or a == 0x3C240 else 32
    cases[f"type 5 {a:X}"] = [(a, w, 16, 0)]
for k in range(16):
    cases[f"type 49 dir {k}"] = [(0x41358 + 0xA0 * k, 16, 16, 0)]
cases["trolley as sprites (level 1's conversion, not used)"] = [(0x4B95A, 32, 47, 0)]
res = {}
print(f"{'composition':48} {'full max/line':>13} {'1-layer':>7} {'sprites':>7} {'lines>3':>7}")
for name, parts in cases.items():
    try:
        c = lines(parts)
        c1 = lines(parts, True)
    except KeyError as e:
        print(f"{name:48} missing frame {e}")
        continue
    over = sorted(y for y, n in c.items() if n > 3)
    res[name] = {"max": max(c.values()), "max1": max(c1.values()), "sprites": total(parts),
                 "sprites1": total(parts, True), "lines_over3": len(over)}
    print(f"{name:48} {max(c.values()):13} {max(c1.values()):7} {total(parts):7} {len(over):7}")
rc = js["max_line"]
print(f"RoboCop: most sprites a line {max(rc)} (compositions at 5: {sum(1 for m in rc if m == 5)} of {len(rc)}); "
      f"sprites per composition {min(js['sprites'])}-{max(js['sprites'])}")
Path(pre.parent / "compose_l2.json").write_text(json.dumps(res, indent=1))
