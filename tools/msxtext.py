#!/usr/bin/env python3
"""The text screens' data for the MSX front end (msx/front.asm): the 8x8 bitmap font of the
Amiga's text screens and the level statistics script, from the composite RAM image as the game
code reads them (tools/rc2front.py; docs/AMIGA_ANALYSIS.md, "Front end: title, text screens,
high scores").

- Font ($65DB0, PERMA): 44 glyphs of 3 planes x 8 lines, drawn with move.b into planes 0-2 by
  $118D6. Plane 1 is always clear and planes 0 and 2 never meet: the strokes are colour 1, their
  hand-drawn shadow colour 4. Here each glyph is 8 x 8 pixels in SCREEN 5 (4 bytes a line, the
  left pixel high), the cell's every pixel written (colour 0 between).
- Palette ($109A8, COLOR01-15, components at most E): the MSX's 3-bit components (c * 7 / 15,
  rounded, then the colour grade: tools/msxbright.py), as the VBLANK loads the play field's
  (isr.asm pf_pal: R then B in the first byte, G in the second).
- Statistics script ($1132F, show_level_stats $85D8 fills its three number fields with $11DC6
  and runs it through $10762): its bytes up to its FF 07 (the interpreter's format in
  rc2front.py), with the offsets of the three 8-character fields.
- Brainstorm's texts ($8382 after level 1's statistics, each through $10762; msx/front.asm
  fe_text runs them in place with front_stats' engine): the intro ($114AA, txt_bs_intro) and
  the results of the table $840A ($1162F solved, $11667 failed, $11698 out of time: txt_bs_ok,
  txt_bs_fail, txt_bs_time), appended after txt_glyphs. Each is its bytes up to its FF 07,
  checked: positions, characters, waits (FF 02 n) and the end (FF 07) only, every glyph in the
  font, every line inside the play area (fs_char, no bounds check: column c at x 8c - 16, row r
  at line 67 + 8r of page 0) and as many calls as the original takes (rc2front.py's count). The
  intro's long line does not fit 256 pixels: the port's copy splits it (INTRO_LINES). Each
  script's finished play area, page 0's lines 0-161 as fs_char leaves them (text_bs_*.sc5: 128
  bytes a line, SCREEN 5, next to OUT.inc), with its preview in the graded palette (.png), is
  the reference for the port's screens.
- The port's credit on the title picture (with TITLE.sc8 and OUT.sc8: the SCREEN 8 picture of
  tools/msxpic.py): CREDIT's lines in the same font (capitals only), centred over the dark band
  below RoboCop's chin, the strokes in the logo's light grey-blue and their shadow in dark blue
  (G7 bytes: the text screens' green and blue are too dark over the picture); the pixels between
  them keep the picture. OUT.png is its preview. (The pictures keep the plain colours: the
  colour grade made them look blown out, the user's choice, 2026-10-22.)
- GAME OVER under the game over picture (with OVER.sc8 and OUT2.sc8, the user's choice: PIC9
  has no text): a black band of BAND lines below it with the words in the same font and colours
  at twice the size, centred (front.asm pic_show centres the taller picture).

usage: msxtext.py [RAM_IMAGE] [OUT.inc] [TITLE.sc8 OUT.sc8 [OVER.sc8 OUT2.sc8]]
       (defaults: build/ram/level1_full.bin, build/msx/text.inc)
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc2front  # noqa: E402
from msxbright import grade_pal  # noqa: E402
from planar import write_png  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
STATS = 0x1132F                     # show_level_stats' script
STATS_FIELDS = (0x1135A, 0x11379, 0x11398)  # henchmen ($16C2), nukes ($16C0), hostages ($16BE)
CREDIT = ((158, "2026 PORT BY RODRIGO G.M. GARCIA"),   # (picture line, text): the user's credit
          (168, "ORIGINAL AMIGA GAME BY"),              # (32 characters a line at most)
          (178, "OCEAN SOFTWARE LTD"))
CREDIT_INK = 0xDB                   # G7 (GGGRRRBB): the strokes (glyph colour 1),
CREDIT_SHADE = 0x21                 #   their shadow (colour 4)
OVER_TEXT = "GAME OVER"
BAND = 16                           # lines below the game over picture (the text: 192 lines, 6 banks as PIC9)
VIEW_LINES = 162                    # msx/msx.inc: the play area, display lines 0-161 of page 0
# Brainstorm's scripts: label, address, the calls up to the end (elements + waits: the screen
# lasts one tick more without fire, 50 at least: front_stats' loop)
BONUS = (("txt_bs_intro", 0x114AA, 292), ("txt_bs_ok", 0x1162F, 143), ("txt_bs_fail", 0x11667, 136),
         ("txt_bs_time", 0x11698, 129))
INTRO_ELEMENTS = 100
# The intro's second line, "DESTROY ALL RED CHIPS ON THE BOARD", is 34 characters at column 2
# (x 0-271): fs_char would write its last two glyphs at the left edge of a line. The port's copy
# splits it after "CHIPS" (that space becomes a position: 5 positions and 95 characters, the
# original's 100 elements, so the screen lasts as long) and moves the later lines one row down,
# a blank row still between them; only the spacing moves. (column, row, text) of its lines:
INTRO_LINES = ((13, 0, "BRAINSTORM."), (8, 3, "DESTROY ALL RED CHIPS"), (13, 4, "ON THE BOARD"),
               (5, 6, "COMPLETE 4 TO REGAIN MEMORY."), (7, 8, "AND EARN A GAME CREDIT."))
INTRO_SPLIT = 21                    # the long line's character there (a space) becomes the position


def glyph_sc5(ram: bytes, g: int) -> bytes:
    """Glyph g as 8 lines of 4 SCREEN 5 bytes: plane 0 -> colour 1, plane 2 -> colour 4."""
    a = rc2front.BITMAP_FONT + 24 * g
    out = bytearray()
    for y in range(8):
        p0, p1, p2 = ram[a + y], ram[a + 8 + y], ram[a + 16 + y]
        assert p1 == 0 and p0 & p2 == 0, f"glyph {g}: colours other than 1 and 4"
        px = [(1 if p0 & (0x80 >> x) else 0) | (4 if p2 & (0x80 >> x) else 0) for x in range(8)]
        out += bytes(px[x] << 4 | px[x + 1] for x in range(0, 8, 2))
    return bytes(out)


def msx_palette(ram: bytes) -> bytes:
    """COLOR00 (black) + COLOR01-15 as V9938 palette pairs (before the colour grade)."""
    out = bytearray(b"\x00\x00")
    for i in range(15):
        c = struct.unpack_from(">H", ram, rc2front.TEXT_PALETTE + 2 * i)[0]
        r, g, b = (min(c >> s & 15, 14) for s in (8, 4, 0))
        r, g, b = (round(v * 7 / 15) for v in (r, g, b))
        out += bytes([r << 4 | b, g])
    return bytes(out)


def stats_script(ram: bytes) -> bytes:
    """The script's bytes up to and including its FF 07."""
    a = STATS
    while True:
        b = ram[a]
        if b == 0:
            a += 3
        elif b < 0x80:
            a += 1
        else:
            cmd = ram[a + 1]
            a += 3 if cmd in (2, 4) else 2
            if cmd == 7:
                return ram[STATS:a]
            assert cmd == 2, f"command {cmd} in the statistics script"


