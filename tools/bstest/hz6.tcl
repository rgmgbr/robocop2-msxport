# hz6.tcl: step 6's flow checks (source it after hz.tcl, or source load.tcl, in the MCP's openMSX;
# poll "list $::hz_state $::hz_msgs"; never vwait; docs/HARNESS.md).
#
#   hz6_arm DIR TAG ROM LABELS ?MACHINE?
#       an EXTJOY=1 build (no PZ_TEST): level 1 driven by build/emu/drive_end.txt (200 rows), then
#       tools/openmsx_rc2.tcl rc2_pz_arm with build/emu/pz_fail.drive (the game runs on through
#       the level's end, front_stats and the intro into the stage): DIR/TAG_pz.txt, the stage's
#       trace; then the result screen and the new game (hz.tcl hb_step: DIR/TAG_bonus.txt,
#       TAG_intro.sc5, TAG_result.sc5 for bonuscheck.py --result fail).
#   hz6_prod DIR TAG ROM LABELS ?MACHINE?
#       the product ROM on a new machine, its whole flow (below).
#   hz6_time DIR TAG ROM LABELS ?MACHINE?
#       a PZ_TEST=1 build without a script (the timer counts real seconds): the emulated time and
#       the passes ($B00) at the stage's first pass, when $804C goes to FFh (board 0's time out)
#       and at pz_done: DIR/TAG_time.txt.
#   (each NAME also has NAME_setup DIR TAG ROM LABELS: the job's setup, for hz_chain job lists)
#
# The project's rules: no exit, vwait, max or min; files opened once per write and closed on every
# path.

proc hz6_arm {dir tag rom labels {m C-BIOS_MSX2}} {
	file mkdir $dir
	hz_chain [list [list "arm $tag" $m [list hz6_arm_setup $dir $tag $rom $labels] {$::hz_done} 900]]
}

proc hz6_arm_setup {dir tag rom labels} {
	set ::hb_dir $dir
	set ::hb_tag $tag
	set ::h6_labels $labels
	foreach n {txt_bs_intro txt_bs_ok txt_bs_fail txt_bs_time isr_split isr_vblank INPUT_SCRIPT} {
		set ::hb_$n [rc2_label $labels $n]
	}
	set ::hb_st 0
	set ::hz_done 0
	set f [open "$dir/${tag}_bonus.txt" w]
	close $f
	rc2_drive_rom $rom $labels "$dir/${tag}_end_l1.txt" 200 0 "$::hz_root/build/emu/drive_end.txt"
	lappend ::hz_afters [after realtime 0.5 hz6_w1]
}

# (the level-1 drive paused after its 200 rows: the stage's trace armed, the machine resumed)
proc hz6_w1 {} {
	if {$::rc2_trace_done} {
		hb_note "level-1 drive (200 rows) done at [machine_info time] s, tick_n [rc2_w 0xCEE0]"
		rc2_pz_arm $::h6_labels "$::hb_dir/${::hb_tag}_pz.txt" 3000 0 "$::hz_root/build/emu/pz_fail.drive"
		lappend ::hz_afters [after time 0.05 hb_step]
		lappend ::hz_afters [after realtime 0.5 hz6_w2]
		return
	}
	lappend ::hz_afters [after realtime 0.5 hz6_w1]
}

# (the stage's end paused the machine at pz_done: noted, resumed; hb_step goes on)
proc hz6_w2 {} {
	if {$::rc2_trace_done} {
		hb_note "stage done at [machine_info time] s: result $::rc2_pz_result, passes [rc2_w 0xD000], AG 8050h [rc2_w 0xDC50], 805Eh [rc2_w 0xDC5E], tick_n [rc2_w 0xCEE0]"
		set ::pause off
		return
	}
	lappend ::hz_afters [after realtime 0.5 hz6_w2]
}

# hz6_prod DIR TAG ROM LABELS ?MACHINE?
#     the product ROM on a new machine: the title, fire; level 1 to its end by build/emu/
#     drive_end.txt's teleport and poke (rc2_drive_trace: its joystick bytes go to ext_joy, which a
#     product build never reads; 200 rows); then hb_step: the intro, the stage left alone (its
#     real timer: out of time), the result, the title, fire, the new game.
proc hz6_prod {dir tag rom labels {m Gradiente_Expert20_64K}} {
	file mkdir $dir
	hz_chain [list [list "prod $tag" $m [list hz6_prod_setup $dir $tag $rom $labels] {$::hz_done} 900]]
}

