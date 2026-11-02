"""The cadence's options for the user's choice (performance campaign 2, docs/PERF2_PLAN.md D2 and D3; nothing
decided: every build without them is byte-identical): tools/mkrom.py CAD_ADAPT (D2's loop-3: a picture that took
fewer than CAD_ADAPT VBLANKs runs at most 2 game ticks, a slower one up to CAD_MAX or CAD_HOLD) and LAG_X (D3:
how far the V9938 engine's view may lag behind the camera in x before the ticks are held). Their values and
refusals, where their code is (msx/player.asm only), and their rules as the code makes them: the cap cadence
takes for each VBLANK count, and the lags at which cam_lag holds the ticks with each scroll engine."""
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


def equ(lines, name):
    return int(next(l for l in lines if l.startswith(name + ":")).split("equ")[1])


def cap(wf_n, d, adapt):
    """CAD_ADAPT's block at cd_cap, as player.asm has it: the tick cap D after it for WF_N VBLANKs."""
    pl = code("player.asm")
    assert block(pl, pl.index("cd_cap:"), "CAD_ADAPT") == \
        ["ld a,(wf_n)", "cp CAD_ADAPT", "jr nc,cd_ca", "ld a,d", "cp 3", "jr c,cd_ca", "ld d,2", "cd_ca:"]
    if not adapt or wf_n >= adapt:
        return d
    return 2 if d >= 3 else d


def held(lag, lag_x, eng):
    """cam_lag's x test as player.asm has it: True when a lag of LAG pixels in x holds the ticks (NC), with
    the V9938 engine's two pages (eng 1) or the V9958's ring (fb_eng 0)."""
    pl = code("player.asm")
    i = pl.index("cam_lag:")
    lag_max = equ(pl, "LAG_MAX")
    assert pl[i + 1:i + 4] == ["ld hl,(v_x)", "ld de,(cam_x)", "call cl_abs"], pl[i + 1:i + 4]
    assert block(pl, i, "LAG_X != LAG_MAX") == \
        ["jr c,cl_y", "ld a,(fb_eng)", "or a", "ret z", "ld de,LAG_X - LAG_MAX", "sbc hl,de"]
    assert pl[pl.index("endif", i) + 1:pl.index("endif", i) + 3] == ["ret nc", "cl_y:   ld hl,(v_y)"]
    if lag < lag_max:                           # cl_abs: C, HL = lag - LAG_MAX
        return False
    if lag_x == lag_max or eng == 0:            # (the default's code: ret nc; the ring: ret z)
        return True
    return lag - lag_max >= lag_x - lag_max     # sbc hl,LAG_X - LAG_MAX: NC when the lag reaches LAG_X


class CadenceOptionTests(unittest.TestCase):

    def test_the_options(self):
        self.assertEqual(mkrom.OPTIONS["CAD_ADAPT"][0], 0)
        self.assertEqual(mkrom.OPTIONS["LAG_X"][0], equ(code("player.asm"), "LAG_MAX"))
        with tempfile.TemporaryDirectory() as t:
            out = str(Path(t) / "x.rom")
            for opts in (["CAD_ADAPT=8"], ["CAD_ADAPT=256", "CAD_MAX=3"], ["CAD_ADAPT=-1", "CAD_MAX=3"],
                         ["LAG_X=31"], ["LAG_X=65"], ["LAG_X=0"]):
                self.assertEqual(mkrom.main(["mkrom.py", "build/msx/level1", out] + opts), 2, opts)

    def test_where_the_code_is(self):
        uses = [(f.name, l) for f in sorted((ROOT / "msx").glob("*.asm")) for l in code(f.name)
                if "CAD_ADAPT" in l or "LAG_X" in l]
        self.assertEqual(uses, [("player.asm", "if CAD_ADAPT"), ("player.asm", "cp CAD_ADAPT"),
                                ("player.asm", "if LAG_X != LAG_MAX"), ("player.asm", "ld de,LAG_X - LAG_MAX")])

    def test_loop_3_takes_3_ticks_only_for_slow_pictures(self):
        # loop-3 (CAD_ADAPT=8, CAD_MAX=3, CAD_HOLD=3): 2 ticks at most below 8 VBLANKs; no tick while the
        # view lags (D = 0) and the cap of 2 stay as they are
        self.assertEqual([cap(w, 3, 8) for w in range(1, 12)], [2] * 7 + [3] * 4)
        self.assertEqual([cap(w, 0, 8) for w in (1, 9)], [0, 0])
        self.assertEqual([cap(w, 2, 8) for w in (1, 9)], [2, 2])
        self.assertEqual([cap(w, 3, 0) for w in (1, 9)], [3, 3])       # loop-1: CAD_MAX 3 alone

    def test_lag_x_acts_with_the_v9938_engine_only(self):
        lag_max = equ(code("player.asm"), "LAG_MAX")
        for lag in range(0, 100):
            self.assertEqual(held(lag, 64, 1), lag >= 64, lag)
            self.assertEqual(held(lag, 64, 0), lag >= lag_max, lag)
            self.assertEqual(held(lag, lag_max, 1), lag >= lag_max, lag)
        # D = 0 when the ticks are held (cadence takes D as the cap): the high bytes of LAG_MAX, LAG_X - LAG_MAX
        self.assertLess(lag_max, 256)
        self.assertLess(64 - lag_max, 256)


if __name__ == "__main__":
    unittest.main()