def bonus_script(ram: bytes, start: int) -> bytes:
    """A script's bytes up to and including its end (80-FF 07); only waits (80-FF 02 n) may come
    before it among the commands: front_stats' engine runs nothing else."""
    a = start
    while True:
        b = ram[a]
        if b == 0:
            a += 3
        elif b < 0x80:
            a += 1
        else:
            cmd = ram[a + 1]
            assert cmd in (2, 7), f"${start:05X}: command {cmd} at ${a:05X}"
            a += 3 if cmd == 2 else 2
            if cmd == 7:
                return ram[start:a]


def script_lines(script: bytes) -> tuple[list[tuple[int, int, bytes]], bytes]:
    """The lines (column, row, characters) of a script that starts with them, and the commands
    after them."""
    lines, a = [], 0
    while script[a] == 0:
        col, row = script[a + 1], script[a + 2]
        b = a = a + 3
        while 0 < script[a] < 0x80:
            a += 1
        lines.append((col, row, script[b:a]))
    return lines, script[a:]


def decode(chars: bytes) -> str:
    return "".join(rc2front.bitmap_char(c) for c in chars)


def intro_port(script: bytes) -> bytes:
    """The port's copy of the intro: the original's characters on INTRO_LINES."""
    lines, tail = script_lines(script)
    assert len(lines) == 4 and lines[1][2][INTRO_SPLIT] == 0x20, "the intro is not the expected one"
    long = lines[1][2]
    texts = [lines[0][2], long[:INTRO_SPLIT], long[INTRO_SPLIT + 1:], lines[2][2], lines[3][2]]
    assert [decode(t) for t in texts] == [t for _, _, t in INTRO_LINES], "the intro is not the expected one"
    return b"".join(bytes((0, col, row)) + t for (col, row, _), t in zip(INTRO_LINES, texts)) + tail


