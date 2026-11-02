"""The field engine's arithmetic of performance campaign 2 (docs/PERF2_PLAN.md): field-2's tile burst (msx/field.asm
fb_tiles, ftl_ax: a cell's part in a piece by 8-bit arithmetic on the piece's corner) against the 16-bit clip it
replaced (fb_rpiece, fb_dscr), on every piece position and extent and every cell, field-7's band pieces (up to 128
px wide) included; field-7's staging (fb_stage, fb_piece's clamp, fcp_next, fsl_sx, fst_chain's bands) against the
64 x 64 pieces it replaced; TILE-LOOKUP's row reads (tiles.asm gt_row, fb_tiles' cells: a row's map bank at
8000h) against get_tile's (at A000h) over every level's map; field-10's fill (fb_fill: no cell tested when the
cache holds its whole window, which fb_cfind puts over the piece); FC-UPLOAD's line loop (fc_get:
R#14 set once, the frame cache's places in page 2's lines 128-255, a line's bytes in two halves of sprites.asm's
outi32 chain, an odd count's extra byte in the second). Stdlib only."""
from __future__ import annotations

import ast
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def code(path: str, label: str, end: str) -> list[str]:
    """The code lines of msx/PATH from LABEL: up to (not with) the label END:."""
    lines = (ROOT / "msx" / path).read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(label + ":"))
    j = next(k for k, l in enumerate(lines) if l.startswith(end + ":"))
    out = []
    for l in lines[i:j]:
        c = re.sub(r"^\w+:", "", l.split(";")[0]).strip()
        if c:
            out.append(re.sub(r"\s+", " ", c))
    return out


def clip(p0: int, ext: int, cell: int) -> tuple[int, int, int]:
    """The old way (fb_rpiece's clip of the cell's 16 px to the piece [p0, p0 + ext), fb_dscr): the part's
    offset in the piece, its first pixel in the cell (SX/SY's low nibble added), its pixels."""
    x0, x1 = max(16 * cell, p0), min(16 * cell + 16, p0 + ext)
    return x0 - p0, x0 & 15, x1 - x0


def ftl_ax(p0: int, ext: int, cell: int) -> tuple[int, int, int]:
    """msx/field.asm ftl_ax as the Z80 runs it: A = cell, (HL) = p0's low byte, C = ext -> (A, B, C)."""
    a = (cell << 4) & 0xFF                          # add a,a x 4
    a = (a - (p0 & 0xFF)) & 0xFF                    # sub (hl)
    b = a                                           # ld b,a
    a = (a + 16) & 0xFF                             # add a,16
    c = ext
    if a < c:                                       # cp c / jr nc,fta_c
        c = a                                       # ld c,a
    a = b                                           # fta_c: ld a,b / or a
    if a & 0x80:                                    # jp m,fta_m
        return 0, (-a) & 0xFF, c                    # neg / ld b,a / xor a
    return a, 0, (c - b) & 0xFF                     # ld a,c / sub b / ld c,a / ld a,b / ld b,0


class TileBurstTests(unittest.TestCase):
    def test_ftl_ax_is_the_routine_modelled(self):
        self.assertEqual(code("field.asm", "ftl_ax", "fb_issue"),
                         ["add a,a", "add a,a", "add a,a", "add a,a", "sub (hl)", "ld b,a", "add a,16", "cp c",
                          "jr nc,fta_c", "ld c,a", "ld a,b", "or a", "jp m,fta_m", "ld a,c", "sub b", "ld c,a",
                          "ld a,b", "ld b,0", "ret", "neg", "ld b,a", "xor a", "ret"])

    def test_every_cell_of_every_piece_as_the_clip(self):
        """x: the piece's left edge 0-2559, even (fb_clip), widths 2-64 even; y: 0-2559, heights 1-64; every
        cell the piece spans (fb_cc: from p0 >> 4 to (p0 + ext - 1) >> 4)."""
        n = 0
        for step, exts in ((2, range(2, 65, 2)), (1, range(1, 65))):
            for p0 in range(0, 2560, step):
                for ext in exts:
                    for cell in range(p0 >> 4, ((p0 + ext - 1) >> 4) + 1):
                        n += 1
                        if ftl_ax(p0, ext, cell) != clip(p0, ext, cell):
                            self.fail(f"piece {p0} + {ext}, cell {cell}: {ftl_ax(p0, ext, cell)} != {clip(p0, ext, cell)}")
        self.assertEqual(n, 606720)

    def test_every_cell_of_every_band_piece_as_the_clip(self):
        """field-7: a staged band's piece up to 128 px wide (its cells' edges -15 .. 127 px from its corner,
        ftl_ax's signed byte); x only (a piece stays 64 lines tall)."""
        n = 0
        for p0 in range(0, 2560, 2):
            for ext in range(66, 129, 2):
                for cell in range(p0 >> 4, ((p0 + ext - 1) >> 4) + 1):
                    n += 1
                    if ftl_ax(p0, ext, cell) != clip(p0, ext, cell):
                        self.fail(f"piece {p0} + {ext}, cell {cell}: {ftl_ax(p0, ext, cell)} != {clip(p0, ext, cell)}")
        self.assertEqual(n, 284160)

    def test_the_burst_uses_it(self):
        body = code("field.asm", "fb_tiles", "ftl_ax")
        self.assertEqual(body.count("call ftl_ax"), 2)
        for gone in ("call fb_rpiece", "call fb_dscr", "call fb_c16"):
            self.assertNotIn(gone, body)
        for b in ("ld (fb_cmd + 1),a", "ld (fb_cmd + 5),a", "ld (fb_cmd + 9),a", "ld (fb_cmd + 11),a",
                  "ld (fb_cmd + 7),a"):                 # (once a call, before the cells)
            self.assertIn(b, body[:body.index("ld (fb_bn),a")])

    def test_field_upload_runs_in_front2(self):
        """field-2's room (R1): the atlas's upload in BANK_FRONT2 (ending.asm), both its calls through front2_call."""
        self.assertNotIn("field_upload:", (ROOT / "msx" / "field.asm").read_text())
        self.assertIn("field_upload:", (ROOT / "msx" / "ending.asm").read_text())
        cold = [l.split(";")[0].strip() for l in (ROOT / "msx" / "cold.asm").read_text().splitlines()]
        calls = [cold[k + 1] for k, l in enumerate(cold) if l == "ld hl,field_upload"]
        self.assertEqual(sorted(calls), ["call front2_call", "jp front2_call"])


def fst_n(length: int) -> int:
    """msx/field.asm fst_n: HL = a length (1 or more) -> the 64 px pieces it takes ((HL + 63) * 4, its high byte)."""
    return (((length + 63) * 4) >> 8) & 0xFF


def rrca(a: int) -> int:
    return ((a >> 1) | (a << 7)) & 0xFF


def staging(x0: int, y0: int, x1: int, y1: int, band: bool):
    """fb_stage, fb_piece's clamp, fcp_next and fsl_sx as the Z80 runs them, for an item on the page shown (map
    coordinates, x even) -> None when it is not staged, else (fb_stg, fb_scol, the pieces in their order as
    (x0, y0, x1, y1, their x in page 3)); band: field-7 (VAT_ANIM=0), else the 64 x 64 pieces before it."""
    c, b = fst_n(x1 - x0), fst_n(y1 - y0)
    n = c * b
    if n < 2 or n >= 5:
        return None
    if band:
        scol = (c + 1) >> 1                                 # ld a,c / inc a / srl a
        stg = scol * b
    else:
        scol, stg = c, n
    pieces, px, py = [], x0, y0
    while True:
        k = len(pieces)
        if band:                                            # fsl_sx: rrca, and once more for three or four
            sx = rrca(k) if stg < 3 else rrca(rrca(k))
        else:
            sx = rrca(rrca(k))
        ex = min(px + (128 if band else 64), x1)            # fb_piece's clamp
        ey = min(py + 64, y1)
        pieces.append((px, py, ex, ey, sx))
        if ex < x1:                                         # fcp_next: to the right, else the next band
            px = ex
        elif ey < y1:
            px, py = x0, ey
        else:
            break
    return stg, scol, pieces


