# The in-game effects on the SCC: every music.asm fx_start (S tick effect) and, at every
# fx_tick entry, the SCC's channels 0-3 (period, volume, waveform) and PSG R0-R10 (T tick ...),
# under the drive ::fl_drive for ::fl_secs seconds, into ::fl_out.
#
# Level 1's scratch tool of 2026-10-22 (docs/MSX_ARCHITECTURE.md, the effects on the SCC), brought
# into the harness at level 2's step 0 (the plan's 4.3). Its scratch copy was gone; this is its
# last text, from the session's log of 2026-10-27, with two changes for the MSX-AI MCP's openMSX
# (the derived copy the sound's checks ran there on 2026-10-24): it sources tools/openmsx_rc2.tcl
# from its own place, and at the end it sets ::fl_done 1 instead of quitting openMSX (no exit).
# Its checker (fxcheck.py: a model of the engine replaying the starts against sccfx.bin) is lost.
#
# Set before sourcing it: ::fl_rom (an EXTJOY=1 build: a LOCKSTEP build gives the same writes for
# the same logic), ::fl_lab (its labels), ::fl_out, ::fl_drive (a tools/drivejoy.py drive),
# ::fl_secs (emulated seconds); ::fl_dev (optional: the SCC's debuggable, default the cartridge's).
# Then poll ::fl_done. As a tools/bstest/hz.tcl chain job (l2base.tcl l2b_fx_job):
#   {NAME MACHINE {set ::fl_rom ...; ...; source {<repo>/tools/bstest/sess_fxlog.tcl}} {$::fl_done} 600}
source [file join [file dirname [file dirname [file normalize [info script]]]] openmsx_rc2.tcl]
set ::fl_done 0
set ::fl_f [open $::fl_out w]
set ::fl_t 0
if {![info exists ::fl_dev]} { set ::fl_dev "[file tail $::fl_rom] SCC SCC" }
set ::fl_rb "[file tail $::fl_rom] romblocks"
proc fl_s {} { puts $::fl_f "S $::fl_t [reg a]" }
proc fl_t {} {
	set s "T $::fl_t"
	for {set v 0} {$v < 4} {incr v} {
		set f [expr {[debug read $::fl_dev [expr {0xA0 + 2 * $v}]] | (([debug read $::fl_dev [expr {0xA1 + 2 * $v}]] & 15) << 8)}]
		set w 0
		for {set i 0} {$i < 32} {incr i} { set w [expr {($w * 31 + [debug read $::fl_dev [expr {32 * $v + $i}]]) & 0xFFFFFF}] }
		append s " $f [debug read $::fl_dev [expr {0xAA + $v}]] $w"
	}
	append s " [debug read $::fl_dev 0xAF] |"
	for {set r 0} {$r < 11} {incr r} { append s " [debug read {PSG regs} $r]" }
	puts $::fl_f $s
	incr ::fl_t
}
rc2_drive_rom $::fl_rom $::fl_lab [file join [file dirname $::fl_out] fl_trace.txt] 1 999999 $::fl_drive
set ::fl_bank [rc2_label $::fl_lab BANK_MUSIC]
debug set_bp [rc2_label $::fl_lab fx_start] {[debug read $::fl_rb 0xA000] == $::fl_bank} fl_s
debug set_bp [rc2_label $::fl_lab fx_tick] {[debug read $::fl_rb 0xA000] == $::fl_bank} fl_t
after time $::fl_secs { close $::fl_f; set ::fl_done 1 }
set ::pause off
