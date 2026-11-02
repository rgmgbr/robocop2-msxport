"""The hit flash's look, tools/mkrom.py FLASH_LOOK (performance campaign 2, docs/PERF2_PLAN.md D1: a comparison
for the user's choice, nothing decided): 0 the look as always (every build without the option), 6 at most one
white picture in 4 per enemy, 7 an enemy white in the game tick of a hit and the 3 ticks after it, every hit
starting the 4 ticks again. The option's values, the places its code may take (msx/bob.asm, the frame end in
msx/rc2.asm, the slot's reset in msx/objects.asm), and the rules as the code's own constants make them:
fl_pend's byte per enemy slot; 6: bit 0 a hit held from a skipped tick, bits 1-4 shifted right once a picture
shown (rc2.asm's frame end); 7: bits 0-3 the white ticks to come, shifted right at every game tick's start
(bob.asm bob_begin)."""
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


def routine(lines, label):
    """A block's lines from LABEL's line up to (not including) the next label or the block's end."""
    i = next(k for k, l in enumerate(lines) if l.startswith(label + ":"))
    out = [lines[i][len(label) + 1:].strip()] if lines[i][len(label) + 1:].strip() else []
    for l in lines[i + 1:]:
        if re.match(r"^\w+:", l):
            break
        if l:
            out.append(l)
    return out


def arming6():
    """FLASH_LOOK 6's fl_due: the bits a hit sets in the slot's byte, and the bits it tests."""
    six = block(code("bob.asm"), 0, "FLASH_LOOK = 6")[0]
    body = routine(six, "fl_due")
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


def look6(hits, n):
    """The looks of one enemy slot over N pictures shown ('W' or 'N') with FLASH_LOOK 6, a hit shown in each
    picture of HITS, from the code: fl_due's arming and its decision bit, and rc2.asm's frame end."""
    arm, test = arming6()
    rc2 = code("rc2.asm")
    loop = block(rc2, rc2.index("ml_tkd:"), "FLASH_LOOK != 7")[0]
    age = block(loop, 0, "FLASH_LOOK")[0]
    assert age == ["ml_flc: srl (hl)", "res 0,(hl)"], age
    s, out = 0, []
    for p in range(n):
        w = p in hits and not s >> test[0] & 1
        if w:
            s |= arm
        out.append("W" if w else "N")
        s = (s >> 1) & ~1                       # the frame end, once a picture shown
    return "".join(out)


def seven():
    """FLASH_LOOK 7's code: the byte fl_note stores, fl_held's mask, and bob_begin's aging of the 5 slots."""
    bob = code("bob.asm")
    blk = block(bob, bob.index("fl_slot:"), "FLASH_LOOK = 7")[0]
    note, held = routine(blk, "fl_note"), routine(blk, "fl_held")
    assert note[0] == "call fl_slot" and note[2:] == ["ld a,BM_FLASH", "ret"], note
    store = int(re.fullmatch(r"ld \(hl\),(0x[0-9A-Fa-f]+|\d+)", note[1]).group(1), 0)
    assert held[:2] == ["call fl_slot", "ld a,(hl)"] and held[3:] == ["ret"], held
    mask = int(re.fullmatch(r"and (0x[0-9A-Fa-f]+|\d+)", held[2]).group(1), 0)
    age = block(bob, bob.index("bob_begin:"), "FLASH_LOOK = 7")[0]
    assert age == ["ld hl,fl_pend", "ld b,5", "bbg_f:  srl (hl)", "inc hl", "djnz bbg_f"], age
    return store, mask


def look7(hits, n):
    """The looks of one enemy slot over N game ticks ('W' or 'N') with FLASH_LOOK 7, a hit in each tick of
    HITS, from the code: bob_begin's shift at the tick's start, fl_note's store, fl_held's mask (BM_FLASH 1)."""
    store, mask = seven()
    s, out = 0, []
    for t in range(n):
        s >>= 1                                 # bob_begin, at the tick's start
        if t in hits:
            s = store
        out.append("W" if (s & mask) == 1 else "N")
    return "".join(out)


def shown7(hits, frames):
    """FLASH_LOOK 7's looks on the pictures: FRAMES = the ticks run for each picture (the display shows
    the last one's BOBs: bob_skip)."""
    ticks = look7(hits, sum(frames))
    out, t = [], 0
    for k in frames:
        t += k
        out.append(ticks[t - 1])
    return "".join(out)


