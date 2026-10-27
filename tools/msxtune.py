#!/usr/bin/env python3
"""Any tune of Robocop 2's music files on the MSX chips through the title's converters, and
Brainstorm's music and sound effects (PZM) for msx/tune.asm.

The converters (tools/msxsound.py: the PSG, msxscc.py: the SCC, msxfm.py: the OPLL) are written
for TITM tune 1, whose Amiga channels 0-2 are melodic and channel 3 the drums. The other tunes
mix drums and melodic instruments on every channel, so this module routes a tune first (the
routing step), and the converters then run unchanged on the routed tune:
- notes: on each Amiga channel, from a key-on to the next key-on; a note is a drum when its
  instrument is in the tune's drum set, else melodic (or speech: silent, as the title's
  SPEECH_INST);
- melodic notes go to three voices (the converters' channels 0-2): a note keeps the voice its
  Amiga channel used last when that voice is free, else takes a free one, else steals the
  quietest (the ticks lost are counted); the audible part of each note is copied tick by tick
  (period, volume, instrument, sample position: msxsound.Channel's arrays);
- drums: one drum-only copy of each Amiga channel (the SCC version's PSG drum voice takes the
  louder per tick, as msxsound.Effects does with effect 42's two channels; the OPLL's rhythm
  section strikes every hit, several at once when they coincide), and one merged channel for
  the PSG version's Title._drums (per tick the most recent hit, the louder of simultaneous ones).
With TITM tune 1 the routing is the identity: through it the three converters give today's
scc.bin, fm.bin and the PSG title byte for byte (tests/test_msxtune.py).

Brainstorm (PUZL, docs/BRAINSTORM.md): PUZL carries its own copy of the music player at $18000
(PZM: PUZL_25.bin from offset F00h, the same player as MU1's and TITM's; tools/rc2music.py models
it, --verify: 0 differences). PUZL starts tune 1 at every board (3,000 ticks, no loop) and effects
3-6 on Amiga channel 3 through its request byte $B04 (SOUND.md):
- tune 1 in three versions: the SCC's (three SCC voices, the drums on PSG voice C: msxscc), the
  OPLL's (three melodic channels, the rhythm section: msxfm), the PSG's (three voices, the drums
  riding them: msxsound.Title, the title's lambda). Drums: 20 CLUB as BD, 21 PERCUSH2 and 22
  PERCUSH1 as toms, 23 SNAZ as SD;
- effects 3, 4 and 5 through the effect converters at the tune's reference, so their balance
  against the music is the Amiga's (msxsound.Effects: the PSG, levels from the tune's a_ref;
  msxsccfx: the SCC, the tune's SCC scale 1 / ref), FX_ATTEN_DB off (it is MU1's);
- effect 6 designed: PUZL restarts it on every pass of a board's fade-out, so what sounds is the
  restart, a pulse train at the pass rate (Paula plays its byte 0, value 0, for 15.1 ms, then byte
  1, +116, until the next restart: 50 Hz, 24 % duty at 50 passes a second). Converted from its
  data it starts with a silent tick, and restarted every pass it would be silent. The SCC: a
  32-byte pulse, 8 high, at 50.00 Hz; the PSG: a 50.00 Hz square. Their levels from the Amiga's
  (the restarted effect rendered: its AC RMS against the tune's scales), 36 ticks (its own).

Output: build/msx/pzm.bin for tools/mkrom.py (all offsets 24-bit little-endian from its start):
  0-32  eleven streams: the SCC version's voices 0-2 and its PSG drum stream (msxscc's formats),
        the OPLL version's channels 0-2 and its rhythm (msxfm's), the PSG version's voices A-C
        (msxsound's, music.asm MVK_PSG)
  33    the SCC waveform table (W x 32 signed bytes: the tune's, then the effects', numbered from
        0 in the SCC streams; 32-byte aligned, so that none crosses a bank: msx/tune.asm tn_wv)
  36    the OPLL's patch block (14 bytes: the custom instrument 00h-07h, the rhythm's pitches
        16h-18h and 26h-28h)
  39    the effect table: per effect its length in ticks (the $1822C rule: Amiga channel 3 busy),
        its SCC stream's offset and ticks, its PSG stream's offset and ticks (9 bytes; a stream's
        ticks are its records', the trailing silence left out: after them the channel goes back)
  42    W; 43: the tune's ticks (16 bits); 45: the first effect; 46: how many
  47    the data
Every stream is decoded back and checked against what it was made from; every tune stream lasts
the tune. --wav DIR writes previews: the Amiga's tune 1 and the three versions decoded on the
converters' chip models (pzm_amiga.wav, pzm_scc.wav, pzm_psg.wav, pzm_fm.wav). Needs numpy (the
project's venv). About two minutes.

usage: msxtune.py [--out build/msx] [--wav DIR]
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import msxfm as fm  # noqa: E402
import msxscc as sc  # noqa: E402
import msxsccfx as sx  # noqa: E402
import msxsound as ms  # noqa: E402
import rc2music  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PUZL = ROOT / "build" / "extracted" / "files" / "PUZL_25.bin"
PZM_AT = 0xF00                          # PUZL ($17100) from $18000 on: PZM, the player and its data
TITLE_BUDGET = 7680                     # the Makefile's msxsound.py --budget: the PSG title's lambda
TITLE_LAMBDA = 1.9824777683049783       # msxsound.encode's lambda for that budget (sound.inc;
                                        # tests/test_msxtune.py finds it again)
PZM_TUNE = 1
PZM_DRUMS = {20: "bd", 21: "tom", 22: "tom", 23: "sd"}     # CLUB, PERCUSH2, PERCUSH1, SNAZ
PZM_FX = (3, 4, 5)                      # converted
BUZZ = 6                                # designed (the module docstring)
BUZZ_HZ = 50.0                          # the pass rate (the port's: 50 passes a second)
BUZZ_WAVE = [127] * 8 + [-42] * 24      # 8 of 32 high: the Amiga's 24 % duty, no DC
BUZZ_PASSES = 31                        # a fade-out's passes (the level's measure)
HEADER = 47


# ---------------------------------------------------------------------------------------------
# The routing (the module docstring)
# ---------------------------------------------------------------------------------------------

@contextlib.contextmanager
def converter_constants(speech: int, atten: dict | None = None):
    """The converters' title-specific constants for one tune: msxsound.SPEECH_INST (the title's
    speech instrument, left silent; -1: none) and FX_ATTEN_DB (MU1's effects; {} for others),
    put back after."""
    old_sp, old_at = ms.SPEECH_INST, dict(ms.FX_ATTEN_DB)
    ms.SPEECH_INST = speech
    if atten is not None:
        ms.FX_ATTEN_DB.clear()
        ms.FX_ATTEN_DB.update(atten)
    try:
        yield
    finally:
        ms.SPEECH_INST = old_sp
        ms.FX_ATTEN_DB.clear()
        ms.FX_ATTEN_DB.update(old_at)


def amiga_channels(tune: dict, insts: dict, T: int) -> list:
    frames = dict(tune["frames"])
    for c in range(4):
        frames.setdefault(str(c), [[T, 1, 0, None]])
    return [ms.Channel(dict(tune, frames=frames), c, insts, T) for c in range(4)]


FIELDS = ("per", "vol", "ins", "keyon", "pos", "nb", "rate", "amp")


def empty_channel(T: int, insts: dict, cid: int) -> ms.Channel:
    v = object.__new__(ms.Channel)
    v.ch, v.T, v.insts = cid, T, insts
    v.per = np.ones(T, np.int64)
    v.vol = np.zeros(T, np.int64)
    v.ins = np.full(T, -1, np.int64)
    v.keyon = np.zeros(T, bool)
    v.pos = np.zeros(T)
    v.nb = np.zeros(T)
    v.rate = np.zeros(T)
    v.amp = np.zeros(T)
    return v


def copy_ticks(dst: ms.Channel, src: ms.Channel, a: int, b: int) -> None:
    for f in FIELDS:
        getattr(dst, f)[a:b] = getattr(src, f)[a:b]


def tune_length(tune: dict) -> tuple[int, int]:
    """(ticks to encode, loop start tick; 0 when the tune ends or loops from its start)."""
    if tune["loop"]:
        lp = tune["loop"]
        return lp["start_tick"] + lp["length_ticks"], lp["start_tick"]
    return (tune["ends_at_tick"] or tune["ticks"]), 0


class Routing:
    """The notes of a tune routed to 3 melodic voices, drum-only channels and a merged drum
    channel (the module docstring)."""

    def __init__(self, rep: dict, data: bytes, tune_no: int, drums: set[int], speech: set[int],
                 voices: int = 3):
        self.tune = rep["tunes"][tune_no - 1]
        self.T, self.loop_tick = tune_length(self.tune)
        T = self.T
        self.insts = ms.load_insts(rep, data)
        self.amiga = amiga_channels(self.tune, self.insts, T)
        self.drums, self.speech = set(drums), set(speech)
        notes = []
        for c, ch in enumerate(self.amiga):
            ks = list(np.nonzero(ch.keyon)[0]) + [T]
            for s, e in zip(ks, ks[1:]):
                aud = np.nonzero(ch.amp[s:e] > 0)[0]
                if not len(aud):
                    continue
                ea = s + int(aud[-1]) + 1
                i = int(ch.ins[s])
                kind = "drum" if i in self.drums else "speech" if i in self.speech else "mel"
                notes.append({"c": c, "s": int(s), "e": int(e), "ea": ea, "i": i, "kind": kind,
                              "peak": float(ch.amp[s:ea].max())})
        self.notes = notes
        self.mel = [empty_channel(T, self.insts, v) for v in range(voices)]
        self.src = [np.full(T, -1) for _ in range(voices)]
        busy = [None] * voices                       # the note a voice plays
        last = {}
        self.stolen_ticks = 0
        self.stolen_notes = 0
        mel_notes = sorted((n for n in notes if n["kind"] in ("mel", "speech")),
                           key=lambda n: (n["s"], n["c"]))
        for n in mel_notes:
            free = [v for v in range(voices) if busy[v] is None or busy[v]["ea"] <= n["s"]]
            pref = last.get(n["c"])
            if pref is not None and pref in free:
                v = pref
            elif free:
                owners = {vv: c for c, vv in last.items()}
                cand = [vv for vv in free if owners.get(vv) in (None, n["c"])] or free
                v = cand[0]
            else:
                v = min(range(voices), key=lambda vv: float(self.mel[vv].amp[n["s"]]))
                cut = busy[v]["ea"] - n["s"]
                self.stolen_ticks += int(np.sum(self.mel[v].amp[n["s"]:busy[v]["ea"]] > 0))
                self.stolen_notes += 1
                if cut > 0:                             # (the rest of the old note cleared)
                    a, b = n["s"], busy[v]["ea"]
                    blank = empty_channel(b - a, self.insts, v)
                    for f in FIELDS:
                        getattr(self.mel[v], f)[a:b] = getattr(blank, f)
                    self.src[v][a:b] = -1
            copy_ticks(self.mel[v], self.amiga[n["c"]], n["s"], n["ea"])
            self.src[v][n["s"]:n["ea"]] = n["c"]
            busy[v] = n
            last[n["c"]] = v
        self.dchans = []                                # drum-only copies of the Amiga channels
        for c in range(4):
            d = empty_channel(T, self.insts, c)
            any_drum = False
            for n in notes:
                if n["c"] == c and n["kind"] == "drum":
                    copy_ticks(d, self.amiga[c], n["s"], n["ea"])
                    any_drum = True
            if any_drum:
                self.dchans.append(d)
        # the merged drum channel: per tick the most recent hit (the louder of simultaneous ones)
        self.dmerged = empty_channel(T, self.insts, 3)
        hit_at = [np.full(T, -1) for _ in self.dchans]
        for k, d in enumerate(self.dchans):
            h = -1
            for t in range(T):
                if d.keyon[t] and d.amp[t] > 0:
                    h = t
                hit_at[k][t] = h if d.amp[t] > 0 else -1
        self.drum_ticks_lost = 0
        for t in range(T):
            cand = [(hit_at[k][t], float(d.amp[t]), k) for k, d in enumerate(self.dchans) if d.amp[t] > 0]
            if not cand:
                continue
            self.drum_ticks_lost += len(cand) - 1
            _, _, k = max(cand)
            d = self.dchans[k]
            copy_ticks(self.dmerged, d, t, t + 1)
            self.dmerged.keyon[t] = bool(d.keyon[t] and hit_at[k][t] == t)
        self.dmerged.ch = 3

    def summary(self) -> str:
        kinds: dict = {}
        for n in self.notes:
            kinds[n["kind"]] = kinds.get(n["kind"], 0) + 1
        simult = np.zeros(self.T, int)
        for n in self.notes:
            if n["kind"] == "mel":
                simult[n["s"]:n["ea"]] += 1
        return ("%d ticks (loop from %d); notes %s; melodic voices needed at most %d (ticks with "
                "more than 3: %d), stolen %d notes / %d audible ticks; drum channels %d, drum ticks "
                "dropped by the merge %d" % (self.T, self.loop_tick, kinds, int(simult.max()),
                                            int(np.sum(simult > 3)), self.stolen_notes,
                                            self.stolen_ticks, len(self.dchans), self.drum_ticks_lost))


class RoutedTitle(ms.Title):
    """msxsound.Title on a Routing: chans = the three melodic voices + the merged drum channel
    (Title.__init__'s steps on them)."""

    def __init__(self, rt: Routing):                    # (not Title.__init__: no TITM here)
        self.rt = rt
        self.T, self.loop_tick = rt.T, rt.loop_tick
        self.insts = rt.insts
        self.chans = rt.mel[:3] + [rt.dmerged]
        amps = np.concatenate([c.amp[c.amp > 0] for c in self.chans])
        self.a_ref = float(np.percentile(amps, 99.5))
        counts: dict[int, int] = {}
        for c in self.chans[:3]:
            for t in np.nonzero(c.keyon & (c.amp > 0))[0]:
                i = int(c.ins[t])
                counts[i] = counts.get(i, 0) + 1
        self.pitch = {i: ms.sample_pitch(self.insts[i]) for i in counts}
        raw = {i: p[0] for i, p in self.pitch.items() if p[0] > 0}
        self.spc, self.phi, self.tune_why = ms.snap_tuning(self.chans, raw, counts)
        self.octave = {}
        for i, s in self.spc.items():
            fs = [ms.PAULA_HZ / (max(c.per[t], ms.DMA_PERIOD) * s) for c in self.chans[:3]
                  for t in np.nonzero((c.ins == i) & (c.amp > 0) & (c.per > 1))[0]]
            k = 0
            while fs and np.median(fs) * 2 ** k < ms.LOW_HZ:
                k += 1
            self.octave[i] = k
        self.counts = counts
        self.targets = [self._melodic(c) for c in range(3)]
        self.drum_log = self._drums() if rt.dchans else []


class RoutedDrums(ms.Effects):
    """The SCC version's PSG drum voice: the drum-only channels as one PSG voice, made as
    msxsound makes a sound effect's voice (msxscc.TitleDrums on several channels)."""

    def __init__(self, insts: dict, dchans: list, a_ref: float):     # (not Effects.__init__)
        self.insts = insts
        self.chans = {3: dchans}
        self.a_ref = a_ref
        self.wave_spc = {i: ms.sample_pitch(x)[0] for i, x in self.insts.items()
                         if len(x.first) < 64 and x.looped}
        self.info = {}
        self.target = self._target(3)


# ---- the SCC version (msxscc's steps and scc.bin's layout) ----

def scc_version(gt: RoutedTitle) -> dict:
    """msxscc.main's conversion on a routed tune: the waveforms, the three SCC voices against
    their REF_PCT reference, the PSG drum voice in the same scale; the blob in scc.bin's layout
    (five 24-bit offsets: voices 0-2, the drums, the waveform table)."""
    waves = sc.make_waves(gt)
    table = np.array([wv.data for wv in sorted(waves.values(), key=lambda w: w.number)])
    voices = [sc.SccVoice(gt, c, waves) for c in range(3)]
    ratios = np.concatenate([v.ratio[v.inst >= 0] for v in voices])
    ref = float(np.percentile(ratios, sc.REF_PCT))
    for v in voices:
        v.quantise(ref)
    wants = [v.intended() for v in voices]
    srecs = [sc.scc_records(w) for w in wants]
    parts = [sc.scc_bytes(r) for r in srecs]
    drecs, dtarget, dvol = None, None, None
    if gt.rt.dchans:
        drums = RoutedDrums(gt.insts, gt.rt.dchans, 0.5 * sc.PSG_OVER_SCC * ref)
        dtarget = drums.target
        dvol = ms.choose_volumes(dtarget, sc.DRUM_LAMBDA, False)
        drecs = sc.both_periods_first(ms.records(dtarget, dvol))
        parts.append(ms.stream_bytes(drecs))
    else:
        parts.append(bytes([255, 0, 0]))               # (no drums: silent)
    parts.append(table.astype(np.int8).tobytes() if len(waves) else b"")
    offs, pos = [], 15
    for p in parts:
        offs.append(pos)
        pos += len(p)
    blob = b"".join(sc.offset24(o) for o in offs) + b"".join(parts)
    return {"blob": blob, "waves": waves, "table": table, "ref": ref, "wants": wants,
            "srecs": srecs, "drecs": drecs, "dtarget": dtarget, "dvol": dvol,
            "sizes": [len(p) for p in parts]}


# ---- the OPLL version (msxfm's FmTitle on the routed channels) ----

DEFAULT_HZ = {"bd": 100.0, "sd": 196.0, "tom": 209.0}


class RoutedFm(fm.FmTitle):
    """msxfm.FmTitle on a routed tune; the rhythm section strikes every drum hit of every Amiga
    channel (drum_map: instrument -> bd, sd or tom)."""

    def __init__(self, gt: RoutedTitle, drum_map: dict[int, str], log=print):   # (not FmTitle's)
        self.log = log
        ti = self.ti = gt
        self.T = ti.T
        self.chans = ti.chans
        self.insts = ti.insts
        self.a_ref = ti.a_ref
        top = max(20 * math.log10(float(c.amp.max()) / ti.a_ref) for c in ti.chans[:3] if c.amp.max() > 0)
        self.ref = fm.SINE_DB - max(0.0, top)
        self.floor = self.ref + ms.FLOOR_DB
        self.mel = sorted(i for i in ti.pitch if ti.pitch[i][0] > 0 and i != ms.SPEECH_INST)
        self._amiga()
        tot = sum(float(self._w(c, self.aud[c]).sum()) for c in range(3))
        self.importance = {i: sum(float(self._w(c, self.aud[c] & (self.chans[c].ins == i)).sum())
                                  for c in range(3)) / tot for i in self.mel}
        self.reps = {i: self._reps(i) for i in self.mel}
        self._lcache: dict = {}
        self.drum_map = drum_map

    def drums(self, lam: float):
        """FmTitle.drums on every drum channel: the pitches of BD, SD and TOM from their first
        hit (msxfm's way; DEFAULT_HZ when a sound is not used), each hit's volume by its energy
        over its first DRUM_WIN ticks and BD's and SD's early key-off by the error (against its
        own channel's levels); hits on the same tick are struck together (one record), the
        volumes as they stand after them."""
        T = self.T
        hits = []
        for d in self.ti.rt.dchans:
            on = [int(t) for t in np.nonzero(d.keyon & (d.amp > 0))[0]]
            for j, t in enumerate(on):
                nxt = on[j + 1] if j + 1 < len(on) else T
                hits.append((t, nxt, self.drum_map[int(d.ins[t])], d))
        hits.sort(key=lambda h: h[0])
        hz = dict(DEFAULT_HZ)
        for name in ("bd", "sd", "tom"):
            h = next((h for h in hits if h[2] == name), None)
            if h is None:
                continue
            t0, _, _, d = h
            n = {"bd": 2, "sd": 6, "tom": 2}[name]
            seg = d.render(t0, min(T, t0 + n))
            N = 1 << 15
            X = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), N)) ** 2
            f = np.fft.rfftfreq(N, 1 / fm.FS)
            if name == "bd":
                m = (f >= 40) & (f < 300)
                hz[name] = float(2 ** ((X[m] * np.log2(f[m])).sum() / X[m].sum()))
            else:
                m = (f >= 100) & (f < 500)
                hz[name] = float(f[m][np.argmax(X[m])])
        self.drum_hz = hz
        fbs = [fm.fnum_block(hz["bd"]), fm.fnum_block(hz["sd"] / 2), fm.fnum_block(hz["tom"] / fm.MULT[5])]
        tgts = {}
        for d in self.ti.rt.dchans:
            tg = np.where(d.amp > 0, 20 * np.log10(np.maximum(d.amp, 1e-12) / self.a_ref) + self.ref, -np.inf)
            tgts[id(d)] = np.where(tg > self.floor, tg, -np.inf)
        best = None
        for sus in ((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)):
            pitch = fm.pitch_regs(fbs, sus)
            r = self._multi_hits(hits, tgts, fm.pitch_regs_hz(pitch), lam)
            if best is None or r[0] < best[0]:
                best = (r[0], pitch, r[1], r[2])
        _, pitch, events, log = best
        return pitch, events, log

    def _multi_hits(self, hits, tgts, chans, lam):
        vols = {"bd": 0, "sd": 0, "tom": 0, "hh": 15, "tcy": 15}
        keys_at: dict[int, int] = {}
        regs_at: dict[int, tuple] = {}
        offs_at: set[int] = set()
        log = []
        total = 0.0
        for t, nxt, name, d in hits:
            n = max(1, nxt - t)
            offs: list = [None]
            if name in fm.EARLY_OFF:
                offs += [k for k in range(1, fm.EARLY_OFF_MAX + 1) if k < n]
            tg = tgts[id(d)][t:t + n]
            aud = np.isfinite(tg)
            k = min(n, fm.DRUM_WIN)
            e_a = float(np.sum(10 ** (tg[:k][aud[:k]] / 10)))
            w = 10 ** ((np.where(aud, tg, self.floor) - self.ref) / 10)
            bst = None
            for off in offs:
                key = (name, n, off, chans[fm.RHYTHM_CH[name]])
                L = self._lcache.get(key)
                if L is None:
                    L = self._lcache[key] = fm.hit_levels(name, chans, n, off)
                e_o = (10 ** (L[:k] / 10)).sum(axis=0)
                v = int(np.argmin(np.abs(10 * np.log10(np.maximum(e_o, 1e-30) / max(e_a, 1e-30)))))
                Lc = np.maximum(L[:, v], self.floor)
                e_aud = w * np.minimum(((Lc - np.where(aud, tg, 0.0)) / 3) ** 2, fm.DRUM_CAP ** 2)
                e_sil = 10 ** ((Lc - self.ref) / 10) * np.minimum(((Lc - self.floor) / 3) ** 2, fm.DRUM_CAP ** 2)
                err = np.where(aud, e_aud, e_sil)
                cost = float(err.sum()) + lam * (2 if off is not None else 0)
                if bst is None or cost < bst[0]:
                    bst = (cost, v, off)
            cost, v, off = bst
            total += cost + lam * (3 if v != vols[name] else 0)
            vols[name] = v
            keys_at[t] = keys_at.get(t, 0) | dict(fm.RHYTHM)[name]
            regs_at[t] = (vols["bd"], (vols["hh"] << 4) | vols["sd"], (vols["tom"] << 4) | vols["tcy"])
            if off is not None:
                offs_at.add(t + off)
            log.append({"tick": t, "drum": name, "vol": v, "off": off})
        events = [(t, keys_at[t], regs_at[t]) for t in keys_at]
        events += [(t, 0, None) for t in offs_at if t not in keys_at and t < self.T]
        return total, sorted(events), log


