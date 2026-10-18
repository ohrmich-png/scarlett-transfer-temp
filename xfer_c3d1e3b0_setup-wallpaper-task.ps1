# Registers the Scarlett day/night wallpaper schedule on this machine.
# Run once. Creates/refreshes the files then registers the task.

$ErrorActionPreference = "Stop"
$dir = "C:\Scarlett\wallpaper-daynight"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

$taskName = "Scarlett Wallpaper DayNight"
$script = "$dir\wallpaper.ps1"

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$triggerRepeat = New-ScheduledTaskTrigger -Once -At (Get-Date).Date `
    -RepetitionInterval (New-TimeSpan -Minutes 30) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $taskName -Action $action `
    -Trigger $triggerLogon, $triggerRepeat -Settings $settings `
    -Description "Scarlett: day/night wallpaper based on actual sunrise/sunset (Yokneam Illit)" | Out-Null

# Run once right now so the correct wallpaper applies immediately
& $script

$state = (Get-ScheduledTask -TaskName $taskName).State
$wall = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' -Name Wallpaper).Wallpaper
"task=$state wallpaper=$wall"
