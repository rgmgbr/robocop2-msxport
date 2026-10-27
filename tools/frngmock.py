#!/usr/bin/env python3
"""The shooting range's MSX pipeline without the port: tools/openmsx_rc2.tcl's rc2_fr_* procs and
tools/frngcmp.py checked against an Amiga reference (tools/amigaemu.py frng --trace-ram).

The memory an exact port would hold at every pass's fr_tick is made from the Amiga's rows (the
mirror's swapped words: AM D000h-D0C5h, AG DC00h-DCFFh, fr_code's 526 bytes). tclsh runs the procs
on it with openMSX's commands mocked: peek, poke and debug read_block on that memory, debug set_bp
and remove_bp kept in a table, and a breakpoint fired with its condition evaluated (the tick's
bytes CD lo hi are in the mock memory). The run: rc2_fr_drive with the drive file; a stray fr_done
hit before the stage (ignored, as in another slot); one fr_tick a pass, each with that pass's
memory; then, when the reference returned, the mirror's counts and $804C, fr_done, ac_diff's word
(diff_tab + the Amiga's $8060 - $C716) and fr_rated. A reference that did not return ('opp')
stops at its row count (rc2_fr_drive's 'n'). Then tools/frngcmp.py compares the procs' file with
the reference.

Also checked: the bytes poked into ext_joy equal the drive's joystick bytes frame by frame, and the
drive's pokes land at their MSX addresses (a byte at A ^ 1, a word little-endian). With --corrupt
F:ADDR:VALUE the mock memory gets one wrong byte (an MSX address) at the F-th pass, which the
compare must report (exit 1). The labels are made up but for ext_joy (CE5Ah), ac_diff (DD0Ch) and
fr_code (F500h), the plan's addresses.

usage: frngmock.py AMIGA_RAM.jsonl DRIVE_FILE OUTDIR [--corrupt F:ADDR:VALUE]
       (exit 0: 0 differ, the same rows, result and rating, the joystick bytes and pokes right)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import frngcmp  # noqa: E402

TCL = HERE / "openmsx_rc2.tcl"
FIELDS = ROOT / "analysis" / "frng_ram.tsv"
LABELS = {"fr_code": 0xF500, "fr_tick": 0xA123, "fr_frame": 0xA456, "fr_done": 0x7F10, "fr_rated": 0x7F20,
          "ext_joy": 0xCE5A, "ac_diff": 0xDD0C, "diff_tab": 0x9941}


def swap(b: bytes) -> bytes:
    x = bytearray(b + b"\0" * (len(b) & 1))
    x[0::2], x[1::2] = x[1::2], x[0::2]
    return bytes(x)


def fr_code(row: dict) -> bytes:
    """fr_code's 526 bytes in the Amiga's order, from a row's code blocks."""
    out = b""
    for base, n in frngcmp.PIECES:
        for lo, hexs in row["code"].items():
            lo = int(lo, 16)
            blk = bytes.fromhex(hexs)
            if lo <= base and base + n <= lo + len(blk):
                out += blk[base - lo:base - lo + n]
                break
        else:
            raise KeyError(f"${base:x} in no code block")
    return out


def msx_writes(addr: int, value: int, size: int) -> list[tuple[int, int]]:
    """Where rc2_fr_hit must put a drive's poke: [(MSX address, byte)]."""
    if 0x8000 <= addr < 0x8100:
        m = 0x5C00 + addr
    elif 0xB00 <= addr < 0xBC6:
        m = 0xC500 + addr
    else:
        off = frngcmp.piece_offset(addr)
        if off is None:
            return []
        m = LABELS["fr_code"] + off
    if size == 1:
        return [(m ^ 1, value & 0xFF)]
    return [(m, value & 0xFF), (m + 1, value >> 8 & 0xFF)]


