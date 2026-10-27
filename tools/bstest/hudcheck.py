#!/usr/bin/env python3
"""4.2 check 4's HUD part: the HUD (page 3 lines 208-252, VRAM 1E800h) and its colours (SR_PAL) in
step 7's snapshots against a build without the display (step 6) at the same passes of the same drive,
and what changes in the HUD across the stage (its pixel boxes: the timer, the score and the message
are the only ones expected).

usage: hudcheck.py STEP7_DIR STEP6_DIR    (hz7_arm snapshot folders, pNNNN.bin)

For a later change: the two folders hold the same drive's snapshots at the same passes from the
build under test and from a reference build (docs/HARNESS.md). Exit 0 when every pair is equal.
"""
from __future__ import annotations

import sys
from pathlib import Path

HUD, HUD_LEN = 0x1E800, 45 * 128
SR_PAL = 0x20000 + 0xEA22 - 0xC000


def boxes(a: bytes, b: bytes) -> list[tuple]:
    """Connected boxes (x0, y0, x1, y1 in pixels) of the bytes that differ, by 8 x 8 cells."""
    cells = sorted({(((i % 128) * 2) // 8, (i // 128) // 8) for i in range(len(a)) if a[i] != b[i]})
    out = []
    for cx, cy in cells:
        for k, (x0, y0, x1, y1) in enumerate(out):
            if x0 - 1 <= cx <= x1 + 1 and y0 - 1 <= cy <= y1 + 1:
                out[k] = (min(x0, cx), min(y0, cy), max(x1, cx), max(y1, cy))
                break
        else:
            out.append((cx, cy, cx, cy))
    return [(8 * x0, 8 * y0, 8 * x1 + 7, 8 * y1 + 7) for x0, y0, x1, y1 in out]


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    d7, d6 = Path(sys.argv[1]), Path(sys.argv[2])
    bad = 0
    snaps = sorted(d7.glob("p*.bin"))
    if not snaps:
        print(f"no snapshots p*.bin in {d7}")
        return 1
    for p in snaps:
        q = d6 / p.name
        if not q.exists():
            continue
        a, b = p.read_bytes(), q.read_bytes()
        same = a[HUD:HUD + HUD_LEN] == b[HUD:HUD + HUD_LEN] and a[SR_PAL:SR_PAL + 30] == b[SR_PAL:SR_PAL + 30]
        print(f"{p.name}: HUD and its colours {'equal to' if same else 'DIFFERENT from'} the build without the display")
        bad += not same
    first, last = snaps[0].read_bytes(), snaps[-1].read_bytes()
    print(f"HUD changes from {snaps[0].name} to {snaps[-1].name} (x0, y0, x1, y1 in HUD pixels):",
          boxes(first[HUD:HUD + HUD_LEN], last[HUD:HUD + HUD_LEN]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
