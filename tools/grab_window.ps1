param(
    [Parameter(Mandatory = $true)][int]$ProcessId,
    [string]$Out = "tools\shots\live.png"
)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public class W {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }

  public static List<IntPtr> Find(uint target) {
    List<IntPtr> found = new List<IntPtr>();
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      uint pid; GetWindowThreadProcessId(h, out pid);
      if (pid == target && IsWindowVisible(h)) {
        StringBuilder sb = new StringBuilder(256);
        GetClassName(h, sb, 256);
        if (sb.ToString().StartsWith("Tk")) found.Add(h);
      }
      return true;
    }, IntPtr.Zero);
    return found;
  }
}
"@

$dir = Split-Path -Parent $Out
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$ready = Join-Path $dir "Ready.txt"
if (Test-Path $ready) { Remove-Item $ready -Force }
$t0 = Get-Date
while (-not (Test-Path $ready)) {
    Start-Sleep -Milliseconds 200
    if (((Get-Date) - $t0).TotalSeconds -gt 40) { Write-Output "timeout waiting Ready"; exit 1 }
}
Start-Sleep -Milliseconds 900

$hs = [W]::Find([uint32]$ProcessId)
Write-Output ("Tk windows found: " + $hs.Count)
if ($hs.Count -eq 0) { exit 2 }

$best = $hs[0]
$bestArea = 0
foreach ($h in $hs) {
    $r = New-Object W+RECT
    [W]::GetClientRect($h, [ref]$r) | Out-Null
    $area = ($r.R - $r.L) * ($r.B - $r.T)
    if ($area -gt $bestArea) { $bestArea = $area; $best = $h }
}
[W]::SetForegroundWindow($best) | Out-Null
Start-Sleep -Milliseconds 700

$r = New-Object W+RECT
[W]::GetClientRect($best, [ref]$r) | Out-Null
$p = New-Object W+POINT
[W]::ClientToScreen($best, [ref]$p) | Out-Null
$w = $r.R - $r.L; $ht = $r.B - $r.T
Write-Output ("client rect: " + $p.X + "," + $p.Y + " " + $w + "x" + $ht)

$bmp = New-Object System.Drawing.Bitmap($w, $ht)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($p.X, $p.Y, 0, 0, (New-Object System.Drawing.Size($w, $ht)))
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output ("saved " + $Out)