def fm_version(gt: RoutedTitle, drum_map: dict[int, str], quiet: bool = True) -> tuple[RoutedFm, dict]:
    """msxfm.main's conversion on a routed tune: the instruments and the custom patch, then the
    smallest lambda whose blob fits msxfm's budget (fm.bin's layout, msxfm.encode); checked as
    msxfm checks it (decoded twice round against the intent)."""
    ft = RoutedFm(gt, drum_map, log=(lambda *a: None) if quiet else print)
    ft.choose(fm.CUSTOM_MIN)
    enc = fm.encode_budget(ft, fm.BUDGET)
    bad = fm.check(enc, ft.T)
    if bad:
        raise SystemExit("error: the OPLL streams do not read back: " + "; ".join(bad))
    return ft, enc


# ---- the PSG version (msxsound's title encoder) ----

def psg_version(gt: RoutedTitle, lam: float) -> dict:
    """msxsound.encode_title at lambda: the three voices' records and stream bytes, checked
    against the encoder's intent (msxsound.play_streams, check_decode)."""
    recs, vols = ms.encode_title(gt, lam)
    streams = [ms.stream_bytes(r) for r in recs]
    blob, offs = b"", []
    for s in streams:
        offs.append(len(blob))
        blob += s
    T = gt.T
    states = ms.play_streams(blob, [(v, offs[v], None) for v in range(3)], T)
    bad = ms.check_decode(states, {v: ms.intended(gt.targets[v], vols[v], T) for v in range(3)})
    if bad:
        raise SystemExit("error: the PSG streams differ from the encoder on %d voice ticks" % bad)
    return {"recs": recs, "vols": vols, "streams": streams, "states": states}


