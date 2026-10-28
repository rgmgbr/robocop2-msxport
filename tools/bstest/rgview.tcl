# rgview.tcl: the shooting range's display checks (docs/RANGE.md 4.2 checks 2-6 and 10;
# docs/HARNESS.md 5.18), for the MSX-AI MCP's openMSX: source load.tcl (it sources this file after
# hz.tcl and hz7.tcl), start one hz_chain, poll "list $::hz_state $::hz_msgs" with short
# msx_local_cmd calls. Never vwait.
#
# Each job runs an EXTJOY=1 PZ_TEST=2 build (PZ_LEVEL=2 for armed2) on a new machine through
# tools/openmsx_rc2.tcl rc2_fr_drive with build/emu/fr_DRIVE.drive from the power-on (level 1's
# set-up, the range's intro, the stage); its trace goes to OUT/tr/NAME.txt (tools/frngcmp.py).
#
#   rgv_job NAME MACHINE ROM LABELS DRIVE OUT ?PASSES? ?REC? ?RFROM? ?TAIL? ?POKES? ?PROBE?
#       snapshots at the passes ($B00 at fr_tick: between two passes) in PASSES:
#       OUT/st/NAME/pNNNN.bin (hz7.tcl hz7_snap's layout: VRAM, RAM C000h-FFFFh, the VDP registers,
#       the palette); with REC > 0 a record of REC VBLANKs at most from pass RFROM on, and TAIL more
#       past the drive's end (fr_rated: the result's or OUT OF TIME.'s screen next):
#       OUT/st/NAME/rec.bin, rgv_pic's layout (tools/bstest/rgview.py still / rec); POKES {P S ...}:
#       the camera s set to S once a pass has made $B00 = P (rgv_poke_arm: OUT/st/NAME/campoke.txt,
#       rgview.py --campoke); PROBE 1: the HUD's register probe (rgv_probe_arm:
#       OUT/st/NAME/probe.txt, rgview.py probe), 2: the same with split_list + 8 put back to 9Bh at
#       the first pass (the negative control on a V9958)
#   rgv_guard_job NAME MACHINE ROM LABELS DRIVE OUT FROM SECS NL ?POKES?
#       the display guard (rc2_guard, tear counting on) for SECS emulated seconds from pass FROM,
#       NL lines a frame (262 at 60 Hz, 313 at 50 Hz): OUT/flow/NAME.txt; the drive then runs on
#       to its end; POKES as rgv_job's
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

proc rgv_job {name m rom labels drive out {passes {}} {rec 0} {rfrom 0} {tail 0} {pokes {}} {probe 0}} {
	set setup "rgv_drive {$rom} {$labels} {$out} {$name} {$drive}; rgv_arm {$out/st/$name} {$labels} {$passes} $rec $rfrom $tail {$pokes} $probe"
	return [list $name $m [list eval $setup] {[rgv_done]} 900]
}

proc rgv_arm {dir labels passes {rec 0} {rfrom 0} {tail 0} {pokes {}} {probe 0}} {
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
	rgv_poke_arm $dir $labels $pokes
	set ::rvp_on -1
	if {$probe} { rgv_probe_arm $dir $labels [expr {$probe == 2}] }
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
	rgv_poke_end
	rgv_p_end
	return 1
}

# ----- the camera's pokes (docs/RANGE.md 4.2 checks 2 and 4: s = 7, s = 8, a sweep of 0-64)

# POKES {P S ...}: once a pass has made $B00 = P (fr_tick + 3: fr_frame returned, rg_feed next, so
# the builds of that pass's state take it), the wanted state's camera (rg_want + RG_ST_S) = S; with
# DIR, DIR/campoke.txt "P:S,..." for rgview.py --campoke. The crosshair held in the view's middle
# band keeps that s (msx/frng.asm rg_cam).
proc rgv_poke_arm {dir labels pokes} {
	set ::rvk_pokes $pokes
	set ::rvk_bp ""
	if {![llength $pokes]} return
	set ::rvk_addr [expr {[rc2_label $labels rg_want] + [rc2_label $labels RG_ST_S]}]
	lassign [rgv_tickcond $labels] a cond
	set ::rvk_bp [debug set_bp [expr {$a + 3}] $cond rgv_k_hit]
	if {$dir ne ""} {
		set l {}
		foreach {q s} $pokes { lappend l "$q:$s" }
		set f [open "$dir/campoke.txt" w]
		catch {puts $f [join $l ,]}
		close $f
	}
}

