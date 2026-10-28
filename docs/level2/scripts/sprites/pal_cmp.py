"""Level 1's and level 2's Amiga background colours mapped onto level 1's MSX joint palette
(nearest in CIELAB from entry 1, as tools/msxsprites.py maps BOB pixels)."""
import sys, struct
sys.path.insert(0, sys.argv[1])
import numpy as np
import msxsprites as ms
main = open(sys.argv[2], "rb").read()
raw = open(sys.argv[3], "rb").read()
def pal(addr):
    return [struct.unpack_from(">H", main, addr - 0x8000 + 2 * i)[0] for i in range(31)]
p1, p2 = pal(0xFFF6), pal(0x10036)
fixed = np.array([[(raw[2 * k] >> 4) & 7, raw[2 * k + 1] & 7, raw[2 * k] & 7] for k in range(16)], float) / 7
bg1 = np.array([[0, 0, 0]] + [ms.amiga_rgb(c) for c in p1[:15]])
bg2 = np.array([[0, 0, 0]] + [ms.amiga_rgb(c) for c in p2[:15]])
n1, n2 = ms.nearest(bg1, fixed, 1), ms.nearest(bg2, fixed, 1)
q = np.round(fixed * 7).astype(int)
for i in range(16):
    a1 = p1[i - 1] if i else 0
    a2 = p2[i - 1] if i else 0
    print(i, f"L1 {a1:03x}->{n1[i]:2d} ({''.join(map(str, q[n1[i]]))})  L2 {a2:03x}->{n2[i]:2d} ({''.join(map(str, q[n2[i]]))})",
          "" if n1[i] == n2[i] else "  DIFFERENT")
print("sprite colours 17-31 identical:", p1[16:31] == p2[16:31])
