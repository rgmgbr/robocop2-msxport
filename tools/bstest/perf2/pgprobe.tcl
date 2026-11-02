# pgprobe.tcl (tools/bstest/perf2): agent a_flash's probe of 2026-11-01 (source load.tcl): flash-1's
# look-only page path (docs/PERF2_PLAN.md item 3) logged on a field-check run (pf_fd_setup's records and
# holds), to count the windows' page-path uses by the state of their page and correlate them with the
# records. DIR/pg.txt:
#   G vbl time tick fb_cur(12 hex) dn0(list hex) want(list hex) lkf0 vis back bsync phase i flipw eng
#        fp_page: FP_PAGE chosen for a piece (fb_cur's bit 0 its page), with the field engine's pages then:
#        s38_vis_page, s38_back_c0 (FFh: no page beside), fb_bsync (the build target whose page holds
#        the BOBs), s38_phase, s38_i, s38_flip_wait, fb_eng (0 the V9958's ring, 1 the V9938's two pages)
#   B vbl time tick vis back ph cur qback lkf0 lkf1
#        fb_bbinit: a new build target (V9938): the items of the page being built still queued (qback),
#        the pages' look flags then
#   K vbl time page|40h lkq dn(list hex) want(list hex)   fd_copy: the end of a diff (lkq: look-only)
#   # page-path uses N: ring R shown S back-synced Y back-rebuild X; new targets T, with the page being
#     built's items queued Q, of those with its look flag set L   (the last line; pgsum.py reads it)
# A use is "ring" on the V9958 (fb_eng 0); on the V9938 "shown" when its page is the page shown, else
# "back-synced" while the page beside holds its list's BOBs (fb_bsync = s38_back_c0), "back-rebuild"
# while it is copied again for a new build target (its pixels are not its list's composition): the
# review of lane W2F's defect class (C/rev_w2f/tools/rv.tcl, rvan.py: flash-1 may take a piece's
# background only from the page shown, msx/field.asm fp_lkok).
# The breakpoints on fp_page, fd_copy (BANK_FIELD code at A000h) and fb_bbinit (BANK_FIELD's before R3,
# BANK_FRONT2's since: msx/ending.asm, a build with fs_sync) are taken while the cartridge maps that bank
# there (the ROM's "romblocks" debuggable, cen.tcl pf_bp): act_a000's test
# also counted the VBLANK sound player's passes over the same address in its own bank (sound.asm snd_bk
# writes the bank register without act_a000). The labels are flash-1's (fp_page, fd_copy, fb_lkf0,
# fb_lkf1, fb_lkq) and the field engine's RAM, read from the build's label file: a build without
# flash-1 has no fp_page (the set-up fails: run it on flash-1's builds only).
#   pg_jobs DIR R ?TAGS? ?WINS?   pg_setup on pf_field_jobs' windows (R: gate.sh's builds; WINS: the windows'
#                                 names, e.g. {kill1560 boss110 boss300}): DIR/<win>_<tag>/; done: pg_done
#   pg_win NAME MACHINE DIR ROM LABELS DRIVE FROM N   one job of any window (DIR: its folder)
proc pg_setup {dir rom labels drive from n {level 3}} {
	pf_fd_setup $dir $rom $labels $drive $from $n $level
	pf_lab_load $labels
	set ::pg_log {}
	set ::pg_out "$dir/pg.txt"
	set ::pg_written 0
	foreach {v k} {cur fb_cur dn0 fb_dn0 dn1 fb_dn1 wn fb_wn lkf0 fb_lkf0 lkf1 fb_lkf1 lkq fb_lkq dpg fb_dpg tn tick_n vb tick
			vis s38_vis_page back s38_back_c0 bsync fb_bsync phase s38_phase i s38_i flipw s38_flip_wait eng fb_eng
			qn fb_qn q fb_q ph fb_ph} {
		set ::pg_a($v) [pf_lab $k]
	}
	array set ::pg_n {ring 0 shown 0 back-synced 0 back-rebuild 0 B 0 Bq 0 Bl 0}
	set bf [pf_lab BANK_FIELD]
	pf_bp $rom [pf_lab fp_page] pg_hit [list $bf]
	pf_bp $rom [pf_lab fd_copy] pg_diff [list $bf]
	# (R3 moved fb_bbinit to BANK_FRONT2 with the sync, fs_sync: there BANK_FIELD's code at its address is another
	#  routine's)
	set bb [expr {[pf_lab fs_sync 0] ? [pf_lab BANK_FRONT2] : $bf}]
	pf_bp $rom [pf_lab fb_bbinit] pg_bb [list $bb]
}
proc pg_list {a} {
	set n [peek $a]
	if {$n == 255} { return "FF" }
	binary scan [debug read_block memory $a [expr {1 + 7 * ($n > 8 ? 8 : $n)}]] H* h
	return $h
}
proc pg_hit {} {
	binary scan [debug read_block memory $::pg_a(cur) 12] H* cur
	set page [expr {[peek $::pg_a(cur)] & 1}]
	set vis [peek $::pg_a(vis)]
	set back [peek $::pg_a(back)]
	set bsync [peek $::pg_a(bsync)]
	set eng [peek $::pg_a(eng)]
	if {$eng == 0} {
		set k ring
	} elseif {$page == $vis} {
		set k shown
	} elseif {$bsync == $back} {
		set k back-synced
	} else {
		set k back-rebuild
	}
	incr ::pg_n($k)
	lappend ::pg_log "G [peek $::pg_a(vb)] [machine_info time] [rc2_w $::pg_a(tn)] $cur [pg_list $::pg_a(dn0)] [pg_list $::pg_a(wn)] [peek $::pg_a(lkf0)] $vis $back $bsync [peek $::pg_a(phase)] [peek $::pg_a(i)] [peek $::pg_a(flipw)] $eng"
}
proc pg_bb {} {
	set vis [peek $::pg_a(vis)]
	set bk [expr {$vis ^ 1}]
	set qn [peek $::pg_a(qn)]
	set q 0
	for {set k 0} {$k < $qn} {incr k} {
		if {[peek [expr {$::pg_a(q) + 12 * $k}]] == $bk} { incr q }
	}
	set l0 [peek $::pg_a(lkf0)]
	set l1 [peek $::pg_a(lkf1)]
	incr ::pg_n(B)
	if {$q > 0} {
		incr ::pg_n(Bq)
		if {($bk ? $l1 : $l0) == 1} { incr ::pg_n(Bl) }
	}
	lappend ::pg_log "B [peek $::pg_a(vb)] [machine_info time] [rc2_w $::pg_a(tn)] $vis [peek $::pg_a(back)] [peek $::pg_a(ph)] [peek $::pg_a(cur)] $q $l0 $l1"
}
proc pg_diff {} {
	set pg [peek $::pg_a(dpg)]
	set a [expr {($pg & 1) ? $::pg_a(dn1) : $::pg_a(dn0)}]
	lappend ::pg_log "K [peek $::pg_a(vb)] [machine_info time] [format %02X $pg] [peek $::pg_a(lkq)] [pg_list $a] [pg_list $::pg_a(wn)]"
}
proc pg_done {} {
	if {![pf_fd_done]} { return 0 }
	if {!$::pg_written} {
		set ::pg_written 1
		set f [open $::pg_out w]
		catch {
			foreach x $::pg_log { puts $f $x }
			set g [expr {$::pg_n(ring) + $::pg_n(shown) + $::pg_n(back-synced) + $::pg_n(back-rebuild)}]
			puts $f "# page-path uses $g: ring $::pg_n(ring) shown $::pg_n(shown) back-synced $::pg_n(back-synced) back-rebuild $::pg_n(back-rebuild); new targets $::pg_n(B), with the page being built's items queued $::pg_n(Bq), of those with its look flag set $::pg_n(Bl)"
		}
		close $f
		set ::pg_log {}
	}
	return 1
}
proc pg_jobs {dir R {tags ""} {wins ""}} {
	if {$tags eq ""} { set tags $::pf_m3 }
	file mkdir $dir
	set jobs {}
	foreach {w lv b drv from n} $::pf_field_wins {
		if {$wins ne "" && [lsearch -exact $wins $w] < 0} continue
		foreach {t m} $tags {
			lappend jobs [list pg_${w}_$t $m [list pg_setup "$dir/${w}_$t" "$R/$b.rom" "$R/$b.labels" [file join $::pf_emu $drv] $from $n $lv] {[pg_done]} 1200]
		}
	}
	return $jobs
}
proc pg_win {name m dir rom labels drive from n} {
	return [list $name $m [list pg_setup $dir $rom $labels $drive $from $n 3] {[pg_done]} 1200]
}
