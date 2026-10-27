# run8f.tcl: step 8's chain on a set of test candidates plus the solved ending from the keyboard
# (the final candidates of 2026-10-27; docs/HARNESS.md 5.17 h). Source load.tcl (it sources this
# file after run8.tcl, c8.tcl and np.tcl); then c8f_chain; poll "list $::hz_state $::hz_msgs"
# (never vwait).
#
#   c8f_chain CDIR BASE FDIR FTAG ?MOVES?
#       run8.tcl c8_chain's seven jobs on CDIR's four candidates (BASE.ROM, BASE-2M.ROM,
#       BASE-bonus.ROM, BASE-bonus-2M.ROM with their label files; the title records into FDIR as
#       FTAG and FTAG_2m; the rest into CDIR/run/), then solved_m2: BASE-bonus.ROM on
#       Gradiente_Expert20_64K solved by c8f_solved_job: 8 jobs.
#       The night of 2026-10-27 ran: c8f_chain CAND ROBOCOP2_v0.1.3-test2 FRESH final_test2
#   c8f_solved_job NAME MACHINE DIR ROM LABELS PASSES
#       a PZ_TEST=1 ROM (no EXTJOY) from the power-on: hz.tcl hz_bonus_setup's records
#       (DIR/NAME_bonus.txt, _intro.sc5, _result.sc5: bonuscheck.py --result ok), hz7_arm's
#       snapshots at PASSES (DIR/st_NAME/), c8_arm's intro and result snapshots without moves of
#       its own (DIR/NAME_intro.bin, DIR/NAME_result.bin: shots.py), and the moves of
#       build/emu/pz_solve1.drive from the keyboard (np.tcl np_keys_arm)
#
# Rules kept: no exit, vwait, max or min; files opened once per write and closed on every path.

proc c8f_solved_job {name m dir rom labels passes} {
	return [list $name $m [list c8f_solved_setup $name $dir $rom $labels $passes] {$::hz_done} 900]
}

proc c8f_solved_setup {name dir rom labels passes} {
	file mkdir $dir
	hz_bonus_setup $dir $name $rom $labels {}
	hz7_arm "$dir/st_$name" $labels $passes
	c8_arm $dir $name $labels {}
	np_keys_arm $labels "$::hz_root/build/emu/pz_solve1.drive"
}

proc c8f_chain {cdir base fdir ftag {moves {100 d 110 r 120 d 130 l 140 d}}} {
	set jobs [c8_jobs $cdir $base $fdir $ftag $moves]
	set b1 "$cdir/$base-bonus"
	lappend jobs [c8f_solved_job solved_m2 Gradiente_Expert20_64K "$cdir/run" "$b1.ROM" "$b1.labels" {100 300 450 600 650 700}]
	return [hz_chain $jobs]
}
