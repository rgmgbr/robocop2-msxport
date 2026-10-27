#!/usr/bin/env python3
"""ByteKiller decruncher: the game's own $124A6 transcribed, with its two helpers ($12528 reads the
next long, $12534 a field of bits), as REA (Ghidra provider) lists them on the level-1 RAM image.

After the loader, the game decrunches two files with $124A6, from A0 to A1:
  FRNG (the shooting range, FRNG_15)       $1E980 -> $1EA00-$485D9 (93,224 -> 170,970 bytes)
  PUZL (Brainstorm, disk 1's PUZL_13)      $17080 -> $17100-$32CDF (76,012 -> 113,632 bytes,
                                           the bytes of disk 2's plain PUZL_25)

The file (big-endian):
  +0   long  P: the stream's length in bytes (a multiple of 4)
  +4   long  U: the decrunched length
  +8   long  C: the checksum: C xor every long of the stream = 0
  +12        the stream, P bytes, read one long at a time from its end down to +12
Bits leave each long from bit 0 up. In the first long read (the file's last) the highest set bit is
a marker: only the bits below it are data. Every later long gives all 32 bits ($12528 rotates a
marker into bit 31). A field of n bits is read most significant bit first. The output is written
downwards, from A1 + U to A1, by these commands:
  0 0  n(3)          n + 1 literal bytes, 8 bits each
  0 1  o(8)          2 bytes, each copied from o bytes above it
  1 00 o(9)          3 bytes from o above
  1 01 o(10)         4 bytes from o above
  1 10 n(8) o(12)    n + 1 bytes from o above
  1 11 n(8)          n + 9 literal bytes
A copy goes byte by byte downwards, so an offset below the count repeats the last o bytes. The
commands run until the output reaches A1 (cmpa.l A2,A1 after each command). D5, the checksum xor
every long read, is then 0 for an intact file: $124A6 returns it untested (its rts at $12526), and
decrunch() refuses any other value.

The original would read or write outside its buffers on a damaged stream: this decruncher refuses
that instead (a copy from offset 0 or from beyond the output's end, a command that writes below
the output's start, a read before the stream's start), and decrunch() refuses a checksum that is
not 0.

usage: bytekiller.py IN [OUT]
  decrunches IN, prints the lengths, the longs read, the checksum and the output's sha256, and
  writes OUT; exit status 1 for a damaged file (nothing written)
library: decrunch(data) -> bytes (checked); unpack(data) -> Unpacked (the checksum not checked)
"""
from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path
from typing import NamedTuple

HEADER = 12


class CrunchError(ValueError):
    """A stream that would make the original leave its buffers, or a checksum that is not 0."""


class Unpacked(NamedTuple):
    data: bytes         # the decrunched bytes
    checksum: int       # D5 at the end: 0 for an intact file
    longs_read: int     # longs of the stream read (all of them for the game's files)
    longs: int          # longs in the stream


def unpack(src: bytes) -> Unpacked:
    """Decrunches src as $124A6 does; the checksum is returned, not checked."""
    if len(src) < HEADER + 4:
        raise CrunchError(f"{len(src)} bytes: too short for the header and a long")
    plen, ulen, chk = struct.unpack_from(">III", src)
    if plen < 4 or plen % 4 or HEADER + plen > len(src):
        raise CrunchError(f"a stream of {plen} bytes does not fit the {len(src) - HEADER} after the header")
    stream = struct.unpack_from(f">{plen // 4}I", src, HEADER)
    out = bytearray(ulen)
    a0 = len(stream)                # the next long read is stream[a0 - 1] (move.l -(a0),d0)
    a2 = ulen                       # the output pointer, from A1
    d5 = chk

    def next_long() -> int:         # $12528: eor.l d0,d5; move #$10,ccr; roxr.l #1,d0
        nonlocal a0, d0, d5
        if a0 == 0:
            raise CrunchError("the stream ran out before the output was whole")
        a0 -= 1
        v = stream[a0]
        d5 ^= v
        d0 = v >> 1 | 0x80000000
        return v & 1

    def bit() -> int:               # lsr.l #1,d0; zero: the marker left, the bit comes from the next long
        nonlocal d0
        c = d0 & 1
        d0 >>= 1
        return c if d0 else next_long()

    def bits(n: int) -> int:        # $12534: n bits, the first one read the highest (roxl.l #1,d2)
        v = 0
        for _ in range(n):
            v = v << 1 | bit()
        return v

    def literal(n: int) -> None:
        nonlocal a2
        if n > a2:
            raise CrunchError(f"{n} literal bytes at {a2}: below the output's start")
        for _ in range(n):
            a2 -= 1
            out[a2] = bits(8)

    def copy(n: int, o: int) -> None:   # subq.w #1,a2; move.b (a2,d2.w),(a2); dbf d3
        nonlocal a2
        if n > a2:
            raise CrunchError(f"a copy of {n} bytes at {a2}: below the output's start")
        if o == 0 or a2 - 1 + o >= ulen:
            raise CrunchError(f"a copy from offset {o} at {a2}: a byte the output does not hold yet")
        for _ in range(n):
            a2 -= 1
            out[a2] = out[a2 + o]

    a0 -= 1                         # the first long: move.l -(a0),d0; eor.l d0,d5 (its marker stays)
    d0 = stream[a0]
    d5 ^= d0
    while True:
        if bit():
            k = bits(2)
            if k == 3:
                literal(bits(8) + 9)
            elif k == 2:
                n = bits(8) + 1
                copy(n, bits(12))
            else:
                copy(k + 3, bits(9 + k))
        elif bit():
            copy(2, bits(8))
        else:
            literal(bits(3) + 1)
        if a2 <= 0:                 # cmp.l a2,a1; blt: until the output's start
            break
    return Unpacked(bytes(out), d5, len(stream) - a0, len(stream))


def decrunch(src: bytes) -> bytes:
    """The decrunched bytes of a ByteKiller file; CrunchError unless its checksum comes to 0."""
    u = unpack(src)
    if u.checksum:
        raise CrunchError(f"checksum {u.checksum:08x}, not 0: a damaged file")
    return u.data


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print(__doc__, file=sys.stderr)
        return 2
    src = Path(argv[1]).read_bytes()
    try:
        u = unpack(src)
    except CrunchError as e:
        print(f"{argv[1]}: {e}", file=sys.stderr)
        return 1
    plen = struct.unpack_from(">I", src)[0]
    print(f"{argv[1]}: {HEADER} + {plen} -> {len(u.data)} bytes, {u.longs_read} of {u.longs} longs read, "
          f"checksum {u.checksum:08x}, sha256 {hashlib.sha256(u.data).hexdigest()}")
    if u.checksum:
        print(f"{argv[1]}: the checksum is not 0: a damaged file, nothing written", file=sys.stderr)
        return 1
    if len(argv) == 3:
        Path(argv[2]).parent.mkdir(parents=True, exist_ok=True)
        Path(argv[2]).write_bytes(u.data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
