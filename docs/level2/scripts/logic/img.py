"""Read-only access to the level-2 RAM image (build/ram/level2_full.bin): big-endian words, longs, hex."""
import struct

IMG = ("/Users/rodrigogarcia/Library/Mobile Documents/com~apple~CloudDocs/Projects/VSCode Projects/"
       "msxports/build/ram/level2_full.bin")
RAM = open(IMG, "rb").read()


def w(a):
    return struct.unpack_from(">H", RAM, a)[0]


def sw(a):
    return struct.unpack_from(">h", RAM, a)[0]


def l(a):
    return struct.unpack_from(">I", RAM, a)[0]


def b(a):
    return RAM[a]


def hx(a, n):
    return RAM[a:a + n].hex()
