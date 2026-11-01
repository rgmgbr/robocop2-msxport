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
- The final checks (docs/HARNESS.md 5.17): titlecmp.py, titlecmp2.py (its verdicts and what
  --unheard passes) and partialcheck.py on made-up records; in tclsh with openMSX mocked, np.tcl's
  keyboard drive, shifted drive and flows (the solved ending, both exact title records as
  titlecmp.py and titlecmp2.py read them, the text screens ended by fire, two stages, the turbo R
  watch), ft.tcl's four jobs and their files, run8f.tcl's job list, no channel left open.

The bonuscheck and partialcheck cases need build/ram/level1_full.bin (and build/msx/text_bs_*.sc5:
make msx), the restorecheck one build/msx/level1.vram; the Tcl cases need tclsh. Each is skipped
without them."""
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
         "hudcheck.py", "shots.py", "relocheck.py", "romdiff.py", "fixblank.py", "frozen.py",
         "np.tcl", "ft.tcl", "run8f.tcl", "titlecmp.py", "titlecmp2.py", "partialcheck.py",
         "rgview.tcl", "rgview.py", "rgview.sh", "rgflow.tcl", "frsound.tcl", "regress.tcl", "regress.sh",
         "rgcheck.py", "cmpcheck.py"}
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
        for mod, names in ((msxtext, ("glyph_sc5", "bonus_scripts", "fs_render", "fs_run", "msx_palette")),
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

    def test_first_picture_hud_record(self):
        """bonuscheck.py first_picture (--level2, contcheck.py --fire/--again): the notes' record of
        what the HUD shows against the game's values; a picture not recorded fails."""
        import contextlib
        import io
        import bonuscheck
        self.assertEqual(bonuscheck.hud_cells(0x0730, 0x0123, 0x00019725),
                         [0, 7, 3, 0, 1, 2, 3, 0, 0, 1, 9, 7, 2, 5])
        line = ("level 2's first picture at 1.5 s: game frame 0, tick_n 9, RoboCop 352 784, camera 352 784, "
                "timer 0729, score 00019725, lives {lives}, 805Eh 1, weapon 0, ammo 0000, ac_diff - diff_tab 0, "
                "HUD shown {shown} heads {heads} icon 3 can 0100 jobs 0/0\n")
        cases = (("2", "0007030000000000000109070205", "0 0", "holds the game's values"),      # (07:30)
                 ("2", "0007020900000000000109070205", "0 0", "holds the game's values"),
                 ("1", "0007020900000000000109070205", "0 0", "heads 0 0 with 1 lives (0 5 expected)"),
                 ("2", "0007020000000000000109070205", "0 0", "timer cells [0, 7, 2, 0]"),
                 ("2", "0007020900000000000109070204", "0 0", "ammo and score cells"),
                 ("65535", "0007030000000000000000000000", "5 5", "ammo and score cells"))
        for lives, shown, heads, want in cases:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                r = bonuscheck.first_picture(self.tmp, "t", line.format(lives=lives, shown=shown, heads=heads))
            self.assertEqual(r, 1)                          # (no TAG_l2g0 here: not recorded)
            self.assertIn(want, out.getvalue())
            self.assertIn("level 2's first picture not recorded", out.getvalue())

    def test_fieldcheck_counts_a_hostage_torn_per_object(self):
        import fieldcheck
        old_ft = fieldcheck.FT
        fieldcheck.FT = {0: {"sw": 48, "sh": 28}, 2: {"sw": 48, "sh": 28}}
        try:
            a_old, a_new, b_old = (0, 17, 424), (2, 17, 424), (0, 129, 504)
            # (hostage A a picture ahead, hostage B as shown: each whole, no tear)
            ahead = [("new", {a_old, a_new})] * 5 + [("old", {b_old})] * 7
            self.assertEqual(fieldcheck.tear_objects(ahead), 0)
            # (hostage A half old, half new: torn, the fewer kind counted)
            torn = [("new", {a_new})] * 5 + [("old", {a_old})] * 3 + [("old", {b_old})] * 7
            self.assertEqual(fieldcheck.tear_objects(torn), 3)
        finally:
            fieldcheck.FT = old_ft

    def test_vatcheck_flags_a_vat_column_the_beam_drew(self):
        import contextlib
        import io
        import vatcheck
        d = self.tmp
        ok = ("C 1.000000 200 260 60 0 3 0 8 0 0 64\np 0 64 16 144\n"   # (ended in the blank)
              "C 1.500000 210 30 60 1 3 0 8 0 0 64\n")                 # (34 lines before its first)
        (d / "vat_m2.txt").write_text(ok)
        (d / "guard_m2.txt").write_text("guard: reg 0, pal 0, cmd 1, cpu 0, vbl 0, tear 0\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vatcheck.main(["vatcheck.py", str(d)]), 0)
        (d / "vat_m2.txt").write_text(ok + "C 2.000000 220 100 60 2 3 0 8 0 0 64\n")   # (the beam at 100)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vatcheck.main(["vatcheck.py", str(d)]), 1)
        (d / "vat_m2.txt").write_text(ok)
        (d / "guard_m2.txt").write_text("guard: tear 1\n  tear beam lines 70-80 of command 36 0 64 16 144\n")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(vatcheck.main(["vatcheck.py", str(d)]), 1)

    def test_cutview_takes_the_copper_rule_and_flags_a_view_that_jumps_or_hides_the_suspect(self):
        import contextlib
        import io
        import cutview
        row = {"player_x": 936, "camera_x": 672, "camera_y": 521}
        self.assertEqual(cutview.copper_line(row), 0xAA)                       # vat 0, d = 33
        self.assertEqual(cutview.copper_line(dict(row, camera_y=565)), 0xCA)   # d = 4Dh: no cut
        self.assertEqual(cutview.copper_line(dict(row, player_x=1100)), 0xCA)  # beside the vat
        saved = cutview.suspect_columns
        cutview.suspect_columns = lambda: {9: (9, 44), 10: (1, 44)}
        try:
            def record(path: Path, step: int = 2, jump: int = 0, hide: int = 0) -> None:
                lines, add = [], 0
                for g in range(20, 60):
                    vx = add + (4 if g == jump else 0)
                    lines.append(f"T {g} {vx} 500 {add} 260 0 470")
                    lines.append(f"L {g} {30 if g == hide else vx} 500 128 100 50 1 10 241 56")
                    add = min(48, add + step)
                path.write_text("\n".join(lines) + "\n")
            f = self.tmp / "view_end_fx.txt"
            for kw, want in (({}, 0), ({"jump": 30}, 1), ({"step": 3}, 1), ({"hide": 55}, 1)):
                record(f, **kw)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(cutview.main(["cutview.py", "view", str(self.tmp)]), want, kw)
        finally:
            cutview.suspect_columns = saved

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

    def shifted(self) -> list[Path]:
        """Two images: a code bank 1 whose `ld a,D_BANK` and `ld a,D_BANK + 1` (3Eh nn) name the data block
        D, moved from bank 4 to bank 6 because the block X before it grew from 2 banks to 4; their banks.inc
        (in gen/ next to each) and labels."""
        a, b = bytearray(b"\xff" * 8192 * 5), bytearray(b"\xff" * 8192 * 7)
        a[8192:8192 + 4] = b"\x3e\x04\x3e\x05"
        b[8192:8192 + 4] = b"\x3e\x06\x3e\x07"
        a[2 * 8192:4 * 8192] = b"\x22" * 2 * 8192                  # X: 2 banks, then 4 (allowed to differ)
        b[2 * 8192:6 * 8192] = b"\x22" * 4 * 8192
        a[4 * 8192:5 * 8192] = b"\x11" * 8192                      # D: the same bytes at its new bank
        b[6 * 8192:7 * 8192] = b"\x11" * 8192
        d = {}
        for n, rom, dd in (("a", a, 4), ("b", b, 6)):
            (self.tmp / n / "gen").mkdir(parents=True)
            (self.tmp / n / f"{n}.rom").write_bytes(rom)
            (self.tmp / n / "gen" / "banks.inc").write_text(f"BANK_CODE: equ 1\nX_BANK: equ 2\nD_BANK: equ {dd}\n")
            (self.tmp / n / f"{n}.labels").write_text(f"D_BANK:\tequ ${dd:04x}\nfoo:\tequ $4010\n")
            d[n] = self.tmp / n
        return [d["a"] / "a.rom", d["b"] / "b.rom", d["a"] / "a.labels", d["b"] / "b.labels"]

    def test_romdiff_compares_the_blocks_at_their_banks(self):
        a, b = self.shifted()[:2]
        r = run([sys.executable, "-I", BST / "romdiff.py", "--blocks", a, b, "--allow", "X_BANK"])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("D_BANK: banks 4-4 -> 6-6: identical", r.stdout)
        self.assertIn("X_BANK: banks 2-3 -> 2-5: 2 -> 4 banks (identical over the first 2)", r.stdout)
        self.assertIn("BANK_CODE: banks 1-1 -> 1-1: 2 bytes differ, offsets 00001-00003 (code: relocheck.py)", r.stdout)
        self.assertIn("romdiff: PASS", r.stdout)
        r = run([sys.executable, "-I", BST / "romdiff.py", "--blocks", a, b])
        self.assertEqual(r.returncode, 1)
        self.assertIn("romdiff: FAIL (X_BANK)", r.stdout)

    def test_relocheck_takes_a_moved_banks_byte_operands_and_bank_pairs(self):
        files = self.shifted()
        r = run([sys.executable, "-I", BST / "relocheck.py", *files, "1"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("bank 1: 0 relocated label words, one-byte operands D_BANK x1, D_BANK + 1 x1", r.stdout)
        r = run([sys.executable, "-I", BST / "relocheck.py", *files, "D_BANK", "1:1"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("bank D_BANK (4 -> 6): 0 relocated label words", r.stdout)
        b = bytearray(files[1].read_bytes())
        b[8192 + 3] = 8                                          # (moved by 3: no name did)
        files[1].write_bytes(b)
        r = run([sys.executable, "-I", BST / "relocheck.py", *files, "1"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("bank 1 offset 0003: 05 -> 08 not a relocated label word or a changed name's byte", r.stdout)

    def test_l2base_fresh_takes_the_same_sprites_in_another_sat_order(self):
        sys.path.insert(0, str(BST))
        import l2base
        v = bytearray(0x20000)
        for c in l2base.SPRITE_SETS:
            for i in range(4):                                      # 4 entries, then y = 216
                v[c + 0x200 + 4 * i:c + 0x200 + 4 * i + 4] = bytes([85, 140, 0xE0 + 4 * i, 0])
                v[c + 16 * i:c + 16 * i + 16] = bytes([i + 1]) * 16
            v[c + 0x200 + 16] = 216
        w = bytearray(v)
        c = l2base.SPRITE_SETS[0]
        w[c + 0x208:c + 0x210], w[c + 0x200:c + 0x208] = v[c + 0x200:c + 0x208], v[c + 0x208:c + 0x210]
        w[c + 32:c + 64], w[c:c + 32] = v[c:c + 32], v[c + 32:c + 64]
        self.assertIn("the same sprites in another SAT order", l2base.sat_order(bytes(v), bytes(w)))
        x = bytearray(w)
        x[c + 5] = 9                                                 # (a colour row's byte)
        self.assertIsNone(l2base.sat_order(bytes(v), bytes(x)))
        x = bytearray(w)
        x[0x10000] = 1                                               # (outside the sprite sets)
        self.assertIsNone(l2base.sat_order(bytes(v), bytes(x)))
        self.assertIsNone(l2base.sat_order(bytes(v), bytes(v)))

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

    @unittest.skipUnless((ROOT / "build/extracted/files/PUZL_25.bin").exists(), "needs PUZL_25.bin (make extract)")
    def test_stepcheck_visit_2(self):
        import msxpuzl
        import stepcheck
        p1, p2 = stepcheck.puzl(), stepcheck.puzl(2)
        self.assertEqual((p1.visits, p2.visits), ((1,), (1, 2)))
        tv1 = stepcheck.elements(p1)[0][0][3]           # element 0, the TV: its images by picture
        tv2 = stepcheck.elements(p2, 2)[0][0][3]
        self.assertEqual([list(r) for r in tv2[8]], msxpuzl.unpack(p2.tv2[8 * 3200:9 * 3200], 80))
        self.assertNotEqual(tv1[8], tv2[8])                             # Ellen's face, not Murphy's
        self.assertEqual(tv1, stepcheck.elements(p2, 1)[0][0][3])       # visit 1's as before

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

    def test_bonuscheck_range_command_line(self):
        """--range: the shooting range's screens recorded in the same flow (rgflow.tcl rgh_arm), checked
        by rgcheck.py: OUT OF TIME. and a result for given counts, the notes, SHARP at the new game."""
        import msxtext
        ram = LEVEL1_RAM.read_bytes()
        glyphs = [msxtext.glyph_sc5(ram, g) for g in range(44)]
        bs = {label: script for label, _, script in msxtext.bonus_scripts(ram)}
        rg = {label: script for label, _, script in msxtext.range_scripts(ram)}
        (self.tmp / "t_intro.sc5").write_bytes(msxtext.fs_render(glyphs, bs["txt_bs_intro"]))
        (self.tmp / "t_result.sc5").write_bytes(msxtext.fs_render(glyphs, bs["txt_bs_time"]))
        (self.tmp / "t_rgintro.sc5").write_bytes(msxtext.fs_render(glyphs, rg["txt_rg_intro"]))
        (self.tmp / "t_rgres.sc5").write_bytes(msxtext.fs_render(glyphs, bs["txt_bs_time"]))
        for n in ("intro", "result", "rgintro", "rgres"):
            (self.tmp / f"t_{n}_regs.bin").write_bytes(bytes([0x16, 0x62]) + bytes(62))
        (self.tmp / "t_bonus.txt").write_text(
            "intro at 9.4 s, fs_n 150, R#0 16 R#1 62, AG 8050h 1, 805Eh 0\n"
            "result time at 77.5 s, fs_n 80, R#0 16 R#1 62, AG 805Eh 0\n"
            "between the records: 4078 VBLANKs, 4078 HUD splits\n"
            "game tick_n 9790 at 298.5 s, g_frame 101, lives 2\n")
        notes = ("# t: prod/rc2.labels on C-BIOS_MSX2; drive none\n"
                 "intro at 88.8 s, fs_n 151, R#0 16 R#1 62, AG 8050h 1, tick_n 699\n"
                 "stage: result 0 0 255 (dummy correct 804Ch at fr_done), rating 24 at fr_rated (213.1 s, passes 6050)\n"
                 "result time at 215.2 s, fs_n 101, R#0 16 R#1 62, ac_diff - diff_tab 24\n"
                 "between the records: 7629 VBLANKs, 7629 HUD splits; display_on calls 0\n"
                 "game tick_n 9790 at 298.5 s, g_frame 101, lives 2, ac_diff - diff_tab 0; lost: mp 0 atr 0 rd 0 fb 0\n")
        (self.tmp / "t_rg.txt").write_text(notes)
        cmd = [sys.executable, "-I", BST / "bonuscheck.py", self.tmp, "t", "--result", "time", "--range", "time"]
        r = run(cmd)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("the range: PASS", r.stdout)
        # (a flow without the range's records, the counts of a result, a lost write, not SHARP again)
        r = run(cmd[:-1] + ["25,0,1"])
        self.assertEqual(r.returncode, 1)
        (self.tmp / "t_rg.txt").write_text(notes.replace("mp 0 atr", "mp 1 atr"))
        r = run(cmd)
        self.assertEqual(r.returncode, 1)
        self.assertIn("lost counters not 0", r.stdout)
        (self.tmp / "t_rg.txt").write_text(notes.replace("lives 2, ac_diff - diff_tab 0", "lives 2, ac_diff - diff_tab 24"))
        r = run(cmd)
        self.assertEqual(r.returncode, 1)
        self.assertIn("the new game does not run with SHARP", r.stdout)
        (self.tmp / "t_rg.txt").write_text(notes)
        d = bytearray((self.tmp / "t_rgres.sc5").read_bytes())
        d[128 * 60] ^= 0x11
        (self.tmp / "t_rgres.sc5").write_bytes(d)
        r = run(cmd)
        self.assertEqual(r.returncode, 1)
        self.assertIn("rgres (OUT OF TIME.): 1 bytes DIFFER, lines 60-60", r.stdout)
        (self.tmp / "t_rgres.sc5").unlink()
        r = run(cmd)
        self.assertEqual(r.returncode, 1)
        self.assertIn("no record t_rgres.sc5", r.stdout)


def title_files(d: Path, tag: str, vram: bytes, regs: bytes = bytes(64), pal: bytes = bytes(32)) -> None:
    """The title part of a title record (hz_fresh's or np.tcl's)."""
    (d / f"{tag}_title_vram.bin").write_bytes(vram)
    (d / f"{tag}_title_regs.bin").write_bytes(regs)
    (d / f"{tag}_title_pal.bin").write_bytes(pal)


def scc_regs(enable: int = 0x07, vols: tuple = (15, 15, 15, 0, 0), freqs: tuple = (0x100, 0x200, 0x300, 0, 0)) -> bytearray:
    """The SCC debuggable's 256 bytes: frequencies A0h-A9h, volumes AAh-AEh, enable AFh, mirrored at
    B0h-BFh."""
    s = bytearray(256)
    for c, f in enumerate(freqs):
        s[0xA0 + 2 * c], s[0xA1 + 2 * c] = f & 0xFF, f >> 8
    s[0xAA:0xAF] = bytes(vols)
    s[0xAF] = enable
    s[0xB0:0xC0] = s[0xA0:0xB0]
    return s


def psg_regs(mixer: int = 0xBF, vols: tuple = (0, 0, 0)) -> bytearray:
    """The PSG's 16 registers: tone periods 1, 2, 3, noise 5, the mixer R7, volumes R8-R10."""
    r = bytearray(16)
    r[0], r[2], r[4], r[6], r[7] = 1, 2, 3, 5, mixer
    r[8:11] = bytes(vols)
    return r


class FinalToolTests(unittest.TestCase):
    """The final checks' Python tools (docs/HARNESS.md 5.17) on made-up records."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def music2(self, tag: str, rows: list) -> None:
        """An exact music log (np_hf_tick: tick, the SCC's registers, the PSG's, writes count:hash)."""
        lines = ["# 1.0 title shown; SCC debuggable 'x.rom SCC SCC'"]
        lines += [f"{t} {bytes(s).hex()} {bytes(p).hex()} {w}" for t, s, p, w in rows]
        (self.tmp / f"{tag}_music2.txt").write_text("\n".join(lines + ["# 9.0 music end"]) + "\n")

    def game2(self, tag: str, ram: bytes = bytes(0x1000), vram: bytes = bytes(0x20000), tick: int = 817) -> None:
        (self.tmp / f"{tag}_game2_ram.bin").write_bytes(ram)
        (self.tmp / f"{tag}_game2_vram.bin").write_bytes(vram)
        (self.tmp / f"{tag}_game2.txt").write_text(f"time 1.0 tick_n {tick} (the title's game tick 300) g_frame 300\n")

    def titlecmp2(self, *extra: str) -> subprocess.CompletedProcess:
        return run([sys.executable, "-I", BST / "titlecmp2.py", self.tmp, "a", "b", *extra])

    def pair(self, b_scc=None, b_psg=None, b_writes=None, a_scc=None, a_psg=None, ticks=(10, 11, 12, 13)) -> None:
        """Two exact records alike (A's registers: a_scc, a_psg) but for B's registers or writes at the
        middle ticks 11 and 12 (10 and 13 are the window's edges)."""
        s = scc_regs() if a_scc is None else a_scc
        p = psg_regs() if a_psg is None else a_psg
        rows_a = [(t, s, p, "2:5") for t in ticks]
        rows_b = [(t, b_scc if b_scc is not None and t in (11, 12) else s, b_psg if b_psg is not None and t in (11, 12) else p,
                   b_writes if b_writes is not None and t == 12 else "2:5") for t in ticks]
        self.music2("a", rows_a)
        self.music2("b", rows_b)
        self.game2("a")
        self.game2("b", tick=3940)

    def test_titlecmp2_identical_records_pass(self):
        self.pair()
        r = self.titlecmp2()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("music: ticks 10-13 / 10-13; 2 common ticks compared (4 PSG writes in them): differ "
                      "{'SCC': 0, 'PSG regs': 0, 'PSG writes': 0}", r.stdout)
        self.assertIn("game at tick 300, RAM D000h-DFFFh: identical", r.stdout)
        self.assertIn("game at tick 300, VRAM: 0 bytes differ, 0 in the HUD (1E800h-1FE7Fh); by 2 KiB block: identical",
                      r.stdout)
        self.assertTrue(r.stdout.rstrip().endswith("titlecmp2: PASS (the music identical at every compared tick)"))

    def test_titlecmp2_window_edges_are_left_out(self):
        s = scc_regs(freqs=(0x155, 0x200, 0x300, 0, 0))
        self.music2("a", [(t, scc_regs(), psg_regs(), "2:5") for t in (10, 11, 12, 13)])
        self.music2("b", [(t, s if t in (10, 13) else scc_regs(), psg_regs(), "1:9" if t == 13 else "2:5")
                          for t in (10, 11, 12, 13)])
        self.game2("a")
        self.game2("b")
        self.assertEqual(self.titlecmp2().returncode, 0)

    def test_titlecmp2_a_silent_scc_channel_passes_only_with_unheard(self):
        self.pair(b_scc=scc_regs(freqs=(0x100, 0x200, 0x300, 0x1D5, 0)))      # (channel 3: enable bit clear)
        r = self.titlecmp2()
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("differ {'SCC': 2, 'PSG regs': 0, 'PSG writes': 0}", r.stdout)
        for name in ("SCC A6h freq3", "SCC A7h freq3", "SCC B6h freq3 (mirror)", "SCC B7h freq3 (mirror)"):
            self.assertIn(f"  {name}: differs at 2 ticks from tick 11, heard at 0", r.stdout)
        self.assertIn("titlecmp2: FAIL (only registers neither run can hear differ: --unheard passes them)", r.stdout)
        r = self.titlecmp2("--unheard")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("titlecmp2: PASS (only registers neither run can hear differ; the PSG writes identical)", r.stdout)
        # enabled, but at volume 0 in both: silent too; at a volume in one run: heard
        self.pair(a_scc=scc_regs(enable=0x0F), b_scc=scc_regs(enable=0x0F, freqs=(0x100, 0x200, 0x300, 0x1D5, 0)))
        self.assertEqual(self.titlecmp2("--unheard").returncode, 0)
        self.pair(a_scc=scc_regs(enable=0x0F, vols=(15, 15, 15, 8, 0)),
                  b_scc=scc_regs(enable=0x0F, vols=(15, 15, 15, 8, 0), freqs=(0x100, 0x200, 0x300, 0x1D5, 0)))
        r = self.titlecmp2("--unheard")
        self.assertEqual(r.returncode, 1)
        self.assertIn("  SCC A6h freq3: differs at 2 ticks from tick 11, heard at 2", r.stdout)
        self.pair(b_scc=scc_regs(freqs=(0x101, 0x200, 0x300, 0, 0)))
        r = self.titlecmp2("--unheard")
        self.assertEqual(r.returncode, 1)
        self.assertIn("  SCC A0h freq0: differs at 2 ticks from tick 11, heard at 2", r.stdout)
        self.assertTrue(r.stdout.rstrip().endswith("titlecmp2: FAIL"))
        b = scc_regs()
        b[0xAF] = 0x0F                                                        # (the enable bits: always heard)
        self.pair(b_scc=b)
        self.assertEqual(self.titlecmp2("--unheard").returncode, 1)

    def test_titlecmp2_psg_registers(self):
        p = psg_regs()
        p[6] = 9                                                              # (the noise period, all noise off)
        self.pair(b_psg=p)
        r = self.titlecmp2()
        self.assertEqual(r.returncode, 1)
        self.assertIn("  PSG R6: differs at 2 ticks from tick 11, heard at 0", r.stdout)
        self.assertEqual(self.titlecmp2("--unheard").returncode, 0)
        q = psg_regs(mixer=0x9B, vols=(0, 0, 10))                             # (channel C mixes the noise in, audible)
        p = bytearray(q)
        p[6] = 9
        self.pair(a_psg=q, b_psg=p)
        r = self.titlecmp2("--unheard")
        self.assertEqual(r.returncode, 1)
        self.assertIn("  PSG R6: differs at 2 ticks from tick 11, heard at 2", r.stdout)
        q[10] = p[10] = 0                                                     # (its volume 0 in both: silent)
        self.pair(a_psg=q, b_psg=p)
        self.assertEqual(self.titlecmp2("--unheard").returncode, 0)
        q = psg_regs(vols=(0, 0, 0x10))                                       # (an envelope in use: R11-R13 heard)
        p = bytearray(q)
        p[11] = 7
        self.pair(a_psg=q, b_psg=p)
        self.assertEqual(self.titlecmp2("--unheard").returncode, 1)
        p = psg_regs()
        p[0], p[14] = 9, 0x3F                                                 # (a tone off in the mixer; an I/O port)
        self.pair(b_psg=p)
        self.assertEqual(self.titlecmp2("--unheard").returncode, 0)
        p = psg_regs()
        p[7] = 0xBE                                                           # (the mixer itself: always heard)
        self.pair(b_psg=p)
        self.assertEqual(self.titlecmp2("--unheard").returncode, 1)

    def test_titlecmp2_psg_writes_always_count(self):
        self.pair(b_writes="2:6")
        for extra in ((), ("--unheard",)):
            r = self.titlecmp2(*extra)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("'PSG writes': 1}", r.stdout)

    def test_titlecmp2_reports_the_game_and_missing_files(self):
        self.pair()
        ram, vram = bytearray(0x1000), bytearray(0x20000)
        ram[0x32] = 0x24
        vram[0x100] = vram[0x1E800] = 1
        self.game2("b", bytes(ram), bytes(vram))
        r = self.titlecmp2()
        self.assertEqual(r.returncode, 0, r.stdout)                           # (the game: reported only)
        self.assertIn("game at tick 300, RAM D000h-DFFFh: ['D032 00/24']", r.stdout)
        self.assertIn("game at tick 300, VRAM: 2 bytes differ, 1 in the HUD (1E800h-1FE7Fh); by 2 KiB block: "
                      "['00000h:1', '1E800h:1']", r.stdout)
        (self.tmp / "b_game2.txt").unlink()
        r = self.titlecmp2()
        self.assertEqual(r.returncode, 2)
        self.assertIn("b_game2.txt", r.stderr)

    def test_titlecmp_takes_the_title_apart(self):
        va, vb = bytearray(0x20000), bytearray(0x20000)
        vb[0x10000] = 1                                                       # (CPU address 1: shown)
        vb[0x8000] = 1                                                        # (not shown)
        ra, rb = bytearray(64), bytearray(64)
        ra[5], rb[5] = 0xC7, 0xCF
        title_files(self.tmp, "a", bytes(va), bytes(ra))
        title_files(self.tmp, "b", bytes(vb), bytes(rb), bytes(range(32)))
        r = run([sys.executable, "-I", BST / "titlecmp.py", self.tmp, "a", "b"])
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[:4], ["the title's picture (G7, 256 x 212): DIFFERENT in 1 bytes",
                                     "VRAM not shown by the title: 1 bytes differ: ['08000h:1']",
                                     "registers: ['R#5 C7/CF']", "palette: different (G7 does not use it)"])
        self.assertIn("music.txt: not in both records (an exact record's music2.txt: titlecmp2.py)", lines)
        self.assertIn("game_ram.bin, game_vram.bin: not in both records (an exact record's game2_*: titlecmp2.py)", lines)
        # hz_fresh's records: the music by line, the PSG writes, the game
        for tag, r6 in (("a", 5), ("b", 6)):
            p = psg_regs()
            rows = [f"{t} {scc_regs().hex()} {(p if t != 55 else psg_regs()[:6] + bytes([r6]) + psg_regs()[7:]).hex()}"
                    for t in (54, 55, 56)]
            (self.tmp / f"{tag}_music.txt").write_text("# t0\n" + "\n".join(rows) + "\n# end\n")
            (self.tmp / f"{tag}_psg.txt").write_text("5 7\n")
            (self.tmp / f"{tag}_game_ram.bin").write_bytes(bytes(0x1000))
            (self.tmp / f"{tag}_game_vram.bin").write_bytes(bytes(0x20000))
            (self.tmp / f"{tag}_game.txt").write_text("time 1 tick_n 300 g_frame 300\n")
        r = run([sys.executable, "-I", BST / "titlecmp.py", self.tmp, "a", "b"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("music ticks: 3 / 3", r.stdout)
        self.assertIn("music ticks that differ: 1; by register (ticks): {'PSG R6': 1}", r.stdout)
        self.assertIn("PSG writes (count hash): ['5', '7'] / ['5', '7']", r.stdout)
        self.assertIn("game RAM D000h-DFFFh: identical", r.stdout)
        (self.tmp / "b_title_pal.bin").unlink()
        self.assertEqual(run([sys.executable, "-I", BST / "titlecmp.py", self.tmp, "a", "b"]).returncode, 2)

    def test_partialcheck_offsets_follow_fs_run(self):
        import msxtext
        import partialcheck
        script = bytes([0, 2, 3]) + b"AB" + bytes([0x80, 2, 1]) + b"C" + bytes([0xFF, 7])
        self.assertEqual([partialcheck.offset_after(script, k) for k in (0, 1, 3, 4, 7, 8, 9, 20)],
                         [0, 3, 5, 8, 8, 9, 9, 9])
        self.assertEqual(partialcheck.offset_after(script, msxtext.fs_run(script)[1]), len(script) - 2)
        self.assertEqual(partialcheck.FS_N, 0xFBE)

    @unittest.skipUnless(LEVEL1_RAM.exists(), "needs build/ram/level1_full.bin (make ram)")
    def test_partialcheck_command_line(self):
        import msxtext
        import partialcheck
        ram = LEVEL1_RAM.read_bytes()
        glyphs = [msxtext.glyph_sc5(ram, g) for g in range(44)]
        script = {label: s for label, _, s in msxtext.bonus_scripts(ram)}["txt_bs_intro"]
        tag = bytes((0, 15, 10)) + b"TEST 2"

        def render(k: int) -> bytes:
            return msxtext.fs_render(glyphs, tag + script[:partialcheck.offset_after(script, k)] + b"\xff\x07")

        n = next(k for k in range(20, 400) if render(k) != render(k + 1))     # (call n + 1 draws a character)
        snap = bytearray(SNAP_LEN)
        snap[0x20000 + 0xFBE:0x20000 + 0xFC0] = n.to_bytes(2, "little")      # (fs_n)
        for k in (n, n + 1):
            snap[:162 * 128] = render(k)
            (self.tmp / "s.bin").write_bytes(snap)
            r = run([sys.executable, "-I", BST / "partialcheck.py", self.tmp / "s.bin", "txt_bs_intro", "--tag", "2"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn(f"s.bin: fs_n {n}: page 0 = the render of txt_bs_intro after {k} fs_step calls (", r.stdout)
            self.assertIn("TEST 2 first), pixel for pixel", r.stdout)
        snap[128 * 100] ^= 0x11
        (self.tmp / "s.bin").write_bytes(snap)
        r = run([sys.executable, "-I", BST / "partialcheck.py", self.tmp / "s.bin", "txt_bs_intro", "--tag", "2"])
        self.assertEqual(r.returncode, 1)
        self.assertIn(f"equals neither render ({n} or {n + 1} calls of txt_bs_intro)", r.stdout)
        r = run([sys.executable, "-I", BST / "partialcheck.py", self.tmp / "s.bin", "txt_bs_nope"])
        self.assertEqual(r.returncode, 2)


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
        self.assertEqual(len(lines), 55)          # (41 sets, level 2's 7 LV_TEST=2 ones, its 5 CHEAT=1 ones and
                                                  #  its 2 VAT_ANIM=1 VAT_TICK=1 ones)
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
set ::more_debuggables {}
array set ::regs {}
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
proc reg {name} { if {[info exists ::regs($name)]} { return $::regs($name) }; return 0 }
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
			switch -glob -- [lindex $args 0] { "VDP regs" { return 64 } "VDP palette" { return 32 } "* SCC*" { return 256 } default { return 16 } }
		}
		list { return [concat {memory {physical VRAM} {VDP regs} {VDP palette} {PSG regs}} $::more_debuggables] }
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
		remove_watchpoint { dict unset ::wps [lindex $args 0]; return }
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
run_until {[info exists ::hb_st] && $::hb_st == 30}
fire 0x0123
puts "bonus_intro [run_until {[info exists ::hb_st] && $::hb_st == 1}]"
for {set i 0} {$i < 120} {incr i} { fire 0x38; fire 0x39 }
mset 0xCFBE 10
puts "bonus_s6 [run_until {$::hb_st == 6}]"
mset 0xCFB8 0x9300; mset 0xCFBE 80
run_until {$::hb_st == 60}
fire 0x0123
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

# The final checks (np.tcl, ft.tcl, run8f.tcl) with the drives of a made-up build/emu: the keyboard
# drive, the shifted drive, np_job, then each flow driven by hand through its states, the speed jobs,
# c8f_chain's job list
TCL_FINAL = r"""
set tmp [lindex $argv 0]
set lab [lindex $argv 2]
source [file join [lindex $argv 1] tools bstest load.tcl]
set base [llength [file channels]]
set missing {}
foreach p {np_job np_keys_arm np_keys_disarm np_keys_mask np_keys_tick np_keys_end np_hb_init np_solved_setup
		np_title_setup np_t_record np_t_poll np_title0_setup np_t0_poll np_hf_step np_hf_tick np_hf_psg np_hf_game
		np_fire_setup np_f_note np_f_script np_f_first np_f_step np_two_setup np_2_w1 np_shift_drive np_2_ng np_2_w2
		np_wp_job np_wp_setup np_wp_on np_wp_hit np_wp_done np_two_title_setup np_2t_w1 np_2t_step np_2t_w2
		ft_job ft_clock ft_setup ft_classify ft_cb ft_write ft_done ft_flow_job ft_flow_setup ft_flow_wp
		ft_flow_done ft_boot_job ft_boot_setup ft_boot_init ft_boot_cb ft_boot_done ft_l1_job ft_l1_setup
		ft_l1_done c8_jobs c8_chain c8f_chain c8f_solved_job c8f_solved_setup} {
	if {[info procs $p] eq ""} { lappend missing $p }
}
puts "missing $missing"

# made-up drives in a made-up repository (build/ is git-ignored): the procs read them from ::hz_root
set ::hz_root $tmp
file mkdir [file join $tmp build emu]
proc wr {name text} {
	set f [open [file join $::hz_root build emu $name] w]
	puts -nonewline $f $text
	close $f
}
proc readf {path} {
	set f [open $path]
	set s [read $f]
	close $f
	return $s
}
wr pz_solve1.drive "00020208001810\n\n0\n\n"
wr pz_fail.drive "0002\n\n0\n\n"
wr drive_end.txt "0102\n100:0x900:0x2d0\n0\n150:5826:80:2\n"
wr drive_cov1.txt "00\n\n0\n\n"
set rom [file join $tmp x.rom]
set np [file join $tmp np]
# (pz_tick holds "call pz_frame": the breakpoints' byte condition)
proc stage_code {} { mset 0xA123 0x56CD; poke 0xA125 0xA4 }

# np_keys_arm: a drive's bytes as keys at each pass, the key held let go at pz_done; another arm
# lets go of a key an earlier one left held
stage_code
np_keys_arm $lab [file join $tmp build emu pz_solve1.drive]
foreach p {0 1 2 3 4 5 6} { mset 0xD000 $p; fire 0xA123 }
fire 0x7F10
puts "keys [join $::keys |]"
puts "keybps [dict size $::bps]"
set ::keys {}
np_keys_arm $lab [file join $tmp build emu pz_solve1.drive]
mset 0xD000 1; fire 0xA123
np_keys_arm $lab [file join $tmp build emu pz_fail.drive]
puts "rearm [join $::keys |] [dict size $::bps]"
np_keys_disarm
set ::keys {}

# np_shift_drive, np_job
np_shift_drive [file join $tmp build emu drive_end.txt] [file join $tmp shifted.txt] 3
puts "shift [join [split [string trim [readf [file join $tmp shifted.txt]]] \n] |]"
set j [np_job sj M2 np_solved_setup $np $rom $lab 1]
puts "job [lindex $j 0] [lindex $j 1] [lindex $j 3] [lindex $j 4] [file isdirectory $np]"
puts "jobsetup [lindex $j 2 0] [lindex $j 2 2] [lindex $j 2 end] [expr {[lindex $j 2 1] eq $np}]"

# a: the solved ending with the keys: the trace, the stage's keys, ok, the title, fire, the new game
array unset ::mem
stage_code
hz_chain [list [np_job sv SV np_solved_setup $np $rom $lab 1]]
run_until {$::machine eq "SV"}
mset 0xCFB8 0x9000; mset 0xCFBE 150
run_until {$::hb_st == 30}
fire 0x0123
run_until {$::hb_st == 1}
foreach p {0 1 2 3} { mset 0xD000 $p; fire 0xA123 }
fire 0x7F10
run_until {[string match "*stage done*" [readf [file join $np sv_bonus.txt]]]}
mset 0xCFBE 10
run_until {$::hb_st == 6}
mset 0xCFB8 0x9100; mset 0xCFBE 80
run_until {$::hb_st == 60}
fire 0x0123
run_until {$::hb_st == 2}
mset 0xEC44 1
run_until {[llength $::keys] >= 6}
mset 0xEC44 0; mset 0xCEE0 100
puts "solved [run_until {$::hz_state eq "done"}] $::hz_state | [join $::hz_msgs |] | keys [join $::keys |]"

# b: the exact title records after level 1's statistics (np_title0_setup) and after Brainstorm
# (np_title_setup): the title, four music ticks with two PSG writes after each, the game's tick 300
set ::more_debuggables [list "x.rom SCC SCC"]
proc to_game {} {
	mset 0xEC44 1
	run_until {$::h6_ps == 2}
	mset 0xEC44 0
	run_until {$::h6_ps == 3}
	set ::rc2_trace_done 1
}
proc title_record {tag} {
	set ::want $tag
	run_until {[info exists ::hf_tag] && $::hf_tag eq $::want && $::hf_st == 2}
	set ::romblock 3
	foreach t {54 55 56 57} {
		mset 0xC205 $t
		fire 0x4567
		set ::wp_last_address 0xA0; set ::wp_last_value 7; np_hf_psg
		set ::wp_last_address 0xA1; set ::wp_last_value [expr {$t & 0x3F}]; np_hf_psg
	}
	mset 0xC2B2 1
	run_until {$::hf_st == 3}
	mset 0x4100 0x00CD; poke 0x4102 0x42
	mset 0xCEE0 $::hf_ticks
	fire 0x4100
	return [run_until {$::hz_state eq "done"}]
}
array unset ::mem
hz_chain [list [np_job t0x T0 np_title0_setup $np $rom $lab 1]]
run_until {$::machine eq "T0"}
to_game
run_until {$::nt_st == 1}
mset 0xC202 1; mset 0xCEE0 517; mset 0xEC44 1
puts "t0x [title_record t0x] $::hz_state | [join $::hz_msgs |] | $::hf_ticks"
array unset ::mem
hz_chain [list [np_job tx TX np_title_setup $np $rom $lab 1]]
run_until {$::machine eq "TX"}
to_game
mset 0xCFB8 0x9000; mset 0xCFBE 150
run_until {$::hb_st == 30}
fire 0x0123
run_until {$::hb_st == 1}
mset 0xCFBE 10
run_until {$::hb_st == 6}
mset 0xCFB8 0x9300; mset 0xCFBE 80
run_until {$::hb_st == 60}
fire 0x0123
run_until {$::nt_st == 1}
mset 0xC202 1; mset 0xCEE0 3640; mset 0xEC44 1
puts "tx [title_record tx] $::hz_state | [join $::hz_msgs |] | $::hf_ticks $::hb_st"
set ::more_debuggables {}

# d: the text screens ended by fire
array unset ::mem
set ::keys {}
stage_code
hz_chain [list [np_job fi FI np_fire_setup $np $rom $lab]]
run_until {$::machine eq "FI"}
mset 0xCFB8 0x9000; mset 0xCFBE 60
run_until {[llength $::keys] >= 2}
foreach p {0 1} { mset 0xD000 $p; fire 0xA123 }
fire 0x7F10
mset 0xCFB8 0x9200; mset 0xCFBE 10
run_until {$::nf_st == 2}
mset 0xCFBE 61
run_until {$::nf_st == 3}
mset 0xEC44 1
run_until {[llength $::keys] >= 8}
mset 0xEC44 0; mset 0xCEE0 100
puts "fire [run_until {$::hz_state eq "done"}] $::hz_state | [join $::hz_msgs |] | keys [join $::keys |]"

# e: two stages (the script build): the first stage's result 1, the new game, the shifted drive and
# level 1's trace, the second stage armed
array unset ::mem
stage_code
hz_chain [list [np_job tw TW np_two_setup $np $rom $lab]]
run_until {$::machine eq "TW"}
foreach p {0 1} { mset 0xD000 $p; fire 0xA123 }
set ::regs(a) 1
fire 0x7F10
run_until {[info exists ::n2_bp]}
mset 0xCEE0 182
fire 0x40A5
set ::rc2_trace_done 1
run_until {[file exists [file join $np tw_pz2.txt]]}
puts "two [file exists [file join $np tw_pz1.txt]] [file exists [file join $np tw_l1.txt]] [info exists ::rpz_out] [info exists ::rd_out]"
set ::hz_done 1
puts "two_done [run_until {$::hz_state eq "done"}] $::hz_state | [join $::hz_msgs |] | [info exists ::rpz_out] [info exists ::rd_out]"
set ::regs(a) 0
hz_chain [list [np_job tt TT np_two_title_setup $np $rom $lab]]
run_until {$::machine eq "TT"}
puts "twotitle [info exists ::rpz_out] [info exists ::nk_bp] [dict size $::bps]"
set ::hz_done 1
run_until {$::hz_state eq "done"}

# f: the turbo R's watch: nothing counted before front_bonus, one write after it
array unset ::mem
hz_chain [list [np_wp_job wp WP $np $rom $lab]]
run_until {$::machine eq "WP"}
poke 0xC07C 7
fire 0x8249
set ::wp_last_address 0x4100; set ::wp_last_value 0x12; set ::regs(pc) 0x1234
np_wp_hit
puts "wp0 [np_wp_done] [dict size $::wps]"
set ::hz_done 1
puts "wp [run_until {$::hz_state eq "done"}] $::hz_state | [join $::hz_msgs |] | [dict size $::wps]"
unset ::regs(pc)

# g: the speed jobs: the clock unlocked, the hits by place, the files once done
array unset ::mem
stage_code
set fast [file join $tmp fast]
set j [ft_job fx537 FX $rom $lab $fast 5369318]
puts "ftjob [lindex $j 0] [lindex $j 1] [lindex $j 3] [lindex $j 4] [lindex $j 2 0] [lindex $j 2 end-1] [lindex $j 2 end]"
hz_chain [list $j]
run_until {$::machine eq "FX"}
puts "clock $::z80_freq $::z80_freq_locked $::too_fast_vram_access [set {::VDP.too_fast_vram_access_callback}]"
set ::regs(pc) 0x05B3; ft_cb
set ::regs(pc) 0xA8A5; ft_cb; ft_cb
mset 0xD000 0; fire 0xA123
fire 0x7F10
puts "ft [run_until {$::hz_state eq "done"}] $::hz_state | [join $::hz_msgs |] | callback '[set {::VDP.too_fast_vram_access_callback}]'"
unset ::regs(pc)
array unset ::mem
stage_code
hz_chain [list [ft_flow_job flow FL $rom $lab $fast 5369318]]
run_until {$::machine eq "FL"}
puts "flowsetup [dict size $::wps] [info exists ::nk_bp] $::ft_stopped"
set ::wp_last_value 1; ft_flow_wp
puts "flowwp $::ft_stopped '[set {::VDP.too_fast_vram_access_callback}]' $::pause"
puts "flow [run_until {$::hz_state eq "done"}] $::hz_state | [join $::hz_msgs |] | [dict size $::wps]"
array unset ::mem
hz_chain [list [ft_boot_job boot BT $rom $lab $fast 5369318]]
run_until {$::machine eq "BT"}
poke 0x4018 0xF3
fire 0x4018
set ::regs(pc) 0x05B0; set ::regs(sp) 0xF2E2
mset 0xF2E2 0x065A; mset 0xF2E4 0xF392; mset 0xF2E6 0xF040; mset 0xF2E8 0x247A
ft_boot_cb
puts "boot [run_until {$::hz_state eq "done"}] $::hz_state | [join $::hz_msgs |]"
unset ::regs(pc) ::regs(sp)
array unset ::mem
hz_chain [list [ft_l1_job l1 L1 $rom $lab $fast 3579545 1400]]
run_until {$::machine eq "L1"}
puts "l1setup [info exists ::rd_out] $::z80_freq $::z80_freq_locked"
set ::rc2_trace_done 1
puts "l1 [run_until {$::hz_state eq "done"}] $::hz_state | [join $::hz_msgs |] | [info exists ::rd_out]"

# h: c8f_chain: c8_chain's seven jobs and solved_m2; its setup; a missing file refused
set cd [file join $tmp cand]
file mkdir $cd
foreach r {B B-2M B-bonus B-bonus-2M} { foreach x {.ROM .labels} { close [open [file join $cd $r$x] w] } }
puts "c8f [c8f_chain $cd B [file join $tmp F] ft]"
set names {}
foreach j $::hz_jobs { lappend names [lindex $j 0] }
puts "c8fjobs [join $names |]"
puts "c8fsolved [lindex $::hz_jobs end 1] [lindex $::hz_jobs end 2 0] [lindex $::hz_jobs end 2 1] [lindex $::hz_jobs end 2 end]"
set ::q {}
puts "c8 [c8_chain $cd B [file join $tmp F] ft] [llength $::hz_jobs]"
set ::q {}
array unset ::mem
c8f_solved_setup sm [file join $tmp c8run] $rom $lab {100 300}
puts "c8fsetup [file exists [file join $tmp c8run sm_c8.txt]] [file exists [file join $tmp c8run sm_bonus.txt]] [info exists ::nk_bp] [info exists ::h7_bp]"
hz_clean
file delete [file join $cd B-bonus.labels]
puts "c8fmiss [catch {c8f_chain $cd B [file join $tmp F] ft} err] [string range $err 0 12]"
set ::q {}
hz_clean
puts "open [expr {[llength [file channels]] - $base}]"
"""

LABELS = {"pz_tick": 0xA123, "pz_frame": 0xA456, "pz_done": 0x7F10, "pz_boards": 0xF500, "ext_joy": 0xCE5A,
          "iv_late": 0x0123, "txt_bs_intro": 0x9000, "txt_bs_ok": 0x9100, "txt_bs_fail": 0x9200,
          "txt_bs_time": 0x9300, "isr_split": 0x0038, "isr_vblank": 0x0039, "INPUT_SCRIPT": 0, "BANK_MUSIC": 3,
          "mus_adv": 0x4567, "tick_start": 0x4100, "game_tick": 0x4200, "new_game": 0x40A5, "init": 0x4018,
          "front_bonus": 0x8249}


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

    def test_mocked_final_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp)
            (t / "t.labels").write_text("".join(f"{k}:\tequ ${v:04x}\n" for k, v in LABELS.items()))
            (t / "f.tcl").write_text(TCL_MOCK + TCL_FINAL)
            r = run(["tclsh", t / "f.tcl", t, ROOT, t / "t.labels"])
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            out = dict(line.split(" ", 1) if " " in line else (line, "") for line in r.stdout.splitlines())
            np_dir, fast = t / "np", t / "fast"
            self.assertEqual(out["missing"], "")
            # the keyboard drive: UP 20h, DOWN 40h, LEFT 10h, RIGHT 80h, SPACE 01h; let go at pz_done
            self.assertEqual(out["keys"], "down 8 40|up 8 40|down 8 80|up 8 80|down 8 81|up 8 81|down 8 01|up 8 01")
            self.assertEqual(out["keybps"], "0")
            self.assertEqual(out["rearm"], "down 8 40|up 8 40 2")
            self.assertEqual(out["shift"], "0000000102|103:0x900:0x2d0|0|153:5826:80:2")
            self.assertEqual(out["job"], "sj M2 $::hz_done 900 1")
            self.assertEqual(out["jobsetup"], "np_solved_setup sj 1 1")
            # a: the solved ending
            self.assertTrue(out["solved"].startswith("1 done | sv (SV): done in "), out["solved"])
            self.assertTrue(out["solved"].endswith("keys down 8 40|up 8 40|down 8 80|up 8 80|down 8 01|up 8 01"))
            pz = (np_dir / "sv_pz.txt").read_text().splitlines()
            self.assertEqual((pz[0], len(pz), pz[-1]), ("# D000 DC00 F500", 6, "# result 0"))
            notes = (np_dir / "sv_bonus.txt").read_text()
            for pat in (r"^stage done at .* s: result 0, passes 3,", r"^result ok at ", r"^title at .*\nfire at ",
                        r"^game tick_n 100 "):
                self.assertTrue(re.search(pat, notes, re.M), pat + "\n" + notes)
            # b: both exact title records, as titlecmp.py and titlecmp2.py read them
            self.assertTrue(out["t0x"].startswith("1 done | t0x (T0): done in "), out["t0x"])
            self.assertTrue(out["t0x"].endswith("| 817"), out["t0x"])
            self.assertTrue(out["tx"].startswith("1 done | tx (TX): done in "), out["tx"])
            self.assertTrue(out["tx"].endswith("| 3940 99"), out["tx"])                 # (hb_step stopped at the title)
            self.assertIn("the title after the statistics at ", (np_dir / "t0x_bonus.txt").read_text())
            self.assertIn("the title after the result at ", (np_dir / "tx_bonus.txt").read_text())
            for tag in ("t0x", "tx"):
                for n, size in (("title_vram.bin", 0x20000), ("title_regs.bin", 64), ("title_pal.bin", 32),
                                ("game2_vram.bin", 0x20000), ("game2_ram.bin", 0x1000)):
                    self.assertEqual((np_dir / f"{tag}_{n}").stat().st_size, size, f"{tag}_{n}")
                music = (np_dir / f"{tag}_music2.txt").read_text().splitlines()
                self.assertIn("SCC debuggable 'x.rom SCC SCC'", music[0])
                self.assertTrue(music[-1].endswith(" music end"), music[-1])
                rows = [m.split() for m in music[1:-1]]
                self.assertEqual([(x[0], len(x[1]), len(x[2]), x[3].split(":")[0]) for x in rows],
                                 [("54", 512, 32, "0"), ("55", 512, 32, "2"), ("56", 512, 32, "2"), ("57", 512, 32, "2")])
            self.assertIn("tick_n 817 (the title's game tick 300)", (np_dir / "t0x_game2.txt").read_text())
            self.assertIn("tick_n 3940 (the title's game tick 300)", (np_dir / "tx_game2.txt").read_text())
            r2 = run([sys.executable, "-I", BST / "titlecmp2.py", np_dir, "t0x", "tx"])
            self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)
            self.assertIn("music: ticks 54-57 / 54-57; 2 common ticks compared (4 PSG writes in them)", r2.stdout)
            r2 = run([sys.executable, "-I", BST / "titlecmp.py", np_dir, "t0x", "tx"])
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertIn("the title's picture (G7, 256 x 212): identical", r2.stdout)
            # d: the text screens ended by fire
            self.assertTrue(out["fire"].startswith("1 done | fi (FI): done in "), out["fire"])
            self.assertTrue(out["fire"].endswith(
                "keys down 8 01|up 8 01|down 8 40|up 8 40|down 8 01|up 8 01|down 8 01|up 8 01"), out["fire"])
            fire = [line.split(" at ")[0].split(":")[0] for line in (np_dir / "fi_fire.txt").read_text().splitlines()]
            self.assertEqual(fire, ["# fi", "intro", "the stage's first pass", "the result screen (fail)", "result",
                                    "the title", "fire on the title", "the new game"])
            for n in ("fi_intro60.bin", "fi_result60.bin", "fi_game100.bin", "st_fi/p0001.bin"):
                self.assertEqual((np_dir / n).stat().st_size, SNAP_LEN, n)
            self.assertEqual((np_dir / "fi_intro60.bin").read_bytes()[0x20000 + 0xFBE], 60)     # (fs_n: partialcheck.py)
            # e: two stages
            self.assertEqual(out["two"], "1 1 1 1")
            self.assertTrue(out["two_done"].startswith("1 done | tw (TW): done in "), out["two_done"])
            self.assertTrue(out["two_done"].endswith("| 0 0"))                          # (hz_clean closed both)
            self.assertEqual((np_dir / "tw_drive_end.txt").read_text(), "00" * 182 + "0102\n282:0x900:0x2d0\n0\n332:5826:80:2\n")
            notes = (np_dir / "tw_bonus.txt").read_text()
            self.assertTrue(re.search(r"^first stage done at .* s: result 1, passes 1,", notes, re.M), notes)
            self.assertIn("tick_n 182: drive_end's frames moved by 182", notes)
            self.assertTrue((np_dir / "tw_pz2.txt").read_text().startswith("# D000 DC00 F500"))
            self.assertEqual(out["twotitle"], "1 1 4")
            # f: the turbo R's watch
            self.assertEqual(out["wp0"], "0 1")
            self.assertTrue(out["wp"].startswith("1 done | wp (WP): done in ") and out["wp"].endswith("| 0"), out["wp"])
            wp = (np_dir / "wp_wp.txt").read_text().splitlines()
            self.assertEqual(wp[0], "# wp: x.rom on WP: writes to 4000h-7FFFh from front_bonus' entry to level 2's game "
                                    "frame 100 (the new game's tick 100 in a flow without level 2)")
            self.assertRegex(wp[1], r"^watch from [\d.]+ s \(front_bonus\) to [\d.]+ s \(the new game's tick 100, g_frame 0, "
                                    r"cpu_tr 0\): 1 writes \{4100<-12 pc 1234 at [\d.]+ s\}$")
            # g: the speed jobs
            self.assertEqual(out["ftjob"], "fx537 FX [ft_done] 300 ft_setup 5369318 solve1")
            self.assertEqual(out["clock"], "5369318 off real ft_cb")
            self.assertTrue(out["ft"].endswith("| callback ''"), out["ft"])
            self.assertRegex((fast / "flow" / "fx537.txt").read_text(),
                             r"^FX: too fast VRAM accesses 3: cartridge 2 \{a8a5@[\d.]+ a8a5@[\d.]+\}, BIOS 1 \{05b3@[\d.]+\} "
                             r"\(too_fast_vram_access real, z80_freq 5369318, locked off\); result 0, passes 0, emulated [\d.]+ s\n$")
            self.assertTrue((fast / "tr" / "fx537.txt").read_text().startswith("# D000 DC00 F500"))
            self.assertEqual(out["flowsetup"], "1 1 0")
            self.assertEqual(out["flowwp"], "1 '' on")
            self.assertTrue(out["flow"].startswith("1 done | flow (FL): done in ") and out["flow"].endswith("| 0"))
            self.assertRegex((fast / "flow" / "flow.txt").read_text(),
                             r"^FL: power-on to the title's start after the stage \(front_mode 1 at [\d.]+ s\): too fast VRAM "
                             r"accesses 0: cartridge 0 \{\}, BIOS 0 \{\} \(z80_freq 5369318, locked off\); AG 805Eh 0, passes 0\n$")
            self.assertTrue(out["boot"].startswith("1 done | boot (BT): done in "), out["boot"])
            self.assertRegex((fast / "flow" / "boot.txt").read_text(),
                             r"^BT: the first 6 s at z80_freq 5369318: too fast VRAM accesses 1; the cartridge's init at "
                             r"[\d.]+ s; BIOS hits: \{pc 05b0 at [\d.]+ s, sp f2e2: 065a f392 f040 247a\}\n$")
            self.assertEqual(out["l1setup"], "1 3579545 off")
            self.assertTrue(out["l1"].startswith("1 done | l1 (L1): done in ") and out["l1"].endswith("| 0"), out["l1"])
            self.assertRegex((fast / "flow" / "l1.txt").read_text(),
                             r"^L1: level 1, 0 ticks of drive_cov1: too fast VRAM accesses 0: cartridge 0 \{\}, BIOS 0 \{\} "
                             r"\(z80_freq 3579545, locked off\), emulated [\d.]+ s\n$")
            # h: the candidates' chain with the solved ending
            self.assertEqual(out["c8f"], "started 8 job(s)")
            self.assertEqual(out["c8fjobs"], "fresh ft|fresh ft_2m|bonus_m2|bonus_f1|bonus2m_m2|prod_m2|prod_f1|solved_m2")
            self.assertEqual(out["c8fsolved"], "Gradiente_Expert20_64K c8f_solved_setup solved_m2 100 300 450 600 650 700")
            self.assertEqual(out["c8"], "started 7 job(s) 7")
            self.assertEqual(out["c8fsetup"], "1 1 1 1")
            self.assertEqual(out["c8fmiss"], "1 c8_chain: no ")
            self.assertEqual(out["open"], "0")


if __name__ == "__main__":
    unittest.main()