TCL_MOCK = r"""
array set ::mem {}
set ::pokes {}
set ::bps [dict create]
set ::nbp 0
set ::pause on
proc peek {a} { set a [expr {$a}] ; if {[info exists ::mem($a)]} { return $::mem($a) } ; return 0 }
proc poke {a v} { set a [expr {$a}] ; set ::mem($a) [expr {$v & 0xFF}] ; lappend ::pokes $a [expr {$v & 0xFF}] }
proc debug {cmd args} {
	switch -- $cmd {
		read_block { lassign $args space addr len ; set s "" ; for {set i 0} {$i < $len} {incr i} { append s [binary format c [peek [expr {$addr + $i}]]] } ; return $s }
		set_bp { lassign $args addr cond cmd ; incr ::nbp ; set id "bp#$::nbp" ; dict set ::bps $id [list [expr {$addr}] $cond $cmd] ; return $id }
		remove_bp { dict unset ::bps [lindex $args 0] ; return }
		breakpoint { if {[lindex $args 0] eq "list"} { set l {} ; dict for {id v} $::bps { lappend l $id {} } ; return $l } ; dict unset ::bps [lindex $args 1] ; return }
		condition { return {} }
		breaked { return 0 }
	}
}
proc carta {args} {}
proc reset {} {}
proc fire {addr} {
	dict for {id v} $::bps {
		lassign $v a cond cmd
		if {$a != [expr {$addr}]} continue
		if {$cond ne "" && ![expr $cond]} continue
		uplevel #0 $cmd
	}
}
lassign $argv tcl labels trace n drive memfile final
source $tcl
set ::mem([expr {0xA123}]) 0xCD
set ::mem([expr {0xA124}]) 0x56
set ::mem([expr {0xA125}]) 0xA4
set ::mem([expr {0x7F10}]) 0xC9
set ::mem([expr {0x7F20}]) 0xC9
puts "start [rc2_fr_drive mock.rom $labels $trace $n 0 $drive]"
set ::pokes {}
fire 0x7F10
set f [open $memfile r]
while {[gets $f line] >= 0} {
	foreach blk [split $line] {
		lassign [split $blk :] base hex
		set base [expr {"0x$base"}]
		set k [expr {[string length $hex] / 2}]
		for {set i 0} {$i < $k} {incr i} { set ::mem([expr {$base + $i}]) [expr {"0x[string range $hex [expr {2 * $i}] [expr {2 * $i + 1}]]"}] }
	}
	lappend ::pokes tick [expr {[peek 0xD000] + 256 * [peek 0xD001]}]
	fire 0xA123
}
close $f
if {$final ne ""} {
	lassign $final dummy correct timeout offset
	set ::mem([expr {0xD006}]) [expr {$dummy & 0xFF}]
	set ::mem([expr {0xD007}]) [expr {$dummy >> 8 & 0xFF}]
	set ::mem([expr {0xD004}]) [expr {$correct & 0xFF}]
	set ::mem([expr {0xD005}]) [expr {$correct >> 8 & 0xFF}]
	set ::mem([expr {0xDC4D}]) $timeout
	fire 0x7F20
	fire 0x7F10
	set w [expr {0x9941 + $offset}]
	set ::mem([expr {0xDD0C}]) [expr {$w & 0xFF}]
	set ::mem([expr {0xDD0D}]) [expr {$w >> 8 & 0xFF}]
	fire 0x7F20
}
puts "pokes $::pokes"
puts "done $::rc2_trace_done pause $::pause bps [dict size $::bps] result {$::rc2_fr_result} rating $::rc2_fr_rating"
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("amiga", type=Path)
    ap.add_argument("drive", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--corrupt", help="F:ADDR:VALUE: one wrong byte at an MSX address in the F-th pass's memory")
    a = ap.parse_args()
    if not shutil.which("tclsh"):
        print("frngmock.py needs tclsh", file=sys.stderr)
        return 2
    a.out.mkdir(parents=True, exist_ok=True)
    rows, end = frngcmp.read_amiga(a.amiga)
    corrupt = tuple(int(x, 0) for x in a.corrupt.split(":")) if a.corrupt else None
    lines = []
    for k, r in enumerate(rows):
        mem = {0xD000: swap(bytes.fromhex(r["vars"])), 0xDC00: swap(bytes.fromhex(r["glob"])),
               LABELS["fr_code"]: swap(fr_code(r))}
        if corrupt and corrupt[0] == k:
            for base, blk in mem.items():
                if base <= corrupt[1] < base + len(blk):
                    b = bytearray(blk)
                    b[corrupt[1] - base] = corrupt[2]
                    mem[base] = bytes(b)
        lines.append(" ".join(f"{base:04X}:{blk.hex()}" for base, blk in mem.items()))
    (a.out / "mem.txt").write_text("\n".join(lines) + "\n")
    (a.out / "mock.labels").write_text("".join(f"{k}:\tequ ${v:04x}\n" for k, v in LABELS.items()))
    (a.out / "mock.tcl").write_text(TCL_MOCK)
    final = ""
    if end is not None:
        res = end["result"]
        offset = int(end["rating"]["table"], 16) - frngcmp.SHARP
        final = f"{res['dummy']} {res['correct']} {res['timeout']} {offset}"
    n = 100000 if end is not None else len(rows)
    trace = a.out / "msx_trace.txt"
    p = subprocess.run(["tclsh", str(a.out / "mock.tcl"), str(TCL), str(a.out / "mock.labels"), str(trace), str(n),
                        str(a.drive), str(a.out / "mem.txt"), final], capture_output=True, text=True)
    if p.returncode:
        print(p.stdout + p.stderr)
        return 1
    out = dict(line.split(" ", 1) for line in p.stdout.splitlines() if " " in line)
    print(out.get("done", "?"))
    # the input the procs gave: per pass ("tick F"), the bytes poked after it
    words = out.get("pokes", "").split()
    per_pass, cur = {}, None
    i = 0
    while i < len(words):
        if words[i] == "tick":
            cur = int(words[i + 1])
            per_pass[cur] = []
        elif cur is not None:
            per_pass[cur].append((int(words[i]), int(words[i + 1])))
        i += 2
    drive = (a.drive.read_text().split("\n") + ["", "", "", ""])[:4]
    joy = bytes.fromhex(drive[0].strip())
    dpokes = [tuple(int(v, 0) for v in t.split(":")) for t in drive[3].split()]
    joy_ok, poke_ok = True, True
    last = max(per_pass, default=None)
    for f, writes in per_pass.items():
        if not writes and end is None and f == last:
            continue                     # (the n-th line: the trace stopped before that pass's input)
        want = [(LABELS["ext_joy"], joy[f] if f < len(joy) else 0)]
        for pf, addr, v, size in dpokes:
            if pf == f:
                want += msx_writes(addr, v, size)
        if not writes or writes[0] != want[0]:
            joy_ok = False
        if writes[1:] != want[1:]:
            poke_ok = False
    passes_poked = sum(1 for w in per_pass.values() if w)
    print(f"ext_joy: {passes_poked} passes, equal to the drive's bytes: {joy_ok}; "
          f"the drive's {len(dpokes)} pokes at their MSX addresses: {poke_ok}")
    p = subprocess.run([sys.executable, "-I", str(HERE / "frngcmp.py"), str(a.amiga), str(trace),
                        "--fields", str(FIELDS), "--show", "5"], capture_output=True, text=True)
    print(p.stdout.strip() + ("\n" + p.stderr.strip() if p.stderr.strip() else ""))
    return p.returncode or (0 if joy_ok and poke_ok else 1)


if __name__ == "__main__":
    raise SystemExit(main())
