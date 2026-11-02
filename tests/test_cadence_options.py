"""The cadence's options (performance campaign 2, docs/PERF2_PLAN.md D2 and D3): tools/mkrom.py CAD_ADAPT (D2's
loop-3, CAD_MAX=3 CAD_HOLD=3 CAD_ADAPT=8, the product's cadence since the user's choice of 2026-11-02: a picture that
took fewer than CAD_ADAPT VBLANKs runs at most 2 game ticks, a slower one up to CAD_MAX or CAD_HOLD, and level 1 at
most 2 for every picture, the user's rule of 2026-10-21; CAD_MAX=2 CAD_HOLD=2 CAD_ADAPT=0 is the cadence until then)
and LAG_X (D3, not decided, default 32: how far the
V9938 engine's view may lag behind the camera in x before the ticks are held). Their values and refusals, the
product with them and with the look and cadence until 2026-11-02 (FLASH_LOOK=0, D1's, with the cadence above),
where their code is (msx/player.asm only), and their rules as the code makes them: the cap cadence takes for each
VBLANK count, and the lags at which cam_lag holds the ticks with each scroll engine."""
from __future__ import annotations

import contextlib
import io
import re
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


def cap(wf_n, d, adapt, level=3):
    """CAD_ADAPT's block at cd_cap, as player.asm has it: the tick cap D after it for WF_N VBLANKs in LEVEL (1-3:
    the level word's low byte, AG + 8050h, is LEVEL - 1)."""
    pl = code("player.asm")
    assert block(pl, pl.index("cd_cap:"), "CAD_ADAPT") == \
        ["ld a,(AG + 0x8050)", "or a", "jr z,cd_c2", "ld a,(wf_n)", "cp CAD_ADAPT", "jr nc,cd_ca",
         "cd_c2:  ld a,d", "cp 3", "jr c,cd_ca", "ld d,2", "cd_ca:"]
    if not adapt or (level != 1 and wf_n >= adapt):
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
        # loop-3 is the product's cadence (the user's choice of 2026-11-02); LAG_X keeps LAG_MAX
        self.assertEqual([mkrom.OPTIONS[k][0] for k in ("CAD_MAX", "CAD_HOLD", "CAD_ADAPT")], [3, 3, 8])
        self.assertEqual(mkrom.OPTIONS["LAG_X"][0], equ(code("player.asm"), "LAG_MAX"))
        with tempfile.TemporaryDirectory() as t:
            out = str(Path(t) / "x.rom")
            # CAD_ADAPT needs a cap above 2, the default's too: the cadence until 2026-11-02 names CAD_ADAPT=0
            for opts in (["CAD_ADAPT=8", "CAD_MAX=2", "CAD_HOLD=2"], ["CAD_MAX=2", "CAD_HOLD=2"],
                         ["CAD_ADAPT=256"], ["CAD_ADAPT=-1"], ["LAG_X=31"], ["LAG_X=65"], ["LAG_X=0"]):
                self.assertEqual(mkrom.main(["mkrom.py", "build/msx/level1", out] + opts), 2, opts)
        # the checks pass for the cadence and look until 2026-11-02, loop-1, and one cap of 2 with the other 3
        for opts in (["FLASH_LOOK=0", "CAD_MAX=2", "CAD_HOLD=2", "CAD_ADAPT=0"],
                     ["CAD_MAX=2", "CAD_HOLD=2", "CAD_ADAPT=0"], ["CAD_ADAPT=0"], ["CAD_MAX=2"], ["CAD_HOLD=2"]):
            with self.assertRaises(FileNotFoundError, msg=opts):      # (past the checks: the level's files)
                mkrom.main(["mkrom.py", "/nonexistent/level1", "/nonexistent/x.rom"] + opts)

    @unittest.skipUnless((ROOT / "build" / "msx" / "level1.map").exists()
                         and (ROOT / "build" / "msx" / (mkrom.POOL + ".bin")).exists(), "needs the conversions (make msx)")
    def test_the_product_and_the_look_and_cadence_until_2026_11_02(self):
        """The product (flash-7 and loop-3, the defaults) and the build with FLASH_LOOK=0 CAD_MAX=2 CAD_HOLD=2
        CAD_ADAPT=0 (the look and cadence until 2026-11-02, the product of before byte for byte) both build; they
        differ only in the fixed area (flash-7 22 bytes fewer, CAD_ADAPT's block 20 more: 14, and 6 for level 1's
        test) and LC1 (flash-7's slot_clear, 5 more), and the rc-edge table's RC_K is 3 against 2."""
        ends, rck = {}, {}
        with tempfile.TemporaryDirectory() as t:
            for name, opts in (("prod", []), ("old", ["FLASH_LOOK=0", "CAD_MAX=2", "CAD_HOLD=2", "CAD_ADAPT=0"])):
                out = Path(t) / name / "rc2.rom"
                out.parent.mkdir()
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(mkrom.main(["mkrom.py", str(ROOT / "build" / "msx" / "level1"), str(out)] + opts),
                                     0, name)
                lab = out.with_suffix(".labels").read_text()
                ends[name] = dict(re.findall(r"^(\w+_end):\s+equ \$([0-9a-f]+)$", lab, re.M))
                ends[name]["size"] = len(out.read_bytes())
                rck[name] = re.search(r"^RC_K: equ (\d+)", (out.parent / "gen" / "rcedge.inc").read_text(), re.M).group(1)
        a, b = ends["old"], ends["prod"]
        self.assertEqual(a["size"], b["size"])
        diff = {k: int(b[k], 16) - int(a[k], 16) for k in ("code_end", "lc1_end", "lc2_end", "l1_end", "lc3_end",
                                                         "input_end", "front_end", "field_end", "music_end",
                                                         "puzl_end", "frng_end", "l2_end")}
        self.assertEqual(diff, {"code_end": -2, "lc1_end": 5, "lc2_end": 0, "l1_end": 0, "lc3_end": 0,
                                "input_end": 0, "front_end": 0, "field_end": 0, "music_end": 0, "puzl_end": 0,
                                "frng_end": 0, "l2_end": 0})
        self.assertEqual((rck["old"], rck["prod"]), ("2", "3"))

    def test_where_the_code_is(self):
        uses = [(f.name, l) for f in sorted((ROOT / "msx").glob("*.asm")) for l in code(f.name)
                if "CAD_ADAPT" in l or "LAG_X" in l]
        self.assertEqual(uses, [("player.asm", "if CAD_ADAPT"), ("player.asm", "cp CAD_ADAPT"),
                                ("player.asm", "if LAG_X != LAG_MAX"), ("player.asm", "ld de,LAG_X - LAG_MAX")])

    def test_loop_3_takes_3_ticks_only_for_slow_pictures(self):
        # loop-3 (CAD_ADAPT=8, CAD_MAX=3, CAD_HOLD=3): 2 ticks at most below 8 VBLANKs; no tick while the
        # view lags (D = 0) and the cap of 2 stay as they are; level 1 keeps 2 for every picture
        self.assertEqual([cap(w, 3, 8) for w in range(1, 12)], [2] * 7 + [3] * 4)
        self.assertEqual([cap(w, 3, 8, 2) for w in range(1, 12)], [2] * 7 + [3] * 4)
        self.assertEqual([cap(w, 3, 8, 1) for w in range(1, 12)], [2] * 11)
        self.assertEqual([cap(w, d, 8, 1) for w in (1, 9) for d in (0, 2)], [0, 2, 0, 2])
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

    def test_cam38(self):
        # CAM38 (the MSX2's camera): 1 (lock) by default, the user's choice of 2026-11-02; 0 the old camera (its
        # code only under 'if CAM38' blocks), 2 (pace) an option, anything else refused
        self.assertEqual(mkrom.OPTIONS["CAM38"][0], 1)
        for name in ("player.asm", "scroll9938.asm", "ending.asm"):
            lines = code(name)
            for i, l in enumerate(lines):
                if any(k in l for k in ("s38_glide", "s38_pace", "cam_lock", "s38_lv", "s38_tb", "s38_lim")):
                    opened = [j for j in range(i) if lines[j].startswith("if CAM38")]
                    self.assertTrue(opened and "endif" not in lines[opened[-1] + 1:i], (name, l))
        with tempfile.TemporaryDirectory() as t:
            out = str(Path(t) / "x.rom")
            for opts in (["CAM38=3"], ["CAM38=-1"]):
                self.assertEqual(mkrom.main(["mkrom.py", "build/msx/level1", out] + opts), 2, opts)


if __name__ == "__main__":
    unittest.main()
