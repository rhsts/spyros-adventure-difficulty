"""Disassemble main.dol at a virtual address: python ppcdis.py ADDR [COUNT]"""
import struct, sys, capstone
dol = open("sys/main.dol", "rb").read()
off, addr, size = (struct.unpack(">18I", dol[o:o + 72]) for o in (0, 0x48, 0x90))
def v2f(va):
    for o, a, s in zip(off, addr, size):
        if a <= va < a + s:
            return o + va - a
md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
va, n = int(sys.argv[1], 16), int(sys.argv[2]) if len(sys.argv) > 2 else 24
f = v2f(va)
for i in md.disasm(dol[f:f + 4 * n], va):
    print(f"{i.address:08x}  {i.mnemonic:8} {i.op_str}")
