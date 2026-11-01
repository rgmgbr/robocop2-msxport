"""The field engine's arithmetic of performance campaign 2 (docs/PERF2_PLAN.md): field-2's tile burst (msx/field.asm
fb_tiles, ftl_ax: a cell's part in a piece by 8-bit arithmetic on the piece's corner) against the 16-bit clip it
replaced (fb_rpiece, fb_dscr), on every piece position and extent and every cell; FC-UPLOAD's line loop (fc_get:
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


if __name__ == "__main__":
    unittest.main()
