#!/usr/bin/env python3
"""Runs a copy of tools/msxsprites.py (scratch tools/, imported, never the repository's) for level 2,
with level-2 settings patched in. Outputs go to OUT (never into the repository).

  --pal l1|l2        the Amiga background colours the BOBs are read with: level 1's ($FFF6) or level
                     2's ($10036); with l1, level 2's own frames (DATAL2) still take level 2's colour 6
                     (#025, the only one of the five that differ to land on another MSX entry)
  --fix-pal FILE     the MSX joint palette (level 1's robocop.pal: one palette for every level)
  --field CONF       static | dyn14 | dyn14_16 | dyn2_14 (which level-2 frames stream through the slot)
  --flash 0|1        keep the sprite versions of the play-field enemies (types 2, 14, 16) for the hit flash
  --field-h N        the atlas's lines with the dynamic slot (112 today: 88 + 24); 144 = 88 + 32 lines of
                     page 2 (two tile-cache rows) + 24
  --field-banks N, --dyn-banks N   ROM banks allowed for the atlas and the dynamic frames
  --dump FILE.npz    save the BOB previews (per frame: target, full, one layer; MSX palette indices)
everything after "--" goes to msxsprites.py's own argument parser."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "tools"))
import numpy as np  # noqa: E402
import msxsprites as ms  # noqa: E402

DATAL2 = (0x28000, 0x28000 + 105816)


def main() -> int:
    argv = sys.argv[1:]
    split = argv.index("--")
    mine, rest = argv[:split], argv[split + 1:]
    opts = dict(zip(mine[::2], mine[1::2]))
    pal_addr = {"l1": 0xFFF6, "l2": 0x10036}[opts.get("--pal", "l2")]
    orig_init = ms.Level.__init__

    def init(self, main_b, perma, datal, rows):
        orig_init(self, main_b, perma, datal, rows)
        pal12 = [struct.unpack_from(">H", main_b, pal_addr - 0x8000 + 2 * k)[0] for k in range(31)]
        self.bgpal = np.array([[0, 0, 0]] + [ms.amiga_rgb(c) for c in pal12[:15]])
        self.sppal = np.array([[0, 0, 0]] + [ms.amiga_rgb(c) for c in pal12[16:31]])
    ms.Level.__init__ = init
    if opts.get("--pal", "l2") == "l1":
        orig_img = ms.bob_image

        def bob_image(ram, addr, w, h):
            img = orig_img(ram, addr, w, h)
            if DATAL2[0] <= addr < DATAL2[1]:
                img = np.where(img == 6, 5, img)     # (level 2's #025 lands where level 1's #024 does)
            return img
        ms.bob_image = bob_image
    raw = Path(opts["--fix-pal"]).read_bytes()
    fixed = np.array([[(raw[2 * k] >> 4) & 7, raw[2 * k + 1] & 7, raw[2 * k] & 7] for k in range(16)], float) / 7
    ms.order_palette = lambda pal, comps, sppal: fixed.copy()
    ms.joint_palette = lambda level, comps: fixed.copy()
    conf = opts.get("--field", "static")
    ms.FIELD_PROCS = ("obj45_update", "obj02_update", "obj14_update", "obj16_update", "FUN_00008de6", "FUN_00008f02")
    ms.FIELD_RIDDEN = ("FUN_00008de6", "FUN_00008f02")
    ms.FIELD_FLASH = ("obj02_update", "obj14_update", "obj16_update") if opts.get("--flash", "1") == "1" else ()
    extra_dyn, extra_groups = (), ()
    if conf in ("dyn14", "dyn14_16", "dyn2_14"):
        extra_dyn += (0x3DFA0, 0x3E3D8)
        extra_groups += ((0x3DFA0,), (0x3E3D8,))
    if conf == "dyn14_16":
        extra_dyn += (0x40818, 0x40AE8, 0x40DB8, 0x41088)
        extra_groups += ((0x40818, 0x40DB8), (0x40AE8, 0x41088))
    if conf == "dyn2_14":
        extra_dyn += (0x3D280, 0x3D910)
        extra_groups += ((0x3D280,), (0x3D910,))
    ms.FIELD_DYN = ms.FIELD_DYN + extra_dyn
    ms.DYN_GROUPS = ms.DYN_GROUPS + extra_groups
    ms.DYN_ROM = int(opts.get("--dyn-banks", "2")) * 0x2000
    ms.FIELD_ROM = int(opts.get("--field-banks", "1")) * 0x2000
    ms.FIELD_H = int(opts.get("--field-h", "112"))   # (atlas lines above the dynamic slot: FIELD_H - DYN_H)
    if "--dump" in opts:                                   # (the BOB previews: target, full, one layer)
        orig_sheet = ms.render_sheet

        def render_sheet(path, items, pal):
            if str(path).endswith("_bobs.png"):
                np.savez_compressed(opts["--dump"], *[a for t in items for a in t])
            return orig_sheet(path, items, pal)
        ms.render_sheet = render_sheet
    sys.argv = ["msxsprites.py"] + rest
    return ms.main()


if __name__ == "__main__":
    raise SystemExit(main())
