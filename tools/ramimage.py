#!/usr/bin/env python3
"""Builds images of the Amiga RAM during a level, to open in REA/Ghidra.

Each file goes to its destination from the loader name table, in the order given (a later file
overwrites an earlier one where they overlap). A name takes the file's first entry (PUZL: disk 1's
copy, crunched, at $17080); a file can also be named by its extracted file's stem (PUZL_25: disk 2's
plain copy, at $17100). Outputs:
  <out>_full.bin : RAM from $0 to $7FFFF; $0 holds JMP $8000 (REA entry = 0x0)
  <out>_8000.bin : RAM from $8000 to $7FFFF (REA entry = 0x8000)

NAME@ADDR (hex) places the file decrunched instead, at ADDR: a ByteKiller file that the game's $124A6
decrunches after the loader (FRNG: loaded at $1E980, decrunched into $1EA00), through
tools/bytekiller.py, which refuses a checksum that is not 0. The crunched copy is not placed.

usage: ramimage.py build/extracted build/ram/level1 MU1 DATAL1 SPERMA PERMA RB1
       ramimage.py build/extracted build/ram/puzl RB1 MU1 DATAL1 SPERMA PERMA PUZL_25
       (the level-1 image with Brainstorm's PUZL at $17100-$32CDF: docs/AMIGA_ANALYSIS.md, Brainstorm)
       ramimage.py build/extracted build/ram/frng RB1 MU1 DATAL1 SPERMA PERMA FRNG@1ea00
       (the level-1 image with the shooting range's FRNG decrunched at $1EA00-$485D9:
       docs/AMIGA_ANALYSIS.md, the shooting range)
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bytekiller  # noqa: E402

CHIP = 0x80000


def main(argv: list[str]) -> int:
    if len(argv) < 4:
        print(__doc__, file=sys.stderr)
        return 2
    x, out = Path(argv[1]), Path(argv[2])
    files = {}
    for f in json.loads((x / "manifest.json").read_text())["files"]:
        files.setdefault(f["name"], f)  # first entry (PUZL of disk 1)
        files.setdefault(Path(f["file"]).stem, f)  # by its file (PUZL_25: disk 2's)
    ram = bytearray(CHIP)
    ram[0:6] = bytes.fromhex("4ef900008000")  # JMP $8000
    for path, addr in (("boot/loader_100.bin", 0x100), ("boot/loader_300.bin", 0x300), ("boot/main_8000.bin", 0x8000)):
        d = (x / path).read_bytes()
        ram[addr:addr + len(d)] = d
    struct.pack_into(">I", ram, 0xC0, 0x100)
    for item in argv[3:]:
        name, at, dest = item.partition("@")
        f = files[name]
        d = (x / f["file"]).read_bytes()
        a = f["load_address"]
        if at:                                  # decrunched, as $124A6 does after the loader
            d, a = bytekiller.decrunch(d), int(dest, 16)
        if a + len(d) > CHIP:
            raise SystemExit(f"{item}: ${a:05x}-${a + len(d):05x} does not fit in ${CHIP:05x} bytes of RAM")
        ram[a:a + len(d)] = d
        print(f"  {name:7} ${a:05x}-${a + len(d):05x}" + (" (decrunched)" if at else ""))
    out.parent.mkdir(parents=True, exist_ok=True)
    Path(f"{out}_full.bin").write_bytes(ram)
    Path(f"{out}_8000.bin").write_bytes(ram[0x8000:])
    print(f"{out}_full.bin, {out}_8000.bin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
