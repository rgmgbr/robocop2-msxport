"""tools/bstest/fxcheck.py offline (docs/LEVEL2.md 4.3, level 2's step 21): a synthetic ROM image (the
effects' tables and streams in their banks), logs made through the model itself, then the check, its
mutations and the engine's rules. The model against the real engine: fxcheck.py check on fxlog.tcl's
logs in openMSX (docs/HARNESS.md 5.23)."""
import contextlib
import importlib.util
import io
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fxcheck", ROOT / "tools" / "bstest" / "fxcheck.py")
fx = importlib.util.module_from_spec(spec)
sys.modules["fxcheck"] = fx
spec.loader.exec_module(fx)

SCCFX, INPUT, MUSIC = 2, 3, 4
L = {"SCCFX_BANK": SCCFX, "BANK_INPUT": INPUT, "BANK_MUSIC": MUSIC, "GUN_FX": 3, "GUN_TAB": 0x8400,
     "SND_SFX_N": 2, "snd_sfx": 0xA000, "fx_waves": 0xA100, "TN_MARK": 0xFE, "SCC_WAVE": 0x9800,
     "SCC_FREQ": 0x9880, "SCC_VOL": 0x988A, "SCC_ON": 0x988F, "mus_v": 0xC210, "fx_pv": 0xC270,
     "fx_wc": 0xC2A0, "fx_act": 0xC20D, "fx_son": 0xC20E, "fx_tmp": 0xC20C, "snd_v": 0xCF00,
     "snd_div": 0xCF1E, "snd_mix": 0xCF1F, "snd_last": 0xCF20, "snd_qh": 0xCF21, "snd_qt": 0xCF22,
     "snd_q": 0xCF23, "mus_on": 0xC202, "mus_speak": 0xC204, "mus_att": 0xC2B4, "mus_fade": 0xC2B3,
     "mus_mode": 0xC201, "mus_dc": 0xC209, "scc_pg2": 0xC20A, "scc_wb": 0xC250, "cpu_cur": 0xC2A7,
     "INPUT_SCRIPT": 1, "DIAG": 0}


def rom_image() -> bytes:
    """Effect 1: channel 1, a tonal part (two records, the second with a waveform) and a noise
    part; effect 2: channel 3, tonal only; the gun (3-5): channels 0-2, a record each. The PSG
    player's effects 1 (channel 1) and 2 (channel 3), and the gun's three streams."""
    rom = bytearray(b"\xff" * (5 * 0x2000))
    b = SCCFX * 0x2000

    def put(at, data):
        rom[at:at + len(data)] = bytes(data)

    def entry(n, ch, tonal, noise):
        put(b + 4 + 7 * (n - 1), [ch, tonal & 255, tonal >> 8 & 255, 0, noise & 255, noise >> 8 & 255, 0])
    entry(1, 1, 0x100, 0x200)
    entry(2, 3, 0x300, 0)
    for k in range(3):
        entry(3 + k, k, 0x340 + 8 * k, 0)
        put(b + 0x340 + 8 * k, [2, 0x10 | 9, 0x40 + k, 1, 0])          # 2 ticks, period, volume 9
    put(b + 0x100, [3, 0x30 | 12, 0x34, 0x02, 1, 2, 0x20 | 8, 1, 0])  # waveform 1 twice: loaded once
    put(b + 0x200, [2, 0xC0 | 0x20 | 7, 0x10, 0x00, 0x1F, 1, 0x20 | 5, 0])
    put(b + 0x300, [4, 0x30 | 15, 0x00, 0x01, 0, 0])
    i = INPUT * 0x2000
    put(i, [0x00, 0xA2, 1, 0x40, 0xA2, 3])                            # snd_sfx: streams A200h, A240h
    put(i + 0x200, [2, 0x40 | 0x10 | 10, 0x21, 0x01, 3, 0x10 | 6, 0])
    put(i + 0x240, [5, 0x80 | 0x20 | 13, 0x0F, 0])
    put(b + 0x400, [0x40, 0x84, 0x48, 0x84, 0x50, 0x84, 0, 0, 0, 0, 0, 0])    # GUN_TAB
    for k in range(3):
        put(b + 0x440 + 8 * k, [3, 0x40 | 0x10 | (8 + k), 0x80, 0x00, 0])
    m = MUSIC * 0x2000
    put(m + 0x100, list(range(32)) + [255 - x for x in range(32)])   # fx_waves 0 and 1
    return bytes(rom)


