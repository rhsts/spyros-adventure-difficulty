"""Minimal extractor for Skylanders Imaginators IGA v11 archives (.pak).

  python iga.py ARCHIVE                 list files
  python iga.py ARCHIVE PATTERN OUTDIR  extract files whose name contains PATTERN

Layout (little endian): header with file count at 0xC, block counts at 0x1C
(large u32) / 0x20 (medium u16) / 0x24 (small u8), name table offset at 0x28.
File entries (16 bytes) start after the per-file hashes: offset u32, ordinal,
length u32, mode u32 (low 24 bits = first block index). Each block holds up to
0x8000 bytes; a set top bit means compressed: u16 size + raw deflate.
"""
import os, struct, sys, zlib

BLOCK = 0x8000


def read(path):
    d = open(path, "rb").read()
    n = struct.unpack_from("<I", d, 0xC)[0]
    nl, nm, ns = struct.unpack_from("<III", d, 0x1C)
    nt = struct.unpack_from("<Q", d, 0x28)[0]
    entries = 0x38 + 4 * n
    tables = entries + 16 * n
    large = struct.unpack_from(f"<{nl}I", d, tables)
    med = struct.unpack_from(f"<{nm}H", d, tables + 4 * nl)
    small = d[tables + 4 * nl + 2 * nm: tables + 4 * nl + 2 * nm + ns]
    files = []
    for i in range(n):
        off, = struct.unpack_from("<I", d, entries + 16 * i)
        ln, mode = struct.unpack_from("<II", d, entries + 16 * i + 8)
        name = d[nt + struct.unpack_from("<I", d, nt + 4 * i)[0]:].split(b"\0")[0].decode()
        files.append((name, off, ln, mode))

    def data(off, ln, mode):
        nblocks = (ln + BLOCK - 1) // BLOCK
        sectors = (ln + 0x7FF) // 0x800
        # the table a file uses depends on how many sectors it spans
        tab, top, mask = (small, 0x80, 0x7F) if sectors <= 0x7F else \
                         (med, 0x8000, 0x7FFF) if sectors <= 0x7FFF else (large, 0x80000000, 0x7FFFFFFF)
        first = mode & 0xFFFFFF
        out = b""
        for k in range(nblocks):
            v = tab[first + k]
            p = off + (v & mask) * 0x800
            want = min(BLOCK, ln - k * BLOCK)
            if v & top:
                size = struct.unpack_from("<H", d, p)[0]
                out += zlib.decompress(d[p + 2: p + 2 + size], -15)[:want]
            else:
                out += d[p: p + want]
        return out
    return files, data


if __name__ == "__main__":
    files, data = read(sys.argv[1])
    if len(sys.argv) == 2:
        for name, off, ln, mode in files:
            print(ln, name)
    else:
        os.makedirs(sys.argv[3], exist_ok=True)
        for name, off, ln, mode in files:
            if sys.argv[2].lower() in name.lower():
                out = os.path.join(sys.argv[3], name.split("/Output/")[-1].replace("/", "_"))
                open(out, "wb").write(data(off, ln, mode))
                print("wrote", out)
