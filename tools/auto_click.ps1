param([Parameter(Mandatory = $true)][int]$ProcessId)
Add-Type @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public class C {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
  [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, IntPtr e);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }

  public static List<IntPtr> TkWindows(uint target) {
    List<IntPtr> found = new List<IntPtr>();
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      uint pid; GetWindowThreadProcessId(h, out pid);
      if (pid == target && IsWindowVisible(h)) {
        StringBuilder c = new StringBuilder(64); GetClassName(h, c, 64);
        if (c.ToString().StartsWith("Tk")) {
          RECT r; GetClientRect(h, out r);
          if ((r.R - r.L) > 50 && (r.B - r.T) > 50) found.Add(h);
        }
      }
      return true;
    }, IntPtr.Zero);
    return found;
  }
  public static string Title(IntPtr h) {
    StringBuilder t = new StringBuilder(256); GetWindowText(h, t, 256);
    return t.ToString();
  }
  public static void Click(int x, int y) {
    SetCursorPos(x, y);
    System.Threading.Thread.Sleep(150);
    mouse_event(0x0002, 0, 0, 0, IntPtr.Zero);
    System.Threading.Thread.Sleep(60);
    mouse_event(0x0004, 0, 0, 0, IntPtr.Zero);
  }
  public static int[] Origin(IntPtr h) {
    POINT p = new POINT(); ClientToScreen(h, ref p);
    RECT r; GetClientRect(h, out r);
    return new int[] { p.X, p.Y, r.R - r.L, r.B - r.T };
  }
}
"@
$wins = [C]::TkWindows([uint32]$ProcessId)
Write-Output ("Tk windows: " + $wins.Count)
foreach ($w in $wins) {
  $o = [C]::Origin($w)
  Write-Output ("  [" + $o[2] + "x" + $o[3] + "] title=" + [C]::Title($w))
}
if ($wins.Count -eq 0) { Write-Output "FAIL: no Tk window"; exit 1 }

# 出发点弹窗是较小的那个（500x500 画布 + 标签 + 按钮）
$dlg = $null
foreach ($w in $wins) {
  $o = [C]::Origin($w)
  if ($o[2] -lt 800) { $dlg = $w; break }
}
if ($dlg -eq $null) { Write-Output "FAIL: dialog not found"; exit 1 }
$o = [C]::Origin($dlg)
Write-Output ("dialog client: " + $o[0] + "," + $o[1] + " " + $o[2] + "x" + $o[3])
[C]::SetForegroundWindow($dlg) | Out-Null
Start-Sleep -Milliseconds 400

Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap($o[2], $o[3])
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($o[0], $o[1], 0, 0, (New-Object System.Drawing.Size($o[2], $o[3])))
$g.Dispose()
$bx = 0; $by = 0; $cnt = 0
for ($y = 0; $y -lt 300; $y += 2) {
  for ($x = 0; $x -lt $bmp.Width; $x += 2) {
    $c = $bmp.GetPixel($x, $y)
    if ($c.B -gt 150 -and $c.B -gt $c.R + 80 -and $c.B -gt $c.G + 80) {
      $bx += $x; $by += $y; $cnt++
    }
  }
}
$bmp.Dispose()
if ($cnt -eq 0) { Write-Output "FAIL: no blue cell found in dialog"; exit 2 }
$cx = $o[0] + [int]($bx / $cnt)
$cy = $o[1] + [int]($by / $cnt)
Write-Output ("clicking blue cell at " + $cx + "," + $cy + " samples=" + $cnt)
[C]::Click($cx, $cy)
Start-Sleep -Seconds 2

$wins2 = [C]::TkWindows([uint32]$ProcessId)
Write-Output ("after click, Tk windows: " + $wins2.Count)
foreach ($w in $wins2) {
  $o2 = [C]::Origin($w)
  Write-Output ("  [" + $o2[2] + "x" + $o2[3] + "] title=" + [C]::Title($w))
}
if ($wins2.Count -lt 1) { Write-Output "FAIL: main window missing"; exit 3 }
Write-Output "OK"
