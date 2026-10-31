#!/bin/sh
# l2neg.sh REPO BASE W OUT: negative controls of level 2's gate (l2base.sh check's verdicts, docs/HARNESS.md
# 5.21) on copies of W's records (a run that passes against BASE) in OUT: each copy, mutated once, must
# FAIL its verdict; the same copy unmutated must PASS. REPO: a tree with the gate's tools and build data
# (W's builds' labels are read from W). Prints one line per control and "neg: N as expected, M wrong";
# the venv's Python (PY) runs fieldcheck.py and msxframe.py.
set -u
REPO="$1"; B="$2"; W="$3"; OUT="$4"
PY="${PY:-$HOME/.venvs/msxports/bin/python}"
rm -rf "$OUT"; mkdir -p "$OUT"
cd "$REPO" || exit 2
ok=0; bad=0
res() {   # res NAME WANT(PASS|FAIL) RC
  got=PASS; [ "$3" -eq 0 ] || got=FAIL
  if [ "$got" = "$2" ]; then ok=$((ok + 1)); echo "  $1: $got (as expected)"; else bad=$((bad + 1)); echo "  $1: $got (WRONG: $2 expected)"; fi
}
flip() {  # flip FILE OFFSET: one byte xor FFh
  python3 -I -c 'import sys; p=sys.argv[1]; o=int(sys.argv[2],0); b=bytearray(open(p,"rb").read()); b[o]^=0xFF; open(p,"wb").write(b)' "$1" "$2"
}
# 1. level 1's death trace: one row's bytes changed
cp "$W/l1/trace/die.txt" "$OUT/die.txt"
python3 -I tools/tracecmp.py --ram --labels "$W/R/trace/rc2_ext5.labels" build/emu/trace_die_ram.jsonl "$OUT/die.txt" 2>&1 | tail -1 | grep -q ": 0 differ"; res "trace die unchanged" PASS $?
python3 -I - "$OUT/die.txt" <<'EOF'
import sys
p = sys.argv[1]; rows = open(p).read().split("\n")
r = rows[300]; rows[300] = r[:8] + ("1" if r[8] != "1" else "2") + r[9:]    # (camera_x, 0B04h)
open(p, "w").write("\n".join(rows))
EOF
python3 -I tools/tracecmp.py --ram --labels "$W/R/trace/rc2_ext5.labels" build/emu/trace_die_ram.jsonl "$OUT/die.txt" 2>&1 | tail -1 | grep -q ": 0 differ"; res "trace die, row 300\x27s camera_x changed" FAIL $?
# 2-3. the start check: a tear, a CPU write
for k in "tear" "cpu"; do
  sed "s/ $k 0/ $k 1/" "$W/l1/start/st_m2.txt" > "$OUT/st_$k.txt"
  python3 -I tools/bstest/l2base.py start "$OUT/st_$k.txt" "$B/l1/start/st_m2.txt" > /dev/null 2>&1; res "start m2, $k 0 -> 1" FAIL $?
