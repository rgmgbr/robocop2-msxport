#!/usr/bin/env python3
"""rgcheck.py DIR TAG (--counts C,D,M | --time) [--tag N] [--no-game]: checks a record of the shooting
range's screens (rgflow.tcl: rgx_job, rgx_arm_job, rgk_job, and the range inside Brainstorm's flows,
hb_step's rgh_arm; docs/HARNESS.md 5.19).

- DIR/TAG_rgintro.sc5 (page 0's lines 0-161 once the intro is complete) equals tools/msxtext.py's
  render of txt_rg_intro, pixel for pixel, with fe_text's TEST N line at row 10 first when --tag N;
  with N = 0 it also equals build/msx/text_rg_intro.sc5 (the converter's render).
- DIR/TAG_rgres.sc5 equals the render of the result front_range fills for the counts C (correct),
  D (dummy) and M (the timer's minutes) with its rating, or of OUT OF TIME. (txt_bs_time) with
  --time; with N = 0 also build/msx/text_rg_res_cC_dD_mM.sc5 when it exists, or text_rg_time.sc5.
- R#0 16h and R#1 62h at both records; a HUD split at every VBLANK between them (one more or fewer);
- the notes (DIR/TAG_rg.txt): the screen shown; the stage's result at fr_done (dummy, correct,
  $804C) and the rating at fr_rated (ac_diff - diff_tab: 24 - 8 x rating, 24 after a time out)
  as expected; the new game reached (its frame 100, level 1's trace done, or the game a title
  starts) with ac_diff - diff_tab = 0 again (SHARP: obj_start), and the lost counters 0 when noted.
Exit 0 when every check passes. Reads build/ram/level1_full.bin and build/msx of the repository this
file is in (tools/bstest/). bonuscheck.py --range calls check().
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import msxtext  # noqa: E402


def check(d: Path, tag: str, counts: tuple[int, int, int] | None, ntag: int = 0, game: bool = True,
          out=print) -> int:
    """The range's records DIR/TAG_rgintro, _rgres and TAG_rg.txt; counts None: OUT OF TIME.
    Returns 0 when every check passes."""
    ram = (REPO / "build" / "ram" / "level1_full.bin").read_bytes()
    glyphs = [msxtext.glyph_sc5(ram, n) for n in range(44)]
    scripts = {label: s for label, _, s in msxtext.range_scripts(ram)}
    bs = {label: s for label, _, s in msxtext.bonus_scripts(ram)}
    names = msxtext.rg_names(ram)
    tline = msxtext.tag_line(ntag)
    bad = 0
    if counts is None:
        res_script, stored, rating, want_res = bs["txt_bs_time"], "text_rg_time.sc5", 0, None
        what = "OUT OF TIME."
    else:
        c, dm, m = counts
        rating = msxtext.rg_rating(c, dm, m)
        res_script = msxtext.rg_fill(scripts["txt_rg_res"], names, c, dm, rating)
        stored, want_res = f"text_rg_res_c{c}_d{dm}_m{m}.sc5", (dm, c, 0)
        what = f"the result for {c} correct, {dm} dummy, {m} minutes: {msxtext.RG_NAME_TEXT[rating].strip()}"
    for name, script, ref_file in (("rgintro", scripts["txt_rg_intro"], "text_rg_intro.sc5"),
                                   ("rgres", res_script, stored)):
        ref = msxtext.fs_render(glyphs, tline + script)
        label = "the range's intro" if name == "rgintro" else what
        f = d / f"{tag}_{name}.sc5"
        if not f.exists():
            out(f"{name} ({label}): no record {f.name}")
            bad = 1
            continue
        got = f.read_bytes()
        diff = [i for i in range(len(ref)) if ref[i] != got[i]]
        if diff:
            ys = sorted({i // 128 for i in diff})
            out(f"{name} ({label}{', TEST %d' % ntag if ntag else ''}): {len(diff)} bytes DIFFER, lines {ys[0]}-{ys[-1]}")
            bad = 1
        else:
            out(f"{name} ({label}{', TEST %d' % ntag if ntag else ''}): equal to the render, pixel for pixel")
        if not ntag:
            sf = REPO / "build" / "msx" / ref_file
            if sf.exists():
                same = sf.read_bytes() == ref
                out(f"  the render {'equals' if same else 'DIFFERS from'} build/msx/{ref_file}")
                bad |= not same
        regs = (d / f"{tag}_{name}_regs.bin").read_bytes()
        if regs[0] != 0x16 or regs[1] != 0x62:
            out(f"{name}: R#0 {regs[0]:02X}h R#1 {regs[1]:02X}h (the line interrupt and the display not both on)")
            bad = 1
    nf = d / f"{tag}_rg.txt"
    notes = nf.read_text() if nf.exists() else ""
    out(notes.rstrip())
    m_ = re.search(r"^result (\w+) ", notes, re.M)
    want = "time" if counts is None else "res"
    if not m_ or m_[1] != want:
        out(f"the screen shown: {m_[1] if m_ else 'none'}, expected {want}")
        bad = 1
    m_ = re.search(r"(\d+) VBLANKs, (\d+) HUD splits", notes)
    if not m_ or abs(int(m_[1]) - int(m_[2])) > 1 or int(m_[1]) < 100:
        out("the HUD split did not run at every VBLANK between the records")
        bad = 1
    m_ = re.search(r"^stage: result \{?(\d+) (\d+) (\d+)\}? .*rating (-?\d+) at fr_rated", notes, re.M)
    want_rating = 24 if counts is None else 24 - 8 * rating
    if not m_:
        out("no stage result or rating noted")
        bad = 1
    else:
        got = tuple(int(v) for v in m_.groups()[:3])
        if counts is None and got[2] != 255:
            out(f"the stage's result {got}: $804C not FFh after a time out")
            bad = 1
        if want_res and got != want_res:
            out(f"the stage's result {got}, expected {want_res} (dummy, correct, $804C)")
            bad = 1
        if int(m_[4]) != want_rating:
            out(f"the rating at fr_rated: ac_diff - diff_tab = {m_[4]}, expected {want_rating}")
            bad = 1
        else:
            out(f"the rating at fr_rated: ac_diff - diff_tab = {m_[4]}, as expected")
    if game:
        m_ = re.search(r"^game tick_n", notes, re.M)
        sharp = re.search(r"^(game tick_n|level-1 trace done).*ac_diff - diff_tab 0\b", notes, re.M)
        if not m_:
            out("no new game after the range")
            bad = 1
        elif not sharp:
            out("the new game does not run with SHARP (ac_diff - diff_tab 0)")
            bad = 1
        for lm in re.finditer(r"lost: mp (\d+) atr (\d+) rd (\d+) fb (\d+)", notes):
            if any(int(v) for v in lm.groups()):
                out(f"lost counters not 0: {lm[0]}")
                bad = 1
    return bad


def parse_counts(spec: str) -> tuple[int, int, int] | None:
    """'time' -> None (OUT OF TIME.), 'C,D,M' -> the counts"""
    if spec == "time":
        return None
    c, d, m = (int(v) for v in spec.split(","))
    return c, d, m


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", type=Path)
    ap.add_argument("tag")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--counts", help="C,D,M: correct, dummy, the timer's minutes")
    g.add_argument("--time", action="store_true", help="the time out: OUT OF TIME.")
    ap.add_argument("--tag", dest="ntag", type=int, default=0, help="the build's TAG")
    ap.add_argument("--no-game", action="store_true", help="the record has no new game (stopped before)")
    a = ap.parse_args()
    bad = check(a.dir, a.tag, None if a.time else parse_counts(a.counts), a.ntag, not a.no_game)
    print("range check:", "PASS" if not bad else "FAIL")
    return bad


if __name__ == "__main__":
    raise SystemExit(main())