# ---- TITM tune 1: the regression ----

def load_titm() -> tuple[dict, bytes]:
    return ms.load_music("TITM", "TITM_04.bin")


def titm_title() -> RoutedTitle:
    """TITM tune 1 through the routing: its drums are channel 3's instruments (BDRM, SNARE,
    TOM1), its speech instrument 24."""
    rep, data = load_titm()
    drums = {k[2] for k in rep["tunes"][0]["key_ons"] if k[1] == 3}
    with converter_constants(24):
        return RoutedTitle(Routing(rep, data, 1, drums=drums, speech={24}))


def titm_drum_map(gt: RoutedTitle) -> dict[int, str]:
    """msxfm's DRUMS by sample name, per instrument."""
    return {i: fm.DRUMS[gt.insts[i].name] for i in gt.rt.drums}


# ---------------------------------------------------------------------------------------------
# Brainstorm's PZM
# ---------------------------------------------------------------------------------------------

def load_pzm(cache: Path) -> tuple[dict, bytes]:
    """PZM (PUZL_25.bin from F00h: PUZL is loaded at $17100, the player at $18000) and
    tools/rc2music.py's model of it: cache/PZM_00.bin (rc2music.py --verify takes it) and
    cache/PZM.json, made when missing or stale."""
    data = PUZL.read_bytes()[PZM_AT:]
    cache.mkdir(parents=True, exist_ok=True)
    cut, js = cache / "PZM_00.bin", cache / "PZM.json"
    if not cut.exists() or cut.read_bytes() != data:
        cut.write_bytes(data)
        if js.exists():
            js.unlink()
    if js.exists():
        rep = json.loads(js.read_text())
    else:
        rep = rc2music.build_report(cut, None, 400000)
        js.write_text(json.dumps(rep, separators=(",", ":")) + "\n")
    return rep, data


