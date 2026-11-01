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
#                            without a credit), R/l2c (0:0:1:1: with one), each rc2_<b>.rom; and
#                            R/flow/rc2_flow.rom (EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 without LV_TEST:
#                            the product's way into level 2 for hz_l2's flow_l2_end, step 18)
#   hz.sh l3builds R         level 3's trace build (hz.tcl hz_l3; docs/LEVEL3.md 3.8): R/l3/rc2_l3.rom
#                            (EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=3, the default carry)
#   hz.sh fxbuilds R         level 2's sound logs' builds (fxlog.tcl fxl_jobs; docs/LEVEL2.md 4.3),
#                            each R/<b>/rc2.rom: l2, l2x (+ NO_SCC_INT=1), l2n (+ NO_SCC=1) EXTJOY=1
#                            ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2; l2c, l2cn (+ NO_SCC=1) the same with
#                            LV_CARRY=0:0:1:1; pz1 (PZ_TEST=1), pz2 (PZ_TEST=1 PZ_LEVEL=2), pz1n, pz2n
#                            (+ NO_SCC=1): no script
#   hz.sh compare --fields FIELDS DIR R [--refs REFS] [JOB[:ROWS] ...]
#                            level 2's traces (hz_l2): tools/tracecmp.py --ram --fields FIELDS
#                            (analysis/amiga_ram_l2.tsv) on DIR/l2_<job>.txt against its reference
#                            (build/emu/l2_<ref>_ram.jsonl, or REFS/l2_<ref>_ram.jsonl: the bench
#                            with the port's stubs, tools/bstest/l2stub.py) with its build's labels
#                            (R/<b>/rc2_<b>.labels): exit 0 only when every trace compared has its
#                            rows and 0 frames differ. JOB:ROWS compares the job's first ROWS rows
#                            only; without JOBs, every job whose trace is in DIR, whole (cont,
#                            cont_fx, cont_tr through the continue since level 2's step 19). With
#                            DIR/lost.txt (hz_l2's), each job's lost counters too: mp, atr, rd
#                            and fb 0 (the pools' use printed). With analysis/amiga_ram_l3.tsv:
#                            level 3's jobs (hz_l3: tour3, tour3_fx, tour3_tr, beam; DIR/l3_<job>.txt
#                            against build/emu/l3_<ref>_ram.jsonl or REFS', tools/bstest/l3stub.py)
#
# The whole level-1 regression, three steps:
#   sh tools/bstest/hz.sh trace DIR
#   msx_local_cmd: source {<repo>/tools/bstest/hz.tcl}; hz_regress {DIR} {DIR/rc2_ext5.rom} {DIR/rc2_ext5.labels} tr
#                  then poll "list $::hz_state $::hz_msgs" (about 10 s) until "done"
#   sh tools/bstest/hz.sh compare DIR
set -u
H="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$H/../.." && pwd -P)"
usage() { sed -n 2,55p "$0" >&2; exit 2; }
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
    P=l2                    # (the level's prefix: its jobs, traces and references)
    case "$(basename "$F")" in *_l3.tsv) P=l3 ;; esac
    JOBS="end:l2:l2_end:259 tour:l2:l2_tour:2654 lift:l2:l2_lift:801 trolley:l2:l2_trolley:641
      vat:l2:l2_vat:701 fuzz:l2:l2_fuzz:2501 sharp:l2s:l2_trolley_sharp:641 fair:l2f:l2_trolley_fair:641
      poor:l2p:l2_trolley_poor:641 over:l2o:l2_over:109 cont:l2c:l2_cont:301 barrel:l2:l2_barrel:901
      mine:l2:l2_mine:161 t1left:l2:l2_t1left:341 drone:l2:l2_drone:401 tour_fx:l2:l2_tour:2654
      vat_fx:l2:l2_vat:701 trolley_eu:l2:l2_trolley:641 tour_tr:l2:l2_tour:2654 vat_tr:l2:l2_vat:701
      flow_l2_end:flow:l2_flow_l2_end:259 cont_fx:l2c:l2_cont:301 cont_tr:l2c:l2_cont:301"
    [ "$P" = l3 ] && JOBS="tour3:l3:l3_tour3:1401 tour3_fx:l3:l3_tour3:1401 tour3_tr:l3:l3_tour3:1401
      beam:l3:l3_beam:501"
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
      elif [ ! -f "$D/${P}_$n.txt" ]; then
        continue
      fi
      seen=$((seen + 1))
      [ -f "$D/${P}_$n.txt" ] || { echo "$n: no trace"; bad=1; continue; }
      L="$R/$b/rc2_$b.labels"
      [ -f "$L" ] || { echo "$n: no label file $L"; bad=1; continue; }
      rows=$(grep -c . "$D/${P}_$n.txt")
      T="$D/${P}_$n.txt"
      if [ -n "$upto" ]; then
        [ "$rows" -ge "$upto" ] || { echo "$n: $rows rows, $upto wanted"; bad=1; continue; }
        T="$D/.${P}_$n.$upto.txt"; head -n "$upto" "$D/${P}_$n.txt" > "$T"; want="$upto"; rows="$upto"
      fi
      [ -f "$E/${ref}_ram.jsonl" ] || { echo "$n: no reference $E/${ref}_ram.jsonl"; bad=1; continue; }
      out=$(python3 -I tools/tracecmp.py --ram --fields "$F" --labels "$L" "$E/${ref}_ram.jsonl" "$T" 2>&1 | tail -1)
      echo "$n: $rows rows${upto:+ (the first $upto)}; $out"
      [ "$rows" -eq "$want" ] || { echo "  FAIL: $rows rows, $want expected"; bad=1; }
      echo "$out" | grep -q ": 0 differ" || { echo "  FAIL: differences"; bad=1; }
      if [ -f "$D/lost.txt" ]; then
        # (hz_l2's lost counters: the job's last line)
        lost=$(grep "^${P}_$n (" "$D/lost.txt" | tail -1)
        if [ -z "$lost" ]; then
          echo "  FAIL: no lost counters for ${P}_$n in $D/lost.txt"; bad=1
        else
          echo "  lost: ${lost#*): }"
          echo "$lost" | grep -q '): mp 0 atr 0 rd 0 fb 0 pools ' || { echo "  FAIL: lost counters"; bad=1; }
        fi
      fi
    done
    [ -f "$D/lost.txt" ] || echo "(no $D/lost.txt: the lost counters not checked)"
    LV=$(echo "$P" | cut -c2)
    [ $seen -gt 0 ] || { echo "hz.sh: no level-$LV trace to compare in $D" >&2; bad=1; }
    [ $bad -eq 0 ] && echo "level $LV: PASS ($seen traces)" || echo "level $LV: FAIL"
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
  # (the product's way into level 2 for flow_l2_end: level 1, the stages and the briefing first)
  echo "== flow (no LV_TEST)"
  sh "$H/build.sh" "$R/flow/rc2_flow.rom" EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 || bad=1
  [ $bad -eq 0 ] && echo "l2builds: PASS ($R)" || echo "l2builds: FAIL"
  exit $bad
  ;;
