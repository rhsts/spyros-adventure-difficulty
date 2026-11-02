# Test helper: set every script int with ID to VALUE (where it currently equals OLD), 1x multiplier,
# then log the player's HP drops for a few seconds.  python trydmg.py ID OLD VALUE SECONDS
import struct, sys, time
import numpy as np
import dolmem, ssa_difficulty as s
vid, old, new, secs = int(sys.argv[1], 16), int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
d = dolmem.Dolphin()
d.write(s.find_data(d), struct.pack(">I", 256))
v = dolmem.view(d.mem1(), "u32")
i = np.nonzero(v == vid)[0]; i = i[(i >= 2) & (v[i - 2] == s.INT_VT)]
addrs = [0x80000000 + 4 * int(x) + 0x18 for x in i if v[x + 6] == old]
for a in addrs: d.write(a, struct.pack(">I", new))
print("changed", len(addrs), "vars")
p = s.find_player_hp(v); rd = lambda a: int.from_bytes(d.read(a, 4), "big")
last, t0 = rd(p + 0x20), time.time()
while time.time() - t0 < secs:
    hp = rd(p + 0x20)
    if hp != last: print(f"{time.time()-t0:5.2f}  {last} -> {hp}  ({last - hp})"); last = hp
for a in addrs: d.write(a, struct.pack(">I", old))
d.write(s.find_data(d), struct.pack(">I", 0))
print("restored")
