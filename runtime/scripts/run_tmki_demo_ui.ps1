# TMKI Demo UI: Q&A по регламентам в браузере
param(
    [string]$HostAddr = "127.0.0.1",
    [int]$Port = 8770,
    [switch]$OpenBrowser
)

$runtime = Resolve-Path $PSScriptRoot\..
$root = Resolve-Path $PSScriptRoot\..\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"

# Корневой config/rag_config.env (Ollama 768, pgvector chunks, rerank)
Set-Location $runtime
python -c "from tmki_runtime.rag_env import load_rag_config; load_rag_config(override=False)" 2>$null

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

python -c "from tmki_runtime.rag_env import reconcile_rag_config_after_secrets; reconcile_rag_config_after_secrets()" 2>$null

if ($env:OPENAI_API_KEY -and $env:OPENAI_API_KEY -notmatch '^sk-[A-Za-z0-9_-]{20,}$') {
    Remove-Item Env:OPENAI_API_KEY -ErrorAction SilentlyContinue
}

# Не подставляем openai автоматически — TMKI_LLM_PROVIDER задаётся в .env или config

if (-not $env:TMKI_SEARCH_POOL) { $env:TMKI_SEARCH_POOL = "64" }
if (-not $env:TMKI_INDEX_BACKEND) { $env:TMKI_INDEX_BACKEND = "pgvector" }
if (-not $env:TMKI_PGVECTOR_TABLE) { $env:TMKI_PGVECTOR_TABLE = "chunks" }
if (-not $env:TMKI_DEMO_WARMUP) { $env:TMKI_DEMO_WARMUP = "1" }
if ($env:TMKI_DEMO_PORT) { $Port = [int]$env:TMKI_DEMO_PORT }

# Локальное распознавание речи (faster-whisper, пресеты в tmki_voice/whisper_presets.py)
if (-not $env:TMKI_STT_PROVIDER) { $env:TMKI_STT_PROVIDER = "whisper" }
# Голос в демо: fast (medium) — quality слишком медленный на CPU
$env:WHISPER_PRESET = "fast"
if (-not $env:WHISPER_DEVICE) { $env:WHISPER_DEVICE = "cpu" }
if (-not $env:WHISPER_COMPUTE_TYPE) { $env:WHISPER_COMPUTE_TYPE = "int8" }
# Нейро-TTS Piper (ru_RU-ruslan-medium) — не браузерный speechSynthesis
if (-not $env:TMKI_TTS_PROVIDER) { $env:TMKI_TTS_PROVIDER = "piper" }
$env:PIPER_VOICE = "ru_RU-ruslan-medium"
if (-not $env:PIPER_VOICE_DIR) { $env:PIPER_VOICE_DIR = Join-Path $env:USERPROFILE ".local\share\piper-voices" }
$piperOnnx = Join-Path $env:PIPER_VOICE_DIR "$($env:PIPER_VOICE).onnx"
if (-not (Test-Path $piperOnnx)) {
    Write-Host "  Downloading Piper voice $($env:PIPER_VOICE)..." -ForegroundColor Yellow
    python scripts/download_piper_voice.py --voice $env:PIPER_VOICE --dir $env:PIPER_VOICE_DIR
}
python -c "import shutil, sys; sys.exit(0 if shutil.which('piper') else 1)" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "  Installing piper-tts..." -ForegroundColor Yellow
    pip install -q "piper-tts>=1.4.0"
}
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
    $ollamaList = ollama list 2>$null | Out-String
    if ($ollamaList -match 'tmki-qwen2\.5:7b') {
        $env:OLLAMA_MODEL = "tmki-qwen2.5:7b"
    } else {
        $env:OLLAMA_MODEL = "qwen2.5:7b"
    }
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
Write-Host "  backend=$env:TMKI_INDEX_BACKEND table=$env:TMKI_PGVECTOR_TABLE embed=$env:TMKI_EMBEDDING_PROVIDER dims=$env:TMKI_EMBEDDING_DIMS parser=$env:TMKI_INGEST_PARSER fusion_llm=$env:TMKI_RAG_FUSION_LLM LLM=$env:TMKI_LLM_PROVIDER" -ForegroundColor DarkGray
Write-Host "  STT=$env:TMKI_STT_PROVIDER (preset=$env:WHISPER_PRESET, $env:WHISPER_DEVICE/$env:WHISPER_COMPUTE_TYPE)" -ForegroundColor DarkGray
Write-Host "  TTS=$env:TMKI_TTS_PROVIDER voice=$env:PIPER_VOICE" -ForegroundColor DarkGray
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
