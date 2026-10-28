#!/usr/bin/env python3
"""Level 2's map-cell writers, measured on the level-2 RAM image (read-only), the way the port's
tools/mapcells.py measures level 1's, plus the vats of level_tick_1 ($91BC) and act_0c ($9EE8).

Prints the object list ($A828: header +0, REA read_bytes $868C), per entry its type, activator
offset (objtype_table $9D0C + 8Ah + type), look size, cells and map words; then the totals the
port's map patches and packed attribute codes must hold.
usage: l2objects.py level2_full.bin DATAL2.bin
"""
import struct
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path("/Users/rodrigogarcia/Library/Mobile Documents/com~apple~CloudDocs/Projects/VSCode Projects/msxports")
sys.path.insert(0, str(REPO / "tools"))
import mapcells  # noqa: E402
from amitab import parse  # noqa: E402

COLS, ROWS = 160, 50
ACT_NAMES = {0: "look only", 4: "act_04", 8: "act_08", 0x0C: "act_0c ($9EE8)", 0x10: "act_10 relocate",
             0x14: "conveyor left", 0x18: "conveyor right", 0x1C: "barrier", 0x20: "act_20 ($9F74)"}


def w(img, a, n=1):
    v = struct.unpack_from(f">{n}H", img, a)
    return v if n > 1 else v[0]


def main():
    img = Path(sys.argv[1]).read_bytes()
    datal = Path(sys.argv[2]).read_bytes()
    tabs = {r["label"]: r for r in parse(REPO / "analysis" / "amiga_tables.tsv")}
    tabs["objl_l2"] = {"label": "objl_l2", "addr": 0xA828, "count": 530, "kind": "x", "bank": "l2", "comment": ""}
    types = tabs["obj_types"]["addr"]
    # the entries
    a, k = 0xA828, 0
    acts = Counter()
    print("level 2 object list ($A828): entry: type, look, hits, value, x, y -> activator, size, cell")
    while struct.unpack_from(">h", img, a)[0] >= 0:
        t, look, hits, value, x, y = w(img, a, 6)
        t &= 0xFF
        act = w(img, types + 0x8A + t) & 0xFF
        wd = (w(img, types + 0x110 + t) & 0xFF) + 1
        ht = (w(img, types + 0x112 + t) & 0xFF) + 1
        row, col = mapcells.map_cell(x, y, ROWS)
        acts[act] += 1
        print(f"  {k:2d}: type {t:02X}h look {look:04X} hits {hits:04X} value {value:5d} x {x:5d} y {y:4d}"
              f" -> {ACT_NAMES.get(act, hex(act))}, {wd}x{ht}, cell ({row}, {col})")
        a += 12
        k += 1
    print(f"{k} entries; activators: " + ", ".join(f"{ACT_NAMES.get(x, hex(x))} {n}" for x, n in sorted(acts.items())))
    # the writers through the port's model (raises on an activator the port lacks: 0Ch is ao_look there)
    cells, words_of = mapcells.writers(img, tabs, "l2", COLS, ROWS)
    obj_cells = set().union(*cells.values())
    # the vats
    vat_cells = set()
    a = 0x95B2
    while struct.unpack_from(">h", img, a)[0] >= 0:
        xl, y, xr, rows = w(img, a, 4)
        row, col = mapcells.map_cell(xl, y, ROWS)
        ncol = ((xr - xl) & 0xFFFF) >> 4
        vat_cells |= {mapcells.lin(row + r, col + c, COLS) for c in range(ncol + 1) for r in range(rows + 2)}
        a += 8
    vat_words = set(w(img, 0x927A, 48))
    # act_0c's two words ($A4A6 written with E680h / 9700h)
    a0c = {0xE680, 0x9700}
    every = obj_cells | vat_cells
    for name, cs in (("map objects", obj_cells), ("vats", vat_cells), ("map objects without vats", obj_cells - vat_cells),
                     ("all", every)):
        ev = sum(1 for c in cs if c[0] % 2 == 0)
        print(f"{name}: {len(cs)} cells ({ev} in even rows, {len(cs) - ev} in odd rows); MP_N = {mapcells.MP_N} a pool")
    print(f"overlap objects/vats: {len(obj_cells & vat_cells)}")
    vals = sorted({x & 0x7F for ws in words_of.values() for x in ws} | {x & 0x7F for x in vat_words} | {x & 0x7F for x in a0c})
    print("attribute values the writers write:", [hex(v) for v in vals])
    # the map's own attributes and tiles at the vat cells
    m = [w(datal, 0x10000 + 2 * i) for i in range(ROWS * COLS)]
    at = Counter(m[r * COLS + c] & 0x7F for r, c in vat_cells)
    print("the map's own attributes at the vat cells:", dict(at))
    mvals = sorted({x & 0x7F for x in m})
    print("the map's attribute values:", [hex(v) for v in mvals], f"({len(mvals)} codes)")
    new = sorted(set(vals) - set(mvals))
    print("written values the map lacks:", [hex(v) for v in new])
    # tiles: the map's offsets, the writers' offsets
    map_off = {x & ~0x7F for x in m}
    wr_off = {x & ~0x7F for ws in words_of.values() for x in ws} | {x & ~0x7F for x in vat_words} | {x & ~0x7F for x in a0c}
    print(f"tile offsets: map {len(map_off)}, writers {len(wr_off)}, writers not in the map {len(wr_off - map_off)},"
          f" union {len(map_off | wr_off)}")
    # distinct graphics (content) of the 512 DATAL offsets
    seen = {}
    for o in range(0, 0x10000, 0x80):
        seen.setdefault(datal[o:o + 128], []).append(o)
    print(f"distinct tile graphics in DATAL2's 512 offsets: {len(seen)}")
    used = {datal[o:o + 128] for o in map_off | wr_off}
    print(f"distinct graphics used by the map and the writers: {len(used)}")


if __name__ == "__main__":
    main()
