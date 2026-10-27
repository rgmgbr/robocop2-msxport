"""tools/msxpuzl.py: Brainstorm's graphics and tables (docs/BRAINSTORM.md 3.3 and 3.9)."""
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
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import msxpuzl  # noqa: E402

PUZL = ROOT / "build" / "extracted" / "files" / "PUZL_25.bin"     # make extract
# sha256 of the graphics report's prototype outputs (2026-10-26), the acceptance of the converter
PROTOTYPE = {
    "screen": "7e86cb112d15a0b206a797d4dd5bb59fb9528e1989426c18ae678d3701d1c939",
    "sheet": "cd2c9ccb40b3ef64a3c3ea32957f3f3a5891f1995fc6a7155c45e998447fdb8b",
    "tv1": "19553bb240ddaf90b0e562c63e0ff6e3a7c8f2494b28193446525b9acdbfc4d8",
    "tv2": "dcb2e6dc93a5bcdc9a101993060dbd08191a225b6f932f5892f3106744322a8d",
    "cursor": "0459975327174b36b403de1482d227b0352d6a2193e6727d0b83c7252e0486b4",
    "pal1": "003a10a8c9cbf59b13fc6c9d80a8560b74fd334621617ad8e768bd6647e9c552",
    "pal2": "0eafaca32b12136160d01ed152c931f201d2097a3a8d27e6465ed70bdd913b21",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def equates(text: str) -> dict:
    out = {}
    for line in text.splitlines():
        m = re.match(r"^(\w+):\s+equ\s+(\S+)", line)
        if m:
            out[m.group(1)] = int(m.group(2), 0)
    return out


class LayoutTests(unittest.TestCase):
    def test_pieces_fill_the_play_area_once(self):
        msxpuzl.check_pieces()
        self.assertEqual(sum(p[3] * p[4] for p in msxpuzl.PIECES), 256 * 162)

    def test_elements_lie_whole_in_a_piece_at_the_plans_places(self):
        lay = msxpuzl.msx_layout()
        self.assertEqual(len(lay), 88 + 1 + 9 + 3 + 1 + 4 + 4 + 1)
        self.assertEqual(lay[("cell", 0, 0)], (0, 2, 16, 16))
        self.assertEqual(lay[("cell", 10, 7)], (160, 114, 16, 16))
        self.assertEqual(lay[("tv",)], (176, 2, 80, 80))
        self.assertEqual(lay[("light", 3)], (176, 114, 8, 8))
        self.assertEqual(lay[("bar", 2)], (184, 106, 24, 8))
        self.assertEqual(lay[("led", 8)], (128, 138, 8, 16))
        self.assertEqual([lay[("timer", i)][:2] for i in range(3)], [(218, 130), (234, 130), (242, 130)])
        self.assertEqual(lay[("dash",)][:2], (226, 130))
        self.assertEqual(lay[("button",)], (0, 134, 32, 24))

    def test_bad_pieces_are_refused(self):
        def swap(name, *new):
            return [p if p[0] != name else new for p in msxpuzl.PIECES]

        board_split = [p for p in msxpuzl.PIECES if p[0] != "board"]
        board_split += [("board_a", 16, 14, 100, 130, 0, 0), ("board_b", 116, 14, 76, 130, 100, 0)]
        cases = {
            "a hole": (swap("timer", "timer", 280, 144, 38, 32, 218, 130), "empty"),
            "an overlap": (swap("speaker", "speaker", 162, 144, 36, 32, 142, 130), "overlap"),
            "a cut cell": (board_split, "lies whole in 0 pieces"),
            "a moved TV": (swap("tv", "tv", 224, 12, 80, 90, 176, 0), "the plan's"),
        }
        for what, (pieces, msg) in cases.items():
            with self.subTest(what), mock.patch.object(msxpuzl, "PIECES", pieces):
                with self.assertRaisesRegex(ValueError, msg):
                    msxpuzl.msx_layout()

    def test_shown_state_layout(self):
        self.assertEqual(msxpuzl.ST, {"tv": 0, "led": 1, "timer": 10, "button": 13, "light": 14, "bar": 18,
                                      "cell": 22})
        self.assertEqual(msxpuzl.ST_LEN, 110)
        self.assertEqual(msxpuzl.NONE, 0xFF)
        state = bytearray([msxpuzl.NONE] * 110)
        state[msxpuzl.ST["led"] + 4] = 10                     # no digit 10
        with self.assertRaises(ValueError):
            list(msxpuzl.state_items(bytes(state)))
        with self.assertRaises(ValueError):
            list(msxpuzl.state_items(bytes(109)))

    def test_sheet_and_tv_slots(self):
        msxpuzl.check_sheet_slots()
        self.assertEqual(msxpuzl.sheet_slot("chip", 17), (16, 178, 16, 16))
        self.assertEqual(msxpuzl.sheet_slot("digit", 9), (72, 194, 8, 16))
        self.assertEqual(msxpuzl.sheet_slot("light", 1), (88, 194, 8, 8))
        self.assertEqual(msxpuzl.sheet_slot("bar", 1), (120, 194, 24, 8))
        self.assertEqual(msxpuzl.sheet_slot("button", 1), (176, 194, 32, 24))
        self.assertEqual(msxpuzl.tv_slot(0), (0, 512, 80, 80))
        self.assertEqual(msxpuzl.tv_slot(8), (160, 672, 80, 80))     # page 2 lines 160-239

    def test_pack_and_unpack(self):
        rows = [[x % 16 for x in range(16)], [15 - x % 16 for x in range(16)]]
        packed = msxpuzl.pack(rows)
        self.assertEqual(packed[:2], bytes([0x01, 0x23]))
        self.assertEqual(msxpuzl.unpack(packed, 16), rows)

    def test_parse_data(self):
        text = "a:  ; x\n        db 0x01, 2\n        dw 0x0102, 3 ; y\nb:\n        db 7\n"
        self.assertEqual(msxpuzl.parse_data(text), {"a": bytes([1, 2, 2, 1, 3, 0]), "b": bytes([7])})


@unittest.skipUnless(PUZL.exists(), "PUZL_25.bin not extracted (make extract)")
class PuzlDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = PUZL.read_bytes()
        cls.p = msxpuzl.Puzl(cls.data)           # every check of the converter runs here

    def test_outputs_equal_the_prototype(self):
        p = self.p
        self.assertEqual(sha(p.screen), PROTOTYPE["screen"])
        self.assertEqual(sha(p.sheet), PROTOTYPE["sheet"])
        self.assertEqual(sha(p.tv[1]), PROTOTYPE["tv1"])
        self.assertEqual(sha(p.pats), PROTOTYPE["cursor"])
        self.assertEqual(sha(msxpuzl.v9938(p.pal[1])), PROTOTYPE["pal1"])
        self.assertEqual(p.blob, p.screen + p.sheet + p.tv[1])
        self.assertEqual(len(p.blob), 56704)

    def test_tables(self):
        tab = msxpuzl.parse_data(self.p.tab_text())
        self.assertEqual(tab["pzt_recs"], self.data[0x17448 - 0x17100:0x17760 - 0x17100])
        self.assertEqual(len(tab["pzt_recs"]), 792)
        words = {k: list(struct.unpack(f"<{len(v) // 2}H", v)) for k, v in tab.items() if k != "pzt_recs"}
        self.assertEqual(words["pzt_curofs"], [0x40 * i for i in (0, 1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 1, 0, 0)])
        self.assertEqual(words["pzt_masks"], [7, 3, 1, 0, 0])
        self.assertEqual(words["pzt_shifts"], [1, 1, 1, 2, 0])
        self.assertEqual(words["pzt_ledthr"], [0, 3, 6, 8, 10])
        self.assertEqual(words["pzt_ledval"], [0, 1, 8, 6, 4, 5, 4, 7, 2, 4, 8, 5, 3, 0, 2, 6])
        self.assertEqual(words["pzt_rows"], [0, 1, 2, 3, 3, 2, 1, 0])
        recs = tab["pzt_recs"]
        for b, reds in enumerate((22, 21, 24, 28, 23, 21, 24, 28)):
            r = recs[94 * b:94 * (b + 1)]
            self.assertEqual(r[2], reds)
            self.assertEqual(sum(1 for c in r[6:] if c & 15 == 0), reds)
            self.assertEqual(tuple(r[:2]), (0, 0) if b < 4 else (5, 3))
        self.assertEqual(recs[752:761], b"TIMEOUTe\xff")

    def test_bad_data_is_refused(self):
        def poke(addr, *values):
            d = bytearray(self.data)
            d[addr - 0x17100:addr - 0x17100 + len(values)] = bytes(values)
            return bytes(d)

        cases = {
            "a red-chip count": (poke(0x17448 + 2, 23), "red chips"),
            "a cell of type 0 more": (poke(0x17448 + 7, 0x00), "type-0 cells"),
            "a cell of type 15": (poke(0x17448 + 7, 0x0F), "type 15"),
            "an LED threshold": (poke(0x17972 + 3, 4), r"\$17972"),
            "a light row": (poke(0x17ADE + 3, 0x41), r"\$17ADE"),
            "a message": (poke(0x17741, ord("X")), r"\$17741"),
            "a palette colour": (poke(0x17D6A + 1, 0x23), "palette"),
            "the size": (self.data[:-1], "bytes"),
        }
        for what, (data, msg) in cases.items():
            with self.subTest(what), self.assertRaisesRegex(ValueError, msg):
                msxpuzl.Puzl(data)

    def test_inc_equates(self):
        e = equates(self.p.inc_text())
        want = {"PZ_CELL_X": 0, "PZ_CELL_Y": 2, "PZ_TV_X": 176, "PZ_TV_Y": 2, "PZ_LIGHT_X": 176, "PZ_BAR_X": 184,
                "PZ_ROW_Y": 90, "PZ_LED_X": 64, "PZ_LED_Y": 138, "PZ_TMIN_X": 218, "PZ_TTEN_X": 234,
                "PZ_TUNIT_X": 242, "PZ_TIMER_Y": 130, "PZ_BUTTON_X": 0, "PZ_BUTTON_Y": 134, "PZ_SAT_Y": 1,
                "PZ_CHIP_SY": 162, "PZ_DIGIT_SY": 194, "PZ_BUTTON_SX": 144, "PZ_TV5_SX": 160, "PZ_TV5_SY": 592,
                "PZ_TV_VRAM": 0x10000, "PZ_GFX_SHEET": 20736, "PZ_GFX_PAGE0": 27904, "PZ_GFX_TV1": 27904,
                "PZ_GFX_TV2": 27904, "PZ_GFX_LEN": 56704, "PZ_VISITS": 1, "PZ_CUR_PATS": 9, "PZ_CURA_3": 4,
                "PZ_CURB_2": 3, "PZ_CURB_0": 255, "PZ_CUR_COL_1": 15, "PZ_CUR_COL2_1": 14, "PZ_CUR_COL_2": 15,
                "PZ_ST_CELL": 22, "PZ_ST_LEN": 110, "PZ_ST_NONE": 255, "PZ_RECS_V2": 376,
                "PZ_RECS_LEN_V1": 792, "PZ_RECS_LEN_V2": 416, "PZ_BOARDS_LEN": 376, "PZ_MSG_RESTORED": 774}
        self.assertEqual({k: e[k] for k in want}, want)

    def test_render_of_nothing_is_the_screen(self):
        img = self.p.render(bytes([msxpuzl.NONE] * 110))
        self.assertEqual(msxpuzl.pack(img), self.p.screen)
        self.assertTrue(all(v == 0 for r in img[2:82] for v in r[176:256]))    # the TV black

    def test_render_draws_one_element_whole(self):
        base = self.p.render(bytes([msxpuzl.NONE] * 110))
        state = bytearray([msxpuzl.NONE] * 110)
        state[msxpuzl.ST["timer"] + 2] = 7                    # the seconds: digit 7
        img = self.p.render(bytes(state))
        changed = {(x, y) for y in range(162) for x in range(256) if img[y][x] != base[y][x]}
        self.assertTrue(changed)
        self.assertTrue(all(242 <= x < 250 and 130 <= y < 146 for x, y in changed))
        sheet = msxpuzl.unpack(self.p.sheet, 256)
        self.assertEqual([r[242:250] for r in img[130:146]], [r[56:64] for r in sheet[32:48]])

    def test_render_cursor(self):
        none = bytes([msxpuzl.NONE] * 110)
        base = self.p.render(none)
        img = self.p.render(none, (3, 2, 0))                  # image 0: the whole 16 x 16 square's edge
        changed = {(x, y) for y in range(162) for x in range(256) if img[y][x] != base[y][x]}
        self.assertTrue(all(48 <= x < 64 and 34 <= y < 50 for x, y in changed))
        self.assertEqual(img[34][48:64], [15] * 16)
        self.assertEqual(img[49][48:64], [15] * 16)
        img = self.p.render(none, (0, 0, 2))                  # image 2: sprite 1's two pixels in colour 14
        self.assertEqual(sum(r[0:16].count(14) for r in img[2:18]) - sum(r[0:16].count(14) for r in base[2:18]), 2)

    def test_visit_2_ready(self):
        p2 = msxpuzl.Puzl(self.data, (1, 2))
        self.assertEqual((p2.screen, p2.sheet, p2.tv[1]), (self.p.screen, self.p.sheet, self.p.tv[1]))
        self.assertEqual(sha(p2.tv[2]), PROTOTYPE["tv2"])
        self.assertEqual(sha(msxpuzl.v9938(p2.pal[2])), PROTOTYPE["pal2"])
        self.assertEqual(len(p2.blob), 56704 + 28800)
        e = equates(p2.inc_text())
        self.assertEqual((e["PZ_GFX_TV2"], e["PZ_VISITS"], e["PZ_CUR_COL_2"]), (56704, 2, 14))

    def test_command_line(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "puzl"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(msxpuzl.main(["msxpuzl.py", str(PUZL), str(out)]), 0)
            for name, size in (("puzl_1.pal", 32), ("puzl_gfx.bin", 56704), ("puzl_cursor.spr", 288)):
                self.assertEqual((Path(d) / name).stat().st_size, size, name)
            for name in ("puzl.inc", "puzl_tab.inc", "puzl_1_display_plain.png", "puzl_1_display_graded.png",
                         "puzl_1_amiga_vs_msx.png", "puzl_1_screen.png", "puzl_1_sheet.png", "puzl_1_tv.png",
                         "puzl_cursor.png"):
                self.assertTrue((Path(d) / name).exists(), name)
            state = bytearray([msxpuzl.NONE] * 110)
            state[0] = 8
            ram = Path(d) / "ram.bin"
            ram.write_bytes(bytes(16) + state)
            with contextlib.redirect_stdout(io.StringIO()):
                msxpuzl.main(["msxpuzl.py", "render", str(PUZL), str(ram), str(Path(d) / "r"), "--offset", "16",
                              "--cursor", "1,1,4"])
            self.assertEqual(msxpuzl.pack(self.p.render(bytes(state), (1, 1, 4))),
                             (Path(d) / "r.sc5").read_bytes())
            self.assertTrue((Path(d) / "r.png").exists())

    @unittest.skipUnless(shutil.which("z80asm"), "z80asm not installed")
    def test_includes_assemble(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "puzl.inc").write_text(self.p.inc_text())
            (Path(d) / "puzl_tab.inc").write_text(self.p.tab_text())
            (Path(d) / "t.asm").write_text('        org 0xA000\n        include "puzl.inc"\n'
                                           '        include "puzl_tab.inc"\n        db PZ_ST_LEN\n')
            r = subprocess.run(["z80asm", "-o", "t.bin", "t.asm"], cwd=d, capture_output=True, text=True)
            self.assertEqual((r.returncode, r.stdout + r.stderr), (0, ""))
            tab = msxpuzl.parse_data(self.p.tab_text())
            self.assertEqual((Path(d) / "t.bin").read_bytes(), b"".join(tab.values()) + bytes([110]))


if __name__ == "__main__":
    unittest.main()
