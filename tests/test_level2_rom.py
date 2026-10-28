"""Level 2 in the ROM (its plan's step 7): tools/mkrom.py's LV_TEST and LV_CARRY, level 2's BOBHASH of the
frames it shares with level 1, the harness's level-2 job tables (tools/bstest/hz.tcl hz_l2_jobs and
hz.sh compare --fields agree) and tools/bstest/l2stub.py's stubs against the main code."""
from __future__ import annotations

import json
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "bstest"))
import mkrom  # noqa: E402
import l2stub  # noqa: E402

RAM2 = ROOT / "build" / "ram" / "level2_full.bin"


class CarryTests(unittest.TestCase):
    def test_the_default_carry(self):
        self.assertEqual(mkrom.lv_carry(mkrom.LV_CARRY), {"LV_SCORE_H": 0x0001, "LV_SCORE_L": 0x0050,
                                                          "LV_LIVES": 2, "LV_CREDITS": 0, "LV_RATING": 1})

    def test_the_score_is_a_bcd_long(self):
        c = mkrom.lv_carry("12345678:0:1:3")
        self.assertEqual((c["LV_SCORE_H"], c["LV_SCORE_L"], c["LV_CREDITS"], c["LV_RATING"]), (0x1234, 0x5678, 1, 3))

    def test_bad_carries_are_refused(self):
        for bad in ("1:2:3", "1:2:3:4", "123456789:2:0:1", "1:x:0:1", "1:100:0:1", "-1:2:0:1"):
            with self.assertRaises(ValueError, msg=bad):
                mkrom.lv_carry(bad)

    def test_mkrom_refuses_lv_test_with_pz_test_and_a_carry_without_it(self):
        with tempfile.TemporaryDirectory() as t:
            out = str(Path(t) / "x.rom")
            for opts in (["LV_TEST=2", "PZ_TEST=1"], ["LV_TEST=1"], ["LV_CARRY=1:2:0:1"],
                         ["LV_TEST=2", "LV_CARRY=1:2:0:9"]):
                self.assertEqual(mkrom.main(["mkrom.py", "build/msx/level1", out] + opts), 2, opts)
            self.assertFalse(Path(out).exists())


class BobHashTests(unittest.TestCase):
    def frames(self) -> Path:
        d = {"bobs": [{"addr": 0x4B95A, "w": 32, "h": 47, "id": 0},          # SPERMA (shared)
                      {"addr": 0x3C4C0, "w": 48, "h": 24, "id": 1},          # DATAL1's own
                      {"addr": 0x45250, "w": 16, "h": 16, "id": 2},          # MADEX's first byte (shared)
                      {"addr": 0x4524F, "w": 16, "h": 16, "id": 3}],         # DATAL1's last own byte
             "field": [{"addr": 0x498DC, "w": 48, "h": 28, "fid": 0, "sil": 255},
                       {"addr": 0x30000, "w": 48, "h": 24, "fid": 1, "sil": 255}]}
        self.tmp = tempfile.TemporaryDirectory()
        p = Path(self.tmp.name) / "robocop.json"
        p.write_text(json.dumps(d))
        return p

    def tearDown(self):
        if hasattr(self, "tmp"):
            self.tmp.cleanup()

    def ids(self, table: bytes) -> set[int]:
        return {table[8 * k + 5] for k in range(len(table) // 8) if table[8 * k + 5] != 0xFF}

    def test_level_two_keeps_only_the_shared_frames_with_level_ones_ids(self):
        p = self.frames()
        self.assertEqual(self.ids(mkrom.bob_hash(p)), {0, 1, 2, 3, mkrom.FIELD_ID0, mkrom.FIELD_ID0 + 1})
        self.assertEqual(self.ids(mkrom.bob_hash(p, mkrom.shared_frame)), {0, 2, mkrom.FIELD_ID0})
        self.assertEqual(len(mkrom.bob_hash(p, mkrom.shared_frame)), len(mkrom.bob_hash(p)))


class HarnessTableTests(unittest.TestCase):
    def test_hz_tcl_and_hz_sh_list_the_same_jobs(self):
        tcl = (ROOT / "tools" / "bstest" / "hz.tcl").read_text()
        body = tcl[tcl.index("proc hz_l2_jobs"):tcl.index("proc hz_l2 {")]
        spec = re.findall(r"\b(\w+) (l2\w?) (l2_\w+) (\d+) ([\w-]+)", body)
        sh = (ROOT / "tools" / "bstest" / "hz.sh").read_text()
        jobs = re.search(r'JOBS="([^"]+)"', sh)[1].split()
        refs = {"l2s": "l2_trolley_sharp", "l2f": "l2_trolley_fair", "l2p": "l2_trolley_poor"}
        from_tcl = sorted(f"{n}:{b}:{refs.get(b, d)}:{rows}" for n, b, d, rows, _m in spec)
        self.assertEqual(len(spec), 20)
        self.assertEqual(from_tcl, sorted(jobs))

    def test_the_jobs_rows_are_the_references(self):
        import l2drives
        sh = (ROOT / "tools" / "bstest" / "hz.sh").read_text()
        for job in re.search(r'JOBS="([^"]+)"', sh)[1].split():
            _n, _b, ref, rows = job.split(":")
            self.assertEqual(l2drives.REFS[ref[3:]][3], int(rows), job)


@unittest.skipUnless(RAM2.exists(), "needs build/ram/level2_full.bin")
class StubTests(unittest.TestCase):
    def test_the_stubs_patch_the_routines_entries(self):
        img = RAM2.read_bytes()
        # every routine ported (step 9): no stub left
        self.assertEqual(l2stub.STUBS, {})
        # the type handlers the step-9 stubs patched (msx/level2obj.asm): obj_desc's record + 10 + its
        # handler offset (update_objects $C3E4)
        for t, entry in ((1, 0xC736), (2, 0xC868), (5, 0xD0E2), (6, 0xD1E2), (14, 0xCE0A), (16, 0xCD7A),
                         (49, 0xE6C0)):
            rec = 0xBEA6 + 16 * t
            self.assertEqual(rec + 10 + struct.unpack_from(">H", img, rec + 10)[0], entry, t)
        # the hazard dispatch's level-2 entry, the activators' 0Ch entry, the special handlers' 4
        self.assertEqual(img[0x91B4:0x91B6], b"\x60\x00")
        self.assertEqual(0x91B6 + struct.unpack_from(">h", img, 0x91B6)[0], 0x91BC)
        self.assertEqual(0x9ED2 + struct.unpack_from(">h", img, 0x9ED2)[0], 0x9EE8)
        self.assertEqual(0x9EC6 + struct.unpack_from(">h", img, 0x9EC6)[0], 0x9C76)       # activator 0
        # the branches the stubs write: level_tick_1's own end and activator 0's default
        self.assertEqual(0x91BE + (0xFFE0 - 0x10000), 0x919E)
        self.assertEqual(0x9EEA + (0xFD8C - 0x10000), 0x9C76)
        self.assertEqual(img[0x9276:0x927A], b"\x60\x00\xff\x26")                        # bra.w $919E
        self.assertEqual(0x9278 + (0xFF26 - 0x10000), 0x919E)


if __name__ == "__main__":
    unittest.main()
