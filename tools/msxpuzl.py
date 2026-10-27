#!/usr/bin/env python3
"""Brainstorm (PUZL, the chip puzzle after level 1) in SCREEN 5 for msx/puzl.asm: the screen
re-laid out 1:1 from the Amiga's 320 x 176 into the 256 x 162 play area, its 16 colours, the
sheet of blocks the stage copies from, the nine TV pictures, the cursor's sprites and PUZL's
tables (docs/BRAINSTORM.md 3.3 and 3.9; from the graphics report's prototype of 2026-10-26).

Source: PUZL loaded at $17100 (build/extracted/files/PUZL_25.bin, disk 2's plain copy: the same
bytes as disk 1's PUZL_13 decrunched by $124A6). Every address below is one the stage's code
reads (REA, Ghidra provider, on the level-1 RAM image with PUZL at $17100):
  $2A320  the screen: 5 sequential planes of 320 x 176 ($1B80 apart), copper list $17BFC, the
          bitplane pointers from the copper interrupt $17B5A. Plane 4 is set only over the TV
          ($1711C), so the TV uses COLOR16-31 and everything else COLOR00-15
  $234E0  32 chip tiles, 16 x 16 x 4 planes: cell (c, r) at (16 + 16c, 16 + 16r), $1737A;
          tile = the cell's value (its type 0-15, + 16 once visited, $17760)
  $244E0 / $25160  the faces (Murphy: visit 1, Ellen: visit 2), 80 x 80 x 4 planes, COLOR16-31
  $25DE0  4 TV-static frames of 4000 bytes (a mask plane, then 4 planes), cut over the face or
          over the black TV by $17298 (minterm $CA)
  $29C60  10 LED digits, 8 x 16 x 4 planes ($1790E): the LED row $17944, the timer $1797C
  $29EE0  2 lights 8 x 8; $29F20 2 bars 24 x 8 (4 bytes a line, 3 shown); $2A020 2 buttons
          32 x 24: $179FC (image 0 is the bright one of the light and of the bar)
  $17DE8  8 cursor images, hardware sprite 0: 16 lines of (DATA, DATB), $17B5A
  $17D6A / $17DAA  COLOR01-31 (visit 1 / visit 2; COLOR00 black, $171C2)
  $17448-$1775F  8 boards of 94 bytes (visit 1: 0-3, visit 2: 4-7), 3 HUD messages, a pad byte
  $17194, $17284, $1728E, $17972, $179B6, $17ADE  the small tables (docs/BRAINSTORM.md 2.6)

The re-layout: eight rectangles of the Amiga screen (PIECES) copied 1:1, MSX y = Amiga y - 14.
Every functional element lies whole inside one of them, at the MSX place the plan gives
(docs/BRAINSTORM.md 3.3); only decoration is dropped (the top 14 lines, the gold pins, the
ribbon cable, the TV casing, three bits of panel art).

Outputs (OUT = the prefix, e.g. build/msx/puzl):
  OUT_1.pal       visit 1's 16 colours, V9938 pairs (R << 4 | B, G), plain (tools/mkrom.py
                  grades them: decision 8, game play). OUT_2.pal with --visits 1,2
  OUT_gfx.bin     the screen (256 x 162, the TV rectangle black) and the sheet (256 x 56), 128
                  bytes a line: one stream into VRAM page 0 from line 0; then visit 1's 9 TV
                  pictures (80 x 80, 40 bytes a line, TV_STATES order), and visit 2's 9 after
                  them with --visits 1,2 (milestone 3)
  OUT_cursor.spr  9 sprite patterns of 32 bytes (sprite mode 2: left 8 columns, then right 8)
  OUT.inc         equates only (include it anywhere): the elements' places, the sheet's and the
                  TV pictures' VDP coordinates, the blob's layout, the cursor's patterns and
                  colours per visit, a display page's shown state (110 bytes), the boards' layout
  OUT_tab.inc     data: PUZL's $17448-$1775F and its small tables, checked against the plan
  OUT_*.png       previews: the stored screen, sheet, TV pictures and cursor; a moment of the
                  stage in plain and graded colours (with the HUD below it when OUT's folder
                  holds hud.sc5 and hud.pal, tools/msxhud.py); the Amiga against the MSX

Checks (any failure stops the tool): PUZL's tables and palettes equal docs/BRAINSTORM.md 2.6;
every board's red-chip count equals its number of type-0 cells; the pieces neither overlap nor
leave a hole; every functional element lies whole inside one piece, at the plan's place, on even
x; the screen uses COLOR00-15 outside the TV; no face, static or cursor
colour takes a green or a bright red; and a render of shown states through the VRAM model (the
blob, the sheet's and the TV pictures' coordinates, OUT.inc's places) equals the Amiga's own
composition of the same states, pixel for pixel through the pieces.

Render mode (the visual checks of docs/BRAINSTORM.md 4.2): a display page's picture from its
shown state (OUT.inc PZ_ST_*: 110 bytes, PZ_ST_NONE = the screen's own pixels) and, optionally,
the cursor (column, row, image 0-7), built as the stage builds it: the blob in a VRAM model,
one HMMM per element from the sheet or page 2, then the cursor's sprites. It writes OUT.sc5
(the 256 x 162 picture as SCREEN 5 bytes, sprites included) and OUT.png. STATE is a file (the
110 bytes at --offset, e.g. in a RAM dump) or, with --hex, the bytes as hex digits.

Python 3 standard library only.

usage: msxpuzl.py PUZL_25.bin OUT [--visits 1|1,2]
       msxpuzl.py render PUZL_25.bin STATE OUT [--offset N | --hex] [--cursor C,R,I]
                  [--visit 1|2] [--grade] [--scale N]
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from msxbright import BRIGHT  # noqa: E402
from msxhud import lab, to_msx  # noqa: E402
from planar import decode_indices, write_png  # noqa: E402

# ----- the Amiga side -----

LOAD, PUZL_LEN = 0x17100, 0x1BBE0              # PUZL_25.bin: $17100-$32CDF
SCREEN, AW, AH = 0x2A320, 320, 176
CHIPS, FACES, NOISE = 0x234E0, (0x244E0, 0x25160), 0x25DE0
DIGITS, LIGHTS, BARS, BUTTON = 0x29C60, 0x29EE0, 0x29F20, 0x2A020
CURSOR, PALS = 0x17DE8, (0x17D6A, 0x17DAA)
RECS, RECS_END = 0x17448, 0x17760              # 8 boards, the 3 messages, a pad byte
VISIT_RECS = (0x17448, 0x175C0)                # $173D2's operand by the visit (AG $8050 >= 2)
REC_LEN, COLS, ROWS = 94, 11, 8
FACE_WIN = (224, 16, 80, 80)                   # plane 4 set by $1711C: the TV's COLOR16-31

# docs/BRAINSTORM.md 2.6 (words as the 68000 reads them)
PLAN_TABLES = [
    (0x17194, "pzt_curofs", "cursor image offsets from $17DE8 by $B00 & $1E",
     [0x40 * i for i in (0, 1, 2, 3, 4, 5, 6, 7, 6, 5, 4, 3, 2, 1, 0, 0)]),
    (0x17284, "pzt_masks", "the TV's face masks by $B0A (boards 0-3, then after the last)",
     [7, 3, 1, 0, 0]),
    (0x1728E, "pzt_shifts", "the TV's static shifts by $B0A (0: no static)", [1, 1, 1, 2, 0]),
    (0x17972, "pzt_ledthr", "the LED row's thresholds by $B0A", [0, 3, 6, 8, 10]),
    (0x179B6, "pzt_ledval", "the LED row's positions (by $B00 & 15) and digits (by $B02 & $1E)",
     [0, 1, 8, 6, 4, 5, 4, 7, 2, 4, 8, 5, 3, 0, 2, 6]),
    (0x17ADE, "pzt_rows", "the light's row by ($B00 >> 3) & 7, the bar's by $B0A",
     [320 * r for r in (0, 1, 2, 3, 3, 2, 1, 0)]),
]
ROW_BYTES = 320                                # $17ADE holds rows x 8 lines x 40 bytes
PLAN_BOARDS = {1: ((0, 0), (22, 21, 24, 28)), 2: ((5, 3), (23, 21, 24, 28))}  # start, red chips
PLAN_TIMER, PLAN_TUNE, PLAN_SCORE1 = (0x01, 0x00), 1, 9500  # 1:00 (BCD), tune 1; visit 1 solved
PLAN_MESSAGES = [(0x17738, b"TIMEOUTe\xff", "TIMEOUT."), (0x17741, b"MALFUNCTIONe\xff", "MALFUNCTION."),
                 (0x1774E, b"MEMORY RESTOREDe\xff", "MEMORY RESTORED.")]   # 'e' = the HUD font's '.'
PLAN_PAD = 0x08                                # $1775F
PLAN_PALETTES = {                              # COLOR01-31 (docs/BRAINSTORM.md 2.6)
    1: "222 444 666 888 AAA EEE 400 800 E20 020 040 480 620 A60 CA4 "
       "000 876 865 754 543 432 321 210 444 644 533 322 443 332 112 010",
    2: "222 444 666 888 AAA EEE 400 800 E20 020 040 480 620 A60 CA4 "
       "111 DCC EBA DAA D99 333 532 444 555 A9A 756 666 B87 878 965 CAA",
}

# ----- the MSX side -----

MW, MH = 256, 162                              # the play area (msx/msx.inc VIEW_LINES)
LINE_BYTES = 128                               # SCREEN 5: 2 pixels a byte
# The re-layout: rectangles of the Amiga screen copied 1:1 (name, Amiga x, y, w, h, MSX x, y).
PIECES = [
    ("board", 16, 14, 176, 130, 0, 0),           # the PCB: the 11 x 8 cells, 2 lines above them
    ("tv", 224, 14, 80, 90, 176, 0),             # the TV picture, its bezel's top and bottom edges
    ("lights_bars", 216, 104, 32, 40, 176, 90),  # the 4 lights, the 4 bars, the panel under them
    ("panel", 270, 104, 48, 40, 208, 90),        # green buttons, marks, the panel's right edge
    ("button_leds", 0, 144, 142, 32, 0, 130),    # the button, its ribs, the LED row's panel
    ("speaker", 162, 144, 34, 32, 142, 130),     # the speaker (its right rim and screw cut)
    ("signal", 206, 144, 40, 32, 176, 130),      # the SIGNAL box
    ("timer", 278, 144, 40, 32, 216, 130),       # the LED timer's panel
]
TIMER_AX = (280, 296, 304)                     # minutes, tens of seconds, seconds; the dash at 288

# the sheet: page 0 below the play area, the sources of the stage's HMMMs
SHEET_Y, SHEET_H = MH, 56
SHEET_COUNT = {"chip": 32, "digit": 10, "light": 2, "bar": 2, "button": 2}
# the TV pictures: page 2, picture n at (80 (n % 3), TV_PAGE_Y + 80 (n // 3))
TV_PAGE_Y, TV_W, TV_LINE, TV_COUNT = 512, 80, 40, 9
TV_BYTES = TV_W * TV_LINE
TV_STATES = [("F", 0), ("F", 1), ("F", 2), ("F", 3), ("B", 0), ("B", 1), ("B", 2), ("B", 3), ("F", None)]
TV_FACE, TV_BLACK, TV_CLEAN = 0, 4, 8          # face + static n, black + static n, the face alone
# the blob
GFX_SHEET = MH * LINE_BYTES                    # 20,736
GFX_PAGE0 = (MH + SHEET_H) * LINE_BYTES        # 27,904: the screen and the sheet
GFX_TV_LEN = TV_COUNT * TV_BYTES               # 28,800 a visit
# the cursor: sprite mode 2, over cell (c, r) at SAT X = 16c, Y = 1 + 16r (shown a line lower)
SAT_X, SAT_Y = 0, 1

# A display page's shown state (docs/BRAINSTORM.md 3.3): what each element shows, NONE = the
# screen's own pixels (never drawn). Values: a TV picture, a digit, an image, a chip tile.
STATE = [("tv", 1), ("led", 9), ("timer", 3), ("button", 1), ("light", 4), ("bar", 4), ("cell", 88)]


def offsets(fields: list[tuple[str, int]]) -> tuple[dict[str, int], int]:
    out, o = {}, 0
    for name, n in fields:
        out[name] = o
        o += n
    return out, o


ST, ST_LEN = offsets(STATE)                    # ST_LEN = 110
NONE = 0xFF
ST_RANGE = {"tv": TV_COUNT, "led": 10, "timer": 10, "button": 2, "light": 2, "bar": 2, "cell": 32}


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def overlap(a: tuple, b: tuple) -> bool:
    """Do two rectangles (x, y, w, h) share a pixel?"""
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def inside(r: tuple, box: tuple) -> bool:
    return box[0] <= r[0] and r[0] + r[2] <= box[0] + box[2] and box[1] <= r[1] and r[1] + r[3] <= box[1] + box[3]


# ----- layout -----

def check_pieces() -> None:
    """The pieces fill the play area once, from places of the Amiga screen that do not overlap."""
    own = [[None] * MW for _ in range(MH)]
    for i, (name, sx, sy, w, h, dx, dy) in enumerate(PIECES):
        check(sx % 2 == 0 and dx % 2 == 0 and w % 2 == 0, f"piece {name}: odd x or width")
        check(inside((sx, sy, w, h), (0, 0, AW, AH)), f"piece {name}: outside the Amiga screen")
        check(inside((dx, dy, w, h), (0, 0, MW, MH)), f"piece {name}: outside the play area")
        for other in PIECES[i + 1:]:
            check(not overlap((sx, sy, w, h), other[1:5]), f"pieces {name} and {other[0]} overlap on the Amiga")
        for y in range(dy, dy + h):
            for x in range(dx, dx + w):
                check(own[y][x] is None, f"pieces {own[y][x]} and {name} overlap at ({x}, {y})")
                own[y][x] = name
    holes = [(x, y) for y in range(MH) for x in range(MW) if own[y][x] is None]
    check(not holes, f"the pieces leave {len(holes)} pixels empty, the first at {holes[:1]}")


def amiga_elements() -> dict:
    """The functional elements' rectangles on the Amiga screen (x, y, w, h), where the code draws
    them (docs/BRAINSTORM.md 2.8); the timer's dash is static art the timer needs."""
    e = {("tv",): (224, 16, 80, 80), ("button",): (0, 148, 32, 24), ("dash",): (288, 144, 8, 16)}
    for r in range(ROWS):
        for c in range(COLS):
            e[("cell", c, r)] = (16 + 16 * c, 16 + 16 * r, 16, 16)
    for p in range(9):
        e[("led", p)] = (64 + 8 * p, 152, 8, 16)
    for i, x in enumerate(TIMER_AX):
        e[("timer", i)] = (x, 144, 8, 16)
    for k in range(4):
        e[("light", k)] = (216, 104 + 8 * k, 8, 8)
        e[("bar", k)] = (224, 104 + 8 * k, 24, 8)
    return e


