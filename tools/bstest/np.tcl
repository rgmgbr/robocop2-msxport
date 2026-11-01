# np.tcl: the final checks' flows (2026-10-27): the paths no check had run before the final
# candidates (docs/HARNESS.md 5.17, docs/BRAINSTORM.md 4.6). Source load.tcl (it sources this file
# after hz.tcl, hz6.tcl, hz7.tcl and fixchk.tcl) in the MCP's openMSX; start one hz_chain; poll
# "list $::hz_state $::hz_msgs" with short msx_local_cmd calls. Never vwait.
#
#   np_job NAME MACHINE SETUP DIR ROM LABELS ?ARG ...?
#       an hz_chain job: SETUP DIR NAME ROM LABELS ARG ... (a setup below, or hz6.tcl's
#       hz6_prod_setup) on a new MACHINE until ::hz_done, 900 s at most; NAME is the records' tag;
#       DIR is created
#   np_keys_arm LABELS DRIVE
#       the stage's input from the keyboard (keymatrix row 8) as a drive's joystick bytes: at
#       pz_tick, PUZL frame $B00's byte (up 1 -> UP, down 2 -> DOWN, left 4 -> LEFT, right 8 ->
#       RIGHT, fire 10h -> SPACE); every key up past the drive's end and at pz_done
#   np_solved_setup DIR TAG ROM LABELS ?KEYS?
#       a PZ_TEST=1 ROM from the power-on, solved by build/emu/pz_solve1.drive (rc2_pz_drive: the
#       trace DIR/TAG_pz.txt; with KEYS = 1, a build without EXTJOY, the moves come from the
#       keyboard); then hz.tcl hb_step's records (DIR/TAG_bonus.txt, _intro.sc5, _result.sc5:
#       bonuscheck.py --result ok), the shooting range's (rgflow.tcl rgh_arm: a script build times
#       it out, a candidate plays its 2:00; bonuscheck.py --range time), the title when the build
#       has one, fire, the new game
#   np_title_setup DIR TAG ROM LABELS ?EXACT?
#       hz6.tcl hz6_prod_setup's flow (the product: the title, level 1 ended by drive_end, the
#       statistics, the stage left to time out, OUT OF TIME.); at the title that follows, hz.tcl
#       hz_fresh's record: DIR/TAG_title_vram.bin, _regs, _pal, _music.txt, _psg.txt, and the game
#       the title starts by itself at its tick 300 (DIR/TAG_game_vram.bin, _game_ram.bin); with
#       EXACT = 1 the exact record instead (np_hf_step: _music2.txt, _game2_*; titlecmp2.py).
#       Since level 2's step 18 the product goes from the range into the level-2 briefing and level
#       2 (hb_step's records under TAG, its game frame 100 noted); there the level is ended as a
#       CHEAT build's F5 ends it ($16D0 = FFh, $16C4 = 40h: np_t_l2), and hb_step records the
#       statistics' way on under TAG2: Brainstorm's and the range's second visits left to time out
#       (TAG2_intro, _result, _rgintro, _rgres) and the level-3 briefing (TAG2_brief); since level
#       3's step A level 3 follows it, ended the same way at its first tick (np_t_end's breakpoint
#       takes BANK_L3 too), then the game completed (since the ending's step: WELL DONE, the CMP
#       tune to its end, the name entry, where ending.tcl ge_ret_arm presses RETURN, and the table);
#       the title after them is the record above (still under TAG), its game noted in TAG2_rg.txt
#   np_title0_setup DIR TAG ROM LABELS ?EXACT?
#       the same record at the title that follows level 1's statistics, in a build without
#       Brainstorm (the approved flow: the commit before Brainstorm)
#   np_fire_setup DIR TAG ROM LABELS
#       a PZ_TEST=1 build without EXTJOY: SPACE at fs_n 60 of the intro and of the result, the
#       stage stuck from the keyboard (build/emu/pz_fail.drive); DIR/TAG_intro60.bin and
#       DIR/TAG_result60.bin (hz7_snap) just before each press (partialcheck.py), the stage's
#       snapshots in DIR/st_TAG/, notes in DIR/TAG_fire.txt; then the title, fire, the new game's
#       tick 100 (DIR/TAG_game100.bin)
#   np_two_setup DIR TAG ROM LABELS
#       an EXTJOY=1 PZ_TEST=1 build: the first stage (pz_fail.drive, DIR/TAG_pz1.txt), its result,
#       the shooting range timed out at its first pass (rgx_timeout_if), the new game, level 1 ended by build/emu/drive_end.txt (its frames moved by tick_n at the
#       new game: DIR/TAG_drive_end.txt; the trace DIR/TAG_l1.txt), the statistics, the second
#       stage driven by rc2_pz_arm (pz_solve1.drive, DIR/TAG_pz2.txt) with hb_step's records of its
#       screens, the new game
#   np_two_title_setup DIR TAG ROM LABELS
#       the same with the candidates' options (PZ_TEST=1, no EXTJOY), the moves from the keyboard
#       and the title between: the first stage, its result, the title, fire, a new game, level 1
#       ended, the statistics, the second stage, its screens' records, the title, fire, the new game
#   np_wp_job NAME MACHINE DIR ROM LABELS
#       hz6_prod_setup's flow with every write to 4000h-7FFFh counted from front_bonus' entry to
#       the end of hb_step's records: level 2's game frame 100 since level 2's step 18 (before it,
#       the new game's tick 100): DIR/NAME_wp.txt
#
# Rules kept: no exit, vwait, max or min; files opened once per write and closed on every path;
# breakpoints at pz_tick carry its byte condition (they fire only where BANK_PUZL is mapped).

