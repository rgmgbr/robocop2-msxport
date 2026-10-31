# vatlog.tcl: level 2's vats on the screen (docs/LEVEL2.md 4.2 check 8; its step 14). Sourced after
# tools/bstest/load.tcl (hz.tcl, openmsx_rc2.tcl).
#
# vl_jobs DIR ROM LABELS ?SECS? ?FROM? ?MACHINES? ?DRIVE?: on DRIVE (default tour's, build/emu/l2_tour.drive) from
# the power-on of each machine (default C-BIOS_MSX2, the FS-A1FX, the FS-A1GT), from level 2's first
# tick past game frame FROM (default 0) for SECS seconds (default 40): rc2_guard with the tears counted
# (as hz_l2_start_jobs), and every vat column vats.asm draws, into DIR/vat_<m>.txt:
#   C t line0 line1 lines idx look ja jb r23 ycam slot  a column on the page shown: the time of its
#        first part's start (R#46), the beam lines (rc2_rg_line) at that start and when its last part
#        ended, its index in vat_shown, the look, its rows drawn (the vat's own), R#23 when it ended
#        (the play field's when that is in the next picture's display) and cam_y, its first line's
#        place on the page (((r0 + ja) & 15) * 16)
#   p dx dy nx ny  each part (its command's destination: R#36-R#43), P n  their number;
#   M t vblanks  a V9938 mirror done (vat_bk set to cleared, VBLANKs)
#   R t us  vat_run's time (us of emulated time, the chain's wait included) when it drew a column
#   Q t us  vat_prep's when it made a column ready
#   S secs run_us prep_us run_calls prep_calls  at the end: the time spent in vat_run and vat_prep
#   K ...  the window's tries (vr_try), drops (the engines moved, a tile gone, a BOB came: vr_drop),
#        no time (vr_nt), the VBLANK first (vr_lt), and vat_prep's looks (vp_scan)
#   G frame tick  the game frame at each 100th tick (the rates' clock)
# and the guard's lines (start check format) into DIR/guard_<m>.txt. Check with
# tools/bstest/vatcheck.py.
proc vl_jobs {dir rom labels {secs 40} {from 0} {machines {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT}} {drive ""}} {
	file mkdir $dir
	if {$drive eq ""} { set drive "$::hz_root/build/emu/l2_tour.drive" }
	set jobs {}
	foreach {t m} $machines {
		lappend jobs [list vl_$t $m [list vl_setup $dir $t $rom $labels $drive $secs $from] {[vl_done]} 1800]
	}
	return $jobs
}

