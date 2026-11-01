# m3.tcl (tools/bstest/perf2, performance campaign 2's kit; docs/HARNESS.md section 12): a level's speed
# and where its time goes, measured from Tcl only. Breakpoints and probes take no emulated time, so the
# records time the game exactly as it runs without them (m_l3 checked it: the tick times of a run with
# every probe and of one without are identical). m_l3's instrumentation of 2026-11-01, with every
# address taken from the build's own label file and ROM (m3_addrs), and three modes. Source
# tools/bstest/perf2/load.tcl (it sources the harness first).
#
#   m3_job NAME MACHINE DIR ROM LABELS DRIVE N ?MODE?
#       one drive (a build/emu drive file: N rows from tick 0, with rc2_drive_rom's inputs, teleports,
#       pokes and god flag at every tick_start, without its RAM dump) on one machine. MODE:
#         lean  (default) ticks, pics, pubs, frames, fcs: G-SPEED (win.py) and G-HOLD (holds.py)
#         flash lean + per tick the BOBs drawn as a colour-15 silhouette (bob.asm bd_mode with BM_FLASH:
#               levels 1-2's hit flash; level 3's white copies): two more fields on each ticks line
#         cmds  lean + every VDP command started (cmds) and the command engine's probe (ce): sync3.py
#         full  cmds + a PC sample every 0.2 ms (samp): m_l3's profiles
#   m3_jobs DIR ROM LABELS DRIVE N TAGS ?MODE? ?PREFIX?
#       m3_job on each machine of TAGS ({tag machine ...}, e.g. $::pf_m4); NAME = PREFIX_tag (PREFIX:
#       the drive file's name without l3_/l2_ and .drive by default)
#   m3_job2 NAME MACHINE DIR ROM LABELS DRIVE N S0 S1   full + 24 bytes at SP in each sample (ticks S0-S1)
#   m3_job3 NAME MACHINE DIR ROM LABELS DRIVE N S0 S1   full + an ISR flag and the whole return chain
#
# Records, DIR/NAME_<kind>.txt (the formats of m_l3's runs, which win.py, holds.py and sync3.py read):
#   ticks:  per game tick (tick_start's call of game_tick): tick_n, emulated time, fb_add calls and
#           BM_FLASH ones, frame-cache uploads (count, bytes, seconds), commands started, RoboCop x y,
#           camera x y (the counters since the tick before; commands 0 in lean mode); in flash mode
#           then the silhouette BOBs drawn in the tick: those of a tick whose BOBs are shown (bob_skip
#           0), all
#   pics:   per picture put on screen (isr.asm iv_take): time, the tick last started, fb_hold (the
#           VBLANKs fb_pend held it: FB_HOLD = a picture shown with its play-field BOBs not all
#           composed), the list's game frame, the VBLANK counter
#   pubs:   per list published (isr.asm publish): time, tick
#   frames: per main-loop frame (player.asm cadence at cd_cap): time, tick, wf_n, ticks due, the cap
#   fcs:    per frame-cache upload (field.asm fcg_ld .. fcg_dn): start, seconds, bytes, lines, tick
#   cmds:   per VDP command started (the instruction after R#46 in vdp_cmd, vdp_cmd_q, ifg_send, fb_go,
#           fb_qstart): site, time, tick, R#32-R#46 as hex, the caller's return address, act_8000,
#           act_a000, its duration (to the engine's next idle, the sampler's or the next start's time)
#   ce:     VDP.commandExecuting probe transitions: value time
#   samp:   every 0.2 ms: pc act_8000 act_a000 CE (S#2 bit 0); "T tick time" lines at ticks
#   notes:  what the set-up found: the addresses, a probe left out (a label this build lacks)
# Rules kept: no vwait, exit, max or min; every channel closed on every path (hz_clean's wrapper);
# breakpoints on A000h code conditioned on act_a000 = the code's bank.

# ----- labels and addresses

