#!/usr/bin/env python3
"""Level 3's bench drives and their references (docs/LEVEL3.md 3.8 and 4; tools/amigaemu.py game --level 3).

A drive is a tools/drivejoy.py file (the joystick byte of every game frame, the teleports, god mode,
the pokes): the same input for the bench (amigaemu.py --drive) and for openMSX (tools/openmsx_rc2.tcl
rc2_drive_rom on an LV_TEST=3 build). Its reference is the bench's trace of it (--trace-ram, one JSON
line a game frame) from level 3's direct start (Level3Bench: $8050 = $8052 = 2, level_init's entry [2])
with the reference's carry (amigaemu.py --carry). The MSX trace of a job is compared with
tools/tracecmp.py --ram --fields analysis/amiga_ram_l3.tsv (tools/bstest/hz.sh compare --fields ...).

While level 3's types are stubs in the port (msx/level3obj.asm: the plan's step A), a trace differs
from a plain reference from the first frame a stubbed routine runs; tools/bstest/l3stub.py makes the
references again with those routines stubbed on the bench the way the port stubs them, so that
everything the port has compares whole (docs/HARNESS.md 5.26).

The drives (tour3, beam and cont3 built at step A; park, boss and kill at step B, docs/level3/HANDOFF.md
step 6; energy and lives poked every 25 frames in all but beam and cont3, no god mode):
  tour3   the building: the street from the start, the beams of floors 25 and 20 walked through, the three
          lifts ridden up and down, the roof's edge; by teleports between the stretches
  beam    standing in the beam at (416, 336) (floor y 400) from frame 30: its 0Ch a frame for 32 frames
          of 64, until the death (no poke), then the restart at the start
  park    the street from x 1000 leftwards firing (the trucks, type 33, and type 21 shot: their deaths'
          debris), floor 35 under the turrets from x 600 (type 41's and 40's rockets, both shot at),
          then the car park's ground floor from x 1700 right and back firing (its markers, crates,
          waiting bombs and missiles, act_20's pieces)
  boss    the roof's left end (type 47: camera mode 1, type 48: Cain's bursts), the roof from x 900
          rightwards firing: Cain (type 22) comes, runs ahead, falls into the car park; floor 20 to its
          end (act_20's piece opens: both fall), floor 30 leftwards in mode 2 (the bombs and missiles
          from his mailbox, shot at) to its end (the second piece opens), floor 40 rightwards (mode 1)
          until Cain falls onto the ground floor (the third piece)
  kill    boss's route without fire, then RoboCop drops to the ground floor (mode 2: Cain stands left of
          him, low: hurt) and fires left until Cain dies (CAIN DESTROYED., the end count, the level's
          end at about frame 1860)
  cont3   the game over with a continue (carry 0:0:1:good): the beam's death with no life left, fire
          held at the death's end; the offer taken, level 3 again (the drive only: no reference yet)

Files (DIR = build/emu by default; not committed: they hold the game's state):
  DIR/l3_DRIVE.drive (+ .args)     the drives (make)
  DIR/l3_REF_ram.jsonl (+ .log)    the references (refs)

usage: l3drives.py list                                   the references: drive, carry, rows, sha256
       l3drives.py make [--out DIR] [DRIVE ...]           writes the drives (stdlib: drivejoy.py)
       l3drives.py refs [--out DIR] [--jobs N] [REF ...]  makes the references (runs amigaemu.py with
                                                          --python, Unicorn's), then checks them
       l3drives.py check [--out DIR] [REF ...]            rows and sha256 prefixes against the table
       l3drives.py path REF [--out DIR] [--every N]       RoboCop's place, state, energy and the enemy
                                                          slots' types every N rows of a reference
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
EMU = ROOT / "build" / "emu"
CARRY = "10050:2:0:good"              # level 2's flows carry this (amigaemu.py CARRY_L3)


def energy_lives(n: int, step: int = 25) -> str:
    """The energy target ($169A) and the lives ($8034 = 2) poked every 'step' frames up to n."""
    return ",".join(f"{f}:0x169A:256:2,{f}:0x8034:2:2" for f in range(step, n, step))


# tour3's route (game coordinates: a map cell's x is (column + 8) x 16; RoboCop's y on a floor is its
# row x 16: floors at rows 20, 25, 30, 35, 40 and 49; the beams' records at x 416, 480, 544 on floor
# 25 (y 400) and 928, 992, 1056 on floor 20 (y 320); the lifts L0 (319: y 404-484), L1 (1215: 324-404),
# L2 (1215: 484-564))
TOUR3_JOY = ("40:150:l,"                   # the street from the start (x 1184) left, type 4's markers
             "215:120:r,"                  # floor 25 (y 400) from x 392: the beams at 416, 480 and 544
             "345:30:r,"                   # floor 35 (y 560) from x 392: the beam at 416 (its top 496)
             "385:150:r,"                  # floor 20 (y 320) from x 860: the beams at 928, 992 and 1056
             "545:60:u,625:60:d,"          # L0 (x 319, at rest at its bottom 484) up and down
             "725:60:u,805:60:d,"          # L1 (x 1215, 404) up and down
             "905:60:u,985:60:d,"          # L2 (x 1215, 564) up and down
             "1085:120:r,1225:120:l")      # the roof (y 112) to the right, off its edge, and back
TOUR3_TELE = "210:392:400,340:392:560,380:860:320,540:319:484,720:1215:404,900:1215:564,1080:1180:112"



def walk_fire(keys: str, first: int, end: int) -> str:
    """Two-frame joystick entries from 'first' to 'end' with 'keys' (a direction or none), fire added on
    every other entry (a shot every 4 frames)."""
    return ",".join(f"{f}:2:{keys + 'f' if (f // 2) % 2 == 0 else keys}" for f in range(first, end, 2)
                    if keys or (f // 2) % 2 == 0)


# park: the street (the trucks), floor 35 under the turrets 41 (576) and 40 (832), the car park's ground
PARK_JOY = ",".join((walk_fire("l", 40, 240), walk_fire("r", 260, 300), walk_fire("", 300, 600),
                     walk_fire("r", 610, 900), walk_fire("l", 900, 1100)))
PARK_TELE = "30:1000:784,250:600:560,600:1700:784"
# boss and kill: the roof's left end (300, 112) for type 47's mode 1, the roof from (900, 112); right on the
# roof and floor 20 to its end (frames 50-659), left on floor 30 (660-989), right on floor 40 (1060-1379)
BOSS_TELE = "30:300:112,45:900:112"
BOSS_JOY = ",".join((walk_fire("r", 50, 660), walk_fire("l", 660, 990), walk_fire("r", 1060, 1380)))
KILL_JOY = "50:610:r,660:330:l,1060:320:r,1480:14:r,1530:2:l," + walk_fire("", 1560, 2600)

DRIVES = {
    "tour3": dict(joy=TOUR3_JOY, tele=TOUR3_TELE, poke=energy_lives(1400)),
    "beam": dict(tele="30:420:400"),
    "park": dict(joy=PARK_JOY, tele=PARK_TELE, poke=energy_lives(1200)),
    "boss": dict(joy=BOSS_JOY, tele=BOSS_TELE, poke=energy_lives(1400)),
    "kill": dict(joy=KILL_JOY, tele=BOSS_TELE, poke=energy_lives(2600)),
    "cont3": dict(tele="30:420:400", joy="200:20:f"),
}

# The references: name -> (drive, carry, game frames asked, rows, sha256 prefix, what it covers). The
# bench stops at the level's end or at a game over without a continue (--stop-at-end).
REFS = {
    "tour3": ("tour3", CARRY, 1400, 1401, "27fc3e0241c53f5a", "the street, the beams of floors 25, 35 and 20, the "
              "three lifts, the roof"),
    "beam": ("beam", CARRY, 500, 501, "9c293cd6431fb211", "a beam's death at 100 and the restart"),
    "park": ("park", CARRY, 1200, 1201, "6614e02d98a2f6b5", "the trucks and type 21 shot, the turrets 41 and 40, the car park's "
             "ground floor"),
    "boss": ("boss", CARRY, 1400, 1401, "6454a63800dea384", "Cain's chase from the roof down to the ground floor, shot at high up"),
    "kill": ("kill", CARRY, 2600, 1861, "83ff8fd40281d2af", "Cain followed down and killed: the level's end"),
}
# (cont3's drive is made, its reference not yet: the bench faults after its game over, PC $FDB8 at bench
# frame 735 (A1 = 800000h), the continue's text or the high-score entry on level 3's RAM image; the
# plan's step D, contcheck.py --level 3)


def python() -> str:
    """The interpreter with Unicorn: $PY, else the project's venv, else this one."""
    venv = Path.home() / ".venvs" / "msxports" / "bin" / "python"
    return os.environ.get("PY") or (str(venv) if venv.exists() else sys.executable)


