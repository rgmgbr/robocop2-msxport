#!/usr/bin/env python3
"""Summarises a bench trace-ram (JSON lines): per game frame the enemy slots (type, hp, x, y), the
player, the specials' records, the level's end; prints the frames where the slot types change, and a
summary of the types seen (with first frame) and of the events."""
import json, sys
RAM0, GLOB0 = 0xB00, 0x8000
def w(b, a, signed=True):
    v = int.from_bytes(b[a - RAM0:a - RAM0 + 2], 'big'); return v - 0x10000 if signed and v >= 0x8000 else v
def by(b, a): return b[a - RAM0]
def g(gl, a, n=2): return int.from_bytes(gl[a - GLOB0:a - GLOB0 + n], 'big')
seen, events, last = {}, [], None
prev = {}
step = int(sys.argv[2]) if len(sys.argv) > 2 else 0
for n, line in enumerate(open(sys.argv[1])):
    r = json.loads(line)
    if 'ram' not in r: continue
    b = bytes.fromhex(r['ram']); gl = bytes.fromhex(r['glob'])
    slots = []
    for k in range(5):
        t = by(b, 0xC04 + 4 * k)
        if t:
            slots.append((t, by(b, 0xC05 + 4 * k), w(b, 0xBC4 + 4 * k), w(b, 0xB64 + 4 * k)))
            seen.setdefault(t, n)
    types = tuple(s[0] for s in slots)
    st = {'lives': g(gl, 0x8034), 'level': g(gl, 0x8050), 'done': by(b, 0x16D0), 'dying': by(b, 0x16CC),
          'hostages': w(b, 0x16BE), 'henchmen': w(b, 0x16C2), 'nukes': w(b, 0x16C0), 'riding': by(b, 0x16D8),
          'lift': tuple(by(b, a) for a in (0x167A, 0x167B, 0x167C, 0x167D)), 'timeout': gl[0x4C], 'weapon': g(gl, 0x805C)}
    for k, v in st.items():
        if prev.get(k) != v and n > 0:
            events.append((n, k, prev.get(k), v))
    prev = st
    if types != last or (step and n % step == 0):
        print(f"gf {n:5d} p=({r['player_x']},{r['player_y']}) st={r['state']} cam=({r['camera_x']},{r['camera_y']}) "
              f"E={r['energy']} slots={slots} {st}")
        last = types
print("types seen (type: first frame):", dict(sorted(seen.items())))
for e in events[:200]:
    print("event", e)
