# Сид Kanboard: русский язык + демо-задачи
$root = Resolve-Path $PSScriptRoot\..\..
$php = Join-Path $root "runtime\docker\kanboard_seed_demo.php"
docker cp $php tmki-kanboard:/tmp/seed.php
docker exec tmki-kanboard php /tmp/seed.php