# every label of a z80asm label file into ::pf_L (name -> integer)
proc pf_lab_load {labels} {
	array unset ::pf_L
	set f [open $labels r]
	catch {
		while {[gets $f line] >= 0} {
			if {[regexp {^(\w+):\s+equ \$([0-9a-fA-F]+)} $line -> k h]} { set ::pf_L($k) [scan $h %x] }
		}
	}
	close $f
	if {![info exists ::pf_L(tick_start)]} { error "pf_lab_load: no tick_start in $labels" }
}

# a label's value; DEF when the build has none (an error without DEF)
proc pf_lab {name {def ""}} {
	if {[info exists ::pf_L($name)]} { return $::pf_L($name) }
	if {$def ne ""} { return [expr {$def}] }
	error "no label $name"
}

# a ROM file offset: the fixed area 4000h-7FFFh is the image's first 16 KiB, a banked address is
# BANK x 8 KiB on
proc pf_romoff {addr {bank ""}} {
	if {$addr >= 0x4000 && $addr < 0x8000} { return [expr {$addr - 0x4000}] }
	if {$bank eq ""} { error "pf_romoff: [format %04X $addr] needs a bank" }
	return [expr {$bank * 0x2000 + ($addr & 0x1FFF)}]
}

# the address right after the first PATTERN (a byte string) within LIMIT bytes of label NAME
proc pf_find_after {rom name pat {bank ""} {limit 80}} {
	set a [pf_lab $name]
	set f [open $rom rb]
	set blk ""
	catch {
		fconfigure $f -translation binary
		seek $f [pf_romoff $a $bank]
		set blk [read $f $limit]
	}
	close $f
	set i [string first $pat $blk]
	if {$i < 0} { error "pf_find_after: $name: pattern not found" }
	return [expr {$a + $i + [string length $pat]}]
}

# the build's addresses: ::m3_a (routines, banks), ::m3_r (RAM, HEAD's addresses when a label is
# missing), ::m3_csites (the VDP command sites), ::m3_miss (labels this build lacks)
proc m3_addrs {rom labels} {
	pf_lab_load $labels
	array unset ::m3_a
	array unset ::m3_r
	set ::m3_miss {}
	foreach k {tick_start game_tick iv_take publish cd_cap} { set ::m3_a($k) [pf_lab $k] }
	foreach k {fb_add fcg_ld fcg_ln fcg_dn isr_vblank wait_frame isr isr_r15 BANK_FIELD BANK_L1 BANK_L2 BANK_L3 BANK_L3B FB_HOLD} {
		if {[info exists ::pf_L($k)]} { set ::m3_a($k) $::pf_L($k) } else { lappend ::m3_miss $k }
	}
	foreach {k def} {tick_n 0xCEE0 act_8000 0xC07C act_a000 0xC07D fb_hold 0xF1EB pk_list 0xC0E1 tick 0xC001
			wf_n 0xCE7A fc_bpl 0xECF9 ext_joy 0xCE5A lv_cur 0xF1A0} {
		set ::m3_r($k) [pf_lab $k $def]
	}
	set otir "\xED\xB3"
	set r46 "\x3E\xAE\xD3\x99"
	set ::m3_csites {}
	foreach {site pat off spo where} [list vdp_cmd $otir 15 0 fixed vdp_cmd_q $r46 14 0 fixed \
			ifg_send $otir 15 2 fixed fb_go $otir 15 0 field fb_qstart $r46 14 0 field] {
		if {[catch {
			set bank [expr {$where eq "field" ? $::m3_a(BANK_FIELD) : ""}]
			lappend ::m3_csites [list $site [pf_find_after $rom $site $pat $bank] $off $spo $where]
		} err]} { lappend ::m3_miss "$site ($err)" }
	}
}

# ----- the jobs

