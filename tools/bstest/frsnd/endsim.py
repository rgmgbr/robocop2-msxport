"""The ending's sound (docs/ENDING.md): build/msx/end.bin (CMP tune 1 as $11C54 plays it, and HI1's
effects 3 and 4), played by an image's own code in the Brainstorm night's Z80 interpreter (pzsim.py:
the Konami SCC mapper, the PSG, the SCC and the OPLL modelled, every chip write logged) as
msx/ending.asm starts it, and checked after every tick against end.bin's streams decoded apart with the
converters' decoders (frsim.py's FExpect and Check; the effects' schedule with pzsim.Sched: $1822C's
rule, snd_ffx's merge: the higher request stays):

- tune: front_ending's start (ld hl,tn_cmp / call mus_call with BANK_FRONT2 at A000h, mus_call puts it
  back; then tn_hold 0, no stage's pass to wait for): its tick 0 the first tick after it, every tick of
  its T against the streams on the four chip sets at 50 and 60 Hz, the tune over at tick T (tn_left 0:
  front_ending's loop ends there, T + 1 ticks) and the chips silent from then on with no write; no
  effect is requested.
- entry: hs_name's start (the same call, then tn_left 1 and tn_hold 0: no tick of the tune): every tick
  silent but the effects, which snd_ffx (BANK_FRONT2 at A000h) asks for as the keys would: a key alone,
  keys at every tick, a key held through effect 3's length and one at its edge, Return (3 then 4 in
  the same tick: 4 stays), 4 then 3 during it (refused) and after it.
- r800: the tune and the effects on the R800 (cpu_cur 1: no OPLL; the SCC modes only), 600 ticks.

usage: endsim.py ROOT ROM LABELS [--modes 1,5,6,0] [--hz 50,60] [--only tune,entry,r800]
  ROOT: the repository (tools/, build/msx/end.bin)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import frsim  # noqa: E402
import pzsim  # noqa: E402

MM_SCC, MM_FM, MM_RHY = frsim.MM_SCC, frsim.MM_FM, frsim.MM_RHY
MODES = frsim.MODES
# the entry's requests: tick -> effects (snd_ffx after that tick's VBLANK, each)
ENTRY_REQS = {5: [3], 20: [3], 21: [3], 22: [3], 40: [3], 46: [3], 47: [3], 70: [3, 4], 100: [4], 105: [3],
              115: [3], 116: [3], 140: [3], 141: [4], 170: [4], 171: [3]}


def setup(rom: bytes, lab: dict, mode: int, hz50: bool) -> pzsim.Machine:
    m = pzsim.Machine(rom, lab, mode, hz50)
    m.bus.ram[lab["act_a000"]] = lab["BANK_FRONT2"]
    m.bus.win[3] = lab["BANK_FRONT2"]
    return m


def start(m: pzsim.Machine, entry: bool) -> None:
    """msx/ending.asm front_ending (entry False) or hs_name (True): ld hl,tn_cmp / call mus_call, then
    (hs_name) tn_left = 1, and tn_hold = 0."""
    L, r = m.L, m.bus.ram
    m.call(L["mus_call"], hl=L["tn_cmp"])
    if m.bus.win[3] != L["BANK_FRONT2"] or r[L["act_a000"]] != L["BANK_FRONT2"]:
        raise RuntimeError("mus_call left bank %d at A000h" % m.bus.win[3])
    if entry:
        r[L["tn_left"]], r[L["tn_left"] + 1] = 1, 0
    r[L["tn_hold"]] = 0


def run(ex: frsim.FExpect, rom: bytes, lab: dict, mode: int, ticks: int, reqs: dict, entry: bool, hz50: bool,
        r800: bool = False) -> tuple[list[str], dict]:
    """ex: end.bin decoded (frsim.FExpect). Returns (differences, details: the tick tn_left read 0,
    the effects started and refused)."""
    m = setup(rom, lab, mode, hz50)
    if r800:
        m.bus.ram[lab["cpu_cur"]] = 1
    emode = mode & MM_SCC if r800 else mode
    chk = frsim.Check(ex)
    sch = pzsim.Sched(ex.fx, bool(emode & MM_SCC))
    st = {"t": None, "bad": [], "over_at": None}

    def on_tick(mm):
        if st["t"] is None:
            return
        t = st["t"] = st["t"] + 1
        f = sch.tick(t)
        tune = None if entry else t
        st["bad"] += chk.tick(mm.bus, emode, tune, f, t)
        if st["over_at"] is None and m.tn_left() == 0:
            st["over_at"] = t
    m.on_tick = on_tick
    start(m, entry)
    sch.restart()
    st["t"] = -1
    while st["t"] < ticks and len(st["bad"]) < 20:
        t0, before = m.ticks, len(m.bus.log)
        m.vblank()
        if m.ticks == t0:
            if len(m.bus.log) != before:
                st["bad"].append("VBLANK %d (skipped at 60 Hz) wrote %s" % (m.vblanks, m.bus.log[before:before + 3]))
            continue
        t = st["t"]
        if not entry and t > ex.T and len(m.bus.log) != before:
            st["bad"].append("tick %d: writes after the tune's end: %s" % (t, m.bus.log[before:before + 3]))
        for n in reqs.get(t, []):
            m.call(lab["snd_ffx"], a=n, irq=False)
            sch.request(n)
    bad = st["bad"] + sorted(set(m.bus.violations))
    if not entry and st["over_at"] != ex.T and ticks > ex.T:
        bad.append("tn_left read 0 at tick %s, the tune's T %d expected" % (st["over_at"], ex.T))
    if r800 and any(w[0] == "opll" for w in m.bus.log):
        bad.append("the OPLL written on the R800")
    return bad, {"over_at": st["over_at"], "started": sch.started, "refused": sch.refused}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("rom", type=Path)
    ap.add_argument("labels", type=Path)
    ap.add_argument("--modes", default="1,5,6,0")
    ap.add_argument("--hz", default="50,60")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    only = set(filter(None, args.only.split(",")))
    want = lambda k: not only or k in only
    rom = args.rom.read_bytes()
    lab = pzsim.labels(args.labels)
    modes = [(n, mo) for n, mo in MODES if str(mo) in args.modes.split(",")]
    ex = frsim.FExpect(args.root, (args.root / "build" / "msx" / "end.bin").read_bytes())
    T = ex.T
    total = 0
    if want("tune"):
        for name, mode in modes:
            for hz in args.hz.split(","):
                bad, d = run(ex, rom, lab, mode, T + 60, {}, False, hz == "50")
                print("%-18s %s Hz: the tune's %d ticks and 60 after, tn_left 0 at tick %s: %s" % (
                    name, hz, T, d["over_at"], "PASS" if not bad else "FAIL"), flush=True)
                for b in bad[:12]:
                    print("   ", b)
                total += len(bad)
    if want("entry"):
        for name, mode in modes:
            for hz in args.hz.split(","):
                bad, d = run(ex, rom, lab, mode, 200, ENTRY_REQS, True, hz == "50")
                print("%-18s %s Hz: the entry's effects (no tune tick), %d started, refused %s: %s" % (
                    name, hz, len(d["started"]), d["refused"], "PASS" if not bad else "FAIL"), flush=True)
                for b in bad[:12]:
                    print("   ", b)
                total += len(bad)
    if want("r800"):
        for name, mode in (("SCC + OPLL", MM_SCC | MM_RHY), ("OPLL alone", MM_FM | MM_RHY)):
            bad, _ = run(ex, rom, lab, mode, 600, {}, False, True, r800=True)
            bad2, _ = run(ex, rom, lab, mode, 200, ENTRY_REQS, True, True, r800=True)
            print("R800, %-11s the tune's first 600 ticks and the entry's effects, no OPLL write: %s" % (
                name + ":", "PASS" if not bad + bad2 else "FAIL"))
            for b in (bad + bad2)[:12]:
                print("   ", b)
            total += len(bad + bad2)
    print("all: %s" % ("PASS" if not total else "FAIL (%d)" % total))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
