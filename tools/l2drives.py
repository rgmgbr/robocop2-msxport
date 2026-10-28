#!/usr/bin/env python3
"""Level 2's bench drives and their references (the level-2 plan, 4.1; tools/amigaemu.py game --level 2).

A drive is a tools/drivejoy.py file (the joystick byte of every game frame, the teleports, god mode,
the pokes): the same input for the bench (amigaemu.py --drive) and for openMSX (tools/openmsx_rc2.tcl
rc2_drive_rom on an LV_TEST=2 build). Its reference is the bench's trace of it (--trace-ram, one JSON
line a game frame), from level 2's direct start with the reference's carry (amigaemu.py --carry), or,
for flow_l2_end, from the flow start (level 1, Brainstorm and the range played first: --flow). The
MSX trace of a job is compared with tools/tracecmp.py --ram --fields analysis/amiga_ram_l2.tsv.

Files (DIR = build/emu by default; not committed: they hold the game's state):
  DIR/l2_DRIVE.drive (+ .args)     the drives (make)
  DIR/l2_REF_ram.jsonl (+ .log)    the references (refs), REF = a drive's name or a variant's
                                   (trolley_sharp ... plays l2_trolley.drive with another carry)

usage: l2drives.py list                                   the references: drive, carry, rows, sha256
       l2drives.py make [--out DIR] [DRIVE ...]           writes the drives (stdlib: drivejoy.py)
       l2drives.py refs [--out DIR] [--jobs N] [REF ...]  makes the references (runs amigaemu.py with
                                                          --python, Unicorn's), then checks them
       l2drives.py check [--out DIR] [REF ...]            rows and sha256 prefixes against the table
       l2drives.py events REF [--out DIR] [--every N]     (Unicorn) the reference's events, frame by
                                                          frame: spawns, kills, shots, pickups, ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(__file__).resolve().parent
EMU = ROOT / "build" / "emu"
CARRY = "10050:2:0:good"              # drive_end + pz_fail + fr_good: what level 2 starts with
FLOW = ("build/emu/drive_end.txt", "build/emu/pz_fail.drive", "build/emu/fr_good.drive")


def fire_r(a: int, b: int) -> str:
    """Right and fire for 2 frames, every 4th frame from a up to b."""
    return ",".join(f"{f}:2:rf" for f in range(a, b, 4))


def energy(n: int) -> str:
    """The energy target ($169A) poked full every 25 frames up to n."""
    return ",".join(f"{f}:0x169A:256:2" for f in range(25, n, 25))


def energy_lives(n: int) -> str:
    """The energy target and the lives ($8034 = 2) poked every 25 frames up to n."""
    return ",".join(f"{f}:0x169A:256:2,{f}:0x8034:2:2" for f in range(25, n, 25))


def fire(a: int, b: int) -> str:
    """Fire alone (the facing kept) for 2 frames, every 4th frame from a up to b."""
    return ",".join(f"{f}:2:f" for f in range(a, b, 4))


TOUR = ("40:95:r,150:110:u,265:88:r,482:12:u,564:30:ur," + fire_r(615, 642) + ",644:60:r,722:12:u,780:30:ur,"
        "830:18:r,943:12:u,1016:30:ur," + fire_r(1060, 1120) + ",1122:34:r,1242:12:u,1348:30:ur,1610:200:u,1920:150:u,"
        + ",".join(f"{f}:2:l{'f' if f % 8 == 0 else ''}" for f in range(2080, 2400, 2)) + "," + fire_r(2440, 2800))

# The drives: drivejoy.py's --joy, --tele, --poke, --god and extra arguments.
DRIVES = {
    # onto the roof, fire right: the suspect shot, then touched (arrested) at 164, the level's end at row 258
    "end": dict(joy=fire_r(40, 400), tele="20:200:100"),
    # the play-through: no teleport up to vat 3 (L1, trolleys 0-3, the two type-0 blockers shot), then
    # L2, L4 and the roof by teleports; energy and lives poked every 25 frames
    "tour": dict(joy=TOUR, tele="1598:2566:784,1910:2567:384,2410:200:100",
                 poke=",".join(f"{f}:0x169A:256:2,{f}:0x8034:2:2" for f in range(25, 3000, 25))),
    # the lifts: L0 (2 stops), then L1 (3 stops), up and down
    "lift": dict(joy="100:150:u,260:150:d,440:130:u,600:200:d", tele="70:200:784,420:566:784", poke=energy(900)),
    # trolley 0 over vat 0 from the start, no teleport
    "trolley": dict(joy="40:95:r,150:110:u,265:88:r,482:12:u,564:30:ur", poke=energy(900)),
    # a vat's death, then a death by the enemies
    "vat": dict(tele="30:936:600"),
    # the game over with (cont) and without (over) a continue: the carry decides; fire held at the death's end
    "cont": dict(tele="30:936:600", joy="100:20:f"),
    "over": dict(tele="30:936:600", joy="100:20:f"),
    # random keys from the start, god mode
    "fuzz": dict(god=True, extra=("--fuzz", "2", "--frames", "2500")),
    # (step 2's new drives) type 6, the rolling tyres: RoboCop on the left stairs (y 464), firing as he faces
    # (right): launches from x 120, bounces, the gap $D1DC, 17 kills ($C33E: pickups 24h at 4, 8, 12, 1Ch at
    # 16; no launch after the 16th: the waiting tyres freed)
    "barrel": dict(joy=fire(40, 900), tele="10:300:440", poke=energy(900)),
    # act_0c, the mine at x 1184 (object 0): onto the floor left of it, then right onto it (frames 76-80 in
    # its cell: 4 explosions each), its look advancing (+2: 0, 4, 8), then off (+2 high byte FFh); he falls
    "mine": dict(joy="66:14:r", tele="10:1190:130", poke=energy_lives(200)),
    # type 1 facing left (Q2): spawn entry 11 entered at the screen's edge, followed by teleports along its
    # walkway (x 319-931); its fires facing left (bullet type D6 0: the slot written, no bullet) and its turn
    # to the left at the walkway's end on a fire frame (272). Neither type 1 walkway ends at a wall: the
    # missile (D6 2) does not occur in level 2
    "t1left": dict(tele="1:620:430,80:400:430,120:363:430,150:483:430,180:603:430,210:723:430,240:843:430,"
                   "270:963:430,300:863:430", poke=energy_lives(400)),
    # type 49 on the top floor: the drones home in, one touches RoboCop (65), one is shot down (84: $C35A
    # with D5 = 0198h, Q7), more spawn and home in
    "drone": dict(joy=fire(66, 400), tele="10:1600:150", poke=energy_lives(400)),
}

# The references: name -> (drive, carry or "flow", game frames asked, rows, sha256 prefix, what it covers).
# The bench stops at the level's end or at a game over without a continue (--stop-at-end).
REFS = {
    "end": ("end", CARRY, 300, 259, "e0ecb97c30288d6d", "the suspect shot, then arrested: $16D0 at 164"),
    "tour": ("tour", CARRY, 3000, 2654, "d0ef114623da05c8", "the play-through: trolleys 0-3, the arrest at 2559"),
    "lift": ("lift", CARRY, 800, 801, "978d9cc7dec76d65", "L0 and L1 ridden up and down"),
    "trolley": ("trolley", CARRY, 640, 641, "8b93c3bd428166f4", "trolley 0 over vat 0 (rows 499-565)"),
    "trolley_sharp": ("trolley", "10050:2:0:sharp", 640, 641, "3c810e16ee4d22eb", "trolley at SHARP"),
    "trolley_fair": ("trolley", "10050:2:0:fair", 640, 641, "9e608b5a5255c74f", "trolley at FAIR"),
    "trolley_poor": ("trolley", "10050:2:0:poor", 640, 641, "ba9dbf04d18c70e0", "trolley at POOR"),
    "vat": ("vat", CARRY, 700, 701, "05a3aacea265b2c4", "a vat's death at 54, the enemies' at 470"),
    "cont": ("cont", "0:0:1:good", 300, 301, "02692c53cc6458c7", "the game over and a continue (row 109)"),
    "over": ("over", "0:0:0:good", 300, 109, "3d3f211d54e83db7", "the game over without a credit"),
    "fuzz": ("fuzz", CARRY, 2500, 2501, "8bdc1c303d6c7742", "random keys, god mode"),
    "flow_l2_end": ("end", "flow", 300, 259, "e65540af1e959526", "end after level 1, Brainstorm and the range"),
    "barrel": ("barrel", CARRY, 900, 901, "2c4aebed5e969225", "type 6: launches, bounces, $D1DC, 17 kills, the pickups"),
    "mine": ("mine", CARRY, 160, 161, "3cab181fb43ca28b", "the mine at x 1184 stepped on: explosions, its look, off"),
    "t1left": ("t1left", CARRY, 340, 341, "1f00278095ce9e64", "type 1 facing left: bullet type 0, a turn on a fire frame"),
    "drone": ("drone", CARRY, 400, 401, "533db1ac622378fa", "type 49: one touches RoboCop, one shot down (D5 0198h)"),
}


def python() -> str:
    """The interpreter with Unicorn: $PY, else the project's venv, else this one."""
    venv = Path.home() / ".venvs" / "msxports" / "bin" / "python"
    return os.environ.get("PY") or (str(venv) if venv.exists() else sys.executable)