def fs_glyph(code: int) -> int:
    """msx/front.asm fs_char's glyph for a character code, in its 8-bit arithmetic ($118D6:
    ' ' 41, from '@' code - 'A', else code - 16h)."""
    if code == 0x20:
        return 41
    g = (code - 0x16) & 0xFF
    return g if g < 0x40 - 0x16 else (g - (0x41 - 0x16)) & 0xFF


def fs_run(script: bytes) -> tuple[int, int, list[tuple[int, int, int]]]:
    """msx/front.asm fs_step, called until it reads the end: (elements, calls, cells). Elements
    are the positions and the characters; calls are fs_step's calls before the one that reads
    the end (rc2front.py's count: a wait 80-FF 02 n takes max(1, 4n)); cells are (column, row,
    glyph) of each character, in the order fs_char draws them."""
    a = col = row = wait = calls = elements = 0
    cells = []
    while True:
        if wait:
            wait -= 1
        elif script[a] == 0:
            col, row = script[a + 1], script[a + 2]
            a += 3
            elements += 1
        elif script[a] < 0x80:
            cells.append((col, row, fs_glyph(script[a])))
            col = (col + 1) & 0xFF
            a += 1
            elements += 1
        elif script[a + 1] == 2:
            wait = max(1, 4 * script[a + 2]) - 1
            a += 3
        else:
            return elements, calls, cells
        calls += 1


def check_bonus(label: str, script: bytes, calls: int) -> None:
    """The script of a bonus text screen as the port shows it: positions, characters, waits and
    the end only, every glyph in the font, every line inside the play area, its calls."""
    lines, tail = script_lines(script)
    for col, row, chars in lines:
        x0, y0 = 8 * col - 16, 67 + 8 * row
        x1 = x0 + 8 * len(chars) - 1
        assert 0 <= x0 and x1 <= 255, f"{label}: {decode(chars)!r} at x {x0}-{x1}"
        assert y0 + 7 < VIEW_LINES, f"{label}: {decode(chars)!r} at lines {y0}-{y0 + 7}"
        assert all(fs_glyph(c) < rc2front.BITMAP_GLYPHS for c in chars), f"{label}: a code outside the font"
    a = 0
    while a + 3 <= len(tail) and tail[a] >= 0x80 and tail[a + 1] == 2:
        a += 3
    assert len(tail) == a + 2 and tail[a] >= 0x80 and tail[a + 1] == 7, f"{label}: not lines, waits, then the end"
    n = fs_run(script)[1]
    assert n == calls, f"{label}: {n} calls, the original {calls}"


