"""lpan.py (tools/bstest/perf2; agent a_loop's analyser of 2026-11-01): the frame pipeline's time
decomposition from lp.tcl's event stream. usage: python3 -I lpan.py EV LABELS BANKS_INC [--win A:B ...] [--json OUT]
(BANKS_INC: the build's gen/banks.inc; the sources' labels are read from the repository's msx/)

Per window (game frames A..B, tick_n at tick_start): the emulated time split by the main program's phase
(W: wait_frame; P: the picture's work, wf_got to the first tick; T: the ticks), the interrupts (by part:
entry, the split's timed part, isr_fbgo after it, the VBLANK's checks, its list and palette, its late
part, the sound), the VDP command engine (CE) over each, the PC samples classified (spin vs work), the
frame-cache uploads, the VBLANK classes (no list / held / taken), the cadence (ticks due, the cap)."""
import bisect
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

P = Path(__file__).resolve().parents[3]          # (the repository: tools/bstest/perf2/lpan.py)


def load_labels(path):
    lab = {}
    for line in open(path):
        m = re.match(r"(\w+):\s+equ \$([0-9a-fA-F]+)", line)
        if m:
            lab[m.group(1)] = int(m.group(2), 16)
    return lab


def load_banks(path):
    banks = {}
    for line in open(path):
        m = re.match(r"(BANK_\w+):\s+equ (\d+)", line)
        if m:
            banks[int(m.group(2))] = m.group(1)
    return banks


MODS = {"BANK_LC1": ("objects.asm", "shots.asm", "hits.asm"), "BANK_LC2": ("mapobj.asm",),
        "BANK_L1": ("level1.asm", "lvshared.asm"), "BANK_L2": ("level2.asm", "lvshared.asm"),
        "BANK_L3": ("level3.asm", "lvshared.asm"), "BANK_L3B": ("level3obj.asm",),
        "BANK_LC3": ("special.asm", "frame.asm", "plmove.asm"),
        "BANK_INPUT": ("sndplay.asm",), "BANK_FRONT": ("front.asm", "cold.asm"),
        "BANK_FIELD": ("field.asm",), "BANK_MUSIC": ("music.asm", "tune.asm")}
A000 = {"BANK_L1", "BANK_L2", "BANK_L3", "BANK_L3B", "BANK_INPUT", "BANK_FIELD", "BANK_MUSIC"}
FIXED = ("rc2.asm", "bank.asm", "vdp.asm", "isr.asm", "tiles.asm", "bob.asm", "logic.asm",
         "scroll9958.asm", "scroll9938.asm", "sprites.asm", "hud.asm", "player.asm", "sound.asm")


class Resolver:
    def __init__(self, labels, banks):
        self.lab = labels
        self.banks = banks
        src_of = {}
        for f in (P / "msx").glob("*.asm"):
            lines = f.read_text().splitlines()
            for i, l in enumerate(lines):
                m = re.match(r"^([A-Za-z_]\w*):(?!\s*equ)", l)
                if m:
                    src_of.setdefault(m.group(1), f.name)
        # level 2's shared code is assembled with suffixed labels (gen/lvshared_l2.asm)
        self.src_of = src_of
        self.pools = {"fixed": self.pool(FIXED, 0x4000, 0x8000)}
        for b, files in MODS.items():
            lo, hi = (0xA000, 0xC000) if b in A000 else (0x8000, 0xA000)
            self.pools[b] = self.pool(files, lo, hi)
        self.split_lo = labels.get("SR_RAM", 0xE5C0)
        self.split_hi = self.split_lo + 0x140

    def pool(self, files, lo, hi):
        p = sorted((v, k) for k, v in self.lab.items()
                   if self.src_of.get(k) in files and lo <= v < hi)
        return [v for v, _ in p], p

    def look(self, pool, pc):
        vs, p = pool
        i = bisect.bisect_right(vs, pc) - 1
        return (p[i][1], self.src_of.get(p[i][1], "?")) if i >= 0 else ("?", "?")

    def name(self, pc, b8, ba):
        if 0x4000 <= pc < 0x8000:
            return self.look(self.pools["fixed"], pc)
        if 0x8000 <= pc < 0xA000:
            b = self.banks.get(b8)
            return self.look(self.pools[b], pc) if b in self.pools else (f"8000:{b or b8}", "data?")
        if 0xA000 <= pc < 0xC000:
            b = self.banks.get(ba)
            return self.look(self.pools[b], pc) if b in self.pools else (f"A000:{b or ba}", "data?")
        if self.split_lo <= pc < self.split_hi:
            return ("split_ram", "split.asm")
        if pc < 0x4000:
            return ("BIOS", "bios")
        return ("RAM", "ram")


