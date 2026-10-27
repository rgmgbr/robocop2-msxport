# hz.tcl: the Brainstorm harness's emulator checks (2026-10-27), for the MSX-AI MCP's openMSX
# (msx_local_cmd, headless; docs/HARNESS.md). Source it (or load.tcl, which sources every Tcl file
# of the harness), start one chain, then poll "list $::hz_state $::hz_msgs" with short
# msx_local_cmd calls until ::hz_state reads "done" (or starts with "error"). Never vwait.
#
#   source {<repo>/tools/bstest/hz.tcl}
#   hz_regress DIR ROM LABELS ?tr?   the level-1 regression: drive_cov1 (4401 ticks, C-BIOS_MSX2)
#                                    and drive_cov0 (1400 ticks, Panasonic_FS-A1FX; with "tr" also
#                                    1400 ticks on a turbo R, Panasonic_FS-A1GT) through
#                                    tools/openmsx_rc2.tcl rc2_drive_rom (from = 0): DIR/cov1.txt,
#                                    DIR/cov0.txt (DIR/cov0_tr.txt); compare with tools/bstest/hz.sh
#                                    compare DIR LABELS. ROM: an EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1
#                                    build, LABELS its own label file.
#   hz_fresh DIR TAG ROM LABELS ?MACHINE? ?TICKS?
#                                    the product ROM on a new machine (power-on RAM; default
#                                    Gradiente_Expert20_64K, the user's machine's twin): once the
#                                    title shows (front_mode 1, the music on) and one more second:
#                                    DIR/TAG_title_vram.bin (physical VRAM, 128 KiB), _regs.bin (VDP
#                                    registers), _pal.bin (palette); the title music to its end:
#                                    DIR/TAG_music.txt (a line a music tick: mus_tick, the SCC's
#                                    registers, the PSG's) and the PSG writes' count and hash (the
#                                    speech's PCM included) in DIR/TAG_psg.txt; then the game the
#                                    title starts by itself: at game tick TICKS (default 300)
#                                    DIR/TAG_game_vram.bin and DIR/TAG_game_ram.bin (D000h-DFFFh: the
#                                    mirror AM/AG and AC_VARS). Compare two TAGs with hz.sh fresh.
#   hz_bonus DIR TAG ROM LABELS ?MACHINE? ?END?
#                                    Brainstorm's flow on a new machine (default
#                                    Gradiente_Expert20_64K): with END = "" a PZ_TEST=1 ROM from the
#                                    power-on; with END = "end" an EXTJOY=1 ROM driven to level 1's
#                                    end (build/emu/drive_end.txt, 517 ticks), then on through
#                                    front_stats. Records (DIR/TAG_...): intro.sc5 and result.sc5,
#                                    page 0's lines 0-161 (VRAM 0-50FFh) once the intro's text is
#                                    complete (fs_n 150) and the result's (fs_n 80), with the VDP
#                                    registers and palette (intro_regs.bin, ...), the HUD's VRAM
#                                    (page 3 lines 208-252) at both; bonus.txt: the result shown,
#                                    the VBLANKs and HUD splits (isr_split) between the two records,
#                                    then the title (front_mode 1; fire pressed after 1.5 s) when
#                                    the build has one, and the new game's tick 100 (EXTJOY: the
#                                    result's tick + 100). Check with tools/bstest/bonuscheck.py.
#   hz_chain JOBS                    the runner itself: JOBS a list of {name machine setup done
#                                    timeout-seconds}; setup runs at global level on the new
#                                    machine, the job ends when [expr done] is true.
#
# Rules kept (the project's notes): no exit, vwait, max or min; every file is opened once per write
# and closed on every path (a job's long-lived channels too, by hz_clean); a machine switch happens
# only inside an 'after realtime' callback; z80_freq set back to 3.58 MHz on every machine; at most
# this one openMSX.

# The repository: two folders above this file (tools/bstest/hz.tcl). openMSX's working directory is
# another, so every path the harness builds from it is absolute.
if {[info script] eq ""} { error "hz.tcl: source this file (its place gives the repository)" }
set ::hz_root [file dirname [file dirname [file dirname [file normalize [info script]]]]]
source [file join $::hz_root tools openmsx_rc2.tcl]

proc hz_msg {m} { lappend ::hz_msgs $m }

proc hz_cfg {} {
	set ::throttle off
	set ::mute on
	catch {set ::z80_freq 3579545}
	catch {set ::z80_freq_locked on}
}

