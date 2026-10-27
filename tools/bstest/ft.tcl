# ft.tcl: the final checks' VRAM speed jobs (2026-10-27; docs/HARNESS.md 5.8 and 5.17 g,
# docs/BRAINSTORM.md 4.6 g). Source load.tcl (it sources this file after hz.tcl, hz7.tcl and
# np.tcl) in the MCP's openMSX; start one hz_chain; poll "list $::hz_state $::hz_msgs" with short
# msx_local_cmd calls. Never vwait.
#
# Each job counts the VRAM accesses the VDP loses because the CPU made them too fast
# (too_fast_vram_access real; tools/openmsx_rc2.tcl rc2_count_too_fast, which counts since
# b59a338) with the Z80 at FREQ Hz. hz.tcl hz_cfg locks z80_freq at 3.58 MHz on every new machine,
# and openMSX ignores z80_freq while it is locked: each setup sets z80_freq_locked off first
# (ft_clock); hz_cfg locks it again for the next job. Each hit is placed by its PC: the BIOS's code
# (below 4000h) or the cartridge's, the first 8 of each with their emulated times.
#
#   ft_job NAME MACHINE ROM LABELS OUT FREQ ?DRIVE?
#       build/emu/pz_DRIVE.drive (solve1 by default) of an EXTJOY=1 PZ_TEST=1 ROM from the
#       power-on: the intro (fe_text), the stage's entry uploads, its passes, the exit's restore,
#       to pz_done. OUT/flow/NAME.txt: the count, the first PCs, the result; OUT/tr/NAME.txt: the
#       trace (tools/puzlcmp.py)
#   ft_flow_job NAME MACHINE ROM LABELS OUT FREQ
#       a PZ_TEST=1 build without EXTJOY (the candidates' options) from the power-on: the intro
#       with its TEST line, the stage solved from the keyboard (np.tcl np_keys_arm,
#       build/emu/pz_solve1.drive), WELL DONE with its TEST line, up to the title's start
#       (front_mode set to 1: a write watchpoint stops the count there, so the title's own code is
#       not counted): OUT/flow/NAME.txt
#   ft_boot_job NAME MACHINE ROM LABELS OUT FREQ
#       where the BIOS's hits come from: the counter from the power-on, each BIOS hit with its
#       emulated time, SP and the four words on the stack (a return address in 4000h-BFFFh means
#       the cartridge called that BIOS routine), and the time the cartridge's init (label init)
#       starts; 6 emulated seconds: OUT/flow/NAME.txt
#   ft_l1_job NAME MACHINE ROM LABELS OUT FREQ N
#       level 1 driven by build/emu/drive_cov1.txt for N ticks (rc2_drive_rom; an EXTJOY=1 build,
#       the trace build for a trace tools/tracecmp.py compares): OUT/flow/NAME.txt, the trace
#       OUT/tr/NAME.txt
#
# Rules kept: no exit, vwait, max or min; files opened once and closed on every path.

proc ft_job {name m rom labels out freq {drive solve1}} {
	file mkdir "$out/tr"
	file mkdir "$out/flow"
	return [list $name $m [list ft_setup $name $rom $labels $out $freq $drive] {[ft_done]} 300]
}

# the Z80's clock for this job (after hz_cfg, which locked it at 3.58 MHz)
proc ft_clock {freq} {
	set ::z80_freq_locked off
	set ::z80_freq $freq
}

proc ft_setup {name rom labels out freq drive} {
	ft_clock $freq
	set ::too_fast_vram_access real
	rc2_count_too_fast
	ft_classify
	rc2_pz_drive $rom $labels "$out/tr/$name.txt" 3000 0 "$::hz_root/build/emu/pz_$drive.drive"
	set ::ft_file "$out/flow/$name.txt"
}

# rc2_count_too_fast's count, and each hit's place: the BIOS's code (PC < 4000h) or the cartridge's,
# the first 8 of each with their emulated times
proc ft_classify {} {
	set ::ft_bios 0
	set ::ft_cart 0
	set ::ft_bl {}
	set ::ft_cl {}
	set {::VDP.too_fast_vram_access_callback} ft_cb
}

proc ft_cb {args} {
	rc2_too_fast_cb
	set pc [reg pc]
	set e [format "%04x@%.3f" $pc [machine_info time]]
	if {$pc < 0x4000} {
		incr ::ft_bios
		if {[llength $::ft_bl] < 8} { lappend ::ft_bl $e }
	} else {
		incr ::ft_cart
		if {[llength $::ft_cl] < 8} { lappend ::ft_cl $e }
	}
}

# ::ft_file written once with LINE
proc ft_write {line} {
	set f [open $::ft_file w]
	catch {puts $f $line}
	close $f
}

# (a done condition: evaluated every second until it holds, so the file is written once)
proc ft_done {} {
	if {!$::rc2_trace_done} { return 0 }
	ft_write "[machine_info config_name]: too fast VRAM accesses $::rc2_too_fast: cartridge $::ft_cart {$::ft_cl}, BIOS $::ft_bios {$::ft_bl} (too_fast_vram_access [set ::too_fast_vram_access], z80_freq [set ::z80_freq], locked [set ::z80_freq_locked]); result $::rc2_pz_result, passes [rc2_w 0xD000], emulated [format %.3f [machine_info time]] s"
	set {::VDP.too_fast_vram_access_callback} {}
	return 1
}

