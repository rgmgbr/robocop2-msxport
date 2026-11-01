#!/usr/bin/env python3
"""guardsum.py: G-GUARD, the display guard over whole drives (performance campaign 2's kit, docs/HARNESS.md
section 12; docs/PERF2_PLAN.md 5.4).

  guardsum.py table DIR        every gates.tcl pf_guard_jobs record (DIR/<drive>_<tag>.txt): the rows
                               driven, rc2_guard's counts (reg, pal, cmd, cpu, vbl, tear), patcheck,
                               sprlines, satcheck
  guardsum.py gate BASE NEW    every record both hold: FAIL when NEW's tears exceed BASE's (the plan's
                               rule), when patcheck finds a bad entry BASE did not, or when the drive was
                               not driven to its end; the other counters are listed (an increase: WARN)
Exit 0 only when nothing FAILs. The guard (tools/openmsx_rc2.tcl rc2_guard) counts a VDP command still
writing into lines being shown (tear), register writes during the shown lines (reg), palette writes (pal),
commands running into the picture's start (cmd), CPU VRAM access during them (cpu), late VBLANK work (vbl).
"""
import os
import re
import sys

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
    if len(argv) == 2 and argv[0] == 'table':
        for k, r in table(argv[1]).items():
            print(f"{k:10s} {fmt(r)}")
        return 0
    if len(argv) == 3 and argv[0] == 'gate':
        base, new = table(argv[1]), table(argv[2])
        bad = 0
        for k in sorted(new):
            r = new[k]
            if k not in base:
                print(f"{k:10s} (no baseline)")
                continue
            b = base[k]
            why, warn = [], []
            if r.get('rows') != b.get('rows'):
                why.append(f"rows {r.get('rows')} (base {b.get('rows')})")
            if r['tear'] > b['tear']:
                why.append(f"tears {b['tear']} -> {r['tear']}")
            if r.get('pat_bad', 0) > b.get('pat_bad', 0):
                why.append(f"patcheck bad {b.get('pat_bad')} -> {r.get('pat_bad')}")
            for kk in ('reg', 'pal', 'cmd', 'cpu', 'vbl', 'sprlines', 'satcheck'):
                if r.get(kk, 0) > b.get(kk, 0):
                    warn.append(f"{kk} {b.get(kk)} -> {r.get(kk)}")
            bad += bool(why)
            print(f"{k:10s} tears {b['tear']} -> {r['tear']}" + (f"  FAIL ({'; '.join(why)})" if why else '') +
                  (f"  WARN ({'; '.join(warn)})" if warn else ''))
        for k in sorted(set(base) - set(new)):
            print(f"{k:10s} (no new record)")
        print(f"G-GUARD: {'PASS' if not bad else f'FAIL ({bad} runs)'}")
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