proc m3_close {} {
	if {[info exists ::m3_sf]} { catch {close $::m3_sf}; unset ::m3_sf }
	if {[info exists ::m3_aft]} { catch {after cancel $::m3_aft}; unset ::m3_aft }
	catch {foreach line [split [debug probe list_bp] "\n"] {
		set id [lindex $line 0]
		if {$id ne ""} { catch {debug probe remove_bp $id} }
	}}
}
if {[info commands hz_clean_m3orig] eq ""} { rename hz_clean hz_clean_m3orig }
proc hz_clean {} { m3_close; hz_clean_m3orig }

proc m3_job {name m dir rom labels drive n {mode lean}} {
	return [list $name $m [list m3_setup $name $dir $rom $labels $drive $n $mode] {[m3_done]} 3600]
}

proc m3_jobs {dir rom labels drive n tags {mode lean} {prefix ""}} {
	if {$prefix eq ""} { set prefix [m3_drive_tag $drive] }
	set jobs {}
	foreach {t m} $tags { lappend jobs [m3_job ${prefix}_$t $m $dir $rom $labels $drive $n $mode] }
	return $jobs
}

# build/emu/l3_kill.drive -> kill, l2_tour.drive -> l2tour, drive_play.txt -> l1play
proc m3_drive_tag {drive} {
	set b [file rootname [file tail $drive]]
	if {[string match l3_* $b]} { return [string range $b 3 end] }
	if {[string match l2_* $b]} { return "l2[string range $b 3 end]" }
	if {[string match drive_* $b]} { return "l1[string range $b 6 end]" }
	return $b
}

proc m3_zero {} {
	foreach k {add fl fcn fcb cmd} { set ::m3_c($k) 0 }
	set ::m3_c(fct) 0.0
}

proc m3_setup {name dir rom labels drive n {mode lean}} {
	if {$mode ni {lean flash cmds full}} { error "m3: mode $mode (lean, flash, cmds or full)" }
	file mkdir $dir
	m3_addrs $rom $labels
	set ::m3_base "$dir/$name"
	set ::m3_mode $mode
	set ::m3_written 0
	foreach v {m3_ticks m3_pics m3_pubs m3_frames m3_cmds m3_fcs m3_ce} { set ::$v {} }
	set ::m3_copen 0
	set ::m3_tk -1
	m3_zero
	set ::m3_tn $::m3_r(tick_n)
	set ::m3_a8 $::m3_r(act_8000)
	set ::m3_aa $::m3_r(act_a000)
	# the lean drive: rc2_drive_rom's inputs without its RAM dump
	foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
	foreach {id opts} [debug condition list] { debug condition remove $id }
	carta eject
	carta insert $rom -romtype KonamiSCC
	if {[debug breaked]} { debug cont }
	set ::pause off
	reset
	set f [open $drive r]
	catch {
		set ::rd_joy [string trim [gets $f]]
		set ::rd_tele {}
		foreach t [split [string trim [gets $f]]] { if {$t ne ""} { lappend ::rd_tele [split $t :] } }
		set ::rd_god [string trim [gets $f]]
		set ::rd_poke {}
		foreach t [split [string trim [gets $f]]] { if {$t ne ""} { lappend ::rd_poke [split $t :] } }
	}
	close $f
	set ::rd_left $n
	set ::rd_from 0
	set ::rc2_trace_done 0
	set ts $::m3_a(tick_start)
	set gt $::m3_a(game_tick)
	set ::m3_bp_tick [debug set_bp $ts "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $gt" m3_tick]
	debug set_bp $::m3_a(iv_take) {} m3_take
	debug set_bp $::m3_a(publish) {} m3_pub
	debug set_bp $::m3_a(cd_cap) {} m3_cad
	if {[info exists ::m3_a(fb_add)]} { debug set_bp $::m3_a(fb_add) {} m3_fbadd }
	set notes [list "rom $rom" "mode $mode" "drive $drive rows $n"]
	if {[info exists ::m3_a(BANK_FIELD)]} {
		set bf $::m3_a(BANK_FIELD)
		set c "\[peek $::m3_aa\] == $bf"
		if {[info exists ::m3_a(fcg_ld)] && [info exists ::m3_a(fcg_dn)]} {
			debug set_bp $::m3_a(fcg_ld) $c m3_fcld
			debug set_bp $::m3_a(fcg_dn) $c m3_fcdn
			if {[info exists ::m3_a(fcg_ln)]} { debug set_bp $::m3_a(fcg_ln) $c {incr ::m3_fcl} }
		}
	}
	set ::m3_fds 0
	set ::m3_fdn 0
	if {$mode eq "flash"} {
		set ::m3_bsk [pf_lab bob_skip]
		debug set_bp [pf_lab bd_mode] "((\[reg af\] >> 8) & 0xFF) == [pf_lab BM_FLASH 1]" m3_fd
	}
	if {$mode in {cmds full}} {
		foreach s $::m3_csites {
			lassign $s site addr off spo where
			if {$where eq "field"} {
				debug set_bp $addr "\[peek $::m3_aa\] == $::m3_a(BANK_FIELD)" [list m3_cmd $site $off $spo]
			} else {
				debug set_bp $addr {} [list m3_cmd $site $off $spo]
			}
			lappend notes [format "site %s %04X" $site $addr]
		}
		if {[llength $::m3_csites] < 5} { error "m3: command sites missing ($::m3_miss)" }
		debug probe set_bp VDP.commandExecuting {} m3_ceprobe
	}
	if {$mode eq "full"} {
		set ::m3_sf [open "${::m3_base}_samp.txt" w]
		set ::m3_aft [after time 0.0002 m3_samp]
	}
	foreach k $::m3_miss { lappend notes "missing: $k" }
	set f [open "${::m3_base}_notes.txt" w]
	catch { foreach x $notes { puts $f $x } }
	close $f
	return "m3 $name set ($mode)"
}

