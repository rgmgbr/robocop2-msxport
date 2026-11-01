# lp.tcl (tools/bstest/perf2; agent a_loop's probe of 2026-11-01): the frame pipeline's time decomposition
# on a drive, from Tcl only (the game's code unchanged; breakpoints and probes take no emulated time). Source
# tools/bstest/perf2/load.tcl; RAM addresses from the build's labels (HEAD's when a label is missing).
# Analyse the events with lpan.py. One job = one drive on one machine:
#   lp_job NAME MACHINE DIR ROM LABELS DRIVE N WINS ?DT?
# WINS = a list of {FROM TO} game frames (tick_n at tick_start): events are written only inside them.
# DIR/NAME_ev.txt, one event a line, "<code> <emulated time> [args]":
#   t T tick_n              tick_start (a game tick starts)
#   w T                     wait_frame entered        g T     wf_got (wait_frame's exit)
#   d T wf_n due cap        cadence at cd_cap (B = the ticks due, D = the cap)
#   i T                     isr entered               o T     isr's exit (its ei)
#   s T                     isr_split (RAM)           r T     sp_r19 (the split's ROM tail: isr_fbgo)
#   f T                     isr_r15 (after the split check)
#   v T pk_state fb_hold    isr_vblank
#   k T gframe camx camy vx vy  iv_take: a list taken (its game frame and camera; the view wanted)
#   l T                     iv_list                   z T     iv_late
#   u T                     iv_tick (the sound's turn)
#   c T 0|1                 VDP.commandExecuting changed
#   F T / G T               a frame-cache upload's start (fcg_ld) / end (fcg_dn), BANK_FIELD at A000h
#   x T pc b8 ba sp0 sp1 sp2 fb_cq fb_busy pk_state   a PC sample every DT s (DT <= 0: none)
#   n T tick_n              a window's end
# Rules kept: no vwait/exit/max/min; the channel is ::hz_mf (hz_clean closes it on a timeout).

proc lp_job {name m dir rom labels drive n wins {dt 0.0002}} {
	return [list $name $m [list lp_setup $name $dir $rom $labels $drive $n $wins $dt] {[lp_done]} 3600]
}

proc lp_lab {labels} {
	set f [open $labels r]
	catch {
		while {[gets $f line] >= 0} {
			if {[regexp {^(\w+):\s+equ \$([0-9a-fA-F]+)} $line -> k h]} { set ::lp_a($k) [expr {"0x$h"}] }
		}
	}
	close $f
}

