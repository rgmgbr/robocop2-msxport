"""The range's sound (docs/RANGE.md 4.3): an openMSX register log (tools/bstest/frsound.tcl: S, P, R, T,
Q, E, X and Z lines) against frm.bin's streams decoded apart (frsim.py's FExpect and Check: the
converters' decoders, PSG B for a flagged effect with an SCC, the shared noise period as the last
written; pzsim.Sched: $1822C's rule and snd_rfx's merge).

- Every T line (tn_tick's entry) holds the chips as the previous tick left them: compared with that
  tick's tune tick (from tn_left: the tune's T + 1 - tn_left) and the effect voice's model state; the
  Q line (the stage's own snd_stop) with the last tick's. R lines are the requests, consumed at the
  next T line; an S line restarts the model.
- Tick 0: the first T line after S comes after the stage's first pass (a P line before it; at most two
  at 60 Hz, where the passes' and the ticks' dividers skip different VBLANKs).
- The stage's stop (msx/frng.asm rg_end, as $10768's $FE14 right after FRNG's return): a Q line
  before fr_done, at most one T line after the stage's last pass (P) before it (none unless a pass
  overran its frame), no T line after it, and the chips silent at fr_done (the E line).
- The tune's end: when a T line holds tn_left 1 (its last tick), the Q line's counts (sound writes
  from 50 ms after it to the stop) must be 0 and its chips silent.
- The result's stop: snd_stop after fr_done (an X line: front.asm fe_text's), no T line after it,
  and at the Z line (1 s on, the result's screen) the chips silent: SCC volumes 0, PSG R8-R10 0, no
  OPLL key or rhythm key.

usage: frregcmp.py ROOT LOG [LOG ...]   (one summary line per log; exit 1 on any difference)
       frregcmp.py --selftest ROOT ROM LABELS   (logs from the Z80 simulation, and corrupted copies)"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import frsim  # noqa: E402
from frsim import pzsim  # noqa: E402


class Bus:
    def __init__(self):
        self.psg = bytearray(16)
        self.scc = bytearray(256)
        self.opll = bytearray(64)


def scc_to_z80(dbg: bytes) -> bytearray:
    """openMSX's SCC debuggable (waveforms 00h-9Fh, periods A0h-A9h, volumes AAh-AEh, enable AFh) in
    the Z80's layout (9800h on: waveforms, 80h periods, 8Ah volumes, 8Fh enable)."""
    out = bytearray(256)
    out[0x00:0x80] = dbg[0x00:0x80]
    out[0x80:0x8A] = dbg[0xA0:0xAA]
    out[0x8A:0x8F] = dbg[0xAA:0xAF]
    out[0x8F] = dbg[0xAF]
    return out


def bus_of(scc: str, psg: str, opll: str) -> Bus:
    b = Bus()
    if scc != "-":
        b.scc = scc_to_z80(bytes.fromhex(scc))
    b.psg = bytearray(bytes.fromhex(psg))
    if opll != "-":
        b.opll = bytearray(bytes.fromhex(opll))
    return b


def silent(scc: str, psg: str, opll: str) -> list[str]:
    bad = []
    if scc != "-":
        s = bytes.fromhex(scc)
        if any(s[0xAA:0xAF]) and s[0xAF] & 0x1F:
            bad.append("SCC volumes %s with channels on %02X" % (s[0xAA:0xAF].hex(), s[0xAF]))
    p = bytes.fromhex(psg)
    if any(v & 0x1F for v in p[8:11]):
        bad.append("PSG volumes %s" % p[8:11].hex())
    if opll != "-":
        o = bytes.fromhex(opll)
        keys = ["%02Xh" % r for r in range(0x20, 0x29) if o[r] & 0x10]
        if keys or o[0x0E] & 0x1F:
            bad.append("OPLL keys on %s, 0Eh %02X" % (keys, o[0x0E]))
    return bad


