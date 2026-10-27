"""The shooting range (FRNG) bench tools: tools/frngcmp.py and its field map, the rc2_fr_* Tcl procs
of tools/openmsx_rc2.tcl (tclsh with openMSX's commands mocked, directly and through
tools/frngmock.py), tools/frngbot.py's rules and tools/amigaemu.py frng. Synthetic traces only, no
data from the game; the bot and bench cases need Unicorn (the project's venv) and the bench cases
the RAM image (make ram); they are skipped without them."""
import contextlib
import io
import json
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import frngcmp  # noqa: E402

FIELDS = ROOT / "analysis" / "frng_ram.tsv"
MOCK = ROOT / "tools" / "frngmock.py"
TCL = ROOT / "tools" / "openmsx_rc2.tcl"
EXTRACTED = ROOT / "build" / "extracted"
LEVEL1_RAM = ROOT / "build" / "ram" / "level1_full.bin"
CODE_BLOCKS = ((0x1EB30, 2), (0x1EB46, 20), (0x1F246, 2), (0x1F46C, 2), (0x1F502, 10), (0x1F60E, 506),
               (0x1F9B0, 4), (0x1FA8C, 12))


def amiga_row(n: int, poke: dict | None = None) -> dict:
    """A synthetic --trace-ram row: every byte a function of its address and the frame."""
    def blk(base, size):
        return bytes(((base + i) * 7 + n) & 0xFF for i in range(size))
    vars_, glob = bytearray(blk(0xB00, 0xC6)), bytearray(blk(0x8000, 0x100))
    code = {f"{lo:x}": bytearray(blk(lo, size)) for lo, size in CODE_BLOCKS}
    for addr, v in (poke or {}).items():
        if 0xB00 <= addr < 0xBC6:
            vars_[addr - 0xB00] = v
        elif 0x8000 <= addr < 0x8100:
            glob[addr - 0x8000] = v
        else:
            for lo, size in CODE_BLOCKS:
                if lo <= addr < lo + size:
                    code[f"{lo:x}"][addr - lo] = v
    return {"frame": n, "keys": "", "vars": vars_.hex(), "glob": glob.hex(),
            "code": {k: bytes(v).hex() for k, v in code.items()}}


def msx_line(row: dict, poke: dict | None = None) -> str:
    """What an exact port's trace holds: the blocks in the mirror's rule."""
    def sw(b):
        b = bytearray(b)
        b[0::2], b[1::2] = b[1::2], b[0::2]
        return b
    code = b""
    for base, size in frngcmp.PIECES:
        for lo, hexs in row["code"].items():
            lo = int(lo, 16)
            if lo <= base < lo + len(hexs) // 2:
                code += bytes.fromhex(hexs)[base - lo:base - lo + size]
    blocks = [sw(bytes.fromhex(row["vars"])), sw(bytes.fromhex(row["glob"])), sw(code)]
    for (i, off), v in (poke or {}).items():
        blocks[i][off] = v
    return " ".join(bytes(b).hex() for b in blocks)


class FrngCmpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_cmp(self, rows, lines, end=None, msx_end=("# result 3 9 0", "# rating 8")):
        a, m = self.tmp / "a.jsonl", self.tmp / "m.txt"
        a.write_text("".join(json.dumps(r) + "\n" for r in rows)
                     + (json.dumps(end) + "\n" if end else ""))
        m.write_text("# D000 DC00 F500\n" + "".join(x + "\n" for x in lines) + "".join(x + "\n" for x in msx_end))
        return self.compare(a, m)

    def compare(self, a, m, skip=()):
        with contextlib.redirect_stdout(io.StringIO()):
            return frngcmp.compare(a, m, 5, FIELDS, skip)

    END = {"result": {"dummy": 3, "correct": 9, "timer": 512, "timeout": 0, "frames": 3},
           "rating": {"text": "calibration", "table": "0c71e", "rating": 2}, "frames": 3}

    def test_the_field_map_has_143_fields(self):
        fl = frngcmp.fields(FIELDS)
        self.assertEqual(len(fl), 143)
        self.assertEqual(len({f["name"] for f in fl}), 143)
        self.assertEqual(frngcmp.FR_CODE_LEN, 526)

    def test_every_field_resolves_on_both_sides(self):
        row = amiga_row(0)
        (self.tmp / "m.txt").write_text("# D000 DC00 F500\n" + msx_line(row) + "\n")
        got = frngcmp.read_msx(self.tmp / "m.txt")[0][0]
        for f in frngcmp.fields(FIELDS):
            self.assertEqual(frngcmp.amiga_bytes(row, f["addr"], f["size"]), frngcmp.msx_bytes(got, f["addr"], f["size"]),
                             f["name"])

    def test_an_exact_port_compares_equal(self):
        rows = [amiga_row(n) for n in range(3)]
        self.assertEqual(self.run_cmp(rows, [msx_line(r) for r in rows], self.END), 0)

    def test_one_wrong_byte_is_reported(self):
        rows = [amiga_row(n) for n in range(3)]
        lines = [msx_line(r) for r in rows]
        lines[1] = msx_line(rows[1], {(0, 0x9A ^ 1): 0x55})     # (cx's low byte: $B9B at D09Ah)
        self.assertEqual(self.run_cmp(rows, lines, self.END), 1)

    def test_a_conditional_field_is_left_out_while_its_flag_is_clear(self):
        # pend.col ($BB5) counts only while pend.hit ($BB2) is set
        rows = [amiga_row(n, {0xBB2: 0}) for n in range(2)]
        lines = [msx_line(r, {(0, 0xB5 ^ 1): 0x77}) for r in rows]
        self.assertEqual(self.run_cmp(rows, lines, None, ()), 0)
        rows = [amiga_row(n, {0xBB2: 1}) for n in range(2)]
        lines = [msx_line(r, {(0, 0xB5 ^ 1): 0x77}) for r in rows]
        self.assertEqual(self.run_cmp(rows, lines, None, ()), 1)

    def test_a_time_out_compares_the_flag_not_the_counts(self):
        rows = [amiga_row(0)]
        end = {"result": {"dummy": 0, "correct": 1186, "timer": 512, "timeout": 255, "frames": 1},
               "rating": {"text": "out of time", "table": "0c72e", "rating": None}, "frames": 1}
        self.assertEqual(self.run_cmp(rows, [msx_line(rows[0])], end, ("# result 0 0 255", "# rating 24")), 0)
        self.assertEqual(self.run_cmp(rows, [msx_line(rows[0])], end, ("# result 0 0 0", "# rating 24")), 1)

    def test_a_wrong_rating_fails(self):
        rows = [amiga_row(n) for n in range(3)]
        self.assertEqual(self.run_cmp(rows, [msx_line(r) for r in rows], self.END, ("# result 3 9 0", "# rating 0")), 1)

    def test_different_row_counts_fail(self):
        rows = [amiga_row(n) for n in range(3)]
        self.assertEqual(self.run_cmp(rows, [msx_line(r) for r in rows[:2]], self.END), 1)

    def test_skip_leaves_a_field_out(self):
        rows = [amiga_row(n) for n in range(2)]
        lines = [msx_line(r, {(1, 0x46 ^ 1): 0x99}) for r in rows]     # (score's first byte: $8046 at DC47h)
        self.assertEqual(self.run_cmp(rows, lines, None, ()), 1)
        a, m = self.tmp / "a.jsonl", self.tmp / "m.txt"
        self.assertEqual(self.compare(a, m, ("score",)), 0)


TCL_MOCK = r"""
array set ::mem {}
set ::bps [dict create]
set ::nbp 0
set ::pause on
set ::extjoy {}
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
mset 0x7F20 0xC9
"""

