# Полный локальный стек: Docker Postgres + pgvector sync + demo
param(
    [string]$Query = "промбезопасность кран",
    [switch]$SkipDocker
)

$runtime = Resolve-Path $PSScriptRoot\..
Set-Location $runtime

if (-not $SkipDocker) {
    & $PSScriptRoot\tmki_stack_up.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $PSScriptRoot\sync_pgvector_incremental.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PSScriptRoot\run_tmki_demo.ps1 -Query $Query -Backend pgvector
