"""Shelf packing (tools/msxsprites.py field_frames' rule: by height, then width) of level 2's
play-field frames, as stored today (blit boxes) and trimmed to their pixel boxes (even x and width)."""
import json, sys
fr = {f"{f['addr']:X}": f for f in json.load(open(sys.argv[1]))}
static = ["498DC", "49F6C", "4A5FC", "4AC8C", "4B31C", "4B68A", "4B95A", "3D280", "3D910", "3DFA0", "3E3D8",
          "40818", "40AE8", "40DB8", "41088"]
def pack(items, W=256):
    items = sorted(items, key=lambda t: (-t[2], -t[1], t[0]))
    x = y = shelf = 0
    for k, w, h in items:
        if x + w > W:
            x, y, shelf = 0, y + shelf, 0
        x += w
        shelf = max(shelf, h)
    return y + shelf
full = [(k, fr[k]["w"], fr[k]["h"]) for k in static]
trim = []
for k in static:
    x0, y0, x1, y1 = fr[k]["box"]
    x0 -= x0 % 2
    w = x1 - x0 + (x1 - x0) % 2
    trim.append((k, w, y1 - y0))
print("blit boxes:", pack(full), "lines; pixel boxes:", pack(trim), "lines (88 available above the dynamic slot)")
for sub, name in ((["3D280", "3D910"], "type 2 streamed"), (["3DFA0", "3E3D8"], "type 14 streamed"),
                  (["40818", "40AE8", "40DB8", "41088"], "type 16 streamed")):
    print(f"  {name}: blit {pack([t for t in full if t[0] not in sub])}, pixel {pack([t for t in trim if t[0] not in sub])}")
print("area blit", sum(w * h for _, w, h in full), "pixel", sum(w * h for _, w, h in trim), "of", 256 * 88)
