# Hands-off: ждать 100% re-index и запустить finalize (без milestone/pgvector sync/restart)
param(
    [int]$PollSeconds = 120,
    [string]$Query = "промбезопасность кран",
    [switch]$RecordSnapshot
)

$runtime = Resolve-Path $PSScriptRoot\..
$finalizeMarker = Join-Path $runtime "artifacts\regulations-import\finalize-done.json"
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
$env:TMKI_MVP_MESSAGE = $Query
Set-Location $runtime

function Test-ReindexRunning {
    $p = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like '*reindex_regulations_local*' }
    return $null -ne $p
}

Write-Host "watch_to_finalize: poll ${PollSeconds}s (no milestone/sync)" -ForegroundColor Cyan

while ($true) {
    if (Test-Path $finalizeMarker) {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] finalize already done."
        exit 0
    }

    $status = python scripts/reindex_ops_status.py --json | ConvertFrom-Json
    $r = $status.report

    if ($status.ready_for_finalize) {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] re-index 100% — starting finalize..."
        & $PSScriptRoot\wait_and_finalize.ps1 -PollSeconds 0 -Query $Query
        exit $LASTEXITCODE
    }

    if ($r.complete -and -not $status.ready_for_finalize) {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] 100% but lock active (pid=$($r.lock_pid)) — waiting..."
    }
    elseif (-not $r.complete -and -not (Test-ReindexRunning)) {
        Write-Host "[$(Get-Date -Format HH:mm:ss)] re-index stopped at $($r.live_progress)/$($r.total) — run resume_reindex.ps1" -ForegroundColor Yellow
    }
    else {
        $eta = if ($r.eta_hours) { " ETA ~$($r.eta_hours)h" } else { "" }
        $logEta = $status.progress_log_analysis.eta_hours_from_log
        if ($logEta) { $eta = " ETA ~${logEta}h (log)" }
        Write-Host "[$(Get-Date -Format HH:mm:ss)] $($r.live_progress)/$($r.total) ($($r.percent)%)$eta"
    }

    if ($RecordSnapshot) {
        python scripts/record_reindex_snapshot.py 2>$null
    }

    Start-Sleep -Seconds $PollSeconds
}
