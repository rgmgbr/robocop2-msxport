"""A small Z80 interpreter (scratch, for checking the sound player's paths offline: documented
instructions only, flags S Z H P/V N C; the undocumented flag bits 3 and 5 are not modelled).
Decoding after C. Dinu's "Decoding Z80 opcodes" (x/y/z/p/q fields)."""
from __future__ import annotations

S, Z, H, PV, N, C = 0x80, 0x40, 0x10, 0x04, 0x02, 0x01
PARITY = [0] * 256
for _i in range(256):
    PARITY[_i] = PV if bin(_i).count("1") % 2 == 0 else 0


def sz(v: int) -> int:
    return (v & S) | (Z if v == 0 else 0)


class Halted(Exception):
    pass


class Z80:
    def __init__(self, bus):
        self.bus = bus                  # rb(a), wb(a, v), inp(p), outp(p, v)
        self.a = self.f = self.b = self.c = self.d = self.e = self.h = self.l = 0
        self.a_ = self.f_ = self.b_ = self.c_ = self.d_ = self.e_ = self.h_ = self.l_ = 0
        self.ix = self.iy = 0
        self.sp = 0xF380
        self.pc = 0
        self.iff = 0
        self.i = self.r = 0
        self.im = 1
        self.cycles = 0

    # ---- register pairs ----
    def get_rp(self, p: int, idx: int | None = None, af: bool = False) -> int:
        if p == 0:
            return self.b << 8 | self.c
        if p == 1:
            return self.d << 8 | self.e
        if p == 2:
            return self.hl_like(idx)
        return (self.a << 8 | self.f) if af else self.sp

    def set_rp(self, p: int, v: int, idx: int | None = None, af: bool = False) -> None:
        v &= 0xFFFF
        if p == 0:
            self.b, self.c = v >> 8, v & 0xFF
        elif p == 1:
            self.d, self.e = v >> 8, v & 0xFF
        elif p == 2:
            self.set_hl_like(idx, v)
        elif af:
            self.a, self.f = v >> 8, v & 0xFF
        else:
            self.sp = v

    def hl_like(self, idx: int | None) -> int:
        if idx is None:
            return self.h << 8 | self.l
        return self.ix if idx == 0 else self.iy

    def set_hl_like(self, idx: int | None, v: int) -> None:
        v &= 0xFFFF
        if idx is None:
            self.h, self.l = v >> 8, v & 0xFF
        elif idx == 0:
            self.ix = v
        else:
            self.iy = v

    # ---- memory helpers ----
    def fetch(self) -> int:
        v = self.bus.rb(self.pc)
        self.pc = (self.pc + 1) & 0xFFFF
        return v

    def fetch16(self) -> int:
        lo = self.fetch()
        return lo | self.fetch() << 8

    def rw(self, a: int) -> int:
        return self.bus.rb(a) | self.bus.rb((a + 1) & 0xFFFF) << 8

    def ww(self, a: int, v: int) -> None:
        self.bus.wb(a, v & 0xFF)
        self.bus.wb((a + 1) & 0xFFFF, (v >> 8) & 0xFF)

    def push(self, v: int) -> None:
        self.sp = (self.sp - 2) & 0xFFFF
        self.ww(self.sp, v)

    def pop(self) -> int:
        v = self.rw(self.sp)
        self.sp = (self.sp + 2) & 0xFFFF
        return v

    # ---- 8-bit registers by index (r table); 6 = (HL) / (IX+d) ----
    def get_r(self, k: int, idx: int | None, addr: int | None) -> int:
        if k == 6:
            return self.bus.rb(addr)
        if k == 7:
            return self.a
        if k == 4:
            return self.h if idx is None else (self.hl_like(idx) >> 8)
        if k == 5:
            return self.l if idx is None else (self.hl_like(idx) & 0xFF)
        return (self.b, self.c, self.d, self.e)[k]

    def set_r(self, k: int, v: int, idx: int | None, addr: int | None) -> None:
        v &= 0xFF
        if k == 6:
            self.bus.wb(addr, v)
        elif k == 7:
            self.a = v
        elif k == 4:
            if idx is None:
                self.h = v
            else:
                self.set_hl_like(idx, (self.hl_like(idx) & 0xFF) | v << 8)
        elif k == 5:
            if idx is None:
                self.l = v
            else:
                self.set_hl_like(idx, (self.hl_like(idx) & 0xFF00) | v)
        elif k == 0:
            self.b = v
        elif k == 1:
            self.c = v
        elif k == 2:
            self.d = v
        else:
            self.e = v

    # ---- ALU ----
    def add8(self, a: int, b: int, cy: int = 0) -> int:
        r = a + b + cy
        res = r & 0xFF
        f = sz(res) | (H if ((a & 0xF) + (b & 0xF) + cy) & 0x10 else 0)
        f |= PV if ((a ^ ~b) & (a ^ res) & 0x80) else 0
        f |= C if r > 0xFF else 0
        self.f = f
        return res

    def sub8(self, a: int, b: int, cy: int = 0) -> int:
        r = a - b - cy
        res = r & 0xFF
        f = sz(res) | N | (H if ((a & 0xF) - (b & 0xF) - cy) < 0 else 0)
        f |= PV if ((a ^ b) & (a ^ res) & 0x80) else 0
        f |= C if r < 0 else 0
        self.f = f
        return res

    def alu(self, y: int, v: int) -> None:
        a = self.a
        if y == 0:
            self.a = self.add8(a, v)
        elif y == 1:
            self.a = self.add8(a, v, self.f & C)
        elif y == 2:
            self.a = self.sub8(a, v)
        elif y == 3:
            self.a = self.sub8(a, v, self.f & C)
        elif y == 4:
            self.a = a & v
            self.f = sz(self.a) | H | PARITY[self.a]
        elif y == 5:
            self.a = a ^ v
            self.f = sz(self.a) | PARITY[self.a]
        elif y == 6:
            self.a = a | v
            self.f = sz(self.a) | PARITY[self.a]
        else:
            self.sub8(a, v)

    def inc8(self, v: int) -> int:
        r = (v + 1) & 0xFF
        self.f = (self.f & C) | sz(r) | (H if (v & 0xF) == 0xF else 0) | (PV if v == 0x7F else 0)
        return r

    def dec8(self, v: int) -> int:
        r = (v - 1) & 0xFF
        self.f = (self.f & C) | sz(r) | N | (H if (v & 0xF) == 0 else 0) | (PV if v == 0x80 else 0)
        return r

    def rot(self, y: int, v: int) -> int:
        cy = self.f & C
        if y == 0:      # RLC
            c = v >> 7
            r = ((v << 1) | c) & 0xFF
        elif y == 1:    # RRC
            c = v & 1
            r = (v >> 1) | (c << 7)
        elif y == 2:    # RL
            c = v >> 7
            r = ((v << 1) | cy) & 0xFF
        elif y == 3:    # RR
            c = v & 1
            r = (v >> 1) | (cy << 7)
        elif y == 4:    # SLA
            c = v >> 7
            r = (v << 1) & 0xFF
        elif y == 5:    # SRA
            c = v & 1
            r = (v >> 1) | (v & 0x80)
        elif y == 6:    # SLL
            c = v >> 7
            r = ((v << 1) | 1) & 0xFF
        else:           # SRL
            c = v & 1
            r = v >> 1
        self.f = sz(r) | PARITY[r] | (C if c else 0)
        return r

    def cond(self, y: int) -> bool:
        f = self.f
        return (not f & Z, bool(f & Z), not f & C, bool(f & C), not f & PV, bool(f & PV),
                not f & S, bool(f & S))[y]

    # ---- execution ----
    def step(self) -> None:
        self.op_pc = self.pc
        op = self.fetch()
        self.r = (self.r + 1) & 0x7F
        if op == 0xDD or op == 0xFD:
            idx = 0 if op == 0xDD else 1
            op = self.fetch()
            if op == 0xCB:
                d = self.fetch()
                d = d - 256 if d > 127 else d
                addr = (self.hl_like(idx) + d) & 0xFFFF
                self.cb(self.fetch(), idx, addr)
                return
            if op in (0xDD, 0xFD, 0xED):
                raise NotImplementedError("prefix %02X after DD/FD at %04X" % (op, self.pc))
            self.main(op, idx)
            return
        if op == 0xCB:
            self.cb(self.fetch(), None, None)
            return
        if op == 0xED:
            self.ed(self.fetch())
            return
        self.main(op, None)

    def ea(self, idx: int | None) -> int:
        """(HL), or (IX+d)/(IY+d) with d fetched."""
        if idx is None:
            return self.h << 8 | self.l
        d = self.fetch()
        d = d - 256 if d > 127 else d
        return (self.hl_like(idx) + d) & 0xFFFF

    def main(self, op: int, idx: int | None) -> None:
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        p, q = y >> 1, y & 1
        if x == 0:
            if z == 0:
                if y == 0:
                    return
                if y == 1:
                    self.a, self.a_ = self.a_, self.a
                    self.f, self.f_ = self.f_, self.f
                    return
                d = self.fetch()
                d = d - 256 if d > 127 else d
                if y == 2:
                    self.b = (self.b - 1) & 0xFF
                    if self.b:
                        self.pc = (self.pc + d) & 0xFFFF
                elif y == 3 or self.cond(y - 4):
                    self.pc = (self.pc + d) & 0xFFFF
                return
            if z == 1:
                if q == 0:
                    self.set_rp(p, self.fetch16(), idx)
                else:
                    a = self.hl_like(idx)
                    b = self.get_rp(p, idx)
                    r = a + b
                    self.f = (self.f & (S | Z | PV)) | (H if ((a & 0xFFF) + (b & 0xFFF)) > 0xFFF else 0) \
                        | (C if r > 0xFFFF else 0)
                    self.set_hl_like(idx, r)
                return
            if z == 2:
                if q == 0:
                    if p == 0:
                        self.bus.wb(self.b << 8 | self.c, self.a)
                    elif p == 1:
                        self.bus.wb(self.d << 8 | self.e, self.a)
                    elif p == 2:
                        self.ww(self.fetch16(), self.hl_like(idx))
                    else:
                        self.bus.wb(self.fetch16(), self.a)
                else:
                    if p == 0:
                        self.a = self.bus.rb(self.b << 8 | self.c)
                    elif p == 1:
                        self.a = self.bus.rb(self.d << 8 | self.e)
                    elif p == 2:
                        self.set_hl_like(idx, self.rw(self.fetch16()))
                    else:
                        self.a = self.bus.rb(self.fetch16())
                return
            if z == 3:
                self.set_rp(p, self.get_rp(p, idx) + (1 if q == 0 else -1), idx)
                return
            if z in (4, 5):
                addr = self.ea(idx) if y == 6 else None
                v = self.get_r(y, idx, addr)
                self.set_r(y, self.inc8(v) if z == 4 else self.dec8(v), idx, addr)
                return
            if z == 6:
                addr = self.ea(idx) if y == 6 else None
                self.set_r(y, self.fetch(), idx, addr)
                return
            # z == 7
            a, cy = self.a, self.f & C
            if y == 0:
                c = a >> 7
                self.a = ((a << 1) | c) & 0xFF
            elif y == 1:
                c = a & 1
                self.a = (a >> 1) | (c << 7)
            elif y == 2:
                c = a >> 7
                self.a = ((a << 1) | cy) & 0xFF
            elif y == 3:
                c = a & 1
                self.a = (a >> 1) | (cy << 7)
            if y <= 3:
                self.f = (self.f & (S | Z | PV)) | (C if c else 0)
                return
            if y == 4:
                self.daa()
            elif y == 5:
                self.a ^= 0xFF
                self.f |= H | N
            elif y == 6:
                self.f = (self.f & (S | Z | PV)) | C
            else:
                self.f = (self.f & (S | Z | PV)) | (H if cy else 0) | (0 if cy else C)
            return
        if x == 1:
            if op == 0x76:
                raise Halted()
            if y == 6:
                addr = self.ea(idx)
                self.bus.wb(addr, self.get_r(z, None, None))
            elif z == 6:
                addr = self.ea(idx)
                self.set_r(y, self.bus.rb(addr), None, None)
            else:
                self.set_r(y, self.get_r(z, idx, None), idx, None)
            return
        if x == 2:
            addr = self.ea(idx) if z == 6 else None
            self.alu(y, self.get_r(z, idx, addr))
            return
        # x == 3
        if z == 0:
            if self.cond(y):
                self.pc = self.pop()
            return
        if z == 1:
            if q == 0:
                self.set_rp(p, self.pop(), idx, af=True)
            elif p == 0:
                self.pc = self.pop()
            elif p == 1:
                self.b, self.b_ = self.b_, self.b
                self.c, self.c_ = self.c_, self.c
                self.d, self.d_ = self.d_, self.d
                self.e, self.e_ = self.e_, self.e
                self.h, self.h_ = self.h_, self.h
                self.l, self.l_ = self.l_, self.l
            elif p == 2:
                self.pc = self.hl_like(idx)
            else:
                self.sp = self.hl_like(idx)
            return
        if z == 2:
            a = self.fetch16()
            if self.cond(y):
                self.pc = a
            return
        if z == 3:
            if y == 0:
                self.pc = self.fetch16()
            elif y == 2:
                self.bus.outp(self.fetch(), self.a)
            elif y == 3:
                self.a = self.bus.inp(self.fetch())
            elif y == 4:
                v = self.rw(self.sp)
                self.ww(self.sp, self.hl_like(idx))
                self.set_hl_like(idx, v)
            elif y == 5:
                self.d, self.h = self.h, self.d
                self.e, self.l = self.l, self.e
            elif y == 6:
                self.iff = 0
            elif y == 7:
                self.iff = 1
            else:
                raise NotImplementedError("CB in main")
            return
        if z == 4:
            a = self.fetch16()
            if self.cond(y):
                self.push(self.pc)
                self.pc = a
            return
        if z == 5:
            if q == 0:
                self.push(self.get_rp(p, idx, af=True))
            elif p == 0:
                a = self.fetch16()
                self.push(self.pc)
                self.pc = a
            else:
                raise NotImplementedError("prefix in main")
            return
        if z == 6:
            self.alu(y, self.fetch())
            return
        self.push(self.pc)
        self.pc = y * 8

    def daa(self) -> None:
        a, f = self.a, self.f
        corr, cy = 0, f & C
        if (f & H) or (a & 0xF) > 9:
            corr |= 0x06
        if cy or a > 0x99:
            corr |= 0x60
            cy = C
        if f & N:
            hf = H if (f & H) and (a & 0xF) < 6 else 0
            a = (a - corr) & 0xFF
        else:
            hf = H if (a & 0xF) > 9 else 0
            a = (a + corr) & 0xFF
        self.a = a
        self.f = sz(a) | PARITY[a] | (f & N) | hf | cy

    def cb(self, op: int, idx: int | None, addr: int | None) -> None:
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        if idx is not None:
            z_eff, a = 6, addr
        else:
            z_eff, a = z, (self.h << 8 | self.l) if z == 6 else None
        v = self.get_r(z_eff, None, a)
        if x == 0:
            r = self.rot(y, v)
            self.set_r(z_eff, r, None, a)
        elif x == 1:
            bit = v & (1 << y)
            self.f = (self.f & C) | H | (Z | PV if not bit else 0) | (S if y == 7 and bit else 0)
        elif x == 2:
            self.set_r(z_eff, v & ~(1 << y), None, a)
        else:
            self.set_r(z_eff, v | (1 << y), None, a)

    def ed(self, op: int) -> None:
        x, y, z = op >> 6, (op >> 3) & 7, op & 7
        p, q = y >> 1, y & 1
        if x == 1:
            if z == 0:
                v = self.bus.inp(self.c)
                if y != 6:
                    self.set_r(y, v, None, None)
                self.f = (self.f & C) | sz(v) | PARITY[v]
            elif z == 1:
                self.bus.outp(self.c, 0 if y == 6 else self.get_r(y, None, None))
            elif z == 2:
                hl, rr, cy = self.h << 8 | self.l, self.get_rp(p), self.f & C
                if q == 0:
                    r = hl - rr - cy
                    res = r & 0xFFFF
                    f = N | (C if r < 0 else 0) | (H if ((hl & 0xFFF) - (rr & 0xFFF) - cy) < 0 else 0)
                    f |= PV if ((hl ^ rr) & (hl ^ res) & 0x8000) else 0
                else:
                    r = hl + rr + cy
                    res = r & 0xFFFF
                    f = (C if r > 0xFFFF else 0) | (H if ((hl & 0xFFF) + (rr & 0xFFF) + cy) > 0xFFF else 0)
                    f |= PV if ((hl ^ ~rr) & (hl ^ res) & 0x8000) else 0
                f |= (S if res & 0x8000 else 0) | (Z if res == 0 else 0)
                self.f = f
                self.h, self.l = res >> 8, res & 0xFF
            elif z == 3:
                a = self.fetch16()
                if q == 0:
                    self.ww(a, self.get_rp(p))
                else:
                    self.set_rp(p, self.rw(a))
            elif z == 4:
                self.a = self.sub8(0, self.a)
            elif z == 5:
                self.pc = self.pop()
            elif z == 6:
                self.im = (0, 0, 1, 2, 0, 0, 1, 2)[y]
            else:
                if y == 0:
                    self.i = self.a
                elif y == 1:
                    self.r = self.a
                elif y == 2:
                    self.a = self.i
                    self.f = (self.f & C) | sz(self.a) | (PV if self.iff else 0)
                elif y == 3:
                    self.a = self.r
                    self.f = (self.f & C) | sz(self.a) | (PV if self.iff else 0)
                else:
                    raise NotImplementedError("RRD/RLD")
            return
        if x == 2 and z <= 3 and y >= 4:
            if z != 0 and z != 3:
                raise NotImplementedError("block %02X" % op)
            step = 1 if y in (4, 6) else -1
            repeat = y >= 6
            while True:
                hl, de, bc = self.h << 8 | self.l, self.d << 8 | self.e, self.b << 8 | self.c
                if z == 0:      # LDI / LDD / LDIR / LDDR
                    self.bus.wb(de, self.bus.rb(hl))
                    de = (de + step) & 0xFFFF
                    hl = (hl + step) & 0xFFFF
                    bc = (bc - 1) & 0xFFFF
                    self.h, self.l, self.d, self.e = hl >> 8, hl & 0xFF, de >> 8, de & 0xFF
                    self.b, self.c = bc >> 8, bc & 0xFF
                    self.f = (self.f & (S | Z | C)) | (PV if bc else 0)
                    if not repeat or not bc:
                        return
                else:           # OUTI / OUTD / OTIR / OTDR
                    self.bus.outp(self.c, self.bus.rb(hl))
                    hl = (hl + step) & 0xFFFF
                    self.h, self.l = hl >> 8, hl & 0xFF
                    self.b = (self.b - 1) & 0xFF
                    self.f = (self.f & C) | N | (Z if self.b == 0 else 0)
                    if not repeat or not self.b:
                        return
        raise NotImplementedError("ED %02X" % op)
