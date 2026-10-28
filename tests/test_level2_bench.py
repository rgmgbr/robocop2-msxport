"""Level 2's bench (the level-2 plan's step 2): the field set analysis/amiga_ram_l2.tsv, tools/tracecmp.py
--fields, tools/l2mock.py, tools/l2drives.py, and with Unicorn and the game's data tools/amigaemu.py game
--level 2 and tools/amigacov.py --level 2. Synthetic traces where the game's data is not needed."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import l2drives  # noqa: E402
import l2mock  # noqa: E402
import tracecmp  # noqa: E402

FIELDS_L2 = ROOT / "analysis" / "amiga_ram_l2.tsv"
LEVEL2_RAM = ROOT / "build" / "ram" / "level2_full.bin"
EXTRACTED = ROOT / "build" / "extracted"
# The plan's 4.1: the 12 references' sha256 prefixes (the bench report's, reproduced at step 2)
PLAN_REFS = {"end": "e0ecb97c30288d6d", "tour": "d0ef114623da05c8", "lift": "978d9cc7dec76d65",
             "trolley": "8b93c3bd428166f4", "trolley_sharp": "3c810e16ee4d22eb", "trolley_fair": "9e608b5a5255c74f",
             "trolley_poor": "ba9dbf04d18c70e0", "vat": "05a3aacea265b2c4", "cont": "02692c53cc6458c7",
             "over": "3d3f211d54e83db7", "fuzz": "8bdc1c303d6c7742", "flow_l2_end": "e65540af1e959526"}
# The drives' files (drivejoy.py's output; the first eight equal the bench report's)
DRIVE_SHA = {"end": "2058d993448c10d6", "tour": "615dd3a228e7a2bf", "lift": "72863860f0a1bfd3",
             "trolley": "4819c95d8b09d275", "vat": "c7908c621d12ca1c", "cont": "6825e576a26faf5b",
             "over": "6825e576a26faf5b", "fuzz": "5abe5dff8434659a", "barrel": "2d44023921b95a71",
             "mine": "c0458b1a1017df03", "t1left": "aecc6b41cc871e4e", "drone": "c7b689deb28fb66f"}
OWN = {"spawn", "objl", "special", "marker_ptr", "vat_phase", "obj06_countdown", "diff_table", "continues"}


def base_name(f: dict) -> str:
    return f["name"].split("[")[0]


def msx_home(f: dict) -> int:
    if f["msx"] is not None:
        return f["msx"]
    a = f["addr"]
    return 0xD000 + a - tracecmp.RAM0 if a < tracecmp.GLOB0 else 0xDC00 + a - tracecmp.GLOB0


class FieldSetTests(unittest.TestCase):
    def setUp(self):
        self.l1 = tracecmp.fields()
        self.l2 = tracecmp.fields(FIELDS_L2)

    def test_counts_and_the_default(self):
        self.assertEqual(len(self.l1), 948)
        self.assertEqual(len(self.l2), 1022)
        self.assertEqual(tracecmp.FIELDS.name, "amiga_ram.tsv")
        self.assertEqual(len(tracecmp.fields(None)), 948)

    def test_level1_records_replaced(self):
        for f in self.l2:
            for lo, hi in ((0x9626, 0x97B0), (0xA562, 0xA828), (0x9018, 0x9088)):     # level 1's lists
                self.assertFalse(lo <= f["addr"] < hi, f["name"])
        names = {base_name(f) for f in self.l2}
        self.assertTrue(OWN <= names, OWN - names)
        self.assertEqual({base_name(f) for f in self.l1} - names, set())             # every level-1 name kept

    def test_level2_homes(self):
        homes = {}
        for f in self.l2:
            n = base_name(f)
            if n in OWN and f["msx"] is not None:
                lo, hi = homes.get(n, (0x10000, 0))
                homes[n] = (min(lo, f["msx"]), max(hi, f["msx"] + (2 if "ptr" in f else f["size"])))
        self.assertEqual(homes["spawn"], (0xDD80, 0xDFB0))          # 40 x 14: the end word at DFB0h follows
        self.assertEqual(homes["vat_phase"], (0xDFB2, 0xDFDE))      # the plan's 3.4: DFB2h, after the end word
        self.assertEqual(homes["objl"], (0xEE00, 0xF010))
        self.assertEqual(homes["special"], (0xE900, 0xE996))
        self.assertEqual(homes["obj06_countdown"], (0xDD1A, 0xDD1C))
        self.assertEqual(homes["diff_table"], (0xDD0C, 0xDD0E))
        self.assertEqual(homes["marker_ptr"], (0xDD08, 0xDD0A))
        spans = sorted(homes.values())
        for (a, b), (c, _d) in zip(spans, spans[1:]):
            self.assertLessEqual(b, c, "level 2's homes overlap")

    def test_every_field_inside_a_dumped_block(self):
        for f in self.l2:
            m, size = msx_home(f), 2 if "ptr" in f else f["size"]
            self.assertTrue(any(b <= m and m + size <= b + n for b, n in l2mock.BLOCKS.items()), f["name"])


def synthetic_rows(fields: list[dict], n: int, seed: int = 1) -> list[str]:
    """Bench rows (--trace-ram's shape) with random state: the RAM and globals, and one code block for
    every field outside them."""
    rnd = random.Random(seed)
    rows = []
    for i in range(n):
        code = {}
        for f in fields:
            a = f["addr"]
            if not (tracecmp.RAM0 <= a < tracecmp.RAM0 + 0xBEC or tracecmp.GLOB0 <= a < tracecmp.GLOB0 + 0x100):
                code[f"{a:x}"] = bytes(rnd.randrange(256) for _ in range(f["size"])).hex()
        rows.append(json.dumps({"keys": "", "ram": bytes(rnd.randrange(256) for _ in range(0xBEC)).hex(),
                                "glob": bytes(rnd.randrange(256) for _ in range(0x100)).hex(), "code": code}))
    return rows


class MockTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fields = tracecmp.fields(FIELDS_L2)
        self.amiga = self.tmp / "a.jsonl"
        self.amiga.write_text("\n".join(synthetic_rows(self.fields, 6)) + "\n")
        self.labels = self.tmp / "m.labels"
        self.labels.write_text("diff_tab:\tequ $9000\nmk_tab2:\tequ $A123\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def compare(self, mutate=None) -> tuple[int, str]:
        msx = self.tmp / "m.txt"
        with self.amiga.open() as fi:
            lines = list(l2mock.mock_lines(self.fields, tracecmp.labels(self.labels), fi, mutate))
        msx.write_text("\n".join(lines) + "\n")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = tracecmp.compare_ram(self.amiga, msx, 3, self.labels, FIELDS_L2)
        return rc, out.getvalue()

    def test_a_perfect_port_gives_0_differ(self):
        rc, out = self.compare()
        self.assertEqual(rc, 0, out)
        self.assertIn("6 game frames compared (6 Amiga, 6 MSX), 1022 fields: 0 differ", out)

    def test_a_wrong_field_is_caught_from_its_row(self):
        rc, out = self.compare(("vat_phase[3].0", 4, 0x4242))
        self.assertEqual(rc, 1)
        self.assertIn("1022 fields: 2 differ", out)
        self.assertIn("game frame 4 (-): vat_phase[3].0", out)

    def test_a_pointer_field_is_compared_as_an_offset(self):
        rows = [json.loads(r) for r in self.amiga.read_text().split("\n") if r]
        for r in rows:                                               # $8060 = POOR's table, $C72E
            g = bytearray.fromhex(r["glob"])
            g[0x60:0x64] = (0xC72E).to_bytes(4, "big")
            r["glob"] = g.hex()
        self.amiga.write_text("".join(json.dumps(r) + "\n" for r in rows))
        with self.amiga.open() as fi:
            line = next(l2mock.mock_lines(self.fields, tracecmp.labels(self.labels), fi))
        dd00 = tracecmp.swapped(bytes.fromhex(line.split()[2]))
        self.assertEqual(dd00[0x0C:0x0E], (0x9000 + 0x18).to_bytes(2, "big"))   # diff_tab + POOR's offset
        self.assertEqual(self.compare()[0], 0)
        rc, out = self.compare(("diff_table", 0, 0x9000))                       # SHARP where the trace has POOR
        self.assertEqual(rc, 1)
        self.assertIn("diff_table 0x18/0x0", out)
        self.assertIn("1022 fields: 6 differ", out)

    def test_the_mock_rows_are_the_rc2_drive_hit_blocks(self):
        with self.amiga.open() as fi:
            line = next(l2mock.mock_lines(self.fields, {}, fi))
        self.assertEqual([len(h) // 2 for h in line.split()], [0xBEC, 0x100, 0x300, 0x300, 0x100])


class DriveTests(unittest.TestCase):
    def test_the_references_table(self):
        self.assertEqual(len(l2drives.REFS), 16)
        for name, (drive, carry, gframes, rows, sha, _what) in l2drives.REFS.items():
            self.assertIn(drive, l2drives.DRIVES, name)
            self.assertEqual(len(sha), 16, name)
            self.assertLessEqual(rows, gframes + 1, name)
        for name, sha in PLAN_REFS.items():
            self.assertEqual(l2drives.REFS[name][4], sha, name)
        self.assertEqual({n for n in l2drives.REFS if n not in PLAN_REFS}, {"barrel", "mine", "t1left", "drone"})

    def test_the_drives_are_made_byte_for_byte(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(l2drives.make(tmp, []), 0)
            for name, sha in DRIVE_SHA.items():
                self.assertEqual(hashlib.sha256((tmp / f"l2_{name}.drive").read_bytes()).hexdigest()[:16], sha, name)
        finally:
            shutil.rmtree(tmp)

    def test_the_bench_commands(self):
        out = Path("/o")
        cmd = l2drives.ref_cmd("trolley_poor", out, "PY")
        self.assertEqual(cmd, ["PY", "-I", "tools/amigaemu.py", "game", "--level", "2", "--carry", "10050:2:0:poor",
                               "--gframes", "640", "--drive", "/o/l2_trolley.drive", "--stop-at-end",
                               "--trace", "/o/l2_trolley_poor_ram.jsonl", "--trace-ram"])
        cmd = l2drives.ref_cmd("flow_l2_end", out, "PY")
        self.assertIn("build/emu/drive_end.txt:build/emu/pz_fail.drive:build/emu/fr_good.drive", cmd)
        self.assertNotIn("--carry", cmd)
        self.assertEqual(cmd[cmd.index("--drive") + 1], "/o/l2_end.drive")


def bench_or_skip(test: unittest.TestCase):
    if not (LEVEL2_RAM.exists() and (EXTRACTED / "files").exists()):
        test.skipTest("needs build/ram and build/extracted")
    try:
        import amigaemu
    except (ImportError, SystemExit):              # (amigaemu.py exits without Unicorn)
        test.skipTest("needs Unicorn")
    return amigaemu


class BenchTests(unittest.TestCase):
    def test_parse_carry(self):
        ae = bench_or_skip(self)
        self.assertEqual(ae.parse_carry("10050:2:0:good"), {"score": 0x10050, "lives": 2, "continues": 0, "table": 0xC71E})
        self.assertEqual(ae.parse_carry("0:0:1:c72e")["table"], 0xC72E)
        with self.assertRaises(ValueError):
            ae.parse_carry("10050:2:0")

    def test_the_code_blocks_per_level(self):
        ae = bench_or_skip(self)
        self.assertIs(ae.GameBench.code_blocks, ae.CODE_BLOCKS)
        self.assertEqual(ae.CODE_BLOCKS[0], (0x9626, 0x97B0))
        self.assertIs(ae.Level2Bench.code_blocks, ae.CODE_BLOCKS_L2)
        self.assertEqual([lo for lo, _hi in ae.CODE_BLOCKS_L2[:6]], [0x97B0, 0xA828, 0x9088, 0x92DA, 0xA4A6, 0xD1DC])

    def test_the_direct_start_reproduces_the_end_reference(self):
        ae = bench_or_skip(self)
        b = ae.Level2Bench(EXTRACTED, LEVEL2_RAM)
        b.start_direct(ae.parse_carry(ae.CARRY_L2))
        self.assertEqual((b.read_word(0x8050), b.read_word(0x8052), b.read_long(0x8046), b.read_long(0x8060)),
                         (1, 1, 0x10050, 0xC71E))
        tmp = Path(tempfile.mkdtemp())
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                l2drives.make(tmp, ["end"])
            script, tele, god, pokes = ae.read_drive(tmp / "l2_end.drive")
        finally:
            shutil.rmtree(tmp)
        sink = io.StringIO()
        b.play(20, script, True, tele, god, 0, sink, pokes)
        rows = sink.getvalue()
        self.assertEqual(rows.count("\n"), 21)
        first = json.loads(rows.split("\n")[0])
        self.assertEqual((first["player_x"], first["player_y"]), (352, 784))
        self.assertEqual(list(first["code"])[:3], ["97b0", "a828", "9088"])
        # the first 21 rows of build/emu/l2_end_ram.jsonl (sha256 e0ecb97c30288d6d)
        self.assertEqual(hashlib.sha256(rows.encode()).hexdigest()[:16], "4f40a55584231586")

    def test_the_level2_coverage_scenario(self):
        bench_or_skip(self)
        import amigacov
        frames, make = amigacov.SCENARIOS["level2"]
        runs = [amigacov.parse_run(s) for s in make(frames)]
        self.assertEqual([r["frames"] for r in runs], [23250, 4400, 1700])
        self.assertEqual([len(r["tele"]) for r in runs], [153, 0, 8])
        self.assertTrue(all(r["god"] for r in runs))
        r = amigacov.parse_run("10:2:f;tele=5:100:200;poke=7:0x169A:256:2;frames=50")
        self.assertEqual((r["script"], r["tele"], r["pokes"], r["frames"], r["god"]),
                         ([(10, 2, "f")], [(5, 100, 200)], [(7, 0x169A, 256, 2)], 50, False))


if __name__ == "__main__":
    unittest.main()
