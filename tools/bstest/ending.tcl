# ending.tcl: the game completed and the high scores (docs/ENDING.md; load.tcl sources this file
# after hz.tcl). MCP-safe: no exit, vwait, max or min; every file opened once per write and closed.
#
#   ge_ret_arm ROM LABELS
#       for a flow that reaches the name entry (a product's or a CHEAT build's whole flow: np.tcl's
#       tx jobs, cheat.tcl): RETURN pressed (0.3 s) at the entry's first wait for a key (ending.asm
#       hsn_k with BANK_FRONT2 at A000h), so that the flow goes on with a blank name; ::ge_ret counts
#       the presses
#   ge_job DIR TAG ROM LABELS KEYS ?MACHINE? ?FIRE?
#       an hz_chain job (default machine Gradiente_Expert20_64K): ROM, an END_TEST build, from the
#       power-on, its records under DIR/TAG_:
#         end.sc5 (+ _regs.bin, _pal.bin, _hud.bin, _ram.bin): the WELL DONE screen at fs_n 200 (its
#           text typed: 181 calls), taken at the next iv_late (R#0 and R#1 the list's);
#         hs0.sc5, hs1.sc5 ...: the name entry's screen each time it waits for a key (hsn_k: after
#           its first drawing of the name, then after each key KEYS types, one a wait);
#         best.sc5: the table screen at fs_n 60 (its count from 0 seen first: fs_n is the entry's
#           until fe_go);
#         over.sc5 and cont.sc5 (END_TEST=2): PIC9 is left to its 30 s; the offer's record at fs_n
#           50; FIRE 1 presses fire there (SPACE, 0.3 s), 0 leaves it;
#         end.txt: the notes (each step's emulated time, fs_n, the tune's start and its end as
#           tn_left reads 0 with the tune's ticks counted at tn_tick in between, the keys typed, the
#           table in RAM at the title or at lv_cont: hs_tab0, hs_tab1).
#       KEYS: names typed in turn, one a wait of the entry: A-Z, 0-9, KP0-KP9 (the keypad), SPACE,
#       BS, RET. The job ends at the title (front_mode 1 after the entry), at lv_cont, or after 900
#       emulated s. Check with tools/bstest/endcheck.py DIR TAG KEYS.

proc ge_note {m} {
	set f [open "$::ge_dir/${::ge_tag}_end.txt" a]
	catch {puts $f "[format %9.3f [machine_info time]] $m"}
	close $f
}

proc ge_file {name data} {
	set f [open "$::ge_dir/${::ge_tag}_$name" w]
	catch {
		fconfigure $f -translation binary
		puts -nonewline $f $data
	}
	close $f
}

proc ge_snap {name} {
	ge_file $name.sc5 [debug read_block "physical VRAM" 0 [expr {162 * 128}]]
	ge_file ${name}_regs.bin [debug read_block "VDP regs" 0 [debug size "VDP regs"]]
	ge_file ${name}_pal.bin [debug read_block "VDP palette" 0 [debug size "VDP palette"]]
	ge_file ${name}_hud.bin [debug read_block "physical VRAM" 0x1E800 [expr {45 * 128}]]
	ge_file ${name}_ram.bin [debug read_block memory 0xC000 0x4000]
}

# (the key's matrix row and mask: docs MSX2-Technical-Handbook figure 5.17B; msx/ending.asm kb_tab)
proc ge_keymask {k} {
	set letters ABCDEFGHIJKLMNOPQRSTUVWXYZ
	set i [string first $k $letters]
	if {[string length $k] == 1 && $i >= 0} {
		set b [expr {$i + 22}]
		return [list [expr {$b / 8}] [expr {1 << ($b % 8)}]]
	}
	if {[string is digit -strict $k] && [string length $k] == 1} {
		return [list [expr {$k / 8}] [expr {1 << ($k % 8)}]]
	}
	if {[regexp {^KP([0-9])$} $k -> d]} {
		set b [expr {$d + 75}]
		return [list [expr {$b / 8}] [expr {1 << ($b % 8)}]]
	}
	switch -- $k {
		SPACE { return {8 0x01} }
		BS { return {7 0x20} }
		RET { return {7 0x80} }
	}
	error "ge_keymask: no key $k"
}

