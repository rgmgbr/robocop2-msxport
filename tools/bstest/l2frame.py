#!/usr/bin/env python3
"""l2frame.py SNAPDIR LEVEL_PREFIX HUD_PREFIX OUT.png [SPRITE_PAL]: tools/msxframe.py on a level-2 snapshot
(hz.tcl hz_l2_still_jobs) while level 2's sprites are level 1's data (docs/LEVEL2.md 3.12, until its step
12 converts level 2's frames against palette C): msxframe converts every sprite frame again with the
palette it is given, and under palette C (entries 9, 11 and 13 changed) it picks other OR rows than the
ROM holds, so 30-40 of RoboCop's pixels a picture would count as wrong where the screen shows exactly
the ROM's data. Here the sprites' expected pixels come from the palette they were converted with
(SPRITE_PAL, default build/msx/level1.pal: their colour indices), while the render and the comparison
use LEVEL_PREFIX's palette as msxframe does (docs/HARNESS.md 5.22). Needs numpy (the venv's Python).

usage: $PY -I tools/bstest/l2frame.py W/O/still/m2/g0050 build/msx/level2 build/msx/hud OUT.png
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import msxframe  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) not in (4, 5):
        print(__doc__, file=sys.stderr)
        return 2
    pal = Path(argv[4] if len(argv) == 5 else ROOT / "build" / "msx" / "level1.pal").read_bytes()
    expected = msxframe.expected_sprites
    msxframe.expected_sprites = lambda objs, joint_pal: expected(objs, pal)
    sys.argv = ["msxframe.py"] + argv[:4]
    return msxframe.main()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
