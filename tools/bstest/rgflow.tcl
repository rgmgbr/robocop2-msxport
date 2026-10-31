# rgflow.tcl: the shooting range's flow checks (docs/HARNESS.md 5.19), for the MSX-AI MCP's openMSX
# (msx_local_cmd, headless). load.tcl sources it after hz.tcl and the others; start one hz_chain; poll
# "list $::hz_state [llength $::hz_msgs] [lindex $::hz_msgs end]". Never vwait.
#
# Jobs (hz_chain's {name machine setup done timeout}); each records into DIR with the tag NAME:
#   rgx_job NAME MACHINE DIR ROM LABELS DRIVE ?L1?
#       an EXTJOY=1 PZ_TEST=2 build from the power-on: tools/openmsx_rc2.tcl rc2_fr_drive with
#       DRIVE (tools/drivejoy.py's four lines: its pokes at FRNG frames, e.g. the counts and the ammo
#       at pass 5, or $804C = FFh), then the range's screens, the new game. With L1 = "FILE ROWS"
#       (build/emu/drive_cov1.txt 4401): level 1 traced after the new game (the drive's frames
#       moved by tick_n there) into DIR/NAME_l1.txt.
#   rgx_arm_job NAME MACHINE DIR ROM LABELS DRIVE
#       an EXTJOY=1 build (the product's flow): level 1 ended by build/emu/drive_end.txt, Brainstorm
#       by build/emu/pz_fail.drive (hz6.tcl hz6_arm_setup: its screens' records), then the range as
#       above; since level 2's step 18 the level-2 briefing and level 2 follow (rgx_l2: lv_next, then
#       level 2's game frame 100 with the range's rating) instead of a new game.
#   rgx_tarm_job NAME MACHINE DIR ROM LABELS DRIVE
#       docs/RANGE.md 4.1 "after a played level 1 and Brainstorm": an EXTJOY=1 build, level 1 by
#       rc2_drive_rom with drive_end (200 rows, DIR/NAME_l1.txt), Brainstorm by rc2_pz_arm with
#       pz_fail (DIR/NAME_pz.txt), then the range traced by rc2_fr_arm with build/emu/fr_DRIVE.drive
#       (DIR/NAME.txt): tools/frngcmp.py --skip score. Done when the range's trace is.
#   rgx_want_job NAME MACHINE DIR ROM LABELS DRIVE
#       rc2_fr_drive with fr_DRIVE (the trace DIR/NAME.txt) and, at every fr_tick, rg_want's 48
#       bytes and rg_blost (DIR/NAME_want.txt: "pass hex lost"): rgview.py want.
#   rgk_job NAME MACHINE DIR ROM LABELS ?FDRIVE? ?PDRIVE?
#       the product from the power-on, from the keyboard (keymatrix row 8, never ext_joy): the title,
#       fire, a new game, level 1 ended by drive_end.txt's teleport and poke (its joystick bytes go
#       to ext_joy, which the product never reads), the statistics, Brainstorm played from the keyboard
#       with pz_PDRIVE's moves (default solve1; rc2_pz_arm's trace DIR/NAME_pz.txt, hb_step's records
#       of its screens), the range played from the keyboard with fr_FDRIVE's moves (default armed: 25
#       shots; rc2_fr_arm's trace DIR/NAME_fr.txt, the screens' records below), its result, the title
#       (np.tcl np_hf_step's exact record: DIR/NAME_title_*, _music2.txt, _game2_*: titlecmp.py and
#       titlecmp2.py against the base's title) and the game the title starts at its tick 300. Since
#       level 2's step 18: the level-2 briefing and level 2's game frame 100 instead of the title
#       (hz.tcl hb_brief_arm, hb_l2_100; the title after the range comes only in a PZ_TEST build).
#
# The range inside Brainstorm's flows (hz.tcl hb_step, np.tcl, hz6.tcl, c8.tcl, run8f.tcl): rgh_arm.
# After Brainstorm's result, a build with the range records the range's screens into the flow's own
# DIR/TAG (rgintro, rgres, TAG_rg.txt with the result at fr_done, the rating at fr_rated and the new
# game's ac_diff): bonuscheck.py --range. A build with a script (INPUT_SCRIPT: EXTJOY or JOY) has no
# time out, so rgh_arm arms rc2_fr_timeout (OUT OF TIME. at the range's first pass); the others play
# the range's real 2:00 to OUT OF TIME. A job that drives the range itself sets ::hb_range 0 after
# its set-up (rgx_arm_setup, rgk_setup).
#
# Records (DIR/NAME_...): rgintro.sc5 (page 0's lines 0-161 once the range's intro is complete:
# fs_n 150), rgres.sc5 (the result's, fs_n 120, or OUT OF TIME.'s, fs_n 100), each taken at the next
# iv_late, with _regs.bin, _pal.bin, _hud.bin, _ram.bin (C000h-FFFFh); NAME_rg.txt: the notes (the
# result at fr_done, the rating at fr_rated, ac_diff, the VBLANKs and HUD splits between the two
# records, display_on's calls from the range's set-up, the new game). Check with rgcheck.py.
#
# Rules kept (the project's notes): no exit, vwait, max or min; every file opened once per write
# and closed on every path; breakpoints at banked code carry a byte condition.

