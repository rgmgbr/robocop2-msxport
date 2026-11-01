#!/usr/bin/env python3
"""Checks an ending.tcl ge_job record (docs/ENDING.md: the game completed and the high scores) against
tools/msxtext.py's renders of the port's scripts and a model of the original's name entry and table.

usage: endcheck.py DIR TAG KEYS [--tag N] [--score S] [--over [--no-offer]] [--gen GEN_DIR]

KEYS: the keys ge_job typed (one argument, names separated by spaces: A-Z, 0-9, KP0-KP9, SPACE, BS,
RET). S: the score the build carries (LV_CARRY's, decimal; default 10050).
- DIR/TAG_end.sc5 (END_TEST=1: the WELL DONE screen at fs_n 200) equals the render of txt_end (with
  TEST N at row 10 first: --tag N), pixel for pixel;
- DIR/TAG_hsK.sc5, each wait K of the name entry: the render of txt_hisc with the name as the model
  of $1215C holds it after K keys (the mark under the second position at the start; a character at
  the next position, the mark after it but after the last; Backspace takes the last back, the mark
  there; the name full: keys ignored, the field as it was);
- DIR/TAG_best.sc5: the render of the table screen (txt_best's TODAYS BEST and the entries) with the
  model's table: the defaults with S's low 7 digits entered under the last entry they beat ($120C4:
  greater only; $1211C: ties keep the older above), its name the model's after Return (the marks
  cleared);
- at every record R#0 16h and R#1 62h (the line interrupt and the display on) and the palette's
  colours 1-15 txt_pal's (graded);
- the notes (DIR/TAG_end.txt): END_TEST=1: the tune from tn_cmp to tn_left 0 in 4,917 ticks of
  tn_tick (T + 1: its end's tick; one more at most, the poll's), about 98.3 emulated s; the end at
  the title; --over (END_TEST=2): front_over noted and no WELL DONE, the offer's record (cont.sc5)
  equal to the render of txt_cont, the end at lv_cont (--no-offer, no credit: no offer, the end at
  the title); both: the table in RAM at the end equal to the model's (hs_tab0, hs_tab1: per entry the
  name and the score's 4 BCD bytes). A score that does not enter the table: no entry's record and
  KEYS "-" (nothing typed), the table the defaults.
Writes DIR/TAG_*.png previews (play area 2x over the HUD, as bonuscheck.py) for the eye (--gen: the
build's gen folder for the HUD's palette). Exit 0 when every check passed.
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

KEYCHAR = {**{c: ord(c) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}, **{str(d): 0x5B + d for d in range(10)},
           **{f"KP{d}": 0x5B + d for d in range(10)}, "SPACE": 0x20, "BS": 0x7F, "RET": 0x0D}


def entry_model(keys: list[str]) -> tuple[list[bytes], bytes]:
    """$1215C on these keys: the name field at each wait (the first after its first drawing, then one a
    key until Return) and the name after Return (the marks cleared)."""
    name = bytearray(b" " * 9)
    name[1] = msxtext.HS_MARK
    i = 0
    waits = [bytes(name)]
    for k in keys:
        c = KEYCHAR[k]
        if c == 0x0D:
            if i != 9:
                name[i] = 0x20
                if i != 8:
                    name[i + 1] = 0x20
            return waits, bytes(name)
        if c == 0x7F:
            if i:
                name[i - 1] = msxtext.HS_MARK
                if i != 9:
                    name[i] = 0x20
                i -= 1
        elif i != 9:
            name[i] = c
            if i != 8:
                name[i + 1] = msxtext.HS_MARK
            i += 1
        waits.append(bytes(name))
    raise SystemExit("the keys end without Return")


def table_model(table: list[tuple[bytes, int]], name: bytes, score: int) -> list[tuple[bytes, int]]:
    """high_score_entry's table after a score: its low 7 digits against the last entry; greater, the
    last entry is (name, those digits), moved up past every lower score."""
    s = score % 10 ** 7
    t = list(table)
    if s <= t[-1][1]:
        return t
    t[-1] = (name, s)
    k = len(t) - 1
    while k and t[k - 1][1] < t[k][1]:
        t[k - 1], t[k] = t[k], t[k - 1]
        k -= 1
    return t


def ram_table(line: str) -> list[tuple[bytes, int]]:
    """ge_table's hex entries -> (name, score)."""
    out = []
    for h in line.split():
        b = bytes.fromhex(h)
        out.append((b[:9], int(b[9:].hex())))
    return out


