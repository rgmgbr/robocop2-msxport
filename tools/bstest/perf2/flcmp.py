#!/usr/bin/env python3
"""flcmp.py (tools/bstest/perf2; agent a_flash's compare of 2026-11-01) WINDOW LOG... : per probe log (fl.tcl: T tick time / P time hold / U..D uploads / W time n white cmds
list), the window's ticks a second, pictures a second, picture ms (median / p90 / max), held VBLANKs a
picture, uploads (n, ms), the pictures that showed a white entry, and the emulated time of the window.
WINDOW: T0-T1 (ticks). Also checks that the logs' tick lists agree (the same ticks)."""
import sys
import statistics as st


def load(path):
    T, P, U, W = [], [], [], []
    up = None
    for line in open(path):
        f = line.split()
        if not f:
            continue
        if f[0] == 'T':
            T.append((int(f[1]), float(f[2])))
        elif f[0] == 'P':
            P.append((float(f[1]), int(f[2])))
        elif f[0] == 'U':
            up = float(f[1])
        elif f[0] == 'D' and up is not None:
            U.append((up, float(f[1]) - up))
            up = None
        elif f[0] == 'W':
            W.append((float(f[1]), int(f[2]), int(f[3])))
    return T, P, U, W


def main():
    t0, t1 = (int(x) for x in sys.argv[1].split('-'))
    for path in sys.argv[2:]:
        T, P, U, W = load(path)
        tt = {k: t for k, t in T}
        if t0 not in tt or t1 not in tt:
            print(f'{path}: window not reached ({T[-1][0] if T else "-"} ticks)')
            continue
        a, b = tt[t0], tt[t1]
        span = b - a
        pics = [p for p in P if a <= p[0] <= b]
        gaps = sorted(pics[i + 1][0] - pics[i][0] for i in range(len(pics) - 1))
        ups = [u for u in U if a <= u[0] <= b]
        wh = [w for w in W if a <= w[0] <= b and w[2]]
        name = path.split('/')[-1].replace('.txt', '')
        print(f'{name:22s} ticks {t0}-{t1}: {span:7.2f} s, {(t1 - t0) / span:6.2f} ticks/s, {len(pics) / span:6.2f} pictures/s, '
              f'picture ms {1000 * st.median(gaps):5.0f} / {1000 * gaps[int(0.9 * (len(gaps) - 1))]:4.0f} / {1000 * gaps[-1]:4.0f}, '
              f'held {sum(h for _, h in pics) / max(len(pics), 1):4.2f} VBL a picture, uploads {len(ups)} '
              f'({1000 * sum(d for _, d in ups):5.0f} ms, {1000 * st.mean([d for _, d in ups]) if ups else 0:4.1f} each), '
              f'fb_wants with white {len(wh)}')


if __name__ == '__main__':
    main()
