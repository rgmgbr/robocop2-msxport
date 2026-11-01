# load.tcl (tools/bstest/perf2): performance campaign 2's kit (docs/HARNESS.md section 12) in the MSX-AI
# MCP's openMSX (a private session: tools/bstest/mcpd.py and mx.sh):
#
#   source {<repo>/tools/bstest/perf2/load.tcl}
#
# Sources the harness first (tools/bstest/load.tcl, l2base.tcl, l3field.tcl), then the kit's Tcl: m3.tcl
# (speed records), cnt.tcl (call counters, map dumps), cen.tcl (the sprite budget's census), fl.tcl (the
# flash probe), pgprobe.tcl (flash-1's page path), lp.tcl (the frame pipeline), m2.tcl (level 2's
# instrumentation, the enemies' flash bytes) and gates.tcl (each gate's standard jobs). Sourcing it again
# redefines everything; no job is started.
#
# The harness and the drives (build/emu) come from ::pf_repo, by default the repository this file is in.
# A git worktree has no build/: set ::pf_repo to the main checkout before sourcing this file (or link
# build/ into the worktree), e.g. "set ::pf_repo {<main checkout>}; source {<worktree>/tools/bstest/perf2/load.tcl}".

set ::pf_dir [file dirname [file normalize [info script]]]
if {![info exists ::pf_repo]} { set ::pf_repo [file dirname [file dirname [file dirname $::pf_dir]]] }
foreach ::pf_file {load.tcl l2base.tcl l3field.tcl} {
	uplevel #0 [list source [file join $::pf_repo tools bstest $::pf_file]]
}
foreach ::pf_file {m3.tcl cnt.tcl cen.tcl fl.tcl pgprobe.tcl lp.tcl m2.tcl gates.tcl} {
	uplevel #0 [list source [file join $::pf_dir $::pf_file]]
}
unset ::pf_file
set ::pf_emu [file join $::hz_root build emu]
set ::pf_loaded "perf2 kit loaded from $::pf_dir; harness and drives from $::hz_root"
