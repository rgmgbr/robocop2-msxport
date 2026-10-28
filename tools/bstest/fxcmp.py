#!/usr/bin/env python3
"""Level 1's sound effects of two builds compared by their starts, blind to the CPU time (level 2's
gate, docs/HARNESS.md 5.21).

usage: fxcmp.py BASE_sn.txt NEW_sn.txt
       fxcmp.py --starts BASE/fx_scc.txt NEW/fx_scc.txt

The logs: tools/bstest/l2base.tcl l2b_sn_arm's, beside the PSG writes of the LOCKSTEP=24 builds
(W/l1/fx/pw_scc_sn.txt, pw_psg_sn.txt): "F V" at every LOCKSTEP frame's start, "S V EFFECT CHANNEL"
at every start (sndplay.asm sq_sfx), "G V" the gun (channels 0-2), "X V" a stop (every channel),
"T V PSG VOICES [SCC]" at every sound tick (V counts VBLANKs).

Why not write for write: the logic asks for an effect in a game tick; the VBLANK interrupt starts
it at the first VBLANK after the next tick's frame_keys queued it. Under LOCKSTEP=24 a frame (two
game ticks) starts every 24 VBLANKs whatever the CPU time, but where the frame's work reaches
frame_keys moves with the CPU time, so a start moves by whole VBLANKs inside its frame, and the
effects that overlap it then interleave otherwise on the chips (the PSG's shared noise period and
mixer, the voice a channel-3 effect takes). What a change of the CPU time cannot move: the effects
asked for, their order, the frame each one starts in, and each effect's own sound from its start.

Verdicts:
- the starts: the same effects (and gun, stops) in the same order, each in the same LOCKSTEP frame
  as the base's (the tolerance the cadence gives: a start may move inside its frame, 24 VBLANKs or
  20 sound ticks, never out of it); the moves inside the frames are reported;
- each start's own sound, sound tick by sound tick from its start: per Amiga channel it takes, the
  SCC channel (period, volume, waveform; "off" at volume 0 or disabled) and the PSG voice that
  channel owns, whichever it is (volume; the tone period when the tone is on; the voice's own noise
  period, from RAM, when the noise is on), until a later start may take it in either run: the
  next start on the channel (any channel-3 start too for a PSG voice, which may take it; any start
  for channel 3's PSG voice, which a channel 0-2 start may take) or a stop. Exact.
--starts: sess_fxlog.tcl's starts (S lines): the same effects in the same order.
Exit 0 when every verdict passes."""
from __future__ import annotations

import collections
import sys
from pathlib import Path

LOCKSTEP = 24                   # (the builds' frames: 24 VBLANKs)


class Log:
    def __init__(self, path: Path):
        self.frames: list[int] = []             # VBLANK of each frame's start
        self.starts: list[dict] = []
        self.ticks: list[tuple] = []            # (V, psg, voices, scc)
        last = None
        for line in path.read_text().splitlines():
            f = line.split()
            if not f or f[0] == "#":
                continue
            k = f[0]
            if k == "F":
                self.frames.append(int(f[1]))
            elif k in ("S", "G", "X"):
                if k == "S":
                    kind, chans = f"effect {f[2]}", (set() if f[3] == "x" else {int(f[3])})
                elif k == "G":
                    kind, chans = "gun", {0, 1, 2}
                else:
                    kind, chans = "stop", {0, 1, 2, 3}
                self.starts.append({"v": int(f[1]), "kind": kind, "chans": chans, "frame": len(self.frames),
                                    "f0": self.frames[-1] if self.frames else 0, "tick": len(self.ticks)})
            elif k == "T":
                if len(f) > 2:
                    last = (bytes.fromhex(f[2]), bytes.fromhex(f[3]), bytes.fromhex(f[4]) if len(f) > 4 else None)
                if last is None:
                    raise SystemExit(f"{path}: a repeated sound tick before the first state")
                self.ticks.append((int(f[1]),) + last)

    def horizon(self, k: int, c: int, part: str) -> int:
        """Sound ticks from start k until a later start may take channel c's part (or the log ends)."""
        t0 = self.starts[k]["tick"]
        for s in self.starts[k + 1:]:
            ch = s["chans"]
            if c in ch or (part == "psg" and (3 in ch or (c == 3 and ch))):
                return s["tick"] - t0
        return len(self.ticks) - t0


def scc_state(t: tuple, c: int):
    scc = t[3]
    vol = scc[0xAA + c] & 15
    if not vol or not (scc[0xAF] >> c) & 1:
        return "off"
    return (scc[0xA0 + 2 * c] | (scc[0xA1 + 2 * c] & 15) << 8, vol, scc[32 * c:32 * c + 32].hex())


