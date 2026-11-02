"""What msx/sprites.asm's budget takes for granted in the global sprite pool (build/msx/sprites.bin, the
composition format of tools/msxsprites.py FORMAT, as the engine reads it: obj_set, ln_ver, ln_obj), and
the band mask each composition's header holds for obj_set (O_BMASK, docs/PERF2_PLAN.md item 16, spr-8),
and that no tool reads a composition with the header size of before spr-8."""
from __future__ import annotations

import re
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "build" / "msx" / "sprites"          # the global sprite pool (make msx)
COMP_HDR = 9                                        # msx/sprites.asm COMP_HDR (the pool's SPR_COMP_HDR)
BAND = 4                                            # a band entry: dy (signed), A, B, gain


def equates(path: Path) -> dict[str, int]:
    out = {}
    for line in path.read_text().splitlines():
        if ": equ " in line:
            k, v = line.split(": equ ")
            v = v.split()[0]
            out[k.strip()] = out[v] if v in out else int(v, 0)
    return out


@unittest.skipUnless(POOL.with_suffix(".bin").exists(), "build/msx/sprites.bin missing (make msx)")
class RoboCopBandTests(unittest.TestCase):
    """ln_rc counts RoboCop's first version (the one he wants) on an empty ln_cnt by storing each band's
    sprites on its lines, not by keeping the most per line (ln_ver, D = 1): exact only because no two
    bands of a composition of his share a line (a band covers 16 lines from its dy)."""

    @classmethod
    def setUpClass(cls):
        cls.data = POOL.with_suffix(".bin").read_bytes()
        inc = equates(POOL.with_suffix(".inc"))
        assert inc.get("SPR_COMP_HDR") == COMP_HDR, "the pool's composition format is not the engine's (make msx)"
        cls.nrc = inc["SPR_RECORDS"] * 4 + inc["SPR_RC_ARMS"]     # record x aim, then the arm poses
        cls.ncomps = inc["SPR_COMPS"]                               # his compositions (all shown by one)
        assert inc["SPR_RC_ARM"] == inc["SPR_RECORDS"] * 4
        cls.comps = {}
        for k in range(cls.nrc):                                    # RoboCop's index at 8000h
            bank, off = struct.unpack_from("<BH", cls.data, 3 * k)
            o = bank * 0x2000 + off
            if o in cls.comps:
                continue
            nspr, nlines, nbands = cls.data[o], cls.data[o + 1], cls.data[o + 2]
            p = o + COMP_HDR + 12 * nspr
            bands = [struct.unpack_from("<bBBB", cls.data, p + BAND * b) for b in range(nbands)]
            cls.comps[o] = (nspr, nlines, bands)

    def test_his_bands_never_share_a_line(self):
        self.assertEqual(len(self.comps), self.ncomps)              # every one of his (144 on 2026-11-01)
        for o, (nspr, nlines, bands) in self.comps.items():
            dys = sorted(dy for dy, _, _, _ in bands)
            for a, b in zip(dys, dys[1:]):
                self.assertGreaterEqual(b - a, 16, f"composition at {o:#x}: bands at dy {a} and {b}")

    def test_the_band_table_counts_every_sprite(self):
        # (the budget's per-line counts come from the band table alone: A + B sprites a band)
        for o, (nspr, nlines, bands) in self.comps.items():
            self.assertEqual(sum(a + b for _, a, b, _ in bands), nspr, f"composition at {o:#x}")
            for dy, a, b, _ in bands:
                self.assertLessEqual(a + b, 5, f"composition at {o:#x}")   # (RC_CAP, msx/sprites.asm RC_LINE)


