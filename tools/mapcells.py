#!/usr/bin/env python3
"""Checks that the MSX port's map patches hold every map change the level's game logic can make.

The original writes map words into its map while it runs. The port keeps a written word's
attributes in the packed map in page-0 RAM (16 codes: those of the map's own values plus free
ones, msx/tiles.asm atr_put) and a tile that is not the ROM map's as a patch in one of two pools
of MP_N (the even rows' and the odd rows', msx/msx.inc MP_A / MP_B). A patch is never given back,
so a pool must hold every cell of its rows that a writer can ever change, and the codes every
attribute value a writer can write. This tool works out those cells and values from the level's
data, the way the ported writers compute them, and fails when they do not fit:

    map objects (msx/mapobj.asm activate_objects): a conveyor (activator 14h / 18h: act_cv)
        value + 1 cells of its row; an electric barrier (1Ch: act_1c) 3 columns of its row and
        of the rows its count reaches below it (0-4 when the count starts at 0-4: ao_start
        clears it but for type 58h, whose count is its look's high byte); any other entry its
        type's width x height from its cell (ao_copy), the map words of every look of its type's
        look table from its first look on (ao_lookp: the table's and each look's long read by
        its low word in the copy of obj_looks, a negative long ending the table)
    electric beams (msx/level1.asm lt0, the hazard records): the top cell and rows - 1 + 1 below,
        from t23_cell's cell (row y >> 4 as a word, 0 outside the map's rows)
    the level's end (msx/level1.asm type 32): the 36 words of t32_map (35 cells, two words share
        one): column (x >> 4) - 7, row the low byte of y >> 4

The map objects' cell is map_cell's (msx/logic.asm, $EF8E: column (x >> 4) - 8 as a byte, row
the low byte of y >> 4, 0 when y is negative or that byte is past the map's rows). The writers
step rows and columns as bytes (the Z80's D and E), then map_write_lin wraps a column below 0
(F8h-FFh) into the row above's end and one of 160 or more into the next row's start. The cells
are an upper bound: a cell counts though the ROM map may already hold some of its words.

usage: mapcells.py build/ram/level1_full.bin analysis/amiga_tables.tsv build/msx/level1.atrp MAP_COLS MAP_ROWS
"""
from __future__ import annotations

import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amitab import parse  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CODES = 16                          # codes of the packed map (msx/tiles.asm atr_rc: 4 bits)
OBJ_REC = 12                        # an object list entry: type, look, hits, value, x, y (words)
HZ_REC = 8                          # a hazard record: x, y, window x, rows - 1 (words)
ACTS = range(0, 0x24, 4)            # msx/mapobj.asm ao_acts: the activator offsets it has
BARRIER_WORDS = (0x0D00, 0x7980, 0xCD80, 0xCE00, 0xCE80)   # msx/mapobj.asm act_1c
BEAM_OFF_WORDS = (0xE800, 0x0D00)                          # msx/level1.asm lt0_off


def msx_equ(name: str) -> int:
    """A constant of msx/msx.inc."""
    m = re.search(rf"^{name}:\s+equ\s+(\S+)", (ROOT / "msx" / "msx.inc").read_text(), re.M)
    if not m:
        raise SystemExit(f"msx/msx.inc: no {name}")
    return int(m.group(1), 0)


MP_N = msx_equ("MP_N")              # patches in a pool


def words(img: bytes, addr: int, n: int) -> list[int]:
    return list(struct.unpack_from(f">{n}H", img, addr))


def map_cell(x: int, y: int, rows: int, dx: int = 8, whole: bool = False) -> tuple[int, int]:
    """$EF8E's cell (msx/logic.asm map_cell, msx/level1.asm t23_cell): column (x >> 4) - dx as a
    byte (-8..167), row y >> 4 (0 above or below the map's rows: map_cell tests the row's low
    byte, t23_cell, whole, all of it)."""
    col = ((x >> 4) - dx) & 0xFF
    r = (y >> 4) & (0xFFF if whole else 0xFF)
    return (r if not y & 0x8000 and r < rows else 0), col


def lin(row: int, col: int, cols: int) -> tuple[int, int]:
    """map_write_lin: a column below 0 (F8h-FFh) is the row above's end, 160 and more the next
    row's start. Row and column are the writers' D and E: bytes (inc e after FFh gives 0)."""
    row, col = row & 0xFF, col & 0xFF
    if col < cols:
        return row & 0xFF, col
    if col >= 0xF8:
        return (row - 1) & 0xFF, (col + cols) & 0xFF
    return (row + 1) & 0xFF, col - cols


