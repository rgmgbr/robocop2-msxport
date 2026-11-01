"""The bonus stages' texts (tools/msxtext.py) and HUD messages (tools/msxhudrt.py), Brainstorm's
and the shooting range's: the scripts as the port holds them, their counts and their place on the
screen, the range's result for any counts, and the messages appended without moving anything of
level 1's or renumbering Brainstorm's. Also the briefings of levels 2 and 3 and the continue offer
(msxtext.py BRIEF, CONT), appended after the range's texts, everything before them unchanged."""
import contextlib
import hashlib
import io
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import bytekiller  # noqa: E402
import hudmodel  # noqa: E402
import msxhudrt  # noqa: E402
import msxtext  # noqa: E402
import rc2front  # noqa: E402

RAM = ROOT / "build" / "ram" / "level1_full.bin"            # tools/ramimage.py (make ram)
FILES = ROOT / "build" / "extracted" / "files"              # tools/rc2files.py (make extract)
HUD_INPUTS = (FILES / "PERMA_05.bin", ROOT / "build" / "extracted" / "boot" / "main_8000.bin",
              FILES / "PUZL_25.bin", FILES / "FRNG_15.bin")
LINE = 128                                                  # SCREEN 5 bytes a line
# text.inc up to the range's texts (level 1's statistics, Brainstorm's and the range's scripts) as
# a969fc8 built it (build/msx/text.inc): the briefings only append to it
TEXT_INC_A969FC8 = "3d5a464ee87ec9f66c92ea6c4034792ea7e64209230b60f9851eae4aa90f8332"


def equates(inc: str) -> dict[str, int]:
    return {k: int(v, 0) for k, v in re.findall(r"^(\w+):\s+equ (\S+)", inc, re.M)}


def msx_inc(name: str) -> int:
    return int(re.search(rf"^{name}:\s+equ (\S+)", (ROOT / "msx" / "msx.inc").read_text(), re.M)[1], 0)


