"""vertrim.py (tools/bstest/perf2; agent a_field's check of 2026-11-01) OLD NEW: two conversion folders
(build/msx before and after docs/PERF2_PLAN.md item 1, field-1: sprites_l3_field.inc, sprites_l3_fc.bin,
sprites_l3_field_vram.bin). Checks the trimmed output: every level-3 play-field frame drawn from the new tables (field_tab's trimmed box,
the new cache ROM) at (dx, dy) equals the old frame drawn at its (dx, dy), pixel for pixel, normal and white."""
import re, sys, struct
from pathlib import Path
old, new = Path(sys.argv[1]), Path(sys.argv[2])
def load(d):
    inc = (d / "sprites_l3_field.inc").read_text()
    fc = (d / "sprites_l3_fc.bin").read_bytes()
    vram = (d / "sprites_l3_field_vram.bin").read_bytes()
    tab = [tuple(int(v) for v in m.groups()) for m in re.finditer(r"db (\d+), (\d+), (\d+), (\d+), (-?\d+), (-?\d+)", inc.split("field_tab:")[1].split("field_look:")[0])]
    ent = int(re.search(r"FC_ENT: equ 0x([0-9A-F]+)", inc).group(1), 16) - 0x8000
    return tab, fc, vram, ent
def draw(d, fid, white):
    tab, fc, vram, ent = d
    x, y, w, h, dx, dy = tab[fid]
    ci = fc[2 * fid + white]
    if white and ci == 0xFF: return None
    px = {}
    if ci != 0xFF:
        b, a, pl = struct.unpack_from("<BHB", fc, ent + 4 * ci)
        off = b * 8192 + a - 0x8000
        for r in range(h):
            for c in range(w):
                v = (fc[off + r * (w // 2) + c // 2] >> (4 - 4 * (c & 1))) & 15
                if v: px[(dx + c, dy + r)] = v
    else:
        for r in range(h):
            for c in range(w):
                v = (vram[(y + r) * 128 + (x + c) // 2] >> (4 - 4 * ((x + c) & 1))) & 15
                if v: px[(dx + c, dy + r)] = v
    return px
O, N = load(old), load(new)
bad = 0
for fid in range(len(O[0])):
    if O[0][fid][1] >= 232: continue        # (the smoke: level 1's dynamic frames)
    for wb in (0, 1):
        a, b = draw(O, fid, wb), draw(N, fid, wb)
        if a != b:
            bad += 1; print("frame", fid, "white" if wb else "normal", "differs")
print("frames checked:", len(O[0]), "differing:", bad)
