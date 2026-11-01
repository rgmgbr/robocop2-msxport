#!/usr/bin/env python3
"""l3stub.py: level 3's bench references with the routines the port has not ported yet stubbed the way
the port stubs them, so that an MSX trace of the port as it stands compares whole, every row and field
(docs/HARNESS.md 5.26; tools/bstest/l2stub.py's twin for level 2's milestones).

Each reference of tools/l3drives.py (its drive, carry and frames) runs on the bench (tools/amigaemu.py
game --level 3, the direct start, Unicorn: $PY or the project's venv) with the patches of the STUBS
table written into the main code before level_init (--pre-poke ADDR:VALUE:SIZE). A step that ports a
routine drops its stub here (--drop NAME, or the STUBS table) and in the port.

At level 3's step A (docs/LEVEL3.md) the port has level_init's level-3 part, the beams (level_tick_2),
the three deaths of types 21, 22 and 33 with debris_add, the shared handlers (types 4 and 12) and
everything levels 1 and 2 share; stubbed:
  the 19 new types (msx/level3obj.asm: ld a,FFh / ret, update_objects frees the slot): moveq #-1,D0 /
      rts (70FF4E75h) at their handlers;
  act_20 $9F74 (the map objects of activator 20h; the port's ao_acts entry 8 is ao_look, activator 0's
      default): bra.w $9C76 (6000FD00h).
The lift's two-part look ($8ED2) draws only: no stub (the trace holds no BOB).

usage: l3stub.py OUT [--drop NAME ...] [--jobs N] [REF ...]   OUT/l3_<ref>_ram.jsonl (+ .log), every
                                                              reference by default (the drives are
                                                              build/emu's: l3drives.py make)
       l3stub.py --list                                       the stubs
Compare: sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l3.tsv DIR R --refs OUT [JOB ...]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import l3drives  # noqa: E402

TYPE_STUB = "0x70FF4E75:4"                      # moveq #-1,D0 / rts
STUBS: dict[str, list[tuple[int, str]]] = {     # name: [(address, value:size), ...]
    **{f"t{t}": [(a, TYPE_STUB)] for t, a in (
        (21, 0xD2FA), (22, 0xD49C), (33, 0xE0A4), (34, 0xE1D6), (35, 0xE28C), (36, 0xE356), (37, 0xE470),
        (38, 0xE6D6), (39, 0xE7D2), (40, 0xE98C), (41, 0xEB0A), (42, 0xE972), (43, 0xEC02), (46, 0xEE22),
        (47, 0xEE30), (48, 0xEE5E), (50, 0xEEE2), (51, 0xEE68), (52, 0xE8A2))},
    "act_20": [(0x9F74, "0x6000FD00:4")],
}


def main(argv: list[str]) -> int:
    if argv[:1] == ["--list"]:
        for name, patches in STUBS.items():
            print(f"{name:12s} " + ", ".join(f"${a:04X} {v}" for a, v in patches))
        return 0
    if not argv or argv[0].startswith("-"):
        print(__doc__, file=sys.stderr)
        return 2
    out, rest = Path(argv[0]).resolve(), argv[1:]
    drop, jobs, names = set(), 4, []
    while rest:
        a = rest.pop(0)
        if a == "--drop" and rest:
            drop.add(rest.pop(0))
        elif a == "--jobs" and rest:
            jobs = int(rest.pop(0))
        else:
            names.append(a)
    bad = (drop - set(STUBS)) | {n for n in names if n not in l3drives.REFS}
    if bad:
        print(f"l3stub.py: unknown stub or reference: {', '.join(sorted(bad))}", file=sys.stderr)
        return 2
    pre = [x for name, patches in STUBS.items() if name not in drop
           for a, v in patches for x in ("--pre-poke", f"0x{a:04X}:{v}")]
    names = names or list(l3drives.REFS)
    emu = ROOT / "build" / "emu"
    need = sorted({l3drives.REFS[n][0] for n in names} - {p.stem[3:] for p in emu.glob("l3_*.drive")})
    if need and l3drives.make(emu, need):
        return 1
    failed = l3drives.run_refs(out, names, jobs, l3drives.python(), pre, emu)
    for name in names:
        trace = out / f"l3_{name}_ram.jsonl"
        rows = trace.read_bytes().count(b"\n") if trace.exists() else -1
        print(f"{name}: {'missing' if rows < 0 else str(rows) + ' rows'}", flush=True)
    print(f"stubbed references: {len(names) - failed} of {len(names)} in {out} (stubs: "
          f"{', '.join(n for n in STUBS if n not in drop) or 'none'})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
