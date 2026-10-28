"""Scratch (the range's step 11): FRM, the shooting range's tune 1 and effects 2-4 (build/msx/frm.bin),
played by an image's own code in the Brainstorm night's Z80 interpreter (brainstorm/impl/sound pzsim.py:
the Konami SCC mapper, the PSG, the SCC and the OPLL modelled, every chip write logged): the stage's
calls as msx/frng.asm makes them (the tune's start: ld hl,tn_frm / call mus_call with BANK_FRNG at
A000h; the requests: snd_rfx in BANK_FRNG), the VBLANK interrupt's sound (snd_frame -> sq_frame ->
fx_tk -> tune.asm fx_tkd -> tn_tick), the passes modelled ($B00 + 1 after each tick's requests).

After every tick the chips' registers are compared with frm.bin's streams decoded apart in Python with
the converters' decoders (msxscc, msxfm; the PSG format read here record by record), and the effects'
schedule with pzsim.Sched ($1822C's rule as the 68000 runs it, snd_rfx's merge: the higher request
stays). With an SCC an effect flagged in its entry (bit 7 of its SCC ticks byte: effect 2, a noise)
plays its SCC-mode stream, in the PSG format, on PSG voice B; PSG B is silent at every other tick in
the SCC modes (so a shot cut by a hit sound must be silenced at once), PSG A always; SCC channel 3
plays the other effects. The noise period R6 is shared: it must hold the last value written this tick
or before by a voice whose record began with its noise on, in tn_tick's output order (SCC modes: the
effect on B, then the drums on C; the PSG alone: A, B, C), whenever an audible voice mixes the noise.

usage: frsim.py ROOT ROM LABELS [--ticks N] [--only run,r800,stop,edges,title,bseq] [--old ROM LABELS]
  ROOT: the repository (tools/, build/msx/frm.bin, build/music/FRM_00.bin); --old: the image before
  the change, for bseq (Brainstorm's tune and effects, every chip write VBLANK by VBLANK, old against
  new, four chip sets, 50 and 60 Hz)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

BS = Path(__file__).resolve().parent      # z80.py, pzsim.py, int_wavcmp.py: the Brainstorm night's
sys.path.insert(0, str(BS))
import pzsim  # noqa: E402
import z80  # noqa: E402

MM_SCC, MM_FM, MM_RHY = 1, 2, 4
MODES = (("SCC + PSG drums", MM_SCC), ("SCC + OPLL rhythm", MM_SCC | MM_RHY), ("OPLL alone", MM_FM | MM_RHY),
         ("PSG alone", 0))
SILENT = (0, False, False, None, None, False)


def psg_recs(b: bytes, start: int, T: int) -> list[tuple]:
    """A PSG-format stream (sndplay.asm's: dur, ctl (0-3 volume, 4 tone on, 5 noise on, 6 a period word
    follows, 7 a noise period byte), the fields kept from record to record as music.asm mv_rec keeps
    them) per tick: (volume, tone, noise, period, noise period, new: a record begins at this tick);
    silent after its end."""
    out, p, per, npd = [], start, None, None
    while b[p] and len(out) < T:
        d, ctl = b[p], b[p + 1]
        p += 2
        if ctl & 0x40:
            per = (b[p] | b[p + 1] << 8) & 0xFFF
            p += 2
        if ctl & 0x80:
            npd = b[p] & 31
            p += 1
        st = (ctl & 15, bool(ctl & 0x10), bool(ctl & 0x20), per, npd)
        out.append(st + (True,))
        out += [st + (False,)] * (d - 1)
    return (out + [(0, False, False, per, npd, False)] * T)[:T]


class FExpect:
    """frm.bin decoded with the converters' decoders: the tune's voices per tick, the effects'."""

    def __init__(self, root: Path, blob: bytes):
        self.fm, self.sc, self.sx, self.ms, self.mt = pzsim.load_tools(root)
        hd = self.hd = self.mt.parse(blob)
        b, T = blob, hd["T"]
        self.T = T
        self.table = [bytes(b[hd["waves"] + 32 * k:hd["waves"] + 32 * k + 32]) for k in range(hd["W"])]
        self.scc = [self.sc.decode_scc(b, hd["streams"][v], T) for v in range(3)]
        self.drums = psg_recs(b, hd["streams"][3], T)
        self.fmv = [self.fm.decode_melodic(b, hd["streams"][4 + c], T) for c in range(3)]
        self.rhy = self.fm.decode_rhythm(b, hd["streams"][7], T)
        self.psg = [psg_recs(b, hd["streams"][8 + v], T) for v in range(3)]
        self.patch = b[hd["patch"]:hd["patch"] + 14]
        self.fx = {}
        for n, e in hd["effects"].items():
            f = {"len": e["len"], "flag": e["scc_psg"], "scc_ticks": e["scc_ticks"], "psg_ticks": e["psg_ticks"],
                 "psg": psg_recs(b, e["psg"], e["psg_ticks"])}
            if e["scc_psg"]:
                f["scc"] = psg_recs(b, e["scc"], e["scc_ticks"])
            else:
                f["scc"], _, _ = self.sx.decode_scc(b, e["scc"], hd["W"], e["scc_ticks"])
            self.fx[n] = f


