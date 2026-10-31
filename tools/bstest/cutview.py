#!/usr/bin/env python3
"""Level 2's cut at a vat's surface and its arrest scene's view as the MSX shows them (docs/LEVEL2.md
4.2 checks 9 and 10; its step 15).

  cutview.py cut SNAPROOT REF.jsonl [--py PY]
      SNAPROOT/<m>/gNNNN: tools/bstest/hz.tcl hz_l2_still_jobs' stills (the l2 build on the drive of
      the bench reference REF, build/emu/l2_vat.drive). For each still, the tick its list shows (the
      list's game frame G: the bench's row with that game frame next to the still's tick_n, the
      drive's index, holds the camera and RoboCop as that tick's vats saw them) and the original's copper line there (msx/level2.asm lt1's rule: CBh - d for the vat in
      the camera's window whose x range is within 10h of RoboCop's, d = camera y + 98h - its y in
      0..4Ch; else CAh, no cut). Below CAh, its screen line on the MSX is the line - 1Eh (the play
      field's first line) + the camera's y - the list's camera y, and tools/msxframe.py --field --cut
      LINE checks the still: RoboCop's and the hit spark's sprites end above the line, every other
      sprite whole, the play area exact. PASS: every still with a cut exact, and the cut left out some
      of RoboCop's pixels in at least one (else the check saw no sinking). The stills without a cut
      are checked by msxframe alone and only reported (their differences: msxframe's own classes,
      to be compared with the base's stills).
  cutview.py view DIR [--add N]
      DIR/view_<name>_<m>.txt (tools/bstest/cutview.tcl cv_view_jobs): from the suspect's first list
      (its play-field frames in the list) to the arrest's (the last with them):
      - v_addx (the view's offset, level2obj.asm t2) moves at most 2 pixels a tick, up to N (48);
      - the view (v_x) moves at most 2 pixels a tick but where it follows RoboCop at the edge of his
        range (player.asm pv_keep: his place p_x - 131 - v_x at AX_MIN 48 or AX_MAX 160) or stays at
        the map's left edge;
      - RoboCop's place within 48..160 but at the map's left edge (v_x 0);
      - the suspect whole in the view (its pixels' columns, from the level's atlas, within the map x
        the screen shows: cam_x .. cam_x + 247, the V9938's right border from cam_x & 15 above 8 off)
        in every list from the first one with the view at its target (v_x = the game camera's x + N:
        the view has moved) to the arrest.
      PASS when all hold on every record.
"""
from __future__ import annotations

import json
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

VATS = [(848, 1024, 640), (1296, 1440, 640), (1568, 1712, 640), (2016, 2256, 688),   # x0, x1, y
        (1904, 2240, 288), (1264, 1568, 288), (608, 800, 288)]                       # (the original's)
LIST_A, LIST_B, APP_SEQ, RAM_BASE = 0xC080, 0xC0A0, 0xC006, 0xC000
AX_MIN, AX_MAX, PLACE = 48, 160, -131          # player.asm: RoboCop's place = p_x + SPR_X_OFS + 8 - v_x
SUSPECT = (9, 10)                              # its play-field frames (build/msx/sprites_l2.json "field")


def copper_line(row: dict) -> int:
    """The original's sprite cut line ($10356) for the tick whose results the bench's row holds."""
    px, cx, cy = row["player_x"], row["camera_x"], row["camera_y"]
    line = 0xCA
    for x0, x1, y in VATS:
        if not (cy - 0x64 <= y < cy + 0xAC and x1 >= cx + 0x73 and x0 < cx + 0x1A0):
            continue
        if px + 0x10 >= x0 and px - 0x10 < x1:
            d = cy + 0x98 - y
            if 0 <= d < 0x4D:
                line = 0xCB - d
    return line


def list_shown(ram: bytes) -> tuple[int, int, int]:
    """The list on screen (seq = app_seq): its camera x, y and game frame (msx/isr.asm list_tail)."""
    seq = ram[APP_SEQ - RAM_BASE]
    for base in (LIST_A, LIST_B):
        o = base - RAM_BASE
        if ram[o] == seq:
            return struct.unpack_from("<HHH", ram, o + 2 + ram[o + 1])
    raise ValueError(f"no register list with seq {seq}")


