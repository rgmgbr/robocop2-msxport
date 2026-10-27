# c8.tcl: step 8's fresh-machine runs of the morning's PZ_TEST ROMs (source after hz.tcl and hz7.tcl,
# or source load.tcl, in the MCP's openMSX; poll "list $::hz_state $::hz_msgs"; never vwait;
# docs/HARNESS.md).
#
#   c8_job NAME MACHINE DIR ROM LABELS MOVES PASSES ?REC? ?RFROM?
#       an hz_chain job: the ROM from the power-on of a new machine (hz.tcl hz_bonus_setup: the intro
#       and result records, the HUD splits per VBLANK, the title, fire, the new game's 100 ticks);
#       hz7_arm's snapshots at PASSES (and a record of REC pictures from pass RFROM) into
#       DIR/st_NAME; the cursor keys pressed from the keyboard (keymatrix row 8) at the passes of
#       MOVES ({pass dir ...}, dir u d l r: down at that pass, up 5 passes later), then nothing,
#       so that board 0 times out; hz7_snap of the intro (fs_n 150) and of the result (fs_n 80-99)
#       into DIR/NAME_intro.bin and DIR/NAME_result.bin (shots.py); notes in DIR/NAME_c8.txt.
#
# Rules kept: no exit, vwait, max or min; files opened once per write and closed on every path; the
# key breakpoint has the pz_tick byte condition (it fires only where BANK_PUZL is mapped).

proc c8_job {name m dir rom labels moves passes {rec 0} {rfrom 0}} {
	set setup "file mkdir {$dir}; hz_bonus_setup {$dir} {$name} {$rom} {$labels} {}; hz7_arm {$dir/st_$name} {$labels} {$passes} $rec $rfrom; c8_arm {$dir} {$name} {$labels} {$moves}"
	return [list $name $m [list eval $setup] {$::hz_done} 900]
}

proc c8_note {m} {
	set f [open "$::c8_dir/${::c8_tag}_c8.txt" a]
	catch {puts $f $m}
	close $f
}

proc c8_arm {dir tag labels moves} {
	set ::c8_dir $dir
	set ::c8_tag $tag
	set ::c8_st 0
	set ::c8_moves $moves
	set ::c8_up {}
	set ::c8_last 0
	foreach {p d} $moves { if {$p + 5 > $::c8_last} { set ::c8_last [expr {$p + 5}] } }
	foreach n {txt_bs_intro txt_bs_ok txt_bs_time} { set ::c8_$n [rc2_label $labels $n] }
	set f [open "$dir/${tag}_c8.txt" w]
	catch {puts $f "# $tag: [machine_info config_name], moves $moves"}
	close $f
	set a [rc2_label $labels pz_tick]
	set t [rc2_label $labels pz_frame]
	set ::c8_bp [debug set_bp $a "\[peek $a\] == 0xCD && \[rc2_w [expr {$a + 1}]\] == $t" c8_tick]
	lappend ::hz_afters [after time 0.05 c8_step]
}

# (row 8: RIGHT 80h, DOWN 40h, UP 20h, LEFT 10h)
proc c8_mask {d} { return [dict get {u 0x20 d 0x40 l 0x10 r 0x80} $d] }

proc c8_cur {} {
	return "col [peek 0xD00C] row [peek 0xD00E] reds [peek 0xD010] score [format %04X [rc2_w 0xDC48]] joy [format %02X [peek 0xDC2F]]"
}

proc c8_tick {} {
	set p [rc2_w 0xD000]
	foreach {q d} $::c8_moves {
		if {$p == $q} {
			keymatrixdown 8 [c8_mask $d]
			c8_note "pass $p: $d down at [format %.3f [machine_info time]] s, [c8_cur]"
		} elseif {$p == $q + 5} {
			keymatrixup 8 [c8_mask $d]
			c8_note "pass $p: $d up, [c8_cur]"
		}
	}
	if {$p >= $::c8_last + 5} {
		c8_note "pass $p: after the moves, [c8_cur]"
		catch {debug remove_bp $::c8_bp}
	}
}

proc c8_step {} {
	set p [rc2_w 0xCFB8]
	set n [rc2_w 0xCFBE]
	switch -- $::c8_st {
		0 {
			if {$p >= $::c8_txt_bs_intro && $p < $::c8_txt_bs_ok && $n >= 150} {
				hz7_snap $::c8_dir ${::c8_tag}_intro
				c8_note "intro snapshot at [format %.3f [machine_info time]] s, fs_n $n"
				set ::c8_st 1
			}
		}
		1 {
			if {$p >= $::c8_txt_bs_ok && $p < $::c8_txt_bs_time + 64 && $n >= 80 && $n < 100} {
				hz7_snap $::c8_dir ${::c8_tag}_result
				c8_note "result snapshot at [format %.3f [machine_info time]] s, fs_n $n, [c8_cur]"
				set ::c8_st 2
				return
			}
		}
	}
	lappend ::hz_afters [after time 0.05 c8_step]
}
