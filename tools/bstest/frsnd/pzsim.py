"""Scratch: Brainstorm's sound (msx/tune.asm, msx/puzl.asm's two entries) run on a ROM image in z80.py,
an offline complement to the emulator checks (int/EMU_PLAN.md), not a substitute.

The image's own code runs: the stage's calls (the set-up's tail bsu_t: tune 1 through mus_call;
snd_bfx, the pass's request; snd_stop) and the VBLANK interrupt's sound (snd_frame -> sndplay.asm
sq_frame -> sound.asm fx_tk -> tune.asm fx_tkd -> tn_tick), on a Konami SCC mapper model (the
windows' bank registers, the SCC's registers with 3Fh at 9000h), the PSG (ports A0h-A2h) and the
OPLL (7Ch, 7Dh), logged. The main program's passes are modelled: after a tick's requests the pass
counter $B00 + 1 (pz_frame), which releases the tune's tick 0 (tune.asm tn_hold: the first tick after
the stage's next pass). After every tick the chips' registers are compared with what pzm.bin's
streams say, decoded here in Python with the converters' decoders (tools/msxscc.py, msxsound.py,
msxfm.py, msxsccfx.py), independently of the Z80 code; the effects' schedule ($1822C's rule as the
68000 runs it, snd_bfx's merge) is modelled apart too (Sched), and the rule's edge is checked against
tools/rc2music.py's 68000 model itself (edges(): needs WORKTREE/build/music/PZM_00.bin, which
tools/msxtune.py writes).
Also checked: the interrupt rule (DE, IX, IY and the alternate registers kept by snd_frame), the
tune's end (every voice silent at its tick 3000), a board's restart, snd_stop with the PSG alone (no
more writes), a stop queued right before the tune's start (H7: tn_start lets it through first), 60 Hz,
the R800 (cpu_cur set: no OPLL write); the board's start (jingle(): the tune's tick 0 and effect 5 in
the same VBLANK at boards 1-3, tick 0 at the first tick after the first pass at every board, at 50 Hz
and at 60 Hz for every phase of the two dividers); the title after the stage (title_after(): the
title's chip writes equal a fresh machine's).
Images from before the hold (no tn_hold label) or before the entries moved (snd_tune in the fixed
area) still run: their tick 0 is the first tick after the set-up.

usage: pzsim.py WORKTREE ROM LABELS [--ticks N] [--only NAME,...]"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import z80  # noqa: E402

SENTINEL = 0x0000
MM_SCC, MM_FM, MM_RHY = 1, 2, 4


class Msx:
    """The bus: page 0 and 3 RAM, the cartridge's four 8 KiB windows (Konami SCC mapper: 5000h,
    7000h, 9000h, B000h select them), the SCC's registers at 9800h-98FFh while the 8000h window's
    bank is 3Fh, the PSG and the OPLL; every chip write logged with the instruction count."""

    def __init__(self, rom: bytes):
        self.rom = rom
        self.nb = len(rom) // 8192
        self.ram = bytearray(65536)
        self.win = [0, 1, 0, 0]
        self.scc = bytearray(256)
        self.psg = bytearray(16)
        self.psg_latch = 0
        self.opll = bytearray(64)
        self.opll_latch = 0
        self.log: list = []
        self.violations: list = []
        self.cpu = None

    def rb(self, a: int) -> int:
        if a < 0x4000 or a >= 0xC000:
            return self.ram[a]
        w = (a - 0x4000) >> 13
        if w == 2 and (self.win[2] & 0x3F) == 0x3F and 0x9800 <= a <= 0x98FF:
            return self.scc[a - 0x9800]
        bank = self.win[w] % self.nb
        return self.rom[bank * 8192 + (a & 0x1FFF)]

    def wb(self, a: int, v: int) -> None:
        if a < 0x4000 or a >= 0xC000:
            self.ram[a] = v
            return
        if 0x5000 <= a <= 0x57FF:
            self.win[0] = v
        elif 0x7000 <= a <= 0x77FF:
            self.win[1] = v
        elif 0x9000 <= a <= 0x97FF:
            self.win[2] = v
        elif 0xB000 <= a <= 0xB7FF:
            self.win[3] = v
        elif 0x9800 <= a <= 0x98FF and (self.win[2] & 0x3F) == 0x3F:
            self.scc[a - 0x9800] = v
            self.log.append(("scc", a - 0x9800, v))
            # (the store rule: registers by ld (nn),a; the waveform RAM by ldir too)
            pc = self.cpu.op_pc
            op = self.rb(pc)
            form = "ld (nn),a" if op == 0x32 else "ldir" if op == 0xED and self.rb(pc + 1) == 0xB0 else \
                "%02X at %04X" % (op, pc)
            if not (form == "ld (nn),a" or (form == "ldir" and a < 0x9880)):
                self.violations.append("SCC %04X stored by %s" % (a, form))

    def inp(self, p: int) -> int:
        if p == 0xA2:
            return self.psg[self.psg_latch] if self.psg_latch < 14 else 0xFF
        return 0xFF if p == 0xA8 else 0

    def outp(self, p: int, v: int) -> None:
        if p == 0xA0:
            self.psg_latch = v & 0x0F if v < 16 else 16
        elif p == 0xA1:
            if self.psg_latch < 16:
                self.psg[self.psg_latch] = v
                self.log.append(("psg", self.psg_latch, v))
                if self.psg_latch == 7 and (v & 0xC0) != 0x80:
                    self.violations.append("R7 = %02X: port A must stay an input, B an output" % v)
        elif p == 0x7C:
            self.opll_latch = v & 0x3F
        elif p == 0x7D:
            self.opll[self.opll_latch] = v
            self.log.append(("opll", self.opll_latch, v))


def labels(path: Path) -> dict[str, int]:
    out = {}
    for line in path.read_text().splitlines():
        if "\tequ $" in line:
            k, v = line.split(":\tequ $")
            out[k] = int(v, 16)
    return out


class Machine:
    def __init__(self, rom: bytes, lab: dict, mode: int, hz50: bool = True, irq_every: int = 0):
        self.L = lab
        self.bus = Msx(rom)
        self.cpu = z80.Z80(self.bus)
        self.bus.cpu = self.cpu
        self.irq_every = irq_every or 8000
        self.vblanks = 0
        self.ticks = 0                              # VBLANKs that ticked (sq_frame: 50 a second)
        self.tick_vbls: list[int] = []              # (their numbers: self.vblanks after each)
        self.on_tick = None
        r = self.bus.ram
        L = lab
        r[L["mus_mode"]] = mode
        r[L["cpu_cur"]] = 0
        r[L["snd_mix"]] = 0xBF
        r[L["snd_qh"]] = r[L["snd_qt"]] = 0
        for v in range(3):
            r[L["snd_v"] + 10 * v + 2] = 0          # SV_LEFT
            r[L["snd_v"] + 10 * v + 9] = 0xFF       # SV_CH
        for k in ("snd_div", "mus_on", "mus_dc", "mus_att", "mus_fade", "fx_act", "scc_pg2", "mus_speak"):
            r[L[k]] = 0
        r[L["act_8000"]] = L["BANK_FRONT"]
        r[L["act_a000"]] = L["BANK_PUZL"]
        r[0xFFE8] = 2 if hz50 else 0                # RG9SAV: bit 1 = 50 Hz
        self.bus.win = [0, 1, L["BANK_FRONT"], L["BANK_PUZL"]]
        self.bus.psg[7] = 0xBF

    def call(self, addr: int, a: int = 0, limit: int = 3_000_000, irq: bool = True, hl: int | None = None) -> None:
        cpu = self.cpu
        cpu.sp = 0xF300
        cpu.push(SENTINEL)
        cpu.pc = addr
        cpu.a = a
        if hl is not None:
            cpu.h, cpu.l = hl >> 8, hl & 0xFF
        n = since = 0
        while cpu.pc != SENTINEL:
            cpu.step()
            n += 1
            since += 1
            if irq and cpu.iff and self.irq_every and since >= self.irq_every:
                since = 0
                self.interrupt()
            if n > limit:
                raise RuntimeError("no return from %04X (pc %04X)" % (addr, cpu.pc))

    def interrupt(self) -> None:
        """The VBLANK's sound part as isr does it: tick + 1, then AF, BC and HL saved around
        snd_frame (iv_tick: jp snd_frame), the interrupts off meanwhile; the rule checked: the rest
        kept. A VBLANK that ticks (sndplay.asm sq_frame: at 60 Hz not every sixth) calls on_tick."""
        cpu = self.cpu
        r = self.bus.ram
        ticks = bool(r[0xFFE8] & 2) or r[self.L["snd_div"]] != 5
        r[self.L["tick"]] = (r[self.L["tick"]] + 1) & 0xFF
        keep = (cpu.d, cpu.e, cpu.ix, cpu.iy, cpu.a_, cpu.f_, cpu.b_, cpu.c_, cpu.d_, cpu.e_, cpu.h_, cpu.l_)
        saved = (cpu.a, cpu.f, cpu.b, cpu.c, cpu.h, cpu.l, cpu.pc, cpu.sp, cpu.iff)
        cpu.iff = 0
        cpu.push(SENTINEL)
        cpu.pc = self.L["snd_frame"]
        n = 0
        while cpu.pc != SENTINEL:
            cpu.step()
            n += 1
            if n > 1_000_000:
                raise RuntimeError("snd_frame does not return")
        if (cpu.d, cpu.e, cpu.ix, cpu.iy, cpu.a_, cpu.f_, cpu.b_, cpu.c_, cpu.d_, cpu.e_, cpu.h_, cpu.l_) != keep:
            raise RuntimeError("the interrupt rule: snd_frame changed DE, IX, IY or an alternate register")
        cpu.a, cpu.f, cpu.b, cpu.c, cpu.h, cpu.l, cpu.pc, cpu.sp, cpu.iff = saved
        self.vblanks += 1
        if ticks:
            self.ticks += 1
            self.tick_vbls.append(self.vblanks)
            if self.on_tick:
                self.on_tick(self)

    def vblank(self) -> None:
        cpu = self.cpu
        cpu.sp = 0xF300
        # (registers the interrupted program holds: arbitrary values, the rule's check)
        cpu.d, cpu.e, cpu.ix, cpu.iy = 0x12, 0x34, 0x5678, 0x9ABC
        cpu.a_, cpu.f_, cpu.b_, cpu.c_, cpu.d_, cpu.e_, cpu.h_, cpu.l_ = 1, 2, 3, 4, 5, 6, 7, 8
        self.interrupt()

    def pass_(self) -> None:
        """The stage's pass ends: pz_frame's $B00 + 1 (pzv_frame, a word: little-endian)."""
        a = self.L["pzv_frame"]
        r = self.bus.ram
        v = (r[a] | r[a + 1] << 8) + 1
        r[a], r[a + 1] = v & 0xFF, v >> 8 & 0xFF

    def pz_frame(self) -> int:
        return self.bus.ram[self.L["pzv_frame"]]

    def tn_left(self) -> int:
        a = self.L["tn_left"]
        return self.bus.ram[a] | self.bus.ram[a + 1] << 8


def tune_start(m: Machine) -> None:
    """A board's set-up ends: msx/puzl.asm bsu_t (ld hl,tn_pzm / jp mus_call, BANK_PUZL at A000h as
    while the stage runs); images before the move: the fixed area's snd_tune."""
    L = m.L
    m.call(L["bsu_t"] if "bsu_t" in L else L["snd_tune"])


