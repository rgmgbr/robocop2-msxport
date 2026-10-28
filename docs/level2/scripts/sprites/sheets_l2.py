#!/usr/bin/env python3
"""Contact sheets of level 2's new characters: the Amiga frame (level 2's palette, $10036) beside the
MSX look (hardware sprites: the converter's full OR preview; play field: the atlas pixels), both
sides, 3x. MSX colours through the in-game colour grade (tools/msxbright.py BRIGHT), as the game
shows them. Transparent pixels: dark grey.
usage: sheets_l2.py RAM MAIN_8000 PREFIX OUTDIR"""
from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

BRIGHT = (0, 1, 3, 4, 5, 6, 7, 7)
S = 3
ram = Path(sys.argv[1]).read_bytes()
main = Path(sys.argv[2]).read_bytes()
pre = Path(sys.argv[3])
out = Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
js = json.loads(pre.with_suffix(".json").read_text())
prev = np.load(pre.parent / "previews.npz")
raw = pre.with_suffix(".pal").read_bytes()
msx = [((raw[2 * k] >> 4) & 7, raw[2 * k + 1] & 7, raw[2 * k] & 7) for k in range(16)]
msx_rgb = [tuple(round(BRIGHT[c] * 255 / 7) for c in col) for col in msx]
amiga12 = [struct.unpack_from(">H", main, 0x10036 - 0x8000 + 2 * i)[0] for i in range(15)]
amiga_rgb = [(0, 0, 0)] + [(((c >> 8) & 15) * 17, ((c >> 4) & 15) * 17, (c & 15) * 17) for c in amiga12]
BG = (48, 48, 52)
vram = (pre.parent / (pre.name + "_field_vram.bin")).read_bytes()
inc = (pre.parent / (pre.name + "_field.inc")).read_text()
ftab = [tuple(int(v) for v in m.groups()) + (int(m2, 16),) for m, m2 in
        [(re.match(r"\s*db (\d+), (\d+), (\d+), (\d+), (\d+), (\d+)", line), line.split()[-1])
         for line in inc.splitlines() if re.match(r"\s*db \d+, \d+, \d+, \d+, \d+, \d+\s+;", line)]]
fpos = {a: (x, y, w, h) for x, y, w, h, _dx, _dy, a in ftab}
bobs = {(b["addr"], b["w"], b["h"]): i for i, b in enumerate(js["bobs"])}
font = ImageFont.load_default()


def amiga_img(addr, w, h):
    wb, ps = w // 8, (w // 8) * h
    im = Image.new("RGB", (w, h), BG)
    px = im.load()
    for y in range(h):
        for x in range(w):
            byte, bit = y * wb + (x >> 3), 0x80 >> (x & 7)
            if ram[addr + byte] & bit:
                v = sum(1 << p for p in range(4) if ram[addr + ps * (p + 1) + byte] & bit)
                px[x, y] = amiga_rgb[v]
    return im


def msx_img(arr):
    h, w = arr.shape
    im = Image.new("RGB", (w, h), BG)
    px = im.load()
    for y in range(h):
        for x in range(w):
            if arr[y, x] > 0:
                px[x, y] = msx_rgb[arr[y, x]]
    return im


