# fixchk.tcl: the review fixes' emulator checks (2026-10-27). Source it after hz.tcl and hz7.tcl
# (or source load.tcl) in the MCP's openMSX; start one hz_chain; poll "list $::hz_state $::hz_msgs"
# with short msx_local_cmd calls. Never vwait. docs/HARNESS.md.
#
#   hzp_setup DIR TAG ROM LABELS ?MODE?
#       the turbo R's PAUSE key (openMSX's setting turborpause = the key's flip-flop) during
#       Brainstorm: a PZ_TEST=1 ROM without a script (the stage left alone, its real timer) from
#       the power-on. At pass 300 PAUSE goes on: if no VBLANK is serviced for an emulated second the
#       CPU is held (openMSX holds the Z80 alone, the VDP goes on, as the S1990 does); else it runs
#       2 emulated seconds with the key on. PAUSE off. MODE "end": PAUSE on again at
#       pass 2900 and left on through the stage's end and the result screen until the game has
#       waited 2 emulated seconds with the pause LED on (cpu_title's cs_pz); PAUSE off; the title;
#       there PAUSE on (the title's hardware pause: the CPU must stop), off.
#       Every write to port A7h is logged (a change of value: its time, value and PC), and the
#       HUD splits and VBLANKs are counted. DIR/TAG_pause.txt; a hold also leaves the snapshot
#       DIR/TAG_held.bin (frozen.py shows it).
#   hzb_setup DIR TAG ROM LABELS
#       an EXTJOY=1 ROM driven to level 1's end (build/emu/drive_end.txt, 517 ticks), then on
#       through front_stats into the bonus' intro, with the times of every HUD split (isr_split),
#       of cpu_set's display off (cs_go), of display_on's entry and of front_bonus' entry, until
#       30 splits after front_bonus' entry: DIR/TAG_blank.txt (fixblank.py). Done: ::hz_done.
#   hzg_job NAME MACHINE ROM LABELS OUT  the display guard over solve1 (step 7's check 3): passes
#       10-633, tear counting on, OUT/flow/NAME.txt; the trace OUT/tr/NAME.txt.
#   hzf_job NAME MACHINE ROM LABELS OUT  VRAM accesses too fast over solve1 (step 7's check 10),
#       the entry's uploads and the exit's restore included: OUT/flow/NAME.txt; the trace
#       OUT/tr/NAME.txt.
#
# Rules kept: no exit, vwait, max or min; files opened once (per write for the notes) and closed on
# every path.

proc hzp_note {m} {
	set f [open "$::hp_dir/${::hp_tag}_pause.txt" a]
	catch {puts $f $m}
	close $f
}

proc hzp_regs {} {
	set s ""
	foreach r {0 1 2 5 8 9 19 23 25} { append s [format " R#%d %02X" $r [debug read {VDP regs} $r]] }
	return $s
}

proc hzp_state {} {
	return [format "t %.4f s, pass %d, front_mode %d, cpu_cur %d, split_armed %d, splits %d, VBLANKs %d, CASPRV %02X, A7h writes %d,%s" \
		[machine_info time] $::hp_pass [peek 0xEC44] [peek 0xC2A7] [peek 0xC002] $::hp_nsplit $::hp_nvbl \
		[peek 0xFCB1] $::hp_na7 [hzp_regs]]
}

proc hzp_setup {dir tag rom labels {mode ""}} {
	file mkdir $dir
	set ::hp_dir $dir
	set ::hp_tag $tag
	set ::hp_mode $mode
	set ::hp_st 0
	set ::hp_pass -1
	set ::hp_nsplit 0
	set ::hp_nvbl 0
	set ::hp_na7 0
	set ::hp_last7 -1
	set ::hp_n01 0
	set ::hp_lt 0
	set ::hp_lv -1
	set ::hz_done 0
	set f [open "$dir/${tag}_pause.txt" w]
	catch {puts $f "# $tag: [file tail $rom] on [machine_info config_name], mode '$mode'"}
	close $f
	set ::turborpause off
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	set a [rc2_label $labels pz_tick]
	set t [rc2_label $labels pz_frame]
	debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t" {set ::hp_pass [rc2_w 0xD000]}
	debug set_bp [rc2_label $labels isr_split] {} {incr ::hp_nsplit}
	debug set_bp [rc2_label $labels isr_vblank] {} {incr ::hp_nvbl}
	debug set_watchpoint write_io 0xA7 {} hzp_a7
	lappend ::hz_afters [after realtime 0.1 hzp_poll]
}

