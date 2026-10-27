"""Brainstorm's texts (tools/msxtext.py) and its HUD messages (tools/msxhudrt.py): the scripts
as the port holds them, their counts and their place on the screen, and the messages appended
without moving anything of level 1's."""
import contextlib
import io
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hudmodel  # noqa: E402
import msxhudrt  # noqa: E402
import msxtext  # noqa: E402
import rc2front  # noqa: E402

RAM = ROOT / "build" / "ram" / "level1_full.bin"            # tools/ramimage.py (make ram)
FILES = ROOT / "build" / "extracted" / "files"              # tools/rc2files.py (make extract)
HUD_INPUTS = (FILES / "PERMA_05.bin", ROOT / "build" / "extracted" / "boot" / "main_8000.bin",
              FILES / "PUZL_25.bin")
LINE = 128                                                  # SCREEN 5 bytes a line


def equates(inc: str) -> dict[str, int]:
    return {k: int(v, 0) for k, v in re.findall(r"^(\w+):\s+equ (\S+)", inc, re.M)}


def cells(script: bytes) -> list[tuple[int, int, int]]:
    """(first byte, first line, character code) of each character of a script of lines."""
    out = []
    for col, row, chars in msxtext.script_lines(script)[0]:
        out += [((8 * (col + i) - 16) // 2, 67 + 8 * row, c) for i, c in enumerate(chars)]
    return out


class FsModelTests(unittest.TestCase):
    """The model of msx/front.asm fs_step / fs_char, on scripts made up here."""

    def test_glyph_codes_as_the_amiga(self):
        # fs_char maps a code as $118D6 does; a code outside the font stays outside
        for code in range(1, 0x80):
            g = rc2front.bitmap_glyph(code)
            if 0 <= g < rc2front.BITMAP_GLYPHS:
                self.assertEqual(msxtext.fs_glyph(code), g, hex(code))
            else:
                self.assertGreaterEqual(msxtext.fs_glyph(code), rc2front.BITMAP_GLYPHS, hex(code))

    def test_cells_at_8c_minus_16_and_67_plus_8r(self):
        glyphs = [bytes([g + 1]) * 32 for g in range(rc2front.BITMAP_GLYPHS)]
        script = b"\x00\x02\x00A\x00\x21\x0aZ\xff\x07"     # column 2 row 0, column 33 row 10
        area = msxtext.fs_render(glyphs, script)
        self.assertEqual(len(area), msxtext.VIEW_LINES * LINE)
        want = bytearray(len(area))
        for b, y, g in ((0, 67, 0), (124, 147, 25)):        # x 0 and x 248: bytes 0 and 124
            for k in range(8):
                want[(y + k) * LINE + b:(y + k) * LINE + b + 4] = bytes([g + 1]) * 4
        self.assertEqual(area, bytes(want))

    def test_calls_and_elements(self):
        # positions and characters 1 call each, a wait FF 02 n max(1, 4n), the end none
        self.assertEqual(msxtext.fs_run(b"\x00\x02\x00AB\xff\x02\x00\xff\x02\x03\xff\x07")[:2], (3, 3 + 1 + 12))

    def test_lines_must_fit_the_play_area(self):
        msxtext.check_bonus("t", b"\x00\x02\x03" + b"A" * 32 + b"\xff\x07", 33)     # x 0-255
        for bad in (b"\x00\x02\x03" + b"A" * 33 + b"\xff\x07",                     # x 0-263
                    b"\x00\x01\x03A\xff\x07",                                       # x -8
                    b"\x00\x02\x0bA\xff\x07",                                       # lines 155-162
                    b"\x00\x02\x03@\xff\x07",                                       # '@': no glyph
                    b"\x00\x02\x03A\xff\x03\xff\x07",                               # command 3
                    b"\x00\x02\x03A\xff\x02\x01"):                                  # no end
            with self.assertRaises(AssertionError, msg=bad):
                msxtext.check_bonus("t", bad, msxtext.fs_run(bad + b"\xff\x07")[1])

    def test_view_lines_as_msx_inc(self):
        inc = (ROOT / "msx" / "msx.inc").read_text()
        self.assertEqual(int(re.search(r"^VIEW_LINES:\s+equ (\d+)", inc, re.M)[1]), msxtext.VIEW_LINES)


@unittest.skipUnless(RAM.exists(), "level 1's RAM image not built (make ram)")
class BonusTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ram = RAM.read_bytes()
        cls.scripts = {label: (start, s) for label, start, s in msxtext.bonus_scripts(cls.ram)}

    def test_intro_split_over_two_rows(self):
        self.assertEqual(self.scripts["txt_bs_intro"][1],
                         b"\x00\x0d\x00BRAINSTORMe"
                         b"\x00\x08\x03DESTROY ALL RED CHIPS"
                         b"\x00\x0d\x04ON THE BOARD"
                         b"\x00\x05\x06COMPLETE _ TO REGAIN MEMORYe"
                         b"\x00\x07\x08AND EARN A GAME CREDITe"
                         b"\xff\x02\x30\xff\x07")

    def test_results_are_the_originals(self):
        for label, size in (("txt_bs_ok", 56), ("txt_bs_fail", 49), ("txt_bs_time", 42)):
            start, s = self.scripts[label]
            self.assertEqual(len(s), size, label)
            self.assertEqual(s, self.ram[start:start + size], label)

    def test_elements_and_calls(self):
        # the original's: the intro 4 + 96 elements and 292 calls; the results 143, 136, 129
        self.assertEqual(msxtext.fs_run(msxtext.bonus_script(self.ram, 0x114AA))[:2], (100, 292))
        self.assertEqual({k: msxtext.fs_run(s)[:2] for k, (_, s) in self.scripts.items()},
                         {"txt_bs_intro": (100, 292), "txt_bs_ok": (47, 143), "txt_bs_fail": (40, 136),
                          "txt_bs_time": (33, 129)})

    def test_lines_inside_the_play_area(self):
        for label, (_, s) in self.scripts.items():
            lines, tail = msxtext.script_lines(s)
            self.assertEqual(tail[:2] + tail[3:], b"\xff\x02\xff\x07", label)
            for col, row, chars in lines:
                self.assertGreaterEqual(8 * col - 16, 0, label)
                self.assertLessEqual(8 * (col + len(chars)) - 17, 255, label)
                self.assertLessEqual(67 + 8 * row + 7, msxtext.VIEW_LINES - 1, label)

    def test_play_areas(self):
        # each character's glyph (txt_glyphs) in its cell, every other byte 0 (fs_clear)
        glyphs = [msxtext.glyph_sc5(self.ram, g) for g in range(rc2front.BITMAP_GLYPHS)]
        for label, (_, s) in self.scripts.items():
            want = bytearray(msxtext.VIEW_LINES * LINE)
            for b, y, c in cells(s):
                g = glyphs[msxtext.fs_glyph(c)]
                for k in range(8):
                    want[(y + k) * LINE + b:(y + k) * LINE + b + 4] = g[4 * k:4 * k + 4]
            self.assertEqual(msxtext.fs_render(glyphs, s), bytes(want), label)
        # "BRAINSTORM.": 'B' at x 88 of lines 67-74
        area = msxtext.fs_render(glyphs, self.scripts["txt_bs_intro"][1])
        self.assertEqual(b"".join(area[(67 + k) * LINE + 44:(67 + k) * LINE + 48] for k in range(8)), glyphs[1])

    def test_text_inc_appends_the_scripts(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            out = Path(d) / "text.inc"
            self.assertEqual(msxtext.main(["msxtext.py", str(RAM), str(out)]), 0)
            text = out.read_text()
            for label in self.scripts:
                area = (Path(d) / (label.replace("txt_", "text_") + ".sc5")).read_bytes()
                self.assertEqual(len(area), 256 * 162 // 2, label)
                self.assertTrue((Path(d) / (label.replace("txt_", "text_") + ".png")).exists(), label)
        level = msxtext.level_inc(self.ram)
        self.assertTrue(text.startswith(level))         # (the level statistics' part as before)
        rest = text[len(level):]
        self.assertEqual([m for m in re.findall(r"^(\w+):", rest, re.M)], list(self.scripts))
        for label, (_, s) in self.scripts.items():
            body = rest.split(label + ":")[1].split("\n", 1)[1]
            data = []
            for ln in body.splitlines():
                if not ln.startswith("        db "):
                    break
                data += [int(v, 0) for v in ln[11:].split(", ")]
            self.assertEqual(bytes(data), s, label)


@unittest.skipUnless(all(p.exists() for p in HUD_INPUTS), "game files not extracted (make extract)")
class BonusMessageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.perma, cls.main, cls.puzl = (p.read_bytes() for p in HUD_INPUTS)
        cls.blob, cls.inc, _ = msxhudrt.build(cls.perma, cls.main, cls.puzl)
        cls.blob1, cls.inc1, _ = msxhudrt.build(cls.perma, cls.main, None)
        cls.eq = equates(cls.inc)

    def text(self, ptr: int) -> bytes:
        return msxhudrt.message(self.blob, ptr - msxhudrt.BASE)

    def game_msg(self, n: int) -> int:
        """msx/hud.asm game_msg: the pointer at HUD_MSGS + 2 n."""
        self.assertTrue(0 <= n <= 255)
        return struct.unpack_from("<H", self.blob, self.eq["HUD_MSGS"] + 2 * n - msxhudrt.BASE)[0]

    def test_level1_bytes_and_numbers_unchanged(self):
        self.assertTrue(self.blob.startswith(self.blob1))
        self.assertTrue(self.inc.startswith(self.inc1))
        eq1 = equates(self.inc1)
        self.assertEqual([eq1[f"HUD_MSG_{a:04X}"] for a in msxhudrt.MESSAGES], list(range(21)))
        self.assertEqual((eq1["HUD_NMSGS"], self.eq["HUD_NMSGS"]), (21, 21))
        self.assertEqual({k: v for k, v in self.eq.items() if k in eq1}, eq1)

    def test_game_msg_reaches_every_message(self):
        for n, a in enumerate(msxhudrt.MESSAGES):
            self.assertEqual(self.text(self.game_msg(n)), msxhudrt.message(self.main, a - 0x8000), hex(a))
        for a, want in msxhudrt.PUZL_MESSAGES:
            m = self.text(self.game_msg(self.eq[f"HUD_MSG_{a:05X}"]))
            self.assertEqual(m, msxhudrt.message(self.puzl, a - 0x17100), hex(a))
            self.assertEqual("".join(rc2front.GLYPH_NAMES[hudmodel.font_index(c)] for c in m[:-1]), want)

    def test_puzl_messages_at_their_offsets(self):
        self.assertEqual([msxhudrt.message(self.puzl, o) for o in (0x638, 0x641, 0x64E)],
                         [b"TIMEOUTe\xff", b"MALFUNCTIONe\xff", b"MEMORY RESTOREDe\xff"])

    def test_glyphs_in_the_hud_font(self):
        for a, _ in msxhudrt.PUZL_MESSAGES:
            for c in msxhudrt.message(self.puzl, a - 0x17100)[:-1]:
                self.assertIn(hudmodel.font_index(c), range(44), hex(a))

    def test_fits_the_hud_banks(self):
        self.assertLessEqual(len(self.blob), 0x4000)
        self.assertGreaterEqual(self.eq["HUD_PZ_MSGS"], 0xA000)        # (HUD_BANK + 1: game_msg maps it)
        self.assertLessEqual(self.eq["HUD_PZ_MSGS"] + 6 + 39, 0xC000)


if __name__ == "__main__":
    unittest.main()