def has_hold(lab: dict) -> bool:
    return "tn_hold" in lab


# ---------------------------------------------------------------------------------------------
# The expected registers (the streams decoded in Python)
# ---------------------------------------------------------------------------------------------

def load_tools(wt: Path):
    sys.path.insert(0, str(wt / "tools"))
    import msxfm as fm
    import msxscc as sc
    import msxsccfx as sx
    import msxsound as ms
    import msxtune as mt
    return fm, sc, sx, ms, mt


class Expect:
    """Per tick the registers the streams give (pzm.bin, decoded with the converters' decoders)."""

    def __init__(self, wt: Path, blob: bytes, T: int):
        self.fm, self.sc, self.sx, self.ms, self.mt = load_tools(wt)
        self.blob = blob
        hd = self.hd = self.mt.parse(blob)
        self.T = hd["T"]
        b = blob
        sc, fm, sx = self.sc, self.fm, self.sx
        self.table = [bytes(b[hd["waves"] + 32 * k:hd["waves"] + 32 * k + 32]) for k in range(hd["W"])]
        self.scc = [sc.decode_scc(b, hd["streams"][v], self.T) for v in range(3)]
        self.drums = self._psg_voice(hd["streams"][3])
        self.fmv = [fm.decode_melodic(b, hd["streams"][4 + c], self.T) for c in range(3)]
        self.rhy = fm.decode_rhythm(b, hd["streams"][7], self.T)
        self.psg = [self._psg_voice(hd["streams"][8 + v]) for v in range(3)]
        self.patch = b[hd["patch"]:hd["patch"] + 14]
        self.fx = {}
        for k in range(hd["fxn"]):
            n_ = hd["fx0"] + k
            e = hd["effects"][n_]
            s_st, _, _ = sx.decode_scc(b, e["scc"], hd["W"], e["scc_ticks"])
            p_st = self._psg_voice(e["psg"], e["psg_ticks"])
            self.fx[n_] = {"len": e["len"], "scc": s_st, "scc_ticks": e["scc_ticks"], "psg": p_st,
                           "psg_ticks": e["psg_ticks"]}

    def _psg_voice(self, start: int, ticks: int | None = None) -> list[tuple]:
        """A PSG stream (sndplay.asm's format) per tick: (volume, tone, noise, period, noise period)."""
        st, _ = self.sx.decode_psg(self.blob, start, ticks or self.T)
        return st


