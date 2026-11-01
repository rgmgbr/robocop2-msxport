#!/usr/bin/env python3
"""Rebuilds a whole frame of the prototype (play area with sprites + HUD) and checks it.

Inputs (saved from openMSX, see tools/openmsx_rc2.tcl): VRAM (128 KiB), RAM C000h-C7FFh and
the 48 VDP registers. The play-area registers come from the register list the
ISR applied last (seq == app_seq, msx/isr.asm), whose tail also records the camera and the
sprite state that list shows; the HUD registers come from split_list (sprites off; on the
V9958 the border mask off). The main loop writes the SAT of a list right after the VBLANK that
applies it (msx/sprites.asm, sprites_vblank): a snapshot taken in between (spr_vblank still 1
with the list already applied) has the previous SAT, so its sprites are not checked. The split itself (display off on lines VIEW..VIEW+4, HUD from
VIEW+5) was verified separately with the VDP probes. The frame is rendered with
tools/msxscreen.py's model (sprite mode 2 included) and compared with the expected picture:
  - the map at the recorded camera;
  - the HUD as the Amiga panel would be after drawing what msx/hud.asm records as shown
    (digits, energy level, heads, weapon icon; tools/hudmodel.py) plus the message line
    (MSX 7 px rule); while a HUD job (head, icon, full can) is half written the HUD is not
    checked;
  - every sprite object the list shows (pub_spr: RoboCop and BOBs, msx/sprites.asm) as
    tools/msxsprites.py converts its composition (full OR version, or the single-layer
    fallback for the bands the budget dropped), in SAT order (the hit spark's object, then
    object 0 and the others: the first in front): exact. Objects that
    alternate between frames are recorded as not shown on the frames they are off. Lines where
    the SAT shown puts more than 8 sprites (the budget's layout for new positions still on its
    way: the VDP drops the last ones) are reported apart and their sprite pixels not checked;
  - the tile area of VRAM: each of the level's tile-cache slots on page 2 (256; 224 in level 2,
    whose play-field dynamic slot takes page 2's lines 224-247) holds the tile its TC_TILE entry
    names (page-0 RAM, ram0.bin: msx/tiles.asm tc_load), and the level's play-field atlas on page 3
    holds its frames (POOL_lN_field_vram.bin, or level 1's robocop_field_vram.bin, inside each
    static frame's box): nothing else may write there at run time.
Needs numpy for the sprites (tools/msxsprites.py).

With --field (test builds: msx/field.asm fb_visrec), the play area's expected picture is the map
with its patches (msx/tiles.asm map_write: page-0 RAM and F500h-F8FFh) and the play-field BOBs of
the list on screen (fb_vis at F248h: the first in the list on top, as msx/field.asm fb_bobs
composes) as the level's atlas and dynamic frames hold them (FieldLooks: the bytes the ROM
uploads); without it the static map alone, as before (a BOB or a patch counts as a difference).
Level 2's vat cells (LEVEL_PREFIX level2, a snapshot with ramf.bin) are expected at their column's look
on the page shown (tools/mapcmp.py vat_look: vat_disp's nibble; the V9958's ring page 0), a map patch
first with --field, as msx/tiles.asm get_tile draws them; a column that page has not drawn (nibble 0:
always so in the product, VAT_ANIM=0, whose vats are the map's static images) at the map's own tile.

With --cut LINE (level 2's vats: msx/cold.asm spr_cut), RoboCop's and the hit spark's sprites are
expected to end above screen line LINE (their pixels from it down are not shown: the Amiga's copper
turns the sprites off there while he sinks); the other objects are expected whole. The caller gives
the line (tools/bstest/cutview.py cut: the original's copper line for the tick the list shows).

With --no-sprites the sprites are not checked and the play area is rendered with them off (R#8's
SPD), so that every one of its pixels is compared with the expected picture (none is skipped as a
sprite's); the HUD and the tile area as always. For a level's first picture (tools/bstest/
bonuscheck.py --level2, contcheck.py), where the list's SAT is not published yet: the records name
the objects of its tick while the screen shows none or the set before (docs/level2/HANDOFF.md, steps
18-19).

Per level (--sprites POOL --level N): the sprite objects' looks come from the global pool of
tools/msxsprites.py --pool (POOL.bin, .inc), the records the ROM holds, decoded (level N's BOB
index; RoboCop's is both levels'), and the silhouettes from level N's colour rows; without it they
are level 1's, converted again from build/msx/robocop.json as tools/msxsprites.py cut them.

usage: msxframe.py SNAPDIR LEVEL_PREFIX HUD_PREFIX OUT.png [--sprites POOL --level N] [--field] [--cut LINE]
                   [--no-sprites]
       (e.g. build/snap build/msx/level1 build/msx/hud build/png/frame.png)
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from msxscreen import render  # noqa: E402
from planar import write_png  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAM_BASE = 0xC000
PUB_SEQ, APP_SEQ, VDP_ID = 0xC005, 0xC006, 0xC000
SPR_VBLANK = 0xC0E5
HUD_SHOWN, EN_SHOWN, HUD_CHARS, HEADS_G, ICON_SHOWN = 0xC608, 0xC618, 0xC626, 0xC63B, 0xC63D
JOB_LINES, JOBQ_N = 0xC63E, 0xC646
LISTS = (0xC080, 0xC0A0)
MAX_OBJ = 16
SPARK_OBJ = MAX_OBJ - 1                         # msx/sprites.asm: first in the SAT
SAT_ORDER = [SPARK_OBJ] + list(range(SPARK_OBJ))
PUB_SPR = {0xC080: 0xC700, 0xC0A0: 0xC780}     # what each list's SAT shows (MAX_OBJ objects x 8 bytes)
SPLIT_LIST = 0xC0C0
VIEW, HUD_TOP = 162, 167
TC_TILE = 0x0400                                # page-0 RAM: the tile in each cache slot (msx/msx.inc)
TC_SLOTS = {1: 256, 2: 224}                     # the cache's slots per level (tools/mkrom.py TC_SLOTS)
FB_VIS = 0xF248                                 # test builds: the play-field BOBs of the list on screen
FB_MAX = 8
HUD_MSK = 0xC02B
COLS = 160


class FieldLooks:
    """A level's play-field frames as the ROM uploads them (tools/msxsprites.py --pool's files: POOL_lN.json
    "field", the atlas as VRAM holds it, POOL_lN_field_vram.bin, and the dynamic frames, POOL_fdyn.bin with
    the level's field_dyn and dyn_tab, POOL_lN_field.inc): per frame its entry (x, y, sw, sh in the atlas; a
    removed frame's are those of the frame shown, moved by ox, oy) and its pixels (joint palette indices,
    0 transparent). Level 1 without a pool: build/msx/robocop.*."""

    def __init__(self, level: int = 1, pool: Path | None = None):
        import json
        import re
        if pool is None:
            pre, meta = ROOT / "build/msx/robocop", ROOT / "build/msx/robocop.json"
            dyn = ROOT / "build/msx/robocop_fdyn.bin"
        else:
            pre, meta = pool.with_name(f"{pool.name}_l{level}"), pool.with_name(f"{pool.name}_l{level}.json")
            dyn = pool.with_name(f"{pool.name}_fdyn.bin")
        self.frames = {f["fid"]: f for f in json.loads(meta.read_text())["field"]}
        self.atlas = Path(f"{pre}_field_vram.bin").read_bytes()
        self.dyn = dyn.read_bytes()
        inc = Path(f"{pre}_field.inc").read_text()
        self.inc = {m[1]: int(m[2], 0) for m in re.finditer(r"^(\w+): equ (\S+)", inc, re.M)}
        tab = inc.partition("dyn_tab:")[2]
        nums = [int(v, 0) for v in re.findall(r"0x[0-9A-Fa-f]+|\b\d+\b", re.sub(r";.*", "", tab))]
        self.dyn_tab = [tuple(nums[k:k + 5]) for k in range(0, len(nums), 5)]   # bit, evict, bank, addr, 0
        self._img: dict[int, list[bytes]] = {}

    def pixels(self, fid: int) -> list[bytes]:
        """Frame fid's pixels, a bytes object a line (sw x sh)."""
        if fid in self._img:
            return self._img[fid]
        f = self.frames[fid]
        w, h = f["sw"], f["sh"]
        rows = []
        if "dyn" in f:                              # (its strips of DYN_H lines side by side, a line of
            _bit, _ev, bank, addr, _z = self.dyn_tab[f["dyn"]]   # the slot after another: field.asm fb_dyn)
            o = bank * 0x2000 + addr - 0x8000
            dh = self.inc["DYN_H"]
            n = -(-h // dh)
            lines: dict[int, bytes] = {}
            for r in range(min(h, dh)):
                for st in range(n):
                    if r + dh * st < h:
                        lines[r + dh * st] = self.dyn[o:o + w // 2]
                        o += w // 2
            src = [lines[y] for y in range(h)]
        else:
            src = [self.atlas[(f["y"] + y) * 128 + f["x"] // 2:(f["y"] + y) * 128 + (f["x"] + w) // 2] for y in range(h)]
        for line in src:
            rows.append(bytes(v for b in line for v in (b >> 4, b & 15)))
        self._img[fid] = rows
        return rows

    def at(self, lst: list[tuple[int, int, int]], wx: int, wy: int) -> int | None:
        """The colour of the top BOB of lst (frame, map x, map y; the first on top) with a pixel at map
        (wx, wy), or None."""
        for fi, bx, by in lst:
            f = self.frames.get(fi)
            if f is None:
                continue
            dx, dy = wx - bx, wy - by
            if 0 <= dx < f["sw"] and 0 <= dy < f["sh"]:
                c = self.pixels(fi)[dy][dx]
                if c:
                    return c
        return None


def patched(patches: bytes, row: int, col: int) -> bool:
    """(--field) Whether the cell has a map patch (tools/recframes.py tile_at's walk): get_tile takes the
    patch before level 2's vat rule (msx/tiles.asm)."""
    import recframes
    p, pool = patches[row], recframes.MP_POOL[row & 1]
    while p != 0xFF:
        if patches[pool + recframes.MPF_COL + p] == col:
            return True
        p = patches[pool + recframes.MPF_NEXT + p]
    return False


def fb_vis(ramf: bytes) -> list[tuple[int, int, int]]:
    """The play-field BOBs of the list on screen (test builds: msx/field.asm fb_visrec, RAM F248h)."""
    n = ramf[FB_VIS - 0xF000]
    return [struct.unpack_from("<Bhh", ramf, FB_VIS - 0xF000 + 1 + 5 * i) for i in range(min(n, FB_MAX))]


def tile_area(vram: bytes, ram0: bytes, til: bytes, level: int, looks: FieldLooks) -> list[str]:
    """What the tile area of VRAM holds that it should not: the level's cache slots (page 2) against
    their TC_TILE entries and the atlas's static frames (page 3) against the level's atlas."""
    bad = []
    slots = TC_SLOTS[level]
    for s in range(slots):
        t = ram0[TC_TILE + 2 * s] | ram0[TC_TILE + 2 * s + 1] << 8
        if t == 0xFFFF:
            continue
        for y in range(16):
            a = 0x10000 + (s // 16) * 2048 + y * 128 + (s % 16) * 8
            if vram[a:a + 8] != til[t * 128 + 8 * y:t * 128 + 8 * y + 8]:
                bad.append(f"slot {s} (tile {t})")
                break
    for fid, f in sorted(looks.frames.items()):
        if "dyn" in f or f.get("look", fid) != fid:
            continue
        for y in range(f["sh"]):
            a = (f["y"] + y) * 128 + f["x"] // 2
            if vram[0x18000 + a:0x18000 + a + f["sw"] // 2] != looks.atlas[a:a + f["sw"] // 2]:
                bad.append(f"atlas frame {fid}")
                break
    return bad


def applied_list(ram: bytes) -> tuple[dict[int, int], int, int, list[dict]]:
    seq = ram[APP_SEQ - RAM_BASE]
    for base in LISTS:
        o = base - RAM_BASE
        if ram[o] == seq:
            n = ram[o + 1]
            pairs = ram[o + 2:o + 2 + n]
            regs = {pairs[i + 1] & 0x7F: pairs[i] for i in range(0, n, 2)}
            cam_x, cam_y = struct.unpack_from("<HH", ram, o + 2 + n)    # (then the game frame)
            objs = []
            for k in range(MAX_OBJ):
                flags, ident, drop, x, y = struct.unpack_from("<BHBhh", ram, PUB_SPR[base] - RAM_BASE + 8 * k)
                objs.append({"shown": bool(flags & 0x80), "bob": bool(flags & 1), "id": ident, "drop": drop,
                             "x": x, "y": y, "sil": (flags >> 1) & 3})
            return regs, cam_x, cam_y, objs
    raise ValueError(f"no register list with seq {seq}")


def split_regs(ram: bytes) -> dict[int, int]:
    o = SPLIT_LIST - RAM_BASE
    n = ram[o]
    pairs = ram[o + 1:o + 1 + n]
    return {pairs[i + 1] & 0x7F: pairs[i] for i in range(0, n, 2)}


def rgb9(pal: bytes) -> list[tuple[int, int, int]]:
    return [((pal[2 * i] >> 4) * 255 // 7, (pal[2 * i + 1] & 7) * 255 // 7, (pal[2 * i] & 7) * 255 // 7)
            for i in range(16)]


_conv_cache: dict = {}
SOURCE: dict = {}                               # --sprites: {"data": msxsprites.SpriteData, "level": N}


def use_pool(prefix: Path, level: int) -> None:
    """The sprite looks of level N from tools/msxsprites.py --pool's files (see the docstring)."""
    import msxsprites
    SOURCE.update({"data": msxsprites.SpriteData(prefix.with_suffix(".bin"), prefix.with_suffix(".inc")),
                   "level": level})
    _conv_cache.clear()


def converted(obj: dict, joint_pal: bytes) -> list:
    """The bands of an object's composition, as tools/msxsprites.py cuts them."""
    key = (obj["bob"], obj["id"])
    if key in _conv_cache:
        return _conv_cache[key]
    if SOURCE:                                  # (the pool's records, decoded)
        sd = SOURCE["data"]
        o = sd.bob_entry(SOURCE["level"], obj["id"]) if obj["bob"] else sd.entry(obj["id"])
        _conv_cache[key] = sd.record(o)["layout"]
        return _conv_cache[key]
    import json
    import numpy as np
    import msxsprites
    import player
    main = (ROOT / "build/extracted/boot/main_8000.bin").read_bytes()
    pal = np.array([[joint_pal[2 * i] >> 4, joint_pal[2 * i + 1] & 7, joint_pal[2 * i] & 7] for i in range(16)]) / 7
    pal12 = [struct.unpack_from(">H", main, 0xFFF6 - 0x8000 + 2 * i)[0] for i in range(31)]
    sppal = np.array([[0, 0, 0]] + [msxsprites.amiga_rgb(c) for c in pal12[16:31]])
    if obj["bob"]:
        bobs = json.loads((ROOT / "build/msx/robocop.json").read_text())["bobs"]
        fr = bobs[obj["id"]]
        if fr.get("repeat"):                        # a frame removed: another one, moved
            k2, dy, dx = fr["repeat"]
            cols = msxsprites.move_layout(converted({"bob": 1, "id": k2}, joint_pal), dy, dx)
            _conv_cache[key] = cols
            return cols
        if fr.get("mirror"):                        # an earlier frame's layout, mirrored
            m, dy, dx = fr["mirror"]
            cols = msxsprites.mirror_layout(converted({"bob": 1, "id": m}, joint_pal), bobs[m]["w"], dy, dx)
            _conv_cache[key] = cols
            return cols
        ram = (ROOT / "build/ram/level1_full.bin").read_bytes()
        src = msxsprites.bob_image(ram, fr["addr"], fr["w"], fr["h"])
        if fr.get("spark"):                         # the hit spark: RoboCop's colours and pairs
            tgt = np.where(src > 0, msxsprites.nearest(sppal[np.clip(src, 0, 15)], pal, 1), 0)
            cols = msxsprites.Converter(pal, cap=msxsprites.RC_CAP).composition(tgt)
        else:
            bgpal = np.array([[0, 0, 0]] + [msxsprites.amiga_rgb(c) for c in pal12[:15]])
            near = msxsprites.nearest(bgpal, pal, 1)
            tgt = np.where(src >= 0, near[np.clip(src, 0, 15)], 0)
            conv = msxsprites.Converter(pal, msxsprites.PAIRS_ALL, cap=msxsprites.BOB_CAP, align="bottom")
            conv.prefer = {(b, n): order for b, n, *order in fr.get("prefer", [])}
            cols = conv.composition(tgt)
    else:
        # RoboCop: the compositions as tools/msxsprites.py built them (robocop.json: the entries'
        # compositions, those that mirror or move another one)
        if "rc" not in _conv_cache:
            perma = (ROOT / "build/extracted/files/PERMA_05.bin").read_bytes()
            comps, _ = msxsprites.rc_compositions(player.Game(main, perma))
            meta = json.loads((ROOT / "build/msx/robocop.json").read_text())
            _conv_cache["rc"] = (comps, meta["rc_index"],
                                 {int(c): tuple(v) for c, v in meta["rc_mirrors"].items()},
                                 {int(c): tuple(v) for c, v in meta["rc_moves"].items()}, {},
                                 meta.get("rc_start"))
        comps, index, pairs, moves, lays, start = _conv_cache["rc"]
        conv = msxsprites.Converter(pal, cap=msxsprites.RC_CAP)

        def target(c: int) -> np.ndarray:
            return np.where(comps[c] > 0, msxsprites.nearest(sppal[comps[c]], pal, 1), 0)

        def layout(c: int) -> list:
            if c not in lays:
                if c in moves:
                    src, dy, dx = moves[c]
                    lays[c] = msxsprites.move_layout(layout(src), dy, dx)
                elif c in pairs:
                    cr, dy, dx = pairs[c]
                    lays[c] = msxsprites.mirror_layout(layout(cr), player.BUF_W, dy, dx)
                else:
                    lays[c] = conv.composition(target(c))
            return lays[c]

        if start and start["arms"][0] not in lays:  # (the start-of-level arm poses: converted together)
            tg = {c: target(c) for c in set(start["arms"]) | {start["after"]}}
            lays.update(msxsprites.start_layouts(conv, comps, [tg.get(c) for c in range(len(comps))],
                                                 start["arms"], start["after"], sppal, layout))

        cols = layout(index[obj["id"]])
    _conv_cache[key] = cols
    return cols


def expected_sprites(objs: list[dict], joint_pal: bytes, cut: int | None = None,
                     removed: list[int] | None = None) -> dict[tuple[int, int], int]:
    """Screen pixel -> joint palette index of the sprite objects shown (SAT order: the first in
    front). With cut, RoboCop's and the spark's pixels on screen lines from cut down are left out
    (their count added to removed[0])."""
    out: dict[tuple[int, int], int] = {}
    for k in reversed(SAT_ORDER):
        obj = objs[k]
        if not obj["shown"]:
            continue
        line_end = cut if cut is not None and k in (0, SPARK_OBJ) else None
        sil = silhouette_colours(joint_pal)[obj.get("sil", 0)]
        lay = converted(obj, joint_pal)
        for j, (y0, boxes) in enumerate(lay):
            dropped = obj["drop"] >> (len(lay) - 1 - j) & 1      # (bands numbered from the bottom)
            for c in reversed(boxes):                           # (the first box of a band in front)
                im = c["fallback"] if sil or dropped else c["full"]
                for y in range(16):
                    for i in range(16):
                        if im[y, i]:
                            if line_end is not None and obj["y"] + y0 + y >= line_end:
                                if removed is not None:
                                    removed[0] += 1
                                continue
                            out[(obj["x"] + c["x"] + i, obj["y"] + y0 + y)] = sil or int(im[y, i])
    return out


def silhouette_colours(joint_pal: bytes) -> list[int]:
    """Per silhouette mode (msx/bob.asm BM_...) the joint palette entry it is shown in (0: none):
    tools/msxsprites.py's colour rows SPR_SIL_FLASH (the nearest to the background's colour 15)
    and SPR_SIL_BLACK (the palette's black after entry 0); with --sprites, level N's colour rows."""
    if SOURCE:
        sd = SOURCE["data"]
        row = lambda n: sd.data[sd.inc["SPR_COL_BANK"] * 0x2000 + 16 * n] & 15   # noqa: E731
        lv = SOURCE["level"]
        return [0, row(sd.inc[f"SPR_SIL_FLASH_L{lv}"]), row(sd.inc[f"SPR_SIL_BLACK_L{lv}"]), 0]
    import numpy as np
    import msxsprites
    main = (ROOT / "build/extracted/boot/main_8000.bin").read_bytes()
    pal = np.array([[joint_pal[2 * i] >> 4, joint_pal[2 * i + 1] & 7, joint_pal[2 * i] & 7] for i in range(16)]) / 7
    c15 = np.array([msxsprites.amiga_rgb(struct.unpack_from(">H", main, 0xFFF6 - 0x8000 + 2 * 14)[0])])
    white = int(msxsprites.nearest(c15, pal, 1)[0])
    black = next(i for i in range(1, 16) if (pal[i] == 0).all())
    return [0, white, black, 0]


def over_lines(vram: bytes, regs: list[int]) -> set[int]:
    """Play-area lines on which the SAT the registers show puts more than 8 sprites."""
    base = ((regs[11] << 15) | (regs[5] << 7)) & 0x1FC00
    count = [0] * 256
    for i in range(32):
        y = vram[base + 512 + 4 * i]
        if y == 216:
            break
        for k in range(16):
            count[(y + 1 + k - regs[23]) & 0xFF] += 1
    return {line for line in range(VIEW) if count[line] > 8}


def hud_expected(ram: bytes) -> list[list[int]] | None:
    """HUD colour indices for the state msx/hud.asm records (None while a job is pending)."""
    if ram[JOB_LINES - RAM_BASE] or ram[JOBQ_N - RAM_BASE]:
        return None
    import hudmodel
    p = hudmodel.Panel((ROOT / "build/extracted/files/PERMA_05.bin").read_bytes(),
                       (ROOT / "build/extracted/boot/main_8000.bin").read_bytes())
    for k in range(len(hudmodel.DIGIT_CELLS)):
        p.digit(k, ram[HUD_SHOWN - RAM_BASE + k])
    shown = struct.unpack_from("<h", ram, EN_SHOWN - RAM_BASE)[0]
    p.can_level(max(0, min(32, shown >> 3)))
    for s in (0, 1):
        p.head(ram[HEADS_G - RAM_BASE + s], s)
    p.icon(ram[ICON_SHOWN - RAM_BASE])
    hud = p.hud()
    hudmodel.text_line(p.glyph_colours(), list(ram[HUD_CHARS - RAM_BASE:HUD_CHARS - RAM_BASE + 21]), hud)
    return hud


def main() -> int:
    snap, level, hud, out = (Path(a) for a in sys.argv[1:5])
    lv = int(sys.argv[sys.argv.index("--level") + 1]) if "--level" in sys.argv else 1
    pool = Path(sys.argv[sys.argv.index("--sprites") + 1]) if "--sprites" in sys.argv else None
    if pool:
        use_pool(pool, lv)
    looks = FieldLooks(lv, pool)
    vram = (snap / "vram.bin").read_bytes()
    ram = (snap / "ram.bin").read_bytes()
    ram0 = (snap / "ram0.bin").read_bytes() if (snap / "ram0.bin").exists() else None
    ramf = (snap / "ramf.bin").read_bytes() if (snap / "ramf.bin").exists() else None
    field = "--field" in sys.argv and ram0 is not None and ramf is not None
    if field:
        import recframes
        patches = ram0[0x0A00:0x1000] + ramf[0x0500:0x0900]    # (MP_ROW, MP_A; MP_B: recframes' layout)
        lst = fb_vis(ramf)
    base = [int(v) for v in (snap / "regs.txt").read_text().split()]
    play, cam_x, cam_y, objs = applied_list(ram)
    regs_play = list(base)
    for r, v in play.items():
        regs_play[r] = v
    no_spr = "--no-sprites" in sys.argv
    if no_spr:
        regs_play[8] |= 0x02                # (SPD: the play area without the sprites)
    regs_hud = list(base)
    for r, v in split_regs(ram).items():
        regs_hud[r] = v
    regs_hud[8] = 0x0A                      # sprites off in the HUD
    if ram[HUD_MSK - RAM_BASE]:
        regs_hud[25] = 0x01                 # V9958: SP2 kept, mask off
    pal_play = level.with_suffix(".pal").read_bytes()
    pal_hud = hud.with_suffix(".pal").read_bytes()
    _, _, rows_play = render(vram, regs_play, list(pal_play))
    _, _, rows_hud = render(vram, regs_hud, list(pal_hud))
    border = bytes(rgb9(pal_play)[regs_play[7] & 15]) * 256
    frame = rows_play[:VIEW] + [border] * (HUD_TOP - VIEW) + rows_hud[HUD_TOP:212]

    mp = level.with_suffix(".map").read_bytes()
    til = level.with_suffix(".til").read_bytes()
    rows_map = len(mp) // (COLS * 2)
    vats = None
    if ramf is not None and level.name == "level2":            # (the vat rule: tools/mapcmp.py)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import mapcmp
        vats = mapcmp.vat_layout(level)
        vpage = 0 if 26 in play else (regs_play[2] >> 5) & 1  # (the V9958's ring: page 0's looks)
    prgb, hrgb = rgb9(pal_play), rgb9(pal_hud)
    hud_want = hud_expected(ram)
    sat_pending = ram[SPR_VBLANK - RAM_BASE] and ram[PUB_SEQ - RAM_BASE] == ram[APP_SEQ - RAM_BASE]
    cut = int(sys.argv[sys.argv.index("--cut") + 1]) if "--cut" in sys.argv else None
    cut_removed = [0]
    if no_spr:                              # (every play-area pixel against the expected picture)
        print("--no-sprites: sprites not checked, the play area rendered with them off")
        spr, sat_pending = {}, False
    else:
        try:
            spr = {} if sat_pending else expected_sprites(objs, pal_play, cut, cut_removed)
        except (IndexError, struct.error):  # a product build records no pub_spr: render only
            print("no sprite record (product build): sprites not checked")
            spr, sat_pending = {}, True
    over = set() if sat_pending or no_spr else over_lines(vram, regs_play)
    bad = border_px = checked = spr_ok = pending_px = 0
    diff_rows = []
    # V9938 engine: with f > 8 the set-adjust (s = 8 - f) shows the border on the right
    right_border = 256 if 26 in play else 256 - max(0, (cam_x & 15) - 8)
    border_rgb = bytes(prgb[regs_play[7] & 15])
    for y in range(212):
        row = frame[y]
        drow = bytearray(row)
        for x in range(8 if y < HUD_TOP else 0, 256):
            got = row[3 * x:3 * x + 3]
            if y < VIEW and x >= right_border and got == border_rgb:
                border_px += 1
                continue
            if y < VIEW:
                wx, wy = cam_x + x - 8, cam_y + y
                if wy // 16 >= rows_map or wx // 16 >= COLS:
                    continue
                c = looks.at(lst, wx, wy) if field else None
                if c is None:
                    v = vats["cells"].get((wy // 16, wx // 16)) if vats else None
                    lk = mapcmp.vat_look(ramf, v[0], vpage) if v and not (field and patched(patches, wy // 16, wx // 16)) else None
                    if lk is not None:
                        t = mapcmp.vat_tile(vats, v, lk)
                    elif field:
                        t = recframes.tile_at(mp, patches, wy // 16, wx // 16)
                    else:
                        t = mp[2 * ((wy // 16) * COLS + wx // 16)] | mp[2 * ((wy // 16) * COLS + wx // 16) + 1] << 8
                    b = til[t * 128 + (wy % 16) * 8 + (wx % 16) // 2]
                    c = (b >> 4) if wx % 2 == 0 else b & 15
                want = bytes(prgb[c])
                if sat_pending:
                    pass                            # sprites not checked (see the docstring)
                elif (x, y) in spr:
                    if y in over:
                        continue                    # (the VDP dropped sprites on that line)
                    want = bytes(prgb[spr[(x, y)]])
            elif y < HUD_TOP:
                want = border[:3]
            elif hud_want is None:
                continue                            # a HUD job is half written
            else:
                want = bytes(hrgb[hud_want[y - HUD_TOP][x]])
            if sat_pending and y < VIEW and got != want:
                pending_px += 1                     # (a sprite pixel of the previous SAT)
                continue
            checked += 1
            if y < VIEW and (x, y) in spr and got == want:
                spr_ok += 1
            if got != want:
                bad += 1
                drow[3 * x:3 * x + 3] = b"\xff\x00\xff"
        diff_rows.append(bytes(drow))
    write_png(out, 256 * 2, 212 * 2, [b"".join(r[i:i + 3] * 2 for i in range(0, 768, 3)) for r in frame for _ in (0, 1)])
    write_png(out.with_name(out.stem + "_diff.png"), 256, 212, diff_rows)
    print(f"{out}: camera ({cam_x},{cam_y}), play regs {sorted(play.items())}")
    if sat_pending:
        print(f"  SAT of this list not written yet (snapshot right after the VBLANK): sprites not checked, "
              f"{pending_px} play-area pixels skipped")
    shown = [f"{'BOB' if o['bob'] else 'RoboCop'} {o['id']} at ({o['x']},{o['y']})"
             + (f" drop {o['drop']:#04x}" if o["drop"] else "") for o in objs if o["shown"]]
    n_spr = sum(1 for (x, y) in spr if 8 <= x < 256 and 0 <= y < VIEW and y not in over)
    print(f"  sprites: {'; '.join(shown) or 'none'}; {spr_ok}/{n_spr} sprite pixels exact")
    if cut is not None:
        print(f"  cut at screen line {cut}: {cut_removed[0]} of RoboCop's and the spark's pixels below it left out")
    if hud_want is None:
        print("  HUD job pending: HUD not checked")
    if over:
        print(f"  {len(over)} lines with more than 8 sprites in the SAT shown (transient), their sprite pixels "
              f"not checked: {min(over)}..{max(over)}")
    if field:
        print(f"  play field: the map's patches and {len(lst)} BOB(s) of the list on screen: "
              + ", ".join(f"{fi} at ({bx},{by})" for fi, bx, by in lst))
    print(f"  {checked} pixels checked, {bad} differ, {border_px} right-border pixels skipped")
    tile_bad = tile_area(vram, ram0, til, lv, looks) if ram0 is not None else []
    if tile_bad:
        print(f"  tile VRAM changed: {len(tile_bad)} slot(s) or atlas frame(s) differ ({', '.join(tile_bad[:6])})")
    return 0 if bad == 0 and not tile_bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
