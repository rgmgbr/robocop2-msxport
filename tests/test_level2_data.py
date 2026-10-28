"""Level 2's map data (its plan's step 6): palette C (tools/msxlvpal.py), the conversion
(tools/msxconv.py --rows 50), the map writers' and the vats' checks (tools/mapcells.py --level 2) and
analysis/amiga_tables.tsv's bank l2."""
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import amitab  # noqa: E402
import cellmasks  # noqa: E402
import mapcells  # noqa: E402
import msxlvpal  # noqa: E402

X = ROOT / "build" / "extracted"                     # make extract
DATAL2 = X / "files" / "DATAL2_18.bin"
MAIN = X / "boot" / "main_8000.bin"
L2_RAM = ROOT / "build" / "ram" / "level2_full.bin"  # make ram
JOINT = ROOT / "build" / "msx" / "robocop"           # level 1's joint palette (make msx)
TSV = ROOT / "analysis" / "amiga_tables.tsv"
HAVE_DATA = all(p.exists() for p in (DATAL2, MAIN, L2_RAM, JOINT.with_suffix(".pal"), JOINT.with_suffix(".remap")))
# the plan's palette C (default 16): level 1's with 9 = 555, 11 = 015, 13 = 012
PALETTE_C = "000 432 455 344 333 000 111 234 222 555 210 015 100 012 500 630"
LEVEL1 = "000 432 455 344 333 000 111 234 222 666 210 012 100 001 500 630"
REMAP1 = [0, 6, 12, 10, 15, 11, 13, 12, 8, 4, 14, 14, 12, 1, 1, 9]
# the vats: first cell (row, column), columns, cells a column (level_tick_1 $91BC, the records at $95B2)
VATS = [((40, 45), 12, 9), ((40, 73), 10, 9), ((40, 90), 10, 9), ((43, 118), 16, 6), ((18, 111), 22, 4),
        ((18, 71), 20, 4), ((18, 30), 13, 4)]


def pal(text: str) -> list:
    return [tuple(int(v) for v in c) for c in text.split()]


