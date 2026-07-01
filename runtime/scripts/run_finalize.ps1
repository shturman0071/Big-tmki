# Finalize с проверкой Docker (после 100% re-index)
param(
    [int]$PollSeconds = 0,
    [string]$Query = "промбезопасность кран",
    [switch]$WaitDocker,
    [int]$DockerTimeoutSeconds = 600,
    [int]$DockerPollSeconds = 10
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
Set-Location $runtime

if ($WaitDocker) {
    python scripts/wait_for_docker.py --timeout $DockerTimeoutSeconds --poll $DockerPollSeconds
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    python scripts/check_docker.py --require
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Start Docker Desktop or use: .\scripts\run_finalize.ps1 -WaitDocker" -ForegroundColor Yellow
        exit 1
    }
}

& $PSScriptRoot\wait_and_finalize.ps1 -PollSeconds $PollSeconds -Query $Query
