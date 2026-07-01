# Перезапуск re-index, если heartbeat устарел (по умолчанию 20 мин)
param(
    [int]$StaleMinutes = 20,
    [int]$PollSeconds = 120
)

$runtime = Resolve-Path $PSScriptRoot\..
$heartbeat = Join-Path $runtime "artifacts\regulations-import\reindex-heartbeat.json"
$env:PYTHONPATH = $runtime.Path

function Test-ReindexRunning {
    $p = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*reindex_regulations_local*' }
    return $null -ne $p
}

function Test-HeartbeatStale {
    if (-not (Test-Path $heartbeat)) { return $false }
    $hb = Get-Content $heartbeat -Raw | ConvertFrom-Json
    $ts = [datetime]::Parse($hb.updated_at.Replace('Z', '+00:00'))
    $age = (Get-Date).ToUniversalTime() - $ts
    return $age.TotalMinutes -gt $StaleMinutes
}

Set-Location $runtime
Write-Host "watch_reindex: poll every ${PollSeconds}s, stale>${StaleMinutes}m"

while ($true) {
    if (-not (Test-ReindexRunning)) {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] re-index not running — starting resume..."
        & $PSScriptRoot\resume_reindex.ps1
    }
    elseif (Test-HeartbeatStale) {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] heartbeat stale — restarting..."
        Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
            Where-Object { $_.CommandLine -like '*reindex_regulations_local*' } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 3
        & $PSScriptRoot\resume_reindex.ps1
    }
    else {
        python scripts/reindex_status.py 2>$null
    }
    Start-Sleep -Seconds $PollSeconds
}
