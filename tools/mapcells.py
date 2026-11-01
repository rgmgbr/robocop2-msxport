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
    the blinking mines (map objects of activator 0Ch, act_0c $9EE8, level 2): their look's cells,
        with the second word act_0c writes into the look's blinking cell ($A4A6: E680h or 9700h)
    level 3's electric beams (level_tick_2 $9436, the hazard records): two cells wide, the top row
        (lt2_top's longs) and rows - 1 + 1 below (lt2_left, lt2_right; off: 1900h/1880h on top,
        1800h/1780h below), from t23_cell's cell as level 1's
    level 3's wall turrets (types 40, 41 and 42, the spawn list's entries of those types: $E98C,
        $EB0A, $E972): a flashing panel of 2 x 3 cells at map_cell(x & -16 - A0h, y) (type 41: - 70h;
        $EAA6, tur_panel's 3 looks) and the turret, 2 x 3 cells one row below and 10 (41: 7) columns
        right of the panel ($EA50, tur40_look's 5 looks; $EBB8, tur41_look's 4)

Level 3's type 36 ($E356) turns where the map word 18h below it is not 2D00h (its shaft): the port
(msx/level3obj.asm t36_w) knows those cells as constants, so the level's map must hold 2D00h exactly in
SHAFTS_L3 and no writer may change one of them (checked with --level 3). Level 3's beams keep a
map-write cache entry per record (msx/level3.asm lt2_off, msx/msx.inc bm_gen): at most BM_N records.

The map objects' cell is map_cell's (msx/logic.asm, $EF8E: column (x >> 4) - 8 as a byte, row
the low byte of y >> 4, 0 when y is negative or that byte is 51 or more: $EF8E's own limit in
every level, $EFA4 cmpi.w #$66). The writers step rows and columns as bytes (the Z80's D and E),
then map_write_lin wraps a column below 0 (F8h-FFh) into the row above's end and one of 160 or
more into the next row's start. The cells are an upper bound: a cell counts though the ROM map
may already hold some of its words.

The level's hazards (hz_<level>, $91B0 + 4 x level): level 1's electric beams write map patches
(above); level 2's vats (level_tick_1 $91BC) do not: the port draws them as a display layer, so
they stay out of the pools and get their own checks instead:
    every vat word (T0/T1/T2: vat_top, vat_odd, vat_even, 16 words each) and every vat cell of the
        map (the level's RAM image: the map at $38000) has attributes 0: the vats change no
        attribute the logic reads;
    no map object's cell lies in a vat;
    every vat word's tile is in the sheet (<atrp>.otile, .til: tools/msxconv.py's outputs);
    every vat column of the map is one look of the tables (T0[d] in its first row, then T1[d] and
        T2[d] alternating, d 0-15): the cells are level_tick_1's, ((x right - x left) >> 4) + 1
        columns of rows + 2 cells from map_cell(x left, y).

usage: mapcells.py build/ram/level1_full.bin analysis/amiga_tables.tsv build/msx/level1.atrp MAP_COLS MAP_ROWS
       mapcells.py build/ram/level2_full.bin analysis/amiga_tables.tsv build/msx/level2.atrp 160 50 --level 2
       mapcells.py build/ram/level3_full.bin analysis/amiga_tables.tsv build/msx/level3.atrp 160 50 --level 3
"""
from __future__ import annotations

import argparse
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
MINE_WORDS = (0xE680, 0x9700)       # act_0c $9EE8: the look word $A4A6 it writes (move.w #imm at $9EE8, $9EF8)
EF8E_ROWS = 51                      # $EF8E's row limit ($EFA4 cmpi.w #$66): a constant of every level
HAZARDS = {"l1": "beams", "l2": "vats", "l3": "beams2"}   # the hazard ticks: $933A (level 1), $91BC (level 2),
                                    # $9436 (level 3: two cells wide)
BEAM2_OFF_WORDS = (0x1900, 0x1880, 0x1800, 0x1780)        # level_tick_2 $9510: off, the top's two, then below
TURRETS = {40: (0xA0, 10, "tur40_look"), 41: (0x70, 7, "tur41_look"), 42: (0xA0, 10, "tur40_look")}
                                    # level 3's turrets: the panel's x offset, the turret's column offset
                                    # from the panel, its looks (6 words each)
SHAFTS_L3 = ((2, 25, 33), (75, 13, 18), (75, 27, 33))   # type 36's shafts: (column, first row, last row) of
                                    # the 2D00h words (msx/level3obj.asm t36_w's constants)
VAT_WORDS = ("vat_top", "vat_odd", "vat_even")    # level_tick_1's T0, T1, T2: 16 words each, by d
MAP_ADDR = 0x38000                  # draw_background $BCCA: the map in every level (DATAL at $28000)


def msx_equ(name: str) -> int:
    """A constant of msx/msx.inc."""
    m = re.search(rf"^{name}:\s+equ\s+(\S+)", (ROOT / "msx" / "msx.inc").read_text(), re.M)
    if not m:
        raise SystemExit(f"msx/msx.inc: no {name}")
    return int(m.group(1), 0)


MP_N = msx_equ("MP_N")              # patches in a pool
BM_N = msx_equ("BM_N")              # level 3's beam records the map-write cache holds (level3.asm lt2_off)


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
    if f"objl_{level}" not in tabs:
        raise SystemExit(f"analysis/amiga_tables.tsv: no objl_{level} (the level's object list)")
    a = tab(f"objl_{level}")
    k = 0
    while struct.unpack_from(">h", img, a)[0] >= 0:
        t, look, _hits, value, x, y = words(img, a, 6)
        t &= 0xFF                   # (the asm reads bytes of these: the type, the activator,
        act = words(img, types + 0x8A + t, 1)[0] & 0xFF          # width - 1, height - 1)
        row, col = map_cell(x, y, EF8E_ROWS)
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
            if act == 0x0C:
                ws += list(MINE_WORDS)                       # (act_0c: the look's blinking word)
        cells[name] = {lin(r, c, cols) for r, c in cs}
        words_of[name] = ws
        a += OBJ_REC
        k += 1
    hz = f"hz_{level}"
    if hz in tabs and HAZARDS.get(level) not in ("beams", "vats", "beams2"):
        raise SystemExit(f"{hz}: the level's hazard writer is not modelled here")
    if hz in tabs and HAZARDS[level] == "beams":
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
    if hz in tabs and HAZARDS[level] == "beams2":
        top = words(img, tab("lt2_top"), 8)
        body = words(img, tab("lt2_left"), 16) + words(img, tab("lt2_right"), 16)
        a = tab(hz)
        k = 0
        while struct.unpack_from(">h", img, a)[0] >= 0:
            x, y, _wx, rows1 = words(img, a, 4)
            row, col = map_cell(x, y, EF8E_ROWS, whole=True)
            below = rows1 + 1                                   # (dbf: the word + 1 rows)
            cells[f"beam {k}"] = {lin(row + r, col + c, cols) for r in range(below + 1) for c in (0, 1)}
            words_of[f"beam {k}"] = top + body + list(BEAM2_OFF_WORDS)
            a += HZ_REC
            k += 1
    if level == "l3":
        panel = words(img, tab("tur_panel"), 18)
        a = tab(f"spawn_{level}")
        k = 0
        while struct.unpack_from(">h", img, a)[0] >= 0:
            x, y = struct.unpack_from(">hh", img, a)
            t = img[a + 4]
            if t in TURRETS:
                dx, dc, looks = TURRETS[t]
                row, col = map_cell((x & 0xFFF0) - dx, y, EF8E_ROWS)
                cs = [(row + r, col + c) for r in range(3) for c in range(2)]
                cs += [(row + 1 + r, col + dc + c) for r in range(3) for c in range(2)]
                cells[f"turret {k} (type {t})"] = {lin(r, c, cols) for r, c in cs}
                words_of[f"turret {k} (type {t})"] = panel + words(img, tab(looks), tabs[looks]["count"])
            a += 14
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


def vats(img: bytes, tabs: dict, level: str, cols: int, rows: int) -> tuple[list[list[list[tuple[int, int]]]], list[list[int]]]:
    """level_tick_1 $91BC's cells, per record of hz_<level> (x left, y, x right, rows): from
    map_cell(x left, y), ((x right - x left) >> 4) + 1 columns of rows + 2 cells -> (per vat its
    columns, each its cells top down as (row, column)), [T0, T1, T2] (16 map words each)."""
    out = []
    a = tabs[f"hz_{level}"]["addr"]
    while struct.unpack_from(">h", img, a)[0] >= 0:
        xl, y, xr, n = words(img, a, 4)
        row, col = map_cell(xl, y, EF8E_ROWS)
        width = (((xr - xl) & 0xFFFF) >> 4) + 1
        if width > cols or n + 2 > rows or len(out) == 64:
            raise SystemExit(f"hz_{level} at ${a:05X}: a vat of {width} x {n + 2} cells (record {len(out)}): "
                             f"not one of the map's {cols} x {rows}")
        out.append([[lin(row + r, col + c, cols) for r in range(n + 2)] for c in range(width)])
        a += HZ_REC
    return out, [words(img, tabs[t]["addr"], 16) for t in VAT_WORDS]


def column_look(img: bytes, column: list[tuple[int, int]], cols: int, t: list[list[int]]) -> int | None:
    """The look d (0-15) whose words the map holds down a vat column (T0[d], then T1[d] and T2[d]
    alternating), None when it holds none."""
    have = [words(img, MAP_ADDR + 2 * (r * cols + c), 1)[0] for r, c in column]
    for d in range(16):
        if have == [t[0][d]] + [t[1 + (k & 1)][d] for k in range(len(column) - 1)]:
            return d
    return None


VAT_ROWS = 0x40                     # vat_tables: the per-row bytes (a map's rows: 51 at most),
VAT_RECS = 0x40                     #   then 8 bytes a vat (8 vats at most: a row's byte has 8 bits),
VAT_TILES = 0x80                    #   then the 48 vat words' tiles
VAT_SIZE = VAT_TILES + 3 * 16 * 2


def vat_tables(img: bytes, tabs: dict, level: str, cols: int, rows: int, otile: bytes) -> tuple[bytes, bytes]:
    """The vats' display tables (docs/LEVEL2.md 3.5: tools/mkrom.py puts them into the level's tables
    bank at L2_VAT_AT, read at 8000h as map_write reads OTILE; msx/tiles.asm get_tile's vat rule) and
    vat_shown's start (msx/level2.asm l2_init: a fresh level's), from level_tick_1's cells (vats):
      VAT_ROWS  per map row (64 bytes) the vats that cover it: bit v for vat v of hz_<level>;
      VAT_RECS  per vat 8 bytes: its first column, its columns, its first row, its rows (the record's
                rows + 2), its first column's index in vat_shown (the columns of the vats before
                it), then FFh x 3;
      VAT_TILES the tile (the sheet's: <atrp>.otile at the word's offset, word >> 7) of every vat word,
                words little-endian: T0[0..15], T1[0..15], T2[0..15] (a column at look d shows T0[d]
                in its first row, then T1[d] and T2[d] alternating);
    and per vat column (hz_<level>'s order, vat_shown's) the look d (0-15) the static map holds there
    (column_look). The level's vat checks (vat_problems) must pass first."""
    vs, t = vats(img, tabs, level, cols, rows)
    if len(vs) > 8:
        raise SystemExit(f"hz_{level}: {len(vs)} vats, a row's byte holds 8")
    table = bytearray(b"\x00" * VAT_ROWS + b"\xff" * (VAT_TILES - VAT_ROWS))
    first = 0
    looks = []
    for v, columns in enumerate(vs):
        r0, c0 = columns[0][0]
        if any(cell != (r0 + r, c0 + c) for c, column in enumerate(columns) for r, cell in enumerate(column)):
            raise SystemExit(f"hz_{level}: vat {v} is not a box of the map's cells (its columns wrap)")
        if r0 + len(columns[0]) > min(rows, VAT_ROWS):
            raise SystemExit(f"hz_{level}: vat {v}'s rows {r0}-{r0 + len(columns[0]) - 1} outside the map's")
        for r in range(r0, r0 + len(columns[0])):
            table[r] |= 1 << v
        table[VAT_RECS + 8 * v:VAT_RECS + 8 * v + 5] = bytes([c0, len(columns), r0, len(columns[0]), first])
        first += len(columns)
        looks += [column_look(img, column, cols, t) for column in columns]
    if first > 0xFF or None in looks:
        raise SystemExit(f"hz_{level}: {first} vat columns, or a column the tables do not hold")
    for ws in t:
        table += b"".join(struct.pack("<H", struct.unpack_from("<H", otile, 2 * (w >> 7))[0]) for w in ws)
    return bytes(table), bytes(looks)


