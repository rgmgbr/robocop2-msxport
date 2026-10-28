#!/bin/sh
# l2base.sh: level 2's base (step 0 of its plan, docs/HARNESS.md 5.21) and the one comparison of any
# later build against it: the range's whole regression (regress.sh, 5.19) and level 1's records that
# it does not make (l2base.tcl: the death-and-restart and end traces, the start check, the field
# check, the stills, the LOCKSTEP records, the effects). Commands, from anywhere:
#
#   sh tools/bstest/l2base.sh builds W         regress.sh builds W, the LOCKSTEP=24 builds W/L/lock24
#                                              and W/L/lock24p (NO_SCC=1), the code banks' free bytes
#                                              (W/banks.txt); prints the Tcl line:
#   msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; source {<repo>/tools/bstest/l2base.tcl}; l2b_chain {W} {W/all.done}
#                                              (226 jobs; wait for W/all.done)
#   sh tools/bstest/l2base.sh check W BASE [RB] every verdict against BASE (and regress.sh's against RB,
#                                              default BASE), then "l2base: PASS"; exit 0 on PASS
#   sh tools/bstest/l2base.sh base W           W, once its check passed, made a base: its title from
#                                              power-on (fresh/new_*) becomes fresh/base_* (regress.sh
#                                              check reads a base's title there)
#
# W and BASE: folders outside build/msx (a session's scratch folder). The fieldcheck and msxframe
# verdicts need the venv's Python (numpy): PY, default ~/.venvs/msxports/bin/python.
set -u
H="$(cd "$(dirname "$0")" && pwd -P)"
REPO="$(cd "$H/../.." && pwd -P)"
PY="${PY:-$HOME/.venvs/msxports/bin/python}"
usage() { sed -n 2,24p "$0" >&2; exit 2; }
cmd="${1:-}"; [ $# -ge 2 ] || usage
mkdir -p "$2" || exit 2
W="$(cd "$2" && pwd -P)"
shift 2
step() { echo; echo "== $1"; }
verdict() { if [ "$1" -eq 0 ]; then echo "-> PASS"; else echo "-> FAIL"; bad=1; fi; }
case "$cmd" in
builds)
  cd "$REPO" || exit 2
  bad=0
  sh "$H/regress.sh" builds "$W" > "$W/regress_builds.log" 2>&1 || bad=1
  grep -E 'build OK|FAIL|builds:' "$W/regress_builds.log" | sed 's/: build OK: .*(/: build OK (/' | cut -c1-120
  for spec in "lock24 EXTJOY=1 LOCKSTEP=24" "lock24p EXTJOY=1 LOCKSTEP=24 NO_SCC=1"; do
    set -- $spec; d=$1; shift
    r=$(sh "$H/build.sh" "$W/L/$d/rc2.rom" "$@" 2>&1) || { echo "$r" | head -8; bad=1; }
    echo "L/$d [$*]: $(echo "$r" | tail -1 | sed 's/.*build OK: [^ ]*/build OK/')"
  done
  python3 -I "$H/l2base.py" banks "$W" > "$W/banks.txt" 2>&1 || bad=1
  echo "the code banks' free bytes: $W/banks.txt"
  echo "msx_local_cmd: source {$H/load.tcl}; source {$H/l2base.tcl}; l2b_chain {$W} {$W/all.done}"
  [ $bad -eq 0 ] && echo "builds: PASS" || echo "builds: FAIL"
  exit $bad
  ;;