class Check:
    """The registers after each tick (the Z80's chips, or a log's) against the streams."""

    def __init__(self, ex: FExpect):
        self.ex = ex
        self.r6 = None                      # the noise period last written (the model)
        self.shared = 0                     # ticks with two audible noises of different periods

    def psg_voices(self, mode: int, t_tune, f) -> tuple[list, list]:
        """(A, B, C) the PSG voices must show, and R6's writers this tick in output order."""
        ex = self.ex
        over = t_tune is None or t_tune >= ex.T
        tune = (lambda s: SILENT if over else s[t_tune])
        A = B = C = SILENT
        fxs = None
        if isinstance(f, tuple):
            n, k = f
            fxs = ex.fx[n]["scc"][k] if (mode & MM_SCC) else ex.fx[n]["psg"][k]
            if (mode & MM_SCC) and not ex.fx[n]["flag"]:
                fxs = None                  # (on SCC channel 3)
        order = []
        if mode & MM_SCC:
            B = fxs or SILENT
            order.append(B)
            if not mode & MM_RHY:
                C = tune(ex.drums)
                order.append(C)
        elif mode & MM_FM:
            C = fxs or SILENT
            order.append(C)
        else:
            A, B = tune(ex.psg[0]), tune(ex.psg[1])
            if fxs:
                C = fxs
            else:
                C = tune(ex.psg[2])
                if f == "rel":              # (the effect over: C to voice 2 again, its whole state)
                    C = C[:5] + (True,)
            order += [A, B, C]
        return [A, B, C], order

    def tick(self, bus, mode: int, t_tune, f, t: int, scc_ok: bool = True) -> list[str]:
        ex = self.ex
        bad = []
        over = t_tune is None or t_tune >= ex.T
        voices, order = self.psg_voices(mode, t_tune, f)
        for v in order:
            if v[5] and v[2]:
                self.r6 = v[4]
        noises = set()
        for i, (vol, tone, noise, per, npd, new) in enumerate(voices):
            what = "tick %d PSG %s" % (t, "ABC"[i])
            if bus.psg[8 + i] != vol:
                bad.append("%s: volume %d, want %d" % (what, bus.psg[8 + i], vol))
                continue
            if not vol:
                continue
            mix = bus.psg[7]
            if bool(mix & (1 << i)) == tone or bool(mix & (8 << i)) == noise:
                bad.append("%s: mixer %02X, want tone %s noise %s" % (what, mix, tone, noise))
            if tone and (bus.psg[2 * i] | (bus.psg[2 * i + 1] & 15) << 8) != per:
                bad.append("%s: period %d, want %d" % (what, bus.psg[2 * i] | (bus.psg[2 * i + 1] & 15) << 8, per))
            if noise:
                noises.add(npd)
                if (bus.psg[6] & 31) != self.r6:
                    bad.append("%s: noise period %d, want %s (the last written)" % (what, bus.psg[6] & 31, self.r6))
        if len(noises) > 1:
            self.shared += 1
        if mode & MM_SCC and scc_ok:
            def scc_cmp(ch: int, want: tuple, what: str) -> None:
                if bus.scc[0x8A + ch] != want[0]:
                    bad.append("%s: SCC volume %d, want %d" % (what, bus.scc[0x8A + ch], want[0]))
                    return
                if not want[0]:
                    return
                n_, w = want[1], want[2]
                if (bus.scc[0x80 + 2 * ch] | (bus.scc[0x81 + 2 * ch] & 15) << 8) != n_:
                    bad.append("%s: SCC period, want %d" % (what, n_))
                if bytes(bus.scc[32 * ch:32 * ch + 32]) != ex.table[w]:
                    bad.append("%s: SCC waveform, want %d" % (what, w))
                if not bus.scc[0x8F] & (1 << ch):
                    bad.append("%s: SCC channel off (988Fh %02X)" % (what, bus.scc[0x8F]))
            for c in range(3):
                scc_cmp(c, (0,) if over else ex.scc[c][t_tune], "tick %d SCC %d" % (t, c))
            want3 = (0,)
            if isinstance(f, tuple) and not ex.fx[f[0]]["flag"]:
                s = ex.fx[f[0]]["scc"][f[1]]
                want3 = s if s[0] else (0,)
            scc_cmp(3, want3, "tick %d SCC 3 (effect %s)" % (t, f))
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
                last = t_tune
                while last > 0 and not r["rec"][last]:
                    last -= 1
                if bus.opll[0x0E] != 0x20 | int(r["keys"][last]):
                    bad.append("tick %d rhythm: 0Eh %02X, want %02X" % (t, bus.opll[0x0E], 0x20 | int(r["keys"][last])))
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
        return bad


