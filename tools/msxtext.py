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
- The shooting range's texts ($8420 after Brainstorm, each through $10762; msx/front.asm
  front_range runs them with fe_text), appended after Brainstorm's with the same checks: the
  intro ($1142D, txt_rg_intro: its long line does not fit 256 pixels either, so the port's copy
  splits it, RG_INTRO_LINES), the result ($113A5, txt_rg_res: its three 8-character fields
  blank, at TXT_RG_F1-3; front_range copies its TXT_RG_LEN bytes to fs_buf, at most FS_BUF, puts
  the correct and the dummy counts in with fs_num, $11DC6's format, and the rating's name) and
  the ratings' names ($1140D, txt_rg_rate: POOR to SHARP, 8 characters each). The time out is
  Brainstorm's txt_bs_time ($11698: the original shares it). Their play areas are the references
  for the range's screens: text_rg_intro.sc5, text_rg_time.sc5 and text_rg_res_cC_dD_mM.sc5 for
  the counts of RG_RESULTS (every rating), each with its preview (.png); render-result writes
  the result's for any counts.
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
       msxtext.py render-result CORRECT DUMMY MINUTES [-o OUT.sc5] [--rating R] [--tag N] [--ram RAM_IMAGE]
       (the range's result screen for the counts, $B04 and $B06, and the timer's minutes at the
       end, $804A: its play area, its preview and the rating; --rating shows that rating's name
       instead, --tag the TEST n line of a TAG build)
"""
from __future__ import annotations

import argparse
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
# The shooting range's scripts ($8420 after Brainstorm: the intro, then the result; a time out
# shows Brainstorm's txt_bs_time, the original's shared $11698): label, address, the calls up to
# the end
RANGE = (("txt_rg_intro", 0x1142D, 304), ("txt_rg_res", 0x113A5, 347))
RG_INTRO_ELEMENTS = 112
# The intro's third line, "YOUR GUN CALIBRATION WILL BE TESTED", is 35 characters at column 1
# (x -8 to 271). The port's copy splits it after "CALIBRATION" over rows 5 and 6 (that space
# becomes a position: 5 positions and 107 characters, the original's 112 elements, so the
# screen lasts as long) and moves the last line from row 7 to row 8, a blank row still before
# it; only the spacing moves (Brainstorm's rule). (column, row, text) of its lines:
RG_INTRO_LINES = ((11, 0, "SHOOTING RANGE."), (5, 3, "YOU MUST SHOOT ARMED TARGETS"),
                  (9, 5, "YOUR GUN CALIBRATION"), (12, 6, "WILL BE TESTED"),
                  (4, 8, "WARNING ACCURACY IS ESSENTIAL."))
RG_INTRO_LONG = 2                   # the long line,
RG_INTRO_SPLIT = 20                 #   its character there (a space) becomes the position
# The result's 8-character fields, blank in the script ($8420 fills a copy): the correct count
# ($B04, with $11DC6), the dummy count ($B06), the rating's name (8 bytes of $1140D)
RG_FIELDS = (0x113CA, 0x113E4, 0x11400)
RG_NAMES = 0x1140D                  # the ratings' names by rating, 8 characters each
RG_NAME_TEXT = ("POOR.   ", "FAIR.   ", "GOOD.   ", "SHARP.  ")
FS_BUF = 120                        # msx/msx.inc: fs_ptr - fs_buf, the room of a script with numbers
# The result's references written with text.inc: (correct, dummy, the timer's minutes) for
# SHARP, GOOD, FAIR, SHARP with the minutes at 0, and POOR
RG_RESULTS = ((16, 0, 1), (15, 0, 1), (13, 2, 1), (25, 0, 0), (0, 0, 2))


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


def rg_intro_port(script: bytes) -> bytes:
    """The port's copy of the range's intro: the original's characters on RG_INTRO_LINES."""
    lines, tail = script_lines(script)
    k, n = RG_INTRO_LONG, RG_INTRO_SPLIT
    assert len(lines) == 4 and lines[k][2][n] == 0x20, "the range's intro is not the expected one"
    texts = [chars for _, _, chars in lines]
    texts[k:k + 1] = [texts[k][:n], texts[k][n + 1:]]
    assert [decode(t) for t in texts] == [t for _, _, t in RG_INTRO_LINES], "the range's intro is not the expected one"
    return b"".join(bytes((0, col, row)) + t for (col, row, _), t in zip(RG_INTRO_LINES, texts)) + tail


def range_scripts(ram: bytes) -> list[tuple[str, int, bytes]]:
    """The range's scripts as the port holds them (label, address, bytes), checked: the intro
    split, the result's fields blank (fs_num writes only the digits) and its bytes within
    fs_buf."""
    out = []
    for label, start, calls in RANGE:
        script = bonus_script(ram, start)
        if label == "txt_rg_intro":
            assert fs_run(script)[:2] == (RG_INTRO_ELEMENTS, calls), "the range's intro: elements"
            script = rg_intro_port(script)
            assert fs_run(script)[0] == RG_INTRO_ELEMENTS, "the port's range intro: elements"
        else:
            assert all(script[f - start:f - start + 8] == b" " * 8 for f in RG_FIELDS), f"{label}: a field not blank"
            assert len(script) <= FS_BUF, f"{label}: {len(script)} bytes, more than fs_buf's {FS_BUF}"
        check_bonus(label, script, calls)
        out.append((label, start, script))
    return out


