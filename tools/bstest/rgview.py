#!/usr/bin/env python3
"""The shooting range's display checks (docs/RANGE.md 4.2 checks 2, 3 and 10; docs/HARNESS.md 5.18)
on tools/bstest/rgview.tcl's records.

usage:
  rgview.py still SNAP.bin [...] [--ref BENCH.jsonl --gen GEN] [--png DIR]
      the page on screen (the applied list's R#2) equals tools/msxrange.py's render of that page's
      shown state (msx.inc rgs0 / rgs1 in the snapshot's RAM): its 162 lines as built (index 1, the
      sheets' black, counts as 0: a front layer turns the scene's 0 into 1), its sprite set's SAT,
      the colour rows of the sprites in it, and the picture as shown (the sprites drawn from VRAM's
      patterns and colour rows, then R#18's shift); the list's R#18 is the state's (s - c) & 15; the
      view equals the converter's model of the Amiga's own composition (msxrange.py compare: 0
      pixels, quirk 4's apart). With --ref (the bench's trace of the drive, tools/amigaemu.py frng
      --trace-ram) and --gen (the build's gen folder: range.inc, range_tab.inc), the state is what
      the original drew in the pass before the one it was taken at (pass 0: rg_show's, nothing drawn).
      --png writes each snapshot's whole screen, 2 x 2 (the play area as shown, the HUD below)
  rgview.py rec REC.bin [--ref BENCH.jsonl --gen GEN] [--png DIR] [--pngmax N]
      every recorded VBLANK whose list shows a stage page: the page equals the render of its shown
      state (no torn element: every element shows one state, the state of one pass), the list's R#18
      is the state's (s - c) & 15, the SAT is the
      state's (at most 31 entries, at most 3 sprites on a line, every sprite whole in lines
      0-157), no pixel outside the elements of two pictures shown in a row changes (frame-to-frame
      coherence, compared in scene coordinates), with --ref each picture's state is the bench's for
      its pass; reports the pictures, their passes and the crosshair's line outside the view (the
      camera's job, docs/RANGE.md step 9). --png writes the first N pictures (graded palette from
      the record's pf_pal; black ones in the plain palette)
  rgview.py rate RATE.txt [...] [--hz 50|60]
      rgview.tcl rgv_rate_job's log: passes a second, the VBLANK steps between passes (50 Hz: all 1;
      60 Hz: four 1s and one 2 in every 5: fs_div's skip; the rate from the file name's "_eu" when
      --hz is not given), the late passes, the T-states of each pass's work (hud_keep, sec_tick,
      fr_frame, rg_feed) and of fr_frame and rg_feed alone, the active CPU
Exit 0 when every check passed.

A snapshot (hz7.tcl hz7_snap) is VRAM 128 KiB, RAM C000h-FFFFh, the 64 VDP registers and the
palette; a record (rgview.tcl rgv_pic) is REC's parts one after the other, a VBLANK each. Reads
build/extracted/files/FRNG_15.bin of the repository this file is in (tools/bstest/).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import msxrange  # noqa: E402
from planar import write_png  # noqa: E402

W, H = 256, 162
RGS = (0xEE40, 0xEE68)                          # msx.inc rgs0, rgs1: RG_ST_LEN bytes, then the pass
ST_LEN = msxrange.ST_LEN
RGS_LEN = ST_LEN + 2
R2_PAGE = {0x1F: 0, 0x3F: 1}
R8_SPR_ON = 0x08                                # msx.inc: a stage list (fe_text's has the sprites off)
SPR_PAT = 0x1D800
REC = [("regs", 64), ("page", 20736), ("sat", 128), ("pfpal", 32), ("list", 32), ("c0", 256), ("c6", 256),
       ("d0", 256), ("ee", 512)]
REC_LEN = sum(n for _, n in REC)
NORM = bytes([0, 0] + list(range(2, 256)))      # the sheets' black (index 1) is the scene's (0)
HZ = 3579545


def model() -> msxrange.Range:
    frng = msxrange.decrunch((ROOT / "build/extracted/files/FRNG_15.bin").read_bytes())
    return msxrange.Range(frng, sweep=False)


def page_rows(data: bytes) -> list[bytes]:
    """162 lines of 256 colour indices from SCREEN 5 bytes (the left pixel in the high nibble)."""
    out = []
    for y in range(H):
        line = data[128 * y:128 * y + 128]
        r = bytearray(W)
        r[0::2] = bytes(b >> 4 for b in line)
        r[1::2] = bytes(b & 15 for b in line)
        out.append(bytes(r))
    return out


def parse_list(b: bytes) -> tuple[dict, int]:
    n = b[1]
    regs = {b[2 + i + 1] & 0x3F: b[2 + i] for i in range(0, n, 2)}
    tail = 2 + n
    return regs, b[tail + 4] | b[tail + 5] << 8


def sat_entries(sat: bytes) -> list[tuple[int, int, int, int]]:
    out = []
    for k in range(32):
        e = tuple(sat[4 * k:4 * k + 4])
        if e[0] == msxrange.SAT_END:
            break
        out.append(e)
    return out


def want_sat(rg: msxrange.Range, st: msxrange.State) -> list[tuple[int, int, int, int]]:
    return [(y, x, 4 * k, 0) for y, x, k in rg.sat(st)]


def sat_problems(ents: list) -> list[str]:
    """At most 31 entries with the terminator, at most 3 sprites on a line, every sprite a line
    pattern (0-15) whose lines all lie in 0..RG_SPR_LINES - 1."""
    out = []
    if len(ents) > msxrange.SPR_MAX:
        out.append(f"{len(ents)} sprites")
    count = [0] * 256
    for y, x, p, e3 in ents:
        k = p >> 2
        if p & 3 or k >= msxrange.LINE_PATS or e3:
            out.append(f"entry {(y, x, p, e3)}")
            continue
        top = (y + 1) & 255
        if top + k >= msxrange.SPR_LINES:
            out.append(f"a sprite cut: lines {top}-{top + k}")
        for j in range(k + 1):
            count[(top + j) & 255] += 1
    most = max(count)
    if most > msxrange.SPR_PER_LINE:
        out.append(f"{most} sprites on line {count.index(most)}")
    return out


def compose(pic: list[bytearray], vram: bytes, sat_addr: int, ents: list) -> list[str]:
    """Draws the SAT's sprites over pic as the VDP shows them (mode 2, 16 x 16: patterns at SPR_PAT,
    colour rows at the SAT - 200h; sprite 0 in front; Y + 1 the first line) -> problems with the
    colour rows (each row of a sprite in the SAT must be RG_C_GREEN: no EC, CC or IC bit)."""
    bad = []
    col = sat_addr - 0x200
    for k in reversed(range(len(ents))):
        y, x, pat = ents[k][:3]
        rows = vram[col + 16 * k:col + 16 * k + 16]
        if any(c != msxrange.GREEN for c in rows):
            bad.append(f"sprite {k}'s colour rows {rows.hex()}")
        base = SPR_PAT + 8 * pat
        for ly in range(16):
            c = rows[ly] & 15
            sy = (y + 1 + ly) & 255
            if sy >= H or not c:
                continue
            left, right = vram[base + ly], vram[base + 16 + ly]
            for lx in range(16):
                b = (left if lx < 8 else right) >> (7 - (lx & 7)) & 1
                if b and 0 <= x + lx < W:
                    pic[sy][x + lx] = c
    return bad


def shift_rows(pic: list[bytearray], shift: int) -> list[bytearray]:
    """R#18's horizontal adjust: the picture moved right by shift (the uncovered columns colour 0)."""
    if shift > 0:
        return [bytearray(shift) + r[:W - shift] for r in pic]
    if shift < 0:
        return [r[-shift:] + bytearray(-shift) for r in pic]
    return pic


