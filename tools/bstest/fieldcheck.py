"""Pictures recorded with the play-field engine's state (sess_rec_field.tcl: rc2_jumprec's record
+ page-0 RAM 0600h-09FFh): every play-area pixel no sprite covers against the expected picture:
the tile (map + patches) under it, or the play-field BOB the shown page's list (fb_dr0/fb_dr1)
has there (the first in the list on top, as fb_bobs composes). A pixel matching the previous
record's list passes too (the engine composes changes over a few pictures). Writes a contact
sheet (2x, mismatches magenta). usage: fieldcheck.py RECDIR LEVEL_PREFIX OUT.png [--level 2|3]

Level 1's scratch tool of 2026-10-21/22 (the play-field engine's checks), brought into the harness
at level 2's step 0 (the plan's 4.2) from its copy of 2026-10-23 (build/perf_2026-10-23). The
checks are that copy's; changed only so that the harness's rules hold (tests/test_bstest.py): it
imports without numpy or the build's files (they load when it runs: load()), and it finds the
repository from its own place (a relative LEVEL_PREFIX is the repository's); and it reads the map
patches as they have been since 2026-10-25 (46fa12c: two pools by row parity, MP_B at F500h, which
rc2_jumprec's record carries since): patch_map follows tools/recframes.py tile_at, and the record
is rc2_jumprec's (tools/recframes.py REC) + RAM 0600h-09FFh and F240h-F27Fh (EXTRA); a file of
another length is counted as skipped. Needs numpy (tools/msxsprites.py): run it with the venv's
Python. The records: tools/bstest/l2base.tcl l2b_fd_setup.

--level 2 (the level-2 plan's step 13): level 2's play-field frames (build/msx/sprites_l2.json "field",
sprites_l2_field.inc: FIELD_LATE, the dynamic frames), their pixels as the ROM uploads them
(tools/msxframe.py FieldLooks: its atlas and the dynamic frames); LEVEL_PREFIX build/msx/level2. Its
vats stay as the static map shows them until the vats' display (step 14) draws them. Level 1's check
is unchanged. A hostage-like BOB (a hostage, types 2, 14 and 16's bodies) ahead or behind counts as
torn per object: its old and new frames (the shown and the newest lists' entries whose boxes meet)
with pixels of both lists; two of them, one a picture ahead of the other, are each whole (level 1's
check, whose verdicts are compared with level 2's base, takes the picture as a whole).

Level 2's vats (its step 14, the plan's 4.2 checks 2 and 8): a record may carry RAM F012h-F0E6h after
EXTRA (VATX: vat_shown, vat_disp, vat_chg; tools/bstest/l2base.tcl l2b_fd_setup). Then every vat cell
is expected at the look its column has on the page shown (vat_disp's nibble, tools/mapcmp.py vat_look),
so that a column showing two looks or a half-drawn one differs ("CLASS picture vat-look"); and a column
seen in two pictures in a row never shows an older look than the one before ("CLASS picture vat-older":
when it changes look, the new look's age, the latest record up to then in which vat_shown became it, is
before the age of its change before; the looks recur every cycle, so a look kept unchanged keeps its
age and the first one a column shows has none). A column the page has not drawn (nibble 0: vat_look
None) is expected at the map's own tile, as any cell, and is in neither vat class: so it is in the
product (VAT_ANIM=0, the vats as the map's static images) for every column; a VAT_ANIM=1 build draws
a visible column's nibble with its first cell (msx/field.asm vat_tile). The summary line counts both
kinds of columns seen.

--level 3 (the level-3 plan's step C): level 3's play-field frames (build/msx/sprites_l3.json "field",
sprites_l3_field.inc) as its ROM holds them (tools/msxframe.py FieldLooks: its static atlas, the smoke in
level 1's dynamic frames, its frame cache's frames, sprites_l3_fc.bin); a list entry's frame with bit 7
is that frame's white copy (a hit flash, msx/bob.asm fb_add; its normal look when it has none), judged
as the frame itself is (one picture ahead allowed, never behind or torn); LEVEL_PREFIX build/msx/level3."""
import json
import struct
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import mapcmp  # noqa: E402
import recframes as rf  # noqa: E402
from msxscreen import render, sprite_line  # noqa: E402
from planar import write_png  # noqa: E402