l3builds)
  [ $# -ge 1 ] || usage
  R="$(absdir "$1" mk)" || exit 2
  echo "== l3 EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=3"
  sh "$H/build.sh" "$R/l3/rc2_l3.rom" EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=3 && echo "l3builds: PASS ($R)" \
    || { echo "l3builds: FAIL"; exit 1; }
  ;;
fxbuilds)
  [ $# -ge 1 ] || usage
  R="$(absdir "$1" mk)" || exit 2
  bad=0
  T="EXTJOY=1 ENEMY_CAP=0 DAMAGE_X=1 LV_TEST=2"
  for spec in "l2 $T" "l2x $T NO_SCC_INT=1" "l2n $T NO_SCC=1" "l2c $T LV_CARRY=0:0:1:1" \
              "l2cn $T LV_CARRY=0:0:1:1 NO_SCC=1" "pz1 PZ_TEST=1" "pz2 PZ_TEST=1 PZ_LEVEL=2" \
              "pz1n PZ_TEST=1 NO_SCC=1" "pz2n PZ_TEST=1 PZ_LEVEL=2 NO_SCC=1"; do
    set -- $spec
    b="$1"; shift
    echo "== $b $*"
    sh "$H/build.sh" "$R/$b/rc2.rom" "$@" || bad=1
  done
  [ $bad -eq 0 ] && echo "fxbuilds: PASS ($R)" || echo "fxbuilds: FAIL"
  exit $bad
  ;;
*)
  usage ;;
esac
