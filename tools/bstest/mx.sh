#!/bin/sh
# mx.sh NAME 'TCL' [TIMEOUT_S]: one msx_local_cmd through a private MSX-AI MCP session (tools/bstest/
# mcpd.py DIR, running in the background); DIR from MCPD_DIR. Prints the reply (exit 1 without one).
D="${MCPD_DIR:?set MCPD_DIR to the folder of mcpd.py}"
n="$1"; t="${3:-120}"
rm -f "$D/rep/$n.txt"
printf '%s' "$2" > "$D/req/$n.tcl.tmp" && mv "$D/req/$n.tcl.tmp" "$D/req/$n.tcl"
i=0
while [ ! -f "$D/rep/$n.txt" ]; do
  sleep 0.2; i=$((i + 1))
  [ $i -gt $((t * 5)) ] && { echo "mx.sh: no reply in ${t}s"; exit 1; }
done
cat "$D/rep/$n.txt"; echo
