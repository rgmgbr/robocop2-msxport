#!/usr/bin/env python3
"""The shooting range (FRNG, the second bonus stage after level 1) in SCREEN 5 for msx/frng.asm:
the 320 x 172 street kept 1:1 in VRAM and shown through a 256-pixel camera, its 16 colours, the
sheets of pictures the stage copies from, the hit test's data, the line sprites and FRNG's tables
(docs/RANGE.md 3.3, 3.4 and 3.11; from the graphics report's prototype of 2026-10-27).

Source: build/extracted/files/FRNG_15.bin, crunched: tools/bytekiller.py decrunches it (the
game's $124A6) to the 170,970 bytes FRNG holds at $1EA00-$485D9 (checksum 0). Every address below
is one the stage's code reads (REA, Ghidra provider, on the level-1 RAM image with FRNG at $1EA00,
sha256 9470791f...5f3d91a; names in analysis/frng_1ea00.sym):
  $3E062  the clean street: 5 sequential planes of 320 x 172 ($1AE0 apart), copied to the shown
          buffer $769B0 at the set-up and restored from by every erase
  $466C2  the 6th plane: the scenery in front of the pop-ups ($1EDBC's first blit, mode $B50: a
          pop-up shows and can be hit only where it is clear); then 1,080 bytes of FFh
  $2CC62-$3E061  the pictures: a mask plane, then 5 planes, each (w - 1) words x h (BLTSIZE's w
          counts the shift's spare word): 8 pop-ups, 6 walkers, 5 riser frames, 18 dissolve
          frames (types 1-3: frames 0-11; type 4: frames 16-21)
  $1EF88  42 script entries of 4 words; $1F472-$1F501 the 23 stubs (lea descriptor,A0;
          bra $1F50C); $1F60E 23 pop-up descriptors of 22 bytes
  $1F1C2 / $1F1EA / $1F200  the riser's graphic, BLTSIZE and row by frame 0-9
  $1F248-$1F329  the walkers' row, clip, threshold, x offset, BLTSIZE and graphic by kind 0-15
  $1F8AA / $1F8E8 / $1F974 / $1F979  the dissolves' BLTSIZE and graphic by frame, first and end
          frame by type
  $1FBEA / $1FC2A  COLOR01-31 of visit 1 / visit 2 (AG $8050 >= 2); COLOR00 is black
  $1EB46, $1F246, $1F46C, $1F502, $1F60E  the state FRNG keeps in its code, which the port keeps
          in fr_code (526 bytes in the mirror's rule)

The MSX (docs/RANGE.md 3.3): the street stays 320 wide in VRAM; the view shows Amiga columns s to
s + 255 (s = 0-64, the camera) and rows 10-171 on lines 0-161 (MSX x = Amiga x - s, MSX y = Amiga
y - 10). A display page is built at a coarse offset c (a multiple of 16) and R#18 shows it at s
(c - s in -7..8). Every Amiga colour takes its 9-bit rounding (tools/msxhud.py to_msx), one index
map for both visits: 0 the scene's black, 1 the sheets' black (LMMM/TIMP skips index 0), 15 the
crosshair's green, 14 free. Only the vertical lines are sprites; everything else is drawn by the
VDP: HMMM restores from the clean scene in page 2, then LMMM/TIMP of the pictures (a pop-up
clipped to its position's rectangle, then that position's front layer: the scene's pixels where
the 6th plane is set), then the lines.

Outputs (OUT = the prefix, e.g. build/msx/range):
  OUT_1.pal, OUT_2.pal  visit 1's and visit 2's 16 colours, V9938 pairs (R << 4 | B, G), plain
                  (tools/mkrom.py grades them: decision 8, game play)
  OUT_gfx.bin     63,616 bytes of raw nibbles (the left pixel high): the scene's columns 64-319
                  (162 lines x 128 bytes into page 2 line 0); the strip of columns 0-63 (81 lines
                  x 64 bytes: rows 10-90 and rows 91-171 side by side, page 2 line 162); then the
                  sheets S0 and S1 (page 0 / page 1 from line 162, 128 bytes a line), S2 (page 2
                  from line 162 at x 128, 64 bytes a line) and S3 (page 3 from line 88)
  OUT_hit.bin     the hit test's data (3.4), 2 banks: the 6th plane $466C2 (6,880 bytes, 40 a
                  row) and the file's FFh after it, padded with FFh to 8 KiB; then the masks of the
                  8 pop-up, 6 walker and 5 riser pictures as in FRNG, by address (4,896 bytes)
  OUT_line.spr    16 sprite patterns of 32 bytes (mode 2: left 8 columns, then right 8): column 0
                  set on rows 0..k
  OUT.inc         equates only (include it anywhere): the view, the camera rule, the VRAM map, the
                  blob's streams, the sheets, the positions and their front layers, the pictures'
                  indices, the colour indices, the sprites' geometry, the hit data's layout and the
                  recent-blit list's bound, a display page's shown state, fr_code's layout
  OUT_tab.inc     data for BANK_FRNG: fr_code's initial 526 bytes, FRNG's tables in the 68000's
                  layout, the script kinds, the pictures (keyed by the Amiga address: the sheet
                  block, its trim, the mask's offset in OUT_hit.bin) and the positions
  OUT_*.png       previews: the stored scene and sheets; moments at s = 0, 32 and 64, plain and
                  graded, with the HUD below them when OUT's folder holds hud.sc5 and hud.pal
                  (tools/msxhud.py); visit 2; the Amiga against the MSX

Checks (any failure stops the tool): the decrunch's length and checksum; FRNG's tables, its code
state and both palettes against docs/RANGE.md 2.6 and the logic report's tables; every colour the
stage shows keeps its rounding; the scene uses no index 1, 14 or 15; no sheet pixel inside a mask
is 0; every pop-up's visible pixels lie in its position's rectangle, which meet no other; the
blocks fit their areas without overlap and never meet the scene; OUT_hit.bin's bytes equal the
file's; the SAT never holds more than 31 entries or 3 sprites a line; and the sweep: every pop-up
at every slide step, the riser, the walkers, every dissolve frame, mixed and full moments, the
pairs of quirk 4, composed through the VRAM model (the blob, the sheets' coordinates, the
renderer's rules, R#18) against a model of the original's own composition: 0 pixels differ in the
view. The model leaves out the original's display quirks 1-3 (docs/RANGE.md 2.8) and quirk 4: a
pop-up's second blit writes its whole word-aligned box (16 w x h from (X & FFF0h) - 128), the clean
copy wherever its mask is clear, so where that box meets another position's rectangle it wipes
the columns of a pop-up drawn there earlier in the same pass (7 descriptors: OUT's log lists
them). The port keeps that pop-up whole (the zero-glitch rule, as quirk 1); the sweep counts the
pixels quirk 4 would wipe and checks that each lies in such a box and rectangle.

Render mode (the reference of the stills, docs/RANGE.md 4.2): a display page's picture from its
shown state (OUT.inc RG_ST_*: RG_ST_LEN bytes) at the camera s, built as the stage builds it: the
scene at the page's c, the elements in z-order, the sprites, then R#18 = (s - c) & 15 with level
1's sign (msx/scroll9938.asm: nibble 8 moves the picture 8 pixels right, 7 moves it 7 left; the
columns it uncovers show the border, colour 0). It writes OUT.sc5 (the 256 x 162 picture as shown,
sprites included, SCREEN 5 bytes), OUT_page.sc5 (the page's lines 0-161 as VRAM holds them: no
sprites, no shift), OUT.sat (the SAT the state implies: 4 bytes an entry, then Y = 216) and
OUT.png. STATE is a file (RG_ST_LEN bytes at --offset, + --page x RG_ST_LEN) or, with --hex, the
bytes as hex digits. The camera is the state's own s, or --cam S, or --r18 N (the register's
value). --sat FILE draws the sprites from a SAT dump (a set's 128 bytes) instead, with the line
patterns.

Python 3 standard library only.

usage: msxrange.py FRNG_15.bin OUT
       msxrange.py render FRNG_15.bin STATE OUT [--offset N] [--page P] [--hex] [--cam S | --r18 N]
                  [--sat FILE [--sat-offset N]] [--visit 1|2] [--grade] [--scale N]
"""
from __future__ import annotations

import argparse
import hashlib
import random
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bytekiller import unpack  # noqa: E402
from msxhud import to_msx  # noqa: E402
from msxpuzl import hud_rows, pack, parse_data, rgb24, v9938  # noqa: E402
from planar import write_png  # noqa: E402

# ----- the Amiga side: FRNG at $1EA00 -----

LOAD, FRNG_LEN = 0x1EA00, 170970               # $1EA00-$485D9
SHOWN, PLANE, AW, AH = 0x3E062, 0x1AE0, 320, 172
PRIO = SHOWN + 5 * PLANE                       # $466C2, the 6th plane
PRIO_END = PRIO + PLANE                        # $481A2: 1,080 bytes of FFh up to the file's end
PALS = (0x1FBEA, 0x1FC2A)                      # COLOR01-31; $1FC2A when AG $8050 >= 2 ($1FB52)
XBIAS = 128                                    # a BOB's D0 and a sprite's H: bitplane x + 128
SCRIPTS, NSCRIPTS, SPAWNED = 0x1EF88, 42, range(1, 40)   # the spawn picks scripts 1-39 ($1F112)
RTS = 0x1F0D8                                  # the scripts' unused second word points here
H_POPUP, H_MOVE, H_RISE = 0x1F50C, 0x1F32A, 0x1F14E
STUBS = (0x1F472, 0x1F502)                     # 23 stubs: lea descriptor(PC),A0; bra $1F50C
DESCS, NDESC, DLEN = 0x1F60E, 23, 22
RISE_GFX, RISE_SIZE, RISE_ROW, RISE_FRAMES = 0x1F1C2, 0x1F1EA, 0x1F200, 10
WALK_ROW, WALK_CLIP, WALK_THR, WALK_XOFF, WALK_SIZE, WALK_GFX, WALK_KINDS = (
    0x1F248, 0x1F268, 0x1F288, 0x1F2A8, 0x1F2CA, 0x1F2EA, 16)
FX_SIZE, FX_GFX, FX_FIRST, FX_END, FX_FRAMES = 0x1F8AA, 0x1F8E8, 0x1F974, 0x1F979, 22
FX_STORED = list(range(0, 12)) + list(range(16, 22))   # frames 12-15 repeat 8-11 and are never used
# fr_code (docs/RANGE.md 3.2): the state FRNG keeps in its code, these ranges one after another
FR_CODE = ((0x1EB46, 6), (0x1F246, 2), (0x1F46C, 2), (0x1F502, 10), (0x1F60E, 506))
# the right clip $1EE42: the file's value, which $1F3F6 writes back after its draw; every pop-up draw's
CLIP_FILE, CLIP_POPUP = 0x1F4, 0x258
RISE_X = range(0x82, 0x82 + 256)               # $1F14E: X = $82 + ($B00 & $FF)
WALK_X = range(0x159, 0x199)                   # $1F32A: X from $198 down to $159 and back, + offset
FX_DX, FX_DY = 6, -8                           # a walker's dissolve at X + 6; every one at D1 - 8

# docs/RANGE.md 2.6 and the logic report's tables/ (descriptors_1f60e.txt, big_rise_1f1c2.txt,
# big_move_1f246.txt, effects_1f8aa.txt, scripts_1ef88.txt, small_tables.txt)
PLAN_PALETTES = {
    1: "777 666 555 444 333 222 111 654 543 432 321 601 501 400 300 211 40A 309 208 107 105 200 310 "
       "000 120 741 631 520 410 111 3F3",
    2: "555 444 333 222 111 000 000 431 321 322 210 401 301 200 100 211 105 107 208 309 40A 100 100 "
       "000 120 641 522 420 400 000 3F3",
}
# per script 0-41: "-" (empty), "M" (h_move), "R" (h_rise) or the pop-up's descriptor; the hit effect's type
PLAN_SCRIPTS = [("-", 0)] + [(d, t) for d, t in (
    (0x1F758, 3), (0x1F716, 3), (0x1F700, 2), (0x1F7F2, 3), (0x1F7C6, 3), (0x1F76E, 3), (0x1F79A, 3),
    (0x1F63A, 3), (0x1F67C, 2), (0x1F692, 2), (0x1F6A8, 2), (0x1F6BE, 2), (0x1F6D4, 2))] + \
    [("M", 1)] * 9 + [("R", 4)] * 3 + [(d, t) for d, t in (
        (0x1F7DC, 3), (0x1F7B0, 3), (0x1F784, 3), (0x1F742, 3), (0x1F72C, 3), (0x1F6EA, 2), (0x1F67C, 2),
        (0x1F6A8, 2), (0x1F60E, 3), (0x1F624, 2), (0x1F63A, 2), (0x1F650, 3), (0x1F6A8, 2), (0x1F6A8, 2),
        (0x1F650, 2), (0x1F6A8, 3))]
