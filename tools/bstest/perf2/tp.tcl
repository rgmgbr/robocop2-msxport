# tp.tcl (tools/bstest/perf2): the CPU time of routines, interrupts left out, on m3.tcl's lean drive (lane
# W2L's tp_job of batch 2, in the kit since batch 3; source load.tcl). Rules kept: no vwait, exit, max or
# min; the record written once, its file closed on every path.
#
#   tp_job NAME MACHINE DIR ROM LABELS DRIVE N T0 T1 SPECS
#     SPECS: a list of {name label bank caller callbank}: a call is timed from the entry of label (bank: the
#     label of the 8 KiB block its code runs from at 8000h-BFFFh, "" for the fixed area; the breakpoint is
#     taken while the cartridge maps that block there: m3.tcl pf_bankc, the ROM's romblocks) to the
#     instruction after its call in caller (the first CALL of label within 160 bytes after caller; callbank
#     as bank), back at the caller's stack depth; game ticks [T0, T1) (a call that starts in them).
#     The interrupts that fall inside a call are left out: from isr's entry to its reti (msx/isr.asm: one
#     exit, "ei / reti" after isr_r15); the interrupt's acknowledge and its jump to isr (about 30 T each)
#     stay in. Routines may nest (each timed on its own); a routine entered again inside itself (recursion)
#     is timed from its outer entry.
#     -> DIR/NAME_tp.txt: "# ticks T0-T1 (n): name calls seconds T_per_call T_per_tick", a line per routine
#     (T: emulated time x 3,579,545, the Z80's clock: on the turbo R's R800, Z80-equivalent T), plus m3's
#     lean records (DIR/NAME_ticks.txt ...).
#   e.g. tp_job kill_fx Panasonic_FS-A1FX DIR R/l3/cap3.rom R/l3/cap3.labels build/emu/l3_kill.drive 1861 130 1765
#        {{aobj activate_objects BANK_LC2 gtp_act ""} {hzup hz_update BANK_LC3 gtp_act ""}}

proc tp_job {name m dir rom labels drive n t0 t1 specs} {
	return [list $name $m [list tp_setup $name $dir $rom $labels $drive $n $t0 $t1 $specs] {[tp_done]} 3600]
}

proc tp_setup {name dir rom labels drive n t0 t1 specs} {
	file delete -- "$dir/${name}_tp.txt"
	set r [m3_setup $name $dir $rom $labels $drive $n lean]
	set ::tp_file "$dir/${name}_tp.txt"
	set ::tp_t0 $t0
	set ::tp_t1 $t1
	set ::tp_names {}
	set ::tp_written 0
	array unset ::tp_n
	array unset ::tp_s
	array unset ::tp_on
	array unset ::tp_tin
	array unset ::tp_sp
	array unset ::tp_isr
	foreach s $specs {
		lassign $s nm lab bank caller cbank
		set a [pf_lab $lab]
		set pat [binary format ccc 0xCD [expr {$a & 0xFF}] [expr {$a >> 8}]]
		set cb ""
		if {$cbank ne ""} { set cb [pf_lab $cbank] }
		set ret [pf_find_after $rom $caller $pat $cb 160]
		set ::tp_n($nm) 0
		set ::tp_s($nm) 0.0
		set ::tp_on($nm) 0
		lappend ::tp_names $nm
		set ce {}
		if {$bank ne ""} { set ce [pf_bankc $rom $a [pf_lab $bank]] }
		set cx {}
		if {$cbank ne ""} { set cx [pf_bankc $rom $ret $cb] }
		debug set_bp $a $ce [list tp_in $nm]
		debug set_bp $ret $cx [list tp_out $nm]
	}
	set reti [expr {[pf_find_after $rom isr_r15 "\xED\x4D" "" 128] - 2}]
	debug set_bp [pf_lab isr] {} {set ::tp_ist [machine_info time]}
	debug set_bp $reti {} tp_reti
	return "$r; tp [llength $specs] routines, ticks $t0-$t1"
}

proc tp_in {nm} {
	if {$::tp_on($nm)} return
	set t [rc2_w $::m3_tn]
	if {$t < $::tp_t0 || $t >= $::tp_t1} return
	set ::tp_on($nm) 1
	set ::tp_tin($nm) [machine_info time]
	set ::tp_sp($nm) [reg sp]
	set ::tp_isr($nm) 0.0
}

proc tp_out {nm} {
	if {!$::tp_on($nm)} return
	if {[reg sp] != (($::tp_sp($nm) + 2) & 0xFFFF)} return
	set ::tp_s($nm) [expr {$::tp_s($nm) + [machine_info time] - $::tp_tin($nm) - $::tp_isr($nm)}]
	incr ::tp_n($nm)
	set ::tp_on($nm) 0
}

proc tp_reti {} {
	if {![info exists ::tp_ist]} return
	set dt [expr {[machine_info time] - $::tp_ist}]
	foreach nm $::tp_names {
		if {$::tp_on($nm)} { set ::tp_isr($nm) [expr {$::tp_isr($nm) + $dt}] }
	}
}

proc tp_done {} {
	if {![m3_done]} { return 0 }
	if {!$::tp_written} {
		set ::tp_written 1
		set last [rc2_w $::m3_tn]
		set ticks [expr {($last < $::tp_t1 ? $last : $::tp_t1) - $::tp_t0}]
		set f [open $::tp_file w]
		catch {
			puts $f "# ticks $::tp_t0-$::tp_t1 ($ticks): name calls seconds T_per_call T_per_tick"
			foreach nm $::tp_names {
				set n $::tp_n($nm)
				set s $::tp_s($nm)
				set tpc [expr {$n ? $s * 3579545.0 / $n : 0}]
				set tpt [expr {$ticks > 0 ? $s * 3579545.0 / $ticks : 0}]
				puts $f [format "%s %d %.6f %.1f %.1f" $nm $n $s $tpc $tpt]
			}
		}
		close $f
	}
	return 1
}
