#!/usr/bin/env python3
"""A later level's play-field palette for the MSX, made from level 1's joint palette (palette C).

Level 1's palette is a joint one (tools/msxsprites.py: build/msx/robocop.pal and .remap): RoboCop's
sprite colours at the OR-closed indices 1-7 (5 is the sprites' black), the background's colours at
0, 1, 4, 6 and 8-15 through the remap (Amiga background colour -> MSX index), which leaves 2, 3 and 7
to RoboCop's flashes. The Amiga's level 2 keeps RoboCop's colours (COLOR16-31 are the same) and
changes five background colours (c5, c6, c10, c11, c15 of COLOR01-15 at $10036 against level 1's
$FFF6). Palette C does what the Amiga does: level 1's index layout and remap, unchanged, with the
new level's values where they apply:

  - entries 0-7 stay level 1's, so RoboCop's data and every frame level 1 already holds stay
    byte-identical (one sprite pool for every level); the frames show the new level's values
    through entries 8-15, as the Amiga's BOBs show its background palette;
  - an entry 8-15 takes the new level's 3-bit colour when every Amiga colour the remap puts there
    has that same 3-bit colour in the new level. A shared entry whose colours now differ keeps
    level 1's value, the compromise level 1's palette made (level 2's entry 14: c10 A00 -> 500,
    c11 700 -> 300; entry 12: c2, c7 -> 100, c12 -> 200);
  - a colour the remap puts into 1-7 that changed cannot follow (RoboCop's entries): reported.

Level 2 gets 000 432 455 344 333 000 111 234 222 555 210 015 100 012 500 630: level 1's with 9 = 555
(c15 BBB), 11 = 015 (c5 03A) and 13 = 012 (c6 025).

The checks (exit 1 when one fails):
  - entries 0-7 equal level 1's;
  - the remap leaves entries 2, 3 and 7 free of background colours (RoboCop's flashes);
  - colour 0 is black (the HUD split: msx/isr.asm loads colours 1-15 only);
  - the mean colour error over the map's pixels is at most option A's: ΔE76 (CIELAB, D65) of
    each pixel's Amiga colour (12-bit) against its entry (plain 3-bit levels, v / 7), weighted by
    the pixels of the level's map (rows x 160 cells); option A is level 1's palette as it is, each
    Amiga colour 1-15 to its nearest entry 1-15.

Outputs: <out>.pal (16 colours, V9938 pairs R << 4 | B, G) and <out>.remap (16 bytes: the MSX
index of each Amiga background colour) for tools/msxconv.py --joint <out>; a report of the
entries and the errors on stdout. The palette is plain: tools/mkrom.py grades it, as level 1's.

preview: the whole map, the original above the conversion (tools/msxconv.py's <level>.til and
.map under <level>.pal, graded through tools/msxbright.py BRIGHT, as the game shows it), 8 white
lines between, at 1:1; and a check that every cell's MSX tile is the original's tile through
<level>.remap, pixel for pixel (exit 1 otherwise).

usage: msxlvpal.py palette DATAL.bin --pal-file main_8000.bin --base-addr 0xfff6 --pal-addr 0x10036
                           --base build/msx/robocop --rows 50 -o build/msx/level2
       msxlvpal.py preview DATAL.bin --pal-file main_8000.bin --pal-addr 0x10036 --rows 50
                           --level build/msx/level2 -o build/msx/level2_amiga_vs_msx.png
"""
from __future__ import annotations

import argparse
import struct
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from msxbright import BRIGHT  # noqa: E402
from msxconv import COLS, MAP_OFFSET, amiga_to_msx, pack_sc5, tile_indices  # noqa: E402
from planar import write_png  # noqa: E402

FLASH = (2, 3, 7)                   # RoboCop's flash entries: no background colour may use them
ROBOCOP = range(8)                  # entries 0-7: level 1's, in every level


