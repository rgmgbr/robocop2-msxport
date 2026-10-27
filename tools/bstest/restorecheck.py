#!/usr/bin/env python3
"""4.2 check 5 and 4.4's "level 1 after the stage" on hz7_after / hz7_fresh records.

usage: restorecheck.py DIR AFTER_TAG FRESH_TAG [--known]

- DIR/AFTER_result.bin (the result screen after the stage): VRAM 10000h-17FFFh = build/msx/level1.vram's
  (the tiles vdp_setup wrote), page 3 lines 0-87 (18000h-1ABFFh, the play-field atlas) = the intro's
  (DIR/AFTER_intro.bin, before the stage), both SATs (1E200h, 1E600h) start with Y = 216;
- DIR/AFTER_g50.bin (the new game at its frame 50) against DIR/FRESH_g50.bin (a fresh start at the same
  frame): page 2, the atlas, the sprite tables (1D800h-1E7FFh) and the mirror D000h-DFFFh.
Exit 0 when all hold.

The sprite tables differ in 72 known, harmless bytes in every run of 2026-10-27 (docs/BRAINSTORM.md
4.2 check 5, docs/HARNESS.md): the colour rows of sprites 0-1 of both sets (1E000h-1E01Fh,
1E400h-1E41Fh: the cursor's colours where a fresh machine holds power-on bytes; the engine rewrites
them before use) and SAT entries 30-31 of both sets (1E278h-1E27Fh, 1E678h-1E67Fh: the same two
parked sprites, sets swapped: the engine's set phase is one flip apart). Without --known they fail
the check, as they did that night; with --known the colour rows are left out and entries 30-31 must
equal the fresh start's, in the same set or swapped.

Reads build/msx/level1.vram of the repository this file is in (tools/bstest/).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

KNOWN_COLOURS = set(range(0x1E000, 0x1E020)) | set(range(0x1E400, 0x1E420))
SAT30_A, SAT30_B = (0x1E278, 0x1E280), (0x1E678, 0x1E680)


def known_items(ga: bytes, gb: bytes, diff: list[int]) -> tuple[list[int], str]:
    """The differing addresses left once the known items are taken out, and what was taken."""
    a_a, a_b = ga[slice(*SAT30_A)], ga[slice(*SAT30_B)]
    b_a, b_b = gb[slice(*SAT30_A)], gb[slice(*SAT30_B)]
    sat = set(range(*SAT30_A)) | set(range(*SAT30_B))
    swapped = a_a == b_b and a_b == b_a
    rest = [i for i in diff if i not in KNOWN_COLOURS and not (swapped and i in sat)]
    ncol = sum(1 for i in diff if i in KNOWN_COLOURS)
    nsat = sum(1 for i in diff if i in sat) if swapped else 0
    return rest, f"{ncol} in the colour rows of sprites 0-1, {nsat} in SAT entries 30-31 (sets swapped)"


def main(argv: list[str]) -> int:
    known = "--known" in argv
    args = [a for a in argv if a != "--known"]
    if len(args) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    d, a, f = Path(args[0]), args[1], args[2]
    vram_ref = (ROOT / "build/msx/level1.vram").read_bytes()
    res = (d / f"{a}_result.bin").read_bytes()
    intro = (d / f"{a}_intro.bin").read_bytes()
    bad = 0

    def chk(name: str, ok: bool, extra: str = "") -> None:
        nonlocal bad
        print(f"{name}: {'PASS' if ok else 'FAIL'}{extra}")
        bad += not ok

    chk("after the stage: page 2 = level1.vram's tiles", res[0x10000:0x18000] == vram_ref[0x10000:0x18000],
        f" ({sum(x != y for x, y in zip(res[0x10000:0x18000], vram_ref[0x10000:0x18000]))} bytes differ)")
    chk("after the stage: page 3 lines 0-87 = before it (the intro)", res[0x18000:0x1AC00] == intro[0x18000:0x1AC00])
    chk("after the stage: SAT A, SAT B start with Y = 216", res[0x1E200] == 216 and res[0x1E600] == 216,
        f" ({res[0x1E200]}, {res[0x1E600]})")
    gf = (d / f"{f}_g50.bin")
    if gf.exists():
        ga, gb = (d / f"{a}_g50.bin").read_bytes(), gf.read_bytes()
        for name, lo, hi in (("page 2", 0x10000, 0x18000), ("atlas (page 3 lines 0-87)", 0x18000, 0x1AC00),
                             ("sprite patterns, colours, SATs (1D800h-1E7FFh)", 0x1D800, 0x1E800),
                             ("HUD (1E800h-1FE7Fh)", 0x1E800, 0x1FE80)):
            if known and lo == 0x1D800:
                diff = [i for i in range(lo, hi) if ga[i] != gb[i]]
                rest, what = known_items(ga, gb, diff)
                chk(f"new game at frame 50 vs a fresh start: {name}, the known items left out", not rest,
                    f" ({len(diff)} bytes differ: {what}; {len(rest)} others"
                    + (f", first at {rest[0]:05X}h)" if rest else ")"))
                continue
            n = sum(x != y for x, y in zip(ga[lo:hi], gb[lo:hi]))
            chk(f"new game at frame 50 vs a fresh start: {name}", n == 0, f" ({n} bytes differ)")
        ra, rb = ga[0x20000 + 0x1000:0x20000 + 0x2000], gb[0x20000 + 0x1000:0x20000 + 0x2000]
        n = [i for i in range(0x1000) if ra[i] != rb[i]]
        chk("new game at frame 50 vs a fresh start: the mirror D000h-DFFFh", not n,
            f" ({len(n)} bytes differ: {[hex(0xD000 + i) for i in n[:12]]})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
