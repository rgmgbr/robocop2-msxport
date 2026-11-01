import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import amitab  # noqa: E402
import cellmasks  # noqa: E402
import hudmodel  # noqa: E402
import mapcells  # noqa: E402
import mkrom  # noqa: E402
import msxconv  # noqa: E402
import msxbanktest  # noqa: E402
import msxgun  # noqa: E402
import msxhud  # noqa: E402
import msxhudrt  # noqa: E402
import planar  # noqa: E402
import player  # noqa: E402
import pp20  # noqa: E402
import tracecmp  # noqa: E402

SPRITES = ROOT / "build" / "msx" / "robocop"     # tools/msxsprites.py output (make msx)
DISK1 = ROOT / "amiga" / "Robocop 2 (1991)(Ocean)[cr Melnok](Disk 1 of 2).adf"
DISK2 = ROOT / "amiga" / "Robocop 2 (1991)(Ocean)[cr Melnok](Disk 2 of 2).adf"
HAVE_DISKS = DISK1.exists() and DISK2.exists()
MAIN = ROOT / "build" / "extracted" / "boot" / "main_8000.bin"
LEVEL1_RAM = ROOT / "build" / "ram" / "level1_full.bin"     # tools/ramimage.py (make ram)


class PP20Tests(unittest.TestCase):
    def test_rejects_missing_magic(self):
        with self.assertRaises(pp20.PP20Error):
            pp20.decrunch(b"XXXX" + bytes(12))

    def test_trailer(self):
        self.assertEqual(pp20.trailer(b"\x01\x02\x03\x07"), (0x010203, 7))


class PlanarTests(unittest.TestCase):
    def test_two_planes_sequential_and_interleaved(self):
        # 16x1 pixels, 2 planes: plane0 = 0xF0F0, plane1 = 0xFF00 -> indices 3,3,3,3,2,2,2,2,1,1,1,1,0,0,0,0
        expected = [3] * 4 + [2] * 4 + [1] * 4 + [0] * 4
        seq = bytes([0xF0, 0xF0, 0xFF, 0x00])
        self.assertEqual(planar.decode_indices(seq, 0, 16, 1, 2, "planes")[0], expected)
        self.assertEqual(planar.decode_indices(seq, 0, 16, 1, 2, "interleaved")[0], expected)


class MsxConvTests(unittest.TestCase):
    def test_palette_12_to_9_bits(self):
        self.assertEqual(msxconv.amiga_to_msx(0x000), (0, 0, 0))
        self.assertEqual(msxconv.amiga_to_msx(0xFFF), (7, 7, 7))
        self.assertEqual(msxconv.amiga_to_msx(0x8F0), (4, 7, 0))

    def test_pack_sc5_left_pixel_in_high_nibble(self):
        px = [[x % 16 for x in range(16)] for _ in range(16)]
        packed = msxconv.pack_sc5(px)
        self.assertEqual(len(packed), 128)
        self.assertEqual(packed[:8], bytes([0x01, 0x23, 0x45, 0x67, 0x89, 0xAB, 0xCD, 0xEF]))


class MsxHudTests(unittest.TestCase):
    def test_layout_fills_256_px_and_heads_meet_the_score_frame(self):
        xs = msxhud.layout()
        self.assertEqual(xs["can"], 0)
        self.assertEqual(xs["heads"] + 32 + 29, xs["score"])

    def test_digit_cell_keeps_one_background_column(self):
        self.assertEqual(msxhud.cell(224), list(range(225, 238)))

    def test_reduce_keeps_black_and_limits_colours(self):
        pal12 = [0x000] + [0x100 * (i % 8) + 0x010 * (i % 5) + (i % 3) for i in range(1, 32)]
        img = [list(range(32))]
        idx, pal = msxhud.reduce_colours(img, pal12, 16)
        self.assertEqual(len(pal), 16)
        self.assertEqual(pal[0], (0, 0, 0))
        self.assertEqual(idx[0][0], 0)
        self.assertTrue(all(0 <= v < 16 for v in idx[0]))


