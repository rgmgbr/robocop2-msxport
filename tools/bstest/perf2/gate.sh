#!/bin/sh
# gate.sh: the shell side of docs/PERF2_PLAN.md 5.4's gates (performance campaign 2's kit; docs/HARNESS.md
# section 12). The emulator side: gates.tcl's jobs (pf_gate_jobs W R) in a private session.
#
#   gate.sh builds R [SRC]     the gates' builds into R from SRC (a source tree with build/ linked to the
#                              main checkout's, e.g. a worktree; default this repository): R/l3/cap3.rom
#                              (EXTJOY=1 LV_TEST=3), R/l2/cap2.rom (EXTJOY=1 LV_TEST=2), R/l1/ext.rom
#                              (EXTJOY=1), R/L/l1|l2|l3/lock.rom (+ LOCKSTEP=24), and hz.sh's trace builds
#                              in R/T (l3builds, l2builds, trace)
#   gate.sh speed BASE NEW     G-SPEED: win.py --gate BASE/speed NEW/speed
#   gate.sh hold BASE NEW      G-HOLD: holds.py --gate BASE/speed NEW/speed (the same records)
#   gate.sh field BASE NEW [JOBS]
#                              G-FIELD: fieldcheck.py on NEW/field's windows (REPO's build/msx and
#                              fieldcheck.py judge them; JOBS windows at once, default 4), then
#                              fieldsum.py gate BASE/field NEW/field
#   gate.sh guard BASE NEW     G-GUARD: guardsum.py gate BASE/guard NEW/guard
#   gate.sh lock BASE NEW      G-LOCK: lockgate.py BASE/lock NEW/lock
#   gate.sh map BASE NEW [--ignore FROM-TO ...]
#                              G-MAP: mapdiff.py --gate BASE/map NEW/map
#   gate.sh logic W R          G-LOGIC: hz.sh compare on W/logic/l3 and W/logic/l2 (the Amiga bench,
#                              R/T's labels: level 3's 16 jobs and level 2's 23 by name, a missing trace
#                              FAILs) and W/logic/l1 (level 1's cov1, cov0, cov0_tr), with every job's
#                              lost counters 0 (W/logic/l<k>/lost.txt)
#   gate.sh all BASE NEW R     every verdict above in turn (each one's output in NEW/gate_<name>.txt);
#                              "gate: PASS" when all pass
# BASE: W0's HEAD records (the campaign's base folder); NEW: the run folder of pf_gate_jobs. Each verdict's
# last line reads "G-NAME: PASS" or "G-NAME: FAIL ...". Exit 0 only when the verdicts asked for pass.
# A run, window or record BASE holds that NEW lacks FAILs its verdict (as does one cut short).
# Environment: REPO, the checkout whose build/ (the drives' references, the conversions), analysis/ and
# tools/bstest/hz.sh, fieldcheck.py the verdicts use (default this repository; a git worktree has no
# build/: give the main checkout); PARTIAL=1: the verdicts but G-LOGIC judge only what NEW holds (each
# verdict's --partial: a deliberate subset, the records left out listed).
set -u
H="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$H/../../.." && pwd -P)"
usage() { sed -n 2,32p "$0" >&2; exit 2; }
REPO="${REPO:-$ROOT}"
PA=""; [ "${PARTIAL:-}" = 1 ] && PA="--partial"
cmd="${1:-}"; shift || true
abs() { (cd "$1" 2>/dev/null && pwd -P) || { echo "gate.sh: no folder $1" >&2; exit 2; }; }
case "$cmd" in
builds)
  [ $# -ge 1 ] || usage
  mkdir -p "$1" || exit 2
  R="$(abs "$1")"; S="${2:-$ROOT}"; S="$(abs "$S")"
  B="$S/tools/bstest/build.sh"; HZ="$S/tools/bstest/hz.sh"
  bad=0
  b() {
    out="$1"; shift
    mkdir -p "$(dirname "$R/$out")"
    if sh "$B" "$R/$out" "$@" > "$R/${out%.rom}.build.txt" 2>&1; then tail -1 "$R/${out%.rom}.build.txt"
    else echo "FAIL: $out ($R/${out%.rom}.build.txt)"; bad=$((bad + 1)); fi
  }
  b l3/cap3.rom EXTJOY=1 LV_TEST=3
  b l2/cap2.rom EXTJOY=1 LV_TEST=2
  b l1/ext.rom EXTJOY=1
  b L/l1/lock.rom EXTJOY=1 LOCKSTEP=24
  b L/l2/lock.rom EXTJOY=1 LV_TEST=2 LOCKSTEP=24
  b L/l3/lock.rom EXTJOY=1 LV_TEST=3 LOCKSTEP=24
  mkdir -p "$R/T"
  sh "$HZ" l3builds "$R/T" > "$R/T/l3builds.txt" 2>&1 || bad=$((bad + 1)); tail -1 "$R/T/l3builds.txt"
  sh "$HZ" l2builds "$R/T" > "$R/T/l2builds.txt" 2>&1 || bad=$((bad + 1)); tail -1 "$R/T/l2builds.txt"
  sh "$HZ" trace "$R/T/trace" > "$R/T/trace.txt" 2>&1 || bad=$((bad + 1)); grep "build OK" "$R/T/trace.txt" | tail -1
  echo "gate builds: $([ $bad -eq 0 ] && echo OK || echo "$bad FAILED") ($R)"
  [ $bad -eq 0 ]
  ;;
speed) [ $# -eq 2 ] || usage; python3 -I "$H/win.py" --gate "$1/speed" "$2/speed" $PA ;;
hold) [ $# -eq 2 ] || usage; python3 -I "$H/holds.py" --gate "$1/speed" "$2/speed" $PA ;;
field)
  [ $# -ge 2 ] || usage
  J="${3:-4}"
  python3 -I "$H/fieldsum.py" run "$2/field" --root "$REPO" --jobs "$J" > "$2/field/fieldsum_run.txt" 2>&1
  python3 -I "$H/fieldsum.py" gate "$1/field" "$2/field" $PA
  ;;
guard) [ $# -eq 2 ] || usage; python3 -I "$H/guardsum.py" gate "$1/guard" "$2/guard" $PA ;;
lock) [ $# -eq 2 ] || usage; python3 -I "$H/lockgate.py" "$1/lock" "$2/lock" $PA ;;
map) [ $# -ge 2 ] || usage; B="$1"; N="$2"; shift 2; python3 -I "$H/mapdiff.py" --gate "$B/map" "$N/map" "$@" $PA ;;
logic)
  [ $# -eq 2 ] || usage
  W="$(abs "$1")"; R="$(abs "$2")"
  bad=0
  # (every trace pf_logic_jobs makes, named: hz.sh compare fails a named job without its trace, where
  #  it skips an unnamed one; and every job's lost counters, levels 2 and 3 by hz.sh, level 1's here)
  L3J="tour3 tour3_fx tour3_tr beam park park_fx park_tr boss boss_fx boss_tr kill kill_fx kill_tr cont3 cont3_fx cont3_tr"
  L2J="end tour lift trolley vat fuzz sharp fair poor over cont barrel mine t1left drone tour_fx vat_fx trolley_eu tour_tr vat_tr flow_l2_end cont_fx cont_tr"
  for l in l3 l2; do
    [ -f "$W/logic/$l/lost.txt" ] || { echo "$l: FAIL: no lost counters ($W/logic/$l/lost.txt)"; bad=1; }
  done
  sh "$REPO/tools/bstest/hz.sh" compare --fields "$REPO/analysis/amiga_ram_l3.tsv" "$W/logic/l3" "$R/T" $L3J || bad=1
  sh "$REPO/tools/bstest/hz.sh" compare --fields "$REPO/analysis/amiga_ram_l2.tsv" "$W/logic/l2" "$R/T" $L2J || bad=1
  sh "$REPO/tools/bstest/hz.sh" compare "$W/logic/l1" "$R/T/trace/rc2_ext5.labels" || bad=1
  for j in cov1 cov0 cov0_tr; do
    [ -f "$W/logic/l1/$j.txt" ] || { echo "$j: FAIL: no trace"; bad=1; }
    lost=$(grep "^$j (" "$W/logic/l1/lost.txt" 2>/dev/null | tail -1)
    if [ -z "$lost" ]; then
      echo "$j: FAIL: no lost counters in $W/logic/l1/lost.txt (gates.tcl pf_logic_jobs' level-1 jobs record them: run cov1, cov0, cov0_tr again)"; bad=1
    else
      echo "$j lost: ${lost#*): }"
      echo "$lost" | grep -q '): mp 0 atr 0 rd 0 fb 0 pools ' || { echo "  FAIL: lost counters"; bad=1; }
    fi
  done
  echo "G-LOGIC: $([ $bad -eq 0 ] && echo PASS || echo FAIL)"
  [ $bad -eq 0 ]
  ;;
all)
  [ $# -ge 3 ] || usage
  B="$1"; N="$2"; R="$3"
  bad=0
  for g in speed hold guard lock map field logic; do
    if [ "$g" = logic ]; then a1="$N"; a2="$R"; else a1="$B"; a2="$N"; fi
    if REPO="$REPO" sh "$0" "$g" "$a1" "$a2" > "$N/gate_$g.txt" 2>&1; then :; else bad=$((bad + 1)); fi
    tail -1 "$N/gate_$g.txt"
  done
  echo "gate: $([ $bad -eq 0 ] && echo PASS || echo "FAIL ($bad)")"
  [ $bad -eq 0 ]
  ;;
*) usage ;;
esac
