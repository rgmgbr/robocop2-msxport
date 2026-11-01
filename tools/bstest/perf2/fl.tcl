# fl.tcl (tools/bstest/perf2): agent a_flash's probe of 2026-11-01 (source load.tcl): a level-3 drive
# (hz_l2_drive: its trace beside OUT) with, as events written to OUT when the drive's rows are done:
#   T tick_n time            every tick_start (lv_cur = BANK_L3, the logic bank)
#   U time B C E             fcg_ld: a frame-cache upload starts (B cache frame, C play-field frame, E place)
#   D time                   fcg_dn: it ends
#   Y time                   fdy_ld: a dynamic-slot upload (the smoke) starts
#   P time hold              iv_take: a published list goes on screen (fb_hold: the VBLANKs it waited)
#   W time n white cmds      fb_wants: the picture's play-field BOBs (fb_n), those white (bit 7), and the
#                            field commands prepared (fb_issue) since the last fb_wants, then the list
#                            (frame:x:y:owner, comma-separated)
#   B time                   fbb_df: a BOB put off because the VDP was busy (fc_get / fb_dyn refused)
# Banked addresses conditioned on act_a000 = BANK_FIELD; RAM addresses from the build's labels. A label the
# build lacks leaves its event out (noted as an "N label missing" line). Compare logs with flcmp.py.
#   fl_jobs DIR ROM LABELS DRIVE N TAG TAGS   DIR/fl_<TAG>_<tag>.txt per machine of TAGS ({tag machine ...})
# No exit, vwait, max, min; one file, closed.

proc fl_setup {out rom labels drive n} {
	set ::fl_out $out
	set ::fl_log {}
	set ::fl_written 0
	hz_l2_drive $rom $labels "[file rootname $out]_trace.txt" $n $drive
	pf_lab_load $labels
	set ts [pf_lab tick_start]
	set gt [pf_lab game_tick]
	set ::fl_tn [pf_lab tick_n 0xCEE0]
	set ::fl_fbh [pf_lab fb_hold 0xF1EB]
	set ::fl_fbn [pf_lab fb_n 0x1F9C]
	set ::fl_fbnew [pf_lab fb_new 0x1F9D]
	set aa [pf_lab act_a000 0xC07D]
	set lv [pf_lab lv_cur 0xF1A0]
	debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt && \[peek $lv\] == [pf_lab BANK_L3]" {lappend ::fl_log "T [rc2_w $::fl_tn] [machine_info time]"}
	set bf [pf_lab BANK_FIELD]
	set c "\[peek $aa\] == $bf"
	foreach {lb cmd} {
		fcg_ld {lappend ::fl_log "U [machine_info time] [format %d [expr {[reg bc] >> 8}]] [format %d [expr {[reg bc] & 255}]] [format %d [expr {[reg de] & 255}]]"}
		fcg_dn {lappend ::fl_log "D [machine_info time]"}
		fdy_ld {lappend ::fl_log "Y [machine_info time]"}
		fbb_df {lappend ::fl_log "B [machine_info time]"}
		fb_wants fl_wants
		fb_issue {incr ::fl_cmds}} {
		if {[info exists ::pf_L($lb)]} {
			debug set_bp $::pf_L($lb) $c $cmd
		} else {
			lappend ::fl_log "N $lb missing"
		}
	}
	debug set_bp [pf_lab iv_take] {} {lappend ::fl_log "P [machine_info time] [peek $::fl_fbh]"}
	set ::fl_cmds 0
}

proc fl_wants {} {
	set n [peek $::fl_fbn]
	set w 0
	set es {}
	for {set i 0} {$i < $n && $i < 8} {incr i} {
		set a [expr {$::fl_fbnew + 7 * $i}]
		set fr [peek $a]
		if {$fr & 0x80} { incr w }
		lappend es [format %02X:%d:%d:%04X $fr [rc2_w [expr {$a + 1}]] [rc2_w [expr {$a + 3}]] [rc2_w [expr {$a + 5}]]]
	}
	lappend ::fl_log "W [machine_info time] $n $w $::fl_cmds [join $es ,]"
	set ::fl_cmds 0
}

proc fl_done {} {
	if {!$::rc2_trace_done} { return 0 }
	if {!$::fl_written} {
		set ::fl_written 1
		set f [open $::fl_out w]
		catch { foreach x $::fl_log { puts $f $x } }
		close $f
		set ::fl_log {}
	}
	return 1
}

proc fl_jobs {dir rom labels drive n tag machines} {
	file mkdir $dir
	set jobs {}
	foreach {t m} $machines {
		lappend jobs [list fl_${tag}_$t $m [list fl_setup "$dir/fl_${tag}_$t.txt" $rom $labels $drive $n] {[fl_done]} 1500]
	}
	return $jobs
}