class Sched:
    """The effect voice, modelled apart from the Z80 code: request() = snd_bfx (between two ticks
    the higher request stays); tick(t) = the VBLANK's tick: the pending request through $1822C's
    rule (refused when lower than the last started while that one is busy), then per tick
    (effect, its tick) while it sounds, 'rel' at the tick its sound ends, else None; restart() =
    tn_start (no request, no effect, the rule's memory cleared).
    Busy as on the 68000: an effect of length L started at tick s (its tick 0) keeps channel 3's
    flags ($18126) set until its tick s + L reads its end, and PUZL's request of that pass ($17794)
    comes before the tick ($17212): a lower request is refused at ticks s + 1 .. s + L, so
    busy_until = s + L + 1 (edges() checks this against tools/rc2music.py's model).
    The tune's tick 0 is the first tick after the stage's next pass (the 68000 ticks the music in the
    pass, after its request): a request that pass sends starts with it (the jingle at boards 1-3)."""

    def __init__(self, fx: dict, scc: bool):
        self.fx, self.scc = fx, scc
        self.refused = []
        self.started = []
        self.restart()

    def restart(self) -> None:
        self.req, self.last, self.busy_until, self.cur = 0, 0, -1, None

    def request(self, n: int) -> None:
        self.req = max(self.req, n)

    def tick(self, t: int):
        if self.req:
            n, self.req = self.req, 0
            if n in self.fx and not (t < self.busy_until and n < self.last):
                self.last, self.busy_until, self.cur = n, t + self.fx[n]["len"] + 1, (n, t)
                self.started.append((t, n))
            elif n in self.fx:
                self.refused.append((t, n))
        if self.cur is None:
            return None
        n, s = self.cur
        ticks = self.fx[n]["scc_ticks" if self.scc else "psg_ticks"]
        if t - s < ticks:
            return (n, t - s)
        self.cur = None
        return "rel"


def check_tick(m: Machine, ex: Expect, mode: int, t_tune: int | None, f, t: int) -> list[str]:
    """The registers after a tick: t_tune = the tune's tick (None: over), f = the effect voice's
    state (Sched.tick)."""
    bad = []
    bus = m.bus
    T = ex.T
    over = t_tune is None or t_tune >= T
    def psg_cmp(voice: int, want: tuple, what: str) -> None:
        vol, tone, noise, per, npd = want
        if bus.psg[8 + voice] != vol:
            bad.append("%s: PSG volume %d, want %d" % (what, bus.psg[8 + voice], vol))
            return
        if not vol:
            return
        mix = bus.psg[7]
        if bool(mix & (1 << voice)) == tone or bool(mix & (8 << voice)) == noise:
            bad.append("%s: mixer %02X, want tone %s noise %s" % (what, mix, tone, noise))
        if tone and (bus.psg[2 * voice] | (bus.psg[2 * voice + 1] & 15) << 8) != per:
            bad.append("%s: period %d, want %d" % (what, bus.psg[2 * voice] | bus.psg[2 * voice + 1] << 8, per))
        if noise and bus.psg[6] != npd:
            bad.append("%s: noise period %d, want %d" % (what, bus.psg[6], npd))
    def scc_cmp(ch: int, want: tuple, what: str) -> None:
        vol = want[0]
        if bus.scc[0x8A + ch] != vol:
            bad.append("%s: SCC volume %d, want %d" % (what, bus.scc[0x8A + ch], vol))
            return
        if not vol:
            return
        n, w = want[1], want[2]
        if (bus.scc[0x80 + 2 * ch] | (bus.scc[0x81 + 2 * ch] & 15) << 8) != n:
            bad.append("%s: SCC period %d, want %d" % (what, bus.scc[0x80 + 2 * ch] | bus.scc[0x81 + 2 * ch] << 8, n))
        if bytes(bus.scc[32 * ch:32 * ch + 32]) != ex.table[w]:
            bad.append("%s: SCC waveform, want %d" % (what, w))
        if not bus.scc[0x8F] & (1 << ch):
            bad.append("%s: SCC channel off (988Fh %02X)" % (what, bus.scc[0x8F]))
    silent_psg = (0, False, False, None, None)
    # the tune
    if mode & MM_SCC:
        for c in range(3):
            scc_cmp(c, (0,) if over else ex.scc[c][t_tune], "tick %d SCC %d" % (t, c))
    if mode & MM_FM:
        for c in range(3):
            if over:
                if bus.opll[0x30 + c] & 15 != 15 or bus.opll[0x20 + c] & 0x10:
                    bad.append("tick %d FM %d: not silent at the end" % (t, c))
                continue
            d = ex.fmv[c]
            fn, bl = int(d["fnum"][t_tune]), int(d["block"][t_tune])
            want = {0x10 + c: fn & 0xFF, 0x20 + c: (int(d["sus"][t_tune]) << 5) | (int(d["key"][t_tune]) << 4)
                    | (bl << 1) | (fn >> 8), 0x30 + c: (int(d["inst"][t_tune]) << 4) | int(d["vol"][t_tune])}
            for r, v in want.items():
                if bus.opll[r] != v:
                    bad.append("tick %d FM %d: register %02X = %02X, want %02X" % (t, c, r, bus.opll[r], v))
    if mode & MM_RHY:
        if over:
            if bus.opll[0x0E] != 0x20:
                bad.append("tick %d rhythm: 0Eh %02X at the end" % (t, bus.opll[0x0E]))
        else:
            r = ex.rhy
            # (0Eh holds the last record's keys: find it)
            last = t_tune
            while last > 0 and not r["rec"][last]:
                last -= 1
            want0e = 0x20 | int(r["keys"][last])
            if bus.opll[0x0E] != want0e:
                bad.append("tick %d rhythm: 0Eh %02X, want %02X" % (t, bus.opll[0x0E], want0e))
            for reg, fld in ((0x36, "v36"), (0x37, "v37"), (0x38, "v38")):
                if bus.opll[reg] != int(r[fld][t_tune]):
                    bad.append("tick %d rhythm: %02X = %02X, want %02X" % (t, reg, bus.opll[reg], int(r[fld][t_tune])))
    if mode & (MM_FM | MM_RHY):
        for i in range(8):
            if bus.opll[i] != ex.patch[i]:
                bad.append("patch register %02X" % i)
        if mode & MM_RHY:
            for i, reg in enumerate((0x16, 0x17, 0x18, 0x26, 0x27, 0x28)):
                if bus.opll[reg] != ex.patch[8 + i]:
                    bad.append("rhythm pitch register %02X" % reg)
    if (mode & MM_SCC) and not (mode & MM_RHY):
        psg_cmp(2, silent_psg if over else ex.drums[t_tune], "tick %d drums on C" % t)
    if mode == 0:
        for v in range(2):
            psg_cmp(v, silent_psg if over else ex.psg[v][t_tune], "tick %d PSG %s" % (t, "AB"[v]))
    # the effect voice and C
    if mode & MM_SCC:
        if isinstance(f, tuple):
            n, k = f
            scc_cmp(3, ex.fx[n]["scc"][k] if ex.fx[n]["scc"][k][0] else (0,), "tick %d effect %d.%d on SCC 3" % (t, n, k))
        else:
            scc_cmp(3, (0,), "tick %d SCC 3 idle" % t)
    else:
        if isinstance(f, tuple):
            n, k = f
            psg_cmp(2, ex.fx[n]["psg"][k], "tick %d effect %d.%d on C" % (t, n, k))
        elif mode == 0:
            psg_cmp(2, silent_psg if over else ex.psg[2][t_tune], "tick %d PSG C (music)" % t)
        elif bus.psg[10] != 0:
            bad.append("tick %d: PSG C not silent (%d)" % (t, bus.psg[10]))
    return bad


