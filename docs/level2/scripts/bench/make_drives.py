#!/usr/bin/env python3
"""Writes level 2's drives (tools/drivejoy.py files) into DIR/ref: end, tour, lift, trolley, vat, cont, over, fuzz.
usage: make_drives.py BENCHDIR"""
import subprocess, sys
from pathlib import Path
B = Path(sys.argv[1])
DJ = [sys.executable, "-I", str(B / "tools" / "drivejoy.py")]


def dj(name, joy="", tele="", god=False, poke="", extra=()):
    cmd = DJ + ["--joy", joy, "--tele", tele, "--poke", poke] + (["--god"] if god else []) + list(extra) \
        + [str(B / "ref" / f"l2_{name}.drive")]
    print(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip())


fire_r = lambda a, b: ",".join(f"{f}:2:rf" for f in range(a, b, 4))
energy = lambda n: ",".join(f"{f}:0x169A:256:2" for f in range(25, n, 25))
# the level's end: onto the roof, fire right; Cain arrested at 164, the level ends at row 258
dj("end", joy=fire_r(40, 400), tele="20:200:100")
# the play-through: no teleport up to vat 3 (L1, trolleys 0-3, the two type-0 blockers shot), then L2, L4, the roof
S = ("40:95:r,150:110:u,265:88:r,482:12:u,564:30:ur," + fire_r(615, 642) + ",644:60:r,722:12:u,780:30:ur,"
     "830:18:r,943:12:u,1016:30:ur," + fire_r(1060, 1120) + ",1122:34:r,1242:12:u,1348:30:ur,1610:200:u,1920:150:u,"
     + ",".join(f"{f}:2:l{'f' if f % 8 == 0 else ''}" for f in range(2080, 2400, 2)) + "," + fire_r(2440, 2800))
dj("tour", joy=S, tele="1598:2566:784,1910:2567:384,2410:200:100",
   poke=",".join(f"{f}:0x169A:256:2,{f}:0x8034:2:2" for f in range(25, 3000, 25)))
# the lifts: L0 (2 stops), then L1 (3 stops), up and down
dj("lift", joy="100:150:u,260:150:d,440:130:u,600:200:d", tele="70:200:784,420:566:784", poke=energy(900))
# trolley 0 over vat 0 from the start, no teleport
dj("trolley", joy="40:95:r,150:110:u,265:88:r,482:12:u,564:30:ur", poke=energy(900))
# a vat's death, then a death by the enemies
dj("vat", tele="30:936:600")
# the game over with (cont) and without (over) a continue: the carry decides; fire held at the death's end
dj("cont", tele="30:936:600", joy="100:20:f")
dj("over", tele="30:936:600", joy="100:20:f")
# random keys from the start
dj("fuzz", god=True, extra=("--fuzz", "2", "--frames", "2500"))
