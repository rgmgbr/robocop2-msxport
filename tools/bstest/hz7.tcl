# hz7.tcl: step 7's display checks (source it after hz.tcl, or source load.tcl, in the MCP's
# openMSX; poll "list $::hz_state $::hz_msgs"; never vwait; docs/HARNESS.md).
#
#   hz7_snap DIR NAME          one snapshot: DIR/NAME.bin = physical VRAM (128 KiB), RAM C000h-FFFFh,
#                              the 64 VDP registers, the palette (stepcheck.py still, shots.py)
#   hz7_arm DIR LABELS PASSES ?REC? ?RFROM?
#                              (after rc2_pz_drive or a reset) at pz_tick, a snapshot at each pass
#                              ($B00) in PASSES (DIR/pNNNN.bin); with REC > 0, from pass RFROM on, a
#                              record of the next REC pictures (DIR/rec.bin: hz7_pic's layout, one a
#                              VBLANK, at iv_late: the list just applied; stepcheck.py rec)
#   hz7_job NAME MACHINE ROM LABELS DRIVE OUT ?PASSES? ?REC? ?RFROM?
#                              an hz_chain job: rc2_pz_drive of build/emu/pz_DRIVE.drive (trace
#                              OUT/tr/NAME.txt) with hz7_arm into OUT/st/NAME/ (check_all.sh)
#   hz7_guard_arm, hz7_after_setup, hz7_fresh_setup: below.
#
# Rules kept: no exit, vwait, max or min; the record file is opened once and closed on every end
# (hz_clean closes it when a job times out); a snapshot file is opened once per write.

proc hz7_snap {dir name} {
	file mkdir $dir
	set f [open "$dir/$name.bin" w]
	catch {
		fconfigure $f -translation binary
		puts -nonewline $f [debug read_block "physical VRAM" 0 0x20000]
		puts -nonewline $f [debug read_block memory 0xC000 0x4000]
		set regs ""
		for {set i 0} {$i < 64} {incr i} { append regs [binary format cu [debug read "VDP regs" $i]] }
		puts -nonewline $f $regs
		puts -nonewline $f [debug read_block "VDP palette" 0 [debug size "VDP palette"]]
	}
	close $f
}

