"""Level 3's map writers in the port (performance campaign 2, logic-1 and logic-2): the beams' and turrets'
looks with their tiles looked up at build time (tools/mapcells.py look_tables: gen/tt_l3.inc and tt_l3b.inc,
which msx/level3.asm lt2_putt and msx/level3obj.asm tpu_w write through msx/tiles.asm map_write_t) against
map_write's own lookup of the original words, the columns those writers reach without map_write_lin's wrap
(l3_columns), the beam records the map-write cache holds (msx/msx.inc BM_N) and msx/tiles.asm rd_bit's index
without loops."""
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import amitab  # noqa: E402
import mapcells  # noqa: E402

TSV = ROOT / "analysis" / "amiga_tables.tsv"
L1_RAM = ROOT / "build" / "ram" / "level1_full.bin"   # make ram (tools/amitab.py's image: at_l3.inc, at_l3b.inc)
L3_RAM = ROOT / "build" / "ram" / "level3_full.bin"
L3_OTILE = ROOT / "build" / "msx" / "level3.otile"    # make msx (the level's offset table, OTILE in its tables bank)
# the original's tables the port's beams and turrets wrote through map_write_lin (analysis/amiga_tables.tsv),
# in the generated tables' order, and the off words of level_tick_2 ($9510: the top's two, then below)
LOOKS = {"tt_l3": (("lt2_top_t", "lt2_top"), ("lt2_left_t", "lt2_left"), ("lt2_right_t", "lt2_right")),
         "tt_l3b": (("tur_panel_t", "tur_panel"), ("tur40_look_t", "tur40_look"), ("tur41_look_t", "tur41_look"))}
OFF_WORDS = [0x1900, 0x1880, 0x1800, 0x1780]


def entries(text: str) -> dict:
    """A look_tables include -> {label: [(tile's low byte, high byte, attributes), ...]}."""
    out, cur = {}, None
    for line in text.splitlines():
        m = re.match(r"^(\w+):", line)
        if m:
            cur = out.setdefault(m.group(1), [])
            continue
        m = re.match(r"^\s+db 0x([0-9A-F]{2}), 0x([0-9A-F]{2}), 0x([0-9A-F]{2})\b", line)
        if m:
            cur.append(tuple(int(v, 16) for v in m.groups()))
    return out


def map_write_lookup(otile: bytes, w: int) -> tuple:
    """msx/tiles.asm map_write's lookup of map word w, as its code does it: L = H << 1 | bit 7 of L, H = bit 7
    of H (w >> 7), the tile the little-endian word at OTILE + 2 x that; the attributes w & 7Fh."""
    lo, hi = w & 0xFF, w >> 8
    i = ((hi << 1 | lo >> 7) & 0xFF) | (hi >> 7) << 8
    return otile[2 * i], otile[2 * i + 1], w & 0x7F


def table_words(img: bytes, row: dict) -> list:
    """The words of a table row (kinds w and l: a long is two words, the high one first) as the image holds
    them, read the way tools/amitab.py emits them for at_<bank>.inc."""
    n = row["count"] * (2 if row["kind"] == "l" else 1)
    return list(struct.unpack_from(f">{n}H", img, row["addr"]))


class LookTablesTests(unittest.TestCase):
    def setUp(self):
        self.tabs = {r["label"]: r for r in amitab.parse(TSV)}
        # an image whose tables hold distinct words over every offset and attribute, and an offset table
        # whose tiles are all different
        self.img = bytearray(0x10000)
        w = 0x0003
        for _, rows in LOOKS.items():
            for _, table in rows:
                r = self.tabs[table]
                for k in range(r["count"] * (2 if r["kind"] == "l" else 1)):
                    struct.pack_into(">H", self.img, r["addr"] + 2 * k, w)
                    w = (w + 0x2B95) & 0xFFFF
        self.otile = struct.pack("<512H", *((0x0100 + 7 * i) & 0x1FF for i in range(512)))

    def test_entries_are_map_writes_lookup_of_each_word(self):
        out = mapcells.look_tables(bytes(self.img), self.tabs, self.otile)
        self.assertEqual(sorted(out), ["tt_l3", "tt_l3b"])
        for inc, rows in LOOKS.items():
            got = entries(out[inc])
            for label, table in rows:
                ws = table_words(bytes(self.img), self.tabs[table])
                self.assertEqual(got[label], [map_write_lookup(self.otile, w) for w in ws], label)
        self.assertEqual(entries(out["tt_l3"])["lt2_off_t"], [map_write_lookup(self.otile, w) for w in OFF_WORDS])
        # sizes the port's offsets assume: lt2_top 4 longs, 16 + 16 body words, the panel 3 looks, type 40 five
        # looks (the wreck at 30h words = 48h bytes), type 41 four (24h words = 36h bytes): 3 bytes a word
        sizes = {k: len(v) for inc in out.values() for k, v in entries(inc).items()}
        self.assertEqual(sizes, {"lt2_top_t": 8, "lt2_left_t": 16, "lt2_right_t": 16, "lt2_off_t": 4, "tur_panel_t": 18,
                                 "tur40_look_t": 30, "tur41_look_t": 24})

    def test_lookup_model_is_the_word_shifted_by_seven(self):
        for w in (0x0000, 0x007F, 0x0080, 0x7F80, 0x8000, 0xFF80, 0xFFFF, 0x1234):
            i = w >> 7
            self.assertEqual(map_write_lookup(self.otile, w)[:2], (self.otile[2 * i], self.otile[2 * i + 1]))
            self.assertEqual(mapcells.word_tile(self.otile, w), self.otile[2 * i] | self.otile[2 * i + 1] << 8)

    def test_a_table_of_another_size_stops_the_build(self):
        tabs = dict(self.tabs)
        tabs["tur_panel"] = dict(tabs["tur_panel"], count=12)
        with self.assertRaises(SystemExit):
            mapcells.look_tables(bytes(self.img), tabs, self.otile)


