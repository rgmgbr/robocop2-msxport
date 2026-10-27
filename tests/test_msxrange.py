"""tools/msxrange.py: the shooting range's graphics, hit data and tables (docs/RANGE.md 3.3, 3.4, 3.11)."""
import contextlib
import hashlib
import io
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import msxrange  # noqa: E402
from msxpuzl import parse_data, unpack  # noqa: E402

FRNG = ROOT / "build" / "extracted" / "files" / "FRNG_15.bin"    # make extract
# sha256 of the graphics report's prototype outputs (2026-10-27): range_1.pal, range_2.pal,
# range_line.spr, range_sheets.bin, and range_scene.sc5's columns 64-319 and its strip of columns
# 0-63 (rows 10-90 and 91-171 side by side), the acceptance of the converter
PROTOTYPE = {
    "pal1": "36a3757389030c32332e62a7f7fcb22f5b9b15ffce70d4e6ea1de51cd6e72151",
    "pal2": "b7796cc9160f3d2a2c21dc7211fb4efaed31a3e935d50fa9f20e57827bdb2d09",
    "spr": "2af8400eb9459b029283707defb2247520c0a7f98ace7fa87f0c13e1854745e6",
    "sheets": "764a9c1a7f1b662aaae58314a373d7d31aea39f200f93e055805326e37c6477c",
    "scene": "7336a68ac7b56deeea4b813103c33b82d7204268886dce2871b4087d50f88496",
    "strip": "5607830150f79678dff3c25bd53cc4a499274d3b412b30130e31863ec71b2867",
}
# a few of the prototype's sheet places (out/sizes.json) and its position rectangles
PROTO_PLACES = {0x30C82: (0, 162), 0x2F272: (228, 162), 0x31D02: (0, 418), 0x2CC62: (132, 901),
                0x2D7A2: (65, 484), 0x3CFE2: (177, 484), ("front", 0): (107, 901), ("front", 5): (209, 674),
                ("front", 8): (0, 484)}
