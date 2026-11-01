# pgprobe.tcl (tools/bstest/perf2): agent a_flash's probe of 2026-11-01 (source load.tcl): flash-1's
# look-only page path (docs/PERF2_PLAN.md item 3) logged on a field-check run (pf_fd_setup's records and
# holds), to count the windows' page-path uses and correlate them with the records. DIR/pg.txt:
#   G vbl time tick fb_cur(12 hex) dn0(list hex) want(list hex) lkf0   fp_page: FP_PAGE chosen for a piece
#   K vbl time page|40h lkq dn(list hex) want(list hex)               fd_copy: the end of a diff (lkq: look-only)
# The labels are flash-1's (fp_page, fd_copy, fb_lkf0, fb_lkq) and the field engine's RAM (fb_cur, fb_dn0,
# fb_dn1, fb_wn, fb_dpg, tick_n, tick), read from the build's label file: a build without flash-1 has no
# fp_page (the set-up fails: run it on flash-1's builds only).
#   pg_jobs DIR R ?TAGS? ?WINS?   pg_setup on pf_field_jobs' windows (R: gate.sh's builds; WINS: the windows'
#                                 names, e.g. {kill1560 boss110 boss300}): DIR/<win>_<tag>/; done: pg_done
proc pg_setup {dir rom labels drive from n {level 3}} {
	pf_fd_setup $dir $rom $labels $drive $from $n $level
	pf_lab_load $labels
	set ::pg_log {}
	set ::pg_out "$dir/pg.txt"
	set ::pg_written 0
	foreach {v k} {cur fb_cur dn0 fb_dn0 dn1 fb_dn1 wn fb_wn lkf0 fb_lkf0 lkq fb_lkq dpg fb_dpg tn tick_n vb tick} {
		set ::pg_a($v) [pf_lab $k]
	}
	set bf [pf_lab BANK_FIELD]
	set aa [pf_lab act_a000 0xC07D]
	debug set_bp [pf_lab fp_page] "\[peek $aa\] == $bf" pg_hit
	debug set_bp [pf_lab fd_copy] "\[peek $aa\] == $bf" pg_diff
}
proc pg_list {a} {
	set n [peek $a]
	if {$n == 255} { return "FF" }
	binary scan [debug read_block memory $a [expr {1 + 7 * ($n > 8 ? 8 : $n)}]] H* h
	return $h
}
proc pg_hit {} {
	binary scan [debug read_block memory $::pg_a(cur) 12] H* cur
	lappend ::pg_log "G [peek $::pg_a(vb)] [machine_info time] [rc2_w $::pg_a(tn)] $cur [pg_list $::pg_a(dn0)] [pg_list $::pg_a(wn)] [peek $::pg_a(lkf0)]"
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
			set g 0
			foreach x $::pg_log { if {[string index $x 0] eq "G"} { incr g } }
			puts $f "# page-path uses $g"
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
