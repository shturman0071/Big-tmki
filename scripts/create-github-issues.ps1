# Создание GitHub Issues из roadmap (требуется gh CLI + gh auth login)
# Использование: .\scripts\create-github-issues.ps1 [-IncludeDone]

param(
    [switch]$IncludeDone
)

$ErrorActionPreference = "Stop"
$repo = "shturman0071/Big-tmki"

$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) {
    $defaultGh = "C:\Program Files\GitHub CLI\gh.exe"
    if (Test-Path $defaultGh) { $gh = $defaultGh }
}
if (-not $gh) {
    Write-Error "GitHub CLI (gh) не найден. Установите: winget install GitHub.cli, затем перезапустите терминал."
}

function Invoke-Gh {
    param([string[]]$GhArgs)
    & $gh @GhArgs
}

$authCheck = & $gh auth status --hostname github.com 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Error "Не авторизованы в gh. Выполните:`n& `"$gh`" auth login -h github.com -p https -w`n$authCheck"
}

$labels = @("phase-0", "phase-1", "phase-2", "phase-3", "phase-4", "phase-5", "phase-6", "security", "runtime", "docs", "done")
foreach ($l in $labels) {
    Invoke-Gh @('label', 'create', $l, '--repo', $repo, '--force') 2>$null | Out-Null
}

function New-RoadmapIssue {
    param(
        [string]$Title,
        [string]$Labels,
        [string]$Body,
        [bool]$Closed = $false
    )

    $labelArgs = @()
    foreach ($label in ($Labels -split ',')) {
        $labelArgs += @('--label', $label.Trim())
    }

    Write-Host "Создание: $Title"
    $createArgs = @('issue', 'create', '--repo', $repo, '--title', $Title, '--body', $Body) + $labelArgs
    $url = Invoke-Gh $createArgs
    if ($Closed -and $url) {
        $num = ($url -split '/')[-1]
        Invoke-Gh @('issue', 'close', $num, '--repo', $repo, '--comment', 'Закрыто: реализовано в хэндбуке v0.1 (см. docs/ROADMAP.md).') | Out-Null
    }
}

$openIssues = @(
    @{
        title  = '[phase-0][docs] #2 Закрепить владельцев и процесс апрува хэндбука'
        labels = 'phase-0,docs'
        body   = @'
Определить:
- кто апрувит изменения MUST-требований
- когда обязателен security-review
- когда обновлять README.md

Критерий: раздел в AGENTS.md или README.
План: docs/ROADMAP.md #2
'@
    },
    @{
        title  = '[phase-1][docs] #4 Назначить владельцев в 13_ai_skills_registry.md'
        labels = 'phase-1,docs'
        body   = 'Для каждого skill указать владельца и один пример сценария inputs/outputs.' + "`n`n" + 'План: docs/ROADMAP.md #4'
    },
    @{
        title  = '[phase-1][docs] #5 Карточки Approved в 18_technology_watch.md'
        labels = 'phase-1,docs'
        body   = 'Версия, владелец, риски, дата пересмотра, ссылка на 16_tool_registry.md.' + "`n`n" + 'План: docs/ROADMAP.md #5'
    },
    @{
        title  = '[phase-1][docs] #6 Импорт регламентов из ТМКИ оригнал'
        labels = 'phase-1,docs'
        body   = 'Инвентаризация файлов (локально), выжимка в markdown без бинарников. Skill: vsdx-org-import.' + "`n`n" + 'План: docs/ROADMAP.md #6'
    },
    @{
        title  = '[phase-2][security] #7 Согласовать открытые вопросы RLS (Сатимол)'
        labels = 'phase-2,security'
        body   = @'
DRAFT v0.1 в ORG_MODEL.md готов. Осталось согласовать:
- уровни access_label
- scope Projektleiter к смежным подразделениям
- роль SchBK / group_admin
- модель доступа подрядчиков (contractor_id, guest role)

План: docs/ROADMAP.md #7
'@
    },
    @{
        title  = '[phase-2][security] #8 Схема сущностей org model'
        labels = 'phase-2,security'
        body   = 'Формализовать: company, department, position, employee, project, project_role, assignment.' + "`n`n" + 'План: docs/ROADMAP.md #8'
    },
    @{
        title  = '[phase-2][docs] #9 Актуализировать вакансии оргсхемы (10.09.2025)'
        labels = 'phase-2,docs'
        body   = 'Сверка вакансий от 10.09.2025 с HR/проектом.' + "`n`n" + 'План: docs/ROADMAP.md #9'
    }
)

$doneIssues = @(
    @{ title = '[phase-0][docs] #1 Синхронизировать перекрёстные ссылки'; labels = 'phase-0,docs,done'; body = 'Готово v0.1 — секции «Связанные документы» во всех главах.' },
    @{ title = '[phase-3][runtime] #10 JSON-схемы Run / Step / Event'; labels = 'phase-3,runtime,done'; body = 'Готово v0.1 — schemas/runtime/' },
    @{ title = '[phase-3][runtime] #11 State machine Loop Engine'; labels = 'phase-3,runtime,done'; body = 'Готово v0.1 — loop-state.schema.json' },
    @{ title = '[phase-3][security] #12 Каталог audit events'; labels = 'phase-3,security,runtime,done'; body = 'Готово v0.1 — audit-event-catalog.json' },
    @{ title = '[phase-4][runtime] #13 Ingest + dedup по content_hash'; labels = 'phase-4,runtime,done'; body = 'Готово v0.1 — schemas/document/' },
    @{ title = '[phase-4][runtime] #14 OCR MinerU + fallback Mistral OCR 4'; labels = 'phase-4,runtime,done'; body = 'Готово v0.1 — ocr-result.schema.json' },
    @{ title = '[phase-4][security] #15 Индексация с server-side фильтрацией'; labels = 'phase-4,security,runtime,done'; body = 'Готово v0.1 — search-*.schema.json' },
    @{ title = '[phase-5][runtime] #16 Каркас Tool Registry'; labels = 'phase-5,runtime,done'; body = 'Готово v0.1 — schemas/tools/' },
    @{ title = '[phase-5][security] #17 Tool gating по org/role/env'; labels = 'phase-5,security,runtime,done'; body = 'Готово v0.1 — tool-gating.rules.json' },
    @{ title = '[phase-6][runtime] #18 MVP runtime end-to-end'; labels = 'phase-6,runtime,done'; body = 'Готово v0.1 — mvp-flow.json' },
    @{ title = '[phase-6][security] #19 Security-review перед MVP-релизом'; labels = 'phase-6,security,done'; body = 'Готово v0.1 — schemas/security/' },
    @{ title = '[phase-0] #20 CI: markdown lint + secret scan'; labels = 'phase-0,done'; body = 'Готово v0.1 — handbook-ci.yml' }
)

foreach ($i in $openIssues) {
    New-RoadmapIssue -Title $i.title -Labels $i.labels -Body $i.body -Closed $false
}

if ($IncludeDone) {
    foreach ($i in $doneIssues) {
        New-RoadmapIssue -Title $i.title -Labels $i.labels -Body $i.body -Closed $true
    }
}

Write-Host "Готово. Issues: https://github.com/$repo/issues"