# every breakpoint, condition, watchpoint and pending 'after time' of these checks removed, and the
# output channels a job keeps open (rc2_drive_trace's, hz_fresh's music log, rc2_pz_arm's trace,
# hz7.tcl's record, fixchk.tcl's event log) closed: a job that timed out leaves no file open
proc hz_clean {} {
	foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
	foreach {id opts} [debug condition list] { debug condition remove $id }
	hz_nowp
	if {[info exists ::hz_afters]} { foreach a $::hz_afters { catch {after cancel $a} } }
	set ::hz_afters {}
	foreach v {rd_out hz_mf rpz_out h7_rf hzb_f} {
		if {[info exists ::$v]} { catch {close [set ::$v]}; unset ::$v }
	}
}

# every watchpoint removed (the dict API, else the older one's lines "wp#N ...")
proc hz_nowp {} {
	if {[catch {foreach {id opts} [debug watchpoint list] { debug watchpoint remove $id }}]} {
		catch {foreach line [split [debug list_watchpoints] "\n"] {
			set id [lindex $line 0]
			if {$id ne ""} { debug remove_watchpoint $id }
		}}
	}
}

proc hz_chain {jobs} {
	set ::hz_jobs $jobs
	set ::hz_i -1
	set ::hz_state running
	set ::hz_msgs {}
	set ::pause on
	after realtime 0.2 hz_next
	return "started [llength $jobs] job(s)"
}