def psg_state(t: tuple, c: int):
    psg, voices = t[1], t[2]
    for v in range(3):
        left, noise, owner = voices[3 * v:3 * v + 3]
        if left and (owner if owner != 0xFF else v) == c:    # (the gun's parts: no channel, voices A-C)
            vol = psg[8 + v] & 0x1F
            tone, nz = not (psg[7] >> v) & 1, not (psg[7] >> (3 + v)) & 1
            if not vol or not (tone or nz):
                return "off"
            return (vol, (psg[2 * v] | (psg[2 * v + 1] & 15) << 8) if tone else None, noise if nz else None)
    return "off"


def compare(a: Log, b: Log) -> int:
    bad = []
    na, nb = len(a.starts), len(b.starts)
    kinds = [s["kind"] for s in a.starts] == [s["kind"] for s in b.starts]
    first = next((i for i, (x, y) in enumerate(zip(a.starts, b.starts)) if x["kind"] != y["kind"]), min(na, nb))
    if na != nb or not kinds:
        bad.append(f"the starts differ from start {first} on (base {na}, new {nb})")
    frames = [i for i, (x, y) in enumerate(zip(a.starts, b.starts)) if x["frame"] != y["frame"]]
    if frames:
        i = frames[0]
        bad.append(f"{len(frames)} starts out of the base's frame (start {i}, {a.starts[i]['kind']}: frame "
                   f"{a.starts[i]['frame']} / {b.starts[i]['frame']})")
    moves = collections.Counter((y["v"] - y["f0"]) - (x["v"] - x["f0"]) for x, y in zip(a.starts, b.starts))
    far = [m for m in moves if abs(m) >= LOCKSTEP]
    if far:
        bad.append(f"starts moved by {sorted(far)} VBLANKs inside their frames (a frame is {LOCKSTEP})")
    print(f"starts: {na} / {nb}, " + ("the same in order" if na == nb and kinds else "DIFFERENT")
          + f"; {sum(1 for s in a.starts if s['kind'] == 'stop')} stops, frames {len(a.frames)} / {len(b.frames)}; "
          f"every start in the base's frame: {'yes' if not frames else 'NO'}; its move inside the frame (VBLANKs, "
          f"new - base): {dict(sorted(moves.items()))}")
    parts = {"scc": [0, 0, 0], "psg": [0, 0, 0]}       # parts compared, ticks compared, parts that differ
    diffs = []
    has_scc = bool(a.ticks) and a.ticks[0][3] is not None and bool(b.ticks) and b.ticks[0][3] is not None
    for k, (x, y) in enumerate(zip(a.starts, b.starts)):
        if x["kind"] != y["kind"] or x["kind"] == "stop":
            continue
        for c in sorted(x["chans"]):
            for part, fn in (("scc", scc_state), ("psg", psg_state)):
                if part == "scc" and not has_scc:
                    continue
                h = min(a.horizon(k, c, part), b.horizon(k, c, part))
                p = parts[part]
                p[0] += 1
                p[1] += max(h, 0)
                for j in range(max(h, 0)):
                    sa, sb = fn(a.ticks[x["tick"] + j], c), fn(b.ticks[y["tick"] + j], c)
                    if sa != sb:
                        p[2] += 1
                        diffs.append(f"start {k} ({x['kind']}, frame {x['frame']}): {part.upper()} channel {c} "
                                     f"{j} sound ticks after the start: base {sa} / new {sb}")
                        break
    for part, (n, t, d) in parts.items():
        if n:
            print(f"{part.upper()}: {n} channel parts compared from their starts, {t} sound ticks: {d} differ")
    for line in diffs[:12]:
        print("  DIFFER " + line)
    if diffs:
        bad.append(f"{len(diffs)} effects' own sound differs")
    print("fxcmp: " + ("PASS" if not bad else "FAIL: " + "; ".join(bad)))
    return 0 if not bad else 1


def starts_only(pa: Path, pb: Path) -> int:
    def starts(p: Path) -> list[str]:
        return [line.split()[2] for line in p.read_text().splitlines() if line.startswith("S")]
    x, y = starts(pa), starts(pb)
    ok = x == y and len(x) > 0
    print(f"the SCC's effect starts (sess_fxlog.tcl): {len(x)} / {len(y)}, "
          + ("the same effects in the same order" if ok else "DIFFERENT") + ": " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 3 and args[0] == "--starts":
        return starts_only(Path(args[1]), Path(args[2]))
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    for p in args:
        if not Path(p).is_file():
            print(f"fxcmp: no {p}", file=sys.stderr)
            return 2
    return compare(Log(Path(args[0])), Log(Path(args[1])))


if __name__ == "__main__":
    sys.exit(main())
