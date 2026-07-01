# Finalize с проверкой Docker (после 100% re-index)
param(
    [int]$PollSeconds = 0,
    [string]$Query = "промбезопасность кран"
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
Set-Location $runtime

python scripts/check_docker.py --require
if ($LASTEXITCODE -ne 0) {
    Write-Host "Start Docker Desktop and retry: .\scripts\run_finalize.ps1" -ForegroundColor Yellow
    exit 1
}

& $PSScriptRoot\wait_and_finalize.ps1 -PollSeconds $PollSeconds -Query $Query