def compare(root: Path, lines: list[str]) -> tuple[list[str], dict]:
    ex = frsim.FExpect(root, (root / "build" / "msx" / "frm.bin").read_bytes())
    T1 = ex.T + 1
    sch = chk = None
    bad, info = [], {"ticks": 0, "starts": 0, "modes": set(), "passes_before_tick0": [], "last_left": None,
                     "ended": False, "x": False, "z": False, "e": None, "q": None, "q_ticks": None}
    prev = None
    t = 0
    passes = None
    since_p = 0
    for line in lines:
        f = line.split()
        if not f or f[0].startswith("#"):
            if f:
                bad.append("log note: %s" % line)
            continue
        k = f[0]
        if k == "S":
            if sch is None:
                sch = pzsim.Sched(ex.fx, True)
            chk = frsim.Check(ex)
            sch.restart()
            prev, passes = None, 0
            info["starts"] += 1
        elif k == "P":
            since_p = 0
            if passes is not None:
                passes += 1
        elif k == "R":
            if sch is not None:
                sch.request(int(f[1]))
        elif k == "T" and sch is not None:
            left, mode = int(f[1]), int(f[7])
            info["modes"].add("%s/%s" % (f[6], f[7]))
            sch.scc = bool(mode & frsim.MM_SCC)
            if passes is not None:
                info["passes_before_tick0"].append(passes)
                if not 1 <= passes <= 2:
                    bad.append("the tune's tick 0 after %d passes" % passes)
                passes = None
            if prev is not None:
                tune, fx, pmode = prev
                bad += chk.tick(bus_of(f[8], f[9], f[10]), pmode, tune, fx, t)
                info["ticks"] += 1
            if info["x"]:
                bad.append("a tick (T line) after the stop (X)")
            elif info["q"] is not None:
                bad.append("a tick (T line) after the stage's stop (Q)")
            since_p += 1
            t += 1
            fxs = sch.tick(t)
            prev = (T1 - left if left else None, fxs, mode)
            info["last_left"] = left
            if left == 1:
                info["ended"] = True
        elif k == "Q":
            if info["q"] is not None or info["e"] is not None:
                bad.append("a second stop before fr_done, or one after it (Q)")
                continue
            info["q"], info["q_ticks"] = f[1:4], since_p
            if since_p > 1:
                bad.append("the stage's stop %d ticks after its last pass" % since_p)
            if prev is not None and chk is not None:
                tune, fx, pmode = prev
                bad += chk.tick(bus_of(f[4], f[5], f[6]), pmode, tune, fx, t)
            if info["ended"]:
                if f[1:4] not in (["0", "0", "0"], ["-1", "-1", "-1"]):
                    bad.append("sound writes after the tune's end, before the stage's stop: PSG %s, OPLL %s, SCC %s"
                               % tuple(f[1:4]))
                bad += ["at the stage's stop after the tune's end: " + b for b in silent(f[4], f[5], f[6])]
        elif k == "E":
            info["e"] = f[1:4]
            if info["q"] is None:
                bad.append("no stop at the stage's end (Q) before fr_done")
            bad += ["at fr_done after the stage's stop: " + b for b in silent(f[4], f[5], f[6])]
        elif k == "X":
            info["x"] = True
        elif k == "Z":
            info["z"] = True
            if not info["x"]:
                bad.append("no snd_stop after fr_done before the Z line")
            if f[1] != "0":
                bad.append("%s T lines after the stop" % f[1])
            bad += ["after the stop: " + b for b in silent(f[2], f[3], f[4])]
    if not info["starts"]:
        bad.append("no tune start (S)")
    if not info["z"]:
        bad.append("no Z line (the job did not reach the result's screen)")
    if sch is not None:
        info["started"] = len(sch.started)
        info["refused"] = len(sch.refused)
        info["by_effect"] = {n: sum(1 for _, m in sch.started if m == n) for n in sorted(ex.fx)}
        info["shared"] = chk.shared if chk else 0
    return bad, info


