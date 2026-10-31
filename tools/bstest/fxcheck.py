#!/usr/bin/env python3
"""fxcheck.py: the in-game sound effects write for write (docs/LEVEL2.md 4.3, docs/HARNESS.md 5.23).

  fxcheck.py check LOG ROM LABELS [--bench REF.jsonl] [--expect scc|ext|psg] [--show N]
  fxcheck.py visits LOG_A LOG_B
  fxcheck.py selftest LOG ROM LABELS

check: LOG is a tools/bstest/fxlog.tcl log of a run of ROM (its z80asm label file LABELS). From the
state the log's I line holds (the engine's RAM at the arming), a model of the sound engine (msx/
sndplay.asm, the PSG player; msx/music.asm's in-game effects on the SCC, fx_start and fx_tick, their
data read from ROM: sccfx.bin's table and streams in SCCFX_BANK, fx_waves in BANK_MUSIC, snd_sfx and
its PSG streams in BANK_INPUT, the gun's table GUN_TAB) replays every event of the log: each request
queued (Q), taken by the VBLANK (S, G, X), each tick (T), each stop (Y: mus_quiet; Z: sq_mute), and
gives the writes each of them makes, in order. Every segment of the log (an event and the writes
after it, until the next event of the same program: the main program's or the VBLANK's) must hold
exactly those writes: the PSG's registers R0-R13 with their values, the SCC's addresses and values
(each one received by the SCC the game uses: the cartridge's, or another slot's), the OPLL's.
Besides: every request queued is taken by the VBLANK, in order (a full queue drops one: none may
be); a tick comes exactly where the player's divider gives one (50 Hz: every VBLANK; 60 Hz: five of
six); the engine's variables at the log's end (E) equal the model's; per effect number its starts,
those the priority rule ($1822C: a lower effect than the last one is not played while the Amiga's
channel 3 plays one) refused, and those played whole (every part of it to its stream's end, not cut
by another start or a stop). --bench: the requests the main program queued in each game frame (F)
equal the reference's ($B31 ... $B2C at that frame, frame_keys' order; effect 3, the gun's
opening, as SQ_GUN once, at its first frame). Text screens (B ... b: front.asm fe_text): after their
own stop no write at all. --expect: the chips the run must have used. Exit 0 only when all of it
holds ("fxcheck: PASS").

visits: the stages' tunes in two logs (their U lines: the chips at every tick of tune.asm, N at
each tune's start) equal tick for tick: Brainstorm's PZM and the range's FRM of visit 2 against
visit 1 (docs/LEVEL2.md 4.3).

selftest: LOG must pass, and every one of a set of mutations of it (a PSG write's value, an SCC
write's value or address, a write missing, a write more, two writes swapped, a start lost, a tick
lost, a request lost) must fail.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MV_PTR, MV_BANK, MV_LEFT, MV_CTL, MV_PER, MV_AUX, MV_NEW, MV_RV, MV_SIZE = 0, 2, 3, 4, 5, 7, 11, 12, 16
SV_PTR, SV_LEFT, SV_CTL, SV_PER, SV_NOISE, SV_LOOP, SV_CH, SV_SIZE = 0, 2, 3, 4, 6, 7, 9, 10
SQ_GUN, SQ_MUSIC, SQ_STOP, SQ_N = 0xFD, 0xFE, 0xFF, 8
MM_SCC, MM_FM, MM_RHY = 1, 2, 4
RAM0 = 0xC000                       # fxlog.tcl's I and E lines: C000h-CFFFh
FD_TAB = [                          # music.asm fd_tab: the SCC's volumes at each fade step
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], [0, 1, 1, 2, 3, 4, 4, 5, 6, 6, 7, 8, 8, 9, 10, 11],
    [0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8], [0, 0, 1, 1, 1, 2, 2, 2, 3, 3, 4, 4, 4, 5, 5, 5],
    [0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 4, 4], [0, 0, 0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 3],
    [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2], [0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1], [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1]]
# the engine's variables compared at the log's end (name, bytes)
STATE = (("mus_v", 4 * MV_SIZE), ("fx_pv", 3 * MV_SIZE), ("fx_wc", 4), ("fx_act", 1), ("fx_son", 1),
         ("fx_tmp", 1), ("snd_v", 3 * SV_SIZE), ("snd_div", 1), ("snd_mix", 1), ("snd_last", 1),
         ("snd_qh", 1), ("snd_qt", 1), ("snd_q", SQ_N), ("mus_on", 1), ("mus_att", 1), ("mus_fade", 1),
         ("scc_wb", 32))
LABELS_NEEDED = ("SCCFX_BANK", "BANK_INPUT", "BANK_MUSIC", "GUN_FX", "GUN_TAB", "SND_SFX_N", "snd_sfx",
                 "fx_waves", "TN_MARK", "SCC_FREQ", "SCC_VOL", "SCC_ON", "SCC_WAVE", "mus_v", "fx_pv",
                 "fx_wc", "fx_act", "fx_son", "fx_tmp", "snd_v", "snd_div", "snd_mix", "snd_last",
                 "snd_qh", "snd_qt", "snd_q", "mus_on", "mus_att", "mus_fade", "mus_mode", "mus_dc",
                 "scc_pg2", "scc_wb", "cpu_cur")
MAIN_EVENTS = "FQZYBb"
ISR_EVENTS = "SGXMT"


class ModelError(Exception):
    """An event the model does not cover (the title's music, a tune of the stages, the fade)."""


def read_labels(path: Path | str) -> dict[str, int]:
    labels = {}
    for line in Path(path).read_text(errors="replace").splitlines():
        m = re.match(r"^([A-Za-z_][\w.]*):\s+equ \$([0-9a-fA-F]+)\s*$", line)
        if m:
            labels[m[1]] = int(m[2], 16)
    return labels


class Engine:
    """The sound engine of msx/sndplay.asm and msx/music.asm's in-game effects, routine for
    routine, on a copy of its RAM (C000h-CFFFh) and the ROM's data. Each event method returns the
    chip writes the routine makes, in order: ("P", register, value), ("C", address, value),
    ("O", register, value)."""

    def __init__(self, rom: bytes, labels: dict[str, int], ram: bytes, rg9: int):
        missing = [k for k in LABELS_NEEDED if k not in labels]
        if missing:
            raise ValueError("labels missing: " + ", ".join(missing))
        self.rom, self.L, self.ram, self.rg9 = rom, labels, bytearray(ram), rg9
        self.script = labels.get("INPUT_SCRIPT", 0)
        self.diag = labels.get("DIAG", 0)
        self.w: list[tuple] = []
        self.owner: dict[tuple, int] = {}          # ("scc", b) / ("fxp", v) / ("psg", v) -> start id
        self.parts: dict[int, dict] = {}           # start id -> {"n": effect, "left": parts, "cut": bool}
        self.next_id = 0
        self.warn: list[str] = []
        self.scope: list[int] = []                 # SCC: requests on channels 0-2 played that $1822C refuses

    # ----- memory
    def r8(self, a: int) -> int:
        return self.ram[a - RAM0]

    def w8(self, a: int, v: int) -> None:
        self.ram[a - RAM0] = v & 0xFF

    def r16(self, a: int) -> int:
        return self.r8(a) | self.r8(a + 1) << 8

    def w16(self, a: int, v: int) -> None:
        self.w8(a, v)
        self.w8(a + 1, v >> 8)

    def rom8(self, bank: int, addr: int, base: int) -> int:
        return self.rom[bank * 0x2000 + addr - base]

    def win8(self, addr: int, a000: int) -> int:
        """A byte of the 8000h window (SCCFX_BANK while the player and the effects run) or the
        A000h window (bank a000)."""
        if 0x8000 <= addr < 0xA000:
            return self.rom8(self.L["SCCFX_BANK"], addr, 0x8000)
        if 0xA000 <= addr < 0xC000:
            return self.rom8(a000, addr, 0xA000)
        raise ModelError(f"a stream read at {addr:04X}h (not in the 8000h or A000h window)")

    def v(self, name: str) -> int:
        return self.r8(self.L[name])

    def setv(self, name: str, val: int) -> None:
        self.w8(self.L[name], val)

    # ----- the effects' ownership (played whole, cut)
    def take(self, key: tuple) -> None:
        sid = self.owner.pop(key, None)
        if sid is not None and sid in self.parts:
            p = self.parts[sid]
            p["cut"] = True
            p["left"] -= 1

    def own(self, key: tuple, sid: int) -> None:
        self.take(key)
        self.owner[key] = sid
        self.parts[sid]["left"] += 1
        self.parts[sid]["n_parts"] += 1

    def ended(self, key: tuple) -> None:
        sid = self.owner.pop(key, None)
        if sid is not None and sid in self.parts:
            self.parts[sid]["left"] -= 1

    def new_start(self, n: int) -> int:
        sid = self.next_id
        self.next_id += 1
        self.parts[sid] = {"n": n, "left": 0, "n_parts": 0, "cut": False, "refused": False}
        return sid

    # ----- the chips' outputs
    def psg(self, r: int, val: int) -> None:
        self.w.append(("P", r, val & 0xFF))

    def scc(self, a: int, val: int) -> None:
        self.w.append(("C", a, val & 0xFF))

    def opll(self, r: int, val: int) -> None:
        self.w.append(("O", r, val & 0xFF))

    def mixer(self, voice: int, ctl: int) -> None:
        d = 1 << voice
        nb = d << 3
        a = ((self.v("snd_mix") | d | nb) & 0x3F) | 0x80
        if ctl & 0x10:
            a ^= d
        if ctl & 0x20:
            a ^= nb
        self.setv("snd_mix", a)
        self.psg(7, a)

    # ----- sndplay.asm: the PSG player
    def sv(self, b: int) -> int:
        return self.L["snd_v"] + SV_SIZE * b

    def sq_out(self, b: int) -> None:
        ix = self.sv(b)
        self.psg(2 * b, self.r8(ix + SV_PER))
        self.psg(2 * b + 1, self.r8(ix + SV_PER + 1))
        vol = self.r8(ix + SV_CTL) & 15
        if not self.script:
            vol = max(0, vol - self.v("mus_att"))
        self.psg(8 + b, vol)
        c = self.r8(ix + SV_CTL)
        if c & 0x20:
            self.psg(6, self.r8(ix + SV_NOISE))
        self.mixer(b, c)

    def sq_off(self, b: int) -> None:
        ix = self.sv(b)
        self.w8(ix + SV_LEFT, 0)
        self.w8(ix + SV_CTL, 0)
        self.sq_out(b)

    def sq_rec(self, b: int) -> None:
        ix = self.sv(b)
        hl = self.r16(ix + SV_PTR)
        bi = self.L["BANK_INPUT"]
        a = self.win8(hl, bi)
        hl += 1
        if a == 0:
            if self.r16(ix + SV_LOOP):
                raise ModelError("a title stream's end (mus_end)")
            self.ended(("psg", b))
            self.sq_off(b)
            return
        self.w8(ix + SV_LEFT, a)
        c = self.win8(hl, bi)
        hl += 1
        self.w8(ix + SV_CTL, c)
        if c & 0x40:
            self.w8(ix + SV_PER, self.win8(hl, bi))
            self.w8(ix + SV_PER + 1, self.win8(hl + 1, bi))
            hl += 2
        if c & 0x80:
            self.w8(ix + SV_NOISE, self.win8(hl, bi))
            hl += 1
        self.w16(ix + SV_PTR, hl)
        self.sq_out(b)

    def sq_stop(self) -> None:
        for b in range(3):
            self.w8(self.sv(b) + SV_CH, 0xFF)
            self.take(("psg", b))
            self.sq_off(b)
        self.setv("mus_fade", 0)
        self.setv("mus_att", 0)

    def sq_three(self, tab: int) -> None:
        sid = self.new_start(self.L["GUN_FX"])
        for b in range(3):
            ix = self.sv(b)
            s = self.win8(tab + 2 * b, 0) | self.win8(tab + 2 * b + 1, 0) << 8
            lp = self.win8(tab + 2 * b + 6, 0) | self.win8(tab + 2 * b + 7, 0) << 8
            self.w16(ix + SV_PTR, s)
            self.w16(ix + SV_LOOP, lp)
            self.w8(ix + SV_CH, 0xFF)
            self.own(("psg", b), sid)
            self.sq_rec(b)

    def sq_sfx(self, n: int) -> str:
        """An effect taken from the queue: 'started', 'refused' (the priority rule) or 'ignored'."""
        if n == 0 or n > self.L["SND_SFX_N"]:
            return "ignored"
        if self.v("mus_mode") & 1:
            return self.fx_start(n)
        for b in range(3):
            ix = self.sv(b)
            if self.r8(ix + SV_CH) == 3 and self.r8(ix + SV_LEFT):
                if n < self.v("snd_last"):
                    sid = self.new_start(n)
                    self.parts[sid]["refused"] = True
                    return "refused"
                break
        self.setv("snd_last", n)
        e = self.L["snd_sfx"] + 3 * (n - 1)
        bi = self.L["BANK_INPUT"]
        stream = self.rom8(bi, e, 0xA000) | self.rom8(bi, e + 1, 0xA000) << 8
        ch = self.rom8(bi, e + 2, 0xA000)
        if ch < 3:
            b = ch
        else:
            h, l = 0xFF, 0
            for c in (2, 1, 0):
                left = self.r8(self.sv(c) + SV_LEFT)
                if left < h:
                    h, l = left, c
            b = l
        ix = self.sv(b)
        self.w8(ix + SV_CH, ch)
        self.w16(ix + SV_LOOP, 0)
        self.w16(ix + SV_PTR, stream)
        sid = self.new_start(n)
        self.own(("psg", b), sid)
        self.sq_rec(b)
        return "started"

    def sq_gun(self) -> None:
        if self.v("mus_mode") & 1:
            self.fx_start(self.L["GUN_FX"])
        else:
            self.sq_three(self.L["GUN_TAB"])

    # ----- music.asm: the in-game effects with an SCC
    def mv(self, b: int) -> int:
        return self.L["mus_v"] + MV_SIZE * b

    def pv(self, b: int) -> int:
        return self.L["fx_pv"] + MV_SIZE * b

    def scc_pvs(self, b: int, c: int, de: int, vol: int) -> None:
        if c & 0x10:
            self.scc(self.L["SCC_FREQ"] + 2 * b, de)
            self.scc(self.L["SCC_FREQ"] + 2 * b + 1, de >> 8)
        self.scc(self.L["SCC_VOL"] + b, vol)
        self.scc(self.L["SCC_ON"], 7 if self.v("mus_on") else 0x0F)

    def fx_wave(self, w: int, i: int) -> int:
        return self.rom8(self.L["BANK_MUSIC"], self.L["fx_waves"] + 32 * w + i, 0xA000)

    def fxr_wc(self, b: int, ix: int) -> bool:
        """NZ (True) when the channel does not hold the waveform yet; fx_wc notes it."""
        a = self.L["fx_wc"] + b
        new = self.r8(ix + MV_AUX) != self.r8(a)
        self.w8(a, self.r8(ix + MV_AUX))
        return new

    def fd_scc(self, vol: int) -> int:
        att = self.v("mus_att")
        if not att:
            return vol
        return 0 if att >= len(FD_TAB) else FD_TAB[att][vol]

    def mo_sc1(self, b: int, ix: int) -> None:
        c = self.r8(ix + MV_NEW)
        if not c:
            return
        if c & 0x20:
            if self.v("mus_on"):
                raise ModelError("the title music's waveform")
            w = self.r8(ix + MV_AUX)
            for i in range(32):
                self.w8(self.L["scc_wb"] + i, self.fx_wave(w, i))
            for i in range(32):
                self.scc(self.L["SCC_WAVE"] + 32 * b + i, self.r8(self.L["scc_wb"] + i))
        de = self.r16(ix + MV_PER)
        self.scc_pvs(b, c, de, self.fd_scc(self.r8(ix + MV_CTL) & 15))

    def fxr_so(self, b: int, ix: int, c: int, de: int) -> None:
        if self.v("scc_pg2") == 0:
            if c & 0x20 and self.fxr_wc(b, ix):
                w = self.r8(ix + MV_AUX)
                for i in range(32):
                    self.scc(self.L["SCC_WAVE"] + 32 * b + i, self.fx_wave(w, i))
            self.scc_pvs(b, c, de, c & 15)
            return
        self.w8(ix + MV_CTL, c)
        if c & 0x10:
            self.w16(ix + MV_PER, de)
        self.w8(ix + MV_NEW, (c & 0x30) | 1)
        if c & 0x20 and not self.fxr_wc(b, ix):
            self.w8(ix + MV_NEW, self.r8(ix + MV_NEW) & ~0x20)
        self.mo_sc1(b, ix)

    def fxr_sc(self, b: int) -> None:
        ix = self.mv(b)
        hl = self.r16(ix + MV_PTR)
        a = self.win8(hl, 0)
        if a == 0:
            self.w8(ix + MV_LEFT, 0)
            self.ended(("scc", b))
            self.fxr_so(b, ix, 0, 0)
            return
        self.w8(ix + MV_LEFT, a)
        hl += 1
        c = self.win8(hl, 0)
        hl += 1
        de = 0
        if c & 0x10:
            de = self.win8(hl, 0) | self.win8(hl + 1, 0) << 8
            hl += 2
        if c & 0x20:
            self.w8(ix + MV_AUX, self.win8(hl, 0))
            hl += 1
        self.w16(ix + MV_PTR, hl)
        self.fxr_so(b, ix, c, de)

    def mo_pw(self, e: int, ix: int) -> None:
        c = self.r8(ix + MV_CTL)
        if c & 0x10:
            self.psg(2 * e, self.r8(ix + MV_PER))
            self.psg(2 * e + 1, self.r8(ix + MV_PER + 1))
        self.psg(8 + e, max(0, (c & 15) - self.v("mus_att")))
        if c & 0x20:
            self.psg(6, self.r8(ix + MV_AUX))
        self.mixer(e, c)

    def fxr_ps(self, b: int) -> None:
        ix = self.pv(b)
        hl = self.r16(ix + MV_PTR)
        a = self.win8(hl, 0)
        if a == 0:
            self.w8(ix + MV_LEFT, 0)
            self.w8(ix + MV_CTL, 0)
            self.ended(("fxp", b))
            self.mo_pw(b, ix)
            return
        self.w8(ix + MV_LEFT, a)
        hl += 1
        c = self.win8(hl, 0)
        hl += 1
        self.w8(ix + MV_CTL, c)
        if c & 0x40:
            self.w8(ix + MV_PER, self.win8(hl, 0))
            self.w8(ix + MV_PER + 1, self.win8(hl + 1, 0))
            hl += 2
        if c & 0x80:
            self.w8(ix + MV_AUX, self.win8(hl, 0))
            hl += 1
        self.w16(ix + MV_PTR, hl)
        self.mo_pw(b, ix)

    def fx_ofs(self, hl: int) -> tuple[int, int]:
        e, d, h = self.win8(hl, 0), self.win8(hl + 1, 0), self.win8(hl + 2, 0)
        if not (e | d | h):
            return 0, hl + 3
        bank = self.L["SCCFX_BANK"] + (h << 3 | d >> 5)
        if bank != self.L["SCCFX_BANK"]:
            self.warn.append(f"a stream in bank {bank} (read in SCCFX_BANK's window, as music.asm does)")
        return 0x8000 | (d & 0x1F) << 8 | e, hl + 3

    def fx_busy3(self) -> bool:
        if self.r8(self.mv(3) + MV_LEFT):
            return True
        return any(self.r8(self.pv(c) + MV_LEFT) and self.r8(self.pv(c) + MV_RV + 1) == 3 for c in range(3))

    def fx_pown(self, b: int) -> None:
        for c in range(3):
            ix = self.pv(c)
            if self.r8(ix + MV_LEFT) and self.r8(ix + MV_RV + 1) == b:
                self.w8(ix + MV_LEFT, 0)
                self.w8(ix + MV_CTL, 0)
                self.w8(ix + MV_NEW, 1)
                self.take(("fxp", c))
                self.mo_pw(c, ix)

    def fx_pfree(self) -> int:
        h, l = 0xFF, 0
        for c in (2, 1, 0):
            left = self.r8(self.pv(c) + MV_LEFT)
            if left < h:
                h, l = left, c
        return l

    def scc_on(self, a: int) -> None:
        self.scc(self.L["SCC_ON"], a)

    def fxs_one(self, n: int, sid: int | None = None) -> str:
        if self.v("mus_on"):
            return "ignored"
        e = 0x8004 + 7 * (n - 1)
        b = self.win8(e, 0)
        hl = e + 1
        res = "started"
        lower = self.fx_busy3() and n < self.v("snd_last")
        if b == 3 and lower:
            res = "refused"
        else:
            if lower and n < 0x80 and n != self.L["GUN_FX"] + 1 and n != self.L["GUN_FX"] + 2:
                self.scope.append(n)   # (music.asm refuses only channel 3's; the original every one)
            self.setv("snd_last", n)
            if sid is None:
                sid = self.new_start(n)
            ix = self.mv(b)
            ptr, hl = self.fx_ofs(hl)
            if ptr:
                self.w16(ix + MV_PTR, ptr)
                self.own(("scc", b), sid)
                self.fxr_sc(b)
            else:
                self.w8(ix + MV_LEFT, 0)
                self.take(("scc", b))
                self.fxr_so(b, ix, 0, 0)
            ptr2, hl = self.fx_ofs(hl)
            self.fx_pown(b)
            voice = b if b < 3 else self.fx_pfree()
            self.setv("fx_tmp", voice)
            if ptr2:
                ix = self.pv(voice)
                self.w8(ix + MV_RV, voice)
                self.w8(ix + MV_RV + 1, b)
                self.w16(ix + MV_PTR, ptr2)
                self.own(("fxp", voice), sid)
                self.fxr_ps(voice)
        self.setv("fx_act", 1)
        if self.v("fx_son") != 1:
            self.setv("fx_son", 1)
            self.scc_on(0x0F)
        if res == "refused":
            s = self.new_start(n)
            self.parts[s]["refused"] = True
        return res

    def fx_start(self, n: int) -> str:
        if n == self.L["GUN_FX"] and not self.diag:
            sid = self.new_start(n)
            for k in range(3):
                self.fxs_one(n + k, sid)
            self.setv("snd_last", 3)
            return "started"
        return self.fxs_one(n)

    def fx_tick(self) -> None:
        if self.v("mus_on"):
            return
        for b in range(4):
            ix = self.mv(b)
            if self.r8(ix + MV_LEFT):
                self.w8(ix + MV_LEFT, self.r8(ix + MV_LEFT) - 1)
                if not self.r8(ix + MV_LEFT):
                    self.fxr_sc(b)
        for b in range(3):
            ix = self.pv(b)
            if self.r8(ix + MV_LEFT):
                self.w8(ix + MV_LEFT, self.r8(ix + MV_LEFT) - 1)
                if not self.r8(ix + MV_LEFT):
                    self.fxr_ps(b)
        act = 0
        for b in range(4):
            act |= self.r8(self.mv(b) + MV_LEFT)
        for b in range(3):
            act |= self.r8(self.pv(b) + MV_LEFT)
        self.setv("fx_act", act)

    def mus_quiet(self) -> None:
        for k in ("mus_on", "mus_fade", "mus_att"):
            self.setv(k, 0)
        self.w8(self.L.get("mus_speak", self.L["mus_on"] + 2), 0)
        for b in range(4):
            self.w8(self.mv(b) + MV_LEFT, 0)
            self.w8(self.mv(b) + MV_NEW, 0)
            self.take(("scc", b))
        for b in range(3):
            self.w8(self.pv(b) + MV_LEFT, 0)
            self.w8(self.pv(b) + MV_NEW, 0)
            self.take(("fxp", b))
        self.setv("fx_act", 0)
        self.setv("fx_son", 0)
        for b in range(4):
            self.w8(self.L["fx_wc"] + b, 0xFF)
        mode = self.v("mus_mode")
        if mode & 1:
            self.scc_on(0)
            for b in range(5):
                self.scc(self.L["SCC_VOL"] + b, 0)
        if (self.diag or not self.v("cpu_cur")) and mode & (MM_FM | MM_RHY):
            self.opll(0x0E, 0)
            for r in (0x20, 0x21, 0x22):
                self.opll(r, 0)
        self.psg(10, 0)
        if self.v("mus_dc"):
            raise ModelError("mus_quiet with the speech's DC held (dc_fall)")

    # ----- the events
    def ev_Y(self) -> None:
        self.mus_quiet()

    def ev_Z(self) -> None:
        for r in (8, 9, 10):
            self.psg(r, 0)

    def ev_X(self) -> None:
        self.sq_stop()

    def ev_G(self) -> None:
        self.sq_gun()

    def ev_T(self) -> None:
        if not self.v("mus_mode") & 1:
            for b in range(3):
                ix = self.sv(b)
                if self.r8(ix + SV_LEFT):
                    self.w8(ix + SV_LEFT, self.r8(ix + SV_LEFT) - 1)
                    if not self.r8(ix + SV_LEFT):
                        self.sq_rec(b)
            if not self.script and self.v("mus_mode") == 0 and self.v("mus_fade"):
                raise ModelError("the title music's fade on the PSG player")
        if self.v("fx_act"):
            if self.r8(self.sv(0) + SV_CH) == self.L["TN_MARK"]:
                raise ModelError("a tune of the stages ticks (tune.asm)")
            if self.v("mus_mode") & 1:
                self.fx_tick()
            else:
                self.setv("fx_act", 0)

    def tick_due(self) -> bool:
        """sq_frame's divider at a VBLANK: True when this VBLANK ticks."""
        if self.rg9 & 2:
            return True
        d = (self.v("snd_div") + 1) & 0xFF
        if d < 6:
            self.setv("snd_div", d)
            return True
        self.setv("snd_div", 0)
        return False

    def queue_put(self, a: int) -> bool:
        qt, qh = self.v("snd_qt"), self.v("snd_qh")
        nt = (qt + 1) & (SQ_N - 1)
        if nt == qh:
            return False
        self.w8(self.L["snd_q"] + qt, a)
        self.setv("snd_qt", nt)
        return True

    def queue_take(self) -> int | None:
        qt, qh = self.v("snd_qt"), self.v("snd_qh")
        if qh == qt:
            return None
        a = self.r8(self.L["snd_q"] + qh)
        self.setv("snd_qh", (qh + 1) & (SQ_N - 1))
        return a

    def run(self, kind: str, arg: int | None) -> tuple[list, str | None]:
        self.w = []
        res = None
        if kind == "S":
            res = self.sq_sfx(arg)
        elif kind in "YZXGT":
            getattr(self, "ev_" + kind)()
        elif kind == "M":
            raise ModelError("the title's music (sq_title)")
        return self.w, res


# ----- the log

def parse_log(path: Path | str) -> list[tuple]:
    """fxlog.tcl's lines as (kind, args, line number)."""
    out = []
    for i, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line or line[0] == "#":
            continue
        k, _, rest = line.partition(" ")
        out.append((k, rest.split() if rest else [], i))
    return out


def fmt_w(w: tuple) -> str:
    k, a, v = w[:3]
    return f"{k} {a:04X}h={v:02X}h" if k == "C" else f"{k} R{a}={v:02X}h"


class Checker:
    def __init__(self, rom: bytes, labels: dict[str, int], show: int = 8):
        self.rom, self.L, self.show = rom, labels, show
        self.errors: list[str] = []
        self.nerr = 0
        self.notes: list[str] = []

    def err(self, s: str) -> None:
        self.nerr += 1
        if len(self.errors) < self.show:
            self.errors.append(s)

    def check(self, events: list[tuple], expect: str | None = None, bench: list[dict] | None = None) -> bool:
        first = next((i for i, e in enumerate(events) if e[0] == "I"), None)
        if first is None:
            self.err("no I line: the log was never armed")
            return False
        ram = bytes.fromhex(events[first][1][0])
        rg9 = int(events[first][1][1], 16)
        eng = Engine(self.rom, self.L, ram, rg9)
        self.eng = eng
        mode = eng.v("mus_mode")
        pg2 = eng.v("scc_pg2")
        kind = ("ext" if pg2 else "scc") if mode & 1 else "psg"
        self.kind = kind
        self.notes.append(f"chips: {'the SCC in another slot (A8h bits ' + format(pg2, '02X') + 'h)' if kind == 'ext' else 'the SCC in the cartridge' if kind == 'scc' else 'the PSG alone'}"
                          f" (mus_mode {mode}), {'50' if rg9 & 2 else '60'} Hz, {'a script build' if eng.script else 'no script'}")
        if expect and expect != kind:
            self.err(f"the run used {kind}, expected {expect}")
        want_k = "x" if kind == "ext" else "c"
        # segments: per program the event in effect and the writes seen since
        seg = {"main": None, "isr": None}
        ctx = ["main"]
        cnt = {"V": 0, "T": 0, "F": 0, "Q": 0, "S": 0, "P": 0, "C": 0, "O": 0, "seg": 0}
        starts: dict[int, list] = {}     # effect -> [started, refused, ignored]
        pend: list[tuple] = []           # requests in the model's queue: (value, Q's event index)
        last_main = None                 # (event index, kind) of the main program's last event
        tick_due = False
        tick_seen = False
        frame = None
        frame_q: dict[int, list[int]] = {}
        gun_frames: list[int] = []
        q0c: list[int] = []
        s0c: list[tuple] = []
        texts: list[dict] = []
        text = None
        delays: list[int] = []
        v_count = 0
        q_at: dict[int, int] = {}        # Q event index -> the VBLANK count then
        drops = 0
        # the queue at the arming: requests the VBLANK has still to take
        qh, qt = eng.v("snd_qh"), eng.v("snd_qt")
        while qh != qt:
            pend.append((eng.r8(eng.L["snd_q"] + qh), -1))
            qh = (qh + 1) & (SQ_N - 1)
        frames: list[int] = []

        self.cut_end = False

        def close(p: str, final: bool = False) -> None:
            s = seg[p]
            if s is None:
                return
            ev, exp, got, line = s
            cnt["seg"] += 1
            gw = [g[:3] for g in got]
            if exp != gw:
                i = next((j for j in range(min(len(exp), len(gw))) if exp[j] != gw[j]), min(len(exp), len(gw)))
                e1 = fmt_w(exp[i]) if i < len(exp) else "nothing"
                g1 = fmt_w(got[i][:3]) if i < len(got) else "nothing"
                at = got[i][3] if i < len(got) else line
                if not (final and len(gw) < len(exp) and exp[:len(gw)] == gw):
                    self.err(f"line {at}: {ev} (line {line}): write {i + 1} of {len(exp)} expected: {e1}, logged: {g1}"
                             f" ({len(got)} logged)")
                else:
                    self.notes.append(f"the last {ev} (line {line}) cut by the end: {len(got)} of {len(exp)} writes, as expected")
                    self.cut_end = True
            seg[p] = None

        def open_(p: str, ev: str, exp: list, line: int) -> None:
            close(p)
            seg[p] = (ev, exp, [], line)

        for idx in range(first + 1, len(events)):
            k, args, line = events[idx]
            p = ctx[-1]
            if k == "U":
                continue
            if k == "M":                 # (sq_title in the VBLANK, mus_start in the main program)
                close("main", True)
                close("isr", True)
                self.notes.append(f"the title's music starts at line {line}: the check ends there (not modelled)")
                break
            try:
                if k == "N":
                    raise ModelError("a tune of the stages starts (tns_go)")
                if k in "PCO":
                    if k == "C":
                        a, val, where = int(args[0], 16), int(args[1]), args[2]
                        if where != want_k:
                            self.err(f"line {line}: an SCC write to {a:04X}h went to '{where}' (the chips used: {want_k})")
                    else:
                        a, val = int(args[0]), int(args[1])
                    cnt[k] += 1
                    if seg[p] is None:
                        open_(p, "(no event)", [], line)
                    seg[p][2].append((k, a, val, line))
                    if text is not None and text["stopped"] and seg[p][0][0] not in "YZX":
                        text["after"] += 1
                    continue
                if k == "V":
                    if p == "isr":
                        self.err(f"line {line}: a VBLANK inside the VBLANK's sound work")
                    ctx.append("isr")
                    v_count += 1
                    cnt["V"] += 1
                    tick_due = eng.tick_due()
                    tick_seen = False
                    open_("isr", "V", [], line)
                    continue
                if k == "W":
                    if p != "isr":
                        self.err(f"line {line}: W outside the VBLANK's sound work")
                        continue
                    close("isr")
                    if tick_due and not tick_seen:
                        self.err(f"line {line}: no tick at a VBLANK the divider ticks")
                    # requests left in the queue: only one sq_put had not finished (its Q the main
                    # program's last event, or that and its own Z)
                    for j, (a, qi) in enumerate(pend):
                        if not (j == len(pend) - 1 and qi >= 0 and last_main is not None
                                and (last_main[0] == qi or (last_main[1] == "Z" and last_main[2] == qi))):
                            self.err(f"line {line}: request {a:02X}h (queued at line {events[qi][2] if qi >= 0 else '?'})"
                                     f" not taken by this VBLANK")
                            break
                    ctx.pop()
                    continue
                if k in ISR_EVENTS:
                    if p != "isr":
                        self.err(f"line {line}: {k} outside the VBLANK's sound work")
                    if k == "T":
                        cnt["T"] += 1
                        if not tick_due:
                            self.err(f"line {line}: a tick at a VBLANK the divider skips")
                        tick_seen = True
                        exp, _ = eng.run("T", None)
                        open_("isr", "T", exp, line)
                        continue
                    val = {"S": None, "G": SQ_GUN, "X": SQ_STOP}[k]
                    if k == "S":
                        val = int(args[0])
                        cnt["S"] += 1
                    taken = eng.queue_take()
                    if not pend or taken is None:
                        self.err(f"line {line}: {k} {val:02X}h taken, the queue empty")
                    else:
                        qa, qi = pend.pop(0)
                        if qa != val or taken != val:
                            self.err(f"line {line}: {k} {val:02X}h taken, {qa:02X}h queued first")
                        if qi >= 0:
                            delays.append(v_count - q_at[qi])
                    exp, res = eng.run(k, val)
                    if k == "S":
                        st = starts.setdefault(val, [0, 0, 0])
                        st[["started", "refused", "ignored"].index(res)] += 1
                        if val == 0x0C:
                            s0c.append((frame, res))
                    open_("isr", f"{k} {val:02X}h", exp, line)
                    if k == "X" and text is not None and not text["stopped"]:
                        text["stopped"] = True
                    continue
                # the main program's events
                if p != "main":
                    self.err(f"line {line}: {k} inside the VBLANK's sound work")
                if k == "F":
                    frame = int(args[0])
                    frames.append(frame)
                    cnt["F"] += 1
                    open_("main", "F", [], line)
                elif k == "Q":
                    a = int(args[0])
                    cnt["Q"] += 1
                    if eng.queue_put(a):
                        pend.append((a, idx))
                        q_at[idx] = v_count
                    else:
                        drops += 1
                        self.err(f"line {line}: request {a:02X}h dropped (the queue full)")
                    if frame is not None and a not in (SQ_GUN, SQ_MUSIC, SQ_STOP):
                        frame_q.setdefault(frame, []).append(a)
                    if a == SQ_GUN:
                        gun_frames.append(frame)
                    if a == 0x0C:
                        q0c.append(frame)
                    open_("main", f"Q {a:02X}h", [], line)
                elif k in "YZ":
                    exp, _ = eng.run(k, None)
                    open_("main", k, exp, line)
                    if k == "Z" and last_main is not None and last_main[1] == "Q":
                        last_main = (idx, "Z", last_main[0])
                        continue
                elif k == "B":
                    text = {"hl": int(args[0], 16), "line": line, "stopped": False, "after": 0, "noise": 0}
                    texts.append(text)
                    open_("main", "B", [], line)
                elif k == "b":
                    if text is not None:
                        text["end"] = line
                    text = None
                    open_("main", "b", [], line)
                elif k == "E":
                    close("main", True)
                    close("isr", True)
                    if self.cut_end:
                        self.notes.append("the engine's variables at the end not compared (a routine cut by the end)")
                    else:
                        self.final(eng, bytes.fromhex(args[0]))
                    break
                else:
                    self.err(f"line {line}: unknown line {k}")
                last_main = (idx, k, None)
            except ModelError as e:
                self.err(f"line {line}: not modelled: {e}")
                return False
        else:
            close("main")
            close("isr")
            self.err("no E line: the log has no end")
        # (a text screen's stop: its X, the VBLANK's; "after" counts the writes past that X's own)
        self.report(cnt, starts, eng, drops, delays, frame_q, gun_frames, q0c, s0c, texts, bench, frames)
        return self.nerr == 0

    def final(self, eng: Engine, ram: bytes) -> None:
        bad = []
        for name, n in STATE:
            a = eng.L[name] - RAM0
            if eng.ram[a:a + n] != ram[a:a + n]:
                j = next(i for i in range(n) if eng.ram[a + i] != ram[a + i])
                bad.append(f"{name}+{j}: model {eng.ram[a + j]:02X}h, logged {ram[a + j]:02X}h")
        if bad:
            self.err("the engine's variables at the end differ: " + "; ".join(bad[:6]))
        else:
            self.notes.append(f"the engine's variables at the end equal the model's ({sum(n for _, n in STATE)} bytes)")

    def report(self, cnt, starts, eng, drops, delays, frame_q, gun_frames, q0c, s0c, texts, bench, frames) -> None:
        self.notes.append(f"{cnt['V']} VBLANKs, {cnt['T']} ticks (each where the divider gives one), "
                          f"{cnt['F']} game frames")
        self.notes.append(f"requests: {cnt['Q']} queued, {cnt['S']} effects taken, every one in order"
                          f"{', ' + str(drops) + ' dropped' if drops else ', none dropped'}"
                          f"{', taken ' + str(min(delays)) + '-' + str(max(delays)) + ' VBLANKs after' if delays else ''}")
        self.notes.append(f"writes: PSG {cnt['P']}, SCC {cnt['C']}, OPLL {cnt['O']} in {cnt['seg']} segments, "
                          f"each compared with the model")
        whole: dict[int, list] = {}
        for sid, p in eng.parts.items():
            w = whole.setdefault(p["n"], [0, 0, 0])
            if p["refused"]:
                continue
            if p["left"] == 0 and not p["cut"] and p["n_parts"]:
                w[0] += 1
            elif p["cut"]:
                w[1] += 1
            else:
                w[2] += 1
        rows = []
        for n in sorted(set(starts) | {eng.L["GUN_FX"]} & set(whole)):
            st = starts.get(n, [0, 0, 0])
            w = whole.get(n, [0, 0, 0])
            name = "gun" if n == eng.L["GUN_FX"] else f"{n:02X}h"
            if n == eng.L["GUN_FX"]:
                st = [w[0] + w[1] + w[2], 0, 0]
            rows.append(f"{name} {st[0]}/{st[1]}r/{w[0]}w/{w[1]}c")
        self.effects = {(("gun" if n == eng.L["GUN_FX"] else f"{n:02X}")): {"started": starts.get(n, [0])[0],
                        "refused": starts.get(n, [0, 0])[1], "whole": whole.get(n, [0])[0],
                        "cut": whole.get(n, [0, 0])[1], "playing": whole.get(n, [0, 0, 0])[2]}
                        for n in set(starts) | set(whole)}
        self.notes.append("effects (started/refused by the priority rule/played whole/cut): " + ", ".join(rows))
        if eng.scope:
            by = {}
            for n in eng.scope:
                by[n] = by.get(n, 0) + 1
            self.notes.append(f"the priority rule's scope (open issue): {len(eng.scope)} requests on channels 0-2 played while"
                              f" channel 3 played a higher effect, which $1822C (and the PSG player) refuse: "
                              + ", ".join(f"{n:02X}h x{c}" for n, c in sorted(by.items())))
        if q0c:
            runs, cur = [], [q0c[0]]
            for f in q0c[1:]:
                if f == cur[-1] + 2:
                    cur.append(f)
                else:
                    runs.append(cur)
                    cur = [f]
            runs.append(cur)
            best = max(runs, key=len)
            started = sum(1 for f, r in s0c if r == "started")
            self.notes.append(f"0Ch: {len(q0c)} requests, the longest run every 2nd frame {len(best)} "
                              f"(frames {best[0]}-{best[-1]}); {started} of {len(s0c)} taken started")
        for t in texts:
            name = next((k for k, v in self.L.items() if v == t["hl"] and k.startswith("txt_")), f"{t['hl']:04X}h")
            if "end" not in t:
                self.err(f"text screen {name} (line {t['line']}): no end logged")
            elif not t["stopped"]:
                self.err(f"text screen {name} (line {t['line']}): no stop taken by a VBLANK")
            elif t["after"]:
                self.err(f"text screen {name} (line {t['line']}): {t['after']} writes after its stop")
            else:
                self.notes.append(f"text screen {name} (lines {t['line']}-{t['end']}): silent after its stop (0 writes)")
        if bench is not None:
            self.bench(bench, frame_q, gun_frames, frames)

    def bench(self, rows: list[dict], frame_q: dict, gun_frames: list, frames: list) -> None:
        bad = 0
        n = 0
        guns = []                        # (a level start's gun: the first row of each life asking for
        life_gun = False                 #  effect 3, which the original asks for again and again
        prev_gf = -1                     #  during the opening; a death restarts game_frame, $B00)
        done = set(frames[:-1])          # (the last F's tick did not run: the drive paused there)
        skipped = 0
        for f, r in enumerate(rows):     # (row k is tick_n k: game_frame, $B00, restarts at a death)
            if f not in done:
                skipped += 1
                continue
            ram = bytes.fromhex(r["ram"])
            want = [ram[0x2C + i] for i in range(5, -1, -1) if ram[0x2C + i] and ram[0x2C + i] != 3]
            if r["game_frame"] < prev_gf:
                life_gun = False
            prev_gf = r["game_frame"]
            if any(ram[0x2C + i] == 3 for i in range(6)) and not life_gun:
                guns.append(f)
                life_gun = True
            got = frame_q.get(f, [])
            n += len(want)
            if got != want:
                bad += 1
                self.err(f"bench: game frame {f}: requests {' '.join('%02X' % a for a in got) or '-'}, "
                         f"the reference's {' '.join('%02X' % a for a in want) or '-'}")
        extra = sorted(f for f in frame_q if f >= len(rows))
        compared = len(rows) - skipped
        if gun_frames != guns:
            self.err(f"bench: the gun's opening at frames {gun_frames}, the reference's first effect 3 of each life at {guns}")
        if not bad:
            self.notes.append(f"bench: the requests of the {compared} game frames run equal the reference's ({n} requests"
                              f"; the gun's opening once a level start, at frames {', '.join(map(str, guns))})"
                              f"{'; ' + str(skipped) + ' not run (the drive ended there)' if skipped else ''}"
                              f"{'; ' + str(len(extra)) + ' frames past it not compared' if extra else ''}")


def visits(a: Path, b: Path) -> int:
    def tunes(p):
        out, cur = [], None
        for k, args, line in parse_log(p):
            if k == "N":
                cur = []
                out.append(cur)
            elif k == "U":
                if cur is None:
                    cur = []
                    out.append(cur)
                cur.append((" ".join(args), line))
        return out
    ta, tb = tunes(a), tunes(b)
    print(f"visits: {a.name}: {len(ta)} tunes ({', '.join(str(len(t)) for t in ta)} ticks); "
          f"{b.name}: {len(tb)} tunes ({', '.join(str(len(t)) for t in tb)} ticks)")
    ok = len(ta) == len(tb) and len(ta) > 0
    for i, (x, y) in enumerate(zip(ta, tb)):
        if len(x) != len(y):
            ok = False
            print(f"  tune {i + 1}: {len(x)} against {len(y)} ticks")
        d = next((j for j in range(min(len(x), len(y))) if x[j][0] != y[j][0]), None)
        if d is not None:
            ok = False
            print(f"  tune {i + 1}, tick {d}: lines {x[d][1]} / {y[d][1]} differ")
        elif len(x) == len(y):
            print(f"  tune {i + 1}: {len(x)} ticks, every chip register equal")
    print("visits: PASS" if ok else "visits: FAIL")
    return 0 if ok else 1


def run_check(log: Path, rom: bytes, labels: dict, expect=None, bench=None, show=8, quiet=False) -> bool:
    c = Checker(rom, labels, show)
    ok = c.check(parse_log(log), expect, bench)
    if not quiet:
        print(f"fxcheck: {log}")
        for n in c.notes:
            print("  " + n)
        for e in c.errors:
            print("  DIFFER " + e)
        if c.nerr > len(c.errors):
            print(f"  ... {c.nerr - len(c.errors)} more")
        print("fxcheck: PASS" if ok else f"fxcheck: FAIL ({c.nerr})")
    return ok


def mutations(lines: list[str]) -> list[tuple[str, list[str]]]:
    """The self-test's mutations of a log's lines: each must make the check fail."""
    out = []
    ia = next(i for i, l in enumerate(lines) if l.startswith("I "))

    def first(pred, start=ia):
        return next((i for i in range(start, len(lines)) if pred(lines[i])), None)
    p = first(lambda l: l.startswith("P "))
    c = first(lambda l: l.startswith("C "))
    if p is not None:
        r, v = lines[p].split()[1:3]
        out.append(("a PSG write's value + 1", lines[:p] + [f"P {r} {(int(v) + 1) & 255}"] + lines[p + 1:]))
        out.append(("a PSG write's register", lines[:p] + [f"P {(int(r) + 1) % 14} {v}"] + lines[p + 1:]))
        out.append(("a PSG write missing", lines[:p] + lines[p + 1:]))
        out.append(("a PSG write more", lines[:p + 1] + [lines[p]] + lines[p + 1:]))
    if c is not None:
        a, v, k = lines[c].split()[1:4]
        out.append(("an SCC write's value + 1", lines[:c] + [f"C {a} {(int(v) + 1) & 255} {k}"] + lines[c + 1:]))
        out.append(("an SCC write's address", lines[:c] + [f"C {int(a, 16) ^ 1:04x} {v} {k}"] + lines[c + 1:]))
        out.append(("an SCC write to no chip", lines[:c] + [f"C {a} {v} -"] + lines[c + 1:]))
    for i in range(ia, len(lines) - 1):         # two different writes in a row swapped
        if lines[i][0] in "PC" and lines[i + 1][0] in "PC" and lines[i] != lines[i + 1]:
            out.append(("two writes swapped", lines[:i] + [lines[i + 1], lines[i]] + lines[i + 2:]))
            break
    s = first(lambda l: l.startswith("S "))
    if s is not None:
        out.append(("an effect's start lost (S)", lines[:s] + lines[s + 1:]))
    t = first(lambda l: l == "T")
    if t is not None:
        out.append(("a tick lost (T)", lines[:t] + lines[t + 1:]))
    q = first(lambda l: l.startswith("Q "))
    if q is not None:
        out.append(("a request lost (Q)", lines[:q] + lines[q + 1:]))
    e = first(lambda l: l.startswith("E "))
    if e is not None:
        hx, rg = lines[e].split()[1:3]
        a = (0xC20D - RAM0) * 2           # fx_act's byte flipped (msx.inc: C20Dh)
        hx = hx[:a] + format(int(hx[a:a + 2], 16) ^ 0x55, "02x") + hx[a + 2:]
        out.append(("the end state's fx_act", lines[:e] + [f"E {hx} {rg}"] + lines[e + 1:]))
    return out


def selftest(log: Path, rom: bytes, labels: dict) -> int:
    ok = run_check(log, rom, labels, quiet=True)
    print(f"selftest: {log.name} unmutated: {'PASS' if ok else 'FAIL'}")
    lines = log.read_text().splitlines()
    tmp = log.with_name(log.name + ".mut")
    caught = 0
    muts = mutations(lines)
    for name, ml in muts:
        tmp.write_text("\n".join(ml) + "\n")
        bad = not run_check(tmp, rom, labels, quiet=True)
        caught += bad
        print(f"  {name}: {'caught' if bad else 'NOT CAUGHT'}")
    tmp.unlink(missing_ok=True)
    good = ok and caught == len(muts) and muts
    print(f"selftest: {caught} of {len(muts)} mutations caught: {'PASS' if good else 'FAIL'}")
    return 0 if good else 1


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("check", "visits", "selftest"):
        print(__doc__, file=sys.stderr)
        return 2
    cmd, args = argv[1], argv[2:]
    if cmd == "visits":
        if len(args) != 2:
            print(__doc__, file=sys.stderr)
            return 2
        return visits(Path(args[0]), Path(args[1]))
    opts = {"--bench": None, "--expect": None, "--show": "8"}
    pos = []
    i = 0
    while i < len(args):
        if args[i] in opts:
            opts[args[i]] = args[i + 1]
            i += 2
        else:
            pos.append(args[i])
            i += 1
    if len(pos) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    log, rom, labels = Path(pos[0]), Path(pos[1]).read_bytes(), read_labels(pos[2])
    if cmd == "selftest":
        return selftest(log, rom, labels)
    bench = None
    if opts["--bench"]:
        bench = [json.loads(l) for l in Path(opts["--bench"]).read_text().splitlines() if l.strip()]
    return 0 if run_check(log, rom, labels, opts["--expect"], bench, int(opts["--show"])) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
