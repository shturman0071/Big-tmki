# Русский языковой пакет для Tesseract (лучше OCR кириллицы в сканах).
# Запуск: .\scripts\setup_tesseract_rus.ps1

$ErrorActionPreference = "Stop"
$runtime = Resolve-Path $PSScriptRoot\..
$tessdata = Join-Path $runtime "tessdata"
$rus = Join-Path $tessdata "rus.traineddata"
$url = "https://github.com/tesseract-ocr/tessdata_fast/raw/main/rus.traineddata"

New-Item -ItemType Directory -Force -Path $tessdata | Out-Null

if (Test-Path $rus) {
    Write-Host "OK: rus.traineddata already exists at $rus" -ForegroundColor Green
    exit 0
}

Write-Host "Downloading rus.traineddata to $tessdata ..." -ForegroundColor Cyan
Invoke-WebRequest -Uri $url -OutFile $rus -UseBasicParsing
Write-Host "Done. Re-run: python scripts\reocr_files.py --corpus arm-ks --reocr-failed" -ForegroundColor Green
