# Pandoc + mcp-pandoc (uvx) для dev-шаблонов MD→DOCX.
# Запуск: .\runtime\scripts\setup_pandoc_mcp.ps1
# MCP-конфиг: config/mcp.dev.example.json → скопируйте блок "pandoc" в .cursor/mcp.json

$ErrorActionPreference = "Stop"
$root = Resolve-Path $PSScriptRoot\..\..
$templates = Join-Path $root "schemas\document\examples\templates"

function Test-Cmd($name) {
    $c = Get-Command $name -ErrorAction SilentlyContinue
    return [bool]$c
}

if (-not (Test-Cmd pandoc)) {
    Write-Host "Installing Pandoc via winget..." -ForegroundColor Cyan
    winget install --id JohnMacFarlane.Pandoc -e --accept-source-agreements --accept-package-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
        [System.Environment]::GetEnvironmentVariable("Path", "User")
}

if (-not (Test-Cmd uvx)) {
    Write-Host "Installing uv (provides uvx) via pip..." -ForegroundColor Cyan
    python -m pip install -U uv
    $scripts = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
    if ($scripts -and (Test-Path $scripts)) {
        $env:Path = "$scripts;$env:Path"
    }
}

Write-Host "`nVersions:" -ForegroundColor Cyan
pandoc --version | Select-Object -First 1
uvx --version

$md = Join-Path $templates "instruction_internal.md"
$out = Join-Path $root "runtime\artifacts\templates"
New-Item -ItemType Directory -Force -Path $out | Out-Null
$docx = Join-Path $out "instruction_internal_smoke.docx"

if (Test-Path $md) {
    Write-Host "`nSmoke test: pandoc MD -> DOCX" -ForegroundColor Cyan
    pandoc $md -o $docx
    if (Test-Path $docx) {
        $kb = [math]::Round((Get-Item $docx).Length / 1KB, 1)
        Write-Host "OK: $docx ($kb KB)" -ForegroundColor Green
    }
}

Write-Host "`nMCP: добавьте в .cursor/mcp.json блок из config/mcp.dev.example.json (pandoc + uvx)." -ForegroundColor Yellow
Write-Host "Шаблоны: schemas/document/examples/templates/" -ForegroundColor DarkGray