class HudRuntimeTests(unittest.TestCase):
    def test_font_codes_as_panel_draw_char(self):
        # $10620: ' ' -> 41, letters from 'A', other codes below '@' from $16; the game's
        # strings use lower-case letters for the punctuation glyphs ('e' = '.')
        self.assertEqual([hudmodel.font_index(ord(c)) for c in " AZ09e"], [41, 0, 25, 26, 35, 36])
        self.assertEqual(hudmodel.font_index(0x80 | ord("A")), 0)

    def test_digit_cell_byte_ownership(self):
        # a cell at an even x owns its 7 bytes (the last one shares the next cell's constant
        # first column); at an odd x its first byte belongs to the cell on its left
        self.assertEqual(msxhudrt.cell_bytes(160), (80, 7))
        self.assertEqual(msxhudrt.cell_bytes(173), (87, 6))


class GameLogicToolTests(unittest.TestCase):
    def test_joystick_script_entries(self):
        inc = mkrom.input_inc("70:40:r,115:3:uf")
        self.assertIn("        dw 70, 40\n        db 0x08", inc)
        self.assertIn("        dw 115, 3\n        db 0x11", inc)
        self.assertTrue(inc.rstrip().endswith("dw 0xFFFF"))
        self.assertEqual(mkrom.input_inc("").count("dw"), 1)

    def test_cell_masks_from_the_routines_windows(self):
        import struct
        # one spawn entry at (200h, 100h), one beam at (2B0h, 60h): big-endian, as the RAM image is
        img = struct.pack(">hh", 0x200, 0x100) + bytes(10) + struct.pack(">h", -1)
        img += struct.pack(">hhhh", 0x2B0, 0x60, 0x2B0, 2) + struct.pack(">h", -1)
        entries, recs = cellmasks.spawn_entries(img, 0), cellmasks.hazard_records(img, 16)
        self.assertEqual((entries, recs), ([(0x200, 0x100)], [(0x2B0, 0x60, 0x2B0, 2)]))

        def cells(items, n, test):
            return [c for c, m in enumerate(cellmasks.cell_masks(items, n, test)) if m]
        # the walk's window: camera x + 5Eh <= x <= camera x + 1AFh (camera x 81..418), camera y - 28h
        # < y <= camera y + A8h (88..295); the hazards': window x >= camera x + 73h and x < camera x
        # + 1A0h (273..573), camera y - 64h <= y < camera y + ACh (0..196); 64-pixel cells
        self.assertEqual(cells(entries, 40, cellmasks.spawn_x), [1, 2, 3, 4, 5, 6])
        self.assertEqual(cells(entries, 13, cellmasks.spawn_y), [1, 2, 3, 4])
        self.assertEqual(cells(recs, 40, cellmasks.hazard_x), [4, 5, 6, 7, 8])
        self.assertEqual(cells(recs, 13, cellmasks.hazard_y), [0, 1, 2, 3])
        inc = cellmasks.inc_text("l1", entries, recs, 40, 13, "test")
        self.assertIn("SW_N:       equ 1 ", inc)
        self.assertIn("sw_all:  db 0x01,0x00,0x00,0x00,0x00 ", inc)
        self.assertIn("hz_all:  db 0x01,0x00 ", inc)
        self.assertNotIn("sw_ptr", inc)         # (msx/lvshared.asm holds it, SW_MAX entries)
        # another level's names carry its suffix (tools/mkrom.py's copy of msx/lvshared.asm uses them)
        inc2 = cellmasks.inc_text("l2", entries, recs, 40, 13, "test")
        for name in ("SW_N_l2:", "SW_XN_l2:", "sw_xm_l2:", "sw_all_l2:", "HZ_YN_l2:", "hz_ym_l2:", "hz_all_l2:"):
            self.assertIn(name, inc2)
        # the masks' size is the shared code's (msx/msx.inc SW_MAX, SW_MB)
        inc_msx = (ROOT / "msx" / "msx.inc").read_text()
        self.assertRegex(inc_msx, rf"(?m)^SW_MAX:\s+equ {cellmasks.SW_MAX}\s")
        self.assertRegex(inc_msx, rf"(?m)^SW_MB:\s+equ {cellmasks.SW_MB}\s")

    def test_lvshared_copy_renames_labels_and_level_data(self):
        src = ("; a comment naming t3 and sw_xm stays\n"
               "t3:     call walker2                ; (t3's own)\n"
               "        ld hl,t3_gfx\n"
               "        ld de,0x5E\n"
               "        jr t3\n"
               "        cp SW_N\n")
        out = mkrom.lvshared_copy(src, "l2", {"t3_gfx", "SW_N", "spawn_l1"}).split("\n")
        self.assertTrue(out[0].startswith("; generated by tools/mkrom.py"))
        self.assertEqual(out[1:], ["; a comment naming t3 and sw_xm stays",
                                   "t3_l2:     call walker2                ; (t3's own)",
                                   "        ld hl,t3_gfx_l2", "        ld de,0x5E", "        jr t3_l2",
                                   "        cp SW_N_l2", ""])
        labels = "t3:\tequ $a0f0\nt3_l2:\tequ $a0f0\n"
        self.assertEqual(mkrom.lvshared_check(src, labels), [])
        self.assertEqual(len(mkrom.lvshared_check(src, labels.replace("t3_l2:\tequ $a0f0", "t3_l2:\tequ $a0f2"))), 1)

    def test_lvshared_copy_without_its_last_section(self):
        # VAT_ANIM=1 builds: the other levels' copies end before the sprite budget's give-way, which
        # level 1's bank alone holds then (msx/sprites.asm bu_lvl maps it)
        src = ("t3:     call walker2\n"
               "        jr t3\n"
               "\n" + mkrom.LVS_TAIL + " (msx/sprites.asm budget) -----\n"
               "ft_give:\n"
               "        jr ft_give\n")
        whole = mkrom.lvshared_copy(src, "l2", set())
        cut = mkrom.lvshared_copy(src, "l2", set(), tail=False)
        self.assertIn("ft_give_l2:", whole)
        self.assertIn("t3_l2:     call walker2", cut)
        self.assertNotIn("ft_give", cut)
        self.assertTrue(whole.startswith(cut.rstrip("\n") + "\n\n" + mkrom.LVS_TAIL))     # (the rest as it was)
        with self.assertRaises(ValueError):
            mkrom.lvshared_copy("t3:     ret\n", "l2", set(), tail=False)
        # the repository's msx/lvshared.asm: the section is there once, and it is the last one
        lvs = (ROOT / "msx" / "lvshared.asm").read_text()
        self.assertEqual(lvs.count("\n" + mkrom.LVS_TAIL), 1)
        self.assertNotIn("\n; -----", lvs.split("\n" + mkrom.LVS_TAIL, 1)[1])

    def test_map_cells_as_the_writers_address_them(self):
        # $EF8E: column (x >> 4) - 8 as a byte, row y >> 4, 0 above or below the map's rows
        self.assertEqual(mapcells.map_cell(0x2B0, 0x60, 51), (6, 35))
        self.assertEqual(mapcells.map_cell(0x40, 0x60, 51), (6, 0xFC))
        self.assertEqual(mapcells.map_cell(0x2B0, -16 & 0xFFFF, 51), (0, 35))
        self.assertEqual(mapcells.map_cell(0x2B0, 51 * 16, 51), (0, 35))
        self.assertEqual(mapcells.map_cell(0x2B0, 0x60, 51, dx=7), (6, 36))
        # map_write_lin: columns -8..-1 the row above's end, 160..167 the next row's start
        self.assertEqual(mapcells.lin(6, 0xFC, 160), (5, 156))
        self.assertEqual(mapcells.lin(6, 161, 160), (7, 1))
        self.assertEqual(mapcells.lin(6, 159, 160), (6, 159))
        self.assertEqual(mapcells.lin(6, 0xFF + 1, 160), (6, 0))     # (inc e after FFh: 0)
        self.assertEqual(mapcells.map_cell(0x2B0, 0x1000, 51), (0, 35))      # (4096: row 0)
        self.assertEqual(mapcells.map_cell(0x2B0, 0x1050, 51, whole=True), (0, 35))
        self.assertEqual(mapcells.map_cell(0x2B0, 0x1050, 51), (5, 35))      # (map_cell: low byte)

    @unittest.skipUnless(LEVEL1_RAM.exists(), "level 1's RAM image not built (make ram)")
    def test_level1_map_changes_fit_the_patch_pools(self):
        tabs = {r["label"]: r for r in amitab.parse(ROOT / "analysis" / "amiga_tables.tsv")}
        cells, words = mapcells.writers(LEVEL1_RAM.read_bytes(), tabs, "l1", 160, 51)
        every = set().union(*cells.values())
        pools = [sum(1 for r, _ in every if r % 2 == p) for p in (0, 1)]
        self.assertEqual((len(every), pools), (438, [213, 225]))
        self.assertTrue(all(n <= mapcells.MP_N for n in pools))
        self.assertEqual(sum(len(c) for k, c in cells.items() if k.startswith("beam")), 80)
        self.assertEqual(len(cells["type 32"]), 35)            # (36 words, two in one cell)
        self.assertEqual(sorted({w & 0x7F for ws in words.values() for w in ws}), [0, 1, 2, 3, 0x29])

    def test_attribute_codes_need_ffh_free_entries(self):
        values = [0, 1, 2, 3, 0x29]
        new = bytes([0, 1, 2, 3, 9, 10, 11, 13, 0x20]) + b"\xff" * 7
        self.assertEqual(mapcells.code_problems(new, values), [])
        old = bytes([0, 1, 2, 3, 9, 10, 11, 13, 0x20]) + bytes(7)     # (zero padding: no free code)
        self.assertIn("same value", mapcells.code_problems(old, values)[0])
        full = bytes(range(0x30, 0x40))
        self.assertIn("29h", mapcells.code_problems(full, [0x30, 0x29])[0])
        self.assertEqual(mapcells.code_problems(full, [0x30, 0x3F]), [])

    def test_stream_ticks_reads_each_format(self):
        # [duration, ctl, its fields...]: SCC / OPLL ctl bit 4 a word, bit 5 a byte; the PSG's
        # bits 6 and 7; the rhythm's bit 5 three volume bytes; a duration of 0 ends the stream
        scc = bytes([3, 0x3F, 1, 2, 9, 4, 0x0F, 0])
        self.assertEqual(mkrom.stream_ticks(scc, 0, mkrom.MVK_SCC), 7)
        psg = bytes([2, 0xCF, 1, 2, 9, 5, 0x30, 0])
        self.assertEqual(mkrom.stream_ticks(psg, 0, mkrom.MVK_PSG), 7)
        rhy = bytes([6, 0x31, 1, 2, 3, 1, 0x01, 0])
        self.assertEqual(mkrom.stream_ticks(rhy, 0, mkrom.MVK_RHY), 7)

    @unittest.skipUnless((ROOT / "build" / "msx" / "fm.bin").exists(), "music data not built (make msx)")
    def test_title_streams_last_one_tune(self):
        # music.asm mus_adv ends the title at MUS_TICKS: the eight streams must end together
        scc = (ROOT / "build" / "msx" / "scc.bin").read_bytes()
        fm = (ROOT / "build" / "msx" / "fm.bin").read_bytes()
        kinds = ((scc, (mkrom.MVK_SCC,) * 3 + (mkrom.MVK_PSG,)), (fm, (mkrom.MVK_FM,) * 3 + (mkrom.MVK_RHY,)))
        ticks = [mkrom.stream_ticks(b, mkrom.offsets(b, 4)[i], k) for b, ks in kinds for i, k in enumerate(ks)]
        self.assertEqual(ticks, [5184] * 8)

    @unittest.skipUnless((ROOT / "build" / "msx" / "voice.inc").exists(), "speech not built (make msx)")
    def test_speech_starts_and_ends_on_the_held_level(self):
        # tools/msxvoice.py: both PCMs from and back to VOICE_DC_IDX (music.asm vm_alone, vm_music:
        # no step); voice.bin's padding silent and long enough for vm_cal's 81 bytes
        import re
        inc = (ROOT / "build" / "msx" / "voice.inc").read_text()
        eq = {k: int(v) for k, v in re.findall(r"^(VOICE_\w+): equ (\d+)", inc, re.M)}
        voice = (ROOT / "build" / "msx" / "voice.bin").read_bytes()
        mix = (ROOT / "build" / "msx" / "voice_mix.bin").read_bytes()
        n, m, dc = eq["VOICE_LEN"], eq["VOICE_MIX_LEN"], eq["VOICE_DC_IDX"]
        self.assertEqual((voice[0], voice[n - 1], mix[0], mix[m - 1]), (dc, dc, dc, dc))
        self.assertEqual(set(voice[n:]), {0})
        self.assertGreaterEqual(len(voice) - n, 81)

    def test_gun_streams_read_back_as_their_records(self):
        # tools/msxgun.py: both blobs check their streams against the records while built
        scc, psg = msxgun.scc_blob(), msxgun.psg_blob()
        self.assertEqual(scc[3], len(msxgun.WAVES))
        self.assertEqual([e[0] for e in mkrom.fx_entries(scc)], [0, 1, 2])     # channels 0-2
        self.assertEqual(psg[0] | psg[1] << 8, 6)
        self.assertEqual(len(psg), 6 + sum(len(msxgun.psg_stream(v)) for v in msxgun.PSG_VOICES))
        self.assertEqual(msxgun.ticks(msxgun.PSG_VOICES[2]), 8)      # (C idle for a bullet after)
        self.assertEqual(msxgun.psg_stream([(2, 0, 1, 0, None, None)]), bytes([2, 0, 0]))
        self.assertEqual(msxgun.scc_stream([(1, 5, 0x123, 2)]), bytes([1, 0x35, 0x23, 0x01, 2, 0]))

    def test_fx_append_moves_offsets_and_waveforms(self):
        def blob(fx: list[tuple[int, bytes, bytes]], waves: int) -> bytes:
            head, body, entries = 4 + 7 * len(fx), b"", b""
            for ch, scc, psg in fx:
                so = head + len(body) if scc else 0
                body += scc
                po = head + len(body) if psg else 0
                body += psg
                entries += bytes([ch]) + so.to_bytes(3, "little") + po.to_bytes(3, "little")
            tab = head + len(body)
            return tab.to_bytes(3, "little") + bytes([waves]) + entries + body + bytes(range(32 * waves))
        base = blob([(2, bytes([3, 0x35, 0x10, 0x00, 1, 0]), bytes([2, 0x05, 0])),
                     (3, b"", bytes([1, 0x25, 0]))], 2)
        more = blob([(0, bytes([1, 0x31, 0x20, 0x00, 0, 2, 0x24, 1, 0]), b"")], 1)
        m = mkrom.fx_append(base, more)
        fx = mkrom.fx_entries(m)
        self.assertEqual(len(fx), 3)
        self.assertEqual(m[3], 3)
        self.assertEqual([e[0] for e in fx], [2, 3, 0])
        self.assertEqual(m[fx[0][1]:fx[0][1] + 6], bytes([3, 0x35, 0x10, 0x00, 1, 0]))     # (kept)
        self.assertEqual(m[fx[1][2]:fx[1][2] + 3], bytes([1, 0x25, 0]))
        self.assertEqual(fx[1][1], 0)
        self.assertEqual(m[fx[2][1]:fx[2][1] + 9], bytes([1, 0x31, 0x20, 0x00, 2, 2, 0x24, 3, 0]))
        tab = mkrom.offsets(m, 1)[0]
        self.assertEqual(m[tab:], bytes(range(64)) + bytes(range(32)))

    def test_bank_test_tags_name_every_bank(self):
        # tools/msxbanktest.py: the byte at 0020h names its bank, the one at 1720h is 9Bh more
        for b in range(msxbanktest.BANKS):
            t = msxbanktest.fill(b, msxbanktest.TAG)
            self.assertEqual(msxbanktest.shown(t), b)
            self.assertEqual(msxbanktest.fill(b, msxbanktest.TAG2), (t + 0x9B) & 0xFF)

    @unittest.skipUnless(shutil.which("z80asm"), "z80asm not installed")
    def test_bank_test_image(self):
        rom = msxbanktest.image(*msxbanktest.assemble("T1"))
        bank = msxbanktest.BANK
        self.assertEqual(len(rom), 256 * bank)
        self.assertEqual(rom[0x10:0x18], b"ROM_KON5")
        self.assertEqual((rom[0x20], rom[0x1720]), (0x20, 0xBB))       # bank 0's tags, in the code's room
        self.assertEqual(rom[0xC5 * bank:0xC6 * bank], msxbanktest.bank_data(0xC5))

    def test_rom_banks_and_the_2m_guard_tag(self):
        # tools/mkrom.py: a power of two of banks; over 1 MiB the last bank holds rom_guard's tag
        # (msx/frontx.asm since the ending's step, cold.asm before), the same bytes as its rg_tag
        self.assertEqual([mkrom.rom_banks(78), mkrom.rom_banks(129), mkrom.rom_banks(78, 256)], [128, 256, 256])
        self.assertEqual(mkrom.guard_tag(256), b"RC2BANK\xff")
        asm = (ROOT / "msx" / "frontx.asm").read_text()
        self.assertRegex(asm, r'rg_tag: db "RC2BANK", ROM_BANKS - 1')
        self.assertIn(f"0xA000 + 0x{mkrom.GUARD_AT:04X}", asm)

    def test_msx_trace_rows_are_signed_where_the_amiga_is(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "t.txt"
            f.write_text("3 144 800 2 0 4 65516 65535 640 255 16 16\n")
            r = tracecmp.msx_rows(f)[0]
        self.assertEqual((r["vy"], r["camera_x"], r["airborne"], r["joy"]), (-20, -1, 255, 16))

    @unittest.skipUnless(MAIN.exists(), "main code not extracted (make extract)")
    def test_logic_tables(self):
        text = player.logic_inc(MAIN.read_bytes())
        eq = {k.strip(): int(v.split()[0]) for k, v in (ln.split(": equ ") for ln in text.splitlines()
                                                         if ": equ " in ln)}
        self.assertEqual((eq["LVL_X"], eq["LVL_Y"], eq["LVL_YMAX"]), (144, 800, 640))
        self.assertEqual((eq["CAM_DX"], eq["CAM_DY"], eq["CAM_XMAX"], eq["FADE_STATE"]), (0x108, 0x70, 0x8E0, 10))

        def table(label):
            lines = text.split(label + ":\n")[1].split("\n")
            vals = []
            for ln in lines:
                if not ln.startswith("        d"):
                    break
                vals += [int(v, 0) for v in ln.split(None, 1)[1].split(", ")]
            return vals
        self.assertEqual(len(table("pl_xstep")), player.NSTATES)
        self.assertEqual(len(table("pl_stparm")), 3 * player.NPARAMS)
        self.assertEqual(len(table("pl_aimtab")), 16)
        rec0, nrec = table("pl_rec0"), table("pl_nrec")
        self.assertEqual([a + b for a, b in zip(rec0, nrec)][:-1], rec0[1:])   # records state by state
        self.assertEqual(len(table("pl_hot")), 2 * (rec0[-1] + nrec[-1]))
        self.assertEqual(eq["PL_ARM_REC"], rec0[player.ARM_STATE])


@unittest.skipUnless(SPRITES.with_suffix(".bin").exists(), "sprite data not built (make msx)")
class SpriteDataTests(unittest.TestCase):
    """The composition format msx/sprites.asm reads (FORMAT in tools/msxsprites.py)."""

    @classmethod
    def setUpClass(cls):
        import struct
        cls.data = SPRITES.with_suffix(".bin").read_bytes()
        inc = {}
        for line in SPRITES.with_suffix(".inc").read_text().splitlines():
            if ": equ " in line:
                k, v = line.split(": equ ")
                inc[k] = int(v.split()[0], 0)
        cls.inc = inc
        cls.comps = {}
        cls.robocop = set()                             # compositions of RoboCop (the rest: BOBs)
        nrc = inc["SPR_RECORDS"] * 4 + inc["SPR_RC_ARMS"]   # record x aim, then the arm poses
        assert inc["SPR_RC_ARM"] == inc["SPR_RECORDS"] * 4
        index = [3 * k for k in range(nrc)]
        index += [inc["SPR_BOB_INDEX"] - 0x8000 + 3 * k for k in range(inc["SPR_BOBS"])]
        for n, e in enumerate(index):
            bank, off = struct.unpack_from("<BH", cls.data, e)
            o = bank * 0x2000 + off
            if n < nrc:
                cls.robocop.add(o)
            if o in cls.comps:
                continue
            nspr, nlines, ncols, mindx, maxdx, n_a, mfull, mone = struct.unpack_from("<BBBbbBBB", cls.data, o)
            recs = [struct.unpack_from("<BbBBHHHH", cls.data, o + 8 + 12 * i) for i in range(nspr)]
            p = o + 8 + 12 * nspr
            ranks = []
            for _ in range(ncols):
                bit, gain, nb = cls.data[p], cls.data[p + 1], cls.data[p + 2]
                ranks.append((bit, list(cls.data[p + 3:p + 3 + nb]), gain))
                p += 3 + nb
            maxk = list(cls.data[p:p + ncols + 1])
            p += ncols + 1
            cls.comps[o] = (nspr, nlines, ncols, mindx, maxdx, recs, (mfull, mone, maxk), ranks, p - o, n_a)

    def test_compositions_fit_their_bank_and_the_limits(self):
        for o, (nspr, nlines, ncols, *_, size, n_a) in self.comps.items():
            self.assertEqual(o // 0x2000, (o + size - 1) // 0x2000)
            self.assertLessEqual(nspr, 32)              # an entry page holds 32 entries
            self.assertLessEqual(nlines, self.inc["SPR_MAX_LINES"])
            self.assertLessEqual(ncols, 8)              # the drop mask has 8 bits
            if o in self.robocop:
                self.assertLessEqual(nspr, self.inc["SPR_MAX"])
                self.assertLessEqual(n_a, self.inc["SPR_RC_ONE"])

    def test_records_bits_ids_and_sat_order(self):
        npat = (self.inc["SPR_COL_BANK"] - self.inc["SPR_PAT_BANK"]) * 256
        for nspr, nlines, ncols, mindx, maxdx, recs, *_ in self.comps.values():  # noqa: B007
            cols_seen, layer = [], {}
            for dy, dx, pbit, abit, pat, col, pat1, col1 in recs:
                self.assertTrue((pbit == 0) != (abit == 0))
                bit = pbit | abit
                self.assertEqual(bin(bit).count("1"), 1)
                self.assertLess(bit, 1 << ncols)
                self.assertLessEqual(dy + 16, nlines)
                self.assertLess(pat, npat)
                if pbit:
                    self.assertEqual((pat1, col1), (0xFFFF, 0xFFFF))
                else:
                    self.assertLess(pat1, npat)
                # SAT order: columns contiguous, A spans before B spans in each column
                if not cols_seen or cols_seen[-1] != bit:
                    self.assertNotIn(bit, cols_seen)
                    cols_seen.append(bit)
                elif layer[bit] and not pbit:
                    self.fail("A span after a B span in the same column")
                layer[bit] = bool(pbit)
            self.assertEqual((mindx, maxdx), (min(r[1] for r in recs), max(r[1] for r in recs)))

    def test_line_counts_and_rank_list(self):
        for nspr, nlines, ncols, _, _, recs, (mfull, mone, maxk), ranks, _, n_a in self.comps.values():
            want, want1 = [0] * nlines, [0] * nlines
            for r in recs:
                for line in range(r[0], r[0] + 16):
                    want[line] += 1
                    want1[line] += not r[2]
            self.assertEqual((mfull, mone), (max(want), max(want1)))
            for k in range(ncols + 1):                     # maxima after dropping each rank prefix
                dropped = sum(bit for bit, _, _ in ranks[:k])
                cnt = [0] * nlines
                for r in recs:
                    if not r[2] & dropped:
                        for line in range(r[0], r[0] + 16):
                            cnt[line] += 1
                self.assertEqual(maxk[k], max(cnt))
            self.assertEqual((maxk[0], maxk[-1]), (mfull, mone))
            self.assertEqual(n_a, sum(1 for r in recs if not r[2]))
            self.assertLessEqual(mfull, 8)
            self.assertEqual(sorted(bit for bit, _, _ in ranks), [1 << k for k in range(ncols)])
            gains = [g for _, _, g in ranks]
            self.assertEqual(gains, sorted(gains))         # cheapest OR layer first
            self.assertLess(max(gains), 255)               # FFh means "no candidate" at run time
            for bit, dys, _ in ranks:
                self.assertEqual(dys, [r[0] for r in recs if r[2] == bit])


@unittest.skipUnless(HAVE_DISKS, "ADFs missing from amiga/")
class Robocop2DiskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import rc2files
        cls.rc = rc2files.Robocop2(str(DISK1), str(DISK2))

    def test_boot_chain(self):
        loads = {(ld.disk_offset, ld.length, ld.final) for ld in self.rc.boot_loads}
        self.assertEqual(loads, {(0x400, 0xA600, 0x8000), (0xCE600, 0x200, 0x100),
                                 (0xCE800, 0x800, 0x300), (0xD4800, 0x5200, 0x71000)})
        self.assertTrue(self.rc.boot_ok)

    def test_tables(self):
        self.assertEqual(self.rc.name_table_addr, 0x14E)
        self.assertEqual(self.rc.directory_addr, 0x91C)
        self.assertEqual(len(self.rc.entries), 27)

    def test_all_pp20_files_decrunch_exactly(self):
        packed = [e for e in self.rc.entries if e.packed]
        self.assertEqual(len(packed), 14)
        for e in packed:
            self.assertEqual(e.notes, [], e.name)
        sizes = {e.name: len(e.data) for e in self.rc.entries}
        self.assertEqual(sizes["DATAE"], 32032)
        self.assertEqual(sizes["DATAL3"], 185356)

    def test_hud_heads_identical_and_1to1(self):
        import planar
        perma = next(e.data for e in self.rc.entries if e.name == "PERMA")
        panel = planar.decode_indices(perma, msxhud.PANEL_OFFSET, 320, 48, 5, "planes")[:46]
        hud, dyn = msxhud.compose(panel)
        (x0, y0), (x1, y1) = dyn["heads"]
        for y in range(4, 32):                  # the faces: below the frame pieces
            self.assertEqual(hud[y0 + y][x0:x0 + 26], hud[y1 + y][x1:x1 + 26])
            self.assertEqual(hud[y0 + y][x0:x0 + 26], panel[14 + y][128:154])

    def test_panel_model_redraws_the_original_panel(self):
        # the panel in PERMA is what the game's own routines draw at the start: timer 09:58,
        # ammo 000, score 0000000, full can, two RoboCop heads, weapon 0's icon
        perma = next(e.data for e in self.rc.entries if e.name == "PERMA")
        ld = next(ld for ld in self.rc.boot_loads if ld.final == 0x8000)
        main = self.rc.disks[1].read(ld.disk_offset, ld.length)
        p = hudmodel.Panel(perma, main)
        before = [row[:] for row in p.px]
        for k, v in enumerate([0, 9, 5, 8] + [0] * 10):
            p.digit(k, v)
        p.can_full()
        p.head(0, 0)
        p.head(0, 1)
        p.icon(p.weapon_icon(0))
        self.assertEqual(p.px[:46], before[:46])

    def test_disks_fully_accounted(self):
        unknown = [(d, a, b) for d, runs in self.rc.coverage().items() for a, b, k in runs if k.startswith("??")]
        orphans = {(d, s // 512) for d, s, _ in self.rc.unlisted_pp20()}
        self.assertTrue(all((d, a) in orphans for d, a, _ in unknown), unknown)


if __name__ == "__main__":
    unittest.main()