def ram0(mode=1, pg2=0) -> bytearray:
    ram = bytearray(0x1000)
    e = fx.Engine(rom_image(), L, ram, 0)
    e.setv("mus_mode", mode)
    e.setv("scc_pg2", pg2)
    e.setv("snd_mix", 0xBF)
    for b in range(3):
        e.w8(e.sv(b) + fx.SV_CH, 0xFF)
    for b in range(4):
        e.w8(L["fx_wc"] + b, 0xFF)
    return e.ram


def make_log(script, mode=1, pg2=0, rg9=2) -> list[str]:
    """A log as fxlog.tcl writes it, its writes the model's: SCRIPT a list of ("F", n), ("Q", a),
    ("V", [items taken: "S n", "G", "X"], tick?), ("Y",), ("Z",)."""
    rom = rom_image()
    ram = ram0(mode, pg2)
    e = fx.Engine(rom, L, ram, rg9)
    out = [f"I {bytes(ram).hex()} {rg9:02x}"]
    kind = "x" if pg2 else "c"

    def emit(ws):
        for w in ws:
            out.append(f"C {w[1]:04x} {w[2]} {kind}" if w[0] == "C" else f"{w[0]} {w[1]} {w[2]}")
    for item in script:
        k = item[0]
        if k == "F":
            out.append(f"F {item[1]}")
        elif k == "Q":
            out.append(f"Q {item[1]}")
            e.queue_put(item[1])
            if item[1] == fx.SQ_STOP:
                out.append("Z")
                emit(e.run("Z", None)[0])
        elif k == "Y":
            out.append("Y")
            emit(e.run("Y", None)[0])
        elif k == "V":
            out.append("V")
            tick = e.tick_due()
            for t in item[1]:
                e.queue_take()
                if t.startswith("S"):
                    out.append(t)
                    emit(e.run("S", int(t.split()[1]))[0])
                else:
                    out.append(t)
                    emit(e.run(t, None)[0])
            if tick:
                out.append("T")
                emit(e.run("T", None)[0])
            out.append("W")
    out.append(f"E {bytes(e.ram).hex()} {rg9:02x}")
    return out


