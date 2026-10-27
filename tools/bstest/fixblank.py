#!/usr/bin/env python3
"""The HUD's blank between front_stats and Brainstorm's intro, from fixchk.tcl hzb_setup's events.

usage: fixblank.py DIR/TAG_blank.txt

Events: S = a HUD split (isr_split), C E = cpu_set's display off (cs_go, E = its target CPU),
D = display_on's entry, B = front_bonus' entry. Prints the last split before the C that precedes
B, the first split after B, the time between them and the frames without a HUD split (a HUD shown).
On the FS-A1GT on 2026-10-27: 6 frames (docs/BRAINSTORM.md section 7, default 2).
"""
from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    ev = []
    with open(sys.argv[1]) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            t, *what = line.split()
            ev.append((float(t), " ".join(what)))
    ib = next(i for i, (_, w) in enumerate(ev) if w == "B")
    ic = max(i for i, (_, w) in enumerate(ev[:ib]) if w.startswith("C"))
    s_before = max(i for i, (_, w) in enumerate(ev[:ic]) if w == "S")
    s_after = next(i for i in range(ib, len(ev)) if ev[i][1] == "S")
    d = [ev[i] for i in range(ic, s_after) if ev[i][1] == "D"]
    splits = [t for t, w in ev if w == "S"]
    gaps = sorted(b - a for a, b in zip(splits, splits[1:]) if b - a < 0.03)
    period = gaps[len(gaps) // 2] if gaps else 1 / 59.92
    t0, t1 = ev[s_before][0], ev[s_after][0]
    frames = round((t1 - t0) / period) - 1
    print(f"frame period (median split gap) {period * 1000:.3f} ms")
    print(f"last HUD split before the switch {t0:.6f} s; cpu_set ({ev[ic][1]}) {ev[ic][0]:.6f} s "
          f"(+{(ev[ic][0] - t0) * 1000:.2f} ms)")
    for t, w in d:
        print(f"display_on {t:.6f} s (+{(t - t0) * 1000:.2f} ms)")
    print(f"front_bonus {ev[ib][0]:.6f} s; first HUD split after it {t1:.6f} s")
    print(f"between the two splits: {(t1 - t0) * 1000:.2f} ms = {(t1 - t0) / period:.2f} frame periods: "
          f"{frames} frame(s) without the HUD")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