# per descriptor: position, coordinate A, B's base, passes to slide, speed, passes held, horizontal,
# BLTSIZE, graphic, threshold
PLAN_DESCS = """
1F60E 0 130  60 14 -2 80 0 0783 2CF32  0     1F624 1 192  58 14 -2 80 0 0783 2CF32  0
1F63A 2 188 134 14 -2 80 0 0783 2CF32  0     1F650 3 252 128 14 -2 80 0 0783 2CF32  0
1F666 3  99 280 16 -2 96 1 0A03 2DE32 99     1F67C 3  94 282 16 -2 94 1 0A03 2DA72 24
1F692 1  24 218 18 -2 96 1 0A03 2DA72 24     1F6A8 2  99 218 18 -2 96 1 0A03 2DE32 99
1F6BE 1  24 218 18 -2 96 1 0A03 2DE32 99     1F6D4 2  99 218 18 -2 90 1 0A03 2DA72 24
1F6EA 0  25 156  8 -3 80 1 0A03 2DE32 99     1F700 2 180 136 18 -2 90 0 0A03 2DA72 24
1F716 4 320  66 11 -2 80 0 0783 2CF32  0     1F72C 4 320  66 11 -2 80 0 0783 2D7A2 99
1F742 7 318 128 14 -2 96 0 0783 2D4D2 99     1F758 8 100 380  8 -2 96 1 0782 2CDCA 99
1F76E 8 356 128 14 -2 80 0 0783 2CF32  0     1F784 5 358  68 24 -1 80 0 0783 2D202 24
1F79A 5  44 380 16 -1 80 1 0782 2CDCA 99     1F7B0 6  44 416  8 -2 96 1 0782 2CDCA 99
1F7C6 6  43 382  9  2 96 1 0783 2CF32  0     1F7DC 7 324 124 24 -1 96 0 0782 2CC62 99
1F7F2 7 100 286 16  2 96 1 0783 2CF32  0
"""
PLAN_RISE = [(0x33922, 0x0405, 156), (0x33322, 0x0805, 140), (0x32A22, 0x0C05, 124), (0x31D02, 0x1185, 102),
             (0x30C82, 0x1605, 84)]
PLAN_RISE = PLAN_RISE + PLAN_RISE[::-1]
# per kind 0-15: row, clip, threshold, x offset, BLTSIZE, graphic
PLAN_WALK = [(96, 0x1A0, 0, 0, 0x0E05, 0x33C22), (87, 0x1A0, 0, 0, 0x1004, 0x2E972),
             (96, 0x1A0, 99, 0, 0x0E03, 0x2F272), (96, 0x1A0, 0, 0, 0x0E04, 0x2F7B2),
             (92, 0x1A0, 32, 0, 0x0F04, 0x2FF92), (104, 0x1A0, 0, 0, 0x0C03, 0x30802),
             (114, 0x1C0, 0, 34, 0x0E05, 0x33C22), (105, 0x1C0, 0, 34, 0x1004, 0x2E972),
             (114, 0x1C0, 99, 34, 0x0E03, 0x2F272), (112, 0x1C0, 99, 34, 0x0E03, 0x2F272),
             (114, 0x1C0, 0, 34, 0x0E04, 0x2F7B2), (110, 0x1C0, 32, 34, 0x0F04, 0x2FF92),
             (122, 0x1C0, 0, 34, 0x0C03, 0x30802), (96, 0x1A0, 99, 0, 0x0E03, 0x2F272),
             (114, 0x1C0, 99, 34, 0x0E03, 0x2F272), (96, 0x1A0, 99, 0, 0x0E03, 0x2F272)]
PLAN_FX = [(0x1003, g) for g in (0x36562, 0x36B62, 0x37162, 0x37762)] + \
          [(0x0A03, g) for g in (0x352A2, 0x35662, 0x35A22, 0x35DE2)] + \
          [(0x0803, g) for g in (0x346A2, 0x349A2, 0x34CA2, 0x34FA2)] * 2 + \
          [(0x1605, g) for g in (0x37D62, 0x38DE2, 0x39E62, 0x3AEE2, 0x3BF62, 0x3CFE2)]
PLAN_FX_TYPES = [(0, 4), (0, 4), (4, 8), (8, 12), (16, 22)]    # $1F974 / $1F979 by type 0-4
PLAN_CODE = {0x1EB46: "00 00 FF 18 FF FF", 0x1F246: "00 14", 0x1F46C: "01 C0",
             0x1F502: "00 00 00 00 00 00 FF 00 00 00"}      # position 6 locked (quirk T2)
PLAN_PRIO_SET = 48077                          # of the 6th plane's 55,040 pixels (docs/RANGE.md 2.8)

# ----- the MSX side -----

TOP, VIEW_H, SCENE_W, VIEW_W = 10, 162, 320, 256
CAM_MAX, CAM_START = SCENE_W - VIEW_W, 32
BAND_LO, BAND_HI = 64, 191                     # the camera keeps cx - s in 64..191 when it can
ADJ_LO, ADJ_HI = 5, 240                        # RG_ADJ=0 (docs/RANGE.md 6): s in 16-px steps, cx - s in 5..240
SHIFT_MIN, SHIFT_MAX = -7, 8                   # what R#18 can show: c - s
LINE_DX = 111                                  # the crosshair's line: bitplane x $B9A - 111, the hit column
                                               # (docs/RANGE.md default 17)
SIDE_DX = 113                                  # the box's sides: bitplane x H - 113 (the H - 128 inference, pixel 15)
EDGE_DX = 112                                  # the box's edges from bitplane x C - 16n - 112 ($1ED5A: byte H/8 - 14)
EDGE_ROWS = 158                                # $1ED5A draws rows 0-157 only
SIDE_TOP = -2                                  # a side shows when its top row Y - 16n >= -2 (sprite DMA from $20:
                                               # default 18)
SPR_ROWS = 168                                 # the Amiga's sprites stop at line $CA: rows 0-167
SPR_LINES = SPR_ROWS - TOP                     # the MSX's: lines 0-157
SPR_MAX, SPR_PER_LINE, SAT_END = 30, 3, 216
LINE_PATS = 16
BLACK, DUP, FREE, GREEN = 0, 1, 14, 15
NONE = 0xFF
LINE_BYTES = 128
# VRAM (VDP x, y; y over the 4 pages): the sheet areas (name, x, y, w, lines) the packer may fill
AREAS = [
    ("S0", 0, 162, 256, 94),                   # page 0 below display page A
    ("S1", 0, 256 + 162, 256, 94),             # page 1 below display page B
    ("S2", 128, 512 + 162, 128, 94),           # page 2 beside the scene's strip
    ("S3", 0, 768 + 88, 256, 74),              # page 3 between the atlas and line 162
]
PAGE_B, SCENE_Y = 256, 512                     # display page B's first line; the clean scene (page 2)
SPLIT_COL, STRIP_ROWS = 64, 81                 # Amiga columns 0-63 in the strip, as two blocks of 81 lines
STRIP_Y, STRIP_X2 = 512 + 162, 64              # the strip: lines 0-80 at x 0-63, lines 81-161 at x 64-127
SPR_PAT, SPR_COL_A, SPR_COL_B = 0x1D800, 0x1E000, 0x1E400    # msx/msx.inc: the patterns and both sets
SAT_OFS = 0x200                                # a set's SAT after its colour table
HIT_PRIO, HIT_STRIDE, HIT_MASKS, HIT_LEN0 = 0, 40, 0x2000, 0x2000   # OUT_hit.bin: the plane's bank, then the masks'
BLITS_ROOM = 0xF800 - 0xF70E                   # docs/RANGE.md 3.2: the recent-blit list's RAM, F70Eh-F7FFh

# a display page's shown state (docs/RANGE.md 3.3), words little-endian
ST_FIELDS = [("C", 0, 1, "the page's coarse offset c: 0, 16, 32, 48 or 64; RG_NONE: never built"),
             ("S", 1, 1, "the camera s it was published for (0-64): R#18 = (s - c) & 15"),
             ("POP", 2, 12, "2 pop-up slots of RG_POP_LEN, slot k at + k x RG_POP_LEN"),
             ("BIG", 14, 7, "the big target drawn by $1F3F6 (RG_BIG_...)"),
             ("FX", 21, 5, "the dissolve frame drawn by $1F83A (RG_FX_...)"),
             ("CROSS", 26, 4, "the crosshair at the pass's end: $B9A (0: none), $B9E (dw each)"),
             ("BOX", 30, 5, "the fire box (RG_BOX_...)")]
ST_LEN = 35
POP_LEN, BIG_LEN, FX_LEN = 6, 7, 5
ST_SUB = [("POP_PLACE", 0, "db the position 0-8 (the descriptor's +0); RG_NONE: no pop-up"),
          ("POP_PIC", 1, "db the picture (its index in rgt_pics)"),
          ("POP_X", 2, "dw D0 of its draw: bitplane x + 128"),
          ("POP_Y", 4, "dw D1: the Amiga row of its top"),
          ("BIG_PIC", 0, "db the picture; RG_NONE: none"),
          ("BIG_X", 1, "dw $BAE"), ("BIG_Y", 3, "dw $BB0"),
          ("BIG_CLIP", 5, "dw $1F46C: the right clip, bitplane x clip - 128"),
          ("FX_PIC", 0, "db the frame's picture; RG_NONE: none"),
          ("FX_X", 1, "dw $B56"), ("FX_Y", 3, "dw $B66"),
          ("BOX_N", 0, "db n 1-8 ($1EB4A's value for this pass); RG_NONE or 0: none"),
          ("BOX_C", 1, "dw its centre: (4 + $B9A) & FFF0h before the pass's move"),
          ("BOX_Y", 3, "dw $B9E before the move")]
K_NONE, K_POPUP, K_MOVE, K_RISE = 0, 1, 2, 3
PIC_LEN, PLACE_LEN = 12, 8


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def s16(v: int) -> int:
    v &= 0xFFFF
    return v - 0x10000 if v & 0x8000 else v


def mirror(data: bytes) -> bytes:
    """The mirror's rule (words little-endian: the byte at A at A ^ 1)."""
    check(len(data) % 2 == 0, "mirror: an odd length")
    b = bytearray(data)
    b[0::2], b[1::2] = data[1::2], data[0::2]
    return bytes(b)


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def camera(s: int, b9a: int) -> int:
    """docs/RANGE.md 3.3's rule, once a pass: the crosshair's line cx kept in the view's middle band."""
    cx = b9a - LINE_DX
    return clamp(clamp(s, cx - BAND_HI, cx - BAND_LO), 0, CAM_MAX)


def camera_ring(s: int, b9a: int) -> int:
    """The V9958's ring (msx/frng.asm rg_cam with rgr_ring): the view is the 248 columns s..s + 247
    (MSK hides screen x 0-7), so the band ends 8 columns sooner and s goes up to CAM_MAX + 8."""
    cx = b9a - LINE_DX
    return clamp(clamp(s, cx - (BAND_HI - 8), cx - BAND_LO), 0, CAM_MAX + 8)


def camera_steps(s: int, b9a: int) -> int:
    """The RG_ADJ=0 build's rule (docs/RANGE.md 6: R#18 always 0), once a pass: s a multiple of 16
    that moves only when the crosshair's line would leave cx - s in ADJ_LO..ADJ_HI."""
    cx = b9a - LINE_DX
    if s < cx - ADJ_HI:
        s = (cx - ADJ_HI + 15) & ~15
    if s > cx - ADJ_LO:
        s = (cx - ADJ_LO) & ~15
    return clamp(s, 0, CAM_MAX)


