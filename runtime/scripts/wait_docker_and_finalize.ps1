# Ожидание Docker и finalize (hands-off после 100% re-index)
param(
    [int]$DockerTimeoutSeconds = 600,
    [int]$DockerPollSeconds = 10,
    [int]$PollSeconds = 0,
    [string]$Query = "промбезопасность кран"
)

$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
Set-Location $runtime

python scripts/wait_for_docker.py --timeout $DockerTimeoutSeconds --poll $DockerPollSeconds
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $PSScriptRoot\wait_and_finalize.ps1 -PollSeconds $PollSeconds -Query $Query