def drive_cmd(name: str, out: Path) -> list[str]:
    d = DRIVES[name]
    cmd = [sys.executable, "-I", str(TOOLS / "drivejoy.py"), "--joy", d.get("joy", ""), "--tele", d.get("tele", ""),
           "--poke", d.get("poke", "")]
    return cmd + (["--god"] if d.get("god") else []) + list(d.get("extra", ())) + [str(out / f"l2_{name}.drive")]


def make(out: Path, names: list[str]) -> int:
    out.mkdir(parents=True, exist_ok=True)
    for name in names or DRIVES:
        r = subprocess.run(drive_cmd(name, out), capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        if r.returncode:
            return r.returncode
    return 0


def ref_cmd(name: str, out: Path, py: str) -> list[str]:
    """The bench's command line for a reference (run from the repository's root)."""
    drive, carry, gframes, *_ = REFS[name]
    cmd = [py, "-I", "tools/amigaemu.py", "game", "--level", "2"]
    if carry == "flow":
        cmd += ["--flow", ":".join(FLOW), "--report", str(out / f"l2_{name}.json")]
    else:
        cmd += ["--carry", carry]
    return cmd + ["--gframes", str(gframes), "--drive", str(out / f"l2_{drive}.drive"), "--stop-at-end",
                  "--trace", str(out / f"l2_{name}_ram.jsonl"), "--trace-ram"]


def refs(out: Path, names: list[str], jobs: int, py: str) -> int:
    names = names or list(REFS)
    need = sorted({REFS[n][0] for n in names} - {p.stem[3:] for p in out.glob("l2_*.drive")})
    if need and make(out, need):
        return 1
    running: list[tuple[str, subprocess.Popen, object]] = []
    todo = list(names)
    while todo or running:
        while todo and len(running) < jobs:
            name = todo.pop(0)
            cmd = ref_cmd(name, out, py)
            print(" ".join(c if " " not in c else repr(c) for c in cmd), flush=True)
            log = (out / f"l2_{name}.log").open("w")
            running.append((name, subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT), log))
        name, p, log = running.pop(0)
        p.wait()
        log.close()
        if p.returncode:
            print(f"{name}: the bench failed (exit {p.returncode}): see {out / f'l2_{name}.log'}")
    return check(out, names)