def setup(rom: bytes, lab: dict, mode: int, hz50: bool = True) -> pzsim.Machine:
    m = pzsim.Machine(rom, lab, mode, hz50)
    m.bus.ram[lab["act_a000"]] = lab["BANK_FRNG"]
    m.bus.win[3] = lab["BANK_FRNG"]
    return m


def tune_start(m: pzsim.Machine) -> None:
    """msx/frng.asm rg_stage: ld hl,tn_frm / call mus_call (BANK_FRNG at A000h)."""
    m.call(m.L["mus_call"], hl=m.L["tn_frm"])
    if m.bus.win[3] != m.L["BANK_FRNG"]:
        raise RuntimeError("mus_call left bank %d at A000h" % m.bus.win[3])


def request(m: pzsim.Machine, n: int) -> None:
    """msx/frng.asm snd_rfx (BANK_FRNG at A000h), A = the effect."""
    m.call(m.L["snd_rfx"], a=n, irq=False)


def run(root: Path, rom: bytes, lab: dict, mode: int, plan: dict, hz50: bool = True, r800: bool = False):
    """plan: 'ticks'; 'requests' {t: [n, ...]} (snd_rfx in the pass after the VBLANK tick t, each);
    'stop' t (snd_stop after the pass of tick t). Returns (differences, details)."""
    blob = (root / "build" / "msx" / "frm.bin").read_bytes()
    ex = FExpect(root, blob)
    m = setup(rom, lab, mode, hz50)
    if r800:
        m.bus.ram[lab["cpu_cur"]] = 1
    emode = mode & MM_SCC if r800 else mode
    chk = Check(ex)
    sch = pzsim.Sched(ex.fx, bool(emode & MM_SCC))
    st = {"tune": None, "bad": [], "stopped": False, "fx": None, "held": True, "hpz": 0, "was_held": False,
          "tick0": [], "in_call": False, "silent_after": None}

    def on_tick(mm):
        t = mm.ticks
        st["was_held"] = False
        if st["held"]:
            if mm.pz_frame() == st["hpz"]:
                st["was_held"] = True
                if not st["stopped"] and not st["in_call"]:
                    st["bad"] += pzsim.check_held(mm, emode, t)
                return
            st["held"] = False
        st["fx"] = sch.tick(t)
        if st["tune"] is not None:
            st["tune"] += 1
            if st["tune"] == 0:
                st["tick0"].append(t)
        if not st["stopped"] and not st["in_call"]:
            st["bad"] += chk.tick(mm.bus, emode, st["tune"], st["fx"], t)
    m.on_tick = on_tick
    st["in_call"] = True
    tune_start(m)
    st["in_call"] = False
    sch.restart()
    st["tune"] = -1
    st["hpz"] = m.pz_frame()
    reqs = plan.get("requests", {})
    first_pass = None
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
        for n in reqs.get(t, []):
            request(m, n)
            sch.request(n)
        if first_pass is None:
            first_pass = t
        m.pass_()
        if plan.get("stop") == t:
            m.call(lab["snd_stop"], irq=False)
            st["stopped"] = True
    bad = st["bad"] + sorted(set(m.bus.violations))
    if r800 and any(w[0] == "opll" for w in m.bus.log):
        bad.append("the OPLL written on the R800")
    if st["tick0"] != [first_pass + 1]:
        bad.append("the tune's tick 0 at tick %s, the first pass after tick %s" % (st["tick0"], first_pass))
    return bad, {"refused": sch.refused, "started": sch.started, "shared": chk.shared, "tick0": st["tick0"]}


