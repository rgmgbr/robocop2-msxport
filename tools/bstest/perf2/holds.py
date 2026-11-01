#!/usr/bin/env python3
"""holds.py: the pictures that reached FB_HOLD (G-HOLD; performance campaign 2's kit, docs/HARNESS.md
section 12). Agent a_scroll's count of 2026-11-01, per minute of play over whole drives.

A picture reaches FB_HOLD when the VBLANK put it on screen after holding it FB_HOLD (8) VBLANKs for its
play-field BOBs (isr.asm iv_take after fb_pend): its BOBs are one picture behind its sprites. The class
predates the campaign and moves with any change of timing; short windows are noise (control builds
scatter between 3 and 7), so the gate counts whole drives.

  holds.py PREFIX [FROM TO]        a run (m3.tcl's records: PREFIX_ticks.txt, PREFIX_pics.txt): the whole
                                   drive (its first tick to its last), or the tick window FROM-TO
  holds.py --table DIR [--json OUT] every run in DIR (DRIVE_TAG, m3.tcl's names) over its whole drive
  holds.py --gate BASE NEW         every judged run of BASE (HEAD's records): FAIL when NEW's FB_HOLD pictures
                                   per minute exceed BASE's, when NEW's run does not span BASE's ticks (a run
                                   that ended early), or when NEW lacks the run (--partial: listed, not
                                   judged); a gate that judged no run FAILs. Exit 0 only when nothing FAILs.
Options: --hold N (default 8, msx/isr.asm FB_HOLD); --partial.
"""
import json
import os
import sys

DRIVES = ('kill', 'boss', 'tour3', 'park', 'l2tour', 'l1play')
GATE_DRIVES = ('kill', 'boss', 'tour3', 'l2tour')


def count(prefix, f=None, t=None, hold=8):
    tt = {}
    with open(prefix + '_ticks.txt') as fh:
        for line in fh:
            p = line.split()
            if len(p) >= 2:
                tt.setdefault(int(p[0]), float(p[1]))
    if not tt:
        return None
    if f is None:
        f, t = min(tt), max(tt)
    if f not in tt or t not in tt:
        return None
    t0, t1 = tt[f], tt[t]
    tot = n8 = vb = 0
    with open(prefix + '_pics.txt') as fh:
        for line in fh:
            p = line.split()
            if len(p) < 3:
                continue
            tm = float(p[0])
            if not (t0 <= tm < t1):
                continue
            x = int(p[2])
            tot += 1
            vb += x
            n8 += x >= hold
    span = t1 - t0
    return {'from': f, 'to': t, 'seconds': round(span, 3), 'pictures': tot, 'fb_hold': n8,
            'per_min': round(60.0 * n8 / span, 3), 'per_pic_pct': round(100.0 * n8 / max(1, tot), 3),
            'held_vbl_pct': round(100.0 * vb / (span * 59.92), 2)}


def fmt(name, r):
    return (f"{name:16s} {r['from']}-{r['to']}: {r['seconds']:7.1f} s, pictures {r['pictures']:5d}, FB_HOLD reached "
            f"{r['fb_hold']:4d} ({r['per_pic_pct']:4.1f} %), {r['per_min']:6.2f} a minute, held VBLANKs {r['held_vbl_pct']:4.1f} %")


def table(d, hold):
    res = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith('_ticks.txt'):
            continue
        name = fn[:-len('_ticks.txt')]
        if name.rsplit('_', 1)[0] not in DRIVES or not os.path.exists(os.path.join(d, name + '_pics.txt')):
            continue
        r = count(os.path.join(d, name), hold=hold)
        if r:
            res[name] = r
    return res


def main(argv):
    hold = 8
    if '--hold' in argv:
        i = argv.index('--hold')
        hold = int(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    partial = '--partial' in argv
    argv = [a for a in argv if a != '--partial']
    if len(argv) >= 2 and argv[0] == '--table':
        res = table(argv[1], hold)
        for name, r in res.items():
            print(fmt(name, r))
        if len(argv) >= 4 and argv[2] == '--json':
            with open(argv[3], 'w') as f:
                json.dump(res, f, indent=1, sort_keys=True)
        return 0
    if len(argv) == 3 and argv[0] == '--gate':
        base, new = table(argv[1], hold), table(argv[2], hold)
        bad = judged = 0
        for name in sorted(new):
            if name.rsplit('_', 1)[0] not in GATE_DRIVES:
                continue
            if name not in base:
                print(f"{name:16s} (no baseline run)")
                continue
            b, r = base[name], new[name]
            judged += 1
            why = ''
            if (r['from'], r['to']) != (b['from'], b['to']):
                why = f"  FAIL: ticks {r['from']}-{r['to']}, the baseline's {b['from']}-{b['to']}"
            elif r['per_min'] > b['per_min']:
                why = '  FAIL'
            bad += bool(why)
            print(f"{name:16s} FB_HOLD a minute {b['per_min']:6.2f} -> {r['per_min']:6.2f} ({b['fb_hold']} -> {r['fb_hold']} "
                  f"pictures, {b['seconds']:.0f} -> {r['seconds']:.0f} s){why}")
        for name in sorted(n for n in set(base) - set(new) if n.rsplit('_', 1)[0] in GATE_DRIVES):
            if partial:
                print(f"{name:16s} (no new run: not judged, --partial)")
            else:
                print(f"{name:16s} FAIL: no new run (--partial judges a subset)")
                bad += 1
        if not judged:
            print("no run judged")
            bad += 1
        print(f"G-HOLD: {'PASS' if not bad else f'FAIL ({bad} runs)'}")
        return 1 if bad else 0
    if len(argv) in (1, 3) and not argv[0].startswith('-'):
        f = t = None
        if len(argv) == 3:
            f, t = int(argv[1]), int(argv[2])
        r = count(argv[0], f, t, hold)
        print(fmt(os.path.basename(argv[0]), r) if r else f"{argv[0]}: window not reached")
        return 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
