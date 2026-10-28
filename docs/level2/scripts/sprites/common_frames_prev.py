"""Frames of the shared drawing routines from the original's tables (data in main_8000.bin),
used to classify the level-1 bench coverage frames by routine."""
import json, struct, sys
from pathlib import Path
ROOT = Path(sys.argv[1])
m = (ROOT / "build/extracted/boot/main_8000.bin").read_bytes()
w = lambda a: struct.unpack_from(">h", m, a - 0x8000)[0]
uw = lambda a: struct.unpack_from(">H", m, a - 0x8000)[0]
ul = lambda a: struct.unpack_from(">L", m, a - 0x8000)[0]
def dims(d4):
    return ((d4 & 63) - 1) * 16, d4 >> 6
F = {}
def add(name, addr, d4):
    wd, h = dims(d4)
    if wd > 0 and h > 0:
        F.setdefault((addr, wd, h), set()).add(name)
for i in range(16):
    add("walker1 legs", 0x4BD06 + w(0xC9B4 + 2 * i), uw(0xC9D4 + 2 * i))
for i in range(20):
    add("walker2 legs", 0x4F1D6 + w(0xCBFA + 2 * i), uw(0xCC22 + 2 * i))
    add("type3 torso", 0x4F1D6 + w(0xCBAA + 2 * i), uw(0xCBD2 + 2 * i))
for i in range(6):
    add("gunman torso", 0x4E466 + w(0xCB4A + 2 * i), uw(0xCB56 + 2 * i))
for i in range(8):
    add("type4 torso", 0x57192 + w(0xD066 + 2 * i), uw(0xD096 + 2 * i))
for i in range(40):
    add("explosion", ul(0xF1C6 + 4 * i), uw(0xF140 + 2 * i))
for i in range(9):
    add("explosion F266", 0x45250 + w(0xF2E6 + 2 * i), uw(0xF2F8 + 2 * i))
    if uw(0xF340 + 2 * i):
        add("explosion F266", 0x45250 + w(0xF32E + 2 * i), uw(0xF340 + 2 * i))
for t in range(23):
    g, d4 = ul(0xF4A4 + 4 * t), uw(0xF500 + 4 * t)
    step, lim = w(0xF55C + 4 * t), w(0xF55C + 4 * t + 2)
    wd, h = dims(d4)
    n = 1 if step <= 0 else max(1, lim // step + 1) if lim > 0 else 1
    for k in range(min(n, 8)):
        add(f"enemy bullet {t}", g + k * max(step, 0), d4)
for i in range(11):
    add("pickup", ul(0xF964 + 4 * i), 0x402)
for i in range(8):
    add("shot", 0x6BEA0 + w(0xAF76 + 2 * i), 0x402)
    add("muzzle flash", 0x6B9A0 + 0x50 * 2 * i // 2 * 1, 0x402)
for i in range(16):
    add("hostage top", 0x498DC + w(0xEDE2 + 2 * i), 0xE04)
add("hostage legs", 0x4B31C, 0x503)
json.dump({f"{a:x}:{wd}:{h}": sorted(v) for (a, wd, h), v in F.items()}, open(sys.argv[2], "w"), indent=0)
cov = json.load(open(ROOT / "build/emu/cov_level1.json"))["bobs"]
def region(a):
    if 0x28000 <= a < 0x45250: return "DATAL1"
    if 0x45250 <= a < 0x4B54C: return "MADEX"
    if 0x4B68A <= a < 0x5884E: return "SPERMA"
    if 0x58850 <= a < 0x6FFA0: return "PERMA"
    return "other"
unk = []
for f in cov:
    k = (f["addr"], f["w"], f["h"])
    if k in F:
        continue
    unk.append(f"{region(f['addr'])} {f['addr']:X}:{f['w']}x{f['h']} n={f['count']}")
print(len(F), "frames from the tables;", len(cov), "coverage frames;", len(unk), "unexplained:")
print("\n".join(sorted(unk)))
