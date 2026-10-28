#!/usr/bin/env python3
"""Level 2's vats (level_tick_1 $91BC): what changes between the animation's steps, per tile and
per vat, and what that costs the VDP. Reads the level-2 RAM image (read-only).

The model is level_tick_1's (REA, level2_full.bin):
  - the records at $95B2 (8 bytes: x left, y, x right, rows; -1 ends);
  - on odd game frames ($B01 bit 0) every column k of a vat in the window gets, in its first row,
    T0[d], then rows + 1 more cells alternating T1[d], T2[d] (rows + 2 cells in all), where
    d = (phase_k & 0Eh) + (10h if the high byte of entry k + 1 is not 0) and phase_k is the low
    byte of entry k of the table at $92DA, which grows by 2 at the first vat of every odd frame;
  - T0 = $927A, T1 = $929A, T2 = $92BA: 16 map words each.
usage: vats.py level2_full.bin outdir
"""
import struct
import sys
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path("/Users/rodrigogarcia/Library/Mobile Documents/com~apple~CloudDocs/Projects/VSCode Projects/msxports")
sys.path.insert(0, str(REPO / "tools"))
from planar import write_png  # noqa: E402

DATAL = 0x28000


def words(img, a, n):
    return list(struct.unpack_from(f">{n}H", img, a))


def tile(img, off):
    """map word's tile (offset & ~7Fh from DATAL) -> 16x16 indices."""
    rows = []
    for y in range(16):
        r = []
        for x in range(16):
            v = 0
            for p in range(4):
                if img[DATAL + off + (y * 4 + p) * 2 + (x >> 3)] & (0x80 >> (x & 7)):
                    v |= 1 << p
            r.append(v)
        rows.append(r)
    return rows


def diff(a, b):
    """-> changed pixels, changed bytes (2 px each, SCREEN 5), bounding box (x0, y0, x1, y1) in
    bytes/lines or None, changed lines."""
    px = [(x, y) for y in range(16) for x in range(16) if a[y][x] != b[y][x]]
    if not px:
        return 0, 0, None, 0
    by = {(x >> 1, y) for x, y in px}
    xs = [x for x, _ in by]
    ys = [y for _, y in by]
    return len(px), len(by), (min(xs), min(ys), max(xs) + 1, max(ys) + 1), len(set(ys))


def colour_map(a, b):
    """A pixel-wise colour mapping a -> b, if one exists (palette cycling possible)."""
    m = {}
    for y in range(16):
        for x in range(16):
            if m.setdefault(a[y][x], b[y][x]) != b[y][x]:
                return None
    return m


def main():
    img = Path(sys.argv[1]).read_bytes()
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    T = {"T0": words(img, 0x927A, 16), "T1": words(img, 0x929A, 16), "T2": words(img, 0x92BA, 16)}
    ph = words(img, 0x92DA, 48)
    vats = []
    a = 0x95B2
    while struct.unpack_from(">h", img, a)[0] >= 0:
        vats.append(words(img, a, 4))
        a += 8
    print("vat records ($95B2):")
    for k, (xl, y, xr, rows) in enumerate(vats):
        cols = ((xr - xl) & 0xFFFF) // 16 + 1
        print(f"  vat {k}: x {xl}-{xr} y {y} rows {rows}: {cols} columns x {rows + 2} rows = {cols * (rows + 2)} cells"
              f" (map column {(xl >> 4) - 8}, row {y >> 4})")
    print("tables:")
    for n, ws in T.items():
        print(f"  {n}: " + " ".join(f"{w:04X}" for w in ws), " attributes:", sorted({w & 0x7F for w in ws}))
    print("  phase table $92DA:", " ".join(f"{w:04X}" for w in ph))
    tiles = {w: tile(img, w & ~0x7F) for ws in T.values() for w in ws}
    print(f"distinct vat words: {len(tiles)}")
    # per table and variant: the step p -> p + 1 (8 phases, cyclic)
    print("step costs (d = 2p + 16v -> 2(p+1 mod 8) + 16v): changed bytes of 128, bounding box, colour map?")
    step_bytes = {}
    for n, ws in T.items():
        for v in (0, 1):
            line = []
            for p in range(8):
                w0, w1 = ws[p + 8 * v], ws[(p + 1) % 8 + 8 * v]
                npx, nby, box, nl = diff(tiles[w0], tiles[w1])
                step_bytes[(n, v, p)] = (nby, box)
                cm = colour_map(tiles[w0], tiles[w1]) if npx else {}
                line.append(f"{p}:{nby:3d}B{'' if box is None else ' %dx%d' % (box[2] - box[0], box[3] - box[1])}"
                            f"{' pal' if cm is not None and npx else ''}")
            print(f"  {n} v{v}: " + " | ".join(line))
    # per vat: the cells and bytes one animation step changes (the columns' phases from $92DA)
    print("per vat and step (all its columns), V9958 (one copy) / V9938 (both pages):")
    tot = {}
    for k, (xl, y, xr, rows) in enumerate(vats):
        cols = ((xr - xl) & 0xFFFF) // 16 + 1
        res = []
        for s in range(8):
            cells = byts = boxb = 0
            for c in range(cols):
                p = ((ph[c] & 0xFF) // 2 + s) % 8
                v = 1 if ph[c + 1] >> 8 else 0
                seq = ["T0"] + [("T1" if r % 2 == 0 else "T2") for r in range(rows + 1)]
                for n in seq:
                    nby, box = step_bytes[(n, v, p)]
                    if nby:
                        cells += 1
                        byts += nby
                        boxb += (box[2] - box[0]) * (box[3] - box[1])
            res.append((cells, byts, boxb))
        mc = max(r[0] for r in res)
        mb = max(r[1] for r in res)
        mbox = max(r[2] for r in res)
        tot[k] = (cols * (rows + 2), mc, mb, mbox)
        print(f"  vat {k}: {cols * (rows + 2)} cells; a step changes at most {mc} cells, {mc * 128} B as whole tiles, "
              f"{mbox} B as bounding boxes, {mb} B exactly (mean {sum(r[0] for r in res) / 8:.1f} cells)")
    # sheet of the vat tiles in the Amiga's level-2 palette
    pal12 = [0] + words(img, 0x10036, 15)
    rgb = [(((c >> 8) & 15) * 17, ((c >> 4) & 15) * 17, (c & 15) * 17) for c in pal12]
    S = 3
    W, H = 16 * 17 * S, 3 * 17 * S
    rowsimg = [bytearray(W * 3) for _ in range(H)]
    for ti, (n, ws) in enumerate(T.items()):
        for i, w in enumerate(ws):
            t = tiles[w]
            for yy in range(16 * S):
                for xx in range(16 * S):
                    c = rgb[t[yy // S][xx // S]]
                    X, Y = (i * 17) * S + xx, (ti * 17) * S + yy
                    rowsimg[Y][3 * X:3 * X + 3] = bytes(c)
    write_png(out / "vat_tiles_amiga.png", W, H, [bytes(r) for r in rowsimg])
    print("wrote", out / "vat_tiles_amiga.png")


if __name__ == "__main__":
    main()
