# Pipeline status (PowerShell wrapper)
param(
    [switch]$Json,
    [switch]$Save
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
Set-Location $runtime

$args = @("scripts/pipeline_status.py")
if ($Json) { $args += "--json" }
if ($Save) { $args += "--save" }
python @args
