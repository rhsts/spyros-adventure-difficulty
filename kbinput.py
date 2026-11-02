"""Let a script play: map Wiimote 1 + Nunchuk to the keyboard, press keys, put the PS4 mapping back.

  python kbinput.py apply      back up WiimoteNew.ini, switch Wiimote 1 to keyboard (Dolphin closed)
  python kbinput.py restore    put the backup back (Dolphin closed)
  python kbinput.py press KEY SECONDS [KEY SECONDS ...]   hold keys in turn, e.g. press J 0.1 W 1.5

Keyboard layout: A=J, B=K, 1=1, 2=2, -=O, +=P, Home=H, D-pad=arrows,
Nunchuk stick=WASD, C=Q, Z=E.
"""
import ctypes, os, shutil, sys, time

CFG = os.path.expandvars(r"%APPDATA%\Dolphin Emulator\Config\WiimoteNew.ini")
BACKUP = CFG + ".ps4.bak"
MAP = {
    "Device": "DInput/0/Keyboard Mouse",
    "Buttons/A": "`J`", "Buttons/B": "`K`", "Buttons/1": "`1`", "Buttons/2": "`2`",
    "Buttons/-": "`O`", "Buttons/+": "`P`", "Buttons/Home": "`H`",
    "D-Pad/Up": "`UP`", "D-Pad/Down": "`DOWN`", "D-Pad/Left": "`LEFT`", "D-Pad/Right": "`RIGHT`",
    "Nunchuk/Buttons/C": "`Q`", "Nunchuk/Buttons/Z": "`E`",
    "Nunchuk/Stick/Up": "`W`", "Nunchuk/Stick/Down": "`S`",
    "Nunchuk/Stick/Left": "`A`", "Nunchuk/Stick/Right": "`D`",
    # Wii pointer follows the mouse over the render window (menus like "Do you want to travel?")
    "IR/Up": "`Cursor Y-`", "IR/Down": "`Cursor Y+`", "IR/Left": "`Cursor X-`", "IR/Right": "`Cursor X+`",
}
VK = {"UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27, "F9": 0x78, "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73, "F10": 0x79}


def apply():
    if not os.path.exists(BACKUP):           # never overwrite the original backup
        shutil.copyfile(CFG, BACKUP)
    out, section = [], None
    for line in open(BACKUP).read().splitlines():
        if line.startswith("["):
            section = line
            if section == "[Wiimote1]":         # keys the PS4 profile does not have (pointer)
                present = {l.split(" = ")[0] for l in open(BACKUP).read().splitlines()}
                out.append(line)
                out += [f"{k} = {v}" for k, v in MAP.items() if k not in present]
                continue
        key = line.split(" = ")[0]
        if section == "[Wiimote1]" and key in MAP:
            line = f"{key} = {MAP[key]}"
        elif section == "[Wiimote1]" and key.startswith(("IMU", "Nunchuk/IMU")):
            continue                            # no motion from the keyboard
        out.append(line)
    open(CFG, "w").write("\n".join(out) + "\n")


def restore():
    shutil.copyfile(BACKUP, CFG)
    os.remove(BACKUP)


def focus(prefix="Dolphin 2609a |"):
    """Bring the game window to the front. Windows only allows that right after a
    keypress, so tap Alt first."""
    u = ctypes.windll.user32
    found = []
    buf = ctypes.create_unicode_buffer(256)

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        u.GetWindowTextW(hwnd, buf, 256)
        if buf.value.startswith(prefix) and u.IsWindowVisible(hwnd):
            found.append(hwnd)
            return False
        return True
    u.EnumWindows(cb, 0)
    if found:
        u.keybd_event(0x12, 0, 0, 0)
        u.keybd_event(0x12, 0, 2, 0)
        u.SetForegroundWindow(found[0])
        time.sleep(0.2)
    return bool(found)


def press(key, seconds):
    vk = VK.get(key) or ord(key.upper())
    scan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    ctypes.windll.user32.keybd_event(vk, scan, 0, 0)
    time.sleep(seconds)
    ctypes.windll.user32.keybd_event(vk, scan, 2, 0)   # KEYEVENTF_KEYUP


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "apply":
        apply()
    elif cmd == "restore":
        restore()
    elif cmd == "press":
        args = sys.argv[2:]
        # Hotkeys (F1..F12) need the window in front. Game buttons do not (background
        # input is on), and the Alt tap that focus() needs can eat the next key.
        if any(k.startswith("F") and k[1:].isdigit() for k in args[::2]):
            focus()
        for k, s in zip(args[::2], args[1::2]):
            press(k, float(s))
