# frsound.tcl: the shooting range's sound in openMSX (docs/RANGE.md 4.3, docs/HARNESS.md 5.19), jobs
# for hz.tcl's hz_chain (load.tcl sources this file). MCP-safe: no exit, vwait, max or min; every
# file opened once and closed on every path; the recorder stopped on every path (hz_clean does not
# know it: each job's set-up stops a recording a TIMEOUT left running; end a chain with "catch
# {record stop}"). Check the logs with frsnd/frregcmp.py, the recordings with frsnd/frwavcmp.py and
# frsnd/fxalone.py (the venv's Python).
#
# The register log (frs_arm), one line each:
#   S <tick>          tn_start after its wait (tns_go, BANK_MUSIC at A000h)
#   P <$B00>          a pass (fr_tick, BANK_FRNG at A000h: before fr_frame's $B00 + 1)
#   R <n>             snd_rfx's entry (A = the request; BANK_FRNG at A000h)
#   T <tn_left> <tn_snd> <tn_busy> <tn_last> <tn_req> <mus_mode> <tn_mode> <scc> <psg> <opll>
#                     tn_tick's entry: the chips as the previous tick left them (scc: the SCC's
#                     debuggable 00h-AFh, "-" without one; psg R0-R15; opll its 64 registers or "-")
#   Q <psg> <opll> <scc> <scc regs> <psg regs> <opll regs>   snd_stop's entry after the tune's first
#                     tick, before fr_done (msx/frng.asm rg_end: the stage's own stop, right after
#                     its last pass): the sound writes counted from 50 ms after the tune's last tick
#                     (the T line with tn_left 1) to this stop (PSG R0-R13, OPLL 7Ch/7Dh, SCC
#                     9800h-98FFh: -1 when the tune did not end), then the chips as the last tick
#                     left them
#   X                 snd_stop called after fr_done (front.asm fe_text's: the result's screen)
#   E <psg> <opll> <scc> <scc regs> <psg regs> <opll regs>   at fr_done: the counts as Q's, to
#                     fr_done (they hold Q's stop's own writes), then the chips, which Q's stop
#                     silenced
#   Z <t lines after X> <scc regs> <psg regs> <opll regs>   1 emulated s after the stage's end (the
#                     result's screen): the chips, which snd_stop silenced
#
# Jobs:
#   frs_drive TAG MACHINE DIR ROM LABELS EXTS DRIVE ?PASSES? ?REC?
#       an EXTJOY=1 PZ_TEST=2 build driven by tools/openmsx_rc2.tcl rc2_fr_drive (the trace into
#       DIR/TAG_trace.txt), the log into DIR/TAG_fr.txt; REC 1: "record start -audioonly DIR/TAG.wav"
#       at the first tns_go, stopped at the Z line
#   frs_alone TAG MACHINE DIR ROM LABELS EXTS ?REC?
#       a PZ_TEST=2 build without a script from the power-on: the stage left alone (the real timer,
#       its time out after 2:00), the log into DIR/TAG_fr.txt; REC as above
# EXTS: openMSX extensions (scc, scc+, fmpac) into cartridge slot B (extb) before the cartridge.

set ::frs_dir [file dirname [file normalize [info script]]]

proc frs_hex {dev n} {
	if {$dev eq ""} { return "-" }
	binary scan [debug read_block $dev 0 $n] H* x
	return $x
}

# the SCC the game uses (scc_pg2 C20Ah: 0 the cartridge's own, named after the ROM; else another
# slot's) and the OPLL's registers' debuggable
proc frs_devs {} {
	set own ""
	set other ""
	foreach d [debug list] {
		if {[string match "* SCC" $d]} {
			if {[string match "[file tail $::frs_rom]*" $d]} { set own $d } else { set other $d }
		}
	}
	set scc $own
	if {([peek 0xC20A] != 0 && $other ne "") || $own eq ""} { set scc $other }
	set fm ""
	foreach d [debug list] {
		if {[string match "*regs" $d] && ([string match -nocase "*music*" $d] || [string match -nocase "*fm*" $d])} {
			set fm $d
		}
	}
	return [list $scc $fm]
}