def plan_requests(ticks: int) -> dict:
    """Shots (2, 6 ticks), correct (3, 16) and dummy (4, 12) hit sounds: a shot alone; a shot
    restarted by a shot; a shot cut by 3 and by 4 (PSG B silenced in the SCC modes); shots refused
    during a hit sound, at its edge L and L + 1 (busy L + 1); 4 cutting 3; 3 refused during 4 and at
    the edge; 2 and 3 in one pass (3 stays, either order); a hit sound at a shot's last tick and at
    the tick after it; a long stretch of play (a shot every 24 passes, hit sounds 11 passes after two
    shots in three); effects after the tune's end."""
    r = {20: [2], 40: [2], 43: [2], 60: [2], 62: [3], 70: [2], 78: [2], 79: [2], 100: [2], 101: [4],
         130: [3], 131: [4], 160: [4], 161: [3], 172: [3], 173: [3], 200: [2, 3], 230: [3, 2], 260: [2], 265: [3],
         300: [2], 306: [4], 330: [2], 337: [3]}
    k = 0
    for t in range(400, min(ticks, 5990), 24):
        r.setdefault(t, []).append(2)
        k += 1
        if k % 3:
            r.setdefault(t + 11, []).append(3 if k % 2 else 4)
    for t, n in ((6005, 2), (6020, 3), (6040, 4), (6060, 2)):
        if t < ticks:
            r.setdefault(t, []).append(n)
    return r


def edges(root: Path, rom: bytes, lab: dict) -> tuple[list[str], int]:
    """$1822C's rule at its edge: the image's tn_go against tools/rc2music.py's 68000 model of FRM's
    player (FRM_00.bin), every pair of effects 2-4, the lower one 1, L - 1, L and L + 1 ticks after
    (pzsim.edges' method: FRNG asks before the pass's tick, as PUZL; frm.bin's lengths against the
    model's end ticks too), four chip sets."""
    sys.path.insert(0, str(root / "tools"))
    import rc2music as rm
    data = (root / "build" / "music" / "FRM_00.bin").read_bytes()
    lay = rm.locate(data)
    hd = pzsim.load_tools(root)[4].parse((root / "build" / "msx" / "frm.bin").read_bytes())
    bad = []
    for n, e in sorted(hd["effects"].items()):
        end = rm.run_tune(data, lay, n, entry="sfx")["end_tick"]
        if e["len"] != end:
            bad.append("effect %d: frm.bin's length %d, the 68000 model's end tick %d" % (n, e["len"], end))

    def amiga(hi: int, lo: int, j: int) -> bool:
        p = rm.Player(data, lay)
        p.init()
        p.stop_all()
        p.start_sfx(hi)
        for _ in range(j):
            p.play()
        return bool(p.start_sfx(lo))

    hits = [0]
    orig = z80.Z80.step

    def step(self, _o=orig):
        if self.pc == lab["tng_s"]:
            hits[0] += 1
        return _o(self)

    def msx(hi: int, lo: int, j: int, mode: int) -> bool:
        m = setup(rom, lab, mode)
        tune_start(m)
        t_hi = m.ticks + 5
        k = None
        while m.ticks < t_hi + j + 1:
            m.vblank()
            if m.ticks == t_hi:
                request(m, hi)
            elif m.ticks == t_hi + j:
                request(m, lo)
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
                    for _, mode in MODES:
                        got = msx(hi, lo, j, mode)
                        cases += 1
                        if got != want:
                            bad.append("effect %d, then %d %d ticks later (mode %d): the 68000 %s it, the Z80 %s" % (
                                hi, lo, j, mode, "starts" if want else "refuses", "starts" if got else "refuses"))
    finally:
        z80.Z80.step = orig
    return bad, cases


