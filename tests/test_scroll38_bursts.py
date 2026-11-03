"""Performance campaign 2's scroll-1, the V9938's part (docs/PERF2_PLAN.md item 6, after V9938-SYNC): the new
column's tiles in a row while the play-field engine has no work (msx/ending.asm s38_colb and fs_stop38, reached
from msx/scroll9938.asm s38_work through f2_call), the pending row's still one a call; and lane W2C's review's
fix: a changed cell handed to the play-field BOBs waits for the build's copy before the page being built takes it
(s38_redraw, rd_phase 2, s38_covr). The loop and the stop rule as built, the rule's decision on every state it
reads, fb_pend's exits (the carry the rule returns), each tile waiting for the one before, the slot rule.
Stdlib only."""
from __future__ import annotations

import itertools
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def code(path: str, label: str, end: str) -> list[str]:
    """The code lines of msx/PATH from LABEL: up to (not with) the label END:, labels dropped."""
    lines = (ROOT / "msx" / path).read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(label + ":"))
    j = next(k for k, l in enumerate(lines) if k > i and l.startswith(end + ":"))
    out = []
    for l in lines[i:j]:
        c = re.sub(r"^\w+:", "", l.split(";")[0]).strip()
        if c:
            out.append(re.sub(r"\s+", " ", c))
    return out


def block(path: str, label: str, n: int) -> list[str]:
    """N code lines of msx/PATH from the line of LABEL: on, labels kept, comments and blank lines dropped."""
    lines = (ROOT / "msx" / path).read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(label + ":"))
    out = []
    for l in lines[i:]:
        c = re.sub(r"\s+", " ", l.split(";")[0].strip())
        if c:
            out.append(c)
        if len(out) == n:
            return out
    raise AssertionError(f"{label}: fewer than {n} lines")


STOP = ["ld a,(split_armed)", "or a", "call z,s38_rburst",               # the changed cells' window,
        "ld a,(fb_busy)", "cp 1", "ccf", "ret c",                          # the field engine's work,
        "if VAT_ANIM", "ld a,(vat_fr + VF_RDY)", "or a", "scf", "ret nz", "endif",   # (a vat column)
        "ld a,(fb_cq)", "rra", "ret c", "call fb_pend", "ret z", "scf", "ret"]       # a copy, a published item


def stop(lines: list[str], ram: dict[str, int], pend: bool, vat: bool) -> tuple[bool, bool]:
    """fs_stop38 as the Z80 runs it (VAT selects the if block) -> (the carry it returns: True when the burst stops,
    whether the changed cells' window ran). fb_pend: NZ when pend, its carry clear (FbPendTests); s38_rburst: its
    flags unknown."""
    c = z = None
    a = 0
    window = False
    skip = False
    for ins in lines:
        if ins == "if VAT_ANIM":
            skip = not vat
            continue
        if ins == "endif":
            skip = False
            continue
        if skip:
            continue
        if ins.startswith("ld a,("):
            a = ram[ins[6:-1]]
        elif ins == "or a":
            c, z = False, a == 0
        elif ins == "call z,s38_rburst":
            if z:
                window = True
                c = z = None
        elif ins == "cp 1":
            c, z = a < 1, a == 1
        elif ins == "ccf":
            c = not c
        elif ins == "rra":
            a, c = (a >> 1) | (0x80 if c else 0), bool(a & 1)
        elif ins == "call fb_pend":
            z, c = not pend, False
        elif ins == "scf":
            c = True
        elif ins == "ret c":
            if c is None:
                raise AssertionError("ret c on an unknown carry")
            if c:
                return True, window
        elif ins in ("ret z", "ret nz"):
            if z is None:
                raise AssertionError(ins + " on an unknown zero flag")
            if z == (ins == "ret z"):
                return c, window
        elif ins == "ret":
            return c, window
        else:
            raise AssertionError(ins)
    raise AssertionError("no return")


def routine(path: str, label: str) -> list[str]:
    """The code lines of msx/PATH from LABEL: to the first blank line after it, labels dropped, if/endif kept."""
    lines = (ROOT / "msx" / path).read_text().splitlines()
    i = next(k for k, l in enumerate(lines) if l.startswith(label + ":"))
    out = []
    for l in lines[i:]:
        if not l.strip():
            break
        c = re.sub(r"\s+", " ", re.sub(r"^\w+:", "", l.split(";")[0]).strip())
        if c:
            out.append(c)
    return out


