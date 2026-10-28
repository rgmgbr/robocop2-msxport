# l2base.tcl: level 2's base (step 0 of its plan; docs/HARNESS.md 5.21): the records of level 1's
# picture and effects that the range's regression (regress.tcl) does not make, as hz.tcl chain jobs
# in the MSX-AI MCP's openMSX, and one chain with the whole regression. Source it after load.tcl,
# on the builds of "sh tools/bstest/l2base.sh builds W" (W/R: hz.sh builds; W/L: the LOCKSTEP=24
# builds):
#
#   source {<repo>/tools/bstest/load.tcl}; source {<repo>/tools/bstest/l2base.tcl}
#   l2b_chain W ?MARK?   rgr_jobs W all (regress.tcl, 208 jobs), then l2b_jobs W (19): one chain
#   l2b_jobs W           level 1's jobs alone (records into W/l1):
#     tr_die, tr_over, tr_end  the death-and-restart drives and the level's end (build/emu/drive_die,
#                              drive_over, drive_end: 901, 1249, 517 ticks) on the trace build
#                              (W/R/trace), C-BIOS_MSX2: W/l1/trace/NAME.txt (rc2_drive_rom from 0)
#     st_m2, st_fx, st_tr      the start check: the product (W/R/prod) from the power-on of a new
#                              machine (C-BIOS_MSX2, the FS-A1FX, the FS-A1GT: the R800), the title,
#                              SPACE, then 40 s of level 1 from its tick 20 under rc2_guard (tears
#                              counted), rc2_patcheck, rc2_sprlines and rc2_satcheck, started at
#                              tick_start (no VRAM transfer under way: a guard started inside one
#                              takes its writes for the address it does not know, 0); the lost
#                              counters at the end: W/l1/start/NAME.txt
#     fd_FROM_M                the field records: the EXTJOY build (W/R/ext) on drive_cov0, every
#                              picture from game frame FROM, N of them (430 125, 860 480, 1490 360),
#                              on C-BIOS_MSX2 (m2) and the FS-A1FX (fx): rc2_jumprec's record + RAM
#                              0600h-09FFh and F240h-F27Fh, W/l1/field/FROM_M/ (fieldcheck.py)
#     sl_m2, sl_fx             the stills: the LOCKSTEP=24 build (W/L/lock24) on drive_cov0, rc2_snap
#                              at the HUD split of the first new list from game frames 100, 430, 860,
#                              1490 and 2400: W/l1/still/M/gNNNN (tools/msxframe.py)
#     lk_m2, lk_fx             the LOCKSTEP records: rc2_disp_rom, 3000 lists of drive_cov0 on the
#                              same build: W/l1/lock/disp_M.txt (tools/dispcmp.py), the late frames
#                              in disp_M.over
#     fx_scc                   the effects on the SCC: sess_fxlog.tcl for 300 s of drive_cov0 on the
#                              LOCKSTEP build (W/L/lock24), C-BIOS_MSX2: W/l1/fx/fx_scc.txt
#     pw_scc, pw_psg           every PSG write ("VBLANK register value") over the same 300 s, on that
#                              build and on its twin without the SCC (W/L/lock24p, NO_SCC=1: the
#                              effects on the PSG alone, which sess_fxlog.tcl does not see):
#                              W/l1/fx/pw_K.txt; and in the same run the effects by their starts
#                              (l2b_sn_arm: the frames, the starts, every sound tick's state):
#                              W/l1/fx/pw_K_sn.txt (tools/bstest/fxcmp.py)
# Then "sh tools/bstest/l2base.sh check W BASE".
# Rules kept (hz.tcl's): no exit, vwait, max or min; every channel closed on every path; a job's
# probes removed when it ends.

