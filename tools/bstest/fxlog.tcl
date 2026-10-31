# fxlog.tcl: the sound effects write for write (docs/LEVEL2.md 4.3, docs/HARNESS.md 5.23), jobs for
# hz.tcl's hz_chain (load.tcl sources this file): every write to the PSG's sound registers (R0-R13),
# to the SCC's (9800h-98FFh) and to the OPLL, with the sound engine's events around them. Checked by
# tools/bstest/fxcheck.py: the engine's model replays every request and every tick from the state
# at the arming and must give the same writes, in the same order. MCP-safe: no exit, vwait, max or
# min; the lines stay in memory until the job's end writes the file (a job that times out leaves no
# channel open and no log: its verdict fails).
#
# The log, a line each (the engine's routines by label, each only with its own bank mapped; a fixed
# routine only with its own bytes there, not the BIOS's during the boot):
#   I <ram> <rg9>   at the arming: RAM C000h-CFFFh (music.asm's voices, the PSG player's, the queue)
#                   and RG9SAV (FFE8h: bit 1, 50 Hz), as hex
#   F <n>           tick_start: game frame n begins (tick_n)
#   Q <a>           sndplay.asm sq_put: a request queued by the main program (snd_play, snd_stop)
#   Z               sq_mute (inside sq_put for a stop: R8-R10 = 0 at once)
#   Y               music.asm mus_stop (snd_stop with an SCC or an OPLL: mus_quiet)
#   B <hl>          front.asm fe_text's entry (a text screen, HL its script); b its return
#   V, W            the VBLANK's sound work: sound.asm snd_frame's entry, then sf_back
#   S <a>           sq_sfx (a request taken from the queue); G sq_gun; X sq_stop; M sq_title or
#                   music.asm mus_start (the title's music: fxcheck.py's model ends there)
#   T               sqf_t: a tick of the player (50 a second; at 60 Hz every sixth VBLANK none)
#   N               tune.asm tns_go: a tune of the stages starts (fxcheck.py does not model them)
#   U <left> <scc> <psg> <opll>   tune.asm tn_tick's entry: the tune's ticks left + 1 and the chips
#                   as its previous tick left them (the SCC's debuggable 00h-AFh, PSG R0-R13, the
#                   OPLL's 64 registers; "-" for a chip that is not there), from the job's start
#   P <r> <v>       a PSG write: register r (the latch; R14/R15, the I/O ports, left out) = v
#   C <a> <v> <k>   a write to 9800h-98FFh (a hex): k = c the cartridge's SCC (page 2 its slot, the
#                   mapper's bank there 3Fh), x another slot's (page 2 not the cartridge's slot), -
#                   neither (the cartridge's ROM: a write no chip gets)
#   O <r> <v>       an OPLL write (7Ch the latch, 7Dh the data)
#   E <ram> <rg9>   at the end: as I
#   # ...           the job's notes
# Before the arming only U and N lines are kept.
#
# Jobs (fxl_jobs DIR R): see that proc. One job alone:
#   hz_chain [list [fxl_drive_job NAME MACHINE ROM LABELS OUT N DRIVE EXTS]]

proc fxl_put {s} { if {$::fxl_on} { lappend ::fxl_buf $s } }

proc fxl_hex {dev n} {
	if {$dev eq ""} { return "-" }
	binary scan [debug read_block $dev 0 $n] H* x
	return $x
}

proc fxl_ram {} {
	binary scan [debug read_block memory 0xC000 0x1000] H* r
	return "$r [format %02x [peek 0xFFE8]]"
}

# the SCC the game uses (scc_pg2: 0 the cartridge's own, named after the ROM; else another slot's)
# and the OPLL's registers' debuggable, once the game has found its chips
proc fxl_devs {} {
	set own ""
	set other ""
	foreach d [debug list] {
		if {[string match "* SCC" $d]} {
			if {[string match "[file tail $::fxl_rom]*" $d]} { set own $d } else { set other $d }
		}
	}
	set scc $own
	if {([peek $::fxl_a(scc_pg2)] != 0 && $other ne "") || $own eq ""} { set scc $other }
	if {!([peek $::fxl_a(mus_mode)] & 1)} { set scc "" }
	set fm ""
	foreach d [debug list] {
		if {[string match "*regs" $d] && ([string match -nocase "*music*" $d] || [string match -nocase "*fm*" $d])} {
			set fm $d
		}
	}
	return [list $scc $fm]
}