def vat_problems(img: bytes, tabs: dict, level: str, cols: int, rows: int, objects: set,
                 otile: bytes, ntiles: int) -> tuple[list[str], str]:
    """The vats' own checks -> (what fails, a summary)."""
    vs, t = vats(img, tabs, level, cols, rows)
    every = [cell for v in vs for column in v for cell in column]
    cells = set(every)
    bad = []
    if len(cells) != len(every):
        bad.append("vats that share cells")
    outside = sorted(c for c in cells if c[0] >= rows)
    if outside:
        bad.append(f"vat cells outside the map's rows: {outside[:8]}")
    vw = [w for ws in t for w in ws]
    if any(w & 0x7F for w in vw):
        bad.append("vat words with attributes: " + ", ".join(f"{w:04X}h" for w in vw if w & 0x7F))
    attr = sorted({(r, c) for r, c in cells - set(outside) if words(img, MAP_ADDR + 2 * (r * cols + c), 1)[0] & 0x7F})
    if attr:
        bad.append(f"vat cells of the map with attributes: {attr[:8]}")
    shared = sorted(cells & objects)
    if shared:
        bad.append(f"map object cells in a vat: {shared[:8]}")
    if len(otile) != 1024:
        bad.append(f".otile: {len(otile)} bytes, not 512 tiles' words")
    else:
        lost = sorted({w for w in vw if struct.unpack_from("<H", otile, 2 * (w >> 7))[0] >= ntiles})
        if lost:
            bad.append("vat words whose tile is not in the sheet: " + ", ".join(f"{w:04X}h" for w in lost))
    columns = [column for v in vs for column in v]
    odd = [column[0] for column in columns if not outside and column_look(img, column, cols, t) is None]
    if odd:
        bad.append(f"vat columns of the map that are no look of the tables (first cells {odd[:8]})")
    return bad, (f"{len(vs)} vats, {len(cells)} cells in {len(columns)} columns (outside the pools), "
                 f"{len(set(w & ~0x7F for w in vw))} tile offsets, attributes 0, every column one look")


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
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="the level's RAM image (tools/ramimage.py)")
    ap.add_argument("tables", help="analysis/amiga_tables.tsv")
    ap.add_argument("atrp", help="the level's packed attributes (tools/msxconv.py)")
    ap.add_argument("cols", type=lambda s: int(s, 0))
    ap.add_argument("rows", type=lambda s: int(s, 0))
    ap.add_argument("--level", type=int, default=1, choices=(1, 2, 3))
    a = ap.parse_args(argv[1:])
    level = f"l{a.level}"
    img = Path(a.image).read_bytes()
    tabs = {r["label"]: r for r in parse(Path(a.tables))}
    table = Path(a.atrp).read_bytes()[-CODES:]
    cols, rows = a.cols, a.rows
    cells, words_of = writers(img, tabs, level, cols, rows)
    every = set().union(*cells.values())
    outside = sorted(c for c in every if c[0] >= rows)
    pools = [sorted(c for c in every if c[0] % 2 == p) for p in (0, 1)]
    values = sorted({w & 0x7F for ws in words_of.values() for w in ws})
    lut = {v for v in table if v != 0xFF}
    print(f"mapcells: {'' if level == 'l1' else f'level {a.level}: '}{len(every)} cells the writers can change ({len(pools[0])} in even rows, "
          f"{len(pools[1])} in odd ones; {MP_N} a pool), {len(lut | set(values))} attribute values "
          f"({len(set(values) - lut)} not in the map; {CODES} codes, {table.count(0xFF)} free)")
    bad = []
    if outside:
        bad.append(f"cells outside the map's rows (row FFh is the one above row 0; atr_put keeps no "
                   f"attributes there): {outside[:8]}")
    for p, name in ((0, "even"), (1, "odd")):
        if len(pools[p]) > MP_N:
            bad.append(f"the {name} rows' pool: {len(pools[p])} cells, more than its {MP_N} patches")
    bad += [f"{a.atrp}: {b}" for b in code_problems(table, values)]
    if f"hz_{level}" in tabs and HAZARDS[level] == "vats":
        sheet = Path(a.atrp)
        vbad, summary = vat_problems(img, tabs, level, cols, rows, every, sheet.with_suffix(".otile").read_bytes(),
                                     len(sheet.with_suffix(".til").read_bytes()) // 128)
        print(f"mapcells: vats: {summary}" if not vbad else "mapcells: vats: checks failed")
        bad += [f"vats: {b}" for b in vbad]
    if level == "l3":
        shafts = {(r, c) for c, r0, r1 in SHAFTS_L3 for r in range(r0, r1 + 1)}
        found = {(r, c) for r in range(rows) for c in range(cols)
                 if struct.unpack_from(">H", img, 0x38000 + 2 * (r * cols + c))[0] == 0x2D00}
        if found != shafts:
            bad.append(f"type 36's shafts (2D00h): the map has {sorted(found ^ shafts)[:8]} other than SHAFTS_L3")
        if every & shafts:
            bad.append(f"a writer changes type 36's shafts: {sorted(every & shafts)[:8]}")
        print(f"mapcells: level 3: type 36's shafts: {len(found)} cells of 2D00h, as SHAFTS_L3, no writer's")
        beams = sum(1 for name in cells if name.startswith("beam "))
        if beams > BM_N:
            bad.append(f"{beams} beam records, msx/msx.inc BM_N {BM_N} (level3.asm lt2_off's bm_gen entries)")
        print(f"mapcells: level 3: {beams} beam records, {BM_N} map-write cache entries (BM_N)")
    for b in bad:
        print(f"mapcells: error: {b}", file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