def title_after(rom: bytes, lab: dict, mode: int, hz50: bool) -> tuple[list[str], list[str], int]:
    """The title after the range: rg_stage's snd_stop, the tune and play (shots, hit sounds, a shot
    cut by a hit sound), the stage's end mid-tune (frng.asm rg_end's snd_stop, then rg_hide's waits),
    the result screen (fe_text: snd_stop at its start and at its end, 130 ticks), then the title (snd_music) to its end
    and 100 VBLANKs more; against a fresh machine's title (pzsim.title_after's method). Every chip
    write VBLANK by VBLANK equal; the registers the fresh title wrote equal at the end (the others,
    left as the range left them, listed)."""
    a = setup(rom, lab, mode, hz50)
    a.call(lab["snd_stop"], irq=False)
    for _ in range(3):
        a.vblank()
    tune_start(a)
    for k in range(400):
        a.vblank()
        if k in (5, 30, 60, 90, 120, 150, 200, 260, 300):
            request(a, 2)
        if k in (33, 95, 160, 210):
            request(a, 3 if k % 2 else 4)
        a.pass_()
    a.call(lab["snd_stop"], irq=False)
    for _ in range(2):
        a.vblank()
    a.call(lab["snd_stop"], irq=False)
    for _ in range(130):
        a.vblank()
    a.call(lab["snd_stop"], irq=False)
    a.vblank()
    b = setup(rom, lab, mode, hz50)
    b.bus.ram[lab["snd_div"]] = a.bus.ram[lab["snd_div"]]
    out = []
    for m in (a, b):
        m.bus.log.clear()
        m.bus.ram[lab["act_a000"]] = lab["BANK_FRONT"]
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
        bad.append("the title's chip writes differ from a fresh title's first at VBLANK %d: %s / %s" % (
            k, ra[k][:4], rb[k][:4]))
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
    writes = sum(len(x[1]) if x and x[0] == "start" else len(x) for x in rb)
    return bad, other, writes


