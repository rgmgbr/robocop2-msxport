#!/usr/bin/env python3
"""The gun's opening at the start of a level: the port's own sound in place of the original's
effect 3 (player_move's 303h at $B2E, game frames 1Ch-40h; msx/plmove.asm asks for this one
instead, at the frame the original plays its first), the user's choice (2026-10-25): a
recording the user supplied, a motor starting (a 377 Hz hum sweeping to a 705-721 Hz whine at
the clunk, a grind, the whine again, a latch click ringing at 1.2 kHz, small clicks at 1.85-2.26
kHz), as tick-rate effect streams, 53 ticks of 20 ms from 33 ms of the recording on.

Designed per event (the "events" design of the synthesis panel, 2026-10-25) and fitted to the
recording's per-tick levels and third-octave spectra on the project's chip models (msxscc's
SCC, msxsound's PSG, openMSX's default balance): the user chose it by ear; two designs that
fitted the spectra better lost the motor's pitch (a buzz, "totalmente distorcido").
- With an SCC: three effects started together on music.asm's effect engine (fx_start: GUN_FX
  and the two after, Amiga channels 0-2): SCC 0 the motor (the hum's waveform at 377 Hz, then
  the sine on the whine's pitch), SCC 1 the gear (a comb at the whine / 11), SCC 2 the clunk's
  body, the thud and the pings; PSG voice A, channel 0's noise part, the clunk, the grind's
  rattle (noise, or noise gated by a tone) and the clicks. Four waveform loads in all (three at
  the start, the motor's hum to the sine at the clunk).
- Without one (msx/sndplay.asm sq_gun): voice A the motor and the pings, B every noise, C the
  clunk's body alone: its stream ends at tick 8, so an effect on channel 3 (an enemy's bullet)
  finds C idle, the voice it takes first.
The body is at a PSG level 11 voice's loudness (the old effect 3's loudest tick), the clunk ~13.

Records here: SCC (dur, volume, period N or None, waveform or None: a field not given keeps
its value, the first gives both), PSG (dur, volume, tone on, noise on, tone period or None,
noise period or None): the formats of tools/msxscc.py's and tools/msxsound.py's streams, as
music.asm and sndplay.asm read them (a silent PSG record is ctl 0).

Output (OUT_DIR, default build/msx): gun_scc.bin, tools/msxsccfx.py's sccfx.bin layout for
three effects (tools/mkrom.py appends them to sccfx.bin, effects 43-45, their waveforms after
its own); gun_psg.bin, three 16-bit offsets from its start, then the PSG voice streams A, B, C.
Each stream is read back and checked against its records tick by tick. Python 3 standard
library only.

usage: msxgun.py [OUT_DIR]
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAVE_LEN = 32

WAVES = [                               # (32 signed bytes each: music.asm fx_waves)
    # the sine: the whine, the clunk's body, the thud, the pings
    [12, 37, 60, 81, 98, 112, 122, 126, 126, 122, 112, 98, 81, 60, 37, 12, -12, -37, -60, -81,
     -98, -112, -122, -126, -126, -122, -112, -98, -81, -60, -37, -12],
    # the hum: harmonic 1, and harmonic 5 at -8 dB
    [104, 66, 42, 50, 72, 80, 53, 1, -44, -57, -42, -26, -36, -73, -114, -127, -104, -66, -42,
     -50, -72, -80, -53, -1, 44, 57, 42, 26, 36, 73, 114, 127],
    # the gear: harmonics 1-15 of the whine / 11 (11 left to SCC 0), the least crest
    [82, 72, -18, -118, 107, -112, 26, -57, 125, 13, -109, 126, -74, 13, 127, -90, -12, 111, -94,
     -80, 4, 45, 28, -25, -51, 87, -5, 34, -34, -65, -102, 46],
]

SCC_FX = [
    # Amiga channel 0: SCC 0: motor, PSG A: noise
    (0, [
        (2, 1, 296, 1), (1, 2, None, None), (2, 0, None, None), (1, 5, 303, 0),
        (1, 12, 250, None), (1, 4, 221, None), (1, 6, 187, None), (1, 6, 156, None),
        (1, 9, None, None), (1, 8, 154, None), (1, 8, 157, None), (2, 8, 155, None),
        (1, 6, None, None), (1, 7, 159, None), (1, 4, 155, None), (1, 3, 170, None),
        (2, 4, 181, None), (1, 4, 163, None), (4, 3, 156, None), (1, 3, 151, None),
        (1, 5, 156, None), (1, 3, 148, None), (1, 3, 156, None), (1, 5, 157, None),
        (1, 4, 158, None), (1, 6, 157, None)],
     [
        (2, 1, 0, 1, None, 24), (1, 6, 0, 1, None, 16), (1, 6, 0, 1, None, 31),
        (1, 4, 0, 1, None, None), (1, 10, 0, 1, None, 20), (1, 11, 0, 1, None, 28),
        (1, 9, 0, 1, None, 31), (1, 11, 1, 1, 375, None), (1, 11, 0, 1, None, None),
        (1, 9, 1, 1, 470, None), (1, 5, 1, 1, 310, None), (1, 8, 1, 1, 475, 24),
        (1, 12, 1, 1, 108, None), (1, 11, 0, 1, None, 28), (1, 9, 0, 1, None, 24),
        (1, 10, 0, 1, None, 28), (1, 9, 0, 1, None, None), (1, 8, 1, 1, None, 31),
        (1, 6, 0, 1, None, 20), (1, 9, 0, 1, None, 28), (1, 11, 1, 1, 327, 31),
        (1, 11, 1, 1, 471, None), (1, 9, 1, 1, None, None), (1, 5, 1, 1, 314, 24),
        (1, 9, 0, 1, None, 20), (1, 11, 1, 1, 304, 31), (1, 10, 1, 1, 315, None),
        (1, 10, 0, 1, None, 28), (1, 10, 1, 1, 108, 31), (1, 8, 0, 1, None, 20),
        (1, 9, 0, 1, None, 28), (1, 6, 0, 1, None, None), (1, 4, 1, 1, 1721, 24),
        (3, 1, 0, 1, None, 31), (1, 4, 0, 1, None, 20), (1, 9, 0, 1, None, None),
        (1, 5, 0, 1, None, None), (2, 5, 0, 1, None, 16), (1, 6, 0, 1, None, None),
        (1, 8, 0, 1, None, 20), (1, 8, 0, 1, None, 16), (1, 5, 0, 1, None, 24),
        (1, 3, 0, 1, None, None), (1, 5, 0, 1, None, 12), (1, 1, 0, 1, None, 6),
        (1, 2, 0, 1, None, None), (1, 8, 0, 1, None, 24), (1, 4, 0, 1, None, None),
        (1, 1, 0, 1, None, 20)]),
    # Amiga channel 1: SCC 1: gear
    (1, [
        (7, 0, 2441, 2), (1, 8, None, None), (1, 5, 2067, None), (1, 1, 1726, None),
        (1, 0, None, None), (1, 3, 1704, None), (1, 0, None, None), (1, 2, 1715, None),
        (2, 4, None, None), (1, 4, 1759, None), (1, 6, 1715, None), (1, 6, 1880, None),
        (2, 5, 2001, None), (1, 8, 1803, None), (1, 4, 1726, None), (3, 2, None, None),
        (1, 2, 1671, None), (1, 6, 1726, None), (1, 11, 1638, None), (1, 2, 1726, None),
        (1, 3, 1737, None), (1, 1, 1748, None), (1, 2, 1737, None), (1, 2, 1803, None)],
     None),
    # Amiga channel 2: SCC 2: clunk body, thud, ringing
    (2, [
        (6, 0, 446, 0), (1, 3, None, None), (1, 3, 519, None), (1, 2, 86, None),
        (1, 4, 62, None), (1, 1, 118, None), (1, 0, None, None), (1, 1, 122, None),
        (1, 4, 90, None), (1, 5, 107, None), (1, 3, 108, None), (1, 6, 126, None),
        (1, 4, 95, None), (1, 1, 73, None), (1, 1, 72, None), (1, 3, 65, None),
        (1, 5, 70, None), (1, 2, 107, None), (1, 0, None, None), (1, 3, 72, None),
        (1, 3, 76, None), (1, 5, None, None), (1, 0, None, None), (1, 1, None, None),
        (1, 3, 75, None), (1, 2, 105, None), (1, 2, 88, None), (1, 2, 89, None),
        (1, 1, 1720, None), (4, 0, None, None), (1, 5, 92, None), (1, 1, None, None),
        (2, 0, None, None), (1, 1, 53, None), (1, 2, 48, None), (1, 1, 164, None),
        (2, 0, None, None), (1, 1, 56, None), (2, 0, None, None), (1, 1, 59, None)],
     None),
]

PSG_VOICES = [
    # A: motor + ringing
    [
        (2, 3, 1, 0, 297, None), (1, 6, 1, 0, None, None), (2, 1, 1, 0, None, None),
        (1, 9, 1, 0, 304, None), (1, 12, 1, 0, 251, None), (1, 9, 1, 0, 222, None),
        (1, 10, 1, 0, 188, None), (1, 9, 1, 0, 157, None), (1, 11, 1, 0, None, None),
        (1, 11, 1, 0, 155, None), (1, 10, 1, 0, 158, None), (1, 10, 1, 0, 156, None),
        (1, 11, 1, 0, None, None), (1, 10, 1, 0, None, None), (1, 10, 1, 0, 160, None),
        (1, 9, 1, 0, 156, None), (1, 9, 1, 0, 153, None), (2, 9, 1, 0, 182, None),
        (1, 9, 1, 0, 164, None), (1, 4, 1, 0, 176, None), (1, 6, 1, 0, 157, None),
        (1, 4, 1, 0, None, None), (1, 5, 1, 0, None, None), (1, 7, 1, 0, 152, None),
        (1, 9, 1, 0, 157, None), (1, 7, 1, 0, 149, None), (1, 4, 1, 0, 178, None),
        (1, 9, 1, 0, 158, None), (1, 9, 1, 0, 159, None), (1, 9, 1, 0, 158, None),
        (4, 0, 0, 0, None, None), (1, 1, 1, 0, 59, None), (1, 8, 1, 0, 93, None),
        (1, 5, 1, 0, None, None), (1, 1, 1, 0, None, None), (1, 3, 1, 0, 38, None),
        (1, 6, 1, 0, 54, None), (1, 6, 1, 0, 49, None), (1, 5, 1, 0, 165, None),
        (1, 2, 1, 0, None, None), (1, 0, 0, 0, None, None), (1, 4, 1, 0, 57, None),
        (2, 0, 0, 0, None, None), (1, 5, 1, 0, 60, None), (1, 1, 1, 0, 61, None)],
    # B: noise
    [
        (2, 2, 0, 1, None, 24), (1, 6, 0, 1, None, 16), (1, 6, 0, 1, None, 31),
        (1, 3, 0, 1, None, None), (1, 9, 0, 1, None, 24), (1, 10, 1, 1, 501, None),
        (1, 10, 0, 1, None, 31), (1, 11, 1, 1, 375, None), (1, 11, 0, 1, None, None),
        (1, 8, 1, 1, 470, None), (1, 6, 1, 1, 465, None), (1, 6, 1, 1, 475, None),
        (1, 12, 1, 1, 108, 24), (1, 11, 0, 1, None, 31), (1, 10, 1, 1, None, None),
        (1, 11, 0, 1, None, None), (1, 10, 0, 1, None, 28), (1, 9, 1, 1, None, 31),
        (1, 9, 1, 1, 364, None), (1, 10, 0, 1, None, 24), (1, 12, 1, 1, 327, 31),
        (1, 12, 1, 1, 471, None), (1, 9, 1, 1, 314, None), (2, 9, 0, 1, None, 24),
        (1, 12, 1, 1, 304, 31), (1, 11, 1, 1, 315, None), (1, 12, 0, 1, None, 28),
        (1, 10, 0, 1, None, 24), (1, 9, 1, 1, 108, 31), (1, 9, 0, 1, None, None),
        (1, 6, 0, 1, None, None), (1, 5, 1, 1, 1721, 24), (1, 0, 0, 0, None, None),
        (2, 1, 0, 1, None, 31), (1, 4, 0, 1, None, 24), (1, 9, 0, 1, None, 20),
        (1, 5, 0, 1, None, None), (2, 5, 0, 1, None, 16), (1, 6, 0, 1, None, None),
        (1, 8, 0, 1, None, 20), (1, 8, 0, 1, None, 16), (1, 5, 0, 1, None, 24),
        (1, 2, 0, 1, None, None), (1, 5, 0, 1, None, 16), (1, 0, 0, 0, None, None),
        (1, 2, 0, 1, None, 6), (1, 8, 0, 1, None, 24), (1, 4, 0, 1, None, None),
        (1, 1, 0, 1, None, 20)],
    # C: clunk body
    [
        (5, 0, 0, 0, None, None), (1, 1, 1, 0, 373, None), (1, 10, 1, 0, None, None),
        (1, 9, 1, 0, 520, None)],
]


def ticks(recs: list[tuple]) -> int:
    return sum(r[0] for r in recs)


def scc_stream(recs: list[tuple]) -> bytes:
    """[dur, ctl (the volume; bit 4: a period word follows; bit 5: a waveform byte follows)
    ...] and 0."""
    out = bytearray()
    for d, vol, per, wav in recs:
        out += bytes([d, vol | (0x10 if per is not None else 0) | (0x20 if wav is not None else 0)])
        if per is not None:
            out += bytes([per & 0xFF, per >> 8])
        if wav is not None:
            out.append(wav)
    out.append(0)
    return bytes(out)


def psg_stream(recs: list[tuple]) -> bytes:
    """[dur, ctl (the volume; bit 4 tone on, 5 noise on; bit 6: a period word follows, bit 7:
    a noise byte follows) ...] and 0; a silent record is ctl 0."""
    out = bytearray()
    for d, vol, tone, noise, per, npd in recs:
        if vol == 0:
            out += bytes([d, 0])
            continue
        ctl = vol | (0x10 if tone else 0) | (0x20 if noise else 0)
        ctl |= (0x40 if per is not None else 0) | (0x80 if npd is not None else 0)
        out += bytes([d, ctl])
        if per is not None:
            out += bytes([per & 0xFF, per >> 8])
        if npd is not None:
            out.append(npd)
    out.append(0)
    return bytes(out)


def per_tick(recs: list[tuple], fields: int) -> list[tuple]:
    """The records' state per tick, the fields not given kept (from None)."""
    out, kept = [], [None] * fields
    for r in recs:
        d, rest = r[0], list(r[1:])
        for i in range(len(rest) - fields, len(rest)):
            if rest[i] is None:
                rest[i] = kept[i - (len(rest) - fields)]
            else:
                kept[i - (len(rest) - fields)] = rest[i]
        out += [tuple(rest)] * d
    return out


