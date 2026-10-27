"""tools/msxmatrix.py: the verdict on a session's rows, and the session's timing in tclsh with
openMSX's commands mocked (a virtual emulated clock for 'after time'). No emulator, no ROM; the
Tcl case is skipped without tclsh."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import msxmatrix  # noqa: E402

SND = "mus_mode 01 snd_fm 00 scc_pg2 00"


def row(tag: str, tick: int, r1: int = 0x62, r0: int = 0x16) -> str:
    return f"{tag} R0 {r0:02X} R1 {r1:02X} tick {tick} {SND}"


class VerdictTests(unittest.TestCase):
    def test_title_mode_line(self):
        rows = [row("title", 0, r0=0x0E), row("game1", 170), row("game2", 345), row("game2b", 345), ""]
        self.assertEqual(msxmatrix.verdict("msx2", rows, False, ""), "msx2         PASS ticks 170->345  " + SND)

    def test_title_mode_without_a_title(self):
        line = msxmatrix.verdict("msx2", [row("notitle", 0, r0=0x16)], False, "")
        self.assertTrue(line.startswith("msx2         FAIL no title notitle "), line)

    def test_no_title_mode(self):
        rows = [row("game1", 410), row("game2", 760), row("game2b", 760)]
        self.assertEqual(msxmatrix.verdict("turbor", rows, False, "", title=False),
                         "turbor       PASS ticks 410->760  " + SND)
        self.assertIn("FAIL ticks 410->410", msxmatrix.verdict("x", rows[:1] + [row("game2", 410)], False, "",
                                                               title=False))

    def test_display_counts_past_the_split_blank(self):
        rows = [row("game1", 410), row("game2", 760, r1=0x22), row("game2b", 760)]
        self.assertIn(" PASS ", msxmatrix.verdict("x", rows, False, "", title=False))
        rows[2] = row("game2b", 760, r1=0x22)
        self.assertIn("FAIL ticks 410->760 display off", msxmatrix.verdict("x", rows, False, "", title=False))

    def test_halt_and_missing_rows_fail(self):
        rows = [row("game1", 410), row("game2", 760), row("game2b", 760)]
        self.assertIn("FAIL ticks 410->760 DI; HALT", msxmatrix.verdict("x", rows, True, "", title=False))
        line = msxmatrix.verdict("x", rows[:1], False, "Error: something\n", title=False)
        self.assertIn("FAIL ticks 410->? Error: something", line)


MOCK = r"""
set ::now 0.0
set ::q {}
set ::seq 0
set ::done 0
set ::title_at %(title_at)s
set ::keys {}
rename after tcl_after
proc after {kind t script} {
  incr ::seq
  lappend ::q [list [expr {$::now + $t}] $::seq $script]
  return "after#$::seq"
}
proc vdpreg {r} { if {$r == 0} { return [expr {$::now >= $::title_at ? 0x0E : 0x16}] }; return 0x62 }
proc peek {a} { set ms [expr {int(round($::now * 1000))}]; return [expr {$a == 0x1000 ? $ms & 255 : ($ms >> 8) & 255}] }
proc keymatrixdown {r b} { lappend ::keys [format "down %%.3f" $::now] }
proc keymatrixup {r b} { lappend ::keys [format "up %%.3f" $::now] }
rename exit tcl_exit
proc exit {} { set ::done 1 }
source [lindex $argv 0]
source [lindex $argv 1]
while {!$::done && [llength $::q]} {
  set ::q [lsort -real -index 0 [lsort -integer -index 1 $::q]]
  set e [lindex $::q 0]
  set ::q [lrange $::q 1 end]
  set ::now [lindex $e 0]
  uplevel #0 [lindex $e 2]
}
puts "keys $::keys"
puts "end [format %%.3f $::now]"
"""


@unittest.skipUnless(shutil.which("tclsh"), "no tclsh")
class SessionTests(unittest.TestCase):
    def session(self, notitle: int, title_at: float) -> tuple[list[str], str]:
        """The rows the session writes (tick = the emulated time in ms) and the mock's output."""
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "pre.tcl").write_text(f'set ::mx_out "{t / "state.txt"}"\nset ::mx_rom "{t / "x.rom"}"\n'
                                       f'set ::mx_mode cart\nset ::mx_tick "0x1000"\nset ::mx_vars {{}}\n'
                                       f"set ::mx_notitle {notitle}\n")
            (t / "session.tcl").write_text(msxmatrix.SESSION)
            (t / "mock.tcl").write_text(MOCK % {"title_at": title_at})
            r = subprocess.run(["tclsh", str(t / "mock.tcl"), str(t / "pre.tcl"), str(t / "session.tcl")],
                               capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 0, r.stderr)
            return [s for s in (t / "state.txt").read_text().split("\n") if s], r.stdout

    def test_title_mode_samples(self):
        rows, out = self.session(0, 8.0)
        self.assertEqual([s.split()[0] for s in rows], ["title", "game1", "game2", "game2b"])
        self.assertEqual([int(s.split()[6]) for s in rows], [8000, 20000, 27000, 27005])
        self.assertIn("keys {down 9.000} {up 9.300}", out)

    def test_title_mode_gives_up(self):
        rows, out = self.session(0, 99.0)
        self.assertEqual(rows, ["notitle R0 16 R1 62 tick 20000"])

    def test_no_title_mode_samples(self):
        rows, out = self.session(1, 8.0)
        self.assertEqual([s.split()[0] for s in rows], ["game1", "game2", "game2b"])
        self.assertEqual([int(s.split()[6]) for s in rows], [20000, 27000, 27005])
        self.assertIn("keys \n", out)
        self.assertIn("end 27.005", out)


if __name__ == "__main__":
    unittest.main()