def writers(img: bytes, tabs: dict, level: str, cols: int, rows: int) -> tuple[dict, dict]:
    """-> (writer name: its cells as a set of (row, column)), (writer name: its map words)."""
    def tab(label: str) -> int:
        return tabs[label]["addr"]
    types = tab("obj_types")
    lo = tab("obj_looks")
    hi = lo + 2 * tabs["obj_looks"]["count"]              # (the copy the port reads)

    def copy_words(addr: int, n: int, what: str) -> list[int]:
        if not lo <= addr <= hi - 2 * n:
            raise SystemExit(f"{what} at ${addr:05X}: outside the port's copy of obj_looks (${lo:05X}-${hi - 1:05X})")
        return words(img, addr, n)

    conv = words(img, tab("conv_words"), 16)
    cells, words_of = {}, {}
    a = tab(f"objl_{level}")
    k = 0
    while struct.unpack_from(">h", img, a)[0] >= 0:
        t, look, _hits, value, x, y = words(img, a, 6)
        t &= 0xFF                   # (the asm reads bytes of these: the type, the activator,
        act = words(img, types + 0x8A + t, 1)[0] & 0xFF          # width - 1, height - 1)
        row, col = map_cell(x, y, rows)
        name = f"entry {k} (type {t:02X}h)"
        if act not in ACTS:
            raise SystemExit(f"{name}: activator offset {act:02X}h, not in msx/mapobj.asm ao_acts")
        first = look if t == 0x58 else 0                     # (ao_start keeps type 58h's look)
        if act in (0x14, 0x18):
            if value < 1:
                raise SystemExit(f"{name}: a conveyor of value {value} (act_cv writes 65535 cells)")
            cs = [(row, col + c) for c in range(value + 1)]
            ws = conv
        elif act == 0x1C:
            reach = range(5) if first >> 8 <= 4 else range(256)
            cs = [(row + r, col + c) for r in reach for c in range(3)]
            ws = list(BARRIER_WORDS)
        else:
            wd = (words(img, types + 0x110 + t, 1)[0] & 0xFF) + 1
            ht = (words(img, types + 0x112 + t, 1)[0] & 0xFF) + 1
            if wd > 128 or ht > 128:
                raise SystemExit(f"{name}: a look of {wd} x {ht} cells (ao_copy's jp p loops end at 128)")
            cs = [(row + r, col + c) for r in range(ht) for c in range(wd)]
            table = words(img, types + t + 2, 1)[0]             # (the table long's low word)
            ws = []
            for n in range(64):
                high, low = copy_words(table + first + 4 * n, 2, f"{name}: its look table's entry")
                if high & 0x8000:
                    break
                ws += copy_words(low, wd * ht, f"{name}: its look {n}")
            else:
                raise SystemExit(f"{name}: no end (a negative long) in its look table at ${table:05X}")
        cells[name] = {lin(r, c, cols) for r, c in cs}
        words_of[name] = ws
        a += OBJ_REC
        k += 1
    hz = f"hz_{level}"
    if hz in tabs:
        top, body = words(img, tab("lt0_top"), 4), words(img, tab("lt0_body"), 32)
        a = tab(hz)
        k = 0
        while struct.unpack_from(">h", img, a)[0] >= 0:
            x, y, _wx, rows1 = words(img, a, 4)
            row, col = map_cell(x, y, rows, whole=True)
            below = ((rows1 & 0xFF) + 1) & 0xFF or 256           # (inc b, then djnz)
            cells[f"beam {k}"] = {lin(row + r, col, cols) for r in range(below + 1)}
            words_of[f"beam {k}"] = top + body + list(BEAM_OFF_WORDS)
            a += HZ_REC
            k += 1
    if level == "l1":
        t32 = words(img, tab("t32_map"), 108)
        cs, ws = set(), []
        for n in range(36):
            x, y, w = t32[3 * n:3 * n + 3]
            cs.add(lin((y >> 4) & 0xFF, ((x >> 4) - 7) & 0xFF, cols))
            ws.append(w)
        cells["type 32"], words_of["type 32"] = cs, ws
    return cells, words_of


def code_problems(table: bytes, values: list[int]) -> list[str]:
    """The packed map's 16 code values (the .atrp's last 16 bytes, FFh a free code) against the
    attribute values the writers write -> what does not fit (nothing: they fit)."""
    lut = [v for v in table if v != 0xFF]
    if len(lut) != len(set(lut)):
        return [f"codes with the same value ({table.hex()}): free codes must be FFh (tools/msxconv.py: make msx)"]
    new = sorted(set(values) - set(lut))
    if len(new) > table.count(0xFF):
        return [f"{len(new)} attribute values the map has not (" + ", ".join(f"{v:02X}h" for v in new)
                + f"), {table.count(0xFF)} free codes"]
    return []


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        print(__doc__, file=sys.stderr)
        return 2
    img = Path(argv[1]).read_bytes()
    tabs = {r["label"]: r for r in parse(Path(argv[2]))}
    table = Path(argv[3]).read_bytes()[-CODES:]
    cols, rows = int(argv[4], 0), int(argv[5], 0)
    cells, words_of = writers(img, tabs, "l1", cols, rows)
    every = set().union(*cells.values())
    outside = sorted(c for c in every if c[0] >= rows)
    pools = [sorted(c for c in every if c[0] % 2 == p) for p in (0, 1)]
    values = sorted({w & 0x7F for ws in words_of.values() for w in ws})
    lut = {v for v in table if v != 0xFF}
    print(f"mapcells: {len(every)} cells the writers can change ({len(pools[0])} in even rows, "
          f"{len(pools[1])} in odd ones; {MP_N} a pool), {len(lut | set(values))} attribute values "
          f"({len(set(values) - lut)} not in the map; {CODES} codes, {table.count(0xFF)} free)")
    bad = []
    if outside:
        bad.append(f"cells outside the map's rows (row FFh is the one above row 0; atr_put keeps no "
                   f"attributes there): {outside[:8]}")
    for p, name in ((0, "even"), (1, "odd")):
        if len(pools[p]) > MP_N:
            bad.append(f"the {name} rows' pool: {len(pools[p])} cells, more than its {MP_N} patches")
    bad += [f"{argv[3]}: {b}" for b in code_problems(table, values)]
    for b in bad:
        print(f"mapcells: error: {b}", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
