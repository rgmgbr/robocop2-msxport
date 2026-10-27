"""tools/msxtune.py (the routing step, Brainstorm's PZM) and tools/mkrom.py's part for it
(pzm.bin's checks, tune.inc's layout against msx/tune.asm).

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

import mkrom  # noqa: E402

try:
    import numpy  # noqa: F401
    HAVE_NUMPY = True
except ImportError:
    HAVE_NUMPY = False
MSX = ROOT / "build" / "msx"
TITM = ROOT / "build" / "music" / "TITM.json"
PUZL = ROOT / "build" / "extracted" / "files" / "PUZL_25.bin"


def equates(path: Path) -> dict[str, int]:
    out = {}
    for m in re.finditer(r"^(\w+):\s+equ (0x[0-9A-Fa-f]+|\d+)\b", path.read_text(), re.M):
        out[m.group(1)] = int(m.group(2), 0)
    return out


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


def stream(ticks: int, ctl: int, extra: bytes = b"") -> bytes:
    """One record of `ticks` ticks (ctl and its fields), the end marker."""
    return bytes([ticks, ctl]) + extra + b"\x00"


def blob(T: int = 10, waves: int = 2, bad_align: bool = False, wave_no: int = 1) -> bytes:
    """A small pzm.bin in tools/msxtune.py's layout (mkrom.pzm_parse)."""
    streams = ([stream(T, 0x3F, bytes([1, 0, wave_no]))] * 3 + [stream(T, 0x0F)]
               + [stream(T, 0x0F)] * 3 + [stream(T, 0x01)] + [stream(T, 0x0F)] * 3)
    body, offs = bytearray(), []
    for s in streams:
        offs.append(mkrom.PZM_HEADER + len(body))
        body += s
    body += bytes(-(mkrom.PZM_HEADER + len(body)) % 32 + (1 if bad_align else 0))
    w_off = mkrom.PZM_HEADER + len(body)
    body += bytes(32 * waves)
    p_off = mkrom.PZM_HEADER + len(body)
    body += bytes(range(14))
    e_off = mkrom.PZM_HEADER + len(body)
    s_o, p_o = e_off + 9, e_off + 9 + 6
    body += bytes([12]) + s_o.to_bytes(3, "little") + bytes([5]) + p_o.to_bytes(3, "little") + bytes([4])
    body += stream(5, 0x38, bytes([2, 0, 0]))[:-1] + b"\x00" + stream(4, 0x0F)
    head = b"".join(o.to_bytes(3, "little") for o in offs + [w_off, p_off, e_off])
    head += bytes([waves, T & 0xFF, T >> 8, 3, 1])
    return head + bytes(body)


