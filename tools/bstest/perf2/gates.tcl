# gates.tcl (tools/bstest/perf2): the standard jobs of docs/PERF2_PLAN.md 5.4's gates, for hz_chain, on the
# builds of "sh tools/bstest/perf2/gate.sh builds R" (R/l3/cap3.rom EXTJOY=1 LV_TEST=3, R/l2/cap2.rom
# EXTJOY=1 LV_TEST=2, R/l1/ext.rom EXTJOY=1, R/L/l<k>/lock.rom with LOCKSTEP=24, R/T: hz.sh's trace builds).
# HEAD's records of every job are W0's baselines (C/w0/base). The verdicts: gate.sh (shell side).
#
#   pf_speed_jobs DIR R ?TAGS? ?DRIVES?   G-SPEED and G-HOLD: one m3 lean run per drive and machine:
#                                         DIR/<drive>_<tag>_*.txt (win.py, holds.py)
#   pf_field_jobs DIR R ?TAGS? ?LEVELS?   G-FIELD: the field records of each window, with the hold of
#                                         every picture: DIR/<win>_<tag>/ (fieldsum.py)
#   pf_guard_jobs DIR R ?TAGS? ?DRIVES?   G-GUARD: rc2_guard (tears counted), patcheck, sprlines and
#                                         satcheck over a whole drive: DIR/<drive>_<tag>.txt
#   pf_lock_jobs DIR R ?TAGS?             G-LOCK: rc2_disp_rom on the LOCKSTEP=24 builds:
#                                         DIR/<run>_<tag>.txt (+ .over) (tools/dispcmp.py)
#   pf_map_jobs DIR R ?TAGS?              G-MAP: cnt.tcl's map dumps every 100 ticks: DIR/<drive>_<tag>_map.txt
#   pf_logic_jobs DIR R                   G-LOGIC: hz_l3_jobs, hz_l2_jobs (with the turbo R) and level 1's
#                                         cov1/cov0/cov0_tr on R/T: DIR/l3, DIR/l2, DIR/l1 (hz.sh compare),
#                                         each with its lost counters in DIR/l<k>/lost.txt
# TAGS: {tag machine ...}: ::pf_m4 (C-BIOS_MSX2 m2, the Expert ex, the FS-A1FX fx, the FS-A1GT tr),
# ::pf_m3 (m2 fx tr), ::pf_vdp2 (m2 fx: both VDPs). Every job's drive comes from ::pf_emu (build/emu).

set ::pf_m4 {m2 C-BIOS_MSX2 ex Gradiente_Expert20_64K fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT}
set ::pf_m3 {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT}
set ::pf_vdp2 {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX}

# the drives: name -> build (R's sub-path without .rom), drive file, rows
array set ::pf_drives {
	kill   {l3/cap3 l3_kill.drive 1861}
	boss   {l3/cap3 l3_boss.drive 1401}
	tour3  {l3/cap3 l3_tour3.drive 1401}
	park   {l3/cap3 l3_park.drive 1201}
	l2tour {l2/cap2 l2_tour.drive 2654}
	l1play {l1/ext drive_play.txt 1451}
}
set ::pf_speed_drives {kill boss tour3 park l2tour l1play}

proc pf_drive {name} {
	if {![info exists ::pf_drives($name)]} { error "pf: no drive $name ([array names ::pf_drives])" }
	return $::pf_drives($name)
}

proc pf_speed_jobs {dir R {tags ""} {drives ""}} {
	if {$tags eq ""} { set tags $::pf_m4 }
	if {$drives eq ""} { set drives $::pf_speed_drives }
	file mkdir $dir
	set jobs {}
	foreach d $drives {
		lassign [pf_drive $d] b drv n
		foreach {t m} $tags {
			lappend jobs [m3_job ${d}_$t $m $dir "$R/$b.rom" "$R/$b.labels" [file join $::pf_emu $drv] $n lean]
		}
	}
	return $jobs
}

# ----- G-FIELD: the field records (l2base.tcl l2b_fd_setup) with the hold of every picture

# the windows: name, level (fieldcheck.py --level), build, drive, from (game frame), records
set ::pf_field_wins {
	kill300   3 l3/cap3 l3_kill.drive  300 900
	kill1025  3 l3/cap3 l3_kill.drive 1025 900
	kill1560  3 l3/cap3 l3_kill.drive 1560 900
	boss110   3 l3/cap3 l3_boss.drive  110 900
	boss300   3 l3/cap3 l3_boss.drive  300 900
	park40    3 l3/cap3 l3_park.drive   40 900
	tour545   3 l3/cap3 l3_tour3.drive 545 900
	l2t1      2 l2/cap2 l2_tour.drive    1 300
	l2t150    2 l2/cap2 l2_tour.drive  150 300
	l2t495    2 l2/cap2 l2_tour.drive  495 300
	l2t735    2 l2/cap2 l2_tour.drive  735 200
	l2t960    2 l2/cap2 l2_tour.drive  960 250
	l2t1150   2 l2/cap2 l2_tour.drive 1150 300
	l2t1255   2 l2/cap2 l2_tour.drive 1255 350
	l2t2140   2 l2/cap2 l2_tour.drive 2140 260
	l2t2385   2 l2/cap2 l2_tour.drive 2385 400
	l2t2420   2 l2/cap2 l2_tour.drive 2420 400
	l2t2500   2 l2/cap2 l2_tour.drive 2500 300
	l1c430    1 l1/ext  drive_cov0.txt  430 125
	l1c860    1 l1/ext  drive_cov0.txt  860 480
	l1c1490   1 l1/ext  drive_cov0.txt 1490 360
}

