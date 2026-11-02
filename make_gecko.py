"""Build the damage-multiplier Gecko code for Spyro's Adventure (SSPP52 Rev 3).

Hooks the shared script-int setter (80034784: stw r0,0x20(r3)). When the
variable being set is the Skylander's HP (ID HP_ID and flag word PLAYER_FLAG)
and the new value is lower, the loss is scaled by a multiplier/256. The
multiplier sits inside the code after the magic word 'SSA2', so
ssa_difficulty.py can change it while the game runs.

The white damage number still shows the unscaled hit: the game reads it, like
the HP subtraction, straight from the attacker's damage variable (a chompy's
is script int 0x111d6850; setting it to 30 made both the HP loss and the
number 30). The per-hit variables 0x12fcddae ("incoming damage", player 1/2)
and 0x12fcf880 (generic temp slot) also carry the damage, but scaling them
(code v3, 'SSA3') changed neither the HP loss nor the number.
"""
import capstone

HOOK = 0x80034784
# HP_ID is not HP-specific: the scripts reuse it for ~38 slots per level (enemy
# HP, but also counters, timers and floats). Scaling those corrupts game logic,
# so only the player's HP is touched. The low bits of the flag word count
# references: at rest the player's HP reads 0x03400002 (all others
# 0x03400001), and while a script writes it one more reference is held, so the
# hook sees 0x03400003 (measured: 0x03400002 never matched a hit). The HUD
# copy 0x12fcc7dc and the stats copy 0x12fc5244 only mirror it.
HP_ID = 0x12fc5b28
PLAYER_FLAG = 0x03400003
# 'SSA2': version 2 counts the multiplier in 1/256 steps (version 1, 'SSAD',
# used quarters). The marker keeps old code and old save states from being
# fed values in the wrong unit.
MAGIC = 0x53534132
ONE = 256  # multiplier value for 1.0x


def words(taken=ONE):
    """taken: multiplier in 1/256 steps (256 = 1.0x) for damage the Skylander takes."""
    return [
        0x7D4802A6,                     # mflr  r10
        0x48000015,                     # bl    +20 (over the 4 data words)
        MAGIC,                          # .long 'SSA2'
        taken,                          # +4  .long multiplier
        HP_ID,                          # +8  .long HP variable ID
        PLAYER_FLAG,                    # +12 .long flag word of the player's HP
        0x7D6802A6,                     # mflr  r11          -> &MAGIC
        0x7D4803A6,                     # mtlr  r10
        0x81830008,                     # lwz   r12, 8(r3)   variable ID
        0x814B0008,                     # lwz   r10, 8(r11)  HP ID
        0x7C0C5000,                     # cmpw  r12, r10
        0x40820044,                     # bne   done
        0x81830004,                     # lwz   r12, 4(r3)   variable flag word
        0x814B000C,                     # lwz   r10, 12(r11) player flag
        0x7C0C5000,                     # cmpw  r12, r10
        0x40820034,                     # bne   done         not the player
        0x81830020,                     # lwz   r12, 0x20(r3) old HP
        0x7C006000,                     # cmpw  r0, r12
        0x40800028,                     # bge   done         not a loss
        0x814B0004,                     # lwz   r10, 4(r11)  multiplier
        0x7D606050,                     # subf  r11, r0, r12 loss = old - new
        0x7D6B51D6,                     # mullw r11, r11, r10
        0x7D6B4670,                     # srawi r11, r11, 8  (/256)
        0x7C0B6050,                     # subf  r0, r11, r12 new = old - loss*mult
        0x7C006040,                     # cmplw r0, r12      unsigned: catches < 0 and overflow
        0x4081000C,                     # ble   done         0 <= new <= old
        0x38000000,                     # li    r0, 0
        0x60000000,                     # nop                (keeps the word count even)
        0x90030020,                     # done: stw r0, 0x20(r3) (original)
        0x00000000,                     # branch back, filled by the code handler
    ]


def gecko(taken=ONE):
    w = words(taken)
    assert len(w) % 2 == 0
    lines = [f"C2{HOOK & 0x1FFFFFF:06X} {len(w) // 2:08X}"]
    lines += [f"{w[i]:08X} {w[i + 1]:08X}" for i in range(0, len(w), 2)]
    return "\n".join(lines)


if __name__ == "__main__":
    md = capstone.Cs(capstone.CS_ARCH_PPC, capstone.CS_MODE_32 | capstone.CS_MODE_BIG_ENDIAN)
    for i, x in enumerate(words()):
        ins = next(md.disasm(x.to_bytes(4, "big"), 0x1000 + 4 * i), None)
        print(f"{0x1000 + 4 * i:x} {x:08X} {ins.mnemonic + ' ' + ins.op_str if ins else '(data)'}")
    print()
    print(gecko())