proc m3_ceprobe {} {
	lappend ::m3_ce "[debug probe read VDP.commandExecuting] [machine_info time]"
}

proc m3_samp {} {
	set ce [expr {[debug read "VDP status regs" 2] & 1}]
	puts $::m3_sf "[reg pc] [peek $::m3_a8] [peek $::m3_aa] $ce"
	if {$::m3_copen && !$ce} { m3_cclose [machine_info time] }
	set ::m3_aft [after time 0.0002 m3_samp]
}

proc m3_tick {} {
	set gf [rc2_w $::m3_tn]
	set t [machine_info time]
	set row "$gf $t $::m3_c(add) $::m3_c(fl) $::m3_c(fcn) $::m3_c(fcb) $::m3_c(fct) $::m3_c(cmd) [rc2_w 0xDAD0] [rc2_w 0xDAD4] [rc2_w 0xD004] [rc2_w 0xD006]"
	if {$::m3_mode eq "flash"} {
		append row " $::m3_fds $::m3_fdn"
		set ::m3_fds 0
		set ::m3_fdn 0
	}
	lappend ::m3_ticks $row
	m3_zero
	set ::m3_tk $gf
	if {[info exists ::m3_sf]} { puts $::m3_sf "T $gf $t" }
	m3_drive $gf
}

