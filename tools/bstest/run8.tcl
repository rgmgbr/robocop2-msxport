# run8.tcl: step 8's chain on a set of test candidates (source after hz.tcl, hz7.tcl, hz6.tcl and
# c8.tcl, or source load.tcl; then c8_chain; poll "list $::hz_state $::hz_msgs"; docs/HARNESS.md).
#
#   c8_chain CDIR BASE FDIR FTAG ?MOVES?
#       CDIR holds the four candidates BASE.ROM (the product), BASE-2M.ROM (its ROM_2M=1 twin),
#       BASE-bonus.ROM (PZ_TEST=1) and BASE-bonus-2M.ROM, each with its label file (BASE.labels,
#       ...). FDIR is the title references' folder (hz_fresh records, compared by hz.sh fresh): the
#       products' records go there as FTAG and FTAG_2m. The other output goes to CDIR/run/:
#       - bonus_m2 (Gradiente_Expert20_64K), bonus_f1 (Sony_HB-F1XDJ_128K_Lite) on BASE-bonus.ROM
#         and bonus2m_m2 on BASE-bonus-2M.ROM: c8_job with MOVES (default solve1's first five:
#         {100 d 110 r 120 d 130 l 140 d}), snapshots at passes 60, 90, 150-400 every 5, 1000,
#         2000, 3000 and 1000 pictures recorded from pass 90;
#       - prod_m2 and prod_f1: the product's whole flow (hz6_prod_setup).
#       The night of 2026-10-27 ran: c8_chain CAND ROBOCOP2_v0.1.3-test2 FRESH cand_test2

proc c8_chain {cdir base fdir ftag {moves {100 d 110 r 120 d 130 l 140 d}}} {
	set C $cdir
	set P {60 90}
	for {set i 150} {$i <= 400} {incr i 5} { lappend P $i }
	lappend P 1000 2000 3000
	# (solve1's first five moves: (0,0) -> (0,1) -> (1,1) -> (1,2) red -> (0,2) -> (0,3) red; two
	#  neighbours stay free, so the board times out)
	set mv $moves
	set b1 "$C/$base-bonus"
	set b2 "$C/$base-bonus-2M"
	set p1 "$C/$base"
	set p2 "$C/$base-2M"
	foreach r [list $b1 $b2 $p1 $p2] {
		foreach x {.ROM .labels} {
			if {![file exists "$r$x"]} { error "c8_chain: no $r$x" }
		}
	}
	file mkdir "$C/run"
	file mkdir $fdir
	set jobs {}
	lappend jobs [list "fresh $ftag" Gradiente_Expert20_64K [list hz_fresh_setup $fdir $ftag "$p1.ROM" "$p1.labels" 300] {$::hz_done} 900]
	lappend jobs [list "fresh ${ftag}_2m" Gradiente_Expert20_64K [list hz_fresh_setup $fdir ${ftag}_2m "$p2.ROM" "$p2.labels" 300] {$::hz_done} 900]
	lappend jobs [c8_job bonus_m2 Gradiente_Expert20_64K "$C/run" "$b1.ROM" "$b1.labels" $mv $P 1000 90]
	lappend jobs [c8_job bonus_f1 Sony_HB-F1XDJ_128K_Lite "$C/run" "$b1.ROM" "$b1.labels" $mv $P 1000 90]
	lappend jobs [c8_job bonus2m_m2 Gradiente_Expert20_64K "$C/run" "$b2.ROM" "$b2.labels" $mv $P 1000 90]
	lappend jobs [list prod_m2 Gradiente_Expert20_64K [list hz6_prod_setup "$C/run" prod_m2 "$p1.ROM" "$p1.labels"] {$::hz_done} 900]
	lappend jobs [list prod_f1 Sony_HB-F1XDJ_128K_Lite [list hz6_prod_setup "$C/run" prod_f1 "$p1.ROM" "$p1.labels"] {$::hz_done} 900]
	return [hz_chain $jobs]
}
