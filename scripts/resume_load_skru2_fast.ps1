# Перезапуск загрузки СКРУ-2 с batch /api/embed (быстрее).
# Останавливает только процесс load_skru2_to_chunks.py, продолжает с checkpoint.

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root

Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'load_skru2_to_chunks\.py' } |
    ForEach-Object {
        Write-Host "Stopping load_skru2 PID $($_.ProcessId)..." -ForegroundColor Yellow
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
Start-Sleep -Seconds 2

$env:TMKI_EMBED_BATCH = if ($env:TMKI_EMBED_BATCH) { $env:TMKI_EMBED_BATCH } else { "96" }
$env:TMKI_LOAD_WORKERS = if ($env:TMKI_LOAD_WORKERS) { $env:TMKI_LOAD_WORKERS } else { "2" }
Write-Host "Starting load_skru2 (embed-batch=$env:TMKI_EMBED_BATCH workers=$env:TMKI_LOAD_WORKERS)..." -ForegroundColor Cyan
python -u scripts/load_skru2_to_chunks.py --resume --embed-batch $env:TMKI_EMBED_BATCH --workers $env:TMKI_LOAD_WORKERS --batch 800
