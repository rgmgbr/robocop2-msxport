#!/usr/bin/env python3
"""vercmp.py BASE NEW: two cen.tcl censuses of the sprite budget (performance campaign 2's kit, docs/HARNESS.md
section 12; agent a_sprites' compare of 2026-11-01), record by record: every R, E, C, F and O record equal
but the R records' times (the census of docs/PERF2_PLAN.md items 12, 13 and 16: 0 differing records), then
the budget's own time per run in T-states (t_end - t_budget) and the line phase's (t_bgtot - t_lnfill).
An E/O record's O_OUT of an object not wanted (O_FLAGS bit 7 clear) is never read and not compared; an R
record's cand and anyb are visit counts, not decisions, and not compared. Exit 1 when a record differs or
the record counts differ.
"""
import sys

HZ = 3579545


def load(p):
    recs = []
    with open(p) as f:
        for line in f:
            t = line.split()
            if not t:
                continue
            if t[0] == "R":
                v = t[1:]
                times = [float(x) for x in v[1:6]]
                c = v[6:]
                recs.append(("R", v[0], tuple(c[:5] + c[7:]), times))
            elif t[0] in "EO":
                h = bytearray(bytes.fromhex(t[-1]))
                for o in range(16):
                    if not h[32 * o] & 0x80:
                        h[32 * o + 27] = 0
                recs.append((t[0], " ".join(t[1:-1] + [h.hex()]), None, None))
            else:
                recs.append((t[0], " ".join(t[1:]), None, None))
    return recs


def tsum(recs):
    w = ln = 0.0
    for r in recs:
        if r[0] != "R":
            continue
        t0, t1, t2, t3, t4 = r[3]
        w += t4 - t0
        if t1 >= 0:
            ln += t3 - t1
    return w * HZ, ln * HZ


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    a, b = load(argv[0]), load(argv[1])
    diff = 0
    first = None
    nr = sum(1 for r in a if r[0] == "R")
    nrb = sum(1 for r in b if r[0] == "R")
    for i, (x, y) in enumerate(zip(a, b)):
        if x[0] != y[0] or x[1] != y[1] or x[2] != y[2]:
            diff += 1
            if first is None:
                first = (i, x[:3], y[:3])
    print(f"records {len(a)} / {len(b)}, budget runs {nr} / {nrb}, differing records {diff}")
    if first:
        print("first difference:", first[0], str(first[1])[:200], "|", str(first[2])[:200])
    wa, la = tsum(a)
    wb, lb = tsum(b)
    if nr and nrb and wa and la:
        print(f"budget time: base {wa / nr:,.0f} T/run, new {wb / nrb:,.0f} T/run ({100 * (wb / nrb - wa / nr) / (wa / nr):+.1f} %); "
              f"line phase: base {la / nr:,.0f}, new {lb / nrb:,.0f} ({100 * (lb / nrb - la / nr) / (la / nr):+.1f} %)")
    ok = diff == 0 and len(a) == len(b)
    print(f"census: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
