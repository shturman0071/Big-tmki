# Director dashboard preview (port 8772, no warmup, bypass demo pause).
param(
    [int]$Port = 8772
)

$root = $PSScriptRoot
$env:TMKI_DEMO_WARMUP = "0"
$env:TMKI_DEMO_PORT = "$Port"
$env:TMKI_DEMO_OPEN_PATH = "/director"

Write-Host "Director Dashboard: http://127.0.0.1:$Port/director" -ForegroundColor Cyan

& (Join-Path $root "start-demo.ps1") -Force -Port $Port -OpenBrowser