proc frs_put {s} {
	if {[info exists ::frs_f]} { puts $::frs_f $s }
}

proc frs_chips {} {
	if {$::frs_devs eq "?"} { set ::frs_devs [frs_devs] }
	lassign $::frs_devs scc fm
	return "[frs_hex $scc 0xB0] [frs_hex {PSG regs} 16] [frs_hex $fm 64]"
}

proc frs_tick {} {
	set left [rc2_w $::frs_a(tn_left)]
	frs_put "T $left [peek $::frs_a(tn_snd)] [peek $::frs_a(tn_busy)] [peek $::frs_a(tn_last)] [peek $::frs_a(tn_req)] [peek $::frs_a(mus_mode)] [peek $::frs_a(tn_mode)] [frs_chips] [format %.6f [machine_info time]]"
	incr ::frs_nt
	if {$::frs_x} { incr ::frs_tx }
	if {$left == 1 && !$::frs_cnt} {
		lappend ::hz_afters [after time 0.05 {set ::frs_cnt 1}]
	}
}

proc frs_start {} {
	frs_put "S [peek $::frs_a(tick)] [format %.6f [machine_info time]]"
	if {$::frs_rec_on && !$::frs_rec} {
		if {[catch {record start -audioonly $::frs_wav} err]} {
			hz_msg "$::hz_jobname: record start failed: $err"
		} else {
			set ::frs_rec 1
			set ::frs_rec_t0 [machine_info time]
		}
	}
}

proc frs_psg {} {
	if {($::wp_last_address & 1) == 0} {
		set ::frs_lat [expr {$::wp_last_value & 0x0F}]
	} elseif {$::frs_cnt && $::frs_lat < 14} {
		incr ::frs_np
	}
}

proc frs_counts {} {
	if {$::frs_cnt} { return "$::frs_np $::frs_no $::frs_ns" }
	return "-1 -1 -1"
}

proc frs_done {} {
	if {$::frs_e} return
	set ::frs_e 1
	frs_put "E [frs_counts] [frs_chips]"
	lappend ::hz_afters [after time 1.0 frs_z]
}

# snd_stop's entry once the tune has ticked: the stage's own stop before fr_done (Q), fe_text's
# after it (X)
proc frs_stopcall {} {
	if {!$::frs_e} {
		if {!$::frs_q} {
			set ::frs_q 1
			frs_put "Q [frs_counts] [frs_chips]"
		}
	} elseif {!$::frs_x} {
		set ::frs_x 1
		frs_put "X"
	}
}

proc frs_z {} {
	frs_put "Z $::frs_tx [frs_chips]"
	frs_end
}

proc frs_recstop {} {
	if {[info exists ::frs_rec] && $::frs_rec} {
		catch {record stop}
		hz_msg [format "%s: recorded %.2f emulated s from the first tune start" $::hz_jobname [expr {[machine_info time] - $::frs_rec_t0}]]
	}
	set ::frs_rec 0
}

proc frs_end {} {
	if {$::frs_fin} return
	set ::frs_fin 1
	frs_recstop
	foreach id $::frs_bps { catch {debug remove_bp $id} }
	set ::frs_bps {}
	hz_nowp
	if {[info exists ::frs_f]} { close $::frs_f; unset ::frs_f }
	hz_msg "$::hz_jobname: $::frs_nt T lines; the job ended"
	set ::pause on
}

