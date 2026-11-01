#!/usr/bin/env python3
"""fieldsum.py: G-FIELD, the field check's windows taken together (performance campaign 2's kit,
docs/HARNESS.md section 12; docs/PERF2_PLAN.md 5.4).

  fieldsum.py run DIR [--root REPO] [--py PY] [--check FIELDCHECK] [--jobs N] [--force] [--only WIN_TAG ...]
      runs tools/bstest/fieldcheck.py on every window folder of DIR (gates.tcl pf_fd_setup's records:
      DIR/<win>_<tag>/ with level.txt and holds.txt), the level's conversion build/msx/level<N> and
      --level N, keeping its output in DIR/<win>_<tag>.fc.txt (and the contact sheet .png); then writes
      DIR/fieldsum.json. REPO: the checkout whose build/msx conversions and fieldcheck.py are used (default
      this repository; a git worktree has no build/: give the main checkout); PY: a Python with numpy
      (default ~/.venvs/msxports/bin/python); FIELDCHECK: another checker (a change of the converters
      brings its own, e.g. docs/PERF2_PLAN.md item 1's, with its own conversions in REPO); N: windows
      checked at once (default 4; a 900-record window takes about a minute).
      A window already checked is not checked again unless --force, or unless it was recorded again
      since (its level.txt or holds.txt newer than its .fc.txt: pf_fd_setup writes level.txt at every
      recording's start, holds.txt at its end).
  fieldsum.py table DIR    the summary per window: pictures, pictures with differences, the classes
  fieldsum.py gate BASE NEW [--partial]
      every window of BASE: FAIL when NEW shows a difference class that BASE's same window does not
      (docs/PERF2_PLAN.md 5.4 G-FIELD), not counting the pictures shown after FB_HOLD (their BOBs one
      picture behind the sprites: G-HOLD's class, holds.py); FAIL too when the window's pictures with
      differences (FB_HOLD's left out) grow beyond 3 x BASE's + 30 (a gross regression such as a misdrawn
      BOB in every picture, which a class BASE already shows would hide). A class whose pictures more than
      double (and grow by 3 or more) is reported as WARN (timing moves these pictures; look at them).
      A window is judged only when fieldcheck.py checked every record it wanted (its summary line's
      "N pictures (M checked)" with M the window's n, level.txt): a check that stopped (no summary: a
      crash, a wrong --root), records of another length (skipped), a recording cut short (a timed-out
      job), a check older than its records (the window recorded again since) or a window NEW lacks
      (--partial: listed, not judged) FAIL, as does a gate that judged none.

The classes are fieldcheck.py's "CLASS picture kind" lines (hostage-tear, smoke-tear, vat-look, vat-older,
other: a play-area pixel no sprite covers that is neither the tile nor the BOB the shown list has there,
nor the previous picture's). A picture's hold is fb_hold when the picture on screen was taken (isr.asm
iv_take; holds.txt). A window's first record is not judged: no record before it excuses a composition
under way (a timing-shifted, decision-identical build showed one there where HEAD showed none). Exit 0
only when nothing FAILs.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FB_HOLD = 8
FIRST = 'j001_f0000'                     # a window's first record (l2b_fd_hit's file name)


def windows(d):
    out = []
    for p in sorted(Path(d).iterdir()):
        if p.is_dir() and (p / 'level.txt').exists():
            out.append(p)
    return out


def stale(win):
    """the window was recorded again after its check: its level.txt (written when a recording starts) or
    holds.txt (when it ends) is newer than its .fc.txt"""
    fc = win.parent / (win.name + '.fc.txt')
    if not fc.exists():
        return False
    t = fc.stat().st_mtime
    return any((win / f).exists() and (win / f).stat().st_mtime > t for f in ('level.txt', 'holds.txt'))


def parse(win):
    """the window's fieldcheck output and holds -> summary"""
    fc = win.parent / (win.name + '.fc.txt')
    holds = {}
    hp = win / 'holds.txt'
    if hp.exists():
        for line in hp.read_text().splitlines():
            f = line.split()
            if len(f) >= 2:
                holds[f[0]] = int(f[1])
    cls, cls_hold = {}, {}
    pics_bad, pics_nonhold = set(), set()
    first = []
    summary = ''
    if fc.exists():
        for line in fc.read_text().splitlines():
            if line.startswith('CLASS '):
                f = line.split()
                stem, kind = f[1], f[2]
                if stem == FIRST:
                    first.append(kind)
                    continue
                pics_bad.add(stem)
                if holds.get(stem, 0) >= FB_HOLD:
                    cls_hold[kind] = cls_hold.get(kind, 0) + 1
                else:
                    cls[kind] = cls.get(kind, 0) + 1
                    pics_nonhold.add(stem)
            elif re.match(r'\d+ pictures \(', line):
                summary = line
    n = len([f for f in os.listdir(win) if f.endswith('.bin')])
    held = sum(1 for v in holds.values() if v >= FB_HOLD)
    lv = (win / 'level.txt').read_text().split() if (win / 'level.txt').exists() else []
    wanted = int(lv[lv.index('n') + 1]) if 'n' in lv[:-1] and lv[lv.index('n') + 1].isdigit() else None
    return {'records': n, 'checked': fc.exists(), 'classes': cls, 'hold_classes': cls_hold,
            'pictures_with_differences': len(pics_bad), 'pictures_nonhold': len(pics_nonhold), 'first_record': first,
            'records_held': held, 'summary': summary, 'wanted': wanted, 'stale': stale(win)}


