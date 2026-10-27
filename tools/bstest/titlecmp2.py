#!/usr/bin/env python3
"""np.tcl's exact title records (np_title_setup / np_title0_setup with EXACT 1; docs/HARNESS.md
5.17 b) of two runs compared: DIR/A_* against DIR/B_*.

usage: titlecmp2.py DIR A B [--unheard]

- the music log keyed by mus_tick (A_music2.txt): at every tick both runs logged, the SCC's
  registers, the PSG's and the count and hash of the PSG writes since the previous tick (the
  speech's PCM, the music, the joystick reads through R#14/R#15); the first and last common ticks
  are window edges (the records start and stop by 0.1 s polls) and are left out. Every register
  that differs is named, with the ticks it differs at and those where it can be heard;
- the game the title starts by itself, at exactly its tick 300 (A_game2_ram.bin: RAM D000h-DFFFh
  by address; A_game2_vram.bin: the physical VRAM bytes that differ, those in the HUD
  (1E800h-1FE7Fh), by 2 KiB block): reported only.

Exit 0 when the music is identical at every compared tick, 1 otherwise, 2 when a file is missing.
With --unheard a register that differs passes where neither run can hear it at that tick, and the
PSG writes must still be identical at every tick:
- an SCC channel's waveform, frequency or volume, with the channel off in both runs (its enable
  bit clear or its volume 0). The SCC debuggable: waveforms 00h-9Fh (32 bytes a channel), then
  frequencies A0h-A9h, volumes AAh-AEh and the enable bits AFh, mirrored at B0h-BFh; the bytes
  from C0h on always count as heard;
- a PSG channel's tone period (R0-R5) with its tone off in the mixer (R7) or the channel silent
  (volume 0 without the envelope); the noise period (R6) with no channel that mixes the noise in
  and can sound; the envelope (R11-R13) with no channel in envelope mode; the I/O ports (R14, R15).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from titlecmp import blocks  # noqa: E402

HUD = (0x1E800, 0x1FE80)


def log(path: Path) -> dict[int, tuple[bytes, bytes, str]]:
    """music2.txt: {mus_tick: (the SCC's registers, the PSG's, "count:hash" of the PSG writes since
    the previous tick)}; a line without the SCC's column (no SCC debuggable found) gives b""."""
    out = {}
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            continue
        p = line.split()
        out[int(p[0])] = (bytes.fromhex(p[1]) if len(p) == 4 else b"", bytes.fromhex(p[-2]), p[-1])
    return out


def scc_role(i: int) -> tuple[str, int]:
    """The SCC debuggable's byte i: (kind, channel), kind wave, freq, vol, enable or other (channel
    -1 for the last two)."""
    if i < 0xA0:
        return "wave", i >> 5
    if i < 0xC0:
        j = i & 0x0F
        if j < 0x0A:
            return "freq", j >> 1
        if j < 0x0F:
            return "vol", j - 0x0A
        return "enable", -1
    return "other", -1


def scc_name(i: int) -> str:
    kind, ch = scc_role(i)
    if kind == "wave":
        return f"SCC wave{ch} ({32 * ch:02X}h-{32 * ch + 31:02X}h)"
    return f"SCC {i:02X}h {kind}{ch if ch >= 0 else ''}{' (mirror)' if 0xB0 <= i < 0xC0 else ''}"


def scc_off(s: bytes) -> set[int]:
    """The SCC channels that cannot sound: enable bit clear (AFh) or volume 0 (AAh + channel)."""
    if len(s) < 0xB0:
        return set()
    return {c for c in range(5) if not s[0xAF] >> c & 1 or not s[0xAA + c] & 0x0F}


