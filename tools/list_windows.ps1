param([Parameter(Mandatory = $true)][int]$ProcessId)
Add-Type @"
using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
public class V {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, IntPtr l);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }

  public static List<string> List(uint target) {
    List<string> found = new List<string>();
    EnumWindows(delegate(IntPtr h, IntPtr l) {
      uint pid; GetWindowThreadProcessId(h, out pid);
      if (pid == target && IsWindowVisible(h)) {
        StringBuilder t = new StringBuilder(256), c = new StringBuilder(64);
        GetWindowText(h, t, 256); GetClassName(h, c, 64);
        RECT r; GetWindowRect(h, out r);
        found.Add(c.ToString() + " | " + (r.R - r.L) + "x" + (r.B - r.T)
                  + " at " + r.L + "," + r.T + " | title=" + t.ToString());
      }
      return true;
    }, IntPtr.Zero);
    return found;
  }
}
"@
$list = [V]::List([uint32]$ProcessId)
Write-Output ("可见顶层窗口数: " + $list.Count)
foreach ($item in $list) { Write-Output ("  " + $item) }
