#!/usr/bin/env python3
"""Compares two bench traces (JSON lines, --trace-ram) row by row: every differing byte, by block."""
import json, sys
a, b = open(sys.argv[1]).read().split("\n"), open(sys.argv[2]).read().split("\n")
a = [json.loads(x) for x in a if x.strip()]; b = [json.loads(x) for x in b if x.strip()]
print(f"rows {len(a)} / {len(b)}")
diffs = {}
first = None
for i, (ra, rb) in enumerate(zip(a, b)):
    for key, base in (("ram", 0xB00), ("glob", 0x8000)):
        xa, xb = bytes.fromhex(ra[key]), bytes.fromhex(rb[key])
        for k, (u, v) in enumerate(zip(xa, xb)):
            if u != v:
                d = diffs.setdefault(base + k, [0, i, u, v]); d[0] += 1
                first = i if first is None else first
    for lo in ra.get("code", {}):
        xa, xb = bytes.fromhex(ra["code"][lo]), bytes.fromhex(rb["code"].get(lo, ""))
        for k, (u, v) in enumerate(zip(xa, xb)):
            if u != v:
                d = diffs.setdefault(int(lo, 16) + k, [0, i, u, v]); d[0] += 1
                first = i if first is None else first
    for k in ra:
        if k not in ("ram", "glob", "code") and ra[k] != rb.get(k):
            d = diffs.setdefault(k, [0, i, ra[k], rb.get(k)]); d[0] += 1
print(f"differing addresses: {len(diffs)}; first differing row: {first}")
for k, (n, i, u, v) in sorted(diffs.items(), key=lambda kv: (str(type(kv[0])), kv[0])):
    print(f"  {k if isinstance(k, str) else f'${k:05x}'}: {n} rows, first row {i}: {u} / {v}")
