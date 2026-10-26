#!/usr/bin/env python3
"""Bank test cartridge for a 2 MiB Konami SCC MegaROM: msx/banktest.asm in bank 0, every bank
filled so that one byte tells which bank a window shows and every byte can be checked without a
table (written 2026-10-26 to try the 2 MiB ROM on the user's devices: docs/ROM_BUDGET.md 6.1).

Bank b holds f(b, o) = b * 3Bh + (o >> 8) * 1Dh + (o & FFh) (low 8 bits) at its offset o; bank 0
only where the code leaves room. 3Bh is odd, so the byte at 0020h names one bank:
b = -13 * (byte - 20h), 13 * 3Bh being FFh. The byte at 1720h (below the SCC's 9800h when the
bank is at 8000h) is 9Bh more in every bank.

    msxbanktest.py OUT.rom [--id TEXT]

The id is shown on screen, to tell photos of two builds apart. Needs z80asm 1.8 (as
tools/mkrom.py).
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = 0x2000
BANKS = 256
TAG, TAG2 = 0x0020, 0x1720
RAM_ROOM = {"rc_chk": 0x80, "rc_spd": 0x80}     # msx/banktest.asm RC_CHK, RC_SPD
SCC_TESTS = (0x5A, 0xBF, 0x24, 0x89)            # msx/banktest.asm scc: the values stored at 9800h


def fill(bank: int, offset: int) -> int:
    return (bank * 0x3B + (offset >> 8) * 0x1D + (offset & 0xFF)) & 0xFF


def shown(byte: int) -> int:
    """The bank whose byte at TAG is `byte` (msx/banktest.asm tag_rd)."""
    return -13 * (byte - TAG) & 0xFF


def bank_data(bank: int) -> bytes:
    return bytes(fill(bank, o) for o in range(BANK))


def assemble(ident: str) -> tuple[bytes, dict[str, int]]:
    """msx/banktest.asm with tx_id = ident: the code and its labels."""
    if not re.fullmatch(r"[A-Z0-9.-]{1,9}", ident):
        raise SystemExit(f"--id {ident!r}: 1-9 capitals, digits, '-' or '.'")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        (work / "banktest_id.inc").write_text(f'tx_id:      db "{ident}", 0\n')
        code = work / "banktest.bin"
        r = subprocess.run(["z80asm", "-I", str(ROOT / "msx"), "-L", "-o", str(code),
                            str(ROOT / "msx" / "banktest.asm")], capture_output=True, text=True, cwd=work)
        if r.returncode != 0 or not code.exists():
            raise SystemExit(r.stderr or "z80asm failed")
        labels = {m[1]: int(m[2], 16) for m in re.finditer(r"^(\w+):\s+equ \$([0-9a-f]+)$", r.stderr, re.M)}
        return code.read_bytes(), labels


def image(code: bytes, labels: dict[str, int]) -> bytes:
    if code[:2] != b"AB" or code[0x10:0x18] != b"ROM_KON5" or code[TAG] != fill(0, TAG):
        raise SystemExit("msx/banktest.asm: the header, the mapper's tag or bank 0's tag moved")
    if len(code) > TAG2:
        raise SystemExit(f"msx/banktest.asm: {len(code)} bytes reach bank 0's second tag at {TAG2:04X}h")
    for name, room in RAM_ROOM.items():
        size = labels[name + "_end"] - labels[name]
        if size > room:
            raise SystemExit(f"msx/banktest.asm: {name} takes {size} bytes in RAM ({room} free)")
    banks = [bytearray(bank_data(b)) for b in range(BANKS)]
    banks[0][:len(code)] = code
    rom = b"".join(banks)
    # (with a value stored at 9800h a MegaRAM selects that bank at 8000h, and a Konami SCC
    # mapper without the chip shows the ROM there: neither may give the value back)
    for v in SCC_TESTS:
        if v in (rom[v * BANK + 0x1800], *(rom[b * BANK + 0x1800] for b in (0x3F, 0x7F, 0xBF, 0xFF))):
            raise SystemExit(f"a ROM byte at 9800h would read as the SCC's {v:02X}h")
    # (the MSX Pico+ firmware starts a Konami SCC ROM holding "OPLL" as an FM-PAC game, without
    # its SCC: docs/MSX_ARCHITECTURE.md)
    if b"OPLL" in rom:
        raise SystemExit(f"\"OPLL\" at {rom.index(b'OPLL'):06X}h")
    return rom


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--id", default="BT2M", help="shown on screen (1-9 capitals, digits, '-', '.')")
    a = ap.parse_args()
    rom = image(*assemble(a.id))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(rom)
    print(f"{a.out}: {len(rom) // 1024} KiB, {BANKS} banks, id {a.id}")


if __name__ == "__main__":
    main()