def simlog(rom: bytes, lab: dict, mode: int, ticks: int, reqs: dict, hz50: bool = True) -> list[str]:
    """The log frsound.tcl writes, from the Z80 simulation (frsim's machine): S at tns_go, P at each pass
    (before $B00 + 1), R at snd_rfx's entry, T at tn_tick's (the SCC in openMSX's debuggable layout);
    Q after the last pass, then the stage's snd_stop and two VBLANKs (rg_hide's waits), E, the
    result's snd_stop (X) and the chips (Z)."""
    m = frsim.setup(rom, lab, mode, hz50)
    out = []
    r = m.bus.ram
    orig = frsim.z80.Z80.step

    def chips() -> str:
        s = m.bus.scc
        dbg = bytes(s[0x00:0x80]) + bytes(32) + bytes(s[0x80:0x8A]) + bytes(s[0x8A:0x8F]) + bytes([s[0x8F]])
        return "%s %s %s" % (dbg.hex() if mode & 1 else "-", bytes(m.bus.psg).hex(),
                             bytes(m.bus.opll).hex() if mode & 6 else "-")

    def step(self, _o=orig):
        pc = self.pc
        if pc == lab["tn_tick"] and m.bus.win[3] == lab["BANK_MUSIC"]:
            out.append("T %d %d %d %d %d %d %d %s" % (
                r[lab["tn_left"]] | r[lab["tn_left"] + 1] << 8, r[lab["tn_snd"]], r[lab["tn_busy"]], r[lab["tn_last"]],
                r[lab["tn_req"]], r[lab["mus_mode"]], r[lab["tn_mode"]], chips()))
        elif pc == lab["tns_go"] and m.bus.win[3] == lab["BANK_MUSIC"]:
            out.append("S %d" % r[lab["tick"]])
        elif pc == lab["snd_rfx"] and m.bus.win[3] == lab["BANK_FRNG"]:
            out.append("R %d" % self.a)
        return _o(self)
    frsim.z80.Z80.step = step
    try:
        frsim.tune_start(m)
        while m.ticks < ticks:
            t0 = m.ticks
            m.vblank()
            if m.ticks == t0:
                continue
            for n in reqs.get(m.ticks, []):
                frsim.request(m, n)
            out.append("P %d" % m.pz_frame())
            m.pass_()
        out.append("Q -1 -1 -1 " + chips())
        m.call(lab["snd_stop"], irq=False)
        for _ in range(2):
            m.vblank()
        out.append("E -1 -1 -1 " + chips())
        m.call(lab["snd_stop"], irq=False)
        out.append("X")
        for _ in range(3):
            m.vblank()
        out.append("Z 0 " + chips())
    finally:
        frsim.z80.Z80.step = orig
    return out


def selftest(root: Path, rom: Path, labels: Path) -> int:
    rb, lab = rom.read_bytes(), pzsim.labels(labels)
    reqs = frsim.plan_requests(1500)
    total = 0
    for name, mode in frsim.MODES:
        log = simlog(rb, lab, mode, 1500, reqs)
        bad, info = compare(root, log)
        k = next(i for i, x in enumerate(log) if x.startswith("T") and i > len(log) // 3)
        f = log[k].split()
        psg = bytearray(bytes.fromhex(f[9]))
        psg[9 if mode & 1 else 10] ^= 1
        f[9] = psg.hex()
        bad2, _ = compare(root, log[:k] + [" ".join(f)] + log[k + 1:])
        # the stage's stop: left out, or two ticks late (the last tick's T line twice before Q)
        q = next(i for i, x in enumerate(log) if x.startswith("Q"))
        bad3, _ = compare(root, log[:q] + log[q + 1:])
        lt = max(i for i, x in enumerate(log[:q]) if x.startswith("T"))
        bad4, _ = compare(root, log[:q] + [log[lt], log[lt]] + log[q:])
        late = any("ticks after its last pass" in b for b in bad4)
        ok = not bad and bad2 and bad3 and late
        total += not ok
        print("selftest %-18s %d lines, %d ticks compared: %s; a corrupted tick caught: %s; no stop caught: %s; "
              "a late stop caught: %s" % (name, len(log), info["ticks"], "PASS" if not bad else "FAIL %s" % bad[:3],
                                          bool(bad2), bool(bad3), late))
    print("selftest: %s" % ("PASS" if not total else "FAIL"))
    return 1 if total else 0


def main() -> int:
    if sys.argv[1] == "--selftest":
        return selftest(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    root = Path(sys.argv[1])
    total = 0
    for p in map(Path, sys.argv[2:]):
        bad, info = compare(root, p.read_text().splitlines())
        print("%s: %d ticks compared, %s; modes (mus_mode/tn_mode) %s; tick 0 after %s pass(es); effects started "
              "%s %s, refused %s; R6 shared on %s ticks; the tune %s (last tn_left %s); Q %s after %s tick(s) "
              "from the last pass; E %s; stop %s" % (
                  p.name, info["ticks"], "0 differences" if not bad else "%d differences" % len(bad),
                  ",".join(sorted(info["modes"])), info["passes_before_tick0"], info.get("started"),
                  info.get("by_effect"), info.get("refused"), info.get("shared"),
                  "ended" if info["ended"] else "still playing", info["last_left"], info["q"], info["q_ticks"],
                  info["e"],
                  "X, Z silent" if info["x"] and info["z"] else "missing"))
        for b in bad[:12]:
            print("   ", b)
        total += len(bad)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