def fx_effects(rep: dict, data: bytes, nums: tuple, a_ref: float) -> ms.Effects:
    """msxsound.Effects of the tunes `nums`, their levels from the music's reference a_ref
    (0 dB = PSG level 15 for the tune's loudest ticks), not their own set's loudest."""
    fx = ms.Effects(dict(rep, tunes=[t for t in rep["tunes"] if t["tune"] in nums]), data)
    fx.a_ref = a_ref
    fx.targets = {n: fx._target(n) for n in fx.chans}
    return fx


def trim_silence(recs: list) -> list:
    """A record list without its trailing silent records (ctl 0, or volume 0)."""
    recs = list(recs)
    while recs and (recs[-1][1] & 15) == 0:
        recs.pop()
    return recs


def scc_effects(fx: ms.Effects, gain: float) -> dict:
    """msxsccfx.convert's SCC part at a given scale (the tune's: 1 / its SCC reference) instead
    of its choose_gain: per effect its SCC states and records (the trailing silence left out),
    their waveforms (msxsccfx.make_waves); no noise part (checked: PZM's effects 3-5 are tones)."""
    plans = {n: sx.Plan(fx, n) for n in sorted(fx.chans)}
    bad = [n for n, pl in plans.items() if not pl.replica_ok]
    if bad:
        raise SystemExit("error: msxsccfx's measure differs from msxsound's Effects on %s" % bad)
    waves = sx.Waves()
    sx.make_waves(fx, plans, waves)
    out = {}
    for n, pl in plans.items():
        if np.any(pl.amp_n > 0):
            raise SystemExit("error: effect %d has a noise part (the effect voice has no PSG part)" % n)
        sst = sx.scc_states(pl, waves, gain)
        recs = trim_silence(sc.scc_records(sst))
        out[n] = {"states": sst, "recs": recs, "T": pl.T}
    return {"fx": out, "table": waves.table(), "waves": waves}


