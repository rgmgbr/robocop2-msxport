#!/usr/bin/env python3
"""Execution bench for the Robocop 2 68000 code on top of Unicorn.

Code analysis goes through REA + Ghidra (project rule); this bench only emulates the
Amiga hardware needed for the game code to run and be inspected (it is not a full
Amiga emulator):

- 512 KiB of chip RAM at $000000 and 512 KiB of "slow RAM" at $C00000;
- custom registers at $DFF000 (beam counters, DMA/INT, colours, pointers) and CIAs at
  $BFD000/$BFE001 (fire button, minimal keyboard);
- area-mode blitter (channels A-D, shifts, masks, minterm, ascending and descending),
  run when BLTSIZE is written;
- game loader intercepted at $100 (A0 = name): loads the files from build/extracted
  to their name-table destination, as the trackloader would;
- VBL interrupt (level 3) injected every frame when enabled;
- joystick in port 2 (JOY1DAT, fire on CIA-A PRA bit 7);
- write watchpoints and address breakpoints, for tracing.

"run" boots from the boot block's entry (the intro still fails on the logo plotting). "game"
skips it: it loads a level's RAM image (tools/ramimage.py), installs the interrupt vectors and
runs the game's own new-game path without the title (hardware setup $FEDA, lives and score
$FFC4, level_init $871A), then main_loop. At the start of every game frame (after main_loop's
VBL wait, $80CC) it applies the joystick script and records the traced variables: a reference
for the MSX port of the game logic (the logic only depends on the inputs and on the random
generator $B32, which reads CIA timers the bench returns as FFh).

"puzl" runs Brainstorm, the bonus stage after levels 1 and 2 (load_level1 $8582 -> $8382): the
same set-up ($FEDA, $FFC4), $8050 = the level done, then what $8382 does from its loader call on
(PUZL loaded by the game's loader; disk 1's copy decrunched by the game's own $124A6 from $17080
to $17100) and jsr $17100, or with --via-8382 the whole of $8382 (intro text, PIC3, loader).
PUZL keeps its own frame loop ($171BA: one frame per $802C, one VBL; its VBL handler $17B5A); at
the start of every PUZL frame (after the wait, $171C2) the joystick script is applied and the
stage's variables recorded, until $17100 returns D0 (0 solved, 1 failed, 2 out of time). Its
music player ($18000, PZM) is skipped as MU1's is. The timer (CIA-B, level 6) stands still unless
--sec N raises it after every N-th PUZL frame.

Depends on Unicorn (pip install unicorn).

usage:
  amigaemu.py run --frames 600 [--fire 300:20] [--dump build/emu/ram.bin]
                  [--watch 0x3e810-0x40000] [--screenshot build/emu/frame.png]
  amigaemu.py game --ram build/ram/level1_full.bin --gframes 200 [--joy 10:40:r --joy 60:5:rf ...]
                   [--trace OUT.jsonl] [--bobs OUT.jsonl] [--screenshot build/emu/game.png]
                   [--dump OUT.bin] (chip RAM after the last game frame: the map at $38000 ...)
     (--bobs: per game frame, every draw_bob $AB08 call: A2, D4, D0, D1, minterm, drawn)
     (--joy GAMEFRAME:COUNT:KEYS, keys among u d l r f, game frames counted from the first)
  amigaemu.py puzl [--level 1] [--via-8382] --pframes 600 [--joy 0:1:r --joy 2:1:d ...]
                   [--drive FILE] [--poke F:ADDR:VALUE[:SIZE] ...] [--sec 60]
                   [--trace OUT.jsonl] [--trace-ram] [--screenshot OUT.png] [--dump OUT.bin]
     (--joy PUZLFRAME:COUNT:KEYS, PUZL frames counted from its first; --drive: tools/drivejoy.py's
     file, its joystick bytes and pokes)
"""
from __future__ import annotations

import argparse
import ctypes
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amigahw import CUSTOM, rgb12_to_rgb24  # noqa: E402

try:
    from unicorn import (UC_ARCH_M68K, UC_HOOK_CODE, UC_HOOK_MEM_WRITE, UC_MODE_BIG_ENDIAN, UC_PROT_ALL, Uc,
                         UcError)
    from unicorn.m68k_const import (UC_CPU_M68K_M68000, UC_M68K_REG_A0, UC_M68K_REG_A7, UC_M68K_REG_D0,
                                    UC_M68K_REG_PC, UC_M68K_REG_SR)
except ImportError:  # pragma: no cover
    sys.exit("amigaemu.py needs Unicorn: pip install unicorn")

ROOT = Path(__file__).resolve().parents[1]
CHIP_SIZE = 0x80000
SLOW_BASE, SLOW_SIZE = 0xC00000, 0x80000
CUSTOM_BASE = 0xDFF000
CIA_BASE = 0xBFD000
LOADER_ENTRY = 0x100
LINES = 312  # PAL
SR_STUB = 0xE00000          # a page outside the A500's map: 'move.w sr,(SR_STUB + $100).l' (live_sr)

REG = {name: off for off, name in CUSTOM.items()}


def a_reg(n: int) -> int:
    return UC_M68K_REG_A0 + n


def d_reg(n: int) -> int:
    return UC_M68K_REG_D0 + n


