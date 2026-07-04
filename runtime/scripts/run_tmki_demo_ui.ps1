# TMKI Demo UI: Q&A по регламентам в браузере
param(
    [string]$HostAddr = "127.0.0.1",
    [int]$Port = 8770,
    [switch]$OpenBrowser
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"

# Авто: secrets.local + merge_env + определение parser/pgvector/fusion-llm
Set-Location $runtime
python scripts/merge_env.py 2>&1 | ForEach-Object {
    if ($_ -match '^AUTO:|^TMKI_INGEST|^TMKI_INDEX|^TMKI_RAG_FUSION') {
        Write-Host "  $_" -ForegroundColor DarkCyan
    }
}

# Локальные секреты: runtime/.env (не в git)
$dotenv = Join-Path $runtime ".env"
if (Test-Path $dotenv) {
    Get-Content $dotenv -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $name = $line.Substring(0, $eq).Trim()
        $value = $line.Substring($eq + 1).Trim().Trim('"').Trim("'")
        if ($name) { Set-Item -Path "Env:$name" -Value $value }
    }
    Write-Host "  Loaded secrets from $dotenv" -ForegroundColor DarkGray
}

if ($env:OPENAI_API_KEY -and $env:OPENAI_API_KEY -notmatch '^sk-[A-Za-z0-9_-]{20,}$') {
    Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
}

# Не подставляем openai автоматически — TMKI_LLM_PROVIDER задаётся в .env или ниже

if (-not $env:TMKI_EMBEDDING_PROVIDER) { $env:TMKI_EMBEDDING_PROVIDER = "local" }
if (-not $env:TMKI_SEARCH_POOL) { $env:TMKI_SEARCH_POOL = "64" }
# Retrieval: значения из merge_env / autoconfigure (.env)
if (-not $env:TMKI_INDEX_BACKEND) { $env:TMKI_INDEX_BACKEND = "json" }
if (-not $env:TMKI_DEMO_WARMUP) { $env:TMKI_DEMO_WARMUP = "1" }

# Локальное распознавание речи (faster-whisper, пресеты в tmki_voice/whisper_presets.py)
if (-not $env:TMKI_STT_PROVIDER) { $env:TMKI_STT_PROVIDER = "whisper" }
# Голос в демо: fast (medium) — quality слишком медленный на CPU
$env:WHISPER_PRESET = "fast"
if (-not $env:WHISPER_DEVICE) { $env:WHISPER_DEVICE = "cpu" }
if (-not $env:WHISPER_COMPUTE_TYPE) { $env:WHISPER_COMPUTE_TYPE = "int8" }
# OpenAI отложен: по умолчанию Ollama (если не задано в .env)
if (-not $env:TMKI_LLM_PROVIDER) {
    $env:TMKI_LLM_PROVIDER = "ollama"
}
if (-not $env:TMKI_REGULATIONS_ARCHIVE) {
    $env:TMKI_REGULATIONS_ARCHIVE = "D:\Курсор\СКРУ-2"
}
if (-not $env:TMKI_ARM_KS_ARCHIVE) {
    $env:TMKI_ARM_KS_ARCHIVE = "D:\Курсор\Армировка КС"
}
if (-not $env:OLLAMA_MODEL) {
    $env:OLLAMA_MODEL = "qwen2.5:7b"
}

$url = "http://${HostAddr}:${Port}/"
Set-Location $runtime

# Освободить порт от зависших экземпляров demo (python)
$listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
foreach ($conn in $listeners) {
    $proc = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -match '^(python|pythonw)$') {
        Write-Host "  Stopping old demo (PID $($conn.OwningProcess))..." -ForegroundColor Yellow
        Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 1
    }
}

Write-Host "TMKI Demo UI: $url" -ForegroundColor Cyan
Write-Host "  backend=$env:TMKI_INDEX_BACKEND parser=$env:TMKI_INGEST_PARSER fusion_llm=$env:TMKI_RAG_FUSION_LLM LLM=$env:TMKI_LLM_PROVIDER" -ForegroundColor DarkGray
Write-Host "  STT=$env:TMKI_STT_PROVIDER (preset=$env:WHISPER_PRESET, $env:WHISPER_DEVICE/$env:WHISPER_COMPUTE_TYPE)" -ForegroundColor DarkGray
Write-Host "  Keep this window open while using the demo." -ForegroundColor Yellow

if ($OpenBrowser) {
    $env:TMKI_DEMO_OPEN_BROWSER = "1"
} else {
    Remove-Item Env:TMKI_DEMO_OPEN_BROWSER -ErrorAction SilentlyContinue
}

python -m tmki_demo --host $HostAddr --port $Port
$exit = $LASTEXITCODE
if ($exit -ne 0) {
    Write-Host "Demo exited (code $exit). Port $Port may be in use." -ForegroundColor Red
}
exit $exit
