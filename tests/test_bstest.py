"""The Brainstorm acceptance harness (tools/bstest/, docs/HARNESS.md) without an emulator.

- Every Python tool compiles and imports, and the repository tools it calls still have the names it
  uses; the helpers on made-up data (relocheck, romdiff, fixblank, hudcheck, stepcheck's parsers,
  shots, frozen, restorecheck's known items).
- The shell scripts parse (sh -n); build.sh, hz.sh builds and variants.sh run against a stub
  tools/mkrom.py in a source tree of their own (SRC=), so that a broken refusal could never write
  into build/msx; hz.sh fresh compares records.
- Every Tcl file is a complete script with no exit, vwait, max or min outside comments; in tclsh
  with openMSX's commands mocked: load.tcl finds the repository, hz_chain runs, times out and stops
  on errors, hz_clean closes the channels a job left open, hz_fresh's and hz_bonus's records have
  the layout hz.sh and bonuscheck.py read, hz7.tcl's snapshot and record the layout stepcheck.py
  reads, the suite's job lists, c8's key presses and hzf_done, and no channel is left open.

The bonuscheck case needs build/ram/level1_full.bin and build/msx/text_bs_*.sc5 (make msx), the
restorecheck one build/msx/level1.vram; the Tcl cases need tclsh. Each is skipped without them."""
import importlib
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BST = ROOT / "tools" / "bstest"
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(BST))

FILES = {"build.sh", "hz.sh", "check_all.sh", "variants.sh", "hz.tcl", "hz6.tcl", "hz7.tcl", "fixchk.tcl",
         "suite.tcl", "c8.tcl", "run8.tcl", "load.tcl", "bonuscheck.py", "stepcheck.py", "restorecheck.py",
         "hudcheck.py", "shots.py", "relocheck.py", "romdiff.py", "fixblank.py", "frozen.py"}
LEVEL1_RAM = ROOT / "build" / "ram" / "level1_full.bin"
TEXT_SC5 = [ROOT / "build" / "msx" / f"text_bs_{n}.sc5" for n in ("intro", "time")]
LEVEL1_VRAM = ROOT / "build" / "msx" / "level1.vram"
SNAP_LEN = 0x20000 + 0x4000 + 64 + 32           # hz7_snap: VRAM, RAM C000h-FFFFh, VDP registers, palette


def run(cmd: list, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=120, **kw)


def png_size(path: Path) -> tuple[int, int]:
    d = path.read_bytes()
    assert d[:8] == b"\x89PNG\r\n\x1a\n" and d[12:16] == b"IHDR"
    return int.from_bytes(d[16:20], "big"), int.from_bytes(d[20:24], "big")


def snapshot(pf_pal: bytes = bytes(range(32)), page_byte: int = 0x12) -> bytearray:
    """A made-up hz7_snap file: page 0 filled with page_byte, the applied list at C100h showing page 0
    with sprites off (R#2 1Fh, R#8 0Ah, R#5 C7h, list $B00 1234h), pf_pal and SR_PAL set."""
    d = bytearray(SNAP_LEN)
    d[0:20736] = bytes([page_byte]) * 20736
    ram = 0x20000
    d[ram + 3], d[ram + 4] = 0x00, 0xC1
    lst = bytes([1, 6, 0x1F, 0x82, 0x0A, 0x88, 0xC7, 0x85, 0, 0, 0, 0, 0x34, 0x12])
    d[ram + 0x100:ram + 0x100 + len(lst)] = lst
    d[ram + 0x2A40:ram + 0x2A60] = pf_pal
    d[ram + 0x2A22:ram + 0x2A40] = bytes(range(30))
    d[0x24000 + 1] = 0x40                                       # (R#1: the display on)
    d[0x24000 + 2] = 0x1F
    d[0x24000 + 8] = 0x20
    d[0x24040:0x24060] = bytes(range(32))
    return d


