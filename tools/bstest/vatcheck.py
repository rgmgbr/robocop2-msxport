#!/usr/bin/env python3
"""Level 2's vats on the screen (docs/LEVEL2.md 4.2 check 8; its step 14): the records of
tools/bstest/vatlog.tcl (DIR/vat_<m>.txt, DIR/guard_<m>.txt) summarised per machine:
- the columns drawn and their rate (a second of emulated time), per vat the columns seen, their draws a
  column a second over the record and how often a column changes look while it is being redrawn (its
  draws' median interval under 4 s);
- each column's time from its first part's start to its last part's end (lines of 63.5 us), the beam
  line it started at, and, for those that ended in the next picture's display, the margin from the
  beam to the column's first line on the screen (R#23 then): negative is a column the beam drew
  while it changed;
- the time the CPU spent in vats.asm (vat_run: the window's column with its parts' waits; vat_prep:
  the preparation, the V9938's mirror) as a share of the emulated time; the V9938's mirrors (the
  VBLANKs from a column to its copy on the other page: what a flip may wait for);
- the guard's counts, and its tears and play-area commands that are a vat column's (the destination
  of one of its parts within 20 game frames of that column's on the G lines' clock) or not.
Exit 1 when a vat column was drawn into by the beam (a negative margin or a guard tear of a vat
column). usage: vatcheck.py DIR [MACHINE ...] (default: every vat_<m>.txt in DIR)
"""
from __future__ import annotations

import re
import statistics as st
import sys
from pathlib import Path

VATS = [(45, 12, 40, 9), (73, 10, 40, 9), (90, 10, 40, 9), (118, 16, 43, 6),
        (111, 22, 18, 4), (71, 20, 18, 4), (30, 13, 18, 4)]   # first column, columns, first row, rows
FIRST = [sum(v[1] for v in VATS[:i]) for i in range(len(VATS))]
VIEW = 162


def vat_of(idx: int) -> int:
    return max(i for i in range(len(VATS)) if FIRST[i] <= idx)


