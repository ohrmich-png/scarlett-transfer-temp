# Scarlett: laptop bootstrap — Tailscale + OpenSSH Server (mirrors the desktop recipe, 2026-10-20).
# Run: right-click -> "Run with PowerShell". It re-launches itself elevated (one UAC click),
# then does everything unattended except the Tailscale sign-in at the end.

$ErrorActionPreference = 'Stop'

# --- Self-elevate ---
$admin = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $admin.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Requesting admin rights..."
    Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

Write-Host "=== Scarlett laptop bootstrap ==="

# --- 1. Tailscale ---
$tsExe = 'C:\Program Files\Tailscale\tailscale.exe'
if (-not (Test-Path $tsExe)) {
    Write-Host "[1/5] Installing Tailscale..."
    $msi = "$env:TEMP\tailscale-setup-latest-amd64.msi"
    Invoke-WebRequest -Uri 'https://pkgs.tailscale.com/stable/tailscale-setup-latest-amd64.msi' -OutFile $msi -UseBasicParsing
    Start-Process msiexec.exe -ArgumentList "/i `"$msi`" /quiet /norestart" -Wait
    Start-Sleep 5
} else {
    Write-Host "[1/5] Tailscale already installed."
}
Start-Service Tailscale -ErrorAction SilentlyContinue
Set-Service Tailscale -StartupType Automatic

# --- 2. OpenSSH Server ---
$cap = Get-WindowsCapability -Online | Where-Object { $_.Name -like 'OpenSSH.Server*' }
if ($cap.State -ne 'Installed') {
    Write-Host "[2/5] Installing OpenSSH Server..."
    Add-WindowsCapability -Online -Name 'OpenSSH.Server~~~~0.0.1.0' | Out-Null
} else {
    Write-Host "[2/5] OpenSSH Server already installed."
}

# --- 3. Scarlett's public key (key-only auth) ---
$pub = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHHz4LvFRnuSzxzPUhN8BiOV5QxfLhAjttKCv5pDhX6Z hatch'
$adminKeys = 'C:\ProgramData\ssh\administrators_authorized_keys'
$userKeys  = Join-Path $env:USERPROFILE '.ssh\authorized_keys'
New-Item -ItemType Directory -Force -Path (Split-Path $adminKeys) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $userKeys)  | Out-Null
Set-Content $adminKeys $pub -NoNewline -Encoding ascii
Set-Content $userKeys  $pub -NoNewline -Encoding ascii
icacls $adminKeys /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F" | Out-Null
Write-Host "[3/5] Keys installed."

# --- 4. sshd config: key-only ---
$cfg = 'C:\ProgramData\ssh\sshd_config'
$c = Get-Content $cfg -Raw
if ($c -match '(?m)^#?PasswordAuthentication\s+.*') { $c = $c -replace '(?m)^#?PasswordAuthentication\s+.*', 'PasswordAuthentication no' }
else { $c += "`r`nPasswordAuthentication no`r`n" }
if ($c -match '(?m)^#?PubkeyAuthentication\s+.*') { $c = $c -replace '(?m)^#?PubkeyAuthentication\s+.*', 'PubkeyAuthentication yes' }
else { $c += "PubkeyAuthentication yes`r`n" }
Set-Content $cfg $c -NoNewline -Encoding ascii
Write-Host "[4/5] sshd set to key-only."

# --- 5. Firewall: SSH only from the tailnet ---
if (-not (Get-NetFirewallRule -DisplayName 'OpenSSH-Scarlett-Tailnet' -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName 'OpenSSH-Scarlett-Tailnet' -Direction Inbound -Protocol TCP -LocalPort 22 -RemoteAddress '100.64.0.0/10' -Action Allow | Out-Null
}
Set-Service sshd -StartupType Automatic
Restart-Service sshd
Write-Host "[5/5] sshd running, firewall scoped to tailnet."

# --- 6. Join the tailnet (needs Or's one-time sign-in) ---
Write-Host ""
Write-Host "=== Last step: Tailscale sign-in ==="
Write-Host "A Tailscale login page will open (or this URL is shown below)."
Write-Host "Sign in once, then come back here."
& $tsExe up
$ip = ''
for ($i = 0; $i -lt 60 -and -not $ip; $i++) {
    Start-Sleep 5
    $ip = (& $tsExe ip -4 2>$null) | Select-Object -First 1
}
Write-Host ""
if ($ip) {
    Write-Host "DONE. Laptop tailnet IP: $ip"
    Write-Host "Tell Scarlett: she can now reach the laptop directly."
} else {
    Write-Host "Tailscale did not report an IP yet - sign in at the page above, then run: tailscale ip"
}
Write-Host "Press any key to close."; [void][System.Console]::ReadKey($true)
