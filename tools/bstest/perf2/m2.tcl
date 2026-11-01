# m2.tcl (tools/bstest/perf2; agent m_l2's instrumentation of 2026-11-01, source load.tcl): level 2's time
# per tick, per picture, the VDP's commands and a PC sampling profile in one pass of a drive (the
# instrumentation is all in Tcl; the game's code is the product's: EXTJOY=1 LV_TEST=2). The RAM addresses
# are msx/msx.inc's at a75405c; m2_setup checks them against the build's labels and stops on a moved one.
# The flash probe (docs/PERF2_PLAN.md 5.3, W0's step 3): DIR/TAG_flash.txt, after every game_tick: time,
# g_frame, per enemy slot OS_FLASH/OS_TYPE/fl_pend (objects.asm: slot k's bytes at OBJ_SLOTS + 4k + 23h
# and + 21h; bob.asm fl_pend), then "fd S N": the BOBs drawn as a colour-15 silhouette in the tick
# (bob.asm bd_mode with A = BM_FLASH), S of them in a tick whose BOBs are shown (bob_skip 0), N in all;
# analyse with flash12.py.
# Side-effect rules learnt on 2026-11-01 (openMSX 21): reading the command registers (debug read "VDP
# regs" 32-46) or S#2 inside the VDP.commandExecuting probe's callback ends the starting command at
# once (the engine is synced before its start-up ran): the commands' parameters are shadowed here from
# the CPU's own port writes (99h with its latch, 9Bh with R#17), the probe callback reads the probe
# value only, and nothing reads S#2.
#   DIR/TAG_ticks.txt  per game tick (tick_start's call of game_tick with lv_cur = BANK_L2):
#                      tick_n g_frame time gcam_x gcam_y p_x p_y vblank_count
#   DIR/TAG_pics.txt   per new list put on screen (iv_late with app_seq changed):
#                      time vblank_count list_gframe list_camx list_camy vram_bytes_so_far cmds_so_far
#   DIR/TAG_cmds.txt   "S time pc b8 ba R#2 R#23 r32 ... r45 r46 isr sp0 sp1 sp2" at each write of R#46 (before it),
#                      "P time v pc" at each change of VDP.commandExecuting
#   DIR/TAG_samp.txt   every DT s: time pc act_8000 act_a000 ctx isr sp0 sp1 sp2 (ctx 1: inside wait_frame; isr 1:
#                      between isr's entry and its ei/reti; spN the stack's words)
#   DIR/TAG_vw.txt     CPU writes to port 98h per "pc:b8:ba"
# Output channels use names hz_clean closes (hz_mf, hzb_f) so that a timed-out job leaves none open.