def cmd_cut(args: list[str]) -> int:
    root, ref = Path(args[0]), Path(args[1])
    py = args[args.index("--py") + 1] if "--py" in args else str(Path.home() / ".venvs/msxports/bin/python")
    rows = [json.loads(x) for x in ref.read_text().splitlines()]
    bad = cut_px = cuts = other = 0
    for snap in sorted(p for p in root.glob("*/g*") if (p / "ram.bin").exists()):
        cam_x, cam_y, g = list_shown((snap / "ram.bin").read_bytes())
        # (the bench's row: the drive's index, the still's tick_n, near it; the game frame restarts
        # at every life)
        tick = int(re.search(r"tick_n (\d+)", (snap / "when.txt").read_text())[1])
        near = [i for i, r in enumerate(rows) if r["game_frame"] == g and abs(i - tick) <= 4]
        row = rows[min(near, key=lambda i: abs(i - tick))] if near else None
        if row is None:
            print(f"{snap.parent.name}/{snap.name}: list of game frame {g}: no bench row")
            bad += 1
            continue
        line = copper_line(row)
        cmd = [py, "-I", str(ROOT / "tools/msxframe.py"), str(snap), str(ROOT / "build/msx/level2"),
               str(ROOT / "build/msx/hud"), str(snap / "cut.png"), "--sprites", str(ROOT / "build/msx/sprites"),
               "--level", "2", "--field"]
        at = ""
        if line < 0xCA:
            scr = line - 0x1E + row["camera_y"] - cam_y
            cmd += ["--cut", str(scr)]
            at = f"line {line:#04x}, screen line {scr}"
            cuts += 1
        out = subprocess.run(cmd, capture_output=True, text=True)
        txt = out.stdout + out.stderr
        m = re.search(r"(\d+)/(\d+) sprite pixels exact", txt)
        d = re.search(r"(\d+) pixels checked, (\d+) differ", txt)
        c = re.search(r"cut at screen line -?\d+: (\d+) of", txt)
        left = int(c[1]) if c else 0
        cut_px += left
        ok = out.returncode == 0 and m and m[1] == m[2] and d and d[2] == "0"
        if at:
            bad += not ok
        else:
            other += not ok
        print(f"{snap.parent.name}/{snap.name}: list of game frame {g}, camera ({cam_x},{cam_y}); "
              f"{at or 'no cut (CAh)'}; " + (f"{left} of RoboCop's pixels left out; " if at else "")
              + (f"sprite pixels {m[1]}/{m[2]} exact, " if m else "") + (f"{d[2]} of {d[1]} differ" if d else "")
              + ("" if ok else "  <- NOT EXACT" if at else "  (not exact, no cut)")
              + ("" if ok or "tile VRAM changed" not in txt else "; tile VRAM changed"))
    print(f"cut: {cuts} stills with a cut, {cut_px} of RoboCop's pixels left out in all, {bad} of them not exact; "
          f"{other} without a cut not exact")
    ok = bad == 0 and cut_px > 0
    print("cut: PASS" if ok else "cut: FAIL")
    return 0 if ok else 1


def suspect_columns() -> dict[int, tuple[int, int]]:
    """Per frame of the suspect: the first and last column of its pixels (the level's atlas)."""
    import msxframe
    looks = msxframe.FieldLooks(2, ROOT / "build/msx/sprites")
    out = {}
    for fid in SUSPECT:
        px = looks.pixels(fid)
        cols = [x for x in range(len(px[0])) if any(line[x] for line in px)]
        out[fid] = (cols[0], cols[-1])
    return out