proc vl_setup {dir t rom labels drive secs from} {
	set ::vl_dir $dir
	set ::vl_t $t
	set ::vl_lab $labels
	set ::vl_secs $secs
	set ::vl_from $from
	set ::vl_on 0
	set ::vl_written 0
	set ::rg_done 0
	unset -nocomplain ::rg_notear
	catch {close $::vl_f}
	set ::vl_f [open [file join $dir vat_$t.txt] w]
	hz_l2_drive $rom $labels [file join $dir l2_$t.txt] 2654 $drive
	set ts [rc2_label $labels tick_start]
	set gt [rc2_label $labels game_tick]
	set bank [expr {[rc2_label $labels BANK_L2]}]
	set ::vl_bank $bank
	set ::vl_go_bp [debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt && \[peek 0xF1A0\] == $bank && \[rc2_w 0xD000\] >= $from" vl_go]
}

proc vl_go {} {
	debug remove_bp $::vl_go_bp
	set lab $::vl_lab
	rc2_guard $::vl_secs 159 262 163 $lab
	catch {puts $::vl_f "G [rc2_w 0xD000] [rc2_w 0xCEE0] [format %.6f [machine_info time]]"}
	set a0 [rc2_label $lab act_a000]
	set b $::vl_bank
	set ::vl_bps [list \
		[debug set_bp [rc2_label $lab ve_go1] "\[peek $a0\] == $b" vl_c0] \
		[debug set_bp [rc2_label $lab ve_go2] "\[peek $a0\] == $b" vl_c1] \
		[debug set_bp [rc2_label $lab vr_ok] "\[peek $a0\] == $b" vl_cok] \
		[debug set_bp [rc2_label $lab vat_run] "\[peek $a0\] == $b" vl_r0] \
		[debug set_bp [rc2_label $lab vw_ret] {} vl_r1] \
		[debug set_bp [rc2_label $lab vmg_end] "\[peek $a0\] == $b" vl_m1] \
		[debug set_bp [rc2_label $lab tick_start] {} vl_tick]]
	set ::vl_pb [debug probe set_bp VDP.commandExecuting {[debug probe read VDP.commandExecuting] == 0} vl_cend]
	set ::vl_bk [rc2_label $lab vat_bk]
	set ::vl_wait 0
	set ::vl_r -1
	set ::vl_drew 0
	set ::vl_mt -1
	set ::vl_on 1
	set ::vl_ticks 0
	set ::vl_p -1
	set ::vl_sum {0 0 0 0}
	set ::vl_t0 [machine_info time]
	set ::vl_rdy [expr {[rc2_label $lab vat_fr] + 28}]
	lappend ::vl_bps [debug set_bp [rc2_label $lab vat_prep] "\[peek $a0\] == $b" vl_p0]
	set ::vl_mm -1
	set ::vl_msum {0 0}
	lappend ::vl_bps [debug set_bp [rc2_label $lab vat_mirror] "\[peek $a0\] == $b" {set ::vl_mm [machine_info time]}]
	lappend ::vl_bps [debug set_bp [rc2_label $lab vat_pass] "\[peek $a0\] == $b" {set ::vl_ps [machine_info time]}]
	catch {
		set ::vl_mc {}
		lappend ::vl_bps [debug set_bp [rc2_label $lab vmg_c] "\[peek $a0\] == $b" {set ::vl_mc1 [machine_info time]; set ::vl_mcb [expr {[debug read "VDP status regs" 2] & 1}]}]
		lappend ::vl_bps [debug set_bp [rc2_label $lab vmg_d] "\[peek $a0\] == $b" {lappend ::vl_mc [list [expr {int(($::vl_mc1 - $::vl_mm) * 1e6)}] [expr {int(([machine_info time] - $::vl_mc1) * 1e6)}] $::vl_mcb]}]
		lappend ::vl_bps [debug set_bp [rc2_label $lab vmg_end] "\[peek $a0\] == $b" {set ::vl_me [machine_info time]}]
		lappend ::vl_bps [debug set_bp [rc2_label $lab fb_meetq] {} {incr ::vl_mq}]
		set ::vl_mq 0
	}
	set ::vl_ps -1
	set ::vl_psum {0 0}
	array unset ::vl_k
	foreach k {vr_try vr_drop vr_nt vr_lt vp_scan} {
		set ::vl_k($k) 0
		lappend ::vl_bps [debug set_bp [rc2_label $lab $k] "\[peek $a0\] == $b" [list incr ::vl_k($k)]]
	}
}

proc vl_c0 {} {                         ;# a column's first part: R#46 about to be written
	set ix [reg ix]
	set ::vl_c [list [machine_info time] [rc2_rg_line] [peek [expr {$ix + 26}]] [peek [expr {$ix + 25}]] \
		[peek [expr {$ix + 3}]] [peek [expr {$ix + 4}]] [debug read "VDP regs" 23] [rc2_w 0xC022] \
		[expr {(([peek [expr {$ix + 2}]] + [peek [expr {$ix + 3}]]) & 15) * 16}]]
	set ::vl_n 1
	set ::vl_parts [list [vl_dest]]
}
proc vl_c1 {} { incr ::vl_n; lappend ::vl_parts [vl_dest] }
proc vl_dest {} {
	set r {}
	foreach k {36 38 40 42} { lappend r [expr {[debug read "VDP regs" $k] | ([debug read "VDP regs" [expr {$k + 1}]] << 8)}] }
	return $r
}
proc vl_cok {} {                        ;# its last part started: its end is the next command end
	set ::vl_wait 1
	set ::vl_drew 1
	if {[peek $::vl_bk]} { set ::vl_mt [peek 0xC001] }
}
proc vl_cend {} {
	if {!$::vl_wait} { return }
	set ::vl_wait 0
	lassign $::vl_c t l0 idx look ja jb r23 ycam slot
	set r23 [debug read "VDP regs" 23]
	set t1 [machine_info time]
	set l1 [rc2_rg_line]
	set n [expr {int(($t1 - $t) * 3579545.0 / 228.0 + 0.5)}]
	catch {
		puts $::vl_f "C [format %.6f $t] $l0 $l1 $n $idx $look $ja $jb $r23 $ycam $slot"
		foreach q $::vl_parts { puts $::vl_f "p $q" }
		puts $::vl_f "P $::vl_n"
	}
}
proc vl_r0 {} { set ::vl_r [machine_info time]; set ::vl_drew 0 }
proc vl_p0 {} { set ::vl_p [machine_info time]; set ::vl_p_rdy [peek $::vl_rdy] }
proc vl_r1 {} {
	set now [machine_info time]
	if {$::vl_r >= 0} {
		set us [expr {($now - $::vl_r) * 1e6}]
		lset ::vl_sum 0 [expr {[lindex $::vl_sum 0] + $us}]
		lset ::vl_sum 2 [expr {[lindex $::vl_sum 2] + 1}]
		if {$::vl_drew} { catch {puts $::vl_f "R [format %.6f $::vl_r] [expr {int($us + 0.5)}]"} }
		set ::vl_r -1
	}
	if {$::vl_mm >= 0} {
		catch {lappend ::vl_mc [list end [expr {int(($now - $::vl_me) * 1e6)}] meetq $::vl_mq]; set ::vl_me $now}
		lset ::vl_msum 0 [expr {[lindex $::vl_msum 0] + ($now - $::vl_mm) * 1e6}]
		lset ::vl_msum 1 [expr {[lindex $::vl_msum 1] + 1}]
		set ::vl_mm -1
	}
	if {$::vl_ps >= 0} {
		lset ::vl_psum 0 [expr {[lindex $::vl_psum 0] + ($now - $::vl_ps) * 1e6}]
		lset ::vl_psum 1 [expr {[lindex $::vl_psum 1] + 1}]
		set ::vl_ps -1
	}
	if {$::vl_p >= 0} {
		set us [expr {($now - $::vl_p) * 1e6}]
		lset ::vl_sum 1 [expr {[lindex $::vl_sum 1] + $us}]
		lset ::vl_sum 3 [expr {[lindex $::vl_sum 3] + 1}]
		if {!$::vl_p_rdy && [peek $::vl_rdy]} { catch {puts $::vl_f "Q [format %.6f $::vl_p] [expr {int($us + 0.5)}]"} }
		set ::vl_p -1
	}
}
proc vl_m1 {} {
	if {$::vl_mt < 0} { return }
	catch {puts $::vl_f "M [format %.6f [machine_info time]] [expr {([peek 0xC001] - $::vl_mt) & 255}]"}
	set ::vl_mt -1
}
proc vl_tick {} {
	incr ::vl_ticks
	if {$::vl_ticks % 100 == 0} { catch {puts $::vl_f "G [rc2_w 0xD000] [rc2_w 0xCEE0] [format %.6f [machine_info time]]"} }
}

proc vl_done {} {
	if {!$::vl_on || !$::rg_done} { return 0 }
	if {$::vl_written} { return 1 }
	set ::vl_written 1
	foreach b $::vl_bps { catch {debug remove_bp $b} }
	catch {debug probe remove_bp $::vl_pb}
	catch {puts $::vl_f "S [format %.3f [expr {[machine_info time] - $::vl_t0}]] [expr {int([lindex $::vl_sum 0])}] [expr {int([lindex $::vl_sum 1])}] [lindex $::vl_sum 2] [lindex $::vl_sum 3]"}
	catch {puts $::vl_f "MC $::vl_mc"}
	catch {puts $::vl_f "K [array get ::vl_k] frames [expr {int(([machine_info time] - $::vl_t0) * 60)}] mirror_us [expr {int([lindex $::vl_msum 0])}] mirror_calls [lindex $::vl_msum 1] pass_us [expr {int([lindex $::vl_psum 0])}] passes [lindex $::vl_psum 1]"}
	catch {close $::vl_f}
	set f [open [file join $::vl_dir guard_$::vl_t.txt] w]
	catch {
		puts $f "end: game frame [rc2_w 0xD000] tick_n [rc2_w 0xCEE0] time [machine_info time]"
		puts $f "lost: mp [peek 0x1084] atr [peek 0x1082] rd [peek 0x1088] fb [peek 0x069C]"
		set g {}
		foreach k {reg pal cmd cpu vbl tear} { lappend g "$k $::rg_n($k)" }
		puts $f "guard: [join $g {, }]"
		foreach x $::rg_log { puts $f "  $x" }
	}
	close $f
	return 1
}

# vl_speed_jobs DIR ROM LABELS ?SECS? ?FROM? ?MACHINES?: the game's speed (no guard, no logger) on tour
# from level 2's first tick past game frame FROM for SECS seconds: DIR/speed_<m>.txt "speed: frames F0 F1
# ticks T0 T1 secs S" (the game frames and ticks run; compare a build with the vats' display with one
# without, e.g. the commit before it: the vats' CPU share as the game sees it).
proc vl_speed_jobs {dir rom labels {secs 25} {from 450} {machines {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT}}} {
	file mkdir $dir
	set e "$::hz_root/build/emu"
	set jobs {}
	foreach {t m} $machines {
		lappend jobs [list sp_$t $m [list vl_speed_setup [file join $dir speed_$t.txt] $rom $labels "$e/l2_tour.drive" $secs $from] {$::vl_sp_done} 1800]
	}
	return $jobs
}
proc vl_speed_setup {out rom labels drive secs from} {
	set ::vl_sp_out $out
	set ::vl_sp_secs $secs
	set ::vl_sp_done 0
	hz_l2_drive $rom $labels [file join [file dirname $out] sp_trace.txt] 2654 $drive
	set ts [rc2_label $labels tick_start]
	set gt [rc2_label $labels game_tick]
	set bank [expr {[rc2_label $labels BANK_L2]}]
	set ::vl_sp_bp [debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt && \[peek 0xF1A0\] == $bank && \[rc2_w 0xD000\] >= $from" vl_sp_go]
}
proc vl_sp_go {} {
	debug remove_bp $::vl_sp_bp
	set ::vl_sp0 [list [rc2_w 0xD000] [rc2_w 0xCEE0] [machine_info time]]
	after time $::vl_sp_secs vl_sp_end
}
proc vl_sp_end {} {
	lassign $::vl_sp0 f0 t0 s0
	set f [open $::vl_sp_out w]
	catch {puts $f "speed: frames $f0 [rc2_w 0xD000] ticks $t0 [rc2_w 0xCEE0] secs [format %.3f [expr {[machine_info time] - $s0}]] lost: mp [peek 0x1084] atr [peek 0x1082] rd [peek 0x1088] fb [peek 0x069C]"}
	close $f
	set ::vl_sp_done 1
}

# vl_snap_jobs DIR ROM LABELS FRAMES ?MACHINES?: tour's drive from the power-on with n = F + 1 rows for
# each F of FRAMES, rc2_snap at the trace's end into DIR/<m>_gF: the port's map at the start of game frame
# F, against the bench's (tools/amigaemu.py game --level 2 --carry 10050:2:0:good --gframes F --drive
# build/emu/l2_tour.drive --stop-at-end --dump D) with tools/mapcmp.py D DIR/<m>_gF build/msx/level2.
proc vl_snap_jobs {dir rom labels frames {machines {m2 C-BIOS_MSX2 tr Panasonic_FS-A1GT}}} {
	file mkdir $dir
	set e "$::hz_root/build/emu"
	set jobs {}
	foreach {t m} $machines {
		foreach f $frames {
			lappend jobs [list snap_${t}_$f $m [list vl_snap_setup [file join $dir ${t}_g$f] $rom $labels "$e/l2_tour.drive" [expr {$f + 1}]] {[vl_snap_done]} 900]
		}
	}
	return $jobs
}
proc vl_snap_setup {out rom labels drive n} {
	set ::vl_sn_out $out
	set ::vl_sn_done 0
	hz_l2_drive $rom $labels "$out.trace.txt" $n $drive
}
proc vl_snap_done {} {
	if {$::vl_sn_done} { return 1 }
	if {![info exists ::rc2_trace_done] || !$::rc2_trace_done} { return 0 }
	rc2_snap $::vl_sn_out
	set ::vl_sn_done 1
	return 1
}