def rg_names(ram: bytes) -> bytes:
    """$1140D: the ratings' names, POOR (0) to SHARP (3), 8 characters each, checked."""
    names = ram[RG_NAMES:RG_NAMES + 32]
    assert [decode(names[i:i + 8]) for i in range(0, 32, 8)] == list(RG_NAME_TEXT), "the ratings' names"
    return names


def num_field(n: int) -> bytes:
    """A blank 8-character field after front.asm fs_num (n 0-65535): the digits ('[' + digit) from
    the field's end back, the spaces before them kept ($11DC6: leading zeros as spaces, 0 as one
    digit)."""
    if not 0 <= n <= 0xFFFF:
        raise ValueError(f"{n}: not a 16-bit count")
    s = str(n)
    return b" " * (8 - len(s)) + bytes(0x5B + int(ch) for ch in s)


def rg_rating(correct: int, dummy: int, minutes: int) -> int:
    """$84C0-$84EE (ported by msx/front.asm front_range): 6 correct - dummy - 50, 12 less when the
    timer's minutes ($804A) are 0, in 16-bit words; negative POOR (0), else its div 14, at most
    SHARP (3)."""
    s = (6 * correct - dummy - 50 - (12 if minutes == 0 else 0)) & 0xFFFF
    return 0 if s & 0x8000 else min(3, s // 14)


def rg_fill(script: bytes, names: bytes, correct: int, dummy: int, rating: int) -> bytes:
    """txt_rg_res as front_range leaves it in fs_buf for fe_text: the correct and the dummy counts
    in their fields (fs_num) and the rating's name, checked."""
    if rating not in range(4):
        raise ValueError(f"rating {rating}: not 0-3")
    label, start, calls = RANGE[1]
    s = bytearray(script)
    for f, v in zip(RG_FIELDS, (num_field(correct), num_field(dummy), names[8 * rating:8 * rating + 8])):
        s[f - start:f - start + 8] = v
    check_bonus(label, bytes(s), calls)
    return bytes(s)


def tag_line(tag: int) -> bytes:
    """front.asm fe_text's TEST n line of a TAG build (row 10, drawn before the script) as script
    bytes (a position and its characters); none for TAG 0."""
    if not 0 <= tag <= 99:
        raise ValueError(f"TAG {tag}: not 0-99")
    return bytes((0, 14 if tag > 9 else 15, 10)) + b"TEST " + str(tag).encode() if tag else b""


def range_inc(scripts: list[tuple[str, int, bytes]], names: bytes) -> str:
    """text.inc's part for the range: the result's equates, the scripts and the names."""
    _, start, res = scripts[1]
    equ = [("TXT_RG_LEN", len(res), "txt_rg_res' bytes: front_range fills a copy in fs_buf"),
           ("TXT_RG_F1", RG_FIELDS[0] - start, "the correct count's field ($113CA: $11DC6, 8 characters)"),
           ("TXT_RG_F2", RG_FIELDS[1] - start, "the dummy count's field ($113E4)"),
           ("TXT_RG_F3", RG_FIELDS[2] - start, "the rating's name ($11400: 8 bytes of txt_rg_rate)")]
    text = ("; The shooting range's texts ($8420 after Brainstorm: the intro, then the result; a time out\n"
            "; shows txt_bs_time) for front.asm front_range and fe_text\n"
            + "".join(f"{f'{k}: equ {v}':<36}; {what}\n" for k, v, what in equ))
    for label, start, script in scripts:
        elements, calls, _ = fs_run(script)
        note = f"${start:05X}" + (", the long line split" if label == "txt_rg_intro" else ", its fields blank")
        text += f"{label}:{' ' * (35 - len(label))}; {note}: {elements} elements, {calls} calls\n" + db_lines(script)
    return (text + f"txt_rg_rate:{' ' * 24}; ${RG_NAMES:05X}: the ratings' names, 8 bytes each: "
            + ", ".join(t.rstrip(". ") for t in RG_NAME_TEXT) + "\n" + db_lines(names))


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


def render_result(argv: list[str]) -> int:
    """msxtext.py render-result (the module's usage): the range's result screen for given counts."""
    ap = argparse.ArgumentParser(
        prog="msxtext.py render-result",
        description="The shooting range's result screen as front.asm front_range shows it (txt_rg_res filled "
                    "in fs_buf, through fe_text): its play area (page 0's lines 0-161, SCREEN 5) and its "
                    "preview (.png); prints the rating and ac_diff's offset into diff_tab.")
    ap.add_argument("correct", type=int, help="the correct targets ($B04)")
    ap.add_argument("dummy", type=int, help="the dummy targets ($B06)")
    ap.add_argument("minutes", type=int, help="the timer's minutes at the end ($804A): 0 costs 12")
    ap.add_argument("-o", "--out", type=Path,
                    help="the .sc5 to write (default: build/msx/text_rg_res_cC_dD_mM[_rR][_tN].sc5)")
    ap.add_argument("--rating", type=int, choices=range(4),
                    help="show this rating's name (0 POOR to 3 SHARP) instead of the counts' rating")
    ap.add_argument("--tag", type=int, default=0, help="the build's TAG: TEST n at row 10 (0-99)")
    ap.add_argument("--ram", type=Path, default=ROOT / "build/ram/level1_full.bin",
                    help="the RAM image (default: build/ram/level1_full.bin)")
    a = ap.parse_args(argv)
    for v, what, top in ((a.correct, "correct", 0xFFFF), (a.dummy, "dummy", 0xFFFF), (a.minutes, "minutes", 255),
                         (a.tag, "--tag", 99)):
        if not 0 <= v <= top:
            ap.error(f"{what} {v}: not 0-{top}")
    ram = a.ram.read_bytes()
    rating = rg_rating(a.correct, a.dummy, a.minutes)
    shown = rating if a.rating is None else a.rating
    script = tag_line(a.tag) + rg_fill(range_scripts(ram)[1][2], rg_names(ram), a.correct, a.dummy, shown)
    out = a.out or ROOT / "build" / "msx" / (f"text_rg_res_c{a.correct}_d{a.dummy}_m{a.minutes}"
                                             + (f"_r{shown}" if a.rating is not None else "")
                                             + (f"_t{a.tag}" if a.tag else "") + ".sc5")
    out.parent.mkdir(parents=True, exist_ok=True)
    glyphs = [glyph_sc5(ram, g) for g in range(rc2front.BITMAP_GLYPHS)]
    write_sc5(out, fs_render(glyphs, script), grade_pal(msx_palette(ram)))
    print(f"{out}: correct {a.correct}, dummy {a.dummy}, minutes {a.minutes}: rating {rating} "
          f"({RG_NAME_TEXT[rating].rstrip('. ')}), ac_diff = diff_tab + {24 - 8 * rating}"
          + (f"; the name shown: rating {shown} ({RG_NAME_TEXT[shown].rstrip('. ')})" if shown != rating else "")
          + (f"; TEST {a.tag} at row 10" if a.tag else ""))
    return 0


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] == "render-result":
        return render_result(argv[2:])
    ram = Path(argv[1] if len(argv) > 1 else ROOT / "build/ram/level1_full.bin").read_bytes()
    out = Path(argv[2] if len(argv) > 2 else ROOT / "build/msx/text.inc")
    bonus = bonus_scripts(ram)
    rg, names = range_scripts(ram), rg_names(ram)
    out.write_text(level_inc(ram) + bonus_inc(bonus) + range_inc(rg, names))
    print(f"{out}: {rc2front.BITMAP_GLYPHS} glyphs, statistics script {len(stats_script(ram))} bytes")
    glyphs = [glyph_sc5(ram, g) for g in range(rc2front.BITMAP_GLYPHS)]
    pal = grade_pal(msx_palette(ram))
    for label, _, script in bonus:
        write_sc5(out.parent / (label.replace("txt_", "text_") + ".sc5"), fs_render(glyphs, script), pal)
    print(f"{out}: Brainstorm's texts, " + ", ".join(f"{label} {len(s)} bytes ({fs_run(s)[1]} calls)"
                                                  for label, _, s in bonus)
          + f"; their play areas in {out.parent / 'text_bs_*.sc5'} (.png)")
    scripts = {label: s for label, _, s in bonus + rg}
    write_sc5(out.parent / "text_rg_intro.sc5", fs_render(glyphs, scripts["txt_rg_intro"]), pal)
    write_sc5(out.parent / "text_rg_time.sc5", fs_render(glyphs, scripts["txt_bs_time"]), pal)
    for c, d, m in RG_RESULTS:
        res = rg_fill(scripts["txt_rg_res"], names, c, d, rg_rating(c, d, m))
        write_sc5(out.parent / f"text_rg_res_c{c}_d{d}_m{m}.sc5", fs_render(glyphs, res), pal)
    print(f"{out}: the range's texts, " + ", ".join(f"{label} {len(s)} bytes ({fs_run(s)[1]} calls)"
                                                 for label, _, s in rg)
          + f", txt_rg_rate {len(names)} bytes, the time out txt_bs_time; their play areas in "
          + f"{out.parent / 'text_rg_*.sc5'} (.png): the intro, the time out, the result for "
          + ", ".join(f"{c}/{d}/{m} ({RG_NAME_TEXT[rg_rating(c, d, m)].rstrip('. ')})" for c, d, m in RG_RESULTS))
    if len(argv) > 4:
        write_sc8(Path(argv[4]), credit_sc8(ram, Path(argv[3]).read_bytes()))
        print(f"{argv[4]}: the title with the credit ({len(CREDIT)} lines)")
    if len(argv) > 6:
        write_sc8(Path(argv[6]), over_sc8(ram, Path(argv[5]).read_bytes()))
        print(f"{argv[6]}: the game over picture with {OVER_TEXT} below it")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
