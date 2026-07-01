# Создание GitHub Issues из roadmap (требуется gh CLI + gh auth login)
# Usage: .\scripts\create-github-issues.ps1

$ErrorActionPreference = "Stop"
$repo = "shturman0071/Big-tmki"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI (gh) не установлен. Установите: winget install GitHub.cli"
}

$labels = @("phase-0","phase-1","phase-2","phase-3","phase-4","phase-5","phase-6","security","runtime","docs")
foreach ($l in $labels) {
    gh label create $l --repo $repo --force 2>$null
}

$issues = @(
    @{ title="[phase-0][docs] Закрепить владельцев и процесс апрува хэндбука"; labels="phase-0,docs"; body="Определить owner MUST-требований, когда нужен security-review, когда обновлять README.`n`nКритерий: раздел в AGENTS.md или README." },
    @{ title="[phase-1][docs] Назначить owners в 13_ai_skills_registry.md"; labels="phase-1,docs"; body="Для каждого skill указать owner и один пример сценария inputs/outputs." },
    @{ title="[phase-1][docs] Карточки Approved в 18_technology_watch.md"; labels="phase-1,docs"; body="Версия, owner, риски, дата пересмотра для каждой Approved-технологии." },
    @{ title="[phase-1][docs] Импорт регламентов из ТМКИ оригнал"; labels="phase-1,docs"; body="Инвентаризация и выжимка в markdown без бинарников." },
    @{ title="[phase-2][security] Матрица роль → права → RLS"; labels="phase-2,security"; body="На базе ORG_MODEL.md (Сатимол). Выход: таблица role × resource × action × RLS-поля." },
    @{ title="[phase-2][security] Схема сущностей org model"; labels="phase-2,security"; body="company, department, position, employee, project, project_role, assignment." },
    @{ title="[phase-2][docs] Актуализировать вакансии оргсхемы"; labels="phase-2,docs"; body="Сверка вакансий от 10.09.2025 с HR/проектом." },
    @{ title="[phase-3][runtime] JSON-схемы Run / Step / Event"; labels="phase-3,runtime"; body="Формализация контрактов из 10_ai_runtime.md." },
    @{ title="[phase-3][runtime] State machine Loop Engine"; labels="phase-3,runtime"; body="Лимиты, таймауты, budget, circuit breaker." },
    @{ title="[phase-3][security] Каталог audit events"; labels="phase-3,security,runtime"; body="event_type, severity, санитизация payload." },
    @{ title="[phase-4][runtime] Ingest + dedup по content_hash"; labels="phase-4,runtime"; body="По 09_document_processing.md + ORG_MODEL поля." },
    @{ title="[phase-4][runtime] OCR MinerU + fallback Mistral OCR 4"; labels="phase-4,runtime"; body="Метрики fallback, warnings в metadata." },
    @{ title="[phase-4][security] Индексация с server-side фильтрацией"; labels="phase-4,security,runtime"; body="pgvector + RLS до выдачи в RAG." },
    @{ title="[phase-5][runtime] Каркас Tool Registry"; labels="phase-5,runtime"; body="Provider pattern по 16_tool_registry.md." },
    @{ title="[phase-6][runtime] MVP runtime end-to-end"; labels="phase-6,runtime"; body="Context → RAG → Loop → Judge → Audit." }
)

foreach ($i in $issues) {
    Write-Host "Creating: $($i.title)"
    gh issue create --repo $repo --title $i.title --label $i.labels --body $i.body
}

Write-Host "Done. Open: https://github.com/$repo/issues"