proc hz6_prod_setup {dir tag rom labels} {
	set ::hb_dir $dir
	set ::hb_tag $tag
	set ::h6_labels $labels
	foreach n {txt_bs_intro txt_bs_ok txt_bs_fail txt_bs_time isr_split isr_vblank INPUT_SCRIPT} {
		set ::hb_$n [rc2_label $labels $n]
	}
	set ::hb_st 0
	set ::hz_done 0
	set ::h6_ps 0
	set f [open "$dir/${tag}_bonus.txt" w]
	close $f
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	lappend ::hz_afters [after time 0.2 hz6_p_step]
}

proc hz6_p_step {} {
	switch -- $::h6_ps {
		0 {
			if {[peek 0xEC44] == 1} {
				hb_note "first title at [machine_info time] s"
				set ::h6_ps 1
				lappend ::hz_afters [after time 1.5 hz6_p_step]
				return
			}
		}
		1 {
			keymatrixdown 8 1
			lappend ::hz_afters [after time 0.3 {keymatrixup 8 1}]
			set ::h6_ps 2
		}
		2 {
			if {[peek 0xEC44] == 0} {
				rc2_drive_trace "$::hb_dir/${::hb_tag}_l1.txt" 200 [rc2_label $::h6_labels tick_start] [rc2_label $::h6_labels game_tick] 0 "$::hz_root/build/emu/drive_end.txt"
				hb_note "the game at [machine_info time] s, tick_n [rc2_w 0xCEE0]"
				set ::h6_ps 3
				lappend ::hz_afters [after realtime 0.5 hz6_p_w]
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.1 hz6_p_step]
}

proc hz6_p_w {} {
	if {$::rc2_trace_done} {
		hb_note "level-1 drive (200 rows) done at [machine_info time] s, tick_n [rc2_w 0xCEE0], lives [peek 0xDC34]"
		set ::pause off
		lappend ::hz_afters [after time 0.05 hb_step]
		return
	}
	lappend ::hz_afters [after realtime 0.5 hz6_p_w]
}

proc hz6_time {dir tag rom labels {m Gradiente_Expert20_64K}} {
	file mkdir $dir
	hz_chain [list [list "time $tag" $m [list hz6_time_setup $dir $tag $rom $labels] {$::hz_done} 900]]
}

proc hz6_time_setup {dir tag rom labels} {
	set ::h6_file "$dir/${tag}_time.txt"
	set f [open $::h6_file w]
	catch {puts $f "# $tag: [machine_info config_name], RG9SAV [format %02X [peek 0xFFE8]] at the set-up"}
	close $f
	set ::h6_tick [rc2_label $labels pz_tick]
	set ::h6_frame [rc2_label $labels pz_frame]
	set ::h6_done [rc2_label $labels pz_done]
	set ::h6_st 0
	set ::hz_done 0
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	set cond "\[peek $::h6_tick\] == 0xCD && \[rc2_w [expr {$::h6_tick + 1}]\] == $::h6_frame"
	set ::h6_bp [debug set_bp $::h6_tick $cond hz6_t_tick]
	lappend ::hz_afters [after time 0.05 hz6_t_poll]
}

proc hz6_t_note {m} {
	set f [open $::h6_file a]
	catch {puts $f $m}
	close $f
}

# (the first pass: its time; then pz_done's breakpoint)
proc hz6_t_tick {} {
	if {$::h6_st != 0} return
	set ::h6_st 1
	set ::h6_t0 [machine_info time]
	hz6_t_note "first pass at [format %.3f $::h6_t0] s: passes [rc2_w 0xD000], timer [format %02X:%02X [peek 0xDC4B] [peek 0xDC4A]], RG9SAV [format %02X [peek 0xFFE8]], R#9 [format %02X [debug read {VDP regs} 9]]"
	catch {debug remove_bp $::h6_bp}
	set ::h6_bp [debug set_bp $::h6_done {} hz6_t_done]
}

proc hz6_t_poll {} {
	if {$::h6_st == 1 && [peek 0xDC4D] == 0xFF} {
		set t [machine_info time]
		hz6_t_note "time out at [format %.3f $t] s: [format %.3f [expr {$t - $::h6_t0}]] s after the first pass, passes [rc2_w 0xD000], timer [format %02X:%02X [peek 0xDC4B] [peek 0xDC4A]]"
		set ::h6_st 2
	}
	if {$::h6_st < 3} { lappend ::hz_afters [after time 0.02 hz6_t_poll] }
}

proc hz6_t_done {} {
	if {$::h6_st != 2} return
	set ::h6_st 3
	set t [machine_info time]
	hz6_t_note "pz_done at [format %.3f $t] s: result [reg a], passes [rc2_w 0xD000], [format %.3f [expr {$t - $::h6_t0}]] s after the first pass"
	catch {debug remove_bp $::h6_bp}
	set ::hz_done 1
	set ::pause on
}