proc hzp_a7 {} {
	incr ::hp_na7
	set v $::wp_last_value
	if {$v == 1} { incr ::hp_n01 }
	if {$v != $::hp_last7} {
		set ::hp_last7 $v
		hzp_note [format "  A7h <- %02X at %.6f s (pc %04X), pass %d, front_mode %d, cpu_cur %d" $v [machine_info time] [reg pc] $::hp_pass [peek 0xEC44] [peek 0xC2A7]]
	}
}

proc hzp_on {why} {
	set ::turborpause on
	set ::hp_lv $::hp_nvbl
	set ::hp_lt [machine_info time]
	set ::hp_t0 [machine_info time]
	set ::hp_r0 [clock milliseconds]
	set ::hp_s0 $::hp_nsplit
	set ::hp_v0 $::hp_nvbl
	set ::hp_p0 $::hp_pass
	hzp_note "PAUSE on ($why): [hzp_state]"
}

# 1 when the CPU has stood still for an emulated second: no VBLANK interrupt serviced while the
# emulated time (the VDP) went on (openMSX holds the Z80 alone, as the S1990 does), else 0
proc hzp_track {} {
	set t [machine_info time]
	if {$::hp_nvbl != $::hp_lv} {
		set ::hp_lv $::hp_nvbl
		set ::hp_lt $t
		return 0
	}
	return [expr {$t - $::hp_lt >= 1.0}]
}

proc hzp_off {why} {
	hzp_note [format "  with PAUSE on: %.4f emulated s, passes %d -> %d, splits +%d, VBLANKs +%d" \
		[expr {[machine_info time] - $::hp_t0}] $::hp_p0 $::hp_pass [expr {$::hp_nsplit - $::hp_s0}] [expr {$::hp_nvbl - $::hp_v0}]]
	set ::turborpause off
	hzp_note "PAUSE off ($why): [hzp_state]"
}

proc hzp_poll {} {
	switch -- $::hp_st {
		0 {
			if {$::hp_pass >= 300} {
				hzp_on "the stage at pass $::hp_pass"
				set ::hp_st 1
			}
		}
		1 {
			if {[hzp_track]} {
				hzp_note "  HELD: no VBLANK serviced for an emulated second: [hzp_state]"
				hz7_snap $::hp_dir ${::hp_tag}_held
				hzp_off "after the hold"
				set ::hp_st 2
				set ::hp_t1 [machine_info time]
			} elseif {[machine_info time] - $::hp_t0 >= 2.0} {
				hzp_note "  RAN 2 emulated seconds: [hzp_state]"
				hzp_off "after 2 emulated seconds"
				set ::hp_st 2
				set ::hp_t1 [machine_info time]
			}
		}
		2 {
			if {$::hp_mode ne "end"} {
				if {[machine_info time] - $::hp_t1 >= 1.0} {
					hzp_note "1 emulated s later: [hzp_state]"
					set ::hp_st 9
				}
			} elseif {$::hp_pass >= 2900} {
				hzp_on "the stage at pass $::hp_pass, kept on through the end"
				set ::hp_n01 0
				set ::hp_st 3
			}
		}
		3 {
			if {[peek 0xEC44] == 1} {
				hzp_note "  FAIL: the title started with PAUSE on: [hzp_state]"
				set ::hp_st 9
			} elseif {$::hp_n01 > 0} {
				set ::hp_tw [machine_info time]
				set ::hp_sw $::hp_nsplit
				set ::hp_vw $::hp_nvbl
				hzp_note "  waiting with the pause LED on (A7h <- 01h): [hzp_state]"
				set ::hp_st 4
			} elseif {[hzp_track]} {
				hzp_note "  HELD before the end: [hzp_state]"
				hzp_off "after the hold"
				set ::hp_st 9
			}
		}
		4 {
			if {[machine_info time] - $::hp_tw >= 2.0} {
				hzp_note [format "  2 emulated s of that wait: splits +%d, VBLANKs +%d, front_mode %d, A7h <- 01h %d times" \
					[expr {$::hp_nsplit - $::hp_sw}] [expr {$::hp_nvbl - $::hp_vw}] [peek 0xEC44] $::hp_n01]
				hzp_off "the end's wait"
				set ::hp_st 5
			} elseif {[hzp_track]} {
				hzp_note "  HELD in the end's wait: [hzp_state]"
				hzp_off "after the hold"
				set ::hp_st 9
			}
		}
		5 {
			if {[peek 0xEC44] == 1} {
				hzp_note "the title: [hzp_state]"
				set ::hp_t2 [machine_info time]
				set ::hp_st 6
			}
		}
		6 {
			if {[machine_info time] - $::hp_t2 >= 1.0} {
				hzp_on "the title"
				set ::hp_st 7
			}
		}
		7 {
			if {[hzp_track]} {
				hzp_note "  HELD on the title (its hardware pause, as before the bonus existed): [hzp_state]"
				hzp_off "the title"
				set ::hp_t1 [machine_info time]
				set ::hp_st 8
			} elseif {[machine_info time] - $::hp_t0 >= 2.0} {
				hzp_note "  RAN on the title with PAUSE on: [hzp_state]"
				hzp_off "the title"
				set ::hp_t1 [machine_info time]
				set ::hp_st 8
			}
		}
		8 {
			if {[machine_info time] - $::hp_t1 >= 1.0} {
				hzp_note "1 emulated s later: [hzp_state]"
				set ::hp_st 9
			}
		}
		9 {
			hz_nowp
			foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
			set ::turborpause off
			set ::hz_done 1
			set ::pause on
			return
		}
	}
	lappend ::hz_afters [after realtime 0.05 hzp_poll]
}