class ColumnsTests(unittest.TestCase):
    def setUp(self):
        self.tabs = {"hz_l3": {"addr": 0x100}, "spawn_l3": {"addr": 0x200}}
        self.img = bytearray(0x400)
        struct.pack_into(">4Hh", self.img, 0x100, 416, 496, 0, 7, -1)                 # beam: column 18
        struct.pack_into(">hhB", self.img, 0x200, 832, 496, 40)                        # turret 40
        struct.pack_into(">h", self.img, 0x200 + 14, -1)

    def test_writers_columns_before_any_wrap(self):
        cols = mapcells.l3_columns(bytes(self.img), self.tabs)
        self.assertEqual(cols["beam 0"], [18, 19])
        # turret 40: the panel at (832 - A0h) >> 4 - 8 = 34, the turret 10 columns right
        self.assertEqual(cols["turret 0 (type 40)"], [34, 35, 44, 45])
        # a beam at the map's last column writes column 160 as its second cell (map_write_lin would wrap it)
        struct.pack_into(">H", self.img, 0x100, (159 + 8) * 16)
        self.assertEqual(mapcells.l3_columns(bytes(self.img), self.tabs)["beam 0"], [159, 160])
        # left of the map: a byte, F8h-FFh (map_write_lin: the row above's end)
        struct.pack_into(">H", self.img, 0x100, 4 * 16)
        self.assertEqual(mapcells.l3_columns(bytes(self.img), self.tabs)["beam 0"], [0xFC, 0xFD])


class RdBitTests(unittest.TestCase):
    def test_index_without_loops_equals_the_window_index(self):
        """msx/tiles.asm rd_bit: (row & 15) x 20 + column % 20 as byte i / 8, bit i & 7, for every row and
        every column 0-159 (map_write's), against its loop-free form: column % 20 by three compares, t = 4r +
        column % 20 with r = row & 15, byte 2r + (t rotated right three times & 1Fh), bit t & 7."""
        for row in range(256):
            for col in range(160):
                i = (row & 15) * 20 + col % 20
                c = col
                for k in (80, 40, 20):
                    if c >= k:
                        c -= k
                r = row & 15
                t = 4 * r + c
                rot = ((t >> 3) | (t << 5)) & 0xFF                 # rrca x 3 of the byte t
                self.assertLess(t, 80)
                self.assertEqual(((rot & 0x1F) + 2 * r, t & 7), (i >> 3, i & 7), (row, col))


@unittest.skipUnless(L3_RAM.exists() and L1_RAM.exists() and L3_OTILE.exists(),
                     "needs build/ram/level1_full.bin, level3_full.bin (make ram) and build/msx/level3.otile (make msx)")
class Level3DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tabs = {r["label"]: r for r in amitab.parse(TSV)}
        cls.img3 = L3_RAM.read_bytes()
        cls.img1 = L1_RAM.read_bytes()
        cls.otile = L3_OTILE.read_bytes()

    def test_generated_tables_equal_otiles_lookup_of_the_original_words(self):
        out = mapcells.look_tables(self.img3, self.tabs, self.otile)
        for inc, rows in LOOKS.items():
            got = entries(out[inc])
            for label, table in rows:
                # the words the port wrote before (at_l3.inc, at_l3b.inc: tools/amitab.py on level 1's image)
                # are the level-3 image's (the main code is the same in every level's image)
                ws = table_words(self.img1, self.tabs[table])
                self.assertEqual(ws, table_words(self.img3, self.tabs[table]), table)
                self.assertEqual(got[label], [map_write_lookup(self.otile, w) for w in ws], label)
        self.assertEqual(entries(out["tt_l3"])["lt2_off_t"], [map_write_lookup(self.otile, w) for w in OFF_WORDS])

    def test_writers_columns_never_wrap_and_the_beams_fit_the_cache(self):
        cols = mapcells.l3_columns(self.img3, self.tabs)
        beams = [k for k in cols if k.startswith("beam ")]
        self.assertEqual(len(beams), 7)
        self.assertLessEqual(len(beams), mapcells.BM_N)
        self.assertEqual(len(cols) - len(beams), 3)                    # (the turrets of types 41, 40, 42)
        every = [c for cs in cols.values() for c in cs]
        self.assertTrue(all(0 <= c < 160 for c in every), cols)
        self.assertEqual((min(every), max(every)), (18, 63))


if __name__ == "__main__":
    unittest.main()