# the log's breakpoints and watchpoints in the running machine (after rc2_fr_drive, which removes
# every breakpoint)
proc frs_arm {rom labels out rec} {
	if {[info exists ::frs_f]} { catch {close $::frs_f}; unset ::frs_f }
	set ::frs_rom $rom
	set ::frs_devs "?"
	set ::frs_nt 0
	set ::frs_tx 0
	set ::frs_x 0
	set ::frs_q 0
	set ::frs_e 0
	set ::frs_fin 0
	set ::frs_cnt 0
	set ::frs_np 0
	set ::frs_no 0
	set ::frs_ns 0
	set ::frs_lat 0
	set ::frs_rec 0
	set ::frs_rec_on $rec
	set ::frs_wav "[file rootname $out].wav"
	if {$rec} { file delete -force $::frs_wav }
	foreach k {tn_left tn_snd tn_busy tn_last tn_req tn_mode mus_mode tick} {
		set ::frs_a($k) [rc2_label $labels $k]
	}
	set ::frs_f [open $out w]
	set rb "[file tail $rom] romblocks"
	set bm [rc2_label $labels BANK_MUSIC]
	set ::frs_bps {}
	lappend ::frs_bps [debug set_bp [rc2_label $labels tn_tick] "\[debug read {$rb} 0xA000\] == $bm" frs_tick]
	lappend ::frs_bps [debug set_bp [rc2_label $labels tns_go] "\[debug read {$rb} 0xA000\] == $bm" frs_start]
	set b [rc2_label $labels snd_rfx]
	lappend ::frs_bps [debug set_bp $b "\[peek $b\] == 0x21 && \[rc2_w [expr {$b + 1}]\] == $::frs_a(tn_req)" {frs_put "R [reg a]"}]
	set t [rc2_label $labels fr_tick]
	set f [rc2_label $labels fr_frame]
	lappend ::frs_bps [debug set_bp $t "\[peek $t\] == 0xCD && \[rc2_w [expr {$t + 1}]\] == $f" {frs_put "P [rc2_w 0xD000]"}]
	# (fr_done and snd_stop are fixed code: their own first bytes)
	set d [rc2_label $labels fr_done]
	lappend ::frs_bps [debug set_bp $d "\[peek $d\] == 0xC9 && \$::frs_nt > 0" frs_done]
	set s [rc2_label $labels snd_stop]
	lappend ::frs_bps [debug set_bp $s "\[peek $s\] == [frs_romb $rom $s] && \$::frs_nt > 0" frs_stopcall]
	debug set_watchpoint write_io {0xA0 0xA1} {} frs_psg
	debug set_watchpoint write_io {0x7C 0x7D} {} {if {$::frs_cnt} { incr ::frs_no }}
	debug set_watchpoint write_mem {0x9800 0x98FF} {} {if {$::frs_cnt} { incr ::frs_ns }}
}

proc frs_exts {exts} { foreach e $exts { extb $e } }

# the ROM's byte at a fixed-area address (4000h-7FFFh: banks 0-1, file offset A - 4000h)
proc frs_romb {rom addr} {
	set f [open $rom rb]
	seek $f [expr {$addr - 0x4000}]
	binary scan [read $f 1] cu b
	close $f
	return $b
}

proc frs_drive {tag m dir rom labels exts drive {passes 3000} {rec 0} {tuneoff 0}} {
	file mkdir $dir
	return [list "frs $tag" $m [list frs_drive_setup $tag $dir $rom $labels $exts $drive $passes $rec $tuneoff] {$::frs_fin} 900]
}

# TUNEOFF 1 (a harness poke, to hear the effects alone): at the stage's first pass tn_left = 2, so the
# tune plays its tick 0 and ends at its tick 1 (its voices silent); the effects then play alone
proc frs_drive_setup {tag dir rom labels exts drive passes rec {tuneoff 0}} {
	frs_recstop
	set ::frs_fin 0
	frs_exts $exts
	rc2_fr_drive $rom $labels "$dir/${tag}_trace.txt" $passes 0 $drive
	frs_arm $rom $labels "$dir/${tag}_fr.txt" $rec
	if {$tuneoff} {
		set t [rc2_label $labels fr_tick]
		set f [rc2_label $labels fr_frame]
		set ::frs_toff [rc2_label $labels tn_left]
		lappend ::frs_bps [debug set_bp $t "\[peek $t\] == 0xCD && \[rc2_w [expr {$t + 1}]\] == $f && \[rc2_w 0xD000\] == 0" {poke $::frs_toff 2; poke [expr {$::frs_toff + 1}] 0; frs_put "# tn_left poked to 2 (the tune off)"}]
	}
	lappend ::hz_afters [after realtime 0.5 frs_dpoll]
}

# (rc2_fr_drive pauses at fr_rated, before the result's text screen: on, so that the Z line comes)
proc frs_dpoll {} {
	if {$::frs_fin} return
	if {$::rc2_trace_done && [info exists ::pause] && $::pause} {
		if {!$::frs_e} {
			frs_put "# the drive ended without fr_done"
			frs_end
			return
		}
		set ::pause off
	}
	lappend ::hz_afters [after realtime 0.5 frs_dpoll]
}

