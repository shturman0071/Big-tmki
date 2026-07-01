# Единый dashboard re-index (read-only)
param(
    [switch]$RecordSnapshot,
    [switch]$Json
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
Set-Location $runtime

$args = @("scripts/reindex_dashboard.py")
if ($RecordSnapshot) { $args += "--record-snapshot" }
if ($Json) { $args += "--json" }
python @args
