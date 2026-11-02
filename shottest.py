# Test helper: set the multiplier, unpause if needed, log HP drops and screenshot the first bites.
#   python shottest.py MULT SECONDS SHOTS
import struct, sys, time
import dolmem, kbinput, ssa_difficulty as s
mult, secs, shots = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
d = dolmem.Dolphin(); d.write(s.find_data(d), struct.pack(">I", mult))
a = d.mem1().copy(); time.sleep(0.5)
if int((a != d.mem1()).sum()) < 1000:
    kbinput.focus(); kbinput.press("F10", 0.12); time.sleep(1)
v = dolmem.view(d.mem1(), "u32"); p = s.find_player_hp(v)
rd = lambda x: int.from_bytes(d.read(x, 4), "big")
last, t0, taken = rd(p + 0x20), time.time(), 0
print("hp", last)
while time.time() - t0 < secs:
    hp = rd(p + 0x20)
    if hp != last:
        print(f"{time.time()-t0:5.2f}  {last} -> {hp}  (-{last - hp})", flush=True)
        if taken < shots and hp < last:
            time.sleep(0.1); kbinput.focus(); kbinput.press("F9", 0.1); taken += 1
        last = hp
