#!/usr/bin/env python3
"""guardsum.py: G-GUARD, the display guard over whole drives (performance campaign 2's kit, docs/HARNESS.md
section 12; docs/PERF2_PLAN.md 5.4).

  guardsum.py table DIR        every gates.tcl pf_guard_jobs record (DIR/<drive>_<tag>.txt): the rows
                               driven, rc2_guard's counts (reg, pal, cmd, cpu, vbl, tear), patcheck,
                               sprlines, satcheck
  guardsum.py gate BASE NEW [--partial]
                               every record of BASE: FAIL when NEW's tears exceed the highest count of
                               BASE and its timing controls (BASE/ctl/<name>/, ref.py: builds that differ
                               from BASE only by a few T-states; a tear's count moves with timing, 108 ->
                               116 for 4 NOPs a tick) by more than their spread (highest - lowest) and at
                               least by SLACK (3 tears, or 5 % of the highest):
                                 NEW > highest + max(spread, SLACK)
                               (without controls: NEW > BASE, batch 1's rule); when patcheck finds more
                               bad entries than any of them, when the drive was not driven to its end, or
                               when NEW lacks the record (--partial: listed, not judged); the other
                               counters are listed (above the reference set's highest: WARN)
Exit 0 only when nothing FAILs (a gate that judged no record FAILs). The guard (tools/openmsx_rc2.tcl rc2_guard) counts a VDP command still
writing into lines being shown (tear), register writes during the shown lines (reg), palette writes (pal),
commands running into the picture's start (cmd), CPU VRAM access during them (cpu), late VBLANK work (vbl).
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ref  # noqa: E402  (tools/bstest/perf2/ref.py)

SLACK_ABS, SLACK_REL = 3, 0.05   # tears a count may pass the reference set's highest: 3, or 5 % of it
KEYS = ('reg', 'pal', 'cmd', 'cpu', 'vbl', 'tear')


def parse(p):
    r = {}
    with open(p) as f:
        for line in f:
            if line.startswith('rows:'):
                r['rows'] = int(line.split()[1])
            elif line.startswith('guard:'):
                for k, v in re.findall(r'(\w+) (\d+)', line[6:]):
                    r[k] = int(v)
            elif line.startswith('patcheck:'):
                m = re.search(r'(\d+) entries, (\d+) bad', line)
                if m:
                    r['pat_bad'] = int(m.group(2))
            elif line.startswith('sprlines:'):
                r['sprlines'] = int(line.split()[1])
            elif line.startswith('satcheck:'):
                r['satcheck'] = int(line.split()[1])
            elif line.startswith('end: game frame'):
                r['end_frame'] = int(line.split()[3])
    return r


def table(d):
    out = {}
    for fn in sorted(os.listdir(d)):
        if fn.endswith('.txt') and not fn.endswith('_trace.txt'):
            r = parse(os.path.join(d, fn))
            if 'tear' in r:
                out[fn[:-4]] = r
    return out


def fmt(r):
    return (f"rows {r.get('rows', '?')}, " + ', '.join(f"{k} {r.get(k, '?')}" for k in KEYS) +
            f"; patcheck bad {r.get('pat_bad', '?')}, sprlines {r.get('sprlines', '?')}, satcheck {r.get('satcheck', '?')}")


def main(argv):
    partial = '--partial' in argv
    argv = [a for a in argv if a != '--partial']
    if len(argv) == 2 and argv[0] == 'table':
        for k, r in table(argv[1]).items():
            print(f"{k:10s} {fmt(r)}")
        return 0
    if len(argv) == 3 and argv[0] == 'gate':
        base, new = table(argv[1]), table(argv[2])
        ctls = [(c.name, table(str(c))) for c in ref.controls(argv[1])]
        if ctls:
            print(f"reference: BASE and its controls {', '.join(n for n, _ in ctls)} (NEW above highest + "
                  f"max(spread, {SLACK_ABS} or {SLACK_REL:.0%}) FAILs)")
        else:
            print("reference: BASE alone (no controls: more tears than BASE FAILs)")
        bad = judged = 0
        for k in sorted(new):
            r = new[k]
            if k not in base:
                print(f"{k:10s} (no baseline)")
                continue
            b = base[k]
            judged += 1
            why, warn = [], []
            cs = [ct.get(k) for _, ct in ctls]
            if not all(cs):
                why.append(f"the controls {', '.join(n for (n, _), c in zip(ctls, cs) if not c)} lack the record")
                cs = [c for c in cs if c]
            refs = [b] + cs
            if r.get('rows') != b.get('rows'):
                why.append(f"rows {r.get('rows')} (base {b.get('rows')})")
            vals = [x['tear'] for x in refs]
            lo, hi, sp = ref.span(vals)
            thr = hi + max(sp, SLACK_ABS, round(SLACK_REL * hi)) if ctls else hi
            if r['tear'] > thr:
                why.append(f"tears {r['tear']} above {thr}")
            if r.get('pat_bad', 0) > max(x.get('pat_bad', 0) for x in refs):
                why.append(f"patcheck bad {b.get('pat_bad')} -> {r.get('pat_bad')}")
            for kk in ('reg', 'pal', 'cmd', 'cpu', 'vbl', 'sprlines', 'satcheck'):
                if r.get(kk, 0) > max(x.get(kk, 0) for x in refs):
                    warn.append(f"{kk} {'/'.join(str(x.get(kk)) for x in refs)} -> {r.get(kk)}")
            bad += bool(why)
            rt = f" (reference {', '.join(str(v) for v in vals)}, FAIL above {thr})" if ctls else ''
            print(f"{k:10s} tears {b['tear']} -> {r['tear']}{rt}" + (f"  FAIL ({'; '.join(why)})" if why else '') +
                  (f"  WARN ({'; '.join(warn)})" if warn else ''))
        for k in sorted(set(base) - set(new)):
            if partial:
                print(f"{k:10s} (no new record: not judged, --partial)")
            else:
                print(f"{k:10s} FAIL: no new record (--partial judges a subset)")
                bad += 1
        if not judged:
            print("no record judged")
            bad += 1
        print(f"G-GUARD: {'PASS' if not bad else f'FAIL ({bad} runs)'}")
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