TCL_DRIVE = TCL_MOCK + r"""
puts "start [rc2_fr_drive t.rom [lindex $argv 1] [lindex $argv 2] [lindex $argv 4] 0 [lindex $argv 3]]"
fire 0x7F10
fire 0x7F20
mset 0xA123 0xCD
mset 0xA124 0x56
mset 0xA125 0xA4
for {set n 0} {$n < 3} {incr n} {
	mset 0xD000 $n
	mset 0xF500 [expr {0x10 + $n}]
	fire 0xA123
}
fire 0x7F20
mset 0xD006 2
mset 0xD004 7
mset 0xDD0C 0x51
mset 0xDD0D 0x99
fire 0x7F10
mset 0x7F20 0x00
fire 0x7F20
mset 0x7F20 0xC9
fire 0x7F20
puts "extjoy $::extjoy"
puts "mem [peek 0xDC4D] [peek 0xD018] [peek 0xD019] [peek 0xF510] [peek 0xDC4C]"
puts "end $::rc2_trace_done {$::rc2_fr_result} $::rc2_fr_rating $::pause [dict size $::bps]"
"""

TCL_TIMEOUT = TCL_MOCK + r"""
set ::pause off
puts "start [rc2_fr_timeout [lindex $argv 1]]"
mset 0xA123 0xCD
mset 0xA124 0x00
mset 0xA125 0x00
fire 0xA123
puts "other [peek 0xDC4D] $::rc2_fr_timeout_done [dict size $::bps]"
mset 0xA124 0x56
mset 0xA125 0xA4
fire 0xA123
puts "first [peek 0xDC4D] $::rc2_fr_timeout_done [dict size $::bps] $::pause"
"""

LABELS = ("fr_code:\tequ $f500\nfr_tick:\tequ $a123\nfr_frame:\tequ $a456\nfr_done:\tequ $7f10\n"
          "fr_rated:\tequ $7f20\next_joy:\tequ $ce5a\nac_diff:\tequ $dd0c\ndiff_tab:\tequ $9941\n"
          "diff_tab_end:\tequ $9961\n")


