#!/usr/bin/env python3
"""The movie stills for the MSX (msx/photo.asm; docs/AMIGA_ANALYSIS.md, "Pictures"): PIC1-PIC7 and the
final picture PICF from the extracted files, as SCREEN 8 pictures packed with ZX0 (tools/zx0.py), for
tools/mkrom.py PHOTOS=1 builds.

- PIC1-PIC7: HAM6 320 x 176 (a 128-byte header: 32 OCS colours and zeros, the six planes from +80h;
  show_picture $11E06 shows all 176 lines, display lines 30-205), decoded as tools/planar.py does.
- PICF: HAM6 320 x 256; $11C54 shows its lines 0-223 (the picture's copper $12352 turns the planes on
  at display line 30, its COP2 list $123EA off at line 254). The MSX's 212 lines are its lines 0-211:
  RoboCop's helmet reaches line 4, so the 12 visible lines left out are the bottom's. $11C54 first
  clears 141 bytes at the picture's start and every 2800h bytes after it (the first 13 bytes of
  planes 0-3's line 0 and the last 128 of planes 0-2; its two other clears, at -6000h and -3800h
  through sign-extended word indexes, land before the picture), so the conversion does too.
- Each picture to SCREEN 8 with tools/msxpic.py's conversion (320 -> 256 wide, Floyd-Steinberg on
  the fixed G7 palette), then ZX0 with offsets up to 256 (the line above among them: msx/photo.asm
  copies from a 256-byte ring in RAM, never reading VRAM back) and a penalty for every copy (PENALTY:
  the unpacking's time); every stream is unpacked again and compared.

Outputs, in OUTDIR: photos.bin (the streams one after another), photos.json (per picture its name,
lines, offset and size in photos.bin), photo_<NAME>.sc8 / .png (the conversion and its preview),
photos_sheet.png (a contact sheet: the eight and the game over picture, gameover_text.png, as the
MSX shows them, 256 x 212 each). A picture whose .sc8 is newer than its source and this tool is not
converted again.

usage: msxphoto.py FILES_DIR OUTDIR   (requires numpy and Pillow)
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import msxpic  # noqa: E402
import planar  # noqa: E402
import zx0  # noqa: E402

# (name, extracted file, height, lines kept): in show_picture's order (D0 = 0-6), then PICF
PHOTOS = (("PIC1", "PIC1_08.bin", 176, 176), ("PIC2", "PIC2_14.bin", 176, 176), ("PIC3", "PIC3_12.bin", 176, 176),
          ("PIC4", "PIC4_16.bin", 176, 176), ("PIC5", "PIC5_19.bin", 176, 176), ("PIC6", "PIC6_20.bin", 176, 176),
          ("PIC7", "PIC7_21.bin", 176, 176), ("PICF", "PICF_23.bin", 256, 212))
HEADER = 0x80
PICF_CLEAR = (0x0000, 0x2800, 0x5000, 0x7800)   # $11C54's clears inside the file (from $6FFA0), 141 bytes
SCREEN_LINES = 212
MAX_OFFSET = 256                    # msx/photo.asm pho_unz keeps the last 256 bytes in RAM: no copy reads VRAM
PENALTY = 12                        # bits added to every copy (zx0.py): fewer, longer copies, each costs the
                                    # Z80 about 220 T-states besides its bytes; 12 takes the unpacking from
                                    # 1.3-2.5 s to 1.0-1.6 s a picture for 6 banks more (30, against 24)


def decode(path: Path, height: int, clear: bool) -> Image.Image:
    data = bytearray(path.read_bytes())
    pal = [planar.rgb12_to_rgb24(struct.unpack_from(">H", data, 2 * i)[0]) for i in range(16)]
    if clear:                           # (after the palette went to the copper list: $11EA6 first)
        for at in PICF_CLEAR:
            data[at:at + 141] = bytes(141)
    idx = planar.decode_indices(bytes(data), HEADER, 320, height, 6, "planes")
    rows = planar.render(idx, pal, True, 1)
    return Image.frombytes("RGB", (320, height), b"".join(rows))


def screen(prev: Image.Image) -> Image.Image:
    """A picture as the MSX shows it: centred on 212 black lines (msx/photo.asm pz_show)."""
    img = Image.new("RGB", (256, SCREEN_LINES))
    img.paste(prev, (0, (SCREEN_LINES - prev.size[1]) // 2 if prev.size[1] < SCREEN_LINES else 0))
    return img


def main(argv: list[str]) -> int:
    files, out = Path(argv[1]), Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    tool = max(Path(__file__).stat().st_mtime, Path(msxpic.__file__).stat().st_mtime)
    blob, manifest, sheet = b"", [], []
    for name, fn, height, keep in PHOTOS:
        src = files / fn
        sc8, png = out / f"photo_{name}.sc8", out / f"photo_{name}.png"
        if sc8.exists() and png.exists() and sc8.stat().st_mtime > max(src.stat().st_mtime, tool):
            code = sc8.read_bytes()
        else:
            rgb = decode(src, height, name == "PICF").crop((0, 0, 320, keep))
            c, prev = msxpic.to_sc8(rgb)
            code = c.tobytes()
            Image.fromarray(prev).save(png)
            sc8.write_bytes(code)
        assert len(code) == 256 * keep, f"{sc8}: {len(code)} bytes"
        packed = zx0.pack(code, 256, PENALTY, MAX_OFFSET)
        if zx0.unpack(packed) != code:
            print(f"error: {name}'s ZX0 stream does not unpack to its picture", file=sys.stderr)
            return 1
        manifest.append({"name": name, "file": fn, "lines": keep, "offset": len(blob), "size": len(packed)})
        print(f"{sc8}: 256 x {keep}, {len(code)} bytes -> ZX0 {len(packed)} bytes ({100 * len(packed) / len(code):.1f} %)")
        blob += packed
        sheet.append((name, screen(Image.open(png).convert("RGB"))))
    (out / "photos.bin").write_bytes(blob)
    (out / "photos.json").write_text(json.dumps(manifest, indent=1) + "\n")
    over = out / "gameover_text.png"
    if over.exists():
        sheet.append(("PIC9 (game over)", screen(Image.open(over).convert("RGB"))))
    cols = 3
    w, h = 256 + 8, SCREEN_LINES + 20
    rows = -(-len(sheet) // cols)
    img = Image.new("RGB", (cols * w + 8, rows * h + 8), (40, 40, 40))
    d = ImageDraw.Draw(img)
    for k, (name, pic) in enumerate(sheet):
        x, y = 8 + (k % cols) * w, 8 + (k // cols) * h
        img.paste(pic, (x, y + 14))
        d.text((x, y), name, fill=(255, 255, 255))
    img.save(out / "photos_sheet.png")
    print(f"{out / 'photos.bin'}: {len(blob)} bytes, {len(manifest)} pictures ({-(-len(blob) // 8192)} banks); "
          f"the contact sheet {out / 'photos_sheet.png'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