proc l2b_jobs {w} {
	set r "$w/R"
	set l "$w/L"
	set o "$w/l1"
	set e "$::hz_root/build/emu"
	foreach d {trace start field still lock fx} { file mkdir "$o/$d" }
	set jobs {}
	set tr "$r/trace/rc2_ext5.rom"; set trl "$r/trace/rc2_ext5.labels"
	foreach {t n} {die 901 over 1249 end 517} {
		lappend jobs [list tr_$t C-BIOS_MSX2 [list rc2_drive_rom $tr $trl "$o/trace/$t.txt" $n 0 "$e/drive_$t.txt"] {$::rc2_trace_done} 600]
	}
	foreach {t m} {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT} {
		lappend jobs [list st_$t $m [list l2b_st_setup "$o/start/st_$t.txt" "$r/prod/rc2.rom" "$r/prod/rc2.labels" 40] {[l2b_st_done]} 900]
	}
	foreach {t m} {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX} {
		foreach {from n} {430 125 860 480 1490 360} {
			lappend jobs [list fd_${from}_$t $m [list l2b_fd_setup "$o/field/${from}_$t" "$r/ext/rc2_ext.rom" "$r/ext/rc2_ext.labels" "$e/drive_cov0.txt" $from $n] {$::l2b_fd_done} 900]
		}
	}
	set lk "$l/lock24/rc2.rom"; set lkl "$l/lock24/rc2.labels"
	foreach {t m} {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX} {
		lappend jobs [list sl_$t $m [list l2b_sl_setup "$o/still/$t" $lk $lkl "$e/drive_cov0.txt" {100 430 860 1490 2400}] {$::l2b_sl_done} 900]
	}
	foreach {t m} {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX} {
		lappend jobs [list lk_$t $m [list rc2_disp_rom $lk $lkl "$o/lock/disp_$t.txt" 3000 "$e/drive_cov0.txt"] "\[l2b_lk_done {$o/lock/disp_$t.over}\]" 900]
	}
	lappend jobs [list fx_scc C-BIOS_MSX2 [list l2b_fx_setup "$o/fx/fx_scc.txt" "$l/lock24/rc2.rom" "$l/lock24/rc2.labels" "$e/drive_cov0.txt" 300] {$::fl_done} 900]
	foreach {k d} {scc lock24 psg lock24p} {
		lappend jobs [list pw_$k C-BIOS_MSX2 [list l2b_pw_setup "$o/fx/pw_$k.txt" "$l/$d/rc2.rom" "$l/$d/rc2.labels" "$e/drive_cov0.txt" 300] {$::l2b_pw_done} 900]
	}
	return $jobs
}

proc l2b_chain {w {mark ""}} {
	set jobs [concat [rgr_jobs $w all] [l2b_jobs $w]]
	return "[hz_chain $jobs $mark] (l2base.tcl: the regression and level 1's records)"
}

# ----- the start check (the product from the power-on)

proc l2b_st_setup {out rom labels secs} {
	set ::l2b_st_out $out
	set ::l2b_st_rom $rom
	set ::l2b_st_lab $labels
	set ::l2b_st_secs $secs
	set ::l2b_st 0
	set ::l2b_st_written 0
	set ::rg_done 0
	unset -nocomplain ::rg_notear              ;# (tears counted)
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	lappend ::hz_afters [after time 0.2 l2b_st_step]
}

