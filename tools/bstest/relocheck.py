#!/usr/bin/env python3
"""relocheck.py OLD.rom NEW.rom OLD.labels NEW.labels BANK...: every differing byte of the given banks
lies in a little-endian word whose old value is a label that moved and whose new value is that label's
new address (a relocated operand), or is a one-byte operand of a name that changed: NAME + k, an
equate of a byte both times (a bank number, FIELD_ID0, LV_SIZE) plus 0-63, moved by as much as that
name (`ld a,BANK_FRONT`, `add a,SPR_BASE_BANK + SPR_COL_BANK`, `ld a,HUD_BANK + 1`, a bank number
that tools/mkrom.py wrote into gen/music.inc), or the low or high byte of a moved label after an
instruction that takes a byte (`add a,atr_rows & 0FFh`); prints any byte that is neither. A BANK is
a number (the same bank in both images), OLD:NEW (a code bank that moved: the late sections after
the sprite pool's growth, the level-2 plan's step 12) or a name of the label files (BANK_PUZL: its
value in each). Exit 0 when every differing byte is one (romdiff.py lists the banks and blocks that
differ; docs/HARNESS.md 5.15)."""
from __future__ import annotations

import re
import sys
from collections import Counter

IMM8 = {0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E, 0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE}


def load(p: str) -> dict[str, int]:
    d = {}
    with open(p) as f:
        for line in f:
            m = re.match(r"^(\w+):\s+equ \$([0-9a-fA-F]+)", line)
            if m:
                d[m[1]] = int(m[2], 16)
    return d


def main(argv: list[str]) -> int:
    if len(argv) < 5:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[0], "rb") as f:
        a = f.read()
    with open(argv[1], "rb") as f:
        b = f.read()
    la, lb = load(argv[2]), load(argv[3])
    moved = {la[k]: lb[k] for k in la if k in lb and la[k] != lb[k]}
    # (one-byte operands: the names whose value changed, by their old and new bytes)
    small: list[tuple[str, int, int]] = []
    part: dict[tuple[int, int], str] = {}
    for k in sorted(la):
        if k in lb and la[k] != lb[k]:
            if la[k] < 256 and lb[k] < 256:
                small.append((k, la[k], lb[k]))
            else:
                part.setdefault((la[k] & 0xFF, lb[k] & 0xFF), f"{k} & 0FFh")
                part.setdefault((la[k] >> 8, lb[k] >> 8), f"{k} / 256")

    def byte_name(b0: int, b1: int) -> str | None:
        """NAME + k for a byte b0 -> b1: the changed byte equate nearest below b0 (k < 64) that moved
        by b1 - b0."""
        best = None
        for k, o, n in small:
            if b1 - b0 == n - o and 0 <= b0 - o < 64 and (best is None or b0 - o < best[1]):
                best = (k, b0 - o)
        return None if best is None else best[0] + (f" + {best[1]}" if best[1] else "")
    bad = 0
    for spec in argv[4:]:
        if ":" in spec:
            ob, nb = (int(x) for x in spec.split(":"))
        elif spec.isdigit():
            ob = nb = int(spec)
        elif spec in la and spec in lb:
            ob, nb = la[spec], lb[spec]
        else:
            print(f"relocheck: {spec}: not a bank, a pair of banks or a name of both label files", file=sys.stderr)
            return 2
        oa, na = ob * 8192, nb * 8192
        i = 0
        n = 0
        names: Counter[str] = Counter()
        while i < 8192:
            if a[oa + i] != b[na + i]:
                ok = False
                for j in (i - 1, i):
                    if 0 <= j < 8191:
                        wo = a[oa + j] | a[oa + j + 1] << 8
                        wn = b[na + j] | b[na + j + 1] << 8
                        if moved.get(wo) == wn:
                            ok = True
                            i = j + 2
                            n += 1
                            break
                if not ok:
                    pair = (a[oa + i], b[na + i])
                    name = byte_name(*pair)
                    if name is None and i > 0 and a[oa + i - 1] == b[na + i - 1] and a[oa + i - 1] in IMM8:
                        name = part.get(pair)
                    if name is not None:
                        names[name] += 1
                        i += 1
                        continue
                    print(f"bank {spec} offset {i:04X}: {a[oa + i]:02X} -> {b[na + i]:02X} not a relocated label word "
                          f"or a changed name's byte")
                    bad += 1
                    i += 1
            else:
                i += 1
        where = f"bank {spec}" + (f" ({ob} -> {nb})" if ob != nb or not spec.isdigit() else "")
        print(f"{where}: {n} relocated label words" + (", one-byte operands " + ", ".join(
            f"{k} x{v}" for k, v in sorted(names.items())) if names else ""))
    print("relocheck:", "PASS" if not bad else f"FAIL ({bad})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