def psg_effects(fx: ms.Effects) -> dict:
    """msxsound's effect encoding (choose_volumes at FX_LAMBDA, records), the trailing silence
    left out."""
    out = {}
    for n, tg in fx.targets.items():
        vol = ms.choose_volumes(tg, ms.FX_LAMBDA, False)
        out[n] = {"recs": trim_silence(ms.records(tg, vol)), "intent": ms.intended(tg, vol, tg.T),
                  "T": tg.T}
    return out


def buzz_amp(insts: dict) -> float:
    """Effect 6 as PUZL plays it in a fade-out (a key-on every pass: AUDxPER 54,191, volume 64,
    instrument 0, the model's tune 6 at its first tick), rendered: the median AC RMS of a pass."""
    k = BUZZ_PASSES
    tune = {"frames": {"3": [[k, 54191, 64, 0], [1, 1, 0, None]]},
            "key_ons": [[t, 3, 0, 0, -33, 54191] for t in range(k)]}
    y = ms.Channel(tune, 3, insts, k).render().reshape(k, ms.SPT)
    ac = np.sqrt(((y - y.mean(axis=1, keepdims=True)) ** 2).mean(axis=1))
    return float(np.median(ac))


def buzz(rep: dict, insts: dict, gt: RoutedTitle, scc_ref: float) -> dict:
    """Effect 6 designed (the module docstring): the SCC's record (the pulse at BUZZ_HZ, its
    volume from the Amiga's level on the SCC version's scale) and the PSG's (a square at BUZZ_HZ,
    the AY level nearest the Amiga's on the PSG version's), each its length."""
    tune = next(t for t in rep["tunes"] if t["tune"] == BUZZ)
    T = tune["ends_at_tick"] or tune["ticks"]
    amp = buzz_amp(insts)
    w = np.array(BUZZ_WAVE, float)
    w_rms = math.sqrt(float(np.mean((w / 128) ** 2)))
    vol = sc.nearest_level(15 * amp / (w_rms * scc_ref))
    n = int(round(sc.SCC_HZ / (sc.WAVE_LEN * BUZZ_HZ))) - 1
    lv = 20 * math.log10(amp / gt.a_ref)
    level = int(np.argmin(np.abs(ms.AY_DB - lv)))
    per = ms.ay_period(BUZZ_HZ)
    return {"T": T, "amp_db": lv, "scc": (T, vol, n), "psg": (T, level, per),
            "scc_hz": sc.SCC_HZ / (sc.WAVE_LEN * (n + 1)), "psg_hz": ms.AY_STEP / per}