class Blitter:
    """OCS blitter in area mode (no line mode, no fill)."""

    def __init__(self, emu: "AmigaEmu"):
        self.emu = emu
        self.count = 0
        self.unsupported: dict[str, int] = defaultdict(int)

    def run(self, size: int) -> None:
        r = self.emu.regs
        con0, con1 = r[REG["BLTCON0"]], r[REG["BLTCON1"]]
        if con1 & 1:
            self.unsupported["line"] += 1
            return
        if con1 & 0x18:
            self.unsupported["fill"] += 1
        h = (size >> 6) & 0x3FF or 1024
        w = size & 0x3F or 64
        use_a, use_b, use_c, use_d = con0 & 0x800, con0 & 0x400, con0 & 0x200, con0 & 0x100
        lf = con0 & 0xFF
        ash, bsh = con0 >> 12, con1 >> 12
        desc = bool(con1 & 2)
        step = -2 if desc else 2

        def ptr(name):
            return ((r[REG[name + "PTH"]] << 16) | r[REG[name + "PTL"]]) & (CHIP_SIZE - 2)

        def smod(name):
            v = r[REG[name + "MOD"]] & 0xFFFE
            return v - 0x10000 if v & 0x8000 else v

        apt, bpt, cpt, dpt = ptr("BLTA"), ptr("BLTB"), ptr("BLTC"), ptr("BLTD")
        amod, bmod, cmod, dmod = smod("BLTA"), smod("BLTB"), smod("BLTC"), smod("BLTD")
        if desc:
            amod, bmod, cmod, dmod = -amod, -bmod, -cmod, -dmod
        afwm, alwm = r[REG["BLTAFWM"]], r[REG["BLTALWM"]]
        adat, bdat, cdat = r[REG["BLTADAT"]], r[REG["BLTBDAT"]], r[REG["BLTCDAT"]]
        mem = self.emu.chip
        aold = bold = 0
        zero = True
        for _y in range(h):
            for x in range(w):
                apt &= CHIP_SIZE - 2
                bpt &= CHIP_SIZE - 2
                cpt &= CHIP_SIZE - 2
                dpt &= CHIP_SIZE - 2
                a = (mem[apt] << 8 | mem[apt + 1]) if use_a else adat
                if use_a:
                    apt += step
                if x == 0:
                    a &= afwm
                if x == w - 1:
                    a &= alwm
                b = (mem[bpt] << 8 | mem[bpt + 1]) if use_b else bdat
                if use_b:
                    bpt += step
                c = (mem[cpt] << 8 | mem[cpt + 1]) if use_c else cdat
                if use_c:
                    cpt += step
                if desc:
                    asft = ((a << 16 | aold) << ash >> 16) & 0xFFFF
                    bsft = ((b << 16 | bold) << bsh >> 16) & 0xFFFF
                else:
                    asft = ((aold << 16 | a) >> ash) & 0xFFFF
                    bsft = ((bold << 16 | b) >> bsh) & 0xFFFF
                aold, bold = a, b
                d = 0
                for k in range(8):
                    if lf >> k & 1:
                        t = asft if k & 4 else ~asft
                        t &= bsft if k & 2 else ~bsft
                        t &= c if k & 1 else ~c
                        d |= t
                d &= 0xFFFF
                if d:
                    zero = False
                if use_d:
                    mem[dpt] = d >> 8
                    mem[dpt + 1] = d & 0xFF
                    self.emu.note_write(dpt, 2, "blitter")
                    dpt += step
            apt += amod if use_a else 0
            bpt += bmod if use_b else 0
            cpt += cmod if use_c else 0
            dpt += dmod if use_d else 0
        self.count += 1
        self.emu.bzero = zero
        # final pointers stay in the registers, as on the hardware
        for name, v in (("BLTA", apt), ("BLTB", bpt), ("BLTC", cpt), ("BLTD", dpt)):
            r[REG[name + "PTH"]], r[REG[name + "PTL"]] = (v >> 16) & 0xFFFF, v & 0xFFFF


