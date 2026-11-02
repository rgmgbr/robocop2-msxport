#!/bin/sh
# usage: build.sh OUT.rom [NAME=VALUE ...]
# Builds the ROM with tools/mkrom.py from the repository's msx/ into OUT.rom (never in build/msx or the
# folder it resolves to: the user picks ROMs there; docs/HARNESS.md), from build/msx/level1, and checks
# the build: mkrom's exit status, no "error" in its output, a ROM written by this build (the old one is
# removed first), and z80asm's messages in OUT.labels (mkrom keeps z80asm's stderr there): only the 12
# known "expression fully enclosed in parenthesis" warnings may appear. Writes OUT.log (the ROM's
# name with .log; the label file is the ROM's name with .labels, gen/ lands next to it).
# Exit 0 only when every check passed.
# Environment:
#   LEVEL=PATH         another conversion folder's level (default build/msx/level1; a relative
#                      path is taken from the repository root)
#   SRC=DIR            builds another source tree's msx/ with its tools/mkrom.py: a git worktree
#                      of an older commit whose build/ links to this checkout's (docs/HARNESS.md)
#   KNOWN_WARNINGS=N   the count of known z80asm warnings (default 12)
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
if [ $# -lt 1 ]; then sed -n 2,15p "$0" >&2; exit 2; fi
OUT="$1"; shift
case "$OUT" in
  *.rom|*.ROM) ;;
  *) echo "build.sh: OUT must end in .rom" >&2; exit 2 ;;
esac
# (absolute: mkrom runs in the source tree; and a relative OUT must not slip past the refusal.
# The nearest existing folder is resolved and the rest appended, so that nothing is created in
# build/msx before the check; checked again once the folders exist)
abspath() {
  d="$(dirname "$1")"; rest="$(basename "$1")"
  case "$d" in /*) ;; *) d="$(pwd -P)/$d" ;; esac
  while [ ! -d "$d" ]; do rest="$(basename "$d")/$rest"; d="$(dirname "$d")"; done
  echo "$(cd "$d" && pwd -P)/$rest"
}
refuse() {
  case "$1" in
    "$ROOT"/build/msx/*) echo "build.sh: OUT must not be in build/msx (the user picks ROMs there)" >&2; exit 2 ;;
  esac
  # (also the folder build/msx resolves to: a tree whose build/ or build/msx links to another
  # checkout's, as a git worktree's may, would write into that checkout's build/msx; and any other
  # spelling of it, build/MSX on a case-insensitive volume: each existing folder of OUT is compared
  # with build/msx by inode)
  if [ -d "$ROOT/build/msx" ]; then
    d="$(dirname "$1")"
    while :; do
      if [ "$d" -ef "$ROOT/build/msx" ]; then
        echo "build.sh: OUT must not be in build/msx (the user picks ROMs there; here $d)" >&2; exit 2
      fi
      case "$d" in /|.) break ;; esac
      d="$(dirname "$d")"
    done
  fi
}
OUT="$(abspath "$OUT")"
refuse "$OUT"
mkdir -p "$(dirname "$OUT")" || exit 2
OUT="$(cd "$(dirname "$OUT")" && pwd -P)/$(basename "$OUT")"
refuse "$OUT"
LEVEL="${LEVEL:-build/msx/level1}"
case "$LEVEL" in /*) ;; *) LEVEL="$ROOT/$LEVEL" ;; esac
SRC="${SRC:-$ROOT}"
KNOWN="${KNOWN_WARNINGS:-12}"
LAB="${OUT%.*}.labels"
LOG="${OUT%.*}.log"
rm -f "$OUT" "$LAB"
cd "$SRC" || exit 2
if [ ! -f tools/mkrom.py ]; then echo "build.sh: no tools/mkrom.py in $SRC" >&2; exit 2; fi
python3 -I tools/mkrom.py "$LEVEL" "$OUT" "$@" > "$LOG" 2>&1
rc=$?
bad=0
if [ $rc -ne 0 ]; then echo "FAIL: mkrom exit $rc"; bad=1; fi
if grep -i -q "error" "$LOG"; then echo "FAIL: error in the build log:"; grep -i "error" "$LOG" | head -5; bad=1; fi
if [ ! -f "$OUT" ]; then echo "FAIL: no new ROM at $OUT (the old one was removed before the build)"; bad=1; fi
if [ -f "$LAB" ]; then
  nw=$(grep -c "warning" "$LAB")
  other=$(grep -v "equ \\$" "$LAB" | grep -v "warning: expression fully enclosed in parenthesis" | grep -c .)
  known=$(grep -c "warning: expression fully enclosed in parenthesis" "$LAB")
  if [ "$other" -ne 0 ]; then echo "FAIL: z80asm messages other than the known warnings:"; grep -v "equ \\$" "$LAB" | grep -v "warning: expression fully enclosed in parenthesis" | head -10; bad=1; fi
  if [ "$known" -ne "$KNOWN" ]; then echo "FAIL: $known 'fully enclosed' warnings ($KNOWN known)"; bad=1; fi
  echo "z80asm: $nw warnings ($known known), $other other messages"
else
  echo "FAIL: no labels file"; bad=1
fi
tail -1 "$LOG"
[ $bad -eq 0 ] && echo "build OK: $OUT ($(shasum -a 256 "$OUT" | cut -c1-16))"
exit $bad
