# Создание GitHub Issues из roadmap (требуется gh CLI + gh auth login)
# Usage: .\scripts\create-github-issues.ps1 [-IncludeDone]

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
    Write-Error "GitHub CLI (gh) ne naiden. Ustanovite: winget install GitHub.cli, zatem perezapustite terminal."
}

function Invoke-Gh {
    param([string[]]$GhArgs)
    & $gh @GhArgs
}

$authCheck = & $gh auth status --hostname github.com 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Error "Ne avtorizovany v gh. Vypolnite:`n& `"$gh`" auth login -h github.com -p https -w`n$authCheck"
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

    Write-Host "Creating: $Title"
    $createArgs = @('issue', 'create', '--repo', $repo, '--title', $Title, '--body', $Body) + $labelArgs
    $url = Invoke-Gh $createArgs
    if ($Closed -and $url) {
        $num = ($url -split '/')[-1]
        Invoke-Gh @('issue', 'close', $num, '--repo', $repo, '--comment', 'Zakryto: realizovano v handbook v0.1 (sm. docs/ROADMAP.md).') | Out-Null
    }
}

$openIssues = @(
    @{
        title  = '[phase-0][docs] #2 Zakrepit vladelcev i process apruva handbook'
        labels = 'phase-0,docs'
        body   = @'
Opredelit:
- kto apruvit izmeneniya MUST-trebovanij
- kogda obyazatelen security-review
- kogda obnovlyat README.md

Kriterij: razdel v AGENTS.md ili README.
Roadmap: docs/ROADMAP.md #2
'@
    },
    @{
        title  = '[phase-1][docs] #4 Naznachit owners v 13_ai_skills_registry.md'
        labels = 'phase-1,docs'
        body   = 'Dlya kazhdogo skill ukazat owner i odin primer scenariya inputs/outputs.' + "`n`n" + 'Roadmap: docs/ROADMAP.md #4'
    },
    @{
        title  = '[phase-1][docs] #5 Kartochki Approved v 18_technology_watch.md'
        labels = 'phase-1,docs'
        body   = 'Versiya, owner, riski, data peresmotra, ssylka na 16_tool_registry.md.' + "`n`n" + 'Roadmap: docs/ROADMAP.md #5'
    },
    @{
        title  = '[phase-1][docs] #6 Import reglamentov iz TMKI original'
        labels = 'phase-1,docs'
        body   = 'Inventarizaciya fajlov (lokalno), vyzhimka v markdown bez binarnikov. Skill: vsdx-org-import.' + "`n`n" + 'Roadmap: docs/ROADMAP.md #6'
    },
    @{
        title  = '[phase-2][security] #7 Soglasovat otkrytye voprosy RLS (Satimol)'
        labels = 'phase-2,security'
        body   = @'
DRAFT v0.1 v ORG_MODEL.md gotov. Ostalos soglasovat:
- urovni access_label
- scope Projektleiter k smezhnym podrazdeleniyam
- rol SchBK / group_admin
- model dostupa podryadchikov (contractor_id, guest role)

Roadmap: docs/ROADMAP.md #7
'@
    },
    @{
        title  = '[phase-2][security] #8 Skhema sushchnostej org model'
        labels = 'phase-2,security'
        body   = 'Formalizovat: company, department, position, employee, project, project_role, assignment.' + "`n`n" + 'Roadmap: docs/ROADMAP.md #8'
    },
    @{
        title  = '[phase-2][docs] #9 Aktualizirovat vakansii orgshemы (10.09.2025)'
        labels = 'phase-2,docs'
        body   = 'Sverka vakansij ot 10.09.2025 s HR/proektom.' + "`n`n" + 'Roadmap: docs/ROADMAP.md #9'
    }
)

$doneIssues = @(
    @{ title = '[phase-0][docs] #1 Sinkhronizirovat perekrestnye ssylki'; labels = 'phase-0,docs,done'; body = 'Done v0.1 - Related docs sections in all chapters.' },
    @{ title = '[phase-3][runtime] #10 JSON-shemy Run / Step / Event'; labels = 'phase-3,runtime,done'; body = 'Done v0.1 - schemas/runtime/' },
    @{ title = '[phase-3][runtime] #11 State machine Loop Engine'; labels = 'phase-3,runtime,done'; body = 'Done v0.1 - loop-state.schema.json' },
    @{ title = '[phase-3][security] #12 Katalog audit events'; labels = 'phase-3,security,runtime,done'; body = 'Done v0.1 - audit-event-catalog.json' },
    @{ title = '[phase-4][runtime] #13 Ingest + dedup po content_hash'; labels = 'phase-4,runtime,done'; body = 'Done v0.1 - schemas/document/' },
    @{ title = '[phase-4][runtime] #14 OCR MinerU + fallback Mistral OCR 4'; labels = 'phase-4,runtime,done'; body = 'Done v0.1 - ocr-result.schema.json' },
    @{ title = '[phase-4][security] #15 Indeksaciya s server-side filtraciej'; labels = 'phase-4,security,runtime,done'; body = 'Done v0.1 - search-*.schema.json' },
    @{ title = '[phase-5][runtime] #16 Karkas Tool Registry'; labels = 'phase-5,runtime,done'; body = 'Done v0.1 - schemas/tools/' },
    @{ title = '[phase-5][security] #17 Tool gating po org/role/env'; labels = 'phase-5,security,runtime,done'; body = 'Done v0.1 - tool-gating.rules.json' },
    @{ title = '[phase-6][runtime] #18 MVP runtime end-to-end'; labels = 'phase-6,runtime,done'; body = 'Done v0.1 - mvp-flow.json' },
    @{ title = '[phase-6][security] #19 Security-review pered MVP-relizom'; labels = 'phase-6,security,done'; body = 'Done v0.1 - schemas/security/' },
    @{ title = '[phase-0] #20 CI: markdown lint + secret scan'; labels = 'phase-0,done'; body = 'Done v0.1 - handbook-ci.yml' }
)

foreach ($i in $openIssues) {
    New-RoadmapIssue -Title $i.title -Labels $i.labels -Body $i.body -Closed $false
}

if ($IncludeDone) {
    foreach ($i in $doneIssues) {
        New-RoadmapIssue -Title $i.title -Labels $i.labels -Body $i.body -Closed $true
    }
}

Write-Host "Done. Open: https://github.com/$repo/issues"
