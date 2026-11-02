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
- Batch 2's recalibration (docs/HARNESS.md 12.2): with timing controls beside the base (BASE/<gate>/ctl/),
  each verdict passes a value inside the reference set's range and fails one beyond it (speed: lowest -
  spread; FB_HOLD pictures and tears: highest + spread; a field class none of them shows); a control
  lacking a run fails; a teleport's stall and the field records past a drive's end are left out; the kit's
  tables match gates.tcl's (drives, windows) and gate.sh's level-3 lock build is LOCKSTEP=48.
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

    def test_ref_tables_match_gates_tcl(self):
        # ref.py's drives (file, rows) are gates.tcl's ::pf_drives; fieldsum.py's window prefixes name the drive
        # whose file gates.tcl's ::pf_field_wins records each window on; level 3's lock build has LOCKSTEP 48
        sys.path.insert(0, str(KIT))
        import fieldsum
        import ref
        tcl = (KIT / "gates.tcl").read_text()
        drives = re.search(r"array set ::pf_drives \{(.*?)\n\}", tcl, re.S).group(1)
        got = {m[0]: (m[2], int(m[3])) for m in re.findall(r"(\w+)\s+\{(\S+) (\S+) (\d+)\}", drives)}
        self.assertEqual(got, ref.DRIVES)
        wins = re.search(r"set ::pf_field_wins \{(.*?)\n\}", tcl, re.S).group(1)
        n = 0
        for w, lv, b, drv, frm, cnt in re.findall(r"(\w+)\s+(\d) (\S+) (\S+)\s+(\d+) (\d+)", wins):
            d = [dn for pre, dn in fieldsum.WIN_DRIVES if w.startswith(pre)]
            if drv.startswith("drive_cov"):
                self.assertEqual(d, [], w)
            else:
                self.assertEqual(ref.DRIVES[d[0]][0], drv, w)
                n += 1
        self.assertEqual(n, 18)
        gate = (KIT / "gate.sh").read_text()
        self.assertIn("b L/l3/lock.rom EXTJOY=1 LV_TEST=3 LOCKSTEP=48", gate)
        self.assertNotIn("0x0890", (ROOT / "tools" / "bstest" / "fieldcheck.py").read_text())
        self.assertIn("rd_head", tcl)

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

    def test_win_with_controls(self):
        # the reference set: BASE (0.1 s a tick) and two controls (+1 %, -0.5 %): NEW passes down to the lowest
        # minus the spread (the floor 0.5 % being smaller), fails beyond; a control lacking the run fails
        self.speed_run(self.base / "speed", "kill_m2")
        for c, slow in (("ct1", 1.01), ("ct2", 0.995)):
            (self.base / "speed" / "ctl" / c).mkdir(parents=True)
            self.speed_run(self.base / "speed" / "ctl" / c, "kill_m2", slow=slow)
        self.speed_run(self.new / "speed", "kill_m2", slow=1.022)
        r = run(KIT / "win.py", "--gate", self.base / "speed", self.new / "speed")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("ref", r.stdout)
        self.speed_run(self.new / "speed", "kill_m2", slow=1.04)
        r = run(KIT / "win.py", "--gate", self.base / "speed", self.new / "speed")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.speed_run(self.new / "speed", "kill_m2")
        (self.base / "speed" / "ctl" / "ct2" / "kill_m2_ticks.txt").unlink()
        r = run(KIT / "win.py", "--gate", self.base / "speed", self.new / "speed")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("control", r.stdout)

    def test_win_and_holds_leave_teleports_out(self):
        # a drive with a teleport at tick 500: NEW stalls 30 s there (its ticks held while the engines walk)
        # and holds a picture there: both verdicts pass, the stall left out; without the teleport both fail
        emu = self.tmp / "emu"
        emu.mkdir()
        (emu / "l3_kill.drive").write_text("00" * 1900 + "\n500:300:112\n0\n\n")
        self.speed_run(self.base / "speed", "kill_m2")
        self.speed_run(self.new / "speed", "kill_m2")
        for name in ("kill_m2_ticks.txt", "kill_m2_pics.txt"):
            p = self.new / "speed" / name
            out = []
            for line in p.read_text().splitlines():
                f = line.split()
                t = float(f[0] if name.endswith("pics.txt") else f[1])
                k = int(f[1] if name.endswith("pics.txt") else f[0])
                if k > 500 or (name.endswith("pics.txt") and k == 500):
                    t += 30.0
                f[0 if name.endswith("pics.txt") else 1] = f"{t:.6f}"
                if name.endswith("pics.txt") and k == 500:
                    f[2] = "8"
                out.append(" ".join(f))
            p.write_text("\n".join(out) + "\n")
        for script in ("win.py", "holds.py"):
            r = run(KIT / script, "--gate", self.base / "speed", self.new / "speed", "--emu", emu)
            self.assertEqual(r.returncode, 0, script + r.stdout)
        (emu / "l3_kill.drive").write_text("00" * 1900 + "\n\n0\n\n")
        for script in ("win.py", "holds.py"):
            r = run(KIT / script, "--gate", self.base / "speed", self.new / "speed", "--emu", emu)
            self.assertEqual(r.returncode, 1, script + r.stdout)
        # --emu names a folder without the drive file: an error, not a silent pass
        r = run(KIT / "win.py", "--gate", self.base / "speed", self.new / "speed", "--emu", self.tmp / "none")
        self.assertNotEqual(r.returncode, 0, r.stdout)

    def holds_run(self, d, name, n):
        # a run whose pictures reach FB_HOLD n times (ticks 100, 101, ...)
        with open(d / f"{name}_ticks.txt", "w") as ft, open(d / f"{name}_pics.txt", "w") as fp:
            for k in range(1900):
                ft.write(f"{k} {10 + 0.1 * k:.6f} 0\n")
                fp.write(f"{10.01 + 0.1 * k:.6f} {k} {8 if 100 <= k < 100 + n else 0} {k} {k}\n")

    def test_holds_with_controls(self):
        # BASE 4, controls 6 and 3: FAIL above 6 + max(3, 2) = 9
        self.holds_run(self.base / "speed", "boss_fx", 4)
        for c, n in (("ct1", 6), ("ct2", 3)):
            (self.base / "speed" / "ctl" / c).mkdir(parents=True)
            self.holds_run(self.base / "speed" / "ctl" / c, "boss_fx", n)
        self.holds_run(self.new / "speed", "boss_fx", 9)
        r = run(KIT / "holds.py", "--gate", self.base / "speed", self.new / "speed")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.holds_run(self.new / "speed", "boss_fx", 10)
        r = run(KIT / "holds.py", "--gate", self.base / "speed", self.new / "speed")
        self.assertEqual(r.returncode, 1, r.stdout)

    def test_guardsum_with_controls(self):
        # tears 100, 104, 110: FAIL above 110 + max(10, 3, 6) = 120; a patcheck bad entry fails
        rec = "rows: 1861\nguard: reg 0, pal 0, cmd 749, cpu 0, vbl 2, tear {t}\npatcheck: 81437 entries, {b} bad\n"
        (self.base / "guard" / "kill_fx.txt").write_text(rec.format(t=100, b=0))
        for c, t in (("ct1", 104), ("ct2", 110)):
            (self.base / "guard" / "ctl" / c).mkdir(parents=True)
            (self.base / "guard" / "ctl" / c / "kill_fx.txt").write_text(rec.format(t=t, b=0))
        (self.new / "guard" / "kill_fx.txt").write_text(rec.format(t=120, b=0))
        self.assertEqual(run(KIT / "guardsum.py", "gate", self.base / "guard", self.new / "guard").returncode, 0)
        (self.new / "guard" / "kill_fx.txt").write_text(rec.format(t=121, b=0))
        self.assertEqual(run(KIT / "guardsum.py", "gate", self.base / "guard", self.new / "guard").returncode, 1)
        (self.new / "guard" / "kill_fx.txt").write_text(rec.format(t=100, b=1))
        self.assertEqual(run(KIT / "guardsum.py", "gate", self.base / "guard", self.new / "guard").returncode, 1)

    def test_fieldsum_with_controls_teleports_and_end(self):
        # a class only a control shows passes; one none shows fails from 4 pictures (or above what another
        # machine's same window shows); left out: the records of a teleport's stall (game frames T .. T + 2),
        # the class "other" up to T + 39, the records past the end
        def win(d, classes):
            w = d / "kill300_m2"
            w.mkdir(parents=True, exist_ok=True)
            (w / "level.txt").write_text("level 3 from 300 n 60 drive l3_kill.drive rows 355 tele 320 rom x.rom\n")
            stems = [f"j001_f{k:04d}" for k in range(60)]
            (w / "holds.txt").write_text("".join(f"{s} 0 {300 + k} {300 + k} 0 0\n" for k, s in enumerate(stems)))
            lines = [f"CLASS j001_f{k:04d} {c} px=10" for k, c in classes]
            (d / "kill300_m2.fc.txt").write_text("\n".join(lines + ["60 pictures (60 checked): 0 with differences"]) + "\n")

        def gate():
            return run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field")
        win(self.base / "field", [])
        win(self.base / "field" / "ctl" / "ct1", [(k, "hostage-tear") for k in (5, 6, 7)])
        win(self.new / "field", [(k, "hostage-tear") for k in (8, 9, 10, 11, 12, 13)])
        r = gate()
        self.assertEqual(r.returncode, 0, r.stdout)          # 6 against the control's 3: within 3 + max(3, 3)
        win(self.new / "field", [(k, "hostage-tear") for k in range(8, 15)])
        self.assertEqual(gate().returncode, 1)               # 7: above
        win(self.new / "field", [(k, "other") for k in (1, 2, 3, 4)])
        self.assertEqual(gate().returncode, 1)               # a class none shows, 4 pictures
        win(self.new / "field", [(k, "other") for k in (20, 21, 22, 23, 24, 30, 55, 56, 57)])
        r = gate()
        self.assertEqual(r.returncode, 0, r.stdout)          # the stall, "other" after it, past the end
        self.assertIn("left out", gate().stdout + run(KIT / "fieldsum.py", "table", self.new / "field").stdout)
        win(self.new / "field", [(k, "smoke-tear") for k in (23, 24, 25, 26)])
        self.assertEqual(gate().returncode, 1)               # after the stall another class is judged
        # a control lacking the window fails
        shutil.rmtree(self.base / "field" / "ctl" / "ct1" / "kill300_m2")
        win(self.new / "field", [])
        r = gate()
        self.assertEqual(r.returncode, 1, r.stdout)

    def pics_every(self, d, name, step):
        # the run's pictures thinned to one in STEP (its ticks unchanged)
        p = d / f"{name}_pics.txt"
        lines = p.read_text().splitlines()
        p.write_text("".join(x + "\n" for k, x in enumerate(lines) if k % step == 0))

    def test_win_level1_frame_rate(self):
        # level 1's play "must stay at 25 ticks/s and 25 pictures/s": with its ticks/s unchanged, half its
        # pictures fail l1play; the same on kill (pictures/s reported, not judged) passes
        for d in (self.base, self.new):
            self.speed_run(d / "speed", "l1play_m2")
            self.speed_run(d / "speed", "kill_m2")
        self.assertEqual(run(KIT / "win.py", "--gate", self.base / "speed", self.new / "speed").returncode, 0)
        self.pics_every(self.new / "speed", "kill_m2", 2)
        r = run(KIT / "win.py", "--gate", self.base / "speed", self.new / "speed")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.pics_every(self.new / "speed", "l1play_m2", 2)
        r = run(KIT / "win.py", "--gate", self.base / "speed", self.new / "speed")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("pictures/s", r.stdout)

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

    def test_fieldsum_stale_check(self):
        # a window recorded again after its check (level.txt newer than its .fc.txt) fails the gate until
        # fieldsum.py run checks it again (here with a stand-in checker that finds no difference)
        import os
        self.field_window(self.base, [])
        self.field_window(self.new, [])
        self.assertEqual(run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field").returncode, 0)
        fc = self.new / "field" / "kill300_m2.fc.txt"
        lv = self.new / "field" / "kill300_m2" / "level.txt"
        old = lv.stat().st_mtime - 20                      # (the check made 20 s before the new recording)
        os.utime(fc, (old, old))
        r = run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("predates", r.stdout)
        fake = self.tmp / "fakecheck.py"
        fake.write_text("import sys, pathlib\nn = len(list(pathlib.Path(sys.argv[1]).glob('*.bin')))\n"
                        "print(f'{n} pictures ({n} checked): 0 with differences, 0 pixels')\n")
        run(KIT / "fieldsum.py", "run", self.new / "field", "--py", sys.executable, "--check", fake, "--root", self.tmp)
        self.assertGreater(fc.stat().st_mtime, old)        # (checked again)
        self.assertEqual(run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field").returncode, 0)

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
        tears = [(f"j001_f{k:04d}", "hostage-tear") for k in (7, 8, 9, 10)]
        self.field_window(self.new, [("j001_f0005", "other")] + tears, hold_stems={s for s, _ in tears})
        # the new hostage tears are at FB_HOLD (G-HOLD's class): passes
        self.assertEqual(run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field").returncode, 0)
        # a class the base does not show: 1-3 pictures WARN (a timing shift alone made such), 4 fail
        self.field_window(self.new, [("j001_f0005", "other")] + tears[:3])
        r = run(KIT / "fieldsum.py", "gate", self.base / "field", self.new / "field")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("WARN", r.stdout)
        self.field_window(self.new, [("j001_f0005", "other")] + tears)
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
