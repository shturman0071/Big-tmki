# TMKI Demo UI: Q&A по регламентам в браузере
param(
    [string]$HostAddr = "127.0.0.1",
    [int]$Port = 8767
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"

if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
}
if (-not $env:TMKI_INDEX_BACKEND) {
    $env:TMKI_INDEX_BACKEND = "pgvector"
}
if (-not $env:OLLAMA_MODEL) {
    $env:OLLAMA_MODEL = "qwen2.5:7b"
}

Set-Location $runtime
Write-Host "TMKI Demo UI: http://${HostAddr}:${Port}/" -ForegroundColor Cyan
Write-Host "  DATABASE_URL set, TMKI_INDEX_BACKEND=$env:TMKI_INDEX_BACKEND" -ForegroundColor DarkGray
python -m tmki_demo --host $HostAddr --port $Port