proc hz_next {} {
	incr ::hz_i
	if {$::hz_i >= [llength $::hz_jobs]} {
		set ::hz_state done
		set ::pause on
		return
	}
	lassign [lindex $::hz_jobs $::hz_i] name m setup done tmo
	hz_clean
	set ::hz_jobname $name
	if {[catch {machine $m} err]} {
		hz_msg "$name: machine $m failed: $err"
		set ::hz_state "error: $name"
		return
	}
	hz_cfg
	set ::hz_done 0
	set ::rc2_trace_done 0
	if {[catch {uplevel #0 $setup} err]} {
		hz_msg "$name: setup failed: $err"
		hz_clean
		set ::hz_state "error: $name"
		return
	}
	set ::pause off
	set ::hz_t0 [clock milliseconds]
	set ::hz_tmo $tmo
	after realtime 1 hz_poll
}

proc hz_poll {} {
	lassign [lindex $::hz_jobs $::hz_i] name m setup done tmo
	set ok 0
	if {[catch {set ok [uplevel #0 [list expr $done]]} err]} { set ok 0 }
	set secs [expr {([clock milliseconds] - $::hz_t0) / 1000.0}]
	if {$ok} {
		hz_msg [format "%s (%s): done in %.1f s, emulated %.1f s" $name $m $secs [machine_info time]]
		set ::pause on
		hz_clean
		after realtime 0.3 hz_next
		return
	}
	if {$secs > $tmo} {
		hz_msg [format "%s (%s): TIMEOUT after %.1f s (emulated %.1f s)" $name $m $secs [machine_info time]]
		set ::pause on
		hz_clean
		after realtime 0.3 hz_next
		return
	}
	after realtime 1 hz_poll
}

# ----- the level-1 regression

proc hz_regress {dir rom labels {tr ""}} {
	file mkdir $dir
	set e "$::hz_root/build/emu"
	set jobs [list \
		[list cov1 C-BIOS_MSX2 [list rc2_drive_rom $rom $labels "$dir/cov1.txt" 4401 0 "$e/drive_cov1.txt"] {$::rc2_trace_done} 900] \
		[list cov0 Panasonic_FS-A1FX [list rc2_drive_rom $rom $labels "$dir/cov0.txt" 1400 0 "$e/drive_cov0.txt"] {$::rc2_trace_done} 600]]
	if {$tr eq "tr"} {
		lappend jobs [list cov0_tr Panasonic_FS-A1GT [list rc2_drive_rom $rom $labels "$dir/cov0_tr.txt" 1400 0 "$e/drive_cov0.txt"] {$::rc2_trace_done} 600]
	}
	hz_chain $jobs
}

# ----- a fresh machine: the title, its music, the start of the game

proc hz_fresh {dir tag rom labels {m Gradiente_Expert20_64K} {ticks 300}} {
	file mkdir $dir
	hz_chain [list [list "fresh $tag" $m [list hz_fresh_setup $dir $tag $rom $labels $ticks] {$::hz_done} 900]]
}

proc hz_fresh_setup {dir tag rom labels ticks} {
	set ::hf_dir $dir
	set ::hf_tag $tag
	set ::hf_ticks $ticks
	set ::hf_rom [file tail $rom]
	set ::hf_mus [rc2_label $labels BANK_MUSIC]
	set ::hf_adv [rc2_label $labels mus_adv]
	set ::hf_st 0
	set ::hf_h 0
	set ::hf_n 0
	set ::hz_done 0
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	lappend ::hz_afters [after time 0.2 hf_step]
}

proc hf_file {name data} {
	set f [open "$::hf_dir/${::hf_tag}_$name" w]
	catch {
		fconfigure $f -translation binary
		puts -nonewline $f $data
	}
	close $f
}

proc hf_step {} {
	switch -- $::hf_st {
		0 {
			# the title: front_mode 1 and the music on
			if {[peek 0xEC44] == 1 && [peek 0xC202] == 1} {
				set ::hf_st 1
				lappend ::hz_afters [after time 1.0 hf_step]
				return
			}
		}
		1 {
			hf_file title_vram.bin [debug read_block "physical VRAM" 0 0x20000]
			hf_file title_regs.bin [debug read_block "VDP regs" 0 [debug size "VDP regs"]]
			hf_file title_pal.bin [debug read_block "VDP palette" 0 [debug size "VDP palette"]]
			set ::hz_mf [open "$::hf_dir/${::hf_tag}_music.txt" w]
			set ::hf_scc ""
			foreach d [debug list] {
				if {[string match "$::hf_rom SCC*" $d]} { set ::hf_scc $d }
			}
			puts $::hz_mf "# [machine_info time] title shown; SCC debuggable '$::hf_scc'"
			debug set_bp $::hf_adv "\[debug read {$::hf_rom romblocks} 0xA000\] == $::hf_mus && \[peek 0xC202\] == 1" hf_tick
			debug set_watchpoint write_io {0xA0 0xA1} {} hf_psg
			set ::hf_st 2
		}
		2 {
			# the music played to its end (mus_end): the game starts by itself
			if {[peek 0xC2B2] == 1} {
				foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
				hz_nowp
				catch {puts $::hz_mf "# [machine_info time] music end; PSG writes $::hf_n hash $::hf_h"}
				close $::hz_mf
				unset ::hz_mf
				set f [open "$::hf_dir/${::hf_tag}_psg.txt" w]
				catch {puts $f "$::hf_n $::hf_h"}
				close $f
				set ::hf_st 3
			}
		}
		3 {
			if {[peek 0xEC44] == 0 && [rc2_w 0xCEE0] >= $::hf_ticks} {
				hf_file game_vram.bin [debug read_block "physical VRAM" 0 0x20000]
				hf_file game_ram.bin [debug read_block memory 0xD000 0x1000]
				set f [open "$::hf_dir/${::hf_tag}_game.txt" w]
				catch {puts $f "time [machine_info time] tick_n [rc2_w 0xCEE0] g_frame [rc2_w 0xD000]"}
				close $f
				set ::hf_st 4
				set ::hz_done 1
				set ::pause on
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.1 hf_step]
}

proc hf_tick {} {
	set s "[rc2_w 0xC205]"
	if {$::hf_scc ne ""} {
		binary scan [debug read_block $::hf_scc 0 [debug size $::hf_scc]] H* x
		append s " $x"
	}
	binary scan [debug read_block "PSG regs" 0 16] H* p
	append s " $p"
	puts $::hz_mf $s
}

proc hf_psg {} {
	set v [expr {(($::wp_last_address & 1) << 8) | $::wp_last_value}]
	set ::hf_h [expr {($::hf_h * 31 + $v + 1) & 0xFFFFFFFF}]
	incr ::hf_n
}

# ----- Brainstorm's flow: the text screens around the stage, the title, the new game

proc hz_bonus {dir tag rom labels {m Gradiente_Expert20_64K} {end ""}} {
	file mkdir $dir
	hz_chain [list [list "bonus $tag" $m [list hz_bonus_setup $dir $tag $rom $labels $end] {$::hz_done} 900]]
}

proc hz_bonus_setup {dir tag rom labels end} {
	set ::hb_dir $dir
	set ::hb_tag $tag
	foreach n {txt_bs_intro txt_bs_ok txt_bs_fail txt_bs_time isr_split isr_vblank INPUT_SCRIPT} {
		set ::hb_$n [rc2_label $labels $n]
	}
	set ::hb_st 0
	set ::hb_log {}
	set ::hz_done 0
	set f [open "$dir/${tag}_bonus.txt" w]
	close $f
	if {$end eq "end"} {
		set ::hb_end 1
		rc2_drive_rom $rom $labels "$dir/${tag}_end_trace.txt" 517 0 "$::hz_root/build/emu/drive_end.txt"
		lappend ::hz_afters [after realtime 0.5 hb_wait_end]
	} else {
		set ::hb_end 0
		carta eject
		carta insert $rom -romtype KonamiSCC
		reset
		lappend ::hz_afters [after time 0.2 hb_step]
	}
}

# (END: the drive pauses the machine after its last row, so this waits in real time; then on
# through the statistics)
proc hb_wait_end {} {
	if {$::rc2_trace_done} {
		hb_note "level-1 drive done at [machine_info time] s, tick_n [rc2_w 0xCEE0]"
		lappend ::hz_afters [after time 0.05 hb_step]
		set ::pause off
		return
	}
	lappend ::hz_afters [after realtime 0.5 hb_wait_end]
}

proc hb_note {m} {
	set f [open "$::hb_dir/${::hb_tag}_bonus.txt" a]
	catch {puts $f $m}
	close $f
}

proc hb_file {name data} {
	set f [open "$::hb_dir/${::hb_tag}_$name" w]
	catch {
		fconfigure $f -translation binary
		puts -nonewline $f $data
	}
	close $f
}

# the script fe_text (or front_stats) reads: intro, ok, fail, time or "-"
proc hb_script {} {
	set p [rc2_w 0xCFB8]
	if {$p >= $::hb_txt_bs_intro && $p < $::hb_txt_bs_ok} { return intro }
	if {$p >= $::hb_txt_bs_ok && $p < $::hb_txt_bs_fail} { return ok }
	if {$p >= $::hb_txt_bs_fail && $p < $::hb_txt_bs_time} { return fail }
	if {$p >= $::hb_txt_bs_time && $p < $::hb_txt_bs_time + 64} { return time }
	return "-"
}

proc hb_snap {name} {
	hb_file $name.sc5 [debug read_block "physical VRAM" 0 [expr {162 * 128}]]
	hb_file ${name}_regs.bin [debug read_block "VDP regs" 0 [debug size "VDP regs"]]
	hb_file ${name}_pal.bin [debug read_block "VDP palette" 0 [debug size "VDP palette"]]
	hb_file ${name}_hud.bin [debug read_block "physical VRAM" 0x1E800 [expr {45 * 128}]]
	hb_file ${name}_ram.bin [debug read_block memory 0xC000 0x4000]
}

proc hb_split {} { incr ::hb_nsplit }
proc hb_vbl {} { incr ::hb_nvbl }

proc hb_step {} {
	switch -- $::hb_st {
		0 {
			if {[hb_script] eq "intro" && [rc2_w 0xCFBE] >= 150} {
				hb_snap intro
				hb_note "intro at [machine_info time] s, fs_n [rc2_w 0xCFBE], R#0 [format %02X [debug read {VDP regs} 0]] R#1 [format %02X [debug read {VDP regs} 1]], AG 8050h [rc2_w 0xDC50], 805Eh [rc2_w 0xDC5E]"
				set ::hb_nsplit 0
				set ::hb_nvbl 0
				debug set_bp $::hb_isr_split {} hb_split
				debug set_bp $::hb_isr_vblank {} hb_vbl
				set ::hb_st 1
			}
		}
		1 {
			# (the next screen started: fs_n from 0 again; the intro's end leaves fs_ptr on the
			# result scripts' first byte)
			if {[rc2_w 0xCFBE] < 50} { set ::hb_st 6 }
		}
		6 {
			set sc [hb_script]
			if {$sc ne "intro" && $sc ne "-" && [rc2_w 0xCFBE] >= 80} {
				hb_snap result
				foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
				hb_note "result $sc at [machine_info time] s, fs_n [rc2_w 0xCFBE], R#0 [format %02X [debug read {VDP regs} 0]] R#1 [format %02X [debug read {VDP regs} 1]], AG 805Eh [rc2_w 0xDC5E]"
				hb_note "between the records: $::hb_nvbl VBLANKs, $::hb_nsplit HUD splits"
				set ::hb_tn [rc2_w 0xCEE0]
				set ::hb_st [expr {$::hb_INPUT_SCRIPT ? 4 : 2}]
			}
		}
		2 {
			if {[peek 0xEC44] == 1} {
				hb_note "title at [machine_info time] s"
				set ::hb_st 3
				lappend ::hz_afters [after time 1.5 hb_step]
				return
			}
		}
		3 {
			keymatrixdown 8 1
			lappend ::hz_afters [after time 0.3 {keymatrixup 8 1}]
			hb_note "fire at [machine_info time] s"
			# (the stage's passes advance tick_n too: the new game's 100 ticks from here)
			set ::hb_tn [rc2_w 0xCEE0]
			set ::hb_st 4
		}
		4 {
			if {[peek 0xEC44] == 0 && [rc2_w 0xCEE0] >= $::hb_tn + 100} {
				hb_file game_vram.bin [debug read_block "physical VRAM" 0 0x20000]
				hb_note "game tick_n [rc2_w 0xCEE0] at [machine_info time] s, g_frame [rc2_w 0xD000], lives [peek 0xDC34]"
				set ::hb_st 5
				set ::hz_done 1
				set ::pause on
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.05 hb_step]
}
