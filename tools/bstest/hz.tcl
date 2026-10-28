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
#                                    then, in a build with the shooting range, its screens
#                                    (rgflow.tcl rgh_arm: rgintro, rgres, TAG_rg.txt; a script
#                                    build times it out at its first pass), then the title
#                                    (front_mode 1; fire pressed after 1.5 s) when the build has
#                                    one, and the new game's tick 100 (EXTJOY: the result's tick +
#                                    100). Check with tools/bstest/bonuscheck.py (--range).
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
# hz7.tcl's record, fixchk.tcl's event log, rc2_fr_arm's trace, rgview.tcl's record and rate log)
# closed: a job that timed out leaves no file open
proc hz_clean {} {
	foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
	foreach {id opts} [debug condition list] { debug condition remove $id }
	hz_nowp
	if {[info exists ::hz_afters]} { foreach a $::hz_afters { catch {after cancel $a} } }
	set ::hz_afters {}
	foreach v {rd_out hz_mf rpz_out h7_rf hzb_f rfr_out rv_rf rv_tf} {
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

# hz_chain JOBS ?MARK?: with MARK (a file), the chain's messages are written there when it ends (done
# or an error), so that a shell can wait for the file instead of polling the emulator
proc hz_chain {jobs {mark ""}} {
	set ::hz_mark $mark
	if {$mark ne ""} { file delete $mark }
	set ::hz_jobs $jobs
	set ::hz_i -1
	set ::hz_state running
	set ::hz_msgs {}
	set ::pause on
	after realtime 0.2 hz_next
	return "started [llength $jobs] job(s)"
}

proc hz_mark_write {} {
	if {![info exists ::hz_mark] || $::hz_mark eq ""} return
	set f [open $::hz_mark w]
	catch {
		puts $f "state $::hz_state"
		foreach m $::hz_msgs { puts $f $m }
	}
	close $f
}

proc hz_next {} {
	incr ::hz_i
	if {$::hz_i >= [llength $::hz_jobs]} {
		set ::hz_state done
		set ::pause on
		hz_mark_write
		return
	}
	lassign [lindex $::hz_jobs $::hz_i] name m setup done tmo
	hz_clean
	set ::hz_jobname $name
	if {[catch {machine $m} err]} {
		hz_msg "$name: machine $m failed: $err"
		set ::hz_state "error: $name"
		hz_mark_write
		return
	}
	hz_cfg
	set ::hz_done 0
	set ::rc2_trace_done 0
	if {[catch {uplevel #0 $setup} err]} {
		hz_msg "$name: setup failed: $err"
		hz_clean
		set ::hz_state "error: $name"
		hz_mark_write
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

# ----- level 2's drives (docs/LEVEL2.md 4.1; docs/HARNESS.md 5.22)

# hz_l2 DIR R ?tr? ?ONLY?: the bench's level-2 references played on the LV_TEST=2 builds of
# "hz.sh l2builds R" (R/<b>/rc2_<b>.rom: l2 the default carry, l2s, l2f and l2p the ratings SHARP,
# FAIR and POOR, l2o and l2c the game over without and with a credit) through rc2_drive_rom (no tick
# runs before level 2 in those builds, so tick_n is the drive's index): DIR/l2_<job>.txt, n rows
# each (the reference's). With "tr", tour and vat on a turbo R too. ONLY: a list of job names (the
# others skipped). Compare with "hz.sh compare --fields analysis/amiga_ram_l2.tsv DIR R".
# Each job also keeps, at every tick_start, the port's lost counters and the map patches' pools in
# use (hz_l2_drive), and appends them to DIR/lost.txt when it ends (hz_l2_lost; docs/LEVEL2.md 4.2
# check 5): "hz.sh compare --fields" takes each job's last line there and wants mp, atr, rd, fb 0.
# (cont: since level 2's step 8 RoboCop dies in the vat, and until the port has the continue (its
# step 19) the game over ends the trace at row 108: the job ends once those 109 rows are written
# (its lost counters those of row 108's tick; 60 s at most), and "hz.sh compare" takes it as
# cont:109, the plan's milestone 1; step 19 gives it the others' condition again)
proc hz_l2_jobs {dir R {tr ""} {only ""}} {
	file mkdir $dir
	set e "$::hz_root/build/emu"
	set lost [file join $dir lost.txt]
	set spec [list \
		end l2 l2_end 259 C-BIOS_MSX2            tour l2 l2_tour 2654 C-BIOS_MSX2 \
		lift l2 l2_lift 801 C-BIOS_MSX2          trolley l2 l2_trolley 641 C-BIOS_MSX2 \
		vat l2 l2_vat 701 C-BIOS_MSX2            fuzz l2 l2_fuzz 2501 C-BIOS_MSX2 \
		sharp l2s l2_trolley 641 C-BIOS_MSX2     fair l2f l2_trolley 641 C-BIOS_MSX2 \
		poor l2p l2_trolley 641 C-BIOS_MSX2      over l2o l2_over 109 C-BIOS_MSX2 \
		cont l2c l2_cont 301 C-BIOS_MSX2         barrel l2 l2_barrel 901 C-BIOS_MSX2 \
		mine l2 l2_mine 161 C-BIOS_MSX2          t1left l2 l2_t1left 341 C-BIOS_MSX2 \
		drone l2 l2_drone 401 C-BIOS_MSX2        tour_fx l2 l2_tour 2654 Panasonic_FS-A1FX \
		vat_fx l2 l2_vat 701 Panasonic_FS-A1FX   trolley_eu l2 l2_trolley 641 C-BIOS_MSX2_EU]
	if {$tr eq "tr"} {
		lappend spec tour_tr l2 l2_tour 2654 Panasonic_FS-A1GT vat_tr l2 l2_vat 701 Panasonic_FS-A1GT
	}
	set jobs {}
	foreach {name b drive n m} $spec {
		if {$only ne "" && [lsearch -exact $only $name] < 0} continue
		set tmo 1800
		set done "\$::rc2_trace_done && \[hz_l2_lost {$lost}\]"
		if {$name eq "cont"} {
			set tmo 60
			set done "\$::rd_left <= [expr {$n - 109}] && \[hz_l2_lost {$lost}\]"
		}
		lappend jobs [list l2_$name $m [list hz_l2_drive "$R/$b/rc2_$b.rom" "$R/$b/rc2_$b.labels" \
			"$dir/l2_$name.txt" $n "$e/$drive.drive"] $done $tmo]
	}
	return $jobs
}

# Level 2's objects against the bench (the plan's 4.2 check 3, step 12): rc2_objs_rom (each new
# register list's objects) on an LV_TEST=2 EXTJOY build driven by a bench drive, until the game frame
# passes the drive's rows (its file closed, its probe gone: hz_l2_objs_done). DIR/<name>_<m2|fx|tr>.txt;
# the record runs on a little past the drive (the poll comes once a real second): tools/objcmp.py's
# --rows N cuts it. The bench's side: tools/amigaemu.py game --level 2 --carry 10050:2:0:good --gframes
# G --drive build/emu/l2_<name>.drive --stop-at-end --bobs AMI.jsonl.
proc hz_l2_objs_jobs {dir R names {machines {C-BIOS_MSX2 m2 Panasonic_FS-A1FX fx Panasonic_FS-A1GT tr}}} {
	file mkdir $dir
	set e "$::hz_root/build/emu"
	set rows [dict create end 259 tour 2654 lift 801 trolley 641 vat 701 barrel 901 mine 161 t1left 341 drone 401]
	set jobs {}
	foreach name $names {
		set n [dict get $rows $name]
		foreach {m tag} $machines {
			lappend jobs [list objs_${name}_$tag $m [list hz_l2_objs "$R/l2/rc2_l2.rom" "$R/l2/rc2_l2.labels" \
				"$dir/${name}_$tag.txt" [expr {8 * $n}] "$e/l2_$name.drive"] "\[hz_l2_objs_done $n\]" 900]
		}
	}
	return $jobs
}

proc hz_l2_objs {rom labels file n drive} {
	if {[info exists ::ro_out]} { catch {close $::ro_out}; unset ::ro_out }
	if {[info exists ::ro_bp]} { catch {debug probe remove_bp $::ro_bp} }
	rc2_objs_rom $rom $labels $file $n $drive
}

proc hz_l2_objs_done {rows} {
	if {$::ro_done} { return 1 }
	if {[rc2_w 0xCEE0] < $rows} { return 0 }
	catch {close $::ro_out}
	unset -nocomplain ::ro_out
	catch {debug probe remove_bp $::ro_bp}
	set ::ro_done 1
	set ::pause on
	return 1
}

proc hz_l2 {dir R {tr ""} {only ""}} {
	hz_chain [hz_l2_jobs $dir $R $tr $only]
}

# hz_l2_drive ROM LABELS OUT N DRIVE: rc2_drive_rom from 0 and, at every tick_start, the port's lost
# counters (mp_lost 1084h, atr_lost 1082h, rd_lost 1088h, fb_lost 069Ch) and the map patches' pools
# in use (MP_A's and MP_B's entry FFh: 0BFFh, F5FFh; tiles.asm map_write) kept in ::hz_l2_lv with
# tick_n, for hz_l2_lost (rc2_drive_rom removes every breakpoint: this one is set after it)
proc hz_l2_drive {rom labels out n drive} {
	rc2_drive_rom $rom $labels $out $n 0 $drive
	set ts [rc2_label $labels tick_start]
	set gt [rc2_label $labels game_tick]
	set ::hz_l2_lv {}
	debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt" hz_l2_lv_hit
}

proc hz_l2_lv_hit {} {
	set ::hz_l2_lv [list [peek 0x1084] [peek 0x1082] [peek 0x1088] [peek 0x069C] [peek 0x0BFF] [peek 0xF5FF] [rc2_w 0xCEE0]]
}

# the job's last kept counters appended to FILE ("l2_<job> (<machine>): mp N atr N rd N fb N pools
# EVEN/ODD tick T"); a done condition's last term: returns 1
proc hz_l2_lost {file} {
	set f [open $file a]
	catch {
		if {[llength $::hz_l2_lv] == 7} {
			lassign $::hz_l2_lv mp atr rd fb pa pb t
			puts $f "$::hz_jobname ([machine_info config_name]): mp $mp atr $atr rd $rd fb $fb pools $pa/$pb tick $t"
		} else {
			puts $f "$::hz_jobname ([machine_info config_name]): no tick seen"
		}
	}
	close $f
	return 1
}

# hz_l2_start_jobs DIR ROM LABELS ?SECS?: level 2's start check (docs/LEVEL2.md 4.2 check 1) on the
# three machines (C-BIOS_MSX2, the FS-A1FX's V9958, the FS-A1GT's R800): ROM (an EXTJOY=1 LV_TEST=2
# build, LABELS its label file) from the power-on on tour's drive; from level 2's first tick_start
# (lv_cur's logic bank BANK_L2: no VRAM transfer under way), SECS (default 42) of emulated time
# under rc2_guard (tears counted), rc2_patcheck, rc2_sprlines and rc2_satcheck, as l2base.tcl's
# start check of level 1. DIR/start_<m2|fx|tr>.txt: at that first tick ("start:") and at the end
# ("end:") the game frame, RoboCop's and the camera's place, lv_cur's logic bank, R#1, the VDP's
# palette, lv_pal and pf_pal (hex), the lost counters and the pools; the rows driven, the guard's
# counts, patcheck, sprlines, satcheck. The drive's trace (tour's first rows, up to the guard's end)
# goes to DIR/l2_tour.txt, l2_tour_fx.txt, l2_tour_tr.txt: on the l2 build (hz.sh l2builds) compare
# them with "hz.sh compare --fields analysis/amiga_ram_l2.tsv DIR R tour:N tour_fx:N tour_tr:N".
proc hz_l2_start_jobs {dir rom labels {secs 42}} {
	file mkdir $dir
	set e "$::hz_root/build/emu"
	set jobs {}
	foreach {t m tn} {m2 C-BIOS_MSX2 tour fx Panasonic_FS-A1FX tour_fx tr Panasonic_FS-A1GT tour_tr} {
		lappend jobs [list l2start_$t $m [list hz_l2_start_setup "$dir/start_$t.txt" $rom $labels \
			"$dir/l2_$tn.txt" "$e/l2_tour.drive" $secs] {[hz_l2_start_done]} 900]
	}
	return $jobs
}

proc hz_l2_start_setup {out rom labels trace drive secs} {
	set ::hz_l2g_out $out
	set ::hz_l2g_rom $rom
	set ::hz_l2g_lab $labels
	set ::hz_l2g_secs $secs
	set ::hz_l2g_n 2654
	set ::hz_l2g 0
	set ::hz_l2g_written 0
	set ::rg_done 0
	unset -nocomplain ::rg_notear              ;# (tears counted)
	hz_l2_drive $rom $labels $trace $::hz_l2g_n $drive
	set ts [rc2_label $labels tick_start]
	set gt [rc2_label $labels game_tick]
	set bank [expr {[rc2_label $labels BANK_L2]}]
	set ::hz_l2g_bp [debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt && \[peek 0xF1A0\] == $bank" hz_l2_start_go]
}

proc hz_l2_start_go {} {
	debug remove_bp $::hz_l2g_bp
	set lab $::hz_l2g_lab
	set ::hz_l2g_t0 [hz_l2_state]
	rc2_guard $::hz_l2g_secs 159 262 163 $lab
	rc2_patcheck $::hz_l2g_rom [rc2_label $lab spr_plan] [expr {[rc2_label $lab SPR_BASE_BANK]}] \
		[expr {[rc2_label $lab SPR_PAT_BANK]}] [expr {[rc2_label $lab SPR_COL_BANK]}] 100000
	rc2_sprlines 100000 [expr {[rc2_label $lab VIEW_LINES]}]
	rc2_satcheck 100000
	set ::hz_l2g 1
}

# the machine's state, a line per item (hz_l2_start_jobs' "start:" and "end:" lines)
proc hz_l2_state {} {
	set lab $::hz_l2g_lab
	set s [list "game frame [rc2_w 0xD000] tick_n [rc2_w 0xCEE0] time [machine_info time]"]
	lappend s "robocop [rc2_w 0xDAD0] [rc2_w 0xDAD4] camera [rc2_w 0xD004] [rc2_w 0xD006] lv_logic [peek 0xF1A0] R#1 [format %02X [debug read {VDP regs} 1]]"
	binary scan [debug read_block {VDP palette} 0 32] H* p
	lappend s "vdp_palette $p"
	foreach v {lv_pal pf_pal} {
		binary scan [debug read_block memory [rc2_label $lab $v] 32] H* p
		lappend s "$v $p"
	}
	lappend s "lost: mp [peek 0x1084] atr [peek 0x1082] rd [peek 0x1088] fb [peek 0x069C] pools [peek 0x0BFF]/[peek 0xF5FF]"
	return $s
}

# the job's end: the guard done (it pauses the machine); the results written once
proc hz_l2_start_done {} {
	if {$::hz_l2g != 1 || !$::rg_done} { return 0 }
	if {$::hz_l2g_written} { return 1 }
	set ::hz_l2g_written 1
	catch {debug probe remove_bp $::rx8_bp}
	catch {debug probe remove_bp $::rs_sat_bp}
	catch {debug remove_bp $::rp_bp}
	set f [open $::hz_l2g_out w]
	catch {
		foreach x $::hz_l2g_t0 { puts $f "start: $x" }
		foreach x [hz_l2_state] { puts $f "end: $x" }
		puts $f "rows: [expr {$::hz_l2g_n - $::rd_left}]"
		set g {}
		foreach k {reg pal cmd cpu vbl tear} { lappend g "$k $::rg_n($k)" }
		puts $f "guard: [join $g {, }]"
		foreach x $::rg_log { puts $f "  $x" }
		puts $f "patcheck: $::rp_n entries, $::rp_bad bad"
		foreach x [lrange $::rp_log 0 40] { puts $f "  $x" }
		puts $f "sprlines: $::rx8_frames frames with a line above 8"
		foreach x [lrange $::rx8_log 0 40] { puts $f "  $x" }
		puts $f "satcheck: $::rs_sat_bad frames differ (mux $::rs_sat_mux)"
		foreach x [lrange $::rs_sat_log 0 40] { puts $f "  $x" }
	}
	close $f
	return 1
}

# hz_l2_still_jobs DIR R ?FRAMES? ?DRIVE?: level 2's start on the three machines (C-BIOS_MSX2, the
# FS-A1FX's V9958, the FS-A1GT's R800): the l2 build (R/l2) from the power-on on DRIVE (default lift's,
# build/emu/l2_<DRIVE>.drive), a snapshot (rc2_snap) at the HUD split of the first new list from each
# game frame of FRAMES (default 0 and 50) with level 2's logic bank in lv_cur and the display on, into
# DIR/<m2|fx|tr>/gNNNN (when.txt: the game frame, tick_n, the list, the time; pos.txt: RoboCop's x and
# y, the camera's, lv_cur's logic bank); check them with tools/msxframe.py (build/msx/level2's map and
# tiles; --sprites build/msx/sprites --level 2 --field: the play-field BOBs too) and look at the PNG.
# hz_l2_still_setup's BANK (the label of the level's logic bank, BANK_L1 for level 1 on an EXTJOY
# build) takes the same records of another level.
proc hz_l2_still_jobs {dir R {frames {0 50}} {drive l2_lift}} {
	set e "$::hz_root/build/emu"
	set jobs {}
	foreach {t m} {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT} {
		lappend jobs [list l2st_$t $m [list hz_l2_still_setup "$dir/$t" "$R/l2/rc2_l2.rom" "$R/l2/rc2_l2.labels" \
			"$e/$drive.drive" $frames] {$::hz_l2s_done} 600]
	}
	return $jobs
}

# hz_l2_field_jobs DIR ROM LABELS DRIVE WINDOWS ?MACHINES?: level 2's field records (the plan's 4.2 check
# 2, its step 13): l2b_fd_setup (l2base.tcl, sourced when missing: rc2_jumprec's record and RAM
# 0600h-09FFh, F240h-F27Fh at every picture's HUD split) on ROM (an EXTJOY=1 LV_TEST=2 build) driven by
# DRIVE (a build/emu/l2_<name>.drive), per window {FROM N} (N records from game frame FROM) and machine
# (default C-BIOS_MSX2 m2, the FS-A1FX fx, the FS-A1GT tr): DIR/<FROM>_<tag>. Check each with
# "$PY -I tools/bstest/fieldcheck.py DIR/W build/msx/level2 DIR/W.png --level 2".
proc hz_l2_field_jobs {dir rom labels drive wins {machines {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT}}} {
	if {[info commands l2b_fd_setup] eq ""} { source [file join $::hz_root tools bstest l2base.tcl] }
	set jobs {}
	foreach {t m} $machines {
		foreach {from n} $wins {
			lappend jobs [list fd_${from}_$t $m [list l2b_fd_setup "$dir/${from}_$t" $rom $labels $drive $from $n] \
				{$::l2b_fd_done} 900]
		}
	}
	return $jobs
}

proc hz_l2_still_setup {dir rom labels drive frames {bank BANK_L2}} {
	file mkdir $dir
	set ::hz_l2s_dir $dir
	set ::hz_l2s_want $frames
	set ::hz_l2s_seq -1
	set ::hz_l2s_done 0
	set ::hz_l2s_bank [expr {[rc2_label $labels $bank]}]
	rc2_drive_rom $rom $labels [file join $dir trace.txt] 1 999999 $drive
	set ::hz_l2s_bp [debug probe set_bp VDP.IRQhorizontal {[debug probe read VDP.IRQhorizontal] == 1} hz_l2_still_hit]
}

# (the level's set-up runs with the display off, and a line match still sets the VDP's flag then:
# only a split with the display on counts)
proc hz_l2_still_hit {} {
	if {$::hz_l2s_done || [peek 0xC002] == 0 || ([debug read "VDP regs" 1] & 0x40) == 0} { return }
	set seq [peek 0xC006]
	if {$seq == $::hz_l2s_seq} { return }
	set ::hz_l2s_seq $seq
	set g [lindex $::hz_l2s_want 0]
	if {[peek 0xF1A0] != $::hz_l2s_bank || [rc2_w 0xD000] < $g} { return }
	set d [file join $::hz_l2s_dir [format g%04d $g]]
	rc2_snap $d
	set f [open [file join $d when.txt] w]
	catch {puts $f "game frame [rc2_w 0xD000] tick_n [rc2_w 0xCEE0] seq $seq time [machine_info time]"}
	close $f
	set f [open [file join $d pos.txt] w]
	catch {puts $f "robocop [rc2_w 0xDAD0] [rc2_w 0xDAD4] camera [rc2_w 0xD004] [rc2_w 0xD006] lv_logic [peek 0xF1A0]"}
	close $f
	set ::hz_l2s_want [lrange $::hz_l2s_want 1 end]
	if {[llength $::hz_l2s_want] == 0} {
		catch {debug probe remove_bp $::hz_l2s_bp}
		set ::hz_l2s_done 1
		set ::pause on
	}
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
	hb_init_range $labels
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

# the range after Brainstorm (rgflow.tcl rgh_arm): recorded by hb_step in a build that has it, unless
# the job drives it itself (::hb_range 0 after its set-up)
proc hb_init_range {labels} {
	set ::hb_labels $labels
	set ::hb_range 1
	set ::rgh_on 0
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
				# (the shooting range comes next: its screens recorded, then on as before)
				if {[rgh_arm]} { set ::hb_st 7 }
			}
		}
		7 {
			if {$::rgx_st == 2} {
				set ::hb_tn [rc2_w 0xCEE0]
				set ::hb_st $::rgh_next
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
				if {[info exists ::rgh_on] && $::rgh_on} { rgh_game }
				set ::hb_st 5
				set ::hz_done 1
				set ::pause on
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.05 hb_step]
}
