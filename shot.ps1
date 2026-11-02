# Screenshot the Dolphin game window (or another window by title prefix) to a PNG.
# Usage: powershell -File shot.ps1 OUT.png [TitlePrefix]
param([string]$Out, [string]$Title = "Dolphin 2609a |")
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System; using System.Text; using System.Runtime.InteropServices;
public class Win { public delegate bool CB(IntPtr h, IntPtr p);
[DllImport("user32.dll")] public static extern bool EnumWindows(CB cb, IntPtr p);
[DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
[DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
[DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
[DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
[DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
public struct RECT { public int L, T, R, B; }
public static IntPtr Find(string t) { IntPtr f = IntPtr.Zero; EnumWindows((h, q) => { var s = new StringBuilder(256); GetWindowText(h, s, 256); if (IsWindowVisible(h) && s.ToString().StartsWith(t)) { f = h; return false; } return true; }, IntPtr.Zero); return f; } }
'@
[Win]::SetProcessDPIAware() | Out-Null
$h = [Win]::Find($Title)
if ($h -eq [IntPtr]::Zero) { Write-Output "window not found"; exit 1 }
[Win]::SetForegroundWindow($h) | Out-Null; Start-Sleep -Milliseconds 300
$r = New-Object Win+RECT; [Win]::GetWindowRect($h, [ref]$r) | Out-Null
$bmp = New-Object System.Drawing.Bitmap ([int]($r.R - $r.L)), ([int]($r.B - $r.T))
[System.Drawing.Graphics]::FromImage($bmp).CopyFromScreen($r.L, $r.T, 0, 0, $bmp.Size)
$small = New-Object System.Drawing.Bitmap $bmp, ([int]($bmp.Width / 2)), ([int]($bmp.Height / 2))
$small.Save($Out)
