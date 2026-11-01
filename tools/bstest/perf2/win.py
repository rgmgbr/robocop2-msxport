#!/usr/bin/env python3
"""win.py: the speed of tick windows from m3.tcl's records (G-SPEED; performance campaign 2's kit,
docs/HARNESS.md section 12). Agent v_gain's window speed of 2026-11-01, with the gate's windows and verdict.

  win.py T0-T1 PREFIX...         one window of each run (PREFIX = a run's path without _ticks.txt)
  win.py --table DIR [--json OUT] every run in DIR named DRIVE_TAG (m3.tcl's NAME, e.g. kill_m2) and the
                                 gate's windows of its drive (WINDOWS below)
  win.py --gate BASE NEW [--partial]
                                 every run and window of BASE (HEAD's records) against NEW's

Per window: emulated seconds, ticks/s (game speed: 25 is full speed), pictures/s (pictures put on screen),
pictures/s with game progress (the list's game frame differs from the picture's before), the VBLANKs a
picture was held for its play-field BOBs (fb_hold). A run's ticks file holds a line per tick: tick_n,
emulated time, ...; its pics file a line per picture: time, tick, fb_hold, game frame, VBLANK count.

The gate (docs/PERF2_PLAN.md 5.4 G-SPEED): FAIL when a window's ticks/s in NEW is below BASE's by more than
its tolerance: 1 % for a window of 400 ticks or more, 5 % for a shorter one (the ground floor, kill
1500-1765, is the plan's example; tour3's street, beams and roof, l2_tour 2080-2350 are as short).
Level 1's drive_play (l1play) "must stay at 25 ticks/s and 25 pictures/s": its ticks/s sit at the logic's
cap (24.96 at HEAD), where CAD_MAX 2 would hide a slower frame, so its pictures/s and progress pictures/s
are judged too, with the same tolerance. A window NEW has not reached (a run that ended early) FAILs, and
so does a run BASE holds that NEW lacks (--partial: listed, not judged, for a deliberate subset); a run
BASE lacks is listed, not judged; a gate that judged no window FAILs. Exit 0 only when nothing FAILs.
"""
import json
import os
import sys

# the drives' windows (tick ranges; m3.tcl's drive names; docs/PERF2_PLAN.md 5.4)
WINDOWS = {
    'kill': [(130, 1400), (300, 1500), (1500, 1765)],
    'boss': [(130, 1400)],
    'tour3': [(40, 210), (215, 540), (545, 1065), (1085, 1400)],
    'park': [(40, 1200)],
    'l2tour': [(20, 1590), (2080, 2350)],
    'l1play': [(40, 1450)],
}
SHORT = 400          # ticks: a shorter window's tolerance is 5 %, a longer one's 1 %
FRAME_RATE = ('l1play',)  # drives whose pictures/s and progress pictures/s the gate judges as well


def tolerance(t0, t1):
    return 5.0 if t1 - t0 < SHORT else 1.0


def ticks(prefix):
    tt = {}
    with open(prefix + '_ticks.txt') as f:
        for line in f:
            p = line.split()
            if len(p) >= 2:
                try:
                    tt.setdefault(int(p[0]), float(p[1]))
                except ValueError:
                    pass
    return tt


def pics(prefix):
    path = prefix + '_pics.txt'
    if not os.path.exists(path):
        return None
    out = []
    with open(path) as f:
        for line in f:
            p = line.split()
            if len(p) >= 4:
                try:
                    out.append((float(p[0]), int(p[2]), int(p[3])))
                except ValueError:
                    pass
    return out


def window(tt, pp, t0, t1):
    """the window's numbers, or None when the run did not reach it"""
    if t0 not in tt or t1 not in tt:
        return None
    a, b = tt[t0], tt[t1]
    span = b - a
    r = {'from': t0, 'to': t1, 'seconds': round(span, 4), 'ticks_s': round((t1 - t0) / span, 3)}
    if pp is not None:
        prev = None
        n = prog = held = 0
        for t, h, gf in pp:
            if t < a:
                prev = gf
                continue
            if t > b:
                break
            n += 1
            held += h
            if prev is None or gf != prev:
                prog += 1
            prev = gf
        r.update(pictures_s=round(n / span, 3), progress_s=round(prog / span, 3),
                 held_vbl=round(held / n, 3) if n else 0.0, pictures=n)
    return r


