#!/usr/bin/env python3
"""Checks a hz.tcl hz_bonus record: the bonus text screens against renders of the port's scripts.

usage: bonuscheck.py DIR TAG [--tag N] [--result time|ok|fail] [--gen GEN_DIR] [--range time|C,D,M]
                     [--brief l2|l3] [--level2 | --level3] [--no-game]

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
With --brief (level 2's step 18: front.asm front_brief after the range; hz.tcl hb_brief_arm): DIR/
TAG_brief.sc5 equals the render of txt_l2_brief or txt_l3_brief (with TEST N), R#0 16h and R#1 62h
there, the screen's length at its fe_end the script's calls + 1 ticks (394, 412: the original's VBLs)
or, ended by fire, 50 or more, and a HUD split at every VBLANK from the record to that end. With --level2 (the product's
flow: lv_next after the briefing): no new game but level 2 at its game frame 100 ("level 2 at
tick_n"), the lost counters 0 there, with --range the range's rating kept into level 2 (rgcheck.py),
and its first picture (first_picture: TAG_l2g0, hz.tcl hb_l2_snap) checked: tools/msxframe.py on it
(--field --no-sprites, the venv's Python or --py PY) must exit 0, and the notes' record of what the
HUD shows must hold the game's score, ammo, timer, lives (the heads) and full can. With --level3 (level 3's
step D: the product's flow after level 2's end, np.tcl np_l3flow_setup's TAG2): the same for level 3 after the
level-3 briefing (TAG_l3g0, "level 3's first picture", "level 3 at tick_n"); with --range the rating level 3
runs with is the range's (rgcheck.py's fr_rated: POOR, 24, after a time out).
Exit 0 when every check passed.

Reads build/ram/level1_full.bin and build/msx/text_bs_*.sc5 of the repository this file is in
(tools/bstest/); docs/HARNESS.md.
"""
from __future__ import annotations

import argparse
import re
import subprocess
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


BRIEF_CALLS = {"l2": 393, "l3": 411}
VPY = str(Path.home() / ".venvs/msxports/bin/python")      # (msxframe.py needs numpy)
# msx/hud.asm cell_src: per digit cell the byte of hud_timer, hud_ammo, hud_score (the game's words
# big-endian) and its nibble (80h: the high one): the timer's 4, the ammo's 3, the score's 7
CELL_SRC = (0x80, 0x00, 0x81, 0x01, 0x02, 0x83, 0x03, 0x04, 0x85, 0x05, 0x86, 0x06, 0x87, 0x07)
FIRST = re.compile(r"^level (\d)'s first picture at .*?timer ([0-9A-F]{4}), score ([0-9A-F]{8}), lives (\d+), "
                   r".*?weapon (\d+), ammo ([0-9A-F]{4}), .*?HUD shown ([0-9a-f]{28}) heads (\d+) (\d+) "
                   r"icon (\d+) can ([0-9A-F]{4}) jobs (\d+)/(\d+)", re.M)


def hud_cells(timer: int, ammo: int, score: int) -> list[int]:
    """The digit each HUD cell shows for these values (hud.asm hud_digits, cell_digit)."""
    b = timer.to_bytes(2, "big") + ammo.to_bytes(2, "big") + score.to_bytes(4, "big")
    return [b[c & 0x7F] >> 4 if c & 0x80 else b[c & 0x7F] & 15 for c in CELL_SRC]