# ----- the whole bonus flow from the power-on to the title's start

proc ft_flow_job {name m rom labels out freq} {
	file mkdir "$out/flow"
	return [list $name $m [list ft_flow_setup $name $rom $labels $out $freq] {[ft_flow_done]} 300]
}

proc ft_flow_setup {name rom labels out freq} {
	ft_clock $freq
	set ::too_fast_vram_access real
	rc2_count_too_fast
	ft_classify
	set ::ft_file "$out/flow/$name.txt"
	set ::ft_stopped 0
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	np_keys_arm $labels "$::hz_root/build/emu/pz_solve1.drive"
	set ::ft_wp [debug set_watchpoint write_mem 0xEC44 {} ft_flow_wp]
}

proc ft_flow_wp {} {
	if {$::wp_last_value == 1 && !$::ft_stopped} {
		set ::ft_stopped 1
		set {::VDP.too_fast_vram_access_callback} {}
		set ::ft_t1 [machine_info time]
		set ::pause on
	}
}

proc ft_flow_done {} {
	if {!$::ft_stopped} { return 0 }
	ft_write "[machine_info config_name]: power-on to the title's start after the stage (front_mode 1 at [format %.3f $::ft_t1] s): too fast VRAM accesses $::rc2_too_fast: cartridge $::ft_cart {$::ft_cl}, BIOS $::ft_bios {$::ft_bl} (z80_freq [set ::z80_freq], locked [set ::z80_freq_locked]); AG 805Eh [rc2_w 0xDC5E], passes [rc2_w 0xD000]"
	catch {debug remove_watchpoint $::ft_wp}
	return 1
}

# ----- the BIOS's own hits at the power-on

proc ft_boot_job {name m rom labels out freq} {
	file mkdir "$out/flow"
	return [list $name $m [list ft_boot_setup $name $rom $labels $out $freq] {[ft_boot_done]} 120]
}

proc ft_boot_setup {name rom labels out freq} {
	ft_clock $freq
	set ::too_fast_vram_access real
	rc2_count_too_fast
	set ::fb_l {}
	set ::fb_init -1
	set {::VDP.too_fast_vram_access_callback} ft_boot_cb
	set ::ft_file "$out/flow/$name.txt"
	carta eject
	carta insert $rom -romtype KonamiSCC
	reset
	# (init's first byte is DI, F3h: the breakpoint fires only where the cartridge is mapped)
	set ::fb_ia [rc2_label $labels init]
	debug set_bp $::fb_ia "\[peek $::fb_ia\] == 0xF3" ft_boot_init
	set ::fb_end [expr {[machine_info time] + 6}]
}

proc ft_boot_init {} {
	if {$::fb_init < 0} { set ::fb_init [machine_info time] }
}

proc ft_boot_cb {args} {
	rc2_too_fast_cb
	set pc [reg pc]
	if {$pc < 0x4000 && [llength $::fb_l] < 8} {
		set sp [reg sp]
		set w {}
		for {set i 0} {$i < 8} {incr i 2} { lappend w [format %04x [rc2_w [expr {($sp + $i) & 0xFFFF}]]] }
		lappend ::fb_l [format "pc %04x at %.4f s, sp %04x: %s" $pc [machine_info time] $sp $w]
	}
}

proc ft_boot_done {} {
	if {[machine_info time] < $::fb_end} { return 0 }
	ft_write "[machine_info config_name]: the first 6 s at z80_freq [set ::z80_freq]: too fast VRAM accesses $::rc2_too_fast; the cartridge's init at [format %.4f $::fb_init] s; BIOS hits: $::fb_l"
	set {::VDP.too_fast_vram_access_callback} {}
	return 1
}

# ----- level 1 (its sprite engine's OUTIs), for the record

proc ft_l1_job {name m rom labels out freq n} {
	file mkdir "$out/tr"
	file mkdir "$out/flow"
	return [list $name $m [list ft_l1_setup $name $rom $labels $out $freq $n] {[ft_l1_done]} 300]
}

proc ft_l1_setup {name rom labels out freq n} {
	ft_clock $freq
	set ::too_fast_vram_access real
	rc2_count_too_fast
	ft_classify
	rc2_drive_rom $rom $labels "$out/tr/$name.txt" $n 0 "$::hz_root/build/emu/drive_cov1.txt"
	set ::ft_file "$out/flow/$name.txt"
}

proc ft_l1_done {} {
	if {!$::rc2_trace_done} { return 0 }
	ft_write "[machine_info config_name]: level 1, [rc2_w 0xCEE0] ticks of drive_cov1: too fast VRAM accesses $::rc2_too_fast: cartridge $::ft_cart {$::ft_cl}, BIOS $::ft_bios {$::ft_bl} (z80_freq [set ::z80_freq], locked [set ::z80_freq_locked]), emulated [format %.3f [machine_info time]] s"
	set {::VDP.too_fast_vram_access_callback} {}
	return 1
}