def field_img(addr):
    x0, y0, w, h = fpos[addr]
    arr = np.zeros((h, w), int)
    for y in range(h):
        for x in range(w):
            b = vram[(y0 + y) * 128 + (x0 + x) // 2]
            arr[y, x] = b >> 4 if (x0 + x) % 2 == 0 else b & 15
    return msx_img(arr)


def sprite_img(addr, w, h):
    i = bobs[(addr, w, h)]
    return msx_img(prev[f"arr_{3 * i + 1}"])


def sheet(name, title, frames, kind):
    """frames: list of (label, addr, w, h); kind 'sprite' or 'field'."""
    cells = []
    for label, a, w, h in frames:
        am = amiga_img(a, w, h)
        ms_ = sprite_img(a, w, h) if kind == "sprite" else field_img(a)
        cells.append((label, am, ms_))
    cw = max(c[1].width + c[2].width for c in cells) * S + 3 * 8
    ch = max(max(c[1].height, c[2].height) for c in cells) * S + 24
    cols = max(1, min(len(cells), 1200 // cw))
    rows = -(-len(cells) // cols)
    img = Image.new("RGB", (cols * cw + 8, rows * ch + 40), (24, 24, 28))
    d = ImageDraw.Draw(img)
    d.text((8, 8), title + "  (each cell: Amiga | MSX, 3x)", fill=(230, 230, 230), font=font)
    for n, (label, am, ms_) in enumerate(cells):
        ox, oy = 8 + (n % cols) * cw, 32 + (n // cols) * ch
        img.paste(am.resize((am.width * S, am.height * S), Image.NEAREST), (ox, oy + 16))
        img.paste(ms_.resize((ms_.width * S, ms_.height * S), Image.NEAREST), (ox + am.width * S + 8, oy + 16))
        d.text((ox, oy), label, fill=(200, 200, 200), font=font)
    img.save(out / f"{name}.png")
    return img.size


uw = lambda a: struct.unpack_from(">H", ram, a)[0]   # noqa: E731
done = []
if (0x78000, 48, 44) in bobs:                                      # type 1 as joint compositions
    done.append(sheet("type1_joint", "Type 1 (walking gunman, $C736): legs + torso as one composition, left then right",
                      [(f"{'L' if k < 8 else 'R'} step {k & 7}", 0x78000 + 0x600 * k, 48, 44) for k in range(16)], "sprite"))
else:
    done.append(sheet("type1_parts", "Type 1 (walking gunman, $C736): legs ($3E810, 32x23) and torso ($404D0, 32x21)",
                      [(f"legs {'L' if k < 8 else 'R'}{k & 7}", 0x3E810 + uw(0xC7E0 + 2 * k), 32, 23) for k in range(16)]
                      + [("torso L", 0x404D0, 32, 21), ("torso R", 0x40674, 32, 21)], "sprite"))
done.append(sheet("type2_field", "Type 2 (armed suspect to arrest, $C868): play field",
                  [("first 70 ticks", 0x3D280, 48, 56), ("after", 0x3D910, 48, 56)], "field"))
done.append(sheet("type2_flash", "Type 2: its sprite version (shown only as the white flash's silhouette)",
                  [("first 70 ticks", 0x3D280, 48, 56), ("after", 0x3D910, 48, 56)], "sprite"))
done.append(sheet("type5", "Type 5 (falling debris, $D0E2): sprites",
                  [(f"{a:X}", a, 16 if a in (0x3BFC0, 0x3C060, 0x3C100, 0x3C1A0, 0x3C240) else 32, 16) for a in
                   (0x3BFC0, 0x3C060, 0x3C100, 0x3C1A0, 0x3C2E0, 0x3C240, 0x3C560, 0x3C6A0, 0x3C7E0)], "sprite"))
done.append(sheet("type6", "Type 6 (jumper, $D1E2): sprites, one side only (it moves right)",
                  [(f"{a:X}", a, 32, 24) for a in (0x3C920, 0x3CB00, 0x3CCE0, 0x3CEC0, 0x3D0A0)], "sprite"))
done.append(sheet("type14_field", "Type 14 (gunner that stays put, $CE0A): play field, left and right",
                  [("L", 0x3DFA0, 48, 36), ("R", 0x3E3D8, 48, 36)], "field"))
done.append(sheet("type16_field", "Type 16 (walking bazooka man, $CD7A): body in the play field (legs: walker1 sprites)",
                  [("L stand", 0x40818, 48, 24), ("L aim", 0x40DB8, 48, 24), ("R stand", 0x40AE8, 48, 24),
                   ("R aim", 0x41088, 48, 24)], "field"))
done.append(sheet("type16_legs", "Type 16's legs: walker1 ($C948, SPERMA, shared with level 1), sprites",
                  [(f"{'L' if i < 8 else 'R'}{i & 7}", 0x4BD06 + struct.unpack_from('>h', ram, 0xC9B4 + 2 * i)[0],
                    ((uw(0xC9D4 + 2 * i) & 63) - 1) * 16, uw(0xC9D4 + 2 * i) >> 6) for i in range(16)], "sprite"))
done.append(sheet("type49", "Type 49 (homing drone, $E6C0 / $E728): 16 directions, sprites",
                  [(f"dir {k}", 0x41358 + uw(0xE7B2 + 2 * k), 16, 16) for k in range(16)], "sprite"))
done.append(sheet("trolley_field", "Trolley ($8F02, SPERMA $4B95A): play field (RoboCop hangs from it)",
                  [("trolley", 0x4B95A, 32, 47)], "field"))
done.append(sheet("type4_new", "Type 4's aims level 1 never drew ($CFB0: $57192 + $D066[aim]) and flash 4 ($6C8A0)",
                  [("aim 4", 0x57912, 32, 32), ("aim 7", 0x58092, 32, 32), ("aim 0", 0x58312, 32, 38),
                   ("flash 4", 0x6C8A0, 16, 16)], "sprite"))
print(done)
