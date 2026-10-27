#!/usr/bin/env python3
"""What the VDP shows while the CPU is held (no split, no VBLANK list): every display line from the
same registers.

usage: frozen.py SNAP.bin OUT.png   (SNAP: hz7.tcl hz7_snap: VRAM 128 KiB, RAM C000h-FFFFh,
64 VDP registers, the palette; fixchk.tcl hzp_setup writes DIR/TAG_held.bin on a hold)

SCREEN 5: 212 lines of the page R#2 selects, scrolled by R#23, in the palette as it stands; colour 0
is the backdrop R#7 (TP off); sprites left out. Written 2x.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from planar import write_png  # noqa: E402


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    d = Path(sys.argv[1]).read_bytes()
    vram, regs, pal = d[:0x20000], d[0x24000:0x24040], d[0x24040:0x24060]
    page = (regs[2] >> 5) & 3
    rgb = [bytes(v * 255 // 7 for v in (pal[2 * i] >> 4 & 7, pal[2 * i + 1] & 7, pal[2 * i] & 7)) for i in range(16)]
    if not regs[8] & 0x20:
        rgb[0] = rgb[regs[7] & 15]
    rows = []
    for y in range(212):
        line = vram[page * 0x8000 + ((y + regs[23]) & 0xFF) * 128:][:128]
        px = b"".join(rgb[b >> 4] + rgb[b & 15] for b in line)
        px2 = b"".join(px[3 * i:3 * i + 3] * 2 for i in range(256))
        rows += [px2, px2]
    if not regs[1] & 0x40:
        rows = [rgb[regs[7] & 15] * 512] * 424
    write_png(Path(sys.argv[2]), 512, 424, rows)
    print(f"page {page}, R#23 {regs[23]}, R#1 {regs[1]:02X}, R#8 {regs[8]:02X}, R#7 {regs[7]:02X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
