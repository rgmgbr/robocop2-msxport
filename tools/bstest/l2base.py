#!/usr/bin/env python3
"""Level 2's base (step 0 of its plan; docs/HARNESS.md 5.21): the verdicts on level 1's records of
tools/bstest/l2base.tcl against the base's, and the code banks' free bytes. tools/bstest/l2base.sh
calls it; stdlib only.

  l2base.py banks W [BASE]         every build under W (a ROM with its label file): the free bytes of
                                   each code bank (the "ds LIMIT - NAME_end" lines of msx/rc2.asm);
                                   the product's bank map (W/R/prod/gen/banks.inc, mkrom's summary);
                                   with BASE, the base's free bytes beside them
  l2base.py start NEW.txt BASE.txt a start check (l2b_st_done's file) against the base's: reg, pal,
                                   cmd, cpu, vbl, the patterns, the SATs and the lost counters 0;
                                   tears and lines above 8 at most the base's
  l2base.py field NEW.txt BASE.txt fieldcheck.py's verdicts on a window (NEW.txt: W/l1/field/FROM_M.check.txt):
                                   every picture checked; every picture that differs of a known
                                   class (TEARS: the hostage tear), and per window at most the bound
                                   the timing-control set gives; the base's count beside it
  l2base.py tears CHECK.txt ...    the classes and counts of fieldcheck.py's outputs (the
                                   timing-control set's: TEARS is derived from it)
  l2base.py fresh DIR A B A.labels B.labels
                                   two exact title records from power-on (regress.tcl rgr_xfresh_setup:
                                   DIR/A_*, DIR/B_*): the title's VRAM, registers and palette
                                   identical, its music identical at every tick (titlecmp2.py), the
                                   game at exactly its tick 300: VRAM identical, RAM by ram's rules
  l2base.py ram A.bin B.bin A.labels B.labels [ORIGIN]
                                   two RAM dumps (default D000h-DFFFh) of two builds, by name: a byte
                                   is compared at its variable's place in each build (the nearest
                                   RAM label at or below it, the same name in both, as far as the
                                   variable reaches in the new layout: up to its next label); a byte
                                   past that in place, unless a moved variable's byte lies there; a
                                   differing word that points at the same label and offset in both
                                   builds is a relocated pointer; $B32 (D032h-D033h, R-seeded: the
                                   plan's 4.4) apart; a variable whose name is gone fails
  l2base.py stills NEW BASE        the stills' pictures (tools/msxframe.py's PNGs, NEW/*.png against
                                   BASE/*.png, its _diff.png apart): 0 pixels differ; msxframe's own
                                   verdict (NEW/*.txt: "N differ" against its map without the field
                                   BOBs and patches) at most the base's
Exit 0 when every verdict passes."""
from __future__ import annotations

import bisect
import contextlib
import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def bank_limits() -> list[tuple[str, int]]:
    """(NAME_end, the window's end) for every code bank msx/rc2.asm pads: "ds 0xC000 - field_end"."""
    out = []
    for line in (ROOT / "msx" / "rc2.asm").read_text().splitlines():
        m = re.match(r"\s*ds\s+0x([0-9A-Fa-f]+)\s*-\s*(\w+_end)\b", line)
        if m:
            out.append((m.group(2), int(m.group(1), 16)))
    return out


