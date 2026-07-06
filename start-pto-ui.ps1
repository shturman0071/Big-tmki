# PTO dashboard preview (port 8771, no warmup, bypass demo pause).
param(
    [int]$Port = 8771
)

$root = $PSScriptRoot
$env:TMKI_DEMO_WARMUP = "0"
$env:TMKI_DEMO_PORT = "$Port"
$env:TMKI_DEMO_OPEN_PATH = "/pto"

Write-Host "PTO Dashboard: http://127.0.0.1:$Port/pto" -ForegroundColor Cyan

& (Join-Path $root "start-demo.ps1") -Force -Port $Port -OpenBrowser