class FilesTests(unittest.TestCase):
    def test_the_harness_is_complete(self):
        self.assertLessEqual(FILES, {p.name for p in BST.iterdir()})

    def test_every_python_tool_compiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            for p in sorted(BST.glob("*.py")):
                py_compile.compile(str(p), cfile=os.path.join(tmp, p.stem + ".pyc"), doraise=True)

    def test_every_python_tool_imports(self):
        for p in sorted(BST.glob("*.py")):
            m = importlib.import_module(p.stem)
            self.assertTrue(callable(getattr(m, "main", None)), p.name)

    def test_the_tools_it_calls_have_its_names(self):
        import msxbright
        import msxpuzl
        import msxtext
        import planar
        for mod, names in ((msxtext, ("glyph_sc5", "bonus_scripts", "fs_render", "msx_palette")),
                           (msxbright, ("grade_pal",)), (planar, ("write_png",)),
                           (msxpuzl, ("Puzl", "SAT_X", "SAT_Y", "ST_LEN", "STATE", "ST", "ST_RANGE", "NONE",
                                      "state_items"))):
            for n in names:
                self.assertTrue(hasattr(mod, n), f"{mod.__name__}.{n}")
        for f in ("tools/mkrom.py", "tools/puzlcmp.py", "tools/tracecmp.py", "tools/openmsx_rc2.tcl",
                  "tools/msxmatrix.py", "tools/checkrun.py"):
            self.assertTrue((ROOT / f).exists(), f)

    def test_no_absolute_path_of_this_machine(self):
        for p in sorted(BST.iterdir()):
            if p.is_file():
                text = p.read_text()
                for s in ("/private/tmp", "/Users/", "scratchpad"):
                    self.assertNotIn(s, text, p.name)

    def test_shell_scripts_parse(self):
        for p in sorted(BST.glob("*.sh")):
            r = run(["sh", "-n", p])
            self.assertEqual(r.returncode, 0, p.name + r.stderr)


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def roms(self, stray: bool) -> list[Path]:
        """Two 2-bank images and their labels: foo moved from 4010h to 4013h, its word at bank 1 + 100h."""
        a, b = bytearray(b"\xff" * 16384), bytearray(b"\xff" * 16384)
        a[8192 + 0x100:8192 + 0x102] = b"\x10\x40"
        b[8192 + 0x100:8192 + 0x102] = b"\x13\x40"
        if stray:
            b[8192 + 0x200] = 0
        files = [self.tmp / "a.rom", self.tmp / "b.rom", self.tmp / "a.labels", self.tmp / "b.labels"]
        files[0].write_bytes(a)
        files[1].write_bytes(b)
        files[2].write_text("foo:\tequ $4010\nbar:\tequ $4100\n")
        files[3].write_text("foo:\tequ $4013\nbar:\tequ $4100\n")
        return files

    def test_relocheck_passes_relocated_words_and_fails_others(self):
        r = run([sys.executable, "-I", BST / "relocheck.py", *self.roms(False), 0, 1])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("bank 1: 1 relocated label words", r.stdout)
        self.assertIn("relocheck: PASS", r.stdout)
        r = run([sys.executable, "-I", BST / "relocheck.py", *self.roms(True), 1])
        self.assertEqual(r.returncode, 1)
        self.assertIn("bank 1 offset 0200: FF -> 00 not a relocated label word", r.stdout)
        self.assertIn("relocheck: FAIL (1)", r.stdout)

    def test_romdiff_lists_the_banks(self):
        a, b = self.roms(True)[:2]
        r = run([sys.executable, "-I", BST / "romdiff.py", a, b])
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.splitlines(), ["sizes 16384 16384", "bank 1: 2 bytes differ, offsets 0100-0200"])

    def test_fixblank_counts_the_frames_without_the_hud(self):
        p = 0.0166833
        lines = ["# made up"] + [f"{k * p:.6f} S" for k in range(60)]
        t0 = 59 * p
        lines += [f"{t0 + 0.00425:.6f} C 00", f"{t0 + 0.0066:.6f} D", f"{t0 + 0.05:.6f} B"]
        lines += [f"{t0 + (7 + k) * p:.6f} S" for k in range(10)]
        f = self.tmp / "x_blank.txt"
        f.write_text("\n".join(lines) + "\n")
        r = run([sys.executable, "-I", BST / "fixblank.py", f])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("7.00 frame periods: 6 frame(s) without the HUD", r.stdout)

    def test_hudcheck_boxes(self):
        import hudcheck
        a = bytearray(45 * 128)
        b = bytearray(a)
        b[24 * 128 + 100] = 0x11
        b[25 * 128 + 101] = 0x11
        self.assertEqual(hudcheck.boxes(bytes(a), bytes(b)), [(200, 24, 207, 31)])

    def test_stepcheck_parsers(self):
        import stepcheck
        regs, gframe = stepcheck.parse_list(bytes([1, 6, 0x1F, 0x82, 0x0A, 0x88, 0xC7, 0x85, 0, 0, 0, 0, 0x34, 0x12])
                                            + bytes(18))
        self.assertEqual(regs, {2: 0x1F, 8: 0x0A, 5: 0xC7})
        self.assertEqual(gframe, 0x1234)
        sat = bytes([17, 32, 4, 0, 17, 32, 12, 0, 216, 0, 0, 0]) + bytes(20)
        self.assertEqual(stepcheck.sat_entries(sat), [(17, 32, 4), (17, 32, 12)])
        px = stepcheck.page_pixels(bytes([0x12]) + bytes(20735))
        self.assertEqual((px[0][0], px[0][1], px[0][2], len(px), len(px[0])), (1, 2, 0, 162, 256))
        self.assertEqual(stepcheck.REC_LEN, 64 + 20736 + 32 + 32 + 32 + 4 * 256)

    def test_shots_and_frozen_draw_a_snapshot(self):
        snap = self.tmp / "p0100.bin"
        snap.write_bytes(snapshot())
        r = run([sys.executable, "-I", BST / "shots.py", self.tmp / "png", snap])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(png_size(self.tmp / "png" / "p0100.png"), (512, 424))
        r = run([sys.executable, "-I", BST / "frozen.py", snap, self.tmp / "held.png"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(png_size(self.tmp / "held.png"), (512, 424))
        self.assertIn("page 0, R#23 0, R#1 40", r.stdout)

    def test_restorecheck_known_items(self):
        import restorecheck
        ga = bytearray(SNAP_LEN)
        gb = bytearray(ga)
        ga[0x1E000:0x1E010] = b"\x0f" * 16                          # (the cursor's colours)
        ga[0x1E278:0x1E280], gb[0x1E678:0x1E680] = b"\xc1\xfa\x20\x00\xc1\xfa\x24\x00", b"\xc1\xfa\x20\x00\xc1\xfa\x24\x00"
        ga[0x1E678:0x1E680], gb[0x1E278:0x1E280] = b"\xc5\xf5\x20\x00\xc5\xf5\x24\x00", b"\xc5\xf5\x20\x00\xc5\xf5\x24\x00"
        diff = [i for i in range(0x1D800, 0x1E800) if ga[i] != gb[i]]
        rest, what = restorecheck.known_items(bytes(ga), bytes(gb), diff)
        self.assertEqual(rest, [])
        self.assertIn("16 in the colour rows", what)
        gb[0x1E678] = 0xC6                                          # (no longer the same entries swapped)
        diff = [i for i in range(0x1D800, 0x1E800) if ga[i] != gb[i]]
        rest, _ = restorecheck.known_items(bytes(ga), bytes(gb), diff)
        self.assertIn(0x1E678, rest)
        ga[0x1D800] = 1                                             # (a pattern byte: never known)
        diff = [i for i in range(0x1D800, 0x1E800) if ga[i] != gb[i]]
        self.assertIn(0x1D800, restorecheck.known_items(bytes(ga), bytes(gb), diff)[0])

    @unittest.skipUnless(LEVEL1_VRAM.exists(), "needs build/msx/level1.vram (make msx)")
    def test_restorecheck_command_line(self):
        vram = LEVEL1_VRAM.read_bytes()
        res = bytearray(SNAP_LEN)
        res[0x10000:0x18000] = vram[0x10000:0x18000]
        res[0x1E200] = res[0x1E600] = 216
        (self.tmp / "a_result.bin").write_bytes(res)
        (self.tmp / "a_intro.bin").write_bytes(bytes(SNAP_LEN))
        ga, gb = bytearray(SNAP_LEN), bytearray(SNAP_LEN)
        ga[0x1E400:0x1E420] = b"\x0e" * 32
        (self.tmp / "a_g50.bin").write_bytes(ga)
        (self.tmp / "f_g50.bin").write_bytes(gb)
        r = run([sys.executable, "-I", BST / "restorecheck.py", self.tmp, "a", "f"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("SATs (1D800h-1E7FFh): FAIL (32 bytes differ)", r.stdout)
        r = run([sys.executable, "-I", BST / "restorecheck.py", self.tmp, "a", "f", "--known"])
        self.assertEqual(r.returncode, 0, r.stdout)
        ga[0x1E800] = 1
        (self.tmp / "a_g50.bin").write_bytes(ga)
        r = run([sys.executable, "-I", BST / "restorecheck.py", self.tmp, "a", "f", "--known"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("HUD (1E800h-1FE7Fh): FAIL (1 bytes differ)", r.stdout)

    @unittest.skipUnless(LEVEL1_RAM.exists() and all(p.exists() for p in TEXT_SC5),
                         "needs build/ram/level1_full.bin and build/msx/text_bs_*.sc5 (make msx)")
    def test_bonuscheck_command_line(self):
        import msxtext
        ram = LEVEL1_RAM.read_bytes()
        glyphs = [msxtext.glyph_sc5(ram, g) for g in range(44)]
        scripts = {label: script for label, _, script in msxtext.bonus_scripts(ram)}
        tag = bytes((0, 15, 10)) + b"TEST 2"
        (self.tmp / "t_intro.sc5").write_bytes(msxtext.fs_render(glyphs, tag + scripts["txt_bs_intro"]))
        (self.tmp / "t_result.sc5").write_bytes(msxtext.fs_render(glyphs, tag + scripts["txt_bs_time"]))
        for n in ("intro", "result"):
            (self.tmp / f"t_{n}_regs.bin").write_bytes(bytes([0x16, 0x62]) + bytes(62))
        (self.tmp / "t_bonus.txt").write_text(
            "intro at 9.4 s, fs_n 150, R#0 16 R#1 62, AG 8050h 1, 805Eh 0\n"
            "result time at 77.5 s, fs_n 80, R#0 16 R#1 62, AG 805Eh 0\n"
            "between the records: 4078 VBLANKs, 4078 HUD splits\n"
            "game tick_n 3240 at 80.1 s, g_frame 100, lives 2\n")
        cmd = [sys.executable, "-I", BST / "bonuscheck.py", self.tmp, "t", "--tag", "2", "--result", "time"]
        r = run(cmd)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("bonus check: PASS", r.stdout)
        r = run(cmd[:-1] + ["fail"])
        self.assertEqual(r.returncode, 1)
        d = bytearray((self.tmp / "t_result.sc5").read_bytes())
        d[128 * 100] ^= 0x11
        (self.tmp / "t_result.sc5").write_bytes(d)
        r = run(cmd)
        self.assertEqual(r.returncode, 1)
        self.assertIn("result (txt_bs_time, TEST 2): 1 bytes DIFFER, lines 100-100", r.stdout)


STUB_MKROM = r'''
import json
import sys
from pathlib import Path
here = Path(__file__).resolve().parents[1]
with (here / "calls.txt").open("a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
mode = (here / "mode.txt").read_text().strip()
out = Path(sys.argv[2])
labels = "".join("l%d:\tequ $%04x\n" % (i, i) for i in range(5))
labels += "rc2.asm:1: warning: expression fully enclosed in parenthesis\n" * 12
if mode == "extra":
    labels += "rc2.asm:2: warning: something else\n"
if mode != "norom":
    out.write_bytes(b"\xff" * 16)
out.with_suffix(".labels").write_text(labels)
print("stub: " + out.name)
'''


class ShellTests(unittest.TestCase):
    """build.sh, hz.sh and variants.sh against a stub mkrom (SRC=), never the real one."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.src = self.tmp / "src"
        (self.src / "tools").mkdir(parents=True)
        (self.src / "tools" / "mkrom.py").write_text(STUB_MKROM)
        self.mode("ok")
        self.env = dict(os.environ, SRC=str(self.src))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def mode(self, m: str) -> None:
        (self.src / "mode.txt").write_text(m)

    def calls(self) -> list[list[str]]:
        """The stub's argument lists, one a call."""
        f = self.src / "calls.txt"
        return [json.loads(line) for line in f.read_text().splitlines()] if f.exists() else []

    def test_build_checks(self):
        out = self.tmp / "o" / "x.rom"
        r = run(["sh", BST / "build.sh", out, "TAG=2"], env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("z80asm: 12 warnings (12 known), 0 other messages", r.stdout)
        self.assertIn("build OK: ", r.stdout)
        level, rom, *opts = self.calls()[-1]
        self.assertEqual(level, str(ROOT / "build" / "msx" / "level1"))
        self.assertEqual((Path(rom).name, opts), ("x.rom", ["TAG=2"]))
        r = run(["sh", BST / "build.sh", out], env=dict(self.env, KNOWN_WARNINGS="11"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL: 12 'fully enclosed' warnings (11 known)", r.stdout)
        self.mode("extra")
        r = run(["sh", BST / "build.sh", out], env=self.env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL: z80asm messages other than the known warnings", r.stdout)
        self.mode("norom")
        r = run(["sh", BST / "build.sh", out], env=self.env)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL: no new ROM", r.stdout)
        self.mode("ok")
        r = run(["sh", BST / "build.sh", self.tmp / "o" / "Y.ROM"], env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertTrue((self.tmp / "o" / "Y.labels").exists())

    def test_build_refuses_build_msx_and_creates_nothing_there(self):
        before = sorted(p.name for p in (ROOT / "build" / "msx").iterdir()) if (ROOT / "build" / "msx").exists() else None
        for out, cwd in ((ROOT / "build" / "msx" / "bstest_refused.rom", ROOT),
                         (ROOT / "build" / "msx" / "bstest_refused_dir" / "x.rom", ROOT),
                         (Path("build/msx/bstest_refused.rom"), ROOT), (Path("msx/bstest_refused.rom"), ROOT / "build")):
            if not cwd.exists():
                continue
            r = run(["sh", BST / "build.sh", out], env=self.env, cwd=cwd)
            self.assertEqual(r.returncode, 2, f"{out}: {r.stdout}{r.stderr}")
            self.assertIn("must not be in build/msx", r.stderr)
        self.assertEqual(self.calls(), [])
        after = sorted(p.name for p in (ROOT / "build" / "msx").iterdir()) if (ROOT / "build" / "msx").exists() else None
        self.assertEqual(before, after)
        r = run(["sh", BST / "build.sh", self.tmp / "x.bin"], env=self.env)
        self.assertEqual(r.returncode, 2)

    def test_hz_sh_builds_the_suite(self):
        r = run(["sh", BST / "hz.sh", "builds", self.tmp / "R"], env=self.env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("builds: PASS", r.stdout)
        for f in ("prod/rc2.rom", "pzt/rc2.rom", "pz1/rc2_pz1.rom", "pz2/rc2_pz2.rom", "trace/rc2_ext5.rom",
                  "ext/rc2_ext.rom"):
            self.assertTrue((self.tmp / "R" / f).exists(), f)
        opts = [c[2:] for c in self.calls()]
        self.assertEqual(opts, [[], ["PZ_TEST=1"], ["EXTJOY=1", "PZ_TEST=1"], ["EXTJOY=1", "PZ_TEST=1", "PZ_LEVEL=2"],
                                ["EXTJOY=1", "ENEMY_CAP=0", "DAMAGE_X=1"], ["EXTJOY=1"]])

    def test_hz_sh_usage_and_compare_without_labels(self):
        r = run(["sh", BST / "hz.sh"])
        self.assertEqual(r.returncode, 2)
        self.assertIn("hz.sh compare DIR [LABELS]", r.stderr)
        r = run(["sh", BST / "hz.sh", "compare", self.tmp])
        self.assertEqual(r.returncode, 2)
        self.assertIn("no label file", r.stderr)

    def test_hz_sh_fresh(self):
        names = ("title_vram.bin", "title_regs.bin", "title_pal.bin", "psg.txt", "game_vram.bin", "game_ram.bin")
        for tag in ("a", "b"):
            for n in names:
                (self.tmp / f"{tag}_{n}").write_bytes(bytes(64))
            (self.tmp / f"{tag}_music.txt").write_text(f"# {tag} time\n1 00\n2 00\n# end {tag}\n")
            (self.tmp / f"{tag}_game.txt").write_text("time 1 tick_n 300 g_frame 300\n")
        r = run(["sh", BST / "hz.sh", "fresh", self.tmp, "a", "b"])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("music.txt: identical (2 ticks)", r.stdout)
        self.assertIn("fresh: PASS", r.stdout)
        (self.tmp / "b_game_ram.bin").write_bytes(bytes(63) + b"\x01")
        r = run(["sh", BST / "hz.sh", "fresh", self.tmp, "a", "b"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("game_ram.bin: DIFFERENT (1 bytes)", r.stdout)

    def test_variants_build_every_option_set(self):
        r = run(["sh", BST / "variants.sh", self.tmp / "var"], env=self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(len(lines), 41)
        self.assertTrue(all(line.endswith(" OK") for line in lines), r.stdout)


# openMSX's Tcl commands, mocked: memory, breakpoints fired by hand (fire ADDR: its condition, then its
# command, at global level), 'after' on a virtual clock (run_until), keys and calls recorded
TCL_MOCK = r"""
array set ::mem {}
set ::now 0.0
set ::q {}
set ::seq 0
set ::bps {}
set ::wps {}
set ::nbp 0
set ::keys {}
set ::calls {}
set ::machine none
set ::romblock 0
set ::pause on
rename after tcl_after
proc after {kind args} {
	if {$kind eq "cancel"} {
		set i [lsearch -index 1 $::q [lindex $args 0]]
		if {$i >= 0} { set ::q [lreplace $::q $i $i] }
		return
	}
	lassign $args t script
	incr ::seq
	lappend ::q [list [expr {$::now + $t}] "after#$::seq" $::seq $script]
	return "after#$::seq"
}
proc run_until {cond {limit 20000}} {
	set n 0
	while {![uplevel #0 [list expr $cond]] && [llength $::q] && $n < $limit} {
		set ::q [lsort -real -index 0 [lsort -integer -index 2 $::q]]
		set e [lindex $::q 0]
		set ::q [lrange $::q 1 end]
		set ::now [lindex $e 0]
		uplevel #0 [lindex $e 3]
		incr n
	}
	return [uplevel #0 [list expr $cond]]
}
proc peek {a} { set a [expr {$a}]; if {[info exists ::mem($a)]} { return $::mem($a) }; return 0 }
proc poke {a v} { set ::mem([expr {$a}]) [expr {$v & 0xFF}] }
proc mset {a v} { poke $a $v; poke [expr {$a + 1}] [expr {$v >> 8}] }
proc reg {name} { return 0 }
proc machine {name} { if {$name eq "bad"} { error "no such machine" }; set ::machine $name; lappend ::calls "machine $name" }
proc machine_info {what} { if {$what eq "time"} { return $::now }; return $::machine }
proc carta {args} { lappend ::calls "carta $args" }
proc reset {} { lappend ::calls reset }
proc keymatrixdown {r m} { lappend ::keys [format "down %d %02X" $r $m] }
proc keymatrixup {r m} { lappend ::keys [format "up %d %02X" $r $m] }
proc debug {cmd args} {
	switch -- $cmd {
		read {
			lassign $args space addr
			if {$space eq "VDP regs"} { return [expr {($addr * 3) & 0xFF}] }
			if {[string match "* romblocks" $space]} { return $::romblock }
			return 0
		}
		read_block {
			lassign $args space addr len
			if {$space eq "memory"} {
				set s ""
				for {set i 0} {$i < $len} {incr i} { append s [binary format cu [peek [expr {$addr + $i}]]] }
				return $s
			}
			return [string repeat [binary format cu 0x5A] $len]
		}
		size {
			switch -- [lindex $args 0] { "VDP regs" { return 64 } "VDP palette" { return 32 } default { return 16 } }
		}
		list { return {memory {physical VRAM} {VDP regs} {VDP palette} {PSG regs}} }
		set_bp {
			lassign $args addr cond cmd
			incr ::nbp
			dict set ::bps "bp#$::nbp" [list [expr {$addr}] $cond $cmd]
			return "bp#$::nbp"
		}
		remove_bp { dict unset ::bps [lindex $args 0]; return }
		breakpoint {
			if {[lindex $args 0] eq "list"} { set l {}; dict for {id v} $::bps { lappend l $id {} }; return $l }
			dict unset ::bps [lindex $args 1]; return
		}
		condition { if {[lindex $args 0] eq "list"} { return {} }; return }
		set_watchpoint { incr ::nbp; dict set ::wps "wp#$::nbp" $args; return "wp#$::nbp" }
		watchpoint {
			if {[lindex $args 0] eq "list"} { set l {}; dict for {id v} $::wps { lappend l $id {} }; return $l }
			dict unset ::wps [lindex $args 1]; return
		}
		breaked { return 0 }
		cont { return }
	}
	error "debug $cmd: not mocked"
}
proc fire {addr} {
	dict for {id v} $::bps {
		lassign $v a cond cmd
		if {$a != $addr} continue
		if {$cond ne "" && ![uplevel #0 [list expr $cond]]} continue
		uplevel #0 $cmd
	}
}
"""

TCL_SCENARIO = r"""
set tmp [lindex $argv 0]
set lab [lindex $argv 2]
source [file join [lindex $argv 1] tools bstest load.tcl]
set base [llength [file channels]]
puts "root $::hz_root"
set missing {}
foreach p {hz_chain hz_clean hz_regress hz_fresh hz_fresh_setup hz_bonus hz_bonus_setup hz6_arm hz6_arm_setup
		hz6_prod hz6_prod_setup hz6_time hz6_time_setup hz7_snap hz7_arm hz7_job hz7_guard_arm hz7_after_setup
		hz7_fresh_setup hzp_setup hzb_setup hzg_job hzf_job hzf_done suite_drives suite_flows c8_job c8_arm
		c8_chain rc2_pz_drive rc2_label rc2_drive_rom rc2_guard} {
	if {[info procs $p] eq ""} { lappend missing $p }
}
puts "missing $missing"

# a chain: a job done at once; one that times out with five channels open; one whose setup fails
set ::x 0
set opener [list apply {{tmp} {
	foreach v {rd_out rpz_out h7_rf hzb_f hz_mf} { set ::$v [open [file join $tmp $v.txt] w] }
}} $tmp]
hz_chain [list {j1 MA {set ::x 1} {$::x} 5} [list j2 MB $opener {0} -1] {j3 MC {error boom} {1} 5} {j4 MD {} {1} 5}]
run_until {[string match "error*" $::hz_state]}
puts "chain1 $::hz_state"
puts "msgs1 [join $::hz_msgs |]"
puts "open1 [expr {[llength [file channels]] - $base}]"
puts "machines1 [join [lsearch -all -inline $::calls machine*] |]"
hz_chain {{k1 bad {} {1} 5}}
run_until {$::hz_state ne "running"}
puts "chain2 $::hz_state | [join $::hz_msgs |]"

# hz_fresh: the title, two music ticks, one PSG write, the music's end, the game at tick 10
hz_fresh [file join $tmp fr] ft [file join $tmp x.rom] $lab M2 10
mset 0xEC44 1; mset 0xC202 1
run_until {[info exists ::hf_st] && $::hf_st == 2}
set ::romblock 3
fire 0x4567; fire 0x4567
set ::wp_last_address 0xA1; set ::wp_last_value 7; hf_psg
mset 0xC2B2 1
run_until {$::hf_st == 3}
mset 0xEC44 0; mset 0xCEE0 10
run_until {$::hz_state eq "done"}
puts "fresh $::hz_state | [join $::hz_msgs |]"

# hz_bonus: the intro, 120 VBLANKs with their splits, OUT OF TIME., the title, fire, the new game
array unset ::mem
hz_bonus [file join $tmp b] bt [file join $tmp x.rom] $lab M2
mset 0xCFB8 0x9000; mset 0xCFBE 150
puts "bonus_intro [run_until {[info exists ::hb_st] && $::hb_st == 1}]"
for {set i 0} {$i < 120} {incr i} { fire 0x38; fire 0x39 }
mset 0xCFBE 10
puts "bonus_s6 [run_until {$::hb_st == 6}]"
mset 0xCFB8 0x9300; mset 0xCFBE 80
puts "bonus_s2 [run_until {$::hb_st == 2}]"
mset 0xEC44 1
puts "bonus_s4 [run_until {$::hb_st == 4}]"
puts "bonus_keys [run_until {[llength $::keys] >= 2}]"
mset 0xEC44 0; mset 0xCEE0 100
puts "bonus [run_until {$::hz_state eq "done"}] $::hz_state | [join $::hz_msgs |] | keys [join $::keys |]"

# hz7: a snapshot at pass 5 and a record of 3 pictures from pass 5; then a record cut by the drive's end
hz_clean
mset 0xA123 0x56CD; poke 0xA125 0xA4
set ::rc2_trace_done 0
hz7_arm [file join $tmp st] $lab {5} 3 5
mset 0xD000 4; fire 0xA123
mset 0xD000 5; fire 0xA123
foreach i {1 2 3 4} { fire 0x0123 }
puts "rec $::h7_recn $::h7_recdone [info exists ::h7_rf]"
hz_clean
hz7_arm [file join $tmp st2] $lab {} 10 0
fire 0xA123; fire 0x0123; fire 0x0123
puts "rec2 [hz7_done] [hz7_done] $::h7_recn [info exists ::h7_rf]"
set ::rc2_trace_done 1
puts "rec3 [hz7_done] $::h7_recn [info exists ::h7_rf]"
hz_clean

# the suite's job lists
set jd [suite_drives [file join $tmp R] [file join $tmp O]]
set jf [suite_flows [file join $tmp R] [file join $tmp O] [file join $tmp F] base]
puts "suite [llength $jd] [llength $jf] [lindex $jd 0 0] [lindex $jd 0 1] | [lindex $jf 3 0] | [lindex $jf end 0]"
puts "setup0 [lindex $jd 0 2]"

# c8: the keys of two moves, then the breakpoint gone
set ::keys {}
c8_arm $tmp c8t $lab {10 d 20 r}
foreach p {9 10 12 15 20 25 30 31} { mset 0xD000 $p; fire 0xA123 }
puts "c8keys [join $::keys |]"
hz_clean

# hzf_done: nothing until the drive's end, then its file
set ::hzf_file [file join $tmp fast.txt]
set ::rc2_trace_done 0
puts "hzf0 [hzf_done] [file exists $::hzf_file]"
set ::rc2_trace_done 1; set ::rc2_too_fast 0; set ::rc2_too_fast_pc {}; set ::too_fast_vram_access real
set ::rc2_pz_result 0; mset 0xD000 732
puts "hzf1 [hzf_done] [file exists $::hzf_file]"
puts "open [expr {[llength [file channels]] - $base}]"
"""

LABELS = {"pz_tick": 0xA123, "pz_frame": 0xA456, "pz_done": 0x7F10, "pz_boards": 0xF500, "ext_joy": 0xCE5A,
          "iv_late": 0x0123, "txt_bs_intro": 0x9000, "txt_bs_ok": 0x9100, "txt_bs_fail": 0x9200,
          "txt_bs_time": 0x9300, "isr_split": 0x0038, "isr_vblank": 0x0039, "INPUT_SCRIPT": 0, "BANK_MUSIC": 3,
          "mus_adv": 0x4567, "tick_start": 0x4100, "game_tick": 0x4200}


@unittest.skipUnless(shutil.which("tclsh"), "needs tclsh")
class TclTests(unittest.TestCase):
    def test_files_are_complete_without_exit_vwait_max_min(self):
        for p in sorted(BST.glob("*.tcl")):
            r = run(["tclsh"], input=f"set f [open {{{p}}}]; set s [read $f]; close $f; puts [info complete $s]\n")
            self.assertEqual(r.stdout.strip(), "1", p.name + r.stderr)
            code = "\n".join(line for line in p.read_text().splitlines() if not line.lstrip().startswith("#"))
            for bad in (r"\bexit\b", r"\bvwait\b", r"\bmax\s*\(", r"\bmin\s*\("):
                self.assertIsNone(re.search(bad, code), f"{p.name}: {bad}")

    def test_mocked_session(self):
        import stepcheck
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "t.labels").write_text("".join(f"{k}:\tequ ${v:04x}\n" for k, v in LABELS.items()))
            (t / "s.tcl").write_text(TCL_MOCK + TCL_SCENARIO)
            r = run(["tclsh", t / "s.tcl", t, ROOT, t / "t.labels"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = dict(line.split(" ", 1) if " " in line else (line, "") for line in r.stdout.splitlines())
            self.assertEqual(Path(out["root"]).resolve(), ROOT)
            self.assertEqual(out["missing"], "")
            # the chain
            self.assertEqual(out["chain1"], "error: j3")
            msgs = out["msgs1"].split("|")
            self.assertTrue(msgs[0].startswith("j1 (MA): done in "), msgs)
            self.assertTrue(msgs[1].startswith("j2 (MB): TIMEOUT after "), msgs)
            self.assertEqual(msgs[2], "j3: setup failed: boom")
            self.assertEqual(out["open1"], "0")                     # (hz_clean closed the five)
            self.assertEqual(out["machines1"], "machine MA|machine MB|machine MC")
            self.assertEqual(out["chain2"], "error: k1 | k1: machine bad failed: no such machine")
            # hz_fresh's records, as hz.sh fresh reads them
            self.assertTrue(out["fresh"].startswith("done | fresh ft (M2): done in "), out["fresh"])
            fr = t / "fr"
            for n, size in (("title_vram.bin", 0x20000), ("title_regs.bin", 64), ("title_pal.bin", 32),
                            ("game_vram.bin", 0x20000), ("game_ram.bin", 0x1000)):
                self.assertEqual((fr / f"ft_{n}").stat().st_size, size, n)
            music = (fr / "ft_music.txt").read_text().splitlines()
            self.assertEqual([m for m in music if not m.startswith("#")], ["0 " + "5a" * 16] * 2)
            self.assertIn("music end; PSG writes 1 hash 264", music[-1])
            self.assertEqual((fr / "ft_psg.txt").read_text(), "1 264\n")
            self.assertIn("tick_n 10 g_frame 0", (fr / "ft_game.txt").read_text())
            r2 = run(["sh", BST / "hz.sh", "fresh", fr, "ft", "ft"])
            self.assertIn("fresh: PASS", r2.stdout)
            # hz_bonus's records, as bonuscheck.py reads them
            for k in ("bonus_intro", "bonus_s6", "bonus_s2", "bonus_s4", "bonus_keys"):
                self.assertEqual(out[k], "1", k)
            self.assertIn("bonus bt (M2): done in ", out["bonus"])
            self.assertTrue(out["bonus"].endswith("keys down 8 01|up 8 01"), out["bonus"])
            b = t / "b"
            for n, size in (("intro.sc5", 20736), ("intro_regs.bin", 64), ("intro_pal.bin", 32),
                            ("intro_hud.bin", 45 * 128), ("intro_ram.bin", 0x4000), ("result.sc5", 20736),
                            ("result_regs.bin", 64), ("game_vram.bin", 0x20000)):
                self.assertEqual((b / f"bt_{n}").stat().st_size, size, n)
            notes = (b / "bt_bonus.txt").read_text()
            self.assertEqual(re.search(r"^result (\w+) ", notes, re.M)[1], "time")
            self.assertEqual(re.search(r"(\d+) VBLANKs, (\d+) HUD splits", notes).groups(), ("120", "120"))
            self.assertTrue(re.search(r"^game tick_n 100 ", notes, re.M), notes)
            self.assertTrue(re.search(r"^title at .*\nfire at ", notes, re.M), notes)
            # hz7's snapshot and record, as stepcheck.py and shots.py read them
            self.assertEqual(out["rec"], "3 1 0")
            snap = (t / "st" / "p0005.bin").read_bytes()
            self.assertEqual(len(snap), SNAP_LEN)
            self.assertEqual(snap[0x24000:0x24040], bytes((3 * i) & 0xFF for i in range(64)))
            self.assertEqual(snap[0x20000 + 0x1000:0x20000 + 0x1002], bytes((5, 0)))    # (RAM D000h: the pass)
            self.assertFalse((t / "st" / "p0004.bin").exists())
            self.assertEqual((t / "st" / "rec.bin").stat().st_size, 3 * stepcheck.REC_LEN)
            self.assertEqual(out["rec2"], "0 0 2 1")
            self.assertEqual(out["rec3"], "1 2 0")
            self.assertEqual((t / "st2" / "rec.bin").stat().st_size, 2 * stepcheck.REC_LEN)
            # the suite's job lists
            self.assertEqual(out["suite"], "25 13 solve1_m2 C-BIOS_MSX2 | fresh base | blank_tr")
            self.assertIn(str(t / "R" / "pz1" / "rc2_pz1.rom"), out["setup0"])
            self.assertIn(out["root"] + "/build/emu/pz_solve1.drive", out["setup0"])
            # c8's keys: down at the move's pass, up 5 passes later
            self.assertEqual(out["c8keys"], "down 8 40|up 8 40|down 8 80|up 8 80")
            notes = (t / "c8t_c8.txt").read_text().splitlines()
            self.assertEqual([n.split(":")[0] for n in notes[1:]],
                             ["pass 10", "pass 15", "pass 20", "pass 25", "pass 30"])
            # hzf_done
            self.assertEqual(out["hzf0"], "0 0")
            self.assertEqual(out["hzf1"], "1 1")
            self.assertEqual((t / "fast.txt").read_text(),
                             "too fast VRAM accesses: 0 at  (setting real); result 0, passes 732\n")
            self.assertEqual(out["open"], "0")


if __name__ == "__main__":
    unittest.main()
