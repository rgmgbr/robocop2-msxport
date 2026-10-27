"""Brainstorm (PUZL) bench tools: tools/puzlsolve.py, tools/puzlcmp.py, tools/drivejoy.py --fuzz,
tools/amigaemu.py puzl and tools/openmsx_rc2.tcl's rc2_pz_* procs (tclsh with openMSX's commands
mocked). Synthetic boards and traces only: no data from the game; the bench case needs the RAM
image (make ram) and Unicorn (the project's venv), and is skipped without them."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import drivejoy  # noqa: E402
import puzlcmp  # noqa: E402
import puzlsolve  # noqa: E402

LEVEL1_RAM = ROOT / "build" / "ram" / "level1_full.bin"


def board(rows: list[str], start=(0, 0)) -> dict:
    """'R' red chip (0), '#' black chip (1), '.' board (2); 11 x 8."""
    assert len(rows) == 8 and all(len(r) == 11 for r in rows)
    cells = [{"R": 0, "#": 1, ".": 2}[c] for r in rows for c in r]
    return {"start": start, "reds": cells.count(0), "timer": 0x100, "tune": 1, "cells": cells}


class PuzlSolveTests(unittest.TestCase):
    def test_path_takes_every_red_chip_by_single_steps(self):
        b = board(["..R........", ".#......R..", "....R......", "...........",
                   "R.....#....", "...........", "......R....", "..........R"])
        p = puzlsolve.solve(b)
        self.assertIsNotNone(p)
        self.assertEqual(p[0], (0, 0))
        self.assertEqual(len(set(p)), len(p))                       # never a visited cell again
        for (ax, ay), (bx, by) in zip(p, p[1:]):
            self.assertEqual(abs(ax - bx) + abs(ay - by), 1)
        reds = {(i % 11, i // 11) for i, v in enumerate(b["cells"]) if v == 0}
        self.assertTrue(reds <= set(p))
        self.assertIn(p[-1], reds)                                  # it ends on the last one

    def test_two_dead_end_red_chips_cannot_both_be_taken(self):
        b = board(["R#.........", "...........", "...........", "...........",
                   "...........", "...........", "...........", ".........#R"], start=(5, 3))
        self.assertIsNone(puzlsolve.solve(b, limit=5000, tries=3))

    def test_bot_presses_once_then_releases(self):
        bot = puzlsolve.Bot([[(0, 0), (1, 0), (1, 1)]])
        row = {"board2": 0, "done": 0, "fail": 0, "endc": 0, "active": 255, "col": 0, "row": 0}
        self.assertEqual(bot(row), "r")
        self.assertEqual(bot(row), "")                              # (a release: the next press is a change)
        self.assertEqual(bot(dict(row, col=1)), "d")

    def test_quirk1_path_keeps_the_tested_cell_free(self):
        # (4, 0) has one way in, (3, 0): every path ends there, so the quirk's move is down,
        # testing (0, 1) from the clobbered column 0 while (4, 1) is a black chip
        b = board(["...RR#.....", "....#......", "R..........", "...........",
                   "...........", "...........", "...........", "..........."])
        p, keys = puzlsolve.solve_quirk1(b)
        self.assertEqual(keys, "df")
        self.assertEqual(p[-1], (4, 0))
        self.assertNotIn((0, 1), p)
        reds = {(i % 11, i // 11) for i, v in enumerate(b["cells"]) if v == 0}
        self.assertTrue(reds <= set(p))

    def test_bot_presses_the_quirk_keys_after_the_last_move_of_the_4th_board(self):
        paths = [[(0, 0)]] * 3 + [[(0, 0), (1, 0), (2, 0)]]
        bot = puzlsolve.Bot(paths, "df")
        row = {"board2": 6, "done": 0, "fail": 0, "endc": 0, "active": 255, "col": 0, "row": 0}
        self.assertEqual(bot(row), "r")
        self.assertEqual(bot(row), "")                              # (not the last move: a release)
        self.assertEqual(bot(dict(row, col=1)), "r")
        self.assertEqual(bot(dict(row, col=1)), "df")               # (the last one: the quirk's keys)
        self.assertEqual(bot(dict(row, col=2)), "")


class DriveJoyFuzzTests(unittest.TestCase):
    def test_fuzz_keys_are_reproducible_and_read_as_themselves(self):
        a, b = drivejoy.fuzz_items(7, 500), drivejoy.fuzz_items(7, 500)
        self.assertEqual(a, b)
        self.assertNotEqual(a, drivejoy.fuzz_items(8, 500))
        self.assertTrue(all(1 <= c <= 6 for _, c, _ in a))
        self.assertGreaterEqual(a[-1][0] + a[-1][1], 494)
        for keys in drivejoy.FUZZ_KEYS:                             # (no up with down, no left with right:
            self.assertFalse({"u", "d"} <= set(keys))              #  read_joystick's table reads them as
            self.assertFalse({"l", "r"} <= set(keys))              #  no direction, ext_joy as they are)
        self.assertTrue(any(len(set(k) - {"f"}) == 2 for k in drivejoy.FUZZ_KEYS))
        self.assertTrue(any("f" in k and len(k) == 2 for k in drivejoy.FUZZ_KEYS))


class PuzlCmpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def traces(self, corrupt=None, score=False):
        """Two PUZL frames on the Amiga's side and the mirror a faithful port would dump."""
        boards_at = 0xE000
        table = 0x17448
        amiga, msx = [], ["# D000 DC00 %04X" % boards_at]
        for n in range(2):
            v = bytearray(0x22)
            v[0:2] = n.to_bytes(2, "big")                           # $B00
            v[6:10] = (table + 6).to_bytes(4, "big")                # $B06
            v[0x0C:0x0E] = (3 + n).to_bytes(2, "big")               # $B0C
            v[0x12:0x16] = (0x17DE8 + 64 * n if n else 0).to_bytes(4, "big")
            g = bytearray(0x100)
            g[0x46:0x4A] = bytes.fromhex("00000100")                # $8046 score
            boards = bytearray(376)
            boards[6] = 0x16
            amiga.append({"frame": n, "vars": v.hex(), "glob": g.hex(), "boards": boards.hex(),
                          "code": {"173d4": f"{table:08x}"}})
            mv = bytearray(v)
            mv[6:10] = (boards_at + 6).to_bytes(4, "big")
            mv[0x12:0x16] = (64 * n).to_bytes(4, "big")
            if corrupt == n:
                mv[0x0C:0x0E] = (9).to_bytes(2, "big")
            mg = bytearray(g)
            if score:
                mg[0x49] = 0x50                                     # (another score: a played level 1)
            msx.append(" ".join(puzlcmp.swapped(bytes(x)).hex() for x in (mv, mg)) + " " + boards.hex())
        msx.append("# result 0")
        (self.tmp / "a.jsonl").write_text("\n".join(json.dumps(r) for r in amiga)
                                          + "\n" + json.dumps({"result": 0, "frames": 2}) + "\n")
        (self.tmp / "m.txt").write_text("\n".join(msx) + "\n")
        return self.tmp / "a.jsonl", self.tmp / "m.txt"

    def test_a_faithful_mirror_compares_equal(self):
        a, m = self.traces()
        self.assertEqual(puzlcmp.compare(a, m, 0), 0)

    def test_a_wrong_byte_is_reported(self):
        a, m = self.traces(corrupt=1)
        self.assertEqual(puzlcmp.compare(a, m, 0), 1)

    def test_skipped_fields_are_not_compared(self):
        a, m = self.traces(score=True)
        self.assertEqual(puzlcmp.compare(a, m, 0), 1)
        self.assertEqual(puzlcmp.compare(a, m, 0, skip=("score",)), 0)


