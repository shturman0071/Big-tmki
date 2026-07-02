# TMKI Demo UI: Q&A по регламентам в браузере
param(
    [string]$HostAddr = "127.0.0.1",
    [int]$Port = 8767,
    [switch]$OpenBrowser
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"

$env:TMKI_INDEX_BACKEND = "json"
$env:TMKI_EMBEDDING_PROVIDER = "local"
if (-not $env:TMKI_LLM_PROVIDER) {
    $env:TMKI_LLM_PROVIDER = "stub"
}
if (-not $env:TMKI_REGULATIONS_ARCHIVE) {
    $env:TMKI_REGULATIONS_ARCHIVE = "D:\Курсор\СКРУ-2"
}
if (-not $env:OLLAMA_MODEL) {
    $env:OLLAMA_MODEL = "qwen2.5:7b"
}

$url = "http://${HostAddr}:${Port}/"
Set-Location $runtime
Write-Host "TMKI Demo UI: $url" -ForegroundColor Cyan
Write-Host "  TMKI_INDEX_BACKEND=$env:TMKI_INDEX_BACKEND, LLM=$env:TMKI_LLM_PROVIDER, embeddings=$env:TMKI_EMBEDDING_PROVIDER" -ForegroundColor DarkGray

if ($OpenBrowser) {
    Start-Job -ScriptBlock {
        param($OpenUrl)
        Start-Sleep -Seconds 2
        Start-Process $OpenUrl
    } -ArgumentList $url | Out-Null
}

python -m tmki_demo --host $HostAddr --port $Port