def compare(d: Path, tag: str, name: str, ref: bytes, txt_pal: bytes, what: str) -> int:
    f = d / f"{tag}_{name}.sc5"
    if not f.exists():
        print(f"{what}: no record {f.name}")
        return 1
    got = f.read_bytes()
    bad = 0
    diff = [i for i in range(len(ref)) if ref[i] != got[i]]
    if diff:
        ys = sorted({i // 128 for i in diff})
        print(f"{what}: {len(diff)} bytes DIFFER, lines {ys[0]}-{ys[-1]}")
        bad = 1
    else:
        print(f"{what}: equal to the render, pixel for pixel")
    regs = (d / f"{tag}_{name}_regs.bin").read_bytes()
    pal = (d / f"{tag}_{name}_pal.bin").read_bytes()
    if regs[0] != 0x16 or regs[1] != 0x62:
        print(f"{what}: R#0 {regs[0]:02X}h R#1 {regs[1]:02X}h (the line interrupt and the display not both on)")
        bad = 1
    if pal[2:32] != txt_pal[2:32]:
        print(f"{what}: the palette's colours 1-15 are not txt_pal's")
        bad = 1
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dir", type=Path)
    ap.add_argument("tag")
    ap.add_argument("keys")
    ap.add_argument("--tag", dest="ntag", type=int, default=0, help="the build's TAG")
    ap.add_argument("--score", type=int, default=10050, help="the score the build carries (LV_CARRY's)")
    ap.add_argument("--over", action="store_true", help="END_TEST=2: the game over's way")
    ap.add_argument("--no-offer", action="store_true", help="with --over: no credit, the title after the entry")
    ap.add_argument("--gen", type=Path, help="the build's gen folder (hud_grade.pal) for the previews")
    a = ap.parse_args()
    ram = (ROOT / "build/ram/level1_full.bin").read_bytes()
    glyphs = [msxtext.glyph_sc5(ram, g) for g in range(msxtext.rc2front.BITMAP_GLYPHS)]
    txt_pal = grade_pal(msxtext.msx_palette(ram))
    tl = msxtext.tag_line(a.ntag)
    keys = [] if a.keys == "-" else a.keys.split()
    notes = (a.dir / f"{a.tag}_end.txt").read_text()
    bad = 0
    tg = f", TEST {a.ntag}" if a.ntag else ""
    end = msxtext.brief_scripts(ram, msxtext.END)[0][2]
    hisc = msxtext.hisc_scripts(ram)[0][2]
    head, table = msxtext.hs_defaults(ram)
    enters = a.score % 10 ** 7 > table[-1][1]
    waits, final = entry_model(keys) if enters else ([], b"")
    want = table_model(table, final, a.score)
    shots = ["end"] if not a.over else []
    if not a.over:
        bad |= compare(a.dir, a.tag, "end", msxtext.fs_render(glyphs, tl + end), txt_pal, f"the WELL DONE screen{tg}")
        m1 = re.search(r"^\s*([\d.]+) tn_cmp through mus_call:", notes, re.M)
        m2 = re.search(r"^\s*([\d.]+) the tune over \(tn_left 0\): .*ticks counted (\d+)", notes, re.M)
        T = msxtext_end_ticks()
        if not (m1 and m2):
            print("the tune: its start or its end not noted")
            bad = 1
        else:
            n, secs = int(m2[2]), float(m2[1]) - float(m1[1])
            ok = n in (T + 1, T + 2)
            print(f"the tune: {n} ticks of tn_tick to tn_left 0 in {secs:.1f} emulated s (T + 1 = {T + 1}): "
                  + ("PASS" if ok else "FAIL"))
            bad |= not ok
        if not re.search(r"end: the title \(fr_title\)", notes):
            print("the end: not at the title")
            bad = 1
    else:
        if not re.search(r"front_over \(PIC9\)", notes) or re.search(r"front_ending:", notes):
            print("the game over: front_over not noted, or the ending shown")
            bad = 1
        if a.no_offer:
            if (a.dir / f"{a.tag}_cont.sc5").exists() or not re.search(r"end: the title \(fr_title\)", notes):
                print("no credit: an offer recorded, or the end not at the title")
                bad = 1
        else:
            script = msxtext.cont_scripts(ram)[0][2]
            bad |= compare(a.dir, a.tag, "cont", msxtext.fs_render(glyphs, tl + script), txt_pal,
                           f"the continue offer{tg}")
            shots.append("cont")
            if not re.search(r"end: lv_cont", notes):
                print("the end: not at lv_cont")
                bad = 1
    for k, field in enumerate(waits):
        what = f"the name entry, wait {k} ({msxtext.decode(field)!r}{tg})"
        bad |= compare(a.dir, a.tag, f"hs{k}", msxtext.hisc_area(glyphs, tl + hisc, field), txt_pal, what)
        shots.append(f"hs{k}")
    if (a.dir / f"{a.tag}_hs{len(waits)}.sc5").exists():
        print(f"the name entry: a record after Return (hs{len(waits)})")
        bad = 1
    if enters:
        ref = msxtext.fs_render(glyphs, tl + msxtext.best_text(head, want) + msxtext.best_script())
        bad |= compare(a.dir, a.tag, "best", ref, txt_pal, f"the table screen{tg}: "
                       + ", ".join(f"{msxtext.decode(n).rstrip() or '(blank)'} {s}" for n, s in want))
        shots.append("best")
    else:
        ok = not (a.dir / f"{a.tag}_best.sc5").exists() and "hs_best" not in notes
        print(f"the score {a.score} does not enter the table: no entry, no table screen: " + ("PASS" if ok else "FAIL"))
        bad |= not ok
    m = re.search(r"^\s*[\d.]+ table: (.*)$", notes, re.M)
    if not m:
        print("the table in RAM: not noted")
        bad = 1
    else:
        got = ram_table(m[1])
        ok = got == want
        print("the table in RAM at the end: " + ("equal to the model's" if ok else f"DIFFERS: {got}"))
        bad |= not ok
    if a.gen:
        hud_pal = (a.gen / "hud_grade.pal").read_bytes()
        for s in shots:
            f = a.dir / f"{a.tag}_{s}.sc5"
            if f.exists():
                preview(a.dir / f"{a.tag}_{s}.png", f.read_bytes(), (a.dir / f"{a.tag}_{s}_hud.bin").read_bytes(),
                        txt_pal, hud_pal)
    print(f"endcheck {a.tag}: " + ("PASS" if not bad else "FAIL"))
    return 1 if bad else 0


def msxtext_end_ticks() -> int:
    """The ending's tune's ticks (end.bin's T: tools/msxtune.py end_ticks, 4,916)."""
    blob = (ROOT / "build/msx/end.bin").read_bytes()
    return blob[43] | blob[44] << 8


if __name__ == "__main__":
    raise SystemExit(main())
