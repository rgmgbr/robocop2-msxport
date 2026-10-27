#!/usr/bin/env python3
"""The input file of openMSX's driven trace (tools/openmsx_rc2.tcl rc2_drive_trace) for an EXTJOY=1
test build (tools/mkrom.py), from the same joystick script, teleports and god mode that
tools/amigaemu.py game plays (--joy, --tele, --god), or from a coverage scenario's run
(tools/amigacov.py --scenario).

Four lines: the joystick byte of every game frame as hex (up 1, down 2, left 4, right 8, fire 10h;
every entry that covers a frame ORed), the teleports as "frame:x:y ...", god 0/1, the pokes as
"frame:address:value:size ..." (Amiga addresses of the game's variables, $B00-$16EB or
$8000-$80FF; size 1 or 2 bytes; numbers in C notation).

Brainstorm's drives (tools/amigaemu.py puzl --drive, tools/openmsx_rc2.tcl rc2_pz_drive and
rc2_pz_arm) are the same file with PUZL frames ($B00) for game frames; they use the joystick
bytes and the pokes only.

usage: drivejoy.py --joy F:C:KEYS,... [--tele F:X:Y,...] [--god] [--poke F:ADDR:VALUE[:SIZE],...] OUT
       drivejoy.py --scenario level1 --run 0 [--frames N] OUT   (also writes OUT.args: the bench's)
       drivejoy.py --fuzz SEED [--frames N] [--joy ...] [--poke ...] OUT
       (--fuzz: random keys from FUZZ_KEYS, each held 1-6 frames, up to frame N (2500 by
       default): diagonals and fire toggles, as the Brainstorm logic report's random runs; the
       same seed gives the same keys)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
KEY_BITS = {"u": 0x01, "d": 0x02, "l": 0x04, "r": 0x08, "f": 0x10}
# The random runs' key sets: the logic report's, with its "lr", "ud" and "udlr" replaced by "ur", "dl"
# and "df". read_joystick's table ($BDEC, $BE26: 10 11 15 14 12 10 10 16 1A 10 10 10 18 19 10 10)
# reads any key set with up and down or left and right as no direction, while an EXTJOY build
# takes ext_joy's byte as it is: every set here reads as itself on both sides.
FUZZ_KEYS = ("", "u", "d", "l", "r", "f", "uf", "rf", "ul", "dr", "ur", "dl", "df", "lf")


def fuzz_items(seed: int, frames: int) -> list[tuple[int, int, str]]:
    """Random joystick entries: a key set of FUZZ_KEYS ('' = none) held 1-6 frames, then the
    next, until 'frames' (the last may run past it)."""
    import random
    rnd = random.Random(seed)
    p, out = 0, []
    while p < frames:
        k, c = rnd.choice(FUZZ_KEYS), rnd.randint(1, 6)
        if k:
            out.append((p, c, k))
        p += c
    return out


def frame_bytes(items: list[tuple[int, int, str]]) -> bytes:
    end = max((f + c for f, c, _ in items), default=0)
    out = bytearray(end)
    for f, c, keys in items:
        bits = 0
        for k in keys:
            bits |= KEY_BITS[k]
        for n in range(f, f + c):
            out[n] |= bits
    return bytes(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--joy", default="")
    ap.add_argument("--tele", default="")
    ap.add_argument("--god", action="store_true")
    ap.add_argument("--poke", default="")
    ap.add_argument("--scenario")
    ap.add_argument("--run", type=int, default=0)
    ap.add_argument("--frames", type=int, help="with --scenario: only the script up to this game frame; "
                    "with --fuzz: the random keys' length (2500)")
    ap.add_argument("--fuzz", type=int, help="random keys from this seed (FUZZ_KEYS)")
    ap.add_argument("out", type=Path)
    a = ap.parse_args()
    joy, tele, god = a.joy, a.tele, a.god
    if a.scenario:
        import amigacov
        frames, make = amigacov.SCENARIOS[a.scenario]
        spec = make(a.frames or frames)[a.run]
        run = amigacov.parse_run(spec)
        joy = ",".join(f"{f}:{c}:{k}" for f, c, k in run["script"])
        tele = ",".join(f"{f}:{x}:{y}" for f, x, y in run["tele"] if a.frames is None or f < a.frames)
        god = run["god"]
    if a.fuzz is not None:
        joy = ",".join(filter(None, [joy] + [f"{f}:{c}:{k}" for f, c, k in fuzz_items(a.fuzz, a.frames or 2500)]))
    items = []
    for item in filter(None, joy.split(",")):
        f, c, k = item.split(":")
        items.append((int(f), int(c), k))
    teles = [t for t in filter(None, tele.split(","))]
    pokes = []
    for item in filter(None, a.poke.split(",")):
        f, addr, v, *size = (int(x, 0) for x in item.split(":"))
        size = size[0] if size else 1
        if size not in (1, 2) or not (0xB00 <= addr < 0x16EC or 0x8000 <= addr < 0x8100):
            print(f"bad poke {item!r}: size 1/2 into $B00-$16EB or $8000-$80FF", file=sys.stderr)
            return 2
        pokes.append(f"{f}:{addr}:{v}:{size}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(frame_bytes(items).hex() + "\n" + " ".join(teles) + "\n" + ("1" if god else "0") + "\n"
                     + " ".join(pokes) + "\n")
    args = [f"--joy {i[0]}:{i[1]}:{i[2]}" for i in items] + [f"--tele {t}" for t in teles] + (["--god"] if god else [])
    a.out.with_suffix(a.out.suffix + ".args").write_text(" ".join(args) + "\n")
    print(f"{a.out}: {len(items)} joystick entries, {len(teles)} teleports, god {int(god)}, {len(pokes)} pokes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