def page_c(s: int) -> int:
    """The coarse offset a page shows s from: the multiple of 16 in s - 7..s + 8."""
    return (s + 8) >> 4 << 4


def r18_shift(r18: int) -> int:
    """How far R#18's low nibble moves the picture right (msx/scroll9938.asm: 8 is +8, 7 is -7)."""
    v = r18 & 15
    return -v if v <= 7 else 16 - v


def overlap(a: tuple, b: tuple) -> bool:
    """Do two rectangles (x, y, w, h) share a pixel?"""
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


# ----- FRNG's data -----

BITS = [tuple(i for i in range(8) if v & (0x80 >> i)) for v in range(256)]


class Frng:
    """FRNG decrunched, as the 68000 sees it at $1EA00, with its tables decoded and checked."""

    def __init__(self, data: bytes):
        check(len(data) == FRNG_LEN, f"FRNG: {len(data)} bytes, not {FRNG_LEN} ($1EA00-$485D9)")
        self.data = data
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.pal12 = {v: [0] + [self.w(PALS[v - 1] + 2 * i) for i in range(31)] for v in (1, 2)}
        self.scripts = self.decode_scripts()
        self.descs = self.decode_descs()
        self.rise = [(self.l(RISE_GFX + 4 * f), self.w(RISE_SIZE + 2 * f), self.sw(RISE_ROW + 2 * f))
                     for f in range(RISE_FRAMES)]
        self.walk = [(self.sw(WALK_ROW + 2 * k), self.w(WALK_CLIP + 2 * k), self.sw(WALK_THR + 2 * k),
                      self.sw(WALK_XOFF + 2 * k), self.w(WALK_SIZE + 2 * k), self.l(WALK_GFX + 4 * k))
                     for k in range(WALK_KINDS)]
        self.fx = [(self.w(FX_SIZE + 2 * f), self.l(FX_GFX + 4 * f)) for f in range(FX_FRAMES)]
        self.fx_types = [(self.data[FX_FIRST + t - LOAD], self.data[FX_END + t - LOAD]) for t in range(5)]
        self.check_tables()

    # the 68000's reads
    def rd(self, a: int, n: int) -> bytes:
        check(LOAD <= a and a + n <= LOAD + FRNG_LEN, f"${a:X}: outside FRNG")
        return self.data[a - LOAD:a - LOAD + n]

    def w(self, a: int) -> int:
        return struct.unpack(">H", self.rd(a, 2))[0]

    def sw(self, a: int) -> int:
        return struct.unpack(">h", self.rd(a, 2))[0]

    def l(self, a: int) -> int:
        return struct.unpack(">I", self.rd(a, 4))[0]

    def decode_scripts(self) -> list[dict]:
        out = []
        for n in range(NSCRIPTS):
            a = SCRIPTS + 8 * n
            w0, w1, typ, w3 = struct.unpack(">hhhh", self.rd(a, 8))
            e = {"n": n, "addr": a, "words": (w0, w1, typ, w3), "type": typ, "kind": K_NONE, "desc": None}
            handler = a + w0
            if n == 0:
                check((w0, w1, typ, w3) == (0, 0, 0, 0), "script 0 is not empty ($1EF88)")
            elif handler == H_MOVE:
                e["kind"] = K_MOVE
            elif handler == H_RISE:
                e["kind"] = K_RISE
            else:
                check(STUBS[0] <= handler < STUBS[1], f"script {n}: handler ${handler:X} is no stub")
                e["kind"], e["desc"] = K_POPUP, self.stub(handler)
            if n:
                check(a + 2 + w1 == RTS and w3 == 0, f"script {n}: words 1 and 3 (${a:X})")
            out.append(e)
        return out

    def stub(self, a: int) -> int:
        """lea d16(PC),A0 then bra.s/bra.w $1F50C: the descriptor."""
        check(self.w(a) == 0x41FA, f"stub ${a:X}: not lea d16(PC),A0")
        desc = a + 2 + self.sw(a + 2)
        op = self.w(a + 4)
        target = a + 6 + (self.sw(a + 6) if op == 0x6000 else s16((op & 0xFF) << 8) >> 8)
        check(op >> 8 == 0x60 and target == H_POPUP, f"stub ${a:X}: no bra $1F50C")
        return desc

    def decode_descs(self) -> list[dict]:
        out = []
        for k in range(NDESC):
            a = DESCS + DLEN * k
            d = self.rd(a, DLEN)
            e = {"addr": a, "place": d[0], "A": s16(d[2] << 8 | d[3]), "B": s16(d[4] << 8 | d[5]), "slide": d[7],
                 "step": s16(d[8] << 8 | d[9]), "stay": d[10], "horiz": d[11] != 0, "blt": d[12] << 8 | d[13],
                 "ptr": struct.unpack(">I", d[14:18])[0], "thr": s16(d[20] << 8 | d[21])}
            # $1F538: D0 = +2, D1 = +4 + the offset (0, step, .., slide x step): the offset moves y, or x
            # when +B is set (D0 and D1 exchanged)
            offs = [e["step"] * i for i in range(e["slide"] + 1)]
            e["pos"] = [(e["B"] + o, e["A"]) if e["horiz"] else (e["A"], e["B"] + o) for o in offs]
            out.append(e)
        return out

    def check_tables(self) -> None:
        for v in (1, 2):
            want = [0] + [int(c, 16) for c in PLAN_PALETTES[v].split()]
            check(self.pal12[v] == want, f"visit {v}'s palette (${PALS[v - 1]:X}): not docs/RANGE.md 2.6's")
        for e, (want, typ) in zip(self.scripts, PLAN_SCRIPTS):
            kind = {K_NONE: "-", K_MOVE: "M", K_RISE: "R", K_POPUP: e["desc"]}[e["kind"]]
            check((kind, e["type"]) == (want, typ), f"script {e['n']} (${e['addr']:X}): {kind}, effect {e['type']}")
        rows = PLAN_DESCS.split()
        for e, k in zip(self.descs, range(0, len(rows), 11)):
            r = rows[k:k + 11]
            want = (int(r[0], 16), int(r[1]), int(r[2]), int(r[3]), int(r[4]), int(r[5]), int(r[6]), r[7] == "1",
                    int(r[8], 16), int(r[9], 16), int(r[10]))
            got = (e["addr"], e["place"], e["A"], e["B"], e["slide"], e["step"], e["stay"], e["horiz"], e["blt"],
                   e["ptr"], e["thr"])
            check(got == want, f"descriptor ${e['addr']:X}: {got}")
        check(len(rows) == 11 * NDESC, "PLAN_DESCS")
        check(self.rise == [(g, b, r) for g, b, r in PLAN_RISE], "the riser's tables ($1F1C2, $1F1EA, $1F200)")
        check(self.walk == PLAN_WALK, "the walkers' tables ($1F248-$1F329)")
        check(self.fx == PLAN_FX, "the dissolves' tables ($1F8AA, $1F8E8)")
        check(self.fx_types == PLAN_FX_TYPES, "the dissolves' first and end frames ($1F974, $1F979)")
        for a, want in PLAN_CODE.items():
            check(self.rd(a, len(want.split())) == bytes.fromhex(want), f"the code state at ${a:X}")
        prio = sum(bin(b).count("1") for b in self.rd(PRIO, PLANE))
        check(prio == PLAN_PRIO_SET, f"the 6th plane sets {prio} pixels, not {PLAN_PRIO_SET}")
        check(self.rd(PRIO_END, LOAD + FRNG_LEN - PRIO_END) == b"\xff" * (LOAD + FRNG_LEN - PRIO_END),
              "$481A2-$485D9: not FFh")

    def planes(self, addr: int, w: int, h: int, n: int, plane: int | None = None) -> list[bytearray]:
        """n sequential planes of w x h pixels (w a multiple of 16) as rows of colour indices."""
        bpr = w // 8
        ps = plane or bpr * h
        rows = [bytearray(w) for _ in range(h)]
        for p in range(n):
            bit = 1 << p
            for y in range(h):
                row = rows[y]
                for bx, v in enumerate(self.rd(addr + p * ps + y * bpr, bpr)):
                    for i in BITS[v]:
                        row[8 * bx + i] |= bit
        return rows

    def bob(self, ptr: int, blt: int) -> tuple[list[bytearray], list[bytearray]]:
        """A picture of $1EDBC: (its mask, its colours), (w - 1) words x h each."""
        w, h = 16 * ((blt & 0x3F) - 1), blt >> 6
        size = w // 8 * h
        return self.planes(ptr, w, h, 1), self.planes(ptr + size, w, h, 5, size)

    def fr_code(self) -> bytes:
        """fr_code's initial 526 bytes, as the file holds them (the 68000's order)."""
        return b"".join(self.rd(a, n) for a, n in FR_CODE)


def decrunch(crunched: bytes) -> bytes:
    """FRNG_15.bin through $124A6: checked for its length and checksum."""
    u = unpack(crunched)
    check(u.checksum == 0 and u.longs_read == u.longs,
          f"FRNG_15: checksum {u.checksum:08X}, {u.longs_read} of {u.longs} longs read")
    check(len(u.data) == FRNG_LEN, f"FRNG_15 decrunches to {len(u.data)} bytes, not {FRNG_LEN}")
    return u.data


# ----- colours -----

def palettes(f: Frng, used: set[int]) -> tuple[dict, list[int]]:
    """One index map for both visits, every colour its 9-bit rounding (the prototype's)."""
    p = f.pal12
    pairs, remap = [], {}
    for c in range(32):
        key = (to_msx(p[1][c]), to_msx(p[2][c]))
        if c == 31:
            remap[c] = GREEN
        elif key == ((0, 0, 0), (0, 0, 0)):
            remap[c] = BLACK
        elif c in used:
            if key not in pairs:
                pairs.append(key)
            remap[c] = 2 + pairs.index(key)
    check(len(pairs) <= 12, f"{len(pairs)} colours for indices 2-13")
    pal = {1: [(0, 0, 0)] * 16, 2: [(0, 0, 0)] * 16}
    for i, (a, b) in enumerate(pairs):
        pal[1][2 + i], pal[2][2 + i] = a, b
    pal[1][GREEN], pal[2][GREEN] = to_msx(p[1][31]), to_msx(p[2][31])
    for c in range(32):                        # colours the stage never shows: the nearest entry
        if c not in remap:
            k = to_msx(p[1][c]) + to_msx(p[2][c])
            remap[c] = min(range(2, 14), key=lambda i: sum(abs(u - v) for u, v in zip(pal[1][i] + pal[2][i], k)))
    return pal, [remap[c] for c in range(32)]


# ----- VRAM: a shelf packer, the model -----

def pack_blocks(blocks: list[tuple]) -> tuple[dict, list[int]]:
    """Blocks (key, w, h), the tallest first, into the AREAS' shelves: {key: (x, y)} and each area's
    next free line (the prototype's packer)."""
    shelves = []                               # [area, shelf y, shelf h, next x]
    used_y = [a[2] for a in AREAS]
    place = {}
    for key, w, h in sorted(blocks, key=lambda b: (-b[2], -b[1])):
        for s in shelves:
            a = AREAS[s[0]]
            if h <= s[2] and s[3] + w <= a[1] + a[3]:
                place[key] = (s[3], s[1])
                s[3] += w
                break
        else:
            for i, a in enumerate(AREAS):
                if used_y[i] + h <= a[2] + a[4] and w <= a[3]:
                    shelves.append([i, used_y[i], h, a[1] + w])
                    place[key] = (a[1], used_y[i])
                    used_y[i] += h
                    break
            else:
                raise ValueError(f"block {key} {w} x {h} does not fit the sheet areas")
    return place, used_y


class Vram:
    """128 KiB of SCREEN 5 VRAM as one colour index a pixel: 1024 rows of 256, Y over the 4 pages."""

    def __init__(self):
        self.px = [bytearray(256) for _ in range(1024)]

    def put(self, x: int, y: int, rows) -> None:
        for j, r in enumerate(rows):
            self.px[y + j][x:x + len(r)] = bytes(r)

    def stream(self, x: int, y: int, w: int, lines: int) -> bytes:
        """The bytes of w pixels a line from (x, y) down: what the stage writes there, line by line."""
        return pack([self.px[y + j][x:x + w] for j in range(lines)])