def check_held(m: Machine, mode: int, t: int) -> list[str]:
    """A tick before the tune's tick 0 (held until the stage's next pass): nothing sounds, the chips
    as tn_start left them: the SCC's channels 0-3 at volume 0, PSG A-C at volume 0, no OPLL key."""
    bad = []
    bus = m.bus
    if mode & MM_SCC and any(bus.scc[0x8A + c] for c in range(4)):
        bad.append("tick %d (held): SCC volumes %s" % (t, bytes(bus.scc[0x8A:0x8E]).hex()))
    if any(bus.psg[8 + v] for v in range(3)):
        bad.append("tick %d (held): PSG volumes %s" % (t, bytes(bus.psg[8:11]).hex()))
    if mode & (MM_FM | MM_RHY):
        keys = ["%02Xh" % r for r in range(0x20, 0x29) if bus.opll[r] & 0x10]
        if keys or bus.opll[0x0E] & 0x1F:
            bad.append("tick %d (held): OPLL keys on %s, 0Eh %02X" % (t, keys, bus.opll[0x0E]))
    return bad


def run(wt: Path, rom: bytes, lab: dict, mode: int, plan: dict, hz50: bool = True,
        r800: bool = False) -> list[str]:
    """plan: 'ticks' to run; 'requests' {t: [n, ...]}: snd_bfx in the pass after the VBLANK tick t
    (t counts every tick from the start: the requests consumed at the next tick); every tick is
    followed by a pass (its requests, then $B00 + 1); 'restarts' [t: a board's set-up after the
    pass of tick t; tn_start's wait lets a VBLANK through, a tick of the tune playing; the new
    tune's tick 0 at the first tick after the next pass, with that pass's requests: the pass after
    tick t + 2]; 'stop' t
    (snd_stop after tick t); 'h7' (snd_stop right before the first set-up); 'refused' (a list: the
    model's refusals, (tick, effect), added); 'started' (likewise the effects started); 'tick0' (the
    ticks the tunes' tick 0 came at).
    r800: cpu_cur set (a turbo R's R800): tn_start leaves the OPLL out (mode & MM_SCC), and no
    OPLL write may come."""
    blob = (wt / "build" / "msx" / "pzm.bin").read_bytes()
    m = Machine(rom, lab, mode, hz50)
    if r800:
        m.bus.ram[lab["cpu_cur"]] = 1
    emode = mode & MM_SCC if r800 else mode         # (the chips tn_start picks)
    ex = Expect(wt, blob, plan["ticks"])
    sch = Sched(ex.fx, bool(emode & MM_SCC))
    hold = has_hold(lab)
    st = {"tune": None, "bad": [], "stopped": False, "fx": None, "held": False, "hpz": 0, "was_held": False}

    def on_tick(mm):
        t = mm.ticks
        st["was_held"] = False
        if st["held"]:
            if mm.pz_frame() == st["hpz"]:
                st["was_held"] = True
                if not st["stopped"] and not st.get("in_call"):
                    st["bad"] += check_held(mm, emode, t)
                return
            st["held"] = False
        st["fx"] = sch.tick(t)
        if st["tune"] is not None:
            st["tune"] += 1
            if st["tune"] == 0:
                st["tick0"].append(t)
        if not st["stopped"] and not st.get("in_call"):
            st["bad"] += check_tick(mm, ex, emode, st["tune"], st["fx"], t)
    m.on_tick = on_tick
    st["tick0"] = []

    def start():
        st["in_call"] = True
        tune_start(m)
        st["in_call"] = False
        sch.restart()
        st["tune"] = -1                             # (tn_start: its tick 0 the next unheld tick)
        st["held"], st["hpz"] = hold, m.pz_frame()

    if plan.get("h7"):
        m.call(lab["snd_stop"], irq=False)
    start()
    if plan.get("h7") and m.vblanks < 1:
        st["bad"].append("H7: tn_start did not let the queued stop through")
    reqs = plan.get("requests", {})
    while m.ticks < plan["ticks"] and len(st["bad"]) < 20:
        t0, before = m.ticks, len(m.bus.log)
        m.vblank()
        if m.ticks == t0:
            if len(m.bus.log) != before and not st["stopped"]:
                st["bad"].append("VBLANK %d (skipped at 60 Hz) wrote %s" % (m.vblanks, m.bus.log[before:before + 3]))
            continue
        t = m.ticks
        if st["was_held"] and len(m.bus.log) != before:
            st["bad"].append("tick %d (held) wrote %s" % (t, m.bus.log[before:before + 3]))
        if st["stopped"] and t > plan["stop"] + 1 and len(m.bus.log) != before:
            st["bad"].append("tick %d: writes after snd_stop: %s" % (t, m.bus.log[before:before + 3]))
        # (the pass after this tick: its requests, $B00 + 1, then the end checks: a set-up)
        for n in reqs.get(t, []):
            m.call(lab["snd_bfx"], a=n, irq=False)
            sch.request(n)
        m.pass_()
        if t in plan.get("restarts", []):
            start()
        if plan.get("stop") == t:
            m.call(lab["snd_stop"], irq=False)
            st["stopped"] = True
    bad = st["bad"] + sorted(set(m.bus.violations))
    if r800 and any(w[0] == "opll" for w in m.bus.log):
        bad.append("the OPLL written on the R800")
    if "refused" in plan:
        plan["refused"] += sch.refused
    if "started" in plan:
        plan["started"] += sch.started
    if "tick0" in plan:
        plan["tick0"] += st["tick0"]
    return bad + (["refused %s" % sch.refused] if plan.get("show_refused") else [])


