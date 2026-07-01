# Read-only чеклист после finalize
param()

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
Set-Location $runtime

Write-Host "=== Post-finalize checklist ===" -ForegroundColor Cyan
python scripts/post_finalize_report.py
Write-Host ""
python scripts/verify_post_finalize.py
Write-Host ""
python scripts/print_reindex_handoff.py --finalize
