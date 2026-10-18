# Scarlett day/night wallpaper scheduler
# Switches between the day wallpaper (scarleet.jpg) and the night wallpaper
# (stars) based on actual sunrise/sunset for Yokneam Illit, Israel.
# Runs via Windows Task Scheduler (logon + every 30 min). Idempotent.

$dayWallpaper   = "$env:USERPROFILE\Downloads\scarleet.jpg"
$nightWallpaper = "$env:USERPROFILE\Downloads\starts in the night.jpg"
$logFile        = "C:\Scarlett\wallpaper-daynight\wallpaper.log"

function d2r($d) { return $d * [Math]::PI / 180 }
function r2d($r) { return $r * 180 / [Math]::PI }

# NOAA solar calculation -> event time in UTC hours (fractional)
function SunTimeUtc($lat, $lon, $date, $rise) {
    $N = $date.DayOfYear
    $lngHour = $lon / 15.0
    $base = if ($rise) { 6 } else { 18 }
    $t = $N + (($base - $lngHour) / 24)
    $M = (0.9856 * $t) - 3.289
    $L = $M + 1.916 * [Math]::Sin((d2r $M)) + 0.020 * [Math]::Sin((d2r (2 * $M))) + 282.634
    while ($L -ge 360) { $L -= 360 }; while ($L -lt 0) { $L += 360 }
    $RA = r2d ([Math]::Atan(0.91764 * [Math]::Tan((d2r $L))))
    while ($RA -ge 360) { $RA -= 360 }; while ($RA -lt 0) { $RA += 360 }
    $Lquad  = [Math]::Floor($L / 90) * 90
    $RAquad = [Math]::Floor($RA / 90) * 90
    $RA = ($RA + ($Lquad - $RAquad)) / 15
    $sinDec = 0.39782 * [Math]::Sin((d2r $L))
    $cosDec = [Math]::Cos([Math]::Asin($sinDec))
    $cosH = ([Math]::Cos((d2r 90.833)) - ($sinDec * [Math]::Sin((d2r $lat)))) / ($cosDec * [Math]::Cos((d2r $lat)))
    if ($cosH -gt 1 -or $cosH -lt -1) { return $null }
    $Hdeg = r2d ([Math]::Acos($cosH))
    if ($rise) { $Hdeg = 360 - $Hdeg }
    $H = $Hdeg / 15
    $T = $H + $RA - (0.06571 * $t) - 6.622
    $UT = $T - $lngHour
    while ($UT -ge 24) { $UT -= 24 }; while ($UT -lt 0) { $UT += 24 }
    return $UT
}

function Write-Log($msg) {
    $ts = (Get-Date).ToString("yyyy-MM-dd HH:mm")
    "$ts $msg" | Out-File -FilePath $logFile -Append -Encoding utf8
}

try {
    if (-not (Test-Path $dayWallpaper))   { Write-Log "MISSING day wallpaper: $dayWallpaper"; exit 1 }
    if (-not (Test-Path $nightWallpaper)) { Write-Log "MISSING night wallpaper: $nightWallpaper"; exit 1 }

    $now = Get-Date
    $offsetHrs = [TimeZoneInfo]::Local.GetUtcOffset($now).TotalHours
    $sunriseUtc = SunTimeUtc 32.65 35.10 $now $true
    $sunsetUtc  = SunTimeUtc 32.65 35.10 $now $false
    if ($null -eq $sunriseUtc -or $null -eq $sunsetUtc) { Write-Log "solar calc failed"; exit 1 }

    $sunrise = $sunriseUtc + $offsetHrs
    $sunset  = $sunsetUtc + $offsetHrs
    $hourNow = $now.Hour + $now.Minute / 60.0
    $isDay = ($hourNow -ge $sunrise) -and ($hourNow -lt $sunset)
    $target = if ($isDay) { $dayWallpaper } else { $nightWallpaper }
    $mode = if ($isDay) { "DAY" } else { "NIGHT" }

    $current = (Get-ItemProperty 'HKCU:\Control Panel\Desktop' -Name Wallpaper -ErrorAction SilentlyContinue).Wallpaper
    if ($current -eq $target) {
        Write-Log "$mode already set (sunrise $([int]$sunrise):$('{0:D2}' -f [int](($sunrise%1)*60)) / sunset $([int]$sunset):$('{0:D2}' -f [int](($sunset%1)*60)))"
        exit 0
    }

    Set-ItemProperty 'HKCU:\Control Panel\Desktop' -Name Wallpaper -Value $target
    Set-ItemProperty 'HKCU:\Control Panel\Desktop' -Name WallpaperStyle -Value 10
    Set-ItemProperty 'HKCU:\Control Panel\Desktop' -Name TileWallpaper -Value 0

    Add-Type -TypeDefinition @"
using System.Runtime.InteropServices;
public class ScarlettWP {
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
}
"@
    [ScarlettWP]::SystemParametersInfo(20, 0, $target, 3) | Out-Null
    Write-Log "switched to $mode wallpaper"
}
catch {
    Write-Log "ERROR: $($_.Exception.Message)"
    exit 1
}