proc pf_field_jobs {dir R {tags ""} {levels {1 2 3}} {only ""}} {
	if {$tags eq ""} { set tags $::pf_m3 }
	file mkdir $dir
	set jobs {}
	foreach {w lv b drv from n} $::pf_field_wins {
		if {[lsearch -exact $levels $lv] < 0} continue
		if {$only ne "" && [lsearch -exact $only $w] < 0} continue
		foreach {t m} $tags {
			lappend jobs [list fd_${w}_$t $m [list pf_fd_setup "$dir/${w}_$t" "$R/$b.rom" "$R/$b.labels" \
				[file join $::pf_emu $drv] $from $n $lv] {[pf_fd_done]} 1200]
		}
	}
	return $jobs
}

# l2b_fd_setup's records, and DIR/holds.txt: per record "jNNN_fNNNN fb_hold tick_n" (fb_hold as the picture
# on screen was taken at isr.asm iv_take: FB_HOLD = shown with its play-field BOBs not all composed, the
# class G-HOLD judges), DIR/level.txt (the level for fieldcheck.py)
proc pf_fd_setup {dir rom labels drive from n level} {
	l2b_fd_setup $dir $rom $labels $drive $from $n
	catch {debug probe remove_bp $::l2b_fd_bp}
	set ::l2b_fd_bp [debug probe set_bp VDP.IRQhorizontal {[debug probe read VDP.IRQhorizontal] == 1} pf_fd_hit]
	set ::pf_fd_hold -1
	set ::pf_fd_htick -1
	set ::pf_fd_log {}
	set ::pf_fd_written 0
	set ::pf_fd_fbh [rc2_label $labels fb_hold]
	debug set_bp [rc2_label $labels iv_take] {} {set ::pf_fd_hold [peek $::pf_fd_fbh]; set ::pf_fd_htick [rc2_w 0xCEE0]}
	set f [open [file join $dir level.txt] w]
	catch {puts $f "level $level from $from n $n rom $rom"}
	close $f
}

proc pf_fd_hit {} {
	set k $::l2b_fd_k
	l2b_fd_hit
	if {$::l2b_fd_k != $k} {
		lappend ::pf_fd_log "[format j%03d_f%04d [expr {$k / 60 + 1}] [expr {$k % 60}]] $::pf_fd_hold $::pf_fd_htick [rc2_w 0xCEE0]"
	}
}

proc pf_fd_done {} {
	if {!$::l2b_fd_done} { return 0 }
	if {!$::pf_fd_written} {
		set ::pf_fd_written 1
		set f [open [file join $::l2b_fd_dir holds.txt] w]
		catch { foreach x $::pf_fd_log { puts $f $x } }
		close $f
		set ::pf_fd_log {}
	}
	return 1
}

# ----- G-GUARD: the guard over a whole drive (hz.tcl hz_l2_start_go's checks from the level's first tick)

set ::pf_guard_drives {kill boss}