def drive_cmd(name: str, out: Path) -> list[str]:
    d = DRIVES[name]
    cmd = [sys.executable, "-I", str(TOOLS / "drivejoy.py"), "--joy", d.get("joy", ""), "--tele", d.get("tele", ""),
           "--poke", d.get("poke", "")]
    return cmd + (["--god"] if d.get("god") else []) + list(d.get("extra", ())) + [str(out / f"l3_{name}.drive")]


def make(out: Path, names: list[str]) -> int:
    out.mkdir(parents=True, exist_ok=True)
    for name in names or DRIVES:
        r = subprocess.run(drive_cmd(name, out), capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        if r.returncode:
            return r.returncode
    return 0


def ref_cmd(name: str, out: Path, py: str, emu: Path | None = None) -> list[str]:
    """The bench's command line for a reference (run from the repository's root); emu: the drives'
    folder (default out)."""
    drive, carry, gframes, *_ = REFS[name]
    return [py, "-I", "tools/amigaemu.py", "game", "--level", "3", "--carry", carry, "--gframes", str(gframes),
            "--drive", str((emu or out) / f"l3_{drive}.drive"), "--stop-at-end",
            "--trace", str(out / f"l3_{name}_ram.jsonl"), "--trace-ram"]


def run_refs(out: Path, names: list[str], jobs: int, py: str, extra: list[str] = (), emu: Path | None = None) -> int:
    """Runs the bench for the references (extra: more amigaemu.py arguments, l3stub.py's --pre-poke)."""
    running: list[tuple[str, subprocess.Popen, object]] = []
    todo, failed = list(names), 0
    out.mkdir(parents=True, exist_ok=True)
    while todo or running:
        while todo and len(running) < jobs:
            name = todo.pop(0)
            cmd = ref_cmd(name, out, py, emu) + list(extra)
            print(" ".join(c if " " not in c else repr(c) for c in cmd[:14]) + (" ..." if extra else ""), flush=True)
            log = (out / f"l3_{name}.log").open("w")
            running.append((name, subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT), log))
        name, p, log = running.pop(0)
        p.wait()
        log.close()
        if p.returncode:
            failed += 1
            print(f"{name}: the bench failed (exit {p.returncode}): see {out / f'l3_{name}.log'}")
    return failed


