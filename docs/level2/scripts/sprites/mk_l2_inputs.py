#!/usr/bin/env python3
"""Inputs for tools/msxsprites.py --level level2 (scratch, measurement only).

catalog_l2.json: level 1's catalogue refs (level1 / common) restricted to the frames level 2 also
holds and draws (MADEX = DATAL1's tail byte for byte, SPERMA, PERMA), in level 1's order and with
level 1's procs, so that the shared frames convert exactly as in level 1 (same animation groups,
same mirror partners); minus the refs no level-2 object draws or that the catalogue's scan got
wrong (REA, l2cat.py notes); then the frames REA found for level 2's own objects and the shared
frames level 1 never drew (obj04's torso aims 3/6/0 and its muzzle flash 4).
drawn_l2.json: level 1's bench coverage frames in the shared ranges (the same "drawn" groups).
usage: mk_l2_inputs.py CATALOG_L1 COV_L1 RAM_L2 OUTDIR"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

cat = json.loads(Path(sys.argv[1]).read_text())
cov = json.loads(Path(sys.argv[2]).read_text())["bobs"]
ram = Path(sys.argv[3]).read_bytes()
out = Path(sys.argv[4])
uw = lambda a: struct.unpack_from(">H", ram, a)[0]   # noqa: E731


def shared(a: int) -> bool:
    return 0x45250 <= a < 0x4B54C or 0x4B68A <= a < 0x5884E or 0x58850 <= a < 0x6FFA0


# refs level 2 never draws, or the scan's mistakes (REA: $CFB0 draws $57192 + $D066[aim] with
# BLTSIZE $D096[aim], 32 x 32 / 32 x 38, never 16 x 16; $CA78 draws $4E466 + $CB4A[i] with
# $CB56[i], never $4ED26 as 16 x 16; type 37 ($525CC) is not in level 2's lists)
DROP = {(0xD040, 16, 16), (0xCB0E, 16, 16), (0xE600, 32, 32)}
refs = []
for r in cat["refs"]:
    lv = (r["level"] or "").split("+")
    if not ({"level1", "common"} & set(lv)):
        continue
    if (r["site"], r["width"], r["height"]) in DROP:
        continue
    fr = [f for f in r["frames"] if shared(f)]
    if not fr:
        continue
    r = dict(r, frames=fr, level="level2")
    refs.append(r)


def ref(proc: str, frames: list[int], d4: int, why: str) -> dict:
    w, h = ((d4 & 63) - 1) * 16, d4 >> 6
    return {"proc": 0, "proc_name": proc, "site": 0, "base": frames[0], "adjust": [], "table": None, "ltable": None,
            "bltsize": d4, "width": w, "height": h, "frames": frames, "level": "level2", "evidence": why}


# shared frames level 1 lacks (obj04 $CFB0, REA tables $D066/$D096 and the flash $6C620 + 50h * aim)
t4 = [(0x57192 + uw(0xD066 + 2 * k), uw(0xD096 + 2 * k)) for k in range(8)]
refs.append(ref("obj04_update", sorted({a for a, d in t4 if d == 0x803}), 0x803, "REA $D066/$D096"))
refs.append(ref("obj04_update", [a for a, d in t4 if d == 0x983], 0x983, "REA $D066/$D096"))
refs.append(ref("obj04_flash", [0x6C620 + 0xA0 * k for k in range(8)], 0x402, "REA $CFF0: $6C620 + 50h * D3"))
# level 2's own objects (REA: procedure_assembly of each handler, tables read with read_bytes)
refs.append(ref("obj01_update", [0x3E810 + uw(0xC7E0 + 2 * k) for k in range(16)], 0x5C3, "REA $C7A2"))
refs.append(ref("obj01_update", [0x404D0, 0x404D0 + 0x1A4], 0x543, "REA $C7C0"))
refs.append(ref("obj02_update", [0x3D280, 0x3D910], 0xE04, "REA $C888/$C8F8"))
refs.append(ref("obj05_update", sorted({0x3BFC0 + uw(0xD19A + 2 * k) for k in range(11) if uw(0xD17C + 2 * k) == 0x402}),
                0x402, "REA $D162"))
refs.append(ref("obj05_update", sorted({0x3BFC0 + uw(0xD19A + 2 * k) for k in range(11) if uw(0xD17C + 2 * k) == 0x403}),
                0x403, "REA $D162"))
refs.append(ref("obj06_update", sorted({0x3C920 + uw(0xD2DA + 2 * k) for k in range(8)}), 0x603, "REA $D2BC"))
refs.append(ref("obj14_update", [0x3DFA0, 0x3DFA0 + 0x438], 0x904, "REA $CE1E"))
refs.append(ref("obj16_update", [0x40818, 0x40818 + 0x2D0, 0x40818 + 0x5A0, 0x40818 + 0x870], 0x604, "REA $CDDA"))
refs.append(ref("obj49_update", [0x41358 + uw(0xE7B2 + 2 * k) for k in range(16)], 0x402, "REA $E77A"))
refs.append(ref("FUN_00008de6", [0x4B68A], 0x604, "REA lift $8ECC"))
(out / "catalog_l2.json").write_text(json.dumps({"draw_targets": [], "refs": refs}, indent=0))
drawn = [f for f in cov if shared(f["addr"])]
(out / "drawn_l2.json").write_text(json.dumps({"bobs": drawn}))
n = sum(len(r["frames"]) for r in refs)
print(f"{len(refs)} refs, {n} frame entries; {len(drawn)} shared coverage frames")
