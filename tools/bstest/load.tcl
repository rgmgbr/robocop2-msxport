# load.tcl: sources every Tcl file of the Brainstorm harness in its order, for the MSX-AI MCP's
# openMSX (docs/HARNESS.md):
#
#   msx_local_cmd: source {<repo>/tools/bstest/load.tcl}
#
# hz.tcl comes first (it sources tools/openmsx_rc2.tcl and sets ::hz_root, the repository); the
# others only define procs: the acceptance suite's, then the final checks' (np.tcl, ft.tcl,
# run8f.tcl). Sourcing it again redefines them (no job is started).

set ::hz_dir [file dirname [file normalize [info script]]]
foreach ::hz_file {hz.tcl hz6.tcl hz7.tcl fixchk.tcl suite.tcl c8.tcl run8.tcl np.tcl ft.tcl run8f.tcl} {
	uplevel #0 [list source [file join $::hz_dir $::hz_file]]
}
unset ::hz_file
set ::hz_loaded "bstest loaded from $::hz_dir; repository $::hz_root"