def read_scc(b: bytes, p: int) -> list[tuple]:
    """An SCC stream read back: per tick (volume, period, waveform)."""
    out, per, wav = [], None, None
    while b[p]:
        d, ctl = b[p], b[p + 1]
        p += 2
        if ctl & 0xC0:
            raise ValueError("SCC ctl bits 6-7")
        if not out and (ctl & 0x30) != 0x30:
            raise ValueError("the first SCC record gives no period or waveform")
        if ctl & 0x10:
            per = b[p] | b[p + 1] << 8
            p += 2
        if ctl & 0x20:
            wav = b[p]
            p += 1
        out += [(ctl & 15, per, wav)] * d
    return out


def read_psg(b: bytes, p: int) -> list[tuple]:
    """A PSG voice stream read back: per tick (volume, tone, noise, period, noise period)."""
    out, per, npd = [], None, None
    while b[p]:
        d, ctl = b[p], b[p + 1]
        p += 2
        if ctl & 0x40:
            per = b[p] | b[p + 1] << 8
            p += 2
        if ctl & 0x80:
            npd = b[p]
            p += 1
        vol, tone, noise = ctl & 15, int(bool(ctl & 0x10)), int(bool(ctl & 0x20))
        if vol == 0 and ctl:
            raise ValueError("a silent PSG record with ctl %02X" % ctl)
        if (tone and per is None) or (noise and npd is None):
            raise ValueError("a PSG record uses a period not given yet")
        out += [(vol, tone, noise, per, npd)] * d
    return out


