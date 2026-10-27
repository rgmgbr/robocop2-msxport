"""tools/msxtune.py (the routing step, Brainstorm's PZM, the shooting range's FRM), msxscc.py's
octave rule and tools/mkrom.py's part for them (pzm.bin's checks, tune.inc's layout against
msx/tune.asm).

The regression the routing rests on: through it TITM tune 1 gives today's conversions byte for
byte (scc.bin 25,803 B, fm.bin 13,238 B, the PSG title 5,990 B at msxsound's lambda for the
Makefile's budget). Those tests need numpy (the project's venv: ~/.venvs/msxports/bin/python -I -m
unittest discover -s tests -p test_msxtune.py) and the converted files (make msx; frm.bin:
tools/msxtune.py --frm); without them they are skipped. The OPLL conversion fits patches: about
three minutes in all."""
import hashlib
import re
import struct
import subprocess
import sys
import tempfile
import types
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
FRNG = ROOT / "build" / "extracted" / "files" / "FRNG_15.bin"
FRM_SHA256 = "93876996266513bfdbcbf7bf8f3a0a10cd0a6dde00f6f96109c947b867da2f34"    # FRM_00.bin


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

    def test_the_tune_tick_0_waits_for_the_stage_next_pass(self):
        # the 68000 ticks PZM inside PUZL's pass, after that pass's request ($17794, then $17212),
        # and the stop all and tune 1 end a board's set-up: its first tick plays tune 1's tick 0 with
        # the effect the next pass asks for (5 at boards 1-3). tn_start saves the pass counter's low
        # byte and sets tn_hold; fx_tkd holds the tune's ticks until the counter moved, then clears
        # tn_hold and goes on into tn_tick
        tune = (ROOT / "msx" / "tune.asm").read_text()
        start = tune.split("\ntn_start:")[1].split("\ntn_fm:")[0]
        self.assertRegex(start, r"\n\s+ld a,\(pzv_frame\)[^\n]*\n\s+ld \(tn_hpz\),a[^\n]*\n\s+ld a,1\n"
                                r"\s+ld \(tn_hold\),a\n\s+ei\n\s+ret\n")
        disp = tune.split("\nfx_tkd: ")[1].split("\ntn_tick:")[0]
        self.assertRegex(disp, r"\n\s+jr z,fxd_t\n(.*\n)+fxd_t:\s+ld hl,tn_hold\n\s+ld a,\(hl\)\n\s+or a\n"
                               r"\s+jp z,tn_tick\n\s+inc hl[^\n]*\n\s+ld a,\(pzv_frame\)\n\s+cp \(hl\)\n"
                               r"\s+ret z[^\n]*\n\s+dec hl\n\s+ld \(hl\),0[^\n]*\n\n(;[^\n]*\n)*;[^\n]*$")
        inc = equates(ROOT / "msx" / "msx.inc")
        self.assertEqual(inc["tn_hpz"], inc["tn_hold"] + 1)

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

    def test_the_octave_rule_leaves_the_title_alone(self):
        # TITM's notes never pass N 3,329: with msxscc's octave rule on, scc.bin stays byte for byte
        res = self.mt.scc_version(self.gt, octave_up=True)
        self.assertEqual(res["raised"], [[], [], []])
        self.assertEqual(res["blob"], (MSX / "scc.bin").read_bytes())