def compositions(data: bytes, inc: dict[str, int]) -> dict[int, str]:
    """Every composition an index entry of the pool names (RoboCop's, then levels 1-3's BOB frames)
    -> its offset in the pool and the first entry that names it."""
    out = {}
    nrc = inc["SPR_RECORDS"] * 4 + inc["SPR_RC_ARMS"]
    entries = [(3 * k, f"RoboCop {k}") for k in range(nrc)]
    for n in (1, 2, 3):
        if f"SPR_BOB_INDEX_L{n}" in inc:
            base = inc[f"SPR_BOB_INDEX_L{n}"] - 0x8000
            entries += [(base + 3 * k, f"level {n} frame {k}") for k in range(inc[f"SPR_BOBS_L{n}"])]
    for e, name in entries:
        bank, off = struct.unpack_from("<BH", data, e)
        out.setdefault(bank * 0x2000 + off, name)
    return out


@unittest.skipUnless(POOL.with_suffix(".bin").exists(), "build/msx/sprites.bin missing (make msx)")
class BandMaskTests(unittest.TestCase):
    """obj_set copies a composition's band mask (its bands with B sprites, O_BMASK) from the header's
    last byte: it must equal what obj_set worked out before 2026-11-02, walking the band table from
    its first entry (the lowest band, bit 0) and setting a band's bit when it has B sprites, for
    every composition of every level."""

    @classmethod
    def setUpClass(cls):
        cls.data = POOL.with_suffix(".bin").read_bytes()
        cls.inc = equates(POOL.with_suffix(".inc"))
        cls.comps = compositions(cls.data, cls.inc)

    def test_every_level_is_there(self):
        self.assertEqual(self.inc.get("SPR_COMP_HDR"), COMP_HDR)
        self.assertTrue(all(f"SPR_BOB_INDEX_L{n}" in self.inc for n in (1, 2, 3)))
        self.assertGreater(len(self.comps), 400)                    # (482 on 2026-11-02)

    def test_the_stored_mask_is_the_band_walks(self):
        d = self.data
        for o, name in self.comps.items():
            nspr, nbands, mask = d[o], d[o + 2], d[o + COMP_HDR - 1]
            p = o + COMP_HDR + 12 * nspr                            # (the band table, after the records)
            walked, bit = 0, 1
            for b in range(nbands):                                 # (obj_set's os_bm loop)
                if d[p + BAND * b + 2]:
                    walked |= bit
                bit <<= 1
            self.assertEqual(mask, walked, f"{name} (composition at {o:#x})")

    def test_the_stored_mask_is_the_b_sprites_bands(self):
        d = self.data
        for o, name in self.comps.items():
            nspr, nbands, mask = d[o], d[o + 2], d[o + COMP_HDR - 1]
            parks = 0
            for s in range(nspr):
                parks |= d[o + COMP_HDR + 12 * s + 2]               # (a B sprite's park bit: its band's)
            self.assertEqual(mask, parks, f"{name} (composition at {o:#x})")
            self.assertLess(mask, 1 << nbands, f"{name} (composition at {o:#x})")


class HeaderSizeTests(unittest.TestCase):
    """Since spr-8 (2026-11-02) a composition's header is the pool's SPR_COMP_HDR bytes (9: the band mask after
    the eight before it). A tool that reads a composition's sprite records or band table takes that size from
    the pool (tools/msxsprites.py SpriteData.hdr, the .inc's SPR_COMP_HDR), never a literal 8: a reader written
    against the older format ("o + 8 + 12 * i") takes every record a byte early, and its build stops (an index
    past the pattern pool) or, worse, its tables come out wrong. A source check (no conversion needed): a tool
    with such a reader that comes in from another branch fails here, before its first build."""

    def test_no_tool_reads_a_composition_with_8_header_bytes(self):
        lit = re.compile(r"\+\s*8\s*\+\s*12\s*\*")         # (the header, then the 12-byte sprite records)
        bad = []
        for top in ("tools", "docs"):
            for path in sorted((ROOT / top).rglob("*.py")):
                for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
                    if lit.search(line.split("#")[0]):
                        bad.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()}")
        self.assertEqual(bad, [], "a composition read with the 8-byte header of before spr-8: take the pool's "
                                  "SPR_COMP_HDR (tools/msxsprites.py SpriteData.hdr)")


if __name__ == "__main__":
    unittest.main()
