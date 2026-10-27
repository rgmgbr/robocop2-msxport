#!/usr/bin/env python3
"""Two title records (DIR/A_*, DIR/B_*) taken apart: what the title shows and plays against what it
leaves unseen.

usage: titlecmp.py DIR A B

The records: hz.tcl hz_fresh's, or np.tcl np_title_setup's / np_title0_setup's (docs/HARNESS.md
5.17 b). Compared:
- the picture: the title is SCREEN 8 (G7, 212 lines, R#2 1Fh: VRAM 0-D3FFh, interleaved: CPU address
  x lands at physical (x >> 1) + (x & 1) * 10000h); its 54,272 bytes as the VDP shows them;
- the other physical VRAM bytes that differ, by 2 KiB block;
- the VDP registers and the palette (G7 takes neither from the palette: its pixels are 8-bit colours);
- the music log (A_music.txt): per music tick, the SCC's registers and the PSG's; the bytes that
  differ are named (the SCC debuggable: waveforms 00h-7Fh, frequencies A0h-A9h, volumes AAh-AEh,
  enable AFh; the PSG: registers 0-15). Lines are paired in order: the records' windows must start
  at the same tick (an exact record, A_music2.txt, is titlecmp2.py's);
- the PSG writes' count and hash (A_psg.txt);
- the game (at tick 300 of the game the title starts): its RAM D000h-DFFFh by address, its VRAM by
  2 KiB block.
A part whose files are not in both records is left out (an exact record has no music.txt, psg.txt
or game_*: titlecmp2.py compares them). A report: exit 0 unless a file it needs is missing (2).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def blocks(a: bytes, b: bytes, size: int = 2048) -> list[str]:
    out = []
    for k in range(0, len(a), size):
        n = sum(x != y for x, y in zip(a[k:k + size], b[k:k + size]))
        if n:
            out.append(f"{k:05X}h:{n}")
    return out


def picture(v: bytes) -> bytes:
    return bytes(v[(x >> 1) + (x & 1) * 0x10000] for x in range(256 * 212))


def music(path: Path) -> list[tuple[str, bytes, bytes]]:
    """hz_fresh's music log: (tick, the SCC's registers, the PSG's) a line ("tick scc psg"; "tick
    psg" when the record found no SCC debuggable)."""
    rows = []
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            continue
        p = line.split()
        rows.append((p[0], bytes.fromhex(p[1]) if len(p) == 3 else b"", bytes.fromhex(p[-1])))
    return rows


def scc_name(i: int) -> str:
    if i < 0x80:
        return f"wave{i // 32}"
    if i < 0xA0:
        return f"x{i:02X}"
    if i < 0xAA:
        return f"freq{(i - 0xA0) // 2}"
    if i < 0xAF:
        return f"vol{i - 0xAA}"
    if i == 0xAF:
        return "enable"
    return f"x{i:02X}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", type=Path)
    ap.add_argument("a")
    ap.add_argument("b")
    args = ap.parse_args(argv)
    d, a, b = args.dir, args.a, args.b
    for t in (a, b):
        for n in ("title_vram.bin", "title_regs.bin", "title_pal.bin"):
            if not (d / f"{t}_{n}").is_file():
                print(f"titlecmp: no {d / f'{t}_{n}'}", file=sys.stderr)
                return 2
    f = lambda t, n: (d / f"{t}_{n}").read_bytes()
    both = lambda n: (d / f"{a}_{n}").is_file() and (d / f"{b}_{n}").is_file()
    va, vb = f(a, "title_vram.bin"), f(b, "title_vram.bin")
    pa, pb = picture(va), picture(vb)
    shown = {(x >> 1) + (x & 1) * 0x10000 for x in range(256 * 212)}
    other = [i for i in range(len(va)) if va[i] != vb[i] and i not in shown]
    print(f"the title's picture (G7, 256 x 212): {'identical' if pa == pb else 'DIFFERENT in %d bytes' % sum(x != y for x, y in zip(pa, pb))}")
    print(f"VRAM not shown by the title: {len(other)} bytes differ: {blocks(bytes(va[i] if i not in shown else 0 for i in range(len(va))), bytes(vb[i] if i not in shown else 0 for i in range(len(vb))))}")
    ra, rb = f(a, "title_regs.bin"), f(b, "title_regs.bin")
    print("registers:", [f"R#{i} {ra[i]:02X}/{rb[i]:02X}" for i in range(len(ra)) if ra[i] != rb[i]] or "identical")
    la, lb = f(a, "title_pal.bin"), f(b, "title_pal.bin")
    print(f"palette: {'identical' if la == lb else 'different (G7 does not use it)'}")
    if both("music.txt"):
        ma, mb = music(d / f"{a}_music.txt"), music(d / f"{b}_music.txt")
        print(f"music ticks: {len(ma)} / {len(mb)}")
        names, lines = {}, 0
        for (ta, sa, ga), (tb, sb, gb) in zip(ma, mb):
            diff = [scc_name(i) for i in range(len(sa)) if sa[i] != sb[i]] + [f"PSG R{i}" for i in range(16) if ga[i] != gb[i]]
            if ta != tb:
                diff.append("tick")
            if diff:
                lines += 1
                for n in set(diff):
                    names[n] = names.get(n, 0) + 1
        print(f"music ticks that differ: {lines}; by register (ticks): {dict(sorted(names.items()))}")
        if names:
            # the PSG's volume registers decide whether a channel's tone is heard; the SCC's enable bits
            # and volumes whether its waveforms are
            for (ta, sa, ga), (tb, sb, gb) in zip(ma, mb):
                if sa != sb or ga != gb:
                    scc = (f"SCC enable {sa[0xAF]:02X}/{sb[0xAF]:02X} vol {sa[0xAA:0xAF].hex()}/{sb[0xAA:0xAF].hex()}; "
                           if min(len(sa), len(sb)) > 0xAF else "")
                    print(f"  first: tick {ta}: {scc}PSG {ga.hex()} / {gb.hex()}")
                    break
    else:
        print("music.txt: not in both records (an exact record's music2.txt: titlecmp2.py)")
    if both("psg.txt"):
        print(f"PSG writes (count hash): {(d / f'{a}_psg.txt').read_text().split()} / {(d / f'{b}_psg.txt').read_text().split()}")
    else:
        print("psg.txt: not in both records")
    if both("game_ram.bin") and both("game_vram.bin"):
        ga, gb = f(a, "game_ram.bin"), f(b, "game_ram.bin")
        print("game RAM D000h-DFFFh:", [f"{0xD000 + i:04X} {ga[i]:02X}/{gb[i]:02X}" for i in range(len(ga)) if ga[i] != gb[i]] or "identical")
        gva, gvb = f(a, "game_vram.bin"), f(b, "game_vram.bin")
        print("game VRAM by 2 KiB block:", blocks(gva, gvb) or "identical")
        if both("game.txt"):
            print("game:", (d / f"{a}_game.txt").read_text().strip(), "/", (d / f"{b}_game.txt").read_text().strip())
    else:
        print("game_ram.bin, game_vram.bin: not in both records (an exact record's game2_*: titlecmp2.py)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
