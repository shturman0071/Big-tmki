# Полная переиндексация корпуса СКРУ-2 (все ingest-форматы, TMKI_OCR_MODE=local)
param(
    [ValidateSet("local", "http", "stub")]
    [string]$OcrMode = "local",
    [switch]$Resume,
    [switch]$LoadPg,
    [int]$CheckpointEvery = 200
)

$runtime = Resolve-Path $PSScriptRoot\..
$repo = Resolve-Path (Join-Path $runtime "..")
$env:PYTHONPATH = $runtime.Path
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

$dotenv = Join-Path $runtime ".env"
if (Test-Path $dotenv) {
    Get-Content $dotenv -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $name = $line.Substring(0, $eq).Trim()
        $value = $line.Substring($eq + 1).Trim().Trim('"').Trim("'")
        if ($name) { Set-Item -Path "Env:$name" -Value $value }
    }
}

if (-not $env:TMKI_REGULATIONS_ARCHIVE) {
    $env:TMKI_REGULATIONS_ARCHIVE = "D:\Курсор\СКРУ-2"
}
$env:TMKI_OCR_MODE = $OcrMode
if (-not $env:TMKI_LOCAL_TESSERACT) { $env:TMKI_LOCAL_TESSERACT = "1" }

Set-Location $runtime
Write-Host "Re-index: SKRU-2 (full extended ingest)" -ForegroundColor Cyan
Write-Host "  archive: $env:TMKI_REGULATIONS_ARCHIVE" -ForegroundColor DarkGray
Write-Host "  OCR:     $env:TMKI_OCR_MODE" -ForegroundColor DarkGray
Write-Host "  formats: pdf doc docx images xlsx ppt zip dwg csv sdr ..." -ForegroundColor DarkGray

$pyArgs = @(
    "scripts/reindex_regulations_local.py",
    "--corpus", "skru-2",
    "--ocr-mode", $OcrMode,
    "--checkpoint-every", "$CheckpointEvery"
)
if (-not $Resume) {
    $pyArgs += "--no-resume"
    Write-Host "  mode: fresh start (--no-resume)" -ForegroundColor Yellow
}

python @pyArgs
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if ($LoadPg) {
    Write-Host "`nLoad chunks to PostgreSQL (replace corpus skru-2)..." -ForegroundColor Cyan
    Set-Location $repo
    python scripts/load_skru2_to_chunks.py --corpus skru-2 --replace-corpus --embed-batch 48 --resume
    exit $LASTEXITCODE
}

exit 0