proc rgv_k_hit {} {
	set f [rc2_w 0xD000]
	foreach {q s} $::rvk_pokes {
		if {$q == $f} { poke $::rvk_addr $s }
	}
}

proc rgv_poke_end {} {
	if {[info exists ::rvk_bp] && $::rvk_bp ne ""} { catch {debug remove_bp $::rvk_bp} }
	set ::rvk_bp ""
}

# ----- the HUD under R#18 (docs/RANGE.md 4.2 check 4)

# From the stage's first pass to the job's end: at the HUD split's end (sp_r19, after its timed
# writes) R#18 must be 0 (the V9938's split list writes it; on a V9958 split_list + 8 makes its last
# write R#18's: msx/frngview.asm rg_show); at each VBLANK once its list is in (iv_late) R#18 must be
# the applied list's. A shift is a register's effect that no VRAM snapshot shows, so the probe reads
# the register. NEG 1 (the negative control): split_list + 8 put back to 9Bh (R#27) at the first
# pass, so that a V9958 must report the shifted HUD. DIR/probe.txt at the end (rgview.py probe).
proc rgv_probe_arm {dir labels neg} {
	set ::rvp_file "$dir/probe.txt"
	set ::rvp_neg $neg
	set ::rvp_on 0
	foreach k {frames shifted hud late splits vblanks} { set ::rvp_n($k) 0 }
	array unset ::rvp_sh
	set ::rvp_lv 0
	set ::rvp_sl [rc2_label $labels split_list]
	set ::rvp_msk [rc2_label $labels hud_msk]
	set ::rvp_ring [rc2_label $labels rgr_ring]
	set ::rvp_n(ring) 0
	set ::rvp_l27 0
	lassign [rgv_tickcond $labels] a cond
	set ::rvp_tbp [debug set_bp $a $cond rgv_p_tick]
	set ::rvp_bps [list [debug set_bp [rc2_label $labels sp_r19] {} rgv_p_split] \
		[debug set_bp [rc2_label $labels iv_late] {} rgv_p_vbl]]
}

proc rgv_p_tick {} {
	if {$::rvp_on} return
	set ::rvp_on 1
	# (the V9958's ring keeps R#18 at 0 and scrolls by R#27: its control turns the split's R#27 = 0
	# into R#18 = 0, so that R#27 stays the play area's)
	if {$::rvp_neg} { poke [expr {$::rvp_sl + 8}] [expr {[peek $::rvp_ring] ? 0x92 : 0x9B}] }
	catch {debug remove_bp $::rvp_tbp}
}

proc rgv_p_vbl {} {
	if {$::rvp_on != 1} return
	incr ::rvp_n(vblanks)
	set lp [rc2_w 0xC003]
	set n [peek [expr {$lp + 1}]]
	set lv 0
	set r25 0
	set r27 0
	for {set i 0} {$i < $n} {incr i 2} {
		set r [expr {[peek [expr {$lp + 3 + $i}]] & 0x3F}]
		set v [peek [expr {$lp + 2 + $i}]]
		if {$r == 18} { set lv $v }
		if {$r == 25} { set r25 $v }
		if {$r == 27} { set r27 $v }
	}
	set ::rvp_lv $lv
	set ::rvp_l27 [expr {($r25 & 2) ? $r27 : 0}]
	if {$r25 & 2} { incr ::rvp_n(ring) }
	if {[debug read "VDP regs" 18] != $lv} { incr ::rvp_n(late) }
}

proc rgv_p_split {} {
	if {$::rvp_on != 1} return
	incr ::rvp_n(splits)
	incr ::rvp_n(frames)
	set sh [expr {$::rvp_lv ? $::rvp_lv : $::rvp_l27}]
	if {$sh} {
		incr ::rvp_n(shifted)
		if {[info exists ::rvp_sh($sh)]} { incr ::rvp_sh($sh) } else { set ::rvp_sh($sh) 1 }
	}
	if {[debug read "VDP regs" 18] || [debug read "VDP regs" 27] || ([debug read "VDP regs" 25] & 2)} {
		incr ::rvp_n(hud)
	}
}

