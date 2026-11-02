#!/usr/bin/env python3
"""pgsum.py PATH...: flash-1's page-path uses by the state of their page (performance campaign 2's kit,
docs/HARNESS.md section 12), from pgprobe.tcl's records: each PATH a pg.txt or a folder searched for
<window>/pg.txt files. Per record: the uses ("G" lines) as ring (the V9958), shown (the V9938's page
shown), back-synced (the page beside, holding its list's BOBs) and back-rebuild (the page being built,
copied again for a new build target: its pixels are not its list's composition), and the new build
targets ("B" lines) with the page being built's items still queued, of those with its look flag set
(lane W2F's review, C/rev_w2f/tools/rvan.py). msx/field.asm fp_lkok lets flash-1 take a piece's
background only from the page shown on the V9938: a use on another page FAILs (exit 1), as does a
record without its summary line (a run cut short) or a path with no record."""
import sys
from pathlib import Path

KINDS = ('ring', 'shown', 'back-synced', 'back-rebuild')


def one(p):
    n = dict.fromkeys(KINDS, 0)
    b = bq = bl = 0
    summary = False
    for line in p.read_text().splitlines():
        f = line.split()
        if not f:
            continue
        if f[0] == 'G' and len(f) >= 15:
            page = int(f[4][:2], 16) & 1
            vis, back, bsync, eng = int(f[8]), int(f[9]), int(f[10]), int(f[14])
            if eng == 0:
                n['ring'] += 1
            elif page == vis:
                n['shown'] += 1
            elif bsync == back:
                n['back-synced'] += 1
            else:
                n['back-rebuild'] += 1
        elif f[0] == 'G':
            n.setdefault('old', 0)
            n['old'] += 1
        elif f[0] == 'B' and len(f) >= 11:
            b += 1
            q = int(f[8])
            if q > 0:
                bq += 1
                if int(f[9 + (int(f[4]) ^ 1)]) == 1:
                    bl += 1
        elif line.startswith('# page-path uses'):
            summary = True
    return n, b, bq, bl, summary


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    files = []
    for a in argv:
        p = Path(a)
        files += sorted(p.glob('*/pg.txt')) if p.is_dir() else [p]
    if not files:
        print('no pg.txt record')
        return 1
    bad = 0
    tot = dict.fromkeys(KINDS, 0)
    for p in files:
        n, b, bq, bl, summary = one(p)
        for k in KINDS:
            tot[k] += n[k]
        wrong = n['back-synced'] + n['back-rebuild']
        why = []
        if wrong:
            why.append(f"{wrong} on a page not shown")
        if not summary:
            why.append('no summary line (cut short)')
        if n.get('old'):
            why.append(f"{n['old']} uses without the page state (an older probe)")
        bad += bool(why)
        print(f"{p.parent.name:16s} uses {sum(n[k] for k in KINDS):5d}: " + ', '.join(f"{k} {n[k]}" for k in KINDS) +
              f"; new targets {b} (page being built's items queued {bq}, its flag set {bl})" +
              (f"  FAIL ({'; '.join(why)})" if why else ''))
    print(f"all: {sum(tot.values())} uses: " + ', '.join(f"{k} {tot[k]}" for k in KINDS) + f"; {'FAIL' if bad else 'PASS'}")
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