EXTRA = 0x440
VATX = 0xD5                                     # (RAM F012h-F0E6h: vat_shown, vat_disp, vat_chg)
meta = FT = atlas = np = msxsprites = _RAM = _MAIN = _JP = _PAL = _BGPAL = _NEAR = INC = None
FIELD_Y0 = FIELD_LATE = DYN0 = DYN1 = None
_IMG = {}


LOOKS = None                                    # --level 2: tools/msxframe.py FieldLooks
VATS, VATS_N = None, 0                          # level 2's vats: tools/mapcmp.py vat_layout


def load(level=1):
    """The conversions the pictures are checked against (build/msx, build/ram, build/extracted) and
    numpy: read when the check runs, not when the module is imported."""
    global meta, FT, atlas, np, msxsprites, _RAM, _MAIN, _JP, _PAL, _BGPAL, _NEAR, INC
    global FIELD_Y0, FIELD_LATE, DYN0, DYN1, LOOKS
    import numpy as np
    import msxsprites
    b = ROOT / "build"
    if level in (2, 3):                         # (level 2's or 3's frames as its ROM holds them)
        from msxframe import FieldLooks
        LOOKS = FieldLooks(level, b / "msx/sprites")
        FT = dict(LOOKS.frames)
        if level == 3:                          # (bit 7: a frame's white copy, its look's pixels)
            FT.update({k | 0x80: dict(f, fid=k | 0x80) for k, f in LOOKS.frames.items()})
        INC = LOOKS.inc
        FIELD_Y0, FIELD_LATE = INC["FIELD_Y0"], INC["FIELD_LATE"]
        DYN0, DYN1 = INC["FIELD_DYN0"], INC["FIELD_DYN1"]
        return
    meta = json.loads((b / "msx/robocop.json").read_text())
    FT = {f["fid"]: f for f in meta["field"]}
    atlas = (b / "msx/robocop_field_vram.bin").read_bytes()   # (the atlas as VRAM holds it)
    _RAM = (b / "ram/level1_full.bin").read_bytes()
    _MAIN = (b / "extracted/boot/main_8000.bin").read_bytes()
    _JP = (b / "msx/robocop.pal").read_bytes()
    _PAL = np.array([[_JP[2 * i] >> 4, _JP[2 * i + 1] & 7, _JP[2 * i] & 7] for i in range(16)]) / 7
    _BGPAL = np.array([[0, 0, 0]] + [msxsprites.amiga_rgb(struct.unpack_from(">H", _MAIN, 0xFFF6 - 0x8000 + 2 * i)[0])
                                     for i in range(15)])
    _NEAR = msxsprites.nearest(_BGPAL, _PAL, 1)
    INC = {l.split(":")[0]: int(l.split("equ")[1].split()[0], 0) for l in
           (b / "msx/robocop_field.inc").read_text().splitlines() if ": equ" in l}
    FIELD_Y0 = INC["FIELD_Y0"]
    FIELD_LATE = INC["FIELD_LATE"]              # robocop_field.inc: lifts and the vehicle from here
    DYN0, DYN1 = INC["FIELD_DYN0"], INC["FIELD_DYN1"]   # the explosion and the smoke: never held


def frame_img(f):
    """The pixels a play-field frame draws (its "src": the frame shown), joint palette indices."""
    if LOOKS is not None:
        if f["fid"] not in _IMG:
            _IMG[f["fid"]] = np.array([list(r) for r in LOOKS.pixels(f["fid"])], dtype=np.uint8)
        return _IMG[f["fid"]]
    k = f["src"]
    if k not in _IMG:
        a, w, h = k.split(":")
        src = msxsprites.bob_image(_RAM, int(a, 16), int(w), int(h))
        _IMG[k] = np.where(src >= 0, _NEAR[np.clip(src, 0, 15)], 0)
    return _IMG[k]


VIS_PAGE = None