proc fxl_tune {} {
	if {$::fxl_devs eq "?"} { set ::fxl_devs [fxl_devs] }
	lassign $::fxl_devs scc fm
	lappend ::fxl_buf "U [rc2_w $::fxl_a(tn_left)] [fxl_hex $scc 0xB0] [fxl_hex {PSG regs} 14] [fxl_hex $fm 64]"
	incr ::fxl_nu
}

proc fxl_psg {} {
	if {($::wp_last_address & 1) == 0} {
		set ::fxl_lat [expr {$::wp_last_value & 0x0F}]
	} elseif {$::fxl_on && $::fxl_lat < 14} {
		lappend ::fxl_buf "P $::fxl_lat $::wp_last_value"
	}
}

proc fxl_scc {} {
	if {!$::fxl_on} return
	set a8 [debug read ioports 0xA8]
	set k -
	if {(($a8 >> 4) & 3) != (($a8 >> 2) & 3)} {
		set k x
	} elseif {[debug read $::fxl_rb 0x9800] == 0x3F} {
		set k c
	}
	lappend ::fxl_buf [format "C %04x %d %s" $::wp_last_address $::wp_last_value $k]
}

proc fxl_opll {} {
	if {($::wp_last_address & 1) == 0} {
		set ::fxl_olat $::wp_last_value
	} elseif {$::fxl_on} {
		lappend ::fxl_buf "O $::fxl_olat $::wp_last_value"
	}
}

proc fxl_arm_now {} {
	if {$::fxl_on} return
	set ::fxl_on 1
	lappend ::fxl_buf "I [fxl_ram]"
}

proc fxl_tick {} {
	if {$::fxl_arm eq "tick"} { fxl_arm_now }
	fxl_put "F [rc2_w $::fxl_a(tick_n)]"
}

# fe_text's entry: B, its return's breakpoint (SP back above the return address); an armed screen
# (ARM = its script's label) arms the log; its end, END_S emulated seconds after its return, ends
# the job
proc fxl_text {} {
	set hl [reg hl]
	if {!$::fxl_on && $::fxl_arm ne "tick" && $hl == $::fxl_armhl} {
		fxl_arm_now
		set ::fxl_mine 1
	} else {
		set ::fxl_mine 0
	}
	fxl_put [format "B %04x" $hl]
	set sp [reg sp]
	set ret [rc2_w $sp]
	set ::fxl_bret [debug set_bp $ret "\[reg sp\] == [expr {$sp + 2}]" fxl_text_end]
	lappend ::fxl_bps $::fxl_bret
}

proc fxl_text_end {} {
	fxl_put "b"
	catch {debug remove_bp $::fxl_bret}
	if {$::fxl_mine && $::fxl_endtext} {
		set ::fxl_mine 0
		lappend ::hz_afters [after time $::fxl_ends fxl_end]
	}
}

# a fixed routine's breakpoint condition: its first three bytes as the ROM holds them (4000h-7FFFh:
# file offset A - 4000h), so that the BIOS's code there during the boot does not fire it
proc fxl_fixed {addr} {
	set f [open $::fxl_rom rb]
	seek $f [expr {$addr - 0x4000}]
	binary scan [read $f 3] cucucu b0 b1 b2
	close $f
	return "\[peek $addr\] == $b0 && \[peek [expr {$addr + 1}]\] == $b1 && \[peek [expr {$addr + 2}]\] == $b2"
}