def main():
    args = sys.argv[1:]
    ev, labf, banksf = args[:3]
    wins = []
    jout = None
    i = 3
    while i < len(args):
        if args[i] == "--win":
            a, b = args[i + 1].split(":")
            wins.append((int(a), int(b)))
            i += 2
        elif args[i] == "--json":
            jout = args[i + 1]
            i += 2
        else:
            i += 1
    lab = load_labels(labf)
    res = Resolver(lab, load_banks(banksf))
    vdp_wait = lab["vdp_wait"]
    vdp_cmd = lab["vdp_cmd"]
    idle_rets = {lab["idle_work"] + 0x23, lab["idle_work"] + 0x2D}   # after its two vdp_busy calls
    wf_ret = lab["wf_idle"] + 4                                         # after wait_frame's idle_work call

    # per window accumulators
    W = defaultdict(lambda: {"t": Counter(), "n": Counter(), "samp": Counter(), "rout": Counter(),
                             "first": None, "last": None, "ticks": 0, "pics": 0, "vbl": Counter(),
                             "holds": [], "cad": Counter(), "due": 0, "ran": 0, "fc": 0.0, "fcn": 0,
                             "fc_ce": 0.0, "lost": 0, "tpp": Counter(), "pint": [], "lastk": None,
                             "lastgf": None, "fbq": Counter()})

    def win_of(gf):
        return [(a, b) for a, b in wins if a <= gf < b]

    cur = []            # the windows the current tick is in (they may overlap)
    ph = "?"            # main program phase
    isr = 0
    sub = "-"
    ce = 0
    fc = 0
    t_last = None
    pend_vbl = None     # (pk_state, fb_hold) at the last isr_vblank
    took = False

    def acc(t):
        nonlocal t_last
        if cur and t_last is not None and t > t_last:
            d = t - t_last
            key = (("I:" + sub) if isr else ph, ce)
            for wk in cur:
                w = W[wk]
                w["t"][key] += d
                if fc:
                    w["fc"] += d
                    if ce:
                        w["fc_ce"] += d
        t_last = t

    def enter(nw, t):
        for wk in nw:
            if W[wk]["first"] is None:
                W[wk]["first"] = t

    for line in open(ev):
        f = line.split()
        if not f:
            continue
        c = f[0]
        if c == "e":
            break
        t = float(f[1])
        if c == "b":
            gf = int(f[2])
            cur = win_of(gf)
            ce = int(f[3])
            ph = "T"
            isr = 0
            sub = "-"
            fc = 0
            t_last = t
            enter(cur, t)
            continue
        if c == "n":
            acc(t)
            for wk in cur:
                W[wk]["last"] = t
            cur = []
            continue
        acc(t)
        if c == "t":
            gf = int(f[2])
            nw = win_of(gf)
            for wk in cur:
                if wk not in nw:
                    W[wk]["last"] = t
            enter([wk for wk in nw if wk not in cur], t)
            cur = nw
            ph = "T"
            for wk in cur:
                W[wk]["ticks"] += 1
        elif c == "w":
            ph = "W"
        elif c == "g":
            ph = "P"
        elif c == "i":
            isr = 1
            sub = "entry"
        elif c == "s":
            sub = "split"
        elif c == "r":
            sub = "fbgo"
        elif c == "f":
            sub = "post"
        elif c == "v":
            sub = "vchk"
            pend_vbl = (int(f[2]), int(f[3]))
            took = False
        elif c == "k":
            took = True
            for wk in cur:
                w = W[wk]
                w["pics"] += 1
                if len(f) > 2:
                    gfr = int(f[2])
                    if w["lastgf"] is not None:
                        w["tpp"][min(gfr - w["lastgf"], 9)] += 1
                    w["lastgf"] = gfr
                if w["lastk"] is not None:
                    w["pint"].append(t - w["lastk"])
                w["lastk"] = t
        elif c == "l":
            sub = "list"
            if pend_vbl is not None:
                pk, hold = pend_vbl
                for wk in cur:
                    w = W[wk]
                    if pk == 0:
                        w["vbl"]["N"] += 1
                    elif took:
                        w["vbl"]["T"] += 1
                        w["holds"].append(hold)
                    elif pk == 2:
                        w["vbl"]["H"] += 1
                    else:
                        w["vbl"]["Q%d" % pk] += 1
                pend_vbl = None
        elif c == "z":
            sub = "late"
        elif c == "u":
            sub = "sound"
        elif c == "o":
            isr = 0
            sub = "-"
        elif c == "c":
            ce = int(f[2])
        elif c == "F":
            fc = 1
            for wk in cur:
                W[wk]["fcn"] += 1
        elif c == "G":
            fc = 0
        elif c == "d":
            wfn, due, cap = int(f[2]), int(f[3]), int(f[4])
            ran = due if due <= cap else cap
            for wk in cur:
                w = W[wk]
                w["due"] += due
                w["ran"] += ran
                if cap == 0:
                    w["cad"]["cap0"] += 1
                if due > cap:
                    w["cad"]["capped"] += 1
                    w["lost"] += due - cap
                w["cad"]["frames"] += 1
                w["cad"]["wfn%d" % (wfn if wfn < 9 else 9)] += 1
        elif c == "x":
            pc, b8, ba, s0, s1, s2 = (int(v) for v in f[2:8])
            r, fl = res.name(pc, b8, ba)
            state = ("I:" + sub) if isr else ph
            cls = classify(r, fl, pc, s0, s1, s2, lab, vdp_wait, vdp_cmd, idle_rets, wf_ret, state)
            fbq = None
            if len(f) >= 11:
                fbcq, fbb, pks = int(f[8]), int(f[9]), int(f[10])
                fbq = ("copy-waits" if fbcq & 1 else ("copy-runs" if fbcq in (2, 4) else
                       ("field-work" if fbb else "no-field-work")), ce)
            for wk in cur:
                W[wk]["samp"][(state, ce, cls)] += 1
                W[wk]["rout"][(state, r)] += 1
                if fbq:
                    W[wk]["fbq"][fbq] += 1
        for wk in cur:
            W[wk]["last"] = t

    out = {}
    for k in sorted(W):
        w = W[k]
        tot = sum(w["t"].values())
        if tot <= 0:
            continue
        span = (w["last"] or 0) - (w["first"] or 0)
        rep = {"window": list(k), "emulated_s": round(tot, 3), "span_s": round(span, 3), "ticks": w["ticks"],
               "pictures": w["pics"], "ticks_per_s": round(w["ticks"] / tot, 2),
               "pictures_per_s": round(w["pics"] / tot, 2)}
        byst = Counter()
        cebyst = Counter()
        for (st, c), d in w["t"].items():
            byst[st] += d
            if c:
                cebyst[st] += d
        rep["time_pct"] = {st: round(100 * d / tot, 2) for st, d in sorted(byst.items(), key=lambda x: -x[1])}
        rep["ce_busy_pct_of_state"] = {st: round(100 * cebyst[st] / byst[st], 1) for st in byst if byst[st] > 0}
        rep["ce_busy_pct"] = round(100 * sum(cebyst.values()) / tot, 2)
        isr_t = sum(d for st, d in byst.items() if st.startswith("I:"))
        rep["isr_pct"] = round(100 * isr_t / tot, 2)
        # the samples: classes per state
        ns = sum(w["samp"].values())
        cls = Counter()
        cls_ce = Counter()
        for (st, c, cl), n in w["samp"].items():
            cls[(st, cl)] += n
            if c:
                cls_ce[(st, cl)] += n
        rep["samples"] = ns
        rep["sample_classes_pct"] = {f"{st}/{cl}": [round(100 * n / ns, 2), round(100 * cls_ce[(st, cl)] / n, 1)]
                                     for (st, cl), n in sorted(cls.items(), key=lambda x: -x[1]) if n * 1000 >= ns}
        fq = w["fbq"]
        nq = sum(fq.values())
        if nq:
            rep["field_state_pct"] = {f"{k}/ce{c}": round(100 * v / nq, 2) for (k, c), v in sorted(fq.items())}
        rr = Counter()
        for (st, r), n in w["rout"].items():
            rr[r] += n
        rep["top_routines_pct"] = [[r, round(100 * n / ns, 2)] for r, n in rr.most_common(40)]
        rep["vblanks"] = dict(w["vbl"])
        h = w["holds"]
        rep["pictures_held"] = sum(1 for x in h if x > 0)
        rep["hold_vblanks_mean"] = round(sum(h) / len(h), 2) if h else 0
        rep["hold_hist"] = dict(Counter(min(x, 8) for x in h))
        rep["cadence"] = dict(w["cad"])
        rep["ticks_due"] = w["due"]
        rep["ticks_ran"] = w["ran"]
        rep["ticks_lost"] = w["lost"]
        rep["ticks_per_picture"] = {str(k): v for k, v in sorted(w["tpp"].items())}
        pi = sorted(w["pint"])
        if pi:
            def q(x):
                return round(1000 * pi[min(int(x * (len(pi) - 1)), len(pi) - 1)], 1)
            rep["picture_ms"] = {"median": q(0.5), "p90": q(0.9), "p99": q(0.99), "max": round(1000 * pi[-1], 1),
                                 "mean": round(1000 * sum(pi) / len(pi), 1)}
        rep["fc_uploads"] = w["fcn"]
        rep["fc_pct"] = round(100 * w["fc"] / tot, 2)
        rep["fc_ce_pct_of_fc"] = round(100 * w["fc_ce"] / w["fc"], 1) if w["fc"] else 0
        out[f"{k[0]}-{k[1]}"] = rep
    js = json.dumps(out, indent=1)
    if jout:
        Path(jout).write_text(js)
    print(js)


