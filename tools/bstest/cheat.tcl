# cheat.tcl: a CHEAT=1 build (tools/mkrom.py, docs/LEVEL2.md section 6) from the power-on, by the
# keyboard (docs/HARNESS.md 5.23; load.tcl sources this file): the title, SPACE, level 1 to its game
# frame 100, F5 (the level's end: $16D0), the statistics, Brainstorm and the range left alone, the
# level-2 briefing, level 2 to its game frame 100, its energy poked to 40h, F4 (the energy full:
# 102h), F5, the statistics, both stages' second visits left alone, the level-3 briefing and the
# title. Snapshots (rc2_snap at the HUD split's line interrupt: render them with tools/msxframe.py)
# and the notes (DIR/cheat.txt) into DIR. MCP-safe: no exit, vwait, max or min; the notes written
# once at the end. One job:
#   hz_chain [list [ch_job DIR ROM LABELS ?MACHINE?]]
# The game's variables by their homes (msx/msx.inc AM C500h, AG 5C00h + address): g_frame ($B00)
# D000h, the energy ($169A) DB9Ah, the level's end ($16D0) DBD1h, $804F DC4Eh, the level ($8050) DC50h.

proc ch_note {m} { lappend ::ch_notes "[format %8.3f [machine_info time]] $m" }

proc ch_state {} {
	return "game frame [rc2_w 0xD000], level [rc2_w 0xDC50], energy [format %X [rc2_w 0xDB9A]], \$16D0 [format %02X [peek 0xDBD1]], \$804F [format %02X [peek 0xDC4E]], \$8032 [format %02X [peek 0xDC33]]"
}

proc ch_snap {tag} {
	set ::ch_stag $tag
	set ::ch_sbp [debug probe set_bp VDP.IRQhorizontal {[debug probe read VDP.IRQhorizontal] == 1} ch_snap_hit]
}

proc ch_snap_hit {} {
	if {([debug read "VDP regs" 1] & 0x40) == 0} return
	catch {debug probe remove_bp $::ch_sbp}
	rc2_snap "$::ch_dir/$::ch_stag"
	ch_note "snapshot $::ch_stag: [ch_state]"
}

proc ch_key {row mask secs} {
	keymatrixdown $row $mask
	lappend ::hz_afters [after time $secs [list keymatrixup $row $mask]]
}

proc ch_end {why} {
	if {$::ch_fin} return
	set ::ch_fin 1
	ch_note "end: $why"
	foreach b $::ch_bps { catch {debug remove_bp $b} }
	catch {debug probe remove_bp $::ch_sbp}
	set f [open "$::ch_dir/cheat.txt" w]
	catch {puts $f [join $::ch_notes "\n"]}
	close $f
	set ::pause on
}

# every game tick's start: the steps of the run by the game's own state
proc ch_tick {} {
	set gf [rc2_w 0xD000]
	set lv [rc2_w 0xDC50]
	switch -- $::ch_st {
		1 {
			if {$lv == 0 && $gf >= 100} {
				ch_note "level 1 at frame 100: [ch_state]"
				ch_snap l1_100
				ch_key 7 0x02 0.5
				ch_note "F5 down (0.5 s)"
				set ::ch_st 2
			}
		}
		2 {
			if {[peek 0xDBD1] == 0xFF} {
				ch_note "level 1's end set: [ch_state]"
				set ::ch_t $gf
				set ::ch_st 3
			}
		}
		3 { if {$gf >= $::ch_t + 20} { ch_snap l1_end; set ::ch_st 4 } }
		5 {
			if {$lv == 1 && $gf >= 100} {
				ch_note "level 2 at frame 100: [ch_state]"
				ch_snap l2_100
				rc2_wset 0xDB9A 0x40
				ch_note "energy poked to 40h"
				set ::ch_t $gf
				set ::ch_st 6
			}
		}
		6 {
			if {$gf >= $::ch_t + 25} {
				ch_note "before F4: [ch_state]"
				ch_snap l2_low
				ch_key 7 0x01 0.5
				ch_note "F4 down (0.5 s)"
				set ::ch_st 7
			}
		}
		7 {
			if {[rc2_w 0xDB9A] == 0x102} {
				ch_note "the energy full: [ch_state]"
				set ::ch_t $gf
				set ::ch_st 8
			}
		}
		8 {
			if {$gf >= $::ch_t + 40} {
				ch_snap l2_full
				ch_key 7 0x02 0.5
				ch_note "F5 down (0.5 s)"
				set ::ch_st 9
			}
		}
		9 {
			if {[peek 0xDBD1] == 0xFF} {
				ch_note "level 2's end set: [ch_state]"
				set ::ch_t $gf
				set ::ch_st 10
			}
		}
		10 { if {$gf >= $::ch_t + 20} { ch_snap l2_end; set ::ch_st 11 } }
	}
}

proc ch_stats {} {
	ch_note "front_stats: [ch_state]"
	if {$::ch_st == 4} {
		lappend ::hz_afters [after time 4 {ch_snap l1_stats}]
		set ::ch_st 5
	} elseif {$::ch_st == 11} {
		lappend ::hz_afters [after time 4 {ch_snap l2_stats}]
		set ::ch_st 12
	}
}

proc ch_title {} {
	incr ::ch_nt
	ch_note "the title (fr_title, the [expr {$::ch_nt == 1 ? "first" : "next"}] time): [ch_state]"
	if {$::ch_nt == 1} {
		lappend ::hz_afters [after time 3 {ch_key 8 0x01 0.3; ch_note "SPACE"}]
		set ::ch_st 1
	} elseif {$::ch_st == 12} {
		lappend ::hz_afters [after time 3 {rc2_snap "$::ch_dir/title"; ch_note "snapshot title (no split: taken at once): R#0 [format %02X [debug read {VDP regs} 0]] R#1 [format %02X [debug read {VDP regs} 1]], front_mode [peek $::ch_fm]"; ch_end "the title after level 2"}]
	}
}

proc ch_setup {dir rom labels} {
	file mkdir $dir
	set ::ch_dir $dir
	set ::ch_notes {}
	set ::ch_fin 0
	set ::ch_st 0
	set ::ch_nt 0
	set ::ch_bps {}
	foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
	foreach {id opts} [debug condition list] { debug condition remove $id }
	carta eject
	carta insert $rom -romtype KonamiSCC
	if {[debug breaked]} { debug cont }
	set ::pause off
	reset
	set rb "[file tail $rom] romblocks"
	set cf "\[debug read {$rb} 0x8000\] == [rc2_label $labels BANK_FRONT]"
	set ts [rc2_label $labels tick_start]
	lappend ::ch_bps [debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == [rc2_label $labels game_tick]" ch_tick]
	lappend ::ch_bps [debug set_bp [rc2_label $labels front_stats] $cf ch_stats]
	lappend ::ch_bps [debug set_bp [rc2_label $labels fr_title] $cf ch_title]
	set ::ch_fm [rc2_label $labels front_mode]
	ch_note "[file tail $rom] on [machine_info config_name]"
	lappend ::hz_afters [after time 900 {ch_end "no title after level 2 in 900 emulated s (state $::ch_st)"}]
}

proc ch_job {dir rom labels {m C-BIOS_MSX2}} {
	return [list cheat $m [list ch_setup $dir $rom $labels] {$::ch_fin} 1800]
}

set ::ch_loaded "cheat.tcl loaded"