class FxcheckTest(unittest.TestCase):
    def run_lines(self, lines, **kw):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "log.txt"
            p.write_text("\n".join(lines) + "\n")
            c = fx.Checker(rom_image(), L)
            ok = c.check(fx.parse_log(p), **kw)
            return ok, c

    def script(self):
        s = [("F", 0), ("Q", 1), ("V", ["S 1"]), ("V", []), ("F", 1), ("Q", 2), ("V", ["S 2"])]
        s += [("V", [])] * 6 + [("F", 2), ("Q", 1), ("V", ["S 1"]), ("Q", 0xFD), ("V", ["G"])]
        s += [("V", [])] * 5 + [("Y",), ("Q", 0xFF), ("V", ["X"]), ("V", [])]
        return s

    def test_scc_log_passes_and_mutations_fail(self):
        for pg2 in (0, 0x10):
            lines = make_log(self.script(), 1, pg2)
            ok, c = self.run_lines(lines, expect="ext" if pg2 else "scc")
            self.assertTrue(ok, c.errors)
            muts = fx.mutations(lines)
            self.assertGreaterEqual(len(muts), 10)
            for name, ml in muts:
                self.assertFalse(self.run_lines(ml)[0], name)

    def test_psg_log_passes_and_mutations_fail(self):
        lines = make_log(self.script(), 0, 0)
        ok, c = self.run_lines(lines, expect="psg")
        self.assertTrue(ok, c.errors)
        self.assertFalse(any(l.startswith("C ") for l in lines))
        for name, ml in fx.mutations(lines):
            self.assertFalse(self.run_lines(ml)[0], name)

    def test_expect_and_wrong_chip(self):
        lines = make_log(self.script(), 1, 0)
        self.assertFalse(self.run_lines(lines, expect="psg")[0])
        bad = [l[:-1] + "x" if l.startswith("C ") else l for l in lines]
        self.assertFalse(self.run_lines(bad)[0])

    def test_waveform_loaded_once_and_scc_writes(self):
        e = fx.Engine(rom_image(), L, ram0(1, 0), 2)
        w, res = e.run("S", 1)
        self.assertEqual(res, "started")
        waves = [x for x in w if x[0] == "C" and 0x9820 <= x[1] < 0x9840]
        self.assertEqual([x[2] for x in waves], [255 - i for i in range(32)])     # waveform 1 on channel 1
        self.assertIn(("C", 0x9882, 0x34), w)
        self.assertIn(("C", 0x9883, 0x02), w)
        self.assertIn(("C", 0x988B, 12), w)
        self.assertEqual(w[-1], ("C", 0x988F, 0x0F))                            # fx_son: channels 0-3 on
        for _ in range(3):
            w, _ = e.run("T", None)
        self.assertFalse(any(0x9800 <= x[1] < 0x9880 for x in w if x[0] == "C"))   # (the channel has it)
        self.assertIn(("C", 0x988B, 8), w)

    def test_psg_noise_part_and_mixer(self):
        e = fx.Engine(rom_image(), L, ram0(1, 0), 2)
        w, _ = e.run("S", 1)
        psg = [x[1:] for x in w if x[0] == "P"]
        # (the record's tone off: no period written; the noise on: R6, the mixer's noise bit B cleared)
        self.assertEqual(psg, [(9, 7), (6, 0x1F), (7, 0xAF)])

    def test_priority_rule_on_both_players(self):
        # the PSG player: while channel 3 plays effect 2, effect 1 (channel 1, lower) is refused
        e = fx.Engine(rom_image(), L, ram0(0, 0), 2)
        self.assertEqual(e.run("S", 2)[1], "started")
        self.assertEqual(e.run("S", 1)[1], "refused")
        # music.asm (the SCC): its rule only for channel 3's requests (docs/level2/HANDOFF.md step 21,
        # open issue 1): effect 1 plays, counted as outside the original's rule
        e = fx.Engine(rom_image(), L, ram0(1, 0), 2)
        self.assertEqual(e.run("S", 2)[1], "started")
        self.assertEqual(e.run("S", 1)[1], "started")
        self.assertEqual(e.scope, [1])

    def test_channel3_voice_choice(self):
        e = fx.Engine(rom_image(), L, ram0(0, 0), 2)
        e.w8(e.sv(2) + fx.SV_LEFT, 9)
        e.w8(e.sv(1) + fx.SV_LEFT, 4)
        e.w8(e.sv(0) + fx.SV_LEFT, 4)
        e.run("S", 2)
        self.assertEqual(e.r8(e.sv(1) + fx.SV_CH), 3)                       # the nearest its end, from C
        self.assertEqual(e.r8(e.sv(1) + fx.SV_LEFT), 5)

    def test_divider_60_hz(self):
        e = fx.Engine(rom_image(), L, ram0(), 0)
        self.assertEqual([e.tick_due() for _ in range(12)], [True] * 5 + [False] + [True] * 5 + [False])

    def test_queue_order_and_missing_tick(self):
        lines = make_log(self.script(), 1, 0)
        i = next(i for i, l in enumerate(lines) if l == "S 1")
        swapped = lines[:i] + ["S 2"] + lines[i + 1:]
        self.assertFalse(self.run_lines(swapped)[0])
        lines50 = make_log(self.script(), 1, 0, rg9=0)
        self.assertTrue(self.run_lines(lines50)[0])
        self.assertIn("T", lines50)

    def test_isr_inside_a_stop(self):
        lines = make_log([("F", 0), ("Q", 1), ("V", ["S 1"]), ("Q", 0xFF), ("V", ["X"])], 0, 0)
        z = lines.index("Z")
        # a VBLANK between sq_mute's first and second write (sq_mute's ei)
        moved = lines[:z + 2] + ["V", "T"] + [] + ["W"] + lines[z + 2:]
        ok, c = self.run_lines(moved)
        self.assertFalse(ok)                          # (that VBLANK's tick writes are missing)
        e = fx.Engine(rom_image(), L, ram0(0, 0), 2)  # with its own writes, it passes
        e.queue_put(1)
        e.queue_take()
        e.run("S", 1)
        e.queue_put(0xFF)
        e.run("Z", None)
        tw, _ = e.run("T", None)
        moved = lines[:z + 2] + ["V", "T"] + [f"P {w[1]} {w[2]}" for w in tw] + ["W"] + lines[z + 2:]
        ok, c = self.run_lines(moved)
        self.assertFalse(ok)                          # (the end state and the next tick shift)
        self.assertTrue(any("line" in x for x in c.errors))

    def test_text_screen_silence(self):
        s = [("F", 0), ("Q", 1), ("V", ["S 1"])]
        lines = make_log(s + [("Y",), ("Q", 0xFF), ("V", ["X"]), ("V", [])], 1, 0)
        y = lines.index("Y")
        lines = lines[:y] + ["B 98de"] + lines[y:-1] + ["b", lines[-1]]
        L2 = dict(L, txt_l2_brief=0x98DE)
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "log.txt"
            p.write_text("\n".join(lines) + "\n")
            c = fx.Checker(rom_image(), L2)
            self.assertTrue(c.check(fx.parse_log(p)), c.errors)
            self.assertTrue(any("txt_l2_brief" in n and "silent" in n for n in c.notes))
            noisy = lines[:-2] + ["P 8 5", lines[-2], lines[-1]]
            p.write_text("\n".join(noisy) + "\n")
            self.assertFalse(fx.Checker(rom_image(), L2).check(fx.parse_log(p)))

    def test_bench_rows_by_index(self):
        lines = make_log([("F", 0), ("Q", 1), ("V", ["S 1"]), ("F", 1), ("Q", 2), ("V", ["S 2"]), ("F", 2)], 0, 0)

        def row(gf, reqs):
            ram = bytearray(0xBEC)
            for i, a in reqs:
                ram[0x2C + i] = a
            return {"game_frame": gf, "ram": ram.hex()}
        rows = [row(0, [(1, 1)]), row(0, [(1, 2)]), row(1, [])]      # (game_frame restarted: a death)
        self.assertTrue(self.run_lines(lines, bench=rows)[0])
        rows[1] = row(0, [(1, 1)])
        self.assertFalse(self.run_lines(lines, bench=rows)[0])

    def test_visits(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.txt", Path(d) / "b.txt"
            a.write_text("N\nU 3 - 00ff -\nU 2 - 01ff -\n")
            b.write_text("N\nU 3 - 00ff -\nU 2 - 01ff -\n")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(fx.visits(a, b), 0)
                b.write_text("N\nU 3 - 00ff -\nU 2 - 02ff -\n")
                self.assertEqual(fx.visits(a, b), 1)

    def test_fxl_jobs_use_the_builds_of_hz_sh_fxbuilds(self):
        tcl = (ROOT / "tools" / "bstest" / "fxlog.tcl").read_text()
        body = tcl[tcl.index("proc fxl_jobs"):]
        used = set(re.findall(r"\b(l2\w*|pz\w+)\b(?= \{\}| scc| txt_)", body))
        used |= set(re.findall(r"\{(?:scc|ext|psg) (l2\w*) ", body))
        used |= set(re.findall(r"(?:scc|psg) (l2c\w*)\b", body))
        sh = (ROOT / "tools" / "bstest" / "hz.sh").read_text()
        built = set(re.findall(r'"(\w+) (?:\$T|PZ_TEST)', sh[sh.index("fxbuilds)"):]))
        self.assertEqual(built, {"l2", "l2x", "l2n", "l2c", "l2cn", "pz1", "pz2", "pz1n", "pz2n"})
        self.assertTrue(used <= built, used - built)
        self.assertIn("fxlog.tcl", (ROOT / "tools" / "bstest" / "load.tcl").read_text())

    def test_labels_and_command_line(self):
        with tempfile.TemporaryDirectory() as d:
            lab = Path(d) / "x.labels"
            lab.write_text("x.asm:1: warning: something\nsnd_v:\tequ $cf00\nGUN_FX:\tequ $002b\n")
            self.assertEqual(fx.read_labels(lab), {"snd_v": 0xCF00, "GUN_FX": 0x2B})
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(fx.main(["fxcheck.py"]), 2)
            self.assertEqual(fx.main(["fxcheck.py", "check", "a"]), 2)


if __name__ == "__main__":
    unittest.main()
