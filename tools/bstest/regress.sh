#!/bin/sh
# regress.sh: the shooting range milestone's whole regression against the base 4a8a61d (the commit
# before the range; docs/HARNESS.md 5.19). Commands, from anywhere (the repository is two folders up):
#
#   sh tools/bstest/regress.sh base B        the base: a worktree of 4a8a61d in B/wt (the build data
#                                            copied, the two conversions the range changed rebuilt
#                                            with the base's tools), its builds in B/R (hz.sh builds),
#                                            the product checked against its known SHA-256; prints
#                                            the Tcl line of its records (rgr_base_chain B)
#   sh tools/bstest/regress.sh basecheck B   after rgr_base_chain: check_all.sh's log B/check_all.log
#   sh tools/bstest/regress.sh builds W      the repository's builds as it is now: W/R (hz.sh builds),
#                                            W/X (the range's test builds), W/V (rgview.sh builds),
#                                            W/S (the sound's builds), W/drives; prints the Tcl line
#   msx_local_cmd: source {<repo>/tools/bstest/load.tcl}; rgr_chain {W} all {W/all.done}
#                                            (about 210 jobs; or one family: flows, final, drives,
#                                            range, display, sound; poll, or wait for the file)
#   sh tools/bstest/regress.sh check W B [FAMILY ...]
#                                            every verdict (default: every family whose records
#                                            exist), then "regress: PASS" or "FAIL"; exit 0 on PASS
#
# W and B: folders outside build/msx (a session's scratch folder). B holds the base's records and is
# made once per milestone; it needs the MCP's openMSX for rgr_base_chain (about 45 jobs).
set -u
H="$(cd "$(dirname "$0")" && pwd -P)"
REPO="$(cd "$H/../.." && pwd -P)"
BASE_COMMIT=4a8a61d
BASE_PROD=29d29e99e24731c8
usage() { sed -n 2,24p "$0" >&2; exit 2; }
cmd="${1:-}"; [ $# -ge 2 ] || usage
mkdir -p "$2" || exit 2
W="$(cd "$2" && pwd -P)"
shift 2
step() { echo; echo "== $1"; }
verdict() { if [ "$1" -eq 0 ]; then echo "-> PASS"; else echo "-> FAIL"; bad=1; fi; }
bld() {   # bld DIR OPTIONS...: one build through build.sh's checks
  d="$1"; shift
  r=$(sh "$H/build.sh" "$d/rc2.rom" "$@" 2>&1); rc=$?
  echo "$(basename "$d") [$*]: $(echo "$r" | tail -1 | sed 's/.*build OK: [^ ]*/build OK/')"
  [ $rc -eq 0 ] || { echo "$r" | head -8; bad=1; }
}
case "$cmd" in
base)
  cd "$REPO" || exit 2
  bad=0
  if [ ! -d "$W/wt" ]; then git worktree add --detach "$W/wt" $BASE_COMMIT || exit 2; fi
  mkdir -p "$W/wt/build"
  # (build/extracted is read only; build/ram and build/msx are copied: a symlinked build would defeat
  #  build.sh's guard. build/msx without ROMs, labels, pictures and the generated sources)
  [ -e "$W/wt/build/extracted" ] || ln -s "$REPO/build/extracted" "$W/wt/build/extracted"
  rm -rf "$W/wt/build/ram" "$W/wt/build/msx"
  cp -R build/ram "$W/wt/build/ram"
  mkdir -p "$W/wt/build/msx"
  (cd build/msx && find . -type f ! -name '*.rom' ! -name '*.ROM' ! -name '*.labels' ! -name '*.png' \
     ! -path './gen/*' ! -name '*.wav' -print | cpio -pdm "$W/wt/build/msx" 2>/dev/null)
  # (the two conversions the range's step 4 changed, back to the base's: its own tools)
  (cd "$W/wt" && python3 -I tools/msxhudrt.py build/extracted/files/PERMA_05.bin build/extracted/boot/main_8000.bin build/extracted/files/PUZL_25.bin build/msx/hud_rt \
     && python3 -I tools/msxtext.py build/ram/level1_full.bin build/msx/text.inc build/msx/title.sc8 build/msx/title_credit.sc8 build/msx/gameover.sc8 build/msx/gameover_text.sc8) > "$W/convert.log" 2>&1 || { echo "the base's conversions failed: $W/convert.log"; exit 1; }
  (cd "$W/wt" && sh tools/bstest/hz.sh builds "$W/R") > "$W/builds.log" 2>&1 || bad=1
  grep -E '^==|build OK|FAIL|builds:' "$W/builds.log"
  sha=$(shasum -a 256 "$W/R/prod/rc2.rom" | cut -c1-16)
  echo "the base's product: $sha (known: $BASE_PROD)"
  [ "$sha" = "$BASE_PROD" ] || bad=1
  echo "msx_local_cmd: source {$H/load.tcl}; rgr_base_chain {$W} {$W/base.done}"
  [ $bad -eq 0 ] && echo "base: builds PASS" || echo "base: builds FAIL"
  exit $bad
  ;;
