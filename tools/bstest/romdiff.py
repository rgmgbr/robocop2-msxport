#!/usr/bin/env python3
"""romdiff.py A.rom B.rom: the 8 KiB banks that differ, with the differing byte count and range
(relocheck.py then checks that a code bank's differences are relocated label words).

romdiff.py --blocks A.rom B.rom [--allow NAME,...] [A_banks.inc B_banks.inc]: the same by block,
each build's blocks at their own banks (tools/mkrom.py gen/banks.inc, by default the gen/ next
to each ROM, as tools/bstest/build.sh leaves it): a block starts at a bank equate (BANK_*, *_BANK,
L2_TILES, L2_MAP, L2_ATR, L2_TAB, L2_ATLAS, their L3_ twins; FIXED = banks 0-1; an equate at another's bank is an
alias) and runs to the next one, the last to the first bank of 0FFh bytes. Each block of either
build is compared with the other's of the same name wherever it lies: identical, its byte count
and range otherwise, another size, or only in one build. The code blocks (FIXED, BANK_*: msx/rc2.asm's
sections) are listed for relocheck.py; exit 1 when a data block differs, changes its size or is
missing in B but those --allow names (a block only B has is listed, not a failure).
(docs/HARNESS.md 5.15; the shift of every block after the sprite pool, the level-2 plan's step 12)"""
from __future__ import annotations

import re
import sys
from pathlib import Path

BANK = 8192
EXTRA = ("L2_TILES", "L2_MAP", "L2_ATR", "L2_TAB", "L2_ATLAS", "L3_TILES", "L3_MAP", "L3_ATR", "L3_TAB", "L3_ATLAS",
         "L3_FC")


def blocks(rom: bytes, inc: str) -> dict[str, tuple[int, int]]:
    """name -> (first bank, banks) of the image's blocks (banks.inc's text)."""
    starts: dict[int, str] = {0: "FIXED"}
    for m in re.finditer(r"^(\w+): equ (\S+)", inc, re.M):
        name, v = m[1], int(m[2], 0)
        if (name.startswith("BANK_") or name.endswith("_BANK") or name in EXTRA) and v not in starts:
            starts[v] = name
    order = sorted(starts)
    n = len(rom) // BANK
    out = {}
    for i, b in enumerate(order):
        if i + 1 < len(order):
            end = order[i + 1]
        else:
            end = b + 1
            while end < n and rom[end * BANK:(end + 1) * BANK] != b"\xff" * BANK:
                end += 1
        out[starts[b]] = (b, end - b)
    return out


def diff(x: bytes, y: bytes) -> str:
    d = [i for i in range(min(len(x), len(y))) if x[i] != y[i]]
    if not d:
        return "identical"
    return f"{len(d)} bytes differ, offsets {d[0]:05X}-{d[-1]:05X}"


def by_block(args: list[str]) -> int:
    allow: set[str] = set()
    if "--allow" in args:
        k = args.index("--allow")
        allow = set(filter(None, args[k + 1].split(",")))
        del args[k:k + 2]
    if len(args) not in (2, 4):
        print(__doc__, file=sys.stderr)
        return 2
    roms = [Path(p).read_bytes() for p in args[:2]]
    incs = args[2:] or [str(Path(p).parent / "gen" / "banks.inc") for p in args[:2]]
    ba, bb = (blocks(r, Path(i).read_text()) for r, i in zip(roms, incs))
    print(f"sizes {len(roms[0])} {len(roms[1])}")
    bad, same, code = [], [], []
    for name in sorted(set(ba) | set(bb), key=lambda k: (ba.get(k) or bb[k])[0]):
        is_code = name == "FIXED" or name.startswith("BANK_")
        if name not in bb:
            print(f"{name}: banks {ba[name][0]}-{sum(ba[name]) - 1} in A only")
            if name not in allow:
                bad.append(name)
            continue
        if name not in ba:
            print(f"{name}: banks {bb[name][0]}-{sum(bb[name]) - 1} in B only (new)")
            continue
        (a0, an), (b0, bn) = ba[name], bb[name]
        x, y = roms[0][a0 * BANK:(a0 + an) * BANK], roms[1][b0 * BANK:(b0 + bn) * BANK]
        where = f"banks {a0}-{a0 + an - 1} -> {b0}-{b0 + bn - 1}"
        if an != bn:
            verdict = f"{an} -> {bn} banks ({diff(x, y)} over the first {min(an, bn)})"
        else:
            verdict = diff(x, y)
        print(f"{name}: {where}: {verdict}" + (" (code: relocheck.py)" if is_code and verdict != "identical" else ""))
        if is_code:
            code.append(name) if verdict != "identical" else same.append(name)
        elif verdict == "identical":
            same.append(name)
        elif name not in allow:
            bad.append(name)
    print(f"{len(same)} blocks identical; code blocks that differ: {', '.join(code) or 'none'}; data blocks "
          f"that differ but allowed: {', '.join(sorted(allow & set(ba))) or 'none'}")
    print("romdiff: " + ("PASS" if not bad else f"FAIL ({', '.join(bad)})"))
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if argv and argv[0] == "--blocks":
        return by_block(argv[1:])
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[0], "rb") as f:
        a = f.read()
    with open(argv[1], "rb") as f:
        b = f.read()
    print(f"sizes {len(a)} {len(b)}")
    for k in range(max(len(a), len(b)) // 8192):
        x, y = a[k * 8192:(k + 1) * 8192], b[k * 8192:(k + 1) * 8192]
        if x != y:
            d = [i for i in range(8192) if i >= len(x) or i >= len(y) or x[i] != y[i]]
            print(f"bank {k}: {len(d)} bytes differ, offsets {d[0]:04X}-{d[-1]:04X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
