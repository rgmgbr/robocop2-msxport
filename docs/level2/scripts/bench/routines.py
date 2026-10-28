#!/usr/bin/env python3
"""Routines reached: executed blocks attributed to the REA procedure whose entry is the nearest at or
below (an approximation inside Ghidra's gaps), level 2's coverage against level 1's.
usage: routines.py PROCS.txt L1COV.json L2COV.json [...] > OUT"""
import bisect, json, sys
procs = []
for line in open(sys.argv[1]):
    a, n = line.split(None, 1)
    a = int(a, 16)
    if 0x8000 <= a < 0x12600:
        procs.append((a, n.strip()))
procs.sort()
entries = [a for a, _ in procs]
def owner(addr):
    i = bisect.bisect_right(entries, addr) - 1
    return procs[i] if i >= 0 else (0, "?")
def reached(paths):
    out = {}
    for p in paths:
        for blk in json.load(open(p))["blocks"]:
            a = blk[0]
            if not (0x8000 <= a < 0x12600):
                continue
            pa, pn = owner(a)
            e = out.setdefault(pa, [pn, 0, a == pa])
            e[1] += 1
            e[2] = e[2] or a == pa
    return out
l1 = reached([sys.argv[2]])
l2 = reached(sys.argv[3:])
new = sorted(set(l2) - set(l1))
print(f"procedures reached: level 2 {len(l2)}, level 1 {len(l1)}, level 2 only {len(new)}, level 1 only {len(set(l1) - set(l2))}")
for a in new:
    n, k, entered = l2[a]
    print(f"  {a:05x} {n:32s} blocks {k:3d}{'' if entered else '  (entry not executed: a gap inside or after it)'}")
print("level 1 only:", " ".join(f"{a:05x}:{l1[a][0]}" for a in sorted(set(l1) - set(l2))))
