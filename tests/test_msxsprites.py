"""The sprite tools for level 2 (the level-2 plan's step 10): tools/bobcatalog.py's level-2 mode,
tools/msxsprites.py's global pool (--pool), its composition format read back, type 1's joint
compositions, tools/msxframe.py's per-level looks and the frame chooser (tools/msxchooser.py).

The tests that need numpy (tools/msxsprites.py) skip without it: run them with the project's venv
(~/.venvs/msxports/bin/python -I -m unittest discover -s tests -p test_msxsprites.py). The pool's
own test also needs make msx's inputs (build/); it converts both levels into a temporary folder
(about 20 s) and checks the step's acceptance there."""
from __future__ import annotations

import importlib.util
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import bobcatalog  # noqa: E402

HAVE_NUMPY = importlib.util.find_spec("numpy") is not None
BUILD = ROOT / "build"
INPUTS = [BUILD / p for p in ("extracted/boot/main_8000.bin", "extracted/files/PERMA_05.bin",
                              "extracted/files/DATAL1_10.bin", "extracted/files/DATAL2_18.bin",
                              "sprites/catalog.json", "emu/cov_level1.json", "ram/level1_full.bin",
                              "ram/level2_full.bin", "msx/level2.pal", "msx/robocop.bin")]
HAVE_BUILD = all(p.exists() for p in INPUTS) and (BUILD / "rea" / "asm").is_dir()


def main_with(words: dict[int, int], size: int = 0x8000) -> bytes:
    """A main-code image (loaded at 8000h) with these words."""
    b = bytearray(size)
    for a, v in words.items():
        struct.pack_into(">H", b, a - 0x8000, v & 0xFFFF)
    return bytes(b)


class CatalogueTests(unittest.TestCase):
    """tools/bobcatalog.py: its level-2 mode on synthetic code."""

    def setUp(self):
        bobcatalog.UNRESOLVED.clear()

    def test_bltsize_from_a_table_and_any_other_d4_write(self):
        lines = [(0x100, "move.w", "#0x402, D4w"),              # (an earlier immediate)
                 (0x104, "bsr.w", "0x0000ab08"),
                 (0x108, "lea", "(0x57192).l, A2"),
                 (0x10e, "adda.w", "(0xd066,PC,D3w*0x1), A2"),
                 (0x112, "move.w", "(0xd096,PC,D3w*0x1), D4w"),
                 (0x116, "bra.w", "0x0000ac56"),
                 (0x11a, "moveq", "0x3, D4"),                   # (not a BLTSIZE)
                 (0x11c, "bsr.w", "0x0000ab08")]
        procs = {0x100: ("obj04_update", lines)}
        targets = {0xAB08, 0xAC56}
        old = bobcatalog.scan(procs, targets)                   # (level 1: the stale immediate)
        self.assertEqual([(r["site"], r["bltsize"]) for r in old], [(0x116, 0x402), (0x11c, 0x402)])
        bobcatalog.UNRESOLVED.clear()
        new = bobcatalog.scan(procs, targets, l2=True)
        self.assertEqual([(r["site"], r["bltsize"], r.get("d4_table")) for r in new], [(0x116, None, 0xD096)])
        self.assertEqual(bobcatalog.UNRESOLVED, [(0x100, "obj04_update", 0x104), (0x100, "obj04_update", 0x11c)])

    def test_table_frames(self):
        main = main_with({0xD000: 0x0000, 0xD002: 0x00A0, 0xD004: 0x0000, 0xD006: 0x0140,
                          0xD010: 0x0402, 0xD012: 0x0403, 0xD014: 0x0402, 0xD016: 0x0403})
        self.assertEqual(bobcatalog.table_frames(main, 0x3BFC0, ("u", 0xD000, 4), ("t", 0xD010)),
                         [(0x3BFC0, 0x402), (0x3C060, 0x403), (0x3C100, 0x403)])
        self.assertEqual(bobcatalog.table_frames(main, 0x100, (0, 4, 0), 0x402), [(0x100, 0x402), (0x104, 0x402)])

    def test_the_walk_goes_on_past_a_repeated_offset(self):
        fs = 5 * 4 * 24                                         # (32 x 24)
        offs = [0, fs, 2 * fs, 3 * fs, 3 * fs, 4 * fs, 4 * fs, 4 * fs, 3]
        main = main_with({0xD2DA + 2 * i: v for i, v in enumerate(offs)})
        ref = {"bltsize": 0x603, "base": 0x3C920, "adjust": [], "table": 0xD2DA}
        self.assertEqual(len(bobcatalog.frames_for(ref, main, 0x80000)), 4)            # (level 1: stops)
        self.assertEqual(bobcatalog.frames_for(ref, main, 0x80000, dedupe=True),
                         [0x3C920 + k * fs for k in range(5)])                         # (type 6: 5 frames)


