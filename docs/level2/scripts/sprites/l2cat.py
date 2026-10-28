#!/usr/bin/env python3
"""Level 2's BOB frames, from the draw code read with REA (Ghidra, build/ram/level2_full.bin).

Every table below was read with REA read_bytes (dumps in rea/*.hex); this script checks that each
dump equals the RAM image's bytes, then enumerates the frames per object, measures them (pixel box,
Amiga colours), finds exact left/right mirrors, and says which ones level 1's MSX data already
holds (in/robocop.json: sprite frames "bobs", play-field frames "field").

Outputs (out/):
  l2_frames.json        every frame: object, role, side, BLT size, pixel box, colours, mirror,
                        renderer chosen, level-1 status
  catalog_l2.json       a tools/bobcatalog.py-style catalogue for tools/msxsprites.py --level level2
usage: l2cat.py RAM_L2 MAIN_8000 ROBOCOP_JSON OUTDIR
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ram = Path(sys.argv[1]).read_bytes()
main = Path(sys.argv[2]).read_bytes()
l1 = json.loads(Path(sys.argv[3]).read_text())
out = Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)

# --- the REA dumps must be the image's bytes -------------------------------------------------
for f in sorted((HERE / "rea").glob("*.hex")):
    name = f.stem.split("_")[-1]
    addr = int(name, 16)
    d = bytes.fromhex(f.read_text().strip())
    assert ram[addr:addr + len(d)] == d, f"{f.name}: REA dump differs from the RAM image"

uw = lambda a: struct.unpack_from(">H", ram, a)[0]   # noqa: E731
sw = lambda a: struct.unpack_from(">h", ram, a)[0]   # noqa: E731
ul = lambda a: struct.unpack_from(">L", ram, a)[0]   # noqa: E731


def dims(d4: int) -> tuple[int, int]:
    return ((d4 & 63) - 1) * 16, d4 >> 6


def region(a: int) -> str:
    if 0x28000 <= a < 0x28000 + 105816:
        return "DATAL2"
    if 0x45250 <= a < 0x4B54C:
        return "MADEX"
    if 0x4B68A <= a < 0x5884E:
        return "SPERMA"
    if 0x58850 <= a < 0x6FFA0:
        return "PERMA"
    return "other"


def pixels(addr: int, w: int, h: int) -> list[list[int]]:
    wb, ps = w // 8, (w // 8) * h
    rows = []
    for y in range(h):
        row = []
        for x in range(w):
            byte, bit = y * wb + (x >> 3), 0x80 >> (x & 7)
            if ram[addr + byte] & bit:
                row.append(sum(1 << p for p in range(4) if ram[addr + ps * (p + 1) + byte] & bit))
            else:
                row.append(-1)
        rows.append(row)
    return rows


F: dict[tuple[int, int, int], dict] = {}


def add(obj: str, role: str, side: str, addr: int, d4: int, renderer: str, note: str = "") -> None:
    w, h = dims(d4)
    k = (addr, w, h)
    e = F.setdefault(k, {"addr": addr, "w": w, "h": h, "d4": d4, "region": region(addr), "users": [],
                         "renderer": renderer})
    e["users"].append({"obj": obj, "role": role, "side": side, "note": note})
    if renderer == "field":
        e["renderer"] = "field"


# --- level 2's own objects (DATAL2 frames), REA: procedure_assembly of each handler ------------
for k in range(16):                                   # type 1 $C736: legs $3E810 + $C7E0[D2], $5C3
    add("type 1", "legs", "L" if k < 8 else "R", 0x3E810 + uw(0xC7E0 + 2 * k), 0x5C3, "sprite")
add("type 1", "torso", "L", 0x404D0, 0x543, "sprite")        # $C7C0 (facing byte set: left)
add("type 1", "torso", "R", 0x404D0 + 0x1A4, 0x543, "sprite")  # $C7D8
add("type 1", "gun flash", "L", 0x6CDA0, 0x403, "sprite", "every 46 frames ($B00 & 2Dh = 0)")
add("type 1", "gun flash", "R", 0x6CDA0 + 0x140, 0x403, "sprite")
add("type 2", "body (first 70 ticks)", "-", 0x3D280, 0xE04, "field", "flashes white 8 frames in 16 ($AC6E)")
add("type 2", "body", "-", 0x3D910, 0xE04, "field", "flashes white 8 frames in 16 ($AC6E)")
add("type 2", "gun flash", "L", 0x6CDA0, 0x403, "sprite", "($counter & 33h) = 0")
for k in range(11):                                   # type 5 $D0E2: $3BFC0 + $D19A[k], BLT $D17C[k]
    add("type 5", f"step {k}", "-", 0x3BFC0 + uw(0xD19A + 2 * k), uw(0xD17C + 2 * k), "sprite")
for k in range(8):                                    # type 6 $D1E2: $3C920 + $D2DA[D5], $603
    add("type 6", f"step {k}", "-", 0x3C920 + uw(0xD2DA + 2 * k), 0x603, "sprite")
add("type 14", "gunner", "L", 0x3DFA0, 0x904, "field")       # $CE0A, facing set: left
add("type 14", "gunner", "R", 0x3DFA0 + 0x438, 0x904, "field")
add("type 16", "body", "L", 0x40818, 0x604, "field")         # $CD7A: counter < 14h
add("type 16", "body kneel", "L", 0x40818 + 0x5A0, 0x604, "field")
add("type 16", "body", "R", 0x40818 + 0x2D0, 0x604, "field")
add("type 16", "body kneel", "R", 0x40818 + 0x5A0 + 0x2D0, 0x604, "field")
add("type 16", "gun flash", "L", 0x6CDA0, 0x403, "sprite")
add("type 16", "gun flash", "R", 0x6CDA0 + 0x140, 0x403, "sprite")
for k in range(16):                                   # type 49 $E6C0 -> $E728: $41358 + $E7B2[D2]
    add("type 49", f"direction {k}", "-", 0x41358 + uw(0xE7B2 + 2 * k), 0x402, "sprite")
add("trolley $8F02", "pulley", "-", 0x4B95A, 0xBC3, "field", "RoboCop hangs from it (states 14/15)")
add("lift $8DE6", "platform", "-", 0x4B68A, 0x604, "field")

# --- shared objects (SPERMA/PERMA/MADEX), the tables REA read ---------------------------------
for i in range(16):                                   # walker1 $C948 (types 15, 16, 18, 24...)
    add("walker1 legs (types 15, 16)", f"step {i}", "L" if i < 8 else "R",
        0x4BD06 + sw(0xC9B4 + 2 * i), uw(0xC9D4 + 2 * i), "sprite")
for i in range(6):                                    # gunman torso (types 15, 30, 31)
    add("gunman torso (types 15, 30, 31)", f"aim {i}", "-", 0x4E466 + sw(0xCB4A + 2 * i), uw(0xCB56 + 2 * i), "sprite")
for i in range(20):                                   # walker2 $CC4A and type 3's torso $CB6E
    add("walker2 legs (types 3, 30)", f"step {i}", "L" if i < 10 else "R",
        0x4F1D6 + sw(0xCBFA + 2 * i), uw(0xCC22 + 2 * i), "sprite")
    add("type 3", f"torso {i}", "L" if i < 10 else "R", 0x4F1D6 + sw(0xCBAA + 2 * i), uw(0xCBD2 + 2 * i), "sprite")
for t in (1, 2, 3, 4, 5, 6):                          # enemy bullets $F3CE: gfx $F4A4 + 4t, BLT $F500 + 4t
    g, d4 = ul(0xF4A4 + 4 * t), uw(0xF500 + 4 * t)
    step, lim = sw(0xF55C + 4 * t), sw(0xF55C + 4 * t + 2)
    n = 1 if step <= 0 else lim // step + 1
    for k in range(n):
        add(f"enemy bullet {t}", f"step {k}", "-", g + k * max(step, 0), d4, "sprite")
for b in l1["field"]:                                 # the hostage (MADEX) and the dynamic frames
    if b["proc"] == "obj45_update":
        add("hostage (type 45)", "legs" if b["h"] == 20 else "body", "-", b["addr"],
            (b["w"] // 16 + 1) | b["h"] << 6, "field")
    elif "dyn" in b:
        add("explosion / smoke", "step", "-", b["addr"], (b["w"] // 16 + 1) | b["h"] << 6, "dyn")

# type 4 ($CFB0, shared): legs $5860A, torso by aim ($D066/$D096), muzzle flash $6C620 + $50 * aim
add("type 4", "legs", "-", 0x5860A, 0x743, "sprite")
for k in range(8):
    add("type 4", f"torso aim {k}", "-", 0x57192 + uw(0xD066 + 2 * k), uw(0xD096 + 2 * k), "sprite")
    add("muzzle flash (types 4, 12, 15, 30, 31)", f"aim {k}", "-", 0x6C620 + 0xA0 * k, 0x402, "sprite")
add("type 31", "legs", "-", 0x5860A, 0x743, "sprite")
# the catalogue's scan errors (REA: never drawn so) and level-1-only objects: left out
BOGUS = {(a, 16, 16) for a in (0x57192, 0x57412, 0x57692, 0x57912, 0x57B92, 0x57E12, 0x58092, 0x58312, 0x4ED26)} | {(0x525CC, 32, 32)}
# level 1's other shared sprite frames (MADEX/SPERMA/PERMA): kept, none new
for b in l1["bobs"]:
    if (b["addr"], b["w"], b["h"]) in BOGUS:
        continue
    if b.get("spark") or region(b["addr"]) == "other":
        continue
    if region(b["addr"]) in ("MADEX", "SPERMA", "PERMA"):
        k = (b["addr"], b["w"], b["h"])
        if k not in F:
            add(f"level-1 shared ({b['proc']})", "-", "-", b["addr"], (b["w"] // 16 + 1) | b["h"] << 6, "sprite")

# --- measure, mirrors, level-1 status ---------------------------------------------------------
l1_spr = {(b["addr"], b["w"], b["h"]) for b in l1["bobs"]}
l1_fld = {(b["addr"], b["w"], b["h"]) for b in l1["field"]}
img = {}
for k, e in F.items():
    p = pixels(e["addr"], e["w"], e["h"])
    img[k] = p
    ys = [y for y, r in enumerate(p) if any(c >= 0 for c in r)]
    xs = [x for x in range(e["w"]) if any(p[y][x] >= 0 for y in range(e["h"]))]
    e["box"] = [min(xs), min(ys), max(xs) + 1, max(ys) + 1] if xs else None
    e["pw"] = (e["box"][2] - e["box"][0]) if xs else 0
    e["ph"] = (e["box"][3] - e["box"][1]) if xs else 0
    cnt = {}
    for r in p:
        for c in r:
            if c >= 0:
                cnt[c] = cnt.get(c, 0) + 1
    e["colours"] = dict(sorted(cnt.items()))
    e["opaque"] = sum(cnt.values())
    e["in_l1"] = "sprite" if k in l1_spr else "field" if k in l1_fld else "no"


def trimmed(p):
    ys = [y for y, r in enumerate(p) if any(c >= 0 for c in r)]
    xs = [x for x in range(len(p[0])) if any(r[x] >= 0 for r in p)]
    if not xs:
        return None
    return tuple(tuple(r[min(xs):max(xs) + 1]) for r in p[min(ys):max(ys) + 1])


keys = sorted(F)
for i, k in enumerate(keys):
    t = trimmed(img[k])
    if t is None:
        continue
    mt = tuple(tuple(reversed(r)) for r in t)
    for k2 in keys[:i]:
        if trimmed(img[k2]) == mt and mt != t:
            F[k]["mirror_of"] = f"{k2[0]:X}"
            break
    for k2 in keys[:i]:
        if trimmed(img[k2]) == t:
            F[k]["same_as"] = f"{k2[0]:X}"
            break

frames = [F[k] for k in keys]
(out / "l2_frames.json").write_text(json.dumps(frames, indent=1))

# --- a catalogue for tools/msxsprites.py (level "level2"; procs name the field ones) ------------
refs = []
for e in frames:
    u = e["users"][0]
    proc = {"type 2": "obj02_update", "type 14": "obj14_update", "type 16": "obj16_update",
            "trolley $8F02": "FUN_00008f02", "lift $8DE6": "FUN_00008de6",
            "hostage (type 45)": "obj45_update"}.get(u["obj"], "l2_" + u["obj"].split(" (")[0].replace(" ", "_"))
    if e["renderer"] == "dyn":
        proc = "drawn"
    if e["renderer"] == "field" and u["role"] == "gun flash":
        proc = "l2_gun"
    refs.append({"proc": 0, "proc_name": proc, "site": 0, "base": e["addr"], "adjust": [], "table": None,
                 "ltable": None, "bltsize": e["d4"], "width": e["w"], "height": e["h"],
                 "frames": [e["addr"]], "level": "level2", "evidence": "REA (l2cat.py)"})
(out / "catalog_l2.json").write_text(json.dumps({"draw_targets": [], "refs": refs}, indent=0))

# --- report --------------------------------------------------------------------------------------
new = [e for e in frames if e["in_l1"] == "no"]
print(f"{len(frames)} frames; {len(new)} not in level 1's MSX data")
for e in frames:
    u = "; ".join(sorted({f"{x['obj']} {x['role']} {x['side']}".strip() for x in e["users"]}))
    print(f"{e['addr']:05X} {e['region']:6} {e['w']:2}x{e['h']:<2} px {e['pw']:2}x{e['ph']:<2} {e['renderer']:6} "
          f"L1:{e['in_l1']:6} {('mirror ' + e['mirror_of']) if 'mirror_of' in e else ''}"
          f"{('same ' + e['same_as']) if 'same_as' in e else ''} cols {''.join('%X' % c for c in e['colours'])} | {u}")