def check(out: Path, names: list[str]) -> int:
    bad = 0
    for name in names or REFS:
        _drive, _carry, _g, rows, sha, _what = REFS[name]
        p = out / f"l2_{name}_ram.jsonl"
        if not p.exists():
            print(f"{name}: {p} missing")
            bad += 1
            continue
        data = p.read_bytes()
        n, h = data.count(b"\n"), hashlib.sha256(data).hexdigest()[:16]
        ok = n == rows and (not sha or h == sha)
        bad += not ok
        print(f"{name}: {n} rows (expected {rows}), sha256 {h} (expected {sha or '-'}): {'ok' if ok else 'FAIL'}")
    total = len(names or REFS)
    print(f"references: {total - bad} of {total} as expected")
    return 1 if bad else 0


def show_list() -> int:
    for name, (drive, carry, gframes, rows, sha, what) in REFS.items():
        print(f"{name:14} l2_{drive}.drive  carry {carry:16} --gframes {gframes:5}  {rows:5} rows  {sha or '-':16}  {what}")
    return 0


# ---------------------------------------------------------------- events (Unicorn)
def text_at(b, addr: int) -> str:
    raw = bytes(b.uc.mem_read(addr, 40))
    out = []
    for c in raw:
        if c >= 0x80 or c == 0:
            break
        out.append(chr(c) if 32 <= c < 127 else ".")
    return "".join(out)


