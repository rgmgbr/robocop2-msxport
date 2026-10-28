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
#   hz.sh l2builds R         level 2's six trace builds (hz.tcl hz_l2; docs/LEVEL2.md 4.1), all
#                            EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2: R/l2/rc2_l2.rom (the
#                            default carry 10050:2:0:1, GOOD), R/l2s, R/l2f, R/l2p (LV_CARRY
#                            10050:2:0:0, :2, :3: SHARP, FAIR, POOR), R/l2o (0:0:0:1: the game over
#                            without a credit), R/l2c (0:0:1:1: with one), each rc2_<b>.rom
#   hz.sh compare --fields FIELDS DIR R [--refs REFS] [JOB[:ROWS] ...]
#                            level 2's traces (hz_l2): tools/tracecmp.py --ram --fields FIELDS
#                            (analysis/amiga_ram_l2.tsv) on DIR/l2_<job>.txt against its reference
#                            (build/emu/l2_<ref>_ram.jsonl, or REFS/l2_<ref>_ram.jsonl: the bench
#                            with the port's stubs, tools/bstest/l2stub.py) with its build's labels
#                            (R/<b>/rc2_<b>.labels): exit 0 only when every trace compared has its
#                            rows and 0 frames differ. JOB:ROWS compares the job's first ROWS rows
#                            only; without JOBs, every job whose trace is in DIR, whole, but cont
#                            as cont:109 until the port has the continue (level 2's step 19: its
#                            game over ends the trace at row 108, the plan's milestone 1)
#
# The whole level-1 regression, three steps:
#   sh tools/bstest/hz.sh trace DIR
#   msx_local_cmd: source {<repo>/tools/bstest/hz.tcl}; hz_regress {DIR} {DIR/rc2_ext5.rom} {DIR/rc2_ext5.labels} tr
#                  then poll "list $::hz_state $::hz_msgs" (about 10 s) until "done"
#   sh tools/bstest/hz.sh compare DIR
set -u
H="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$H/../.." && pwd -P)"
usage() { sed -n 2,41p "$0" >&2; exit 2; }
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
  if [ "$1" = --fields ]; then
    # level 2's jobs: name, build, reference, rows (hz.tcl hz_l2_jobs)
    [ $# -ge 4 ] || usage
    F="$(absdir "$(dirname "$2")")/$(basename "$2")"
    [ -f "$F" ] || { echo "hz.sh: no field file $2" >&2; exit 2; }
    D="$(absdir "$3")" || { echo "hz.sh: no folder $3" >&2; exit 2; }
    R="$(absdir "$4")" || { echo "hz.sh: no folder $4" >&2; exit 2; }
    shift 4
    E="$ROOT/build/emu"
    if [ "${1:-}" = --refs ]; then
      [ $# -ge 2 ] || usage
      E="$(absdir "$2")" || { echo "hz.sh: no folder $2" >&2; exit 2; }
      shift 2
    fi
    JOBS="end:l2:l2_end:259 tour:l2:l2_tour:2654 lift:l2:l2_lift:801 trolley:l2:l2_trolley:641
      vat:l2:l2_vat:701 fuzz:l2:l2_fuzz:2501 sharp:l2s:l2_trolley_sharp:641 fair:l2f:l2_trolley_fair:641
      poor:l2p:l2_trolley_poor:641 over:l2o:l2_over:109 cont:l2c:l2_cont:301 barrel:l2:l2_barrel:901
      mine:l2:l2_mine:161 t1left:l2:l2_t1left:341 drone:l2:l2_drone:401 tour_fx:l2:l2_tour:2654
      vat_fx:l2:l2_vat:701 trolley_eu:l2:l2_trolley:641 tour_tr:l2:l2_tour:2654 vat_tr:l2:l2_vat:701"
    want_jobs="$*"
    bad=0; seen=0
    cd "$ROOT" || exit 2
    for j in $JOBS; do
      n=$(echo "$j" | cut -d: -f1); b=$(echo "$j" | cut -d: -f2); ref=$(echo "$j" | cut -d: -f3)
      want=$(echo "$j" | cut -d: -f4); upto=""
      if [ -n "$want_jobs" ]; then
        hit=""
        for w in $want_jobs; do
          case "$w" in "$n") hit=1 ;; "$n":*) hit=1; upto="${w#*:}" ;; esac
        done
        [ -n "$hit" ] || continue
      elif [ ! -f "$D/l2_$n.txt" ]; then
        continue
      elif [ "$n" = cont ]; then
        upto=109                    # (until level 2's step 19, the continue: see the usage)
      fi
      seen=$((seen + 1))
      [ -f "$D/l2_$n.txt" ] || { echo "$n: no trace"; bad=1; continue; }
      L="$R/$b/rc2_$b.labels"
      [ -f "$L" ] || { echo "$n: no label file $L"; bad=1; continue; }
      rows=$(grep -c . "$D/l2_$n.txt")
      T="$D/l2_$n.txt"
      if [ -n "$upto" ]; then
        [ "$rows" -ge "$upto" ] || { echo "$n: $rows rows, $upto wanted"; bad=1; continue; }
        T="$D/.l2_$n.$upto.txt"; head -n "$upto" "$D/l2_$n.txt" > "$T"; want="$upto"; rows="$upto"
      fi
      [ -f "$E/${ref}_ram.jsonl" ] || { echo "$n: no reference $E/${ref}_ram.jsonl"; bad=1; continue; }
      out=$(python3 -I tools/tracecmp.py --ram --fields "$F" --labels "$L" "$E/${ref}_ram.jsonl" "$T" 2>&1 | tail -1)
      echo "$n: $rows rows${upto:+ (the first $upto)}; $out"
      [ "$rows" -eq "$want" ] || { echo "  FAIL: $rows rows, $want expected"; bad=1; }
      echo "$out" | grep -q ": 0 differ" || { echo "  FAIL: differences"; bad=1; }
    done
    [ $seen -gt 0 ] || { echo "hz.sh: no level-2 trace to compare in $D" >&2; bad=1; }
    [ $bad -eq 0 ] && echo "level 2: PASS ($seen traces)" || echo "level 2: FAIL"
    exit $bad
  fi
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
l2builds)
  [ $# -ge 1 ] || usage
  R="$(absdir "$1" mk)" || exit 2
  bad=0
  for spec in "l2" "l2s LV_CARRY=10050:2:0:0" "l2f LV_CARRY=10050:2:0:2" "l2p LV_CARRY=10050:2:0:3" \
              "l2o LV_CARRY=0:0:0:1" "l2c LV_CARRY=0:0:1:1"; do
    set -- $spec
    b="$1"; shift
    echo "== $b $*"
    sh "$H/build.sh" "$R/$b/rc2_$b.rom" EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2 "$@" || bad=1
  done
  [ $bad -eq 0 ] && echo "l2builds: PASS ($R)" || echo "l2builds: FAIL"
  exit $bad
  ;;
*)
  usage ;;
esac
