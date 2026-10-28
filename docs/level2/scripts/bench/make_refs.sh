#!/bin/sh
# The level-2 references: drive NAME, carry, game frames (the run stops earlier at the level's end).
# usage: make_refs.sh BENCHDIR   (writes BENCHDIR/ref/l2_<name>_ram.jsonl and .log)
B="$1"; PY="${PY:-$HOME/.venvs/msxports/bin/python}"
cd "$B" || exit 1
run() {  # name drive carry gframes
  "$PY" -I tools/l2bench.py game --start direct --carry "$3" --gframes "$4" --drive "ref/$2.drive" \
      --stop-at-end --trace "ref/$1_ram.jsonl" --trace-ram > "ref/$1.log" 2>&1
  echo "$1: $(wc -l < "ref/$1_ram.jsonl") rows; $(tail -1 "ref/$1.log")"
}
STD=10050:2:0:good
run l2_end l2_end $STD 300 &
run l2_tour l2_tour $STD 3000 &
run l2_lift l2_lift $STD 800 &
run l2_trolley l2_trolley $STD 640 &
run l2_vat l2_vat $STD 700 &
wait
run l2_cont l2_cont 0:0:1:good 300 &
run l2_over l2_over 0:0:0:good 300 &
run l2_fuzz l2_fuzz $STD 2500 &
run l2_trolley_sharp l2_trolley 10050:2:0:sharp 640 &
run l2_trolley_fair l2_trolley 10050:2:0:fair 640 &
run l2_trolley_poor l2_trolley 10050:2:0:poor 640 &
wait
