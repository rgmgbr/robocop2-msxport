#!/bin/sh
# rgview.sh: the shooting range's display checks at the camera's start (docs/RANGE.md 4.2 checks 2,
# 3, 5, 6, 7 and 10; the 15 drives' traces; docs/HARNESS.md 5.18). Three commands:
#
#   sh tools/bstest/rgview.sh builds W   W/fr2 (EXTJOY=1 PZ_TEST=2), W/fr2v2 (+ PZ_LEVEL=2) and W/ext
#                                        (EXTJOY=1), each through build.sh's checks; prints the Tcl line
#   msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; hz_chain [rgv_suite {W}]
#                                        (rgview.tcl: 54 jobs, a few minutes; poll
#                                        "list $::hz_state [llength $::hz_msgs] [lindex $::hz_msgs end]")
#   sh tools/bstest/rgview.sh check W    every verdict, then "rgview: PASS" or "rgview: FAIL"
#
# W: a work folder outside build/msx (a session scratch folder: the records take about 1 GB).
# The checks: the traces (tools/frngcmp.py: 0 differ, equal results and ratings); the stills and
# records (rgview.py still / rec against the bench's states); the display guard (reg, pal, cmd, cpu,
# vbl, tear 0); the VRAM speed (0 lost writes in the cartridge; the BIOS's own are listed); the pass
# rate (rgview.py rate: no late pass); the restore and the new game (restorecheck.py --known --range,
# tools/checkrun.py when ~/.venvs/msxports/bin/python has numpy, the lost counters 0).
set -u
REPO="$(cd "$(dirname "$0")/../.." && pwd -P)"
usage() { sed -n 2,19p "$0" >&2; exit 2; }
cmd="${1:-}"; [ $# -ge 2 ] || usage
mkdir -p "$2" || exit 2
W="$(cd "$2" && pwd -P)"
case "$W" in */build/msx|*/build/msx/*) echo "rgview.sh: not into build/msx (the user picks ROMs there)" >&2; exit 2 ;; esac
cd "$REPO" || exit 2
case "$cmd" in
builds)
  bad=0
  for spec in "fr2:EXTJOY=1 PZ_TEST=2" "fr2v2:EXTJOY=1 PZ_TEST=2 PZ_LEVEL=2" "ext:EXTJOY=1"; do
    out=${spec%%:*}; opts=${spec#*:}
    # (word splitting of $opts is wanted: sh, not zsh)
    r=$(sh tools/bstest/build.sh "$W/$out/rc2.rom" $opts 2>&1); rc=$?
    echo "$out [$opts]: $(echo "$r" | tail -1)"
    [ $rc -eq 0 ] || { echo "$r" | head -8; bad=1; }
  done
  grep -h -E '^frng_end:' "$W/fr2/rc2.labels" 2>/dev/null | sed 's/^/  BANK_FRNG ends at /'
  echo "msx_local_cmd: source {$REPO/tools/bstest/load.tcl}; hz_chain [rgv_suite {$W}]"
  exit $bad
  ;;
check)
  O="$W/O"; bad=0
  step() { echo; echo "== $1"; }
  verdict() { if [ "$1" -eq 0 ]; then echo "-> PASS"; else echo "-> FAIL"; bad=1; fi; }
  drive_of() {   # a job's name -> its drive (NAME_TAG, rate_NAME_TAG)
    n=${1#rate_}; echo "${n%_*}"
  }
  step "the traces against the bench (tools/frngcmp.py)"
  n=0; nb=0
  for f in "$O"/tr/*.txt; do
    t=$(basename "$f" .txt); d=$(drive_of "$t")
    [ -f "build/emu/fr_${d}_ram.jsonl" ] || continue
    r=$(python3 -I tools/frngcmp.py "build/emu/fr_${d}_ram.jsonl" "$f" 2>&1); rc=$?
    n=$((n + 1))
    if [ $rc -ne 0 ]; then nb=$((nb + 1)); echo "  $t: FAIL"; echo "$r" | head -5 | sed 's/^/    /'; fi
    printf '  %-20s %s | %s\n' "$t" "$(echo "$r" | grep 'frames compared' | head -1)" "$(echo "$r" | grep '^result' | head -1)"
  done
  for f in "$O"/flow/after_rg_*_fr.txt; do
    [ -f "$f" ] || continue
    r=$(python3 -I tools/frngcmp.py build/emu/fr_timeout_ram.jsonl "$f" 2>&1); rc=$?
    n=$((n + 1)); [ $rc -eq 0 ] || { nb=$((nb + 1)); echo "  $(basename "$f"): FAIL"; }
    printf '  %-20s %s\n' "$(basename "$f" .txt)" "$(echo "$r" | grep 'frames compared' | head -1)"
  done
  echo "  $n trace(s), $nb failing"
  [ "$nb" -eq 0 ] && [ "$n" -ge 45 ]; verdict $?
  step "the stills: the page on screen, its sprites and R#18 against tools/msxrange.py's render (rgview.py still)"
  sb=0; sn=0
  for d in "$O"/st/*; do
    [ -d "$d" ] || continue
    t=$(basename "$d"); dr=$(drive_of "$t")
    g="$W/fr2/gen"; [ "$dr" = armed2 ] && g="$W/fr2v2/gen"
    ls "$d"/p*.bin >/dev/null 2>&1 || continue
    python3 -I tools/bstest/rgview.py still "$d"/p*.bin --ref "build/emu/fr_${dr}_ram.jsonl" --gen "$g" > "$d/still.txt" 2>&1; rc=$?
    sn=$((sn + $(grep -c '^p[0-9]' "$d/still.txt")))
    [ $rc -eq 0 ] || { sb=1; grep -E 'FAIL' "$d/still.txt" | head -3 | sed "s/^/  $t: /"; }
    echo "  $t: $(tail -1 "$d/still.txt")"
  done
  echo "  $sn snapshot(s)"
  [ "$sb" -eq 0 ] && [ "$sn" -gt 0 ]; verdict $?
  step "the records: no torn element, the SAT, frame-to-frame coherence, the bench's states (rgview.py rec)"
  rb=0; rn=0
  for f in "$O"/st/*/rec.bin; do
    [ -f "$f" ] || continue
    d=$(dirname "$f"); t=$(basename "$d"); dr=$(drive_of "$t")
    g="$W/fr2/gen"; [ "$dr" = armed2 ] && g="$W/fr2v2/gen"
    python3 -I tools/bstest/rgview.py rec "$f" --ref "build/emu/fr_${dr}_ram.jsonl" --gen "$g" > "$d/rec.txt" 2>&1; rc=$?
    rn=$((rn + 1))
    [ $rc -eq 0 ] || { rb=1; head -4 "$d/rec.txt" | sed "s/^/  $t: /"; }
    echo "  $t: $(tail -1 "$d/rec.txt" | cut -c1-260)"
  done
  [ "$rb" -eq 0 ] && [ "$rn" -ge 15 ]; verdict $?
  step "the display guard over armed's passes (reg, pal, cmd, cpu, vbl, tear: 0)"
  gn=0; gb=0
  for f in "$O"/flow/guard_*.txt; do
    [ -f "$f" ] || continue
    gn=$((gn + 1))
    echo "  $(basename "$f" .txt): $(head -1 "$f" | cut -c1-120); $(grep -E '^(reg|pal|cmd|cpu|vbl|tear) ' "$f" | tr '\n' ' ')"
    [ "$(grep -E '^(reg|pal|cmd|cpu|vbl|tear) ' "$f" | grep -c -v ' 0$')" -eq 0 ] || { gb=1; sed -n 8,12p "$f" | sed 's/^/    /'; }
  done
  [ "$gb" -eq 0 ] && [ "$gn" -eq 3 ]; verdict $?
  step "VRAM access speed: armed from the power-on (0 lost in the cartridge; 3.58 and 5.37 MHz)"
  fn=0; fb=0
  for f in "$O"/flow/fast_*.txt; do
    [ -f "$f" ] || continue
    fn=$((fn + 1)); echo "  $(basename "$f" .txt): $(cut -c1-220 "$f")"
    grep -q "the cartridge's 0:" "$f" || fb=1
  done
  [ "$fb" -eq 0 ] && [ "$fn" -eq 4 ]; verdict $?
  step "the pass rate (50 a second, no late pass; the worst pass's T-states)"
  python3 -I tools/bstest/rgview.py rate "$O"/flow/rate_*_rate.txt | sed 's/^/  /'; verdict $?
  step "the restore after timeout's time out and the new game against a fresh start"
  for m in m2 tr; do
    python3 -I tools/bstest/restorecheck.py "$O/flow" after_rg_$m fresh_rg_$m --known --range > "$W/restore_rg_$m.txt" 2>&1; rc=$?
    sed "s/^/  $m: /" "$W/restore_rg_$m.txt" | cut -c1-200
    grep -h -E 'lost' "$O/flow/after_rg_${m}_after.txt" | sed "s/^/  $m: /"
    l=$(grep -h -E 'lost' "$O/flow/after_rg_${m}_after.txt" | grep -c -E 'mp 0 atr 0 rd 0 fb 0')
    [ "$rc" -eq 0 ] && [ "$l" -ge 1 ]; verdict $?
  done
  PY="$HOME/.venvs/msxports/bin/python"
  if [ -x "$PY" ] && "$PY" -c "import numpy" 2>/dev/null; then
    # (checkrun's exit status also counts "tile VRAM changed": the tile cache, as at a fresh start,
    #  and after the range page 3 lines 88-161, sheet S3, which fb_init freed: docs/HARNESS.md 5.18.
    #  The verdict: every picture 0 pixels differ and every sprite pixel exact.)
    for m in m2 tr; do
      echo "  checkrun after_rg_$m:"
      "$PY" -I tools/checkrun.py "$O/flow/after_rg_${m}_snaps" build/msx/level1 build/msx/hud > "$W/checkrun_rg_$m.txt" 2>&1
      grep -o -E '^s[0-9]+: frame [0-9]+|[0-9]+/[0-9]+ sprite pixels exact|[0-9]+ pixels checked, [0-9]+ differ|tile VRAM changed: [0-9]+ bytes' "$W/checkrun_rg_$m.txt" | paste -sd' ' - | sed 's/ s\([0-9]\)/\n    s\1/g; s/^/    /'
      np=$(grep -c -E '^s[0-9]+:' "$W/checkrun_rg_$m.txt")
      ex=$(grep -E '^s[0-9]+:' "$W/checkrun_rg_$m.txt" | grep -o -E '[0-9]+/[0-9]+ sprite pixels exact' | awk -F'[/ ]' '$1 != $2' | wc -l | tr -d ' ')
      d0=$(grep -E '^s[0-9]+:' "$W/checkrun_rg_$m.txt" | grep -c ', 0 differ')
      [ "$np" -ge 6 ] && [ "$d0" -eq "$np" ] && [ "$ex" -eq 0 ]; verdict $?
    done
  else
    echo "  (no numpy at $PY: checkrun.py skipped)"
  fi
  echo
  [ $bad -eq 0 ] && echo "rgview: PASS" || echo "rgview: FAIL"
  exit $bad
  ;;
*)
  usage ;;
esac
