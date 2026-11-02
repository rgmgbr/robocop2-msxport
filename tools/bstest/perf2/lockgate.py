#!/usr/bin/env python3
"""lockgate.py BASE NEW [--partial]: G-LOCK, the LOCKSTEP display records of two builds (performance
campaign 2's kit, docs/HARNESS.md section 12; docs/PERF2_PLAN.md 5.4): every record BASE holds (gates.tcl
pf_lock_jobs: DIR/<run>_<tag>.txt with its .over) compared with NEW's by tools/dispcmp.py's rules (per list,
the SAT, each shown entry's colour row and pattern, what the list records as shown). A record NEW lacks
FAILs (--partial: listed, not judged).

The displayed cameras (each list's last two fields). The V9938's scroll engine moves the displayed camera
in its idle time, which LOCKSTEP does not pin: a build whose CPU side takes another time can show a list
with the camera one step behind or ahead (W2S's and W2C's kill_m2 against BASE: game frames 300 and 304,
cam_x 1423 against 1428). tools/dispcmp.py stops at the first such list, which left 746 of kill_m2's 896
lists unjudged; since batch 3 (docs/HARNESS.md 12.3) every list whose displayed cameras agree is compared
(lane W2S's dispcam.py), and the lists whose cameras differ are counted apart, not compared. FAIL too when
the cameras differ in more than CAM_MAX % of the common lists, or still differ at the last common list (a
camera that never comes back: a shifted view would otherwise leave every list unjudged).

Under LOCKSTEP=K a frame of two ticks starts every K VBLANKs whatever the CPU time; a frame that takes
longer starts late (its .over file: "late N at GAME_FRAMES") and the record is exact only before it. The
lists from the first late frame of either run on are compared and reported but not judged (HEAD's level-3
records on the MSX2 at K = 24 had one: boss at game frame 225, kill at 990; level 3's lock build is K = 48
since batch 2, gate.sh builds, docs/HARNESS.md 12.2: BASE's and its timing controls' records complete).
FAIL when a judged list differs, or when NEW has fewer lists. Exit 0 only when nothing FAILs.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import dispcmp  # noqa: E402  (tools/dispcmp.py)

CAM_MAX = 5.0           # % of the common lists whose displayed cameras may differ (each left uncompared)


def late(path):
    """the game frames of the late frames (the .over file beside the record), or []"""
    p = Path(str(path)[:-4] + '.over')
    if not p.exists():
        return []
    f = p.read_text().split()
    if len(f) >= 3 and f[0] == 'late':
        return [int(x) for x in f[3:] if x.isdigit()]
    return []


def compare(pa, pb):
    A, B = dispcmp.load(Path(pa)), dispcmp.load(Path(pb))
    cut = min(late(pa) + late(pb), default=None)
    common = sorted(set(A) & set(B))
    judged = differ = after = 0
    cams = []
    first = None
    for gf in common:
        if A[gf][8:] != B[gf][8:]:
            cams.append(gf)
            continue
        x, y = dispcmp.shown(A[gf]), dispcmp.shown(B[gf])
        same = x == y
        if cut is not None and gf >= cut:
            after += not same
            continue
        judged += 1
        if not same:
            differ += 1
            if first is None:
                first = gf
    cam_bad = None
    if cams and common and cams[-1] == common[-1]:
        k = len(cams) - 1                       # (the stretch that reaches the end)
        while k > 0 and common.index(cams[k - 1]) == common.index(cams[k]) - 1:
            k -= 1
        cam_bad = f"the displayed cameras differ from game frame {cams[k]} to the last list"
    elif common and 100.0 * len(cams) / len(common) > CAM_MAX:
        cam_bad = f"the displayed cameras differ in {len(cams)} of {len(common)} lists (more than {CAM_MAX:g} %)"
    return {'lists_a': len(A), 'lists_b': len(B), 'judged': judged, 'differ': differ, 'first': first,
            'late_from': cut, 'after_late_differ': after, 'cams': cams, 'cam_bad': cam_bad}


def main(argv):
    partial = '--partial' in argv
    argv = [a for a in argv if a != '--partial']
    if len(argv) != 2:
        print(__doc__)
        return 2
    base, new = argv
    bad = 0
    names = sorted(f for f in os.listdir(new) if f.endswith('.txt') and f != 'disp_drive.txt')
    for fn in sorted(f for f in os.listdir(base) if f.endswith('.txt') and f != 'disp_drive.txt'):
        if fn not in names:
            if partial:
                print(f"{fn}: no new record (not judged, --partial)")
            else:
                print(f"{fn}: FAIL: no new record (--partial judges a subset)")
                bad += 1
    judged = 0
    for fn in names:
        pb = os.path.join(base, fn)
        if not os.path.exists(pb):
            print(f"{fn}: no baseline")
            continue
        judged += 1
        r = compare(pb, os.path.join(new, fn))
        fail = r['differ'] > 0 or r['lists_b'] < r['lists_a'] or r['cam_bad'] is not None
        bad += fail
        s = f"{fn}: {r['judged']} lists judged ({r['lists_a']} / {r['lists_b']}), {r['differ']} differ"
        if r['first'] is not None:
            s += f" (first at game frame {r['first']})"
        if r['late_from'] is not None:
            s += f"; a late frame at game frame {r['late_from']}: {r['after_late_differ']} lists after it differ (not judged)"
        if r['cams']:
            g = ', '.join(map(str, r['cams'][:8])) + (' ...' if len(r['cams']) > 8 else '')
            s += f"; {len(r['cams'])} lists with other displayed cameras, not compared (game frames {g})"
        if r['cam_bad']:
            s += f"; {r['cam_bad']}"
        print(s + ('  FAIL' if fail else ''))
    if not judged:
        print("no record judged")
    ok = judged and not bad
    print(f"G-LOCK: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
