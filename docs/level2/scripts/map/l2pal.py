#!/usr/bin/env python3
"""Level 2's palette for the MSX: the options measured on the whole level (map + the tiles the
writers put in it), and previews (Amiga against MSX, graded).

Options (16 MSX colours, RoboCop's at the OR-closed indices 1..7):
  A  level 1's joint palette (build/msx/robocop.pal) as it is, every level-2 colour to its nearest
     entry (the earlier level2_joint_l1pal experiment);
  B  level 2's own joint palette from tools/msxsprites.py run on level 2's colours (the earlier
     level2_joint_own experiment: its .pal and the remap of its run, l2_B3);
  C  level 1's index layout with level 2's values: every Amiga colour keeps level 1's index
     (level 1's remap), and the entries whose Amiga colour changed between the levels take level
     2's value (index 9 <- c15 BBB, 11 <- c5 03A, 13 <- c6 025); 0..7 unchanged, so RoboCop's
     sprite data (indices 1..7) and every shared frame stay byte-identical;
  D  (reference only) 0..7 fixed, 8..15 refitted freely to level 2's background (the best a free
     fit could do; it would change the meaning of 8..15 for the frames level 1 already holds).
usage: l2pal.py REPO OUTDIR   (run with the project's venv python, -I -B)
"""
import itertools
import struct
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
REPO = Path(sys.argv[1])
OUT = Path(sys.argv[2])
sys.path.insert(0, str(REPO / "tools"))
from planar import write_png  # noqa: E402
from msxbright import BRIGHT  # noqa: E402

COLS, ROWS = 160, 50
S = Path("/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space")


def lab(rgb):
    """sRGB 0..1 (..., 3) -> CIELAB (D65)."""
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def pal_file(p):
    d = Path(p).read_bytes()
    return [(d[2 * i] >> 4 & 7, d[2 * i + 1] & 7, d[2 * i] & 7) for i in range(16)]


def amiga12(c):
    return ((c >> 8) & 15, (c >> 4) & 15, c & 15)


def to3(c12):
    return tuple(round(v * 7 / 15) for v in c12)