# fxl_arm ROM LABELS OUT ARM ?ENDTEXT? ?ENDS?: the log's breakpoints and watchpoints in the running
# machine (after rc2_drive_rom or a reset: set them last). ARM: "tick" (the first tick_start) or a
# script's label (fe_text's entry with HL there: txt_l2_brief, txt_l3_brief, txt_cont). ENDTEXT 1:
# the job ends ENDS emulated seconds after that screen's return (fxl_end); else the job's done
# condition calls fxl_end.
proc fxl_arm {rom labels out arm {endtext 0} {ends 1.0}} {
	set ::fxl_rom $rom
	set ::fxl_out $out
	set ::fxl_arm $arm
	set ::fxl_endtext $endtext
	set ::fxl_ends $ends
	set ::fxl_on 0
	set ::fxl_fin 0
	set ::fxl_buf {}
	set ::fxl_bps {}
	set ::fxl_wps {}
	set ::fxl_lat 0
	set ::fxl_olat 0
	set ::fxl_nu 0
	set ::fxl_mine 0
	set ::fxl_devs "?"
	set ::fxl_rb "[file tail $rom] romblocks"
	foreach k {tick_start game_tick tick_n snd_frame sf_back sq_put sq_mute sq_sfx sq_gun sq_stop sq_title sqf_t
	           mus_stop mus_start fe_text tns_go tn_tick tn_left scc_pg2 mus_mode BANK_INPUT BANK_MUSIC BANK_FRONT} {
		set ::fxl_a($k) [rc2_label $labels $k]
	}
	set ::fxl_armhl 0
	if {$arm ne "tick"} { set ::fxl_armhl [rc2_label $labels $arm] }
	set ci "\[debug read {$::fxl_rb} 0xA000\] == $::fxl_a(BANK_INPUT)"
	set cm "\[debug read {$::fxl_rb} 0xA000\] == $::fxl_a(BANK_MUSIC)"
	set cf "\[debug read {$::fxl_rb} 0x8000\] == $::fxl_a(BANK_FRONT)"
	set ts $::fxl_a(tick_start)
	foreach {name cond cmd} [list \
			tick_start "\[peek $ts\] == 0xCD && \[rc2_w [expr {$ts + 1}]\] == $::fxl_a(game_tick)" fxl_tick \
			sq_put $ci {fxl_put "Q [reg a]"} \
			sq_mute $ci {fxl_put Z} \
			mus_stop $cm {fxl_put Y} \
			snd_frame [fxl_fixed $::fxl_a(snd_frame)] {fxl_put V} \
			sf_back [fxl_fixed $::fxl_a(sf_back)] {fxl_put W} \
			sq_sfx $ci {fxl_put "S [reg a]"} \
			sq_gun $ci {fxl_put G} \
			sq_stop $ci {fxl_put X} \
			sq_title $ci {fxl_put M} \
			mus_start $cm {fxl_put M} \
			sqf_t $ci {fxl_put T} \
			fe_text $cf fxl_text \
			tns_go $cm {lappend ::fxl_buf N} \
			tn_tick $cm fxl_tune] {
		lappend ::fxl_bps [debug set_bp $::fxl_a($name) $cond $cmd]
	}
	lappend ::fxl_wps [debug set_watchpoint write_io {0xA0 0xA1} {} fxl_psg]
	lappend ::fxl_wps [debug set_watchpoint write_mem {0x9800 0x98FF} {} fxl_scc]
	lappend ::fxl_wps [debug set_watchpoint write_io {0x7C 0x7D} {} fxl_opll]
}

# the log written (E, the notes), every breakpoint and watchpoint of it removed; returns 1 (a done
# condition's last term)
proc fxl_end {} {
	if {$::fxl_fin} { return 1 }
	set ::fxl_fin 1
	foreach b $::fxl_bps { catch {debug remove_bp $b} }
	foreach w $::fxl_wps { catch {debug remove_watchpoint $w} }
	set ::fxl_bps {}
	set ::fxl_wps {}
	if {$::fxl_on} { lappend ::fxl_buf "E [fxl_ram]" }
	lappend ::fxl_buf "# [machine_info config_name], emulated [format %.3f [machine_info time]] s, armed $::fxl_on, $::fxl_nu U lines"
	set f [open $::fxl_out w]
	catch {puts $f [join $::fxl_buf "\n"]}
	close $f
	set ::fxl_buf {}
	set ::pause on
	return 1
}

# extensions (scc, scc+, fmpac) into cartridge slot B before the cartridge
proc fxl_exts {exts} { foreach e $exts { extb $e } }

# a drive (tools/openmsx_rc2.tcl rc2_drive_rom: N rows into OUT's trace) logged from its first tick
proc fxl_drive_setup {rom labels out n drive exts} {
	fxl_exts $exts
	rc2_drive_rom $rom $labels "[file rootname $out]_trace.txt" $n 0 $drive
	fxl_arm $rom $labels $out tick
}

proc fxl_drive_job {name m rom labels out n drive {exts {}}} {
	return [list $name $m [list fxl_drive_setup $rom $labels $out $n $drive $exts] {$::rc2_trace_done && [fxl_end]} 1800]
}