def plan_place(key: tuple) -> tuple[int, int]:
    """The MSX place docs/BRAINSTORM.md 3.3 gives each element."""
    kind = key[0]
    if kind == "cell":
        return 16 * key[1], 2 + 16 * key[2]
    if kind == "light":
        return 176, 90 + 8 * key[1]
    if kind == "bar":
        return 184, 90 + 8 * key[1]
    if kind == "led":
        return 64 + 8 * key[1], 138
    if kind == "timer":
        return (218, 234, 242)[key[1]], 130
    return {"tv": (176, 2), "button": (0, 134), "dash": (226, 130)}[kind]


def msx_layout() -> dict:
    """Each functional element's MSX rectangle, through the piece that holds it whole."""
    check_pieces()
    out = {}
    for key, rect in amiga_elements().items():
        hits = [p for p in PIECES if inside(rect, p[1:5])]
        check(len(hits) == 1, f"element {key} at {rect} lies whole in {len(hits)} pieces, not 1")
        name, sx, sy, w, h, dx, dy = hits[0]
        m = (rect[0] - sx + dx, rect[1] - sy + dy, rect[2], rect[3])
        check(m[:2] == plan_place(key), f"element {key}: MSX place {m[:2]}, the plan's {plan_place(key)}")
        check(m[0] % 2 == 0 and m[2] % 2 == 0, f"element {key}: odd x or width (HMMM moves whole bytes)")
        out[key] = m
    keys = list(out)
    for i, k in enumerate(keys):
        for k2 in keys[i + 1:]:
            check(not overlap(out[k], out[k2]), f"elements {k} and {k2} overlap on the MSX")
    return out