proc pf_guard_jobs {dir R {tags ""} {drives ""}} {
	if {$tags eq ""} { set tags $::pf_m3 }
	if {$drives eq ""} { set drives $::pf_guard_drives }
	file mkdir $dir
	set jobs {}
	foreach d $drives {
		lassign [pf_drive $d] b drv n
		set bank [expr {[string match l3/* $b] ? "BANK_L3" : ([string match l2/* $b] ? "BANK_L2" : "BANK_L1")}]
		foreach {t m} $tags {
			lappend jobs [list gd_${d}_$t $m [list pf_guard_setup "$dir/${d}_$t.txt" "$R/$b.rom" "$R/$b.labels" \
				"$dir/${d}_${t}_trace.txt" [file join $::pf_emu $drv] $n $bank] {[pf_guard_done]} 1800]
		}
	}
	return $jobs
}

# hz_l2_start_setup's set-up for any level and drive: the guard starts at the level's first tick_start
# (lv_cur = BANK) and runs until the drive's last row (the machine pauses there), then ends
proc pf_guard_setup {out rom labels trace drive rows bank} {
	file delete -- $out                     ;# (an earlier run's record: written again only at the end)
	set ::hz_l2g_out $out
	set ::hz_l2g_rom $rom
	set ::hz_l2g_lab $labels
	set ::hz_l2g_secs 100000
	set ::hz_l2g_n $rows
	set ::hz_l2g 0
	set ::hz_l2g_written 0
	set ::rg_done 0
	unset -nocomplain ::rg_notear
	hz_l2_drive $rom $labels $trace $rows $drive
	set ts [rc2_label $labels tick_start]
	set gt [rc2_label $labels game_tick]
	set bv [expr {[rc2_label $labels $bank]}]
	set lv [rc2_label $labels lv_cur]
	set ::hz_l2g_bp [debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt && \[peek $lv\] == $bv" hz_l2_start_go]
}

proc pf_guard_done {} {
	if {$::hz_l2g == 1 && !$::rg_done && $::rc2_trace_done} { rc2_rg_end }
	return [hz_l2_start_done]
}

# ----- G-LOCK: the LOCKSTEP=24 display records (rc2_disp_rom), both VDPs

# name, build, drive, lists
set ::pf_lock_runs {
	l1cov0  L/l1/lock drive_cov0.txt 3000
	l2tour  L/l2/lock l2_tour.drive  1300
	kill    L/l3/lock l3_kill.drive   900
	boss    L/l3/lock l3_boss.drive   680
}

proc pf_lock_jobs {dir R {tags ""} {only ""}} {
	if {$tags eq ""} { set tags $::pf_vdp2 }
	file mkdir $dir
	set jobs {}
	foreach {r b drv n} $::pf_lock_runs {
		if {$only ne "" && [lsearch -exact $only $r] < 0} continue
		foreach {t m} $tags {
			lappend jobs [list lk_${r}_$t $m [list rc2_disp_rom "$R/$b.rom" "$R/$b.labels" "$dir/${r}_$t.txt" $n \
				[file join $::pf_emu $drv]] "\[l2b_lk_done {$dir/${r}_$t.over}\]" 1800]
		}
	}
	return $jobs
}

# ----- G-MAP: the map's state every 100 ticks (cnt.tcl)

set ::pf_map_drives {tour3 park}

proc pf_map_jobs {dir R {tags ""} {drives ""}} {
	if {$tags eq ""} { set tags $::pf_vdp2 }
	if {$drives eq ""} { set drives $::pf_map_drives }
	file mkdir $dir
	set jobs {}
	foreach d $drives {
		lassign [pf_drive $d] b drv n
		foreach {t m} $tags {
			lappend jobs [cnt_job ${d}_$t $m $dir "$R/$b.rom" "$R/$b.labels" [file join $::pf_emu $drv] $n {} 1]
		}
	}
	return $jobs
}

# ----- G-LOGIC: the logic traces against the Amiga bench (hz.sh compare)

# (level 1's three traces through hz_l2_drive, as levels 2 and 3's: the same rc2_drive_rom trace, plus the
#  lost counters at every tick_start, appended to DIR/l1/lost.txt when the job ends: gate.sh logic wants
#  mp, atr, rd and fb 0 there too)
proc pf_logic_jobs {dir R} {
	set jobs [concat [hz_l3_jobs "$dir/l3" "$R/T" tr] [hz_l2_jobs "$dir/l2" "$R/T" tr]]
	file mkdir "$dir/l1"
	set rom "$R/T/trace/rc2_ext5.rom"
	set lab "$R/T/trace/rc2_ext5.labels"
	set lost [file join $dir l1 lost.txt]
	foreach {j m n drv} {cov1 C-BIOS_MSX2 4401 drive_cov1.txt cov0 Panasonic_FS-A1FX 1400 drive_cov0.txt cov0_tr Panasonic_FS-A1GT 1400 drive_cov0.txt} {
		lappend jobs [list $j $m [list hz_l2_drive $rom $lab "$dir/l1/$j.txt" $n [file join $::pf_emu $drv]] \
			"\$::rc2_trace_done && \[hz_l2_lost {$lost}\]" 900]
	}
	return $jobs
}

# ----- every gate's jobs in one chain

# pf_gate_jobs W R ?GATES?: the jobs of GATES (default all: speed field guard lock map logic) on gate.sh's
# builds R, the records into W/<gate> (G-HOLD reads W/speed); then "gate.sh all BASE W R"
proc pf_gate_jobs {w R {gates {speed field guard lock map logic}}} {
	set jobs {}
	foreach g $gates {
		switch -- $g {
			speed { set jobs [concat $jobs [pf_speed_jobs "$w/speed" $R]] }
			field { set jobs [concat $jobs [pf_field_jobs "$w/field" $R]] }
			guard { set jobs [concat $jobs [pf_guard_jobs "$w/guard" $R]] }
			lock { set jobs [concat $jobs [pf_lock_jobs "$w/lock" $R]] }
			map { set jobs [concat $jobs [pf_map_jobs "$w/map" $R]] }
			logic { set jobs [concat $jobs [pf_logic_jobs "$w/logic" $R]] }
			default { error "pf_gate_jobs: no gate $g" }
		}
	}
	return $jobs
}
