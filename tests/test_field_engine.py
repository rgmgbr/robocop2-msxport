"""The field engine's arithmetic of performance campaign 2 (docs/PERF2_PLAN.md): field-2's tile burst (msx/field.asm
fb_tiles, ftl_ax: a cell's part in a piece by 8-bit arithmetic on the piece's corner) against the 16-bit clip it
replaced (fb_rpiece, fb_dscr), on every piece position and extent and every cell. Stdlib only."""
from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
