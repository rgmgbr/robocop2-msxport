#!/usr/bin/env python3
"""win.py: the speed of tick windows from m3.tcl's records (G-SPEED; performance campaign 2's kit,
docs/HARNESS.md section 12). Agent v_gain's window speed of 2026-11-01, with the gate's windows and verdict.

  win.py T0-T1 PREFIX...         one window of each run (PREFIX = a run's path without _ticks.txt)
  win.py --table DIR [--json OUT] every run in DIR named DRIVE_TAG (m3.tcl's NAME, e.g. kill_m2) and the
                                 gate's windows of its drive (WINDOWS below)
  win.py --gate BASE NEW [--partial]
                                 every run and window of BASE (the baseline's records) against NEW's
Options: --emu DIR, the drive files (default this checkout's build/emu; gate.sh passes REPO's, and then a
drive file that is not there is an error).

Per window: emulated seconds, ticks/s (game speed: 25 is full speed), pictures/s (pictures put on screen),
pictures/s with game progress (the list's game frame differs from the picture's before), the VBLANKs a
picture was held for its play-field BOBs (fb_hold). A run's ticks file holds a line per tick: tick_n,
emulated time, ...; its pics file a line per picture: time, tick, fb_hold, game frame, VBLANK count.
A window leaves out each teleport of its drive (ref.py: the test drive's poke, while the engines walk to
the new view and the ticks wait): the tick intervals from the teleport's game frame T to T + 2, their
time, their ticks and the pictures shown in them (tour3's seven teleports took 0.3-12.3 s each on the
MSX2, a stall play never has).

The gate (docs/PERF2_PLAN.md 5.4 G-SPEED, recalibrated for batch 2: docs/HARNESS.md 12.2). The reference
set of a window: BASE's value and those of BASE's timing controls (BASE/ctl/<name>/, the same runs: ref.py),
which differ from BASE only by a few T-states and show what a timing shift alone does to the window. FAIL
when NEW's ticks/s is below the reference set's lowest by more than the set's spread (highest - lowest),
and at least by FLOOR % of BASE's value (1 % for a window of 400 ticks or more, 4 % for a shorter one):
  NEW < lowest - max(spread, FLOOR % x BASE)
Without controls (a base folder with none): the flat rule of batch 1, 1 % (400 ticks or more) or 5 %
(shorter) below BASE. Level 1's drive_play (l1play) "must stay at 25 ticks/s and 25 pictures/s": its
ticks/s sit at the logic's cap (24.96), where CAD_MAX 2 would hide a slower frame, so its pictures/s and
progress pictures/s are judged too, by the same rule. A window NEW has not reached (a run that ended
early) FAILs, and so does a run BASE holds that NEW lacks (--partial: listed, not judged); a run BASE
lacks is listed, not judged; a gate that judged no window FAILs. Exit 0 only when nothing FAILs.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ref  # noqa: E402  (tools/bstest/perf2/ref.py)

# the drives' windows (tick ranges; m3.tcl's drive names; docs/PERF2_PLAN.md 5.4)
WINDOWS = {
    'kill': [(130, 1400), (300, 1500), (1500, 1765)],
    'boss': [(130, 1400)],
    'tour3': [(40, 210), (215, 540), (545, 1065), (1085, 1400)],
    'park': [(40, 1200)],
    'l2tour': [(20, 1590), (2080, 2350)],
    'l1play': [(40, 1450)],
}
SHORT = 400          # ticks: a shorter window's floor is 4 % (5 % without controls), a longer one's 1 % (1 %)
FLOOR_LONG, FLOOR_SHORT = 1.0, 4.0
FLAT_LONG, FLAT_SHORT = 1.0, 5.0
FRAME_RATE = ('l1play',)  # drives whose pictures/s and progress pictures/s the gate judges as well


def tolerance(t0, t1):
    """the flat rule's tolerance (no controls), in %"""
    return FLAT_SHORT if t1 - t0 < SHORT else FLAT_LONG


def floor(t0, t1):
    """the least margin below the reference set's lowest value, in % of BASE's"""
    return FLOOR_SHORT if t1 - t0 < SHORT else FLOOR_LONG


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


def window(tt, pp, t0, t1, skip=()):
    """the window's numbers, or None when the run did not reach it; skip: ticks whose interval to the next
    tick is left out (a teleport's stall: its time, the tick and the pictures shown in it)"""
    if t0 not in tt or t1 not in tt:
        return None
    a, b = tt[t0], tt[t1]
    cut = []                                    # (the intervals left out: from, to)
    for t in sorted(skip):
        if t0 <= t < t1 and t in tt and t + 1 in tt:
            cut.append((tt[t], tt[t + 1]))
    left = sum(y - x for x, y in cut)
    span = b - a - left
    n_t = (t1 - t0) - len(cut)
    r = {'from': t0, 'to': t1, 'seconds': round(span, 4), 'ticks_s': round(n_t / span, 3)}
    if cut:
        r['left_out'] = round(left, 3)
    if pp is not None:
        prev = None
        n = prog = held = 0
        for t, h, gf in pp:
            if t < a:
                prev = gf
                continue
            if t > b:
                break
            if any(x <= t < y for x, y in cut):
                prev = gf
                continue
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
    if r.get('left_out'):
        s += f" ({r['left_out']:.2f} s of teleports left out)"
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