def atlas_px(x, y):
    b = atlas[y * 128 + x // 2]
    return (b >> 4) if x % 2 == 0 else b & 15


def vis_list(low):
    """The play-field BOBs of the list on screen (msx/tiles.asm fb_visrec, fb_vis at F248h)."""
    base = 0x400 + 8
    n = low[base]
    out = []
    for i in range(min(n, 8)):
        out.append(struct.unpack_from("<Bhh", low, base + 1 + 5 * i))
    return out


def field_list(low, page):
    base = (0x06D9 if page == 0 else 0x0712) - 0x0600
    n = low[base]
    if n == 0xFF:
        n = 0
    out = []
    for i in range(min(n, 8)):
        fi, wx, wy, _own = struct.unpack_from("<BhhH", low, base + 1 + 7 * i)
        out.append((fi, wx, wy))
    return out


def patch_map(patches):
    """{(row, col): tile} of every map patch (tiles.asm: per row a chain of patches in its row
    parity's pool; the record's patches as tools/recframes.py tile_at reads them)."""
    out = {}
    for row in range(256):
        p = patches[row]
        pool = rf.MP_POOL[row & 1]
        n = 0
        while p != 0xFF and n < 256:
            col = patches[pool + rf.MPF_COL + p]
            out[(row, col)] = patches[pool + rf.MPF_TILEL + p] | patches[pool + rf.MPF_TILEH + p] << 8
            p = patches[pool + rf.MPF_NEXT + p]
            n += 1
    return out


VOLATILE_N = 30                                 # records a changed cell stays volatile
DYN_HIST = 12                                   # (explosions and smoke: any step of the last DYN_HIST lists is fine)


def is_dyn(fid):
    return fid is not None and DYN0 <= (fid & 0x7F) < DYN1


def fid_base(fid):
    """A frame id without its white copy's mark (level 3: bit 7)."""
    return None if fid is None else fid & 0x7F


def bob_fid(lst, wx, wy):
    """The frame of the top BOB with a pixel at (wx, wy) in lst, or None."""
    for fi, bx, by in lst:
        f = FT.get(fi)
        if not f:
            continue
        dx, dy = wx - bx, wy - by
        if 0 <= dx < f["sw"] and 0 <= dy < f["sh"] and frame_img(f)[dy, dx]:
            return fi
    return None


def bob_ent(lst, wx, wy):
    """The list entry (frame, x, y) of the top BOB with a pixel at (wx, wy) in lst, or None."""
    for e in lst:
        f = FT.get(e[0])
        if not f:
            continue
        dx, dy = wx - e[1], wy - e[2]
        if 0 <= dx < f["sw"] and 0 <= dy < f["sh"] and frame_img(f)[dy, dx]:
            return e
    return None


def tear_note(shown, newest, lst, tlst, wx, wy):
    """A torn hostage pixel: its hostage BOBs (never a lift's, the vehicle's, an explosion's or the
    smoke's) of the shown list and of the newest one, into the picture's sets."""
    for s, L in ((shown, lst), (newest, tlst)):
        e = bob_ent(L, wx, wy)
        if e is not None and fid_base(e[0]) < FIELD_LATE and not is_dyn(e[0]):
            s.add(e)


def tear_objects(pix):
    """--level 2: the torn objects among a picture's hostage-like pixels (pix: (kind "old" or "new",
    the BOB entries of the shown and newest lists the pixel belongs to)): entries whose boxes meet
    are one object (its old and new frames); an object with pixels of both kinds is torn -> the
    pixels counted torn (per torn object the fewer kind)."""
    ents = sorted({e for _k, es in pix for e in es})
    up = {e: e for e in ents}

    def find(e):
        while up[e] != e:
            e = up[e]
        return e

    def box(e):
        f = FT[e[0]]
        return e[1], e[2], e[1] + f["sw"], e[2] + f["sh"]
    for i, a in enumerate(ents):
        for b in ents[i + 1:]:
            ax0, ay0, ax1, ay1 = box(a)
            bx0, by0, bx1, by1 = box(b)
            if ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1:
                up[find(a)] = find(b)
    n = {}
    for k, es in pix:
        for g in {find(e) for e in es}:
            n.setdefault(g, {"old": 0, "new": 0})[k] += 1
    return sum(min(c["old"], c["new"]) for c in n.values())


def tear_key(shown, newest):
    """A hostage tear's class: the hostage BOBs of the shown list and of the newest list that the
    torn pixels belong to ("fid@x,y", joined by "+"); the same BOBs in the same frames are the same
    tear whichever picture, VDP or timing shows it."""
    def side(s):
        return "+".join(f"{f}@{x},{y}" for f, x, y in sorted(s)) or "-"
    return f"shown={side(shown)} newest={side(newest)}"


def bob_at(lst, wx, wy):
    for fi, bx, by in lst:                      # the first in the list on top
        f = FT.get(fi)
        if not f:
            continue
        dx, dy = wx - bx, wy - by
        if 0 <= dx < f["sw"] and 0 <= dy < f["sh"]:
            c = int(frame_img(f)[dy, dx])
            if c:
                return c
    return None


def main():
    level = 1
    if len(sys.argv) == 6 and sys.argv[4] == "--level":
        level = int(sys.argv.pop(5))
        sys.argv.pop(4)
    if len(sys.argv) != 4 or level not in (1, 2, 3):
        sys.exit(__doc__.split("\n\n")[0])
    load(level)
    d, level, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    if not level.is_absolute():
        level = ROOT / level
    mp = level.with_suffix(".map").read_bytes()
    til = level.with_suffix(".til").read_bytes()
    files = sorted(p for p in d.glob("*.bin"))
    global VATS, VATS_N
    VATS = mapcmp.vat_layout(level) if level.name == "level2" else None
    VATS_N = len({v[0] for v in VATS["cells"].values()}) if VATS else 0
    vat_hist, vat_age, vat_older, vat_recs, vat_cols = {}, {}, 0, 0, set()
    vat_mcols = set()                           # (the vat columns seen at the map's own tile)
    vat_last = {}                               # (each column seen: the look it showed last)
    prev_low = None
    sheet, total_bad, pics_bad = [], 0, 0
    hist = []                                   # the last VOLATILE_N records' patch maps
    vhist = []                                  # the last DYN_HIST lists on screen
    dyn_lag = 0
    dyn_torn = 0
    skipped = 0
    wrong = 0
    for p in files:
        data = p.read_bytes()
        sp2 = len(data) in (rf.REC + 0x8000 + EXTRA, rf.REC + 0x8000 + EXTRA + VATX)
        if len(data) not in (rf.REC + EXTRA, rf.REC + 0x8000 + EXTRA, rf.REC + EXTRA + VATX,
                             rf.REC + 0x8000 + EXTRA + VATX):
            wrong += 1
            continue
        regs = list(data[:64])
        pal = list(data[64:96])
        pos = 96
        page = (regs[2] >> 5) & 3
        vram = bytearray(0x20000)
        base, size = ((page & 2) * 0x8000, 0x10000) if sp2 else (page * 0x8000, 0x8000)
        vram[base:base + size] = data[pos:pos + size]
        pos += size
        vram[0x1D800:0x20000] = data[pos:pos + 0x2800]
        pos += 0x2800
        ram = data[pos:pos + 0x1000]
        pos += 0x1000
        patches = data[pos:pos + 0x600 + 0x400]     # (0A00h-0FFFh, then MP_B F500h-F8FFh)
        pos += 0x600 + 0x400
        low = data[pos:pos + EXTRA]
        vram_f = bytes(0x12) + data[pos + EXTRA:pos + EXTRA + VATX] if len(data) - pos - EXTRA == VATX else None
        cam_x, cam_y = rf.camera(ram)
        if vram_f is not None:
            vat_recs += 1
        pm = patch_map(patches)
        hist.append(pm)
        if len(hist) > VOLATILE_N:
            hist.pop(0)
        volatile = set()                        # cells the game rewrote lately (map animations:
        for a, b in zip(hist, hist[1:]):        # beams, mechanisms): the scroll engine's, not
            for k in set(a) | set(b):           # checked unless a BOB covers the pixel
                if a.get(k) != b.get(k):
                    volatile.add(k)
        if len(hist) < VOLATILE_N:              # (the recording's start: no history yet, every
            volatile |= set(pm)                 # patched cell counts)
        _, _, rows = render(bytes(vram), regs, pal)
        rgb = [((pal[2 * i] >> 4) * 255 // 7, (pal[2 * i + 1] & 7) * 255 // 7, (pal[2 * i] & 7) * 255 // 7)
               for i in range(16)]
        adj = ((regs[18] & 15) ^ 7) - 7
        right = 256 if sp2 else 256 - max(0, (cam_x & 15) - 8)
        shown = 0 if sp2 else (page & 1)
        lst = vis_list(low)
        if prev_low is None:
            prev_patches = patches
        plst = vis_list(prev_low) if prev_low else lst
        tlst = field_list(low, shown)           # the page's newest list: a hostage may be ahead
        vhist = (vhist + [lst])[-DYN_HIST:]
        rows_map = len(mp) // (rf.COLS * 2)
        bad = 0
        badcells = {}
        only_new = only_old = 0
        tear_shown, tear_newest = set(), set()  # (the torn pixels' hostage BOBs: the tear's class)
        tear_pix = []                           # (--level 2: per such pixel its kind and BOBs)
        dyn_masks = []                          # per explosion/smoke pixel: the recent lists
        cands = vhist + [tlst]                  # whose state it shows
        dyn_box = []
        for L in cands:
            for fi, bx, by in L:
                if is_dyn(fi) and FT.get(fi):
                    dyn_box.append((bx, by, bx + FT[fi]["sw"], by + FT[fi]["sh"]))
        vat_on = VATS is not None and vram_f is not None
        if vat_on:
            vpage = 0 if sp2 else (page & 1)
            for idx in range(VATS_N):           # (vat_shown's history: its looks' ages)
                lk = vram_f[0x12 + idx]
                h = vat_hist.setdefault(idx, [])
                if not h or h[-1][1] != lk:
                    h.append((len(sheet), lk))

        def vlook(row, col):
            """-> the look of a vat cell's column on the page shown, None for any other cell and
            for a column that page has not drawn (the map's own tile)"""
            v = VATS["cells"].get((row, col)) if vat_on else None
            if not v:
                return None
            lk = mapcmp.vat_look(vram_f, v[0], vpage)
            if lk is None:
                vat_map.add(v[0])
            return lk

        def vtile(P, row, col):
            lk = vlook(row, col)
            if lk is not None:
                v = VATS["cells"][(row, col)]
                vat_seen.add(v[0])
                return mapcmp.vat_tile(VATS, v, lk)
            return rf.tile_at(mp, P, row, col)
        vat_seen = set()
        vat_map = set()
        vat_px = 0
        img = []
        for y in range(rf.VIEW):
            row = rows[y]
            spr = sprite_line(bytes(vram), regs, y)
            drow = bytearray(row)
            for x in range(8, right):
                if 0 <= x - adj < 256 and spr[x - adj] is not None:
                    continue
                wx, wy = cam_x + x - 8, cam_y + y
                if wy < 0 or wx < 0 or wy // 16 >= rows_map or wx // 16 >= rf.COLS:
                    continue
                got = row[3 * x:3 * x + 3]
                if (wy // 16, wx // 16) in volatile and bob_at(lst, wx, wy) is None and \
                        bob_at(plst, wx, wy) is None:
                    skipped += 1
                    continue
                if any(x0 <= wx < x1 and y0 <= wy < y1 for x0, y0, x1, y1 in dyn_box):
                    tops = [bob_fid(L, wx, wy) for L in cands]
                    if all(t is None or is_dyn(t) for t in tops) and any(t is not None for t in tops):
                        m = 0                   # (a pixel only explosions/smoke or the tiles hold:
                        for li, L in enumerate(cands):   # the lists whose state it shows)
                            c = bob_at(L, wx, wy)
                            if c is None:
                                t = vtile(patches, wy // 16, wx // 16)
                                b = til[t * 128 + (wy % 16) * 8 + (wx % 16) // 2]
                                c = (b >> 4) if wx % 2 == 0 else b & 15
                            if got == bytes(rgb[c]):
                                m |= 1 << li
                        dyn_masks.append(m)
                ok = False
                for L in (lst, plst):
                    for P in (patches, prev_patches):
                        c = bob_at(L, wx, wy)
                        if c is None:
                            t = vtile(P, wy // 16, wx // 16)
                            b = til[t * 128 + (wy % 16) * 8 + (wx % 16) // 2]
                            c = (b >> 4) if wx % 2 == 0 else b & 15
                        if got == bytes(rgb[c]):
                            ok = True
                            break
                    if ok:
                        break
                if ok and tlst != lst:
                    # (a hostage pixel matching the shown list but not the newest one: with one
                    # matching only the newest, the hostage is half old, half new)
                    fo = bob_fid(lst, wx, wy)
                    fn = bob_fid(tlst, wx, wy)
                    if (fo is not None and fid_base(fo) < FIELD_LATE and not is_dyn(fo)) or \
                            (fn is not None and fid_base(fn) < FIELD_LATE and not is_dyn(fn)):
                        c = bob_at(tlst, wx, wy)
                        if c is None:
                            t = vtile(patches, wy // 16, wx // 16)
                            b = til[t * 128 + (wy % 16) * 8 + (wx % 16) // 2]
                            c = (b >> 4) if wx % 2 == 0 else b & 15
                        if got != bytes(rgb[c]):
                            only_old += 1
                            tear_note(tear_shown, tear_newest, lst, tlst, wx, wy)
                            if LOOKS is not None:
                                tear_pix.append(("old", {e for e in (bob_ent(lst, wx, wy), bob_ent(tlst, wx, wy)) if e}))
                if not ok:
                    # ahead: a hostage pixel of the newest list (never a lift's or the vehicle's)
                    fn = bob_fid(tlst, wx, wy)
                    fo = bob_fid(lst, wx, wy)
                    if (fn is None or fid_base(fn) < FIELD_LATE) and (fo is None or fid_base(fo) < FIELD_LATE) and \
                            not is_dyn(fn) and not is_dyn(fo) and \
                            (fn is not None or fo is not None):
                        c = bob_at(tlst, wx, wy)
                        if c is None:
                            t = vtile(patches, wy // 16, wx // 16)
                            b = til[t * 128 + (wy % 16) * 8 + (wx % 16) // 2]
                            c = (b >> 4) if wx % 2 == 0 else b & 15
                        if got == bytes(rgb[c]):
                            ok = True
                            only_new += 1
                            tear_note(tear_shown, tear_newest, lst, tlst, wx, wy)
                            if LOOKS is not None:
                                tear_pix.append(("new", {e for e in (bob_ent(lst, wx, wy), bob_ent(tlst, wx, wy)) if e}))
                if not ok:
                    # an explosion's or the smoke's step, never held: any recent list's (but all
                    # of a picture's such pixels from one list: else the step shows torn)
                    fo = bob_fid(lst, wx, wy)
                    for L in cands:
                        fl = bob_fid(L, wx, wy)
                        if not (is_dyn(fl) or is_dyn(fo)):
                            continue
                        if fl is not None and not is_dyn(fl):
                            continue            # (an old step's pixel, never another BOB's)
                        c = bob_at(L, wx, wy)
                        if c is None:
                            t = vtile(patches, wy // 16, wx // 16)
                            b = til[t * 128 + (wy % 16) * 8 + (wx % 16) // 2]
                            c = (b >> 4) if wx % 2 == 0 else b & 15
                        if got == bytes(rgb[c]):
                            ok = True
                            dyn_lag += 1
                            break
                if not ok:
                    bad += 1
                    if vlook(wy // 16, wx // 16) is not None:
                        vat_px += 1             # (a drawn vat column's cell; the map's: "other")
                    badcells[(wy // 16, wx // 16)] = badcells.get((wy // 16, wx // 16), 0) + 1
                    drow[3 * x:3 * x + 3] = b"\xff\x00\xff"
            img.append(bytes(drow))
        prev_low = low
        prev_patches = patches
        older = []                              # (a vat column seen again at an older look)
        if vat_on:
            # A column's look changes only when it is drawn, at a look vat_shown had then: its age is
            # the last record (up to this one) in which vat_shown became it. The looks recur every
            # cycle, so a look kept from before (the column first seen, or not drawn since) has no
            # age: only a change is dated, and compared with the change before it.
            for idx in vat_seen:
                lk = mapcmp.vat_look(vram_f, idx, vpage)
                if vat_last.get(idx) == lk:
                    continue                    # (not drawn again: its age, if known, stays)
                first = idx not in vat_last
                vat_last[idx] = lk
                ages = [k for k, l2 in vat_hist[idx] if l2 == lk and k <= len(sheet)]
                if first or not ages:
                    vat_age.pop(idx, None)      # (seen first, or a look from before the record)
                    continue
                if idx in vat_age and ages[-1] < vat_age[idx]:
                    older.append(idx)
                vat_age[idx] = ages[-1]
            for idx in list(vat_last):
                if idx not in vat_seen:
                    del vat_last[idx]           # (not seen in this picture: a new start)
                    vat_age.pop(idx, None)
        if older:
            vat_older += 1
            print(f"{p.stem}: vat column(s) {sorted(older)} at an older look than the picture before")
        other_px = bad - vat_px                 # (the pixels that match no list: no known class)
        tear_px = dyn_px = 0
        if only_new and only_old:               # half old, half new
            tear_px = min(only_new, only_old) if LOOKS is None else tear_objects(tear_pix)
            bad += tear_px
            if tear_px:
                print(f"{p.stem}: hostage torn ({only_old} old, {only_new} new pixels)")
        if dyn_masks:                           # (torn: no one list shows all of them)
            best = max(range(len(cands)), key=lambda i: sum(1 for m in dyn_masks if m >> i & 1))
            off = sum(1 for m in dyn_masks if not m >> best & 1)
            if True:
                if off > 8:
                    bad += off
                    dyn_px = off
                    dyn_torn += 1
                    print(f"{p.stem}: explosion/smoke torn ({off} of {len(dyn_masks)} pixels not from one step)")
        total_bad += bad
        pics_bad += bad > 0
        if bad:
            print(f"{p.stem}: {bad} pixels differ; list {lst} qn {low[0x0890 - 0x600]} lost {low[0x069C - 0x600]} "
                  f"cells {sorted(badcells.items())[:6]}")
            # (one line a kind of difference, for tools/bstest/l2base.py field: "CLASS picture kind
            #  [key] px=N"; the hostage tear's key names its BOBs, tear_key)
            if tear_px:
                print(f"CLASS {p.stem} hostage-tear {tear_key(tear_shown, tear_newest)} px={tear_px}")
            if dyn_px:
                print(f"CLASS {p.stem} smoke-tear px={dyn_px}")
            if vat_px:
                print(f"CLASS {p.stem} vat-look px={vat_px}")
            if other_px:
                print(f"CLASS {p.stem} other px={other_px}")
        if older:
            print(f"CLASS {p.stem} vat-older px=0")
        vat_cols |= vat_seen
        vat_mcols |= vat_map
        sheet.append(img)
    if wrong:
        print(f"{wrong} files of another length skipped")
    print(f"{len(files)} pictures ({len(files) - wrong} checked): {pics_bad} with differences, {total_bad} pixels "
          f"({skipped} pixels of animated map cells not checked; {dyn_lag} explosion/smoke pixels of a recent step; "
          f"{dyn_torn} torn explosion/smoke pictures)")
    if VATS is not None:
        print(f"vats: {vat_recs} records with the vats' RAM, {len(vat_cols)} vat columns seen, {vat_older} pictures "
              f"with a column at an older look; {len(vat_mcols)} vat columns seen at the map's own tile")
    # contact sheet: 8 per row, 1x
    per = 8
    w = 256
    rows_out = []
    for k in range(0, len(sheet), per):
        chunk = sheet[k:k + per]
        for y in range(rf.VIEW):
            line = b"".join(c[y] for c in chunk) + b"\x00\x00\x00" * w * (per - len(chunk))
            rows_out.append(line)
        rows_out.append(b"\x40\x40\x40" * w * per)
    write_png(out, w * per, len(rows_out), rows_out)


if __name__ == "__main__":
    main()
