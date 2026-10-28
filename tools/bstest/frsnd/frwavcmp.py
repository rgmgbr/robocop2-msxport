"""Scratch (the range's step 12): an openMSX recording of the range's sound (s11/frs.tcl: "record start
-audioonly" at the first tune start, tns_go) against the converter's previews (impl/sound/wav:
frm_scc.wav, frm_sccfm.wav, frm_fm.wav, frm_psg.wav: frm.bin decoded on the converters' chip models;
frm_amiga.wav: the original), with the Brainstorm integration's measures (brainstorm/impl/sound
int_wavcmp.py: helpers imported unchanged; msxsound's YIN, chroma, envelope), FRM's tune of 5,999
ticks.

tune: per preview: the lag (the recording's tick 0), the level offset, the envelope r, the chroma,
  the pitch track (YIN per tick, the same note within 50 cents modulo octaves, exact, the median
  cents); the cleanliness: per tick the energy above 4 kHz against 50 Hz-4 kHz in the recording and
  the preview, the median difference and the ticks where the recording has 12 dB or more of it than
  the preview (a hiss or a click the player adds); then the tune's end: the loudest tick from the
  tune's tick 6,004 to the recording's end (the time out and the silent OUT OF TIME. screen) must be
  50 dB or more under the tune's peak.
marks (a driven recording with its register log, frs.tcl's DIR/TAG_fr.txt): each effect start (a T
  line whose tn_snd rose; tn_last the effect), its level against the music just before it (the
  power mean of the 25 ticks before, outside effects); for the hit sounds (3, 4) the frequency of
  the strongest peak the effect adds in its ticks 0, 1 and 3 (one tick's samples, 300 Hz-4 kHz,
  the spectrum against the tick before the effect) against that tick's record (frm.bin's streams:
  effect 3 864, 864, 1734 Hz on the SCC; effect 4 791, 736 Hz, falling to 432). The T lines are the tune's ticks 0, 1, ... (no held tick after tick 0): their times are
  the tune's tick 0 found by the alignment against PREVIEW plus TEMPO's.

usage: frwavcmp.py ROOT tune REC.wav PREVIEW.wav [PREVIEW.wav ...] --vdp 60|50
       frwavcmp.py ROOT marks REC.wav REC_fr.txt PREVIEW.wav scc|psg --vdp 60|50   (the effects' chip:
       scc with an SCC, psg with the OPLL alone or the PSG alone)"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

BS = Path(__file__).resolve().parent      # z80.py, pzsim.py, int_wavcmp.py: the Brainstorm night's
sys.path.insert(0, str(BS))
import int_wavcmp as iw  # noqa: E402

FS, SPT = iw.FS, iw.SPT
TUNE_T = 5999
FX_LEN = {2: 6, 3: 16, 4: 12}
FX_HZ = {                               # (each tick's frequency: frm.bin's effect streams decoded, the
    "scc": {3: [864] * 3 + [1734] * 4 + [864] * 2 + [3469] * 4 + [1734] * 3,      # SCC's period and its
            4: [791, 736, 687, 645, 608, 574, 544, 518, 493, 471, 451, 432]},  # waveform's 4 cycles; the
    "psg": {3: [867] * 3 + [1721] * 4 + [867] * 2 + [3496] * 4 + [1721] * 3,      # PSG's tone period)
            4: [793, 736, 686, 647, 608, 574, 546, 518, 493, 472, 451, 432]}}


def hf_ratio(x: np.ndarray, st: np.ndarray) -> np.ndarray:
    """Per tick (SPT samples from its start): 10 log10(energy 4-16 kHz / energy 50 Hz-4 kHz)."""
    f = np.fft.rfftfreq(SPT, 1 / FS)
    lo, hi = (f >= 50) & (f < 4000), (f >= 4000) & (f <= 16000)
    win = np.hanning(SPT)
    out = np.zeros(len(st))
    for i, s in enumerate(st):
        y = x[s:s + SPT]
        if len(y) < SPT:
            y = np.pad(y, (0, SPT - len(y)))
        P = np.abs(np.fft.rfft((y - y.mean()) * win)) ** 2
        out[i] = 10 * np.log10((P[hi].sum() + 1e-12) / (P[lo].sum() + 1e-12))
    return out


def tune(ms, rec: np.ndarray, prev: Path, tempo) -> tuple[list[str], float]:
    ref = iw.load(prev, FS)
    T = min(len(ref) // SPT, TUNE_T)
    off, st, x = iw.rec_grid(rec, ref, tempo, T)
    T = int(min(T, np.searchsorted(st, len(x) - 8192 - SPT, side="right")))
    st = st[:T]
    sr = np.arange(T) * SPT
    rp = np.concatenate([ref, np.zeros(8192)])
    a, b = iw.tick_db_at(rp, sr), iw.tick_db_at(x, st)
    both = (a > a.max() - 30) & (b > b.max() - 30)
    lvl = float(np.median(b[both] - a[both])) if both.any() else float("nan")
    spread = float(np.percentile(np.abs((b[both] - a[both]) - lvl), 90)) if both.any() else float("nan")
    env = iw.env_from_db(a, b)
    chroma = iw.chroma_sim(iw.chroma_at(ref, sr), iw.chroma_at(x, st))
    pa, pb = iw.pitch_at(ms, rp, sr, a), iw.pitch_at(ms, x, st, b)
    ha, hb = hf_ratio(rp, sr), hf_ratio(x, st)
    snd = both
    d = hb[snd] - ha[snd]
    r = env.get("r")
    return ["%s: lag %+.3f s, %d ticks; level %+.1f dB (90th percentile spread %.1f dB); envelope r %s, "
            "mean |diff| %s dB; chroma %.3f; pitch %s; above 4 kHz: recording %.1f dB, preview %.1f dB (median "
            "of the sounding ticks), the recording 12 dB or more over the preview on %d of %d ticks" % (
                prev.name, off, T, lvl, spread, "%.3f" % r if r is not None else "-",
                "%.1f" % env["mae_db"] if env.get("mae_db") is not None else "-", chroma, iw.pitch_line(pa, pb),
                float(np.median(hb[snd])), float(np.median(ha[snd])), int(np.sum(d >= 12 + np.median(d))),
                int(snd.sum()))], off


def tune_end(rec: np.ndarray, tempo, off: float) -> str:
    x = np.concatenate([rec, np.zeros(8192)])
    last = int((len(rec) - SPT) / FS * tempo.hz)
    u = np.arange(0, last + 1)
    st = np.round(FS * (off + tempo.at(u))).astype(np.int64)
    keep = (st >= 0) & (st + SPT <= len(rec))
    u, st = u[keep], st[keep]
    if len(u) == 0 or u[-1] < TUNE_T + 30:
        return "the tune's end: the recording stops before the tune's tick %d (not checked)" % (TUNE_T + 30)
    db = iw.tick_db_at(x, st)
    peak = db[u < TUNE_T].max()
    j0 = int(np.nonzero(u >= TUNE_T + 5)[0][0])
    w = db[j0:]
    k = int(np.argmax(w))
    return ("the tune's end: from the tune's tick %d (%.2f s into the recording) to the recording's end (%.2f s, "
            "%d ticks): loudest tick %.1f dB under the tune's peak (at %.2f s) (%s: 50 dB or more)" % (
                TUNE_T + 5, st[j0] / FS, len(rec) / FS, len(w), peak - w[k], st[j0 + k] / FS,
                "PASS" if peak - w[k] >= 50 else "FAIL"))


def peak_added(x: np.ndarray, s_fx: int, s_before: int) -> float:
    """The frequency (Hz) whose power rises most from one tick before the effect to the effect's
    tick at s_fx (one tick's samples, Hann, zero-padded to 16384, 300 Hz-4 kHz)."""
    n = 16384
    win = np.hanning(SPT)
    def spec(s: int) -> np.ndarray:
        y = x[s:s + SPT]
        if len(y) < SPT:
            y = np.pad(y, (0, SPT - len(y)))
        return np.abs(np.fft.rfft((y - y.mean()) * win, n)) ** 2
    f = np.fft.rfftfreq(n, 1 / FS)
    m = (f >= 300) & (f <= 4000)
    a = spec(s_fx)
    b = spec(max(0, s_before))
    gain = 10 * np.log10((a[m] + 1e-9) / (b[m] + 1e-9)) + 10 * np.log10(a[m] / a[m].max() + 1e-12)
    return float(f[m][int(np.argmax(gain))])


def marks(ms, rec: np.ndarray, log: Path, prev: Path, tempo, chip: str) -> list[str]:
    ts, started = [], False
    for line in log.read_text().splitlines():
        f = line.split()
        if not f:
            continue
        if f[0] == "S":
            started = True
            continue
        if f[0] == "T" and started:
            ts.append((int(f[2]), int(f[4])))           # (tn_snd, tn_last) at the tick's entry
    starts = []
    for i in range(1, len(ts)):
        snd, last = ts[i]
        if snd > ts[i - 1][0] - 1 and snd > 1 and last in FX_LEN:
            starts.append((i - 1, last))                # (the tick that started it: the line before)
    ref = iw.load(prev, FS)
    off = iw.align_tempo(rec, ref, FS, tempo)
    x = np.concatenate([rec, np.zeros(8192)])
    T = len(ts)
    st = np.round(FS * (off + tempo.at(np.arange(T)))).astype(np.int64)
    ok = (st >= 0) & (st + SPT <= len(rec))
    a = np.full(T, -140.0)
    a[ok] = iw.tick_db_at(x, st[ok])
    inside = np.zeros(T, bool)
    for s, n in starts:
        inside[s:s + FX_LEN[n]] = True

    def pmean(v: np.ndarray) -> float:
        return float(10 * np.log10(np.mean(10 ** (v / 10)))) if len(v) else float("nan")
    by = {n: [] for n in FX_LEN}
    hz = {n: [] for n in FX_HZ[chip]}
    for s, n in starts:
        if not ok[min(s + FX_LEN[n], T - 1)]:
            continue
        before = [t for t in range(max(0, s - 25), s) if not inside[t]]
        if before:
            by[n].append(pmean(a[s:s + FX_LEN[n]]) - pmean(a[before]))
        if n in FX_HZ[chip] and s >= 1:
            for k in (0, 1, 3):            # (its first records; effect 3's tick 3: the octave up)
                if s + k < T:
                    hz[n].append((peak_added(x, int(st[s + k]), int(st[s - 1])), FX_HZ[chip][n][k]))
    out = ["%d T lines, %d effect starts (%s); tick 0 at %+.3f s (aligned on %s)" % (
        T, len(starts), ", ".join("%d: %d" % (n, sum(1 for _, m in starts if m == n)) for n in FX_LEN), off, prev.name)]
    for n in FX_LEN:
        v = np.array(by[n])
        if len(v):
            out.append("effect %d: %d starts, level over its ticks against the music before it: median %+.1f dB "
                       "(%+.1f to %+.1f)" % (n, len(v), float(np.median(v)), float(v.min()), float(v.max())))
    for n in FX_HZ[chip]:
        v = np.array(hz[n])
        if len(v):
            c = 1200 * np.log2(v[:, 0] / v[:, 1])
            oc = (c + 600) % 1200 - 600
            out.append("effect %d (%s stream): the peak each of its ticks 0, 1 and 3 adds against that tick's frequency: "
                       "%d of %d within 50 cents, %d more an octave off, median |cents| %.0f" % (
                           n, chip.upper(), int(np.sum(np.abs(c) < 50)), len(v),
                           int(np.sum((np.abs(c) >= 50) & (np.abs(oc) < 50))), float(np.median(np.abs(c)))))
    return out


def main() -> int:
    tempo, argv = iw.parse_tempo(sys.argv[1:])
    root, mode, rec_p = Path(argv[0]), argv[1], Path(argv[2])
    sys.path.insert(0, str(root / "tools"))
    import msxsound as ms  # noqa: E402
    if tempo is None:
        raise SystemExit("--vdp 60|50")
    rec = iw.load(rec_p, FS)
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
        for line in marks(ms, rec, Path(argv[3]), Path(argv[4]), tempo, argv[5] if len(argv) > 5 else "scc"):
            print("  " + line)
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
