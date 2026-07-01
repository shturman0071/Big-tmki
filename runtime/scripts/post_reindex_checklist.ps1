# Read-only чеклист re-index: отчёт, ошибки, аудит (не трогает re-index)
param(
    [switch]$ExportAudit,
    [switch]$RecordSnapshot
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
Set-Location $runtime

Write-Host "=== Re-index checklist ===" -ForegroundColor Cyan
python scripts/reindex_dashboard.py
Write-Host ""
python scripts/reindex_errors.py --summary
if ($RecordSnapshot) {
    Write-Host ""
    python scripts/record_reindex_snapshot.py
}
if (Test-Path "artifacts\regulations-import\reindex-progress-log.jsonl") {
    Write-Host ""
    python scripts/analyze_reindex_progress_log.py
}
if ($ExportAudit) {
    Write-Host ""
    python scripts/export_reindex_audit.py
}
