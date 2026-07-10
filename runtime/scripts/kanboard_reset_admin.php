<?php
$pdo = new PDO('sqlite:/var/www/app/data/db.sqlite');
$hash = password_hash('admin', PASSWORD_BCRYPT);
$st = $pdo->prepare('UPDATE users SET password=? WHERE username=?');
$st->execute([$hash, 'admin']);
fwrite(STDOUT, 'rows=' . $st->rowCount() . PHP_EOL);
