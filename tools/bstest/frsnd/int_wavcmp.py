"""Scratch: an openMSX recording of Brainstorm's sound (`record start -audioonly`, int/hz_int.tcl
hzi_rec, EMU_PLAN.md stage 6) against the previews, by pitch and by level, with tools/msxsound.py's
own measures (the 2026-10-25 lesson: judge synth sounds by a pitch track, not band levels).

usage: int_wavcmp.py WORKTREE tune REC.wav PREVIEW.wav [PREVIEW.wav ...] TEMPO
       int_wavcmp.py WORKTREE marks REC.wav REC_pz.txt [--buzz BUZZ.wav ...] TEMPO
       int_wavcmp.py WORKTREE selfcheck PREVIEW.wav OTHER.wav
TEMPO (required since the audit's finding 1, 2026-10-27): how the recording's tune ticks.
  --vdp 60 | --vdp 50   the machine's VDP frequency. The MSX ticks the tune on its VBLANKs
                        (sndplay.asm sq_frame; at 60 Hz every sixth one skipped): 5/6 x 21477270 /
                        (1368 x 262) = 49.9356 Hz on a 60 Hz VDP, 21477270 / (1368 x 313) = 50.1590
                        Hz on a 50 Hz one (openMSX: 49.93560-49.93563 Hz and 50.15897 Hz,
                        audit_fix/tickrate.tcl);
  --tick-hz HZ          a rate (50: the previews' own, no correction: the method before the audit);
  --ticks TICKS.txt     the tick times of the very run (audit_fix/tickrate.tcl hzt_rec: the
                        emulated time of each tn_tick from the recording's start, its k-th T line
                        the register log's k-th): exact, the 60 Hz ticks' 16.7 / 33.4 ms steps and
                        the held ticks at a board's start included.
The previews tick at 50.000 Hz, so over the tune's 3,000 ticks a 60 Hz machine's recording falls
77.4 ms behind them and a 50 Hz machine's runs 190 ms ahead; before the audit this tool aligned on
the first 20 s only and compared the rest on the previews' grid. Every per-tick measure now reads the
recording at its own ticks: tick k's windows (the level's 882 samples, YIN's 2048 from the tick's
start, the chroma's 4096 centred on the tick) start at the recording's tick k, on its own samples
(nothing resampled: no pitch moves), where the previews' start at k x 882.

The recording is read at any rate and channel count (16-bit PCM: mixed to mono, resampled to
44.1 kHz). hzi_rec starts it at the first tune start (tune.asm tns_go, board 0's set-up); the
tune's tick 0 comes two VBLANKs later (tn_hold: the first tick after the stage's next pass).

tune: per preview (sound/wav/pzm_scc.wav, pzm_fm.wav, pzm_psg.wav: pzm.bin decoded on the converters'
chip models; pzm_amiga.wav: the original rendered; all 60 s from the tune's tick 0):
  - lag: the recording's tick 0 (s from its start), the per-millisecond log envelopes matched
    within +-1 s over the preview's first 20 s, the recording's read along TEMPO;
  - level: the median per-tick dB difference (recording - preview) where both sound (within 30 dB
    of their peaks): an arbitrary offset (the previews are normalised), only its spread matters;
  - envelope: msxsound.env_compare's measures (Pearson r of the tick dB, the mean |difference|
    after the medians are aligned, the coverage);
  - chroma: msxsound.chroma_similarity's (12-bin chroma per tick, mean cosine);
  - pitch: YIN on both (2048 samples from each tick's start, aperiodicity < 0.2, within 30 dB of
    the peak): the share of the ticks both are periodic within 50 cents modulo octaves (the same
    note), within 50 cents exactly, and the median error in cents modulo octaves;
  then the tune's end (H6), the lag of the first preview: the loudest 20 ms from the tune's tick
  3,005 to the title's music (from the tune's tick 3,200 on, the first block of 100 ticks of which
  90 sound within 60 dB of the tune's peak, from its first such tick: the time out and the silent
  result screen come before it) must be 50 dB or more under the tune's peak (its ticks 0-2,999).
marks (a driven recording, hzi_rec with a drive, and its register log REC_pz.txt from
sound/sess_pzregs.tcl): every effect start (a T line whose tn_snd rose: tn_last is the effect; effect
6's restarts merged), its time, the recording's level over the effect against the music's just
before it (the power mean of the 25 ticks before, outside effects), and for effect 6 (the buzz: a
restart a pass) the median YIN pitch against BUZZ.wav's. A T line's time: its tick's with --ticks;
with a rate, line i at i / rate s (approximate: a board's held ticks log no T line).
selfcheck: the per-tick-start measures on the previews' own grid against msxsound's functions
(they must agree to rounding: the method is the same, only where a window starts moved).
Exit status 0; the numbers are for the stage's judgement and the user's ears (EMU_PLAN.md 6)."""
from __future__ import annotations