# rc2_drive_hit's inputs (tools/openmsx_rc2.tcl) for game frame GF: the drive's joystick byte, its
# teleports, pokes and god flag (the Amiga mirror's addresses); the drive's end pauses the machine
proc m3_drive {gf} {
	if {$gf >= $::rd_from && $::rd_left > 0} {
		incr ::rd_left -1
		if {$::rd_left == 0} {
			debug remove_bp $::m3_bp_tick
			set ::rc2_trace_done 1
			set ::pause on
			return
		}
	}
	set i [expr {2 * $gf}]
	set b [string range $::rd_joy $i [expr {$i + 1}]]
	poke $::m3_r(ext_joy) [expr {$b eq "" ? 0 : "0x$b"}]
	foreach tt $::rd_tele {
		lassign $tt tf tx ty
		if {$tf == $gf} {
			rc2_wset 0xDAD0 $tx
			rc2_wset 0xDAD4 $ty
			set cx [expr {$tx - 0x108}]
			if {$cx < 0} { set cx 0 }
			if {$cx > 0x8E0} { set cx 0x8E0 }
			set cy [expr {$ty - 0x70}]
			if {$cy < 0} { set cy 0 }
			rc2_wset 0xD004 $cx
			rc2_wset 0xD006 $cy
		}
	}
	foreach tt $::rd_poke {
		lassign $tt pf pa pv ps
		if {$pf == $gf} {
			set mm [expr {$pa >= 0x8000 ? 0x5C00 + $pa : 0xC500 + $pa}]
			if {$ps == 1} { poke [expr {$mm ^ 1}] [expr {$pv & 0xFF}] } else { rc2_wset $mm $pv }
		}
	}
	if {$::rd_god} {
		rc2_wset 0xDB9A 0x100
		rc2_wset 0xDBC4 0x100
		rc2_wset 0xDC34 2
	}
}

# a BOB drawn as a silhouette (flash mode)
proc m3_fd {} {
	incr ::m3_fdn
	if {[peek $::m3_bsk] == 0} { incr ::m3_fds }
}

proc m3_take {} {
	set l [rc2_w $::m3_r(pk_list)]
	set len [peek [expr {($l + 1) & 0xFFFF}]]
	set gfr [rc2_w [expr {($l + 2 + $len + 4) & 0xFFFF}]]
	lappend ::m3_pics "[machine_info time] $::m3_tk [peek $::m3_r(fb_hold)] $gfr [peek $::m3_r(tick)]"
}

proc m3_pub {} { lappend ::m3_pubs "[machine_info time] $::m3_tk" }

proc m3_cad {} {
	lappend ::m3_frames "[machine_info time] $::m3_tk [peek $::m3_r(wf_n)] [expr {[reg bc] >> 8}] [expr {[reg de] >> 8}]"
}

proc m3_fbadd {} {
	incr ::m3_c(add)
	if {[peek [expr {([reg ix] + 9) & 0xFFFF}]] & 1} { incr ::m3_c(fl) }
}

proc m3_fcld {} {
	set ::m3_fct0 [machine_info time]
	set ::m3_fcl 0
}

proc m3_fcdn {} {
	if {![info exists ::m3_fct0]} return
	set dt [expr {[machine_info time] - $::m3_fct0}]
	set by [expr {$::m3_fcl * [peek $::m3_r(fc_bpl)]}]
	incr ::m3_c(fcn)
	incr ::m3_c(fcb) $by
	set ::m3_c(fct) [expr {$::m3_c(fct) + $dt}]
	lappend ::m3_fcs "$::m3_fct0 $dt $by $::m3_fcl $::m3_tk"
	unset ::m3_fct0
}

proc m3_cmd {site off spo} {
	set t [machine_info time]
	if {$::m3_copen} { m3_cclose $t }
	set b [expr {([reg hl] - $off) & 0xFFFF}]
	binary scan [debug read_block memory $b 15] H* hex
	set ret [rc2_w [expr {([reg sp] + $spo) & 0xFFFF}]]
	set ::m3_cur "$site $t $::m3_tk $hex $ret [peek $::m3_a8] [peek $::m3_aa]"
	set ::m3_copen 1
	incr ::m3_c(cmd)
}

proc m3_cclose {t} {
	lappend ::m3_cmds "$::m3_cur [expr {$t - [lindex $::m3_cur 1]}]"
	set ::m3_copen 0
}

proc m3_write {suffix lst} {
	set f [open "${::m3_base}_$suffix.txt" w]
	catch { foreach x $lst { puts $f $x } }
	close $f
}

