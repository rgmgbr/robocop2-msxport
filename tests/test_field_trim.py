"""The play-field frames cut to their opaque box (performance campaign 2, field-1: docs/PERF2_PLAN.md item 1;
tools/msxsprites.py field_trim, trim_entries): every frame, normal and white, draws the same pixels at the same
places as the whole frame did, from the tables the ROM gets (POOL_lN_field.inc's field_tab: x, y, width, height,
dx, dy), the atlas as VRAM holds it, the frame cache's ROM and the dynamic frames (tools/msxframe.py FieldLooks,
as tools/bstest/fieldcheck.py reads them).

The conversion test converts the pool twice into a temporary folder (with and without --no-trim, about 35 s:
numpy and make msx's inputs, as tests/test_msxsprites.py's PoolTests) and compares them frame by frame. Run it
with the project's venv: ~/.venvs/msxports/bin/python -I -m unittest discover -s tests -p test_field_trim.py."""
from __future__ import annotations

import importlib.util
import json
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

HAVE_NUMPY = importlib.util.find_spec("numpy") is not None
BUILD = ROOT / "build"
X = BUILD / "extracted"
INPUTS = [X / "boot/main_8000.bin", X / "files/PERMA_05.bin", X / "files/DATAL1_10.bin", X / "files/DATAL2_18.bin",
          BUILD / "sprites/catalog.json", BUILD / "sprites/catalog_l2.json", BUILD / "sprites/catalog_l3.json",
          BUILD / "emu/cov_level1.json", BUILD / "ram/level1_full.bin", BUILD / "ram/level2_full.bin",
          BUILD / "ram/level3_full.bin", BUILD / "msx/level2.pal", BUILD / "msx/level3.pal"]
HAVE_BUILD = all(p.exists() for p in INPUTS)


def field_tab(pool: Path, level: int) -> list[tuple[int, ...]]:
    """POOL_lN_field.inc's field_tab: per frame (x, y, width, height, dx, dy), dx and dy signed."""
    inc = pool.with_name(f"{pool.name}_l{level}_field.inc").read_text()
    body = re.sub(r";.*", "", inc.partition("field_tab:")[2].partition("field_look:")[0])
    out = []
    for m in re.finditer(r"db (\d+), (\d+), (\d+), (\d+), (\d+), (\d+)", body):
        x, y, w, h, dx, dy = (int(v) for v in m.groups())
        out.append((x, y, w, h, dx - 256 * (dx >> 7), dy - 256 * (dy >> 7)))
    return out


def drawings(pool: Path, level: int) -> dict[tuple[int, int], frozenset]:
    """Per (frame id, white) the pixels the engine draws for a BOB of that frame at (0, 0): msx/field.asm
    fb_wants places it at the record + the frame's own dx, dy and draws the frame it looks like (field_look:
    its field_tab entry, its pixels; level 3's white copy when it has one, msx/field.asm fc_find) -> a set
    of (x, y, colour)."""
    import msxframe
    looks = msxframe.FieldLooks(level, pool)
    tab = field_tab(pool, level)
    assert len(tab) == len(looks.frames)
    out = {}
    for fid, f in looks.frames.items():
        look = looks.frames[f["look"]]
        x, y, w, h, _, _ = tab[f["look"]]
        assert (look["x"], look["y"], look["sw"], look["sh"]) == (x, y, w, h), (level, fid)
        assert (f["sw"], f["sh"]) == (w, h), (level, fid)
        dx, dy = tab[fid][4:]
        assert (f["ox"], f["oy"]) == (dx, dy), (level, fid)
        for white in ((0, 1) if level == 3 else (0,)):
            px = looks.pixels(f["look"] | (0x80 if white else 0))
            assert len(px) == h and all(len(r) == w for r in px), (level, fid)
            out[(fid, white)] = frozenset((dx + c, dy + r, v) for r, row in enumerate(px) for c, v in enumerate(row) if v)
    return out


def tight(pool: Path, level: int) -> list[int]:
    """The frames whose box has an empty side (no pixel in its first or last line, or in its first or last
    two columns: x edges are even) among those it cut (their "tx" in the json)."""
    import msxframe
    looks = msxframe.FieldLooks(level, pool)
    bad = []
    for fid, f in looks.frames.items():
        if "tx" not in f:
            continue
        px = looks.pixels(fid)
        cols = lambda c0: any(row[c] for row in px for c in (c0, c0 + 1) if c < len(row))   # noqa: E731
        if not (any(px[0]) and any(px[-1]) and cols(0) and cols(len(px[0]) - 2)):
            bad.append(fid)
    return bad