proc rgx_job {name m dir rom labels drive {l1 ""}} {
	file mkdir $dir
	return [list $name $m [list rgx_pz2_setup $dir $name $rom $labels $drive $l1] {$::hz_done} 900]
}

proc rgx_arm_job {name m dir rom labels drive} {
	file mkdir $dir
	return [list $name $m [list rgx_arm_setup $dir $name $rom $labels $drive] {$::hz_done} 900]
}

proc rgx_init {dir tag labels drive l1} {
	set ::rgx_dir $dir
	set ::rgx_tag $tag
	set ::rgx_labels $labels
	set ::rgx_drive $drive
	set ::rgx_l1 $l1
	set ::rgx_hb 0
	foreach n {txt_rg_intro txt_rg_res txt_bs_time isr_split isr_vblank fs_buf new_game display_on tick_start game_tick ac_diff diff_tab iv_late fr_done fr_rated} {
		set ::rgx_$n [rc2_label $labels $n]
	}
	set ::rgx_st 0
	set ::rgx_dn 0
	set ::rgx_l2n 0
	set ::rgx_bps {}
	set ::hz_done 0
	set f [open "$dir/${tag}_rg.txt" w]
	catch {puts $f "# $tag: [file tail [file dirname $labels]]/[file tail $labels] on [machine_info config_name]; drive [file tail $drive]"}
	close $f
}

proc rgx_note {m} {
	set f [open "$::rgx_dir/${::rgx_tag}_rg.txt" a]
	catch {puts $f $m}
	close $f
}

proc rgx_file {name data} {
	set f [open "$::rgx_dir/${::rgx_tag}_$name" w]
	catch {
		fconfigure $f -translation binary
		puts -nonewline $f $data
	}
	close $f
}

proc rgx_snap {name} {
	rgx_file $name.sc5 [debug read_block "physical VRAM" 0 [expr {162 * 128}]]
	rgx_file ${name}_regs.bin [debug read_block "VDP regs" 0 [debug size "VDP regs"]]
	rgx_file ${name}_pal.bin [debug read_block "VDP palette" 0 [debug size "VDP palette"]]
	rgx_file ${name}_hud.bin [debug read_block "physical VRAM" 0x1E800 [expr {45 * 128}]]
	rgx_file ${name}_ram.bin [debug read_block memory 0xC000 0x4000]
}

proc rgx_regs {} {
	return "R#0 [format %02X [debug read {VDP regs} 0]] R#1 [format %02X [debug read {VDP regs} 1]]"
}

proc rgx_lost {} {
	return "lost: mp [peek 0x1084] atr [peek 0x1082] rd [peek 0x1088] fb [peek 0x069C]"
}

proc rgx_rating {} {
	return [expr {([rc2_w $::rgx_ac_diff] - $::rgx_diff_tab) & 0xFFFF}]
}

# The PZ_TEST=2 job: a fresh start through rc2_fr_drive (every breakpoint removed, a reset), then
# display_on's calls noted (the range's fb_prep on a turbo R) and the pollers.
proc rgx_pz2_setup {dir tag rom labels drive l1} {
	rgx_init $dir $tag $labels $drive $l1
	rc2_fr_drive $rom $labels "$dir/${tag}_fr.txt" 1 100000 $drive
	rgx_arm_extra
	lappend ::hz_afters [after time 0.05 rgx_step]
	lappend ::hz_afters [after realtime 0.5 rgx_rt]
}

# The product's flow in an EXTJOY=1 build: hz6_arm_setup (level 1, the statistics, Brainstorm by
# pz_fail with hb_step's records); once Brainstorm's result is recorded (hb_step past its state 6,
# which removes every breakpoint), hb_step stops and the range's trace and pollers start.
proc rgx_arm_setup {dir tag rom labels drive} {
	hz6_arm_setup $dir $tag $rom $labels
	set ::hb_range 0
	rgx_init $dir $tag $labels $drive ""
	lappend ::hz_afters [after time 0.1 rgx_wait_bs]
}

proc rgx_wait_bs {} {
	if {$::hb_st == 4 || $::hb_st == 2} {
		set ::hb_st 99
		rgx_note "Brainstorm's result recorded at [machine_info time] s: the range's trace armed"
		rc2_fr_arm $::rgx_labels "$::rgx_dir/${::rgx_tag}_fr.txt" 1 100000 $::rgx_drive
		rgx_arm_extra
		lappend ::hz_afters [after time 0.05 rgx_step]
		lappend ::hz_afters [after realtime 0.5 rgx_rt]
		return
	}
	lappend ::hz_afters [after time 0.1 rgx_wait_bs]
}

