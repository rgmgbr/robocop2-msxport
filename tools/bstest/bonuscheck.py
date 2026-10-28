#!/usr/bin/env python3
"""Checks a hz.tcl hz_bonus record: the bonus text screens against renders of the port's scripts.

usage: bonuscheck.py DIR TAG [--tag N] [--result time|ok|fail] [--gen GEN_DIR] [--range time|C,D,M]
                     [--no-game]

DIR/TAG_intro.sc5 and DIR/TAG_result.sc5 (page 0's lines 0-161 as the emulator held them) must
equal tools/msxtext.py fs_render of txt_bs_intro and of the result's script (txt_bs_time by
default), pixel for pixel; with --tag N the renders get "TEST N" at row 10 first, as front.asm
fe_text draws it (column 15, 14 for two digits). The TAG = 0 renders must equal step 3's
build/msx/text_bs_*.sc5. Also: DIR/TAG_bonus.txt's notes (the result shown, the HUD splits per
VBLANK between the records, the title, the new game) are printed and checked: the result named,
every VBLANK with its split (one more or fewer at most: the window
starts and ends mid-frame), R#0 with the line interrupt and R#1 with the
display on at both records. Writes DIR/TAG_intro.png and DIR/TAG_result.png: the play area
(txt_pal through the grade) over 5 blank lines and the HUD (DIR/TAG_*_hud.bin in GEN_DIR's
hud_grade.pal), 2x. With --range (a build with the shooting range, which follows Brainstorm's result):
the range's screens recorded in the same flow (DIR/TAG_rgintro.sc5, _rgres.sc5, TAG_rg.txt: rgflow.tcl
rgh_arm, rgk_job) checked by rgcheck.py: its intro, OUT OF TIME. ("time") or the result for C correct,
D dummy and M minutes, the HUD split, the result at fr_done, the rating at fr_rated, SHARP at the new
game (noted in TAG_rg.txt). --no-game: Brainstorm's notes have no new game (the keyboard flow ends at
the title's own game, which the range's notes give).
Exit 0 when every check passed.

Reads build/ram/level1_full.bin and build/msx/text_bs_*.sc5 of the repository this file is in
(tools/bstest/); docs/HARNESS.md.
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
import rgcheck  # noqa: E402
from msxbright import grade_pal  # noqa: E402
from planar import write_png  # noqa: E402

LINES = 162


def rgb_of(pal: bytes) -> list[bytes]:
    return [bytes(v * 255 // 7 for v in (pal[2 * i] >> 4 & 7, pal[2 * i + 1] & 7, pal[2 * i] & 7)) for i in range(16)]


def preview(path: Path, area: bytes, hud: bytes, txt_pal: bytes, hud_pal: bytes) -> None:
    a, h = rgb_of(txt_pal), rgb_of(hud_pal)
    a[0] = bytes(3)
    rows = []
    for y in range(LINES):
        rows.append(b"".join(a[b >> 4] * 2 + a[b & 15] * 2 for b in area[y * 128:y * 128 + 128]))
    rows += [bytes(3 * 512)] * 5
    for y in range(len(hud) // 128):
        rows.append(b"".join(h[b >> 4] * 2 + h[b & 15] * 2 for b in hud[y * 128:y * 128 + 128]))
    rows = [r for r in rows for _ in (0, 1)]
    write_png(path, 512, len(rows), rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", type=Path)
    ap.add_argument("tag")
    ap.add_argument("--tag", dest="ntag", type=int, default=0, help="the build's TAG")
    ap.add_argument("--result", default="time", choices=("ok", "fail", "time"))
    ap.add_argument("--gen", type=Path, help="the build's gen folder (hud_grade.pal) for the previews")
    ap.add_argument("--range", dest="rg", help="the shooting range's screens in this flow: time or C,D,M")
    ap.add_argument("--no-game", action="store_true", help="the record stops before a new game")
    a = ap.parse_args()
    ram = (ROOT / "build" / "ram" / "level1_full.bin").read_bytes()
    glyphs = [msxtext.glyph_sc5(ram, g) for g in range(44)]
    scripts = {label: script for label, _, script in msxtext.bonus_scripts(ram)}
    bad = 0
    for name, label in (("intro", "txt_bs_intro"), ("result", f"txt_bs_{a.result}")):
        script = scripts[label]
        plain = msxtext.fs_render(glyphs, script)
        stored = (ROOT / "build" / "msx" / f"text_bs_{label[7:]}.sc5").read_bytes()
        if plain != stored:
            print(f"{name}: the render of {label} differs from build/msx's text_bs_{label[7:]}.sc5")
            bad = 1
        if a.ntag:
            tag = b"TEST " + str(a.ntag).encode()
            script = bytes((0, 14 if a.ntag > 9 else 15, 10)) + tag + script
        ref = msxtext.fs_render(glyphs, script)
        got = (a.dir / f"{a.tag}_{name}.sc5").read_bytes()
        diff = [i for i in range(len(ref)) if ref[i] != got[i]]
        if diff:
            ys = sorted({i // 128 for i in diff})
            print(f"{name} ({label}{', TEST %d' % a.ntag if a.ntag else ''}): {len(diff)} bytes DIFFER, lines {ys[0]}-{ys[-1]}")
            bad = 1
        else:
            print(f"{name} ({label}{', TEST %d' % a.ntag if a.ntag else ''}): equal to the render, pixel for pixel")
        regs = (a.dir / f"{a.tag}_{name}_regs.bin").read_bytes()
        if regs[0] != 0x16 or regs[1] != 0x62:
            print(f"{name}: R#0 {regs[0]:02X}h R#1 {regs[1]:02X}h (the line interrupt and the display not both on)")
            bad = 1
        if a.gen:
            txt_pal = grade_pal(msxtext.msx_palette(ram))
            hud_pal = (a.gen / "hud_grade.pal").read_bytes()
            preview(a.dir / f"{a.tag}_{name}.png", got, (a.dir / f"{a.tag}_{name}_hud.bin").read_bytes(), txt_pal, hud_pal)
    notes = (a.dir / f"{a.tag}_bonus.txt").read_text()
    print(notes.rstrip())
    m = re.search(r"^result (\w+) ", notes, re.M)
    if not m or m[1] != a.result:
        print(f"the result screen shown: {m[1] if m else 'none'}, expected {a.result}")
        bad = 1
    m = re.search(r"(\d+) VBLANKs, (\d+) HUD splits", notes)
    if not m or abs(int(m[1]) - int(m[2])) > 1 or int(m[1]) < 100:      # (the window starts and ends mid-frame)
        print("the HUD split did not run at every VBLANK between the records")
        bad = 1
    if not a.no_game and not re.search(r"^game tick_n", notes, re.M):
        print("no new game after the stage")
        bad = 1
    if a.rg:
        print("-- the shooting range after Brainstorm's result")
        rb = rgcheck.check(a.dir, a.tag, rgcheck.parse_counts(a.rg), a.ntag)
        print("  the range:", "PASS" if not rb else "FAIL")
        bad |= rb
    print("bonus check:", "PASS" if not bad else "FAIL")
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