SPIN_W = {"wait_frame", "wf_lp", "wf_idle", "wf_got", "idle_work", "iw_fb", "iw_scr"}


def classify(r, fl, pc, s0, s1, s2, lab, vdp_wait, vdp_cmd, idle_rets, wf_ret, state):
    """The sample's class: what the CPU does there for the pipeline."""
    if fl == "split.asm" or r == "split_ram":
        return "split_ram"
    if r in ("vdp_busy", "vdp_wait"):
        rets = (s0, s1, s2)
        if any(x in idle_rets for x in rets):
            return "poll_idle"          # idle_work's look at the VDP (nothing to start: busy)
        if any(vdp_wait <= x < vdp_wait + 6 for x in rets) or r == "vdp_wait":
            return "spin_vdp_wait"      # a command waiting for the one before
        return "poll_other"
    if r in ("ifg_idle", "ifg_wt", "ifn_wt", "ifg_vr", "ifg_2", "ifn_2"):
        return "isr_chain_wait"
    if r in SPIN_W:
        return "spin_wait_frame"
    if r in ("feed_vdp", "fv_nv", "fv_chk", "fv_go"):
        return "feed_vdp"
    if fl in ("sndplay.asm", "music.asm", "tune.asm") or r.startswith("snd_") or fl == "sound.asm":
        return "sound"
    if fl == "field.asm":
        return "field"
    if fl in ("scroll9938.asm", "scroll9958.asm", "tiles.asm"):
        return "scroll_tiles"
    if fl == "sprites.asm":
        return "sprites"
    if fl == "bob.asm":
        return "bob"
    if fl in ("objects.asm", "shots.asm", "hits.asm", "mapobj.asm", "special.asm", "frame.asm", "plmove.asm",
              "level1.asm", "level2.asm", "level3.asm", "level3obj.asm", "lvshared.asm", "logic.asm"):
        return "logic"
    if fl == "player.asm":
        return "player"
    if fl == "isr.asm":
        return "isr_code"
    if fl == "hud.asm":
        return "hud"
    if fl in ("rc2.asm", "bank.asm"):
        return "loop_glue"
    if fl == "vdp.asm":
        return "vdp_other"
    return fl


if __name__ == "__main__":
    main()
