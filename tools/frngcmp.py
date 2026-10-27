#!/usr/bin/env python3
"""Compares the MSX port's shooting range (FRNG) with the original, FRNG frame by FRNG frame.

The reference is tools/amigaemu.py frng --trace-ram (JSON lines: FRNG's variables $B00-$BC5, the
globals $8000-$80FF and FRNG's code blocks at the start of every FRNG frame; the last line
{"result": {"dummy", "correct", "timer", "timeout", "frames"}, "rating": {"text", "table", ...}}
when $1EA00 returned and $8420 set the result up). The port's trace comes from
tools/openmsx_rc2.tcl rc2_fr_drive or rc2_fr_arm: a first line "# D000 DC00 <fr_code>", then per
FRNG frame three blocks as hex (D000h-D0C5h: the AM mirror of $B00-$BC5; DC00h-DCFFh: AG; fr_code:
PIECES below), then "# result DUMMY CORRECT TIMEOUT" (the mirror's $B06, $B04, $804C at fr_done)
and "# rating OFFSET" (the word at ac_diff less diff_tab at fr_rated) when the stage returned. Every
block keeps the mirror's rule (words little-endian, the byte at A at A ^ 1) and is read swapped
back, as tools/tracecmp.py does. Both traces must play the same drive (tools/drivejoy.py's file:
amigaemu --drive and the procs' 'script'). The fields are listed in analysis/frng_ram.tsv. The
rating is compared as an offset into the hit-point tables: the Amiga's $8060 less $C716 (SHARP),
the port's ac_diff less diff_tab; 0 SHARP, 8 GOOD, 16 FAIR, 24 POOR or a time out.

Prints the first differing frames ("FRNG frame F (keys): name amiga/msx, ..."), then "N FRNG
frames compared (A Amiga, M MSX), F fields: D differ", "result: Amiga ..., MSX ..." and
"rating: Amiga ..., MSX ...". Exit status 0 only when no field differs, both traces have the same
rows, the same result (the counts are compared only when no time out ended the stage: FRNG then
returns through message_queue with D0 and D1 left over) and the same rating.

usage: frngcmp.py AMIGA.jsonl MSX.txt [--fields analysis/frng_ram.tsv] [--skip NAME,...] [--show N]
       (--skip: fields left out by name or name prefix, e.g. 'score' for a range reached from a
       played level, 'd' for every descriptor)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = HERE.parent / "analysis" / "frng_ram.tsv"
VARS0, VARS_LEN, GLOB0 = 0x0B00, 0xC6, 0x8000
# fr_code: FRNG's code-area state the port keeps, these Amiga ranges one after the other
PIECES = ((0x1EB46, 6), (0x1F246, 2), (0x1F46C, 2), (0x1F502, 10), (0x1F60E, 506))
FR_CODE_LEN = sum(n for _, n in PIECES)
SHARP = 0xC716                     # the SHARP hit-point table; $8060 = SHARP + 24 - 8 x rating


def fields(path: Path = FIELDS) -> list[dict]:
    out = []
    for line in path.read_text().splitlines():
        line = line.split(";", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        f = {"addr": int(parts[0], 16), "size": int(parts[1]), "name": parts[2]}
        opt = dict(p.split("=", 1) for p in parts[3:] if "=" in p)
        if "if" in opt:
            f["if"] = int(opt["if"], 16)
        out.append(f)
    return out


def swapped(blk: bytes) -> bytes:
    """The mirror's words little-endian (the byte at A at A ^ 1), swapped back to the Amiga's."""
    b = bytearray(blk + b"\0" * (len(blk) & 1))
    b[0::2], b[1::2] = b[1::2], b[0::2]
    return bytes(b)


def piece_offset(addr: int) -> int | None:
    off = 0
    for base, n in PIECES:
        if base <= addr < base + n:
            return off + addr - base
        off += n
    return None


def amiga_bytes(row: dict, addr: int, size: int) -> bytes:
    if VARS0 <= addr < VARS0 + VARS_LEN:
        return bytes.fromhex(row["vars"])[addr - VARS0:addr - VARS0 + size]
    if GLOB0 <= addr < GLOB0 + 0x100:
        return bytes.fromhex(row["glob"])[addr - GLOB0:addr - GLOB0 + size]
    for lo, hexs in row["code"].items():
        lo = int(lo, 16)
        blk = bytes.fromhex(hexs)
        if lo <= addr and addr + size <= lo + len(blk):
            return blk[addr - lo:addr - lo + size]
    raise KeyError(f"${addr:x} is in no block of the Amiga trace")


def msx_bytes(m: dict, addr: int, size: int) -> bytes:
    if VARS0 <= addr < VARS0 + VARS_LEN:
        return m["vars"][addr - VARS0:addr - VARS0 + size]
    if GLOB0 <= addr < GLOB0 + 0x100:
        return m["glob"][addr - GLOB0:addr - GLOB0 + size]
    off = piece_offset(addr)
    if off is None:
        raise KeyError(f"${addr:x} is in no block of the MSX trace")
    return m["code"][off:off + size]


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
                raise SystemExit(f"{path}: rows without the blocks (run amigaemu.py frng with --trace-ram)")
            rows.append(r)
    return rows, end


def read_msx(path: Path) -> tuple[list[dict], tuple | None, int | None]:
    rows, result, rating = [], None, None
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        if line.startswith("#"):
            p = line[1:].split()
            if p and p[0] == "result":
                result = tuple(int(v) for v in p[1:4])
            elif p and p[0] == "rating":
                rating = int(p[1])
            continue
        v, g, c = line.split()
        rows.append({"vars": swapped(bytes.fromhex(v)), "glob": swapped(bytes.fromhex(g)),
                     "code": swapped(bytes.fromhex(c))})
    return rows, result, rating


def compare(amiga: Path, msx: Path, show: int, field_file: Path = FIELDS, skip: tuple[str, ...] = ()) -> int:
    fl = [f for f in fields(field_file) if not any(f["name"] == s or f["name"].startswith(s + ".")
                                                     or (s == "d" and f["name"][:1] == "d" and f["name"][1:3].isdigit())
                                                     for s in skip)]
    ref, end = read_amiga(amiga)
    got, result, rating = read_msx(msx)
    n = min(len(ref), len(got))
    bad, first = 0, None
    for i in range(n):
        a, m = ref[i], got[i]
        diff = []
        for f in fl:
            if "if" in f and not amiga_bytes(a, f["if"], 1)[0]:
                continue
            va = int.from_bytes(amiga_bytes(a, f["addr"], f["size"]), "big")
            vm = int.from_bytes(msx_bytes(m, f["addr"], f["size"]), "big")
            if va != vm:
                diff.append(f"{f['name']} {va:#x}/{vm:#x}")
        if diff:
            bad += 1
            first = a.get("frame", i) if first is None else first
            if bad <= show:
                print(f"FRNG frame {a.get('frame', i)} ({a.get('keys') or '-'}): " + ", ".join(diff[:12])
                      + (f" (+{len(diff) - 12})" if len(diff) > 12 else ""))
    print(f"{n} FRNG frames compared ({len(ref)} Amiga, {len(got)} MSX), {len(fl)} fields: {bad} differ"
          + (f", first at {first}" if first is not None else ""))
    ok = bad == 0 and len(ref) == len(got)
    ra = None if end is None else end["result"]
    if ra is not None or result is not None:
        want = None if ra is None else (ra["dummy"], ra["correct"], ra["timeout"])
        print(f"result: Amiga {want}, MSX {result}" + (" (time out: the counts not compared)" if want and want[2] else ""))
        if want is None or result is None:
            ok = False
        elif want[2]:
            ok = ok and result[2] == want[2]
        else:
            ok = ok and result == want
    rt = None if end is None or not end.get("rating") else int(end["rating"]["table"], 16) - SHARP
    if rt is not None or rating is not None:
        print(f"rating: Amiga {rt}, MSX {rating} ($8060 - $C716, ac_diff - diff_tab: 0 SHARP, 8 GOOD, 16 FAIR, "
              f"24 POOR or a time out)")
        ok = ok and rt == rating
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("amiga", type=Path)
    ap.add_argument("msx", type=Path)
    ap.add_argument("--fields", type=Path, default=FIELDS)
    ap.add_argument("--skip", default="", help="fields left out, by name or prefix (comma-separated)")
    ap.add_argument("--show", type=int, default=10, help="differing frames to print")
    a = ap.parse_args()
    return compare(a.amiga, a.msx, a.show, a.fields, tuple(filter(None, a.skip.split(","))))


if __name__ == "__main__":
    raise SystemExit(main())