proc ge_press {k {secs 0.15}} {
	lassign [ge_keymask $k] row mask
	keymatrixdown $row $mask
	lappend ::hz_afters [after time $secs [list keymatrixup $row $mask]]
}

# the condition that ending.asm's code runs at ADDR: BANK_FRONT2 at A000h (the mapper's state)
proc ge_cond {rom labels} {
	return "\[debug read {[file tail $rom] romblocks} 0xA000\] == [rc2_label $labels BANK_FRONT2]"
}

proc ge_ret_arm {rom labels} {
	set ::ge_ret 0
	set a [rc2_label $labels hsn_k]
	set ::ge_retbp [debug set_bp $a [ge_cond $rom $labels] ge_ret_hit]
}

proc ge_ret_hit {} {
	if {$::ge_ret} return
	incr ::ge_ret
	lappend ::hz_afters [after time 0.3 {ge_press RET 0.3}]
}

proc ge_table {} {
	set out {}
	foreach base {0xC5D0 0xC2D9} {
		for {set k 0} {$k < 3} {incr k} {
			set a [expr {$base + 13 * $k}]
			binary scan [debug read_block memory $a 13] H* h
			lappend out $h
		}
	}
	return $out
}

proc ge_setup {dir tag rom labels keys fire} {
	file mkdir $dir
	set ::ge_dir $dir
	set ::ge_tag $tag
	set ::ge_keys $keys
	set ::ge_k 0
	set ::ge_fire $fire
	set ::ge_fin 0
	set ::ge_st 0
	set ::ge_ticks 0
	set ::ge_tn 0
	set f [open "$dir/${tag}_end.txt" w]
	close $f
	foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
	foreach {id opts} [debug condition list] { debug condition remove $id }
	carta eject
	carta insert $rom -romtype KonamiSCC
	if {[debug breaked]} { debug cont }
	set ::pause off
	reset
	foreach n {txt_end txt_hisc txt_cont txt_best tn_cmp mus_call tn_tick tn_left iv_late hsn_k front_over
	           lv_cont fr_title front_ending hs_best BANK_FRONT BANK_FRONT2 BANK_MUSIC front_mode} {
		set ::ge_$n [rc2_label $labels $n]
	}
	set c2 [ge_cond $rom $labels]
	set rb "[file tail $rom] romblocks"
	set cf "\[debug read {$rb} 0x8000\] == $::ge_BANK_FRONT"
	set ::ge_bps {}
	lappend ::ge_bps [debug set_bp $::ge_front_ending $c2 {ge_note "front_ending: [ge_state]"}]
	lappend ::ge_bps [debug set_bp $::ge_mus_call "\[reg hl\] == $::ge_tn_cmp" ge_tune]
	set t $::ge_tn_tick
	lappend ::ge_bps [debug set_bp $t "\[debug read {$rb} 0xA000\] == $::ge_BANK_MUSIC" {incr ::ge_ticks}]
	lappend ::ge_bps [debug set_bp $::ge_hsn_k $c2 ge_key]
	lappend ::ge_bps [debug set_bp $::ge_hs_best $c2 {ge_note "the table screen (hs_best): [ge_state]"; set ::ge_st 30}]
	lappend ::ge_bps [debug set_bp $::ge_front_over $cf {ge_note "front_over (PIC9): [ge_state]"; set ::ge_st 20}]
	lappend ::ge_bps [debug set_bp $::ge_lv_cont {} {ge_end "lv_cont"}]
	lappend ::ge_bps [debug set_bp $::ge_fr_title $cf {ge_end "the title (fr_title)"}]
	ge_note "[file tail $rom] on [machine_info config_name], keys: $keys"
	lappend ::hz_afters [after time 0.05 ge_poll]
	lappend ::hz_afters [after time 900 {ge_end "no title or continue in 900 emulated s (state $::ge_st)"}]
}

