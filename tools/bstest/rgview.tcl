# rgview.tcl: the shooting range's display checks (docs/RANGE.md 4.2 checks 2, 3, 5, 6 and 10;
# docs/HARNESS.md 5.18), for the MSX-AI MCP's openMSX: source load.tcl (it sources this file after
# hz.tcl and hz7.tcl), start one hz_chain, poll "list $::hz_state $::hz_msgs" with short
# msx_local_cmd calls. Never vwait.
#
# Each job runs an EXTJOY=1 PZ_TEST=2 build (PZ_LEVEL=2 for armed2) on a new machine through
# tools/openmsx_rc2.tcl rc2_fr_drive with build/emu/fr_DRIVE.drive from the power-on (level 1's
# set-up, the range's intro, the stage); its trace goes to OUT/tr/NAME.txt (tools/frngcmp.py).
#
#   rgv_job NAME MACHINE ROM LABELS DRIVE OUT ?PASSES? ?REC? ?RFROM? ?TAIL?
#       snapshots at the passes ($B00 at fr_tick: between two passes) in PASSES:
#       OUT/st/NAME/pNNNN.bin (hz7.tcl hz7_snap's layout: VRAM, RAM C000h-FFFFh, the VDP registers,
#       the palette); with REC > 0 a record of REC VBLANKs at most from pass RFROM on, and TAIL more
#       past the drive's end (fr_rated: the result's or OUT OF TIME.'s screen next):
#       OUT/st/NAME/rec.bin, rgv_pic's layout (tools/bstest/rgview.py still / rec)
#   rgv_guard_job NAME MACHINE ROM LABELS DRIVE OUT FROM SECS NL
#       the display guard (rc2_guard, tear counting on) for SECS emulated seconds from pass FROM,
#       NL lines a frame (262 at 60 Hz, 313 at 50 Hz): OUT/flow/NAME.txt; the drive then runs on
#       to its end
#   rgv_fast_job NAME MACHINE ROM LABELS DRIVE OUT FREQ
#       the VRAM accesses lost to a too fast CPU (rc2_count_too_fast, the Z80 at FREQ Hz; ft.tcl's
#       ft_clock and ft_classify) from the power-on (the BIOS, level 1's set-up, the range's intro,
#       the stage's entry uploads, its passes, its exit) to fr_rated: OUT/flow/NAME.txt
#   rgv_rate_job NAME MACHINE ROM LABELS DRIVE OUT
#       per pass: tick (the VBLANK count) at fr_tick, the emulated times at the loop's work's start
#       (rg_loop + 3: rg_wait returned), at fr_tick, after fr_frame (fr_tick + 3) and after the
#       pass's rg_feed (fr_tick + 6), and the active CPU: OUT/flow/NAME_rate.txt (rgview.py rate)
#
# Rules kept: no exit, vwait, max or min; every file opened once and closed on every path (hz.tcl
# hz_clean closes ::rv_rf and ::rv_tf when a job times out).

proc rgv_drive {rom labels out name drive} {
	file mkdir "$out/tr"
	rc2_fr_drive $rom $labels "$out/tr/$name.txt" 3000 0 "$::hz_root/build/emu/fr_$drive.drive"
}

