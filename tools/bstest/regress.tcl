# regress.tcl: the whole regression of the shooting range's milestone (docs/HARNESS.md 5.19), as
# hz_chain jobs in the MSX-AI MCP's openMSX. load.tcl sources it. On the builds of
# "sh tools/bstest/regress.sh builds W" (W/R: hz.sh builds; W/X: the range's test builds; W/V:
# rgview.sh builds; W/S: the sound's builds; W/drives: the range's poke drives):
#
#   rgr_chain W ?FAMILY? ?MARK?   one chain of FAMILY's jobs (default all), records into W/O, W/fresh;
#                                 with MARK (a file) the chain's messages are written there at its end
#   rgr_jobs W ?FAMILY?           the job list
#   rgr_base_chain B ?MARK?       the base's records (regress.sh base B made B/R): B/O, B/fresh
#
# Families (rgr_chain W all runs them in this order):
#   flows   Brainstorm's flows, now through the range (13: suite_flows: level 1's coverage traces, the
#           title from power-on as "new", the product's and PZ_TEST=1 flows with the range's screens,
#           the restore with the range timed out, the turbo R's blank); the title after the flows,
#           exact (np_title_setup EXACT 1: tx_ex, tx_f1, tx_tr); the turbo R's writes to 4000h-7FFFh
#           (wp_tr); the 2 MiB product through both bonus stages (p2m_ex); the product from the
#           keyboard (rgk_job: kb_ex, kb_tr). 21 jobs
#   final   the final checks' flows through the range (np.tcl): solved_m2, solved_tr (pz1),
#           solved_cand_ex (the candidate build from the keyboard), fire_ex, two_m2, two_title_ex,
#           the 5.37 MHz flow (ft_flow_job: ftflow_fx). 7 jobs
#   drives  Brainstorm's 20 traces, stills, records, guard and VRAM speed (suite_drives). 25 jobs
#   range   the range's screens through PZ_TEST=2 and through the product's flow (EXTJOY=1: level 1,
#           Brainstorm by pz_fail) for 5 poked results (the 4 ratings) and the time out, on
#           C-BIOS_MSX2, the FS-A1FX and the FS-A1GT (36); TAG=4 (2); level 1 traced after the range
#           and the new game (3); the real timer's time out at 60 and 50 Hz and on the turbo R (3);
#           the range traced after a played level 1 and Brainstorm (tarm_m2, tarm_tr: fr_mixed); the
#           wanted state at every pass (want_*: 8 drives). 54 jobs
#   display rgview.tcl rgv_suite on W/V (the stills, records, camera, probe, guard, VRAM speed, pass
#           rate, restore, the 15 drives' traces on C-BIOS_MSX2 and the FS-A1GT). 81 jobs
#   sound   frsound.tcl frs_suite on W/S: the 20 register logs (15 drives, 5 stages left alone). 20 jobs
# Then "sh tools/bstest/regress.sh check W B" (B: the base's folder).
# Rules kept: no exit, vwait, max or min (the sourced files' rules).

