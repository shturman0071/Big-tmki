# Read-only чеклист re-index: отчёт, ошибки, аудит (не трогает re-index)
param(
    [switch]$ExportAudit
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
Set-Location $runtime

Write-Host "=== Re-index checklist ===" -ForegroundColor Cyan
python scripts/reindex_report.py
Write-Host ""
python scripts/reindex_errors.py --summary
if ($ExportAudit) {
    Write-Host ""
    python scripts/export_reindex_audit.py
}