# a build from its power-on (no script, or a script build's own start), logged from the text screen
# ARM's entry to ENDS emulated seconds after its return; GUARD emulated seconds at most
proc fxl_text_setup {rom labels out arm exts guard} {
	fxl_exts $exts
	foreach {id opts} [debug breakpoint list] { debug breakpoint remove $id }
	foreach {id opts} [debug condition list] { debug condition remove $id }
	carta eject
	carta insert $rom -romtype KonamiSCC
	if {[debug breaked]} { debug cont }
	set ::pause off
	reset
	fxl_arm $rom $labels $out $arm 1 1.0
	lappend ::hz_afters [after time $guard {if {!$::fxl_fin} { lappend ::fxl_buf "# no end in the guard's time"; fxl_end }}]
}

proc fxl_text_job {name m rom labels out arm {exts {}} {guard 600}} {
	return [list $name $m [list fxl_text_setup $rom $labels $out $arm $exts $guard] {$::fxl_fin} 1800]
}

# fxl_jobs DIR R ?ONLY?: level 2's sound logs (docs/LEVEL2.md 4.3) on the builds of "hz.sh fxbuilds R",
# C-BIOS_MSX2, into DIR (ONLY: a list of job names):
#   d_<drive>_<k>  the bench's drive (tour 2654, vat 701, mine 161, end 259, t1left 341, trolley 641
#                  rows) on chips k: scc (R/l2: EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2, the
#                  cartridge's SCC), ext (R/l2x: + NO_SCC_INT=1, an SCC cartridge in slot B), psg
#                  (R/l2n: + NO_SCC=1, the PSG alone): DIR/d_<drive>_<k>.txt, the trace beside it
#   cont_<k>       the cont drive (301 rows) on R/l2c (scc) and R/l2cn (psg): level 2, its game over,
#                  PIC9, the continue offer taken, level 2 again
#   brief_<k>      R/l2 (scc), R/l2n (psg) from the power-on: LV_TEST's briefing (txt_l2_brief) to 1 s
#                  after it, the level's set-up within
#   pz<v>_<k>      R/pz1 (PZ_TEST=1), R/pz2 (PZ_TEST=1 PZ_LEVEL=2), and R/pz2n (+ NO_SCC=1) from the
#                  power-on, no script: Brainstorm and the range of visit v left alone (their tunes in
#                  U lines), then the next level's briefing (txt_l2_brief, txt_l3_brief) logged to 1 s
#                  after it
proc fxl_jobs {dir R {only ""}} {
	file mkdir $dir
	set e "$::hz_root/build/emu"
	set m C-BIOS_MSX2
	set jobs {}
	foreach {k b exts} {scc l2 {} ext l2x scc psg l2n {}} {
		foreach {d n} {tour 2654 vat 701 mine 161 end 259 t1left 341 trolley 641} {
			lappend jobs [fxl_drive_job d_${d}_$k $m "$R/$b/rc2.rom" "$R/$b/rc2.labels" "$dir/d_${d}_$k.txt" $n "$e/l2_$d.drive" $exts]
		}
	}
	foreach {k b} {scc l2c psg l2cn} {
		lappend jobs [fxl_drive_job cont_$k $m "$R/$b/rc2.rom" "$R/$b/rc2.labels" "$dir/cont_$k.txt" 301 "$e/l2_cont.drive"]
	}
	foreach {k b} {scc l2 psg l2n} {
		lappend jobs [fxl_text_job brief_$k $m "$R/$b/rc2.rom" "$R/$b/rc2.labels" "$dir/brief_$k.txt" txt_l2_brief]
	}
	foreach {t b arm} {pz1_scc pz1 txt_l2_brief pz2_scc pz2 txt_l3_brief pz1_psg pz1n txt_l2_brief pz2_psg pz2n txt_l3_brief} {
		lappend jobs [fxl_text_job $t $m "$R/$b/rc2.rom" "$R/$b/rc2.labels" "$dir/$t.txt" $arm {} 900]
	}
	if {$only eq ""} { return $jobs }
	set out {}
	foreach j $jobs { if {[lsearch -exact $only [lindex $j 0]] >= 0} { lappend out $j } }
	return $out
}

set ::fxl_loaded "fxlog.tcl loaded"
