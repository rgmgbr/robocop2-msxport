"""rc-edge (performance campaign 2, batch 3; docs/MSX_ARCHITECTURE.md "The cadence"): RoboCop's reach, the table
tools/mkrom.py rcedge writes into gen/rcedge.inc for msx/plmove.asm rc_bound, against the sprite pool.

- SpriteData.opaque_x (no numpy: the build's) gives every composition RoboCop uses (his records' four aims and
  the start-of-level arm poses) the same leftmost and rightmost opaque column as record()'s full looks (numpy:
  the project's venv; skipped without it).
- Each state's reach holds, with the record's hotspot, every opaque column of the compositions of its records and
  of the first records any state starts with within the ticks (the animation counter from 0, the record its half),
  and no more; a frame of 3 ticks reaches the second records too; the largest x step is pl_xstep's.
- The include assembles as signed bytes, one pair a state, in pl_rec0's order.

Needs the conversions (build/msx: the pool sprites.bin / .inc and player.inc); skipped without them."""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import mkrom  # noqa: E402
import msxsprites  # noqa: E402

MSX = ROOT / "build" / "msx"
POOL = MSX / mkrom.POOL
HAVE = POOL.with_suffix(".bin").exists() and POOL.with_suffix(".inc").exists() and (MSX / "player.inc").exists()
HAVE_NUMPY = importlib.util.find_spec("numpy") is not None