basecheck)
  cd "$REPO" || exit 2
  sh "$H/check_all.sh" "$W/O" m2 tr fx eu > "$W/check_all.log" 2>&1
  tail -3 "$W/check_all.log"
  echo "the base's Brainstorm checks in $W/check_all.log (a torn cell under a black palette is the known case)"
  exit 0
  ;;
builds)
  cd "$REPO" || exit 2
  bad=0
  sh "$H/hz.sh" builds "$W/R" > "$W/builds.log" 2>&1 || bad=1
  grep -E '^==|build OK|FAIL|builds:' "$W/builds.log"
  bld "$W/X/fr2" EXTJOY=1 PZ_TEST=2
  bld "$W/X/fr2t" EXTJOY=1 PZ_TEST=2 ENEMY_CAP=0 DAMAGE_X=1
  bld "$W/X/fr2tag" EXTJOY=1 PZ_TEST=2 TAG=4
  bld "$W/X/ext" EXTJOY=1
  bld "$W/X/pzt2" PZ_TEST=2
  bld "$W/X/p2m" ROM_2M=1
  bld "$W/X/cand" PZ_TEST=1 TAG=4
  sh "$H/rgview.sh" builds "$W/V" > "$W/builds_v.log" 2>&1 || bad=1
  grep -E 'build OK|FAIL|rc=' "$W/builds_v.log" | sed 's/^/V: /'
  # (the sound's: W/S/fr2 and W/S/pz2 are W/X/fr2's and W/X/pzt2's options, copied)
  mkdir -p "$W/S"
  rm -rf "$W/S/fr2" "$W/S/pz2"
  cp -R "$W/X/fr2" "$W/S/fr2"; cp -R "$W/X/pzt2" "$W/S/pz2"
  bld "$W/S/fr2_noscc" EXTJOY=1 PZ_TEST=2 NO_SCC=1
  bld "$W/S/fr2_nosccint" EXTJOY=1 PZ_TEST=2 NO_SCC_INT=1
  bld "$W/S/fr2_psg" EXTJOY=1 PZ_TEST=2 NO_SCC=1 NO_FM=1
  bld "$W/S/pz2_noscc" PZ_TEST=2 NO_SCC=1
  mkdir -p "$W/drives"
  for spec in 16,0,1 15,0,1 13,2,1 25,0,0 0,0,2; do
    c=${spec%%,*}; rest=${spec#*,}; d=${rest%%,*}; m=${rest#*,}
    printf '\n\n0\n5:0xb04:%d:2 5:0xb06:%d:2 5:0x804a:%d:1 5:0x8030:0:2\n' "$c" "$d" "$m" > "$W/drives/rg_c${c}_d${d}_m${m}.drive"
  done
  printf '\n\n0\n5:0x804c:0xff:1\n' > "$W/drives/rg_time.drive"
  printf '\n\n0\n\n' > "$W/drives/rg_none.drive"
  echo "msx_local_cmd: source {$H/load.tcl}; rgr_chain {$W} all {$W/all.done}"
  [ $bad -eq 0 ] && echo "builds: PASS" || echo "builds: FAIL"
  exit $bad
  ;;
check)
  [ $# -ge 1 ] || usage
  B="$(cd "$1" && pwd -P)" || exit 2
  shift
  cd "$REPO" || exit 2
  O="$W/O"; bad=0
  fams="$*"
  [ -n "$fams" ] || fams="flows final drives range display sound"
  for fam in $fams; do
  case $fam in
  flows)
    [ -d "$O/trace" ] || { echo; echo "== flows: no records in $O"; bad=1; continue; }
    step "level 1's coverage traces (C-BIOS_MSX2 4401, FS-A1FX and FS-A1GT 1400)"
    sh "$H/hz.sh" compare "$O/trace" "$W/R/trace/rc2_ext5.labels"; verdict $?
    step "the title from power-on on a fresh Gradiente Expert 2.0, against the base (4a8a61d)"
    cp "$B"/fresh/base_* "$W/fresh/" 2>/dev/null
    sh "$H/hz.sh" fresh "$W/fresh" base new; verdict $?
    step "the product's and PZ_TEST=1 flows: Brainstorm's screens, then the range's (its real 2:00, OUT OF TIME.), the title, the new game"
    for t in prod_m2 prod_tr pzt_m2 pzt_tr; do
      case $t in prod*) g=prod ;; *) g=pzt ;; esac
      python3 -I "$H/bonuscheck.py" "$O/flow" $t --result time --gen "$W/R/$g/gen" --range time > "$W/bonus_$t.txt" 2>&1; rc=$?
      grep -E 'equal|DIFFER|VBLANKs|^title at|^game tick_n|bonus check|the range:|rating at fr_rated' "$W/bonus_$t.txt" | sed "s/^/  $t: /" | cut -c1-200
      verdict $rc
    done
    step "the restore and the new game against a fresh start (the range timed out by rc2_fr_timeout)"
    for m in m2 tr; do
      python3 -I "$H/restorecheck.py" "$O/flow" after_$m fresh_$m --known --range > "$W/restore_$m.txt" 2>&1; rc=$?
      grep -E 'PASS|FAIL' "$W/restore_$m.txt" | sed "s/^/  $m: /" | cut -c1-160
      verdict $rc
    done
    step "the turbo R's HUD blank at the switch to the Z80 (6 frames at the base)"
    python3 -I "$H/fixblank.py" "$O/flow/blank_tr_blank.txt" | tail -1
    step "the turbo R: writes to 4000h-7FFFh from front_bonus' entry to the new game's tick 100"
    tail -1 "$O/np/wp_tr_wp.txt" | cut -c1-200
    tail -1 "$O/np/wp_tr_wp.txt" | grep -q ': 0 writes'; verdict $?
    step "the title after the bonus flows (exact records) against the base's title after Brainstorm"
    for m in ex f1 tr; do
      for f in "$B"/O/np/tx_${m}_*; do cp "$f" "$O/np/b$(basename "$f")"; done
      python3 -I "$H/titlecmp.py" "$O/np" btx_$m tx_$m > "$W/title_$m.txt" 2>&1
      grep -E "picture|palette|registers" "$W/title_$m.txt" | head -4 | sed "s/^/  $m: /"
      python3 -I "$H/titlecmp2.py" "$O/np" btx_$m tx_$m --unheard > "$W/title2_$m.txt" 2>&1; rc=$?
      grep -E 'common ticks|titlecmp2' "$W/title2_$m.txt" | sed "s/^/  $m: /"
      p=$(grep -c -E "picture.*: identical|palette: identical|registers: identical" "$W/title_$m.txt")
      [ "$rc" -eq 0 ] && [ "$p" -ge 3 ]; verdict $?
    done
    step "the 2 MiB product (ROM_2M=1) through both bonus stages, the title, the new game"
    python3 -I "$H/bonuscheck.py" "$O/np" p2m_ex --result time --gen "$W/X/p2m/gen" --range time > "$W/bonus_p2m_ex.txt" 2>&1; rc=$?
    grep -E 'equal|DIFFER|VBLANKs|^title at|^game tick_n|bonus check|the range:' "$W/bonus_p2m_ex.txt" | sed "s/^/  /" | cut -c1-200
    verdict $rc
    step "the product from the keyboard (row 8, no EXTJOY): level 1 ended, Brainstorm solved, the range's 25 shots, the result, the title"
    for m in ex tr; do
      t=kb_$m; K="$O/kb"
      [ -f "$K/${t}_bonus.txt" ] || { echo "  $t: no record"; bad=1; continue; }
      r1=$(python3 -I tools/puzlcmp.py --skip joy,last_joy,timer_min,timer_sec,score build/emu/pz_solve1_ram.jsonl "$K/${t}_pz.txt" 2>&1); c1=$?
      r2=$(python3 -I tools/frngcmp.py --skip joy,timer_min,timer_sec,score build/emu/fr_armed_ram.jsonl "$K/${t}_fr.txt" 2>&1); c2=$?
      python3 -I "$H/bonuscheck.py" "$K" $t --result ok --no-game --gen "$W/R/prod/gen" --range 25,0,1 > "$W/bonus_$t.txt" 2>&1; c3=$?
      for f in "$B"/O/np/tx_${m}_*; do cp "$f" "$K/b$(basename "$f" | sed "s/^tx_${m}_/kb_${m}_/")"; done
      python3 -I "$H/titlecmp.py" "$K" b$t $t > "$W/title_$t.txt" 2>&1
      python3 -I "$H/titlecmp2.py" "$K" b$t $t --unheard > "$W/title2_$t.txt" 2>&1; c4=$?
      p=$(grep -c -E "picture.*: identical|palette: identical|registers: identical" "$W/title_$t.txt")
      echo "  $t: Brainstorm $(echo "$r1" | grep -E 'frames compared' | head -1) | $(echo "$r1" | grep '^result' | head -1)"
      echo "  $t: the range $(echo "$r2" | grep -E 'frames compared' | head -1) | $(echo "$r2" | grep '^result' | head -1)"
      grep -E 'equal|DIFFER|bonus check|the range:|rating at fr_rated|^game tick_n|keys' "$W/bonus_$t.txt" | sed "s/^/  $t: /" | cut -c1-200
      grep -E 'picture|palette|registers' "$W/title_$t.txt" | head -3 | sed "s/^/  $t: /"
      grep -E 'common ticks|titlecmp2' "$W/title2_$t.txt" | sed "s/^/  $t: /"
      [ $c1 -eq 0 ] && [ $c2 -eq 0 ] && [ $c3 -eq 0 ] && [ $c4 -eq 0 ] && [ "$p" -ge 3 ]; verdict $?
    done
    ;;
  final)
    [ -f "$O/np/solved_m2_bonus.txt" ] || { echo; echo "== final: no records in $O/np"; bad=1; continue; }
    step "the final checks' flows through the range (docs/HARNESS.md 5.17 a, d, e, g)"
    for t in solved_m2 solved_tr; do
      r=$(python3 -I tools/puzlcmp.py build/emu/pz_solve1_ram.jsonl "$O/np/${t}_pz.txt" 2>&1); c1=$?
      python3 -I "$H/bonuscheck.py" "$O/np" $t --result ok --gen "$W/R/pz1/gen" --range time > "$W/bonus_$t.txt" 2>&1; c2=$?
      echo "  $t: $(echo "$r" | grep -E 'frames compared' | head -1); $(grep -E 'bonus check|the range:' "$W/bonus_$t.txt" | tr '\n' ' ')"
      [ $c1 -eq 0 ] && [ $c2 -eq 0 ]; verdict $?
    done
    t=solved_cand_ex
    r=$(python3 -I tools/puzlcmp.py --skip joy,last_joy,timer_min,timer_sec build/emu/pz_solve1_ram.jsonl "$O/np/${t}_pz.txt" 2>&1); c1=$?
    python3 -I "$H/bonuscheck.py" "$O/np" $t --tag 4 --result ok --gen "$W/X/cand/gen" --range time > "$W/bonus_$t.txt" 2>&1; c2=$?
    echo "  $t: $(echo "$r" | grep -E 'frames compared' | head -1); $(grep -E 'bonus check|the range:' "$W/bonus_$t.txt" | tr '\n' ' ')"
    [ $c1 -eq 0 ] && [ $c2 -eq 0 ]; verdict $?
    t=fire_ex
    python3 -I "$H/partialcheck.py" "$O/np/${t}_intro60.bin" txt_bs_intro --tag 4 > "$W/partial_$t.txt" 2>&1; c1=$?
    python3 -I "$H/partialcheck.py" "$O/np/${t}_result60.bin" txt_bs_fail --tag 4 >> "$W/partial_$t.txt" 2>&1; c2=$?
    grep -E 'the title at|the new game' "$O/np/${t}_fire.txt" | sed "s/^/  $t: /" | cut -c1-200
    tail -2 "$W/partial_$t.txt" | sed "s/^/  $t: /" | cut -c1-160
    grep -q 'the new game: .*lost: mp 0 atr 0 rd 0 fb 0' "$O/np/${t}_fire.txt"; c3=$?
    [ $c1 -eq 0 ] && [ $c2 -eq 0 ] && [ $c3 -eq 0 ]; verdict $?
    t=two_m2
    r1=$(python3 -I tools/puzlcmp.py build/emu/pz_fail_ram.jsonl "$O/np/${t}_pz1.txt" 2>&1); c1=$?
    r2=$(python3 -I tools/puzlcmp.py --skip score build/emu/pz_solve1_ram.jsonl "$O/np/${t}_pz2.txt" 2>&1); c2=$?
    python3 -I "$H/bonuscheck.py" "$O/np" $t --result ok --gen "$W/R/pz1/gen" --range time > "$W/bonus_$t.txt" 2>&1; c3=$?
    echo "  $t: $(echo "$r1" | grep -E 'frames compared' | head -1); $(echo "$r2" | grep -E 'frames compared' | head -1); $(grep -E 'bonus check|the range:' "$W/bonus_$t.txt" | tr '\n' ' ')"
    [ $c1 -eq 0 ] && [ $c2 -eq 0 ] && [ $c3 -eq 0 ]; verdict $?
    t=two_title_ex
    r1=$(python3 -I tools/puzlcmp.py --skip joy,last_joy,timer_min,timer_sec build/emu/pz_fail_ram.jsonl "$O/np/${t}_pz1.txt" 2>&1); c1=$?
    r2=$(python3 -I tools/puzlcmp.py --skip joy,last_joy,timer_min,timer_sec,score build/emu/pz_solve1_ram.jsonl "$O/np/${t}_pz2.txt" 2>&1); c2=$?
    python3 -I "$H/bonuscheck.py" "$O/np" $t --tag 4 --result ok --gen "$W/X/cand/gen" --range time > "$W/bonus_$t.txt" 2>&1; c3=$?
    echo "  $t: $(echo "$r1" | grep -E 'frames compared' | head -1); $(echo "$r2" | grep -E 'frames compared' | head -1); $(grep -E 'bonus check|the range:' "$W/bonus_$t.txt" | tr '\n' ' ')"
    [ $c1 -eq 0 ] && [ $c2 -eq 0 ] && [ $c3 -eq 0 ]; verdict $?
    t=ftflow_fx
    cat "$O/flow/$t.txt" 2>/dev/null | cut -c1-240 | sed "s/^/  /"
    grep -q 'cartridge 0 {}' "$O/flow/$t.txt" 2>/dev/null; verdict $?
    ;;
  drives)
    [ -d "$O/st/solve1_m2" ] || { echo; echo "== drives: no records in $O"; bad=1; continue; }
    step "Brainstorm's 20 traces, stills and records (check_all.sh) against the base's"
    sh "$H/check_all.sh" "$O" m2 tr fx eu > "$W/check_all.log" 2>&1
    python3 -I "$H/cmpcheck.py" "$B/check_all.log" "$W/check_all.log" "$O"; verdict $?
    step "the display guard and the VRAM speed (Brainstorm's solve1)"
    grep -H -E '^(reg|pal|cmd|cpu|vbl|tear) ' "$O"/flow/guard_*.txt | sed "s|$O/flow/||" | tr '\n' ' '; echo
    echo "  base: $(grep -H -E '^(cmd|tear) ' "$B"/O/flow/guard_*.txt | sed "s|$B/O/flow/||" | tr '\n' ' ')"
    g=$(grep -h -E '^(reg|pal|cpu|vbl) ' "$O"/flow/guard_*.txt | grep -c -v ' 0$')
    f=$(grep -h 'too fast VRAM accesses: 0 ' "$O"/flow/fast_*.txt | wc -l | tr -d ' ')
    grep -h 'too fast' "$O"/flow/fast_*.txt
    [ "$g" -eq 0 ] && [ "$f" -eq 2 ]; verdict $?
    step "the HUD during Brainstorm (solve1_m2) against the base's snapshots"
    python3 -I "$H/hudcheck.py" "$O/st/solve1_m2" "$B/O/st/solve1_m2" | tail -3; verdict $?
    ;;
  range)
    [ -d "$O/rg" ] && ls "$O"/rg/*_rg.txt >/dev/null 2>&1 || { echo; echo "== range: no records in $O/rg"; bad=1; continue; }
    step "the range: its screens (PZ_TEST=2 and the product's flow), the ratings, the new game"
    n=0; nb=0
    for f in "$O"/rg/*_rg.txt; do
      t=$(basename "$f" _rg.txt)
      case $t in
        l1*) continue ;;
        tag_*) tg="--tag 4" ;;
        *) tg="" ;;
      esac
      case $t in
        real_*) ex="--time" ;;
        *_time_*|*_time) ex="--time" ;;
        *) c=$(echo "$t" | sed -E 's/^[a-z0-9]+_c([0-9]+)_d([0-9]+)_m([0-9]+)_.*/\1,\2,\3/'); ex="--counts $c" ;;
      esac
      python3 -I "$H/rgcheck.py" "$O/rg" "$t" $ex $tg > "$O/rg/${t}_check.txt" 2>&1; rc=$?
      n=$((n + 1)); [ $rc -eq 0 ] || { nb=$((nb + 1)); echo "  $t: FAIL"; grep -E 'DIFFER|expected|not|no ' "$O/rg/${t}_check.txt" | head -5; }
    done
    echo "  $n record(s), $nb failing"
    [ "$nb" -eq 0 ] && [ "$n" -ge 41 ]; verdict $?
    echo "  the real timer (PZ_TEST=2 without a script): the passes to the time out, 50 a second"
    grep -h -E '^stage:' "$O"/rg/real_time_*_rg.txt | sed 's/^/    /'
    grep -h -E '^stage:' "$O"/rg/real_time_*_rg.txt | grep -c 'passes 6050)' | grep -q '^3$'; verdict $?
    step "level 1 traced after the range's result and the new game (SHARP again)"
    r1=0
    for t in "l1cov1_m2 trace_cov1_ram.jsonl 4401" "l1cov0_fx trace_cov0_ram.jsonl 1400" "l1cov0_tr trace_cov0_ram.jsonl 1400"; do
      set -- $t
      out=$(python3 -I tools/tracecmp.py --ram "build/emu/$2" "$O/rg/${1}_l1.txt" --labels "$W/X/fr2t/rc2.labels" 2>&1 | tail -1)
      rows=$(grep -c . "$O/rg/${1}_l1.txt" 2>/dev/null)
      echo "  $1: $rows rows; $out"
      echo "$out" | grep -q ": 0 differ" && [ "$rows" = "$3" ] || r1=1
      grep -E '^(new game|level-1 trace done)' "$O/rg/${1}_rg.txt" | sed "s/^/    /"
    done
    verdict $r1
    step "the range traced after a played level 1 and Brainstorm (fr_mixed, --skip score)"
    for m in m2 tr; do
      r=$(python3 -I tools/frngcmp.py --skip score build/emu/fr_mixed_ram.jsonl "$O/lt/tarm_$m.txt" 2>&1); rc=$?
      echo "$r" | head -3 | sed "s/^/  tarm_$m: /" | cut -c1-200
      verdict $rc
    done
    step "the wanted state at every pass's start against the bench (rgview.py want)"
    r1=0
    for dv in armed mixed dummy edge fuzz quirk4 hold armed2; do
      g="$W/X/fr2/gen"; [ $dv = armed2 ] && g="$W/V/fr2v2/gen"
      python3 -I "$H/rgview.py" want "$O/lt/want_${dv}_want.txt" --ref "build/emu/fr_${dv}_ram.jsonl" --gen "$g" > "$W/want_$dv.txt" 2>&1 || r1=1
      python3 -I tools/frngcmp.py "build/emu/fr_${dv}_ram.jsonl" "$O/lt/want_$dv.txt" > "$W/want_${dv}_trace.txt" 2>&1 || r1=1
      echo "  $(tail -1 "$W/want_$dv.txt" | cut -c1-170); trace: $(grep -E 'frames compared' "$W/want_${dv}_trace.txt" | cut -c1-80)"
    done
    verdict $r1
    ;;
  display)
    [ -d "$W/V/O" ] || { echo; echo "== display: no records in $W/V/O"; bad=1; continue; }
    step "the range's display, camera, HUD probe, guard, VRAM speed, pass rate, restore (rgview.sh check)"
    sh "$H/rgview.sh" check "$W/V" > "$W/display.log" 2>&1; rc=$?
    grep -E '^== |-> |rgview:' "$W/display.log" | sed 's/^/  /' | cut -c1-200
    verdict $rc
    ;;
  sound)
    [ -d "$O/snd" ] || { echo; echo "== sound: no records in $O/snd"; bad=1; continue; }
    PY=~/.venvs/msxports/bin/python
    step "the range's sound: FRM's registers per tick against the streams (frsnd/frregcmp.py), 20 logs"
    n=$(ls "$O"/snd/*_fr.txt 2>/dev/null | wc -l | tr -d ' ')
    $PY -I "$H/frsnd/frregcmp.py" "$REPO" "$O"/snd/*_fr.txt > "$W/frregcmp.log" 2>&1; rc=$?
    sed 's/^/  /' "$W/frregcmp.log" | cut -c1-200
    echo "  $n logs"
    [ $rc -eq 0 ] && [ "$n" -ge 20 ]; verdict $?
    step "the sound jobs' traces still 0 differ (fr_mixed)"
    r1=0
    for f in "$O"/snd/d_*_trace.txt; do
      r=$(python3 -I tools/frngcmp.py build/emu/fr_mixed_ram.jsonl "$f" 2>&1) || r1=1
      echo "  $(basename "$f"): $(echo "$r" | grep -E 'frames compared' | cut -c1-90)"
    done
    verdict $r1
    ;;
  *) echo "unknown family $fam"; bad=1 ;;
  esac
  done
  echo
  [ $bad -eq 0 ] && echo "regress: PASS" || echo "regress: FAIL"
  exit $bad
  ;;
*)
  usage ;;
esac
