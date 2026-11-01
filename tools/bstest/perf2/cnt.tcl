# cnt.tcl (tools/bstest/perf2): call counters per game tick and the map's state every 100 ticks, on m3.tcl's
# lean drive (agents a_scroll's and a_logic's cnt.tcl of 2026-11-01, merged; source load.tcl).
#
#   cnt_job NAME MACHINE DIR ROM LABELS DRIVE N ?NAMES? ?MAP?
#     NAMES: labels to count, each "label" (fixed area or RAM) or "label@BANK" (banked code: the breakpoint
#     counts only while act_8000 or act_a000, as the address says, holds the bank label's value), e.g.
#     {map_write get_tile fb_inval@BANK_FIELD lt2_off@BANK_L3 tur_put@BANK_L3B}
#     -> DIR/NAME_cnt.txt: "# tick time NAMES", then per tick "tick_n time c1 c2 ..." (cumulative)
#     MAP 1 (default) -> DIR/NAME_map.txt: at the tick_start of every tick_n multiple of 100 (before the
#     tick runs) "tick hexA hexB hexC": A = 0910h-0FFFh (ATR_RAM1, MP_ROW, the MP_A pool), B = 1082h-1F9Bh
#     (atr_lost, mp_lost, the redraw queue's pointers, ATR_RAM0, atr_lut), C = F500h-F9FFh (the MP_B pool);
#     compare two runs with mapdiff.py (G-MAP)
#   plus m3's lean records (DIR/NAME_ticks.txt, _pics.txt, ...).
# Rules kept: no vwait, exit, max or min; the map file closed on every path (hz_clean's wrapper).

proc cnt_job {name m dir rom labels drive n {names {}} {map 1}} {
	return [list $name $m [list cnt_setup $name $dir $rom $labels $drive $n $names $map] {[cnt_done]} 3600]
}

proc cnt_close {} {
	if {[info exists ::cnt_mf]} { catch {close $::cnt_mf}; unset ::cnt_mf }
}
if {[info commands hz_clean_cntorig] eq ""} { rename hz_clean hz_clean_cntorig }
proc hz_clean {} { cnt_close; hz_clean_cntorig }

proc cnt_setup {name dir rom labels drive n names map} {
	set r [m3_setup $name $dir $rom $labels $drive $n lean]
	set ::cnt_file "$dir/${name}_cnt.txt"
	set ::cnt_names $names
	set ::cnt_rows {}
	set ::cnt_written 0
	array unset ::cnt
	foreach k $names {
		set ::cnt($k) 0
		lassign [split $k @] lb bk
		set a [pf_lab $lb]
		if {$bk ne ""} {
			set bv [pf_lab $bk]
			set port [expr {$a >= 0xA000 ? $::m3_aa : $::m3_a8}]
			debug set_bp $a "\[peek $port\] == $bv" [list incr ::cnt($k)]
		} else {
			if {$a >= 0x8000 && $a < 0xC000} { error "cnt: $lb is banked code ([format %04X $a]): count it as $lb@BANK" }
			debug set_bp $a {} [list incr ::cnt($k)]
		}
	}
	cnt_close
	if {$map} { set ::cnt_mf [open "$dir/${name}_map.txt" w] }
	set ts $::m3_a(tick_start)
	set gt $::m3_a(game_tick)
	debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt" cnt_tick
	return "$r; cnt: [llength $names] counters, map $map"
}

proc cnt_tick {} {
	set gf [rc2_w $::m3_tn]
	if {[llength $::cnt_names]} {
		set row "$gf [machine_info time]"
		foreach k $::cnt_names { append row " $::cnt($k)" }
		lappend ::cnt_rows $row
	}
	if {[info exists ::cnt_mf] && ($gf % 100) == 0} {
		binary scan [debug read_block memory 0x0910 0x06F0] H* a
		binary scan [debug read_block memory 0x1082 0x0F1A] H* b
		binary scan [debug read_block memory 0xF500 0x0500] H* c
		puts $::cnt_mf "$gf $a $b $c"
	}
}

proc cnt_done {} {
	if {![m3_done]} { return 0 }
	if {!$::cnt_written} {
		set ::cnt_written 1
		cnt_close
		if {[llength $::cnt_names]} {
			set f [open $::cnt_file w]
			catch {
				puts $f "# tick time $::cnt_names"
				foreach x $::cnt_rows { puts $f $x }
			}
			close $f
		}
		set ::cnt_rows {}
	}
	return 1
}
