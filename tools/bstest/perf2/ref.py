#!/usr/bin/env python3
"""ref.py: the reference set the kit's verdicts judge a build against (performance campaign 2's kit,
docs/HARNESS.md section 12): BASE's records and those of its timing controls, and the gate drives'
teleports and ends. Imported by win.py, holds.py, guardsum.py and fieldsum.py; as a script it lists a
base folder's reference set.

  ref.py BASE        each gate folder of BASE (speed, field, guard, lock, map) and its controls

A timing control is a build of BASE that differs from it only in timing: a few T-states more where no
decision is made (docs/HARNESS.md 12.2: 4 NOPs a game tick, 8 a picture, 3 a budget run). Its records
show what a pure timing shift does to the counts the gates judge (FB_HOLD pictures, tears, the field
check's classes, the speed of a window): they scatter, because the game's pictures follow its timing.
A gate folder's controls are its subfolders ctl/<name>/, in the gate folder's own layout
(BASE/speed/ctl/ct1/kill_m2_ticks.txt, BASE/field/ctl/ct1/kill300_m2/ ...). A verdict judges NEW
against the range BASE and its controls span (docs/HARNESS.md 12.2); with no controls, against BASE
alone as before.

The drives (gates.tcl ::pf_drives): each run's drive file in build/emu, its teleports (the file's second
line, "tick:x:y ..."): the test drive pokes RoboCop's place and the camera at those game frames, and the
engines walk to the new view while the cadence holds the ticks (msx/player.asm cadence's lag rule), a
stall the game itself never has (its own relocation, mapobj.asm act_10, draws the view at once:
engines_jump). The verdicts leave each teleport's ticks out (TELE_TICKS from the teleport's game frame;
the field check TELE_FIELD), and the field records past the drive's end (ROWS: kill's 1861 ends with
the level's end screen, which tools/bstest/fieldcheck.py does not model).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# gates.tcl ::pf_drives: drive name -> (drive file, rows the gates drive)
DRIVES = {
    'kill': ('l3_kill.drive', 1861),
    'boss': ('l3_boss.drive', 1401),
    'tour3': ('l3_tour3.drive', 1401),
    'park': ('l3_park.drive', 1201),
    'l2tour': ('l2_tour.drive', 2654),
    'l1play': ('drive_play.txt', 1451),
}
TELE_TICKS = 2          # a teleport's stall: the tick intervals from its game frame T to T + 2 (the
                        # stall lands in the first or the second: m3's tick_n against the game frame)
TELE_FIELD = 60         # the field check: records of game frames T .. T + 59 (BASE's stale beam cells
                        # after tour3's teleport at 540 last to 574; play draws a relocation at once)


def controls(d):
    """the timing controls' folders of gate folder d (d/ctl/<name>/), sorted by name"""
    c = Path(d) / 'ctl'
    if not c.is_dir():
        return []
    return [p for p in sorted(c.iterdir()) if p.is_dir()]


def drive_file(drive, emu=None):
    """the drive file of a drive name, or None"""
    if drive not in DRIVES:
        return None
    return Path(emu or (ROOT / 'build' / 'emu')) / DRIVES[drive][0]


def teleports(drive, emu=None, strict=False):
    """the game frames of a drive's teleports (its file's second line); [] for a drive without any. A drive
    file that is not there: [] (strict: an error, the gate's own call: gate.sh passes --emu)"""
    p = drive_file(drive, emu)
    if p is None:
        return []
    if not p.exists():
        if strict:
            raise SystemExit(f"ref.py: no drive file {p} (--emu: the checkout's build/emu)")
        return []
    with open(p) as f:
        f.readline()
        line = f.readline()
    out = []
    for t in line.split():
        try:
            out.append(int(t.split(':')[0]))
        except ValueError:
            pass
    return sorted(out)


def skip_ticks(teles, n=TELE_TICKS):
    """the ticks whose interval to the next tick is left out: T .. T + n - 1 for each teleport T"""
    return {t + k for t in teles for k in range(n)}


def emu_arg(argv):
    """-> (argv without --emu DIR, DIR or None)"""
    if '--emu' in argv:
        i = argv.index('--emu')
        return argv[:i] + argv[i + 2:], argv[i + 1]
    return argv, None


def span(values):
    """(lowest, highest, highest - lowest) of a reference set's values"""
    return min(values), max(values), max(values) - min(values)


def main(argv):
    if len(argv) != 1:
        print(__doc__)
        return 2
    for g in ('speed', 'field', 'guard', 'lock', 'map'):
        d = Path(argv[0]) / g
        if d.is_dir():
            print(f"{g}: {d}; controls: {', '.join(p.name for p in controls(d)) or 'none'}")
    for name in DRIVES:
        print(f"{name}: {DRIVES[name][0]}, {DRIVES[name][1]} rows, teleports {teleports(name) or '-'}")
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
