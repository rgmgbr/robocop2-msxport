#!/usr/bin/env python3
"""flash12.py HEAD CONTROL [T0-T1]: the cost of levels 1-2's hit flash (performance campaign 2's kit,
docs/HARNESS.md section 12; docs/PERF2_PLAN.md 5.3, W0's step 3).

HEAD and CONTROL are two m3.tcl runs (PREFIX without _ticks.txt) of the same drive and machine: HEAD in
flash mode (each ticks line ends with the silhouette BOBs drawn in the tick: those of a shown tick, all),
CONTROL a build whose bob.asm draws BM_NORMAL where it drew BM_FLASH (the flash's look removed, nothing
else: the logic traces are identical). Over the tick window (default the whole drive):
  - the emulated time of each and the difference (the flash's whole cost, measured);
  - the flash ticks (a shown tick with a silhouette) and the flash pictures (HEAD's pictures whose list's
    game frame is a flash tick: tick_n is the game frame in an LV_TEST or EXTJOY drive), their time on
    screen (to the next picture), and the picture after each;
  - the cost per flash picture, and as a share of the time of the pictures where it shows (the flash
    pictures alone; with the picture after each, where the normal look comes back);
  - HEAD's mean picture time with and without a flash (a correlation only: flashes come in busy scenes).
docs/PERF2_PLAN.md 5.3: above about 20 % of those pictures' time, the silhouette toggle gets an item.
"""
import statistics as st
import sys


def ticks(prefix):
    tt, fl = {}, {}
    with open(prefix + '_ticks.txt') as f:
        for line in f:
            p = line.split()
            if len(p) < 2:
                continue
            g = int(p[0])
            tt.setdefault(g, float(p[1]))
            if len(p) >= 14:
                fl[g] = int(p[12])
    return tt, fl


def pics(prefix):
    out = []
    with open(prefix + '_pics.txt') as f:
        for line in f:
            p = line.split()
            if len(p) >= 4:
                out.append((float(p[0]), int(p[1]), int(p[3])))
    return out


def main(argv):
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    th, fl = ticks(argv[0])
    tc, _ = ticks(argv[1])
    if len(argv) == 3:
        t0, t1 = (int(x) for x in argv[2].split('-'))
    else:
        t0, t1 = max(min(th), min(tc)), min(max(th), max(tc))
    if not fl:
        print(f"{argv[0]}: no silhouette counts (run it in m3.tcl's flash mode)")
        return 2
    ah, bh, ac, bc = th[t0], th[t1], tc[t0], tc[t1]
    dh, dc = bh - ah, bc - ac
    ftk = {g for g, n in fl.items() if n > 0 and t0 <= g < t1}
    pp = [p for p in pics(argv[0])]
    durs = []
    for i in range(len(pp) - 1):
        t, tk, gf = pp[i]
        if ah <= t < bh:
            durs.append((t, gf, pp[i + 1][0] - t))
    flash = [d for d in durs if d[1] in ftk]
    idx = {d[0]: k for k, d in enumerate(durs)}
    after = []
    for d in flash:
        k = idx[d[0]] + 1
        if k < len(durs) and durs[k][1] not in ftk:
            after.append(durs[k])
    other = [d for d in durs if d[1] not in ftk]
    dflash = sum(d[2] for d in flash)
    dafter = sum(d[2] for d in after)
    cost = dh - dc
    name = argv[0].rsplit('/', 1)[-1]
    print(f"{name}: ticks {t0}-{t1}: HEAD {dh:.3f} s ({(t1 - t0) / dh:.2f} ticks/s), control {dc:.3f} s "
          f"({(t1 - t0) / dc:.2f} ticks/s): the flash costs {1000 * cost:+.1f} ms ({100 * cost / dh:+.2f} % of the window)")
    print(f"  flash ticks {len(ftk)}, flash pictures {len(flash)} ({1000 * dflash:.0f} ms on screen), "
          f"the pictures after them {len(after)} ({1000 * dafter:.0f} ms)")
    if flash:
        print(f"  per flash picture {1000 * cost / len(flash):+.1f} ms; share of the flash pictures' time "
              f"{100 * cost / dflash:+.1f} %, with the picture after each {100 * cost / (dflash + dafter):+.1f} %")
        print(f"  HEAD's picture ms: flash {1000 * st.mean(d[2] for d in flash):.0f} (median "
              f"{1000 * st.median(d[2] for d in flash):.0f}), after {1000 * st.mean(d[2] for d in after) if after else 0:.0f}, "
              f"others {1000 * st.mean(d[2] for d in other):.0f} (median {1000 * st.median(d[2] for d in other):.0f})")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
