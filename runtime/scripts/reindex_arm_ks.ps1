# Полная переиндексация корпуса «Армировка КС» (все подпапки, ingest-кандидаты)
param(
    [ValidateSet("local", "http", "stub")]
    [string]$OcrMode = "local",
    [switch]$Resume,
    [int]$CheckpointEvery = 100
)

$runtime = Resolve-Path $PSScriptRoot\..
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

if (-not $env:TMKI_ARM_KS_ARCHIVE) {
    $env:TMKI_ARM_KS_ARCHIVE = "D:\Курсор\Армировка КС"
}
$env:TMKI_OCR_MODE = $OcrMode

Set-Location $runtime
Write-Host "Re-index: Армировка КС" -ForegroundColor Cyan
Write-Host "  archive: $env:TMKI_ARM_KS_ARCHIVE" -ForegroundColor DarkGray
Write-Host "  OCR:     $env:TMKI_OCR_MODE" -ForegroundColor DarkGray

$pyArgs = @(
    "scripts/reindex_regulations_local.py",
    "--corpus", "arm-ks",
    "--ocr-mode", $OcrMode,
    "--checkpoint-every", "$CheckpointEvery"
)
if (-not $Resume) {
    $pyArgs += "--no-resume"
}

python @pyArgs
exit $LASTEXITCODE
