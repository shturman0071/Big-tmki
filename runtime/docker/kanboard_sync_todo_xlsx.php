<?php
/**
 * Синхронизация задач Owner=Аксенов из to-do-list.xlsx в Kanboard.
 * Стабильный ключ: tasks.reference = xlsx-aksenov:<slug>
 * Удаляет устаревшие xlsx-aksenov:* задачи, которых больше нет в файле.
 */
$db = '/var/www/app/data/db.sqlite';
$jsonPath = '/tmp/aksenov_todo_tasks.json';

if (!is_file($db) || !is_file($jsonPath)) {
    fwrite(STDERR, "db or json missing\n");
    exit(1);
}

$tasks = json_decode(file_get_contents($jsonPath), true);
if (!is_array($tasks)) {
    fwrite(STDERR, "bad json\n");
    exit(1);
}

$pdo = new PDO('sqlite:' . $db);
$pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

$adminId = (int) $pdo->query("SELECT id FROM users WHERE username='admin' LIMIT 1")->fetchColumn();
$projectId = (int) $pdo->query('SELECT id FROM projects ORDER BY id LIMIT 1')->fetchColumn();
if ($adminId < 1 || $projectId < 1) {
    fwrite(STDERR, "admin/project missing\n");
    exit(1);
}

$swimlaneId = (int) $pdo->query(
    "SELECT id FROM swimlanes WHERE project_id={$projectId} AND is_active=1 ORDER BY position LIMIT 1"
)->fetchColumn();
if ($swimlaneId < 1) {
    $swimlaneId = 1;
}

// Ensure existing board tasks have a swimlane (иначе карточки могут не рисоваться).
$pdo->exec("UPDATE tasks SET swimlane_id={$swimlaneId} WHERE project_id={$projectId} AND (swimlane_id IS NULL OR swimlane_id=0)");

$cols = $pdo->query("SELECT id, position, title FROM columns WHERE project_id={$projectId} ORDER BY position")->fetchAll(PDO::FETCH_ASSOC);
$colByPos = [];
foreach ($cols as $c) {
    $colByPos[(int) $c['position']] = (int) $c['id'];
}
$defaultCol = $colByPos[2] ?? ($colByPos[1] ?? (int) ($cols[0]['id'] ?? 1));
$statusMap = [
    // Planning сразу на видную колонку «Готово к работе»
    'planning' => $colByPos[2] ?? ($colByPos[1] ?? $defaultCol),
    'approved' => $colByPos[2] ?? $defaultCol,
    'pending review' => $colByPos[3] ?? $defaultCol,
    'in progress' => $colByPos[3] ?? $defaultCol,
    'completed' => $colByPos[4] ?? $defaultCol,
    'done' => $colByPos[4] ?? $defaultCol,
];

$findRef = $pdo->prepare("SELECT id FROM tasks WHERE project_id=? AND reference=? LIMIT 1");
$upd = $pdo->prepare(
    "UPDATE tasks SET title=?, description=?, date_due=?, date_modification=?, date_moved=?,
        column_id=?, swimlane_id=?, color_id=?, is_active=1, owner_id=?, priority=?
     WHERE id=?"
);
$ins = $pdo->prepare(
    "INSERT INTO tasks (
        title, description, date_creation, date_modification, date_due, date_moved,
        project_id, column_id, swimlane_id, owner_id, creator_id, position, is_active,
        color_id, priority, reference
     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)"
);

$now = time();
$added = 0;
$updated = 0;
$keepRefs = [];

$maxPos = (int) $pdo->query("SELECT COALESCE(MAX(position),0) FROM tasks WHERE project_id={$projectId}")->fetchColumn();

foreach ($tasks as $i => $t) {
    $ref = trim((string) ($t['reference'] ?? ''));
    $title = trim((string) ($t['title'] ?? ''));
    if ($ref === '' || $title === '') {
        continue;
    }
    $keepRefs[] = $ref;
    $due = (int) ($t['date_due'] ?? 0);
    $desc = trim((string) ($t['description'] ?? ''));
    $status = strtolower(trim((string) ($t['status'] ?? 'planning')));
    $colId = $statusMap[$status] ?? $defaultCol;
    $color = (($t['priority'] ?? '') === 'High') ? 'red' : 'yellow';
    $prio = (($t['priority'] ?? '') === 'High') ? 2 : 0;

    $findRef->execute([$projectId, $ref]);
    $existingId = (int) $findRef->fetchColumn();
    if ($existingId > 0) {
        $upd->execute([$title, $desc, $due, $now, $now, $colId, $swimlaneId, $color, $adminId, $prio, $existingId]);
        $updated++;
    } else {
        $maxPos++;
        $ins->execute([
            $title, $desc, $now, $now, $due, $now,
            $projectId, $colId, $swimlaneId, $adminId, $adminId, $maxPos,
            $color, $prio, $ref,
        ]);
        $added++;
    }
}

// Remove stale synced cards
$stale = $pdo->query(
    "SELECT id, reference FROM tasks WHERE project_id={$projectId} AND reference LIKE 'xlsx-aksenov:%'"
)->fetchAll(PDO::FETCH_ASSOC);
$removed = 0;
$del = $pdo->prepare("DELETE FROM tasks WHERE id=?");
foreach ($stale as $row) {
    if (!in_array($row['reference'], $keepRefs, true)) {
        $del->execute([(int) $row['id']]);
        $removed++;
    }
}

// Убрать дубликаты без reference с тем же заголовком, что у синхронизированных.
$titles = [];
foreach ($tasks as $t) {
    $titles[] = trim((string) ($t['title'] ?? ''));
}
$dup = $pdo->prepare(
    "DELETE FROM tasks WHERE project_id=? AND title=? AND (reference IS NULL OR reference='')"
);
foreach (array_unique(array_filter($titles)) as $title) {
    $dup->execute([$projectId, $title]);
    $removed += $dup->rowCount();
}

echo json_encode([
    'ok' => true,
    'project_id' => $projectId,
    'swimlane_id' => $swimlaneId,
    'added' => $added,
    'updated' => $updated,
    'removed' => $removed,
    'tasks' => count($keepRefs),
], JSON_UNESCAPED_UNICODE) . "\n";