def u24(v: int) -> bytes:
    return bytes([v & 0xFF, (v >> 8) & 0xFF, v >> 16])


def scc_stream_waves(b: bytes, delta: int) -> bytes:
    """An SCC stream (msxscc's format, to its end marker) with its waveform numbers moved by
    delta."""
    out, p = bytearray(b), 0
    while out[p]:
        ctl = out[p + 1]
        p += 2 + (2 if ctl & 0x10 else 0)
        if ctl & 0x20:
            out[p] += delta
            p += 1
    return bytes(out)


def assemble(scc: dict, fmv: dict, psg: dict, fx_scc: dict, fx_psg: dict, fx_len: dict,
             table: np.ndarray, T: int) -> bytes:
    """pzm.bin (the module docstring)."""
    so = [scc["blob"][3 * k] | scc["blob"][3 * k + 1] << 8 | scc["blob"][3 * k + 2] << 16 for k in range(5)]
    scc_streams = [scc["blob"][so[k]:so[k + 1]] for k in range(4)]
    fo = fmv["offs"]                                    # (mel 0-2, rhythm, patch)
    fb = fmv["blob"]
    fm_streams = [fb[fo[0]:fo[1]], fb[fo[1]:fo[2]], fb[fo[2]:fo[3]], fb[fo[3]:]]
    patch = fb[fo[4]:fo[4] + 14]
    streams = scc_streams + fm_streams + psg["streams"]
    nums = sorted(fx_len)
    body = bytearray()
    offs = []
    for s in streams:
        offs.append(HEADER + len(body))
        body += s
    body += bytes(-(HEADER + len(body)) % 32)          # (32-byte aligned: no waveform across a bank)
    w_off = HEADER + len(body)
    body += table.astype(np.int8).tobytes()
    p_off = HEADER + len(body)
    body += patch
    fx_streams = bytearray()
    entries = []
    e_off = HEADER + len(body)
    base = e_off + 9 * len(nums)
    for n in nums:
        s_b, p_b = fx_scc[n]["bytes"], fx_psg[n]["bytes"]
        s_o = base + len(fx_streams)
        fx_streams += s_b
        p_o = base + len(fx_streams)
        fx_streams += p_b
        entries.append(bytes([fx_len[n]]) + u24(s_o) + bytes([fx_scc[n]["ticks"]]) + u24(p_o)
                       + bytes([fx_psg[n]["ticks"]]))
    body += b"".join(entries) + fx_streams
    head = (b"".join(u24(o) for o in offs) + u24(w_off) + u24(p_off) + u24(e_off)
            + bytes([len(table), T & 0xFF, T >> 8, nums[0], len(nums)]))
    if len(head) != HEADER or nums != list(range(nums[0], nums[0] + len(nums))):
        raise SystemExit("error: pzm.bin's header")
    return head + bytes(body)


def parse(blob: bytes) -> dict:
    """pzm.bin read back (tools/mkrom.py reads it the same way)."""
    def r24(i: int) -> int:
        return blob[i] | blob[i + 1] << 8 | blob[i + 2] << 16
    out = {"streams": [r24(3 * k) for k in range(11)], "waves": r24(33), "patch": r24(36),
           "fx": r24(39), "W": blob[42], "T": blob[43] | blob[44] << 8, "fx0": blob[45],
           "fxn": blob[46], "effects": {}}
    for k in range(out["fxn"]):
        e = out["fx"] + 9 * k
        out["effects"][out["fx0"] + k] = {"len": blob[e], "scc": r24(e + 1), "scc_ticks": blob[e + 4],
                                          "psg": r24(e + 5), "psg_ticks": blob[e + 8]}
    return out


KINDS = ("scc",) * 3 + ("psg",) + ("fm",) * 3 + ("rhy",) + ("psg",) * 3


def stream_ticks(blob: bytes, start: int, kind: str) -> int:
    """The ticks of a stream up to its end marker (tools/mkrom.py stream_ticks' formats)."""
    word, byte = (0x40, 0x80) if kind == "psg" else (0x10, 0x20)
    p, t = start, 0
    while blob[p]:
        t, ctl, p = t + blob[p], blob[p + 1], p + 2
        if kind == "rhy":
            p += 3 if ctl & 0x20 else 0
        else:
            p += (2 if ctl & word else 0) + (1 if ctl & byte else 0)
    return t