def sheet_slot(kind: str, i: int) -> tuple[int, int, int, int]:
    """VDP (x, y, w, h) of block i of a kind in the sheet (page 0)."""
    check(0 <= i < SHEET_COUNT[kind], f"no {kind} {i} in the sheet")
    if kind == "chip":
        return 16 * (i % 16), SHEET_Y + 16 * (i // 16), 16, 16
    x0, w, h = {"digit": (0, 8, 16), "light": (80, 8, 8), "bar": (96, 24, 8), "button": (144, 32, 24)}[kind]
    return x0 + w * i, SHEET_Y + 32, w, h


def check_sheet_slots() -> None:
    slots = [(k, i, sheet_slot(k, i)) for k, n in SHEET_COUNT.items() for i in range(n)]
    for j, (k, i, r) in enumerate(slots):
        check(inside(r, (0, SHEET_Y, MW, SHEET_H)) and r[0] % 2 == 0 and r[2] % 2 == 0, f"sheet {k} {i}: {r}")
        for k2, i2, r2 in slots[j + 1:]:
            check(not overlap(r, r2), f"sheet slots {k} {i} and {k2} {i2} overlap")


def tv_slot(n: int) -> tuple[int, int, int, int]:
    """VDP (x, y, w, h) of TV picture n in page 2."""
    check(0 <= n < TV_COUNT, f"no TV picture {n}")
    return TV_W * (n % 3), TV_PAGE_Y + TV_W * (n // 3), TV_W, TV_W


# ----- the Amiga data -----

def rd(puzl: bytes, addr: int, n: int) -> bytes:
    check(LOAD <= addr and addr + n <= LOAD + len(puzl), f"${addr:X}+{n} is outside PUZL")
    return puzl[addr - LOAD:addr - LOAD + n]


def words(puzl: bytes, addr: int, n: int) -> list[int]:
    return list(struct.unpack(f">{n}H", rd(puzl, addr, 2 * n)))


def planar(puzl: bytes, addr: int, w: int, h: int, planes: int, bpr: int | None = None) -> list[list[int]]:
    rd(puzl, addr, planes * h * (bpr or (w + 15) // 16 * 2))       # the range check
    return decode_indices(puzl, addr - LOAD, w, h, planes, "planes", row_bytes=bpr)


def amiga_palette(puzl: bytes, visit: int) -> list[int]:
    return [0] + words(puzl, PALS[visit - 1], 31)


def check_tables(puzl: bytes) -> None:
    """PUZL's tables and palettes against docs/BRAINSTORM.md 2.6."""
    for addr, label, what, want in PLAN_TABLES:
        got = words(puzl, addr, len(want))
        check(got == want, f"${addr:X} ({what}): {got}, the plan's {want}")
    for visit, (start, reds) in PLAN_BOARDS.items():
        for b in range(4):
            r = rd(puzl, VISIT_RECS[visit - 1] + REC_LEN * b, REC_LEN)
            cells = r[6:]
            where = f"visit {visit} board {b} (${VISIT_RECS[visit - 1] + REC_LEN * b:X})"
            check(tuple(r[:2]) == start, f"{where}: start {tuple(r[:2])}, the plan's {start}")
            check(r[2] == reds[b], f"{where}: {r[2]} red chips, the plan's {reds[b]}")
            zeros = sum(1 for c in cells if c & 15 == 0)
            check(zeros == r[2], f"{where}: {r[2]} red chips but {zeros} type-0 cells")
            check(tuple(r[3:5]) == PLAN_TIMER and r[5] == PLAN_TUNE, f"{where}: timer or tune {r[3:6].hex()}")
            check(all(c & 15 != 15 for c in cells), f"{where}: a cell of type 15")
    check(100 * sum(PLAN_BOARDS[1][1]) == PLAN_SCORE1, "visit 1's full solve is not 9,500 points")
    for addr, want, _ in PLAN_MESSAGES:
        check(rd(puzl, addr, len(want)) == want, f"${addr:X}: {rd(puzl, addr, len(want))!r}, not {want!r}")
    check(rd(puzl, RECS_END - 1, 1)[0] == PLAN_PAD, "the pad byte at $1775F")
    check(RECS + 8 * REC_LEN == PLAN_MESSAGES[0][0] and PLAN_MESSAGES[2][0] + len(PLAN_MESSAGES[2][1]) + 1 == RECS_END,
          "the records, the messages and the pad do not fill $17448-$1775F")
    for visit, text in PLAN_PALETTES.items():
        check(amiga_palette(puzl, visit)[1:] == [int(c, 16) for c in text.split()], f"visit {visit}'s palette")


class Assets:
    """PUZL's graphics for one visit, as Amiga colour indices (0-31)."""

    def __init__(self, puzl: bytes, visit: int):
        check(visit in (1, 2), f"visit {visit}")
        self.visit = visit
        self.pal = amiga_palette(puzl, visit)
        self.screen = planar(puzl, SCREEN, AW, AH, 5)
        self.chips = [planar(puzl, CHIPS + 128 * t, 16, 16, 4) for t in range(32)]
        self.face = [[v | 16 for v in r] for r in planar(puzl, FACES[visit - 1], 80, 80, 4)]
        self.noise = []
        for f in range(4):
            mk = planar(puzl, NOISE + 4000 * f, 80, 80, 1)
            col = planar(puzl, NOISE + 4000 * f + 800, 80, 80, 4)
            self.noise.append([[(col[y][x] | 16) if mk[y][x] else None for x in range(80)] for y in range(80)])
        self.digits = [planar(puzl, DIGITS + 64 * g, 8, 16, 4, 1) for g in range(10)]
        self.lights = [planar(puzl, LIGHTS + 32 * k, 8, 8, 4, 1) for k in range(2)]
        self.bars = [[r[:24] for r in planar(puzl, BARS + 128 * k, 32, 8, 4, 4)] for k in range(2)]
        self.button = [planar(puzl, BUTTON + 0x180 * k, 32, 24, 4) for k in range(2)]
        self.cursor = []
        for i in range(8):
            img = []
            for y in range(16):
                da, db = struct.unpack(">HH", rd(puzl, CURSOR + 64 * i + 4 * y, 4))
                img.append([(da >> (15 - x) & 1) | (db >> (15 - x) & 1) << 1 for x in range(16)])
            self.cursor.append(img)
        self.boards = []
        for b in range(4):
            r = rd(puzl, VISIT_RECS[visit - 1] + REC_LEN * b, REC_LEN)
            self.boards.append({"start": (r[0], r[1]), "reds": r[2], "cells": [c & 15 for c in r[6:]]})

    def block(self, kind: str, i: int) -> list[list[int]]:
        return {"chip": self.chips, "digit": self.digits, "light": self.lights, "bar": self.bars,
                "button": self.button}[kind][i]

    def tv(self, n: int) -> list[list[int]]:
        """TV picture n (TV_STATES): the face or black (COLOR16), then static frame f cut over it."""
        face_on, f = TV_STATES[n]
        img = [r[:] for r in self.face] if face_on == "F" else [[16] * 80 for _ in range(80)]
        if f is not None:
            for y in range(80):
                for x in range(80):
                    if self.noise[f][y][x] is not None:
                        img[y][x] = self.noise[f][y][x]
        return img


def blit(img: list[list[int]], src: list[list[int]], x0: int, y0: int) -> None:
    for y, r in enumerate(src):
        img[y0 + y][x0:x0 + len(r)] = r


def state_items(state: bytes):
    """(kind, i, value) for every element of a shown state that is not NONE (range-checked)."""
    check(len(state) == ST_LEN, f"a shown state has {ST_LEN} bytes, not {len(state)}")
    for kind, n in STATE:
        for i in range(n):
            v = state[ST[kind] + i]
            if v != NONE:
                check(v < ST_RANGE[kind], f"state byte {ST[kind] + i} ({kind} {i}): {v} is out of range")
                yield kind, i, v


def element_key(kind: str, i: int) -> tuple:
    if kind in ("tv", "button"):
        return (kind,)
    if kind == "cell":
        return ("cell", i % COLS, i // COLS)
    return (kind, i)


def amiga_compose(a: Assets, state: bytes, cursor: tuple | None = None) -> list[list[int]]:
    """The Amiga screen (COLOR00-31) showing a shown state, drawn as PUZL draws it."""
    img = [r[:] for r in a.screen]
    fx, fy, fw, fh = FACE_WIN
    for y in range(fy, fy + fh):
        img[y][fx:fx + fw] = [v | 16 for v in img[y][fx:fx + fw]]
    places = amiga_elements()
    for kind, i, v in state_items(state):
        x, y = places[element_key(kind, i)][:2]
        if kind == "tv":
            blit(img, a.tv(v), x, y)
        else:
            src = {"led": "digit", "timer": "digit", "cell": "chip"}.get(kind, kind)
            blit(img, a.block(src, v), x, y)
    if cursor is not None:
        c, r, n = cursor
        x, y = places[("cell", c, r)][:2]
        for yy, line in enumerate(a.cursor[n]):
            for xx, v in enumerate(line):
                if v:
                    img[y + yy][x + xx] = 16 + v
    return img


# ----- colours -----

# The stage's 16 colours a visit, hand-picked as tools/msxhud.py's HUD_PALETTE. The screen uses 24
# distinct 9-bit colours in visit 1 (the frame's 16, COLOR00-15, the same in both visits, and 8
# more of the face and the static), 26 in visit 2. The frame keeps 14: $EEE (777: 40 pixels of
# highlight) shows as 555 and $CA4 (652: 22 pixels, the lights' brightest orange) as 530. The face
# and the static get the last two entries, the pair with the least mean CIELAB error from their
# true colours (an exhaustive search, the gfx report's faceopt.py): 9.8 for visit 1. Visit 2's
# pair is PROVISIONAL (Ellen's face looks flat in 9 bits): milestone 3, the user's choice.
FRAME = [(0, 0, 0), (1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4), (5, 5, 5), (2, 0, 0), (4, 0, 0),
         (7, 1, 0), (0, 1, 0), (0, 2, 0), (2, 4, 0), (3, 1, 0), (5, 3, 0)]
FACE = {1: [(4, 3, 3), (3, 2, 2)], 2: [(6, 5, 5), (6, 4, 4)]}
NOT_FOR_FACE = {(0, 1, 0), (0, 2, 0), (2, 4, 0), (7, 1, 0), (4, 0, 0)}   # the greens, the bright reds


def lab12(c12: int) -> tuple:
    """CIELAB of an Amiga colour's true value ($RGB / 15)."""
    def lin(v):
        v /= 15
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin((c12 >> s) & 15) for s in (8, 4, 0))
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (x, y, z)]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def msx_palette(a: Assets) -> tuple[list[tuple], list[int]]:
    """The visit's 16 colours and the MSX index of each Amiga colour: its own 9-bit value when the
    palette has it, else the entry nearest its true colour in CIELAB. A face, static or cursor
    colour (COLOR16-31) never takes a green or a bright red (without that rule $321 lands on the
    PCB's dark green and puts green specks in the face)."""
    pal = FRAME + FACE[a.visit]
    check(len(pal) == 16 and len(set(pal)) == 16 and pal[0] == (0, 0, 0), "the palette")
    labs = [lab(c) for c in pal]
    remap = []
    for v in range(32):
        c = to_msx(a.pal[v]) if v else (0, 0, 0)
        if c in pal:
            remap.append(pal.index(c))
        else:
            L = lab12(a.pal[v])
            pool = [i for i in range(16) if v < 16 or pal[i] not in NOT_FOR_FACE]
            remap.append(min(pool, key=lambda i: sum((p - q) ** 2 for p, q in zip(L, labs[i]))))
        check(v < 16 or pal[remap[v]] not in NOT_FOR_FACE, f"COLOR{v} maps to a green or a bright red")
    return pal, remap


def v9938(pal: list[tuple]) -> bytes:
    return b"".join(bytes(((r << 4) | b, g)) for r, g, b in pal)


def rgb24(c: tuple, grade: bool = False) -> tuple:
    if grade:
        c = tuple(BRIGHT[v] for v in c)
    return tuple(v * 255 // 7 for v in c)


# ----- packing, sprites, VRAM -----

def pack(rows: list[list[int]]) -> bytes:
    """SCREEN 5 bytes: the left pixel in the high nibble."""
    return b"".join(bytes((r[x] << 4) | r[x + 1] for x in range(0, len(r), 2)) for r in rows)


def unpack(data: bytes, w: int) -> list[list[int]]:
    bpl = w // 2
    return [[v for b in data[i:i + bpl] for v in (b >> 4, b & 15)] for i in range(0, len(data), bpl)]


def cursor_sprites(a: Assets) -> tuple[bytes, list[tuple]]:
    """Mode-2 16 x 16 patterns: an image's colour-3 pixels (COLOR19) in one pattern; image 2's two
    colour-2 pixels (COLOR18) in one of their own. Returns the patterns and, per image, (sprite
    0's pattern, sprite 1's pattern or None)."""
    pats, use = [], []

    def pattern(img, colour):
        bits = [[1 if v == colour else 0 for v in r] for r in img]
        return bytes(sum(bits[y][half + x] << (7 - x) for x in range(8)) for half in (0, 8) for y in range(16))

    for i, img in enumerate(a.cursor):
        values = {v for r in img for v in r}
        check(values <= {0, 2, 3}, f"cursor image {i}: colours {values}")
        check((2 in values) == (i == 2), f"cursor image {i}: colour 2 only in image 2")
        pats.append(pattern(img, 3))
        pa, pb = len(pats) - 1, None
        if 2 in values:
            pats.append(pattern(img, 2))
            pb = len(pats) - 1
        use.append((pa, pb))
    return b"".join(pats), use


class Vram:
    """128 KiB of SCREEN 5 VRAM as one colour index a pixel: 256 x 1024, Y over the 4 pages."""

    def __init__(self):
        self.px = bytearray(MW * 1024)

    def copy(self) -> "Vram":
        v = Vram()
        v.px[:] = self.px
        return v

    def write(self, x: int, y: int, w: int, data: bytes) -> None:
        """CPU writes of whole lines of w pixels (w / 2 bytes a line) from (x, y) down."""
        for j, row in enumerate(unpack(data, w)):
            o = MW * (y + j) + x
            self.px[o:o + w] = bytes(row)

    def hmmm(self, sx: int, sy: int, dx: int, dy: int, w: int, h: int) -> None:
        check(sx % 2 == 0 and dx % 2 == 0 and w % 2 == 0, "HMMM on odd x or width")
        rows = [self.px[MW * (sy + j) + sx:MW * (sy + j) + sx + w] for j in range(h)]
        for j, row in enumerate(rows):
            self.px[MW * (dy + j) + dx:MW * (dy + j) + dx + w] = row

    def rows(self, x: int, y: int, w: int, h: int) -> list[list[int]]:
        return [list(self.px[MW * (y + j) + x:MW * (y + j) + x + w]) for j in range(h)]


# ----- the conversion -----

class Puzl:
    """Everything the converter makes, in memory: built and checked by the constructor."""

    def __init__(self, puzl: bytes, visits: tuple[int, ...] = (1,)):
        check(len(puzl) == PUZL_LEN, f"PUZL: {len(puzl)} bytes, not {PUZL_LEN} ($17100-$32CDF)")
        check(visits in ((1,), (1, 2)), f"visits {visits}: 1, or 1 and 2")
        check_tables(puzl)
        check_sheet_slots()
        self.puzl, self.visits = puzl, visits
        self.layout = msx_layout()
        self.assets = {v: Assets(puzl, v) for v in visits}
        self.pal, self.remap, self.tv = {}, {}, {}
        for v in visits:
            self.pal[v], self.remap[v] = msx_palette(self.assets[v])
        a, m = self.assets[1], self.remap[1]
        for name, sx, sy, w, h, dx, dy in PIECES:
            for y in range(sy, sy + h):
                for x in range(sx, sx + w):
                    check(a.screen[y][x] < 16 or inside((x, y, 1, 1), FACE_WIN),
                          f"the screen's ({x}, {y}) uses COLOR{a.screen[y][x]} outside the TV")
        scr = [[None] * MW for _ in range(MH)]
        for name, sx, sy, w, h, dx, dy in PIECES:
            for y in range(h):
                scr[dy + y][dx:dx + w] = [m[c] for c in a.screen[sy + y][sx:sx + w]]
        tx, ty, tw, th = self.layout[("tv",)]
        for y in range(ty, ty + th):
            scr[y][tx:tx + tw] = [0] * tw                  # black: the same bytes in both visits
        sheet = [[0] * MW for _ in range(SHEET_H)]
        for kind, n in SHEET_COUNT.items():
            for i in range(n):
                x, y = sheet_slot(kind, i)[:2]
                blit(sheet, [[m[c] for c in r] for r in a.block(kind, i)], x, y - SHEET_Y)
        self.screen, self.sheet = pack(scr), pack(sheet)
        for v in visits:
            b = self.assets[v]
            if v != 1:              # the screen and the sheet are shared: the frame's colours match
                check(all(self.remap[v][c] == m[c] for c in range(16)), f"visit {v}: the frame's colours")
                check(self.pal[v][:14] == self.pal[1][:14], f"visit {v}: the frame's palette")
            self.tv[v] = b"".join(pack([[self.remap[v][c] for c in r] for r in b.tv(n)]) for n in range(TV_COUNT))
        self.pats, self.use = cursor_sprites(a)
        self.blob = self.screen + self.sheet + b"".join(self.tv[v] for v in visits)
        check(len(self.screen) == GFX_SHEET and len(self.screen + self.sheet) == GFX_PAGE0, "the blob's layout")
        check(all(len(t) == GFX_TV_LEN for t in self.tv.values()), "the TV pictures' size")
        self.vram = {v: self.vram_for(v) for v in visits}
        for v in visits:
            self.check_render(v)

    def tv_offset(self, visit: int) -> int:
        """The visit's TV pictures in the blob (visit 1's when visit 2 is not built)."""
        return GFX_PAGE0 + GFX_TV_LEN * (self.visits.index(visit) if visit in self.visits else 0)

    def cursor_colours(self, visit: int) -> tuple[int, int]:
        """Sprite 0's colour (COLOR19) and sprite 1's (COLOR18) in the palette the visit shows."""
        m = self.remap[visit if visit in self.visits else 1]
        return m[19], m[18]

    def vram_for(self, visit: int) -> Vram:
        """VRAM as the stage's entry leaves it: the screen and the sheet in page 0 (page 1 is a
        copy of page 0's play area), the visit's TV pictures in page 2."""
        v = Vram()
        v.write(0, 0, MW, self.blob[:GFX_PAGE0])
        t = self.tv_offset(visit)
        for n in range(TV_COUNT):
            x, y = tv_slot(n)[:2]
            v.write(x, y, TV_W, self.blob[t + TV_BYTES * n:t + TV_BYTES * (n + 1)])
        return v

    def copies(self, state: bytes) -> list[tuple]:
        """The HMMMs (sx, sy, dx, dy, w, h) that draw a shown state into display page A, one an
        element, in the state's order (add PZ_PAGE_B to dy for page B)."""
        out = []
        for kind, i, v in state_items(state):
            if kind == "tv":
                src = tv_slot(v)
            else:
                src = sheet_slot({"led": "digit", "timer": "digit", "cell": "chip"}.get(kind, kind), v)
            dst = self.layout[element_key(kind, i)]
            check(src[2:] == dst[2:], f"{kind} {i}: source {src} and destination {dst} differ in size")
            out.append((src[0], src[1], dst[0], dst[1], dst[2], dst[3]))
        return out

    def render(self, state: bytes, cursor: tuple | None = None, visit: int = 1) -> list[list[int]]:
        """A display page's picture (MSX indices, 256 x 162) from its shown state and the cursor
        (column, row, image) of its sprite set, as the stage draws them."""
        check(visit in self.vram, f"visit {visit} is not built (--visits 1,2)")
        v = self.vram[visit].copy()
        for c in self.copies(state):
            v.hmmm(*c)
        img = v.rows(0, 0, MW, MH)
        if cursor is not None:
            c, r, n = cursor
            check(0 <= c < COLS and 0 <= r < ROWS and 0 <= n < 8, f"cursor {cursor}")
            col0, col1 = self.cursor_colours(visit)
            x0, y0 = SAT_X + 16 * c, SAT_Y + 16 * r + 1
            pa, pb = self.use[n]
            for pat, col in ((pb, col1), (pa, col0)):          # sprite 0 in front of sprite 1
                if pat is None:
                    continue
                p = self.pats[32 * pat:32 * pat + 32]
                for y in range(16):
                    for x in range(16):
                        if p[y + (16 if x >= 8 else 0)] >> (7 - (x & 7)) & 1:
                            img[y0 + y][x0 + x] = col
        return img

    def check_render(self, visit: int) -> None:
        """Renders of shown states through the VRAM model equal the Amiga's own composition of
        the same states, pixel for pixel through the pieces (the TV black where it shows NONE):
        every TV picture, digit, image, chip tile and cursor image once at least."""
        src = [[None] * MW for _ in range(MH)]
        for name, sx, sy, w, h, dx, dy in PIECES:
            for y in range(h):
                for x in range(w):
                    src[dy + y][dx + x] = (sx + x, sy + y)
        tv = self.layout[("tv",)]
        m = self.remap[visit]
        cases = [(bytes([NONE] * ST_LEN), None)]
        for k in range(TV_COUNT):
            s = [k] + [(p + k) % 10 for p in range(9)] + [(9 + i + k) % 10 for i in range(3)] + [k & 1]
            s += [(j + k) & 1 for j in range(4)] + [(j + k + 1) & 1 for j in range(4)]
            s += [(i + 3 * k) % 32 for i in range(COLS * ROWS)]
            cases.append((bytes(s), (k % COLS, k % ROWS, k % 8)))
        cases.append(preview_state(self.assets[visit]))
        for state, cursor in cases:
            msx = self.render(state, cursor, visit)
            ami = amiga_compose(self.assets[visit], state, cursor)
            for y in range(MH):
                for x in range(MW):
                    if state[ST["tv"]] == NONE and inside((x, y, 1, 1), tv):
                        want = 0
                    else:
                        sx, sy = src[y][x]
                        want = m[ami[sy][sx]]
                    check(msx[y][x] == want, f"visit {visit}: render ({x}, {y}) = {msx[y][x]}, the Amiga's {want}"
                          f" (state {state.hex()}, cursor {cursor})")

    # ----- the include files -----

    def inc_text(self) -> str:
        L = self.layout
        cell, tv, light, bar = L[("cell", 0, 0)], L[("tv",)], L[("light", 0)], L[("bar", 0)]
        led, button = L[("led", 0)], L[("button",)]
        for (kind, *ix), r in L.items():          # the strides the equates' comments promise
            if kind == "cell":
                check(r[:2] == (cell[0] + 16 * ix[0], cell[1] + 16 * ix[1]), f"cell {ix}")
            elif kind in ("light", "bar"):
                check(r[:2] == ((light if kind == "light" else bar)[0], light[1] + 8 * ix[0]), f"{kind} {ix}")
            elif kind == "led":
                check(r[:2] == (led[0] + 8 * ix[0], led[1]), f"led {ix}")
        tmr = [L[("timer", i)] for i in range(3)]
        check(len({r[1] for r in tmr}) == 1 and light[1] == bar[1], "the timer's and the rows' lines")
        out = ["; generated by tools/msxpuzl.py: Brainstorm's graphics for msx/puzl.asm (docs/BRAINSTORM.md",
               "; 3.3 and 3.9). Equates only: include it anywhere. Places are VDP coordinates: X 0-255, Y over",
               "; the 4 pages (page p from 256p); the display pages are 0 (A) and 1 (B), the sheet is in page 0",
               "; below the play area, the TV pictures in page 2. HMMM moves whole bytes: every x is even."]

        def eq(name: str, value, comment: str = "") -> None:
            v = f"0x{value:X}" if isinstance(value, int) and value >= 0x10000 else str(value)
            line = f"{name + ':':<20}equ {v}"
            out.append(f"{line:<36}; {comment}" if comment else line)

        out.append("; puzl_gfx.bin (read through the 8000h window, split at every 8 KiB boundary)")
        eq("PZ_GFX_LEN", len(self.blob), "the blob's bytes")
        eq("PZ_GFX_SCREEN", 0, "the screen, 256 x 162, the TV rectangle black")
        eq("PZ_GFX_SHEET", GFX_SHEET, "the sheet, 256 x 56, right after it")
        eq("PZ_GFX_PAGE0", GFX_PAGE0, "screen + sheet: one stream into page 0 from VRAM 0")
        eq("PZ_LINE_BYTES", LINE_BYTES, "bytes a line of the screen and the sheet")
        eq("PZ_SCREEN_LINES", MH)
        eq("PZ_SHEET_LINES", SHEET_H)
        eq("PZ_GFX_TV1", self.tv_offset(1), "visit 1's 9 TV pictures, TV_STATES order")
        eq("PZ_GFX_TV2", self.tv_offset(2), "visit 2's" + ("" if 2 in self.visits else ": visit 1's until milestone 3"))
        eq("PZ_TV_BYTES", TV_BYTES, "one picture: 80 lines of PZ_TV_LINE bytes")
        eq("PZ_TV_LINE", TV_LINE)
        eq("PZ_GFX_TV_LEN", GFX_TV_LEN, "a visit's 9 pictures")
        eq("PZ_VISITS", len(self.visits), "visits with their own TV pictures and palette")
        out.append("; the play area: display page A (page 0); page B: Y + PZ_PAGE_B")
        eq("PZ_PAGE_B", 256)
        eq("PZ_COLS", COLS)
        eq("PZ_ROWS", ROWS)
        eq("PZ_CELL_X", cell[0], "cell (c, r) at (PZ_CELL_X + 16c, PZ_CELL_Y + 16r)")
        eq("PZ_CELL_Y", cell[1])
        eq("PZ_CELL_W", 16, "and its height")
        eq("PZ_TV_X", tv[0], "the TV picture, PZ_TV_W x PZ_TV_W")
        eq("PZ_TV_Y", tv[1])
        eq("PZ_TV_W", TV_W)
        eq("PZ_LIGHT_X", light[0], "the light of row k at (PZ_LIGHT_X, PZ_ROW_Y + 8k)")
        eq("PZ_BAR_X", bar[0], "the bar of row k at (PZ_BAR_X, PZ_ROW_Y + 8k)")
        eq("PZ_ROW_Y", light[1])
        eq("PZ_LED_X", led[0], "LED position p at (PZ_LED_X + 8p, PZ_LED_Y)")
        eq("PZ_LED_Y", led[1])
        eq("PZ_TMIN_X", tmr[0][0], "the timer's minutes (the dash at 226 is in the screen)")
        eq("PZ_TTEN_X", tmr[1][0], "its tens of seconds")
        eq("PZ_TUNIT_X", tmr[2][0], "its seconds")
        eq("PZ_TIMER_Y", tmr[0][1])
        eq("PZ_BUTTON_X", button[0], "the button")
        eq("PZ_BUTTON_Y", button[1])
        eq("PZ_SAT_X", SAT_X, "the cursor over cell (c, r): SAT X = PZ_SAT_X + 16c,")
        eq("PZ_SAT_Y", SAT_Y, "  Y = PZ_SAT_Y + 16r (mode 2 shows it a line lower)")
        out.append("; the blocks' sizes")
        for name, (w, h) in (("DIGIT", (8, 16)), ("LIGHT", (8, 8)), ("BAR", (24, 8)), ("BUTTON", (32, 24))):
            eq(f"PZ_{name}_W", w)
            eq(f"PZ_{name}_H", h)
        out.append("; the sheet (page 0): the sources of the HMMMs")
        eq("PZ_SHEET_Y", SHEET_Y, "its first line")
        eq("PZ_CHIP_SX", sheet_slot("chip", 0)[0], "chip tile t at (PZ_CHIP_SX + 16 (t & 15),")
        eq("PZ_CHIP_SY", sheet_slot("chip", 0)[1], "  PZ_CHIP_SY + 16 (t >> 4))")
        for kind, what in (("digit", "digit k"), ("light", "light image k (0 bright, 1 dark)"),
                           ("bar", "bar image k (0 bright, 1 dark)"), ("button", "button image k")):
            x, y, w, h = sheet_slot(kind, 0)
            check(sheet_slot(kind, 1)[:2] == (x + w, y), f"the sheet's {kind} stride")
            n = kind.upper()
            eq(f"PZ_{n}_SX", x, f"{what} at (PZ_{n}_SX + {w}k, PZ_{n}_SY)")
            eq(f"PZ_{n}_SY", y)
        out.append("; the TV pictures (page 2): picture n at (80 (n % 3), PZ_TVPIC_Y + 80 (n / 3)); its line y")
        out.append("; at VRAM PZ_TV_VRAM + 128 (80 (n / 3) + y) + 40 (n % 3)")
        eq("PZ_TVPIC_Y", TV_PAGE_Y)
        eq("PZ_TV_VRAM", 0x10000, "page 2's first byte")
        for n in range(TV_COUNT):
            x, y = tv_slot(n)[:2]
            face, f = TV_STATES[n]
            what = "the face" if face == "F" else "black"
            what += f" + static frame {f}" if f is not None else ", no static"
            eq(f"PZ_TV{n}_SX", x, what)
            eq(f"PZ_TV{n}_SY", y)
        eq("PZ_TV_FACE", TV_FACE, "picture PZ_TV_FACE + f: the face under static frame f")
        eq("PZ_TV_BLACK", TV_BLACK, "PZ_TV_BLACK + f: black under static frame f")
        eq("PZ_TV_CLEAN", TV_CLEAN, "the face alone (after the last board)")
        out.append("; the cursor: puzl_cursor.spr, an image's pattern for sprite 0 (its colour-3 pixels) and")
        out.append("; for sprite 1 (its colour-2 pixels, image 2 only; 255: none); the SAT holds 4 x the pattern")
        eq("PZ_CUR_PATS", len(self.pats) // 32, "patterns of 32 bytes (mode 2: left 8 columns, then right 8)")
        for i, (pa, pb) in enumerate(self.use):
            eq(f"PZ_CURA_{i}", pa)
        for i, (pa, pb) in enumerate(self.use):
            eq(f"PZ_CURB_{i}", 255 if pb is None else pb)
        for v in (1, 2):
            c0, c1 = self.cursor_colours(v)
            note = "" if v in self.visits else " (visit 1's palette until milestone 3)"
            eq(f"PZ_CUR_COL_{v}", c0, f"visit {v}: sprite 0's colour (COLOR19){note}")
            eq(f"PZ_CUR_COL2_{v}", c1, f"visit {v}: sprite 1's colour (COLOR18)")
        out.append("; a display page's shown state (PZ_ST_LEN bytes): what each element shows, PZ_ST_NONE = the")
        out.append("; screen's own pixels (never drawn)")
        what = {"tv": "the TV picture 0-8", "led": "9 LED digits 0-9, position p at + p",
                "timer": "3 timer digits 0-9: minutes, tens of seconds, seconds", "button": "the button's image 0-1",
                "light": "4 light images 0-1, row k at + k", "bar": "4 bar images 0-1, row k at + k",
                "cell": "88 chip tiles 0-31 (the cells' values), cell (c, r) at + 11r + c"}
        for kind, n in STATE:
            eq(f"PZ_ST_{kind.upper()}", ST[kind], what[kind])
        eq("PZ_ST_LEN", ST_LEN)
        eq("PZ_ST_NONE", f"0x{NONE:02X}")
        out.append("; the boards (puzl_tab.inc pzt_recs: $17448-$1775F)")
        eq("PZ_REC_LEN", REC_LEN, "a board: start column, row, red chips, timer MM SS (BCD),")
        eq("PZ_REC_COL", 0, "  tune, then the 88 cells row by row")
        eq("PZ_REC_ROW", 1)
        eq("PZ_REC_REDS", 2)
        eq("PZ_REC_TIMER", 3)
        eq("PZ_REC_TUNE", 5)
        eq("PZ_REC_CELLS", 6)
        eq("PZ_BOARDS_LEN", 4 * REC_LEN, "a visit's 4 boards (pz_boards)")
        eq("PZ_RECS_V1", VISIT_RECS[0] - RECS, "visit 1's boards in pzt_recs ($17448)")
        eq("PZ_RECS_V2", VISIT_RECS[1] - RECS, "visit 2's ($175C0)")
        eq("PZ_RECS_LEN_V1", RECS_END - VISIT_RECS[0], "copied to PZ_TAB on visit 1: up to $1775F")
        eq("PZ_RECS_LEN_V2", RECS_END - VISIT_RECS[1], "on visit 2")
        for (addr, _, text), name in zip(PLAN_MESSAGES, ("TIMEOUT", "MALFUNCTION", "RESTORED")):
            eq(f"PZ_MSG_{name}", addr - RECS, f'"{text}" in pzt_recs (${addr:X})')
        return "\n".join(out) + "\n"

    def tab_text(self) -> str:
        recs = rd(self.puzl, RECS, RECS_END - RECS)
        out = ["; generated by tools/msxpuzl.py: PUZL's tables for msx/puzl.asm (BANK_PUZL), read from PUZL",
               "; ($17100) and checked against docs/BRAINSTORM.md 2.6. Data: include it once. Words hold the",
               "; 68000's values (dw: little-endian), indexed as the 68000 indexes them.",
               "pzt_recs:                           ; $17448-$1775F: 8 boards of 94 bytes (visit 1: 0-3; visit 2:",
               "                                    ; 4-7, from + PZ_RECS_V2), 3 messages, a pad byte"]
        for b in range(8):
            r = recs[REC_LEN * b:REC_LEN * (b + 1)]
            out.append(f"        ; ${RECS + REC_LEN * b:X}: visit {1 + b // 4} board {b % 4}: start ({r[0]}, {r[1]}),"
                       f" {r[2]} red chips, {r[3]:X}:{r[4]:02X}, tune {r[5]}")
            out.append("        db " + ", ".join(f"0x{v:02X}" for v in r[:6]))
            for row in range(ROWS):
                out.append("        db " + ", ".join(f"0x{v:02X}" for v in r[6 + COLS * row:6 + COLS * (row + 1)]))
        for addr, want, text in PLAN_MESSAGES:
            out.append(f'        ; ${addr:X}: "{text}" (the HUD font\'s codes, FF-ended)')
            out.append("        db " + ", ".join(f"0x{v:02X}" for v in want))
        out.append(f"        db 0x{recs[-1]:02X}                         ; $1775F: a pad byte")
        for addr, label, what, want in PLAN_TABLES:
            vals = [w // ROW_BYTES for w in want] if label == "pzt_rows" else want
            note = " / 320 (a row: 8 lines of 40 bytes)" if label == "pzt_rows" else ""
            out.append(f"{label + ':':<36}; ${addr:X}{note}: {what}")
            out.append("        dw " + ", ".join(f"0x{v:04X}" if label == "pzt_curofs" else str(v) for v in vals))
        return "\n".join(out) + "\n"


def parse_data(text: str) -> dict[str, bytes]:
    """The bytes each label of a generated data include assembles to (db/dw lines only)."""
    out, label = {}, None
    for line in text.splitlines():
        code = line.split(";")[0]
        m = re.match(r"^(\w+):", code)
        if m:
            label = m.group(1)
            out[label] = b""
            code = code[m.end():]
        m = re.match(r"^\s*(db|dw)\s+(.*)$", code)
        if m:
            vals = [int(v, 0) for v in m.group(2).split(",")]
            out[label] += bytes(vals) if m.group(1) == "db" else b"".join(struct.pack("<H", v) for v in vals)
    return out


def preview_state(a: Assets) -> tuple[bytes, tuple]:
    """The previews' moment (the gfx report's): board 1 with a few cells visited, the cursor
    (image 2) on the last or the next one, TV picture F + static 1, the LED row's static digits,
    1:00, the light and the bar of row 1 lit."""
    visited = [(0, 0), (0, 1), (0, 2)] if a.visit == 1 else [(5, 3), (5, 2)]
    cursor = (0, 3, 2) if a.visit == 1 else (5, 2, 2)
    s = [NONE] * ST_LEN
    s[ST["tv"]] = 1
    s[ST["led"]:ST["led"] + 9] = [0, 1, 3, 8, 4, 7, 4, 8, 6]
    s[ST["timer"]:ST["timer"] + 3] = [1, 0, 0]
    s[ST["button"]] = 0
    s[ST["light"] + 1] = 0
    s[ST["bar"] + 1] = 0
    for i, t in enumerate(a.boards[1]["cells"]):
        s[ST["cell"] + i] = t + (16 if (i % COLS, i // COLS) in visited else 0)
    return bytes(s), cursor


# ----- previews -----

def png(path: Path, img: list[list[int]], cols: list[tuple], scale: int = 1) -> None:
    rows = []
    for r in img:
        line = b"".join(bytes(cols[v]) * scale for v in r)
        rows += [line] * scale
    write_png(path, len(img[0]) * scale, len(rows), rows)


def hud_rows(folder: Path, grade: bool) -> list[bytes] | None:
    """The HUD as msx/hud.asm shows it (tools/msxhud.py's hud.sc5 and hud.pal), if it is there."""
    sc5, hp = folder / "hud.sc5", folder / "hud.pal"
    if not (sc5.exists() and hp.exists()):
        return None
    data, p = sc5.read_bytes(), hp.read_bytes()
    cols = [rgb24(((p[2 * i] >> 4) & 7, p[2 * i + 1] & 7, p[2 * i] & 7), grade) for i in range(16)]
    return [b"".join(bytes(cols[b >> 4]) + bytes(cols[b & 15]) for b in data[i:i + LINE_BYTES])
            for i in range(0, len(data), LINE_BYTES)]


def previews(p: Puzl, out: Path) -> list[Path]:
    """The previews of every visit built; returns the files written."""
    files = []

    def put(path: Path, img, cols, scale):
        png(path, img, cols, scale)
        files.append(path)

    for v in p.visits:
        a, pal, m = p.assets[v], p.pal[v], p.remap[v]
        plain, graded = [rgb24(c) for c in pal], [rgb24(c, True) for c in pal]
        stem = f"{out}_{v}"
        put(Path(stem + "_screen.png"), unpack(p.screen, MW), plain, 3)
        put(Path(stem + "_sheet.png"), unpack(p.sheet, MW), plain, 3)
        grid = [[0] * (3 * 82) for _ in range(3 * 82)]
        for n in range(TV_COUNT):
            blit(grid, unpack(p.tv[v][TV_BYTES * n:TV_BYTES * (n + 1)], TV_W), 82 * (n % 3), 82 * (n // 3))
        put(Path(stem + "_tv.png"), grid, plain, 3)
        state, cursor = preview_state(a)
        msx = p.render(state, cursor, v)
        for name, cols, grade in (("plain", plain, False), ("graded", graded, True)):
            rows = [b"".join(bytes(cols[c]) for c in r) for r in msx]
            hud = hud_rows(out.parent, grade)
            if hud is not None:
                rows += [bytes(3 * MW)] * 5 + hud     # the 5 blank lines, then the HUD (msx.inc)
            s = 3
            big = [b"".join(r[3 * x:3 * x + 3] * s for x in range(MW)) for r in rows for _ in range(s)]
            path = Path(f"{stem}_display_{name}.png")
            write_png(path, MW * s, len(big), big)
            files.append(path)
        ami = amiga_compose(a, state, cursor)
        acol = [tuple(((c >> sh) & 15) * 17 for sh in (8, 4, 0)) for c in a.pal]
        s = 2
        rows_a = [b"".join(bytes(acol[c]) * s for c in r) for r in ami]
        rows_p = [b"".join(bytes(plain[c]) * s for c in r) for r in msx]
        rows_g = [b"".join(bytes(graded[c]) * s for c in r) for r in msx]
        gap = bytes((255, 255, 255)) * 8
        comp = []
        for y in range(AH):
            lp = rows_p[y] if y < MH else bytes(3 * MW * s)
            lg = rows_g[y] if y < MH else bytes(3 * MW * s)
            comp += [rows_a[y] + gap + lp + gap + lg] * s
        path = Path(f"{stem}_amiga_vs_msx.png")
        write_png(path, len(comp[0]) // 3, len(comp), comp)
        files.append(path)
    # the cursor's 8 images as the sprites show them (visit 1's colours)
    c0, c1 = p.cursor_colours(1)
    cols = [rgb24(c) for c in p.pal[1]]
    s, rows = 6, []
    for y in range(16):
        line = b""
        for n in range(8):
            img = [[None] * 16 for _ in range(16)]
            pa, pb = p.use[n]
            for pat, col in ((pb, c1), (pa, c0)):
                if pat is not None:
                    q = p.pats[32 * pat:32 * pat + 32]
                    for yy in range(16):
                        for xx in range(16):
                            if q[yy + (16 if xx >= 8 else 0)] >> (7 - (xx & 7)) & 1:
                                img[yy][xx] = col
            line += b"".join(bytes(cols[v] if v is not None else (20, 60, 20)) * s for v in img[y])
            line += bytes((255, 255, 255)) * s
        rows += [line] * s
    path = Path(f"{out}_cursor.png")
    write_png(path, len(rows[0]) // 3, len(rows), rows)
    files.append(path)
    return files


# ----- main -----

def convert(src: Path, out: Path, visits: tuple[int, ...]) -> int:
    p = Puzl(src.read_bytes(), visits)
    out.parent.mkdir(parents=True, exist_ok=True)
    written = []

    def put(path: Path, data) -> None:
        if isinstance(data, str):
            path.write_text(data)
        else:
            path.write_bytes(data)
        written.append(path)

    for v in visits:
        put(Path(f"{out}_{v}.pal"), v9938(p.pal[v]))
    put(Path(f"{out}_gfx.bin"), p.blob)
    put(Path(f"{out}_cursor.spr"), p.pats)
    inc, tab = p.inc_text(), p.tab_text()
    data = parse_data(tab)
    check(data["pzt_recs"] == rd(p.puzl, RECS, RECS_END - RECS), "puzl_tab.inc: pzt_recs")
    for addr, label, what, want in PLAN_TABLES:
        vals = [w // ROW_BYTES for w in want] if label == "pzt_rows" else want
        check(data[label] == b"".join(struct.pack("<H", w) for w in vals), f"puzl_tab.inc: {label}")
    put(Path(f"{out}.inc"), inc)
    put(Path(f"{out}_tab.inc"), tab)
    written += previews(p, out)
    for v in visits:
        print(f"visit {v}: palette {' '.join('%d%d%d' % c for c in p.pal[v])}")
        print("  Amiga colour -> MSX index: " + " ".join(f"{c}:{p.remap[v][c]}" for c in range(32)))
        c0, c1 = p.cursor_colours(v)
        print(f"  cursor: sprite 0 colour {c0} (COLOR19), sprite 1 colour {c1} (COLOR18)")
    print(f"cursor patterns (sprite 0/1 per image): {' '.join(f'{a}/{255 if b is None else b}' for a, b in p.use)}")
    print(f"{out}_gfx.bin: {len(p.blob)} bytes = {len(p.blob) / 8192:.2f} banks: screen {len(p.screen)} + sheet "
          f"{len(p.sheet)} + TV {' + '.join(str(len(p.tv[v])) for v in visits)}")
    print("checks passed: the tables (plan 2.6), the red chips, the pieces, the elements' places, the colours, "
          f"the renders against the Amiga ({TV_COUNT + 2} states a visit)")
    print("wrote " + " ".join(f.name for f in written))
    return 0


def render_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="msxpuzl.py render", description="a display page's picture from its shown state")
    ap.add_argument("puzl", type=Path, help="PUZL_25.bin")
    ap.add_argument("state", help=f"a file holding the {ST_LEN} bytes (at --offset), or hex digits with --hex")
    ap.add_argument("out", type=Path, help="writes OUT.sc5 and OUT.png")
    ap.add_argument("--offset", type=lambda s: int(s, 0), default=0, help="the state's offset in the file")
    ap.add_argument("--hex", action="store_true", help="STATE is the bytes as hex digits")
    ap.add_argument("--cursor", help="C,R,I: the cursor over column C, row R, image I (0-7)")
    ap.add_argument("--visit", type=int, choices=(1, 2), default=1, help="the visit's TV pictures and palette")
    ap.add_argument("--grade", action="store_true", help="the PNG in the graded colours (as the ROM shows them)")
    ap.add_argument("--scale", type=int, default=1)
    a = ap.parse_args(argv)
    if a.hex:
        state = bytes.fromhex(a.state.replace(" ", ""))
    else:
        state = Path(a.state).read_bytes()[a.offset:a.offset + ST_LEN]
    check(len(state) == ST_LEN, f"the state has {len(state)} bytes, not {ST_LEN}")
    cursor = tuple(int(v) for v in a.cursor.split(",")) if a.cursor else None
    check(cursor is None or len(cursor) == 3, "--cursor C,R,I")
    p = Puzl(a.puzl.read_bytes(), (1, 2) if a.visit == 2 else (1,))
    img = p.render(state, cursor, a.visit)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.with_suffix(".sc5").write_bytes(pack(img))
    png(a.out.with_suffix(".png"), img, [rgb24(c, a.grade) for c in p.pal[a.visit]], a.scale)
    shown = sorted({k for k, i, v in state_items(state)})
    print(f"{a.out.with_suffix('.sc5')}, {a.out.with_suffix('.png')}: visit {a.visit}, drawn: "
          f"{', '.join(shown) or 'nothing'}; cursor {cursor if cursor else 'hidden'}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "render":
        return render_main(argv[2:])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("puzl", type=Path, help="PUZL_25.bin (loaded at $17100)")
    ap.add_argument("out", type=Path, help="the output prefix, e.g. build/msx/puzl")
    ap.add_argument("--visits", default="1", choices=("1", "1,2"),
                    help="1 (milestone 1), or 1,2 (visit 2's palette and TV pictures: milestone 3)")
    a = ap.parse_args(argv[1:])
    return convert(a.puzl, a.out, tuple(int(v) for v in a.visits.split(",")))


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except ValueError as e:
        raise SystemExit(f"msxpuzl.py: {e}")
