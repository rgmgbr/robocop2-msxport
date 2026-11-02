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


if __name__ == "__main__":
    unittest.main()
