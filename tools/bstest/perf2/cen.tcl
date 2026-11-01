# cen.tcl (tools/bstest/perf2): a census of the sprite budget on a drive (agent a_sprites' census of
# 2026-11-01; source load.tcl). One record per budget run (msx/sprites.asm budget, called by sprites_tick):
#   R tick t_budget t_lnfill t_ftlines t_bgtot t_end lhit give_line give_tot drop leave cand anyb lnadd_line lnadd_tot
#   E bu_tot bu_tot+1 bu_cut obj_tab(hex)     the budget's totals and the object table at its end
#   C hex   ln_cnt (VIEW_LINES bytes) right after ln_rc (RoboCop's lines only)   (line phase only)
#   F hex   ln_cnt at ft_lines (every object's lines)                           (line phase only)
#   O hex   obj_tab (16 x 32 bytes) at ft_lines                                  (line phase only)
# Times are emulated seconds (machine_info time); -1 when the phase did not run. Compare two censuses with
# vercmp.py (records equal but their times; the budget's T-states per run).
#
#   cen_jobs DIR ROM LABELS DRIVE N ?TAGS?     DIR/cen_<drive>_<tag>.txt (+ _trace.txt: the drive's trace)
#
# The budget's code may move into a level bank (docs/PERF2_PLAN.md item 12, spr-6: msx/lvshared.asm, at
# the same address in every level bank, its level-2 and level-3 copies' labels suffixed _l2 and _l3): a
# label at 8000h-BFFFh is then counted only while the cartridge maps one of the level banks there (the
# ROM's "romblocks" debuggable: exact however the bank was mapped); another banked label needs NAME@BANK.
# The output channel is ::h7_rf (hz_clean closes it when a job times out). No vwait/exit/max/min.

set ::cen_names {budget ln_fill ft_lines bg_tot sprites_tick fl_hit ft_give ft_drop_t ft_leave_t ft_cand ft_anyb ln_add obj_tab ft_line bu_tot bu_cut ln_rc VIEW_LINES}

# a breakpoint at ADDR running CMD: none for the fixed area and RAM; for banked code, only while the
# cartridge maps one of BANKS there (BANKS empty: an error)
proc pf_bp {rom addr cmd {banks {}}} {
	if {$addr < 0x8000 || $addr >= 0xC000} { return [debug set_bp $addr {} $cmd] }
	if {![llength $banks]} { error "pf_bp: [format %04X $addr] is banked: name its bank" }
	set rb "[file tail $rom] romblocks"
	return [debug set_bp $addr "\[debug read {$rb} $addr\] in {$banks}" $cmd]
}

# the banks a census label's code can be in: none (fixed area, RAM), the level banks (an msx/lvshared.asm
# label: its _l3 twin exists), or NAME@BANK's
proc cen_banks {name} {
	lassign [split $name @] lb bk
	set a [pf_lab $lb]
	if {$a < 0x8000 || $a >= 0xC000} { return {} }
	if {$bk ne ""} { return [list [pf_lab $bk]] }
	if {[info exists ::pf_L(${lb}_l3)]} { return [list [pf_lab BANK_L1] [pf_lab BANK_L2] [pf_lab BANK_L3]] }
	error "cen: $lb is banked ([format %04X $a]) and not an lvshared label: give its bank as $lb@BANK"
}

