#!/usr/bin/env python3
"""Solves Brainstorm's boards and writes a joystick script that plays them on the bench.

The rules, as PUZL's frame routine $17760 has them (REA listing; tools/amigaemu.py puzl
confirms them): the cursor starts at the board's (column, row); every frame the cell under it is
marked visited (+ $10) and, when it is a red chip (0), destroyed: 100 points, the red count
$B10 - 1, the board done ($B17) at 0. A change of the joystick byte moves the cursor one cell
(the lowest of up 1, down 2, left 4, right 8) unless the edge, a black chip (1) or a visited cell
is there ($178E8); a frame without a move attempt checks the four neighbours ($178A4) and, when
none is free and the board is not done, the stage fails ($B16, D0 = 1). So a board is a simple
path from the start through every red chip, and it may end only on the last one.

A move takes two PUZL frames here (the keys at frame f are read at f's end, $17760 moves the
cursor in f + 1, and the release in f + 1 makes the next press a change): the bot presses the
next direction once the row shows the cursor on the previous target.

With --quirk1 the 4th board's path must leave free a cell next to column 0 of its last red
chip's row that a move from the cursor's own column would not reach, and the bot presses that
direction with fire in the frame after its last move: in the pass that destroys that chip,
$17760 moves from the column message_queue's D0 left (0 on the bench: $8056 & $C), not from the
cursor's (the logic report's quirk of 7.2, the plan's quirk 1). On visit 1's 4th board every
path ends at (4, 0) (its only way in is (3, 0)), so the move is down: (0, 1) free, (4, 1) a
black chip; the cursor then shows on (4, 1).

usage: puzlsolve.py [--level 1] [--ram RAM] [--boards 4] [--solve-only] [--quirk1] OUT_PREFIX
       (writes OUT_PREFIX.paths.json, OUT_PREFIX.joy (amigaemu --joy items, one a line),
       OUT_PREFIX.drive (tools/drivejoy.py's four lines) and OUT_PREFIX.jsonl (the bench's trace))
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

W, H = 11, 8
DIRS = (("u", 0, -1, 0x01), ("d", 0, 1, 0x02), ("l", -1, 0, 0x04), ("r", 1, 0, 0x08))


def parse_board(rec: bytes) -> dict:
    cells = [v & 0x0F for v in rec[6:6 + W * H]]
    return {"start": (rec[0], rec[1]), "reds": rec[2], "timer": rec[3] << 8 | rec[4], "tune": rec[5],
            "cells": cells}


def solve(board: dict, limit: int = 20_000, tries: int = 150, final=None) -> list[tuple[int, int]] | None:
    """A simple path from the start through every red chip: depth first and pruned, restarted
    with another order of the moves (a fixed sequence of seeds) when a try visits 'limit'
    nodes. final(path, visited), when given, must accept the finished path (cell indices from the
    start; visited by cell index) or the search goes on."""
    for seed in range(tries):
        p = solve_once(board, limit, seed, final)
        if p:
            return p
    return None


QUIRK1_MOVES = (("df", 0, 1), ("uf", 0, -1), ("rf", 1, 0))   # keys; the cell they test from (0, row)


def solve_quirk1(board: dict, limit: int = 20_000, tries: int = 150) -> tuple[list[tuple[int, int]] | None, str]:
    """--quirk1: a path and the keys of the move after its last one. The move goes from column 0
    of the last red chip's row (y): the cell it tests (neither a red nor a black chip) is held
    blocked while searching, so it stays free, and the same move from the chip's own column (c)
    must end elsewhere: right lands on column 1 where the cursor's would stay on c or go to
    c + 1 (c >= 2); up or down changes the row where the cursor's would be refused (c >= 1,
    (c, y -+ 1) a black chip or visited)."""
    cells = board["cells"]
    for y in range(H):
        for keys, dx, dy in QUIRK1_MOVES:
            fx, fy = dx, y + dy
            if not 0 <= fy < H or cells[fy * W + fx] in (0, 1):
                continue

            def final(path, visited, y=y, dx=dx, dy=dy):
                c, r = path[-1] % W, path[-1] // W
                if r != y:
                    return False
                if dx:
                    return c >= 2
                t = (r + dy) * W + c
                return c >= 1 and (cells[t] == 1 or visited[t])
            held = dict(board, cells=cells[:fy * W + fx] + [1] + cells[fy * W + fx + 1:])
            p = solve(held, limit, tries, final)
            if p:
                return p, keys
    return None, ""


def solve_once(board: dict, limit: int, seed: int, final=None) -> list[tuple[int, int]] | None:
    import random
    rnd = random.Random(seed)
    cells = board["cells"]
    free = [v != 1 for v in cells]
    sx, sy = board["start"]
    visited = [False] * (W * H)
    reds = {i for i, v in enumerate(cells) if v == 0}

    def nbrs(i):
        x, y = i % W, i // W
        if x > 0:
            yield i - 1
        if x < W - 1:
            yield i + 1
        if y > 0:
            yield i - W
        if y < H - 1:
            yield i + W

    def ok(cur, left):
        """Every red left reachable from cur through free unvisited cells, and at most one of
        them a dead end (it can only be the path's last cell)."""
        if not left:
            return True
        seen = {cur}
        stack = [cur]
        while stack:
            c = stack.pop()
            for n in nbrs(c):
                if n not in seen and free[n] and not visited[n]:
                    seen.add(n)
                    stack.append(n)
        if not left <= seen:
            return False
        ends = 0
        for r in left:
            deg = sum(1 for n in nbrs(r) if (free[n] and not visited[n]) or n == cur)
            if deg <= 1:
                ends += 1
                if ends > 1:
                    return False
        return True

    nodes = [0]
    path = []

    def dfs(cur, left):
        nodes[0] += 1
        if nodes[0] > limit:
            return False
        if not left:
            return final is None or final([start] + path, visited)
        cand = [n for n in nbrs(cur) if free[n] and not visited[n]]
        # reds first, then the cells with the fewest ways on (Warnsdorff)
        cand.sort(key=lambda n: (n not in left if seed % 2 == 0 else 0,
                                 sum(1 for m in nbrs(n) if free[m] and not visited[m]),
                                 rnd.random() if seed else 0))
        for n in cand:
            visited[n] = True
            path.append(n)
            nl = left - {n}
            if ok(n, nl) and dfs(n, nl):
                return True
            path.pop()
            visited[n] = False
        return False

    start = sy * W + sx
    visited[start] = True
    left = reds - {start}
    if not ok(start, left):
        return None
    if dfs(start, left):
        return [(sx, sy)] + [(c % W, c // W) for c in path]
    return None


class Bot:
    """Plays the solved paths on the bench (PuzlBench.play's bot): keys from each row."""

    def __init__(self, paths: list[list[tuple[int, int]]], quirk: str = ""):
        self.paths = paths
        self.board = None
        self.i = 0
        self.pressed = False
        self.keys: list[str] = []
        self.quirk = quirk               # the keys of the frame after the 4th board's last move
        self.last_move = False           # (instead of the release: --quirk1)

    def __call__(self, row: dict) -> str:
        k = self.step(row)
        self.keys.append(k)
        return k

    def step(self, row: dict) -> str:
        if self.pressed:                 # (a release between two presses: the next is a change)
            self.pressed = False
            if self.last_move:
                self.last_move = False
                return self.quirk
            return ""
        b = row["board2"] // 2
        if b != self.board:
            self.board, self.i = b, 0
        if row["done"] or row["fail"] or row["endc"] or not row["active"] or not 0 <= b < len(self.paths):
            return ""
        path = self.paths[b]
        pos = (row["col"], row["row"])
        while self.i + 1 < len(path) and path[self.i] != pos and path[self.i + 1] == pos:
            self.i += 1                  # (the last move landed)
        if path[self.i] != pos or self.i + 1 >= len(path):
            return ""                    # (on its way, or at the end)
        nx, ny = path[self.i + 1]
        for k, dx, dy, _ in DIRS:
            if (pos[0] + dx, pos[1] + dy) == (nx, ny):
                self.pressed = True
                self.last_move = b == 3 and self.i + 2 == len(path)
                return k
        raise RuntimeError(f"path step {pos} -> {(nx, ny)} is not a move")


def runs(keys: list[str]) -> list[tuple[int, int, str]]:
    out = []
    for n, k in enumerate(keys):
        if not k:
            continue
        if out and out[-1][2] == k and out[-1][0] + out[-1][1] == n:
            out[-1] = (out[-1][0], out[-1][1] + 1, k)
        else:
            out.append((n, 1, k))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", type=Path)
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--boards", type=int, default=4, help="boards to solve (the bot stops after them)")
    ap.add_argument("--pframes", type=int, default=3000)
    ap.add_argument("--solve-only", action="store_true")
    ap.add_argument("--quirk1", action="store_true",
                    help="the 4th board's path keeps free a cell next to column 0 of its last row; "
                         "that move, with fire, right after its last move")
    ap.add_argument("--ram", type=Path)
    ap.add_argument("--extracted", type=Path)
    a = ap.parse_args()
    import amigaemu as ae
    ram = a.ram or ae.ROOT / "build" / "ram" / "level1_full.bin"
    extracted = a.extracted or ae.ROOT / "build" / "extracted"
    bench = ae.PuzlBench(extracted, ram)
    bench.setup(a.level)
    table = 0x17448 if a.level < 2 else 0x175C0          # ($17100: $8050 < 2 or not)
    paths = []
    quirk = ""
    for b in range(4):
        board = parse_board(bytes(bench.uc.mem_read(table + 94 * b, 94)))
        if b >= a.boards:
            p = None
        elif a.quirk1 and b == 3:
            p, quirk = solve_quirk1(board)
        else:
            p = solve(board)
        print(f"board {b}: start {board['start']}, {board['reds']} red chips, timer {board['timer']:04x}: "
              + (f"path of {len(p) - 1} moves" if p else "not solved"))
        if p is None:
            break
        paths.append(p)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{a.out}.paths.json").write_text(json.dumps(paths))
    if a.solve_only:
        return 0
    bot = Bot(paths, quirk if a.quirk1 else "")
    with open(f"{a.out}.jsonl", "w") as sink:
        bench.play(a.pframes, [], False, (), 0, sink, bot=bot)
    res = bench.result
    print(f"bot: PUZL frames {bench.pframes_run}, board {bench.read_word(0xB0A) // 2}, result "
          + (f"D0 = {res} ({ae.PUZL_RESULTS.get(res)})" if res is not None else "none (still playing)"))
    items = runs(bot.keys)
    Path(f"{a.out}.joy").write_text("".join(f"{f}:{c}:{k}\n" for f, c, k in items))
    bits = {"u": 1, "d": 2, "l": 4, "r": 8, "f": 16}
    joy = bytes(sum(bits[c] for c in k) for k in bot.keys)
    Path(f"{a.out}.drive").write_text(joy.hex() + "\n\n0\n\n")
    print(f"{len(items)} joystick items over {len(bot.keys)} frames -> {a.out}.joy, {a.out}.drive")
    if a.quirk1:                         # (the pass of the last red chip: where the cursor went)
        rows = [json.loads(line) for line in Path(f"{a.out}.jsonl").read_text().splitlines()]
        j = next((i for i, r in enumerate(rows) if r.get("board2") == 8), None)
        if j is None or j < 1:
            print("quirk 1: the 4th board was not finished")
            return 1
        before, after = rows[j - 1], rows[j]
        print(f"quirk 1: pass {j - 1} destroys the last red chip at ({before['col']}, {before['row']}) "
              f"with keys {rows[j - 2]['keys'] or '-'} read; the cursor then at ({after['col']}, {after['row']})")
    return 0 if res == 0 or (res is None and len(paths) < 4) else 1


if __name__ == "__main__":
    raise SystemExit(main())
