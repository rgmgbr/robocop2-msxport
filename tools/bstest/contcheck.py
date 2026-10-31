#!/usr/bin/env python3
"""Checks level 2's continue (its step 19: front.asm front_over, front_cont, rc2.asm lv_cont;
docs/LEVEL2.md 3.7, 4.2 check 11, 4.4's game-over row) on hz.tcl hz_l2_cont_arm's records.

usage: contcheck.py DIR TAG (--fire | --again | --no-fire | --none) [--tag N] [--gen GEN_DIR]

--fire: the offer shown and taken (fire from its tick 60):
  - DIR/TAG_cont.sc5 (page 0's lines 0-161 once the offer's text is typed, fs_n 50) equals
    tools/msxtext.py's render of txt_cont (TEST N at row 10 first with --tag N), pixel for pixel;
  - R#0 16h and R#1 62h at that record (the line interrupt and the display on again after PIC9);
  - a HUD split at every VBLANK from the record to the screen's end (one more or fewer);
  - the screen ended by fire (fs_done 0, 50 ticks or more), then lv_cont with the credit used (AG
    $805E 0) and fo_cont set (its two lives come after its entry: the trace's row 109); no new game;
  - DIR/TAG_over_ram.bin (the CPU's 64 KiB at front_over's entry, before PIC9) and TAG_lvc_ram.bin
    (at lv_cont's entry) equal in the map patches (MP_ROW, MP_A, MP_B), the attribute RAM (ATR_RAM0,
    ATR_RAM1 with lv_cur's lv_atrn bytes, atr_lut), the level's lists (spawn_ram with its end word,
    objl_ram, SP_RAM, sp_ptrs), the vat state (vat_phase, vat_shown, vat_disp, vat_chg) and the tile
    cache (TC_SLOT, and TC_TILE and TC_REF over the level's slots: lv_cont resets it after its entry).
--again: as --fire (the RAM comparison too), then a second game over without a credit: no second
  offer, AG $805E 00FFh ($11FEE) at the new game (the title's, which a script build skips).
--no-fire: the offer shown and left alone: the same record checks, then its whole length (txt_cont's
  304 calls and the call that reads the end: 305 ticks, the original's VBLs), no continue, the credit
  used, a new game (the title, which a script build skips).
--none: no credit: no offer (no record), no continue, AG $805E's high byte cleared (00FFh, as $11FEE
  leaves it), a new game.
Exit 0 when every check passes. Reads build/ram/level1_full.bin and msx/msx.inc of the repository
this file is in (tools/bstest/); docs/HARNESS.md 5.22.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import msxtext  # noqa: E402
from bonuscheck import preview  # noqa: E402
from msxbright import grade_pal  # noqa: E402

CONT_CALLS = 304
# (name, msx.inc equate, size in bytes; None: lv_cur's lv_atrn word at F1A5h; "slots": the level's
#  tile slots (lv_tcn at F1BCh, negated) x the entry's bytes: the slots beyond them hold other modules'
#  RAM, msx.inc)
REGIONS = (
    ("the map patches", (("MP_ROW", 256), ("MP_A", 0x500), ("MP_B", 0x500))),
    ("the attribute RAM", (("ATR_RAM0", 48 * 80), ("ATR_RAM1", None), ("atr_lut", 16))),
    ("the level's lists", (("spawn_ram", 0x232), ("objl_ram", 0x210), ("SP_RAM", 0x100), ("sp_ptrs", 32))),
    ("the vat state", (("vat_phase", 46), ("vat_shown", 103), ("vat_disp", 103), ("vat_chg", 7))),
    ("the tile cache", (("TC_SLOT", 1024), ("TC_TILE", ("slots", 2)), ("TC_REF", ("slots", 1)))),
)


def equates() -> dict[str, int]:
    out = {}
    for line in (ROOT / "msx" / "msx.inc").read_text().splitlines():
        m = re.match(r"(\w+):\s+equ\s+0x([0-9A-Fa-f]+)", line)
        if m:
            out[m[1]] = int(m[2], 16)
    return out


def regions(before: bytes, after: bytes) -> int:
    eq = equates()
    atrn = before[0xF1A5] | before[0xF1A6] << 8
    slots = 0x10000 - (before[0xF1BC] | before[0xF1BD] << 8)
    bad = 0
    for what, parts in REGIONS:
        diffs = []
        for name, size in parts:
            a = eq[name]
            n = atrn if size is None else slots * size[1] if isinstance(size, tuple) else size
            d = [i for i in range(a, a + n) if before[i] != after[i]]
            if d:
                diffs.append(f"{name} {len(d)} bytes ({d[0]:04X}h-{d[-1]:04X}h)")
        names = ", ".join(n for n, _ in parts)
        if diffs:
            print(f"{what} ({names}): DIFFER before PIC9 and at lv_cont's entry: {'; '.join(diffs)}")
            bad = 1
        else:
            print(f"{what} ({names}): equal before PIC9 and at lv_cont's entry")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", type=Path)
    ap.add_argument("tag")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--fire", dest="mode", action="store_const", const="fire")
    g.add_argument("--again", dest="mode", action="store_const", const="again")
    g.add_argument("--no-fire", dest="mode", action="store_const", const="nofire")
    g.add_argument("--none", dest="mode", action="store_const", const="none")
    ap.add_argument("--tag", dest="ntag", type=int, default=0, help="the build's TAG")
    ap.add_argument("--gen", type=Path, help="the build's gen folder (hud_grade.pal) for the preview")
    a = ap.parse_args()
    notes = (a.dir / f"{a.tag}_cont.txt").read_text()
    print(notes.rstrip())
    bad = 0
    lvc = re.search(r"^lv_cont at .*AG 8034h (\d+), 805Eh ([0-9A-F]+), 8050h \d+, fo_cont (\d+)", notes, re.M)
    ng = re.search(r"^new game at .*805Eh ([0-9A-F]+)", notes, re.M)
    if a.mode == "none":
        if (a.dir / f"{a.tag}_cont.sc5").exists() or re.search(r"^cont at ", notes, re.M):
            print("an offer without a credit")
            bad = 1
        if lvc or not ng:
            print("not a new game after the game over")
            bad = 1
        elif ng[1] != "00FF":
            print(f"AG $805E {ng[1]}h at the new game's start, 00FFh expected ($11FEE)")
            bad = 1
        print("cont check:", "PASS" if not bad else "FAIL")
        return bad
    ram = (ROOT / "build" / "ram" / "level1_full.bin").read_bytes()
    glyphs = [msxtext.glyph_sc5(ram, g) for g in range(44)]
    script = {lb: sc for lb, _, sc in msxtext.cont_scripts(ram)}["txt_cont"]
    ref = msxtext.fs_render(glyphs, msxtext.tag_line(a.ntag) + script)
    f = a.dir / f"{a.tag}_cont.sc5"
    if not f.exists():
        print(f"no record {f.name}")
        return 1
    got = f.read_bytes()
    diff = [i for i in range(len(ref)) if ref[i] != got[i]]
    tg = f", TEST {a.ntag}" if a.ntag else ""
    if diff:
        ys = sorted({i // 128 for i in diff})
        print(f"cont (txt_cont{tg}): {len(diff)} bytes DIFFER, lines {ys[0]}-{ys[-1]}")
        bad = 1
    else:
        print(f"cont (txt_cont{tg}): equal to the render, pixel for pixel")
    regs = (a.dir / f"{a.tag}_cont_regs.bin").read_bytes()
    if regs[0] != 0x16 or regs[1] != 0x62:
        print(f"cont: R#0 {regs[0]:02X}h R#1 {regs[1]:02X}h (the line interrupt and the display not both on)")
        bad = 1
    else:
        print("cont: R#0 16h R#1 62h (the line interrupt and the display on)")
    m = re.search(r"^cont end at .*fs_n (\d+), fs_done (\d+); from the record: (\d+) VBLANKs, (\d+) HUD splits",
                  notes, re.M)
    if not m:
        print("the screen's end not noted")
        return 1
    n, done, vbl, spl = (int(v) for v in m.groups())
    if abs(vbl - spl) > 1 or vbl < 10:
        print(f"cont: {vbl} VBLANKs, {spl} HUD splits (the split not at every VBLANK)")
        bad = 1
    else:
        print(f"cont: {vbl} VBLANKs, {spl} HUD splits from the record to its end")
    if a.mode in ("fire", "again"):
        if done or not 50 <= n <= CONT_CALLS:
            print(f"cont: fs_n {n}, fs_done {done}: not ended by fire")
            bad = 1
        else:
            print(f"cont: ended by fire at its tick {n}")
        if a.mode == "again":
            if not ng or ng[1] != "00FF" or len(re.findall(r"^cont at ", notes, re.M)) != 1:
                print("no second game over without a credit and without an offer, then a new game "
                      f"(AG $805E {ng[1] if ng else '-'}h, 00FFh expected)")
                bad = 1
            else:
                print("the second game over: no offer, AG $805E 00FFh, the title's new game")
        elif ng:
            print("a new game after the continue")
            bad = 1
        if not lvc:
            print("no continue (lv_cont) after the offer's fire")
            bad = 1
        elif (lvc[2], lvc[3]) != ("0000", "1"):
            print(f"lv_cont with $805E {lvc[2]}h, fo_cont {lvc[3]}: 0000h and 1 expected")
            bad = 1
        else:
            print(f"lv_cont: the credit used ($805E 0000h), fo_cont 1 (the lives at its entry {lvc[1]}: "
                  "lv_cfront sets 2; the trace's row 109 has them)")
        before, after = (a.dir / f"{a.tag}_over_ram.bin").read_bytes(), (a.dir / f"{a.tag}_lvc_ram.bin").read_bytes()
        bad |= regions(before, after)
    else:
        if not done or n != CONT_CALLS + 1:
            print(f"cont: fs_n {n}, fs_done {done}: its whole length ({CONT_CALLS + 1} ticks) expected")
            bad = 1
        else:
            print(f"cont: {n} ticks, its whole length ({CONT_CALLS} calls)")
        if lvc or not ng:
            print("a continue without fire, or no new game")
            bad = 1
        elif ng[1] != "0000":
            print(f"AG $805E {ng[1]}h at the new game, 0000h expected (the credit used)")
            bad = 1
    if a.gen:
        hud_pal = (a.gen / "hud_grade.pal").read_bytes()
        preview(a.dir / f"{a.tag}_cont.png", got, (a.dir / f"{a.tag}_cont_hud.bin").read_bytes(),
                grade_pal(msxtext.msx_palette(ram)), hud_pal)
    print("cont check:", "PASS" if not bad else "FAIL")
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