def s16(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v


def cmd_view(args: list[str]) -> int:
    d = Path(args[0])
    add_max = int(args[args.index("--add") + 1]) if "--add" in args else 48
    cols = suspect_columns()
    allok = True
    for f in sorted(d.glob("view_*.txt")):
        ticks, lists = {}, []
        for line in f.read_text().splitlines():
            p = line.split()
            if p and p[0] == "T":
                g, vx, vy, add, px, gcx, gcy = (int(x) for x in p[1:8])
                ticks[g] = dict(vx=s16(vx), add=add, px=s16(px), gcx=s16(gcx))
            elif p and p[0] == "L":
                g, cx, cy, rf, rx, ry, n = (int(x) for x in p[1:8])
                bobs = [(int(p[8 + 3 * i]), s16(int(p[9 + 3 * i])), s16(int(p[10 + 3 * i]))) for i in range(n)]
                lists.append(dict(g=g, cx=cx, cy=cy, bobs=bobs))
        sl = [l for l in lists if any(b[0] in SUSPECT for b in l["bobs"])]
        name = f.stem[5:]
        if not sl or not ticks:
            print(f"{name}: no suspect in the record ({len(lists)} lists, {len(ticks)} ticks)")
            allok = False
            continue
        g0, g1 = sl[0]["g"], sl[-1]["g"]
        v9958 = not name.endswith("_m2")
        errs, add_steps, view_steps, keep_steps, edge = [], set(), [], 0, 0
        gs = sorted(g for g in ticks if g0 <= g <= g1)
        for a, b in zip(gs, gs[1:]):
            if b != a + 1:
                continue
            ta, tb = ticks[a], ticks[b]
            add_steps.add(tb["add"] - ta["add"])
            dv = tb["vx"] - ta["vx"]
            place = tb["px"] + PLACE - tb["vx"]
            if abs(dv) > 2:
                if place in (AX_MIN, AX_MAX) or tb["vx"] == 0:
                    keep_steps += 1
                else:
                    errs.append(f"tick {b}: the view moved {dv} px (RoboCop's place {place})")
            view_steps.append(dv)
        for g in gs:
            t = ticks[g]
            place = t["px"] + PLACE - t["vx"]
            if not AX_MIN <= place <= AX_MAX:
                if t["vx"] == 0:
                    edge += 1
                else:
                    errs.append(f"tick {g}: RoboCop's place {place} outside {AX_MIN}..{AX_MAX}")
            if not 0 <= t["add"] <= add_max:
                errs.append(f"tick {g}: v_addx {t['add']}")
        bad_add = [s for s in add_steps if s not in (0, 2)]
        if bad_add:
            errs.append(f"v_addx steps {sorted(add_steps)}")
        moved = next((g for g in gs if ticks[g]["vx"] == ticks[g]["gcx"] + add_max), None)
        whole_from, part = None, []
        for l in sl:
            right = l["cx"] + (247 if v9958 else min(247, 255 - (l["cx"] & 15)))
            whole = all(l["cx"] <= bx + cols[fi][0] and bx + cols[fi][1] <= right
                        for fi, bx, by in l["bobs"] if fi in SUSPECT)
            if whole and whole_from is None:
                whole_from = l["g"]
            if moved is not None and l["g"] > moved and not whole:
                part.append(l["g"])
        if moved is None:
            errs.append("the view never reached its target")
        if part:
            errs.append(f"the suspect not whole after the view moved, lists of game frames {part[:8]}")
        tops = max((abs(s) for s in view_steps), default=0)
        print(f"{name}: suspect lists {len(sl)} (game frames {g0}-{g1}); v_addx steps {sorted(add_steps)}, "
              f"at {add_max} from tick {next((g for g in gs if ticks[g]['add'] == add_max), None)}; the view at its "
              f"target from tick {moved}, the suspect whole from list {whole_from}; the view's steps at most {tops} "
              f"px a tick ({keep_steps} above 2 following RoboCop at his range's edge or at the map's edge); "
              f"RoboCop at the map's left edge outside {AX_MIN}..{AX_MAX} on {edge} ticks"
              + ("" if not errs else "\n  " + "\n  ".join(errs[:12])))
        allok &= not errs
    print("view: PASS" if allok else "view: FAIL")
    return 0 if allok else 1


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in ("cut", "view"):
        print(__doc__)
        return 2
    return cmd_cut(argv[2:]) if argv[1] == "cut" else cmd_view(argv[2:])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