TCL_MOCK = r"""
array set ::mem {}
set ::extjoy {}
set ::bps {}
set ::nbp 0
set ::pause on
set ::rega 0
proc peek {a} { set a [expr {$a}] ; if {[info exists ::mem($a)]} { return $::mem($a) } ; return 0 }
proc mset {a v} { set ::mem([expr {$a}]) [expr {$v}] }
proc poke {a v} { set a [expr {$a}] ; set ::mem($a) [expr {$v & 0xFF}] ; if {$a == 0xCE5A} { lappend ::extjoy [expr {$v & 0xFF}] } }
proc debug {cmd args} {
	switch -- $cmd {
		read_block { lassign $args space addr len ; set s "" ; for {set i 0} {$i < $len} {incr i} { append s [binary format c [peek [expr {$addr + $i}]]] } ; return $s }
		set_bp { lassign $args addr cond cmd ; incr ::nbp ; set id "bp#$::nbp" ; dict set ::bps $id [list [expr {$addr}] $cond $cmd] ; return $id }
		remove_bp { dict unset ::bps [lindex $args 0] ; return }
		breakpoint { if {[lindex $args 0] eq "list"} { set l {} ; dict for {id v} $::bps { lappend l $id {} } ; return $l } ; dict unset ::bps [lindex $args 1] ; return }
		condition { return {} }
		breaked { return 0 }
	}
}
proc carta {args} {}
proc reset {} {}
proc reg {name} { return $::rega }
proc fire {addr} {
	dict for {id v} $::bps {
		lassign $v a cond cmd
		if {$a != $addr} continue
		if {$cond ne "" && ![expr $cond]} continue
		uplevel #0 $cmd
	}
}
source [lindex $argv 0]
mset 0x7F10 0xC9
puts "start [rc2_pz_drive t.rom [lindex $argv 1] [lindex $argv 2] 100 0 [lindex $argv 3]]"
fire 0x7F10
mset 0xA123 0xCD
mset 0xA124 0x56
mset 0xA125 0xA4
for {set n 0} {$n < 3} {incr n} {
	mset 0xD000 $n
	mset 0xF500 [expr {0x10 + $n}]
	fire 0xA123
}
set ::rega 1
fire 0x7F10
puts "extjoy $::extjoy"
puts "mem [peek 0xDC4D] [peek 0xD018] [peek 0xD019] [peek 0xDC4C]"
puts "end $::rc2_trace_done $::rc2_pz_result $::pause [dict size $::bps]"
"""


