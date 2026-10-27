"""tools/msxtune.py: the routing step, Brainstorm's PZM.

The regression the routing rests on: through it TITM tune 1 gives today's conversions byte for
byte (scc.bin 25,803 B, fm.bin 13,238 B, the PSG title 5,990 B at msxsound's lambda for the
Makefile's budget). Those tests need numpy (the project's venv: ~/.venvs/msxports/bin/python -I -m
unittest tests.test_msxtune) and the converted files (make msx); without them they are skipped.
The OPLL conversion fits patches: about two minutes in all."""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False
MSX = ROOT / "build" / "msx"
TITM = ROOT / "build" / "music" / "TITM.json"
PUZL = ROOT / "build" / "extracted" / "files" / "PUZL_25.bin"


def stream_len(b: bytes, start: int, kind: int) -> int:
    """A stream's bytes, its end marker included (kind: music.asm's MVK_SCC 0, MVK_PSG 1, MVK_FM 2,
    MVK_RHY 3)."""
    word, byte = (0x40, 0x80) if kind == 1 else (0x10, 0x20)
    p = start
    while b[p]:
        ctl, p = b[p + 1], p + 2
        if kind == 3:
            p += 3 if ctl & 0x20 else 0
        else:
            p += (2 if ctl & word else 0) + (1 if ctl & byte else 0)
    return p + 1 - start


@unittest.skipUnless(HAVE_NUMPY, "needs numpy (the project's venv)")
@unittest.skipUnless(TITM.exists() and (MSX / "scc.bin").exists() and (MSX / "fm.bin").exists()
                     and (MSX / "sound.inc").exists(), "title music not converted (make msx)")
class TitleThroughTheRoutingTests(unittest.TestCase):
    """TITM tune 1 through tools/msxtune.py's routing: today's files, byte for byte."""

    @classmethod
    def setUpClass(cls):
        import msxtune
        cls.mt = msxtune
        cls.gt = msxtune.titm_title()

    def test_routing_is_the_identity(self):
        rt = self.gt.rt
        self.assertEqual((rt.T, rt.loop_tick, rt.stolen_notes, rt.drum_ticks_lost, len(rt.dchans)), (5184, 0, 0, 0, 1))

    def test_scc_bin(self):
        ref = (MSX / "scc.bin").read_bytes()
        self.assertEqual(len(ref), 25803)
        self.assertEqual(self.mt.scc_version(self.gt)["blob"], ref)

    def test_psg_title(self):
        ms = self.mt.ms
        rt, dt = ms.load_music("TITM", "TITM_04.bin")
        rf, df = ms.load_music("MU1", "MU1_09.bin")
        lam = ms.encode(ms.Title(rt, dt), ms.Effects(rf, df), self.mt.TITLE_BUDGET, ms.FX_LAMBDA)["lam"]
        self.assertEqual(lam, self.mt.TITLE_LAMBDA)
        inc = (MSX / "sound.inc").read_text()
        ref = []
        for v in "abc":
            body = re.search(r"^title_%s:\n(.*?)\n\n" % v, inc, re.M | re.S).group(1)
            ref.append(bytes(int(x, 0) for line in body.splitlines() if line.strip().startswith("db ")
                             for x in line.strip()[3:].split(",")))
        got = self.mt.psg_version(self.gt, lam)["streams"]
        self.assertEqual(sum(len(x) for x in ref), 5990)
        self.assertEqual(got, ref)

    def test_fm_bin(self):
        ref = (MSX / "fm.bin").read_bytes()
        self.assertEqual(len(ref), 13238)
        _, enc = self.mt.fm_version(self.gt, self.mt.titm_drum_map(self.gt))
        self.assertEqual(enc["blob"], ref)


@unittest.skipUnless(HAVE_NUMPY, "needs numpy (the project's venv)")
@unittest.skipUnless(PUZL.exists() and (MSX / "pzm.bin").exists(), "PZM not converted (tools/msxtune.py)")
class PzmTests(unittest.TestCase):
    """Brainstorm's pzm.bin: its streams, sizes and effects; the conversion gives it again."""

    @classmethod
    def setUpClass(cls):
        import msxtune
        cls.mt = msxtune
        cls.blob = (MSX / "pzm.bin").read_bytes()
        cls.hd = msxtune.parse(cls.blob)

    def test_every_tune_stream_lasts_3000_ticks(self):
        T = [self.mt.stream_ticks(self.blob, o, k) for o, k in zip(self.hd["streams"], self.mt.KINDS)]
        self.assertEqual(T, [3000] * 11)
        self.assertEqual(self.hd["waves"] % 32, 0)          # (no waveform across a bank)

    def test_sizes_are_the_sound_reports(self):
        # (the sound report's sizes, SOUND.md 3.1: the same converters before the port)
        size = [stream_len(self.blob, o, {"scc": 0, "psg": 1, "fm": 2, "rhy": 3}[k])
                for o, k in zip(self.hd["streams"], self.mt.KINDS)]
        self.assertEqual(size, [1285, 2026, 608, 2790, 763, 1688, 568, 532, 740, 810, 328])
        self.assertEqual(self.hd["W"], 7)

    def test_effects(self):
        e = self.hd["effects"]
        self.assertEqual({n: x["len"] for n, x in e.items()}, {3: 12, 4: 6, 5: 48, 6: 36})
        b, w = self.blob, self.hd["waves"]
        # effect 6, designed: one record each, the SCC's pulse (8 of 32 high) at 50 Hz, volume 8;
        # the PSG's square at 50 Hz, level 13
        so, po = e[6]["scc"], e[6]["psg"]
        self.assertEqual(b[so:so + 6], bytes([36, 0x38, 2236 & 0xFF, 2236 >> 8, b[so + 4], 0]))
        self.assertEqual(b[w + 32 * b[so + 4]:w + 32 * b[so + 4] + 32], bytes([127] * 8 + [256 - 42] * 24))
        self.assertEqual(b[po:po + 5], bytes([36, 0x5D, 2237 & 0xFF, 2237 >> 8, 0]))

    def test_the_conversion_gives_the_blob_again(self):
        with tempfile.TemporaryDirectory() as d:
            self.mt.convert(Path(d), ROOT / "build" / "music", log=lambda *a: None)
            self.assertEqual((Path(d) / "pzm.bin").read_bytes(), self.blob)

    def test_rc2music_verify(self):
        try:
            import unicorn  # noqa: F401
        except ImportError:
            self.skipTest("needs Unicorn (the project's venv)")
        r = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "rc2music.py"), "--verify",
                            str(ROOT / "build" / "music" / "PZM_00.bin")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("tunes with a difference: 0", r.stdout)


if __name__ == "__main__":
    unittest.main()
