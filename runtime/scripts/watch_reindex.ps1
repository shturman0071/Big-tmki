# Перезапуск re-index, если heartbeat устарел (по умолчанию 20 мин)
param(
    [int]$StaleMinutes = 20,
    [int]$PollSeconds = 120,
    [switch]$SyncPgvector,
    [switch]$Finalize,
    [switch]$Milestone
)

$runtime = Resolve-Path $PSScriptRoot\..
$heartbeat = Join-Path $runtime "artifacts\regulations-import\reindex-heartbeat.json"
$stateFile = Join-Path $runtime "artifacts\regulations-import\reindex-state.json"
$syncMarker = Join-Path $runtime "artifacts\regulations-import\last-pgvector-sync.json"
$finalizeMarker = Join-Path $runtime "artifacts\regulations-import\finalize-done.json"
$env:PYTHONPATH = $runtime.Path

function Get-StateUpdatedAt {
    if (-not (Test-Path $stateFile)) { return $null }
    $st = Get-Content $stateFile -Raw | ConvertFrom-Json
    return $st.updated_at
}

function Invoke-PgvectorSyncIfNeeded {
    if (-not $SyncPgvector) { return }
    $cur = Get-StateUpdatedAt
    if (-not $cur) { return }
    $prev = $null
    if (Test-Path $syncMarker) {
        $prev = (Get-Content $syncMarker -Raw | ConvertFrom-Json).updated_at
    }
    if ($cur -eq $prev) { return }
    Write-Host "[$(Get-Date -Format HH:mm:ss)] pgvector incremental sync..."
    & $PSScriptRoot\sync_pgvector_incremental.ps1
    if ($LASTEXITCODE -eq 0) {
        @{ updated_at = $cur } | ConvertTo-Json | Set-Content $syncMarker -Encoding utf8
    }
}

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

function Test-ReindexComplete {
    if (-not (Test-Path $stateFile)) { return $false }
    $report = python scripts/reindex_report.py --json | ConvertFrom-Json
    return ($report.live_progress -ge $report.total)
}

function Invoke-FinalizeIfNeeded {
    if (-not $Finalize) { return }
    if (Test-Path $finalizeMarker) { return }
    if (-not (Test-ReindexComplete)) { return }
    Write-Host "[$(Get-Date -Format HH:mm:ss)] re-index complete — finalize..."
    & $PSScriptRoot\finalize_regulations_index.ps1
    if ($LASTEXITCODE -eq 0) {
        @{ done_at = (Get-Date).ToUniversalTime().ToString("o") } | ConvertTo-Json | Set-Content $finalizeMarker -Encoding utf8
    }
}

function Invoke-MilestoneIfNeeded {
    if (-not $Milestone) { return }
    & $PSScriptRoot\reindex_milestone.ps1
}

Set-Location $runtime
Write-Host "watch_reindex: poll every ${PollSeconds}s, stale>${StaleMinutes}m"

while ($true) {
    if (-not (Test-ReindexRunning)) {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] re-index not running — starting resume..."
        python scripts/reindex_regulations_local.py --checkpoint-every 200
    }
    elseif (Test-HeartbeatStale) {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] heartbeat stale — restarting..."
        Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
            Where-Object { $_.CommandLine -like '*reindex_regulations_local*' } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Seconds 3
        python scripts/reindex_regulations_local.py --checkpoint-every 200 --force-lock
    }
    else {
        python scripts/reindex_report.py 2>$null
        Invoke-PgvectorSyncIfNeeded
        Invoke-MilestoneIfNeeded
        Invoke-FinalizeIfNeeded
    }
    Start-Sleep -Seconds $PollSeconds
}