PROTO_RECTS = {0: (4, 29, 25, 28), 1: (58, 24, 29, 34), 2: (56, 99, 31, 33), 3: (126, 99, 27, 29),
               4: (194, 47, 20, 46), 5: (236, 44, 19, 51), 6: (274, 46, 22, 21), 7: (194, 104, 20, 29),
               8: (234, 100, 20, 23)}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def equates(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = re.match(r"^(\w+):\s+equ\s+(\S+)", line)
        if m:
            out[m.group(1)] = int(m.group(2), 0)
    return out


class RuleTests(unittest.TestCase):
    def test_camera_keeps_the_line_in_view(self):
        for b9a in range(0x7C, 0x199, 4):
            for s0 in range(0, 65):
                s = msxrange.camera(s0, b9a)
                cx = b9a - msxrange.LINE_DX
                self.assertTrue(0 <= s <= 64 and 13 <= cx - s <= 233, (b9a, s0, s))
                if 64 <= cx - s0 <= 191:
                    self.assertEqual(s, s0)          # the middle band: the camera holds still
        self.assertEqual(msxrange.camera(32, 240), 32)

    def test_pages_and_r18(self):
        for s in range(0, 65):
            c = msxrange.page_c(s)
            self.assertTrue(c % 16 == 0 and 0 <= c <= 64 and -7 <= c - s <= 8, s)
            self.assertEqual(msxrange.r18_shift((s - c) & 15), c - s)
        self.assertEqual((msxrange.page_c(7), msxrange.page_c(8)), (0, 16))
        self.assertEqual([msxrange.r18_shift(v) for v in (8, 9, 15, 0, 1, 7)], [8, 7, 1, 0, -1, -7])

    def test_columns_and_sat(self):
        self.assertEqual(len(msxrange.column(5, 0, msxrange.SPR_LINES)), 10)
        self.assertEqual(msxrange.column(5, 0, msxrange.SPR_LINES)[-1], (143, 5, 13))   # lines 144-157
        self.assertEqual(msxrange.column(9, -20, 30), [(255, 9, 9)])                    # lines 0-9
        self.assertEqual(msxrange.sat_bytes([(255, 9, 9)]), bytes((255, 9, 36, 0, 216, 0, 0, 0)))
        self.assertEqual(msxrange.parse_sat(bytes((255, 9, 36, 0, 216, 1, 2, 3, 7, 7, 7, 7))), [(255, 9, 9)])
        with self.assertRaisesRegex(ValueError, "pattern"):
            msxrange.parse_sat(bytes((0, 0, 64, 0)))

    def test_line_patterns(self):
        pats = msxrange.line_patterns()
        self.assertEqual(len(pats), 512)
        self.assertEqual(pats[32 * 13:32 * 13 + 16], bytes([0x80] * 14 + [0, 0]))
        self.assertEqual(pats[32 * 13 + 16:32 * 14], bytes(16))

    def test_mirror(self):
        self.assertEqual(msxrange.mirror(bytes.fromhex("0002cf32")), bytes.fromhex("020032cf"))


@unittest.skipUnless(FRNG.exists(), "make extract first")
class RangeDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.crunched = FRNG.read_bytes()
        cls.data = msxrange.decrunch(cls.crunched)
        cls.rg = msxrange.Range(cls.data)          # every check of the converter runs here, the sweep too

    def test_decrunch(self):
        self.assertEqual(sha(self.data), "2ec1d6a4bf965d9ab11ea6ac2b1c8fde8385b1030ce4643c7740cbf203b6d26f")
        bad = bytearray(self.crunched)
        bad[200] ^= 0x10
        with self.assertRaises(ValueError):
            msxrange.decrunch(bytes(bad))

    def test_outputs_equal_the_prototype(self):
        rg = self.rg
        self.assertEqual(sha(msxrange.v9938(rg.pal[1])), PROTOTYPE["pal1"])
        self.assertEqual(sha(msxrange.v9938(rg.pal[2])), PROTOTYPE["pal2"])
        self.assertEqual(sha(rg.pats), PROTOTYPE["spr"])
        self.assertEqual(len(rg.blob), 63616)
        self.assertEqual(sha(rg.blob[:20736]), PROTOTYPE["scene"])
        self.assertEqual(sha(rg.blob[20736:25920]), PROTOTYPE["strip"])
        self.assertEqual(sha(rg.blob[25920:]), PROTOTYPE["sheets"])
        self.assertEqual({k: rg.place[k] for k in PROTO_PLACES}, PROTO_PLACES)
        self.assertEqual(rg.places, PROTO_RECTS)
        self.assertEqual([s[4] for s in rg.streams], [162, 81, 88, 89, 87, 74])

    def test_blob_is_the_vram_model(self):
        rg = self.rg
        scene = unpack(rg.blob[:20736], 256)
        self.assertEqual([bytes(r) for r in scene], [r[64:] for r in rg.scene])
        strip = unpack(rg.blob[20736:25920], 128)
        self.assertEqual([bytes(r[:64]) for r in strip], [r[:64] for r in rg.scene[:81]])
        self.assertEqual([bytes(r[64:]) for r in strip], [r[:64] for r in rg.scene[81:]])
        self.assertFalse({v for r in rg.scene for v in r} & {1, 14, 15})
        self.assertEqual(len(rg.pics), 37)
        self.assertEqual(sum(w * h for _, w, h in rg.blocks), 65969)

    def test_hit_data(self):
        rg, d = self.rg, self.data
        hit = rg.hit
        self.assertEqual(len(hit), 8192 + 4896)
        self.assertEqual(hit[:6880], d[0x466C2 - 0x1EA00:0x481A2 - 0x1EA00])
        self.assertEqual(hit[6880:8192], b"\xff" * 1312)
        self.assertEqual(d[0x481A2 - 0x1EA00:], b"\xff" * 1080)
        masks = [p for p in rg.pics if rg.kind[p] != "dissolve"]
        self.assertEqual(len(masks), 19)
        o = 8192
        for p in masks:                            # by address, one after another, each in one bank
            n = 2 * ((rg.blt[p] & 63) - 1) * (rg.blt[p] >> 6)
            self.assertEqual(rg.mask_ofs[p], o)
            self.assertEqual(hit[o:o + n], d[p - 0x1EA00:p - 0x1EA00 + n])
            o += n
        self.assertEqual(o, len(hit))

    def test_tables(self):
        rg = self.rg
        tab = parse_data(rg.tab_text())
        rg.check_tab(rg.tab_text())
        self.assertEqual(rg.tab_len, 1950)
        self.assertEqual(list(tab["rgt_kind"][:3]), [0, 1, 1])
        self.assertEqual(list(tab["rgt_kind"][14:26]), [2] * 9 + [3] * 3)
        desc = struct.unpack("<42H", tab["rgt_desc"])
        self.assertEqual(desc[1], 20 + 0x1F758 - 0x1F60E)        # script 1: $1F758
        self.assertEqual(desc[34], 20)                             # script 34: $1F60E
        self.assertEqual((desc[0], desc[14], desc[23]), (0xFFFF, 0xFFFF, 0xFFFF))
        code = tab["rgt_frcode"]
        self.assertEqual(len(code), 526)
        self.assertEqual(code[:10], bytes.fromhex("000018ffffff1400c001"))   # $1EB46-$1F46D swapped
        self.assertEqual(code[10 + (6 ^ 1)], 0xFF)                           # position 6 locked
        self.assertEqual(code[20 + (0 ^ 1)], 0)                              # $1F60E +0: position 0
        self.assertEqual(struct.unpack_from("<H", code, 20 + 12)[0], 0x0783)  # $1F60E +$C: BLTSIZE
        self.assertEqual(struct.unpack("<5H", tab["rgt_rise_size"][:10]), (0x405, 0x805, 0xC05, 0x1185, 0x1605))
        self.assertEqual(struct.unpack("<2H", tab["rgt_walk_gfx"][:4]), (0x0003, 0x3C22))
        self.assertEqual(list(tab["rgt_fx_first"]) + list(tab["rgt_fx_end"]), [0, 0, 4, 8, 16, 4, 4, 8, 12, 22])
        pics = tab["rgt_pics"]
        key, hi, sx, sy, tx, ty, w, h, m = struct.unpack_from("<HBBHBBBBH", pics, 12 * 13)
        self.assertEqual((hi << 16 | key, sx, sy, tx, ty, w, h), (0x30C82, 0, 162, 3, 0, 57, 88))
        self.assertEqual(rg.hit[m:m + 8], self.data[0x30C82 - 0x1EA00:0x30C8A - 0x1EA00])
        self.assertEqual(struct.unpack_from("<HBBBBH", tab["rgt_places"], 8 * 3), (126, 99, 27, 29, 0, 901))

    def test_bad_data_is_refused(self):
        def poke(addr, *values):
            d = bytearray(self.data)
            d[addr - 0x1EA00:addr - 0x1EA00 + len(values)] = bytes(values)
            return bytes(d)

        cases = {
            "a palette colour": (poke(0x1FBEA + 1, 0x76), "visit 1's palette"),
            "a slide's passes": (poke(0x1F60E + 7, 15), r"descriptor \$1F60E"),
            "a walker's clip": (poke(0x1F268 + 1, 0xB0), "walkers' tables"),
            "an effect's type": (poke(0x1EF88 + 8 + 5, 2), "script 1 "),
            "a stub": (poke(0x1F472, 0x43), r"stub \$1F472"),
            "the lock": (poke(0x1F502 + 6, 0), r"code state at \$1F502"),
            "the 6th plane": (poke(0x466C2, self.data[0x466C2 - 0x1EA00] ^ 1), "6th plane sets"),
            "its tail": (poke(0x481A2, 0), r"\$481A2"),
            "a dissolve frame": (poke(0x1F974 + 2, 5), "first and end"),
            "the size": (self.data[:-1], "bytes"),
        }
        for what, (data, msg) in cases.items():
            with self.subTest(what), self.assertRaisesRegex(ValueError, msg):
                msxrange.Range(data, sweep=False)

    def test_inc_equates(self):
        e = equates(self.rg.inc_text())
        want = {"RG_TOP": 10, "RG_VIEW_H": 162, "RG_CAM_MAX": 64, "RG_CAM_START": 32, "RG_LINE_DX": 111,
                "RG_SHIFT_MIN": -7, "RG_SHIFT_MAX": 8, "RG_SCENE_Y": 512, "RG_STRIP_Y": 674, "RG_STRIP_X2": 64,
                "RG_S0_LINES": 88, "RG_S1_LINES": 89, "RG_S2_X": 128, "RG_S2_LINES": 87, "RG_S3_Y": 856,
                "RG_S3_LINES": 74, "RG_LINE_VRAM": 0x1D800, "RG_SAT_A": 0x1E200, "RG_SAT_B": 0x1E600,
                "RG_GFX_LEN": 63616, "RG_GFX_STRIP_OFS": 20736, "RG_GFX_STRIP_VRAM": 0x15100,
                "RG_GFX_S0_OFS": 25920, "RG_GFX_S1_OFS": 37184, "RG_GFX_S2_OFS": 48576, "RG_GFX_S2_BPL": 64,
                "RG_GFX_S2_VRAM": 0x15140, "RG_GFX_S3_OFS": 54144, "RG_GFX_S3_VRAM": 0x1AC00, "RG_PICS": 37,
                "RG_PIC_LEN": 12, "RG_PIC_30C82": 13, "RG_PIC_3CFE2": 36, "RG_PLACE3_X": 126, "RG_PLACE3_FY": 901,
                "RG_PLACE8_FX": 0, "RG_C_SHEET": 1, "RG_C_GREEN": 15, "RG_GREEN_FILL": 255, "RG_SPR_LINES": 158,
                "RG_SIDE_TOP": -2, "RG_HIT_MASKS": 8192, "RG_HIT_LEN": 13088, "RG_HIT_USED": 11776,
                "RG_BLITS_MAX": 18, "RG_BLITS_ROOM": 242, "RG_NONE": 255, "RG_ST_LEN": 35, "RG_ST_CROSS": 26,
                "RG_BIG_CLIP": 5, "RG_FC_LEN": 526, "RG_FC_1F60E": 20, "RG_FC_LOCKS": 10, "RG_K_RISE": 3}
        self.assertEqual({k: e[k] for k in want}, want)

    def test_blit_bound(self):
        sizes = self.rg.sizes
        self.assertEqual(list(sizes), [120, 160, 180, 192, 224, 240, 256, 288, 320, 336, 360, 384, 448, 480, 512,
                                       560, 700, 880])
        self.assertEqual(sizes[120], {"pop-ups"})                      # 16 x 30: 2 words x 30
        self.assertEqual(sizes[700], {"the riser"})                    # 64 x 70: 5 words x 70
        self.assertEqual(sizes[880], {"the riser", "the dissolves"})   # 64 x 88
        self.assertIn("the walkers", sizes[224])                       # 64 x 56 clipped to 2 words
        self.assertLessEqual(len(sizes) * 13, msxrange.BLITS_ROOM)     # room for entries up to 13 bytes

    def test_quirk4_and_the_sweep(self):
        rg = self.rg
        self.assertEqual([(a, q) for a, ks, q, cols in rg.quirk4],
                         [(0x1F6A8, 3), (0x1F6D4, 3), (0x1F6EA, 1), (0x1F716, 5), (0x1F72C, 5), (0x1F7C6, 5),
                          (0x1F7F2, 3)])
        rep = rg.sweep_report
        self.assertEqual({k: v[0] for k, v in rep.items()},
                         {"pop-up steps": 347, "riser cases": 240, "walker cases": 160, "dissolve cases": 54,
                          "mixed moments": 39, "full moments": 7, "quirk 4 pairs": 156})
        self.assertEqual({v[1] for v in rep.values()}, {0})
        self.assertGreater(rep["quirk 4 pairs"][2], 0)

    def test_state_round_trip(self):
        for name, st in self.rg.moments():
            b = st.to_bytes()
            self.assertEqual(len(b), 35)
            self.assertEqual(msxrange.State.from_bytes(b).__dict__, st.__dict__, name)
        empty = msxrange.State(16, 20)
        self.assertEqual(empty.to_bytes(), bytes([16, 20] + [255] * 24 + [0] * 4 + [255] * 5))
        self.assertEqual(msxrange.State.from_bytes(empty.to_bytes()).__dict__, empty.__dict__)

    def test_render_of_nothing_is_the_scene(self):
        rg = self.rg
        for c, s in ((0, 0), (16, 8), (64, 57)):
            pic, page = rg.shown(msxrange.State(c, s))
            self.assertEqual([bytes(r) for r in page], [r[c:c + 256] for r in rg.scene])
            shift = c - s
            self.assertEqual([bytes(r[shift:]) for r in pic], [r[c:c + 256 - shift] for r in rg.scene])
            self.assertTrue(all(r[:shift] == bytes(shift) for r in pic))
        with self.assertRaisesRegex(ValueError, "R#18 cannot"):
            rg.shown(msxrange.State(0, 8))

    def test_render_draws_one_pop_up_in_its_rectangle(self):
        rg = self.rg
        e = rg.desc[0x1F67C]                                    # position 3, sliding horizontally
        base, _ = rg.shown(msxrange.State(64, 64))
        for X, Y in e["pos"]:
            st = msxrange.State(64, 64, [(3, rg.pic_index[e["ptr"]], X, Y), None])
            pic, _ = rg.shown(st)
            changed = {(x + 64, y + 10) for y in range(162) for x in range(256) if pic[y][x] != base[y][x]}
            x0, y0, w, h = rg.places[3]
            self.assertTrue(all(x0 <= x < x0 + w and y0 <= y < y0 + h for x, y in changed), (X, Y))
            self.assertEqual(rg.compare(st), (0, 0))

    def test_render_sprites_and_r18(self):
        rg = self.rg
        st = msxrange.State(32, 32, cross=(240, 130), box=(4, (240 + 4) & 0xFFF0, 130))
        sat = rg.sat(st)
        self.assertEqual(len(sat), 10 + 2 * 7)                  # the sides: rows 66-193, to row 167: lines 56-157
        self.assertEqual({x for _, x, _ in sat}, {240 - 111 - 32, 240 - 64 - 113 - 32, 240 + 64 - 113 - 32})
        self.assertEqual(sat[10], (55, 31, 15))
        pic, page = rg.shown(st)
        self.assertEqual(pic[0][97], 15)                           # the line at x cx - s, from line 0
        self.assertEqual(bytes(page[120]), bytes([15]) * 256)      # the crosshair's row, line 130 - 10
        self.assertEqual(bytes(page[56][32:160]), bytes([15]) * 128)   # the box's top edge, row 66
        self.assertNotEqual(page[56][31], 15)
        self.assertEqual((pic[56][31], pic[119][159], pic[120][31]), (15, 15, 15))
        moved, _ = rg.shown(st, 25)                                # R#18 = 9: 7 pixels right
        self.assertEqual([r[7:] for r in moved], [r[:249] for r in pic])
        self.assertTrue(all(r[:7] == bytes(7) for r in moved))
        st.box = (4, (240 + 4) & 0xFFF0, 61)                     # Y - 16n = -3: the sides hidden
        self.assertEqual(len(rg.sat(st)), 10)
        st.box = (4, (240 + 4) & 0xFFF0, 62)                     # -2: shown, lines 0-115
        self.assertEqual(len(rg.sat(st)), 10 + 2 * 8)

    def test_moments_equal_the_original(self):
        for name, st in self.rg.moments():
            self.assertEqual(self.rg.compare(st), (0, 0), name)

    def test_msx_inc_agrees(self):
        text = (ROOT / "msx" / "msx.inc").read_text()

        def value(name):
            return int(re.search(rf"^{name}:\s+equ\s+(\S+)", text, re.M).group(1), 0)

        self.assertEqual((value("SPR_PAT"), value("SPR_COL_A"), value("SPR_COL_B"), value("VIEW_LINES")),
                         (msxrange.SPR_PAT, msxrange.SPR_COL_A, msxrange.SPR_COL_B, msxrange.VIEW_H))

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "range"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(msxrange.main(["msxrange.py", str(FRNG), str(out)]), 0)
            for name, size in (("range_1.pal", 32), ("range_2.pal", 32), ("range_gfx.bin", 63616),
                               ("range_hit.bin", 13088), ("range_line.spr", 512)):
                self.assertEqual((Path(d) / name).stat().st_size, size, name)
            self.assertEqual((Path(d) / "range_gfx.bin").read_bytes(), self.rg.blob)
            self.assertEqual((Path(d) / "range_tab.inc").read_text(), self.rg.tab_text())
            for name in ("range.inc", "range_scene.png", "range_vram.png", "range_s32_plain.png",
                         "range_s0_graded.png", "range_s64_v2_graded.png", "range_amiga_vs_msx.png"):
                self.assertTrue((Path(d) / name).exists(), name)
            st = self.rg.moments()[2][1]
            ram = Path(d) / "ram.bin"
            ram.write_bytes(bytes(16) + bytes(35) + st.to_bytes())
            sat = Path(d) / "sat.bin"
            sat.write_bytes(msxrange.sat_bytes(self.rg.sat(st)) + bytes(64))
            r = Path(d) / "r"
            with contextlib.redirect_stdout(io.StringIO()):
                msxrange.main(["msxrange.py", "render", str(FRNG), str(ram), str(r), "--offset", "16", "--page", "1",
                               "--r18", "9", "--sat", str(sat)])
            pic, page = self.rg.shown(st, 57)
            self.assertEqual((Path(d) / "r.sc5").read_bytes(), msxrange.pack(pic))
            self.assertEqual((Path(d) / "r_page.sc5").read_bytes(), msxrange.pack(page))
            self.assertEqual((Path(d) / "r.sat").read_bytes(), msxrange.sat_bytes(self.rg.sat(st)))
            self.assertTrue((Path(d) / "r.png").exists())
            with contextlib.redirect_stdout(io.StringIO()):
                msxrange.main(["msxrange.py", "render", str(FRNG), st.to_bytes().hex(), str(r), "--hex"])
            self.assertEqual((Path(d) / "r.sc5").read_bytes(), msxrange.pack(self.rg.shown(st)[0]))

    @unittest.skipUnless(shutil.which("z80asm"), "z80asm not installed")
    def test_includes_assemble(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "range.inc").write_text(self.rg.inc_text())
            (Path(d) / "range_tab.inc").write_text(self.rg.tab_text())
            (Path(d) / "t.asm").write_text('        org 0xA000\n        include "range.inc"\n'
                                           '        include "range_tab.inc"\n        db RG_ST_LEN, RG_SIDE_TOP & 255\n')
            r = subprocess.run(["z80asm", "-o", "t.bin", "t.asm"], cwd=d, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout + r.stderr), (0, ""))
            tab = parse_data(self.rg.tab_text())
            self.assertEqual((Path(d) / "t.bin").read_bytes(), b"".join(tab.values()) + bytes([35, 254]))


if __name__ == "__main__":
    unittest.main()
