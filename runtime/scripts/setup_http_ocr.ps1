# Проверка и smoke HTTP OCR (MinerU / Mistral)
$runtime = Resolve-Path $PSScriptRoot\..
$env:PYTHONPATH = $runtime.Path
Set-Location $runtime

if (-not $env:MINERU_API_URL -and -not $env:MISTRAL_OCR_API_URL) {
    Write-Host "MINERU_API_URL / MISTRAL_OCR_API_URL не заданы — mock smoke"
    python scripts/run_ocr_http_smoke.py --mock
    exit $LASTEXITCODE
}

$env:TMKI_OCR_MODE = "http"
python scripts/check_ocr_http.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/run_ocr_http_smoke.py