proc m2_setup {dir tag rom labels drive n {dt 0.0002} {light 0}} {
	file mkdir $dir
	set ::m2_dir $dir
	set ::m2_tag $tag
	set ::m2_light $light
	set ::m2_on 0
	set ::m2_fin 0
	set ::m2_stop 0
	set ::m2_dt $dt
	set ::m2_ticks {}
	set ::m2_pics {}
	set ::m2_marks {}
	set ::m2_fl {}
	set ::m2_ctx 0
	set ::m2_isr 0
	set ::m2_app -1
	set ::m2_vwn 0
	set ::m2_ncmd 0
	set ::m2_lat -1
	set ::m2_r17 0
	set ::m2_ai 1
	array unset ::m2_vw
	array unset ::m2_cr
	for {set i 32} {$i <= 46} {incr i} { set ::m2_cr($i) 0 }
	catch {foreach id [m2_probe_ids] { debug probe remove_bp $id }}
	set ::m2_pbp ""
	set ::m2_wps {}
	hz_l2_drive $rom $labels "$dir/${tag}_trace.txt" $n $drive
	foreach {k a} {tick_n 0xCEE0 tick 0xC001 app_seq 0xC006 vbl_ptr 0xC003 act_8000 0xC07C act_a000 0xC07D
			lv_cur 0xF1A0 fl_pend 0xEC49 late 0xC00A frame 0xC008 mp_lost 0x1084 atr_lost 0x1082 rd_lost 0x1088
			fb_lost 0x069C} {
		if {[rc2_label $labels $k] != $a} { error "m2: $k moved to [rc2_label $labels $k] (m2.tcl reads $a)" }
	}
	set ::m2_fdn 0
	set ::m2_fds 0
	set ts [rc2_label $labels tick_start]
	set gt [rc2_label $labels game_tick]
	set ::m2_bank [expr {[rc2_label $labels BANK_L2]}]
	set late [rc2_label $labels iv_late]
	set wf [rc2_label $labels wait_frame]
	set ml [rc2_label $labels mainloop]
	set isr [rc2_label $labels isr]
	set ::m2_reti [m2_find_reti $rom [rc2_label $labels isr_r15]]
	debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt && \[peek 0xF1A0\] == $::m2_bank" m2_tick
	debug set_bp $late {$::m2_on} m2_pic
	if {!$light} {
		debug set_bp $wf {$::m2_on} {set ::m2_ctx 1}
		debug set_bp [expr {$ml + 3}] {$::m2_on} {set ::m2_ctx 0}
		# the main loop's phases (rc2.asm; offsets checked against this build's bytes): A the loop's top
		# (wait_frame called), B wait_frame returned, C after hud_frame and feed_vdp (the update starts),
		# D ml_fbn (a tick frame's do_update, cam_mark, pl_show, bob_flush done), E ml_spr (fb_frame
		# called), F after fb_frame, G after sprites_frame, H after do_publish, I after cadence,
		# U after a game_tick, K ml_tkd (the ticks done)
		set ts0 [rc2_label $labels tick_start]
		set fbn [rc2_label $labels ml_fbn]
		set spr [rc2_label $labels ml_spr]
		set tkd [rc2_label $labels ml_tkd]
		foreach {k a} [list A $ml B [expr {$ml + 3}] C [expr {$ml + 18}] D $fbn E $spr F [expr {$spr + 6}] G [expr {$spr + 9}] H [expr {$spr + 12}] I [expr {$spr + 15}] U [expr {$ts0 + 3}] K $tkd] {
			debug set_bp $a {$::m2_on} [list m2_mk $k]
		}
		# after each game_tick: the 5 enemy slots' hit-flash bytes (objects.asm OS_FLASH, slot k at
		# OBJ_SLOTS + 4k = D0E4h + 4k, byte +23h) and types (+21h), and fl_pend (EC49h, 5 bytes)
		debug set_bp [expr {$ts0 + 3}] {$::m2_on} m2_flash
		set ::m2_bsk [rc2_label $labels bob_skip]
		debug set_bp [rc2_label $labels bd_mode] "\$::m2_on && ((\[reg af\] >> 8) & 0xFF) == 1" m2_fd
		debug set_bp $isr {$::m2_on} {set ::m2_isr 1}
		debug set_bp $::m2_reti {$::m2_on} {set ::m2_isr 0}
		set ::hz_mf [open "$dir/${tag}_samp.txt" w]
		set ::hzb_f [open "$dir/${tag}_cmds.txt" w]
	}
	return "m2 armed $tag"
}

# the address of isr's "ei / reti" (FB ED 4D) after isr_r15, from the ROM file (the fixed area 4000h-7FFFh
# is the ROM's first 16 KiB)
proc m2_find_reti {rom from} {
	set f [open $rom rb]
	fconfigure $f -translation binary
	seek $f [expr {$from - 0x4000}]
	set b [read $f 128]
	close $f
	set i [string first "\xFB\xED\x4D" $b]
	if {$i < 0} { error "no ei/reti after isr_r15" }
	return [expr {$from + $i}]
}

proc m2_probe_ids {} {
	set ids {}
	foreach x [debug probe list_bp] { lappend ids [lindex $x 0] }
	return $ids
}

