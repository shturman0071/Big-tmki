# Установка OCR-зависимостей и проверка конфигурации
param(
    [ValidateSet("local", "http", "stub")]
    [string]$Mode = "local"
)

$runtime = Resolve-Path $PSScriptRoot\..
Set-Location $runtime

Write-Host "pip install -e '.[ocr,search]'" -ForegroundColor Cyan
pip install -e ".[ocr,search]"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$envExample = Join-Path $runtime "env.ocr.example"
$dotenv = Join-Path $runtime ".env"
if (-not (Test-Path $dotenv) -and (Test-Path $envExample)) {
    Copy-Item $envExample $dotenv
    Write-Host "Created $dotenv from env.ocr.example" -ForegroundColor Green
} elseif (Test-Path $dotenv) {
    Write-Host "Using existing $dotenv" -ForegroundColor DarkGray
} else {
    Write-Host "Create runtime/.env from env.ocr.example" -ForegroundColor Yellow
}

$env:PYTHONPATH = $runtime.Path
$env:TMKI_OCR_MODE = $Mode

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
    if ($env:TMKI_OCR_MODE) { $env:TMKI_OCR_MODE = $env:TMKI_OCR_MODE }
}

Write-Host "`nTMKI_OCR_MODE=$($env:TMKI_OCR_MODE)" -ForegroundColor Cyan
python scripts/check_runtime_health.py
$health = $LASTEXITCODE

if ($env:TMKI_OCR_MODE -eq "http") {
    python scripts/check_ocr_http.py
    if ($LASTEXITCODE -ne 0) { $health = 1 }
}

if ($env:TMKI_OCR_MODE -eq "local") {
    python -c "from pypdf import PdfReader; from tmki_ocr.extractors import extract_local_text; print('pypdf + extractors OK')"
    if ($LASTEXITCODE -ne 0) { $health = 1 }
}

exit $health