@unittest.skipUnless(HAVE_NUMPY, "needs numpy (the project's venv)")
class OctaveRuleTests(unittest.TestCase):
    """msxscc.SccVoice's octave rule on a synthetic voice: a sample of 32 bytes a cycle, so that
    N + 1 = AUDxPER."""

    @staticmethod
    def voice(pers: list[int], keyons: list[int], octave_up: bool) -> list[int]:
        import numpy as np
        import msxscc
        T = len(pers)
        inst = types.SimpleNamespace(energy=lambda a, b: float(b - a))
        ch = types.SimpleNamespace(
            per=np.array(pers, np.int64), ins=np.array([0 if p else -1 for p in pers]),
            amp=np.array([1.0 if p else 0.0 for p in pers]), keyon=np.array([t in keyons for t in range(T)]),
            vol=np.full(T, 64), insts={0: inst}, span=lambda t: (0.0, 64.0))
        title = types.SimpleNamespace(chans=[ch], T=T, pitch={0: (32.0, 1.0)})
        waves = {0: types.SimpleNamespace(number=0, rms=0.5)}
        return [int(n) for n in msxscc.SccVoice(title, 0, waves, octave_up).per]

    def test_clamp_by_default_octaves_up_when_asked(self):
        # notes (a key-on or silence starts one): 5000 (one octave up), 9000 (two), 3000 (in range),
        # a slide 4000-4200 that passes 4096 on its last tick (the whole note an octave up)
        pers = [5000, 5000, 5000, 9000, 9000, 0, 3000, 3000, 4000, 4096, 4200]
        keyons = [0, 3, 6, 8]
        self.assertEqual(self.voice(pers, keyons, False),
                         [4095, 4095, 4095, 4095, 4095, 0, 2999, 2999, 3999, 4095, 4095])
        self.assertEqual(self.voice(pers, keyons, True),
                         [2499, 2499, 2499, 2249, 2249, 0, 2999, 2999, 1999, 2047, 2099])

    def test_a_note_ends_at_silence_or_a_key_on(self):
        # the same period after a silent tick or a key-on is another note: only the one below
        # the range moves
        self.assertEqual(self.voice([3000, 0, 5000, 3000], [0, 2, 3], True), [2999, 0, 2499, 2999])
        self.assertEqual(self.voice([5000, 3000], [0], True), [2499, 1499])


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

    def test_no_effect_entry_sets_the_psg_format_flag(self):
        # bit 7 of an effect's SCC ticks byte flags a PSG-format stream (FRM's effect 2): PZM's
        # effects are all SCC streams under 128 ticks, so their entries keep their bytes
        for n, e in self.hd["effects"].items():
            self.assertFalse(e["scc_psg"])
            self.assertEqual(self.blob[self.hd["fx"] + 9 * (n - self.hd["fx0"]) + 4], e["scc_ticks"])

    def test_the_octave_rule_leaves_pzm_alone(self):
        # PZM's notes never pass N 2,654: with msxscc's octave rule on, its SCC streams are
        # pzm.bin's
        mt = self.mt
        rep, data = mt.load_pzm(ROOT / "build" / "music")
        with mt.converter_constants(-1, {}):
            gt = mt.RoutedTitle(mt.Routing(rep, data, mt.PZM_TUNE, drums=set(mt.PZM_DRUMS), speech=set()))
            res = mt.scc_version(gt, octave_up=True)
        self.assertEqual(res["raised"], [[], [], []])
        so = [res["blob"][3 * k] | res["blob"][3 * k + 1] << 8 | res["blob"][3 * k + 2] << 16 for k in range(5)]
        for k in range(4):
            o = self.hd["streams"][k]
            self.assertEqual(self.blob[o:o + so[k + 1] - so[k]], res["blob"][so[k]:so[k + 1]])


def assemble_inputs(fx_ticks: int, psg_format: bool):
    """The smallest parts tools/msxtune.py's assemble takes: a tune of 4 ticks (one record per
    stream), one effect (3) whose SCC-mode stream lasts fx_ticks ticks, in the PSG format or not."""
    import numpy as np
    def offs(parts: list[bytes], first: int) -> tuple[list[int], bytes]:
        out, pos = [], first
        for p in parts:
            out.append(pos)
            pos += len(p)
        return out, b"".join(parts)
    s = [stream(4, 0x3F, bytes([1, 0, 0]))] * 3 + [stream(4, 0x0F)] + [bytes(32)]
    so, sb = offs(s, 15)
    scc = {"blob": b"".join(o.to_bytes(3, "little") for o in so) + sb}
    f = [stream(4, 0x0F)] * 3 + [stream(4, 0x01)] + [bytes(range(14))]
    fo, fb = offs(f, 0)
    fmv = {"offs": fo, "blob": fb}
    psg = {"streams": [stream(4, 0x0F)] * 3}
    body = stream(fx_ticks, 0xAF, bytes([29])) if psg_format else stream(fx_ticks, 0x3F, bytes([1, 0, 0]))
    fx_scc = {3: {"bytes": body, "ticks": fx_ticks, "psg": psg_format}}
    fx_psg = {3: {"bytes": stream(2, 0x0F), "ticks": 2}}
    return scc, fmv, psg, fx_scc, fx_psg, {3: 140}, np.zeros((1, 32), np.int8)