# display_on's calls (fb_prep on a turbo R: the split measured on the Z80) until the range's first
# pass, at most 8 noted
proc rgx_arm_extra {} {
	set ::rgx_don 0
	lappend ::rgx_bps [debug set_bp $::rgx_display_on {} rgx_don_hit]
}

proc rgx_don_hit {} {
	incr ::rgx_don
	if {$::rgx_don <= 8} {
		rgx_note [format "display_on at %.6f s, cpu_tr %d, fs_ptr %04X" [machine_info time] [peek 0xC2A6] [rc2_w 0xCFB8]]
	}
}

proc rgx_split {} { incr ::rgx_nsplit }
proc rgx_vbl {} { incr ::rgx_nvbl }

# the range's text screens, by fs_ptr: intro, res (fs_buf), time (txt_bs_time) or "-"
proc rgx_script {} {
	set p [rc2_w 0xCFB8]
	if {$p >= $::rgx_txt_rg_intro && $p < $::rgx_txt_rg_res} { return intro }
	if {$p >= $::rgx_fs_buf && $p < $::rgx_fs_buf + 120} { return res }
	if {$p >= $::rgx_txt_bs_time && $p < $::rgx_txt_rg_intro} { return time }
	return "-"
}

# A screen's record is taken at the next iv_late, once the VBLANK has applied the list: R#0, R#1 and
# the rest are then the list's, wherever the poll found the beam (an 'after time' poll inside the
# HUD split's 5 blank lines read R#1 = R1_BLANK, 22h, there).
proc rgx_late {script} {
	set ::rgx_late_script $script
	set ::rgx_late_bp [debug set_bp $::rgx_iv_late {} rgx_late_hit]
}

proc rgx_late_hit {} {
	catch {debug remove_bp $::rgx_late_bp}
	uplevel #0 $::rgx_late_script
	lappend ::hz_afters [after time 0.05 rgx_step]
}

proc rgx_step {} {
	set n [rc2_w 0xCFBE]
	switch -- $::rgx_st {
		0 {
			if {[rgx_script] eq "intro" && $n >= 150} {
				set ::rgx_st 10
				rgx_late rgx_intro_rec
				return
			}
		}
		1 {
			set sc [rgx_script]
			if {($sc eq "res" && $n >= 120) || ($sc eq "time" && $n >= 100)} {
				set ::rgx_st 11
				rgx_late rgx_res_rec
				return
			}
		}
		2 {
			return
		}
		10 - 11 {
			return
		}
	}
	lappend ::hz_afters [after time 0.05 rgx_step]
}

proc rgx_intro_rec {} {
	set n [rc2_w 0xCFBE]
	rgx_snap rgintro
	rgx_note "intro at [machine_info time] s, fs_n $n, [rgx_regs], AG 8050h [rc2_w 0xDC50], tick_n [rc2_w 0xCEE0]"
	set ::rgx_nsplit 0
	set ::rgx_nvbl 0
	lappend ::rgx_bps [debug set_bp $::rgx_isr_split {} rgx_split]
	lappend ::rgx_bps [debug set_bp $::rgx_isr_vblank {} rgx_vbl]
	set ::rgx_st 1
}

proc rgx_res_rec {} {
	set n [rc2_w 0xCFBE]
	set sc [rgx_script]
	rgx_snap rgres
	foreach b $::rgx_bps { catch {debug remove_bp $b} }
	set ::rgx_bps {}
	rgx_note "result $sc at [machine_info time] s, fs_n $n, [rgx_regs], ac_diff - diff_tab [rgx_rating], passes [rc2_w 0xD000], correct [rc2_w 0xD004], dummy [rc2_w 0xD006], timer [format %04X [rc2_w 0xDC4A]], 804Ch [format %02X [peek 0xDC4D]], ammo [format %04X [rc2_w 0xDC30]], weapon [rc2_w 0xDC5C], msg_wr [peek 0xC623]"
	rgx_note "between the records: $::rgx_nvbl VBLANKs, $::rgx_nsplit HUD splits; display_on calls $::rgx_don"
	if {$::rgx_hb} {
		# (a Brainstorm flow or the keyboard flow: its own steps go on to the title or the new game)
		set ::rgx_st 2
		return
	}
	set a $::rgx_new_game
	set ::rgx_ngbp [debug set_bp $a "\[peek $a\] == [peek $a]" rgx_ng]
	# (the product's flow, level 2's step 18: the level-2 briefing, then lv_next instead of a new game)
	if {![catch {rc2_label $::rgx_labels lv_next} ln]} {
		set ds [rc2_label $::rgx_labels dsp_off]
		set ::rgx_l2bp [debug set_bp $ln "\[peek $ln\] == 0xCD && \[rc2_w [expr {$ln + 1}]\] == $ds" rgx_l2]
	}
	set ::rgx_st 2
}

