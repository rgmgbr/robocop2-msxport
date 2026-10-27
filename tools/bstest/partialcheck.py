#!/usr/bin/env python3
"""A bonus text screen cut short by fire (np.tcl np_fire_setup; docs/HARNESS.md 5.17 d): the
snapshot taken just before the press (hz7_snap: physical VRAM, RAM C000h-FFFFh, ...) shows in page
0's lines 0-161 the render of the script as far as front.asm fs_step got (fs_n calls; fs_n + 1 when
the snapshot fell between fs_step and fs_n's increment), with TEST n drawn first as fe_text draws it.

usage: partialcheck.py SNAP.bin LABEL [--tag N]     (LABEL: txt_bs_intro, txt_bs_ok, ...)
Exit 0 when one of the two renders equals the page, pixel for pixel; 1 otherwise; 2 on an unknown
label.

Reads build/ram/level1_full.bin of the repository this file is in (tools/bstest/).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import msxtext  # noqa: E402

FS_N = 0xCFBE - 0xC000          # fs_n in the snapshot's RAM (C000h-FFFFh after the 128 KiB of VRAM)


def offset_after(script: bytes, calls: int) -> int:
    """fs_step's byte offset in the script after 'calls' calls (msxtext.fs_run's rules)."""
    a = wait = 0
    for _ in range(calls):
        if wait:
            wait -= 1
        elif script[a] == 0:
            a += 3
        elif script[a] < 0x80:
            a += 1
        elif script[a + 1] == 2:
            wait = (4 * script[a + 2] if script[a + 2] else 1) - 1
            a += 3
        else:
            break
    return a


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("snap", type=Path)
    ap.add_argument("label")
    ap.add_argument("--tag", type=int, default=0)
    a = ap.parse_args(argv)
    ram = (ROOT / "build" / "ram" / "level1_full.bin").read_bytes()
    glyphs = [msxtext.glyph_sc5(ram, g) for g in range(44)]
    scripts = {label: s for label, _, s in msxtext.bonus_scripts(ram)}
    if a.label not in scripts:
        print(f"partialcheck: no script {a.label} (the scripts: {', '.join(scripts)})", file=sys.stderr)
        return 2
    script = scripts[a.label]
    d = a.snap.read_bytes()
    page = d[:162 * 128]
    fs_n = d[0x20000 + FS_N] | d[0x20000 + FS_N + 1] << 8
    full = msxtext.fs_run(script)[2]
    for k in (fs_n, fs_n + 1):
        cut = offset_after(script, k)
        part = script[:cut] + b"\xff\x07"
        if a.tag:
            part = bytes((0, 14 if a.tag > 9 else 15, 10)) + b"TEST " + str(a.tag).encode() + part
        ref = msxtext.fs_render(glyphs, part)
        if ref == page:
            shown = len(msxtext.fs_run(script[:cut] + b"\xff\x07")[2])
            print(f"{a.snap.name}: fs_n {fs_n}: page 0 = the render of {a.label} after {k} fs_step calls "
                  f"({shown} of its {len(full)} characters{', TEST %d first' % a.tag if a.tag else ''}), pixel for pixel")
            return 0
    print(f"{a.snap.name}: fs_n {fs_n}: page 0 equals neither render ({fs_n} or {fs_n + 1} calls of {a.label})")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