def fmt(name, r):
    s = f"{name:16s} {r['from']:5d}-{r['to']:<5d} {r['seconds']:8.2f} s {r['ticks_s']:6.2f} ticks/s"
    if 'pictures_s' in r:
        s += f" {r['pictures_s']:6.2f} pictures/s {r['progress_s']:6.2f} with progress, held {r['held_vbl']:4.2f} VBL"
    return s


def runs(d):
    out = {}
    for fn in sorted(os.listdir(d)):
        if fn.endswith('_ticks.txt'):
            name = fn[:-len('_ticks.txt')]
            drive = name.rsplit('_', 1)[0]
            if drive in WINDOWS:
                out[name] = os.path.join(d, name)
    return out


def table(d):
    res = {}
    for name, prefix in runs(d).items():
        tt, pp = ticks(prefix), pics(prefix)
        res[name] = {}
        for t0, t1 in WINDOWS[name.rsplit('_', 1)[0]]:
            r = window(tt, pp, t0, t1)
            res[name][f'{t0}-{t1}'] = r if r else {'from': t0, 'to': t1, 'missing': max(tt) if tt else -1}
    return res


def main(argv):
    partial = '--partial' in argv
    argv = [a for a in argv if a != '--partial']
    if len(argv) >= 2 and argv[0] == '--table':
        res = table(argv[1])
        for name, ws in res.items():
            for w, r in ws.items():
                print(fmt(name, r) if 'missing' not in r else f"{name:16s} {w}: not reached (last tick {r['missing']})")
        if len(argv) >= 4 and argv[2] == '--json':
            with open(argv[3], 'w') as f:
                json.dump(res, f, indent=1, sort_keys=True)
        return 0
    if len(argv) == 3 and argv[0] == '--gate':
        base, new = table(argv[1]), table(argv[2])
        bad = judged = 0
        for name in sorted(new):
            if name not in base:
                print(f"{name:16s} (no baseline run)")
                continue
            for w, r in new[name].items():
                b = base[name].get(w)
                if not b or 'missing' in b:
                    print(f"{name:16s} {w}: the baseline did not reach it")
                    continue
                judged += 1
                if 'missing' in r:
                    print(f"{name:16s} {w}: FAIL: not reached (last tick {r['missing']})")
                    bad += 1
                    continue
                tol = tolerance(r['from'], r['to'])
                d = 100.0 * (r['ticks_s'] - b['ticks_s']) / b['ticks_s']
                ok = d >= -tol
                extra = ''
                if 'pictures_s' in r and 'pictures_s' in b:
                    extra = (f"; pictures/s {b['pictures_s']:.2f} -> {r['pictures_s']:.2f}, with progress "
                             f"{b['progress_s']:.2f} -> {r['progress_s']:.2f}")
                    if name.rsplit('_', 1)[0] in FRAME_RATE:
                        for k, what in (('pictures_s', 'pictures/s'), ('progress_s', 'progress pictures/s')):
                            dk = 100.0 * (r[k] - b[k]) / b[k] if b[k] else 0.0
                            if dk < -tol:
                                ok = False
                                extra += f" ({what} {dk:+.2f} %: FAIL)"
                elif name.rsplit('_', 1)[0] in FRAME_RATE:
                    ok = False
                    extra = "; no pictures record (the drive's pictures/s are judged)"
                bad += not ok
                print(f"{name:16s} {w:10s} ticks/s {b['ticks_s']:6.2f} -> {r['ticks_s']:6.2f} ({d:+6.2f} %, "
                      f"tolerance {tol:.0f} %){extra}{'' if ok else '  FAIL'}")
        for name in sorted(set(base) - set(new)):
            if partial:
                print(f"{name:16s} (no new run: not judged, --partial)")
            else:
                print(f"{name:16s} FAIL: no new run (--partial judges a subset)")
                bad += 1
        if not judged:
            print("no window judged")
            bad += 1
        print(f"G-SPEED: {'PASS' if not bad else f'FAIL ({bad} windows)'}")
        return 1 if bad else 0
    if len(argv) >= 2 and '-' in argv[0] and not argv[0].startswith('-'):
        t0, t1 = (int(x) for x in argv[0].split('-'))
        for prefix in argv[1:]:
            name = os.path.basename(prefix)
            try:
                tt = ticks(prefix)
            except OSError:
                print(f'{name:16s} missing')
                continue
            r = window(tt, pics(prefix), t0, t1)
            print(fmt(name, r) if r else f'{name:16s} window not reached (last tick {max(tt) if tt else "-"})')
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