def amiga_colours(data: bytes, load: int, addr: int) -> list[int]:
    """COLOR00-15 of a level: 0, then the 15 words at addr (COLOR01-15)."""
    return [0] + list(struct.unpack_from(">15H", data, addr - load))


def read_pal(data: bytes) -> list[tuple[int, int, int]]:
    """V9938 pairs (R << 4 | B, G) -> 16 (r, g, b), 3 bits each."""
    return [(data[2 * i] >> 4 & 7, data[2 * i + 1] & 7, data[2 * i] & 7) for i in range(16)]


def pal_bytes(pal: list[tuple[int, int, int]]) -> bytes:
    return bytes(b for r, g, bl in pal for b in ((r << 4) | bl, g))


def lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """sRGB components 0..1 -> CIELAB (D65)."""
    def linear(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (linear(c) for c in rgb)
    xyz = ((0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047,
           0.2126 * r + 0.7152 * g + 0.0722 * b,
           (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883)

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 216 / 24389 else (24389 / 27 * t + 16) / 116
    fx, fy, fz = (f(t) for t in xyz)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def lab_amiga(c12: int) -> tuple[float, float, float]:
    return lab(tuple(((c12 >> s) & 15) / 15 for s in (8, 4, 0)))


def lab_msx(c: tuple[int, int, int]) -> tuple[float, float, float]:
    return lab(tuple(v / 7 for v in c))


def delta_e(p: tuple, q: tuple) -> float:
    return sum((a - b) ** 2 for a, b in zip(p, q)) ** 0.5


def palette_c(base: list[tuple], remap: list[int], old: list[int], new: list[int]) -> tuple[list[tuple], list[str]]:
    """Palette C: level 1's palette (base) with an entry 8-15 set to the new level's 3-bit colour
    when every Amiga colour the remap puts there has that colour -> (palette, notes)."""
    pal = list(base)
    notes = []
    for i in range(8, 16):
        users = [c for c in range(16) if remap[c] == i]
        values = {amiga_to_msx(new[c]) for c in users}
        if len(values) == 1 and pal[i] != next(iter(values)):
            pal[i] = values.pop()
            notes.append(f"entry {i:2d}: {''.join(map(str, base[i]))} -> {''.join(map(str, pal[i]))} "
                         f"(" + ", ".join(f"c{c} {new[c]:03X}" for c in users) + ")")
        elif len(values) > 1 and any(old[c] != new[c] for c in users):
            notes.append(f"entry {i:2d}: {''.join(map(str, base[i]))} kept, its colours differ now ("
                         + ", ".join(f"c{c} {old[c]:03X} -> {new[c]:03X}" for c in users) + ")")
    for c in range(1, 16):
        if remap[c] in ROBOCOP and old[c] != new[c]:
            notes.append(f"c{c} {old[c]:03X} -> {new[c]:03X} keeps RoboCop's entry {remap[c]} "
                         f"({''.join(map(str, base[remap[c]]))}): palette C cannot follow it")
    return pal, notes


def nearest_remap(pal: list[tuple], colours: list[int]) -> list[int]:
    """Option A's remap: each Amiga colour 1-15 to its nearest entry 1-15 (the first of equals)."""
    labs = [lab_msx(c) for c in pal]
    out = [0]
    for c in colours[1:]:
        lc = lab_amiga(c)
        out.append(min(range(1, 16), key=lambda i: (delta_e(labs[i], lc), i)))
    return out


def pixel_counts(datal: bytes, rows: int) -> list[int]:
    """Pixels of each Amiga colour over the level's map (rows x 160 cells)."""
    uses = Counter(struct.unpack_from(">H", datal, MAP_OFFSET + 2 * i)[0] & ~0x7F for i in range(rows * COLS))
    count = [0] * 16
    for off, n in uses.items():
        for row in tile_indices(datal, off):
            for v in row:
                count[v] += n
    return count


def colour_errors(pal: list[tuple], remap: list[int], colours: list[int]) -> list[float]:
    return [delta_e(lab_msx(pal[remap[c]]), lab_amiga(colours[c])) for c in range(16)]


def mean_error(errors: list[float], count: list[int]) -> float:
    return sum(e * n for e, n in zip(errors, count)) / sum(count)


def checks(pal: list[tuple], base: list[tuple], remap: list[int], mean_c: float, mean_a: float) -> list[str]:
    """What fails among the checks (nothing: palette C holds)."""
    bad = []
    if pal[:8] != base[:8]:
        bad.append("entries 0-7 differ from level 1's (RoboCop's data and the shared frames)")
    used = sorted(set(remap) & set(FLASH))
    if used:
        bad.append(f"the remap puts background colours into {used} (RoboCop's flash entries 2, 3, 7)")
    if pal[0] != (0, 0, 0) or remap[0] != 0:
        bad.append("colour 0 is not black (the HUD split loads colours 1-15 only)")
    if mean_c > mean_a + 1e-9:
        bad.append(f"mean dE76 {mean_c:.3f} above option A's {mean_a:.3f} (level 1's palette as it is)")
    return bad


def name(c: tuple) -> str:
    return "".join(map(str, c))


def cmd_palette(a) -> int:
    datal = Path(a.datal).read_bytes()
    code = Path(a.pal_file).read_bytes()
    old = amiga_colours(code, a.pal_load, a.base_addr)
    new = amiga_colours(code, a.pal_load, a.pal_addr)
    base = read_pal(Path(a.base).with_suffix(".pal").read_bytes())
    remap = list(Path(a.base).with_suffix(".remap").read_bytes())
    if len(remap) != 16 or any(not 0 <= v < 16 for v in remap):
        print(f"error: {Path(a.base).with_suffix('.remap')}: not 16 indices 0-15", file=sys.stderr)
        return 1
    pal, notes = palette_c(base, remap, old, new)
    count = pixel_counts(datal, a.rows)
    err_c = colour_errors(pal, remap, new)
    remap_a = nearest_remap(base, new)
    err_a = colour_errors(base, remap_a, new)
    mean_c, mean_a = mean_error(err_c, count), mean_error(err_a, count)
    total = sum(count)
    print(f"Amiga background colours, level 1 ${a.base_addr:X} / this level ${a.pal_addr:X}: changed "
          + (", ".join(f"c{c} {old[c]:03X} -> {new[c]:03X}" for c in range(1, 16) if old[c] != new[c]) or "none"))
    for n in notes:
        print("  " + n)
    print("palette C: " + " ".join(name(c) for c in pal) + "   (level 1: " + " ".join(name(c) for c in base) + ")")
    print("remap (level 1's): " + " ".join(map(str, remap)))
    print("per colour: share of the map's pixels, dE76 under C / under A (level 1's palette, nearest entry):")
    print("  " + "  ".join(f"c{c} {100 * count[c] / total:.2f}% {err_c[c]:.1f}/{err_a[c]:.1f}"
                           for c in range(16) if count[c]))
    print(f"mean dE76 over the map's pixels: C {mean_c:.3f}, A {mean_a:.3f} (A's remap: {' '.join(map(str, remap_a))})")
    bad = checks(pal, base, remap, mean_c, mean_a)
    for b in bad:
        print(f"msxlvpal: error: {b}", file=sys.stderr)
    if bad:
        return 1
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".pal").write_bytes(pal_bytes(pal))
    out.with_suffix(".remap").write_bytes(bytes(remap))
    print(f"{out}.pal, .remap: entries 0-7 level 1's, 2/3/7 free, colour 0 black, mean dE76 {mean_c:.2f} <= A's {mean_a:.2f}")
    return 0


def cmd_preview(a) -> int:
    datal = Path(a.datal).read_bytes()
    colours = amiga_colours(Path(a.pal_file).read_bytes(), a.pal_load, a.pal_addr)
    lv = Path(a.level)
    til, mp = lv.with_suffix(".til").read_bytes(), lv.with_suffix(".map").read_bytes()
    pal = read_pal(lv.with_suffix(".pal").read_bytes())
    remap = list(lv.with_suffix(".remap").read_bytes())
    if len(mp) != a.rows * COLS * 2:
        print(f"error: {lv.with_suffix('.map')}: {len(mp)} bytes, not {a.rows} x {COLS} words", file=sys.stderr)
        return 1
    am_rgb = [bytes(((c >> s) & 15) * 17 for s in (8, 4, 0)) for c in colours]
    msx_rgb = [bytes(BRIGHT[v] * 255 // 7 for v in c) for c in pal]
    tiles = len(til) // 128
    am_rows: dict[int, list[bytes]] = {}
    msx_rows: dict[int, list[bytes]] = {}
    pairs: set[tuple[int, int]] = set()             # (offset, tile) pairs checked
    bad = []
    top, bottom = [], []
    for r in range(a.rows):
        a_cells, m_cells = [], []
        for c in range(COLS):
            off = struct.unpack_from(">H", datal, MAP_OFFSET + 2 * (r * COLS + c))[0] & ~0x7F
            t = struct.unpack_from("<H", mp, 2 * (r * COLS + c))[0]
            if off not in am_rows:
                am_rows[off] = [b"".join(am_rgb[v] for v in row) for row in tile_indices(datal, off)]
            if t >= tiles:
                bad.append(f"row {r}, column {c}: tile {t} beyond the {tiles} of {lv.with_suffix('.til')}")
                t = 0
            elif (off, t) not in pairs:
                pairs.add((off, t))
                if til[128 * t:128 * t + 128] != pack_sc5([[remap[v] for v in row] for row in tile_indices(datal, off)]):
                    bad.append(f"row {r}, column {c}: tile {t} is not offset {off:04X}'s through the remap")
            if t not in msx_rows:
                msx_rows[t] = [b"".join(msx_rgb[til[128 * t + 8 * y + x // 2] >> (0 if x & 1 else 4) & 15]
                                        for x in range(16)) for y in range(16)]
            a_cells.append(am_rows[off])
            m_cells.append(msx_rows[t])
        for y in range(16):
            top.append(b"".join(cell[y] for cell in a_cells))
            bottom.append(b"".join(cell[y] for cell in m_cells))
    for b in bad[:8]:
        print(f"msxlvpal: error: {b}", file=sys.stderr)
    w = COLS * 16
    write_png(Path(a.output), w, 2 * len(top) + 8, top + [b"\xff" * 3 * w] * 8 + bottom)
    print(f"{a.output}: the original's map ({len(am_rows)} tile offsets) over the conversion ({len(msx_rows)} tiles, "
          f"graded), {w} x {2 * len(top) + 8}; {len(bad)} cells differ from the remap")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    num = lambda s: int(s, 0)  # noqa: E731
    for n in ("palette", "preview"):
        p = sub.add_parser(n)
        p.add_argument("datal", help="the level's DATAL file (tile sheet, then the map at 10000h)")
        p.add_argument("--pal-file", required=True, help="the file holding the Amiga palettes (main_8000.bin)")
        p.add_argument("--pal-load", type=num, default=0x8000, help="its load address")
        p.add_argument("--pal-addr", type=num, required=True, help="the level's COLOR01-15 (level 2: 0x10036)")
        p.add_argument("--rows", type=int, required=True, help="the map's rows (level 2: 50)")
        p.add_argument("-o", "--output", required=True)
        if n == "palette":
            p.add_argument("--base-addr", type=num, default=0xFFF6, help="level 1's COLOR01-15")
            p.add_argument("--base", required=True, help="prefix of level 1's joint .pal/.remap (tools/msxsprites.py)")
        else:
            p.add_argument("--level", required=True, help="prefix of the level's tools/msxconv.py outputs")
    a = ap.parse_args()
    return cmd_palette(a) if a.cmd == "palette" else cmd_preview(a)


if __name__ == "__main__":
    raise SystemExit(main())
