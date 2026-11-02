#!/usr/bin/env python3
"""ZX0 (version 2, Einar Saukas' format: the "standard" forward streams) in Python: a packer and an
unpacker, for the movie stills (tools/msxphoto.py; msx/photo.asm pz_unz unpacks them into VRAM).

The format, as dzx0_standard reads it:
- Bits are read from the top of a byte down; interlaced Elias gamma: a value v >= 1 is its bits after
  the leading 1, each sent as 0 then the bit, then a 1.
- The first block is literals (no indicator): Elias(n), then n bytes.
- After literals: 0 = a copy from the last offset (Elias(n)), 1 = a copy from a new offset.
- After a copy: 0 = literals, 1 = a copy from a new offset.
- A new offset: Elias((offset - 1) // 128 + 1) with its data bits inverted, then a byte
  (127 - (offset - 1) % 128) << 1 whose bit 0 is the first bit of Elias(length - 1); length >= 2.
- The end: a new offset whose high part is 256. The last offset starts at 1.

The packer is an optimal parse over two states per position (the last block literals or a copy, with
the last offset of the cheapest way there), with candidate offsets from a 2-byte hash chain (DEPTH
most recent occurrences) plus the offsets of the lines above (stride: one picture line); it is not
the reference packer's exhaustive search, so its output is a valid ZX0 stream, a little longer.

usage: zx0.py pack IN OUT [--stride N] [--max-offset N] [--penalty BITS] | zx0.py unpack IN OUT
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MAX_OFFSET = 32640                  # the high part's Elias value 255 at most (256 is the end mark)
DEPTH = 24                          # the hash chain's candidates a position looks at
SHORT = 16                          # every length up to this one is tried, then the longest only
PENALTY = 0                         # bits added to every copy's cost: a decoder whose copies cost more
                                    # time than their bytes (msx/photo.asm reads them back from VRAM)
                                    # gets fewer, longer ones (pack's penalty argument)


def elias_bits(v: int) -> int:
    return 2 * (v.bit_length() - 1) + 1


def match_len(data: bytes, i: int, j: int, limit: int) -> int:
    """The length (at most limit) of data[i:] equal to data[j:], j < i (overlapping allowed: the
    copy repeats the pattern, as the unpacker's byte-by-byte copy does)."""
    n = 0
    while n + 16 <= limit and data[i + n:i + n + 16] == data[j + n:j + n + 16]:
        n += 16
    while n < limit and data[i + n] == data[j + n]:
        n += 1
    return n


def candidates(data: bytes, stride: int, max_offset: int = MAX_OFFSET) -> list[list[tuple[int, int]]]:
    """Per position the useful (offset, longest length) pairs: a longer offset only when its match
    is longer than every nearer one's."""
    n = len(data)
    chains: dict[int, list[int]] = {}
    out: list[list[tuple[int, int]]] = []
    for i in range(n):
        cands: list[tuple[int, int]] = []
        if i + 1 < n:
            key = data[i] << 8 | data[i + 1]
            prev = chains.get(key)
            offs = set()
            if prev:
                for j in reversed(prev[-DEPTH:]):
                    if i - j > max_offset:
                        break
                    offs.add(i - j)
            for k in (1, 2, 3):
                if stride and k * stride <= min(i, max_offset):
                    offs.add(k * stride)
            best = 1
            for o in sorted(offs):
                ln = match_len(data, i, i - o, n - i)
                if ln > best:
                    cands.append((o, ln))
                    best = ln
            if prev is None:
                chains[key] = [i]
            else:
                prev.append(i)
        out.append(cands)
    return out


def pack(data: bytes, stride: int = 0, penalty: int | None = None, max_offset: int = MAX_OFFSET) -> bytes:
    """data -> a ZX0 stream: offsets up to max_offset, PENALTY (or penalty) bits added to every copy."""
    pen = PENALTY if penalty is None else penalty
    n = len(data)
    if n == 0:
        raise ValueError("nothing to pack")
    INF = float("inf")
    cands = candidates(data, stride, max_offset)
    # state arrays: lit_* = the last block literals ending here, cp_* = a copy ending here
    lit_cost = [INF] * (n + 1)
    lit_from = [0] * (n + 1)        # the literals' first position
    lit_off = [1] * (n + 1)         # the last offset there
    cp_cost = [INF] * (n + 1)
    cp_from = [0] * (n + 1)         # the copy's first position
    cp_off = [1] * (n + 1)
    cp_prev = [0] * (n + 1)         # 0: it follows literals, 1: a copy, 2: the start (none)
    cp_rep = [False] * (n + 1)      # a copy from the last offset
    cp_cost[0] = 0
    cp_prev[0] = 2
    # the best start of literals ending at j: min over copies ending at i < j of cp_cost[i] + 1 - 8i
    best_base, best_i = INF, 0
    for i in range(n + 1):
        # literals ending at i (from the best copy end before it, or the one right before)
        if i > 0:
            for s in (best_i, i - 1):
                if cp_cost[s] < INF:
                    c = cp_cost[s] + (0 if s == 0 else 1) + elias_bits(i - s) + 8 * (i - s)
                    if c < lit_cost[i]:
                        lit_cost[i], lit_from[i], lit_off[i] = c, s, cp_off[s]
        if i == n:
            break
        if cp_cost[i] < INF:
            base = cp_cost[i] + (0 if i == 0 else 1) - 8 * i
            if base < best_base:
                best_base, best_i = base, i
        # copies from i
        lc, cc = lit_cost[i], cp_cost[i] if i > 0 else INF
        if lc < INF:                # from the last offset (after literals only)
            o = lit_off[i]
            if o <= i and o <= max_offset:
                rl = match_len(data, i, i - o, n - i)
                for ln in list(range(1, min(rl, SHORT) + 1)) + ([rl] if rl > SHORT else []):
                    c = lc + 1 + elias_bits(ln) + pen
                    if c < cp_cost[i + ln]:
                        cp_cost[i + ln], cp_from[i + ln], cp_off[i + ln] = c, i, o
                        cp_prev[i + ln], cp_rep[i + ln] = 0, True
        start = min(lc, cc)
        if start < INF and cands[i]:
            prev = 0 if lc <= cc else 1
            for o, ml in cands[i]:
                head = start + elias_bits((o - 1) // 128 + 1) + 8 + pen
                for ln in list(range(2, min(ml, SHORT) + 1)) + ([ml] if ml > SHORT else []):
                    c = head + elias_bits(ln - 1)
                    if c < cp_cost[i + ln]:
                        cp_cost[i + ln], cp_from[i + ln], cp_off[i + ln] = c, i, o
                        cp_prev[i + ln], cp_rep[i + ln] = prev, False
    # the blocks, back from the end
    blocks = []
    pos, kind = n, ("lit" if lit_cost[n] <= cp_cost[n] else "cp")
    while pos > 0:
        if kind == "lit":
            s = lit_from[pos]
            blocks.append(("lit", s, pos - s, 0))
            pos, kind = s, "cp"
        else:
            s = cp_from[pos]
            blocks.append(("rep" if cp_rep[pos] else "new", s, pos - s, cp_off[pos]))
            kind = ("lit", "cp", "cp")[cp_prev[pos]]
            pos = s
    blocks.reverse()
    return emit(data, blocks)


class _Bits:
    def __init__(self) -> None:
        self.out = bytearray()
        self.mask = 0
        self.at = 0
        self.back = False

    def bit(self, v: int) -> None:
        if self.back:
            if v:
                self.out[-1] |= 1
            self.back = False
            return
        if not self.mask:
            self.mask = 0x80
            self.at = len(self.out)
            self.out.append(0)
        if v:
            self.out[self.at] |= self.mask
        self.mask >>= 1

    def byte(self, v: int) -> None:
        self.out.append(v)

    def elias(self, v: int, invert: bool = False) -> None:
        i = 1 << (v.bit_length() - 1)
        while i > 1:
            i >>= 1
            self.bit(0)
            self.bit((not (v & i)) if invert else bool(v & i))
        self.bit(1)


def emit(data: bytes, blocks: list[tuple[str, int, int, int]]) -> bytes:
    w = _Bits()
    last, first, after_lit = 1, True, False
    for kind, s, ln, off in blocks:
        if kind == "lit":
            assert not after_lit or first, "two literal blocks in a row"
            if not first:
                w.bit(0)
            w.elias(ln)
            for b in data[s:s + ln]:
                w.byte(b)
            after_lit = True
        elif kind == "rep":
            assert after_lit and off == last, "a copy from the last offset not after literals"
            w.bit(0)
            w.elias(ln)
            after_lit = False
        else:
            assert not first and ln >= 2
            w.bit(1)
            w.elias((off - 1) // 128 + 1, invert=True)
            w.byte((127 - (off - 1) % 128) << 1)
            w.back = True
            w.elias(ln - 1)
            last, after_lit = off, False
        first = False
    w.bit(1)
    w.elias(256, invert=True)
    return bytes(w.out)


def unpack(src: bytes) -> bytes:
    """dzx0_standard's reading, in Python (the reference for msx/photo.asm pz_unz)."""
    out = bytearray()
    pos = 0
    bits = 0x80

    def bit() -> int:
        nonlocal bits, pos
        bits <<= 1
        if bits & 0xFF == 0:
            b = src[pos]
            pos += 1
            bits = (b << 1) | 1
        v = bits >> 8 & 1
        bits &= 0xFF
        return v

    def elias(invert: bool = False, first: int | None = None) -> int:
        v = 1
        ctl = first if first is not None else bit()
        while not ctl:
            v = v << 1 | (bit() ^ (1 if invert else 0))
            ctl = bit()
        return v

    last = 1
    state = "lit"
    while True:
        if state == "lit":
            n = elias()
            out += src[pos:pos + n]
            pos += n
            state = "new" if bit() else "rep"
        elif state == "rep":
            n = elias()
            for _ in range(n):
                out.append(out[-last])
            state = "new" if bit() else "lit"
        else:
            msb = elias(invert=True)
            if msb == 256:
                return bytes(out)
            lsb = src[pos]
            pos += 1
            last = msb * 128 - (lsb >> 1)
            n = elias(first=lsb & 1) + 1
            for _ in range(n):
                out.append(out[-last])
            state = "new" if bit() else "lit"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("op", choices=("pack", "unpack"))
    ap.add_argument("input", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--stride", type=int, default=0, help="also try the offsets of 1-3 lines of this many bytes")
    ap.add_argument("--max-offset", type=int, default=MAX_OFFSET, help="the farthest copy (msx/photo.asm: 256)")
    ap.add_argument("--penalty", type=int, default=0, help="bits added to every copy's cost (fewer, longer copies)")
    a = ap.parse_args(argv[1:])
    data = a.input.read_bytes()
    res = pack(data, a.stride, a.penalty, a.max_offset) if a.op == "pack" else unpack(data)
    if a.op == "pack" and unpack(res) != data:
        print("error: the packed stream does not unpack to the input", file=sys.stderr)
        return 1
    a.output.write_bytes(res)
    print(f"{a.output}: {len(data)} -> {len(res)} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