check)
  [ $# -ge 1 ] || usage
  B="$(cd "$1" && pwd -P)" || exit 2
  RB="${2:-$B}"
  RB="$(cd "$RB" && pwd -P)" || exit 2
  cd "$REPO" || exit 2
  O="$W/l1"; BO="$B/l1"; bad=0
  step "the range's whole regression (regress.sh check against $RB)"
  sh "$H/regress.sh" check "$W" "$RB" > "$W/regress_check.log" 2>&1; rc=$?
  grep -E '^== |-> FAIL|regress:' "$W/regress_check.log" | sed 's/^/  /' | cut -c1-200
  echo "  ($(grep -c -- '-> PASS' "$W/regress_check.log") verdicts PASS, $(grep -c -- '-> FAIL' "$W/regress_check.log") FAIL: $W/regress_check.log)"
  verdict $rc
  step "level 1's death-and-restart and end drives against the bench (948 fields)"
  r1=0
  for t in "die 901" "over 1249" "end 517"; do
    set -- $t
    out=$(python3 -I tools/tracecmp.py --ram --labels "$W/R/trace/rc2_ext5.labels" "build/emu/trace_${1}_ram.jsonl" "$O/trace/$1.txt" 2>&1 | tail -1)
    rows=$(grep -c . "$O/trace/$1.txt" 2>/dev/null)
    echo "  $1: $rows rows; $out"
    echo "$out" | grep -q ": 0 differ" && [ "$rows" = "$2" ] || r1=1
  done
  verdict $r1
  step "the start check: the product from the power-on, 40 s of level 1 (C-BIOS_MSX2, FS-A1FX, FS-A1GT)"
  r1=0
  for m in m2 fx tr; do
    printf '  %s: ' $m
    python3 -I "$H/l2base.py" start "$O/start/st_$m.txt" "$BO/start/st_$m.txt" | tr '\n' ' ' | cut -c1-260; echo
    python3 -I "$H/l2base.py" start "$O/start/st_$m.txt" "$BO/start/st_$m.txt" > /dev/null 2>&1 || r1=1
  done
  verdict $r1
  step "the field check: every play-area pixel no sprite covers (fieldcheck.py; drive_cov0's windows)"
  for d in "$O"/field/*_m2 "$O"/field/*_fx; do
    [ -d "$d" ] || continue
    "$PY" -I "$H/fieldcheck.py" "$d" build/msx/level1 "$d.png" > "$d.check.txt" 2>&1 &
  done
  wait
  r1=0; n=0
  for d in "$BO"/field/*_m2 "$BO"/field/*_fx; do
    [ -d "$d" ] || continue
    t=$(basename "$d"); n=$((n + 1))
    printf '  %s: ' "$t"
    python3 -I "$H/l2base.py" field "$O/field/$t.check.txt" "$d.check.txt" || r1=1
  done
  [ "$n" -ge 6 ] || r1=1
  verdict $r1
  step "the stills (LOCKSTEP=24 build, drive_cov0 at game frames 100-2400): msxframe.py, then against the base's pictures"
  r1=0
  for m in m2 fx; do
    for s in "$O"/still/$m/g*; do
      [ -d "$s" ] || continue
      "$PY" -I tools/msxframe.py "$s" build/msx/level1 build/msx/hud "$O/still/${m}_$(basename "$s").png" > "$O/still/${m}_$(basename "$s").txt" 2>&1
      # (msxframe's exit status follows its own count, which l2base.py stills judges against the base's)
    done
  done
  python3 -I "$H/l2base.py" stills "$O/still" "$BO/still" | sed 's/^/  /' || r1=1
  python3 -I "$H/l2base.py" stills "$O/still" "$BO/still" > /dev/null 2>&1 || r1=1
  verdict $r1
  step "the LOCKSTEP records (3000 lists of drive_cov0) against the base's (tools/dispcmp.py)"
  r1=0
  for m in m2 fx; do
    out=$(python3 -I tools/dispcmp.py "$BO/lock/disp_$m.txt" "$O/lock/disp_$m.txt" 2>&1); c=$?
    echo "  $m: $(wc -l < "$O/lock/disp_$m.txt" | tr -d ' ') lines, $(cat "$O/lock/disp_$m.over" 2>/dev/null); $(echo "$out" | tail -1)"
    [ $c -eq 0 ] || r1=1
  done
  verdict $r1
  step "the effects (300 s of drive_cov0, LOCKSTEP=24): write for write as the base"
  r1=0
  f="$O/fx/fx_scc.txt"
  echo "  the SCC (sess_fxlog.tcl): $(grep -c '^S' "$f" 2>/dev/null) starts, $(grep -c '^T' "$f" 2>/dev/null) ticks; $(cmp -s "$BO/fx/fx_scc.txt" "$f" && echo identical to the base || echo DIFFERS from the base)"
  cmp -s "$BO/fx/fx_scc.txt" "$f" && [ "$(grep -c '^S' "$f")" -gt 0 ] || r1=1
  for k in scc psg; do
    f="$O/fx/pw_$k.txt"
    echo "  the PSG's writes ($k build): $(tail -1 "$f" 2>/dev/null | sed 's/^# //'); $(cmp -s "$BO/fx/pw_$k.txt" "$f" && echo identical to the base || echo DIFFERS from the base)"
    cmp -s "$BO/fx/pw_$k.txt" "$f" && [ "$(grep -c -v '^#' "$f")" -gt 0 ] || r1=1
  done
  verdict $r1
  step "the code banks' free bytes (against the base's)"
  python3 -I "$H/l2base.py" banks "$W" "$B" > "$W/banks.txt" 2>&1
  sed -n '1,4p' "$W/banks.txt" | sed 's/^/  /'
  echo "  (every build: $W/banks.txt)"
  echo
  [ $bad -eq 0 ] && echo "l2base: PASS" || echo "l2base: FAIL"
  exit $bad
  ;;
base)
  [ -d "$W/fresh" ] || { echo "no $W/fresh"; exit 1; }
  n=0
  for f in "$W"/fresh/new_*; do
    [ -f "$f" ] || continue
    cp "$f" "$W/fresh/base_${f##*/new_}"; n=$((n + 1))
  done
  echo "$W: $n title records copied to fresh/base_* (regress.sh check W2 $W compares W2's title with this one's)"
  [ -f "$W/check_all.log" ] && [ -d "$W/O/np" ] && [ -d "$W/O/st/solve1_m2" ] && [ -d "$W/l1" ] || { echo "base: incomplete (run the chain and check first)"; exit 1; }
  echo "base: ready"
  ;;
*)
  usage ;;
esac