def edges(wt: Path, rom: bytes, lab: dict) -> tuple[list[str], int]:
    """$1822C's rule at its edge: the ROM's own Z80 code (tn_go) against tools/rc2music.py's 68000
    model (PZM's player: --verify, 0 differences), one tick a pass in PUZL's order: effect hi
    started in pass P ($17794, then that pass's tick $17212), effect lo requested j passes later
    (before that pass's tick), for every pair of PZM's effects and j = 1, L - 1, L, L + 1 (L: hi's
    length), on the four chip sets. Started on the Z80 = tn_go's start path (tng_s) taken in the
    tick that read lo. Also: pzm.bin's effect lengths against the model's end ticks. Returns the
    differences and the cases compared."""
    sys.path.insert(0, str(wt / "tools"))
    import rc2music as rm
    data = (wt / "build" / "music" / "PZM_00.bin").read_bytes()
    lay = rm.locate(data)
    hd = load_tools(wt)[4].parse((wt / "build" / "msx" / "pzm.bin").read_bytes())
    bad = []
    for n, e in sorted(hd["effects"].items()):
        end = rm.run_tune(data, lay, n, entry="sfx")["end_tick"]
        if e["len"] != end:
            bad.append("effect %d: pzm.bin's length %d, the 68000 model's end tick %d" % (n, e["len"], end))

    def amiga(hi: int, lo: int, j: int) -> bool:
        p = rm.Player(data, lay)
        p.init()
        p.stop_all()
        p.start_sfx(hi)                     # (pass P), then the ticks of passes P .. P + j - 1
        for _ in range(j):
            p.play()
        return bool(p.start_sfx(lo))        # (pass P + j, before its tick)

    hits = [0]
    orig = z80.Z80.step

    def step(self, _o=orig):
        if self.pc == lab["tng_s"]:
            hits[0] += 1
        return _o(self)

    def msx(hi: int, lo: int, j: int, mode: int) -> bool:
        m = Machine(rom, lab, mode)
        tune_start(m)
        t_hi = m.ticks + 5
        k = None
        while m.ticks < t_hi + j + 1:
            m.vblank()
            if m.ticks == t_hi:
                m.call(lab["snd_bfx"], a=hi, irq=False)     # (hi's tick 0: t_hi + 1)
            elif m.ticks == t_hi + j:
                m.call(lab["snd_bfx"], a=lo, irq=False)     # (read at t_hi + j + 1: j ticks of hi)
                k = hits[0]
            m.pass_()
        return hits[0] > k

    nums = sorted(hd["effects"])
    cases = 0
    z80.Z80.step = step
    try:
        for hi in nums:
            L = hd["effects"][hi]["len"]
            for lo in nums:
                for j in sorted({1, L - 1, L, L + 1} - {0}):
                    want = amiga(hi, lo, j)
                    for mode in (MM_SCC, MM_SCC | MM_RHY, MM_FM | MM_RHY, 0):
                        got = msx(hi, lo, j, mode)
                        cases += 1
                        if got != want:
                            bad.append("effect %d, then %d %d ticks later (mode %d): the 68000 %s it, the Z80 %s" % (
                                hi, lo, j, mode, "starts" if want else "refuses", "starts" if got else "refuses"))
    finally:
        z80.Z80.step = orig
    return bad, cases