class AmigaEmu:
    def __init__(self, extracted: Path, *, verbose: bool = False):
        self.extracted = extracted
        self.verbose = verbose
        self.manifest = json.loads((extracted / "manifest.json").read_text())
        self.uc = Uc(UC_ARCH_M68K, UC_MODE_BIG_ENDIAN)
        self.uc.ctl_set_cpu_model(UC_CPU_M68K_M68000)
        # chip RAM mirrored up to $1FFFFF, as on an A500 with 512 KiB of chip RAM
        self._chipbuf = (ctypes.c_ubyte * CHIP_SIZE)()
        self.chip = memoryview(self._chipbuf).cast("B")
        for mirror in range(0, 0x200000, CHIP_SIZE):
            self.uc.mem_map_ptr(mirror, CHIP_SIZE, UC_PROT_ALL, ctypes.addressof(self._chipbuf))
        self.uc.mem_map(SLOW_BASE, SLOW_SIZE)
        self.uc.mmio_map(CUSTOM_BASE, 0x1000, self._custom_read, None, self._custom_write, None)
        self.uc.mmio_map(CIA_BASE, 0x2000, self._cia_read, None, self._cia_write, None)
        self.uc.mem_map(SR_STUB, 0x1000)
        self.uc.mem_write(SR_STUB, struct.pack(">HI", 0x40F9, SR_STUB + 0x100))
        self.fix_sr = False     # interrupts push live_sr() (the puzl mode; see live_sr)
        self.regs = [0] * 0x100  # custom register words, index = offset
        self.dmacon = 0
        self.intena = 0
        self.intreq = 0
        self.vpos = 0
        self.bzero = True
        self.frame = 0
        self.fire = False
        self.fire_script: list[tuple[int, int]] = []
        self.joy = 0                    # JOY1DAT
        self._sentinel_hit = False
        self.blitter = Blitter(self)
        self.watch: list[tuple[int, int]] = []
        self.write_log: list[tuple[int, int, int, str]] = []
        self.loads: list[tuple[int, str, int, int]] = []
        self.breakpoints: dict[int, str] = {}
        self.hits: list[tuple[int, int, str]] = []
        self._stop_reason: str | None = None
        self._pending_loader = False
        self.uc.hook_add(UC_HOOK_CODE, self._on_loader, None, LOADER_ENTRY, LOADER_ENTRY + 1)
        self.names = self._name_table()

    # ------------------------------------------------------------ memory
    def read_long(self, a: int) -> int:
        return struct.unpack(">I", self.uc.mem_read(a, 4))[0]

    def read_word(self, a: int) -> int:
        return struct.unpack(">H", self.uc.mem_read(a, 2))[0]

    def note_write(self, addr: int, size: int, who: str) -> None:
        for lo, hi in self.watch:
            if lo <= addr < hi:
                self.write_log.append((self.frame, addr, size, who))
                return

    # ------------------------------------------------------------ files
    def _name_table(self) -> list[dict]:
        files = self.manifest["files"]
        return files

    def load_file(self, name: str) -> tuple[int, int]:
        cands = [f for f in self.names if f["name"] == name]
        if not cands:
            raise KeyError(f"unknown file: {name!r}")
        f = cands[0]
        if name[2:3] == "Z" and self.read_word(0x8050) == 2 and len(cands) > 1:
            f = cands[1]
        data = (self.extracted / f["file"]).read_bytes()
        dest = f["load_address"]
        self.uc.mem_write(dest, data)
        self.loads.append((self.frame, name, dest, len(data)))
        if self.verbose:
            print(f"[frame {self.frame}] loaded {name} at ${dest:05x} (+{len(data)})")
        if self.watch:
            for lo, hi in self.watch:
                if dest < hi and dest + len(data) > lo:
                    self.write_log.append((self.frame, max(lo, dest), min(hi, dest + len(data)) - max(lo, dest),
                                           f"loader:{name}"))
        return dest, f["id"]

    def _on_loader(self, uc, address, size, user_data):
        self._pending_loader = True
        uc.emu_stop()

    def _service_loader(self) -> None:
        a0 = self.uc.reg_read(a_reg(0))
        raw = bytes(self.uc.mem_read(a0, 8))
        name = raw.split(b"\0", 1)[0].decode("ascii", "replace")
        dest, fid = self.load_file(name)
        sp = self.uc.reg_read(UC_M68K_REG_A7)
        ret = self.read_long(sp)
        self.uc.reg_write(UC_M68K_REG_A7, sp + 4)
        self.uc.reg_write(a_reg(0), dest)
        self.uc.reg_write(d_reg(0), fid & 0x7F)
        self.uc.reg_write(UC_M68K_REG_PC, ret)

    # ------------------------------------------------------------ custom chips
    def _custom_read(self, uc, offset, size, user_data):
        if size == 4:
            return (self._custom_read(uc, offset, 2, None) << 16) | self._custom_read(uc, offset + 2, 2, None)
        word_off = offset & ~1
        v = self._custom_word(word_off)
        if size == 1:
            return (v >> 8) & 0xFF if offset % 2 == 0 else v & 0xFF
        return v

    def _custom_word(self, off: int) -> int:
        if off == 0x002:  # DMACONR
            return (self.dmacon & 0x07FF) | (0x2000 if self.bzero else 0)
        if off == 0x004:  # VPOSR
            return (self.vpos >> 8) & 1
        if off == 0x006:  # VHPOSR: advances one line per read
            self.vpos = (self.vpos + 1) % LINES
            return (self.vpos & 0xFF) << 8
        if off == 0x01C:
            return self.intena
        if off == 0x01E:
            return self.intreq
        if off == 0x00C:  # JOY1DAT (port 2)
            return self.joy
        if off == 0x00A:  # JOY0DAT
            return 0
        if off == 0x016:  # POTGOR: secondary buttons released
            return 0xFF00
        return self.regs[off >> 0] if off < len(self.regs) else 0

    def _custom_write(self, uc, offset, size, value, user_data):
        if size == 4:
            self._custom_write(uc, offset, 2, (value >> 16) & 0xFFFF, None)
            self._custom_write(uc, offset + 2, 2, value & 0xFFFF, None)
            return
        if size == 1:
            return
        off = offset & 0x1FE
        if off == 0x096:
            self.dmacon = self._setclr(self.dmacon, value)
        elif off == 0x09A:
            self.intena = self._setclr(self.intena, value)
        elif off == 0x09C:
            self.intreq = self._setclr(self.intreq, value)
        else:
            if off < len(self.regs):
                self.regs[off] = value & 0xFFFF
            if off == 0x058:  # BLTSIZE
                self.blitter.run(value & 0xFFFF)

    @staticmethod
    def _setclr(reg: int, value: int) -> int:
        return reg | (value & 0x7FFF) if value & 0x8000 else reg & ~value & 0x7FFF

    # ------------------------------------------------------------ CIAs
    def _cia_read(self, uc, offset, size, user_data):
        addr = CIA_BASE + offset
        if addr == 0xBFE001:  # CIAA PRA: bit 7 = port 2 fire (active low)
            return 0x7F if self.fire else 0xFF
        if addr == 0xBFED01:  # CIAA ICR
            return 0
        return 0xFF

    def _cia_write(self, uc, offset, size, value, user_data):
        return

    # ------------------------------------------------------------ execution
    def boot(self) -> None:
        x = self.extracted / "boot"
        self.uc.mem_write(0x8000, (x / "main_8000.bin").read_bytes())
        self.uc.mem_write(0x100, (x / "loader_100.bin").read_bytes())
        self.uc.mem_write(0x300, (x / "loader_300.bin").read_bytes())
        self.uc.mem_write(0xC0, struct.pack(">I", 0x100))
        self.uc.reg_write(UC_M68K_REG_SR, 0x2700)
        self.uc.reg_write(UC_M68K_REG_A7, 0x7FFF0)
        self.uc.reg_write(UC_M68K_REG_PC, 0x8000)

    def do_rte(self) -> bool:
        """Unicorn's m68k raises an exception on RTE: done here (68000 frame: SR, PC)."""
        pc = self.uc.reg_read(UC_M68K_REG_PC)
        if self.read_word(pc) != 0x4E73:
            return False
        sp = self.uc.reg_read(UC_M68K_REG_A7)
        sr, ret = struct.unpack(">HI", bytes(self.uc.mem_read(sp, 6)))
        self.uc.reg_write(UC_M68K_REG_A7, sp + 6)
        self.uc.reg_write(UC_M68K_REG_SR, sr)
        self.uc.reg_write(UC_M68K_REG_PC, ret)
        return True

    def inject_vbl(self) -> bool:
        """Level 3 at the start of the frame: VERTB, or COPER when the game uses the copper's
        interrupt instead (Robocop 2 does: its copper list raises COPER and SOFT)."""
        bit = 0x0020 if self.intena & 0x0020 else 0x0010
        return self.inject(3, 0x6C, bit)

    def live_sr(self) -> int:
        """SR with the condition codes of the last instruction. Unicorn's m68k keeps the flags
        lazily and reg_read(SR) returns a stale CCR, so an interrupt pushed from it returns with
        the flags of an earlier instruction: the game's decruncher $124A6, stopped between its
        cmpa.l A2,A1 ($12522) and blt ($12524) by a VBL, gave up after 2 frames. A 'move.w sr'
        stub computes them without changing them."""
        pc = self.uc.reg_read(UC_M68K_REG_PC)
        self.uc.emu_start(SR_STUB, SR_STUB + 6)
        self.uc.reg_write(UC_M68K_REG_PC, pc)
        return self.read_word(SR_STUB + 0x100)

    def inject(self, level: int, vector: int, bit: int) -> bool:
        sr = self.live_sr() if self.fix_sr else self.uc.reg_read(UC_M68K_REG_SR)
        if not (self.intena & 0x4000 and self.intena & bit):
            return False
        if (sr >> 8) & 7 >= level:
            return False
        self.intreq |= bit
        pc = self.uc.reg_read(UC_M68K_REG_PC)
        sp = self.uc.reg_read(UC_M68K_REG_A7) - 6
        self.uc.mem_write(sp, struct.pack(">HI", sr & 0xFFFF, pc))
        self.uc.reg_write(UC_M68K_REG_A7, sp)
        self.uc.reg_write(UC_M68K_REG_SR, (sr & 0xF8FF) | 0x2000 | (level << 8))
        self.uc.reg_write(UC_M68K_REG_PC, self.read_long(vector))
        return True

    def run_frames(self, frames: int, insns_per_frame: int = 40000) -> None:
        for _ in range(frames):
            self.fire = any(s <= self.frame < s + n for s, n in self.fire_script)
            budget = insns_per_frame
            while budget > 0:
                pc = self.uc.reg_read(UC_M68K_REG_PC)
                chunk = min(budget, 5000)
                try:
                    self.uc.emu_start(pc, 0xFFFFFFFE, 0, chunk)
                except UcError as e:
                    raise RuntimeError(f"CPU fault in frame {self.frame}: {e}\n{self.regs_text()}") from e
                if self._pending_loader:
                    self._pending_loader = False
                    self._service_loader()
                    budget -= 100
                    continue
                budget -= chunk
            self.vpos = 0
            self.inject_vbl()
            self.frame += 1

    # ------------------------------------------------------------ inspection
    def regs_text(self) -> str:
        r = self.uc.reg_read
        d = " ".join(f"D{i}={r(d_reg(i)):08x}" for i in range(8))
        a = " ".join(f"A{i}={r(a_reg(i)):08x}" for i in range(8))
        return f"PC={r(UC_M68K_REG_PC):06x} SR={r(UC_M68K_REG_SR):04x}\n{d}\n{a}"

    def dump(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes(self.uc.mem_read(0, CHIP_SIZE)))

    def screenshot(self, path: Path, base: int | None = None, lines: int = 192) -> None:
        """Renders the interleaved playfield (4 planes x 38 bytes) with the palette of copper list $1049E."""
        from planar import decode_indices, render, write_png
        ram = bytes(self.uc.mem_read(0, CHIP_SIZE))
        if base is None:
            base = self.read_long(0xB16) ^ 0x18E00  # front buffer
        pal = [(0, 0, 0)] + [rgb12_to_rgb24(struct.unpack_from(">H", ram, 0x104A4 + 4 * i)[0]) for i in range(15)]
        idx = decode_indices(ram, base, 304, lines, 4, "interleaved", row_bytes=38)
        write_png(path, 304 * 2, lines * 2, render(idx, pal, False, 2))


