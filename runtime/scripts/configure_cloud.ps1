# Merge secrets.local -> .env
param([switch]$SkipHealth)

$runtime = Resolve-Path $PSScriptRoot\..
Set-Location $runtime
python scripts/merge_env.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($SkipHealth) { exit 0 }

$env:PYTHONPATH = $runtime.Path
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
python scripts/check_runtime_health.py
$code = $LASTEXITCODE
if ($env:TMKI_OCR_MODE -eq "http") {
    python scripts/check_ocr_http.py
    if ($LASTEXITCODE -ne 0) { $code = 1 }
}
exit $code
