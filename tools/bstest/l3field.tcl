# l3field.tcl: level 3's frame cache on the screen (docs/LEVEL3.md 4 checks 3-5; its step C). Sourced after
# tools/bstest/load.tcl and tools/bstest/l2base.tcl (l2b_fd_setup's records).
#
# With step A's stub types nothing in level 3 draws Cain's or type 21's frames yet: lf_jobs drives DRIVE
# (default tour3's) on R/l3/rc2_l3.rom (hz.sh l3builds) and, at every tick, right after bob_flush (rc2.asm
# ml_fbn), appends scripted enemies to the tick's play-field list (fb_new, fb_n; FB_MAX 8 at most): POSES
# (tools/bstest/l3poses.py) gives phases of ::lf_len ticks, each a list of parts that cycle through their
# frames, a hit flash (the white copies: the frame id's bit 7, as msx/bob.asm fb_add sets it) every 16th
# tick; the enemy walks across the view (map x = cam_x + 48 + (2 x tick) mod 128, y = cam_y + 40), so that
# its pieces cross the V9958 ring's x 256 and y 256 and the V9938's page builds. The pictures are recorded
# as the field check's (l2b_fd_hit: DIR/<m>/jNNN_fNNNN.bin, from game frame FROM, N of them) and judged by
# "$PY -I tools/bstest/fieldcheck.py DIR/<m> build/msx/level3 OUT.png --level 3": every play-area pixel no
# sprite covers is the tile or the BOB the shown page's list holds there (the frame cache's copies among
# them). DIR/<m>/fc.txt: the copies into the cache (fcg_ld to fcg_dn: count, the emulated time).
# ::lf_mul (default 1) slows the parts' frames down, ::lf_dx (default 2) is the walk's pixels a tick.
proc lf_jobs {dir R poses {from 0} {n 400} {machines {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT}} {drive l3_tour3}} {
	set jobs {}
	foreach {t m} $machines {
		lappend jobs [list lf_$t $m [list lf_setup "$dir/$t" "$R/l3/rc2_l3.rom" "$R/l3/rc2_l3.labels" \
			"$::hz_root/build/emu/$drive.drive" $from $n $poses] {[lf_done]} 3600]
	}
	return $jobs
}

proc lf_setup {dir rom labels drive from n poses} {
	uplevel #0 [list source $poses]
	if {![info exists ::lf_mul]} { set ::lf_mul 1 }    ;# (slower: each part's period times lf_mul,
	if {![info exists ::lf_dx]} { set ::lf_dx 2 }      ;#  lf_dx px a tick across the view, 0: still)
	l2b_fd_setup $dir $rom $labels $drive $from $n
	set ::lf_dir $dir
	set ::lf_new [rc2_label $labels fb_new]
	set ::lf_n [rc2_label $labels fb_n]
	set ::lf_loads 0
	set ::lf_t0 -1
	set ::lf_us 0
	set ::lf_max 0
	set ::lf_written 0
	set fbank [expr {[rc2_label $labels BANK_FIELD]}]
	set a0 [rc2_label $labels act_a000]
	debug set_bp [rc2_label $labels ml_fbn] {} lf_inject
	debug set_bp [rc2_label $labels fcg_ld] "\[peek $a0\] == $fbank" {set ::lf_t0 [machine_info time]}
	debug set_bp [rc2_label $labels fcg_dn] "\[peek $a0\] == $fbank" lf_copied
}

proc lf_copied {} {
	if {$::lf_t0 < 0} { return }
	set us [expr {([machine_info time] - $::lf_t0) * 1e6}]
	incr ::lf_loads
	set ::lf_us [expr {$::lf_us + $us}]
	if {$us > $::lf_max} { set ::lf_max $us }
	set ::lf_t0 -1
}