def band_copies(stg: int, scol: int, pieces):
    """fst_chain's copies: per band, from the last band to the first, its rectangle in the map and its x in page
    3 (its first piece's corner and place, its last piece's other corner)."""
    out, k = [], stg
    while True:
        k -= scol
        first, last = pieces[k], pieces[k + scol - 1]
        out.append(((first[0], first[1], last[2], last[3]), first[4]))
        if k == 0:
            return out


class StagedBandTests(unittest.TestCase):
    """field-7 (docs/PERF2_PLAN.md item 9): a staged item's band of pieces composed as one piece up to 128 px
    wide; the copies onto the page as before."""

    def test_the_routines_modelled(self):
        stage = code("field.asm", "fb_stage", "fst_n")
        k = stage.index("ld a,c")
        self.assertEqual(stage[k:k + 15], ["ld a,c", "inc a", "srl a", "ld (fb_scol),a", "ld c,a", "ld b,e", "xor a",
                                           "add a,c", "djnz fsg_n", "ld (fb_stg),a", "xor a", "ld (fb_sbx),a",
                                           "ld b,3", "else", "ld (fb_stg),a"])
        self.assertEqual(stage[stage.index("call fst_n") + 1:][:12],
                         ["ld c,a", "ld hl,(fb_cur + 9)", "ld de,(fb_cur + 5)", "or a", "sbc hl,de", "call fst_n",
                          "ld b,a", "if VAT_ANIM = 0", "ld e,a", "endif", "xor a", "add a,c"])
        self.assertEqual(code("field.asm", "fst_n", "fst_done"), ["ld de,63", "add hl,de", "add hl,hl", "add hl,hl",
                                                                  "ld a,h", "ret"])
        sx = code("field.asm", "fsl_sx", "fsl_x")
        self.assertEqual(sx[:sx.index("else")], ["ld a,(fb_spk)", "rrca", "ld c,a", "ld a,(fb_stg)", "cp 3", "ld a,c",
                                                 "jr c,fsl_x", "rrca"])
        piece = code("field.asm", "fb_piece", "fp_lkok")
        k = piece.index("ld de,64")
        self.assertEqual(piece[k - 1:k + 8], ["ld hl,(fb_px)", "ld de,64", "if VAT_ANIM = 0", "ld a,(fb_stg)",
                                              "or a", "jr z,fp_w", "ld e,128", "endif", "add hl,de"])   # (fp_w: endif)
        done = code("field.asm", "fst_done", "fst_cp")
        self.assertEqual(done[-11:], ["jr z,fst_cp", "if VAT_ANIM = 0", "call fsl_sx", "else", "ld a,(hl)", "dec a",
                                      "rrca", "rrca", "ld (fb_sbx),a", "endif", "jp fcp_next"])
        nxt = code("field.asm", "fcp_next", "fcp_redo")
        self.assertEqual(nxt[:5], ["ld hl,(fb_pe)", "ld (fb_px),hl", "ld de,(fb_cur + 7)", "call fb_cmp", "jr c,fcn_p"])

    def test_every_staged_item(self):
        """Every item size a page's window allows (x even, 2-304 px wide, 1-208 lines tall; x0 0-15 apart from the
        cells' grid, y0 0-15): fb_stg counts the pieces fcp_next takes; they cover the item exactly, each at most
        128 x 64 (64 x 64 before field-7) and inside its place in page 3 (x 0-255), the places not overlapping; a
        band's pieces lie side by side there as in the map, and its copy (fst_chain) is the old staging's: the same
        rectangle in the map, the same pixels."""
        items = staged = merged = 0
        for x0 in range(0, 16, 2):
            for y0 in range(0, 16, 5):
                for w in range(2, 305, 2):
                    for h in range(1, 209, 3):
                        x1, y1 = x0 + w, y0 + h
                        old, new = staging(x0, y0, x1, y1, False), staging(x0, y0, x1, y1, True)
                        items += 1
                        self.assertEqual(old is None, new is None, (w, h))
                        if new is None:
                            continue
                        staged += 1
                        for (stg, scol, pieces), wmax in ((old, 64), (new, 128)):
                            self.assertEqual(len(pieces), stg, (w, h, wmax))
                            self.assertTrue(1 <= stg <= 4 and stg % scol == 0, (w, h, wmax))
                            area = 0
                            for i, (a, b, c, d, sx) in enumerate(pieces):
                                self.assertTrue(0 < c - a <= wmax and 0 < d - b <= 64, (w, h, wmax, i))
                                self.assertLessEqual(sx + (c - a), 256, (w, h, wmax, i))
                                area += (c - a) * (d - b)
                                for e, f, g, hh, sy in pieces[:i]:
                                    self.assertFalse(a < g and e < c and b < hh and f < d, (w, h, wmax, i))
                                    self.assertFalse(sx < sy + (g - e) and sy < sx + (c - a), (w, h, wmax, i))
                            self.assertEqual(area, w * h, (w, h, wmax))
                            for j in range(0, stg, scol):           # (a band's pieces side by side in page 3)
                                band = pieces[j:j + scol]
                                for a, b, c, d, sx in band:
                                    self.assertEqual(sx - band[0][4], a - band[0][0], (w, h, wmax, j))
                        old_c, new_c = band_copies(*old), band_copies(*new)
                        self.assertEqual([r for r, _ in old_c], [r for r, _ in new_c], (w, h))
                        merged += old[0] - new[0]
        self.assertEqual((items, staged), (8 * 4 * 152 * 70, 138240))
        self.assertGreater(merged, 0)

    def test_a_staged_piece_takes_no_cache(self):
        """A one-band item two places wide is one piece, the whole item: the caches are lent (fb_stage frees all
        three), so fb_piece sends a staged piece to the tiles before its cache test."""
        piece = code("field.asm", "fb_piece", "fp_lkok")
        k = piece.index("jp z,fp_page")
        self.assertLess(k, piece.index("ld a,(fb_stg)", k))
        self.assertLess(piece.index("jp nz,fp_tiles", k), piece.index("call fb_cfind"))
        stage = code("field.asm", "fb_stage", "fst_n")
        k = stage.index("ld hl,fb_cache")
        self.assertEqual(stage[k:k + 9], ["ld hl,fb_cache", "ld de,FB_CSZ", "ld (hl),0xFF", "inc hl", "ld (hl),0xFF",
                                          "dec hl", "add hl,de", "djnz fsg_c", "ret"])


