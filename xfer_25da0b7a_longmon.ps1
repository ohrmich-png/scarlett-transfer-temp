$logFile = "C:\Scarlett\wallpaper-daynight\longmon.log"
$known = @{}
Get-Process -ErrorAction SilentlyContinue | ForEach-Object { $known[$_.Id] = $true }
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') longmon started (60 min)" | Out-File $logFile -Append -Encoding utf8
$endTime = (Get-Date).AddMinutes(60)
while ((Get-Date) -lt $endTime) {
    try {
        $procs = Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object { $_.Name -match "^(powershell|cmd|conhost|wt)\.exe$" }
        foreach ($p in $procs) {
            if (-not $known.ContainsKey($p.ProcessId)) {
                $known[$p.ProcessId] = $true
                $cl = if ($p.CommandLine) { $p.CommandLine.Substring(0, [Math]::Min(150, $p.CommandLine.Length)) } else { "" }
                "$(Get-Date -Format 'HH:mm:ss.fff') NEW: $($p.Name) pid=$($p.ProcessId) ppid=$($p.ParentProcessId) cmd='$cl'" | Out-File $logFile -Append -Encoding utf8
            }
        }
    } catch { }
    Start-Sleep -Milliseconds 500
}
"$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') longmon done" | Out-File $logFile -Append -Encoding utf8