# ----- the HUD's blank at the switch to the Z80 (finding 3: measured, not fixed)

proc hzb_setup {dir tag rom labels} {
	set ::hzb_after -1
	set ::hzb_n 0
	rc2_drive_rom $rom $labels "$dir/${tag}_end_trace.txt" 517 0 "$::hz_root/build/emu/drive_end.txt"
	set ::hzb_f [open "$dir/${tag}_blank.txt" w]
	puts $::hzb_f "# $tag on [machine_info config_name]: S = isr_split, C = cpu_set's cs_go (E = its target), D = display_on, B = front_bonus"
	debug set_bp [rc2_label $labels isr_split] {} {hzb_ev S}
	debug set_bp [rc2_label $labels cs_go] {[peek 0xC07C] == 7} {hzb_ev "C [format %02X [reg e]]"}
	debug set_bp [rc2_label $labels display_on] {} {hzb_ev D}
	debug set_bp [rc2_label $labels front_bonus] {[peek 0xC07C] == 7} {hzb_ev B}
	lappend ::hz_afters [after realtime 0.5 hzb_wait_end]
}

# (the level-1 drive pauses the machine after its last row: resumed, on through front_stats)
proc hzb_wait_end {} {
	if {$::rc2_trace_done} {
		set ::pause off
		return
	}
	lappend ::hz_afters [after realtime 0.5 hzb_wait_end]
}

proc hzb_ev {what} {
	if {![info exists ::hzb_f]} return
	puts $::hzb_f [format "%.6f %s" [machine_info time] $what]
	incr ::hzb_n
	if {$what eq "B"} { set ::hzb_after 0 }
	if {$what eq "S" && $::hzb_after >= 0} { incr ::hzb_after }
	if {$::hzb_after >= 30 || $::hzb_n > 20000} {
		hzb_close
		set ::hz_done 1
		set ::pause on
	}
}

proc hzb_close {} {
	if {[info exists ::hzb_f]} { catch {close $::hzb_f}; unset ::hzb_f }
}

# ----- step 7's guard and VRAM speed checks as hz_chain jobs

proc hzg_job {name m rom labels out} {
	set setup "rc2_pz_drive {$rom} {$labels} {$out/tr/$name.txt} 3000 0 {$::hz_root/build/emu/pz_solve1.drive}; hz7_guard_arm {$labels} 10 13 262 {$out/flow/$name.txt}"
	return [list $name $m [list eval $setup] {$::rc2_trace_done} 600]
}

proc hzf_job {name m rom labels out} {
	set setup "set ::too_fast_vram_access real; rc2_count_too_fast; rc2_pz_drive {$rom} {$labels} {$out/tr/$name.txt} 3000 0 {$::hz_root/build/emu/pz_solve1.drive}; set ::hzf_file {$out/flow/$name.txt}"
	return [list $name $m [list eval $setup] {[hzf_done]} 300]
}

# (the done condition: evaluated every second until it holds, so the file is written once, when the
# drive has ended)
proc hzf_done {} {
	if {!$::rc2_trace_done} { return 0 }
	set f [open $::hzf_file w]
	catch {puts $f "too fast VRAM accesses: $::rc2_too_fast at $::rc2_too_fast_pc (setting [set ::too_fast_vram_access]); result $::rc2_pz_result, passes [rc2_w 0xD000]"}
	close $f
	set {::VDP.too_fast_vram_access_callback} {}
	return 1
}