def transitions(rom: bytes, lab: dict, mode: int) -> list[str]:
    """The tune, snd_stop (the stage's end), then a level-1 effect (snd_play): the tune's ticks
    must not run again, the effect must play as on a machine that never ran the tune; then a level-1
    effect still playing when a set-up starts the tune: stopped, the tune's ticks from its tick 0
    on (the first tick after the next pass)."""
    bad = []
    a = Machine(rom, lab, mode)
    tune_start(a)
    t_start = a.tn_left()
    for _ in range(100):
        a.vblank()
        a.pass_()
    a.call(lab["snd_stop"], irq=False)
    a.vblank()
    left = a.tn_left()
    a.bus.log.clear()
    a.call(lab["snd_play"], a=4, irq=False)
    for _ in range(60):
        a.vblank()
    got = list(a.bus.log)
    if a.tn_left() != left:
        bad.append("the tune ticked after snd_stop")
    if left > t_start - 90:                         # (it must have played: about 100 ticks)
        bad.append("the tune did not play before snd_stop (tn_left %d -> %d)" % (t_start, left))
    b = Machine(rom, lab, mode)                 # (a machine that never ran the tune)
    b.call(lab["snd_stop"], irq=False)
    b.vblank()
    b.bus.log.clear()
    b.call(lab["snd_play"], a=4, irq=False)
    for _ in range(60):
        b.vblank()
    if got != list(b.bus.log):
        bad.append("level 1's effect 4 after the stage differs from a fresh machine's (%d / %d writes)"
                   % (len(got), len(b.bus.log)))
    if not got:
        bad.append("level 1's effect 4 wrote nothing")
    # a level-1 effect playing (the gun's opening: three effects, 53 ticks) when the tune starts
    c = Machine(rom, lab, mode)
    c.call(lab["snd_play"], a=0xFD, irq=False)
    for _ in range(5):
        c.vblank()
    tune_start(c)
    t0 = c.tn_left()
    for _ in range(10):
        c.vblank()
        c.pass_()
    want = t0 - 10 + (1 if has_hold(lab) else 0)    # (the first tick held: no pass yet)
    if c.tn_left() != want:
        bad.append("the tune does not tick after a level-1 effect (tn_left %d -> %d, want %d)" % (t0, c.tn_left(), want))
    if mode & MM_SCC and any(c.bus.ram[lab["fx_pv"] + 16 * k + 3] for k in range(3)):
        bad.append("a level-1 effect voice still plays under the tune")
    return bad


def jingle(rom: bytes, lab: dict, mode: int, hz50: bool, snd_div: int, fs_div: int, board: int,
           mid: bool) -> dict:
    """A board's start as the stage runs it. Board 0: bs_stage's snd_stop, 3 VBLANKs of its VRAM
    set-up, then bs_setup's tail (tune 1 after the stop all). Boards 1-3: the board before plays
    (its set-up, a move, then the 31-pass fade-out's buzz: effect 6 every pass), then the new
    board's set-up right after its last pass. Then the pass loop: bs_wait (a VBLANK; at 60 Hz every
    sixth skipped by its own divider fs_div, as sndplay.asm's snd_div skips the ticks', each from
    the phase given), then the pass: bst_go's request in the first pass (5 at boards 1-3: the
    set-up's), then pz_frame's $B00 + 1; mid: a VBLANK inside that first pass, between the request
    and $B00 + 1 (a pass that overruns its frame). Returns the VBLANK numbers of: the tune's tick 0
    (tn_tick reading the first records: tn_left = its length + 1), effect 5's start (tn_go's tng_s
    with C = 5), the first pass's end, the first ticking VBLANK after it; and the tune's ticks seen
    before tick 0."""
    m = Machine(rom, lab, mode, hz50)
    r = m.bus.ram
    r[lab["snd_div"]] = snd_div
    fs = [fs_div]
    ev = {"tick0": None, "fx5": None, "before": 0, "T1": None, "on": False}
    orig = z80.Z80.step

    def step(self, _o=orig):
        if ev["on"] and m.bus.win[3] == lab["BANK_MUSIC"]:
            if self.pc == lab["tn_tick"]:
                if ev["tick0"] is None:
                    if m.tn_left() == ev["T1"]:
                        ev["tick0"] = m.vblanks + 1
                    else:
                        ev["before"] += 1
            elif self.pc == lab["tng_s"] and self.c == 5 and ev["fx5"] is None:
                ev["fx5"] = m.vblanks + 1
        return _o(self)

    def bs_wait():
        while True:
            m.vblank()
            if hz50:
                return
            fs[0] += 1
            if fs[0] < 6:
                return
            fs[0] = 0

    z80.Z80.step = step
    try:
        if board == 0:
            m.call(lab["snd_stop"], irq=False)
            for _ in range(3):
                m.vblank()
        else:
            tune_start(m)
            for k in range(32):
                bs_wait()
                if k:
                    m.call(lab["snd_bfx"], a=6 if k > 1 else 4, irq=False)
                m.pass_()
        tune_start(m)                       # (its VBLANK wait: the board before's last tick)
        ev["T1"] = m.tn_left()
        ev["on"] = True
        p1 = None
        for k in range(3):
            bs_wait()
            if k == 0 and board:
                m.call(lab["snd_bfx"], a=5, irq=False)
                if mid:
                    m.vblank()
            m.pass_()
            if k == 0:
                p1 = m.vblanks
    finally:
        z80.Z80.step = orig
    after = [v for v in m.tick_vbls if v > p1]
    return {"tick0": ev["tick0"], "fx5": ev["fx5"], "p1": p1, "first_after": after[0] if after else None,
            "before": ev["before"]}


def jingles(rom: bytes, lab: dict) -> tuple[list[str], int]:
    """jingle() at 50 Hz (boards 0-3, with and without a VBLANK inside the first pass) and at 60 Hz
    for every phase of the two dividers (snd_div, fs_div: 0-5 each; boards 0 and 1, with and without),
    on the four chip sets: at every board the tune's tick 0 is the first ticking VBLANK after the first
    pass's end, no tick of the tune before it; at boards 1-3 effect 5 starts in that same VBLANK."""
    bad, n = [], 0
    for name, mode in (("SCC", MM_SCC), ("SCC + OPLL", MM_SCC | MM_RHY), ("OPLL", MM_FM | MM_RHY), ("PSG", 0)):
        cases = [(True, 0, 0, b, mid) for b in range(4) for mid in (False, True)]
        cases += [(False, sd, fd, b, mid) for sd in range(6) for fd in range(6) for b in (0, 1) for mid in (False, True)]
        for hz50, sd, fd, b, mid in cases:
            j = jingle(rom, lab, mode, hz50, sd, fd, b, mid)
            n += 1
            what = "%s %d Hz snd_div %d fs_div %d board %d%s" % (name, 50 if hz50 else 60, sd, fd, b,
                                                                 " (a VBLANK inside the first pass)" if mid else "")
            if j["tick0"] is None:
                bad.append("%s: no tick 0" % what)
                continue
            if j["before"]:
                bad.append("%s: %d tune ticks before tick 0" % (what, j["before"]))
            if j["tick0"] != j["first_after"]:
                bad.append("%s: tick 0 in VBLANK %d, the first tick after the first pass (ended after VBLANK %d) "
                           "is %s" % (what, j["tick0"], j["p1"], j["first_after"]))
            if b and j["fx5"] != j["tick0"]:
                bad.append("%s: effect 5 in VBLANK %s, the tune's tick 0 in %d" % (what, j["fx5"], j["tick0"]))
            if not b and j["fx5"] is not None:
                bad.append("%s: effect 5 at board 0" % what)
    return bad, n