proc m2_tick {} {
	if {!$::m2_on} {
		set ::m2_on 1
		if {!$::m2_light} {
			set ::m2_pbp [debug probe set_bp VDP.commandExecuting {} m2_probe]
			lappend ::m2_wps [debug set_watchpoint write_io 0x98 {} m2_vwr]
			lappend ::m2_wps [debug set_watchpoint write_io 0x99 {} m2_w99]
			lappend ::m2_wps [debug set_watchpoint read_io 0x99 {} {set ::m2_lat -1}]
			lappend ::m2_wps [debug set_watchpoint write_io 0x9B {} m2_w9b]
			set ::m2_next [expr {[machine_info time] + $::m2_dt}]
			set ::hz_afters [list [after time $::m2_dt m2_samp]]
		}
	}
	lappend ::m2_ticks "[rc2_w 0xCEE0] [rc2_w 0xD000] [machine_info time] [rc2_w 0xD004] [rc2_w 0xD006] [rc2_w 0xDAD0] [rc2_w 0xDAD4] [peek 0xC001]"
}

proc m2_pic {} {
	set a [peek 0xC006]
	if {$a == $::m2_app} return
	set ::m2_app $a
	set l [rc2_w 0xC003]
	set t [expr {$l + 2 + [peek [expr {$l + 1}]]}]
	lappend ::m2_pics "[machine_info time] [peek 0xC001] [rc2_w [expr {$t + 4}]] [rc2_w $t] [rc2_w [expr {$t + 2}]] $::m2_vwn $::m2_ncmd"
}

proc m2_flash {} {
	set r "[machine_info time] [rc2_w 0xD000]"
	for {set k 0} {$k < 5} {incr k} { append r " [peek [expr {0xD0E4 + 4 * $k + 0x23}]]/[peek [expr {0xD0E4 + 4 * $k + 0x21}]]/[peek [expr {0xEC49 + $k}]]" }
	append r " fd $::m2_fds $::m2_fdn"
	set ::m2_fds 0
	set ::m2_fdn 0
	lappend ::m2_fl $r
}

# a BOB drawn as a colour-15 silhouette (bd_mode with BM_FLASH)
proc m2_fd {} {
	incr ::m2_fdn
	if {[peek $::m2_bsk] == 0} { incr ::m2_fds }
}

proc m2_mk {k} {
	lappend ::m2_marks "$k [machine_info time]"
}

proc m2_probe {} {
	if {$::m2_fin} return
	puts $::hzb_f "P [machine_info time] [debug probe read VDP.commandExecuting] [reg pc]"
}

proc m2_cstart {v} {
	incr ::m2_ncmd
	set r {}
	for {set i 32} {$i <= 45} {incr i} { lappend r $::m2_cr($i) }
	set sp [reg sp]
	puts $::hzb_f "S [machine_info time] [reg pc] [peek 0xC07C] [peek 0xC07D] [debug read {VDP regs} 2] [debug read {VDP regs} 23] $r $v $::m2_isr [rc2_w $sp] [rc2_w [expr {$sp + 2}]] [rc2_w [expr {$sp + 4}]]"
}

proc m2_w99 {} {
	if {$::m2_fin} return
	set v $::wp_last_value
	if {$::m2_lat < 0} { set ::m2_lat $v; return }
	set lo $::m2_lat
	set ::m2_lat -1
	if {($v & 0xC0) != 0x80} return
	set r [expr {$v & 0x3F}]
	if {$r == 17} { set ::m2_r17 [expr {$lo & 0x3F}]; set ::m2_ai [expr {!($lo & 0x80)}]; return }
	if {$r >= 32 && $r <= 46} {
		set ::m2_cr($r) $lo
		if {$r == 46} { m2_cstart $lo }
	}
}

