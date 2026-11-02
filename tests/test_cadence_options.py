"""The cadence's options for the user's choice (performance campaign 2, docs/PERF2_PLAN.md D2; nothing decided:
every build without them is byte-identical): tools/mkrom.py CAD_ADAPT (D2's loop-3: a picture that took fewer
than CAD_ADAPT VBLANKs runs at most 2 game ticks, a slower one up to CAD_MAX or CAD_HOLD). Its values and
refusals, where its code is (msx/player.asm only), and its rule as the code makes it: the cap cadence takes for
each VBLANK count."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mkrom  # noqa: E402


def code(name):
    """msx/NAME's lines without comments, stripped."""
    return [l.split(";")[0].strip() for l in (ROOT / "msx" / name).read_text().splitlines()]


def block(lines, start, cond):
    """The lines of the if block that starts at the first 'if COND' at or after START (no else, no nesting)."""
    i = lines.index(f"if {cond}", start)
    j = lines.index("endif", i)
    return [l for l in lines[i + 1:j] if l]


def cap(wf_n, d, adapt):
    """CAD_ADAPT's block at cd_cap, as player.asm has it: the tick cap D after it for WF_N VBLANKs."""
    pl = code("player.asm")
    assert block(pl, pl.index("cd_cap:"), "CAD_ADAPT") == \
        ["ld a,(wf_n)", "cp CAD_ADAPT", "jr nc,cd_ca", "ld a,d", "cp 3", "jr c,cd_ca", "ld d,2", "cd_ca:"]
    if not adapt or wf_n >= adapt:
        return d
    return 2 if d >= 3 else d


class CadenceOptionTests(unittest.TestCase):

    def test_the_options(self):
        self.assertEqual(mkrom.OPTIONS["CAD_ADAPT"][0], 0)
        with tempfile.TemporaryDirectory() as t:
            out = str(Path(t) / "x.rom")
            for opts in (["CAD_ADAPT=8"], ["CAD_ADAPT=256", "CAD_MAX=3"], ["CAD_ADAPT=-1", "CAD_MAX=3"]):
                self.assertEqual(mkrom.main(["mkrom.py", "build/msx/level1", out] + opts), 2, opts)

    def test_where_the_code_is(self):
        uses = [(f.name, l) for f in sorted((ROOT / "msx").glob("*.asm")) for l in code(f.name)
                if "CAD_ADAPT" in l]
        self.assertEqual(uses, [("player.asm", "if CAD_ADAPT"), ("player.asm", "cp CAD_ADAPT")])

    def test_loop_3_takes_3_ticks_only_for_slow_pictures(self):
        # loop-3 (CAD_ADAPT=8, CAD_MAX=3, CAD_HOLD=3): 2 ticks at most below 8 VBLANKs; no tick while the
        # view lags (D = 0) and the cap of 2 stay as they are
        self.assertEqual([cap(w, 3, 8) for w in range(1, 12)], [2] * 7 + [3] * 4)
        self.assertEqual([cap(w, 0, 8) for w in (1, 9)], [0, 0])
        self.assertEqual([cap(w, 2, 8) for w in (1, 9)], [2, 2])
        self.assertEqual([cap(w, 3, 0) for w in (1, 9)], [3, 3])       # loop-1: CAD_MAX 3 alone


if __name__ == "__main__":
    unittest.main()
