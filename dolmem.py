"""Read/write emulated Wii MEM1 inside a running Dolphin, plus a value scanner.

Usage:
  python dolmem.py info
  python dolmem.py scan u32|u16|f32 VALUE      start a new candidate list
  python dolmem.py next VALUE                  keep candidates now equal to VALUE
  python dolmem.py snap u32|u16|f32            start with every value (unknown value)
  python dolmem.py dec|inc|same                keep candidates that went down/up/stayed
  python dolmem.py list                     show candidates (max 50)
  python dolmem.py read ADDR [N]               hex dump N bytes at 0x80xxxxxx
  python dolmem.py write u32|u16|f32 ADDR VALUE
"""
import ctypes, ctypes.wintypes as wt, os, struct, subprocess, sys
import numpy as np

MEM1_SIZE = 0x1800000          # 24 MB on Wii, mapped in a 32 MB view
GAME_ID = b"SSPP52"
k32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wt.DWORD), ("PartitionId", wt.WORD),
                ("RegionSize", ctypes.c_size_t), ("State", wt.DWORD),
                ("Protect", wt.DWORD), ("Type", wt.DWORD)]


def dolphin_pid():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Dolphin.exe", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        if line.startswith('"Dolphin.exe"'):
            return int(line.split('","')[1])
    sys.exit("Dolphin.exe is not running")


class Dolphin:
    def __init__(self):
        self.h = k32.OpenProcess(0x0438, False, dolphin_pid())  # VM_READ|VM_WRITE|VM_OPERATION|QUERY_INFO
        if not self.h:
            sys.exit(f"OpenProcess failed: {ctypes.get_last_error()}")
        self.base = self._find_mem1()

    def _find_mem1(self):
        mbi, addr = MBI(), 0
        while k32.VirtualQueryEx(self.h, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
            # MEM1 is a MEM_MAPPED (0x40000) committed view that starts with the game ID
            if mbi.Type == 0x40000 and mbi.State == 0x1000 and mbi.RegionSize >= MEM1_SIZE:
                if self._raw(mbi.BaseAddress, 6) == GAME_ID:
                    return mbi.BaseAddress
            addr = (mbi.BaseAddress or 0) + mbi.RegionSize
        sys.exit("MEM1 not found - is the game booted?")

    def _raw(self, host, n):
        buf, got = ctypes.create_string_buffer(n), ctypes.c_size_t()
        ok = k32.ReadProcessMemory(self.h, ctypes.c_void_p(host), buf, n, ctypes.byref(got))
        return buf.raw[:got.value] if ok else b""

    def read(self, addr, n):
        return self._raw(self.base + (addr & 0x1FFFFFF), n)

    def write(self, addr, data):
        got = ctypes.c_size_t()
        k32.WriteProcessMemory(self.h, ctypes.c_void_p(self.base + (addr & 0x1FFFFFF)),
                               data, len(data), ctypes.byref(got))

    def mem1(self):
        return np.frombuffer(self.read(0x80000000, MEM1_SIZE), dtype=np.uint8)


TYPES = {"u32": (">u4", 4, int), "u16": (">u2", 2, int), "f32": (">f4", 4, float)}
STATE = os.environ.get("DOLMEM_STATE", "scan_state.npz")  # separate files for parallel scans


def view(mem, t):
    dt, size, _ = TYPES[t]
    # aligned values only; the game stores fields aligned
    return mem[: len(mem) // size * size].view(dt)


def match(vals, t, value):
    return np.abs(vals - value) < 0.01 if t == "f32" else vals == value


def main(argv):
    cmd = argv[0] if argv else "info"
    d = Dolphin()
    if cmd == "info":
        print(f"MEM1 host base {d.base:#x}, game {d.read(0x80000000, 6).decode()}")
    elif cmd == "scan":
        t, value = argv[1], TYPES[argv[1]][2](argv[2])
        vals = view(d.mem1(), t)
        idx = np.nonzero(match(vals, t, value))[0]
        np.savez(STATE, idx=idx, t=t, prev=vals[idx])
        print(f"{len(idx)} candidates")
    elif cmd == "next":
        s = np.load(STATE)
        t = str(s["t"])
        value = TYPES[t][2](argv[1])
        vals = view(d.mem1(), t)[s["idx"]]
        ok = match(vals, t, value)
        idx = s["idx"][ok]
        np.savez(STATE, idx=idx, t=t, prev=vals[ok])
        print(f"{len(idx)} candidates")
        if len(idx) <= 50:
            main(["list"])
    elif cmd == "snap":
        # unknown value: remember all values, then filter with dec/inc/same
        t = argv[1]
        vals = view(d.mem1(), t)
        np.savez(STATE, idx=np.arange(len(vals)), t=t, prev=vals)
        print(f"{len(vals)} candidates")
    elif cmd in ("dec", "inc", "same"):
        s = np.load(STATE)
        t, idx = str(s["t"]), s["idx"]
        prev = s["prev"]
        cur = view(d.mem1(), t)[idx]
        ok = {"dec": cur < prev, "inc": cur > prev, "same": cur == prev}[cmd]
        if t == "f32":
            ok &= np.isfinite(cur) & (np.abs(cur) < 1e6)
        np.savez(STATE, idx=idx[ok], t=t, prev=cur[ok])
        print(f"{ok.sum()} candidates")
        if ok.sum() <= 50:
            main(["list"])
    elif cmd == "list":
        s = np.load(STATE)
        t = str(s["t"])
        vals = view(d.mem1(), t)
        for i in s["idx"][:50]:
            print(f"{0x80000000 + int(i) * TYPES[t][1]:#010x}  {vals[i]}")
    elif cmd == "read":
        addr, n = int(argv[1], 16), int(argv[2], 0) if len(argv) > 2 else 0x100
        data = d.read(addr, n)
        for o in range(0, len(data), 16):
            row = data[o:o + 16]
            fl = " ".join(f"{x:9.3f}" for x in struct.unpack(f">{len(row)//4}f", row[: len(row) // 4 * 4]))
            print(f"{addr + o:08x}  {row.hex(' ', 4)}  {fl}")
    elif cmd == "write":
        t, addr, value = argv[1], int(argv[2], 16), TYPES[argv[1]][2](argv[3])
        d.write(addr, np.array([value], dtype=TYPES[t][0]).tobytes())
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
