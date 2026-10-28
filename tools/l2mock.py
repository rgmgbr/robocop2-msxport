#!/usr/bin/env python3
"""The MSX trace a perfect port would give, made from a bench reference: a self-test of a field file
and of tools/tracecmp.py --ram without an emulator (the level-2 plan, 4.1).

A bench row (tools/amigaemu.py game --trace-ram: the game's variables $B00-$16EB, the globals
$8000-$80FF, the code-area blocks) becomes one line of tools/openmsx_rc2.tcl rc2_drive_hit's trace:
the five hex blocks D000h (AM, 0BECh bytes), DC00h (AG), DD00h-DFFFh, EE00h-F0FFh and E900h-E9FFh,
words little-endian as the port keeps them. AM and AG hold the bench's blocks as they are; every
field of the field file with an msx= home is placed at its home, a ptr= field as an offset from the
label's value. --mutate NAME:ROW:VALUE writes VALUE for field NAME from row ROW on (the check that
tracecmp catches a wrong field).

The labels (pointer fields: diff_tab, mk_tab2) come from --labels, or are the mock's own (MOCK_LABELS),
written next to the output as OUT.labels for tracecmp's --labels.

usage: l2mock.py AMIGA.jsonl OUT.txt [--fields analysis/amiga_ram_l2.tsv] [--labels FILE]
                 [--mutate NAME:ROW:VALUE]
then:  tracecmp.py --ram --fields analysis/amiga_ram_l2.tsv --labels OUT.txt.labels AMIGA.jsonl OUT.txt
       ("N game frames compared (N Amiga, N MSX), 1022 fields: 0 differ")
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tracecmp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIELDS_L2 = ROOT / "analysis" / "amiga_ram_l2.tsv"
BLOCKS = dict(zip(tracecmp.MSX_DUMPS, (0xBEC, 0x100, 0x300, 0x300, 0x100)))   # rc2_drive_hit's dumps: base, length
MOCK_LABELS = {"diff_tab": 0x9000, "mk_tab2": 0xA123}


def mock_lines(fields: list[dict], labels: dict[str, int], rows: Iterable[str],
               mutate: tuple[str, int, int] | None = None) -> Iterator[str]:
    """The MSX trace lines for the bench rows (JSON lines) under the field list fields
    (tracecmp.fields)."""
    for i, line in enumerate(rows):
        if not line.strip():
            continue
        row = json.loads(line)
        view = {b: bytearray(n) for b, n in BLOCKS.items()}     # the swapped-back view tracecmp reads
        view[0xD000][:] = bytes.fromhex(row["ram"])[:BLOCKS[0xD000]]
        view[0xDC00][:] = bytes.fromhex(row["glob"])[:BLOCKS[0xDC00]]
        for f in fields:
            if f["msx"] is None:
                continue
            try:
                va = tracecmp.amiga_value(row, f["addr"], f["size"])
            except KeyError:
                continue
            size = f["size"]
            if "ptr" in f:
                base, label = f["ptr"]
                va, size = (va - base + labels.get(label, 0)) & 0xFFFF, 2
            if mutate and f["name"] == mutate[0] and i >= mutate[1]:
                va = mutate[2] & ((1 << 8 * size) - 1)
            m = f["msx"]
            for b, n in BLOCKS.items():
                if b <= m and m + size <= b + n:
                    view[b][m - b:m - b + size] = va.to_bytes(size, "big")
                    break
            else:
                raise ValueError(f"{f['name']}: msx={m:04X}h is in no dumped block")
        yield " ".join(tracecmp.swapped(bytes(view[b])).hex() for b in BLOCKS)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("amiga", type=Path, help="a bench reference (--trace-ram JSON lines)")
    ap.add_argument("out", type=Path, help="the mock MSX trace")
    ap.add_argument("--fields", type=Path, default=FIELDS_L2)
    ap.add_argument("--labels", type=Path, help="the label file (default: the mock's, written to OUT.labels)")
    ap.add_argument("--mutate", help="NAME:ROW:VALUE (a field's name as tracecmp prints it, e.g. vat_phase[3].0)")
    a = ap.parse_args()
    mutate = None
    if a.mutate:
        name, row, value = a.mutate.rsplit(":", 2)
        mutate = (name, int(row), int(value, 0))
    fl = tracecmp.fields(a.fields)
    if mutate and mutate[0] not in {f["name"] for f in fl}:
        ap.error(f"--mutate: no field {mutate[0]!r} in {a.fields}")
    if a.labels:
        labels = tracecmp.labels(a.labels)
    else:
        labels = MOCK_LABELS
        Path(f"{a.out}.labels").write_text("".join(f"{k}:\tequ ${v:04X}\n" for k, v in labels.items()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with a.amiga.open() as fi, a.out.open("w") as fo:
        for line in mock_lines(fl, labels, fi, mutate):
            fo.write(line + "\n")
            n += 1
    print(f"{a.out}: {n} rows, {len(fl)} fields" + (f", {mutate[0]} = {mutate[2]:#x} from row {mutate[1]}" if mutate else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
