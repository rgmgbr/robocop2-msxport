"""Level 2 in the ROM (its plan's steps 7, 12 and 13): tools/mkrom.py's LV_TEST and LV_CARRY, the BOBHASH
tables (the slots, level 2's from the global sprite pool with its own play-field frames and their
silhouettes, the hidden frames, the lines a joint composition reaches above its place), level 2's atlas
in banks of their own tables (atlas_banks), its play-field tables beside level 1's (field_inc), the
vats' display tables (tools/mapcells.py vat_tables), the harness's level-2 job tables
(tools/bstest/hz.tcl hz_l2_jobs and hz.sh compare --fields agree), tools/bstest/l2stub.py's stubs
against the main code, and CHEAT (step 21)."""
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
POOL = ROOT / "build" / "msx" / "sprites"          # the global sprite pool (make msx)


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

    def test_the_shared_frames_filter_keeps_level_ones_ids(self):
        p = self.frames()
        self.assertEqual(mkrom.FIELD_ID0, 0xD0)
        self.assertEqual(self.ids(mkrom.bob_hash(p)), {0, 1, 2, 3, mkrom.FIELD_ID0, mkrom.FIELD_ID0 + 1})
        self.assertEqual(self.ids(mkrom.bob_hash(p, mkrom.shared_frame)), {0, 2, mkrom.FIELD_ID0})
        self.assertEqual(len(mkrom.bob_hash(p, mkrom.shared_frame)), len(mkrom.bob_hash(p)))

    def slot(self, table: bytes, addr: int, w: int, h: int) -> bytes:
        d4 = (h << 6) | (w // 16 + 1)
        key = bytes([addr & 0xFF, addr >> 8 & 0xFF, addr >> 16, d4 & 0xFF, d4 >> 8])
        return next(table[8 * k:8 * k + 8] for k in range(len(table) // 8) if table[8 * k:8 * k + 5] == key)

    def test_a_slot_holds_the_id_the_silhouette_and_the_lines_above(self):
        t = mkrom.hash_table([{"addr": 0x3E810, "w": 32, "h": 23, "id": 3, "above": 21},
                              {"addr": 0x498DC, "w": 48, "h": 28, "id": 0xD0, "sil": 19}])
        self.assertEqual(self.slot(t, 0x3E810, 32, 23)[5:], bytes([3, 0xFF, 21]))
        self.assertEqual(self.slot(t, 0x498DC, 48, 28)[5:], bytes([0xD0, 19, 0]))
        with self.assertRaises(SystemExit):
            mkrom.hash_table([{"addr": 0x3E810, "w": 32, "h": 23, "id": 3}] * 2)

    def test_level_two_its_sprite_frames_the_hidden_ones_and_its_own_play_field(self):
        l2 = {"bobs": [{"addr": 0x3E810, "w": 32, "h": 23, "id": 3},
                       {"addr": 0x4B4AC, "w": 16, "h": 16, "id": 7},
                       {"addr": 0x3D280, "w": 48, "h": 56, "id": 109, "field": 9},               # a silhouette
                       {"addr": 0x6D020, "w": 16, "h": 16, "id": 200, "spark": True}],
              "field": [{"addr": 0x498DC, "w": 48, "h": 28, "fid": 0, "sil": 255},              # the hostage
                        {"addr": 0x3D280, "w": 48, "h": 56, "fid": 9, "sil": 109},              # type 2
                        {"addr": 0x4B95A, "w": 32, "h": 47, "fid": 34, "sil": 255}],            # the trolley
              "hidden": [{"addr": 0x404D0, "w": 32, "h": 21}]}
        t = mkrom.l2_hash(l2, {3: 21})
        self.assertEqual(self.ids(t), {3, 7, mkrom.HIDDEN_ID, mkrom.FIELD_ID0, mkrom.FIELD_ID0 + 9,
                                       mkrom.FIELD_ID0 + 34})
        self.assertEqual(self.slot(t, 0x3E810, 32, 23)[5:], bytes([3, 0xFF, 21]))
        self.assertEqual(self.slot(t, 0x404D0, 32, 21)[5:], bytes([mkrom.HIDDEN_ID, 0xFF, 0]))
        self.assertEqual(self.slot(t, 0x498DC, 48, 28)[5:], bytes([mkrom.FIELD_ID0, 0xFF, 0]))
        self.assertEqual(self.slot(t, 0x3D280, 48, 56)[5:], bytes([mkrom.FIELD_ID0 + 9, 109, 0]))   # (its blink)
        self.assertEqual(self.slot(t, 0x4B95A, 32, 47)[5:], bytes([mkrom.FIELD_ID0 + 34, 0xFF, 0]))


class AtlasTests(unittest.TestCase):
    @staticmethod
    def atlas(frames: list[tuple[int, int, int, int, int]]) -> bytes:
        """msxsprites.py's layout: (y, x / 2, bytes a line, lines, the mirrored frame's index or -1)."""
        head, pix, at = 1 + 7 * len(frames), b"", []
        for k, (y, x2, bpl, h, m) in enumerate(frames):
            if m < 0:
                at.append(head + len(pix))
                pix += bytes((k * 16 + i) & 0xFF for i in range(bpl * h))
            else:
                at.append(at[m])
        return bytes([len(frames)]) + b"".join(struct.pack("<BBBBBH", y, x2, bpl, h, int(m >= 0), at[k])
                                              for k, (y, x2, bpl, h, m) in enumerate(frames)) + pix

    @staticmethod
    def flat(rom: bytes) -> list[tuple]:
        """msxsprites.py's layout decoded: every frame's place, size, mirror flag and pixels."""
        out = []
        for i in range(rom[0]):
            y, x2, bpl, h, m, off = struct.unpack_from("<BBBBBH", rom, 1 + 7 * i)
            out.append((y, x2, bpl, h, m, rom[off:off + bpl * h]))
        return out

    @staticmethod
    def decoded(rom: bytes) -> list[tuple]:
        """Every frame field_upload writes (msx/field.asm), bank by bank."""
        out, b = [], 0
        while True:
            bank = rom[b * mkrom.BANK:(b + 1) * mkrom.BANK]
            for i in range(bank[0] & 0x7F):
                y, x2, bpl, h, m, off = struct.unpack_from("<BBBBBH", bank, 1 + 7 * i)
                out.append((y, x2, bpl, h, m, bank[off:off + bpl * h]))
            if not bank[0] & 0x80:
                return out
            b += 1

    def test_an_atlas_of_one_bank_is_kept_byte_for_byte(self):
        rom = self.atlas([(0, 0, 24, 40, -1), (0, 24, 24, 40, 0), (40, 0, 16, 28, -1)])
        self.assertEqual(mkrom.atlas_banks(rom), rom)

    def test_a_larger_atlas_is_cut_into_banks_of_their_own_tables(self):
        frames = [(0, 24 * k % 128, 24, 56, -1) for k in range(6)] + [(56, 0, 24, 56, 0)] \
            + [(112, 0, 24, 36, -1)]
        rom = self.atlas(frames)
        self.assertGreater(len(rom), mkrom.BANK)
        cut = mkrom.atlas_banks(rom)
        self.assertEqual(len(cut) % mkrom.BANK, 0)
        self.assertEqual(cut[0] & 0x80, 0x80)
        self.assertEqual(self.decoded(cut), self.flat(rom))

    def test_a_mirror_whose_frame_is_in_another_bank_gets_its_pixels(self):
        frames = [(0, 24 * k % 128, 24, 60, -1) for k in range(6)] + [(60, 0, 24, 60, 0)]
        rom = self.atlas(frames)
        cut = mkrom.atlas_banks(rom)
        self.assertEqual(cut[mkrom.BANK], 2)                            # (frame 5 and the mirror of 0)
        self.assertEqual(self.decoded(cut), self.flat(rom))


class FieldIncTests(unittest.TestCase):
    L1 = ("FIELD_N: equ 2\nFIELD_LATE: equ 1\nfield_tab:\n        db 0, 0, 48, 28, 0, 0\nfield_look:\n"
          "        db 0\nfield_dyn:\n        db 0\ndyn_tab:\n        dw 0x0001, 0x0000\n")

    def test_level_twos_tables_get_their_names_and_level_ones_dynamic_tables(self):
        l2 = self.L1.replace("FIELD_N: equ 2", "FIELD_N: equ 3")
        out = mkrom.field_inc(self.L1, l2, "l2")
        self.assertIn("FIELD_N_l2: equ 3", out)
        self.assertIn("field_tab_l2:", out)
        self.assertIn("field_look_l2:", out)
        self.assertNotIn("field_dyn", out)
        self.assertNotIn("dyn_tab", out)

    def test_other_dynamic_frames_are_refused(self):
        with self.assertRaises(SystemExit):
            mkrom.field_inc(self.L1, self.L1.replace("0x0001, 0x0000", "0x0001, 0x0002"), "l2")


@unittest.skipUnless(RAM2.exists() and (ROOT / "build/msx/level2.otile").exists(), "needs level 2's conversions")
class VatTableTests(unittest.TestCase):
    def test_the_vats_rows_columns_and_static_looks(self):
        import mapcells
        from amitab import parse
        img = RAM2.read_bytes()
        tabs = {r["label"]: r for r in parse(ROOT / "analysis/amiga_tables.tsv")}
        otile = (ROOT / "build/msx/level2.otile").read_bytes()
        table, looks = mapcells.vat_tables(img, tabs, "l2", 160, 50, otile)
        self.assertEqual(len(table), mapcells.VAT_SIZE)
        vs, t = mapcells.vats(img, tabs, "l2", 160, 50)
        self.assertEqual(len(looks), sum(len(v) for v in vs))
        self.assertEqual(len(looks), 103)                       # (msx/msx.inc vat_shown)
        first = 0
        for v, columns in enumerate(vs):
            c0, n, r0, rows, k = table[mapcells.VAT_RECS + 8 * v:mapcells.VAT_RECS + 8 * v + 5]
            self.assertEqual((r0, c0), columns[0][0])
            self.assertEqual((n, rows, k), (len(columns), len(columns[0]), first))
            for r in range(r0, r0 + rows):
                self.assertTrue(table[r] >> v & 1)
            first += n
        self.assertEqual(sum(bin(b).count("1") for b in table[:mapcells.VAT_ROWS]),
                         sum(len(v[0]) for v in vs))
        for k, w in enumerate(t[1]):                             # T1[d]'s tile: the sheet's at the word
            self.assertEqual(struct.unpack_from("<H", table, mapcells.VAT_TILES + 32 + 2 * k)[0],
                             struct.unpack_from("<H", otile, 2 * (w >> 7))[0])

    @unittest.skipUnless(POOL.with_suffix(".bin").exists(), "needs build/msx/sprites.bin (make msx)")
    def test_only_level_twos_joint_compositions_reach_above_their_place(self):
        blob = POOL.with_suffix(".bin").read_bytes()
        inc = mkrom.equates(POOL.with_suffix(".inc"))
        l1 = json.loads((ROOT / "build/msx/sprites_l1.json").read_text())
        l2 = json.loads((ROOT / "build/msx/sprites_l2.json").read_text())
        self.assertEqual(mkrom.pool_above(blob, inc, 1, l1), {})
        above = mkrom.pool_above(blob, inc, 2, l2)
        joints = {f["id"] for f in l2["bobs"] if f.get("joint")}
        self.assertEqual(set(above), joints)
        self.assertEqual(len(joints), 16)
        self.assertEqual(set(above.values()), {20, 21})


class HarnessTableTests(unittest.TestCase):
    def test_hz_tcl_and_hz_sh_list_the_same_jobs(self):
        tcl = (ROOT / "tools" / "bstest" / "hz.tcl").read_text()
        body = tcl[tcl.index("proc hz_l2_jobs"):tcl.index("proc hz_l2 {")]
        spec = re.findall(r"\b(\w+) (l2\w?) (l2_\w+) (\d+) ([\w-]+)", body)
        sh = (ROOT / "tools" / "bstest" / "hz.sh").read_text()
        jobs = re.search(r'JOBS="([^"]+)"', sh)[1].split()
        refs = {"l2s": "l2_trolley_sharp", "l2f": "l2_trolley_fair", "l2p": "l2_trolley_poor"}
        from_tcl = [f"{n}:{b}:{refs.get(b, d)}:{rows}" for n, b, d, rows, _m in spec]
        # (level 2's step 18: the product's way into level 2 on the flow build, its own set-up)
        flow = re.search(r'\[list l2_(flow_\w+) [\w-]+ \[list hz_l2_flow_setup "\$R/(\w+)/rc2_\w+\.rom".*?\.txt" (\d+) ',
                         body, re.S)
        self.assertIsNotNone(flow)
        from_tcl.append(f"{flow[1]}:{flow[2]}:l2_{flow[1]}:{flow[3]}")
        self.assertEqual(len(spec), 22)
        self.assertEqual(sorted(from_tcl), sorted(jobs))

    def test_the_jobs_rows_are_the_references(self):
        import l2drives
        sh = (ROOT / "tools" / "bstest" / "hz.sh").read_text()
        for job in re.search(r'JOBS="([^"]+)"', sh)[1].split():
            _n, _b, ref, rows = job.split(":")
            self.assertEqual(l2drives.REFS[ref[3:]][3], int(rows), job)


class CheatTests(unittest.TestCase):
    """CHEAT=1 (level 2's step 21): the original's cheat mode at each new game and its keys on F5/F4;
    its code only in CHEAT builds, none in the fixed area."""

    def test_mkrom_refuses_a_bad_cheat_and_cheat_with_diag(self):
        with tempfile.TemporaryDirectory() as t:
            out = str(Path(t) / "x.rom")
            for opts in (["CHEAT=2"], ["CHEAT=1", "DIAG=1"], ["CHEAT=1", "DIAG=2"]):
                self.assertEqual(mkrom.main(["mkrom.py", "build/msx/level1", out] + opts), 2, opts)
            self.assertFalse(Path(out).exists())

    @staticmethod
    def blocks(path):
        """The lines between "if CHEAT" and its endif in an asm file (no nesting there)."""
        out, inside = [], False
        for line in (ROOT / "msx" / path).read_text().splitlines():
            code = line.split(";")[0].strip()
            if code == "if CHEAT":
                inside = True
            elif inside and code == "endif":
                inside = False
            elif inside:
                out.append(code)
        return out

    def test_the_cheat_code_is_in_its_if_blocks_and_banked(self):
        frame = self.blocks("frame.asm")
        self.assertIn("call fe_keys", frame)
        self.assertIn("fe_keys:", frame)
        self.assertIn("ld a,0x59", frame)
        cold = self.blocks("cold.asm")
        self.assertEqual(cold, ["ld a,0xFF", "ld (AG + (0x804F ^ 1)),a"])
        for f in ("rc2.asm", "player.asm", "sound.asm", "isr.asm", "tiles.asm", "sprites.asm"):
            self.assertNotIn("CHEAT", (ROOT / "msx" / f).read_text(), f)     # (the fixed area: nothing)
        src = (ROOT / "msx" / "frame.asm").read_text()
        self.assertEqual(src.count("fe_keys"), len([l for l in frame if "fe_keys" in l]))

    @unittest.skipUnless((ROOT / "build" / "msx" / "level1.map").exists() and POOL.with_suffix(".bin").exists(),
                         "needs the conversions (make msx)")
    def test_a_cheat_build_spends_no_fixed_area_byte(self):
        """The code windows' ends (msx/rc2.asm NAME_end): the fixed area's and every bank's as the
        product's but LC3's (fe_keys and its call) and FRONT's (the $804F store). The banks may
        differ besides in operands: the labels after the new code moved."""
        import contextlib
        import io
        ends = {}
        with tempfile.TemporaryDirectory() as t:
            for name, opts in (("prod", []), ("cheat", ["CHEAT=1"])):
                out = Path(t) / name / "rc2.rom"
                out.parent.mkdir()
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(mkrom.main(["mkrom.py", str(ROOT / "build" / "msx" / "level1"), str(out)] + opts), 0)
                lab = out.with_suffix(".labels").read_text()
                ends[name] = dict(re.findall(r"^(\w+_end):\s+equ \$([0-9a-f]+)$", lab, re.M))
                ends[name]["size"] = len(out.read_bytes())
        a, b = ends["prod"], ends["cheat"]
        self.assertEqual(a["code_end"], b["code_end"])
        self.assertEqual(a["size"], b["size"])
        diff = {k: int(b[k], 16) - int(a[k], 16) for k in ("code_end", "lc1_end", "lc2_end", "l1_end", "lc3_end",
                                                         "input_end", "front_end", "field_end", "music_end",
                                                         "puzl_end", "frng_end", "l2_end")}
        self.assertEqual(diff, {"code_end": 0, "lc1_end": 0, "lc2_end": 0, "l1_end": 0, "lc3_end": 33,
                                "input_end": 0, "front_end": 5, "field_end": 0, "music_end": 0, "puzl_end": 0,
                                "frng_end": 0, "l2_end": 0})


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
