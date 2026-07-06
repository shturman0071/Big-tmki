# Запуск TMKI Demo UI из корня репозитория
param(
    [int]$Port = 8770,
    [switch]$OpenBrowser,
    [switch]$Force
)

$pauseFile = Join-Path $PSScriptRoot "runtime\artifacts\demo\demo-paused.json"
if (-not $Force -and (Test-Path $pauseFile)) {
    try {
        $pause = Get-Content $pauseFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($pause.paused) {
            Write-Host "Demo на паузе: $($pause.reason)" -ForegroundColor Yellow
            Write-Host "  $($pause.resume_hint)" -ForegroundColor DarkGray
            Write-Host "  Принудительно: .\start-demo.ps1 -Force" -ForegroundColor DarkGray
            exit 0
        }
    } catch { }
}

$script = Join-Path $PSScriptRoot "runtime\scripts\run_tmki_demo_ui.ps1"
if (-not (Test-Path $script)) {
    Write-Error "Не найден: $script"
    exit 1
}
if ($OpenBrowser) {
    & $script -Port $Port -OpenBrowser
} else {
    & $script -Port $Port
}