def check_blob(blob: bytes, scc: dict, fmv: dict, psg: dict, fx_scc: dict, fx_psg: dict) -> list[str]:
    """pzm.bin decoded with the converters' independent decoders against what it was made from:
    the SCC voices (msxscc.decode_scc against the intent), the PSG drum stream and the PSG
    version (msxsound.play_streams), the OPLL streams (msxfm.decode_melodic / decode_rhythm
    against msxfm's blob), the effects (msxsccfx.decode_scc and decode_psg against their
    records), every tune stream's length."""
    bad = []
    hd = parse(blob)
    T = hd["T"]
    for k, (o, kind) in enumerate(zip(hd["streams"], KINDS)):
        n = stream_ticks(blob, o, kind)
        if n != T:
            bad.append("stream %d (%s) lasts %d ticks, not %d" % (k, kind, n, T))
    for v in range(3):
        st = sc.decode_scc(blob, hd["streams"][v], T)
        if sc.audible(st) != scc["wants"][v]:
            bad.append("SCC voice %d does not read back" % v)
    if scc["dtarget"] is not None:
        st = ms.play_streams(blob, [(sc.DRUM_VOICE, hd["streams"][3], None)], T)
        if ms.check_decode(st, {sc.DRUM_VOICE: ms.intended(scc["dtarget"], scc["dvol"], T)}):
            bad.append("the SCC version's PSG drums do not read back")
    fo = fmv["offs"]
    for c in range(3):
        a = fm.decode_melodic(blob, hd["streams"][4 + c], T)
        b = fm.decode_melodic(fmv["blob"], fo[c], T)
        if any(not np.array_equal(a[f], b[f]) for f in a):
            bad.append("OPLL channel %d does not read back" % c)
    a = fm.decode_rhythm(blob, hd["streams"][7], T)
    b = fm.decode_rhythm(fmv["blob"], fo[3], T)
    if any(not np.array_equal(a[f], b[f]) for f in a):
        bad.append("the OPLL rhythm does not read back")
    if blob[hd["patch"]:hd["patch"] + 14] != fmv["blob"][fo[4]:fo[4] + 14]:
        bad.append("the OPLL patch block")
    st = ms.play_streams(blob, [(v, hd["streams"][8 + v], None) for v in range(3)], T)
    if st != psg["states"]:
        bad.append("the PSG version does not read back")
    for n, e in hd["effects"].items():
        sst, length, _ = sx.decode_scc(blob, e["scc"], hd["W"], e["scc_ticks"])  # (raises past the table)
        if length != e["scc_ticks"] or [s if s[0] else (0,) for s in sst] != fx_scc[n]["want"]:
            bad.append("effect %d's SCC stream does not read back" % n)
        pst, length = sx.decode_psg(blob, e["psg"], e["psg_ticks"])
        if length != e["psg_ticks"] or pst != fx_psg[n]["want"]:
            bad.append("effect %d's PSG stream does not read back" % n)
        if max(e["scc_ticks"], e["psg_ticks"]) > e["len"]:
            bad.append("effect %d sounds past its length" % n)
    return bad


def per_tick_scc(recs: list) -> list[tuple]:
    """msxscc records -> per tick (volume, N, waveform) or (0,), the fields kept."""
    out, n, w = [], None, None
    for d, ctl, per, wav in recs:
        n = per if per is not None else n
        w = wav if wav is not None else w
        out += [(ctl & 15, n, w) if ctl & 15 else (0,)] * d
    return out


def per_tick_psg(recs: list) -> list[tuple]:
    """msxsound records -> per tick (volume, tone, noise, period, noise period) as
    msxsccfx.decode_psg reads them."""
    out, per, npd = [], None, None
    for d, ctl, w, b in recs:
        per = w if w is not None else per
        npd = b if b is not None else npd
        out += [(ctl & 15, bool(ctl & 0x10), bool(ctl & 0x20), per, npd)] * d
    return out


