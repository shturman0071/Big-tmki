<?php
/** Демо: русский интерфейс и синтетические задачи для Kanboard. */
$db = '/var/www/app/data/db.sqlite';
if (!is_file($db)) {
    fwrite(STDERR, "db missing\n");
    exit(1);
}
$pdo = new PDO('sqlite:' . $db);
$pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$adminId = (int) $pdo->query("SELECT id FROM users WHERE username='admin' LIMIT 1")->fetchColumn();
if ($adminId < 1) {
    fwrite(STDERR, "admin missing\n");
    exit(1);
}

$pdo->exec("UPDATE users SET language='ru_RU' WHERE username='admin'");

$projectId = (int) $pdo->query('SELECT id FROM projects ORDER BY id LIMIT 1')->fetchColumn();
if ($projectId < 1) {
    $now = time();
    $pdo->prepare(
        'INSERT INTO projects (name, is_active, token, last_modified, date_creation, is_public, is_private, description, identifier, start_date, end_date, owner_id, priority, default_swimlane, show_default_swimlane, is_everybody_allowed, enable_global_tags)
         VALUES (?, 1, ?, ?, ?, 0, 1, ?, ?, 0, 0, ?, 0, 0, 1, 0, 1)'
    )->execute(['Сатимол — демо', bin2hex(random_bytes(20)), $now, $now, 'Демо-задачи управленческого дашборда', 'SATIMOL', $adminId]);
    $projectId = (int) $pdo->lastInsertId();
} else {
    $pdo->prepare('UPDATE projects SET name=?, description=? WHERE id=?')->execute(
        ['Сатимол — демо', 'Демо-задачи управленческого дашборда ТМКИ', $projectId]
    );
}

$columnTitles = [
    1 => 'Бэклог',
    2 => 'Готово к работе',
    3 => 'В работе',
    4 => 'Выполнено',
];
$cols = $pdo->query("SELECT id, position FROM columns WHERE project_id={$projectId} ORDER BY position")->fetchAll(PDO::FETCH_ASSOC);
if (!$cols) {
    $now = time();
    $ins = $pdo->prepare('INSERT INTO columns (title, position, project_id) VALUES (?, ?, ?)');
    $pos = 1;
    foreach ($columnTitles as $title) {
        $ins->execute([$title, $pos++, $projectId]);
    }
    $cols = $pdo->query("SELECT id, position FROM columns WHERE project_id={$projectId} ORDER BY position")->fetchAll(PDO::FETCH_ASSOC);
} else {
    $upd = $pdo->prepare('UPDATE columns SET title=? WHERE id=?');
    foreach ($cols as $c) {
        $pos = (int) $c['position'];
        if (isset($columnTitles[$pos])) {
            $upd->execute([$columnTitles[$pos], (int) $c['id']]);
        }
    }
}

$colByPos = [];
foreach ($cols as $c) {
    $colByPos[(int) $c['position']] = (int) $c['id'];
}

$existing = (int) $pdo->query("SELECT COUNT(*) FROM tasks WHERE project_id={$projectId}")->fetchColumn();
if ($existing >= 5) {
    echo "seed_skip tasks={$existing}\n";
    exit(0);
}

$now = time();
$demoTasks = [
    [$colByPos[1] ?? 1, 1, 'Согласовать КС-3 за май по СКРУ-2', 'ПТО, срок до пятницы'],
    [$colByPos[2] ?? 2, 1, 'Проверить график поставки оборудования', 'Связать с договором СМР-САТ-024'],
    [$colByPos[3] ?? 3, 1, 'Подготовить ответ по просрочке договора', 'Дебиторка, контрагент из списка'],
    [$colByPos[3] ?? 3, 2, 'Запросить акты скрытых работ у подрядчика', 'Объект Сатимола'],
    [$colByPos[1] ?? 1, 2, 'Сверить риски по согласованию договоров', 'Юр. отдел + ПТО'],
    [$colByPos[2] ?? 2, 2, 'Уточнить сроки монтажа на объекте Германия', 'Поставщик, перевод документов'],
    [$colByPos[4] ?? 4, 1, 'Обновить платёжный календарь на июнь', 'Финансы'],
    [$colByPos[1] ?? 1, 3, 'Согласовать ТБ-наряд на выезд бригады', 'Служба ОТ и ПБ'],
];

$ins = $pdo->prepare(
    'INSERT INTO tasks (title, description, date_creation, date_modification, project_id, column_id, owner_id, creator_id, position, is_active, color_id, priority)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 0)'
);
$added = 0;
foreach ($demoTasks as [$colId, $pos, $title, $desc]) {
    $ins->execute([$title, $desc, $now, $now, $projectId, $colId, $adminId, $adminId, $pos, 'yellow']);
    $added++;
}

echo "seed_ok project={$projectId} tasks_added={$added} lang=ru_RU\n";
