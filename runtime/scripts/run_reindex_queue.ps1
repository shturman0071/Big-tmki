# Очередь фоновых задач: дождаться re-OCR «Армировка КС», затем re-index «СКРУ-2»
param(
    [int]$WaitPid = 0,
    [string]$WaitLog = "artifacts/arm-ks-import/reocr-rus.log",
    [ValidateSet("local", "http", "stub")]
    [string]$OcrMode = "local",
    [switch]$NoResume,
    [int]$PollSeconds = 30
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

if (-not $env:TMKI_REGULATIONS_ARCHIVE) {
    $env:TMKI_REGULATIONS_ARCHIVE = "D:\Курсор\СКРУ-2"
}

$logPath = Join-Path $runtime $WaitLog
$queueLog = Join-Path $runtime "artifacts\regulations-import\reindex-queue.log"
$queueLogDir = Split-Path $queueLog -Parent
if (-not (Test-Path $queueLogDir)) {
    New-Item -ItemType Directory -Path $queueLogDir -Force | Out-Null
}

function Write-QueueLog([string]$Message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "[$ts] $Message"
    Add-Content -Path $queueLog -Value $line -Encoding UTF8
    Write-Host $line
}

Write-QueueLog "Queue started: wait arm-ks re-OCR, then re-index skru-2"

if ($WaitPid -gt 0) {
    Write-QueueLog "Waiting for PID $WaitPid ..."
    while ($true) {
        $proc = Get-Process -Id $WaitPid -ErrorAction SilentlyContinue
        if (-not $proc) {
            Write-QueueLog "PID $WaitPid finished"
            break
        }
        Start-Sleep -Seconds $PollSeconds
    }
} elseif (Test-Path $logPath) {
    Write-QueueLog "Waiting for Done: in $WaitLog ..."
    while ($true) {
        $tail = Get-Content $logPath -Tail 5 -ErrorAction SilentlyContinue
        if ($tail -match "Done:") {
            Write-QueueLog "arm-ks re-OCR completed (log marker)"
            break
        }
        Start-Sleep -Seconds $PollSeconds
    }
} else {
    Write-QueueLog "WARN: no WaitPid and log missing - starting skru-2 immediately"
}

Set-Location $runtime
$tessdata = Join-Path $runtime "tessdata"
if (Test-Path (Join-Path $tessdata "rus.traineddata")) {
    $env:TESSDATA_PREFIX = $tessdata
    Write-QueueLog "TESSDATA_PREFIX=$tessdata"
}

$env:TMKI_OCR_MODE = $OcrMode
Write-QueueLog "Starting re-index skru-2 (OCR=$OcrMode, archive=$env:TMKI_REGULATIONS_ARCHIVE)"

$pyArgs = @(
    "scripts/reindex_regulations_local.py",
    "--corpus", "skru-2",
    "--ocr-mode", $OcrMode,
    "--checkpoint-every", "200"
)
if ($NoResume) {
    $pyArgs += "--no-resume"
}

python @pyArgs 2>&1 | Tee-Object -FilePath $queueLog -Append
$exit = $LASTEXITCODE
Write-QueueLog "skru-2 re-index finished (exit=$exit)"
exit $exit
