"""The movie stills (tools/zx0.py, tools/msxphoto.py, msx/photo.asm) and level 1's briefing
(tools/msxtext.py brief1.inc, msx/photo2.asm)."""
from __future__ import annotations

import random
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import msxtext  # noqa: E402
import zx0  # noqa: E402

RAM = ROOT / "build" / "ram" / "level1_full.bin"            # tools/ramimage.py (make ram)
FILES = ROOT / "build" / "extracted" / "files"              # tools/rc2files.py (make extract)


def blocks(src: bytes) -> list[tuple[str, int, int]]:
    """A ZX0 stream's blocks (kind, length, offset) as dzx0_standard reads them."""
    pos, bits, out = 0, 0x80, []

    def bit() -> int:
        nonlocal bits, pos
        bits <<= 1
        if bits & 0xFF == 0:
            bits = src[pos] << 1 | 1
            pos += 1
        v = bits >> 8 & 1
        bits &= 0xFF
        return v

    def elias(invert: bool = False, first: int | None = None) -> int:
        v, ctl = 1, (bit() if first is None else first)
        while not ctl:
            v = v << 1 | (bit() ^ invert)
            ctl = bit()
        return v

    last, state = 1, "lit"
    while True:
        if state == "lit":
            n = elias()
            out.append(("lit", n, 0))
            pos += n
            state = "new" if bit() else "rep"
        elif state == "rep":
            out.append(("rep", elias(), last))
            state = "new" if bit() else "lit"
        else:
            msb = elias(invert=True)
            if msb == 256:
                return out
            lsb = src[pos]
            pos += 1
            last = msb * 128 - (lsb >> 1)
            out.append(("new", elias(first=lsb & 1) + 1, last))
            state = "new" if bit() else "lit"


class Zx0Tests(unittest.TestCase):
    def test_round_trip(self):
        rnd = random.Random(7)
        for k in range(120):
            data = bytes(rnd.randrange(rnd.randint(1, 5)) for _ in range(rnd.randint(1, 700)))
            for stride, pen, mo in ((0, 0, zx0.MAX_OFFSET), (16, 12, 256), (7, 0, 32)):
                packed = zx0.pack(data, stride, pen, mo)
                self.assertEqual(zx0.unpack(packed), data, (k, stride, pen, mo))
                self.assertTrue(all(off <= mo for kind, _, off in blocks(packed) if kind != "lit"))

    def test_format_details(self):
        # the first block literals, a long run as copies from offset 1, the end mark
        data = b"A" + b"B" * 300 + b"AB" * 20
        b = blocks(zx0.pack(data))
        self.assertEqual(b[0][0], "lit")
        self.assertEqual(sum(n for _, n, _ in b), len(data))
        self.assertTrue(any(kind != "lit" and off == 1 and n > 200 for kind, n, off in b))
        self.assertTrue(all(n >= 2 for kind, n, _ in b if kind == "new"))

    def test_penalty_makes_fewer_copies(self):
        rnd = random.Random(3)
        data = bytes(rnd.choice(b"\x00\x24\x49\x92") for _ in range(4000))
        few = sum(k != "lit" for k, _, _ in blocks(zx0.pack(data, 0, 12, 256)))
        many = sum(k != "lit" for k, _, _ in blocks(zx0.pack(data, 0, 0, 256)))
        self.assertLess(few, many)


class PhotoAsmTests(unittest.TestCase):
    def test_photo_asm_reads_what_msxphoto_writes(self):
        # (msxphoto.py needs Pillow, which make test's python lacks: its table read from its text)
        tool = (ROOT / "tools" / "msxphoto.py").read_text()
        asm = (ROOT / "msx" / "photo.asm").read_text()
        self.assertIn("MAX_OFFSET = 256", tool)          # pho_unz's ring: one 256-byte page
        photos = re.findall(r'\("(PIC\w)", "PIC\w_\d+\.bin", (\d+), (\d+)\)', tool)
        names = [n for n, _, _ in photos]
        self.assertEqual(names, ["PIC1", "PIC2", "PIC3", "PIC4", "PIC5", "PIC6", "PIC7", "PICF"])
        self.assertEqual(re.findall(r"db PHOTO_(\w+)_BANK", asm), names)   # pho_tab: show_picture's D0, 7 PICF
        self.assertIn("PHO_TICKS:   equ 251", asm)       # $11E06: dbf from 250
        self.assertEqual([int(k) for _, _, k in photos], [176] * 7 + [212])

    def test_options_off_leave_the_code_out(self):
        for f in ("photo.asm", "photo2.asm"):
            text = (ROOT / "msx" / f).read_text()
            code = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith(";")]
            self.assertIn(code[0].split(";")[0].strip(), ("if PHOTOS", "if L1BRIEF"), f)


@unittest.skipUnless(RAM.exists(), "level 1's RAM image not built (make ram)")
class LevelOneBriefingTests(unittest.TestCase):
    def test_script(self):
        (label, start, script), = msxtext.brief_scripts(RAM.read_bytes(), msxtext.BRIEF1)
        self.assertEqual((label, start), ("txt_l1_brief", 0x11108))
        self.assertEqual(msxtext.fs_run(script)[1], 485)
        text = msxtext.decode(bytes(b for b in script if 0x20 <= b < 0x80))
        for line in ("THE RIVER ROUGE", "COMPLEX", "NEGOTIATE THE RIVER COMPLEX", "COLLECT TEN NUKE CAPSULES",
                     "THEN DESTROY THE DRUGS LAB", "RESCUE ALL HOSTAGES", "FOR AN EXTRA LIFE."):
            self.assertIn(line, text)

    def test_particle_lines(self):
        lines, calls = msxtext.particle_lines(RAM.read_bytes(), 0x11108)
        self.assertEqual([c for c, _ in lines], [b"THE RIVER ROUGE", b"COMPLEX"])
        self.assertEqual(calls, 109)
        (_, _, y0, _), (_, _, y1, _) = (box for _, box in lines)
        self.assertEqual(y1 - y0, 16)                   # one particle line below the other


if __name__ == "__main__":
    unittest.main()
