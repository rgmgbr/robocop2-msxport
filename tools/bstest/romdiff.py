#!/usr/bin/env python3
"""romdiff.py A.rom B.rom: the 8 KiB banks that differ, with the differing byte count and range
(relocheck.py then checks that a code bank's differences are relocated label words)."""
from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[0], "rb") as f:
        a = f.read()
    with open(argv[1], "rb") as f:
        b = f.read()
    print(f"sizes {len(a)} {len(b)}")
    for k in range(max(len(a), len(b)) // 8192):
        x, y = a[k * 8192:(k + 1) * 8192], b[k * 8192:(k + 1) * 8192]
        if x != y:
            d = [i for i in range(8192) if i >= len(x) or i >= len(y) or x[i] != y[i]]
            print(f"bank {k}: {len(d)} bytes differ, offsets {d[0]:04X}-{d[-1]:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
