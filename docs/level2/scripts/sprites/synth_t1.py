#!/usr/bin/env python3
"""Type 1 as joint compositions (measurement): each of its 16 leg steps with its torso, placed as
obj01_update ($C736, REA) draws them -- legs at (x, y + 21) through $AC44, then the torso over them at
(x - 2, y + $C800[step]) facing left, (x + 2, ...) facing right, through $AC56 -- written as BOB frames
(mask + 4 planes, 48 x 44) into a copy of the RAM image at $78000 + n * $600, with a catalogue whose
obj01 legs/torso refs are replaced by them.
usage: synth_t1.py RAM_IN CATALOG_IN RAM_OUT CATALOG_OUT"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

ram = bytearray(Path(sys.argv[1]).read_bytes())
cat = json.loads(Path(sys.argv[2]).read_text())
uw = lambda a: struct.unpack_from(">H", ram, a)[0]   # noqa: E731


def read(addr, w, h):
    wb, ps = w // 8, (w // 8) * h
    return [[(sum(1 << p for p in range(4) if ram[addr + ps * (p + 1) + y * wb + (x >> 3)] & (0x80 >> (x & 7)))
              if ram[addr + y * wb + (x >> 3)] & (0x80 >> (x & 7)) else -1) for x in range(w)] for y in range(h)]


def write(addr, img, w, h):
    wb, ps = w // 8, (w // 8) * h
    for i in range(5 * ps):
        ram[addr + i] = 0
    for y in range(h):
        for x in range(w):
            c = img[y][x]
            if c < 0:
                continue
            byte, bit = y * wb + (x >> 3), 0x80 >> (x & 7)
            ram[addr + byte] |= bit
            for p in range(4):
                if c >> p & 1:
                    ram[addr + ps * (p + 1) + byte] |= bit


W, H = 48, 44
frames = []
for k in range(16):
    left = k < 8
    legs = read(0x3E810 + uw(0xC7E0 + 2 * k), 32, 23)
    torso = read(0x404D0 if left else 0x40674, 32, 21)
    bob = uw(0xC800 + 2 * (k & 7))
    img = [[-1] * W for _ in range(H)]
    lx, tx = (2, 0) if left else (0, 2)          # (origin: the leftmost of the two parts)
    for y in range(23):
        for x in range(32):
            if legs[y][x] >= 0:
                img[21 + y][lx + x] = legs[y][x]
    for y in range(21):
        for x in range(32):
            if torso[y][x] >= 0:
                img[bob + y][tx + x] = torso[y][x]
    a = 0x78000 + k * 0x600
    write(a, img, W, H)
    frames.append(a)
refs = [r for r in cat["refs"] if not (r["proc_name"] == "obj01_update" and (r["width"], r["height"]) in ((32, 23), (32, 21)))]
d4 = (W // 16 + 1) | H << 6
refs.append({"proc": 0, "proc_name": "obj01_joint", "site": 0, "base": frames[0], "adjust": [], "table": None,
             "ltable": None, "bltsize": d4, "width": W, "height": H, "frames": frames, "level": "level2",
             "evidence": "joint legs + torso (synth_t1.py)"})
Path(sys.argv[3]).write_bytes(bytes(ram))
Path(sys.argv[4]).write_text(json.dumps({"draw_targets": [], "refs": refs}))
print(f"{len(frames)} joint frames {W} x {H}; {len(refs)} refs")