class MkromTuneTests(unittest.TestCase):
    def test_parse_and_check_a_small_blob(self):
        b = blob()
        hd = mkrom.pzm_parse(b)
        self.assertEqual((hd["T"], hd["W"], hd["fx0"], hd["fxn"]), (10, 2, 3, 1))
        self.assertEqual(hd["effects"][0]["len"], 12)
        self.assertEqual((hd["effects"][0]["scc_ticks"], hd["effects"][0]["psg_ticks"]), (5, 4))
        mkrom.pzm_check(b)                                   # (no exception)

    def test_check_refuses_what_tune_asm_cannot_play(self):
        with self.assertRaises(SystemExit):
            mkrom.pzm_check(blob(bad_align=True))           # a waveform across a bank
        with self.assertRaises(SystemExit):
            mkrom.pzm_check(blob(wave_no=2))                # past the table
        b = bytearray(blob())
        b[mkrom.pzm_parse(bytes(b))["streams"][5]] = 9      # a stream shorter than the tune
        with self.assertRaises(SystemExit):
            mkrom.pzm_check(bytes(b))
        b = bytearray(blob())
        b[mkrom.pzm_parse(bytes(b))["fx"]] = 254            # an effect 254 ticks long: busy for 255
        mkrom.pzm_check(bytes(b))
        b[mkrom.pzm_parse(bytes(b))["fx"]] = 255            # 255: busy for 256 (tn_go's byte)
        with self.assertRaises(SystemExit):
            mkrom.pzm_check(bytes(b))

    def test_the_effect_voice_is_busy_one_tick_past_its_length(self):
        # $1822C's rule as the 68000 runs it: channel 3 stays busy until the tick that reads the
        # effect's end (its length after its first), and PUZL's request comes before the tick
        # (PzmTests.test_effects_hold_channel_3_one_tick_past_their_length): tn_go counts the
        # length + 1 from its own tick
        asm = (ROOT / "msx" / "tune.asm").read_text()
        self.assertRegex(asm, r"\n\s+ld a,\(hl\)\n\s+inc a\b[^\n]*\n\s+ld \(tn_busy\),a")

    def test_tune_inc_holds_tune_asm_layout(self):
        # pz_desc's bytes up to pz_fx are TD_SIZE (tune.asm checks it at build time too), each
        # effect TF_SIZE; the streams' and waveforms' banks and addresses in the 8000h window
        eq = equates(ROOT / "msx" / "tune.asm")
        text = mkrom.tune_inc(blob(), 86)
        def size(part: str) -> int:
            n = 0
            for line in part.splitlines():
                line = line.split(";")[0].strip()
                if line.startswith("db "):
                    n += len(line[3:].split(","))
                elif line.startswith("dw "):
                    n += 2 * len(line[3:].split(","))
            return n
        desc = text.split("pz_desc:")[1].split("pz_fx:")[0]
        fx = text.split("pz_fx:")[1]
        self.assertEqual(size(desc), eq["TD_SIZE"])
        self.assertEqual(size(fx), eq["TF_SIZE"])
        self.assertEqual((eq["TD_FM"], eq["TD_PSG"], eq["TD_TICKS"], eq["TD_PATCH"], eq["TD_FX"], eq["TD_WAVES"]),
                         (12, 24, 33, 35, 49, 53))
        self.assertIn("db 86\n        dw 0x802F", text)     # (the first stream at offset 47)

    def test_nothing_of_the_tunes_in_the_fixed_area_but_fx_tk_operand(self):
        # the fixed area is as without the tunes (no option set loses room), fx_tk's operand
        # aside: ld hl,fx_tkd instead of ld hl,fx_tick, the same size, on into fx_bk. The dispatch
        # (fx_tkd) is in BANK_MUSIC after the title's code and tables; the stage's two entries in
        # BANK_PUZL: the set-up's tail through mus_call, the request a routine of its own
        asm = (ROOT / "msx" / "rc2.asm").read_text()
        self.assertNotIn("sndtune", asm)
        self.assertRegex(asm, r'include "rowtab.inc"\n\ncode_end:')
        self.assertRegex(asm, r'include "voice.inc".*\n(.*\n){2}\s+include "tune.inc".*\n\s+include "tune.asm"')
        self.assertRegex((ROOT / "msx" / "sound.asm").read_text(), r"\nfx_tk:\s+ld hl,fx_tkd\nfx_bk:")
        tune = (ROOT / "msx" / "tune.asm").read_text()
        self.assertRegex(tune, r"\nfx_tkd: ld a,\(snd_v \+ SV_CH\)\n")
        self.assertRegex(tune, r"\n\s+else\b[^\n]*\ntn_pzm:\s+equ mus_stop\b[^\n]*\nfx_tkd:\s+equ fx_tick\b")
        puzl = (ROOT / "msx" / "puzl.asm").read_text()
        self.assertRegex(puzl, r"\n(\w+:)?\s+ld hl,tn_pzm\b[^\n]*\n\s+jp mus_call\b")
        self.assertRegex(puzl, r"\nsnd_bfx:\n\s+ld hl,tn_req\n")


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

    def test_effects_hold_channel_3_one_tick_past_their_length(self):
        # tools/rc2music.py's model of PZM's player (--verify: 0 differences): started through
        # $1822C, an effect of length L keeps channel 3's flags ($18126) set through L + 1 ticks,
        # until the tick that reads its end; msx/tune.asm tn_go keeps the effect voice busy as long
        import rc2music
        data = (ROOT / "build" / "music" / "PZM_00.bin").read_bytes()
        lay = rc2music.locate(data)
        held = {}
        for n in self.hd["effects"]:
            p = rc2music.Player(data, lay)
            p.init()
            p.stop_all()
            self.assertTrue(p.start_sfx(n))
            held[n] = 0
            while p.m.rw(lay["structs"][3]) and held[n] < 300:
                p.play()
                held[n] += 1
        self.assertEqual(held, {n: x["len"] + 1 for n, x in self.hd["effects"].items()})

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
