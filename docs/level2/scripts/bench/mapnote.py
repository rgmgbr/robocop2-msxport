#!/usr/bin/env python3
"""Annotates the level-2 map render (2560 x 800) with the spawn list, object list, special records."""
import struct, sys
from PIL import Image, ImageDraw
src, ram_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
ram = open(ram_path, 'rb').read()
im = Image.open(src).convert('RGB')
d = ImageDraw.Draw(im)
for x in range(0, 2560, 160):
    d.line([(x, 0), (x, 799)], fill=(60, 60, 60))
    d.text((x + 2, 2), str(x), fill=(255, 255, 255))
for y in range(0, 800, 80):
    d.line([(0, y), (2559, y)], fill=(60, 60, 60))
    d.text((2, y + 2), str(y), fill=(255, 255, 255))
a = 0x97B0; i = 0
while struct.unpack_from('>h', ram, a)[0] >= 0:
    x, y, t = struct.unpack_from('>hhB', ram, a)
    d.rectangle([x - 4, y - 4, x + 4, y + 4], outline=(255, 0, 0))
    d.text((x + 6, y - 6), f"s{i}:{t}", fill=(255, 80, 80))
    a += 14; i += 1
a = 0xA828; i = 0
while struct.unpack_from('>h', ram, a)[0] >= 0:
    w = struct.unpack_from('>6h', ram, a)
    x, y = w[4], w[5]
    d.rectangle([x - 3, y - 3, x + 3, y + 3], outline=(0, 255, 255))
    d.text((x + 5, y + 2), f"o{i}:{w[0]:x}", fill=(0, 255, 255))
    a += 12; i += 1
lst = 0x8FE0; k = 0
while True:
    p = struct.unpack_from('>I', ram, lst)[0]
    if p == 0xFFFFFFFF: break
    w = struct.unpack_from('>8h', ram, p)
    t, x, y = w[0], w[1], w[2]
    col = (255, 255, 0) if t == 0 else (255, 0, 255)
    d.rectangle([x - 6, y - 6, x + 6, y + 6], outline=col)
    d.text((x + 8, y - 14), f"{'L' if t == 0 else 'T'}{k}@{p:x}", fill=col)
    lst += 4; k += 1
x, y = 352, 784
d.ellipse([x - 8, y - 8, x + 8, y + 8], outline=(0, 255, 0), width=2)
d.text((x + 10, y - 10), "START", fill=(0, 255, 0))
im.save(out)
w, h = im.size
im.crop((0, 0, 1280, 800)).save(out.replace('.png', '_a.png'))
im.crop((1280, 0, 2560, 800)).save(out.replace('.png', '_b.png'))