proc m3_done {} {
	if {!$::rc2_trace_done} { return 0 }
	if {!$::m3_written} {
		set ::m3_written 1
		if {$::m3_copen} { m3_cclose [machine_info time] }
		m3_close
		m3_write ticks $::m3_ticks
		m3_write pics $::m3_pics
		m3_write pubs $::m3_pubs
		m3_write frames $::m3_frames
		m3_write fcs $::m3_fcs
		if {$::m3_mode in {cmds full}} {
			m3_write cmds $::m3_cmds
			m3_write ce $::m3_ce
		}
		foreach v {m3_ticks m3_pics m3_pubs m3_frames m3_cmds m3_fcs m3_ce} { set ::$v {} }
	}
	return 1
}

# The stack variant (m_l3's chain 2): every 0.2 ms also the 24 bytes at SP (the return addresses for an
# inclusive profile), only while the tick is within [S0, S1).
proc m3_job2 {name m dir rom labels drive n s0 s1} {
	return [list $name $m [list m3_setup2 $name $dir $rom $labels $drive $n $s0 $s1] {[m3_done]} 3600]
}
proc m3_setup2 {name dir rom labels drive n s0 s1} {
	set ::m3_s0 $s0
	set ::m3_s1 $s1
	m3_setup $name $dir $rom $labels $drive $n full
	after cancel $::m3_aft
	set ::m3_aft [after time 0.0002 m3_samp2]
	return "m3 $name set (stacks)"
}
proc m3_samp2 {} {
	set ce [expr {[debug read "VDP status regs" 2] & 1}]
	if {$::m3_tk >= $::m3_s0 && $::m3_tk < $::m3_s1} {
		binary scan [debug read_block memory [reg sp] 24] H* sk
		puts $::m3_sf "[reg pc] [peek $::m3_a8] [peek $::m3_aa] $ce [reg sp] $sk"
	}
	if {$::m3_copen && !$ce} { m3_cclose [machine_info time] }
	set ::m3_aft [after time 0.0002 m3_samp2]
}

# The deep-stack variant (m_l3's chain 3): every 0.2 ms the PC, the banks, CE, an ISR flag (isr's entry
# .. its reti, found after isr_r15 in the ROM) and every word from SP up to the stack's top (F380h)
# whose 3 bytes before hold a CALL opcode (as now mapped)
foreach op {0xCD 0xC4 0xCC 0xD4 0xDC 0xE4 0xEC 0xF4 0xFC} { set ::m3_callop([expr {$op}]) 1 }
proc m3_job3 {name m dir rom labels drive n s0 s1} {
	return [list $name $m [list m3_setup3 $name $dir $rom $labels $drive $n $s0 $s1] {[m3_done]} 3600]
}
proc m3_setup3 {name dir rom labels drive n s0 s1} {
	set ::m3_s0 $s0
	set ::m3_s1 $s1
	set ::m3_inisr 0
	m3_setup $name $dir $rom $labels $drive $n full
	set reti [expr {[pf_find_after $rom isr_r15 "\xED\x4D" "" 128] - 2}]
	debug set_bp $::m3_a(isr) {} {set ::m3_inisr 1}
	debug set_bp $reti {} {set ::m3_inisr 0}
	after cancel $::m3_aft
	set ::m3_aft [after time 0.0002 m3_samp3]
	return "m3 $name set (deep stacks)"
}
proc m3_samp3 {} {
	set ce [expr {[debug read "VDP status regs" 2] & 1}]
	if {$::m3_tk >= $::m3_s0 && $::m3_tk < $::m3_s1} {
		set sp [reg sp]
		set n [expr {0xF380 - $sp}]
		set fr {}
		if {$n > 1 && $n <= 256} {
			binary scan [debug read_block memory $sp $n] su* ws
			foreach w $ws {
				if {$w >= 0x4003 && $w < 0xC000 && [info exists ::m3_callop([peek [expr {$w - 3}]])]} { lappend fr [format %x $w] }
			}
		}
		puts $::m3_sf "[reg pc] [peek $::m3_a8] [peek $::m3_aa] $ce $::m3_inisr [join $fr ,]"
	}
	if {$::m3_copen && !$ce} { m3_cclose [machine_info time] }
	set ::m3_aft [after time 0.0002 m3_samp3]
}