def first_picture(d: Path, tag: str, notes: str, py: str = VPY, level: int = 2) -> int:
    """Level 2's first picture (DIR/TAG_l2g0, hz.tcl hb_l2_snap: the split of its first list with the
    display on, the HUD not being drawn; after lv_next or lv_cont), against the level's own and the
    game's values (docs/LEVEL2.md 4.2 checks 1 and 13); level 3's (level=3: DIR/TAG_l3g0, the notes'
    "level 3's first picture", tools/msxframe.py --level 3; docs/LEVEL3.md 4 checks 7 and 8) the same way:
      - tools/msxframe.py on it with --field --no-sprites exits 0: the play area equal to the map with
        its patches, the vats and the play-field BOBs of the list (the sprites not checked: the list's
        SAT is not published yet at its frame 0), the HUD equal to what hud.asm records as shown, the
        tile cache's slots on page 2 and the atlas on page 3 equal to the level's;
      - the notes' record of what the HUD shows (its line "level 2's first picture at") holds the
        game's values: the score's 7 cells and the ammo's 3 as AG's words, the timer's 4 as AG's
        timer or 07:30 (the level's start, the timer's first second not yet drawn), the heads (slot
        k: 0 while the lives are more than k, else the lost life's 5), weapon 0's icon 3, the can full
        (0100h), no HUD job pending.
    Returns 0 when every check passes."""
    bad = 0
    m = next((x for x in FIRST.finditer(notes) if int(x[1]) == level), None)
    if not m:
        print(f"level {level}'s first picture: not noted (or not in the notes' format)")
        return 1
    timer, score, lives, weapon, ammo = int(m[2], 16), int(m[3], 16), int(m[4]), int(m[5]), int(m[6], 16)
    shown = list(bytes.fromhex(m[7]))
    heads, icon, can, jobs = (int(m[8]), int(m[9])), int(m[10]), int(m[11], 16), (int(m[12]), int(m[13]))
    lives -= 0x10000 if lives >= 0x8000 else 0
    want = hud_cells(timer, ammo, score)
    start = hud_cells(0x0730, ammo, score)
    what = []
    if shown[4:] != want[4:]:
        what.append(f"ammo and score cells {shown[4:]} (the game's {ammo:04X}h, {score:08X}h: {want[4:]})")
    if shown[:4] not in (want[:4], start[:4]):
        what.append(f"timer cells {shown[:4]} (the game's {timer:04X}h: {want[:4]}, or 07:30)")
    want_heads = tuple(0 if lives > k else 5 for k in (0, 1))
    if heads != want_heads:
        what.append(f"heads {heads[0]} {heads[1]} with {lives} lives ({want_heads[0]} {want_heads[1]} expected)")
    if weapon == 0 and icon != 3:
        what.append(f"icon {icon} with weapon 0 (3 expected)")
    if can != 0x100:
        what.append(f"the can {can:04X}h (full: 0100h)")
    if jobs != (0, 0):
        what.append(f"HUD jobs pending {jobs[0]}/{jobs[1]}")
    if what:
        print(f"level {level}'s first picture: the HUD's record does not hold the game's values: " + "; ".join(what))
        bad = 1
    else:
        print(f"level {level}'s first picture: the HUD's record holds the game's values (score {score:08X}h, "
              f"ammo {ammo:04X}h, timer {''.join(map(str, shown[:4]))}, {lives} lives: heads {heads[0]} "
              f"{heads[1]}, icon {icon}, the can full, no job)")
    snap = d / f"{tag}_l{level}g0"
    if not (snap / "vram.bin").exists():
        print(f"level {level}'s first picture not recorded")
        return 1
    cmd = [py, "-I", str(ROOT / "tools/msxframe.py"), str(snap), str(ROOT / f"build/msx/level{level}"),
           str(ROOT / "build/msx/hud"), str(d / f"{tag}_l{level}g0.png"), "--sprites", str(ROOT / "build/msx/sprites"),
           "--level", str(level), "--field", "--no-sprites"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
    except OSError as e:
        print(f"level {level}'s first picture: msxframe.py not run ({e}: give --py PY, a Python with numpy)")
        return 1
    for line in r.stdout.splitlines():
        if re.search(r"pixels checked|tile VRAM|HUD job|play field:", line):
            print("  msxframe: " + line.strip()[:200])
    if r.returncode:
        print(f"level {level}'s first picture: msxframe.py exit {r.returncode} ({r.stderr.strip()[-200:]})")
        bad = 1
    else:
        print(f"level {level}'s first picture: msxframe.py exit 0 (the play area, the HUD, the tiles and the atlas)")
    return bad


def check_brief(a, ram: bytes, glyphs: list[bytes], notes: str) -> int:
    """The next level's briefing (--brief): its record against the render, its registers, its
    length and the HUD split while it showed. Returns 0 when every check passes."""
    bad = 0
    label = f"txt_{a.brief}_brief"
    script = {lb: sc for lb, _, sc in msxtext.brief_scripts(ram)}[label]
    ref = msxtext.fs_render(glyphs, msxtext.tag_line(a.ntag) + script)
    f = a.dir / f"{a.tag}_brief.sc5"
    if not f.exists():
        print(f"brief ({label}): no record {f.name}")
        return 1
    got = f.read_bytes()
    diff = [i for i in range(len(ref)) if ref[i] != got[i]]
    tg = f", TEST {a.ntag}" if a.ntag else ""
    if diff:
        ys = sorted({i // 128 for i in diff})
        print(f"brief ({label}{tg}): {len(diff)} bytes DIFFER, lines {ys[0]}-{ys[-1]}")
        bad = 1
    else:
        print(f"brief ({label}{tg}): equal to the render, pixel for pixel")
    regs = (a.dir / f"{a.tag}_brief_regs.bin").read_bytes()
    if regs[0] != 0x16 or regs[1] != 0x62:
        print(f"brief: R#0 {regs[0]:02X}h R#1 {regs[1]:02X}h (the line interrupt and the display not both on)")
        bad = 1
    if not re.search(rf"^brief {a.brief} at ", notes, re.M):
        print(f"brief: the notes name no {a.brief} briefing")
        bad = 1
    m = re.search(rf"^brief {a.brief} end at .*fs_n (\d+), fs_done (\d+); from the record: (\d+) VBLANKs, (\d+) HUD splits", notes, re.M)
    if not m:
        print("brief: its end not noted")
        return 1
    n, done, vbl, spl = (int(v) for v in m.groups())
    calls = BRIEF_CALLS[a.brief]
    # (fs_n at fe_end counts the call that reads the end too: the script's calls + 1 ticks, the
    #  original's VBLs: 393 calls, 394 VBLs, docs/LEVEL2.md 2.1)
    if done and n != calls + 1:
        print(f"brief: {n} ticks, the script's {calls} calls + 1 expected")
        bad = 1
    elif not done and not 50 <= n <= calls:
        print(f"brief: ended by fire at tick {n} (50 to {calls} expected)")
        bad = 1
    else:
        print(f"brief: {n} ticks ({f'its whole length: {calls} calls' if done else 'ended by fire'})")
    if abs(vbl - spl) > 1 or vbl < 100:
        print(f"brief: {vbl} VBLANKs, {spl} HUD splits (the split not at every VBLANK)")
        bad = 1
    if a.gen:
        txt_pal = grade_pal(msxtext.msx_palette(ram))
        hud_pal = (a.gen / "hud_grade.pal").read_bytes()
        preview(a.dir / f"{a.tag}_brief.png", got, (a.dir / f"{a.tag}_brief_hud.bin").read_bytes(), txt_pal, hud_pal)
    return bad


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", type=Path)
    ap.add_argument("tag")
    ap.add_argument("--tag", dest="ntag", type=int, default=0, help="the build's TAG")
    ap.add_argument("--result", default="time", choices=("ok", "fail", "time"))
    ap.add_argument("--gen", type=Path, help="the build's gen folder (hud_grade.pal) for the previews")
    ap.add_argument("--range", dest="rg", help="the shooting range's screens in this flow: time or C,D,M")
    ap.add_argument("--no-game", action="store_true", help="the record stops before a new game")
    ap.add_argument("--brief", choices=("l2", "l3"), help="the next level's briefing recorded after the range")
    ap.add_argument("--level2", action="store_true", help="level 2 follows the briefing (no new game)")
    ap.add_argument("--level3", action="store_true", help="level 3 follows the briefing (no new game)")
    ap.add_argument("--py", default=VPY, help="the Python with numpy for tools/msxframe.py (--level2)")
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
    if a.brief:
        bad |= check_brief(a, ram, glyphs, notes)
    if a.level2 or a.level3:
        lv = 2 if a.level2 else 3
        m = re.search(rf"^level {lv} at tick_n (\d+), game frame (\d+).*ac_diff - diff_tab (\d+).*"
                      r"lost: mp (\d+) atr (\d+) rd (\d+) fb (\d+)", notes, re.M)
        if not m:
            print(f"no level {lv} after the briefing (its game frame 100)")
            bad = 1
        else:
            if any(int(v) for v in m.groups()[3:]):
                print(f"level {lv}: lost counters not 0 ({m[0][-40:]})")
                bad = 1
            else:
                print(f"level {lv} at its game frame {m[2]}: the lost counters 0")
            if lv == 3 and a.rg:
                want = 24 if a.rg == "time" else None      # (rgcheck.py: a time out rates POOR)
                rn = (a.dir / f"{a.tag}_rg.txt")
                r = re.search(r"rating (-?\d+) at fr_rated", rn.read_text() if rn.exists() else "")
                got = int(m[3])
                if want is None and r:
                    want = int(r[1])
                if want is None or got != want:
                    print(f"level 3 runs with ac_diff - diff_tab {got}, the range's {want} expected")
                    bad = 1
                else:
                    print(f"level 3 runs with the range's rating (ac_diff - diff_tab {got})")
        bad |= first_picture(a.dir, a.tag, notes, a.py, lv)
        if re.search(r"^game tick_n", notes, re.M):
            print(f"a new game after the briefing, not level {lv}")
            bad = 1
    elif not a.no_game and not re.search(r"^game tick_n", notes, re.M):
        print("no new game after the stage")
        bad = 1
    if a.rg:
        print("-- the shooting range after Brainstorm's result")
        rb = rgcheck.check(a.dir, a.tag, rgcheck.parse_counts(a.rg), a.ntag, game=not a.level3, level2=a.level2)
        print("  the range:", "PASS" if not rb else "FAIL")
        bad |= rb
    print("bonus check:", "PASS" if not bad else "FAIL")
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