proc hz7_arm {dir labels passes {rec 0} {rfrom 0}} {
	file mkdir $dir
	set ::h7_dir $dir
	set ::h7_passes $passes
	set ::h7_rec $rec
	set ::h7_rfrom $rfrom
	set ::h7_recn 0
	set ::h7_recdone [expr {$rec > 0 ? 0 : 1}]
	set a [rc2_label $labels pz_tick]
	set t [rc2_label $labels pz_frame]
	set ::h7_ivl [rc2_label $labels iv_late]
	set ::h7_bp [debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t" hz7_tick]
	set ::h7_rbp ""
	return "armed"
}

proc hz7_tick {} {
	set f [rc2_w 0xD000]
	if {[lsearch -exact $::h7_passes $f] >= 0} { hz7_snap $::h7_dir [format p%04d $f] }
	if {$::h7_rec > 0 && $::h7_rbp eq "" && !$::h7_recdone && $f >= $::h7_rfrom} {
		set ::h7_rf [open "$::h7_dir/rec.bin" w]
		fconfigure $::h7_rf -translation binary
		set ::h7_rbp [debug set_bp $::h7_ivl {} hz7_pic]
	}
}

# One picture: what the list just applied shows (layout in stepcheck.py REC): the VDP registers,
# R#2's page lines 0-161, R#5's SAT (32 bytes), pf_pal, the list, RAM C000h-C0FFh, C600h-C6FFh,
# D000h-D0FFh, EE00h-EEFFh.
proc hz7_pic {} {
	set regs ""
	for {set i 0} {$i < 64} {incr i} { append regs [binary format cu [debug read "VDP regs" $i]] }
	set r2 [debug read "VDP regs" 2]
	set page [expr {($r2 >> 5) & 3}]
	set sat [expr {(([debug read "VDP regs" 11] & 3) << 15) | (([debug read "VDP regs" 5] & 0xFC) << 7)}]
	set lp [rc2_w 0xC003]
	puts -nonewline $::h7_rf $regs
	puts -nonewline $::h7_rf [debug read_block "physical VRAM" [expr {$page * 0x8000}] 20736]
	puts -nonewline $::h7_rf [debug read_block "physical VRAM" $sat 32]
	puts -nonewline $::h7_rf [debug read_block memory 0xEA40 32]
	puts -nonewline $::h7_rf [debug read_block memory $lp 32]
	puts -nonewline $::h7_rf [debug read_block memory 0xC000 256]
	puts -nonewline $::h7_rf [debug read_block memory 0xC600 256]
	puts -nonewline $::h7_rf [debug read_block memory 0xD000 256]
	puts -nonewline $::h7_rf [debug read_block memory 0xEE00 256]
	incr ::h7_recn
	if {$::h7_recn >= $::h7_rec} { hz7_recend }
}

proc hz7_recend {} {
	if {$::h7_rbp ne ""} { catch {debug remove_bp $::h7_rbp} }
	set ::h7_rbp ""
	if {[info exists ::h7_rf]} { catch {close $::h7_rf}; unset ::h7_rf }
	set ::h7_recdone 1
}

proc hz7_disarm {} {
	catch {debug remove_bp $::h7_bp}
	hz7_recend
}

# a job's done condition: the drive ended (rc2_pz_drive: paused at pz_done or after n rows); the
# record closed in every case
proc hz7_done {} {
	if {$::rc2_trace_done} {
		hz7_disarm
		return 1
	}
	return 0
}

# A job of hz_chain: the drive build/emu/pz_DRIVE.drive on MACHINE with ROM (an EXTJOY=1 PZ_TEST=1
# build), its trace into OUT/tr/NAME.txt; snapshots at PASSES and a record of REC pictures from pass
# RFROM into OUT/st/NAME/.
proc hz7_job {name m rom labels drive out {passes {}} {rec 0} {rfrom 0}} {
	set setup "rc2_pz_drive {$rom} {$labels} {$out/tr/$name.txt} 3000 0 {$::hz_root/build/emu/pz_$drive.drive}; hz7_arm {$out/st/$name} {$labels} {$passes} $rec $rfrom"
	return [list $name $m [list eval $setup] {[hz7_done]} 300]
}

# The display guard (tools/openmsx_rc2.tcl rc2_guard) over SECS emulated seconds from pass FROM of
# a drive (after rc2_pz_drive): its counts and log into FILE; the machine resumed afterwards
# (rc2_rg_end pauses it), so that the drive runs to its end.
proc hz7_guard_arm {labels from secs nl file} {
	set ::h7g_labels $labels
	set ::h7g_from $from
	set ::h7g_secs $secs
	set ::h7g_nl $nl
	set ::h7g_file $file
	set ::h7g_on 0
	set a [rc2_label $labels pz_tick]
	set t [rc2_label $labels pz_frame]
	set ::h7g_bp [debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t" hz7_g_tick]
}

proc hz7_g_tick {} {
	if {$::h7g_on || [rc2_w 0xD000] < $::h7g_from} return
	set ::h7g_on 1
	catch {debug remove_bp $::h7g_bp}
	unset -nocomplain ::rg_notear
	rc2_guard $::h7g_secs 157 $::h7g_nl 162 $::h7g_labels
	set ::h7g_t0 [machine_info time]
	lappend ::hz_afters [after realtime 0.5 hz7_g_poll]
}

proc hz7_g_poll {} {
	if {[info exists ::rg_done] && $::rg_done} {
		set f [open $::h7g_file w]
		catch {
			puts $f "guard from pass $::h7g_from (emulated [format %.3f $::h7g_t0] s) for $::h7g_secs s, to pass [rc2_w 0xD000]: frames $::rg_frames, commands $::rg_cmds"
			foreach k {reg pal cmd cpu vbl tear} { puts $f "$k $::rg_n($k)" }
			foreach l $::rg_log { puts $f $l }
		}
		close $f
		set ::rg_done 0
		set ::pause off
		return
	}
	lappend ::hz_afters [after realtime 0.5 hz7_g_poll]
}

# After the stage (an EXTJOY=1 PZ_TEST=1 build, the drive build/emu/pz_DRIVE.drive): DIR/TAG_intro.bin
# once the intro's text is complete (fs_n 150), the stage (rc2_pz_drive, DIR/TAG_pz.txt), then on:
# DIR/TAG_result.bin (the result's fs_n 80: page 2 and the SATs as the stage left them), the new
# game: DIR/TAG_g50.bin at its game frame 50, then rc2_snaps DIR/TAG_snaps (6, 0.5 s apart) for
# tools/checkrun.py. Notes: DIR/TAG_after.txt (restorecheck.py).
proc hz7_after_setup {dir tag rom labels drive} {
	set ::h7a_dir $dir
	set ::h7a_tag $tag
	set ::h7a_st 0
	set ::h7a_labels $labels
	set ::rc2_snaps_done 0
	foreach n {txt_bs_intro txt_bs_ok} { set ::h7a_$n [rc2_label $labels $n] }
	set ::hz_done 0
	rc2_pz_drive $rom $labels "$dir/${tag}_pz.txt" 3000 0 "$::hz_root/build/emu/pz_$drive.drive"
	# (a script build: the shooting range after Brainstorm's result never times out by itself)
	rgx_timeout_if $labels
	lappend ::hz_afters [after time 0.05 hz7a_step]
	lappend ::hz_afters [after realtime 0.5 hz7a_rt]
}

proc hz7a_note {m} {
	set f [open "$::h7a_dir/${::h7a_tag}_after.txt" a]
	catch {puts $f $m}
	close $f
}

# (the stage's end paused the machine at pz_done: resumed)
proc hz7a_rt {} {
	if {$::h7a_st == 1 && $::rc2_trace_done} {
		hz7a_note "stage done at [machine_info time] s: result $::rc2_pz_result, passes [rc2_w 0xD000]"
		poke 0xCE5A 0
		set ::h7a_st 2
		set ::pause off
		lappend ::hz_afters [after time 0.05 hz7a_step]
		return
	}
	if {$::h7a_st < 2} { lappend ::hz_afters [after realtime 0.5 hz7a_rt] }
}

proc hz7a_step {} {
	set p [rc2_w 0xCFB8]
	set n [rc2_w 0xCFBE]
	switch -- $::h7a_st {
		0 {
			if {$p >= $::h7a_txt_bs_intro && $p < $::h7a_txt_bs_ok && $n >= 150} {
				hz7_snap $::h7a_dir ${::h7a_tag}_intro
				hz7a_note "intro at [machine_info time] s"
				set ::h7a_st 1
				return
			}
		}
		2 {
			if {$p >= $::h7a_txt_bs_ok && $n >= 80 && $n < 100} {
				hz7_snap $::h7a_dir ${::h7a_tag}_result
				hz7a_note "result at [machine_info time] s, fs_n $n"
				set ::h7a_st 3
			}
		}
		3 {
			hz7_g50_arm
			set ::h7a_st 4
			return
		}
		5 {
			if {$::rc2_snaps_done} {
				hz7a_note "snapshots done at [machine_info time] s; lost: mp [peek 0x1084] atr [peek 0x1082] rd [peek 0x1088] fb [peek 0x069C]"
				set ::hz_done 1
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.05 hz7a_step]
}

# The new game's frame 50 (tools/openmsx_rc2.tcl's tick_start: "call game_tick"): DIR/TAG_g50.bin,
# then rc2_snaps DIR/TAG_snaps (hz7a_step state 5 waits for them).
proc hz7_g50_arm {} {
	set a [rc2_label $::h7a_labels tick_start]
	set t [rc2_label $::h7a_labels game_tick]
	set ::h7a_bp [debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t && \[rc2_w 0xD000\] >= 50" hz7_g50]
}

proc hz7_g50 {} {
	catch {debug remove_bp $::h7a_bp}
	hz7_snap $::h7a_dir ${::h7a_tag}_g50
	hz7a_note "game frame [rc2_w 0xD000] at [machine_info time] s, tick_n [rc2_w 0xCEE0]"
	rc2_snaps "$::h7a_dir/${::h7a_tag}_snaps" 6 0.5
	set ::h7a_st 5
	lappend ::hz_afters [after realtime 0.5 hz7a_rt5]
}

# (rc2_snaps pauses the machine after its last snapshot: polled in real time)
proc hz7a_rt5 {} {
	if {$::rc2_snaps_done} {
		hz7a_note "snapshots done at [machine_info time] s; lost: mp [peek 0x1084] atr [peek 0x1082] rd [peek 0x1088] fb [peek 0x069C]"
		set ::hz_done 1
		return
	}
	lappend ::hz_afters [after realtime 0.5 hz7a_rt5]
}

# A fresh start of an EXTJOY=1 build (no PZ_TEST): DIR/TAG_g50.bin at game frame 50 and rc2_snaps
# DIR/TAG_snaps, as hz7_after's new game.
proc hz7_fresh_setup {dir tag rom labels} {
	set ::h7a_dir $dir
	set ::h7a_tag $tag
	set ::h7a_labels $labels
	set ::h7a_st 4
	set ::hz_done 0
	set ::rc2_snaps_done 0
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	hz7_g50_arm
}