proc l2b_st_step {} {
	switch -- $::l2b_st {
		0 {
			# the title: front_mode 1 and its music on; SPACE a second later
			if {[peek 0xEC44] == 1 && [peek 0xC202] == 1} {
				set ::l2b_st 1
				lappend ::hz_afters [after time 1.0 l2b_st_press]
				return
			}
		}
		2 {
			# level 1 from its tick 20: the checks start at the next tick_start (its "call game_tick")
			if {[peek 0xEC44] == 0 && [rc2_w 0xCEE0] >= 20} {
				set ts [rc2_label $::l2b_st_lab tick_start]
				set gt [rc2_label $::l2b_st_lab game_tick]
				set ::l2b_st_bp [debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt" l2b_st_go]
				set ::l2b_st 3
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.05 l2b_st_step]
}

proc l2b_st_go {} {
	debug remove_bp $::l2b_st_bp
	set lab $::l2b_st_lab
	set ::l2b_st_t0 "game frame [rc2_w 0xD000], tick_n [rc2_w 0xCEE0], time [machine_info time]"
	rc2_guard $::l2b_st_secs 159 262 163 $lab
	rc2_patcheck $::l2b_st_rom [rc2_label $lab spr_plan] [expr {[rc2_label $lab SPR_BASE_BANK]}] \
		[expr {[rc2_label $lab SPR_PAT_BANK]}] [expr {[rc2_label $lab SPR_COL_BANK]}] 100000
	rc2_sprlines 100000 [expr {[rc2_label $lab VIEW_LINES]}]
	rc2_satcheck 100000
	set ::l2b_st 4
}

proc l2b_st_press {} {
	keymatrixdown 8 1
	lappend ::hz_afters [after time 0.3 {keymatrixup 8 1}]
	set ::l2b_st 2
	lappend ::hz_afters [after time 0.05 l2b_st_step]
}

# the job's end: the guard done (it pauses the machine); the results written once
proc l2b_st_done {} {
	if {$::l2b_st != 4 || !$::rg_done} { return 0 }
	if {$::l2b_st_written} { return 1 }
	set ::l2b_st_written 1
	catch {debug probe remove_bp $::rx8_bp}
	catch {debug probe remove_bp $::rs_sat_bp}
	catch {debug remove_bp $::rp_bp}
	set f [open $::l2b_st_out w]
	catch {
		puts $f "start: $::l2b_st_t0"
		puts $f "end: game frame [rc2_w 0xD000], tick_n [rc2_w 0xCEE0], time [machine_info time]"
		set g {}
		foreach k {reg pal cmd cpu vbl tear} { lappend g "$k $::rg_n($k)" }
		puts $f "guard: [join $g {, }]"
		foreach x [lrange $::rg_log 0 40] { puts $f "  $x" }
		puts $f "patcheck: $::rp_n entries, $::rp_bad bad"
		foreach x $::rp_log { puts $f "  $x" }
		puts $f "sprlines: $::rx8_frames frames with a line above 8"
		foreach x $::rx8_log { puts $f "  $x" }
		puts $f "satcheck: $::rs_sat_bad frames differ (mux $::rs_sat_mux)"
		foreach x $::rs_sat_log { puts $f "  $x" }
		puts $f "lost: mp [peek 0x1084] atr [peek 0x1082] rd [peek 0x1088] fb [peek 0x069C]"
	}
	close $f
	return 1
}

# ----- the field records (the play-field engine's state with every picture)

proc l2b_fd_setup {dir rom labels drive from n} {
	file mkdir $dir
	foreach old [glob -nocomplain -directory $dir *.bin] { file delete $old }
	set ::l2b_fd_dir $dir
	set ::l2b_fd_from $from
	set ::l2b_fd_n $n
	set ::l2b_fd_k 0
	set ::l2b_fd_done 0
	rc2_drive_rom $rom $labels [file join $dir trace.txt] 1 999999 $drive
	set ::l2b_fd_bp [debug probe set_bp VDP.IRQhorizontal {[debug probe read VDP.IRQhorizontal] == 1} l2b_fd_hit]
}

proc l2b_fd_hit {} {
	if {$::l2b_fd_done} { return }
	if {[peek 0xC002] == 0} { return }
	set g [rc2_w 0xCEE0]
	if {$g < $::l2b_fd_from || $g > 60000} { return }
	set regs ""
	for {set i 0} {$i < 64} {incr i} { append regs [binary format cu [debug read "VDP regs" $i]] }
	set page [expr {([debug read "VDP regs" 2] >> 5) & 3}]
	set k $::l2b_fd_k
	set f [open [file join $::l2b_fd_dir [format j%03d_f%04d.bin [expr {$k / 60 + 1}] [expr {$k % 60}]]] wb]
	catch {
		fconfigure $f -translation binary
		puts -nonewline $f $regs
		puts -nonewline $f [debug read_block "VDP palette" 0 32]
		if {([debug read "VDP regs" 25] & 1) && ($page & 1)} {
			puts -nonewline $f [debug read_block VRAM [expr {($page & 2) * 0x8000}] 0x10000]
		} else {
			puts -nonewline $f [debug read_block VRAM [expr {$page * 0x8000}] 0x8000]
		}
		puts -nonewline $f [debug read_block VRAM 0x1D800 0x2800]
		puts -nonewline $f [debug read_block memory 0xC000 0x1000]
		puts -nonewline $f [debug read_block memory 0x0A00 0x600]
		puts -nonewline $f [debug read_block memory 0xF500 0x400]
		puts -nonewline $f [debug read_block memory 0x0600 0x400]
		puts -nonewline $f [debug read_block memory 0xF240 0x40]
	}
	close $f
	incr ::l2b_fd_k
	if {$::l2b_fd_k >= $::l2b_fd_n} {
		catch {debug probe remove_bp $::l2b_fd_bp}
		set ::l2b_fd_done 1
		set ::pause on
	}
}

# ----- the stills (LOCKSTEP build: the same pictures at the same game frames)

proc l2b_sl_setup {dir rom labels drive frames} {
	file mkdir $dir
	set ::l2b_sl_dir $dir
	set ::l2b_sl_want $frames
	set ::l2b_sl_seq -1
	set ::l2b_sl_done 0
	rc2_drive_rom $rom $labels [file join $dir trace.txt] 1 999999 $drive
	set ::l2b_sl_bp [debug probe set_bp VDP.IRQhorizontal {[debug probe read VDP.IRQhorizontal] == 1} l2b_sl_hit]
}

proc l2b_sl_hit {} {
	if {$::l2b_sl_done || [peek 0xC002] == 0} { return }
	set seq [peek 0xC006]
	if {$seq == $::l2b_sl_seq} { return }
	set ::l2b_sl_seq $seq
	set g [lindex $::l2b_sl_want 0]
	if {[rc2_w 0xD000] < $g} { return }
	rc2_snap [file join $::l2b_sl_dir [format g%04d $g]]
	set f [open [file join $::l2b_sl_dir [format g%04d $g] when.txt] w]
	catch {puts $f "game frame [rc2_w 0xD000] tick_n [rc2_w 0xCEE0] seq $seq time [machine_info time]"}
	close $f
	set ::l2b_sl_want [lrange $::l2b_sl_want 1 end]
	if {[llength $::l2b_sl_want] == 0} {
		catch {debug probe remove_bp $::l2b_sl_bp}
		set ::l2b_sl_done 1
		set ::pause on
	}
}

# ----- the LOCKSTEP records' end: the late frames beside the record

proc l2b_lk_done {over} {
	if {![info exists ::rx_done] || !$::rx_done} { return 0 }
	set f [open $over w]
	catch {puts $f "late $::rx_over at $::rx_late"}
	close $f
	set ::rx_done 0
	return 1
}

# ----- the effects (sess_fxlog.tcl as a job)

proc l2b_fx_setup {out rom labels drive secs} {
	set ::fl_rom $rom
	set ::fl_lab $labels
	set ::fl_out $out
	set ::fl_drive $drive
	set ::fl_secs $secs
	unset -nocomplain ::fl_dev
	uplevel #0 [list source [file join $::hz_root tools bstest sess_fxlog.tcl]]
}

# ----- every PSG write (the effects without an SCC go to the PSG alone)

proc l2b_pw_setup {out rom labels drive secs} {
	set ::l2b_pw_done 0
	set ::l2b_pw_v 0
	set ::l2b_pw_r 0
	set ::l2b_pw_n 0
	rc2_drive_rom $rom $labels [file join [file dirname $out] pw_trace.txt] 1 999999 $drive
	set ::l2b_pw_f [open $out w]
	set ::l2b_pw_wp [debug set_watchpoint write_io {0xA0 0xA1} {} l2b_pw_w]
	set ::l2b_pw_pb [debug probe set_bp VDP.IRQvertical {[debug probe read VDP.IRQvertical] == 1} {incr ::l2b_pw_v}]
	l2b_sn_arm "[file rootname $out]_sn.txt" $rom $labels
	lappend ::hz_afters [after time $secs l2b_pw_end]
}

# The effects by their starts (tools/bstest/fxcmp.py), in the same run: OUT gets "F V" at every
# LOCKSTEP frame's start (wait_frame's wfk_ok), "S V EFFECT CHANNEL" at every effect the VBLANK
# interrupt starts (sndplay.asm sq_sfx; CHANNEL from snd_sfx, the Amiga channel), "G V" at the
# gun's opening (sq_gun: channels 0-2), "X V" where everything stops (sndplay.asm sq_stop, music.asm
# mus_stop: every channel), and "T V PSG VOICES [SCC]" at every sound tick (sq_frame's
# sqf_t, 50 a second: the state before the tick, after the VBLANK's starts): PSG R0-R10, per PSG
# voice its ticks left, noise period and Amiga channel (with an SCC music.asm's fx_pv, else
# sndplay.asm's snd_v), and with an SCC its registers 00h-AFh; "T V" alone repeats the last state.
# V counts VBLANKs (VDP.IRQvertical). The lines stay in memory until the job's end writes the file
# (a job that times out leaves no channel open and no log: its verdict fails).
proc l2b_sn_arm {out rom labels} {
	set ::l2b_sn_out $out
	set ::l2b_sn_buf {}
	set ::l2b_sn_last ""
	set ::l2b_sn_rb "[file tail $rom] romblocks"
	set ::l2b_sn_scc ""
	foreach d [debug list] {
		if {[string match "[file tail $rom] SCC*" $d]} { set ::l2b_sn_scc $d }
	}
	foreach k {BANK_INPUT BANK_MUSIC SND_SFX_N snd_sfx snd_v fx_pv mus_mode} { set ::l2b_sn_$k [rc2_label $labels $k] }
	set c "\[debug read {$::l2b_sn_rb} 0xA000\] == $::l2b_sn_BANK_INPUT"
	set cm "\[debug read {$::l2b_sn_rb} 0xA000\] == $::l2b_sn_BANK_MUSIC"
	set ::l2b_sn_bps [list \
		[debug set_bp [rc2_label $labels wfk_ok] {} {l2b_sn_put "F $::l2b_pw_v"}] \
		[debug set_bp [rc2_label $labels sq_sfx] $c l2b_sn_s] \
		[debug set_bp [rc2_label $labels sq_gun] $c {l2b_sn_put "G $::l2b_pw_v"}] \
		[debug set_bp [rc2_label $labels sq_stop] $c {l2b_sn_put "X $::l2b_pw_v"}] \
		[debug set_bp [rc2_label $labels mus_stop] $cm {l2b_sn_put "X $::l2b_pw_v"}] \
		[debug set_bp [rc2_label $labels sqf_t] $c l2b_sn_t]]
}

proc l2b_sn_put {s} { lappend ::l2b_sn_buf $s }

proc l2b_sn_s {} {
	set a [reg a]
	set ch x
	if {$a >= 1 && $a <= $::l2b_sn_SND_SFX_N} { set ch [peek [expr {$::l2b_sn_snd_sfx + 3 * ($a - 1) + 2}]] }
	lappend ::l2b_sn_buf "S $::l2b_pw_v $a $ch"
}

proc l2b_sn_t {} {
	binary scan [debug read_block {PSG regs} 0 11] H* p
	set v ""
	if {[peek $::l2b_sn_mus_mode] & 1} {
		for {set i 0} {$i < 3} {incr i} {
			set b [expr {$::l2b_sn_fx_pv + 16 * $i}]
			append v [format %02x%02x%02x [peek [expr {$b + 3}]] [peek [expr {$b + 7}]] [peek [expr {$b + 13}]]]
		}
		set s ""
		if {$::l2b_sn_scc ne ""} { binary scan [debug read_block $::l2b_sn_scc 0 0xB0] H* s }
		set x "$p $v $s"
	} else {
		for {set i 0} {$i < 3} {incr i} {
			set b [expr {$::l2b_sn_snd_v + 10 * $i}]
			append v [format %02x%02x%02x [peek [expr {$b + 2}]] [peek [expr {$b + 6}]] [peek [expr {$b + 9}]]]
		}
		set x "$p $v"
	}
	if {$x eq $::l2b_sn_last} {
		lappend ::l2b_sn_buf "T $::l2b_pw_v"
	} else {
		lappend ::l2b_sn_buf "T $::l2b_pw_v $x"
		set ::l2b_sn_last $x
	}
}

proc l2b_sn_end {} {
	foreach b $::l2b_sn_bps { catch {debug remove_bp $b} }
	set ::l2b_sn_bps {}
	lappend ::l2b_sn_buf "# $::l2b_pw_v VBLANKs, time [machine_info time]"
	set f [open $::l2b_sn_out w]
	catch {puts $f [join $::l2b_sn_buf "\n"]}
	close $f
	set ::l2b_sn_buf {}
}

proc l2b_pw_w {} {
	if {$::wp_last_address & 1} {
		puts $::l2b_pw_f "$::l2b_pw_v $::l2b_pw_r $::wp_last_value"
		incr ::l2b_pw_n
	} else {
		set ::l2b_pw_r $::wp_last_value
	}
}

proc l2b_pw_end {} {
	catch {debug remove_watchpoint $::l2b_pw_wp}
	catch {debug probe remove_bp $::l2b_pw_pb}
	l2b_sn_end
	catch {puts $::l2b_pw_f "# $::l2b_pw_n writes, $::l2b_pw_v VBLANKs, time [machine_info time]"}
	close $::l2b_pw_f
	set ::l2b_pw_done 1
	set ::pause on
}

set ::l2b_loaded "l2base.tcl loaded"