@unittest.skipUnless(shutil.which("tclsh"), "needs tclsh")
class PuzlTclTests(unittest.TestCase):
    def test_rc2_pz_drive_rows_input_and_result(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            labels = tmp / "t.labels"
            labels.write_text("pz_boards:\tequ $f500\npz_tick:\tequ $a123\npz_frame:\tequ $a456\n"
                              "pz_done:\tequ $7f10\next_joy:\tequ $ce5a\n")
            drive = tmp / "t.drive"                                 # bytes 08 12; at frame 1: $804C = FFh, $B18 = 1234h
            drive.write_text("0812\n\n0\n1:32844:255:1 1:2840:4660:2\n")
            (tmp / "mock.tcl").write_text(TCL_MOCK)
            out = tmp / "t.txt"
            p = subprocess.run(["tclsh", str(tmp / "mock.tcl"), str(ROOT / "tools" / "openmsx_rc2.tcl"),
                                str(labels), str(out), str(drive)], capture_output=True, text=True, timeout=60)
            self.assertEqual(p.returncode, 0, p.stderr)
            got = dict(line.split(" ", 1) for line in p.stdout.splitlines())
            self.assertEqual(got["extjoy"].split(), ["0", "8", "18", "0"])     # (armed: 0; then the script's bytes)
            self.assertEqual(got["mem"].split(), ["255", "52", "18", "0"])     # (a byte at A ^ 1; a word little-endian)
            self.assertEqual(got["end"].split(), ["1", "1", "on", "0"])
            lines = out.read_text().splitlines()
            self.assertEqual(lines[0], "# D000 DC00 F500")
            self.assertEqual(lines[-1], "# result 1")
            rows = [line.split() for line in lines[1:-1]]
            self.assertEqual(len(rows), 3)                          # (the stray pz_done before the stage ignored)
            for n, (v, g, b) in enumerate(rows):
                self.assertEqual((len(v), len(g), len(b)), (0x44, 0x200, 752))
                self.assertEqual(v[:4], f"{n:02x}00")
                self.assertEqual(b[:2], f"{0x10 + n:02x}")
        finally:
            shutil.rmtree(tmp)


@unittest.skipUnless(LEVEL1_RAM.exists(), "needs build/ram/level1_full.bin (make ram)")
class PuzlBenchTests(unittest.TestCase):
    def test_the_solved_boards_return_0(self):
        try:
            import amigaemu
        except SystemExit:
            self.skipTest("needs Unicorn")
        b = amigaemu.PuzlBench(LEVEL1_RAM.parents[1] / "extracted", LEVEL1_RAM)
        b.setup(1)
        paths = [puzlsolve.solve(puzlsolve.parse_board(bytes(b.uc.mem_read(0x17448 + 94 * k, 94))))
                 for k in range(4)]
        bot = puzlsolve.Bot(paths)
        b.play(2000, [], bot=bot)
        self.assertEqual(b.result, 0)


if __name__ == "__main__":
    unittest.main()
