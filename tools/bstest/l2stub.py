#!/usr/bin/env python3
"""l2stub.py: level 2's bench references with the routines the port has not ported yet stubbed the way
the port stubs them, so that an MSX trace of the port as it stands compares whole, every row and field
(docs/HARNESS.md 5.22). Against the plain references (build/emu/l2_<ref>_ram.jsonl) a level-2 trace
differs from the first frame a stubbed routine runs (at step 7 from row 0: act_0c ran in level_init's
map-object pass, the trolleys from frame 0, type 1 from frame 4).

Each reference of tools/l2drives.py (its drive, carry and frames; not the flow one) runs on the bench
(tools/amigaemu.py game --level 2, the direct start, Unicorn: $PY or the project's venv) with the
patches of the STUBS table, written into the main code before level_init (--pre-poke ADDR:VALUE:SIZE).
A step that ports a routine drops its stub here (--drop NAME, or the STUBS table) and in the port.

Every level-2 routine is ported since level 2's step 9, so the table is empty and the references this
script makes are the plain ones (the 20 jobs compare against build/emu directly). Dropped:
  step 8: the trolley $8F02 (msx/special.asm sp_trolley), the vats $91BC (msx/level2.asm lt1) and act_0c
          $9EE8 (msx/mapobj.asm), whose stubs were rts, bra.w $919E (the next hazard record) and
          bra.w $9C76 (activator 0's default, the port's ao_look);
  step 9: the types 1, 2, 5, 6, 14, 16 and 49 (msx/level2obj.asm), whose stubs were moveq #-1,D0 / rts
          (70FF4E75h) at their handlers $C736, $C868, $D0E2, $D1E2, $CE0A, $CD7A and $E6C0 (the port's
          ld a,FFh / ret: update_objects frees the slot).

usage: l2stub.py OUT [--drop NAME ...] [--jobs N] [REF ...]   OUT/l2_<ref>_ram.jsonl (+ .log), every
                                                              direct reference by default
       l2stub.py --list                                       the stubs
Compare: sh tools/bstest/hz.sh compare --fields analysis/amiga_ram_l2.tsv DIR R --refs OUT [JOB ...]
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import l2drives  # noqa: E402

STUBS: dict[str, list[tuple[int, str]]] = {}   # name: [(address, value:size), ...]; none left (step 9)


def main(argv: list[str]) -> int:
    if argv[:1] == ["--list"]:
        for name, patches in STUBS.items():
            print(f"{name:8s} " + ", ".join(f"${a:04X} {v}" for a, v in patches))
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
    bad = (drop - set(STUBS)) | {n for n in names if n not in l2drives.REFS or l2drives.REFS[n][1] == "flow"}
    if bad:
        print(f"l2stub.py: unknown stub or reference: {', '.join(sorted(bad))}", file=sys.stderr)
        return 2
    pre = [x for name, patches in STUBS.items() if name not in drop
           for a, v in patches for x in ("--pre-poke", f"0x{a:04X}:{v}")]
    names = names or [n for n in l2drives.REFS if l2drives.REFS[n][1] != "flow"]
    out.mkdir(parents=True, exist_ok=True)
    py = l2drives.python()
    todo, running, failed = list(names), [], 0
    while todo or running:
        while todo and len(running) < jobs:
            name = todo.pop(0)
            cmd = l2drives.ref_cmd(name, ROOT / "build" / "emu", py)
            cmd[cmd.index("--trace") + 1] = str(out / f"l2_{name}_ram.jsonl")
            log = (out / f"l2_{name}.log").open("w")
            running.append((name, subprocess.Popen(cmd + pre, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT), log))
        name, p, log = running.pop(0)
        p.wait()
        log.close()
        trace = out / f"l2_{name}_ram.jsonl"
        rows = trace.read_bytes().count(b"\n") if p.returncode == 0 and trace.exists() else -1
        failed += rows < 0
        print(f"{name}: {'exit ' + str(p.returncode) if rows < 0 else str(rows) + ' rows'}", flush=True)
    print(f"stubbed references: {len(names) - failed} of {len(names)} in {out} (stubs: "
          f"{', '.join(n for n in STUBS if n not in drop) or 'none'})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