def fc_layout(pool: Path) -> tuple[list[int], list[int], bytes]:
    """Level 3's frame cache's header: per frame [normal, white] cache frames, per cache frame its place, the
    places' table."""
    inc = {m[1]: int(m[2], 0) for m in re.finditer(r"^(\w+): equ (\S+)", pool.with_name(pool.name + "_l3_field.inc")
                                                   .read_text(), re.M)}
    fc = pool.with_name(pool.name + "_l3_fc.bin").read_bytes()
    ent, plc = inc["FC_ENT"] - 0x8000, inc["FC_PLC"] - 0x8000
    return list(fc[:ent]), [fc[ent + 4 * c + 3] for c in range(inc["FC_N"])], fc[plc:plc + 3 * inc["FC_PLACES"]]


@unittest.skipUnless(HAVE_NUMPY, "numpy missing: run with the project's venv")
class TrimTests(unittest.TestCase):
    """tools/msxsprites.py field_trim on made-up frames."""

    def test_the_box(self):
        import numpy as np
        import msxsprites as ms
        img = np.zeros((10, 16), np.uint8)
        self.assertEqual(ms.field_trim(img), (0, 0, 16, 10))        # (no pixel: the whole frame)
        img[3, 5] = 7
        self.assertEqual(ms.field_trim(img), (4, 3, 6, 4))          # (x edges even)
        img[8, 12] = 1
        self.assertEqual(ms.field_trim(img), (4, 3, 14, 9))
        img[0, 0] = img[9, 15] = 2
        self.assertEqual(ms.field_trim(img), (0, 0, 16, 10))

    def test_a_mirror_cut_is_the_cut_mirrored(self):
        import numpy as np
        import msxsprites as ms
        rng = np.random.default_rng(3)
        for _ in range(200):
            img = np.zeros((12, 24), np.uint8)
            y0, x0 = rng.integers(0, 6), rng.integers(0, 12)
            img[y0:y0 + rng.integers(1, 6), x0:x0 + rng.integers(1, 12)] = rng.integers(1, 16)
            x0_, y0_, x1_, y1_ = ms.field_trim(img)
            m0, n0, m1, n1 = ms.field_trim(img[:, ::-1])
            self.assertEqual((m0, n0, m1, n1), (24 - x1_, y0_, 24 - x0_, y1_))
            self.assertTrue(np.array_equal(img[y0_:y1_, x0_:x1_][:, ::-1], img[:, ::-1][n0:n1, m0:m1]))

    def test_trim_entries_moves_the_offsets(self):
        import msxsprites as ms
        out = [{"src": "a", "x": 10, "y": 20, "sw": 48, "sh": 28, "ox": 0, "oy": 0},
               {"src": "a", "x": 10, "y": 20, "sw": 48, "sh": 28, "ox": 0, "oy": 4},     # (a removed frame)
               {"src": "c", "x": 0, "y": 0, "sw": 64, "sh": 40, "ox": 0, "oy": 0},       # (a cache frame)
               {"src": "d", "x": 0, "y": 232, "sw": 48, "sh": 56, "ox": 0, "oy": 0}]     # (not cut)
        ms.trim_entries(out, {"a": (6, 1, 40, 28), "c": (0, 3, 64, 40)}, {"a"})
        self.assertEqual([(e["x"], e["y"], e["sw"], e["sh"], e["ox"], e["oy"]) for e in out],
                         [(16, 21, 34, 27, 6, 1), (16, 21, 34, 27, 6, 5), (0, 0, 64, 37, 0, 3), (0, 232, 48, 56, 0, 0)])
        self.assertEqual([(e.get("tx"), e.get("ty")) for e in out], [(6, 1), (6, 1), (0, 3), (None, None)])