def ndiff(a: list, b: list) -> list[tuple[int, int]]:
    out = []
    for y in range(H):
        ra, rb = bytes(a[y]).translate(NORM), bytes(b[y]).translate(NORM)
        if ra != rb:
            out += [(x, y) for x in range(W) if ra[x] != rb[x]]
    return out


# ----- what the original drew, from the bench's trace (docs/RANGE.md 3.3's wanted state)

class Bench:
    """Per pass P the wanted state the MSX takes at P's start (msx/frng.asm fr_frame's rg_want after
    pass P - 1), worked out from the bench's rows (impl step 7's wantcheck): the pop-ups each slot's
    script drew ($1F5F8: the descriptor's position and graphic, D0 = +2, D1 = +4 + the slot's offset
    of the row before; swapped when +$B), the big target ($BA8: $BAA's picture, $BAE, $BB0, $1F46C),
    the dissolve ($B3E: $1F8E8[$B46]'s picture, $B56, $B66), the crosshair ($B9A, $B9E), the box
    (n = $1EB4A of the row before, its centre (4 + $B9A) & FFF0h and row $B9E of the row before)."""

    def __init__(self, ref: Path, gen: Path):
        inc = (gen / "range.inc").read_text()
        tab = (gen / "range_tab.inc").read_text()
        eq = {m[1]: int(m[2], 0) for m in re.finditer(r"^(\w+):\s+equ\s+(-?\w+)", inc, re.M)}
        self.pic = {k[7:].lower(): v for k, v in eq.items() if re.fullmatch(r"RG_PIC_[0-9A-F]{5}", k)}

        def dws(label):
            m = re.search(label + r":.*?\n((?:\s+d[wb] [^\n]*\n)+)", tab, re.S)
            return [int(x, 0) for x in re.findall(r"0x[0-9A-Fa-f]+|\b\d+\b",
                                                  "".join(ln.split(";")[0].replace("dw", "").replace("db", "")
                                                          for ln in m[1].splitlines()))]
        fxg = dws("rgt_fx_gfx")
        self.fxgfx = [fxg[2 * i] << 16 | fxg[2 * i + 1] for i in range(len(fxg) // 2)]
        self.kinds = dws("rgt_kind")
        self.descofs = [None if x == 0xFFFF else x - eq["RG_FC_1F60E"] for x in dws("rgt_desc")]
        self.rows = {}
        for line in ref.read_text().splitlines():
            if line.startswith('{"frame"'):
                r = json.loads(line)
                self.rows[r["frame"]] = r

    def state(self, k: int) -> bytes | None:
        """The wanted state (RG_ST_LEN bytes, the camera at its start) at pass k's start."""
        if k not in self.rows or k - 1 not in self.rows:
            return None
        r, p = self.rows[k], self.rows[k - 1]
        v, vp = bytes.fromhex(r["vars"]), bytes.fromhex(p["vars"])

        def w16(b, a):
            return b[a] << 8 | b[a + 1]

        def l32(b, a):
            return w16(b, a) << 16 | w16(b, a + 2)

        def V(a):
            return a - 0xB00
        code = {int(a, 16): bytes.fromhex(h) for a, h in r["code"].items()}
        codep = {int(a, 16): bytes.fromhex(h) for a, h in p["code"].items()}
        d = code[0x1F60E]
        pops = []
        for a3 in (0xB2E, 0xB32):
            scr = v[V(a3 + 8)]
            if scr and self.kinds[scr] == msxrange.K_POPUP and v[V(a3)]:
                off = self.descofs[scr]
                x, y = w16(d, off + 2), (w16(d, off + 4) + w16(vp, V(a3 - 0x1E))) & 0xFFFF
                if d[off + 0xB]:
                    x, y = y, x
                pops.append((d[off], self.pic[f"{l32(d, off + 0xE):05x}"], x, y))
            else:
                pops.append(None)
        big = (self.pic[f"{l32(v, V(0xBAA)):05x}"], w16(v, V(0xBAE)), w16(v, V(0xBB0)), w16(code[0x1F46C], 0)) \
            if w16(v, V(0xBA8)) else None
        fx = (self.pic[f"{self.fxgfx[v[V(0xB46)]]:05x}"], w16(v, V(0xB56)), w16(v, V(0xB66))) if v[V(0xB3E)] else None
        n = msxrange.s16(w16(codep[0x1EB46], 4))
        box = (n, (4 + w16(vp, V(0xB9A))) & 0xFFF0, w16(vp, V(0xB9E))) if n > 0 else None
        st = msxrange.State(msxrange.CAM_START, msxrange.CAM_START, pops, big, fx, (w16(v, V(0xB9A)), w16(v, V(0xB9E))), box)
        return st.to_bytes()


def same_state(a: bytes, b: bytes) -> bool:
    """Two shown states that draw the same: the box's n 0 and RG_NONE both mean none; C and S apart."""
    sa, sb = msxrange.State.from_bytes(a), msxrange.State.from_bytes(b)
    return all(getattr(sa, f) == getattr(sb, f) for f in ("pops", "big", "fx", "cross", "box"))


# ----- stills

def rgb(lo: int, hi: int) -> bytes:
    return bytes(v * 255 // 7 for v in (lo >> 4 & 7, hi & 7, lo & 7))


def screen_png(out: Path, pic: list, vram: bytes, ram: bytes) -> None:
    """The whole screen 2 x 2 (shots.py's): the play area as shown (its colours pf_pal), the 5 blank
    lines, the HUD (page 3 from line 208, the split's colours SR_PAL)."""
    pf = ram[0xEA40 - 0xC000:0xEA40 - 0xC000 + 32]
    hp = ram[0xEA22 - 0xC000:0xEA22 - 0xC000 + 30]
    pal = [bytes(3)] + [rgb(pf[2 * i], pf[2 * i + 1]) for i in range(1, 16)]
    hud = [bytes(3)] + [rgb(hp[2 * i - 2], hp[2 * i - 1]) for i in range(1, 16)]
    rows = [b"".join(pal[c] * 2 for c in r) for r in pic]
    rows += [bytes(3 * 512)] * 5
    for y in range(45):
        line = vram[0x1E800 + 128 * y:0x1E800 + 128 * y + 128]
        rows.append(b"".join(hud[b >> 4] * 2 + hud[b & 15] * 2 for b in line))
    write_png(out, 512, 2 * len(rows), [r for r in rows for _ in (0, 1)])


def still(paths: list[Path], bench: Bench | None, png: Path | None = None) -> int:
    rg = model()
    bad = 0
    for path in paths:
        d = path.read_bytes()
        vram, ram, vregs = d[:0x20000], d[0x20000:0x24000], d[0x24000:0x24040]
        lp = ram[3] | ram[4] << 8
        lregs, gframe = parse_list(ram[lp - 0xC000:lp - 0xC000 + 32])
        r2, r5, r18, r8 = lregs.get(2), lregs.get(5), lregs.get(18, 0), lregs.get(8)
        page = R2_PAGE.get(r2)
        if page is None:
            print(f"{path.name}: the list shows R#2 = {r2}: not a display page")
            bad += 1
            continue
        raw = ram[RGS[page] - 0xC000:RGS[page] - 0xC000 + RGS_LEN]
        st = msxrange.State.from_bytes(raw[:ST_LEN])
        spass = raw[ST_LEN] | raw[ST_LEN + 1] << 8
        msg = []
        if (r18 & 15) != ((st.s - st.c) & 15) or r18 >> 4:
            msg.append(f"R#18 {r18:02X}h for c {st.c} s {st.s}")
        want_pic, want_page = rg.shown(st)
        got_page = page_rows(vram[page * 0x8000:page * 0x8000 + 20736])
        dp = ndiff([bytearray(r) for r in got_page], want_page)
        if dp:
            msg.append(f"the page: {len(dp)} pixels differ, first {dp[:4]}")
        sprites = r8 == R8_SPR_ON
        sat_addr = ((vregs[11] & 3) << 15) | ((r5 & 0xFC) << 7)
        ents = sat_entries(vram[sat_addr:sat_addr + 128])
        if sprites:
            if ents != want_sat(rg, st):
                msg.append(f"the SAT {ents[:3]}... ({len(ents)}), the state's {want_sat(rg, st)[:3]}... "
                           f"({len(want_sat(rg, st))})")
            msg += sat_problems(ents)
        pic = [bytearray(r) for r in got_page]
        if sprites:
            msg += compose(pic, vram, sat_addr, ents)
            ref_pic = want_pic
        else:
            ref_pic = [bytearray(r) for r in want_page]   # (the intro's list: no sprites, R#18 0)
        pic = shift_rows(pic, msxrange.r18_shift(r18))
        ds = ndiff(pic, ref_pic)
        if ds:
            msg.append(f"the picture: {len(ds)} pixels differ, first {ds[:4]}")
        amiga, quirk = rg.compare(st)
        if amiga:
            msg.append(f"the view: {amiga} pixels differ from the Amiga's composition")
        if bench and spass == 0:
            if any((st.pops[0], st.pops[1], st.big, st.fx, st.cross, st.box)):
                msg.append("the entry's state (pass 0) has something drawn")
        elif bench:
            exp = bench.state(spass)
            if exp is None:
                msg.append(f"no bench rows for pass {spass}")
            elif not same_state(exp, raw[:ST_LEN]):
                msg.append(f"the state is not the bench's for pass {spass}: {msxrange.State.from_bytes(exp).__dict__}")
        drawn = [k for k, v in (("pop-up 0", st.pops[0]), ("pop-up 1", st.pops[1]), ("big", st.big),
                                ("dissolve", st.fx), ("crosshair", st.cross), ("box", st.box)) if v]
        pal0 = all(v == 0 for v in ram[0xEA40 - 0xC000 + 2:0xEA40 - 0xC000 + 32])
        print(f"{path.name}: $B00 {ram[0x1000] | ram[0x1001] << 8}, page {page} (the state of pass {spass}), "
              f"c {st.c} s {st.s} R#18 {r18:02X}h, {len(ents) if sprites else 'no'} sprites, "
              f"{', '.join(drawn) or 'nothing'} drawn{', quirk 4: %d' % quirk if quirk else ''}"
              f"{' (palette black)' if pal0 else ''}{'' if sprites else ' (the intro list)'}: "
              + ("equal to the render" if not msg else "FAIL: " + "; ".join(msg)))
        bad += bool(msg)
        if png:
            screen_png(png / f"{path.stem}.png", pic, vram, ram)
    print(f"{len(paths)} snapshot(s), {bad} with differences")
    return 1 if bad else 0


# ----- records

def element_mask(rg: msxrange.Range, st: msxrange.State) -> list[tuple[int, int, int, int]]:
    """Every rectangle (x0, y0, x1, y1 exclusive, Amiga coordinates) a state's elements may change:
    the pop-ups' positions, the big target's and the dissolve's blocks, the lines' rows."""
    out = []
    for p in st.pops:
        if p:
            px, py, pw, ph = rg.places[p[0]]
            out.append((px, py, px + pw, py + ph))
    for e in (st.big, st.fx):
        if e:
            tx, ty, tw, th = rg.trim[rg.pics[e[0]]]
            x0, y0 = e[1] - msxrange.XBIAS + tx, e[2] + ty
            out.append((x0, y0, x0 + tw, y0 + th))
    for y, x0, x1 in rg.lines(st):
        out.append((x0, y, x1, y + 1))
    return out


def coherence(rg, sa, ia, sb, ib) -> int:
    """Pixels of two pictures shown in a row (states sa, sb; their pages' lines ia, ib) that differ
    outside both states' elements, compared in scene coordinates (screen x + s) as shown (R#18's
    shift applied); the columns the shift uncovers are left out."""
    m = [bytearray(msxrange.AW) for _ in range(H)]
    for x0, y0, x1, y1 in element_mask(rg, sa) + element_mask(rg, sb):
        for y in range(max(y0 - msxrange.TOP, 0), min(y1 - msxrange.TOP, H)):
            m[y][max(x0, 0):max(min(x1, msxrange.AW), 0)] = b"\1" * (max(min(x1, msxrange.AW), 0) - max(x0, 0))
    va = shift_rows([bytearray(r) for r in ia], sa.c - sa.s)
    vb = shift_rows([bytearray(r) for r in ib], sb.c - sb.s)
    lo_a, hi_a = max(0, sa.c - sa.s), min(W, W + sa.c - sa.s)
    lo_b, hi_b = max(0, sb.c - sb.s), min(W, W + sb.c - sb.s)
    n = 0
    for y in range(H):
        ra, rb = bytes(va[y]).translate(NORM), bytes(vb[y]).translate(NORM)
        if ra == rb and sa.s == sb.s:
            continue
        for x in range(lo_b, hi_b):
            sx = x + sb.s
            xa = sx - sa.s
            if lo_a <= xa < hi_a and not m[y][sx] and ra[xa] != rb[x]:
                n += 1
    return n


def draw_lines(pic: list[bytearray], ents: list) -> None:
    """The SAT's line sprites (column 0 of pattern k: k + 1 lines from Y + 1) in colour 15."""
    for y, x, p, _ in ents:
        for j in range((p >> 2) + 1):
            yy = (y + 1 + j) & 255
            if yy < H and 0 <= x < W:
                pic[yy][x] = msxrange.GREEN


def rec(path: Path, bench: Bench | None, png: Path | None, pngmax: int) -> int:
    rg = model()
    data = path.read_bytes()
    n = len(data) // REC_LEN
    renders = {}
    torn = satbad = outside = benchbad = stage = hidden = regbad = 0
    pics, passes, lastseq, prev, outview, shown_from = 0, [], None, None, 0, None
    bad_lines = []
    for k in range(n):
        b = data[k * REC_LEN:(k + 1) * REC_LEN]
        parts, o = {}, 0
        for name, ln in REC:
            parts[name] = b[o:o + ln]
            o += ln
        lregs, gframe = parse_list(parts["list"])
        seq = parts["list"][0]
        page = R2_PAGE.get(lregs.get(2))
        if page is None or lregs.get(8) != R8_SPR_ON:
            prev = None                                 # (fe_text's list: not a stage picture)
            lastseq = seq
            continue
        stage += 1
        newpic = seq != lastseq
        lastseq = seq
        raw = parts["ee"][RGS[page] - 0xEE00:RGS[page] - 0xEE00 + RGS_LEN]
        st = msxrange.State.from_bytes(raw[:ST_LEN])
        spass = raw[ST_LEN] | raw[ST_LEN + 1] << 8
        key = bytes(raw[:ST_LEN])
        if key not in renders:
            renders[key] = rg.shown(st)
        want_pic, want_page = renders[key]
        img = page_rows(parts["page"])
        msg = []
        r18 = lregs.get(18, 0)
        if r18 != (st.s - st.c) & 15:
            regbad += 1
            msg.append(f"R#18 {r18:02X}h for c {st.c} s {st.s}")
        dp = ndiff([bytearray(r) for r in img], want_page)
        if dp:
            torn += 1
            msg.append(f"page {page}: {len(dp)} pixels differ from its state's render, first {dp[:3]}")
        ents = sat_entries(parts["sat"])
        sp = sat_problems(ents)
        black = not any(parts["pfpal"][2:])
        if not ents and black and ents != want_sat(rg, st):
            hidden += 1                                 # (rg_hide: the SATs emptied, the palette black)
        elif ents != want_sat(rg, st) or sp:
            satbad += 1
            msg.append(f"SAT: {'; '.join(sp) or 'not the state'}'s")
        if st.cross and not 0 <= st.cross[0] - msxrange.LINE_DX - st.s < W:
            outview += newpic
        if bench and newpic:
            exp = bench.state(spass)
            if exp is None or not same_state(exp, raw[:ST_LEN]):
                benchbad += 1
                msg.append(f"the state is not the bench's for pass {spass}")
        if prev is not None and newpic:
            nout = coherence(rg, prev[0], prev[1], st, img)
            if nout:
                outside += 1
                msg.append(f"{nout} pixels outside the elements changed")
        if newpic:
            pics += 1
            passes.append(spass)
            prev = (st, img)
            if shown_from is None:
                shown_from = k
            if png and pics <= pngmax:
                pal = parts["pfpal"]
                cols = [bytes(v * 255 // 7 for v in (pal[2 * i] >> 4 & 7, pal[2 * i + 1] & 7, pal[2 * i] & 7))
                        for i in range(16)]
                if all(c == bytes(3) for c in cols[1:]):
                    cols = [bytes(msxrange.rgb24(c, True)) for c in rg.pal[1]]
                pic = [bytearray(r) for r in img]
                draw_lines(pic, ents)
                pic = shift_rows(pic, msxrange.r18_shift(lregs.get(18, 0)))
                write_png(png / f"pic{pics:04d}_p{spass:04d}.png", W * 2, H * 2,
                          [b"".join(cols[v] * 2 for v in r) for r in pic for _ in range(2)])
        if msg:
            bad_lines.append(f"record {k} (list {seq}, $B00 {gframe}, page {page}, state of pass {spass}): "
                             + "; ".join(msg))
    for line in bad_lines[:12]:
        print(line)
    steps = Counter(b - a for a, b in zip(passes, passes[1:]))
    print(f"{n} records, {stage} with a stage list: {pics} pictures (passes {passes[:1]}..{passes[-1:]}, "
          f"pass steps {dict(sorted(steps.items()))}); torn {torn}, SAT errors {satbad}, pictures with "
          f"pixels outside the elements changed {outside}, states not the bench's {benchbad}, R#18 not the "
          f"state's (s - c) & 15 {regbad}; {hidden} VBLANKs "
          f"with the SATs emptied and the palette black (rg_hide); "
          f"the crosshair's line outside the view in {outview} pictures (the camera: step 9)")
    return 1 if torn or satbad or outside or benchbad or regbad else 0


# ----- the pass rate

def rate(paths: list[Path], hz: int | None) -> int:
    bad = 0
    for path in paths:
        rows = []
        for line in path.read_text().splitlines():
            p = line.split()
            if len(p) == 6:
                rows.append((int(p[0]), float(p[1]), float(p[2]), float(p[3]), float(p[4]), p[5]))
        if len(rows) < 2:
            print(f"{path.name}: no rows")
            bad += 1
            continue
        f = hz or (50 if "_eu" in path.name else 60)
        steps = [(b[0] - a[0]) & 0xFF for a, b in zip(rows, rows[1:])]
        if f == 50:
            late = [i + 1 for i, s in enumerate(steps) if s != 1]
        else:
            late = [i + 1 for i, s in enumerate(steps) if s not in (1, 2)]
            twos = [i for i, s in enumerate(steps) if s == 2]
            late += [twos[k + 1] + 1 for k in range(len(twos) - 1) if twos[k + 1] - twos[k] != 5]
        work = [((r[4] - r[1]) * HZ, i) for i, r in enumerate(rows) if r[1] > 0]
        frame = [(r[3] - r[2]) * HZ for r in rows]
        feed = [(r[4] - r[3]) * HZ for r in rows]
        wmax, wi = max(work)
        rate_ = (len(rows) - 1) / (rows[-1][2] - rows[0][2])
        print(f"{path.name}: {len(rows)} passes, {rate_:.3f} passes/s; VBLANK steps {dict(sorted(Counter(steps).items()))};"
              f" late passes {len(sorted(set(late)))}{(' at ' + str(sorted(set(late))[:6])) if late else ''}; "
              f"work max {wmax:.0f} T (pass {wi}), mean {sum(w for w, _ in work) / len(work):.0f} T; fr_frame max "
              f"{max(frame):.0f} T; rg_feed after the pass max {max(feed):.0f} T, mean {sum(feed) / len(feed):.0f} T; "
              f"a VBLANK: {HZ / f:.0f} T; cpu {dict(Counter(r[5] for r in rows))}")
        bad += bool(late)
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=("still", "rec", "rate"))
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--ref", type=Path, help="the bench's trace of the drive (build/emu/fr_NAME_ram.jsonl)")
    ap.add_argument("--gen", type=Path, help="the build's gen folder (range.inc, range_tab.inc), with --ref")
    ap.add_argument("--png", type=Path)
    ap.add_argument("--pngmax", type=int, default=60)
    ap.add_argument("--hz", type=int, choices=(50, 60))
    a = ap.parse_args()
    if a.mode == "rate":
        return rate(a.files, a.hz)
    bench = None
    if a.ref:
        if not a.gen:
            ap.error("--ref needs --gen")
        bench = Bench(a.ref, a.gen)
    if a.png:
        a.png.mkdir(parents=True, exist_ok=True)
    if a.mode == "still":
        return still(a.files, bench, a.png)
    return max(rec(f, bench, a.png, a.pngmax) for f in a.files)


if __name__ == "__main__":
    raise SystemExit(main())
