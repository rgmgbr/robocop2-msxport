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
      every window of BASE, against the reference set: BASE's same window and its timing controls'
      (BASE/ctl/<name>/<win>: builds of BASE that differ from it only by a few T-states, ref.py;
      docs/PERF2_PLAN.md 5.4 G-FIELD, recalibrated: docs/HARNESS.md 12.2). Per difference class, the
      pictures that show it, not counting those shown after FB_HOLD (their BOBs one picture behind the
      sprites: G-HOLD's class, holds.py): FAIL when NEW's pass the reference set's highest by more than
      their spread and at least by SLACK (3) pictures (a class none of them shows: from 4 pictures), and
      pass the highest count the reference set shows in the same window on another machine; above the
      highest but within that: WARN (timing moves these pictures: a pure timing shift made one to three
      hostage tears appear where BASE had none, l1c860 on the MSX2 with ct3, which BASE shows on the
      FS-A1FX; look at them). FAIL too when the window's
      pictures with differences (FB_HOLD's left out) grow beyond 3 x the reference set's highest + 30 (a
      gross regression such as a misdrawn BOB in every picture).
      Left out of every window, BASE's and its controls' as NEW's: the records of a teleport's stall (game
      frames T .. T + TELE_REC - 1 of each teleport T of the window's drive: the test drive pokes RoboCop's
      place and the engines walk to the new view, ref.py), the class "other" in the TELE_NOTE game frames
      after it (the redraw queue waits behind that walk: stale beam cells, the test drive's artefact; play
      relocates through engines_jump, which clears the queue and draws the view), and the records past
      the drive's end (game frame >= its rows: kill's level ends at 1861, the end screen fieldcheck.py
      does not model); level.txt names the drive's rows and teleports (gates.tcl pf_fd_setup), holds.txt
      each record's game frame.
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
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ref  # noqa: E402  (tools/bstest/perf2/ref.py)

FB_HOLD = 8
FIRST = 'j001_f0000'                     # a window's first record (l2b_fd_hit's file name)
TELE_REC = 3                             # a teleport's stall: its records show game frame T + 1 or T + 2
TELE_NOTE = 40                           # game frames after a teleport whose "other" pictures are left out
SLACK = 3                                # pictures a class may pass the reference set's highest


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


# the gate drives of the windows (gates.tcl ::pf_field_wins): a window's name -> ref.DRIVES' drive, for records
# whose level.txt does not name the drive's rows and teleports (recorded before pf_fd_setup wrote them)
WIN_DRIVES = (('kill', 'kill'), ('boss', 'boss'), ('park', 'park'), ('tour', 'tour3'), ('l2t', 'l2tour'))


def drive_of(win, lv):
    """the window's drive's (rows, teleports): level.txt's "rows R tele T1,T2" when it has them, else the
    window's gate drive's (ref.py), else (None, [])"""
    if 'rows' in lv and 'tele' in lv:
        try:
            rows = int(lv[lv.index('rows') + 1])
            t = lv[lv.index('tele') + 1]
            return rows, ([] if t == '-' else [int(x) for x in t.split(',')])
        except (ValueError, IndexError):
            pass
    name = win.name.rsplit('_', 1)[0]
    for pre, d in WIN_DRIVES:
        if name.startswith(pre):
            return ref.DRIVES[d][1], ref.teleports(d)
    return None, []


def parse(win):
    """the window's fieldcheck output and holds -> summary (the records of teleports' stalls and past the
    drive's end left out)"""
    fc = win.parent / (win.name + '.fc.txt')
    lv = (win / 'level.txt').read_text().split() if (win / 'level.txt').exists() else []
    rows, teles = drive_of(win, lv)
    holds, gfs = {}, {}
    hp = win / 'holds.txt'
    if hp.exists():
        for line in hp.read_text().splitlines():
            f = line.split()
            if len(f) >= 2:
                holds[f[0]] = int(f[1])
            if len(f) >= 4:
                gfs[f[0]] = int(f[3])

    def why_out(stem):
        g = gfs.get(stem)
        if g is None:
            return None
        if rows is not None and g >= rows:
            return 'end'
        if any(t <= g < t + TELE_REC for t in teles):
            return 'tele'
        return None
    left = {'end': 0, 'tele': 0}
    for st in gfs:
        w = why_out(st)
        if w:
            left[w] += 1
    cls, cls_hold, cls_out = {}, {}, {}
    pics_bad, pics_nonhold, after_tele = set(), set(), set()
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
                w = why_out(stem)
                g = gfs.get(stem)
                if not w and kind == 'other' and g is not None and any(t <= g < t + TELE_NOTE for t in teles):
                    w = 'after a teleport'
                    after_tele.add(stem)
                if w:
                    cls_out[f"{kind} ({w})"] = cls_out.get(f"{kind} ({w})", 0) + 1
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
    wanted = int(lv[lv.index('n') + 1]) if 'n' in lv[:-1] and lv[lv.index('n') + 1].isdigit() else None
    return {'records': n, 'checked': fc.exists(), 'classes': cls, 'hold_classes': cls_hold,
            'pictures_with_differences': len(pics_bad), 'pictures_nonhold': len(pics_nonhold), 'first_record': first,
            'records_held': held, 'summary': summary, 'wanted': wanted, 'stale': stale(win),
            'left_out': left, 'left_classes': cls_out, 'after_teleport': len(after_tele)}


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
    lo = r.get('left_out') or {}
    out = ', '.join(f"{v} {k}" for k, v in sorted(lo.items()) if v)
    lc = ', '.join(f"{k} {v}" for k, v in sorted((r.get('left_classes') or {}).items()))
    return (f"{name:16s} {r['records']:4d} records ({r['records_held']} after FB_HOLD"
            f"{'; left out: ' + out + ' records' if out else ''}{'; left-out pictures: ' + lc if lc else ''}), "
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
        ctls = [(c.name, load(c)) for c in ref.controls(argv[1])]
        if ctls:
            print(f"reference: BASE and its controls {', '.join(n for n, _ in ctls)} (a class's pictures above "
                  f"highest + max(spread, {SLACK}) and above the window's on any machine, or more than 3 x the highest + 30 "
                  f"pictures with differences FAILs)")
        else:
            print(f"reference: BASE alone (a class's pictures above BASE's + {SLACK}, or more than 3 x BASE's + 30 "
                  f"pictures with differences FAILs)")
        bad = judged = 0
        for k in sorted(new):
            r = new[k]
            if k not in base:
                print(f"{k:16s} (no baseline window)")
                continue
            b = base[k]
            cs = [(n, c.get(k)) for n, c in ctls]
            ir, ib = incomplete(r), incomplete(b)
            if not ir and not ib and (r.get('wanted') or r['records']) != (b.get('wanted') or b['records']):
                ir = f"{r.get('wanted') or r['records']} records, the baseline's {b.get('wanted') or b['records']}"
            ic = [f"control {n}: {'no window' if c is None else incomplete(c)}" for n, c in cs
                  if c is None or incomplete(c)]
            if ir or ib or ic:
                print(f"{k:16s} FAIL: {'new: ' + ir if ir else ('base: ' + ib if ib else '; '.join(ic))}")
                bad += 1
                continue
            judged += 1
            refs = [b] + [c for _, c in cs]
            # (the same window on the other machines: a class a timing shift shows on one VDP it may
            #  show on another, l1c860's hostage tears on the FS-A1FX at BASE, on the MSX2 with ct3)
            stem = k.rsplit('_', 1)[0]
            sib = [x for kk, x in list(base.items()) + [kk2 for _, c in ctls for kk2 in c.items()]
                   if kk.rsplit('_', 1)[0] == stem and kk != k]
            over, warn = [], []
            for c, v in sorted(r['classes'].items()):
                vals = [x['classes'].get(c, 0) for x in refs]
                lo, hi, sp = ref.span(vals)
                thr = max(hi + max(sp, SLACK), max([x['classes'].get(c, 0) for x in sib], default=0))
                if v > thr:
                    over.append(f"{c} {v} (reference {'/'.join(map(str, vals))}, FAIL above {thr})")
                elif v > hi:
                    warn.append(f"{c} {v} (reference {'/'.join(map(str, vals))}, FAIL above {thr})")
            nb = max(x.get('pictures_nonhold', 0) for x in refs)
            nn = r.get('pictures_nonhold', 0)
            gross = nn > 3 * nb + 30
            rc = '; '.join(f"{n}: {fmt('', c).split('; classes: ')[1]}" for n, c in cs)
            line = (f"{k:16s} base: {fmt('', b).split('; classes: ')[1]} | new: {fmt('', r).split('; classes: ')[1]}"
                    f"{' | ' + rc if rc else ''}")
            if over or gross:
                bad += 1
                why = list(over)
                if gross:
                    why.append(f"{nn} pictures with differences against the reference set's highest {nb}, "
                               f"FB_HOLD's left out")
                line += f"  FAIL ({'; '.join(why)})"
            elif warn:
                line += f"  WARN ({'; '.join(warn)})"
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
