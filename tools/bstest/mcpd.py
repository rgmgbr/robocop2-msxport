#!/usr/bin/env python3
"""mcpd.py DIR: a private MSX-AI MCP session (the same msx_local_* tools, its own headless openMSX),
for an agent whose process's MCP target another agent holds (docs/level2/HANDOFF.md).

Spawns msx-ai-mcp (JSON-RPC over stdio), calls msx_local_boot (profile cbios, headless), then serves
DIR/req/NAME.tcl files: each one's text goes to msx_local_cmd and the reply is written to
DIR/rep/NAME.txt (tools/bstest/mx.sh writes the requests and waits for the replies). DIR/req/quit.tcl
calls msx_local_shutdown and ends the daemon. Log: DIR/mcpd.log. Run it in the background:
python3 -I tools/bstest/mcpd.py DIR; then MCPD_DIR=DIR sh tools/bstest/mx.sh NAME 'TCL'.
"""
import json
import os
import subprocess
import sys
import time

MCP = "/opt/homebrew/bin/msx-ai-mcp"


def main():
    d = os.path.abspath(sys.argv[1])
    req, rep = os.path.join(d, "req"), os.path.join(d, "rep")
    os.makedirs(req, exist_ok=True)
    os.makedirs(rep, exist_ok=True)
    log = open(os.path.join(d, "mcpd.log"), "a", buffering=1)
    err = open(os.path.join(d, "mcp_stderr.log"), "a")
    p = subprocess.Popen([MCP], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err,
                         text=True, bufsize=1)
    nid = [0]

    def call(method, params=None, notify=False):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        if not notify:
            nid[0] += 1
            msg["id"] = nid[0]
        p.stdin.write(json.dumps(msg) + "\n")
        p.stdin.flush()
        if notify:
            return None
        while True:
            line = p.stdout.readline()
            if not line:
                raise SystemExit("msx-ai-mcp closed its output")
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("id") == nid[0]:
                return r

    def tool(name, args):
        r = call("tools/call", {"name": name, "arguments": args})
        if "error" in r:
            return "ERROR " + json.dumps(r["error"])
        res = r.get("result", {})
        out = []
        for c in res.get("content", []):
            if c.get("type") == "text":
                out.append(c.get("text", ""))
        s = "\n".join(out)
        if res.get("isError"):
            s = "ISERROR " + s
        return s

    r = call("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                            "clientInfo": {"name": "mcpd", "version": "1"}})
    log.write("initialize: %s\n" % json.dumps(r.get("result", {}).get("serverInfo", {})))
    call("notifications/initialized", notify=True)
    log.write("boot: %s\n" % tool("msx_local_boot", {"profile": "cbios", "window": False})[:400])
    while True:
        names = sorted(n for n in os.listdir(req) if n.endswith(".tcl"))
        if not names:
            time.sleep(0.2)
            continue
        for n in names:
            f = os.path.join(req, n)
            try:
                tcl = open(f).read()
            except OSError:
                continue
            os.remove(f)
            base = n[:-4]
            if base == "quit":
                log.write("quit: %s\n" % tool("msx_local_shutdown", {})[:400])
                p.stdin.close()
                p.wait(timeout=30)
                return
            t0 = time.time()
            out = tool("msx_local_cmd", {"tcl": tcl})
            tmp = os.path.join(rep, base + ".tmp")
            with open(tmp, "w") as o:
                o.write(out)
            os.rename(tmp, os.path.join(rep, base + ".txt"))
            log.write("%s %s: %.1fs %d chars\n" % (time.strftime("%H:%M:%S"), base, time.time() - t0,
                                                     len(out)))


if __name__ == "__main__":
    main()
