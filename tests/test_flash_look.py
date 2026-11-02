"""The hit flash's look, tools/mkrom.py FLASH_LOOK (performance campaign 2, docs/PERF2_PLAN.md D1: a comparison
for the user's choice, nothing decided): 0 the look as always (every build without the option), 6 at most one
white picture in 4 per enemy, 7 an enemy stays white while hit at most 2 pictures apart and turns normal 2
pictures after its last hit. The option's values, the places its code may take (msx/bob.asm, the frame end in
msx/rc2.asm, the slot's reset in msx/objects.asm), and the rule as the code's own constants make it: fl_pend's
byte per enemy slot, bit 0 a hit held from a skipped tick, bits 1-4 shifted right once a picture shown."""
from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import mkrom  # noqa: E402


def code(name):
    """msx/NAME's lines without comments, stripped."""
    return [l.split(";")[0].strip() for l in (ROOT / "msx" / name).read_text().splitlines()]


def block(lines, start, cond):
    """The lines of the if/else block that starts at the first 'if COND' at or after START: (then, else)."""
    i = lines.index(f"if {cond}", start)
    depth, part, out = 0, 0, ([], [])
    for l in lines[i + 1:]:
        if l.startswith("if "):
            depth += 1
        elif l == "endif":
            if depth == 0:
                return out
            depth -= 1
        elif l == "else" and depth == 0:
            part = 1
            continue
        out[part].append(l)
    raise AssertionError(f"no endif for 'if {cond}'")


def arming(look):
    """fl_due's code for LOOK: the bits a hit sets in the slot's byte, and the bits it tests."""
    bob = code("bob.asm")
    then, other = block(bob, bob.index("fl_due:"), "FLASH_LOOK = 7")
    body = then if look == 7 else other
    arm = 0
    for l in body:
        m = re.fullmatch(r"set (\d),\(hl\)", l)
        if m:
            arm |= 1 << int(m.group(1))
        m = re.fullmatch(r"or (0x[0-9A-Fa-f]+|\d+)", l)
        if m:
            arm |= int(m.group(1), 0)
    test = [int(m.group(1)) for l in body for m in [re.fullmatch(r"bit (\d),\(hl\)", l)] if m]
    return arm, test


def look_rule(look, hits, n):
    """The looks of one enemy slot over N pictures shown ('W' or 'N'), a hit shown in each picture of HITS,
    from the code: fl_due's arming and its decision bit, and rc2.asm's frame end."""
    bob = code("bob.asm")
    arm, test = arming(look)
    held = block(bob, bob.index("fl_held:"), "FLASH_LOOK = 7")[0 if look == 7 else 1]
    rc2 = code("rc2.asm")
    age = block(rc2, rc2.index("ml_tkd: ld hl,fl_pend"), "FLASH_LOOK")[0]
    assert age == ["ml_flc: srl (hl)", "res 0,(hl)"], age
    s, out = 0, []
    for p in range(n):
        if p in hits:
            if look == 7:
                s |= arm
                w = True
            else:
                w = not s >> test[0] & 1
                if w:
                    s |= arm
        else:
            # fl_held without a hit: 7 reads bit 1 (and 2, rrca: BM_FLASH), 6 shows the normal look
            w = look == 7 and held[:3] == ["ld a,(hl)", "and 2", "rrca"] and bool(s & 2)
        out.append("W" if w else "N")
        s = (s >> 1) & ~1                       # the frame end, once a picture shown
    return "".join(out)


class FlashLookTests(unittest.TestCase):

    def test_the_option(self):
        self.assertEqual(mkrom.OPTIONS["FLASH_LOOK"][0], 0)
        with tempfile.TemporaryDirectory() as t:
            out = str(Path(t) / "x.rom")
            for v in ("1", "5", "8"):
                self.assertEqual(mkrom.main(["mkrom.py", "build/msx/level1", out, f"FLASH_LOOK={v}"]), 2, v)

    def test_where_the_code_is(self):
        uses = []
        for f in sorted((ROOT / "msx").glob("*.asm")):
            for l in code(f.name):
                if "FLASH_LOOK" in l:
                    uses.append((f.name, l))
        self.assertEqual(uses, [("bob.asm", "if FLASH_LOOK"), ("bob.asm", "if FLASH_LOOK"),
                                ("bob.asm", "if FLASH_LOOK = 0"), ("bob.asm", "if FLASH_LOOK"),
                                ("bob.asm", "if FLASH_LOOK = 7"), ("bob.asm", "if FLASH_LOOK = 7"),
                                ("objects.asm", "if FLASH_LOOK"), ("rc2.asm", "if FLASH_LOOK")])
        # the logic's flash byte is read and cleared as always, never written by the look
        bob = code("bob.asm")
        self.assertEqual([l for l in bob if "OS_FLASH" in l],
                         ["ld a,(ix+OS_FLASH)", "ld a,(ix+OS_FLASH)", "ld (ix+OS_FLASH),0"])
        # the reset of a new object's look in slot_clear, after the slot's own fields
        obj = code("objects.asm")
        self.assertEqual(block(obj, obj.index("slot_clear:"), "FLASH_LOOK")[0], ["call fl_slot", "ld (hl),0"])

    def test_every_part_takes_one_look(self):
        # a hit arms bits 2 and up only: bit 1, this picture's, which every part of the enemy reads (6) or
        # shows (7), changes only at the frame end, so the parts drawn after the arming one look the same
        for look in (6, 7):
            arm, test = arming(look)
            self.assertTrue(arm and not arm & 3, (look, arm))
        self.assertEqual(arming(6)[1], [1])

    def test_look_7_stays_white_in_a_burst(self):
        self.assertEqual(look_rule(7, {0}, 4), "WWNN")
        self.assertEqual(look_rule(7, {0, 2, 4, 6}, 10), "WWWWWWWWNN")      # hits every 2 pictures: steady
        self.assertEqual(look_rule(7, {0, 1, 2}, 6), "WWWWNN")
        self.assertEqual(look_rule(7, {0, 3, 6}, 9), "WWNWWNWWN")           # 3 apart: it blinks

    def test_look_6_one_white_in_4(self):
        self.assertEqual(look_rule(6, {0, 2, 4, 6, 8}, 10), "WNNNWNNNWN")   # half the hits show no white
        self.assertEqual(look_rule(6, {0, 4, 8}, 9), "WNNNWNNNW")
        self.assertEqual(look_rule(6, set(range(10)), 10), "WNNNWNNNWN")
        self.assertEqual(look_rule(6, {0, 3, 5}, 6), "WNNNNW")
        for hits in ({0, 1, 2, 3}, {1, 2, 5, 6, 7}, set(range(0, 20, 3))):
            s = look_rule(6, hits, 20)
            self.assertTrue(all(s[i:i + 4].count("W") <= 1 for i in range(20)), (hits, s))


if __name__ == "__main__":
    unittest.main()