proc lp_setup {name dir rom labels drive n wins dt} {
	file mkdir $dir
	array unset ::lp_a
	lp_lab $labels
	foreach {k def} {act_a000 0xC07D act_8000 0xC07C pk_state 0xC0E0 fb_hold 0xF1EB pk_list 0xC0E1 v_x 0xCE6A v_y 0xCE6C
			wf_n 0xCE7A fb_cq 0xE0FD fb_busy 0xF1E0 tick_n 0xCEE0 ext_joy 0xCE5A} {
		if {![info exists ::lp_a($k)]} { set ::lp_a($k) $def }
	}
	set ::lp_wins $wins
	set ::lp_on 0
	set ::lp_fin 0
	set ::lp_dt $dt
	set ::lp_end [expr {[lindex [lindex $wins end] 1]}]
	set ::lp_written 0
	foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
	foreach {id opts} [debug condition list] { debug condition remove $id }
	catch {foreach x [debug probe list_bp] { debug probe remove_bp [lindex $x 0] }}
	carta eject
	carta insert $rom -romtype KonamiSCC
	if {[debug breaked]} { debug cont }
	set ::pause off
	reset
	set f [open $drive r]
	catch {
		set ::rd_joy [string trim [gets $f]]
		set ::rd_tele {}
		foreach t [split [string trim [gets $f]]] { if {$t ne ""} { lappend ::rd_tele [split $t :] } }
		set ::rd_god [string trim [gets $f]]
		set ::rd_poke {}
		foreach t [split [string trim [gets $f]]] { if {$t ne ""} { lappend ::rd_poke [split $t :] } }
	}
	close $f
	set ::rd_left $n
	set ::rc2_trace_done 0
	set ::hz_mf [open "$dir/${name}_ev.txt" w]
	set ts $::lp_a(tick_start)
	set gt $::lp_a(game_tick)
	set ::lp_bp_tick [debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt" lp_tick]
	set isr $::lp_a(isr)
	set r15 $::lp_a(isr_r15)
	# the fixed area's points: only while a window is on (page 1 holds the cartridge then)
	foreach {code addr} [list w $::lp_a(wait_frame) g $::lp_a(wf_got) i $isr o [expr {$r15 + 16}] \
			r $::lp_a(sp_r19) f $r15 l $::lp_a(iv_list) z $::lp_a(iv_late) \
			u $::lp_a(iv_tick) s $::lp_a(isr_split)] {
		debug set_bp $addr {$::lp_on} [list lp_ev $code]
	}
	debug set_bp $::lp_a(isr_vblank) {$::lp_on} lp_vbl
	debug set_bp $::lp_a(iv_take) {$::lp_on} lp_take
	debug set_bp $::lp_a(cd_cap) {$::lp_on} lp_cad
	set bf $::lp_a(BANK_FIELD)
	debug set_bp $::lp_a(fcg_ld) "\$::lp_on && \[peek $::lp_a(act_a000)\] == $bf" [list lp_ev F]
	debug set_bp $::lp_a(fcg_dn) "\$::lp_on && \[peek $::lp_a(act_a000)\] == $bf" [list lp_ev G]
	set ::lp_pb [debug probe set_bp VDP.commandExecuting {$::lp_on} lp_ce]
	if {$dt > 0} { set ::hz_afters [list [after time $dt lp_samp]] }
	return "lp $name set"
}

proc lp_ev {code} { puts $::hz_mf "$code [machine_info time]" }

proc lp_vbl {} { puts $::hz_mf "v [machine_info time] [peek $::lp_a(pk_state)] [peek $::lp_a(fb_hold)]" }

# a list taken: its game frame (the tail after its pairs: cam_x, cam_y, g_frame), the camera it shows,
# the view wanted (v_x, v_y)
proc lp_take {} {
	set l [rc2_w $::lp_a(pk_list)]
	set len [peek [expr {($l + 1) & 0xFFFF}]]
	set tl [expr {($l + 2 + $len) & 0xFFFF}]
	puts $::hz_mf "k [machine_info time] [rc2_w [expr {($tl + 4) & 0xFFFF}]] [rc2_w $tl] [rc2_w [expr {($tl + 2) & 0xFFFF}]] [rc2_w $::lp_a(v_x)] [rc2_w $::lp_a(v_y)]"
}

proc lp_cad {} {
	puts $::hz_mf "d [machine_info time] [peek $::lp_a(wf_n)] [expr {[reg bc] >> 8}] [expr {[reg de] >> 8}]"
}

proc lp_ce {} { puts $::hz_mf "c [machine_info time] [debug probe read VDP.commandExecuting]" }

proc lp_samp {} {
	if {$::lp_fin} return
	if {$::lp_on} {
		set sp [reg sp]
		puts $::hz_mf "x [machine_info time] [reg pc] [peek $::lp_a(act_8000)] [peek $::lp_a(act_a000)] [rc2_w $sp] [rc2_w [expr {($sp + 2) & 0xFFFF}]] [rc2_w [expr {($sp + 4) & 0xFFFF}]] [peek $::lp_a(fb_cq)] [peek $::lp_a(fb_busy)] [peek $::lp_a(pk_state)]"
	}
	set ::hz_afters [list [after time $::lp_dt lp_samp]]
}

proc lp_inwin {gf} {
	foreach w $::lp_wins {
		lassign $w a b
		if {$gf >= $a && $gf < $b} { return 1 }
	}
	return 0
}

proc lp_tick {} {
	set gf [rc2_w $::lp_a(tick_n)]
	set t [machine_info time]
	set on [lp_inwin $gf]
	if {$on && !$::lp_on} {
		puts $::hz_mf "b $t $gf [debug probe read VDP.commandExecuting]"
	}
	if {!$on && $::lp_on} { puts $::hz_mf "n $t $gf" }
	set ::lp_on $on
	if {$on} { puts $::hz_mf "t $t $gf" }
	if {$::rd_left > 0} {
		incr ::rd_left -1
		if {$::rd_left == 0 || $gf >= $::lp_end} {
			set ::lp_on 0
			debug remove_bp $::lp_bp_tick
			set ::rc2_trace_done 1
			set ::pause on
			return
		}
	}
	set i [expr {2 * $gf}]
	set b [string range $::rd_joy $i [expr {$i + 1}]]
	poke $::lp_a(ext_joy) [expr {$b eq "" ? 0 : "0x$b"}]
	foreach tt $::rd_tele {
		lassign $tt tf tx ty
		if {$tf == $gf} {
			rc2_wset 0xDAD0 $tx
			rc2_wset 0xDAD4 $ty
			set cx [expr {$tx - 0x108}]
			if {$cx < 0} { set cx 0 }
			if {$cx > 0x8E0} { set cx 0x8E0 }
			set cy [expr {$ty - 0x70}]
			if {$cy < 0} { set cy 0 }
			rc2_wset 0xD004 $cx
			rc2_wset 0xD006 $cy
		}
	}
	foreach tt $::rd_poke {
		lassign $tt pf pa pv ps
		if {$pf == $gf} {
			set mm [expr {$pa >= 0x8000 ? 0x5C00 + $pa : 0xC500 + $pa}]
			if {$ps == 1} { poke [expr {$mm ^ 1}] [expr {$pv & 0xFF}] } else { rc2_wset $mm $pv }
		}
	}
	if {$::rd_god} {
		rc2_wset 0xDB9A 0x100
		rc2_wset 0xDBC4 0x100
		rc2_wset 0xDC34 2
	}
}

# the done condition: the drive's rows done (or the last window's end) -> the file closed once; 1
proc lp_done {} {
	if {!$::rc2_trace_done} { return 0 }
	if {!$::lp_written} {
		set ::lp_written 1
		set ::lp_fin 1
		set ::lp_on 0
		catch {debug probe remove_bp $::lp_pb}
		catch {puts $::hz_mf "e [machine_info time] [machine_info config_name]"}
		catch {close $::hz_mf}
		unset -nocomplain ::hz_mf
	}
	return 1
}
