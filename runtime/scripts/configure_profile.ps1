# Профили опциональных фич TMKI (запись в secrets.local + merge_env)
param(
    [ValidateSet("default", "fusion-llm", "docling", "kreuzberg", "pgvector", "chat", "full")]
    [string]$Profile = "default",
    [switch]$SessionOnly,
    [switch]$InstallDeps
)

$runtime = Resolve-Path $PSScriptRoot\..
$secrets = Join-Path $runtime "secrets.local"
$example = Join-Path $runtime "env.advanced.example"

$profiles = @{
    "default" = @{
        Remove = @("TMKI_RAG_FUSION_LLM", "TMKI_INGEST_PARSER", "DATABASE_URL", "TMKI_INDEX_BACKEND")
        Set    = @{ TMKI_INGEST_PARSER = "default"; TMKI_INDEX_BACKEND = "json" }
    }
    "fusion-llm" = @{
        Set = @{ TMKI_RAG_FUSION_LLM = "1" }
    }
    "docling" = @{
        Set = @{ TMKI_INGEST_PARSER = "docling" }
        PipExtra = "ingest-docling"
    }
    "kreuzberg" = @{
        Set = @{ TMKI_INGEST_PARSER = "kreuzberg" }
        PipExtra = "ingest-kreuzberg"
    }
    "pgvector" = @{
        Set = @{
            DATABASE_URL       = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
            TMKI_INDEX_BACKEND = "pgvector"
            TMKI_EMBEDDING_PROVIDER = "local"
        }
        PipExtra = "pgvector"
        Docker   = $true
    }
    "chat" = @{
        Set = @{
            TMKI_CHAT_MODE     = "1"
            TMKI_CHAT_PERSIST  = "1"
            TMKI_RAG_FUSION_LLM = "1"
            TMKI_INGEST_PARSER = "docling"
        }
        PipExtra = "ingest-docling"
    }
    "full" = @{
        Set = @{
            TMKI_RAG_FUSION_LLM = "1"
            TMKI_INGEST_PARSER  = "docling"
            DATABASE_URL        = "postgresql://tmki:tmki_dev@127.0.0.1:5432/tmki"
            TMKI_INDEX_BACKEND  = "pgvector"
        }
        PipExtra = @("ingest-docling", "pgvector", "rerank")
        Docker   = $true
    }
}

$p = $profiles[$Profile]
if (-not $p) { throw "Unknown profile: $Profile" }

function Read-EnvMap([string]$Path) {
    $map = @{}
    if (-not (Test-Path $Path)) { return $map }
    Get-Content $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $map[$line.Substring(0, $eq).Trim()] = $line.Substring($eq + 1).Trim()
    }
    return $map
}

if ($InstallDeps -and $p.PipExtra) {
    Set-Location $runtime
    $extras = $p.PipExtra
    if ($extras -is [string]) { $extras = @($extras) }
    foreach ($extra in $extras) {
        Write-Host "pip install -e `".[$extra]`"" -ForegroundColor Cyan
        pip install -e ".[$extra]"
    }
}

if ($p.Docker) {
    $compose = Join-Path $runtime "docker\docker-compose.yml"
    if (Test-Path $compose) {
        Write-Host "docker compose up -d (Postgres+pgvector)..." -ForegroundColor Cyan
        docker compose -f $compose up -d
    } else {
        Write-Host "WARN: docker-compose.yml not found" -ForegroundColor Yellow
    }
}

foreach ($key in $p.Set.Keys) {
    Set-Item -Path "Env:$key" -Value $p.Set[$key]
}
if ($p.Remove) {
    foreach ($key in $p.Remove) {
        Remove-Item "Env:$key" -ErrorAction SilentlyContinue
    }
}

Write-Host "Profile '$Profile' applied to session:" -ForegroundColor Green
$p.Set.GetEnumerator() | ForEach-Object { Write-Host "  $($_.Key)=$($_.Value)" }

if (-not $SessionOnly) {
    $map = Read-EnvMap $secrets
    if ($p.Remove) {
        foreach ($key in $p.Remove) { $map.Remove($key) }
    }
    foreach ($key in $p.Set.Keys) { $map[$key] = $p.Set[$key] }
    # Сохранить существующие ключи; дописать только если файла нет
    if (-not (Test-Path $secrets) -and (Test-Path (Join-Path $runtime "secrets.local.example"))) {
        $exampleMap = Read-EnvMap (Join-Path $runtime "secrets.local.example")
        foreach ($key in $exampleMap.Keys) {
            if (-not $map.ContainsKey($key)) { $map[$key] = $exampleMap[$key] }
        }
    }
    $header = @("# TMKI secrets.local", "# profile: $Profile", "")
    $body = ($map.Keys | Sort-Object | ForEach-Object { "$_=$($map[$_])" })
    $footer = @("", "# Advanced: runtime/env.advanced.example")
    Set-Content -Path $secrets -Value (($header + $body + $footer) -join "`n") -Encoding UTF8
    Write-Host "Updated: $secrets" -ForegroundColor Green
    Set-Location $runtime
    python scripts/merge_env.py
    if ($Profile -eq "pgvector" -or $Profile -eq "full") {
        Write-Host "Load vectors: python scripts/load_regulations_pgvector.py --variant v2" -ForegroundColor Yellow
    }
}

Write-Host "Restart demo: .\scripts\run_tmki_demo_ui.ps1" -ForegroundColor Yellow