def refs(out: Path, names: list[str], jobs: int, py: str) -> int:
    names = names or list(REFS)
    need = sorted({REFS[n][0] for n in names} - {p.stem[3:] for p in out.glob("l3_*.drive")})
    if need and make(out, need):
        return 1
    if run_refs(out, names, jobs, py):
        return 1
    return check(out, names)


def check(out: Path, names: list[str]) -> int:
    bad = 0
    for name in names or REFS:
        _drive, _carry, _g, rows, sha, _what = REFS[name]
        p = out / f"l3_{name}_ram.jsonl"
        if not p.exists():
            print(f"{name}: {p} missing")
            bad += 1
            continue
        data = p.read_bytes()
        n, h = data.count(b"\n"), hashlib.sha256(data).hexdigest()[:16]
        ok = n == rows and (not sha or h == sha)
        bad += not ok
        print(f"{name}: {n} rows (expected {rows}), sha256 {h} (expected {sha or '-'}): {'ok' if ok else 'FAIL'}")
    total = len(names or REFS)
    print(f"references: {total - bad} of {total} as expected")
    return 1 if bad else 0


def show_list() -> int:
    for name, (drive, carry, gframes, rows, sha, what) in REFS.items():
        print(f"{name:8} l3_{drive}.drive  carry {carry:16} --gframes {gframes:5}  {rows:5} rows  {sha or '-':16}  {what}")
    return 0


def path(name: str, out: Path, every: int) -> int:
    """RoboCop's place every 'every' rows of a reference (and its last), the enemy slots' types."""
    p = out / f"l3_{name}_ram.jsonl"
    rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    for r in rows:
        if r["game_frame"] % every and r is not rows[-1]:
            continue
        ram = r["ram"]
        types = [int(ram[(0xC04 + 4 * k - 0xB00) * 2:(0xC04 + 4 * k - 0xB00) * 2 + 2], 16) for k in range(5)]
        print(f"{r['game_frame']:5d}  ({r['player_x']:5d}, {r['player_y']:4d})  state {r['state']:2d}  camera "
              f"({r['camera_x']}, {r['camera_y']})  energy {r['energy']:4d}  slots {types}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("list", "make", "refs", "check", "path"))
    ap.add_argument("names", nargs="*", help="drives (make) or references (refs, check, path); all by default")
    ap.add_argument("--out", type=Path, default=EMU, help="the drives' and references' folder (build/emu)")
    ap.add_argument("--jobs", type=int, default=4, help="refs: bench runs at a time")
    ap.add_argument("--python", default=python(), help="refs: the interpreter with Unicorn ($PY)")
    ap.add_argument("--every", type=int, default=50, help="path: every N rows")
    a = ap.parse_args()
    out = a.out.resolve()
    unknown = [n for n in a.names if n not in (DRIVES if a.cmd == "make" else REFS)]
    if unknown:
        ap.error(f"unknown: {' '.join(unknown)}")
    if a.cmd == "list":
        return show_list()
    if a.cmd == "make":
        return make(out, a.names)
    if a.cmd == "refs":
        return refs(out, a.names, max(1, a.jobs), a.python)
    if a.cmd == "check":
        return check(out, a.names)
    if len(a.names) != 1:
        ap.error("path: one reference")
    return path(a.names[0], out, a.every)


if __name__ == "__main__":
    raise SystemExit(main())
