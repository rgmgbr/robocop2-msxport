"""Level 3's sprites and play field (docs/LEVEL3.md step C, its 3.5-3.6): tools/bobcatalog.py's level-3
tables, tools/msxsprites.py's level-3 pool (its first play-field id, its frame cache: the header, the
places, the white copies), tools/mkrom.py's late blocks (place_banks) and level 3's BOBHASH, and the
engine's sources (msx/field.asm's per-level tables and frame cache, msx/bob.asm's lv_fid0)."""
from __future__ import annotations

import json
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import bobcatalog  # noqa: E402
import mkrom  # noqa: E402

POOL = ROOT / "build" / "msx" / "sprites"          # the global sprite pool (make msx)
L3 = POOL.with_name("sprites_l3.json")
FC = POOL.with_name("sprites_l3_fc.bin")
INC = POOL.with_name("sprites_l3_field.inc")


def asm(name: str) -> str:
    return (ROOT / "msx" / name).read_text()


class CatalogueTests(unittest.TestCase):
    def test_the_level3_tables(self):
        names = {r[0] for r in bobcatalog.L3_HARD}
        for t in ("obj21_update", "obj22_update", "obj33_update", "obj34_update", "obj35_update", "obj36_update",
                  "obj37_update", "obj38_update", "obj39_update", "obj50_update", "obj51_update", "obj52_update",
                  "FUN_00008de6", "obj04_update", "obj12_update"):
            self.assertIn(t, names)
        self.assertEqual(bobcatalog.L3_EXPL, (0, 1, 4, 6, 7))
        self.assertNotIn(1, bobcatalog.L3_BULLETS)          # (types 1, 2, 4, 7, 8, 15h: other levels')
        self.assertIn(0x11, bobcatalog.L3_BULLETS)          # (the rocket)


