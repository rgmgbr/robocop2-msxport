#!/usr/bin/env python3
"""Compares the MSX port's Brainstorm (PUZL) with the original, PUZL frame by PUZL frame.

The reference is tools/amigaemu.py puzl --trace-ram (JSON lines: the stage's variables, the
globals and the board table at the start of every PUZL frame; the last line {"result": D0,
"frames": n} when the stage returned). The port's trace comes from tools/openmsx_rc2.tcl
rc2_pz_drive or rc2_pz_arm (a first line "# D000 DC00 <pz_boards>", then per PUZL frame the
three blocks as hex, and "# result N" when the stage returned). Both must play the same script
(amigaemu --drive FILE and the procs' 'script': tools/drivejoy.py's file). The fields are listed
in analysis/puzl_ram.tsv; the MSX mirror keeps words little-endian (the byte at A at A ^ 1), read
swapped back here as tools/tracecmp.py does.

Prints the first differing frames ("PUZL frame F (keys): name amiga/msx, ..."), then
"N PUZL frames compared (A Amiga, M MSX), F fields: D differ" and "result: Amiga R, MSX R".
Exit status 0 only when no field differs, both traces have the same rows and the same result.

usage: puzlcmp.py AMIGA.jsonl MSX.txt [--fields analysis/puzl_ram.tsv] [--skip NAME,...] [--show N]
       (--skip: fields left out by name, e.g. 'score' for a stage reached from a played level 1;
       'boards' leaves out the whole table)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = HERE.parent / "analysis" / "puzl_ram.tsv"
VARS0, GLOB0 = 0x0B00, 0x8000        # the Amiga's blocks: PUZL's variables, the globals
TABLE_PTR = "173d4"                  # the Amiga row's code block holding the board table's address


def fields(path: Path = FIELDS) -> list[dict]:
    out = []
    for line in path.read_text().splitlines():
        line = line.split(";", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        addr, size, name = parts[0], int(parts[1]), parts[2]
        opt = dict(p.split("=", 1) for p in parts[3:] if "=" in p)
        if addr == "boards":
            out += [{"addr": ("boards", k), "size": 1, "name": f"{name}[{k // 94}][{k % 94}]"} for k in range(size)]
            continue
        f = {"addr": int(addr, 16), "size": size, "name": name, "skip0": "skip0" in parts[3:]}
        if "ptr" in opt:
            a, m = opt["ptr"].split(":")
            f["ptr"] = (a, m)
        out.append(f)
    return out


def swapped(blk: bytes) -> bytes:
    """The mirror's words little-endian (the byte at A at A ^ 1), swapped back to the Amiga's."""
    b = bytearray(blk + b"\0" * (len(blk) & 1))
    b[0::2], b[1::2] = b[1::2], b[0::2]
    return bytes(b)


def amiga_value(row: dict, addr, size: int) -> int:
    if isinstance(addr, tuple):
        return bytes.fromhex(row["boards"])[addr[1]]
    if VARS0 <= addr < VARS0 + 0x22:
        b = bytes.fromhex(row["vars"])[addr - VARS0:addr - VARS0 + size]
    elif GLOB0 <= addr < GLOB0 + 0x100:
        b = bytes.fromhex(row["glob"])[addr - GLOB0:addr - GLOB0 + size]
    else:
        raise KeyError(f"${addr:x} is in no block of the Amiga trace")
    return int.from_bytes(b, "big")


def msx_value(blocks: dict, addr, size: int) -> int:
    if isinstance(addr, tuple):
        return blocks["boards"][addr[1]]
    if VARS0 <= addr < VARS0 + 0x22:
        b = blocks["vars"][addr - VARS0:addr - VARS0 + size]
    elif GLOB0 <= addr < GLOB0 + 0x100:
        b = blocks["glob"][addr - GLOB0:addr - GLOB0 + size]
    else:
        raise KeyError(f"{addr:x} is in no block of the MSX trace")
    return int.from_bytes(b, "big")


def read_amiga(path: Path) -> tuple[list[dict], dict | None]:
    rows, end = [], None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if "result" in r:
            end = r
        else:
            if "vars" not in r:
                raise SystemExit(f"{path}: rows without the blocks (run amigaemu.py puzl with --trace-ram)")
            rows.append(r)
    return rows, end


def read_msx(path: Path) -> tuple[list[dict], int, int | None]:
    rows, boards_at, result = [], 0, None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        if line.startswith("#"):
            p = line[1:].split()
            if p and p[0] == "result":
                result = int(p[1])
            elif len(p) == 3:
                boards_at = int(p[2], 16)
            continue
        v, g, b = line.split()
        rows.append({"vars": swapped(bytes.fromhex(v)), "glob": swapped(bytes.fromhex(g)),
                     "boards": bytes.fromhex(b)})
    return rows, boards_at, result


def compare(amiga: Path, msx: Path, show: int, field_file: Path = FIELDS, skip: tuple[str, ...] = ()) -> int:
    fl = [f for f in fields(field_file) if f["name"].split("[", 1)[0] not in skip]
    ref, end = read_amiga(amiga)
    got, boards_at, result = read_msx(msx)
    n = min(len(ref), len(got))
    bad, first = 0, None
    for i in range(n):
        a, m = ref[i], got[i]
        pf = a.get("frame", i)           # (the PUZL frame: the row index plus the traces' 'from')
        table = int(a["code"][TABLE_PTR], 16)
        diff = []
        for f in fl:
            va, vm = amiga_value(a, f["addr"], f["size"]), msx_value(m, f["addr"], f["size"])
            if f.get("skip0") and va == 0:
                continue
            if "ptr" in f:
                ab, mb = f["ptr"]
                va = (va - (table if ab == "table" else int(ab, 16))) & 0xFFFF
                vm = ((vm & 0xFFFF) - (boards_at if mb == "table" else int(mb, 16))) & 0xFFFF
            if va != vm:
                diff.append(f"{f['name']} {va:#x}/{vm:#x}")
        if diff:
            bad += 1
            first = pf if first is None else first
            if bad <= show:
                print(f"PUZL frame {pf} ({a.get('keys') or '-'}): " + ", ".join(diff[:12])
                      + (f" (+{len(diff) - 12})" if len(diff) > 12 else ""))
    print(f"{n} PUZL frames compared ({len(ref)} Amiga, {len(got)} MSX), {len(fl)} fields: {bad} differ"
          + (f", first at {first}" if first is not None else ""))
    ra = None if end is None else end["result"]
    if ra is not None or result is not None:
        print(f"result: Amiga {ra}, MSX {result}")
    ok = bad == 0 and len(ref) == len(got) and ra == result
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("amiga", type=Path)
    ap.add_argument("msx", type=Path)
    ap.add_argument("--fields", type=Path, default=FIELDS)
    ap.add_argument("--skip", default="", help="fields left out, by name (comma-separated)")
    ap.add_argument("--show", type=int, default=10, help="differing frames to print")
    a = ap.parse_args()
    return compare(a.amiga, a.msx, a.show, a.fields, tuple(filter(None, a.skip.split(","))))


if __name__ == "__main__":
    raise SystemExit(main())