class State:
    """A display page's shown state (docs/RANGE.md 3.3; OUT.inc RG_ST_*). Coordinates are the
    68000's: X = bitplane x + 128, Y the row; the pictures are rgt_pics indices."""

    def __init__(self, c: int = CAM_START, s: int | None = None, pops=(None, None), big=None, fx=None,
                 cross=None, box=None):
        self.c, self.s = c, c if s is None else s
        self.pops = list(pops)                 # (place, pic, X, Y) or None, slot 0 then slot 1
        self.big = big                         # (pic, X, Y, clip) or None
        self.fx = fx                           # (pic, X, Y) or None
        self.cross = cross                     # ($B9A, $B9E) or None
        self.box = box                         # (n, C, Y) or None

    def to_bytes(self) -> bytes:
        b = bytearray([NONE] * ST_LEN)
        b[0], b[1] = self.c, self.s
        for k, p in enumerate(self.pops):
            if p:
                struct.pack_into("<BBhh", b, 2 + POP_LEN * k, *p)
        if self.big:
            struct.pack_into("<Bhhh", b, 14, *self.big)
        if self.fx:
            struct.pack_into("<Bhh", b, 21, *self.fx)
        struct.pack_into("<hh", b, 26, *(self.cross or (0, 0)))
        if self.box:
            struct.pack_into("<Bhh", b, 30, *self.box)
        return bytes(b)

    @classmethod
    def from_bytes(cls, b: bytes) -> "State":
        check(len(b) == ST_LEN, f"a shown state has {ST_LEN} bytes, not {len(b)}")
        pops = [struct.unpack_from("<BBhh", b, 2 + POP_LEN * k) for k in range(2)]
        big, fx = struct.unpack_from("<Bhhh", b, 14), struct.unpack_from("<Bhh", b, 21)
        cross, box = struct.unpack_from("<hh", b, 26), struct.unpack_from("<Bhh", b, 30)
        return cls(b[0], b[1], [p if p[0] != NONE else None for p in pops], big if big[0] != NONE else None,
                   fx if fx[0] != NONE else None, cross if cross[0] else None,
                   box if box[0] not in (0, NONE) else None)


# ----- the conversion -----