@unittest.skipUnless(HAVE_NUMPY, "numpy missing: run with the project's venv")
class FormatTests(unittest.TestCase):
    """tools/msxsprites.py: a composition encoded, packed and read back (SpriteData)."""

    def test_records_read_back(self):
        import numpy as np
        import msxsprites as ms
        pal = ms.msx_palette(bytes([0x00, 0, 0x77, 7, 0x70, 0, 0x07, 0, 0x00, 7, 0x44, 4, 0x11, 1, 0x22, 2]
                                   + [0x33, 3] * 8))
        rng = np.random.default_rng(5)
        tgt = np.zeros((40, 40), int)
        tgt[3:37, 4:38] = rng.integers(1, 8, (34, 34))
        conv = ms.Converter(pal, ms.PAIRS_ALL, cap=ms.BOB_CAP, align="bottom")
        lay = conv.composition(tgt)
        pats, cols = ms.Pool(), ms.Pool()
        blob, sprites, nlines = ms.encode(lay, pats, cols)
        filler = b"\xee" * (ms.BANK - 40)                       # (the second blob crosses no bank's end)
        area, where = ms.pack_area([filler, None, blob], 3 * 2)
        self.assertEqual(where[1], None)
        self.assertEqual(where[2] // ms.BANK, 1)
        struct.pack_into("<BH", area, 3, where[2] // ms.BANK, where[2] % ms.BANK)
        pad = lambda b: bytes(b) + b"\xff" * (-len(b) % ms.BANK)  # noqa: E731
        data = pad(area) + pad(b"".join(pats.items)) + pad(b"".join(cols.items))
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "p.bin").write_bytes(data)
            (Path(d) / "p.inc").write_text(f"SPR_PAT_BANK: equ {len(pad(area)) // ms.BANK}\n"
                                           f"SPR_COL_BANK: equ {(len(pad(area)) + len(pad(b''.join(pats.items)))) // ms.BANK}\n"
                                           "SPR_BOB_INDEX_L2: equ 0x8003\nSPR_BOB_INDEX: equ SPR_BOB_INDEX_L2\n")
            sd = ms.SpriteData(Path(d) / "p.bin", Path(d) / "p.inc")
        self.assertEqual(sd.inc["SPR_BOB_INDEX"], 0x8003)
        o = sd.bob_entry(2, 0)
        self.assertEqual(o, where[2])
        rec = sd.record(o)
        self.assertEqual(rec["header"][:2], (len(sprites), nlines))
        self.assertEqual(len(rec["layout"]), len(lay))
        for (ya, ba), (yb, bb) in zip(lay, rec["layout"]):
            self.assertEqual(ya, yb)
            for a, b in zip(ba, bb):
                self.assertEqual(a["x"], b["x"])
                self.assertTrue((a["full"] == b["full"]).all())
                self.assertTrue((a["fallback"] == b["fallback"]).all())
        _, full, fb = ms.preview(lay, tgt)
        for one, want in ((False, np.pad(full, 32)), (True, np.pad(fb, 32))):
            img, y0, x0 = sd.look(o, one)
            self.assertTrue((want[y0 + 32:y0 + 32 + img.shape[0], x0 + 32:x0 + 32 + img.shape[1]] == img).all())
            self.assertEqual(int((img > 0).sum()), int((want > 0).sum()))
        self.assertLessEqual(ms.max_per_line(lay), ms.BOB_CAP)

    def test_read_inc(self):
        import msxsprites as ms
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.inc"
            p.write_text("; c\nA: equ 0x10      ; x\nB: equ A\nC: equ 7\n")
            self.assertEqual(ms.read_inc(p), {"A": 16, "B": 16, "C": 7})


@unittest.skipUnless(HAVE_NUMPY and (BUILD / "ram/level2_full.bin").exists(), "numpy or build/ram missing")
class JointTests(unittest.TestCase):
    def test_type1_joint_compositions(self):
        import numpy as np
        import msxsprites as ms
        ram = (BUILD / "ram/level2_full.bin").read_bytes()
        main = (BUILD / "extracted/boot/main_8000.bin").read_bytes()
        near = np.arange(16)
        joints = ms.joint_targets(ram, main, near)
        self.assertEqual(len(joints), 16)
        for k, (fr, tgt) in enumerate(joints):
            legs, torso = fr["joint"]
            self.assertEqual((fr["addr"], fr["w"], fr["h"]), tuple(legs[:3]))
            self.assertEqual(legs[0], 0x3E810 + struct.unpack_from(">H", main, 0xC7E0 + 2 * k - 0x8000)[0])
            self.assertEqual(torso[0], 0x404D0 if k < 8 else 0x40674)
            self.assertEqual(torso[3], -2 if k < 8 else 2)
            self.assertEqual(torso[4], (1, 1, 0, 0)[(k % 8) % 4] - 21)   # ($C800[k & 7], less the legs' 21)
            want = np.full((60, 60), -1, int)                   # (the legs at (10, 30), the torso over them)
            for addr, w, h, dx, dy in (legs, torso):
                img = ms.bob_image(ram, addr, w, h)
                reg = want[30 + dy:30 + dy + h, 10 + dx:10 + dx + w]
                reg[img >= 0] = img[img >= 0]
            ox, oy = fr["origin"]
            got = want[30 + oy:30 + oy + tgt.shape[0], 10 + ox:10 + ox + tgt.shape[1]]
            self.assertTrue((np.where(got >= 0, got, 0) == tgt).all())
            self.assertEqual(int((want >= 0).sum()), int((got >= 0).sum()))   # (nothing outside the canvas)
        mirrors = ms.bob_mirrors([t for _, t in joints])
        self.assertEqual(sorted(mirrors), list(range(8, 16)))   # (the right side: the left one mirrored)


@unittest.skipUnless(HAVE_NUMPY and HAVE_BUILD, "numpy or make msx's inputs missing")
class PoolTests(unittest.TestCase):
    """The step's acceptance on a fresh conversion of both levels."""

    @classmethod
    def setUpClass(cls):
        import msxsprites as ms
        cls.ms = ms
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        py = sys.executable
        run = lambda *a: subprocess.run([py, "-I", *map(str, a)], cwd=ROOT, capture_output=True, text=True)  # noqa: E731
        cat = run(ROOT / "tools/bobcatalog.py", "level2", "-o", t / "catalog_l2.json")
        assert cat.returncode == 0, cat.stdout + cat.stderr
        cls.cat_log = cat.stdout
        x = BUILD / "extracted"
        r = run(ROOT / "tools/msxsprites.py", x / "boot/main_8000.bin", x / "files/PERMA_05.bin",
                x / "files/DATAL1_10.bin", "--rows", 51, "--bobs", BUILD / "sprites/catalog.json",
                "--drawn", BUILD / "emu/cov_level1.json", "--ram", BUILD / "ram/level1_full.bin",
                "--level", "level1", "--remove", ROOT / "msx/level1_frames.json", "--pool", t / "sprites",
                "--l2-datal", x / "files/DATAL2_18.bin", "--l2-rows", 50, "--l2-bobs", t / "catalog_l2.json",
                "--l2-ram", BUILD / "ram/level2_full.bin", "--l2-pal", BUILD / "msx/level2.pal",
                "--l2-remove", ROOT / "msx/level2_frames.json", t / "robocop")
        assert r.returncode == 0, r.stdout + r.stderr
        cls.log = r.stdout
        c = run(ROOT / "tools/msxchooser.py", t / "sprites", t / "quadros.html")
        assert c.returncode == 0, c.stdout + c.stderr
        cls.t = t
        cls.l2 = json.loads((t / "sprites_l2.json").read_text())
        cls.inc = ms.read_inc(t / "sprites.inc")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_catalogue_lists_level2s_229_frames(self):
        self.assertIn("229 distinct frames (56 in DATAL2, 173 shared)", self.cat_log)
        frames = self.l2["frames"]
        self.assertEqual(len(frames), 229)
        self.assertNotIn("none", frames.values())               # (every one converted: sprite, joint, field)
        for k in ("3d280:48:56", "3d0a0:32:24", "58312:32:38", "57912:32:32", "41358:16:16", "3c2e0:32:16"):
            self.assertIn(k, frames)
        for k in ("57192:16:16", "4ed26:16:16"):                # (the level-1 scan's errors)
            self.assertNotIn(k, frames)

    def test_level1s_files_unchanged(self):
        for name in ("robocop.bin", "robocop.inc", "robocop.json", "robocop_field.bin", "robocop_field.inc",
                     "robocop_fdyn.bin", "robocop_flash.inc", "robocop.pal", "robocop.remap"):
            self.assertEqual((self.t / name).read_bytes(), (BUILD / "msx" / name).read_bytes(), name)

    def test_the_pool_grows_by_four_banks(self):
        old = self.ms.read_inc(BUILD / "msx/robocop.inc")
        banks = len((self.t / "sprites.bin").read_bytes()) // self.ms.BANK
        self.assertEqual(banks, len((BUILD / "msx/robocop.bin").read_bytes()) // self.ms.BANK + 4)
        self.assertEqual((self.inc["SPR_PAT_BANK"], self.inc["SPR_COL_BANK"] - self.inc["SPR_PAT_BANK"]),
                         (old["SPR_PAT_BANK"] + 1, old["SPR_COL_BANK"] - old["SPR_PAT_BANK"] + 2))
        self.assertEqual(self.inc["SPR_BOB_INDEX_L1"], old["SPR_BOB_INDEX"])
        self.assertEqual(self.inc["SPR_BOB_INDEX_L2"], old["SPR_BOB_INDEX"] + 3 * old["SPR_BOBS"])
        self.assertEqual((self.inc["SPR_BOBS_L2"], self.inc["SPR_SPARK_L2"]), (204, 200))

    def test_level1s_frames_render_the_same(self):
        ms = self.ms
        old = ms.SpriteData(BUILD / "msx/robocop.bin", BUILD / "msx/robocop.inc")
        new = ms.SpriteData(self.t / "sprites.bin", self.t / "sprites.inc")
        n_rc = old.inc["SPR_RECORDS"] * 4 + old.inc["SPR_RC_ARMS"]
        pairs = [(old.entry(k), new.entry(k)) for k in range(n_rc)]
        pairs += [(old.bob_entry(None, k), new.bob_entry(1, k)) for k in range(old.inc["SPR_BOBS"])]
        for oo, on in pairs:
            for one in (False, True):
                a, b = old.look(oo, one), new.look(on, one)
                self.assertEqual(a[1:], b[1:])
                self.assertTrue((a[0] == b[0]).all())

    def test_type1_joint_and_the_field(self):
        joint = [b for b in self.l2["bobs"] if b["proc"] == "obj01_joint"]
        self.assertEqual(len(joint), 16)
        self.assertLessEqual(max(b["max_line"] for b in joint), 3)
        self.assertEqual(sorted((h["addr"], h["w"], h["h"]) for h in self.l2["hidden"]),
                         [(0x404D0, 32, 21), (0x40674, 32, 21)])
        self.assertEqual(len(self.l2["field"]), 35)
        inc = self.ms.read_inc(self.t / "sprites_l2_field.inc")
        self.assertEqual((inc["FIELD_LINES"], inc["FIELD_ID0"], inc["DYN_Y"]), (108, 0xD0, 224))
        self.assertEqual(self.ms.read_inc(self.t / "sprites_l1_field.inc")["FIELD_ID0"], 0xD0)
        self.assertLessEqual(len((self.t / "sprites_l2_field.bin").read_bytes()), 2 * self.ms.BANK)
        self.assertEqual((self.t / "sprites_fdyn.bin").read_bytes(), (BUILD / "msx/robocop_fdyn.bin").read_bytes())
        self.assertTrue(self.l2["flash_same"])

    def test_msxframe_reads_the_pool(self):
        import msxframe
        try:
            msxframe.use_pool(self.t / "sprites", 2)
            lay = msxframe.converted({"bob": 1, "id": next(b["id"] for b in self.l2["bobs"]
                                                           if b["proc"] == "obj01_joint")}, b"")
            self.assertLessEqual(min(y for y, _ in lay), -21)     # (the torso above the legs' call)
            self.assertEqual(msxframe.silhouette_colours(b"")[1:3], [9, 5])
        finally:
            msxframe.SOURCE.clear()
            msxframe._conv_cache.clear()

    def test_the_chooser_lists_level2s_new_frames(self):
        html = (self.t / "quadros.html").read_text()
        data = json.loads(html[html.index('type="application/json">') + 24:html.index("</script>")])
        keys = {k for g in data["groups"] if g["section"] == "Level 2" for c in g["items"]
                for k in [c["key"], *c["also"]]}
        for b in self.l2["bobs"]:
            if "new" in b:
                self.assertIn(f"l2:bob:{b['addr']:x}:{b['w']}:{b['h']}", keys)
        for f in self.l2["field"]:
            if f["proc"] in ("obj02_update", "obj14_update", "obj16_update", "FUN_00008f02"):
                self.assertIn(f"l2:bob:{f['addr']:x}:{f['w']}:{f['h']}", keys)
        self.assertIn("rc:14:0", {c["key"] for g in data["groups"] if g["section"] == "Level 2" for c in g["items"]})



@unittest.skipUnless((BUILD / "msx/sprites_l2_field.inc").exists() and (BUILD / "msx/sprites_fdyn.bin").exists(),
                     "make msx's sprite pool missing")
class FieldLooksTests(unittest.TestCase):
    """tools/msxframe.py FieldLooks: each level's play-field frames as its ROM uploads them (the level-2
    plan's step 13): level 2's own frames from its atlas, the dynamic ones the same as level 1's."""

    def test_level_twos_frames_and_the_shared_dynamic_ones(self):
        import msxframe
        pool = BUILD / "msx/sprites"
        l1, l2 = msxframe.FieldLooks(1, pool), msxframe.FieldLooks(2, pool)
        self.assertEqual(len(l2.frames), l2.inc["FIELD_N"])
        trolley = next(f for f in l2.frames.values() if f["addr"] == 0x4B95A)
        px = l2.pixels(trolley["fid"])
        self.assertEqual((len(px), len(px[0])), (trolley["sh"], trolley["sw"]))
        self.assertTrue(any(c for row in px for c in row))
        for f in l2.frames.values():
            if "dyn" not in f:
                continue
            g = next(g for g in l1.frames.values() if (g["addr"], g["w"], g["h"]) == (f["addr"], f["w"], f["h"]))
            self.assertEqual(l2.pixels(f["fid"]), l1.pixels(g["fid"]), hex(f["addr"]))


if __name__ == "__main__":
    unittest.main()
