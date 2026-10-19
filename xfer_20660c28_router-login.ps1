# router-login.ps1 — fills the Cellcom router login form. Creds are read from
# C:\Scarlett\home\router.py on this machine; never printed or transmitted.
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
$ws = New-Object -ComObject WScript.Shell
if (-not $ws.AppActivate('Gateways')) { Write-Output "NO_WINDOW"; exit 1 }
Start-Sleep -Milliseconds 800
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class M {
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
    [DllImport("user32.dll")] public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, UIntPtr dwExtraInfo);
}
"@
$w = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width
$h = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height
# Click the "User" field (centered form, ~46% down the screen)
[M]::SetCursorPos([int]($w*0.5), [int]($h*0.463))
Start-Sleep -Milliseconds 250
[M]::mouse_event(0x0002,0,0,0,[UIntPtr]::Zero)
[M]::mouse_event(0x0004,0,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 400
$lines = & 'C:\Python314\python.exe' -c "import sys; sys.path.insert(0, r'C:\Scarlett\home'); import router; print(router.USERNAME); print(router.PASSWORD)"
$user = $lines[0].Trim(); $pass = $lines[1].Trim()
$ws.SendKeys('^a')
Start-Sleep -Milliseconds 200
[System.Windows.Forms.Clipboard]::SetText($user)
$ws.SendKeys('^v')
Start-Sleep -Milliseconds 300
$ws.SendKeys('{TAB}')
Start-Sleep -Milliseconds 300
[System.Windows.Forms.Clipboard]::SetText($pass)
$ws.SendKeys('^v')
Start-Sleep -Milliseconds 300
$ws.SendKeys('{ENTER}')
Start-Sleep -Seconds 5
Write-Output "SUBMITTED"
