# Read-only чеклист re-index: отчёт, ошибки, аудит (не трогает re-index)
param(
    [switch]$ExportAudit,
    [switch]$RecordSnapshot,
    [switch]$QualitySnapshot,
    [switch]$Bundle
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
if ($QualitySnapshot) {
    Write-Host ""
    python scripts/snapshot_partial_quality.py
}
if ($ExportAudit) {
    Write-Host ""
    python scripts/export_reindex_audit.py
}
if ($Bundle) {
    Write-Host ""
    python scripts/export_reindex_ops_bundle.py
}
if (Test-Path "artifacts\regulations-import\quality-partial-p*.json") {
    Write-Host ""
    python scripts/compare_partial_quality.py
}
