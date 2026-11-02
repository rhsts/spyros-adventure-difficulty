# Test helper: set the damage-taken multiplier, then log the player's real HP and HUD HP.
#   python hittest.py QUARTERS SECONDS
import struct, sys, time
import dolmem, ssa_difficulty as s
q, secs = int(sys.argv[1]), float(sys.argv[2])
d = dolmem.Dolphin()
d.write(s.find_data(d), struct.pack(">I", q))
v = dolmem.view(d.mem1(), "u32")
p = s.find_player_hp(v)
huds = s.find_vars(v, s.HUD_ID)
rd = lambda a: int.from_bytes(d.read(a, 4), "big")
last, t0 = None, time.time()
while time.time() - t0 < secs:
    cur = (rd(p + 0x20), max(rd(a) for a in huds))
    if cur != last:
        print(f"{time.time() - t0:6.3f}  real {cur[0]:4}  hud {cur[1]:4}", flush=True)
        last = cur