proc ge_state {} {
	return "fs_n [rc2_w 0xCFBE], fs_ptr [format %04X [rc2_w 0xCFB8]], tn_left [rc2_w $::ge_tn_left], ticks counted $::ge_ticks, score [format %04X%04X [rc2_w 0xDC46] [rc2_w 0xDC48]], 805Eh [rc2_w 0xDC5E], front_mode [peek $::ge_front_mode]"
}

proc ge_tune {} {
	set ::ge_ticks 0
	set ::ge_tn 1
	ge_note "tn_cmp through mus_call: [ge_state]"
}

proc ge_key {} {
	set n $::ge_k
	set ::ge_rec "hs$n"
	set ::ge_ilbp [debug set_bp $::ge_iv_late {} ge_rec]
	if {$n < [llength $::ge_keys]} {
		set k [lindex $::ge_keys $n]
		lappend ::hz_afters [after time 0.4 [list ge_press $k 0.15]]
		lappend ::hz_afters [after time 0.4 [list ge_note "key $k down"]]
	}
	incr ::ge_k
}

proc ge_rec {} {
	catch {debug remove_bp $::ge_ilbp}
	ge_snap $::ge_rec
	ge_note "record $::ge_rec: R#0 [format %02X [debug read {VDP regs} 0]] R#1 [format %02X [debug read {VDP regs} 1]], [ge_state], name [ge_name]"
}

proc ge_name {} {
	binary scan [debug read_block memory [expr {0xC2D9 + 26}] 9] H* h
	return $h
}

# the screens' records by fs_ptr and fs_n (polled each 20 ms of emulated time), the tune's end
proc ge_poll {} {
	if {$::ge_fin} return
	set p [rc2_w 0xCFB8]
	set n [rc2_w 0xCFBE]
	switch -- $::ge_st {
		0 {
			if {$p >= $::ge_txt_end && $p < $::ge_txt_hisc && $n >= 200 && $n < 300} {
				set ::ge_rec end
				set ::ge_ilbp [debug set_bp $::ge_iv_late {} ge_rec]
				set ::ge_st 1
			}
		}
		1 {
			if {$::ge_tn == 1 && [rc2_w $::ge_tn_left] != 0} { set ::ge_tn 2 }
			if {$::ge_tn == 2 && [rc2_w $::ge_tn_left] == 0} {
				ge_note "the tune over (tn_left 0): [ge_state]"
				set ::ge_st 2
			}
		}
		20 {
			if {$n < 50} { set ::ge_st 21 }
		}
		30 {
			if {$n < 50} { set ::ge_st 32 }
		}
		32 {
			if {$p >= $::ge_txt_best && $p < $::ge_txt_best + 8 && $n >= 60 && $n < 200} {
				set ::ge_rec best
				set ::ge_ilbp [debug set_bp $::ge_iv_late {} ge_rec]
				set ::ge_st 31
			}
		}
		21 -
		31 {
			if {$p >= $::ge_txt_cont && $p < $::ge_txt_cont + 64 && $n >= 50 && $n < 120} {
				set ::ge_rec cont
				set ::ge_ilbp [debug set_bp $::ge_iv_late {} ge_rec]
				if {$::ge_fire} { lappend ::hz_afters [after time 0.6 {ge_press SPACE 0.3; ge_note "SPACE down (fire)"}] }
				set ::ge_st 40
			}
		}
	}
	lappend ::hz_afters [after time 0.02 ge_poll]
}

proc ge_end {why} {
	if {$::ge_fin} return
	set ::ge_fin 1
	ge_note "end: $why: [ge_state]"
	ge_note "table: [ge_table]"
	foreach b $::ge_bps { catch {debug remove_bp $b} }
	set ::pause on
}

proc ge_job {dir tag rom labels keys {m Gradiente_Expert20_64K} {fire 1}} {
	return [list "ending $tag" $m [list ge_setup $dir $tag $rom $labels $keys $fire] {$::ge_fin} 1200]
}

set ::ge_loaded "ending.tcl loaded"
