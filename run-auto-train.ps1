# Автообучение TMKI: анализ форматов → Azure Q&A → Ollama-модель
param(
    [string]$Source = "",
    [string]$OutputModel = "tmki-qwen2.5:7b",
    [int]$Limit = 0
)

$runtime = Join-Path $PSScriptRoot "runtime"
Set-Location $runtime
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"

python -c "from tmki_runtime.rag_env import load_rag_config; load_rag_config(override=False)" 2>$null

$args = @("scripts/auto_train_pipeline.py", "--output-model", $OutputModel)
if ($Source) { $args += @("--source", $Source) }
if ($Limit -gt 0) { $args += @("--limit", $Limit) }

Write-Host "TMKI auto-train pipeline..." -ForegroundColor Cyan
python @args
exit $LASTEXITCODE
