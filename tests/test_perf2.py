"""Performance campaign 2's kit (tools/bstest/perf2, docs/HARNESS.md section 12) without an emulator.

- Every Python script compiles; every Tcl file is a complete script with no exit, vwait, max or min
  outside comments; gate.sh parses; no file holds an absolute path of this machine.
- Each gate's verdict on made-up records in the formats the kit's Tcl writes: it passes when the new
  records equal the base's and fails on a mutated copy (a check that cannot fail is worse than none):
  win.py (a window 2 % slower), holds.py (one more FB_HOLD picture), mapdiff.py (one map byte),
  guardsum.py (one more tear), fieldsum.py (a new difference class; a gross rise of a class the base
  shows), lockgate.py (one SAT byte; the lists after a late frame not judged).
- Records missing or cut short fail every verdict (an empty run folder must not pass): a run, window,
  dump or record the base holds and the new folder lacks (--partial: not judged), a run that ended
  early, a map dump with fewer ticks, a field check that stopped or checked fewer records.
"""
import json
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "tools" / "bstest" / "perf2"


def run(*args):
    return subprocess.run([sys.executable, "-I", *map(str, args)], capture_output=True, text=True)


class KitFilesTests(unittest.TestCase):
    def test_python_compiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            for p in sorted(KIT.glob("*.py")):
                py_compile.compile(str(p), cfile=str(Path(tmp) / (p.stem + ".pyc")), doraise=True)

    @unittest.skipUnless(shutil.which("tclsh"), "needs tclsh")
    def test_tcl_complete_without_exit_vwait_max_min(self):
        for p in sorted(KIT.glob("*.tcl")):
            r = subprocess.run(["tclsh"], input=f"set f [open {{{p}}}]; set s [read $f]; close $f; puts [info complete $s]\n",
                               capture_output=True, text=True)
            self.assertEqual(r.stdout.strip(), "1", p.name + r.stderr)
            code = "\n".join(line for line in p.read_text().splitlines() if not line.lstrip().startswith("#"))
            for bad in (r"\bexit\b", r"\bvwait\b", r"\bmax\s*\(", r"\bmin\s*\("):
                self.assertIsNone(re.search(bad, code), f"{p.name}: {bad}")

    def test_gate_sh_parses_and_no_machine_paths(self):
        self.assertEqual(subprocess.run(["sh", "-n", str(KIT / "gate.sh")]).returncode, 0)
        for p in sorted(KIT.iterdir()):
            if p.is_file() and p.suffix in (".py", ".tcl", ".sh"):
                text = p.read_text()
                for s in ("/private/tmp", "/Users/", "scratchpad"):
                    self.assertNotIn(s, text, p.name)

    def test_gate_sh_logic_names_every_compared_job(self):
        # G-LOGIC names each trace (hz.sh compare skips an unnamed one that is missing): the names must be
        # hz.sh's compared jobs of each level, all of them
        hz = (ROOT / "tools" / "bstest" / "hz.sh").read_text()
        lists = re.findall(r'JOBS="([^"]*)"', hz)
        l2, l3 = ({j.split(":")[0] for j in s.split()} for s in lists[:2])
        gate = (KIT / "gate.sh").read_text()
        self.assertEqual(set(re.search(r'L3J="([^"]*)"', gate).group(1).split()), l3)
        self.assertEqual(set(re.search(r'L2J="([^"]*)"', gate).group(1).split()), l2)
        self.assertEqual((len(l3), len(l2)), (16, 23))


class KitVerdictTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.base, self.new = self.tmp / "base", self.tmp / "new"
        for d in (self.base, self.new):
            for g in ("speed", "map", "guard", "field", "lock"):
                (d / g).mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    # m3.tcl's records: ticks "tick_n time ...", pics "time tick fb_hold game_frame vblank"
    def speed_run(self, d, name, slow=1.0, extra_hold=False, ticks=1900):
        t = 10.0
        with open(d / f"{name}_ticks.txt", "w") as ft, open(d / f"{name}_pics.txt", "w") as fp:
            for k in range(ticks):
                ft.write(f"{k} {t:.6f} 0 0 0 0 0.0 0 0 0 0 0\n")
                fp.write(f"{t + 0.01:.6f} {k} {8 if (k % 400 == 0 or (extra_hold and k == 777)) else 0} {k} {k}\n")
                t += 0.1 * slow

    def test_win_and_holds(self):
        for d in (self.base, self.new):
            self.speed_run(d / "speed", "kill_m2")
        self.assertEqual(run(KIT / "win.py", "--gate", self.base / "speed", self.new / "speed").returncode, 0)
        self.assertEqual(run(KIT / "holds.py", "--gate", self.base / "speed", self.new / "speed").returncode, 0)
        self.speed_run(self.new / "speed", "kill_m2", slow=1.02, extra_hold=True)
        r = run(KIT / "win.py", "--gate", self.base / "speed", self.new / "speed")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("FAIL", r.stdout)
        self.assertEqual(run(KIT / "holds.py", "--gate", self.base / "speed", self.new / "speed").returncode, 1)

    def test_win_and_holds_missing_runs(self):
        for d in (self.base, self.new):
            self.speed_run(d / "speed", "kill_m2")
        self.speed_run(self.base / "speed", "boss_m2")
        # the new folder lacks boss_m2: both fail; --partial judges kill_m2 alone
        for script in ("win.py", "holds.py"):
            r = run(KIT / script, "--gate", self.base / "speed", self.new / "speed")
            self.assertEqual(r.returncode, 1, script + r.stdout)
            self.assertIn("no new run", r.stdout)
            self.assertEqual(run(KIT / script, "--gate", self.base / "speed", self.new / "speed", "--partial").returncode, 0)
        # an empty new folder judges nothing: fails, --partial too
        empty = self.tmp / "empty"
        empty.mkdir()
        for script in ("win.py", "holds.py"):
            self.assertEqual(run(KIT / script, "--gate", self.base / "speed", empty, "--partial").returncode, 1, script)
        # a run that ended early (its last tick 1500 of 1899): holds.py fails on the span
        self.speed_run(self.new / "speed", "boss_m2", ticks=1501)
        r = run(KIT / "holds.py", "--gate", self.base / "speed", self.new / "speed")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("ticks 0-1500", r.stdout)

    def test_mapdiff(self):
        a = "00" * 0x6F0
        b = "00" * 0xF1A
        c = "00" * 0x500
        for d in (self.base, self.new):
            (d / "map" / "tour3_m2_map.txt").write_text(f"0 {a} {b} {c}\n100 {a} {b} {c}\n")
        self.assertEqual(run(KIT / "mapdiff.py", "--gate", self.base / "map", self.new / "map").returncode, 0)
        b2 = b[:6] + "ff" + b[8:]          # 1085h: the redraw queue's head, never compared
        (self.new / "map" / "tour3_m2_map.txt").write_text(f"0 {a} {b2} {c}\n100 {a} {b} {c}\n")
        self.assertEqual(run(KIT / "mapdiff.py", "--gate", self.base / "map", self.new / "map").returncode, 0)
        a2 = "01" + a[2:]                  # 0910h: a map byte
        (self.new / "map" / "tour3_m2_map.txt").write_text(f"0 {a} {b} {c}\n100 {a2} {b} {c}\n")
        self.assertEqual(run(KIT / "mapdiff.py", "--gate", self.base / "map", self.new / "map").returncode, 1)
        self.assertEqual(run(KIT / "mapdiff.py", "--gate", self.base / "map", self.new / "map",
                             "--ignore", "0910-0910").returncode, 0)
        # a dump cut short (tick 100 missing) fails, --partial too; a dump the new folder lacks fails
        (self.new / "map" / "tour3_m2_map.txt").write_text(f"0 {a} {b} {c}\n")
        for extra in ((), ("--partial",)):
            self.assertEqual(run(KIT / "mapdiff.py", "--gate", self.base / "map", self.new / "map", *extra).returncode, 1)
        (self.new / "map" / "tour3_m2_map.txt").write_text(f"0 {a} {b} {c}\n100 {a} {b} {c}\n")
        (self.base / "map" / "park_m2_map.txt").write_text(f"0 {a} {b} {c}\n")
        self.assertEqual(run(KIT / "mapdiff.py", "--gate", self.base / "map", self.new / "map").returncode, 1)
        self.assertEqual(run(KIT / "mapdiff.py", "--gate", self.base / "map", self.new / "map", "--partial").returncode, 0)

    def test_guardsum(self):
        rec = "rows: 1861\nguard: reg 0, pal 0, cmd 749, cpu 0, vbl 2, tear {t}\npatcheck: 81437 entries, 0 bad\n" \
              "sprlines: 9 frames with a line above 8\nsatcheck: 1 frames differ (mux 0)\n"
        (self.base / "guard" / "kill_m2.txt").write_text(rec.format(t=124))
        (self.new / "guard" / "kill_m2.txt").write_text(rec.format(t=124))
        self.assertEqual(run(KIT / "guardsum.py", "gate", self.base / "guard", self.new / "guard").returncode, 0)
        (self.new / "guard" / "kill_m2.txt").write_text(rec.format(t=125))
        self.assertEqual(run(KIT / "guardsum.py", "gate", self.base / "guard", self.new / "guard").returncode, 1)
        # a record the new folder lacks fails (--partial: not judged)
        (self.new / "guard" / "kill_m2.txt").write_text(rec.format(t=124))
        (self.base / "guard" / "boss_m2.txt").write_text(rec.format(t=9))
        self.assertEqual(run(KIT / "guardsum.py", "gate", self.base / "guard", self.new / "guard").returncode, 1)
        self.assertEqual(run(KIT / "guardsum.py", "gate", self.base / "guard", self.new / "guard", "--partial").returncode, 0)

    def field_window(self, d, classes, hold_stems=(), name="kill300_m2", records=60, summary=None):
        w = d / "field" / name
        w.mkdir(parents=True, exist_ok=True)
        (w / "level.txt").write_text("level 3 from 300 n 60\n")
        stems = [f"j001_f{k:04d}" for k in range(records)]
        (w / "holds.txt").write_text("".join(f"{s} {8 if s in hold_stems else 0} 300 300\n" for s in stems))
        for s in stems:
            (w / f"{s}.bin").write_bytes(b"")
        lines = [f"CLASS {s} {k} px=10" for s, k in classes]
        if summary is None:
            summary = f"{records} pictures ({records} checked): {len(classes)} with differences, 0 pixels"
        (d / "field" / f"{name}.fc.txt").write_text("\n".join(lines + [summary]) + "\n")

    def test_fieldsum_incomplete(self):
        self.field_window(self.base, [("j001_f0001", "other")])
        for kw in ({"records": 40},                                             # a recording cut short
                   {"summary": "STDERR Traceback (most recent call last):"},    # the check stopped
                   {"summary": "60 pictures (0 checked): 0 with differences"}):  # records of another length
            self.field_window(self.new, [], **kw)
            r = run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field")
            self.assertEqual(r.returncode, 1, f"{kw} {r.stdout}")
        self.field_window(self.new, [("j001_f0001", "other")])
        self.assertEqual(run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field").returncode, 0)
        # a window the new folder lacks fails (--partial: not judged)
        self.field_window(self.base, [], name="boss110_m2")
        self.assertEqual(run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field").returncode, 1)
        self.assertEqual(run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field", "--partial").returncode, 0)

    def test_fieldsum(self):
        self.field_window(self.base, [("j001_f0001", "other"), ("j001_f0002", "other")], hold_stems={"j001_f0002"})
        self.field_window(self.new, [("j001_f0005", "other"), ("j001_f0007", "hostage-tear")], hold_stems={"j001_f0007"})
        # the new hostage tear is at FB_HOLD (G-HOLD's class): passes
        self.assertEqual(run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field").returncode, 0)
        self.field_window(self.new, [("j001_f0005", "other"), ("j001_f0007", "hostage-tear")])
        self.assertEqual(run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field").returncode, 1)
        self.field_window(self.new, [(f"j001_f{k:04d}", "other") for k in range(40)])
        r = run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field")
        self.assertEqual(r.returncode, 1, r.stdout)          # 40 against 1: a gross rise of a known class

    def lock_record(self, path, sat_byte=0, late=""):
        park = 217
        lines = ["0 0 217 0 " + "d8" * 256 + " " + "00" * 512 + " " + "00" * 2048 + " " + "00" * 128 + " 0 0"]
        for gf in range(2, 202, 2):
            sat = bytes([100, 50, (4 * (gf % 3)) & 255, 0]) + bytes([216]) + bytes(251)
            if gf == 150 and sat_byte:
                sat = bytes([100, 50 + sat_byte]) + sat[2:]
            lines.append(f"{gf // 2} {gf} {park} 0 {sat.hex()} {'0f' * 512} {'aa' * 2048} {'00' * 128} 100 200")
        path.write_text("\n".join(lines) + "\n")
        Path(str(path)[:-4] + ".over").write_text(late or "late 0 at \n")

    def test_lockgate(self):
        self.lock_record(self.base / "lock" / "kill_m2.txt")
        self.lock_record(self.new / "lock" / "kill_m2.txt")
        self.assertEqual(run(KIT / "lockgate.py", self.base / "lock", self.new / "lock").returncode, 0)
        self.lock_record(self.new / "lock" / "kill_m2.txt", sat_byte=1)
        self.assertEqual(run(KIT / "lockgate.py", self.base / "lock", self.new / "lock").returncode, 1)
        self.lock_record(self.base / "lock" / "kill_m2.txt", late="late 1 at 120\n")
        r = run(KIT / "lockgate.py", self.base / "lock", self.new / "lock")
        self.assertEqual(r.returncode, 0, r.stdout)            # after the base's late frame: not judged
        self.assertIn("not judged", r.stdout)
        # a record the new folder lacks fails (--partial: not judged)
        self.lock_record(self.base / "lock" / "boss_m2.txt")
        self.assertEqual(run(KIT / "lockgate.py", self.base / "lock", self.new / "lock").returncode, 1)
        self.assertEqual(run(KIT / "lockgate.py", self.base / "lock", self.new / "lock", "--partial").returncode, 0)


if __name__ == "__main__":
    unittest.main()