import math
import sys
import wave
from pathlib import Path

import numpy as np

FX_LEN = {3: 12, 4: 6, 5: 48, 6: 36}       # the effects' lengths in ticks (pzm.bin's table, WIRING.md)
HZ60 = 21477270 / (1368 * 262) * 5 / 6     # the tune's ticks on a 60 Hz VDP (five VBLANKs in six)
HZ50 = 21477270 / (1368 * 313)             # on a 50 Hz VDP (every VBLANK)
FS = 44100
SPT = FS // 50


def load(path: Path, fs: int) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise SystemExit("%s: 16-bit PCM expected" % path)
        ch, rate = w.getnchannels(), w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float64) / 32767
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if rate != fs:
        n = int(round(len(x) * fs / rate))
        x = np.interp(np.arange(n) * rate / fs, np.arange(len(x)), x)
    return x


# ----- the tempo: where the recording's ticks are

class Tempo:
    """The recording's time (s) of the tune's tick u (a float array), relative to its tick 0: u / hz,
    or the run's own tick times (--ticks; past the last one at the run's mean rate)."""

    def __init__(self, hz: float | None = None, ticks: Path | None = None):
        self.t = None
        if ticks is not None:
            t = []
            for line in ticks.read_text().splitlines():
                f = line.split()
                if f and f[0] == "T":
                    t.append(float(f[2]))
            if len(t) < 2:
                raise SystemExit("%s: no tick times" % ticks)
            self.t = np.array(t)
            self.t0 = float(self.t[0])
            self.hz = (len(t) - 1) / (self.t[-1] - self.t[0])
            self.label = "the run's tick times (%s: %d ticks, %.5f Hz on average, tick 0 at +%.4f s)" % (
                ticks.name, len(t), self.hz, self.t0)
        else:
            self.hz = float(hz)
            self.t0 = None
            self.label = "%.4f ticks a second%s" % (self.hz, " (the previews' own: no correction)"
                                                    if abs(self.hz - 50) < 1e-9 else "")

    def at(self, u: np.ndarray) -> np.ndarray:
        u = np.asarray(u, dtype=np.float64)
        if self.t is None:
            return u / self.hz
        k = np.arange(len(self.t))
        out = np.interp(u, k, self.t) - self.t0
        past = u > k[-1]
        out[past] = self.t[-1] - self.t0 + (u[past] - k[-1]) / self.hz
        return out

    def line_s(self, i: np.ndarray) -> np.ndarray:
        """marks: the time (s from the recording's start) of the register log's T line i."""
        i = np.asarray(i, dtype=np.float64)
        if self.t is None:
            return i / self.hz
        return self.t0 + self.at(i)


def parse_tempo(argv: list[str]) -> tuple[Tempo | None, list[str]]:
    rest, tempo, i = [], None, 0
    while i < len(argv):
        a = argv[i]
        if a in ("--vdp", "--tick-hz", "--ticks") and i + 1 < len(argv):
            v = argv[i + 1]
            if a == "--vdp":
                if v not in ("60", "50"):
                    raise SystemExit("--vdp 60 or --vdp 50")
                tempo = Tempo(HZ60 if v == "60" else HZ50)
            elif a == "--tick-hz":
                tempo = Tempo(float(v))
            else:
                tempo = Tempo(ticks=Path(v))
            i += 2
            continue
        rest.append(a)
        i += 1
    return tempo, rest


# ----- the per-millisecond envelopes and the alignment

def env_ms(x: np.ndarray, fs: int) -> np.ndarray:
    k = fs // 1000
    n = len(x) // k
    return np.sqrt((x[:n * k].reshape(n, k) ** 2).mean(axis=1))


def align(rec: np.ndarray, ref: np.ndarray, fs: int, span_s: float = 1.0, use_s: float = 20.0) -> int:
    """(Before the audit: the preview's grid.) The lag in samples (rec later than ref: positive)."""
    return int(round(align_tempo(rec, ref, fs, Tempo(50.0), span_s, use_s) * fs))


