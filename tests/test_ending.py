"""The game completed and the high scores (docs/ENDING.md): the ending's tune as $11C54 plays it
(tools/msxtune.py end_ticks, unrolled), the ending's and the name entry's texts and the table's
defaults (tools/msxtext.py END, HISC, hs_defaults, ending.inc apart from text.inc), and the models
tools/bstest/endcheck.py checks the emulator's records against ($1215C's name entry, $1211C's
table), with the options tools/mkrom.py takes for the test start (END_TEST)."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "bstest"))

RAM = ROOT / "build" / "ram" / "level1_full.bin"            # tools/ramimage.py (make ram)


def have_numpy() -> bool:
    try:
        import numpy  # noqa: F401
    except ImportError:
        return False
    return True


@unittest.skipUnless(have_numpy(), "tools/msxtune.py needs numpy (the project's venv)")
class TuneTest(unittest.TestCase):
    def test_end_ticks_four_of_five_passes(self):
        import msxtune
        self.assertEqual(msxtune.end_ticks(), 4916)             # 1801h passes, $11C52 from 0
        self.assertEqual(msxtune.end_ticks(5), 4)                # tick, tick, tick, tick, skip
        self.assertEqual(msxtune.end_ticks(6), 5)
        self.assertEqual(msxtune.end_ticks(1, 3), 1)             # 3 - 1 = 2: a tick
        self.assertEqual(msxtune.end_ticks(1, 1), 0)             # 1 - 1 = 0: no tick

    def test_unrolled_loop(self):
        import msxtune
        tune = {"loop": {"start_tick": 2, "length_ticks": 3},
                "frames": {"0": [[1, 100, 64, 1], [1, 101, 64, 1], [3, 102, 32, 2]]},
                "key_ons": [[0, 0, 1, 10, 0, 100], [3, 0, 2, 12, 2, 102]], "ticks": 5}
        u = msxtune.unrolled(tune, 9)
        per = [p for n, p, v, i in u["frames"]["0"] for _ in range(n)]
        self.assertEqual(per, [100, 101, 102, 102, 102, 102, 102, 102, 102])
        self.assertEqual([k[0] for k in u["key_ons"]], [0, 3, 6])    # tick 3 again at 3 + 3
        self.assertIsNone(u["loop"])
        self.assertEqual(u["ticks"], 9)


@unittest.skipUnless(RAM.exists(), "needs build/ram/level1_full.bin (make ram)")
class TextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import msxtext
        cls.t = msxtext
        cls.ram = RAM.read_bytes()

    def test_end_screen_as_the_briefings(self):
        end = self.t.brief_scripts(self.ram, self.t.END)
        label, start, script = end[0]
        self.assertEqual((label, start), ("txt_end", 0x112C5))
        self.assertEqual(self.t.fs_run(script)[1], 341)
        self.assertEqual(script[:3], bytes((0, 11, 0xFD)))              # column 11, row -3
        self.assertEqual(self.t.decode(script[3:14]), "  WELL DONE")
        self.assertIn(b"YOU HAVE DEFEATED ROBOCOP ]f", script)       # the original's lines follow
        self.assertTrue(script.endswith(b"\xff\x02\x28\xff\x07"))

    def test_hisc_screen_is_the_originals(self):
        (label, start, script), = self.t.hisc_scripts(self.ram)
        self.assertEqual(script, self.ram[0x115C9:0x1162F])
        self.assertEqual(self.t.fs_run(script)[1], 92)
        with self.assertRaises(AssertionError):                       # its last line at row 9
            self.t.check_text(label, script, 92)

    def test_table_defaults(self):
        head, table = self.t.hs_defaults(self.ram)
        self.assertEqual(head, b"   TODAYS BEST ")
        self.assertEqual([(self.t.decode(n).rstrip(), s) for n, s in table],
                         [("IAN", 100000), ("KAREN", 90000), ("COLIN", 50000), ("KEITH", 45000),
                          ("ANDY", 9000), ("PAUL", 7500)])
        self.assertEqual(self.t.hs_bcd(100000), bytes((0x00, 0x10, 0x00, 0x00)))
        self.assertEqual(self.t.hs_bcd(12345678), bytes((0x12, 0x34, 0x56, 0x78)))
        self.assertEqual(self.t.hs_line(b"IAN      ", 100000)[11:], b"[\\[[[[[")

    def test_best_screen(self):
        head, table = self.t.hs_defaults(self.ram)
        self.assertEqual(self.t.fs_run(self.t.best_script())[1], 748)
        text = self.t.best_text(head, table)
        self.t.check_text("the table", text + self.t.best_script(), 7 + 15 + 6 * 18 + 748)
        self.assertEqual(text[:3], bytes((0, 11, 0xFC)))                 # BEST_COL, BEST_ROW
        self.assertEqual(text[18:21], bytes((0, 11, 0xFE)))              # the next line 2 rows on

    def test_ending_inc_apart_text_inc_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "text.inc"
            with contextlib.redirect_stdout(io.StringIO()):
                self.t.main(["msxtext.py", str(RAM), str(out)])
            ending = (Path(d) / "ending.inc").read_text()
            self.assertNotIn("txt_end", out.read_text())
            for name in ("txt_end:", "txt_hisc:", "txt_best:", "hs_head:", "hs_def:", "HS_X: equ 48",
                         "HS_Y: equ 80", "BEST_ROW: equ -4"):
                self.assertIn(name, ending)


class ModelTest(unittest.TestCase):
    def test_entry_model(self):
        import endcheck
        mark = 0x67
        waits, final = endcheck.entry_model(["RET"])
        self.assertEqual(waits, [b" " + bytes([mark]) + b" " * 7])     # the mark under the second
        self.assertEqual(final, b" " * 9)
        waits, final = endcheck.entry_model("R O B O C O P 2 X BS KP9 Z RET".split())
        self.assertEqual(len(waits), 13)
        self.assertEqual(waits[9], b"ROBOCOP]X")                      # full, no mark ('2': '[' + 2)
        self.assertEqual(waits[10], b"ROBOCOP]" + bytes([mark]))      # Backspace
        self.assertEqual(waits[12], waits[11])                        # Z ignored
        self.assertEqual(final, b"ROBOCOP]d")                         # the keypad's 9: '[' + 9
        waits, final = endcheck.entry_model("BS A BS BS RET".split())
        self.assertEqual(waits[2], b"A" + bytes([mark]) + b" " * 7)
        self.assertEqual(waits[3], bytes([mark]) + b" " * 8)          # A taken back: the mark there
        self.assertEqual(final, b" " * 9)

    def test_table_model_ties_keep_the_older_above(self):
        import endcheck
        t = [(b"A", 100), (b"B", 90), (b"C", 50), (b"D", 45), (b"E", 9), (b"F", 7)]
        self.assertEqual(endcheck.table_model(t, b"N", 7), t)                     # a tie: no entry
        self.assertEqual(endcheck.table_model(t, b"N", 50)[2:4], [(b"C", 50), (b"N", 50)])
        self.assertEqual(endcheck.table_model(t, b"N", 101)[0], (b"N", 101))
        self.assertEqual(endcheck.table_model(t, b"N", 10 ** 7 + 8)[5], (b"N", 8))  # the low 7 digits


class OptionsTest(unittest.TestCase):
    def run_mkrom(self, *opts):
        import mkrom
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            rc = mkrom.main(["mkrom.py", "/nonexistent/level1", "/nonexistent/x.rom", *opts])
        return rc, err.getvalue()

    def test_end_test_alone(self):
        self.assertEqual(self.run_mkrom("END_TEST=1", "LV_TEST=2")[0], 2)
        self.assertEqual(self.run_mkrom("END_TEST=2", "PZ_TEST=1")[0], 2)
        self.assertEqual(self.run_mkrom("END_TEST=3")[0], 2)
        rc, err = self.run_mkrom("LV_CARRY=10050:2:0:1")
        self.assertEqual(rc, 2)
        self.assertIn("END_TEST", err)


if __name__ == "__main__":
    unittest.main()
