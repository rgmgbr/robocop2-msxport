"""tools/bytekiller.py, the ByteKiller decruncher ($124A6 transcribed). Synthetic streams from the
small packer below: every command, overlapping copies, the first long's marker, the checksum and
the refusals. The game's files when build/extracted exists (make extract): FRNG_15 and disk 1's
PUZL_13. The game's own $124A6 on the bench when the level-1 RAM image (make ram) and Unicorn (the
project's venv) are there. No data from the game in here."""
import hashlib
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import bytekiller  # noqa: E402

EXTRACTED = ROOT / "build" / "extracted"
LEVEL1_RAM = ROOT / "build" / "ram" / "level1_full.bin"
FRNG_SHA256 = "2ec1d6a4bf965d9ab11ea6ac2b1c8fde8385b1030ce4643c7740cbf203b6d26f"


def field(v: int, n: int) -> list[int]:
    """n bits of v, the highest first (the order the decruncher reads a field)."""
    assert 0 <= v < 1 << n
    return [v >> (n - 1 - i) & 1 for i in range(n)]


def encode(cmd: tuple) -> list[int]:
    """('lit', bytes in reading order) or ('copy', count, offset[, long form]) as stream bits."""
    if cmd[0] == "lit":
        data = cmd[1]
        head = [0, 0] + field(len(data) - 1, 3) if len(data) <= 8 else [1, 1, 1] + field(len(data) - 9, 8)
        return head + [b for x in data for b in field(x, 8)]
    _, n, o = cmd[:3]
    if (len(cmd) > 3 and cmd[3]) or n not in (2, 3, 4):
        return [1, 1, 0] + field(n - 1, 8) + field(o, 12)
    head, width = {2: ([0, 1], 8), 3: ([1, 0, 0], 9), 4: ([1, 0, 1], 10)}[n]
    return head + field(o, width)


def run(cmds: list[tuple], ulen: int) -> bytes:
    """What the commands write: downwards from the end, a copy byte by byte."""
    out, a = bytearray(ulen), ulen
    for cmd in cmds:
        if cmd[0] == "lit":
            for x in cmd[1]:
                a -= 1
                out[a] = x
        else:
            for _ in range(cmd[1]):
                a -= 1
                out[a] = out[a + cmd[2]]
    assert a == 0
    return bytes(out)


def pack(bits: list[int], ulen: int, first: int = 31, chk_delta: int = 0) -> bytes:
    """A file holding the bits: `first` of them under the first long's marker, then 32 a long, the
    longs stored in the other order (the decruncher reads them from the file's end)."""
    first = min(first, len(bits))
    longs = [1 << first | sum(b << j for j, b in enumerate(bits[:first]))]
    rest = bits[first:]
    longs += [sum(b << j for j, b in enumerate(rest[t:t + 32])) for t in range(0, len(rest), 32)]
    stream = longs[::-1]
    chk = chk_delta
    for v in stream:
        chk ^= v
    return struct.pack(f">III{len(stream)}I", 4 * len(stream), ulen, chk, *stream)


