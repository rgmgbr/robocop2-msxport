#!/bin/sh
# hz.sh: the shell side of the Brainstorm harness's emulator checks (the emulator side: hz.tcl and
# the files load.tcl sources, run in the MSX-AI MCP's openMSX; docs/HARNESS.md). Subcommands:
#
#   hz.sh trace DIR          builds DIR/rc2_ext5.rom (EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1: the
#                            reference traces' options) from the repository as it is, with
#                            build.sh's checks, and prints the msx_local_cmd line that runs the
#                            regression on it
#   hz.sh compare DIR [LABELS]
#                            tools/tracecmp.py --ram on DIR/cov1.txt and DIR/cov0.txt (and
#                            DIR/cov0_tr.txt when present) with LABELS, the traced ROM's label file
#                            (default DIR/rc2_ext5.labels): exit 0 only when every trace has its
#                            full length and 0 frames differ
#   hz.sh product DIR [OPTS] builds the product ROM DIR/rc2.rom (OPTS: extra NAME=VALUE) and
#                            prints the msx_local_cmd line of hz_fresh for it
#   hz.sh fresh DIR A B      compares two hz_fresh records (tags A and B in DIR): the title's
#                            VRAM, registers and palette, the music log and the PSG hash, the
#                            game's VRAM and mirror at the same game tick
#   hz.sh builds R           the acceptance suite's six builds (suite.tcl): R/prod/rc2.rom (the
#                            product), R/pzt/rc2.rom (PZ_TEST=1), R/pz1/rc2_pz1.rom (EXTJOY=1
#                            PZ_TEST=1), R/pz2/rc2_pz2.rom (EXTJOY=1 PZ_TEST=1 PZ_LEVEL=2),
#                            R/trace/rc2_ext5.rom (trace's), R/ext/rc2_ext.rom (EXTJOY=1)
#
# The whole level-1 regression, three steps:
#   sh tools/bstest/hz.sh trace DIR
#   msx_local_cmd: source {<repo>/tools/bstest/hz.tcl}; hz_regress {DIR} {DIR/rc2_ext5.rom} {DIR/rc2_ext5.labels} tr
#                  then poll "list $::hz_state $::hz_msgs" (about 10 s) until "done"
#   sh tools/bstest/hz.sh compare DIR
set -u
H="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$H/../.." && pwd -P)"
usage() { sed -n 2,28p "$0" >&2; exit 2; }
# a folder's absolute path (the printed lines run in openMSX, whose working directory is another;
# compare runs from the repository root); "mk" creates it first
absdir() {
  if [ "${2:-}" = mk ]; then mkdir -p "$1" || return 1; fi
  (cd "$1" 2>/dev/null && pwd -P)
}
cmd="${1:-}"; shift || true
case "$cmd" in
trace)
  [ $# -ge 1 ] || usage
  D="$(absdir "$1" mk)" || exit 2
  sh "$H/build.sh" "$D/rc2_ext5.rom" EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 || exit 1
  echo "msx_local_cmd: source {$H/hz.tcl}; hz_regress {$D} {$D/rc2_ext5.rom} {$D/rc2_ext5.labels} tr"
  ;;
compare)
  [ $# -ge 1 ] || usage
  D="$(absdir "$1")" || { echo "hz.sh: no folder $1" >&2; exit 2; }
  if [ $# -ge 2 ]; then
    L="$(absdir "$(dirname "$2")")/$(basename "$2")"
  else
    L="$D/rc2_ext5.labels"
  fi
  [ -f "$L" ] || { echo "hz.sh: no label file $L (pass the traced ROM's)" >&2; exit 2; }
  bad=0
  cd "$ROOT" || exit 2
  for t in "cov1:4401:trace_cov1_ram.jsonl" "cov0:1400:trace_cov0_ram.jsonl" "cov0_tr:1400:trace_cov0_ram.jsonl"; do
    n=$(echo "$t" | cut -d: -f1); want=$(echo "$t" | cut -d: -f2); ref=$(echo "$t" | cut -d: -f3)
    [ -f "$D/$n.txt" ] || { [ "$n" = cov0_tr ] && continue; echo "$n: no trace"; bad=1; continue; }
    rows=$(grep -c . "$D/$n.txt")
    out=$(python3 -I tools/tracecmp.py --ram "build/emu/$ref" "$D/$n.txt" --labels "$L" 2>&1 | tail -1)
    echo "$n: $rows rows; $out"
    [ "$rows" -eq "$want" ] || { echo "  FAIL: $rows rows, $want expected"; bad=1; }
    echo "$out" | grep -q ": 0 differ" || { echo "  FAIL: differences"; bad=1; }
  done
  [ $bad -eq 0 ] && echo "regression: PASS" || echo "regression: FAIL"
  exit $bad
  ;;
product)
  [ $# -ge 1 ] || usage
  D="$(absdir "$1" mk)" || exit 2
  shift
  sh "$H/build.sh" "$D/rc2.rom" "$@" || exit 1
  echo "msx_local_cmd: source {$H/hz.tcl}; hz_fresh {FDIR} TAG {$D/rc2.rom} {$D/rc2.labels}"
  echo "  (FDIR: the folder that holds the reference's records; TAG: this build's name there)"
  ;;
fresh)
  [ $# -ge 3 ] || usage
  D="$1"; A="$2"; B="$3"; bad=0
  for f in title_vram.bin title_regs.bin title_pal.bin music.txt psg.txt game_vram.bin game_ram.bin; do
    if [ ! -f "$D/${A}_$f" ] || [ ! -f "$D/${B}_$f" ]; then echo "$f: missing"; bad=1; continue; fi
    if [ "$f" = music.txt ]; then
      # (the comment lines hold emulated times)
      grep -v '^#' "$D/${A}_$f" > "$D/.hz_a.txt"; grep -v '^#' "$D/${B}_$f" > "$D/.hz_b.txt"
      if cmp -s "$D/.hz_a.txt" "$D/.hz_b.txt"; then
        echo "$f: identical ($(grep -vc '^#' "$D/${A}_$f") ticks)"
      else echo "$f: DIFFERENT"; bad=1; fi
    elif cmp -s "$D/${A}_$f" "$D/${B}_$f"; then echo "$f: identical"
    else echo "$f: DIFFERENT ($(cmp -l "$D/${A}_$f" "$D/${B}_$f" | wc -l | tr -d ' ') bytes)"; bad=1; fi
  done
  echo "game: $(cat "$D/${A}_game.txt" 2>/dev/null) / $(cat "$D/${B}_game.txt" 2>/dev/null)"
  [ $bad -eq 0 ] && echo "fresh: PASS" || echo "fresh: FAIL"
  exit $bad
  ;;
builds)
  [ $# -ge 1 ] || usage
  R="$(absdir "$1" mk)" || exit 2
  bad=0
  for spec in "prod/rc2.rom" "pzt/rc2.rom PZ_TEST=1" "pz1/rc2_pz1.rom EXTJOY=1 PZ_TEST=1" \
              "pz2/rc2_pz2.rom EXTJOY=1 PZ_TEST=1 PZ_LEVEL=2" \
              "trace/rc2_ext5.rom EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1" "ext/rc2_ext.rom EXTJOY=1"; do
    # (sh splits the words; the options hold no spaces)
    set -- $spec
    out="$1"; shift
    echo "== $out $*"
    sh "$H/build.sh" "$R/$out" "$@" || bad=1
  done
  [ $bad -eq 0 ] && echo "builds: PASS ($R)" || echo "builds: FAIL"
  exit $bad
  ;;
*)
  usage ;;
esac