def check_scc(recs: list[tuple], b: bytes, p: int) -> None:
    want = [(v, n, w) if v else (0, n, w) for v, n, w in per_tick(recs, 2)]
    got = read_scc(b, p)
    if [g[0] for g in got] != [w[0] for w in want] or any(
            g[1:] != w[1:] for g, w in zip(got, want) if w[0]):
        raise SystemExit("error: an SCC stream does not read back as its records")


def check_psg(recs: list[tuple], b: bytes, p: int) -> None:
    want = per_tick(recs, 2)
    got = read_psg(b, p)
    if len(got) != len(want):
        raise SystemExit("error: a PSG stream's length does not read back")
    for g, w in zip(got, want):
        vol, tone, noise, per, npd = w
        if g[0] != vol or (vol and (g[1], g[2]) != (tone, noise)) or (vol and tone and g[3] != per) \
                or (vol and noise and g[4] != npd):
            raise SystemExit("error: a PSG stream does not read back as its records")


def u24(v: int) -> bytes:
    return bytes([v & 0xFF, v >> 8 & 0xFF, v >> 16])


def scc_blob() -> bytes:
    """sccfx.bin's layout for the three effects: bytes 0-2 the waveform table's offset, byte 3
    the count; effect n (1-3) at 4 + 7 (n - 1): its Amiga channel, its SCC stream's offset, its
    PSG stream's (24-bit, 0 = none); the streams; the table."""
    head = 4 + 7 * len(SCC_FX)
    body = bytearray()
    entries = []
    for ch, scc, psg in SCC_FX:
        so = po = 0
        if scc is not None:
            so = head + len(body)
            body += scc_stream(scc)
        if psg is not None:
            po = head + len(body)
            body += psg_stream(psg)
        entries.append(bytes([ch]) + u24(so) + u24(po))
    table = bytes(v & 0xFF for w in WAVES for v in w)
    blob = u24(head + len(body)) + bytes([len(WAVES)]) + b"".join(entries) + bytes(body) + table
    for (ch, scc, psg), e in zip(SCC_FX, range(len(SCC_FX))):
        so = int.from_bytes(blob[4 + 7 * e + 1:4 + 7 * e + 4], "little")
        po = int.from_bytes(blob[4 + 7 * e + 4:4 + 7 * e + 7], "little")
        if scc is not None:
            check_scc(scc, blob, so)
            if max(w for _, _, _, w in scc if w is not None) >= len(WAVES):
                raise SystemExit("error: a waveform number past the table")
        if psg is not None:
            check_psg(psg, blob, po)
    return blob


