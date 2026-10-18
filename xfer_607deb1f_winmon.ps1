Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinMon {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
}
"@
$logFile = "C:\Scarlett\wallpaper-daynight\winmon.log"
$lastHwnd = [IntPtr]::Zero
$endTime = (Get-Date).AddMinutes(10)
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') monitor started" | Out-File $logFile -Append -Encoding utf8
while ((Get-Date) -lt $endTime) {
    $hwnd = [WinMon]::GetForegroundWindow()
    if ($hwnd -ne $lastHwnd -and $hwnd -ne [IntPtr]::Zero) {
        $sb = New-Object System.Text.StringBuilder 256
        [WinMon]::GetWindowText($hwnd, $sb, 256) | Out-Null
        $pid = 0
        [WinMon]::GetWindowThreadProcessId($hwnd, [ref]$pid) | Out-Null
        try { $pname = (Get-Process -Id $pid -ErrorAction Stop).ProcessName } catch { $pname = "?" }
        "$(Get-Date -Format 'HH:mm:ss.fff') FOREGROUND: hwnd=$hwnd title='$($sb.ToString())' pid=$pid proc=$pname" | Out-File $logFile -Append -Encoding utf8
        $lastHwnd = $hwnd
    }
    Start-Sleep -Milliseconds 200
}
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') monitor done" | Out-File $logFile -Append -Encoding utf8