@unittest.skipUnless(shutil.which("tclsh"), "needs tclsh")
class FrngTclTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "t.labels").write_text(LABELS)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def tclsh(self, script: str, *args) -> dict:
        (self.tmp / "mock.tcl").write_text(script)
        p = subprocess.run(["tclsh", str(self.tmp / "mock.tcl"), str(TCL), str(self.tmp / "t.labels"), *map(str, args)],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, p.stderr)
        return dict(line.split(" ", 1) for line in p.stdout.splitlines())

    def test_rc2_fr_drive_rows_input_result_and_rating(self):
        drive = self.tmp / "t.drive"     # bytes 08 12; at frame 1: $804C = FFh, $B18 = 1234h, lane 7 ($1F509) = 1, $C0000 (skipped)
        drive.write_text("0812\n\n0\n1:0x804c:0xff:1 1:0xb18:0x1234:2 1:0x1f509:1:1 1:0xc0000:5:1\n")
        out = self.tmp / "t.txt"
        got = self.tclsh(TCL_DRIVE, out, drive, 100)
        self.assertEqual(got["extjoy"].split(), ["0", "8", "18", "0"])          # (armed: 0; then the script's bytes)
        # (a byte at A ^ 1; a word little-endian; lane 7, fr_code's 18th byte, at (F500h + 17) ^ 1)
        self.assertEqual(got["mem"].split(), ["255", "52", "18", "1", "0"])
        self.assertEqual(got["end"], "1 {2 7 255} 16 on 0")                     # (DC4Dh poked: the time-out flag)
        lines = out.read_text().splitlines()
        self.assertEqual(lines[0], "# D000 DC00 F500")
        self.assertEqual(lines[-2:], ["# result 2 7 255", "# rating 16"])        # (the stray hits ignored)
        self.assertEqual(lines[3], "# poke 1:0xc0000:5:1 skipped: not in the trace's blocks")
        rows = [line.split() for line in lines[1:-2] if not line.startswith("#")]
        self.assertEqual(len(rows), 3)
        for n, (v, g, c) in enumerate(rows):
            self.assertEqual((len(v), len(g), len(c)), (0xC6 * 2, 0x200, 526 * 2))
            self.assertEqual(v[:4], f"{n:02x}00")
            self.assertEqual(c[:2], f"{0x10 + n:02x}")

    def test_rc2_fr_drive_stops_at_n_lines(self):
        drive = self.tmp / "t.drive"
        drive.write_text("0812\n\n0\n\n")
        out = self.tmp / "t.txt"
        got = self.tclsh(TCL_DRIVE, out, drive, 2)
        self.assertEqual(got["extjoy"].split(), ["0", "8"])                     # (no input after the n-th line)
        self.assertEqual(got["end"], "1 {} -1 on 0")
        self.assertEqual(len(out.read_text().splitlines()), 3)

    def test_rc2_fr_timeout_pokes_the_flag_once_at_the_stage_tick(self):
        got = self.tclsh(TCL_TIMEOUT)
        self.assertEqual(got["other"], "0 0 1")                  # (other bytes at fr_tick: another bank, no poke)
        self.assertEqual(got["first"], "255 1 0 off")            # (DC4Dh = FFh, its breakpoint gone, not paused)

    def test_frngmock_on_a_synthetic_trace(self):
        rows = [amiga_row(n, {0xB00: 0, 0xB01: n}) for n in range(4)]     # ($B00: the frame index)
        end = FrngCmpTests.END | {"result": FrngCmpTests.END["result"] | {"frames": 4}}
        (self.tmp / "a.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows) + json.dumps(end) + "\n")
        (self.tmp / "d.drive").write_text("0a0010\n\n0\n2:0x802e:0x1f:1\n")
        p = subprocess.run([sys.executable, "-I", str(MOCK), str(self.tmp / "a.jsonl"), str(self.tmp / "d.drive"),
                            str(self.tmp / "out")], capture_output=True, text=True, timeout=120)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("equal to the drive's bytes: True; the drive's 1 pokes at their MSX addresses: True", p.stdout)
        self.assertIn("4 FRNG frames compared (4 Amiga, 4 MSX), 143 fields: 0 differ", p.stdout)
        p = subprocess.run([sys.executable, "-I", str(MOCK), str(self.tmp / "a.jsonl"), str(self.tmp / "d.drive"),
                            str(self.tmp / "bad"), "--corrupt", "2:0xD09A:0x99"], capture_output=True, text=True,
                           timeout=120)
        self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
        self.assertIn("FRNG frame 2 (-): cx", p.stdout)


def frngbot_or_skip(test: unittest.TestCase):
    try:
        import frngbot
    except (ImportError, SystemExit):              # (amigaemu.py exits without Unicorn)
        test.skipTest("needs Unicorn")
    return frngbot


class BotRuleTests(unittest.TestCase):
    def test_counts_as_follows_each_handler(self):
        frngbot = frngbot_or_skip(self)
        bot = frngbot.Bot.__new__(frngbot.Bot)
        popup = {"kind": "popup", "x": 0x100 + 4, "thr": 24}            # (x & 15 = 4: the column is c + 4)
        self.assertEqual(bot.counts_as(popup, 19), "correct")           # column 23
        self.assertEqual(bot.counts_as(popup, 20), "dummy")             # column 24
        self.assertEqual(bot.counts_as(dict(popup, thr=0), 0), "dummy")
        moving = {"kind": "moving", "x": 0x100, "thr": 0}
        self.assertEqual(bot.counts_as(moving, 0), "correct")           # (T1's handler: thr >= column)
        self.assertEqual(bot.counts_as(moving, 1), "dummy")
        self.assertEqual(bot.counts_as({"kind": "rising", "x": 0}, 30), "correct")

    def test_fuzz_keys_follow_the_seed(self):
        frngbot = frngbot_or_skip(self)
        a = [frngbot.FuzzBot(21).choose({"frame": n, "cx": 0, "cy": 0, "ammo": 0}) for n in range(1)]
        b1, b2 = frngbot.FuzzBot(21), frngbot.FuzzBot(21)
        k1 = [b1.choose({"frame": n, "cx": 0, "cy": 0, "ammo": 0}) for n in range(300)]
        k2 = [b2.choose({"frame": n, "cx": 0, "cy": 0, "ammo": 0}) for n in range(300)]
        self.assertEqual(k1, k2)
        self.assertEqual(k1[0], a[0])
        for k in k1:                                   # (no opposite directions; the drive file's order)
            self.assertFalse(("u" in k and "d" in k) or ("l" in k and "r" in k), k)
            self.assertEqual(k, "".join(c for c in "udlrf" if c in k))
        # the logic report's fuzz(): a key set held 1-29 frames, fire added in 35 % of the frames
        rnd = random.Random(21)
        want, left, cur = [], 0, ""
        for _ in range(300):
            if left <= 0:
                cur = rnd.choice(["", "u", "d", "l", "r", "ul", "ur", "dl", "dr"])
                left = rnd.randrange(1, 30)
            left -= 1
            k = cur + ("f" if rnd.random() < 0.35 else "")
            want.append("".join(c for c in "udlrf" if c in k))
        self.assertEqual(k1, want)

    def test_targets_reads_the_slots_and_the_pending_draw(self):
        frngbot = frngbot_or_skip(self)
        mem = bytearray(0x20000)

        def w(a, v):
            mem[a:a + 2] = (v & 0xFFFF).to_bytes(2, "big")
        # slot 0 ($B2E): type 2, its record's handler offset -> a stub 'lea desc,A0' at $1F600 (desc $1F700)
        mem[0xB2E] = 1                                  # (the long at A3 not 0: the pop-up runs)
        mem[0xB36] = 2
        w(frngbot.TYPES + 16, 0x1F600 - (frngbot.TYPES + 16))
        w(0x1F602, 0x1F700 - 0x1F602)
        w(0x1F702, 200)                                 # x
        w(0x1F704, 90)                                  # y, + the slot's offset (-$1E,A3)
        w(0xB2E - 0x1E, 0xFFFE)
        w(0x1F70C, 30 << 6 | 3)                         # BLTSIZE: 30 rows, 3 words
        w(0x1F714, 24)                                  # the threshold
        w(0xBA8, 40 << 6 | 5)                           # the pending draw: 40 rows, 5 words at (300, 60)
        w(0xBAE, 300)
        w(0xBB0, 60)
        got = frngbot.targets(lambda a, n: mem[a:a + n])
        self.assertEqual(got, [(200, 88, 2, 30, "popup", 24), (300, 60, 4, 40, "big", 99)])
        mem[0x1F70B] = 1                                # (the horizontal flag: x and y swapped)
        self.assertEqual(frngbot.targets(lambda a, n: mem[a:a + n])[0][:2], (88, 200))


@unittest.skipUnless(LEVEL1_RAM.exists() and (EXTRACTED / "files").exists(), "needs build/ram and build/extracted")
class BenchTests(unittest.TestCase):
    def setUp(self):
        try:
            import amigaemu
        except (ImportError, SystemExit):
            self.skipTest("needs Unicorn")
        self.ae = amigaemu

    def test_a_scripted_shot_hits_the_first_armed_target(self):
        b = self.ae.FrngBench(EXTRACTED, LEVEL1_RAM)
        b.setup(1)
        rows = b.play(40, [(0, 11, "dr"), (11, 18, "r"), (32, 1, "f")])
        self.assertEqual((rows[35]["correct"], rows[36]["correct"]), (0, 1))
        self.assertEqual((rows[36]["cx"], rows[36]["cy"], rows[36]["ammo"]), (356, 116, 0x24))
        self.assertEqual(rows[36]["dummy"], 0)

    def test_fire_held_spends_the_ammo_and_rates_poor(self):
        b = self.ae.FrngBench(EXTRACTED, LEVEL1_RAM)
        b.setup(1)
        b.play(3000, [(0, 800, "f")])
        self.assertEqual(b.fframes_run, 732)
        self.assertEqual((b.returned["dummy"], b.returned["correct"], b.returned["timeout"]), (0, 0, 0))
        self.assertEqual((b.rating["table"], b.rating["rated"]), ("0c72e", "POORe   "))

    def test_a_time_out_poke_returns_at_once(self):
        b = self.ae.FrngBench(EXTRACTED, LEVEL1_RAM)
        b.setup(1)
        b.play(3000, [], pokes=[(20, 0x804C, 0xFF, 1)])
        self.assertEqual(b.fframes_run, 21)
        self.assertEqual((b.returned["timeout"], b.rating["text"], b.rating["table"]), (255, "out of time", "0c72e"))


if __name__ == "__main__":
    unittest.main()
