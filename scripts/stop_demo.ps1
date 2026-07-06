# Остановить Demo UI (освободить Ollama/CPU на время индексации).
# Запуск: .\scripts\stop_demo.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$pauseFile = Join-Path $root "runtime\artifacts\demo\demo-paused.json"
$port = if ($env:TMKI_DEMO_PORT) { [int]$env:TMKI_DEMO_PORT } else { 8770 }

Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
    $proc = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -match '^(python|pythonw)$') {
        Write-Host "Stopping demo PID $($_.OwningProcess)..." -ForegroundColor Yellow
        Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
    }
}

Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match 'tmki_demo' } |
    ForEach-Object {
        Write-Host "Stopping tmki_demo PID $($_.ProcessId)..." -ForegroundColor Yellow
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }

New-Item -ItemType Directory -Force -Path (Split-Path $pauseFile) | Out-Null
@{
    paused = $true
    reason = "До 100% индексации СКРУ-2"
    paused_at = (Get-Date).ToUniversalTime().ToString("o")
    resume_hint = ".\start-demo.ps1 после завершения load_skru2"
} | ConvertTo-Json | Set-Content -Path $pauseFile -Encoding UTF8

Write-Host "Demo остановлен. Пауза зафиксирована: $pauseFile" -ForegroundColor Green
