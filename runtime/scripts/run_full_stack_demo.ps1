# Полный локальный стек: Docker Postgres + pgvector sync + demo
param(
    [string]$Query = "промбезопасность кран",
    [switch]$SkipDocker,
    [switch]$Experience,
    [switch]$Milestone
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:TMKI_MVP_MESSAGE = $Query
Set-Location $runtime

if (-not $SkipDocker) {
    & $PSScriptRoot\tmki_stack_up.ps1
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

& $PSScriptRoot\sync_pgvector_incremental.ps1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$demoArgs = @("-Query", $Query, "-Backend", "pgvector")
if ($Experience) { $demoArgs += "-Experience" }
if ($Milestone) { $demoArgs += "-Milestone" }
& $PSScriptRoot\run_tmki_demo.ps1 @demoArgs
