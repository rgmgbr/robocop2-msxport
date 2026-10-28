#!/bin/zsh
# try.sh JOY TELE GFRAMES [CARRY] [GOD]: runs l2bench with a drive made from JOY/TELE, prints rows every 10 frames from $4
B=/private/tmp/claude-501/-Users-rodrigogarcia-Library-Mobile-Documents-com-apple-CloudDocs-Projects-VSCode-Projects-msxports/0d8bec81-2242-4472-bdb7-9edaf3f21500/scratchpad/space/l2/bench
cd $B
GOD=${6:---god}
python3 -I tools/drivejoy.py --joy "$1" --tele "$2" $GOD $B/drives/try.drive > /dev/null
~/.venvs/msxports/bin/python -I tools/l2bench.py game --start direct --carry ${5:-0:2:0:good} --gframes $3 --drive $B/drives/try.drive --trace $B/out/try.jsonl --trace-ram > /dev/null 2>&1
python3 -c "
import json
rows=[json.loads(l) for l in open('$B/out/try.jsonl')]
for n in range(${4:-0}, len(rows), ${7:-10}):
    r=rows[n]; print(n, r['keys'], (r['player_x'], r['player_y']), 'st', r['state'], 'cam', (r['camera_x'], r['camera_y']), 'E', r['energy'])
"