proc lf_inject {} {
	set t [rc2_w 0xCEE0]
	set np [llength $::lf_phases]
	set p [expr {($t / $::lf_len) % $np}]
	set parts [lindex [lindex $::lf_phases $p] 1]
	set k [expr {$t % $::lf_len}]
	set white [expr {($t % 16) == 0 ? 0x80 : 0}]
	set ax [expr {[rc2_w 0xC020] + 48 + (($t * $::lf_dx) % 128)}]
	set ay [expr {[rc2_w 0xC022] + 40}]
	set n [peek $::lf_n]
	set own [expr {0x5000 + $p}]
	foreach part $parts {
		if {$n >= 8} { break }
		lassign $part frames per dx dy
		set fid [expr {[lindex $frames [expr {($k / ($per * $::lf_mul)) % [llength $frames]}]] | $white}]
		set a [expr {$::lf_new + 7 * $n}]
		poke $a $fid
		rc2_wset [expr {$a + 1}] [expr {$ax + $dx + 143}]
		rc2_wset [expr {$a + 3}] [expr {$ay + $dy}]
		rc2_wset [expr {$a + 5}] $own
		incr n
	}
	poke $::lf_n $n
}

proc lf_done {} {
	if {!$::l2b_fd_done} { return 0 }
	if {!$::lf_written} {
		set ::lf_written 1
		set f [open [file join $::lf_dir fc.txt] w]
		puts $f "copies $::lf_loads us [expr {int($::lf_us)}] max_us [expr {int($::lf_max)}] game_frame [rc2_w 0xCEE0] lost fb [peek 0x069C] mp [peek 0x1084]"
		close $f
	}
	return 1
}

# lf_start_jobs DIR R ?SECS? ?POSES?: level 3's start check (docs/LEVEL3.md 4 checks 2 and 5), as
# hz_l2_start_jobs: R/l3/rc2_l3.rom from the power-on of the three machines on tour3's drive, from level
# 3's first tick (lv_cur's logic bank BANK_L3) SECS (default 42) of emulated time under rc2_guard (tears
# counted), rc2_patcheck, rc2_sprlines and rc2_satcheck: DIR/start_<m2|fx|tr>.txt (the same lines); with
# POSES the scripted enemies of lf_jobs too (the frame cache under the guard). The drive's trace goes to
# DIR/l3_tour3.txt, l3_tour3_fx.txt, l3_tour3_tr.txt.
proc lf_start_jobs {dir R {secs 42} {poses ""}} {
	file mkdir $dir
	set e "$::hz_root/build/emu"
	set jobs {}
	foreach {t m tn} {m2 C-BIOS_MSX2 tour3 fx Panasonic_FS-A1FX tour3_fx tr Panasonic_FS-A1GT tour3_tr} {
		lappend jobs [list l3start_$t $m [list lf_start_setup "$dir/start_$t.txt" "$R/l3/rc2_l3.rom" \
			"$R/l3/rc2_l3.labels" "$dir/l3_$tn.txt" "$e/l3_tour3.drive" $secs $poses] {[hz_l2_start_done]} 900]
	}
	return $jobs
}

proc lf_start_setup {out rom labels trace drive secs poses} {
	set ::hz_l2g_out $out
	set ::hz_l2g_rom $rom
	set ::hz_l2g_lab $labels
	set ::hz_l2g_secs $secs
	set ::hz_l2g_n 1401
	set ::hz_l2g 0
	set ::hz_l2g_written 0
	set ::rg_done 0
	unset -nocomplain ::rg_notear
	hz_l2_drive $rom $labels $trace $::hz_l2g_n $drive
	set ts [rc2_label $labels tick_start]
	set gt [rc2_label $labels game_tick]
	set bank [expr {[rc2_label $labels BANK_L3]}]
	set ::hz_l2g_bp [debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt && \[peek 0xF1A0\] == $bank" hz_l2_start_go]
	if {$poses ne ""} {
		uplevel #0 [list source $poses]
		if {![info exists ::lf_mul]} { set ::lf_mul 1 }
		if {![info exists ::lf_dx]} { set ::lf_dx 2 }
		set ::lf_new [rc2_label $labels fb_new]
		set ::lf_n [rc2_label $labels fb_n]
		debug set_bp [rc2_label $labels ml_fbn] {} lf_inject
	}
}
