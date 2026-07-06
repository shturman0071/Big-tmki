# Мониторинг загрузки СКРУ-2 в PostgreSQL (обновление каждые 5 сек)
param(
    [int]$Interval = 5,
    [switch]$Once
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

$args = @("scripts/watch_load_skru2.py", "--interval", $Interval)
if ($Once) { $args += "--once" }

python -u @args