@unittest.skipUnless(HAVE_NUMPY, "needs numpy (the project's venv)")
class EffectFlagTests(unittest.TestCase):
    """The effect table's PSG-format flag (bit 7 of the SCC ticks byte), on assemble's smallest
    blob."""

    def test_the_flag_and_the_ticks(self):
        import msxtune
        for fmt in (False, True):
            b = msxtune.assemble(*assemble_inputs(6, fmt), 4)
            hd = msxtune.parse(b)
            e = hd["effects"][3]
            self.assertEqual((e["scc_ticks"], e["scc_psg"], e["psg_ticks"], e["len"]), (6, fmt, 2, 140))
            self.assertEqual(b[hd["fx"] + 4], 0x86 if fmt else 0x06)
            mkrom.pzm_parse(b)                               # (the layout mkrom reads)

    def test_a_stream_of_128_ticks_is_refused(self):
        import msxtune
        msxtune.assemble(*assemble_inputs(127, False), 4)
        with self.assertRaises(SystemExit):
            msxtune.assemble(*assemble_inputs(128, False), 4)


@unittest.skipUnless(HAVE_NUMPY, "needs numpy (the project's venv)")
@unittest.skipUnless(FRNG.exists() and (MSX / "frm.bin").exists()
                     and (ROOT / "build" / "music" / "FRM_00.bin").exists(),
                     "FRM not converted (tools/msxtune.py --frm)")
