#!/usr/bin/env python3
"""Code and state coverage of the original game on the execution bench (tools/amigaemu.py).

Plays a level from its RAM image (one or more runs) and records:
- every basic block executed in the main code ($8000-$125FF): the code a level really runs, i.e.
  what the MSX port must carry (to be read in REA/Ghidra; executed code Ghidra did not decode
  becomes a seed, see --seeds);
- every CPU write into the main code's area (variables and tables kept inside the code: state
  the port must mirror besides $B00-$16EB and $8000-$80FF);
- every CPU write elsewhere in RAM, by writing instruction (address range and count), outside
  the variables already mirrored and the stack;
- every BOB draw_bob ($AB08) drew (it returned through $AC40): graphics address A2 and BLTSIZE
  D4, with how many times (the level's BOB frames for tools/msxsprites.py --drawn).

Level 2 (--level 2): each run starts at amigaemu.py's direct start (Level2Bench, --carry) and stops
at the level's end; the output adds the enemy types seen in the slots ($C04 + 4k: their first
run and game frame, the frames seen, the highest hit points), the messages queued (message_queue
$FD76: A0's text) and the vat records level_tick_1 ($91BC) ran (A3), and each run's carried state.
Level 3 (--level 3) the same from Level3Bench's direct start, with the beam records level_tick_2
($9436) ran ("hazards") in place of the vats.

Runs: --run "SCRIPT[;tele=F:X:Y][;god][;poke=F:ADDR:VALUE:SIZE,...][;frames=N]" (SCRIPT = the
joystick script of amigaemu.py game, F:C:KEYS,...; tele moves RoboCop and the camera to world X, Y
at game frame F; god keeps the energy and the lives full and never lets the level end, so a long
run survives; poke writes the game's variables at game frame F; frames: the run's own length
instead of --gframes). Teleports, pokes and god mode change the game's state: they are for coverage
only, never for the reference traces.

usage: amigacov.py --ram build/ram/level1_full.bin --gframes 2000 --run "..." [--run ...] OUT.json
       amigacov.py --scenario level1 OUT.json   (the level's BOB frames for make msx, ~20 minutes)
       amigacov.py --level 2 [--carry 10050:2:0:good] --gframes N --run "..." OUT.json
       amigacov.py --level 2 --scenario level2 OUT.json   (three runs, 29,353 game frames, ~13 minutes)
       amigacov.py --level 3 --scenario level3 OUT.json   (three runs, docs/LEVEL3.md)
       amigacov.py --report OUT.json [--rea build/rea/lin.json] [--seeds]
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import amigaemu  # noqa: E402
from unicorn import UC_HOOK_BLOCK, UC_HOOK_MEM_WRITE  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CODE = (0x8000, 0x12600)
MIRRORED = ((0x0B00, 0x16EC), (0x8000, 0x8100))
STACK = (0x7F000, 0x80000)
MESSAGE_QUEUE = 0xFD76                     # message_queue: A0 the text
LEVEL_TICK_1 = 0x91BC                      # level_tick_1, level 2's vats: A3 the hazard record
LEVEL_TICK_2 = 0x9436                      # level_tick_2, level 3's beams: A3 the hazard record


def parse_run(spec: str) -> dict:
    run = {"script": [], "tele": [], "god": False, "pokes": [], "frames": None}
    for part in spec.split(";"):
        part = part.strip()
        if not part:
            continue
        if part == "god":
            run["god"] = True
        elif part.startswith("tele="):
            for t in part[5:].split(","):
                f, x, y = (int(v, 0) for v in t.split(":"))
                run["tele"].append((f, x, y))
        elif part.startswith("poke="):
            run["pokes"] += [tuple(int(v, 0) for v in t.split(":")) for t in part[5:].split(",") if t]
        elif part.startswith("frames="):
            run["frames"] = int(part[7:])
        else:
            for item in filter(None, part.split(",")):
                f, c, k = item.split(":")
                run["script"].append((int(f), int(c), k))
    return run


def play(ram: Path, frames: int, run: dict, cov: dict, level: int = 1, carry: str = "") -> None:
    if level in (2, 3):
        b = (amigaemu.Level2Bench if level == 2 else amigaemu.Level3Bench)(ROOT / "build" / "extracted", ram)
        b.start_direct(amigaemu.parse_carry(carry or (amigaemu.CARRY_L2 if level == 2 else amigaemu.CARRY_L3)))
        b.stop_at_level_end(level)
    else:
        b = amigaemu.GameBench(ROOT / "build" / "extracted", ram)
        b.start_level()
    frames = run.get("frames") or frames
    blocks = cov["blocks"]
    code_w = cov["code_writes"]
    ram_w = cov["ram_writes"]
    state = {"gf": 0}

    def on_block(uc, address, size, user_data):
        k = (address, size)
        if k not in blocks:
            blocks[k] = state["gf"]

    def on_write(uc, access, address, size, value, user_data):
        pc = uc.reg_read(amigaemu.UC_M68K_REG_PC)
        if CODE[0] <= address < CODE[1]:
            e = code_w.setdefault(address, [0, set(), state["gf"]])
            e[0] += 1
            e[1].add(pc)
            return
        for lo, hi in MIRRORED:
            if lo <= address < hi:
                return
        if STACK[0] <= address < STACK[1]:
            return
        e = ram_w.setdefault(pc, [address, address + size, 0])
        e[0] = min(e[0], address)
        e[1] = max(e[1], address + size)
        e[2] += 1

    def on_frame(uc, address, size, user_data):
        gf = state["gf"]
        for f, x, y in run["tele"]:
            if f == gf:
                uc.mem_write(0x15D0, struct.pack(">h", x))
                uc.mem_write(0x15D4, struct.pack(">h", y))
                uc.mem_write(0x0B04, struct.pack(">h", max(0, min(0x8E0, x - 0x108))))
                uc.mem_write(0x0B06, struct.pack(">h", max(0, y - 0x70)))
        for f, addr, v, size in run.get("pokes", ()):
            if f == gf:
                uc.mem_write(addr, (v & ((1 << 8 * size) - 1)).to_bytes(size, "big"))
        if run["god"]:
            uc.mem_write(0x169A, struct.pack(">h", 0x100))
            uc.mem_write(0x8034, struct.pack(">h", 2))
            uc.mem_write(0x16C4, struct.pack(">h", 0x100))     # the level's end never comes
        if "types" in cov:                                  # (level 2: the enemy types in the slots)
            for k in range(5):
                t = b.uc.mem_read(0xC04 + 4 * k, 1)[0]
                if t:
                    e = cov["types"].setdefault(t, {"first": [len(cov["runs"]), gf], "frames": 0, "max_hp": 0})
                    e["frames"] += 1
                    e["max_hp"] = max(e["max_hp"], b.uc.mem_read(0xC05 + 4 * k, 1)[0])
        state["gf"] = gf + 1

    bobs = cov["bobs"]
    cur = {}

    def on_draw(uc, address, size, user_data):          # draw_bob ($AB08): A2, D4
        cur["k"] = (uc.reg_read(amigaemu.a_reg(2)) & 0xFFFFFF, uc.reg_read(amigaemu.d_reg(4)) & 0xFFFF)

    def on_drawn(uc, address, size, user_data):         # its drawn exit ($AC40)
        bobs[cur["k"]] = bobs.get(cur["k"], 0) + 1

    def on_msg(uc, address, size, user_data):          # message_queue ($FD76): A0's text
        a0 = uc.reg_read(amigaemu.a_reg(0)) & 0xFFFFFF
        text = ""
        for c in bytes(b.uc.mem_read(a0, 40)):          # (the text ends at a byte 0 or from 80h)
            if c == 0 or c >= 0x80:
                break
            text += chr(c) if 32 <= c < 127 else "."
        e = cov["messages"].setdefault(f"{a0:05x} {text}", [0, len(cov["runs"]), state["gf"]])
        e[0] += 1

    def on_vat(uc, address, size, user_data):          # level_tick_1 ($91BC) / _2 ($9436): A3 the record
        e = cov["vats" if level == 2 else "hazards"].setdefault(f"{uc.reg_read(amigaemu.a_reg(3)) & 0xFFFFFF:05x}", [0, len(cov["runs"]), state["gf"]])
        e[0] += 1

    if "types" in cov:
        b.uc.hook_add(amigaemu.UC_HOOK_CODE, on_msg, None, MESSAGE_QUEUE, MESSAGE_QUEUE + 1)
        tick = LEVEL_TICK_1 if level == 2 else LEVEL_TICK_2
        b.uc.hook_add(amigaemu.UC_HOOK_CODE, on_vat, None, tick, tick + 1)
    b.uc.hook_add(amigaemu.UC_HOOK_CODE, on_draw, None, 0xAB08, 0xAB09)
    b.uc.hook_add(amigaemu.UC_HOOK_CODE, on_drawn, None, 0xAC40, 0xAC41)
    b.uc.hook_add(UC_HOOK_BLOCK, on_block, None, CODE[0], CODE[1] - 1)
    b.uc.hook_add(UC_HOOK_MEM_WRITE, on_write, None, 0, 0x7FFFF)
    b.uc.hook_add(amigaemu.UC_HOOK_CODE, on_frame, None, amigaemu.GAME_FRAME_START,
                  amigaemu.GAME_FRAME_START + 1)
    try:
        b.play(frames, run["script"])
    except RuntimeError as e:                               # (the bench lacks some hardware)
        print(f"run stopped at game frame {state['gf']}: {str(e).splitlines()[0]}")
    cov["runs"].append({"frames": state["gf"], "level": b.read_word(0x8050), "player": [
        struct.unpack(">h", b.uc.mem_read(0x15D0, 2))[0], struct.unpack(">h", b.uc.mem_read(0x15D4, 2))[0]]})
    if level in (2, 3):
        cov["runs"][-1] |= b.carried() | {"level_done": b.uc.mem_read(0x16D0, 1)[0]}


def merge_ranges(blocks) -> list[list[int]]:
    rs = sorted([a, a + s] for a, s in blocks)
    out: list[list[int]] = []
    for lo, hi in rs:
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return out


def scenario_level1(frames: int) -> list[str]:
    """The level-1 coverage runs (with god mode): (1) a 150-frame loop of walking right, up, left
    and down, firing every other 2 frames, teleported every 150 frames over a grid of the map
    (x 150-2550 step 150, rows y 790, 700, 600 ... 100); (2) right for 2000 frames, up for 200,
    left for 2000, firing likewise."""
    def alt(k: str, a: int, b: int) -> list[str]:
        return [f"{f}:2:{k}{'f' if (f - a) % 4 == 0 else ''}" for f in range(a, b, 2) if f < frames]

    items = ["70:30:r"] + alt("d", 100, 140)
    for t in range(80, frames, 150):
        items += alt("r", max(t, 140), t + 92) + alt("u", t + 90, t + 102) + alt("l", t + 100, t + 140) \
            + alt("d", t + 140, t + 152)
    grid = [(x, y) for y in (790, 700, 600, 500, 400, 300, 200, 100) for x in range(150, 2551, 150)]
    tele = [f"{140 + 150 * i}:{x}:{y}" for i, (x, y) in enumerate(grid)]
    run2 = ["70:30:r"] + alt("d", 100, 140) + alt("r", 140, 2140) + alt("u", 2140, 2340) + alt("l", 2340, 4340)
    return [",".join(items) + ";tele=" + ",".join(tele) + ";god", ",".join(run2) + ";god"]


def scenario_level2(frames: int) -> list[str]:
    """Level 2's coverage runs (god mode, each with its own length): (1) level 1's run 1 on level 2's
    map: the 150-frame loop teleported every 150 frames over x 150-2550 step 150 and the floors y 784,
    700, 624, 560, 480, 400, 300, 220 and 112 (23,251 game frames); (2) level 1's run 2 (4,401); (3) the
    top floor, where the drones (type 49) are: left and right by turns of 40 frames, firing every 8th
    frame, teleported along y 150 and 60, no keys 10 frames around a teleport (1,701)."""
    def alt(k: str, a: int, b: int) -> list[str]:
        return [f"{f}:2:{k}{'f' if (f - a) % 4 == 0 else ''}" for f in range(a, b, 2) if f < frames]

    items = ["70:30:r"] + alt("d", 100, 140)
    for t in range(80, frames, 150):
        items += alt("r", max(t, 140), t + 92) + alt("u", t + 90, t + 102) + alt("l", t + 100, t + 140) \
            + alt("d", t + 140, t + 152)
    grid = [(x, y) for y in (784, 700, 624, 560, 480, 400, 300, 220, 112) for x in range(150, 2551, 150)]
    tele = [f"{140 + 150 * i}:{x}:{y}" for i, (x, y) in enumerate(grid) if 140 + 150 * i < frames]
    run2 = ["70:30:r"] + alt("d", 100, 140) + alt("r", 140, 2140) + alt("u", 2140, 2340) + alt("l", 2340, 4340)
    top_tele = ((60, 1500, 150), (260, 1700, 150), (460, 1900, 150), (660, 2100, 150), (860, 2300, 150), (1060, 2450, 150),
                (1260, 1600, 60), (1460, 2200, 60))
    top = [f"{f}:2:{'r' if (f - 80) // 40 % 2 == 0 else 'l'}{'f' if (f - 80) % 8 == 0 else ''}" for f in range(70, 1650, 2)
           if not any(t - 10 <= f < t + 10 for t, _x, _y in top_tele[1:])]     # (no keys 10 frames around a teleport)
    return [",".join(items) + ";tele=" + ",".join(tele) + f";god;frames={frames}",
            ",".join(run2) + ";god;frames=4400", ",".join(top) + ";tele=" + ",".join(f"{t}:{x}:{y}" for t, x, y in top_tele) + ";god;frames=1700"]


def scenario_level3(frames: int) -> list[str]:
    """Level 3's coverage runs (god mode, each with its own length): (1) level 2's run 1 on level 3's
    map: the 150-frame loop teleported every 150 frames over x 150-2550 step 150 and the floors (the
    map's rows with floor cells, attribute bit 3: 7, 20, 25, 30, 35, 40, 49) y 784, 640, 560, 480,
    400, 320 and 112; (2) level 1's run 2 (4,401 frames); (3) the roof (row 7, y 112), where the spawn
    list's type 22 (Cain as RoboCop 2, x 1280) comes: left and right by turns of 40 frames, firing every
    4th frame, from x 700 and 1000, no keys 10 frames around a teleport (2,400)."""
    def alt(k: str, a: int, b: int) -> list[str]:
        return [f"{f}:2:{k}{'f' if (f - a) % 4 == 0 else ''}" for f in range(a, b, 2) if f < frames]

    items = ["70:30:r"] + alt("d", 100, 140)
    for t in range(80, frames, 150):
        items += alt("r", max(t, 140), t + 92) + alt("u", t + 90, t + 102) + alt("l", t + 100, t + 140) \
            + alt("d", t + 140, t + 152)
    grid = [(x, y) for y in (784, 640, 560, 480, 400, 320, 112) for x in range(150, 2551, 150)]
    tele = [f"{140 + 150 * i}:{x}:{y}" for i, (x, y) in enumerate(grid) if 140 + 150 * i < frames]
    run2 = ["70:30:r"] + alt("d", 100, 140) + alt("r", 140, 2140) + alt("u", 2140, 2340) + alt("l", 2340, 4340)
    roof_tele = ((60, 700, 112), (1260, 1000, 112))
    roof = [f"{f}:2:{'r' if (f - 80) // 40 % 2 == 0 else 'l'}{'f' if (f - 80) % 4 == 0 else ''}" for f in range(70, 2400, 2)
            if not any(t - 10 <= f < t + 10 for t, _x, _y in roof_tele[1:])]
    return [",".join(items) + ";tele=" + ",".join(tele) + f";god;frames={frames}",
            ",".join(run2) + ";god;frames=4400",
            ",".join(roof) + ";tele=" + ",".join(f"{t}:{x}:{y}" for t, x, y in roof_tele) + ";god;frames=2400"]


SCENARIOS = {"level1": (20540, scenario_level1), "level2": (len(range(150, 2551, 150)) * 9 * 150 + 300, scenario_level2),
             "level3": (len(range(150, 2551, 150)) * 7 * 150 + 300, scenario_level3)}


def collect(a) -> int:
    if a.scenario:
        if a.level != int(a.scenario[-1]):
            sys.exit(f"--scenario {a.scenario} belongs to --level {a.scenario[-1]}")
        frames, make = SCENARIOS[a.scenario]
        a.gframes = frames
        a.run = make(frames) + (a.run or [])
    cov = {"blocks": {}, "code_writes": {}, "ram_writes": {}, "runs": [], "bobs": {}}
    if a.level == 2:
        cov |= {"types": {}, "messages": {}, "vats": {}}
    elif a.level == 3:
        cov |= {"types": {}, "messages": {}, "hazards": {}}
    for spec in a.run or [""]:
        play(a.ram, a.gframes, parse_run(spec), cov, a.level, a.carry)
    out = {
        "ram": str(a.ram), "runs": cov["runs"],
        "executed": merge_ranges(cov["blocks"]),
        "blocks": sorted([a_, s, f] for (a_, s), f in cov["blocks"].items()),
        "code_writes": {f"{k:x}": [v[0], sorted(f"{p:x}" for p in v[1]), v[2]]
                        for k, v in sorted(cov["code_writes"].items())},
        "ram_writes": {f"{k:x}": [f"{v[0]:x}", f"{v[1]:x}", v[2]] for k, v in sorted(cov["ram_writes"].items())},
        "bobs": [{"addr": a2, "bltsize": d4, "w": ((d4 & 63) - 1) * 16, "h": d4 >> 6, "count": n}
                 for (a2, d4), n in sorted(cov["bobs"].items())],
    }
    if a.level == 2:
        out |= {"level": 2, "carry": a.carry or amigaemu.CARRY_L2,
                "types": {str(k): v for k, v in sorted(cov["types"].items())},
                "messages": cov["messages"], "vats": dict(sorted(cov["vats"].items()))}
    elif a.level == 3:
        out |= {"level": 3, "carry": a.carry or amigaemu.CARRY_L3,
                "types": {str(k): v for k, v in sorted(cov["types"].items())},
                "messages": cov["messages"], "hazards": dict(sorted(cov["hazards"].items()))}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(out, indent=0))
    n = sum(hi - lo for lo, hi in out["executed"])
    print(f"{a.out}: {len(out['blocks'])} blocks, {len(out['executed'])} ranges, {n} bytes of code executed; "
          f"{len(out['code_writes'])} code-area addresses written; {len(out['ram_writes'])} other writers; "
          f"{len(out['bobs'])} BOB frames drawn" + (f"; enemy types {sorted(cov['types'])}" if a.level >= 2 else ""))
    return 0


def report(a) -> int:
    cov = json.loads(a.report.read_text())
    rea = set()
    if a.rea and a.rea.exists():
        rea = {int(k) for k in json.loads(a.rea.read_text())}
    gaps = []
    for lo, hi in cov["executed"]:
        if rea and not any(x in rea for x in range(lo, hi, 2)):
            gaps.append((lo, hi))
        elif rea and lo not in rea:
            gaps.append((lo, hi))
    print(f"executed ranges: {len(cov['executed'])}; not decoded by Ghidra (start missing): {len(gaps)}")
    for lo, hi in gaps:
        print(f"  {lo:05x}-{hi:05x}")
    if a.seeds:
        for lo, _hi in gaps:
            print(f"+code {lo:x}")
    print("code-area writes (address: count, writers):")
    rows = sorted(cov["code_writes"].items(), key=lambda kv: int(kv[0], 16))
    for k, (n, pcs, f0) in rows:
        print(f"  {k}: {n:6d}  {' '.join(pcs[:6])}{' ...' if len(pcs) > 6 else ''}  (first gf {f0})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ram", type=Path, help="the RAM image (build/ram/level1_full.bin, --level 2: level2_full.bin)")
    ap.add_argument("--level", type=int, choices=(1, 2, 3), default=1,
                    help="the level played (2, 3: amigaemu.py's direct start)")
    ap.add_argument("--carry", default="", help="--level 2: SCORE:LIVES:CONTINUES:TABLE (amigaemu.py --carry)")
    ap.add_argument("--gframes", type=int, default=1000)
    ap.add_argument("--run", action="append", help="SCRIPT[;tele=F:X:Y,...][;god][;poke=F:ADDR:VALUE:SIZE,...][;frames=N]")
    ap.add_argument("--scenario", choices=sorted(SCENARIOS), help="the runs (and frames) of a named coverage scenario")
    ap.add_argument("--report", type=Path, help="prints a coverage file")
    ap.add_argument("--rea", type=Path, help="instruction addresses Ghidra decoded (JSON object keyed by address)")
    ap.add_argument("--seeds", action="store_true", help="with --report: seed lines for the gaps")
    ap.add_argument("out", type=Path, nargs="?")
    a = ap.parse_args()
    if a.report:
        return report(a)
    if not a.out:
        ap.error("OUT.json is required")
    if a.scenario in ("level2", "level3"):
        a.level = int(a.scenario[-1])
    a.ram = a.ram or ROOT / "build" / "ram" / f"level{a.level}_full.bin"
    return collect(a)


if __name__ == "__main__":
    raise SystemExit(main())
