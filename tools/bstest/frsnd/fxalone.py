"""Scratch (the range's step 12): the range's effects heard alone in openMSX (s11/frs.tcl frs_drive with
TUNEOFF: the drive fr_mixed, the tune ended at its tick 1 by a harness poke, "record start -audioonly"
at tns_go; the register log's T lines carry each tick's emulated time, the S line the recording's
start) against frm.bin's effect streams and the converter's previews (impl/sound/wav frm_fx_scc.wav,
frm_fx_psg.wav: effects 2, 3, 4 rendered on the converters' chip models), by pitch: msxsound's YIN
on each tick's samples (the tick's own 20 ms, from its T line's time).

- Effects 3 and 4: each sounding tick's YIN pitch against that tick's record (frm.bin decoded:
  effect 3 864/867, 1734/1721, 3469/3496 Hz; effect 4 791 falling to 432 Hz), within 50 cents; the
  same on the previews.
- Effect 2 (the shot, a noise): its ticks aperiodic (YIN aperiodicity above 0.3: no pitch, no
  buzz), as in the preview.
- Between the effects (from the first effect on: the tune's ticks 0 and 1 before it are the
  poke's): every tick outside an effect's sound (and the tick after it), and every 20 ms of the gaps
  where no tick runs, 50 dB or more under the effects' loudest tick (the project's criterion, as
  the tune's end: nothing left sounding, a shot cut by a hit sound silenced, no hiss or click from
  the player).

usage: fxalone.py ROOT REC.wav REC_fr.txt PREVIEW.wav scc|psg"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import frwavcmp as fw  # noqa: E402

iw = fw.iw
FS, SPT = fw.FS, fw.SPT
TICKS = {"scc": {2: 6, 3: 16, 4: 12}, "psg": {2: 6, 3: 16, 4: 12}}


def tick_pitch(ms, x: np.ndarray, s: int) -> tuple[float, float]:
    y = x[s:s + SPT]
    r = ms.yin(y, int(FS / 200), lo=int(FS / 5000))
    if not r or r[0] <= 0:
        return 0.0, 1.0
    return FS / r[0], r[1]


def db(x: np.ndarray, s: int) -> float:
    y = x[s:s + SPT]
    return float(20 * np.log10(max(y.std(), 1e-7)))


def from_log(log: Path) -> tuple[float, list]:
    t_s, rows = None, []
    for line in log.read_text().splitlines():
        f = line.split()
        if not f:
            continue
        if f[0] == "S" and t_s is None:
            t_s = float(f[2])
        elif f[0] == "T" and t_s is not None and len(f) > 11:
            rows.append((int(f[2]), int(f[4]), float(f[11]) - t_s))      # (tn_snd, tn_last, s into the recording)
    return t_s, rows


def main() -> int:
    root, rec_p, log, prev, chip = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5]
    sys.path.insert(0, str(root / "tools"))
    import msxsound as ms
    x = np.concatenate([iw.load(rec_p, FS), np.zeros(8192)])
    _, rows = from_log(log)
    starts = []
    for i in range(1, len(rows)):
        if rows[i][0] > rows[i - 1][0] - 1 and rows[i][0] > 1 and rows[i][1] in (2, 3, 4):
            starts.append((i - 1, rows[i][1]))
    want = fw.FX_HZ[chip]
    good = {3: [0, 0], 4: [0, 0]}
    noise = [0, 0]
    sounding = set()
    peak = -200.0
    for j, (i, n) in enumerate(starts):
        nxt = starts[j + 1][0] if j + 1 < len(starts) else len(rows)
        L = min(TICKS[chip][n], nxt - i)                 # (cut by the next effect)
        for k in range(L + 1):
            sounding.add(i + k)
        for k in range(L):
            if i + k >= len(rows):
                break
            s = int(round(FS * rows[i + k][2])) + 64     # (past the tick's writes)
            peak = max(peak, db(x, s))
            hz, ap = tick_pitch(ms, x, s)
            if n == 2:
                noise[0] += ap > 0.3
                noise[1] += 1
            else:
                c = 1200 * np.log2(hz / want[n][k]) if hz > 0 else 9999
                good[n][0] += abs(c) < 50
                good[n][1] += 1
    # (between the effects: the ticks the log has that no effect holds; and the gaps between the T
    # lines, where no tick runs: every 20 ms there)
    first = starts[0][0] if starts else len(rows)
    quiet = []
    for i, r in enumerate(rows):
        if i >= first and i not in sounding:
            quiet.append(db(x, int(round(FS * r[2])) + 64))
    gaps = []
    for i in range(first + 1, len(rows)):
        a, b = rows[i - 1][2] + 0.06, rows[i][2] - 0.02
        t = a
        while t < b:
            gaps.append(db(x, int(round(FS * t))))
            t += 0.02
    q = max(quiet + gaps) if quiet or gaps else -200.0
    print("%s: %d effect starts (%s); effect 3 ticks at their record's pitch (50 cents): %d of %d; effect 4: %d of %d; "
          "effect 2 ticks aperiodic (noise): %d of %d; the loudest tick between the effects %.1f dB under the "
          "effects' loudest (%d ticks, %d gap windows): %s" % (
              rec_p.name, len(starts), ", ".join("%d: %d" % (n, sum(1 for _, m in starts if m == n)) for n in (2, 3, 4)),
              good[3][0], good[3][1], good[4][0], good[4][1], noise[0], noise[1], peak - q, len(quiet), len(gaps),
              "PASS" if peak - q >= 50 else "FAIL"))
    # the previews: effects 2, 3, 4 one after another; their onsets by level
    p = np.concatenate([iw.load(prev, FS), np.zeros(8192)])
    lv = np.array([db(p, k * SPT) for k in range((len(p) - 8192) // SPT)])
    on = [k for k in range(len(lv)) if lv[k] > lv.max() - 40 and (k == 0 or lv[k - 1] <= lv.max() - 40)]
    out = []
    for n, k0 in zip((2, 3, 4), on):
        if n == 2:
            aps = [tick_pitch(ms, p, (k0 + k) * SPT)[1] for k in range(TICKS[chip][n])]
            out.append("effect 2: %d of %d ticks aperiodic" % (sum(a > 0.3 for a in aps), len(aps)))
        else:
            ok = 0
            for k in range(TICKS[chip][n]):
                hz, _ = tick_pitch(ms, p, (k0 + k) * SPT)
                ok += hz > 0 and abs(1200 * np.log2(hz / want[n][k])) < 50
            out.append("effect %d: %d of %d ticks at their record's pitch" % (n, ok, TICKS[chip][n]))
    print("  the preview %s (onsets at ticks %s): %s" % (prev.name, on[:3], "; ".join(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