@unittest.skipUnless(HAVE_NUMPY and HAVE_BUILD, "numpy or make msx's inputs missing")
class ConversionTests(unittest.TestCase):
    """Both conversions of the pool (the frames cut, and --no-trim): the same pictures."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)

        def convert(out: Path, *extra: str) -> None:
            out.mkdir()
            r = subprocess.run([sys.executable, "-I", str(ROOT / "tools/msxsprites.py"), str(X / "boot/main_8000.bin"),
                                str(X / "files/PERMA_05.bin"), str(X / "files/DATAL1_10.bin"), "--rows", "51",
                                "--bobs", str(BUILD / "sprites/catalog.json"), "--drawn", str(BUILD / "emu/cov_level1.json"),
                                "--ram", str(BUILD / "ram/level1_full.bin"), "--level", "level1",
                                "--remove", str(ROOT / "msx/level1_frames.json"), "--pool", str(out / "sprites"),
                                "--l2-datal", str(X / "files/DATAL2_18.bin"), "--l2-rows", "50",
                                "--l2-bobs", str(BUILD / "sprites/catalog_l2.json"),
                                "--l2-ram", str(BUILD / "ram/level2_full.bin"), "--l2-pal", str(BUILD / "msx/level2.pal"),
                                "--l2-remove", str(ROOT / "msx/level2_frames.json"),
                                "--l3-bobs", str(BUILD / "sprites/catalog_l3.json"),
                                "--l3-ram", str(BUILD / "ram/level3_full.bin"), "--l3-pal", str(BUILD / "msx/level3.pal"),
                                "--l3-remove", str(ROOT / "msx/level3_frames.json"), *extra, str(out / "robocop")],
                               cwd=ROOT, capture_output=True, text=True)
            assert r.returncode == 0, r.stdout + r.stderr
        convert(t / "cut")
        convert(t / "whole", "--no-trim")
        cls.cut, cls.whole = t / "cut" / "sprites", t / "whole" / "sprites"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def json(self, pool: Path, level: int) -> dict:
        return json.loads(pool.with_name(f"{pool.name}_l{level}.json").read_text())

    def test_every_frame_draws_the_same(self):
        for level in (1, 2, 3):
            a, b = drawings(self.whole, level), drawings(self.cut, level)
            self.assertEqual(sorted(a), sorted(b))
            same = [k for k in a if a[k] == b[k]]
            self.assertEqual(len(same), len(a), (level, sorted(set(a) - set(same))))
        self.assertEqual(len([k for k in b if k[1]]), 66)               # (level 3: 66 frames, normal and white)

    def test_level3s_cut(self):
        cut = [f for f in self.json(self.cut, 3)["field"] if "tx" in f]
        kinds = {f["kind"] for f in cut}
        self.assertLessEqual(kinds, {0, 1})                             # (the static and the cache's frames)
        self.assertGreaterEqual(len(cut), 50)
        self.assertEqual(tight(self.cut, 3), [])
        whole = {f["fid"]: f for f in self.json(self.whole, 3)["field"]}
        for f in self.json(self.cut, 3)["field"]:                      # (the smoke and the lift's parts whole)
            if f["kind"] in (2, 3):
                self.assertEqual((f["x"], f["y"], f["sw"], f["sh"], f["ox"], f["oy"]),
                                 tuple(whole[f["fid"]][k] for k in ("x", "y", "sw", "sh", "ox", "oy")))

    def test_level3s_cache_keeps_its_places_and_shrinks(self):
        a, b = fc_layout(self.whole), fc_layout(self.cut)
        self.assertEqual(a, b)                                          # (the same frames, places and table)
        fa = self.whole.with_name("sprites_l3_fc.bin").stat().st_size
        fb = self.cut.with_name("sprites_l3_fc.bin").stat().st_size
        self.assertLess(fb, fa)
        for c in self.json(self.cut, 3)["fc"]:                          # (each cache frame as drawn: its box)
            self.assertEqual(c["w"] % 2, 0)

    def test_the_atlases_and_the_rest_unchanged(self):
        for name in ("sprites.bin", "sprites.inc", "sprites_fdyn.bin", "sprites_l1_field.bin", "sprites_l2_field.bin",
                     "sprites_l3_field.bin", "sprites_l1_field_vram.bin", "sprites_l2_field_vram.bin",
                     "sprites_l3_field_vram.bin", "robocop.bin", "robocop_fdyn.bin"):
            self.assertEqual(self.cut.with_name(name).read_bytes(), self.whole.with_name(name).read_bytes(), name)


if __name__ == "__main__":
    unittest.main()
