#!/usr/bin/env python3
"""cmpcheck.py BASE.log NEW.log [OUT]: two tools/bstest/check_all.sh logs, job by job. Every job of
the base must be in the new log with its trace at 0 differences (and the same frames and result),
its stills with 0 differences, and its record with no pixels outside the elements and no cursor
errors (as the base's). A torn cell is accepted only while the palette is black (the record's
pfpal all 0): bs_board's copies into the page on screen at a board's set-up, by design invisible
(docs/BRAINSTORM.md 4.3, 4.6; the base 4a8a61d has one, in solve1_tr at $B00 160). Which run shows
one depends on the CPU's phase against the VBLANK, which any change of timing moves. With OUT (the
check's output folder) each new torn cell is looked up in OUT/st/JOB/rec.txt and rec.bin. Exit 0
when it holds."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stepcheck  # noqa: E402


def torn_black(out, job):
    """the torn cells of OUT/st/JOB's record and whether the palette was black at each"""
    st = Path(out) / "st" / job
    recs = [int(m[1]) for m in re.finditer(r"^record (\d+) \(", (st / "rec.txt").read_text(), re.M)]
    data = (st / "rec.bin").read_bytes()
    o = 0
    for name, n in stepcheck.REC:
        if name == "pfpal":
            break
        o += n
    return [(r, not any(data[r * stepcheck.REC_LEN + o:r * stepcheck.REC_LEN + o + 32])) for r in recs]


def parse(path):
    jobs, cur = {}, None
    for line in open(path):
        m = re.match(r"^(\w+): (\d+) PUZL frames compared \((\d+) Amiga, (\d+) MSX\), (\d+) fields: (\d+) differ result: Amiga (\d+), MSX (\d+)", line)
        if m:
            cur = m[1]
            jobs[cur] = {"trace": m.groups()[1:]}
            continue
        if cur and "still:" in line:
            jobs[cur]["still"] = int(re.search(r"(\d+) with differences", line)[1])
        if cur and "rec:" in line and "torn/unknown" in line:
            m = re.search(r"torn/unknown blocks (\d+), pictures with pixels outside the elements (\d+), cursor errors (\d+)", line)
            jobs[cur]["rec"] = tuple(int(v) for v in m.groups())
            jobs[cur]["pics"] = re.search(r"(\d+) pictures in (\d+) VBLANKs", line).groups()
    return jobs


def main():
    base, new = parse(sys.argv[1]), parse(sys.argv[2])
    bad = 0
    for job, b in base.items():
        n = new.get(job)
        if not n:
            print(f"{job}: missing")
            bad = 1
            continue
        t = n["trace"]
        ok = t[4] == "0" and t[0] == b["trace"][0] and t[5:] == b["trace"][5:] and t[5] == t[6]
        msg = f"{job}: trace {t[0]} frames, {t[4]} differ, result {t[6]}"
        if "still" in b:
            ok &= n.get("still", 1) == 0
            msg += f"; stills {n.get('still')} differ"
        if "rec" in b:
            r = n.get("rec", (99, 99, 99))
            ok &= r[1] == 0 and r[2] == 0
            msg += f"; record {n.get('pics', ('?', '?'))[0]} pictures, torn {r[0]} (base {b['rec'][0]}), outside {r[1]}, cursor {r[2]}"
            if r[0]:
                if len(sys.argv) > 3:
                    tb = torn_black(sys.argv[3], job)
                    ok &= len(tb) == r[0] and all(blk for _, blk in tb)
                    msg += " [" + ", ".join(f"record {k}: palette {'black' if blk else 'NOT black'}" for k, blk in tb) + "]"
                else:
                    ok &= r[0] <= b["rec"][0]
        print(("  " if ok else "  FAIL ") + msg)
        bad |= not ok
    zero = sum(1 for j in new.values() if j["trace"][4] == "0")
    print(f"{zero} of {len(new)} traces 0 differ (base: {len(base)} jobs)")
    print("cmpcheck:", "PASS" if not bad else "FAIL")
    return bad


if __name__ == "__main__":
    sys.exit(main())