class SyntheticTests(unittest.TestCase):
    def test_known_answer_three_literal_bytes(self):
        # 0 0 010, then C B A: 29 bits under the marker at bit 29 = $30485848; the checksum the same
        src = bytes.fromhex("00000004 00000003 30485848 30485848")
        self.assertEqual(bytekiller.decrunch(src), b"ABC")
        self.assertEqual(bytekiller.unpack(src), (b"ABC", 0, 1, 1))
        self.assertEqual(pack(encode(("lit", b"CBA")), 3), src)

    def test_an_overlapping_copy_repeats_the_last_bytes(self):
        cmds = [("lit", b"YX"), ("copy", 4, 2)]          # 1 01 offset 2: X Y X Y below X Y
        self.assertEqual(bytekiller.decrunch(pack([b for c in cmds for b in encode(c)], 6)), b"XYXYXY")
        cmds = [("lit", b"Z"), ("copy", 200, 1)]          # the long form, offset 1: one byte 201 times
        self.assertEqual(bytekiller.decrunch(pack([b for c in cmds for b in encode(c)], 201)), b"Z" * 201)

    def test_every_command_and_marker_position(self):
        rnd = random.Random(1)
        for first in (0, 1, 5, 17, 31):
            cmds, size = [("lit", bytes(rnd.randrange(256) for _ in range(9)))], 9
            while size < 6000:
                kind = rnd.randrange(7)
                if kind == 0:                                   # 0 0 n(3) or 1 11 n(8)
                    n = rnd.randint(1, 8) if rnd.randrange(2) else rnd.randint(9, 264)
                    cmds.append(("lit", bytes(rnd.randrange(256) for _ in range(n))))
                    size += n
                    continue
                if kind <= 3:                                   # 0 1, 1 00, 1 01: 2, 3, 4 bytes
                    n, long_form = kind + 1, False
                else:                                           # 1 10 n(8) o(12): any count
                    n, long_form = (rnd.randint(1, 256) if kind < 6 else rnd.randint(2, 4)), True
                limit = 4095 if long_form else {2: 255, 3: 511, 4: 1023}[n]
                cmds.append(("copy", n, rnd.randint(1, min(size, limit)), long_form))
                size += n
            bits = [b for c in cmds for b in encode(c)]
            with self.subTest(first=first):
                u = bytekiller.unpack(pack(bits, size, first))
                self.assertEqual(u.data, run(cmds, size))
                self.assertEqual(u.checksum, 0)
                self.assertEqual(u.longs_read, u.longs)

    def test_a_wrong_checksum_is_refused(self):
        src = pack(encode(("lit", b"CBA")), 3, chk_delta=0x100)
        self.assertEqual(bytekiller.unpack(src).checksum, 0x100)
        with self.assertRaises(bytekiller.CrunchError):
            bytekiller.decrunch(src)

    def test_streams_that_leave_the_buffers_are_refused(self):
        bad = {
            "a copy before any byte is written": ([("copy", 2, 1)], 4),
            "a copy from offset 0": ([("lit", b"A"), ("copy", 2, 0)], 3),
            "a copy from beyond the end": ([("lit", b"AB"), ("copy", 2, 3)], 4),
            "literals below the start": ([("lit", b"ABC")], 2),
            "a copy below the start": ([("lit", b"AB"), ("copy", 3, 1)], 4),
        }
        for what, (cmds, ulen) in bad.items():
            with self.subTest(what), self.assertRaises(bytekiller.CrunchError):
                bytekiller.unpack(pack([b for c in cmds for b in encode(c)], ulen))
        with self.subTest("the stream runs out"), self.assertRaises(bytekiller.CrunchError):
            bytekiller.unpack(pack(encode(("lit", b"CBA")), 4))
        with self.subTest("a stream longer than the file"), self.assertRaises(bytekiller.CrunchError):
            bytekiller.unpack(pack(encode(("lit", b"CBA")), 3)[:-4])

    def test_the_command_line_writes_only_an_intact_file(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            (tmp / "ok.bk").write_bytes(pack(encode(("lit", b"CBA")), 3))
            (tmp / "bad.bk").write_bytes(pack(encode(("lit", b"CBA")), 3, chk_delta=1))
            tool = [sys.executable, "-I", str(ROOT / "tools" / "bytekiller.py")]
            r = subprocess.run(tool + [str(tmp / "ok.bk"), str(tmp / "ok.bin")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual((tmp / "ok.bin").read_bytes(), b"ABC")
            self.assertIn("checksum 00000000", r.stdout)
            r = subprocess.run(tool + [str(tmp / "bad.bk"), str(tmp / "bad.bin")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertFalse((tmp / "bad.bin").exists())
        finally:
            shutil.rmtree(tmp)


@unittest.skipUnless((EXTRACTED / "files" / "FRNG_15.bin").exists(), "needs build/extracted (make extract)")
class GameFileTests(unittest.TestCase):
    def test_frng_decrunches_whole_with_checksum_0(self):
        u = bytekiller.unpack((EXTRACTED / "files" / "FRNG_15.bin").read_bytes())
        self.assertEqual((len(u.data), u.checksum, u.longs_read, u.longs), (170970, 0, 23303, 23303))
        self.assertEqual(hashlib.sha256(u.data).hexdigest(), FRNG_SHA256)

    def test_disk_1_puzl_decrunches_to_disk_2_plain_copy(self):
        data = bytekiller.decrunch((EXTRACTED / "files" / "PUZL_13.bin").read_bytes())
        self.assertEqual(data, (EXTRACTED / "files" / "PUZL_25.bin").read_bytes())


@unittest.skipUnless(LEVEL1_RAM.exists() and (EXTRACTED / "files" / "FRNG_15.bin").exists(),
                     "needs build/ram/level1_full.bin and build/extracted (make ram)")
class BenchTests(unittest.TestCase):
    def test_the_games_own_124a6_gives_the_same_bytes(self):
        try:
            import amigaemu
            from unicorn.m68k_const import UC_M68K_REG_A0, UC_M68K_REG_A1
        except (SystemExit, ImportError):
            self.skipTest("needs Unicorn")
        b = amigaemu.PuzlBench(EXTRACTED, LEVEL1_RAM)     # (live SR across the bench's interrupts)
        b.boot_game()                                   # as the bench's frng mode: $8420's steps
        b.uc.mem_write(0x8050, struct.pack(">H", 1))
        b.uc.mem_write(0x10320, struct.pack(">I", 0x1032E))
        b.load_file("FRNG")                             # the loader: FRNG_15 at $1E980
        b.uc.reg_write(UC_M68K_REG_A0, 0x1E980)
        b.uc.reg_write(UC_M68K_REG_A1, 0x1EA00)
        b.call(amigaemu.DECRUNCH)
        mine = bytekiller.decrunch((EXTRACTED / "files" / "FRNG_15.bin").read_bytes())
        self.assertEqual(bytes(b.uc.mem_read(0x1EA00, len(mine))), mine)
        self.assertEqual(bytes(b.uc.mem_read(0x1EA00 + len(mine), 64)),
                         LEVEL1_RAM.read_bytes()[0x1EA00 + len(mine):0x1EA00 + len(mine) + 64])


if __name__ == "__main__":
    unittest.main()
