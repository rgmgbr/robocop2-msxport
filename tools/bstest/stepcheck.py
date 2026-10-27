#!/usr/bin/env python3
"""Step 7's display checks (docs/BRAINSTORM.md 4.2 checks 2 and 3) on hz7.tcl's records.

usage:
  stepcheck.py still SNAP.bin [...]           the page on screen (the applied list's R#2) with its
                                              sprites (R#5's SAT) equals tools/msxpuzl.py's render
                                              of that page's shown state (rd_st0 / rd_st1 in the
                                              snapshot's RAM) and of the cursor in the SAT
  stepcheck.py rec REC.bin [--ref REF.jsonl] [--png DIR] [--from N] [--every K]
                                              every recorded picture: each element rectangle is
                                              one of its states (no torn block), every pixel
                                              outside them is the static screen's (coherence), the
                                              cursor's SAT is valid and, with --ref (the bench's
                                              trace of the same drive), the cursor of the pass the
                                              list was published after (list_tail's $B00): present
                                              in play, absent in the end sequences
Exit 0 when every check passed.

A snapshot (hz7.tcl hz7_snap) is VRAM 128 KiB, RAM C000h-FFFFh, the 64 VDP registers and the
palette; a record (hz7_pic) is REC's parts, one after the other, a VBLANK each. Reads
build/extracted/files/PUZL_25.bin of the repository this file is in (tools/bstest/);
docs/HARNESS.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import msxpuzl  # noqa: E402
from planar import write_png  # noqa: E402

W, H = 256, 162
RD_ST = (0xEE20, 0xEE90)
REC = [("regs", 64), ("page", 20736), ("sat", 32), ("pfpal", 32), ("list", 32), ("c0", 256), ("c6", 256),
       ("d0", 256), ("ee", 256)]
REC_LEN = sum(n for _, n in REC)


def puzl() -> msxpuzl.Puzl:
    return msxpuzl.Puzl((ROOT / "build/extracted/files/PUZL_25.bin").read_bytes())


def page_pixels(data: bytes) -> list[list[int]]:
    return [[(data[128 * y + x // 2] >> (0 if x & 1 else 4)) & 15 for x in range(W)] for y in range(H)]


def parse_list(b: bytes) -> tuple[dict, int]:
    n = b[1]
    regs = {b[2 + i + 1] & 0x3F: b[2 + i] for i in range(0, n, 2)}
    tail = 2 + n
    gframe = b[tail + 4] | b[tail + 5] << 8
    return regs, gframe


def sat_entries(sat: bytes) -> list[tuple[int, int, int]]:
    out = []
    for k in range(8):
        y, x, p = sat[4 * k], sat[4 * k + 1], sat[4 * k + 2]
        if y == 216:
            break
        out.append((y, x, p))
    return out


def cursor_of(p: msxpuzl.Puzl, ents: list) -> tuple | None | str:
    """The (column, row, image) the SAT entries show, None when empty, or an error string."""
    if not ents:
        return None
    y, x, pa = ents[0]
    if (y - msxpuzl.SAT_Y) % 16 or (x - msxpuzl.SAT_X) % 16 or pa % 4:
        return f"entry 0 {ents[0]} off the grid"
    c, r = (x - msxpuzl.SAT_X) // 16, (y - msxpuzl.SAT_Y) // 16
    pb = None
    if len(ents) > 1:
        if len(ents) > 2 or ents[1][:2] != (y, x) or ents[1][2] % 4:
            return f"entries {ents}"
        pb = ents[1][2] // 4
    for i, (ua, ub) in enumerate(p.use):
        if ua == pa // 4 and ub == pb:
            return (c, r, i)
    return f"patterns {pa // 4}, {pb}: no image"


def compose_sprites(img: list[list[int]], vram: bytes, sat_addr: int, ents: list) -> None:
    """Draws the SAT's sprites (mode 2, 16 x 16: patterns at 1D800h, colours at the SAT - 200h) over
    img as the VDP shows them (sprite 0 in front; Y + 1 is the first line)."""
    col = sat_addr - 0x200
    for k in reversed(range(len(ents))):
        y, x, pat = ents[k]
        base = 0x1D800 + 32 * (pat >> 2)
        for ly in range(16):
            c = vram[col + 16 * k + ly] & 15
            sy = (y + 1 + ly) & 255
            if sy >= H:
                continue
            for lx in range(16):
                byte = vram[base + ly + (16 if lx >= 8 else 0)]
                if byte >> (7 - (lx & 7)) & 1 and 0 <= x + lx < W and c:
                    img[sy][x + lx] = c


def still(paths: list[Path]) -> int:
    p = puzl()
    bad = 0
    for path in paths:
        d = path.read_bytes()
        vram, ram = d[:0x20000], d[0x20000:0x24000]
        regs = d[0x24000:0x24040]
        lp = ram[3] | ram[4] << 8
        lregs, gframe = parse_list(ram[lp - 0xC000:lp - 0xC000 + 32])
        r2, r5 = lregs.get(2), lregs.get(5)
        page = {0x1F: 0, 0x3F: 1}.get(r2)
        if page is None:
            print(f"{path.name}: the list shows R#2 = {r2} (fe_text's or none): not a stage page")
            bad += 1
            continue
        state = ram[RD_ST[page] - 0xC000:RD_ST[page] - 0xC000 + msxpuzl.ST_LEN]
        sat_addr = ((regs[11] & 3) << 15) | ((r5 & 0xFC) << 7)
        ents = sat_entries(vram[sat_addr:sat_addr + 32])
        cur = cursor_of(p, ents)
        if isinstance(cur, str):
            print(f"{path.name}: FAIL: the SAT: {cur}")
            bad += 1
            continue
        want = p.render(bytes(state), cur)
        got = page_pixels(vram[page * 0x8000:page * 0x8000 + 20736])
        compose_sprites(got, vram, sat_addr, ents)
        diffs = [(x, y) for y in range(H) for x in range(W) if got[y][x] != want[y][x]]
        drawn = sorted({k for k, i, v in msxpuzl.state_items(bytes(state))})
        pal0 = all(v == 0 for v in d[0x24040:0x24060][2:])
        print(f"{path.name}: $B00 {ram[0x1000] | ram[0x1001] << 8} list $B00 {gframe} page {page} R#5 {r5:02X} "
              f"cursor {cur} TV {state[0] if state[0] != 255 else '-'} drawn {','.join(drawn)}"
              f"{' (palette black)' if pal0 else ''}: "
              + ("equal to the render" if not diffs else f"FAIL: {len(diffs)} pixels differ, first {diffs[:4]}"))
        bad += bool(diffs)
    print(f"{len(paths)} snapshot(s), {bad} with differences")
    return 1 if bad else 0


def elements(p: msxpuzl.Puzl):
    """Per element (state index): its rectangle and its images (value -> pixels; 'static' too)."""
    v = p.vram[1]
    static = v.rows(0, 0, W, H)
    out = []
    for e in range(msxpuzl.ST_LEN):
        kind = next(k for k, n in msxpuzl.STATE if msxpuzl.ST[k] <= e < msxpuzl.ST[k] + n)
        rng = msxpuzl.ST_RANGE[kind]
        imgs, rect = {}, None
        for val in range(rng):
            st = bytearray([msxpuzl.NONE] * msxpuzl.ST_LEN)
            st[e] = val
            (sx, sy, dx, dy, w, h), = p.copies(bytes(st))
            rect = (dx, dy, w, h)
            imgs[val] = tuple(tuple(r) for r in v.rows(sx, sy, w, h))
        dx, dy, w, h = rect
        imgs["static"] = tuple(tuple(r[dx:dx + w]) for r in static[dy:dy + h])
        out.append((e, kind, rect, imgs))
    return out, static


def rec(path: Path, ref: Path | None, png: Path | None, start: int, every: int) -> int:
    p = puzl()
    els, static = elements(p)
    inside = [[False] * W for _ in range(H)]
    for e, kind, (dx, dy, w, h), imgs in els:
        for y in range(dy, dy + h):
            for x in range(dx, dx + w):
                inside[y][x] = True
    rows = {}
    if ref:
        for line in ref.read_text().splitlines():
            r = json.loads(line)
            if "frame" in r:
                rows[r["frame"]] = r
    data = path.read_bytes()
    n = len(data) // REC_LEN
    bad = torn = outside = curbad = 0
    seqs, faces, lastseq, pics, shown_frames = [], 0, None, 0, []
    prev = None
    changes = []
    for k in range(n):
        rec_b = data[k * REC_LEN:(k + 1) * REC_LEN]
        parts, o = {}, 0
        for name, ln in REC:
            parts[name] = rec_b[o:o + ln]
            o += ln
        lregs, gframe = parse_list(parts["list"])
        seq = parts["list"][0]
        newpic = seq != lastseq
        lastseq = seq
        r2 = lregs.get(2)
        page = {0x1F: 0, 0x3F: 1}.get(r2)
        if page is None:
            continue                            # (fe_text's list: not a stage picture)
        if not newpic and k % every:
            continue
        pics += newpic
        img = page_pixels(parts["page"])
        msg = []
        state_seen = []
        for e, kind, (dx, dy, w, h), imgs in els:
            blk = tuple(tuple(r[dx:dx + w]) for r in img[dy:dy + h])
            hit = [val for val, im in imgs.items() if im == blk]
            if not hit:
                torn += 1
                msg.append(f"{kind} {e}: no state")
            state_seen.append(hit[0] if hit else None)
        nout = sum(1 for y in range(H) for x in range(W) if not inside[y][x] and img[y][x] != static[y][x])
        if nout:
            outside += 1
            msg.append(f"{nout} pixels outside the elements differ from the screen")
        ents = sat_entries(parts["sat"])
        cur = cursor_of(p, ents)
        if isinstance(cur, str):
            curbad += 1
            msg.append(f"SAT: {cur}")
        elif ref and gframe in rows:
            r = rows[gframe]
            spr = r["spr"]
            want = None if spr >= 0x200 or spr < 0 else (r["col"] & 0xFFFF, r["row"] & 0xFFFF, spr // 0x40)
            if want != cur:
                curbad += 1
                msg.append(f"cursor {cur}, the bench's pass {gframe - 1}: {want}")
        if prev is not None and newpic:
            changes.append(sum(1 for a, b in zip(prev, state_seen) if a != b))
        if newpic:
            prev = state_seen
            shown_frames.append(gframe)
            tv = state_seen[0]
            faces += isinstance(tv, int) and (tv < 4 or tv == 8)
        if msg:
            bad += 1
            if bad <= 12:
                print(f"record {k} (list {seq}, $B00 {gframe}, page {page}): " + "; ".join(msg))
        if png and newpic and pics <= 400:
            pal = [bytes(v * 255 // 7 for v in (parts["pfpal"][2 * i] >> 4 & 7, parts["pfpal"][2 * i + 1] & 7,
                                                parts["pfpal"][2 * i] & 7)) for i in range(16)]
            if all(c == bytes(3) for c in pal):
                pal = [bytes(v * 255 // 7 for v in (q >> 8, q >> 4 & 15, q & 15)) for q in [0] * 16]
            pic = [r[:] for r in img]
            compose_sprites_rec(pic, parts, ents, p)
            write_png(png / f"pic{k:05d}.png", W, H, [b"".join(pal[c] for c in r) for r in pic])
    rate = f"{pics} pictures in {n} VBLANKs"
    print(f"{n} records: {rate}; torn/unknown blocks {torn}, pictures with pixels outside the elements "
          f"{outside}, cursor errors {curbad}; elements changed a picture: "
          f"{(sum(changes) / len(changes)) if changes else 0:.2f} on average")
    print(f"pictures with the face: {faces} of {pics}; $B00 of the pictures: {shown_frames[:3]}...{shown_frames[-3:]}")
    return 1 if bad else 0


def compose_sprites_rec(pic, parts, ents, p=None):
    """The record's SAT drawn with the converter's patterns (colours 15 and 14), sprite 0 in front."""
    cols = (15, 14)
    for k in reversed(range(min(2, len(ents)))):
        y, x, pat = ents[k]
        pp = p.pats[32 * (pat >> 2):32 * (pat >> 2) + 32]
        for ly in range(16):
            for lx in range(16):
                if pp[ly + (16 if lx >= 8 else 0)] >> (7 - (lx & 7)) & 1:
                    yy, xx = y + 1 + ly, x + lx
                    if 0 <= yy < H and 0 <= xx < W:
                        pic[yy][xx] = cols[k]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("still", "rec"))
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--ref", type=Path)
    ap.add_argument("--png", type=Path)
    ap.add_argument("--from", dest="start", type=int, default=0)
    ap.add_argument("--every", type=int, default=1)
    a = ap.parse_args()
    if a.mode == "still":
        return still(a.files)
    if a.png:
        a.png.mkdir(parents=True, exist_ok=True)
    return max(rec(f, a.ref, a.png, a.start, a.every) for f in a.files)


if __name__ == "__main__":
    raise SystemExit(main())