proc rgr_jobs {w {what all}} {
	set r "$w/R"
	set o "$w/O"
	set x "$w/X"
	set e "$::hz_root/build/emu"
	file mkdir "$o/np"
	file mkdir "$o/rg"
	file mkdir "$w/fresh"
	set jobs {}
	if {$what eq "all" || $what eq "flows"} {
		set jobs [concat $jobs [suite_flows $r $o "$w/fresh" new]]
		foreach {t m} {ex Gradiente_Expert20_64K f1 Sony_HB-F1XDJ_128K_Lite tr Panasonic_FS-A1GT} {
			lappend jobs [np_job tx_$t $m np_title_setup "$o/np" "$r/prod/rc2.rom" "$r/prod/rc2.labels" 1]
		}
		lappend jobs [np_wp_job wp_tr Panasonic_FS-A1GT "$o/np" "$r/prod/rc2.rom" "$r/prod/rc2.labels"]
		lappend jobs [np_job p2m_ex Gradiente_Expert20_64K hz6_prod_setup "$o/np" "$x/p2m/rc2.rom" "$x/p2m/rc2.labels"]
		foreach {t m} {ex Gradiente_Expert20_64K tr Panasonic_FS-A1GT} {
			lappend jobs [rgk_job kb_$t $m "$o/kb" "$r/prod/rc2.rom" "$r/prod/rc2.labels"]
		}
	}
	if {$what eq "all" || $what eq "final"} {
		set p1 "$r/pz1/rc2_pz1.rom"; set l1 "$r/pz1/rc2_pz1.labels"
		set c "$x/cand/rc2.rom"; set cl "$x/cand/rc2.labels"
		lappend jobs [np_job solved_m2 C-BIOS_MSX2 np_solved_setup "$o/np" $p1 $l1]
		lappend jobs [np_job solved_tr Panasonic_FS-A1GT np_solved_setup "$o/np" $p1 $l1]
		lappend jobs [np_job solved_cand_ex Gradiente_Expert20_64K np_solved_setup "$o/np" $c $cl 1]
		lappend jobs [np_job fire_ex Gradiente_Expert20_64K np_fire_setup "$o/np" $c $cl]
		lappend jobs [np_job two_m2 C-BIOS_MSX2 np_two_setup "$o/np" $p1 $l1]
		lappend jobs [list two_title_ex Gradiente_Expert20_64K [list np_two_title_setup "$o/np" two_title_ex $c $cl] {$::hz_done} 1500]
		lappend jobs [ft_flow_job ftflow_fx Panasonic_FS-A1FX $c $cl $o 5369318]
	}
	if {$what eq "all" || $what eq "drives"} {
		set jobs [concat $jobs [suite_drives $r $o]]
	}
	if {($what eq "all" || $what eq "range") && [file exists "$x/fr2/rc2.rom"]} {
		set d "$w/drives"
		foreach {mt m} {m2 C-BIOS_MSX2 fx Panasonic_FS-A1FX tr Panasonic_FS-A1GT} {
			foreach c {c16_d0_m1 c15_d0_m1 c13_d2_m1 c25_d0_m0 c0_d0_m2 time} {
				lappend jobs [rgx_job pz_${c}_$mt $m "$o/rg" "$x/fr2/rc2.rom" "$x/fr2/rc2.labels" "$d/rg_$c.drive"]
				lappend jobs [rgx_arm_job ar_${c}_$mt $m "$o/rg" "$x/ext/rc2.rom" "$x/ext/rc2.labels" "$d/rg_$c.drive"]
			}
		}
		foreach c {c16_d0_m1 time} {
			lappend jobs [rgx_job tag_${c}_m2 C-BIOS_MSX2 "$o/rg" "$x/fr2tag/rc2.rom" "$x/fr2tag/rc2.labels" "$d/rg_$c.drive"]
		}
		lappend jobs [rgx_job l1cov1_m2 C-BIOS_MSX2 "$o/rg" "$x/fr2t/rc2.rom" "$x/fr2t/rc2.labels" "$d/rg_c0_d0_m2.drive" [list "$e/drive_cov1.txt" 4401]]
		lappend jobs [rgx_job l1cov0_fx Panasonic_FS-A1FX "$o/rg" "$x/fr2t/rc2.rom" "$x/fr2t/rc2.labels" "$d/rg_time.drive" [list "$e/drive_cov0.txt" 1400]]
		lappend jobs [rgx_job l1cov0_tr Panasonic_FS-A1GT "$o/rg" "$x/fr2t/rc2.rom" "$x/fr2t/rc2.labels" "$d/rg_c16_d0_m1.drive" [list "$e/drive_cov0.txt" 1400]]
		foreach {mt m} {ex Gradiente_Expert20_64K eu C-BIOS_MSX2_EU tr Panasonic_FS-A1GT} {
			lappend jobs [rgx_job real_time_$mt $m "$o/rg" "$x/pzt2/rc2.rom" "$x/pzt2/rc2.labels" "$d/rg_none.drive"]
		}
		foreach {mt m} {m2 C-BIOS_MSX2 tr Panasonic_FS-A1GT} {
			lappend jobs [rgx_tarm_job tarm_$mt $m "$o/lt" "$x/ext/rc2.rom" "$x/ext/rc2.labels" mixed]
		}
		foreach dv {armed mixed dummy edge fuzz quirk4 hold} {
			lappend jobs [rgx_want_job want_$dv C-BIOS_MSX2 "$o/lt" "$x/fr2/rc2.rom" "$x/fr2/rc2.labels" $dv]
		}
		lappend jobs [rgx_want_job want_armed2 C-BIOS_MSX2 "$o/lt" "$w/V/fr2v2/rc2.rom" "$w/V/fr2v2/rc2.labels" armed2]
	}
	if {($what eq "all" || $what eq "display") && [file exists "$w/V/fr2/rc2.rom"]} {
		set jobs [concat $jobs [rgv_suite "$w/V"]]
	}
	if {($what eq "all" || $what eq "sound") && [file exists "$w/S/fr2/rc2.rom"]} {
		set jobs [concat $jobs [frs_suite $w]]
	}
	return $jobs
}

proc rgr_chain {w {what all} {mark ""}} {
	set jobs [rgr_jobs $w $what]
	return "[hz_chain $jobs $mark] (regress.tcl: $what)"
}

# The base's records (docs/HARNESS.md 5.19), on the builds "regress.sh base B" made in B/R: the
# flows (the title from power-on as "base" into B/fresh), the title after Brainstorm, exact, on the
# three machines (B/O/np/tx_*), Brainstorm's 25 drive jobs (B/O). Then "regress.sh basecheck B".
proc rgr_base_chain {b {mark ""}} {
	set r "$b/R"
	set o "$b/O"
	file mkdir "$o/np"
	file mkdir "$b/fresh"
	set jobs [suite_flows $r $o "$b/fresh" base]
	foreach {t m} {ex Gradiente_Expert20_64K f1 Sony_HB-F1XDJ_128K_Lite tr Panasonic_FS-A1GT} {
		lappend jobs [np_job tx_$t $m np_title_setup "$o/np" "$r/prod/rc2.rom" "$r/prod/rc2.labels" 1]
	}
	set jobs [concat $jobs [suite_drives $r $o]]
	return "[hz_chain $jobs $mark] (regress.tcl: the base)"
}

set ::rgr_loaded "regress.tcl loaded"