def main():
    img = (REPO / "build/ram/level2_full.bin").read_bytes()
    datal = (REPO / "build/extracted/files/DATAL2_18.bin").read_bytes()
    l1 = [0] + list(struct.unpack_from(">15H", img, 0xFFF6))
    l2 = [0] + list(struct.unpack_from(">15H", img, 0x10036))
    sp1 = list(struct.unpack_from(">16H", img, 0xFFF6 + 30))
    sp2 = list(struct.unpack_from(">16H", img, 0x10036 + 30))
    print("Amiga background COLOR01-15, level 1 / level 2 (REA read_bytes $FFF6, $10036):")
    for i in range(1, 16):
        print(f"  c{i:2d}: {l1[i]:03X} / {l2[i]:03X} -> 3-bit {''.join(map(str, to3(amiga12(l1[i]))))} / "
              f"{''.join(map(str, to3(amiga12(l2[i]))))}{'   changed' if l1[i] != l2[i] else ''}")
    print("sprite colours COLOR16-31 identical in both levels:", sp1 == sp2)
    # pixel counts per Amiga colour: the map's cells plus the writers' tiles at their cells
    words = [struct.unpack_from(">H", datal, 0x10000 + 2 * i)[0] for i in range(ROWS * COLS)]

    def tile_ix(off):
        t = np.zeros((16, 16), np.uint8)
        for y in range(16):
            for p in range(4):
                b = datal[off + (y * 4 + p) * 2:off + (y * 4 + p) * 2 + 2]
                v = (b[0] << 8) | b[1]
                for x in range(16):
                    if v & (0x8000 >> x):
                        t[y, x] |= 1 << p
        return t
    tiles = {off: tile_ix(off) for off in range(0, 0x10000, 0x80)}
    count = np.zeros(16)
    for wd in words:
        count += np.bincount(tiles[wd & ~0x7F].ravel(), minlength=16)
    print("level 2 pixel share per Amiga colour (the map): " +
          " ".join(f"c{i}:{100 * count[i] / count.sum():.2f}%" for i in range(16)))
    am_rgb = np.array([[v * 17 / 255 for v in amiga12(c)] for c in l2])
    am_lab = lab(am_rgb)
    # options
    p1 = pal_file(REPO / "build/msx/robocop.pal")
    r1 = list((REPO / "build/msx/robocop.remap").read_bytes())
    pB = pal_file(S / "level2/conv/level2_joint_own.pal")
    rB = list((S / "level2/l2_B3/robocop.remap").read_bytes())

    def nearest_remap(pal):
        P = lab(np.array(pal) / 7)
        return [0] + [int(((P[1:] - am_lab[c]) ** 2).sum(-1).argmin()) + 1 for c in range(1, 16)]
    pA, rA = p1, nearest_remap(p1)
    pC = list(p1)
    for c in (5, 6, 15):                      # the colours level 2 changed that level 1 gives an index of their own
        pC[r1[c]] = to3(amiga12(l2[c]))
    # (c10 B00 -> A00 is 500 either way; c11 800 -> 700 shares index 14 with c10: kept there, C11 tries its nearest)
    rC = list(r1)
    # c11 (level 1: 800 -> idx 14 with c10) may sit better elsewhere now: its nearest in pC
    PC = lab(np.array(pC) / 7)
    best11 = int(((PC[8:] - am_lab[11]) ** 2).sum(-1).argmin()) + 8
    # (only among 8..15: RoboCop's 1..7 serve the background where level 1's remap put it)
    # D: 0..7 fixed, 8..15 chosen from the level's own 3-bit colours (exhaustive)
    fixed = p1[:8]
    cand = sorted({to3(amiga12(l2[c])) for c in range(1, 16)} - set(fixed))

    def err(pal, remap=None):
        P = lab(np.array(pal) / 7)
        if remap is None:
            remap = [0] + [int(((P[1:] - am_lab[c]) ** 2).sum(-1).argmin()) + 1 for c in range(1, 16)]
        e = np.sqrt(((P[remap] - am_lab) ** 2).sum(-1))
        return (e * count).sum() / count.sum(), remap, e
    bestD = None
    for comb in itertools.combinations(cand, min(8, len(cand))):
        pal = fixed + list(comb) + [(0, 0, 0)] * (8 - len(comb))
        m, rem, _ = err(pal)
        if bestD is None or m < bestD[0]:
            bestD = (m, pal, rem)
    opts = {"A": (pA, rA), "B": (pB, rB), "C": (pC, rC), "D": (bestD[1], bestD[2])}
    rC11 = list(rC)
    rC11[11] = best11
    opts["C11"] = (pC, rC11)
    print("\noption: palette | remap | mean dE76 over the level's pixels | per-colour dE")
    res = {}
    for k, (pal, rem) in opts.items():
        m, _, e = err(pal, rem)
        res[k] = m
        print(f"  {k}: {' '.join(''.join(map(str, c)) for c in pal)} | {' '.join(map(str, rem))} | {m:.2f} | "
              + " ".join(f"c{c}:{e[c]:.1f}" for c in range(1, 16) if count[c] > 0))
        print(f"     RoboCop 1..7 as level 1's: {pal[1:8] == p1[1:8]}; entries 2,3,7 free of background: "
              f"{not {2, 3, 7} & set(rem)}")
    # level 1 for reference: its own colours under its palette
    am1 = lab(np.array([[v * 17 / 255 for v in amiga12(c)] for c in l1]))
    P1 = lab(np.array(p1) / 7)
    e1 = np.sqrt(((P1[r1] - am1) ** 2).sum(-1))
    print(f"  level 1 under its own palette (per-colour dE): " + " ".join(f"c{c}:{e1[c]:.1f}" for c in range(1, 16)))
    # distinct tiles after each remap
    for k, (pal, rem) in opts.items():
        lut = np.array(rem, np.uint8)
        packed = {lut[t].tobytes() for t in tiles.values()}
        used = {lut[tiles[o]].tobytes() for o in {wd & ~0x7F for wd in words} | set(VAT_OFFS(img))}
        print(f"  {k}: {len(packed)} distinct tiles of the 512 offsets; map + vats use {len(used)}")
    # previews
    OUT.mkdir(parents=True, exist_ok=True)
    W, H = COLS * 16, ROWS * 16

    def render(rgb_of_index, remap):
        im = np.zeros((H, W, 3), np.uint8)
        lut = np.array(remap, np.uint8)
        for r in range(ROWS):
            for c in range(COLS):
                t = lut[tiles[words[r * COLS + c] & ~0x7F]]
                im[r * 16:r * 16 + 16, c * 16:c * 16 + 16] = rgb_of_index[t]
        return im
    am8 = np.array([[v * 17 for v in amiga12(c)] for c in l2], np.uint8)
    ims = {"amiga": render(am8, list(range(16)))}
    for k in ("A", "B", "C"):
        pal, rem = opts[k]
        graded = np.array([[BRIGHT[v] * 255 // 7 for v in c] for c in pal], np.uint8)
        plain = np.array([[v * 255 // 7 for v in c] for c in pal], np.uint8)
        ims[k] = render(graded, rem)
        ims[k + "_plain"] = render(plain, rem)
    for k, im in ims.items():
        write_png(OUT / f"level2_{k}.png", W, H, [im[y].tobytes() for y in range(H)])
    # half-size overview: Amiga, then C graded, then A graded, then B graded
    def half(im):
        return ((im[0::2, 0::2].astype(np.uint16) + im[1::2, 0::2] + im[0::2, 1::2] + im[1::2, 1::2]) // 4).astype(np.uint8)
    stack = np.concatenate([half(ims["amiga"]), np.full((8, W // 2, 3), 255, np.uint8), half(ims["C"]),
                            np.full((8, W // 2, 3), 255, np.uint8), half(ims["A"]),
                            np.full((8, W // 2, 3), 255, np.uint8), half(ims["B"])])
    write_png(OUT / "level2_compare_half.png", W // 2, stack.shape[0], [stack[y].tobytes() for y in range(stack.shape[0])])
    # 1:1 crops (Amiga | C graded | A graded | B graded) of three areas
    crops = {"vat0": (640, 600), "blue": None, "top": (960, 96)}
    # the area with the most c5/c6 (the blues) in a 288 x 176 window
    blue = np.isin(render(np.arange(16, dtype=np.uint8)[:, None].repeat(3, 1), list(range(16)))[..., 0], [5, 6])
    best = max(((blue[y:y + 176, x:x + 288].sum(), x, y) for y in range(0, H - 176, 16) for x in range(0, W - 288, 32)))
    crops["blue"] = (best[1], best[2])
    for name, (x, y) in crops.items():
        y = min(y, H - 176)
        parts = [ims[k][y:y + 176, x:x + 288] for k in ("amiga", "C", "A", "B")]
        sep = np.full((176, 4, 3), 255, np.uint8)
        row = np.concatenate([parts[0], sep, parts[1], sep, parts[2], sep, parts[3]], 1)
        write_png(OUT / f"crop_{name}.png", row.shape[1], row.shape[0], [row[i].tobytes() for i in range(row.shape[0])])
        print(f"crop {name}: map x {x}, y {y} (288 x 176: Amiga | C | A | B, graded)")
    (OUT / "level2_C.pal").write_bytes(bytes(b for r, g, b_ in pC for b in ((r << 4) | b_, g)))
    (OUT / "level2_C.remap").write_bytes(bytes(rC))
    print("best c11 index in C among 8..15:", best11, "res:", {k: round(v, 3) for k, v in res.items()})


def VAT_OFFS(img):
    return [w & ~0x7F for w in struct.unpack_from(">48H", img, 0x927A)]


if __name__ == "__main__":
    main()