class ColumnBurstTests(unittest.TestCase):
    def test_s38_work_hands_the_column_to_front2(self):
        work = code("scroll9938.asm", "s38_work", "s38_rburst")
        self.assertEqual(work[:2], ["call vdp_busy", "ret nz"])
        k = work.index("ld hl,s38_colb")
        self.assertEqual(work[k - 2:k + 2], ["or a", "jr nz,s38w_copy", "ld hl,s38_colb", "jp f2_call"])
        self.assertNotIn("call s38_col_tile", work)
        # the pending row: one tile a call, as before
        self.assertEqual(code("scroll9938.asm", "s38w_rq", "s38w_b")[:3], ["ld a,(s38_rq)", "cp 0xFF", "jp nz,s38_row_step"])

    def test_the_burst(self):
        """A tile, its count, the next one while fs_stop38 lets it; the last one starts the copy's phase."""
        self.assertEqual(code("ending.asm", "s38_colb", "fyk_end"),
                         ["call s38_col_tile", "ld hl,s38_i", "inc (hl)", "ld a,(hl)", "cp VIEW_ROWS", "jr nc,fyk_end",
                          "call fs_stop38", "jr nc,s38_colb", "ret"])
        self.assertEqual(code("ending.asm", "fyk_end", "fs_stop38"), ["ld (hl),0", "ld a,1", "ld (s38_phase),a", "ret"])

    def test_the_stop_rule(self):
        """C (stop) when the play-field BOBs have any work (fb_busy), a copy of theirs waits for the blank (fb_cq 1 or
        3) or they have work of a published picture (fb_pend NZ), and in VAT_ANIM=1 builds a vat column waits for the
        blank; between the HUD split and the VBLANK (split_armed 0) the changed cells' window first, whatever it
        then decides."""
        self.assertEqual(routine("ending.asm", "fs_stop38"), STOP)
        for armed, busy, cq, rdy, pend, vat in itertools.product((0, 1), (0, 1), range(5), (0, 1), (False, True),
                                                                (False, True)):
            ram = {"split_armed": armed, "fb_busy": busy, "fb_cq": cq, "vat_fr + VF_RDY": rdy}
            want = bool(busy) or (vat and bool(rdy)) or bool(cq & 1) or pend
            self.assertEqual(stop(STOP, ram, pend, vat), (want, armed == 0), (armed, busy, cq, rdy, pend, vat))
        self.assertEqual(code("scroll9938.asm", "s38_rburst", "s38_redraw")[:3],
                         ["ld b,RD_BURST*2", "call rd_win", "ret nz"])   # (on into the blank after the VBLANK)

    def test_front2_reaches_only_fixed_code(self):
        """The burst runs in BANK_FRONT2 at A000h: the routines it calls are the fixed area's (scroll9938.asm,
        tiles.asm), which put the A000h window back where they map it (field_call, get_tile)."""
        calls = [c for c in code("ending.asm", "s38_colb", "fyk_end") if c.startswith("call ")]
        self.assertEqual(calls, ["call s38_col_tile", "call fs_stop38"])
        calls = sorted(c for c in routine("ending.asm", "fs_stop38") if c.startswith("call "))
        self.assertEqual(calls, ["call fb_pend", "call z,s38_rburst"])
        for path, label in (("scroll9938.asm", "s38_col_tile"), ("scroll9938.asm", "s38_rburst"),
                            ("tiles.asm", "fb_pend")):
            self.assertIsNotNone(re.search(rf"^{label}:", (ROOT / "msx" / path).read_text(), re.M), label)


class FbPendTests(unittest.TestCase):
    def test_every_exit_clears_the_carry(self):
        """fs_stop38 returns fb_pend's carry on its Z exits: every return of fb_pend (and of fpd_it, whose NZ it
        returns) follows an instruction that clears it."""
        lines = code("tiles.asm", "fb_pend", "fb_redraw")
        rets = [k for k, c in enumerate(lines) if c in ("ret", "ret z", "ret nz")]
        self.assertGreaterEqual(len(rets), 7)
        for k in rets:
            self.assertIn(lines[k - 1], ("or a", "xor a", "or 1", "call fpd_it"), (k, lines[k - 1]))
        self.assertNotIn("ret c", lines)
        self.assertNotIn("ret nc", lines)


class TileWaitTests(unittest.TestCase):
    def test_each_tile_waits_for_the_one_before(self):
        """The burst's tiles go through tile_to_page, which waits for the VDP (vdp_wait, and vdp_cmd again) after the
        tile's set-up: the set-up runs while the tile before is copied."""
        self.assertEqual(code("scroll9938.asm", "tile_to_page", "ttp_count"),
                         ["call ttp_prep", "ret nc", "call vdp_wait", "ld hl,cmdbuf", "call vdp_cmd"])
        self.assertIn("call vdp_wait", code("vdp.asm", "vdp_cmd", "vdp_cmd_q"))
        self.assertEqual(code("scroll9938.asm", "s38_col_tile", "s38_copy_chunk")[-1], "jp tile_to_page")


