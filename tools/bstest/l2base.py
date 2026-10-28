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
  l2base.py field NEW.txt BASE.txt fieldcheck.py's verdicts on a window: every picture checked, and at
                                   most the base's pictures and pixels that differ
  l2base.py stills NEW BASE        the stills' pictures (tools/msxframe.py's PNGs, NEW/*.png against
                                   BASE/*.png, its _diff.png apart): 0 pixels differ; msxframe's own
                                   verdict (NEW/*.txt: "N differ" against its map without the field
                                   BOBs and patches) at most the base's
Exit 0 when every verdict passes."""
from __future__ import annotations

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


def cmd_field(args: list[str]) -> int:
    new, base = parse_field(Path(args[0])), parse_field(Path(args[1]))
    ok = new[0] > 0 and new[1] == new[0] and new[0] == base[0] and 0 <= new[2] <= base[2] and 0 <= new[3] <= base[3]
    print(f"{new[1]} of {new[0]} pictures checked, {new[2]} differ, {new[3]} pixels | base {base[1]} of {base[0]}, "
          f"{base[2]} differ, {base[3]} pixels: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


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
    if len(sys.argv) < 3 or sys.argv[1] not in ("banks", "start", "field", "stills"):
        print(__doc__, file=sys.stderr)
        return 2
    return {"banks": cmd_banks, "start": cmd_start, "field": cmd_field, "stills": cmd_stills}[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    sys.exit(main())