@unittest.skipUnless(HAVE, "make msx's conversions missing (build/msx)")
class RcEdgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sd = msxsprites.SpriteData(POOL.with_suffix(".bin"), POOL.with_suffix(".inc"))
        cls.sinc = mkrom.equates(POOL.with_suffix(".inc"))
        cls.text = (MSX / "player.inc").read_text()
        cls.pl = mkrom.equates(MSX / "player.inc")
        cls.hot = mkrom.inc_table(cls.text, "pl_hot")[0::2]
        cls.rec0 = mkrom.inc_table(cls.text, "pl_rec0")
        cls.nrec = mkrom.inc_table(cls.text, "pl_nrec")
        cls.ids = list(range(4 * len(cls.hot))) + list(range(cls.sinc["SPR_RC_ARM"],
                                                             cls.sinc["SPR_RC_ARM"] + cls.sinc["SPR_RC_ARMS"]))

    def rel(self, r):
        """record r's compositions' opaque columns, with its hotspot (the arm poses with theirs)"""
        ids = [4 * r + a for a in range(4)]
        if r == self.pl["PL_ARM_REC"]:
            ids += list(range(self.sinc["SPR_RC_ARM"], self.sinc["SPR_RC_ARM"] + self.sinc["SPR_RC_ARMS"]))
        cols = [self.sd.opaque_x(self.sd.entry(i)) for i in ids]
        return [(self.hot[r] + lo, self.hot[r] + hi) for lo, hi in cols]

    def test_every_composition_has_opaque_columns_inside_its_header(self):
        for i in self.ids:
            o = self.sd.entry(i)
            ext = self.sd.opaque_x(o)
            self.assertIsNotNone(ext, i)
            mindx, maxdx = self.sd.record(o)["header"][3:5] if HAVE_NUMPY else \
                __import__("struct").unpack_from("<bb", self.sd.data, o + 3)
            self.assertGreaterEqual(ext[0], mindx, i)
            self.assertLessEqual(ext[1], maxdx + 15, i)

    @unittest.skipUnless(HAVE_NUMPY, "numpy missing: run with the project's venv")
    def test_opaque_x_equals_the_pools_full_looks(self):
        for i in self.ids:
            lo = hi = None
            for _dy, boxes in self.sd.record(self.sd.entry(i))["layout"]:
                for b in boxes:
                    cols = [x for x in range(16) if b["full"][:, x].any()]
                    if cols:
                        lo = b["x"] + cols[0] if lo is None else min(lo, b["x"] + cols[0])
                        hi = b["x"] + cols[-1] if hi is None else max(hi, b["x"] + cols[-1])
            self.assertEqual(self.sd.opaque_x(self.sd.entry(i)), (lo, hi), i)

    def test_the_reach_of_each_state(self):
        for ticks in (1, 2, 3, 4):
            rc = mkrom.rcedge(POOL, MSX / "player.inc", ticks)
            self.assertEqual(rc["vx"], max(abs(v) for v in mkrom.inc_table(self.text, "pl_xstep")))
            first = [r for s0, n in zip(self.rec0, self.nrec) for r in range(s0, s0 + min((ticks - 1) // 2, n - 1) + 1)]
            self.assertEqual(len(rc["reach"]), len(self.rec0))
            for s, (s0, n) in enumerate(zip(self.rec0, self.nrec)):
                cols = [c for r in list(range(s0, s0 + n)) + first for c in self.rel(r)]
                self.assertEqual(rc["reach"][s], (min(c[0] for c in cols), max(c[1] for c in cols)), (ticks, s))

    def test_the_punch_and_the_walk(self):
        # walking right (state 0), the punch (state 6, composition 82: record 20) can start within a frame: its
        # opaque columns reach past every walk record's; in the punch the later records (22-24) reach further
        rc = mkrom.rcedge(POOL, MSX / "player.inc", 2)
        walk = max(c[1] for r in range(self.rec0[0], self.rec0[0] + self.nrec[0]) for c in self.rel(r))
        punch = max(c[1] for c in self.rel(self.rec0[6]))
        self.assertGreater(punch, walk)
        self.assertEqual(rc["reach"][0][1], punch)
        self.assertGreater(rc["reach"][6][1], punch)

    def test_the_include(self):
        rc = mkrom.rcedge(POOL, MSX / "player.inc", 2)
        inc = mkrom.rcedge_inc(rc)
        self.assertIn("RC_K: equ 2", inc)
        self.assertIn(f"RC_STATES: equ {len(self.rec0)}", inc)
        rows = re.findall(r"^\s+db (-?\d+), (-?\d+)", inc, re.M)
        self.assertEqual([(int(a), int(b)) for a, b in rows], rc["reach"])
        self.assertTrue(all(-128 <= int(v) <= 127 for row in rows for v in row))


def asm_equ(text: str, name: str) -> int:
    m = re.search(rf"^{name}:\s+equ\s+(\S+)", text, re.M)
    if not m:
        raise AssertionError(f"no {name}")
    return int(m.group(1), 0)


class RcMoversTests(unittest.TestCase):
    """rc_bound's growth covers the logic's other moves of his x within a tick (msx/plmove.asm rc_step, rc_snap): the
    constants against the code that moves him and against the levels' data."""

    @classmethod
    def setUpClass(cls):
        cls.plmove = (ROOT / "msx" / "plmove.asm").read_text()
        cls.special = (ROOT / "msx" / "special.asm").read_text()

    def test_the_mounts_entries(self):
        # special.asm's entries of the lifts table (sp_entry's width): the trolley's and the vehicle's snap his x,
        # the lift's moves him in y only; rc_snap tells them apart by these widths
        widths = {int(w, 0) for w in re.findall(r"ld hl,(0x[0-9A-Fa-f]+)\n\s+call sp_entry", self.special)}
        self.assertEqual(widths, {0x10, 0x30, 0x36})
        body = self.plmove[self.plmove.index("rc_snap:"):]
        self.assertIn("cp 0x10", body)
        self.assertIn("cp 0x36", body)
        self.assertIn("ld (p_x),hl                 ; ($15D0 = D0)", self.special)    # (the trolley: his x its left)
        self.assertRegex(self.special, r"spv_ride:\n\s+ld hl,\(sp_x\)\n\s+ld de,0x12\n")  # (the vehicle: left + 12h)

    @unittest.skipUnless((ROOT / "build" / "ram" / "level1_full.bin").exists(), "level 1's RAM image missing (make ram)")
    def test_the_conveyors(self):
        # mapobj.asm act_cv carries him 4 px a tick per conveyor entry he stands on; entries at one place add up
        mo = (ROOT / "msx" / "mapobj.asm").read_text()
        cv = mo[mo.index("act_cv:"):mo.index("acv_ph:")]
        carry = max(abs(int(v, 0)) for v in re.findall(r"ld de,(-?\d+)\n", cv[cv.index("ld (snd_b2d),a"):]))
        self.assertEqual(carry, 4)
        import mapcells
        import struct
        img = (ROOT / "build" / "ram" / "level1_full.bin").read_bytes()
        tabs = {r["label"]: r for r in mapcells.parse(ROOT / "analysis" / "amiga_tables.tsv")}
        types, a = tabs["obj_types"]["addr"], tabs["objl_l1"]["addr"]
        at = {}
        while struct.unpack_from(">h", img, a)[0] >= 0:
            t, _look, _hits, _value, x, y = mapcells.words(img, a, 6)
            if mapcells.words(img, types + 0x8A + (t & 0xFF), 1)[0] & 0xFF in (0x14, 0x18):
                at[(x, y)] = at.get((x, y), 0) + 1
            a += 12
        self.assertTrue(at)
        self.assertLessEqual(carry * max(at.values()), asm_equ(self.plmove, "RC_BELT"))


if __name__ == "__main__":
    unittest.main()