def psg_blob() -> bytes:
    """Three 16-bit offsets from the start, then the voices' streams A, B, C."""
    streams = [psg_stream(v) for v in PSG_VOICES]
    out, off = bytearray(), 2 * len(streams)
    for s in streams:
        out += bytes([off & 0xFF, off >> 8])
        off += len(s)
    blob = bytes(out) + b"".join(streams)
    for i, v in enumerate(PSG_VOICES):
        check_psg(v, blob, blob[2 * i] | blob[2 * i + 1] << 8)
    return blob


def main(argv: list[str]) -> int:
    out = Path(argv[1]) if len(argv) > 1 else ROOT / "build" / "msx"
    out.mkdir(parents=True, exist_ok=True)
    for w in WAVES:
        if len(w) != WAVE_LEN or min(w) < -128 or max(w) > 127:
            raise SystemExit("error: a waveform is not 32 signed bytes")
    lengths = [ticks(s) for _, s, _ in SCC_FX] + [ticks(p) for _, _, p in SCC_FX if p] + [ticks(v) for v in PSG_VOICES]
    if max(lengths) > 53:
        raise SystemExit("error: a stream runs past the sound's 53 ticks")
    scc, psg = scc_blob(), psg_blob()
    (out / "gun_scc.bin").write_bytes(scc)
    (out / "gun_psg.bin").write_bytes(psg)
    print(f"gun: SCC machines {len(scc)} bytes (3 effects, {len(WAVES)} waveforms), "
          f"PSG alone {len(psg)} bytes (voices of {', '.join(str(ticks(v)) for v in PSG_VOICES)} ticks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