class Range:
    """Everything the converter makes, in memory: built and checked by the constructor."""

    def __init__(self, frng: bytes, sweep: bool = True):
        f = self.f = Frng(frng)
        self.bg = f.planes(SHOWN, AW, AH, 5, PLANE)
        self.prio = f.planes(PRIO, AW, AH, 1, PLANE)
        # the pictures the stage draws: the spawned pop-ups' (scripts 1-39), the riser's, the
        # walkers', the stored dissolve frames'
        self.used_desc = sorted({s["desc"] for s in f.scripts if s["n"] in SPAWNED and s["desc"]})
        self.desc = {e["addr"]: e for e in f.descs}
        kinds = {}
        uses = [("pop-up", self.desc[a]["ptr"], self.desc[a]["blt"]) for a in self.used_desc] + \
               [("riser", g, b) for g, b, _ in f.rise] + [("walker", g, b) for *_, b, g in f.walk] + \
               [("dissolve", f.fx[fr][1], f.fx[fr][0]) for fr in FX_STORED]
        for kind, ptr, blt in uses:
            check(kinds.setdefault(ptr, (kind, blt)) == (kind, blt), f"picture ${ptr:X}: two kinds or sizes")
        self.pics = sorted(kinds)              # rgt_pics: by Amiga address
        self.pic_index = {p: i for i, p in enumerate(self.pics)}
        self.kind = {p: kinds[p][0] for p in self.pics}
        self.blt = {p: kinds[p][1] for p in self.pics}
        self.bobs = {p: f.bob(p, self.blt[p]) for p in self.pics}
        check(len({p & 0xFFFF for p in self.pics}) == len(self.pics), "two pictures share an address's low word")
        used = {v for r in self.bg for v in r} | {31}
        for p in self.pics:
            mask, cols = self.bobs[p]
            used |= {c for mr, cr in zip(mask, cols) for m, c in zip(mr, cr) if m}
        self.used_colours = used
        self.pal, self.remap = palettes(f, used)
        self.places = self.place_rects()
        self.check_colours()
        # the sheet blocks: the trimmed pictures, then the positions' front layers
        self.scene = [bytes(self.remap[v] for v in self.bg[y]) for y in range(TOP, AH)]
        self.block_img, self.trim, blocks = {}, {}, []
        for p in self.pics:
            mask, cols = self.bobs[p]
            tx, ty, tw, th = trim(mask)
            img = [bytes((self.remap[cols[ty + j][tx + i]] or DUP) if mask[ty + j][tx + i] else 0 for i in range(tw))
                   for j in range(th)]
            check(all(v for j, r in enumerate(img) for i, v in enumerate(r) if mask[ty + j][tx + i]),
                  f"picture ${p:X}: a pixel inside its mask is 0")
            self.block_img[p], self.trim[p] = img, (tx, ty, tw, th)
            blocks.append((p, tw, th))
        for q, (x, y, w, h) in self.places.items():
            img = [bytes((self.remap[self.bg[y + j][x + i]] or DUP) if self.prio[y + j][x + i] else 0
                         for i in range(w)) for j in range(h)]
            self.block_img[("front", q)] = img
            blocks.append((("front", q), w, h))
        self.blocks = blocks
        self.place, self.used_y = pack_blocks(blocks)
        # VRAM as rg_show leaves it: the scene, the strip, the sheets
        self.vram = Vram()
        for key, w, h in blocks:
            self.vram.put(*self.place[key], self.block_img[key])
        self.vram.put(0, SCENE_Y, [r[SPLIT_COL:] for r in self.scene])
        self.vram.put(0, STRIP_Y, [r[:SPLIT_COL] for r in self.scene[:STRIP_ROWS]])
        self.vram.put(STRIP_X2, STRIP_Y, [r[:SPLIT_COL] for r in self.scene[STRIP_ROWS:]])
        self.check_layout()
        # the scene as the restores read it back from page 2 (320 a line)
        self.vscene = [bytes(self.vram.px[STRIP_Y + (y if y < STRIP_ROWS else y - STRIP_ROWS)]
                             [(0 if y < STRIP_ROWS else STRIP_X2):][:SPLIT_COL]) + bytes(self.vram.px[SCENE_Y + y])
                       for y in range(VIEW_H)]
        check(self.vscene == self.scene, "the scene does not read back from page 2")
        # the outputs
        self.streams = [("SCENE", 0, SCENE_Y, 256, VIEW_H), ("STRIP", 0, STRIP_Y, 128, STRIP_ROWS)] + \
                       [(a[0], a[1], a[2], a[3], self.used_y[i] - a[2]) for i, a in enumerate(AREAS)]
        self.blob = b"".join(self.vram.stream(x, y, w, n) for _, x, y, w, n in self.streams)
        self.hit, self.mask_ofs = self.hit_data()
        self.pats = line_patterns()
        self.sizes = self.blit_sizes()
        self.check_sat()
        self.quirk4 = self.box_overlaps()
        self.sweep_report = self.sweep() if sweep else None

    # ----- geometry -----

    def place_rects(self) -> dict[int, tuple]:
        """Per position: the bounding box of every pixel a pop-up there can show (its mask and not
        the 6th plane, over its whole slide): the clip of its draws and its front layer."""
        vis = {}
        for a in self.used_desc:
            e = self.desc[a]
            mask, _ = self.bobs[e["ptr"]]
            s = vis.setdefault(e["place"], set())
            for X, Y in e["pos"]:
                for j, row in enumerate(mask):
                    for i in (i for i, m in enumerate(row) if m):
                        x, y = X - XBIAS + i, Y + j
                        if 0 <= x < AW and 0 <= y < AH and not self.prio[y][x]:
                            s.add((x, y))
        rects = {}
        for q, s in sorted(vis.items()):
            xs, ys = [p[0] for p in s], [p[1] for p in s]
            rects[q] = (min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)
        r = list(rects.items())
        for i, (q, a) in enumerate(r):
            for q2, b in r[i + 1:]:
                check(not overlap(a, b), f"the rectangles of positions {q} and {q2} overlap")
        return rects

    def check_colours(self) -> None:
        for c in sorted(self.used_colours):
            for v in (1, 2):
                want = to_msx(self.f.pal12[v][c])
                check(self.pal[v][self.remap[c]] == want, f"visit {v}: colour {c} shows {self.pal[v][self.remap[c]]}, "
                                                          f"not its rounding {want}")
        check(not {self.remap[v] for r in self.bg[TOP:] for v in r} & {DUP, FREE, GREEN},
              "the scene uses index 1, 14 or 15")
        check(self.pal[1][DUP] == self.pal[2][DUP] == self.pal[1][BLACK] == (0, 0, 0), "index 1 is not black")

    def check_layout(self) -> None:
        occ = {}
        for key, w, h in self.blocks:
            x, y = self.place[key]
            check(any(a[1] <= x and x + w <= a[1] + a[3] and a[2] <= y and y + h <= a[2] + a[4] for a in AREAS),
                  f"block {key} outside the sheet areas")
            for j in range(h):
                for i in range(w):
                    check((x + i, y + j) not in occ, f"blocks {key} and {occ.get((x + i, y + j))} overlap")
                    occ[(x + i, y + j)] = key
        for x0, y0, w, h in ((0, SCENE_Y, 256, VIEW_H), (0, STRIP_Y, 128, STRIP_ROWS)):
            check(not any((x0 + i, y0 + j) in occ for j in range(h) for i in range(w)), "a block meets the scene")

    def hit_data(self) -> tuple[bytes, dict]:
        """OUT_hit.bin: the 6th plane and the FFh after it, to 8 KiB; then the 19 masks by address."""
        f = self.f
        plane = f.rd(PRIO, LOAD + FRNG_LEN - PRIO)            # the plane, then the file's 1,080 FFh
        out = bytearray(plane + b"\xff" * (HIT_MASKS - len(plane)))
        ofs = {}
        for p in self.pics:
            if self.kind[p] == "dissolve":
                continue                       # no used test reads them (docs/RANGE.md 3.4)
            n = 2 * ((self.blt[p] & 0x3F) - 1) * (self.blt[p] >> 6)
            ofs[p] = len(out)
            out += f.rd(p, n)
        check(len(ofs) == 19, f"{len(ofs)} masks, not 19")
        for p, o in ofs.items():
            n = 2 * ((self.blt[p] & 0x3F) - 1) * (self.blt[p] >> 6)
            check(out[o:o + n] == f.rd(p, n) and (o >> 13) == ((o + n - 1) >> 13), f"the mask ${p:X}")
        check(out[:PLANE] == f.rd(PRIO, PLANE) and len(out) - HIT_MASKS == 4896, "OUT_hit.bin")
        return bytes(out), ofs

    def blit_sizes(self) -> dict[int, set]:
        """Every output size 2 w' h of $1EDBC's first blit (docs/RANGE.md 3.4) over every call the
        tables allow: the recent-blit list's sizes strictly fall, so it never holds more entries
        than there are sizes. The clip of each call: a pop-up's draw sets $258, its erase finds $258
        or $1F4; the riser's draw $1F4; a walker's draw its kind's clip; the big erase and the
        dissolves find $1F4 or $258."""
        sizes = {}

        def add(blt: int, xs, clips, what: str) -> None:
            w, h = blt & 0x3F, blt >> 6
            wb = 2 * (w - 1)
            for X in xs:
                for clip in clips:
                    t = s16(wb * 8 + X - clip)
                    wp = w
                    if t >= 0:
                        k = t >> 4
                        if 0x26 - wb + 2 * k >= 0x28:
                            continue           # clipped to nothing: no blit, no entry ($1ED56)
                        wp = w - k
                    sizes.setdefault(2 * wp * h, set()).add(what)

        f = self.f
        pop_x = set()
        for a in self.used_desc:
            e = self.desc[a]
            xs = [X for X, _ in e["pos"]]
            pop_x |= set(xs)
            add(e["blt"], xs, (CLIP_POPUP, CLIP_FILE), "pop-ups")
        for g, b, _ in f.rise:
            add(b, RISE_X, (CLIP_FILE,), "the riser")
        walk_x = set()
        for row, clip, thr, xoff, b, g in f.walk:
            xs = [X + xoff for X in WALK_X]
            walk_x |= set(xs)
            add(b, xs, (clip,), "the walkers")
            add(b, xs, (CLIP_FILE,), "the walkers' erases")
        fx_x = pop_x | set(RISE_X) | {X + FX_DX for X in walk_x}
        for fr in FX_STORED:
            add(f.fx[fr][0], sorted(fx_x), (CLIP_FILE, CLIP_POPUP), "the dissolves")
        return dict(sorted(sizes.items()))

    # ----- the sprites -----

    def sat(self, st: State) -> list[tuple[int, int, int]]:
        """(SAT y, x, pattern 0-15) in the order the stage writes them: the crosshair's line, then
        the box's left and right sides; x in the page (R#18 moves them with the bitmap)."""
        out = []
        if st.cross:
            x = st.cross[0] - LINE_DX - st.c
            if 0 <= x < 256:
                out += column(x, 0, SPR_LINES)
        if st.box:
            n, cb, yb = st.box
            top = yb - 16 * n
            if top >= SIDE_TOP:
                for h in (cb - 16 * n, cb + 16 * n):
                    x = h - SIDE_DX - st.c
                    if 0 <= x < 256:
                        out += column(x, top - TOP, 32 * n)
        return out

    def check_sat(self) -> None:
        """At most 30 sprites (31 SAT entries with the terminator) and 3 on a line, for every box
        and crosshair the stage can show (rows on its lattice, every n, both page ends)."""
        worst = 0
        for n in range(1, 9):
            for yb in range(16, 159, 2):
                for b9a, c in ((124, 0), (240, 32), (408, 64), (240, 0), (240, 64)):
                    st = State(c, c, cross=(b9a, yb), box=(n, (4 + b9a) & 0xFFF0, yb))
                    sat = self.sat(st)
                    edge = [0] * 257                   # +1 at a sprite's first line, -1 after its last
                    for sy, x, k in sat:
                        top = sy + 1 if sy < SAT_END else sy + 1 - 256
                        check(0 <= top and top + k < SPR_LINES, f"a sprite outside lines 0-157: {st.__dict__}")
                        edge[top] += 1
                        edge[top + k + 1] -= 1
                    on, most = 0, 0
                    for v in edge:
                        on += v
                        most = max(most, on)
                    check(len(sat) <= SPR_MAX and most <= SPR_PER_LINE,
                          f"the SAT for {st.__dict__}: {len(sat)} sprites, {most} on a line")
                    worst = max(worst, len(sat))
        self.sat_worst = worst

    # ----- the MSX picture -----

    def page_rows(self, st: State) -> list[bytearray]:
        """The page as the stage builds it from the state: lines 0-161, the scene at its c, then
        the elements in the original's z-order (docs/RANGE.md 3.3)."""
        c = st.c
        check(c in range(0, CAM_MAX + 1, 2), f"a page's c is {c}, not even in 0..64 (multiples of 16 for "
              "R#18; any even c for the V9958's ring, msx/frngview.asm)")
        rows = [bytearray(r[c:c + VIEW_W]) for r in self.vscene]        # HMMM from page 2
        for p in st.pops:
            if p:
                place, pic, X, Y = p
                check(place in self.places and pic < len(self.pics), f"a pop-up ({place}, {pic})")
                px, py, pw, ph = self.places[place]
                clip = (px, py, px + pw - 1, py + ph - 1)
                self.lmmm(rows, c, self.pics[pic], X - XBIAS, Y, clip)
                self.lmmm(rows, c, ("front", place), px, py, clip)
        if st.big:
            pic, X, Y, clip = st.big
            check(pic < len(self.pics), f"the big target's picture {pic}")
            self.lmmm(rows, c, self.pics[pic], X - XBIAS, Y, (-1024, -1024, clip - XBIAS - 1, 1024))
        if st.fx:
            pic, X, Y = st.fx
            check(pic < len(self.pics), f"the dissolve's picture {pic}")
            self.lmmm(rows, c, self.pics[pic], X - XBIAS, Y)
        for y, x0, x1 in self.lines(st):
            if TOP <= y < TOP + VIEW_H:
                a, b = max(x0, c) - c, min(x1, c + VIEW_W) - c
                if a < b:
                    rows[y - TOP][a:b] = bytes([GREEN]) * (b - a)
        return rows

    def lmmm(self, rows: list[bytearray], c: int, key, ax: int, ay: int, clip=None) -> None:
        """LMMM/TIMP of a sheet block whose BOB origin is at bitplane (ax, ay) (a front layer's: its
        rectangle's origin), clipped to clip = (x0, y0, x1, y1) inclusive and to the page."""
        sx, sy = self.place[key]
        img = self.block_img[key]
        tx, ty = (self.trim[key][:2] if key in self.trim else (0, 0))
        w, h = len(img[0]), len(img)
        X0, Y0 = ax + tx, ay + ty
        x0, y0, x1, y1 = X0, Y0, X0 + w - 1, Y0 + h - 1
        if clip:
            x0, y0, x1, y1 = max(x0, clip[0]), max(y0, clip[1]), min(x1, clip[2]), min(y1, clip[3])
        x0, x1 = max(x0, c), min(x1, c + VIEW_W - 1)
        y0, y1 = max(y0, TOP), min(y1, TOP + VIEW_H - 1)
        for y in range(y0, y1 + 1):
            src = self.vram.px[sy + y - Y0]
            dst = rows[y - TOP]
            for x in range(x0, x1 + 1):
                v = src[sx + x - X0]
                if v:
                    dst[x - c] = v

    def lines(self, st: State) -> list[tuple[int, int, int]]:
        """The bitmap's lines (row, x0, x1 exclusive, bitplane): the box's top and bottom edges
        ($1ED5A: rows 0-157, cut at the screen's edges), then the crosshair's row (all 320)."""
        out = []
        if st.box:
            n, cb, yb = st.box
            x0 = cb - 16 * n - EDGE_DX
            for y in (yb - 16 * n, yb + 16 * n):
                if 0 <= y < EDGE_ROWS and max(x0, 0) < min(x0 + 32 * n, AW):
                    out.append((y, max(x0, 0), min(x0 + 32 * n, AW)))
        if st.cross:
            out.append((st.cross[1], 0, AW))
        return out

    def shown(self, st: State, s: int | None = None, sat=None) -> tuple[list[bytearray], list[bytearray]]:
        """(the picture as shown: the page, its sprites, R#18 applied; the page as built)."""
        s = st.s if s is None else s
        shift = st.c - s
        check(0 <= s <= CAM_MAX and SHIFT_MIN <= shift <= SHIFT_MAX,
              f"R#18 cannot show the page at c = {st.c} at s = {s}")
        page = self.page_rows(st)
        pic = [bytearray(r) for r in page]
        for sy, x, k in (self.sat(st) if sat is None else sat):
            top = sy + 1 if sy < SAT_END else sy + 1 - 256
            pat = self.pats[32 * k:32 * k + 32]
            for j in range(16):
                for i in range(16):
                    if pat[j + (16 if i >= 8 else 0)] & (0x80 >> (i & 7)) and 0 <= top + j < VIEW_H \
                            and 0 <= x + i < 256:
                        pic[top + j][x + i] = GREEN
        if shift > 0:
            pic = [bytearray(shift) + r[:VIEW_W - shift] for r in pic]
        elif shift < 0:
            pic = [r[-shift:] + bytearray(-shift) for r in pic]
        return pic, page

    # ----- the original's own composition (the model the sweep compares with) -----

    def amiga(self, st: State, quirk4: bool = True) -> list[bytearray]:
        """320 x 172 Amiga colour indices at the pass's end: the clean street, the pop-ups in slot
        order (blit 2 writes the picture where its mask is set and the 6th plane clear; with quirk4,
        the clean copy over the rest of its word-aligned box too), the big target and the dissolve
        cut over the screen (the walker clipped at bitplane x clip - 128), the lines, the sprites
        (COLOR31; the crosshair's line at the port's x, $B9A - 111). Display quirks 1-3 are left out."""
        scr = [bytearray(r) for r in self.bg]
        for p in st.pops:
            if p:
                place, pic, X, Y = p
                ptr = self.pics[pic]
                mask, cols = self.bobs[ptr]
                w = self.blt[ptr] & 0x3F
                bx = (X & 0xFFF0) - XBIAS if quirk4 else X - XBIAS
                bw = 16 * w if quirk4 else len(mask[0])
                for y in range(max(Y, 0), min(Y + len(mask), AH)):
                    j = y - Y
                    for x in range(max(bx, 0), min(bx + bw, AW)):
                        i = x - (X - XBIAS)
                        if 0 <= i < len(mask[0]) and mask[j][i] and not self.prio[y][x]:
                            scr[y][x] = cols[j][i]
                        elif quirk4:
                            scr[y][x] = self.bg[y][x]          # blit 2: the clean copy (C)
        cut = []
        if st.big:
            cut.append((st.big[:3], st.big[3] - XBIAS))
        if st.fx:
            cut.append((st.fx, AW))
        for (pic, X, Y), clip in cut:
            mask, cols = self.bobs[self.pics[pic]]
            for j, (mr, cr) in enumerate(zip(mask, cols)):
                y = Y + j
                if 0 <= y < AH:
                    for i in (i for i, m in enumerate(mr) if m):
                        x = X - XBIAS + i
                        if 0 <= x < min(clip, AW):
                            scr[y][x] = cr[i]
        for y, x0, x1 in self.lines(st):
            scr[y][x0:x1] = bytes([31]) * (x1 - x0)
        spr = []
        if st.cross:
            spr.append((st.cross[0] - LINE_DX, 0, SPR_ROWS))
        if st.box:
            n, cb, yb = st.box
            if yb - 16 * n >= SIDE_TOP:
                spr += [(h - SIDE_DX, yb - 16 * n, yb + 16 * n) for h in (cb - 16 * n, cb + 16 * n)]
        for x, y0, y1 in spr:
            if 0 <= x < AW:
                for y in range(max(y0, 0), min(y1, SPR_ROWS)):
                    scr[y][x] = 31
        return scr

    def compare(self, st: State, s: int | None = None) -> tuple[int, int]:
        """(pixels of the view that differ from the original's composition without quirk 4, pixels
        quirk 4 changes there); the columns R#18 uncovers are left out."""
        s = st.s if s is None else s
        pic, _ = self.shown(st, s)
        shift = st.c - s
        clean = self.amiga(st, False)
        full = self.amiga(st, True) if st.pops[0] and st.pops[1] else clean
        remap = bytes(self.remap) + bytes(224)
        norm = bytes([0, 0] + list(range(2, 256)))                   # the sheets' black is black
        lo, hi = max(0, shift), min(VIEW_W, VIEW_W + shift)
        bad = quirk = 0
        for y in range(VIEW_H):
            m = pic[y][lo:hi].translate(norm)
            b = clean[y + TOP][s + lo:s + hi].translate(remap)
            if m != b:
                bad += sum(1 for u, v in zip(m, b) if u != v)
            a = full[y + TOP][s + lo:s + hi].translate(remap)
            if a != b:
                for i in (i for i in range(len(a)) if a[i] != b[i]):
                    check(self.in_quirk4(st, s + lo + i, y + TOP), f"the original's model: ({s + lo + i}, {y + TOP})")
                    quirk += 1
        return bad, quirk

    def in_quirk4(self, st: State, x: int, y: int) -> bool:
        """Does a later slot's pop-up box restore (x, y) inside an earlier slot's position?"""
        p0, p1 = st.pops
        if not (p0 and p1):
            return False
        place0 = p0[0]
        X = p1[2]
        w = self.blt[self.pics[p1[1]]] & 0x3F
        bx = (X & 0xFFF0) - XBIAS
        h = self.blt[self.pics[p1[1]]] >> 6
        return bx <= x < bx + 16 * w and p1[3] <= y < p1[3] + h and overlap(self.places[place0], (x, y, 1, 1))

    def box_overlaps(self) -> list[tuple]:
        """Quirk 4's cases: (descriptor, slide steps, the other position, its columns) where a
        pop-up's word-aligned box (16 w x h from (X & FFF0h) - 128) meets another position's rect."""
        out = []
        for a in self.used_desc:
            e = self.desc[a]
            w, h = e["blt"] & 0x3F, e["blt"] >> 6
            hits = {}
            for k, (X, Y) in enumerate(e["pos"]):
                box = ((X & 0xFFF0) - XBIAS, Y, 16 * w, h)
                for q, r in self.places.items():
                    if q != e["place"] and overlap(box, r):
                        x0, x1 = max(box[0], r[0]), min(box[0] + box[2], r[0] + r[2])
                        hits.setdefault(q, [set(), set()])
                        hits[q][0].add(k)
                        hits[q][1] |= set(range(x0, x1))
            for q, (ks, xs) in sorted(hits.items()):
                out.append((a, sorted(ks), q, (min(xs), max(xs))))
        return out

    def sweep(self) -> dict:
        """docs/RANGE.md 3.3's sweep through the VRAM model: (cases, differing pixels, of them quirk 4's)."""
        f = self.f
        rep = {}

        def run(name: str, st: State, s: int) -> None:
            st.s = s
            st.c = page_c(s)
            d, q = self.compare(st)
            r = rep.setdefault(name, [0, 0, 0])
            r[0], r[1], r[2] = r[0] + 1, r[1] + d, r[2] + q

        pi = self.pic_index
        for a in self.used_desc:                                    # every pop-up at every slide step
            e = self.desc[a]
            px, py, pw, ph = self.places[e["place"]]
            s = clamp(px + pw // 2 - 128, 0, CAM_MAX)
            for X, Y in e["pos"]:
                run("pop-up steps", State(pops=[(e["place"], pi[e["ptr"]], X, Y), None]), s)
        for x in (2, 31, 64, 100, 128, 191, 200, 257):              # the riser at 8 x, 3 cameras
            for g, b, row in f.rise:
                for s in (0, 32, 64):
                    run("riser cases", State(big=(pi[g], x + XBIAS, row, CLIP_FILE)), s)
        for row, clip, thr, xoff, b, g in f.walk:                   # every walker kind at 10 x
            for X in range(345, 409, 7):
                run("walker cases", State(big=(pi[g], X + xoff, row, clip)), 64)
        for fr in FX_STORED:                                       # every dissolve frame at 3 places
            for x, y in ((4, 20), (120, 90), (250, 100)):
                run("dissolve cases", State(fx=(pi[f.fx[fr][1]], x + XBIAS, y)), 32 if x > 32 else 0)
        rnd = random.Random(1)                                     # mixed moments
        descs = [self.desc[a] for a in self.used_desc]
        for k in range(40):
            es = rnd.sample(descs, 2)
            if es[0]["place"] == es[1]["place"]:
                continue
            pops = []
            for e in es:
                X, Y = rnd.choice(e["pos"])
                pops.append((e["place"], pi[e["ptr"]], X, Y))
            row, clip, thr, xoff, b, g = rnd.choice(f.walk)
            X = rnd.randint(345, 408)
            run("mixed moments", State(pops=pops, big=(pi[g], X + xoff, row, clip)), rnd.choice((0, 16, 32, 48, 64)))
        for name, st in self.moments():                            # with the lines and the sprites
            for s in sorted({st.s, clamp(st.s - 7, 0, 64), clamp(st.s + 8, 0, 64)}):
                run("full moments", State(st.c, st.s, st.pops, st.big, st.fx, st.cross, st.box), s)
        for (a, ks, q, cols) in self.quirk4:                       # quirk 4: its first and last step,
            e = self.desc[a]                                       # each pop-up of the other position
            s = clamp(cols[0] - 128, 0, CAM_MAX)                   # at 3 steps, both slot orders
            for k in sorted({ks[0], ks[-1]}):
                mine = (e["place"], pi[e["ptr"]], *e["pos"][k])
                for b in (self.desc[d] for d in self.used_desc if self.desc[d]["place"] == q):
                    for X2, Y2 in (b["pos"][0], b["pos"][len(b["pos"]) // 2], b["pos"][-1]):
                        other = (q, pi[b["ptr"]], X2, Y2)
                        run("quirk 4 pairs", State(pops=[other, mine]), s)
                        run("quirk 4 pairs", State(pops=[mine, other]), s)
        for name, (n, d, q) in rep.items():
            check(d == 0, f"the sweep: {name}: {d} pixels differ from the original's composition")
        check(rep["quirk 4 pairs"][2] > 0, "the sweep: quirk 4 never shows")
        return rep

    def moments(self) -> list[tuple[str, State]]:
        """The previews' moments (the graphics report's), as shown states."""
        pi, f, d = self.pic_index, self.f, self.desc

        def pop(a, x, y):
            return (d[a]["place"], pi[d[a]["ptr"]], x + XBIAS, y)

        def walker(k, x):
            row, clip, thr, xoff, b, g = f.walk[k]
            return (pi[g], x + XBIAS, row, clip)

        b = ((300 + 4) & 0xFFF0, 70)
        s32 = State(32, 32, [pop(0x1F624, 64, 30), pop(0x1F76E, 228, 114)], walker(3, 232),
                    (pi[f.fx[9][1]], 124 + XBIAS, 92), (300, 70), (3, *b))
        s0 = State(0, 0, [pop(0x1F60E, 2, 32), pop(0x1F700, 52, 116)], (pi[f.rise[4][0]], 12 + XBIAS, 84, CLIP_FILE),
                   None, (150, 120), None)
        s64 = State(64, 64, [pop(0x1F7C6, 266, 43), pop(0x1F784, 230, 50)], walker(6, 286),
                    (pi[f.fx[17][1]], 100 + XBIAS, 84), (400, 100), (1, (400 + 4) & 0xFFF0, 100))
        return [("s32", s32), ("s0", s0), ("s64", s64)]

    # ----- the include files -----

    def inc_text(self) -> str:
        out = ["; generated by tools/msxrange.py: the shooting range's graphics for msx/frng.asm (docs/RANGE.md",
               "; 3.3, 3.4 and 3.11). Equates only: include it anywhere. VDP coordinates: X 0-255, Y over the 4",
               "; pages (page p from 256p). Amiga coordinates: bitplane x 0-319, rows 0-171; a BOB's D0 and a",
               "; sprite's H are bitplane x + 128. Words little-endian, as the Z80 keeps them."]

        def eq(name: str, value, comment: str = "") -> None:
            v = f"0x{value:X}" if isinstance(value, int) and value >= 0x10000 else str(value)
            line = f"{name + ':':<22}equ {v}"
            out.append(f"{line:<40}; {comment}" if comment else line)

        out.append("; --- the view: MSX x = Amiga x - s, MSX line = Amiga row - RG_TOP")
        eq("RG_TOP", TOP, "the Amiga row on line 0: rows 10-171 on lines 0-161")
        eq("RG_VIEW_H", VIEW_H)
        eq("RG_SCENE_W", SCENE_W)
        eq("RG_CAM_MAX", CAM_MAX, "the camera s: 0..RG_CAM_MAX, the view Amiga columns s..s+255")
        eq("RG_CAM_START", CAM_START)
        eq("RG_LINE_DX", LINE_DX, "cx = $B9A - RG_LINE_DX: the crosshair's line, the hit column")
        eq("RG_BAND_LO", BAND_LO, "once a pass: s = clamp(clamp(s, cx - RG_BAND_HI,")
        eq("RG_BAND_HI", BAND_HI, "  cx - RG_BAND_LO), 0, RG_CAM_MAX)")
        eq("RG_ADJ_LO", ADJ_LO, "RG_ADJ=0 (16-px steps, R#18 0): s moves only to keep")
        eq("RG_ADJ_HI", ADJ_HI, "  cx - s in RG_ADJ_LO..RG_ADJ_HI")
        eq("RG_C_ROUND", 8, "a page at c = (s + RG_C_ROUND) & F0h shows s:")
        eq("RG_SHIFT_MIN", SHIFT_MIN, "  c - s in RG_SHIFT_MIN..RG_SHIFT_MAX, R#18 = (s - c) & 15")
        eq("RG_SHIFT_MAX", SHIFT_MAX, "  (level 1's sign: 8 moves the picture 8 px right, 7 7 px left)")
        out.append("; --- VRAM (docs/RANGE.md 3.3): display pages A (page 0) and B, lines 0-161; the clean scene in")
        out.append("; page 2: Amiga columns 64-319 at x 0-255 from RG_SCENE_Y; columns 0-63 in the strip: rows")
        out.append("; 10-90 at x 0-63 from RG_STRIP_Y, rows 91-171 at x RG_STRIP_X2; the sheets S0-S3")
        eq("RG_PAGE_B", PAGE_B, "display page B's first line (page A's: 0)")
        eq("RG_SCENE_Y", SCENE_Y)
        eq("RG_SPLIT_COL", SPLIT_COL, "the first Amiga column in page 2's main part")
        eq("RG_STRIP_Y", STRIP_Y)
        eq("RG_STRIP_X2", STRIP_X2)
        eq("RG_STRIP_ROWS", STRIP_ROWS, "lines 0-80 in the first block, 81-161 in the second")
        for i, a in enumerate(AREAS):
            eq(f"RG_{a[0]}_X", a[1], f"sheet {a[0]}: page {a[2] // 256} lines {a[2] % 256}-"
                                     f"{self.used_y[i] - 1 - a[2] // 256 * 256}, x {a[1]}-{a[1] + a[3] - 1}")
            eq(f"RG_{a[0]}_Y", a[2])
            eq(f"RG_{a[0]}_LINES", self.used_y[i] - a[2])
        eq("RG_LINE_VRAM", SPR_PAT, "the 16 line patterns (OUT_line.spr): msx.inc SPR_PAT, 0-15")
        eq("RG_LINE_PATS", LINE_PATS)
        eq("RG_SAT_A", SPR_COL_A + SAT_OFS, "set A's SAT (msx.inc SPR_COL_A + 200h), set B's below")
        eq("RG_SAT_B", SPR_COL_B + SAT_OFS)
        out.append("; --- range_gfx.bin: streams of RG_GFX_<n>_LINES lines of RG_GFX_<n>_BPL bytes from (X, Y), at")
        out.append("; RG_GFX_<n>_OFS (read through the 8000h window from RANGE_GFX_BANK, split at 8 KiB)")
        eq("RG_GFX_LEN", len(self.blob))
        o = 0
        for name, x, y, w, n in self.streams:
            eq(f"RG_GFX_{name}_OFS", o, f"{name}: {n} lines of {w // 2} bytes at ({x}, {y})")
            eq(f"RG_GFX_{name}_LEN", w // 2 * n)
            eq(f"RG_GFX_{name}_X", x)
            eq(f"RG_GFX_{name}_Y", y)
            eq(f"RG_GFX_{name}_BPL", w // 2)
            eq(f"RG_GFX_{name}_LINES", n)
            eq(f"RG_GFX_{name}_VRAM", y * 128 + x // 2, "its first byte's VRAM address")
            o += w // 2 * n
        out.append("; --- the pictures: rgt_pics records of RG_PIC_LEN bytes, by Amiga address (RG_PIC_<address>")
        out.append("; the index; the shown state holds it)")
        eq("RG_PICS", len(self.pics))
        eq("RG_PIC_LEN", PIC_LEN)
        for name, o, what in (("KEY", 0, "dw the Amiga address's low word (unique)"), ("HI", 2, "db its high byte"),
                              ("SX", 3, "db the sheet block's x"), ("SY", 4, "dw its y"),
                              ("TX", 6, "db its offset from the BOB's origin (the trim)"), ("TY", 7, "db"),
                              ("W", 8, "db its size"), ("H", 9, "db"),
                              ("MASK", 10, "dw the mask's offset in range_hit.bin (FFFFh: none)")):
            eq(f"RG_PIC_{name}", o, what)
        for i, p in enumerate(self.pics):
            eq(f"RG_PIC_{p:05X}", i, self.kind[p])
        out.append("; --- the positions 0-8: the rectangle every pop-up there shows in (Amiga), and its front layer")
        out.append("; (the scene's pixels where the 6th plane is set) at (RG_PLACE<n>_FX, RG_PLACE<n>_FY), the")
        out.append("; rectangle's size; rgt_places holds the same, RG_PLACE_LEN bytes a position")
        eq("RG_PLACES", len(self.places))
        eq("RG_PLACE_LEN", PLACE_LEN)
        for name, o, what in (("X", 0, "dw"), ("Y", 2, "db"), ("W", 3, "db"), ("H", 4, "db"), ("FX", 5, "db"),
                              ("FY", 6, "dw")):
            eq(f"RG_PLACE_{name}", o, what)
        for q, (x, y, w, h) in self.places.items():
            fx, fy = self.place[("front", q)]
            for name, v in (("X", x), ("Y", y), ("W", w), ("H", h), ("FX", fx), ("FY", fy)):
                eq(f"RG_PLACE{q}_{name}", v)
        out.append("; --- the colours (range_1.pal, range_2.pal, plain; the grade: tools/mkrom.py writes their graded")
        out.append("; copies gen/range_<v>_grade.pal for the play, decision 8; the fade limits them with")
        out.append("; grade.inc's fade_cap[$BC1 >> 2], msx/logic.asm pal_fade's rule)")
        eq("RG_C_BLACK", BLACK, "the scene's black")
        eq("RG_C_SHEET", DUP, "the sheets' black (LMMM/TIMP skips 0): black in both visits")
        eq("RG_C_FREE", FREE)
        eq("RG_C_GREEN", GREEN, "COLOR31: the crosshair, the box")
        eq("RG_GREEN_FILL", GREEN * 17, "HMMV's byte: two green pixels")
        eq("RG_GRADED", 1, "the play's palettes are the graded ones")
        out.append("; --- the sprites (mode 2, 16 x 16; colour rows all RG_C_GREEN): the crosshair's line from")
        out.append("; line 0 to RG_SPR_LINES - 1 at x cx - c; the box's sides at bitplane x H - RG_SIDE_DX, H =")
        out.append("; C -/+ 16n, Amiga rows Y - 16n..Y + 16n - 1, shown when Y - 16n >= RG_SIDE_TOP; its edges")
        out.append("; on rows Y -/+ 16n below RG_EDGE_ROWS, from bitplane x C - 16n - RG_EDGE_DX, 32n wide, cut")
        out.append("; at 0 and 320. A sprite of k + 1 lines from line y: pattern k, SAT y - 1")
        eq("RG_SPR_LINES", SPR_LINES)
        eq("RG_SIDE_DX", SIDE_DX)
        eq("RG_SIDE_TOP", SIDE_TOP)
        eq("RG_EDGE_DX", EDGE_DX)
        eq("RG_EDGE_ROWS", EDGE_ROWS)
        eq("RG_SPR_MAX", SPR_MAX, "sprites at most (the SAT: + the terminator)")
        eq("RG_SAT_END", SAT_END)
        out.append("; --- the hit test (docs/RANGE.md 3.4): range_hit.bin from RANGE_HIT_BANK: the 6th plane")
        out.append("; (RG_HIT_STRIDE bytes a row, FFh past row 171), then the masks (rgt_pics RG_PIC_MASK)")
        eq("RG_HIT_PRIO", HIT_PRIO)
        eq("RG_HIT_STRIDE", HIT_STRIDE)
        eq("RG_HIT_MASKS", HIT_MASKS)
        eq("RG_HIT_LEN", len(self.hit))
        eq("RG_HIT_USED", PLANE + len(self.hit) - HIT_MASKS, "the plane and the masks")
        sizes = " ".join(map(str, self.sizes))
        out.append(f"; the first blit's output sizes 2 w' h: {sizes}")
        eq("RG_BLITS_MAX", len(self.sizes), "the recent-blit list's entries at most")
        eq("RG_BLITS_ROOM", BLITS_ROOM, "its RAM, F70Eh-F7FFh (docs/RANGE.md 3.2)")
        out.append("; --- a display page's shown state (RG_ST_LEN bytes); RG_NONE: nothing drawn")
        eq("RG_NONE", f"0x{NONE:02X}")
        for name, o, n, what in ST_FIELDS:
            eq(f"RG_ST_{name}", o, what)
        eq("RG_ST_LEN", ST_LEN)
        eq("RG_POP_LEN", POP_LEN)
        eq("RG_BIG_LEN", BIG_LEN)
        eq("RG_FX_LEN", FX_LEN)
        for name, o, what in ST_SUB:
            eq(f"RG_{name}", o, what)
        out.append("; --- fr_code (docs/RANGE.md 3.2): $1EB46-$1EB4B, $1F246-$1F247, $1F46C-$1F46D, $1F502-$1F50B,")
        out.append("; $1F60E-$1F807 one after another in the mirror's rule (a byte at A at offset ^ 1)")
        o = 0
        for a, n in FR_CODE:
            eq(f"RG_FC_{a:05X}", o, f"${a:X}, {n} bytes")
            o += n
        eq("RG_FC_LEN", o)
        eq("RG_FC_SHOT", 1, "db $1EB46: the shot flag")
        eq("RG_FC_REPEAT", 2, "dw $1EB48: the fire repeat counter")
        eq("RG_FC_BOX", 4, "dw $1EB4A: the box's n (8..0, -1 idle)")
        eq("RG_FC_KIND", 6, "dw $1F246: the walker's kind x 2")
        eq("RG_FC_CLIP", 8, "dw $1F46C: the big target's clip")
        eq("RG_FC_LOCKS", 10, "db x 10: position p's lock at + (p ^ 1)")
        eq("RG_FC_DESC", 20, "descriptor d at + RG_DESC_LEN x d (rgt_desc)")
        eq("RG_DESC_LEN", DLEN)
        eq("RG_DESCS", NDESC)
        out.append("; --- the script kinds (rgt_kind)")
        for name, v in (("NONE", K_NONE), ("POPUP", K_POPUP), ("MOVE", K_MOVE), ("RISE", K_RISE)):
            eq(f"RG_K_{name}", v)
        eq("RG_SCRIPTS", NSCRIPTS)
        return "\n".join(out) + "\n"

    def tab_text(self) -> str:
        f = self.f
        out = ["; generated by tools/msxrange.py: the shooting range's tables for msx/frng.asm (BANK_FRNG), read",
               "; from FRNG ($1EA00) and checked against docs/RANGE.md 2.6. Data: include it once. Words hold the",
               "; 68000's values (dw: little-endian), longs their high word first (the mirror's rule), indexed",
               "; as the 68000 indexes them; byte tables keep the 68000's order."]

        def rows(vals: list[int], op: str, per: int, fmt: str) -> None:
            for i in range(0, len(vals), per):
                out.append(f"        {op} " + ", ".join(fmt.format(v) for v in vals[i:i + per]))

        def longs(vals: list[int]) -> list[int]:
            return [h for v in vals for h in (v >> 16, v & 0xFFFF)]

        code = mirror(f.fr_code())
        out.append("rgt_frcode:                         ; fr_code's initial 526 bytes, the mirror's rule (RG_FC_...)")
        rows(list(code), "db", 16, "0x{:02X}")
        out.append("rgt_scripts:                        ; $1EF88-$1F0D7: script n at + 8n: the handler's offset")
        out.append("                                    ; from the entry, an offset to $1F0D8 (unused), the effect's")
        out.append("                                    ; type, 0")
        for e in f.scripts:
            what = f"pop-up ${e['desc']:X}" if e["desc"] else ("empty", "", "h_move", "h_rise")[e["kind"]]
            out.append(f"        dw " + ", ".join(f"0x{v & 0xFFFF:04X}" for v in e["words"]) + f"  ; {e['n']}: {what}")
        out.append("rgt_kind:                           ; by script: RG_K_NONE, _POPUP, _MOVE or _RISE")
        rows([e["kind"] for e in f.scripts], "db", 14, "{}")
        out.append("rgt_desc:                           ; by script: its descriptor's offset in fr_code, FFFFh: none")
        rows([20 + (e["desc"] - DESCS) if e["desc"] else 0xFFFF for e in f.scripts], "dw", 14, "0x{:04X}")
        out.append("rgt_rise_gfx:                       ; $1F1C2: by frame 0-9, the graphic (long)")
        rows(longs([g for g, b, r in f.rise]), "dw", 10, "0x{:04X}")
        out.append("rgt_rise_size:                      ; $1F1EA: BLTSIZE")
        rows([b for g, b, r in f.rise], "dw", 10, "0x{:04X}")
        out.append("rgt_rise_row:                       ; $1F200: the row of its top (each frame ends on row 171)")
        rows([r for g, b, r in f.rise], "dw", 10, "{}")
        for i, (label, addr, what) in enumerate((("rgt_walk_row", WALK_ROW, "the row"),
                                                 ("rgt_walk_clip", WALK_CLIP, "the clip ($1F46C)"),
                                                 ("rgt_walk_thr", WALK_THR, "the threshold (hit x <= it: armed)"),
                                                 ("rgt_walk_xoff", WALK_XOFF, "the x offset"),
                                                 ("rgt_walk_size", WALK_SIZE, "BLTSIZE"))):
            out.append(f"{label + ':':<36}; ${addr:X}: by kind 0-15 (index $1F246 = 2k): {what}")
            rows([v[i] & 0xFFFF for v in f.walk], "dw", 8, "0x{:04X}")
        out.append("rgt_walk_gfx:                       ; $1F2EA: the graphic (long, index 2 x $1F246)")
        rows(longs([v[5] for v in f.walk]), "dw", 8, "0x{:04X}")
        out.append("rgt_fx_size:                        ; $1F8AA: by frame 0-21, BLTSIZE")
        rows([b for b, g in f.fx], "dw", 11, "0x{:04X}")
        out.append("rgt_fx_gfx:                         ; $1F8E8: by frame, the graphic (long)")
        rows(longs([g for b, g in f.fx]), "dw", 8, "0x{:04X}")
        out.append("rgt_fx_first:                       ; $1F974: by type 0-4, the first frame")
        rows([a for a, b in f.fx_types], "db", 5, "{}")
        out.append("rgt_fx_end:                         ; $1F979: by type 0-4, the end frame")
        rows([b for a, b in f.fx_types], "db", 5, "{}")
        out.append("rgt_pics:                           ; RG_PICS records of RG_PIC_LEN bytes, by Amiga address")
        for i, p in enumerate(self.pics):
            sx, sy = self.place[p]
            tx, ty, tw, th = self.trim[p]
            m = self.mask_ofs.get(p, 0xFFFF)
            out.append(f"{'        dw 0x%04X' % (p & 0xFFFF):<36}; {i}: ${p:X}, {self.kind[p]}\n"
                       f"        db 0x{p >> 16:02X}, {sx}\n        dw {sy}\n        db {tx}, {ty}, {tw}, {th}\n"
                       f"        dw 0x{m:04X}")
        out.append("rgt_places:                         ; RG_PLACES records of RG_PLACE_LEN bytes")
        for q, (x, y, w, h) in self.places.items():
            fx, fy = self.place[("front", q)]
            out.append(f"{'        dw %d' % x:<36}; position {q}\n        db {y}, {w}, {h}, {fx}\n        dw {fy}")
        return "\n".join(out) + "\n"

    def check_tab(self, text: str) -> None:
        """OUT_tab.inc assembles to the file's bytes."""
        f = self.f
        data = parse_data(text)

        def words(a: int, n: int) -> bytes:
            return mirror(f.rd(a, 2 * n))

        want = {"rgt_frcode": mirror(f.fr_code()), "rgt_scripts": words(SCRIPTS, 4 * NSCRIPTS),
                "rgt_rise_gfx": words(RISE_GFX, 20), "rgt_rise_size": words(RISE_SIZE, 10),
                "rgt_rise_row": words(RISE_ROW, 10), "rgt_walk_row": words(WALK_ROW, 16),
                "rgt_walk_clip": words(WALK_CLIP, 16), "rgt_walk_thr": words(WALK_THR, 16),
                "rgt_walk_xoff": words(WALK_XOFF, 16), "rgt_walk_size": words(WALK_SIZE, 16),
                "rgt_walk_gfx": words(WALK_GFX, 32), "rgt_fx_size": words(FX_SIZE, 22),
                "rgt_fx_gfx": words(FX_GFX, 44), "rgt_fx_first": f.rd(FX_FIRST, 5), "rgt_fx_end": f.rd(FX_END, 5)}
        for label, b in want.items():
            check(data[label] == b, f"OUT_tab.inc: {label}")
        check(len(data["rgt_pics"]) == PIC_LEN * len(self.pics) and len(data["rgt_places"]) == PLACE_LEN * 9,
              "OUT_tab.inc: rgt_pics, rgt_places")
        for i, p in enumerate(self.pics):
            r = data["rgt_pics"][PIC_LEN * i:PIC_LEN * (i + 1)]
            key, hi, sx, sy, tx, ty, tw, th, m = struct.unpack("<HBBHBBBBH", r)
            check((hi << 16 | key, (sx, sy), (tx, ty, tw, th)) == (p, self.place[p], self.trim[p]), f"rgt_pics {i}")
            check(m == 0xFFFF or self.hit[m:m + 2] == f.rd(p, 2), f"rgt_pics {i}: the mask")
        self.tab_len = sum(len(v) for v in data.values())


def trim(mask: list) -> tuple[int, int, int, int]:
    ys = [y for y, r in enumerate(mask) if any(r)]
    xs = [x for x in range(len(mask[0])) if any(r[x] for r in mask)]
    return min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1


def column(x: int, y0: int, h: int) -> list[tuple[int, int, int]]:
    """A vertical line at page x from line y0, h lines, cut to lines 0..SPR_LINES - 1: stacked 16-line
    sprites, (SAT y, x, pattern): the last one shows only its rows."""
    y1, y = min(y0 + h, SPR_LINES), max(y0, 0)
    out = []
    while y < y1:
        n = min(16, y1 - y)
        out.append(((y - 1) & 255, x, n - 1))  # SAT y is one line above the first shown line
        y += n
    return out


def line_patterns() -> bytes:
    """Pattern k (0-15): column 0 set on rows 0..k; mode 2, 16 x 16 (left 8 columns, then right 8)."""
    return b"".join(bytes(0x80 if y <= k else 0 for y in range(16)) + bytes(16) for k in range(LINE_PATS))


def sat_bytes(sat: list[tuple[int, int, int]]) -> bytes:
    return b"".join(bytes((y, x, 4 * k, 0)) for y, x, k in sat) + bytes((SAT_END, 0, 0, 0))


def parse_sat(data: bytes) -> list[tuple[int, int, int]]:
    """A set's SAT dump: its entries up to Y = 216 (32 at most), patterns of the line sprites."""
    out = []
    for i in range(0, min(len(data), 128), 4):
        y, x, p = data[i], data[i + 1], data[i + 2]
        if y == SAT_END:
            break
        check(p >> 2 < LINE_PATS, f"SAT entry {i // 4}: pattern {p >> 2} is not a line's")
        out.append((y, x, p >> 2))
    return out


# ----- previews -----

def previews(rg: Range, out: Path) -> list[Path]:
    files = []

    def put(path: Path, rows: list[bytes]) -> None:
        write_png(path, len(rows[0]) // 3, len(rows), rows)
        files.append(path)

    def scaled(rows: list, cols: list[tuple], s: int) -> list[bytes]:
        return [b"".join(bytes(cols[v]) * s for v in r) for r in rows for _ in range(s)]

    plain = {v: [rgb24(c) for c in rg.pal[v]] for v in (1, 2)}
    graded = {v: [rgb24(c, True) for c in rg.pal[v]] for v in (1, 2)}
    put(Path(f"{out}_scene.png"), scaled([list(r) for r in rg.scene], plain[1], 2))
    purple = (60, 0, 80)
    vram = [[plain[1][v] if v else purple for v in r] for r in rg.vram.px]
    put(Path(f"{out}_vram.png"), [b"".join(bytes(c) for c in r) for r in vram])
    amc = [tuple(((c >> sh) & 15) * 17 for sh in (8, 4, 0)) for c in rg.f.pal12[1]]
    for name, st in rg.moments():
        pic, _ = rg.shown(st)
        for tag, visits in (("plain", (1,)), ("graded", (1, 2))):
            for v in visits:
                cols = plain[v] if tag == "plain" else graded[v]
                rows = [b"".join(bytes(cols[p]) for p in r) for r in pic]
                hud = hud_rows(out.parent, tag == "graded")
                if hud is not None:
                    rows += [bytes(3 * VIEW_W)] * 5 + hud
                big = [b"".join(r[3 * x:3 * x + 3] * 2 for x in range(VIEW_W)) for r in rows for _ in range(2)]
                put(Path(f"{out}_{name}{'_v2' if v == 2 else ''}_{tag}.png"), big)
        if name == "s32":
            am = rg.amiga(st)
            rows_a = scaled(am, amc, 2)
            rows_m = scaled(pic, plain[1], 2)
            gap = bytes((255, 255, 255)) * 8
            comp = [a + gap + (rows_m[y] if y < len(rows_m) else bytes(3 * 2 * VIEW_W)) for y, a in enumerate(rows_a)]
            put(Path(f"{out}_amiga_vs_msx.png"), comp)
    return files


# ----- main -----

def convert(src: Path, out: Path) -> int:
    rg = Range(decrunch(src.read_bytes()))
    out.parent.mkdir(parents=True, exist_ok=True)
    written = []

    def put(path: Path, data) -> None:
        if isinstance(data, str):
            path.write_text(data)
        else:
            path.write_bytes(data)
        written.append(path)

    for v in (1, 2):
        put(Path(f"{out}_{v}.pal"), v9938(rg.pal[v]))
    put(Path(f"{out}_gfx.bin"), rg.blob)
    put(Path(f"{out}_hit.bin"), rg.hit)
    put(Path(f"{out}_line.spr"), rg.pats)
    inc, tab = rg.inc_text(), rg.tab_text()
    rg.check_tab(tab)
    put(Path(f"{out}.inc"), inc)
    put(Path(f"{out}_tab.inc"), tab)
    written += previews(rg, out)
    print(f"FRNG: 170970 bytes, checksum 0, sha256 {rg.f.sha256}")
    for v in (1, 2):
        print(f"visit {v}: palette {' '.join('%d%d%d' % c for c in rg.pal[v])}")
    print("  Amiga colour -> MSX index: " + " ".join(f"{c}:{rg.remap[c]}" for c in range(32)))
    print(f"positions (Amiga x, y, w, h): {' '.join(f'{q}:{r}' for q, r in rg.places.items())}")
    print(f"{out}_gfx.bin: {len(rg.blob)} bytes = {len(rg.blob) / 8192:.2f} banks: "
          + ", ".join(f"{n} {w // 2 * k}" for n, x, y, w, k in rg.streams))
    print(f"{out}_hit.bin: {len(rg.hit)} bytes ({PLANE + len(rg.hit) - HIT_MASKS} used), 2 banks; "
          f"{out}_tab.inc: {rg.tab_len} bytes")
    print(f"the recent-blit list: at most {len(rg.sizes)} entries (sizes {' '.join(map(str, rg.sizes))})")
    print(f"the SAT: at most {rg.sat_worst} sprites + the terminator")
    print("quirk 4 (a pop-up's box over another position): " +
          "; ".join(f"${a:X} steps {ks[0]}-{ks[-1]} over position {q} x {c[0]}-{c[1]}" for a, ks, q, c in rg.quirk4))
    print("the sweep (cases, pixels differing from the original's composition, pixels quirk 4 wipes there): " +
          ", ".join(f"{k} {v[0]} {v[1]} {v[2]}" for k, v in rg.sweep_report.items()))
    print("checks passed: the decrunch, the tables and palettes (docs/RANGE.md 2.6), the colours, the positions, "
          "the sheets, range_hit.bin, the SAT, the sweep (0 pixels)")
    print("wrote " + " ".join(p.name for p in written))
    return 0


def render_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="msxrange.py render", description="a display page's picture from its shown state")
    ap.add_argument("frng", type=Path, help="FRNG_15.bin")
    ap.add_argument("state", help=f"a file holding the {ST_LEN} bytes (at --offset), or hex digits with --hex")
    ap.add_argument("out", type=Path, help="writes OUT.sc5, OUT_page.sc5, OUT.sat and OUT.png")
    ap.add_argument("--offset", type=lambda s: int(s, 0), default=0, help="the state's offset in the file")
    ap.add_argument("--page", type=int, choices=(0, 1), default=0, help="+ PAGE x RG_ST_LEN (rgs0, rgs1)")
    ap.add_argument("--hex", action="store_true", help="STATE is the bytes as hex digits")
    cam = ap.add_mutually_exclusive_group()
    cam.add_argument("--cam", type=int, help="the camera s (default: the state's own)")
    cam.add_argument("--r18", type=lambda s: int(s, 0), help="R#18's value: s = c - its shift")
    ap.add_argument("--sat", type=Path, help="draw the sprites from this SAT dump instead")
    ap.add_argument("--sat-offset", type=lambda s: int(s, 0), default=0)
    ap.add_argument("--visit", type=int, choices=(1, 2), default=1, help="the palette of the PNG")
    ap.add_argument("--grade", action="store_true", help="the PNG in the graded colours (as the ROM shows them)")
    ap.add_argument("--scale", type=int, default=1)
    a = ap.parse_args(argv)
    if a.hex:
        raw = bytes.fromhex(a.state.replace(" ", ""))
    else:
        o = a.offset + a.page * ST_LEN
        raw = Path(a.state).read_bytes()[o:o + ST_LEN]
    st = State.from_bytes(raw)
    check(st.c != NONE, "the state is unset (RG_ST_C = RG_NONE): the page was never built")
    s = st.s
    if a.cam is not None:
        s = a.cam
    elif a.r18 is not None:
        check(a.r18 >> 4 == 0, f"R#18 = {a.r18:02X}h: its vertical adjust is not 0")
        s = st.c - r18_shift(a.r18)
    rg = Range(decrunch(a.frng.read_bytes()), sweep=False)
    sat = rg.sat(st)
    drawn = parse_sat(a.sat.read_bytes()[a.sat_offset:a.sat_offset + 128]) if a.sat else None
    pic, page = rg.shown(st, s, drawn)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    stem = a.out.with_suffix("")
    a.out.with_suffix(".sc5").write_bytes(pack(pic))
    Path(f"{stem}_page.sc5").write_bytes(pack(page))
    a.out.with_suffix(".sat").write_bytes(sat_bytes(sat))
    cols = [rgb24(c, a.grade) for c in rg.pal[a.visit]]
    rows = [b"".join(bytes(cols[v]) * a.scale for v in r) for r in pic for _ in range(a.scale)]
    write_png(a.out.with_suffix(".png"), VIEW_W * a.scale, len(rows), rows)
    note = ""
    if drawn is not None:
        ref, _ = rg.shown(st, s)
        diff = sum(1 for r1, r2 in zip(ref, pic) for u, v in zip(r1, r2) if u != v)
        note = f"; the SAT dump's sprites: {len(drawn)} ({diff} pixels differ from the state's {len(sat)})"
    drawn_el = [k for k, v in (("pop-up 0", st.pops[0]), ("pop-up 1", st.pops[1]), ("big", st.big),
                               ("dissolve", st.fx), ("crosshair", st.cross), ("box", st.box)) if v]
    print(f"{a.out.with_suffix('.sc5')}: c = {st.c}, s = {s}, R#18 = {(s - st.c) & 15:02X}h; drawn: "
          f"{', '.join(drawn_el) or 'nothing'}; {len(sat)} sprites{note}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "render":
        return render_main(argv[2:])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("frng", type=Path, help="FRNG_15.bin (crunched)")
    ap.add_argument("out", type=Path, help="the output prefix, e.g. build/msx/range")
    a = ap.parse_args(argv[1:])
    return convert(a.frng, a.out)


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except ValueError as e:
        raise SystemExit(f"msxrange.py: {e}")