def align_tempo(rec: np.ndarray, ref: np.ndarray, fs: int, tempo: Tempo, span_s: float = 1.0,
                use_s: float = 20.0) -> float:
    """The recording's time (s) of the tune's tick 0: the log envelopes (env_ms: bins of fs // 1000
    samples) of the preview's first use_s x 1000 bins against the recording's, read at the
    recording's times of the same tune positions (tempo), the best Pearson r within +-span_s x 1000
    bins. With 50 ticks a second it is the method before the audit, sample for sample."""
    k = fs // 1000
    a, b = env_ms(rec, fs), env_ms(ref, fs)
    m = int(use_s * 1000)
    a, b = np.log10(a[:m + 3000] + 1e-5), np.log10(b[:m] + 1e-5)
    u = 50.0 * k * np.arange(len(b)) / fs                       # (the preview's bin j: the tune's tick)
    pos = fs * tempo.at(u) / k                                  # (the recording's bin of that tick)
    ka = np.arange(len(a))
    best, lag = -2.0, 0
    span = int(span_s * 1000)
    for d in range(-span, span + 1):
        p = pos + d
        ok = (p >= 0) & (p <= len(a) - 1)
        if ok.sum() < 1000:
            continue
        x = np.interp(p[ok], ka, a)
        v = b[ok]
        if x.std() < 1e-9 or v.std() < 1e-9:
            continue
        c = float(np.corrcoef(x, v)[0, 1])
        if c > best:
            best, lag = c, d
    return lag * k / fs


def shift(x: np.ndarray, lag: int) -> np.ndarray:
    return x[lag:] if lag >= 0 else np.concatenate([np.zeros(-lag), x])


def rec_grid(rec: np.ndarray, ref: np.ndarray, tempo: Tempo, T: int) -> tuple[float, np.ndarray, np.ndarray]:
    """The recording's tick 0 (s), and the starts (samples) of its ticks 0..T-1 in the returned
    copy (zero-padded so that every window fits)."""
    off = align_tempo(rec, ref, FS, tempo)
    st = np.round(FS * (off + tempo.at(np.arange(T)))).astype(np.int64)
    front = int(max(0, -int(st.min())))
    x = np.concatenate([np.zeros(front), rec, np.zeros(8192)])
    return off, st + front, x


# ----- msxsound's per-tick measures, with each tick's window where its tick starts

def tick_db_at(x: np.ndarray, st: np.ndarray) -> np.ndarray:
    """msxsound.tick_db: the AC RMS of each tick's SPT samples in dB."""
    y = np.stack([x[s:s + SPT] for s in st])
    return 20 * np.log10(np.maximum(y.std(axis=1), 1e-7))


def env_from_db(a: np.ndarray, b: np.ndarray) -> dict:
    """msxsound.env_compare's body on two tick-dB arrays (a the reference)."""
    fa, fb = a.max() - 40, b.max() - 40
    m = (a > fa) | (b > fb)
    a2, b2 = np.maximum(a, fa), np.maximum(b, fb)
    out = {"r": None, "mae_db": None, "coverage": None}
    if m.sum() >= 3 and np.std(a2[m]) > 1e-6 and np.std(b2[m]) > 1e-6:
        out["r"] = float(np.corrcoef(a2[m], b2[m])[0, 1])
    both = (a > a.max() - 30) & (b > fb)
    if both.any():
        d = a[both] - b[both]
        out["mae_db"] = float(np.mean(np.abs(d - np.median(d))))
    aud = a > a.max() - 30
    if aud.any():
        out["coverage"] = float(np.mean(b[aud] > b.max() - 40))
    return out