def title_after(rom: bytes, lab: dict, mode: int, hz50: bool) -> list[str]:
    """The title after the stage: the stage's sound (board 0: moves, a red chip, the fade-out's buzz;
    board 1's set-up and jingle, moves), the stage's end in the middle of the tune (front_bonus'
    snd_stop), the result screen (fe_text: snd_stop at its start and its end, 130 ticks), then the
    title's music (front_title: snd_music) to its end and 100 VBLANKs more; against a fresh machine's
    title (eqcmp.py's title(): the power-on state). The PSG player's 60 Hz divider (snd_div) runs free
    from the power-on: the fresh machine gets the stage machine's phase. Every chip write, VBLANK by
    VBLANK, must be equal; then the chips must be equal on every register the fresh title wrote (the
    ones it never writes may keep the stage's: listed, not a failure)."""
    a = Machine(rom, lab, mode, hz50)
    a.call(lab["snd_stop"], irq=False)                     # (bs_stage's start)
    for _ in range(3):
        a.vblank()
    tune_start(a)                                          # (board 0)
    for k in range(240):
        a.vblank()
        if k in (5, 9, 14, 30, 31, 60, 90):
            a.call(lab["snd_bfx"], a=3 if k == 31 else 4, irq=False)
        if 200 <= k < 231:
            a.call(lab["snd_bfx"], a=6, irq=False)
        a.pass_()
    tune_start(a)                                          # (board 1)
    for k in range(120):
        a.vblank()
        if k == 0:
            a.call(lab["snd_bfx"], a=5, irq=False)
        if k in (10, 40, 70):
            a.call(lab["snd_bfx"], a=4, irq=False)
        a.pass_()
    a.call(lab["snd_stop"], irq=False)                     # (front_bonus, $83E4)
    a.call(lab["snd_stop"], irq=False)                     # (fe_text's start)
    for _ in range(130):
        a.vblank()
    a.call(lab["snd_stop"], irq=False)                     # (fe_text's end)
    a.vblank()
    b = Machine(rom, lab, mode, hz50)
    b.bus.ram[lab["snd_div"]] = a.bus.ram[lab["snd_div"]]
    out = []
    for m in (a, b):
        m.bus.log.clear()
        m.bus.ram[lab["act_a000"]] = lab["BANK_FRONT"]      # (as eqcmp.py: mus_call puts it back)
        m.call(lab["snd_music"], irq=False)
        rec = [("start", tuple(m.bus.log))]
        m.bus.log.clear()
        for _ in range(5184 * 6 // 5 + 200 if not hz50 else 5184 + 100):
            m.vblank()
            rec.append(tuple(m.bus.log))
            m.bus.log.clear()
        out.append(rec)
    bad = []
    ra, rb = out
    if ra != rb:
        k = next(i for i in range(min(len(ra), len(rb))) if ra[i] != rb[i])
        flat_a = [w for x in ra for w in (x[1] if x and x[0] == "start" else x)]
        flat_b = [w for x in rb for w in (x[1] if x and x[0] == "start" else x)]
        bad.append("the title's chip writes differ from a fresh title's first at VBLANK %d (%d / %d writes; "
                   "the same writes in another grouping: %s): %s / %s" % (
                       k, len(flat_a), len(flat_b), flat_a == flat_b, ra[k][:4], rb[k][:4]))
    written = {(w[0], w[1]) for x in rb for w in (x[1] if x and x[0] == "start" else x)}
    other = []
    for chip, regs_a, regs_b, n in (("scc", a.bus.scc, b.bus.scc, 0x90), ("psg", a.bus.psg, b.bus.psg, 14),
                                    ("opll", a.bus.opll, b.bus.opll, 0x39)):
        for reg in range(n):
            if regs_a[reg] != regs_b[reg]:
                if (chip, reg) in written:
                    bad.append("after the title: %s register %02X = %02X, a fresh title's %02X" % (
                        chip, reg, regs_a[reg], regs_b[reg]))
                else:
                    other.append("%s %02X" % (chip, reg))
    # (as ranges: "scc 60h-7Fh")
    runs, prev = [], None
    for x in other:
        chip, reg = x.split()
        reg = int(reg, 16)
        if prev and prev[0] == chip and prev[2] == reg - 1:
            prev[2] = reg
        else:
            prev = [chip, reg, reg]
            runs.append(prev)
    title_after.ignored = ["%s %02Xh%s" % (c, a, "-%02Xh" % b if b != a else "") for c, a, b in runs]
    title_after.writes = sum(len(x[1]) if x and x[0] == "start" else len(x) for x in rb)
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("worktree", type=Path)
    ap.add_argument("rom", type=Path)
    ap.add_argument("labels", type=Path)
    ap.add_argument("--ticks", type=int, default=3100)
    ap.add_argument("--only", default="", help="run,restart,stop,h7,transitions,r800,edges,jingle,title")
    args = ap.parse_args()
    only = set(filter(None, args.only.split(",")))
    want_ = lambda k: not only or k in only
    rom = args.rom.read_bytes()
    lab = labels(args.labels)
    print("image: %s; the tune's tick 0 %s" % (args.rom.name, "after the stage's next pass (tn_hold)" if has_hold(lab)
                                                else "at the first tick after the set-up (no tn_hold)"))
    reqs = {}
    # a move (4), then a red chip a pass later (3: refused while 4 plays), several moves; the
    # jingle (5) with moves inside it (refused), a burst of 6 (the buzz restarted every pass); two
    # requests between two ticks (4 then 3: 4 stays); effects after the tune's end (H6); $1822C's
    # edge, a lower request L ticks after an effect of length L started (refused, as on the
    # 68000) and L + 1 (started): 4 -> 3 (16, 17), 5 -> 4 (108, 109), 6 -> 5 (366, 367), 5 -> 3
    # (415, 416)
    for t, ns in ((10, [4]), (11, [3]), (16, [3]), (17, [3]), (40, [4]), (44, [4]), (60, [5]), (70, [4]),
                  (80, [4]), (108, [4]), (109, [4]), (120, [4, 3]), (200, [3]), (366, [5]), (367, [5]),
                  (415, [3]), (416, [3]), (2995, [4]), (3010, [5]), (3070, [4])):
        reqs[t] = ns
    for t in range(300, 331):
        reqs[t] = [6]
    # (the model's refusals the plan must give: (tick that read the request, effect))
    want_refused = [(12, 3), (17, 3), (71, 4), (81, 4), (109, 4), (367, 5), (416, 3)]
    total = 0
    for name, mode in (("SCC + PSG drums", MM_SCC), ("SCC + OPLL rhythm", MM_SCC | MM_RHY),
                       ("OPLL alone", MM_FM | MM_RHY), ("PSG alone", 0)):
        if want_("run"):
            for hz in (True, False):
                plan = {"ticks": args.ticks, "requests": reqs, "refused": []}
                bad = run(args.worktree, rom, lab, mode, plan, hz)
                if args.ticks >= 420 and plan["refused"] != want_refused:
                    bad.append("the plan's refusals %s, want %s" % (plan["refused"], want_refused))
                print("%-18s %s Hz, %d ticks, effects, the end: %s" % (name, 50 if hz else 60, args.ticks,
                                                                      "PASS" if not bad else "FAIL"))
                for b in bad[:12]:
                    print("   ", b)
                total += len(bad)
        if want_("restart"):
            # a board's restart after the pass of tick 500 (tick 501 in its VBLANK wait), an effect
            # playing across it; the next pass (after tick 502) sends the jingle: it must start with the
            # new tune's tick 0 (with the hold 503: tick 502 is held, no pass since the set-up yet)
            plan = {"ticks": 900, "requests": {495: [5], 502: [5], 520: [4]}, "restarts": [500], "started": [],
                    "tick0": []}
            bad = run(args.worktree, rom, lab, mode, plan)
            jt = [t for t, n in plan["started"] if n == 5 and t > 500]
            t0 = [t for t in plan["tick0"] if t > 500]
            if jt != t0:
                bad.append("the jingle after the restart started at tick %s, the new tune's tick 0 at %s" % (jt, t0))
            print("%-18s restart at 500, the jingle with its tick 0: %s" % (name, "PASS" if not bad else "FAIL"))
            for b in bad[:12]:
                print("   ", b)
            total += len(bad)
    if want_("stop"):
        # the PSG alone: snd_stop stops the tune's ticks (no more writes after its SQ_STOP)
        bad = run(args.worktree, rom, lab, 0, {"ticks": 400, "requests": {}, "stop": 200})
        print("PSG alone, snd_stop at 200: %s" % ("PASS" if not bad else "FAIL"))
        for b in bad[:12]:
            print("   ", b)
        total += len(bad)
    if want_("h7"):
        # H7: snd_stop right before the set-up (the PSG alone): tn_start lets the queued stop through
        bad = run(args.worktree, rom, lab, 0, {"ticks": 300, "requests": {}, "h7": True})
        print("PSG alone, snd_stop right before the tune's start (H7): %s" % ("PASS" if not bad else "FAIL"))
        for b in bad[:12]:
            print("   ", b)
        total += len(bad)
    if want_("transitions"):
        for name, mode in (("SCC", MM_SCC), ("PSG alone", 0)):
            bad = transitions(rom, lab, mode)
            print("%s: the stage -> level 1 -> the stage: %s" % (name, "PASS" if not bad else "FAIL"))
            for b in bad[:12]:
                print("   ", b)
            total += len(bad)
    if want_("r800"):
        # the R800 (a turbo R before cpu_set 80h): no OPLL, the SCC version or the PSG's
        for name, mode in (("SCC + OPLL", MM_SCC | MM_RHY), ("OPLL alone", MM_FM | MM_RHY)):
            plan = {"ticks": args.ticks, "requests": reqs, "refused": []}
            bad = run(args.worktree, rom, lab, mode, plan, True, r800=True)
            print("R800, %-11s %d ticks, effects, the end, no OPLL write: %s" % (
                name + ":", args.ticks, "PASS" if not bad else "FAIL"))
            for b in bad[:12]:
                print("   ", b)
            total += len(bad)
    if want_("jingle"):
        bad, n = jingles(rom, lab)
        print("the board's start: %d cases (50 Hz boards 0-3; 60 Hz every snd_div/fs_div phase, boards 0-1; with "
              "and without a VBLANK inside the first pass; four chip sets): tick 0 at the first tick after the "
              "first pass, effect 5 in the same VBLANK at boards 1-3: %s" % (n, "PASS" if not bad else "FAIL (%d)" % len(bad)))
        for b in bad[:12]:
            print("   ", b)
        total += len(bad)
    if want_("title"):
        for name, mode in (("SCC + PSG drums", MM_SCC), ("SCC + OPLL rhythm", MM_SCC | MM_RHY),
                           ("OPLL alone", MM_FM | MM_RHY), ("PSG alone", 0)):
            for hz in (True, False):
                bad = title_after(rom, lab, mode, hz)
                print("%-18s %d Hz: the title after the stage, %d chip writes against a fresh title's: %s%s" % (
                    name, 50 if hz else 60, title_after.writes, "PASS" if not bad else "FAIL",
                    "; registers the title never writes left as the stage left them: %s" % (
                        ", ".join(title_after.ignored) if title_after.ignored else "none")))
                for b in bad[:12]:
                    print("   ", b)
                total += len(bad)
    if want_("edges"):
        # $1822C's edge against the 68000 model
        bad, cases = edges(args.worktree, rom, lab)
        print("$1822C's rule against tools/rc2music.py's 68000 model: %d cases (every pair of effects, "
              "j = 1, L - 1, L, L + 1, four chip sets), the lengths: %s" % (cases, "PASS" if not bad else "FAIL"))
        for b in bad[:12]:
            print("   ", b)
        total += len(bad)
    print("all: %s" % ("PASS" if not total else "FAIL (%d)" % total))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