# the next level after the range (the product's flow): ac_diff noted (the range's rating, kept), then
# level 2's game frame 100 (rgx_g100_hit, lv_cur's logic bank level 2's), the lost counters
proc rgx_l2 {} {
	catch {debug remove_bp $::rgx_l2bp}
	catch {debug remove_bp $::rgx_ngbp}
	rgx_note "level 2 at lv_next at [machine_info time] s, tick_n [rc2_w 0xCEE0], AG 8050h [rc2_w 0xDC50], ac_diff - diff_tab [rgx_rating]"
	set ::rgx_l2n 1
	set a $::rgx_tick_start
	set t $::rgx_game_tick
	set b [rc2_label $::rgx_labels BANK_L2]
	set ::rgx_g100 [debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t && \[peek 0xF1A0\] == $b && \[rc2_w 0xD000\] >= 100" rgx_g100_hit]
}

# rc2_fr_arm's end: fr_rated paused the emulation (the rating noted in the trace's file): noted
# here, resumed
proc rgx_rt {} {
	if {$::rc2_trace_done && !$::rgx_dn} {
		set ::rgx_dn 1
		rgx_note "stage: result $::rc2_fr_result (dummy correct 804Ch at fr_done), rating $::rc2_fr_rating at fr_rated ([machine_info time] s, passes [rc2_w 0xD000])"
		set ::pause off
		return
	}
	lappend ::hz_afters [after realtime 0.5 rgx_rt]
}

# the new game (EXTJOY builds: no title): its game frame 100, or level 1's trace
proc rgx_ng {} {
	catch {debug remove_bp $::rgx_ngbp}
	if {[info exists ::rgx_l2bp]} { catch {debug remove_bp $::rgx_l2bp} }
	set k [rc2_w 0xCEE0]
	rgx_note "new game at [machine_info time] s, tick_n $k, ac_diff - diff_tab [rgx_rating]"
	if {$::rgx_l1 ne ""} {
		lassign $::rgx_l1 src rows
		np_shift_drive $src "$::rgx_dir/${::rgx_tag}_l1drive.txt" $k
		rc2_drive_trace "$::rgx_dir/${::rgx_tag}_l1.txt" $rows $::rgx_tick_start $::rgx_game_tick $k "$::rgx_dir/${::rgx_tag}_l1drive.txt"
		lappend ::hz_afters [after realtime 0.5 rgx_l1_wait]
		return
	}
	set a $::rgx_tick_start
	set t $::rgx_game_tick
	set ::rgx_g100 [debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t && \[rc2_w 0xD000\] >= 100" rgx_g100_hit]
}

proc rgx_g100_hit {} {
	catch {debug remove_bp $::rgx_g100}
	rgx_file game_vram.bin [debug read_block "physical VRAM" 0 0x20000]
	set what [expr {$::rgx_l2n ? "level 2 at tick_n" : "game tick_n"}]
	rgx_note "$what [rc2_w 0xCEE0] at [machine_info time] s, g_frame [rc2_w 0xD000], lives [peek 0xDC34], ac_diff - diff_tab [rgx_rating]; [rgx_lost]"
	set ::rgx_st 3
	set ::hz_done 1
	set ::pause on
}

proc rgx_l1_wait {} {
	if {$::rc2_trace_done} {
		rgx_note "level-1 trace done at [machine_info time] s, tick_n [rc2_w 0xCEE0], g_frame [rc2_w 0xD000], ac_diff - diff_tab [rgx_rating]; [rgx_lost]"
		rgx_note "game tick_n [rc2_w 0xCEE0] (the trace's end)"
		set ::rgx_st 3
		set ::hz_done 1
		return
	}
	lappend ::hz_afters [after realtime 0.5 rgx_l1_wait]
}

# ----- the range inside Brainstorm's flows (hz.tcl hb_step state 6 calls rgh_arm; state 7 waits for
# the range's result record; state 4 calls rgh_game)

# 1 when the range's records are armed (the build has the range and the job wants them), else 0
proc rgh_arm {} {
	if {![info exists ::hb_range] || !$::hb_range || ![info exists ::hb_labels]} { return 0 }
	if {[catch {rc2_label $::hb_labels fr_tick}]} { return 0 }
	set ::rgh_next $::hb_st
	rgx_init $::hb_dir $::hb_tag $::hb_labels none ""
	set ::rgx_hb 1
	set ::rgh_res {}
	set ::rgh_rated 0
	set ::rgh_on 1
	set d $::rgx_fr_done
	set r $::rgx_fr_rated
	lappend ::rgx_bps [debug set_bp $d "\[peek $d\] == [peek $d]" rgh_done]
	lappend ::rgx_bps [debug set_bp $r "\[peek $r\] == [peek $r]" rgh_rate]
	if {$::hb_INPUT_SCRIPT} {
		rc2_fr_timeout $::hb_labels
		rgx_note "a script build: rc2_fr_timeout armed at [machine_info time] s (the range's first pass times out)"
	} else {
		rgx_note "no script: the range plays its real 2:00 (armed at [machine_info time] s)"
	}
	rgx_arm_extra
	lappend ::hz_afters [after time 0.05 rgx_step]
	return 1
}

proc rgh_done {} {
	if {[llength $::rgh_res]} return
	set ::rgh_res [list [rc2_w 0xD006] [rc2_w 0xD004] [peek [expr {0xDC4C ^ 1}]]]
}

proc rgh_rate {} {
	if {$::rgh_rated || ![llength $::rgh_res]} return
	set ::rgh_rated 1
	rgx_note "stage: result $::rgh_res (dummy correct 804Ch at fr_done), rating [rgx_rating] at fr_rated ([machine_info time] s, passes [rc2_w 0xD000])"
}

# hb_step's new game (its state 4): the range's notes get the game and ac_diff (SHARP again)
proc rgh_game {} {
	set ::rgh_on 0
	rgx_note "game tick_n [rc2_w 0xCEE0] at [machine_info time] s, g_frame [rc2_w 0xD000], lives [peek 0xDC34], ac_diff - diff_tab [rgx_rating]; [rgx_lost]"
}

# rc2_fr_timeout when the build has the range (a script build's flow that does not record it)
proc rgx_timeout_if {labels} {
	if {![catch {rc2_label $labels fr_tick}]} { rc2_fr_timeout $labels }
}

# ----- docs/RANGE.md 4.1: the range traced after a played level 1 and Brainstorm

proc rgx_tarm_job {name m dir rom labels drive} {
	file mkdir $dir
	return [list $name $m [list rgx_tarm_setup $dir $name $rom $labels $drive] {$::rgt_st == 2 && $::rc2_trace_done} 900]
}

proc rgx_tarm_setup {dir name rom labels drive} {
	set ::rgt_dir $dir
	set ::rgt_name $name
	set ::rgt_labels $labels
	set ::rgt_drive "$::hz_root/build/emu/fr_$drive.drive"
	set ::rgt_st 0
	rc2_drive_rom $rom $labels "$dir/${name}_l1.txt" 200 0 "$::hz_root/build/emu/drive_end.txt"
	lappend ::hz_afters [after realtime 0.5 rgx_tarm_poll]
}

proc rgx_tarm_poll {} {
	if {$::rc2_trace_done} {
		if {$::rgt_st == 0} {
			rc2_pz_arm $::rgt_labels "$::rgt_dir/${::rgt_name}_pz.txt" 3000 0 "$::hz_root/build/emu/pz_fail.drive"
			set ::rgt_st 1
		} elseif {$::rgt_st == 1} {
			rc2_fr_arm $::rgt_labels "$::rgt_dir/${::rgt_name}.txt" 3000 0 $::rgt_drive
			set ::rgt_st 2
			return
		}
	}
	lappend ::hz_afters [after realtime 0.5 rgx_tarm_poll]
}

# ----- the wanted state at every pass's start (what the previous pass drew): rgview.py want

proc rgx_want_job {name m dir rom labels drive} {
	file mkdir $dir
	return [list $name $m [list rgx_want_setup $dir $name $rom $labels $drive] {$::rgw_done} 900]
}

proc rgx_want_setup {dir name rom labels drive} {
	set ::rgw_done 0
	set ::rgw_want [rc2_label $labels rg_want]
	set ::rgw_lost [rc2_label $labels rg_blost]
	set a [rc2_label $labels fr_tick]
	set t [rc2_label $labels fr_frame]
	rc2_fr_drive $rom $labels "$dir/${name}.txt" 3000 0 "$::hz_root/build/emu/fr_$drive.drive"
	set ::rgw_f [open "$dir/${name}_want.txt" w]
	set ::rgw_bp [debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t" rgx_want_hit]
	lappend ::hz_afters [after realtime 0.5 rgx_want_poll]
}

proc rgx_want_hit {} {
	if {![info exists ::rgw_f]} return
	binary scan [debug read_block memory $::rgw_want 48] H* w
	catch {puts $::rgw_f "[rc2_w 0xD000] $w [peek $::rgw_lost]"}
}

proc rgx_want_poll {} {
	if {$::rc2_trace_done} {
		catch {debug remove_bp $::rgw_bp}
		if {[info exists ::rgw_f]} { catch {close $::rgw_f}; unset ::rgw_f }
		set ::rgw_done 1
		return
	}
	lappend ::hz_afters [after realtime 0.5 rgx_want_poll]
}

# ----- the product from the keyboard: the title, level 1, the statistics, Brainstorm and the range
# played from keymatrix row 8, the result, the title

proc rgk_job {name m dir rom labels {fdrive armed} {pdrive solve1}} {
	file mkdir $dir
	return [list $name $m [list rgk_setup $dir $name $rom $labels $fdrive $pdrive] {[rgk_done]} 1500]
}

proc rgk_setup {dir tag rom labels fdrive pdrive} {
	set ::hb_dir $dir
	set ::hb_tag $tag
	set ::h6_labels $labels
	foreach n {txt_bs_intro txt_bs_ok txt_bs_fail txt_bs_time isr_split isr_vblank INPUT_SCRIPT} {
		set ::hb_$n [rc2_label $labels $n]
	}
	hb_init_range $labels
	set ::hb_range 0
	set ::hb_st 99
	set ::hz_done 0
	set ::rgk_st 0
	set ::rgk_end 0
	set ::rgk_fdrive "$::hz_root/build/emu/fr_$fdrive.drive"
	set ::rgk_pdrive "$::hz_root/build/emu/pz_$pdrive.drive"
	set ::nt_rom $rom
	set ::nt_labels $labels
	set ::nt_exact 1
	set f [open "$dir/${tag}_bonus.txt" w]
	catch {puts $f "# $tag: [file tail $rom] on [machine_info config_name], from the keyboard: Brainstorm [file tail $::rgk_pdrive], the range [file tail $::rgk_fdrive]"}
	close $f
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	lappend ::hz_afters [after time 0.2 rgk_step]
}

proc rgk_step {} {
	switch -- $::rgk_st {
		0 {
			if {[peek 0xEC44] == 1} {
				hb_note "first title at [machine_info time] s"
				set ::rgk_st 1
				lappend ::hz_afters [after time 1.5 rgk_step]
				return
			}
		}
		1 {
			keymatrixdown 8 1
			lappend ::hz_afters [after time 0.3 {keymatrixup 8 1}]
			hb_note "fire at [machine_info time] s"
			set ::rgk_st 2
		}
		2 {
			if {[peek 0xEC44] == 0} {
				rc2_drive_trace "$::hb_dir/${::hb_tag}_l1.txt" 200 [rc2_label $::h6_labels tick_start] [rc2_label $::h6_labels game_tick] 0 "$::hz_root/build/emu/drive_end.txt"
				hb_note "the game at [machine_info time] s, tick_n [rc2_w 0xCEE0]"
				set ::rgk_st 3
				lappend ::hz_afters [after realtime 0.5 rgk_rt]
				return
			}
		}
		7 {
			if {[peek 0xEC44] == 1} {
				hb_note "the title after the range at [machine_info time] s, tick_n [rc2_w 0xCEE0]: the exact record from here"
				set ::rgk_st 8
				np_t_record
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.05 rgk_step]
}

# (the points where a trace paused the machine: real-time polls, as the emulator waits there; the
#  conditions of a running machine are polled in emulated time, rgk_tp: with throttle off, half a
#  real second is a minute or more of the game)
proc rgk_rt {} {
	switch -- $::rgk_st {
		3 {
			if {$::rc2_trace_done} {
				hb_note "level-1 drive (200 rows) done at [machine_info time] s, tick_n [rc2_w 0xCEE0], lives [peek 0xDC34]"
				rc2_pz_arm $::h6_labels "$::hb_dir/${::hb_tag}_pz.txt" 3000 0 $::rgk_pdrive
				np_keys_arm $::h6_labels $::rgk_pdrive
				set ::hb_st 0
				lappend ::hz_afters [after time 0.05 hb_step]
				set ::rgk_st 4
			}
		}
		4 {
			if {$::rc2_trace_done} {
				hb_note "stage done at [machine_info time] s: result $::rc2_pz_result, passes [rc2_w 0xD000], AG 805Eh [rc2_w 0xDC5E], tick_n [rc2_w 0xCEE0]"
				set ::rgk_st 5
				set ::pause off
				lappend ::hz_afters [after time 0.05 rgk_tp]
				return
			}
		}
	}
	lappend ::hz_afters [after realtime 0.5 rgk_rt]
}

proc rgk_tp {} {
	switch -- $::rgk_st {
		5 {
			if {$::hb_st == 2 || $::hb_st == 4} {
				set ::hb_st 99
				rgx_init $::hb_dir $::hb_tag $::h6_labels $::rgk_fdrive ""
				set ::rgx_hb 1
				rgx_note "Brainstorm's result recorded at [machine_info time] s: the range's trace and keys armed"
				rc2_fr_arm $::h6_labels "$::hb_dir/${::hb_tag}_fr.txt" 3000 0 $::rgk_fdrive
				rgk_keys_arm $::h6_labels $::rgk_fdrive
				rgx_arm_extra
				lappend ::hz_afters [after time 0.05 rgx_step]
				lappend ::hz_afters [after realtime 0.5 rgx_rt]
				set ::rgk_st 6
			}
		}
		6 {
			if {$::rgx_st == 2} {
				rgk_keys_disarm
				# (the next level's briefing and level 2, level 2's step 18: hb_step records them,
				#  and level 2's game frame 100 ends the job; the title only after a PZ_TEST stage)
				if {[hb_has_brief]} { hb_brief_arm 99 }
				set ::rgk_st 7
				lappend ::hz_afters [after time 0.05 rgk_step]
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.05 rgk_tp]
}

# (the job's done condition: np_hf_game's game at the title's tick 300 sets ::hz_done; then the
#  range's notes get that game's ac_diff and the lost counters, once)
proc rgk_done {} {
	if {!$::hz_done} { return 0 }
	if {!$::rgk_end} {
		set ::rgk_end 1
		# (level 2's line is hb_l2_100's)
		if {$::hb_l2} { return 1 }
		rgx_note "game tick_n [rc2_w 0xCEE0] at [machine_info time] s (the title's game at its tick 300), g_frame [rc2_w 0xD000], lives [peek 0xDC34], ac_diff - diff_tab [rgx_rating]; [rgx_lost]"
	}
	return 1
}

# The range's input from the keyboard (row 8), np.tcl np_keys_arm's for fr_tick: at each pass the byte
# of FRNG frame $B00 of the drive's first line becomes keys; every key up past the drive's end and at
# fr_done.
proc rgk_keys_arm {labels drive} {
	rgk_keys_disarm
	set f [open $drive r]
	set rc [catch {gets $f} line]
	close $f
	if {$rc} { error "rgk_keys_arm: $drive: $line" }
	set ::rk_joy [string trim $line]
	set ::rk_held 0
	set ::rk_n 0
	set a [rc2_label $labels fr_tick]
	set t [rc2_label $labels fr_frame]
	set d [rc2_label $labels fr_done]
	set ::rk_bp [debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t" rgk_keys_tick]
	set ::rk_bp2 [debug set_bp $d "\[peek $d\] == [peek $d]" rgk_keys_disarm]
}

proc rgk_keys_disarm {} {
	if {[info exists ::rk_held] && $::rk_held} { keymatrixup 8 $::rk_held }
	set ::rk_held 0
	foreach v {::rk_bp ::rk_bp2} {
		if {[info exists $v]} {
			catch {debug remove_bp [set $v]}
			unset $v
		}
	}
}

proc rgk_keys_tick {} {
	set i [expr {2 * [rc2_w 0xD000]}]
	set b [string range $::rk_joy $i [expr {$i + 1}]]
	set m [expr {$b eq "" ? 0 : [np_keys_mask "0x$b"]}]
	if {$m & 1 && !($::rk_held & 1)} { incr ::rk_n }
	if {$m != $::rk_held} {
		if {$::rk_held} { keymatrixup 8 $::rk_held }
		if {$m} { keymatrixdown 8 $m }
		set ::rk_held $m
	}
}

# ----- the range's test candidates (docs/HARNESS.md 5.20): PZ_TEST=2 builds without a script, played
# from the keyboard (keymatrix row 8, never ext_joy)

# rgc_job NAME MACHINE DIR ROM LABELS DRIVE ?PASSES? ?REC? ?RFROM? ?TAIL?
#   a PZ_TEST=2 build from the power-on: the range's intro, the stage played from the keyboard with
#   DRIVE's moves (a .drive path: rgk_keys_arm; rc2_fr_arm's trace into DIR/NAME_fr.txt, ext_joy
#   unread), rgview.tcl's snapshots at PASSES and a record of REC VBLANKs from pass RFROM, TAIL more
#   past fr_rated (DIR/st/NAME), the intro's and the result's records (rgx_step: rgcheck.py), then
#   the title, fire 1.5 s after it, and the new game's frame 100 (rgx_ng: SHARP again, the lost
#   counters). DRIVE "-": no input, the real 2:00 to OUT OF TIME. (the trace from pass 5990 only).
proc rgc_job {name m dir rom labels drive {passes {}} {rec 0} {rfrom 0} {tail 0}} {
	file mkdir $dir
	return [list $name $m [list rgc_setup $dir $name $rom $labels $drive $passes $rec $rfrom $tail] {[rgc_done]} 1200]
}

proc rgc_setup {dir tag rom labels drive passes rec rfrom tail} {
	set n 3000
	set from 0
	if {$drive eq "-"} {
		set drive "$dir/${tag}_idle.drive"
		set f [open $drive w]
		catch {puts -nonewline $f "\n\n\n\n"}
		close $f
		set n 100000
		set from 5990
	}
	rgx_init $dir $tag $labels $drive ""
	set ::rgc_st 0
	set ::rgc_rv 0
	rc2_fr_drive $rom $labels "$dir/${tag}_fr.txt" $n $from $drive
	rgk_keys_arm $labels $drive
	rgv_arm "$dir/st/$tag" $labels $passes $rec $rfrom $tail
	set ::rgx_hb 1
	rgx_arm_extra
	lappend ::hz_afters [after time 0.05 rgx_step]
	lappend ::hz_afters [after realtime 0.5 rgx_rt]
	lappend ::hz_afters [after time 0.1 rgc_step]
}

proc rgc_step {} {
	switch -- $::rgc_st {
		0 {
			if {$::rgx_st == 2} { set ::rgc_st 1 }
		}
		1 {
			if {[peek 0xEC44] == 1} {
				rgx_note "the title at [machine_info time] s, tick_n [rc2_w 0xCEE0]"
				set a $::rgx_new_game
				set ::rgx_ngbp [debug set_bp $a "\[peek $a\] == [peek $a]" rgx_ng]
				set ::rgc_st 2
				lappend ::hz_afters [after time 1.5 rgc_step]
				return
			}
		}
		2 {
			keymatrixdown 8 1
			lappend ::hz_afters [after time 0.3 {keymatrixup 8 1}]
			rgx_note "fire at [machine_info time] s"
			set ::rgc_st 3
			return
		}
	}
	lappend ::hz_afters [after time 0.05 rgc_step]
}

# (the job's done condition: rgview.tcl's snapshots and record closed once the trace is done, the
#  machine resumed after a record's tail, then the new game's frame 100)
proc rgc_done {} {
	if {!$::rgc_rv} {
		if {[rgv_done]} {
			set ::rgc_rv 1
			set ::pause off
		}
		return 0
	}
	return $::hz_done
}

# rgc_chain CB CDIR BASE W: the candidates CDIR/BASE.ROM (the product), BASE-2M, BASE-range,
# BASE-range-2M, BASE-range-noadj (RG_ADJ=0) and BASE-range-v2 (PZ_LEVEL=2), their label files from
# their builds CB/{prod,prod2m,range,range2m,noadj,v2}/rc2.labels; output in W/run and W/fresh
# (regress.sh cand W B BASE CB). 15 jobs: the title from the power-on of BASE and BASE-2M (cand,
# cand_2m: hz.sh fresh), the product from the keyboard (rgk_job) on an MSX2, an MSX2+ and a turbo R
# and the 2 MiB product on the MSX2, the range candidates from the keyboard (rgc_job, armed's 25
# shots; armed2 for v2) with snapshots and a record, and two left alone to their time out.
proc rgc_chain {cb cdir base w} {
	set C $cdir
	set R "$w/run"
	set fdir "$w/fresh"
	set ftag cand
	set sets {prod "" prod2m -2M range -range range2m -range-2M noadj -range-noadj v2 -range-v2}
	foreach {k x} $sets {
		set rom($k) "$C/$base$x.ROM"
		set lab($k) "$cb/$k/rc2.labels"
		foreach f [list $rom($k) $lab($k)] {
			if {![file exists $f]} { error "rgc_chain: no $f" }
		}
	}
	file mkdir $R
	file mkdir $fdir
	set e "$::hz_root/build/emu"
	set P {60 300 600 900 1100}
	set M2 Gradiente_Expert20_64K
	set F1 Sony_HB-F1XDJ_128K_Lite
	set TR Panasonic_FS-A1GT
	set jobs {}
	lappend jobs [list "fresh $ftag" $M2 [list hz_fresh_setup $fdir $ftag $rom(prod) $lab(prod) 300] {$::hz_done} 900]
	lappend jobs [list "fresh ${ftag}_2m" $M2 [list hz_fresh_setup $fdir ${ftag}_2m $rom(prod2m) $lab(prod2m) 300] {$::hz_done} 900]
	foreach {t m} [list m2 $M2 f1 $F1 tr $TR] {
		lappend jobs [rgk_job kb_$t $m $R $rom(prod) $lab(prod)]
	}
	lappend jobs [rgk_job kb2m_m2 $M2 $R $rom(prod2m) $lab(prod2m)]
	foreach {t m k d} [list rg_m2 $M2 range armed rg_f1 $F1 range armed rg_tr $TR range armed \
			rg2m_m2 $M2 range2m armed rgn_m2 $M2 noadj armed rgn_f1 $F1 noadj armed rgv2_m2 $M2 v2 armed2] {
		lappend jobs [rgc_job $t $m $R $rom($k) $lab($k) "$e/fr_$d.drive" $P 600 1000 60]
	}
	lappend jobs [rgc_job rgt_m2 $M2 $R $rom(range) $lab(range) - {600 3000 6040} 0 0 0]
	lappend jobs [rgc_job rgt_f1 $F1 $R $rom(noadj) $lab(noadj) - {600 3000 6040} 0 0 0]
	return [hz_chain $jobs]
}

set ::rgx_loaded "rgflow loaded"
