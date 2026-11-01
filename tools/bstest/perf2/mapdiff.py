#!/usr/bin/env python3
"""mapdiff.py: the map's state of two runs at the same ticks (G-MAP; performance campaign 2's kit,
docs/HARNESS.md section 12; agent a_logic's compare of 2026-11-01).

  mapdiff.py A_map.txt B_map.txt [--ignore 0A33-0AFF ...]   two cnt.tcl map dumps
  mapdiff.py --gate BASE NEW [--ignore ...] [--partial]     every DRIVE_TAG_map.txt BASE holds, against NEW's:
                                                            FAIL on a byte, on a tick BASE dumped and NEW did
                                                            not (a run that ended early), on a dump NEW lacks
                                                            (--partial: listed, not judged)

A dump (cnt.tcl, NAME_map.txt) holds "tick hexA hexB hexC" every 100 ticks: A = 0910h-0FFFh (ATR_RAM1, MP_ROW,
the MP_A pool), B = 1082h-1F9Bh (atr_lost, mp_lost, the redraw queue's pointers, ATR_RAM0, atr_lut),
C = F500h-F9FFh (the MP_B pool). 1085h-108Bh are never compared (the redraw queue's head, tail and phase,
rd_lost, tc_loads, map_write's scratch mw_atr: the display's timing, not the map). --ignore FROM-TO (hex,
inclusive) leaves out more: a change that puts its own RAM inside these ranges (docs/PERF2_PLAN.md item 10's
row hints in MP_ROW's tail: --ignore 0A33-0AFF). Prints the ticks that differ; exit 1 on any difference,
when the runs share no tick, or when one run dumped a tick the other did not.
"""
import os
import sys

BASES = (0x0910, 0x1082, 0xF500)
ALWAYS = [(0x1085, 0x108B)]


def load(p):
    d = {}
    with open(p) as f:
        for line in f:
            p_ = line.split()
            if len(p_) == 4:
                d[int(p_[0])] = (bytes.fromhex(p_[1]), bytes.fromhex(p_[2]), bytes.fromhex(p_[3]))
    return d


def compare(pa, pb, ignore, quiet=False):
    a, b = load(pa), load(pb)
    bad = 0
    ticks = sorted(set(a) & set(b))
    for t in ticks:
        diffs = []
        for k in range(3):
            for i, (x, y) in enumerate(zip(a[t][k], b[t][k])):
                addr = BASES[k] + i
                if any(lo <= addr <= hi for lo, hi in ignore):
                    continue
                if x != y:
                    diffs.append(f"{addr:04X}:{x:02X}/{y:02X}")
        if diffs:
            bad += 1
            if not quiet:
                print(f"  tick {t}: {len(diffs)} bytes differ: {' '.join(diffs[:12])}")
    only = sorted(set(a) ^ set(b))
    if only and not quiet:
        print(f"  ticks dumped by one run only: {' '.join(str(t) for t in only[:12])}{' ...' if len(only) > 12 else ''}")
    return len(ticks), bad, (ticks[0] if ticks else None), (ticks[-1] if ticks else None), len(only)


def main(argv):
    ignore = list(ALWAYS)
    rest = []
    partial = False
    i = 0
    while i < len(argv):
        if argv[i] == '--ignore':
            lo, hi = argv[i + 1].split('-')
            ignore.append((int(lo, 16), int(hi, 16)))
            i += 2
        elif argv[i] == '--partial':
            partial = True
            i += 1
        else:
            rest.append(argv[i])
            i += 1
    if len(rest) == 3 and rest[0] == '--gate':
        base, new = rest[1], rest[2]
        fails = judged = 0
        names = sorted(f for f in os.listdir(new) if f.endswith('_map.txt'))
        for fn in sorted(f for f in os.listdir(base) if f.endswith('_map.txt')):
            if fn not in names:
                if partial:
                    print(f"{fn}: no new dump (not judged, --partial)")
                else:
                    print(f"{fn}: FAIL: no new dump (--partial judges a subset)")
                    fails += 1
        for fn in names:
            if not os.path.exists(os.path.join(base, fn)):
                print(f"{fn}: no baseline")
                continue
            judged += 1
            n, bad, t0, t1, only = compare(os.path.join(base, fn), os.path.join(new, fn), ignore)
            ok = n > 0 and bad == 0 and only == 0
            fails += not ok
            print(f"{fn}: {n} ticks compared ({t0}..{t1}), {bad} differ"
                  f"{f', {only} ticks dumped by one run only' if only else ''}{'' if ok else '  FAIL'}")
        if not judged:
            print("no dump judged")
        ok = judged and not fails
        print(f"G-MAP: {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    if len(rest) == 2:
        n, bad, t0, t1, only = compare(rest[0], rest[1], ignore)
        print(f"{n} ticks compared ({t0}..{t1}), {bad} differ{f', {only} ticks dumped by one run only' if only else ''}")
        return 1 if bad or not n or only else 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
