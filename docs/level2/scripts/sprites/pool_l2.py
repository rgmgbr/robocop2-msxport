#!/usr/bin/env python3
"""Level 2's sprite data against level 1's (tools/msxsprites.py blobs): what a global pool adds.

For each blob: the pattern and colour-row pools, RoboCop's records (byte for byte, pointing at the
same pattern / row bytes), and per BOB frame its record. A level-2 frame whose record (resolved to
pattern and row bytes) equals a level-1 frame's needs only a level-2 index entry; the others need
their record and the patterns / rows level 1's pools lack.
usage: pool_l2.py L1_PREFIX L2_PREFIX"""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

BANK = 0x2000


def load(pre: Path):
    data = pre.with_suffix(".bin").read_bytes()
    inc = pre.with_suffix(".inc").read_text()
    js = json.loads(pre.with_suffix(".json").read_text())
    eq = {m.group(1): int(m.group(2), 0) for m in re.finditer(r"^(\w+): equ (\S+)", inc, re.M)}
    p0, c0 = eq["SPR_PAT_BANK"] * BANK, eq["SPR_COL_BANK"] * BANK
    pat = lambda i: data[p0 + 32 * i:p0 + 32 * i + 32] if i != 0xFFFF else b""  # noqa: E731
    col = lambda i: data[c0 + 16 * i:c0 + 16 * i + 16] if i != 0xFFFF else b""  # noqa: E731
    n_rc = len(js["rc_index"])
    n = n_rc + len(js["bobs"])
    recs = []
    for k in range(n):
        b, o = struct.unpack_from("<BH", data, 3 * k)
        w = b * BANK + o
        nspr, nb = data[w], data[w + 2]
        items = [bytes(data[w:w + 8])]
        ps, cs = set(), set()
        for s in range(nspr):
            y, x, pb, ab, p, c, p1, c1 = struct.unpack_from("<bbBBHHHH", data, w + 8 + 12 * s)
            items.append((y, x, pb, ab, pat(p), col(c), pat(p1), col(c1)))
            ps |= {pat(p), pat(p1)} - {b""}
            cs |= {col(c), col(c1)} - {b""}
        items.append(bytes(data[w + 8 + 12 * nspr:w + 8 + 12 * nspr + 4 * nb]))
        recs.append({"key": tuple(items), "size": 8 + 12 * nspr + 4 * nb, "where": w, "pats": ps, "cols": cs})
    pats = {pat(i) for i in range(js["patterns"])}
    cols = {col(i) for i in range(js["colour_rows"])}
    return js, recs, n_rc, pats, cols


j1, r1, n1, p1, c1 = load(Path(sys.argv[1]))
j2, r2, n2, p2, c2 = load(Path(sys.argv[2]))
assert n1 == n2
rc_same = sum(1 for k in range(n1) if r1[k]["key"] == r2[k]["key"])
print(f"RoboCop: {rc_same} of {n1} index entries identical in content")
l1keys = {r["key"] for r in r1}
new_frames, shared_frames = [], []
seen_where = set()
new_rec_bytes = 0
for i, b in enumerate(j2["bobs"]):
    r = r2[n2 + i]
    if r["key"] in l1keys:
        shared_frames.append(b)
    else:
        new_frames.append((b, r))
        if r["where"] not in seen_where:
            seen_where.add(r["where"])
            new_rec_bytes += r["size"]
newp = p2 - p1
newc = c2 - c1
print(f"level-2 BOB frames: {len(j2['bobs'])} ({len(shared_frames)} identical to a level-1 record, {len(new_frames)} new)")
print(f"patterns: level 2 uses {len(p2)}, {len(newp)} not in level 1's pool; colour rows: {len(c2)}, {len(newc)} new")
idx = 3 * len(j2["bobs"])
tot = 32 * len(newp) + 16 * len(newc) + new_rec_bytes + idx
print(f"new bytes: patterns {32 * len(newp)}, colour rows {16 * len(newc)}, records {new_rec_bytes}, "
      f"level-2 BOB index {idx}; total {tot} B = {tot / 1024:.1f} KiB")
by = {}
for b, r in new_frames:
    key = b["proc"]
    e = by.setdefault(key, [0, 0, set(), set(), 0, []])
    e[0] += 1
    e[1] += b["sprites"]
    e[2] |= r["pats"] & newp
    e[3] |= r["cols"] & newc
    e[4] = max(e[4], b["max_line"])
    e[5].append(f"{b['addr']:X}{'m' if b.get('mirror') else ''}")
print("new frames by routine: frames, sprites, new patterns, new rows, most a line")
for k, (n, s, ps, cs, ml, a) in sorted(by.items()):
    print(f"  {k:16} {n:3} {s:4} {len(ps):4} {len(cs):4} {ml:2}  {' '.join(a)}")