proc frs_alone {tag m dir rom labels exts {rec 0}} {
	file mkdir $dir
	return [list "frs $tag" $m [list frs_alone_setup $tag $dir $rom $labels $exts $rec] {$::frs_fin} 900]
}

proc frs_alone_setup {tag dir rom labels exts rec} {
	frs_recstop
	set ::frs_fin 0
	frs_exts $exts
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	frs_arm $rom $labels "$dir/${tag}_fr.txt" $rec
	# (a guard: 200 emulated s, the stage's 2:00 and its intro well inside)
	lappend ::hz_afters [after time 200 {if {!$::frs_fin} { frs_put "# no end in 200 s"; frs_end }}]
}

# frs_suite W ?REC?: the 20 register logs of docs/RANGE.md 4.3 on the builds of "regress.sh builds W"
# (W/S/fr2: EXTJOY=1 PZ_TEST=2; fr2_noscc: + NO_SCC=1; fr2_nosccint: + NO_SCC_INT=1; fr2_psg: +
# NO_SCC=1 NO_FM=1; pz2: PZ_TEST=2; pz2_noscc: + NO_SCC=1), into W/O/snd: fr_mixed's drive (1,869
# passes, 39 effects) on the cartridge's SCC (Expert 60 Hz, C-BIOS_MSX2_EU 50 Hz, HB-F1XDJ), an SCC
# and an SCC+ in slot B, SCC + OPLL (Expert and EU with an FM-PAC, the FS-A1GT), the OPLL alone, the
# PSG alone; and the stage left alone to its real time out (the tune's 5,999 ticks, then silence) on
# the SCC (60 and 50 Hz), SCC + OPLL (FS-A1GT), the OPLL alone and the PSG alone. With REC 1 each job
# also records its sound (W/O/snd/TAG.wav), and three more jobs run: fx_scc and fx_psg (the drive with
# the tune ended at its tick 1: the effects alone) and t_scc (the drive, recorded).
proc frs_suite {w {rec 0}} {
	set s "$w/S"
	set o "$w/O/snd"
	set d "$::hz_root/build/emu/fr_mixed.drive"
	set ex Gradiente_Expert20_64K
	set eu C-BIOS_MSX2_EU
	set xd Sony_HB-F1XDJ_128K_Lite
	set gt Panasonic_FS-A1GT
	set jobs {}
	foreach {tag m b exts} [list scc $ex fr2 {} 50 $eu fr2 {} xd $xd fr2 {} ext $ex fr2_nosccint scc \
			extp $ex fr2_nosccint scc+ sccfm $ex fr2 fmpac 50sccfm $eu fr2 fmpac tr $gt fr2 {} \
			fm $ex fr2_noscc fmpac 50fm $eu fr2_noscc fmpac trfm $gt fr2_noscc {} \
			psg $ex fr2_noscc {} 50psg $eu fr2_noscc {} xdpsg $xd fr2_psg {} trpsg $gt fr2_psg {}] {
		lappend jobs [frs_drive d_$tag $m $o "$s/$b/rc2.rom" "$s/$b/rc2.labels" $exts $d 3000 $rec]
	}
	foreach {tag m b exts} [list scc $ex pz2 {} 50 $eu pz2 {} sccfm $gt pz2 {} fm $ex pz2_noscc fmpac psg $ex pz2_noscc {}] {
		lappend jobs [frs_alone a_$tag $m $o "$s/$b/rc2.rom" "$s/$b/rc2.labels" $exts $rec]
	}
	if {$rec} {
		lappend jobs [frs_drive fx_scc $ex $o "$s/fr2/rc2.rom" "$s/fr2/rc2.labels" {} $d 3000 1 1]
		lappend jobs [frs_drive fx_psg $ex $o "$s/fr2_noscc/rc2.rom" "$s/fr2_noscc/rc2.labels" {} $d 3000 1 1]
	}
	return $jobs
}

set ::frs_loaded "frsound.tcl loaded from $::frs_dir"
