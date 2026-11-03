"""Performance campaign 2's scroll-1 on the V9958 (docs/PERF2_PLAN.md item 6): msx/scroll9958.asm scroll_work draws
its column and row queues' tiles in a row while msx/tiles.asm sc_stop allows (sw_next), each tile set up while the one
before is copied. The loops as built, the stop rule's decision on every state it reads (in VAT_ANIM=0 and VAT_ANIM=1 builds;
the changed cells' window first between the HUD split and the VBLANK),
fb_pend's exits (the carry sc_stop returns), every tile of a burst waiting for the one before, and the stop rule taken by
the V9958's engine alone (msx/scroll9938.asm never calls it). Stdlib only."""
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


STOP = ["ld a,(split_armed)", "or a", "call z,sw_redraw",                      # the window: the changed cells first,
        "if VAT_ANIM", "ld a,(vat_fr + VF_RDY)", "or a", "scf", "ret nz", "endif",   # a vat column waits (VAT_ANIM=1),
        "ld a,(fb_cq)", "rra", "ret c",                                               # a copy waits for the blank,
        "call fb_pend", "ret z", "scf", "ret"]                                        # work of a published picture


def stop(lines: list[str], ram: dict[str, int], pend: bool, vat_anim: bool) -> tuple[bool, bool]:
    """sc_stop as the Z80 runs it in a build with VAT_ANIM 0 or 1 -> (the carry it returns: True when the burst stops,
    whether the changed cells' window ran). fb_pend: NZ when pend, its carry clear (FbPendTests); sw_redraw: its flags
    unknown."""
    c = z = None
    a = 0
    skip = False
    window = False
    for ins in lines:
        if ins == "if VAT_ANIM":
            skip = not vat_anim
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
        elif ins == "call z,sw_redraw":
            if z is None:
                raise AssertionError("call z on an unknown zero flag")
            if z:
                window = True
                c = z = None
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
                if c is None:
                    raise AssertionError("a return with an unknown carry")
                return c, window
        elif ins == "ret":
            return c, window
        else:
            raise AssertionError(ins)
    raise AssertionError("no return")


class BurstTests(unittest.TestCase):
    def test_the_v9958_bursts(self):
        """Each queued tile drawn through draw_kept, then sw_next: the queues' next tile while sc_stop allows (the
        column first, then the row), with both empty the idle work (sw_idle)."""
        self.assertEqual(code("scroll9958.asm", "sw_next", "sw_row"), ["call sc_stop", "jr nc,sw_cq", "ret"])
        self.assertEqual(code("scroll9958.asm", "sw_cq", "sw_next")[-2:], ["pop af", "call draw_kept"])
        rows = code("scroll9958.asm", "sw_row", "sw_idle")
        self.assertEqual(rows[:3], ["ld a,(q_row)", "cp 0xFF", "jr z,sw_idle"])
        self.assertEqual(rows[-2:], ["call draw_kept", "jr sw_next"])
        work = code("scroll9958.asm", "scroll_work", "sw_idle")
        self.assertEqual(work[:2], ["call vdp_busy", "ret nz"])
        self.assertEqual(work.count("call sc_stop"), 1)
        self.assertEqual(work[work.index("call vat_win") + 1:work.index("call vat_win") + 3],
                         ["ret nz", "ld a,(q_col)"])                  # (the vats' window before the queues)

    def test_only_the_v9958_engine_takes_its_stop_rule(self):
        """sc_stop is the V9958 engine's rule: between the HUD split and the VBLANK it draws the ring's changed
        cells (scroll9958.asm sw_redraw), so only scroll9958.asm's sw_next calls it, never the V9938's engine
        (msx/scroll9938.asm: its own work and its own column burst, the V9938's part of the same item, which
        this test leaves to that engine's tests; until 2026-11-02 it asserted the V9938's one command a call,
        which that part changes)."""
        self.assertNotIn("sc_stop", (ROOT / "msx" / "scroll9938.asm").read_text())
        call = re.compile(r"(?m)^[^;]*\b(call|jp|jr)\b[^;]*\bsc_stop\b")
        callers = sorted(p.name for p in (ROOT / "msx").glob("*.asm") if call.search(p.read_text()))
        self.assertEqual(callers, ["scroll9958.asm"])
        self.assertEqual(len(call.findall((ROOT / "msx" / "scroll9958.asm").read_text())), 1)

    def test_the_stop_rule(self):
        """Between the HUD split and the VBLANK (split_armed 0) the changed cells' window first (sw_redraw), whatever
        it then decides. C (stop) when a copy of the play-field BOBs waits for the blank (fb_cq 1 or 3) or they have
        work of a published picture (fb_pend NZ); in VAT_ANIM=1 builds also while a vat column waits for the blank
        (vat_fr's VF_RDY, which vat_win draws at the engine's next call). NC: the next tile follows."""
        self.assertEqual(code("tiles.asm", "sc_stop", "fb_pend"), STOP)
        self.assertNotIn("sc_stop:", (ROOT / "msx" / "scroll9958.asm").read_text())
        for vat_anim, armed, rdy, cq, pend in itertools.product((False, True), (0, 1), (0, 1), range(5), (False, True)):
            ram = {"split_armed": armed, "fb_cq": cq, "vat_fr + VF_RDY": rdy}
            want = bool(cq & 1) or pend or (vat_anim and rdy != 0)
            self.assertEqual(stop(STOP, ram, pend, vat_anim), (want, armed == 0), (vat_anim, armed, rdy, cq, pend))
        red = code("scroll9958.asm", "sw_redraw", "swr_one")
        self.assertEqual(red[:6], ["ld b,RD_BURST", "ld a,(split_armed)", "or a", "jr z,swr_lp", "ld b,1",
                                   "push bc"])                       # (up to RD_BURST cells in the window, one
                                                                     #  a call in the blank after the VBLANK)
        work = code("scroll9958.asm", "scroll_work", "sw_idle")
        self.assertEqual(work[2:5], ["ld a,(split_armed)", "or a", "jr nz,sw_vb"])
        self.assertEqual(work[5], "call sw_redraw")                  # (the same window at scroll_work's start)

    def test_the_vat_flag(self):
        """VF_RDY is vat_fr's ready flag (field.asm), set by vats.asm vat_prep and cleared by vat_run; vat_win
        reads the same byte."""
        field = (ROOT / "msx" / "field.asm").read_text()
        self.assertRegex(field, r"(?m)^VF_RDY:\s+equ\s+28\b")
        tiles = (ROOT / "msx" / "tiles.asm").read_text()
        self.assertIn("ld a,(vat_fr + VF_RDY)", tiles)


class FbPendTests(unittest.TestCase):
    def test_every_exit_clears_the_carry(self):
        """sc_stop returns fb_pend's carry on its Z exits: every return of fb_pend (and of fpd_it, whose NZ it
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
        """A burst's tiles go through draw_tile, which waits for the VDP (vdp_wait, and vdp_cmd again) after the
        tile's set-up: the set-up runs while the tile before is copied."""
        self.assertEqual(code("scroll9958.asm", "draw_tile", "dt_count"),
                         ["call dt_prep", "ret nc", "call vdp_wait", "ld hl,cmdbuf", "call vdp_cmd"])
        self.assertIn("call vdp_wait", code("vdp.asm", "vdp_cmd", "vdp_cmd_q"))


if __name__ == "__main__":
    unittest.main()
