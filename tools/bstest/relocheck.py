#!/usr/bin/env python3
"""relocheck.py OLD.rom NEW.rom OLD.labels NEW.labels BANK...: every differing byte of the given banks
lies in a little-endian word whose old value is a label that moved and whose new value is that label's
new address (a relocated operand); prints any byte that is not. Exit 0 when every differing byte is
one (romdiff.py lists the banks that differ; docs/HARNESS.md)."""
from __future__ import annotations

import re
import sys


def load(p: str) -> dict[str, int]:
    d = {}
    with open(p) as f:
        for line in f:
            m = re.match(r"^(\w+):\s+equ \$([0-9a-fA-F]+)", line)
            if m:
                d[m[1]] = int(m[2], 16)
    return d


def main(argv: list[str]) -> int:
    if len(argv) < 5:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[0], "rb") as f:
        a = f.read()
    with open(argv[1], "rb") as f:
        b = f.read()
    la, lb = load(argv[2]), load(argv[3])
    moved = {la[k]: lb[k] for k in la if k in lb and la[k] != lb[k]}
    bad = 0
    for bank in map(int, argv[4:]):
        base = bank * 8192
        i = 0
        n = 0
        while i < 8192:
            if a[base + i] != b[base + i]:
                ok = False
                for j in (i - 1, i):
                    if 0 <= j < 8191:
                        wo = a[base + j] | a[base + j + 1] << 8
                        wn = b[base + j] | b[base + j + 1] << 8
                        if moved.get(wo) == wn:
                            ok = True
                            i = j + 2
                            n += 1
                            break
                if not ok:
                    print(f"bank {bank} offset {i:04X}: {a[base + i]:02X} -> {b[base + i]:02X} not a relocated label word")
                    bad += 1
                    i += 1
            else:
                i += 1
        print(f"bank {bank}: {n} relocated label words")
    print("relocheck:", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
