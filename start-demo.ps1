# Запуск TMKI Demo UI из корня репозитория
param(
    [int]$Port = 8770,
    [switch]$OpenBrowser
)

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
