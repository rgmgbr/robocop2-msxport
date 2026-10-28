#!/bin/sh
# variants.sh OUT: the night review's option sets (2026-10-27), built with the repository as it is
# through build.sh, one folder each (OUT/NAME/rc2.rom, the log in OUT/NAME.out); prints NAME OK or
# NAME FAIL with the build's first error. At 14bc5ef every set built except DEMO_ACTORS=2/5 and
# DEMO_HUD=1, which overflow the fixed area at 52149b0 too (docs/HARNESS.md). The last seven (l2_*,
# level 2's step 7) are the LV_TEST=2 sets: 48 in all.
if [ $# -lt 1 ]; then sed -n 2,6p "$0" >&2; exit 2; fi
H="$(cd "$(dirname "$0")" && pwd -P)"
OUT="$1"
v() { n="$1"; shift; if sh "$H/build.sh" "$OUT/$n/rc2.rom" "$@" > "$OUT/$n.out" 2>&1; then echo "$n OK"; else echo "$n FAIL: $(grep -i 'error' "$OUT/$n/rc2.log" 2>/dev/null | head -1 | sed 's/.*msxports\///')"; fi; }
mkdir -p "$OUT"
v cad4 CAD_MAX=4
v cand_t2 TAG=2
v cand_t2b PZ_TEST=1 TAG=2
v demoact DEMO_ACTORS=2
v demoact5 DEMO_ACTORS=5
v demohud DEMO_HUD=1
v diag1 DIAG=1
v diag2 DIAG=2
v ec2 ENEMY_CAP=2
v ext EXTJOY=1
v forcescc FORCE_SCC=1
v god GOD=1 JOY=70:40:r,120:5:ru
v hz30 TICK_HZ=30
v joy JOY=70:40:r,120:5:ru
v lock EXTJOY=1 LOCKSTEP=24
v lock14 EXTJOY=1 LOCKSTEP=14
v lvl2only PZ_LEVEL=2
v nofm NO_FM=1
v noscc NO_SCC=1
v nosccint NO_SCC_INT=1
v p_prod
v p_pz PZ_TEST=1
v p_pz2 PZ_LEVEL=2 PZ_TEST=1
v p_pz2m PZ_TEST=1 ROM_2M=1 TAG=2
v p_pz30 PZ_TEST=1 TICK_HZ=30
v p_pzdiag DIAG=1 PZ_TEST=1
v p_pzdiag2 DIAG=2 PZ_TEST=1
v p_pzjoy PZ_TEST=1 JOY=70:40:r,120:5:ru
v p_pzlock EXTJOY=1 LOCKSTEP=24 PZ_TEST=1
v p_pzping PZ_TEST=1 R800PING=1
v p_pzsplit PZ_TEST=1 SPLITDIAG=1
v p_pzsplitping PZ_TEST=1 R800PING=1 SPLITDIAG=1 TAG=12
v p_pzx EXTJOY=1 PZ_TEST=1
v p_pzx2 EXTJOY=1 PZ_LEVEL=2 PZ_TEST=1
v p_splitping R800PING=1 SPLITDIAG=1
v p_tag99 PZ_TEST=1 TAG=99
v ping R800PING=1
v rom2m ROM_2M=1
v splitdiag SPLITDIAG=1
v trace DAMAGE_X=1 ENEMY_CAP=0 EXTJOY=1
v v9938 FORCE_V9938=1
v l2_test LV_TEST=2
v l2_trace DAMAGE_X=1 ENEMY_CAP=0 EXTJOY=1 LV_TEST=2
v l2_carry LV_CARRY=0:0:1:3 LV_TEST=2
v l2_lock EXTJOY=1 LOCKSTEP=24 LV_TEST=2
v l2_tag LV_TEST=2 TAG=5
v l2_2m LV_TEST=2 ROM_2M=1
v l2_diag DIAG=1 LV_TEST=2
