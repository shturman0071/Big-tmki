# Быстрый demo: health → report → MVP
param(
    [string]$Query = "промбезопасность кран",
    [ValidateSet("json", "pgvector")]
    [string]$Backend = "json",
    [ValidateSet("auto", "ollama", "stub", "openai")]
    [string]$Llm = "auto",
    [switch]$Experience,
    [switch]$Milestone
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
$env:TMKI_MVP_MESSAGE = $Query
Set-Location $runtime

Write-Host "=== TMKI demo ===" -ForegroundColor Cyan
python scripts/check_runtime_health.py
python scripts/reindex_dashboard.py

$resolvedLlm = if ($Llm -eq "auto") {
    $r = python scripts/check_ollama.py --resolve 2>$null
    if ($LASTEXITCODE -eq 0 -and $r) { $r.Trim() } else { "stub" }
} else { $Llm }
if ($resolvedLlm -eq "ollama") {
    $env:TMKI_LLM_PROVIDER = "ollama"
    if (-not $env:OLLAMA_MODEL) { $env:OLLAMA_MODEL = "qwen2.5:7b" }
    Write-Host "LLM: ollama ($env:OLLAMA_MODEL)" -ForegroundColor Green
} else {
    Write-Host "LLM: $resolvedLlm" -ForegroundColor $(if ($resolvedLlm -eq "stub") { "Yellow" } else { "Green" })
}

$mvpArgs = @("scripts/run_mvp_regulations.py", $Query, "--variant", "v2", "--hybrid", "--llm", $resolvedLlm)
if ($Backend -eq "pgvector") {
    $env:DATABASE_URL = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
    $env:TMKI_INDEX_BACKEND = "pgvector"
    $mvpArgs += @("--backend", "pgvector")
}
if ($Experience) {
    $mvpArgs += @("--tts", "--cast", "tv")
}
python @mvpArgs
if ($Milestone) {
    & $PSScriptRoot\reindex_milestone.ps1
}