def table(d, emu=None, strict=False):
    res = {}
    for name, prefix in runs(d).items():
        drive = name.rsplit('_', 1)[0]
        tt, pp = ticks(prefix), pics(prefix)
        skip = ref.skip_ticks(ref.teleports(drive, emu, strict))
        res[name] = {}
        for t0, t1 in WINDOWS[drive]:
            r = window(tt, pp, t0, t1, skip)
            res[name][f'{t0}-{t1}'] = r if r else {'from': t0, 'to': t1, 'missing': max(tt) if tt else -1}
    return res


def judge(b, cs, r, key, t0, t1):
    """NEW's value r[key] against BASE's b[key] and the controls' -> (ok, threshold, the reference text)"""
    vb = b[key]
    vals = [vb] + [c[key] for c in cs if key in c]
    if len(vals) == 1:
        thr = vb * (1 - tolerance(t0, t1) / 100)
        return r[key] >= thr, thr, f"flat {tolerance(t0, t1):.0f} %"
    lo, hi, sp = ref.span(vals)
    thr = lo - max(sp, floor(t0, t1) / 100 * vb)
    return r[key] >= thr, thr, f"ref {lo:.2f}-{hi:.2f}"


def gate(base_dir, new_dir, partial, emu=None, strict=False):
    base, new = table(base_dir, emu, strict), table(new_dir, emu, strict)
    ctls = [(c.name, table(str(c), emu, strict)) for c in ref.controls(base_dir)]
    if ctls:
        print(f"reference: BASE and its controls {', '.join(n for n, _ in ctls)} "
              f"(NEW below lowest - max(spread, {FLOOR_LONG} % / {FLOOR_SHORT} %) FAILs)")
    else:
        print(f"reference: BASE alone (no controls: {FLAT_LONG:.0f} % / {FLAT_SHORT:.0f} % below it FAILs)")
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
            cs = []
            for cn, ct in ctls:
                c = ct.get(name, {}).get(w)
                if not c or 'missing' in c:
                    print(f"{name:16s} {w}: FAIL: control {cn} lacks the window (the reference set is incomplete)")
                    bad += 1
                    c = None
                if c:
                    cs.append(c)
            if len(cs) != len(ctls):
                continue
            d = 100.0 * (r['ticks_s'] - b['ticks_s']) / b['ticks_s']
            ok, thr, rtxt = judge(b, cs, r, 'ticks_s', r['from'], r['to'])
            extra = ''
            if 'pictures_s' in r and 'pictures_s' in b:
                extra = (f"; pictures/s {b['pictures_s']:.2f} -> {r['pictures_s']:.2f}, with progress "
                         f"{b['progress_s']:.2f} -> {r['progress_s']:.2f}")
                if name.rsplit('_', 1)[0] in FRAME_RATE:
                    for k, what in (('pictures_s', 'pictures/s'), ('progress_s', 'progress pictures/s')):
                        if not b[k]:
                            continue
                        okk, thk, _ = judge(b, cs, r, k, r['from'], r['to'])
                        if not okk:
                            ok = False
                            extra += f" ({what} below {thk:.2f}: FAIL)"
            elif name.rsplit('_', 1)[0] in FRAME_RATE:
                ok = False
                extra = "; no pictures record (the drive's pictures/s are judged)"
            bad += not ok
            lo = f", {r['left_out']:.2f} s left out" if r.get('left_out') else ''
            print(f"{name:16s} {w:10s} ticks/s {b['ticks_s']:6.2f} -> {r['ticks_s']:6.2f} ({d:+6.2f} %; {rtxt}, "
                  f"FAIL below {thr:.2f}{lo}){extra}{'' if ok else '  FAIL'}")
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


def main(argv):
    partial = '--partial' in argv
    argv = [a for a in argv if a != '--partial']
    argv, emu = ref.emu_arg(argv)
    strict = emu is not None
    if len(argv) >= 2 and argv[0] == '--table':
        res = table(argv[1], emu, strict)
        for name, ws in res.items():
            for w, r in ws.items():
                print(fmt(name, r) if 'missing' not in r else f"{name:16s} {w}: not reached (last tick {r['missing']})")
        if len(argv) >= 4 and argv[2] == '--json':
            with open(argv[3], 'w') as f:
                json.dump(res, f, indent=1, sort_keys=True)
        return 0
    if len(argv) == 3 and argv[0] == '--gate':
        return gate(argv[1], argv[2], partial, emu, strict)
    if len(argv) >= 2 and '-' in argv[0] and not argv[0].startswith('-'):
        t0, t1 = (int(x) for x in argv[0].split('-'))
        for prefix in argv[1:]:
            name = os.path.basename(prefix)
            try:
                tt = ticks(prefix)
            except OSError:
                print(f'{name:16s} missing')
                continue
            skip = ref.skip_ticks(ref.teleports(name.rsplit('_', 1)[0], emu, strict))
            r = window(tt, pics(prefix), t0, t1, skip)
            print(fmt(name, r) if r else f'{name:16s} window not reached (last tick {max(tt) if tt else "-"})')
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
