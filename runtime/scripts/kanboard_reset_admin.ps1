# Сброс пароля Kanboard admin/admin для локального демо.
$ErrorActionPreference = "Stop"
$container = "tmki-kanboard"
$script = Join-Path $PSScriptRoot "kanboard_reset_admin.php"
$running = docker ps --filter "name=$container" --format "{{.Names}}" 2>$null
if (-not $running) {
    Write-Host "Контейнер $container не запущен. Сначала: docker compose -f runtime/docker/docker-compose.kanboard.yml up -d"
    exit 1
}
docker cp $script "${container}:/tmp/reset.php"
docker exec $container php /tmp/reset.php
Write-Host "OK: admin / admin"