def mkrom_constant(name: str):
    """A constant of tools/mkrom.py, read from its source."""
    for node in ast.parse((ROOT / "tools/mkrom.py").read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def map_word(mp: bytes, row: int, col: int) -> int:
    return mp[(row * 160 + col) * 2] | mp[(row * 160 + col) * 2 + 1] << 8


class TileLookupTests(unittest.TestCase):
    """TILE-LOOKUP (docs/PERF2_PLAN.md item 11): fb_tiles reads a row's tiles in the 8000h window (tiles.asm
    gt_row: the row's map bank mapped there once a row), get_tile for a row with patches; the cells' tiles are
    get_tile's."""

    def test_gt_row_is_the_routine_modelled(self):
        row = code("tiles.asm", "gt_row", "vat_win")
        self.assertEqual(row[:row.index("res 5,h") + 2],
                         ["ld l,a", "ld h,MP_ROW/256", "ld a,(hl)", "inc a", "ld h,0", "ret nz", "if VAT_ANIM",
                          "ld a,(lv_logic)", "cp BANK_L2", "ret z", "endif", "ld c,l", "ld b,h", "add hl,hl",
                          "add hl,bc", "ld bc,rowtab", "add hl,bc", "ld a,(lv_mapb)", "add a,(hl)", "call bank_8000",
                          "inc hl", "ld a,(hl)", "inc hl", "ld h,(hl)", "ld l,a", "res 5,h", "ret"])
        get = code("tiles.asm", "get_tile", "gt_row")        # (get_tile's read at A000h, as modelled below)
        k = get.index("ld de,rowtab")
        self.assertEqual(get[k - 7:k + 25],
                         ["ld a,d", "ld l,a", "ld h,0", "ld e,a", "ld d,0", "add hl,hl", "add hl,de", "ld de,rowtab",
                          "add hl,de", "ld a,(act_a000)", "push af", "ld a,(lv_mapb)", "add a,(hl)",
                          "call bank_a000", "inc hl", "ld a,(hl)", "inc hl", "ld h,(hl)", "ld l,a", "pop af", "pop de",
                          "push de", "push af", "ld d,0", "add hl,de", "add hl,de", "ld a,(hl)", "inc hl", "ld h,(hl)",
                          "ld l,a", "pop af", "call bank_a000"])
        self.assertEqual(get[:7], ["push de", "ld d,a", "ld l,a", "ld h,MP_ROW/256", "ld a,(hl)", "cp 0xFF",
                                   "jr z,gt_rom"])           # (a row with patches walks them: gt_row leaves it)

    def test_the_burst_reads_the_cells_so(self):
        body = code("field.asm", "fb_tiles", "ftl_ax")
        self.assertEqual(body.count("call gt_row"), 1)
        k = body.index("call gt_row")
        self.assertEqual(body[k - 1:k + 2], ["ld a,d", "call gt_row", "ld (fb_r),hl"])
        k = body.index("ld hl,(fb_r)")
        self.assertEqual(body[k:k + 17], ["ld hl,(fb_r)", "inc h", "dec h", "jr z,ftl_pt", "ld c,e", "ld b,0",
                                          "add hl,bc", "add hl,bc", "ld a,(hl)", "inc hl", "ld h,(hl)", "ld l,a",
                                          "call tile_srct", "jr ftl_x", "ld a,d", "call tile_src", "ld a,(fb_pe)"])
        # between the row's mapping and its cells' reads only tile_srct / tile_src (get_tile: the A000h window,
        # put back; tc_load: the 8000h window put back), ftl_ax, fb_cnext and the command (fin_c) run
        calls = sorted({l.split()[1] for l in body if l.startswith("call ")})
        self.assertEqual(calls, ["fb_cnext", "fin_c", "ftl_ax", "gt_row", "tile_src", "tile_srct"])
        load = code("tiles.asm", "tc_load", "tc_upload")
        k = load.index("call tc_upload")
        self.assertEqual(load[k - 2:k + 3], ["ld a,(act_8000)", "push af", "call tc_upload", "pop af",
                                             "call bank_8000"])
        self.assertEqual(code("tiles.asm", "tile_src", "tc_load")[:2], ["call get_tile", "push de"])
        for label, end in (("fb_cnext", "fb_fill"), ("ftl_ax", "fb_issue"), ("fb_issue_now", "fb_go")):
            self.assertFalse([l for l in code("field.asm", label, end) if "bank_" in l], label)
        for label, end in (("vdp_busy", "vdp_cmd_q"),):
            self.assertFalse([l for l in code("vdp.asm", label, end) if "bank_" in l], label)
        # the 8000h window's bank as it was at the call, put back on both ways out (ftl_rs)
        self.assertEqual(body[body.index("ld (fb_bn),a") + 1:][:2], ["ld a,(act_8000)", "push af"])
        self.assertEqual(body[-10:], ["jr z,ftl_lp", "jp ftl_rw", "ld hl,fbg_bob", "ex (sp),hl", "push hl", "pop af",
                                      "ld hl,act_8000", "cp (hl)", "ret z", "jp bank_8000"])
        self.assertEqual(body.count("jr z,ftl_rs") + body.count("jp c,ftl_bob"), 2)
        self.assertEqual(code("field.asm", "fbg_bob", "fb_part"), ["ld a,FP_BOB", "ld (fb_ph),a", "ld a,(fb_sn)",
                                                                   "ld (fb_ci),a", "jp fb_bobs"])
        # CLR, ARG and CMD once a call (fin_c: fb_issue_now without them)
        pre = body[:body.index("ld (fb_bn),a")]
        for b in ("ld (fb_cmd + 12),a", "ld hl,FB_HMMM * 256", "ld (fb_cmd + 13),hl"):
            self.assertIn(b, pre)
        self.assertEqual(code("field.asm", "fb_issue_now", "fb_go")[4:],
                         ["ld a,1", "ld (fb_shc),a", "ld hl,fb_cmd", "jp vdp_cmd"])

    def test_every_cell_of_every_level_as_get_tile(self):
        """The maps' banks and rowtab as tools/mkrom.py makes them (25 rows of 320 bytes a bank, FFh after them;
        rowtab: the bank from lv_mapb, the row's A000h address): every cell of every level's map read as get_tile
        reads it (the bank at A000h) and as fb_tiles reads it (gt_row: the bank at 8000h, the address less 2000h)
        gives the map's word."""
        maps = {n: ROOT / "build" / "msx" / f"level{n}.map" for n in (1, 2, 3)}
        if not all(f.exists() for f in maps.values()):
            self.skipTest("needs make msx (the levels' maps)")
        rpb, cols, bank = (mkrom_constant(k) for k in ("ROWS_PER_BANK", "COLS", "BANK"))
        self.assertEqual(cols, 160)
        rows1 = len(maps[1].read_bytes()) // (cols * 2)
        rowtab = [(r // rpb, 0xA000 + (r % rpb) * cols * 2) for r in range(rows1)]   # (mkrom.py's lines)
        src = (ROOT / "tools" / "mkrom.py").read_text()
        self.assertIn('rowtab.append(f"        db {r // ROWS_PER_BANK}\\n        dw 0x{0xA000 + (r % ROWS_PER_BANK) '
                      '* COLS * 2:04X}\\n")', src)
        n = 0
        for lv, f in maps.items():
            mp = f.read_bytes()
            rows = len(mp) // (cols * 2)
            self.assertLessEqual(rows, rows1)                       # (one rowtab: level 1's rows)
            banks = [mp[b * cols * 2:(b + rpb) * cols * 2] for b in range(0, rows, rpb)]
            banks = [c + b"\xff" * (bank - len(c)) for c in banks]
            for r in range(rows):
                b, a = rowtab[r]
                hl8 = a & ~0x2000                                   # (res 5,h)
                for c in range(cols):
                    at_a000 = a + 2 * c                             # get_tile: add hl,de twice
                    at_8000 = hl8 + 2 * c                           # fb_tiles: add hl,bc twice
                    self.assertTrue(0xA000 <= at_a000 and at_a000 + 1 <= 0xBFFF, (lv, r, c))
                    self.assertTrue(0x8000 <= at_8000 and at_8000 + 1 <= 0x9FFF, (lv, r, c))
                    g = banks[b][at_a000 - 0xA000] | banks[b][at_a000 - 0xA000 + 1] << 8
                    t = banks[b][at_8000 - 0x8000] | banks[b][at_8000 - 0x8000 + 1] << 8
                    self.assertEqual(t, g, (lv, r, c))
                    self.assertEqual(t, map_word(mp, r, c), (lv, r, c))
                    n += 1
        self.assertEqual(n, (51 + 50 + 50) * 160)


def cfind_window(w: int, c0: int, c1: int) -> int:
    """msx/field.asm fb_cfind's window move on one axis (fcf_got: columns, then rows the same way): the
    window's first cell w, the piece's first and last c0, c1 -> the window's first cell after it."""
    if c0 < w:                                          # cp (ix+2) / jr c,fcf_xm (A = c0)
        return c0
    if c1 <= w + 3:                                     # jr c,fcf_y / jr z,fcf_y
        return w
    return c1 - 3                                       # sub 3


class FillSkipTests(unittest.TestCase):
    """field-10 (docs/PERF2_PLAN.md item 19): fb_fill tests no cell when its cache holds all 16 cells of its
    window: the piece (at most 4 x 4 cells: fb_piece's cache path, the 5th column from the tiles) lies inside
    the window fb_cfind leaves, and every cell of the window has its bit (fb_cbit: row * 4 + column from the
    origin, both mod 4)."""

    def test_the_routine(self):
        fill = code("field.asm", "fb_fill", "ffl_held")
        self.assertEqual(fill[:6], ["call fb_cix", "ld a,(ix+6)", "and (ix+7)", "inc a", "jr z,ffl_done",
                                    "ld a,FB_BURST"])
        self.assertEqual(code("field.asm", "ffl_done", "fb_bg"), ["xor a", "ld (fb_ci),a", "ld a,FP_BG",
                                                                 "ld (fb_ph),a"])
        got = code("field.asm", "fcf_got", "fcf_mvx")
        self.assertEqual(got[4:24], ["ld a,(fb_cc)", "cp (ix+2)", "jr c,fcf_xm", "ld a,(ix+2)", "add a,3", "ld b,a",
                                     "ld a,(fb_cc + 2)", "cp b", "jr c,fcf_y", "jr z,fcf_y", "sub 3", "call fcf_mvx",
                                     "ld a,(fb_cc + 1)", "cp (ix+3)", "jr c,fcf_ym", "ld a,(ix+3)", "add a,3",
                                     "ld b,a", "ld a,(fb_cc + 3)", "cp b"])

    def test_the_window_holds_the_piece(self):
        """Every window place and piece of 1-4 cells (map columns 0-159, rows 0-50): the piece's cells lie in the
        window fb_cfind leaves, and with all 16 bits held each of them is held, whatever the origin."""
        n = 0
        for w in range(0, 157):
            for c0 in range(0, 157):
                for k in range(4):
                    c1 = c0 + k
                    nw = cfind_window(w, c0, c1)
                    self.assertTrue(nw <= c0 and c1 <= nw + 3, (w, c0, c1, nw))
                    n += 1
        self.assertEqual(n, 157 * 157 * 4)
        for ox in range(4):                             # (the bits of a window's 16 cells: each once)
            for oy in range(4):
                bits = {((r - oy) & 3) * 4 + ((c - ox) & 3) for r in range(10, 14) for c in range(20, 24)}
                self.assertEqual(bits, set(range(16)))


def converter_constant(name: str):
    """A constant of tools/msxsprites.py, read from its source (no numpy needed)."""
    for node in ast.parse((ROOT / "tools/msxsprites.py").read_text()).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


def halves(count: int) -> tuple[int, int]:
    """fc_get's entries into outi32 for a line of 'count' bytes, as the Z80 computes them: IX's offset
    (and 0xFE, cpl, add a,65) and IY's (two less for an odd count)."""
    a = ((~(count & 0xFE)) + 65) & 0xFF
    return a, a - 2 if count & 1 else a


class CacheUploadTests(unittest.TestCase):
    def test_the_places_lie_in_page_2s_lines_128_255(self):
        for x, y, w, h in converter_constant("L3_FC_PLACES"):
            self.assertTrue(128 <= y and y + h <= 256 and x % 2 == 0 and x + w <= 256, (x, y, w, h))
            self.assertLessEqual(w, 128)                        # (64 bytes a line at most: two halves of 32)

    def test_the_assembly_checks_them(self):
        f = [l.split(";")[0].strip() for l in (ROOT / "msx/field.asm").read_text().splitlines()]
        for cond, label in (("if 128 > FC_TOP_l3", "fc_top_err:"), ("if FC_END_l3 > 256", "fc_end_err:")):
            k = f.index(cond)
            self.assertEqual(f[k + 1:k + 4], [label, label, "endif"])
        src = (ROOT / "tools/msxsprites.py").read_text()
        self.assertIn('FC_TOP: equ {min(y for _, y, _, _ in L3_FC_PLACES)}', src)
        self.assertIn('FC_END: equ {max(y + h for _, y, _, h in L3_FC_PLACES)}', src)
        inc = ROOT / "build/msx/sprites_l3_field.inc"
        if inc.exists():                                       # (a conversion: its equates as the places)
            q = {m[1]: int(m[2]) for m in re.finditer(r"^(FC_TOP|FC_END): equ (\d+)", inc.read_text(), re.M)}
            places = converter_constant("L3_FC_PLACES")
            self.assertEqual(q, {"FC_TOP": min(p[1] for p in places), "FC_END": max(p[1] + p[3] for p in places)})

    def test_the_halves_of_every_line(self):
        for count in range(1, 65):
            ix, iy = halves(count)
            n1, n2 = (64 - ix) // 2, (64 - iy) // 2
            self.assertTrue(ix % 2 == 0 and iy % 2 == 0 and 0 <= iy <= ix <= 64, count)   # (an OUTI's start)
            self.assertEqual((n1, n2), (count >> 1, count - (count >> 1)), count)

    def test_the_loop_is_the_one_modelled(self):
        body = code("field.asm", "fcg_ld", "fcg_dn")
        k = body.index("ld a,(fc_bpl)", body.index("call vram_write"))
        self.assertEqual(body[k:k + 4], ["ld a,(fc_bpl)", "and 0xFE", "cpl", "add a,65"])
        self.assertEqual(body[k + 4:k + 18], ["ld e,a", "ld d,0", "ex de,hl", "ld bc,outi32", "add hl,bc", "push hl",
                                              "pop ix", "ld a,(fc_bpl)", "rra", "jr nc,fcg_ev", "dec hl", "dec hl",
                                              "push hl", "pop iy"])
        loop = body[body.index("ld c,VDP_DATA") + 1:]
        self.assertEqual(loop[:8], ["di", "ld a,e", "out (VDP_CTRL),a", "ld a,d", "out (VDP_CTRL),a", "ei",
                                    "call fcg_jx", "call fcg_jy"])
        self.assertNotIn("otir", body)
        self.assertNotIn("call vram_write", loop)
        self.assertEqual(code("field.asm", "fcg_jx", "fcg_jy"), ["jp (ix)"])
        chain = code("sprites.asm", "outi32", "pend_commit")
        self.assertEqual([l for l in chain if l != "outi"], ["ret"])
        self.assertEqual(chain, ["outi"] * 32 + ["ret"])         # (two bytes an OUTI: the entries' arithmetic)

    def test_every_cache_frame_fits_a_line(self):
        j = ROOT / "build/msx/sprites_l3.json"
        if not j.exists():
            self.skipTest("needs make msx (the pool with level 3)")
        for c in json.loads(j.read_text())["fc"]:
            self.assertTrue(c["w"] % 2 == 0 and c["w"] // 2 <= 64, c)


def code_lines(path: str) -> list[str]:
    """msx/PATH's lines without their comments, stripped (labels kept)."""
    return [l.split(";")[0].strip() for l in (ROOT / "msx" / path).read_text().splitlines()]


class EngineSetupTests(unittest.TestCase):
    """R2 (docs/PERF2_PLAN.md 5.2): the scroll engines' set-up in BANK_FRONT2 (ending.asm), reached from the
    main loop's code through the fixed area's f2_call (BANK_FRONT2 at A000h around it, act_a000 kept)."""
    MOVED = ("engines_init", "engines_jump", "scroll_init", "s38_init")

    def test_the_set_up_left_the_field_bank(self):
        field = (ROOT / "msx" / "field.asm").read_text()
        ending = (ROOT / "msx" / "ending.asm").read_text()
        for label in self.MOVED:
            self.assertIsNone(re.search(rf"^{label}:", field, re.M), label)
            self.assertIsNotNone(re.search(rf"^{label}:", ending, re.M), label)

    def test_its_calls_go_through_f2_call(self):
        rc2 = code_lines("rc2.asm")
        calls = [rc2[k + 1] for k, l in enumerate(rc2) if l in ("ld hl,engines_init", "ld hl,engines_jump")]
        self.assertEqual(sorted(calls), ["call f2_call", "call f2_call", "jp f2_call"])
        for path in ("rc2.asm", "cold.asm", "front.asm", "frontx.asm", "ending.asm", "isr.asm", "tiles.asm",
                     "scroll9938.asm", "scroll9958.asm", "vats.asm"):
            for l in code_lines(path):
                for label in self.MOVED:
                    if re.fullmatch(rf"(call|jp)( \w+,)? ?{label}", l.replace("  ", " ")):
                        self.assertEqual(path, "ending.asm", (path, l))      # (only its own jumps)

    def test_f2_call_is_field_calls_way_in_with_front2(self):
        self.assertEqual(code("rc2.asm", "f2_call", "rowtab"),
                         ["ld a,(act_a000)", "push af", "ld a,BANK_FRONT2", "jp fc_bk"])
        self.assertEqual(code("rc2.asm", "field_call", "fc_hl"),
                         ["ld a,(act_a000)", "push af", "ld a,BANK_FIELD", "call bank_a000", "call fc_hl", "pop af",
                          "jp bank_a000"])
        self.assertIn("fc_bk:  call bank_a000", (ROOT / "msx" / "rc2.asm").read_text())
        rc2 = code_lines("rc2.asm")             # (after the code, before the last table: no routine moves)
        k = rc2.index('include "grade.inc"')
        self.assertEqual([l for l in rc2[k + 1:rc2.index("rowtab:")] if l][:1], ["f2_call:"])

    def test_the_field_routines_it_runs_through_field_call(self):
        body = code("ending.asm", "engines_init", "s38_init") + code("ending.asm", "s38_init", "s38i_row")
        self.assertNotIn("call vat_init", body)
        pairs = [(body[k], body[k + 1]) for k, l in enumerate(body) if l == "ld hl,vat_init"]
        self.assertEqual(len(pairs), 2)
        self.assertTrue(all(b == "call field_call" for _, b in pairs), pairs)
        self.assertEqual(body.count("call fb_init"), 2)         # (R3: fb_init is in this bank, below)
        self.assertNotIn("ld hl,fb_init", body)
        k = body.index("di")
        self.assertEqual(body[k:k + 3], ["di", "call fb_init", "ei"])                      # (engines_jump)



class RelocationR3Tests(unittest.TestCase):
    """R3 (docs/PERF2_PLAN.md 5.2): the field's set-up and the V9938 builds' start and sync in BANK_FRONT2
    (ending.asm), behind the fixed area's f2_call; BANK_FIELD keeps the level's tables' copy (fb_fldcp: lv_fld
    points into it), the sync's gate (fb_sync) and the queue's way in with the page in C (fb_queuec)."""
    MOVED = ("fb_init", "fb_bbinit", "fbi_one", "fs_sync", "fs_dnp", "fs_lsz", "fs_bxs")
    KEPT = ("fb_fldcp", "fb_sync", "fb_queuec", "fb_bbadd", "fb_bbcell", "fq_new", "fb_queue")

    def test_where_they_are(self):
        field = (ROOT / "msx" / "field.asm").read_text()
        ending = (ROOT / "msx" / "ending.asm").read_text()
        for label in self.MOVED:
            self.assertIsNone(re.search(rf"^{label}:", field, re.M), label)
            self.assertIsNotNone(re.search(rf"^{label}:", ending, re.M), label)
        for label in self.KEPT:
            self.assertIsNotNone(re.search(rf"^{label}:", field, re.M), label)
            self.assertIsNone(re.search(rf"^{label}:", ending, re.M), label)

    def test_the_callers_reach_front2(self):
        # from the fixed area and the front end through f2_call; inside BANK_FRONT2 directly
        for path, label, n in (("scroll9938.asm", "fb_bbinit", 1), ("front.asm", "fb_init", 2)):
            lines = code_lines(path)
            calls = [lines[k + 1] for k, l in enumerate(lines) if l == "ld hl," + label]
            self.assertEqual(calls, ["call f2_call"] * n, (path, label))
        for path in ("rc2.asm", "cold.asm", "front.asm", "frontx.asm", "isr.asm", "tiles.asm", "scroll9938.asm",
                     "scroll9958.asm", "vats.asm", "field.asm", "sprites.asm", "bob.asm"):
            for l in code_lines(path):
                for label in self.MOVED:
                    self.assertIsNone(re.fullmatch(rf"(call|jp|jr)( \w+,)? ?{label}", l), (path, l))
        field = code("field.asm", "fb_sync", "fsy_no")
        self.assertEqual(field[-5:], ["ld hl,fs_sync", "call f2_call", "ld a,l", "cp 1", "ret"])

    def test_front2_reaches_the_field_through_field_call(self):
        field_labels = set(re.findall(r"^(\w+):", (ROOT / "msx" / "field.asm").read_text(), re.M))
        ending = code_lines("ending.asm")
        k = ending.index("fb_init:")
        sect = ending[k:]
        for i, l in enumerate(sect):
            m = re.fullmatch(r"(?:call|jp|jr)\s+(?:\w+,)?\s*(\w+)", l)
            if m:
                self.assertNotIn(m.group(1), field_labels, l)       # (BANK_FIELD is not mapped here)
            m = re.fullmatch(r"ld hl,(\w+)", l)
            if m and m.group(1) in field_labels and m.group(1) not in ("fb_dn0", "fb_dn1"):
                self.assertIn(sect[i + 1], ("call field_call", "jp field_call"), (l, sect[i + 1]))

    def test_the_copies_are_the_field_routines(self):
        def body(path, a, b, rename):
            out = code(path, a, b)
            for x, y in rename:
                out = [re.sub(rf"\b{x}\b", y, l) for l in out]
            return out
        self.assertEqual(body("ending.asm", "fs_dnp", "fs_lsz", []), code("field.asm", "fb_dnp", "fb_rect"))
        self.assertEqual(body("ending.asm", "fs_lsz", "fs_bxs", [("fsl_n", "fls_n")]),
                         code("field.asm", "fb_lsz", "fb_dnp"))
        want = code("field.asm", "fbx_set", "fb_lsz")
        lines = (ROOT / "msx" / "ending.asm").read_text().splitlines()
        i = next(k for k, l in enumerate(lines) if l.startswith("fs_bxs:"))
        got = [re.sub(r"\s+", " ", re.sub(r"^\w+:", "", l.split(";")[0]).strip()) for l in lines[i:]]
        got = [re.sub(r"\bfsb_c\b", "fxs_c", l) for l in got if l][:len(want)]
        self.assertEqual(got, want)

    def test_fb_init_is_the_set_up(self):
        init = code("ending.asm", "fb_init", "fb_bbinit")
        self.assertEqual(init[:2], ["ld hl,fb_fldcp", "call field_call"])
        self.assertEqual(code("field.asm", "fb_fldcp", "fb_frame"),
                         ["ld hl,(lv_fld)", "ld de,fb_flate", "ld bc,FB_FLDN", "ldir", "ret"])



def sync_parts(r, vis_c0, back_dir, prev_cy):
    """The model of ending.asm fs_rect and fs_copy (V9938-SYNC): rectangle r = (x0, y0, x1, y1) of fb_bb ->
    (the new column's part or None, [the copies' parts], the rest's part or None) for the page built for the
    right (back_dir 0: back_c0 = vis_c0 + 1) or the left (1: vis_c0 - 1), the kept rows [prev_cy - 1,
    prev_cy + 13)."""
    back_c0 = vis_c0 + (1 if back_dir == 0 else -1)
    bx = back_c0 * 16
    x0, y0, x1, y1 = r
    y0, y1 = max(y0, (prev_cy - 1) * 16), min(y1, (prev_cy + 13) * 16)
    x0, x1 = max(x0, bx), min(x1, bx + 256)
    if not (y0 < y1 and x0 < x1):
        return None, [], None
    x0, x1 = x0 & ~1, (x1 + 1) & ~1
    nx = bx + (240 if back_dir == 0 else 0)
    ov = (bx, bx + 240) if back_dir == 0 else (bx + 16, bx + 256)
    new = (max(x0, nx), y0, min(x1, nx + 16), y1)
    rest = (max(x0, ov[0]), y0, min(x1, ov[1]), y1)
    new = new if new[0] < new[2] else None
    rest = rest if rest[0] < rest[2] else None
    copies = []
    if rest:
        a, b = rest[1], rest[3]
        while a < b:                                    # (fs_copy: a part a call, each ending at a line 256)
            e = min(b, (a & ~255) + 256)
            copies.append(dict(sx=rest[0] - vis_c0 * 16, dx=rest[0] - bx, sy=a & 255, ny=e - a,
                               nx=rest[2] - rest[0], x=rest[0], y=a))
            a = e
    return new, copies, rest


class V9938SyncTests(unittest.TestCase):
    """V9938-SYNC (docs/PERF2_PLAN.md item 7): the page being built takes its BOB rectangles from the page shown
    with one HMMM each where that page holds its list's composition (ending.asm fs_sync, fs_rect, fs_copy), the
    new column's part composed; its steps among the field engine's items (field.asm fb_sync from fb_step and
    fn_take, after the page shown's published items), its list from the start (fb_bsq: tiles.asm fb_mark38's
    tiles on that page meet it), a change of the page shown meanwhile marks what it has not copied (fs_dirty)."""

    def test_a_flip_waits_for_the_vdp(self):
        # (the sync's last copy, started at any time while its page was hidden, may still run when the marker
        #  lets the flip come: fb_frame's flip waits for the VDP before the picture that shows it is published)
        f = code("field.asm", "fbf_38", "fbf_b")
        k = f.index("call nz,vdp_wait")
        self.assertEqual(f[k - 3:k + 2], ["ld b,(hl)", "ld (hl),a", "inc b", "call nz,vdp_wait", "ld a,(hl)"])
        self.assertLess(k, f.index("call fq_purge"))      # (not at the first picture since fb_init: fb_vlast FFh)
        main = code("rc2.asm", "mainloop", "ml_tk")
        self.assertLess(main.index("call do_update"), main.index("ld hl,fb_frame"))
        self.assertLess(main.index("ld hl,fb_frame"), main.index("call do_publish"))

    def test_the_hooks(self):
        self.assertEqual(code("field.asm", "fb_next", "fn_take"),
                         ["ld a,(fb_qn)", "or a", "jr nz,fn_take", "xor a", "ld (fb_qlk),a", "or 1", "ret"])
        take = code("field.asm", "fn_take", "fn_key")
        self.assertEqual(take[0], "ld c,0")                 # (fb_qlk from fn_got on: the sync's step without it)
        k = take.index("call fb_sync")
        self.assertEqual(take[k:k + 3], ["call fb_sync", "jp c,fn_take", "jr nz,fn_none"])
        self.assertLess(take.index("jr z,fn_s3"), k)         # (after the page shown's published items)
        g = code("field.asm", "fn_got", "fn_rect")
        self.assertEqual(g[:2], ["ld a,1", "ld (fb_qlk),a"])
        step = code("field.asm", "fb_step", "fwk_ph")
        self.assertEqual(step[step.index("call fb_sync"):][:3], ["call fb_sync", "jr c,fb_step", "ret nz"])
        bba = code("field.asm", "fb_bbadd", "fba_go")
        self.assertEqual(bba[:7], ["ld a,(fb_bsq)", "ld hl,s38_back_c0", "cp (hl)", "jr nz,fba_ad", "ld a,(fb_sbi)",
                                   "inc a", "jr z,fba_ad"])     # (its sync under way: fs_dirty only)
        self.assertEqual(bba[7:9], ["ld hl,fs_dirty", "jp f2_call"])
        mark = code("tiles.asm", "fb_mark38", "fm38_go")
        self.assertIn("ld hl,fb_bsq", mark)
        self.assertNotIn("ld hl,fb_bsync", mark)
        vm = code("field.asm", "vat_mmark", "vat_srcs")
        self.assertEqual(vm[-4:], ["ld a,0xFF", "ld (fb_bsync),a", "ld (fb_bsq),a", "jp fb_bbadd"])
        self.assertIn("ld (fb_bsq),a", code("ending.asm", "fb_init", "fb_bbinit"))
        bb = code("ending.asm", "fb_bbinit", "fbi_one")
        self.assertLess(bb.index("ld (fb_bsq),a"), bb.index("call fbi_add"))
        self.assertIn("ld hl,fqp_lp", bb)                   # (the page being built's items dropped)

    def test_the_ram(self):
        inc = (ROOT / "msx" / "msx.inc").read_text()
        addr = {n: int(v, 0) for n, v in re.findall(r"^(\w+):\s+equ (0x[0-9A-Fa-f]+)", inc, re.M)}
        mine = {"fb_bsq": 0x074B, "fb_sbi": 0xE0FE, "fb_sdm": 0xE0FF}
        for n, a in mine.items():
            self.assertEqual(addr[n], a, n)
            self.assertEqual([m for m, b in addr.items() if b == a and m != n], [], n)

    def test_the_steps(self):
        sy = code("ending.asm", "fs_sync", "syn_done")
        self.assertEqual(sy[:4], ["ld l,2", "ld a,(fb_rdy)", "or a", "ret nz"])   # (its copy prepared first)
        self.assertLess(sy.index("call nz,fs_begin"), sy.index("cp FB_QMAX - 1"))  # (room for a rectangle's items)
        self.assertIn("jr z,fs_mark", sy)
        self.assertIn("call fs_rect", sy)
        self.assertIn("call syn_done", code("ending.asm", "fs_rect", "fs_ovx"))   # (a rectangle done)
        self.assertIn("cp FB_QMAX", code("ending.asm", "fs_mark", "fs_comp"))
        lb = code("ending.asm", "fs_lbox", "fs_newc")
        self.assertEqual(lb[lb.index("ld hl,fb_rect"):][:2], ["ld hl,fb_rect", "call field_call"])
        cp = code("ending.asm", "fs_copy", "fs_qmeet")
        for l in ("ld a,FB_HMMM", "ld (fb_cmd + 14),a", "ld (fb_cmd + 12),a", "ld (fb_cmd + 13),a", "ld (fb_rdy),a",
                  "ld a,(s38_vis_c0)", "ld a,(s38_back_c0)", "ld (fb_cmd + 3),a", "ld (fb_cmd + 7),a",
                  "call syn_done", "ld (ix+2),l"):
            self.assertIn(l, cp)
        r = code("ending.asm", "fs_rect", "fs_ovx")
        self.assertLess(r.index("call fs_qmeet"), r.index("jp fs_copy"))
        self.assertLess(r.index("ld a,(fb_sdm)"), r.index("jp fs_copy"))
        self.assertLess(r.index("call fs_lbox"), r.index("call fs_qmeet"))

    def test_the_parts(self):
        import random
        rng = random.Random(11)
        n = copies = 0
        for _ in range(20000):
            vis_c0 = rng.randrange(1, 150)
            d = rng.randrange(2)
            cy = rng.randrange(0, 40)
            x0 = vis_c0 * 16 + rng.randrange(-80, 300)
            y0 = (cy - 1) * 16 + rng.randrange(-60, 250)
            r = (max(0, x0), max(0, y0), max(0, x0) + rng.randrange(1, 140), max(0, y0) + rng.randrange(1, 140))
            new, cps, rest = sync_parts(r, vis_c0, d, cy)
            back_c0 = vis_c0 + (1 if d == 0 else -1)
            # the clipped rectangle (fs_rect): the new column's part and the rest, side by side, nothing else
            parts = [p for p in (new, rest) if p]
            if not parts:
                continue
            n += 1
            self.assertEqual(sum(p[2] - p[0] for p in parts), max(p[2] for p in parts) - min(p[0] for p in parts))
            for p in parts:
                self.assertEqual(p[0] % 2, 0)
                self.assertEqual(p[2] % 2, 0)
                self.assertTrue(back_c0 * 16 <= p[0] < p[2] <= back_c0 * 16 + 256)
            if new:                                     # (the page shown does not hold it)
                self.assertLessEqual(new[2] - new[0], 16)
                self.assertTrue(new[2] <= vis_c0 * 16 or new[0] >= vis_c0 * 16 + 256)
            if rest:                                    # (the page shown holds it)
                self.assertTrue(vis_c0 * 16 <= rest[0] and rest[2] <= vis_c0 * 16 + 256)
            # the copies (fs_copy): the rest, line for line; one page's x on both; within a 256-line page
            area = 0
            for c in cps:
                copies += 1
                self.assertTrue(0 <= c["sx"] and c["sx"] + c["nx"] <= 256)
                self.assertTrue(0 <= c["dx"] and c["dx"] + c["nx"] <= 256)
                self.assertEqual(c["sx"] + vis_c0 * 16, c["dx"] + back_c0 * 16)      # (the same map x)
                self.assertTrue(0 < c["ny"] and c["sy"] + c["ny"] <= 256)
                self.assertEqual(c["sy"], c["y"] & 255)
                area += c["nx"] * c["ny"]
            if rest:
                self.assertEqual(area, (rest[2] - rest[0]) * (rest[3] - rest[1]))
                self.assertLessEqual(len(cps), 2)       # (14 kept rows: 224 lines cross a line 256 once)
        self.assertGreater(n, 10000)
        self.assertGreater(copies, 10000)


FB_ENT = 7


def fd_lkchk(want: list[bytes], page: list[bytes] | None) -> int:
    """msx/field.asm fd_lkchk as the Z80 runs it: fb_want's entries, the page's list (None: count FFh,
    unknown) -> fb_lkq."""
    wn = len(want)
    if wn == 0:                                     # ld a,(fb_wn) / or a / ret z
        return 0
    if page is None or len(page) != wn:             # dec hl / cp (hl) / ret nz
        return 0
    w, p = b"".join(want), b"".join(page)
    i = 0
    for _ in range(wn):                             # fdk_e .. djnz fdk_e
        if (w[i] ^ p[i]) & 0x7F:                    # xor (hl) / and 0x7F / ret nz
            return 0
        for _ in range(FB_ENT - 1):                 # fdk_b: inc hl / inc de / cp (hl) / ret nz
            i += 1
            if w[i] != p[i]:
                return 0
        i += 1
    return 1


def look_only(want: list[bytes], page: list[bytes] | None) -> bool:
    """The rule: the same BOBs in the same order, their frames equal but for bit 7 (a hit flash's look)."""
    return (page is not None and 0 < len(want) == len(page)
            and all(a[0] & 0x7F == b[0] & 0x7F and a[1:] == b[1:] for a, b in zip(want, page)))


class LookOnlyTests(unittest.TestCase):
    """flash-1 (docs/PERF2_PLAN.md item 3): a look-only change takes each piece's background from its page
    (msx/field.asm fd_lkchk, the flags fb_lkf0 / fb_lkf1 / fb_lkq, fp_lkok, FP_PAGE's fb_pgbg)."""

    def test_fd_lkchk_is_the_routine_modelled(self):
        self.assertEqual(code("field.asm", "fd_lkchk", "fb_qent"),
                         ["xor a", "ld (fb_lkq),a", "ld a,(fb_wn)", "or a", "ret z", "ld hl,(fb_dptr)", "dec hl",
                          "cp (hl)", "ret nz", "inc hl", "ld b,a", "ld de,fb_want", "ld a,(de)", "xor (hl)",
                          "and 0x7F", "ret nz", "ld c,FB_ENT - 1", "inc hl", "inc de", "ld a,(de)", "cp (hl)", "ret nz",
                          "dec c", "jr nz,fdk_b", "inc hl", "inc de", "djnz fdk_e", "ld a,1", "ld (fb_lkq),a", "ret"])

    def test_fd_lkchk_finds_look_only_changes_only(self):
        import random
        rng = random.Random(7)
        n = hits = 0
        for _ in range(20000):
            want = [bytes([rng.choice((0x98, 0xA3, 0x18, 0x23))] + [rng.randrange(256) for _ in range(6)])
                    for _ in range(rng.randrange(0, 9))]
            page = [bytearray(e) for e in want]
            for e in page:                          # (some looks, sometimes another byte or BOB)
                if rng.random() < 0.5:
                    e[0] ^= 0x80
                if rng.random() < 0.05:
                    e[rng.randrange(7)] ^= 1 << rng.randrange(7)
            page = [bytes(e) for e in page]
            if rng.random() < 0.05:
                page = page[:-1] if page else [want[0] if want else bytes(7)]
            if rng.random() < 0.03:
                page = None
            if page == want:                        # (fb_diff returns before: nothing changes)
                continue
            n += 1
            hits += fd_lkchk(want, page)
            self.assertEqual(fd_lkchk(want, page), int(look_only(want, page)), (want, page))
        self.assertGreater(hits, 1000)
        self.assertGreater(n - hits, 1000)

    def test_the_flags_rules(self):
        diff = code("field.asm", "fb_diff", "fd_copy")
        k = diff.index("ld (fb_dptr),hl")
        self.assertEqual(diff[k + 1], "call fd_lkchk")              # (fb_dptr set, before any item is queued)
        self.assertLess(k, diff.index("call nz,fb_qent"))
        self.assertEqual(code("field.asm", "fd_copy", "fd_lkchk")[:2], ["xor a", "ld (fb_lkq),a"])
        self.assertEqual(code("field.asm", "fq_go", "fq_x1")[:8],
                         ["ld c,a", "ld a,(fb_lkq)", "or a", "jr nz,fq_lk", "ld h,a", "ld l,a", "ld (fb_lkf0),hl",
                          "ld a,(fb_tick)"])
        step = code("field.asm", "fb_step", "fwk_ph")
        self.assertEqual(step[-8:], ["jr c,fb_step", "ret nz", "xor a", "ld (fb_busy),a", "inc a", "ld (fb_lkf0),a",
                                     "ld (fb_lkf1),a", "ret"])        # (nothing queued, composed or to sync)
        init = code("ending.asm", "fb_init", "fb_bbinit")          # (BANK_FRONT2 since R3)
        z = init.index("xor a")
        for f in ("fb_lkf0", "fb_lkf1", "fb_lkq"):
            self.assertIn(f"ld ({f}),a", init[z:init.index("ld a,FB_SX")])
        # fq_go is the queue's only way in (fb_queue's) but for the sync's marker (fq_new, which composes
        # nothing; ending.asm fs_sync through field_call since R3): outside fq_go's own code no jump into it
        field = (ROOT / "msx" / "field.asm").read_text()
        own = field[field.index("\nfq_go:"):field.index("\nfq_fits:")]
        rest = field.replace(own, "")
        calls = re.findall(r"^\s+(?:call|jp|jr)\s+(?:\w+,)?(fq_go|fq_add|fq_new|fq_mrg|fq_lk)\b", rest, re.M)
        self.assertEqual(sorted(calls), ["fq_go"])
        self.assertIn("call fq_go", code("field.asm", "fb_queue", "fq_go"))
        ending = code_lines("ending.asm")
        news = [ending[k + 1] for k, l in enumerate(ending) if l == "ld hl,fq_new"]
        self.assertEqual(news, ["call field_call"])
        self.assertIsNone(re.search(r"^\s+(?:call|jp|jr)\s+(?:\w+,)?(fq_go|fq_add|fq_new|fq_mrg|fq_lk)\b",
                                    (ROOT / "msx" / "ending.asm").read_text(), re.M))

    def test_the_ram(self):
        inc = (ROOT / "msx" / "msx.inc").read_text()
        eq = {m[1]: int(m[2], 16) for m in re.finditer(r"^(\w+):\s+equ 0x([0-9A-Fa-f]+)", inc, re.M)}
        self.assertEqual((eq["fb_lkf0"], eq["fb_lkf1"], eq["fb_lkq"]), (0xED09, 0xED0A, 0xED0B))
        self.assertEqual([k for k, v in eq.items() if 0xED09 <= v <= 0xED0B], ["fb_lkf0", "fb_lkf1", "fb_lkq"])
        bm_n = int(re.search(r"^BM_N:\s+equ (\d+)", inc, re.M)[1])
        self.assertLessEqual(eq["bm_gen"] + 2 * bm_n, 0xED09)      # (the beams' words end before them)
        self.assertEqual(eq["sb_end"], 0xED0C)

    def test_fp_lkok_and_its_rule(self):
        self.assertEqual(code("field.asm", "fp_lkok", "fp_page"),
                         ["ld a,(fb_cur)", "bit 7,a", "ret nz", "ld hl,fb_lkf0", "rra", "jr nc,fpk_p", "inc hl",
                          "ld a,(hl)", "dec a", "ret nz", "ld a,(rd_head)", "ld hl,rd_tail", "cp (hl)", "ret nz",
                          "ld a,(fb_eng)", "or a", "jr nz,fpk_38", "ld a,(q_col)", "ld hl,q_row", "and (hl)",
                          "jr fpk_q", "ld a,(fb_cur)", "ld hl,s38_vis_page", "xor (hl)", "and 1", "ret nz",
                          "ld a,(s38_back_c0)", "ld hl,fb_bsync", "cp (hl)", "jr nz,fpk_rq", "inc a", "ret nz",
                          "ld a,(s38_rq)", "inc a", "ret nz", "call fb_inwin", "sbc a,a", "inc a", "ret"])
        piece = code("field.asm", "fb_piece", "fp_lkok")
        k = piece.index("call fp_lkok")
        self.assertEqual(piece[k - 4:k + 8], ["if VAT_ANIM", "call vat_inbox", "jp nz,fp_tiles", "endif",
                                              "call fp_lkok", "jp z,fp_page", "if VAT_ANIM = 0", "ld a,(fb_stg)",
                                              "or a", "jp nz,fp_tiles", "endif", "ld hl,(fb_cur + 1)"])
        self.assertLess(piece.index("ld (fb_cc + 3),a"), k)          # (fb_px .. fb_pe, the cells: set)
        self.assertEqual(code("field.asm", "fp_page", "fb_pgbg"),
                         ["call fcp_sp", "xor a", "ld (fb_ci),a", "ld a,FP_PAGE", "ld (fb_ph),a", "ret"])

    def test_the_v9938_rule(self):
        """On the V9938 the page path takes the page shown only, and not while the page beside it is synced
        (fb_bsync = s38_back_c0, both FFh: none): the model of fpk_38's test against the rule, every state."""
        def fpk_38(page: int, vis: int, back: int, bsync: int) -> bool:
            if (page ^ vis) & 1:                            # xor (hl) / and 1 / ret nz
                return False
            if back != bsync:                               # cp (hl) / jr nz,fpk_rq
                return True
            return (back + 1) & 0xFF == 0                   # inc a / ret nz
        for page in (0, 1):
            for vis in (0, 1):
                for back in (0, 1, 2, 142, 143, 144, 0xFF):
                    for bsync in (0, 1, 142, 143, 144, 0xFF):
                        rule = page == vis and not (bsync == back and back != 0xFF)
                        self.assertEqual(fpk_38(page, vis, back, bsync), rule, (page, vis, back, bsync))
        # the page shown is never rebuilt and its first column changes only at a flip, which needs the page
        # beside synced (fb_bsync, the sync's marker taken by fb_next between items): an item started while
        # it is not synced meets no flip
        nxt = code("field.asm", "fb_next", "fn_rect")
        self.assertIn("ld (fb_bsync),a", nxt)
        s38 = code("scroll9938.asm", "s38_update", "s38_target")
        k = s38.index("ld a,(fb_bsync)")
        self.assertEqual(s38[k + 1:k + 3], ["cp e", "jr nz,s38u_hold"])
        self.assertLess(k, s38.index("ld (s38_vis_c0),a"))

    def test_the_page_phase(self):
        self.assertRegex((ROOT / "msx" / "field.asm").read_text(), r"\nFP_WAIT:\s+equ 6\b.*\nFP_PAGE:\s+equ 7\b")
        self.assertEqual(code("field.asm", "fwk_ph", "fb_next")[-3:], ["dec a", "jp z,fb_wait", "jp fb_pgbg"])
        body = code("field.asm", "fb_pgbg", "fb_cfind")
        k = body.index("call fb_pcmd")
        self.assertEqual(body[k - 1:k + 15], ["ld hl,fb_cmd", "call fb_pcmd", "ld hl,fb_cmd", "ld de,fb_cmd + 4",
                                              "ld b,4", "ld a,(de)", "ld c,(hl)", "ld (hl),a", "ld a,c", "ld (de),a",
                                              "inc hl", "inc de", "djnz fpg_sw", "ld a,FB_HMMM", "jp fb_issue",
                                              "ld a,FP_BOB"])
        self.assertEqual(body[:8], ["ld a,(fb_ci)", "cp 4", "jr nc,fpg_dn", "inc a", "ld (fb_ci),a", "dec a",
                                    "call fb_part", "jr nc,fb_pgbg"])
        self.assertEqual(body[-4:], ["ld (fb_ph),a", "ld a,(fb_sn)", "ld (fb_ci),a", "jp fb_bobs"])


if __name__ == "__main__":
    unittest.main()