def main(argv: list[str]) -> int:
    d = Path(argv[1])
    ms = argv[2:] or sorted(p.stem[4:] for p in d.glob("vat_*.txt"))
    bad = 0
    for m in ms:
        f = d / f"vat_{m}.txt"
        if not f.exists():
            print(f"{m}: no record")
            bad = 1
            continue
        cols, runs, preps, mirrors, s_line, parts, clock = [], [], [], [], None, [], []
        for line in f.read_text().splitlines():
            p = line.split()
            if not p:
                continue
            if p[0] == "C":
                t, l0, l1, n, idx, look, ja, jb, r23, ycam, slot = (float(p[1]),) + tuple(int(x) for x in p[2:12])
                cols.append(dict(t=t, l0=l0, l1=l1, n=n, idx=idx, look=look, rows=jb - ja + 1, r23=r23, slot=slot))
            elif p[0] == "p":
                parts.append((cols[-1]["t"] if cols else None, tuple(int(x) for x in p[1:5])))
            elif p[0] == "G":
                clock.append((float(p[3]), int(p[1])))
            elif p[0] == "R":
                runs.append(int(p[2]))
            elif p[0] == "Q":
                preps.append(int(p[2]))
            elif p[0] == "M":
                mirrors.append(int(p[2]))
            elif p[0] == "S":
                s_line = [float(p[1])] + [int(x) for x in p[2:]]
            elif p[0] == "K":
                print(f"  {m}: windows: " + " ".join(p[1:]))
        print(f"== {m}: {len(cols)} vat columns drawn")
        if cols:
            span = cols[-1]["t"] - cols[0]["t"] or 1
            print(f"  {len(cols) / span:.1f} columns a second over {span:.1f} s; parts' time (lines): min "
                  f"{min(c['n'] for c in cols)}, median {st.median(c['n'] for c in cols):.0f}, max "
                  f"{max(c['n'] for c in cols)}; started at beam lines {min(c['l0'] for c in cols)}-"
                  f"{max(c['l0'] for c in cols)}")
            late = [c for c in cols if c["l1"] < c["l0"] and c["l1"] < VIEW]
            worst = None
            for c in late:
                ya = (c["slot"] - c["r23"]) & 255          # its first line on the screen
                if ya >= VIEW:
                    continue                                # (above the screen or below it: not shown)
                margin = ya - c["l1"]
                worst = margin if worst is None else min(worst, margin)
                if margin < 0:
                    bad = 1
                    print(f"  DRAWN BY THE BEAM: column {c['idx']} at {c['t']:.6f}: ended at line {c['l1']}, "
                          f"its first line {ya}")
            print(f"  {len(late)} ended in the next picture's display; the least margin to the column's first "
                  f"line: {worst if worst is not None else '-'} lines")
            per = {}
            for c in cols:
                per.setdefault(vat_of(c["idx"]), {}).setdefault(c["idx"], []).append(c["t"])
            for v in sorted(per):
                gaps = [b - a for ts in per[v].values() for a, b in zip(ts, ts[1:]) if b - a < 4]
                rate = f"{1 / st.median(gaps):.1f}" if gaps else "-"
                nd = sum(len(x) for x in per[v].values())
                print(f"  vat {v}: {len(per[v])} columns, {nd} draws ({nd / len(per[v]) / span:.2f} a column a second "
                      f"over the record); a column's look changes {rate} times a second (median of {len(gaps)} "
                      f"intervals under 4 s)")
        if runs:
            print(f"  vat_run with a column: {len(runs)}, median {st.median(runs):.0f} us, max {max(runs)} us")
        if preps:
            print(f"  vat_prep making one ready: {len(preps)}, median {st.median(preps):.0f} us, max {max(preps)} us")
        if s_line:
            secs, run_us, prep_us, rc, pc = s_line
            print(f"  CPU: vat_run {run_us / 1e4 / secs:.1f} %, vat_prep {prep_us / 1e4 / secs:.1f} % of {secs:.1f} s "
                  f"({rc} and {pc} calls)")
        if mirrors:
            print(f"  V9938 mirrors: {len(mirrors)}, VBLANKs from the column to its copy: median "
                  f"{st.median(mirrors):.0f}, max {max(mirrors)}")
        def frame_of(t):                                    # (the game frame at time t: the G lines)
            if t is None or len(clock) < 2:
                return None
            (t0, f0), (t1, f1) = (clock[0], clock[1]) if t <= clock[1][0] else \
                next(((a, b) for a, b in zip(clock, clock[1:]) if t <= b[0]), (clock[-2], clock[-1]))
            return f0 + (t - t0) * (f1 - f0) / ((t1 - t0) or 1)
        vparts = [(frame_of(t), q) for t, q in parts]

        def is_vat(q, f):
            return any(pq == q and (pf is None or abs(pf - f) <= 20) for pf, pq in vparts)
        g = d / f"guard_{m}.txt"
        if g.exists():
            txt = g.read_text().splitlines()
            print("  " + next((x for x in txt if x.startswith("guard:")), "guard: ?"))
            vt = vo = vc = oc = 0
            for x in txt:
                mf = re.search(r"f=(\d+)", x)
                f = int(mf.group(1)) if mf else 0
                mt = re.search(r"tear beam lines .* of command (\d+) (\d+) (\d+) (\d+) (\d+)", x)
                mc = re.search(r" cmd line \d+ op d0 dest \((\d+),(\d+)\) (\d+)x(\d+)", x)
                if mt:
                    q = tuple(int(mt.group(k)) for k in (2, 3, 4, 5))
                    if is_vat(q, f):
                        vt += 1
                        bad = 1
                        print(f"  A VAT COLUMN'S TEAR: {x.strip()}")
                    else:
                        vo += 1
                if mc:
                    q = (int(mc.group(1)), int(mc.group(2)), int(mc.group(3)), int(mc.group(4)))
                    if is_vat(q, f):
                        vc += 1
                    else:
                        oc += 1
            print(f"  guard tears: {vt} of a vat column, {vo} other; play-area commands: {vc} a vat column's "
                  f"(started while the beam was above it), {oc} other")
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv))
