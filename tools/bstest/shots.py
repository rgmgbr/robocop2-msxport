#!/usr/bin/env python3
"""A hz7.tcl snapshot as the screen shows it: the play area (the applied list's page, its sprites,
the play field's colours pf_pal), the 5 blank lines and the HUD (page 3 from line 208 in the split's
colours SR_PAL), each MSX pixel 2 x 2.

usage: shots.py OUT_DIR SNAP.bin [...]   -> OUT_DIR/<snapshot name>.png
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from planar import write_png  # noqa: E402
import stepcheck  # noqa: E402

PF_PAL, SR_PAL = 0xEA40, 0xEA22


def rgb(pair_lo: int, pair_hi: int) -> bytes:
    return bytes(v * 255 // 7 for v in (pair_lo >> 4 & 7, pair_hi & 7, pair_lo & 7))


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for path in map(Path, sys.argv[2:]):
        d = path.read_bytes()
        vram, ram, regs = d[:0x20000], d[0x20000:0x24000], d[0x24000:0x24040]
        lp = ram[3] | ram[4] << 8
        lregs, _ = stepcheck.parse_list(ram[lp - 0xC000:lp - 0xC000 + 32])
        page = (lregs.get(2, 0x1F) >> 5) & 3
        pf = ram[PF_PAL - 0xC000:PF_PAL - 0xC000 + 32]
        hp = ram[SR_PAL - 0xC000:SR_PAL - 0xC000 + 30]
        pal = [bytes(3)] + [rgb(pf[2 * i], pf[2 * i + 1]) for i in range(1, 16)]
        hud = [bytes(3)] + [rgb(hp[2 * i - 2], hp[2 * i - 1]) for i in range(1, 16)]
        img = stepcheck.page_pixels(vram[page * 0x8000:page * 0x8000 + 20736])
        if lregs.get(8, 0x0A) & 2 == 0:
            sat = ((regs[11] & 3) << 15) | ((lregs.get(5, 0xC7) & 0xFC) << 7)
            stepcheck.compose_sprites(img, vram, sat, stepcheck.sat_entries(vram[sat:sat + 32]))
        rows = [b"".join(pal[c] * 2 for c in r) for r in img]
        rows += [bytes(3 * 512)] * 5
        for y in range(45):
            line = vram[0x1E800 + 128 * y:0x1E800 + 128 * y + 128]
            rows.append(b"".join(hud[b >> 4] * 2 + hud[b & 15] * 2 for b in line))
        rows = [r for r in rows for _ in (0, 1)]
        write_png(out / f"{path.stem}.png", 512, len(rows), rows)
        print(out / f"{path.stem}.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