SENTINEL = 0x7FF00                     # return address of call(): stops the emulation
MUSIC = (0x18000, 0x28000)              # MU1 and its player (up to DATAL1)
GAME_FRAME_START = 0x80CC               # main_loop right after its VBL wait
DRAW_BOB, DRAW_BOB_DONE = 0xAB08, 0xAC40  # draw_bob's entry and its "drawn" exit (moveq #0,D0)
BOB_MINTERM = 0xAC16                    # the ori.w immediate the wrappers patch ($AC6E, $AC84)
VECTORS = {0x64: 0x101CC, 0x68: 0x101DC, 0x6C: 0x10266, 0x70: 0x1015C, 0x78: 0x1015E}
TRACE = {                               # name: (address, size, signed)
    "game_frame": (0xB00, 2, False), "player_x": (0x15D0, 2, True), "player_y": (0x15D4, 2, True),
    "state": (0x15E2, 2, False), "anim": (0x15DC, 2, False), "aim": (0x15DA, 2, False),
    "vy": (0x15E0, 2, True), "airborne": (0x15E6, 1, False), "camera_x": (0xB04, 2, True),
    "camera_y": (0xB06, 2, True), "joy": (0x802E, 1, False), "energy": (0x169A, 2, True),
}


RAM_BLOCK = (0xB00, 0x16EC)              # the game's variables (clear_game_vars $FE96)
GLOB_BLOCK = (0x8000, 0x8100)            # globals of the main code
CODE_BLOCKS = (                          # state kept inside the code area (tools/amigacov.py)
    (0x9626, 0x97B0),                    # level 1 spawn list
    (0xA562, 0xA828),                    # level 1 object list
    (0xB2D6, 0xB2DA), (0xB2FA, 0xB2FE),  # the camera's offsets (immediates obj32 patches)
    (0xC44A, 0xC44C),                    # the marker scan's step
    (0xC53C, 0xC53E),                    # the marker spawn interval (moveq immediate)
    (0xC598, 0xC59C),                    # the marker table's last entry
    (0x8C98, 0x8C9A),                    # RoboCop's state on the vehicle (an immediate)
    (0x9018, 0x9088),                    # level 1 special objects' records
    (0xB02A, 0xB02C),                    # player_move's joystick mask (moveq immediate)
    (0xF07E, 0xF080),                    # the explosions' frame divider
    (0xF826, 0xF828),                    # the palette flash countdown
)


def joy_value(keys: str) -> int:
    """JOY1DAT for the keys u d l r (fire is on the CIA)."""
    up, down, left, right = ("u" in keys), ("d" in keys), ("l" in keys), ("r" in keys)
    return (left << 9) | ((up ^ left) << 8) | (right << 1) | (down ^ right)


