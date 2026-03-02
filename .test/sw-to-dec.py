from util import nios2_as, get_debug, require_symbols, hotpatch, get_regs
from csim import Nios2
import struct

# convert number to what we'd expect on hex display
def hexd(n):
    DIGIT = [0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d, 0x07, 0x7f, 0x67]
    n_digits = [int(x) for x in '%d'%n]     # individual digits
    n_bytes = list(map(lambda x: DIGIT[x], n_digits))   # map to 7seg values
    return struct.unpack('>I', bytes(n_bytes).rjust(4, b'\x00'))[0]       # combine into 32-bit value


def seg_to_rows(seg_byte):
    """Convert a 7-segment byte to 3 rows of ASCII art (3 chars wide each).

    Bit layout:
      bit 0 = a (top)        bit 4 = e (bottom-left)
      bit 1 = b (top-right)  bit 5 = f (top-left)
      bit 2 = c (bot-right)  bit 6 = g (middle)
      bit 3 = d (bottom)
    """
    a = (seg_byte >> 0) & 1
    b = (seg_byte >> 1) & 1
    c = (seg_byte >> 2) & 1
    d = (seg_byte >> 3) & 1
    e = (seg_byte >> 4) & 1
    f = (seg_byte >> 5) & 1
    g = (seg_byte >> 6) & 1
    return [
        ' _ ' if a else '   ',
        ('|' if f else ' ') + ('_' if g else ' ') + ('|' if b else ' '),
        ('|' if e else ' ') + ('_' if d else ' ') + ('|' if c else ' '),
    ]

def display_ascii(val32):
    """Return 3 lines of ASCII art for a 4-digit 7-seg display value.

    The 32-bit word maps as: bits 31:24 -> HEX3 (leftmost) ... bits 7:0 -> HEX0 (rightmost).
    """
    segs = [(val32 >> (8 * i)) & 0xff for i in range(3, -1, -1)]
    digit_rows = [seg_to_rows(s) for s in segs]
    return [' '.join(d[r] for d in digit_rows) for r in range(3)]


def check_sw(asm, tests):
    obj = nios2_as(asm.encode('utf-8'))
    cpu = Nios2(obj=obj)


    class MMIO(object):
        def __init__(self):
            self.cur_sw = 0
            self.cur_hex = 0

        # MMIO interfaces
        def write_hex(self, val):
            self.cur_hex = val
        def write_hex_byte(self, val):
            # TODO
            print('Error: This CPU does not support word-unaligned MMIO (e.g. stbio unsupported')
            return
        def write_upper_hex(self, val):
            self.cur_hex = (self.cur_hex & 0xffffffff) | (val << 32)

        def read_sw(self):
            return self.cur_sw

        def set_sw(self, n):
            self.cur_sw = n
        def get_hex(self):
            return self.cur_hex

    mmio = MMIO()

    # MMIO
    cpu.add_mmio(0xFF200040, mmio.read_sw)
    cpu.add_mmio(0xFF200020, mmio.write_hex)
    cpu.add_mmio(0xFF200021, mmio.write_hex_byte)
    cpu.add_mmio(0xFF200022, mmio.write_hex_byte)
    cpu.add_mmio(0xFF200023, mmio.write_hex_byte)
    cpu.add_mmio(0xFF200030, mmio.write_upper_hex)
    cpu.add_mmio(0xFF200031, mmio.write_hex_byte)
    cpu.add_mmio(0xFF200032, mmio.write_hex_byte)
    cpu.add_mmio(0xFF200033, mmio.write_hex_byte)

    passed = True

    for sw, expected in tests:
        mmio.set_sw(sw)
        
        # run a little bit...
        cpu.unhalt()
        instrs = cpu.run_until_halted(1000)
        if instrs < 1000:
            # cpu halted?
            print('Error: cpu halted after %d instructions' % instrs)

        val = mmio.get_hex()

        if val != expected:
            got_lines = display_ascii(val)
            exp_lines = display_ascii(expected)
            col_w = 24  # wide enough for label + 15-char display
            exp_label = f'Expected (0x{expected:08x}):'
            got_label = f'Got (0x{val:08x}):'
            print(f'Error: set switches to {sw}')
            print(f'  {exp_label:<{col_w}}  {got_label}')
            for el, gl in zip(exp_lines, got_lines):
                print(f'  {el:<{col_w}}  {gl}')
            passed = False
            

    err = cpu.get_error()
    if err != '':
        #print(err)
        pass     #don't print error because we reach the instruction limit a bunch...
    del cpu

    if passed:
        print('Passed')



import sys

# tests is a list of switch positions to test, e.g. '5,3,12'
# we automatically check/convert with hexd()
tests = [(int(x),hexd(int(x))) for x in sys.argv[1].split(',')]
check_sw(sys.stdin.read(), tests)
 