def chroma_at(x: np.ndarray, st: np.ndarray) -> np.ndarray:
    """msxsound.chroma: 12-bin chroma (55 Hz .. 2 kHz) of 4096 samples centred on each tick
    (msxsound.frame: from max(0, the tick's middle - 2048), zero-padded)."""
    n = 4096
    f = np.fft.rfftfreq(n, 1 / FS)
    m = (f >= 55) & (f <= 2000)
    pc = np.round(12 * np.log2(f[m] / 440.0)).astype(int) % 12
    win = np.hanning(n)
    out = np.zeros((len(st), 12))
    for t, s in enumerate(st):
        a = max(0, int(s) + SPT // 2 - n // 2)
        fr = x[a:a + n]
        if len(fr) < n:
            fr = np.pad(fr, (0, n - len(fr)))
        X = np.abs(np.fft.rfft((fr - fr.mean()) * win)) ** 2
        out[t] = np.bincount(pc, weights=X[m], minlength=12)
    return out


def chroma_sim(a: np.ndarray, b: np.ndarray) -> float:
    """msxsound.chroma_similarity's body on two chroma arrays."""
    na, nb = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
    m = (na > 1e-9) & (nb > 1e-9) & (na > np.percentile(na, 10))
    return float(np.mean((a[m] * b[m]).sum(axis=1) / (na[m] * nb[m])))


def pitch_at(ms, x: np.ndarray, st: np.ndarray, db: np.ndarray) -> np.ndarray:
    """YIN (msxsound.yin, 40 Hz-4 kHz) on 2048 samples from each tick's start, where the tick is
    within 30 dB of the loudest; 0 where not periodic (aperiodicity above 0.2)."""
    out = np.zeros(len(st))
    for t, s in enumerate(st):
        if db[t] < db.max() - 30:
            continue
        r = ms.yin(x[s:s + 2048], int(FS / 40), lo=int(FS / 4000))
        if r and r[1] <= 0.2 and r[0] > 0:
            out[t] = FS / r[0]
    return out


def pitch_track(ms, x: np.ndarray, T: int) -> np.ndarray:
    """(Before the audit, kept for the other scripts: the previews' grid.)"""
    st = np.arange(T) * SPT
    return pitch_at(ms, x, st, tick_db_at(np.concatenate([x, np.zeros(8192)]), st))


def tracks(ms, rec: np.ndarray, ref: np.ndarray, tempo: Tempo, T: int = 3000) -> tuple:
    """For the other scripts: (the recording's tick 0 in s, the ticks compared, the preview's tick dB
    and YIN pitch, the recording's), the recording read at its own ticks (tempo)."""
    T = min(len(ref) // SPT, T)
    off, st, x = rec_grid(rec, ref, tempo, T)
    T = int(min(T, np.searchsorted(st, len(x) - 8192 - SPT, side="right")))
    st = st[:T]
    sr = np.arange(T) * SPT
    rp = np.concatenate([ref, np.zeros(8192)])
    a, b = tick_db_at(rp, sr), tick_db_at(x, st)
    return off, T, a, pitch_at(ms, rp, sr, a), b, pitch_at(ms, x, st, b)


def pitch_line(pa: np.ndarray, pb: np.ndarray, mask: np.ndarray | None = None) -> str:
    m = (pa > 0) & (pb > 0)
    if mask is not None:
        m &= mask
    if not m.any():
        return "no tick periodic in both"
    d = 1200 * np.log2(pb[m] / pa[m])
    do = (d + 600) % 1200 - 600
    return "%d ticks: %.1f %% the same note (50 cents modulo octaves), %.1f %% exact, median %.1f cents" % (
        int(m.sum()), 100 * np.mean(np.abs(do) < 50), 100 * np.mean(np.abs(d) < 50), float(np.median(np.abs(do))))


# ----- the modes

def tune(ms, rec: np.ndarray, prev: Path, tempo: Tempo) -> tuple[list[str], float]:
    ref = load(prev, FS)
    T = min(len(ref) // SPT, 3000)
    off, st, x = rec_grid(rec, ref, tempo, T)
    T = int(min(T, np.searchsorted(st, len(x) - 8192 - SPT, side="right")))
    st = st[:T]
    sr = np.arange(T) * SPT
    a, b = tick_db_at(np.concatenate([ref, np.zeros(8192)]), sr), tick_db_at(x, st)
    both = (a > a.max() - 30) & (b > b.max() - 30)
    lvl = float(np.median(b[both] - a[both])) if both.any() else float("nan")
    spread = float(np.percentile(np.abs((b[both] - a[both]) - lvl), 90)) if both.any() else float("nan")
    env = env_from_db(a, b)
    chroma = chroma_sim(chroma_at(ref, sr), chroma_at(x, st))
    pa, pb = pitch_at(ms, ref, sr, a), pitch_at(ms, x, st, b)
    r = env.get("r")
    return ["%s: lag %+.3f s, %d ticks; level %+.1f dB (90th percentile spread %.1f dB); envelope r %s, "
            "mean |diff| %s dB, coverage %s; chroma %.3f; pitch %s" % (
                prev.name, off, T, lvl, spread, "%.3f" % r if r is not None else "-",
                "%.1f" % env["mae_db"] if env.get("mae_db") is not None else "-",
                "%.2f" % env["coverage"] if env.get("coverage") is not None else "-", chroma,
                pitch_line(pa, pb))], off


def tune_end(rec: np.ndarray, tempo: Tempo, off: float) -> str:
    x = np.concatenate([rec, np.zeros(8192)])
    last = int((len(rec) - SPT) / FS * tempo.hz)                # (about the recording's last tick)
    u = np.arange(0, last + 1)
    st = np.round(FS * (off + tempo.at(u))).astype(np.int64)
    u, st = u[(st >= 0) & (st + SPT <= len(rec))], st[(st >= 0) & (st + SPT <= len(rec))]
    if len(u) == 0 or u[-1] < 3005 + 25:
        return "the tune's end: the recording stops before the tune's tick 3,030 (not checked)"
    db = tick_db_at(x, st)
    peak = db[u < 3000].max()
    loud = db > peak - 60
    title = None
    for i in np.nonzero(u >= 3200)[0]:
        if i + 100 <= len(u) and loud[i:i + 100].sum() >= 90:
            title = i + int(np.argmax(loud[i:i + 100]))     # (its first sounding tick)
            break
    j0 = int(np.nonzero(u >= 3005)[0][0])
    j1 = title if title is not None else len(u)
    w = db[j0:j1]
    k = int(np.argmax(w))
    return ("the tune's end: from the tune's tick 3,005 (%.2f s into the recording) to %s: loudest tick %.1f dB "
            "under the tune's peak (at %.2f s) (%s: 50 dB or more)" % (
                st[j0] / FS, "the title's music at its tick %d (%.2f s)" % (u[title], st[title] / FS)
                if title is not None else "the recording's end", peak - w[k], st[j0 + k] / FS,
                "PASS" if peak - w[k] >= 50 else "FAIL"))


def marks(ms, rec: np.ndarray, log: Path, buzz: list[Path], tempo: Tempo) -> list[str]:
    ts, started = [], False
    for line in log.read_text().splitlines():
        f = line.split()
        if not f:
            continue
        if f[0] == "S":
            started = True
            continue
        if f[0] == "T" and started:
            ts.append((int(f[2]), int(f[4])))           # (tn_snd, tn_last)
    # (a start or a restart: tn_snd did not count down, 1 a tick, while the voice was busy: effect
    # 6 restarted every pass holds it at 36)
    starts = []
    for i, (snd, last) in enumerate(ts):
        prev = ts[i - 1][0] if i else 0
        if snd > 1 and snd >= prev and last in FX_LEN:
            starts.append((i, last))
    # (effect 6 restarted every pass: one segment)
    segs = []
    for i, n in starts:
        if segs and n == 6 and segs[-1][2] == 6 and i <= segs[-1][3] + 2:
            segs[-1][1] = i + FX_LEN[6]
            segs[-1][3] = i
            segs[-1][4] += 1
            continue
        segs.append([i, i + FX_LEN[n], n, i, 1])     # (start, end, effect, last restart, starts)
    x = np.concatenate([rec, np.zeros(8192)])
    T = len(ts)
    st = np.round(FS * tempo.line_s(np.arange(T))).astype(np.int64)
    ok = st + SPT <= len(rec)
    T = int(ok.sum()) if ok.all() else int(np.argmin(ok))
    st = st[:T]
    a = tick_db_at(x, st)
    inside = np.zeros(T, bool)
    for s, e, *_ in segs:
        inside[s:min(e, T)] = True
    out = ["%d T lines (%d within the recording), %d effect starts, %d segments; times: %s" % (
        len(ts), T, len(starts), len(segs), tempo.label if tempo.t is not None else
        "line i at i / %.4f s (approximate: give --ticks)" % tempo.hz)]

    def pmean(v: np.ndarray) -> float:
        return float(10 * np.log10(np.mean(10 ** (v / 10)))) if len(v) else float("nan")
    bz = []
    for p in buzz:
        b = load(p, FS)
        n = min(len(b) // SPT, 200)
        sb = np.arange(n) * SPT
        hz = pitch_at(ms, np.concatenate([b, np.zeros(8192)]), sb, tick_db_at(np.concatenate([b, np.zeros(8192)]), sb))
        bz.append("%s %.1f Hz" % (p.name, float(np.median(hz[hz > 0])) if (hz > 0).any() else float("nan")))
    for s, e, n, _, k in segs:
        if s >= T:
            out.append("effect %d at T line %d: past the recording's end" % (n, s))
            continue
        before = [t for t in range(max(0, s - 25), s) if not inside[t]]
        lv, lm = pmean(a[s:min(e, T)]), pmean(a[before]) if before else float("nan")
        line = "effect %d at %6.2f s (%3d ticks%s): level %6.1f dB, the music before it %6.1f dB, %+5.1f dB" % (
            n, st[s] / FS, e - s, ", %d starts" % k if k > 1 else "", lv, lm, lv - lm)
        if n == 6:
            seg = st[s:min(e, T)]
            hz = pitch_at(ms, x, seg, a[s:min(e, T)])
            line += "; pitch %.1f Hz" % (float(np.median(hz[hz > 0])) if (hz > 0).any() else float("nan"))
            if bz:
                line += " (previews: %s)" % ", ".join(bz)
        out.append(line)
    return out


def selfcheck(ms, prev: Path, other: Path) -> list[str]:
    """The per-tick-start measures on the previews' grid against msxsound's own functions."""
    ref, oth = load(prev, FS), load(other, FS)
    T = min(len(ref), len(oth)) // SPT
    sr = np.arange(T) * SPT
    rp, op = np.concatenate([ref, np.zeros(8192)]), np.concatenate([oth, np.zeros(8192)])
    a, b = tick_db_at(rp, sr), tick_db_at(op, sr)
    out = []
    out.append("tick_db: max |difference| %.2e dB" % float(np.max(np.abs(a - ms.tick_db(ref, T)))))
    e1, e2 = env_from_db(a, b), ms.env_compare(ref, oth, T)
    out.append("env_compare: %s against %s" % (
        {k: round(v, 9) for k, v in e1.items() if v is not None},
        {k: round(e2[k], 9) for k in ("r", "mae_db", "coverage") if e2.get(k) is not None}))
    c1, c2 = chroma_sim(chroma_at(ref, sr), chroma_at(oth, sr)), ms.chroma_similarity(ref, oth, T)
    out.append("chroma_similarity: %.9f against %.9f" % (c1, c2))
    n = min(T, 600)
    p1 = pitch_at(ms, rp, sr[:n], a[:n])
    p2 = np.zeros(n)
    full = ms.tick_db(ref, n)
    for t in range(n):                       # (the old int_wavcmp.pitch_track, inline)
        if full[t] < full.max() - 30:
            continue
        r = ms.yin(ref[t * SPT:t * SPT + 2048], int(FS / 40), lo=int(FS / 4000))
        if r and r[1] <= 0.2 and r[0] > 0:
            p2[t] = FS / r[0]
    out.append("pitch (first %d ticks): %d periodic, %d differ" % (n, int((p1 > 0).sum()), int(np.sum(p1 != p2))))
    return out


def main() -> int:
    tempo, argv = parse_tempo(sys.argv[1:])
    if len(argv) < 3:
        raise SystemExit(__doc__)
    wt, mode, rec_p = Path(argv[0]), argv[1], Path(argv[2])
    sys.path.insert(0, str(wt / "tools"))
    import msxsound as ms  # noqa: E402
    if ms.FS != FS or ms.SPT != SPT:
        raise SystemExit("msxsound's FS/SPT changed")
    if mode == "selfcheck":
        for line in selfcheck(ms, rec_p, Path(argv[3])):
            print("  " + line)
        return 0
    if tempo is None:
        raise SystemExit("give the recording's tempo: --vdp 60 (a 60 Hz machine), --vdp 50, --tick-hz HZ "
                         "or --ticks TICKS.txt (see the usage)")
    rec = load(rec_p, FS)
    print("%s: %.2f s; tempo: %s" % (rec_p.name, len(rec) / FS, tempo.label))
    if mode == "tune":
        off0 = None
        for p in argv[3:]:
            lines, off = tune(ms, rec, Path(p), tempo)
            off0 = off if off0 is None else off0
            for line in lines:
                print("  " + line)
        print("  " + tune_end(rec, tempo, off0 if off0 is not None else 0.0))
    elif mode == "marks":
        log = Path(argv[3])
        buzz = [Path(p) for p in argv[5:]] if len(argv) > 4 and argv[4] == "--buzz" else []
        for line in marks(ms, rec, log, buzz, tempo):
            print("  " + line)
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