def events(name: str, out: Path, every: int = 0) -> int:
    """Plays a reference's drive on the bench (its direct start and carry) and prints its events: the
    enemy slots' spawns and frees, the code points of level 2's new logic as they run (with their
    registers), the pickups, the messages, the deaths and the level's end; with every, RoboCop's
    position every that many game frames. Game frame numbers are the trace's rows."""
    import amigaemu as ae
    drive, carry, gframes, *_ = REFS[name]
    if carry == "flow":
        print("events: the direct references only (flow_l2_end plays end's drive)")
        return 2
    b = ae.Level2Bench(ROOT / "build" / "extracted", ae.RAM_IMAGES[2])
    b.start_direct(ae.parse_carry(carry))
    script, tele, god, pokes = ae.read_drive(out / f"l2_{drive}.drive")
    st = {"gf": -1, "slots": [0] * 5, "pk": [0] * 4, "lives": None, "dying": 0, "face": {}}
    log: list[tuple[int, str]] = []
    rd = b.uc.reg_read

    def w(addr: int, signed: bool = True) -> int:
        v = b.read_word(addr)
        return v - 0x10000 if signed and v & 0x8000 else v

    def ev(text: str) -> None:
        log.append((st["gf"], text))

    def slot() -> int:
        return ((rd(ae.a_reg(3)) & 0xFFFFFF) - 0xBE4) // 4

    def word(reg: int) -> int:
        v = rd(reg) & 0xFFFF
        return v - 0x10000 if v & 0x8000 else v

    hooks = {
        0xC78E: lambda: ev(f"type 1 fires: slot {slot()}, facing {'left' if b.uc.mem_read(rd(ae.a_reg(3)) + 2, 1)[0] else 'right'}, "
                           f"bullet type D6 {rd(ae.d_reg(6)) & 0xFFFF}, dir D7 {rd(ae.d_reg(7)) & 0xFF:#x}, "
                           f"at ({word(ae.d_reg(0))}, {word(ae.d_reg(1))})"),
        0xC35A: lambda: ev(f"explosion death $C35A: slot {slot()}, D5 {rd(ae.d_reg(5)) & 0xFFFF:#06x}"),
        0xC33E: lambda: ev(f"type 6 killed: $15F2 {w(0x15F2) + 1}"),
        0xC356: lambda: ev(f"type 6's pickup: type {rd(ae.d_reg(2)) & 0xFF:#04x}"),
        0xD20E: lambda: ev(f"type 6 launched: slot {slot()}, gap $D1DC {w(0xD1DC)} -> 2"),
        0xD1CA: lambda: ev(f"type 6 waits: gap $D1DC {w(0xD1DC)} -> {w(0xD1DC) - 1}"),
        0xD29E: lambda: ev(f"type 6 bounces: slot {slot()} at ({word(ae.d_reg(0))}, {word(ae.d_reg(1))})"),
        0x9F32: lambda: ev(f"mine stepped on: object {((rd(ae.a_reg(1)) & 0xFFFFFF) - 0xA828) // 12} "
                           f"at ({word(ae.d_reg(0))}, {word(ae.d_reg(1))})"),
        0xF366: lambda: ev(f"explosion: type D5 {rd(ae.d_reg(5)) & 0xFFFF:#x} at ({word(ae.d_reg(0))}, {word(ae.d_reg(1))}), "
                           f"from ${b.read_long(rd(ae.a_reg(7)) & 0xFFFFFF) - 4:05x}"),
        0xE796: lambda: ev(f"type 49 touches RoboCop: slot {slot()}, energy target {w(0x169A)} - 18h"),
        0xE79C: lambda: ev(f"type 49 explodes: slot {slot()}"),
        0xC2D8: lambda: ev(f"type 2 killed (death $C2D8): slot {slot()}"),
        0xC936: lambda: ev("type 2 arrested: $16D0 set ($C936)"),
        0xFD76: lambda: ev(f"message: {text_at(b, rd(ae.a_reg(0)) & 0xFFFFFF)!r}"),
    }

    def on_code(uc, address, size, user_data):
        hooks[address]()

    def on_walked(uc, address, size, user_data):    # type 1 after $EF42 ($C760): its turns, D6 as walk left it
        a3 = rd(ae.a_reg(3)) & 0xFFFFFF
        face, d6 = b.uc.mem_read(a3 + 2, 1)[0], rd(ae.d_reg(6)) & 0xFFFF
        k = slot()
        if k in st["face"] and (face != st["face"][k] or d6):
            ev(f"type 1 turns: slot {k} at x {w(0xBC4 + 4 * k)}, now facing {'left' if face else 'right'}, D6 {d6}")
        st["face"][k] = face

    def on_frame(uc, address, size, user_data):
        st["gf"] += 1
        for k in range(5):
            t = b.uc.mem_read(0xC04 + 4 * k, 1)[0]
            if t != st["slots"][k]:
                if t:
                    ev(f"slot {k}: type {t} spawns at ({w(0xBC4 + 4 * k)}, {w(0xB64 + 4 * k)}), "
                       f"hp {b.uc.mem_read(0xC05 + 4 * k, 1)[0]}")
                else:
                    ev(f"slot {k}: type {st['slots'][k]} gone")
                st["face"].pop(k, None)
                st["slots"][k] = t
        for k in range(4):
            t = b.uc.mem_read(0xD80 + k, 1)[0]
            if t != st["pk"][k]:
                ev(f"pickup slot {k}: type {t:#04x}" + (f" at ({w(0xD84 + 4 * k)}, {w(0xD94 + 4 * k)})" if t else " gone"))
                st["pk"][k] = t
        if every and st["gf"] % every == 0:
            ev(f"RoboCop ({w(0x15D0)}, {w(0x15D4)}), state {w(0x15E2)}, camera ({w(0xB04)}, {w(0xB06)}), "
               f"energy target {w(0x169A)}")
        objl = bytes(b.uc.mem_read(0xA828, 44 * 12))       # the object list: a record's words changing
        if st.get("objl") is not None:
            for k in range(44):
                old, new = st["objl"][12 * k:12 * k + 12], objl[12 * k:12 * k + 12]
                if old != new:
                    ev(f"object {k}: words {old.hex(' ', 2)} -> {new.hex(' ', 2)}")
        st["objl"] = objl
        lives, dying = w(0x8034), b.uc.mem_read(0x16CC, 1)[0]
        if st["lives"] is not None and lives != st["lives"]:
            ev(f"lives {st['lives']} -> {lives}")
        if dying != st["dying"]:
            ev(f"dying ($16CC) {st['dying']:#04x} -> {dying:#04x}, energy target {w(0x169A)}")
        st["lives"], st["dying"] = lives, dying

    for addr in hooks:
        b.uc.hook_add(ae.UC_HOOK_CODE, on_code, None, addr, addr + 1)
    b.uc.hook_add(ae.UC_HOOK_CODE, on_walked, None, 0xC760, 0xC761)
    b.uc.hook_add(ae.UC_HOOK_CODE, on_frame, None, ae.GAME_FRAME_START, ae.GAME_FRAME_START + 1)
    b.stop_at_level_end(2)
    b.play(gframes, script, False, tele, god, 0, None, pokes)
    for gf, text in log:
        print(f"{gf:5d}  {text}")
    end = b.carried()
    print(f"{name}: {st['gf'] + 1} game frames, $8050 {end['level']}, lives {end['lives']}, score {end['score']}, "
          f"{len(log)} events")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("list", "make", "refs", "check", "events"))
    ap.add_argument("names", nargs="*", help="drives (make) or references (refs, check, events); all by default")
    ap.add_argument("--out", type=Path, default=EMU, help="the drives' and references' folder (build/emu)")
    ap.add_argument("--jobs", type=int, default=4, help="refs: bench runs at a time")
    ap.add_argument("--python", default=python(), help="refs: the interpreter with Unicorn ($PY)")
    ap.add_argument("--every", type=int, default=0, help="events: RoboCop's position every N game frames")
    a = ap.parse_args()
    out = a.out.resolve()
    unknown = [n for n in a.names if n not in (DRIVES if a.cmd == "make" else REFS)]
    if unknown:
        ap.error(f"unknown: {' '.join(unknown)}")
    if a.cmd == "list":
        return show_list()
    if a.cmd == "make":
        return make(out, a.names)
    if a.cmd == "refs":
        return refs(out, a.names, max(1, a.jobs), a.python)
    if a.cmd == "check":
        return check(out, a.names)
    if len(a.names) != 1:
        ap.error("events: one reference")
    sys.path.insert(0, str(TOOLS))
    return events(a.names[0], out, a.every)


if __name__ == "__main__":
    raise SystemExit(main())