def rating_68000(correct: int, dummy: int, minutes: int) -> int:
    """$84C2-$84EE as the 68000 runs them, in words (flow report's REA listing): D0 = correct,
    D1 = dummy; s = 6c + 2d - 50 - 3 (d + 4 [minutes = 0]); bpl, divs.w #14, at most 3."""
    w = 0xFFFF
    d0, d1 = correct & w, dummy & w
    d0 = (d0 + d0) & w                      # add.w D0,D0
    d2 = (0x19 - d1 - d0) & w               # moveq #$19,D2; sub.w D1,D2; sub.w D0,D2
    d0 = (d0 - d2 - d2) & w                 # sub.w D2,D0 twice
    if minutes == 0:
        d1 = (d1 + 4) & w                   # tst.b $804A; bne; addq.w #4,D1
    d0 = (d0 - 3 * d1) & w                  # sub.w D1,D0 three times
    if d0 & 0x8000:
        return 0                            # bpl $84E4; moveq #0,D0
    return min(3, d0 // 14)                 # divs.w #14,D0 (high word 0); cmpi.w #3,D0; bmi


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

    def test_fs_buf_as_msx_inc(self):
        # the room front_stats and front_range copy a script with numbers into (fs_ptr follows it)
        self.assertEqual(msx_inc("fs_ptr") - msx_inc("fs_buf"), msxtext.FS_BUF)

    def test_num_field_as_fs_num(self):
        # front.asm fs_num over a blank field: the digits ('[' + digit) from its end back
        for n in list(range(0, 1000)) + [9999, 10000, 32767, 65535]:
            field, v, i = bytearray(b" " * 8), n, 7
            while True:
                field[i], v, i = 0x5B + v % 10, v // 10, i - 1
                if not v:
                    break
            self.assertEqual(msxtext.num_field(n), bytes(field), n)
        self.assertEqual(msxtext.decode(msxtext.num_field(0)), "       0")
        self.assertEqual(msxtext.decode(msxtext.num_field(25)), "      25")
        for bad in (-1, 65536):
            with self.assertRaises(ValueError):
                msxtext.num_field(bad)

    def test_rating_as_the_68000(self):
        cases = [(c, d, m) for c in range(41) for d in range(41) for m in (0, 1, 2)]
        cases += [(c, d, m) for c in (5470, 5475, 10922, 10923, 21845, 65535) for d in (0, 1, 65535) for m in (0, 1)]
        for c, d, m in cases:
            self.assertEqual(msxtext.rg_rating(c, d, m), rating_68000(c, d, m), (c, d, m))
        # the flow report's least correct counts for each rating (dummy 0; timer >= 1:00, < 1:00)
        self.assertEqual([[msxtext.rg_rating(c, 0, m) for c in (0, 10, 11, 12, 13, 14, 15, 16, 17, 18)] for m in (1, 0)],
                         [[0, 0, 1, 1, 2, 2, 2, 3, 3, 3], [0, 0, 0, 0, 1, 1, 2, 2, 2, 3]])
        self.assertEqual(msxtext.rg_rating(10923, 0, 1), 0)     # 6c wraps in 16 bits, as on both CPUs

    def test_tag_line_as_front_asm(self):
        # fe_text: FE_TAG_COL 15 ("TEST n", x 104-151) or 14 ("TEST nn", x 96-151), row 10
        self.assertEqual(msxtext.tag_line(0), b"")
        self.assertEqual(msxtext.tag_line(4), b"\x00\x0f\x0aTEST 4")
        self.assertEqual(msxtext.tag_line(12), b"\x00\x0e\x0aTEST 12")
        for bad in (-1, 100):
            with self.assertRaises(ValueError):
                msxtext.tag_line(bad)

    def test_negative_rows_in_8_bits(self):
        # fs_char's line 67 + 8r in 8 bits: row FDh (-3) at line 43, row F8h (-8) at line 3
        glyphs = [bytes([g + 1]) * 32 for g in range(rc2front.BITMAP_GLYPHS)]
        area = msxtext.fs_render(glyphs, b"\x00\x02\xfdA\x00\x21\xf8Z\xff\x07")
        want = bytearray(len(area))
        for b, y, g in ((0, 43, 0), (124, 3, 25)):
            for k in range(8):
                want[(y + k) * LINE + b:(y + k) * LINE + b + 4] = bytes([g + 1]) * 4
        self.assertEqual(area, bytes(want))
        self.assertEqual([msxtext.s8(v) for v in (0, 0x7F, 0x80, 0xF8, 0xFD, 0xFF)], [0, 127, -128, -8, -3, -1])

    def test_check_text(self):
        # any order of positions, characters and waits; rows -8 to 8 (the TAG line's row 10 free)
        ok = b"\x00\x02\xf8A\xff\x02\x01\x00\x21\x08Z\x00\x21\x08\xff\x02\x00\xff\x07"
        msxtext.check_text("t", ok, msxtext.fs_run(ok)[1])
        for bad in (b"\x00\x02\xf7A\xff\x07",                                       # row -9: line 251
                    b"\x00\x02\x09A\xff\x07",                                       # row 9
                    b"\x00\x02\x0aA\xff\x07",                                       # row 10: the TAG line
                    b"\x00\x01\x00A\xff\x07",                                       # x -8
                    b"\x00\x21\x00AB\xff\x07",                                      # x 256
                    b"\x00\x02\x00A\x00\x02\x00B\xff\x07",                          # a cell written twice
                    b"\x00\x02\x00@\xff\x07",                                       # '@': no glyph
                    b"\x00\x02\x00A\xff\x03\xff\x07",                               # command 3
                    b"\x00\x02\x00A\xff\x07\x00"):                                  # bytes after the end
            with self.assertRaises(AssertionError, msg=bad):
                msxtext.check_text("t", bad, msxtext.fs_run(bad)[1])
        with self.assertRaises(AssertionError):
            msxtext.check_text("t", ok, msxtext.fs_run(ok)[1] + 1)                  # not the original's calls


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
        labels = re.findall(r"^(\w+):", rest, re.M)
        self.assertEqual(labels[:len(self.scripts)], list(self.scripts))    # (the range's after them)
        self.assertTrue(rest.startswith(msxtext.bonus_inc(msxtext.bonus_scripts(self.ram))))
        for label, (_, s) in self.scripts.items():
            body = rest.split(label + ":")[1].split("\n", 1)[1]
            data = []
            for ln in body.splitlines():
                if not ln.startswith("        db "):
                    break
                data += [int(v, 0) for v in ln[11:].split(", ")]
            self.assertEqual(bytes(data), s, label)


def db_data(body: str) -> bytes:
    """The bytes of the db lines at the start of body."""
    data = []
    for ln in body.splitlines():
        if not ln.startswith("        db "):
            break
        data += [int(v, 0) for v in ln[11:].split(", ")]
    return bytes(data)


@unittest.skipUnless(RAM.exists(), "level 1's RAM image not built (make ram)")
class RangeTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ram = RAM.read_bytes()
        cls.scripts = {label: (start, s) for label, start, s in msxtext.range_scripts(cls.ram)}
        cls.names = msxtext.rg_names(cls.ram)
        cls.time = dict((label, s) for label, _, s in msxtext.bonus_scripts(cls.ram))["txt_bs_time"]
        cls.glyphs = [msxtext.glyph_sc5(cls.ram, g) for g in range(rc2front.BITMAP_GLYPHS)]

    def res(self, correct: int, dummy: int, rating: int) -> bytes:
        return msxtext.rg_fill(self.scripts["txt_rg_res"][1], self.names, correct, dummy, rating)

    def want_area(self, script: bytes) -> bytes:
        """Each character's glyph in its cell, every other byte 0 (fs_clear)."""
        want = bytearray(msxtext.VIEW_LINES * LINE)
        for b, y, c in cells(script):
            g = self.glyphs[msxtext.fs_glyph(c)]
            for k in range(8):
                want[(y + k) * LINE + b:(y + k) * LINE + b + 4] = g[4 * k:4 * k + 4]
        return bytes(want)

    def test_intro_split_after_calibration(self):
        # rows 5 and 6, the last line from row 7 to row 8 (the plan's default 4)
        self.assertEqual(self.scripts["txt_rg_intro"][1],
                         b"\x00\x0b\x00SHOOTING RANGEe"
                         b"\x00\x05\x03YOU MUST SHOOT ARMED TARGETS"
                         b"\x00\x09\x05YOUR GUN CALIBRATION"
                         b"\x00\x0c\x06WILL BE TESTED"
                         b"\x00\x04\x08WARNING ACCURACY IS ESSENTIALe"
                         b"\xff\x02\x30\xff\x07")
        lines = msxtext.script_lines(msxtext.bonus_script(self.ram, 0x1142D))[0]
        self.assertEqual([(c, r) for c, r, _ in lines], [(11, 0), (5, 3), (1, 5), (4, 7)])   # the original's

    def test_result_and_names_are_the_originals(self):
        start, s = self.scripts["txt_rg_res"]
        self.assertEqual((start, len(s)), (0x113A5, 104))
        self.assertEqual(s, self.ram[0x113A5:0x113A5 + 104])
        for f in (37, 63, 91):                              # blank: fs_num writes only the digits
            self.assertEqual(s[f:f + 8], b" " * 8, f)
        self.assertEqual(self.names, self.ram[0x1140D:0x1140D + 32])
        self.assertEqual(msxtext.decode(self.names), "POOR.   FAIR.   GOOD.   SHARP.  ")

    def test_elements_and_calls(self):
        # the original's: the intro 4 + 108 elements and 304 calls, the result 347, the time out 129
        self.assertEqual(msxtext.fs_run(msxtext.bonus_script(self.ram, 0x1142D))[:2], (112, 304))
        self.assertEqual({k: msxtext.fs_run(s)[:2] for k, (_, s) in self.scripts.items()},
                         {"txt_rg_intro": (112, 304), "txt_rg_res": (91, 347)})
        self.assertEqual(msxtext.fs_run(self.time)[:2], (33, 129))
        for r in range(4):
            self.assertEqual(msxtext.fs_run(self.res(25, 3, r))[:2], (91, 347), r)

    def test_scripts_fit_fs_buf(self):
        room = msx_inc("fs_ptr") - msx_inc("fs_buf")
        self.assertEqual(room, 120)
        self.assertLessEqual(len(self.scripts["txt_rg_res"][1]), room)
        self.assertLessEqual(len(msxtext.stats_script(self.ram)), room)

    def test_lines_inside_the_play_area_and_row_10_free(self):
        scripts = [self.scripts["txt_rg_intro"][1], self.time] + [self.res(65535, 65535, r) for r in range(4)]
        for s in scripts:
            msxtext.check_bonus("t", s, msxtext.fs_run(s)[1])
            lines, _ = msxtext.script_lines(s)
            self.assertLessEqual(max(r for _, r, _ in lines), 8)            # row 10: the TAG line
        self.assertEqual(max(8 * (c + len(t)) - 17 for c, _, t in msxtext.script_lines(scripts[0])[0]), 255)

    def test_results_for_any_counts(self):
        seen = set()
        for c in range(31):
            for d in range(0, 31, 3):
                for m in (0, 1, 2):
                    r = msxtext.rg_rating(c, d, m)
                    seen.add(r)
                    lines = [msxtext.decode(t) for _, _, t in msxtext.script_lines(self.res(c, d, r))[0]]
                    self.assertEqual(lines, ["GUN CALIBRATION.", f"CORRECT TARGETS{c:>8}", f"DUMMY TARGETS  {d:>8}",
                                             "YOU ARE RATED AS " + msxtext.RG_NAME_TEXT[r]], (c, d, m))
        self.assertEqual(seen, {0, 1, 2, 3})
        self.assertEqual({msxtext.rg_rating(*cdm) for cdm in msxtext.RG_RESULTS}, {0, 1, 2, 3})

    def test_play_areas(self):
        for s in [self.scripts["txt_rg_intro"][1], self.time] + [self.res(c, d, msxtext.rg_rating(c, d, m))
                                                                for c, d, m in msxtext.RG_RESULTS]:
            self.assertEqual(msxtext.fs_render(self.glyphs, s), self.want_area(s))
        # "SHOOTING RANGE.": 'S' at x 72 of lines 67-74; "WARNING ...": its '.' at x 248 of lines 131-138
        area = msxtext.fs_render(self.glyphs, self.scripts["txt_rg_intro"][1])
        self.assertEqual(b"".join(area[(67 + k) * LINE + 36:(67 + k) * LINE + 40] for k in range(8)), self.glyphs[18])
        self.assertEqual(b"".join(area[(131 + k) * LINE + 124:(131 + k) * LINE + 128] for k in range(8)), self.glyphs[36])

    def test_text_inc_appends_the_range(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            out = Path(d) / "text.inc"
            self.assertEqual(msxtext.main(["msxtext.py", str(RAM), str(out)]), 0)
            text = out.read_text()
            areas = {p.stem: p.read_bytes() for p in Path(d).glob("text_rg_*.sc5")}
            pngs = {p.stem for p in Path(d).glob("text_rg_*.png")}
            time = (Path(d) / "text_bs_time.sc5").read_bytes()
        before = msxtext.level_inc(self.ram) + msxtext.bonus_inc(msxtext.bonus_scripts(self.ram))
        self.assertTrue(text.startswith(before))        # (everything before the range as before)
        rest = text[len(before):]
        rest = rest[:rest.index("\n; The briefings")]   # (the briefings' part after the range's)
        self.assertEqual(re.findall(r"^(\w+):", rest, re.M),
                         ["TXT_RG_LEN", "TXT_RG_F1", "TXT_RG_F2", "TXT_RG_F3", "txt_rg_intro", "txt_rg_res", "txt_rg_rate"])
        self.assertEqual(equates(rest), {"TXT_RG_LEN": 104, "TXT_RG_F1": 37, "TXT_RG_F2": 63, "TXT_RG_F3": 91})
        self.assertEqual({0x113A5 + v for k, v in equates(rest).items() if k != "TXT_RG_LEN"}, set(msxtext.RG_FIELDS))
        for label, want in (("txt_rg_intro", self.scripts["txt_rg_intro"][1]), ("txt_rg_res", self.scripts["txt_rg_res"][1]),
                            ("txt_rg_rate", self.names)):
            self.assertEqual(db_data(rest.split(label + ":")[1].split("\n", 1)[1]), want, label)
        results = {f"text_rg_res_c{c}_d{d}_m{m}": self.res(c, d, msxtext.rg_rating(c, d, m))
                   for c, d, m in msxtext.RG_RESULTS}
        self.assertEqual(set(areas), {"text_rg_intro", "text_rg_time"} | set(results))
        self.assertEqual(pngs, set(areas))
        self.assertEqual(areas["text_rg_intro"], self.want_area(self.scripts["txt_rg_intro"][1]))
        self.assertEqual(areas["text_rg_time"], time)
        for name, s in results.items():
            self.assertEqual(areas[name], self.want_area(s), name)

    def run_render(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = msxtext.main(["msxtext.py", "render-result", *args, "--ram", str(RAM)])
        return code, out.getvalue()

    def test_render_result_command(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.sc5"
            code, text = self.run_render("13", "2", "1", "-o", str(p))
            self.assertEqual(code, 0)
            self.assertIn("rating 1 (FAIR), ac_diff = diff_tab + 16", text)
            self.assertEqual(p.read_bytes(), self.want_area(self.res(13, 2, 1)))
            self.assertTrue(p.with_suffix(".png").exists())
            # TAG 4: TEST 4 at row 10 (x 104-151, lines 147-154) as front.asm fe_text draws it
            code, text = self.run_render("16", "0", "0", "-o", str(p), "--tag", "4")
            self.assertIn("rating 2 (GOOD)", text)
            self.assertEqual(p.read_bytes(), self.want_area(msxtext.tag_line(4) + self.res(16, 0, 2)))
            self.assertNotEqual(p.read_bytes(), self.want_area(self.res(16, 0, 2)))
            # another rating's name, for a check that knows the rating and not the minutes
            code, text = self.run_render("25", "0", "1", "-o", str(p), "--rating", "0")
            self.assertIn("rating 3 (SHARP), ac_diff = diff_tab + 0; the name shown: rating 0 (POOR)", text)
            self.assertEqual(p.read_bytes(), self.want_area(self.res(25, 0, 0)))
        for bad in (["-1", "0", "1"], ["0", "65536", "1"], ["0", "0", "256"], ["0", "0", "1", "--rating", "4"],
                    ["0", "0", "1", "--tag", "100"]):
            with self.assertRaises(SystemExit, msg=bad), contextlib.redirect_stderr(io.StringIO()):
                self.run_render(*bad, "-o", "/nonexistent/x.sc5")


def signed_cells(script: bytes) -> list[tuple[int, int, int]]:
    """(first byte, first line, character code) of each character of any script of positions,
    characters and waits, its rows signed as $116CA reads them (the Amiga's text origin)."""
    out, a, col, row = [], 0, 0, 0
    while not (script[a] >= 0x80 and script[a + 1] == 7):
        if script[a] == 0:
            col, row = script[a + 1], struct.unpack_from("b", script, a + 2)[0]
            a += 3
        elif script[a] >= 0x80:
            a += 3
        else:
            out.append(((8 * col - 16) // 2, 67 + 8 * row, script[a]))
            col, a = col + 1, a + 1
    return out


@unittest.skipUnless(RAM.exists(), "level 1's RAM image not built (make ram)")
class BriefTextTests(unittest.TestCase):
    """The briefings of levels 2 and 3 and the continue offer (msxtext.py BRIEF, CONT)."""

    @classmethod
    def setUpClass(cls):
        cls.ram = RAM.read_bytes()
        cls.scripts = {label: (start, s) for label, start, s in msxtext.brief_scripts(cls.ram) + msxtext.cont_scripts(cls.ram)}
        cls.glyphs = [msxtext.glyph_sc5(cls.ram, g) for g in range(rc2front.BITMAP_GLYPHS)]

    def want_area(self, script: bytes) -> bytes:
        """Each character's glyph in its cell (rows signed), every other byte 0 (fs_clear)."""
        want = bytearray(msxtext.VIEW_LINES * LINE)
        for b, y, c in signed_cells(script):
            self.assertTrue(0 <= y <= msxtext.VIEW_LINES - 8)
            g = self.glyphs[msxtext.fs_glyph(c)]
            for k in range(8):
                want[(y + k) * LINE + b:(y + k) * LINE + b + 4] = g[4 * k:4 * k + 4]
        return bytes(want)

    def test_scripts_as_the_plan(self):
        # level 2: 00 0A FD "TOKUGAWA BREWERY" FF 02 1B, then the original's after its FF 04 30 FF 03
        start, s = self.scripts["txt_l2_brief"]
        self.assertEqual(self.ram[0x110F0:0x11108], b"\xff\x04\x30\xff\x03\x00\x0c\x04ARREST CAIN\xff\x02\x40\xff\x07")
        self.assertEqual((start, s), (0x110F0, b"\x00\x0a\xfdTOKUGAWA BREWERY\xff\x02\x1b" + self.ram[0x110F5:0x11108]))
        # level 3: 00 0C FA "CIVIC CENTRUM" FF 02 17, 00 0C FA three times, then the original's after FF 04 3C FF 03
        start, s = self.scripts["txt_l3_brief"]
        self.assertEqual(self.ram[0x110B4:0x110B9], b"\xff\x04\x3c\xff\x03")
        self.assertEqual(self.ram[0x110B9:0x110F0], b"\x00\x04\x01BATTLE YOUR WAY TO THE ROOF TO\x00\x0c\x03CONFRONT CAINe"
                                                   b"\xff\x02\x40\xff\x07")
        self.assertEqual((start, s), (0x110B4, b"\x00\x0c\xfaCIVIC CENTRUM\xff\x02\x17" + b"\x00\x0c\xfa" * 3
                                      + self.ram[0x110B9:0x110F0]))
        # the continue: the original's bytes
        self.assertEqual(self.scripts["txt_cont"], (0x11590, self.ram[0x11590:0x11590 + 57]))
        self.assertEqual({k: len(s) for k, (_, s) in self.scripts.items()},
                         {"txt_l2_brief": 41, "txt_l3_brief": 83, "txt_cont": 57})

    def test_calls_as_the_original(self):
        # rc2front.py's model of $116CA, the particle writer's 124 and 108 calls included: 393, 411, 304
        for label, (start, s) in self.scripts.items():
            elements, _ = rc2front.Interpreter(self.ram).run(start)
            self.assertEqual(msxtext.fs_run(s)[1], sum(e["calls"] for e in elements), label)
        self.assertEqual({k: msxtext.fs_run(s)[:2] for k, (_, s) in self.scripts.items()},
                         {"txt_l2_brief": (29, 393), "txt_l3_brief": (63, 411), "txt_cont": (48, 304)})
        # the typed title takes the particle part's calls: the original's lines start at the same call
        for label, n, calls in (("txt_l2_brief", 22, 1 + 124), ("txt_l3_brief", 28, 1 + 108)):
            self.assertEqual(msxtext.fs_run(self.scripts[label][1][:n] + b"\xff\x07")[1], calls, label)

    def test_titles_centred_on_the_stroke_text(self):
        # the particle writer leaves "TOKUGAWA BREWERY" at x 0-253 of lines 40-53 and "CIVIC CENTRUM" at
        # x 32-237 of lines 16-29 (the port's x: the bitplane's - 32); the typed title's cells are
        # centred on that box within half a cell
        for label, text, calls, box in (("txt_l2_brief", b"TOKUGAWA BREWERY", 125, (0, 253, 40, 53)),
                                        ("txt_l3_brief", b"CIVIC CENTRUM", 109, (32, 237, 16, 29))):
            start, s = self.scripts[label]
            self.assertEqual(msxtext.particle_title(self.ram, start), (text, calls, box), label)
            x0, y0 = 8 * s[1] - 16, 67 + 8 * msxtext.s8(s[2])
            self.assertEqual(s[3:3 + len(text)], text, label)
            self.assertLessEqual(abs(2 * x0 + 8 * len(text) - 1 - box[0] - box[1]), 8, label)
            self.assertLessEqual(abs(2 * y0 + 7 - box[2] - box[3]), 8, label)

    def test_play_areas(self):
        # fs_render (fs_char's 8-bit arithmetic) puts every cell where the Amiga's signed rows do
        for label, (_, s) in self.scripts.items():
            self.assertEqual(msxtext.fs_render(self.glyphs, s), self.want_area(s), label)
            # a TAG build's TEST 5 at row 10 meets none of them
            tag = msxtext.tag_line(5)
            self.assertEqual(msxtext.fs_render(self.glyphs, tag + s), self.want_area(tag + s), label)
            self.assertFalse({y for _, y, _ in signed_cells(s)} & {y for _, y, _ in signed_cells(tag + b"\xff\x07")}, label)
        # 'T' of "TOKUGAWA BREWERY" at x 64 of lines 43-50; 'C' of "CIVIC CENTRUM" at x 80 of lines 19-26
        for label, b, y, g in (("txt_l2_brief", 32, 43, 19), ("txt_l3_brief", 40, 19, 2)):
            area = msxtext.fs_render(self.glyphs, self.scripts[label][1])
            self.assertEqual(b"".join(area[(y + k) * LINE + b:(y + k) * LINE + b + 4] for k in range(8)), self.glyphs[g], label)

    def test_text_inc_appends_the_briefings(self):
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            out = Path(d) / "text.inc"
            self.assertEqual(msxtext.main(["msxtext.py", str(RAM), str(out)]), 0)
            text = out.read_text()
            areas = {p.stem: p.read_bytes() for p in Path(d).glob("*.sc5")}
            pngs = {p.stem for p in Path(d).glob("*.png")}
        before = (msxtext.level_inc(self.ram) + msxtext.bonus_inc(msxtext.bonus_scripts(self.ram))
                  + msxtext.range_inc(msxtext.range_scripts(self.ram), msxtext.rg_names(self.ram)))
        # level 1's, Brainstorm's and the range's part byte-identical to a969fc8's text.inc
        self.assertEqual(hashlib.sha256(before.encode()).hexdigest(), TEXT_INC_A969FC8)
        self.assertTrue(text.startswith(before))
        rest = text[len(before):]
        self.assertEqual(rest, msxtext.brief_inc(msxtext.brief_scripts(self.ram) + msxtext.cont_scripts(self.ram)))
        self.assertEqual(re.findall(r"^(\w+):", rest, re.M), ["txt_l2_brief", "txt_l3_brief", "txt_cont"])
        for label, (_, s) in self.scripts.items():
            self.assertEqual(db_data(rest.split(label + ":")[1].split("\n", 1)[1]), s, label)
            self.assertEqual(areas[label.replace("txt_", "text_")], self.want_area(s), label)
        self.assertEqual(pngs, set(areas))
        # (+ 3: the ending's and the high scores' references, text_end, text_hisc, text_best:
        #  tests/test_ending.py)
        self.assertEqual(len(areas), 4 + 2 + len(msxtext.RG_RESULTS) + 3 + 3)


@unittest.skipUnless(all(p.exists() for p in HUD_INPUTS), "game files not extracted (make extract)")
class BonusMessageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.perma, cls.main, cls.puzl, frng = (p.read_bytes() for p in HUD_INPUTS)
        cls.frng = bytekiller.decrunch(frng)                    # (its bytes from $1EA00)
        cls.blob, cls.inc, _ = msxhudrt.build(cls.perma, cls.main, cls.puzl, cls.frng)
        cls.blob_pz, cls.inc_pz, _ = msxhudrt.build(cls.perma, cls.main, cls.puzl)
        cls.blob1, cls.inc1, _ = msxhudrt.build(cls.perma, cls.main, None)
        cls.eq = equates(cls.inc)

    def text(self, ptr: int, blob: bytes | None = None) -> bytes:
        return msxhudrt.message(self.blob if blob is None else blob, ptr - msxhudrt.BASE)

    def game_msg(self, n: int, blob: bytes | None = None) -> int:
        """msx/hud.asm game_msg: the pointer at HUD_MSGS + 2 n."""
        self.assertTrue(0 <= n <= 255)
        return struct.unpack_from("<H", self.blob if blob is None else blob,
                                  self.eq["HUD_MSGS"] + 2 * n - msxhudrt.BASE)[0]

    def test_level1_bytes_and_numbers_unchanged(self):
        self.assertTrue(self.blob.startswith(self.blob1))
        self.assertTrue(self.inc.startswith(self.inc1))
        eq1 = equates(self.inc1)
        self.assertEqual([eq1[f"HUD_MSG_{a:04X}"] for a in msxhudrt.MESSAGES], list(range(21)))
        self.assertEqual((eq1["HUD_NMSGS"], self.eq["HUD_NMSGS"]), (21, 21))
        self.assertEqual({k: v for k, v in self.eq.items() if k in eq1}, eq1)

    def test_puzl_numbers_and_bytes_unchanged(self):
        # the range's messages after PUZL's: PUZL's keep their numbers and bytes, 4 bytes on
        self.assertTrue(self.inc.startswith(self.inc_pz))
        eq_pz = equates(self.inc_pz)
        self.assertEqual({k: v for k, v in self.eq.items() if k in eq_pz}, eq_pz)
        self.assertEqual(sorted(set(self.eq) - set(eq_pz)), ["HUD_MSG_1EB32", "HUD_MSG_1EB3B"])
        self.assertEqual([self.eq[f"HUD_MSG_{a:05X}"] for a, _ in msxhudrt.PUZL_MESSAGES], [174, 175, 176])
        cut = self.eq["HUD_PZ_MSGS"] - msxhudrt.BASE
        self.assertEqual(self.blob[:cut], self.blob_pz[:cut])
        for n in (174, 175, 176):
            self.assertEqual(self.game_msg(n), self.game_msg(n, self.blob_pz) + 4, n)
            self.assertEqual(self.text(self.game_msg(n)), self.text(self.game_msg(n, self.blob_pz), self.blob_pz), n)
        self.assertEqual(len(self.blob) - len(self.blob_pz), 4 + 9 + 10)

    def test_game_msg_reaches_every_message(self):
        for n, a in enumerate(msxhudrt.MESSAGES):
            self.assertEqual(self.text(self.game_msg(n)), msxhudrt.message(self.main, a - 0x8000), hex(a))
        for data, load, table in ((self.puzl, 0x17100, msxhudrt.PUZL_MESSAGES),
                                  (self.frng, 0x1EA00, msxhudrt.FRNG_MESSAGES)):
            for a, want in table:
                m = self.text(self.game_msg(self.eq[f"HUD_MSG_{a:05X}"]))
                self.assertEqual(m, msxhudrt.message(data, a - load), hex(a))
                self.assertEqual("".join(rc2front.GLYPH_NAMES[hudmodel.font_index(c)] for c in m[:-1]), want)

    def test_puzl_messages_at_their_offsets(self):
        self.assertEqual([msxhudrt.message(self.puzl, o) for o in (0x638, 0x641, 0x64E)],
                         [b"TIMEOUTe\xff", b"MALFUNCTIONe\xff", b"MEMORY RESTOREDe\xff"])

    def test_frng_messages_at_their_offsets_and_numbers(self):
        self.assertEqual(len(self.frng), 170970)
        self.assertEqual([msxhudrt.message(self.frng, o) for o in (0x132, 0x13B)], [b"NO AMMOe\xff", b"TIME OUTe\xff"])
        self.assertEqual((self.eq["HUD_MSG_1EB32"], self.eq["HUD_MSG_1EB3B"]), (177, 178))

    def test_glyphs_in_the_hud_font(self):
        for data, load, table in ((self.puzl, 0x17100, msxhudrt.PUZL_MESSAGES),
                                  (self.frng, 0x1EA00, msxhudrt.FRNG_MESSAGES)):
            for a, _ in table:
                for c in msxhudrt.message(data, a - load)[:-1]:
                    self.assertIn(hudmodel.font_index(c), range(44), hex(a))

    def test_fits_the_hud_banks(self):
        self.assertLessEqual(len(self.blob), 0x4000)
        self.assertGreaterEqual(self.eq["HUD_PZ_MSGS"], 0xA000)        # (HUD_BANK + 1: game_msg maps it)
        self.assertLessEqual(self.eq["HUD_PZ_MSGS"] + 10 + 39 + 19, 0xC000)

    def test_frng_needs_puzl(self):
        with self.assertRaises(SystemExit):
            msxhudrt.build(self.perma, self.main, None, self.frng)

    def test_command_line(self):
        # OUT then FRNG_15.bin as on the disk (decrunched by the tool); without it, the data before the range
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(io.StringIO()):
            ins = [str(p) for p in HUD_INPUTS[:3]]
            self.assertEqual(msxhudrt.main(["msxhudrt.py", *ins, str(Path(d) / "a"), str(HUD_INPUTS[3])]), 0)
            self.assertEqual(msxhudrt.main(["msxhudrt.py", *ins, str(Path(d) / "b")]), 0)
            for name, blob, inc in (("a", self.blob, self.inc), ("b", self.blob_pz, self.inc_pz)):
                self.assertEqual((Path(d) / f"{name}.bin").read_bytes(), blob + b"\xff" * (0x4000 - len(blob)), name)
                self.assertEqual((Path(d) / f"{name}.inc").read_text(), inc, name)
            bad = Path(d) / "bad.bin"
            bad.write_bytes(HUD_INPUTS[3].read_bytes()[:-4])
            with self.assertRaises(SystemExit):
                msxhudrt.main(["msxhudrt.py", *ins, str(Path(d) / "c"), str(bad)])
            self.assertFalse((Path(d) / "c.bin").exists())


if __name__ == "__main__":
    unittest.main()