proc rgv_p_end {} {
	if {![info exists ::rvp_on] || $::rvp_on < 0} return
	foreach b $::rvp_bps { catch {debug remove_bp $b} }
	catch {debug remove_bp $::rvp_tbp}
	set sh {}
	foreach k [lsort -integer [array names ::rvp_sh]] { lappend sh "[format %02X $k]h:$::rvp_sh($k)" }
	set f [open $::rvp_file w]
	catch {
		foreach k {frames shifted hud late splits vblanks} { puts $f "$k $::rvp_n($k)" }
		puts $f "msk [peek $::rvp_msk]"
		puts $f "shifts [join $sh { }]"
		puts $f "neg $::rvp_neg"
		puts $f "ring $::rvp_n(ring)"
	}
	close $f
	set ::rvp_on -1
}

# ----- the display guard

proc rgv_guard_job {name m rom labels drive out from secs nl {pokes {}}} {
	file mkdir "$out/flow"
	set setup "rgv_drive {$rom} {$labels} {$out} {$name} {$drive}; rgv_guard_arm {$labels} $from $secs $nl {$out/flow/$name.txt}; rgv_poke_arm {} {$labels} {$pokes}"
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
# EXTJOY=1 PZ_TEST=2; W/fr2v2: + PZ_LEVEL=2; W/fr2n: + RG_ADJ=0; W/ext: EXTJOY=1), outputs into W/O
# (tr/, st/, flow/):
#   - armed, mixed, edge, timeout and armed2 with their snapshots, whole records (3,000 VBLANKs at
#     most, 150 more past the end) and the HUD's register probe on C-BIOS_MSX2 (_m2), the Panasonic
#     FS-A1FX (_fx) and FS-A1GT (_tr);
#   - the camera held at s = 7 and s = 8 (hold7_, hold8_: shifts -7 and +8, R#18's ends) and swept
#     over s = 0-64 (sweep_), on the hold drive (the crosshair still) with the camera poked: snapshots,
#     records and the probe on the three; the probe alone on armed, hold7 and hold8 on the Gradiente
#     Expert 2.0 (_ex) and the Sony HB-F1XDJ (_xd, its 128K Lite set-up); its negative control
#     (split_list + 8 back to 9Bh: neg8_) on the three V9958 machines (FS-A1FX, HB-F1XDJ, FS-A1GT);
#   - the RG_ADJ=0 build (16-px camera steps, R#18 0): armed, mixed, edge, timeout with snapshots
#     and records on C-BIOS_MSX2 and the FS-A1GT (_m2n, _trn);
#   - the display guard over armed's passes 5 to about 1,130 on the three (guard_...), and over the
#     sweep on the HB-F1XDJ (guard_sweep_xd);
#   - the VRAM speed over armed from the power-on at 3.58 MHz (C-BIOS_MSX2, FS-A1GT) and 5.37 MHz
#     (FS-A1FX, C-BIOS_MSX2+): fast_m2, fast_tr, fast_fx, fast_p2;
#   - the pass rate of armed, mixed and edge at 60 and 50 Hz (rate_..._m2, rate_..._eu), armed on
#     the FS-A1GT (rate_armed_tr);
#   - the other ten drives' traces on C-BIOS_MSX2 and the FS-A1GT, opp on the Expert;
#   - the restore after timeout's time out and the new game against a fresh start (after_rg_...,
#     fresh_rg_... on C-BIOS_MSX2 and the FS-A1GT).
# 81 jobs, 15-25 minutes; poll "list $::hz_state [llength $::hz_msgs] [lindex $::hz_msgs end]".
proc rgv_suite {w} {
	set o "$w/O"
	foreach d {tr st flow} { file mkdir "$o/$d" }
	set r "$w/fr2/rc2.rom"; set l "$w/fr2/rc2.labels"
	set r2 "$w/fr2v2/rc2.rom"; set l2 "$w/fr2v2/rc2.labels"
	set rn "$w/fr2n/rc2.rom"; set ln "$w/fr2n/rc2.labels"
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
			lappend jobs [rgv_job ${d}_$tag $m $r $l $d $o [dict get $snaps $d] 3000 1 150 {} 1]
		}
		lappend jobs [rgv_job armed2_$tag $m $r2 $l2 armed2 $o [dict get $snaps armed2] 3000 1 150 {} 1]
		lappend jobs [rgv_guard_job guard_$tag $m $r $l armed $o 5 22.5 262]
	}
	set hold7 {2 7}
	set hold8 {2 8}
	set sweep {}
	set sweepst {}
	for {set k 0} {$k <= 64} {incr k} {
		lappend sweep [expr {10 + 10 * $k}] $k
		lappend sweepst [expr {19 + 10 * $k}]
	}
	set holdst {20 40 60 100 200 300 500 700 728}
	foreach {tag m} {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT} {
		lappend jobs [rgv_job hold7_$tag $m $r $l hold $o $holdst 3000 1 150 $hold7 1]
		lappend jobs [rgv_job hold8_$tag $m $r $l hold $o $holdst 3000 1 150 $hold8 1]
		lappend jobs [rgv_job sweep_$tag $m $r $l hold $o $sweepst 3000 1 150 $sweep 1]
	}
	foreach {tag m} {ex Gradiente_Expert20_64K xd Sony_HB-F1XDJ_128K_Lite} {
		lappend jobs [rgv_job armed_$tag $m $r $l armed $o {} 0 0 0 {} 1]
		lappend jobs [rgv_job hold7_$tag $m $r $l hold $o {} 0 0 0 $hold7 1]
		lappend jobs [rgv_job hold8_$tag $m $r $l hold $o {} 0 0 0 $hold8 1]
	}
	foreach {tag m} {fx Panasonic_FS-A1FX xd Sony_HB-F1XDJ_128K_Lite tr Panasonic_FS-A1GT} {
		# (held at s = 7: R#18 7 on the R#18 path, R#27 1 on the V9958's ring, whose s = 8 scrolls by
		# whole 8-column steps only)
		lappend jobs [rgv_job neg8_$tag $m $r $l hold $o {} 0 0 0 $hold7 2]
	}
	foreach {tag m} {m2n C-BIOS_MSX2 trn Panasonic_FS-A1GT} {
		foreach d {armed mixed edge timeout} {
			lappend jobs [rgv_job ${d}_$tag $m $rn $ln $d $o [dict get $snaps $d] 3000 1 150]
		}
	}
	lappend jobs [rgv_guard_job guard_sweep_xd Sony_HB-F1XDJ_128K_Lite $r $l hold $o 5 13 262 $sweep]
	foreach {tag m f} {m2 C-BIOS_MSX2 3579545 tr Panasonic_FS-A1GT 3579545 fx Panasonic_FS-A1FX 5369318 p2 C-BIOS_MSX2+ 5369318} {
		lappend jobs [rgv_fast_job fast_$tag $m $r $l armed $o $f]
	}
	foreach {tag m} {m2 C-BIOS_MSX2 eu C-BIOS_MSX2_EU} {
		foreach d {armed mixed edge} { lappend jobs [rgv_rate_job rate_${d}_$tag $m $r $l $d $o] }
	}
	lappend jobs [rgv_rate_job rate_armed_tr Panasonic_FS-A1GT $r $l armed $o]
	foreach {tag m} {m2 C-BIOS_MSX2 tr Panasonic_FS-A1GT} {
		foreach d {dummy poor fair good good_min0 late_timeout hold fuzz quirk4} {
			lappend jobs [rgv_tjob ${d}_$tag $m $r $l $d $o 3000]
		}
		lappend jobs [rgv_tjob opp_$tag $m $r $l opp $o 81]
	}
	lappend jobs [rgv_tjob opp_ex Gradiente_Expert20_64K $r $l opp $o 81]
	foreach {tag m} {m2 C-BIOS_MSX2 tr Panasonic_FS-A1GT} {
		lappend jobs [list after_rg_$tag $m [list rgv_after_setup "$o/flow" after_rg_$tag $r $l timeout] {$::hz_done} 600]
		lappend jobs [list fresh_rg_$tag $m [list hz7_fresh_setup "$o/flow" fresh_rg_$tag "$w/ext/rc2.rom" "$w/ext/rc2.labels"] {$::hz_done} 600]
	}
	return $jobs
}