def incomplete(r):
    """why a window's check does not cover the window (None when it does): fieldcheck's summary line
    "N pictures (M checked)" must be there with M = the records the window wanted (level.txt's n), and
    the check must be newer than the recording"""
    if not r['checked']:
        return 'not checked'
    if r.get('stale'):
        return 'the check predates the records (recorded again since: fieldsum.py run checks it again)'
    m = re.match(r'(\d+) pictures \((\d+) checked\)', r.get('summary') or '')
    if not m:
        return 'the check did not finish (no summary line)'
    want = r.get('wanted') or r['records']
    if int(m.group(2)) != want:
        return f"{m.group(2)} of {want} records checked"
    return None


def check_one(win, root, py, check):
    fc = win.parent / (win.name + '.fc.txt')
    lv = int((win / 'level.txt').read_text().split()[1])
    prefix = root / 'build' / 'msx' / f'level{lv}'
    cmd = [py, '-I', str(check), str(win), str(prefix), str(win.parent / (win.name + '.png'))]
    if lv in (2, 3):
        cmd += ['--level', str(lv)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    fc.write_text(r.stdout + (('\nSTDERR ' + r.stderr) if r.returncode else ''))
    last = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:]
    return f"{win.name}: exit {r.returncode}; {last}"


def run(d, root, py, check, force, only, jobs=4):
    from concurrent.futures import ThreadPoolExecutor
    todo = []
    for win in windows(d):
        if only and win.name not in only:
            continue
        fc = win.parent / (win.name + '.fc.txt')
        if fc.exists() and not force and not stale(win):
            continue
        todo.append(win)
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        for msg in ex.map(lambda w: check_one(w, root, py, check), todo):
            print(msg, flush=True)
    res = {w.name: parse(w) for w in windows(d)}
    (Path(d) / 'fieldsum.json').write_text(json.dumps(res, indent=1, sort_keys=True))
    return res


def load(d):
    """the windows' summaries, parsed from the window folders (fieldsum.json only when they are gone)"""
    wins = windows(d)
    if wins:
        return {w.name: parse(w) for w in wins}
    p = Path(d) / 'fieldsum.json'
    return json.loads(p.read_text()) if p.exists() else {}


def fmt(name, r):
    c = ', '.join(f"{k} {v}" for k, v in sorted(r['classes'].items())) or 'none'
    h = ', '.join(f"{k} {v}" for k, v in sorted(r['hold_classes'].items()))
    return (f"{name:16s} {r['records']:4d} records ({r['records_held']} after FB_HOLD), "
            f"{r['pictures_with_differences']:3d} with differences; classes: {c}{'; at FB_HOLD: ' + h if h else ''}"
            f"{'' if r['checked'] else '  (not checked)'}")


def main(argv):
    if len(argv) >= 2 and argv[0] == 'run':
        d = argv[1]
        py = os.path.expanduser('~/.venvs/msxports/bin/python')
        root = ROOT
        check = None
        force = '--force' in argv
        jobs = 4
        only = []
        i = 2
        while i < len(argv):
            if argv[i] == '--py':
                py = argv[i + 1]
                i += 2
            elif argv[i] == '--jobs':
                jobs = int(argv[i + 1])
                i += 2
            elif argv[i] == '--root':
                root = Path(argv[i + 1])
                i += 2
            elif argv[i] == '--check':
                check = Path(argv[i + 1])
                i += 2
            elif argv[i] == '--only':
                only = argv[i + 1:]
                break
            else:
                i += 1
        if check is None:
            check = root / 'tools' / 'bstest' / 'fieldcheck.py'
        res = run(d, root, py, check, force, only, jobs)
        for k, r in res.items():
            print(fmt(k, r))
        return 0
    if len(argv) == 2 and argv[0] == 'table':
        for k, r in load(argv[1]).items():
            print(fmt(k, r))
        return 0
    if len(argv) in (3, 4) and argv[0] == 'gate' and argv[3:] in ([], ['--partial']):
        partial = argv[3:] == ['--partial']
        base, new = load(argv[1]), load(argv[2])
        bad = judged = 0
        for k in sorted(new):
            r = new[k]
            if k not in base:
                print(f"{k:16s} (no baseline window)")
                continue
            b = base[k]
            ir, ib = incomplete(r), incomplete(b)
            if not ir and not ib and (r.get('wanted') or r['records']) != (b.get('wanted') or b['records']):
                ir = f"{r.get('wanted') or r['records']} records, the baseline's {b.get('wanted') or b['records']}"
            if ir or ib:
                print(f"{k:16s} FAIL: {'new' if ir else 'base'}: {ir or ib}")
                bad += 1
                continue
            judged += 1
            newc = sorted(set(r['classes']) - set(b['classes']))
            nb, nn = b.get('pictures_nonhold', 0), r.get('pictures_nonhold', 0)
            gross = nn > 3 * nb + 30
            warn = [c for c in r['classes'] if c in b['classes'] and r['classes'][c] >= 2 * b['classes'][c]
                    and r['classes'][c] - b['classes'][c] >= 3]
            line = f"{k:16s} base: {fmt('', b).split('; classes: ')[1]} | new: {fmt('', r).split('; classes: ')[1]}"
            if newc or gross:
                bad += 1
                why = [f"new class: {', '.join(newc)}"] if newc else []
                if gross:
                    why.append(f"{nn} pictures with differences against {nb}, FB_HOLD's left out")
                line += f"  FAIL ({'; '.join(why)})"
            elif warn:
                line += f"  WARN ({', '.join(warn)} more often)"
            print(line)
        for k in sorted(set(base) - set(new)):
            if partial:
                print(f"{k:16s} (no new window: not judged, --partial)")
            else:
                print(f"{k:16s} FAIL: no new window (--partial judges a subset)")
                bad += 1
        if not judged:
            print("no window judged")
            bad += 1
        print(f"G-FIELD: {'PASS' if not bad else f'FAIL ({bad} windows)'}")
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