class RedrawWaitTests(unittest.TestCase):
    def test_a_cell_handed_to_the_bobs_waits_for_the_copy(self):
        """A changed cell whose first phase goes to the play-field BOBs (fb_redraw NZ: rd_phase 2) is drawn on the
        V9938's page being built only once that build's copy has passed its row slot (s38_covr): the copy brings the
        slot from the page shown, which gets the new tile only when the BOBs compose it. Meanwhile the cell stays the
        oldest (no rd_pop) and the call returns Z (the other work goes on, the copy among it). A first phase drawn on
        the page shown (rd_phase 1), no page being built, or a flip's new displayed page: at once, as before."""
        red = code("scroll9938.asm", "s38_redraw", "s38_shown")
        self.assertEqual(red[red.index("call fb_redraw") + 1], "jr nz,s38r_fb")
        self.assertEqual(block("scroll9938.asm", "s38r_vis", 7),
                         ["s38r_vis:", "ld a,1", "s38r_ph:", "ld (rd_phase),a", "or a", "ret", "s38r_fb:"])
        self.assertEqual(block("scroll9938.asm", "s38r_fb", 6),
                         ["s38r_fb:", "ld a,2", "jr s38r_ph", "s38r_wait:", "xor a", "ret"])
        self.assertEqual(block("scroll9938.asm", "s38r_back", 11),
                         ["s38r_back:", "dec a", "jr z,s38r_go", "ld a,(s38_back_c0)", "inc a", "jr z,s38r_go",
                          "ld a,d", "call s38_covr", "jr z,s38r_wait", "s38r_go:", "call rd_pop"])
        k = red.index("jr nz,s38r_back")
        self.assertEqual(red[k - 2:k], ["ld a,(rd_phase)", "or a"])

    def test_a_flip_s_new_page_lets_the_bobs_compose(self):
        """During a flip not on screen yet (s38_flip_wait) the new displayed page takes a changed cell as a page shown
        does: where a BOB of its list meets the cell the BOBs compose it (fb_redraw NZ: nothing drawn here), else the
        tile is drawn there (a tile drawn over a BOB was a hole in it when the flip showed)."""
        self.assertEqual(block("scroll9938.asm", "s38r_go", 9),
                         ["s38r_go:", "call rd_pop", "ld a,(s38_flip_wait)", "or a", "jr z,s38r_bk",
                          "ld a,(s38_vis_page)", "call fb_redraw", "jr nz,s38r_nz", "ld a,(s38_vis_c0)"])
        self.assertEqual(block("scroll9938.asm", "s38r_nz", 3), ["s38r_nz:", "or 1", "ret"])

    def test_the_slot_rule(self):
        """s38_covr (A = row; s38_covered: the pending row s38_rq) -> Z exactly when the build's copy will still
        bring the row's slot: its place (row - s38_r0) & 15 among the copy's VIEW_ROWS slots, with the copy not
        begun (s38_phase 0) or not yet past it (s38_i, the slots copied)."""
        self.assertEqual(block("scroll9938.asm", "s38_covered", 22),
                         ["s38_covered:", "ld a,(s38_rq)", "s38_covr:", "ld hl,s38_r0", "sub (hl)", "and 15",
                          "cp VIEW_ROWS", "jr nc,s38c_no", "ld b,a", "ld a,(s38_phase)", "or a", "jr z,s38c_yes",
                          "ld a,(s38_i)", "ld c,a", "ld a,b", "cp c", "jr c,s38c_no", "s38c_yes:", "xor a", "ret",
                          "s38c_no:", "or 1"])
        view = int(re.search(r"^VIEW_ROWS:\s*equ\s+(\d+)", (ROOT / "msx" / "msx.inc").read_text(), re.M).group(1))
        for row, r0, phase, i in itertools.product(range(0, 256, 3), range(0, 256, 5), (0, 1), range(view + 1)):
            a = ((row - r0) & 0xFF) & 15
            if a >= view:
                z = False
            elif phase == 0:
                z = True
            else:
                z = not a < i
            slots = [(r0 + k) & 15 for k in range(view)]
            want = (row & 15) in slots and (phase == 0 or slots.index(row & 15) >= i)
            self.assertEqual(z, want, (row, r0, phase, i))


if __name__ == "__main__":
    unittest.main()