class GameBench(AmigaEmu):
    def __init__(self, extracted: Path, ram: Path, *, verbose: bool = False):
        super().__init__(extracted, verbose=verbose)
        self.ram_image = ram
        self.pulse_fire = False
        self.uc.hook_add(UC_HOOK_CODE, self._on_sentinel, None, SENTINEL, SENTINEL + 1)
        # the music player (MU1 at $18000, called from the interrupt) waits on audio hardware the
        # bench lacks: every call into it returns at once (the game logic does not depend on it)
        self.uc.hook_add(UC_HOOK_CODE, self._on_music, None, MUSIC[0], MUSIC[1] - 1)

    def _on_music(self, uc, address, size, user_data):
        sp = uc.reg_read(UC_M68K_REG_A7)
        uc.reg_write(UC_M68K_REG_PC, self.read_long(sp))
        uc.reg_write(UC_M68K_REG_A7, sp + 4)

    def _on_sentinel(self, uc, address, size, user_data):
        self._sentinel_hit = True
        uc.emu_stop()

    def call(self, addr: int, max_frames: int = 5000) -> None:
        """Runs the routine at addr (VBLs injected) until it returns."""
        sp = self.uc.reg_read(UC_M68K_REG_A7) - 4
        self.uc.mem_write(sp, struct.pack(">I", SENTINEL))
        self.uc.reg_write(UC_M68K_REG_A7, sp)
        self.uc.reg_write(UC_M68K_REG_PC, addr)
        self._sentinel_hit = False
        for _ in range(max_frames):
            self._run_one_frame()
            if self._sentinel_hit:
                return
        raise RuntimeError(f"${addr:05x} did not return in {max_frames} frames\n{self.regs_text()}")

    def _run_one_frame(self, insns: int = 40000) -> None:
        if self.pulse_fire:
            self.fire = (self.frame // 10) % 2 == 1     # (briefing and pictures wait for fire)
        budget = insns
        soft_at = insns // 2                            # the copper list's SOFT (level 1: frame count)
        while budget > 0 and not self._sentinel_hit:
            if soft_at is not None and budget <= soft_at:
                soft_at = None
                self.inject(1, 0x64, 0x0004)
            pc = self.uc.reg_read(UC_M68K_REG_PC)
            if pc == SENTINEL:
                self._sentinel_hit = True
                break
            chunk = min(budget, 5000)
            try:
                self.uc.emu_start(pc, 0xFFFFFFFE, 0, chunk)
            except UcError as e:
                if not self.do_rte():
                    raise RuntimeError(f"CPU fault in frame {self.frame}: {e}\n{self.regs_text()}") from e
                budget -= 100
                continue
            if self._pending_loader:
                self._pending_loader = False
                self._service_loader()
                budget -= 100
                continue
            budget -= chunk
        self.vpos = 0
        if not self._sentinel_hit:      # (no interrupt on top of a routine that returned)
            self.inject_vbl()
        self.frame += 1

    def boot_game(self) -> None:
        """The RAM image, the interrupt vectors, $FEDA and $FFC4 (a new game's set-up)."""
        self.uc.mem_write(0, self.ram_image.read_bytes())
        for vec, handler in VECTORS.items():
            self.uc.mem_write(vec, struct.pack(">I", handler))
        self.uc.reg_write(UC_M68K_REG_SR, 0x2000)
        self.uc.reg_write(UC_M68K_REG_A7, 0x80000)
        self.uc.reg_write(a_reg(6), 0xDFF002)   # the game keeps A6 on the custom chips (DMACONR)
        self.call(0xFEDA)                # hardware setup
        self.call(0xFFC4)                # level 1, score, lives

    def start_level(self) -> None:
        self.boot_game()
        self.pulse_fire = True
        self.call(0x871A)                # level_init (briefing and picture: fire pressed)
        self.pulse_fire = False
        self.fire = False
        self.uc.reg_write(UC_M68K_REG_A7, 0x80000)
        self.uc.reg_write(UC_M68K_REG_PC, 0x80C2)

    def read_var(self, addr: int, size: int, signed: bool) -> int:
        v = int.from_bytes(bytes(self.uc.mem_read(addr, size)), "big", signed=signed)
        return v

    def play(self, game_frames: int, script: list[tuple[int, int, str]], ram: bool = False,
             tele: list[tuple[int, int, int]] = (), god: bool = False, first: int = 0,
             sink=None, pokes: list[tuple[int, int, int, int]] = (), bobs=None) -> list[dict]:
        """Runs game frames from main_loop; returns the traced variables at each frame start (with
        ram: also the game's variables $B00-$16EB, globals $8000-$80FF and the state kept in the
        code area, CODE_BLOCKS, as hex). Test aids, applied after a frame's row is recorded (the
        MSX test builds do the same at the start of their game tick, tools/mkrom.py TELE / GOD):
        tele (game frame, x, y) puts RoboCop and the camera there; god keeps the energy ($169A
        100h) and the lives ($8034: 2) full and the level's end away ($16C4: 100h); pokes (game
        frame, address, value, size 1/2) write the game's variables. Rows are kept
        from game frame first on; with a sink (a text file) they are written there as JSON lines
        instead of kept. With bobs (a text file): per game frame a JSON line of its draw_bob calls
        [A2, D4, D0, D1 (world), minterm, drawn]."""
        hits = []
        count = [0]
        calls = []
        gf = [0]

        def word(reg: int) -> int:
            v = self.uc.reg_read(reg) & 0xFFFF
            return v - 0x10000 if v & 0x8000 else v

        def on_bob(uc, address, size, user_data):
            if address == DRAW_BOB:
                calls.append([self.uc.reg_read(a_reg(2)) & 0xFFFFFF, self.uc.reg_read(d_reg(4)) & 0xFFFF,
                              word(d_reg(0)), word(d_reg(1)), self.read_word(BOB_MINTERM), 0])
            elif address == DRAW_BOB_DONE and calls:
                calls[-1][5] = 1

        hb = None
        if bobs is not None:
            hb = self.uc.hook_add(UC_HOOK_CODE, on_bob, None, DRAW_BOB, DRAW_BOB_DONE)

        def on_frame(uc, address, size, user_data):
            n = count[0]
            count[0] += 1
            if bobs is not None:
                if n > 0 and n - 1 >= first:
                    bobs.write(json.dumps({"frame": n - 1, "game_frame": gf[0], "bobs": calls}) + "\n")
                calls.clear()
                gf[0] = self.read_var(0xB00, 2, False)
            keys = "".join(k for s, c, k in script if s <= n < s + c)
            self.joy = joy_value(keys)
            self.fire = "f" in keys
            if n >= first:
                row = {name: self.read_var(*spec) for name, spec in TRACE.items()} | {"keys": keys}
                if ram:
                    row["ram"] = bytes(uc.mem_read(RAM_BLOCK[0], RAM_BLOCK[1] - RAM_BLOCK[0])).hex()
                    row["glob"] = bytes(uc.mem_read(GLOB_BLOCK[0], GLOB_BLOCK[1] - GLOB_BLOCK[0])).hex()
                    row["code"] = {f"{lo:x}": bytes(uc.mem_read(lo, hi - lo)).hex() for lo, hi in CODE_BLOCKS}
                if sink is not None:
                    sink.write(json.dumps(row) + "\n")
                else:
                    hits.append(row)
            for f, x, y in tele:
                if f == n:
                    uc.mem_write(0x15D0, struct.pack(">h", x))
                    uc.mem_write(0x15D4, struct.pack(">h", y))
                    uc.mem_write(0x0B04, struct.pack(">h", max(0, min(0x8E0, x - 0x108))))
                    uc.mem_write(0x0B06, struct.pack(">h", max(0, y - 0x70)))
            for f, addr, v, size in pokes:
                if f == n:
                    uc.mem_write(addr, (v & (0xFF if size == 1 else 0xFFFF)).to_bytes(size, "big"))
            if god:
                uc.mem_write(0x169A, struct.pack(">h", 0x100))
                uc.mem_write(0x8034, struct.pack(">h", 2))
                uc.mem_write(0x16C4, struct.pack(">h", 0x100))
            if count[0] > game_frames:
                uc.emu_stop()
                self._sentinel_hit = True

        h = self.uc.hook_add(UC_HOOK_CODE, on_frame, None, GAME_FRAME_START, GAME_FRAME_START + 1)
        self._sentinel_hit = False
        while not self._sentinel_hit:
            self._run_one_frame()
        self.uc.hook_del(h)
        if hb is not None:
            self.uc.hook_del(hb)
        return hits[:game_frames - first]


# ---------------------------------------------------------------- Brainstorm (PUZL)
PUZL_PACKED, PUZL_ENTRY = 0x17080, 0x17100   # disk 1's copy, and where $124A6 decrunches it
DECRUNCH = 0x124A6                          # the game's ByteKiller decruncher (A0 source, A1 destination)
BRAINSTORM = 0x8382                         # load_level1's call (D0 = 2: PIC3), load_level2's (D0 = 4)
BRAINSTORM_RET = 0x83E4                     # $8382 right after its jsr $17100: D0 = the result
PUZL_FRAME_START = 0x171C2                  # PUZL's frame loop right after its wait for $802C ($171BA)
PUZL_VARS = (0xB00, 0xB22)                  # PUZL's variables (cleared by $17D1A)
PUZL_TABLE_PTR = 0x173D4                    # the board table it uses ($17448 after level 1, $175C0 after 2)
PUZL_BOARD, PUZL_BOARDS = 94, 4             # a board: start column, row, red chips, timer (BCD), tune,
                                            # then 11 x 8 cells (0 red chip, 1 black chip, 2-15 board;
                                            # + $10 once visited); 4 boards a table
PUZL_SPRITES = 0x17DE8                      # the cursor's sprite frames ($B12 points into them)
PUZL_CODE = ((0x17282, 0x17284),            # state kept in the code: the music divider,
             (0x1729A, 0x1729E),            # the face's graphics ($17298's lea),
             (0x173D4, 0x173D8),            # the board table,
             (0x17440, 0x17442),            # the board's tune (the moveq at $17440),
             (0x17B20, 0x17B24),            # the palette ($17AF0's lea)
             (0xFD92, 0xFDA2))              # and the main code's message slots ($FD76, $FDA2)
PUZL_TRACE = {                              # name: (address, size, signed)
    "game_frame": (0xB00, 2, False), "anim": (0xB02, 2, False), "sfx": (0xB04, 1, False),
    "board2": (0xB0A, 2, True), "col": (0xB0C, 2, False), "row": (0xB0E, 2, False),
    "reds": (0xB10, 2, False), "fail": (0xB16, 1, False), "done": (0xB17, 1, False),
    "fade": (0xB19, 1, False), "endc": (0xB1A, 2, False), "last_joy": (0xB1E, 1, False),
    "active": (0xB20, 1, False), "joy": (0x802E, 1, False), "timer": (0x804A, 2, False),
    "timeout": (0x804C, 1, False), "score": (0x8046, 4, False),
}
PUZL_RESULTS = {0: "solved", 1: "failed (memory malfunction)", 2: "out of time"}


class PuzlBench(GameBench):
    """Brainstorm (PUZL) on the bench: the module's docstring, "puzl"."""

    def __init__(self, extracted: Path, ram: Path, *, verbose: bool = False):
        super().__init__(extracted, ram, verbose=verbose)
        self.fix_sr = True              # (the decruncher's flags across interrupts: live_sr)
        self.sec = 0                    # CIA-B (the timer's second) after every sec-th PUZL frame
        self.cia_pending = False
        self.result: int | None = None  # $17100's D0 once it returned
        # The CIA-B handler's countdown ($1015E) tests each SBCD's borrow with BPL: the 68000 sets
        # N from the result's bit 7 (00 - 01 = 99: minus), Unicorn leaves N alone (1:00 went on
        # to 1:99). Its two BPLs take the branch from D0's bit 7 here.
        for at, plus, minus in ((0x10198, 0x101BA, 0x1019A), (0x101A6, 0x101B0, 0x101A8)):
            self.uc.hook_add(UC_HOOK_CODE, self._on_sbcd_bpl, (plus, minus), at, at + 1)

    def _on_sbcd_bpl(self, uc, address, size, targets):
        plus, minus = targets
        uc.reg_write(UC_M68K_REG_PC, minus if uc.reg_read(d_reg(0)) & 0x80 else plus)

    def inject_vbl(self) -> bool:
        done = super().inject_vbl()
        if self.cia_pending and self.inject(6, 0x78, 0x2000):     # (level 6 on top of the VBL's)
            self.cia_pending = False
        return done

    def _push_call(self, addr: int) -> None:
        sp = self.uc.reg_read(UC_M68K_REG_A7) - 4
        self.uc.mem_write(sp, struct.pack(">I", SENTINEL))
        self.uc.reg_write(UC_M68K_REG_A7, sp)
        self.uc.reg_write(UC_M68K_REG_PC, addr)
        self._sentinel_hit = False

    def setup(self, level: int = 1, via_8382: bool = False) -> None:
        """A new game's set-up, level 'level' done ($8050), then Brainstorm: with via_8382 the call
        of $8382 itself (intro text, picture, loader; fire pulsed until PUZL starts), else its
        steps from $8398 on: the copper and sprite pointers, PUZL by the loader, disk 1's copy
        decrunched by $124A6, and the call of $17100 (play() runs it)."""
        self.boot_game()
        self.uc.mem_write(0x8050, struct.pack(">H", level))
        if via_8382:
            self.uc.reg_write(d_reg(0), 2 * level)
            self.pulse_fire = True
            self._push_call(BRAINSTORM)
            return
        self.uc.mem_write(0x10320, struct.pack(">I", 0x1032E))
        self.uc.mem_write(0x8036, struct.pack(">I", 0x12558))
        self.load_file("PUZL")           # (level 1: disk 1's PUZL_13 at $17080; 2: disk 2's at $17100)
        if level < 2:
            self.uc.reg_write(a_reg(0), PUZL_PACKED)
            self.uc.reg_write(a_reg(1), PUZL_ENTRY)
            self.call(DECRUNCH)
        self.uc.mem_write(0x8036, struct.pack(">I", 0x12558))
        self._push_call(PUZL_ENTRY)

    def puzl_row(self, n: int, keys: str, ram: bool) -> dict:
        """The stage's variables at the start of PUZL frame n (with ram: the whole state as hex)."""
        row = {"frame": n} | {name: self.read_var(*spec) for name, spec in PUZL_TRACE.items()}
        table = self.read_long(PUZL_TABLE_PTR)
        grid = self.read_long(0xB06)
        row["grid_at"] = grid - table   # 6 + 94 x board
        row["grid"] = bytes(self.uc.mem_read(grid, 88)).hex() if table <= grid < table + 376 else ""
        row["spr"] = self.read_long(0xB12) - PUZL_SPRITES
        row["keys"] = keys
        if ram:
            row["vars"] = bytes(self.uc.mem_read(PUZL_VARS[0], PUZL_VARS[1] - PUZL_VARS[0])).hex()
            row["glob"] = bytes(self.uc.mem_read(GLOB_BLOCK[0], GLOB_BLOCK[1] - GLOB_BLOCK[0])).hex()
            row["boards"] = bytes(self.uc.mem_read(table, PUZL_BOARD * PUZL_BOARDS)).hex()
            row["code"] = {f"{lo:x}": bytes(self.uc.mem_read(lo, hi - lo)).hex() for lo, hi in PUZL_CODE}
        return row

    def play(self, pframes: int, script: list[tuple[int, int, str]], ram: bool = False,
             pokes: list[tuple[int, int, int, int]] = (), first: int = 0, sink=None, bot=None) -> list[dict]:
        """Runs PUZL frames until $17100 returns (self.result) or pframes have run; returns the
        rows (with sink, a text file: written there as JSON lines instead). Each frame's start:
        its keys applied (JOY1DAT, fire), the row recorded, then the pokes (frame, address, value,
        size 1/2/4) and, with sec, the CIA-B second due after the frame. bot(row) -> keys, when
        given, chooses the keys from the row instead of the script (rows are then recorded with
        the keys it chose)."""
        hits = []
        count = [0]
        self.result = None

        def on_start(uc, address, size, user_data):      # (via $8382: the fire pulses stop)
            self.pulse_fire = False
            self.fire = False

        def on_frame(uc, address, size, user_data):
            n = count[0]
            count[0] += 1
            keys = "".join(k for s, c, k in script if s <= n < s + c)
            if bot is not None:
                keys = bot(self.puzl_row(n, keys, False))
            self.joy = joy_value(keys)
            self.fire = "f" in keys
            if n >= first:
                row = self.puzl_row(n, keys, ram)
                if sink is not None:
                    sink.write(json.dumps(row) + "\n")
                else:
                    hits.append(row)
            for f, addr, v, size in pokes:
                if f == n:
                    uc.mem_write(addr, (v & ((1 << 8 * size) - 1)).to_bytes(size, "big"))
            if self.sec and (n + 1) % self.sec == 0:
                self.cia_pending = True
            if count[0] > pframes:
                uc.emu_stop()
                self._sentinel_hit = True

        def on_return(uc, address, size, user_data):     # (via $8382: after its jsr $17100)
            self.result = uc.reg_read(d_reg(0)) & 0xFFFF
            uc.emu_stop()
            self._sentinel_hit = True

        hooks = [self.uc.hook_add(UC_HOOK_CODE, on_frame, None, PUZL_FRAME_START, PUZL_FRAME_START + 1),
                 self.uc.hook_add(UC_HOOK_CODE, on_start, None, PUZL_ENTRY, PUZL_ENTRY + 1),
                 self.uc.hook_add(UC_HOOK_CODE, on_return, None, BRAINSTORM_RET, BRAINSTORM_RET + 1)]
        self._sentinel_hit = False
        while not self._sentinel_hit:
            self._run_one_frame()
        for h in hooks:
            self.uc.hook_del(h)
        if self.result is None and count[0] <= pframes:  # (the direct call's return: the sentinel)
            self.result = self.uc.reg_read(d_reg(0)) & 0xFFFF
        self.pframes_run = count[0]
        if sink is not None and self.result is not None:   # (the last line: how the stage ended)
            sink.write(json.dumps({"result": self.result, "frames": count[0]}) + "\n")
        return hits

    def puzl_screenshot(self, path: Path) -> None:
        """PUZL's screen: 5 planes of 320 x 176 at $2A320 ($1B80 apart), the copper list's colours
        ($17BFC: COLOR01-31 from $17C5E), the cursor's cell outlined in white."""
        from planar import decode_indices, render, write_png
        ram = bytes(self.uc.mem_read(0, CHIP_SIZE))
        pal = [(0, 0, 0)] + [rgb12_to_rgb24(struct.unpack_from(">H", ram, 0x17C5E + 4 * i)[0]) for i in range(31)]
        pal.append((255, 255, 255))
        idx = decode_indices(ram, 0x2A320, 320, 176, 5, "planes", row_bytes=40)
        col, row = self.read_word(0xB0C), self.read_word(0xB0E)
        if col < 11 and row < 8:
            x0, y0 = 16 + 16 * col, 16 + 16 * row
            for k in range(16):
                for x, y in ((x0 + k, y0), (x0 + k, y0 + 15), (x0, y0 + k), (x0 + 15, y0 + k)):
                    idx[y][x] = 32
        write_png(path, 640, 352, render(idx, pal, False, 2))


def parse_range(s: str) -> tuple[int, int]:
    lo, hi = s.split("-")
    return int(lo, 0), int(hi, 0)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("run", "game", "puzl"))
    ap.add_argument("--ram", type=Path, default=ROOT / "build" / "ram" / "level1_full.bin")
    ap.add_argument("--level", type=int, default=1, help="puzl: the level done ($8050): 1 or 2")
    ap.add_argument("--via-8382", action="store_true", help="puzl: run $8382 itself (intro text, picture, loader)")
    ap.add_argument("--pframes", type=int, default=600, help="puzl: PUZL frames to play at most")
    ap.add_argument("--poke", action="append", default=[], help="puzl: FRAME:ADDRESS:VALUE[:SIZE] after the row")
    ap.add_argument("--sec", type=int, default=0, help="puzl: the timer's second (CIA-B) after every N-th frame")
    ap.add_argument("--gframes", type=int, default=100, help="game: game frames to play")
    ap.add_argument("--joy", action="append", default=[], help="game, puzl: FRAME:COUNT:KEYS (u d l r f)")
    ap.add_argument("--trace", type=Path, help="game, puzl: JSON lines of the traced variables")
    ap.add_argument("--trace-ram", action="store_true", help="game, puzl: also the variables' blocks in the trace")
    ap.add_argument("--tele", action="append", default=[], help="game: GAMEFRAME:X:Y puts RoboCop and the camera there")
    ap.add_argument("--god", action="store_true", help="game: energy and lives kept full, the level never ends")
    ap.add_argument("--trace-from", type=int, default=0, help="game, puzl: trace rows from this frame on")
    ap.add_argument("--drive", type=Path, help="game (puzl: joystick and pokes): a tools/drivejoy.py file")
    ap.add_argument("--extracted", type=Path, default=ROOT / "build" / "extracted")
    ap.add_argument("--frames", type=int, default=300)
    ap.add_argument("--insns", type=int, default=40000, help="instructions per frame")
    ap.add_argument("--fire", action="append", default=[], help="FRAME:DURATION with fire pressed")
    ap.add_argument("--watch", action="append", default=[], help="write range to log, e.g. 0x3e810-0x40000")
    ap.add_argument("--dump", type=Path)
    ap.add_argument("--screenshot", type=Path)
    ap.add_argument("--bobs", type=Path, help="game: JSON lines of each game frame's draw_bob calls")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    if a.cmd == "puzl":
        bench = PuzlBench(a.extracted, a.ram, verbose=a.verbose)
        bench.sec = a.sec
        bench.setup(a.level, a.via_8382)
        script = []
        for j in a.joy:
            f, c, k = j.split(":")
            script.append((int(f), int(c), k))
        pokes = [tuple(int(v, 0) for v in (t.split(":") + ["1"])[:4]) for t in a.poke]
        if a.drive:                      # (the same input as the MSX's driven trace)
            joy_hex, _tele, _god, poke_s = (a.drive.read_text().split("\n") + ["", "", "", ""])[:4]
            for n, b in enumerate(bytes.fromhex(joy_hex.strip())):
                if b:
                    script.append((n, 1, "".join(k for k, m in zip("udlrf", (1, 2, 4, 8, 16)) if b & m)))
            pokes += [tuple(int(v, 0) for v in t.split(":")) for t in poke_s.split()]
        if a.trace:
            a.trace.parent.mkdir(parents=True, exist_ok=True)
            with a.trace.open("w") as sink:
                rows = bench.play(a.pframes, script, a.trace_ram, pokes, a.trace_from, sink)
        else:
            rows = bench.play(a.pframes, script, a.trace_ram, pokes, a.trace_from)
        for r in rows[:: max(1, len(rows) // 12)]:
            print({k: v for k, v in r.items() if k not in ("vars", "glob", "boards", "code", "grid")})
        res = bench.result
        print(f"VBL frames {bench.frame}, PUZL frames {bench.pframes_run}, board {bench.read_var(0xB0A, 2, True) // 2}, "
              + (f"result D0 = {res} ({PUZL_RESULTS.get(res, '?')})" if res is not None else "still playing"))
        if a.screenshot:
            bench.puzl_screenshot(a.screenshot)
        if a.dump:
            bench.dump(a.dump)
        return 0
    if a.cmd == "game":
        bench = GameBench(a.extracted, a.ram, verbose=a.verbose)
        bench.start_level()
        script = []
        for j in a.joy:
            f, c, k = j.split(":")
            script.append((int(f), int(c), k))
        tele = [tuple(int(v, 0) for v in t.split(":")) for t in a.tele]
        pokes = []
        if a.drive:                      # (the same input as the MSX's driven trace)
            joy_hex, tele_s, god_s, poke_s = (a.drive.read_text().split("\n") + ["", "", "", ""])[:4]
            for n, b in enumerate(bytes.fromhex(joy_hex.strip())):
                if b:
                    script.append((n, 1, "".join(k for k, m in zip("udlrf", (1, 2, 4, 8, 16)) if b & m)))
            tele += [tuple(int(v, 0) for v in t.split(":")) for t in tele_s.split()]
            a.god = a.god or god_s.strip() == "1"
            pokes = [tuple(int(v, 0) for v in t.split(":")) for t in poke_s.split()]
        bobs = a.bobs.open("w") if a.bobs else None
        if a.trace:
            a.trace.parent.mkdir(parents=True, exist_ok=True)
            with a.trace.open("w") as sink:
                rows = bench.play(a.gframes, script, a.trace_ram, tele, a.god, a.trace_from, sink, pokes, bobs)
        else:
            rows = bench.play(a.gframes, script, a.trace_ram, tele, a.god, a.trace_from, pokes=pokes, bobs=bobs)
        if bobs:
            bobs.close()
        for r in rows[:: max(1, len(rows) // 12)]:
            print({k: v for k, v in r.items() if k not in ("ram", "glob", "code")})
        print(f"VBL frames {bench.frame}, game frames {len(rows)}, level {bench.read_word(0x8050)}")
        if a.screenshot:
            bench.screenshot(a.screenshot)
        if a.dump:
            bench.dump(a.dump)
        return 0
    emu = AmigaEmu(a.extracted, verbose=a.verbose)
    emu.fire_script = [tuple(int(x) for x in f.split(":")) for f in a.fire]
    emu.watch = [parse_range(w) for w in a.watch]
    if emu.watch:
        def on_write(uc, access, address, size, value, user_data):
            pc = uc.reg_read(UC_M68K_REG_PC)
            emu.write_log.append((emu.frame, address, size, f"cpu@{pc:06x}"))
        for lo, hi in emu.watch:
            emu.uc.hook_add(UC_HOOK_MEM_WRITE, on_write, None, lo, hi - 1)
    emu.boot()
    try:
        emu.run_frames(a.frames, a.insns)
    finally:
        pc = emu.uc.reg_read(UC_M68K_REG_PC)
        print(f"frames={emu.frame} PC=${pc:06x} blits={emu.blitter.count} "
              f"unsupported={dict(emu.blitter.unsupported)} level={emu.read_word(0x8050)}")
        for fr, name, dest, ln in emu.loads:
            print(f"  load f{fr}: {name} -> ${dest:05x} (+{ln})")
        if emu.write_log:
            by_who = defaultdict(lambda: [0, None, None])
            for fr, addr, size, who in emu.write_log:
                e = by_who[who]
                e[0] += 1
                e[1] = addr if e[1] is None else min(e[1], addr)
                e[2] = addr if e[2] is None else max(e[2], addr)
            print("  writes in the watched ranges (source: n, range):")
            for who, (n, lo, hi) in sorted(by_who.items(), key=lambda kv: -kv[1][0])[:30]:
                print(f"    {who:24} {n:7d}  ${lo:06x}-${hi:06x}")
        if a.dump:
            emu.dump(a.dump)
        if a.screenshot:
            emu.screenshot(a.screenshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
