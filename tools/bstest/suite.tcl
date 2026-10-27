# suite.tcl: the acceptance suite's emulator jobs for a set of ROMs (the review fixes, 2026-10-27;
# docs/HARNESS.md). Source after hz.tcl, hz7.tcl, hz6.tcl and fixchk.tcl (or source load.tcl); then
#   hz_chain [suite_drives R O]   the nine drives on C-BIOS_MSX2 and the FS-A1GT, solve1 on the FS-A1FX
#                                 and C-BIOS_MSX2_EU (traces, step 7's stills and records), step 7's
#                                 guard (solve1 on the three 60 Hz machines) and the VRAM speed check:
#                                 25 jobs
#   hz_chain [suite_flows R O FDIR FTAG]
#                                 the level-1 regression, the title on a fresh machine (hz_fresh into
#                                 FDIR with the tag FTAG: the reference's folder), the product and
#                                 PZ_TEST flows, the restore and the new game, the HUD's blank at
#                                 the switch to the Z80 (measured): 13 jobs
# R: the folder with prod/, pzt/, pz1/, pz2/, trace/, ext/ (hz.sh builds R); O: the output folder
# (tr/, st/, flow/, trace/ under it). Poll "list $::hz_state $::hz_msgs".

proc suite_drives {r o} {
	foreach d {tr st flow} { file mkdir "$o/$d" }
	set p1 "$r/pz1/rc2_pz1.rom"; set l1 "$r/pz1/rc2_pz1.labels"
	set p2 "$r/pz2/rc2_pz2.rom"; set l2 "$r/pz2/rc2_pz2.labels"
	set s1 {5 40 100 131 160 165 200 300 450 600 650 700}
	set jobs {}
	foreach {tag m} {m2 C-BIOS_MSX2 tr Panasonic_FS-A1GT} {
		lappend jobs [hz7_job solve1_$tag $m $p1 $l1 solve1 $o $s1 3000 0]
		lappend jobs [hz7_job fail_$tag $m $p1 $l1 fail $o {60 100 150} 3000 0]
		lappend jobs [hz7_job timeout_$tag $m $p1 $l1 timeout $o {100 120 170} 3000 0]
		lappend jobs [hz7_job quirk2_$tag $m $p1 $l1 quirk2 $o {} 3000 100]
		lappend jobs [hz7_job fuzz1_$tag $m $p1 $l1 fuzz1 $o]
		lappend jobs [hz7_job quirk1_$tag $m $p1 $l1 quirk1 $o]
		lappend jobs [hz7_job opp_$tag $m $p1 $l1 opp $o]
		lappend jobs [hz7_job solve2_$tag $m $p2 $l2 solve2 $o {100 400 700} 3000 0]
		lappend jobs [hz7_job fuzz2_$tag $m $p2 $l2 fuzz2 $o]
	}
	lappend jobs [hz7_job solve1_fx Panasonic_FS-A1FX $p1 $l1 solve1 $o $s1 3000 0]
	lappend jobs [hz7_job solve1_eu C-BIOS_MSX2_EU $p1 $l1 solve1 $o {5 100 300 600 700} 3000 0]
	foreach {tag m} {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT} {
		lappend jobs [hzg_job guard_$tag $m $p1 $l1 $o]
	}
	foreach {tag m} {m2 C-BIOS_MSX2 tr Panasonic_FS-A1GT} {
		lappend jobs [hzf_job fast_$tag $m $p1 $l1 $o]
	}
	return $jobs
}

proc suite_flows {r o fdir ftag} {
	foreach d {flow trace} { file mkdir "$o/$d" }
	set e "$::hz_root/build/emu"
	set t "$r/trace/rc2_ext5.rom"; set tl "$r/trace/rc2_ext5.labels"
	set jobs [list \
		[list cov1 C-BIOS_MSX2 [list rc2_drive_rom $t $tl "$o/trace/cov1.txt" 4401 0 "$e/drive_cov1.txt"] {$::rc2_trace_done} 900] \
		[list cov0 Panasonic_FS-A1FX [list rc2_drive_rom $t $tl "$o/trace/cov0.txt" 1400 0 "$e/drive_cov0.txt"] {$::rc2_trace_done} 600] \
		[list cov0_tr Panasonic_FS-A1GT [list rc2_drive_rom $t $tl "$o/trace/cov0_tr.txt" 1400 0 "$e/drive_cov0.txt"] {$::rc2_trace_done} 600]]
	lappend jobs [list "fresh $ftag" Gradiente_Expert20_64K [list hz_fresh_setup $fdir $ftag "$r/prod/rc2.rom" "$r/prod/rc2.labels" 300] {$::hz_done} 900]
	lappend jobs [list prod_m2 Gradiente_Expert20_64K [list hz6_prod_setup "$o/flow" prod_m2 "$r/prod/rc2.rom" "$r/prod/rc2.labels"] {$::hz_done} 900]
	lappend jobs [list prod_tr Panasonic_FS-A1GT [list hz6_prod_setup "$o/flow" prod_tr "$r/prod/rc2.rom" "$r/prod/rc2.labels"] {$::hz_done} 900]
	lappend jobs [list pzt_m2 Gradiente_Expert20_64K [list hz_bonus_setup "$o/flow" pzt_m2 "$r/pzt/rc2.rom" "$r/pzt/rc2.labels" ""] {$::hz_done} 900]
	lappend jobs [list pzt_tr Panasonic_FS-A1GT [list hz_bonus_setup "$o/flow" pzt_tr "$r/pzt/rc2.rom" "$r/pzt/rc2.labels" ""] {$::hz_done} 900]
	foreach {tag m} {m2 C-BIOS_MSX2 tr Panasonic_FS-A1GT} {
		lappend jobs [list after_$tag $m [list hz7_after_setup "$o/flow" after_$tag "$r/pz1/rc2_pz1.rom" "$r/pz1/rc2_pz1.labels" fail] {$::hz_done} 600]
		lappend jobs [list fresh_$tag $m [list hz7_fresh_setup "$o/flow" fresh_$tag "$r/ext/rc2_ext.rom" "$r/ext/rc2_ext.labels"] {$::hz_done} 600]
	}
	lappend jobs [list blank_tr Panasonic_FS-A1GT [list hzb_setup "$o/flow" blank_tr "$r/ext/rc2_ext.rom" "$r/ext/rc2_ext.labels"] {$::hz_done} 600]
	return $jobs
}
