#!/usr/bin/env python3
"""Extracts the pseudocode (or assembly) of a saved REA batch_decompile / procedure result into OUTDIR/<addr>.c"""
import json, sys, pathlib
src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
d = json.loads(src.read_text())
items = d.get("normalized_result", {}).get("items")
if items is None:
    nr = d.get("normalized_result", d)
    items = [nr]
for it in items:
    addr = it.get("address", "x")
    pc = it.get("pseudocode")
    if isinstance(pc, dict):
        txt = pc.get("text") or pc.get("pseudocode") or json.dumps(pc)[:200000]
    else:
        txt = pc if isinstance(pc, str) else json.dumps(it)[:2000]
    (out / f"{addr}.c").write_text(txt if isinstance(txt, str) else str(txt))
    print(addr, it.get("status"), len(txt) if txt else 0)