def psg_quiet(r: bytes) -> set[int]:
    """The PSG registers whose value cannot be heard with the registers r (R7: a set bit turns a
    channel's tone (bits 0-2) or noise (bits 3-5) off; R8-R10: bit 4 the envelope, bits 0-3 the
    volume)."""
    quiet = {14, 15}
    silent = [not r[8 + c] & 0x10 and not r[8 + c] & 0x0F for c in range(3)]
    for c in range(3):
        if r[7] >> c & 1 or silent[c]:
            quiet |= {2 * c, 2 * c + 1}
    if all(r[7] >> (3 + c) & 1 or silent[c] for c in range(3)):
        quiet.add(6)
    if not any(r[8 + c] & 0x10 for c in range(3)):
        quiet |= {11, 12, 13}
    return quiet


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", type=Path)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--unheard", action="store_true",
                    help="pass register differences neither run can hear (the PSG writes still identical)")
    args = ap.parse_args(argv)
    d, a, b = args.dir, args.a, args.b
    missing = [str(d / f"{t}_{n}") for t in (a, b) for n in ("music2.txt", "game2_ram.bin", "game2_vram.bin", "game2.txt")
               if not (d / f"{t}_{n}").is_file()]
    if missing:
        print("titlecmp2: no " + ", ".join(missing), file=sys.stderr)
        return 2
    la, lb = log(d / f"{a}_music2.txt"), log(d / f"{b}_music2.txt")
    if not la or not lb:
        print("titlecmp2: a music log without ticks", file=sys.stderr)
        return 2
    common = sorted(set(la) & set(lb))[1:-1]
    bad = {"SCC": 0, "PSG regs": 0, "PSG writes": 0}
    regs: dict[str, list[int]] = {}             # name: [ticks it differs at, ticks it is heard at, first tick]

    def note(name: str, t: int, quiet: bool) -> None:
        r = regs.setdefault(name, [0, 0, t])
        r[0] += 1
        r[1] += not quiet

    for t in common:
        (sa, ga, wa), (sb, gb, wb) = la[t], lb[t]
        if sa != sb:
            bad["SCC"] += 1
            off = scc_off(sa) & scc_off(sb)
            for i, (x, y) in enumerate(zip(sa, sb)):
                if x != y:
                    kind, ch = scc_role(i)
                    note(scc_name(i), t, kind in ("wave", "freq", "vol") and ch in off)
            if len(sa) != len(sb):
                note("SCC length", t, False)
        if ga != gb:
            bad["PSG regs"] += 1
            quiet = psg_quiet(ga) & psg_quiet(gb)
            for i in range(16):
                if ga[i] != gb[i]:
                    note(f"PSG R{i}", t, i in quiet)
        if wa != wb:
            bad["PSG writes"] += 1
    nw = sum(int(la[t][2].split(":")[0]) for t in common)
    print(f"music: ticks {min(la)}-{max(la)} / {min(lb)}-{max(lb)}; {len(common)} common ticks compared "
          f"({nw} PSG writes in them): differ {bad}")
    for name, (n, h, t0) in regs.items():
        print(f"  {name}: differs at {n} ticks from tick {t0}, heard at {h}")
    ga, gb = (d / f"{a}_game2_ram.bin").read_bytes(), (d / f"{b}_game2_ram.bin").read_bytes()
    print("game at tick 300, RAM D000h-DFFFh:", [f"{0xD000 + i:04X} {ga[i]:02X}/{gb[i]:02X}" for i in range(len(ga)) if ga[i] != gb[i]] or "identical")
    va, vb = (d / f"{a}_game2_vram.bin").read_bytes(), (d / f"{b}_game2_vram.bin").read_bytes()
    n = sum(x != y for x, y in zip(va, vb))
    hud = sum(x != y for x, y in zip(va[HUD[0]:HUD[1]], vb[HUD[0]:HUD[1]]))
    print(f"game at tick 300, VRAM: {n} bytes differ, {hud} in the HUD (1E800h-1FE7Fh); by 2 KiB block:",
          blocks(va, vb) or "identical")
    print("game:", (d / f"{a}_game2.txt").read_text().strip(), "/", (d / f"{b}_game2.txt").read_text().strip())
    heard = sum(h for _, h, _ in regs.values())
    if not common:
        verdict = "FAIL (no music tick in both logs)"
    elif not any(bad.values()):
        verdict = "PASS (the music identical at every compared tick)"
    elif not bad["PSG writes"] and not heard:
        verdict = ("PASS (only registers neither run can hear differ; the PSG writes identical)" if args.unheard
                   else "FAIL (only registers neither run can hear differ: --unheard passes them)")
    else:
        verdict = "FAIL"
    print("titlecmp2:", verdict)
    return 0 if verdict.startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