@unittest.skipUnless(L3.exists() and FC.exists() and INC.exists(), "needs make msx (the pool with level 3)")
class PoolTests(unittest.TestCase):
    def setUp(self):
        self.l3 = json.loads(L3.read_text())
        self.fc = FC.read_bytes()
        self.inc = {m[1]: int(m[2], 0) for m in re.finditer(r"^(\w+): equ (0x[0-9A-Fa-f]+|\d+)\b", INC.read_text(), re.M)}

    def test_the_ids(self):
        fid0 = self.l3["field_id0"]
        self.assertEqual(fid0 % 8, 0)
        self.assertGreaterEqual(fid0, len(self.l3["bobs"]))
        self.assertLessEqual(fid0 + len(self.l3["field"]), mkrom.HIDDEN_ID)
        self.assertEqual(self.inc["FIELD_ID0"], fid0)

    def test_the_kinds_in_their_order(self):
        kinds = [f["kind"] for f in self.l3["field"]]
        self.assertEqual(kinds, sorted(kinds))              # static, cache, smoke, the lift's parts
        late = [f["fid"] for f in self.l3["field"] if f["kind"] == 3]
        self.assertEqual(self.inc["FIELD_LATE"], min(late))
        dyn = [f["fid"] for f in self.l3["field"] if "dyn" in f]
        self.assertEqual((self.inc["FIELD_DYN0"], self.inc["FIELD_DYN1"]), (dyn[0], dyn[-1] + 1))
        for f in self.l3["field"]:
            self.assertTrue(f["w"] >= 48 or "FUN_00008de6" in f["procs"], f)

    def test_the_cache(self):
        places = self.l3["fc_places"]
        self.assertLessEqual(len(places), 8)
        n, m = len(self.l3["field"]), len(self.l3["fc"])
        ent, plc = self.inc["FC_ENT"] - 0x8000, self.inc["FC_PLC"] - 0x8000
        self.assertEqual((ent, plc), (2 * n, 2 * n + 4 * m))
        for k, (x, y, w, h) in enumerate(places):          # (page 2: after the tile slots, before the
            self.assertTrue(160 <= y and y + h <= 232 and x + w <= 256)     # explosions' slot)
            px, py, over = self.fc[plc + 3 * k:plc + 3 * k + 3]
            self.assertEqual((px, py), (x, y))
            for q, (qx, qy, qw, qh) in enumerate(places):
                meet = q != k and qx < x + w and x < qx + qw and qy < y + h and y < qy + qh
                self.assertEqual(bool(over >> q & 1), meet, (k, q))
        by_fid = {f["fid"]: f for f in self.l3["field"]}
        for fid, f in by_fid.items():
            normal, white = self.fc[2 * fid], self.fc[2 * fid + 1]
            self.assertEqual(normal != 0xFF, f["kind"] == 1 or (f["look"] != fid and by_fid[f["look"]]["kind"] == 1))
            for c in (normal, white):
                if c == 0xFF:
                    continue
                bank, addr, pl = struct.unpack_from("<BHB", self.fc, ent + 4 * c)
                o = bank * 0x2000 + addr - 0x8000
                size = f["sw"] // 2 * f["sh"]
                self.assertTrue(0x8000 <= addr and (addr - 0x8000) + size <= 0x2000 and o + size <= len(self.fc))
                x, y, w, h = places[pl]
                self.assertTrue(f["sw"] <= w and f["sh"] <= h)
        whites = [c for c in self.l3["fc"] if c["white"]]
        self.assertTrue(whites)
        for c in whites:                                    # (one colour where the frame has pixels)
            j = self.l3["fc"].index(c)
            bank, addr, _pl = struct.unpack_from("<BHB", self.fc, ent + 4 * j)
            o = bank * 0x2000 + addr - 0x8000
            px = {v for b in self.fc[o:o + c["w"] // 2 * c["h"]] for v in (b >> 4, b & 15)}
            self.assertEqual(px - {0}, {self.l3["flash"]})


class LateBlocksTests(unittest.TestCase):
    def test_place_banks_keeps_the_3fh_banks_for_a000h_code(self):
        at, pads, end = mkrom.place_banks(124, ["FRONT2", "L3", "L3B"],
                                          [("tv2", 4), ("end", 4), ("tiles", 8), ("map", 2), ("atr", 1), ("tab", 1),
                                           ("atlas", 2), ("fc", 14)])
        self.assertEqual(at["FRONT2"], 127)
        self.assertEqual(pads, [])
        data = {k: v for k, v in at.items() if k not in ("FRONT2", "L3", "L3B")}
        sizes = {"tv2": 4, "end": 4, "tiles": 8, "map": 2, "atr": 1, "tab": 1, "atlas": 2, "fc": 14}
        for k, b in data.items():
            self.assertFalse(any(x & 0x3F == 0x3F for x in range(b, b + sizes[k])), k)
        self.assertEqual(end, 124 + sum(sizes.values()) + 3)

    def test_level3_bobhash(self):
        l3 = {"field_id0": 0x98, "bobs": [{"addr": 0x3BFC0 + 2 * k, "w": 32, "h": 16, "id": k} for k in range(3)],
              "field": [{"addr": 0x41000, "w": 48, "h": 44, "fid": 0}]}
        t = mkrom.l3_hash(l3, {})
        ids = {t[8 * s + 5] for s in range(len(t) // 8)} - {0xFF}
        self.assertEqual(ids, {0, 1, 2, 0x98})
        t = mkrom.l3_hash(l3, {}, field=False)              # (VAT_ANIM=1 builds: no play-field frame)
        self.assertEqual({t[8 * s + 5] for s in range(len(t) // 8)} - {0xFF}, {0, 1, 2})


class EngineSourceTests(unittest.TestCase):
    def test_the_levels_tables(self):
        f = asm("field.asm")
        for lv in ("fld_l1", "fld_l2"):
            i = f.index(lv + ":")
            self.assertTrue(f[i:i + 200].split("\n")[1].strip().endswith(", field_dyn"), lv)
        self.assertIn("db 0x80, L3_FC", f)
        self.assertIn("ld hl,(fb_fdyt)", f)                 # (fb_dyn: the level's field_dyn)
        self.assertNotIn("ld hl,field_dyn", f)

    def test_bob_reads_lv_fid0(self):
        b = asm("bob.asm")
        self.assertNotIn("FIELD_ID0", re.sub(r";.*", "", b))
        self.assertEqual(len(re.findall(r"ld hl,lv_fid0", b)), 2)
        self.assertIn("set 7,c", b)                         # (fb_add: a hit flash's mark)


if __name__ == "__main__":
    unittest.main()
