#!/usr/bin/env python3
"""sync3.py (tools/bstest/perf2; agent a_scroll's timing of 2026-11-01): the V9938 build's last phase: copy end -> the field's first command onto the built page (the
sync's start), its last one (the sync's end) -> the next build's first column tile (the flip on screen).
usage: sync3.py PREFIX FROM TO (PREFIX: an m3.tcl run in cmds or full mode: PREFIX_ticks.txt, PREFIX_cmds.txt;
docs/PERF2_PLAN.md item 7's flip timing, the V9938 machines)"""
import statistics as st
import sys
from pathlib import Path
P, f, t = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
tt = {}
for l in Path(P + "_ticks.txt").read_text().splitlines():
    p = l.split(); tt.setdefault(int(p[0]), float(p[1]))
t0, t1 = tt[f], tt[t]
ev = []
for l in Path(P + "_cmds.txt").read_text().splitlines():
    p = l.split(); tm = float(p[1])
    if not (t0 <= tm < t1): continue
    b = bytes.fromhex(p[3]); sx, sy, dx, dy, nx, ny = (b[i] | b[i+1] << 8 for i in range(0, 12, 2))
    op = b[14] >> 4; d = float(p[7])
    if op == 0xD and nx == 240 and (sy >> 8) < 2 and (dy >> 8) < 2:
        ev.append(("copy", tm, d, dy >> 8, ny // 16))
    elif op == 0xD and nx == 16 and ny == 16 and (sy >> 8) >= 2 and (dy >> 8) < 2:
        ev.append(("tile", tm, d, dy >> 8, dx))
    elif (sy >> 8) == 3 and (dy >> 8) < 2:
        ev.append(("fcopy", tm, d, dy >> 8, 0))      # a composed piece onto a play-field page
# builds: copy runs into a page
builds, cur = [], None
for e in ev:
    if e[0] == "copy":
        if cur is None or cur["page"] != e[3] or cur["slots"] >= 14:
            cur = {"page": e[3], "c0": e[1], "slots": 0}
            builds.append(cur)
        cur["slots"] += e[4]; cur["cend"] = e[1] + e[2]
rows = []
for i, b in enumerate(builds[:-1]):
    nb = builds[i + 1]
    # the next build's first column tile: a tile into nb's page at DX 0 or 240 after b's copy end
    nxt = [e for e in ev if e[0] == "tile" and e[3] == nb["page"] and e[4] in (0, 240) and b["cend"] <= e[1] < nb["c0"]]
    if not nxt or b["slots"] < 14:
        continue
    n0 = nxt[0][1]
    sync = [e for e in ev if e[0] == "fcopy" and e[3] == b["page"] and b["cend"] <= e[1] < n0]
    if sync:
        rows.append((sync[0][1] - b["cend"], sync[-1][1] + sync[-1][2] - sync[0][1], n0 - (sync[-1][1] + sync[-1][2]), n0 - b["cend"]))
    else:
        rows.append((None, 0.0, n0 - b["cend"], n0 - b["cend"]))
w = [r for r in rows if r[0] is not None]
ms = lambda xs: f"mean {1000*st.mean(xs):5.0f} med {1000*st.median(xs):5.0f}" if xs else "-"
print(f"{f}-{t}: {len(rows)} builds, {len(w)} with a field copy onto the built page before the flip")
print("  copy end -> sync's first piece onto the page:", ms([r[0] for r in w]))
print("  sync's first -> last piece end:", ms([r[1] for r in w]))
print("  sync end -> next build's first tile (flip decided, published, shown):", ms([r[2] for r in w]))
print("  builds without a sync piece: copy end -> next build:", ms([r[2] for r in rows if r[0] is None]))
print("  copy end -> next build (all):", ms([r[3] for r in rows]))
