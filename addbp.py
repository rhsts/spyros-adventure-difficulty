# Add a Dolphin breakpoint (log only) through the debugger UI.
#   python addbp.py ADDRESS              memory breakpoint on writes
#   python addbp.py ADDRESS CONDITION    instruction breakpoint with a condition, e.g. "r0 == 11"
import ctypes, subprocess, sys, time
u = ctypes.windll.user32; u.SetProcessDPIAware()
addr = sys.argv[1]
cond = sys.argv[2] if len(sys.argv) > 2 else None
ps = r'''
Add-Type -AssemblyName UIAutomationClient, UIAutomationTypes
$ae = [System.Windows.Automation.AutomationElement]; $S = [System.Windows.Automation.TreeScope]
$main = $ae::RootElement.FindFirst($S::Children, (New-Object System.Windows.Automation.PropertyCondition($ae::NameProperty, "Dolphin 2609a")))
$c = New-Object System.Windows.Automation.AndCondition((New-Object System.Windows.Automation.PropertyCondition($ae::NameProperty, "New")), (New-Object System.Windows.Automation.PropertyCondition($ae::ControlTypeProperty, [System.Windows.Automation.ControlType]::Button)))
$r = $main.FindFirst($S::Descendants, $c).Current.BoundingRectangle
"{0} {1}" -f [int]($r.X + $r.Width / 2), [int]($r.Y + $r.Height / 2)
'''
x, y = map(int, subprocess.run(["powershell", "-Command", ps], capture_output=True, text=True).stdout.split())
class R(ctypes.Structure): _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
def click(px, py):
    u.SetCursorPos(px, py); time.sleep(0.1); u.mouse_event(2, 0, 0, 0, 0); u.mouse_event(4, 0, 0, 0, 0); time.sleep(0.3)
def key(vk, up=False): u.keybd_event(vk, 0, 2 if up else 0, 0)
main = u.FindWindowW(None, "Dolphin 2609a")
key(0x12); key(0x12, True); u.SetForegroundWindow(main); time.sleep(0.3)
click(x, y)
for _ in range(20):
    h = u.FindWindowW(None, "New Breakpoint")
    if h: break
    time.sleep(0.2)
r = R(); u.GetWindowRect(h, ctypes.byref(r))
def typ(text):
    key(0x11); key(0x41); key(0x41, True); key(0x11, True); key(0x2E); key(0x2E, True)
    for ch in text:
        s = u.VkKeyScanW(ord(ch)); vk, shift = s & 0xFF, (s >> 8) & 1
        if shift: key(0x10)
        key(vk); key(vk, True)
        if shift: key(0x10, True)
        time.sleep(0.03)
if cond:
    click(r.l + 36, r.t + 60)         # Instruction Breakpoint
    click(r.l + 220, r.t + 94)        # its Address field
    typ(addr)
    click(r.l + 220, r.t + 352)       # Action condition field
    typ(cond)
else:
    click(r.l + 36, r.t + 150)        # Memory Breakpoint
    click(r.l + 220, r.t + 216)       # Address field
    typ(addr)
click(r.l + 36, r.t + 376)            # Write to Log
key(0x0D); key(0x0D, True); time.sleep(0.4)
print("added" if not u.FindWindowW(None, "New Breakpoint") else "dialog still open")