proc cen_setup {out rom labels drive n} {
	set ::cen_written 0
	hz_l2_drive $rom $labels "[file rootname $out]_trace.txt" $n $drive
	pf_lab_load $labels
	foreach nm $::cen_names { set ::cen_a($nm) [pf_lab $nm] }
	set ::cen_vl $::cen_a(VIEW_LINES)
	set ::cen_on 0
	set ::h7_rf [open $out w]
	pf_bp $rom $::cen_a(budget) cen_b0 [cen_banks budget]
	pf_bp $rom $::cen_a(ln_fill) {set ::cen_t1 [machine_info time]} [cen_banks ln_fill]
	# the instruction after ln_fill's "call ln_rc" (CDh, ln_rc), found in the ROM file
	set lf $::cen_a(ln_fill)
	set lb [cen_banks ln_fill]
	set rf [open $rom rb]
	set blk ""
	catch {
		fconfigure $rf -translation binary
		seek $rf [pf_romoff $lf [lindex $lb 0]]
		set blk [read $rf 64]
	}
	close $rf
	set lr $::cen_a(ln_rc)
	set i [string first [binary format cs 0xCD $lr] $blk]
	if {$i < 0} { error "cen: no call ln_rc in ln_fill" }
	pf_bp $rom [expr {$lf + $i + 3}] cen_rc $lb
	pf_bp $rom $::cen_a(ft_lines) cen_fl [cen_banks ft_lines]
	pf_bp $rom $::cen_a(bg_tot) {set ::cen_t3 [machine_info time]} [cen_banks bg_tot]
	# the budget's end: the instruction after sprites_tick's "call budget"
	set st $::cen_a(sprites_tick)
	set sb [cen_banks sprites_tick]
	set rf [open $rom rb]
	catch {
		fconfigure $rf -translation binary
		seek $rf [pf_romoff $st [lindex $sb 0]]
		set blk [read $rf 64]
	}
	close $rf
	set i [string first [binary format cs 0xCD $::cen_a(budget)] $blk]
	if {$i < 0} { error "cen: no call budget in sprites_tick" }
	pf_bp $rom [expr {$st + $i + 3}] cen_end $sb
	pf_bp $rom $::cen_a(fl_hit) {incr ::cen_c(lhit)} [cen_banks fl_hit]
	pf_bp $rom $::cen_a(ft_give) cen_give [cen_banks ft_give]
	pf_bp $rom $::cen_a(ft_drop_t) {incr ::cen_c(drop)} [cen_banks ft_drop_t]
	pf_bp $rom $::cen_a(ft_leave_t) {incr ::cen_c(leave)} [cen_banks ft_leave_t]
	pf_bp $rom $::cen_a(ft_cand) {incr ::cen_c(cand)} [cen_banks ft_cand]
	pf_bp $rom $::cen_a(ft_anyb) {incr ::cen_c(anyb)} [cen_banks ft_anyb]
	pf_bp $rom $::cen_a(ln_add) cen_lnadd [cen_banks ln_add]
	return "cen armed"
}

proc cen_b0 {} {
	set ::cen_on 1
	set ::cen_t0 [machine_info time]
	set ::cen_t1 -1
	set ::cen_t2 -1
	set ::cen_t3 -1
	set ::cen_gives 0
	set ::cen_rch ""
	set ::cen_fh ""
	set ::cen_oh ""
	foreach k {lhit gl gt drop leave cand anyb lal lat} { set ::cen_c($k) 0 }
}

proc cen_rc {} {
	if {!$::cen_on} return
	binary scan [debug read_block memory 0xE000 $::cen_vl] H* ::cen_rch
}

proc cen_fl {} {
	if {!$::cen_on} return
	set ::cen_t2 [machine_info time]
	binary scan [debug read_block memory 0xE000 $::cen_vl] H* ::cen_fh
	binary scan [debug read_block memory $::cen_a(obj_tab) 512] H* ::cen_oh
}

proc cen_give {} {
	if {!$::cen_on} return
	set ::cen_gives 1
	if {[peek $::cen_a(ft_line)] == 255} { incr ::cen_c(gt) } else { incr ::cen_c(gl) }
}

proc cen_lnadd {} {
	if {!$::cen_on || !$::cen_gives} return
	if {[peek $::cen_a(ft_line)] == 255} { incr ::cen_c(lat) } else { incr ::cen_c(lal) }
}

proc cen_end {} {
	if {!$::cen_on} return
	set ::cen_on 0
	set t4 [machine_info time]
	set c [list]
	foreach k {lhit gl gt drop leave cand anyb lal lat} { lappend c $::cen_c($k) }
	puts $::h7_rf "R [rc2_w 0xCEE0] $::cen_t0 $::cen_t1 $::cen_t2 $::cen_t3 $t4 [join $c { }]"
	binary scan [debug read_block memory $::cen_a(obj_tab) 512] H* eh
	puts $::h7_rf "E [peek $::cen_a(bu_tot)] [peek [expr {$::cen_a(bu_tot) + 1}]] [peek $::cen_a(bu_cut)] $eh"
	if {$::cen_t1 != -1} {
		puts $::h7_rf "C $::cen_rch"
		puts $::h7_rf "F $::cen_fh"
		puts $::h7_rf "O $::cen_oh"
	}
}

proc cen_done {} {
	if {!$::rc2_trace_done} { return 0 }
	if {!$::cen_written} {
		set ::cen_written 1
		catch {close $::h7_rf}
		unset -nocomplain ::h7_rf
	}
	return 1
}

proc cen_jobs {dir rom labels drive n {machines {m2 C-BIOS_MSX2}}} {
	file mkdir $dir
	set jobs {}
	set dn [file rootname [file tail $drive]]
	foreach {t m} $machines {
		lappend jobs [list cen_${dn}_$t $m [list cen_setup "$dir/cen_${dn}_$t.txt" $rom $labels $drive $n] {[cen_done]} 3600]
	}
	return $jobs
}