def bonus_scripts(ram: bytes) -> list[tuple[str, int, bytes]]:
    """Brainstorm's scripts as the port holds them (label, address, bytes), checked."""
    out = []
    for label, start, calls in BONUS:
        script = bonus_script(ram, start)
        if label == "txt_bs_intro":
            assert fs_run(script)[:2] == (INTRO_ELEMENTS, calls), "the intro's elements"
            script = intro_port(script)
            assert fs_run(script)[0] == INTRO_ELEMENTS, "the port's intro: elements"
        check_bonus(label, script, calls)
        out.append((label, start, script))
    return out


def bonus_inc(scripts: list[tuple[str, int, bytes]]) -> str:
    text = "; Brainstorm's texts ($8382: the intro, then the result by $840A) for front.asm fe_text\n"
    for label, start, script in scripts:
        elements, calls, _ = fs_run(script)
        note = f"${start:05X}" + (", the long line split" if label == "txt_bs_intro" else "")
        text += f"{label}:{' ' * (35 - len(label))}; {note}: {elements} elements, {calls} calls\n" + db_lines(script)
    return text


def fs_render(glyphs: list[bytes], script: bytes) -> bytes:
    """The play area once the script has run (VIEW_LINES lines of 128 bytes, SCREEN 5): page 0
    cleared (front.asm fs_clear), then each character's glyph (8 lines of 4 bytes) written at
    byte 4 column - 8 of line 67 + 8 row, in fs_char's 8-bit arithmetic."""
    vram = bytearray(0x8000 + 4)
    for col, row, g in fs_run(script)[2]:
        c = (4 * col - 8) & 0xFF
        line = (8 * row + 67) & 0xFF
        for k in range(8):
            a = ((line + k) & 0xFF) << 7 | c
            vram[a:a + 4] = glyphs[g][4 * k:4 * k + 4]
    return bytes(vram[:VIEW_LINES * 128])


