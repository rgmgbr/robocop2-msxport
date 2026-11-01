"""What msx/sprites.asm's budget takes for granted in the global sprite pool (build/msx/sprites.bin, the
composition format of tools/msxsprites.py FORMAT, as the engine reads it: obj_set, ln_ver, ln_obj)."""
from __future__ import annotations

import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POOL = ROOT / "build" / "msx" / "sprites"          # the global sprite pool (make msx)
COMP_HDR = 8                                        # msx/sprites.asm COMP_HDR
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


if __name__ == "__main__":
    unittest.main()