def convert(out: Path, cache: Path, log=print) -> dict:
    """The whole PZM conversion; writes out/pzm.bin. Returns the parts (previews, tests)."""
    rep, data = load_pzm(cache)
    with converter_constants(-1, {}):
        rt = Routing(rep, data, PZM_TUNE, drums=set(PZM_DRUMS), speech=set())
        log("PZM tune %d: %s" % (PZM_TUNE, rt.summary()))
        if rt.loop_tick or rt.stolen_notes:
            raise SystemExit("error: PZM's tune loops or steals notes: the routing's assumptions")
        gt = RoutedTitle(rt)
        psg = psg_version(gt, TITLE_LAMBDA)
        scc = scc_version(gt)
        ft, fmv = fm_version(gt, PZM_DRUMS)
        fx = fx_effects(rep, data, PZM_FX, gt.a_ref)
        fsc = scc_effects(fx, 1 / scc["ref"])
        fps = psg_effects(fx)
        bz = buzz(rep, gt.insts, gt, scc["ref"])
    T = gt.T
    # the SCC table: the tune's waveforms, then the effects' (identical ones shared), the buzz's
    table = [bytes(x.astype(np.int8).tobytes()) for x in scc["table"]]
    def wave_no(b: bytes) -> int:
        if b not in table:
            table.append(b)
        return table.index(b)
    fx_scc, fx_psg, fx_len = {}, {}, {}
    for n in PZM_FX:
        f = fsc["fx"][n]
        remap = {}
        for i, row in enumerate(fsc["table"]):
            remap[i] = wave_no(bytes(row.astype(np.int8).tobytes()))
        recs = [(d, c, p, None if w is None else remap[w]) for d, c, p, w in f["recs"]]
        fx_scc[n] = {"bytes": sc.scc_bytes(recs), "ticks": sum(r[0] for r in recs),
                     "want": per_tick_scc(recs)}
        p = fps[n]["recs"]
        fx_psg[n] = {"bytes": ms.stream_bytes(p), "ticks": sum(r[0] for r in p), "want": per_tick_psg(p)}
        fx_len[n] = fps[n]["T"]
        if f["T"] != fps[n]["T"]:
            raise SystemExit("error: effect %d's lengths differ between the two converters" % n)
    T6, vol, n6 = bz["scc"]
    srec = [(T6, vol | 0x30, n6, wave_no(bytes(np.array(BUZZ_WAVE, np.int8).tobytes())))]
    fx_scc[BUZZ] = {"bytes": sc.scc_bytes(srec), "ticks": T6, "want": per_tick_scc(srec)}
    _, level, per = bz["psg"]
    prec = [(T6, level | 0x50, per, None)]
    fx_psg[BUZZ] = {"bytes": ms.stream_bytes(prec), "ticks": T6, "want": per_tick_psg(prec)}
    fx_len[BUZZ] = bz["T"]
    tab = np.frombuffer(b"".join(table), np.int8).reshape(-1, 32)
    blob = assemble(scc, fmv, psg, fx_scc, fx_psg, fx_len, tab, T)
    bad = check_blob(blob, scc, fmv, psg, fx_scc, fx_psg)
    if b"OPLL" in blob:
        bad.append("\"OPLL\" in the blob (tools/mkrom.py refuses it)")
    if bad:
        raise SystemExit("error: " + "; ".join(bad))
    out.mkdir(parents=True, exist_ok=True)
    (out / "pzm.bin").write_bytes(blob)
    hd = parse(blob)
    fb = fmv["blob"]
    log("PSG (lambda %.4f): voices %s = %d bytes" % (
        TITLE_LAMBDA, "+".join(str(len(s)) for s in psg["streams"]), sum(len(s) for s in psg["streams"])))
    log("SCC: voices %s, drums %d, the tune's %d waveforms (%s): %d bytes" % (
        "+".join(map(str, scc["sizes"][:3])), scc["sizes"][3], len(scc["waves"]),
        ", ".join(w.name for w in sorted(scc["waves"].values(), key=lambda w: w.number)), len(scc["blob"])))
    log("OPLL: melodic %s, rhythm %d (%d hits), patch 14: %d bytes; %s; custom patch for %s" % (
        "+".join(str(len(x)) for x in fmv["mel"]), len(fmv["rhy"]), len(fmv["drum_log"]), len(fb),
        ", ".join("%s -> %s" % (ft.insts[i].name, fm.PRESET_NAMES[k]) for i, k in sorted(ft.mapping.items())),
        ft.insts[ft.custom_for].name))
    log("effects: %s" % "; ".join(
        "%d: %d ticks, SCC %d B (%d ticks), PSG %d B (%d ticks)" % (
            n, fx_len[n], len(fx_scc[n]["bytes"]), fx_scc[n]["ticks"], len(fx_psg[n]["bytes"]),
            fx_psg[n]["ticks"]) for n in sorted(fx_len)))
    log("effect 6 (designed): the Amiga's restarts at %.1f dB of the tune's reference; SCC volume %d, "
        "N %d (%.2f Hz); PSG level %d (%.1f dB), period %d (%.2f Hz)" % (
            bz["amp_db"], vol, n6, bz["scc_hz"], level, ms.AY_DB[level], per, bz["psg_hz"]))
    log("pzm.bin: %d bytes, %d SCC waveforms, every tune stream %d ticks, decoded back: identical" % (
        len(blob), hd["W"], T))
    return {"rep": rep, "data": data, "rt": rt, "gt": gt, "psg": psg, "scc": scc, "ft": ft, "fmv": fmv,
            "fx": fx, "fsc": fsc, "fps": fps, "buzz": bz, "blob": blob, "table": tab}


def previews(res: dict, wav: Path, seconds: float = 60.0) -> None:
    """The Amiga's tune 1 (the model rendered) and the three versions decoded from pzm.bin on the
    converters' chip models (msxscc's SCC, msxsound's PSG, msxfm's OPLL), each normalised as
    msxsound.write_wav does, the speech-free mix."""
    gt, blob = res["gt"], res["blob"]
    hd = parse(blob)
    T = min(hd["T"], int(seconds * ms.TICK_HZ))
    amiga = sum(c.render(0, T) for c in res["rt"].amiga)
    ms.write_wav(wav / "pzm_amiga.wav", amiga)
    table = np.frombuffer(blob[hd["waves"]:hd["waves"] + 32 * hd["W"]], np.int8).reshape(-1, 32)
    scc = sum(sc.render_scc(sc.decode_scc(blob, hd["streams"][v], T), table, T) for v in range(3))
    dst = ms.play_streams(blob, [(sc.DRUM_VOICE, hd["streams"][3], None)], T)
    scc = scc + ms.dc_block(ms.Psg().render(dst)[sc.DRUM_VOICE]) * sc.PSG_OVER_SCC
    ms.write_wav(wav / "pzm_scc.wav", scc)
    pst = ms.play_streams(blob, [(v, hd["streams"][8 + v], None) for v in range(3)], T)
    ms.write_wav(wav / "pzm_psg.wav", ms.dc_block(ms.Psg().render(pst).sum(axis=0)))
    patch = blob[hd["patch"]:hd["patch"] + 14]
    patches = [fm.Patch(patch[:8])] + fm.PRESETS[1:]
    mel = sum(fm.Melodic(fm.decode_melodic(blob, hd["streams"][4 + c], T), patches).render(T) for c in range(3))
    rhy = fm.Rhythm(fm.decode_rhythm(blob, hd["streams"][7], T), patch[8:]).render(T)
    ms.write_wav(wav / "pzm_fm.wav", ms.dc_block(mel + rhy))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT / "build" / "msx", help="directory of pzm.bin")
    ap.add_argument("--cache", type=Path, default=ROOT / "build" / "music",
                    help="directory of PZM_00.bin and PZM.json (rc2music.py's model)")
    ap.add_argument("--wav", type=Path, help="directory of the previews")
    args = ap.parse_args()
    res = convert(args.out, args.cache)
    print("wrote", args.out / "pzm.bin")
    if args.wav:
        previews(res, args.wav)
        print("wrote the previews in", args.wav)
    return 0


if __name__ == "__main__":
    sys.exit(main())