def labels(path: Path) -> dict[str, int]:
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        m = re.match(r"(\w+):\s+equ \$([0-9a-fA-F]+)$", line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


def free_bytes(lab: Path) -> dict[str, int]:
    lb = labels(lab)
    return {name: limit - lb[name] for name, limit in bank_limits() if name in lb}


def builds(w: Path) -> list[Path]:
    """The label files of the builds under w (a ROM beside them): the product's first, then the
    others by their folder."""
    out = []
    for lab in sorted(w.rglob("*.labels")):
        if lab.with_suffix(".rom").exists() and "variants" not in lab.relative_to(w).parts:
            out.append(lab)
    return sorted(out, key=lambda lab: (lab.parent != w / "R" / "prod", str(lab)))


def cmd_banks(args: list[str]) -> int:
    w = Path(args[0])
    base = Path(args[1]) if len(args) > 1 else None
    names = [n for n, _ in bank_limits()]
    print("free bytes in the code banks (msx/rc2.asm's padded windows; NAME_end labels)")
    print("build".ljust(24) + "".join(n.replace("_end", "").rjust(8) for n in names))
    for lab in builds(w):
        rel = lab.relative_to(w)
        fb = free_bytes(lab)
        print(str(rel.with_suffix("")).ljust(24) + "".join((str(fb[n]) if n in fb else "-").rjust(8) for n in names))
        if base is not None and (base / rel).exists():
            fo = free_bytes(base / rel)
            line = "  base".ljust(24) + "".join((str(fo[n]) if n in fo else "-").rjust(8) for n in names)
            if fo != fb:
                line += "   (differs)"
            print(line)
    prod = w / "R" / "prod"
    inc = prod / "gen" / "banks.inc"
    if inc.exists():
        print()
        print("the product's bank map (R/prod/gen/banks.inc; banks of 8 KiB):")
        for line in inc.read_text().splitlines():
            if "BANK" in line or line.startswith("ROM_BANKS"):
                print("  " + line)
    log = prod / "rc2.log"
    if log.exists():
        last = log.read_text().strip().splitlines()[-1]
        print("mkrom: " + last.split(": ", 1)[-1])
    return 0


def parse_start(path: Path) -> dict[str, int]:
    t = path.read_text()
    out = {}
    m = re.search(r"^guard: (.*)$", t, re.M)
    for kv in (m.group(1).split(", ") if m else []):
        k, v = kv.split()
        out[k] = int(v)
    m = re.search(r"^patcheck: (\d+) entries, (\d+) bad", t, re.M)
    if m:
        out["patterns checked"], out["patterns bad"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"^sprlines: (\d+) frames", t, re.M)
    if m:
        out["lines above 8"] = int(m.group(1))
    m = re.search(r"^satcheck: (\d+) frames differ", t, re.M)
    if m:
        out["SATs bad"] = int(m.group(1))
    m = re.search(r"^lost: mp (\d+) atr (\d+) rd (\d+) fb (\d+)", t, re.M)
    if m:
        out["lost"] = sum(int(x) for x in m.groups())
    return out


def cmd_start(args: list[str]) -> int:
    new, base = parse_start(Path(args[0])), parse_start(Path(args[1]))
    bad = []
    for k in ("reg", "pal", "cmd", "cpu", "vbl", "patterns bad", "SATs bad", "lost"):
        if new.get(k, -1) != 0:
            bad.append(f"{k} {new.get(k, 'missing')}")
    for k in ("tear", "lines above 8"):
        if k not in new or new[k] > base.get(k, 0):
            bad.append(f"{k} {new.get(k, 'missing')} (base {base.get(k, 'missing')})")
    if new.get("patterns checked", 0) == 0:
        bad.append("no pattern checked")
    print(", ".join(f"{k} {v}" for k, v in new.items()) + f"   | base: tear {base.get('tear')}, lines above 8 {base.get('lines above 8')}")
    print("start: " + ("PASS" if not bad else "FAIL: " + "; ".join(bad)))
    return 0 if not bad else 1


def parse_field(path: Path) -> tuple[int, int, int, int]:
    """fieldcheck.py's last line: pictures, checked, pictures that differ, pixels."""
    m = re.search(r"^(\d+) pictures \((\d+) checked\): (\d+) with differences, (\d+) pixels", path.read_text(), re.M)
    if not m:
        return (0, 0, -1, -1)
    return tuple(int(x) for x in m.groups())


# The known hostage tear: level 1's play-field glitch, older than level 2's work (the base a969fc8 has
# it; v0.1.1 had "3/6"): for a few pictures the hostage at (785, 680) shows half its old frame, half
# its new one. Which VDP and which pictures show it moves with the CPU time, so it is classified
# (fieldcheck.py's CLASS lines: the hostage BOBs of the shown and of the newest list), counted and
# reported, and bounded per window on either machine by the timing-control set: the base a969fc8,
# step 4 c726025 and step 5 e0399d4 (2026-10-28, "l2base.py tears" on their check files):
#   860_m2: base 3 pictures (class A), step 4 0, step 5 3 (A); 860_fx: base 0, step 4 6 (A 3, B 3,
#   183 pixels), step 5 5 (A 2, B 3, 124 pixels); every other window 0.
# Per class: at most its pictures and pixels a picture in any one window record of the set; per
# window and machine: at most the set's most pictures and pixels. Any other class (a pixel no list
# explains, a torn explosion, another BOB torn) fails. Milestone 2's field work should fix the tear
# (zero glitches): then this table empties.
TEARS = {
    "860": {
        "classes": {
            "hostage-tear shown=4@785,680 newest=2@785,680+11@961,760": (3, 59),    # A
            "hostage-tear shown=2@785,680+11@961,760 newest=0@785,680": (3, 2),     # B
        },
        "pictures": 6,
        "pixels": 183,
    },
}


def field_classes(path: Path) -> dict[str, list[tuple[str, int]]]:
    """fieldcheck.py's CLASS lines: {class: [(picture, pixels)]}."""
    out: dict[str, list[tuple[str, int]]] = {}
    for line in path.read_text().splitlines():
        m = re.match(r"CLASS (\S+) (.*) px=(\d+)$", line)
        if m:
            out.setdefault(m.group(2), []).append((m.group(1), int(m.group(3))))
    return out


def window_of(path: Path) -> str:
    """The window of a check file W/l1/field/FROM_M.check.txt: FROM (the name's first number)."""
    return next((x for x in path.name.split(".")[0].split("_") if x.isdigit()), "?")


def cmd_field(args: list[str]) -> int:
    newp, basep = Path(args[0]), Path(args[1])
    new, base = parse_field(newp), parse_field(basep)
    win = window_of(newp)
    known = TEARS.get(win, {"classes": {}, "pictures": 0, "pixels": 0})
    cls = field_classes(newp)
    bad = []
    if not (new[0] > 0 and new[1] == new[0] and new[0] == base[0]):
        bad.append("not every picture checked")
    pics: set[str] = set()
    px = 0
    parts = []
    order = list(known["classes"])
    for c, hits in sorted(cls.items(), key=lambda kv: (order.index(kv[0]) if kv[0] in order else 99, kv[0])):
        n, worst = len(hits), max(p for _, p in hits)
        pics |= {h for h, _ in hits}
        px += sum(p for _, p in hits)
        if c not in known["classes"]:
            bad.append(f"a new class: {c} ({n} pictures, {hits[0][0]} first)")
            continue
        bn, bpx = known["classes"][c]
        name = "ABCDEFGH"[order.index(c)]
        parts.append(f"{name} {n}")
        if n > bn or worst > bpx:
            bad.append(f"class {name}: {n} pictures, {worst} pixels a picture (bound {bn}, {bpx})")
    if len(pics) != max(new[2], 0) or px != max(new[3], 0):
        bad.append(f"the classes cover {len(pics)} pictures, {px} pixels of {new[2]}, {new[3]}")
    if len(pics) > known["pictures"] or px > known["pixels"]:
        bad.append(f"{len(pics)} pictures, {px} pixels above the window's bound {known['pictures']}, {known['pixels']}")
    tear = f"the known hostage tear: {', '.join(parts)} pictures; " if parts else ""
    print(f"{new[1]} of {new[0]} pictures checked, {new[2]} differ, {new[3]} pixels ({tear}bound "
          f"{known['pictures']} pictures, {known['pixels']} pixels) | base {base[2]} differ, {base[3]} pixels: "
          + ("PASS" if not bad else "FAIL: " + "; ".join(bad)))
    return 0 if not bad else 1


def cmd_tears(args: list[str]) -> int:
    """Per window: each class's most pictures and pixels a picture in one check file, and the most
    pictures and pixels of one check file (the TEARS table's numbers)."""
    wins: dict[str, dict] = {}
    for a in args:
        p = Path(a)
        w = wins.setdefault(window_of(p), {"classes": {}, "pictures": 0, "pixels": 0, "files": []})
        cls = field_classes(p)
        pics = {h for hits in cls.values() for h, _ in hits}
        px = sum(n for hits in cls.values() for _, n in hits)
        w["pictures"], w["pixels"] = (max(w["pictures"], len(pics)), max(w["pixels"], px))
        w["files"].append(f"{p.parent.name}/{p.name}: {len(pics)} pictures, {px} pixels")
        for c, hits in cls.items():
            n0, p0 = w["classes"].get(c, (0, 0))
            w["classes"][c] = (max(n0, len(hits)), max(p0, max(n for _, n in hits)))
    for k in sorted(wins, key=lambda x: int(x) if x.isdigit() else 0):
        w = wins[k]
        print(f"window {k}: at most {w['pictures']} pictures, {w['pixels']} pixels in one record")
        for c, (n, px) in sorted(w["classes"].items()):
            print(f"  {c}: at most {n} pictures, {px} pixels a picture")
        for f in w["files"]:
            print(f"    {f}")
    return 0


def cmd_ram(args: list[str]) -> int:
    a, b = Path(args[0]).read_bytes(), Path(args[1]).read_bytes()
    la, lb = labels(Path(args[2])), labels(Path(args[3]))
    org = int(args[4], 16) if len(args) > 4 else 0xD000
    end = org + min(len(a), len(b))
    # (the variables: the labels inside the dump, by address; aliases kept together)
    def by_addr(lab: dict[str, int]) -> list[tuple[int, list[str]]]:
        d: dict[int, list[str]] = {}
        for k, v in lab.items():
            if org <= v < end:
                d.setdefault(v, []).append(k)
        return sorted(d.items())
    va = by_addr(la)
    keys = [x for x, _ in va]
    nb = [x for x, _ in by_addr(lb)] + [end]

    def home(i: int) -> list[int]:
        """The new build's offsets for the base's offset i: its variable (the nearest label at or
        below it) by the same name in the new build, at the same offset when the variable reaches
        that far there (up to the new build's next label); [] when it has none (a gap or a tail the
        new layout dropped)."""
        k = bisect.bisect_right(keys, org + i) - 1
        if k < 0:
            return [i]                      # (below every label: in place)
        addr, names = va[k]
        off = org + i - addr
        out = set()
        for n in names:
            if n in lb and org <= lb[n] < end:
                nxt = nb[bisect.bisect_right(nb, lb[n])]
                if lb[n] + off < nxt:
                    out.add(lb[n] + off - org)
        return sorted(out)

    def gone(i: int) -> bool:
        """The base's offset i belongs to a variable whose name the new build lost."""
        k = bisect.bisect_right(keys, org + i) - 1
        return k >= 0 and not any(n in lb for n in va[k][1])

    def near(lab: dict[str, int], v: int) -> tuple[str, int] | None:
        best = None
        for k, x in lab.items():
            if 0x4000 <= x <= v and (best is None or x > best[1] or (x == best[1] and k < best[0])):
                best = (k, x)
        return best

    def pointer(i: int, j: int) -> str | None:
        """The word at base offset i (or i - 1) and its home j: one label and offset in both builds."""
        for w0, w1 in ((i, j), (i - 1, j - 1)):
            if w0 < 0 or w0 + 1 >= len(a) or w1 < 0 or w1 + 1 >= len(b) or w1 + 1 not in home(w0 + 1):
                continue
            x, y = a[w0] | a[w0 + 1] << 8, b[w1] | b[w1 + 1] << 8
            if x < 0x4000 or y < 0x4000:
                continue
            nx, ny = near(la, x), near(lb, y)
            if nx and ny and nx[0] == ny[0] and x - nx[1] == y - ny[1]:
                return f"{org + w0:04X}->{org + w1:04X} {x:04X}->{y:04X} = {nx[0]}+{x - nx[1]}"
        return None

    rseed = {0x032, 0x033}                  # ($B32: R-seeded, the plan's 4.4)
    moved = relocated = same = 0
    homeless, bad, notes = [], [], []
    mapped: set[int] = set()
    for i in range(len(a)):
        hs = home(i)
        if not hs:
            homeless.append(i)
            continue
        mapped.update(hs)
        if i in rseed:
            continue
        if any(a[i] == b[j] for j in hs):
            same += 1
            moved += all(j != i for j in hs)
            continue
        p = next((r for r in (pointer(i, j) for j in hs) if r), None)
        if p:
            relocated += 1
            if p not in notes:
                notes.append(p)
            continue
        bad.append(f"{org + i:04X} {a[i]:02X} / {org + hs[0]:04X} {b[hs[0]]:02X}")
    lost = [i for i in homeless if gone(i)]
    for i in lost:
        bad.append(f"{org + i:04X} {a[i]:02X}: its variable's name is gone from the new build")
    # (a byte past its variable's room in the new layout: free RAM after it in the base, or a tail
    #  the new layout gave to a new or moved variable. In place when no base byte moved there:
    #  equal, else a difference; under a moved variable's bytes: not compared)
    tails = [i for i in homeless if not gone(i) and i in mapped]
    inplace = [i for i in homeless if not gone(i) and i not in mapped]
    for i in inplace:
        if a[i] != b[i]:
            bad.append(f"{org + i:04X} {a[i]:02X} / {b[i]:02X} (in place: past its variable's room in the new layout)")

    def ranges(xs: list[int]) -> str:
        out, k = [], 0
        while k < len(xs):
            j = k
            while j + 1 < len(xs) and xs[j + 1] == xs[j] + 1:
                j += 1
            out.append(f"{org + xs[k]:04X}h" + (f"-{org + xs[j]:04X}h" if j > k else ""))
            k = j + 1
        return ", ".join(out)
    new_only = len(b) - len(mapped)
    print(f"RAM {org:04X}h-{end - 1:04X}h: {len(a)} bytes, {same} equal at their variable's place ({moved} moved "
          f"with it), {relocated} bytes of relocated pointers, D032h-D033h ($B32, R-seeded) apart; past their "
          f"variable's room in the new layout {len(inplace)} compared in place ({ranges(inplace) or 'none'}), "
          f"{len(tails)} not compared (moved variables' bytes there: {ranges(tails) or 'none'}); {new_only} new "
          f"bytes without a base variable; {len(bad)} differ")
    for n in notes:
        print(f"  relocated pointer {n}")
    for x in bad[:20]:
        print(f"  DIFFER {x}")
    print("ram: " + ("PASS" if not bad else "FAIL"))
    return 0 if not bad else 1


def cmd_fresh(args: list[str]) -> int:
    d, ta, tb = Path(args[0]), args[1], args[2]
    bad = []
    for f in ("title_vram.bin", "title_regs.bin", "title_pal.bin", "game2_vram.bin"):
        fa, fb = d / f"{ta}_{f}", d / f"{tb}_{f}"
        if not fa.exists() or not fb.exists():
            print(f"{f}: missing")
            bad.append(f)
            continue
        x, y = fa.read_bytes(), fb.read_bytes()
        n = sum(p != q for p, q in zip(x, y)) + abs(len(x) - len(y))
        print(f"{f}: " + ("identical" if not n else f"DIFFERENT ({n} bytes)"))
        if n:
            bad.append(f)
    ticks = []
    for t in (ta, tb):
        g = d / f"{t}_game2.txt"
        m = re.search(r"tick_n (\d+) \(the title's game tick (\d+)\)", g.read_text() if g.exists() else "")
        ticks.append(m.group(2) if m else "missing")
    print(f"the game recorded at the title's game tick {ticks[0]} / {ticks[1]}")
    if ticks != ["300", "300"]:
        bad.append("the game's tick")
    import titlecmp2                            # (this folder: the music log keyed by mus_tick)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        rc = titlecmp2.main([str(d), ta, tb])
    for line in buf.getvalue().splitlines():
        if line.startswith(("music:", "titlecmp2:", "  ")):
            print("music2: " + line.strip())
    if rc:
        bad.append("the music")
    ra, rb = d / f"{ta}_game2_ram.bin", d / f"{tb}_game2_ram.bin"
    if not ra.exists() or not rb.exists():
        print("game2_ram.bin: missing")
        bad.append("game2_ram.bin")
    elif cmd_ram([str(ra), str(rb), args[3], args[4]]):
        bad.append("the game's RAM")
    print("fresh (exact): " + ("PASS" if not bad else "FAIL: " + ", ".join(bad)))
    return 0 if not bad else 1


def cmd_stills(args: list[str]) -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    from msxreal import read_png                # (stdlib: zlib)
    new, base = Path(args[0]), Path(args[1])
    bad = 0
    n = 0
    def own(d: Path, stem: str) -> int:
        t = (d / (stem + ".txt")).read_text() if (d / (stem + ".txt")).exists() else ""
        m = re.search(r"(\d+) pixels checked, (\d+) differ", t)
        return int(m.group(2)) if m else -1
    for b in sorted(base.glob("*.png")):
        if b.stem.endswith("_diff"):
            continue
        a = new / b.name
        n += 1
        if not a.exists():
            print(f"{b.name}: missing")
            bad += 1
            continue
        mn, mb = own(new, b.stem), own(base, b.stem)
        ownv = f"msxframe {mn} differ (base {mb})"
        if mn < 0 or mn > mb:
            bad += 1
            ownv += " FAIL"
        if a.read_bytes() == b.read_bytes():
            print(f"{b.name}: identical to the base; {ownv}")
            continue
        wa, ha, ra = read_png(a)
        wb, hb, rb = read_png(b)
        if (wa, ha) != (wb, hb):
            print(f"{b.name}: {wa}x{ha} against the base's {wb}x{hb}")
            bad += 1
            continue
        d = sum(1 for y in range(ha) for x in range(wa) if ra[y][3 * x:3 * x + 3] != rb[y][3 * x:3 * x + 3])
        print(f"{b.name}: {d} pixels differ from the base; {ownv}")
        if d:
            bad += 1
    print(f"stills: {n} pictures, " + ("PASS" if n and not bad else f"FAIL ({bad})"))
    return 0 if n and not bad else 1


def main() -> int:
    cmds = {"banks": cmd_banks, "start": cmd_start, "field": cmd_field, "stills": cmd_stills, "tears": cmd_tears,
            "fresh": cmd_fresh, "ram": cmd_ram}
    need = {"fresh": 5, "ram": 4, "field": 2, "start": 2, "stills": 2}
    if len(sys.argv) < 3 or sys.argv[1] not in cmds or len(sys.argv) - 2 < need.get(sys.argv[1], 1):
        print(__doc__, file=sys.stderr)
        return 2
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    return cmds[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