def write_sc5(path: Path, area: bytes, pal: bytes) -> None:
    """A SCREEN 5 play area (128 bytes a line) and its preview (.png) in pal (pf_pal's pairs;
    colour 0 black: the VBLANK never loads it)."""
    path.write_bytes(area)
    rgb = [bytes((0, 0, 0))] + [bytes(v * 255 // 7 for v in (pal[2 * i] >> 4 & 7, pal[2 * i + 1] & 7, pal[2 * i] & 7))
                                for i in range(1, 16)]
    rows = [b"".join(rgb[b >> 4] + rgb[b & 15] for b in area[y * 128:y * 128 + 128]) for y in range(len(area) // 128)]
    write_png(path.with_suffix(".png"), 256, len(rows), rows)


def draw_text(ram: bytes, out: bytearray, top: int, text: str, scale: int = 1) -> None:
    """text in the font into the SCREEN 8 picture out (256 bytes a line), centred, from line top,
    each glyph pixel scale x scale; the pixels between the strokes and the shadow are kept."""
    x0 = (256 - 8 * scale * len(text)) // 2
    for i, ch in enumerate(text):
        a = rc2front.BITMAP_FONT + 24 * rc2front.GLYPH_NAMES.index(ch)
        for y in range(8 * scale):
            p0, p2 = ram[a + y // scale], ram[a + 16 + y // scale]
            for x in range(8 * scale):
                o = (top + y) * 256 + x0 + 8 * scale * i + x
                if p0 & (0x80 >> x // scale):
                    out[o] = CREDIT_INK
                elif p2 & (0x80 >> x // scale):
                    out[o] = CREDIT_SHADE


def credit_sc8(ram: bytes, pic: bytes) -> bytes:
    """The title picture with CREDIT drawn into it."""
    out = bytearray(pic)
    for top, text in CREDIT:
        draw_text(ram, out, top, text)
    return bytes(out)


def over_sc8(ram: bytes, pic: bytes) -> bytes:
    """The game over picture with a band below it: GAME OVER at twice the size."""
    out = bytearray(pic) + bytes(256 * BAND)
    draw_text(ram, out, len(pic) // 256 + (BAND - 16) // 2, OVER_TEXT, 2)
    return bytes(out)


def write_sc8(path: Path, pic: bytes) -> None:
    """The SCREEN 8 picture and its preview (.png)."""
    path.write_bytes(pic)
    write_png(path.with_suffix(".png"), 256, len(pic) // 256,
              [b"".join(g7_rgb(v) for v in pic[y * 256:y * 256 + 256]) for y in range(len(pic) // 256)])


def g7_rgb(v: int) -> bytes:
    return bytes((round((v >> 2 & 7) * 255 / 7), round((v >> 5) * 255 / 7), round((v & 3) * 255 / 3)))


def db_lines(data: bytes, per: int = 16) -> str:
    return "".join("        db " + ", ".join(f"0x{v:02X}" for v in data[i:i + per]) + "\n"
                   for i in range(0, len(data), per))


def level_inc(ram: bytes) -> str:
    """text.inc up to its glyphs: the font, the palette and the level statistics."""
    script = stats_script(ram)
    return ("; generated by tools/msxtext.py: the text screens' font, palette and the level statistics\n"
            f"TXT_STATS_LEN: equ {len(script)}\n"
            + "".join(f"TXT_F{i + 1}: equ {f - STATS}{' ' * 12}; its number field ($11DC6: 8 characters)\n"
                      for i, f in enumerate(STATS_FIELDS))
            + "txt_pal:                            ; $109A8 (pf_pal's format)\n" + db_lines(grade_pal(msx_palette(ram)))
            + "txt_stats:                          ; $1132F\n" + db_lines(script)
            + f"txt_glyphs:                         ; $65DB0: {rc2front.BITMAP_GLYPHS} x 8 lines x 4 bytes\n"
            + "".join(f"        ; {rc2front.GLYPH_NAMES[g]!r}\n" + db_lines(glyph_sc5(ram, g))
                      for g in range(rc2front.BITMAP_GLYPHS)))


def main(argv: list[str]) -> int:
    ram = Path(argv[1] if len(argv) > 1 else ROOT / "build/ram/level1_full.bin").read_bytes()
    out = Path(argv[2] if len(argv) > 2 else ROOT / "build/msx/text.inc")
    bonus = bonus_scripts(ram)
    out.write_text(level_inc(ram) + bonus_inc(bonus))
    print(f"{out}: {rc2front.BITMAP_GLYPHS} glyphs, statistics script {len(stats_script(ram))} bytes")
    glyphs = [glyph_sc5(ram, g) for g in range(rc2front.BITMAP_GLYPHS)]
    pal = grade_pal(msx_palette(ram))
    for label, _, script in bonus:
        write_sc5(out.parent / (label.replace("txt_", "text_") + ".sc5"), fs_render(glyphs, script), pal)
    print(f"{out}: Brainstorm's texts, " + ", ".join(f"{label} {len(s)} bytes ({fs_run(s)[1]} calls)"
                                                  for label, _, s in bonus)
          + f"; their play areas in {out.parent / 'text_bs_*.sc5'} (.png)")
    if len(argv) > 4:
        write_sc8(Path(argv[4]), credit_sc8(ram, Path(argv[3]).read_bytes()))
        print(f"{argv[4]}: the title with the credit ({len(CREDIT)} lines)")
    if len(argv) > 6:
        write_sc8(Path(argv[6]), over_sc8(ram, Path(argv[5]).read_bytes()))
        print(f"{argv[6]}: the game over picture with {OVER_TEXT} below it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
