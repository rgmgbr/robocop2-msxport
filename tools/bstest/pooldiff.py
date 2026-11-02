#!/usr/bin/env python3
"""pooldiff.py OLD_PREFIX NEW_PREFIX: the global sprite pool against an older pool (PREFIX.bin,
PREFIX.inc: tools/msxsprites.py --pool), as when the pool grows for another level (docs/LEVEL3.md
3.10, docs/HARNESS.md 5.27) or its composition format changes: every index entry of RoboCop's and of
levels 1, 2 and 3 (level 3's when both pools have it) resolves to the same record (its header, its
bands with B sprites, sprites and bands), and every pattern and colour row a record names holds the
same bytes. A pool's header size is its .inc's SPR_COMP_HDR (8 when absent: the format before
2026-11-02, whose band mask msx/sprites.asm obj_set worked out from the band table, as this script
does for it). Exit 1 on a difference."""
import re, struct, sys
from pathlib import Path
BANK = 0x2000

def load(prefix):
    b = Path(prefix + ".bin").read_bytes()
    inc = {m[1]: int(m[2], 0) for m in re.finditer(r"^(\w+): equ (0x[0-9A-Fa-f]+|[0-9]+)\b", Path(prefix + ".inc").read_text(), re.M)}
    return b, inc

def record(b, inc, index, k):
    """Index entry k: (header (8 bytes), band mask, sprites, bands, patterns, colour rows)."""
    hdr = inc.get("SPR_COMP_HDR", 8)
    o = index - 0x8000 + 3 * k
    c = b[o] * BANK + (b[o + 1] | b[o + 2] << 8)
    nspr, nb = b[c], b[c + 2]
    head = b[c:c + 8]
    sprites = b[c + hdr:c + hdr + 12 * nspr]
    bands = b[c + hdr + 12 * nspr:c + hdr + 12 * nspr + 4 * nb]
    walked = sum(1 << j for j in range(nb) if bands[4 * j + 2])     # (obj_set's walk of the band table)
    mask = b[c + 8] if hdr > 8 else walked
    if mask != walked:
        mask = ("stored", mask, "walked", walked)
    pats, cols = [], []
    for s in range(nspr):
        dy, dx, pb, ab, q0, c0, q1, c1 = struct.unpack_from("<bbBBHHHH", b, c + hdr + 12 * s)
        for q in (q0, q1):
            if q != 0xFFFF:
                p0 = inc["SPR_PAT_BANK"] * BANK + 32 * q
                pats.append(b[p0:p0 + 32])
        for cc in (c0, c1):
            if cc != 0xFFFF:
                k0 = inc["SPR_COL_BANK"] * BANK + 16 * cc
                cols.append(b[k0:k0 + 16])
    return head, mask, sprites, bands, pats, cols

def main():
    (ob, oi), (nb, ni) = load(sys.argv[1]), load(sys.argv[2])
    bad = 0
    n_rc = (oi["SPR_BOB_INDEX_L1"] - 0x8000) // 3
    sets = [("RoboCop", None, n_rc)] + [(f"level {n}", f"SPR_BOB_INDEX_L{n}", oi[f"SPR_BOBS_L{n}"])
                                         for n in (1, 2, 3) if f"SPR_BOB_INDEX_L{n}" in oi and f"SPR_BOB_INDEX_L{n}" in ni]
    for name, idx_key, n in sets:
        oidx = 0x8000 if idx_key is None else oi[idx_key]
        nidx = 0x8000 if idx_key is None else ni[idx_key]
        diff = 0
        for k in range(n):
            if record(ob, oi, oidx, k) != record(nb, ni, nidx, k):
                diff += 1
        print(f"{name}: {n} index entries, {diff} differ")
        bad += diff
    print("pooldiff: " + ("PASS" if not bad else "FAIL"))
    return 1 if bad else 0

if __name__ == "__main__":
    raise SystemExit(main())