class FrmTests(unittest.TestCase):
    """The shooting range's frm.bin: FRNG's player copy extracted, its streams, sizes and effects;
    the conversion gives it again."""

    @classmethod
    def setUpClass(cls):
        import msxtune
        cls.mt = msxtune
        cls.blob = (MSX / "frm.bin").read_bytes()
        cls.hd = msxtune.parse(cls.blob)
        cls.frm = (ROOT / "build" / "music" / "FRM_00.bin").read_bytes()

    def frng(self) -> bytes:
        import bytekiller
        return bytekiller.decrunch(FRNG.read_bytes())

    def test_the_extraction(self):
        # FRNG decrunched, $20000 on moved to $18000: the sound report's FRM_00.bin; record 0
        # ($18B96) points at the 22-byte sine at $18D88 (start and loop), TITM's
        mt = self.mt
        frm = mt.extract_frm(self.frng(), mt.MU1.read_bytes(), mt.TITM.read_bytes())
        self.assertEqual(frm, self.frm)
        self.assertEqual(hashlib.sha256(frm).hexdigest(), FRM_SHA256)
        self.assertEqual(len(frm), 0x485DA - 0x20000)
        self.assertEqual(frm[0xB96:0xBA6].hex(), "002100018d88000b00018d88000b0000")
        self.assertEqual(frm[0xD88:0xD9E], mt.TITM.read_bytes()[0xD88:0xD9E])

    def test_the_extraction_refuses_what_is_not_the_player(self):
        mt = self.mt
        frng = bytearray(self.frng())
        mu1, titm = mt.MU1.read_bytes(), mt.TITM.read_bytes()
        bad = bytearray(frng)
        bad[mt.FRM_AT - mt.FRNG_AT + 0x400] ^= 1           # a code byte ($18400) not MU1's
        with self.assertRaises(SystemExit):
            mt.extract_frm(bytes(bad), mu1, titm)
        bad = bytearray(frng)
        struct.pack_into(">I", bad, mt.FRM_AT - mt.FRNG_AT + 0xB98, 0x28D88)    # record 0 elsewhere
        with self.assertRaises(SystemExit):
            mt.extract_frm(bytes(bad), mu1, titm)
        mt.extract_frm(bytes(frng), mu1, titm)              # (no exception)

    def test_every_tune_stream_lasts_5999_ticks(self):
        T = [self.mt.stream_ticks(self.blob, o, k) for o, k in zip(self.hd["streams"], self.mt.KINDS)]
        self.assertEqual(T, [5999] * 11)
        self.assertEqual(self.hd["T"], 5999)
        self.assertEqual(self.hd["waves"] % 32, 0)          # (no waveform across a bank)

    def test_sizes(self):
        # the sound report's (SOUND.md 3.1) but for SCC voice 2: the octave rule merges its ten
        # raised notes with the bass's own notes an octave up (8 B less), which the waveforms'
        # alignment takes back: 39,341 B, 5 banks
        size = [stream_len(self.blob, o, {"scc": 0, "psg": 1, "fm": 2, "rhy": 3}[k])
                for o, k in zip(self.hd["streams"], self.mt.KINDS)]
        self.assertEqual(size, [4584, 4227, 5612, 2078, 5748, 5139, 5092, 536, 2380, 2140, 1362])
        self.assertEqual(self.hd["W"], 5)
        self.assertEqual(len(self.blob), 39341)
        self.assertNotIn(b"OPLL", self.blob)

    def test_effects(self):
        import msxsccfx as sx
        e = self.hd["effects"]
        self.assertEqual((self.hd["fx0"], self.hd["fxn"]), (2, 3))
        self.assertEqual({n: x["len"] for n, x in e.items()}, {2: 6, 3: 16, 4: 12})
        self.assertEqual({n: x["scc_psg"] for n, x in e.items()}, {2: True, 3: False, 4: False})
        # effect 2, the shot: noise on PSG voice B at the SCC music's scale (levels 12 and 11, a
        # tone gating the noise on 3 ticks), and the PSG alone's noise at level 15
        st, n = sx.decode_psg(self.blob, e[2]["scc"], 6)
        self.assertEqual(n, 6)
        self.assertTrue(all(x[2] for x in st))              # noise on every tick
        self.assertEqual([x[0] for x in st], [12, 11, 11, 11, 11, 12])
        self.assertEqual(sum(x[1] for x in st), 3)
        st, n = sx.decode_psg(self.blob, e[2]["psg"], 6)
        self.assertEqual((n, {x[:3] for x in st}), (6, {(15, False, True)}))
        # effects 3 and 4: the sine (the table's last waveform) on SCC channel 3, volume 3
        for k, T in ((3, 16), (4, 12)):
            st, n, loads = sx.decode_scc(self.blob, e[k]["scc"], self.hd["W"], T)
            self.assertEqual((n, loads, {x[0] for x in st}, {x[2] for x in st}), (T, 1, {3}, {4}))

    def test_the_bass_notes_below_the_scc_play_an_octave_up(self):
        # #1's ten notes at 25.09 Hz (AUDxPER 670, 212.97 bytes a cycle: N + 1 = 4459.04) play at
        # N 2229 (50.16 Hz, 0.4 cents under twice that), not clamped at N 4095 (147 cents sharp)
        import msxscc
        st = msxscc.decode_scc(self.blob, self.hd["streams"][2], 5999)
        for t in (1347, 1383, 1419, 1455, 1479, 5187, 5223, 5259, 5295, 5319):
            self.assertEqual(st[t][1:], (2229, 0))
        self.assertLessEqual(max(x[1] for v in range(3) for x in msxscc.decode_scc(
            self.blob, self.hd["streams"][v], 5999) if x[0]), 4095)

    def test_effects_hold_channel_3_one_tick_past_their_length(self):
        # as PZM's (tn_go: busy for L + 1 ticks), on rc2music.py's model of FRM's player
        import rc2music
        lay = rc2music.locate(self.frm)
        held = {}
        for n in self.hd["effects"]:
            p = rc2music.Player(self.frm, lay)
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
            res = self.mt.convert_frm(Path(d), ROOT / "build" / "music", log=lambda *a: None)
            self.assertEqual((Path(d) / "frm.bin").read_bytes(), self.blob)
        self.assertEqual(res["scc"]["raised"][2], [(t, n, 1) for t, n in (
            (1347, 36), (1383, 12), (1419, 36), (1455, 24), (1479, 12),
            (5187, 36), (5223, 12), (5259, 36), (5295, 24), (5319, 12))])

    def test_rc2music_verify(self):
        try:
            import unicorn  # noqa: F401
        except ImportError:
            self.skipTest("needs Unicorn (the project's venv)")
        r = subprocess.run([sys.executable, "-I", str(ROOT / "tools" / "rc2music.py"), "--verify",
                            str(ROOT / "build" / "music" / "FRM_00.bin")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ticks compared: 12600, tunes with a difference: 0", r.stdout)


if __name__ == "__main__":
    unittest.main()
