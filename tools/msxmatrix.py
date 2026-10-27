#!/usr/bin/env python3
"""Runs a ROM headless in openMSX on a fixed set of generic set-ups, so that every candidate is
checked beyond the user's own hardware (the game relies only on the standard Konami SCC mapper
and the optional sound chips: CLAUDE.md "Generic hardware support").

Each set-up is a fresh machine. The tool waits for the title (SCREEN 8: R#0 = 0Eh), presses
SPACE, and checks that the game runs: the game's tick counter (tick_n) advances, the display is
on, and openMSX reports no DI; HALT. With a label file it also reports what the sound detection
found (mus_mode, snd_fm, scc_pg2).

--no-title is for builds that start without the title (PZ_TEST=1: Brainstorm from the power-on):
no title wait and no key; tick_n must advance between samples at 20 s and 27 s of emulated time
from the power-on, past the BIOS, the intro (about 6 s) and the stage's entry, where the stage's
passes advance it (50 a second). The display and DI; HALT are checked as above.

The display counts as on when R#1 has it at the last sample or 5 ms later: the HUD split blanks a
few lines of every frame (msx/split.asm), and a sample can fall into them.

Set-ups (machine, extensions, how the ROM goes in):
  msx2        Gradiente Expert 2.0, 64K (V9938), the ROM as a Konami SCC cartridge in slot 1
  msx2p       Sony HB-F1XDJ (V9958, MSX-MUSIC built in)
  turbor      Panasonic FS-A1GT (the game on the R800)
  cbios50     C-BIOS MSX2 EU (50 Hz)
  disk        a DDX 3.0 disk interface in slot 1, the cartridge in slot 2
  subslot     the cartridge in subslot 1-0 of a slot expander
  fmpac       the cartridge and an FM-PAC
  megaram     a 2 MiB MegaRAM in slot 1 (the ROM written into its RAM, banks 0-3 selected and
              INIT called, as a loader does) and an SCC cartridge in slot 2
  megaram+    the same with an SCC+ cartridge
  megaram_psg the MegaRAM alone (no SCC: the PSG and the OPLL versions)

usage: msxmatrix.py ROM [--labels FILE] [--home DIR] [--only NAME,...] [--jobs N] [--no-title]
  --home: an openMSX home (share/machines, share/systemroms) with the machines above; it is
  copied for every run and never written. Default: $OPENMSX_HOME or ~/.openMSX.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

OPENMSX = "/Applications/openMSX.app/Contents/MacOS/openmsx"
SETUPS = {
    "msx2": ("Gradiente_Expert20_64K", [], "cart"),
    "msx2p": ("Sony_HB-F1XDJ_128K_Lite", [], "cart"),
    "turbor": ("Panasonic_FS-A1GT", [], "cart"),
    "cbios50": ("C-BIOS_MSX2_EU", [], "cart"),
    "disk": ("Gradiente_Expert20_64K", ["DDX_3.0"], "cart"),
    "subslot": ("Gradiente_Expert20_64K", ["slotexpander"], "cart"),
    "fmpac": ("Gradiente_Expert20_64K", ["fmpac"], "cart"),
    "megaram": ("Gradiente_Expert20_64K", ["MegaRAM_2MB", "scc"], "megaram"),
    "megaram+": ("Gradiente_Expert20_64K", ["MegaRAM_2MB", "scc+"], "megaram"),
    "megaram_psg": ("Gradiente_Expert20_64K", ["MegaRAM_2MB"], "megaram"),
}
# (the session: the title by 20 s at the latest, SPACE, then the game checked 18 s later; with
# --no-title, ::mx_notitle 1: the game sampled at 20 s and 27 s from the power-on)
SESSION = r"""
set ::mx_f [open $::mx_out w]
proc mx_w {a} { expr {[peek $a] + 256 * [peek [expr {$a + 1}]]} }
proc mx_state {tag} {
  set s [format "%s R0 %02X R1 %02X" $tag [vdpreg 0] [vdpreg 1]]
  if {$::mx_tick ne ""} { append s [format " tick %d" [mx_w $::mx_tick]] }
  foreach {n a} $::mx_vars { append s [format " %s %02X" $n [peek $a]] }
  puts $::mx_f $s
}
# (a MegaRAM loader's way: once BASIC is up, the image into the RAM, banks 0-3 selected by writes
# in the MegaRAM's slot 1, page 1 switched to it and a jump to INIT; a reset would not do: the
# BIOS's RAM search writes in its slot, which selects other banks at 4000h-7FFFh)
proc mx_megaram {} {
  set f [open $::mx_rom rb]
  fconfigure $f -translation binary
  set d [read $f]
  close $f
  debug write_block {MegaRam RAM} 0 $d
  foreach {a b} {0x4000 0 0x6000 1 0x8000 2 0xA000 3} { debug write {slotted memory} [expr {(1 << 18) | $a}] $b }
  set i 0
  foreach b {0xF3 0xDB 0xA8 0xE6 0xF3 0xF6 0x04 0xD3 0xA8 0x2A 0x02 0x40 0xE9} {
    debug write memory [expr {0xE000 + $i}] $b
    incr i
  }
  reg pc 0xE000
}
if {$::mx_mode eq "megaram"} { after time 7 mx_megaram }
# (the last sample, then R#1 again 5 ms later, past the split's blank lines)
proc mx_end {} {
  mx_state game2
  after time 0.005 {mx_state game2b; close $::mx_f; exit}
}
set ::mx_title 0
proc mx_poll {} {
  if {[vdpreg 0] == 0x0E} {
    mx_state title
    after time 1 {keymatrixdown 8 1}
    after time 1.3 {keymatrixup 8 1}
    after time 12 {mx_state game1}
    after time 19 mx_end
    return
  }
  incr ::mx_title
  if {$::mx_title > 32} { mx_state notitle; close $::mx_f; exit }
  after time 0.5 mx_poll
}
if {$::mx_notitle} {
  after time 20 {mx_state game1}
  after time 27 mx_end
} else {
  after time 4 mx_poll
}
"""


def label(labels: str, name: str) -> int | None:
    m = re.search(rf"^{name}:\s+equ \$([0-9a-f]+)$", labels, re.M)
    return int(m[1], 16) if m else None


def run(name: str, rom: Path, labels: str, home: Path, title: bool = True) -> str:
    machine, exts, mode = SETUPS[name]
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "home"
        shutil.copytree(home, h, symlinks=True)
        out = Path(tmp) / "state.txt"
        tick = label(labels, "tick_n")
        vs = " ".join(f"{n} 0x{label(labels, n):04X}" for n in ("mus_mode", "snd_fm", "scc_pg2") if label(labels, n))
        pre = Path(tmp) / "pre.tcl"
        pre.write_text(f'set ::mx_out "{out}"\nset ::mx_rom "{rom}"\nset ::mx_mode {mode}\n'
                       f'set ::mx_tick "{f"0x{tick:04X}" if tick else ""}"\nset ::mx_vars {{{vs}}}\n'
                       f'set ::mx_notitle {0 if title else 1}\n')
        sess = Path(tmp) / "session.tcl"
        sess.write_text(SESSION)
        cmd = [OPENMSX, "-machine", machine]
        for e in exts:
            cmd += ["-ext", e]
        if mode == "cart":
            cmd += ["-cart", str(rom), "-romtype", "KonamiSCC"]
        cmd += ["-command", "set mute on; set renderer none; set throttle off", "-script", str(pre), "-script", str(sess)]
        env = dict(os.environ, OPENMSX_HOME=str(h))
        try:
            r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=240)
            log = r.stdout + r.stderr
        except subprocess.TimeoutExpired:
            return f"{name:12s} TIMEOUT"
        state = out.read_text().split("\n") if out.exists() else []
        halt = "DI; HALT" in log
        return verdict(name, state, halt, log, title)


def verdict(name: str, state: list[str], halt: bool, log: str, title: bool = True) -> str:
    """One set-up's line from the session's rows (title, game1, game2, game2b: "TAG R0 xx R1 xx
    tick N mus_mode xx ..."). title = False: --no-title (no title row; the sound from game1's)."""
    rows = {s.split()[0]: s for s in state if s}
    err = next((l for l in log.splitlines() if "rror" in l), "")
    if title and "title" not in rows:
        return f"{name:12s} FAIL no title {'(DI; HALT) ' if halt else ''}{rows.get('notitle', '')} {err}".rstrip()
    t1 = re.search(r"tick (\d+)", rows.get("game1", ""))
    t2 = re.search(r"tick (\d+)", rows.get("game2", ""))
    r1 = [re.search(r"R1 ([0-9A-F]{2})", rows.get(k, "")) for k in ("game2", "game2b")]
    on = any(m and int(m[1], 16) & 0x40 for m in r1)
    ok = not halt and t1 and t2 and int(t2[1]) > int(t1[1]) and on
    tw = rows.get("title" if title else "game1", "").split()
    snd = " ".join(tw[tw.index("mus_mode"):]) if "mus_mode" in tw else ""
    why = "" if ok else (" display off" if t2 and not on else "") + (f" {err}" if err and not (t1 and t2) else "")
    return (f"{name:12s} {'PASS' if ok else 'FAIL'} ticks {t1[1] if t1 else '?'}->{t2[1] if t2 else '?'}"
            f"{' DI; HALT' if halt else ''}{why}  {snd}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("rom", type=Path)
    ap.add_argument("--labels", type=Path)
    ap.add_argument("--home", type=Path, default=Path(os.environ.get("OPENMSX_HOME", Path.home() / ".openMSX")))
    ap.add_argument("--only", default="")
    ap.add_argument("--jobs", type=int, default=2, help="openMSX instances at a time (the project's limit is 2)")
    ap.add_argument("--no-title", action="store_true",
                    help="a build without the title (PZ_TEST=1): no title wait, samples at 20 s and 27 s")
    a = ap.parse_args()
    names = [n for n in (a.only.split(",") if a.only else SETUPS) if n]
    labels = a.labels.read_text() if a.labels else ""
    rom = a.rom.resolve()
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(a.jobs, 2)) as ex:
        results = list(ex.map(lambda n: run(n, rom, labels, a.home, not a.no_title), names))
    for r in results:
        print(r)
    return 0 if all(" PASS " in r + " " for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