# ----- a job of the setups below

proc np_job {name m setup dir rom labels args} {
	file mkdir $dir
	return [list $name $m [list $setup $dir $name $rom $labels {*}$args] {$::hz_done} 900]
}

# ----- the keyboard as a drive

proc np_keys_arm {labels drive} {
	np_keys_disarm
	set f [open $drive r]
	set rc [catch {gets $f} line]
	close $f
	if {$rc} { error "np_keys_arm: $drive: $line" }
	set ::nk_joy [string trim $line]
	set ::nk_held 0
	set ::nk_seen 0
	set ::nk_d [rc2_label $labels pz_done]
	set a [rc2_label $labels pz_tick]
	set t [rc2_label $labels pz_frame]
	set ::nk_bp [debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t" np_keys_tick]
	set ::nk_bp2 [debug set_bp $::nk_d {} np_keys_end]
}

# a key still held let go and an earlier arm's breakpoints removed
proc np_keys_disarm {} {
	if {[info exists ::nk_held] && $::nk_held} { keymatrixup 8 $::nk_held }
	set ::nk_held 0
	foreach v {::nk_bp ::nk_bp2} {
		if {[info exists $v]} {
			catch {debug remove_bp [set $v]}
			unset $v
		}
	}
}

# (row 8: RIGHT 80h, DOWN 40h, UP 20h, LEFT 10h, SPACE 01h)
proc np_keys_mask {b} {
	set m 0
	if {$b & 1} { set m [expr {$m | 0x20}] }
	if {$b & 2} { set m [expr {$m | 0x40}] }
	if {$b & 4} { set m [expr {$m | 0x10}] }
	if {$b & 8} { set m [expr {$m | 0x80}] }
	if {$b & 16} { set m [expr {$m | 0x01}] }
	return $m
}

proc np_keys_tick {} {
	if {!$::nk_seen} {
		set ::nk_seen 1
		set ::nk_op [peek $::nk_d]
	}
	set i [expr {2 * [rc2_w 0xD000]}]
	set b [string range $::nk_joy $i [expr {$i + 1}]]
	set m [expr {$b eq "" ? 0 : [np_keys_mask "0x$b"]}]
	if {$m != $::nk_held} {
		if {$::nk_held} { keymatrixup 8 $::nk_held }
		if {$m} { keymatrixdown 8 $m }
		set ::nk_held $m
	}
}

# (pz_done's breakpoint fires at its address in any slot: only after the stage's first pass and
#  with the same byte there)
proc np_keys_end {} {
	if {!$::nk_seen || [peek $::nk_d] != $::nk_op} return
	np_keys_disarm
}

proc np_hb_init {dir tag labels} {
	file mkdir $dir
	set ::hb_dir $dir
	set ::hb_tag $tag
	foreach n {txt_bs_intro txt_bs_ok txt_bs_fail txt_bs_time isr_split isr_vblank INPUT_SCRIPT} {
		set ::hb_$n [rc2_label $labels $n]
	}
	set ::hb_st 0
	set ::hz_done 0
	hb_init_range $labels
	set f [open "$dir/${tag}_bonus.txt" w]
	close $f
}

# ----- a: the solved ending

proc np_solved_setup {dir tag rom labels {keys 0}} {
	np_hb_init $dir $tag $labels
	rc2_pz_drive $rom $labels "$dir/${tag}_pz.txt" 3000 0 "$::hz_root/build/emu/pz_solve1.drive"
	if {$keys} { np_keys_arm $labels "$::hz_root/build/emu/pz_solve1.drive" }
	lappend ::hz_afters [after time 0.2 hb_step]
	lappend ::hz_afters [after realtime 0.5 hz6_w2]
}

# ----- b: the title after Brainstorm, recorded as on a fresh machine

proc np_title_setup {dir tag rom labels {exact 0}} {
	file mkdir $dir
	set ::hb_l3rec 0
	set ::nt_l3go 0
	hz6_prod_setup $dir $tag $rom $labels
	set ::nt_rom $rom
	set ::nt_labels $labels
	set ::nt_exact $exact
	set ::nt_tag $tag
	set ::nt_gnote 0
	set ::nt_rgarm 0
	set ::nt_st 0
	set ::hb_l2next np_t_l2
	set ::hb_tjob 1
	lappend ::hz_afters [after time 0.5 np_t_poll]
}

# (hb_step's level 2 at its game frame 100) the level's end as the cheat key ends it (frame.asm
# frame_end: $16D0 FFh, $16C4 40h: 65 frames of 100 points, the fade, AG $8050 = 2), asked again at
# each tick of level 2 while $16D0 is 0 (a death restarts the level with it cleared), and at level 3's
# first tick the same (since level 3's step A: AG $8050 = 3, the game completed; a build without level 3
# has no BANK_L3); then hb_step's records under TAG2 from the statistics on, np_t_poll waiting for the
# title after them
proc np_t_l2 {} {
	set ts [rc2_label $::nt_labels tick_start]
	set gt [rc2_label $::nt_labels game_tick]
	set b [rc2_label $::nt_labels BANK_L2]
	if {[catch {set b3 [rc2_label $::nt_labels BANK_L3]}]} { set b3 $b }
	# (::nt_l3go: level 3 played to that game frame first, np_l3flow_setup; 0 in the other jobs)
	set g3 [expr {[info exists ::nt_l3go] ? $::nt_l3go : 0}]
	set ::nt_endbp [debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt && (\[peek 0xF1A0\] == $b || (\[peek 0xF1A0\] == $b3 && \[rc2_w 0xD000\] >= $g3)) && \[peek 0xDBD1\] == 0" np_t_end]
	set ::hb_tag "${::nt_tag}2"
	hb_init_range $::nt_labels
	set ::hb_tjob 1
	set f [open "$::hb_dir/${::hb_tag}_bonus.txt" w]
	close $f
	set ::nt_gnote 1
	set ::nt_st 0
	set ::hb_st 0
	# (pictures of the second visits in play for the eye: Brainstorm's passes 100 and 400, hz7.tcl's
	#  snapshots, stepcheck.py still --visit 2 and shots.py; the range's pass 1500)
	hz7_arm "$::hb_dir/st_${::hb_tag}" $::nt_labels {100 400}
	set ::nt_rgarm 1
	# (after hb_init_range, which clears it: level 3's game frame 100 goes on, np_l3flow_setup)
	if {$g3 > 0} { set ::hb_l2next np_t_l3 }
}

# (hb_step's level 3 at its game frame 100 in np_l3flow_setup's job: its end asked here, as F5 would ask
#  it; the breakpoint above is gone by then: the stages' records remove every breakpoint; then the end
#  count, the game completed, the name entry and the title)
proc np_t_l3 {} {
	hb_note "level 3 played to its game frame [rc2_w 0xD000]: its end asked as F5 would ask it"
	np_t_end
	# (the game completed's records under TAG2, ending.tcl's: the WELL DONE screen, the tune, the name
	#  entry's first wait (ge_ret_arm types RETURN), the table, the end at the title; the flow goes on)
	set ::ge_nopause 1
	ge_arm $::hb_dir $::hb_tag $::nt_rom $::nt_labels {} 0
}

# np_l3flow_setup DIR TAG ROM LABELS: np_title_setup's flow (EXACT 1) with level 3 recorded (level 3's step
# D, docs/LEVEL3.md 4 check 7): after the level-3 briefing hb_step's TAG2_l3g0 (its first picture) and
# "level 3 at tick_n" at its game frame 100, where its end is asked (np_t_end), then the end count, the
# game completed, the name entry (RETURN) and the table with ending.tcl's records under TAG2 (ge_arm),
# and the title recorded as np_title_setup's. Check with bonuscheck.py DIR TAG2 --result time --range
# time --brief l3 --level3 and endcheck.py DIR TAG2 RET --score S (S: the score at the end, its notes').
proc np_l3flow_setup {dir tag rom labels} {
	np_title_setup $dir $tag $rom $labels 1
	set ::hb_l3rec 1
	set ::nt_l3go 100
}

# (the range's snapshot armed once hb_step records the range: its state 6 removes every breakpoint)
proc np_t_rgarm {} {
	set ::nt_rgarm 0
	set a [rc2_label $::nt_labels fr_tick]
	set t [rc2_label $::nt_labels fr_frame]
	set ::nt_rgbp [debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t && \[rc2_w 0xD000\] == 1500" np_t_rgsnap]
}

proc np_t_rgsnap {} {
	catch {debug remove_bp $::nt_rgbp}
	hz7_snap "$::hb_dir/st_${::hb_tag}" rg1500
}

proc np_t_end {} {
	poke 0xDBD1 0xFF
	rc2_wset 0xDBC4 0x40
	hb_note "the level's end asked at [machine_info time] s: game frame [rc2_w 0xD000], tick_n [rc2_w 0xCEE0], energy [format %04X [rc2_w 0xDB9A]]"
}

# (hz_fresh's variables for hf_step or np_hf_step, from the title shown now: the game's tick 300 is
#  tick_n + 300)
proc np_t_record {} {
	set ::hf_dir $::hb_dir
	set ::hf_tag [expr {[info exists ::nt_tag] ? $::nt_tag : $::hb_tag}]
	if {[info exists ::nt_endbp]} { catch {debug remove_bp $::nt_endbp}; unset ::nt_endbp }
	if {[info exists ::nt_rgbp]} { catch {debug remove_bp $::nt_rgbp}; unset ::nt_rgbp; hz7_disarm }
	set ::hf_ticks [expr {[rc2_w 0xCEE0] + 300}]
	set ::hf_rom [file tail $::nt_rom]
	set ::hf_mus [rc2_label $::nt_labels BANK_MUSIC]
	set ::hf_adv [rc2_label $::nt_labels mus_adv]
	set ::hf_st 0
	set ::hf_h 0
	set ::hf_n 0
	set ::nt_st 2
	if {$::nt_exact} { np_hf_step } else { hf_step }
}

proc np_t_poll {} {
	if {[info exists ::nt_rgarm] && $::nt_rgarm && $::hb_st == 7} { np_t_rgarm }
	if {$::nt_st == 0 && ($::hb_st == 2 || $::hb_st == 99)} {
		# (the result recorded: hb_step stops here, no fire on the title)
		set ::hb_st 99
		set ::nt_st 1
		# (since the ending's step the level-3 briefing is followed by the game completed and the
		#  name entry: RETURN there, a blank name (ending.tcl), armed here after the stages' records,
		#  which remove every breakpoint; a build without the ending has no hsn_k: nothing armed)
		catch {ge_ret_arm $::nt_rom $::nt_labels}
	}
	if {$::nt_st == 1 && [peek 0xEC44] == 1} {
		hb_note "the title after the result at [machine_info time] s, tick_n [rc2_w 0xCEE0]: hz_fresh's record from here"
		np_t_record
		return
	}
	lappend ::hz_afters [after time 0.05 np_t_poll]
}

# The same record in a ROM without Brainstorm (level 1, its statistics, then the title): hz6_prod's
# title, fire and level-1 drive, then hz_fresh's record at the title after the statistics (the
# approved flow's title after a played level).
proc np_title0_setup {dir tag rom labels {exact 0}} {
	file mkdir $dir
	set ::hb_dir $dir
	set ::hb_tag $tag
	set ::h6_labels $labels
	set ::hb_st 99
	set ::hz_done 0
	set ::h6_ps 0
	set f [open "$dir/${tag}_bonus.txt" w]
	close $f
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	set ::nt_rom $rom
	set ::nt_labels $labels
	set ::nt_exact $exact
	set ::nt_st 0
	lappend ::hz_afters [after time 0.2 hz6_p_step]
	lappend ::hz_afters [after time 0.5 np_t0_poll]
}

proc np_t0_poll {} {
	if {$::nt_st == 0 && $::h6_ps == 3} { set ::nt_st 1 }
	if {$::nt_st == 1 && [peek 0xEC44] == 1} {
		hb_note "the title after the statistics at [machine_info time] s, tick_n [rc2_w 0xCEE0]: hz_fresh's record from here"
		np_t_record
		return
	}
	lappend ::hz_afters [after time 0.05 np_t0_poll]
}

# hz.tcl hf_step's record made exact for two runs whose title starts at another emulated time: the
# music log keyed by mus_tick with, on each line, the count and hash of the PSG writes since the
# previous tick (DIR/TAG_music2.txt; the window's ends no longer matter), and the game's VRAM and RAM
# at exactly game tick TICKS (a breakpoint at tick_start: DIR/TAG_game2_vram.bin, _game2_ram.bin,
# _game2.txt). np_title_setup / np_title0_setup with EXACT 1 use it.
proc np_hf_step {} {
	switch -- $::hf_st {
		0 {
			if {[peek 0xEC44] == 1 && [peek 0xC202] == 1} {
				set ::hf_st 1
				lappend ::hz_afters [after time 1.0 np_hf_step]
				return
			}
		}
		1 {
			hf_file title_vram.bin [debug read_block "physical VRAM" 0 0x20000]
			hf_file title_regs.bin [debug read_block "VDP regs" 0 [debug size "VDP regs"]]
			hf_file title_pal.bin [debug read_block "VDP palette" 0 [debug size "VDP palette"]]
			set ::hz_mf [open "$::hf_dir/${::hf_tag}_music2.txt" w]
			set ::hf_scc ""
			foreach d [debug list] {
				if {[string match "$::hf_rom SCC*" $d]} { set ::hf_scc $d }
			}
			set ::np_tn 0
			set ::np_th 0
			catch {puts $::hz_mf "# [machine_info time] title shown; SCC debuggable '$::hf_scc'"}
			debug set_bp $::hf_adv "\[debug read {$::hf_rom romblocks} 0xA000\] == $::hf_mus && \[peek 0xC202\] == 1" np_hf_tick
			debug set_watchpoint write_io {0xA0 0xA1} {} np_hf_psg
			set ::hf_st 2
		}
		2 {
			if {[peek 0xC2B2] == 1} {
				foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
				hz_nowp
				catch {puts $::hz_mf "# [machine_info time] music end"}
				close $::hz_mf
				unset ::hz_mf
				set a [rc2_label $::nt_labels tick_start]
				set t [rc2_label $::nt_labels game_tick]
				debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t && \[rc2_w 0xCEE0\] == $::hf_ticks" np_hf_game
				set ::hf_st 3
				return
			}
		}
		3 {
			return
		}
	}
	lappend ::hz_afters [after time 0.1 np_hf_step]
}

proc np_hf_tick {} {
	set s "[rc2_w 0xC205]"
	if {$::hf_scc ne ""} {
		binary scan [debug read_block $::hf_scc 0 [debug size $::hf_scc]] H* x
		append s " $x"
	}
	binary scan [debug read_block "PSG regs" 0 16] H* p
	append s " $p $::np_tn:$::np_th"
	puts $::hz_mf $s
	set ::np_tn 0
	set ::np_th 0
}

proc np_hf_psg {} {
	set v [expr {(($::wp_last_address & 1) << 8) | $::wp_last_value}]
	set ::np_th [expr {($::np_th * 31 + $v + 1) & 0xFFFFFFFF}]
	incr ::np_tn
}

proc np_hf_game {} {
	foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
	hf_file game2_vram.bin [debug read_block "physical VRAM" 0 0x20000]
	hf_file game2_ram.bin [debug read_block memory 0xD000 0x1000]
	set f [open "$::hf_dir/${::hf_tag}_game2.txt" w]
	catch {puts $f "time [machine_info time] tick_n [rc2_w 0xCEE0] (the title's game tick [expr {[rc2_w 0xCEE0] - $::hf_ticks + 300}]) g_frame [rc2_w 0xD000]"}
	close $f
	if {[info exists ::nt_gnote] && $::nt_gnote && [info exists ::rgx_tag]} {
		# (np_title_setup after level 2: the range's second visit's notes get the new game)
		rgx_note "game tick_n [rc2_w 0xCEE0] at [machine_info time] s (the title's game at its tick 300), g_frame [rc2_w 0xD000], lives [peek 0xDC34], ac_diff - diff_tab [rgx_rating], lv_logic [peek 0xF1A0]; [rgx_lost]"
	}
	set ::hf_st 4
	set ::hz_done 1
	set ::pause on
}

# ----- d: the text screens ended by fire

proc np_fire_setup {dir tag rom labels} {
	file mkdir $dir
	set ::nf_dir $dir
	set ::nf_tag $tag
	foreach n {txt_bs_intro txt_bs_ok txt_bs_fail txt_bs_time} { set ::nf_$n [rc2_label $labels $n] }
	set ::nf_st 0
	set ::nf_tp 0
	set ::hz_done 0
	set f [open "$dir/${tag}_fire.txt" w]
	catch {puts $f "# $tag: [file tail $rom] on [machine_info config_name]"}
	close $f
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	np_keys_arm $labels "$::hz_root/build/emu/pz_fail.drive"
	hz7_arm "$dir/st_$tag" $labels {1 5 30 45 52 60 100}
	set a [rc2_label $labels pz_tick]
	set t [rc2_label $labels pz_frame]
	set ::nf_bp [debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t" np_f_first]
	lappend ::hz_afters [after time 0.05 np_f_step]
}

proc np_f_note {m} {
	set f [open "$::nf_dir/${::nf_tag}_fire.txt" a]
	catch {puts $f $m}
	close $f
}

proc np_f_script {} {
	set p [rc2_w 0xCFB8]
	if {$p >= $::nf_txt_bs_intro && $p < $::nf_txt_bs_ok} { return intro }
	if {$p >= $::nf_txt_bs_ok && $p < $::nf_txt_bs_time + 64} { return result }
	return "-"
}

proc np_f_first {} {
	catch {debug remove_bp $::nf_bp}
	np_f_note "the stage's first pass at [format %.3f [machine_info time]] s, [format %.3f [expr {[machine_info time] - $::nf_tp}]] s after the press: pass [rc2_w 0xD000], the intro ended at fs_n [rc2_w 0xCFBE]"
}

proc np_f_step {} {
	set n [rc2_w 0xCFBE]
	switch -- $::nf_st {
		0 {
			if {[np_f_script] eq "intro" && $n >= 60} {
				hz7_snap $::nf_dir ${::nf_tag}_intro60
				keymatrixdown 8 1
				set ::nf_tp [machine_info time]
				np_f_note "intro: SPACE down at [format %.3f $::nf_tp] s, fs_n $n (up 0.15 s later)"
				lappend ::hz_afters [after time 0.15 {keymatrixup 8 1}]
				set ::nf_st 1
			}
		}
		1 {
			if {[np_f_script] eq "result" && $n < 50} {
				set p [rc2_w 0xCFB8]
				set sc [expr {$p < $::nf_txt_bs_fail ? "ok" : ($p < $::nf_txt_bs_time ? "fail" : "time")}]
				np_f_note "the result screen ($sc) at [format %.3f [machine_info time]] s: passes [rc2_w 0xD000], AG 805Eh [rc2_w 0xDC5E], msg_wr [peek 0xC623]"
				set ::nf_st 2
			}
		}
		2 {
			if {$n >= 60} {
				hz7_snap $::nf_dir ${::nf_tag}_result60
				keymatrixdown 8 1
				set ::nf_tp [machine_info time]
				np_f_note "result: SPACE down at [format %.3f $::nf_tp] s, fs_n $n (up 0.15 s later)"
				lappend ::hz_afters [after time 0.15 {keymatrixup 8 1}]
				set ::nf_st 3
			}
		}
		3 {
			if {[peek 0xEC44] == 1} {
				np_f_note "the title at [format %.3f [machine_info time]] s, [format %.3f [expr {[machine_info time] - $::nf_tp}]] s after the press; the result ended at fs_n [rc2_w 0xCFBE]"
				set ::nf_st 4
				lappend ::hz_afters [after time 1.5 np_f_step]
				return
			}
		}
		4 {
			keymatrixdown 8 1
			lappend ::hz_afters [after time 0.3 {keymatrixup 8 1}]
			np_f_note "fire on the title at [format %.3f [machine_info time]] s"
			set ::nf_tn [rc2_w 0xCEE0]
			set ::nf_st 5
		}
		5 {
			if {[peek 0xEC44] == 0 && [rc2_w 0xCEE0] >= $::nf_tn + 100} {
				hz7_snap $::nf_dir ${::nf_tag}_game100
				np_f_note "the new game: tick_n [rc2_w 0xCEE0] at [format %.3f [machine_info time]] s, g_frame [rc2_w 0xD000], lives [peek 0xDC34]; lost: mp [peek 0x1084] atr [peek 0x1082] rd [peek 0x1088] fb [peek 0x069C]"
				hz7_disarm
				set ::nf_st 6
				set ::hz_done 1
				set ::pause on
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.02 np_f_step]
}

# ----- e: a second Brainstorm in one session

proc np_two_setup {dir tag rom labels} {
	np_hb_init $dir $tag $labels
	set ::n2_labels $labels
	rc2_pz_drive $rom $labels "$dir/${tag}_pz1.txt" 3000 0 "$::hz_root/build/emu/pz_fail.drive"
	lappend ::hz_afters [after realtime 0.5 np_2_w1]
}

proc np_2_w1 {} {
	if {$::rc2_trace_done} {
		hb_note "first stage done at [machine_info time] s: result $::rc2_pz_result, passes [rc2_w 0xD000], AG 805Eh [rc2_w 0xDC5E], tick_n [rc2_w 0xCEE0]"
		set a [rc2_label $::n2_labels new_game]
		set ::n2_bp [debug set_bp $a "\[peek $a\] == [peek $a]" np_2_ng]
		# (the shooting range after the first stage's result: a script build's has no time out)
		rgx_timeout_if $::n2_labels
		set ::pause off
		return
	}
	lappend ::hz_afters [after realtime 0.5 np_2_w1]
}

# drive_end.txt with its frames moved by k (rc2_drive_hit indexes it by tick_n, the ticks since the
# power-on): k zero joystick bytes first, k added to every teleport's and poke's frame
proc np_shift_drive {src dst k} {
	set f [open $src r]
	set rc [catch {
		set joy [string trim [gets $f]]
		set tele [string trim [gets $f]]
		set god [string trim [gets $f]]
		set poke [string trim [gets $f]]
	} err]
	close $f
	if {$rc} { error "np_shift_drive: $src: $err" }
	set t2 {}
	foreach t [split $tele] {
		if {$t ne ""} {
			lassign [split $t :] a x y
			lappend t2 "[expr {$a + $k}]:$x:$y"
		}
	}
	set p2 {}
	foreach t [split $poke] {
		if {$t ne ""} {
			lassign [split $t :] a ad v s
			lappend p2 "[expr {$a + $k}]:$ad:$v:$s"
		}
	}
	set f [open $dst w]
	set rc [catch {
		puts $f "[string repeat 00 $k]$joy"
		puts $f [join $t2]
		puts $f $god
		puts $f [join $p2]
	} err]
	close $f
	if {$rc} { error "np_shift_drive: $dst: $err" }
}

proc np_2_ng {} {
	catch {debug remove_bp $::n2_bp}
	set k [rc2_w 0xCEE0]
	set ::n2_k $k
	hb_note "new game at [machine_info time] s, tick_n $k: drive_end's frames moved by $k"
	np_shift_drive "$::hz_root/build/emu/drive_end.txt" "$::hb_dir/${::hb_tag}_drive_end.txt" $k
	rc2_drive_trace "$::hb_dir/${::hb_tag}_l1.txt" 200 [rc2_label $::n2_labels tick_start] [rc2_label $::n2_labels game_tick] $k "$::hb_dir/${::hb_tag}_drive_end.txt"
	lappend ::hz_afters [after realtime 0.5 np_2_w2]
}

proc np_2_w2 {} {
	if {$::rc2_trace_done} {
		hb_note "level-1 drive (200 rows) done at [machine_info time] s, tick_n [rc2_w 0xCEE0], lives [peek 0xDC34]"
		rc2_pz_arm $::n2_labels "$::hb_dir/${::hb_tag}_pz2.txt" 3000 0 "$::hz_root/build/emu/pz_solve1.drive"
		lappend ::hz_afters [after time 0.05 hb_step]
		lappend ::hz_afters [after realtime 0.5 hz6_w2]
		return
	}
	lappend ::hz_afters [after realtime 0.5 np_2_w2]
}

# ----- f: writes to the fixed area (4000h-7FFFh) from front_bonus to the new game

proc np_wp_job {name m dir rom labels} {
	file mkdir $dir
	return [list $name $m [list np_wp_setup $dir $name $rom $labels] {[np_wp_done]} 900]
}

proc np_wp_setup {dir tag rom labels} {
	hz6_prod_setup $dir $tag $rom $labels
	set ::nw_file "$dir/${tag}_wp.txt"
	set ::nw_n 0
	set ::nw_l {}
	set ::nw_t0 -1
	set ::nw_wp ""
	set f [open $::nw_file w]
	catch {puts $f "# $tag: [file tail $rom] on [machine_info config_name]: writes to 4000h-7FFFh from front_bonus' entry to level 2's game frame 100 (the new game's tick 100 in a flow without level 2)"}
	close $f
	set fb [rc2_label $labels front_bonus]
	set ::nw_bp [debug set_bp $fb {[peek 0xC07C] == 7} np_wp_on]
}

proc np_wp_on {} {
	if {$::nw_t0 >= 0} return
	set ::nw_t0 [machine_info time]
	set ::nw_wp [debug set_watchpoint write_mem {0x4000 0x7FFF} {} np_wp_hit]
}

proc np_wp_hit {} {
	incr ::nw_n
	if {[llength $::nw_l] < 16} {
		lappend ::nw_l [format "%04x<-%02x pc %04x at %.4f s" $::wp_last_address $::wp_last_value [reg pc] [machine_info time]]
	}
}

# (the job's done condition: 0 until hb_step's new game; then the count, written once)
proc np_wp_done {} {
	if {!$::hz_done} { return 0 }
	set f [open $::nw_file a]
	set to [expr {[info exists ::hb_l2] && $::hb_l2 ? "level 2's game frame 100" : "the new game's tick 100"}]
	catch {puts $f [format "watch from %.3f s (front_bonus) to %.3f s (%s, g_frame %d, cpu_tr %d): %d writes %s" $::nw_t0 [machine_info time] $to [rc2_w 0xD000] [peek 0xC2A6] $::nw_n $::nw_l]}
	close $f
	if {$::nw_wp ne ""} { catch {debug remove_watchpoint $::nw_wp} }
	return 1
}

# ----- e with the title between: a PZ_TEST=1 build without EXTJOY (the candidates' options), the
# moves from the keyboard. The first stage (pz_fail.drive's moves; rc2_pz_drive's trace
# DIR/TAG_pz1.txt), its result, the title, fire, a new game, level 1 ended by drive_end.txt (moved
# by tick_n; its teleport and poke reach any build), the statistics, the second stage
# (pz_solve1.drive's moves; rc2_pz_arm's trace DIR/TAG_pz2.txt) with hb_step's records of its
# screens, the title, fire, the new game.
proc np_two_title_setup {dir tag rom labels} {
	np_hb_init $dir $tag $labels
	set ::n2_labels $labels
	set ::n2_st 0
	rc2_pz_drive $rom $labels "$dir/${tag}_pz1.txt" 3000 0 "$::hz_root/build/emu/pz_fail.drive"
	np_keys_arm $labels "$::hz_root/build/emu/pz_fail.drive"
	lappend ::hz_afters [after realtime 0.5 np_2t_w1]
}

proc np_2t_w1 {} {
	if {$::rc2_trace_done} {
		hb_note "first stage done at [machine_info time] s: result $::rc2_pz_result, passes [rc2_w 0xD000], AG 805Eh [rc2_w 0xDC5E], tick_n [rc2_w 0xCEE0]"
		set ::pause off
		lappend ::hz_afters [after time 0.05 np_2t_step]
		return
	}
	lappend ::hz_afters [after realtime 0.5 np_2t_w1]
}

proc np_2t_step {} {
	switch -- $::n2_st {
		0 {
			if {[peek 0xEC44] == 1} {
				hb_note "the title after the first stage at [machine_info time] s"
				set ::n2_st 1
				lappend ::hz_afters [after time 1.5 np_2t_step]
				return
			}
		}
		1 {
			keymatrixdown 8 1
			lappend ::hz_afters [after time 0.3 {keymatrixup 8 1}]
			hb_note "fire at [machine_info time] s"
			set ::n2_st 2
		}
		2 {
			if {[peek 0xEC44] == 0} {
				set k [rc2_w 0xCEE0]
				hb_note "the game at [machine_info time] s, tick_n $k: drive_end's frames moved by $k"
				np_shift_drive "$::hz_root/build/emu/drive_end.txt" "$::hb_dir/${::hb_tag}_drive_end.txt" $k
				rc2_drive_trace "$::hb_dir/${::hb_tag}_l1.txt" 200 [rc2_label $::n2_labels tick_start] [rc2_label $::n2_labels game_tick] $k "$::hb_dir/${::hb_tag}_drive_end.txt"
				set ::n2_st 3
				lappend ::hz_afters [after realtime 0.5 np_2t_w2]
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.05 np_2t_step]
}

proc np_2t_w2 {} {
	if {$::rc2_trace_done} {
		hb_note "level-1 drive (200 rows) done at [machine_info time] s, tick_n [rc2_w 0xCEE0], lives [peek 0xDC34]"
		rc2_pz_arm $::n2_labels "$::hb_dir/${::hb_tag}_pz2.txt" 3000 0 "$::hz_root/build/emu/pz_solve1.drive"
		np_keys_arm $::n2_labels "$::hz_root/build/emu/pz_solve1.drive"
		lappend ::hz_afters [after time 0.05 hb_step]
		lappend ::hz_afters [after realtime 0.5 hz6_w2]
		return
	}
	lappend ::hz_afters [after realtime 0.5 np_2t_w2]
}