# the condition of a breakpoint at fr_tick: the stage's bank holds "call fr_frame" there
proc rgv_tickcond {labels} {
	set a [rc2_label $labels fr_tick]
	set t [rc2_label $labels fr_frame]
	return [list $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t"]
}

# ----- snapshots and the record

proc rgv_job {name m rom labels drive out {passes {}} {rec 0} {rfrom 0} {tail 0}} {
	set setup "rgv_drive {$rom} {$labels} {$out} {$name} {$drive}; rgv_arm {$out/st/$name} {$labels} {$passes} $rec $rfrom $tail"
	return [list $name $m [list eval $setup] {[rgv_done]} 900]
}

proc rgv_arm {dir labels passes {rec 0} {rfrom 0} {tail 0}} {
	file mkdir $dir
	set ::rv_dir $dir
	set ::rv_passes $passes
	set ::rv_rec $rec
	set ::rv_rfrom $rfrom
	set ::rv_tail $tail
	set ::rv_tailon 0
	set ::rv_recn 0
	set ::rv_recdone [expr {$rec > 0 ? 0 : 1}]
	set ::rv_ivl [rc2_label $labels iv_late]
	lassign [rgv_tickcond $labels] a cond
	set ::rv_bp [debug set_bp $a $cond rgv_tick]
	set ::rv_rbp ""
	return "armed"
}

proc rgv_tick {} {
	set f [rc2_w 0xD000]
	if {[lsearch -exact $::rv_passes $f] >= 0} { hz7_snap $::rv_dir [format p%04d $f] }
	if {$::rv_rec > 0 && $::rv_rbp eq "" && !$::rv_recdone && $f >= $::rv_rfrom} {
		set ::rv_rf [open "$::rv_dir/rec.bin" w]
		fconfigure $::rv_rf -translation binary
		set ::rv_rbp [debug set_bp $::rv_ivl {} rgv_pic]
	}
}

# One VBLANK, once its list is applied (iv_late; layout in rgview.py REC): the VDP registers, R#2's
# page lines 0-161, R#5's SAT (32 entries), pf_pal, the list, RAM C000h-C0FFh, C600h-C6FFh,
# D000h-D0FFh (the mirror's $B00 on), EE00h-EFFFh (the wanted state, both pages' shown states, the
# build's target, its rectangles, the elements).
proc rgv_pic {} {
	if {![info exists ::rv_rf]} return
	set regs ""
	for {set i 0} {$i < 64} {incr i} { append regs [binary format cu [debug read "VDP regs" $i]] }
	set page [expr {([debug read "VDP regs" 2] >> 5) & 3}]
	set sat [expr {(([debug read "VDP regs" 11] & 3) << 15) | (([debug read "VDP regs" 5] & 0xFC) << 7)}]
	set lp [rc2_w 0xC003]
	puts -nonewline $::rv_rf $regs
	puts -nonewline $::rv_rf [debug read_block "physical VRAM" [expr {$page * 0x8000}] 20736]
	puts -nonewline $::rv_rf [debug read_block "physical VRAM" $sat 128]
	puts -nonewline $::rv_rf [debug read_block memory 0xEA40 32]
	puts -nonewline $::rv_rf [debug read_block memory $lp 32]
	puts -nonewline $::rv_rf [debug read_block memory 0xC000 256]
	puts -nonewline $::rv_rf [debug read_block memory 0xC600 256]
	puts -nonewline $::rv_rf [debug read_block memory 0xD000 256]
	puts -nonewline $::rv_rf [debug read_block memory 0xEE00 512]
	incr ::rv_recn
	if {$::rv_tailon} {
		incr ::rv_tail -1
		if {$::rv_tail <= 0} {
			rgv_recend
			set ::pause on
		}
	} elseif {$::rv_recn >= $::rv_rec} {
		rgv_recend
	}
}

proc rgv_recend {} {
	if {$::rv_rbp ne ""} { catch {debug remove_bp $::rv_rbp} }
	set ::rv_rbp ""
	if {[info exists ::rv_rf]} { catch {close $::rv_rf}; unset ::rv_rf }
	set ::rv_recdone 1
}

# the job's done condition: the drive ended (rc2_fr_drive paused the machine at fr_rated); a record
# still open with a TAIL goes on that many VBLANKs (the machine resumed) and ends; the files closed
proc rgv_done {} {
	if {!$::rc2_trace_done} { return 0 }
	if {!$::rv_recdone && $::rv_tail > 0 && $::rv_rbp ne ""} {
		if {!$::rv_tailon} {
			set ::rv_tailon 1
			catch {debug remove_bp $::rv_bp}
			set ::pause off
		}
		return 0
	}
	catch {debug remove_bp $::rv_bp}
	rgv_recend
	return 1
}

# ----- the display guard

proc rgv_guard_job {name m rom labels drive out from secs nl} {
	file mkdir "$out/flow"
	set setup "rgv_drive {$rom} {$labels} {$out} {$name} {$drive}; rgv_guard_arm {$labels} $from $secs $nl {$out/flow/$name.txt}"
	return [list $name $m [list eval $setup] {$::rc2_trace_done} 900]
}

proc rgv_guard_arm {labels from secs nl file} {
	set ::rvg_labels $labels
	set ::rvg_from $from
	set ::rvg_secs $secs
	set ::rvg_nl $nl
	set ::rvg_file $file
	set ::rvg_on 0
	lassign [rgv_tickcond $labels] a cond
	set ::rvg_bp [debug set_bp $a $cond rgv_g_tick]
}

proc rgv_g_tick {} {
	if {$::rvg_on || [rc2_w 0xD000] < $::rvg_from} return
	set ::rvg_on 1
	catch {debug remove_bp $::rvg_bp}
	unset -nocomplain ::rg_notear
	rc2_guard $::rvg_secs 157 $::rvg_nl 162 $::rvg_labels
	set ::rvg_t0 [machine_info time]
	lappend ::hz_afters [after realtime 0.5 rgv_g_poll]
}

proc rgv_g_poll {} {
	if {[info exists ::rg_done] && $::rg_done} {
		set f [open $::rvg_file w]
		catch {
			puts $f "guard from pass $::rvg_from (emulated [format %.3f $::rvg_t0] s) for $::rvg_secs s, to pass [rc2_w 0xD000]: frames $::rg_frames, commands $::rg_cmds"
			foreach k {reg pal cmd cpu vbl tear} { puts $f "$k $::rg_n($k)" }
			foreach l $::rg_log { puts $f $l }
		}
		close $f
		set ::rg_done 0
		set ::pause off
		return
	}
	lappend ::hz_afters [after realtime 0.5 rgv_g_poll]
}

# ----- VRAM access speed

proc rgv_fast_job {name m rom labels drive out freq} {
	file mkdir "$out/flow"
	return [list $name $m [list rgv_fast_setup $name $rom $labels $drive $out $freq] {[rgv_fast_done]} 900]
}

proc rgv_fast_setup {name rom labels drive out freq} {
	ft_clock $freq
	set ::too_fast_vram_access real
	rc2_count_too_fast
	ft_classify
	rgv_drive $rom $labels $out $name $drive
	set ::rvf_file "$out/flow/$name.txt"
}

proc rgv_fast_done {} {
	if {!$::rc2_trace_done} { return 0 }
	set f [open $::rvf_file w]
	catch {puts $f "too fast VRAM accesses: $::rc2_too_fast (the BIOS's $::ft_bios: $::ft_bl; the cartridge's $::ft_cart: $::ft_cl) with the Z80 at [set ::z80_freq] Hz; result $::rc2_fr_result, rating $::rc2_fr_rating, passes [rc2_w 0xD000]"}
	close $f
	set {::VDP.too_fast_vram_access_callback} {}
	return 1
}

# ----- the pass rate

proc rgv_rate_job {name m rom labels drive out} {
	file mkdir "$out/flow"
	return [list $name $m [list rgv_rate_setup $name $rom $labels $drive $out] {[rgv_rate_done]} 900]
}

proc rgv_rate_setup {name rom labels drive out} {
	set ::rvr_tickv [rc2_label $labels tick]
	set loop [rc2_label $labels rg_loop]
	rgv_drive $rom $labels $out $name $drive
	lassign [rgv_tickcond $labels] a cond
	set ::rvr_w 0
	set ::rvr_t 0
	set ::rvr_e 0
	set ::rv_tf [open "$out/flow/${name}_rate.txt" w]
	set ::rvr_bps [list [debug set_bp [expr {$loop + 3}] $cond {set ::rvr_w [machine_info time]}] \
		[debug set_bp $a $cond {set ::rvr_t [machine_info time]}] \
		[debug set_bp [expr {$a + 3}] $cond {set ::rvr_e [machine_info time]}] \
		[debug set_bp [expr {$a + 6}] $cond rgv_r_out]]
}

proc rgv_r_out {} {
	if {![info exists ::rv_tf]} return
	catch {puts $::rv_tf [format "%d %.9f %.9f %.9f %.9f %s" [peek $::rvr_tickv] $::rvr_w $::rvr_t $::rvr_e [machine_info time] [get_active_cpu]]}
}

proc rgv_rate_done {} {
	if {!$::rc2_trace_done} { return 0 }
	foreach b $::rvr_bps { catch {debug remove_bp $b} }
	if {[info exists ::rv_tf]} { catch {close $::rv_tf}; unset ::rv_tf }
	return 1
}

# ----- traces alone

# rgv_tjob NAME MACHINE ROM LABELS DRIVE OUT N: the drive's trace (N passes at most) into OUT/tr/NAME.txt
proc rgv_tjob {name m rom labels drive out n} {
	file mkdir "$out/tr"
	return [list $name $m [list rc2_fr_drive $rom $labels "$out/tr/$name.txt" $n 0 "$::hz_root/build/emu/fr_$drive.drive"] {$::rc2_trace_done} 900]
}

# ----- the restore and the next game (docs/RANGE.md 4.2 check 7)

# rgv_after_setup DIR TAG ROM LABELS DRIVE: an EXTJOY=1 PZ_TEST=2 build with DRIVE (timeout: the
# stage times out at its pass 301, its palette lit): DIR/TAG_intro.bin once the range's intro is
# complete (fs_n 150), the stage (its trace DIR/TAG_fr.txt), DIR/TAG_result.bin at OUT OF TIME.'s
# fs_n 80, the new game's frame 50 (DIR/TAG_g50.bin) and rc2_snaps DIR/TAG_snaps (6, 0.5 s apart:
# tools/checkrun.py); notes DIR/TAG_after.txt with the lost counters (hz7.tcl hz7_g50_arm,
# hz7a_note, hz7a_rt5). Against hz7_fresh_setup's fresh start of an EXTJOY=1 build:
# restorecheck.py DIR TAG FRESH --known --range.
proc rgv_after_setup {dir tag rom labels drive} {
	set ::h7a_dir $dir
	set ::h7a_tag $tag
	set ::h7a_labels $labels
	set ::rc2_snaps_done 0
	set ::rva_intro [rgv_span $labels txt_rg_intro]
	set ::rva_res [rgv_span $labels txt_bs_time]
	set ::rva_st 0
	set ::hz_done 0
	rc2_fr_drive $rom $labels "$dir/${tag}_fr.txt" 3000 0 "$::hz_root/build/emu/fr_$drive.drive"
	lappend ::hz_afters [after time 0.05 rgva_step]
	lappend ::hz_afters [after realtime 0.5 rgva_rt]
}

# LABELS' address of the text NAME and the next text's above it (the txt_ labels: the scripts follow
# one another in FRONT; other banks' labels share those addresses): the span of NAME's script
proc rgv_span {labels name} {
	set lo [rc2_label $labels $name]
	set hi 0x10000
	set f [open $labels r]
	catch {
		while {[gets $f line] >= 0} {
			if {[regexp {^(txt_\w+):\s+equ\s+\$([0-9a-fA-F]+)} $line -> n v]} {
				set v [expr {"0x$v"}]
				if {$v > $lo && $v < $hi} { set hi $v }
			}
		}
	}
	close $f
	return [list $lo $hi]
}

proc rgva_step {} {
	set p [rc2_w 0xCFB8]
	set n [rc2_w 0xCFBE]
	switch -- $::rva_st {
		0 {
			lassign $::rva_intro lo hi
			if {$p >= $lo && $p < $hi && $n >= 150} {
				hz7_snap $::h7a_dir ${::h7a_tag}_intro
				hz7a_note "intro at [machine_info time] s"
				set ::rva_st 1
				return
			}
		}
		2 {
			lassign $::rva_res lo hi
			if {$p >= $lo && $p < $hi && $n >= 80 && $n < 100} {
				hz7_snap $::h7a_dir ${::h7a_tag}_result
				hz7a_note "result at [machine_info time] s, fs_n $n"
				hz7_g50_arm
				set ::rva_st 3
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.05 rgva_step]
}

# (the stage's end paused the machine at fr_rated: resumed, ext_joy 0)
proc rgva_rt {} {
	if {$::rva_st == 1 && $::rc2_trace_done} {
		hz7a_note "stage done at [machine_info time] s: result $::rc2_fr_result, rating $::rc2_fr_rating, passes [rc2_w 0xD000]"
		poke 0xCE5A 0
		set ::rva_st 2
		set ::pause off
		lappend ::hz_afters [after time 0.05 rgva_step]
		return
	}
	if {$::rva_st < 2} { lappend ::hz_afters [after realtime 0.5 rgva_rt] }
}

# ----- the whole set

# rgv_suite W: the jobs of docs/HARNESS.md 5.18 on the builds of "rgview.sh builds W" (W/fr2:
# EXTJOY=1 PZ_TEST=2; W/fr2v2: + PZ_LEVEL=2; W/ext: EXTJOY=1), outputs into W/O (tr/, st/, flow/):
#   - armed, mixed, edge, timeout and armed2 with their snapshots and whole records (3,000 VBLANKs at
#     most, 150 more past the end) on C-BIOS_MSX2 (_m2), the Panasonic FS-A1FX (_fx) and FS-A1GT (_tr);
#   - the display guard over armed's passes 5 to about 1,130 on the three (guard_...);
#   - the VRAM speed over armed from the power-on at 3.58 MHz (C-BIOS_MSX2, FS-A1GT) and 5.37 MHz
#     (FS-A1FX, C-BIOS_MSX2+): fast_m2, fast_tr, fast_fx, fast_p2;
#   - the pass rate of armed, mixed and edge at 60 and 50 Hz (rate_..._m2, rate_..._eu);
#   - the other ten drives' traces on C-BIOS_MSX2 and the FS-A1GT, armed and opp on the Gradiente
#     Expert 2.0 (_ex);
#   - the restore after timeout's time out and the new game against a fresh start (after_rg_...,
#     fresh_rg_... on C-BIOS_MSX2 and the FS-A1GT).
# 54 jobs, a few minutes; poll "list $::hz_state [llength $::hz_msgs] [lindex $::hz_msgs end]".
proc rgv_suite {w} {
	set o "$w/O"
	foreach d {tr st flow} { file mkdir "$o/$d" }
	set r "$w/fr2/rc2.rom"; set l "$w/fr2/rc2.labels"
	set r2 "$w/fr2v2/rc2.rom"; set l2 "$w/fr2v2/rc2.labels"
	set snaps {
		armed {4 5 6 7 8 18 20 22 26 27 28 29 30 31 32 33 34 35 36 84 86 88 90 92 128 130 132 134 136 298 300 302 700 1100 1140 1150 1155 1160 1162}
		mixed {6 20 28 30 32 34 86 90 130 134 300 600 900 1200 1500 1800 1840 1860 1868}
		edge {6 20 32 33 34 40 41 45 50 117 120 200 300 340 343}
		timeout {6 20 30 100 200 290 295 299 300}
		armed2 {5 6 8 20 30 32 90 130 300 700 1140 1162}
	}
	set jobs {}
	foreach {tag m} {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT} {
		foreach d {armed mixed edge timeout} {
			lappend jobs [rgv_job ${d}_$tag $m $r $l $d $o [dict get $snaps $d] 3000 1 150]
		}
		lappend jobs [rgv_job armed2_$tag $m $r2 $l2 armed2 $o [dict get $snaps armed2] 3000 1 150]
		lappend jobs [rgv_guard_job guard_$tag $m $r $l armed $o 5 22.5 262]
	}
	foreach {tag m f} {m2 C-BIOS_MSX2 3579545 tr Panasonic_FS-A1GT 3579545 fx Panasonic_FS-A1FX 5369318 p2 C-BIOS_MSX2+ 5369318} {
		lappend jobs [rgv_fast_job fast_$tag $m $r $l armed $o $f]
	}
	foreach {tag m} {m2 C-BIOS_MSX2 eu C-BIOS_MSX2_EU} {
		foreach d {armed mixed edge} { lappend jobs [rgv_rate_job rate_${d}_$tag $m $r $l $d $o] }
	}
	foreach {tag m} {m2 C-BIOS_MSX2 tr Panasonic_FS-A1GT} {
		foreach d {dummy poor fair good good_min0 late_timeout hold fuzz quirk4} {
			lappend jobs [rgv_tjob ${d}_$tag $m $r $l $d $o 3000]
		}
		lappend jobs [rgv_tjob opp_$tag $m $r $l opp $o 81]
	}
	lappend jobs [rgv_tjob armed_ex Gradiente_Expert20_64K $r $l armed $o 3000]
	lappend jobs [rgv_tjob opp_ex Gradiente_Expert20_64K $r $l opp $o 81]
	foreach {tag m} {m2 C-BIOS_MSX2 tr Panasonic_FS-A1GT} {
		lappend jobs [list after_rg_$tag $m [list rgv_after_setup "$o/flow" after_rg_$tag $r $l timeout] {$::hz_done} 600]
		lappend jobs [list fresh_rg_$tag $m [list hz7_fresh_setup "$o/flow" fresh_rg_$tag "$w/ext/rc2.rom" "$w/ext/rc2.labels"] {$::hz_done} 600]
	}
	return $jobs
}