proc m2_w9b {} {
	if {$::m2_fin} return
	set r $::m2_r17
	if {$::m2_ai} { set ::m2_r17 [expr {($r + 1) & 0x3F}] }
	if {$r >= 32 && $r <= 46} {
		set ::m2_cr($r) $::wp_last_value
		if {$r == 46} { m2_cstart $::wp_last_value }
	}
}

proc m2_vwr {} {
	incr ::m2_vwn
	set k "[reg pc]:[peek 0xC07C]:[peek 0xC07D]"
	if {[info exists ::m2_vw($k)]} { incr ::m2_vw($k) } else { set ::m2_vw($k) 1 }
}

# (each sample is scheduled at its ideal time t0 + k DT, not DT after the last one: an 'after time'
#  callback runs at the first instruction boundary at or after its time, and relative delays drifted by
#  about 0.9 % over a run; the actual time is written too)
proc m2_samp {} {
	if {$::m2_stop} return
	set sp [reg sp]
	set t [machine_info time]
	puts $::hz_mf "$t [reg pc] [peek 0xC07C] [peek 0xC07D] $::m2_ctx $::m2_isr [rc2_w $sp] [rc2_w [expr {$sp + 2}]] [rc2_w [expr {$sp + 4}]]"
	set ::m2_next [expr {$::m2_next + $::m2_dt}]
	set d [expr {$::m2_next - $t}]
	if {$d < 1e-7} { set d 1e-7 }
	set ::hz_afters [list [after time $d m2_samp]]
}

# the done condition: the drive's rows written -> everything written and closed once; returns 1
proc m2_done {} {
	if {!$::rc2_trace_done} { return 0 }
	if {$::m2_fin} { return 1 }
	set ::m2_fin 1
	set ::m2_stop 1
	catch {debug probe remove_bp $::m2_pbp}
	foreach w $::m2_wps { catch {debug remove_watchpoint $w} }
	set d $::m2_dir
	set tg $::m2_tag
	set f [open "$d/${tg}_ticks.txt" w]
	catch { foreach x $::m2_ticks { puts $f $x } }
	close $f
	set f [open "$d/${tg}_pics.txt" w]
	catch { foreach x $::m2_pics { puts $f $x } }
	close $f
	if {!$::m2_light} {
		set f [open "$d/${tg}_flash.txt" w]
		catch { foreach x $::m2_fl { puts $f $x } }
		close $f
		set f [open "$d/${tg}_marks.txt" w]
		catch { foreach x $::m2_marks { puts $f $x } }
		close $f
		set f [open "$d/${tg}_vw.txt" w]
		catch { foreach k [array names ::m2_vw] { puts $f "$k $::m2_vw($k)" } }
		close $f
	}
	catch {close $::hz_mf}
	unset -nocomplain ::hz_mf
	catch {close $::hzb_f}
	unset -nocomplain ::hzb_f
	set f [open "$d/${tg}_end.txt" w]
	catch { puts $f "machine [machine_info config_name] end_time [machine_info time] ticks [llength $::m2_ticks] pics [llength $::m2_pics] cmds $::m2_ncmd vram_bytes $::m2_vwn late [rc2_w 0xC00A] frame [rc2_w 0xC008] lost mp [peek 0x1084] atr [peek 0x1082] rd [peek 0x1088] fb [peek 0x069C]" }
	close $f
	return 1
}

# jobs: DRIVE (a build/emu name, e.g. l2_tour) with N rows on the given machines; LIGHT 1: ticks and
# pictures only (the reference for the full instrumentation's non-interference)
proc m2_jobs {dir rom labels drive n {machines {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT}} {dt 0.0002} {light 0}} {
	set jobs {}
	foreach {t m} $machines {
		set tag "${drive}_$t"
		if {$light} { append tag _light }
		lappend jobs [list m2_$tag $m [list m2_setup $dir $tag $rom $labels "$::hz_root/build/emu/$drive.drive" $n $dt $light] {[m2_done]} 3000]
	}
	return $jobs
}
