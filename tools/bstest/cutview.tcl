# cutview.tcl: level 2's arrest scene's view on the screen (docs/LEVEL2.md 4.2 check 10; its step 15).
# Sourced after tools/bstest/load.tcl (hz.tcl, openmsx_rc2.tcl). The cut at a vat's surface (check 9)
# takes hz.tcl's stills (hz_l2_still_jobs on l2_vat) and tools/bstest/cutview.py cut.
#
# cv_view_jobs DIR ROM LABELS ?SPEC? ?MACHINES?: each drive of SPEC (name, its rows, the first game
# frame recorded; default end 259 15 and tour 2654 2405: the suspect's scene) on ROM (an EXTJOY=1
# LV_TEST=2 build, LABELS its label file) from the power-on of each machine (default C-BIOS_MSX2, the
# FS-A1FX, the FS-A1GT), into DIR/view_<name>_<m>.txt from that frame to the drive's end:
#   T g vx vy add px gcx gcy   at every tick_start: the game frame, the view the game asks for (v_x,
#        v_y: pl_view's, the last tick's), v_addx (level2obj.asm t2), RoboCop's x and the game's camera
#   L g cx cy rf rx ry n [f x y]...  at the HUD split of each new list on screen: its game frame and
#        camera (the list's tail), RoboCop's record as its SAT shows him (pub_spr: flags, x, y of his
#        composition on screen), its play-field BOBs (fb_vis: n, then frame, map x, map y each)
# and the drive's trace into DIR/trace_<name>_<m>.txt. Check with tools/bstest/cutview.py view DIR.
proc cv_view_jobs {dir rom labels {spec {end 259 15 tour 2654 2405}} {machines {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT}}} {
	file mkdir $dir
	set jobs {}
	foreach {name n from} $spec {
		foreach {t m} $machines {
			lappend jobs [list cv_${name}_$t $m [list cv_view_setup $dir $name $t $rom $labels $n $from] \
				{$::rc2_trace_done && [cv_view_close]} 1800]
		}
	}
	return $jobs
}

proc cv_view_setup {dir name t rom labels n from} {
	catch {close $::cv_f}
	set ::cv_f [open [file join $dir view_${name}_$t.txt] w]
	set ::cv_from $from
	set ::cv_seq -1
	rc2_drive_rom $rom $labels [file join $dir trace_${name}_$t.txt] $n 0 "$::hz_root/build/emu/l2_$name.drive"
	set ts [rc2_label $labels tick_start]
	set gt [rc2_label $labels game_tick]
	debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt && \[rc2_w 0xD000\] >= $from" cv_tick
	set ::cv_bp [debug probe set_bp VDP.IRQhorizontal {[debug probe read VDP.IRQhorizontal] == 1} cv_list]
}

proc cv_tick {} {
	catch {puts $::cv_f "T [rc2_w 0xD000] [rc2_w 0xCE6A] [rc2_w 0xCE6C] [peek 0xCE43] [rc2_w 0xDAD0] [rc2_w 0xD004] [rc2_w 0xD006]"}
}

# (the HUD split with the display on, a new list: app_seq changed)
proc cv_list {} {
	if {![info exists ::cv_f] || [peek 0xC002] == 0 || ([debug read "VDP regs" 1] & 0x40) == 0} { return }
	set seq [peek 0xC006]
	if {$seq == $::cv_seq} { return }
	set ::cv_seq $seq
	foreach {l pub} {0xC080 0xC700 0xC0A0 0xC780} {
		if {[peek $l] != $seq} continue
		set tail [expr {$l + 2 + [peek [expr {$l + 1}]]}]
		set g [rc2_w [expr {$tail + 4}]]
		if {$g < $::cv_from} { return }
		set r "L $g [rc2_w $tail] [rc2_w [expr {$tail + 2}]] [peek $pub] [rc2_w [expr {$pub + 4}]] [rc2_w [expr {$pub + 6}]]"
		set nb [peek 0xF248]
		append r " $nb"
		for {set i 0} {$i < $nb && $i < 8} {incr i} {
			set e [expr {0xF249 + 5 * $i}]
			append r " [peek $e] [rc2_w [expr {$e + 1}]] [rc2_w [expr {$e + 3}]]"
		}
		catch {puts $::cv_f $r}
		return
	}
}

# a done condition's last term: the record closed (returns 1)
proc cv_view_close {} {
	catch {debug probe remove_bp $::cv_bp}
	catch {close $::cv_f}
	unset -nocomplain ::cv_f
	return 1
}