class FlashLookTests(unittest.TestCase):

    def test_the_option(self):
        self.assertEqual(mkrom.OPTIONS["FLASH_LOOK"][0], 0)
        with tempfile.TemporaryDirectory() as t:
            out = str(Path(t) / "x.rom")
            for v in ("1", "5", "8"):
                self.assertEqual(mkrom.main(["mkrom.py", "build/msx/level1", out, f"FLASH_LOOK={v}"]), 2, v)
            # 7's 4 white ticks must reach the tick shown: at most 4 ticks a picture
            for o in ("CAD_MAX=5", "CAD_HOLD=5"):
                self.assertEqual(mkrom.main(["mkrom.py", "build/msx/level1", out, "FLASH_LOOK=7", o]), 2, o)

    def test_where_the_code_is(self):
        uses = []
        for f in sorted((ROOT / "msx").glob("*.asm")):
            for l in code(f.name):
                if "FLASH_LOOK" in l:
                    uses.append((f.name, l))
        self.assertEqual(uses, [("bob.asm", "if FLASH_LOOK = 7"), ("bob.asm", "if FLASH_LOOK"),
                                ("bob.asm", "if FLASH_LOOK"), ("bob.asm", "if FLASH_LOOK = 0"),
                                ("bob.asm", "if FLASH_LOOK = 7"), ("bob.asm", "if FLASH_LOOK = 6"),
                                ("bob.asm", "if FLASH_LOOK = 0"), ("objects.asm", "if FLASH_LOOK"),
                                ("rc2.asm", "if FLASH_LOOK != 7"), ("rc2.asm", "if FLASH_LOOK")])
        # the logic's flash byte is read and cleared as always, never written by the look
        bob = code("bob.asm")
        self.assertEqual([l for l in bob if "OS_FLASH" in l],
                         ["ld a,(ix+OS_FLASH)", "ld a,(ix+OS_FLASH)", "ld (ix+OS_FLASH),0"])
        # the reset of a new object's look in slot_clear, after the slot's own fields
        obj = code("objects.asm")
        self.assertEqual(block(obj, obj.index("slot_clear:"), "FLASH_LOOK")[0], ["call fl_slot", "ld (hl),0"])

    def test_7_counts_game_ticks(self):
        # bob_begin, which ages 7's look, runs once at every game tick's start: its one caller is
        # player.asm's gt_go (game_tick after the pause); rc2.asm's frame end has no fl_pend loop for 7
        calls = [(f.name, k) for f in sorted((ROOT / "msx").glob("*.asm"))
                 for k, l in enumerate(code(f.name)) if re.search(r"\bbob_begin\b", l) and not l.startswith("bob_begin:")]
        self.assertEqual([c[0] for c in calls], ["player.asm"])
        pl = code("player.asm")
        self.assertEqual(pl[calls[0][1]], "gt_go:  call bob_begin")
        rc2 = code("rc2.asm")
        i = rc2.index("ml_tkd:")
        self.assertEqual(rc2[i + 1], "if FLASH_LOOK != 7")
        self.assertEqual([l for l in rc2 if "fl_pend" in l], ["ld hl,fl_pend"])
        self.assertIn("ld hl,fl_pend", block(rc2, i, "FLASH_LOOK != 7")[0])
        # no held hit and no skipped-tick test in 7's code: a hit in a skipped tick is inside its hold
        blk = block(code("bob.asm"), code("bob.asm").index("fl_slot:"), "FLASH_LOOK = 7")[0]
        self.assertFalse([l for l in blk if "bob_skip" in l or "bit " in l or "set " in l], blk)

    def test_every_part_takes_one_look(self):
        # 6: a hit arms bits 2 and up only: bit 1, this picture's, which every part of the enemy reads,
        # changes only at the frame end. 7: a hit sets bit 0, this tick's, at once: the parts drawn after
        # the noting one (fl_held, OS_FLASH already cleared by bob_part2) are white too
        arm, test = arming6()
        self.assertTrue(arm and not arm & 3, arm)
        self.assertEqual(test, [1])
        store, mask = seven()
        self.assertTrue(store & mask & 1)

    def test_look_7_a_hit_is_white_4_ticks(self):
        self.assertEqual(look7({0}, 6), "WWWWNN")
        self.assertEqual(look7({2}, 8), "NNWWWWNN")
        self.assertEqual(look7({0, 2}, 8), "WWWWWWNN")                      # a hit starts its 4 ticks again
        self.assertEqual(look7({0, 4, 8}, 14), "W" * 12 + "NN")             # hits every 4 ticks: steady
        self.assertEqual(look7({0, 5, 10}, 15), "WWWWNWWWWNWWWWN")          # 5 apart: one normal tick between

    def test_look_7_on_the_pictures(self):
        # 2 ticks a picture (the Z80 machines with Cain): a hit shows 2 white pictures, hits every 4 ticks
        # a steady white; 1 tick a picture (the turbo R often): 4; a hit is never lost in a skipped tick
        self.assertEqual(shown7({0}, [2] * 4), "WWNN")
        self.assertEqual(shown7({1}, [2] * 4), "WWNN")
        self.assertEqual(shown7({0}, [1] * 6), "WWWWNN")
        self.assertEqual(shown7(set(range(0, 40, 4)), [2] * 20), "W" * 20)
        self.assertEqual(shown7(set(range(0, 30, 4)), [2] * 20), "W" * 16 + "N" * 4)
        self.assertEqual(shown7(set(range(0, 40, 4)), [1, 2, 1, 1, 2, 2, 1, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2]),
                         "W" * 20)
        for k in (1, 2, 3, 4):
            for t in range(k):
                self.assertEqual(shown7({k + t}, [k] * 3)[1], "W", (k, t))  # the hit's own picture
        self.assertEqual(shown7({5}, [5] * 3), "NNN")                        # (5 a picture: mkrom refuses)

    def test_look_6_one_white_in_4(self):
        self.assertEqual(look6({0, 2, 4, 6, 8}, 10), "WNNNWNNNWN")   # half the hits show no white
        self.assertEqual(look6({0, 4, 8}, 9), "WNNNWNNNW")
        self.assertEqual(look6(set(range(10)), 10), "WNNNWNNNWN")
        self.assertEqual(look6({0, 3, 5}, 6), "WNNNNW")
        for hits in ({0, 1, 2, 3}, {1, 2, 5, 6, 7}, set(range(0, 20, 3))):
            s = look6(hits, 20)
            self.assertTrue(all(s[i:i + 4].count("W") <= 1 for i in range(20)), (hits, s))


if __name__ == "__main__":
    unittest.main()