def run(*args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", *map(str, args)], capture_output=True, text=True, cwd=ROOT)


class PaletteRuleTests(unittest.TestCase):
    def test_entries_take_the_new_values_their_colours_agree_on(self):
        base, remap = pal(LEVEL1), list(REMAP1)
        old = [0, 0x222, 0x200, 0x531, 0xD70, 0x024, 0x012, 0x310, 0x444, 0x666, 0xB00, 0x800, 0x400, 0x864, 0xB97, 0xCCC]
        new = list(old)
        new[5], new[6], new[10], new[11], new[15] = 0x03A, 0x025, 0xA00, 0x700, 0xBBB
        p, notes = msxlvpal.palette_c(base, remap, old, new)
        self.assertEqual(" ".join(msxlvpal.name(c) for c in p), PALETTE_C)
        self.assertTrue(any(n.startswith("entry 14: 500 kept") for n in notes), notes)
        # both colours of a shared entry on one value: the entry follows them
        new[11] = 0xA00
        p, _ = msxlvpal.palette_c(base, remap, old, new)
        self.assertEqual(p[14], (5, 0, 0))
        new[10] = new[11] = 0x700
        p, _ = msxlvpal.palette_c(base, remap, old, new)
        self.assertEqual(p[14], (3, 0, 0))
        # a colour in RoboCop's entries 1-7 cannot follow: kept, and reported
        new[1] = 0x555
        p, notes = msxlvpal.palette_c(base, remap, old, new)
        self.assertEqual(p[:8], base[:8])
        self.assertTrue(any("c1 222 -> 555 keeps RoboCop's entry 6" in n for n in notes), notes)

    def test_checks_catch_each_failure(self):
        base, remap = pal(LEVEL1), list(REMAP1)
        c = pal(PALETTE_C)
        self.assertEqual(msxlvpal.checks(c, base, remap, 2.4, 2.5), [])
        moved = list(c)
        moved[3] = (3, 4, 5)
        self.assertIn("entries 0-7", msxlvpal.checks(moved, base, remap, 2.4, 2.5)[0])
        flash = list(remap)
        flash[13] = 7
        self.assertIn("[7]", msxlvpal.checks(c, base, flash, 2.4, 2.5)[0])
        grey0 = list(c)
        grey0[0] = (1, 1, 1)
        bad = msxlvpal.checks(grey0, [grey0[0]] + base[1:], remap, 2.4, 2.5)
        self.assertEqual(len(bad), 1)
        self.assertIn("colour 0", bad[0])
        self.assertIn("option A", msxlvpal.checks(c, base, remap, 2.6, 2.5)[0])

    def test_lab_and_delta_e(self):
        self.assertEqual(msxlvpal.lab((0.0, 0.0, 0.0)), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(msxlvpal.delta_e(msxlvpal.lab_msx((7, 7, 7)), msxlvpal.lab_amiga(0x000)), 100, delta=0.01)
        # an Amiga colour and its plain 3-bit level: equal when the level is exact (F -> 7)
        self.assertAlmostEqual(msxlvpal.delta_e(msxlvpal.lab_msx((7, 0, 7)), msxlvpal.lab_amiga(0xF0F)), 0, delta=1e-9)
        self.assertEqual(msxlvpal.nearest_remap(pal(LEVEL1), [0] + [0x666] * 15)[1:], [4] * 15)


class VatGeometryTests(unittest.TestCase):
    def setUp(self):
        # a RAM image with one vat record (vat 0's), its T tables and a map that holds one look
        self.img = bytearray(mapcells.MAP_ADDR + 160 * 50 * 2)
        struct.pack_into(">4Hh", self.img, 0x100, 848, 640, 1024, 7, -1)
        self.t = [[0x1000 + 0x80 * (16 * k + d) for d in range(16)] for k in range(3)]
        for k, name in enumerate(mapcells.VAT_WORDS):
            struct.pack_into(">16H", self.img, 0x200 + 32 * k, *self.t[k])
        self.tabs = {"hz_l2": {"addr": 0x100}, "vat_top": {"addr": 0x200}, "vat_odd": {"addr": 0x220},
                     "vat_even": {"addr": 0x240}}

    def put(self, row, col, word):
        struct.pack_into(">H", self.img, mapcells.MAP_ADDR + 2 * (160 * row + col), word)

    def test_cells_and_looks_as_level_tick_1_writes_them(self):
        vs, t = mapcells.vats(bytes(self.img), self.tabs, "l2", 160, 50)
        self.assertEqual(t, self.t)
        self.assertEqual((len(vs), len(vs[0]), len(vs[0][0])), (1, 12, 9))
        self.assertEqual((vs[0][0][0], vs[0][11][8]), ((40, 45), (48, 56)))
        column = vs[0][3]
        for k, (r, c) in enumerate(column):
            self.put(r, c, self.t[0][5] if k == 0 else self.t[1 + ((k - 1) & 1)][5])
        self.assertEqual(mapcells.column_look(bytes(self.img), column, 160, t), 5)
        self.put(*column[4], self.t[1][5])                 # (row 4 must be T2's)
        self.assertIsNone(mapcells.column_look(bytes(self.img), column, 160, t))

    def test_vat_checks(self):
        for column in mapcells.vats(bytes(self.img), self.tabs, "l2", 160, 50)[0][0]:
            for k, (r, c) in enumerate(column):
                self.put(r, c, self.t[0][2] if k == 0 else self.t[1 + ((k - 1) & 1)][2])
        otile = struct.pack("<512H", *range(512))
        bad, summary = mapcells.vat_problems(bytes(self.img), self.tabs, "l2", 160, 50, set(), otile, 512)
        self.assertEqual(bad, [])
        self.assertIn("1 vats, 108 cells in 12 columns", summary)
        bad, _ = mapcells.vat_problems(bytes(self.img), self.tabs, "l2", 160, 50, {(44, 50)}, otile, 40)
        self.assertEqual(len(bad), 2, bad)                  # (an object cell in the vat; tiles 40-79 past 40)
        self.put(40, 45, self.t[0][2] | 1)
        bad, _ = mapcells.vat_problems(bytes(self.img), self.tabs, "l2", 160, 50, set(), otile, 512)
        self.assertTrue(any("with attributes" in b for b in bad), bad)
        self.assertTrue(any("no look" in b for b in bad), bad)
        # a record that is no vat of the map (misread data) stops at once
        struct.pack_into(">4H", self.img, 0x100, 848, 640, 848 + 16 * 160, 7)
        with self.assertRaises(SystemExit):
            mapcells.vats(bytes(self.img), self.tabs, "l2", 160, 50)


@unittest.skipUnless(L2_RAM.exists() and TSV.exists(), "level 2's RAM image not built (make ram)")
class TablesBankL2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = amitab.parse(TSV)
        cls.tabs = {r["label"]: r for r in cls.rows}
        cls.img = L2_RAM.read_bytes()

    def end_after(self, label, size):
        """Entries of the list at the label, up to its end word (a negative first word)."""
        a, n = self.tabs[label]["addr"], 0
        while struct.unpack_from(">h", self.img, a + n * size)[0] >= 0:
            n += 1
        return n

    def test_labels_unique_and_the_copies_level_1s(self):
        labels = [r["label"] for r in self.rows]
        self.assertEqual(len(labels), len(set(labels)))
        l2 = [r for r in self.rows if r["bank"] == "l2"]
        self.assertEqual(len(l2), 34 + ("spawn_l2" in self.tabs))
        copies = [r for r in l2 if r["label"].endswith("_l2") and r["label"][:-3] in self.tabs]
        self.assertEqual(sorted(r["label"][:-3] for r in copies),
                         sorted(["t3_gfx", "t3_size", "t4_gx", "t4_gy", "t4_tgfx", "t4_tx", "t4_ty", "t4_tsize",
                                 "t12_gfx", "t12_dx", "t12_mx", "t12_my", "t30_dy", "t45_gfx", "t45_dy"]))
        for r in copies:
            src = self.tabs[r["label"][:-3]]
            self.assertEqual((r["addr"], r["count"], r["kind"], src["bank"]), (src["addr"], src["count"], src["kind"], "l1"))

    def test_the_lists_end_where_their_counts_say(self):
        hdr = struct.unpack_from(">10L", self.img, self.tabs["l2_hdr"]["addr"])
        self.assertEqual((hdr[0], hdr[1], hdr[2], hdr[3], hdr[6]), (self.tabs["objl_l2"]["addr"], self.tabs["hz_l2"]["addr"],
                                                                     self.tabs["spl_l2"]["addr"], 0x97B0,
                                                                     self.tabs["mk_tab2"]["addr"]))
        self.assertEqual((self.end_after("objl_l2", 12), self.tabs["objl_l2"]["count"]), (44, 44 * 12 + 2))
        self.assertEqual((self.end_after("hz_l2", 8), self.tabs["hz_l2"]["count"]), (7, 7 * 4 + 1))
        self.assertEqual((self.end_after("mk_tab2", 6), self.tabs["mk_tab2"]["count"]), (9, 9 * 3 + 1))
        spl = struct.unpack_from(">10l", self.img, self.tabs["spl_l2"]["addr"])
        self.assertEqual(spl[9], -1)
        sp = self.tabs["sp_l2"]
        self.assertTrue(all(sp["addr"] <= a < sp["addr"] + sp["count"] for a in spl[:9]))
        # the phases: a word per column of the widest vat, + the next one's high byte
        self.assertEqual(self.tabs["vat_ph0"]["count"], max(n for _, n, _ in VATS) + 1)
        # level 2's spawn list (40 entries) waits for cellmasks.py's SW_MAX 40 (the plan's step 5)
        n = 0
        while struct.unpack_from(">h", self.img, 0x97B0 + 14 * n)[0] >= 0:
            n += 1
        self.assertEqual(n, 40)
        if "spawn_l2" in self.tabs:
            self.assertGreaterEqual(cellmasks.SW_MAX, n, "spawn_l2 listed: tools/cellmasks.py must take 40 entries")
            self.assertEqual((self.tabs["spawn_l2"]["addr"], self.tabs["spawn_l2"]["count"]), (0x97B0, 40 * 14 + 2))

    def test_at_l2_inc_holds_every_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run(ROOT / "tools" / "amitab.py", L2_RAM, TSV, tmp)
            self.assertEqual(r.returncode, 0, r.stderr)
            inc = (Path(tmp) / "at_l2.inc").read_text()
        for row in self.rows:
            if row["bank"] == "l2":
                self.assertIn(f"\n{row['label']}:", inc)
                self.assertIn(f"\n{row['label']}_end:", inc)

    def test_mine_words_are_act_0c_s(self):
        # $9EE8 and $9EF8: move.w #word,($A4A6).l
        for addr, word in zip((0x9EE8, 0x9EF8), mapcells.MINE_WORDS):
            self.assertEqual(self.img[addr:addr + 8], struct.pack(">HHL", 0x33FC, word, 0xA4A6))
        self.assertEqual(struct.unpack_from(">H", self.img, 0xA4A6)[0], mapcells.MINE_WORDS[0])

    def test_level2_writers_and_vats(self):
        cells, words = mapcells.writers(self.img, self.tabs, "l2", 160, 50)
        every = set().union(*cells.values())
        self.assertEqual((len(every), [sum(1 for r, _ in every if r % 2 == p) for p in (0, 1)]), (289, [146, 143]))
        self.assertEqual(sorted({w & 0x7F for ws in words.values() for w in ws}), [0, 1, 2])
        mines = [k for k in cells if k.endswith("(type 30h)")]
        self.assertEqual(len(mines), 4)
        self.assertTrue(all(set(mapcells.MINE_WORDS) <= set(words[k]) for k in mines))
        self.assertFalse(any(k.startswith("beam") for k in cells))
        vs, t = mapcells.vats(self.img, self.tabs, "l2", 160, 50)
        self.assertEqual([(v[0][0], len(v), len(v[0])) for v in vs], VATS)
        vat = {c for v in vs for column in v for c in column}
        self.assertEqual((len(vat), len(vat & every)), (604, 0))
        looks = [mapcells.column_look(self.img, column, 160, t) for v in vs for column in v]
        self.assertEqual((len(looks), looks.count(None)), (103, 0))
        self.assertEqual(len({w & ~0x7F for ws in t for w in ws}), 37)
        self.assertFalse(any(w & 0x7F for ws in t for w in ws))


@unittest.skipUnless(HAVE_DATA, "needs build/extracted, build/ram and level 1's joint palette (make msx)")
class Level2ConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "level2"
        common = ["--pal-file", MAIN, "--rows", "50"]
        cls.pal = run(ROOT / "tools" / "msxlvpal.py", "palette", DATAL2, *common, "--base-addr", "0xfff6",
                      "--pal-addr", "0x10036", "--base", JOINT, "-o", cls.out)
        cls.conv = run(ROOT / "tools" / "msxconv.py", "level", DATAL2, *common, "--pal-addr", "0x10036",
                       "--joint", cls.out, "-o", cls.out)
        cls.cells = run(ROOT / "tools" / "mapcells.py", L2_RAM, TSV, cls.out.with_suffix(".atrp"), "160", "50", "--level", "2")
        cls.prev = run(ROOT / "tools" / "msxlvpal.py", "preview", DATAL2, *common, "--pal-addr", "0x10036",
                       "--level", cls.out, "-o", Path(cls.tmp.name) / "level2_amiga_vs_msx.png")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_palette_c(self):
        self.assertEqual(self.pal.returncode, 0, self.pal.stderr)
        c = msxlvpal.read_pal(self.out.with_suffix(".pal").read_bytes())
        self.assertEqual(" ".join(msxlvpal.name(e) for e in c), PALETTE_C)
        self.assertEqual(c[:8], msxlvpal.read_pal(JOINT.with_suffix(".pal").read_bytes())[:8])
        self.assertEqual(self.out.with_suffix(".remap").read_bytes(), JOINT.with_suffix(".remap").read_bytes())
        m = re.search(r"mean dE76 over the map's pixels: C ([\d.]+), A ([\d.]+) ", self.pal.stdout)
        self.assertEqual((m.group(1), m.group(2)), ("2.417", "2.501"))

    def test_the_rule_gives_level_1_its_own_palette(self):
        code = MAIN.read_bytes()
        l1 = msxlvpal.amiga_colours(code, 0x8000, 0xFFF6)
        base = msxlvpal.read_pal(JOINT.with_suffix(".pal").read_bytes())
        self.assertEqual(msxlvpal.palette_c(base, list(JOINT.with_suffix(".remap").read_bytes()), l1, l1)[0], base)
        # RoboCop's colours (COLOR16-31) are level 1's in level 2 (what keeps entries 0-7 right)
        self.assertEqual(code[0xFFF6 - 0x8000 + 30:0xFFF6 - 0x8000 + 62], code[0x10036 - 0x8000 + 30:0x10036 - 0x8000 + 62])

    def test_outputs_sizes_and_tiles(self):
        self.assertEqual(self.conv.returncode, 0, self.conv.stderr)
        sizes = {e: self.out.with_suffix(e).stat().st_size for e in (".map", ".atrp", ".otile", ".atr2", ".til", ".pal")}
        self.assertEqual(sizes, {".map": 16000, ".atrp": 4016, ".otile": 1024, ".atr2": 320, ".til": 65408, ".pal": 32})
        self.assertEqual(sizes[".til"] // 128, 511)
        self.assertEqual(self.out.with_suffix(".pal").read_bytes(), msxlvpal.pal_bytes(pal(PALETTE_C)))
        otile = struct.unpack("<512H", self.out.with_suffix(".otile").read_bytes())
        self.assertEqual(max(otile), 510)
        # the packed attributes: the map's 8 values, then 8 free codes
        self.assertEqual(self.out.with_suffix(".atrp").read_bytes()[-16:], bytes([0, 1, 2, 3, 8, 9, 0xB, 0xD]) + b"\xff" * 8)

    def test_map_writers_and_vats_fit(self):
        self.assertEqual(self.cells.returncode, 0, self.cells.stderr)
        self.assertIn("level 2: 289 cells the writers can change (146 in even rows, 143 in odd ones; 255 a pool)",
                      self.cells.stdout)
        self.assertIn("7 vats, 604 cells in 103 columns (outside the pools), 37 tile offsets", self.cells.stdout)

    def test_every_cell_is_the_original_through_the_remap(self):
        self.assertEqual(self.prev.returncode, 0, self.prev.stderr)
        self.assertIn("0 cells differ from the remap", self.prev.stdout)
        png = Path(self.tmp.name) / "level2_amiga_vs_msx.png"
        self.assertEqual(struct.unpack(">II", png.read_bytes()[16:24]), (2560, 1608))


if __name__ == "__main__":
    unittest.main()
