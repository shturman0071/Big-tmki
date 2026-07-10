#!/bin/sh
# Демо: сброс пароля admin/admin, русский язык и синтетические задачи.
if [ -f /var/www/app/data/db.sqlite ]; then
  (
    sleep 6
    php -r '
$pdo = new PDO("sqlite:/var/www/app/data/db.sqlite");
$hash = password_hash("admin", PASSWORD_BCRYPT);
$st = $pdo->prepare("UPDATE users SET password=? WHERE username=?");
$st->execute([$hash, "admin"]);
' >/dev/null 2>&1 || true
    if [ -f /kanboard_seed_demo.php ]; then
      php /kanboard_seed_demo.php >/dev/null 2>&1 || true
    fi
  ) &
fi
exec /usr/local/bin/entrypoint.sh "$@"
