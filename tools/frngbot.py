#!/usr/bin/env python3
"""A bot for the shooting range (FRNG) on the execution bench: it plays $1EA00 through
tools/amigaemu.py frng, aims the sight at targets and fires, and writes the joystick script it
played (.joy, and .drive in tools/drivejoy.py's format) and the bench's trace.

Each FRNG frame the bot sees the frame's target draws (draw_bob $1EDBC: x D0, y D1, size D4, the
graphics A2, the minterm immediate $1EEC6, the caller; for the pop-up targets' visible draw, caller
$1F5FC, the descriptor A0) and picks a target by --mode:
  armed:  only shots that count as correct targets: the pop-ups whose descriptor's threshold
          ($14,A0) leaves the aimed column below it, the rising targets ($1F14E: always correct)
          and the moving ones ($1F32A) whose table threshold is at least the column;
  dummy:  only shots that count as dummy targets (the same rules the other way);
  mixed:  armed first, a dummy every --every-dummy shots;
  quirk4: armed, but with one idle frame after a shot instead of four and the target just shot
          left out for 8 frames, so that a second armed target is often counted within the 10
          passes of the first one's score delay ($BBC): quirk T4, the first one's + 25 lost.
The aim point (c, r) of a draw at (x, y) must hit a set bit of the target's mask plane (A2), and
of the scenery's priority plane ($3E062 + $8660) clear when the minterm is $B50, as $1EDBC's test
reads them: column $B9A + 17 - (x & ~15), row $B9E - y. The sight moves 4 px a frame on each axis
(keys at frame f move it in frame f + 1); fire is pressed once (one frame) when the sight will be
on the point and the target has held still for 2 frames; the hit is tested 2 frames later.

Two modes do not aim (the logic report's scenarios.py, its bench runs bot_edge and fuzz1; the same
seed gives the same keys, frame by frame):
  edge:   (--seed 4) the first target the state names (a slot's pop-up, else the pending draw of a
          rising or moving target), a random column of the row just below it (row offset = the
          BOB's height: quirk T1, the hit test then reads past its blit's output), the sight
          moved there 4 px a frame, fire tapped near it;
  fuzz:   (--seed 21) random key sets (none, a direction or a diagonal) held 1-29 frames, fire
          added in 35 % of the frames.

usage: frngbot.py OUT [--mode armed|dummy|mixed|quirk4|edge|fuzz] [--every-dummy N] [--shots N]
                  [--seed N] [--level 1] [--frames 3000]
                  [--ram build/ram/level1_full.bin] [--extracted build/extracted]
       (writes OUT.joy: F:C:KEYS lines; OUT.drive; OUT.jsonl: the trace; OUT.log: the shots, or
       for edge and fuzz the frames with fire pressed)
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import amigaemu as ae  # noqa: E402
from unicorn.m68k_const import UC_M68K_REG_A7  # noqa: E402

ROOT = HERE.parent
TYPES = 0x1EF88                 # 8-byte records by target type: the handler's offset first
T4, T1 = 0x1F14E, 0x1F32A       # the rising target's and the moving target's handlers
T1_THR = 0x1F288                # the moving targets' thresholds by track ($1F246 / 2)
PRIO = 0x3E062 + 0x8660         # the scenery's priority plane (the background's 6th)


def s16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def ident(d: dict) -> tuple:
    """A target draw's identity: a pop-up by its descriptor, the rising or moving target by its kind
    (one runs at a time)."""
    return d["kind"], d.get("desc")


def keys_order(keys: str) -> str:
    return "".join(k for k in "udlrf" if k in keys)       # (the drive file's order)


class Bot:
    def __init__(self, bench: ae.FrngBench, mode: str, every_dummy: int, max_shots: int):
        self.b = bench
        self.mode = mode
        self.every_dummy = every_dummy
        self.max_shots = max_shots
        self.quirk4 = mode == "quirk4"
        self.left_out: tuple | None = None   # (quirk4) the target just shot, and the frame it is free again
        self.draws: list[dict] = []          # this frame's
        self.prev: list[dict] = []           # last frame's
        self.prev2: list[dict] = []
        self.last_keys = ""
        self.shots: list[dict] = []
        self.wait = 0                        # frames to wait after a shot
        self.keys_log: list[str] = []
        self.pts_cache: dict = {}

    # ---- what $1EDBC tests
    def hit_points(self, d: dict) -> list[tuple[int, int]]:
        """The (c, r) of the draw where $1EDBC's test finds a set mask bit: the target's mask plane
        (the first plane at A2, (words - 1) x 16 px wide), less the scenery's priority plane where the
        minterm is $B50 (A & !C)."""
        key = (d["gfx"], d["x"], d["y"], d["minterm"], d["words"], d["h"])
        if key in self.pts_cache:
            return self.pts_cache[key]
        w, h = d["words"], d["h"]
        row = (w - 1) * 2
        mask = bytes(self.b.uc.mem_read(d["gfx"], row * h))
        pts = []
        for r in range(h):
            y = d["y"] + r
            prio = bytes(self.b.uc.mem_read(PRIO + y * 40, 40)) if d["minterm"] == 0xB50 and 0 <= y < 172 else None
            for c in range((w - 1) * 16):
                if not mask[r * row + c // 8] >> (7 - c % 8) & 1:
                    continue
                if prio is not None:
                    bx = d["x"] - 128 + c
                    if 0 <= bx < 320 and prio[bx // 8] >> (7 - bx % 8) & 1:
                        continue
                pts.append((c, r))
        self.pts_cache[key] = pts
        return pts

    def counts_as(self, d: dict, c: int) -> str | None:
        col = c + (d["x"] & 15)
        if d["kind"] == "popup":
            return "dummy" if col >= d["thr"] else "correct"
        if d["kind"] == "rising":
            return "correct"
        if d["kind"] == "moving":
            return "dummy" if d["thr"] < col else "correct"
        return None

    def on_draw(self, uc, address, size, user_data):
        ret = self.b.read_long(uc.reg_read(UC_M68K_REG_A7))
        d4 = uc.reg_read(ae.d_reg(4)) & 0xFFFF
        d = {"x": s16(uc.reg_read(ae.d_reg(0))), "y": s16(uc.reg_read(ae.d_reg(1))), "words": d4 & 0x3F,
             "h": d4 >> 6, "gfx": uc.reg_read(ae.a_reg(2)) & 0xFFFFFF, "minterm": self.b.read_word(0x1EEC6),
             "caller": ret, "kind": None}
        if ret == 0x1F5FC:                   # a pop-up target ($1F50C): A0 its descriptor
            a0 = uc.reg_read(ae.a_reg(0)) & 0xFFFFFF
            d |= {"kind": "popup", "desc": a0, "thr": s16(self.b.read_word(a0 + 0x14))}
        elif ret == 0x1F42A:                 # the pending draw of a rising or a moving target ($1F3F6)
            for slot in (0, 1):
                t = self.b.read_var(0xB36 + 4 * slot, 1, False)
                if t:
                    rec = TYPES + 8 * t
                    h = rec + s16(self.b.read_word(rec))
                    if h == T4:
                        d["kind"] = "rising"
                    elif h == T1:
                        d["kind"] = "moving"
                        d["thr"] = s16(self.b.read_word(T1_THR + self.b.read_word(0x1F246)))
        if d["kind"] and d["minterm"] != 0x100:
            self.draws.append(d)

    def frame_start(self):
        self.prev2, self.prev, self.draws = self.prev, self.draws, []

    def predicted(self, d: dict) -> dict | None:
        """The draw d (last frame's) where it will be when the hit is tested: 3 frames on, at the
        speed it moved from the frame before (None when that frame has no such target)."""
        best = None
        for e in self.prev2:
            if e["kind"] == d["kind"] and e.get("desc") == d.get("desc") and e["words"] == d["words"]:
                v = (d["x"] - e["x"], d["y"] - e["y"])
                if abs(v[0]) <= 8 and abs(v[1]) <= 8 and (best is None or abs(v[0]) + abs(v[1]) < abs(best[0]) + abs(best[1])):
                    best = v
        if best is None:
            return None
        return d | {"x": d["x"] + 3 * best[0], "y": d["y"] + 3 * best[1]}

    def want(self) -> str:
        if self.mode == "mixed":
            n = len(self.shots) + 1
            return "dummy" if self.every_dummy and n % self.every_dummy == 0 else "correct"
        return "dummy" if self.mode == "dummy" else "correct"

    def choose(self, row: dict) -> str:
        """The keys for this frame from the row at its start."""
        dx = (4 if "r" in self.last_keys else -4 if "l" in self.last_keys else 0)
        dy = (4 if "d" in self.last_keys else -4 if "u" in self.last_keys else 0)
        px = max(0x7C, min(0x198, row["cx"] + dx))    # where this frame's move leaves the sight
        py = max(0x10, min(0x9E, row["cy"] + dy))
        keys = ""
        if self.wait > 0:
            self.wait -= 1
        elif row["ammo"] and row["endc"] == 0 and sum(s["want"] != "none" for s in self.shots) >= self.max_shots:
            # the aimed shots done: the rest of the ammo fired where no target will be (a miss)
            busy = False
            for d0 in self.prev:
                d = self.predicted(d0) or d0
                if any(d["x"] + c - 17 == px and d["y"] + r == py for c, r in self.hit_points(d)):
                    busy = True
            if not busy:
                keys = "f"
                self.shots.append({"frame": row["frame"], "at": [px, py], "want": "none",
                                   "correct": row["correct"], "dummy": row["dummy"]})
                self.wait = 4
        elif row["ammo"] and row["endc"] == 0:
            want = self.want()
            best = None
            for d0 in self.prev:                 # (the targets drawn last frame, 3 frames on)
                d = self.predicted(d0)
                if d is None:
                    continue
                if self.left_out and row["frame"] < self.left_out[1] and ident(d) == self.left_out[0]:
                    continue
                for c, r in self.hit_points(d):
                    ax, ay = d["x"] + c - 17, d["y"] + r
                    if ax % 4 != px % 4 or ay % 4 != py % 4 or not (0x7C <= ax <= 0x198 and 0x10 <= ay <= 0x9E):
                        continue
                    if self.counts_as(d, c) != want:
                        continue
                    dist = max(abs(ax - px), abs(ay - py))
                    if best is None or dist < best[0]:
                        best = (dist, ax, ay, d, c, r)
            if best is not None:
                dist, ax, ay, d, c, r = best
                if ax > px:
                    keys += "r"
                elif ax < px:
                    keys += "l"
                if ay > py:
                    keys += "d"
                elif ay < py:
                    keys += "u"
                if not keys:
                    keys = "f"
                    self.shots.append({"frame": row["frame"], "at": [ax, ay], "target": {k: d[k] for k in
                                       ("x", "y", "gfx", "kind", "caller") if k in d} | {"c": c, "r": r},
                                       "want": want, "correct": row["correct"], "dummy": row["dummy"]})
                    self.wait = 4
                    if self.quirk4:
                        self.wait = 1            # (one frame with fire up: the next press shoots at once)
                        self.left_out = (ident(d), row["frame"] + 8)
        self.last_keys = keys.replace("f", "")
        return keys_order(keys)


def _w(m, a: int) -> int:
    return int.from_bytes(m(a, 2), "big")


def _sw(m, a: int) -> int:
    return int.from_bytes(m(a, 2), "big", signed=True)


def targets(m) -> list[tuple]:
    """The targets the state names at a frame's start, in BOB coordinates (x as given to $1EDBC):
    (x, y, words - 1, rows, kind, threshold) of each slot's pop-up, then of the pending draw of a
    rising or moving target ($BA8 its BLTSIZE). The logic report's scenarios.py targets()."""
    out = []
    for k in (0, 1):
        a3 = 0xB2E + 4 * k
        s = m(a3 + 8, 1)[0]
        if not s or not int.from_bytes(m(a3, 4), "big"):
            continue
        e = TYPES + 8 * s
        h = (e + _sw(m, e)) & 0xFFFFFF
        if h in (T4, T1):
            continue
        d = h + 2 + _sw(m, h + 2)                  # (the stub: lea desc,A0)
        x, y = _w(m, d + 2), (_w(m, d + 4) + _w(m, a3 - 0x1E)) & 0xFFFF
        if m(d + 11, 1)[0]:
            x, y = y, x
        bs = _w(m, d + 12)
        out.append((x, y, (bs & 63) - 1, bs >> 6, "popup", _w(m, d + 20)))
    if _w(m, 0xBA8):
        bs = _w(m, 0xBA8)
        out.append((_w(m, 0xBAE), _w(m, 0xBB0), (bs & 63) - 1, bs >> 6, "big", 99))
    return out


class EdgeBot:
    """--mode edge: the logic report's bot_edge (scenarios.py bot("edge", seed)), call for call:
    the same random numbers in the same order, so the same seed gives the same keys."""

    def __init__(self, bench: ae.FrngBench, seed: int):
        self.m = bench.uc.mem_read
        self.rnd = random.Random(seed)
        self.tap = 0
        self.shots: list[dict] = []

    def frame_start(self):
        pass

    def choose(self, row: dict) -> str:
        m, rnd = self.m, self.rnd
        cx, cy = _w(m, 0xB9A) + 17, _w(m, 0xB9E)       # the hit point in BOB coordinates
        ts = targets(m)
        k = ""
        goal = None
        if ts:
            x, y, w, h, kind, thr = ts[0]
            gy = y + h                                   # the row just below the BOB
            gx = (x & 0xFFF0) + rnd.randrange(0, 16 * w)
            goal = (gx, gy, kind)
            if cx < gx - 2:
                k += "r"
            elif cx > gx + 2:
                k += "l"
            if cy < gy - 2:
                k += "d"
            elif cy > gy + 2:
                k += "u"
            near = abs(cx - gx) <= 4 and abs(cy - gy) <= 4
        else:
            near = False
            if rnd.random() < 0.3:
                k += rnd.choice("udlr")
        self.tap ^= 1
        if near and self.tap and rnd.random() < 0.6:
            k += "f"
            self.shots.append({"frame": row["frame"], "sight": [cx, cy], "goal": goal, "ammo": row["ammo"]})
        return keys_order(k)


class FuzzBot:
    """--mode fuzz: the logic report's fuzz (scenarios.py fuzz(seed)), call for call."""

    def __init__(self, seed: int):
        self.rnd = random.Random(seed)
        self.k = ""
        self.left = 0
        self.shots: list[dict] = []

    def frame_start(self):
        pass

    def choose(self, row: dict) -> str:
        rnd = self.rnd
        if self.left <= 0:
            self.k = rnd.choice(["", "u", "d", "l", "r", "ul", "ur", "dl", "dr"])
            self.left = rnd.randrange(1, 30)
        self.left -= 1
        k = self.k
        if rnd.random() < 0.35:
            k += "f"
            self.shots.append({"frame": row["frame"], "sight": [row["cx"], row["cy"]], "ammo": row["ammo"]})
        return keys_order(k)


def counted(trace: Path) -> tuple[list[int], int]:
    """The passes where the correct count rose, from the bot's trace, and the final score (BCD)."""
    passes, last, score = [], 0, 0
    for line in trace.read_text().splitlines():
        r = json.loads(line)
        if "frame" not in r:
            continue
        if r["correct"] > last:
            passes.append(r["frame"])
        last, score = r["correct"], r["score"]
    return passes, score


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", type=Path)
    ap.add_argument("--mode", choices=("armed", "dummy", "mixed", "quirk4", "edge", "fuzz"), default="armed")
    ap.add_argument("--every-dummy", type=int, default=4)
    ap.add_argument("--shots", type=int, default=99, help="aimed shots; the rest of the ammo is fired to miss")
    ap.add_argument("--seed", type=int, help="edge, fuzz: the random keys' seed (4 and 21: bot_edge and fuzz1)")
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--frames", type=int, default=3000)
    ap.add_argument("--ram", type=Path, default=ROOT / "build" / "ram" / "level1_full.bin")
    ap.add_argument("--extracted", type=Path, default=ROOT / "build" / "extracted")
    a = ap.parse_args()
    b = ae.FrngBench(a.extracted, a.ram)
    b.setup(a.level)
    if a.mode == "edge":
        bot = EdgeBot(b, 4 if a.seed is None else a.seed)
    elif a.mode == "fuzz":
        bot = FuzzBot(21 if a.seed is None else a.seed)
    else:
        bot = Bot(b, a.mode, a.every_dummy, a.shots)
        b.uc.hook_add(ae.UC_HOOK_CODE, bot.on_draw, None, 0x1EDBC, 0x1EDBD)
    keys_by_frame: list[str] = []

    def play_bot(row: dict) -> str:
        bot.frame_start()
        k = bot.choose(row)
        keys_by_frame.append(k)
        return k

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with Path(f"{a.out}.jsonl").open("w") as sink:
        b.play(a.frames, [], False, (), 0, sink, bot=play_bot)
    # the script, as runs of equal keys (F:C:KEYS), and the drive file
    items, n = [], 0
    while n < len(keys_by_frame):
        k = keys_by_frame[n]
        m = n
        while m + 1 < len(keys_by_frame) and keys_by_frame[m + 1] == k:
            m += 1
        if k:
            items.append(f"{n}:{m - n + 1}:{k}")
        n = m + 1
    Path(f"{a.out}.joy").write_text("\n".join(items) + "\n")
    bits = {"u": 1, "d": 2, "l": 4, "r": 8, "f": 16}
    joy = bytes(sum(bits[c] for c in k) for k in keys_by_frame).rstrip(b"\0")
    Path(f"{a.out}.drive").write_text(joy.hex() + "\n\n0\n\n")
    with Path(f"{a.out}.log").open("w") as f:
        for s in bot.shots:
            f.write(json.dumps(s) + "\n")
    what = "frames with fire" if a.mode in ("edge", "fuzz") else "shots"
    print(f"{a.out}: {len(bot.shots)} {what}, FRNG frames {b.fframes_run}, returned {b.returned}, {b.rating}")
    passes, score = counted(Path(f"{a.out}.jsonl"))
    t4 = sum(q - p <= 10 for p, q in zip(passes, passes[1:]))
    print(f"correct targets counted at {len(passes)} passes; T4 (counted within 10 passes of the one "
          f"before): {t4}; score {score:x}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