def bs_log(rom: bytes, lab: dict, mode: int, hz50: bool, ticks: int) -> list:
    """Brainstorm's sound on an image (pzsim's machine): bsu_t (tn_pzm), requests through snd_bfx
    (moves, a red chip refused, the jingle, the buzz restarted every pass, two requests in one pass,
    effects after the tune's end), a board's restart; every chip write, VBLANK by VBLANK."""
    m = pzsim.Machine(rom, lab, mode, hz50)
    reqs = {10: [4], 11: [3], 16: [3], 17: [3], 40: [4], 60: [5], 70: [4], 108: [4], 109: [4], 120: [4, 3],
            366: [5], 367: [5], 415: [3], 416: [3], 2995: [4], 3010: [5], 3070: [4]}
    for t in range(300, 331):
        reqs[t] = [6]
    out = []
    m.bus.log.clear()
    pzsim.tune_start(m)
    out.append(("start", tuple(m.bus.log)))
    m.bus.log.clear()
    while m.ticks < ticks:
        m.vblank()
        out.append(tuple(m.bus.log))
        m.bus.log.clear()
        for n in reqs.get(m.ticks, []):
            m.call(lab["snd_bfx"], a=n, irq=False)
        m.pass_()
        if m.ticks == 1500:
            pzsim.tune_start(m)
            out.append(("restart", tuple(m.bus.log)))
            m.bus.log.clear()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("rom", type=Path)
    ap.add_argument("labels", type=Path)
    ap.add_argument("--ticks", type=int, default=6100)
    ap.add_argument("--only", default="")
    ap.add_argument("--modes", default="1,5,6,0")
    ap.add_argument("--hz", default="50,60")
    ap.add_argument("--old", nargs=2, type=Path)
    args = ap.parse_args()
    only = set(filter(None, args.only.split(",")))
    want = lambda k: not only or k in only
    rom = args.rom.read_bytes()
    lab = pzsim.labels(args.labels)
    modes = [(n, m) for n, m in MODES if str(m) in args.modes.split(",")]
    total = 0
    if want("run"):
        reqs = plan_requests(args.ticks)
        for name, mode in modes:
            for hz in args.hz.split(","):
                bad, d = run(args.root, rom, lab, mode, {"ticks": args.ticks, "requests": reqs}, hz == "50")
                print("%-18s %s Hz, %d ticks (the tune's 5,999 and after), %d effects started, %d refused, tick 0 at "
                      "%s, R6 shared by two audible noises on %d ticks: %s" % (
                          name, hz, args.ticks, len(d["started"]), len(d["refused"]), d["tick0"], d["shared"],
                          "PASS" if not bad else "FAIL"), flush=True)
                if hz == "50" and mode == 1:
                    print("    refused (tick, effect): %s" % d["refused"][:12])
                for b in bad[:12]:
                    print("   ", b)
                total += len(bad)
    if want("r800"):
        reqs = plan_requests(1200)
        for name, mode in (("SCC + OPLL", MM_SCC | MM_RHY), ("OPLL alone", MM_FM | MM_RHY)):
            bad, d = run(args.root, rom, lab, mode, {"ticks": 1200, "requests": reqs}, True, r800=True)
            print("R800, %-11s 1200 ticks, effects, no OPLL write: %s" % (name + ":", "PASS" if not bad else "FAIL"))
            for b in bad[:12]:
                print("   ", b)
            total += len(bad)
    if want("stop"):
        for name, mode in MODES:
            bad, d = run(args.root, rom, lab, mode, {"ticks": 500, "requests": {150: [2], 196: [3]}, "stop": 200})
            print("%-18s snd_stop mid-tune at 200 (an effect sounding): no write after it: %s" % (
                name, "PASS" if not bad else "FAIL"))
            for b in bad[:12]:
                print("   ", b)
            total += len(bad)
    if want("edges"):
        bad, cases = edges(args.root, rom, lab)
        print("$1822C's rule against tools/rc2music.py's 68000 model of FRM: %d cases (every pair of effects 2-4, "
              "j = 1, L - 1, L, L + 1, four chip sets), the lengths: %s" % (cases, "PASS" if not bad else "FAIL"))
        for b in bad[:12]:
            print("   ", b)
        total += len(bad)
    if want("title"):
        for name, mode in MODES:
            for hz in (True, False):
                bad, other, writes = title_after(rom, lab, mode, hz)
                print("%-18s %d Hz: the title after the range, %d chip writes against a fresh title's: %s; "
                      "registers the title never writes, left as the range left them: %s" % (
                          name, 50 if hz else 60, writes, "PASS" if not bad else "FAIL", ", ".join(other) or "none"))
                for b in bad[:12]:
                    print("   ", b)
                total += len(bad)
    if want("bseq") and args.old:
        orom, olab = args.old[0].read_bytes(), pzsim.labels(args.old[1])
        for name, mode in MODES:
            for hz in (True, False):
                a = bs_log(orom, olab, mode, hz, 3100)
                b = bs_log(rom, lab, mode, hz, 3100)
                n = sum(len(x[1]) if x and isinstance(x[0], str) else len(x) for x in a)
                ok = a == b
                print("%-18s %d Hz: Brainstorm's tune and effects (3,100 ticks, a restart), %d chip writes, old "
                      "image against new, VBLANK by VBLANK: %s" % (name, 50 if hz else 60, n,
                                                                    "identical" if ok else "DIFFER"))
                if not ok:
                    k = next(i for i in range(min(len(a), len(b))) if a[i] != b[i])
                    print("    first at %d: %s / %s" % (k, a[k][:4], b[k][:4]))
                total += not ok
    print("all: %s" % ("PASS" if not total else "FAIL (%d)" % total))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