done
python3 -I tools/bstest/l2base.py start "$W/l1/start/st_m2.txt" "$B/l1/start/st_m2.txt" > /dev/null 2>&1; res "start m2 unchanged" PASS $?
# 4. the field check: one record's page zeroed (after its 64 registers and 32 palette bytes)
cp -R "$W/l1/field/430_m2" "$OUT/430_m2"
"$PY" -I tools/bstest/fieldcheck.py "$OUT/430_m2" build/msx/level1 "$OUT/430_m2.png" > "$OUT/430_m2.check.txt" 2>&1
python3 -I tools/bstest/l2base.py field "$OUT/430_m2.check.txt" "$B/l1/field/430_m2.check.txt" > /dev/null 2>&1; res "field 430_m2 unchanged" PASS $?
python3 -I -c 'import sys; p=sys.argv[1]; b=bytearray(open(p,"rb").read()); b[96:96+0x8000]=bytes(0x8000); open(p,"wb").write(b)' "$OUT/430_m2/j001_f0030.bin"
"$PY" -I tools/bstest/fieldcheck.py "$OUT/430_m2" build/msx/level1 "$OUT/430_m2.png" > "$OUT/430_m2.check.txt" 2>&1
python3 -I tools/bstest/l2base.py field "$OUT/430_m2.check.txt" "$B/l1/field/430_m2.check.txt" > "$OUT/field.txt" 2>&1; rc=$?
res "field 430_m2, the page of picture 30 zeroed (fieldcheck again: $(grep -o '[0-9]* differ, [0-9]* pixels' "$OUT/field.txt" | head -1))" FAIL $rc
# 5. the stills: 16 KiB of one snapshot's VRAM zeroed (msxframe again)
mkdir -p "$OUT/still"
for m in m2 fx; do cp -R "$W/l1/still/$m" "$OUT/still/$m"; done
cp "$W"/l1/still/*.png "$W"/l1/still/*.txt "$OUT/still/" 2>/dev/null
python3 -I tools/bstest/l2base.py stills "$OUT/still" "$B/l1/still" > /dev/null 2>&1; res "stills unchanged" PASS $?
python3 -I -c 'import sys; p=sys.argv[1]; b=bytearray(open(p,"rb").read()); b[0:65536]=bytes(65536); open(p,"wb").write(b)' "$OUT/still/m2/g0430/vram.bin"
"$PY" -I tools/msxframe.py "$OUT/still/m2/g0430" build/msx/level1 build/msx/hud "$OUT/still/m2_g0430.png" > "$OUT/still/m2_g0430.txt" 2>&1
python3 -I tools/bstest/l2base.py stills "$OUT/still" "$B/l1/still" > /dev/null 2>&1; res "stills, m2 g0430's play pages 0-1 zeroed" FAIL $?
# 6. LOCKSTEP: one SAT byte of list 10
python3 -I tools/dispcmp.py "$B/l1/lock/disp_m2.txt" "$W/l1/lock/disp_m2.txt" > /dev/null 2>&1; res "LOCKSTEP m2 unchanged" PASS $?
python3 -I - "$W/l1/lock/disp_m2.txt" "$OUT/disp_m2.txt" <<'EOF'
import sys
rows = open(sys.argv[1]).read().split("\n")
f = rows[10].split(" ")
f[4] = ("1" if f[4][0] != "1" else "2") + f[4][1:]
rows[10] = " ".join(f)
open(sys.argv[2], "w").write("\n".join(rows))
EOF
python3 -I tools/dispcmp.py "$B/l1/lock/disp_m2.txt" "$OUT/disp_m2.txt" > /dev/null 2>&1; res "LOCKSTEP m2, list 10's SAT byte changed" FAIL $?
# 7-8. the effects: a start one frame late, a sound tick's SCC state changed
python3 -I tools/bstest/fxcmp.py "$B/l1/fx/pw_scc_sn.txt" "$W/l1/fx/pw_scc_sn.txt" > /dev/null 2>&1; res "effects (scc build) unchanged" PASS $?
python3 -I - "$W/l1/fx/pw_scc_sn.txt" "$OUT/late.txt" "$OUT/tick.txt" <<'EOF'
import sys
rows = open(sys.argv[1]).read().split("\n")
s = next(i for i, r in enumerate(rows) if r.startswith("S ") and i > 2000)
f = rows[s].split(" "); f[1] = str(int(f[1]) + 30); late = list(rows); late[s] = " ".join(f)
open(sys.argv[2], "w").write("\n".join(late))
f = rows[s].split(" "); f[2] = str((int(f[2]) % 40) + 1); tick = list(rows); tick[s] = " ".join(f)
open(sys.argv[3], "w").write("\n".join(tick))
EOF
python3 -I tools/bstest/fxcmp.py "$B/l1/fx/pw_scc_sn.txt" "$OUT/late.txt" > /dev/null 2>&1; res "effects, a start 30 VBLANKs late" FAIL $?
python3 -I tools/bstest/fxcmp.py "$B/l1/fx/pw_scc_sn.txt" "$OUT/tick.txt" > /dev/null 2>&1; res "effects, another effect at a start" FAIL $?
# 9-11. the title from power-on (exact record): unchanged, a title VRAM byte, a game RAM byte (D100h)
mkdir -p "$OUT/fresh"
cp "$W"/fresh/xnew_* "$B"/fresh/xbase_* "$OUT/fresh/"
python3 -I tools/bstest/l2base.py fresh "$OUT/fresh" xbase xnew "$B/R/prod/rc2.labels" "$W/R/prod/rc2.labels" > /dev/null 2>&1; res "title from power-on unchanged" PASS $?
flip "$OUT/fresh/xnew_title_vram.bin" 0x5000
python3 -I tools/bstest/l2base.py fresh "$OUT/fresh" xbase xnew "$B/R/prod/rc2.labels" "$W/R/prod/rc2.labels" > /dev/null 2>&1; res "title from power-on, a title VRAM byte" FAIL $?
cp "$W/fresh/xnew_title_vram.bin" "$OUT/fresh/"
flip "$OUT/fresh/xnew_game2_ram.bin" 0x100
python3 -I tools/bstest/l2base.py fresh "$OUT/fresh" xbase xnew "$B/R/prod/rc2.labels" "$W/R/prod/rc2.labels" > /dev/null 2>&1; res "title from power-on, the game's RAM D100h" FAIL $?
# 12. the range traced after a played level 1 and Brainstorm: one row's byte
cp "$W/O/lt/tarm_m2.txt" "$OUT/tarm_m2.txt"
python3 -I tools/frngcmp.py --skip score build/emu/fr_mixed_ram.jsonl "$OUT/tarm_m2.txt" > /dev/null 2>&1; res "range tarm_m2 unchanged" PASS $?
python3 -I - "$OUT/tarm_m2.txt" <<'EOF'
import sys
p = sys.argv[1]; rows = open(p).read().split("\n")
i = 40; r = rows[i]; rows[i] = r[:10] + ("1" if r[10] != "1" else "2") + r[11:]
open(p, "w").write("\n".join(rows))
EOF
python3 -I tools/frngcmp.py --skip score build/emu/fr_mixed_ram.jsonl "$OUT/tarm_m2.txt" > /dev/null 2>&1; res "range tarm_m2, row 40 changed" FAIL $?
echo "neg: $ok as expected, $bad wrong"
