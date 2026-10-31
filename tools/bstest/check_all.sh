#!/bin/sh
# check_all.sh OUT TAG...: for each job NAME_TAG of hz7_job (OUT/tr/NAME_TAG.txt, OUT/st/NAME_TAG/;
# suite.tcl suite_drives runs them): tools/puzlcmp.py against build/emu/pz_NAME_ram.jsonl (0 differ,
# the result), stepcheck.py still on its snapshots and rec on its record (with the bench's trace
# for the cursor; the report in OUT/st/NAME_TAG/rec.txt). NAME: the nine drives (solve1 fail
# timeout quirk2 fuzz1 quirk1 opp solve2 fuzz2); a missing trace is skipped; solve2 and fuzz2 are
# visit 2's (stepcheck.py --visit 2: Ellen's pictures, visit 2's cursor colours). Exit 0 when all pass.
# docs/HARNESS.md.
set -u
if [ $# -lt 2 ]; then sed -n 2,8p "$0" >&2; exit 2; fi
H="$(cd "$(dirname "$0")" && pwd -P)"
ROOT="$(cd "$H/../.." && pwd -P)"
OUT="$(cd "$1" 2>/dev/null && pwd -P)" || { echo "check_all.sh: no folder $1" >&2; exit 2; }
shift
cd "$ROOT" || exit 2
bad=0
for tag in "$@"; do
  for d in solve1 fail timeout quirk2 fuzz1 quirk1 opp solve2 fuzz2; do
    t="$OUT/tr/${d}_$tag.txt"
    [ -f "$t" ] || continue
    case "$d" in solve2|fuzz2) vis="--visit 2" ;; *) vis="" ;; esac
    r=$(python3 -I tools/puzlcmp.py "build/emu/pz_${d}_ram.jsonl" "$t" 2>&1 | tr '\n' ' ')
    echo "${d}_$tag: $r"
    echo "$r" | grep -q ": 0 differ" || bad=1
    st="$OUT/st/${d}_$tag"
    if ls "$st"/p*.bin >/dev/null 2>&1; then
      s=$(python3 -I "$H/stepcheck.py" still $vis "$st"/p*.bin | tail -1)
      echo "  still: $s"
      echo "$s" | grep -q ", 0 with differences" || bad=1
    fi
    if [ -s "$st/rec.bin" ]; then
      python3 -I "$H/stepcheck.py" rec "$st/rec.bin" --ref "build/emu/pz_${d}_ram.jsonl" $vis > "$st/rec.txt" 2>&1 || bad=1
      sed 's/^/  rec: /' "$st/rec.txt" | tail -4
    fi
  done
done
[ $bad -eq 0 ] && echo "check_all: PASS" || echo "check_all: FAIL"
exit $bad
